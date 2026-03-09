import logging
import os
import shutil

from crewai import Agent, LLM
from crewai.mcp import MCPServerStdio, MCPServerHTTP
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from dialectic.tools import (
    file_read_tool,
    file_write_tool,
    json_search_tool,
    directory_read_tool,
    code_docs_tool,
)

logger = logging.getLogger(__name__)


def _make_mcp(constructor, *, required_env: str | None = None,
              required_cmd: str | None = None, **kwargs):
    """Instantiate an MCP server only when its configuration is valid.

    Returns None (with a log warning) if a required env var is unset
    or a required command is not found on PATH.
    """
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


# ---------------------------------------------------------------------------
# LLM instances (stateless connectors — safe as module-level singletons)
# ---------------------------------------------------------------------------

LLM_TIMEOUT = int(os.getenv("LLM_REQUEST_TIMEOUT", "900"))

LLM_MODEL_SIMPLE = os.getenv("LLM_MODEL_SIMPLE", "gpt-4o-mini")
LLM_MODEL_COMPLEX = os.getenv("LLM_MODEL_COMPLEX", "gpt-4o")
LLM_MODEL_REASONING = os.getenv("LLM_MODEL_REASONING", "o3-mini")
LLM_MODEL_PLANNING = os.getenv("LLM_MODEL_PLANNING", LLM_MODEL_REASONING)

_common: dict = {"timeout": LLM_TIMEOUT}

llm_simple = LLM(model=LLM_MODEL_SIMPLE, **_common)
llm_complex = LLM(model=LLM_MODEL_COMPLEX, **_common)
llm_reasoning = LLM(model=LLM_MODEL_REASONING, **_common)
llm_planning = LLM(model=LLM_MODEL_PLANNING, **_common)

# ---------------------------------------------------------------------------
# MCP server configurations (optional; agents degrade gracefully if unavailable)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Knowledge source: VISION.md loaded via semantic chunking + vector retrieval.
# Attach to Crew(..., knowledge_sources=[vision_knowledge()]) so agents get
# relevant sections automatically instead of raw text injection.
# ---------------------------------------------------------------------------

def vision_knowledge() -> TextFileKnowledgeSource:
    """Create a TextFileKnowledgeSource for VISION.md.

    CrewAI automatically resolves string paths relative to the `knowledge/`
    directory, so the file must live at `knowledge/VISION.md`.
    """
    return TextFileKnowledgeSource(file_paths=["VISION.md"])


# ---------------------------------------------------------------------------
# Agent factory functions — each call returns a fresh Agent instance
# to avoid cross-flow contamination when memory=True.
# ---------------------------------------------------------------------------

def create_visionario() -> Agent:
    return Agent(
        role="Senior Visionary Architect",
        goal="Propose the most elegant initial solution aligned with the system's macro vision",
        backstory=(
            "You are an architect with 18 years of experience. You always think of the "
            "system as a whole. Your first proposal (thesis) must be bold and comprehensive.\n\n"
            "You ALWAYS consult the system's macro vision (VISION.md, available via your "
            "knowledge sources) before anything else.\n\n"
            "Before proposing anything, analyze:\n"
            "1. What the macro vision requires\n"
            "2. Which modules are affected\n"
            "3. Which non-functional requirements matter\n"
            "4. What is the ideal tradeoff between speed and quality\n\n"
            "Your proposal must be holistic, coherent, and aligned with the macro vision."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_reasoning,
        reasoning=True,
        max_reasoning_attempts=3,
        tools=[t for t in [file_read_tool, directory_read_tool, code_docs_tool] if t],
        mcps=[m for m in [mcp_context7, mcp_brave_search] if m],
    )


def create_critico_socratico() -> Agent:
    return Agent(
        role="Relentless Socratic Critic",
        goal="Rigorously evaluate whether the implementation meets what was requested in the task, without expanding scope",
        backstory=(
            "You are the ultimate devil's advocate. Your method is 100% Socratic.\n\n"
            "FUNDAMENTAL RULE: Evaluate ONLY what the task requests. Do NOT expand the scope.\n"
            "If the task says 'add a variable to .env', evaluate whether the variable was added correctly.\n"
            "Do NOT request CI/CD, CODEOWNERS, security automation, or anything the task did not ask for.\n\n"
            "Your job — ALWAYS within the task's scope:\n"
            "1. Was the task description met point by point?\n"
            "2. Are there contradictions with VISION.md in what was done?\n"
            "3. Did the implementer do MORE than requested (overscope)?\n"
            "4. Are there bugs or technical errors in what was delivered?\n"
            "5. Assign a FAIR score of 1-10 considering ONLY the task's scope\n\n"
            "Be rigorous but fair. A simple task well executed deserves a high score.\n"
            "Do not penalize for things that were not requested."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_complex,
        reasoning=True,
        max_reasoning_attempts=2,
        tools=[],
        mcps=[m for m in [mcp_sequential_thinking] if m],
    )


def create_sintetizador() -> Agent:
    return Agent(
        role="Dialectic Synthesizer",
        goal="Transform thesis + antithesis into a superior version, eliminating ALL weaknesses",
        backstory=(
            "You are Hegel in code form. You receive the proposal + the critiques and "
            "produce the final synthesis.\n\n"
            "Your mission is to ensure the final version scores >= 9.0 with zero contradictions "
            "against the macro vision.\n\n"
            "When you receive:\n"
            "- The original proposal (thesis) from the Visionary\n"
            "- The critique (antithesis) from the Socratic Critic\n\n"
            "You must create a SYNTHESIS that:\n"
            "1. Preserves what was good in the thesis\n"
            "2. Incorporates ALL critiques from the antithesis\n"
            "3. Eliminates ALL identified weaknesses\n"
            "4. Resolves contradictions creatively\n"
            "5. Is better than both individual proposals\n\n"
            "The synthesis is not a mediocre middle ground — it is a dialectical transcendence."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_complex,
        reasoning=True,
        max_reasoning_attempts=2,
        tools=[],
        mcps=[m for m in [mcp_context7] if m],
    )


def create_validador_macro() -> Agent:
    return Agent(
        role="Macro & Quality Validator",
        goal="Assign a final score of 0-10 and decide whether to approve or force a retry",
        backstory=(
            "You are the final gate. Your job is to validate the final PRD with rigor.\n\n"
            "You ALWAYS consult the macro vision (VISION.md, available via your knowledge "
            "sources) for the final comparison.\n\n"
            "Respond ONLY with:\n"
            "- quality_score: float (exactly one decimal place, e.g.: 8.5)\n"
            "- consensus_reached: true/false\n"
            "- final_validation_notes: detailed explanation\n\n"
            "If score < 9.0, explain EXACTLY what still needs improvement.\n\n"
            "Validation checklist:\n"
            "1. Feature aligned with macro vision?\n"
            "2. Affected modules considered?\n"
            "3. Risks mitigated?\n"
            "4. Non-functional requirements covered?\n"
            "5. User stories consistent and complete?\n"
            "6. 5+ anti-drift questions answered?\n"
            "7. Zero contradictions with VISION.md?"
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_simple,
        tools=[t for t in [file_read_tool, directory_read_tool, json_search_tool] if t],
    )


def create_implementer() -> Agent:
    return Agent(
        role="Technical Implementer",
        goal="Execute the task as described, generating code/config/files aligned with VISION.md",
        backstory=(
            "You are an experienced technical implementer. Your role is to execute "
            "implementation tasks as specified in the plan, strictly following VISION.md.\n\n"
            "You ALWAYS consult the macro vision (VISION.md, available via your knowledge "
            "sources) before implementing.\n\n"
            "Rules:\n"
            "1. Implement exactly what the task asks for, without overscope\n"
            "2. Respect the project's existing structure\n"
            "3. Write clean, testable code aligned with the macro vision\n"
            "4. If the task requires config, use .env or existing config\n"
            "5. Document relevant changes\n\n"
            "Upon completion, clearly describe what was done and which files were created/modified."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm_complex,
        tools=[file_read_tool, file_write_tool, directory_read_tool],
        mcps=[m for m in [mcp_context7, mcp_brave_search] if m],
    )
