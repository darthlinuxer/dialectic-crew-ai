"""Vision knowledge and crew memory helpers for dialectic crews."""

from __future__ import annotations

from pathlib import Path

from crewai import Memory  # pylint: disable=no-name-in-module
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from dialectic.target import target_memory_namespace
from dialectic.vision import (
    VisionContext,
    _VISION_PATHS,
    get_vision_path,
    prepare_vision_runtime,
    resolve_project_root,
)


def vision_label(vision_paths: dict[VisionContext, Path], context: VisionContext) -> str:
    """Return the human-readable vision document name for prompts."""
    return vision_paths[context].name


def _vision_label(context: VisionContext = VisionContext.PROJECT) -> str:
    """Return the active vision filename for prompt rendering."""
    return vision_label(_VISION_PATHS, context)


def vision_path_label(vision_paths: dict[VisionContext, Path], context: VisionContext) -> str:
    """Return the repo-relative vision path for prompt rendering."""
    return vision_paths[context].as_posix()


def _vision_path(context: VisionContext = VisionContext.PROJECT) -> str:
    """Return the active repo-relative vision path for prompt rendering."""
    app_root = resolve_project_root()
    vision_path = get_vision_path(context)
    try:
        return vision_path.relative_to(app_root).as_posix()
    except ValueError:
        return vision_path.as_posix()


def vision_knowledge_source(
    context: VisionContext,
    *,
    prepare_vision_runtime_fn,
    get_vision_path_fn,
    knowledge_source_cls=TextFileKnowledgeSource,
):
    """Create a knowledge source for the active vision document."""
    prepare_vision_runtime_fn(context)
    vision_path = get_vision_path_fn(context)
    return knowledge_source_cls(file_paths=[vision_path])


def vision_knowledge(
    context: VisionContext = VisionContext.PROJECT,
    *,
    prepare_vision_runtime_fn=None,
    get_vision_path_fn=None,
    knowledge_source_cls=None,
):
    """Create a knowledge source for the active vision document."""
    return vision_knowledge_source(
        context,
        prepare_vision_runtime_fn=prepare_vision_runtime_fn or prepare_vision_runtime,
        get_vision_path_fn=get_vision_path_fn or get_vision_path,
        knowledge_source_cls=knowledge_source_cls or TextFileKnowledgeSource,
    )


def crew_memory_store(
    context: VisionContext,
    namespace: str,
    *,
    resolve_project_root_fn,
    memory_cls=Memory,
) -> Memory:
    """Return a Memory instance isolated by vision context and crew namespace."""
    safe_namespace = namespace.strip("/") or "shared"
    if context is VisionContext.PROJECT:
        safe_namespace = target_memory_namespace(safe_namespace)
    storage_dir = (
        resolve_project_root_fn()
        / ".crewai"
        / "memory"
        / context.value
        / safe_namespace
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    return memory_cls(storage=str(storage_dir))


def crew_memory(
    context: VisionContext = VisionContext.PROJECT,
    namespace: str = "shared",
    *,
    resolve_project_root_fn=None,
    memory_cls=None,
) -> Memory:
    """Return a Memory instance isolated by vision context and crew namespace."""
    return crew_memory_store(
        context,
        namespace,
        resolve_project_root_fn=resolve_project_root_fn or resolve_project_root,
        memory_cls=memory_cls or Memory,
    )


_STYLE_GUIDE_PATHS = [
    Path("src/mcp/skills/senior-software-developer/reference/python-style.md"),
    Path("src/mcp/skills/senior-software-developer/reference/python-patterns.md"),
    Path("src/mcp/skills/senior-software-developer/reference/python-testing.md"),
]


def style_guide_knowledge(
    *,
    resolve_project_root_fn=None,
    knowledge_source_cls=None,
) -> list:
    """Create knowledge sources for Python style guides (for self-improve context)."""
    root_fn = resolve_project_root_fn or resolve_project_root
    source_cls = knowledge_source_cls or TextFileKnowledgeSource
    app_root = root_fn()

    sources = []
    for rel_path in _STYLE_GUIDE_PATHS:
        full_path = app_root / rel_path
        if full_path.exists():
            sources.append(source_cls(file_paths=[full_path]))
    return sources
