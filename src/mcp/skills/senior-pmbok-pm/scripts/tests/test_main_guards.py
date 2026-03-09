import runpy
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))


class TestMainGuards(unittest.TestCase):
    def test_artifact_mapper_main_guard(self):
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
            argv = ["artifact_mapper.py", "--list", "--index", str(index_path)]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    runpy.run_module("artifact_mapper", run_name="__main__")

    def test_inputs_validator_main_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            inputs_path = Path(tmp) / "INPUTS.md"
            template_path.write_text("Hello {{a}}", encoding="utf-8")
            inputs_path.write_text("| Chave | Desc |\n|---|---|\n| a | x |", encoding="utf-8")
            argv = [
                "inputs_validator.py",
                "--template",
                str(template_path),
                "--inputs",
                str(inputs_path),
            ]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    runpy.run_module("inputs_validator", run_name="__main__")

    def test_quality_audit_main_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact_path = Path(tmp) / "artifact.md"
            artifact_path.write_text("Versão 1.0", encoding="utf-8")
            argv = ["quality_audit.py", str(artifact_path)]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    runpy.run_module("quality_audit", run_name="__main__")

    def test_template_normalizer_main_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            template_path = Path(tmp) / "TEMPLATE.md"
            template_path.write_text("Section 1", encoding="utf-8")
            argv = ["template_normalizer.py", str(template_path)]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    runpy.run_module("template_normalizer", run_name="__main__")

    def test_terminology_consistency_main_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "file.md"
            file_path.write_text("escopo", encoding="utf-8")
            argv = ["terminology_consistency_checker.py", str(file_path)]
            with unittest.mock.patch("sys.argv", argv):
                with self.assertRaises(SystemExit):
                    runpy.run_module("terminology_consistency_checker", run_name="__main__")

    def test_workflow_checklist_main_guard(self):
        argv = ["workflow_checklist_generator.py", "create"]
        with unittest.mock.patch("sys.argv", argv):
            with self.assertRaises(SystemExit):
                runpy.run_module("workflow_checklist_generator", run_name="__main__")


if __name__ == "__main__":
    unittest.main()
