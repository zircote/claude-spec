"""
Learning detector for PostToolUse hook.

Detects learnable moments from tool execution using pattern matching
and heuristics. Returns a score (0.0-1.0) indicating the likelihood
that the tool output contains something worth capturing.
"""

import re
from dataclasses import dataclass, field
from typing import Any

from .models import (
    DetectionSignal,
    LearningCategory,
    LearningSeverity,
)

# Default capture threshold - only capture if score >= this value
DEFAULT_THRESHOLD = 0.6


@dataclass
class SignalPattern:
    """Pattern for detecting learnable signals in tool output."""

    name: str
    pattern: re.Pattern[str]
    weight: float
    category: LearningCategory
    severity: LearningSeverity
    description: str = ""


# Pre-compiled patterns for signal detection
# Organized by category for maintainability
ERROR_PATTERNS: list[SignalPattern] = [
    SignalPattern(
        name="exit_nonzero",
        pattern=re.compile(r"^exit code: [1-9]", re.IGNORECASE | re.MULTILINE),
        weight=0.4,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Non-zero exit code indicates command failure",
    ),
    SignalPattern(
        name="error_keyword",
        pattern=re.compile(
            r"\b(error|failed|failure|fatal|cannot|unable|denied|refused|"
            r"no such|not found|invalid|exception|traceback)\b",
            re.IGNORECASE,
        ),
        weight=0.3,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Error-related keywords in output",
    ),
    SignalPattern(
        name="command_not_found",
        pattern=re.compile(r"command not found|not recognized as", re.IGNORECASE),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Command or program not found",
    ),
    SignalPattern(
        name="permission_error",
        pattern=re.compile(
            r"permission denied|access denied|unauthorized|forbidden|EACCES",
            re.IGNORECASE,
        ),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Permission or access error",
    ),
    SignalPattern(
        name="file_not_found",
        pattern=re.compile(
            r"(file|directory|path) (not found|does not exist)|ENOENT|no such file",
            re.IGNORECASE,
        ),
        weight=0.4,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="File or path not found",
    ),
    SignalPattern(
        name="syntax_error",
        pattern=re.compile(
            r"syntax error|unexpected token|parse error|SyntaxError",
            re.IGNORECASE,
        ),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Syntax or parsing error",
    ),
    SignalPattern(
        name="type_error",
        pattern=re.compile(
            r"TypeError|AttributeError|NameError|KeyError|IndexError",
            re.IGNORECASE,
        ),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Runtime type or attribute error",
    ),
    SignalPattern(
        name="import_error",
        pattern=re.compile(
            r"ImportError|ModuleNotFoundError|cannot find module|no module named",
            re.IGNORECASE,
        ),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Module import failure",
    ),
    SignalPattern(
        name="connection_error",
        pattern=re.compile(
            r"connection (refused|reset|timed out)|ECONNREFUSED|ETIMEDOUT|"
            r"network (error|unreachable)",
            re.IGNORECASE,
        ),
        weight=0.5,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_1,
        description="Network or connection error",
    ),
    SignalPattern(
        name="timeout",
        pattern=re.compile(r"\btimeout\b|timed out|deadline exceeded", re.IGNORECASE),
        weight=0.4,
        category=LearningCategory.ERROR,
        severity=LearningSeverity.SEV_2,
        description="Operation timeout",
    ),
]

WARNING_PATTERNS: list[SignalPattern] = [
    SignalPattern(
        name="warning_keyword",
        pattern=re.compile(
            r"\b(warning|warn|deprecated|deprecation|caution)\b",
            re.IGNORECASE,
        ),
        weight=0.25,
        category=LearningCategory.WARNING,
        severity=LearningSeverity.SEV_3,
        description="Warning messages in output",
    ),
    SignalPattern(
        name="experimental_feature",
        pattern=re.compile(
            r"experimental|unstable|beta|preview|not recommended",
            re.IGNORECASE,
        ),
        weight=0.2,
        category=LearningCategory.WARNING,
        severity=LearningSeverity.SEV_3,
        description="Experimental or unstable feature usage",
    ),
]

DISCOVERY_PATTERNS: list[SignalPattern] = [
    SignalPattern(
        name="version_info",
        pattern=re.compile(
            r"version\s*[:\s]\s*v?[\d.]+|"
            r"(Python|Node|npm|pip|go|rust|cargo|ruby)\s+[\d.]+",
            re.IGNORECASE,
        ),
        weight=0.15,
        category=LearningCategory.DISCOVERY,
        severity=LearningSeverity.SEV_3,
        description="Version information discovered",
    ),
    SignalPattern(
        name="config_loaded",
        pattern=re.compile(
            r"(config|configuration|settings) (loaded|found|using)|"
            r"using (default|config)",
            re.IGNORECASE,
        ),
        weight=0.15,
        category=LearningCategory.DISCOVERY,
        severity=LearningSeverity.SEV_3,
        description="Configuration information",
    ),
]

WORKAROUND_PATTERNS: list[SignalPattern] = [
    SignalPattern(
        name="retry_success",
        pattern=re.compile(
            r"retry|retrying|retried|attempt \d|trying again",
            re.IGNORECASE,
        ),
        weight=0.3,
        category=LearningCategory.WORKAROUND,
        severity=LearningSeverity.SEV_2,
        description="Retry behavior indicating workaround",
    ),
    SignalPattern(
        name="fallback",
        pattern=re.compile(
            r"fallback|falling back|using alternative|defaulting to",
            re.IGNORECASE,
        ),
        weight=0.35,
        category=LearningCategory.WORKAROUND,
        severity=LearningSeverity.SEV_2,
        description="Fallback behavior",
    ),
]

# Noise patterns - these REDUCE the score (common non-learnable output)
NOISE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^(ok|OK|done|Done|success|Success|passed|Passed)$", re.MULTILINE),
    re.compile(r"^\s*$", re.MULTILINE),  # Empty lines
    re.compile(r"^#+ ", re.MULTILINE),  # Markdown headers (docs output)
    re.compile(r"^\d+ tests passed", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Build complete|build succeeded", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^Successfully installed", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^\[INFO\]", re.MULTILINE),  # Maven/log info
]

# Combine all signal patterns
ALL_SIGNAL_PATTERNS = (
    ERROR_PATTERNS + WARNING_PATTERNS + DISCOVERY_PATTERNS + WORKAROUND_PATTERNS
)


@dataclass
class DetectionResult:
    """Result of learning detection."""

    score: float
    signals: list[DetectionSignal] = field(default_factory=list)
    primary_category: str = LearningCategory.ERROR.value
    primary_severity: str = LearningSeverity.SEV_2.value
    noise_factor: float = 0.0

    @property
    def should_capture(self) -> bool:
        """Check if score meets capture threshold."""
        return self.score >= DEFAULT_THRESHOLD


class LearningDetector:
    """
    Detect learnable moments from tool execution.

    Uses pattern matching and heuristics to calculate a score (0.0-1.0)
    indicating the likelihood that tool output contains something worth
    capturing as a learning.
    """

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        """
        Initialize the detector.

        Args:
            threshold: Minimum score to consider worth capturing
        """
        self.threshold = threshold
        self._signal_patterns = ALL_SIGNAL_PATTERNS
        self._noise_patterns = NOISE_PATTERNS

    def calculate_score(
        self,
        tool_name: str,
        response: dict[str, Any],
    ) -> float:
        """
        Calculate capture score for tool response.

        Args:
            tool_name: Name of the tool (Bash, Read, Write, etc.)
            response: Tool response dict with stdout, stderr, exit_code, etc.

        Returns:
            Float between 0.0 and 1.0 indicating capture worthiness
        """
        result = self.detect(tool_name, response)
        return result.score

    def detect(
        self,
        tool_name: str,
        response: dict[str, Any],
    ) -> DetectionResult:
        """
        Full detection with signals and category information.

        Args:
            tool_name: Name of the tool
            response: Tool response dictionary

        Returns:
            DetectionResult with score, signals, and categories
        """
        signals: list[DetectionSignal] = []

        # Extract text content to analyze
        text = self._extract_text(response)

        # Check for exit code (Bash-specific, very strong signal)
        exit_code = response.get("exit_code")
        if exit_code is not None and exit_code != 0:
            signals.append(
                DetectionSignal(
                    pattern_name="exit_code_nonzero",
                    weight=0.5,  # Always 0.5 when exit_code != 0 (condition above)
                    matched_text=f"exit_code={exit_code}",
                    category_hint=LearningCategory.ERROR.value,
                    severity_hint=(
                        LearningSeverity.SEV_0.value
                        if not text.strip()
                        else LearningSeverity.SEV_1.value
                    ),
                )
            )

        # Run signal patterns
        for pattern in self._signal_patterns:
            match = pattern.pattern.search(text)
            if match:
                signals.append(
                    DetectionSignal(
                        pattern_name=pattern.name,
                        weight=pattern.weight,
                        matched_text=match.group(0)[:100],  # Limit matched text
                        category_hint=pattern.category.value,
                        severity_hint=pattern.severity.value,
                    )
                )

        # Calculate base score from signals
        if not signals:
            return DetectionResult(score=0.0, signals=[])

        # Sum weights but cap at 1.0
        base_score = min(1.0, sum(s.weight for s in signals))

        # Apply noise reduction
        noise_factor = self._calculate_noise(text)
        final_score = max(0.0, base_score - noise_factor)

        # Determine primary category/severity from highest-weight signal
        primary_signal = max(signals, key=lambda s: s.weight)

        return DetectionResult(
            score=final_score,
            signals=signals,
            primary_category=primary_signal.category_hint,
            primary_severity=primary_signal.severity_hint,
            noise_factor=noise_factor,
        )

    def _extract_text(self, response: dict[str, Any]) -> str:
        """Extract analyzable text from tool response."""
        parts = []

        # Different tools have different response formats
        if "stderr" in response and response["stderr"]:
            parts.append(str(response["stderr"]))
        if "stdout" in response and response["stdout"]:
            parts.append(str(response["stdout"]))
        if "content" in response and response["content"]:
            parts.append(str(response["content"]))
        if "output" in response and response["output"]:
            parts.append(str(response["output"]))
        if "result" in response and response["result"]:
            parts.append(str(response["result"]))
        # Handle error field
        if "error" in response and response["error"]:
            parts.append(str(response["error"]))

        return "\n".join(parts)

    def _calculate_noise(self, text: str) -> float:
        """
        Calculate noise reduction factor.

        Returns a value to subtract from the score based on
        how much of the output is routine/noisy.
        """
        if not text:
            return 0.0

        noise_matches = 0
        for pattern in self._noise_patterns:
            noise_matches += len(pattern.findall(text))

        # More noise matches = higher reduction (up to 0.3)
        return min(0.3, noise_matches * 0.05)
