"""
cs-memory: Git-native memory system for claude-spec.

This module provides persistent, semantically-searchable context across Claude Code
sessions using Git notes as the canonical storage layer and SQLite with sqlite-vec
for semantic retrieval.

Core Principle: "If a memory has no commit, it had no effect."
"""

from .config import (
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_DIMENSIONS,
    INDEX_PATH,
    LOCK_FILE,
    LOCK_TIMEOUT,
    NAMESPACES,
)
from .exceptions import (
    CaptureError,
    EmbeddingError,
    MemoryError,
    MemoryIndexError,
    ParseError,
    StorageError,
)
from .models import (
    HydratedMemory,
    HydrationLevel,
    IndexStats,
    Memory,
    MemoryResult,
    SpecContext,
    VerificationResult,
)


# Services - lazy import to avoid loading heavy dependencies on module import
def get_capture_service():
    """Get the CaptureService (lazy import)."""
    from .capture import CaptureService

    return CaptureService


def get_recall_service():
    """Get the RecallService (lazy import)."""
    from .recall import RecallService

    return RecallService


def get_sync_service():
    """Get the SyncService (lazy import)."""
    from .sync import SyncService

    return SyncService


def get_search_optimizer():
    """Get the SearchOptimizer (lazy import)."""
    from .search import get_optimizer

    return get_optimizer()


def get_pattern_manager():
    """Get the PatternManager (lazy import)."""
    from .patterns import get_pattern_manager

    return get_pattern_manager()


def get_lifecycle_manager():
    """Get the LifecycleManager (lazy import)."""
    from .lifecycle import get_lifecycle_manager

    return get_lifecycle_manager()


def get_embedding_service(preload: bool = False):
    """
    Get the embedding service singleton (lazy import).

    Args:
        preload: If True, force model loading immediately.
    """
    from .embedding import get_embedding_service as _get_embedding_service

    return _get_embedding_service(preload=preload)


def preload_embedding_model():
    """Pre-warm the embedding model for low-latency hooks."""
    from .embedding import preload_model

    preload_model()


__version__ = "1.0.0"

__all__ = [
    # Models
    "Memory",
    "MemoryResult",
    "HydrationLevel",
    "HydratedMemory",
    "SpecContext",
    "IndexStats",
    "VerificationResult",
    # Config
    "NAMESPACES",
    "DEFAULT_EMBEDDING_MODEL",
    "EMBEDDING_DIMENSIONS",
    "INDEX_PATH",
    "LOCK_FILE",
    "LOCK_TIMEOUT",
    # Exceptions
    "MemoryError",
    "StorageError",
    "MemoryIndexError",
    "EmbeddingError",
    "ParseError",
    "CaptureError",
    # Service factories
    "get_capture_service",
    "get_recall_service",
    "get_sync_service",
    "get_search_optimizer",
    "get_pattern_manager",
    "get_lifecycle_manager",
    "get_embedding_service",
    "preload_embedding_model",
]
