#!/usr/bin/env python3
"""Generate LLM-friendly documentation formats from MkDocs build

This script extracts all markdown content from the MkDocs documentation
and generates three LLM-friendly formats:

1. llms.txt - Simple text format following llms.txt convention
2. llms.json - Structured JSON with metadata and content
3. llms-full.md - Single concatenated markdown file

These files are served via GitLab Pages for consumption by LLM agents.
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


# Custom YAML loader that skips Python-specific tags
class SkipPythonTagsLoader(yaml.SafeLoader):
    """YAML loader that ignores Python-specific tags like !!python/name"""

    pass


def skip_python_tag(loader, tag_suffix, node):
    """Skip Python-specific tags and return None"""
    return None


# Register custom constructor for Python tags
SkipPythonTagsLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/", skip_python_tag
)


class Page:
    """Represents a documentation page with content and metadata"""

    def __init__(self, title: str, path: str, source_file: str, content: str):
        self.title = title
        self.path = path
        self.source_file = source_file
        self.content = content
        self.word_count = len(content.split())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "title": self.title,
            "path": self.path,
            "url": f"https://huskycat-570fbd.gitlab.io{self.path}",
            "source_file": self.source_file,
            "content": self.content,
            "word_count": self.word_count,
        }


def get_git_commit_sha() -> str:
    """Get current git commit SHA (short form)"""
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def extract_metadata() -> dict[str, Any]:
    """Extract project metadata from mkdocs.yml and git"""
    # Use custom loader that skips Python-specific tags
    with open("mkdocs.yml") as f:
        mkdocs_config = yaml.load(f, Loader=SkipPythonTagsLoader)

    return {
        "project": mkdocs_config.get("site_name", "HuskyCat"),
        "tagline": mkdocs_config.get(
            "site_description", "Universal Code Validation Platform"
        ),
        "version": get_git_commit_sha(),
        "updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "source_repo": mkdocs_config.get("repo_url", ""),
        "docs_url": mkdocs_config.get("site_url", ""),
        "generator": "llms-txt-generator v1.0.0",
    }


def parse_navigation(mkdocs_config: dict) -> list[tuple[str, str]]:
    """Extract navigation structure from mkdocs.yml

    Returns list of (title, filepath) tuples in navigation order
    """
    nav = mkdocs_config.get("nav", [])
    pages = []

    def extract_pages(items, prefix=""):
        """Recursively extract pages from navigation structure"""
        for item in items:
            if isinstance(item, dict):
                for key, value in item.items():
                    if isinstance(value, str):
                        # Leaf node: title -> file
                        pages.append((key, value))
                    elif isinstance(value, list):
                        # Nested section - recurse
                        extract_pages(value, prefix=key)
            elif isinstance(item, str):
                # Direct file reference without title
                title = item.replace(".md", "").replace("-", " ").title()
                pages.append((title, item))

    extract_pages(nav)
    return pages


def read_markdown_file(filepath: str) -> str:
    """Read markdown file content from docs/ directory"""
    path = Path("docs") / filepath
    if not path.exists():
        print(f"  ⚠️  Warning: File not found: {path}")
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ⚠️  Error reading {path}: {e}")
        return ""


def parse_markdown_files(metadata: dict) -> list[Page]:
    """Parse all markdown files from navigation"""
    # Use custom loader that skips Python-specific tags
    with open("mkdocs.yml") as f:
        mkdocs_config = yaml.load(f, Loader=SkipPythonTagsLoader)

    nav_pages = parse_navigation(mkdocs_config)
    pages = []

    for title, source_file in nav_pages:
        content = read_markdown_file(source_file)
        if not content:
            continue

        # Convert file path to URL path
        # e.g., "installation.md" -> "/installation/"
        # e.g., "features/mcp-server.md" -> "/features/mcp-server/"
        path = "/" + source_file.replace(".md", "/")
        if path == "//":
            path = "/"
        if path.endswith("index/"):
            path = path.replace("index/", "")

        page = Page(
            title=title, path=path, source_file=f"docs/{source_file}", content=content
        )
        pages.append(page)

    return pages


def generate_llms_txt(metadata: dict, pages: list[Page]) -> str:
    """Generate llms.txt format following llms.txt convention

    Format:
    - Header with project info
    - Table of contents
    - Full content of each page with metadata
    - Page separators (---)
    """
    lines = [
        f"# {metadata['project']}",
        f"> {metadata['tagline']}",
        "",
        f"Last Updated: {metadata['updated']}",
        f"Version: {metadata['version']}",
        f"Source: {metadata['source_repo']}",
        f"Documentation: {metadata['docs_url']}",
        "",
        "## Table of Contents",
        "",
    ]

    # Add table of contents
    for i, page in enumerate(pages, 1):
        source = page.source_file.replace("docs/", "")
        lines.append(f"{i}. {page.title} ({source})")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Add each page with full content
    for page in pages:
        lines.extend(
            [
                f"### {page.title}",
                f"URL: {metadata['docs_url']}{page.path}",
                f"Path: {page.path}",
                f"Source: {page.source_file}",
                "",
                page.content,
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)


def generate_llms_json(metadata: dict, pages: list[Page]) -> dict:
    """Generate structured JSON format with full metadata and statistics"""
    return {
        "metadata": metadata,
        "pages": [page.to_dict() for page in pages],
        "stats": {
            "total_pages": len(pages),
            "total_words": sum(p.word_count for p in pages),
            "total_size_bytes": sum(len(p.content.encode()) for p in pages),
        },
    }


def generate_llms_full_md(metadata: dict, pages: list[Page]) -> str:
    """Generate single concatenated markdown file with TOC and anchors"""
    lines = [
        f"# {metadata['project']} Documentation",
        f"> {metadata['tagline']}",
        "",
        f"**Last Updated**: {metadata['updated']}",
        f"**Version**: {metadata['version']}",
        f"**Source**: {metadata['source_repo']}",
        "",
        "---",
        "",
        "# Table of Contents",
        "",
    ]

    # Add TOC with anchors
    for page in pages:
        # Create HTML-safe anchor ID
        anchor = (
            page.title.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace(":", "")
            .replace("(", "")
            .replace(")", "")
        )
        lines.append(f"- [{page.title}](#{anchor})")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Add each page with HTML anchor
    for page in pages:
        anchor = (
            page.title.lower()
            .replace(" ", "-")
            .replace("/", "-")
            .replace(":", "")
            .replace("(", "")
            .replace(")", "")
        )
        lines.extend(
            [
                f'<div id="{anchor}"></div>',
                "",
                page.content,
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)


def format_bytes(num_bytes: int) -> str:
    """Format bytes as human-readable string"""
    for unit in ["B", "KB", "MB", "GB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} TB"


def main():
    """Generate all LLM-friendly documentation formats"""
    print("")
    print("🚀 Generating LLM-friendly documentation formats...")
    print("")

    # Extract metadata
    print("1️⃣  Extracting metadata from mkdocs.yml and git...")
    metadata = extract_metadata()
    print(f"   Project: {metadata['project']}")
    print(f"   Version: {metadata['version']}")
    print(f"   Updated: {metadata['updated']}")

    # Parse markdown files
    print("")
    print("2️⃣  Parsing markdown files from docs/...")
    pages = parse_markdown_files(metadata)
    print(f"   ✓ Found {len(pages)} pages in navigation")
    total_words = sum(p.word_count for p in pages)
    print(f"   ✓ Total word count: {total_words:,}")

    # Ensure site/ directory exists
    Path("site").mkdir(exist_ok=True)

    # Generate llms.txt
    print("")
    print("3️⃣  Generating llms.txt...")
    llms_txt = generate_llms_txt(metadata, pages)
    llms_txt_path = Path("site/llms.txt")
    llms_txt_path.write_text(llms_txt, encoding="utf-8")
    size = llms_txt_path.stat().st_size
    print(f"   ✓ Written: site/llms.txt ({format_bytes(size)})")

    # Generate llms.json
    print("")
    print("4️⃣  Generating llms.json...")
    llms_json_data = generate_llms_json(metadata, pages)
    llms_json = json.dumps(llms_json_data, indent=2)
    llms_json_path = Path("site/llms.json")
    llms_json_path.write_text(llms_json, encoding="utf-8")
    size = llms_json_path.stat().st_size
    print(f"   ✓ Written: site/llms.json ({format_bytes(size)})")

    # Generate llms-full.md
    print("")
    print("5️⃣  Generating llms-full.md...")
    llms_full_md = generate_llms_full_md(metadata, pages)
    llms_full_md_path = Path("site/llms-full.md")
    llms_full_md_path.write_text(llms_full_md, encoding="utf-8")
    size = llms_full_md_path.stat().st_size
    print(f"   ✓ Written: site/llms-full.md ({format_bytes(size)})")

    print("")
    print("✅ LLM documentation generation complete!")
    print("")
    print("📄 Files generated:")
    print("   • site/llms.txt")
    print("   • site/llms.json")
    print("   • site/llms-full.md")
    print("")
    print("🌐 These files will be served at:")
    print(f"   • {metadata['docs_url']}/llms.txt")
    print(f"   • {metadata['docs_url']}/llms.json")
    print(f"   • {metadata['docs_url']}/llms-full.md")
    print("")


if __name__ == "__main__":
    main()
