#!/usr/bin/env python3
"""Bootstrap: adds src/ to path and delegates to the real CLI."""
# pylint: disable=wrong-import-position,consider-using-from-import

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
MAIN_PACKAGE_DIR = os.path.join(SRC_DIR, "main")

sys.path.insert(0, SRC_DIR)

# Help static analyzers and imports treat this bootstrap module as a package-like
# shim that exposes the real implementation from src/main/.
__path__ = [MAIN_PACKAGE_DIR]

import src.main.self_improve as self_improve  # noqa: E402
import src.main.self_improve.git_helpers as git_helpers  # noqa: E402
import src.main.self_improve.pr_builder as pr_builder  # noqa: E402
from src.main import cli_main, run_self_improve  # noqa: E402

sys.modules.setdefault("main.git_helpers", git_helpers)
sys.modules.setdefault("main.pr_builder", pr_builder)
sys.modules.setdefault("main.self_improve", self_improve)


def main(*args, **kwargs):
    """Run the canonical CLI entrypoint through the src.main package surface."""
    return cli_main(*args, **kwargs)

__all__ = [
    "cli_main",
    "git_helpers",
    "main",
    "pr_builder",
    "run_self_improve",
    "self_improve",
]

if __name__ == "__main__":
    main()
