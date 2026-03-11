"""Vision knowledge and crew memory helpers for dialectic agents."""

from __future__ import annotations

from pathlib import Path

from crewai import Memory
from crewai.knowledge.source.text_file_knowledge_source import TextFileKnowledgeSource

from dialectic.vision import VisionContext


def vision_label(vision_paths: dict[VisionContext, Path], context: VisionContext) -> str:
    """Return the human-readable vision document name for prompts."""
    return vision_paths[context].name


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


def crew_memory_store(
    context: VisionContext,
    namespace: str,
    *,
    resolve_project_root_fn,
    memory_cls=Memory,
) -> Memory:
    """Return a Memory instance isolated by vision context and crew namespace."""
    safe_namespace = namespace.strip("/") or "shared"
    storage_dir = (
        resolve_project_root_fn()
        / ".crewai"
        / "memory"
        / context.value
        / safe_namespace
    )
    storage_dir.mkdir(parents=True, exist_ok=True)
    return memory_cls(storage=str(storage_dir))