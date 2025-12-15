# Project Brief: Git-Native Memory System for claude-spec

## Executive Summary

Implement a comprehensive memory system for the claude-spec framework that uses Git notes as the canonical storage layer and SQLite with sqlite-vec for semantic retrieval. This system will enable persistent, semantically-searchable context across Claude Code sessions, capturing decisions, learnings, blockers, and progress throughout the specification-driven development lifecycle.

## Problem Statement

### The Core Problem: Context Loss After Compaction

Claude Code sessions suffer from **context window exhaustion**. After 2+ compactions, Claude strays from documented guidance in CLAUDE.md, forgets architectural decisions, library versions, and user-provided directives—requiring developers to repeatedly reinforce and redo work.

Current mitigations are insufficient:

1. **CLAUDE.md files**: Guidance exists but isn't indexed or searchable
2. **Bloated .md files**: Decisions scattered across unindexed markdown (DECISIONS.md, PROGRESS.md)
3. **No commit coupling**: Memories disconnected from the code they describe
4. **No automatic recall**: Relevant context must be manually re-provided after compaction

### Secondary Problem: Team Context Sharing

Development teams (typically 6 concurrent developers per project) need to share evolving decisions across feature branches. Local work stays local until merged, capitalizing on Git's distributed nature—but there's no mechanism to share contextual memories alongside code.

### What This Is NOT

- Not a cross-repository knowledge base
- Not an onboarding tool (though that's a tertiary benefit)
- Not a replacement for CLAUDE.md—it **supplements** with indexed, progressively-revealed detail

## Proposed Solution

A dual-layer memory architecture:

1. **Storage Layer (Git Notes)**: Structured memories attached directly to commits via Git's notes feature, organized by namespace (decisions, learnings, blockers, etc.)

2. **Index Layer (SQLite + sqlite-vec)**: A derived, gitignored vector index enabling semantic search through embedding-based similarity

### Core Principle

> "If a memory has no commit, it had no effect."

Every memory must attach to a commit. Specification documents serve as commit anchors for pre-implementation memories through an early-scaffold, amend-as-developed strategy.

## Scope

### In Scope

- Memory capture system with structured note schema
- Semantic recall via vector similarity search
- Auto-capture integration with /cs:p, /cs:i, /cs:c commands
- Git notes namespace management and sync configuration
- SQLite index with sqlite-vec for KNN search
- Local embedding generation (sentence-transformers or Ollama)
- Progressive hydration (summary → full content → file snapshots)
- New commands: /cs:remember, /cs:recall, /cs:context, /cs:memory

### Out of Scope (Future Work)

- Cross-repository memory sharing
- Cloud-based embedding APIs
- Git UI integration
- Real-time collaborative memory editing

## Success Criteria

1. Memories persist across Claude Code sessions via Git notes
2. Semantic queries return relevant memories with <500ms latency
3. Auto-capture requires zero manual intervention during normal workflow
4. Index rebuilds correctly from notes (verifiable via rebuild test)
5. Notes sync correctly via git push/pull
6. **Proactive recall**: Claude automatically searches for relevant memories when working on topics
7. **Session awareness**: Minimal notification at session start that memories are available
8. Memory recall demonstrably reduces "straying from guidance" after compaction

## Technical Constraints

- Python 3.11+ (aligned with existing claude-spec)
- sqlite-vec extension for vector search
- Local embedding model (all-MiniLM-L6-v2 or similar, 384 dimensions)
- YAML front matter + Markdown body for note schema
- Must integrate with existing claude-spec plugin architecture

## Stakeholders

- **Primary User**: Developers using claude-spec for AI-assisted development
- **Integration Point**: claude-spec plugin system (commands, hooks)

## Timeline Estimate

- Phase 1 (Foundation): 1-2 weeks
- Phase 2 (Integration): 1-2 weeks  
- Phase 3 (Intelligence): 1-2 weeks

## References

- Research Paper: "Git-Native Memory Architecture for AI-Assisted Software Development"
- Git Notes Documentation: https://git-scm.com/docs/git-notes
- sqlite-vec: https://github.com/asg017/sqlite-vec
- Git-Context-Controller: https://arxiv.org/abs/2508.00031
