"""
Dialectic core: agents, tools, state, PRD flow, and export.
"""

from dialectic.agents import (
    create_visionario,
    create_critico_socratico,
    create_sintetizador,
    create_validador_macro,
    create_implementer,
    vision_knowledge,
)
from dialectic.state import DialecticState
from dialectic.prd_flow import DialecticFlow, run_dialectic_flow, OUTPUT_DIR
from dialectic.export import prd_to_markdown, execution_plan_to_markdown

__all__ = [
    "create_visionario",
    "create_critico_socratico",
    "create_sintetizador",
    "create_validador_macro",
    "create_implementer",
    "vision_knowledge",
    "DialecticState",
    "DialecticFlow",
    "run_dialectic_flow",
    "OUTPUT_DIR",
    "prd_to_markdown",
    "execution_plan_to_markdown",
]
