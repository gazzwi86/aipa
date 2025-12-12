"""Unit tests for the files handler."""

import io
from pathlib import Path

from fastapi.testclient import TestClient


class TestListFiles:
    """Tests for the file listing endpoint."""

    def test_list_empty_directory(self, client: TestClient, temp_workspace: Path):
        """Test listing an empty directory."""
        response = client.get("/files")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_files_with_content(self, client: TestClient, temp_workspace: Path):
        """Test listing a directory with files."""
        # Create test files
        files_dir = temp_workspace / "files"
        (files_dir / "test.txt").write_text("hello")
        (files_dir / "test.pdf").write_text("pdf content")

        response = client.get("/files")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 2

        names = [f["name"] for f in data]
        assert "test.txt" in names
        assert "test.pdf" in names

    def test_list_subdirectory(self, client: TestClient, temp_workspace: Path):
        """Test listing a subdirectory."""
        # Create subdirectory with files
        files_dir = temp_workspace / "files"
        subdir = files_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").write_text("nested")

        response = client.get("/files?path=subdir")
        assert response.status_code == 200

        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "nested.txt"

    def test_list_nonexistent_path(self, client: TestClient):
        """Test listing a nonexistent path returns 404."""
        response = client.get("/files?path=nonexistent")
        assert response.status_code == 404

    def test_path_traversal_blocked(self, client: TestClient):
        """Test that path traversal is blocked."""
        response = client.get("/files?path=../etc")
        assert response.status_code in [400, 403]


class TestDownloadFile:
    """Tests for file download endpoint."""

    def test_download_file(self, client: TestClient, temp_workspace: Path):
        """Test downloading a file."""
        # Create test file
        files_dir = temp_workspace / "files"
        test_file = files_dir / "download.txt"
        test_file.write_text("download content")

        response = client.get("/files/download.txt")
        assert response.status_code == 200
        assert response.content == b"download content"

    def test_download_nonexistent_file(self, client: TestClient):
        """Test downloading a nonexistent file returns 404."""
        response = client.get("/files/nonexistent.txt")
        assert response.status_code == 404

    def test_download_directory_fails(self, client: TestClient, temp_workspace: Path):
        """Test that downloading a directory fails."""
        # Create directory
        files_dir = temp_workspace / "files"
        subdir = files_dir / "testdir"
        subdir.mkdir()

        response = client.get("/files/testdir")
        assert response.status_code == 400

    def test_download_path_traversal_blocked(self, client: TestClient):
        """Test that path traversal in download is blocked."""
        response = client.get("/files/../../../etc/passwd")
        # 404 is acceptable - file not found after path normalization
        assert response.status_code in [400, 403, 404]


class TestUploadFile:
    """Tests for file upload endpoint."""

    def test_upload_file_unauthenticated(self, client: TestClient):
        """Test that upload requires authentication."""
        files = {"file": ("test.txt", io.BytesIO(b"content"), "text/plain")}
        response = client.post("/files/upload", files=files)
        assert response.status_code == 401

    def test_upload_file_authenticated(
        self, authenticated_client: TestClient, temp_workspace: Path
    ):
        """Test uploading a file when authenticated."""
        files = {"file": ("uploaded.txt", io.BytesIO(b"uploaded content"), "text/plain")}
        response = authenticated_client.post("/files/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["filename"] == "uploaded.txt"

        # Verify file exists
        uploaded_file = temp_workspace / "files" / "uploaded.txt"
        assert uploaded_file.exists()
        assert uploaded_file.read_text() == "uploaded content"

    def test_upload_duplicate_file_renamed(
        self, authenticated_client: TestClient, temp_workspace: Path
    ):
        """Test that duplicate files are renamed."""
        files_dir = temp_workspace / "files"
        (files_dir / "duplicate.txt").write_text("original")

        files = {"file": ("duplicate.txt", io.BytesIO(b"new content"), "text/plain")}
        response = authenticated_client.post("/files/upload", files=files)

        assert response.status_code == 200
        data = response.json()
        # Should be renamed to duplicate_1.txt
        assert data["filename"] == "duplicate_1.txt"


class TestCreateFolder:
    """Tests for folder creation endpoint."""

    def test_create_folder_unauthenticated(self, client: TestClient):
        """Test that folder creation requires authentication."""
        response = client.post("/files/folder", json={"name": "newfolder"})
        assert response.status_code == 401

    def test_create_folder_authenticated(
        self, authenticated_client: TestClient, temp_workspace: Path
    ):
        """Test creating a folder when authenticated."""
        response = authenticated_client.post("/files/folder", json={"name": "newfolder"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["name"] == "newfolder"

        # Verify folder exists
        folder = temp_workspace / "files" / "newfolder"
        assert folder.exists()
        assert folder.is_dir()

    def test_create_nested_folder(self, authenticated_client: TestClient, temp_workspace: Path):
        """Test creating a folder in a subdirectory."""
        # Create parent folder first
        parent = temp_workspace / "files" / "parent"
        parent.mkdir()

        response = authenticated_client.post(
            "/files/folder", json={"name": "child", "path": "parent"}
        )

        assert response.status_code == 200
        assert (parent / "child").exists()

    def test_create_folder_invalid_name(self, authenticated_client: TestClient):
        """Test that invalid folder names are rejected."""
        # Name with path separator
        response = authenticated_client.post("/files/folder", json={"name": "bad/name"})
        assert response.status_code == 400

        # Name with path traversal
        response = authenticated_client.post("/files/folder", json={"name": ".."})
        assert response.status_code == 400

    def test_create_duplicate_folder(self, authenticated_client: TestClient, temp_workspace: Path):
        """Test that creating a duplicate folder fails."""
        # Create folder first
        (temp_workspace / "files" / "existing").mkdir()

        response = authenticated_client.post("/files/folder", json={"name": "existing"})
        assert response.status_code == 400


class TestDeleteFile:
    """Tests for file deletion endpoint."""

    def test_delete_file_unauthenticated(self, client: TestClient, temp_workspace: Path):
        """Test that deletion requires authentication."""
        # Create test file
        (temp_workspace / "files" / "todelete.txt").write_text("delete me")

        response = client.delete("/files/todelete.txt")
        assert response.status_code == 401

    def test_delete_file_authenticated(
        self, authenticated_client: TestClient, temp_workspace: Path
    ):
        """Test deleting a file when authenticated."""
        # Create test file
        test_file = temp_workspace / "files" / "todelete.txt"
        test_file.write_text("delete me")

        response = authenticated_client.delete("/files/todelete.txt")
        assert response.status_code == 200
        assert not test_file.exists()

    def test_delete_empty_folder(self, authenticated_client: TestClient, temp_workspace: Path):
        """Test deleting an empty folder."""
        # Create empty folder
        empty_folder = temp_workspace / "files" / "emptydir"
        empty_folder.mkdir()

        response = authenticated_client.delete("/files/emptydir")
        assert response.status_code == 200
        assert not empty_folder.exists()

    def test_delete_nonempty_folder_fails(
        self, authenticated_client: TestClient, temp_workspace: Path
    ):
        """Test that deleting a non-empty folder fails."""
        # Create folder with file
        folder = temp_workspace / "files" / "nonempty"
        folder.mkdir()
        (folder / "file.txt").write_text("content")

        response = authenticated_client.delete("/files/nonempty")
        assert response.status_code == 400

    def test_delete_nonexistent_file(self, authenticated_client: TestClient):
        """Test deleting a nonexistent file returns 404."""
        response = authenticated_client.delete("/files/nonexistent.txt")
        assert response.status_code == 404

    def test_delete_path_traversal_blocked(self, authenticated_client: TestClient):
        """Test that path traversal in delete is blocked."""
        response = authenticated_client.delete("/files/../../../etc/passwd")
        # 404 is acceptable - file not found after path normalization
        assert response.status_code in [400, 403, 404]


class TestFilesPage:
    """Tests for the files page UI endpoint."""

    def test_files_page_unauthenticated(self, client: TestClient):
        """Test that files page requires authentication."""
        response = client.get("/files-page", follow_redirects=False)
        assert response.status_code == 302
        assert "/login" in response.headers.get("location", "")

    def test_files_page_authenticated(self, authenticated_client: TestClient):
        """Test accessing files page when authenticated."""
        response = authenticated_client.get("/files-page")
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Files" in response.text
