# pylint: disable=trailing-newlines
"""MCP server exposing local skill discovery and retrieval tools."""

from __future__ import annotations

from dataclasses import asdict
from enum import Enum
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence, cast

from pydantic import BaseModel, Field, ConfigDict

try:
    from mcp.server.fastmcp import FastMCP as _RuntimeFastMCP
    from mcp.types import ToolAnnotations

    FastMCP = cast(Any, _RuntimeFastMCP)

    def _make_tool_annotations(**kwargs: Any) -> Any:
        return ToolAnnotations(**kwargs)
except ModuleNotFoundError:

    def _make_tool_annotations(**kwargs: Any) -> Any:
        return kwargs

    class FastMCP:  # type: ignore[no-redef]
        """Fallback FastMCP stub used when the MCP dependency is unavailable."""

        def __init__(self, name: str, **_: Any):
            self.name = name
            self.settings = type("Settings", (), {"port": 8000})()
            self.last_transport = "stdio"

        def tool(self, *_args: Any, **_kwargs: Any):
            """Return a no-op decorator for tool registration."""

            def decorator(func: Any) -> Any:
                return func

            return decorator

        def resource(self, *_args: Any, **_kwargs: Any):
            """Return a no-op decorator for resource registration."""

            def decorator(func: Any) -> Any:
                return func

            return decorator

        def run(
            self,
            transport: str = "stdio",
            mount_path: str | None = None,
        ) -> None:
            """Record the requested transport in fallback mode."""

            _ = mount_path
            self.last_transport = transport


from .skills_index import SkillIndex, SkillMetadata, SkillSource


class ResponseFormat(str, Enum):
    """Supported output formats for MCP tool responses."""

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
        description=(
            "Optional case-insensitive substring filter applied to skill id, "
            "display name, and description."
        ),
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
        description=(
            "Output format: 'json' for structured data, 'markdown' for "
            "human-readable summary."
        ),
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
        description=(
            "Whether to include metadata (source, description, path) in the "
            "JSON response."
        ),
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.JSON,
        description=(
            "Output format: 'json' for structured data, 'markdown' for "
            "human-readable content."
        ),
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
        description=(
            "Output format: 'json' for structured data, 'markdown' for "
            "human-readable summary."
        ),
    )


ROOTS: List[Path] = [
    Path("src/mcp/skills").resolve(),
    Path.home() / ".agents" / "skills",
    Path.home() / ".cursor" / "skills-cursor",
]

TransportName = Literal["stdio", "sse", "streamable-http"]
HTTP_TRANSPORT: Literal["streamable-http"] = "streamable-http"
HTTP_FLAGS = frozenset({"--http", "--streamable-http"})
DEFAULT_HTTP_PORT = 8001

READ_ONLY_ANNOTATIONS = _make_tool_annotations(
    title="List available skills",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

GET_SKILL_ANNOTATIONS = _make_tool_annotations(
    title="Get a single skill",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

SEARCH_SKILL_ANNOTATIONS = _make_tool_annotations(
    title="Search within skill contents",
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)

_INDEX = SkillIndex(roots=ROOTS)

mcp = FastMCP("skills_mcp")


def _skill_to_dict(skill: SkillMetadata) -> Dict[str, Any]:
    """Convert a skill metadata object into a JSON-serializable dictionary."""

    data = asdict(skill)
    data["path"] = str(skill.path)
    data["source"] = skill.source.value
    return data


@mcp.tool(
    name="skills_list_skills",
    annotations=READ_ONLY_ANNOTATIONS,
)
async def skills_list_skills(params: ListSkillsInput) -> str:
    """List available skills discovered from configured skill directories.

    This tool scans the local filesystem for `SKILL.md` files and returns
    a paginated list of skills that agents can use, including basic metadata
    such as `skill_id`, `display_name`, `description`, and `source`.

    Typical CrewAI usage:
    - Connect to this MCP server via `mcps` using `MCPServerStdio` (local) or
      `MCPServerHTTP` (streamable HTTP).
    - Call `skills_list_skills` to discover relevant skills (for example,
      `using-superpowers`, `sequential-thinking`), then call `skills_get_skill`
      to load the chosen SKILL content before acting.
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
    annotations=GET_SKILL_ANNOTATIONS,
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

    return json.dumps(data, indent=2, sort_keys=True)


@mcp.tool(
    name="skills_search_skills",
    annotations=SEARCH_SKILL_ANNOTATIONS,
)
async def skills_search_skills(params: SearchSkillsInput) -> str:
    """Search within SKILL.md contents for a query string.

    This tool performs a simple full-text search across all discovered skills
    and returns snippets showing where the query appears. CrewAI agents can
    use it when they do not yet know which specific skill to load with
    `skills_get_skill`.
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
    for a given skill without additional metadata. This is useful when a
    client wants direct access to the skill file outside the higher-level
    tools.
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


def _resolve_transport(
    argv: Sequence[str], environ: Mapping[str, str]
) -> TransportName:
    """Resolve the requested MCP transport from environment and CLI flags."""

    transport = environ.get("SKILLS_MCP_TRANSPORT", "stdio").strip().lower()
    transport = transport.replace("_", "-")

    argv_flags = {arg for arg in argv if arg.startswith("--")}
    if HTTP_FLAGS & argv_flags:
        return HTTP_TRANSPORT
    if transport == "sse":
        return "sse"
    if transport == HTTP_TRANSPORT:
        return HTTP_TRANSPORT
    return "stdio"


def _resolve_http_port(environ: Mapping[str, str]) -> int:
    """Read the configured HTTP port, falling back to the default on parse errors."""

    port_str = environ.get("SKILLS_MCP_PORT", str(DEFAULT_HTTP_PORT))
    try:
        return int(port_str)
    except ValueError:
        return DEFAULT_HTTP_PORT


def run_server(
    argv: Sequence[str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Run the skills MCP server using the resolved transport settings."""

    runtime_argv = list(argv) if argv is not None else []
    runtime_environ = environ if environ is not None else os.environ

    transport = _resolve_transport(runtime_argv, runtime_environ)
    if transport == HTTP_TRANSPORT:
        cast(Any, mcp.settings).port = _resolve_http_port(runtime_environ)
        mcp.run(transport=HTTP_TRANSPORT)
        return

    mcp.run(transport=transport)


if __name__ == "__main__":
    import sys

    run_server(argv=sys.argv[1:], environ=os.environ)
