"""Detect terminology drift across artifacts and documentation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from pmbok_utils import normalize_text, read_text, write_output

DEFAULT_TERM_GROUPS = [
    ["escopo", "scope"],
    ["beneficios", "benefícios", "benefits"],
    ["riscos", "risco", "risks"],
    ["stakeholders", "partes interessadas", "interessados"],
    ["cronograma", "schedule"],
]


def check_terms(text: str, term_groups: List[List[str]]) -> Dict[str, List[str]]:
    normalized = normalize_text(text)
    inconsistencies: Dict[str, List[str]] = {}
    for group in term_groups:
        found = [term for term in group if normalize_text(term) in normalized]
        if len(found) > 1:
            inconsistencies[" / ".join(group)] = found
    return inconsistencies


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check terminology consistency in files and directories.")
    parser.add_argument("paths", nargs="+", help="Files or directories to analyze (directories will be searched for *.md files)")
    parser.add_argument(
        "--format",
        default="json",
        help="Output format: json|markdown|md|mermaid|plantuml|pdf|txt|html",
    )
    parser.add_argument("--output", help="Write output to a file instead of stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON output")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # Collect all files to analyze (expand directories to *.md files)
    files_to_check: List[Path] = []
    for path_str in args.paths:
        path = Path(path_str)
        if path.is_dir():
            # Recursively find all markdown files in directory
            files_to_check.extend(path.glob("*.md"))
            files_to_check.extend(path.glob("**/*.md"))
        elif path.exists():
            files_to_check.append(path)
        # Skip non-existent paths gracefully

    report: Dict[str, object] = {"files": {}}
    for file_path in files_to_check:
        try:
            text = read_text(file_path)
            inconsistencies = check_terms(text, DEFAULT_TERM_GROUPS)
            report["files"][str(file_path)] = {
                "inconsistencies": inconsistencies,
                "has_inconsistencies": bool(inconsistencies),
            }
        except Exception:
            # Skip files that can't be read
            continue

    output_path = Path(args.output) if args.output else None
    write_output(report, args.format, output_path, pretty=args.pretty)
    if any(value["has_inconsistencies"] for value in report["files"].values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
