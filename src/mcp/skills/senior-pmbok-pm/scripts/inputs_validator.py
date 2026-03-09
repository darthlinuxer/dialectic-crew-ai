"""Validate placeholder coverage between TEMPLATE.md and INPUTS.md."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List, Set

from pmbok_utils import extract_placeholders, placeholder_keys, read_text, write_output


def parse_inputs_keys(text: str) -> Set[str]:
    lines = [line for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return set()
    header = [h.strip() for h in lines[0].strip("|").split("|")]
    if "Chave" not in header and "Key" not in header:
        return set()
    key_index = header.index("Chave") if "Chave" in header else header.index("Key")
    keys: Set[str] = set()
    for line in lines[2:]:
        if "---" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) <= key_index:
            continue
        key = re.sub(r"`", "", cells[key_index]).strip()
        if key:
            keys.add(key)
    return keys


def validate_placeholders(template_text: str, inputs_text: str) -> Dict[str, List[str]]:
    placeholders = placeholder_keys(extract_placeholders(template_text))
    input_keys = parse_inputs_keys(inputs_text)

    missing_inputs = sorted([ph for ph in placeholders if ph not in input_keys])
    unused_inputs = sorted([key for key in input_keys if key not in placeholders])

    return {
        "missing_inputs": missing_inputs,
        "unused_inputs": unused_inputs,
        "placeholder_count": len(placeholders),
        "inputs_count": len(input_keys),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate TEMPLATE.md placeholders vs INPUTS.md keys.")
    parser.add_argument("--template", required=True, help="Path to TEMPLATE.md")
    parser.add_argument("--inputs", required=True, help="Path to INPUTS.md")
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

    template_text = read_text(Path(args.template))
    inputs_text = read_text(Path(args.inputs))

    report = validate_placeholders(template_text, inputs_text)
    output_path = Path(args.output) if args.output else None
    write_output(report, args.format, output_path, pretty=args.pretty)

    if report["missing_inputs"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
