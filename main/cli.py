#!/usr/bin/env python3
"""CLI mínimo para executar o fluxo dialético (prd) e sobrescrever --output-format temporariamente.

Usage:
  python -m main.cli "Feature request text" [--output-format {md,json,both}]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dialectic.prd_flow import run_dialectic_flow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Dialectic PRD flow and export results.")
    parser.add_argument("feature", help="Feature request / objective to generate a PRD for")
    parser.add_argument("--output-format", choices=["md", "json", "both"], help="Temporarily override PRD_OUTPUT_FORMAT for this run")
    args = parser.parse_args(argv)

    # Optionally override environment variable for this run
    if args.output_format:
        os.environ["PRD_OUTPUT_FORMAT"] = args.output_format
        print(f"NOTE: PRD_OUTPUT_FORMAT overridden for this run -> {args.output_format}")

    vision_path = Path("VISION.md")
    if vision_path.exists():
        vision_content = vision_path.read_text(encoding="utf-8")
    else:
        print("Warning: VISION.md not found in current directory; passing empty vision_content.")
        vision_content = ""

    result = run_dialectic_flow(args.feature, vision_content)

    print("\n--- Run summary ---")
    print(f"success: {result.get('success')}")
    print(f"quality_score: {result.get('quality_score')}")
    print(f"iterations: {result.get('iterations')}")
    print(f"consensus_reached: {result.get('consensus_reached')}")

    return 0 if result.get("success") else 2


if __name__ == "__main__":
    raise SystemExit(main())
