---
title: teng-lin/notebooklm-py — senior-engineering review
type: research
tags: [notebooklm, python, rpc, reverse-engineering, claude-code-skill, agentic-skills, cli, batchexecute]
summary: Mature unofficial Python/CLI/skill for Google NotebookLM. Clean layered async client over reverse-engineered batchexecute RPC. Strong CI, narrow surface, strong agent-skill installer pattern.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# teng-lin/notebooklm-py

## Executive Summary

Unofficial async Python client, CLI, and Claude/Codex skill for Google NotebookLM. Drives the undocumented `batchexecute` RPC protocol with reverse-engineered method IDs. Project is healthy and active: 11,868 stars, 1,608 forks, MIT license, default branch `main`, last push 2026-04-21, 220 commits in the last 90 days, 8 releases in 4 months (v0.1.4 → v0.3.4).

`pyproject.toml:2` pins version `0.3.4`, "Beta" classifier, Python 3.10–3.14, lean runtime deps (httpx, click, rich) with optional `playwright` for browser login. CI matrix tests 3 OSes × 5 Python versions (`.github/workflows/test.yml:46`); coverage threshold is 70% in CI but `pyproject.toml:113` sets `fail_under = 90` locally.

## Architecture

Four-layer async stack (`CLAUDE.md:64`):

```
CLI (cli/, click)  →  Domain APIs (_*.py)  →  ClientCore (_core.py)  →  RPC (rpc/)
```

- `client.py:41` — `NotebookLMClient` wires eight namespaced sub-APIs (`notebooks`, `sources`, `artifacts`, `chat`, `research`, `notes`, `settings`, `sharing`) and exposes `from_storage()` plus `refresh_auth()`. Async context manager.
- `_core.py:81` — `ClientCore` owns the single `httpx.AsyncClient`, RPC dispatch, FIFO conversation cache (cap 100, `_core.py:32`), HTTP→typed exception mapping (rate limit, timeout, server, client), and a coordinated single-flight token refresh (`_core.py:354` uses an `asyncio.Lock` plus shared `Task` so concurrent callers join the same refresh).
- `rpc/types.py:6` — Endpoint constants and the `RPCMethod` str-enum that catalogs ~35 obfuscated method IDs (e.g. `wXbhsf`, `R7cb6c`). Single source of truth, mirrored in `docs/rpc-reference.md`.
- `rpc/encoder.py:13` — Triple-nested `[[[rpc_id, json_params, null, "generic"]]]` request encoding into form-encoded `f.req` body.
- `rpc/decoder.py:62` — Strips Google's `)]}'` anti-XSSI prefix, parses chunked responses, maps gRPC canonical codes to messages (`_GRPC_STATUS_MESSAGES`). Notably contains an `_ACCOUNT_MISMATCH_HINT` that deliberately avoids substrings used by `AUTH_ERROR_PATTERNS` in `_core.py:39` so NOT_FOUND errors don't trigger a redundant auth-refresh retry — issues #114, #294. That cross-module coupling is documented in the comment.
- `auth.py` — Cookie-based auth from a Playwright `storage_state.json`, supports a `MINIMUM_REQUIRED_COOKIES = {"SID"}` (`auth.py:46`), `ALLOWED_COOKIE_DOMAINS` plus a hand-curated `GOOGLE_REGIONAL_CCTLDS` frozenset of ~70 ccTLDs (`auth.py:64`) so SID cookies on regional domains work.
- `paths.py:7` — Profile-aware path resolver. `NOTEBOOKLM_HOME` and `NOTEBOOKLM_PROFILE` envs, `~/.notebooklm/profiles/<name>/{storage_state.json, context.json, browser_profile/}` layout with auto-migration of legacy flat layout. Unix dirs created `0o700` with explicit chmod for TOCTOU safety (`paths.py:111`).
- `cli/skill.py` — Multi-target skill installer; writes `SKILL.md` to `~/.claude/skills/notebooklm/` and `~/.agents/skills/notebooklm/`, stamps a version comment in frontmatter (`cli/skill.py:70`), supports `user|project` scopes, `install|status|uninstall|show` subcommands, version-mismatch detection (`cli/skill.py:200`).
- `cli/agent_templates.py:11` — Importer prefers repo-root `SKILL.md` when running from source checkout, falls back to packaged `notebooklm/data/SKILL.md` (force-included via `pyproject.toml:90`).

Test corpus is substantial: 89 test files, dedicated unit suites for encoder/decoder/auth, full CLI coverage, VCR-recorded fixtures, e2e marker, pytest-timeout safety net (60s, `pyproject.toml:99`).

## Quality Assessment

### Strengths

- **Disciplined RPC layer.** All obfuscated method IDs centralized in one enum (`rpc/types.py:11`), mirrored in human-readable `docs/rpc-reference.md`. Each row links back to the implementing module. Update path is obvious when Google changes IDs.
- **Single-flight auth refresh.** `_try_refresh_and_retry` (`_core.py:354`) coordinates concurrent failures onto a shared task. The lock holds only long enough to read/create the task; the await happens outside it. Senior-grade async hygiene.
- **HTTP-status to exception mapping.** `_core.py:246-326` discriminates 429/5xx/4xx/connect-timeout/timeout/connect-error and emits typed exceptions with `method_id` for diagnostics. `RateLimitError` extracts `Retry-After` (`_core.py:259`). No bare `RPCError`-everywhere.
- **Issue → code traceability.** The auth-pattern carve-out at `decoder.py:85` cites issues #114 and #294 in the source. Commit log shows tight feedback loops from PR review (`fix(decoder): address PR #295 review feedback`).
- **Skill install is idempotent and version-aware.** `add_version_comment` (`cli/skill.py:70`) embeds `<!-- notebooklm-py v{version} -->` in frontmatter. `status` warns on version drift. `uninstall` prunes empty parent dirs but stops at scope root (`cli/skill.py:82`).
- **Cross-platform care.** Windows gets a separate path-permission branch (`paths.py:104`) because Python 3.13 mode= applies restrictive ACLs. ProactorEventLoop fix for Windows Playwright login (CHANGELOG 0.3.2). CI matrix actually exercises Windows, macOS, Linux.
- **Profile model.** `NOTEBOOKLM_HOME` / `NOTEBOOKLM_PROFILE` / `NOTEBOOKLM_AUTH_JSON` env-var triad makes parallel-agent and CI use trivial. Legacy migration is automatic.
- **Coverage threshold of 70 in CI** (`.github/workflows/test.yml:86`) — pragmatic floor.

### Weaknesses

- **`_artifacts.py` is 2,478 lines and `types.py` is 1,277.** Above the ~700-line refactor threshold. Hand-rolled HTML-attribute scraping for quiz/flashcard JSON sits inside the same file (`_artifacts.py:71`). Splitting per artifact-type would help.
- **Several CLI modules cross 1k lines** (`cli/generate.py:1169`, `cli/session.py:1133`, `cli/source.py:902`). Click groups encourage monoliths.
- **CSRF/session extraction is regex-on-HTML** (`client.py:187`). Brittle by design; documented but no fallback.
- **Coverage drift.** Local config demands 90 (`pyproject.toml:113`); CI gate is 70. Easy to merge degraded suites.
- **No mypy strict on the whole tree.** `disallow_untyped_defs = false` (`pyproject.toml:119`); `tests/` excluded.
- **Conversation cache eviction is purely FIFO**, not LRU (`_core.py:451`). Hot conversations get evicted under churn.

### Notable Patterns

- **Sentinel-based config caching with mtime invalidation.** `paths.py:120` uses an `_UNSET` sentinel to distinguish "not cached" from "cached as None" — common-sense Python that most projects botch.
- **String enums for user-facing types** (`types.py:74`, `:100`) so `source.kind == "web_page"` and `source.kind == SourceType.WEB_PAGE` both work. Cuts the kind-string-vs-enum debate.
- **`UnknownTypeWarning`** (`types.py:64`) when the API returns codes not in the enum. Forward-compat without crashes.
- **Module-level `__getattr__` for deprecation warnings** (`__init__.py:218`) caches the resolved value in `globals()` to avoid duplicate warnings on repeated access. Clean.
- **Hatch fancy-pypi-readme substitutions** (`pyproject.toml:67`) rewrite relative doc links to version-tagged absolute URLs at build time, so the PyPI README stays accurate per release.
- **`force-include` of `SKILL.md` and `AGENTS.md` into `notebooklm/data/`** (`pyproject.toml:90`) — repo-root canonical files become package data, keeping a single source of truth.

## Engineering Grade: A−

Senior engineering throughout: layered architecture, typed exception taxonomy, cross-platform CI matrix, single-flight auth, profile-aware paths, principled skill installer. Held back from A by oversized artifact/CLI modules and the CI/local coverage-threshold drift. Best-in-class for "unofficial undocumented-API client."

## Relevance to Helioy

### context-matters (cm)

- **Profile model is directly portable.** `paths.py` `NOTEBOOKLM_HOME` / `NOTEBOOKLM_PROFILE` / legacy auto-migration is the same problem cm faces if it ever needs per-account or per-agent isolation. The "always set to `0o700`, chmod even if exists" TOCTOU defense (`paths.py:111`) is worth copying for any cm directory creation.
- **Single-flight refresh pattern** (`_core.py:354`) maps to any cm operation that must be deduplicated across concurrent callers (e.g., reindex, snapshot, rotate). Lock-around-task-creation, await-outside-lock is the right shape.
- **FIFO conversation cache → cm session/turn ledger.** `_core.py:438` is a minimal model for ephemeral session state if cm ever needs an in-process working memory.

### attention-matters (am)

- **Limited overlap on the geometric side.** The chat conversation cache is FIFO and string-based, no embeddings.
- **Salience signal opportunity.** `client.chat.ask` returns `AskResult` with references; piping those through `am_buffer` + `am_salient` could let am learn which NotebookLM answers were promoted to notes (via `--save-as-note`). That promotion event is a free salience label.

### knowledge-matters (graph-based, upcoming)

- **Mind-map generation produces hierarchical JSON** (`generate mind-map` → `download mind-map ./mindmap.json`). That is a ready-made graph ingestion source. Schema is whatever NotebookLM emits; would need a parser, but the export path is built and battle-tested.
- **Source/notebook/artifact/note relationships** form a small graph already (notebooks own sources and artifacts; chat refs back to source spans). Useful as a fixture for early knowledge-matters schema work.

### fmm

- **No AST or code-structure overlap.** notebooklm-py is a pure RPC client. Skip.

### markdown-matters / ~/.mdx

- **Report/study-guide artifacts download as Markdown.** Valid ingestion source for `~/.mdx`. CLI: `notebooklm download report ./out.md`.
- **Skill files are markdown with frontmatter.** `cli/skill.py:70` `add_version_comment` and the frontmatter-preserving split-on-`---` pattern is the same shape ~/.mdx already uses for research artifacts. No new lessons, but a confirmation.

### Helioy distribution / installer patterns

This is the highest-leverage section.

- **The skill installer is the cleanest reference implementation I've seen for Helioy's own plugin/skill distribution.** Key moves:
  - Multi-target dispatch (`TARGETS` dict at `cli/skill.py:21`) — `~/.claude/skills/<name>/SKILL.md` and `~/.agents/skills/<name>/SKILL.md` written in one pass.
  - `user` vs `project` scope flag (`cli/skill.py:25`) selects `Path.home()` or `Path.cwd()` as root.
  - Version stamp embedded in the skill body itself (`cli/skill.py:70`); `status` reads first 500 bytes (`cli/skill.py:48`) and warns on drift. No separate manifest needed.
  - `uninstall` prunes empty parent dirs but stops at scope root (`cli/skill.py:82`) — no accidental `rm -rf $HOME`.
  - `npx skills add teng-lin/notebooklm-py` route (`README.md:217`) as a parallel install path that just fetches `SKILL.md` from GitHub. Worth supporting in Helioy distribution.
  - **Repo-root SKILL.md is the canonical artifact**, packaged via `force-include` (`pyproject.toml:90`); CLI prefers repo-root when running from source checkout (`cli/agent_templates.py:29`). One file, three install routes. Helioy should copy this exact pattern for any plugin that ships a skill.
- **`scripts/check_rpc_health.py` and the nightly `rpc-health.yml` workflow** are a model for any Helioy component that depends on an unstable upstream — schedule a probe, alert on regression.

## Sources Consulted

- README.md, CLAUDE.md, AGENTS.md, SKILL.md (head)
- pyproject.toml, .github/workflows/test.yml
- src/notebooklm/__init__.py, client.py, _core.py, auth.py, paths.py, exceptions.py, types.py
- src/notebooklm/rpc/types.py, encoder.py, decoder.py
- src/notebooklm/cli/skill.py, agent_templates.py
- docs/rpc-development.md, rpc-reference.md, configuration.md
- CHANGELOG.md, gh release list, gh pr list, git log (90d)

## Open Questions

- How is the conversation cache invalidated on auth refresh? FIFO eviction is by capacity; stale-by-account is not modeled.
- `_artifacts.py` 2,478 lines — what's the actual cyclomatic peak? Likely the polling/wait helpers around `wait_for_completion`.
- The MCP server PR (#305) is open. If merged, NotebookLM becomes a first-class MCP citizen and Helioy could compose it directly via `mcp__plugin_*__notebooklm_*` tools without going through the CLI.
- Is there an upstream signal (a NotebookLM Workspace API or Drive API) that would replace `batchexecute` if Google ships official endpoints? Project survival depends on this.
