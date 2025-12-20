# Research Notes: cs-memory

## 1. Prior Art

### 1.1 Git-Context-Controller (GCC)

**Source**: Chen et al., 2025. arXiv:2508.00031

**Key Findings**:
- GCC structures agent memory as a persistent file system with Git-like operations
- Operations: COMMIT, BRANCH, MERGE, CONTEXT
- Achieved 48% resolution on SWE-Bench-Lite (state-of-the-art)
- "Milestone-based checkpointing, exploration of alternative plans, and structured reflection"

**Relevance**:
- Validates Git semantics for AI memory
- Our approach differs: use Git itself, not Git-like system
- Similar progressive context retrieval concept

**Quote**:
> "Relying on simple compression means removing fine-grained details, weakening the agent's ability to ground its actions in specific prior thoughts."

### 1.2 Git Notes

**Source**: Git Documentation, git-scm.com/docs/git-notes

**Key Features**:
- Attach metadata to any Git object without changing its hash
- Stored in `refs/notes/` namespace
- Support multiple namespaces (`--ref=<namespace>`)
- Can push/pull independently

**Real-World Usage**:
- Git project links commits to mailing list discussions
- Google's git-appraise: full code review system on notes
- Gerrit reviewnotes plugin

**Quote** (Tyler Cipriani, 2022):
> "Git notes are almost a secret. They're buried by their own distressing usability. But git notes are continually rediscovered by engineers trying to stash metadata inside git."

### 1.3 sqlite-vec

**Source**: Alex Garcia, 2024. alexgarcia.xyz/blog/2024/sqlite-vec-stable-release

**Key Features**:
- SQLite extension for vector search
- Brute-force KNN (optimized with SIMD)
- Supports float32, int8, bit vectors
- Zero dependencies, runs anywhere

**Performance**:
- 100k vectors, 768 dimensions: ~75ms query time
- Bit vectors (3072d): 11ms query time
- "Fast enough" for most local AI workloads

**Quote**:
> "Most applications of local AI or embeddings aren't working with billions of vectors. Most deal with thousands of vectors, maybe hundreds of thousands."

**Related Tools**:
- sqlite-lembed: Local embedding generation in SQLite
- sqlite-rembed: Remote embedding API calls

---

## 2. Technical References

### 2.1 Git Notes Operations

```bash
# Add note to HEAD
git notes --ref=<namespace> add -m "<content>" HEAD

# Add note to specific commit
git notes --ref=<namespace> add -m "<content>" <commit-sha>

# Show note for commit
git notes --ref=<namespace> show <commit-sha>

# List all notes in namespace
git notes --ref=<namespace> list
# Output: <note-sha> <object-sha>

# Append to existing note
git notes --ref=<namespace> append -m "<additional>" <commit-sha>

# Edit note interactively
git notes --ref=<namespace> edit <commit-sha>

# Remove note
git notes --ref=<namespace> remove <commit-sha>

# Copy note to another commit
git notes --ref=<namespace> copy <source> <dest>

# Merge notes from another ref
git notes --ref=<namespace> merge <other-ref>
# Strategies: manual, ours, theirs, union, cat_sort_uniq

# Configure push
git config --add remote.origin.push "refs/notes/*:refs/notes/*"

# Configure fetch
git config --add remote.origin.fetch "refs/notes/*:refs/notes/*"

# View log with notes
git log --show-notes=<namespace>
```

### 2.2 sqlite-vec Schema

```sql
-- Load extension
.load ./vec0

-- Create virtual table for vectors
CREATE VIRTUAL TABLE vec_examples USING vec0(
    sample_embedding float[384]
);

-- Insert vectors (JSON format)
INSERT INTO vec_examples(rowid, sample_embedding)
VALUES (1, '[-0.200, 0.250, 0.341, ...]');

-- KNN query
SELECT rowid, distance
FROM vec_examples
WHERE sample_embedding MATCH '[0.890, 0.544, ...]'
ORDER BY distance
LIMIT 10;

-- With metadata table join
SELECT m.*, v.distance
FROM metadata m
JOIN vec_table v ON m.rowid = v.rowid
WHERE v.embedding MATCH ?
ORDER BY v.distance
LIMIT 10;
```

### 2.3 Sentence Transformers

```python
from sentence_transformers import SentenceTransformer

# Load model (downloads on first use)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embedding
embedding = model.encode("text to embed")
# Returns: numpy array of shape (384,)

# Batch encoding
embeddings = model.encode(["text 1", "text 2", "text 3"])
# Returns: numpy array of shape (3, 384)

# Available models (384 dimensions):
# - all-MiniLM-L6-v2 (fast, good quality)
# - all-MiniLM-L12-v2 (slower, better quality)
# - paraphrase-MiniLM-L6-v2 (paraphrase detection)

# Available models (768 dimensions):
# - all-mpnet-base-v2 (best quality)
# - multi-qa-mpnet-base-dot-v1 (Q&A optimized)
```

### 2.4 YAML Front Matter Parsing

```python
import yaml
import re

def parse_note(content: str) -> tuple[dict, str]:
    """Parse YAML front matter from note content."""
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        raise ValueError("Invalid note format: missing front matter")
    
    metadata = yaml.safe_load(match.group(1))
    body = match.group(2).strip()
    
    return metadata, body

def format_note(metadata: dict, body: str) -> str:
    """Format metadata and body into note content."""
    yaml_content = yaml.dump(metadata, default_flow_style=False)
    return f"---\n{yaml_content}---\n\n{body}"
```

---

## 3. Embedding Model Comparison

| Model | Dimensions | Speed | Quality | Size |
|-------|------------|-------|---------|------|
| all-MiniLM-L6-v2 | 384 | Fast | Good | 80MB |
| all-MiniLM-L12-v2 | 384 | Medium | Better | 120MB |
| all-mpnet-base-v2 | 768 | Slow | Best | 420MB |
| text-embedding-3-small (OpenAI) | 1536 | API | Excellent | N/A |
| nomic-embed-text (Ollama) | 768 | Local | Good | 274MB |

**Recommendation**: Start with all-MiniLM-L6-v2 for balance of speed/quality/size.

---

## 4. Performance Benchmarks

### 4.1 sqlite-vec (from Garcia's benchmarks)

**In-memory, 100k vectors**:
| Dimensions | Element Type | Query Time |
|------------|--------------|------------|
| 3072 | float32 | 214ms |
| 1536 | float32 | 105ms |
| 768 | float32 | 52ms |
| 384 | float32 | 26ms |
| 3072 | bit | 11ms |

**On-disk, 100k vectors**:
| Dimensions | Element Type | Query Time |
|------------|--------------|------------|
| 768 | float32 | <75ms |
| 384 | float32 | <50ms |

### 4.2 Embedding Generation

**all-MiniLM-L6-v2 on CPU**:
- Single text: ~30-50ms
- Batch of 10: ~100-150ms
- Batch of 100: ~800-1000ms

---

## 5. Git Notes Limitations

### 5.1 UI Support

| Platform | Notes Display | Notes Edit |
|----------|---------------|------------|
| GitHub | ❌ No | ❌ No |
| GitLab | ❌ No | ❌ No |
| Bitbucket | ❌ No | ❌ No |
| git log | ✅ Yes | N/A |
| git notes | ✅ Yes | ✅ Yes |
| GitKraken | ❌ No | ❌ No |

**Implication**: Notes are primarily CLI-accessible.

### 5.2 Conflict Handling

When two developers add notes to the same commit:
```bash
# Merge strategy options
git notes merge --strategy=manual      # Manual resolution
git notes merge --strategy=ours        # Keep local
git notes merge --strategy=theirs      # Keep remote
git notes merge --strategy=union       # Combine unique lines
git notes merge --strategy=cat_sort_uniq # Concatenate and sort

# Recommended for our use case
git config notes.cs.mergeStrategy cat_sort_uniq
```

### 5.3 Note Size Limits

- No hard limit in Git
- Practical limit: notes should be < 1MB
- Our notes typically < 5KB
- Large content should reference files, not embed

---

## 6. Integration Patterns

### 6.1 Hook-Based Capture

```python
# Using claude-spec hooks system
# plugins/cs/hooks/memory_hooks.py

def on_planning_complete(spec: str, artifacts: dict):
    """Hook called when /cs:p completes planning."""
    capture_service.capture(
        namespace="inception",
        spec=spec,
        summary=f"Initiated spec: {spec}",
        content=artifacts.get("problem_statement", ""),
    )

def on_task_complete(spec: str, task: str):
    """Hook called when a task is marked complete."""
    capture_service.capture(
        namespace="progress",
        spec=spec,
        summary=f"Completed: {task}",
        content=f"Task '{task}' marked complete.",
    )
```

### 6.2 Command Integration

```markdown
# In command markdown (e.g., p.md)

## Memory Integration

Before proceeding with planning:
1. Search for similar past specs: `/cs:recall "<idea>" --type=inception`
2. Search for relevant learnings: `/cs:recall "<domain>" --type=learnings`
3. Display findings to user

After generating artifacts:
1. Capture inception memory with problem statement
2. Capture decision memories for each ADR
3. Display memory capture summary
```

---

## 7. Open Questions

### 7.1 Resolved

- [x] Storage layer: Git notes ✓
- [x] Index layer: sqlite-vec ✓
- [x] Embedding model: all-MiniLM-L6-v2 ✓
- [x] Note format: YAML + Markdown ✓
- [x] Memory sharing: Team-wide ✓
- [x] Capture mode: Fully automatic ✓

### 7.2 To Explore During Implementation

- [ ] Optimal embedding text (summary only vs. full content?)
- [ ] Index update frequency (immediate vs. batched?)
- [ ] Memory pruning strategy for old specs
- [ ] Cross-repo memory sharing mechanism
- [ ] Privacy controls for sensitive memories
