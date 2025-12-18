"""
Capture service for cs-memory.

Orchestrates the memory capture flow: format -> git notes -> embed -> index.
Includes concurrency safety via file locking per FR-022.
"""

import fcntl
import os
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import (
    AUTO_CAPTURE_DEFAULT,
    AUTO_CAPTURE_ENV_VAR,
    AUTO_CAPTURE_NAMESPACES,
    LOCK_FILE,
    MAX_CONTENT_LENGTH,
    NAMESPACES,
    PATTERN_TYPES,
    RETROSPECTIVE_OUTCOMES,
    REVIEW_CATEGORIES,
    REVIEW_SEVERITIES,
)
from .embedding import EmbeddingService
from .exceptions import CaptureError
from .git_ops import GitOps
from .index import IndexService
from .models import CaptureResult, Memory
from .note_parser import extract_memory_id, format_note


@contextmanager
def capture_lock(lock_path: Path = LOCK_FILE) -> Generator[None, None, None]:
    """
    Acquire exclusive lock for capture operations (FR-022).

    SEC-004: Uses proper context manager pattern to prevent file descriptor leaks.

    Args:
        lock_path: Path to lock file

    Yields:
        Nothing - context manager for lock lifetime

    Raises:
        CaptureError: If lock cannot be acquired
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # SEC-004: Use context manager to ensure file is always closed
    with open(lock_path, "w") as lock_fd:
        try:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError as err:
            raise CaptureError(
                "Another capture operation is in progress",
                f"Wait and retry, or remove {lock_path} if stuck",
            ) from err
        finally:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


def validate_auto_capture_namespace(namespace: str) -> bool:
    """
    Check if namespace is valid and enabled for auto-capture.

    Args:
        namespace: The namespace to validate

    Returns:
        True if namespace is enabled for auto-capture

    Raises:
        CaptureError: If namespace is not a valid NAMESPACES value
    """
    if namespace not in NAMESPACES:
        raise CaptureError(
            f"Invalid namespace: {namespace}",
            f"Use one of: {', '.join(sorted(NAMESPACES))}",
        )
    return namespace in AUTO_CAPTURE_NAMESPACES


def is_auto_capture_enabled() -> bool:
    """
    Check if auto-capture is enabled via environment variable.

    Auto-capture can be disabled by setting CS_AUTO_CAPTURE_ENABLED=false.
    Default is enabled (true) if not set.

    Returns:
        True if auto-capture is enabled
    """
    env_value = os.environ.get(AUTO_CAPTURE_ENV_VAR, "").lower()
    if not env_value:
        return AUTO_CAPTURE_DEFAULT
    return env_value in ("true", "1", "yes", "on")


class CaptureService:
    """
    Orchestrates memory capture operations.

    Handles the full capture flow with concurrency safety:
    1. Auto-configure git notes sync (first use only)
    2. Acquire capture lock
    3. Format note with YAML front matter
    4. Attach note to commit via git notes append
    5. Generate embedding
    6. Index in SQLite
    7. Release lock
    """

    # Class-level flag to track if git sync has been configured this session
    _sync_configured: bool = False

    def __init__(
        self,
        git_ops: GitOps | None = None,
        embedding_service: EmbeddingService | None = None,
        index_service: IndexService | None = None,
    ):
        """
        Initialize the capture service.

        Args:
            git_ops: Git operations wrapper (created if None)
            embedding_service: Embedding generator (created if None)
            index_service: Index manager (created if None)
        """
        self.git_ops = git_ops or GitOps()
        self.embedding_service = embedding_service or EmbeddingService()
        self.index_service = index_service or IndexService()

    def _ensure_sync_configured(self) -> None:
        """
        Ensure git notes sync is configured (auto-configure on first use).

        This is idempotent - safe to call multiple times. Only actually
        configures git on first capture, then skips on subsequent calls.
        """
        if CaptureService._sync_configured:
            return

        # Auto-configure git notes sync (push, fetch, rewriteRef, merge)
        # This is idempotent - won't duplicate if already configured
        self.git_ops.configure_sync()
        CaptureService._sync_configured = True

    @classmethod
    def reset_sync_configured(cls) -> None:
        """Reset the sync configuration flag (for testing)."""
        cls._sync_configured = False

    def capture(
        self,
        namespace: str,
        summary: str,
        content: str,
        spec: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
        phase: str | None = None,
        status: str | None = None,
    ) -> CaptureResult:
        """
        Capture a memory as a Git note.

        Args:
            namespace: Memory type (decisions, learnings, blockers, etc.)
            summary: One-line summary (max 100 chars)
            content: Full markdown body
            spec: Specification slug
            commit: Commit to attach note to (default: HEAD)
            tags: Categorization tags
            phase: Lifecycle phase
            status: For blockers/reviews - open/resolved

        Returns:
            CaptureResult with success status and captured memory

        Raises:
            CaptureError: If capture fails
            StorageError: If git operations fail
        """
        # Auto-configure git notes sync on first capture
        self._ensure_sync_configured()

        if namespace not in NAMESPACES:
            raise CaptureError(
                f"Invalid namespace: {namespace}",
                f"Use one of: {', '.join(sorted(NAMESPACES))}",
            )

        # SEC-005: Validate content length to prevent resource exhaustion
        if len(content) > MAX_CONTENT_LENGTH:
            raise CaptureError(
                f"Content too long: {len(content)} bytes exceeds {MAX_CONTENT_LENGTH} limit",
                "Reduce content size or split into multiple captures",
            )

        timestamp = datetime.now(UTC)

        # Build metadata
        metadata = {
            "type": namespace,
            "spec": spec,
            "timestamp": timestamp,
            "summary": summary,
        }
        if phase:
            metadata["phase"] = phase
        if tags:
            metadata["tags"] = tags
        if status:
            metadata["status"] = status

        # Format the note
        note_content = format_note(metadata, content)

        # Get the actual commit SHA
        commit_sha = self.git_ops.get_commit_sha(commit)

        with capture_lock():
            # Append note to git (safe for concurrent operations)
            self.git_ops.append_note(namespace, note_content, commit_sha)

            # Generate memory ID (include timestamp for uniqueness)
            memory_id = extract_memory_id(namespace, commit_sha, timestamp)

            # Create Memory object
            memory = Memory(
                id=memory_id,
                commit_sha=commit_sha,
                namespace=namespace,
                spec=spec,
                phase=phase,
                summary=summary,
                content=content,
                tags=tuple(tags) if tags else (),
                timestamp=timestamp,
                status=status,
            )

            # Try to index (graceful degradation on failure)
            indexed = False
            warning = None

            try:
                # Embed the summary + content for semantic search
                embed_text = f"{summary}\n\n{content}"
                embedding = self.embedding_service.embed(embed_text)

                # Initialize index if needed and insert
                self.index_service.initialize()
                self.index_service.insert(memory, embedding)
                indexed = True

            except Exception as e:
                # Graceful degradation - note is saved, just not indexed
                warning = f"Embedding/indexing failed: {e}. Memory saved to git notes."

        return CaptureResult(
            success=True,
            memory=memory,
            indexed=indexed,
            warning=warning,
        )

    def capture_decision(
        self,
        spec: str,
        summary: str,
        context: str,
        rationale: str,
        alternatives: list[str] | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture an Architecture Decision Record.

        Args:
            spec: Specification slug
            summary: One-line summary of the decision
            context: Problem/background
            rationale: Why this decision was made
            alternatives: Other options considered
            commit: Commit to attach to
            tags: Additional tags

        Returns:
            CaptureResult
        """
        # Build ADR body
        body_parts = ["## Context", context, "", "## Decision", rationale]

        if alternatives:
            body_parts.extend(["", "## Alternatives Considered"])
            for alt in alternatives:
                body_parts.append(f"- {alt}")

        content = "\n".join(body_parts)

        return self.capture(
            namespace="decisions",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=tags,
            phase="architecture",
        )

    def capture_blocker(
        self,
        spec: str,
        summary: str,
        problem: str,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture an unresolved blocker.

        Args:
            spec: Specification slug
            summary: One-line blocker description
            problem: Full problem description
            commit: Commit to attach to
            tags: Additional tags

        Returns:
            CaptureResult
        """
        content = f"## Problem\n{problem}"

        return self.capture(
            namespace="blockers",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=tags,
            phase="implementation",
            status="unresolved",
        )

    def resolve_blocker(
        self,
        memory_id: str,
        resolution: str,
    ) -> CaptureResult:
        """
        Update a blocker with its resolution.

        Appends resolution to the existing note and updates status.

        Args:
            memory_id: ID of the blocker memory
            resolution: How the blocker was resolved

        Returns:
            CaptureResult with updated memory
        """
        # Get existing memory
        existing = self.index_service.get(memory_id)
        if not existing:
            raise CaptureError(
                f"Blocker not found: {memory_id}",
                "Check memory ID or run /memory reindex",
            )

        if existing.namespace != "blockers":
            raise CaptureError(
                f"Memory is not a blocker: {memory_id}",
                "Can only resolve memories in blockers namespace",
            )

        # Append resolution to the note
        resolution_content = f"\n\n## Resolution\n{resolution}"
        self.git_ops.append_note(
            "blockers",
            resolution_content,
            existing.commit_sha,
        )

        # Update in index
        updated_memory = Memory(
            id=existing.id,
            commit_sha=existing.commit_sha,
            namespace=existing.namespace,
            spec=existing.spec,
            phase=existing.phase,
            summary=existing.summary,
            content=existing.content + resolution_content,
            tags=existing.tags,
            timestamp=existing.timestamp,
            status="resolved",
            relates_to=existing.relates_to,
        )

        self.index_service.update(updated_memory)

        return CaptureResult(
            success=True,
            memory=updated_memory,
            indexed=True,
        )

    def capture_learning(
        self,
        spec: str | None,
        summary: str,
        insight: str,
        applicability: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture a technical learning/insight.

        Args:
            spec: Specification slug (None for global learnings)
            summary: One-line summary
            insight: The learning/insight
            applicability: When/where this applies
            commit: Commit to attach to
            tags: Additional tags

        Returns:
            CaptureResult
        """
        body_parts = ["## Insight", insight]

        if applicability:
            body_parts.extend(["", "## Applicability", applicability])

        content = "\n".join(body_parts)

        return self.capture(
            namespace="learnings",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=tags,
        )

    def capture_progress(
        self,
        spec: str,
        summary: str,
        task_id: str | None = None,
        details: str | None = None,
        commit: str = "HEAD",
    ) -> CaptureResult:
        """
        Capture task completion progress.

        Args:
            spec: Specification slug
            summary: One-line progress summary
            task_id: Task identifier if applicable
            details: Additional details
            commit: Commit to attach to

        Returns:
            CaptureResult
        """
        body_parts = []
        if task_id:
            body_parts.append(f"**Task ID**: {task_id}")
        if details:
            body_parts.extend(["", details])

        content = "\n".join(body_parts) if body_parts else summary

        return self.capture(
            namespace="progress",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            phase="implementation",
        )

    def capture_retrospective(
        self,
        spec: str,
        summary: str,
        outcome: str,
        what_went_well: list[str],
        what_to_improve: list[str],
        key_learnings: list[str],
        recommendations: list[str] | None = None,
        metrics: dict[str, Any] | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture a project retrospective summary.

        Called during /c close-out to preserve project learnings.

        Args:
            spec: Specification slug (required for retrospectives)
            summary: One-line summary (e.g., "Retrospective: project-name")
            outcome: Project outcome (success, partial, failed, abandoned)
            what_went_well: List of things that went well
            what_to_improve: List of things to improve
            key_learnings: List of key learnings
            recommendations: List of recommendations for future projects (optional)
            metrics: Dict of metrics (duration, effort, scope variance) (optional)
            commit: Commit to attach note to
            tags: Additional tags

        Returns:
            CaptureResult

        Raises:
            CaptureError: If outcome is invalid
        """
        if outcome not in RETROSPECTIVE_OUTCOMES:
            raise CaptureError(
                f"Invalid retrospective outcome: {outcome}",
                f"Use one of: {', '.join(sorted(RETROSPECTIVE_OUTCOMES))}",
            )

        # Build structured content
        body_parts = [
            "## Outcome",
            outcome,
            "",
            "## What Went Well",
        ]
        for item in what_went_well:
            body_parts.append(f"- {item}")

        body_parts.extend(["", "## What Could Be Improved"])
        for item in what_to_improve:
            body_parts.append(f"- {item}")

        body_parts.extend(["", "## Key Learnings"])
        for item in key_learnings:
            body_parts.append(f"- {item}")

        if recommendations:
            body_parts.extend(["", "## Recommendations"])
            for item in recommendations:
                body_parts.append(f"- {item}")

        if metrics:
            body_parts.extend(["", "## Metrics"])
            for key, value in metrics.items():
                body_parts.append(f"- **{key}**: {value}")

        content = "\n".join(body_parts)

        # Build tags
        all_tags = ["retrospective", outcome]
        if tags:
            all_tags.extend(tags)

        return self.capture(
            namespace="retrospective",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=all_tags,
            phase="close-out",
        )

    def capture_pattern(
        self,
        spec: str | None,
        summary: str,
        pattern_type: str,
        description: str,
        context: str,
        applicability: str,
        evidence: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture a reusable pattern or anti-pattern.

        Patterns are cross-spec generalizations extracted from retrospectives
        and deviations encountered during implementation.

        Args:
            spec: Specification slug (None for global patterns)
            summary: One-line summary of the pattern
            pattern_type: Type of pattern (success, anti-pattern, deviation)
            description: What the pattern is
            context: When/why this pattern applies
            applicability: Where/when to apply this pattern
            evidence: Evidence supporting the pattern (optional)
            commit: Commit to attach note to
            tags: Additional tags

        Returns:
            CaptureResult

        Raises:
            CaptureError: If pattern_type is invalid
        """
        if pattern_type not in PATTERN_TYPES:
            raise CaptureError(
                f"Invalid pattern type: {pattern_type}",
                f"Use one of: {', '.join(sorted(PATTERN_TYPES))}",
            )

        # Build structured content
        body_parts = [
            "## Pattern Type",
            pattern_type,
            "",
            "## Description",
            description,
            "",
            "## Context",
            context,
            "",
            "## Applicability",
            applicability,
        ]

        if evidence:
            body_parts.extend(["", "## Evidence", evidence])

        content = "\n".join(body_parts)

        # Build tags
        all_tags = ["pattern", pattern_type]
        if tags:
            all_tags.extend(tags)

        return self.capture(
            namespace="patterns",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=all_tags,
        )

    def capture_review(
        self,
        spec: str | None,
        summary: str,
        category: str,
        severity: str,
        file_path: str,
        line: int,
        description: str,
        suggested_fix: str | None = None,
        impact: str | None = None,
        commit: str = "HEAD",
        tags: list[str] | None = None,
    ) -> CaptureResult:
        """
        Capture a code review finding.

        Args:
            spec: Specification slug (None for global findings)
            summary: One-line summary of the finding
            category: Finding category (security, performance, architecture, quality, tests, documentation)
            severity: Finding severity (critical, high, medium, low)
            file_path: File path where the issue was found
            line: Line number in the file
            description: Detailed description of the finding
            suggested_fix: How to fix the issue (optional)
            impact: Impact of the issue (optional)
            commit: Commit to attach note to
            tags: Additional tags

        Returns:
            CaptureResult

        Raises:
            CaptureError: If category or severity is invalid
        """
        if category not in REVIEW_CATEGORIES:
            raise CaptureError(
                f"Invalid review category: {category}",
                f"Use one of: {', '.join(sorted(REVIEW_CATEGORIES))}",
            )

        if severity not in REVIEW_SEVERITIES:
            raise CaptureError(
                f"Invalid review severity: {severity}",
                f"Use one of: {', '.join(sorted(REVIEW_SEVERITIES))}",
            )

        # Build structured content
        body_parts = [
            "## Category",
            category,
            "",
            "## Severity",
            severity,
            "",
            "## Location",
            f"{file_path}:{line}",
            "",
            "## Description",
            description,
        ]

        if impact:
            body_parts.extend(["", "## Impact", impact])

        if suggested_fix:
            body_parts.extend(["", "## Suggested Fix", suggested_fix])

        content = "\n".join(body_parts)

        # Build tags
        all_tags = [category, severity, "code-review"]
        if tags:
            all_tags.extend(tags)

        return self.capture(
            namespace="reviews",
            summary=summary,
            content=content,
            spec=spec,
            commit=commit,
            tags=all_tags,
            status="open",
        )
