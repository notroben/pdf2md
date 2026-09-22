"""Rich Terminal UI module for PDF-to-Markdown converter.

Provides styled ASCII banners, interactive wizards, job configuration tables,
live progress indicators, and completion report panels.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich.text import Text

# Global console instances with UTF-8 support
console = Console(highlight=False)
err_console = Console(stderr=True, highlight=False)


def print_banner() -> None:
    """Print a modern, styled ASCII logo and subtitle."""
    banner_text = Text()
    banner_text.append(
        r"""
  ██████╗ ██████╗ ███████╗    ████████╗ ██████╗     ███╗   ███╗██████╗ 
  ██╔══██╗██╔══██╗██╔════╝    ╚══██╔══╝██╔═══██╗    ████╗ ████║██╔══██╗
  ██████╔╝██║  ██║█████╗         ██║   ██║   ██║    ██╔████╔██║██║  ██║
  ██╔═══╝ ██║  ██║██╔══╝         ██║   ██║   ██║    ██║╚██╔╝██║██║  ██║
  ██║     ██████╔╝██║            ██║   ╚██████╔╝    ██║ └──═╝██║██████╔╝
  ╚═╝     ╚═════╝ ╚═╝            ╚═╝    ╚═════╝     ╚═╝     ╚═╝╚═════╝ 
""",
        style="bold cyan",
    )
    banner_text.append(
        "\n      High-Performance PDF to Markdown Engine • Multi-Threaded • TOC Aware\n",
        style="italic bright_black",
    )

    panel = Panel(
        Align.center(banner_text),
        border_style="bright_blue",
        padding=(0, 1),
    )
    console.print(panel)


def render_job_panel(
    pdf_path: Path,
    total_pages: int,
    target_count: int,
    mode: str,
    split_level: int,
    extract_images: bool,
    workers: int,
    output_dir: Path,
) -> None:
    """Render a clean summary table of the planned conversion job."""
    file_size_mb = pdf_path.stat().st_size / (1024 * 1024)

    table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2))
    table.add_column("Property", style="bold white", width=18)
    table.add_column("Value", style="cyan")

    table.add_row("Source PDF", f"{pdf_path.name} [bright_black]({file_size_mb:.1f} MB)[/bright_black]")
    pages_desc = f"{target_count} pages" if target_count == total_pages else f"{target_count} of {total_pages} pages"
    table.add_row("Pages", f"[green]{pages_desc}[/green]")

    mode_label = {
        "both": "Both (Unified .md + Chapter files)",
        "single": "Single Unified Document (.md)",
        "split": f"Split Chapters (Level {split_level})",
    }.get(mode, mode.title())
    table.add_row("Output Mode", f"[bold yellow]{mode_label}[/bold yellow]")

    img_label = "[green]Enabled (Saved to assets/)[/green]" if extract_images else "[bright_black]Disabled (Pure text mode)[/bright_black]"
    table.add_row("Image Policy", img_label)
    table.add_row("Workers Pool", f"{workers} concurrent threads")
    table.add_row("Destination", f"[underline blue]{output_dir}[/underline blue]")

    panel = Panel(
        table,
        title="[bold bright_white]Conversion Job Configuration[/bold bright_white]",
        border_style="cyan",
        padding=(1, 2),
    )
    console.print(panel)
    console.print()


def create_progress_bar() -> Progress:
    """Create a customized, visually appealing Rich progress bar."""
    return Progress(
        SpinnerColumn("dots", style="bold cyan"),
        TextColumn("[bold bright_white]{task.description}[/bold bright_white]"),
        BarColumn(
            bar_width=32,
            style="bright_black",
            complete_style="bold green",
            finished_style="bold green",
        ),
        TaskProgressColumn("[bold green]{task.percentage:>3.0f}%[/bold green]"),
        TextColumn("•"),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def render_completion_panel(stats: Any, output_dir: Path) -> None:
    """Render a post-conversion report panel with metrics and generated files."""
    speed = stats.converted_pages / max(0.01, stats.duration_seconds)

    table = Table(box=None, show_header=False, pad_edge=False, padding=(0, 2))
    table.add_column("Metric", style="bold white", width=20)
    table.add_column("Value", style="bold green")

    table.add_row("Converted Pages", f"{stats.converted_pages} of {stats.total_pages}")
    table.add_row("Elapsed Time", f"{stats.duration_seconds:.2f} s [bright_black]({speed:.1f} pages/s)[/bright_black]")
    table.add_row("Estimated Words", f"{stats.word_count:,}")
    if stats.image_count > 0:
        table.add_row("Images Extracted", f"{stats.image_count} files [bright_black](in assets/)[/bright_black]")
    table.add_row("Output Directory", f"[underline cyan]{output_dir}[/underline cyan]")

    console.print()
    panel = Panel(
        table,
        title="[bold bright_green]Conversion Successful[/bold bright_green]",
        border_style="green",
        padding=(1, 2),
    )
    console.print(panel)

    # Generated files list
    if stats.output_files:
        files_table = Table(
            title="[bold white]Generated Artifacts[/bold white]",
            box=None,
            pad_edge=False,
            padding=(0, 1),
            show_header=True,
            header_style="bold cyan",
        )
        files_table.add_column("File Name", style="white")
        files_table.add_column("Size", style="bright_black")

        for f_path_str in stats.output_files[:18]:
            p = Path(f_path_str)
            if p.exists():
                sz_kb = p.stat().st_size / 1024
                size_str = f"{sz_kb:.1f} KB" if sz_kb < 1024 else f"{sz_kb/1024:.2f} MB"
            else:
                size_str = "-"
            try:
                rel = p.relative_to(output_dir)
            except ValueError:
                rel = p.name
            files_table.add_row(f"  - {rel}", size_str)

        if len(stats.output_files) > 18:
            files_table.add_row(f"  ... and {len(stats.output_files) - 18} more files", "")

        console.print(files_table)
        console.print()


def interactive_wizard() -> dict[str, Any]:
    """Run an interactive Rich wizard to gather conversion parameters."""
    print_banner()

    # Discover PDFs in current directory or parent directory
    pdf_files = list(Path(".").glob("*.pdf"))
    if not pdf_files and Path("..").exists():
        pdf_files = list(Path("..").glob("*.pdf"))

    if not pdf_files:
        console.print("[yellow]No PDF files found in the current folder.[/yellow]")
        while True:
            raw_path = Prompt.ask("   Enter or drag-and-drop a PDF file path").strip().strip("'\"")
            if not raw_path:
                continue
            p = Path(raw_path)
            if p.exists() and p.is_file() and p.suffix.lower() == ".pdf":
                pdf_files = [p]
                break
            console.print(f"   [bold red]File not found or not a PDF:[/bold red] {raw_path}")

    # Prioritize typst-documentation.pdf if found
    default_idx = 0
    for i, p in enumerate(pdf_files):
        if "typst" in p.name.lower():
            default_idx = i
            break

    console.print("[bold bright_white]1. Select PDF Document:[/bold bright_white]")
    for idx, p in enumerate(pdf_files):
        size_mb = p.stat().st_size / (1024 * 1024)
        marker = "[bold cyan]>[/bold cyan]" if idx == default_idx else " "
        console.print(f"   {marker} [bold white]{idx + 1}[/bold white]. {p.name} [bright_black]({size_mb:.1f} MB)[/bright_black]")

    choice_str = Prompt.ask(
        "   Enter choice",
        default=str(default_idx + 1),
        choices=[str(i + 1) for i in range(len(pdf_files))],
    )
    pdf_path = pdf_files[int(choice_str) - 1]

    # Inspect total pages
    import pymupdf
    doc = pymupdf.open(str(pdf_path))
    total_pages = len(doc)
    doc.close()

    console.print(f"\n[bold bright_white]2. Choose Output Format[/bold bright_white] [bright_black](Target: {pdf_path.name}, {total_pages} pages)[/bright_black]:")
    console.print("   [bold white]1[/bold white]. Both: Unified single file [cyan].md[/cyan] AND chapter-split files [green](Recommended)[/green]")
    console.print("   [bold white]2[/bold white]. Single file only: One unified [cyan].md[/cyan] file with interactive Table of Contents")
    console.print("   [bold white]3[/bold white]. Split chapters only: Partition into modular files + [cyan]SUMMARY.md[/cyan]")

    mode_choice = Prompt.ask("   Select format", default="1", choices=["1", "2", "3"])
    mode_map = {"1": "both", "2": "single", "3": "split"}
    mode = mode_map[mode_choice]

    split_level = 1
    if mode in ("split", "both"):
        console.print("\n[bold bright_white]3. Chapter Partitioning Depth:[/bold bright_white]")
        console.print("   [bold white]1[/bold white]. Top chapters [bright_black](Overview, Tutorial, Reference, Guides, Changelog)[/bright_black]")
        console.print("   [bold white]2[/bold white]. Deep split [bright_black](organizes Reference submodules into subfolders e.g. Syntax, Scripting)[/bright_black]")
        split_choice = Prompt.ask("   Select depth", default="1", choices=["1", "2"])
        split_level = int(split_choice)

    console.print("\n[bold bright_white]4. Image Extraction:[/bold bright_white]")
    console.print("   [bold white]1[/bold white]. Skip images [bright_black](Faster, compact text, ideal for LLMs / search)[/bright_black]")
    console.print("   [bold white]2[/bold white]. Extract images [bright_black](Save diagrams/screenshots to assets/ folder & link in markdown)[/bright_black]")
    img_choice = Prompt.ask("   Select option", default="1", choices=["1", "2"])
    extract_images = (img_choice == "2")

    console.print(f"\n[bold bright_white]5. Page Selection[/bold bright_white] [bright_black]({total_pages} total pages)[/bright_black]:")
    page_input = Prompt.ask(
        "   Enter range [bright_black](e.g. 1-50, 10,20, or press Enter for ALL)[/bright_black]",
        default="all",
    )

    from main import parse_page_range
    target_pages = parse_page_range(page_input, total_pages)

    default_out = f"{pdf_path.stem}_markdown"
    console.print(f"\n[bold bright_white]6. Destination Folder:[/bold bright_white]")
    out_dir_str = Prompt.ask("   Output folder", default=default_out)

    return {
        "pdf_path": pdf_path,
        "output_dir": Path(out_dir_str),
        "mode": mode,
        "split_level": split_level,
        "extract_images": extract_images,
        "pages": target_pages,
        "clean": True,
        "workers": None,
    }


def prompt_post_conversion() -> bool:
    """Prompt user after a conversion finishes: convert another or exit."""
    console.print()
    console.print("[bold bright_white]What would you like to do next?[/bold bright_white]")
    console.print("   [bold white]1[/bold white]. Convert another PDF (Back to start)")
    console.print("   [bold white]2[/bold white]. Exit")
    choice = Prompt.ask("   Select option", default="1", choices=["1", "2", "q", "exit"])
    if choice in ("2", "q", "exit"):
        console.print("\n[bold cyan]Goodbye![/bold cyan]\n")
        return False
    console.print("\n" + "=" * 60 + "\n")
    return True
