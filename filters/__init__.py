"""Prompt capture filters for claude-spec plugin.

This package provides content filtering for prompt logging, including
secret detection and content truncation.

Modules:
    pipeline: Filter orchestration and secret detection (filter_pipeline, FilterResult)
    log_entry: Data structures for log entries (LogEntry, FilterInfo, EntryMetadata)
    log_writer: Atomic NDJSON append operations (append_to_log, read_log)

Usage:
    from filters import filter_pipeline, FilterResult
    from filters import LogEntry, append_to_log

    result = filter_pipeline(user_input)
    if result.secret_count > 0:
        print(f"Filtered {result.secret_count} secrets")

Security Features:
    - Detects 20+ secret types (AWS, GitHub, Stripe, etc.)
    - Base64 decoding to catch encoded secrets
    - Path traversal and symlink attack prevention
    - Atomic file locking for concurrent writes
"""

from .log_entry import EntryMetadata, FilterInfo, LogEntry
from .log_writer import append_to_log, get_log_path, read_log
from .pipeline import FilterResult, filter_pipeline

__all__ = [
    "filter_pipeline",
    "FilterResult",
    "LogEntry",
    "FilterInfo",
    "EntryMetadata",
    "append_to_log",
    "read_log",
    "get_log_path",
]
