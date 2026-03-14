"""CLI and self-improvement entry points for Dialectic Crew AI."""

from . import cleanup_commands
from . import vision_commands


def cli_main(*args, **kwargs):
    """Run the CLI entrypoint lazily to avoid heavyweight imports during package import."""
    from .cli import main  # pylint: disable=import-outside-toplevel

    return main(*args, **kwargs)


def run_self_improve(*args, **kwargs):
    """Run the self-improve entrypoint lazily to avoid import cycles at package import time."""
    from .self_improve import (  # pylint: disable=import-outside-toplevel
        run_self_improve as _run_self_improve,
    )

    return _run_self_improve(*args, **kwargs)


__all__ = ["cli_main", "run_self_improve", "vision_commands", "cleanup_commands"]
