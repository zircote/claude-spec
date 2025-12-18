"""
Data models for tool learning capture.

These dataclasses define the domain objects for the PostToolUse learning system.
All models are immutable (frozen) to ensure thread-safety.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class LearningCategory(Enum):
    """
    Category of learning captured from tool execution.

    ERROR: Command/operation failed with an error
    WORKAROUND: User or system found a workaround for an issue
    DISCOVERY: New information or behavior discovered
    WARNING: Non-fatal warning that may be relevant
    """

    ERROR = "error"
    WORKAROUND = "workaround"
    DISCOVERY = "discovery"
    WARNING = "warning"


class LearningSeverity(Enum):
    """
    Severity of the learning event.

    SEV_0: Silent failure - dangerous, no obvious indication
    SEV_1: Hard failure - obvious error, operation completely failed
    SEV_2: Recoverable - operation partially succeeded or recovered
    SEV_3: Informational - minor issue or noteworthy behavior
    """

    SEV_0 = "sev-0"  # Silent failure - most dangerous
    SEV_1 = "sev-1"  # Hard failure
    SEV_2 = "sev-2"  # Recoverable
    SEV_3 = "sev-3"  # Informational


# Valid category values for validation
VALID_CATEGORIES = frozenset(c.value for c in LearningCategory)
VALID_SEVERITIES = frozenset(s.value for s in LearningSeverity)


@dataclass(frozen=True)
class ToolLearning:
    """
    Structured learning extracted from tool execution.

    Captures the essential information about a learnable moment detected
    during tool use, ready for conversion to a Memory object.

    Attributes:
        tool_name: Tool that produced this learning (Bash, Read, Write, etc.)
        category: Type of learning (error, workaround, discovery, warning)
        severity: Severity level (sev-0 to sev-3)
        summary: One-line auto-generated summary (max 100 chars)
        context: What was being attempted when this occurred
        observation: What actually happened (the learning itself)
        exit_code: For Bash tools, the exit code (None for other tools)
        output_excerpt: Truncated relevant output (max 1KB)
        timestamp: When this learning was detected
        tags: Additional categorization tags
        spec: Specification slug if in a spec context
    """

    tool_name: str
    category: str  # LearningCategory value
    severity: str  # LearningSeverity value
    summary: str
    context: str
    observation: str
    exit_code: int | None = None
    output_excerpt: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    tags: tuple[str, ...] = field(default_factory=tuple)
    spec: str | None = None

    def __post_init__(self) -> None:
        """Validate category and severity values."""
        if self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"Invalid category: {self.category}. "
                f"Must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
            )
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Invalid severity: {self.severity}. "
                f"Must be one of: {', '.join(sorted(VALID_SEVERITIES))}"
            )
        # Validate summary length
        if len(self.summary) > 100:
            # Frozen dataclass - can't modify, but we validate on creation
            # Caller should truncate before creating
            raise ValueError(f"Summary too long: {len(self.summary)} chars (max 100)")

    def to_memory_args(self) -> dict:
        """
        Convert to arguments for CaptureService.capture_learning().

        Returns:
            Dict of arguments suitable for capture_learning() method.
        """
        # Build insight content
        insight_parts = [
            f"**Tool**: {self.tool_name}",
            f"**Category**: {self.category}",
            f"**Severity**: {self.severity}",
            "",
            "## Context",
            self.context,
            "",
            "## Observation",
            self.observation,
        ]

        if self.exit_code is not None:
            insight_parts.insert(3, f"**Exit Code**: {self.exit_code}")

        if self.output_excerpt:
            insight_parts.extend(
                [
                    "",
                    "## Output Excerpt",
                    "```",
                    self.output_excerpt,
                    "```",
                ]
            )

        insight = "\n".join(insight_parts)

        # Build tags
        all_tags = list(self.tags)
        all_tags.extend([self.tool_name.lower(), self.category, self.severity])

        return {
            "spec": self.spec,
            "summary": self.summary,
            "insight": insight,
            "applicability": f"When using {self.tool_name} tool",
            "tags": all_tags,
        }


@dataclass(frozen=True)
class DetectionSignal:
    """
    A detected signal that contributes to the learning score.

    Used internally by LearningDetector to track what patterns matched
    and contribute to the final score.

    Attributes:
        pattern_name: Name of the pattern that matched
        weight: Contribution to the score (0.0-1.0)
        matched_text: The text that triggered this signal
        category_hint: Suggested category based on this signal
        severity_hint: Suggested severity based on this signal
    """

    pattern_name: str
    weight: float
    matched_text: str = ""
    category_hint: str = LearningCategory.ERROR.value
    severity_hint: str = LearningSeverity.SEV_2.value
