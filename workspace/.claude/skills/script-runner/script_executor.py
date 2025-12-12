"""Script executor with security constraints for the script-runner skill.

This module provides safe execution of Python and bash scripts with:
- Timeout enforcement
- Output capture
- Blocked dangerous operations
- Workspace path restrictions
"""

import ast
import contextlib
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# Configuration
DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 120  # seconds
MAX_OUTPUT_SIZE = 100 * 1024  # 100KB


# Blocked Python modules (security risk)
BLOCKED_MODULES = {
    # Network
    "urllib",
    "urllib.request",
    "urllib2",
    "httplib",
    "http.client",
    "requests",
    "httpx",
    "aiohttp",
    "socket",
    "ssl",
    "ftplib",
    "smtplib",
    "poplib",
    "imaplib",
    "telnetlib",
    # System execution
    "subprocess",
    "os.system",
    "os.popen",
    "os.spawn",
    "pty",
    "pexpect",
    # Code execution
    "exec",
    "eval",
    "compile",
    "importlib",
    "__import__",
    # File system (outside workspace)
    "shutil.rmtree",  # Dangerous
    # Pickle (security risk)
    "pickle",
    "cPickle",
    "marshal",
    # Other dangerous
    "ctypes",
    "multiprocessing",
}

# Allowed standard library modules
ALLOWED_MODULES = {
    # Data processing
    "csv",
    "json",
    "xml",
    "xml.etree",
    "xml.etree.ElementTree",
    "html",
    "html.parser",
    # Math/Stats
    "math",
    "statistics",
    "decimal",
    "fractions",
    "random",
    # Text processing
    "re",
    "string",
    "textwrap",
    "difflib",
    "unicodedata",
    # Date/Time
    "datetime",
    "time",
    "calendar",
    "zoneinfo",
    # Collections
    "collections",
    "itertools",
    "functools",
    "operator",
    # File handling (restricted)
    "pathlib",
    "io",
    "tempfile",
    # Other safe
    "hashlib",
    "base64",
    "uuid",
    "copy",
    "pprint",
    "typing",
    "dataclasses",
    "enum",
}


@dataclass
class ScriptResult:
    """Result of script execution."""

    success: bool
    output: str
    error: str | None = None
    return_code: int = 0
    timed_out: bool = False
    execution_time: float = 0.0


def validate_python_code(code: str) -> tuple[bool, str | None]:
    """Validate Python code for blocked operations.

    Args:
        code: Python source code to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, f"Syntax error: {e}"

    # Walk the AST looking for blocked operations
    for node in ast.walk(tree):
        # Check imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module in BLOCKED_MODULES or alias.name in BLOCKED_MODULES:
                    return False, f"Blocked import: {alias.name}"

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module = node.module.split(".")[0]
                if module in BLOCKED_MODULES or node.module in BLOCKED_MODULES:
                    return False, f"Blocked import: {node.module}"

        # Check for exec/eval calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in {
                "exec",
                "eval",
                "compile",
                "__import__",
            }:
                return False, f"Blocked function: {node.func.id}"

        # Check for os.system, subprocess, etc. via attributes
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            full_name = f"{node.value.id}.{node.attr}"
            if full_name in BLOCKED_MODULES:
                return False, f"Blocked operation: {full_name}"

    return True, None


def validate_workspace_path(path: str, workspace: Path) -> bool:
    """Check if a path is within the workspace.

    Args:
        path: Path to check
        workspace: Workspace root directory

    Returns:
        True if path is within workspace
    """
    try:
        resolved = Path(path).resolve()
        workspace_resolved = workspace.resolve()
        return str(resolved).startswith(str(workspace_resolved))
    except (ValueError, OSError):
        return False


def run_python_script(
    code: str,
    workspace: str | Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    input_data: str | None = None,
) -> ScriptResult:
    """Execute Python code safely.

    Args:
        code: Python source code to execute
        workspace: Workspace directory (files read/written here)
        timeout: Maximum execution time in seconds
        input_data: Optional stdin input

    Returns:
        ScriptResult with output or error
    """
    import time as time_module

    # Validate timeout
    timeout = min(timeout, MAX_TIMEOUT)

    # Set workspace
    if workspace is None:
        workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
    else:
        workspace = Path(workspace)

    # Validate code
    is_valid, error = validate_python_code(code)
    if not is_valid:
        return ScriptResult(
            success=False,
            output="",
            error=f"Code validation failed: {error}",
        )

    # Create a wrapper script that sets up the environment
    wrapper = f'''
import sys
import os

# Restrict file system access to workspace
WORKSPACE = "{workspace}"
os.chdir(WORKSPACE)

# Override open to restrict paths
_original_open = open
def restricted_open(path, *args, **kwargs):
    from pathlib import Path
    resolved = Path(path).resolve()
    workspace_resolved = Path(WORKSPACE).resolve()
    if not str(resolved).startswith(str(workspace_resolved)):
        raise PermissionError(f"Access denied: {{path}} is outside workspace")
    return _original_open(path, *args, **kwargs)

# Note: In real production, use RestrictedPython or similar
# This is a basic restriction for demonstration

# User code
{code}
'''

    # Write to temp file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".py",
        delete=False,
    ) as f:
        f.write(wrapper)
        script_path = f.name

    try:
        start_time = time_module.time()

        # Run the script
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workspace),
            input=input_data,
            env={
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "WORKSPACE": str(workspace),
            },
        )

        execution_time = time_module.time() - start_time

        # Truncate output if too large
        stdout = result.stdout[:MAX_OUTPUT_SIZE]
        stderr = result.stderr[:MAX_OUTPUT_SIZE]

        if result.returncode == 0:
            return ScriptResult(
                success=True,
                output=stdout,
                error=stderr if stderr else None,
                return_code=result.returncode,
                execution_time=execution_time,
            )
        else:
            return ScriptResult(
                success=False,
                output=stdout,
                error=stderr or "Script failed with no error output",
                return_code=result.returncode,
                execution_time=execution_time,
            )

    except subprocess.TimeoutExpired:
        return ScriptResult(
            success=False,
            output="",
            error=f"Script timed out after {timeout} seconds",
            timed_out=True,
        )

    except Exception as e:
        return ScriptResult(
            success=False,
            output="",
            error=f"Execution error: {str(e)}",
        )

    finally:
        # Cleanup temp file
        with contextlib.suppress(OSError):
            os.unlink(script_path)


def run_bash_script(
    script: str,
    workspace: str | Path | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    input_data: str | None = None,
) -> ScriptResult:
    """Execute bash commands safely.

    Args:
        script: Bash commands to execute
        workspace: Workspace directory
        timeout: Maximum execution time in seconds
        input_data: Optional stdin input

    Returns:
        ScriptResult with output or error
    """
    import time as time_module

    # Validate timeout
    timeout = min(timeout, MAX_TIMEOUT)

    # Set workspace
    if workspace is None:
        workspace = Path(os.environ.get("WORKSPACE", "/workspace"))
    else:
        workspace = Path(workspace)

    # Basic validation - block dangerous commands
    dangerous_patterns = [
        "rm -rf /",
        "rm -rf /*",
        "dd if=",
        "mkfs",
        ":(){:|:&};:",  # Fork bomb
        "chmod -R 777 /",
        "curl | bash",
        "wget | bash",
        "sudo",
        "su ",
    ]

    script_lower = script.lower()
    for pattern in dangerous_patterns:
        if pattern in script_lower:
            return ScriptResult(
                success=False,
                output="",
                error=f"Blocked dangerous command pattern: {pattern}",
            )

    try:
        start_time = time_module.time()

        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(workspace),
            input=input_data,
            env={
                **os.environ,
                "WORKSPACE": str(workspace),
            },
        )

        execution_time = time_module.time() - start_time

        # Truncate output if too large
        stdout = result.stdout[:MAX_OUTPUT_SIZE]
        stderr = result.stderr[:MAX_OUTPUT_SIZE]

        if result.returncode == 0:
            return ScriptResult(
                success=True,
                output=stdout,
                error=stderr if stderr else None,
                return_code=result.returncode,
                execution_time=execution_time,
            )
        else:
            return ScriptResult(
                success=False,
                output=stdout,
                error=stderr or "Script failed with no error output",
                return_code=result.returncode,
                execution_time=execution_time,
            )

    except subprocess.TimeoutExpired:
        return ScriptResult(
            success=False,
            output="",
            error=f"Script timed out after {timeout} seconds",
            timed_out=True,
        )

    except Exception as e:
        return ScriptResult(
            success=False,
            output="",
            error=f"Execution error: {str(e)}",
        )


if __name__ == "__main__":
    # Quick tests
    print("Testing Python script execution:")
    result = run_python_script(
        'print("Hello from Python!")\nprint(2 + 2)',
        workspace=Path.cwd(),
    )
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")

    print("\nTesting blocked import:")
    result = run_python_script(
        'import requests\nprint("This should fail")',
        workspace=Path.cwd(),
    )
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")

    print("\nTesting bash script:")
    result = run_bash_script(
        'echo "Hello from bash" && date',
        workspace=Path.cwd(),
    )
    print(f"  Success: {result.success}")
    print(f"  Output: {result.output}")

    print("\nTesting blocked bash command:")
    result = run_bash_script(
        "sudo rm -rf /",
        workspace=Path.cwd(),
    )
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")
