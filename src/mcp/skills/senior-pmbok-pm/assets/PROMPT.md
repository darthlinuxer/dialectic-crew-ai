# Prompt — Auditoria e Correção de Links (PM_DOCS_PT_BR)

## Optimized Prompt

You are a senior technical editor and Markdown QA specialist.
Your task is to audit and fix internal links across **all folders** inside:

`assets/PM_DOCS_PT_BR`

### Objectives
For **every** subfolder that contains a `TEMPLATE.md`, enforce the following:

1. **Input placeholder links**
   Each input placeholder in `TEMPLATE.md` (format `{{input_variavel}}`, e.g., `{{fase_1_inicio}}`) must be linked to its corresponding entry in the local `INPUTS.md`.
   - Use proper Markdown link syntax in the target files (placeholder → INPUTS.md#<anchor>)
   - Anchor must match the correct heading or section in `INPUTS.md` (GitHub-style slug).
   - If the input appears in a table row, the placeholder itself should be the link.

2. **Documentação section links**
   Each section in `TEMPLATE.md` that contains a “Documentação” placeholder must link to the correct file in the local `DOCUMENTACAO/` folder.
   - Use proper Markdown link syntax.
   - The link target must be a valid file that exists in `DOCUMENTACAO/`.

3. **Consistency and validity**
   - Fix any missing, broken, or inconsistent links.
   - Do not alter the meaning, content, or structure beyond link fixes.
   - Preserve Portuguese language and formatting.

### Required Workflow
- Iterate **every** `TEMPLATE.md` under `PM_DOCS_PT_BR`.
- Cross-check with `INPUTS.md` and `DOCUMENTACAO/` in the **same folder**.
- Apply fixes directly in the files.

### Output Format
Return:
1. A list of edited files.

### Constraints
- Markdown links only (no raw paths).
- Paths must be relative and case-correct.
- No new content unless required for link accuracy.
- No new files, update the existing ones only.

- **Strict Validation**: if any placeholder does not map to a valid `INPUTS.md` variable name entry, provide a detailed report in the end of the run of were the inconsistencies occurred.
- **Anchor Auto-Generation**: Compute GitHub-style anchors for headers and table sections automatically.
