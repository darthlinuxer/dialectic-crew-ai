import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quality_audit import audit_quality, main


class TestQualityAudit(unittest.TestCase):
    def test_audit_detects_checks(self):
        text = "Versão 1.0\nResponsável: PMO\nReferência: R1\n{{placeholder}}"
        report = audit_quality(text)
        self.assertTrue(report["checks"]["has_version_control"])
        self.assertTrue(report["checks"]["has_ownership"])
        self.assertTrue(report["checks"]["has_traceability"])
        self.assertTrue(report["checks"]["has_placeholders"])

    def test_main_returns_zero_when_no_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "artifact.md"
            artifact_path.write_text("Versão 1.0\nResponsável: PMO\nReferência: R1", encoding="utf-8")
            stdout = io.StringIO()
            argv = ["quality_audit.py", str(artifact_path)]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("score", stdout.getvalue())

    def test_main_returns_two_when_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "artifact.md"
            artifact_path.write_text("Versão 1.0\n{{placeholder}}", encoding="utf-8")
            stdout = io.StringIO()
            argv = ["quality_audit.py", str(artifact_path), "--pretty"]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 2)

    def test_main_output_file_plantuml(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "artifact.md"
            output_path = Path(tmp) / "report.puml"
            artifact_path.write_text("Versão 1.0", encoding="utf-8")
            argv = [
                "quality_audit.py",
                str(artifact_path),
                "--format",
                "plantuml",
                "--output",
                str(output_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
