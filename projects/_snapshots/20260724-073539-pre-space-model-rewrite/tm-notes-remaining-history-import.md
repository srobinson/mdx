---
title: "TM Notes Work-Remaining Audit — History Import / Postgres-first Session Store"
type: research
tags: [transport-matters, history-import, postgres, session-store, work-remaining, audit]
summary: "All 6 slices of NOTES/history-import-postgres-first.md are REMAINING; the note is an unstarted initial spec and the legacy Tier-1 path it targets for retirement is still live-wired."
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# Work-Remaining Audit: History Import / Postgres-first Session Store

**Slice owner note:** `NOTES/history-import-postgres-first.md` (gitignored scratch, dated 2026-06-11, self-labeled "Status: initial spec").
**Repo root:** `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
**Method:** Verified every claim against committed code (`git log`, grep for named symbols/tables/CLI commands, source reads). The note's own status lines were treated as non-evidence.

## Bottom line

**All 6 slices (S1–S6) are REMAINING. Confidence: high.** No import scanner/writer modules exist, none of the proposed tables exist in any migration, there is no `transport-matters import` CLI command, there are no `/api/import/*` routes, no tool-use summary is computed or stored, and the entire Tier-1 legacy path targeted for retirement (S4) still exists **and is live-wired into the capture path**. The only pre-existing affordance the spec could lean on is the `session.source_descriptor jsonb` column, which predates this epic (shipped in the original session-store foundation migration).

No `import`/`backfill`-retirement/`tool-summary` commit appears in `git log --all`. The newest history-relevant commits all predate or are unrelated to this spec (e.g. PR #59 tier-1 indexes, PR #33/#32/#31/#30 tier-1 replay — these *build* the legacy path the spec wants gone).

---

## Per-slice status

### Slice 1 — Inventory and cleanup plan → REMAINING

The cleanup the slice plans has not been executed; the docs/tests still enshrine Tier-1.

- PROJECT.md still frames Tier-1 as the session source of truth, not Postgres. Anchors: `PROJECT.md` heading `## Tier 1 source of truth` (line ~66); `Tier 1 is authoritative` (line ~141); `## Backfill and replay` (line ~129); `sessions.json, the durable owned launch facts` (line ~76); `session/backfill.py replays transcript snapshots from tier 1 using sessions.json` (lines ~92-93). Spec item S1.4 ("Update PROJECT.md so Postgres is the session source of truth") is undone.
- No "deletion tests that fail while legacy disk writes remain" (S1.5) exist. The opposite is present: tests still assert the legacy artifacts. Anchors: `api/src/transport_matters/storage/test_session_facts.py`, `.../storage/test_transcript_snapshot.py`, `.../storage/test_disk_cache_backfill.py`.
- Confidence: high.

### Slice 2 — Import scanner → REMAINING

No Claude/Codex native-history scan exists; the proposed import modules are absent.

- `absent: find api/src -name import_scan.py -o -name import_plan.py -> 0 hits`.
- No native-history scanner emitting an import plan (counts/date-ranges/warnings/workspace-mapping). `absent: grep -rE "import_scan|import_plan|scan.*claude.*history|rollout root" api/src/**/*.py -> 0 hits`.
- Confidence: high.

### Slice 3 — Import writer + provenance tables → REMAINING

No writer, no tables.

- `absent: find api/src -name import_writer.py -o -name import_job.py -> 0 hits`.
- Proposed tables absent from all three migrations (`api/migrations/versions/0001_session_store_foundation.py`, `0002_event_tier1_indexes.py`, `0003_event_dead_letter.py`). `absent: grep -rIE "import_job|import_source" api/migrations -> 0 hits`.
- Provenance columns on `session` are only partially pre-existing: `source_descriptor jsonb` exists (`api/migrations/versions/0001_session_store_foundation.py:31`, inside `CREATE TABLE "session"` at line 21) but `origin` (live|imported) and `import_job_id` do **not** exist. `absent: grep -IE "origin|import_job_id" 0001_session_store_foundation.py -> 0 hits (only source_descriptor matches)`. Note: `source_descriptor` shipped with the original foundation migration, not this epic, so it is reusable scaffolding rather than delivered S3 work.
- Confidence: high.

### Slice 4 — Remove legacy Tier-1 session rebuild → REMAINING (and still live-wired)

Every retirement target still exists and is actively called on the live capture/launch path, so nothing here has even begun.

- `storage/session_facts.py` exists and `sessions.json` is **still being written on live launches**. Anchors: `api/src/transport_matters/cli/launch_profile.py:38` (`from ...storage.session_facts import OwnedSessionFacts, write_owned_session_facts`), `launch_profile.py:264` (calls `write_owned_session_facts`), invoked via `persist_owned_session_facts` from `captured_run.py:118` and `:209` and `cli/codex_cmd.py:440`. Spec items S4.1/S4.2 undone.
- `storage/transcript_snapshot.py` exists and snapshot teeing is **still wired into the addon runtime**. Anchors: `api/src/transport_matters/addon_runtime.py:26` (`from ...storage.transcript_snapshot import make_transcript_snapshot_writer`) and `addon_runtime.py:180` (instantiates the snapshot writer at capture). Spec item S4.3 undone.
- `session/backfill.py` exists and still reads `sessions.json` + transcript snapshots. Anchors: `api/src/transport_matters/session/backfill.py:27` (imports `read_run_session_facts`), `:53` (`read_run_session_facts(root)`), `:75` (`transcript_snapshot_path(session_id)`). Spec item S4.4 undone.
- Legacy tests still present (S4.5 undone): `storage/test_session_facts.py`, `storage/test_transcript_snapshot.py`, `storage/test_disk_cache_backfill.py`.
- Confidence: high.

### Slice 5 — Product surface (CLI / API / desktop) → REMAINING

No import command, no import routes, no desktop import workflow.

- CLI is a Typer app (`api/src/transport_matters/cli/__init__.py:128` `main = typer.Typer(...)`). Full command set: `claude` (`:253`), `codex` (`:309`), `desktop` (`:362`), `doctor` (`:447`), `paths` (`:483`), `list` (`:509`), `version` (`:524`), plus the `db` sub-app (`:136`, commands `status`/`upgrade` in `cli/db_cmd.py:44,66`). **No `import` command** (`import scan|run|jobs|show` from the spec are all absent). `absent: grep "@main.command" cli/__init__.py -> 7 commands, none named import`.
- No `/api/import/*` routes. The API router (`api/src/transport_matters/api/v1/router.py`) mounts only: overrides, breakpoint, meta, sessions, local-file, stream, terminal, runs, capabilities. `absent: grep -ril "import" api/v1/router.py -> no import_routes include`.
- No desktop import workflow. `absent: grep -rIE "import" desktop -> no import job/scan UI` (not separately re-verified at file level beyond the route/CLI absence, but the API/CLI backing it does not exist).
- Confidence: high.

### Slice 6 — Tool-use summary + curation signal → REMAINING

Nothing computed, stored, or exposed.

- No `session_tool_summary` table. `absent: grep -rIE "session_tool_summary" api/migrations -> 0 hits`.
- No per-session tool-use summary computed during ingest or in the session writer/API. `absent: grep -rInE "session_tool_summary|tool_use_summary|tools_used|skills_invoked|curation" api/src/transport_matters --include="*.py" -> 0 hits`. (A grep without the `.py` filter only matches minified `www/assets/*.js` exchange-detail bundles that render raw `tool_use` blocks for the UI — unrelated to the spec's denormalized summary.)
- Not exposed in session list/detail APIs (`api/src/transport_matters/api/v1/session_routes.py` carries no tool-summary field).
- Confidence: high.

---

## Summary table

| Slice | Subject | Status | Strongest evidence anchor |
|-------|---------|--------|---------------------------|
| S1 | Inventory + cleanup plan | REMAINING | `PROJECT.md:66` `## Tier 1 source of truth` still authoritative |
| S2 | Import scanner | REMAINING | `absent: import_scan.py / import_plan.py -> 0 hits` |
| S3 | Import writer + tables | REMAINING | `absent: grep import_job\|import_source api/migrations -> 0 hits` |
| S4 | Retire Tier-1 rebuild | REMAINING | `launch_profile.py:264` still writes sessions.json; `addon_runtime.py:180` still tees snapshots; `session/backfill.py` present |
| S5 | Product surface CLI/API | REMAINING | CLI has 7 commands, none `import`; router mounts no `/import` |
| S6 | Tool-use summary + curation | REMAINING | `absent: session_tool_summary across .py + migrations -> 0 hits` |

## Caveats / confidence notes

- The audit is structural (existence + wiring of named symbols/tables/commands), which is decisive for "did the work land": every named deliverable is absent or, for retirement targets, still present and live. Confidence high across all six.
- One genuine pre-existing affordance: `session.source_descriptor jsonb` (migration 0001:31) gives S3 a place to stash native-source metadata without an ALTER. It is foundation scaffolding, not delivered import work.
- Desktop-specific UI (S5.3/S5.4 badges + workflow) was inferred-absent from the missing API/CLI backing rather than exhaustively walked file-by-file in `desktop/`; if a deeper desktop pass is wanted, flag it.
