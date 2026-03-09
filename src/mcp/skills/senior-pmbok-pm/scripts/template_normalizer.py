"""Validate and optionally normalize TEMPLATE.md files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

from pmbok_utils import extract_placeholders, read_text, write_output, write_text


def analyze_template(text: str) -> Dict[str, object]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    has_title = any(line.startswith("# ") for line in lines[:5])
    has_purpose = any("propósito" in line.lower() or "purpose" in line.lower() for line in lines[:20])
    has_doc_map = any("DOCUMENTACAO" in line or "DOCUMENTAÇÃO" in line for line in lines)
    has_numbered_sections = any(line[0].isdigit() and "." in line[:3] for line in lines)
    placeholders = extract_placeholders(text)
    return {
        "has_title": has_title,
        "has_purpose": has_purpose,
        "has_doc_map": has_doc_map,
        "has_numbered_sections": has_numbered_sections,
        "has_placeholders": bool(placeholders),
        "placeholders": placeholders,
    }


def normalize_template(text: str, report: Dict[str, object]) -> str:
    normalized = text
    insertions: List[str] = []
    if not report["has_title"]:
        insertions.append("# TEMPLATE\n")
    if not report["has_purpose"]:
        insertions.append("\n## Propósito\n\nTODO: descreva o propósito do documento.\n")
    if not report["has_doc_map"]:
        insertions.append("\n## Documentação\n\nConsulte `DOCUMENTACAO/` ou `DOCUMENTACAO.md` para orientação.\n")
    if insertions:
        normalized = "\n".join(insertions).rstrip() + "\n\n" + normalized.lstrip()
    return normalized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and normalize TEMPLATE.md files.")
    parser.add_argument("template", help="Path to TEMPLATE.md")
    parser.add_argument("--apply", action="store_true", help="Write a normalized copy")
    parser.add_argument("--output", help="Output path for normalized copy")
    parser.add_argument(
        "--format",
        default="json",
        help="Output format: json|markdown|md|mermaid|plantuml|pdf|txt|html",
    )
    parser.add_argument("--report-output", help="Write report to a file instead of stdout")
    parser.add_argument("--pretty", action="store_true", help="Pretty JSON report")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    template_path = Path(args.template)
    text = read_text(template_path)
    report = analyze_template(text)

    if args.apply:
        output_path = Path(args.output) if args.output else template_path.with_suffix(".normalized.md")
        normalized = normalize_template(text, report)
        write_text(output_path, normalized)
        report["normalized_path"] = str(output_path)

    report_output_path = Path(args.report_output) if args.report_output else None
    write_output(report, args.format, report_output_path, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
