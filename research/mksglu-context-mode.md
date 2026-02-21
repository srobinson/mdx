---
title: mksglu/context-mode review for cm, mdm, helioy-plugins, fmm
type: research
tags: [github-review, context-mode, cm, mdm, helioy-plugins, fmm, fts5, bm25, mcp, sandbox-execution, elv2, typescript]
summary: 11k-star MCP plugin that sandboxes tool output and indexes it into FTS5/BM25 for on-demand retrieval. Different problem from cm. Carries strong primitives for mdm (FTS5 patterns) and helioy-plugins (multi-platform adapter detection, snapshot-as-table-of-contents).
status: active
source: github-researcher
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Stats

10,999 stars, 759 forks, 30 contributors, born 2026-02-23, last commit 2026-04-28 (active daily). Elastic License 2.0 — no SaaS-style hosting allowed, but local use and patterns are fine; code lifting requires contemplating the host-as-service clause and the share-alike posture. TypeScript primary (1.9 MB) with JS bundles (1.4 MB) and shell hooks. Packaging is a hybrid: npm package with `bin: context-mode`, MCP server (`server.bundle.mjs`, 513 KB esbuild output), Claude Code plugin (`.claude-plugin/`), OpenClaw extension, Pi extension, and shell-hook drop-ins. Single bundled CLI, no CI configs visible at root, vitest test suite, GitHub Discord community. The project optimises for shipping into 14 platforms (Claude Code, Gemini CLI, VS Code Copilot, OpenCode, Codex CLI, Cursor, Antigravity, Kiro, Kilo, Zed, JetBrains Copilot, Qwen, OpenClaw, Pi). HN #1 with 570+ points cited in README.

## Grade

**B**. Same band as graphify. The code quality is genuinely good (FTS5 BM25 with porter+trigram dual index, RRF fusion with proximity reranking, prepared-statement caching, FTS5 schema migration, mtime+sha-staleness checks for file-backed sources, byte-safe UTF-8 truncation). The conception is real and was thought through. Below B+ because the core "context window optimisation" thesis collides with cm without complementing it: cm is structured durable knowledge, context-mode is ephemeral per-session sandboxing of tool noise. Most of the bulk (executor, security policy, multi-platform adapters, hook scaffolding) is platform plumbing that does not transfer to Helioy.

## Primitives that transfer

1. **FTS5 dual-tokenizer + RRF fusion + proximity reranking + fuzzy levenshtein on a vocabulary table** for the markdown-matters/cm retrieval path. Two virtual tables `chunks` (porter unicode61) and `chunks_trigram` (trigram), fused via reciprocal rank, then reranked by token-position span (`spanProximity` style). Fuzzy correction runs against an insert-only `vocabulary` table with an LRU cache invalidated only on insert.
   - `src/store.ts:448-470` (dual-table schema), `src/store.ts:1168-1206` (`searchWithFallback`, RRF then fuzzy fallback), `src/store.ts:301-329` (proximity span), `src/store.ts:1023+` (`fuzzyCorrect` with LRU), `src/store.ts:48-62` (stopword set tuned for code/changelogs).
   - **Helioy landing target**: `markdown-matters` (`md_search`) — currently FTS5 single-tokenizer; lifting the porter+trigram fusion plus proximity reranking would lift recall on partial-match and typo cases without abandoning BM25. Same ideas could pressure-test cm's recall pipeline.

2. **Snapshot-as-table-of-contents pattern.** Compaction-safe session restore that writes structured XML sections (`<files>`, `<git>`, `<task_state>`, `<environment>`, `<subagents>`, `<skills>`, `<roles>`, `<intent>`) where each section contains a tiny natural summary plus a runnable `ctx_search(queries: [...], source: "session-events")` tool call. Zero inline truncation; full data lives in SQLite, snapshot is a pointer surface.
   - `src/session/snapshot.ts:1-15` (intent), `src/session/snapshot.ts:43-60` (`buildQueries` + `toolCall`), `src/session/snapshot.ts:63-112` (file section), `src/session/snapshot.ts:213-262` (`renderTaskState` reconstructing pending tasks from create+update event positional matching).
   - **Helioy landing target**: `attention-matters` and `cm`. AM already does identity-as-points; this is the orthogonal case of session-state-as-pointers. Helioy could emit a compaction snapshot whose body is am_query + cx_recall + md_search invocations rather than inline summaries. Same shape works for nancyr supervisor checkpoints.

3. **Multi-platform adapter pattern with env-var-first detection and SHA-truncated project hashing.** `BaseAdapter` abstract class folds 12 platforms into one shared lifecycle (session dir, DB path = `sha256(projectDir).slice(0,16) + ".db"`, settings backup, events file path); concrete adapters override only what differs. Detection cascade: MCP `clientInfo.name` (high), env vars (high), config dir (medium), Claude Code fallback (low).
   - `src/adapters/base.ts:25-63` (15-line BaseAdapter with project-hash session paths), `src/adapters/detect.ts:33-44` (PLATFORM_ENV_VARS as single source of truth), `src/adapters/detect.ts:52-90` (detection priority).
   - **Helioy landing target**: `helioy-plugins`. When the plugin grows beyond Claude Code (Codex CLI, Cursor, OpenCode are realistic next targets), this BaseAdapter shape collapses the per-platform install+lifecycle code into ~20 lines of override per platform.

4. **Worktree-aware session isolation via git worktree porcelain.** Detects when CWD is not the main worktree, derives an 8-char SHA suffix from CWD, and namespaces the session DB. Falls back gracefully when git is unavailable. `CONTEXT_MODE_SESSION_SUFFIX` env override for CI.
   - `src/session/db.ts:28-59` (`getWorktreeSuffix`).
   - **Helioy landing target**: `cm` (scope_path resolution) and `helioy-bus` (per-worktree agent registries). Solves the same problem Stuart already hits when nancyr or helioy-bus run in two worktrees of the same repo and collide on shared SQLite paths.

## Does NOT transfer

1. **The core thesis (sandbox tool output, retrieve via search) collides with cm rather than complementing it.** cm's job is durable structured knowledge across sessions; context-mode's job is making one session's raw `gh issue list` output disappear from the window. The retrieval surface is BM25 over ephemeral chunks. Building this into cm would dilute cm's storage policy. If Helioy wants this primitive, it belongs in mdm or as a separate ephemeral-cache tool, not in cm.

2. **The PolyglotExecutor and 11-language runtime detection** (`src/executor.ts`, `src/runtime.ts:1-160`). Useful only for the "Think in Code" surface where the LLM writes a snippet and only stdout enters context. Helioy does not have an equivalent surface; nancyr workers run code, not LLM-authored ad-hoc scripts. Off-mission.

3. **The bash deny-policy parser** (`src/security.ts:1-200`, glob-to-regex with colon vs space semantics, file-glob with `**`). Solves Claude-Code-permission-pattern interpretation. Helioy uses skills and the harness's own permission system; reimplementing this is reinventing settings.json semantics for no gain.

4. **Auto-memory search over `CLAUDE.md` and `<configDir>/memory/*.md`** (`src/search/auto-memory.ts:37-136`). Hard-codes the Claude Code memory layout. cm + am already cover this for Helioy and would not benefit from a parallel grep-of-CLAUDE.md path.

5. **Prose marketing surface (README.md is 64 KB, BENCHMARK.md, three PRD files at root, multiple "Used at Microsoft/Google/Meta" badges).** The 98% number is real for the benchmarked corpus but rests on summarisation of nginx logs and CSV files; do not adopt the rhetorical posture for Helioy.

6. **The "Think in Code" mandate prose** (`CLAUDE.md`, `skills/context-mode/SKILL.md`). It is a valid pattern but tightly coupled to `ctx_execute`. Helioy's caveman-output preference partially overlaps; copying the SKILL.md verbatim would import an opinionated Bash-whitelist that does not match Stuart's working style.

7. **Output compression rules ("Terse like caveman. Only fluff die.")** are already echoed in Stuart's anti-slop instructions; nothing new to lift.

## Verdict

**Borrow** (patterns only, ELv2-aware reimplementation). Three concrete pulls: dual-tokenizer FTS5 with RRF fusion into mdm, snapshot-as-table-of-contents into am/cm compaction surface, BaseAdapter+detection cascade into helioy-plugins.

## Why

Context-mode is a serious project solving a specific surface (raw tool-output flooding) that Helioy has not directly tackled. Most of its bulk is platform reach and ephemeral caching that the Helioy ecosystem either does not need or covers differently through cm and am. The retrieval engine and the snapshot pattern are the high-density bits, and both are reusable without lifting code or running into ELv2's hosted-service clause. The collision with cm's name is real but the conceptions diverge fast: cm is durable structured knowledge with kinds and scopes, context-mode is per-session BM25 over tool stdout. Reading their code is genuinely sharpening for the mdm retrieval path, which is the closest Helioy analogue.

## How to apply

- **mdm**: prototype a porter+trigram dual-index in markdown-matters. Add reciprocal rank fusion across the two tokenizers, then a proximity reranker (`spanProximity` from `src/store.ts:285-329` is ~50 lines of cleanly-implementable logic). Add a vocabulary table populated on insert and an LRU-cached `fuzzyCorrect` for typo-tolerance. Validate with the `claudex` SQLite-FTS5 lessons already in memory.
- **am + cm compaction support**: when the harness emits a compact event, generate a snapshot XML where each section ends in `am_query` / `cx_recall` / `md_search` calls instead of inline data. Pattern lifts cleanly from `src/session/snapshot.ts`. Tag this work as the second "snapshot" lesson alongside the existing project-attribution memory.
- **helioy-plugins**: when adding a second platform target, start by writing `BaseAdapter` (`src/adapters/base.ts:25-63` is the canonical 40-line shape) plus a `PLATFORM_ENV_VARS` constant; do not duplicate session-dir or settings-backup logic per platform. The MCP `clientInfo.name` detection at `src/adapters/detect.ts:54-66` is the highest-confidence signal and is free if you ship MCP servers.
- **cm + helioy-bus worktree isolation**: lift `getWorktreeSuffix` (`src/session/db.ts:28-59`) into the cm scope-path resolver so `repo:helioy` in a worktree gets a stable SHA-suffixed sub-scope without manual configuration.
- **Skip**: the executor, the bash policy parser, the auto-memory grep, the marketing copy, the SKILL.md mandate.

## Sources Consulted

- `README.md` (substance), `CLAUDE.md`, `BENCHMARK.md`, `LICENSE`
- `src/store.ts` (1722 lines, FTS5 schema and search pipeline)
- `src/search/unified.ts`, `src/search/auto-memory.ts`
- `src/session/db.ts`, `src/session/snapshot.ts`, `src/session/extract.ts`
- `src/adapters/base.ts`, `src/adapters/detect.ts`
- `src/executor.ts`, `src/runtime.ts`, `src/security.ts`
- `src/server.ts` (MCP tool surface, 11 tools registered)
- `skills/context-mode/SKILL.md`
- `package.json` (packaging shape)

## Open Questions

- How does context-mode's RRF rank fusion compare to mdm's current ranking when both run over the Helioy `~/.mdx` corpus? A bake-off on the existing claudex/notebooklm-py research files would settle whether the fusion approach materially lifts recall on Stuart's writing style.
- Does the snapshot-as-table-of-contents pattern survive harness compaction without help, or does the harness need a hook to inject the XML at the right point in the new context window? Worth testing before committing am or cm to emit one.
