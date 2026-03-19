"""Data models for self-improve quality-gate execution."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""

    tool: str
    passed: bool
    error_count: int = 0
    warning_count: int = 0
    output: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class QualityGateResult:
    """Aggregated result of all quality checks."""

    passed: bool
    checks: list[QualityCheckResult] = field(default_factory=list)
    summary: str = ""
    remediation_attempted: bool = False
    remediation_attempt_count: int = 0
    remediation_succeeded: bool = False
    remediation_steps: list[str] = field(default_factory=list)
    remediation_failure_reason: str = ""
    remediation_exhausted: bool = False

    def add_check(self, check: QualityCheckResult) -> None:
        """Record a check result and update aggregate pass/fail state."""
        self.checks.append(check)
        if not check.passed:
            self.passed = False

    def build_summary(self) -> str:
        """Build and cache a single-line human-readable summary."""
        lines = []
        for check in self.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"{check.tool}: {status} ({check.error_count} errors)")
        self.summary = "; ".join(lines)
        return self.summary


@dataclass(frozen=True)
class RemediationAction:
    """A deterministic remediation command for Python validation failures."""

    label: str
    command: list[str]
    reason: str
