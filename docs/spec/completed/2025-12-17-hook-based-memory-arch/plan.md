# Git-Native Memory Architecture Implementation Plan

## Project Context

This specification defines the implementation of a Git-Native Memory Architecture for `claude-spec`, integrating persistent, semantically-searchable memory across AI-assisted development sessions. The architecture leverages Git notes as the canonical storage layer and SQLite-vec for semantic retrieval, following the principle: **"If a memory has no commit, it had no effect."**

## Related Resources

- **Research Paper**: "Beyond Ephemeral Context: A Git-Native Memory Architecture for AI-Assisted Development"
- **Core Repository**: https://github.com/zircote/claude-spec
- **Git-ADR Reference**: https://github.com/zircote/git-adr (git notes patterns)
- **Benchmark Harness**: https://github.com/zircote/claude-spec-benchmark

---

## Phase 1: Core Memory Infrastructure

### 1.1 Memory Storage Layer (Git Notes)

Create a Python module `plugins/cs/memory/storage.py` that manages Git notes for memory persistence.

**Namespace Schema:**

| Namespace | Ref Path | Purpose |
|-----------|----------|---------|
| `cs/inception` | `refs/notes/cs/inception` | Problem statements, scope, success criteria |
| `cs/elicitation` | `refs/notes/cs/elicitation` | Requirements clarifications, constraints |
| `cs/research` | `refs/notes/cs/research` | Technology evaluations, codebase analysis |
| `cs/decisions` | `refs/notes/cs/decisions` | ADRs: context, options, rationale |
| `cs/progress` | `refs/notes/cs/progress` | Task completions, milestones |
| `cs/blockers` | `refs/notes/cs/blockers` | Obstacles and resolutions |
| `cs/learnings` | `refs/notes/cs/learnings` | Technical insights, patterns |
| `cs/patterns` | `refs/notes/cs/patterns` | Cross-project reusable patterns |

**Note Schema (YAML Front Matter + Markdown):**

```yaml
---
type: decision|learning|blocker|research|...
spec: <project-slug>
phase: planning|implementation|review|close-out
timestamp: <ISO8601>
tags: [tag1, tag2]
summary: <one-line summary for index>
commit: <commit-sha>
---

## Context
<detailed context>

## Content
<memory content>
```

**Implementation Requirements:**

```python
# plugins/cs/memory/storage.py
from dataclasses import dataclass
from typing import Literal
import subprocess
import yaml

MemoryType = Literal[
    "inception", "elicitation", "research", "decision",
    "progress", "blocker", "learning", "pattern"
]

@dataclass
class Memory:
    type: MemoryType
    spec: str
    phase: str
    timestamp: str
    tags: list[str]
    summary: str
    commit: str
    content: str

class GitNotesStorage:
    """Canonical storage layer using git notes."""
    
    NAMESPACE_PREFIX = "refs/notes/cs"
    
    def add_memory(self, memory: Memory) -> str:
        """Add a memory as a git note attached to a commit."""
        ...
    
    def get_memory(self, commit_sha: str, namespace: MemoryType) -> Memory | None:
        """Retrieve a memory by commit and namespace."""
        ...
    
    def list_memories(
        self,
        namespace: MemoryType | None = None,
        spec: str | None = None,
        since: str | None = None
    ) -> list[Memory]:
        """List memories with optional filters."""
        ...
    
    def configure_remote_sync(self) -> None:
        """Configure push/fetch refspecs for memory sync."""
        # git config --add remote.origin.push "refs/notes/cs/*:refs/notes/cs/*"
        # git config --add remote.origin.fetch "refs/notes/cs/*:refs/notes/cs/*"
        ...
```

### 1.2 Memory Index Layer (SQLite-vec)

Create `plugins/cs/memory/index.py` for semantic retrieval.

**Database Schema:**

```sql
-- memories table for metadata
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
    UNIQUE(commit_sha, namespace)
);

CREATE INDEX idx_memories_spec ON memories(spec);
CREATE INDEX idx_memories_namespace ON memories(namespace);
CREATE INDEX idx_memories_timestamp ON memories(timestamp DESC);

-- vector embeddings for semantic search
CREATE VIRTUAL TABLE IF NOT EXISTS vec_memories USING vec0(
    id TEXT PRIMARY KEY,
    embedding FLOAT[384]
);
```

**Implementation Requirements:**

```python
# plugins/cs/memory/index.py
import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer

class MemoryIndex:
    """Semantic retrieval layer with sqlite-vec."""
    
    INDEX_PATH = ".cs-memory/index.db"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    
    def __init__(self):
        self.db = self._init_db()
        self.encoder = SentenceTransformer(self.EMBEDDING_MODEL)
    
    def index_memory(self, memory: Memory) -> None:
        """Index a memory with embedding."""
        ...
    
    def search(
        self,
        query: str,
        namespace: str | None = None,
        spec: str | None = None,
        limit: int = 10
    ) -> list[tuple[Memory, float]]:
        """Semantic search returning (memory, similarity_score) tuples."""
        ...
    
    def rebuild_from_notes(self, storage: GitNotesStorage) -> int:
        """Rebuild index from canonical git notes. Returns count."""
        ...
```

### 1.3 Progressive Hydration

Implement three-level hydration for context budget management:

```python
# plugins/cs/memory/hydration.py
from enum import Enum

class HydrationLevel(Enum):
    INDEX = 1      # commit SHA + one-line summary only
    MESSAGE = 2    # full note content (YAML header + body)
    FILES = 3      # + file snapshots from associated commit

@dataclass
class HydratedMemory:
    memory: Memory
    level: HydrationLevel
    files: dict[str, str] | None = None  # path -> content

def hydrate(
    memory: Memory,
    level: HydrationLevel = HydrationLevel.MESSAGE
) -> HydratedMemory:
    """Progressively hydrate memory to requested level."""
    ...
```

---

## Phase 2: Hook Integration

### 2.1 SessionStart Hook - Context Injection

Create `plugins/cs/hooks/session_start.py` to inject relevant memories at session start.

**Trigger:** Every new Claude Code session in a repository with `.cs-memory/`.

**Behavior:**
1. Detect active specification (from `docs/spec/active/`)
2. Query index for relevant memories (decisions, blockers, learnings)
3. Return `additionalContext` with memory summary

```python
#!/usr/bin/env python3
"""SessionStart hook for memory injection."""

import json
import sys
from memory.index import MemoryIndex
from memory.hydration import HydrationLevel

def main():
    hook_data = json.loads(sys.stdin.read())
    cwd = hook_data.get("cwd", ".")
    
    index = MemoryIndex()
    active_spec = detect_active_spec(cwd)
    
    if not active_spec:
        # No active spec, provide recent cross-project patterns
        memories = index.search(
            query="recent patterns and learnings",
            namespace="patterns",
            limit=5
        )
    else:
        # Active spec: inject relevant context
        memories = index.search(
            query=f"decisions blockers learnings for {active_spec}",
            spec=active_spec,
            limit=10
        )
    
    if not memories:
        sys.exit(0)
    
    context = format_memory_context(memories, HydrationLevel.INDEX)
    
    print(json.dumps({
        "additionalContext": f"""
## Project Memory Context

The following memories from previous sessions are relevant:

{context}

Use `/cs:recall <query>` to retrieve more detailed memories.
"""
    }))

if __name__ == "__main__":
    main()
```

**Hook Registration (hooks/hooks.json):**

```json
{
  "hooks": [
    {
      "event": "SessionStart",
      "command": ["python3", "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"],
      "timeout": 5000
    }
  ]
}
```

### 2.2 UserPromptSubmit Hook - Context Enrichment & Capture

Create `plugins/cs/hooks/prompt_submit.py` for bi-directional memory flow.

**Behavior:**
1. Analyze user prompt for memory-related keywords
2. Query index for contextually relevant memories
3. Inject via `additionalContext`
4. Log prompt to capture file (existing prompt_capture.py integration)

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook for context enrichment."""

import json
import sys
import re
from memory.index import MemoryIndex

# Trigger phrases that indicate memory retrieval would help
MEMORY_TRIGGERS = [
    r"why did we",
    r"what was the decision",
    r"remind me",
    r"continue (from|where)",
    r"last time",
    r"previous(ly)?",
    r"earlier",
    r"the plan",
    r"the blocker",
]

def should_inject_memory(prompt: str) -> bool:
    """Check if prompt suggests memory retrieval would help."""
    prompt_lower = prompt.lower()
    return any(re.search(pattern, prompt_lower) for pattern in MEMORY_TRIGGERS)

def main():
    hook_data = json.loads(sys.stdin.read())
    prompt = hook_data.get("prompt", "")
    
    if not should_inject_memory(prompt):
        sys.exit(0)
    
    index = MemoryIndex()
    
    # Use the prompt itself as the semantic query
    memories = index.search(query=prompt, limit=5)
    
    if not memories:
        sys.exit(0)
    
    context = format_memory_context(memories)
    
    print(json.dumps({
        "additionalContext": f"""
## Relevant Memories

Based on your question, here are relevant memories from previous sessions:

{context}
"""
    }))

if __name__ == "__main__":
    main()
```

### 2.3 PostToolUse Hook - Learning Capture

Create `plugins/cs/hooks/post_tool_use.py` to capture learnings from tool execution.

**Trigger Matchers:**
- `Write` (file creation/modification)
- `Edit` (code changes)
- `Bash` (command execution with errors/discoveries)
- `Task` (subagent completions)

**Behavior:**
1. Analyze tool output for capturable insights
2. Queue memory for persistence (don't block with git operations)
3. Use `additionalContext` to acknowledge capture

```python
#!/usr/bin/env python3
"""PostToolUse hook for learning capture."""

import json
import sys
from pathlib import Path

# Patterns indicating learnable moments
LEARNING_INDICATORS = [
    "error:",
    "warning:",
    "deprecated",
    "workaround",
    "fixed by",
    "the issue was",
    "discovered that",
    "turns out",
    "important:",
    "note:",
]

def extract_learning(tool_name: str, output: str) -> str | None:
    """Extract potential learning from tool output."""
    output_lower = output.lower()
    
    for indicator in LEARNING_INDICATORS:
        if indicator in output_lower:
            # Extract context around the indicator
            return extract_context_around(output, indicator)
    
    return None

def main():
    hook_data = json.loads(sys.stdin.read())
    tool_name = hook_data.get("toolName", "")
    tool_output = hook_data.get("toolOutput", "")
    
    learning = extract_learning(tool_name, tool_output)
    
    if not learning:
        sys.exit(0)
    
    # Queue for async persistence (don't block)
    queue_memory({
        "type": "learning",
        "source_tool": tool_name,
        "content": learning,
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    print(json.dumps({
        "additionalContext": "📝 Learning captured for future reference."
    }))

if __name__ == "__main__":
    main()
```

### 2.4 Stop Hook - Memory Persistence

Create `plugins/cs/hooks/stop.py` to ensure memories are persisted before session ends.

**Behavior:**
1. Flush any queued memories to git notes
2. Update index with new memories
3. Generate session summary if significant work occurred

```python
#!/usr/bin/env python3
"""Stop hook for memory persistence."""

import json
import sys
from memory.storage import GitNotesStorage
from memory.index import MemoryIndex
from memory.queue import MemoryQueue

def main():
    hook_data = json.loads(sys.stdin.read())
    stop_reason = hook_data.get("stopReason", "")
    
    # Check for infinite loop prevention
    if hook_data.get("stop_hook_active"):
        sys.exit(0)
    
    queue = MemoryQueue()
    pending = queue.get_pending()
    
    if not pending:
        sys.exit(0)
    
    storage = GitNotesStorage()
    index = MemoryIndex()
    
    persisted = 0
    for memory in pending:
        try:
            storage.add_memory(memory)
            index.index_memory(memory)
            persisted += 1
        except Exception as e:
            # Log but don't fail the stop
            log_error(f"Failed to persist memory: {e}")
    
    queue.clear()
    
    if persisted > 0:
        print(json.dumps({
            "additionalContext": f"💾 Persisted {persisted} memories to project history."
        }))

if __name__ == "__main__":
    main()
```

---

## Phase 3: CLI Commands

### 3.1 Memory Management Commands

Add new slash commands to `plugins/cs/commands/`:

**`/cs:remember` - Explicit Memory Capture**

```markdown
---
argument-hint: <type> <summary>
description: Explicitly capture a memory of specified type
---

# Memory Capture

Capture a memory to persist across sessions.

## Usage

/cs:remember decision "Chose PostgreSQL for ACID compliance"
/cs:remember blocker "CI fails on ARM64 due to missing wheels"
/cs:remember learning "pytest-xdist requires -n auto for parallelism"

## Memory Types

- `decision` - Architectural or design decisions (creates ADR)
- `blocker` - Obstacles encountered (with resolution tracking)
- `learning` - Technical insights discovered
- `progress` - Task completion markers
- `pattern` - Reusable cross-project patterns

## Workflow

1. Parse type and summary from arguments
2. Prompt for additional context if needed
3. Determine commit anchor (HEAD or prompt for specific commit)
4. Store in appropriate namespace
5. Index for semantic retrieval
```

**`/cs:recall` - Semantic Memory Search**

```markdown
---
argument-hint: <query>
description: Semantic search across project memories
---

# Memory Recall

Query memories using natural language.

## Usage

/cs:recall "why did we choose PostgreSQL"
/cs:recall "blockers in authentication"
/cs:recall --spec user-auth "all decisions"
/cs:recall --type learning "database performance"

## Options

- `--spec <slug>` - Filter to specific specification
- `--type <type>` - Filter by memory type
- `--since <date>` - Filter by date
- `--hydrate` - Show full content (default: summaries only)
- `--files` - Include file snapshots from commits

## Progressive Hydration

Default output shows summaries. Use `--hydrate` for full content.
Claude will automatically fetch file context when reasoning requires it.
```

**`/cs:memory` - Memory System Management**

```markdown
---
argument-hint: <action>
description: Memory system management
---

# Memory Management

Manage the memory system infrastructure.

## Actions

### status
Show memory system health:
- Note count by namespace
- Index sync status
- Storage size

### reindex
Rebuild SQLite index from git notes:
```
/cs:memory reindex
```

### sync
Push/pull memories to/from remote:
```
/cs:memory sync push
/cs:memory sync pull
```

### gc
Garbage collect orphaned memories:
```
/cs:memory gc --dry-run
/cs:memory gc --force
```

### export
Export memories to markdown:
```
/cs:memory export --spec user-auth > memories.md
```
```

---

## Phase 4: Lifecycle Integration

### 4.1 Planning Phase (`/cs:p`) Integration

Modify `plugins/cs/commands/p.md` to integrate memory:

**Memory In (Consumption):**
```
1. Auto-recall similar past specifications via semantic search
2. Surface relevant patterns from cs/patterns namespace
3. Inject previous decisions that may inform this spec
4. Show blockers from similar implementations
```

**Memory Out (Creation):**
```
1. Create cs/inception memory with problem statement
2. Capture elicitation Q&A as cs/elicitation memories
3. Store research findings as cs/research memories
4. Record architectural decisions as cs/decisions (ADR format)
```

### 4.2 Implementation Phase (`/cs:i`) Integration

Modify `plugins/cs/commands/i.md`:

**Memory In:**
```
1. Load all decisions and research from planning phase
2. Surface blockers from similar implementations
3. Inject learnings tagged with relevant technologies
```

**Memory Out:**
```
1. Capture progress markers on task completion
2. Record blockers when obstacles arise
3. Document learnings from technical discoveries
4. Note deviations from original plan
```

### 4.3 Close-out Phase (`/cs:c`) Integration

Modify `plugins/cs/commands/c.md`:

**Memory In:**
```
1. Comprehensive recall of all memories for this spec
2. Cross-reference with original plan
```

**Memory Out:**
```
1. Generate retrospective summary
2. Extract generalizable patterns to cs/patterns
3. Archive spec-specific memories with completion marker
```

---

## Phase 5: Testing & Benchmarking

### 5.1 Unit Tests

Create `tests/memory/` with pytest tests:

```python
# tests/memory/test_storage.py
import pytest
from plugins.cs.memory.storage import GitNotesStorage, Memory

class TestGitNotesStorage:
    def test_add_memory_creates_note(self, git_repo):
        storage = GitNotesStorage()
        memory = Memory(
            type="decision",
            spec="test-spec",
            phase="planning",
            timestamp="2025-12-17T10:00:00Z",
            tags=["test"],
            summary="Test decision",
            commit="HEAD",
            content="## Context\nTest context"
        )
        
        note_id = storage.add_memory(memory)
        
        assert note_id is not None
        retrieved = storage.get_memory("HEAD", "decision")
        assert retrieved.summary == "Test decision"

# tests/memory/test_index.py
class TestMemoryIndex:
    def test_semantic_search_returns_relevant(self, populated_index):
        results = populated_index.search("database choice")
        
        assert len(results) > 0
        assert any("PostgreSQL" in m.summary for m, _ in results)

# tests/memory/test_hooks.py
class TestHooks:
    def test_session_start_injects_context(self, active_spec_repo):
        result = run_hook("session_start", {"cwd": str(active_spec_repo)})
        
        assert "additionalContext" in result
        assert "memories" in result["additionalContext"].lower()
```

### 5.2 Integration Tests for claude-spec-benchmark

Create benchmark scenarios that validate memory persistence and retrieval:

```python
# benchmarks/memory_scenarios.py

MEMORY_BENCHMARK_SCENARIOS = [
    {
        "id": "memory-persistence-001",
        "name": "Decision Memory Roundtrip",
        "description": "Verify decisions persist across sessions",
        "steps": [
            {"action": "create_spec", "args": {"name": "test-auth"}},
            {"action": "add_memory", "args": {
                "type": "decision",
                "summary": "Use JWT for authentication"
            }},
            {"action": "new_session"},  # Simulate session restart
            {"action": "recall_memory", "args": {
                "query": "authentication decision"
            }},
        ],
        "expected": {
            "memory_found": True,
            "summary_contains": "JWT"
        }
    },
    {
        "id": "memory-context-001",
        "name": "SessionStart Context Injection",
        "description": "Verify relevant memories injected at session start",
        "steps": [
            {"action": "seed_memories", "args": {
                "spec": "user-auth",
                "memories": [
                    {"type": "blocker", "summary": "OAuth callback URL mismatch"},
                    {"type": "learning", "summary": "Use state parameter for CSRF"}
                ]
            }},
            {"action": "start_session", "args": {"active_spec": "user-auth"}},
        ],
        "expected": {
            "context_contains": ["OAuth", "state parameter"]
        }
    },
    {
        "id": "memory-semantic-001",
        "name": "Semantic Search Accuracy",
        "description": "Verify semantic search finds relevant memories",
        "steps": [
            {"action": "seed_memories", "args": {
                "memories": [
                    {"type": "decision", "summary": "PostgreSQL for relational data"},
                    {"type": "decision", "summary": "Redis for caching"},
                    {"type": "learning", "summary": "Connection pooling essential"}
                ]
            }},
            {"action": "recall_memory", "args": {
                "query": "database performance optimization"
            }},
        ],
        "expected": {
            "top_result_contains": ["PostgreSQL", "pooling"]
        }
    }
]
```

---

## Phase 6: Dependencies & Configuration

### 6.1 pyproject.toml Additions

```toml
[project.optional-dependencies]
memory = [
    "sqlite-vec>=0.1.0",
    "sentence-transformers>=2.2.0",
    "pyyaml>=6.0",
]

[project.scripts]
cs-memory = "plugins.cs.memory.cli:main"
```

### 6.2 Configuration Schema

Add to `plugins/cs/config.py`:

```python
MEMORY_CONFIG = {
    "index_path": ".cs-memory/index.db",
    "embedding_model": "all-MiniLM-L6-v2",
    "auto_capture": True,
    "capture_learnings": True,
    "capture_blockers": True,
    "session_context_limit": 10,  # Max memories in SessionStart
    "hydration_default": "INDEX",  # INDEX | MESSAGE | FILES
}
```

### 6.3 .gitignore Additions

```gitignore
# Memory index (derived, rebuildable)
.cs-memory/
```

---

## Implementation Order

1. **Week 1: Core Infrastructure**
   - [ ] `storage.py` - Git notes CRUD operations
   - [ ] `index.py` - SQLite-vec schema and basic queries
   - [ ] `hydration.py` - Progressive hydration logic
   - [ ] Unit tests for core modules

2. **Week 2: Hook Integration**
   - [ ] `session_start.py` hook
   - [ ] `prompt_submit.py` hook
   - [ ] `post_tool_use.py` hook
   - [ ] `stop.py` hook
   - [ ] Update `hooks/hooks.json`

3. **Week 3: CLI Commands**
   - [ ] `/cs:remember` command
   - [ ] `/cs:recall` command
   - [ ] `/cs:memory` management command
   - [ ] Integration with existing `/cs:p`, `/cs:i`, `/cs:c`

4. **Week 4: Testing & Benchmarking**
   - [ ] Integration tests
   - [ ] Benchmark scenarios for claude-spec-benchmark
   - [ ] Performance profiling
   - [ ] Documentation

---

## Success Criteria

1. **Persistence**: Memories survive session restarts and repository clones
2. **Retrieval**: Semantic search returns relevant memories within 500ms
3. **Integration**: Existing `/cs:*` commands automatically capture/consume memories
4. **Sync**: `git push/pull` transparently syncs memories
5. **Rebuild**: Index can be rebuilt from notes in under 10 seconds for 1000 memories
6. **Benchmark**: All memory scenarios pass in claude-spec-benchmark

---

## Execution Instructions

Begin implementation with Phase 1 (Core Infrastructure). Use test-driven development:

1. Write failing tests first
2. Implement minimal code to pass
3. Refactor for clarity
4. Proceed to next component

Use `uv` for dependency management. Follow existing claude-spec code style (ruff formatting, type hints, docstrings).

For each phase, create a separate branch and PR for review before merging to main.
