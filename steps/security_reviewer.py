"""
Security Reviewer Step - Pre-step for /cs:c command.

This step performs a lightweight security review by running the Bandit
security scanner on Python code in the project before close-out.

Requirements
------------

**Bandit Installation**:
    This step requires the ``bandit`` package to be installed::

        pip install bandit
        # or
        uv add bandit

    If bandit is not installed, the step completes with a warning and
    returns an empty findings list. This is intentional - the step
    follows the "fail-open" philosophy and does not block project
    close-out if the security scanner is unavailable.

Configuration Options
---------------------

The step accepts the following configuration options via lifecycle config:

.. code-block:: json

    {
        "name": "security-review",
        "enabled": true,
        "timeout": 120
    }

Options:
    - ``enabled`` (bool): Whether to run the step. Default: ``true``
    - ``timeout`` (int): Maximum execution time in seconds. Default: ``120``

The timeout applies to the bandit scan itself. Large codebases may need
a higher timeout value.

Security Checks Performed
-------------------------

Bandit scans Python files for common security issues including:

**Code Injection**:
    - Use of ``eval()``, ``exec()``, ``compile()``
    - Shell injection via ``subprocess`` with ``shell=True``
    - SQL injection patterns

**Cryptography**:
    - Weak cryptographic algorithms (MD5, SHA1 for security)
    - Hardcoded passwords and secrets
    - Use of insecure random number generators

**Network Security**:
    - Binding to all interfaces (0.0.0.0)
    - SSL/TLS verification disabled
    - Unvalidated redirects

**File System**:
    - Hardcoded temporary file paths
    - Use of ``os.chmod`` with permissive modes

**Deserialization**:
    - Pickle/marshal loading of untrusted data
    - YAML load without safe_load

Bandit Output
-------------

The step runs bandit with the following flags:
    - ``-r``: Recursive scan of project directory
    - ``-f json``: JSON output format for parsing
    - ``-ll``: Report LOW severity and above
    - ``-q``: Quiet mode (suppress progress)

Findings are formatted as::

    [SEVERITY/CONFIDENCE] filename:line - issue description

Example::

    [MEDIUM/HIGH] app/utils.py:42 - Use of shell=True in subprocess call

Output Behavior
---------------

- Findings are printed to stderr for immediate visibility
- First 10 findings are shown; additional count is noted
- Full findings list is available in result.data["findings"]
- If scan fails or is incomplete, warnings are added to result

Hook Integration
----------------

This step is typically configured as a pre-step for ``/cs:c``::

    {
        "commands": {
            "cs:c": {
                "preSteps": [
                    { "name": "security-review", "enabled": true, "timeout": 120 }
                ]
            }
        }
    }

The step runs before the close-out command executes, giving developers
a chance to address security issues before marking a project complete.
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from .base import BaseStep, StepResult


class SecurityReviewerStep(BaseStep):
    """Runs security review as pre-step for /cs:c.

    Executes bandit security scanner on the project's Python code and
    reports findings. Follows fail-open philosophy - will not block
    workflow if bandit is unavailable or scan fails.

    Attributes:
        name: Step identifier ("security-review").
        DEFAULT_TIMEOUT: Default scan timeout in seconds (120).
    """

    name = "security-review"

    # Default timeout in seconds
    DEFAULT_TIMEOUT = 120

    def execute(self) -> StepResult:
        """Run the security review step.

        Attempts to run bandit security scanner on the project. Handles
        various failure modes gracefully:
        - Bandit not installed: Returns success with warning
        - Scan timeout: Returns partial results with warning
        - Parse error: Returns success with warning

        Returns:
            StepResult with findings in data["findings"], findings_count,
            and scan_complete flag.
        """
        timeout = self.config.get("timeout", self.DEFAULT_TIMEOUT)

        # Try bandit security scanner
        findings, scan_complete = self._run_bandit(timeout)

        # Check if bandit is not available (empty findings and incomplete)
        if not findings and not scan_complete:
            # Could be either bandit not installed or scan error
            # Check if bandit is available to distinguish
            try:
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

    This function is the entry point called by the hook system when
    executing the security-review step.

    Args:
        cwd: Current working directory (project root)
        config: Optional step configuration from lifecycle config

    Returns:
        StepResult from step execution
    """
    step = SecurityReviewerStep(cwd, config)
    return step.run()
