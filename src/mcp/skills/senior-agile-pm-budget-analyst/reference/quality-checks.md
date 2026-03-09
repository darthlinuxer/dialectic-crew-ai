# Quality Checks & Template Standard

## Template standard (required format)
A compliant `TEMPLATE.md` should include:
1. **Title** and **purpose** at the top.
2. **Documentation map** linking to `DOCUMENTACAO.md` or `DOCUMENTACAO/`.
3. **Numbered sections** with clear headings.
4. **Placeholders** using `{{snake_case}}` for inputs.
5. **Inline documentation links** for each major section.
6. **Methodology markers** indicating Scrum/BDD requirements.

If a template deviates:
- Normalize headings and numbering.
- Add a documentation map if missing.
- Convert ad-hoc placeholders to `{{...}}`.
- Preserve original content and intent.
- Keep edits minimal and traceable.

## Scrum methodology checklist

### User Stories (3 Cs principle)
- [ ] **Card**: Written description exists
- [ ] **Card**: Uses "Como [usuário], eu quero [funcionalidade] para que [benefício]" format
- [ ] **Card**: Who, What, Why are clearly defined
- [ ] **Conversation**: Collaboration notes or discussion points included
- [ ] **Conversation**: Clarifications from Product Owner documented
- [ ] **Conversation**: Technical considerations noted
- [ ] **Confirmation**: Acceptance criteria defined
- [ ] **Confirmation**: BDD format used (Given-When-Then)
- [ ] **Confirmation**: Criteria are testable and verifiable

### User Story card structure
- [ ] **ID**: Unique identifier present (e.g., US-001)
- [ ] **Title**: Short descriptive title
- [ ] **Description**: Full "Como/Quero/Para que" format
- [ ] **Acceptance Criteria**: Minimum 2-3 BDD scenarios
- [ ] **Estimation**: Story points using Fibonacci (1, 2, 3, 5, 8, 13...)
- [ ] **Estimation**: Stories > threshold are broken down
- [ ] **Priority**: High/Medium/Low assigned
- [ ] **Definition of Done**: Specific checklist present
- [ ] **Dependencies**: Linked to other stories/epics if applicable
- [ ] **Notes**: Additional context provided when needed

## BDD methodology checklist

### Given-When-Then format
- [ ] **Given** (Dado): Initial context or pre-condition clearly stated
- [ ] **When** (Quando): Action or event explicitly described
- [ ] **Then** (Então): Expected result or verification defined
- [ ] **Completeness**: All three parts present for each scenario
- [ ] **Testability**: Criteria can be verified by all stakeholders
- [ ] **Clarity**: No ambiguous language
- [ ] **Measurability**: Expected outcomes are measurable

### BDD scenario quality
- [ ] Multiple scenarios when behavior has variations
- [ ] Edge cases considered
- [ ] Error conditions addressed
- [ ] Success criteria clear
- [ ] Failure criteria clear
- [ ] Time constraints specified (when applicable)
- [ ] Quantitative measures included (when applicable)

### Example quality BDD scenario:
```
**Critério 1: Login bem-sucedido**
- **Given** (Dado): O usuário está na página de login com credenciais válidas cadastradas
- **When** (Quando): Ele insere email "user@example.com" e senha correta, e clica em "Entrar"
- **Then** (Então):
  - O sistema valida as credenciais em até 2 segundos
  - O usuário é redirecionado para o dashboard
  - A mensagem "Bem-vindo de volta!" é exibida
  - O token de sessão é criado com validade de 24 horas
```

## Poker Planning checklist

### Configuration
- [ ] Points-to-sprint ratio documented (e.g., 5 points = 2 weeks)
- [ ] Sprint duration specified
- [ ] Team velocity recorded (if known)
- [ ] Estimation scale defined (Fibonacci recommended)

### Estimation quality
- [ ] Fibonacci sequence used: 1, 2, 3, 5, 8, 13, 21...
- [ ] Stories > threshold are broken down
- [ ] Estimation reasoning documented
- [ ] Team consensus achieved
- [ ] Complexity considered
- [ ] Uncertainty reflected in estimate
- [ ] Effort (not time) estimated

### Story breakdown rules
- [ ] If story > threshold → broken into smaller cards
- [ ] Smaller cards are independently deliverable
- [ ] Smaller cards maintain business value
- [ ] Smaller cards sum to approximately original estimate
- [ ] Dependencies between broken-down cards mapped

## Budget analysis checklist

### Input parameters
- [ ] Team composition defined (roles, quantities)
- [ ] Hourly/daily rates per role documented
- [ ] Sprint duration specified
- [ ] Overhead percentage defined (typically 15-30%)
- [ ] Fixed costs identified (licenses, infrastructure)
- [ ] Currency specified

### Calculation quality
- [ ] Story points → effort hours conversion documented
- [ ] Effort hours × rates calculation shown
- [ ] Overhead added to base costs
- [ ] Fixed costs added separately
- [ ] Total project cost calculated
- [ ] Breakdown by initiative/epic/sprint provided

### Traceability
- [ ] Budget links to story points
- [ ] Story points link to user stories
- [ ] User stories link to epics
- [ ] Epics link to initiatives
- [ ] Full traceability from cost → business value

## Gantt Chart checklist

### Chart elements
- [ ] All tasks/user stories included
- [ ] Start/End dates specified
- [ ] Duration calculated correctly
- [ ] Dependencies mapped (predecessor tasks)
- [ ] Milestones marked
- [ ] Sprint boundaries shown
- [ ] Buffer time included (10-20% recommended)
- [ ] Critical path highlighted

### Dependency mapping
- [ ] Finish-to-Start dependencies identified
- [ ] Start-to-Start dependencies (if any)
- [ ] Finish-to-Finish dependencies (if any)
- [ ] External dependencies noted
- [ ] Dependency constraints documented

### Format quality
- [ ] Visual or table format provided
- [ ] Legend included
- [ ] Annotations for key points
- [ ] Readable and clear
- [ ] Exportable/shareable format

## Critical Path Analysis checklist

### Network diagram
- [ ] All tasks included
- [ ] Dependencies correctly mapped
- [ ] Earliest Start (ES) times calculated
- [ ] Earliest Finish (EF) times calculated
- [ ] Latest Start (LS) times calculated
- [ ] Latest Finish (LF) times calculated
- [ ] Slack/Float calculated (LS - ES or LF - EF)

### Critical path identification
- [ ] Longest dependent sequence identified
- [ ] Tasks with zero slack marked as critical
- [ ] Total project duration calculated
- [ ] Critical path visualized or listed
- [ ] Bottlenecks identified

### Risk assessment
- [ ] Critical tasks analyzed for risk
- [ ] Mitigation strategies proposed
- [ ] Alternative paths considered
- [ ] Resource constraints addressed
- [ ] Timeline optimization suggested

## General artifact review checklist

### Structure
- [ ] All required sections from template present
- [ ] Headings properly formatted and numbered
- [ ] Professional formatting consistent
- [ ] Tables properly formatted
- [ ] Links valid and working

### Content quality
- [ ] All placeholders filled (or justified if not)
- [ ] Content aligns with documentation guidance
- [ ] Terminology consistent across sections
- [ ] No contradictions between sections
- [ ] Specific and actionable (not vague)

### Scrum/Agile principles
- [ ] User-centric language
- [ ] Business value clear
- [ ] Iterative approach evident
- [ ] Collaboration emphasized
- [ ] Continuous improvement mindset

### Traceability
- [ ] Links between artifacts maintained
- [ ] References to related documents
- [ ] Version control information
- [ ] Change history documented
- [ ] Clear ownership defined

## Common issues to flag

### User Story issues
- Missing "Como/Quero/Para que" structure
- Vague or technical descriptions (not user-centric)
- Missing acceptance criteria
- Acceptance criteria not in BDD format
- Stories too large (> threshold) without breakdown
- Missing Definition of Done
- No priority assigned

### Estimation issues
- Not using Fibonacci sequence
- Stories > threshold not broken down
- No estimation reasoning
- Estimates are time-based (not effort-based)
- Team consensus not documented

### BDD issues
- Missing Given/When/Then structure
- Vague or ambiguous criteria
- Not testable or verifiable
- Missing edge cases
- No quantitative measures
- No time constraints where needed

### Budget issues
- Calculations not traceable to story points
- Missing team composition or rates
- No overhead included
- Fixed costs not separated
- No breakdown by initiative/epic/sprint

### Gantt/Critical Path issues
- Missing dependencies
- Unrealistic timelines
- No buffer time
- Critical path not identified
- Bottlenecks not addressed
- No risk mitigation

### General issues
- Placeholders left in final artifact without justification
- Inconsistent terminology
- No traceability between artifacts
- Document controls not updated
- Missing references
- Weak or generic content

## Quality improvement recommendations

### For User Stories:
1. Always start with user perspective: "Como [usuário]..."
2. Clarify the benefit: "para que [valor]"
3. Use concrete examples in acceptance criteria
4. Include both success and failure scenarios
5. Reference designs/wireframes when available

### For Estimations:
1. Estimate relative effort, not time
2. Consider complexity, uncertainty, and effort
3. Use team discussion to reach consensus
4. Document assumptions
5. Review and adjust based on actual velocity

### For BDD Scenarios:
1. Use specific data in Given/When/Then
2. Make Then verifiable (measurable outcomes)
3. Cover happy path and error cases
4. Include performance criteria (time, load)
5. Keep scenarios independent

### For Budget:
1. Document all assumptions
2. Include contingency (10-20%)
3. Break down by time period (sprint/month/quarter)
4. Link to business value (ROI, cost-benefit)
5. Update regularly based on actuals

### For Timelines:
1. Include buffer for unknowns
2. Map all dependencies
3. Identify critical path early
4. Plan mitigation for bottlenecks
5. Update based on actual progress

## Approval criteria

An artifact is ready for approval when:
- [ ] All quality checks passed
- [ ] No major gaps or inconsistencies
- [ ] Methodology correctly applied (Scrum/BDD)
- [ ] Estimates validated
- [ ] Budget traceable and realistic
- [ ] Timeline achievable
- [ ] Risks identified and mitigated
- [ ] Stakeholders reviewed (when applicable)
- [ ] Document controls updated
- [ ] Ready for team use

## Continuous improvement

After each artifact creation/update/review:
1. Note what worked well
2. Identify areas for improvement
3. Update templates if needed
4. Refine estimation accuracy
5. Improve collaboration processes
6. Share learnings with team
