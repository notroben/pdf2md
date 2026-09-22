#!/usr/bin/env python3
"""CLI & Interactive Runner for PDF-to-Markdown Converter.

Converts large and complex PDFs (like Typst documentation) into clean,
structured Markdown with support for single-file or multi-chapter split.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from converter import PdfToMarkdownConverter
import ui


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse a page range string like '1-20', '10,15,20-25', or 'all' into 0-indexed page ints."""
    spec = spec.strip().lower()
    if spec in ("all", "*", ""):
        return list(range(total_pages))

    pages = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            parts = part.split("-", 1)
            start = max(1, int(parts[0].strip()))
            end = min(total_pages, int(parts[1].strip()))
            for p in range(start, end + 1):
                pages.add(p - 1)
        else:
            p = int(part)
            if 1 <= p <= total_pages:
                pages.add(p - 1)
    return sorted(pages)


def main():
    parser = argparse.ArgumentParser(
        prog="pdf2md",
        description="High-Performance PDF to Markdown Converter with TOC and Code Block Preservation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pdf2md typst-documentation.pdf
  pdf2md typst-documentation.pdf --mode both --extract-images
  pdf2md typst-documentation.pdf --mode single --pages 1-50
  pdf2md typst-documentation.pdf --mode split --split-level 2 -o docs/
  pdf2md --interactive
        """,
    )

    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=None,
        help="Path to the PDF document to convert.",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory path (defaults to <pdf_stem>_markdown).",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["single", "split", "both"],
        default="both",
        help="Output structure: 'single' (.md file), 'split' (chapter files), or 'both' (default: both).",
    )
    parser.add_argument(
        "--split-level",
        type=int,
        choices=[1, 2],
        default=1,
        help="Depth for splitting chapters: 1 = top chapters, 2 = nested submodules (default: 1).",
    )
    parser.add_argument(
        "--extract-images",
        action="store_true",
        default=False,
        help="Extract diagrams and screenshots into an assets folder and link them in markdown.",
    )
    parser.add_argument(
        "--no-images",
        action="store_false",
        dest="extract_images",
        help="Disable image extraction for pure text conversion (default).",
    )
    parser.add_argument(
        "-p", "--pages",
        default="all",
        help="Page range to convert: e.g. '1-30', '10,15,20-25', or 'all' (default: all).",
    )
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=None,
        help="Number of concurrent worker threads (defaults to optimal system thread pool).",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        default=False,
        help="Disable automatic cleaning of OCR artifacts, page numbers, and running headers.",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        default=False,
        help="Force interactive setup wizard.",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    args = parser.parse_args()
    is_interactive = args.interactive or (args.pdf_path is None and len(sys.argv) <= 1)

    try:
        # Determine execution parameters
        if is_interactive:
            params = ui.interactive_wizard()
        else:
            if args.pdf_path is None:
                default_candidate = Path("typst-documentation.pdf")
                if default_candidate.exists():
                    pdf_path = default_candidate
                elif Path("../typst-documentation.pdf").exists():
                    pdf_path = Path("../typst-documentation.pdf")
                else:
                    pdfs = list(Path(".").glob("*.pdf")) or list(Path("..").glob("*.pdf"))
                    if pdfs:
                        pdf_path = pdfs[0]
                    else:
                        ui.print_banner()
                        ui.err_console.print("[bold red]Error:[/bold red] No PDF file specified and none found.")
                        parser.print_help()
                        if is_interactive:
                            try:
                                input("\nPress Enter to exit...")
                            except (EOFError, KeyboardInterrupt):
                                pass
                        sys.exit(1)
            else:
                pdf_path = Path(args.pdf_path)

            if not pdf_path.exists():
                ui.err_console.print(f"[bold red]Error:[/bold red] File '{pdf_path}' not found.")
                if is_interactive:
                    try:
                        input("\nPress Enter to exit...")
                    except (EOFError, KeyboardInterrupt):
                        pass
                sys.exit(1)

            import pymupdf
            doc = pymupdf.open(str(pdf_path))
            total_doc_pages = len(doc)
            doc.close()

            target_pages = parse_page_range(args.pages, total_doc_pages)
            output_dir = Path(args.output) if args.output else Path(f"{pdf_path.stem}_markdown")

            params = {
                "pdf_path": pdf_path,
                "output_dir": output_dir,
                "mode": args.mode,
                "split_level": args.split_level,
                "extract_images": args.extract_images,
                "pages": target_pages,
                "clean": not args.no_clean,
                "workers": args.workers,
            }

            ui.print_banner()

        # Initialize converter
        converter = PdfToMarkdownConverter(
            pdf_path=params["pdf_path"],
            output_dir=params["output_dir"],
            mode=params["mode"],
            split_level=params["split_level"],
            extract_images=params["extract_images"],
            clean_ocr=params["clean"],
            strip_headers=params["clean"],
            enhance_code=params["clean"],
            workers=params["workers"],
        )

        import pymupdf
        doc = pymupdf.open(str(converter.pdf_path))
        total_doc_pages = len(doc)
        doc.close()

        # Display pre-conversion job panel
        ui.render_job_panel(
            pdf_path=converter.pdf_path,
            total_pages=total_doc_pages,
            target_count=len(params["pages"]),
            mode=converter.mode,
            split_level=converter.split_level,
            extract_images=converter.extract_images,
            workers=converter.workers,
            output_dir=converter.output_dir,
        )

        # Progress bar setup
        with ui.create_progress_bar() as progress:
            task_id = progress.add_task(
                "Converting pages...",
                total=len(params["pages"]),
            )

            class ProgressAdapter:
                def update(self, n: int):
                    progress.update(task_id, advance=n)

            adapter = ProgressAdapter()
            stats = converter.convert(pages=params["pages"], progress_bar=adapter)

        # Display completion report
        ui.render_completion_panel(stats, converter.output_dir)

        if is_interactive:
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass

    except KeyboardInterrupt:
        ui.console.print("\n[bold yellow]Conversion cancelled by user.[/bold yellow]")
        if is_interactive:
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
        sys.exit(130)
    except Exception as e:
        ui.err_console.print(f"\n[bold red]Fatal error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        if is_interactive:
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()
