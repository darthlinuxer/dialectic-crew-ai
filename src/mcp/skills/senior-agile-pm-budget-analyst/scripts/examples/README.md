# Export Examples

This directory contains comprehensive examples demonstrating how to use the analytical scripts with multi-format export capabilities.

## 📁 Files

### `00_complete_project_analysis.py` ⭐ START HERE
**Complete end-to-end project analysis** integrating all tools:
- Critical Path Method (CPM)
- Budget Calculation
- Poker Planning Validation
- Gantt Chart Generation
- Burndown Tracking (simulated)

**Exports:** Markdown, Mermaid, HTML, JSON

**Use when:** You want to see how all scripts work together for a complete project analysis.

```bash
cd scripts/examples
python3 00_complete_project_analysis.py
```

**Output Files:**
- `project_analysis_complete.md` - Full markdown report
- `project_diagrams.md` - Mermaid visualizations
- `project_executive_summary.html` - Executive summary (open in browser)
- `project_analysis_data.json` - Raw data

---

### `01_critical_path_exports.py`
**Critical Path Method exports** in multiple formats:
- ✅ Markdown report with tables
- ✅ Mermaid flowchart (network diagram)
- ✅ PlantUML Gantt diagram
- ✅ HTML report
- ✅ CSV data
- ✅ JSON data

```bash
python3 01_critical_path_exports.py
```

**Output Files:**
- `critical_path_report.md`
- `critical_path_flowchart.md` (Mermaid - paste in GitHub README!)
- `critical_path_gantt.puml` (PlantUML)
- `critical_path_report.html`
- `critical_path_data.csv`
- `critical_path_data.json`

---

### `02_budget_exports.py`
**Budget Analysis exports** in multiple formats:
- ✅ Markdown financial report
- ✅ Mermaid pie charts (cost breakdown)
- ✅ HTML executive summary
- ✅ CSV for Excel import
- ✅ JSON for API integration

```bash
python3 02_budget_exports.py
```

**Output Files:**
- `budget_report.md`
- `budget_charts.md` (Mermaid pie charts)
- `budget_report.html`
- `budget_data.csv` (import into Excel!)
- `budget_data.json`

---

## 🎨 Supported Export Formats

| Format | Description | Use Case |
|--------|-------------|----------|
| **Markdown** | GitHub/GitLab compatible documents | Documentation, README files, wikis |
| **Mermaid** | Text-based diagrams (flowcharts, Gantt, pie) | GitHub/GitLab rendering, Notion, Confluence |
| **PlantUML** | Diagram as code | Technical documentation, architecture docs |
| **HTML** | Self-contained web reports | Executive presentations, browser viewing |
| **CSV** | Comma-separated values | Excel, Google Sheets, data analysis |
| **JSON** | Structured data | API integration, custom processing |
| **PDF** | (via HTML conversion) | Final reports, printing, archival |

---

## 🚀 Quick Start

### 1. Run Complete Analysis
```bash
cd /path/to/scripts/examples
python3 00_complete_project_analysis.py
```

### 2. View Outputs
```bash
# Open HTML report in browser
open project_executive_summary.html

# View markdown reports
cat project_analysis_complete.md

# View diagrams (paste in GitHub)
cat project_diagrams.md
```

### 3. Customize for Your Project
Edit any example file and modify:
- Project data (epics, stories, team)
- Configuration (sprint duration, rates, etc.)
- Export formats (enable/disable specific exports)

---

## 📖 How to Use Exporters

### Import the Exporters Module
```python
from exporters import (
    MarkdownExporter,
    MermaidExporter,
    PlantUMLExporter,
    HTMLExporter,
    CSVExporter,
    JSONExporter,
    save_to_file
)
```

### Example: Create Markdown Table
```python
headers = ["Task", "Duration", "Status"]
rows = [
    ["Epic 1", "14 days", "✅ Complete"],
    ["Epic 2", "21 days", "🔄 In Progress"]
]

md_table = MarkdownExporter.table(headers, rows)
save_to_file(md_table, 'tasks.md')
```

### Example: Create Mermaid Flowchart
```python
nodes = [
    {"id": "A", "label": "Start", "shape": "rounded"},
    {"id": "B", "label": "Process", "shape": "box"},
    {"id": "C", "label": "End", "shape": "rounded"}
]

edges = [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C"}
]

flowchart = MermaidExporter.flowchart(nodes, edges)
print(f"```mermaid\n{flowchart}\n```")
```

### Example: Generate HTML Report
```python
sections = [
    {
        "heading": "Summary",
        "content": "<p>Project completed successfully!</p>"
    },
    {
        "heading": "Metrics",
        "content": HTMLExporter.table(["Metric", "Value"], [["Duration", "42 days"]])
    }
]

html = HTMLExporter.simple_report("Project Report", sections)
save_to_file(html, 'report.html')
```

---

## 💡 Integration Tips

### 1. **GitHub/GitLab Integration**
Mermaid diagrams render automatically in markdown:
```markdown
# My Project

## Timeline
```mermaid
gantt
    title Project Schedule
    section Sprint 1
    Epic 1 :done, 2024-03-01, 14d
```\`\`\`
```

### 2. **Excel Integration**
Import CSV files:
1. Open Excel
2. Data → From Text/CSV
3. Select generated `.csv` file
4. Configure delimiters
5. Import

### 3. **Confluence/Notion Integration**
Both support:
- Markdown import
- Mermaid diagrams
- HTML embed
- CSV tables

### 4. **API Integration**
Use JSON exports for programmatic access:
```python
import json

with open('project_analysis_data.json') as f:
    data = json.load(f)

# Use in your application
print(f"Budget: ${data['budget']['summary']['total_budget']}")
```

### 5. **PDF Generation**
Convert HTML to PDF using system tools:
```bash
# Using wkhtmltopdf
wkhtmltopdf project_executive_summary.html project_report.pdf

# Using browser (Chrome/Chromium)
chromium --headless --print-to-pdf=project_report.pdf project_executive_summary.html
```

---

## 🔧 Customization

### Add Custom Export Format
Create new exporter in `exporters.py`:

```python
class CustomExporter:
    @staticmethod
    def to_custom_format(data: dict) -> str:
        # Your custom format logic
        return formatted_string
```

Then use in examples:
```python
from exporters import CustomExporter

custom_output = CustomExporter.to_custom_format(result)
save_to_file(custom_output, 'output.custom')
```

### Modify Export Styling
Edit HTML/CSS in `HTMLExporter.simple_report()` in `exporters.py`.

### Add New Diagram Types
Extend `MermaidExporter` or `PlantUMLExporter` classes.

---

## 📚 References

- Mermaid Documentation
- PlantUML Documentation
- GitHub Flavored Markdown
- HTML5 Specification

---

## 🤝 Contributing

To add new export examples:
1. Create `0X_toolname_exports.py`
2. Follow existing patterns
3. Document in this README
4. Test all export formats

---

## 📄 License

MIT License - See parent directory LICENSE

---

**Generated by Senior Agile PM Budget Analyst Skill**
