# Style and Conventions
- Keep schemas in `src/schemas.py` as the single source of truth.
- Agent factories follow `create_<name>(vision_context: VisionContext) -> Agent` in `src/dialectic/agents.py`.
- CLI commands live in the Typer surface under `src/main/cli/entrypoint.py`.
- Code uses Python type hints and concise docstrings; Pydantic models are used for flow state and structured outputs.
- Prefer CrewAI native features (Memory, Knowledge, planning, reasoning, guardrails) before custom infrastructure.
- Preserve dual-vision correctness: SELF work uses `VisionContext.SELF`, project work uses `VisionContext.PROJECT`.
- Tests live in `tests/` and follow `test_<module>.py`; mocking is local to each test.
