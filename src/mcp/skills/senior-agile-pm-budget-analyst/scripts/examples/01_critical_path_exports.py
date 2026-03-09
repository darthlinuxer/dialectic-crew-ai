#!/usr/bin/env python3
"""
Critical Path Analysis - Multi-Format Export Examples

Demonstrates how to use critical_path.py with various export formats:
- Markdown reports
- Mermaid flowcharts
- PlantUML diagrams
- HTML reports
- CSV data
- PDF (via HTML)

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

import sys
sys.path.append('..')

from critical_path import CriticalPathAnalyzer, Activity
from exporters import (
    MarkdownExporter, MermaidExporter, PlantUMLExporter,
    HTMLExporter, CSVExporter, JSONExporter, save_to_file
)
from datetime import datetime


def export_to_markdown(result: dict) -> str:
    """Export CPM analysis to Markdown format"""
    md = MarkdownExporter

    lines = []
    lines.append(md.heading("Critical Path Analysis Report", 1))
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # Summary
    lines.append(md.heading("Executive Summary", 2))
    lines.append(f"- **Project Duration**: {result['project_duration']} {result['unit']}")
    lines.append(f"- **Critical Path**: {' → '.join(result['critical_path'])}")
    lines.append(f"- **Critical Tasks**: {result['statistics']['critical_activities_count']}")
    lines.append(f"- **Total Activities**: {result['statistics']['total_activities']}")
    lines.append("")

    # Critical Path Details
    lines.append(md.heading("Critical Path", 2))
    lines.append("Tasks that cannot be delayed without impacting project completion:")
    lines.append("")

    critical_tasks = [act for act in result['activities'] if act['critical']]
    crit_headers = ["ID", "Name", "Duration", "ES", "EF"]
    crit_rows = [[t['id'], t['name'], f"{t['duration']}{result['unit']}", t['ES'], t['EF']]
                 for t in critical_tasks]
    lines.append(md.table(crit_headers, crit_rows))
    lines.append("")

    # All Activities
    lines.append(md.heading("All Activities", 2))
    headers = ["ID", "Name", "Duration", "ES", "EF", "LS", "LF", "Slack", "Critical"]
    rows = []
    for act in result['activities']:
        rows.append([
            act['id'],
            act['name'],
            act['duration'],
            act['ES'],
            act['EF'],
            act['LS'],
            act['LF'],
            f"{act['slack']:.1f}",
            "✅" if act['critical'] else "❌"
        ])
    lines.append(md.table(headers, rows))
    lines.append("")

    # Bottlenecks
    if result['bottlenecks']:
        lines.append(md.heading("⚠️ Bottlenecks & Risks", 2))
        lines.append("These critical tasks have high dependency risks:")
        lines.append("")
        for bn in result['bottlenecks']:
            lines.append(f"- **{bn['name']}** (ID: {bn['id']})")
            lines.append(f"  - Depends on: {', '.join(bn['critical_predecessors'])}")
            lines.append(f"  - Successor count: {bn['successor_count']}")
        lines.append("")

    # Optimization Opportunities
    if result['optimization_opportunities']:
        lines.append(md.heading("💡 Optimization Opportunities", 2))
        for opp in result['optimization_opportunities'][:5]:
            lines.append(f"- **{opp['name']}**: {opp['recommendation']}")
        lines.append("")

    # Statistics
    lines.append(md.heading("Statistics", 2))
    stats = result['statistics']
    stats_rows = [
        ["Metric", "Value"],
        ["Total Activities", stats['total_activities']],
        ["Critical Activities", stats['critical_activities_count']],
        ["Average Slack (non-critical)", f"{stats['average_slack']:.2f} {result['unit']}"],
        ["Max Slack", f"{stats['max_slack']:.2f} {result['unit']}"]
    ]
    lines.append(md.table(stats_rows[0], stats_rows[1:]))

    return '\n'.join(lines)


def export_to_mermaid_flowchart(result: dict) -> str:
    """Export CPM analysis to Mermaid flowchart"""
    nodes = []
    edges = []

    # Create nodes
    for act in result['activities']:
        nodes.append({
            'id': act['id'],
            'label': f"{act['name']}\\n{act['duration']}d",
            'shape': 'rounded',
            'critical': act['critical']
        })

    # Create edges
    for act in result['activities']:
        for pred in act.get('predecessors', []):
            label = ""
            if act['critical']:
                label = "Critical"
            edges.append({
                'from': pred,
                'to': act['id'],
                'label': label
            })

    mermaid = MermaidExporter.flowchart(nodes, edges, direction="LR")

    # Wrap in markdown code block
    return f"```mermaid\n{mermaid}\n```"


def export_to_plantuml_gantt(result: dict, start_date: str = "2024-03-01") -> str:
    """Export CPM analysis to PlantUML Gantt diagram"""
    tasks = []

    for act in result['activities']:
        task = {
            'id': act['id'],
            'name': act['name'],
            'start': start_date if not act.get('predecessors') else None,
            'duration': int(act['duration']),
            'dependencies': act.get('predecessors', []),
            'critical': act['critical']
        }
        tasks.append(task)

    plantuml = PlantUMLExporter.gantt_diagram(tasks, "Critical Path Timeline")

    return f"```plantuml\n{plantuml}\n```"


def export_to_html_report(result: dict) -> str:
    """Export CPM analysis to HTML report"""

    sections = []

    # Summary section
    summary_content = f"""
    <div style="background: #e8f4f8; padding: 15px; border-radius: 5px; margin: 20px 0;">
        <h3>Key Metrics</h3>
        <ul>
            <li><strong>Project Duration:</strong> {result['project_duration']} {result['unit']}</li>
            <li><strong>Critical Path:</strong> {' → '.join(result['critical_path'])}</li>
            <li><strong>Critical Activities:</strong> {result['statistics']['critical_activities_count']} / {result['statistics']['total_activities']}</li>
        </ul>
    </div>
    """
    sections.append({"heading": "Executive Summary", "content": summary_content})

    # Activities table
    headers = ["ID", "Name", "Duration", "ES", "EF", "LS", "LF", "Slack", "Critical"]
    rows = []
    for act in result['activities']:
        crit_marker = '<span class="critical">✓ CRITICAL</span>' if act['critical'] else ''
        rows.append([
            act['id'],
            act['name'],
            f"{act['duration']} {result['unit']}",
            act['ES'],
            act['EF'],
            act['LS'],
            act['LF'],
            f"{act['slack']:.1f}",
            crit_marker
        ])

    activities_table = HTMLExporter.table(headers, rows)
    sections.append({"heading": "All Activities", "content": activities_table})

    # Bottlenecks
    if result['bottlenecks']:
        bottleneck_content = "<ul>"
        for bn in result['bottlenecks']:
            bottleneck_content += f"""
            <li>
                <strong>{bn['name']}</strong> (ID: {bn['id']})
                <ul>
                    <li>Depends on: {', '.join(bn['critical_predecessors'])}</li>
                    <li>Has {bn['successor_count']} successor(s)</li>
                </ul>
            </li>
            """
        bottleneck_content += "</ul>"
        sections.append({"heading": "⚠️ Bottlenecks & Risks", "content": bottleneck_content})

    return HTMLExporter.simple_report("Critical Path Analysis", sections)


def export_to_csv(result: dict) -> str:
    """Export CPM analysis to CSV format"""
    headers = ["ID", "Name", "Duration", "ES", "EF", "LS", "LF", "Slack", "Critical", "Predecessors"]
    rows = []

    for act in result['activities']:
        rows.append([
            act['id'],
            act['name'],
            act['duration'],
            act['ES'],
            act['EF'],
            act['LS'],
            act['LF'],
            f"{act['slack']:.2f}",
            "Yes" if act['critical'] else "No",
            ";".join(act.get('predecessors', []))
        ])

    return CSVExporter.to_csv(headers, rows)


def main():
    """Demonstrate all export formats for Critical Path Analysis"""

    print("=" * 80)
    print("CRITICAL PATH ANALYSIS - MULTI-FORMAT EXPORT EXAMPLES")
    print("=" * 80)

    # Sample project data
    activities = [
        {"id": "A", "name": "Requirements Analysis", "duration": 5, "predecessors": []},
        {"id": "B", "name": "Design", "duration": 8, "predecessors": ["A"]},
        {"id": "C", "name": "Procurement", "duration": 3, "predecessors": ["A"]},
        {"id": "D", "name": "Backend Development", "duration": 10, "predecessors": ["B"]},
        {"id": "E", "name": "Frontend Development", "duration": 8, "predecessors": ["B", "C"]},
        {"id": "F", "name": "Integration", "duration": 4, "predecessors": ["D", "E"]},
        {"id": "G", "name": "Testing", "duration": 5, "predecessors": ["F"]},
        {"id": "H", "name": "Deployment", "duration": 2, "predecessors": ["G"]}
    ]

    # Analyze
    analyzer = CriticalPathAnalyzer(activities, unit="days")
    result = analyzer.analyze()

    print(f"\n✅ Analysis Complete!")
    print(f"   Project Duration: {result['project_duration']} days")
    print(f"   Critical Path: {' → '.join(result['critical_path'])}")

    # Export to all formats
    print("\n" + "=" * 80)
    print("GENERATING EXPORTS...")
    print("=" * 80)

    # 1. Markdown
    print("\n📄 1. Markdown Report")
    md_report = export_to_markdown(result)
    save_to_file(md_report, 'critical_path_report.md')
    print("   ✅ Saved: critical_path_report.md")
    print(f"   Preview:\n{md_report[:500]}...\n")

    # 2. Mermaid Flowchart
    print("\n🎨 2. Mermaid Flowchart")
    mermaid_chart = export_to_mermaid_flowchart(result)
    save_to_file(mermaid_chart, 'critical_path_flowchart.md')
    print("   ✅ Saved: critical_path_flowchart.md")
    print(f"   (Paste into GitHub/GitLab markdown for visualization)")

    # 3. PlantUML Gantt
    print("\n📊 3. PlantUML Gantt Diagram")
    plantuml_gantt = export_to_plantuml_gantt(result)
    save_to_file(plantuml_gantt, 'critical_path_gantt.puml')
    print("   ✅ Saved: critical_path_gantt.puml")
    print(f"   (Use PlantUML renderer to visualize)")

    # 4. HTML Report
    print("\n🌐 4. HTML Report")
    html_report = export_to_html_report(result)
    save_to_file(html_report, 'critical_path_report.html')
    print("   ✅ Saved: critical_path_report.html")
    print(f"   (Open in browser to view)")

    # 5. CSV Data
    print("\n📊 5. CSV Export")
    csv_data = export_to_csv(result)
    save_to_file(csv_data, 'critical_path_data.csv')
    print("   ✅ Saved: critical_path_data.csv")
    print(f"   (Import into Excel/Google Sheets)")

    # 6. JSON
    print("\n💾 6. JSON Data")
    json_data = JSONExporter.to_json(result)
    save_to_file(json_data, 'critical_path_data.json')
    print("   ✅ Saved: critical_path_data.json")

    print("\n" + "=" * 80)
    print("ALL EXPORTS COMPLETE!")
    print("=" * 80)
    print("\nFiles generated:")
    print("  - critical_path_report.md (Markdown report)")
    print("  - critical_path_flowchart.md (Mermaid diagram)")
    print("  - critical_path_gantt.puml (PlantUML diagram)")
    print("  - critical_path_report.html (HTML report - open in browser)")
    print("  - critical_path_data.csv (CSV for Excel)")
    print("  - critical_path_data.json (JSON data)")
    print("\n💡 Tip: Use mermaid_flowchart.md in GitHub README for visual diagram!")


if __name__ == "__main__":
    main()
