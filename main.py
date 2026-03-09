#!/usr/bin/env python3
"""Bootstrap: adds src/ to path and delegates to the real CLI."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from main.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
