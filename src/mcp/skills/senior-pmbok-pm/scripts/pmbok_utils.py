"""Shared utilities for PMBOK automation scripts."""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple


PLACEHOLDER_PATTERN = re.compile(r"\{\{[a-z0-9_]+\}\}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def normalize_text(value: str) -> str:
    """Lowercase and strip accents to improve matching."""
    value = value.strip().lower()
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def parse_markdown_table(lines: Sequence[str]) -> List[Dict[str, str]]:
    """Parse a simple markdown table into a list of dicts."""
    table_lines = [line for line in lines if "|" in line]
    if len(table_lines) < 2:
        return []
    headers = [h.strip() for h in table_lines[0].strip("|").split("|")]
    rows: List[Dict[str, str]] = []
    for line in table_lines[2:]:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))
    return rows


def extract_placeholders(text: str) -> List[str]:
    return sorted(set(PLACEHOLDER_PATTERN.findall(text)))


def placeholder_keys(placeholders: Iterable[str]) -> List[str]:
    return [ph.strip("{}").strip() for ph in placeholders]


def to_json(data: object, pretty: bool = True) -> str:
    if pretty:
        return json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)
    return json.dumps(data, ensure_ascii=False)


def _flatten_markdown(data: Any, indent: int = 0) -> List[str]:
    prefix = "  " * indent + "- "
    lines: List[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}**{key}**:")
                lines.extend(_flatten_markdown(value, indent + 1))
            else:
                lines.append(f"{prefix}**{key}**: {value}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_flatten_markdown(item, indent + 1))
            else:
                lines.append(f"{prefix}{item}")
    else:
        lines.append(f"{prefix}{data}")
    return lines


def to_markdown(data: Any) -> str:
    lines = ["# Report", ""]
    lines.extend(_flatten_markdown(data))
    return "\n".join(lines).strip() + "\n"


def _sanitize_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]", "_", value)


def _build_graph_edges(data: Any, parent_id: str, edges: List[Tuple[str, str]], nodes: Dict[str, str]) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            node_id = _sanitize_id(f"{parent_id}_{key}")
            nodes[node_id] = str(key)
            edges.append((parent_id, node_id))
            _build_graph_edges(value, node_id, edges, nodes)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            node_id = _sanitize_id(f"{parent_id}_item_{idx}")
            nodes[node_id] = f"item_{idx}"
            edges.append((parent_id, node_id))
            _build_graph_edges(item, node_id, edges, nodes)
    else:
        leaf_id = _sanitize_id(f"{parent_id}_value")
        nodes[leaf_id] = str(data)
        edges.append((parent_id, leaf_id))


def to_mermaid(data: Any) -> str:
    # Try enhanced PM-specific exporters first
    try:
        from pmbok_exporters import enhance_workflow_output, enhance_audit_output
        enhanced = enhance_workflow_output(data, 'mermaid')
        if enhanced:
            return enhanced
        enhanced = enhance_audit_output(data, 'mermaid')
        if enhanced:
            return enhanced
    except ImportError:
        pass  # pmbok_exporters not available, use fallback

    # Fallback: generic tree diagram
    nodes: Dict[str, str] = {"root": "Report"}
    edges: List[Tuple[str, str]] = []
    _build_graph_edges(data, "root", edges, nodes)
    lines = ["graph TD"]
    for node_id, label in nodes.items():
        safe_label = str(label).replace("\"", "'")
        lines.append(f"  {node_id}[\"{safe_label}\"]")
    for source, target in edges:
        lines.append(f"  {source} --> {target}")
    return "\n".join(lines).strip() + "\n"


def to_plantuml(data: Any) -> str:
    # Try enhanced PM-specific exporters first
    try:
        from pmbok_exporters import enhance_workflow_output, enhance_audit_output
        enhanced = enhance_workflow_output(data, 'plantuml')
        if enhanced:
            return enhanced
        enhanced = enhance_audit_output(data, 'plantuml')
        if enhanced:
            return enhanced
    except ImportError:
        pass  # pmbok_exporters not available, use fallback

    # Fallback: use PlantUML JSON diagram for hierarchical data
    lines = ["@startjson", to_json(data, pretty=True), "@endjson"]
    return "\n".join(lines).strip() + "\n"


def to_html(data: Any) -> str:
    markdown = to_markdown(data)
    return "\n".join([
        "<!doctype html>",
        "<html><head><meta charset=\"utf-8\"><title>Report</title></head><body>",
        "<pre>",
        markdown.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"),
        "</pre></body></html>",
    ])


def to_pdf_bytes(text: str) -> bytes:
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - dependency optional
        raise RuntimeError("reportlab is required for PDF output") from exc

    from io import BytesIO

    buffer = BytesIO()
    canvas_obj = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y_position = height - 50
    for line in text.splitlines():
        if y_position < 50:
            canvas_obj.showPage()
            y_position = height - 50
        canvas_obj.drawString(40, y_position, line[:200])
        y_position -= 14
    canvas_obj.save()
    return buffer.getvalue()


def render_output(data: Any, fmt: str, pretty: bool = True) -> Tuple[str, bytes, bool]:
    fmt_normalized = fmt.lower()
    if fmt_normalized in {"json"}:
        return to_json(data, pretty=pretty), b"", False
    if fmt_normalized in {"md", "markdown"}:
        return to_markdown(data), b"", False
    if fmt_normalized in {"mermaid", "mmd"}:
        return to_mermaid(data), b"", False
    if fmt_normalized in {"plantuml", "puml"}:
        return to_plantuml(data), b"", False
    if fmt_normalized in {"html"}:
        return to_html(data), b"", False
    if fmt_normalized in {"txt", "text"}:
        return to_json(data, pretty=pretty), b"", False
    if fmt_normalized in {"pdf"}:
        text = to_markdown(data)
        return "", to_pdf_bytes(text), True
    raise ValueError(f"Unsupported format: {fmt}")


def write_output(data: Any, fmt: str, output_path: Path | None, pretty: bool = True) -> None:
    text_output, binary_output, is_binary = render_output(data, fmt, pretty=pretty)
    if output_path:
        if is_binary:
            output_path.write_bytes(binary_output)
        else:
            output_path.write_text(text_output, encoding="utf-8")
        return
    if is_binary:
        sys.stdout.buffer.write(binary_output)
        return
    print(text_output)
