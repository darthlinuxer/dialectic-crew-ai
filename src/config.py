from enum import Enum
from typing import Any
from pydantic import BaseSettings, validator, ValidationError, Field
import logging

logger = logging.getLogger(__name__)


class PRDOutputFormat(str, Enum):
    JSON = "json"
    MD = "md"
    BOTH = "both"

    @classmethod
    def from_str(cls, value: str) -> "PRDOutputFormat":
        v = (value or "").strip().lower()
        try:
            return cls(v)
        except ValueError:
            raise ValueError(f"invalid PRD_OUTPUT_FORMAT '{value}'; allowed: md, json, both")


class Settings(BaseSettings):
    prd_output_format: PRDOutputFormat = Field(PRDOutputFormat.JSON, env="PRD_OUTPUT_FORMAT")
    crewai_tracing_enabled: bool = Field(False, env="CREWAI_TRACING_ENABLED")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("prd_output_format", pre=True)
    def validate_prd_output_format(cls, v: Any) -> PRDOutputFormat:
        if v is None or (isinstance(v, str) and v.strip() == ""):
            return PRDOutputFormat.JSON
        if isinstance(v, PRDOutputFormat):
            return v
        try:
            return PRDOutputFormat.from_str(str(v))
        except ValueError as e:
            raise ValueError(str(e))


def load_settings() -> Settings:
    try:
        s = Settings()
        logger.debug("Loaded settings: prd_output_format=%s, crewai_tracing_enabled=%s",
                     s.prd_output_format, s.crewai_tracing_enabled)
        return s
    except ValidationError as e:
        logger.error("Invalid configuration: %s", e)
        raise
