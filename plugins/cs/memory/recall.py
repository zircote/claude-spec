"""
Recall service for cs-memory.

Orchestrates memory retrieval operations including semantic search,
progressive hydration, and context loading.
"""

from datetime import datetime
from typing import Any

from .config import DEFAULT_RECALL_LIMIT, MAX_RECALL_LIMIT
from .embedding import EmbeddingService
from .git_ops import GitOps
from .index import IndexService
from .models import HydratedMemory, HydrationLevel, Memory, MemoryResult, SpecContext


class RecallService:
    """
    Orchestrates memory retrieval operations.

    Provides semantic search over memories with progressive hydration
    for controlling how much detail is loaded.
    """

    def __init__(
        self,
        git_ops: GitOps | None = None,
        embedding_service: EmbeddingService | None = None,
        index_service: IndexService | None = None,
    ):
        """
        Initialize the recall service.

        Args:
            git_ops: Git operations wrapper (created if None)
            embedding_service: Embedding generator (created if None)
            index_service: Index manager (created if None)
        """
        self.git_ops = git_ops or GitOps()
        self.embedding_service = embedding_service or EmbeddingService()
        self.index_service = index_service or IndexService()

    def search(
        self,
        query: str,
        spec: str | None = None,
        namespace: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int = DEFAULT_RECALL_LIMIT,
    ) -> list[MemoryResult]:
        """
        Perform semantic search over memories.

        Args:
            query: Natural language search query
            spec: Filter to specific specification
            namespace: Filter to memory type
            since: Only memories after this time
            until: Only memories before this time
            limit: Maximum results (capped at MAX_RECALL_LIMIT)

        Returns:
            List of MemoryResult sorted by relevance (distance)
        """
        # Cap limit
        limit = min(limit, MAX_RECALL_LIMIT)

        # Generate query embedding
        query_embedding = self.embedding_service.embed(query)

        # Build filters
        filters: dict[str, Any] = {}
        if spec:
            filters["spec"] = spec
        if namespace:
            filters["namespace"] = namespace
        if since:
            filters["since"] = since
        if until:
            filters["until"] = until

        # Execute vector search
        results = self.index_service.search_vector(
            query_embedding,
            filters=filters,
            limit=limit,
        )

        # Hydrate results to Level 1 (summary)
        memory_results = []
        for memory_id, distance in results:
            memory = self.index_service.get(memory_id)
            if memory:
                memory_results.append(
                    MemoryResult(
                        memory=memory,
                        distance=distance,
                    )
                )

        return memory_results

    def hydrate(
        self,
        result: MemoryResult,
        level: HydrationLevel,
    ) -> HydratedMemory:
        """
        Progressive hydration of a memory.

        Level 1 (SUMMARY): Just the summary (already in MemoryResult)
        Level 2 (FULL): Complete note content from git notes show
        Level 3 (FILES): Full content plus file snapshots from commit

        Args:
            result: Memory search result
            level: Desired hydration level

        Returns:
            HydratedMemory with requested detail level
        """
        memory = result.memory

        # Base hydration (Level 1)
        hydrated = HydratedMemory(result=result)

        if level.value >= HydrationLevel.FULL.value:
            # Level 2: Get full note content from git
            note_content = self.git_ops.show_note(
                memory.namespace,
                memory.commit_sha,
            )
            hydrated = HydratedMemory(
                result=result,
                full_content=note_content,
            )

        if level.value >= HydrationLevel.FILES.value:
            # Level 3: Get file snapshots from commit
            commit_info = self.git_ops.get_commit_info(memory.commit_sha)
            changed_files = self.git_ops.get_changed_files(memory.commit_sha)

            files = {}
            for file_path in changed_files:
                content = self.git_ops.get_file_at_commit(
                    file_path,
                    memory.commit_sha,
                )
                if content:
                    files[file_path] = content

            hydrated = HydratedMemory(
                result=result,
                full_content=hydrated.full_content,
                files=files,
                commit_info=commit_info,
            )

        return hydrated

    def context(self, spec: str) -> SpecContext:
        """
        Load all memories for a specification.

        Retrieves all memories across namespaces for the given spec,
        organized chronologically and grouped by namespace.

        Args:
            spec: Specification slug

        Returns:
            SpecContext with all memories
        """
        # Get all memories for spec (no semantic search, just filter)
        # We need to query each namespace since we can't do a full table scan
        # efficiently with vector tables

        from .config import NAMESPACES

        all_memories: dict[str, list[Memory]] = {}
        total_count = 0
        total_content_length = 0

        for namespace in NAMESPACES:
            # Search with empty query but spec filter
            # This is a bit of a hack - we use a generic query
            # In production, we might want a separate method for filtered listing
            results = self.search(
                query=spec,  # Use spec name as query for now
                spec=spec,
                namespace=namespace,
                limit=MAX_RECALL_LIMIT,
            )

            memories = [r.memory for r in results]
            if memories:
                # Sort by timestamp
                memories.sort(key=lambda m: m.timestamp)
                all_memories[namespace] = memories
                total_count += len(memories)
                total_content_length += sum(
                    len(m.summary) + len(m.content) for m in memories
                )

        # Rough token estimate (4 chars per token)
        token_estimate = total_content_length // 4

        return SpecContext(
            spec=spec,
            memories=all_memories,
            total_count=total_count,
            token_estimate=token_estimate,
        )

    def recent(
        self,
        spec: str | None = None,
        namespace: str | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        """
        Get the most recent memories.

        Args:
            spec: Filter to specification
            namespace: Filter to namespace
            limit: Maximum results

        Returns:
            List of Memory objects, most recent first
        """
        # This is a convenience method that doesn't use semantic search
        # It queries the index directly for recent entries

        conn = self.index_service._get_connection()

        query = "SELECT * FROM memories WHERE 1=1"
        params: list[Any] = []

        if spec:
            query += " AND spec = ?"
            params.append(spec)
        if namespace:
            query += " AND namespace = ?"
            params.append(namespace)

        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        return [self.index_service._row_to_memory(row) for row in cursor]

    def similar(
        self,
        memory: Memory,
        limit: int = 5,
    ) -> list[MemoryResult]:
        """
        Find memories similar to a given memory.

        Args:
            memory: Memory to find similar to
            limit: Maximum results

        Returns:
            List of similar memories (excluding the input memory)
        """
        # Search using the memory's summary + content
        query = f"{memory.summary}\n\n{memory.content}"
        results = self.search(query, limit=limit + 1)

        # Filter out the input memory itself
        return [r for r in results if r.memory.id != memory.id][:limit]

    def by_commit(self, commit_sha: str) -> list[Memory]:
        """
        Get all memories attached to a specific commit.

        Args:
            commit_sha: Git commit SHA

        Returns:
            List of memories attached to that commit
        """
        conn = self.index_service._get_connection()

        cursor = conn.execute(
            "SELECT * FROM memories WHERE commit_sha = ?", (commit_sha,)
        )

        return [self.index_service._row_to_memory(row) for row in cursor]
