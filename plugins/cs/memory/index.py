"""
Index service for cs-memory.

Manages the SQLite database with sqlite-vec for semantic search.
The index is derived from Git notes and can be rebuilt at any time.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import EMBEDDING_DIMENSIONS, INDEX_PATH
from .exceptions import MemoryIndexError
from .models import IndexStats, Memory


class IndexService:
    """
    SQLite + sqlite-vec index manager.

    Handles all database operations including CRUD and vector search.
    The database schema uses a metadata table joined with a virtual
    sqlite-vec table for embeddings.

    Supports context manager protocol for automatic resource cleanup:

        with IndexService() as index:
            index.search_vector(embedding)
        # Connection automatically closed
    """

    def __init__(self, db_path: Path | str | None = None):
        """
        Initialize the index service.

        Args:
            db_path: Path to SQLite database. If None, uses default.
        """
        self.db_path = Path(db_path) if db_path else INDEX_PATH
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> "IndexService":
        """Enter context manager, returning self for use."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit context manager, closing connection."""
        self.close()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = self._create_connection()
        return self._conn

    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection with sqlite-vec loaded."""
        # Validate db_path is not a directory
        if self.db_path.is_dir():
            raise MemoryIndexError(
                f"Database path is a directory: {self.db_path}",
                "Pass a file path like '/path/to/.cs-memory/index.db', not a directory",
            )

        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            # Show absolute path for easier debugging
            abs_path = self.db_path.resolve()
            raise MemoryIndexError(
                f"Failed to open database: {e}",
                f"Check permissions on {abs_path} and parent directory",
            ) from e

        # Load sqlite-vec extension
        try:
            import sqlite_vec

            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
        except ImportError as err:
            raise MemoryIndexError(
                "sqlite-vec package not installed",
                "Install with: pip install sqlite-vec",
            ) from err
        except Exception as e:
            raise MemoryIndexError(
                f"Failed to load sqlite-vec extension: {e}",
                "Ensure sqlite-vec is properly installed",
            ) from e

        return conn

    def initialize(self) -> None:
        """
        Create database tables if they don't exist.

        Creates the memories metadata table and vec_memories virtual table.
        """
        conn = self._get_connection()

        try:
            conn.executescript("""
                -- Metadata table
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    commit_sha TEXT NOT NULL,
                    namespace TEXT NOT NULL,
                    spec TEXT,
                    phase TEXT,
                    summary TEXT NOT NULL,
                    full_content TEXT NOT NULL,
                    tags JSON,
                    timestamp DATETIME NOT NULL,
                    status TEXT,
                    relates_to JSON,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_memories_spec
                    ON memories(spec);
                CREATE INDEX IF NOT EXISTS idx_memories_namespace
                    ON memories(namespace);
                CREATE INDEX IF NOT EXISTS idx_memories_timestamp
                    ON memories(timestamp);
                CREATE INDEX IF NOT EXISTS idx_memories_commit
                    ON memories(commit_sha);
            """)

            # Create virtual table for vectors
            # Note: sqlite-vec uses vec0 type
            conn.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
                    embedding float[{EMBEDDING_DIMENSIONS}]
                )
            """)

            conn.commit()

        except sqlite3.Error as e:
            raise MemoryIndexError(
                f"Failed to initialize database: {e}",
                "Try deleting the database file and retrying",
            ) from e

    def insert(self, memory: Memory, embedding: list[float]) -> None:
        """
        Insert a memory with its embedding.

        Args:
            memory: Memory object to insert
            embedding: Embedding vector for the memory

        Raises:
            IndexError: If insertion fails
        """
        conn = self._get_connection()

        try:
            # Insert metadata
            conn.execute(
                """
                INSERT OR REPLACE INTO memories
                (id, commit_sha, namespace, spec, phase, summary, full_content,
                 tags, timestamp, status, relates_to)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory.id,
                    memory.commit_sha,
                    memory.namespace,
                    memory.spec,
                    memory.phase,
                    memory.summary,
                    memory.content,
                    json.dumps(list(memory.tags)) if memory.tags else None,
                    memory.timestamp.isoformat(),
                    memory.status,
                    json.dumps(list(memory.relates_to)) if memory.relates_to else None,
                ),
            )

            # Get the rowid for the metadata row
            cursor = conn.execute(
                "SELECT rowid FROM memories WHERE id = ?", (memory.id,)
            )
            row = cursor.fetchone()
            if not row:
                raise MemoryIndexError(
                    "Failed to get rowid after insert",
                    "Database may be corrupted - try reindex",
                )
            rowid = row[0]

            # Insert embedding (use same rowid)
            conn.execute(
                """
                INSERT OR REPLACE INTO vec_memories (rowid, embedding)
                VALUES (?, ?)
            """,
                (rowid, json.dumps(embedding)),
            )

            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            raise MemoryIndexError(
                f"Failed to insert memory: {e}",
                "Check database integrity and try again",
            ) from e

    def get(self, memory_id: str) -> Memory | None:
        """
        Get a memory by ID.

        Args:
            memory_id: Memory ID (format: namespace:commit_sha)

        Returns:
            Memory object or None if not found
        """
        conn = self._get_connection()

        cursor = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
        row = cursor.fetchone()

        if not row:
            return None

        return self._row_to_memory(row)

    def get_batch(self, memory_ids: list[str]) -> dict[str, Memory]:
        """
        Batch retrieve memories by IDs.

        This avoids N+1 query patterns when loading multiple memories.

        Args:
            memory_ids: List of memory IDs to retrieve

        Returns:
            Dictionary mapping memory_id to Memory object
        """
        if not memory_ids:
            return {}

        conn = self._get_connection()
        placeholders = ",".join("?" * len(memory_ids))
        cursor = conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",  # nosec B608
            memory_ids,
        )
        return {row["id"]: self._row_to_memory(row) for row in cursor}

    def get_by_spec(self, spec: str) -> dict[str, list[Memory]]:
        """
        Get all memories for a specification, grouped by namespace.

        This is an optimized method that avoids N+1 queries and
        repeated embedding generation for full context loading.

        Args:
            spec: Specification slug to filter by

        Returns:
            Dictionary mapping namespace to list of Memory objects
        """
        conn = self._get_connection()

        cursor = conn.execute(
            "SELECT * FROM memories WHERE spec = ? ORDER BY timestamp",
            (spec,),
        )

        result: dict[str, list[Memory]] = {}
        for row in cursor:
            memory = self._row_to_memory(row)
            if memory.namespace not in result:
                result[memory.namespace] = []
            result[memory.namespace].append(memory)

        return result

    def delete(self, memory_id: str) -> bool:
        """
        Delete a memory by ID.

        Args:
            memory_id: Memory ID to delete

        Returns:
            True if deleted, False if not found
        """
        conn = self._get_connection()

        try:
            # Get rowid first
            cursor = conn.execute(
                "SELECT rowid FROM memories WHERE id = ?", (memory_id,)
            )
            row = cursor.fetchone()
            if not row:
                return False

            rowid = row[0]

            # Delete from both tables
            conn.execute("DELETE FROM vec_memories WHERE rowid = ?", (rowid,))
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()

            return True

        except sqlite3.Error as e:
            conn.rollback()
            raise MemoryIndexError(
                f"Failed to delete memory: {e}", "Check database integrity"
            ) from e

    def update(self, memory: Memory) -> None:
        """
        Update an existing memory's metadata.

        Note: Does not update embedding. Use delete + insert for that.

        Args:
            memory: Memory object with updated values
        """
        conn = self._get_connection()

        try:
            conn.execute(
                """
                UPDATE memories SET
                    spec = ?,
                    phase = ?,
                    summary = ?,
                    full_content = ?,
                    tags = ?,
                    timestamp = ?,
                    status = ?,
                    relates_to = ?
                WHERE id = ?
            """,
                (
                    memory.spec,
                    memory.phase,
                    memory.summary,
                    memory.content,
                    json.dumps(list(memory.tags)) if memory.tags else None,
                    memory.timestamp.isoformat(),
                    memory.status,
                    json.dumps(list(memory.relates_to)) if memory.relates_to else None,
                    memory.id,
                ),
            )
            conn.commit()

        except sqlite3.Error as e:
            conn.rollback()
            raise MemoryIndexError(
                f"Failed to update memory: {e}", "Check database integrity"
            ) from e

    def search_vector(
        self,
        embedding: list[float],
        filters: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[tuple[str, float]]:
        """
        Perform KNN search over memories.

        Args:
            embedding: Query embedding vector
            filters: Optional filters (spec, namespace, since, until)
            limit: Maximum results to return

        Returns:
            List of (memory_id, distance) tuples, sorted by distance
        """
        conn = self._get_connection()

        # Build filter clauses
        where_clauses = []
        params: list[Any] = []

        if filters:
            if "spec" in filters and filters["spec"]:
                where_clauses.append("m.spec = ?")
                params.append(filters["spec"])

            if "namespace" in filters and filters["namespace"]:
                where_clauses.append("m.namespace = ?")
                params.append(filters["namespace"])

            if "since" in filters and filters["since"]:
                where_clauses.append("m.timestamp >= ?")
                params.append(filters["since"].isoformat())

            if "until" in filters and filters["until"]:
                where_clauses.append("m.timestamp <= ?")
                params.append(filters["until"].isoformat())

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # Query with vector search
        # sqlite-vec requires 'k = ?' in the vec0 WHERE clause for KNN queries
        # We do a subquery to get KNN results, then filter with metadata
        # nosec B608 - where_sql uses parameterized values (all ? placeholders)
        query = f"""
            SELECT m.id, v.distance
            FROM vec_memories v
            JOIN memories m ON m.rowid = v.rowid
            WHERE v.embedding MATCH ?
              AND k = ?
              AND {where_sql}
            ORDER BY v.distance
        """  # nosec

        # k and embedding params go first for vec0
        params = [json.dumps(embedding), limit] + params

        try:
            cursor = conn.execute(query, params)
            return [(row["id"], row["distance"]) for row in cursor]
        except sqlite3.Error as e:
            raise MemoryIndexError(
                f"Vector search failed: {e}",
                "Try rebuilding the index with /cs:memory reindex",
            ) from e

    def get_stats(self) -> IndexStats:
        """
        Get statistics about the index.

        Returns:
            IndexStats with counts and sizes
        """
        conn = self._get_connection()

        # Total count
        cursor = conn.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        # By namespace
        cursor = conn.execute("""
            SELECT namespace, COUNT(*) as cnt
            FROM memories
            GROUP BY namespace
        """)
        by_namespace = {row["namespace"]: row["cnt"] for row in cursor}

        # By spec
        cursor = conn.execute("""
            SELECT spec, COUNT(*) as cnt
            FROM memories
            WHERE spec IS NOT NULL
            GROUP BY spec
        """)
        by_spec = {row["spec"]: row["cnt"] for row in cursor}

        # Last sync time (newest memory)
        cursor = conn.execute("""
            SELECT MAX(created_at) as last_sync FROM memories
        """)
        row = cursor.fetchone()
        last_sync = None
        if row and row["last_sync"]:
            last_sync = datetime.fromisoformat(row["last_sync"])

        # Database file size
        try:
            size = self.db_path.stat().st_size
        except OSError:
            size = 0

        return IndexStats(
            total_memories=total,
            by_namespace=by_namespace,
            by_spec=by_spec,
            last_sync=last_sync,
            index_size_bytes=size,
        )

    def clear(self) -> None:
        """Clear all data from the index."""
        conn = self._get_connection()

        try:
            conn.execute("DELETE FROM vec_memories")
            conn.execute("DELETE FROM memories")
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            raise MemoryIndexError(
                f"Failed to clear index: {e}", "Try deleting the database file manually"
            ) from e

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def list_recent(
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
        conn = self._get_connection()

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
        return [self._row_to_memory(row) for row in cursor]

    def get_by_commit(self, commit_sha: str) -> list[Memory]:
        """
        Get all memories attached to a specific commit.

        Args:
            commit_sha: Git commit SHA

        Returns:
            List of memories attached to that commit
        """
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM memories WHERE commit_sha = ?", (commit_sha,)
        )
        return [self._row_to_memory(row) for row in cursor]

    def get_all_ids(self) -> set[str]:
        """
        Get all memory IDs in the index.

        Returns:
            Set of all memory IDs
        """
        conn = self._get_connection()
        cursor = conn.execute("SELECT id FROM memories")
        return {row["id"] for row in cursor}

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a database row to a Memory object."""
        tags = ()
        if row["tags"]:
            tags = tuple(json.loads(row["tags"]))

        relates_to = ()
        if row["relates_to"]:
            relates_to = tuple(json.loads(row["relates_to"]))

        timestamp = row["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        return Memory(
            id=row["id"],
            commit_sha=row["commit_sha"],
            namespace=row["namespace"],
            spec=row["spec"],
            phase=row["phase"],
            summary=row["summary"],
            content=row["full_content"],
            tags=tags,
            timestamp=timestamp,
            status=row["status"],
            relates_to=relates_to,
        )
