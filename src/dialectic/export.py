from __future__ import annotations

from typing import Union, List
from pathlib import Path
from datetime import datetime, timezone
import logging
import re
import hashlib
import os
import tempfile
from dataclasses import dataclass
import json

from schemas import PRDSchema, UserStoryExecutionPlan
from dialectic.config import ExportConfig
from dialectic.vision import VisionContext, get_vision_hash

logger = logging.getLogger(__name__)

# Prefer PyYAML for robust frontmatter parsing; fallback implemented below.
try:
    import yaml  # type: ignore
except Exception:
    yaml = None
    logger.debug("PyYAML not available; frontmatter parsing will use a simple fallback. For robust parsing, install PyYAML.")


class ExportException(Exception):
    """Raised when export fails and a rollback is performed."""


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


def execution_plan_to_markdown(plan: Union[UserStoryExecutionPlan, dict]) -> str:
    """Converts an execution plan (user story) to Markdown."""
    if isinstance(plan, dict):
        plan = UserStoryExecutionPlan.model_validate(plan)
    lines = [
        f"# Execution Plan — {plan.user_story_id} {plan.user_story_title}",
        "",
        f"**Score:** {plan.quality_score}/10.0  |  **Consensus:** {'Yes' if plan.consensus_reached else 'No'}",
        "",
        "---",
        "",
        "## Approach",
        "",
        plan.approach_summary,
        "",
        "---",
        "",
        "## Tasks",
        "",
    ]
    for t in sorted(plan.tasks, key=lambda x: (x.order, x.id)):
        lines.append(f"### {t.id} — {t.title}")
        lines.append("")
        lines.append(t.description)
        if t.dependencies:
            lines.append("")
            lines.append(f"*Dependencies:* {', '.join(t.dependencies)}")
        lines.append("")
    if plan.risks_mitigated:
        lines.extend(["---", "", "## Mitigated Risks", ""])
        for r in plan.risks_mitigated:
            lines.append(f"- {r}")
        lines.append("")
    if plan.tech_notes:
        lines.extend(["---", "", "## Technical Notes", "", plan.tech_notes, ""])
    lines.extend(["---", "", "## Validation", "", plan.final_validation_notes.strip(), ""])
    return "\n".join(lines).strip() + "\n"


def prd_to_markdown(prd: Union[PRDSchema, dict]) -> str:
    """Converts a PRD to a narrative Markdown document."""
    if isinstance(prd, dict):
        prd = PRDSchema.model_validate(prd)

    lines = [
        f"# PRD — {prd.feature_name}",
        "",
        f"**Version:** {prd.version}  |  **Score:** {prd.quality_score}/10.0  |  **Consensus:** {'Yes' if prd.consensus_reached else 'No'}",
        "",
        "---",
        "",
        "## Objective",
        "",
        prd.objective,
        "",
        "---",
        "",
        "## Macro Impact",
        "",
        f"- **Modules affected:** {', '.join(prd.macro_impact.modules_affected)}",
        f"- **Risk level:** {prd.macro_impact.risk_level}",
        f"- **Performance impact:** {prd.macro_impact.performance_impact}",
        f"- **Security impact:** {prd.macro_impact.security_impact}",
        "",
        "---",
        "",
        "## User Stories",
        "",
    ]

    for us in prd.user_stories:
        lines.extend([
            f"### {us.id} — {us.title}",
            "",
            us.description,
            "",
            "**Acceptance criteria:**",
            "",
        ])
        for ac in us.acceptance_criteria:
            lines.append(f"- {ac}")
        lines.extend([
            "",
            f"**Effort:** {us.effort}",
            "",
        ])
        if us.dependencies:
            lines.append(f"**Dependencies:** {', '.join(us.dependencies)}")
            lines.append("")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Anti-Drift Questions",
        "",
    ])
    for q in prd.anti_drift_questions:
        lines.append(f"- **{q.question}** — {q.answer}")
    lines.append("")

    lines.extend([
        "---",
        "",
        "## Final Validation",
        "",
        prd.final_validation_notes.strip(),
        "",
    ])

    return "\n".join(lines).strip() + "\n"


def _slugify(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "prd"


def _parse_frontmatter(md_text: str) -> dict:
    """Extract YAML frontmatter as a dict from the start of md_text.

    Strategy:
    - Prefer yaml.safe_load if PyYAML is available (handles multiline and special chars).
    - Fallback: simple parser for "key: value" style lines inside the top-most frontmatter block.

    Returns a dict of parsed frontmatter keys/values (values are kept as loaded by yaml when available).
    """
    md_text = (md_text or "").lstrip()
    if not md_text.startswith("---"):
        return {}
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm_text = parts[1]

    if yaml is not None:
        try:
            loaded = yaml.safe_load(fm_text)
            if isinstance(loaded, dict):
                return loaded
            # if not dict, fall through to simple parser
        except Exception as e:
            logger.warning("Failed to parse frontmatter with PyYAML: %s. Falling back to simple parser.", e)

    # Fallback simple parser (best-effort): parse lines with 'key: value' and keep rest as string
    data: dict = {}
    for line in fm_text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        k, v = line.split(":", 1)
        data[k.strip()] = v.strip()
    if yaml is None:
        logger.debug("Using fallback frontmatter parser; consider installing PyYAML for robust parsing.")
    return data


def validate_consistency(
    md_path: Path,
    json_path: Path,
    prd: PRDSchema,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> ValidationResult:
    """Validates consistency between the generated Markdown and the PRD/JSON.

    Checks implemented:
    - required headers present in MD (simple existence checks)
    - quality_score in frontmatter matches prd.quality_score
    - vision_hash in frontmatter matches current VISION.md hash (if present in frontmatter)
    - JSON (from json_path) contains expected core fields that match the PRDSchema instance (feature_name, version, quality_score, consensus_reached)

    The json_path is actively used to cross-check that the serialized JSON matches the in-memory PRD and the MD frontmatter.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Read MD
    try:
        md_text = md_path.read_text(encoding="utf-8")
    except Exception as e:
        return ValidationResult(is_valid=False, errors=[f"Could not read MD file {md_path}: {e}"], warnings=[])

    front = _parse_frontmatter(md_text)

    # 1) required headers
    required_headers = ["# Objective", "## Macro Impact", "## User Stories", "## Anti-Drift Questions"]
    body = md_text
    # if frontmatter present, strip it for header checks
    if md_text.lstrip().startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    for hdr in required_headers:
        if hdr not in body:
            errors.append(f"Missing required header in MD: {hdr}")

    # 2) quality_score match between frontmatter and prd
    fm_quality = front.get("quality_score")
    try:
        if fm_quality is not None:
            # allow numeric or string
            fm_q = float(fm_quality)
            if abs(fm_q - float(prd.quality_score)) > 0.0001:
                errors.append(f"quality_score mismatch: MD={fm_q} vs PRD={prd.quality_score}")
        else:
            warnings.append("quality_score not found in MD frontmatter")
    except Exception:
        errors.append(f"Invalid quality_score value in MD frontmatter: {fm_quality}")

    # 3) vision_hash
    fm_vision = front.get("vision_hash")
    vision_hash_current = get_vision_hash(vision_context)
    if vision_hash_current is None:
        warnings.append("Could not read vision document to verify vision_hash")

    if fm_vision:
        if vision_hash_current is None:
            errors.append("MD contains vision_hash but the vision document could not be read to verify it")
        elif str(fm_vision) != vision_hash_current:
            errors.append("vision_hash in MD does not match current vision document")
    else:
        # it's acceptable for MD to omit vision_hash; warn
        warnings.append("vision_hash not present in MD frontmatter")

    # 4) JSON cross-check
    try:
        json_text = Path(json_path).read_text(encoding="utf-8")
        json_obj = json.loads(json_text)
    except Exception as e:
        errors.append(f"Could not read/parse JSON file {json_path}: {e}")
        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    # Check essential fields in JSON match PRDSchema instance
    def _get_js_field(obj: dict, key: str):
        return obj.get(key)

    js_feature = _get_js_field(json_obj, "feature_name")
    js_version = _get_js_field(json_obj, "version")
    js_quality = _get_js_field(json_obj, "quality_score")
    js_consensus = _get_js_field(json_obj, "consensus_reached")

    if js_feature is None:
        errors.append("JSON missing required field: feature_name")
    else:
        if js_feature != prd.feature_name:
            errors.append(f"feature_name mismatch: JSON={js_feature} vs PRD={prd.feature_name}")

    if js_version is None:
        errors.append("JSON missing required field: version")
    else:
        if str(js_version) != str(prd.version):
            errors.append(f"version mismatch: JSON={js_version} vs PRD={prd.version}")

    if js_quality is None:
        errors.append("JSON missing required field: quality_score")
    else:
        try:
            js_q = float(js_quality)
            if abs(js_q - float(prd.quality_score)) > 0.0001:
                errors.append(f"quality_score mismatch: JSON={js_q} vs PRD={prd.quality_score}")
        except Exception:
            errors.append(f"Invalid quality_score in JSON: {js_quality}")

    if js_consensus is None:
        errors.append("JSON missing required field: consensus_reached")
    else:
        if bool(js_consensus) != bool(prd.consensus_reached):
            errors.append(f"consensus_reached mismatch: JSON={js_consensus} vs PRD={prd.consensus_reached}")

    is_valid = len(errors) == 0
    return ValidationResult(is_valid=is_valid, errors=errors, warnings=warnings)


def render_markdown(
    prd: PRDSchema,
    config: ExportConfig,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> str:
    """Renders the final Markdown with metadata frontmatter and body generated from the schema.

    Frontmatter (YAML) includes:
      - quality_score
      - validation_status
      - generated_at (UTC ISO)
      - vision_hash (SHA-256 of the active vision document) ONLY if available

    The body contains the sections: # Objective, ## Macro Impact, ## User Stories, ## Anti-Drift Questions.
    """
    vision_hash = get_vision_hash(vision_context)
    if vision_hash is None:
        logger.debug("Could not read vision document to compute hash; continuing without vision_hash.")

    quality = getattr(prd, "quality_score", None)
    # determine validation status: prefer explicit field, else derive from consensus_reached
    validation_status = getattr(prd, "validation_status", None)
    if validation_status is None:
        validation_status = "approved" if getattr(prd, "consensus_reached", False) else "unapproved"

    generated_at = datetime.now(tz=timezone.utc).isoformat()

    front: List[str] = ["---",]
    if quality is not None:
        front.append(f"quality_score: {quality}")
    if validation_status is not None:
        front.append(f"validation_status: {validation_status}")
    if generated_at:
        front.append(f"generated_at: {generated_at}")
    if vision_hash:
        front.append(f"vision_hash: {vision_hash}")
    front.extend(["---", ""])

    # build body with strict section headings mapped to schema
    if isinstance(prd, dict):
        prd = PRDSchema.model_validate(prd)

    body_lines: List[str] = []
    # Objective (top-level as requested)
    body_lines.append(f"# Objective")
    body_lines.append("")
    body_lines.append(prd.objective)
    body_lines.append("")

    # Macro Impact
    body_lines.append("## Macro Impact")
    body_lines.append("")
    mi = prd.macro_impact
    body_lines.append(f"- Modules affected: {', '.join(mi.modules_affected)}")
    body_lines.append(f"- Risk level: {mi.risk_level}")
    body_lines.append(f"- Performance impact: {mi.performance_impact}")
    body_lines.append(f"- Security impact: {mi.security_impact}")
    body_lines.append("")

    # User Stories
    body_lines.append("## User Stories")
    body_lines.append("")
    for us in prd.user_stories:
        body_lines.append(f"### {us.id} — {us.title}")
        body_lines.append("")
        body_lines.append(us.description)
        body_lines.append("")
        body_lines.append("**Acceptance criteria:**")
        body_lines.append("")
        for ac in us.acceptance_criteria:
            body_lines.append(f"- {ac}")
        body_lines.append("")
        body_lines.append(f"**Effort:** {us.effort}")
        body_lines.append("")
        if getattr(us, "dependencies", None):
            body_lines.append(f"**Dependencies:** {', '.join(us.dependencies)}")
            body_lines.append("")

    # Anti-Drift Questions
    body_lines.append("## Anti-Drift Questions")
    body_lines.append("")
    for q in prd.anti_drift_questions:
        body_lines.append(f"- **{q.question}** — {q.answer}")
    body_lines.append("")

    if getattr(prd, "vision_hash", None):
        body_lines.append("## Runtime Provenance")
        body_lines.append("")
        body_lines.append(f"- vision_hash: {prd.vision_hash}")
        if getattr(prd, "source_prd_path", None):
            body_lines.append(f"- source_prd_path: {prd.source_prd_path}")
        body_lines.append("")

    # join frontmatter and body; ensure UTF-8 when writing elsewhere
    return "\n".join(front + body_lines)


class PRDExporter:
    """Dual exporter for PRD: generates JSON and/or Markdown according to ExportConfig.

    Behavior:
      - Writes JSON first (safe for pipelines). If MD is also requested, writes MD after.
      - If MD write fails after JSON was written, attempts to rollback the JSON file and raises ExportException.
      - Returns list of pathlib.Path objects pointing to the files actually created (respecting config.output_format).
    """

    def export(self, prd: PRDSchema, config: ExportConfig) -> List[Path]:
        created: List[Path] = []

        # Ensure output dir exists
        out_dir = Path(config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Prepare filenames using a slug of the feature name and version
        slug = _slugify(getattr(prd, 'feature_name', None) or '')
        version = getattr(prd, 'version', None) or datetime.utcnow().strftime('%Y%m%d%H%M%S')

        json_path = out_dir / f"{slug}-{version}.json"
        md_path = out_dir / f"{slug}-{version}.md"

        # Helper to write JSON
        def _write_json():
            try:
                json_text = prd.model_dump_json(indent=2)
            except Exception as e:
                logger.exception("Failed to serialize PRD to JSON: %s", e)
                raise ExportException(f"Failed to serialize PRD to JSON: {e}")

            try:
                json_path.write_text(json_text, encoding='utf-8')
                created.append(json_path)
                logger.info("Wrote JSON PRD to %s", json_path)
            except Exception as e:
                logger.exception("Failed to write JSON file %s: %s", json_path, e)
                raise ExportException(f"Failed to write JSON file {json_path}: {e}")

        # Helper to write MD
        def _write_md():
            try:
                md_text = render_markdown(prd, config)
            except Exception as e:
                logger.exception("Failed to render Markdown: %s", e)
                raise ExportException(f"Failed to render Markdown: {e}")

            try:
                md_path.write_text(md_text, encoding='utf-8')
                created.append(md_path)
                logger.info("Wrote Markdown PRD to %s", md_path)
            except Exception as e:
                logger.exception("Failed to write MD file %s: %s", md_path, e)
                raise ExportException(f"Failed to write MD file {md_path}: {e}")

        fmt = (config.output_format or 'json').lower()

        # Perform writes according to requested format, ensuring atomic rollback behavior when writing both
        if fmt == 'json':
            _write_json()
            return created

        if fmt == 'md':
            # MD only: just write markdown
            _write_md()
            return created

        if fmt == 'both':
            # Write JSON first
            try:
                _write_json()
            except ExportException:
                # JSON failure; nothing to rollback
                raise

            # Then write MD; if MD fails, remove the JSON file and raise
            try:
                _write_md()
            except ExportException as e:
                # attempt rollback of JSON
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

        # Unknown format: be defensive and raise
        raise ExportException(f"Unknown output format: {config.output_format}")
