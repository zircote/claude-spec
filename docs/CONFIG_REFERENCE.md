# Configuration Reference

This document describes the configuration options for the claude-spec plugin.

## File Locations

| Path | Description |
|------|-------------|
| `~/.claude/claude-spec.config.json` | **User config** - your personal settings (takes precedence) |
| `./claude-spec.config.json` | **Plugin default** - default values at plugin root |

**Precedence:** User config → Plugin default → Hardcoded defaults

### Auto-Migration

If you have an existing config at `~/.claude/worktree-manager.config.json`, it will be automatically renamed to `~/.claude/claude-spec.config.json` on first load.

## Full Configuration Schema

```json
{
  "terminal": "ghostty",
  "shell": "bash",
  "claudeCommand": "claude --dangerously-skip-permissions",
  "portPool": {
    "start": 8100,
    "end": 8199
  },
  "portsPerWorktree": 2,
  "worktreeBase": "~/Projects/worktrees",
  "registryPath": "~/.claude/worktree-registry.json",
  "defaultCopyDirs": [".agents", ".env.example", ".env"],
  "healthCheckTimeout": 30,
  "healthCheckRetries": 6,
  "lifecycle": {
    "sessionStart": {
      "enabled": true,
      "loadContext": {
        "claudeMd": true,
        "gitState": true,
        "projectStructure": true
      }
    },
    "commands": {
      "claude-spec:complete": {
        "preSteps": [
          { "name": "security-review", "enabled": true, "timeout": 120 }
        ],
        "postSteps": [
          { "name": "generate-retrospective", "enabled": true },
          { "name": "archive-logs", "enabled": true },
          { "name": "cleanup-markers", "enabled": true }
        ]
      }
    }
  }
}
```

## Property Reference

### Terminal Settings

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `terminal` | string | `"ghostty"` | Terminal app for worktree agents |
| `shell` | string | `"bash"` | Shell to use in terminal |
| `claudeCommand` | string | `"claude --dangerously-skip-permissions"` | Command to launch Claude Code |

**Terminal Options:**
- `ghostty` - GPU-accelerated terminal
- `iterm2` - iTerm2 window
- `iterm2-tab` - iTerm2 tab (recommended for macOS)
- `tmux` - Terminal multiplexer session
- `wezterm` - WezTerm terminal
- `kitty` - Kitty terminal
- `alacritty` - Alacritty terminal

### Port Pool

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `portPool.start` | number | `8100` | First port in available range |
| `portPool.end` | number | `8199` | Last port in available range |
| `portsPerWorktree` | number | `2` | Ports allocated per worktree |

With default settings (100-port pool, 2 per worktree), you can have up to 50 concurrent worktrees.

### Worktree Settings

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `worktreeBase` | string | `"~/Projects/worktrees"` | Base directory for worktrees |
| `registryPath` | string | `"~/.claude/worktree-registry.json"` | Global worktree registry location |
| `defaultCopyDirs` | string[] | `[".agents", ".env.example", ".env"]` | Directories to copy to new worktrees |
| `healthCheckTimeout` | number | `30` | Health check timeout in seconds |
| `healthCheckRetries` | number | `6` | Number of health check retries |

### Lifecycle Configuration

The `lifecycle` object controls hook behavior and command step execution.

#### Session Start

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `lifecycle.sessionStart.enabled` | boolean | `true` | Enable session start hook |
| `lifecycle.sessionStart.loadContext.claudeMd` | boolean | `true` | Load CLAUDE.md files |
| `lifecycle.sessionStart.loadContext.gitState` | boolean | `true` | Load git status/branch info |
| `lifecycle.sessionStart.loadContext.projectStructure` | boolean | `true` | Load project directory structure |

#### Command Lifecycle

Each command can have `preSteps` and `postSteps` arrays:

```json
{
  "lifecycle": {
    "commands": {
      "claude-spec:complete": {
        "preSteps": [...],
        "postSteps": [...]
      }
    }
  }
}
```

**Supported Commands:**

| Command Key | Triggered By |
|-------------|--------------|
| `claude-spec:plan` | `/claude-spec:plan` |
| `claude-spec:complete` | `/claude-spec:complete` |
| `claude-spec:implement` | `/claude-spec:implement` |
| `claude-spec:status` | `/claude-spec:status` |
| `claude-spec:log` | `/claude-spec:log` |
| `claude-spec:worktree` | `/claude-spec:worktree-*` |
| `claude-spec:memory-remember` | `/claude-spec:memory-remember` |
| `claude-spec:memory-recall` | `/claude-spec:memory-recall` |
| `claude-spec:memory-context` | `/claude-spec:memory-context` |
| `claude-spec:memory` | `/claude-spec:memory` |
| `claude-spec:code-review` | `/claude-spec:code-review` |
| `claude-spec:code-fix` | `/claude-spec:code-fix` |

## Available Steps

### Pre-Steps

Pre-steps run BEFORE the command executes.

| Step Name | Description | Options |
|-----------|-------------|---------|
| `security-review` | Run Bandit security scanner on Python code | `timeout`: scan timeout in seconds (default: 120) |

### Post-Steps

Post-steps run AFTER the command completes.

| Step Name | Description | Options |
|-----------|-------------|---------|
| `generate-retrospective` | Generate RETROSPECTIVE.md from logs | - |
| `archive-logs` | Archive .prompt-log.json to completed project | - |
| `cleanup-markers` | Remove temp files (.prompt-log-enabled, .cs-session-state.json) | - |

### Step Configuration

Each step in preSteps/postSteps has:

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | string | Yes | Step identifier |
| `enabled` | boolean | No | Enable/disable step (default: true) |
| `timeout` | number | No | Step-specific timeout in seconds |

Example:
```json
{
  "preSteps": [
    { "name": "security-review", "enabled": true, "timeout": 120 }
  ]
}
```

## Example Configurations

### Minimal Config

Only override what you need:

```json
{
  "terminal": "iterm2-tab",
  "claudeCommand": "cc"
}
```

### Disable Security Review

```json
{
  "lifecycle": {
    "commands": {
      "claude-spec:complete": {
        "preSteps": [
          { "name": "security-review", "enabled": false }
        ]
      }
    }
  }
}
```

### Add Custom Post-Step

```json
{
  "lifecycle": {
    "commands": {
      "claude-spec:complete": {
        "postSteps": [
          { "name": "generate-retrospective", "enabled": true },
          { "name": "archive-logs", "enabled": true },
          { "name": "cleanup-markers", "enabled": true }
        ]
      }
    }
  }
}
```

### Disable Session Start Context

```json
{
  "lifecycle": {
    "sessionStart": {
      "enabled": false
    }
  }
}
```

## Configuration Loading

The config loader (`hooks/lib/config_loader.py`) implements:

1. **User Config Check**: Look for `~/.claude/claude-spec.config.json`
2. **Auto-Migration**: If old path exists (`~/.claude/worktree-manager.config.json`), rename to new path
3. **Fallback**: If no user config, load plugin default (`./claude-spec.config.json`)
4. **Deep Merge**: User config values override defaults recursively
5. **Caching**: Config is cached with mtime-based invalidation (ARCH-002)

### Shell Config Loader

The Bash config loader (`skills/worktree-manager/scripts/lib/config.sh`) provides:

- `get_config <key>` - Get a config value
- `get_config_array <key>` - Get an array config value
- Auto-migration from old config path
- jq-based JSON parsing
