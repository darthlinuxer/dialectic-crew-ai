import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inputs_validator import main, parse_inputs_keys, validate_placeholders


class TestInputsValidator(unittest.TestCase):
    def test_validate_placeholders(self):
        template = "Hello {{a}} and {{b}}"
        inputs = """
| Chave | Descrição |
|---|---|
| a | test |
| b | test |
| c | test |
"""
        report = validate_placeholders(template, inputs)
        self.assertEqual(report["missing_inputs"], [])
        self.assertEqual(report["unused_inputs"], ["c"])

    def test_parse_inputs_keys_missing_header(self):
        inputs = "| Something | else |\n|---|---|\n| a | b |"
        self.assertEqual(parse_inputs_keys(inputs), set())

    def test_parse_inputs_keys_key_header(self):
        inputs = """
| Key | Desc |
|---|---|
| alpha | x |
"""
        self.assertEqual(parse_inputs_keys(inputs), {"alpha"})

    def test_parse_inputs_keys_empty(self):
        inputs = "No table here"
        self.assertEqual(parse_inputs_keys(inputs), set())

    def test_parse_inputs_keys_short_row(self):
        inputs = """
| Desc | Chave | Extra |
|---|---|---|
| only-one |
"""
        self.assertEqual(parse_inputs_keys(inputs), set())

    def test_parse_inputs_keys_skips_divider_in_body(self):
        inputs = """
| Chave | Descrição |
|---|---|
|---|---|
| a | ok |
"""
        self.assertEqual(parse_inputs_keys(inputs), {"a"})

    def test_main_missing_inputs_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            inputs_path = Path(tmp) / "INPUTS.md"
            template_path.write_text("Hello {{a}} {{b}}", encoding="utf-8")
            inputs_path.write_text("| Chave | Desc |\n|---|---|\n| a | x |", encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "inputs_validator.py",
                "--template",
                str(template_path),
                "--inputs",
                str(inputs_path),
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 2)
            self.assertIn("missing_inputs", stdout.getvalue())

    def test_main_success_returns_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            inputs_path = Path(tmp) / "INPUTS.md"
            template_path.write_text("Hello {{a}}", encoding="utf-8")
            inputs_path.write_text("| Chave | Desc |\n|---|---|\n| a | x |", encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "inputs_validator.py",
                "--template",
                str(template_path),
                "--inputs",
                str(inputs_path),
                "--pretty",
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)

    def test_main_output_file_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            inputs_path = Path(tmp) / "INPUTS.md"
            output_path = Path(tmp) / "report.md"
            template_path.write_text("Hello {{a}}", encoding="utf-8")
            inputs_path.write_text("| Chave | Desc |\n|---|---|\n| a | x |", encoding="utf-8")
            argv = [
                "inputs_validator.py",
                "--template",
                str(template_path),
                "--inputs",
                str(inputs_path),
                "--format",
                "markdown",
                "--output",
                str(output_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
