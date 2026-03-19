from __future__ import annotations

from dataclasses import dataclass

from .emitted_view import EmittedView
from .lifecycle import PublicationLifecycle
from .persistence_plan import PersistencePlan
from .requested_view import RequestedView


@dataclass(frozen=True)
class PublicationPolicyDecision:
    lifecycle: PublicationLifecycle
    requested_view: RequestedView
    emitted_view: EmittedView
    persistence: PersistencePlan
