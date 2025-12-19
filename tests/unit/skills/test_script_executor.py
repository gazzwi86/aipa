"""Unit tests for the script-runner skill executor.

These tests verify the script_executor module works correctly with
proper security constraints and execution handling.
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add the skill directory to the path for imports
skill_path = Path(__file__).parent.parent.parent.parent / "workspace/.claude/skills/script-runner"
sys.path.insert(0, str(skill_path))

from script_executor import (  # noqa: E402
    run_bash_script,
    run_python_script,
    validate_python_code,
    validate_workspace_path,
)


class TestValidatePythonCode:
    """Tests for Python code validation."""

    def test_valid_simple_code(self):
        """Should accept simple valid Python code."""
        is_valid, error = validate_python_code('print("hello")')
        assert is_valid is True
        assert error is None

    def test_valid_imports(self):
        """Should accept allowed imports."""
        code = """
import json
import csv
import datetime
from pathlib import Path
"""
        is_valid, error = validate_python_code(code)
        assert is_valid is True

    def test_blocks_requests(self):
        """Should block requests import."""
        is_valid, error = validate_python_code("import requests")
        assert is_valid is False
        assert "Blocked import" in error

    def test_blocks_subprocess(self):
        """Should block subprocess import."""
        is_valid, error = validate_python_code("import subprocess")
        assert is_valid is False
        assert "Blocked import" in error

    def test_blocks_socket(self):
        """Should block socket import."""
        is_valid, error = validate_python_code("import socket")
        assert is_valid is False
        assert "Blocked import" in error

    def test_blocks_exec(self):
        """Should block exec() calls."""
        is_valid, error = validate_python_code('exec("print(1)")')
        assert is_valid is False
        assert "Blocked function: exec" in error

    def test_blocks_eval(self):
        """Should block eval() calls."""
        is_valid, error = validate_python_code('eval("1+1")')
        assert is_valid is False
        assert "Blocked function: eval" in error

    def test_syntax_error(self):
        """Should catch syntax errors."""
        is_valid, error = validate_python_code("def broken(")
        assert is_valid is False
        assert "Syntax error" in error

    def test_blocks_httpx(self):
        """Should block httpx import."""
        is_valid, error = validate_python_code("import httpx")
        assert is_valid is False
        assert "Blocked import" in error

    def test_blocks_pickle(self):
        """Should block pickle (security risk)."""
        is_valid, error = validate_python_code("import pickle")
        assert is_valid is False
        assert "Blocked import" in error


class TestValidateWorkspacePath:
    """Tests for workspace path validation."""

    def test_path_within_workspace(self):
        """Should allow paths within workspace."""
        workspace = Path("/workspace")
        assert validate_workspace_path("/workspace/files/data.csv", workspace) is True
        assert validate_workspace_path("/workspace/subdir/file.txt", workspace) is True

    def test_path_outside_workspace(self):
        """Should reject paths outside workspace."""
        workspace = Path("/workspace")
        assert validate_workspace_path("/etc/passwd", workspace) is False
        assert validate_workspace_path("/home/user/data.csv", workspace) is False

    def test_path_traversal_attack(self):
        """Should reject path traversal attempts."""
        workspace = Path("/workspace")
        # Note: Path.resolve() handles .. so this should resolve to /etc/passwd
        assert validate_workspace_path("/workspace/../etc/passwd", workspace) is False


class TestRunPythonScript:
    """Tests for Python script execution."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "files").mkdir()
            yield workspace

    def test_simple_script(self, temp_workspace):
        """Should execute simple Python code."""
        result = run_python_script(
            'print("Hello, World!")',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "Hello, World!" in result.output

    def test_math_calculation(self, temp_workspace):
        """Should handle math calculations."""
        result = run_python_script(
            "print(sum([1, 2, 3, 4, 5]))",
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "15" in result.output

    def test_csv_processing(self, temp_workspace):
        """Should process CSV files."""
        # Create test CSV
        csv_file = temp_workspace / "files" / "test.csv"
        csv_file.write_text("name,value\nAlice,10\nBob,20\nCharlie,30\n")

        result = run_python_script(
            f'''
import csv
with open("{csv_file}") as f:
    reader = csv.DictReader(f)
    total = sum(int(row["value"]) for row in reader)
print(f"Total: {{total}}")
''',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "Total: 60" in result.output

    def test_json_processing(self, temp_workspace):
        """Should process JSON files."""
        json_file = temp_workspace / "files" / "test.json"
        json_file.write_text('{"items": [1, 2, 3]}')

        result = run_python_script(
            f'''
import json
with open("{json_file}") as f:
    data = json.load(f)
print(len(data["items"]))
''',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "3" in result.output

    def test_blocked_import_fails(self, temp_workspace):
        """Should fail when using blocked imports."""
        result = run_python_script(
            "import requests",
            workspace=temp_workspace,
        )
        assert result.success is False
        assert "Blocked import" in result.error

    def test_timeout_enforcement(self, temp_workspace):
        """Should timeout long-running scripts."""
        result = run_python_script(
            "import time; time.sleep(10)",
            workspace=temp_workspace,
            timeout=1,
        )
        assert result.success is False
        assert result.timed_out is True
        assert "timed out" in result.error.lower()

    def test_returns_stderr(self, temp_workspace):
        """Should capture stderr."""
        result = run_python_script(
            'import sys; sys.stderr.write("Error message")',
            workspace=temp_workspace,
        )
        # Script succeeds but has stderr
        assert result.success is True
        assert "Error message" in (result.error or "")

    def test_handles_exceptions(self, temp_workspace):
        """Should handle Python exceptions gracefully."""
        result = run_python_script(
            'raise ValueError("Test error")',
            workspace=temp_workspace,
        )
        assert result.success is False
        assert "ValueError" in result.error


class TestRunBashScript:
    """Tests for bash script execution."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "files").mkdir()
            yield workspace

    def test_simple_command(self, temp_workspace):
        """Should execute simple bash commands."""
        result = run_bash_script(
            'echo "Hello from bash"',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "Hello from bash" in result.output

    def test_pipeline(self, temp_workspace):
        """Should handle command pipelines."""
        result = run_bash_script(
            'echo "a\nb\nc" | wc -l',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "3" in result.output

    def test_file_operations(self, temp_workspace):
        """Should handle file operations."""
        test_file = temp_workspace / "files" / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        result = run_bash_script(
            f'cat "{test_file}" | grep line',
            workspace=temp_workspace,
        )
        assert result.success is True
        assert "line1" in result.output

    def test_blocks_sudo(self, temp_workspace):
        """Should block sudo commands."""
        result = run_bash_script(
            "sudo ls /",
            workspace=temp_workspace,
        )
        assert result.success is False
        assert "Blocked" in result.error

    def test_blocks_dangerous_rm(self, temp_workspace):
        """Should block dangerous rm commands."""
        result = run_bash_script(
            "rm -rf /",
            workspace=temp_workspace,
        )
        assert result.success is False
        assert "Blocked" in result.error

    def test_timeout_enforcement(self, temp_workspace):
        """Should timeout long-running commands."""
        result = run_bash_script(
            "sleep 10",
            workspace=temp_workspace,
            timeout=1,
        )
        assert result.success is False
        assert result.timed_out is True

    def test_returns_exit_code(self, temp_workspace):
        """Should return correct exit code."""
        result = run_bash_script(
            "exit 42",
            workspace=temp_workspace,
        )
        assert result.success is False
        assert result.return_code == 42


class TestScriptSecurityBypass:
    """Tests verifying security bypasses are blocked."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "files").mkdir()
            yield workspace

    def test_agent_respects_security(self, temp_workspace):
        """Agent should not be able to bypass security."""
        # Try various bypass attempts
        attempts = [
            "import subprocess; subprocess.run(['ls'])",
            "import os; os.system('ls')",
            "__import__('subprocess')",
            "eval('import subprocess')",
        ]

        for code in attempts:
            result = run_python_script(code, workspace=temp_workspace)
            assert result.success is False, f"Security bypass succeeded: {code}"
