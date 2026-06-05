---
title: Slice 8b-ii — home_dir first-class on source_descriptor + durable owned-launch sessions.json
type: sessions
tags: [backend, transport-matters, capture-substrate, slice-8b-ii, source-descriptor, sessions-json, no-version-bump, moe]
summary: Make tier-1 a complete source of truth for owned launch state — home_dir on the descriptor + binding, and a durable per-run sessions.json — so 8c rebuilds transcript paths without the live env.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

Slice 8b-ii (capture substrate) finishes making tier-1 the complete source of truth for the OWNED
launch state, so the §10.5 / 8c rebuild re-resolves transcript paths faithfully WITHOUT the live
launch env. Authored on branch `feat/capture-slice-8b-ii-home-dir-descriptor-durable-facts` @
`d6afc79` (off main `ee0272b`). `just ci` green (1195 passed, +20; mypy 285 clean; ruff clean).
MoE: author 3.1 (claude), reviewer 3.2 (codex). Coordinator gates `just ci` + PR on dual sign-off;
Stuart road-tests under `--home-dir` before merge.

Four coupled pieces, one hard constraint (no version bump), one new module.

## API / contract changes

- `FileTailSource` (index/adapters/base.py): new optional `home_dir: str | None = None`. Round-trips
  through the single `_SOURCE_ADAPTER` codec. Old persisted descriptors (no field) decode to
  `home_dir=None`.
- `SessionBinding` + `RunContext`: new optional `home_dir: str | None = None` (in-memory carriers,
  handled like `cwd`).
- `claude_transcript_source(..., home_dir=None)`: records home on the descriptor; when only `home_dir`
  is given (the `locate` path) it computes `projects_root = <home_dir>/projects` — the one read-side
  definition of that mapping.
- `seed_codex_session(..., home_dir=None)`: records home on the codex rollout descriptor.
- `build_launch_env(..., home_dir=None)` → `env_keys.HOME_DIR` (`TRANSPORT_MATTERS_HOME_DIR`).
- `Settings.home_dir: Path | None`; `RunFacts.home_dir` + `build_run_facts(home_dir=...)`.
- `LaunchProfile.mints_session_id: ClassVar[bool]` (claude True / codex False) — launch-side twin of
  `bind_exchange`'s read-side `minted` derivation, recorded only for the durable facts.
- NEW `storage/session_facts.py`: `OwnedSessionFacts`, `RunSessionFacts`,
  `write_owned_session_facts(storage_root, facts)`, `read_run_session_facts(storage_root)`.
- NEW `cli/launch_profile.persist_owned_session_facts(profile, managed_session, *, run_id, storage_root, home_dir)`.
- `DiskStorageLayout.sessions_facts_path` → `<run_dir>/sessions.json`.

## Data / storage changes

- NO schema change. `source_descriptor` is `TEXT` — adding a JSON field changes content, not DDL.
- `<run_dir>/sessions.json` (new tier-1 artifact) sits beside `index.jsonl` (the durable run marker
  `iter_run_dirs` enumerates). Document shape: `{ "sessions": [OwnedSessionFacts...] }`. Atomic write
  (tmp + `replace`), upsert keyed on `native_session_id`.
- **No version bump (the load-bearing safety claim):** `ADAPTERS_VERSION` and `_GATED_KEYS` are
  hardcoded literals in `index/schema.py` (NOT derived from the descriptor shape); `schema.py` is not
  in the diff → `_gated_mismatch` cannot trip → an existing `index.db` is NOT dropped on upgrade.
  `upsert_session` writes explicit columns, so the binding's `home_dir` is never a session-row column.
  The bump + drop+rebuild belongs with 8c's executor.

## Security considerations

- No new attack surface. `home_dir` is a launcher-resolved path (`--home-dir`, already
  `.expanduser().resolve()`-d at the CLI boundary), flowed through the existing `TRANSPORT_MATTERS_*`
  process-env contract. The addon never derives a path from untrusted wire input.

## Performance notes

- `sessions.json` is written once per run, synchronously, at launch (off the wire hot path).
- `bind_exchange` stamps one extra optional string per binding (no extra query / IO).

## Design decisions

1. **`home_dir` handled like `cwd`, not like `minted`/`source_descriptor`.** `bind()` propagates
   `run.home_dir` onto the returned binding; the re-bind threads `binding.home_dir → RunContext`. No
   `model_copy` carry in `register_session_cursor` (that carry exists only for values `bind()` reports
   wrong: `minted=False` always, `source_descriptor=None` always). `home_dir` is reported correctly,
   so it needs no carry — same as `cwd`.
2. **`bind_exchange` stamps `home_dir` on EVERY binding, not just owned.** The external-adoption claude
   session under a managed home has no owned descriptor and falls to `locate`, which needs the home.
3. **`sessions.json` writer = the launcher (cli → storage), not an injected addon callback.** Unlike
   the 8b-i transcript snapshot (whose bytes are read-side), all owned facts here are
   LAUNCH-authoritative and known at `prepare_managed_session`. `minted` comes from the profile
   (`mints_session_id`), not duplicated logic. DAG-clean: no `index → storage` edge.
4. **WHEN: top of `run_launch`, inside the per-run lock, before the retry loop.** `WorkspaceLock.__enter__`
   mkdirs the run dir, and `resolved_storage == run_root(working_dir, run_id)` when `--storage-dir` is
   unset, so the dir exists; written once (the retry loop is inside `run_client_with_retry`). Respects
   the "defer run dir creation" fix (`65124c2`): the run dir is minted by the lock, and `--print-command`
   returns before `run_launch`, so dry runs touch no disk. `write_owned_session_facts` also
   `mkdir(exist_ok)` for an explicit `--storage-dir` that does not exist yet.

## Open items

- DUAL SIGN-OFF REACHED @ d6afc79 (author 3.1 + reviewer 3.2, round 1, no blockers). codex verified:
  no schema diff / no gate bump, old-descriptor decode, home_dir locate/env/binding path, sessions.json
  DAG + codex/claude paths; local `just ci` green. Coordinator gating CI + opening the PR.
- Stuart's pre-merge real run under `--home-dir` (claude AND codex): assert `sessions.json` carries the
  right home_dir + descriptor + cli + minted, and the descriptor's `home_dir` matches the managed home.
- 8c (next slice) consumes the 8b-i snapshot + this `sessions.json` and OWNS the `ADAPTERS_VERSION`
  bump + the drop+rebuild executor.
