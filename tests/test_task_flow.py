"""Execution-flow regressions for TaskExecutionFlow routing."""

from pathlib import Path
from textwrap import dedent

from execution import local_verification
from execution.task_flow import (
    TaskExecutionFlow,
    _extract_generated_files,
    _materialize_generated_files,
    _run_local_verification_fallback,
)
from schemas import ValidationOutput, VerificationResult, TaskExecutionResult


def test_local_verification_module_docstring_scopes_supported_fallback_checks():
    docstring = local_verification.__doc__
    normalized_docstring = " ".join((docstring or "").split())

    assert docstring is not None
    assert "currently supported acceptance-check phrases" in normalized_docstring
    for phrase in local_verification._SUPPORTED_FALLBACK_PHRASES:
        assert phrase in normalized_docstring
    assert (
        "Future roadmap-specific phrases belong in prompt/test data until "
        "the repo ships those artifacts"
    ) in normalized_docstring


def test_task_execution_flow_kickoff_runs_dialectic_and_verify(monkeypatch):
    """Kickoff should route from dispatch into dialectic work instead of stopping early."""

    class DummyScope:  # pylint: disable=too-few-public-methods
        """No-op hook scope used to keep the flow test deterministic."""

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        """Minimal CrewAI task output stub for dialectic validation."""

        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    class FakeCrew:  # pylint: disable=too-few-public-methods
        """Return a successful dialectic validation payload."""

        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="implementation complete"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw="synthesis"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.7,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(
        TaskExecutionFlow,
        "_run_independent_verifier",
        lambda self, checks=None: VerificationResult(
            verified=True,
            checks_passed=checks or self.state.acceptance_checks,
            notes="All checks passed.",
        ),
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-001",
            "task_title": "Define schema",
            "task_description": "Create the schema for vision metadata.",
            "acceptance_checks": ["schema file exists"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert result.success is True
    assert result.score == 8.7
    assert flow.state.phases_executed == ["dialectic", "verify"]
    assert flow.state.current_phase == "completed"


def test_task_execution_flow_high_confidence_reimplementation_still_runs_stack_gate(monkeypatch):
    class DummyScope:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    class FakeDialecticCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="implementation complete"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw="synthesis"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.1,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    class FakeReimplementationCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="fixed implementation"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=9.6,
                                consensus_reached=True,
                                final_validation_notes="Repair accepted.",
                            )
                        ),
                    ]
                },
            )()

    verification_calls = {"count": 0}

    def fake_verifier(self, checks=None):
        del self, checks
        verification_calls["count"] += 1
        return VerificationResult(
            verified=False,
            checks_failed=["imports broken"],
            notes="Initial verification failed.",
        )

    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeDialecticCrew())
    monkeypatch.setattr("execution.task_flow.build_task_flow_reimplementation_crew", lambda **kwargs: FakeReimplementationCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(TaskExecutionFlow, "_run_independent_verifier", fake_verifier)
    monkeypatch.setattr(
        "execution.task_flow.run_stack_validation_gate",
        lambda profile: VerificationResult(
            verified=False,
            checks_failed=["stack validation: mypy"],
            notes="stack validation failed: mypy",
        ),
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-009",
            "task_title": "Repair import graph",
            "task_description": "Fix module wiring.",
            "acceptance_checks": ["imports resolve"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert verification_calls["count"] == 1
    assert result.success is False
    assert flow.state.reimplement_score == 9.6
    assert flow.state.verification.checks_failed == ["stack validation: mypy"]
    assert "stack validation failed" in flow.state.verification.notes


def test_task_execution_flow_routes_to_reimplementation_when_verifier_raises(monkeypatch):
    class DummyScope:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    class FakeDialecticCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="implementation complete"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw="synthesis"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.2,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    class FailingVerificationCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            raise ValueError("structured verifier exploded")

    class FakeReimplementationCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="fixed implementation"),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.8,
                                consensus_reached=True,
                                final_validation_notes="Repair accepted.",
                            )
                        ),
                    ]
                },
            )()

    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeDialecticCrew())
    monkeypatch.setattr("execution.task_flow.build_task_flow_verification_crew", lambda **kwargs: FailingVerificationCrew())
    monkeypatch.setattr("execution.task_flow.build_task_flow_reimplementation_crew", lambda **kwargs: FakeReimplementationCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(
        "execution.task_flow.run_stack_validation_gate",
        lambda profile: VerificationResult(verified=True, checks_passed=["stack gate"], notes="ok"),
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-010",
            "task_title": "Recover verifier failure",
            "task_description": "Recover when verifier output is malformed.",
            "acceptance_checks": ["artifact exists"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert result.success is False
    assert flow.state.phases_executed == ["dialectic", "verify", "reimplement", "reverify"]
    assert "Local fallback verification executed." in flow.state.verification.notes


def test_materialize_generated_files_writes_repo_relative_artifacts(tmp_path):
    raw_output = """Files added:
- schemas/example.schema.json
- adapters/examples/invalid_example.json

Contents (complete file contents):

1) schemas/example.schema.json
{
  \"type\": \"object\"
}

2) adapters/examples/invalid_example.json
{
  \"id\": \"bad\"
  /* INVALID: missing comma-free comment should be stripped */
}

Notes and guidance for CI:
- ignored
"""

    written = _materialize_generated_files(raw_output, tmp_path)

    assert written == [
        str(tmp_path / "schemas/example.schema.json"),
        str(tmp_path / "adapters/examples/invalid_example.json"),
    ]
    assert (tmp_path / "schemas/example.schema.json").read_text(encoding="utf-8") == '{\n  "type": "object"\n}\n'
    assert "/* INVALID" not in (tmp_path / "adapters/examples/invalid_example.json").read_text(
        encoding="utf-8"
    )


def test_task_execution_flow_materializes_dialectic_files_before_verification(monkeypatch, tmp_path):
    class DummyScope:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeTaskOutput:  # pylint: disable=too-few-public-methods
        def __init__(self, *, raw: str = "", pydantic=None):
            self.raw = raw
            self.pydantic = pydantic

    raw_impl = """Files added:
- schemas/adapter_manifest.schema.json

Contents (complete file contents):

1) schemas/adapter_manifest.schema.json
{
  \"type\": \"object\"
}
"""

    class FakeCrew:  # pylint: disable=too-few-public-methods
        def kickoff(self):
            return type(
                "Result",
                (),
                {
                    "tasks_output": [
                        FakeTaskOutput(raw="draft implementation"),
                        FakeTaskOutput(raw="critique"),
                        FakeTaskOutput(raw=raw_impl),
                        FakeTaskOutput(
                            pydantic=ValidationOutput(
                                quality_score=8.5,
                                consensus_reached=True,
                                final_validation_notes="Looks good.",
                            )
                        ),
                    ]
                },
            )()

    def fake_verifier(self, checks=None):
        del self
        del checks
        target = Path.cwd() / "schemas/adapter_manifest.schema.json"
        return VerificationResult(
            verified=target.exists(),
            checks_passed=["schema file exists"] if target.exists() else [],
            checks_failed=[] if target.exists() else ["schema file exists"],
            notes="Verifier inspected repo files.",
        )

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("execution.task_flow.build_task_dialectic_crew", lambda **kwargs: FakeCrew())
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(TaskExecutionFlow, "_run_independent_verifier", fake_verifier)

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-011",
            "task_title": "Materialize schema",
            "task_description": "Create schema artifacts.",
            "acceptance_checks": ["schema file exists"],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert result.success is True
    assert (tmp_path / "schemas/adapter_manifest.schema.json").exists()


def test_extract_generated_files_ignores_non_path_numbered_sections():
    raw_output = """1) Overview
This is just a heading.

2) registry/examples/sample.json
{
  \"status\": \"active\"
}
"""

    assert _extract_generated_files(raw_output) == [
        ("registry/examples/sample.json", '{\n  "status": "active"\n}')
    ]


def test_extract_generated_files_supports_dashed_file_sections():
    raw_output = dedent(
        """\
        Files created
        - schemas/adapter_manifest.schema.json

        Below are the complete contents of each file.

        --- schemas/adapter_manifest.schema.json ---
        {
          \"type\": \"object\"
        }

        --- registry/examples/invalid_registry_item.json ---
        {
          \"status\": \"broken\"
        }

        Quick instructions for running the validation
        - ignored
        """
    )

    assert _extract_generated_files(raw_output) == [
        ("schemas/adapter_manifest.schema.json", '{\n  "type": "object"\n}'),
        ("registry/examples/invalid_registry_item.json", '{\n  "status": "broken"\n}'),
    ]


def test_extract_generated_files_normalizes_annotated_paths_and_prefers_dashed_sections():
    raw_output = dedent(
        """\
        1) examples/canonicalization-run-seed-42.md (revised with asserted hashes + clear commands)
        --- examples/canonicalization-run-seed-42.md ---
        Canonical content.

        2) examples/example-schema.json (new small schema for end-to-end reproducibility)
        --- examples/example-schema.json ---
        {
          "type": "object"
        }
        """
    )

    assert _extract_generated_files(raw_output) == [
        ("examples/canonicalization-run-seed-42.md", "Canonical content."),
        ("examples/example-schema.json", '{\n  "type": "object"\n}'),
    ]


def test_local_verification_fallback_validates_schema_task_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    _materialize_generated_files(
        dedent(
            """\
            --- schemas/adapter_manifest.schema.json ---
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["id", "version_semver", "capabilities", "contract_schema_url", "owner"],
                "additionalProperties": false,
                "properties": {
                    "id": {"type": "string"},
                    "version_semver": {"type": "string", "pattern": "^(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)$"},
                    "capabilities": {"type": "array", "minItems": 1, "items": {"type": "string"}, "uniqueItems": true},
                    "contract_schema_url": {"type": "string", "format": "uri", "pattern": "^https://"},
                    "owner": {
                        "type": "object",
                        "required": ["team_id", "primary_contact", "escalation_policy_url"],
                        "properties": {
                            "team_id": {"type": "string"},
                            "primary_contact": {"type": "string", "format": "email"},
                            "escalation_policy_url": {"type": "string", "format": "uri", "pattern": "^https://"}
                        }
                    },
                    "deprecation_date": {"type": "string", "format": "date-time"}
                }
            }

            --- schemas/registry_item.schema.json ---
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["id", "version_semver", "capabilities", "contract_schema_url", "owner", "created_at", "updated_at", "status"],
                "properties": {
                    "id": {"type": "string"},
                    "version_semver": {"type": "string", "pattern": "^(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)$"},
                    "capabilities": {"type": "array", "minItems": 1, "items": {"type": "string"}, "uniqueItems": true},
                    "contract_schema_url": {"type": "string", "format": "uri", "pattern": "^https://"},
                    "owner": {
                        "type": "object",
                        "required": ["team_id", "primary_contact", "escalation_policy_url"],
                        "properties": {
                            "team_id": {"type": "string"},
                            "primary_contact": {"type": "string", "format": "email"},
                            "escalation_policy_url": {"type": "string", "format": "uri", "pattern": "^https://"}
                        }
                    },
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "status": {"type": "string", "enum": ["active", "deprecated", "archived", "pending"]}
                }
            }

            --- adapters/examples/valid_adapter_manifest.json ---
            {"id": "a1", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}}

            --- adapters/examples/invalid_adapter_missing_owner.json ---
            {"id": "a2", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json"}

            --- registry/examples/valid_registry_item.json ---
            {"id": "r1", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-02T00:00:00Z", "status": "active"}

            --- registry/examples/invalid_registry_item_bad_semver.json ---
            {"id": "r2", "version_semver": "v1.2", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-02T00:00:00Z", "status": "active"}
            """
        ),
        tmp_path,
    )

    result = _run_local_verification_fallback(
        [
            "schemas/adapter_manifest.schema.json exists",
            "schemas/registry_item.schema.json exists",
            "Schemas validate example manifests in adapters/examples/* and registry/examples/*",
            "version_semver pattern enforcement is present",
            "contract_schema_url uses HTTPS",
            "ISO-8601 deprecation_date validation",
            "owner.sub-object includes required fields (team_id, primary_contact, escalation_policy_url)",
        ]
    )

    assert result is not None
    assert result.verified is True
    assert len(result.checks_passed) == 7


def test_task_execution_flow_skips_verifier_when_preverified_locally(monkeypatch, tmp_path):
    class DummyScope:  # pylint: disable=too-few-public-methods
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    verifier_calls = {"count": 0}

    def fail_if_called(self, checks=None):
        del self, checks
        verifier_calls["count"] += 1
        raise AssertionError("independent verifier should be skipped after deterministic preverification")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("execution.task_flow.HookScope", DummyScope)
    monkeypatch.setattr(TaskExecutionFlow, "_run_independent_verifier", fail_if_called)

    _materialize_generated_files(
        dedent(
            """\
            --- schemas/adapter_manifest.schema.json ---
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["id", "version_semver", "capabilities", "contract_schema_url", "owner"],
                "additionalProperties": false,
                "properties": {
                    "id": {"type": "string"},
                    "version_semver": {"type": "string", "pattern": "^(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)$"},
                    "capabilities": {"type": "array", "minItems": 1, "items": {"type": "string"}, "uniqueItems": true},
                    "contract_schema_url": {"type": "string", "format": "uri", "pattern": "^https://.+"},
                    "owner": {
                        "type": "object",
                        "required": ["team_id", "primary_contact", "escalation_policy_url"],
                        "properties": {
                            "team_id": {"type": "string"},
                            "primary_contact": {"type": "string", "format": "email"},
                            "escalation_policy_url": {"type": "string", "format": "uri", "pattern": "^https://.+"}
                        }
                    },
                    "deprecation_date": {"type": "string", "format": "date-time"}
                }
            }

            --- schemas/registry_item.schema.json ---
            {
                "$schema": "http://json-schema.org/draft-07/schema#",
                "type": "object",
                "required": ["id", "version_semver", "capabilities", "contract_schema_url", "owner", "created_at", "updated_at", "status"],
                "properties": {
                    "id": {"type": "string"},
                    "version_semver": {"type": "string", "pattern": "^(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)\\\\.(0|[1-9]\\\\d*)$"},
                    "capabilities": {"type": "array", "minItems": 1, "items": {"type": "string"}, "uniqueItems": true},
                    "contract_schema_url": {"type": "string", "format": "uri", "pattern": "^https://.+"},
                    "owner": {
                        "type": "object",
                        "required": ["team_id", "primary_contact", "escalation_policy_url"],
                        "properties": {
                            "team_id": {"type": "string"},
                            "primary_contact": {"type": "string", "format": "email"},
                            "escalation_policy_url": {"type": "string", "format": "uri", "pattern": "^https://.+"}
                        }
                    },
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"},
                    "status": {"type": "string", "enum": ["active", "deprecated", "archived", "pending"]}
                }
            }

            --- adapters/examples/valid_adapter_manifest.json ---
            {"id": "a1", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}}

            --- adapters/examples/invalid_adapter_missing_owner.json ---
            {"id": "a2", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json"}

            --- registry/examples/valid_registry_item.json ---
            {"id": "r1", "version_semver": "1.2.3", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-02T00:00:00Z", "status": "active"}

            --- registry/examples/invalid_registry_item_bad_semver.json ---
            {"id": "r2", "version_semver": "v1.2", "capabilities": ["read"], "contract_schema_url": "https://example.com/schema.json", "owner": {"team_id": "team", "primary_contact": "a@example.com", "escalation_policy_url": "https://example.com/escalate"}, "created_at": "2024-01-01T00:00:00Z", "updated_at": "2024-01-02T00:00:00Z", "status": "active"}
            """
        ),
        tmp_path,
    )

    flow = TaskExecutionFlow()
    result = flow.kickoff(
        inputs={
            "task_id": "T-012",
            "task_title": "Reuse validated artifacts",
            "task_description": "Skip redundant verification when artifacts already pass locally.",
            "acceptance_checks": [
                "schemas/adapter_manifest.schema.json exists",
                "schemas/registry_item.schema.json exists",
                "Schemas validate example manifests in adapters/examples/* and registry/examples/*",
                "version_semver pattern enforcement is present",
                "contract_schema_url uses HTTPS",
                "ISO-8601 deprecation_date validation",
                "owner.sub-object includes required fields (team_id, primary_contact, escalation_policy_url)",
            ],
            "min_score": 7.5,
        }
    )

    assert isinstance(result, TaskExecutionResult)
    assert result.success is True
    assert verifier_calls["count"] == 0
    assert flow.state.phases_executed == ["dialectic", "verify"]
    assert flow.state.dialectic_notes == "Skipped dialectic: existing artifacts already satisfy acceptance checks."
    assert flow.state.verification.verified is True