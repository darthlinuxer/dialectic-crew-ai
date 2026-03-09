"""Loader robusto para configuração de exportação PRD.

Regras:
- Lê PRD_OUTPUT_FORMAT e PRD_OUTPUT_DIR a partir do ambiente (.env via pydantic-settings quando disponível).
- PRD_OUTPUT_FORMAT:
    * valores válidos (case-insensitive): 'md', 'json', 'both'
    * se ausente OU inválido -> fallback seguro: 'json' (e log warning)
    * valor retornado é normalizado para lowercase
- PRD_OUTPUT_DIR:
    * se ausente -> Path('prd_output')
    * deve ser retornado como pathlib.Path

O loader tenta usar pydantic-settings (BaseSettings). Se a dependência não estiver
instalada ou for incompatível, o módulo faz um fallback gracioso usando os.environ
(e não falha em import-time). Em todos os casos, situações de fallback são
registradas via logger para visibilidade em CI/execuções locais.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

_VALID_FORMATS = ("md", "json", "both")


@dataclass
class ExportConfig:
    """Dataclass representando a configuração de exportação.

    Possui validação mínima em __post_init__ para garantir que o objeto seja
    confiável em runtime (mesmo que a fonte das variáveis de ambiente seja
    questionável).
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
            raise ValueError(f"invalid output_format '{self.output_format}'; must be one of {_VALID_FORMATS}")

        self.output_format = fmt  # type: ignore[assignment]

        # coerce output_dir to Path
        if not isinstance(self.output_dir, Path):
            self.output_dir = Path(self.output_dir)


# Try to import pydantic-settings; if unavailable, fallback to os.environ loader.
try:
    from pydantic import Field
    from pydantic_settings import BaseSettings, SettingsConfigDict

    _HAS_PYDANTIC_SETTINGS = True
except Exception:  # broad except to tolerate ImportError or API changes
    _HAS_PYDANTIC_SETTINGS = False


if _HAS_PYDANTIC_SETTINGS:
    class _ExportSettings(BaseSettings):
        # Note: intentionally using simple types; validation/coercion is minimal here
        PRD_OUTPUT_FORMAT: Optional[str] = None  # don't default to 'both' to allow "absent -> fallback 'json'"
        PRD_OUTPUT_DIR: Optional[Path] = None

        model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')


def _load_from_environ_fallback() -> tuple[Optional[str], Optional[str]]:
    """Fallback loader that reads from os.environ if pydantic-settings is not available.

    Returns a tuple (format_raw, dir_raw) where values may be None.
    """
    fmt = os.environ.get('PRD_OUTPUT_FORMAT')
    d = os.environ.get('PRD_OUTPUT_DIR')
    return fmt, d


def get_export_config() -> ExportConfig:
    """Carrega a configuração de exportação e retorna ExportConfig.

    Regras de normalização/validação (implementadas):
    - Se PRD_OUTPUT_FORMAT ausente OU inválido -> fallback 'json' e log WARNING
    - Se presente e válido (case-insensitive) -> normaliza para lowercase
    - PRD_OUTPUT_DIR é resolvido para Path; se ausente -> Path('prd_output')

    A função tenta usar pydantic-settings quando disponível; caso contrário faz
    fallback para leitura direta de os.environ. Em ambos os casos, logs são
    escritos quando aplicável.
    """

    if _HAS_PYDANTIC_SETTINGS:
        try:
            settings = _ExportSettings()
            fmt_raw = settings.PRD_OUTPUT_FORMAT
            dir_raw = str(settings.PRD_OUTPUT_DIR) if settings.PRD_OUTPUT_DIR is not None else None
        except Exception as e:
            # If pydantic-settings fails at runtime (e.g., incompatible version),
            # fallback to environ and record warning.
            logger.warning("pydantic-settings unavailable or failed to load; falling back to environment: %s", e)
            fmt_raw, dir_raw = _load_from_environ_fallback()
    else:
        logger.warning("pydantic-settings not installed; using os.environ fallback for export config")
        fmt_raw, dir_raw = _load_from_environ_fallback()

    # Normalize and validate PRD_OUTPUT_FORMAT
    if fmt_raw is None or (isinstance(fmt_raw, str) and fmt_raw.strip() == ""):
        logger.warning("PRD_OUTPUT_FORMAT is absent or empty; using safe fallback 'json'")
        fmt = 'json'
    else:
        fmt_candidate = fmt_raw.lower().strip()
        if fmt_candidate not in _VALID_FORMATS:
            logger.warning("PRD_OUTPUT_FORMAT value '%s' is invalid; using safe fallback 'json'", fmt_raw)
            fmt = 'json'
        else:
            fmt = fmt_candidate

    # Resolve output dir
    if dir_raw is None or (isinstance(dir_raw, str) and dir_raw.strip() == ""):
        out_dir = Path('prd_output')
    else:
        out_dir = Path(dir_raw)

    # Construct ExportConfig (which will validate in __post_init__)
    try:
        cfg = ExportConfig(output_format=fmt, output_dir=out_dir)
    except ValueError as e:
        # This should not normally happen because we normalized above, but be defensive
        logger.warning("ExportConfig validation failed after normalization: %s; falling back to safe defaults", e)
        cfg = ExportConfig(output_format='json', output_dir=Path('prd_output'))

    return cfg
