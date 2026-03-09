import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from terminology_consistency_checker import DEFAULT_TERM_GROUPS, check_terms, main


class TestTerminologyConsistencyChecker(unittest.TestCase):
    def test_detects_inconsistency(self):
        text = "This scope is defined alongside escopo."
        inconsistencies = check_terms(text, DEFAULT_TERM_GROUPS)
        self.assertTrue(any(inconsistencies.values()))

    def test_main_inconsistency_and_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.md"
            good_path = Path(tmp) / "good.md"
            bad_path.write_text("scope e escopo", encoding="utf-8")
            good_path.write_text("escopo apenas", encoding="utf-8")

            stdout = io.StringIO()
            argv = ["terminology_consistency_checker.py", str(bad_path)]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 2)
            self.assertIn("inconsistencies", stdout.getvalue())

            stdout = io.StringIO()
            argv = ["terminology_consistency_checker.py", str(good_path)]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)

            stdout = io.StringIO()
            argv = ["terminology_consistency_checker.py", str(good_path), "--pretty"]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("\n", stdout.getvalue())

            output_path = Path(tmp) / "report.mmd"
            argv = [
                "terminology_consistency_checker.py",
                str(good_path),
                "--format",
                "mermaid",
                "--output",
                str(output_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
