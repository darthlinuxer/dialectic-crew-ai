"""Enhanced export utilities for PMBOK PM artifacts with domain-specific visualizations."""

from typing import Any, Dict, List


class WorkflowExporter:
    """Export workflow checklists as PM diagrams"""

    @staticmethod
    def to_plantuml_activity(workflow_data: Dict[str, Any]) -> str:
        """
        Convert workflow checklist to PlantUML activity diagram

        Args:
            workflow_data: Dict with 'command' and 'checklist' fields

        Returns:
            PlantUML activity diagram string
        """
        command = workflow_data.get('command', 'Workflow')
        checklist = workflow_data.get('checklist', '')

        # Extract steps from checklist (lines starting with "- [ ]")
        steps = []
        for line in checklist.splitlines():
            line = line.strip()
            if line.startswith('- [ ]'):
                step = line.replace('- [ ]', '').strip()
                if step:
                    steps.append(step)

        lines = [
            "@startuml",
            f"title {command.title()} Workflow",
            "start"
        ]

        for step in steps:
            # Escape special characters for PlantUML
            safe_step = step.replace('"', "'").replace('|', '/')
            lines.append(f":{safe_step};")

        lines.extend([
            "stop",
            "@enduml"
        ])

        return '\n'.join(lines) + '\n'

    @staticmethod
    def to_mermaid_flowchart(workflow_data: Dict[str, Any]) -> str:
        """
        Convert workflow checklist to Mermaid flowchart

        Args:
            workflow_data: Dict with 'command' and 'checklist' fields

        Returns:
            Mermaid flowchart string
        """
        command = workflow_data.get('command', 'Workflow')
        checklist = workflow_data.get('checklist', '')

        # Extract steps from checklist
        steps = []
        for line in checklist.splitlines():
            line = line.strip()
            if line.startswith('- [ ]'):
                step = line.replace('- [ ]', '').strip()
                if step:
                    steps.append(step)

        lines = [
            "flowchart TD",
            f"    Start([Start: {command.title()} Workflow])"
        ]

        # Generate step nodes
        for i, step in enumerate(steps):
            step_id = f"Step{i+1}"
            # Truncate long steps for readability
            short_step = step if len(step) <= 50 else step[:47] + "..."
            safe_step = short_step.replace('"', "'").replace('|', '/')
            lines.append(f"    {step_id}[{safe_step}]")

        lines.append("    End([Complete])")
        lines.append("")

        # Generate connections
        if steps:
            lines.append("    Start --> Step1")
            for i in range(len(steps) - 1):
                lines.append(f"    Step{i+1} --> Step{i+2}")
            lines.append(f"    Step{len(steps)} --> End")

        return '\n'.join(lines) + '\n'


class AuditExporter:
    """Export quality audit results as structured diagrams"""

    @staticmethod
    def to_plantuml_class(audit_data: Dict[str, Any]) -> str:
        """
        Convert audit results to PlantUML Salt table (doesn't require GraphViz!)

        Args:
            audit_data: Audit results dictionary

        Returns:
            PlantUML Salt wireframe table string
        """
        lines = [
            "@startsalt",
            "{",
            "  Quality Audit Results",
            "  ==",
        ]

        # Handle nested structure - look for artifacts/audit keys
        artifacts_dict = audit_data
        if 'artifacts' in audit_data:
            artifacts_dict = audit_data['artifacts']
        elif 'audit' in audit_data:
            artifacts_dict = audit_data['audit']

        # Create table rows for each artifact
        if isinstance(artifacts_dict, dict):
            # Add header
            lines.append("  {T")
            lines.append("  + Artifact | Status | Version | Owner | Issues")

            # Add data rows
            for artifact_name, details in artifacts_dict.items():
                if isinstance(details, dict):
                    status = details.get('status', 'N/A')
                    version = details.get('version', 'N/A')
                    owner = details.get('owner', 'N/A')
                    issues = details.get('issues', 'N/A')

                    lines.append(f"  | {artifact_name} | {status} | {version} | {owner} | {issues}")
                else:
                    lines.append(f"  | {artifact_name} | {details} | - | - | -")

            lines.append("  }")

        lines.extend([
            "}",
            "@endsalt"
        ])

        return '\n'.join(lines) + '\n'

    @staticmethod
    def to_mermaid_table(audit_data: Dict[str, Any]) -> str:
        """
        Convert audit results to Mermaid-compatible markdown table

        Args:
            audit_data: Audit results dictionary

        Returns:
            Markdown table string
        """
        lines = [
            "# Quality Audit Results",
            "",
            "| Artifact | Status | Details |",
            "|----------|--------|---------|"
        ]

        if isinstance(audit_data, dict):
            for artifact, details in audit_data.items():
                artifact_str = str(artifact)
                if isinstance(details, dict):
                    status = details.get('status', 'unknown')
                    detail_str = ', '.join(f"{k}={v}" for k, v in details.items() if k != 'status')
                else:
                    status = 'N/A'
                    detail_str = str(details)[:100]

                lines.append(f"| {artifact_str} | {status} | {detail_str} |")

        return '\n'.join(lines) + '\n'


def enhance_workflow_output(data: Dict[str, Any], fmt: str) -> str:
    """
    Enhance workflow checklist output with PM-specific diagrams

    Args:
        data: Workflow data dict
        fmt: Output format ('plantuml' or 'mermaid')

    Returns:
        Enhanced diagram string
    """
    # Check if this is workflow data
    if 'checklist' in data or 'command' in data:
        if fmt.lower() in {'plantuml', 'puml'}:
            return WorkflowExporter.to_plantuml_activity(data)
        elif fmt.lower() in {'mermaid', 'mmd'}:
            return WorkflowExporter.to_mermaid_flowchart(data)

    return None  # Not workflow data


def enhance_audit_output(data: Dict[str, Any], fmt: str) -> str:
    """
    Enhance audit output with PM-specific diagrams

    Args:
        data: Audit data dict
        fmt: Output format ('plantuml' or 'mermaid')

    Returns:
        Enhanced diagram string
    """
    # Check if this looks like audit data
    if any(key in data for key in ['artifacts', 'audit', 'quality', 'issues']):
        if fmt.lower() in {'plantuml', 'puml'}:
            return AuditExporter.to_plantuml_class(data)
        elif fmt.lower() in {'mermaid', 'mmd'}:
            return AuditExporter.to_mermaid_table(data)

    return None  # Not audit data
