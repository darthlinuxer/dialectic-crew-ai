## Skills MCP Server Integration with CrewAI

This document explains how to connect the `skills_mcp` server in this repo to CrewAI agents using the MCP features described in the CrewAI docs:

- [MCP overview](https://docs.crewai.com/en/mcp/overview)
- [Stdio transport](https://docs.crewai.com/en/mcp/stdio)
- [Streamable HTTP transport](https://docs.crewai.com/en/mcp/streamable-http)
- [Connecting to multiple servers](https://docs.crewai.com/en/mcp/multiple-servers)

### Server Overview

- **Server implementation**: `skills_mcp` lives in `src/mcp/skills_mcp.py` and is built with `FastMCP("skills_mcp")`.
- **Transports**:
  - **Default**: stdio (local process) via `mcp.run()`.
  - **Optional**: streamable HTTP via `mcp.run(transport="streamable_http", port=...)` when enabled with an env var or CLI flag.
- **Purpose**: Expose local skill definitions (`SKILL.md` files under `src/mcp/skills`, `~/.agents/skills`, `.cursor/skills-cursor`) as MCP tools and resources so CrewAI agents can dynamically discover and load skills.

The main tools are:

- `skills_list_skills` – list available skills with pagination and metadata.
- `skills_get_skill` – fetch a specific skill’s metadata and full SKILL markdown content.
- `skills_search_skills` – full-text search across SKILL contents.

Each skill is also available as an MCP resource at `skills://{skill_id}`.

### Running the Server (Local Stdio)

By default, running `src/mcp/skills_mcp.py` starts a stdio-based MCP server suitable for CrewAI’s `MCPServerStdio`:

```bash
python -m src.mcp.skills_mcp
```

This matches the Stdio transport patterns in the CrewAI docs ([Stdio transport](https://docs.crewai.com/en/mcp/stdio)).

### Connecting from CrewAI via Stdio

Use `MCPServerStdio` from `crewai.mcp` to attach `skills_mcp` as a local MCP server:

```python
from crewai import Agent
from crewai.mcp import MCPServerStdio
from crewai.mcp.filters import create_static_tool_filter

skills_server = MCPServerStdio(
    command="python",
    args=["-m", "src.mcp.skills_mcp"],
    cache_tools_list=True,
    tool_filter=create_static_tool_filter(
        allowed_tool_names=[
            "skills_list_skills",
            "skills_get_skill",
            "skills_search_skills",
        ]
    ),
)

agent = Agent(
    role="Skills-Aware Agent",
    goal="Discover and follow local skills before taking actions.",
    backstory="Uses MCP to load SKILL.md guidance such as 'using-superpowers' and 'sequential-thinking'.",
    mcps=[skills_server],
)
```

At runtime, the agent can call:

1. `skills_list_skills` to find relevant skills.
2. `skills_get_skill` to load the full SKILL content (for example, `using-superpowers`).
3. Follow the loaded instructions before executing other tools or code.

This pattern lines up with the CrewAI MCP overview ([MCP overview](https://docs.crewai.com/en/mcp/overview)) using structured MCP configurations.

### Optional: Running as a Streamable HTTP Server

`skills_mcp` also supports running as a streamable HTTP MCP server so it can be reached via `MCPServerHTTP` or string-based `mcps` URLs.

Start the server in HTTP mode by setting an environment variable or passing a flag:

```bash
# Environment-based
SKILLS_MCP_TRANSPORT=streamable_http SKILLS_MCP_PORT=8001 python -m src.mcp.skills_mcp

# Or flag-based (equivalent)
python -m src.mcp.skills_mcp --http
```

This is compatible with the Streamable HTTP patterns in the CrewAI docs ([Streamable HTTP transport](https://docs.crewai.com/en/mcp/streamable-http)).

Then configure an agent with `MCPServerHTTP`:

```python
from crewai import Agent
from crewai.mcp import MCPServerHTTP

skills_http = MCPServerHTTP(
    url="http://localhost:8001/mcp",
    streamable=True,
    cache_tools_list=True,
)

agent = Agent(
    role="Remote Skills-Aware Agent",
    goal="Use remote skills_mcp over HTTP to load skills.",
    backstory="Accesses skills via streamable HTTP MCP.",
    mcps=[skills_http],
)
```

### Aggregating skills_mcp with Other MCP Servers

To combine `skills_mcp` with other MCP servers, follow the multiple-server guidance from the CrewAI docs ([Connecting to Multiple MCP Servers](https://docs.crewai.com/en/mcp/multiple-servers)). Conceptually:

- Use `MCPServerStdio` or `MCPServerHTTP` for `skills_mcp`.
- Add additional MCP server configurations (stdio, SSE, or streamable HTTP) in the same `mcps` list or via `MCPServerAdapter`.

Example using the simple `mcps` DSL:

```python
from crewai import Agent
from crewai.mcp import MCPServerStdio, MCPServerHTTP

skills_stdio = MCPServerStdio(
    command="python",
    args=["-m", "src.mcp.skills_mcp"],
)

other_http = MCPServerHTTP(
    url="https://api.example.com/mcp",
    streamable=True,
)

agent = Agent(
    role="Composite MCP Agent",
    goal="Use both local skills and remote tools.",
    backstory="Combines skills_mcp with external MCP services.",
    mcps=[skills_stdio, other_http],
)
```

Now the agent has access to:

- All `skills_*` tools from `skills_mcp`.
- Tools exposed by the remote HTTP server.

