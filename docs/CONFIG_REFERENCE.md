# Configuration Reference

This document describes the configuration options for the claude-spec plugin.

## File Locations

| Path | Description |
|------|-------------|
| `~/.claude/claude-spec.config.json` | **User config** - your personal settings (takes precedence) |
| `./claude-spec.config.json` | **Plugin default** - default values at plugin root |

**Precedence:** User config -> Plugin default -> Hardcoded defaults

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
  "healthCheckRetries": 6
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

## Example Configurations

### Minimal Config

Only override what you need:

```json
{
  "terminal": "iterm2-tab",
  "claudeCommand": "cc"
}
```

### Full Worktree Config

```json
{
  "terminal": "iterm2-tab",
  "shell": "zsh",
  "claudeCommand": "claude --dangerously-skip-permissions",
  "worktreeBase": "~/Projects/worktrees",
  "portPool": { "start": 8100, "end": 8199 },
  "portsPerWorktree": 2,
  "registryPath": "~/.claude/worktree-registry.json",
  "defaultCopyDirs": [".agents", ".env.example", ".env"],
  "healthCheckTimeout": 30,
  "healthCheckRetries": 6
}
```

### tmux Configuration

For users who prefer tmux sessions:

```json
{
  "terminal": "tmux",
  "shell": "zsh",
  "claudeCommand": "claude"
}
```

## Configuration Loading

The shell config loader (`skills/worktree-manager/scripts/lib/config.sh`) provides:

- `get_config <key>` - Get a config value
- `get_config_array <key>` - Get an array config value
- Auto-migration from old config path
- jq-based JSON parsing

### Loading Priority

1. **User Config Check**: Look for `~/.claude/claude-spec.config.json`
2. **Auto-Migration**: If old path exists (`~/.claude/worktree-manager.config.json`), rename to new path
3. **Fallback**: If no user config, load plugin default (`./claude-spec.config.json`)
4. **Deep Merge**: User config values override defaults recursively
