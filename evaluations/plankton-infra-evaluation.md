# Plankton Infrastructure Evaluation

**Date**: 2026-02-22
**Evaluator**: Claude Opus 4.6
**Repo**: `/Users/alphab/Dev/LLM/DEV/plankton/`
**Commit**: `aefeb88` (main, clean)

## Executive Summary

Plankton is a well-architected Claude Code hooks framework for
real-time code quality enforcement across 8 languages. The
documentation is exceptionally thorough (particularly the reference
docs and ADRs), the hook scripts are production-tested, and the
overall design reflects significant iteration. However, there are
meaningful gaps in automated testing, CI pipeline coverage, and
onboarding smoothness that should be addressed before wider
adoption.

**Overall assessment**: Strong architecture and documentation,
weak automated test coverage, minimal CI pipeline.

---

## 1. Documentation Quality

### 1.1 README.md

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/README.md` (170
lines)

**Strengths**:

- Compelling problem statement in the opening paragraphs.
  The pain of copy-pasting pre-commit errors is relatable
  and immediately establishes the value proposition
- Clear three-phase architecture explanation
- Honest "todos" section showing active development and
  known limitations (lines 146-163)
- CAUTION banner warning about research status (line 35-37)

**Issues**:

1. **Quick start assumes template usage** (line 41): "Use this
   template to create a new repository" -- but the repo is not
   currently set up as a GitHub template. The GitHub repo settings
   would need `is_template: true`. Users cloning directly would
   skip this step and may miss important context.

2. **Missing prerequisite list in quick start**: The quick start
   says "Only jaq and ruff are required" (line 51) but does not
   include install commands inline. Users must navigate to
   `docs/SETUP.md` for `brew install jaq ruff uv`. This is one
   click too many for a quick start section.

3. **No screenshot or demo**: For a tool focused on developer
   experience, a GIF or screenshot showing the hook in action
   (violation caught, fixed by subprocess, clean exit) would
   significantly improve first impressions.

4. **"how it works" section is narrative-heavy**: Lines 67-101
   read more like a blog post than technical documentation. The
   first-person voice ("I built Plankton because...") is engaging
   but may not match what users scanning docs expect. Consider
   separating the narrative motivation from the technical
   description.

5. **pyproject.toml uses placeholder name** (line 1 of
   pyproject.toml): `name = "my-project"` -- this should be
   `name = "plankton"` for the template repo itself, or the
   README should instruct users to rename it.

6. **License section says MIT but LICENSE file has copyright
   "2025"** (`/Users/alphab/Dev/LLM/DEV/plankton/LICENSE` line
   3): The copyright year is 2025 but the project dates suggest 2026. Minor but worth updating.

### 1.2 docs/REFERENCE.md

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/docs/REFERENCE.md`
(1843 lines)

**Strengths**:

- Exceptionally detailed. This is one of the most thorough hook
  system references I have seen for any CLI tool extension.
- ASCII art diagrams for architecture, message flow, execution
  timeline, and visibility model are clear and well-structured
  (lines 8-38, 42-84, 436-472, 484-530)
- Comprehensive table of all possible messages (lines 400-408)
- Exit code strategy is unambiguous (lines 409-429)
- Linter behavior table by file type (lines 603-628) is an
  excellent quick reference
- Model selection documentation with rationale (lines 1259-1343)
- Subprocess hook prevention section is well-explained with the
  "why needed" and "why safe" structure (lines 1204-1233)

**Issues**:

1. **Stale line number references in ADR**: The hook schema
   convention ADR (`adr-hook-schema-convention.md` line 305)
   references "docs/REFERENCE.md line 817" for the Hook Schema
   Reference table. The actual table is near line 820-828.
   Line numbers in cross-references are fragile and will drift.
   Consider using section anchors instead.

2. **Missing biome.json from repo**: REFERENCE.md documents Biome
   configuration (line 1403: `biome.json`) but no `biome.json`
   exists at the project root. The `init-typescript.sh` script
   creates one, but this creates a bootstrapping confusion: the
   config file is listed as "protected" in `config.json` (line 34) and CLAUDE.md, but does not exist yet.

3. **PostToolUse timeout discrepancy**: The REFERENCE.md
   discusses hook timeouts generally, but the actual
   `settings.json` sets the PostToolUse timeout to 600 seconds
   (line 39), while the portable-hooks-template spec (line 370)
   documents 60 seconds. The 600-second timeout is likely correct
   for subprocess delegation but is not documented in
   REFERENCE.md.

4. **No table of contents**: At 1843 lines, this document needs
   a TOC. Markdown renderers on GitHub auto-generate one, but
   an explicit TOC would help users navigating offline or in
   editors.

### 1.3 docs/SETUP.md

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/docs/SETUP.md`
(254 lines)

**Strengths**:

- Per-language sections with clear install commands
- "Starter configs" section (lines 189-243) with three realistic
  profiles (minimal, Python-only, full-stack) is excellent
- Explicit explanation of when to disable vs. when tools are
  auto-skipped (lines 177-188)
- Verification step at the end (line 246-253)

**Issues**:

1. **macOS-only install commands**: All install commands use
   `brew install`. Linux users (the CI environment is
   ubuntu-latest) have no guidance. The CI workflow
   (`ci.yml`) only installs via `uv sync` and does not install
   brew-only tools (shellcheck, shfmt, hadolint, taplo, jaq).
   This means CI skips most linters silently.

2. **Missing `uv` install command**: The core dependencies
   section (line 11) says `brew install jaq ruff uv` but `uv`
   is often installed via `curl -LsSf https://astral.sh/uv/install.sh | sh`
   rather than brew. The setup guide should mention both methods.

3. **TypeScript section references `npm install`**: Line 87
   says `npm install` but the project enforces bun via package
   manager enforcement hooks. The first command a user runs
   would trigger a hook block. Should say `bun install` first,
   with npm as a fallback note.

4. **No troubleshooting section**: Common first-time issues
   (jaq not found, timeout not available on macOS, ruff version
   incompatibility) are not covered. These are mentioned in the
   portable-hooks-template spec but not in SETUP.md itself.

### 1.4 docs/FAQ.md

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/docs/FAQ.md`
(166 lines)

**Strengths**:

- Addresses the most important skeptical questions head-on
- "Won't the agent just modify the linting rules?" (line 42)
  is the killer feature explanation and is well-written
- Comparison with LSP plugins (lines 59-82) is technically
  accurate and fills a genuine knowledge gap
- "Can I use this on an existing codebase?" (line 157) is
  honest about limitations

**Issues**:

1. **Missing FAQ**: "How do I add a new linter?" This is
   the most common customization task and requires coordinated
   changes across 4-5 files (multi_linter.sh, config.json,
   CLAUDE.md, .pre-commit-config.yaml, and the config file
   itself). The portable-hooks-template spec documents this
   (Phase 7, Step 7.1, item 7) but it never made it into the
   published FAQ.

2. **Missing FAQ**: "How do I debug when hooks aren't firing?"
   The REFERENCE.md has debugging info (lines 699-773) but the
   FAQ does not mention it.

3. **Missing FAQ**: "What happens if jaq is not installed?"
   This is a common failure mode for first-time users.

### 1.5 docs/specs/\*.md (ADRs)

**Files**: 6 ADR/spec documents

| Document                              | Status   | Lines | Quality   |
| ------------------------------------- | -------- | ----- | --------- |
| `adr-typescript-hooks-expansion.md`   | Proposed | ~800+ | Excellent |
| `adr-hook-schema-convention.md`       | Accepted | 317   | Excellent |
| `adr-hook-integration-testing.md`     | Accepted | 400+  | Excellent |
| `adr-package-manager-enforcement.md`  | Accepted | 1285  | Excellent |
| `adr-cli-tool-preference-warnings.md` | Draft    | 308   | Good      |
| `portable-hooks-template.md`          | Draft    | 1069  | Good      |

**Overall**: The ADR quality is exceptionally high. Each follows
a consistent structure (Context, Decision Drivers, Decisions with
alternatives tables, Risks, Consequences). The level of detail
in the package manager enforcement ADR is particularly impressive
-- it includes regex patterns, bash code, processing flow, and
all edge cases.

**Issues**:

1. **CLI tool preferences ADR is Draft with unchecked
   implementation items** (line 285-289): D2 is still "TBD".
   The `enforce_package_managers.sh` script exists and works,
   but the CLI tool preferences (grep/jq warnings) appear
   unimplemented. The ADR exists but the feature does not.

2. **portable-hooks-template.md references "Incide"**: This
   document (lines 9, 17, 19, etc.) references the original
   "Incide" codebase extensively. For a published repo, these
   internal references should be cleaned up or contextualized.

3. **`[verify:]` markers in integration testing ADR**: Lines
   7-10 state that verify markers "must be resolved before this
   ADR moves to Accepted." The status is "Accepted" but the
   markers remain throughout the document. This is a process gap.

### 1.6 docs/psf/00-plankton-architecture-overview.md

**File**:
`/Users/alphab/Dev/LLM/DEV/plankton/docs/psf/00-plankton-architecture-overview.md`

**Strengths**:

- Mermaid diagrams for context, data flow, and system overview
- TL;DR section at the top is effective
- Component inventory with line counts and responsibilities

**Issues**:

1. **Only 200 lines read** (file may be longer): The
   architecture overview appears truncated in my reading. The
   component descriptions for protect_linter_configs.sh and
   stop_config_guardian.sh are cut off.

---

## 2. Testing

### 2.1 Python Test Suite

**Files**:

- `/Users/alphab/Dev/LLM/DEV/plankton/tests/__init__.py` (empty)
- `/Users/alphab/Dev/LLM/DEV/plankton/tests/unit/__init__.py` (empty)
- `/Users/alphab/Dev/LLM/DEV/plankton/tests/conftest.py` (13 lines)

**Assessment**: The Python test directory is essentially empty.
There is a conftest.py with a single `tmp_data_dir` fixture and
empty `__init__.py` files in `tests/` and `tests/unit/`. There
are zero actual test files (no `test_*.py` files anywhere).

**Impact**: The CI pipeline runs `uv run pytest tests/` which
will discover zero tests and exit successfully, giving a false
sense of passing CI. The `pyproject.toml` configures pytest with
`testpaths = ["tests"]` and `addopts = "-n auto"` (parallel
execution), but there is nothing to parallelize.

### 2.2 Hook Self-Test Suite

**File**:
`/Users/alphab/Dev/LLM/DEV/plankton/.claude/hooks/test_hook.sh`
(1106 lines)

This is the primary test artifact. It is a bash script with a
`--self-test` flag that exercises the hook pipeline with temp
files. It covers:

- Dockerfile patterns (valid and violation)
- Python, Shell, JSON, YAML file types
- JSON violation output format
- Model selection (haiku/sonnet/opus routing)
- TypeScript tests (gated on Biome availability)
- Protected file blocking

**Issue**: This test suite runs manually via
`.claude/hooks/test_hook.sh --self-test`. It is not integrated
into CI. The CI pipeline does not run it.

### 2.3 Stress Test Suite

**File**:
`/Users/alphab/Dev/LLM/DEV/plankton/tests/stress/run_stress_tests.sh`
(2335 lines)

**Strengths**:

- TAP (Test Anything Protocol) output format
- Performance timing with nanosecond resolution
- Category-based counters for structured reporting
- Cleanup traps for temp files and session markers
- Helper functions for running each hook type

**Issues**:

1. **Not integrated into CI**: Like the self-test suite, this
   runs manually. The CI workflow does not execute it.

2. **No documentation on how to run**: The script header says
   `Usage: bash tests/stress/run_stress_tests.sh` but there is
   no mention of it in README.md, SETUP.md, or REFERENCE.md.

### 2.4 Integration Test Suite

**Files**:

- `/Users/alphab/Dev/LLM/DEV/plankton/.claude/tests/hooks/results/RESULTS.md`
- `/Users/alphab/Dev/LLM/DEV/plankton/.claude/tests/hooks/results/COMPARISON.md`
- Spec: `docs/specs/adr-hook-integration-testing.md`

**Assessment**: The 103-test integration suite ran via Claude
Code's TeamCreate feature (3 parallel agents). Results show
94 pass, 2 fail, 8 skip. The failures are environmental (wrong
test path, TeamCreate PreToolUse limitation), not hook defects.

**Issues**:

1. **JSONL result files are gitignored**: The `.gitignore` at
   line 61 excludes `.claude/tests/hooks/results/.start_ts` and
   the archive directory. The JSONL files referenced in
   RESULTS.md (`dep-agent-20260220T154717Z.jsonl`, etc.) are not
   present in the repo.

2. **Suite requires Claude Code with experimental agent teams**:
   This cannot be run in CI or by contributors without access to
   `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`.

3. **uv-managed tools largely absent during test run**:
   RESULTS.md line 153-157 notes ty, vulture, flake8-pydantic,
   flake8-async, and bandit are all absent. This means the
   integration tests never exercised the full Python linting
   pipeline.

### 2.5 Coverage Gaps

| Area                                       | Covered                              | Gap                                 |
| ------------------------------------------ | ------------------------------------ | ----------------------------------- |
| multi_linter.sh per-language               | Yes (self-test, stress, integration) | No CI automation                    |
| protect_linter_configs.sh                  | Yes (self-test)                      | No CI automation                    |
| enforce_package_managers.sh                | Yes (integration)                    | No CI, no self-test                 |
| stop_config_guardian.sh                    | Manual only                          | Cannot automate (needs session end) |
| config.json parsing                        | Partial (integration)                | No unit tests for jaq fallbacks     |
| Model selection logic                      | Yes (self-test, stress)              | No CI automation                    |
| Subprocess delegation                      | Never tested deterministically       | Stochastic by nature                |
| Phase 1 auto-format idempotency            | Partial (M25)                        | Not systematic                      |
| Error handling (jaq missing, ruff missing) | Not tested                           | Critical path untested              |
| Concurrent hook invocations                | Not tested                           | Documented as safe but unverified   |
| Edge case file paths (spaces, unicode)     | Not tested                           | Could break sed parsing             |

---

## 3. CI/CD

### 3.1 GitHub Actions Workflow

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/.github/workflows/ci.yml`
(25 lines)

**Assessment**: This is a minimal CI pipeline with two jobs:

```yaml
lint: uv sync --all-extras --locked && uv run pre-commit run --all-files
test: uv sync --all-extras --locked && uv run pytest tests/
```

**Issues**:

1. **No system dependency installation**: The lint job runs
   `uv run pre-commit run --all-files` on ubuntu-latest, but
   does not install jaq, shellcheck, shfmt, hadolint, taplo,
   markdownlint-cli2, biome, or any other non-Python tool.
   Pre-commit hooks for these tools will either fail silently
   (if `command -v` gated) or error out. The biome hooks in
   `.pre-commit-config.yaml` (lines 25, 32) gracefully exit 0
   when biome is absent, but shellcheck, hadolint, taplo,
   actionlint, and markdownlint-cli2 will hard-fail.

2. **Test job runs zero tests**: As documented in section 2.1,
   there are no Python test files. The test job passes
   vacuously.

3. **No hook self-test in CI**: Neither `test_hook.sh --self-test`
   nor `tests/stress/run_stress_tests.sh` runs in CI. The hooks
   are the core deliverable of this project, yet CI does not
   test them.

4. **No matrix testing**: Single Python version (whatever
   ubuntu-latest ships), single OS. No macOS testing despite
   macOS-specific dependencies (GNU coreutils `timeout`).

5. **No caching**: `uv sync --all-extras --locked` runs twice
   (once per job) without caching. Could use
   `actions/cache` or the built-in uv caching from
   `astral-sh/setup-uv`.

6. **`--locked` may fail**: The `--locked` flag requires
   `uv.lock` to be in sync with `pyproject.toml`. If a
   contributor updates pyproject.toml without running `uv lock`,
   CI fails with a confusing error. This is arguably desired
   behavior but should be documented.

### 3.2 Pre-commit Configuration

**File**:
`/Users/alphab/Dev/LLM/DEV/plankton/.pre-commit-config.yaml`
(129 lines)

**Strengths**:

- 15 hooks covering all supported languages
- Phase-organized with clear comments
- Graceful biome fallback (exit 0 if not installed)
- Intentional exclusions section with rationale (lines 120-128)
- `pass_filenames: false` for markdownlint and jscpd
  (project-wide scans)
- `require_serial: true` for ty-check (correct -- ty needs
  full project context)

**Issues**:

1. **markdownlint runs without filenames**: Line 107 sets
   `pass_filenames: false`, which means markdownlint-cli2 uses
   the globs from `.markdownlint-cli2.jsonc`. This is correct
   for the CI use case but different from how the hook runs
   (single file with `--no-globs`). The difference is documented
   in REFERENCE.md but could cause confusion.

2. **jscpd threshold duplicated**: The pre-commit hook passes
   `--threshold 5` (line 113) while `.jscpd.json` also sets
   `"threshold": 5`. This duplication could drift.

3. **check-jsonschema uses `github-workflows`**: Line 91 uses
   `--builtin-schema github-workflows` which is the correct
   modern flag name (not the deprecated `vendor.github-workflows`
   mentioned in the portable-hooks-template spec at line 647).

### 3.3 GitHub Templates

**Files**:

- `/Users/alphab/Dev/LLM/DEV/plankton/.github/PULL_REQUEST_TEMPLATE.md`
- `/Users/alphab/Dev/LLM/DEV/plankton/.github/ISSUE_TEMPLATE/bug_report.md`
- `/Users/alphab/Dev/LLM/DEV/plankton/.github/ISSUE_TEMPLATE/feature_request.md`

**Assessment**: Clean, minimal templates. The PR template
includes a checklist for self-test and pre-commit (appropriate).
The bug report template asks for Claude Code version and tool
versions (good diagnostics). Feature request template is standard.

**Issue**: No `config.yml` for issue template chooser. GitHub
will show both templates plus a blank issue option. Adding a
`config.yml` with `blank_issues_enabled: false` would funnel
users into the templates.

---

## 4. Project Configuration

### 4.1 pyproject.toml

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/pyproject.toml`
(44 lines)

**Issues**:

1. **Placeholder project name**: `name = "my-project"` (line 2).
   Should be `name = "plankton"`.

2. **No version pinning for dev dependencies**: All dev
   dependencies (ruff, ty, flake8, etc.) are unpinned. While
   `uv.lock` provides reproducibility, the pyproject.toml should
   have at minimum lower bounds for tools that have breaking
   changes between versions (e.g., ruff's preview rules).

3. **Missing `yamllint` type annotation**: yamllint is listed
   under `dev` extras but not under a separate `lint` group.
   Separating test deps from lint deps would allow
   `uv sync --extra lint` without installing pytest.

4. **`hatchling` build backend**: The project has no actual
   Python package to build. The `src/` directory contains only
   empty `__init__.py` files. The build-system section is
   template boilerplate that serves no purpose for this project.

### 4.2 package.json

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/package.json`
(28 lines)

**Issues**:

1. **`"main": "index.js"`** (line 5): No `index.js` exists.
   This is npm init boilerplate.

2. **`"license": "ISC"`** (line 19): Conflicts with the MIT
   LICENSE file at the repo root. Should be `"MIT"`.

3. **`"test": "echo \"Error: no test specified\" && exit 1"`**
   (line 11): The test script errors on invocation. Should
   either be removed or pointed at something meaningful.

4. **Missing `"author"`** (line 18): Empty string. Should be
   populated.

5. **`"keywords": []`** (line 17): Should include relevant
   keywords for discoverability (claude-code, hooks, linting,
   code-quality).

### 4.3 Docker Setup

**Dockerfile** (`/Users/alphab/Dev/LLM/DEV/plankton/Dockerfile`,
25 lines): Multi-stage build with proper LABEL, non-root user,
and uv for dependency installation. Clean template.

**docker-compose.yml** (7 lines): Minimal service definition.
Mounts `src/` for development. Appropriate for a template.

**Issue**: The Dockerfile copies `uv.lock` but does not install
any of the hook dependencies (jaq, shellcheck, etc.). This is
fine if Docker is for the application, not for running hooks.
But if someone tries to run hooks inside Docker, nothing will
work. A note in SETUP.md would help.

### 4.4 Makefile

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/Makefile`
(23 lines)

**Assessment**: Standard targets (install, lint, test, format,
install-hooks, clean). All use `uv run` correctly.

**Issues**:

1. **`make lint` only runs ruff**: Does not run shellcheck,
   yamllint, hadolint, or any other linter. The comprehensive
   lint is only available via `uv run pre-commit run --all-files`.
   A `make lint-all` target that runs pre-commit would be useful.

2. **No `make self-test` target**: The hook self-test is the
   most important validation but has no Makefile target.

### 4.5 Linter Configurations

All 14+ linter config files are present, well-documented, and
internally consistent:

| Config                     | Lines | Quality   | Notes                                        |
| -------------------------- | ----- | --------- | -------------------------------------------- |
| `.ruff.toml`               | 94    | Excellent | Comprehensive rule selection with rationale  |
| `ty.toml`                  | 61    | Good      | Test file relaxation with rationale          |
| `.flake8`                  | 6     | Good      | Minimal, focused on PYD and ASYNC            |
| `.yamllint`                | 127   | Excellent | All 23 rules explicitly configured           |
| `.shellcheckrc`            | 18    | Good      | Maximum enforcement with all checks          |
| `.hadolint.yaml`           | 62    | Excellent | Each ignore has documented rationale         |
| `.markdownlint.jsonc`      | 22    | Good      | Sensible defaults                            |
| `.markdownlint-cli2.jsonc` | 28    | Good      | Scoped globs                                 |
| `.jscpd.json`              | 23    | Good      | 5% threshold, sensible excludes              |
| `taplo.toml`               | 28    | Good      | Relaxed formatting, pyproject.toml exception |

**Notable**: The `.ruff.toml` enables 30+ rule categories
including preview rules, with per-file-ignores for tests that
are carefully calibrated. The `.hadolint.yaml` has individually
justified ignores for version pinning rules. This level of
intentionality is rare.

### 4.6 .claude/hooks/config.json

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/.claude/hooks/config.json`
(80 lines)

**Assessment**: Well-structured runtime configuration. All
documented keys are present. TypeScript is enabled with sensible
defaults.

**Issue**: The `sonnet_patterns` value (line 55) is a single
extremely long string (~800 characters) containing TypeScript
Semgrep rule names. This is unwieldy for maintenance. A future
improvement could split this into an array that the hook joins
at runtime.

### 4.7 .claude/settings.json

**File**: `/Users/alphab/Dev/LLM/DEV/plankton/.claude/settings.json`
(56 lines)

**Assessment**: Correctly registers all four hook scripts with
appropriate matchers and timeouts.

**Issue**: The PostToolUse timeout is 600 seconds (10 minutes).
This is high but justified by subprocess delegation. However,
the REFERENCE.md "Complete Timeline with Blocking" diagram
(line 488) shows T=26s as the expected completion time. The
10-minute timeout provides 23x headroom, which seems excessive.
A 120-second (2-minute) timeout would provide 5x headroom and
prevent runaway processes from blocking the agent for too long.

---

## 5. Gaps and Issues

### 5.1 Critical

1. **CI does not test hooks**: The core deliverable (bash hook
   scripts) is not tested in CI. The `test` job runs zero Python
   tests. The `lint` job runs pre-commit but will fail on missing
   system tools (shellcheck, hadolint, etc.) or silently skip
   them. **Recommendation**: Add a `hooks` job that installs all
   dependencies and runs `test_hook.sh --self-test` and/or
   `tests/stress/run_stress_tests.sh`.

2. **CI is incomplete for the linter tools**: The `lint` job
   does not install jaq, shellcheck, shfmt, hadolint, taplo,
   markdownlint-cli2, biome, or actionlint. Most pre-commit
   hooks will fail. **Recommendation**: Add installation steps
   for all system dependencies, or make the pre-commit hooks
   gracefully skip like the biome hooks do.

3. **Zero Python test files**: `tests/unit/` is empty. The
   conftest.py fixture is unused. The CI test job reports
   success with zero tests collected.

### 5.2 High

4. **No Linux install instructions**: All install commands in
   SETUP.md use `brew install`. Ubuntu/Debian users (and CI)
   need `apt-get`, `cargo install`, or download instructions.

5. **package.json/pyproject.toml placeholder values**: Project
   name is "my-project", license is ISC (should be MIT), author
   is empty, main is "index.js" (nonexistent). These should be
   corrected for the published repo.

6. **ADR implementation gaps**: The CLI tool preferences ADR
   (`adr-cli-tool-preference-warnings.md`) is Draft with an
   unresolved decision (D2). The `tool_preferences` config key
   is not present in config.json and the feature appears
   unimplemented. The ADR should either be implemented or marked
   as deferred.

7. **Schema convention deprecation risk**: The hook schema
   convention ADR (line 196-204) acknowledges that the `decision`
   field is deprecated for PreToolUse hooks. This is an
   acknowledged migration that has not been scheduled.

### 5.3 Medium

8. **Stress test suite not documented**: The 2335-line stress
   test script (`tests/stress/run_stress_tests.sh`) is not
   mentioned in any documentation file. Users and contributors
   would not know it exists.

9. **init-typescript.sh references npm**: Line 257 says
   `npm install` as the first recommended next step, but the
   project enforces bun. Should say `bun install`.

10. **biome.json bootstrapping chicken-and-egg**: The file is
    listed as protected in config.json and CLAUDE.md, but does
    not exist until `init-typescript.sh` is run. The PreToolUse
    hook will block creation of biome.json, requiring the user
    to approve the override. This should be documented.

11. **Fragile sed parsing acknowledged but not mitigated**: The
    REFERENCE.md (lines 1527-1568) documents that yamllint,
    flake8, and markdownlint output parsing uses sed and is
    fragile. The decision to keep sed parsing is documented, but
    no version pinning or format validation exists to catch
    regressions.

12. **`.gitignore` excludes CLAUDE.md then re-includes it**:
    Lines 58-59 have `CLAUDE.md` and `!/CLAUDE.md`. This pattern
    works but is confusing. The intent appears to be excluding
    CLAUDE.md from gitignore patterns higher in the file, then
    re-including it.

### 5.4 Low

13. **LICENSE copyright year**: 2025 in a project with 2026
    dates throughout.

14. **`bun.lock` committed**: The `bun.lock` file (7790 bytes)
    is committed. The `.gitignore` does not exclude it (correct
    behavior -- lockfiles should be committed). But
    `package-lock.json` is gitignored (line 60), creating
    asymmetry. If someone runs `npm install` by accident, they
    get no lockfile committed.

15. **Duplicate `dist/` in .gitignore**: Lines 6 and 40 both
    exclude `dist/`.

16. **`vulture_whitelist.py` is documentation-only**: Contains
    a docstring and no actual whitelist entries. This is correct
    for a template but the file will trigger a linting pass on
    itself (vulture checks that referenced names exist in the
    codebase).

---

## 6. Onboarding Friction Points

For a new user cloning this repo and trying to use it:

1. **Step 1 ambiguity**: README says "Use this template" but
   the repo may not be configured as a GitHub template. Cloning
   directly works but misses the template semantics.

2. **jaq is obscure**: Most developers have never heard of jaq.
   The first thing they see is "jaq and ruff are required" and
   may not understand why jq is not used instead. A one-line
   explanation ("jaq is a faster Rust-based jq alternative used
   for JSON parsing in hook scripts") in the quick start would
   help.

3. **No `make setup` or install wizard**: The README todos
   acknowledge this (line 146-147). Currently, users must
   manually run `brew install jaq ruff uv`, then `uv sync`,
   then optionally install 10+ more tools. An `./install.sh`
   or `make setup` that detects the platform and installs
   everything would dramatically improve first-run experience.

4. **config.json is not self-documenting**: While the `_comment`
   field exists, there is no JSON schema file for IDE validation.
   The `$schema` field points to the generic JSON Schema
   meta-schema, not a Plankton-specific schema.

5. **No `CONTRIBUTING.md`**: The repo accepts contributions
   (README line 165) but has no contributing guide explaining
   how to test changes, the ADR process, or the codebase
   structure.

---

## 7. Recommendations (Priority Order)

### P0 (Before wider adoption)

1. **Fix CI pipeline**: Add system dependency installation
   and hook self-test execution to the GitHub Actions workflow.
   At minimum, the CI should run
   `.claude/hooks/test_hook.sh --self-test` after installing
   jaq and ruff.

2. **Fix placeholder values**: Update pyproject.toml name,
   package.json license/author/main, LICENSE copyright year.

3. **Add Linux install instructions**: Provide apt-get, cargo,
   and/or binary download commands alongside brew commands in
   SETUP.md.

### P1 (Near-term improvements)

4. **Write Python tests or remove test infrastructure**: Either
   add meaningful tests to `tests/unit/` or remove the empty
   directory and the pytest CI job to avoid false confidence.

5. **Integrate stress tests into CI**: Add
   `tests/stress/run_stress_tests.sh` as a CI job with all
   dependencies installed.

6. **Create `make setup` target**: Detect platform, install
   dependencies, run `uv sync`, and verify installation.

7. **Document the stress test suite**: Add a mention in
   README.md and a section in REFERENCE.md.

### P2 (Quality improvements)

8. **Add `CONTRIBUTING.md`**: Document the development workflow,
   testing requirements, and ADR process.

9. **Create a Plankton-specific JSON schema** for config.json
   to enable IDE validation.

10. **Schedule the hook schema migration**: The `decision` field
    deprecation is acknowledged. Create a tracking issue for the
    atomic migration to `hookSpecificOutput.permissionDecision`.

11. **Clean up portable-hooks-template.md**: Remove or
    contextualize "Incide" references for the published repo.

---

## 8. Architecture Strengths Worth Preserving

1. **Three-phase design**: Format-collect-delegate is elegant
   and well-separated. The ~40-50% reduction from auto-formatting
   before subprocess delegation is a meaningful efficiency gain.

2. **Defense in depth for config protection**: PreToolUse
   blocking + Stop hook recovery + CLAUDE.md policy is a
   well-layered defense.

3. **Model routing**: Complexity-based model selection
   (haiku/sonnet/opus) is a genuinely novel approach to
   cost-optimizing subprocess delegation.

4. **Fail-open philosophy**: Missing tools degrade gracefully
   rather than blocking work. This is the right default for a
   development tool.

5. **ADR quality**: The decision documentation is publication-
   quality. Every non-obvious choice has a rationale, alternatives
   table, and risk assessment.

6. **Subprocess isolation**: Using `--settings` with
   `disableAllHooks` to prevent recursive hook invocation is
   clean, and the atomic `mktemp+mv` pattern for concurrent
   safety shows careful engineering.
