"""
Advanced Integration Tests for Enhanced PMBOK PM Exports

Tests PM-specific diagram generation (workflows, audits) with real output validation.
No mocks - we test actual functionality and validate visual outputs.
"""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pmbok_utils import write_output
from pmbok_exporters import WorkflowExporter, AuditExporter

EXAMPLES_DIR = Path(__file__).resolve().parent / "examples" / "advanced"


class TestEnhancedExports(unittest.TestCase):
    """Integration tests for enhanced PM-specific exports"""

    @classmethod
    def setUpClass(cls):
        """Create output directory"""
        EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        print(f"\n📁 Advanced examples will be saved to: {EXAMPLES_DIR}")

    def test_01_workflow_plantuml_activity_diagram(self):
        """Test workflow checklist → PlantUML activity diagram"""
        print("\n🔄 Testing Workflow → PlantUML Activity Diagram...")

        workflow_data = {
            "command": "create",
            "checklist": """Create Progress:
- [ ] Confirm artifact(s)
- [ ] Read TEMPLATE.md, INPUTS.md, DOCUMENTACAO
- [ ] Validate/normalize template format
- [ ] Map inputs from user context to placeholders
- [ ] create|update|refactor artifact following TEMPLATE.md
- [ ] Run quality checks"""
        }

        puml_path = EXAMPLES_DIR / "workflow_activity.puml"
        write_output(workflow_data, "plantuml", puml_path)

        self.assertTrue(puml_path.exists(), "PlantUML file not created")
        content = puml_path.read_text(encoding="utf-8")

        # Validate PlantUML structure
        self.assertIn("@startuml", content)
        self.assertIn("@enduml", content)
        self.assertIn("title", content)
        self.assertIn("start", content)
        self.assertIn("stop", content)

        # Validate workflow steps are present
        self.assertIn("Confirm artifact", content)
        self.assertIn("Read TEMPLATE", content)
        self.assertIn("Run quality checks", content)

        # Ensure it's an activity diagram (has colons for activities)
        self.assertIn(":", content, "Should use activity syntax (:step;)")

        # Verify no generic object diagram artifacts
        self.assertNotIn("object", content.lower(), "Should not be object diagram")

        print(f"   ✅ Activity diagram created: {puml_path}")
        print(f"   ✅ Contains {content.count(':'):} activity steps")

    def test_02_workflow_mermaid_flowchart(self):
        """Test workflow checklist → Mermaid flowchart"""
        print("\n🌊 Testing Workflow → Mermaid Flowchart...")

        workflow_data = {
            "command": "update",
            "checklist": """Update Progress:
- [ ] Locate existing artifact
- [ ] Read current version
- [ ] Review TEMPLATE.md for updates
- [ ] Apply changes maintaining structure
- [ ] Validate output
- [ ] Run quality audit
- [ ] Update version control"""
        }

        mmd_path = EXAMPLES_DIR / "workflow_flowchart.mmd"
        write_output(workflow_data, "mermaid", mmd_path)

        self.assertTrue(mmd_path.exists(), "Mermaid file not created")
        content = mmd_path.read_text(encoding="utf-8")

        # Validate Mermaid flowchart structure
        self.assertIn("flowchart", content)
        self.assertIn("Start", content)
        self.assertIn("End", content)

        # Validate steps are present
        self.assertIn("Locate existing artifact", content)
        self.assertIn("Run quality audit", content)
        self.assertIn("Update version control", content)

        # Validate arrows/connections
        arrow_count = content.count("-->")
        self.assertGreater(arrow_count, 5, f"Should have many connections, found {arrow_count}")

        # Verify not a generic tree diagram
        self.assertNotIn("root[", content, "Should not be generic tree")

        print(f"   ✅ Flowchart created: {mmd_path}")
        print(f"   ✅ Contains {arrow_count} workflow connections")

    def test_03_complex_workflow_with_conditionals(self):
        """Test complex workflow with many steps"""
        print("\n🔥 Testing Complex Workflow (10+ steps)...")

        complex_workflow = {
            "command": "review",
            "checklist": """Review Progress:
- [ ] Identify artifacts for review
- [ ] Load artifact templates and standards
- [ ] Check version control history
- [ ] Validate artifact structure
- [ ] Verify placeholder coverage
- [ ] Check terminology consistency
- [ ] Audit quality metrics
- [ ] Review traceability matrix
- [ ] Validate ownership and approvals
- [ ] Generate review report
- [ ] Document findings
- [ ] Create action items if needed"""
        }

        # Test both formats
        puml_path = EXAMPLES_DIR / "complex_workflow.puml"
        mmd_path = EXAMPLES_DIR / "complex_workflow.mmd"

        write_output(complex_workflow, "plantuml", puml_path)
        write_output(complex_workflow, "mermaid", mmd_path)

        self.assertTrue(puml_path.exists())
        self.assertTrue(mmd_path.exists())

        puml_content = puml_path.read_text()
        mmd_content = mmd_path.read_text()

        # Validate PlantUML has all steps
        step_count_puml = puml_content.count(":")
        self.assertGreater(step_count_puml, 10, f"Should have 10+ steps, found {step_count_puml}")

        # Validate Mermaid has all steps
        step_count_mmd = mmd_content.count("Step")
        self.assertGreater(step_count_mmd, 10, f"Should have 10+ steps, found {step_count_mmd}")

        print(f"   ✅ Complex PlantUML: {step_count_puml} activities")
        print(f"   ✅ Complex Mermaid: {step_count_mmd} steps")

    def test_04_audit_plantuml_class_diagram(self):
        """Test audit results → PlantUML class diagram"""
        print("\n📋 Testing Audit → PlantUML Class Diagram...")

        audit_data = {
            "artifacts": {
                "project_charter": {
                    "status": "complete",
                    "version": "1.2",
                    "owner": "PM Team",
                    "issues": 0
                },
                "wbs": {
                    "status": "in_progress",
                    "version": "0.8",
                    "owner": "Tech Lead",
                    "issues": 2
                },
                "risk_register": {
                    "status": "complete",
                    "version": "1.0",
                    "owner": "Risk Manager",
                    "issues": 0
                }
            }
        }

        puml_path = EXAMPLES_DIR / "audit_class.puml"
        write_output(audit_data, "plantuml", puml_path)

        self.assertTrue(puml_path.exists())
        content = puml_path.read_text()

        # Validate Salt table structure (doesn't require GraphViz!)
        self.assertIn("@startsalt", content)
        self.assertIn("@endsalt", content)
        self.assertIn("Quality Audit Results", content)

        # Validate artifacts are in the table
        self.assertIn("project_charter", content)
        self.assertIn("wbs", content)
        self.assertIn("risk_register", content)

        # Validate table columns
        self.assertIn("Artifact", content)
        self.assertIn("Status", content)
        self.assertIn("Version", content)
        self.assertIn("Owner", content)

        # Validate data values
        self.assertIn("complete", content)
        self.assertIn("in_progress", content)
        self.assertIn("PM Team", content)
        self.assertIn("Tech Lead", content)

        print(f"   ✅ Salt table created: {puml_path}")
        print(f"   ✅ Contains {content.count('|')} table cells")

    def test_05_audit_mermaid_table(self):
        """Test audit results → Mermaid markdown table"""
        print("\n📊 Testing Audit → Mermaid Table...")

        audit_data = {
            "audit": {
                "stakeholder_register": {
                    "status": "approved",
                    "last_updated": "2024-01-15",
                    "compliance": "100%"
                },
                "communication_plan": {
                    "status": "draft",
                    "last_updated": "2024-01-10",
                    "compliance": "85%"
                }
            }
        }

        mmd_path = EXAMPLES_DIR / "audit_table.md"
        write_output(audit_data, "mermaid", mmd_path)

        self.assertTrue(mmd_path.exists())
        content = mmd_path.read_text()

        # Validate table structure
        self.assertIn("| Artifact", content)
        self.assertIn("| Status", content)
        self.assertIn("|---", content, "Should have table separator")

        # Validate data rows
        self.assertIn("stakeholder_register", content)
        self.assertIn("communication_plan", content)
        self.assertIn("approved", content)
        self.assertIn("draft", content)

        print(f"   ✅ Audit table created: {mmd_path}")

    def test_06_fallback_to_generic_for_unknown_data(self):
        """Test fallback to generic diagrams for non-PM data"""
        print("\n🔄 Testing Fallback for Generic Data...")

        generic_data = {
            "title": "Generic Report",
            "items": ["a", "b", "c"]
        }

        puml_path = EXAMPLES_DIR / "fallback_generic.puml"
        mmd_path = EXAMPLES_DIR / "fallback_generic.mmd"

        write_output(generic_data, "plantuml", puml_path)
        write_output(generic_data, "mermaid", mmd_path)

        self.assertTrue(puml_path.exists())
        self.assertTrue(mmd_path.exists())

        puml_content = puml_path.read_text()
        mmd_content = mmd_path.read_text()

        # PlantUML should use JSON diagram for generic data
        self.assertIn("@startjson", puml_content)
        self.assertIn("@endjson", puml_content)

        # Mermaid should use tree diagram
        self.assertIn("graph TD", mmd_content)

        print(f"   ✅ Fallback mechanisms work correctly (JSON/Tree)")


if __name__ == "__main__":
    unittest.main()
