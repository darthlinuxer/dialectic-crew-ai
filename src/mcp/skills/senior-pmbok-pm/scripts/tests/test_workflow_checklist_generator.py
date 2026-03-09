import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workflow_checklist_generator import extract_checklists, main


class TestWorkflowChecklistGenerator(unittest.TestCase):
    def test_extract_checklists(self):
        text = """
```
Create Progress:
- [ ] Step 1
```
```
Update Progress:
- [ ] Step 2
```
"""
        checklists = extract_checklists(text)
        self.assertIn("create", checklists)
        self.assertIn("update", checklists)

    def test_main_returns_checklist_and_error(self):
        content = """
```
Create Progress:
- [ ] Step 1
```
"""
        with tempfile.TemporaryDirectory() as tmp:
            workflows_path = Path(tmp) / "workflows.md"
            workflows_path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "workflow_checklist_generator.py",
                "create",
                "--workflows",
                str(workflows_path),
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("Create Progress", stdout.getvalue())

            stdout = io.StringIO()
            argv = [
                "workflow_checklist_generator.py",
                "review",
                "--workflows",
                str(workflows_path),
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            # With fallback checklists, script now returns 0 and provides default checklist
            self.assertEqual(code, 0)
            output = stdout.getvalue()
            # Should contain fallback checklist content
            self.assertIn("review", output.lower())

    def test_main_default_workflows_path(self):
        stdout = io.StringIO()
        argv = ["workflow_checklist_generator.py", "create"]
        with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
            code = main()
        self.assertEqual(code, 0)

    def test_main_output_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "checklist.pdf"
            argv = [
                "workflow_checklist_generator.py",
                "create",
                "--format",
                "pdf",
                "--output",
                str(output_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
