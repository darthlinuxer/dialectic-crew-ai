"""
Dialectic core: agents, tools, state, PRD flow, and export.
"""

from dialectic.agents import (
    create_visionario,
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    create_implementer,
)
from dialectic.knowledge import vision_knowledge
from dialectic.markdown_renderers import prd_to_markdown, execution_plan_to_markdown
from dialectic.prd_exporter import PRDExporter
from dialectic.export_validation import validate_consistency
from dialectic.state import DialecticState
from dialectic.prd_flow import DialecticFlow, run_dialectic_flow, OUTPUT_DIR
from dialectic import prd_runtime
from dialectic import prioritize_runtime
from dialectic.vision import VisionContext

__all__ = [
    "create_visionario",
    "create_critico_socratico",
    "create_sintetizador",
    "create_validador_macro",
    "create_implementer",
    "vision_knowledge",
    "VisionContext",
    "DialecticState",
    "DialecticFlow",
    "run_dialectic_flow",
    "OUTPUT_DIR",
    "prd_runtime",
    "prioritize_runtime",
    "PRDExporter",
    "validate_consistency",
    "prd_to_markdown",
    "execution_plan_to_markdown",
]
