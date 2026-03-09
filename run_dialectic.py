"""
Script de conveniência para executar o fluxo dialético completo.
Delega para dialectic.prd_flow que usa features nativas do CrewAI
(output_pydantic, guardrails, Flow pattern).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv()

from dialectic.prd_flow import run_dialectic_flow


if __name__ == "__main__":
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Teste"

    if os.path.exists("VISION.md"):
        with open("VISION.md", "r", encoding="utf-8") as f:
            vision = f.read()
    else:
        vision = "Projeto de gestão de projetos ágeis"

    result = run_dialectic_flow(feature, vision)
    print(f"\nScore Final: {result['quality_score']}/10.0")
    print(f"Consenso: {result['consensus_reached']}")
    print(f"Iterações: {result['iterations']}")
