# Senior Agile PM Budget Analyst - Python Scripts

This directory contains deterministic, expert-level Python scripts to enhance the Senior Agile PM Budget Analyst skill. All scripts are production-ready, require no external LLM calls, and use only Python standard library.

## 📋 Table of Contents

- [Overview](#overview)
- [Scripts](#scripts)
- [Multi-Format Exports](#multi-format-exports) ⭐ NEW
- [Installation](#installation)
- [Usage Examples](#usage-examples)
- [Integration with Skill](#integration-with-skill)
- [API Reference](#api-reference)

## 🎯 Overview

These scripts provide algorithmic implementations of key Agile/Scrum methodologies:

1. **Critical Path Analysis (CPM)** - Project scheduling and bottleneck identification
2. **Budget Calculator** - Story point-based budget estimation with scenarios
3. **Poker Planning** - Estimation validation and velocity tracking
4. **Gantt Chart Generator** - Timeline visualization and resource allocation
5. **Burndown/Burnup Calculator** - Sprint and release progress tracking

**Key Features:**
- ✅ No external dependencies (pure Python 3.8+)
- ✅ Deterministic algorithms (no ML/AI)
- ✅ Expert-level implementations based on PMBOK/Scrum standards
- ✅ Type hints throughout
- ✅ Comprehensive examples and documentation
- ✅ Production-ready error handling
- ✅ **Multi-format exports** (Markdown, Mermaid, PlantUML, HTML, CSV, JSON, PDF)

## 🎨 Multi-Format Exports

All analytical scripts can export results in multiple formats for stakeholder communication:

| Format | Description | Use Case |
|--------|-------------|----------|
| **Markdown** | GitHub/GitLab documents | Documentation, wikis, README files |
| **Mermaid** | Text-based diagrams | Flowcharts, Gantt, pie charts (renders in GitHub) |
| **PlantUML** | Diagram as code | Architecture docs, technical diagrams |
| **HTML** | Self-contained reports | Executive presentations, browser viewing |
| **CSV** | Tabular data | Excel/Sheets import, data analysis |
| **JSON** | Structured data | API integration, programmatic access |
| **PDF** | (via HTML) | Final reports, printing, distribution |

### Export Utilities

**`exporters.py`** - Comprehensive export utilities module:
- `MarkdownExporter` - Tables, lists, code blocks, formatting
- `MermaidExporter` - Flowcharts, Gantt charts, pie charts, line charts
- `PlantUMLExporter` - Activity diagrams, Gantt, class diagrams
- `HTMLExporter` - Styled reports with tables and sections
- `CSVExporter` - CSV generation from lists and dicts
- `JSONExporter` - Pretty-printed JSON output

### Complete Integration Examples

The **`examples/`** directory contains ready-to-run integration examples:

#### 📊 `00_complete_project_analysis.py` ⭐ START HERE
Complete end-to-end analysis using ALL scripts:
```bash
cd scripts/examples
python3 00_complete_project_analysis.py
```

Generates:
- `project_analysis_complete.md` - Full markdown report
- `project_diagrams.md` - Mermaid visualizations (paste in GitHub!)
- `project_executive_summary.html` - Executive summary (open in browser)
- `project_analysis_data.json` - Raw data for API integration

#### 🔍 `01_critical_path_exports.py`
Critical Path exports in 6 formats:
```bash
python3 01_critical_path_exports.py
```

Generates:
- Markdown report with tables
- Mermaid flowchart (network diagram)
- PlantUML Gantt diagram
- HTML report
- CSV data
- JSON data

#### 💰 `02_budget_exports.py`
Budget analysis exports:
```bash
python3 02_budget_exports.py
```

Generates:
- Markdown financial report
- Mermaid pie charts (cost breakdown)
- HTML executive summary
- CSV for Excel
- JSON for APIs

### Quick Example: Export Critical Path to Mermaid

```python
from critical_path import CriticalPathAnalyzer
from exporters import MermaidExporter, save_to_file

# Analyze
activities = [
    {"id": "A", "name": "Design", "duration": 5, "predecessors": []},
    {"id": "B", "name": "Dev", "duration": 10, "predecessors": ["A"]},
    {"id": "C", "name": "Test", "duration": 3, "predecessors": ["B"]}
]

analyzer = CriticalPathAnalyzer(activities)
result = analyzer.analyze()

# Create Mermaid flowchart
nodes = [{"id": a['id'], "label": a['name'], "critical": a['critical']}
         for a in result['activities']]
edges = [{"from": p, "to": a['id']}
         for a in result['activities'] for p in a.get('predecessors', [])]

mermaid = MermaidExporter.flowchart(nodes, edges, direction="LR")

# Save to markdown file
save_to_file(f"```mermaid\n{mermaid}\n```", "critical_path.md")
```

Paste the output markdown file into your GitHub README and the diagram will render automatically!

### 📖 Documentation

See **[examples/README.md](examples/README.md)** for:
- Detailed export examples
- Integration patterns
- Customization guide
- Format specifications

## 📦 Scripts

### 1. critical_path.py

Implements Critical Path Method (CPM) for project scheduling.

**Features:**
- Forward Pass (ES/EF calculation)
- Backward Pass (LS/LF calculation)
- Slack time calculation
- Critical path identification
- Cycle detection (DAG validation)
- Bottleneck analysis
- Optimization recommendations

**Use Cases:**
- Identify project duration
- Find critical tasks requiring attention
- Optimize resource allocation
- Detect scheduling conflicts

**Example:**
```python
from critical_path import CriticalPathAnalyzer, Activity

activities = [
    Activity(id="A", name="Design", duration=5, predecessors=[]),
    Activity(id="B", name="Development", duration=10, predecessors=["A"]),
    Activity(id="C", name="Testing", duration=3, predecessors=["B"])
]

analyzer = CriticalPathAnalyzer(activities)
result = analyzer.analyze()

print(f"Project Duration: {result['project_duration']} days")
print(f"Critical Path: {' → '.join(result['critical_path'])}")
```

**Output:**
```json
{
  "project_duration": 18,
  "critical_path": ["A", "B", "C"],
  "activities": {
    "A": {"ES": 0, "EF": 5, "LS": 0, "LF": 5, "slack": 0, "critical": true},
    "B": {"ES": 5, "EF": 15, "LS": 5, "LF": 15, "slack": 0, "critical": true},
    "C": {"ES": 15, "EF": 18, "LS": 15, "LF": 18, "slack": 0, "critical": true}
  }
}
```

---

### 2. budget_calculator.py

Calculates project budget based on story points and resource costs.

**Features:**
- Weighted average hourly rate calculation
- Base cost, overhead, fixed costs, contingency
- Scenario analysis (optimistic/realistic/pessimistic)
- Cost breakdown by role and sprint
- Comprehensive metrics

**Use Cases:**
- Project budget estimation
- Resource cost analysis
- Financial scenario planning
- ROI calculation support

**Example:**
```python
from budget_calculator import BudgetCalculator, BudgetConfig, TeamMember

team = [
    TeamMember(role="Senior Dev", count=2, hourly_rate=100),
    TeamMember(role="Junior Dev", count=3, hourly_rate=60),
    TeamMember(role="QA", count=1, hourly_rate=70)
]

config = BudgetConfig(
    total_story_points=100,
    points_per_sprint=20,
    sprint_duration_weeks=2,
    hours_per_sprint=200
)

calculator = BudgetCalculator(config, team, fixed_costs=10000)
result = calculator.calculate()

print(f"Total Budget: ${result['summary']['total_budget']:,.2f}")
print(f"Base Cost: ${result['breakdown']['base_cost']:,.2f}")
print(f"Duration: {result['project_metrics']['total_sprints']} sprints")
```

**Output:**
```json
{
  "summary": {
    "total_budget": 115000.00,
    "base_cost": 80000.00,
    "overhead": 16000.00,
    "fixed_costs": 10000.00,
    "contingency": 9000.00
  },
  "scenarios": {
    "optimistic": 97750.00,
    "realistic": 115000.00,
    "pessimistic": 143750.00
  }
}
```

---

### 3. poker_planning.py

Validates estimations and supports Agile planning activities.

**Features:**
- Fibonacci sequence validation
- Story breakdown recommendations
- Planning session analysis
- Velocity calculation
- Sprint capacity planning
- Backlog health analysis

**Use Cases:**
- Validate poker planning estimates
- Recommend story splitting
- Calculate team velocity
- Plan sprint commitments
- Analyze backlog distribution

**Example:**
```python
from poker_planning import PokerPlanningCalculator, PokerConfig, Story

config = PokerConfig(
    scale=EstimationScale.FIBONACCI,
    breakdown_threshold=13,
    points_per_sprint=20
)

calculator = PokerPlanningCalculator(config)

# Validate estimate
is_valid, msg = calculator.validate_estimate(21)
print(f"21 points: {msg}")

# Check if breakdown needed
breakdown = calculator.recommend_breakdown(21)
if breakdown['should_breakdown']:
    print(f"Recommendation: {breakdown['reason']}")
    for suggestion in breakdown['suggested_breakdown']:
        print(f"  - {suggestion}")
```

**Output:**
```
21 points: 21 is valid in fibonacci scale
Recommendation: Story exceeds threshold of 13 points. Large stories have higher uncertainty and risk.
  - Break into 3 stories of approximately 8 points each
  - This brings each story within the ideal range of 2-8 points
```

---

### 4. gantt_chart.py

Generates Gantt chart data structures and visualizations.

**Features:**
- Task scheduling with dependencies
- ASCII chart generation
- Resource allocation analysis
- Sprint view organization
- Milestone tracking
- Critical path integration

**Use Cases:**
- Project timeline visualization
- Dependency management
- Resource planning
- Stakeholder communication
- Progress tracking

**Example:**
```python
from gantt_chart import GanttChartGenerator, GanttConfig, Task, TaskType
from datetime import datetime, timedelta

config = GanttConfig(
    project_start_date=datetime(2024, 3, 1),
    sprint_duration_days=14
)

generator = GanttChartGenerator(config)

generator.add_task(Task(
    id="EPIC-001",
    name="Authentication",
    task_type=TaskType.EPIC,
    start_date=config.project_start_date,
    duration_days=14,
    status=TaskStatus.COMPLETED,
    progress_percent=100
))

chart_data = generator.generate()
print(chart_data['ascii_chart'])
```

**Output:**
```
================================================================================
TASK                           | TIMELINE
--------------------------------------------------------------------------------
                               | W1  W2  W3  W4
--------------------------------------------------------------------------------
Authentication                 | ████████████████
Product Catalog                |                 ░░░░░░░░░░░░░░░░
Shopping Cart                  |                 ░░░░░░░░░░░░░░░░
Checkout                       |                                 ░░░░░░░░
================================================================================
```

---

### 5. burndown_chart.py

Tracks sprint and release progress with burndown/burnup charts.

**Features:**
- Sprint and release tracking
- Burndown and burnup modes
- Ideal line calculation
- Velocity and trend analysis
- Scope change tracking
- Health indicators
- Forecast completion

**Use Cases:**
- Daily sprint tracking
- Release progress monitoring
- Scope change analysis
- Performance forecasting
- Team health assessment

**Example:**
```python
from burndown_chart import BurndownCalculator, BurndownConfig, ChartType
from datetime import datetime, timedelta

config = BurndownConfig(
    chart_type=ChartType.BURNDOWN,
    sprint_duration_days=10
)

calculator = BurndownCalculator(
    config=config,
    start_date=datetime(2024, 3, 1),
    initial_scope=50
)

# Add daily progress
for day in range(1, 10):
    calculator.add_data_point(
        date=datetime(2024, 3, 1) + timedelta(days=day),
        completed_points=day * 5
    )

chart_data = calculator.generate()
forecast = chart_data['forecast']
print(f"Status: {forecast['status']}")
print(f"Velocity: {forecast['current_velocity']} points/day")
print(f"Days Delta: {forecast['days_delta']:+d} days")
```

**Output:**
```
Status: On Track
Velocity: 5.0 points/day
Days Delta: 0 days
```

---

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- No external dependencies required

### Setup

From the repository root:

```bash
cd .claude/skills/senior-agile-pm-budget-analyst/scripts

# Verify Python version
python3 --version

# Test installation by running examples
python3 critical_path.py
python3 budget_calculator.py
python3 poker_planning.py
python3 gantt_chart.py
python3 burndown_chart.py
```

### Optional Dependencies

For enhanced functionality (not required):

```bash
pip install -r requirements.txt
```

---

## 💡 Usage Examples

### End-to-End Project Analysis

```python
from critical_path import CriticalPathAnalyzer, Activity
from budget_calculator import BudgetCalculator, BudgetConfig, TeamMember
from poker_planning import PokerPlanningCalculator, PokerConfig

# 1. Define project structure
activities = [
    Activity(id="E1", name="Epic 1", duration=10, predecessors=[]),
    Activity(id="E2", name="Epic 2", duration=12, predecessors=["E1"]),
    Activity(id="E3", name="Epic 3", duration=8, predecessors=["E1"]),
    Activity(id="E4", name="Epic 4", duration=6, predecessors=["E2", "E3"])
]

# 2. Calculate critical path
cpm_analyzer = CriticalPathAnalyzer(activities)
cpm_result = cpm_analyzer.analyze()

print(f"Project Duration: {cpm_result['project_duration']} days")
print(f"Critical Path: {' → '.join(cpm_result['critical_path'])}")

# 3. Calculate budget
team = [
    TeamMember(role="Tech Lead", count=1, hourly_rate=120),
    TeamMember(role="Senior Dev", count=2, hourly_rate=100),
    TeamMember(role="Developer", count=3, hourly_rate=70)
]

budget_config = BudgetConfig(
    total_story_points=120,
    points_per_sprint=20,
    sprint_duration_weeks=2,
    hours_per_sprint=200
)

budget_calc = BudgetCalculator(budget_config, team, fixed_costs=15000)
budget_result = budget_calc.calculate()

print(f"\nBudget Summary:")
print(f"  Total: ${budget_result['summary']['total_budget']:,.2f}")
print(f"  Optimistic: ${budget_result['scenarios']['optimistic']:,.2f}")
print(f"  Pessimistic: ${budget_result['scenarios']['pessimistic']:,.2f}")

# 4. Validate poker planning
poker_config = PokerConfig(points_per_sprint=20)
poker_calc = PokerPlanningCalculator(poker_config)

# Estimate completion
remaining_points = 120
estimation = poker_calc.estimate_completion(remaining_points, use_velocity=20)

print(f"\nProject Estimation:")
print(f"  Typical: {estimation['scenarios']['realistic']['duration']['sprints']} sprints")
print(f"  Best case: {estimation['scenarios']['optimistic']['duration']['sprints']} sprints")
print(f"  Worst case: {estimation['scenarios']['pessimistic']['duration']['sprints']} sprints")
```

---

## 🔌 Integration with Skill

These scripts are designed to be called from the Senior Agile PM Budget Analyst skill. The skill can invoke them via Python subprocess or import them directly.

### Example: Skill Integration Pattern

```python
import subprocess
import json

def run_critical_path_analysis(activities_json: str) -> dict:
    """
    Run CPM analysis from skill

    Args:
        activities_json: JSON string of activities

    Returns:
        Analysis results as dictionary
    """
    result = subprocess.run(
        ['python3', 'scripts/critical_path.py'],
        input=activities_json,
        capture_output=True,
        text=True
    )

    return json.loads(result.stdout)

# Use in skill workflow
activities = [
    {"id": "A", "name": "Epic 1", "duration": 14, "predecessors": []},
    {"id": "B", "name": "Epic 2", "duration": 21, "predecessors": ["A"]}
]

result = run_critical_path_analysis(json.dumps(activities))
print(f"Project will take {result['project_duration']} days")
```

---

## 📚 API Reference

### Common Data Structures

All scripts use consistent data structures:

```python
# Activity/Task
{
    "id": str,           # Unique identifier
    "name": str,         # Human-readable name
    "duration": float,   # Duration in days
    "predecessors": List[str]  # Dependencies
}

# Story Points
{
    "story_id": str,
    "points": float,
    "status": "completed" | "in_progress" | "not_started"
}

# Team Member
{
    "role": str,
    "count": int,
    "hourly_rate": float,
    "dedication_percent": float  # 0-100
}
```

### Error Handling

All scripts use custom exceptions:

```python
class ValidationError(Exception):
    """Raised when input validation fails"""
    pass

class CalculationError(Exception):
    """Raised when calculation fails"""
    pass
```

Example error handling:

```python
try:
    result = analyzer.analyze()
except ValidationError as e:
    print(f"Invalid input: {e}")
except CalculationError as e:
    print(f"Calculation failed: {e}")
```

---

## 🧪 Testing

Each script includes comprehensive examples in its `main()` function. Run any script directly to see examples:

```bash
python3 critical_path.py
python3 budget_calculator.py
python3 poker_planning.py
python3 gantt_chart.py
python3 burndown_chart.py
```

---

## 📖 References

These implementations are based on industry standards:

- **Critical Path Method**: PMBOK (Project Management Body of Knowledge)
- **Budget Calculation**: PMBOK Cost Management
- **Poker Planning**: Scrum Guide, Mike Cohn's "Agile Estimating and Planning"
- **Gantt Charts**: PMI scheduling standards
- **Burndown Charts**: Scrum Guide, Henrik Kniberg's practices

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Contributing

These scripts are part of the Senior Agile PM Budget Analyst skill. For improvements or bug reports, please refer to the main skill documentation.

---

## 🔗 Related Documentation

- [SKILL.md](../SKILL.md) - Main skill documentation
- [PROMPT.md](../PROMPT.md) - Skill prompt and instructions
- [AGILE_DOCS_PT_BR](../assets/AGILE_DOCS_PT_BR/) - Comprehensive Agile/Scrum theory (Portuguese)
- [reference/](../reference/) - Workflow and quality check references
