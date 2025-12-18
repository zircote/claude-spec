"""
File-based queue for cross-process persistence.

This module provides atomic file-based queue operations to persist
learning data across Python process boundaries (hook invocations).

The queue is stored as a JSON file in the project directory,
allowing PostToolUse hooks to enqueue items and the Stop hook
to flush them to git notes.

Thread/process safety:
- Uses fcntl.flock for file locking
- Atomic writes via temp file + rename
- Graceful handling of stale/corrupt files

Queue file location: .cs-learning-queue.json in project root
"""

from __future__ import annotations

import fcntl
import json
import os
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Queue file name in project root
QUEUE_FILE = ".cs-learning-queue.json"

# Maximum age of queue file before considering it stale (24 hours)
MAX_QUEUE_AGE_SECONDS = 24 * 60 * 60

# Maximum items to keep in queue (prevent unbounded growth)
MAX_QUEUE_SIZE = 100

LOG_PREFIX = "file_queue"


def _get_queue_path(cwd: str) -> Path:
    """Get the queue file path for a project."""
    return Path(cwd) / QUEUE_FILE


def _is_queue_stale(queue_data: dict[str, Any]) -> bool:
    """Check if queue data is stale (from old session)."""
    created = queue_data.get("created")
    if not created:
        return True

    try:
        created_dt = datetime.fromisoformat(created)
        age = (datetime.now(UTC) - created_dt).total_seconds()
        return age > MAX_QUEUE_AGE_SECONDS
    except (ValueError, TypeError):
        return True


def _read_queue(queue_path: Path) -> dict[str, Any]:
    """Read queue file with locking.

    Returns:
        Queue data dict or empty queue structure
    """
    if not queue_path.is_file():
        return {"created": datetime.now(UTC).isoformat(), "items": []}

    try:
        with open(queue_path, encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                data = json.load(f)
                # Check for stale queue
                if _is_queue_stale(data):
                    return {"created": datetime.now(UTC).isoformat(), "items": []}
                return data
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error reading queue: {e}\n")
        return {"created": datetime.now(UTC).isoformat(), "items": []}


def _write_queue(queue_path: Path, data: dict[str, Any]) -> bool:
    """Write queue file atomically with locking.

    Args:
        queue_path: Path to queue file
        data: Queue data to write

    Returns:
        True if successful
    """
    try:
        # Write to temp file first
        dir_path = queue_path.parent
        fd, temp_path = tempfile.mkstemp(
            prefix=".cs-queue-", suffix=".tmp", dir=str(dir_path)
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                try:
                    json.dump(data, f, indent=2, default=str)
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)

            # Atomic rename
            os.rename(temp_path, queue_path)
            return True

        except Exception:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise

    except OSError as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error writing queue: {e}\n")
        return False


def enqueue_learning(
    cwd: str,
    tool_name: str,
    summary: str,
    content: str,
    category: str,
    severity: str,
    spec: str | None = None,
    tags: list[str] | None = None,
) -> bool:
    """Add a learning to the queue.

    Args:
        cwd: Project root directory
        tool_name: Tool that generated the learning
        summary: One-line summary
        content: Full content with insight
        category: Learning category (error, warning, workaround, etc.)
        severity: Severity level (critical, high, medium, low)
        spec: Specification slug (optional)
        tags: Categorization tags (optional)

    Returns:
        True if successfully queued
    """
    queue_path = _get_queue_path(cwd)
    queue_data = _read_queue(queue_path)

    # Create learning item
    item = {
        "id": f"{int(time.time() * 1000)}",
        "timestamp": datetime.now(UTC).isoformat(),
        "tool_name": tool_name,
        "summary": summary,
        "content": content,
        "category": category,
        "severity": severity,
        "spec": spec,
        "tags": tags or [],
    }

    # Add to queue, respecting max size
    items = queue_data.get("items", [])
    items.append(item)

    # Trim if over max size (keep newest)
    if len(items) > MAX_QUEUE_SIZE:
        items = items[-MAX_QUEUE_SIZE:]

    queue_data["items"] = items
    queue_data["updated"] = datetime.now(UTC).isoformat()

    return _write_queue(queue_path, queue_data)


def dequeue_all(cwd: str) -> list[dict[str, Any]]:
    """Read and clear all items from the queue.

    Args:
        cwd: Project root directory

    Returns:
        List of queued learning items
    """
    queue_path = _get_queue_path(cwd)
    queue_data = _read_queue(queue_path)

    items = queue_data.get("items", [])

    # Delete the queue file after reading (cleanup)
    if items:
        try:
            if queue_path.is_file():
                queue_path.unlink()
        except OSError as e:
            sys.stderr.write(f"{LOG_PREFIX}: Error deleting queue file: {e}\n")

    return items


def get_queue_size(cwd: str) -> int:
    """Get the number of items in the queue.

    Args:
        cwd: Project root directory

    Returns:
        Number of queued items
    """
    queue_path = _get_queue_path(cwd)
    queue_data = _read_queue(queue_path)
    return len(queue_data.get("items", []))


def clear_queue(cwd: str) -> bool:
    """Clear the queue without reading items.

    Args:
        cwd: Project root directory

    Returns:
        True if successful
    """
    queue_path = _get_queue_path(cwd)

    try:
        if queue_path.is_file():
            queue_path.unlink()
        return True
    except OSError as e:
        sys.stderr.write(f"{LOG_PREFIX}: Error clearing queue: {e}\n")
        return False
