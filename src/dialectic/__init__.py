"""
Núcleo dialético: agentes, tools, estado, fluxo PRD e export.
"""

from dialectic.agents import (
    visionario,
    critico_socratico,
    sintetizador,
    validador_macro,
)
from dialectic.state import DialecticState
from dialectic.prd_flow import DialecticFlow, run_dialectic_flow, OUTPUT_DIR
from dialectic.export import prd_to_markdown, execution_plan_to_markdown

__all__ = [
    "visionario",
    "critico_socratico",
    "sintetizador",
    "validador_macro",
    "DialecticState",
    "DialecticFlow",
    "run_dialectic_flow",
    "OUTPUT_DIR",
    "prd_to_markdown",
    "execution_plan_to_markdown",
]
