---
project_id: SPEC-2025-12-14-001
project_name: "Git-Native Memory System for claude-spec"
slug: cs-memory
status: in-progress
created: 2025-12-14T20:14:00Z
approved: null
started: 2025-12-14T21:30:00Z
completed: null
expires: 2026-03-14T20:14:00Z
superseded_by: null
tags: [memory, git-notes, semantic-search, sqlite-vec, embeddings, proactive-recall]
stakeholders: []
worktree:
  branch: plan/git-notes-integration
  base_branch: main
---

# Git-Native Memory System for claude-spec

## Quick Links

- [Requirements](./REQUIREMENTS.md)
- [Architecture](./ARCHITECTURE.md)
- [Implementation Plan](./IMPLEMENTATION_PLAN.md)
- [Decisions](./DECISIONS.md)
- [Research Notes](./RESEARCH_NOTES.md)

## Overview

Implement a comprehensive memory system for the claude-spec framework that enables persistent, semantically-searchable context across Claude Code sessions. The system uses Git notes as the canonical storage layer (attached to commits) and SQLite with sqlite-vec for semantic retrieval via vector similarity search.

## Core Principle

> "If a memory has no commit, it had no effect."

Every memory (decision, learning, blocker, progress) must attach to a Git commit, ensuring memories are grounded in concrete project history and distributed with the repository.

## Status

- **Current Phase**: Specification Review
- **Status**: In Review
- **Next Step**: Approve and run `/cs:i cs-memory` to begin implementation

## Specification Summary

| Metric | Count |
|--------|-------|
| User Stories | 19 |
| Functional Requirements | 23 |
| Non-Functional Requirements | 13 |
| Architecture Decision Records | 15 |
| Implementation Tasks | 90+ |
| Estimated Phases | 3 |

## Key Revisions

### v1.2.0 (2025-12-14) - Research Review

Based on deep research analysis (10 findings, architect review 7.5/10):

1. **ADR Counter Eliminated**: SHA-based identification replaces monotonic counter (ADR-012 revised)
2. **Concurrency Safety Added**: File locking + `append` instead of `add` (FR-022, FR-023)
3. **Review Note Format Clarified**: JSON array per commit (FR-018)
4. **Error Handling Added**: Section 7 with taxonomy and graceful degradation
5. **History Rewriting Documented**: ADR-015 for orphaned notes handling

### v1.0.0 (2025-12-14) - Initial

Based on requirements elicitation, the following clarifications were incorporated:

1. **Primary Problem Reframed**: Claude's context loss after compaction (not just developer memory)
2. **Proactive Recall Added**: Session awareness + topic-based search (US-015, US-016, ADR-011)
3. **Team Scale Clarified**: ~6 concurrent developers per project
4. **Scope Confirmed**: Single-repo only, supplements CLAUDE.md
