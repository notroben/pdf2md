<div align="center">

# PDF to Markdown Converter (pdf2md)

**A high-performance CLI tool engineered to convert large, complex technical PDFs into clean, beautifully structured Markdown.**

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-v1.0.0-brightgreen.svg)](https://github.com/)

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#interactive-mode">Interactive Mode</a> •
  <a href="#cli-usage--flags">CLI Flags</a> •
  <a href="#building-the-exe">Building from Source</a> •
  <a href="#github-release-guide">GitHub Release</a>
</p>

```
  ██████╗ ██████╗ ███████╗    ████████╗ ██████╗     ███╗   ███╗██████╗ 
  ██╔══██╗██╔══██╗██╔════╝    ╚══██╔══╝██╔═══██╗    ████╗ ████║██╔══██╗
  ██████╔╝██║  ██║█████╗         ██║   ██║   ██║    ██╔████╔██║██║  ██║
  ██╔═══╝ ██║  ██║██╔══╝         ██║   ██║   ██║    ██║╚██╔╝██║██║  ██║
  ██║     ██████╔╝██║            ██║   ╚██████╔╝    ██║ └──═╝██║██████╔╝
  ╚═╝     ╚═════╝ ╚═╝            ╚═╝    ╚═════╝     ╚═╝     ╚═╝╚═════╝ 
```

</div>

---

## Highlights

- **Blazing Fast**: Converts a **692-page PDF in ~2.5 minutes** (~4.4 pages/sec) via multi-threaded batching.
- **Rich Terminal UI**: Animated progress bars, colored status badges, pre-flight job tables, and completion reports.
- **Standalone Executable**: Pre-compiled `pdf2md.exe` available under **Releases** -- no Python or external dependencies required!
- **Dual Output Modes**:
  - **Single File (`--mode single`)**: Generates one unified `.md` file with a clickable Table of Contents (great for Ctrl+F and LLM context ingestion).
  - **Modular Chapters (`--mode split`)**: Automatically partitions chapters based on PDF bookmarks (`01-Overview.md`, `02-Tutorial.md`, `03-Reference.md`) and produces a `SUMMARY.md` navigation index (ready for Obsidian, GitBook, or VitePress).
  - **Both (`--mode both`)**: Produces both formats in a single pass without extra overhead!
- **Syntax & Code Preservation**: Identifies language syntax (Typst, Python, Math) and preserves indentation in code fences.
- **Intelligent Cleaners**: Automatically strips noisy fallback OCR comments (`<!-- Start of picture text -->`), running page headers, and stray page numbers.
- **Optional Image Extraction**: Extracts embedded diagrams, figures, and screenshots into an `assets/` directory with relative Markdown links.

---

## Quick Start

### Option A: Standalone Executable (No Python Required)

1. Download **`pdf2md.exe`** from the [GitHub Releases](https://github.com/) page.
2. Place it in any folder or add it to your system `PATH`.
3. Open PowerShell or Command Prompt:
   ```bash
   # Run the interactive wizard
   pdf2md.exe

   # Or convert directly
   pdf2md.exe my-document.pdf
   ```

---

### Option B: Run with Python

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-username/pdf-to-md.git
   cd pdf-to-md
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Convert a document**:
   ```bash
   python main.py typst-documentation.pdf
   ```

---

## Interactive Mode

If you run `pdf2md` without arguments, it launches a guided interactive wizard:

```
+---------------------- Conversion Job Configuration ----------------------+
|                                                                           |
|  Source PDF            typst-documentation.pdf (26.0 MB)                  |
|  Pages                 692 pages (all)                                    |
|  Output Mode           Both (Unified .md + Chapter files)                 |
|  Image Policy          Enabled (Saved to assets/)                         |
|  Workers Pool          8 concurrent threads                               |
|  Destination           ./typst_docs                                       |
|                                                                           |
+---------------------------------------------------------------------------+

  Converting pages... ------------------------- 100% * 692/692 * 0:02:38 * 0:00:00

+------------------------- Conversion Successful ---------------------------+
|                                                                           |
|  Converted Pages       692 of 692                                         |
|  Elapsed Time          158.69 s (4.4 pages/s)                             |
|  Estimated Words       221,296                                            |
|  Images Extracted      214 files (in assets/)                             |
|  Output Directory      ./typst_docs                                       |
|                                                                           |
+---------------------------------------------------------------------------+
```

---

## CLI Usage & Flags

```bash
pdf2md [pdf_path] [options]
```

| Flag | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `pdf_path` | | Path to the PDF file (interactive selection if omitted) | Auto-detect |
| `--output` | `-o` | Output directory path | `<pdf_stem>_markdown` |
| `--mode` | `-m` | Output structure: `both`, `single`, or `split` | `both` |
| `--split-level` | | Chapter depth: `1` (top chapters) or `2` (nested submodules) | `1` |
| `--extract-images` | | Extract diagrams/screenshots into `assets/` and link them | `False` |
| `--no-images` | | Text-only mode (skips image extraction for faster processing) | `True` |
| `--pages` | `-p` | Page range to convert: e.g. `1-50`, `10,15,20-30`, or `all` | `all` |
| `--workers` | `-w` | Number of parallel worker threads | CPU count (max 8) |
| `--no-clean` | | Disable automatic removal of OCR noise & running headers | `False` |
| `--interactive` | `-i` | Force interactive setup wizard | `False` |
| `--version` | `-v` | Show application version number | |

### Common Examples

1. **Convert specific pages for testing**:
   ```bash
   pdf2md document.pdf -p 1-30 -o test_output
   ```

2. **Generate deep submodules for Obsidian / GitBook**:
   ```bash
   pdf2md document.pdf --mode split --split-level 2 -o docs/
   ```

3. **Single pure-text file for LLM context windows (fastest)**:
   ```bash
   pdf2md document.pdf --mode single --no-images -o full_text.md
   ```

4. **Extract all figures and diagrams**:
   ```bash
   pdf2md document.pdf --mode both --extract-images -o output_docs/
   ```

---

## Building the Executable from Source

To compile your own standalone Windows `.exe`:

1. Ensure `pyinstaller` is installed:
   ```bash
   pip install pyinstaller
   ```

2. Run the automated build script:
   ```bash
   python build_exe.py
   ```

3. The compiled binary will be located at:
   ```
   dist/pdf2md.exe
   ```

---

## Publishing to GitHub Releases

When publishing on GitHub:

1. **Tag your release**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```
2. On GitHub, navigate to **Releases** -> **Draft a new release**.
3. Select the `v1.0.0` tag.
4. Set the Release title: `pdf2md v1.0.0 - High-Performance PDF to Markdown Converter`.
5. Attach the pre-compiled binary:
   - Drag and drop `dist/pdf2md.exe` into the **Attach binaries** section.
6. Publish the release! Users can now download `pdf2md.exe` directly and run it without installing Python.

---

## Repository Structure

```
pdf-to-md/
├── converter.py         # Multi-threaded batch conversion engine
├── cleaner.py           # Text post-processing & OCR noise filtering
├── toc_extractor.py     # Bookmark outline parser & chapter planner
├── ui.py                # Rich terminal UI (banners, wizard, progress)
├── main.py              # CLI entry point
├── build_exe.py         # Automated PyInstaller build script
├── dist/                # Output directory for compiled pdf2md.exe
├── requirements.txt     # Python dependencies
└── README.md            # Documentation
```

---

## License

This project is licensed under the [MIT License](LICENSE).
