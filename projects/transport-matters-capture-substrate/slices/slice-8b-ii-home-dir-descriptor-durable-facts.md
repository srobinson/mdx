# Slice 8b-ii — `home_dir` first-class on the descriptor + durable owned-launch facts (sessions.json)

**Goal:** finish making tier-1 a complete source of truth for the **owned launch state**, so a future
rebuild (8c) re-resolves transcript paths faithfully without the live env. Three coupled pieces:
1. `--home-dir` becomes a **first-class field on `source_descriptor`** (`FileTailSource`), carried
   explicitly (not just baked into the path).
2. Fix the claude `locate` fallback, which currently **ignores** `home_dir` (`claude.py:82-86` calls
   `claude_transcript_source(binding.cwd, binding.session_id)` with no `projects_root` → defaults to
   `~/.claude/projects`).
3. Persist the **durable per-run owned facts** (the deferred §11.1 `sessions.json`): `native_session_id`,
   `source_descriptor`, `cli`, `minted`, `home_dir` — written under the run dir at launch/bind, so 8c's
   rebuild reads owned state WITHOUT the live launch env. (The manifest carries `home_dir` but
   **unlinks on exit** (`manifest.py`), so it cannot be the durable home.)

**Depends on:** 8b-i merged (#30 — tier-1 now owns the transcript). **Unblocks:** 8c (backfill/rebuild/
reconcile reads the snapshot + sessions.json). **Branch:** off current `main` (`ee0272b`).

## NON-DESTRUCTIVE — no version bump (confirm + justify)

Adding an **optional** `home_dir` field to `FileTailSource` must **NOT** bump `ADAPTERS_VERSION` /
`schema_version`. Rationale to verify: old persisted descriptors decode fine with `home_dir=None`
(graceful default = native home), `normalize` is untouched, and `source_descriptor` is a TEXT/JSON
column so the DDL is unchanged → existing rows stay valid, no drop needed. **The version bump +
drop+rebuild belongs with 8c's rebuild EXECUTOR** (today the gate drops-to-empty but never replays, so
a bump now would nuke the index with nothing to rebuild it). If you find a reason existing rows DO go
stale, STOP and escalate — do not silently bump.

## Build (RE-CONFIRM line numbers)

1. **`home_dir` on `FileTailSource`** (`index/adapters/base.py` `FileTailSource` :44-53, `encode/
   decode_source_descriptor` :76-83): new optional `home_dir: str | None = None`; round-trips through
   the one codec; decode at `tailer.py:242-245`. Constructors populate it from the resolved home:
   `claude_transcript_source` (`claude.py:43-57`) and the codex seed (`seed_codex_session`). `prepare`
   already resolves the home into the PATH (`launch_profile.py:119-123` via `claude_projects_root`/
   `codex_sessions_root(home_dir, env)`); now also carry `home_dir` explicitly.
2. **claude `locate` honors `home_dir`** (`claude.py:82-86`): thread the resolved `projects_root` (or
   `home_dir`+`env`) onto `SessionBinding` (`base.py:24-41`, survives the re-bind in
   `register_session_cursor` `tailer.py:235-241`) / `RunContext` (`base.py:86-97`) so `locate` resolves
   under the managed home. Managed launches never hit `locate` (owned descriptor decoded directly), so
   this only fixes external-adoption-under-managed-home — but it's a real correctness gap.
3. **`home_dir` into the launch env** (`cli/launch_runtime.py` `build_launch_env` :445-474, `env_keys`,
   `config.py` `Settings` :55-56, `addon_runtime.build_run_facts`/`RunFacts` `ingest.py:40-87`):
   `home_dir` currently reaches the addon ONLY via the (ephemeral) manifest. Thread it through the
   OWNED_* env-var channel so `build_run_facts`/`bind_exchange` carry it onto the binding/descriptor.
4. **Durable per-run `sessions.json`** under the run dir (`storage_root`): owned facts (native id,
   descriptor, cli, minted, home_dir, run_id) written at launch/bind so 8c reads them without the env.
   DECIDE+justify: who writes it (the launcher — cli layer, may import storage — vs an injected writer
   like the 8b-i snapshot callback) and WHEN (launch vs first-bind; the run dir is created lazily —
   `fix: defer workspace run directory creation`). It must be found by `iter_run_dirs`-adjacent enumeration
   and survive process exit. Reuse `disk_layout.py` for the path; do NOT reuse the manifest (it unlinks).

## Invariants (must not break)

- **#17 privacy** (AST-enforced): public symbols only across modules.
- **DAG:** the descriptor lives in `index/adapters` (imports `ir`/`canonicalization` only). The
  `sessions.json` WRITE goes to `storage`/tier-1 — keep it out of `index` (write from the cli launcher,
  or an injected writer at the composition root, mirroring 8b-i; NO `index → storage` write edge).
- **No destructive bump** (above). **Live capture unchanged** functionally (this is additive owned-state
  plumbing + a locate fix).
- LOC ≤ 700/file, funcs ≤ 150; builtins typing; Pydantic v2 (FileTailSource is frozen — add the field).

## Acceptance (§13 + a REAL run)

- `FileTailSource.home_dir` round-trips through encode/decode; an OLD descriptor JSON without the field
  decodes to `home_dir=None` (graceful, no error) — assert it.
- claude `locate` resolves under a managed home when the binding carries one (a managed-home binding →
  `<home>/projects/...`, not `~/.claude/projects/...`).
- `home_dir` reaches the binding/descriptor via the env channel (not just the manifest) — assert
  `build_run_facts`/`bind_exchange` propagate it.
- A durable per-run `sessions.json` is written under the run dir with the owned facts (native id,
  descriptor incl. home_dir, cli, minted), readable after process exit.
- **NO version bump:** `schema_meta` gated keys unchanged → an existing `index.db` is NOT dropped on
  upgrade (assert / state the evidence).
- **REAL-RUN PROOF:** real `transport-matters claude` AND `codex` under `--home-dir` → `sessions.json`
  in the run dir carries the right home_dir + descriptor + cli + minted; the descriptor's `home_dir`
  matches the managed home.
- `just ci` green.

## Sequencing → 8c

8c (backfill/rebuild/reconcile EXECUTOR) consumes the 8b-i transcript snapshot + this `sessions.json`,
and owns any `ADAPTERS_VERSION` bump + the drop+rebuild wiring. Do NOT build 8c here.
