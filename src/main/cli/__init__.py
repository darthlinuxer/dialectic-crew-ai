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
_package_module = _sys.modules[__name__]
_package_path = list(getattr(_package_module, "__path__", []))
_package_spec = getattr(_package_module, "__spec__", None)

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
_entrypoint.__package__ = __name__
if _package_path:
    _entrypoint.__path__ = _package_path
if _package_spec is not None:
    _entrypoint.__spec__ = _package_spec
_sys.modules[__name__] = _entrypoint
