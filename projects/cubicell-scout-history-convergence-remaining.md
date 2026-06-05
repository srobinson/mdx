# Cubicell history-delta convergence: remaining work

Scout: completion accounting, read-only.
Branch: `perf/history-delta` at worktree `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/history-delta`.
SHAs: `main` `77b7795` ← `1541c4b` (slice) ← `4b71646` (fix) ← `35208f4` (type driver; on origin at scout time).
Four prior seats reviewed `1541c4b` only. This report asks what is left on the tip that claims to close their findings.

Owner constraints carried forward: redo does not survive reload (intended). Slice replaces aggregate history rewrite with `historySteps` journal + `history` spine `{head,cursor}`, manifest only when it differs, undo ops only.

---

## 1. REMAINING WORK (ranked by risk)

1. **High — prune anchor project seed may be wrong after `4b71646`.** `src/persistence/promoteContract.ts:retainedHistoryAnchor` no longer walks earlier steps to recover the project omitted under `encodeLocalHistoryStep` equality; it injects `commit.project.manifestBytes` (present project at promote). Wrong when ProjectManifest evolved across the pruned window and the retained step omitted `project` because it matched its *prior step*, not present. No test asserts project continuity across prune. Only depth sequences are checked in `tests/projectStorage.test.ts` prune case.

2. **High — gates and app path unproven on the fix commits.** Unit, browser, budget, and real `pnpm dev` / `pnpm preview` integrator paths were green on `1541c4b` per prior seats; none re-certified on `4b71646` / `35208f4` in the record this scout has. New coverage exists but is unrun from this seat: `tests/cubicellStore.browser.test.ts:historyReloadTests`, `tests/projectStorageRecordBrowserDriver.ts:runHistoryPromoteReadProfile`, restored `tests/projectStorageContract.ts:assertHistory`.

3. **High — reload undo fix is synthetic-only so far.** Integrator failure on `1541c4b` was real-app (`history.baseCommitId` stuck on checkpoint while `asset.lastCommitId` advanced → `src/persistence/storageRecordReads.ts:historyCommitMatches` dropped the spine). `4b71646` addresses it via `src/persistence/promoteContract.ts:historyBaseCommitId`, and `tests/cubicellHistoryReloadBrowserDriver.ts:runMountedEditorHistoryReload` proxies the path with a mounted provider + synthetic undo button. Full studio chrome (dev/preview, real History UI, multi-edit session) not re-driven.

4. **Medium — `historyBaseCommitId` semantics unreviewed.** New production rule: advance spine `baseCommitId` only when the promote advances the committed head for that history `assetKey` (`commit.projectChanged` for `nullAssetKey`, else membership in `commit.assets`). Preparation still stamps `head.id` in `src/persistence/storageRecordPreparation.ts` and promote overwrites. Edge cases without dedicated asserts: multi-asset spines, checkpoint-only promotes, first history write with no prior spine, install/rebase paths.

5. **Medium — two-phase IDB promote unreviewed.** `src/persistence/indexedDbCommit.ts:promotePreparedCommit` switched `historySteps` from `getAll` to `getAllKeys`, then optional second `get` for the prune anchor before `completePromoteReads`. Changes transaction shape, when `reads-complete` fires relative to the second read, and abort timing on `historyPruneAnchorSequence` decode failure (now aborts before plan; previously could surface `StalePromoteError` via plan). Failure driver still keys off `reads-complete` (`tests/projectStorageFailureBrowserDriver.ts`).

6. **Medium — type gate.** `4b71646` fails `tsc -b` on `tests/cubicellHistoryReloadBrowserDriver.ts` (`TS2352` cast missing `children` on `CubicellStoreProvider` props). `35208f4` fixes it (`satisfies ComponentProps` with `children` in props). Must stay on the branch; origin already includes it at scout time, but any cut back to `4b71646` is not mergeable.

7. **Medium — contract guard still not prune-correct.** `tests/projectStorageContract.ts:assertHistory` restores step/cursor/head checks but requires sequences `1..cursor` and `head === cursor`. After prune, journal is e.g. `2..101` with `cursor === 101`. Short port-contract runs never hit prune, so the guard is false-green for the depth invariant the slice exists to enforce. Prior seat Major is only half-closed.

8. **Low — test literals still hardcode `100`.** Production binds `documentHistoryLimit` in `promoteContract.ts` and `projectRecordHydration.ts:decodeHistory`. `tests/projectStorage.test.ts` prune title and expected length still hardcode `100`. Prior seat Minor not fully closed in tests.

9. **Low — measurement and controlled-red not re-run on tip.** Bytes-per-edit (26,597 → 858 on 100-step fixture) and three controlled-red proofs were on `1541c4b`. Unlikely regressed by the fix (mostly promote/read path + tests), but not re-measured.

10. **Low — memory promote still materializes full step values.** `src/persistence/memoryProjectStorage.ts:applyPromote` still filters all `historySteps` values then picks the anchor; only IDB uses keys. Acceptable if memory is test/dev, but the ports are no longer symmetric.

11. **Low — file size pressure.** `src/persistence/promoteContract.ts` ~493 LOC, `indexedDbCommit.ts` ~406, `projectRecordHydration.ts` ~565. Under the 700-line hard limit; no forced split. Watch if more promote logic lands.

12. **Process — `35208f4` and `4b71646` production surface never got the four-lens pass.** Reuse, measurement, consumer/guard, and integrator all closed on `1541c4b`. Everything in the fix commit’s production files is net-new review debt.

---

## 2. BLIND SPOTS (lenses did not cover)

| Area | Why uncovered |
|------|----------------|
| `retainedHistoryAnchor` project provenance after keys-only promote | Reuse seat saw getAll cost; fix seat removed values without re-proving project seed. Measurement used codec fixture, not prune-at-limit with evolving ProjectManifest. |
| `historyBaseCommitId` / reload coupling | Integrator found the bug on `1541c4b`; fix landed after. No seat re-read promote vs `historyCommitMatches` together. |
| Two-phase IDB transaction + event phases | Reviews read static promote plan; nobody stepped the new `afterIndexedDbRequests` nesting under fault injection beyond existing stale tests. |
| Multi-asset / asset-switch history | Reload driver seeds one structure fixture and never switches `activeAssetId`. Spines are per `assetKey`. |
| Pruned journal + hydrate ownership | Hydration seats/codecs tested short chains and corrupt step; not “101 edits, project roster changed, undo after reload past prune boundary”. |
| Full studio surface | Integrator drove two product states on `1541c4b` and failed; no seat re-ran product after fix. Browser test uses `HistoryUndoButton` + `EditorStudioTestRoot`, not the shipped history control path alone. |
| Recovery / quarantine with journal | `indexedDbRecovery` deletes history + historySteps by user range; save-recovery drivers touch spine/steps, but not combined with the new baseCommitId rule. |
| Budget gate | `budgets/initial-delivery.json` bumped on `1541c4b`; `check:budget` not cited as re-run on tip. |
| Concurrent clients / second tab promote | Port contract has multi-client load cases; none assert history journal + baseCommitId under concurrent promotes. |
| Schema v8→v9 wipe UX | Schema bump is full store reset by design (`createIndexedDbProjectSchema`); no product note or user-facing implication reviewed. |
| Redo-drop product expectation | Owner says intentional; no UI copy or test name makes the product contract obvious outside codec tests. |

---

## 3. FIX-INTRODUCED RISK (`4b71646` production)

**Yes — three production semantic/shape changes, not test-only.**

1. **`src/persistence/promoteContract.ts:historyBaseCommitId`** — spine `baseCommitId` no longer always follows `PreparedStorageCommit` / preparation `head.id`. Stops undo/checkpoint promotes from desyncing `historyCommitMatches`. Necessary for the integrator bug. Risk: any caller that assumed spine base always equals latest commit id is wrong; intended callers compare to asset/project `lastCommitId`.

2. **`src/persistence/promoteContract.ts:retainedHistoryAnchor` + `historyPruneAnchorSequence`** — keys-only promote reads one anchor row; project backfill uses **present** project, not accumulated journal project. Can mis-label historical steps after depth prune when manifests changed. This is the main fix-introduced correctness risk relative to what `1541c4b` certified.

3. **`src/persistence/indexedDbCommit.ts:promotePreparedCommit` / `completePromoteReads` / `historyStepKeys`** — promote read plan and phase emission order changed; second round-trip for anchor; prune-path decode errors abort without `StalePromoteError` specialization. Memory port updated in parallel (`memoryProjectStorage.ts:applyPromote`) so plan input shape matches.

Also production: `projectRecordHydration.ts:decodeHistory` and promote prune bound now use `documentHistoryLimit` (closes hardcoded-100 in prod). Net good; not a regression risk.

Tests-only bulk of the +414/−79 is drivers/contract/browser wiring; production risk is concentrated in the three items above.

---

## 4. MERGE CONDITIONS (shortest complete list)

All must be true:

1. **Tip includes `35208f4` (or equivalent)** so `tsc -b` is green on `tests/cubicellHistoryReloadBrowserDriver.ts`.
2. **`pnpm test` green** on tip (unit project).
3. **`pnpm test:browser` green** on tip, including `historyReloadTests` and `runHistoryPromoteReadProfile` (`keyReads: 1, valueReads: 0`).
4. **`pnpm build` / `tsc -b` green** (and budget gate if still required for this repo’s merge bar: `pnpm check:budget`).
5. **Reload undo proven on tip:** either accept `runMountedEditorHistoryReload` expectations as the gate, or re-run real app (edit → save → full reload → undo mutates document). At least one must be green on tip; product re-run preferred once given prior real-app fail.
6. **Review sign-off on `4b71646` production trio:** `historyBaseCommitId`, `retainedHistoryAnchor`/`historyPruneAnchorSequence`, two-phase `indexedDbCommit` promote. Especially a decision on (7).
7. **Prune anchor project correctness closed by one of:**
   - proof that omitted `project` on a retained step always equals present project at prune time, or
   - fix that restores journal-accurate project for the retained seq without reintroducing full `getAll` (e.g. require project on steps that would become anchors, or read a single known seed step that always carries project), plus a test that fails if present project is wrongly stamped after roster change across the prune window.
8. **Contract depth honesty:** either extend `assertHistory` to allow a contiguous window ending at cursor (not only `1..cursor`), or keep prune assertions only in dedicated tests and document that the port contract does not enforce depth. Do not merge believing `assertHistory` guards prune.
9. **No open integrator regression** on the original failure mode: after reload, spine present when `baseCommitId` matches committed head; undo not a no-op.

Non-conditions (explicitly out of merge bar per owner): redo surviving reload; aggregate history record; migration of pre-v9 IDB data.

---

## 5. HONEST ESTIMATE

**Close, short tail — if the anchor project issue is none or a small fix.**

The slice shape is in place: journal + spine, measurement win on `1541c4b`, promote no longer `getAll`s the journal, reload baseCommitId fix and browser proxy exist, type hole patched on `35208f4`. What remains is **verification of the fix commit** and **one possible correctness bug in prune project seeding**, not redesign of the history model.

Not “done”: treating `4b71646` as a pure test patch would be wrong; production promote/hydration semantics moved and only one lens (integrator failure) was the trigger. Remaining calendar risk is mostly “run the gates + one careful promote review,” unless `retainedHistoryAnchor` needs a design touch, in which case still days-scale not weeks.

**Do not merge on reassurance from the four `1541c4b` verdicts alone.**

---

## Appendix: claim map (prior seats → tip)

| Prior finding on `1541c4b` | Tip status |
|----------------------------|------------|
| Major: promote `getAll` historySteps | Claimed fixed: `getAllKeys` + optional anchor `get`; browser profile test added; **not re-run here** |
| Major: `assertLoaded` stripped historySteps/cursor/head | Partial: `assertHistory` restored for short journals; **still wrong for pruned windows** |
| Minor: hardcoded `100` | Prod closed via `documentHistoryLimit`; **tests still hardcode** |
| Integrator: reload undo no-op | Claimed fixed via `historyBaseCommitId` + browser reload test; **product path not re-driven; unit/browser gates not re-run here** |
| Typecheck on new driver | **Fails on `4b71646`; fixed on `35208f4`** |

