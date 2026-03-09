import io
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from artifact_mapper import load_artifacts, main, resolve_artifact


class TestArtifactMapper(unittest.TestCase):
    def test_resolve_artifact_by_alias(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter, initiation |
"""
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            artifacts = load_artifacts(index_path)
            base_dir = Path(tmp)
            resolved = resolve_artifact("charter", "PT-BR", artifacts, base_dir)
            self.assertIsNotNone(resolved)
            self.assertIn("PM_DOCS_PT_BR", resolved["folder"])

    def test_load_artifacts_skips_short_rows(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) |
"""
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            artifacts = load_artifacts(index_path)
            self.assertEqual(artifacts, [])

    def test_resolve_artifact_en_fallback(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter |
"""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            (base_dir / "assets" / "PM_DOCS_PT_BR" / "01_TERMO").mkdir(parents=True)
            index_path = base_dir / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            artifacts = load_artifacts(index_path)
            resolved = resolve_artifact("Project Charter", "EN", artifacts, base_dir)
            self.assertIsNotNone(resolved)
            self.assertIn("PM_DOCS_PT_BR", resolved["folder"])  # fallback path

    def test_main_list_and_not_found(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter |
"""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            index_path = base_dir / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            argv = ["artifact_mapper.py", "--list", "--index", str(index_path)]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("PM_DOCS_PT_BR/01_TERMO", stdout.getvalue())

            stdout = io.StringIO()
            argv = ["artifact_mapper.py", "--artifact", "unknown", "--index", str(index_path)]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 2)
            self.assertIn("Artifact not found", stdout.getvalue())

    def test_main_missing_artifact_arg_raises(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter |
"""
        with tempfile.TemporaryDirectory() as tmp:
            index_path = Path(tmp) / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            argv = ["artifact_mapper.py", "--index", str(index_path)]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    main()

    def test_main_resolved_artifact_pretty(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter |
"""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            (base_dir / "assets" / "PM_DOCS_PT_BR" / "01_TERMO").mkdir(parents=True)
            index_path = base_dir / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            stdout = io.StringIO()
            argv = [
                "artifact_mapper.py",
                "--artifact",
                "charter",
                "--pretty",
                "--index",
                str(index_path),
            ]
            with unittest.mock.patch("sys.argv", argv), unittest.mock.patch("sys.stdout", stdout):
                code = main()
            self.assertEqual(code, 0)
            self.assertIn("\n", stdout.getvalue())

    def test_main_output_file_markdown(self):
        content = """
| Folder (PT-BR) | Artifact (PT/EN) | Template | Inputs | Documentation | Common aliases / triggers |
|---|---|---|---|---|---|
| `PM_DOCS_PT_BR/01_TERMO` | Termo de Abertura / Project Charter | [TEMPLATE](x) | [INPUTS](y) | [DOC](z) | charter |
"""
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            (base_dir / "assets" / "PM_DOCS_PT_BR" / "01_TERMO").mkdir(parents=True)
            index_path = base_dir / "artifact-index.md"
            index_path.write_text(content, encoding="utf-8")
            output_path = base_dir / "report.md"
            argv = [
                "artifact_mapper.py",
                "--artifact",
                "charter",
                "--format",
                "markdown",
                "--output",
                str(output_path),
                "--index",
                str(index_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                code = main()
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
