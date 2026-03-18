"""Robust loader for PRD export configuration.

Rules:
- Reads PRD_OUTPUT_FORMAT and PRD_OUTPUT_DIR from the environment
    (.env via pydantic-settings when available).
- PRD_OUTPUT_FORMAT:
    * valid values (case-insensitive): 'md', 'json', 'both'
    * if absent OR invalid -> default to 'both' (and log warning)
    * returned value is normalized to lowercase
- PRD_OUTPUT_DIR:
    * if absent -> Path('prd_output')
    * must be returned as pathlib.Path

The loader tries to use pydantic-settings (BaseSettings). If the dependency is not
installed or is incompatible, the module falls back gracefully to os.environ
(and does not fail at import-time). In all cases, fallback situations are
logged via logger for visibility in CI/local runs.
"""

from __future__ import annotations

# pylint: disable=too-few-public-methods

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional, cast

logger = logging.getLogger(__name__)

_VALID_FORMATS = ("md", "json", "both")
_DEFAULT_OUTPUT_FORMAT: Literal["md", "json", "both"] = "both"
_PYDANTIC_FIELD: Any = None
_PydanticBaseSettings: type = object
_PydanticSettingsConfigDict: type = dict


@dataclass
class ExportConfig:
    """Dataclass representing the export configuration.

    Has minimal validation in __post_init__ to ensure the object is
    reliable at runtime (even if the source of environment variables is
    questionable).
    """

    output_format: Literal["md", "json", "both"] = "both"
    output_dir: Path = Path("prd_output")

    def __post_init__(self) -> None:
        # normalize/validate output_format
        if isinstance(self.output_format, str):
            fmt = self.output_format.lower()
        else:
            fmt = str(self.output_format)

        if fmt not in _VALID_FORMATS:
            raise ValueError(
                f"invalid output_format '{self.output_format}'; "
                f"must be one of {_VALID_FORMATS}"
            )

        self.output_format = fmt  # type: ignore[assignment]

        # coerce output_dir to Path
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)


# Try to import pydantic-settings; if unavailable, fallback to os.environ loader.
try:
    from pydantic import Field as _PYDANTIC_FIELD
    from pydantic_settings import BaseSettings as _PydanticBaseSettings
    from pydantic_settings import SettingsConfigDict as _PydanticSettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except (ImportError, AttributeError):
    _HAS_PYDANTIC_SETTINGS = False


if _HAS_PYDANTIC_SETTINGS:

    class _ExportSettings(_PydanticBaseSettings):  # pylint: disable=useless-object-inheritance
        # Note: intentionally using simple types; validation/coercion is minimal here
        prd_output_format: Optional[str] = _PYDANTIC_FIELD(
            default=None,
            validation_alias="PRD_OUTPUT_FORMAT",
        )  # keep None here so get_export_config() owns fallback/logging behavior
        prd_output_dir: Optional[Path] = _PYDANTIC_FIELD(
            default=None,
            validation_alias="PRD_OUTPUT_DIR",
        )

        model_config = _PydanticSettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            populate_by_name=True,
        )


def _load_from_environ_fallback() -> tuple[Optional[str], Optional[str]]:
    """Fallback loader that reads from os.environ if pydantic-settings is not available.

    Returns a tuple (format_raw, dir_raw) where values may be None.
    """
    fmt = os.environ.get("PRD_OUTPUT_FORMAT")
    d = os.environ.get("PRD_OUTPUT_DIR")
    return fmt, d


def get_export_config(*, _env_file: Optional[Path | str] = None) -> ExportConfig:
    """Load the export configuration and return an ExportConfig.

    Normalization/validation rules (implemented):
    - If PRD_OUTPUT_FORMAT is absent OR invalid -> fallback 'both' and log WARNING
    - If present and valid (case-insensitive) -> normalize to lowercase
    - PRD_OUTPUT_DIR is resolved to Path; if absent -> Path('prd_output')

    The function tries to use pydantic-settings when available; otherwise falls
    back to reading directly from os.environ. In both cases, logs are
    written when applicable.
    """

    if _HAS_PYDANTIC_SETTINGS:
        try:
            if _env_file is None:
                settings = _ExportSettings()
            else:
                settings_factory = cast(Any, _ExportSettings)
                settings = settings_factory(_env_file=_env_file)
            fmt_raw = settings.prd_output_format
            dir_raw = (
                str(settings.prd_output_dir)
                if settings.prd_output_dir is not None
                else None
            )
        except (AttributeError, OSError, TypeError, ValueError) as e:
            # If pydantic-settings fails at runtime (e.g., incompatible version),
            # fallback to environ and record warning.
            logger.warning(
                "pydantic-settings unavailable or failed to load; "
                "falling back to environment: %s",
                e,
            )
            fmt_raw, dir_raw = _load_from_environ_fallback()
    else:
        logger.warning(
            "pydantic-settings not installed; "
            "using os.environ fallback for export config"
        )
        fmt_raw, dir_raw = _load_from_environ_fallback()

    # Normalize and validate PRD_OUTPUT_FORMAT
    if fmt_raw is None or (isinstance(fmt_raw, str) and fmt_raw.strip() == ""):
        logger.warning(
            "PRD_OUTPUT_FORMAT is absent or empty; defaulting to '%s'",
            _DEFAULT_OUTPUT_FORMAT,
        )
        fmt = _DEFAULT_OUTPUT_FORMAT
    else:
        fmt_candidate = fmt_raw.lower().strip()
        if fmt_candidate not in _VALID_FORMATS:
            logger.warning(
                "PRD_OUTPUT_FORMAT value '%s' is invalid; defaulting to '%s'",
                fmt_raw,
                _DEFAULT_OUTPUT_FORMAT,
            )
            fmt = _DEFAULT_OUTPUT_FORMAT
        else:
            fmt = cast(Literal["md", "json", "both"], fmt_candidate)

    # Resolve output dir
    if dir_raw is None or (isinstance(dir_raw, str) and dir_raw.strip() == ""):
        out_dir = Path("prd_output")
    else:
        out_dir = Path(dir_raw)

    # Construct ExportConfig (which will validate in __post_init__)
    try:
        cfg = ExportConfig(output_format=fmt, output_dir=out_dir)
    except ValueError as e:
        # This should not normally happen because we normalized above, but be defensive
        logger.warning(
            "ExportConfig validation failed after normalization: %s; "
            "falling back to defaults",
            e,
        )
        cfg = ExportConfig(
            output_format=_DEFAULT_OUTPUT_FORMAT,
            output_dir=Path("prd_output"),
        )

    return cfg
