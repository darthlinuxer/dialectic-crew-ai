"""Optional MCP server configuration for dialectic agents."""

from __future__ import annotations

import logging
import os
import shutil
import sys
from typing import Any

from crewai.mcp import MCPServerHTTP, MCPServerStdio

logger = logging.getLogger(__name__)


def _python_command() -> str:
    """Return a reliable Python executable for local stdio MCP servers."""
    return sys.executable or shutil.which("python3") or "python3"


def _make_mcp(
    constructor,
    *,
    required_env: str | None = None,
    required_cmd: str | None = None,
    **kwargs,
):
    """Instantiate an MCP server only when its configuration is valid."""
    if required_env and not os.getenv(required_env):
        logger.warning("MCP server skipped: env var %s not set", required_env)
        return None
    if required_cmd and not shutil.which(required_cmd):
        logger.warning("MCP server skipped: command %r not found", required_cmd)
        return None
    try:
        return constructor(**kwargs)
    except Exception as exc:
        logger.warning("MCP server failed to initialize: %s", exc)
        return None


mcp_context7 = _make_mcp(
    MCPServerHTTP,
    required_env="CONTEXT7_API_KEY",
    url="https://mcp.context7.com/mcp",
    headers={"CONTEXT7_API_KEY": os.getenv("CONTEXT7_API_KEY", "")},
    cache_tools_list=True,
)

mcp_sequential_thinking = _make_mcp(
    MCPServerStdio,
    required_cmd="docker",
    command="docker",
    args=["run", "--rm", "-i", "mcp/sequentialthinking"],
)

mcp_brave_search = _make_mcp(
    MCPServerStdio,
    required_env="BRAVE_API_KEY",
    required_cmd="docker",
    command="docker",
    args=["run", "-i", "--rm", "-e", "BRAVE_API_KEY", "docker.io/mcp/brave-search"],
    env={"BRAVE_API_KEY": os.getenv("BRAVE_API_KEY", "")},
)

mcp_skills = _make_mcp(
    MCPServerStdio,
    command=_python_command(),
    args=["-m", "src.mcp.skills_mcp"],
)

MCP_BUNDLES: dict[str, list[Any]] = {
    "none": [],
    "research": [mcp_context7, mcp_brave_search, mcp_skills],
    "local_reasoning": [mcp_sequential_thinking, mcp_skills],
    "knowledge": [mcp_context7, mcp_skills],
}