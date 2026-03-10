# Project Overview
- Purpose: CrewAI-powered dialectic engine for PRD generation, user-story planning, execution, verification, and guarded self-improvement.
- Core dialectic loop: Thesis → Antithesis → Synthesis → Validation.
- Dual vision system: `knowledge/VISION.md` for external project work and `internal/SELF_VISION.md` for self-evolution.
- Main layers: CLI in `src/main/cli.py`, agent factories in `src/dialectic/agents.py`, PRD flow in `src/dialectic/prd_flow.py`, planning flow in `src/planning/flow.py`, execution flow in `src/execution/`, schemas in `src/schemas.py`, self-improve orchestration in `src/main/self_improve.py`, and local skills MCP in `src/mcp/skills_mcp.py`.
- Tech stack: Python 3.10-3.13, CrewAI 1.10+, crewai-tools MCP support, Pydantic v2, pytest.
