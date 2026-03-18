"""Regression checks for Flow decorator wiring conventions."""

import inspect
import re

import dialectic.prd_flow as prd_flow
from execution.task_flow import TaskExecutionFlow


def _assert_no_string_method_refs(flow_cls):
    source = inspect.getsource(flow_cls)
    method_names = {
        name
        for name, obj in inspect.getmembers(flow_cls, inspect.isfunction)
        if obj.__qualname__.startswith(f"{flow_cls.__name__}.")
    }

    for target in re.findall(r'@listen\(["\']([^"\']+)["\']\)', source):
        assert target not in method_names, (
            f"{flow_cls.__name__} should use a direct method reference for listen target "
            f"{target!r} instead of a string literal"
        )

    for _, _, args in re.findall(r"@(listen|start)\((or_|and_)\((.*?)\)\)", source):
        assert '"' not in args and "'" not in args, (
            f"{flow_cls.__name__} should use direct method references inside composite "
            f"listeners, got: {args}"
        )


def test_flow_subclasses_do_not_use_string_method_refs_in_decorators():
    _assert_no_string_method_refs(prd_flow.DialecticFlow)
    _assert_no_string_method_refs(TaskExecutionFlow)
