"""Tests for report conversion utilities."""

import sys
from pathlib import Path

# Add repo root to sys.path so we can import scripts
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(REPO_ROOT))


def test_markdown_to_html_conversion(tmp_path: Path):
    from scripts.convert_report import convert_md_to_html

    md_file = tmp_path / "test.md"
    html_file = tmp_path / "test.html"

    md_content = """# Test Report
    
This is a **test** with a table.

| Key | Value |
|-----|-------|
| hit | 100%  |
"""
    md_file.write_text(md_content)

    convert_md_to_html(md_file, html_file, title="Unit Test Title")

    assert html_file.exists()
    content = html_file.read_text()

    assert "<title>Unit Test Title</title>" in content
    assert "<h1>Test Report</h1>" in content
    assert "<table>" in content
    assert "<strong>test</strong>" in content
