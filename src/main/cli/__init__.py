"""Compatibility package exposing the CLI entrypoint module."""

from __future__ import annotations

import sys as _sys

from . import commands as _commands
from . import entrypoint as _entrypoint
from .entrypoint import (
    _command_requires_api,
    _command_requires_vision,
    app,
    cmd_help,
    cmd_prd,
    main,
    os,
    sys,
)

commands = _commands

__all__ = [
    "app",
    "cmd_help",
    "cmd_prd",
    "commands",
    "main",
    "os",
    "sys",
    "_command_requires_api",
    "_command_requires_vision",
]

setattr(_entrypoint, "commands", _commands)
_sys.modules[__name__] = _entrypoint

