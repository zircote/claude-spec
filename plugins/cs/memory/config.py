"""
Configuration constants for cs-memory.

All paths are relative to the repository root unless otherwise specified.
"""

from pathlib import Path

# Git notes namespace structure
# Each maps to refs/notes/cs/<namespace>
NAMESPACES = frozenset(
    {
        "inception",  # Problem statements, scope, success criteria
        "elicitation",  # Requirements clarifications, constraints
        "research",  # External findings, technology evaluations
        "decisions",  # Architecture Decision Records
        "progress",  # Task completions, milestones
        "blockers",  # Obstacles and resolutions
        "reviews",  # Code review findings
        "learnings",  # Technical insights, patterns
        "retrospective",  # Post-mortems
        "patterns",  # Cross-spec generalizations
    }
)

# Embedding model configuration
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

# Index storage (gitignored)
INDEX_DIR = Path(".cs-memory")
INDEX_PATH = INDEX_DIR / "index.db"
MODELS_DIR = INDEX_DIR / "models"
CONFIG_FILE = INDEX_DIR / "config.yaml"

# Concurrency control
LOCK_FILE = INDEX_DIR / ".capture.lock"
LOCK_TIMEOUT = 5  # seconds

# Recall defaults
DEFAULT_RECALL_LIMIT = 10
DEFAULT_SEARCH_LIMIT = 10
MAX_RECALL_LIMIT = 100

# Search optimization
SEARCH_CACHE_TTL_SECONDS = 300.0  # 5 minutes
SEARCH_CACHE_MAX_SIZE = 100

# Note schema
NOTE_REQUIRED_FIELDS = frozenset({"type", "spec", "timestamp", "summary"})
NOTE_OPTIONAL_FIELDS = frozenset({"phase", "tags", "relates_to", "status"})
MAX_SUMMARY_LENGTH = 100

# Performance thresholds (NFR targets)
SEARCH_TIMEOUT_MS = 500
CAPTURE_TIMEOUT_MS = 2000
REINDEX_TIMEOUT_MS = 60000

# Auto-capture namespaces (enabled by default)
AUTO_CAPTURE_NAMESPACES = frozenset(
    {
        "inception",
        "elicitation",
        "research",
        "decisions",
        "progress",
        "blockers",
        "learnings",
        "retrospective",
        "patterns",
    }
)

# Proactive recall settings (US-016, NFR-013)
MAX_PROACTIVE_SUGGESTIONS = 3
