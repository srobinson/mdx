# Scout: is `perf/history-delta` converging, or patching around a wrong shape?

Cold read of `1541c4b` then `4b71646` against `main` at `77b7795`.
Worktree `.claude/worktrees/history-delta`. No other seat's report was read.

**Verdict: converging but 5 structural risks remain.** The journal is the right
primitive and the append-only win is real and unarguable. What is wrong is not
the journal, it is that a second, smaller optimisation was bolted onto it
(omit the `ProjectManifest` when it repeats), and that optimisation is the
source of most of the machinery, all of the boundary questions in Q3, and the
only genuinely fragile code on the branch. It saves roughly two hundred bytes
per step.

Provenance, stated precisely because the branch moved under me. The brief named
`4b71646` as HEAD and that is what `git log` showed when I started. At 13:50
a builder landed `35208f4 test: type history reload provider props` into the
same worktree, so my gate runs at 13:54 and 13:58 measured `35208f4`, not
`4b71646`: `tsc -p tsconfig.app.json --noEmit` exits 0, `pnpm lint` exits 0,
`pnpm test` is 2597 passing in 185 files. The brief's typecheck failure was
therefore real at `4b71646` and is fixed at `35208f4`, not stale as I first
read it. `35208f4` touches only `tests/cubicellHistoryReloadBrowserDriver.ts`;
every source claim below reads identically on both commits.

Caution for whoever gates this: `pnpm check` is `oxfmt --write && oxlint --fix`
and mutates the tree. It is not a read-only gate, and it is not typecheck.
Typecheck is `tsc -b`, which no script runs outside `pnpm build`.

---

## 1. IDENTITY: one-off slip, or a conflation?

**A conflation, and it predates the branch.** The slip that broke live undo was
a symptom, not the disease.

`storageRecordTypes:StoredHistoryBytes.baseCommitId` and
`storageRecordReads:historyCommitMatches` both exist on `main` unchanged. On
`main` the spine carried `baseCommitId: head.id` unconditionally
(`storageRecordPreparation:prepareStorageRecords`), so the write side always
claimed the latest commit while the read side asked a different question:
"what is the last commit id on the row the document lives in", spelled
`rows.asset?.lastCommitId ?? rows.project.lastCommitId` in
`indexedDbProjectReads:loadIndexedDbProject`. Those two are different identities.
`main` already drops local history whenever a promote does not rewrite the active
asset row. It was invisible there because the aggregate was rewritten in full on
the next edit, so the loss self-healed within one keystroke.

The journal removed the self-healing. The same conflation now orphans a whole
journal instead of one rewritable blob. `4b71646` responds by teaching the write
side to predict the read side, in `promoteContract:historyBaseCommitId`:

```
assetKey === nullAssetKey ? commit.projectChanged
                          : commit.assets.some(({assetId}) => assetId === assetKey)
```

Judge those two arms separately, because they are not the same quality of code.

The **attached arm is sound by construction**. `commit.assets` is the same array
that `promoteContract:assetWrites` maps over to produce the rows carrying
`lastCommitId`. One source, two consumers. It cannot drift.

The **detached arm is sound by coincidence**. `promoteContract:committedProject`
sets `lastCommitId: commit.commitId` unconditionally, and
`indexedDbCommit:issuePromoteWrites` puts that row unconditionally on every
promote. So `project.lastCommitId` advances on *every* commit, while
`baseCommitId` advances only when `commit.projectChanged`. The two only agree
because of one clause living in a different bounded context entirely:

```
// src/state/projectStorageChangeSet.ts:checkpointStorageChanges
const projectChanged = roster.length > 0
  || before.project.title !== after.project.title
  || (draftChanged && afterActiveId === null);
```

That third disjunct is the entire load-bearing guarantee for detached mode.
Nothing in `src/persistence/` references it, asserts it, or knows it exists,
and `projectStorageChangeSet:authoredStorageChanges` has no equivalent clause.
Delete or narrow that disjunct while refactoring change-set derivation and
detached history dies silently on reload, with every test still green.

So: more bugs of this class are coming, but not because the fix was wrong.
They are coming because the invariant is a cross-context handshake that no
single place states. That is the thing to fix, and it is cheap to fix.

## 2. INVARIANT: state it, then count where it is enforced

> At every quiescent point, the history spine for `(projectId, userId, assetKey)`
> must carry the `lastCommitId` of the row that `assetKey` names: the active
> asset row when `assetKey` is an asset, the project row when it is
> `nullAssetKey`. The journal holds exactly the contiguous sequence
> `(cursor - documentHistoryLimit, cursor]`, and each step's `ops` transform the
> present at its own sequence into the present one step older.

**Re-derived in five places, asserted in none.**

1. `promoteContract:historyBaseCommitId` predicts which rows will advance.
2. `promoteContract:committedProject` and `promoteContract:normalizeAssetRevision`
   actually set the values being predicted.
3. `indexedDbProjectReads:loadIndexedDbProject` derives the head as
   `rows.asset?.lastCommitId ?? rows.project.lastCommitId`.
4. `indexedDbProjectReads:loadIndexedDbProjectHydrationBytes` derives it again,
   inline, with the same expression copied.
5. `memoryProjectStorage:loadProjectRecords` derives it a fifth time as
   `activeAssetId ? assets.get(...)?.lastCommitId : project.lastCommitId`.

Note that 5 is **not equivalent to 3 and 4**. When the active asset row is
missing, IndexedDB falls back to the project's `lastCommitId` and can match;
memory yields `undefined` and can never match. Two ports of one contract already
disagree on the branch's central invariant, and
`tests/projectStorageContract.ts` does not catch it because no contract case
constructs an active asset id with no asset row.

The prune anchor is re-derived too, by two different expressions in two files
that must stay numerically equal:
`promoteContract:historyPruneAnchorSequence` computes `(prior.cursor ?? 0) + 2 -
documentHistoryLimit`, while `promoteContract:historyWrites` passes
`pruneThrough + 1` where `pruneThrough = head - documentHistoryLimit` and
`head = prior.cursor + 1`. Equal today. If either drifts,
`retainedHistoryAnchor` returns `null` on the `stored.seq !== retainedSeq`
guard and silently stops anchoring, with no test failing, because the fallback
produces a plausible manifest anyway.

The minimum repair is one exported function, in `storageRecordReads` next to
`historyCommitMatches`, that takes the stored project row and the stored active
asset row and returns the committed head id. Call it from all three read sites
and from `historyBaseCommitId` on the write side, so prediction and observation
share one expression. That is a single small function and five call-site edits.

## 3. HYDRATION: is walking backwards sound at the boundaries?

The telescoping itself is correct and I verified the chain algebra. Each step's
`ops` is `createHistoryDiff(present_k, present_{k-1})` per
`localHistoryRecordCodec:encodeLocalHistoryStep`, and
`localHistoryRecordCodec:hydrateSteps` walks newest to oldest seeding
`newer = present.workbench`, so the composition telescopes exactly. Boundary by
boundary:

**After a prune: sound.** `promoteContract:historyWrites` deletes only
`seq > cursor || seq <= pruneThrough`, trimming both ends and never the middle.
Contiguity holds.

**After a checkpoint: sound in ordering, unsound in trust.** I chased the
obvious hazard, undo followed immediately by an edit, and it is **not**
reachable: `documentActions:historyCheckpoint` always returns `durable: true`
when history moves, and `projectDurability` drains `units` as a strict FIFO, so
the cursor-retreat promote always lands before the next authored promote.
Credit where due. The real hazard is elsewhere. The retreat branch computes

```
cursor = max(0, min(prior.head, prior.cursor + projected.cursor - storedPastCount))
```

where `projected.cursor` is the *runtime* `history.past.length`. But runtime
`past.length` is itself the output of a lossy hydration. Any read failure that
makes `projectRecordHydration:decodeHistory` return `createDocumentHistory()`
produces `past.length === 0`, the next checkpoint drives `cursor` to `0`, and
the next authored commit sets `cursor = 1` and deletes every step above it.
Permanent. Worked example with `prior.cursor = 50`: checkpoint yields
`50 + 0 - 50 = 0`, then the next edit's `deletes` filter removes seq 2 through 50.

This composes with Q1 into the actual severity of the bug that shipped. The
`baseCommitId` mismatch made hydration return empty history; one autosave later
the journal would have been destroyed rather than merely hidden. The live probe
caught the visible half. The destructive half is still unguarded.

**After undo-then-edit dropping a branch: sound**, given the FIFO above.
`tests/projectStorage.test.ts` covers it directly.

**On a re-anchored oldest step: sound, and pointless.**
`promoteContract:retainedHistoryAnchor` stamps
`decodeProjectRecord(commit.project.manifestBytes)`, which is the manifest of
the commit doing the pruning, onto a historical step. That is not the manifest
that step ever had. Without the anchor,
`localHistoryRecordCodec:hydrateSteps` falls back to `present.project` through
`step.project ?? priorProject ?? present.project`. So the anchor substitutes
"manifest as of prune time" for "manifest as of load time". Both are wrong
relative to the step's real history, and `reconcileProjectAssets` corrects the
roster afterwards either way, leaving only `title` and `revision` differing.
The mechanism buys nothing and costs an extra sequential IndexedDB read phase
inside every authored commit's write transaction
(`indexedDbCommit:promotePreparedCommit`).

**The boundary nobody is checking: contiguity.**
`projectRecordHydration:decodeHistory` dedupes, sorts, filters `seq > cursor`
and slices the last 100, but never asserts the surviving sequences are
contiguous, and `hydrateSteps` `continue`s past a rejected step **without**
advancing `newer`. Under `main`'s design that was harmless, because
`encodePersistedHistory` re-encoded the whole chain in one pass from a live
array and a gap was structurally impossible; a skipped step just meant one lost
entry. Under a journal assembled from independently stored rows, a gap means
every older step is applied to the wrong base. RFC6902 `replace` on a path that
still exists succeeds, so this corrupts silently rather than failing.
**The reject-and-continue semantics were inherited from a design where steps
were self-contained and are wrong now.** They should truncate the chain at the
first rejection, not skip it.

`tests/projectStorage.test.ts:"rejects one corrupted persisted step without
restoring redo"` corrupts the newer of two steps and then asserts
`past: expect.any(Array)`. That assertion is vacuous about exactly the value
that is now wrong. The test certifies the smell.

## 4. SIMPLER: yes, and it is a deletion, not a rewrite

Keep the journal. Delete the manifest-omission optimisation.

`ProjectManifest` (`src/domain/project.ts`) is `{assets: [{id, kind, revision}],
id, revision, title}`. For a real project that is a few hundred bytes. It was
never the 221.88 KB problem; the problem was rewriting ~100 full `Workbench`
copies per edit, and the append-only journal alone solves that completely. Worse,
the optimisation barely fires: `encodeLocalHistoryStep` omits `project` only
when `jsonValuesEqual(project, priorProject)`, and consecutive entries carry
different `assets[].revision` after almost every authored commit, so the field
is written anyway most of the time.

Writing `project` on every step deletes, with no behavioural loss:

- `promoteContract:retainedHistoryAnchor` and
  `promoteContract:historyPruneAnchorSequence`
- the `historyStepAnchor` field threaded through `PromoteInput`, the extra
  `anchorSeq` read phase in `indexedDbCommit:promotePreparedCommit`, and its
  mirror in `memoryProjectStorage:promoteCommit`
- the `priorProject` inheritance walk and the `projects` prepass in
  `localHistoryRecordCodec:hydrateSteps`
- the optional-`project` arm of `localHistoryRecordCodec:decodeLocalHistoryStep`
- one sequential IndexedDB round-trip from the hot authored-commit write path

Each step becomes self-contained with respect to the project, which is also the
precondition that makes the Q3 anchor question disappear entirely.

**Cost to switch now is materially lower than finishing.** It is a deletion of
roughly 60 lines plus the two ports' plumbing, it removes the two hardest
boundary cases from the design rather than testing them, and it does not touch
the append-only journal, the spine, the cursor, or the wire version already
bumped to 9 in `indexedDbSchema`. Owner directives say wire bumps are free and
there is no compatibility case, so there is nothing to stage.

What I would **not** change: the journal, `{head, cursor}`, undo-only
persistence, the per-`assetKey` scoping, and `tests/cubicellHistoryReloadBrowserDriver.ts`.
That driver mounts the real editor and clicks a real button. It is the right
gate and it is the reason this slice is honest rather than merely green.

## 5. VERDICT

`converging but 5 structural risks remain`

| # | Risk | Where | Severity |
|---|---|---|---|
| 1 | Detached-mode `baseCommitId` correctness depends on an unstated clause in another bounded context | `projectStorageChangeSet:checkpointStorageChanges` third disjunct vs `promoteContract:historyBaseCommitId` | silent history loss on reload if that clause is ever narrowed |
| 2 | `writeKind: "install"` advances `project.lastCommitId` but skips the spine put | `indexedDbCommit:issuePromoteWrites` | latent only; `installCommitted` has no product caller in `src` today |
| 3 | Cursor retreat trusts runtime `past.length`, so a transient read failure permanently deletes the journal | `promoteContract:historyWrites` no-step branch | destructive, unguarded, and would have compounded the bug that just shipped |
| 4 | Chain contiguity never asserted; reject-and-continue inherited from the self-contained-step design | `projectRecordHydration:decodeHistory`, `localHistoryRecordCodec:hydrateSteps` | silent workbench corruption, and the guard test asserts `expect.any(Array)` |
| 5 | Committed-head id and prune anchor seq each derived in multiple places, two ports already disagree | five sites listed in Q2 | the mechanism that produced the shipped bug, still in place |

Risks 1, 2 and 5 collapse into one small function. Risk 4 is a `continue` that
should be a `break`, plus a real assertion in the test that already exists.
Risk 3 wants the retreat branch to bound `cursor` by what the journal actually
holds rather than by what hydration managed to rebuild. Q4's deletion removes
the remaining machinery. None of that is a rewrite.

The owner's instinct that wheels are spinning is half right. The wheels are
spinning on the manifest-omission optimisation, which is where the anchor, the
inheritance walk, the extra read phase and both hard boundary cases come from,
and which is worth about two hundred bytes a step. The journal itself is the
right shape. Delete the optimisation, name the invariant once, and finish.
