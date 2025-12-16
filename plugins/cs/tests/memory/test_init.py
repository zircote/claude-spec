"""Tests for memory/__init__.py lazy imports."""

import pytest


class TestLazyImports:
    """Tests for lazy service factory functions."""

    def test_get_capture_service(self):
        """Test lazy import of CaptureService."""
        from memory import get_capture_service

        service_class = get_capture_service()
        assert service_class.__name__ == "CaptureService"

    def test_get_recall_service(self):
        """Test lazy import of RecallService."""
        from memory import get_recall_service

        service_class = get_recall_service()
        assert service_class.__name__ == "RecallService"

    def test_get_sync_service(self):
        """Test lazy import of SyncService."""
        from memory import get_sync_service

        service_class = get_sync_service()
        assert service_class.__name__ == "SyncService"

    def test_get_search_optimizer(self):
        """Test lazy import of SearchOptimizer."""
        from memory import get_search_optimizer

        optimizer = get_search_optimizer()
        # get_optimizer returns an instance, not a class
        assert optimizer is not None

    def test_get_pattern_manager(self):
        """Test lazy import of PatternManager."""
        from memory import get_pattern_manager

        manager = get_pattern_manager()
        assert manager is not None

    def test_get_lifecycle_manager(self):
        """Test lazy import of LifecycleManager."""
        from memory import get_lifecycle_manager

        manager = get_lifecycle_manager()
        assert manager is not None


class TestExports:
    """Tests for module exports."""

    def test_exports_models(self):
        """Test that models are exported."""
        from memory import (
            HydratedMemory,
            HydrationLevel,
            IndexStats,
            Memory,
            MemoryResult,
            SpecContext,
            VerificationResult,
        )

        assert Memory is not None
        assert MemoryResult is not None
        assert HydrationLevel is not None
        assert HydratedMemory is not None
        assert SpecContext is not None
        assert IndexStats is not None
        assert VerificationResult is not None

    def test_exports_config(self):
        """Test that config constants are exported."""
        from memory import (
            DEFAULT_EMBEDDING_MODEL,
            EMBEDDING_DIMENSIONS,
            INDEX_PATH,
            LOCK_FILE,
            LOCK_TIMEOUT,
            NAMESPACES,
        )

        assert NAMESPACES is not None
        assert DEFAULT_EMBEDDING_MODEL is not None
        assert EMBEDDING_DIMENSIONS > 0
        assert INDEX_PATH is not None
        assert LOCK_FILE is not None
        assert LOCK_TIMEOUT > 0

    def test_exports_exceptions(self):
        """Test that exceptions are exported."""
        from memory import (
            CaptureError,
            EmbeddingError,
            MemoryError,
            MemoryIndexError,
            ParseError,
            StorageError,
        )

        assert MemoryError is not None
        assert StorageError is not None
        assert MemoryIndexError is not None
        assert EmbeddingError is not None
        assert ParseError is not None
        assert CaptureError is not None

    def test_version(self):
        """Test that version is defined."""
        from memory import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_all_exports(self):
        """Test that __all__ contains expected items."""
        from memory import __all__

        expected = [
            "Memory",
            "MemoryResult",
            "HydrationLevel",
            "HydratedMemory",
            "SpecContext",
            "IndexStats",
            "VerificationResult",
            "NAMESPACES",
            "DEFAULT_EMBEDDING_MODEL",
            "EMBEDDING_DIMENSIONS",
            "INDEX_PATH",
            "LOCK_FILE",
            "LOCK_TIMEOUT",
            "MemoryError",
            "StorageError",
            "MemoryIndexError",
            "EmbeddingError",
            "ParseError",
            "CaptureError",
            "get_capture_service",
            "get_recall_service",
            "get_sync_service",
            "get_search_optimizer",
            "get_pattern_manager",
            "get_lifecycle_manager",
        ]

        for item in expected:
            assert item in __all__
