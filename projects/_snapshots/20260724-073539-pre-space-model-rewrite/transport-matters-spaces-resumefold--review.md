---
title: Spaces resume-`sessionId` fold + cross-doc consistency — peer review
type: research
tags: [transport-matters, spaces, slice6, resume, sessionId, peer-review, moe]
summary: The just-applied Slice 6 resume-sessionId fold is correct on all four sub-questions and the cross-doc/space-package consistency holds; two Minor findings (legacy-canvas reset via the worktreeId-required guard on the same legacy-import path; an index wording overstatement).
status: active
source: codebase-analyst
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

# Spaces resume-`sessionId` fold — peer review (Mode 1, independent)

**Reviewer:** `transport-matters:helioy-tools:codebase-analyst:1:4.1`
**Scope:** the just-applied resume `sessionId` fold into Slice 6 + the deferred note + index/package updates.
**Method:** read-only. Verified plan claims against LIVE `www` source on `main@2323169`. Tree pristine (no working-tree changes).

**Verdict:** the just-applied fold is **correct on A1–A4** and **cross-doc consistent on B1–B2**. Two **Minor** findings below; neither is the `sessionId` fold itself.

---

## A. The Slice 6 resume `sessionId` fold — VERIFIED CORRECT

Cross-checked against live `www/src/session-canvas/model/paneRecords.ts` (`PaneContentRef`, `isPaneContentRef`), `canvasStore.persistence.ts`, `persistence/canvasPanePersistence.ts`, `persistence/canvasPersistOptions.ts`, `model/spawn.ts`, and plan Task B/D.

- **A1 — field + guard: CORRECT.** Plan Step 3 adds `sessionId?: string` to the `captured-run` variant (optional, alongside the now-required `worktreeId`), and the guard branch is `typeof value.worktreeId === "string" && isOptionalString(value.sessionId)`. `isOptionalString` (`paneRecords.ts:27`) = `value === undefined || typeof value === "string"`, so it accepts a string, accepts absent, and rejects a non-string (`7`). Optional (not `| null`) is the right model: `JSON.stringify` drops `undefined` keys, so a ref without a session never serializes as `null`, and the guard never needs to accept `null`. Note the orchestrator's "nullable" phrasing; the plan's `?:` optional is the correct, internally-consistent choice.

- **A2 — persistence + legacy import carry it through: CORRECT, and correctly requires NO persistence-module change.** The canvas persist path round-trips the **whole ref object**, not a field-by-field reconstruction:
  - Save: `partializeCanvasState` → `getContentRefs` = `paneRefsForOpenRecords` returns `pane.contentRef` verbatim (`canvasStore.persistence.ts:28-34`); `JSON.stringify` includes `sessionId`.
  - Load: `readContentRefs` validates each ref via the guard then stores it **whole** (`contentRefs[paneId] = ref`, `canvasPanePersistence.ts`); `sessionId` rides along untouched.
  - This is why Task B legitimately does NOT list `canvasStore.persistence.ts` as modified — the existing path is field-agnostic. Good catch by the plan author to not over-touch it.
  - One-time legacy import: `importLegacyCanvasCache` (Task D Step 3) is a **raw string copy** (`storage.setItem(target, legacy)`), it never parses refs, so a legacy `captured-run` ref with no `sessionId` copies without crash; on the subsequent rehydrate it passes the guard (sessionId optional). Absence handled, no crash. ✓

- **A3 — round-trip test present: CORRECT.** Plan `paneRecords.test.ts` (Step 1, the `"round-trips a captured-run ref with and without sessionId"` case) asserts: legacy ref WITHOUT `sessionId` → guard true, `sessionId` undefined; bound ref WITH `sessionId: "sess-7"` → survives `JSON.parse(JSON.stringify(...))`, guard true; `sessionId: 7` → guard false. All three cases covered.

- **A4 — deferred framing correct; nothing populates/uses it now: CORRECT.** No write path stamps `sessionId`: `createCapturedRunRef` (Step 7) sets only `worktreeId`; `addCapturedRun` (Step 7) passes only provider/worktreeId/label/template; `makeCapturedRunRef` (Step 7) sets only `worktreeId`. No reader is added — `CapturedRunPane` (Task E) reads `worktreeId`, not `sessionId`. The `CapturedRunRef` return type is `Extract<PaneContentRef, {kind:"captured-run"}>` (live `spawn.ts:12`), under which `sessionId?` is optional, so the constructor omitting it type-checks. Plan prose (lines 15, 362, 479-482) states field-now / population-and-resume-Slice-7 explicitly. No place implies using it now.

---

## B. Cross-doc + cross-slice consistency — VERIFIED CONSISTENT

- **B1 — `space/` package: CONSISTENT, no stragglers.** Every slice and the index reference the singular module `transport_matters.space.{models,detection,store}` (slice1 creates `space/__init__.py`+`space/models.py`; slice2 `space/detection.py`+`space/store.py`; slices 3-5 import `space.{detection,models,store}`). HTTP routes are correctly plural (`/v1/spaces/...`). Grep for old/plural module forms returned only route paths, not module paths. The index build-status table (lines 137-144) matches the per-slice descriptions, and the Slice 6 index entry now carries the `sessionId` bullet (lines 113-117) + the round-trip test line (119) + the "Open at execution time" resume note (155-158).

- **B2 — proposal "Native resume on reopen — deferred (Slice 7)" open-item: ACCURATE, not over-specified.** Section (proposal lines 203-229) names all four anchors correctly: `SessionRow.native_session_id` (220), `parent_session_id`/`forked_at_seq` (221), the Slice 6 captured-run pane `sessionId` "persisted now, populated on session-bind later" (222), `worktreeId` on the pane (223); states the harness-neutral seam ("the per-harness resume strategy ... is a harness-neutral requirement", 215) and the home/transcript survival dependency ("session homes are ephemeral ... TM's owned Tier-1 ... before native resume is reliable", 227-229). It lists anchors + dependencies without prescribing Slice 7 implementation.

---

## Findings

### Finding 1 — [Minor] worktreeId-required guard resets a legacy canvas containing a captured-run pane (same legacy-import → rehydrate path as B2)

**The `sessionId` fold is clean; this is the adjacent `worktreeId`-REQUIRED side of the same Task B, surfaced via the exact legacy-import path B2 asks me to verify.**

Mechanism:
1. Task D `importLegacyCanvasCache` faithfully copies the legacy blob verbatim (raw string).
2. On the next rehydrate, `isPaneContentRef` now **requires** `worktreeId` on `captured-run` (plan Step 3, guard line `typeof value.worktreeId === "string"`).
3. `readContentRefs` is **all-or-nothing**: `for (...) { if (!isContentRef(ref)) return null; }` (`canvasPanePersistence.ts`). One invalid ref → `readPersistedPanes` returns `null` → `rebuildPersistedPanesFromSaved(null, ...)` → `resetPanes` → `paneStatus: "reset"`, empty canvas. (`readDockedPanes`/`isPersistedDockedPane` behave identically for docked refs.)
4. A pre-Slice-6 `captured-run` ref has no `worktreeId`, so a legacy canvas that contains one is **wiped on first reload after Slice 6 — including its healthy sibling panes** (transcript/resource), not just the captured-run pane.

The plan's persistence narrative ("legacy panes simply have it `undefined`", line 362) is true for `sessionId` but does not acknowledge that `worktreeId` becoming required defeats the very preservation the one-time import (Task D) exists to provide, for any legacy canvas with a captured-run pane. `CANVAS_STORE_STORAGE_VERSION` is not bumped (Task D Step 6 keeps `version: CANVAS_STORE_STORAGE_VERSION`), so this reset happens silently through the merge path, not via an intentional `migrate()`.

Severity rationale (why Minor, not Major): TM is single-user with no backward-compat guarantee (schema changes are expected to nuke the cache), and captured runs are process-resident (dead on any API restart anyway), so the captured-run pane itself was not going to survive. **Consider Major** if preserving a mixed legacy canvas (captured-run + transcript panes) across the Slice 6 upgrade is a goal — the headline canvas-captured-run feature makes a real user hitting this plausible.

Recommendation (pick one): (a) make `readContentRefs`/`readDockedPanes` drop only the invalid ref instead of nulling the whole map; or (b) explicitly state in Slice 6 / Task D that legacy canvases containing captured-run panes reset; or (c) tolerate a missing `worktreeId` on captured-run refs during the one-time import (back-stamp `defaultWorktreeId`).

Evidence: `www/src/session-canvas/persistence/canvasPanePersistence.ts` (`readContentRefs`, `readPersistedPanes`, `rebuildPersistedPanesFromSaved`, `resetPanes`); plan Task B Step 3 (worktreeId required on captured-run); plan Task D Step 3 (`importLegacyCanvasCache` raw copy), Step 6 (version unchanged).

### Finding 2 — [Minor] Index wording "import per legacy `workspaceHash` → one default Canvas per Space" overstates the single-blob reality

The pre-Spaces build persisted exactly ONE canvas under a single bare key (`FRONTEND_STORAGE_KEYS.canvasStore`, which Task D aliases as `LEGACY_CANVAS_CACHE_KEY`) — not per-`workspaceHash` keys (live `canvasStore.persistence.ts` uses `name: FRONTEND_STORAGE_KEYS.canvasStore`, no namespacing). `importLegacyCanvasCache` copies that single blob into whichever canvas initializes first; slice6 line 1860 states this correctly ("the single pre-Spaces canvas into whichever Space initializes first"). The index (`transport-matters-spaces--plan.md` lines 111-112) implies multiple per-`workspaceHash` legacy blobs.

Recommendation: align index wording with the slice6 single-blob semantics ("import the single legacy canvas blob into the first Space's default Canvas").

Evidence: live `www/src/session-canvas/model/canvasStore.persistence.ts` (single bare key); slice6 Task D Step 3 (`LEGACY_CANVAS_CACHE_KEY = FRONTEND_STORAGE_KEYS.canvasStore`) + line 1860; index lines 111-112.

---

## Summary

| Area | Result |
|---|---|
| A1 field + guard | ✅ correct |
| A2 persistence + legacy import | ✅ correct (no persistence-module change needed/made) |
| A3 round-trip test | ✅ present (with/without/non-string) |
| A4 deferred framing | ✅ correct (nothing populates/uses now) |
| B1 `space/` package consistency | ✅ consistent, no stragglers |
| B2 proposal resume open-item | ✅ accurate, not over-specified |
| Finding 1 | Minor (consider Major) — legacy canvas reset via worktreeId-required guard |
| Finding 2 | Minor — index wording overstatement |

No Blockers, no Majors. The just-applied `sessionId` fold is sound and ready to sign off; the two Minors concern (1) the adjacent `worktreeId`-required migration behavior on the same legacy-import path and (2) an index doc wording fix.
