# PROJECT.md accuracy audit (Scout B)

- **Repo:** `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` on `main`
- **Subject:** `PROJECT.md` (title: `# transport-matters architecture`)
- **Compared to:** `TLDR.md`, `docs/ARCHITECTURE.md`, code under `api/src/transport_matters/`
- **Mode:** read only; no edits, moves, or git ops
- **Date:** 2026-08-02

## Summary

| Metric | Count |
| --- | ---: |
| Claims audited | 48 |
| ACCURATE | 36 |
| STALE | 7 |
| WRONG | 2 |
| UNVERIFIABLE / incomplete-but-true | 3 |
| Stale + wrong combined | **9** |

Headline: the capture-plane core (session correlation, LaunchProfile/TranscriptAdapter, storage↔session DAG, private import boundary, backfill, quality gates) is still largely true. Drift is concentrated in (1) the hard-coded `~/.transport-matters` path vs channel homes, (2) the wire-store “next substrate” wording, (3) runtime-home “known content lists remain explicit”, (4) an incomplete home-writer inventory, and (5) the DAG layer names `rules` / `pipeline` / `server` vs packages that actually exist.

---

## 1. CLAIM AUDIT

Verdicts: **ACCURATE** | **STALE** | **WRONG** | **UNVERIFIABLE**. Cite paths and symbols, not line numbers.

### Opening (title through retired-surfaces paragraph)

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Product has two active halves (live proxy path + Postgres session store) sharing one capture path | **ACCURATE** | Proxy path via `addon_runtime.load_runtime` / `load_capture_runtime`; session store under `session/`; shared capture in `shared_proxy/core.py` |
| Retired legacy index / block store / diff projection / raw fetch no longer active | **ACCURATE** | Matches `TLDR.md`; surviving `index/` is adapters + tailer + synth only (`index/adapters`, `index/tailer.py`, `index/sessions.py`) |
| Wire vs transcript “needs the next wire store rather than the deleted diff era substrate” | **STALE** | Wire store already rebuilt and ships dark: migration `api/migrations/versions/0008_wire_store.py`, writer `session/wire_store.py`, observer `wire_store_observer.py`. `TLDR.md` is current: writes exchanges/blobs, nothing reads them back. What remains is a **read surface**, not a new substrate |

### System model

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Agents launch via `transport-matters claude` / `codex`; proxy intercepts turns, parses IR, persists, optional breakpoint, forwards | **ACCURATE** | `cli/launch_profile.py`, `request_pipeline.py`, `breakpoint.py`, capture runtime |
| Workspace identity = canonical target path | **ACCURATE** | Workspace hashing under `workspace.py` / storage layout; same model as `TLDR.md` |
| Desktop can run `stable` and `preview` side by side; channel selects home, DB, ports, Electron identity | **ACCURATE** | `channel-specs.json` (`homeDir`, `databaseName`, ports, electron appId); `channel.py` |
| Transcript side owned by launch facts; tailer follows exact source, copies to run dir, normalizes, writes Postgres | **ACCURATE** | `storage/session_facts.py` (`sessions.json`), `storage/transcript_snapshot.py`, `index/tailer.py`, `session/ingest.py` |

### Layering and the import DAG

| Claim | Verdict | Evidence |
| --- | --- | --- |
| DAG: `ir -> adapters -> rules -> pipeline -> storage -> breakpoint -> server` | **ACCURATE** (names drift) | Same formula in `api/CLAUDE.md`. Physical map: `ir.py` → `adapters/` → **`overrides/`** (not a `rules/` package) → **`request_pipeline.py`** (module, not package) → `storage/` → `breakpoint.py` → **`api/`** as server. No `rules/` or `pipeline/` directory exists. Convention still holds; package names do not match the diagram |
| `ir.py` imports nothing from `transport_matters` | **ACCURATE** | Only `typing` + `pydantic` |
| `canonicalization.py` is layer 1, standard library only | **ACCURATE** | Imports: `hashlib`, `json`, `math`, `re`, `collections.abc`, `typing` |
| `session/` may import `ir`, `canonicalization`, surviving `index/{adapters,tailer,sessions}`, storage read helpers | **ACCURATE** incomplete | Also imports `harnesses.compatibility_facts` (`session/backfill.py`). `api/CLAUDE.md` already lists that extra; `PROJECT.md` does not |
| `storage` must never import `session` | **ACCURATE** | No matches under `storage/` for `transport_matters.session` |
| Runtime sinks injected at `load_runtime()` | **ACCURATE** | `addon_runtime.load_runtime` → `load_capture_runtime`; `make_transcript_snapshot_writer` injected; docstring in `storage/transcript_snapshot.py` states the same contract |
| Module privacy: leading `_` private; `test_private_import_boundary.py` enforces | **ACCURATE** | File at `api/src/transport_matters/test_private_import_boundary.py`; AST scan of non-test modules for private imports |

### Two captured streams

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Wire + transcript captured and never collapsed; wire to tier-1; transcript snapshot to tier-1 + session events to Postgres | **ACCURATE** | Tier-1 disk via `storage/disk*`; snapshot writer; `SessionWriter` |

### Tier 1 source of truth

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Path `~/.transport-matters/workspaces/{slug}/{hash}/{run}/` | **STALE** | Layout under channel home: `storage_roots.default_workspaces_root` → `default_storage_root()` → `resolve_channel_spec(...).home`. Homes: stable `.transport-matters`, preview `.transport-matters-preview`, dev `.transport-matters-dev` (`channel-specs.json`). Stable coincides with the documented path; other channels do not. Prefer `<channel home>/workspaces/...` as in `TLDR.md` |
| Per-exchange: `request.raw`, `request.ir.json`, `response.raw`, `response.ir.json`, curated request, audit metadata | **ACCURATE** incomplete | `storage/disk_layout.py` also names `request.curated.raw`, `request.curated.ir.json`, `request.audit.json`, plus `entry.json`, `transport.json`, `events.jsonl`, `turn.json`. PROJECT under-specifies the inventory without being false |
| `index.jsonl`, `transcripts/{session_id}.jsonl`, `sessions.json` | **ACCURATE** incomplete | Also `compatibility.json` (`DiskStorageLayout.compatibility_facts_path`) for historical adapter revision dispatch (S2e) |
| Run manifest is liveness beacon, unlinked on exit; durable enumeration globs `*/*/*/index.jsonl` | **ACCURATE** | Unlink: `launch/manifest.py` (`wslock.manifest_path.unlink()`). Glob: `session/backfill.py` `_RUN_INDEX_GLOB = "*/*/*/index.jsonl"`; `iter_run_dirs` |

### Session store

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Postgres; `SessionWriter` owns tailer + backfill writes; API owner-scoped reads + live events, no raw bytes | **ACCURATE** | Word-for-word also in `TLDR.md` |
| `index/tailer.py` cursor/offsets/parse/normalize; `session/ingest.py` event writes; `session/backfill.py` replays tier-1 snapshots | **ACCURATE** | Modules present as named |
| Surviving `index/` is compatibility namespace: adapters, tailing, synth; no DB/schema/block store/query/rebuild/raw route | **ACCURATE** | Package listing matches; no index-owned SQLite |

### Session correlation (specifically requested)

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Claude managed mint: launcher mints uuid, `claude --session-id <uuid>`, used directly with `minted=True` | **ACCURATE** | `ClaudeLaunchProfile` (`mints_session_id = True`, injects `--session-id`); `prepare_managed_session` mints `uuid4`; binding/`DIRECT_MINT_PROVIDERS` set `minted=True` |
| Codex: launcher mints native rollout uuid, pre-seeds, `codex resume <uuid>`; stored session id is uuid5 over owned native id with `minted=False` | **ACCURATE** | `CodexLaunchProfile` (`mints_session_id = False`); `seed_codex_session`; `index/sessions.synth_session_id` = `uuid5(SESSION_NS, f"{run_id}|{provider}|{native_session_id}")`; `wire_session_id` routes codex through synth |
| `--home-dir` / managed home carried in source descriptor | **ACCURATE** | Descriptor records `home_dir`; `SessionBinding.home_dir`; launch profile passes `home_dir` into prepare |

### Runtime home template materialization (specifically requested)

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Template mode is the only mode with explicit top-level materialization policy; native/manual catch-all symlink; proxy-only does not materialize | **ACCURATE** | `materialize_runtime_home_template_overlay` vs `materialize_runtime_home_overlay`; captured run paths |
| “Known content lists remain explicit, but unknown top level entries default to symlink include” | **WRONG** / **STALE** | Code has **no allowlist** of content names. `_symlink_template_content_entries` symlinks every entry **not** in copy ∪ local_writable ∪ credential ∪ reject (`home_overlay.py`). The Claude/Codex content name lists in PROJECT are narrative only; they are not enforced sets |
| Claude content names (`CLAUDE.md`, `agents`, …) / Codex content names (`AGENTS.md`, …) | **UNVERIFIABLE** as code lists | Appear only as documentation; tests may seed `CLAUDE.md` (`api/v1/test_capture_rpc_routes.py`) but policy is exclude-based |
| Template credentials rejected (Claude `.credentials.json` / account fields; Codex `auth.json` / auth-shaped `config.toml`) | **ACCURATE** | `validate_runtime_home_template`, `_validate_template_secret_free` |
| Generator ignore: `.git`, `runtime.toml` | **ACCURATE** | `home_constants._OVERLAY_NEVER_SYMLINK_NAMES` |
| **Writers list complete?** | **STALE** (incomplete) | Named writers still exist: `materialize_runtime_home_overlay`, `materialize_runtime_home_template_overlay`, `ClaudeSeeder.seed`, `_ensure_claude_skip_dangerous_prompt`, `apply_claude_proxy_env_settings`, `CodexSeeder.seed`, `_relocate_codex_hook_trust_state`, `_merge_codex_project_trust`, `seed_codex_session` (via `CodexLaunchProfile.prepare`). **Missing from PROJECT:** `cli/run_context.install_codex_run_context` (writes runtime `AGENTS.md` self-identity block; called from `cli/codex_cmd.py`) |
| Known Claude writable paths | **ACCURATE** (with nuance) | Code splits **copied** (`.claude.json`, `settings.json`) vs **local writable** (`_CLAUDE_TEMPLATE_LOCAL_WRITABLE_NAMES` + daemon names). PROJECT merges both into “writable”; membership matches. All listed names present in code sets |
| Known Codex writable paths | **ACCURATE** | `_CODEX_TEMPLATE_LOCAL_WRITABLE_NAMES` matches PROJECT’s list; PROJECT’s `goals_1.sqlite*` style wildcards expand in code to explicit `-shm`/`-wal` siblings |

### Launch and adapter ports

| Claim | Verdict | Evidence |
| --- | --- | --- |
| `LaunchProfile` per mint-capable CLI: prepare owned facts, inject id, honor user pin | **ACCURATE** | `cli/launch_profile.py`: ABC + `ClaudeLaunchProfile` + `CodexLaunchProfile`; `prepare_managed_session`; `HARNESSES` registry |
| `TranscriptAdapter` per provider: bind, locate, normalize | **ACCURATE** | `index/adapters/base.py` `TranscriptAdapter`; Claude/Codex adapters under `index/adapters/` |
| Single shared managed launch path; new CLI = one profile + one adapter | **ACCURATE** | Docstring and `prepare_managed_session` design |

### Backfill and replay

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Backfill is transcript only; reads `sessions.json` + owned snapshots; same event shape as live; no wire bytes | **ACCURATE** | `session/backfill.replay_transcript_run` docstring and body; raises without `compatibility.json` rather than guessing |
| Replay idempotent via deterministic event ids and cursor sequencing | **ACCURATE** (wording) | Events keyed by `(session_id, seq)` on `EventRow`, not a separate UUID `event_id`. Determinism is seq/cursor based (`index/record_ingest.py` `plan_ingest_records` / `apply_cursor_state`) |
| Snapshot write failure prevents cursor advance; events never ahead of owned copy | **ACCURATE** | `TranscriptSnapshotGapError` in `storage/transcript_snapshot.py`; gap raises so tailer does not advance past un-snapshotted bytes |

### Storage and runtime contracts

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Tier-1 authoritative; raw before derived observers | **ACCURATE** | Disk persist path + observer registration pattern |
| Session capture startup best-effort | **ACCURATE** | `load_capture_runtime` catches start failure → empty `SessionCaptureRuntime` |
| Transcript snapshots before event advance | **ACCURATE** | See snapshot gap rule above |
| Public APIs do not expose retired raw route; future raw needs wire store API | **ACCURATE** | Wire store write-only/dark; no public wire-raw read surface yet (`local-file/raw` is a different local-file helper, not exchange raw) |
| FastAPI machine-readable errors via exception translation | **ACCURATE** | `exceptions.py` + FastAPI layer (also in `api/CLAUDE.md`) |

### Engineering standards (specifically requested)

| Claim | Verdict | Evidence |
| --- | --- | --- |
| Backend gate `cd api && just ci` | **ACCURATE** | `api/justfile` recipe `ci`: ruff format check, ruff, mypy, migration-smoke, pytest |
| Root `just check`, `just test`, `just build` | **ACCURATE** | Root `justfile` defines all three (js packages + api) |
| Declare layers in `api/CLAUDE.md`; privacy; 700/150; builtins; Pydantic v2; frozen IR; domain exceptions | **ACCURATE** | Mirrors `api/CLAUDE.md` and agent rules; not re-proven by executing gates in this scout |

---

## 2. DUPLICATION MAP

| PROJECT.md section / passage | Also lives in | Recommendation | Owner if kept once |
| --- | --- | --- | --- |
| Opening “retired legacy index, block store, diff projection, and raw fetch…” | `TLDR.md` Mental Model (near identical; TLDR adds wire-store dark ship detail) | **CUT** from PROJECT after rename, or reduce to one sentence + link | `TLDR.md` for product status; capture-plane doc for wire-store read-surface gap only |
| “Session store” first paragraph (Postgres / `SessionWriter` / owner-scoped API) | `TLDR.md` **word-for-word** | **CUT** from PROJECT; keep pointer | `TLDR.md` |
| Workspace identity + two streams (wire vs transcript) | `TLDR.md` Mental Model (same ideas, different wording) | **KEEP** short version in capture-plane doc; TLDR stays one-minute | Capture-plane owns mechanism; TLDR owns pitch |
| Channel side-by-side desktop | `TLDR.md` + `docs/CHANNELS.md` | **CUT** detail from PROJECT; one line + link | `docs/CHANNELS.md` |
| Import DAG + ir purity + storage/session injection + privacy test | `api/CLAUDE.md` Import DAG / Module privacy (**near identical**) | **KEEP** one sentence + link in capture-plane doc; full rules stay in CLAUDE | `api/CLAUDE.md` |
| Engineering standards (types, Pydantic, IR frozen, exceptions, gates) | `api/CLAUDE.md` (Python) + agent rules (700/150) + root `justfile` | **MOVE** out of PROJECT; see Naming §3 | `api/CLAUDE.md` for Python; root README/`CONTRIBUTING` or `docs/ARCHITECTURE.md` only for monorepo gates if needed |
| Tier-1 inventory + session correlation + LaunchProfile/TranscriptAdapter + backfill | **Not** duplicated in ARCHITECTURE or TLDR at this depth | **KEEP** in renamed capture-plane doc | Capture-plane doc |
| Runtime home template materialization (long) | Not in TLDR/ARCHITECTURE | **KEEP** in capture-plane or spin `docs/RUNTIME-HOME.md` if it keeps growing | Capture-plane for now |
| Two-plane / Gateway / Inspector-as-surface vocabulary | `docs/ARCHITECTURE.md` only | PROJECT does **not** currently carry this; do **not** merge into PROJECT content | `docs/ARCHITECTURE.md` owns product-plane architecture |
| Title “architecture” | Conflicts with `docs/ARCHITECTURE.md` title | **RENAME** file; ARCHITECTURE keeps two-plane product architecture | Split: product plane vs capture plane |

**Not duplicated (unique to PROJECT today):** full runtime-home writer inventory, explicit content/writable name tables, LaunchProfile/TranscriptAdapter port description, backfill cursor/snapshot rules, detailed session correlation mint flags.

---

## 3. NAMING: “Inspector” usage + filename for PROJECT content

### How “Inspector” is actually used

| Locus | Usage |
| --- | --- |
| Package | `www/packages/inspector` → npm name `@tm/inspector` |
| Bundle embed | Built into `api/src/transport_matters/www/`, served at `/` (`main.mount_frontend_bundles`) |
| Shell routing | `@tm/shell` `selectRootRoute` → `"inspector"` for `/` and `/inspector` |
| Run identity | `run/identity.py` field `inspector_url`; CLI prompt label `"Inspector UI"` |
| Docs | `docs/ARCHITECTURE.md`: “Inspector is a browser surface backed by the capture plane”; also “frozen **Inspector API**” as what Python capture plane owns |
| Product boundary | `www/packages/inspector/CLAUDE.md`: wire-time breakpoint/edit UI at `/`; never imports `@tm/canvas` |
| Design | `DESIGN.md`: keep Inspector and Canvas presentation separate |
| Control plane docs | Parity language (“Inspector display turns”, conversation parity with Inspector) |

**Verdict:** **(c) both, inconsistently, but with a clear primary.**

1. **Primary (dominant in code and package names):** Inspector = the **browser surface** (`@tm/inspector`, `/`, `inspector_url`).
2. **Secondary (architecture prose):** “Inspector API” = the **frozen Python HTTP API** that backs that surface (capture-plane reads: exchanges, breakpoint, etc.), not mitmproxy/tier-1/launch as a whole.
3. **Not** the whole pre-canvas capture stack (proxy, storage, session store, runtime home). That stack is the **capture plane** (`docs/ARCHITECTURE.md` two-plane rule).

So ARCHITECTURE’s one-liner is directionally right; the leak is calling the Python API surface “Inspector API” while the capture plane is broader than Inspector.

### Filename recommendation for PROJECT.md content

**Support `docs/CAPTURE-PLANE.md`.**

Arguments for:

- Content is almost entirely capture-plane: import DAG, tier-1, session store, correlation, launch ports, backfill, runtime home, storage contracts.
- `docs/ARCHITECTURE.md` already owns **product-plane** architecture (two planes, Gateway, contexts, harness certification). Keeping PROJECT titled “architecture” is a naming collision.
- Aligns vocabulary with ARCHITECTURE’s “Python is the capture plane.”
- “Inspector” must **not** be in the filename: this file is not the browser surface and not only the Inspector API.

Arguments against / caveats:

- Runtime-home materialization is launch/home policy; still capture-adjacent (run dir + managed home), fine under CAPTURE-PLANE, or later extract if it dominates.
- Root `PROJECT.md` is linked from `TLDR.md` (“See PROJECT.md for more”) and `Agents.md`; rename needs link updates in the same change.

**Alternative if CAPTURE-PLANE feels plane-jargon-heavy:** `docs/CAPTURE.md` (shorter, same ownership). Prefer **`docs/CAPTURE-PLANE.md`** for consistency with ARCHITECTURE’s plane language.

**Do not** name it `docs/INSPECTOR.md` (wrong scope) or leave it as root `PROJECT.md` with an “architecture” H1 (collides with ARCHITECTURE).

### Where “Engineering standards” belongs

| Slice | Destination |
| --- | --- |
| Import DAG, privacy, Pydantic/IR/exceptions, builtins | Already in **`api/CLAUDE.md`** — cut from renamed capture-plane doc; one-line “see api/CLAUDE.md” |
| File/function size limits | Global agent rules (`Agents.md` / Claude.md), not capture-plane |
| Quality gates (`just ci` / root `check|test|build`) | Optional one-liner in **`docs/ARCHITECTURE.md`** or a contributor section; not capture semantics |

**Recommendation:** Engineering standards should **not** remain a full section of the capture-plane doc. Move (or leave sole ownership) to `api/CLAUDE.md` + existing agent rules; keep gates as a short pointer if desired.

---

## 4. Fix priority when rewriting PROJECT → CAPTURE-PLANE

1. Replace `~/.transport-matters/workspaces/...` with `<channel home>/workspaces/...` and link `docs/CHANNELS.md`.
2. Replace “needs the next wire store” with TLDR-aligned wording: wire store exists (dark, `0008_wire_store` / `wire_store_observer`); product needs a **read** surface.
3. Fix template content: drop “known content lists remain explicit”; describe exclude sets + default symlink include; treat content name bullets as examples or delete.
4. Add `install_codex_run_context` to home writers; add `compatibility.json` to tier-1 inventory.
5. Optionally rename DAG layers in both PROJECT and `api/CLAUDE.md`: `rules`→`overrides`, `pipeline`→`request_pipeline`, `server`→`api` (or keep abstract names but define the mapping once).
6. Deduplicate Session store paragraph and retired-surfaces blurb against `TLDR.md`.
7. Strip Engineering standards body; link `api/CLAUDE.md`.

---

## 5. Claim tally (for orchestrator reply)

- **48** claims audited across the forced checklist and every PROJECT section.
- **9** stale or wrong (7 STALE + 2 WRONG), concentrated in home path, wire-store wording, template content policy, writer inventory, and DAG package names.
- Core correlation, ports, DAG intent, privacy test, backfill/snapshot ordering, and quality-gate recipes remain **ACCURATE**.
