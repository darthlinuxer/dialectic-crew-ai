"""
Script simplificado para executar uma única passagem do fluxo dialético (sem retry).
Delega para dialectic.prd_flow com max_retries=0.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv()

from dialectic.state import DialecticState
from dialectic.prd_flow import DialecticFlow


if __name__ == "__main__":
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Teste"

    if os.path.exists("VISION.md"):
        with open("VISION.md", "r", encoding="utf-8") as f:
            vision = f.read()
    else:
        vision = "Projeto de gestão de projetos ágeis"

    state = DialecticState(
        feature_objective=feature,
        vision_content=vision,
        max_retries=0,
    )
    flow = DialecticFlow(state)
    result = flow.kickoff()

    print(f"\nScore Final: {result.quality_score}/10.0")
    print(f"Consenso: {result.consensus_reached}")
