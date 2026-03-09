from __future__ import annotations

from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

from .skills_index import SkillIndex, SkillSource, SkillMetadata


class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"


class ListSkillsInput(BaseModel):
    """Input model for listing available skills."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    query: Optional[str] = Field(
        default=None,
        description="Optional case-insensitive substring filter applied to skill id, display name, and description.",
        min_length=1,
        max_length=200,
    )
    source: Optional[SkillSource] = Field(
        default=None,
        description='Optional source filter: "project", "agents", or "cursor".',
    )
    limit: Optional[int] = Field(
        default=50,
        description="Maximum number of skills to return (1-100).",
        ge=1,
        le=100,
    )
    offset: Optional[int] = Field(
        default=0,
        description="Number of skills to skip for pagination (0+).",
        ge=0,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for structured data, 'markdown' for human-readable summary.",
    )


class GetSkillInput(BaseModel):
    """Input model for fetching a single skill."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    skill_id: str = Field(
        ...,
        description="Identifier of the skill (directory name, e.g., 'sequential-thinking').",
        min_length=1,
        max_length=200,
    )
    include_metadata: bool = Field(
        default=True,
        description="Whether to include metadata (source, description, path) in the JSON response.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for structured data, 'markdown' for human-readable content.",
    )


class SearchSkillsInput(BaseModel):
    """Input model for full-text search across skill contents."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    query: str = Field(
        ...,
        description="Search string to match within SKILL.md content.",
        min_length=2,
        max_length=200,
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum number of matches to return (1-100).",
        ge=1,
        le=100,
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description="Output format: 'json' for structured data, 'markdown' for human-readable summary.",
    )


ROOTS: List[Path] = [
    Path("src/mcp/skills").resolve(),
    Path.home() / ".agents" / "skills",
    Path.home() / ".cursor" / "skills-cursor",
]

_INDEX = SkillIndex(roots=ROOTS)

mcp = FastMCP("skills_mcp")


def _skill_to_dict(skill: SkillMetadata) -> Dict[str, Any]:
    data = asdict(skill)
    data["path"] = str(skill.path)
    data["source"] = skill.source.value
    return data


@mcp.tool(
    name="skills_list_skills",
    annotations={
        "title": "List available skills",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def skills_list_skills(params: ListSkillsInput) -> str:
    """List available skills discovered from configured skill directories.

    This tool scans the local filesystem for `SKILL.md` files and returns
    a paginated list of skills that agents can use, including basic metadata
    such as `skill_id`, `display_name`, `description`, and `source`.
    """

    skills = _INDEX.search(query=params.query, source=params.source)
    total = len(skills)
    start = params.offset or 0
    end = min(start + (params.limit or 50), total)
    page = skills[start:end]

    items = [_skill_to_dict(s) for s in page]

    payload: Dict[str, Any] = {
        "total": total,
        "count": len(items),
        "offset": start,
        "items": items,
        "has_more": end < total,
        "next_offset": end if end < total else None,
    }

    if params.response_format == ResponseFormat.JSON:
        import json

        return json.dumps(payload, indent=2, sort_keys=True)

    lines: List[str] = [
        "# Available skills",
        "",
        f"Total skills: {total} (showing {len(items)} from offset {start})",
        "",
    ]
    for item in items:
        lines.append(f"## {item['display_name']} ({item['skill_id']})")
        if item.get("description"):
            lines.append(item["description"])
        lines.append(f"- Source: {item['source']}")
        lines.append("")
    return "\n".join(lines)


@mcp.tool(
    name="skills_get_skill",
    annotations={
        "title": "Get a single skill",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def skills_get_skill(params: GetSkillInput) -> str:
    """Fetch a single skill's metadata and SKILL.md content.

    Use this tool to load the full instructions for a given skill by its
    `skill_id` (directory name). This is useful when an agent has identified
    a relevant skill and wants to follow its guidelines.
    """

    skill = _INDEX.get(params.skill_id)
    if skill is None:
        message = (
            f"Error: Skill '{params.skill_id}' not found. "
            "Use skills_list_skills to discover available skills."
        )
        return message

    try:
        content = skill.path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Error: Failed to read SKILL file for '{params.skill_id}': {exc}"

    if params.response_format == ResponseFormat.MARKDOWN:
        header = [
            f"# Skill: {skill.display_name} ({skill.skill_id})",
            "",
            f"Source: {skill.source.value}",
            "",
            "---",
            "",
        ]
        return "\n".join(header) + content

    data: Dict[str, Any] = {"skill_id": skill.skill_id, "content_markdown": content}
    if params.include_metadata:
        data.update(
            {
                "display_name": skill.display_name,
                "description": skill.description,
                "source": skill.source.value,
                "path": str(skill.path),
            }
        )

    import json

    return json.dumps(data, indent=2, sort_keys=True)


@mcp.tool(
    name="skills_search_skills",
    annotations={
        "title": "Search within skill contents",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def skills_search_skills(params: SearchSkillsInput) -> str:
    """Search within SKILL.md contents for a query string.

    This tool performs a simple full-text search across all discovered skills
    and returns snippets showing where the query appears.
    """

    query_lower = params.query.lower()
    matches: List[Dict[str, Any]] = []

    for skill in _INDEX.all_skills():
        try:
            content = skill.path.read_text(encoding="utf-8")
        except OSError:
            continue

        if query_lower not in content.lower():
            continue

        idx = content.lower().index(query_lower)
        start = max(0, idx - 80)
        end = min(len(content), idx + 80)
        snippet = content[start:end].replace("\n", " ")

        matches.append(
            {
                "skill_id": skill.skill_id,
                "display_name": skill.display_name,
                "source": skill.source.value,
                "snippet": snippet,
            }
        )

        if len(matches) >= (params.limit or 20):
            break

    payload = {"query": params.query, "count": len(matches), "matches": matches}

    if params.response_format == ResponseFormat.JSON:
        import json

        return json.dumps(payload, indent=2, sort_keys=True)

    if not matches:
        return f"No matches found for query '{params.query}'."

    lines: List[str] = [
        f"# Skill search results for '{params.query}'",
        "",
        f"Matches: {len(matches)}",
        "",
    ]
    for match in matches:
        lines.append(
            f"## {match['display_name']} ({match['skill_id']}) [{match['source']}]"
        )
        lines.append(match["snippet"])
        lines.append("")
    return "\n".join(lines)


@mcp.resource("skills://{skill_id}")
async def skills_resource(skill_id: str) -> str:
    """Expose SKILL.md content as an MCP resource.

    Use the `skills://{skill_id}` URI to retrieve the raw markdown content
    for a given skill without additional metadata.
    """

    skill = _INDEX.get(skill_id)
    if skill is None:
        return (
            f"Error: Skill '{skill_id}' not found. "
            "Use skills_list_skills to discover available skills."
        )

    try:
        return skill.path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"Error: Failed to read SKILL file for '{skill_id}': {exc}"


if __name__ == "__main__":
    mcp.run()

