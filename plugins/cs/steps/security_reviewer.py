"""
Security reviewer step - runs security audit before /cs:c.

This step performs a lightweight security review by running bandit
(if available) on Python code in the project.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from .base import BaseStep, StepResult


class SecurityReviewerStep(BaseStep):
    """Runs security review as pre-step for /cs:c."""

    name = "security-review"

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 120

    def execute(self) -> StepResult:
        """Run the security review step.

        Returns:
            StepResult with findings in data["findings"]
        """
        timeout = self.config.get("timeout", self.DEFAULT_TIMEOUT)
        findings: list[str] = []

        # Try bandit security scanner
        bandit_result = self._run_bandit(timeout)
        if bandit_result is not None:
            findings.extend(bandit_result)
        else:
            # Bandit not available - skip detailed scan
            return StepResult.ok(
                "Security review skipped (bandit not installed)",
                findings=[],
                findings_count=0,
            ).add_warning("Install bandit for security scanning: pip install bandit")

        result = StepResult.ok(
            f"Security review complete: {len(findings)} findings",
            findings=findings,
            findings_count=len(findings),
        )

        # Output findings to stderr for user visibility
        if findings:
            sys.stderr.write("\n=== Security Review Findings ===\n")
            for finding in findings[:10]:  # Limit output
                sys.stderr.write(f"  - {finding}\n")
            if len(findings) > 10:
                sys.stderr.write(f"  ... and {len(findings) - 10} more\n")
            sys.stderr.write("================================\n\n")

        return result

    def _run_bandit(self, timeout: int) -> list[str] | None:
        """Run bandit security scanner.

        Args:
            timeout: Command timeout in seconds

        Returns:
            List of findings, or None if bandit unavailable
        """
        try:
            # Check if bandit is available
            subprocess.run(["bandit", "--version"], capture_output=True, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None

        findings = []

        try:
            # Run bandit on Python files
            result = subprocess.run(
                [
                    "bandit",
                    "-r",
                    self.cwd,
                    "-f",
                    "json",
                    "-ll",  # Low and above severity
                    "-q",  # Quiet mode
                ],
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            if result.stdout:
                import json

                try:
                    report = json.loads(result.stdout)
                    for issue in report.get("results", []):
                        severity = issue.get("issue_severity", "UNKNOWN")
                        confidence = issue.get("issue_confidence", "UNKNOWN")
                        text = issue.get("issue_text", "Unknown issue")
                        filename = issue.get("filename", "unknown")
                        line = issue.get("line_number", 0)
                        findings.append(
                            f"[{severity}/{confidence}] {filename}:{line} - {text}"
                        )
                except json.JSONDecodeError:
                    pass

        except subprocess.TimeoutExpired:
            sys.stderr.write(f"security_reviewer: Bandit timed out after {timeout}s\n")
        except Exception as e:
            sys.stderr.write(f"security_reviewer: Bandit error: {e}\n")

        return findings


def run(cwd: str, config: dict[str, Any] | None = None) -> StepResult:
    """Module-level run function for hook integration.

    Args:
        cwd: Current working directory
        config: Optional step configuration

    Returns:
        StepResult from step execution
    """
    step = SecurityReviewerStep(cwd, config)
    return step.run()
