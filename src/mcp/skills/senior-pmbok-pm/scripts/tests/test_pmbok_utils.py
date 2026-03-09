import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tempfile

from pmbok_utils import (
    extract_placeholders,
    normalize_text,
    parse_markdown_table,
    placeholder_keys,
    render_output,
    to_json,
    to_pdf_bytes,
    to_markdown,
    write_output,
)


class TestPmbokUtils(unittest.TestCase):
    def test_extract_and_keys(self):
        text = "Hello {{test_value}} and {{other}}"
        placeholders = extract_placeholders(text)
        self.assertEqual(sorted(placeholders), ["{{other}}", "{{test_value}}"])
        self.assertEqual(placeholder_keys(placeholders), ["other", "test_value"])

    def test_normalize_text(self):
        self.assertEqual(normalize_text("  Árvore "), "arvore")

    def test_parse_markdown_table(self):
        lines = [
            "| Col1 | Col2 |",
            "|---|---|",
            "| A | B |",
        ]
        rows = parse_markdown_table(lines)
        self.assertEqual(rows, [{"Col1": "A", "Col2": "B"}])

    def test_parse_markdown_table_edge_cases(self):
        self.assertEqual(parse_markdown_table([]), [])
        lines = [
            "| Col1 | Col2 |",
            "|---|---|",
            "not-a-row | still-has-pipe",
            "| only-one |",
        ]
        rows = parse_markdown_table(lines)
        self.assertEqual(rows, [])

    def test_to_json(self):
        payload = {"b": 2, "a": 1}
        compact = to_json(payload, pretty=False)
        self.assertIn("\"a\"", compact)
        pretty = to_json(payload, pretty=True)
        self.assertIn("\n", pretty)

    def test_render_output_formats(self):
        data = {"key": "value", "list": ["a", "b"]}
        markdown, _, is_binary = render_output(data, "markdown")
        self.assertIn("# Report", markdown)
        self.assertFalse(is_binary)
        mermaid, _, _ = render_output(data, "mermaid")
        self.assertIn("graph TD", mermaid)
        plantuml, _, _ = render_output(data, "plantuml")
        # Accept both @startuml and @startjson (both valid PlantUML formats)
        self.assertTrue(plantuml.startswith("@startuml") or plantuml.startswith("@startjson"),
                        f"PlantUML should start with @startuml or @startjson, got: {plantuml[:20]}")
        html, _, _ = render_output(data, "html")
        self.assertIn("<html>", html)
        txt, _, _ = render_output(data, "txt")
        self.assertIn("\"key\"", txt)

    def test_markdown_nested_and_scalar(self):
        nested = to_markdown([{"a": 1}])
        self.assertIn("**a**", nested)
        scalar = to_markdown("value")
        self.assertIn("value", scalar)

    def test_render_output_pdf(self):
        data = {"key": "value"}
        _, pdf_bytes, is_binary = render_output(data, "pdf")
        self.assertTrue(is_binary)
        self.assertTrue(len(pdf_bytes) > 0)

    def test_pdf_page_break(self):
        long_text = "\n".join(["line" for _ in range(70)])
        pdf_bytes = to_pdf_bytes(long_text)
        self.assertTrue(len(pdf_bytes) > 0)

    def test_render_output_unsupported(self):
        with self.assertRaises(ValueError):
            render_output({"a": 1}, "unsupported")

    def test_write_output_to_file(self):
        data = {"key": "value"}
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "report.md"
            write_output(data, "markdown", output_path)
            self.assertTrue(output_path.exists())

    def test_write_output_binary_stdout(self):
        class DummyStdout:
            def __init__(self) -> None:
                from io import BytesIO

                self.buffer = BytesIO()

        dummy = DummyStdout()
        original_stdout = sys.stdout
        try:
            sys.stdout = dummy  # type: ignore[assignment]
            write_output({"key": "value"}, "pdf", None)
            self.assertTrue(len(dummy.buffer.getvalue()) > 0)
        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    unittest.main()
