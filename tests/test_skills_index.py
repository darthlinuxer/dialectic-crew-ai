from pathlib import Path

from src.mcp.skills_index import SkillIndex, SkillSource


def _write_skill(tmp_path: Path, name: str, with_front_matter: bool = True) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    if with_front_matter:
        skill_file.write_text(
            "---\n"
            f"name: {name}-display\n"
            f"description: Description for {name}\n"
            "---\n"
            "\n"
            f"# {name}\n",
            encoding="utf-8",
        )
    else:
        skill_file.write_text("# Title only\n", encoding="utf-8")
    return skill_file


def test_skill_index_discovers_skills_and_parses_front_matter(tmp_path: Path) -> None:
    project_root = tmp_path / "src" / "mcp" / "skills"
    seq = _write_skill(project_root, "sequential-thinking")
    using = _write_skill(project_root, "using-superpowers", with_front_matter=False)

    index = SkillIndex(roots=[project_root])
    skills = index.all_skills()

    assert {s.skill_id for s in skills} == {
        "sequential-thinking",
        "using-superpowers",
    }

    seq_meta = index.get("sequential-thinking")
    assert seq_meta is not None
    assert seq_meta.display_name == "sequential-thinking-display"
    assert "Description for sequential-thinking" in seq_meta.description
    assert seq_meta.path == seq
    assert seq_meta.source == SkillSource.PROJECT

    using_meta = index.get("using-superpowers")
    assert using_meta is not None
    assert using_meta.display_name == "using-superpowers"
    assert using_meta.description == ""
    assert using_meta.path == using


def test_skill_index_search_filters_by_query_and_source(tmp_path: Path) -> None:
    project_root = tmp_path / "src" / "mcp" / "skills"
    agents_root = tmp_path / ".agents" / "skills"

    _write_skill(project_root, "sequential-thinking")
    _write_skill(agents_root, "test-driven-development")

    index = SkillIndex(roots=[project_root, agents_root])

    results = index.search(query="sequential")
    assert len(results) == 1
    assert results[0].skill_id == "sequential-thinking"

    results = index.search(source=SkillSource.AGENTS)
    assert len(results) == 1
    assert results[0].skill_id == "test-driven-development"
