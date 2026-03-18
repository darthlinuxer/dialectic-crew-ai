from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import List

from dialectic.dependency_graph import validate_user_story_dependencies
from dialectic.vision import VisionContext, get_vision_hash
from schemas import PRDSchema

logger = logging.getLogger(__name__)

try:
    import yaml  # type: ignore
except Exception:
    yaml = None
    logger.debug(
        "PyYAML not available; frontmatter parsing will use a simple fallback. "
        "For robust parsing, install PyYAML."
    )


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]


def _parse_frontmatter(md_text: str | None) -> dict:
    """Extract YAML frontmatter as a dict from the start of md_text."""
    md_text = (md_text or "").lstrip()
    if not md_text.startswith("---"):
        return {}
    parts = md_text.split("---", 2)
    if len(parts) < 3:
        return {}
    frontmatter_text = parts[1]

    if yaml is not None:
        try:
            loaded = yaml.safe_load(frontmatter_text)
            if isinstance(loaded, dict):
                return loaded
        except Exception as exc:
            logger.warning(
                "Failed to parse frontmatter with PyYAML: %s. Falling back to simple parser.",
                exc,
            )

    data: dict = {}
    for line in frontmatter_text.splitlines():
        if not line.strip() or ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip()
    if yaml is None:
        logger.debug(
            "Using fallback frontmatter parser; consider installing PyYAML for robust parsing."
        )
    return data


def validate_consistency(
    md_path: Path,
    json_path: Path,
    prd: PRDSchema,
    vision_context: VisionContext = VisionContext.PROJECT,
) -> ValidationResult:
    """Validate consistency between the generated Markdown and PRD/JSON artifacts."""
    errors: List[str] = []
    warnings: List[str] = []

    try:
        md_text = md_path.read_text(encoding="utf-8")
    except Exception as exc:
        return ValidationResult(
            is_valid=False,
            errors=[f"Could not read MD file {md_path}: {exc}"],
            warnings=[],
        )

    frontmatter = _parse_frontmatter(md_text)

    required_headers = [
        "# Objective",
        "## Macro Impact",
        "## User Stories",
        "## Anti-Drift Questions",
    ]
    body = md_text
    if md_text.lstrip().startswith("---"):
        parts = md_text.split("---", 2)
        if len(parts) >= 3:
            body = parts[2]
    for header in required_headers:
        if header not in body:
            errors.append(f"Missing required header in MD: {header}")

    frontmatter_quality = frontmatter.get("quality_score")
    try:
        if frontmatter_quality is not None:
            quality = float(frontmatter_quality)
            if abs(quality - float(prd.quality_score)) > 0.0001:
                errors.append(
                    f"quality_score mismatch: MD={quality} vs PRD={prd.quality_score}"
                )
        else:
            warnings.append("quality_score not found in MD frontmatter")
    except Exception:
        errors.append(
            f"Invalid quality_score value in MD frontmatter: {frontmatter_quality}"
        )

    frontmatter_vision_hash = frontmatter.get("vision_hash")
    current_vision_hash = get_vision_hash(vision_context)
    if current_vision_hash is None:
        warnings.append("Could not read vision document to verify vision_hash")

    if frontmatter_vision_hash:
        if current_vision_hash is None:
            errors.append(
                "MD contains vision_hash but the vision document could not be read to verify it"
            )
        elif str(frontmatter_vision_hash) != current_vision_hash:
            errors.append("vision_hash in MD does not match current vision document")
    else:
        warnings.append("vision_hash not present in MD frontmatter")

    try:
        json_object = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Could not read/parse JSON file {json_path}: {exc}")
        return ValidationResult(
            is_valid=len(errors) == 0, errors=errors, warnings=warnings
        )

    json_feature = json_object.get("feature_name")
    json_version = json_object.get("version")
    json_quality = json_object.get("quality_score")
    json_consensus = json_object.get("consensus_reached")

    if json_feature is None:
        errors.append("JSON missing required field: feature_name")
    elif json_feature != prd.feature_name:
        errors.append(
            f"feature_name mismatch: JSON={json_feature} vs PRD={prd.feature_name}"
        )

    if json_version is None:
        errors.append("JSON missing required field: version")
    elif str(json_version) != str(prd.version):
        errors.append(f"version mismatch: JSON={json_version} vs PRD={prd.version}")

    if json_quality is None:
        errors.append("JSON missing required field: quality_score")
    else:
        try:
            quality = float(json_quality)
            if abs(quality - float(prd.quality_score)) > 0.0001:
                errors.append(
                    f"quality_score mismatch: JSON={quality} vs PRD={prd.quality_score}"
                )
        except Exception:
            errors.append(f"Invalid quality_score in JSON: {json_quality}")

    if json_consensus is None:
        errors.append("JSON missing required field: consensus_reached")
    elif bool(json_consensus) != bool(prd.consensus_reached):
        errors.append(
            f"consensus_reached mismatch: JSON={json_consensus} vs PRD={prd.consensus_reached}"
        )

    errors.extend(validate_user_story_dependencies(prd.user_stories))

    return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)
