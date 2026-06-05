# Adversarial review: PR #267 Slice 5 (realtime-slice5-empty-at-spawn)

**Reviewer:** grok (`transport-matters:general:1:2.4` / family grok)  
**PR:** https://github.com/littleorgans/transport-matters/pull/267  
**Branch:** `realtime-slice5-empty-at-spawn` @ `6a55a93`  
**Tree:** pristine  
**Spec:** `~/.mdx/projects/tm-realtime-spec.md` §6 + Slice 5 plan row  
**Verdict:** **CLEAN** — 0 BLOCKER / 0 MAJOR / 0 MINOR

Scope: empty-at-spawn so a never-prompted pane surfaces **Starting**. Owner scoping + migration 0010. READ-ONLY.

---

## 1. Owner-scope leak — PASS

### SQL

`RUNS_BY_WORKSPACE_SQL` (`packages/activity/src/adapters/postgresRecords.ts`):

```sql
FROM run_lifecycle_event AS l
LEFT JOIN session AS s
  ON s.run_id = l.run_id
 AND s.workspace_slug = l.workspace_slug
 AND s.workspace_hash = l.workspace_hash
WHERE l.workspace_slug = $1
  AND l.workspace_hash = $2
  AND COALESCE(s.owner, l.owner) = $3
  AND <PRIMARY_SESSION_FILTER>
GROUP BY l.run_id
```

| Scenario | COALESCE result | Visible to |
|----------|-----------------|------------|
| Lifecycle-only, `l.owner=owner-a` | `owner-a` | A only |
| Session exists, `s.owner=owner-after` | session owner | after only (session authoritative) |
| Drop entire owner predicate | all owners | **leak** |
| `s.owner = $3` only | NULL on no-session | empty-at-spawn **dies** |
| `l.owner = $3` only | lifecycle owner forever | session authority **dies** |

### Red tests (real, load-bearing)

| Test | Guards |
|------|--------|
| `pgIntegration` "surfaces a lifecycle-only run as starting and keeps it owner scoped" | A sees `starting`; B `[]` |
| `pgIntegration` "uses the session owner once the first session exists" | before-session owner empty; after-session owner matches |
| `postgresRecords` unit asserts SQL text contains `LEFT JOIN` + `COALESCE(s.owner, l.owner) = $3` | string-level guard against join flip without COALESCE |

### Null-session path

No session → `s.owner` NULL → COALESCE falls to `l.owner` (NOT NULL DEFAULT `'local'` post-0010). Owner B cannot match owner A's lifecycle row. No alternate read path in this slice enumerates workspace runs without the same SQL.

---

## 2. LEFT JOIN correctness — PASS

| Property | Evidence |
|----------|----------|
| One row per run | `GROUP BY l.run_id`; selected cols are lifecycle aggregates only |
| Multi session × multi lifecycle | `pgIntegration` "returns one row per run with multiple lifecycle events and sessions" → length 1, exit status from lifecycle |
| First session does not double | "returns exactly one run before and after its first session row" |
| `PRIMARY_SESSION_FILTER` on null session | `NOT EXISTS (… parent.session_id = s.parent_session_id …)`; with `s.*` NULL, `= NULL` matches no parent → EXISTS false → NOT EXISTS **true** (vacuous). Lifecycle-only survives. |

---

## 3. Migration 0010 — PASS

| Check | Result |
|-------|--------|
| Revision | `0010_run_lifecycle_owner`, `down_revision = 0009_run_live_status` |
| Change | `ADD COLUMN owner text NOT NULL DEFAULT 'local'` only (new column; DEFAULT backfills) |
| Downgrade | `DROP COLUMN owner` |
| Style | Alembic `op.execute` + contracts constants (matches 0009 pattern) |
| Head pin | migrate smoke expects head `0010_…`; one-step down → 0009 with owner absent |
| Column shape | NOT NULL, default `'local'::text` asserted in `test_migrate` |
| Two-sided contract | `pg-contracts.json` `runLifecycleEventOwnerColumn` pinned in Python `test_activity_pg_contracts` and TS `pgContracts.test` |
| `DEFAULT_ACTIVITY_OWNER` | Python `run_lifecycle_contracts`; TS already has contract `DEFAULT_ACTIVITY_OWNER` for query default |

Writer: `_run_lifecycle_notify_payload` includes `owner`; `RunLifecycleEventRow.owner` + INSERT columns updated. Emit path `build_run_lifecycle_event(..., owner=DEFAULT_ACTIVITY_OWNER)`.

---

## 4. Starting reachable — PASS

| Check | Evidence |
|-------|----------|
| Lifecycle-only → machine `starting` | `listWorkspaceActivity` materializes actor; initial state `starting` (no records needed) |
| Projection status | `pgIntegration` owner-a → `{ status: "starting" }` |
| Reconnect after dropped NOTIFY | "re-lists a lifecycle-only starting run after a dropped NOTIFY" (`onConnected` → store relist from slice 4) |
| Post first session | still one summary; no double-count |

---

## 5. Scope / DRY / sizing — PASS

- **Files:** migration + lifecycle model/writer/DAO + activity SQL/contracts/harness/tests. No consumer/producer realtime churn.
- **LOC:** `postgresRecords.ts` 561; migration 40; `run_lifecycle.py` 125 — all under 700.
- Reuses `DEFAULT_ACTIVITY_OWNER`, existing notify identity shape, slice-4 reconnect relist.

---

## Verification (this review)

```
git status clean @ 6a55a93
pytest migrate + lifecycle writer + emission + pg contracts → 18 passed (with TEST_DATABASE_URL)
pnpm --filter @tm/activity typecheck → clean
pnpm --filter @tm/activity test → 220 passed (unit; pg skipped without env in default run)
pgIntegration + postgresRecords + pgContracts with TEST_DATABASE_URL → 29 passed incl. 5 new empty-at-spawn cases
```

Mutation reasoning (no repo write): drop owner predicate → owner-scope RED; `s.owner=$3` only → starting RED; `l.owner=$3` only → session-authority RED.

---

## Verdict

**CLEAN.** Owner COALESCE + LEFT JOIN is correctly fenced and tested; migration 0010 is additive with dual contract pins; empty-at-spawn `starting` is real including reconnect relist.
