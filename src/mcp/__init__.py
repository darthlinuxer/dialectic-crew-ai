"""MCP package exports for local skills discovery."""

from . import skills_mcp
from .skills_index import SkillIndex, SkillMetadata, SkillSource

__all__ = [
    "skills_mcp",
    "SkillIndex",
    "SkillMetadata",
    "SkillSource",
]
