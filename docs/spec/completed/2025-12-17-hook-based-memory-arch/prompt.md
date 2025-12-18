# Claude Code Execution Prompt: Git-Native Memory Architecture

## Role & Context

You are implementing a Git-Native Memory Architecture for the `claude-spec` plugin. This system enables persistent, semantically-searchable memory across AI-assisted development sessions by storing memories in Git notes (canonical) with SQLite-vec for semantic retrieval.

**Core Principle**: "If a memory has no commit, it had no effect."

## Repositories

- **Implementation Target**: https://github.com/zircote/claude-spec
- **Git Notes Reference**: https://github.com/zircote/git-adr (patterns for git notes storage)
- **Validation**: https://github.com/zircote/claude-spec-benchmark

## Architecture Summary

### Dual-Layer Storage

1. **Canonical Layer (Git Notes)**
   - Namespaces: `refs/notes/cs/{inception,elicitation,research,decisions,progress,blockers,learnings,patterns}`
   - Format: YAML front matter + Markdown body
   - Sync: Standard git push/pull with configured refspecs

2. **Index Layer (SQLite + sqlite-vec)**
   - Location: `.cs-memory/index.db` (gitignored, rebuildable)
   - Embeddings: `all-MiniLM-L6-v2` (384 dimensions)
   - Purpose: Sub-500ms semantic search

### Hook Integration Points

| Hook | Direction | Purpose |
|------|-----------|---------|
| `SessionStart` | Memory → Context | Inject relevant memories at session start |
| `UserPromptSubmit` | Memory → Context | Enrich prompts with contextual memories |
| `PostToolUse` | Output → Memory | Capture learnings from tool execution |
| `Stop` | Queue → Storage | Persist queued memories before session ends |

### CLI Commands

- `/cs:remember <type> <summary>` - Explicit capture
- `/cs:recall <query>` - Semantic search
- `/cs:memory <action>` - System management (status, reindex, sync, gc)

## Implementation Tasks

### Phase 1: Core Infrastructure

Create these files in `plugins/cs/memory/`:

```
plugins/cs/memory/
├── __init__.py
├── storage.py      # GitNotesStorage class
├── index.py        # MemoryIndex class with sqlite-vec
├── hydration.py    # Progressive hydration (INDEX → MESSAGE → FILES)
├── queue.py        # Async memory queue for non-blocking capture
└── models.py       # Memory dataclass and types
```

**Key Classes**:

```python
# models.py
@dataclass
class Memory:
    type: MemoryType  # Literal["inception", "elicitation", ...]
    spec: str
    phase: str
    timestamp: str
    tags: list[str]
    summary: str
    commit: str
    content: str

# storage.py
class GitNotesStorage:
    def add_memory(self, memory: Memory) -> str: ...
    def get_memory(self, commit: str, namespace: str) -> Memory | None: ...
    def list_memories(self, **filters) -> list[Memory]: ...
    def configure_remote_sync(self) -> None: ...

# index.py
class MemoryIndex:
    def index_memory(self, memory: Memory) -> None: ...
    def search(self, query: str, **filters) -> list[tuple[Memory, float]]: ...
    def rebuild_from_notes(self, storage: GitNotesStorage) -> int: ...
```

### Phase 2: Hooks

Create in `plugins/cs/hooks/`:

1. **`session_start.py`** - Auto-recall on session start
   - Detect active spec from `docs/spec/active/`
   - Query index for relevant memories (limit 10)
   - Return `additionalContext` with memory summary

2. **`prompt_submit.py`** - Context enrichment
   - Detect memory-related keywords ("why did we", "remind me", etc.)
   - Query index with prompt as semantic query
   - Inject relevant memories via `additionalContext`

3. **`post_tool_use.py`** - Learning capture
   - Match: Write, Edit, Bash, Task tools
   - Detect learning indicators (error:, warning:, fixed by, etc.)
   - Queue memory for async persistence

4. **`stop.py`** - Persistence flush
   - Flush queued memories to git notes
   - Update index
   - Report count via `additionalContext`

Update `hooks/hooks.json`:
```json
{
  "hooks": [
    {"event": "SessionStart", "command": ["python3", "${CLAUDE_PLUGIN_ROOT}/hooks/session_start.py"], "timeout": 5000},
    {"event": "UserPromptSubmit", "command": ["python3", "${CLAUDE_PLUGIN_ROOT}/hooks/prompt_submit.py"], "timeout": 3000},
    {"event": "PostToolUse", "matcher": {"toolName": "^(Write|Edit|Bash|Task)$"}, "command": ["python3", "${CLAUDE_PLUGIN_ROOT}/hooks/post_tool_use.py"], "timeout": 2000},
    {"event": "Stop", "command": ["python3", "${CLAUDE_PLUGIN_ROOT}/hooks/stop.py"], "timeout": 5000}
  ]
}
```

### Phase 3: Commands

Create in `plugins/cs/commands/`:

1. **`remember.md`** - `/cs:remember`
2. **`recall.md`** - `/cs:recall`  
3. **`memory.md`** - `/cs:memory`

Modify existing commands to integrate memory:
- **`p.md`** - Add memory consumption (recall) and production (capture)
- **`i.md`** - Add progress/blocker capture
- **`c.md`** - Add retrospective synthesis and pattern extraction

### Phase 4: Testing

Create `tests/memory/` with:
- `test_storage.py` - Git notes operations
- `test_index.py` - SQLite-vec search
- `test_hooks.py` - Hook execution
- `conftest.py` - Fixtures (git repos, populated indices)

## Technical Requirements

- Python 3.11+
- Use `uv` for dependency management
- Type hints on all functions
- Docstrings (Google style)
- Ruff formatting
- pytest for tests (>80% coverage)

### Dependencies to Add

```toml
[project.optional-dependencies]
memory = [
    "sqlite-vec>=0.1.0",
    "sentence-transformers>=2.2.0",
]
```

## Execution Order

1. Clone claude-spec locally
2. Create `feature/memory-architecture` branch
3. Implement Phase 1 (core infrastructure) with tests
4. Implement Phase 2 (hooks) with tests
5. Implement Phase 3 (commands) with tests
6. Update documentation
7. Create PR with comprehensive description

## Success Metrics

- [ ] Memories persist across session restarts
- [ ] Semantic search returns relevant results in <500ms
- [ ] `git push/pull` syncs memories
- [ ] Index rebuilds from notes in <10s for 1000 memories
- [ ] All tests pass with >80% coverage
- [ ] Integration with `/cs:p`, `/cs:i`, `/cs:c` works seamlessly

## Begin Implementation

Start with Phase 1. Create `plugins/cs/memory/models.py` first to define the data structures, then `storage.py` for git notes operations, then `index.py` for semantic search. Write tests alongside each module.

Use the existing `git-adr` repository as a reference for git notes patterns - it demonstrates production-quality git notes handling in Python.
