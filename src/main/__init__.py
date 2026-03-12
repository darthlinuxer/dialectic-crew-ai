"""CLI and self-improvement entry points for Dialectic Crew AI."""


def cli_main(*args, **kwargs):
    from main.cli import main

    return main(*args, **kwargs)


def run_self_improve(*args, **kwargs):
    from main.self_improve import run_self_improve as _run_self_improve

    return _run_self_improve(*args, **kwargs)


__all__ = ["cli_main", "run_self_improve"]
