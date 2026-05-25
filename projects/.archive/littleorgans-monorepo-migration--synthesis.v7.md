---
title: littleorgans monorepo migration — synthesis of Claude and Codex parallel plans
type: project-plan-synthesis
tags: [littleorgans, monorepo, migration, moon, synthesis, decisions-queue]
summary: Two independent expert plans (Claude general-purpose + Codex project-planner) converged on the load-bearing decisions (single workspace, v0.8.0, ~/.lilo, clean slate, MIT mirrors) but diverged on six material structural questions. This synthesis lays out the convergence as locked, the divergence as Stuart-decisions, and surfaces gaps neither plan covered.
status: consensus-locked
source: synthesis + 5-phase warroom consensus
confidence: high
created: 2026-05-25
---

# littleorgans monorepo migration — synthesis

Two independent plans were produced in parallel:
- `~/.mdx/projects/littleorgans-monorepo-migration--claude.md` (general-purpose, Claude runtime, ~1180 lines, ~9000 words)
- `~/.mdx/projects/littleorgans-monorepo-migration--codex.md` (project-planner via warroom, Codex runtime, ~1003 lines, ~6500 words)

Both consumed the same brief, the same kubernetes layout research, the same direction doc, and the same on-disk sub-repo state. Neither saw the other's output.

This synthesis structures the result into three layers:
1. **Convergence** — locked decisions where both plans agree. Treat as foundation.
2. **Divergence** — six material disagreements with tradeoffs and a recommended call.
3. **Gaps** — items neither plan covered well; flagged for follow-up.

The numbered sections at the end mirror the brief's twelve required sections, recording the merged position per section.

---

## Decision Log

Snapshot timeline. Each row is a phase boundary committed to git. Source of truth for what is locked at what revision.

| Rev | Date | Phase | Resolutions |
|---|---|---|---|
| rev01 | 2026-05-25 | Phase 0 (orchestrator pre-pass) | **Q1/D5** `lilo-im-stub@0.1.1` confirmed published via `cargo search` → kept in published set (orphaning would violate monotonic-version rule). **d9** JSONL event log → kept as the file-vs-DB exception, both plans converged. **d12** `lilo` binary crate → published (canonical `cargo install lilo` path). **G1** `Cargo.lock` → committed at workspace root for reproducible binary builds. |
| rev02 | 2026-05-25 | Phase 1 LAYOUT (warroom `moe-synthesis-p1`, 1 block-resolution round per item) | **D1/Q2** Internal-crate location → **hierarchical** `internal/<substrate>/<role>/`, amended to `internal/session/{app, core, daemon, driver, store}/` (5 role subdirs, not 4) so every current session impl crate has an explicit destination. Catch by reviewer: initial 4-subdir proposal would have orphaned `sm-core`. **d10** `lilo-paths` → **kept as a separate published crate** with narrow v0.8.0 API: `LiloHome`, `LiloPaths`, `DaemonEndpoint`, `LILO_HOME` only. No legacy `RTM_*` / `SM_*` env-var leakage. Real cross-substrate seam is `sm-paths::rtmd_socket_path` re-exported by `sm-core`; that is what `lilo-paths::DaemonEndpoint` replaces. |
| rev03 | 2026-05-25 | Phase 2 BINARY (warroom `moe-synthesis-p2`, 1 block-resolution round on D2, S first-round on D3) | **D2/Q3** Daemon count → **single merged `lilod`, staged**. Phases 2–6 preserve `rmd` and `smd` as import scaffolding. Phase 7 introduces the compose entry at `internal/session/app/daemon.rs` (session = API server surface for `lilod.sock`). `internal/runtime/daemon/`, `internal/session/daemon/`, and `internal/identity/service/` expose **service factory APIs**; the compose entry wires `RuntimeService` + `SessionService` + `IdentityService` into one Tokio runtime, one socket at `~/.lilo/run/lilod.sock`, one pid file, one log file, one SQLite ownership plan, one coherent cancellation scope, an in-process `RuntimeRpc`-shaped runtime service boundary, and **identity gating fronts every `lilod.sock` RPC including operator namespace runtime commands** (no bypass). Acceptance (resolves Gap 4): in-process integration tests at `tests/integration/` asserting `session-spawn → identity-audit → runtime-kqueue → session-record` ordering AND merged Stop / Ctrl-C / SIGTERM shutdown ordering. **D3/Q4** Shim binary → **hidden subcommand**, no separate `lilo-shim` crate, no second installed binary. Shim impl lives at `internal/runtime/app/shim.rs` after Phase 6 app import. Daemon resolves via `std::env::current_exe()` and launches `[lilo, __runtime-shim, --session-id, <uuid>]`. Hidden command not shown in `lilo --help`. Bootstrap env narrowed to **`LILO_SOCKET_PATH` only** (replaces `RTM_SOCKET_PATH`); tests prove tmux and headless paths do not leak daemon env into the runtime. Real command/argv/env/cwd/optional shell resume still arrive through the `ShimLaunch → LaunchSpec` handoff. Shim remains a distinct child process for signal and lifecycle purposes; only the executable file is shared with `lilo`. |
| rev04 | 2026-05-25 | Phase 3 PUBLISHING (warroom `moe-synthesis-p3`, S first-round on both items) | **D4/Q5** `lilo-sm-core` / `lilo-sm-client` publication → **do not publish in v0.8.0**. Session-matters mirror is a source-and-binary mirror with no crates.io artifacts. `internal/session/core` stays `publish=false`. Promote a narrow session contract crate only when a concrete external consumer needs stable session types — no placeholder publishing, no core-only half-step. Evidence: today's `sm-core` is broad internal aggregation rather than a narrow public contract; sibling repos do not consume it; the mirror remains buildable through source path deps plus the published `lilo-rm-*` and `lilo-im-*` crates. **d11** release-plz tag format → **per-package `{{ package }}-v{{ version }}` tags managed by release-plz**, with the release workflow creating the top-level `v0.8.0` tag for the binary distribution **after** crate publication succeeds. Preserve `version_group` only for semantically coupled contract sets, starting with `rm-contract` for `lilo-rm-core` + `lilo-rm-client`. Do not use single-workspace-tag mode for crate publication. Evidence: today's `runtime-matters` and `identity-matters` release-plz configs already use package-version tags; the installed release-plz 0.3.158 **has no `update_workspace_version` field** (the Claude original proposal was based on a flag that does not exist); single tag mode requires disabling per-package tags and opting one package back in, which fights the tool. |
| rev05 | 2026-05-25 | Phase 4 REPO + VERBS + DATA (warroom `moe-synthesis-p4`, 1 block-resolution round per item, all three signed) | **D6/Q6** Old GitHub repos disposition → **rename-archive-recreate**. Freeze SHAs and push `pre-monorepo-2026-05-25` tags to each old repo. Rename each to `<name>-archive`, archive read-only, then create a fresh canonical-name repo for MIT mirror state. Mirror README generation must include a "Previous source history" link to `<name>-archive` because the GitHub redirect from the rename is **overridden** the moment a new repo takes the canonical name. **d7/Q7** Verb tree → **hybrid CLI**: kubectl-shaped user verbs + explicit operator namespaces. `lilo run` and `lilo create session` use the session API and **create session records**. `lilo runtime spawn` is **diagnostic raw runtime RPC access**, remains identity-gated, **does NOT create a session_record**, appears only in `lilo runtime status/events`, and is **NOT returned by `lilo get session`**. Tests assert these substrate-boundary semantics AND identity audit on both paths. **d8/Q8** Database → **one SQLite file** at `~/.lilo/data/lilo.db` derived from `LiloPaths` under `LILO_HOME`. Runtime, session, and identity are kept as **separate store modules** with substrate-prefixed tables and a shared `schema_migrations` registry keyed by `(substrate, migration_id)`. `RTM_DB_PATH`, `SM_DB_PATH`, and separate identity-audit defaults are deleted. Every `sqlx` and `rusqlite` connection opens with `journal_mode=WAL, busy_timeout=5000ms, synchronous=NORMAL, wal_autocheckpoint=1000`. Tests assert these PRAGMAs and concurrent writes without `SQLITE_BUSY`. `d9` JSONL remains the file exception. **New constraint surfaced: Phase 7 must separately lock transaction / recovery semantics for partial multi-store writes** (added to §10 risks as R11). |
| rev06 | 2026-05-25 | Phase 5 GAPS + DOCS — FINAL (warroom `moe-synthesis-p5`, 1 round on G2/G3/G5, 0 on Q10, **2 rounds on Q9** because Stuart prompted full-read of MAP.md mid-pass) | **G2** `.fmm.db` rebuild → fmm is local generated navigation state for the monorepo. After Phase 1 scaffold, initialize fmm at `littleorgans/littleorgans/` if config absent, then `fmm generate && fmm validate`. Active DB at `<monorepo>/.fmm.db`. Commit `.fmmrc.toml` (matches identity-matters precedent). Gitignore: `.fmm.db`, `.fmm.db-shm`, `.fmm.db-wal`. Regen triggers: file adds/deletes/moves, `Cargo.toml` / `pnpm-workspace.yaml` / `pyproject.toml` workspace-member changes, generated surface refreshes, structural review. Solo workflow: manual `fmm generate && fmm validate`; `fmm watch` only during larger refactors. Parent multi-root `.fmm.db` stays as migration planning aid until Phase 8 cleanup, then removed with old sibling repo dirs. **G3** Monorepo `CLAUDE.md` outline → 11 sections; top note: "follows global rules in `~/.claude/CLAUDE.md`, items below are monorepo-specific additions"; sections: (1) project identity and status, (2) migration drivers, (3) bounded contexts, (4) K8s mental model **post-monorepo** (`lilo` CLI = kubectl, `internal/session` = API server, `internal/runtime` = kubelet, identity = ServiceAccount+RBAC+audit, transport-matters = external out-of-scope observability, `lilod` composition after Phase 7), (5) repository layout, (6) command surface and substrate-boundary rule, (7) data and environment, (8) engineering standards (DRY, 700 LOC files, 150 LOC functions, fmm, context preservation), (9) build/test/generated surfaces, (10) release and mirrors, (11) closeout checklist. `AGENTS.md` is a symlink to `CLAUDE.md`. Per-substrate `CLAUDE.md` allowed only at `internal/<substrate>/CLAUDE.md` when root insufficient. **G5** `lilo-mirror-publish` SPEC outline → data-driven release gate at `tools/mirror-publish`; manifest has one `[[mirror]]` per substrate with `name`, `repo`, `paths`, `public_crates` (may be empty — session-matters case locked rev04), `binaries` (README/Release metadata only — cargo-dist builds `lilo` once in monorepo CI), `README source`, `changelog filter`, `previous_history_url`, `excludes`; outputs are deterministic staging dirs + rewritten Cargo workspace + filtered CHANGELOG + LICENSE + provenance + machine-readable report; Cargo workspace inheritance flattened; external public path deps → registry deps at release version; same-mirror public deps stay local; substrate-owned internal deps embedded only if manifest-selected; **cross-substrate internal deps are hard errors unless replaced by public contracts**; empty-`public_crates` mirrors rewrite `internal/session` deps to published `lilo-rm-*` and `lilo-im-*` registry crates; each mirror builds in isolation; dry-run never mutates remotes; apply refuses unless every registry dep is already on crates.io at the release version; force-push requires `previous_history_url` AND remote match; errors typed, no rollback. **Q9** `runtime-matters/MAP.md` + `PROJECT.md` → both merged into **one** curated `docs/architecture/runtime.md` (design-intent + contracts + diagrams + system shape + stable flows + crate map + task routing + fmm workflow). Do NOT create `docs/provenance/runtime-map.md`. Do NOT keep a second hand-maintained MAP.md. `docs/provenance/imported-repos.md` may mention PROJECT.md and untracked MAP.md existed at migration time. fmm-derived snapshot blocks (MAP.md line totals, exact line-number tables, High Leverage Files ranking) REMOVED from the durable doc; replaced with current fmm commands + regenerate-on-demand guidance. **Q10** Copyright entity → "Stuart Robinson" for v0.x. Root LICENSE: `Copyright (c) 2026 Stuart Robinson` under MIT. Mirror LICENSE files inherit the same text. Root `Cargo.toml` `[workspace.package] authors = ["Stuart Robinson"]`; published crates inherit or flatten to the same value when staged. Revisit at v1.0 if an LLC exists; if changed, update root LICENSE + workspace authors + published crate manifests + release-plz metadata + cargo-dist metadata + mirror templates **together** in one release-prep change. |
| rev07 | 2026-05-25 | Phase 6 R11 + clean-slate lock (warroom `moe-synthesis-p6`, **3 rounds on R11** — most-iterated phase) | **§7 Git history** → **clean slate** confirmed by Stuart (orchestrator pre-step, no warroom — both panes already converged). Provenance recorded in `docs/provenance/imported-repos.md`; old repos tagged `pre-monorepo-2026-05-25` before rename-archive per rev05 D6. **R11 Phase 7 transaction / recovery semantics** → **option-1 spine with phase-aware recovery around runtime side effects**. Phase 7 introduces one shared `LiloDb` backed by **one `sqlx::SqlitePool`** for all `lilod` SQLite state. `sm-store::SqliteStore`, `im-store::SqliteAuditSink`, and the AuditSink call surface **migrate from rusqlite to sqlx** so no lilod-internal store opens rusqlite directly. DB-only cross-substrate transitions use **one `BEGIN IMMEDIATE/COMMIT` in fixed order: identity audit row first, then substrate state rows**. No SQLite transaction is held across process launch, signal delivery, tmux, Docker, ShimReady wait, or d9 JSONL append. **Session-spawn** uses **tx A** (allow audit + `session_spawn_intents(pending)` + `runtime.lifecycle` Forking) → runtime side effect → **tx B** (insert `session.sessions` + update lifecycle Running + resolve intent atomically). **Raw `lilo runtime spawn`** writes no `session_spawn_intents` row and never creates a `session_record` — explicit DB-shape discriminator (closes reviewer's b5 block). `session-mail` is one audit+mail tx; `session-nudge` and `session-delete` use analogous pre-/post-side-effect phases. **d9 JSONL** remains the sole runtime event cursor of record, appended after SQLite commit from committed state, idempotent by `(session_id, event_kind)`, never commit authority. **Startup reconciliation** uses pending `session_spawn_intents` as the discriminator between session-backed pending spawn and raw runtime rows; abort / complete / preserve raw runtime state accordingly. **Single-writer WAL serialization is accepted at Stuart-scale; scale-out and multi-operator semantics are out of scope for v0.8.0** (closes b4). New table `session_spawn_intents` schema: `session_id PK, operation_id, status (pending|resolved|aborted), spawn_request_json, session_draft_json, created_at, updated_at, resolved_at, aborted_reason`. Reviewer caught 5 distinct blocks across 3 rounds: b1 (sm-store sqlx migration scope unstated), b2 (reconciliation matrix undefined), b3 (DB event cursor row conflicted with d9), b4 (scale claim missing), b5 (intent storage encoding unspecified). |

---

## 1. Convergence — the load-bearing decisions both plans made

| # | Decision | Notes |
|---|---|---|
| C1 | **Single Cargo workspace.** No workspace-of-workspaces. | ~15–20 crates is well below the threshold where multi-workspace pain emerges. |
| C2 | **One physical binary: `lilo`.** No separate `rtm` / `sm` / `im` installed binaries. | Driver #5 verbatim. K8s pattern 1 (thin-shell main). |
| C3 | **First monorepo version: `v0.8.0`.** All crates ship at `0.8.0` on cut day. | Beats `lilo-rm-*@0.7.1`; jumps `lilo-im-*` from 0.1.1 to 0.8.0 in one go; abolishes the dual-axis version model that exists today. |
| C4 | **Unified data root: `~/.lilo/`.** | `LILO_HOME` is the override env var. Old `RTM_HOME`, `SM_HOME`, `RTM_SOCKET_PATH` etc. are deleted, not aliased. Driver #4. |
| C5 | **Clean-slate git history**, with provenance tags pushed to old repos before archival. | `git filter-repo` merge is deferred-but-possible if Stuart changes his mind before Phase 1. |
| C6 | **Repo name: `github.com/littleorgans/littleorgans`** (private). | Direction doc decision #11. |
| C7 | **Reserve direction-doc dirs** (`apps/`, `packages/`, `helix/`, `products/`, `infrastructure/`, plus Python slot) as empty placeholders with README stubs. | Topology committed on day one; future migrations slot in without renaming. |
| C8 | **CLI framework: `clap` derive**, top-to-bottom. | Both plans converge on a single `Cli` enum with global flags (`--output`, `--verbose`) flattened in. |
| C9 | **Logging: `tracing` + `tracing-subscriber`** with env-filter. | `LILO_LOG` env var, JSON output gated by flag or TTY detection. |
| C10 | **Errors: `thiserror` at crate boundaries, `anyhow` at the binary edge.** | No workspace-wide error god-enum. |
| C11 | **`release-plz` for crate publishing**, `cargo-dist` for binary distribution. | Both flag release-plz workspace-version handling as something to validate in Phase 7/8. |
| C12 | **One workspace `CHANGELOG.md`** at root, generated by release-plz. Per-mirror CHANGELOGs are filtered views. |
| C13 | **Mirror policy: MIT, force-pushed on every release, no PRs accepted.** Mirror names keep the `-matters` suffix. | k8s pattern 17 (banner README). |
| C14 | **`schedule-matters` deferred.** Empty dir today, no daemon, no published crate. A thin placeholder is acceptable. |
| C15 | **Migration shape: ~8–9 phases.** Phase 0 = decision day, Phase 1 = scaffold-only, Phases 2–4 = per-substrate imports, then path cutover, daemon work, release plumbing. | Each phase decomposes into moe-local-batch items (4–8 per phase). |
| C16 | **Day-one PR ships an empty workspace** with `lilo --version` working and CI green. No source migration in PR 1. | Both plans agreed verbatim on this. |
| C17 | **Moon as orchestrator over Cargo.** Validate Rust toolchain behaviour in Phase 1. | If Moon's Rust support proves flaky, fall back to plain `cargo` + GH Actions and re-introduce Moon when TS lands. |
| C18 | **Old GitHub repos: tag at HEAD, then repurpose as MIT mirrors** (not delete). | Codex prefers in-place repurpose; Claude prefers rename-archive-then-recreate. See divergence D6. |
| C19 | **No backcompat for env vars, paths, or wire formats.** | Driver #4 + Stuart's standing preference. |
| C20 | **`xtask/` crate replaces `hack/` scripts.** | k8s pattern 10 (transfers cleanly). |
| C21 | **`lilo-mirror-publish` is novel work** and the highest-risk piece of the migration. Both plans flag it. | Mid-complexity Rust binary, ~800–1500 LOC. First production use is at v0.8.0 release. |

Twenty-one converged decisions. Take these as locked unless Stuart sees one to revisit.

---

## 2. Divergence — six material disagreements

Each row gives Claude's choice, Codex's choice, the tradeoff, and a recommended call.

### D1. Internal-crate location (the biggest structural decision)

| Plan | Choice |
|---|---|
| Claude | **Flat `crates/`** for everything. Internal crates drop `lilo-` prefix (e.g., `crates/rm-daemon/`, `crates/sm-daemon/`, `crates/im-stub/`). Publish status enforced by `publish = false`. |
| Codex | **Hierarchical split.** `crates/` holds public (published) crates only. Internal crates live under `internal/runtime/{app,daemon,launchers,platform,store}/`, `internal/session/{app,daemon,driver,store}/`, `internal/identity/service/`, `internal/schedule/`. |

**Tradeoff.** Claude's flat tree is simpler to navigate and matches what runtime-matters already does today. Codex's split makes the publish/no-publish boundary visually load-bearing and prevents accidental misclassification — you cannot publish from `internal/` because it is convention-enforced as well as Cargo-enforced.

**LOCKED rev02 (Phase 1 warroom consensus).** **Hierarchical split**, with one amendment from reviewer-blocked iteration: session needs **five** role subdirs, not four, because there are five non-paths session impl crates today (`sm-core`, `sm-cli`, `sm-daemon`, `sm-driver`, `sm-store`). Final shape:

```
internal/
├── runtime/{app, daemon, launchers, platform, store}/
├── session/{app, core, daemon, driver, store}/       # 5 subdirs — sm-core gets explicit home
├── identity/service/
└── schedule/README.md                                  # reserved, no crate yet
```

The convention is convention-enforced and Cargo-enforced: `internal/**/Cargo.toml` carries `publish = false`. CI gates this via the release-plz dry-run.

### D2. Number of daemons

| Plan | Choice |
|---|---|
| Claude | **Two daemons stay separate.** `rmd` and `smd` keep distinct process boundaries. `lilo daemon start` is sugar that spawns both as child processes. |
| Codex | **One daemon: `lilod`.** Runtime + Session + Identity services compose into one process listening on one socket at `~/.lilo/run/lilod.sock`. Phase 7 explicitly merges them. |

**Tradeoff.** Claude preserves the K8s mental-model alignment (kubelet vs apiserver+etcd are separate binaries in real K8s) and keeps a future host-vs-control-plane split open. Codex achieves a stronger driver-5 simplification: one process, one socket, one health check, one log file, one pid file.

**LOCKED rev03 (Phase 2 warroom consensus, 1 block-resolution round).** **Single merged `lilod`, staged.**

- **Phases 2–6** preserve `rmd` and `smd` as two separate processes. Imports stay incremental.
- **Phase 7** is the explicit merge. After it, one `lilod` process serves every substrate.

Compose-layer mechanics (added by reviewer block):

- Compose entry at `internal/session/app/daemon.rs` — session is the API server surface for `lilod.sock`, mirroring the kubectl mental model.
- `internal/runtime/daemon/`, `internal/session/daemon/`, and `internal/identity/service/` each expose a **service factory API** (e.g. `RuntimeService::build(ctx) -> Result<Self>`).
- The compose entry wires `RuntimeService` + `SessionService` + `IdentityService` into:
  - One Tokio runtime.
  - One socket at `~/.lilo/run/lilod.sock`.
  - One pid file at `~/.lilo/run/lilod.pid`.
  - One log file at `~/.lilo/logs/lilod.log`.
  - One SQLite ownership plan (per d8 in Phase 4).
  - One coherent cancellation scope.
  - An in-process `RuntimeRpc`-shaped runtime service boundary (today's wire is the seam; in-process it becomes a direct trait call).
- **Identity gating fronts every `lilod.sock` RPC**, including operator namespace runtime commands (`lilo runtime spawn|status|events|kill`). No bypass. Surface expansion is explicit.

Acceptance (this resolves Gap 4):

- In-process integration tests at `tests/integration/` asserting `session-spawn → identity-audit → runtime-kqueue → session-record` ordering.
- Shutdown ordering tests covering merged Stop, Ctrl-C, and SIGTERM.

### D3. The runtime shim

| Plan | Choice |
|---|---|
| Claude | **Own crate `crates/lilo-shim/`.** Separate published binary `lilo-shim`. Two installed binaries side by side. |
| Codex | **Hidden subcommand `lilo __runtime-shim --session-id=...`** dispatched inside the `lilo` binary via argv. Daemon execs `std::env::current_exe()` with that hidden command. One binary file, two operational roles. |

**Tradeoff.** Claude is more discoverable (separate binary). Codex hits driver #5 more strictly (one binary on disk, period).

**LOCKED rev03 (Phase 2 warroom, S first-round, no block).** **Hidden subcommand.** No separate `lilo-shim` crate, no second installed binary, no published shim package.

- Shim implementation lives at `internal/runtime/app/shim.rs` after the Phase 6 app import.
- Daemon resolves via `std::env::current_exe()` (already today's default in `rtm-daemon`) and launches `[lilo, __runtime-shim, --session-id, <uuid>]`.
- Hidden subcommand declared with `clap::hide = true` so it does not appear in `lilo --help`. Dispatched before ordinary user CLI handling (or via the hidden clap command with identical behaviour and help-snapshot coverage).
- Bootstrap env narrowed to **`LILO_SOCKET_PATH` only** (replaces today's `RTM_SOCKET_PATH`); `env_clear` is preserved. Tests prove both tmux and headless paths do not leak daemon env into the runtime child.
- Runtime's real command, argv, env, cwd, and optional shell resume continue to arrive through the existing `ShimLaunch → LaunchSpec` handoff. Wire contract preserved.
- Shim remains a distinct child process for signal and lifecycle purposes. Only the executable file is shared with `lilo`.

### D4. `lilo-sm-core` / `lilo-sm-client` public crates

| Plan | Choice |
|---|---|
| Claude | **Add both as new published crates** parallel to `lilo-rm-*`. Symmetric mirror story up front. |
| Codex | **Don't add yet.** No concrete external consumer. Keep session protocol internal until a real published need emerges. |

**Tradeoff.** Claude prepares the symmetric shape; Codex avoids publishing crates with no consumers (k8s pattern: "publish exactly what external consumers need, nothing more").

**LOCKED rev04 (Phase 3 warroom, S first-round).** **Do not publish `lilo-sm-core` or `lilo-sm-client` in v0.8.0.**

- `internal/session/core` stays `publish = false`.
- Session-matters mirror is a **source-and-binary mirror** with no crates.io artifacts (Codex §12 acknowledged this; consensus confirms).
- Promote a narrow session contract crate only when a concrete external consumer needs stable session types. No placeholder publishing. No core-only half-step.

Evidence the warroom gathered:

- Today's `sm-core` is a broad internal aggregation, not a narrow public contract crate.
- Sibling repos (runtime-matters, identity-matters) do not depend on it.
- The mirror remains buildable through source path deps plus the already-published `lilo-rm-*` and `lilo-im-*` crates.

### D5. `lilo-im-stub` publication status

| Plan | Choice |
|---|---|
| Claude | **Demote to internal** (`im-stub`, publish=false). |
| Codex | **Keep published.** Notes that `lilo-im-stub@0.1.1` is already on crates.io and treats all three `lilo-im-*` crates as public + monotonic. |

**Tradeoff.** Claude is cleaner long-term; Codex is more accurate about the current crates.io state. The brief listed `lilo-im-core@0.1.1` and `lilo-im-store@0.1.1` as published but **did not mention `lilo-im-stub@0.1.1`**.

**RESOLVED rev01.** `cargo search lilo-im-stub` confirmed `lilo-im-stub = "0.1.1"` is published. Per the monotonic-version rule the crate must be kept in the published set. The next publish from the monorepo bumps it to `0.8.0` along with the rest of the `lilo-im-*` line. Source-side organisation can still put it under `crates/lilo-im-stub/` with `publish = true`.

### D6. Old GitHub repos: archive vs in-place repurpose

| Plan | Choice |
|---|---|
| Claude | **Rename old repos** (e.g., `runtime-matters` → `runtime-matters-archive`), then archive the renamed repos. Create *new* repos at the canonical names to receive mirror state. |
| Codex | **In-place repurpose.** Push final source tag, add archive branch, then force-push generated mirror state to `main`. Same repo, new role. |

**Tradeoff.** Claude's rename-then-recreate preserves the old history at a discoverable URL (`runtime-matters-archive`). Codex's in-place is simpler and keeps the original URL canonical but writes the mirror force-push over the existing main branch.

**LOCKED rev05 (Phase 4 warroom, 1 block-resolution round).** **Rename-archive-recreate.**

- Freeze SHAs on each old repo and push the tag `pre-monorepo-2026-05-25` before any rename.
- Rename `github.com/littleorgans/{identity,runtime,session}-matters` to `{name}-matters-archive`, then archive (read-only) on the GitHub side.
- Create fresh canonical-name repos (`github.com/littleorgans/{identity,runtime,session}-matters`) to receive generated MIT mirror state.
- **Mirror README generation must include a "Previous source history" link to `<name>-archive`** — because the GitHub rename redirect is **overridden** the moment a new repo takes the canonical name. Without the explicit link, users have no path back to the pre-monorepo commit history.

The rev03 mechanic of creating the new repo immediately after the rename works fine: GitHub frees the original name as soon as the rename completes.

---

## 3. Smaller divergences

These six are real but lower-stakes than the above. Quick calls on each.

| # | Topic | Claude | Codex | Pick |
|---|---|---|---|---|
| d7 | Verb tree shape | Substrate-prefixed: `lilo rm spawn`, `lilo sm create session` | kubectl-shaped: `lilo run`, `lilo create session`, with `lilo runtime ...` for operator commands | **LOCKED rev05 (Phase 4 warroom).** Hybrid: kubectl-shaped user verbs + explicit operator namespaces. `lilo run` / `lilo create session` use the **session API** and **create session records**. `lilo runtime spawn` is **diagnostic raw runtime RPC access**, remains identity-gated, does **NOT** create a `session_record`, appears only in `lilo runtime status/events`, and is **NOT** returned by `lilo get session`. Tests assert these substrate-boundary semantics and identity audit on both paths. |
| d8 | Database files | Multiple sqlite files (`db/rm.sqlite`, `db/sm.sqlite`, `db/im-audit.sqlite`) | One sqlite file with substrate-prefixed tables | **LOCKED rev05 (Phase 4 warroom).** One file at `~/.lilo/data/lilo.db` derived from `LiloPaths`. Runtime/session/identity are separate store modules with substrate-prefixed tables; shared `schema_migrations` registry keyed by `(substrate, migration_id)`. Delete `RTM_DB_PATH`, `SM_DB_PATH`. Every connection: `journal_mode=WAL, busy_timeout=5000ms, synchronous=NORMAL, wal_autocheckpoint=1000`. Tests assert PRAGMAs + concurrent writes without `SQLITE_BUSY`. JSONL exception preserved per d9. **New Phase 7 constraint** (R11): transaction / recovery semantics for partial multi-store writes. |
| d9 | JSONL event log | Both keep it | Codex keeps it for runtime events; flags it as the only file-vs-DB exception | **LOCKED rev01.** Keep — append-only cursor model is proven; both plans converged. |
| d10 | `lilo-paths` crate | Folded into `lilo-common::paths` (Claude lean) | Separate `crates/lilo-paths/` crate | **LOCKED rev02.** Separate **published** crate with a narrow intentional v0.8.0 API: `LiloHome`, `LiloPaths`, `DaemonEndpoint`, `LILO_HOME` only. No legacy `RTM_*` / `SM_*` env-var leakage. The real cross-substrate seam being replaced is `sm-paths::rtmd_socket_path` re-exported by `sm-core` (not, as previously stated, a runtime dep of `lilo-rm-client` — that was a dev-dep only). Publishing it is a deliberate SemVer commitment; mirror repos can build against a stable path-resolution contract. |
| d11 | release-plz tag format | `v{{version}}` (one tag per release) | `{{package}}-v{{version}}` (per-package), plus separate top-level `v0.8.0` | **LOCKED rev04 (Phase 3 warroom).** Per-package `{{ package }}-v{{ version }}` managed by release-plz; release workflow creates the top-level `v0.8.0` tag for binary distribution **after** crate publication succeeds. Preserve `version_group` only for coupled contract sets (start with `rm-contract` for `lilo-rm-core` + `lilo-rm-client`). Evidence: installed release-plz 0.3.158 has no `update_workspace_version` field — the Claude single-tag proposal was based on a flag that does not exist. |
| d12 | `lilo` binary crate publication | Published (so `cargo install lilo` works) | Not explicitly addressed | **LOCKED rev01.** Publish — `cargo install lilo` is the canonical install path. |

---

## 4. Gaps — items neither plan covered well

Six things to think about now, before Phase 0 closes:

1. **`Cargo.lock` strategy.** **LOCKED rev01.** Commit `Cargo.lock` at workspace root. Binary crates benefit from reproducible builds.
2. **`.fmm.db` in the new monorepo.** **RESOLVED rev06 (Phase 5 warroom).** Initialize fmm at `littleorgans/littleorgans/` after Phase 1 scaffold (if `.fmmrc.toml` absent). Active DB at `<monorepo>/.fmm.db`. Commit `.fmmrc.toml` (identity-matters precedent); gitignore `.fmm.db`, `.fmm.db-shm`, `.fmm.db-wal`. Regen triggers: file adds/deletes/moves, workspace-manifest changes (`Cargo.toml`, `pnpm-workspace.yaml`, `pyproject.toml` members), generated surface refreshes, structural review. Solo workflow: manual `fmm generate && fmm validate`. `fmm watch` only during larger refactors. Parent multi-root `.fmm.db` stays as migration aid until Phase 8 cleanup, then removed with the sibling repo dirs.
3. **`CLAUDE.md` / `AGENTS.md` content for the monorepo.** **RESOLVED rev06 (Phase 5 warroom).** 11-section outline: top note (inherits `~/.claude/CLAUDE.md`); (1) project identity and status, (2) migration drivers, (3) bounded contexts, (4) K8s mental model post-monorepo (`lilo` CLI = kubectl, `internal/session` = API server, `internal/runtime` = kubelet, identity = ServiceAccount+RBAC+audit, transport-matters = external observability out-of-scope, `lilod` composition after Phase 7), (5) repository layout, (6) command surface + substrate-boundary rule, (7) data and environment, (8) engineering standards (DRY, 700/150 LOC, fmm, context preservation), (9) build/test/generated surfaces, (10) release and mirrors, (11) closeout checklist. `AGENTS.md` symlinks to `CLAUDE.md`. Per-substrate `CLAUDE.md` only at `internal/<substrate>/CLAUDE.md` when root is insufficient.
4. **Daemon-merge testing strategy (Codex Phase 7).** **RESOLVED rev03 (Phase 2 warroom).** In-process integration tests at `tests/integration/` spin up `RuntimeService + SessionService + IdentityService` in one process, exercise cross-service flows, and assert: (a) `session-spawn → identity-audit → runtime-kqueue → session-record` ordering, (b) merged Stop / Ctrl-C / SIGTERM shutdown ordering. Wired into Phase 7 acceptance criteria.
5. **`lilo-mirror-publish` contract.** **RESOLVED rev06 (Phase 5 warroom).** Manifest: `[[mirror]]` per substrate with `name`, `repo`, `paths`, `public_crates` (may be empty — session-matters), `binaries` (README/Release metadata only — cargo-dist builds `lilo` once), `README source`, `changelog filter`, `previous_history_url`, `excludes`. Outputs: deterministic staging dirs, rewritten Cargo workspace, README, filtered CHANGELOG, LICENSE, provenance metadata, machine-readable report. Cargo workspace inheritance flattened. External public path deps → registry deps at release version. Same-mirror public deps stay local. Substrate-owned internal deps embedded only if manifest-selected. Cross-substrate internal deps are hard errors unless replaced by public contracts. Empty-`public_crates` mirrors rewrite `internal/session` deps to published `lilo-rm-*` and `lilo-im-*` registry crates. Each mirror builds in isolation. Dry-run never mutates remotes. Apply refuses unless every registry dep is on crates.io at the release version; force-push requires `previous_history_url` AND remote match; errors typed; no rollback. Fixtures: dependency rewrites, workspace flattening, binaries metadata, empty `public_crates`, previous history links, dry-run safety, apply planning, registry publication preflight. Full SPEC lives at `tools/mirror-publish/SPEC.md` when implemented.
6. **`runtime-matters/MAP.md` + `PROJECT.md`** — **RESOLVED rev06 (Phase 5 warroom).** Both merged into one curated `docs/architecture/runtime.md` (design-intent + contracts + diagrams + system shape + stable flows + crate map + task routing + fmm workflow). Do not create `docs/provenance/runtime-map.md`. Do not keep a second hand-maintained MAP.md. `docs/provenance/imported-repos.md` may mention both existed at migration time. fmm-derived snapshot blocks (MAP.md line totals, exact line-number tables, High Leverage Files ranking) REMOVED from durable doc; replaced with fmm commands + regenerate-on-demand guidance.

---

## 5. Merged plan, by section

This is the consolidated answer per brief section, applying the convergences and divergence calls above. Bullet form; depth lives in the source plans.

### §1 Target directory layout

```
littleorgans/littleorgans/                  # the new private monorepo
├── Cargo.toml                              # one workspace
├── Cargo.lock                              # committed
├── rust-toolchain.toml                     # 1.90 + clippy + rustfmt
├── moon.yml                                # workspace-level Moon project
├── .moon/                                  # workspace.yml + toolchains.yml + tasks/{rust,typescript,python}.yml
├── release-plz.toml
├── README.md  CHANGELOG.md  LICENSE  CLAUDE.md  AGENTS.md → CLAUDE.md
├── crates/                                 # PUBLISHED crates only
│   ├── lilo/                               # the binary crate (published)
│   ├── lilo-common/
│   ├── lilo-paths/
│   ├── lilo-types/                         # cross-substrate base types (optional, see §2)
│   ├── lilo-rm-core/   lilo-rm-client/
│   ├── lilo-im-core/   lilo-im-store/  lilo-im-stub/  (stub TBD per D5)
│   └── lilo-client/                        # added when daemon merges (Phase 7)
├── internal/                               # NON-PUBLISHED, substrate-grouped (LOCKED rev02)
│   ├── runtime/{app, daemon, launchers, platform, store}/
│   ├── session/{app, core, daemon, driver, store}/   # core added rev02 — sm-core's home
│   ├── identity/service/
│   └── schedule/README.md                  # reserved, no crate yet
├── tools/
│   ├── xtask/
│   ├── mirror-publish/                     # the high-risk piece
│   └── schemas/                            # generated artifact outputs
├── tests/{e2e, integration}/
├── docs/
│   ├── architecture/{runtime, session, identity, daemon-composition}.md
│   ├── reference/{cli, mcp, data-layout}.md  (generated)
│   ├── mirrors/{identity,runtime,session}-matters.md
│   ├── provenance/imported-repos.md
│   └── adr/0001-monorepo-collapse.md
├── apps/{desktop, server, web}/            # RESERVED; README.md only
├── packages/                               # RESERVED for TS workspace
├── python/                                 # RESERVED for uv workspace
├── helix/                                  # RESERVED
├── products/  infrastructure/              # RESERVED for direction-doc future
├── pnpm-workspace.yaml  package.json       # RESERVED; activate when TS lands
├── pyproject.toml                          # RESERVED; activate when Python lands
├── justfile                                # convenience commands
└── .github/workflows/{pr, release, mirror-release}.yml
```

### §2 Cargo workspace shape

- One workspace. Resolver "3". Edition 2024. Rust 1.90.
- Public crates in `crates/` with `lilo-` prefix; all use `publish = true`.
- Internal crates in `internal/<substrate>/<role>/` with no `lilo-` prefix; all use `publish = false`.
- `version.workspace = true` across every member.
- `[workspace.dependencies]` is the single source of truth for third-party versions.
- `[workspace.metadata.dist]` carries the cargo-dist target list (Linux glibc + musl, macOS, both x86_64 + aarch64).
- pnpm workspace declared but empty until TS lands.

### §3 Binary surface

One binary: `lilo`. Multi-call dispatch.

- **User-facing verbs** (kubectl-shaped): `lilo run`, `lilo create session`, `lilo get session`, `lilo delete session`, `lilo label`, `lilo mail`, `lilo nudge`, `lilo capture`, `lilo logs`, `lilo wait`, `lilo mcp`.
- **Operator namespaces** (substrate-prefixed): `lilo runtime spawn|status|events|kill|doctor`, `lilo session ...` (raw), `lilo identity audit|whoami`. Identity gate applies to these too (LOCKED rev03).
- **Daemon**: `lilo daemon start|stop|status`. After Phase 7, one merged `lilod` process at `~/.lilo/run/lilod.sock`. Compose layer at `internal/session/app/daemon.rs`.
- **Hidden**: `lilo __runtime-shim --session-id <uuid>` (LOCKED rev03). Daemon resolves via `current_exe()` and execs argv `[lilo, __runtime-shim, --session-id, <uuid>]`. Bootstrap env `LILO_SOCKET_PATH` only. Shim impl at `internal/runtime/app/shim.rs`.
- `lilo doctor` aggregates per-substrate health.

`main()` is the thin shell per k8s pattern 1: ~30 LOC, dispatches into substrate `app` crates via `internal::*::app::run(args, ctx)`. The compose entry `internal/session/app/daemon.rs::run(cmd, ctx)` is the post-Phase-7 home for daemon composition.

### §4 Versioning model

- One workspace version. First monorepo release: **`v0.8.0`**. All crates publish at `0.8.0` on cut day.
- `release-plz.toml` with `git_tag_name = "{{ package }}-v{{ version }}"`; release workflow additionally creates a top-level `v0.8.0` tag for the binary release.
- (See merged plan §4 for the complete published-crate list, locked across rev01 and rev04.)
- New published crates added only when an external consumer appears. No `lilo-sm-*` published in v0.8.0.
- `cargo semver-checks` runs in the release gate per published crate.

### §5 `~/.lilo/` data layout

```
~/.lilo/
├── config/
│   ├── lilo.toml         # global daemon, output, runtime defaults
│   ├── namespaces.toml
│   └── agents/           # was ~/.agm
├── run/
│   ├── lilod.sock
│   └── lilod.pid
├── data/
│   ├── lilo.db           # one SQLite (WAL mode), substrate-prefixed tables
│   └── events/
│       └── runtime.jsonl # the append-only event cursor (preserved)
├── logs/
│   ├── lilod.log
│   ├── sessions/<session-id>.log
│   ├── runtimes/<session-id>/{shim.log, runtime.log}
│   └── mcp/
├── cache/{manifests, docker}/
└── tmp/
```

- `LILO_HOME` overrides root. `LILO_SOCKET_PATH`, `LILO_DB_PATH`, `LILO_LOG` for finer overrides.
- Old `RTM_*`, `SM_*`, `AGM_*` env vars are not honoured. `lilo doctor` warns if it sees them.
- No automatic migration from `~/.rtm/`, `~/.sm/`, `~/.agm/`. Release notes tell Stuart to stop old daemons and start fresh.

### §6 Unified standards

- clap derive top-to-bottom; hidden subcommands marked `hide = true`.
- One typed authored CLI/MCP registry under `tools/schemas/`; `xtask codegen` regenerates docs, snapshots, READMEs in one step.
- `thiserror` in lib crates, `anyhow` at binary boundary; shared `Diagnostic` type in `lilo-common` for stable JSON errors.
- `tracing` everywhere; daemon defaults JSON to file, CLI defaults human to stderr; `LILO_LOG` filter.
- `--output human|json` global flag, JSON output snapshot-tested.
- Exit codes: 0 success, 1 internal, 2 typed domain (not found etc.), 3 input validation, 4 daemon unavailable, 5 authz denied.
- One root `CHANGELOG.md`; per-mirror is filtered view.
- CI = GitHub Actions + Moon; three workflows (`pr.yml`, `release.yml`, `mirror-release.yml`).

### §7 Git history strategy

- **Clean slate.** LOCKED rev07 (Stuart-confirmed). Provenance recorded in `docs/provenance/imported-repos.md` (remotes, tags, final SHAs).
- Old repos tagged `pre-monorepo-2026-05-25` before any source migration.
- ~~Filter-repo merge remains an option~~ — option closed at rev07. No history preservation; mirror archives + crates.io tarballs + the `pre-monorepo-2026-05-25` tags carry forward whatever's needed.

### §8 Migration sequence

Nine phases (Codex's count; closer to lift-and-merge granularity):

0. **Decision day.** Confirm convergence locks, resolve six divergence calls, freeze SHAs.
1. **Scaffold.** Empty workspace, `lilo --version` works, CI green, no source migration. *One commit.*
2. **Identity import.** Move `lilo-im-*` to `crates/`, `internal/identity/service/`. ~1.4K LOC.
3. **Runtime contracts + client import.** Move `lilo-rm-core` + `lilo-rm-client` to `crates/`; `internal/runtime/{app,daemon,launchers,platform,store}/`. ~20K LOC.
4. **Session import.** Move session crates into `internal/session/`. Split `mcp_tools.rs` (700 LOC cap). ~17K LOC.
5. **`~/.lilo/` cutover.** Replace `rtm-paths` + `sm-paths` with `lilo-paths`; delete old env vars.
6. **Unified `lilo` command surface.** Move `rtm-cli` + `sm-cli` modules into `internal/{runtime,session}/app/`; implement top-level `lilo` command; hide shim subcommand.
7. **Compose one daemon.** Merge `rmd` + `smd` into `lilod`. RuntimeService + SessionService + IdentityService share one process and one socket. Critical-path architecture work.
8. **Release + mirror tooling.** Build `tools/mirror-publish`, GitHub Actions release cascade, mirror dry-runs.
9. **Cutover release.** Tag `v0.8.0`, publish crates, push mirrors, archive (rename) old repos.

Each phase decomposes into 4–8 moe-local-batch items per the existing workflow.

### §9 What ships first

PR 1 = Phase 1 alone. Verbatim from Codex's §9 with Claude's mechanics:

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans
mkdir littleorgans && cd littleorgans
git init -b main
# Create directory tree, Cargo.toml, rust-toolchain.toml, .moon/, justfile,
# crates/lilo with src/main.rs printing version, crates/lilo-common stub,
# crates/lilo-paths with LILO_HOME tests.
# .gitignore (Rust template), commit Cargo.lock.
# CI workflow.
cargo build --workspace && cargo test --workspace && cargo run --bin lilo -- --version
git add . && git commit -m "chore: scaffold littleorgans monorepo workspace"
gh repo create littleorgans/littleorgans --private --source=. --remote=origin --push
```

Exit criteria: green CI, `lilo --version` prints `0.8.0`, `lilo doctor --output json` returns a valid empty-state structure.

### §10 Risks and unknowns

Ten material risks (consolidating Claude §10 and Codex §10):

1. Moon's Rust support is young — validate in Phase 1.
2. `release-plz` workspace-version handling — dry-run before Phase 9.
3. `lilo-mirror-publish` is novel CI engineering — separate design pass before Phase 8.
4. Cross-substrate path-dep cycles — `cargo publish --dry-run` gate.
5. Phase 5 (`~/.lilo/` cutover) has no easy revert — tests/e2e must cover full lifecycle first.
6. Daemon merge (Phase 7) is real architecture work — in-process integration tests required.
7. `internal/` vs `crates/` boundary needs CI enforcement (no `internal/` crate accidentally getting `publish = true`).
8. `lilo-im-stub` publication status needs crates.io verification (D5 above).
9. Mirror force-push policy means commit history on mirrors resets every release — accept this.
10. `transport-matters` is out of scope but may share wire types with session-matters; audit during Phase 4.
11. **(R11, added rev05, RESOLVED rev07)** Phase 7 cross-substrate transaction / recovery semantics — **option-1 spine with phase-aware recovery around runtime side effects**.
    - One shared `LiloDb` backed by one `sqlx::SqlitePool` for all `lilod` SQLite state.
    - `sm-store::SqliteStore`, `im-store::SqliteAuditSink`, and the AuditSink call surface migrate from `rusqlite` to `sqlx`. No `lilod`-internal store opens rusqlite directly.
    - DB-only cross-substrate transitions: one `BEGIN IMMEDIATE/COMMIT` in fixed order (identity audit row first, then substrate state rows).
    - No SQLite transaction held across process launch, signal delivery, tmux, Docker, ShimReady wait, or d9 JSONL append.
    - Session-spawn is two-phase: **tx A** writes allow-audit + `session_spawn_intents(pending)` + lifecycle Forking → runtime side effect → **tx B** atomically inserts session row + updates lifecycle Running + resolves intent.
    - Raw `lilo runtime spawn` writes no `session_spawn_intents` row and never creates a `session_record` — this is the DB-shape discriminator between session-backed and raw paths.
    - `session-mail` is one audit+mail tx; `session-nudge` / `session-delete` use analogous pre-/post-side-effect phases.
    - d9 JSONL remains the sole event-cursor-of-record. Appended after SQLite commit. Idempotent by `(session_id, event_kind)`. Never commit authority.
    - Startup reconciliation uses pending `session_spawn_intents` as the session-backed-vs-raw discriminator; abort / complete / preserve raw runtime state accordingly.
    - **Single-writer WAL serialization is accepted at Stuart-scale. Scale-out and multi-operator semantics are out of scope for v0.8.0.**
    - New table schema: `session_spawn_intents(session_id PK, operation_id, status [pending|resolved|aborted], spawn_request_json, session_draft_json, created_at, updated_at, resolved_at, aborted_reason)`.

### §11 schedule-matters status

- Directory exists at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/`. Empty. Not a git repo.
- Design lives in Linear, not in code.
- Disposition: **placeholder `internal/schedule/README.md` only.** No crate, no daemon, no verbs.
- `lilo` does not expose a `sched` namespace yet.
- Cleanup: delete `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/` after Phase 9.

### §12 The four GitHub repos

- `github.com/littleorgans/identity-matters`: tag `pre-monorepo-2026-05-25`, rename to `identity-matters-archive`, archive. Create new `identity-matters` repo for mirror state.
- Same pattern for `runtime-matters` and `session-matters`.
- `schedule-matters`: no current repo, none needed at v0.8.0.
- Cascading release wiring per Codex §12 manifest shape (TOML-driven, data-not-shell):

```toml
[[mirror]]
name = "runtime-matters"
repo = "git@github.com:littleorgans/runtime-matters.git"
paths = ["crates/lilo-rm-core", "crates/lilo-rm-client", "internal/runtime", "docs/mirrors/runtime-matters.md", "LICENSE"]
public_crates = ["lilo-rm-core", "lilo-rm-client"]
binaries = ["lilo"]
```

The `lilo-mirror-publish` tool reads this manifest, stages the substrate, rewrites Cargo.toml workspace fields to concrete values, replaces path deps with crates.io registry deps at the release version, generates README + CHANGELOG, runs `cargo build` in the staged dir to prove buildability, then force-pushes to the mirror repo.

---

## 6. Decision queue for Stuart

In order of blocking impact:

| # | Question | Blocks | Recommendation |
|---|---|---|---|
| ~~Q1~~ | ~~Is `lilo-im-stub@0.1.1` actually published?~~ | ~~D5, §4 published crate list~~ | **RESOLVED rev01.** Yes, published. Kept in published set. |
| ~~Q2~~ | ~~Internal layout: flat vs hierarchical?~~ | ~~§1, §2, all phases~~ | **RESOLVED rev02 (Phase 1 warroom).** Hierarchical with 5-subdir session amendment. |
| ~~Q3~~ | ~~Daemon count: two or one merged?~~ | ~~§3, Phase 7~~ | **RESOLVED rev03 (Phase 2 warroom).** One merged `lilod`, staged. Compose at `internal/session/app/daemon.rs`. Identity gates all RPC. |
| ~~Q4~~ | ~~Shim binary: separate or hidden subcommand?~~ | ~~§3, §9~~ | **RESOLVED rev03 (Phase 2 warroom).** Hidden `lilo __runtime-shim`. Impl at `internal/runtime/app/shim.rs`. `LILO_SOCKET_PATH` only. |
| ~~Q5~~ | ~~Publish `lilo-sm-core` / `lilo-sm-client` now or wait?~~ | ~~§2, §4~~ | **RESOLVED rev04 (Phase 3 warroom).** Wait. Session-matters mirror is source-and-binary only. Promote when a real consumer appears. |
| ~~Q6~~ | ~~Old GitHub repos: rename-archive-recreate or in-place?~~ | ~~§12, Phase 9~~ | **RESOLVED rev05 (Phase 4 warroom).** Rename-archive-recreate. Mirror README links to `<name>-archive` to survive redirect override. |
| ~~Q7~~ | ~~Verb tree shape: substrate-prefixed or kubectl-shaped?~~ | ~~§3, §6~~ | **RESOLVED rev05 (Phase 4 warroom).** Hybrid with strict substrate-boundary semantics: `lilo run` creates session records; `lilo runtime spawn` does not. |
| ~~Q8~~ | ~~Database: multiple sqlite files or one DB?~~ | ~~§5, Phase 5/7~~ | **RESOLVED rev05 (Phase 4 warroom).** One `lilo.db`. PRAGMAs locked. New R11 risk on Phase 7 transaction semantics. |
| ~~Q9~~ | ~~Where does `runtime-matters/MAP.md` land?~~ | ~~Phase 0~~ | **RESOLVED rev06 (Phase 5 warroom).** Merged with PROJECT.md into `docs/architecture/runtime.md`. fmm snapshot data stripped. |
| ~~Q10~~ | ~~Copyright entity in LICENSE~~ | ~~Phase 1~~ | **RESOLVED rev06 (Phase 5 warroom).** `Copyright (c) 2026 Stuart Robinson` (MIT). Workspace `authors = ["Stuart Robinson"]`. Revisit at v1.0; if changed, update all metadata surfaces together. |

Eight of the ten can be decided in a single short conversation. Q1 is a single shell command. The rest are recommendations Stuart can either ratify or flip.

After Q1–Q10 are settled, Phase 1 (the scaffold PR) can ship. The brief decomposes cleanly into moe-local-batch items from there.

---

## 7. Process notes (meta-observations from running the panel)

Useful inputs for future MoE planning runs:

1. **The brief did the heavy lifting.** Twelve numbered required sections forced both agents into the same shape, which is what makes synthesis tractable. Free-form briefs would have produced incomparable artifacts.
2. **The k8s research grading table did real work.** Both plans cite the verdict + effort table directly. Pattern-by-pattern verdicts are more useful than narrative.
3. **The Claude side via `general-purpose` (Agent tool) produced a longer, more code-snippet-heavy plan.** The Codex side via warroom + `helioy-tools:project-planner` produced a tighter, more structured plan with clearer phase exit criteria. Both are valuable; the synthesis benefits from the contrast.
4. **The warroom routing avoided the 1M-context-tier wrapper failure** that blocked two attempts at the `codex:codex-rescue` subagent type. For future MoE-with-Codex runs, default to warroom infrastructure over Agent() subagents.
5. **The parallel-artifact pattern (no live collaboration) preserved real independence.** Neither plan references the other; the synthesis surfaces genuine disagreements rather than echoes.

End of synthesis.
