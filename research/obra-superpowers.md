---
title: obra/superpowers — multi-harness skills plugin distributed via marketplaces, not via installer
type: research
tags: [installer, claude-code, codex, opencode, cursor, gemini, skills, hooks, multi-harness, packaging, version-management]
summary: Superpowers ships skills via per-harness marketplace/extension mechanisms; there is no unified shell installer. The interesting installer engineering is one shell session-start hook with three output formats, a JSON-driven version-bump script with drift detection, and a per-harness manifest folder pattern. Helioy's installer gap remains unsolved by this repo, but the version-drift tooling is directly transferable.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# obra/superpowers

## Snapshot

- **Repo**: https://github.com/obra/superpowers
- **Stars**: 168,686 (2026-04-27)
- **Forks**: 14,895
- **Created**: 2025-10-09 (~6.5 months old)
- **Latest release**: v5.0.7 (2026-03-31)
- **Author**: Jesse Vincent (@obra), with Drew Ritter as primary contributor (Jesse 48 commits, Drew 16 in last 50)
- **License**: MIT
- **Primary language**: Shell
- **Disk**: 1.8M (146 files excluding `.git`)
- **Skills LOC**: ~3,159 lines across 14 SKILL.md files plus references and scripts
- **Open issues**: 163. **Open + closed PRs**: 173. PR rejection rate explicitly stated as 94% in `CLAUDE.md:7`.
- **Top deps**: zero runtime dependencies. The OpenCode plugin is a single 112-line ESM file (`.opencode/plugins/superpowers.js`) using only Node builtins. The brainstorm server was de-vendored in v5.0.2 to remove Express/Chokidar/WebSocket and replace them with Node builtins (`RELEASE-NOTES.md:90-100`).
- **Engineering grade**: **B+**. Disciplined version-stamping tooling, careful per-platform quirk handling (Bash 5.3 heredoc hang, dash on Debian, MSYS2 PID lifecycle, Windows symlink fallbacks), and an explicit "zero third-party dependencies" stance. Loses ground because it has no unified installer at all (each platform delegates to its own marketplace), and the cross-platform polyglot wrapper (`hooks/run-hook.cmd`) is clever but fragile.

## What it does

Superpowers is a skills bundle: 14 markdown skills (TDD, brainstorming, writing-plans, subagent-driven-development, systematic-debugging, etc.) plus a SessionStart hook that injects a "you have superpowers" preamble into the very first turn of every session. The skills enforce a Socratic-spec → plan → subagent-driven-TDD workflow with two-stage review.

The repository is a polyglot plugin: the same `skills/` directory is consumed by Claude Code, Codex, Cursor, OpenCode, Gemini CLI, and Copilot CLI through six different surface manifests (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.opencode/plugins/superpowers.js`, `gemini-extension.json`, plus `AGENTS.md` symlinked to `CLAUDE.md`). Each platform discovers skills via its native mechanism. The repo's actual deliverable is the SKILL.md content; everything else is per-platform packaging.

## Architecture

```
.
├── skills/                  # Canonical content (14 SKILL.md, references, scripts)
├── hooks/                   # SessionStart bootstrap (one shell script, two JSON manifests, one polyglot cmd wrapper)
├── agents/                  # One agent definition (code-reviewer.md)
├── commands/                # Three slash commands (brainstorm, write-plan, execute-plan)
├── .claude-plugin/          # plugin.json + marketplace.json
├── .codex-plugin/           # plugin.json (mirrored to a separate fork repo via sync script)
├── .cursor-plugin/          # plugin.json (references hooks/hooks-cursor.json)
├── .opencode/               # INSTALL.md + plugins/superpowers.js (112 LOC ESM)
├── .codex/INSTALL.md        # symlink-based codex install instructions
├── gemini-extension.json    # one-line manifest pointing at GEMINI.md
├── GEMINI.md                # @imports skills/using-superpowers/SKILL.md
├── CLAUDE.md → AGENTS.md    # contributor guidelines, also doubles as agent context
├── package.json             # npm metadata for OpenCode "git+" install
├── .version-bump.json       # declared version-stamp targets (6 files)
└── scripts/
    ├── bump-version.sh      # version sync + drift detection + audit
    └── sync-to-codex-plugin.sh  # rsync-based mirror to prime-radiant-inc/openai-codex-plugins
```

Data flow at session start:

1. Harness loads its manifest (`.claude-plugin/plugin.json`, etc.).
2. Manifest declares a SessionStart/sessionStart hook (`hooks/hooks.json:5`, `hooks/hooks-cursor.json:4`).
3. Hook runs `hooks/run-hook.cmd session-start`. On Unix this is a polyglot bash script (lines 41-46); on Windows it's a `.cmd` batch file (lines 1-40) that finds Git Bash and reruns the same script.
4. `hooks/session-start` reads `skills/using-superpowers/SKILL.md`, JSON-escapes it via bash parameter substitution (lines 23-31), and emits one of three output shapes depending on environment variables (lines 46-55):
   - Cursor → `additional_context` (snake_case, top-level)
   - Claude Code without Copilot → `hookSpecificOutput.additionalContext` (nested)
   - Copilot CLI / others → `additionalContext` (top-level, SDK standard)
5. OpenCode bypasses hooks entirely and uses a JS plugin (`.opencode/plugins/superpowers.js:101-110`) that injects the same content into the first user message via the `experimental.chat.messages.transform` lifecycle.
6. Gemini uses `@`-imports in `GEMINI.md`, with no runtime hook at all.

Key structural decision: **canonical content lives once at `skills/`; surface manifests live in dotfile folders per harness**. There is no codegen and no central installer; each harness's plugin system pulls from the same tree. The single content source is what makes this scale to six harnesses.

## Install mechanics — DEEP

The headline finding is that **superpowers does not have a unified shell installer**. There is no `install.sh`, no `cli/install.py`, no `npm install -g superpowers`. Each harness has its own native plugin/extension mechanism, and superpowers ships per-harness manifests. The user types a different command per platform.

### Entry points per platform

| Harness | User command | Mechanism | Source |
|---|---|---|---|
| Claude Code (official) | `/plugin install superpowers@claude-plugins-official` | Anthropic marketplace | `README.md:38` |
| Claude Code (dev) | `/plugin marketplace add obra/superpowers-marketplace` then `/plugin install superpowers@superpowers-marketplace` | GitHub-hosted marketplace JSON | `README.md:48-54` |
| Codex CLI | `/plugins` then search "superpowers" | Codex plugin search | `README.md:62-68` |
| Codex (manual) | `git clone ...` + `ln -s ... ~/.agents/skills/superpowers` | symlink, native skill discovery | `.codex/INSTALL.md:11-19` |
| Cursor | `/add-plugin superpowers` | Cursor plugin marketplace | `README.md:84` |
| OpenCode | Add `"superpowers@git+https://github.com/obra/superpowers.git"` to `opencode.json` plugins array | OpenCode npm-style plugin loader | `.opencode/INSTALL.md:11-15` |
| Copilot CLI | `copilot plugin marketplace add obra/superpowers-marketplace` then install | Copilot's port of Claude marketplace format | `README.md:103-104` |
| Gemini | `gemini extensions install https://github.com/obra/superpowers` | Gemini CLI extension manager | `README.md:110` |

The "Quick Install" pattern in `docs/README.codex.md:7-11` is interesting: tell the agent to `Fetch and follow instructions from https://raw.githubusercontent.com/obra/superpowers/refs/heads/main/.codex/INSTALL.md`. This punts the install to the LLM agent itself. It is not a real installer; it is a prompt that asks the agent to read the same `git clone + ln -s` instructions a human would follow.

### Discovery of target assistants

There is **no discovery mechanism**. The user explicitly picks their harness and runs the corresponding incantation. The closest thing to runtime detection is `hooks/session-start:46-55`, which detects which harness is *currently running* by environment variable (`CURSOR_PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`, `COPILOT_CLI`) and emits the matching JSON shape, but this happens at session start, not at install time.

### Where artifacts get written

Different per platform, all user-scope:
- Codex manual: `~/.codex/superpowers/` (clone) and `~/.agents/skills/superpowers` (symlink) — `.codex/INSTALL.md:13-19`.
- OpenCode: nowhere on disk by the user. The plugin loader resolves the `git+https` URL and caches it internally. Skills are registered in-memory via `config.skills.paths.push(superpowersSkillsDir)` in `.opencode/plugins/superpowers.js:91-94`.
- Claude Code, Cursor, Copilot, Gemini: managed by the harness's plugin system, not by superpowers code.

No mode-bit handling. Hooks shipped with executable bits in git (`hooks/session-start`, `hooks/run-hook.cmd`, `scripts/*.sh`) and rely on git to preserve them. There is no `chmod +x` step in any install path.

### Version stamping, drift detection, status, uninstall

This is the **most transferable piece of engineering** in the repo. `scripts/bump-version.sh` plus `.version-bump.json` give them three commands:

- `bump-version.sh 5.0.8` — bumps all declared files using `jq` (lines 178-188).
- `bump-version.sh --check` — reports current version per declared file and flags drift if not all match (lines 56-92). Exit code is non-zero on drift.
- `bump-version.sh --audit` — runs `--check` plus a `grep -rn` for the canonical version string across the whole repo, excluding declared files and an excludes list, so it catches new version references that should have been added to `.version-bump.json` (lines 94-164).

The config drives everything. `.version-bump.json` declares six files (six different package manifests for six harnesses, plus `marketplace.json`'s nested `plugins.0.version`) with their JSON paths. The script supports nested paths via dotted-to-jq translation (lines 30-31). This is a **declarative version-stamp registry** that solves a real Helioy problem: keeping cm/am/fmm/markdown-matters/helioy-plugins versions in sync.

There is **no status command** ("am I installed?") and **no version drift detection at runtime**. The session-start hook does have **legacy detection**: if `~/.config/superpowers/skills` exists, it injects a warning message into the agent's first turn telling the user to migrate (`hooks/session-start:11-15`). That is the closest thing to "check current install state."

Uninstall: per-harness, documented inline. Codex: `rm ~/.agents/skills/superpowers` (`.codex/INSTALL.md:62-67`). OpenCode: remove the line from `opencode.json` (`.opencode/INSTALL.md:25-34`). Claude Code/Cursor: marketplace UI. **No automated uninstall script.**

### Update flow

- Codex manual: `cd ~/.codex/superpowers && git pull` (`.codex/INSTALL.md:53-58`). Symlink picks up changes instantly.
- OpenCode: restart the editor; the plugin loader re-fetches the git ref. Pin via `#v5.0.3` suffix (`.opencode/INSTALL.md:51-57`).
- Claude Code/Cursor/Copilot: marketplace handles updates.
- Gemini: `gemini extensions update superpowers` (`README.md:115`).

No diffing, no "would-overwrite" warnings, no force flags. The marketplace systems handle this transparently; manual installs trust git.

### Multi-target dispatch

**Single canonical source, multi-target manifests, no codegen.** `skills/` is the source of truth. Each harness reads the same directory through its own discovery mechanism. The six manifest files are each ~20-45 lines and are hand-maintained, kept in sync only by the version-bump script.

The one exception is `scripts/sync-to-codex-plugin.sh`, a 431-line bash script that mirrors the repo into a separate downstream fork (`prime-radiant-inc/openai-codex-plugins`). It uses `rsync --delete --delete-excluded` with an anchored excludes list (`scripts/sync-to-codex-plugin.sh:44-76`) — note the leading slashes ("Anchoring prevents that" comment, lines 41-43, where unanchored `scripts/` would falsely match `skills/brainstorming/scripts/`). It opens a PR via `gh pr create` and is deterministic by design ("running twice against the same upstream SHA produces PRs with identical diffs," lines 11-12). This is a **publishing pipeline**, not an installer.

Compared to notebooklm-py's "one canonical SKILL.md, multi-scope install": superpowers is **less ambitious on install** (no installer at all) and **more ambitious on canonical content** (one tree powers six harnesses via native plugin systems). Compared to graphify's missing-installer gap: superpowers has the same gap and explicitly punts to upstream marketplaces.

### Failure modes

- **Bash 5.3+ heredoc hang on macOS Homebrew bash**: discovered and worked around in v5.0.3 by replacing `cat <<EOF` with `printf` (`hooks/session-start:43-44`, issue #571).
- **Dash on Debian/Ubuntu**: `${BASH_SOURCE[0]:-$0}` is a bash-ism that breaks under dash (`/bin/sh`); fixed by using `$0` (`RELEASE-NOTES.md:85`, issue #553).
- **Windows path delimiter**: single-quoted `'${CLAUDE_PLUGIN_ROOT}'` in `hooks.json` fails on Windows cmd.exe and prevents expansion on Linux. Fixed with escaped double quotes (`RELEASE-NOTES.md:155-159`).
- **Windows symlink permissions**: install instructions explicitly use `mklink /J` (junctions) instead of symlinks (`.codex/INSTALL.md:24-26`), which works without Developer Mode.
- **Polyglot wrapper for Windows**: `hooks/run-hook.cmd` is a single file that's simultaneously a valid bash script and a valid Windows cmd batch file, achieved via the `: << 'CMDBLOCK'` shell idiom that hides the cmd.exe block from bash (`hooks/run-hook.cmd:1-46`).
- **Partial install / permission denied**: not handled. The marketplace systems are responsible. Manual symlink failures are the user's problem.
- **Conflicting existing config**: not handled. Each platform's plugin system handles its own conflicts.

### Idempotency

- OpenCode: `if (!config.skills.paths.includes(superpowersSkillsDir))` guard (`.opencode/plugins/superpowers.js:92`) plus a "first-user-message already injected" check (line 107).
- Codex symlink: `ln -s` is not idempotent; rerunning fails. The instructions say "Restart Codex" and don't address re-run.
- Bootstrap injection in OpenCode: explicit dedup via `firstUser.parts.some(p => p.type === 'text' && p.text.includes('EXTREMELY_IMPORTANT'))` (line 107).
- bump-version.sh: idempotent. Running with the current version is a no-op (jq writes the same value).

## Engineering signals

- **Tests**: `tests/` has seven directories. `tests/codex-plugin-sync/test-sync-to-codex-plugin.sh` is a real bash test harness with `assert_equals` / `assert_contains` / `assert_not_contains` helpers and uses fixture versions (`PACKAGE_VERSION="1.2.3"`, `MANIFEST_VERSION="9.8.7"`) to verify behavior. `tests/opencode/run-tests.sh` is a 164-line test runner with `--integration`, `--verbose`, `--test` flags and proper exit codes. CI integration not visible in `.github/` (no workflows directory present in the clone).
- **CI**: `.github/` contains only issue templates, PR template, and `FUNDING.yml`. No workflows. Tests are runnable locally but not gated on PRs.
- **Code-org discipline**: 14 skills, each in its own directory with optional `references/` and `scripts/`. Per agentskills.io spec (`RELEASE-NOTES.md:118-122`).
- **File-size discipline**: largest SKILL.md is `writing-skills/SKILL.md` at 655 lines; second is `test-driven-development/SKILL.md` at 371. The Helioy 700-line rule would flag `writing-skills`. Largest shell script is `sync-to-codex-plugin.sh` at 431 lines.
- **Documentation quality**: README is marketing-thin. `RELEASE-NOTES.md` is 58K, very detailed, includes issue numbers and contributor credits. `docs/` has per-platform README files (`docs/README.codex.md`, `docs/README.opencode.md`).
- **Error handling**: shell scripts uniformly use `set -euo pipefail`. Helpful error messages: `bump-version.sh:170-172` validates semver shape; `sync-to-codex-plugin.sh:164-176` runs preflight checks for `rsync`, `git`, `gh`, `python3`, `gh auth status`, upstream branch state, and uncommitted-changes warnings.
- **Security smells**: low. No secrets in repo, no `curl | bash` install, no eval. The `escape_for_json` function in `hooks/session-start:23-31` does manual JSON escaping in bash; correctness is not obvious but is comment-justified ("orders of magnitude faster than the character-by-character loop this replaces"). The OpenCode plugin reads `OPENCODE_CONFIG_DIR` and uses `path.resolve` to prevent traversal (`.opencode/plugins/superpowers.js:37-47`).
- **Contributor process**: `CLAUDE.md:7` openly states "94% PR rejection rate" and explicitly tells AI agents to push back on their human partners before submitting slop. PR template (`.github/PULL_REQUEST_TEMPLATE.md`) requires a problem statement, prior-art search, alternatives considered, and an "Existing PRs" checkbox.

## Distribution model

- **Velocity is content-driven, not packaging-driven.** 168K stars in 6.5 months is content virality (Jesse's blog post, Twitter, the `EXTREMELY_IMPORTANT` Skills disciplinarian frame). Compare graphify (35K in 24 days, packaging-driven). Superpowers benefits from the *Anthropic plugins marketplace* doing the distribution, not from a one-line installer that the repo provides.
- **Packaged through marketplaces, not curl-bash or brew.** Six different marketplace ecosystems each ship their own copy. The repo's only "package" artifact is `package.json` (6 lines) which exists solely so OpenCode's git-URL plugin loader can read the entry point.
- **Single primary author** (Jesse Vincent, 48/70 recent commits). Drew Ritter is a substantial second contributor (16/70). Three or four community drive-by contributors. Not a team project.
- **The mirror script is a publishing pipeline.** `scripts/sync-to-codex-plugin.sh` automates pushing a re-shaped copy into a different OpenAI-owned plugin index repo, with deterministic re-runs, bootstrap mode, dry-run mode, and PR creation. This is non-trivial release engineering.

## Comparison

| Axis | superpowers | graphify | notebooklm-py | DeepDiagram |
|---|---|---|---|---|
| Unified installer | None | None (the gap) | Single `cli/skill.py` with multi-target install | N/A |
| Canonical SKILL.md model | Yes (14 skills) | No | Yes (one canonical, multi-scope) | N/A |
| Version drift tooling | Yes (`bump-version.sh` + `.version-bump.json`) | Unknown | No | N/A |
| Per-harness manifests | Six (Claude/Codex/Cursor/OpenCode/Gemini/Copilot) | One | One | N/A |
| Install discovery | None | None | Probes paths | N/A |
| Always-on hooks | SessionStart only, one shell script with three output shapes | None | None | N/A |
| Idempotency | Partial (OpenCode yes, Codex no) | Unknown | Yes | N/A |
| Velocity driver | Content + marketplace | Packaging | Content | Demo |

Patterns superpowers has that the others don't:

- **JSON-driven version-stamp registry with audit grep.** The most transferable piece. Neither graphify nor notebooklm-py has this pattern.
- **One bash script with three JSON output shapes selected by env var.** The platform-detection block in `hooks/session-start:46-55` solves a problem Helioy will face the moment it tries to ship a single hook script across Claude Code, Codex, and Cursor.
- **Polyglot bash-and-cmd wrapper.** `hooks/run-hook.cmd` is one file that runs natively on Unix and Windows. Clever but probably not worth borrowing unless Windows support is a hard requirement.
- **Anchored rsync excludes.** `scripts/sync-to-codex-plugin.sh:41-44` explicitly comments why patterns must be anchored. Small detail, high signal of someone who has been bitten.

Patterns superpowers does **not** have that Helioy still needs:

- A single shell command that installs across all detected harnesses.
- Runtime "am I installed and at what version" status.
- Automated uninstall.
- Conflict detection on existing user config.

## Helioy takeaways (filtered)

Honest filter: most of what's visible here is per-harness packaging that Helioy will eventually have to write itself. Superpowers chose **marketplace delegation** over **shell installer**, which is a strategic split that does not match Helioy's stated goal. So most of the install lessons are lessons about what *not* to copy.

### Strong takeaways (worth borrowing)

1. **JSON-driven version-stamp registry.** `.version-bump.json` plus `scripts/bump-version.sh` directly solves a real Helioy problem: cm, am, fmm, markdown-matters, helioy-plugins, helioy-bus, nancyr all carry their own version strings in their own manifests. A single `helioy bump-version 0.4.0 --check --audit` script with declared paths is a 200-line port. Helioy installer sink. **High value.**

2. **One hook script, three JSON output shapes, env-var dispatch.** `hooks/session-start:46-55` shows that *a single bash script* can serve Claude Code, Cursor, and Copilot CLI by emitting different JSON wrappers around the same content. If Helioy's installer writes hooks for multiple harnesses, the hook *body* can be one script and the *manifest* shapes are the only thing that diverges. helioy-plugins sink. **High value.**

3. **Anchored exclude patterns in any rsync/find usage.** Trivial, but the lesson is "patterns like `scripts/` will match nested paths; anchor them." `scripts/sync-to-codex-plugin.sh:41-44`. Useful for any Helioy code that walks directories.

### Medium takeaways (consider but pressure-test)

4. **Per-harness manifest folder pattern: `.claude-plugin/`, `.codex-plugin/`, `.cursor-plugin/`, `.opencode/`.** Concrete answer to "where do I put the plugin manifest for harness X." Helioy's installer will need to write these exact paths. Treat the superpowers manifests as ground-truth examples of what each harness expects. helioy-plugins sink.

5. **Legacy-install detection emits a warning into the agent's first turn instead of failing.** `hooks/session-start:11-15`: if the legacy directory exists, the user gets a polite "please migrate" message via the LLM. This is a low-friction migration UX that Helioy could reuse when migrating cm storage formats or hook locations. helioy-plugins or installer sink.

### Weak / non-takeaways (explicitly excluded)

6. **The "tell the agent to fetch and follow INSTALL.md" pattern (`docs/README.codex.md:9`) is not an installer.** It is a prompt. Helioy users want a real one-shell-command installer; this pattern would be a regression for us. Skip.

7. **Polyglot bash-and-cmd wrapper (`hooks/run-hook.cmd`)** is impressive but Helioy does not currently target Windows. Skip until Windows is on the roadmap.

8. **Marketplace delegation as distribution strategy.** Superpowers gets distribution from Anthropic's official Claude marketplace. Helioy is private/personal infrastructure; marketplace delegation does not apply. Different game.

9. **The 431-line sync-to-codex-plugin.sh.** This is solving a different problem (publishing an embedded copy into someone else's plugin index repo). Helioy does not need this. Skip.

10. **Skill content design** (the EXTREMELY_IMPORTANT framing, the 1% rule, Red Flags tables, "your human partner" terminology). Useful as inspiration for cm/am instruction prose if Helioy ever ships skills, but not load-bearing for the installer question. Out of scope for this review.

## Grade

**B+.** Disciplined version-stamp tooling, honest about the 94% PR rejection rate, careful per-platform quirk handling. The codebase is clean, dependency-free, and the polyglot wrapper plus three-shape JSON dispatch are real engineering. The project loses ground because it has no unified installer (the thing Stuart cares about) and explicitly punts to marketplace ecosystems. The skills content is excellent but is not the axis being evaluated.

Calibrated:
- DeepDiagram (C): demo-quality, not a packaging exemplar.
- graphify (B): packaging-driven velocity, but missing the installer.
- **superpowers (B+)**: version-stamp tooling and per-platform care, but no installer.
- notebooklm-py (A−): the actual installer pattern Helioy should study.

Superpowers' contribution to the Helioy installer question is one strong primitive (`.version-bump.json` + `bump-version.sh`) and one strong sub-pattern (env-var-dispatched hook output). It does **not** answer the "one shell command writes hooks for every harness" question. That question is still open after reading this repo.

## Sources consulted

- `README.md`
- `CLAUDE.md` and `AGENTS.md` (symlink)
- `RELEASE-NOTES.md` v5.0.7 through v5.0.1
- `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`
- `.codex-plugin/plugin.json`, `.codex/INSTALL.md`, `docs/README.codex.md`
- `.cursor-plugin/plugin.json`
- `.opencode/INSTALL.md`, `.opencode/plugins/superpowers.js`
- `gemini-extension.json`, `GEMINI.md`
- `hooks/hooks.json`, `hooks/hooks-cursor.json`, `hooks/session-start`, `hooks/run-hook.cmd`
- `scripts/bump-version.sh`, `scripts/sync-to-codex-plugin.sh`, `.version-bump.json`
- `package.json`
- `tests/codex-plugin-sync/test-sync-to-codex-plugin.sh`, `tests/opencode/run-tests.sh`
- `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`
- `skills/using-superpowers/SKILL.md` (sample skill structure)
- `git log` (commit history, contributor distribution)
- `gh repo view` for stars/forks/PR counts/release cadence

## Open questions

- Is there a private internal installer that Anthropic's marketplace uses to ingest the plugin? Not visible in this repo.
- Does Claude Code's official marketplace ingestion pipeline rewrite paths or run any post-install steps? Unknown from the public repo.
- How does the Gemini extension format compare to the Claude plugin format structurally? Not deeply explored here.
- The OpenCode `experimental.chat.messages.transform` hook is one of two such transforms in the JS plugin (`config` is the other); is there a stable equivalent in Claude Code's plugin API? Unknown.
