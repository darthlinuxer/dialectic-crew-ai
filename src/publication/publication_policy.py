from __future__ import annotations

from dataclasses import dataclass

from .emitted_view import EmittedView
from .lifecycle import PublicationLifecycle


@dataclass(frozen=True)
class PublicationPolicy:
    lifecycle: PublicationLifecycle
    emitted_view: EmittedView
    approval_grade: bool
    persist_to_prd_output: bool
    required_artifacts: tuple[str, ...]
