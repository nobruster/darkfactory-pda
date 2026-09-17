#!/usr/bin/env python3
"""Render canonical Markdown Mermaid blocks for release-guide visual QA."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = [ROOT / "README.md", ROOT / "docs" / "architecture.md"]
BLOCK = re.compile(r"^```mermaid\s*$\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=pathlib.Path, default=ROOT / "tmp" / "pdfs" / "mermaid")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rendered = 0
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        for index, match in enumerate(BLOCK.finditer(text), 1):
            stem = source.stem.lower().replace(" ", "-")
            input_path = output / f"{stem}-{index}.mmd"
            output_path = output / f"{stem}-{index}.png"
            input_path.write_text(match.group(1).strip() + "\n", encoding="utf-8")
            command = [
                "npx",
                "--yes",
                "@mermaid-js/mermaid-cli@11.12.0",
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--backgroundColor",
                "transparent",
                "--scale",
                "2",
            ]
            subprocess.run(command, cwd=ROOT, check=True)
            if not output_path.is_file() or output_path.stat().st_size < 1_000:
                raise SystemExit(f"Mermaid render is missing or too small: {output_path}")
            rendered += 1
    print(f"MERMAID=READY diagrams={rendered} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
