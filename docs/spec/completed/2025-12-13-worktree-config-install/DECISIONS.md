---
document_type: decisions
project_id: SPEC-2025-12-13-001
---

# Worktree Manager Configuration Installation - Architecture Decision Records

## ADR-001: User Config Location

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User, Claude

### Context

The worktree-manager skill needs a stable location for user configuration that survives plugin updates. The current location (`plugins/cs/skills/worktree-manager/config.json`) is overwritten when the plugin updates.

### Decision

Store user configuration at `~/.claude/worktree-manager.config.json`.

### Consequences

**Positive:**
- Follows Claude Code's existing pattern for user-level config
- Survives plugin updates
- Centralized with other Claude configs
- Easy to back up

**Negative:**
- Requires migration for existing users (minor)
- Another file in ~/.claude/ directory

**Neutral:**
- Scripts need modification to look in new location

### Alternatives Considered

1. **`~/.config/worktree-manager/config.json`**: XDG standard, but doesn't follow Claude's pattern
2. **`~/.worktree-manager.json`**: Home directory pollution
3. **Environment variables**: More complex, harder to persist

---

## ADR-002: Config Lookup Precedence

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User, Claude

### Context

Scripts need to find configuration, but user config may not exist (first run) or may be incomplete.

### Decision

Use a fallback chain: User config → Template → Hardcoded defaults

```
1. Check ~/.claude/worktree-manager.config.json (user preferences)
2. Fall back to plugins/.../config.template.json (bundled defaults)
3. Fall back to hardcoded defaults (last resort)
```

### Consequences

**Positive:**
- Scripts always work, even without any config files
- Users can override just the fields they care about
- Template provides reference for all available options

**Negative:**
- Slightly more complex config loading logic

**Neutral:**
- Partial user configs are valid (missing fields use template values)

### Alternatives Considered

1. **Fail if no user config**: Poor first-run experience
2. **Copy template to user location automatically**: May overwrite user changes unexpectedly
3. **Merge at runtime**: Chosen approach - most flexible

---

## ADR-003: Interactive Setup via AskUserQuestion

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User

### Context

First-time users need to configure worktree-manager, but editing JSON files manually is tedious and error-prone.

### Decision

Use Claude's `AskUserQuestion` tool to interactively gather configuration preferences during first-time setup or when `/cs:wt:setup` is run.

### Consequences

**Positive:**
- User-friendly experience
- Validates choices against known options
- Leverages Claude's native UI capabilities
- No external dependencies

**Negative:**
- Requires Claude Code context (can't run standalone)
- Limited to pre-defined options plus "Other"

**Neutral:**
- Setup only runs when needed (missing config or explicit command)

### Alternatives Considered

1. **CLI prompts (readline/fzf)**: Requires additional tools, different UX
2. **Web UI**: Overkill for simple config
3. **Just use defaults**: Loses personalization benefit

---

## ADR-004: Template File Naming

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: Claude

### Context

The bundled configuration file serves as a template/default, not the active user config. The name should reflect this.

### Decision

Rename `config.json` to `config.template.json`.

### Consequences

**Positive:**
- Clear distinction between template and user config
- No confusion about which file to edit
- Template suffix is a common pattern

**Negative:**
- Existing documentation references `config.json`

**Neutral:**
- One-time rename during implementation

### Alternatives Considered

1. **`config.default.json`**: Similar, slightly less clear
2. **`config.example.json`**: Implies it's just an example, not used
3. **Keep `config.json`**: Confusing alongside user config

---

## ADR-005: Prompt Log Timing Fix Location

**Date**: 2025-12-13
**Status**: Accepted
**Deciders**: User, Claude

### Context

When `/cs:p` creates a worktree and launches a new agent, the `.prompt-log-enabled` marker isn't created until after the first prompt is processed, causing the first prompt to be missed.

### Decision

Create the spec directory and `.prompt-log-enabled` marker in the worktree BEFORE launching the agent, within the `p.md` command's `mandatory_first_actions` section.

### Consequences

**Positive:**
- First prompt is captured
- No changes needed to launch-agent.sh (stays generic)
- Marker creation logic stays with spec planning logic

**Negative:**
- p.md needs to compute the slug twice (once for marker, once when command runs)
- Slight complexity in mandatory_first_actions

**Neutral:**
- Works correctly even if second `/cs:p` execution skips directory creation (already exists)

### Alternatives Considered

1. **Add flag to launch-agent.sh**: Couples generic script to spec-specific logic
2. **Separate setup script**: More moving parts
3. **Hook modification**: More complex, harder to reason about timing
