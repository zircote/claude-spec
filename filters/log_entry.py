"""Log Entry Schema for claude-spec Prompt Capture Hook.

This module defines the data structures for prompt log entries stored in
NDJSON format. Each entry captures a user interaction during a /*
command session.

Entry Types
-----------

The ``entry_type`` field identifies the kind of content being logged:

- **user_input**: Direct user prompt text submitted to Claude. This is the
  raw text the user typed or pasted.

- **expanded_prompt**: Full slash command expansion. When a user invokes
  a command like ``/p "project idea"``, this captures the expanded
  prompt template with the user's input interpolated.

- **response_summary**: Summarized Claude response. Instead of storing full
  responses (which can be very large), this captures a summary or key
  excerpts for retrospective analysis.

Field Naming Convention
-----------------------

Note: There is a distinction between the Python attribute name and the
JSON serialization key:

- Python: ``entry_type`` (snake_case, follows Python conventions)
- JSON: ``type`` (shorter key for compact storage)

This mapping is handled by ``to_dict()`` and ``from_dict()`` methods.

Schema Structure
----------------

Each log entry contains:

.. code-block:: json

    {
        "timestamp": "2024-01-15T10:30:00.123456+00:00",
        "session_id": "abc123",
        "type": "user_input",
        "command": "/p",
        "content": "The filtered prompt content...",
        "filter_applied": {
            "secret_count": 2,
            "secret_types": ["aws_access_key", "github_pat"],
            "was_truncated": false
        },
        "metadata": {
            "content_length": 1234,
            "cwd": "/path/to/project"
        }
    }

Filter Information
------------------

The ``filter_applied`` field tracks what content filtering was applied:

- ``secret_count``: Number of secrets detected and redacted
- ``secret_types``: List of secret type identifiers (e.g., "aws_access_key")
- ``was_truncated``: Whether content exceeded MAX_CONTENT_LENGTH

See ``filters/pipeline.py`` for the full list of detected secret types.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class FilterInfo:
    """Information about content filtering applied to an entry.

    Attributes:
        secret_count: Number of secrets detected and replaced.
        secret_types: List of secret type identifiers found.
        was_truncated: Whether content was truncated due to length.
    """

    secret_count: int = 0
    secret_types: list[str] = field(default_factory=list)
    was_truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterInfo:
        """Create FilterInfo from dictionary."""
        return cls(
            secret_count=data.get("secret_count", 0),
            secret_types=data.get("secret_types", []),
            was_truncated=data.get("was_truncated", False),
        )


@dataclass
class EntryMetadata:
    """Metadata about the log entry context.

    Attributes:
        content_length: Length of the content after filtering.
        cwd: Current working directory when entry was created.
    """

    content_length: int = 0
    cwd: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EntryMetadata:
        """Create EntryMetadata from dictionary."""
        return cls(
            content_length=data.get("content_length", 0),
            cwd=data.get("cwd", ""),
        )


@dataclass
class LogEntry:
    """
    A single entry in the prompt capture log.

    Entry types:
        - ``user_input``: Direct user prompt text
        - ``expanded_prompt``: Full slash command expansion
        - ``response_summary``: Summarized Claude response

    Note:
        The ``entry_type`` attribute is serialized as ``type`` in JSON output
        for compact storage. Use ``to_dict()``/``from_dict()`` for conversion.

    Attributes:
        timestamp: ISO 8601 timestamp with timezone.
        session_id: Unique identifier for the Claude Code session.
        entry_type: One of: "user_input", "expanded_prompt", "response_summary".
        command: The /* command if applicable, or None.
        content: The actual content (already filtered for secrets).
        filter_applied: Information about filtering applied.
        metadata: Additional context metadata.
    """

    timestamp: str
    session_id: str
    entry_type: str  # user_input, expanded_prompt, response_summary
    command: str | None  # /p, /i, etc. or None
    content: str
    filter_applied: FilterInfo = field(default_factory=FilterInfo)
    metadata: EntryMetadata = field(default_factory=EntryMetadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Note: ``entry_type`` is serialized as ``type`` for compact JSON output.
        """
        return {
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "type": self.entry_type,
            "command": self.command,
            "content": self.content,
            "filter_applied": self.filter_applied.to_dict(),
            "metadata": self.metadata.to_dict(),
        }

    def to_json(self) -> str:
        """Convert to JSON string (single line for NDJSON)."""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LogEntry:
        """Create LogEntry from dictionary.

        Note: Expects ``type`` key in data, maps to ``entry_type`` attribute.
        """
        return cls(
            timestamp=data.get("timestamp", ""),
            session_id=data.get("session_id", ""),
            entry_type=data.get("type", "user_input"),
            command=data.get("command"),
            content=data.get("content", ""),
            filter_applied=FilterInfo.from_dict(data.get("filter_applied", {})),
            metadata=EntryMetadata.from_dict(data.get("metadata", {})),
        )

    @classmethod
    def from_json(cls, json_str: str) -> LogEntry:
        """Create LogEntry from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create(
        cls,
        session_id: str,
        entry_type: str,
        content: str,
        command: str | None = None,
        cwd: str = "",
        filter_info: FilterInfo | None = None,
    ) -> LogEntry:
        """
        Factory method to create a new log entry with current timestamp.

        Args:
            session_id: Unique session identifier
            entry_type: Type of entry (user_input, expanded_prompt, response_summary)
            content: The actual content (already filtered)
            command: Optional /* command if applicable
            cwd: Current working directory
            filter_info: Information about filtering applied

        Returns:
            New LogEntry instance
        """
        return cls(
            timestamp=datetime.now(UTC).isoformat(),
            session_id=session_id,
            entry_type=entry_type,
            command=command,
            content=content,
            filter_applied=filter_info or FilterInfo(),
            metadata=EntryMetadata(content_length=len(content), cwd=cwd),
        )
