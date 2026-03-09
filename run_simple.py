"""
Simplified script to run a single pass of the dialectic flow (no retry).
Delegates to dialectic.prd_flow with max_retries=0.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv()

from dialectic.state import DialecticState
from dialectic.prd_flow import DialecticFlow


if __name__ == "__main__":
    feature = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Test"

    if os.path.exists("VISION.md"):
        with open("VISION.md", "r", encoding="utf-8") as f:
            vision = f.read()
    else:
        vision = "Agile project management project"

    state = DialecticState(
        feature_objective=feature,
        vision_content=vision,
        max_retries=0,
    )
    flow = DialecticFlow(state)
    result = flow.kickoff()

    print(f"\nFinal Score: {result.quality_score}/10.0")
    print(f"Consensus: {result.consensus_reached}")
