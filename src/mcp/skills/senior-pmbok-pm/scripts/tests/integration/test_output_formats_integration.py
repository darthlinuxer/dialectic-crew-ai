import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pmbok_utils import write_output

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples"


class TestOutputFormatsIntegration(unittest.TestCase):
    def test_generate_markdown_mermaid_plantuml_html_txt(self):
        data = {"title": "Report", "items": ["a", "b"]}
        md_path = EXAMPLES_DIR / "report.md"
        mmd_path = EXAMPLES_DIR / "report.mmd"
        puml_path = EXAMPLES_DIR / "report.puml"
        html_path = EXAMPLES_DIR / "report.html"
        txt_path = EXAMPLES_DIR / "report.txt"

        write_output(data, "markdown", md_path)
        write_output(data, "mermaid", mmd_path)
        write_output(data, "plantuml", puml_path)
        write_output(data, "html", html_path)
        write_output(data, "txt", txt_path)

        self.assertTrue(md_path.exists())
        self.assertTrue(mmd_path.exists())
        self.assertTrue(puml_path.exists())
        self.assertTrue(html_path.exists())
        self.assertTrue(txt_path.exists())

        self.assertTrue(md_path.read_text(encoding="utf-8").startswith("# Report"))
        self.assertTrue(mmd_path.read_text(encoding="utf-8").startswith("graph TD"))
        # Accept both @startuml and @startjson (both valid PlantUML formats)
        puml_content = puml_path.read_text(encoding="utf-8")
        self.assertTrue(puml_content.startswith("@startuml") or puml_content.startswith("@startjson"),
                        f"PlantUML should start with @startuml or @startjson, got: {puml_content[:20]}")
        self.assertIn("<html>", html_path.read_text(encoding="utf-8"))
        self.assertIn("\"title\"", txt_path.read_text(encoding="utf-8"))

    def test_generate_pdf(self):
        data = {"title": "Report", "items": ["a", "b"]}
        pdf_path = EXAMPLES_DIR / "report.pdf"
        write_output(data, "pdf", pdf_path)
        self.assertTrue(pdf_path.exists())
        content = pdf_path.read_bytes()
        self.assertTrue(content.startswith(b"%PDF"))
        self.assertTrue(len(content) > 100)


if __name__ == "__main__":
    unittest.main()
