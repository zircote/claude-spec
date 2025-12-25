# Issue Reporter Command

```yaml
spec-id: SPEC-2025-12-25-002
status: approved
created: 2025-12-25
approved: 2025-12-25T20:03:24Z
approved_by: "Robert Allen <zircote@gmail.com>"
expires: 2026-01-24
github-issue: 27
priority: P1
complexity: medium
estimated-phases: 2
```

## Summary

Add a `/claude-spec:report-issue` command that **investigates issues first**, gathering detailed technical context, then creates a well-formatted GitHub issue with AI-actionable findings that can be leveraged by Claude, Copilot, or other AI tools to resolve the issue.

## Problem Statement

When issues are filed, they often lack the technical context needed for efficient resolution:
- Vague descriptions without code references
- Missing file paths and line numbers
- No analysis of root cause or related code
- Insufficient context for AI-assisted fixing

This results in back-and-forth clarification and slower resolution.

## Solution Overview

A `/report-issue` command that:
1. **Investigates** - Explores codebase to understand the issue
2. **Gathers findings** - Collects file paths, code snippets, error traces, related code
3. **Analyzes context** - Identifies potential causes and affected areas
4. **Confirms with user** - Reviews findings before issue creation
5. **Creates AI-actionable issue** - Rich context formatted for AI resolution

**Key Differentiator**: Issues created by this command include investigatory findings with enough detail that an AI can immediately begin working on a fix.

**Explicitly NOT in scope:**
- Implementing fixes
- Creating PRs
- Modifying any code

## Issue Types

| Type | Label | Investigation Focus |
|------|-------|---------------------|
| `bug` | bug | Error traces, affected code paths, reproduction context |
| `feat` | enhancement | Related existing code, integration points, patterns to follow |
| `docs` | documentation | Current doc state, code it should reflect |
| `chore` | chore | Files to change, dependencies, scope of work |
| `perf` | performance | Bottleneck locations, metrics, optimization targets |

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Scope | Investigation + Issue creation | Rich context enables AI resolution |
| Investigation depth | Thorough exploration | Better context = faster fixes |
| Output format | AI-actionable | Issues should be immediately workable |
| Interaction model | AskUserQuestion at key points | User validates findings before filing |

## Success Criteria

- [ ] `/report-issue` command operational
- [ ] Investigates codebase before issue creation
- [ ] Gathers file paths, code snippets, error context
- [ ] Produces issues with enough detail for AI-assisted fixing
- [ ] Repository detection with user confirmation
- [ ] Issue preview with findings before creation

## Documents

- [REQUIREMENTS.md](./REQUIREMENTS.md) - Detailed requirements
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Component design and investigation flow
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - Phased implementation
- [DECISIONS.md](./DECISIONS.md) - Architecture Decision Records
