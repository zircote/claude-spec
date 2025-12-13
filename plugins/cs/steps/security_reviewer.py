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

        # Try bandit security scanner
        findings, scan_complete = self._run_bandit(timeout)

        # Check if bandit is not available (empty findings and incomplete)
        if not findings and not scan_complete:
            # Could be either bandit not installed or scan error
            # Check if bandit is available to distinguish
            try:
                import subprocess

                subprocess.run(
                    ["bandit", "--version"], capture_output=True, timeout=5, check=True
                )
                # Bandit available but scan failed
                result = StepResult.ok(
                    "Security review incomplete (scan error)",
                    findings=[],
                    findings_count=0,
                    scan_complete=False,
                )
                result.add_warning("Bandit scan failed - results may be incomplete")
                return result
            except (
                subprocess.TimeoutExpired,
                FileNotFoundError,
                subprocess.CalledProcessError,
            ):
                # Bandit not available
                result = StepResult.ok(
                    "Security review skipped (bandit not installed)",
                    findings=[],
                    findings_count=0,
                    scan_complete=False,
                )
                result.add_warning(
                    "Install bandit for security scanning: pip install bandit"
                )
                return result

        # Build result message based on completion status
        if scan_complete:
            message = f"Security review complete: {len(findings)} findings"
        else:
            message = f"Security review incomplete: {len(findings)} findings (scan may have partial results)"

        result = StepResult.ok(
            message,
            findings=findings,
            findings_count=len(findings),
            scan_complete=scan_complete,
        )

        if not scan_complete:
            result.add_warning(
                "Scan did not complete fully - results may be incomplete"
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

    def _run_bandit(self, timeout: int) -> tuple[list[str], bool]:
        """Run bandit security scanner.

        Args:
            timeout: Command timeout in seconds

        Returns:
            Tuple of (findings list, scan_complete bool).
            Returns ([], False) if bandit unavailable or scan failed.
        """
        try:
            # Check if bandit is available
            subprocess.run(["bandit", "--version"], capture_output=True, timeout=5)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return ([], False)

        findings = []
        scan_complete = True

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
                except json.JSONDecodeError as e:
                    sys.stderr.write(
                        f"security_reviewer: Failed to parse bandit output: {e}\n"
                    )
                    scan_complete = False

        except subprocess.TimeoutExpired:
            sys.stderr.write(f"security_reviewer: Bandit timed out after {timeout}s\n")
            scan_complete = False
        except Exception as e:
            sys.stderr.write(f"security_reviewer: Bandit error: {e}\n")
            scan_complete = False

        return (findings, scan_complete)


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
