"""
Exception hierarchy for cs-memory.

All exceptions include recovery suggestions per NFR-009.
"""

from dataclasses import dataclass
from enum import Enum


class ErrorCategory(Enum):
    """Categories of errors that can occur in cs-memory."""

    STORAGE = "storage"  # Git notes operations
    INDEX = "index"  # SQLite/sqlite-vec operations
    EMBEDDING = "embedding"  # Embedding generation
    PARSE = "parse"  # Note content parsing
    CAPTURE = "capture"  # Memory capture orchestration


@dataclass
class MemoryError(Exception):
    """
    Base exception for cs-memory errors.

    All exceptions include a category, message, and recovery action
    to help users understand and resolve issues.
    """

    category: ErrorCategory
    message: str
    recovery_action: str

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}\n-> {self.recovery_action}"


class StorageError(MemoryError):
    """
    Git notes operation failed.

    Common causes:
    - No commits in repository
    - Permission denied
    - Invalid ref name
    - Merge conflicts
    """

    def __init__(self, message: str, recovery_action: str) -> None:
        super().__init__(ErrorCategory.STORAGE, message, recovery_action)


class MemoryIndexError(MemoryError):
    """
    SQLite or sqlite-vec operation failed.

    Common causes:
    - Database locked by another process
    - Corrupted index file
    - sqlite-vec extension not found
    - Schema migration needed

    Note: Named MemoryIndexError to avoid shadowing Python's built-in IndexError.
    """

    def __init__(self, message: str, recovery_action: str) -> None:
        super().__init__(ErrorCategory.INDEX, message, recovery_action)


class EmbeddingError(MemoryError):
    """
    Embedding generation failed.

    Common causes:
    - Insufficient memory for model
    - Corrupted model cache
    - Model download failed
    - CUDA/MPS device error
    """

    def __init__(self, message: str, recovery_action: str) -> None:
        super().__init__(ErrorCategory.EMBEDDING, message, recovery_action)


class ParseError(MemoryError):
    """
    Note content parsing failed.

    Common causes:
    - Invalid YAML front matter
    - Missing required fields
    - Invalid timestamp format
    - Malformed Markdown
    """

    def __init__(self, message: str, recovery_action: str) -> None:
        super().__init__(ErrorCategory.PARSE, message, recovery_action)


class CaptureError(MemoryError):
    """
    Memory capture operation failed.

    Common causes:
    - Lock acquisition timeout
    - Concurrent capture in progress
    - Validation failure
    """

    def __init__(self, message: str, recovery_action: str) -> None:
        super().__init__(ErrorCategory.CAPTURE, message, recovery_action)


# Pre-defined common errors with helpful messages
NO_COMMITS_ERROR = StorageError(
    "Cannot capture memory: no commits exist in this repository",
    "Create at least one commit first: git commit --allow-empty -m 'initial'",
)

PERMISSION_DENIED_ERROR = StorageError(
    "Cannot write to Git notes: permission denied",
    "Check repository permissions and ensure you have write access",
)

INDEX_LOCKED_ERROR = MemoryIndexError(
    "Index database is locked by another process",
    "Wait for the other process to complete, or check for stuck processes",
)

SQLITE_VEC_MISSING_ERROR = MemoryIndexError(
    "sqlite-vec extension not found", "Install sqlite-vec: pip install sqlite-vec"
)

MODEL_OOM_ERROR = EmbeddingError(
    "Insufficient memory to load embedding model",
    "Close other applications or use a smaller model",
)

MODEL_CORRUPTED_ERROR = EmbeddingError(
    "Embedding model cache corrupted", "Delete .cs-memory/models/ directory and retry"
)

INVALID_YAML_ERROR = ParseError(
    "Note contains invalid YAML front matter",
    "Check note format - YAML must be valid and enclosed in --- markers",
)

MISSING_FIELD_ERROR = ParseError(
    "Note missing required field", "Ensure note has: type, spec, timestamp, summary"
)

LOCK_TIMEOUT_ERROR = CaptureError(
    "Another capture operation is in progress",
    "Wait and retry, or check for stuck processes",
)
