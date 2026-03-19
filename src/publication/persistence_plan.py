from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistencePlan:
    persist_markdown: bool
    persist_json: bool
    output_dir: str | None = None

    @property
    def requires_persistence(self) -> bool:
        return self.persist_markdown or self.persist_json
