# Plankton Hooks Framework -- Deep Evaluation

**Date**: 2026-02-22
**Evaluator**: Claude Opus 4.6
**Codebase**: `/Users/alphab/Dev/LLM/DEV/plankton/.claude/hooks/`
**Scope**: All 7 hook scripts + config.json

---

## Executive Summary

Plankton is a Claude Code hooks framework implementing real-time code quality
enforcement through PostToolUse (linting), PreToolUse (config protection,
package manager enforcement), and Stop (session-end config tampering detection)
hooks. The framework covers Python, Shell, YAML, JSON, TOML, Markdown,
Dockerfile, and TypeScript/JS/CSS -- an impressive breadth.

**Overall assessment**: Production-quality shell scripting with strong
architectural decisions. The three-phase PostToolUse design (auto-format,
collect violations, delegate to subprocess) is well-conceived. The main risk
is the 1287-line `multi_linter.sh` monolith, which is approaching the limit
of maintainability for a single shell script.

### Scoring

| Dimension | Score | Notes |
| --------- | ----- | ----- |
| Architecture | 8/10 | Three-phase design is excellent; monolith is the concern |
| Shell quality | 8/10 | Proper quoting, `set -euo pipefail`, ShellCheck-clean |
| Error handling | 7/10 | Fail-open by design; some edge cases noted below |
| Security | 7/10 | Good config protection; `/tmp` file concerns noted |
| Testability | 8/10 | Self-test suite with 103 integration tests is strong |
| Configurability | 9/10 | JSON config with sensible defaults and overrides |
| Performance | 6/10 | Sequential linter invocation; many subshells per file |

---

## 1. multi_linter.sh (1287 lines) -- PostToolUse Hook

### 1.1 Architecture and Control Flow

The three-phase architecture is the right design:

1. **Phase 1 (Auto-format)**: Silent formatting (ruff format, shfmt, taplo,
   markdownlint --fix, biome check --write). Reduces noise by fixing
   trivially-fixable issues before reporting.
2. **Phase 2 (Violation collection)**: Runs linters in check mode, converts
   heterogeneous output formats to a unified JSON violation schema
   (`{line, column, code, message, linter}`). This normalization is a
   significant strength.
3. **Phase 3 (Claude subprocess delegation)**: Spawns a `claude` subprocess
   with `--max-turns 10` to fix unfixable violations, then verifies by
   re-running Phase 1 + Phase 2.

The control flow is linear and readable:
```
stdin JSON -> extract file_path -> determine file_type -> case dispatch ->
Phase 1 -> Phase 2 -> model selection -> subprocess -> verify -> exit
```

**Strength**: The unified violation JSON schema across all linters is
excellent. It enables the model selection logic and subprocess prompting
to be linter-agnostic.

**Strength**: The `HOOK_SKIP_SUBPROCESS=1` testing mode (line 1268) is a
thoughtful design choice that enables testing Phase 1+2 without spawning
expensive subprocesses.

### 1.2 Phase 1: Auto-Format

Clean implementation. Each formatter runs with `|| true` to ensure formatting
failures never block the pipeline. The `is_auto_format_enabled` gate allows
disabling formatting globally.

**Observation**: For TypeScript, Phase 1 runs `biome check --write` which
does both formatting AND safe auto-fixes (line 772). This is more aggressive
than other languages where formatting and fixing are separate steps (e.g.,
Python runs `ruff format` then `ruff check --fix`). This is intentional per
the Biome design, but worth documenting.

### 1.3 Phase 2: Violation Collection

The per-language violation collection is thorough. For Python alone, it runs:
- ruff check (lines 869-875)
- ty type checking (lines 882-897)
- jscpd duplicate detection (lines 901-929)
- flake8-pydantic (lines 934-951)
- vulture dead code (lines 953-976)
- bandit security (lines 978-1002)
- flake8-async (lines 1004-1023)

That is seven tools for Python alone, which raises performance concerns
(see Section 1.7).

#### Bug: `has_issues=true` set unconditionally for pydantic output (line 949)

```bash
# Line 949
has_issues=true
```

This is set outside the `[[ -n "${pyd_json}" ]]` check. If `pyd_json` is
empty (parsing failed but `pydantic_output` was non-empty whitespace), this
incorrectly marks issues as present. The same pattern appears at line 1021
for flake8-async output. Compare with the vulture handler (lines 971-974)
which correctly gates `has_issues=true` inside the JSON check.

**Affected lines**: 949, 1021
**Severity**: Low (unlikely in practice since empty flake8 output means
no violations, but the logic is inconsistent)

#### Potential Issue: Flake8 output parsing fragility (lines 939-946)

The sed-based parsing of flake8's `file:line:col: CODE message` format is
brittle. If the filename contains a colon (unlikely but possible), the
regex `'^[^:]*:([0-9]+):[0-9]+: .*'` would fail. The same pattern is
used for yamllint (line 1065) and markdownlint (line 1213).

**Severity**: Very low (filenames with colons are extremely rare)

#### Design Concern: Duplicate case dispatch (lines 841-852 and 855-1229)

The file type is determined twice. First at lines 841-852 (setting
`file_type` for delegation), then again at lines 855-1229 (the actual
linting case statement). These two case statements must stay in sync.
If someone adds a new extension to one but not the other, the hook
silently does the wrong thing.

```bash
# Line 841-852 (first case - sets file_type for delegation)
case "${file_path}" in
  *.py) file_type="python" ;;
  ...
esac

# Line 855-1229 (second case - runs linters)
case "${file_path}" in
  *.py)
    ...
```

**Recommendation**: Merge into a single case statement, or extract the
file_type determination into a function and use it in both places.

### 1.4 Phase 3: Model Routing Logic

The three-tier model selection (haiku/sonnet/opus) at lines 233-256 is
well-designed:

```
haiku  <- default (simple lint fixes: unused vars, formatting)
sonnet <- complexity rules (C901, PLR*, PYD*, MD*, D*)
opus   <- type errors (unresolved-attribute, type-assertion) OR >5 violations
```

The regex patterns are configurable via `config.json`, with sensible defaults.
The volume threshold (default 5) escalates to opus when there are many
violations, which is smart -- more violations means more context needed.

**Observation**: The model routing is duplicated between `spawn_fix_subprocess`
(lines 233-256) and the debug output block (lines 1242-1263). These two
code paths could drift apart. Consider extracting a `select_model()` function.

**Observation**: The `SONNET_CODE_PATTERN` in `config.json` line 55 is
extremely long (a single-line regex with 40+ alternatives). This makes the
config file hard to read. Consider using a JSON array and joining at runtime.

### 1.5 Error Handling and Edge Cases

**Strengths**:
- Fail-open design: if jaq is missing, the hook exits 0 (line 33)
- All linter commands wrapped with `|| true` to prevent pipeline failures
- `set -euo pipefail` at the top ensures strict mode
- Subprocess timeout via `timeout` command (line 396), with graceful fallback
  when `timeout` is not installed
- The no-hooks-settings.json auto-creation (lines 370-391) uses atomic
  mktemp+mv pattern to handle concurrent invocations

**Concerns**:

1. **`trap 'kill 0' SIGTERM` (line 28)**: This sends SIGTERM to the entire
   process group on SIGTERM. Combined with `set -e`, if the hook receives
   SIGTERM during a subprocess call, `kill 0` will terminate all children.
   This is aggressive but probably correct for a hook that should not outlive
   its parent. However, `kill 0` also sends the signal to the hook itself,
   which could cause recursive signal handling. Consider `trap - SIGTERM;
   kill 0` instead.

2. **No SIGINT/SIGHUP handlers**: Only SIGTERM is trapped. If the user
   sends Ctrl+C during a long subprocess delegation, background processes
   may be orphaned.

3. **Empty `collected_violations` after subprocess**: If the subprocess
   partially fixes violations and introduces new ones, the verification
   step (rerun_phase2) only counts remaining violations -- it does not
   report what they are. The user sees `N violation(s) remain after
   delegation` but not which ones.

### 1.6 JSON Output Formatting

The violation JSON schema is consistent and well-designed:

```json
{
  "line": 42,
  "column": 5,
  "code": "F841",
  "message": "Local variable `x` is assigned but never used",
  "linter": "ruff"
}
```

**Potential issue**: The Biome byte-offset-to-line conversion (lines 800-803)
is clever but may have off-by-one errors for files with mixed line endings
(CRLF vs LF). The jaq expression `split("\n") | length` counts LF-terminated
lines, but CRLF files would include `\r` in each line's content. This is
unlikely to cause problems in practice since Biome itself handles line
endings correctly in its own output.

**Minor**: JSON is constructed by piping multiple arrays through
`jaq -s '.[0] + .[1]'` (e.g., line 873). This is functional but creates
a new jaq process for each merge. For files with many violation sources
(Python has 7), this is 7 jaq invocations just for merging arrays. A more
efficient approach would accumulate violations in a temp file and merge once.

### 1.7 Performance Considerations

This is the weakest area. For a Python file, the hook potentially runs:

1. `ruff format` (Phase 1)
2. `ruff check --fix` (Phase 1)
3. `ruff check --preview --output-format=json` (Phase 2)
4. `uv run ty check` (Phase 2b)
5. `npx jscpd` (Phase 2c -- session-scoped)
6. `uv run flake8 --select=PYD` (Phase 2d)
7. `uv run vulture` (Phase 2e)
8. `uv run bandit` (Phase 2f)
9. `uv run flake8 --select=ASYNC` (Phase 2g)
10. Multiple `jaq` invocations for JSON merging
11. `claude` subprocess (Phase 3)
12. All Phase 1+2 tools again for verification

That is 15+ process spawns per file edit. Each `uv run` has startup overhead
(resolving the venv). The hook has a 600-second timeout in `settings.json`,
which suggests this can indeed be slow.

**Recommendations**:
- Run Phase 2 tools in parallel (background processes + wait)
- Batch `uv run` invocations where possible
- Cache tool availability checks (currently `command -v` runs for every tool
  on every invocation; the biome detection is cached but nothing else is)

### 1.8 Shell Scripting Quality

Generally excellent. Specific observations:

**Proper quoting**: Variables are consistently double-quoted. No word
splitting vulnerabilities observed.

**ShellCheck compliance**: The script includes `# shellcheck disable=SC2310`
and `# shellcheck disable=SC2016` annotations where needed, indicating the
author runs ShellCheck on the script itself.

**Potential portability issue**: The script uses `sha256sum` (line 87 in
stop_config_guardian.sh), which is a GNU coreutils command. On macOS, this
is `shasum -a 256`. The hook appears to run on macOS (`Platform: darwin`
in the environment), so this would fail unless GNU coreutils is installed
via Homebrew. However, this is in `stop_config_guardian.sh`, not
`multi_linter.sh`.

**Anti-pattern: Format string injection in jaq (lines 237, 244, 1246, 1251)**:

```bash
jaq -e '[.[] | select(.code | test("'"${OPUS_CODE_PATTERN}"'"))]'
```

The `OPUS_CODE_PATTERN` is injected directly into the jaq expression via
shell string concatenation. If the pattern contained jaq metacharacters
(like unbalanced quotes or backslashes), this could break. The pattern
comes from `config.json`, so a malicious config could inject arbitrary jaq
expressions. This is low risk since the config is trusted, but `--arg`
would be more robust:

```bash
jaq -e --arg pat "${OPUS_CODE_PATTERN}" '[.[] | select(.code | test($pat))]'
```

### 1.9 Code Organization: The Monolith Question

At 1287 lines, `multi_linter.sh` is a significant monolith. The structure
is organized with clear section comments (`# ============`), and the code
reads linearly from top to bottom. However:

- Adding a new language requires modifying 3+ places (file_type case,
  linting case, rerun_phase1, rerun_phase2)
- The Python section alone (lines 856-1023) is 167 lines
- The TypeScript handler is extracted into a function (`handle_typescript`,
  50+ lines) but Python, Shell, YAML, etc. are inline in the case statement

**Recommendation**: Extract each language handler into a function (like
`handle_typescript`) for consistency. This would reduce the main case
statement to ~20 lines and make per-language logic testable independently.
A more ambitious refactor would split into `multi_linter.sh` (orchestrator)
+ `linters/*.sh` (per-language handlers), but that trades monolith
complexity for file management complexity.

---

## 2. protect_linter_configs.sh (87 lines) -- PreToolUse Hook

### Assessment: Clean and correct.

This script blocks Edit/Write operations on protected config files. The
implementation is straightforward:

1. Extract `file_path` from JSON input
2. Check against `.claude/hooks/*` and `.claude/settings*.json` paths
3. Check basename against `protected_files` list from config.json
4. Return `{"decision": "block"}` or `{"decision": "approve"}`

**Strengths**:
- Fail-open design: if jaq fails, outputs `{"decision": "approve"}` (line 22)
- Always exits 0 (correct for PreToolUse hooks)
- Config-driven protected files list with hardcoded defaults
- Path-based protection for the `.claude/` directory itself (line 36)

**Potential bypass**: The check uses `basename` matching (line 32). A file
at `/some/other/path/biome.json` would be blocked even though it is not the
project's biome.json. This is overly conservative but safe. The alternative
(checking relative path from project root) would be more precise.

**Potential bypass via symlink**: If Claude creates a symlink from an
unprotected name to a protected file, then edits the symlink target, this
hook would not detect it. This is a theoretical attack; Claude Code's Edit
tool likely resolves symlinks, making this a non-issue.

**No issues found.**

---

## 3. enforce_package_managers.sh (485 lines) -- PreToolUse Hook

### Assessment: Thorough and well-structured.

This script blocks legacy package managers (pip, npm, yarn, pnpm, poetry,
pipenv) and suggests replacements (uv, bun). The implementation supports
three modes per ecosystem: block, warn, and off.

**Strengths**:
- Comprehensive command mapping with context-aware replacements (e.g.,
  `pip install -r req.txt` maps to `uv pip install -r req.txt`)
- Allowlist support (`npm audit`, `pip download` are permitted)
- Diagnostic commands (`--version`, `--help`) are always allowed
- Independent blocks for different tool families enable detecting
  compound commands like `pip --version && poetry add requests`
- Debug and logging modes (`HOOK_DEBUG_PM=1`, `HOOK_LOG_PM=1`)
- Session-level bypass (`HOOK_SKIP_PM=1`)

**Design decision**: The script uses `(^|[^a-zA-Z0-9_])` word boundary
patterns (line 343) with bash regex matching. This is correct but Bash
regex support varies across versions. On macOS with Bash 3.2 (the default),
`[[:space:]]` is supported but `\b` is not, so the chosen approach is the
right one.

#### Known limitation: uv pip passthrough approves entire compound command

```bash
# Line 354
if [[ "${cmd}" =~ ${WB_START}uv[[:space:]]+pip ]]; then
  approve   # uv pip passthrough -- exits
```

If the command is `uv pip install -r req.txt && pip install flask`, the
`uv pip` match fires first and approves the entire compound command,
allowing `pip install flask` to execute. This is documented in the test
suite (line 939 of test_hook.sh) as a known limitation.

**Root cause**: The elif chain structure means the first match wins. Since
`uv pip` must be checked before `pip` (to avoid false positives on uv's
own pip passthrough), this ordering is necessary. Fixing this would require
splitting compound commands and checking each subcommand independently,
which adds significant complexity.

#### Potential Issue: Regex with BASH_REMATCH across if/elif (lines 357-375)

The `BASH_REMATCH` array is used correctly within each elif branch. However,
`BASH_REMATCH` is a global variable. If the patterns ever run in a function
that also uses regex matching internally (e.g., `is_allowed_subcommand`),
the match groups could be clobbered. Currently `is_allowed_subcommand` uses
`==` string comparison (not `=~`), so this is safe today but fragile for
future changes.

#### Observation: sed usage for argument extraction

Many branches use `sed -nE` to extract package names and subcommands from
the command string (e.g., lines 78, 90, 103, 112, etc.). This is correct
but creates a subprocess for each extraction. For a frequently-called hook,
pure Bash parameter expansion would be faster, though less readable.

**No bugs found.** The test suite (63 tests in test_hook.sh) provides
good coverage.

---

## 4. stop_config_guardian.sh (158 lines) -- Stop Hook

### Assessment: Well-designed with one portability bug.

This script detects modifications to protected config files at session end
and blocks exit until the user decides (keep/restore/show diff).

**Strengths**:
- Hash-based guard file (lines 79-104) prevents re-prompting after user
  approval within the same session
- Atomic guard file creation via `approve_configs.sh`
- `stop_hook_active` flag (line 24) prevents infinite blocking loops
- Uses `jaq -n` with `--arg` for safe JSON construction (line 149)
- The `AskUserQuestion` integration is well-specified with exact parameter
  templates

#### Bug: `sha256sum` portability (line 87)

```bash
current_hash="sha256:$(sha256sum "${file}" 2>/dev/null | cut -d' ' -f1)"
```

On macOS (the target platform per the environment), `sha256sum` is not
available by default. The correct command is `shasum -a 256`. This will
silently fail (`2>/dev/null`) and produce `current_hash="sha256:"`, which
will never match `stored_hash`, causing the guard check to always fail
and re-prompt the user.

This same issue appears in `approve_configs.sh` (line 36):
```bash
hash=$(sha256sum "${file}" | cut -d' ' -f1)
```

Here it is worse: no `2>/dev/null`, so it will produce an error message.

**Fix**: Use `shasum -a 256` on macOS, or check for availability:
```bash
if command -v sha256sum >/dev/null 2>&1; then
  hash_cmd="sha256sum"
elif command -v shasum >/dev/null 2>&1; then
  hash_cmd="shasum -a 256"
fi
```

**Severity**: Medium. The guard file feature is broken on stock macOS.
However, if GNU coreutils is installed via Homebrew (which the environment
suggests with `timeout` present at `/opt/homebrew/bin/timeout`), `sha256sum`
would be available as `gsha256sum` or via PATH.

**Update**: Checking the test results, `timeout` is at
`/opt/homebrew/bin/timeout`, confirming GNU coreutils is installed. If the
Homebrew gnubin path is in PATH, `sha256sum` would work. This is
environment-dependent.

#### Observation: git diff check against project root

Lines 58-71 check `git diff -- "${file}"` for each protected file. The
`${file}` is the basename from the protected_files list. This works because
the hook runs from the project root (CLAUDE_PROJECT_DIR). However, if a
protected file like `biome.json` exists in a subdirectory, `git diff` would
check the wrong file.

**Severity**: Low (protected files are typically at the project root).

---

## 5. approve_configs.sh (49 lines) -- Config Approval Helper

### Assessment: Simple and correct, with the sha256sum portability issue.

This script creates guard files for the stop hook. It is invoked by Claude
after the user approves config changes via `AskUserQuestion`.

**Strengths**:
- Simple, single-purpose script
- Correct argument validation (line 20)
- JSON output is manually constructed (no jaq dependency)

#### Bug: sha256sum portability (same as stop_config_guardian.sh)

Line 36: `hash=$(sha256sum "${file}" | cut -d' ' -f1)`

Same fix needed as above.

#### Minor: No JSON escaping for filenames (line 38)

```bash
json+="\"${file}\":\"sha256:${hash}\""
```

If a filename contains a double quote or backslash, the JSON would be
malformed. This is extremely unlikely for config file names like
`.ruff.toml`, but a `jaq -n --arg` approach would be more robust.

---

## 6. test_hook.sh (1107 lines) -- Self-Test Suite

### Assessment: Comprehensive and well-structured.

The test suite covers:
- File type detection (Dockerfile, Python, Shell, JSON, YAML)
- Output format validation
- Model selection (haiku/sonnet/opus routing)
- TypeScript-specific tests (Biome, nursery, SFC, oxlint overlap)
- Package manager enforcement (63 tests across pip, npm, yarn, pnpm,
  poetry, pipenv, compound commands, config toggles, warn mode, bypass)
- Tool-missing fallback behavior
- Debug mode

**Strengths**:
- Uses `mktemp -d` with proper cleanup trap (line 21)
- Creates isolated project directories with custom configs for each test
  scenario (e.g., `ts_project_dir`, `pm_project_dir`)
- Tests both decisions and replacement messages
- Tests compound commands and edge cases
- Clear PASS/FAIL output with summary

**Observations**:

1. **No TAP/JUnit output**: The test output is human-readable but not
   machine-parseable. Adding TAP (Test Anything Protocol) output would
   enable CI integration.

2. **Test isolation**: The cleanup trap (line 21) removes temp files
   scoped to `$$`. This is correct but relies on no other process using
   the same PID for temp files during the test run.

3. **Missing negative tests for protect_linter_configs.sh**: Only one
   protection test is included (biome.json, line 437). Testing approval
   of non-protected files would improve coverage.

4. **`script_dir` computed twice**: Lines 12 and 1093 both compute
   `script_dir`. The second computation is in the non-self-test path and
   overrides the first. This is harmless but unnecessary.

---

## 7. config.json -- Configuration Schema

### Assessment: Well-designed with sensible defaults.

The configuration covers:
- Per-language enable/disable with nested object support for TypeScript
- Protected files list (drives both PreToolUse and Stop hooks)
- Exclusion patterns for security linters
- Phase toggles (auto_format, subprocess_delegation)
- Subprocess configuration (timeout, model selection patterns)
- jscpd settings (session threshold, scan dirs, advisory mode)
- Package manager enforcement with per-tool allowlists

**Strengths**:
- `$schema` field for editor support (line 2)
- TypeScript config supports both boolean (`true`) and object
  (`{enabled: true, ...}`) forms for backward compatibility
- Default-true semantics: omitting a language enables it

**Observations**:

1. **No JSON Schema validation**: The `$schema` points to JSON Schema
   draft 2020-12 but no actual schema definition exists. The config
   is validated implicitly by the scripts' `jaq` queries. A proper
   JSON Schema would catch typos like `"pythn": true` at edit time.

2. **The sonnet_patterns string (line 55)**: This is a 700+ character
   regex pattern on a single line. It is unmaintainable. Consider using
   a JSON array:
   ```json
   "sonnet_patterns": [
     "C901", "PLR[0-9]+", "PYD[0-9]+", "FAST[0-9]+",
     "useExhaustiveDependencies", "noFloatingPromises", ...
   ]
   ```
   Then join with `|` at runtime in `load_model_patterns()`.

---

## Cross-Cutting Concerns

### Temp File Security

Multiple scripts use `/tmp/` for session-scoped state:

| File | Purpose |
| ---- | ------- |
| `/tmp/.biome_path_${SESSION_PID}` | Biome binary cache |
| `/tmp/.semgrep_session_${SESSION_PID}` | Semgrep file tracking |
| `/tmp/.jscpd_session_${SESSION_PID}` | jscpd file tracking |
| `/tmp/.jscpd_ts_session_${SESSION_PID}` | jscpd TS file tracking |
| `/tmp/.sfc_warned_${ext}_${SESSION_PID}` | SFC warning dedup |
| `/tmp/.nursery_checked_${SESSION_PID}` | Nursery validation dedup |
| `/tmp/.pm_warn_${tool}_${PID}` | PM tool-missing warning dedup |
| `/tmp/stop_hook_approved_${PID}.json` | Stop hook guard file |

**Concern**: These files use PIDs as identifiers. PIDs can be reused by
the OS after a process exits. If a new Claude session gets the same PPID
as a previous session, it could read stale state from `/tmp/`. This is
unlikely in practice (session duration is long relative to PID cycling)
but could cause subtle issues.

**Recommendation**: Add a timestamp or session start time to the filename,
or use `$TMPDIR` (which is per-user on macOS and often more secure than
`/tmp/`).

**No sensitive data exposure**: The temp files contain file paths, tool
paths, and content hashes. No secrets are written to `/tmp/`.

### Consistency of `is_excluded_from_security_linters`

The exclusion check (lines 203-218) is only applied to vulture and bandit
(lines 957-959, 981-983). It is not applied to flake8-pydantic or
flake8-async, even though those could also produce false positives on
test files. The exclusion list includes `tests/` and `scripts/`, which
are common locations for files that might need different linting rules.

### Exit Code Strategy

The hook uses:
- `exit 0`: No issues, or all issues fixed
- `exit 2`: Issues remain after delegation

This is correct per the Claude Code hook contract. However, `exit 1` is
never used explicitly (it would come from `set -e` on an unhandled failure).
The `jaq` dependency check at line 31 exits 0 (fail-open), which is the
right choice but means a broken jaq installation silently disables all
linting.

### Hook Interdependencies

The hooks are properly independent:
- `protect_linter_configs.sh` runs on Edit/Write PreToolUse
- `enforce_package_managers.sh` runs on Bash PreToolUse
- `multi_linter.sh` runs on Edit/Write PostToolUse
- `stop_config_guardian.sh` runs on Stop

There is a logical dependency between `protect_linter_configs.sh` and
`stop_config_guardian.sh` (both protect the same files). They share the
config via `config.json` but duplicate the fallback defaults. If these
defaults drift, the behavior would be inconsistent. Consider extracting
the defaults into a shared constant or requiring config.json to always
be present.

---

## Recommendations (Priority Order)

### High Priority

1. **Fix sha256sum portability** in `stop_config_guardian.sh` (line 87) and
   `approve_configs.sh` (line 36). Use `shasum -a 256` on macOS or add a
   portability wrapper.

2. **Extract model selection into a function** to eliminate duplication
   between `spawn_fix_subprocess` (line 233) and the debug output block
   (line 1242).

3. **Fix `has_issues=true` placement** in the Python pydantic handler
   (line 949) and flake8-async handler (line 1021). Move inside the JSON
   validation check.

### Medium Priority

4. **Merge duplicate case statements** (lines 841 and 855) into a single
   dispatch or extract `get_file_type()` function.

5. **Use `--arg` for jaq regex injection** instead of shell string
   interpolation (lines 237, 244, 1246, 1251). Eliminates injection risk
   from config values.

6. **Use `$TMPDIR` instead of `/tmp/`** for session state files. More
   secure and portable.

7. **Break the sonnet_patterns config** into a JSON array instead of a
   single long regex string.

### Low Priority

8. **Extract per-language handlers into functions** (like
   `handle_typescript` already is). Improves consistency and testability.

9. **Add parallel linter execution** for Python Phase 2 tools. Use
   background processes + `wait` to run ruff, ty, vulture, bandit, etc.
   concurrently.

10. **Add TAP output option** to `test_hook.sh` for CI integration.

11. **Add signal handlers** for SIGINT and SIGHUP in `multi_linter.sh`
    to ensure subprocess cleanup.

12. **Add a proper JSON Schema** for `config.json` to enable editor-time
    validation.

---

## Summary of Bugs Found

| # | Script | Line | Severity | Description |
| - | ------ | ---- | -------- | ----------- |
| 1 | stop_config_guardian.sh | 87 | Medium | `sha256sum` not available on stock macOS |
| 2 | approve_configs.sh | 36 | Medium | Same `sha256sum` portability issue |
| 3 | multi_linter.sh | 949 | Low | `has_issues=true` unconditional for pydantic |
| 4 | multi_linter.sh | 1021 | Low | `has_issues=true` unconditional for flake8-async |
| 5 | multi_linter.sh | 237,244 | Low | jaq regex injection via string interpolation |

---

## Strengths Worth Calling Out

1. **Fail-open design throughout**: Missing tools never block the developer.
   Every external dependency is checked with `command -v` before use.

2. **Unified violation JSON schema**: All linters output the same structure.
   This is architecturally excellent and enables tool-agnostic downstream
   processing.

3. **103-test integration suite**: The self-test coverage is impressive for
   a shell script project. The three-agent test execution (dep-agent,
   ml-agent, pm-agent) demonstrates a mature testing methodology.

4. **Session-scoped deduplication**: Semgrep, jscpd, and SFC warnings use
   session-scoped files to avoid redundant executions. This is a thoughtful
   performance optimization.

5. **Configurable model routing**: The haiku/sonnet/opus selection based on
   violation complexity is a novel approach that balances cost and capability.

6. **No-hooks recursion prevention**: The `no-hooks-settings.json` pattern
   (line 370) with atomic creation prevents subprocess hooks from triggering
   the parent hook, which would cause infinite recursion.

7. **Package manager enforcement with context-aware replacements**: The
   replacement messages are specific (`uv add flask` not just `use uv`),
   which reduces friction for the developer.
