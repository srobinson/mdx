# cubicell persistence growth log

Read-only snapshots of IndexedDB `cubicell.projects` on `http://localhost:4174`.
Snapshot script: `scratchpad/store-snapshot.js` (opens with no version argument so
it never triggers an upgrade; every transaction is `readonly`).

Purpose: measure what authoring actually costs in stored records, so the outbox
disposition is decided on measured growth rather than on a code reading.

## Method

1. Open one tab on the origin, run the snapshot, close the tab. The tab is closed
   between snapshots so the observer is never a second writer to the same store.
2. Record what was authored between snapshots, in the user's own terms.
3. Derived numbers that matter: records per state, records per edit, KB per state,
   and the outbox share of total bytes.

## Snapshots

### 2026-08-04T03:43Z — baseline, immediately after Stuart cleared everything

All stores empty. Wire version 8.

| store | records | KB |
| --- | --- | --- |
| assets | 0 | 0 |
| drafts | 0 | 0 |
| history | 0 | 0 |
| localCommits | 0 | 0 |
| outbox | 0 | 0 |
| poseRevisions | 0 | 0 |
| projects | 0 | 0 |
| userProjectState | 0 | 0 |

Total `cubicell.projects`: 0 KB.
Origin `navigator.storage.estimate().usage`: 4.66 MB, which is therefore almost
entirely NOT this database (caches, service worker, and the unrelated Firebase
databases in this origin). Useful to know: origin usage is not a proxy for
document size.

### Prior state, for reference — 2026-08-04T03:1xZ, before the reset

33 states, `committedRevision` 289, one `structure` asset.

| store | records | KB |
| --- | --- | --- |
| outbox | 689 | 3,684.2 |
| history | 4 | 887.5 |
| poseRevisions | 131 | 618.2 |
| localCommits | 805 | 409.4 |
| assets | 1 | 30.4 |
| userProjectState | 1 | 0.8 |
| projects | 1 | 0.4 |
| drafts | 0 | 0 |

Total 5.5 MB, of which the outbox was 67%. Quota at the time: 10,244 MB, usage
4.15 MB, 0.04% consumed, localStorage 0.6 KB. So the earlier `quotaRisk=high`
verdict was not supported: the queue is dead weight with a growth rate, not a
quota failure in waiting.

### 2026-08-04 — controlled sample on :4174 (preview), two states

Authored from the zero baseline: State 1 with one cube, State 2 with three cubes
in a row, one transition set to 1200 ms. Snapshot run by Stuart in his own tab,
so no observer tab was open. A repeat of the zero baseline immediately before
authoring confirmed all stores empty.

| store | records | KB | KB/record |
| --- | --- | --- | --- |
| outbox | 12 | 32.7 | 2.7 |
| history | 1 | 18.7 | 18.7 |
| localCommits | 15 | 7.7 | 0.5 |
| poseRevisions | 6 | 6.6 | 1.1 |
| assets | 1 | 3.1 | 3.1 |
| userProjectState | 1 | 0.8 | 0.8 |
| projects | 1 | 0.4 | 0.4 |
| drafts | 0 | 0 | |

Total ≈ 70 KB for two states.

**Findings.**

1. The outbox is already **47% of all stored bytes** after two states.
2. Outbox records are **~5x fatter than the commits they shadow**: 2.7 KB each
   against 0.5 KB per `localCommits` record. The queue costs more than the
   history it mirrors, which is why its share only grows.
3. Ratio `outbox / localCommits` = 12/15 = 0.80 here, against 689/805 = 0.86 on
   the 33-state piece. The scout's "1 per edit" was the right shape but is not
   exactly 1:1; the measured ratio is stable at roughly 0.8 across both samples,
   so projection from it is sound.
4. Per state here: 7.5 commits and 6 outbox records. The 33-state piece ran 24
   commits and 21 outbox records per state, which is expected: commits track
   edits, not states, and that piece carried camera moves and tweaks per state.
5. `history` is a different growth shape worth watching separately: few records,
   each very large (18.7 KB for one here; 887 KB across four on the old piece,
   ~220 KB each). It is second only to the outbox by share and is not covered by
   the outbox disposition.

## Open question this log exists to answer

A scout asserted 1 `localCommits` record and 1 `outbox` record per edit, from
reading the code. With a clean baseline, that becomes measurable. If it holds,
the cost of a 33-state piece is reproducible and the outbox share is predictable.
