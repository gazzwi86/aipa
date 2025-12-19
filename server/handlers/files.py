"""File server for workspace files with visual UI."""

import mimetypes
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from server.config import Settings, get_settings
from server.handlers.auth import require_auth_redirect
from server.models.requests import FileInfo
from server.services.auth import get_auth_service

router = APIRouter()
templates = Jinja2Templates(directory="server/templates")


def validate_path_within(target: Path, root: Path) -> Path:
    """Validate and resolve a path, ensuring it stays within the root directory.

    Args:
        target: The target path to validate
        root: The root directory that target must be within

    Returns:
        The resolved target path

    Raises:
        HTTPException: 400 for invalid paths, 403 for access denied
    """
    try:
        resolved_target = target.resolve()
        resolved_root = root.resolve()
        if not str(resolved_target).startswith(str(resolved_root)):
            raise HTTPException(status_code=403, detail="Access denied")
        return resolved_target
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None


def get_files_path(settings: Settings = Depends(get_settings)) -> Path:
    """Get the files directory path."""
    return Path(settings.workspace_path) / "files"


def get_file_icon(name: str, is_dir: bool) -> str:
    """Get an appropriate icon for a file type."""
    if is_dir:
        return "folder"

    ext = Path(name).suffix.lower()
    icon_map = {
        # Documents
        ".pdf": "picture_as_pdf",
        ".doc": "description",
        ".docx": "description",
        ".txt": "article",
        ".md": "article",
        ".rtf": "description",
        # Spreadsheets
        ".xls": "table_chart",
        ".xlsx": "table_chart",
        ".csv": "table_chart",
        # Presentations
        ".ppt": "slideshow",
        ".pptx": "slideshow",
        # Images
        ".jpg": "image",
        ".jpeg": "image",
        ".png": "image",
        ".gif": "image",
        ".svg": "image",
        ".webp": "image",
        ".ico": "image",
        # Videos
        ".mp4": "movie",
        ".mov": "movie",
        ".avi": "movie",
        ".mkv": "movie",
        ".webm": "movie",
        # Audio
        ".mp3": "audio_file",
        ".wav": "audio_file",
        ".ogg": "audio_file",
        ".m4a": "audio_file",
        ".flac": "audio_file",
        # Code
        ".py": "code",
        ".js": "code",
        ".ts": "code",
        ".html": "code",
        ".css": "code",
        ".json": "data_object",
        ".xml": "code",
        ".yaml": "data_object",
        ".yml": "data_object",
        # Archives
        ".zip": "folder_zip",
        ".tar": "folder_zip",
        ".gz": "folder_zip",
        ".rar": "folder_zip",
        ".7z": "folder_zip",
        # Data
        ".sql": "storage",
        ".db": "storage",
        ".sqlite": "storage",
    }
    return icon_map.get(ext, "draft")


def format_size(size: int) -> str:
    """Format file size in human-readable format."""
    if size == 0:
        return "-"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024:
            if unit == "B":
                return f"{size} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"


def format_time(dt: datetime) -> str:
    """Format datetime in human-readable format."""
    now = datetime.now()
    diff = now - dt

    if diff.days == 0:
        if diff.seconds < 60:
            return "Just now"
        elif diff.seconds < 3600:
            mins = diff.seconds // 60
            return f"{mins}m ago"
        else:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
    elif diff.days == 1:
        return "Yesterday"
    elif diff.days < 7:
        return f"{diff.days} days ago"
    else:
        return dt.strftime("%b %d, %Y")


def get_file_description(name: str, is_dir: bool, size: int) -> str:
    """Get a contextual description for a file."""
    if is_dir:
        return "Folder"

    ext = Path(name).suffix.lower()
    desc_map = {
        ".pdf": "PDF Document",
        ".doc": "Word Document",
        ".docx": "Word Document",
        ".txt": "Text File",
        ".md": "Markdown",
        ".rtf": "Rich Text",
        ".xls": "Excel Spreadsheet",
        ".xlsx": "Excel Spreadsheet",
        ".csv": "CSV Data",
        ".ppt": "Presentation",
        ".pptx": "Presentation",
        ".jpg": "JPEG Image",
        ".jpeg": "JPEG Image",
        ".png": "PNG Image",
        ".gif": "GIF Image",
        ".svg": "SVG Vector",
        ".webp": "WebP Image",
        ".mp4": "MP4 Video",
        ".mov": "QuickTime Video",
        ".avi": "AVI Video",
        ".mp3": "MP3 Audio",
        ".wav": "WAV Audio",
        ".py": "Python Script",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".html": "HTML Document",
        ".css": "Stylesheet",
        ".json": "JSON Data",
        ".yaml": "YAML Config",
        ".yml": "YAML Config",
        ".zip": "ZIP Archive",
        ".tar": "TAR Archive",
        ".gz": "Compressed File",
    }
    return desc_map.get(ext, "File")


@router.get("/files-page")
async def files_page(
    request: Request,
    path: str = "",
    session_id: str = "",
    settings: Settings = Depends(get_settings),
    _auth: bool = Depends(require_auth_redirect),
):
    """Visual file browser page."""
    # Get sessions for filter dropdown (if session service is available)
    sessions = []
    try:
        from server.services.sessions import get_session_service

        session_service = get_session_service()
        sessions_result = await session_service.list_sessions(limit=50)
        sessions = sessions_result[0]  # First element is the list
    except Exception:
        pass  # Sessions not available

    return templates.TemplateResponse(
        "files.html",
        {
            "request": request,
            "agent_name": settings.agent_name,
            "sessions": sessions,
            "session_id": session_id,
        },
    )


# Legacy inline HTML removed - now using templates/files.html


@router.get("/files")
async def list_files(
    path: str = "",
    settings: Settings = Depends(get_settings),
) -> list[FileInfo]:
    """List files in the workspace files directory."""
    files_root = get_files_path(settings)
    target_path = files_root / path

    # Security: ensure we stay within files directory
    try:
        target_path = target_path.resolve()
        files_root = files_root.resolve()
        if not str(target_path).startswith(str(files_root)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None

    if not target_path.exists():
        # Create files directory if it doesn't exist
        if target_path == files_root:
            target_path.mkdir(parents=True, exist_ok=True)
        else:
            raise HTTPException(status_code=404, detail="Path not found")

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="Path is not a directory")

    files = []
    for item in sorted(target_path.iterdir()):
        try:
            stat = item.stat()
            rel_path = str(item.relative_to(files_root))
            files.append(
                FileInfo(
                    name=item.name,
                    path=rel_path,
                    size=stat.st_size if item.is_file() else 0,
                    modified=datetime.fromtimestamp(stat.st_mtime),
                    is_dir=item.is_dir(),
                )
            )
        except Exception:
            continue

    return files


@router.get("/files/{file_path:path}")
async def download_file(
    file_path: str,
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    """Download a file from the workspace."""
    files_root = get_files_path(settings)
    target_path = files_root / file_path

    # Security: ensure we stay within files directory
    try:
        target_path = target_path.resolve()
        files_root = files_root.resolve()
        if not str(target_path).startswith(str(files_root)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if target_path.is_dir():
        raise HTTPException(status_code=400, detail="Cannot download directory")

    # Determine content type
    content_type, _ = mimetypes.guess_type(str(target_path))
    if content_type is None:
        content_type = "application/octet-stream"

    return FileResponse(
        path=target_path,
        filename=target_path.name,
        media_type=content_type,
    )


@router.post("/files/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    path: str = "",
    settings: Settings = Depends(get_settings),
) -> dict:
    """Upload a file to the workspace."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")

    if not token or not auth.verify_session(token):
        raise HTTPException(status_code=401, detail="Not authenticated")

    files_root = get_files_path(settings).resolve()
    target_dir = (files_root / path).resolve()

    # Security: ensure we stay within files directory
    try:
        if not str(target_dir).startswith(str(files_root)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None

    # Create directory if needed
    target_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    target_path = target_dir / file.filename

    # Prevent overwriting existing files without explicit handling
    if target_path.exists():
        # Add counter to filename
        base = target_path.stem
        ext = target_path.suffix
        counter = 1
        while target_path.exists():
            target_path = target_dir / f"{base}_{counter}{ext}"
            counter += 1

    try:
        content = await file.read()
        target_path.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}") from e

    return {
        "success": True,
        "filename": target_path.name,
        "path": str(target_path.relative_to(files_root)),
        "size": len(content),
    }


@router.post("/files/folder")
async def create_folder(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Create a new folder in the workspace."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")

    if not token or not auth.verify_session(token):
        raise HTTPException(status_code=401, detail="Not authenticated")

    body = await request.json()
    name = body.get("name", "").strip()
    path = body.get("path", "")

    if not name:
        raise HTTPException(status_code=400, detail="Folder name required")

    # Validate folder name
    if "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="Invalid folder name")

    files_root = get_files_path(settings).resolve()
    target_dir = (files_root / path / name).resolve()

    # Security: ensure we stay within files directory
    try:
        if not str(target_dir).startswith(str(files_root)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None

    if target_dir.exists():
        raise HTTPException(status_code=400, detail="Folder already exists")

    try:
        target_dir.mkdir(parents=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create folder: {e}") from e

    return {
        "success": True,
        "name": name,
        "path": str(target_dir.relative_to(files_root)),
    }


@router.delete("/files/{file_path:path}")
async def delete_file(
    request: Request,
    file_path: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """Delete a file or empty folder from the workspace."""
    auth = get_auth_service()
    token = request.cookies.get("aipa_session")

    if not token or not auth.verify_session(token):
        raise HTTPException(status_code=401, detail="Not authenticated")

    files_root = get_files_path(settings).resolve()
    target_path = (files_root / file_path).resolve()

    # Security: ensure we stay within files directory
    try:
        if not str(target_path).startswith(str(files_root)):
            raise HTTPException(status_code=403, detail="Access denied")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid path") from None

    if not target_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    try:
        if target_path.is_dir():
            # Only delete empty directories for safety
            if any(target_path.iterdir()):
                raise HTTPException(status_code=400, detail="Directory not empty")
            target_path.rmdir()
        else:
            target_path.unlink()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}") from e

    return {"success": True, "path": file_path}
