"""
Convenience script to run the full dialectic flow.
Delegates to dialectic.prd_flow which uses native CrewAI features
(output_pydantic, guardrails, Flow pattern).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv()

from dialectic.prd_flow import run_dialectic_flow


if __name__ == "__main__":
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test"

    if os.path.exists("VISION.md"):
        with open("VISION.md", "r", encoding="utf-8") as f:
            vision = f.read()
    else:
        vision = "Agile project management project"

    result = run_dialectic_flow(feature, vision)
    print(f"\nFinal Score: {result['quality_score']}/10.0")
    print(f"Consensus: {result['consensus_reached']}")
    print(f"Iterations: {result['iterations']}")
