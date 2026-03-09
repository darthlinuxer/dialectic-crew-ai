"""Generate workflow checklists from reference/workflows.md."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict

from pmbok_utils import read_text, write_output


CHECKLIST_PATTERN = re.compile(r"```\n(?P<title>[^\n]+Progress:[\s\S]+?)```", re.MULTILINE)


def extract_checklists(text: str) -> Dict[str, str]:
    results: Dict[str, str] = {}
    for match in CHECKLIST_PATTERN.finditer(text):
        block = match.group("title").strip()
        title_line = block.splitlines()[0]
        key = title_line.replace(" Progress:", "").strip().lower()
        results[key] = block
    return results


def get_fallback_checklist(command: str) -> str:
    """Return a default checklist when workflows.md is not available."""
    fallback_checklists = {
        "create": """Create Progress:
- [ ] Confirm artifact(s) to create
- [ ] Read TEMPLATE.md, INPUTS.md, and DOCUMENTACAO
- [ ] Validate/normalize template format
- [ ] Map inputs from user context to placeholders
- [ ] Create artifact following TEMPLATE.md structure
- [ ] Run quality checks
- [ ] Review for completeness and accuracy""",
        "update": """Update Progress:
- [ ] Identify artifact(s) to update
- [ ] Read current artifact and TEMPLATE.md
- [ ] Identify required changes
- [ ] Update artifact maintaining structure
- [ ] Verify placeholder coverage
- [ ] Run quality checks
- [ ] Review changes for accuracy""",
        "review": """Review Progress:
- [ ] Read artifact(s) to review
- [ ] Check against TEMPLATE.md structure
- [ ] Verify all placeholders are filled
- [ ] Run quality audit checks
- [ ] Check terminology consistency
- [ ] Validate traceability and ownership
- [ ] Provide feedback and recommendations"""
    }
    return fallback_checklists.get(command, f"No checklist available for command: {command}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate workflow checklist for a command.")
    parser.add_argument("command", choices=["create", "update", "review"], help="Workflow command")
    parser.add_argument("--workflows", help="Path to workflows.md")
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
    workflows_path = Path(args.workflows) if args.workflows else base_dir / "reference" / "workflows.md"

    # Try to read workflows file, use fallback if not available
    checklists: Dict[str, str] = {}
    if workflows_path.exists():
        try:
            text = read_text(workflows_path)
            checklists = extract_checklists(text)
        except Exception:
            # If reading fails, use fallback
            pass

    # Get checklist from file or use fallback
    checklist = checklists.get(args.command)
    if not checklist:
        checklist = get_fallback_checklist(args.command)

    output_path = Path(args.output) if args.output else None
    write_output({"command": args.command, "checklist": checklist}, args.format, output_path, pretty=args.pretty)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
