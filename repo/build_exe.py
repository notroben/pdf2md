"""Automated build script for compiling pdf2md into a standalone Windows executable.

Uses PyInstaller with comprehensive data/binary collection for PyMuPDF, PyMuPDF4LLM,
ONNX runtime, Rich, and project modules.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def build():
    print("==================================================")
    print("       Building Standalone Executable (pdf2md.exe)")
    print("==================================================")

    project_dir = Path(__file__).parent.resolve()
    dist_dir = project_dir / "dist"
    build_dir = project_dir / "build"

    # PyInstaller arguments
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=pdf2md",
        "--onefile",
        "--console",
        "--clean",
        "--noconfirm",
        # Explicit module imports
        "--hidden-import=cleaner",
        "--hidden-import=converter",
        "--hidden-import=toc_extractor",
        "--hidden-import=ui",
        "--hidden-import=rich",
        "--hidden-import=tabulate",
        "--hidden-import=tqdm",
        # Package data and binary collection
        "--collect-all=pymupdf",
        "--collect-all=pymupdf4llm",
        "--collect-all=rich",
        # Main entry script
        str(project_dir / "main.py"),
    ]

    print("\nRunning PyInstaller command:")
    print(" ".join(cmd))
    print("\nCompiling... (this may take 1-2 minutes)\n")

    result = subprocess.run(cmd, cwd=str(project_dir))

    if result.returncode != 0:
        print(f"\n[ERROR] Build failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    exe_path = dist_dir / "pdf2md.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 50)
        print("              BUILD SUCCESSFUL!")
        print("=" * 50)
        print(f"  Binary Name: {exe_path.name}")
        print(f"  File Size  : {size_mb:.2f} MB")
        print(f"  Location   : {exe_path}")
        print("=" * 50 + "\n")
    else:
        print(f"\n[ERROR] Executable not found at {exe_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    build()
