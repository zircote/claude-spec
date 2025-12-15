"""
Sync service for cs-memory.

Handles synchronization between Git notes (source of truth) and
the SQLite index (derived, for fast search).
"""

from collections.abc import Callable

from .config import NAMESPACES
from .embedding import EmbeddingService
from .exceptions import ParseError
from .git_ops import GitOps
from .index import IndexService
from .models import IndexStats, Memory, VerificationResult
from .note_parser import extract_memory_id, parse_note
from .utils import parse_iso_timestamp_safe


class SyncService:
    """
    Manages synchronization between Git notes and the search index.

    The Git notes are the source of truth - the index can always be
    rebuilt from notes. This service handles:
    - Incremental sync after capture
    - Full reindex from all notes
    - Verification of index consistency
    """

    def __init__(
        self,
        git_ops: GitOps | None = None,
        embedding_service: EmbeddingService | None = None,
        index_service: IndexService | None = None,
    ):
        """
        Initialize the sync service.

        Args:
            git_ops: Git operations wrapper
            embedding_service: Embedding generator
            index_service: Index manager
        """
        self.git_ops = git_ops or GitOps()
        self.embedding_service = embedding_service or EmbeddingService()
        self.index_service = index_service or IndexService()

    def sync_note_to_index(
        self,
        namespace: str,
        commit_sha: str,
    ) -> bool:
        """
        Index a single note after capture.

        Args:
            namespace: Memory namespace
            commit_sha: Commit the note is attached to

        Returns:
            True if indexed successfully, False if note doesn't exist
        """
        # Get note content
        note_content = self.git_ops.show_note(namespace, commit_sha)
        if not note_content:
            return False

        try:
            metadata, body = parse_note(note_content)
        except ParseError:
            return False

        # Generate memory ID
        memory_id = extract_memory_id(namespace, commit_sha)

        # Parse timestamp (ARCH-008: use shared utility)
        timestamp = metadata.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = parse_iso_timestamp_safe(timestamp)

        # Create Memory object
        memory = Memory(
            id=memory_id,
            commit_sha=commit_sha,
            namespace=namespace,
            spec=metadata.get("spec"),
            phase=metadata.get("phase"),
            summary=metadata.get("summary", ""),
            content=body,
            tags=tuple(metadata.get("tags", [])),
            timestamp=timestamp,
            status=metadata.get("status"),
            relates_to=tuple(metadata.get("relates_to", [])),
        )

        # Generate embedding and index
        embed_text = f"{memory.summary}\n\n{body}"
        embedding = self.embedding_service.embed(embed_text)

        self.index_service.initialize()
        self.index_service.insert(memory, embedding)

        return True

    def full_reindex(
        self,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> IndexStats:
        """
        Rebuild the entire index from Git notes.

        Iterates all namespaces, parses all notes, generates embeddings,
        and populates the index from scratch.

        Args:
            progress_callback: Optional callback(current, total) for progress

        Returns:
            IndexStats after rebuild
        """
        # Initialize fresh index
        self.index_service.initialize()
        self.index_service.clear()

        total_notes = 0
        processed = 0
        errors = []

        # Count total notes first for progress
        all_notes: list[tuple[str, str, str]] = []  # (namespace, note_sha, commit_sha)
        for namespace in NAMESPACES:
            notes = self.git_ops.list_notes(namespace)
            for note_sha, commit_sha in notes:
                all_notes.append((namespace, note_sha, commit_sha))
                total_notes += 1

        # Process all notes
        for namespace, _note_sha, commit_sha in all_notes:
            try:
                success = self.sync_note_to_index(namespace, commit_sha)
                if not success:
                    errors.append(f"{namespace}:{commit_sha} - parse failed")
            except Exception as e:
                errors.append(f"{namespace}:{commit_sha} - {e}")

            processed += 1
            if progress_callback:
                progress_callback(processed, total_notes)

        return self.index_service.get_stats()

    def verify_index(self) -> VerificationResult:
        """
        Check index consistency against Git notes.

        Compares the index contents with what's in Git notes to detect:
        - Missing entries (in notes but not index)
        - Orphaned entries (in index but not notes)
        - Mismatched content

        Returns:
            VerificationResult with consistency details
        """
        # Get all memory IDs from Git notes
        notes_ids: set[str] = set()
        for namespace in NAMESPACES:
            notes = self.git_ops.list_notes(namespace)
            for _, commit_sha in notes:
                memory_id = extract_memory_id(namespace, commit_sha)
                notes_ids.add(memory_id)

        # Get all memory IDs from index using public method (ARCH-002 fix)
        index_ids = self.index_service.get_all_ids()

        # Calculate differences
        missing_in_index = notes_ids - index_ids
        orphaned_in_index = index_ids - notes_ids

        # Check for content mismatches (basic check - just verify existence for now)
        # A full content check would be expensive
        mismatched: list[str] = []

        is_consistent = (
            len(missing_in_index) == 0
            and len(orphaned_in_index) == 0
            and len(mismatched) == 0
        )

        return VerificationResult(
            is_consistent=is_consistent,
            missing_in_index=tuple(sorted(missing_in_index)),
            orphaned_in_index=tuple(sorted(orphaned_in_index)),
            mismatched=tuple(sorted(mismatched)),
        )

    def repair_index(self) -> tuple[int, int]:
        """
        Repair index inconsistencies.

        Adds missing entries and removes orphaned entries.

        Returns:
            Tuple of (added_count, removed_count)
        """
        result = self.verify_index()

        added = 0
        removed = 0

        # Add missing entries
        for memory_id in result.missing_in_index:
            parts = memory_id.split(":", 1)
            if len(parts) == 2:
                namespace, commit_sha = parts
                if self.sync_note_to_index(namespace, commit_sha):
                    added += 1

        # Remove orphaned entries
        for memory_id in result.orphaned_in_index:
            if self.index_service.delete(memory_id):
                removed += 1

        return added, removed

    def get_sync_status(self) -> dict:
        """
        Get current synchronization status.

        Returns:
            Dict with sync statistics
        """
        stats = self.index_service.get_stats()
        verification = self.verify_index()

        return {
            "total_indexed": stats.total_memories,
            "by_namespace": stats.by_namespace,
            "by_spec": stats.by_spec,
            "last_sync": stats.last_sync.isoformat() if stats.last_sync else None,
            "index_size_bytes": stats.index_size_bytes,
            "is_consistent": verification.is_consistent,
            "missing_count": len(verification.missing_in_index),
            "orphaned_count": len(verification.orphaned_in_index),
        }
