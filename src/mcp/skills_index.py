from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional, Dict


class SkillSource(str, Enum):
    PROJECT = "project"
    AGENTS = "agents"
    CURSOR = "cursor"


@dataclass(frozen=True)
class SkillMetadata:
    skill_id: str
    display_name: str
    description: str
    path: Path
    source: SkillSource


class SkillIndex:
    """Filesystem-backed index of available skills.

    Skills are discovered by scanning configured root directories for
    `*/SKILL.md` files. The directory name becomes the `skill_id`.
    """

    def __init__(self, roots: Iterable[Path]) -> None:
        self._roots: List[Path] = [root for root in roots]
        self._skills_by_id: Dict[str, SkillMetadata] = {}
        self._scan()

    @staticmethod
    def _infer_source(root: Path) -> SkillSource:
        root_str = str(root)
        if "src/mcp/skills" in root_str:
            return SkillSource.PROJECT
        if ".agents/skills" in root_str:
            return SkillSource.AGENTS
        if ".cursor/skills-cursor" in root_str:
            return SkillSource.CURSOR
        return SkillSource.PROJECT

    @staticmethod
    def _parse_front_matter(text: str) -> Dict[str, str]:
        """Parse very small YAML-like front matter block if present."""
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            return {}

        result: Dict[str, str] = {}
        for line in lines[1:]:
            stripped = line.strip()
            if stripped == "---":
                break
            if ":" not in stripped:
                continue
            key, value = stripped.split(":", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
        return result

    def _scan(self) -> None:
        """Scan all roots and build an in-memory index."""
        skills: Dict[str, SkillMetadata] = {}

        for root in self._roots:
            if not root.exists():
                continue
            for skill_file in root.rglob("SKILL.md"):
                skill_dir = skill_file.parent
                skill_id = skill_dir.name
                try:
                    content = skill_file.read_text(encoding="utf-8")
                except OSError:
                    continue

                front_matter = self._parse_front_matter(content)
                display_name = front_matter.get("name", skill_id)
                description = front_matter.get("description", "").strip()
                source = self._infer_source(root)

                # Last one wins if duplicates exist; roots ordering controls precedence.
                skills[skill_id] = SkillMetadata(
                    skill_id=skill_id,
                    display_name=display_name,
                    description=description,
                    path=skill_file,
                    source=source,
                )

        self._skills_by_id = dict(sorted(skills.items(), key=lambda item: item[0]))

    def all_skills(self) -> List[SkillMetadata]:
        return list(self._skills_by_id.values())

    def get(self, skill_id: str) -> Optional[SkillMetadata]:
        return self._skills_by_id.get(skill_id)

    def search(
        self,
        query: Optional[str] = None,
        source: Optional[SkillSource] = None,
    ) -> List[SkillMetadata]:
        items = self._skills_by_id.values()
        if query:
            q = query.lower()
            items = [
                s
                for s in items
                if q in s.skill_id.lower()
                or q in s.display_name.lower()
                or q in s.description.lower()
            ]
        if source is not None:
            items = [s for s in items if s.source == source]
        return list(items)

