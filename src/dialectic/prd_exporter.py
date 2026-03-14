from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path
import re
from typing import List

from dialectic.config import ExportConfig
from dialectic.markdown_renderers import render_markdown
from schemas import PRDSchema

logger = logging.getLogger(__name__)


class ExportException(Exception):
    """Raised when export fails and a rollback is performed."""


def _slugify(text: str | None) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "prd"


class PRDExporter:
    """Dual exporter for PRD JSON/Markdown artifacts according to ExportConfig."""

    def export(self, prd: PRDSchema, config: ExportConfig) -> List[Path]:
        created: List[Path] = []

        output_dir = Path(config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        slug = _slugify(getattr(prd, "feature_name", None) or "")
        version = getattr(prd, "version", None) or datetime.utcnow().strftime("%Y%m%d%H%M%S")

        json_path = output_dir / f"{slug}-{version}.json"
        md_path = output_dir / f"{slug}-{version}.md"

        def _write_json() -> None:
            try:
                json_text = prd.model_dump_json(indent=2)
            except Exception as exc:
                logger.exception("Failed to serialize PRD to JSON: %s", exc)
                raise ExportException(f"Failed to serialize PRD to JSON: {exc}")

            try:
                json_path.write_text(json_text, encoding="utf-8")
                created.append(json_path)
                logger.info("Wrote JSON PRD to %s", json_path)
            except Exception as exc:
                logger.exception("Failed to write JSON file %s: %s", json_path, exc)
                raise ExportException(f"Failed to write JSON file {json_path}: {exc}")

        def _write_md() -> None:
            try:
                markdown_text = render_markdown(prd, config)
            except Exception as exc:
                logger.exception("Failed to render Markdown: %s", exc)
                raise ExportException(f"Failed to render Markdown: {exc}")

            try:
                md_path.write_text(markdown_text, encoding="utf-8")
                created.append(md_path)
                logger.info("Wrote Markdown PRD to %s", md_path)
            except Exception as exc:
                logger.exception("Failed to write MD file %s: %s", md_path, exc)
                raise ExportException(f"Failed to write MD file {md_path}: {exc}")

        output_format = (config.output_format or "json").lower()

        if output_format == "json":
            _write_json()
            return created

        if output_format == "md":
            _write_md()
            return created

        if output_format == "both":
            _write_json()
            try:
                _write_md()
            except ExportException:
                try:
                    if json_path.exists():
                        json_path.unlink()
                        logger.info("Rolled back JSON file %s due to MD write failure", json_path)
                        if json_path in created:
                            created.remove(json_path)
                except Exception:
                    logger.exception("Failed to rollback JSON file %s after MD failure", json_path)
                raise
            return created

        raise ExportException(f"Unknown output format: {config.output_format}")
