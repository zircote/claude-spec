"""
Base classes for the step execution system.

This module provides the foundational classes for the claude-spec plugin's
step-based execution system. Steps are modular, composable units of work
that can be configured to run before (pre-steps) or after (post-steps)
specific slash commands.

Architecture Overview
---------------------

The step system follows a simple pattern:

1. **Configuration**: Steps are configured in ``~/.claude/worktree-manager.config.json``
   under the ``lifecycle.commands`` section.

2. **Discovery**: The hook system (command_detector.py, post_command.py) reads
   step configurations using ``config_loader.get_enabled_steps()``.

3. **Execution**: Each step is instantiated with the current working directory
   and optional configuration, then executed via the ``run()`` method.

4. **Results**: Steps return ``StepResult`` objects indicating success/failure,
   with optional data and warnings.

Creating a New Step
-------------------

To create a new step, extend ``BaseStep`` and implement the ``execute()`` method:

.. code-block:: python

    from steps.base import BaseStep, StepResult

    class MyCustomStep(BaseStep):
        \"\"\"Description of what this step does.\"\"\"

        name = "my-custom-step"  # Must match the name in config

        def validate(self) -> bool:
            \"\"\"Optional: Check preconditions before execution.\"\"\"
            # Return False to skip execution with a validation failure
            return True

        def execute(self) -> StepResult:
            \"\"\"Perform the step's work.\"\"\"
            try:
                # Do work here...
                result_data = {"key": "value"}
                return StepResult.ok("Success message", **result_data)
            except SomeError as e:
                return StepResult.fail(f"Failed: {e}")


    # Required: Module-level run function for hook integration
    def run(cwd: str, config: dict | None = None) -> StepResult:
        \"\"\"Hook integration entry point.\"\"\"
        step = MyCustomStep(cwd, config)
        return step.run()

Step Configuration
------------------

Steps receive configuration from the lifecycle config:

.. code-block:: json

    {
        "name": "my-custom-step",
        "enabled": true,
        "timeout": 120,
        "custom_option": "value"
    }

Access configuration in your step via ``self.config``:

.. code-block:: python

    def execute(self) -> StepResult:
        timeout = self.config.get("timeout", 60)
        custom = self.config.get("custom_option", "default")
        # ...

Error Handling
--------------

The step system follows a "fail-open" philosophy:

- Steps should not block the main command workflow on failure
- Errors are captured and converted to ``StepResult.fail()`` with warnings
- Only ``StepError`` exceptions propagate up (for critical failures)
- Use ``result.add_warning()`` for non-fatal issues

Error Categorization (ARCH-009)
-------------------------------

StepResult includes error categorization for better error handling:

- ``error_code``: Categorized error code (e.g., "validation", "io", "timeout")
- ``retriable``: Whether the error is transient and the step can be retried

Hook Integration
----------------

Steps are integrated via hooks:

- **Pre-steps**: Run by ``command_detector.py`` when a /* command is detected
- **Post-steps**: Run by ``post_command.py`` when a session ends

The hooks look for a module-level ``run(cwd, config)`` function in each step module.

Available Steps
---------------

Pre-steps (run before command):
    - ``security_reviewer.py``: Run bandit security scanner

Post-steps (run after command):
    - ``retrospective_gen.py``: Generate RETROSPECTIVE.md
    - ``log_archiver.py``: Archive prompt logs to completed directory
    - ``marker_cleaner.py``: Clean up temporary marker files
    - ``context_loader.py``: Load project context for session start
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# =============================================================================
# Shared Constants (DRY fix for QUAL-001)
# =============================================================================

LOG_FILE = ".prompt-log.json"


# =============================================================================
# Shared Utility Functions (DRY fix for QUAL-001)
# =============================================================================


def safe_mtime(path: Path, context: str = "base") -> float:
    """Get modification time safely, returning 0 on errors.

    This utility is shared across steps that need to sort files/directories
    by modification time. It handles OSError gracefully for permissions,
    broken symlinks, etc.

    Args:
        path: Path to get modification time for.
        context: Caller context for error messages (e.g., "log_archiver").

    Returns:
        Modification time as float, or 0 on error.
    """
    import sys

    try:
        return path.stat().st_mtime
    except OSError as e:
        sys.stderr.write(f"{context}: Cannot stat {path}: {e}\n")
        return 0


def find_latest_completed_project(cwd: Path, context: str = "base") -> Path | None:
    """Find the most recently modified completed project directory.

    Looks in docs/spec/completed/ for project directories and returns
    the one with the most recent modification time.

    Args:
        cwd: Current working directory (project root).
        context: Caller context for error messages.

    Returns:
        Path to most recent project directory, or None if not found.
    """
    completed_dir = cwd / "docs" / "spec" / "completed"

    if not completed_dir.is_dir():
        return None

    project_dirs = [d for d in completed_dir.iterdir() if d.is_dir()]

    if not project_dirs:
        return None

    # Sort by modification time, most recent first
    project_dirs.sort(key=lambda d: safe_mtime(d, context), reverse=True)
    return project_dirs[0]


class ErrorCode(Enum):
    """Categorized error codes for step failures (ARCH-009).

    These codes help classify errors for better handling and reporting.
    """

    # No error
    NONE = "none"

    # Validation errors - preconditions not met
    VALIDATION = "validation"

    # I/O errors - file system, network, etc.
    IO = "io"

    # Timeout errors - operation took too long
    TIMEOUT = "timeout"

    # Configuration errors - invalid or missing config
    CONFIG = "config"

    # Dependency errors - required external tool/service unavailable
    DEPENDENCY = "dependency"

    # Permission errors - access denied
    PERMISSION = "permission"

    # Parse errors - invalid input format
    PARSE = "parse"

    # Unknown/unclassified errors
    UNKNOWN = "unknown"


@dataclass
class StepResult:
    """Result of a step execution.

    Attributes:
        success: Whether the step completed successfully.
        message: Human-readable description of the result.
        data: Optional dictionary of result data (findings, paths, counts, etc.).
        warnings: List of non-fatal warning messages.
        error_code: Categorized error code for failures (ARCH-009).
        retriable: Whether the error is transient and step can be retried (ARCH-009).

    Examples:
        Creating a successful result::

            result = StepResult.ok("Processed 5 files", file_count=5)

        Creating a failed result::

            result = StepResult.fail("File not found: config.json")

        Creating a retriable failure::

            result = StepResult.fail(
                "Network timeout",
                error_code=ErrorCode.TIMEOUT,
                retriable=True
            )

        Adding warnings::

            result = StepResult.ok("Done with issues")
            result.add_warning("Deprecated API used")
            result.add_warning("Missing optional config")
    """

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error_code: ErrorCode = ErrorCode.NONE
    retriable: bool = False

    @classmethod
    def ok(cls, message: str = "Success", **data: Any) -> "StepResult":
        """Create a successful result.

        Args:
            message: Description of what succeeded.
            **data: Arbitrary key-value pairs to include in result data.

        Returns:
            A StepResult with success=True.
        """
        return cls(success=True, message=message, data=data, error_code=ErrorCode.NONE)

    @classmethod
    def fail(
        cls,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN,
        retriable: bool = False,
        **data: Any,
    ) -> "StepResult":
        """Create a failed result.

        Args:
            message: Description of what failed.
            error_code: Categorized error code (ARCH-009).
            retriable: Whether the error is transient and step can be retried.
            **data: Arbitrary key-value pairs to include in result data.

        Returns:
            A StepResult with success=False.
        """
        return cls(
            success=False,
            message=message,
            data=data,
            error_code=error_code,
            retriable=retriable,
        )

    def add_warning(self, warning: str) -> "StepResult":
        """Add a warning to the result.

        Warnings are non-fatal issues that should be reported but don't
        constitute failure.

        Args:
            warning: Warning message to add.

        Returns:
            Self, for method chaining.
        """
        self.warnings.append(warning)
        return self

    def is_retriable(self) -> bool:
        """Check if this failure is retriable.

        Returns:
            True if the step failed and can be retried.
        """
        return not self.success and self.retriable


class StepError(Exception):
    """Exception raised when a step fails critically.

    Unlike normal failures (returned via StepResult.fail()), StepError
    indicates a critical failure that should propagate up and potentially
    halt the workflow.

    Use sparingly - most failures should be handled gracefully via
    StepResult.fail() to maintain the fail-open philosophy.

    Attributes:
        step_name: Name of the step that raised the error.
        error_code: Categorized error code (ARCH-009).
    """

    def __init__(
        self,
        message: str,
        step_name: str = "unknown",
        error_code: ErrorCode = ErrorCode.UNKNOWN,
    ):
        self.step_name = step_name
        self.error_code = error_code
        super().__init__(f"[{step_name}] {message}")


class BaseStep(ABC):
    """Base class for all steps.

    Provides the template for step implementation with validation,
    execution, and error handling.

    Attributes:
        name: Step identifier (must match config name). Override in subclass.
        cwd: Current working directory for the step.
        config: Configuration dictionary from lifecycle config.

    Subclasses must:
        - Set a unique ``name`` class attribute
        - Implement the ``execute()`` method
        - Optionally override ``validate()`` for precondition checks
    """

    name: str = "base"

    def __init__(self, cwd: str, config: dict[str, Any] | None = None):
        """Initialize the step.

        Args:
            cwd: Current working directory for the step.
            config: Optional configuration dictionary.
        """
        self.cwd = cwd
        self.config = config or {}

    @abstractmethod
    def execute(self) -> StepResult:
        """Execute the step. Must be implemented by subclasses.

        This method contains the main logic of the step. It should:
        - Perform the step's work
        - Return StepResult.ok() on success with relevant data
        - Return StepResult.fail() on recoverable failures
        - Raise StepError only for critical, unrecoverable failures

        Returns:
            StepResult indicating success or failure.
        """

    def validate(self) -> bool:
        """Validate preconditions. Override in subclasses if needed.

        Called before execute(). If validation fails, the step returns
        a failure result without executing.

        Common validations:
        - Check required files exist
        - Verify dependencies are available
        - Validate configuration values

        Returns:
            True if preconditions are met, False otherwise.
        """
        return True

    def run(self) -> StepResult:
        """Run the step with validation and error handling.

        This is the main entry point for step execution. It:
        1. Calls validate() to check preconditions
        2. Calls execute() if validation passes
        3. Catches exceptions and converts to StepResult

        The fail-open philosophy means most errors are caught and
        converted to failed results rather than raising exceptions.

        Returns:
            StepResult from validation failure, execution, or error handling.

        Raises:
            StepError: Only if the step raises StepError explicitly.
        """
        try:
            if not self.validate():
                return StepResult.fail(
                    f"Validation failed for {self.name}",
                    error_code=ErrorCode.VALIDATION,
                )
            return self.execute()
        except StepError:
            raise
        except TimeoutError as e:
            return StepResult.fail(
                str(e),
                error_code=ErrorCode.TIMEOUT,
                retriable=True,
            ).add_warning(f"Step {self.name} timed out")
        except PermissionError as e:
            return StepResult.fail(
                str(e),
                error_code=ErrorCode.PERMISSION,
                retriable=False,
            ).add_warning(f"Step {self.name} permission denied")
        except OSError as e:
            return StepResult.fail(
                str(e),
                error_code=ErrorCode.IO,
                retriable=True,
            ).add_warning(f"Step {self.name} I/O error")
        except Exception as e:
            # Fail-open: log error but don't block
            return StepResult.fail(
                str(e),
                error_code=ErrorCode.UNKNOWN,
                retriable=False,
            ).add_warning(f"Step {self.name} encountered error")
