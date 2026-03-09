# PMBOK Automation Scripts

This folder contains Python utilities that support the `senior-pmbok-pm` skill.

## Scripts
- `artifact_mapper.py` — Resolve artifact names to the correct PT-BR/EN paths.
- `template_normalizer.py` — Validate and optionally normalize `TEMPLATE.md` files.
- `inputs_validator.py` — Validate placeholder coverage between `TEMPLATE.md` and `INPUTS.md`.
- `quality_audit.py` — Audit artifacts for version control, ownership, traceability, and placeholders.
- `workflow_checklist_generator.py` — Generate workflow checklists from `reference/workflows.md`.
- `terminology_consistency_checker.py` — Detect terminology drift across artifacts/docs.

## Output formats
All scripts support the following formats via `--format`:

- `json` (default)
- `markdown` / `md`
- `mermaid`
- `plantuml`
- `pdf`
- `txt`
- `html`

Use `--output <path>` to write to a file. For PDF output, the file extension should be `.pdf`.

## Tests
Run all tests from the `scripts` directory:

```bash
python -m unittest discover -s tests
```

## Requirements
PDF output uses `reportlab`:

```
pip install -r requirements.txt
```
