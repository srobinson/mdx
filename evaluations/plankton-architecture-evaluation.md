# Plankton Architecture Evaluation

**Date**: 2026-02-22
**Evaluator**: Claude Opus 4.6
**Codebase**: `/Users/alphab/Dev/LLM/DEV/plankton/`
**Commit**: `aefeb88` (main, clean)

---

## Executive Summary

Plankton is a real-time code quality enforcement framework for Claude Code,
implemented as a set of shell scripts that hook into Claude Code's lifecycle
events. It addresses a genuine gap in the agentic coding workflow: AI coding
agents do not reliably follow project-specific style rules, and worse, they
actively game linter configurations to make violations disappear rather
than fixing code. Plankton's response is structural enforcement at
write-time through a three-phase pipeline (auto-format, collect violations
as JSON, delegate fixes to Claude subprocesses), config file protection
via defense-in-depth, and package manager enforcement.

The project is ambitious, well-documented, and solves a real problem. It is
also early, monolithic, and tightly coupled to Claude Code's hook system.
The shell scripting choice is both its greatest constraint and its most
pragmatic asset. The template repo distribution model is the right call
for this stage, but the project will need to evolve toward a plugin or
installable package if it wants meaningful adoption.

**Overall assessment**: Strong concept, strong documentation, solid
implementation for a research-stage project. The architecture has clear
scaling limits that are already acknowledged. The biggest risk is not
technical debt but platform dependency: if Claude Code's hook API
changes, the entire system breaks with no migration path.

---

## 1. Architecture Assessment

### 1.1 Three-Phase Design

The format-collect-delegate pipeline is the core innovation and it works
well conceptually:

**Phase 1 (Auto-Format)**: Silent, fast, handles ~40-50% of issues. This
is the right instinct. Running `ruff format`, `shfmt`, `biome check --write`,
`taplo fmt`, and `markdownlint --fix` before collecting violations
dramatically reduces subprocess overhead. The 500ms target for Phase 1
is met easily by the Rust-based toolchain.

**Phase 2 (Violation Collection)**: Converts heterogeneous linter outputs
into a unified JSON schema (`{line, column, code, message, linter}`). This
normalization is well-designed. The schema is simple enough to be robust
but structured enough for the subprocess to act on. The fragile sed parsing
for yamllint, flake8, and markdownlint is a known technical debt but
the right pragmatic choice given that these tools lack native JSON output.

**Phase 3 (Subprocess Delegation + Verification)**: Spawning `claude -p`
with a targeted prompt, then re-running Phase 1+2 to verify, is the most
interesting architectural decision. It creates a two-tier problem-solving
system: cheap, focused Claude instances handle most violations, and only
intractable issues escalate to the main agent. The verification pass after
subprocess exit is critical and well-implemented.

**Critique**: The three phases run synchronously and block the main agent.
For simple files, the cycle completes in seconds. For complex files with
many violations routed to Opus, the blocking time can reach 25-30 seconds.
This is acknowledged as a deliberate trade-off, and I agree it is the
right one: 25 seconds of automated fixing saves minutes of manual
correction. But the blocking model will become painful at scale when
agents need to edit many files in sequence.

### 1.2 Shell Scripting as the Implementation Language

**Pros**:
- Zero runtime dependencies beyond the Unix shell. No Python venv, no
  Node runtime, no compilation step. This is a significant adoption
  advantage for a template repo.
- Shell is the natural language for orchestrating CLI tools. The hook
  scripts call `ruff`, `shellcheck`, `biome`, `jaq`, and `claude` as
  subprocesses. Shell does this natively; Python or TypeScript would
  add indirection.
- Claude Code's hook system expects command-type hooks to be executable
  scripts. Shell is the most direct implementation.
- Fail-open behavior (`command -v` checks, `|| true` guards) is
  idiomatic and simple in shell.

**Cons**:
- `multi_linter.sh` is 1,287 lines. This is past the complexity
  threshold where shell scripting becomes a maintenance liability. The
  script has grown to include config loading, JSON manipulation,
  session-scoped state management, model selection logic, subprocess
  spawning, and language-specific handlers for 8 file types. Each of
  these would be cleaner as a separate module.
- JSON manipulation via `jaq` piping is fragile and verbose. Building
  JSON arrays by concatenating strings (`echo "${collected_violations}"
  "${new_violations}" | jaq -s '.[0] + .[1]'`) works but is error-prone.
  Python's `json` module or TypeScript's native JSON handling would be
  more robust.
- Error handling in shell is crude. The `set -euo pipefail` preamble
  helps, but complex control flow (like the elif chains in the package
  manager hook) is hard to reason about and test.
- No type system. The violation schema is implicit. A Python dataclass
  or TypeScript interface would catch schema drift at development time.
- Testing is manual and relies on exit code checking. There is no
  mocking framework, no assertion library, no coverage tooling. The
  `test_hook.sh --self-test` suite is heroic given these constraints
  but it is fundamentally limited.

**Verdict**: Shell is the right choice for this stage of the project.
The adoption friction of requiring Python or Node for the hook
infrastructure itself would undermine the template repo model. But the
project is approaching the complexity ceiling of shell scripting. The
TODO item about splitting `multi_linter.sh` into per-hook-type files is
the correct next step. Beyond that, a migration to a thin shell dispatcher
that calls language-specific handlers (Python or TypeScript modules)
would be the right evolution.

### 1.3 The Monolithic multi_linter.sh

At 1,287 lines, `multi_linter.sh` does too much in one file:

- Configuration loading and parsing (lines 43-171)
- Biome detection and caching (lines 115-162)
- Delegation functions including subprocess spawning (lines 226-419)
- Phase 1 re-run functions (lines 421-492)
- Phase 2 re-run functions (lines 494-617)
- Full TypeScript handler with Semgrep, jscpd, nursery, SFC handling
  (lines 622-834)
- The main dispatch case statement for all 8 file types (lines 841-1229)
- Delegation and exit logic (lines 1231-1287)

The TypeScript handler alone is 212 lines with its own sub-handlers,
session-scoped helpers, and nursery validation. The Python handler
spans lines 855-1023 with 7 sub-phases (2a through 2g).

**Recommendation**: Split into:
- `lib/config.sh` -- configuration loading
- `lib/delegate.sh` -- subprocess spawning, model selection
- `handlers/python.sh`, `handlers/typescript.sh`, `handlers/shell.sh`,
  etc. -- per-language handlers
- `multi_linter.sh` -- thin dispatcher that sources the above

This is a structural change, not a rewrite. The existing code is clean
enough that extraction would be mechanical.

### 1.4 Config Protection as a First-Class Concern

This is one of Plankton's strongest design choices. The defense-in-depth
approach (PreToolUse blocking + Stop hook recovery with git diff) is
genuinely well-thought-out:

- **Layer 1 (PreToolUse)**: Blocks all Edit/Write operations to 14+
  protected config files and the entire `.claude/hooks/` directory.
  Returns `{"decision": "block"}` with a clear message. This fires on
  every Edit/Write and fast-paths non-protected files.
- **Layer 2 (Stop hook)**: Uses `git diff` at session end to catch
  anything that slipped through (e.g., user-approved overrides). Offers
  a three-way choice via AskUserQuestion: keep changes, restore, or
  show diff. Uses hash-based guard files to prevent re-prompting within
  a session.

The implementation is solid. The atomic `mktemp+mv` pattern for settings
file auto-creation, the SHA-256 content hashing for guard files, the
`stop_hook_active` loop prevention flag -- these show careful
engineering for edge cases.

**Critique**: The protected file list is hardcoded in three places
(config.json, protect_linter_configs.sh defaults, stop_config_guardian.sh
defaults). The config.json is authoritative, but the fallback defaults
in the two scripts are duplicated. A single source of truth would be
cleaner.

### 1.5 Model Routing Strategy

The haiku/sonnet/opus tiering is a smart cost and latency optimization:

| Tier | Trigger | Latency | Use Case |
| --- | --- | --- | --- |
| Haiku | Default (simple violations) | ~5s | F841, SC2034, DL3007 |
| Sonnet | Pattern match (C901, PLR*, PYD*, D*, MD*) | ~15s | Refactoring, docstrings |
| Opus | Pattern match (type-assertion) or >5 violations | ~25s | Complex types, volume |

The patterns are loaded dynamically from config.json, which is good for
extensibility. The volume threshold (default 5) triggering Opus is a
sensible heuristic: many simple violations together likely indicate a
systemic issue that benefits from more reasoning.

**Critique**: The model routing assumes Anthropic models. The README
acknowledges this as a TODO. This is a significant limitation for
adoption: teams using Claude Code with other model providers (Qwen,
Gemini, DeepSeek) cannot use subprocess delegation at all. The fix
is to expose a three-tier config (`fast_model`, `standard_model`,
`capable_model`) that users map to their provider's model IDs.

**Second critique**: The model name strings ("haiku", "sonnet", "opus")
are passed directly to `claude -p --model`. This couples the hook to
Claude Code's model alias resolution. If model naming conventions change
(as they have historically), the hook breaks silently (the subprocess
runs but on the wrong model tier).

### 1.6 The Boy Scout Rule

The enforcement approach via CLAUDE.md is clever: "When you edit a file
using Edit or Write operations, you accept responsibility for ALL linting
violations in that file - whether you introduced them or they were
pre-existing. There are no exceptions."

This works because CLAUDE.md instructions are read by the main agent at
session start and persist in context. The PostToolUse hook then
structurally enforces this by running linters on the entire file, not
just the diff.

**Limitation**: On large existing codebases, touching any file triggers
a cascade of pre-existing violations. The README acknowledges this
honestly: "For existing codebases, either customize config.json
extensively to start with a narrow rule set and widen it gradually."
This is the right advice, but the lack of a diff-only mode (lint only
changed lines) limits adoption on brownfield projects. A future
`boy_scout_mode: "file" | "diff"` config option would help.

---

## 2. Design Philosophy

### 2.1 "Enforcement, Not Suggestion"

The implementation delivers on this promise. The key differentiator from
pre-commit hooks and LSP diagnostics is structural: the agent cannot
proceed until violations are resolved. This is achieved through:

- PostToolUse hooks being synchronous (main agent is blocked)
- Exit code 2 feeding violation context back to the main agent
- Config protection preventing rule-weakening as an escape hatch
- Package manager enforcement blocking wrong tool usage before execution

The FAQ section makes the philosophical case well: LSP diagnostics are
advisory (Claude decides whether to fix them), Plankton hooks are
structural (Claude cannot bypass them). This is a genuine architectural
difference, not marketing.

**Where it falls short**: The subprocess delegation (Phase 3) has a
fail-soft design. If the subprocess times out, fails, or cannot fix
violations, the remaining count is reported to the main agent but does
not hard-block the session. Exit code 2 is "non-blocking" in Claude Code
terminology -- the agent sees the error but can choose to continue. True
enforcement would require the agent to be unable to proceed until
violations reach zero. This would be impractical (some linter false
positives are unfixable), but it means the "enforcement" claim has a
soft ceiling.

### 2.2 Template Repo Approach

Using GitHub's template repository mechanism is the right distribution
model for this stage:

- Users get a complete, working setup with one click
- All config files, hook scripts, linter configs, CI pipeline, and
  documentation are included
- Users customize by editing config.json and deleting languages they
  do not need
- No dependency on a package registry or installation script

**Limitation**: Template repos create a fork-once relationship. Users
do not receive upstream updates. When Plankton improves (new linter
support, bug fixes, performance improvements), template users must
manually merge changes. This is fine for early adopters who will
customize heavily, but it limits network effects. A Claude Code plugin
(installable via marketplace) or an npx-based installer would provide
better update semantics.

**The TODO for a Claude Code marketplace install is the right long-term
vision**. When Claude Code's plugin system matures, Plankton should be
installable as `claude plugin install plankton` with config generated
from a setup wizard.

### 2.3 Language Coverage: Depth vs Breadth

Eight languages with 20+ linters is impressive breadth:

| Language | Phase 1 (Format) | Phase 2 (Lint) | Depth |
| --- | --- | --- | --- |
| Python | ruff format + check --fix | ruff, ty, flake8-pydantic, vulture, bandit, flake8-async | Deep |
| TypeScript | biome check --write | biome lint, Semgrep, jscpd, oxlint (opt-in) | Deep |
| Shell | shfmt | shellcheck | Good |
| Markdown | markdownlint --fix | markdownlint | Good |
| YAML | (none) | yamllint (23 rules) | Good |
| Dockerfile | (none) | hadolint (max strictness) | Good |
| TOML | taplo fmt | taplo check | Adequate |
| JSON | jaq / biome format | jaq syntax check | Minimal |

Python and TypeScript have genuinely deep coverage with 7 and 4+ linters
respectively. Shell, YAML, Markdown, and Dockerfile each have a single
best-in-class tool with thorough configuration. TOML and JSON are
syntax-only.

**Assessment**: The breadth is appropriate for a template. Not every
project uses all 8 languages, and the graceful degradation (skip if
tool not installed) means unused languages add zero overhead. The depth
for Python is exceptional -- ruff + ty + pydantic + vulture + bandit +
async covers style, types, framework-specific validation, dead code,
security, and async patterns. TypeScript coverage is strong with biome
as the primary tool and Semgrep for security.

**Gap**: Go and Swift are mentioned as planned. Rust coverage would be
a natural fit given the toolchain's Rust heritage (ruff, biome, jaq,
taplo are all Rust).

### 2.4 Config-Driven Behavior

The `config.json` design is clean and well-organized:

- Language toggles (boolean or nested object for TypeScript)
- Protected file list (configurable, with sensible defaults)
- Exclusion patterns (tests, docs, .venv, etc.)
- Phase control (auto_format, subprocess_delegation)
- Subprocess config (timeout, model selection patterns)
- jscpd settings (threshold, scan dirs, advisory mode)
- Package manager enforcement (per-ecosystem toggle, allowed subcommands)

The fallback-to-defaults pattern (if config.json is missing, all features
are enabled) is the right default. The environment variable overrides
(`HOOK_SKIP_SUBPROCESS`, `HOOK_SUBPROCESS_TIMEOUT`, `HOOK_SKIP_PM`) provide
session-level escape hatches without editing config files.

**Critique**: The config file is not validated. A typo in a key name
(e.g., `"langauges"` instead of `"languages"`) silently falls through
to defaults. A JSON Schema reference is declared (`$schema`) but no
actual schema file exists for validation. Adding schema validation
(even just a `jaq` check at load time) would catch configuration errors
early.

---

## 3. Strategic Positioning

### 3.1 Comparison to Alternatives

| Tool | When It Runs | Enforcement | Fixes Issues? | Config Protection |
| --- | --- | --- | --- | --- |
| **Plankton** | Every write | Structural (blocks agent) | Yes (subprocess) | Yes (defense-in-depth) |
| pre-commit | At commit | Gate (blocks commit) | Some (--fix flags) | No |
| CI linting | At push/PR | Gate (blocks merge) | No | No |
| Editor plugins | At save | Advisory (shows squiggles) | Some (quick fixes) | No |
| Claude Code LSP | After edit | Advisory (agent decides) | Agent-dependent | No |

Plankton occupies a unique position: write-time enforcement with
automated fixing. Pre-commit is too late (errors accumulate through
the session). CI is much too late (entire PRs of violations). Editor
plugins are advisory. LSP diagnostics are advisory.

**The genuine innovation is the combination of:**
1. Intercepting at write-time (not commit-time)
2. Automated fixing via subprocess delegation (not just reporting)
3. Config protection preventing rule-gaming (unique to agentic context)
4. Model routing for cost efficiency (unique to LLM-based fixing)

### 3.2 The Problem Being Solved

The problem is real and well-articulated:

1. **The copy-paste loop**: Agent writes code, you commit, pre-commit
   finds 15 violations, you paste them back, agent fixes 12, you commit
   again, 3 more appear. This is a genuine pain point for anyone using
   AI coding agents daily.

2. **Rule-gaming behavior**: Agents modifying `.ruff.toml` or
   `biome.json` to make violations disappear. This is an underappreciated
   risk that Plankton addresses directly with config protection.

3. **Style drift**: Agents ignoring formatting conventions, naming rules,
   docstring standards. This is a universal problem with AI-generated code.

4. **Package manager inconsistency**: Agents defaulting to `pip install`
   and `npm install` instead of project-preferred `uv` and `bun`.

These are real problems that every serious Claude Code user encounters.

### 3.3 Market Timing

Claude Code hooks are new (launched late 2025). The hook API is still
evolving. Building a framework on top of an unstable API is risky.

**Too early?** Possibly for production-grade tooling. The README's
caution notice is appropriate: "Research project under active
development. APIs change without notice, hooks may break on CLI updates."

**But the timing is strategically excellent for:**
- Establishing patterns and best practices for hook-based enforcement
- Building a user base of early adopters who will provide feedback
- Demonstrating the category to Anthropic, which may incorporate
  patterns into the CLI itself
- First-mover advantage in a space that will inevitably be commoditized

The Karpathy quote in the README frames this well: hooks, MCP,
permissions, and tools constitute a new programmable layer. Plankton is
one of the first serious attempts to build enforcement infrastructure
on that layer.

### 3.4 Open-Source Strategy

MIT license, GitHub template repo, comprehensive documentation, issue
templates, CI pipeline. This is the right approach for an open-source
developer tool:

- Low adoption friction (one-click template, 3-step setup)
- MIT license removes any licensing concerns
- ADR-documented decision-making builds trust in the design
- The FAQ addresses skepticism directly and honestly

**Missing**: A CONTRIBUTING guide, a changelog, and release tags. These
matter for community building.

---

## 4. Scalability Concerns

### 4.1 Large Codebases

**File-level performance**: The hook processes one file at a time (the
file that was just edited). Phase 1 formatting is O(file size), not
O(codebase size). Phase 2 linting is also per-file for most linters
(ruff, shellcheck, biome, hadolint, yamllint). This scales well.

**Session-scoped tools**: jscpd and Semgrep are deferred until 3+ files
are edited, then scan configured directories. On large codebases, jscpd
scanning `src/` could take significant time. The advisory-only mode
(does not block) mitigates this.

**Subprocess blocking**: The main concern. On a large codebase, an agent
editing 50 files in a session means 50 potential subprocess invocations.
Each blocks the main agent for 5-25 seconds. In the worst case, that is
20+ minutes of blocking time. In practice, Phase 1 auto-formatting
handles most issues and many files pass with zero violations, so the
actual blocking time is much lower. But the worst case is real.

**Recommendation**: A "batch mode" that collects violations from multiple
files and delegates them in a single subprocess invocation would reduce
overhead for bulk edits. This would require buffering violations across
multiple PostToolUse firings, which the current synchronous model does
not support.

### 4.2 Performance Impact on Agent Workflow

For the common case (clean file after Phase 1 formatting), the overhead
is negligible: ~100ms for formatting + ~200ms for linting = ~300ms total.
The agent barely notices.

For files with violations requiring subprocess delegation:
- Haiku: ~5 seconds (simple fixes)
- Sonnet: ~15 seconds (refactoring)
- Opus: ~25 seconds (complex or many violations)

These are acceptable for individual files but accumulate over a session.
The model routing optimization is crucial: without it, every violation
would go to the most expensive model.

### 4.3 Adding New Languages/Linters

The architecture makes this straightforward:
1. Add a new case to the file extension dispatch
2. Implement Phase 1 (formatting) and Phase 2 (violation collection)
3. Add the language toggle to config.json
4. Add the linter config file to the protected list
5. Add tests to test_hook.sh

The unified violation schema (`{line, column, code, message, linter}`)
means new linters just need an output converter. The pattern is well-
established by the existing 8 language handlers.

**Friction point**: Each new language adds ~50-100 lines to the already
1,287-line multi_linter.sh. The per-file-type split recommended in
Section 1.3 becomes more urgent with each new language.

### 4.4 Team Adoption Challenges

**Onboarding friction**: The template repo requires installing multiple
tools (`jaq`, `ruff`, `uv`, optionally `shellcheck`, `shfmt`,
`yamllint`, `hadolint`, `taplo`, `markdownlint-cli2`, `biome`). The
SETUP.md documents this well, but the lack of an install wizard means
each team member must manually install tools. The planned install wizard
is the right solution.

**Brownfield adoption**: The Boy Scout Rule means touching any file in
an existing codebase triggers all its pre-existing violations. This is
intentional but creates a poor first experience. The config.json
`phases.subprocess_delegation: false` option (formatting-only mode) is
a good mitigation, but it should be more prominently documented as the
recommended starting point for existing codebases.

**CI alignment**: The `.pre-commit-config.yaml` and GitHub Actions CI
pipeline share linter configs with the hooks, which is well-designed.
Teams already using pre-commit will find the transition natural.

---

## 5. Critical Gaps and Risks

### 5.1 What Users Will Need

1. **Install wizard**: The README acknowledges this. A `./plankton init`
   script that detects the stack (Python version, Node presence,
   installed linters) and generates config.json would dramatically
   reduce adoption friction.

2. **Diff-only mode**: For brownfield adoption, linting only changed
   lines (using git diff) instead of the entire file would make the
   Boy Scout Rule less aggressive on first touch.

3. **Batch delegation**: Collecting violations across multiple files and
   delegating them in a single subprocess call would reduce blocking
   time for bulk edits.

4. **Metrics/dashboard**: Understanding how many violations Plankton
   catches, fixes, and escalates per session would help teams justify
   the overhead. The `HOOK_LOG_PM=1` pattern could be extended to all
   hooks.

5. **VS Code integration**: When the agent fixes violations via
   subprocess, the editor does not reflect the changes until the file
   is reloaded. A file watcher or VS Code extension that auto-reloads
   would improve the developer experience.

### 5.2 Platform Dependency Risk

**This is the biggest risk.** The entire system depends on Claude Code's
hook API, which is:
- Undocumented beyond blog posts and examples
- Not versioned or stability-guaranteed
- Subject to change without notice

Specific dependencies:
- `settings.json` hook registration format
- `PreToolUse`, `PostToolUse`, `Stop` lifecycle events
- stdin JSON schema (`tool_input.file_path`, `tool_input.command`)
- stdout JSON schema (`decision: approve/block`)
- Exit code semantics (0 = pass, 2 = non-blocking error)
- `stop_hook_active` flag for loop prevention
- `claude -p` subprocess CLI flags (`--settings`, `--allowedTools`,
  `--max-turns`, `--model`)

Any of these could change in a Claude Code CLI update. The project has
no mechanism to detect API changes, no compatibility matrix, and no
fallback behavior. The TODO item "need a strategy for surviving Claude
Code CLI updates without breaking" is the most important unresolved
architectural concern.

**Mitigation recommendation**: Version-pin the Claude Code CLI in the
template's documentation. Add a `claude --version` check at hook
startup that warns if the CLI version is outside a known-compatible
range. Maintain a compatibility matrix in the docs.

### 5.3 Architectural Debt

1. **Protected file list duplication**: Three sources of truth (config.json,
   protect_linter_configs.sh defaults, stop_config_guardian.sh defaults).
   Should be a single source.

2. **Fragile sed parsing**: yamllint, flake8, and markdownlint output
   parsing via sed regex. Any format change in these tools breaks
   violation collection. Mitigation: pin tool versions in documentation
   and add format-detection tests.

3. **Session state in /tmp**: PPID-scoped marker files for jscpd,
   Semgrep, biome path caching, and the stop hook guard file. These
   are ephemeral by design but can accumulate. A cleanup function at
   session end would be hygienic.

4. **No config validation**: Typos in config.json keys fail silently to
   defaults. A schema validation pass at load time would catch errors.

5. **Model name coupling**: "haiku", "sonnet", "opus" are passed
   directly to `claude -p --model`. These are not stable identifiers
   and may require updating as Anthropic releases new models.

6. **The `decision` field is deprecated**: The ADR for hook schema
   convention notes that `decision` is deprecated for PreToolUse hooks
   in favor of `hookSpecificOutput.permissionDecision`. Migration is
   needed but not yet executed.

---

## 6. Strengths

### 6.1 Genuinely Innovative

1. **Config protection as a first-class concern**: No other linting
   framework treats "agents will modify your linter configs" as a
   threat model. Plankton's two-layer defense (PreToolUse block + Stop
   hook recovery) is novel and addresses a real agentic coding risk.

2. **Subprocess delegation with model routing**: Using `claude -p` to
   spawn focused fix instances, with complexity-based model selection,
   is a genuinely new pattern. It creates a two-tier problem-solving
   system where cheap models handle easy fixes and expensive models
   handle hard ones. This is efficient token usage.

3. **Write-time enforcement**: Intercepting at the tool-call level
   (PostToolUse on Edit/Write) rather than at commit or CI time is the
   right granularity for agentic workflows. The agent gets immediate
   feedback, not delayed feedback.

4. **Package manager enforcement**: Blocking `pip install` in favor of
   `uv add` and `npm install` in favor of `bun add` at the command
   level is a practical innovation. The configurable three-position
   model (block/warn/off) with per-tool allowlists is well-designed.

### 6.2 Well-Done

1. **Documentation quality**: The REFERENCE.md is exceptionally
   thorough. ASCII art architecture diagrams, message flow timelines,
   visibility models, configuration tables, testing guides. This is
   reference documentation that respects the reader's time while being
   comprehensive.

2. **ADR discipline**: The `docs/specs/` directory contains Architecture
   Decision Records for major design choices (package manager enforcement,
   hook schema convention, TypeScript expansion, integration testing).
   Each ADR includes context, alternatives considered, decision rationale,
   and consequences. This is mature engineering practice.

3. **Fail-open design**: Every hook defaults to approval if something
   goes wrong (jaq missing, config malformed, JSON parse error). A
   broken enforcement hook must never block all operations. This
   principle is applied consistently.

4. **Test infrastructure**: 103 integration tests across 3 parallel
   agents, plus a self-test suite with ~100 cases covering all file
   types, model selection, config protection, TypeScript handling,
   package manager enforcement, compound commands, warn mode, debug
   mode, and missing-tool scenarios. For shell scripts, this is
   unusually thorough.

5. **Graceful degradation**: Every optional tool is checked with
   `command -v` and silently skipped if absent. Only `jaq` and `ruff`
   are required. This means a user installing Plankton gets immediate
   value from Python formatting/linting without installing 15 other
   tools.

6. **Configuration design**: The layered config approach (config.json
   for runtime behavior, env vars for session overrides, settings.json
   for hook registration) provides appropriate granularity. The
   TypeScript nested object config with sub-options is a clean extension
   of the boolean toggle pattern.

### 6.3 Differentiators from Alternatives

1. **vs pre-commit hooks**: Real-time enforcement at write-time, not
   commit-time. Automated fixing via subprocess, not just error
   reporting. Config protection.
2. **vs CI linting**: Same violations caught 10x earlier in the workflow.
   Fixes generated automatically, not left for the developer.
3. **vs editor plugins**: Structural enforcement (agent is blocked), not
   advisory diagnostics. Coverage of 8 languages with unified config.
4. **vs Claude Code LSP**: Covers style, complexity, security, dead
   code, Pydantic validation, async patterns, Dockerfile best
   practices, YAML strictness. LSP covers types and syntax only.
5. **vs prompting/CLAUDE.md alone**: Structural constraint that the
   model cannot bypass, not soft guidance that degrades over long
   sessions.

---

## 7. Recommendations

### 7.1 High Priority

1. **Split multi_linter.sh**: Extract per-language handlers and shared
   libraries into separate files. This is the single most impactful
   code quality improvement. Target: `lib/` directory with sourced
   scripts, `handlers/` directory with per-language files.

2. **Add config validation**: Validate config.json against a schema at
   load time. Warn on unknown keys. This prevents silent misconfiguration.

3. **Document Claude Code CLI compatibility**: Pin known-compatible CLI
   versions. Add a version check at hook startup. Maintain a compatibility
   matrix.

4. **Create an install wizard**: A `./plankton init` script that detects
   installed tools, prompts for language preferences, and generates
   config.json.

### 7.2 Medium Priority

5. **Abstract model names**: Replace hardcoded "haiku"/"sonnet"/"opus"
   with configurable three-tier model IDs in config.json. Support any
   model that Claude Code supports.

6. **Add diff-only mode**: For brownfield adoption, support linting only
   changed lines (via `git diff`) instead of the entire file. Controlled
   by a `boy_scout_mode` config option.

7. **Single source of truth for protected files**: Eliminate the default
   lists in protect_linter_configs.sh and stop_config_guardian.sh. Make
   config.json the only source, with a hardcoded minimum (the config
   files that must always be protected).

8. **Add a CONTRIBUTING guide and changelog**: These are table stakes
   for community adoption.

### 7.3 Long-Term

9. **Plugin distribution**: When Claude Code's plugin marketplace
   matures, package Plankton as an installable plugin with a setup
   wizard and update mechanism.

10. **Metrics and observability**: Extend the `HOOK_LOG_PM` pattern to
    all hooks. Track violations caught, fixed, escalated per session.
    Provide a session summary report.

11. **Batch delegation**: Collect violations across multiple file edits
    and delegate them in a single subprocess call to reduce blocking
    time.

12. **Benchmarking**: The TODO item about measuring LLM+Plankton vs
    LLM-alone is important for adoption. A controlled experiment
    showing violation reduction, time savings, and code quality
    improvement would be compelling evidence.

---

## 8. Final Assessment

Plankton is a well-conceived, well-documented, and solidly implemented
research project that addresses a genuine gap in the agentic coding
workflow. Its core insight -- that AI coding agents need structural
enforcement, not just advisory diagnostics -- is correct and
increasingly important as AI-assisted coding becomes mainstream.

The shell scripting implementation is pragmatic for this stage but is
approaching its complexity ceiling. The monolithic multi_linter.sh is the
most urgent technical debt. The platform dependency on Claude Code's
unstable hook API is the most serious strategic risk.

The project's strengths are its documentation quality, fail-open design
philosophy, defense-in-depth config protection, and the novel subprocess
delegation with model routing. These are genuinely innovative patterns
that the broader agentic coding ecosystem should learn from.

For adoption beyond early adopters, the project needs an install wizard,
diff-only mode for brownfield codebases, and a plugin distribution
mechanism. The template repo model is correct for now but will not scale
to broad adoption.

**Bottom line**: Plankton is doing the right thing at the right time in
the right way for its maturity stage. The architecture is sound, the
implementation is honest about its limitations, and the roadmap
priorities are correct. It deserves attention from anyone serious about
code quality in agentic workflows.
