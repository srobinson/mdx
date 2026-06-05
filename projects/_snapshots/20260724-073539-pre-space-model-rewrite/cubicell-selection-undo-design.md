# Cubicell: Selection Undo — Design v2 (Ephemeral Assembly Model)

**Status:** v2 rework — replaces v1's persistent-unified model after Stuart's
live-drive of PR #45 (2026-07-10). v1 archived at
`.archive/cubicell-selection-undo-design.v1.md`.
**Arbitration and structure locked** by Stuart's ruling and Opus's final
structure post (journal, not editTag; state fields, not closure).

---

## 1. The two concepts (the correction)

v1 conflated two selection-history ideas. They are now separate:

**(a) Selection as edit context — SHIPPED, KEEP UNTOUCHED.** Every edit entry
in `DocumentHistory` carries the selection it was made under
(`createPresentEntry`), and `applyHistoryStep` restores it on undo/redo.
Undoing an edit restores both the document and the selection context, even
across a later clear. This is on main, Stuart confirmed it, and nothing in
this doc modifies it.

**(b) Multi-select assembly undo — THIS DOC.** Building a selection set is an
assembly gesture: seed pick, grow, prune, act. Undo peels the assembly.
Locked semantics:

1. **Set-only.** `setSelection` (single pick) is plain state — cursor-like
   navigation, never on undo, no journal token, and it does not clear edit
   redo.
2. Only set mutations feed the assembly history: `setSelectionSet`,
   `applySelectionResult` when it yields a multi-member set,
   `toggleSelection`.
3. **Ephemeral and set-scoped.** Assembly history is never persisted and
   never enters `DocumentHistory`. It lives and dies with the current set.
4. **Discard on clear.** `clearSelectionSet` or the set going empty discards
   the assembly history entirely. After a clear, Cmd+Z falls through to the
   last edit; it never resurrects the set. (Undoing an *edit* may still show
   a set — that is (a) restoring the edit's own context, which is intended.)
5. **Edits do not discard.** Extrude mid-assembly, keep peeling the same set.
6. **Baseline = seed pick.** Peeling to the bottom restores the single pick
   the set grew from, not empty.
7. **One Cmd+Z key.** Most-recent-action-first across both lanes.

## 2. Structure (locked)

Two new transient **state** fields in `CubicellState` — not closure
variables. Both are excluded from `partialize` (exactly like `history`), so
`setState(initial)` resets them for free: the stale-marker bug class that
forced Slice 3's guard/`resetCubicellHistoryBookkeeping` hack is
structurally gone, along with the marker itself.

```
selectionAssembly: {
  baseline: CubeSelection | null   // the seed pick the set grew from; null
                                   // when the set had no single seed (grown
                                   // from an (a)-restored set or a
                                   // from-nothing query)
  past: AssemblySnapshot[]         // set states, oldest→newest
  future: AssemblySnapshot[]       // peeled states available to redo
} | null                           // null = no assembly in flight

actionJournal: {
  past: Array<{ lane: 'edit' | 'assembly' }>
  future: Array<{ lane: 'edit' | 'assembly' }>
}
```

An `AssemblySnapshot` is the selection result pair
`{ selection, selectionSet }`. The journal is the **single source of global
ordering**; each lane keeps its own past/future for payloads
(`DocumentHistory` for edits — unchanged — and `selectionAssembly` for set
states). `lane` is the only token payload.

### Wiring rules (locked)

| Event | Effect |
|---|---|
| Edit push (`recordHistory`, incl. compound `selectionResult` fold) | `history` push (unchanged) + journal `{lane:'edit'}` + clear BOTH futures |
| Assembly mutation (`setSelectionSet`, `applySelectionResult`→multi, `toggleSelection`) | snapshot prior set state to `selectionAssembly.past` (first mutation also records `baseline` = the seed pick) + journal `{lane:'assembly'}`; clears BOTH futures (edit redo included) |
| `setSelection` (single pick) | plain state write: no journal, no future clearing |
| Clear (`clearSelectionSet` / set-goes-empty) | prune every `assembly` token from journal past AND future; `selectionAssembly = null`. Edit tokens untouched. No restore point. |
| **Undo** | pop journal `past` top → route by lane: `edit` → `undoDocumentHistory` + `applyHistoryStep` (with (a) restore); `assembly` → peel one snapshot (state → `assembly.future`, token → journal `future`) |
| **Redo** | pop journal `future` top → route by lane, reverse of undo |
| Edit undo/redo lands | reconcile assembly snapshots against the restored document: drop members whose cube no longer exists; terminate the assembly (discard, prune tokens) if fewer than 2 remain |
| `applySelectionResult` → single member, no live set | plain navigation, no assembly entry |
| Collapse of a live set to one member | ends/discards that assembly: survivor == seed → terminal baseline; different survivor → plain state, new potential seed |
| Peel reaching the bottom | restores the `baseline` seed pick (not empty); assembly becomes an empty-past shell peelable no further |

Semantic no-ops (write produces an identical set) neither snapshot nor
journal — `isSameSelectionResult` is the equality.

## 3. Per-action rulings

| Writer / path | Ruling |
|---|---|
| `setSelection` (viewport pick, `select` command) | Non-history navigation. `reversible: false` restored on the `select` command. |
| `setSelectionSet` | Assembly mutation → snapshot + journal token. |
| `applySelectionResult` (`select-query`) | Multi-member result → assembly mutation. Single-member from no live set → navigation. Collapse of a live set → ends the assembly (§2 table). `reversible: true` stays (truthful for the set-yielding case). |
| `toggleSelection` (`select-toggle`) | Assembly mutation. `reversible: true` stays. |
| `clearSelectionSet` | Discard: prune + null, no restore point. Not undoable. |
| Compound edits (`selectionResult` fold: neighbor add, resize, preset) | One edit token, one `DocumentHistory` entry — the v1 fold seam stays exactly as shipped in #45. The derived selection is edit outcome, not an assembly step. |
| `applyBuildModeActive(true)` / `resetEditorSession` | Selection clear = assembly discard (prune + null). No history effect on the edit lane. Build-mode restore graft from #45 stays. |
| `applyPickMode` conversion | Restates the set's vocabulary in place: reconcile snapshots to the new vocabulary is NOT attempted — a conversion while an assembly is open **terminates the assembly** (the set's members changed meaning; peeling across a vocabulary change is undefined). Bare mode change: no effect. |
| `applyHistoryStep` | (a) restore, untouched; triggers assembly reconcile per §2. |

## 4. Integrity (unchanged from v1 + one addition)

`reconcileSelection` at the three commit/capture seams (`updateScene`,
`replaceDocument`, `createPresentEntry`) stays exactly as shipped in #45 —
entries remain trusted atomic pairs and live selection can never dangle.

**Addition:** assembly snapshots are reconciled against the restored
document on every edit undo/redo (§2 table). The same `reconcileSelection`
helper is reused per snapshot. The assembly terminates when NO snapshot
(live, past, or future) remains multi-member after reconciliation — if any
peelable state can still reach a multi set, the assembly survives.
*(Amended 2026-07-10 at review: sharper than the original "live below 2
terminates" wording — a valid peel target keeps the assembly useful.)*

## 5. Refine-draft sessions

The chip's close set (commit / cancel / blur / subject reset / any edit /
any non-refine selection write) stands from v1 as the chip-session
lifecycle.

**Provisional ruling (the one item needing orchestrator confirmation):**
refine re-dispatches carrying the same `against` baseline REPLACE the top
assembly snapshot rather than pushing — the whole refine session is one
assembly step, and cancel-to-baseline restores the pre-session set with no
dead step. Without this, every chip tweak becomes a peelable snapshot.
Alternative if replacement is unwanted: refine dispatches skip the assembly
entirely and only the committed result snapshots.

## 6. Acceptance suite (locked traces first)

1. **Extrude-then-peel LIFO:** click A → +B → +C → extrude → Cmd+Z undoes
   the extrude (most recent action); further Cmd+Z peels C, then B, then
   restores baseline A. Journal ordering, not lane priority.
2. **Clear then edit-undo restores via (a):** {A,B,C} → extrude → clear →
   Cmd+Z undoes the extrude AND shows {A,B,C} as that edit's captured
   context. No peel history exists (assembly stays discarded).
3. **Redo after clear:** assemble → peel (undo) → clear → redo is a no-op
   for the assembly (future pruned); a pending edit redo is unaffected by
   `setSelection` navigation but cleared by a new assembly mutation.
4. **Collapse-to-one:** {A,B} → query collapses to B → assembly discarded;
   Cmd+Z falls through to the edit lane. Survivor == seed → terminal
   baseline case asserted separately.
5. **Interleave with clear:** A → +B → extrude → +C → clear → Cmd+Z: the
   assembly tokens for +B/+C are pruned, so undo hits the extrude and (a)
   restores its captured context {A,B}.
6. **Edits do not discard:** A → +B → extrude → +C: journal is
   [asm, edit, asm]; three Cmd+Z = peel C, undo extrude, peel to baseline A.
7. **`setSelection` is navigation:** never journals, never clears edit redo
   (edit → undo → click other cube → redo still re-applies the edit).
8. **Baseline seed:** peel to bottom → seed pick selected, not empty.
9. **Reconcile on edit undo:** assembly contains a cube created by the last
   edit → undo the edit → snapshot drops the member; below 2 members the
   assembly terminates.
10. **(a) regression guard:** edit entries still capture and restore
    selection exactly as on main.
11. **Persistence:** `selectionAssembly` and `actionJournal` are absent from
    persisted state; rehydrate starts clean.
12. **Compound fold regression:** neighbor add is ONE edit token and one
    undo unit (doc + derived selection).
13. **No-op writes:** identical-set mutation neither snapshots nor journals.
14. **Pick-mode conversion mid-assembly** terminates the assembly; edit lane
    untouched.

## 7. Rework slice sketch (replaces Slice 3's (b) wiring)

**Reverts (delete completely, including now-dead helpers and their tests):**
- `selectionRunOpen` marker and all its clear points.
- `recordedSelectionWrite` and the `writeSelection` routing of the five
  writers.
- `recordSelectionHistory` and `dropLastHistoryEntry` in
  `documentHistory.ts` (they existed only for the unified selection path —
  no parallel dead code).
- `setSelection` / `clearSelectionSet` history recording; `reversible`
  reverts to `false` on the `select` command.
- `invalidateSelectionRedo` and the invisible-effective-clear history
  writes.

**Keeps (shipped in #45, still correct):** (a) restore in
`applyHistoryStep` + build-mode graft; compound-edit `selectionResult`
fold; `reconcileSelection` at the three seams; `editorHoldsSelection`;
the editor no-churn guard; `isSameSelectionResult` (now the assembly
no-op/equality helper).

**New:**
1. `selectionAssembly` + `actionJournal` state fields, `partialize`
   exclusion, types beside `CubicellState`.
2. Pure assembly/journal operations in a new `src/state/selectionAssembly.ts`
   (snapshot push, peel, prune, reconcile-against-scene) — same layering
   discipline as `documentHistory.ts`.
3. Store wiring per §2 table; `undo`/`redo` become journal routers.
4. Command metadata per §3.
5. §6 suite; delete the v1 unified-stack tests that encode rejected
   semantics (do not port them).

## 8. Followup (unchanged, recorded): extract view-lane from the document

Still valid: lifting projection/polarity out of the document deletes the
`withLiveViewLane` graft. The v1 marker this followup would also have
deleted is already gone.

## 9. Non-goals

- Persisting assembly history or the journal across sessions.
- Peeling across pick-mode vocabulary changes (§3: conversion terminates).
- Selection-set diff/merge semantics beyond whole-set snapshots (snapshots
  are cheap reference copies; the set algebra already canonicalizes).
- Any change to (a), `DocumentHistory` structure, or the view-lane rules.
