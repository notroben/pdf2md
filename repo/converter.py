"""High-performance PDF to Markdown converter engine.

Supports single-file generation, chapter-based multi-file splitting,
table & code block preservation, image extraction, and multi-core processing.
"""

from __future__ import annotations

import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pymupdf
import pymupdf4llm

from cleaner import clean_markdown_chunk
from toc_extractor import (
    TocNode,
    extract_toc,
    generate_single_file_toc,
    generate_summary_index,
    plan_chapter_files,
)


@dataclass
class ConversionStats:
    total_pages: int
    converted_pages: int
    duration_seconds: float
    output_files: list[str]
    word_count: int
    image_count: int
    mode: str


class PdfToMarkdownConverter:
    """Converts PDF documents to clean, well-structured GitHub-flavored Markdown."""

    def __init__(
        self,
        pdf_path: str | Path,
        output_dir: str | Path | None = None,
        mode: str = "both",  # "single", "split", "both"
        split_level: int = 1,  # 1 for top chapters, 2 for nested submodules
        extract_images: bool = False,
        image_dir_name: str = "assets",
        clean_ocr: bool = True,
        strip_headers: bool = True,
        enhance_code: bool = True,
        workers: int | None = None,
        chunk_size: int = 10,
    ):
        self.pdf_path = Path(pdf_path).resolve()
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        if output_dir is None:
            self.output_dir = self.pdf_path.parent / f"{self.pdf_path.stem}_markdown"
        else:
            self.output_dir = Path(output_dir).resolve()

        self.mode = mode.lower()
        if self.mode not in ("single", "split", "both"):
            raise ValueError(f"Invalid mode '{mode}'. Choose 'single', 'split', or 'both'.")

        self.split_level = split_level
        self.extract_images = extract_images
        self.image_dir_name = image_dir_name
        self.clean_ocr = clean_ocr
        self.strip_headers = strip_headers
        self.enhance_code = enhance_code
        self.chunk_size = chunk_size

        cpu_count = os.cpu_count() or 4
        self.workers = workers if workers and workers > 0 else min(8, cpu_count)

        self.doc_title = self.pdf_path.stem.replace("-", " ").replace("_", " ").title()

    def _convert_chunk(
        self,
        page_indices: list[int],
        image_output_path: Path | None,
        toc_titles: list[str],
    ) -> list[tuple[int, str]]:
        """Worker function to convert a small chunk of pages."""
        # Use relative image path if images are requested
        rel_img_path = self.image_dir_name if self.extract_images else ""

        try:
            # We open the document per thread/worker to prevent any file handle contention
            doc = pymupdf.open(str(self.pdf_path))
            chunks = pymupdf4llm.to_markdown(
                doc,
                pages=page_indices,
                write_images=self.extract_images,
                image_path=str(image_output_path) if (self.extract_images and image_output_path) else "",
                page_chunks=True,
                force_text=True,
            )
            doc.close()

            results = []
            for item in chunks:
                pno = item["metadata"]["page_number"] - 1  # 0-indexed
                raw_text = item.get("text", "")

                # Clean the page text
                cleaned = clean_markdown_chunk(
                    raw_text,
                    clean_ocr=self.clean_ocr,
                    strip_headers=self.strip_headers,
                    enhance_code=self.enhance_code,
                    toc_titles=toc_titles,
                )

                # Fix image links if images were extracted
                if self.extract_images and image_output_path:
                    # pymupdf4llm puts the full image_path in the markdown image tag ![](path/img.png)
                    # We normalize this to relative ![](assets/img.png)
                    clean_img_dir = self.image_dir_name.replace("\\", "/")
                    cleaned = re.sub(
                        r"!\[(.*?)\]\([^)]*?" + re.escape(clean_img_dir) + r"[/\\\\]([^)]+)\)",
                        rf"![\1]({clean_img_dir}/\2)",
                        cleaned,
                    )

                results.append((pno, cleaned))
            return results

        except Exception as e:
            print(f"Error converting pages {page_indices}: {e}", file=sys.stderr)
            # Fallback: attempt page-by-page extraction if batch fails
            fallback_results = []
            doc = pymupdf.open(str(self.pdf_path))
            for p in page_indices:
                try:
                    text = doc[p].get_text("text")
                    fallback_results.append((p, text))
                except Exception:
                    fallback_results.append((p, f"\n[Error extracting page {p + 1}]\n"))
            doc.close()
            return fallback_results

    def convert(
        self,
        pages: list[int] | range | None = None,
        progress_bar: Any | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> ConversionStats:
        """Run the full conversion pipeline."""
        start_time = time.time()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        image_output_dir = None
        if self.extract_images:
            image_output_dir = self.output_dir / self.image_dir_name
            image_output_dir.mkdir(parents=True, exist_ok=True)

        # Inspect document properties and outline
        doc = pymupdf.open(str(self.pdf_path))
        total_doc_pages = len(doc)
        doc_metadata = doc.metadata or {}
        if doc_metadata.get("title"):
            self.doc_title = doc_metadata["title"].strip()
        doc.close()

        # Determine target pages
        if pages is None:
            target_pages = list(range(total_doc_pages))
        else:
            target_pages = [p for p in pages if 0 <= p < total_doc_pages]

        if not target_pages:
            raise ValueError("No valid pages selected for conversion.")

        # Extract TOC
        toc_nodes = extract_toc(self.pdf_path)
        toc_titles = [n.title for n in toc_nodes]

        # Break into chunks for batch processing
        chunks = [
            target_pages[i : i + self.chunk_size]
            for i in range(0, len(target_pages), self.chunk_size)
        ]

        # Storage for converted page texts: map 0-indexed page number -> markdown text
        page_texts: dict[int, str] = {}
        completed_pages = 0

        # Run conversion across workers
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            future_to_chunk = {
                executor.submit(
                    self._convert_chunk,
                    chunk,
                    image_output_dir,
                    toc_titles,
                ): chunk
                for chunk in chunks
            }

            for future in as_completed(future_to_chunk):
                chunk_results = future.result()
                for pno, text in chunk_results:
                    page_texts[pno] = text

                completed_pages += len(chunk_results)
                if progress_bar:
                    progress_bar.update(len(chunk_results))
                if progress_callback:
                    progress_callback(completed_pages, len(target_pages), f"Converted {completed_pages}/{len(target_pages)} pages")

        # Gather created files
        created_files: list[str] = []

        # Generate Single Unified Markdown File if mode is "single" or "both"
        if self.mode in ("single", "both"):
            single_file_name = f"{self.pdf_path.stem}.md"
            single_file_path = self.output_dir / single_file_name

            single_content_parts = [
                f"# {self.doc_title}\n\n",
            ]

            # Add interactive TOC
            if toc_nodes:
                single_content_parts.append(generate_single_file_toc(toc_nodes, max_level=3))

            # Append pages in order
            for pno in sorted(target_pages):
                p_text = page_texts.get(pno, "").strip()
                if p_text:
                    single_content_parts.append(p_text + "\n\n---\n\n")

            single_file_path.write_text("".join(single_content_parts), encoding="utf-8")
            created_files.append(str(single_file_path))

        # Generate Split Chapter Files if mode is "split" or "both"
        if self.mode in ("split", "both"):
            # If we didn't extract any TOC or target pages are a small subset, handle gracefully
            chapter_plans = plan_chapter_files(toc_nodes, split_level=self.split_level)

            if not chapter_plans:
                # If no TOC entries, create a fallback chapter
                chapter_plans = [{
                    "title": self.doc_title,
                    "rel_path": f"{self.pdf_path.stem}-content.md",
                    "start_page": target_pages[0],
                    "end_page": target_pages[-1],
                }]

            # Write each chapter file
            written_chapters = []
            for plan in chapter_plans:
                start_p = plan["start_page"]
                end_p = plan["end_page"]

                # Collect pages for this chapter that were actually converted
                chapter_pages = [p for p in target_pages if start_p <= p <= end_p]
                if not chapter_pages:
                    continue

                chapter_text_parts = [f"# {plan['title']}\n\n"]
                for pno in chapter_pages:
                    p_text = page_texts.get(pno, "").strip()
                    if p_text:
                        chapter_text_parts.append(p_text + "\n\n")

                content = "".join(chapter_text_parts)

                # If chapter file is inside a subfolder, adjust asset links from ![](assets/...) to ![](../assets/...)
                rel_path = plan["rel_path"]
                if "/" in rel_path:
                    content = content.replace(f"![]({self.image_dir_name}/", f"![](../{self.image_dir_name}/")
                    content = content.replace(f"![screenshot]({self.image_dir_name}/", f"![screenshot](../{self.image_dir_name}/")

                out_file_path = self.output_dir / rel_path
                out_file_path.parent.mkdir(parents=True, exist_ok=True)
                out_file_path.write_text(content, encoding="utf-8")
                created_files.append(str(out_file_path))
                written_chapters.append(plan)

            # Write SUMMARY.md / README.md navigation index
            if written_chapters:
                summary_content = generate_summary_index(self.doc_title, written_chapters)
                summary_path = self.output_dir / "SUMMARY.md"
                summary_path.write_text(summary_content, encoding="utf-8")
                created_files.append(str(summary_path))

                readme_path = self.output_dir / "README.md"
                readme_path.write_text(summary_content, encoding="utf-8")
                created_files.append(str(readme_path))

        # Count extracted images
        image_count = 0
        if self.extract_images and image_output_dir and image_output_dir.exists():
            image_count = len(list(image_output_dir.glob("*.*")))

        # Calculate word count across all converted pages
        total_words = sum(len(text.split()) for text in page_texts.values())
        duration = time.time() - start_time

        return ConversionStats(
            total_pages=total_doc_pages,
            converted_pages=len(target_pages),
            duration_seconds=duration,
            output_files=created_files,
            word_count=total_words,
            image_count=image_count,
            mode=self.mode,
        )
