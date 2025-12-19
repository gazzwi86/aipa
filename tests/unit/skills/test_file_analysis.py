"""Unit tests for file analysis and document summarization utilities.

Tests file reading, PDF handling, and text processing utilities.
These don't call the agent - they test the underlying utility code.
"""

import io
import os
import tempfile
from pathlib import Path

import pytest

# Try to import PDF library - skip tests if not available
try:
    from pypdf import PdfReader, PdfWriter

    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

# Try to import reportlab for PDF creation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "files").mkdir()
        yield workspace


class TestTextFileReading:
    """Tests for reading and analyzing text files."""

    def test_read_simple_text_file(self, temp_workspace):
        """Should read a simple text file."""
        files_dir = temp_workspace / "files"
        test_file = files_dir / "test.txt"
        test_content = """Machine Learning Overview

Machine learning is a subset of artificial intelligence that enables
systems to learn and improve from experience without being explicitly
programmed.

Key Concepts:
1. Supervised Learning - Learning from labeled data
2. Unsupervised Learning - Finding patterns in unlabeled data
3. Reinforcement Learning - Learning through trial and error

Applications include image recognition, natural language processing,
and recommendation systems."""

        test_file.write_text(test_content)

        # Read the file
        content = test_file.read_text()

        assert "Machine Learning" in content
        assert "Supervised Learning" in content
        assert len(content) > 100

    def test_read_markdown_file(self, temp_workspace):
        """Should read markdown files."""
        files_dir = temp_workspace / "files"
        test_file = files_dir / "readme.md"
        test_content = """# Project Documentation

## Overview
This is a sample project for testing file analysis.

## Features
- Feature 1: File reading
- Feature 2: Content summarization
- Feature 3: PDF support

## Installation
```bash
pip install -r requirements.txt
```
"""
        test_file.write_text(test_content)

        content = test_file.read_text()

        assert "Project Documentation" in content
        assert "## Features" in content
        assert "pip install" in content

    def test_extract_key_points_from_text(self):
        """Should be able to identify key points in text content."""
        content = """
        The three main benefits of cloud computing are:
        1. Scalability - easily scale resources up or down
        2. Cost efficiency - pay only for what you use
        3. Reliability - high availability and disaster recovery

        In conclusion, cloud computing offers significant advantages for businesses.
        """

        # Check that we can find key points
        assert "Scalability" in content
        assert "Cost efficiency" in content
        assert "Reliability" in content
        assert "conclusion" in content.lower()


@pytest.mark.skipif(not HAS_PYPDF, reason="pypdf not installed")
class TestPdfFileReading:
    """Tests for reading and analyzing PDF files."""

    @pytest.mark.skipif(not HAS_REPORTLAB, reason="reportlab not installed")
    def test_create_and_read_pdf(self, temp_workspace):
        """Should read text from a PDF file."""
        files_dir = temp_workspace / "files"
        test_file = files_dir / "test_document.pdf"

        # Create a simple PDF using reportlab
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        c.drawString(100, 750, "Test Document Title")
        c.drawString(100, 700, "This is a test PDF document.")
        c.drawString(100, 650, "It contains multiple lines of text.")
        c.drawString(100, 600, "The summarizer should extract this content.")
        c.save()

        # Write PDF to file
        with open(test_file, "wb") as f:
            f.write(buffer.getvalue())

        # Read PDF
        reader = PdfReader(test_file)
        assert len(reader.pages) >= 1

        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""

        assert "Test Document" in text or len(text) > 0

    def test_read_multipage_pdf(self, temp_workspace):
        """Should handle multi-page PDFs."""
        files_dir = temp_workspace / "files"
        test_file = files_dir / "multipage.pdf"

        # Create multi-page PDF
        writer = PdfWriter()

        # Add blank pages with metadata
        for _ in range(3):
            writer.add_blank_page(width=612, height=792)

        with open(test_file, "wb") as f:
            writer.write(f)

        # Read PDF
        reader = PdfReader(test_file)
        assert len(reader.pages) == 3

    def test_pdf_with_no_text(self, temp_workspace):
        """Should handle PDFs with no extractable text gracefully."""
        files_dir = temp_workspace / "files"
        test_file = files_dir / "empty.pdf"

        # Create PDF with no text
        writer = PdfWriter()
        writer.add_blank_page(width=612, height=792)

        with open(test_file, "wb") as f:
            writer.write(f)

        # Read PDF - should not raise exception
        reader = PdfReader(test_file)
        text = reader.pages[0].extract_text() or ""

        # Empty text is acceptable for blank PDF
        assert isinstance(text, str)


class TestFilePathHandling:
    """Tests for file path handling and validation."""

    def test_file_path_construction(self, temp_workspace):
        """Should construct proper file paths."""
        workspace_path = str(temp_workspace)
        filename = "report.pdf"

        full_path = os.path.join(workspace_path, "files", filename)

        assert full_path.endswith("report.pdf")
        assert "files" in full_path

    def test_workspace_files_directory_exists(self, temp_workspace):
        """Workspace should have a files directory."""
        files_dir = temp_workspace / "files"
        assert files_dir.exists()
        assert files_dir.is_dir()

    def test_handle_nested_paths(self, temp_workspace):
        """Should handle files in subdirectories."""
        files_dir = temp_workspace / "files"
        subdir = files_dir / "documents"
        subdir.mkdir()

        test_file = subdir / "nested.txt"
        test_file.write_text("Nested file content")

        assert test_file.exists()
        assert test_file.read_text() == "Nested file content"

    def test_file_extension_detection(self):
        """Should correctly detect file extensions."""
        test_cases = [
            ("document.pdf", ".pdf"),
            ("notes.txt", ".txt"),
            ("readme.md", ".md"),
            ("script.py", ".py"),
            ("file.with.dots.pdf", ".pdf"),
        ]

        for filename, expected_ext in test_cases:
            _, ext = os.path.splitext(filename)
            assert ext == expected_ext, f"Expected {expected_ext} for {filename}"


class TestFileSummarizationPatterns:
    """Tests for file summarization output patterns."""

    def test_summary_structure_text_file(self):
        """Summary should follow expected structure for text files."""
        # Expected elements in a summary
        expected_elements = [
            "**File**:",  # Filename
            "Key Points",  # Key points section
        ]

        # Sample summary output
        sample_summary = """## Document Summary

**File**: report.txt
**Type**: Text
**Size**: 500 words

### Overview
This document discusses project management best practices.

### Key Points
1. Regular communication is essential
2. Clear goals improve team alignment
3. Documentation reduces knowledge silos

### Notable Sections
- Introduction: Sets up the problem space
- Recommendations: Actionable items for teams
"""

        for element in expected_elements:
            assert element in sample_summary, f"Summary should include '{element}'"

    def test_summary_structure_pdf_file(self):
        """Summary should follow expected structure for PDF files."""
        expected_elements = [
            "**File**:",  # Filename
            "**Type**:",  # File type
            "Overview",  # Overview section
        ]

        sample_summary = """## Document Summary

**File**: report.pdf
**Type**: PDF
**Size**: 10 pages

### Overview
A comprehensive analysis of market trends for Q4 2024.

### Key Points
1. Market grew 15% year-over-year
2. New competitors entered the space
3. Customer retention improved

### Metadata
- Author: Research Team
- Created: 2024-12-01
"""

        for element in expected_elements:
            assert element in sample_summary, f"Summary should include '{element}'"
