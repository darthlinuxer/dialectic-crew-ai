import json
import logging
import os
import tempfile
import threading
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel
from .config import load_settings, PRDOutputFormat

logger = logging.getLogger(__name__)
_lock = threading.Lock()


class PRDModel(BaseModel):
    # Minimal example schema; real project should import PRDSchema
    title: str
    description: str
    quality_score: Optional[float] = None


def _atomic_write(path: str, data: bytes) -> None:
    dirpath = os.path.dirname(path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


def export_prd(prd: PRDModel, output_dir: str) -> Dict[str, str]:
    """Export PRD according to PRD_OUTPUT_FORMAT. Returns dict of written paths.

    Behavior:
    - write JSON first (if selected), then MD
    - use atomic replace
    - if MD fails after JSON written, rollback JSON (remove file) and raise
    - thread-safe via simple lock
    """
    settings = load_settings()
    fmt = settings.prd_output_format

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = f"PRD_{timestamp}"
    written = {}

    with _lock:
        try:
            if fmt in (PRDOutputFormat.JSON, PRDOutputFormat.BOTH):
                json_path = os.path.join(output_dir, base + ".json")
                logger.debug("Writing JSON to %s", json_path)
                _atomic_write(json_path, prd.model_dump_json().encode("utf-8"))
                written["json"] = json_path

            if fmt in (PRDOutputFormat.MD, PRDOutputFormat.BOTH):
                md_path = os.path.join(output_dir, base + ".md")
                logger.debug("Writing MD to %s", md_path)
                # Build minimal md content with frontmatter
                frontmatter = {
                    "title": prd.title,
                    "quality_score": prd.quality_score,
                    "timestamp": timestamp,
                }
                md = """---\n"""
                md += "\n".join(f"{k}: {v}" for k, v in frontmatter.items() if v is not None)
                md += "\n---\n\n"
                md += f"# {prd.title}\n\n{prd.description}\n"
                # Simulate potential failure point during md writing by allowing path to be invalid
                _atomic_write(md_path, md.encode("utf-8"))
                written["md"] = md_path

            return written
        except Exception as e:
            logger.exception("Failed to export PRD: %s", e)
            # rollback json if md failed
            if "json" in written and os.path.exists(written["json"]):
                try:
                    os.remove(written["json"])
                    logger.info("Rolled back JSON at %s", written["json"])
                except Exception:
                    logger.exception("Failed to rollback JSON file %s", written.get("json"))
            raise
