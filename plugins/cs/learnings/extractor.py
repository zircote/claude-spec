"""
Learning extractor for PostToolUse hook.

Extracts structured ToolLearning objects from tool responses when the
detection score meets the capture threshold.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# Add plugin root to path for sibling package imports
PLUGIN_ROOT = Path(__file__).parent.parent
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from filters.pipeline import filter_pipeline

from .deduplicator import SessionDeduplicator, get_session_deduplicator
from .detector import DetectionResult, LearningDetector
from .models import LearningCategory, ToolLearning

# Maximum length for output excerpt (1KB per spec)
MAX_OUTPUT_EXCERPT = 1024

# Path sanitization patterns
HOME_PATH_PATTERN = re.compile(r"/Users/[^/\s]+")
CREDENTIALS_PATTERN = re.compile(
    r"(\.env|credentials|secrets|\.aws|\.ssh)", re.IGNORECASE
)


def sanitize_paths(content: str) -> str:
    """
    Sanitize sensitive paths in content.

    Redacts home directory paths and credential-related paths.

    Args:
        content: Text that may contain sensitive paths

    Returns:
        Sanitized text with paths redacted
    """
    # Redact home directory
    content = HOME_PATH_PATTERN.sub("/Users/[USER]", content)
    # Mark credential paths
    content = CREDENTIALS_PATTERN.sub(r"[\1-REDACTED]", content)
    return content


def truncate_output(output: str, max_length: int = MAX_OUTPUT_EXCERPT) -> str:
    """
    Truncate output to max length, preserving useful context.

    Tries to preserve error messages and warnings by prioritizing
    stderr-like content when truncating.

    Args:
        output: Full output text
        max_length: Maximum length to keep

    Returns:
        Truncated output string
    """
    if len(output) <= max_length:
        return output

    # Try to find error/warning sections to preserve
    lines = output.split("\n")

    # Prioritize lines with error indicators
    priority_patterns = [
        r"error|Error|ERROR",
        r"warning|Warning|WARNING",
        r"failed|Failed|FAILED",
        r"exception|Exception|EXCEPTION",
        r"traceback|Traceback",
    ]

    priority_lines: list[str] = []
    other_lines: list[str] = []

    for line in lines:
        is_priority = any(re.search(p, line) for p in priority_patterns)
        if is_priority:
            priority_lines.append(line)
        else:
            other_lines.append(line)

    # Build output: priority lines first, then fill with others
    result_lines: list[str] = []
    current_length = 0

    for line in priority_lines:
        if current_length + len(line) + 1 <= max_length:
            result_lines.append(line)
            current_length += len(line) + 1

    for line in other_lines:
        if current_length + len(line) + 1 <= max_length:
            result_lines.append(line)
            current_length += len(line) + 1

    result = "\n".join(result_lines)

    # Add truncation notice if we actually truncated
    if len(result) < len(output):
        truncated_chars = len(output) - len(result)
        notice = f"\n...[TRUNCATED: {truncated_chars} chars]"
        # Make room for notice
        if len(result) + len(notice) > max_length:
            result = result[: max_length - len(notice)]
        result += notice

    return result


def generate_summary(
    tool_name: str,
    category: str,
    detection_result: DetectionResult,
    context: str = "",
) -> str:
    """
    Generate a concise summary (max 100 chars) for the learning.

    Args:
        tool_name: Name of the tool
        category: Learning category
        detection_result: Detection result with signals
        context: Optional context about what was being attempted

    Returns:
        Summary string (max 100 chars)
    """
    # Get the primary signal for context
    if detection_result.signals:
        primary = max(detection_result.signals, key=lambda s: s.weight)
        signal_text = primary.matched_text[:40] if primary.matched_text else ""
    else:
        signal_text = ""

    # Build summary based on category
    if category == LearningCategory.ERROR.value:
        if signal_text:
            summary = f"{tool_name} error: {signal_text}"
        else:
            summary = f"{tool_name} command failed"
    elif category == LearningCategory.WARNING.value:
        summary = (
            f"{tool_name} warning: {signal_text}"
            if signal_text
            else f"{tool_name} warning"
        )
    elif category == LearningCategory.WORKAROUND.value:
        summary = (
            f"{tool_name} workaround: {signal_text}"
            if signal_text
            else f"{tool_name} recovery"
        )
    elif category == LearningCategory.DISCOVERY.value:
        summary = (
            f"{tool_name} discovery: {signal_text}"
            if signal_text
            else f"{tool_name} observation"
        )
    else:
        summary = f"{tool_name}: {signal_text}" if signal_text else f"{tool_name} event"

    # Truncate to 100 chars
    if len(summary) > 100:
        summary = summary[:97] + "..."

    return summary


def extract_learning(
    tool_name: str,
    response: dict[str, Any],
    context: str = "",
    spec: str | None = None,
    detector: LearningDetector | None = None,
    deduplicator: SessionDeduplicator | None = None,
) -> ToolLearning | None:
    """
    Extract a structured learning from tool response.

    Runs detection, deduplication, and filtering to produce a
    ToolLearning object if the response is worth capturing.

    Args:
        tool_name: Name of the tool (Bash, Read, Write, etc.)
        response: Tool response dict
        context: Description of what was being attempted
        spec: Specification slug if in a spec context
        detector: LearningDetector instance (uses default if None)
        deduplicator: SessionDeduplicator instance (uses session-global if None)

    Returns:
        ToolLearning object if worth capturing, None otherwise
    """
    detector = detector or LearningDetector()
    deduplicator = deduplicator or get_session_deduplicator()

    # Step 1: Detect learnable signals
    detection = detector.detect(tool_name, response)

    if not detection.should_capture:
        return None

    # Step 2: Extract output text
    output_parts = []
    if response.get("stderr"):
        output_parts.append(str(response["stderr"]))
    if response.get("stdout"):
        output_parts.append(str(response["stdout"]))
    if response.get("output"):
        output_parts.append(str(response["output"]))
    if response.get("error"):
        output_parts.append(str(response["error"]))
    if response.get("content"):
        output_parts.append(str(response["content"]))

    raw_output = "\n".join(output_parts)

    # Step 3: Check for duplicates
    exit_code = response.get("exit_code")
    dedup_result = deduplicator.check_learning(
        tool_name=tool_name,
        exit_code=exit_code,
        output_excerpt=raw_output[:500],
    )

    if dedup_result.is_duplicate:
        return None

    # Step 4: Filter secrets from output
    filtered = filter_pipeline(raw_output)
    safe_output = filtered.filtered_text

    # Step 5: Sanitize paths
    safe_output = sanitize_paths(safe_output)

    # Step 6: Truncate to limit
    output_excerpt = truncate_output(safe_output)

    # Step 7: Generate summary
    summary = generate_summary(
        tool_name=tool_name,
        category=detection.primary_category,
        detection_result=detection,
        context=context,
    )

    # Step 8: Determine observation based on signals
    if detection.signals:
        signal_descriptions = [
            s.matched_text for s in detection.signals if s.matched_text
        ]
        observation = "Detected signals: " + "; ".join(signal_descriptions[:3])
    else:
        observation = "Unknown issue detected"

    # Step 9: Build tags
    tags = [tool_name.lower(), detection.primary_category]
    if filtered.secret_count > 0:
        tags.append("secrets-filtered")

    # Step 10: Create ToolLearning
    return ToolLearning(
        tool_name=tool_name,
        category=detection.primary_category,
        severity=detection.primary_severity,
        summary=summary,
        context=context or f"Executing {tool_name} command",
        observation=observation,
        exit_code=exit_code,
        output_excerpt=output_excerpt,
        tags=tuple(tags),
        spec=spec,
    )
