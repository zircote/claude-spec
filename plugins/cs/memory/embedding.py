"""
Embedding service for cs-memory.

Provides local embedding generation using sentence-transformers.
Model is loaded lazily on first use and cached for subsequent calls.

Module-level singleton pattern allows pre-warming during SessionStart
to avoid cold-start latency (2-5s) during latency-sensitive hooks.
"""

import threading
from typing import TYPE_CHECKING

from .config import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSIONS, MODELS_DIR
from .exceptions import EmbeddingError

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# Thread-safe singleton for module-level caching
_embedding_service: "EmbeddingService | None" = None
_embedding_lock = threading.Lock()


def get_embedding_service(preload: bool = False) -> "EmbeddingService":
    """
    Get the module-level embedding service singleton.

    Thread-safe lazy initialization with optional pre-loading.

    Args:
        preload: If True, force model loading immediately.
                 Use during SessionStart hook (500ms budget) to avoid
                 cold start during latency-sensitive hooks (<100ms budget).

    Returns:
        Shared EmbeddingService instance
    """
    global _embedding_service

    if _embedding_service is None:
        with _embedding_lock:
            # Double-checked locking
            if _embedding_service is None:
                _embedding_service = EmbeddingService()

    if preload and not _embedding_service.is_loaded():
        # Force model loading by accessing the model property
        _ = _embedding_service.model

    return _embedding_service


def preload_model() -> None:
    """
    Pre-warm the embedding model.

    Call during SessionStart hook to eliminate cold-start latency
    in subsequent UserPromptSubmit and PostToolUse hooks.
    """
    get_embedding_service(preload=True)


def reset_singleton() -> None:
    """
    Reset the singleton instance (for testing only).

    Warning: Not thread-safe, only use in test teardown.
    """
    global _embedding_service
    if _embedding_service is not None:
        _embedding_service.unload()
    _embedding_service = None


class EmbeddingService:
    """
    Local embedding generation service.

    Uses sentence-transformers with lazy model loading to minimize
    startup time. The model is downloaded on first use if not cached.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_EMBEDDING_MODEL,
        cache_dir: str | None = None,
    ):
        """
        Initialize the embedding service.

        Args:
            model_name: Name of the sentence-transformers model
            cache_dir: Directory to cache models (default: .cs-memory/models)
        """
        self.model_name = model_name
        self.cache_dir = cache_dir or str(MODELS_DIR)
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> "SentenceTransformer":
        """
        Lazily load and return the embedding model.

        Returns:
            Loaded SentenceTransformer model

        Raises:
            EmbeddingError: If model loading fails
        """
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> "SentenceTransformer":
        """
        Load the embedding model.

        Returns:
            Loaded model

        Raises:
            EmbeddingError: On loading failures
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as err:
            raise EmbeddingError(
                "sentence-transformers package not installed",
                "Install with: pip install sentence-transformers",
            ) from err

        try:
            # Create cache directory if needed
            MODELS_DIR.mkdir(parents=True, exist_ok=True)

            model = SentenceTransformer(
                self.model_name,
                cache_folder=self.cache_dir,
            )
            return model

        except MemoryError as err:
            raise EmbeddingError(
                "Insufficient memory to load embedding model",
                "Close other applications or use a smaller model",
            ) from err
        except OSError as e:
            if "No space left" in str(e):
                raise EmbeddingError(
                    "Insufficient disk space to download model",
                    f"Free up space in {self.cache_dir}",
                ) from e
            raise EmbeddingError(
                f"Failed to load embedding model: {e}",
                "Check network connection and try again",
            ) from e
        except Exception as e:
            raise EmbeddingError(
                f"Unexpected error loading model: {e}",
                f"Try deleting {self.cache_dir} and retrying",
            ) from e

    def embed(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not text.strip():
            raise EmbeddingError(
                "Cannot embed empty text", "Provide non-empty text for embedding"
            )

        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except MemoryError as err:
            raise EmbeddingError(
                "Out of memory during embedding generation",
                "Text may be too long or system memory is low",
            ) from err
        except Exception as e:
            raise EmbeddingError(
                f"Embedding generation failed: {e}", "Check input text and try again"
            ) from e

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        More efficient than calling embed() repeatedly due to batching.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not texts:
            return []

        # Filter empty texts
        non_empty_indices = [i for i, t in enumerate(texts) if t.strip()]
        non_empty_texts = [texts[i] for i in non_empty_indices]

        if not non_empty_texts:
            raise EmbeddingError(
                "All texts are empty", "Provide at least one non-empty text"
            )

        try:
            embeddings = self.model.encode(non_empty_texts)
            result: list[list[float] | None] = [None] * len(texts)

            # Map embeddings back to original indices
            for i, emb in zip(non_empty_indices, embeddings, strict=True):
                result[i] = emb.tolist()

            # Handle empty texts (return zero vectors)
            zero_vector = [0.0] * EMBEDDING_DIMENSIONS
            for i, r in enumerate(result):
                if r is None:
                    result[i] = zero_vector

            # At this point, all None values have been replaced with zero vectors
            return [r for r in result if r is not None]

        except MemoryError as err:
            raise EmbeddingError(
                "Out of memory during batch embedding",
                "Try smaller batch size or free system memory",
            ) from err
        except Exception as e:
            raise EmbeddingError(
                f"Batch embedding failed: {e}", "Check input texts and try again"
            ) from e

    def get_dimensions(self) -> int:
        """
        Get the embedding dimensions for the loaded model.

        Returns:
            Number of dimensions (e.g., 384 for all-MiniLM-L6-v2)
        """
        dims = self.model.get_sentence_embedding_dimension()
        return dims if dims is not None else EMBEDDING_DIMENSIONS

    def is_loaded(self) -> bool:
        """Check if the model is already loaded."""
        return self._model is not None

    def unload(self) -> None:
        """Unload the model to free memory."""
        self._model = None
