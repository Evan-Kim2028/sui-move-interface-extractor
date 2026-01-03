#!/usr/bin/env python3
"""
Convert Markdown benchmark reports to HTML for easy browser printing to PDF.
Requires 'markdown' package.
"""

import argparse
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Error: 'markdown' library not found. Install it with: pip install markdown")
    sys.exit(1)

CSS_STYLE = """
<style>
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        line-height: 1.6;
        color: #333;
        max-width: 900px;
        margin: 0 auto;
        padding: 2rem;
    }
    h1, h2, h3 { color: #111; margin-top: 2rem; }
    pre {
        background: #f4f4f4;
        padding: 1rem;
        border-radius: 4px;
        overflow-x: auto;
        border: 1px solid #ddd;
    }
    code { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 1.5rem 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px 12px;
        text-align: left;
    }
    th { background-color: #f8f8f8; }
    tr:nth-child(even) { background-color: #fafafa; }
    .footer {
        margin-top: 4rem;
        font-size: 0.8rem;
        color: #777;
        border-top: 1px solid #eee;
        padding-top: 1rem;
    }
</style>
"""

def convert_md_to_html(md_path: Path, html_path: Path, title: str = "Benchmark Report"):
    md_content = md_path.read_text(encoding="utf-8")
    
    # Convert MD to HTML with tables support
    html_body = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    {CSS_STYLE}
</head>
<body>
    {html_body}
    <div class="footer">
        Generated on {Path(md_path).name}
    </div>
</body>
</html>
"""
    html_path.write_text(full_html, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Convert Markdown to HTML")
    parser.add_argument("input", help="Path to input Markdown file")
    parser.add_argument("--output", "-o", help="Path to output HTML file (default: input.html)")
    parser.add_argument("--title", "-t", default="Benchmark Report", help="HTML document title")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
        
    output_path = Path(args.output) if args.output else input_path.with_suffix(".html")
    
    convert_md_to_html(input_path, output_path, args.title)
    print(f"Successfully converted {input_path} to {output_path}")

if __name__ == "__main__":
    main()
