"""Public interface tests for the refactored self-improve package."""

from __future__ import annotations

from src.main import self_improve
from src.main.self_improve import (
    code_structure,
    git_helpers,
    llm_retries,
    metrics,
    paths,
    persistence,
    pr_builder,
    quality_gate,
    runtime,
    test_runner,
)


def test_self_improve_package_exports_expected_entrypoints():
    expected = {
        "PROTECTED_PATHS",
        "SIMULATION_BRANCH_NAME",
        "_build_pr_body",
        "_list_resumable_cycles",
        "_save_self_improve_record",
        "run_self_improve",
    }
    assert expected.issubset(set(self_improve.__all__))


def test_support_modules_publish_explicit_public_apis():
    assert {
        "run_cmd",
        "git_branch_create",
        "git_discard_branch",
    }.issubset(set(git_helpers.__all__))
    assert {
        "save_self_improve_record",
        "load_self_improve_record",
        "list_resumable_cycles",
    }.issubset(set(persistence.__all__))
    assert {
        "run_quality_gate",
        "print_quality_gate_result",
    }.issubset(set(quality_gate.__all__))
    assert {
        "validate_code_structure",
        "print_structure_validation_result",
    }.issubset(set(code_structure.__all__))
    assert {
        "self_improve_test_timeout",
        "snapshot_tests",
    }.issubset(set(test_runner.__all__))
    assert {"create_pr", "build_pr_body"}.issubset(set(pr_builder.__all__))
    assert {"metrics_stable"} == set(metrics.__all__)
    assert {
        "_command_available",
        "_self_improve_test_timeout",
    }.issubset(set(runtime.__all__))
    assert {
        "_run_with_transient_llm_retries",
        "_is_transient_llm_error",
    }.issubset(set(llm_retries.__all__))
    assert {
        "PROTECTED_PATHS",
        "SELF_IMPROVE_STATE_DIR",
        "SIMULATION_BRANCH_NAME",
    }.issubset(set(paths.__all__))

