"""Resolve PMBOK artifacts to their template/input/documentation paths."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from pmbok_utils import normalize_text, read_text, write_output


def load_artifacts(index_path: Path) -> List[Dict[str, str]]:
    lines = read_text(index_path).splitlines()
    rows: List[Dict[str, str]] = []
    in_table = False
    for line in lines:
        if line.strip().startswith("|") and "Folder" in line:
            in_table = True
            continue
        if in_table and line.strip().startswith("|"):
            if "---" in line:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 6:
                continue
            row = {
                "folder_ptbr": cells[0].strip("`"),
                "artifact_names": cells[1],
                "template": cells[2],
                "inputs": cells[3],
                "documentation": cells[4],
                "aliases": cells[5],
            }
            rows.append(row)
    return rows


def _split_aliases(value: str) -> List[str]:
    aliases = [a.strip() for a in value.split(",")]
    return [a for a in aliases if a]


def _split_artifact_names(value: str) -> List[str]:
    return [part.strip() for part in value.split("/") if part.strip()]


def resolve_artifact(
    query: str,
    language: str,
    artifacts: List[Dict[str, str]],
    base_dir: Path,
) -> Optional[Dict[str, str]]:
    normalized_query = normalize_text(query)
    for row in artifacts:
        candidates = _split_artifact_names(row["artifact_names"]) + _split_aliases(row["aliases"])
        candidates.append(row["folder_ptbr"].split("/")[-1])
        if normalized_query in [normalize_text(c) for c in candidates]:
            folder_ptbr = row["folder_ptbr"].strip("`")
            target_folder = folder_ptbr.replace("PM_DOCS_PT_BR", "PM_DOC_EN")
            if language.upper() == "PT-BR":
                target_folder = folder_ptbr
            target_path = (base_dir / "assets" / target_folder).resolve()
            if not target_path.exists():
                target_path = (base_dir / "assets" / folder_ptbr).resolve()
            return {
                "artifact": row["artifact_names"],
                "folder": str(target_path),
                "template": str(target_path / "TEMPLATE.md"),
                "inputs": str(target_path / "INPUTS.md"),
                "documentation": str(target_path / "DOCUMENTACAO"),
            }
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve PMBOK artifact paths.")
    parser.add_argument("--artifact", help="Artifact name or alias to resolve")
    parser.add_argument("--language", default="PT-BR", help="PT-BR or EN")
    parser.add_argument("--index", help="Path to artifact-index.md")
    parser.add_argument("--list", action="store_true", help="List all artifacts")
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

    base_dir = Path(__file__).resolve().parents[1]
    index_path = Path(args.index) if args.index else base_dir / "reference" / "artifact-index.md"
    artifacts = load_artifacts(index_path)

    output_path = Path(args.output) if args.output else None

    if args.list:
        payload = [{"artifact": row["artifact_names"], "folder": row["folder_ptbr"]} for row in artifacts]
        write_output(payload, args.format, output_path, pretty=args.pretty)
        return 0

    if not args.artifact:
        parser.error("--artifact is required unless --list is used")

    resolved = resolve_artifact(args.artifact, args.language, artifacts, base_dir)
    if not resolved:
        write_output({"error": "Artifact not found", "query": args.artifact}, args.format, output_path, pretty=args.pretty)
        return 2

    write_output(resolved, args.format, output_path, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
