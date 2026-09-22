"""Text cleaning and normalization utilities for PDF-to-Markdown conversion.

Filters OCR artifacts, standalone page numbers, running headers, and enhances code block tags.
"""

from __future__ import annotations

import re


def clean_ocr_noise(text: str) -> str:
    """Remove messy OCR fallback comments produced when OCR is attempted on diagrams/screenshots."""
    # Pattern 1: HTML comments produced by pymupdf4llm
    # <!-- Start of picture text --> ... <!-- End of picture text -->
    text = re.sub(
        r"<!--\s*Start of picture text\s*-->[\s\S]*?<!--\s*End of picture text\s*-->\s*",
        "",
        text,
        flags=re.MULTILINE,
    )
    # Pattern 2: Text dashes fallback
    # ----- Start of picture text ----- ... ----- End of picture text -----
    text = re.sub(
        r"-----\s*Start of picture text\s*-----[\s\S]*?-----\s*End of picture text\s*-----\s*",
        "",
        text,
        flags=re.MULTILINE,
    )
    return text


def clean_page_headers_footers(text: str, toc_titles: list[str] | None = None) -> str:
    """Remove standalone page numbers and repetitive running headers at page boundaries.

    In Typst documentation and books, running headers appear like '3.1 Syntax'
    and footers appear as standalone numbers like '40'.
    """
    # 1. Remove standalone page numbers on their own lines (e.g. \n\n40\n\n)
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$\n?", "", text)

    # 2. Remove known TOC title running headers that appear as solitary plain text lines
    if toc_titles:
        for title in toc_titles:
            escaped = re.escape(title.strip())
            if escaped:
                # Match title on its own line not preceded by '#' (so we don't remove markdown headers)
                text = re.sub(rf"(?m)^(?!#)\s*{escaped}\s*$\n?", "", text)

    # 3. Remove common running header pattern: e.g. "3.1 Syntax" or "2.1 Writing in Typst"
    # when appearing as a plain line without markdown heading markup
    text = re.sub(r"(?m)^(?!#)\s*\d+(\.\d+)*\s+[A-Z][A-Za-z\s]{2,40}\s*$\n?", "", text)

    return text


def enhance_typst_code_blocks(text: str) -> str:
    """Detect untagged code blocks containing Typst syntax and tag them as ```typst.

    Typst code commonly starts with #let, #show, #set, function calls, rules, or markup.
    """
    typst_indicators = [
        "#let",
        "#set",
        "#show",
        "#import",
        "#include",
        "#rect",
        "#circle",
        "#text",
        "#grid",
        "#align",
        "#context",
        "set page(",
        "set text(",
        "set par(",
        "set heading(",
        "show heading:",
        "show raw:",
        "show link:",
        "$",
        "->",
        "=>",
    ]

    def _tag_block(match: re.Match) -> str:
        lang = match.group(1).strip()
        body = match.group(2)
        if not lang:
            # Check if body contains Typst signatures
            if any(ind in body for ind in typst_indicators):
                return f"```typst\n{body}\n```"
            return f"```text\n{body}\n```"
        return match.group(0)

    # Match code fences: ```<optional_lang>\n<body>\n```
    text = re.sub(r"```([a-zA-Z0-9_-]*)\n([\s\S]*?)\n```", _tag_block, text)
    return text


def normalize_markdown(text: str) -> str:
    """Normalize whitespace, excessive newlines, and trailing spaces."""
    # Collapse 3+ newlines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.splitlines()]
    text = "\n".join(lines)
    return text.strip() + "\n"


def clean_markdown_chunk(
    text: str,
    clean_ocr: bool = True,
    strip_headers: bool = True,
    enhance_code: bool = True,
    toc_titles: list[str] | None = None,
) -> str:
    """Full cleaning pipeline for a converted markdown chunk."""
    if clean_ocr:
        text = clean_ocr_noise(text)
    if strip_headers:
        text = clean_page_headers_footers(text, toc_titles=toc_titles)
    if enhance_code:
        text = enhance_typst_code_blocks(text)
    text = normalize_markdown(text)
    return text
