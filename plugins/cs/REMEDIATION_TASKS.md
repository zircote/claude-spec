# Remediation Tasks

Generated: 2025-12-14
Source: [CODE_REVIEW.md](./CODE_REVIEW.md)

---

## Critical (Do Immediately)

- [ ] `memory/search.py:404-413` - Add `reset_optimizer()` for testing - Architecture
- [ ] `memory/patterns.py:640-649` - Add `reset_pattern_manager()` for testing - Architecture
- [ ] `memory/lifecycle.py:521-530` - Add `reset_lifecycle_manager()` for testing - Architecture

---

## High Priority (This Sprint)

- [ ] `hooks/lib/config_loader.py:148-189` - Cache configuration loading - Architecture
- [ ] `memory/capture.py:82-84` - Require dependencies explicitly or use factory - Architecture
- [ ] `memory/recall.py:43-47` - Require dependencies explicitly or use factory - Architecture
- [ ] `memory/sync.py:43-47` - Require dependencies explicitly or use factory - Architecture
- [ ] `hooks/command_detector.py:82-102` - Consolidate fallback I/O to shared module - Code Quality
- [ ] `hooks/post_command.py:68-88` - Consolidate fallback I/O to shared module - Code Quality
- [ ] `hooks/prompt_capture.py:86-106` - Consolidate fallback I/O to shared module - Code Quality

---

## Medium Priority (Next 2-3 Sprints)

### Security
- [ ] `skills/worktree-manager/scripts/launch-agent.sh:66` - Add warning for dangerous flag - Security
- [ ] `skills/worktree-manager/scripts/cleanup.sh:70-76` - Validate port is numeric - Security
- [ ] `filters/log_writer.py:239` - Change permissions from 0o644 to 0o600 - Security

### Performance
- [ ] `memory/sync.py:138-149` - Batch git operations in full_reindex - Performance
- [ ] `filters/log_writer.py:320-332` - Implement tail-read optimization - Performance

### Architecture
- [ ] `hooks/session_start.py:36-39` - Standardize sys.path manipulation - Architecture
- [ ] `hooks/command_detector.py:38-45` - Standardize sys.path manipulation - Architecture
- [ ] `hooks/post_command.py:35-42` - Standardize sys.path manipulation - Architecture
- [ ] `hooks/prompt_capture.py:50-61` - Standardize sys.path manipulation - Architecture
- [ ] `analyzers/log_analyzer.py:13-17` - Standardize sys.path manipulation - Architecture
- [ ] `analyzers/analyze_cli.py:17-21` - Standardize sys.path manipulation - Architecture
- [ ] `filters/pipeline.py` - Add Filter protocol for extensibility - Architecture
- [ ] `memory/index.py` - Consider splitting into Repository and Service layers - Architecture

### Code Quality
- [ ] `steps/log_archiver.py:58-64` - Extract safe_mtime to shared utils - Code Quality
- [ ] `steps/retrospective_gen.py:52-58` - Use shared safe_mtime utility - Code Quality
- [ ] `steps/base.py` - Add error categorization (retriable vs fatal) - Architecture
- [ ] `steps/security_reviewer.py:163-164` - Use VERSION_CHECK_TIMEOUT constant - Code Quality

---

## Low Priority (Backlog)

### Security
- [ ] `memory/search.py:81` - Replace MD5 with SHA256 for cache keys - Security
- [ ] `filters/pipeline.py:158-201` - Expand secret detection patterns - Security

### Performance
- [ ] `memory/lifecycle.py:multiple` - Pass `now` parameter to avoid repeated calls - Performance
- [ ] `hooks/session_start.py:85-105` - Combine filesystem checks - Performance
- [ ] `filters/pipeline.py:253-302` - Quick check before base64 decode - Performance
- [ ] `analyzers/log_analyzer.py:148-181` - Lazy session stats computation - Performance
- [ ] `memory/index.py:38-42` - Document thread safety constraints - Performance
- [ ] `memory/embedding.py:202-204` - Auto-unload model after bulk operations - Performance
- [ ] `memory/note_parser.py:64-65` - Add explicit YAML size limit - Performance

### Architecture
- [ ] Multiple files - Standardize error message prefixes - Architecture
- [ ] `memory/config.py` - Consider Namespace enum instead of frozenset - Architecture
- [ ] `filters/log_writer.py:101` - Consider cross-platform locking - Architecture

### Code Quality
- [ ] `memory/lifecycle.py` - Use shared calculate_temporal_decay - Code Quality
- [ ] `memory/lifecycle.py` - Use SECONDS_PER_DAY constant - Code Quality
- [ ] `memory/sync.py:226` - Add type hints to dict return - Code Quality
- [ ] `memory/search.py:260-276` - Consider RerankOptions dataclass - Code Quality
- [ ] `steps/context_loader.py:54,82-84` - Remove unused warnings list - Code Quality
- [ ] `memory/patterns.py:294-330` - Extract _get_content helper method - Code Quality
- [ ] `memory/note_parser.py:219-240` - Add namespace validation - Code Quality
- [ ] `filters/log_writer.py:145-165` - Rename to _is_symlink_attack - Code Quality
- [ ] `steps/log_archiver.py:58-64` - Add docstring to safe_mtime - Code Quality
- [ ] `memory/capture.py:177-189` - Use specific exception types - Code Quality
- [ ] Multiple files - Define SESSION_STATE_FILE constant - Code Quality
- [ ] `memory/patterns.py` - Remove unnecessary hasattr checks - Code Quality

---

## Summary

| Priority | Count |
|----------|-------|
| Critical | 3 |
| High | 10 |
| Medium | 18 |
| Low | 27 |
| **Total** | **58** |

---

## Notes

- Critical tasks should be addressed before the next release
- High priority tasks can be grouped into 2-3 PRs
- Medium priority can be addressed incrementally
- Low priority items are candidates for tech debt sprints
