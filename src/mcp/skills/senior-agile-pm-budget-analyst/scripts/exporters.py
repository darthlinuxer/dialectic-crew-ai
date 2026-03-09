#!/usr/bin/env python3
"""
Multi-Format Export Utilities

Provides export functions for various output formats:
- Markdown tables and documents
- Mermaid diagrams (flowchart, gantt, pie, etc.)
- PlantUML diagrams
- HTML reports
- CSV data files
- PDF (via HTML conversion)

All exports use only Python standard library (no external dependencies).

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import csv
import io
from html import escape


class MarkdownExporter:
    """Export data to Markdown format"""

    @staticmethod
    def table(headers: List[str], rows: List[List[Any]], alignment: Optional[List[str]] = None) -> str:
        """
        Create a markdown table

        Args:
            headers: Column headers
            rows: Data rows
            alignment: List of 'left', 'center', 'right' for each column

        Returns:
            Markdown table string
        """
        if not rows:
            return ""

        # Default alignment is left
        if alignment is None:
            alignment = ['left'] * len(headers)

        # Create alignment row
        align_map = {
            'left': ':---',
            'center': ':---:',
            'right': '---:'
        }
        align_row = [align_map.get(a, ':---') for a in alignment]

        # Build table
        lines = []
        lines.append('| ' + ' | '.join(str(h) for h in headers) + ' |')
        lines.append('| ' + ' | '.join(align_row) + ' |')

        for row in rows:
            lines.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')

        return '\n'.join(lines)

    @staticmethod
    def heading(text: str, level: int = 1) -> str:
        """Create markdown heading"""
        return '#' * level + ' ' + text

    @staticmethod
    def bullet_list(items: List[str], ordered: bool = False) -> str:
        """Create markdown list"""
        lines = []
        for i, item in enumerate(items, 1):
            prefix = f"{i}." if ordered else "-"
            lines.append(f"{prefix} {item}")
        return '\n'.join(lines)

    @staticmethod
    def code_block(code: str, language: str = "") -> str:
        """Create markdown code block"""
        return f"```{language}\n{code}\n```"

    @staticmethod
    def bold(text: str) -> str:
        """Make text bold"""
        return f"**{text}**"

    @staticmethod
    def italic(text: str) -> str:
        """Make text italic"""
        return f"*{text}*"


class MermaidExporter:
    """Export data to Mermaid diagram format"""

    @staticmethod
    def flowchart(
        nodes: List[Dict],
        edges: List[Dict],
        direction: str = "TB",
        critical_color: str = "#ff6b6b",
        critical_stroke: str = "#c92a2a",
        critical_stroke_width: str = "3px",
        normal_color: str = "#4ECDC4",
        normal_stroke: str = "#45B7AF",
        normal_stroke_width: str = "2px",
        show_duration: bool = False
    ) -> str:
        """
        Create a Mermaid flowchart with configurable styling

        Args:
            nodes: List of {id, label, shape, critical, duration} dicts
            edges: List of {from, to, label} dicts
            direction: TB (top-bottom), LR (left-right), BT, RL
            critical_color: Fill color for critical path nodes (default: red)
            critical_stroke: Border color for critical path nodes
            critical_stroke_width: Border width for critical path nodes
            normal_color: Fill color for non-critical nodes (default: teal)
            normal_stroke: Border color for non-critical nodes
            normal_stroke_width: Border width for non-critical nodes
            show_duration: If True, append duration to edge labels

        Returns:
            Mermaid flowchart string with styled critical path
        """
        lines = [f"flowchart {direction}"]

        # Add nodes
        for node in nodes:
            node_id = node['id']
            label = node.get('label', node_id)
            shape = node.get('shape', 'rounded')

            # Shape mapping
            if shape == 'box':
                lines.append(f"    {node_id}[{label}]")
            elif shape == 'rounded':
                lines.append(f"    {node_id}({label})")
            elif shape == 'circle':
                lines.append(f"    {node_id}(({label}))")
            elif shape == 'diamond':
                lines.append(f"    {node_id}{{{{{label}}}}}")
            elif shape == 'hexagon':
                lines.append(f"    {node_id}{{{{{label}}}}}")
            elif shape == 'stadium':
                lines.append(f"    {node_id}([{label}])")
            else:
                lines.append(f"    {node_id}({label})")

        # Add edges
        for edge in edges:
            from_node = edge['from']
            to_node = edge['to']
            label = edge.get('label', '')

            # Optionally append duration
            if show_duration and 'duration' in edge:
                duration_label = f"{edge['duration']}d"
                label = f"{label} {duration_label}" if label else duration_label

            # Determine edge style (thick for critical path)
            edge_style = "==>" if edge.get('critical', False) else "-->"

            if label:
                lines.append(f"    {from_node} {edge_style}|{label}| {to_node}")
            else:
                lines.append(f"    {from_node} {edge_style} {to_node}")

        # Add styling for critical and normal nodes
        critical_nodes = [n['id'] for n in nodes if n.get('critical', False)]
        normal_nodes = [n['id'] for n in nodes if not n.get('critical', False)]

        if critical_nodes:
            lines.append(f"    classDef critical fill:{critical_color},stroke:{critical_stroke},stroke-width:{critical_stroke_width}")
            lines.append(f"    class {','.join(critical_nodes)} critical")

        if normal_nodes:
            lines.append(f"    classDef normal fill:{normal_color},stroke:{normal_stroke},stroke-width:{normal_stroke_width}")
            lines.append(f"    class {','.join(normal_nodes)} normal")

        return '\n'.join(lines)

    @staticmethod
    def gantt(title: str, sections: List[Dict]) -> str:
        """
        Create a Mermaid Gantt chart

        Args:
            title: Chart title
            sections: List of {name, tasks: [{id, name, start, end, status}]}

        Returns:
            Mermaid Gantt chart string
        """
        lines = ["gantt"]
        lines.append(f"    title {title}")
        lines.append(f"    dateFormat YYYY-MM-DD")

        for section in sections:
            lines.append(f"    section {section['name']}")

            for task in section.get('tasks', []):
                task_name = task['name']
                task_id = task.get('id', task_name.replace(' ', '_'))
                start = task['start']
                end = task['end']
                status = task.get('status', 'active')

                # Status mapping: active, done, crit
                lines.append(f"    {task_name} :{status}, {task_id}, {start}, {end}")

        return '\n'.join(lines)

    @staticmethod
    def pie_chart(title: str, data: Dict[str, float]) -> str:
        """
        Create a Mermaid pie chart

        Args:
            title: Chart title
            data: Dictionary of label -> value

        Returns:
            Mermaid pie chart string
        """
        lines = ["pie"]
        lines.append(f'    title {title}')

        for label, value in data.items():
            lines.append(f'    "{label}" : {value}')

        return '\n'.join(lines)

    @staticmethod
    def line_chart(title: str, x_labels: List[str], datasets: List[Dict]) -> str:
        """
        Create a Mermaid line chart (using xychart)

        Args:
            title: Chart title
            x_labels: X-axis labels
            datasets: List of {label, data: [values]}

        Returns:
            Mermaid line chart string
        """
        lines = ["%%{init: {'theme':'base'}}%%"]
        lines.append("xychart-beta")
        lines.append(f'    title "{title}"')
        x_axis_labels = ", ".join(f'"{x}"' for x in x_labels)
        lines.append(f'    x-axis [{x_axis_labels}]')

        for dataset in datasets:
            label = dataset['label']
            data = dataset['data']
            lines.append(f'    line [{", ".join(str(v) for v in data)}]')

        return '\n'.join(lines)


class PlantUMLExporter:
    """Export data to PlantUML diagram format"""

    @staticmethod
    def activity_diagram(activities: List[Dict], title: str = "Activity Diagram") -> str:
        """
        Create a PlantUML activity diagram

        Args:
            activities: List of {id, name, predecessors, critical} dicts
            title: Diagram title

        Returns:
            PlantUML activity diagram string
        """
        lines = ["@startuml"]
        lines.append(f"title {title}")
        lines.append("")

        # Define activities
        for activity in activities:
            act_id = activity['id']
            name = activity['name']
            is_critical = activity.get('critical', False)

            color = "#FF6B6B" if is_critical else "#4ECDC4"
            lines.append(f":{name};")
            lines.append(f"note right: {act_id}")

        lines.append("")
        lines.append("@enduml")

        return '\n'.join(lines)

    @staticmethod
    def gantt_diagram(
        tasks: List[Dict],
        title: str = "Project Timeline",
        critical_color: str = "Red",
        normal_color: str = "LightBlue",
        print_scale: str = "weekly"
    ) -> str:
        """
        Create a PlantUML Gantt diagram with configurable styling

        Args:
            tasks: List of {id, name, start, duration, dependencies, critical} dicts
            title: Diagram title
            critical_color: Color for critical path tasks (default: Red)
            normal_color: Color for non-critical tasks (default: LightBlue)
            print_scale: Time scale - daily, weekly, monthly (default: weekly)

        Returns:
            PlantUML Gantt diagram string with styled critical path
        """
        lines = ["@startgantt"]
        lines.append(f"title {title}")
        lines.append("")
        lines.append(f"printscale {print_scale}")
        lines.append("")

        for task in tasks:
            task_id = task['id']
            name = task['name']
            start = task.get('start', '')
            duration = int(task.get('duration', 1))  # Convert to int for PlantUML
            deps = task.get('dependencies', [])
            is_critical = task.get('critical', False)

            color = critical_color if is_critical else normal_color

            # PlantUML requires duration and dependencies in SAME statement
            if start:
                # Explicit start date
                lines.append(f"[{name}] as [{task_id}] starts {start} and lasts {duration} days")
            elif len(deps) == 0:
                # No dependencies - just duration
                lines.append(f"[{name}] as [{task_id}] lasts {duration} days")
            elif len(deps) == 1:
                # Single dependency - combine with duration
                lines.append(f"[{name}] as [{task_id}] starts at [{deps[0]}]'s end and lasts {duration} days")
            else:
                # Multiple dependencies - document all but use last one
                lines.append(f"' Note: [{task_id}] depends on: {', '.join(deps)}")
                lines.append(f"[{name}] as [{task_id}] starts at [{deps[-1]}]'s end and lasts {duration} days")

            # Apply color
            lines.append(f"[{task_id}] is colored in {color}")

        lines.append("")
        lines.append("@endgantt")

        return '\n'.join(lines)

    @staticmethod
    def class_diagram(classes: List[Dict], title: str = "Class Diagram") -> str:
        """
        Create a PlantUML class diagram

        Args:
            classes: List of {name, attributes, methods} dicts
            title: Diagram title

        Returns:
            PlantUML class diagram string
        """
        lines = ["@startuml"]
        lines.append(f"title {title}")
        lines.append("")

        for cls in classes:
            lines.append(f"class {cls['name']} {{")

            for attr in cls.get('attributes', []):
                lines.append(f"  {attr}")

            lines.append("  --")

            for method in cls.get('methods', []):
                lines.append(f"  {method}")

            lines.append("}")
            lines.append("")

        lines.append("@enduml")

        return '\n'.join(lines)


class HTMLExporter:
    """Export data to HTML format"""

    @staticmethod
    def simple_report(title: str, sections: List[Dict]) -> str:
        """
        Create a simple HTML report

        Args:
            title: Report title
            sections: List of {heading, content} dicts

        Returns:
            HTML string
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{escape(title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 10px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .critical {{
            color: #e74c3c;
            font-weight: bold;
        }}
        .success {{
            color: #27ae60;
        }}
        .warning {{
            color: #f39c12;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        .metadata {{
            color: #7f8c8d;
            font-size: 0.9em;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h1>{escape(title)}</h1>
"""

        for section in sections:
            heading = section.get('heading', '')
            content = section.get('content', '')

            if heading:
                html += f"    <h2>{escape(heading)}</h2>\n"

            html += f"    {content}\n"

        # Add metadata
        html += f"""
    <div class="metadata">
        Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
        Tool: Senior Agile PM Budget Analyst
    </div>
</body>
</html>
"""

        return html

    @staticmethod
    def table(headers: List[str], rows: List[List[Any]], css_class: str = "") -> str:
        """Create HTML table"""
        html = f'<table class="{css_class}">\n'
        html += '  <tr>\n'

        for header in headers:
            html += f'    <th>{escape(str(header))}</th>\n'

        html += '  </tr>\n'

        for row in rows:
            html += '  <tr>\n'
            for cell in row:
                html += f'    <td>{escape(str(cell))}</td>\n'
            html += '  </tr>\n'

        html += '</table>\n'

        return html


class CSVExporter:
    """Export data to CSV format"""

    @staticmethod
    def to_csv(headers: List[str], rows: List[List[Any]]) -> str:
        """
        Create CSV string

        Args:
            headers: Column headers
            rows: Data rows

        Returns:
            CSV string
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(headers)
        writer.writerows(rows)

        return output.getvalue()

    @staticmethod
    def dict_to_csv(data: List[Dict]) -> str:
        """
        Convert list of dicts to CSV

        Args:
            data: List of dictionaries

        Returns:
            CSV string
        """
        if not data:
            return ""

        output = io.StringIO()
        headers = list(data[0].keys())
        writer = csv.DictWriter(output, fieldnames=headers)

        writer.writeheader()
        writer.writerows(data)

        return output.getvalue()


class JSONExporter:
    """Export data to JSON format"""

    @staticmethod
    def to_json(data: Any, indent: int = 2) -> str:
        """
        Convert data to formatted JSON

        Args:
            data: Data to export
            indent: Indentation level

        Returns:
            JSON string
        """
        return json.dumps(data, indent=indent, default=str)


def save_to_file(content: str, filepath: str) -> None:
    """
    Save content to file

    Args:
        content: String content to save
        filepath: Output file path
    """
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    """Example usage of exporters"""

    print("=" * 80)
    print("EXPORT UTILITIES - Example Usage")
    print("=" * 80)

    # Example 1: Markdown Table
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Markdown Table")
    print("=" * 80)

    headers = ["Task", "Duration", "Status", "Owner"]
    rows = [
        ["Epic 1", "14 days", "✅ Complete", "Team A"],
        ["Epic 2", "21 days", "🔄 In Progress", "Team B"],
        ["Epic 3", "7 days", "⏳ Not Started", "Team A"]
    ]

    md_table = MarkdownExporter.table(headers, rows, alignment=['left', 'right', 'center', 'left'])
    print("\n" + md_table)

    # Example 2: Mermaid Flowchart
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Mermaid Flowchart (Critical Path)")
    print("=" * 80)

    nodes = [
        {"id": "A", "label": "Epic 1", "shape": "box", "critical": True},
        {"id": "B", "label": "Epic 2", "shape": "box", "critical": True},
        {"id": "C", "label": "Epic 3", "shape": "box", "critical": False},
        {"id": "D", "label": "Epic 4", "shape": "box", "critical": True}
    ]

    edges = [
        {"from": "A", "to": "B", "label": "14d"},
        {"from": "A", "to": "C", "label": "7d"},
        {"from": "B", "to": "D", "label": "21d"},
        {"from": "C", "to": "D", "label": ""}
    ]

    mermaid_flow = MermaidExporter.flowchart(nodes, edges, direction="LR")
    print("\n```mermaid")
    print(mermaid_flow)
    print("```")

    # Example 3: Mermaid Gantt Chart
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Mermaid Gantt Chart")
    print("=" * 80)

    sections = [
        {
            "name": "Sprint 1",
            "tasks": [
                {"id": "epic1", "name": "User Authentication", "start": "2024-03-01", "end": "2024-03-14", "status": "done"},
                {"id": "epic2", "name": "Product Catalog", "start": "2024-03-01", "end": "2024-03-14", "status": "done"}
            ]
        },
        {
            "name": "Sprint 2",
            "tasks": [
                {"id": "epic3", "name": "Shopping Cart", "start": "2024-03-15", "end": "2024-03-28", "status": "active"},
                {"id": "epic4", "name": "Checkout Process", "start": "2024-03-15", "end": "2024-03-28", "status": "active"}
            ]
        }
    ]

    mermaid_gantt = MermaidExporter.gantt("E-commerce Project", sections)
    print("\n```mermaid")
    print(mermaid_gantt)
    print("```")

    # Example 4: PlantUML Gantt
    print("\n" + "=" * 80)
    print("EXAMPLE 4: PlantUML Gantt Diagram")
    print("=" * 80)

    tasks = [
        {"id": "E1", "name": "Epic 1", "start": "2024-03-01", "duration": 14, "critical": True},
        {"id": "E2", "name": "Epic 2", "start": "2024-03-15", "duration": 21, "dependencies": ["E1"], "critical": True},
        {"id": "E3", "name": "Epic 3", "start": "2024-03-15", "duration": 14, "dependencies": ["E1"], "critical": False}
    ]

    plantuml_gantt = PlantUMLExporter.gantt_diagram(tasks, "Project Timeline")
    print("\n```plantuml")
    print(plantuml_gantt)
    print("```")

    # Example 5: CSV Export
    print("\n" + "=" * 80)
    print("EXAMPLE 5: CSV Export")
    print("=" * 80)

    csv_data = CSVExporter.to_csv(headers, rows)
    print("\n" + csv_data)

    # Example 6: HTML Report
    print("\n" + "=" * 80)
    print("EXAMPLE 6: HTML Report")
    print("=" * 80)

    html_sections = [
        {
            "heading": "Project Summary",
            "content": "<p>Total Duration: <strong>42 days</strong></p><p>Budget: <strong>$150,000</strong></p>"
        },
        {
            "heading": "Task Overview",
            "content": HTMLExporter.table(headers, rows)
        }
    ]

    html_report = HTMLExporter.simple_report("Project Report", html_sections)
    print("\nHTML Report generated (sample):")
    print(html_report[:500] + "...")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
