import json
from pathlib import Path

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
    skills_mcp._INDEX = skills_mcp.SkillIndex(roots=[project_root])  # type: ignore[attr-defined]


async def test_skills_list_skills_returns_paginated_results(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.ListSkillsInput()
    result = await skills_mcp.skills_list_skills(params)
    data = json.loads(result)

    assert data["total"] == 1
    assert data["count"] == 1
    assert data["items"][0]["skill_id"] == "sequential-thinking"


async def test_skills_get_skill_returns_content(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.GetSkillInput(skill_id="sequential-thinking")
    result = await skills_mcp.skills_get_skill(params)
    data = json.loads(result)

    assert data["skill_id"] == "sequential-thinking"
    assert "Sequential thinking skill" in data["description"]
    assert "# Sequential Thinking" in data["content_markdown"]


async def test_skills_search_skills_finds_matches(tmp_path: Path) -> None:
    _prepare_real_index(tmp_path)

    params = skills_mcp.SearchSkillsInput(query="Content")
    result = await skills_mcp.skills_search_skills(params)
    data = json.loads(result)

    assert data["count"] == 1
    assert data["matches"][0]["skill_id"] == "sequential-thinking"

