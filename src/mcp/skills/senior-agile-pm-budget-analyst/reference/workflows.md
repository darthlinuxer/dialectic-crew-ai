# Workflows

Use the following workflows after selecting command and artifact(s).

## Analyze workflow (complete project breakdown)
Copy this checklist into your response and track progress:

```
Analyze Progress:
- [ ] Confirm project scope and objectives
- [ ] Configure poker planning parameters (points-to-sprint ratio)
- [ ] Gather team composition and rates (for budget)
- [ ] Read project requirements and context
- [ ] Create initiatives breakdown
- [ ] Break initiatives into epics
- [ ] Detail epics into user stories with BDD format
- [ ] Estimate all user stories using poker planning
- [ ] Break down stories > threshold
- [ ] Calculate project budget
- [ ] Generate Gantt chart with dependencies
- [ ] Perform critical path analysis
- [ ] Run quality checks
- [ ] Provide summary with recommendations
```

Steps:
1. **Gather configuration**:
   - Poker planning ratio (default: 5 points = 2 weeks)
   - Team composition (roles, quantities)
   - Hourly/daily rates per role
   - Sprint duration
   - Currency for budget

2. **Understand project**:
   - Read project description, objectives, requirements
   - Identify stakeholders and users
   - Clarify scope and constraints

3. **Create hierarchy**:
   - **Initiatives**: High-level strategic goals (3-10 initiatives typically)
   - **Epics**: Major features per initiative (3-8 epics per initiative)
   - **User Stories**: Detailed cards per epic (5-20 stories per epic)

4. **Detail user stories**:
   - Use "Como/Quero/Para que" format
   - Add BDD acceptance criteria (Given-When-Then)
   - Include Definition of Done
   - Add dependencies and notes

5. **Estimate with poker planning**:
   - Use Fibonacci sequence (1, 2, 3, 5, 8, 13...)
   - Document estimation reasoning
   - Break down stories > threshold

6. **Calculate budget**:
   - Total story points → effort hours
   - Effort hours × rates → costs
   - Add overhead (15-30%)
   - Breakdown by initiative/epic/sprint

7. **Create timeline**:
   - Gantt chart with sprint-based schedule
   - Map dependencies
   - Identify milestones

8. **Critical path analysis**:
   - Find longest dependent sequence
   - Calculate slack times
   - Identify bottlenecks
   - Recommend optimizations

9. **Quality checks**: Verify all artifacts meet standards

10. **Output**:
    - Complete artifact set
    - Budget summary
    - Timeline visualization
    - Critical path report
    - Recommendations and next steps

## Create workflow (single artifact)
Copy this checklist into your response and track progress:

```
Create Progress:
- [ ] Confirm artifact(s)
- [ ] Configure parameters (poker planning, team, rates if needed)
- [ ] Read TEMPLATE.md, INPUTS.md, DOCUMENTACAO
- [ ] Validate/normalize template format
- [ ] Map inputs from user context to placeholders
- [ ] Apply Scrum best practices (3 Cs for user stories)
- [ ] Apply BDD format for acceptance criteria (Given-When-Then)
- [ ] Validate estimations (poker planning, Fibonacci)
- [ ] Create/update artifact following TEMPLATE.md
- [ ] Run quality checks
```

Steps:
1. **Read sources** for each artifact (template, inputs, documentation).
2. **Configure parameters** if needed (poker planning, team composition, rates).
3. **Normalize template** if needed (see `reference/quality-checks.md`).
4. **Map inputs** from `INPUTS.md` and user context.
5. **Apply methodology**:
   - For user stories: 3 Cs (Card, Conversation, Confirmation)
   - For acceptance criteria: BDD (Given-When-Then)
   - For estimations: Poker planning with Fibonacci
6. **Fill placeholders** using the template. Preserve headings and structure.
7. **Break down large items**: If stories > threshold, break into smaller cards.
8. **If inputs are missing**: infer from context → ask independence level → proceed if high and sources exist.
9. **Output** the completed artifact and list assumptions.

## Update workflow
Copy this checklist into your response and track progress:

```
Update Progress:
- [ ] Confirm artifact(s) and update scope
- [ ] Read existing document + TEMPLATE.md + specific DOCUMENTACAO files
- [ ] Validate/normalize template format
- [ ] Map changes to template sections
- [ ] Apply Scrum/BDD best practices
- [ ] Recalculate estimations/budget if needed
- [ ] Apply updates and refresh controls/history
- [ ] Update dependent artifacts (e.g., if epic changes, update linked stories)
- [ ] Run quality checks
```

Steps:
1. **Locate the existing artifact** (ask for the file if not provided).
2. **Read template and documentation** to confirm target structure.
3. **Understand changes**:
   - What needs to be updated?
   - Impact on dependent artifacts?
   - Need to recalculate estimates/budget?
4. **Apply updates** to the relevant sections; keep format consistent with the template.
5. **Ensure consistency**:
   - User stories still follow "Como/Quero/Para que"
   - Acceptance criteria use Given-When-Then
   - Estimations are valid (Fibonacci, < threshold)
6. **Update dependent artifacts**:
   - If epic changes, check linked user stories
   - If estimates change, update budget
   - If timeline changes, update Gantt and critical path
7. **Update document controls** (history, version, last modified).
8. **Output** the updated artifact + change summary + impact analysis.

## Review workflow
Copy this checklist into your response and track progress:

```
Review Progress:
- [ ] Confirm artifact(s) and review criteria
- [ ] Read existing document + TEMPLATE.md + DOCUMENTACAO
- [ ] Check Scrum best practices compliance (3 Cs)
- [ ] Verify BDD format (Given-When-Then) in acceptance criteria
- [ ] Validate poker planning estimates (Fibonacci, threshold)
- [ ] Check user story format ("Como/Quero/Para que")
- [ ] Verify Definition of Done completeness
- [ ] Check dependencies and traceability
- [ ] Identify gaps and inconsistencies
- [ ] Validate budget calculations (if applicable)
- [ ] Check Gantt/critical path accuracy (if applicable)
- [ ] Recommend fixes / provide revised content
- [ ] Run quality checks
```

Steps:
1. **Compare** the document to the template structure and required inputs.
2. **Check Scrum methodology**:
   - User stories use proper format
   - 3 Cs are present (Card, Conversation, Confirmation)
   - Definition of Done is clear
3. **Check BDD methodology**:
   - Acceptance criteria use Given-When-Then
   - Scenarios are testable and verifiable
   - Multiple scenarios when needed
4. **Check estimations**:
   - Fibonacci sequence used
   - Stories > threshold are broken down
   - Estimation reasoning documented
5. **Check dependencies**:
   - Links between initiatives → epics → stories
   - Dependencies mapped in Gantt
   - Critical path identified
6. **Check budget**:
   - Calculations traceable to story points
   - Rates and overhead documented
   - Breakdown by initiative/epic/sprint
7. **List gaps** (missing sections, weak content, inconsistent terms, missing references).
8. **Provide fixes** or an updated draft if requested.
9. **Summarize** risks and next steps.

## Input sufficiency decision
1. Infer from **user-provided context** and **project sources**.
2. If still missing, **ask for independence level** (low/medium/high).
3. If **high** and a **project source is available**, proceed with best assumptions and label them.
4. If no project source exists, request it before proceeding.
5. **ALWAYS ask for poker planning configuration** at the start (points-to-sprint ratio).

## Configuration questions (ask at start when needed)

For analysis, create, or estimation workflows, ask:

1. **Poker planning configuration**:
   - "Qual a relação entre pontos e sprint? (Padrão: 5 pontos = 1 sprint de 2 semanas)"
   - "What is the points-to-sprint ratio? (Default: 5 points = 1 sprint of 2 weeks)"

2. **Team composition** (for budget):
   - "Qual a composição da equipe? (Ex: 3 Devs, 1 QA, 1 Designer)"
   - "What is the team composition? (Ex: 3 Devs, 1 QA, 1 Designer)"

3. **Rates** (for budget):
   - "Quais as taxas horárias/diárias por função?"
   - "What are the hourly/daily rates per role?"

4. **Sprint duration**:
   - "Qual a duração do sprint? (Padrão: 2 semanas)"
   - "What is the sprint duration? (Default: 2 weeks)"

5. **Team velocity** (if known):
   - "Qual a velocidade atual da equipe? (Pontos por sprint)"
   - "What is the current team velocity? (Points per sprint)"

## Python script workflow (when needed)

For Gantt charts, critical path, or complex budget analysis:

1. **Prepare data**:
   - Extract tasks, dependencies, durations from artifacts
   - Organize in pandas DataFrame

2. **Generate code**:
   - Import necessary libraries (matplotlib, networkx, pandas)
   - Add clear comments
   - Include error handling

3. **Create visualizations**:
   - Gantt chart: matplotlib with date formatting
   - Critical path: networkx for network diagram
   - Budget: tables and charts

4. **Output**:
   - Python script (runnable)
   - Visual output (chart/diagram)
   - Text analysis (findings, recommendations)

5. **Documentation**:
   - How to run the script
   - Required libraries
   - Input data format
   - Output interpretation

## Quality assurance (all workflows)

Before completing any workflow, verify:

- [ ] All mandatory sections are present
- [ ] User stories use "Como/Quero/Para que" format
- [ ] Acceptance criteria use BDD Given-When-Then
- [ ] Story points use Fibonacci sequence
- [ ] Stories > threshold are broken down
- [ ] Dependencies are mapped
- [ ] Definition of Done is specific
- [ ] Budget is traceable to story points
- [ ] Gantt includes dependencies and milestones
- [ ] Critical path is identified
- [ ] Traceability: initiatives → epics → user stories
- [ ] Document controls updated (version, date, history)

## Common workflow sequences

### Complete project analysis:
1. Analyze → 2. Create Iniciativas → 3. Create Épicos → 4. Create User Stories → 5. Poker Planning → 6. Create Backlog → 7. Create Orçamento → 8. Create Gantt → 9. Create Caminho Crítico

### Sprint preparation:
1. Review Backlog → 2. Sprint Planning → 3. Update estimations if needed

### Budget recalculation:
1. Update User Stories → 2. Update Poker Planning → 3. Recalculate Orçamento → 4. Update Gantt if timeline changes

### Continuous improvement:
1. Sprint execution → 2. Velocity & Burndown tracking → 3. Retrospectiva → 4. Update Backlog priorities → 5. Adjust estimates based on learnings
