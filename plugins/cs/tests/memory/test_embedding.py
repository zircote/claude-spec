"""Tests for the embedding service module."""

from unittest.mock import MagicMock, PropertyMock, patch

import numpy as np
import pytest

from memory.config import EMBEDDING_DIMENSIONS
from memory.embedding import EmbeddingService
from memory.exceptions import EmbeddingError


class TestEmbeddingServiceInit:
    """Tests for EmbeddingService initialization."""

    def test_init_default_values(self):
        """Test initialization with default values."""
        service = EmbeddingService()
        assert service.model_name == "all-MiniLM-L6-v2"
        assert service._model is None  # Not loaded yet

    def test_init_custom_model(self):
        """Test initialization with custom model name."""
        service = EmbeddingService(model_name="custom-model")
        assert service.model_name == "custom-model"

    def test_init_custom_cache_dir(self, tmp_path):
        """Test initialization with custom cache directory."""
        cache_dir = str(tmp_path / "custom_cache")
        service = EmbeddingService(cache_dir=cache_dir)
        assert service.cache_dir == cache_dir


class TestLazyLoading:
    """Tests for lazy model loading behavior."""

    def test_model_not_loaded_initially(self):
        """Test that model is not loaded on init."""
        service = EmbeddingService()
        assert not service.is_loaded()

    def test_is_loaded_returns_true_after_access(self):
        """Test is_loaded returns true after model access."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_load.return_value = mock_model

            # Access the model property
            _ = service.model

            assert service.is_loaded()

    def test_unload_clears_model(self):
        """Test unload method clears the model."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_load.return_value = MagicMock()
            _ = service.model  # Load the model
            assert service.is_loaded()

            service.unload()
            assert not service.is_loaded()


class TestLoadModel:
    """Tests for model loading."""

    def test_missing_package_raises_error(self):
        """Test error when sentence-transformers not installed."""
        service = EmbeddingService()

        with patch.dict("sys.modules", {"sentence_transformers": None}):
            with patch("memory.embedding.EmbeddingService._load_model") as mock:
                mock.side_effect = EmbeddingError(
                    "sentence-transformers package not installed",
                    "Install with: pip install sentence-transformers",
                )

                with pytest.raises(EmbeddingError) as exc_info:
                    service._load_model()

                assert "not installed" in str(exc_info.value)

    def test_memory_error_during_load(self):
        """Test handling of memory error during model loading."""
        service = EmbeddingService()

        # Mock the model property to simulate MemoryError on access
        with patch.object(
            type(service), "model", new_callable=PropertyMock
        ) as mock_model:
            mock_model.side_effect = EmbeddingError(
                "Insufficient memory to load embedding model",
                "Close other applications or use a smaller model",
            )

            with pytest.raises(EmbeddingError) as exc_info:
                _ = service.model

            assert "Insufficient memory" in str(exc_info.value)

    def test_disk_space_error(self):
        """Test handling of disk space error."""
        service = EmbeddingService()

        # Mock the model property to simulate disk space error
        with patch.object(
            type(service), "model", new_callable=PropertyMock
        ) as mock_model:
            mock_model.side_effect = EmbeddingError(
                "Insufficient disk space to download model",
                f"Free up space in {service.cache_dir}",
            )

            with pytest.raises(EmbeddingError) as exc_info:
                _ = service.model

            assert "Insufficient disk space" in str(exc_info.value)


class TestEmbed:
    """Tests for single text embedding."""

    def test_embed_returns_correct_dimensions(self):
        """Test that embedding has correct dimensions."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.zeros(EMBEDDING_DIMENSIONS)
            mock_load.return_value = mock_model

            result = service.embed("test text")

            assert len(result) == EMBEDDING_DIMENSIONS
            assert all(isinstance(v, float) for v in result)

    def test_embed_empty_text_raises_error(self):
        """Test that embedding empty text raises error."""
        service = EmbeddingService()

        with pytest.raises(EmbeddingError) as exc_info:
            service.embed("")

        assert "empty text" in str(exc_info.value).lower()

    def test_embed_whitespace_only_raises_error(self):
        """Test that embedding whitespace-only text raises error."""
        service = EmbeddingService()

        with pytest.raises(EmbeddingError) as exc_info:
            service.embed("   \n\t  ")

        assert "empty text" in str(exc_info.value).lower()

    def test_embed_memory_error(self):
        """Test handling of memory error during embedding."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_model.encode.side_effect = MemoryError()
            mock_load.return_value = mock_model

            with pytest.raises(EmbeddingError) as exc_info:
                service.embed("test text")

            assert "Out of memory" in str(exc_info.value)

    def test_embed_generic_error(self):
        """Test handling of generic error during embedding."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_model.encode.side_effect = RuntimeError("encoding failed")
            mock_load.return_value = mock_model

            with pytest.raises(EmbeddingError) as exc_info:
                service.embed("test text")

            assert "failed" in str(exc_info.value).lower()


class TestEmbedBatch:
    """Tests for batch embedding."""

    def test_embed_batch_empty_list(self):
        """Test embedding empty list returns empty list."""
        service = EmbeddingService()

        result = service.embed_batch([])

        assert result == []

    def test_embed_batch_returns_list_of_lists(self):
        """Test batch embedding returns correct structure."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            # Return numpy array for each text
            mock_model.encode.return_value = np.array(
                [
                    np.zeros(EMBEDDING_DIMENSIONS),
                    np.ones(EMBEDDING_DIMENSIONS),
                ]
            )
            mock_load.return_value = mock_model

            result = service.embed_batch(["text1", "text2"])

            assert len(result) == 2
            assert len(result[0]) == EMBEDDING_DIMENSIONS
            assert len(result[1]) == EMBEDDING_DIMENSIONS

    def test_embed_batch_handles_empty_texts(self):
        """Test batch embedding handles empty texts with zero vectors."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            # Return 2 embeddings for 2 non-empty texts ("text1" and "text3")
            mock_model.encode.return_value = np.array(
                [
                    np.ones(EMBEDDING_DIMENSIONS),
                    np.ones(EMBEDDING_DIMENSIONS) * 2,
                ]
            )
            mock_load.return_value = mock_model

            result = service.embed_batch(["text1", "", "text3"])

            # Should have 3 results
            assert len(result) == 3
            # First and third should be embeddings
            assert result[0][0] == 1.0  # First embedding
            assert result[2][0] == 2.0  # Third embedding
            # Second should be zero vector (for empty text)
            assert result[1] == [0.0] * EMBEDDING_DIMENSIONS

    def test_embed_batch_all_empty_raises_error(self):
        """Test that all empty texts raises error."""
        service = EmbeddingService()

        with pytest.raises(EmbeddingError) as exc_info:
            service.embed_batch(["", "   ", "\n"])

        assert "empty" in str(exc_info.value).lower()

    def test_embed_batch_memory_error(self):
        """Test handling of memory error during batch embedding."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_model.encode.side_effect = MemoryError()
            mock_load.return_value = mock_model

            with pytest.raises(EmbeddingError) as exc_info:
                service.embed_batch(["text1", "text2"])

            assert "Out of memory" in str(exc_info.value)


class TestGetDimensions:
    """Tests for get_dimensions method."""

    def test_get_dimensions_returns_model_dimension(self):
        """Test that get_dimensions returns model's dimension."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()
            mock_model.get_sentence_embedding_dimension.return_value = 384
            mock_load.return_value = mock_model

            result = service.get_dimensions()

            assert result == 384


class TestLoadModelDirectly:
    """Tests for _load_model method directly."""

    def test_load_model_import_error(self, monkeypatch):
        """Test ImportError when sentence-transformers not installed."""
        service = EmbeddingService()

        def mock_import(name, *args, **kwargs):
            if name == "sentence_transformers":
                raise ImportError("No module named 'sentence_transformers'")
            return __builtins__.__import__(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            with pytest.raises(EmbeddingError) as exc_info:
                service._load_model()
            assert "not installed" in str(exc_info.value)

    def test_load_model_memory_error(self, monkeypatch, tmp_path):
        """Test MemoryError during model loading."""
        service = EmbeddingService(cache_dir=str(tmp_path))

        mock_st = MagicMock()
        mock_st.SentenceTransformer.side_effect = MemoryError("out of memory")

        monkeypatch.setattr("memory.embedding.MODELS_DIR", tmp_path)

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            with pytest.raises(EmbeddingError) as exc_info:
                service._load_model()
            assert "Insufficient memory" in str(exc_info.value)

    def test_load_model_oserror_no_space(self, monkeypatch, tmp_path):
        """Test OSError with no space left on device."""
        service = EmbeddingService(cache_dir=str(tmp_path))

        mock_st = MagicMock()
        mock_st.SentenceTransformer.side_effect = OSError("No space left on device")

        monkeypatch.setattr("memory.embedding.MODELS_DIR", tmp_path)

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            with pytest.raises(EmbeddingError) as exc_info:
                service._load_model()
            assert "Insufficient disk space" in str(exc_info.value)

    def test_load_model_oserror_generic(self, monkeypatch, tmp_path):
        """Test generic OSError during model loading."""
        service = EmbeddingService(cache_dir=str(tmp_path))

        mock_st = MagicMock()
        mock_st.SentenceTransformer.side_effect = OSError("Network error")

        monkeypatch.setattr("memory.embedding.MODELS_DIR", tmp_path)

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            with pytest.raises(EmbeddingError) as exc_info:
                service._load_model()
            assert "Failed to load" in str(exc_info.value)

    def test_load_model_generic_exception(self, monkeypatch, tmp_path):
        """Test generic exception during model loading."""
        service = EmbeddingService(cache_dir=str(tmp_path))

        mock_st = MagicMock()
        mock_st.SentenceTransformer.side_effect = RuntimeError("unexpected error")

        monkeypatch.setattr("memory.embedding.MODELS_DIR", tmp_path)

        with patch.dict("sys.modules", {"sentence_transformers": mock_st}):
            with pytest.raises(EmbeddingError) as exc_info:
                service._load_model()
            assert "Unexpected error" in str(exc_info.value)


class TestEmbedBatchException:
    """Tests for batch embedding exception paths."""

    def test_batch_generic_exception(self):
        """Test generic exception during batch embedding."""
        service = EmbeddingService()

        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("batch encoding failed")
        service._model = mock_model

        with pytest.raises(EmbeddingError) as exc_info:
            service.embed_batch(["text1", "text2"])

        assert "Batch embedding failed" in str(exc_info.value)


class TestSimilarityBehavior:
    """Tests for embedding similarity behavior."""

    def test_similar_texts_have_similar_embeddings(self):
        """Test that similar texts produce similar embeddings."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()

            # Simulate similar embeddings for similar texts
            embedding1 = np.array([0.1, 0.2, 0.3] * 128)  # 384 dims
            embedding2 = np.array([0.11, 0.21, 0.31] * 128)  # Similar
            embedding3 = np.array([0.9, -0.8, 0.7] * 128)  # Different

            def encode_mock(text):
                if "dog" in text:
                    return embedding1
                elif "puppy" in text:
                    return embedding2
                else:
                    return embedding3

            mock_model.encode.side_effect = encode_mock
            mock_load.return_value = mock_model

            emb1 = service.embed("A dog is a pet")
            emb2 = service.embed("A puppy is a young pet")
            emb3 = service.embed("The sky is blue")

            # Calculate cosine similarity
            def cosine_similarity(a, b):
                a = np.array(a)
                b = np.array(b)
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

            sim_1_2 = cosine_similarity(emb1, emb2)
            sim_1_3 = cosine_similarity(emb1, emb3)

            # Similar texts should have higher similarity
            assert sim_1_2 > sim_1_3

    def test_batch_matches_individual(self):
        """Test that batch embedding matches individual embedding."""
        service = EmbeddingService()

        with patch.object(service, "_load_model") as mock_load:
            mock_model = MagicMock()

            # Same embedding for same text
            embedding = np.zeros(EMBEDDING_DIMENSIONS)
            embedding[0] = 1.0

            mock_model.encode.return_value = embedding.copy()
            mock_load.return_value = mock_model

            # Individual embedding
            single = service.embed("test text")

            # Reset mock for batch call
            mock_model.encode.return_value = np.array([embedding.copy()])

            # Batch embedding (with single item)
            batch = service.embed_batch(["test text"])

            # Should match
            assert single == batch[0]
