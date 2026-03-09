import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from template_normalizer import analyze_template, main, normalize_template


class TestTemplateNormalizer(unittest.TestCase):
    def test_normalize_adds_sections(self):
        text = "Section 1\n\n{{input}}"
        report = analyze_template(text)
        normalized = normalize_template(text, report)
        self.assertIn("# TEMPLATE", normalized)
        self.assertIn("## Propósito", normalized)
        self.assertIn("## Documentação", normalized)

    def test_main_apply_outputs_normalized_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            template_path.write_text("Section 1", encoding="utf-8")
            stdout = io.StringIO()
            argv = ["template_normalizer.py", str(template_path), "--apply"]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("normalized_path", stdout.getvalue())

    def test_main_apply_with_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            output_path = Path(tmp) / "custom.md"
            template_path.write_text("Section 1", encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "template_normalizer.py",
                str(template_path),
                "--apply",
                "--output",
                str(output_path),
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())

    def test_main_report_output_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            report_path = Path(tmp) / "report.md"
            template_path.write_text("Section 1", encoding="utf-8")
            argv = [
                "template_normalizer.py",
                str(template_path),
                "--format",
                "markdown",
                "--report-output",
                str(report_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(report_path.exists())


if __name__ == "__main__":
    unittest.main()
