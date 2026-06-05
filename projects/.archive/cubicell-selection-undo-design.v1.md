# Cubicell: Selection on the Undo Timeline — Design

**Status:** Draft v1 — four-family panel consensus (Fable lead, Opus, Grok, GPT/codex), 2026-07-10.
**Decision already made (not relitigated):** selection is undoable and joins the same undo stack as edits. Unified timeline, Figma/Linear model. This doc specifies how.

---

## 1. The reframe: the seam already exists

`DocumentHistoryEntry` already carries selection alongside the document
(`src/state/documentHistory.ts`):

```
DocumentHistoryEntry = { document, selection, selectionSet }
```

`createPresentEntry` (`src/state/cubicellStore.ts`) already captures the live
selection into every entry, and `applyHistoryStep` already restores it on every
undo and redo, including the pick-mode-follows-selection rule. Edit-boundary
selection restore (sub-decision 3) is therefore shipped behavior today: undoing
an edit already restores the selection context the edit was made in. This stays.

The entire gap is one-directional: **selection writes never push an entry.**
Attaching selection to the timeline means making selection changes record
restore points through the machinery that already exists.

**Accepted spine (locked):** no new step kind, no parallel stack, no per-step
payload. One entry type, one stack, one restore path. `applyHistoryStep` needs
no structural change. A selection-only entry shares its document by reference
(entries are reference snapshots), so it costs nothing.

## 2. The undo unit and coalescing (sub-decisions 1 and 2)

### The unit

A **selection run**: an unbroken sequence of effective selection changes with no
document-lane mutation and no undo/redo in between. The run's single restore
point is the selection that was live before the run began. Undo of a run is one
step back to that pre-run selection. This is the Figma semantics Stuart asked
for: bare selection changes are independently undoable, consecutive ones
coalesce.

### The boundary key (locked, with the panel's two repairs)

The naive key — coalesce while `past.at(-1).document === state.document` — is
wrong on both sides, proven by concrete traces:

1. **View-lane transparency (Grok's attack).** Projection and polarity toggles
   go through `updateScene({ recordHistory: false })`, which reallocates the
   document wrapper without touching history. Raw reference equality would
   split `Select F1 → projection toggle → Select F2` into two undo units. View
   chrome must be transparent to selection coalescing (see PR #41: the
   projection toggle is deliberately outside undo).
2. **Undo/redo are boundaries (Grok, GPT, Opus, and Fable independently).**
   Any key that survives an undo lets the next selection change coalesce onto
   an entry the undo just exposed: the following undo then skips the restored
   selection, or worse, silently reverts an edit (Opus's
   `Select A → Edit → Select B → Undo → Select C` trace, where undoing C pops
   the edit's entry). Every applied `applyHistoryStep` must close the open run.

**Locked model — a boolean open-run marker.** One bit, `selectionRunOpen`, in
the store closure beside the existing `historyBatch` bookkeeping (transient,
non-rendering, non-persisted, the established idiom). An integer document-lane
generation is behaviorally equivalent; the panel's ruling and the lead-author
call is the marker, because it is minimal and earns identical coverage. A
selection run is thereby scoped to exactly one document-lane generation.

| Event | Effect |
|---|---|
| Effective selection write, marker clear | **Record**: push pre-change entry, set `selectionRunOpen = true` |
| Effective selection write, marker set | **Coalesce**: clear `future` only, no push |
| Real edit push (the branch of `recordHistory` that actually pushes, so a scrub batch clears once) | clear marker |
| `undo` / `redo` when a step applies | clear marker |
| No-op pop (§5) | pop dead entry, clear marker |
| View-lane write (`recordHistory: false`) | touches nothing |
| Semantic no-op selection write | nothing: no push, no future clear |

Predicate: record iff `!selectionRunOpen`. Redo clearing the marker is
deliberate (Grok's test 3): after a redo lands on an exact selection, the next
selection change is a new gesture and records a new unit.

### Redo invalidation, decoupled (Opus's seam, locked layering)

An effective selection change is a new action, so it always kills the redo
branch, even when coalesced. `pushDocumentHistory` couples clear-future with
append-past; edits keep it unchanged. The selection path gets one new pure
sibling in `documentHistory.ts`:

- `recordSelectionHistory(history, present, coalesce: boolean)` — the record
  branch delegates to `pushDocumentHistory` (clear + append, unchanged); the
  coalesce branch returns `{ future: [], past }`, or `history` untouched when
  `future` is already empty (no object churn on the hot path).

**Layering rule (locked):** the coalescing heuristic never enters the pure
history layer. `documentHistory.ts` stays marker-agnostic and takes a plain
boolean; the marker lives store-local and transient. This keeps the §8
followup a clean deletion: when view-lane state leaves the document, the
marker and the `withLiveViewLane` graft both delete without touching history
structure.

### The store seam (Opus's composer)

One DRY composer through which every recordable selection writer flows:

- `recordedSelectionWrite(state, editor)` — reads the marker to compute
  coalesce, sets it, returns `{ editor, history }` via
  `recordSelectionHistory(state.history, createPresentEntry(state), coalesce)`.

Ordering is free and atomic: `createPresentEntry(state)` reads the pre-change
state inside the single zustand `set` updater. Selection writes never touch
`state.document`, so the captured entry shares the live document reference. No
transient intermediate state is observable; the atomic-write boundary that
motivated `applySelectionResult` is preserved.

`historyBatch` and the selection seam do not interact: the batch folds
scrub-drag scene edits, which move no selection. If a future feature interleaves
drag and selection, revisit then.

**Correctness property:** at most one selection restore point exists per open
run, holding the pre-run selection; any effective selection change kills redo;
undo of a run is a single step to the pre-run selection; view-lane writes are
invisible to all of it.

## 3. Per-action rulings (sub-decision 1, concrete) — GPT's table, locked

| Writer / path | Ruling | Behavior |
|---|---|---|
| `setSelection` (viewport pick, `select` command) | **Undoable** | Records at run start, then coalesces. Its optional paired `setSelectionSet` call stays in the same unit (second write coalesces by the marker). |
| `setSelectionSet` (explicit set edit) | **Undoable** | Same rule; the paired call cannot create a second entry. |
| `applySelectionResult` (`select-query`) | **Undoable** | One atomic query result; consecutive query and refine re-dispatches coalesce. |
| `toggleSelection` (`select-toggle`, shift-pick) | **Undoable** | Same rule. |
| `clearSelectionSet` (explicit Clear affordance) | **Undoable** | Same rule; undo restores the cleared set. |
| Post-edit selection walk/clear (neighbor add at slot, add-to-selected-faces, resize, preset) | **Invisible as a separate unit** | Derived result of the edit: document and repaired/advanced selection land in the same atomic edit transaction, one entry. The edit clears the marker; the next explicit selection change opens a fresh run. |
| `applyBuildModeActive(true)` selection clear | **Invisible** | Build mode's invariant is an empty selection; an undoable clear would restore selection into an active placement tool. Derived mode state. If the clear was effective: forced-coalesce clear-future + marker clear, no push. Leaving build mode changes no selection. |
| `applyPickMode` / `cyclePickMode` with non-null conversion | **Undoable, own boundary** | The vocabulary restatement (cube to 6 faces / 12 edges) is a lossy, user-initiated selection transformation. A conversion **closes any open run and opens its own restore point**, so undo restores the pre-conversion selection (§6 test 13); bare selection changes after it coalesce into the new run; consecutive conversions each record (N mode cycles = N units — accepted: each conversion is independently lossy, and avoiding it would cost a second marker bit). Restore already derives `pickMode` from the restored selection. A mode change with no conversion is invisible. *(Amended 2026-07-10 by panel ruling: the original "records/coalesces normally" contradicted §6 test 13.)* |
| `resetEditorSession` | **Invisible** | Wholesale session teardown, not selection intent. If selection changed: forced-coalesce clear-future + marker clear, no push. |
| `replaceDocument` | Already an edit push | Unchanged; entry carries selection context as today. |
| `applyHistoryStep` (undo/redo itself) | Never records | Consumes history; closes the run marker. |

Uniform rule under the table: every *effective* selection mutation, including
history-invisible derived clears, routes the clear-future seam and resets or
updates the marker. Semantic no-ops do nothing at all.

**Restore into build mode (lead-author ruling):** `applyHistoryStep` currently
restores selection unconditionally. While `buildModeActive`, the restored
selection grafts to null at the same seam where `withLiveViewLane` grafts the
view lane: session-lane state takes precedence over the restored snapshot, by
the exact pattern already established. The document still restores.

**Command metadata:** the three registrations in
`src/interaction/commands/selection.commands.ts` flip `reversible: false` to
`true`. Nothing consumes the flag yet; this is metadata truthfulness.

## 4. Selection integrity (GPT's ruling, locked)

**Invariant:** every history entry's selection is valid for that entry's
document. Entries are atomic pairs captured from one consistent state, and
restore swaps both together, so a restored selection can never dangle —
provided live state is kept consistent at the moment of capture.

**Repair at commit/capture, never restore-only.** A delete or replace can make
the live selection dangle immediately; restore-only repair would leave invalid
live state and could capture it into redo. One new pure helper beside the
selection algebra in `src/domain/selection.ts`:

- `reconcileSelection(scene, active, set)` — filters members whose `cubeId` no
  longer exists, reuses `createCubeSelectionSet` for canonical dedupe/collapse
  and `resolveActiveMember` for deterministic active choice. Zero members →
  `null / null`; one → active plus null set (store convention); many → valid
  active plus canonical set. No existing normalizer does this job (verified);
  `ensureSceneScore` / `repairScore` are the precedent for repairing at the
  write seam.

Applied in the atomic document-write seam (`updateScene`, `replaceDocument`) so
document and repaired selection land together, and again in
`createPresentEntry` as the entry-invariant belt. `applyHistoryStep` then
trusts its entry: the `withLiveViewLane` graft changes only projection and
polarity, which cannot invalidate a selection. Undo-of-delete restores the old
document with its old valid selection; redo restores the new document with its
already-repaired selection.

## 5. The refine-draft session (sub-decision 2) — Grok's ruling, locked

The refine chip is a **UI session, not a second history mechanism**. It rides
the same selection run: every re-dispatch is a coalescing selection write, so
the whole session collapses to one undo unit with no special casing. The chip
freezes its baseline `{selection, selectionSet}` at open and stamps it as
`against` on every re-dispatch.

**Canonical close set** (chip stops stamping `against`; single source of truth):

1. Commit (explicit apply / Enter)
2. Cancel (Escape / explicit cancel)
3. Blur / unmount (chip loses focus or is torn down)
4. Subject reset (pick-mode restate, or a clear that is not a refine tweak)
5. Any edit (any history-recording document mutation)
6. Any non-refine selection write (viewport hit, palette/LLM dispatch not
   carrying this session's `against`)

Non-closes: field tweaks, combine-mode flips, expression edits re-dispatching
with the same `against`.

These close events end the *chip session only*. The *history run* closes only
at document-lane edits and undo/redo (§2). So `select A → refine → commit B` is
one selection run with the pre-A restore point — refine is deliberately not
isolated from adjacent bare selects; isolating it would require a forced record
at chip-open and fight the coalescing rule. Rejected.

**No-op discard (dead-step pop), general rule:** on a coalescing selection
write, if the new live `{selection, selectionSet}` equals the open run's
restore-point selection, pop that dead entry and close the run (undo would
restore what is already live). Equality via a small
`isSameSelectionResult(a, b)` helper built on the existing `isSameSelection`
(id + kind; set comparison order-insensitive). This generically covers
refine-cancel-to-baseline — the common case — and any manual loop back to the
starting selection. The pop also clears `future` if the write was effective at
any intermediate point (redo of an abandoned intermediate is void).

## 6. Acceptance suite

Store-level integration tests (zustand store + registry dispatch), plus unit
tests for the two pure functions. The panel's attack sequences are the spec:

1. **View-lane transparency:** Select F1 → projection toggle → Select F2 →
   one undo restores the pre-run selection (one unit, not two).
2. **Undo is a boundary:** Select F1 → Select F2 → undo → Select F3 → undo
   restores the pre-F3 selection (the one the first undo landed on), not the
   prior edit.
3. **Redo is a boundary:** Select F1 → undo → redo → Select F2 records a new
   unit.
4. **Redo invalidation:** Select A → undo → Select B (coalesced or not) →
   redo is a no-op (future cleared).
5. **Run coalescing:** Select A → Select B → Select C → one undo restores the
   pre-A selection; redo restores C exactly.
6. **Edit boundary restore (regression guard, shipped behavior):** Select S →
   edit → undo restores both the pre-edit document and S.
7. **Edit exposure (Opus's trace):** Select A → edit → Select B → undo →
   Select C → undo restores the B-run selection with the edit intact (never
   reverts the edit).
8. **Refine collapse:** open refine → N tweaks → commit → one undo restores
   the pre-refine (pre-run) selection.
9. **Refine cancel no-op:** open refine → tweaks → cancel to baseline → no
   dead entry: the next undo does something real.
10. **Loop-back no-op:** Select A → Select B → Select A (exact) → no dead
    entry.
11. **Integrity:** select cube → delete it (edit) → live selection repaired
    to null in the same transaction → undo restores cube and selection →
    redo restores deletion and null selection.
12. **Paired write atomicity:** `select` command with `selection` +
    `selectionSet` produces exactly one entry.
13. **Pick-mode restate:** cube selected → pick mode to faces (conversion) →
    undo restores the cube selection and cube pick mode.
14. **Build mode:** selection live → enter build mode → not undoable, redo
    branch dead; undo of a prior edit while build mode active restores the
    document with selection grafted to null.
15. **Scrub batch closes the run once:** open a selection run → begin batch →
    N scene writes → end batch → exactly one edit entry, and a following
    selection change records a fresh restore point (the batched edit cleared
    the marker exactly once).

## 7. Implementation slice sketch (no code)

1. **`src/state/documentHistory.ts`** — add
   `recordSelectionHistory(history, present, coalesce)`, delegating to
   `pushDocumentHistory` on record. Unit tests.
2. **`src/domain/selection.ts`** — add `reconcileSelection` and
   `isSameSelectionResult` beside the existing algebra; export via domain
   index. Unit tests.
3. **`src/state/cubicellStore.ts`** — add the `selectionRunOpen` marker to
   the closure beside `historyBatch`; clear it in the pushing branch of
   `recordHistory` and in `undo`/`redo` when a step applies; add the
   `recordedSelectionWrite` composer (with the no-op pop) and route the five
   undoable writers through it; forced-coalesce clear-future + marker clear
   in the two invisible-but-effective clears; `reconcileSelection` in
   `updateScene` / `replaceDocument` / `createPresentEntry`; build-mode
   selection graft in `applyHistoryStep`. Audit every compound-edit path
   (neighbor add at slot, add-to-selected-faces, resize, preset): scene
   change and derived selection must land in ONE recording `updateScene`
   transaction (§3 fold rule) — a post-edit `writeSelection` would create a
   second undo unit.
4. **`src/interaction/commands/selection.commands.ts`** — flip `reversible`
   to `true` on the three registrations.
5. **Refine chip** — freeze baseline at open; apply the §5 close set as the
   single source of truth for stamping `against`. No history-specific work.
6. **Tests** — the §6 suite.

Order: 1 → 2 → 3+4 → 5 → 6 alongside each. Steps 1 and 2 are pure and
independently landable.

## 8. Followup (recorded, out of scope): extract view-lane from the document

Projection and polarity being embedded in the document scene is the sole reason
`applyHistoryStep` needs the `withLiveViewLane` graft, the reason document
identity changes without an edit (the §2 hole), and part of why the run marker
must live outside history. Lifting view-lane state out of the document would
retire these workarounds in one structural move: raw document identity would
again be a truthful document-lane key, and the graft deletes. High blast radius
(scene type, `updateScene`, renderers, morph, PR #41 surface). Separate future
slice; do not bundle.

## 9. Non-goals

- History persistence: `partialize` continues to exclude `history`; entries
  remain in-memory reference snapshots. Command payloads stay serializable and
  actor-agnostic — key, palette, and LLM dispatch are indistinguishable to the
  store, and nothing here inspects the actor.
- Selection-during-scrub-batch interleaving: no current feature produces it.
- Isolating refine from adjacent bare selection changes (rejected, §5).
