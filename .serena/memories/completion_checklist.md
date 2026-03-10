# Completion Checklist
- Run focused or full pytest relevant to the touched area before claiming success.
- For CrewAI flow or self-improve changes, prefer verified narrow regression suites first, then expand if risk warrants.
- Confirm dual-vision routing and artifact handoff behavior when touching PRD/planning/execution/self-improve paths.
- Keep telemetry and metrics passive; they must not break runtime behavior.
- If self-improve behavior changes, verify baseline/post-run test gating and git-safety behavior remain intact.
