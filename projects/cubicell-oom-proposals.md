# Cubicell OOM — consolidated proposals

Consolidation of three independently-briefed scout reports at
`docs/performance-audit` @ `60da3f7`, tree clean. Zero writes to `src` or
`tests`.

Inputs:

- `~/.mdx/projects/cubicell-scout-oom-writepath.md` (W) — persistence write path
- `~/.mdx/projects/cubicell-scout-oom-allocation.md` (A) — evaluation and input
- `~/.mdx/projects/cubicell-scout-oom-instrumentation.md` (I) — failure surface

12 distinct proposals after deduplication.

## 1. Proposal table

| ID | Layer | Defect (file:line) | Proposed fix | Wrong on its own terms? | Crash impact | Confidence | Cost | Depends on |
|---|---|---|---|---|---|---|---|---|
| **C1** | input / command+history | One gesture emits one authored operation per accepted value; pointer moves, key repeats and wheel ticks all call the same synchronous commit callback — `src/components/ui/scrub-field/ScrubField.tsx:52-55`, `:72-85`, `:107-125`; reaching `src/state/actions/authoredDispatcher.ts:76-103` | One `ScrubField` interaction transaction: transient local display + frame-coalesced preview during the gesture, exactly one authored operation on release, refactoring `createHistoryCoordinator` into the single gesture boundary | yes | high | high | M | — |
| **C2** | persistence | `AuthoredDurabilityUnit` retains a full `CubicellState` per queued value — `src/state/projectDurability.ts:49-57`, `:150-156`, `:598-610` | Retain the existing `ProjectProjectionState` from `compactProjectionState` instead of the whole state — `src/state/projectCommitProjectionCore.ts:52-60` | yes | med | high | S | — |
| **C3** | persistence | `CubicellState.outbox` is appended per authored edit, copied into every queued state snapshot, and has **zero readers** — writers `src/state/actions/authoredDispatcher.ts:81` and `src/state/projectDurabilityHydration.ts:141`, stripped at `src/state/projectCommitProjectionCore.ts:72`, `:78` | Delete `CubicellState.outbox` and `PendingOutboxCommit`; leave all IndexedDB outbox rows untouched | yes | med | high | S | — |
| **C4** | persistence | IndexedDB `outbox` and `localCommits` rows grow per promote with no ordinary removal — `src/persistence/indexedDbCommit.ts:214-233`, `:252-269` | Stop writing ordinary outbox/receipt rows; version bump with reset | **no — see §6** | low | low | L | C3; owner ruling |
| **C5** | persistence | Every authored projection walks the current Workbench *and all history Workbenches* and ships every referenced pose revision through both workers, including pose-neutral `patch-transition` — `src/persistence/projectRecordProjection.ts:86-125`, `src/persistence/storageRecordPreparation.ts:102`, `:204-226` | Carry an exact operation-introduced pose set on authored commits; reserve the aggregate scan for bootstrap and checkpoint | yes | high | high | M | — |
| **C6** | evaluation | The one-entry morph plan cache keys endpoint topology *and* schedule together, so a duration step discards endpoint classification and shared-edge planning the edit cannot change — `src/transport/activeTransitionPlan.ts:29-60`, `src/evaluation/sceneMorph.ts:61-107` | Split `prepareSceneMorph` into `…Topology(a,b)` and `…Schedule(topology,settings)`; keep the existing one-entry cache owner | yes | med | high | S | — |
| **C7** | evaluation | Every interior morph sample builds a new scene graph, and the incremental renderer treats that transient identity as a reason to recreate owner, indexes, packed instances and slot registry — `src/evaluation/sceneMorph.ts:127-227`, `src/scene/incrementalCubeSceneOwner.ts:111-180` | Transient unjournaled full-sync branch that retains the slot owner; then union-slot allocation per endpoint pair | yes | high | high | L | C6 |
| **C8** | failure-surface | Entering `failed`/`recovery-failed` covers the viewport with a fixed full-bleed dialog while nothing stops the transport — `src/app/PersistenceStatus.tsx:10-18`, `src/app/persistence-status.css:17-25`; five save-state setters at `src/state/projectDurability.ts:159-162`, `:325-327`, `:340-345`, `:370`, `:393` touch no transport state | One store `setSaveState` action beside `setMorphScrub`, applying the existing `withTransportPlaying(transport,false,…)` on `failed`/`recovery-failed` — `src/state/actions/transportActions.ts:20-46` | yes | high | high | S | — |
| **C9** | failure-surface | DISCARD is dropped unless status is exactly `failed` (`src/state/projectDurability.ts:356-358`) while RETRY synchronously flips it to `saving` (`:352`), unmounting the whole dialog (`src/app/PersistenceStatus.tsx:10`); DISCARD carries no `disabled` binding where RETRY does (`:38` vs `:45-47`) | Latch the dialog open across in-flight attempts; mirror the `disabled` binding; report the refusal instead of returning bare | yes | med | med | M | — |
| **C10** | failure-surface | `recovery-failed` renders no actions at all — `src/app/PersistenceStatus.tsx:29-30` vs the action row at `:36-48` — though preflight returns before touching storage (`src/state/projectDurability.ts:370-371`), so nothing was discarded | Offer "try recovery again" bound to the existing `recoverToLastCommitted`, widening the `:357` status guard | yes | low | high | S | — |
| **C11** | failure-surface | Authored edits are refused silently whenever `pendingRecovery` is set — `src/state/actions/authoredDispatcher.ts:37-40`, `src/state/actions/checkpointDispatcher.ts:25-30` — under a `saving`/`syncing` status (`src/state/projectPendingHydration.ts:42`, `:57`), so no dialog appears; the flag clears only via a re-publish `drain` cannot reach while blocked (`src/state/projectDurability.ts:256`, `:226-230`, `:315-321`) | Surface `pendingRecovery` as a distinct "editing paused" status in the existing readout (`PersistenceStatus.tsx:56-63`); separately close the guard asymmetry at `src/state/projectDurability.ts:131-141` | yes | low | high | S | guard half → C2/C4 owner |
| **C12** | persistence / shared | Requests funnel through `src/shared/workerRequestClient.ts:16-62` but replies are three independent sites with no shared helper — `src/state/projectCommitProjectionWorker.ts:42`, `src/persistence/storageRecordPreparationWorker.ts:26`, `:31`, `src/persistence/projectRecordHydrationWorker.ts:19` — and the third has no `try` at all, so any throw terminates the worker and rejects every pending request (`workerRequestClient.ts:36-42`) | Shared error envelope + the missing `catch` now; a `createWorkerResponder` mirroring the request client next | yes | med | high | S/M | — |

## 2. Deduplication

Three merges. In each, seats briefed on different layers reached the same seam
from opposite directions; that convergence is evidence, and it is the reason
C1 and C8 carry `high` confidence.

**C1 — ScrubField emission. Three of three reports.**

- A1/A2 reached it from evaluation and input: "a pointer drag is one user
  intent … every accepted value still enters the authored dispatcher".
- W1 reached it from persistence: "every rapid control value becomes a new FIFO
  unit retaining a full `CubicellState`".
- I reached it while mapping actuators: `stepBy` calls neither `onScrubStart`
  nor `onScrubEnd` (`ScrubField.tsx:107-120` vs the pointer path `:65-96`), so
  keyboard stepping is unbatched — which is why it was chosen as the repro
  actuator.

All three cite `ScrubField.tsx:107-125`. A and I additionally agree the
keyboard path's missing batch is a **user-visible undo defect independent of
the crash** (A2), and A and W independently propose refactoring the *same*
existing owner, `createHistoryCoordinator`, rather than adding a second
batcher, both warning against leaving two owners in parallel. A2 is folded into
this row: it is the same seam, and its minimal fix (open the batch on first
Arrow keydown, close on keyup/blur) is the fallback if C1 slips.

**C8 — transport keeps running behind the modal. Two of three reports.**

- A5 reached it from the frame driver: the driver's condition is transport
  playing, independent of save status.
- I reached it from the exclusion precedent: `setMorphScrub`
  (`transportActions.ts:35-46`) already forces `playing:false` for the *weaker*
  comparison-scrub case, documented at `useStagedScene.ts:54-58`.

Both cite `PersistenceStatus.tsx:5-54` and `persistence-status.css:17-25`, and
both independently conclude the policy must live in neither the dialog nor the
persistence queue. See §3 for the owner conflict.

**C12 — worker reply asymmetry. Two of three reports, and a resolved
UNVERIFIED.**

I found the structural asymmetry and left "which worker OOMs" UNVERIFIED. W§5
independently path-traced the *recovery* modal to
`projectRecordHydrationWorker` and reached the identical consequence:
`postMessage` throws, no payload is delivered, the unhandled error reaches
`workerRequestClient.onerror`, which terminates the worker and rejects every
pending request. **That resolves the second modal's worker; the first modal's
worker remains UNVERIFIED.** The hydration worker being the traced one is also
exactly the worker with no `try` — the two findings compound.

## 3. Conflicts

**3.1 C8 owner: store action vs composition effect.** A5 places the pause at
the `EditorApp` composition boundary; I place it in a store `setSaveState`
action beside the other transport exclusions. **The store owner subsumes.** The
rule already exists in the store for `setMorphScrub`, and a composition-level
effect would be a second owner of one rule — a DRY violation, and one that
fires on render rather than on the state transition. The store shape still
satisfies A5's constraint that persistence must not learn about renderer state:
the durability runtime calls a store action, and the store owns the exclusion.

**3.2 C1 subsumes W1's elegant fix.** W1-elegant ("one authored transaction
coordinator … refactor `beginBatch`/`endBatch`") and A1 are the same change
described from two sides. Ship one. W1's **minimal** fix survives separately as
C2: it does not reduce emission, it only shrinks what each unit retains, and is
therefore not an alternative to C1. See §4.

**3.3 C5 and C12 are complementary, not competing.** C5 shrinks the payload
that fails to clone; C12 makes a failed clone degrade to one failed save
instead of killing the worker and rejecting every pending request. Neither
removes the need for the other.

**3.4 C6 is a precondition for C7's benefit.** Retaining render slots across
transient frames (C7) does not help if every settings preview still discards
endpoint topology (C6). A ranks them 2 and 3 for this reason; the dependency is
recorded in the table.

**3.5 Adjudication requested: does removing the outbox make persistence
batching or coalescing unnecessary?**

**No. They are orthogonal, and neither subsumes the other.**

- The outbox is a *per-lifetime* accumulator: one entry per authored edit,
  never removed, copied into every queued state snapshot
  (`authoredDispatcher.ts:81`). Its cost scales with total edits in the session.
- The emission problem is *per-gesture* fan-out: N units, N stage writes, N
  projection round trips, N preparation round trips for one drag. Its cost
  scales with input event frequency.

Removing `CubicellState.outbox` (C3) removes one copied array from each queued
snapshot and changes the count of queued snapshots by zero. Shipping C1 reduces
N to 1 per gesture and leaves the outbox growing once per committed gesture,
forever. They attack different axes.

The one real interaction: C1 reduces the outbox's growth *rate* by the same
factor it reduces commits, which lowers C3's urgency without removing its
justification — an array with zero readers is unjustified at any growth rate.

**3.6 C3 and C4 are not one change.** W3 presents "remove the outbox ledgers" as
a single proposal with a minimal and an elegant slice. The two ledgers have
different consumers and must be split, because one of them is live. See §6.

## 4. The owner's standing decision

> During a pointer drag the value is transient interaction state; the domain
> event happens ONCE on release. A bounded queue with last-one-wins may be added
> as defence in depth but is NOT a licence to keep emitting per-move commands.

Compliance review of every proposal:

| Proposal | Verdict |
|---|---|
| C1 | **Complies, and implements the decision.** "On pointer up, flush the exact final pointer value … dispatch one authored operation"; "There is no independent persistence collapser, debounce, or delayed queue in this proposal." Its per-frame preview is transient interaction state published to a session-only preview, not a domain event. |
| C1, wheel sub-case | **Flag for the owner's ruling.** A proposes folding wheel deltas and committing the aggregate once per frame, because wheel has no release event. That is more than one domain event per continuous wheel interaction. It does not contradict the decision as written (which scopes to pointer drags) but it is the only place in the set where a gesture-like interaction still emits per-frame. Needs an explicit ruling: per-frame, or an idle-terminated wheel gesture. |
| **C2** | **Flagged.** It keeps one durability unit per accepted value and only shrinks what each retains. It is absorption, and shipping it *alone* would read as exactly the licence the decision forbids. Permitted only as defence in depth alongside C1, never instead of it. |
| C3, C4, C5 | Comply. No emission semantics. |
| C6, C7 | Comply. Evaluation-side; no domain events. |
| C8, C9, C10, C11, C12 | Comply. No emission semantics. |

Existing precedent worth naming: the durability runtime already does bounded
last-one-wins for `user-project-state` units — it replaces the tail unit rather
than appending (`src/state/projectDurability.ts:133-135`). That is the shape the
owner permits as defence in depth, and it is already in the codebase, so any
such queue should reuse it rather than invent a second one.

## 5. Recommended ship order

Removal ranks above absorption throughout.

| # | ID | Kind | Reason for this position |
|---|---|---|---|
| 1 | **C8** | removal (of work during the incident) | Smallest change on the list, two seats agree, and it is the only item that reduces harm *while* the failure is happening rather than after. It stops the app making the failure worse: the loop that generates the pressure keeps running behind a dialog that covers the control which would stop it. Reuses `withTransportPlaying` verbatim; no new state. |
| 2 | **C3** | removal | Pure deletion, zero readers verified across `src` and `tests`, no persisted shape change. Ships independently of everything else. Narrowed from W3 to the in-memory mirror only — see §6. |
| 3 | **C1** | removal | The largest single reduction in work, at the point where the work is created, before it reaches evaluation *or* persistence. Three seats converged on it. It also fixes the keyboard undo defect at the same boundary, and establishes the preview contract that C6 and C7 build on. Placed third only because it is M-cost and the two above are S-cost and independent. |
| 4 | **C5** | removal | Removes aggregate-sized pose materialization from a delta commit, in both workers. Independent of C1: it shrinks each commit, where C1 reduces the count. Together they multiply. |
| 5 | **C6** | removal | Small, precise, one-entry bound preserved. Removes endpoint rescan from every settings preview and is the precondition for C7's benefit. |
| 6 | **C12** | absorption | Makes the remaining failure degrade instead of killing the worker. Ranked below the removals by principle, but the missing `catch` in `projectRecordHydrationWorker.ts:17-30` is a live defect on its own and its half of the fix is S-cost. Take the shared envelope and the `catch` here; defer the responder. |
| 7 | **C9**, **C10**, **C11** | correctness | The escape-hatch and status-visibility fixes. Cheap and independent; batch them. C11's guard-asymmetry half waits on whoever owns the durability queue lifecycle. |
| 8 | **C7** | removal | Largest removal remaining, largest cost, depends on C6 and reads better after C1's preview contract exists. |
| 9 | **C2** | absorption | Last, and only if measurement after C1 still shows queued-unit retention. Shipping it earlier risks being mistaken for a fix to the emission problem. |
| — | **C4** | blocked | Not scheduled. See §6. |

## 6. Risk: is the outbox vestigial or a lost feature?

Searches run at `60da3f7`:

- `git log -S "PendingOutboxCommit" --oneline` → **one** commit: `2aa9362`
  `feat(persistence): cut over to committed IndexedDB storage (#107)`.
- `git log -S "outbox" --oneline` → **7** commits: `2aa9362` (#107), `ad5c6f6`
  (#108), `ee484e0` (#109), `c51e976` (#114), `17a10de` (#125), `242c4b4`
  (#127), `bc71cb1` (#132). All local persistence or budget work.
- `git log -S "loadOutbox" --oneline` → `ee484e0` (#109)
  `feat(persistence): forward rebase stale commits`.
- `git log --diff-filter=A --name-only -- "src/**sync*" "src/**supabase*"` →
  no sync or Supabase source file has ever been added.
- `2aa9362`'s message body contains `docs: record collaboration readiness
  principle` and `docs: define storage and collaboration readiness plan`.

**Verdict: neither vestigial nor abandoned. It is deferred-by-design
scaffolding, and one of its two halves has a live local consumer today.**

1. **It never had a remote peer, and that is by design, not by decay.**
   `STORAGE.md:38-40`: "Live collaboration is deferred from V1. Stable
   identities, operations, revisions, membership, and state separation are
   required in V1 so adding collaboration does not replace the persistence
   model." `STORAGE.md:98`: "The remaining gaps are hosted concerns … The local
   outbox and forward rebase path are ready for that layer." The outbox was
   introduced by the commit that also wrote the collaboration-readiness plan.
   Removing it is a product decision to discard planned capability, not a
   cleanup.
2. **The IndexedDB outbox rows back a shipped local feature.**
   `syncForwardRebase` reads them through `storage.loadOutbox(this.address)`
   (`src/state/projectDurability.ts:459-464`) on the `"outbox"` source, reached
   from `installCommitted` (`:185`). `STORAGE.md:88-94` describes exactly this
   as implemented: "Installing a newer committed head applies the same forward
   rebase to retained outbox work." **C4 would delete a working stale-writer
   recovery path**, not dead code.
3. **The in-memory mirror is the only part with no reader.**
   `CubicellState.outbox` has two writers (`authoredDispatcher.ts:81`,
   `projectDurabilityHydration.ts:141`), one pass-through (`:174`), and zero
   reads anywhere in `src` or `tests` — projection explicitly substitutes an
   empty array (`projectCommitProjectionCore.ts:72`, `:78`). The remaining
   `.outbox` hits in `memoryProjectStorage.ts` are that port's own storage-side
   state, and every `tests/` hit is a storage-layer row assertion. Deleting it
   removes a mirror, not a ledger.

This is the failure mode the repo has already recorded once: declared-but-unused
code that turns out to be a deferred or lost feature. **C3 (delete the in-memory
mirror) is safe on the evidence. C4 (stop writing the IndexedDB rows) is not a
cleanup and must not ship on an OOM ticket** — it removes a live recovery path
and forecloses a documented plan. It needs an explicit owner decision to drop
collaboration readiness, taken on its own merits.

W's ship-first recommendation is therefore adopted **only in its narrowed
form**: remove `CubicellState.outbox`; leave the outbox and `localCommits` rows
alone.
