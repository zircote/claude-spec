"""Log Writer Module for claude-spec Prompt Capture Hook.

This module provides atomic NDJSON append operations for the prompt capture log.
It handles concurrent writes safely using file locking and includes comprehensive
security measures against path traversal and symlink attacks.

NDJSON Format Specification
---------------------------

The log file uses Newline Delimited JSON (NDJSON) format:

- Each line is a complete, valid JSON object
- Lines are separated by newline characters (``\\n``)
- No array wrapper or commas between entries
- Each line can be parsed independently

Example file content::

    {"timestamp":"2024-01-15T10:30:00Z","session_id":"abc","type":"user_input",...}
    {"timestamp":"2024-01-15T10:30:05Z","session_id":"abc","type":"user_input",...}
    {"timestamp":"2024-01-15T10:30:10Z","session_id":"abc","type":"user_input",...}

Benefits of NDJSON:
    - Append-only writes (no read-modify-write cycle)
    - Streaming read support (process line by line)
    - Partial file corruption only affects individual lines
    - Simple recovery from corrupted entries

Concurrency Model
-----------------

This module handles concurrent writes from multiple Claude Code sessions
or parallel hook invocations using POSIX advisory file locking:

1. **Exclusive Lock Acquisition**: Before writing, ``fcntl.flock()`` acquires
   an exclusive lock (``LOCK_EX``) on the file descriptor.

2. **Atomic Append**: The write operation appends a single JSON line followed
   by a newline character.

3. **Sync to Disk**: ``fsync()`` ensures data is written to persistent storage
   before the lock is released.

4. **Lock Release**: The lock is released in a ``finally`` block to ensure
   cleanup even on errors.

Lock Behavior:
    - Blocking: If another process holds the lock, we wait (no timeout)
    - File-level: Locks the entire file, not individual records
    - Advisory: Cooperating processes must use the same locking mechanism

File Locking Details
--------------------

The locking implementation uses ``fcntl.flock()`` for POSIX compatibility:

.. code-block:: python

    fcntl.flock(fd, fcntl.LOCK_EX)  # Acquire exclusive lock (blocking)
    try:
        # Write operation
        f.write(entry.to_json() + "\\n")
        f.flush()
        os.fsync(f.fileno())
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)  # Release lock

Considerations:
    - Works on macOS and Linux
    - NFS may have limitations with advisory locks
    - Lock is released automatically if process terminates

Security Features
-----------------

**Path Traversal Protection**:
    All paths are canonicalized using ``Path.resolve()`` and validated to ensure
    the target file remains within the expected project directory. This prevents
    attacks using ``../`` sequences to write outside the project.

**Symlink Attack Prevention**:
    Before writing, the module checks if the target file is a symlink. If so,
    the write is refused. The ``O_NOFOLLOW`` flag is used during file open to
    prevent race conditions between the check and the open.

**Race Condition Mitigation**:
    Using ``os.open()`` with ``O_NOFOLLOW`` provides atomic symlink checking
    during the open operation itself, preventing TOCTOU (time-of-check to
    time-of-use) vulnerabilities.

**Restrictive File Permissions (SEC-005)**:
    Log files are created with 0o600 (owner read/write only) to prevent
    unauthorized access to potentially sensitive prompt data. This is more
    restrictive than the typical 0o644 default.

File Locations
--------------

Log files are stored at the project root:
    - Path: ``{project_root}/.prompt-log.json``
    - Created: When first log entry is written
    - Archived: Moved to completed project dir on ``/c``
"""

from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
from pathlib import Path

from .log_entry import LogEntry

PROMPT_LOG_FILENAME = ".prompt-log.json"

# SEC-005: Restrictive file permissions for log files
# 0o600 = owner read/write only (no group or world access)
# This prevents other users from reading potentially sensitive prompt data
LOG_FILE_PERMISSIONS = 0o600

# RES-HIGH-001: Timeout for file lock acquisition (seconds)
# Prevents indefinite blocking if another process holds the lock
LOCK_TIMEOUT_SECONDS = 30


class LockTimeoutError(TimeoutError):
    """Raised when file lock acquisition times out."""


class PathTraversalError(ValueError):
    """Raised when a path traversal attack is detected.

    This exception indicates that a provided path attempts to escape
    the expected directory boundaries, such as using ``../`` sequences.
    """


def _validate_path(project_dir: str | Path, target_path: Path) -> None:
    """
    Validate that target_path is within project_dir boundaries.

    Args:
        project_dir: The expected base directory
        target_path: The path to validate

    Raises:
        PathTraversalError: If path traversal is detected
    """
    resolved_base = Path(project_dir).resolve()
    resolved_target = target_path.resolve()

    # Check that resolved target starts with resolved base
    try:
        resolved_target.relative_to(resolved_base)
    except ValueError as e:
        raise PathTraversalError(
            f"Path traversal detected: {target_path} escapes {resolved_base}",
        ) from e


def _check_symlink_safety(path: Path) -> bool:
    """
    Check if a path is safe from symlink attacks.

    This only checks the target file itself, not parent directories,
    since system-level symlinks (like /var -> /private/var on macOS)
    are legitimate and safe.

    Args:
        path: The path to check

    Returns:
        True if safe, False if the target file is a symlink
    """
    # Only check if the file itself is a symlink
    # We don't check parent directories because system-level symlinks are safe
    # and the path traversal check already validates the resolved path
    if path.is_symlink():
        return False

    return True


def get_log_path(project_dir: str | Path) -> Path:
    """
    Get the full path to the prompt log file for a project.

    Performs path canonicalization and validation to prevent
    path traversal attacks.

    Args:
        project_dir: Path to the spec project directory

    Returns:
        Full Path object to .prompt-log.json

    Raises:
        PathTraversalError: If path traversal is detected
    """
    resolved = Path(project_dir).resolve()
    log_path = resolved / PROMPT_LOG_FILENAME

    # Verify resolved path is still under project_dir
    _validate_path(resolved, log_path)

    return log_path


def append_to_log(project_dir: str, entry: LogEntry) -> bool:
    """
    Atomically append a log entry to the project's .prompt-log.json.

    Uses file locking to ensure safe concurrent writes.
    Creates the file if it doesn't exist.

    Security measures:
    - Path traversal validation
    - Symlink attack prevention
    - Atomic write with file locking
    - Restrictive file permissions (0o600 - owner only)

    Args:
        project_dir: Path to the spec project directory
        entry: LogEntry to append

    Returns:
        True if successful, False otherwise
    """
    try:
        log_path = get_log_path(project_dir)
    except PathTraversalError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Security error: {e}\n")
        return False

    try:
        # Create parent directory if needed
        parent_dir = log_path.parent
        if parent_dir and not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        # Security: Check for symlink attacks before writing
        # SEC-MED-002: This check creates a TOCTOU window, but O_NOFOLLOW below
        # provides the actual atomic protection. This check is kept for
        # user-friendly error messages when symlinks are detected.
        if log_path.exists() and not _check_symlink_safety(log_path):
            sys.stderr.write(
                f"claude-spec prompt_capture: Symlink detected at {log_path}, "
                "refusing to write\n",
            )
            return False

        # Open in append mode, create if doesn't exist
        # SEC-MED-002: Use os.open with O_NOFOLLOW to atomically prevent symlink attacks
        # SEC-005: Use restrictive permissions (0o600) for new log files
        try:
            fd = os.open(
                str(log_path),
                os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
                LOG_FILE_PERMISSIONS,
            )
        except OSError as e:
            # If O_NOFOLLOW fails because path is symlink, this is a security issue
            if "symbolic link" in str(e).lower() or e.errno == 40:  # ELOOP
                sys.stderr.write(
                    f"claude-spec prompt_capture: Symlink attack prevented: {e}\n",
                )
                return False
            raise

        try:
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                # RES-HIGH-001: Acquire exclusive lock with timeout
                # Set up alarm signal to prevent indefinite blocking
                def _lock_timeout_handler(_signum: int, _frame: object) -> None:
                    raise LockTimeoutError(
                        f"Lock acquisition timed out after {LOCK_TIMEOUT_SECONDS}s",
                    )

                old_handler = signal.signal(signal.SIGALRM, _lock_timeout_handler)
                signal.alarm(LOCK_TIMEOUT_SECONDS)
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                finally:
                    signal.alarm(0)  # Cancel the alarm
                    signal.signal(signal.SIGALRM, old_handler)  # Restore handler

                try:
                    # Write JSON line with newline
                    f.write(entry.to_json() + "\n")
                    f.flush()
                    os.fsync(f.fileno())  # Ensure written to disk
                finally:
                    # Release lock
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        except LockTimeoutError as e:
            sys.stderr.write(f"claude-spec prompt_capture: {e}\n")
            return False
        except Exception:
            # fd is already closed by fdopen on error
            raise

        return True

    except OSError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Error writing log: {e}\n")
        return False


def read_log(project_dir: str) -> list[LogEntry]:
    """
    Read all entries from the prompt log.

    Args:
        project_dir: Path to the spec project directory

    Returns:
        List of LogEntry objects, empty list if file doesn't exist or errors
    """
    try:
        log_path = get_log_path(project_dir)
    except PathTraversalError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Security error: {e}\n")
        return []

    if not log_path.is_file():
        return []

    # Security: Check for symlink attacks before reading
    if not _check_symlink_safety(log_path):
        sys.stderr.write(
            f"claude-spec prompt_capture: Symlink detected at {log_path}, "
            "refusing to read\n",
        )
        return []

    entries = []

    try:
        with log_path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(LogEntry.from_json(line))
                except json.JSONDecodeError:
                    sys.stderr.write(
                        f"claude-spec prompt_capture: Skipping corrupted line "
                        f"{line_num} in {log_path}\n",
                    )
    except OSError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Error reading log: {e}\n")

    return entries


def get_recent_entries(project_dir: str, count: int = 10) -> list[LogEntry]:
    """
    Get the most recent log entries.

    Args:
        project_dir: Path to the spec project directory
        count: Number of recent entries to return

    Returns:
        List of LogEntry objects (most recent last)
    """
    entries = read_log(project_dir)
    return entries[-count:] if entries else []


def log_exists(project_dir: str) -> bool:
    """Check if a prompt log exists for the project."""
    try:
        log_path = get_log_path(project_dir)
        return log_path.is_file()
    except PathTraversalError:
        return False


def clear_log(project_dir: str) -> bool:
    """
    Clear (delete) the prompt log for a project.

    Args:
        project_dir: Path to the spec project directory

    Returns:
        True if successful or file didn't exist, False on error
    """
    try:
        log_path = get_log_path(project_dir)
    except PathTraversalError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Security error: {e}\n")
        return False

    if not log_path.is_file():
        return True

    # Security: Check for symlink attacks before deleting
    if not _check_symlink_safety(log_path):
        sys.stderr.write(
            f"claude-spec prompt_capture: Symlink detected at {log_path}, "
            "refusing to delete\n",
        )
        return False

    try:
        log_path.unlink()
        return True
    except OSError as e:
        sys.stderr.write(f"claude-spec prompt_capture: Error clearing log: {e}\n")
        return False
