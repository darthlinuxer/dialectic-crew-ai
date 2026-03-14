# ruff: noqa: E402

"""
Convenience script: plans execution of a user story (dialectic).
Equivalent to: python main.py plan [prd_path] [US-001]

Usage:
  python run_user_story_dialectic.py [prd_path.json] [US-001]
  python run_user_story_dialectic.py   # latest PRD, first US
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from dotenv import load_dotenv
load_dotenv()

from planning.flow import run_user_story_planning


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    prd_path = args[0] if args else None
    us_ref = args[1] if len(args) > 1 else None

    if prd_path and not os.path.exists(prd_path):
        print(f"PRD not found: {prd_path}")
        sys.exit(1)

    result = run_user_story_planning(prd_path, us_ref)
    print(f"Score: {result['quality_score']}/10.0")


if __name__ == "__main__":
    main()
