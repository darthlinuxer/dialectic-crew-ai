# Workflows

Use the following workflows after selecting command and artifact(s).

## Create workflow
Copy this checklist into your response and track progress:

```
Create Progress:
- [ ] Confirm artifact(s)
- [ ] Read TEMPLATE.md, INPUTS.md, DOCUMENTACAO
- [ ] Validate/normalize template format
- [ ] Map inputs from user context to placeholders
- [ ] create|update|refactor artifact following TEMPLATE.md 
- [ ] Run quality checks
```

Steps:
1. **Read sources** for each artifact.
2. **Normalize template** if needed (see `reference/quality-checks.md`).
3. **Map inputs** from `INPUTS.md` and user context.
4. **Fill placeholders** using the template. Preserve headings and structure.
5. **If inputs are missing**: infer from context → ask independence level → proceed if high and sources exist.
6. **Output** the completed artifact and list assumptions.

## Update workflow
Copy this checklist into your response and track progress:

```
Update Progress:
- [ ] Confirm artifact(s) and update scope
- [ ] Read existing document + TEMPLATE.md + specific files in DOCUMENTACAO depending on the section being worked on
- [ ] Validate/normalize template format (see `reference/quality-checks.md`)
- [ ] Map changes to template sections
- [ ] Apply updates and refresh controls/history
- [ ] Run quality checks
```

Steps:
1. **Locate the existing artifact** (ask for the file if not provided).
2. **Read template and documentation** to confirm target structure.
3. **Apply updates** to the relevant sections; keep format consistent with the template.
4. **Update document controls** (history, version, approvals) in `senior-pmbok-pm/assets/PM_DOCS_PT_BR/00_CONTROLES_DO_DOCUMENTO` if required.
5. **Output** the updated artifact + change summary.

## Review workflow
Copy this checklist into your response and track progress:

```
Review Progress:
- [ ] Confirm artifact(s) and review criteria
- [ ] Read existing document + TEMPLATE.md + DOCUMENTACAO
- [ ] Identify gaps and inconsistencies
- [ ] Recommend fixes / provide revised content
- [ ] Run quality checks
```

Steps:
1. **Compare** the document to the template structure and required inputs.
2. **Check** alignment with specific files in DOCUMENTACAO guidance and PMBOK intent.
3. **List gaps** (missing sections, weak content, inconsistent terms, missing references).
4. **Provide fixes** or an updated draft if requested.
5. **Summarize** risks and next steps.

## Input sufficiency decision
1. Infer from **user-provided context** and **project sources**.
2. If still missing, **ask for independence level** (low/medium/high).
3. If **high** and a **project source is available**, proceed with best assumptions and label them.
4. If no project source exists, request it before proceeding.
