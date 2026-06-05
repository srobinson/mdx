---
title: Slice 5 deletion review — retire SQLite index substrate (PR#37)
type: sessions
tags: [backend, transport-matters, session-store, sqlite-retirement, peer-consensus, review]
summary: Peer-consensus (Claude + Codex) adversarial review of PR#37; deletion is safe and CI-green, sign-off conditional on three stale-doc fixes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-06
updated: 2026-06-06
---

# Slice 5 deletion review — PR#37 `feat/session-5-retire-sqlite`

## Artifact

- PR#37 `feat/session-5-retire-sqlite`, head **`84a528f`** (`+282/-5263`, 51 files).
- Base `main` `97c2532`. Authoritative intent: `retire-map.md` (same dir).
- `aed0434` (briefed) → `84a528f` delta is **PROJECT.md only** (119+/141−, docs); the code
  audit performed at `aed0434` holds verbatim for `84a528f`.
- Reviewers: Claude (`…:3.3`, consensus owner of this file) + Codex (`…:3.2`), peer-consensus.

## Verdict

**FINAL: both reviewers signed off on PR#37 as currently filed @ `30b49c3`.** The conditional
sign-off below was satisfied by the fix commit `30b49c3` ("docs: clean stale session store
references"); re-audited live and verified clean (see "Final-head verification").

**(Original) sign off conditional on three documentation fixes (no code changes).** The deletion is
safe: nothing still-reused was removed, there are no dangling references, the import DAG stays
legal, the retired HTTP surface is fully unregistered with no silent 404, and `just ci` is green
against Postgres with no silent skips. The conditions were stale docs that still presented the
deleted SQLite substrate as the live architecture.

### Final-head verification (`30b49c3`, full delta main..30b49c3 = 60 files, +459/-5464)

- **Condition 1+2 (one edit):** root `CLAUDE.md` is a git `120000` **symlink → TLDR.md**, so the
  single TLDR.md rewrite cleared both. TLDR.md:38 now reads "The active correlated store is
  Postgres."; zero SQLite/`index.db`/content-addressed/FTS residue.
- **Condition 3:** `session_facts.py:10-12` repointed to `session/backfill.py` `iter_run_dirs`.
- **Expanded cleanups (~9, same class):** `canonicalization.py` (dropped dead
  `index.blocks.identity_canonical` clause), `cli/launch_profile.py`, `launch_runtime.py`,
  `env_keys.py`, `codex/request_parser.py`, `index/adapters/codex.py`, `transcript_snapshot.py`,
  session-binding test files — **comment/docstring/test-name only.** Sole non-comment hunk:
  `launch_profile.py` collapsing `mints_session_id = (True ...)` to `= True` (value preserved,
  claude True / codex False). `env_keys.HOME_DIR` value unchanged; test assertions unchanged; the
  new doc ref `session.ingest.build_session` resolves (`ingest.py:48`) — no new stale ref.
- **CI @ `30b49c3` vs local Postgres (real exit codes, no pipe masking):** ruff format+check &
  mypy (285 files) clean; pytest **real exit 0 = 1143 passed**, no errors, no skips.
- **O1** unchanged; remains a non-blocking follow-up.

### Conditions (propose to engineer; do not self-apply)

1. **`TLDR.md:32-38`** — still states tier-2 is `~/.transport-matters/index.db` SQLite with
   content-addressed blocks + FTS + rebuildable projection. Rewrite to match `PROJECT.md`
   (tier-2 = Postgres session store; legacy index/block/diff/raw retired, diff parked behind a
   future wire store). *(Codex F1.)*
2. **`CLAUDE.md:35-38` (repo root)** — carries the **byte-identical** stale "single shared SQLite
   index … blocks, full-text search" text as TLDR.md. This is the project-instructions file
   injected into every agent session, so it is the more load-bearing miss. Apply the same
   rewrite. *(Claude extension of F1; README.md verified clean.)*
3. **`api/src/transport_matters/storage/session_facts.py:10-12`** — comment points the durable
   run marker at `index/maintenance.py` `iter_run_dirs`, but that module is deleted; the surviving
   symbol is `session/backfill.py` `iter_run_dirs`. Repoint the reference. *(Found independently
   by both reviewers; Codex F1 addendum.)*

### Non-blocking observation (follow-up, not a condition)

- **O1 — wire exchange sink is now production-dead.** `storage/exchange_sink.py` plus the
  `emit_to_index(...)` calls in `exchange_recorder.py` and `codex/exchange.py` have **no production
  registrant**: `set_exchange_sink` is called only by tests; the deleted `make_index_sink` was its
  sole `load_runtime` registrant. So `emit_to_index` is a permanent no-op in production. This is
  **faithful to intent** — `retire-map.md` deliberately scoped `exchange_sink.py` out of the DELETE
  list, and the PR re-cast it as a generic "optional post-persist observer," consistent with the
  parked wire-store direction (mirrors the `/raw` "re-provide later" decision). Flag for a future
  cleanup-or-wire decision; not a blocker for this slice.

## Verification matrix (all checks independently run live, not trusted from the brief)

| # | Check | Result | Evidence |
|---|-------|--------|----------|
| 1 | Nothing still-reused deleted | PASS | `load_runtime` tailer→`SessionWriter` wiring (`build_record=build_event`, `submit_batch=submit_events`→`writer.submit_blocking`) is **byte-identical to `main`**; only `set_exchange_sink(make_index_sink(...))` dropped. Adapters, `storage/{transcript_snapshot,session_facts}`, `canonicalization`, `cli/*` launch, `synth_session_id` all intact. |
| 2 | No dangling refs | PASS | Acceptance grep `IndexWriter\|index_db_path\|make_index_sink\|index\.db` over `src` = 0. Broader grep clean: surviving `upsert_session` is the **new Postgres `session.dao` method** (name collision, not the deleted `index/sessions.py` symbol); `rebuild` hits are `codex.repair_rebuild` + a `transcript_snapshot` comment. No surviving `build_transcript_job`/`build_run_facts`/`rebuild_if_stale`/`IndexJob`/`index_router`/`index_routes`. |
| 3 | `iter_run_dirs`/`RunDir` re-home | PASS | Both now defined in `session/backfill.py`; `replay_transcript_runs` consumes them; backfill repointed; no `index→session` back-edge. (One stale doc pointer → condition 3.) |
| 4 | Import DAG legal | PASS | `git grep` shows no `index→session` and no `storage→session` import. `index/__init__.py` exports exactly adapters + tailer survivors (`TailCursor`,`TranscriptTailer`,`ingest_records`,`iter_complete_records`,`register_session_cursor`) + sessions survivors (`SESSION_NS`,`synth_session_id`). `test_private_import_boundary.py` passes (in the green suite). |
| 5 | `/api/index/*` + `/raw` unregistered, no silent 404 | PASS | `router.py` includes only breakpoint/exchanges/meta/overrides/session_routes/stream — no `index_router`. Deleted `/raw` path was `/api/index/exchanges/{id}/raw`; `rg` over `www`/`desktop` finds **zero** `/api/index` or `/raw` calls (sole hit is a `raw-secret` redaction assertion in `ExchangeDetail.test.tsx`). PROJECT.md honestly documents the raw parking. |
| 6 | Trims kept the right halves | PASS | `tailer.py` keeps `iter_complete_records`/`TailCursor`/`TranscriptTailer`/`register_session_cursor`, drops `build_transcript_job` submit, and **no longer drops `None` records** (build_record appended unconditionally; only parent-threading guarded by `if turn is not None`) → meta records flow. `sessions.py` is synth-only (`SESSION_NS`+`synth_session_id`, `upsert_session` gone). `addon_runtime` keeps SessionWriter+pool+tailer+snapshot wiring, cuts the index sink. |
| 7 | `cd api && just ci` green vs PG, no skips | PASS | ruff `format --check` + `check` clean; mypy clean (285 files); pytest **1125 non-PG passed + 25 PG passed** (Claude, local PG) = Codex's **1143 passed** with PG. PG tests **error, not skip,** when `TRANSPORT_MATTERS_TEST_DATABASE_URL` is unset → the intended no-silent-skip behavior. Only tests of deleted modules removed. Frontend (Codex): `pnpm lint && typecheck && test` green, 374 tests. |
| + | PROJECT.md reflects Postgres (orchestrator add-on) | PASS | `84a528f` PROJECT.md removes all SQLite/`index.db`/block/diff/pivot/`/api/index`/rebuild-gate language; states tier-2 = Postgres session store and that the legacy index/block/diff/raw substrate is retired with the diff parked behind a future wire store. |

## Notes

- `retire-map.md` orchestrator decisions 1-4 (canonicalization stays; sessions thin synth-only;
  `/raw` dies with the file; `maintenance.py` gone with `iter_run_dirs` re-homed) are all honored.
- `pyproject.toml` change is clean fallout: drops the now-orphaned ruff `TC003` per-file-ignore for
  the deleted `index_routes.py`.
- The `codex/exchange.py`, `exchange_recorder.py`, `storage/exchange_sink.py`,
  `codex/request_parser.py` diffs and the `test_tier2_sink.py → test_exchange_finalize_sink.py`
  rename are **comment/docstring/log-text only** (executable code byte-identical) — terminology
  de-coupling from the retired "tier-2 SQLite index," not scope creep. See O1.
