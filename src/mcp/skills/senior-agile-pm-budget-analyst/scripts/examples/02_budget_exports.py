#!/usr/bin/env python3
"""
Budget Calculator - Multi-Format Export Examples

Demonstrates how to use budget_calculator.py with various export formats:
- Markdown financial reports
- Mermaid pie charts (cost breakdown)
- HTML executive summaries
- CSV for Excel analysis
- JSON for API integration

Author: Senior Agile PM Budget Analyst Skill
License: MIT
"""

import sys
sys.path.append('..')

from budget_calculator import BudgetCalculator, BudgetConfig, TeamMember
from exporters import (
    MarkdownExporter, MermaidExporter, HTMLExporter,
    CSVExporter, JSONExporter, save_to_file
)
from datetime import datetime


def export_to_markdown(result: dict) -> str:
    """Export budget analysis to Markdown format"""
    md = MarkdownExporter

    lines = []
    lines.append(md.heading("Project Budget Analysis", 1))
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    # Executive Summary
    lines.append(md.heading("Executive Summary", 2))
    summary = result['summary']
    lines.append(f"- **Total Budget**: ${summary['total_budget']:,.2f}")
    lines.append(f"- **Base Cost**: ${summary['base_cost']:,.2f}")
    lines.append(f"- **Overhead**: ${summary['overhead']:,.2f} ({summary['overhead_percentage']:.0f}%)")
    lines.append(f"- **Fixed Costs**: ${summary['fixed_costs']:,.2f}")
    lines.append(f"- **Contingency**: ${summary['contingency']:,.2f} ({summary['contingency_percentage']:.0f}%)")
    lines.append("")

    # Scenario Analysis
    lines.append(md.heading("Scenario Analysis", 2))
    scenarios = result['scenarios']
    scenario_headers = ["Scenario", "Budget", "Variance"]
    scenario_rows = [
        ["Optimistic (-15%)", f"${scenarios['optimistic']:,.2f}", f"-${summary['total_budget'] - scenarios['optimistic']:,.2f}"],
        ["Realistic (Baseline)", f"${scenarios['realistic']:,.2f}", "$0.00"],
        ["Pessimistic (+25%)", f"${scenarios['pessimistic']:,.2f}", f"+${scenarios['pessimistic'] - summary['total_budget']:,.2f}"]
    ]
    lines.append(md.table(scenario_headers, scenario_rows))
    lines.append("")

    # Cost Breakdown by Role
    lines.append(md.heading("Cost Breakdown by Role", 2))
    breakdown = result['breakdown']['by_role']
    role_headers = ["Role", "Hours", "Rate", "Cost", "% of Total"]
    role_rows = []
    for role_name, role_data in breakdown.items():
        pct = (role_data['cost'] / summary['base_cost'] * 100) if summary['base_cost'] > 0 else 0
        role_rows.append([
            role_name,
            f"{role_data['total_hours']:,.0f}",
            f"${role_data['hourly_rate']:.2f}",
            f"${role_data['cost']:,.2f}",
            f"{pct:.1f}%"
        ])
    lines.append(md.table(role_headers, role_rows))
    lines.append("")

    # Cost by Sprint
    lines.append(md.heading("Cost per Sprint", 2))
    sprint_breakdown = result['breakdown']['by_sprint']
    sprint_headers = ["Sprint", "Points", "Cost"]
    sprint_rows = [[f"Sprint {s['sprint_number']}", s['story_points'], f"${s['cost']:,.2f}"]
                   for s in sprint_breakdown]
    lines.append(md.table(sprint_headers, sprint_rows))
    lines.append("")

    # Project Metrics
    lines.append(md.heading("Project Metrics", 2))
    metrics = result['project_metrics']
    metrics_rows = [
        ["Metric", "Value"],
        ["Total Story Points", metrics['total_story_points']],
        ["Total Sprints", metrics['total_sprints']],
        ["Total Hours", f"{metrics['total_hours']:,.0f}"],
        ["Cost per Point", f"${metrics['cost_per_point']:,.2f}"],
        ["Cost per Sprint", f"${metrics['cost_per_sprint']:,.2f}"],
        ["Cost per Hour", f"${metrics['cost_per_hour']:,.2f}"]
    ]
    lines.append(md.table(metrics_rows[0], metrics_rows[1:]))

    return '\n'.join(lines)


def export_to_mermaid_pie(result: dict) -> str:
    """Export budget breakdown to Mermaid pie chart"""
    # Cost breakdown pie chart
    breakdown = result['breakdown']['by_role']
    data = {role: role_data['cost'] for role, role_data in breakdown.items()}

    pie_chart = MermaidExporter.pie_chart("Budget Breakdown by Role", data)

    # Also create budget composition pie
    summary = result['summary']
    composition_data = {
        "Base Cost": summary['base_cost'],
        "Overhead": summary['overhead'],
        "Fixed Costs": summary['fixed_costs'],
        "Contingency": summary['contingency']
    }

    composition_pie = MermaidExporter.pie_chart("Budget Composition", composition_data)

    return f"## Cost Breakdown\n\n```mermaid\n{pie_chart}\n```\n\n## Budget Composition\n\n```mermaid\n{composition_pie}\n```"


def export_to_html_report(result: dict) -> str:
    """Export budget analysis to HTML report"""
    sections = []

    # Executive Summary
    summary = result['summary']
    summary_content = f"""
    <div style="background: #e8f4f8; padding: 20px; border-radius: 5px; margin: 20px 0;">
        <h3>Budget Summary</h3>
        <table style="border: none;">
            <tr style="border: none; background: transparent;">
                <td style="border: none;"><strong>Total Budget:</strong></td>
                <td style="border: none; text-align: right; font-size: 1.5em; color: #2c3e50;">
                    ${summary['total_budget']:,.2f}
                </td>
            </tr>
        </table>
        <hr>
        <ul style="list-style: none; padding: 0;">
            <li>📊 Base Cost: ${summary['base_cost']:,.2f}</li>
            <li>⚙️ Overhead ({summary['overhead_percentage']:.0f}%): ${summary['overhead']:,.2f}</li>
            <li>🏢 Fixed Costs: ${summary['fixed_costs']:,.2f}</li>
            <li>🛡️ Contingency ({summary['contingency_percentage']:.0f}%): ${summary['contingency']:,.2f}</li>
        </ul>
    </div>
    """
    sections.append({"heading": "Executive Summary", "content": summary_content})

    # Scenario Analysis
    scenarios = result['scenarios']
    scenario_headers = ["Scenario", "Budget", "Variance from Baseline"]
    scenario_rows = [
        ["🟢 Optimistic (-15%)", f"${scenarios['optimistic']:,.2f}", f"-${summary['total_budget'] - scenarios['optimistic']:,.2f}"],
        ["🟡 Realistic", f"${scenarios['realistic']:,.2f}", "$0.00"],
        ["🔴 Pessimistic (+25%)", f"${scenarios['pessimistic']:,.2f}", f"+${scenarios['pessimistic'] - summary['total_budget']:,.2f}"]
    ]
    scenario_table = HTMLExporter.table(scenario_headers, scenario_rows)
    sections.append({"heading": "Scenario Analysis", "content": scenario_table})

    # Cost Breakdown
    breakdown = result['breakdown']['by_role']
    role_headers = ["Role", "Total Hours", "Hourly Rate", "Total Cost", "% of Base"]
    role_rows = []
    for role_name, role_data in breakdown.items():
        pct = (role_data['cost'] / summary['base_cost'] * 100) if summary['base_cost'] > 0 else 0
        role_rows.append([
            role_name,
            f"{role_data['total_hours']:,.0f}",
            f"${role_data['hourly_rate']:.2f}",
            f"${role_data['cost']:,.2f}",
            f"{pct:.1f}%"
        ])
    role_table = HTMLExporter.table(role_headers, role_rows)
    sections.append({"heading": "Cost Breakdown by Role", "content": role_table})

    return HTMLExporter.simple_report("Project Budget Analysis", sections)


def export_to_csv(result: dict) -> str:
    """Export budget data to CSV format"""
    # Main budget summary
    summary_csv = "=== BUDGET SUMMARY ===\n"
    summary_csv += CSVExporter.dict_to_csv([result['summary']])

    # Cost by role
    summary_csv += "\n=== COST BY ROLE ===\n"
    role_data = []
    for role_name, role_info in result['breakdown']['by_role'].items():
        role_data.append({
            'Role': role_name,
            'Total Hours': role_info['total_hours'],
            'Hourly Rate': role_info['hourly_rate'],
            'Total Cost': role_info['cost']
        })
    summary_csv += CSVExporter.dict_to_csv(role_data)

    # Cost by sprint
    summary_csv += "\n=== COST BY SPRINT ===\n"
    summary_csv += CSVExporter.dict_to_csv(result['breakdown']['by_sprint'])

    # Scenarios
    summary_csv += "\n=== SCENARIO ANALYSIS ===\n"
    scenarios = result['scenarios']
    scenario_data = [
        {'Scenario': 'Optimistic', 'Budget': scenarios['optimistic']},
        {'Scenario': 'Realistic', 'Budget': scenarios['realistic']},
        {'Scenario': 'Pessimistic', 'Budget': scenarios['pessimistic']}
    ]
    summary_csv += CSVExporter.dict_to_csv(scenario_data)

    return summary_csv


def main():
    """Demonstrate all export formats for Budget Analysis"""

    print("=" * 80)
    print("BUDGET ANALYSIS - MULTI-FORMAT EXPORT EXAMPLES")
    print("=" * 80)

    # Sample project configuration
    team = [
        TeamMember(role="Tech Lead", count=1, hourly_rate=120, dedication_percent=100),
        TeamMember(role="Senior Developer", count=2, hourly_rate=100, dedication_percent=100),
        TeamMember(role="Developer", count=3, hourly_rate=70, dedication_percent=100),
        TeamMember(role="QA Engineer", count=2, hourly_rate=65, dedication_percent=80),
        TeamMember(role="Scrum Master", count=1, hourly_rate=90, dedication_percent=50)
    ]

    config = BudgetConfig(
        total_story_points=120,
        points_per_sprint=20,
        sprint_duration_weeks=2,
        hours_per_sprint=320,  # Team capacity
        overhead_percentage=0.20,
        contingency_percentage=0.15
    )

    fixed_costs = 25000  # Infrastructure, licenses, etc.

    # Calculate budget
    calculator = BudgetCalculator(config, team, fixed_costs)
    result = calculator.calculate()

    print(f"\n✅ Analysis Complete!")
    print(f"   Total Budget: ${result['summary']['total_budget']:,.2f}")
    print(f"   Total Sprints: {result['project_metrics']['total_sprints']}")

    # Export to all formats
    print("\n" + "=" * 80)
    print("GENERATING EXPORTS...")
    print("=" * 80)

    # 1. Markdown
    print("\n📄 1. Markdown Report")
    md_report = export_to_markdown(result)
    save_to_file(md_report, 'budget_report.md')
    print("   ✅ Saved: budget_report.md")

    # 2. Mermaid Pie Charts
    print("\n🎨 2. Mermaid Pie Charts")
    mermaid_charts = export_to_mermaid_pie(result)
    save_to_file(mermaid_charts, 'budget_charts.md')
    print("   ✅ Saved: budget_charts.md")

    # 3. HTML Report
    print("\n🌐 3. HTML Report")
    html_report = export_to_html_report(result)
    save_to_file(html_report, 'budget_report.html')
    print("   ✅ Saved: budget_report.html")

    # 4. CSV Data
    print("\n📊 4. CSV Export")
    csv_data = export_to_csv(result)
    save_to_file(csv_data, 'budget_data.csv')
    print("   ✅ Saved: budget_data.csv")

    # 5. JSON
    print("\n💾 5. JSON Data")
    json_data = JSONExporter.to_json(result)
    save_to_file(json_data, 'budget_data.json')
    print("   ✅ Saved: budget_data.json")

    print("\n" + "=" * 80)
    print("ALL EXPORTS COMPLETE!")
    print("=" * 80)
    print("\nFiles generated:")
    print("  - budget_report.md (Markdown report)")
    print("  - budget_charts.md (Mermaid pie charts)")
    print("  - budget_report.html (HTML executive summary)")
    print("  - budget_data.csv (CSV for Excel)")
    print("  - budget_data.json (JSON data)")
    print("\n💡 Tip: Import budget_data.csv into Excel for further analysis!")


if __name__ == "__main__":
    main()
