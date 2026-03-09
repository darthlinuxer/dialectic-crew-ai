"""Run quality checks against a PMBOK artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

from pmbok_utils import extract_placeholders, read_text, write_output


def audit_quality(text: str) -> Dict[str, object]:
    lower = text.lower()
    checks = {
        "has_version_control": any(token in lower for token in ["versão", "version", "histórico", "history"]),
        "has_ownership": any(token in lower for token in ["responsável", "owner", "aprovador", "approver"]),
        "has_traceability": any(token in lower for token in ["referência", "reference", "rastro", "trace"]),
        "has_placeholders": bool(extract_placeholders(text)),
    }
    score = sum(1 for key, value in checks.items() if key != "has_placeholders" and value)
    total = len(checks) - 1
    return {
        "checks": checks,
        "score": score,
        "total": total,
        "placeholders": extract_placeholders(text),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit PMBOK artifact quality.")
    parser.add_argument("artifact", help="Path to the artifact file to audit")
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

    artifact_text = read_text(Path(args.artifact))
    report = audit_quality(artifact_text)
    output_path = Path(args.output) if args.output else None
    write_output(report, args.format, output_path, pretty=args.pretty)

    if report["placeholders"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
