#!/usr/bin/env python3
"""Bootstrap: adds src/ to path and delegates to the real CLI."""
import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
MAIN_PACKAGE_DIR = os.path.join(SRC_DIR, "main")

sys.path.insert(0, SRC_DIR)

# Help static analyzers and imports treat this bootstrap module as a package-like
# shim that exposes the real implementation from src/main/.
__path__ = [MAIN_PACKAGE_DIR]

from src.main import cli as cli  # noqa: E402
from src.main import git_helpers as git_helpers  # noqa: E402
from src.main import pr_builder as pr_builder  # noqa: E402
from src.main import self_improve as self_improve  # noqa: E402
from src.main import cli_main, run_self_improve  # noqa: E402
from src.main.cli import main  # noqa: E402

sys.modules.setdefault("main.cli", cli)
sys.modules.setdefault("main.git_helpers", git_helpers)
sys.modules.setdefault("main.pr_builder", pr_builder)
sys.modules.setdefault("main.self_improve", self_improve)

__all__ = [
    "cli",
    "cli_main",
    "git_helpers",
    "main",
    "pr_builder",
    "run_self_improve",
    "self_improve",
]

if __name__ == "__main__":
    main()
