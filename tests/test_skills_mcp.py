import json
from pathlib import Path

import pytest

from src.mcp import skills_mcp


def _prepare_real_index(tmp_path: Path) -> None:
    """Point the module-level index at a temporary skills directory."""
    project_root = tmp_path / "src" / "mcp" / "skills"
    skill_dir = project_root / "sequential-thinking"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        "name: sequential-thinking\n"
        "description: Sequential thinking skill\n"
        "---\n"
        "\n"
        "# Sequential Thinking\n"
        "Content here.\n",
        encoding="utf-8",
    )

    # Rebuild the index in the imported module
    setattr(skills_mcp, "_INDEX", skills_mcp.SkillIndex(roots=[project_root]))


@pytest.mark.anyio
async def test_skills_list_skills_returns_paginated_results(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.ListSkillsInput()
    result = await skills_mcp.skills_list_skills(params)
    data = json.loads(result)

    assert data["total"] == 1
    assert data["count"] == 1
    assert data["items"][0]["skill_id"] == "sequential-thinking"


@pytest.mark.anyio
async def test_skills_get_skill_returns_content(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.GetSkillInput(skill_id="sequential-thinking")
    result = await skills_mcp.skills_get_skill(params)
    data = json.loads(result)

    assert data["skill_id"] == "sequential-thinking"
    assert "Sequential thinking skill" in data["description"]
    assert "# Sequential Thinking" in data["content_markdown"]


@pytest.mark.anyio
async def test_skills_search_skills_finds_matches(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.SearchSkillsInput(query="Content")
    result = await skills_mcp.skills_search_skills(params)
    data = json.loads(result)

    assert data["count"] == 1
    assert data["matches"][0]["skill_id"] == "sequential-thinking"


def test_run_server_uses_streamable_http_and_sets_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummySettings:
        def __init__(self) -> None:
            self.port = 8000

    class DummyMCP:
        def __init__(self) -> None:
            self.settings = DummySettings()
            self.calls: list[str] = []

        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            _ = mount_path
            self.calls.append(transport)

    fake_mcp = DummyMCP()
    monkeypatch.setattr(skills_mcp, "mcp", fake_mcp)

    skills_mcp.run_server(
        argv=["--http"],
        environ={"SKILLS_MCP_PORT": "9100"},
    )

    assert fake_mcp.settings.port == 9100
    assert fake_mcp.calls == [skills_mcp.HTTP_TRANSPORT]


def test_run_server_falls_back_to_default_http_port(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummySettings:
        def __init__(self) -> None:
            self.port = 8000

    class DummyMCP:
        def __init__(self) -> None:
            self.settings = DummySettings()
            self.calls: list[str] = []

        def run(self, transport: str = "stdio", mount_path: str | None = None) -> None:
            _ = mount_path
            self.calls.append(transport)

    fake_mcp = DummyMCP()
    monkeypatch.setattr(skills_mcp, "mcp", fake_mcp)

    skills_mcp.run_server(
        environ={
            "SKILLS_MCP_TRANSPORT": "streamable_http",
            "SKILLS_MCP_PORT": "not-a-number",
        },
    )

    assert fake_mcp.settings.port == skills_mcp.DEFAULT_HTTP_PORT
    assert fake_mcp.calls == [skills_mcp.HTTP_TRANSPORT]

