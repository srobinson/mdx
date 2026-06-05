# PR#298 S2e adversarial review (grok)

| Field | Value |
|-------|-------|
| PR | [#298](https://github.com/littleorgans/transport-matters/pull/298) |
| Range | `main...feat/s2e-compatibility-facts` (`4de2e213`…`0320ffd6`) |
| Method | `gh pr diff 298` + full file read of the 18-file range |
| Tree at verdict | `feat/s2e-compatibility-facts` @ `0320ffd6`, **clean** |
| Scope | Read-only review; no gates; no source writes |
| Specs | scout `~/.mdx/projects/transport-matters-scout-s2e.md`, `RUNTIME-SURFACING-S2-PLAN.md` S2e, `HARNESS-COMPATIBILITY.md` Historical read compatibility |
| Decision under test | ACCEPT — pre-S2e run dirs → `historical_contract_unsupported`; no legacy fallback; no guessed parse |

## Summary

S2e lands the durable `compatibility.json` fact artifact and threads recorded-revision dispatch through the one existing adapter registry and the historical replay path. Schema version is gated before pydantic parse; absent artifact / absent or unknown revisions all raise `HistoricalContractUnsupported` with a stable `.code`. Live paths keep harness-only `get_adapter`. Atomic JSON write is promoted to one public helper shared by `session_facts` and the new writer. Writer is not called from launch seams; no `match_release`; no inventory; no migration. Boundaries match the scout.

**Counts: 0 Blocker / 0 Major / 3 Minor**

## Focus checklist

| Focus | Verdict | Evidence |
|-------|---------|----------|
| `fact_schema_version` schema-gated; unknown → unsupported | PASS | `compatibility_facts.py:188-193`; test `test_read_unknown_schema_version_is_unsupported` |
| Unknown/absent recorded revision → unsupported; no silent current-adapter parse | PASS | `get_adapter_for_recorded` (`adapters/__init__.py:44-74`); `_replay_owned` uses only that API (`backfill.py:187-191`); live `addon_runtime` still uses `get_adapter` |
| Absent artifact → unsupported | PASS | `backfill.py:164-170`; `test_replay_transcript_run_without_artifact_is_unsupported` |
| One registry generalized, not a second map; r1 on adapters | PASS | `get_adapter_for_recorded` → `get_adapter`; ClassVars on `TranscriptAdapter` / claude / codex; production keys `ClaudeAdapter.harness` / `CodexAdapter.harness` (test `("claude","codex")` is test-only) |
| Backfill threads recorded-revision dispatch | PASS | `replay_transcript_run` → `read_compatibility_facts` → `_replay_owned` → `get_adapter_for_recorded` |
| Writer atomic, idempotent, typed-absent read | PASS | `atomic_write_model_json` + `write_compatibility_facts`; read `None` when missing; tests round-trip / idempotent / absent |
| DRY: one public `atomic_write_model_json`; session_facts migrates; no third copy; private mixin not imported | PASS | `disk_helpers.py:50-69`; mixin delegates (`:80-81`); `session_facts` / `compatibility_facts` both import public helper |
| Model in `compatibility_facts.py`; reuses `RELEASE_REVISION_FIELDS` | PASS | Builder + validator use `RELEASE_REVISION_FIELDS` |
| Audit mirror: new verb via injected sink; no new table | PASS | `mirror_compatibility_facts` + `COMPATIBILITY_FACTS_AUDIT_VERB`; `ON CONFLICT` on existing `control_plane_action.dispatch_id` |
| No launch writer, no `match_release`, no inventory, no new prod harness list, no migration | PASS | Production call sites of `write_compatibility_facts` / `mirror_*` are only the module itself; launch greps empty; `api/CLAUDE.md` doc-only |
| Tests: write→read→dispatch; unknown revision + absent outcome | PASS | unit + registry + replay integration tests |

## Hygiene (18 changed files only)

| File | LOC | Notes |
|------|-----|-------|
| `harnesses/compatibility_facts.py` | 248 | New, under 700; pure compose + IO + audit mirror |
| `index/adapters/__init__.py` | 75 | Thin revision gate over existing registry |
| `session/backfill.py` | 312 | Historical path only; functions remain small |
| `storage/disk_helpers.py` | 400 | Public helper extracted; mixin thins to delegate |
| `storage/session_facts.py` | 91 | Hand-rolled tempfile removed |
| `harnesses/compatibility.py` | 554 | Correctly avoided growing this; only `FrozenStringMap` public rename |
| Others | small | Layout path, exception, ClassVars, tests, CLAUDE.md |

No new 700+ files. No function past ~150 in the slice. No parallel second registry or second atomic-write owner.

## Issues

### Issue 1 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/compatibility_test_support.py:228-236`
- **Description:** `seed_run_compatibility_facts` invents revision strings via `{harness}-{field}-r1` formula. Six of fourteen facets do not match the embedded release vocabulary (`claude-harness-launch-r1` vs `claude-launch-r1`, `claude-route-catalog-r1` vs `claude-routes-r1`, etc.). Dispatch-critical names luckily match, and the docstring admits that, but the seeder is a second incomplete vocabulary source beside `make_release` / `make_fact_artifact`.
- **Suggestion:** Build the seed through `make_release(harness_id=…)` + `make_fact_artifact(release=…, run_id=…)` (or copy `make_release` field values) so test fixtures share one revision vocabulary.
- **Status:** open

### Issue 2 — Severity: Minor
- **File:** `api/src/transport_matters/storage/disk_helpers.py:59-69`
- **Description:** `atomic_write_model_json` uses `NamedTemporaryFile(..., delete=False)` with no `try`/`finally` cleanup. If `model_dump_json` / write fails after the temp is created, or if `Path.replace` fails, a `*.tmp` orphan remains in the run dir. Success path is covered by tests; failure path is not.
- **Suggestion:** Wrap write+replace in `try`/`except` that unlinks `tmp_path` on failure before re-raising (keep success path as today).
- **Status:** open

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/index/adapters/__init__.py:1` and `:39`
- **Description:** Package docstring still says only `harness -> adapter` and does not mention recorded-revision historical dispatch. Line 39 says "unhonorable recording" (typo; intended "unhonored" / "unrecorded").
- **Suggestion:** Update the module one-liner to mention both live and recorded-revision paths; fix the typo.
- **Status:** open

## Non-issues (checked, plan-sanctioned)

- Pre-S2e dirs raising `historical_contract_unsupported` is the ACCEPT decision, not a regression.
- Equality-gate registry (current adapter ClassVars vs recorded strings) correctly cannot keep multiple historical readers per harness; multi-revision retention is S3 continuation-bridge territory.
- Live `get_adapter` remains ungated; only historical replay is revision-aware.
- Audit mirror always calls `audit.write`; real sink dedupes via `dispatch_id` unique constraint (DriftEmitter shape).
- Writer not wired at launch is S2f by plan.

## Craftsmanship verdict

Tight S2e slice: correct outcome typing, one registry, one atomic writer, boundaries held, tests cover the contract core.
