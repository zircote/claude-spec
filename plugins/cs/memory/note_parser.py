"""
Note parser for cs-memory.

Handles parsing and formatting of Git note content with YAML front matter.
Notes follow the format:

```
---
type: decision
spec: user-auth
timestamp: 2025-12-14T10:30:00Z
summary: One-line summary
tags: [jwt, security]
---

## Context
Full markdown content here...
```
"""

import re
from datetime import datetime
from typing import Any

import yaml

from .config import MAX_SUMMARY_LENGTH, NOTE_OPTIONAL_FIELDS, NOTE_REQUIRED_FIELDS
from .exceptions import ParseError

# Regex to extract YAML front matter
FRONT_MATTER_PATTERN = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL | re.MULTILINE
)


def parse_note(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse a note into metadata and body.

    Args:
        content: Raw note content with YAML front matter

    Returns:
        Tuple of (metadata dict, body markdown string)

    Raises:
        ParseError: If front matter is missing, invalid, or missing required fields
    """
    if not content.strip():
        raise ParseError(
            "Note content is empty", "Provide note content with YAML front matter"
        )

    match = FRONT_MATTER_PATTERN.match(content)
    if not match:
        raise ParseError(
            "Note missing YAML front matter",
            "Note must start with --- followed by YAML metadata and closing ---",
        )

    yaml_content = match.group(1)
    body = content[match.end() :].strip()

    try:
        metadata = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        raise ParseError(
            f"Invalid YAML in front matter: {e}",
            "Check YAML syntax - ensure proper indentation and quoting",
        ) from e

    if not isinstance(metadata, dict):
        raise ParseError(
            "Front matter must be a YAML mapping",
            "Use key: value format in front matter",
        )

    # Validate required fields
    missing = NOTE_REQUIRED_FIELDS - set(metadata.keys())
    if missing:
        raise ParseError(
            f"Note missing required fields: {', '.join(sorted(missing))}",
            f"Add these fields to front matter: {', '.join(sorted(missing))}",
        )

    # Parse timestamp if string
    if isinstance(metadata.get("timestamp"), str):
        try:
            metadata["timestamp"] = datetime.fromisoformat(
                metadata["timestamp"].replace("Z", "+00:00")
            )
        except ValueError as e:
            raise ParseError(
                f"Invalid timestamp format: {e}",
                "Use ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ",
            ) from e

    # Normalize tags to list
    if "tags" in metadata:
        if isinstance(metadata["tags"], str):
            metadata["tags"] = [t.strip() for t in metadata["tags"].split(",")]
        elif not isinstance(metadata["tags"], list):
            metadata["tags"] = [str(metadata["tags"])]

    # Normalize relates_to to list
    if "relates_to" in metadata:
        if isinstance(metadata["relates_to"], str):
            metadata["relates_to"] = [metadata["relates_to"]]
        elif not isinstance(metadata["relates_to"], list):
            metadata["relates_to"] = [str(metadata["relates_to"])]

    return metadata, body


def format_note(
    metadata: dict[str, Any],
    body: str,
) -> str:
    """
    Format metadata and body into note content.

    Args:
        metadata: Dictionary of front matter fields
        body: Markdown body content

    Returns:
        Formatted note string with YAML front matter

    Raises:
        ParseError: If metadata is missing required fields
    """
    # Validate required fields
    missing = NOTE_REQUIRED_FIELDS - set(metadata.keys())
    if missing:
        raise ParseError(
            f"Cannot format note: missing required fields: {', '.join(sorted(missing))}",
            f"Provide values for: {', '.join(sorted(missing))}",
        )

    # Validate summary length
    summary = metadata.get("summary", "")
    if len(summary) > MAX_SUMMARY_LENGTH:
        raise ParseError(
            f"Summary exceeds maximum length ({len(summary)} > {MAX_SUMMARY_LENGTH})",
            f"Shorten summary to {MAX_SUMMARY_LENGTH} characters or less",
        )

    # Prepare metadata for YAML serialization
    yaml_metadata = {}
    for key, value in metadata.items():
        if key in NOTE_REQUIRED_FIELDS or key in NOTE_OPTIONAL_FIELDS:
            if isinstance(value, datetime):
                yaml_metadata[key] = value.isoformat().replace("+00:00", "Z")
            else:
                yaml_metadata[key] = value

    # Format with YAML front matter
    yaml_str = yaml.dump(
        yaml_metadata,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
    ).strip()

    return f"---\n{yaml_str}\n---\n\n{body}"


def validate_note(content: str) -> list[str]:
    """
    Validate note content and return list of warnings.

    Args:
        content: Raw note content

    Returns:
        List of warning messages (empty if fully valid)

    Note:
        This does not raise exceptions - use parse_note() for strict validation.
    """
    warnings = []

    try:
        metadata, body = parse_note(content)
    except ParseError as e:
        return [str(e)]

    # Check optional fields
    if not metadata.get("tags"):
        warnings.append("Consider adding tags for better searchability")

    if not body.strip():
        warnings.append("Note body is empty - consider adding context")

    # Check summary quality
    summary = metadata.get("summary", "")
    if len(summary) < 10:
        warnings.append("Summary is very short - consider being more descriptive")

    return warnings


def extract_memory_id(namespace: str, commit_sha: str) -> str:
    """
    Generate a memory ID from namespace and commit SHA.

    Format: <namespace>:<commit_sha>

    Args:
        namespace: Memory namespace (e.g., "decisions")
        commit_sha: Git commit SHA

    Returns:
        Memory ID string
    """
    return f"{namespace}:{commit_sha}"


def parse_memory_id(memory_id: str) -> tuple[str, str]:
    """
    Parse a memory ID into namespace and commit SHA.

    Args:
        memory_id: Memory ID in format <namespace>:<commit_sha>

    Returns:
        Tuple of (namespace, commit_sha)

    Raises:
        ParseError: If memory ID format is invalid
    """
    if ":" not in memory_id:
        raise ParseError(
            f"Invalid memory ID format: {memory_id}",
            "Memory ID must be in format namespace:commit_sha",
        )

    parts = memory_id.split(":", 1)
    return parts[0], parts[1]
