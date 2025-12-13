"""
Base classes for step execution.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class StepResult:
    """Result of a step execution."""

    success: bool
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls, message: str = "Success", **data: Any) -> "StepResult":
        """Create a successful result."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def fail(cls, message: str, **data: Any) -> "StepResult":
        """Create a failed result."""
        return cls(success=False, message=message, data=data)

    def add_warning(self, warning: str) -> "StepResult":
        """Add a warning to the result."""
        self.warnings.append(warning)
        return self


class StepError(Exception):
    """Exception raised when a step fails critically."""

    def __init__(self, message: str, step_name: str = "unknown"):
        self.step_name = step_name
        super().__init__(f"[{step_name}] {message}")


class BaseStep(ABC):
    """Base class for all steps."""

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
        """Execute the step. Must be implemented by subclasses."""
        pass

    def validate(self) -> bool:
        """Validate preconditions. Override in subclasses if needed."""
        return True

    def run(self) -> StepResult:
        """Run the step with validation and error handling."""
        try:
            if not self.validate():
                return StepResult.fail(f"Validation failed for {self.name}")
            return self.execute()
        except StepError:
            raise
        except Exception as e:
            # Fail-open: log error but don't block
            return StepResult.fail(str(e)).add_warning(
                f"Step {self.name} encountered error"
            )
