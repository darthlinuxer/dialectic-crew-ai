# Suggested Commands
- Install: `uv sync && cp .env.example .env`
- Activate venv: `source .venv/bin/activate`
- Run CLI: `uv run dialectic-crew prd "Login with 2FA"`, `uv run dialectic-crew plan`, `uv run dialectic-crew execute`, `uv run dialectic-crew self-improve --dry-run`
- Run tests: `uv run pytest --tb=short -q`
- Coverage: `uv run pytest --cov=src --cov-report=term-missing`
- Real LLM tests: `uv run pytest -m llm`
- Focused self-improve regressions: `uv run pytest tests/test_self_improve.py tests/test_self_improve_git_safety.py tests/test_self_improve_lineage.py -q`
- Focused retry-feedback regressions: `.venv/bin/python -m pytest tests/test_prd_flow.py tests/test_agents.py tests/test_self_improve.py -q`
- Linux shell utilities expected in this repo: `git`, `ls`, `cd`, `grep`, `find`, `rsync`, `rm`, `cat`.
