"""TOC (Table of Contents) extraction and chapter partitioning utilities.

Extracts PDF bookmarks/outline and organizes pages into structured chapters,
sections, and navigation files (SUMMARY.md / README.md).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pymupdf


@dataclass
class TocNode:
    level: int
    title: str
    page: int  # 1-based page number
    end_page: int = 0  # inclusive 1-based page number
    children: list[TocNode] = field(default_factory=list)
    filename: str = ""

    @property
    def page_span(self) -> int:
        return max(1, self.end_page - self.page + 1) if self.end_page >= self.page else 1


def sanitize_filename(name: str) -> str:
    """Convert chapter titles into filesystem-friendly file names."""
    # Replace spaces and punctuation
    cleaned = re.sub(r"[^\w\s\-.]", "", name)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-")
    return cleaned or "section"


def extract_toc(pdf_path: str | Path) -> list[TocNode]:
    """Extract outline/bookmarks from PDF and calculate page spans for each section."""
    doc = pymupdf.open(str(pdf_path))
    raw_toc = doc.get_toc()  # [[lvl, title, page], ...]
    total_pages = len(doc)
    doc.close()

    if not raw_toc:
        return []

    nodes: list[TocNode] = []
    stack: list[TocNode] = []

    for item in raw_toc:
        lvl, title, page = item[0], item[1].strip(), item[2]
        node = TocNode(level=lvl, title=title, page=max(1, page), end_page=total_pages)

        # Establish parent-child hierarchy
        while stack and stack[-1].level >= lvl:
            popped = stack.pop()
            # Set end_page of popped node based on the start page of current node
            popped.end_page = max(popped.page, page - 1)

        if stack:
            stack[-1].children.append(node)
        else:
            nodes.append(node)
        stack.append(node)

    # Any remaining nodes on stack end at the end of the document
    while stack:
        stack.pop()

    # Recalculate end_pages hierarchically
    _finalize_end_pages(nodes, total_pages)
    return nodes


def _finalize_end_pages(nodes: list[TocNode], total_pages: int):
    for i, node in enumerate(nodes):
        if i < len(nodes) - 1:
            node.end_page = max(node.page, nodes[i + 1].page - 1)
        else:
            node.end_page = total_pages
        if node.children:
            _finalize_end_pages(node.children, node.end_page)


def generate_single_file_toc(nodes: list[TocNode], max_level: int = 2) -> str:
    """Generate Markdown Table of Contents with internal anchor links."""
    lines = ["## Table of Contents\n"]

    def _render(node_list: list[TocNode]):
        for node in node_list:
            if node.level <= max_level:
                indent = "  " * (node.level - 1)
                # Create a markdown anchor from title
                anchor = re.sub(r"[^\w\s-]", "", node.title.lower())
                anchor = re.sub(r"[\s_]+", "-", anchor).strip("-")
                lines.append(f"{indent}- [{node.title}](#{anchor}) *(p. {node.page})*")
                if node.children:
                    _render(node.children)

    _render(nodes)
    lines.append("\n---\n")
    return "\n".join(lines)


def plan_chapter_files(nodes: list[TocNode], split_level: int = 1) -> list[dict[str, Any]]:
    """Determine output files and their corresponding 0-indexed page ranges.

    If split_level == 1:
      Splits top-level chapters (e.g. 01-Overview.md, 02-Tutorial.md, 03-Reference.md).
    If split_level >= 2:
      Allows large chapters (like 3 Reference) to be organized into subfolders with sub-files.
    """
    plans = []
    idx = 1

    for node in nodes:
        # Skip empty or tiny pre-content if it's just 'Contents'
        safe_title = sanitize_filename(node.title)
        filename = f"{idx:02d}-{safe_title}.md"
        node.filename = filename

        # Should we split into subfolder? (e.g., if split_level == 2 and node has children and spans > 50 pages)
        if split_level >= 2 and node.children and node.page_span > 40:
            folder_name = f"{idx:02d}-{safe_title}"
            sub_idx = 1
            for child in node.children:
                child_safe = sanitize_filename(child.title)
                child_file = f"{folder_name}/{sub_idx:02d}-{child_safe}.md"
                child.filename = child_file
                plans.append({
                    "title": f"{node.title} > {child.title}",
                    "rel_path": child_file,
                    "start_page": child.page - 1,  # 0-indexed
                    "end_page": child.end_page - 1,  # 0-indexed inclusive
                    "node": child,
                })
                sub_idx += 1
        else:
            plans.append({
                "title": node.title,
                "rel_path": filename,
                "start_page": node.page - 1,  # 0-indexed
                "end_page": node.end_page - 1,  # 0-indexed inclusive
                "node": node,
            })
        idx += 1

    return plans


def generate_summary_index(doc_title: str, plans: list[dict[str, Any]]) -> str:
    """Generate a SUMMARY.md / README.md index compatible with GitBook / mdBook / Obsidian."""
    lines = [
        f"# {doc_title}\n",
        "> Converted from PDF to Markdown with structured chapters and navigation.\n",
        "## Documentation Index\n",
    ]

    current_prefix = ""
    for item in plans:
        rel = item["rel_path"]
        title = item["title"]
        pages = f"(pp. {item['start_page'] + 1}-{item['end_page'] + 1})"

        # Check if item is in a subfolder
        if "/" in rel:
            folder, file = rel.split("/", 1)
            if folder != current_prefix:
                current_prefix = folder
                lines.append(f"\n### {folder.replace('-', ' ').title()}\n")
            lines.append(f"- [{title.split(' > ')[-1]}]({rel}) *{pages}*")
        else:
            lines.append(f"- [{title}]({rel}) *{pages}*")

    return "\n".join(lines) + "\n"
