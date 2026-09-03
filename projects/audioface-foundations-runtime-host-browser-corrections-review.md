---
title: Audioface browser host boundary correction review
type: projects
tags: [audioface, foundations, browser, worker, boundary, review, verification]
summary: Independent delta review of 3221511 against efa6af6, closing the envelope boundary finding with a three realm probe, fresh headed and headless Chrome proof and artifact equivalence.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundation-program-host-spec, audioface-foundations-runtime-host-browser-corrections, audioface-foundations-runtime-host-browser-review, audioface-foundations-runtime-host-browser-build]
confidence: high
---

# Browser host boundary correction review

Target `3221511a59170b3fafaaa6924cf1a25f98a26b37`, direct parent `efa6af6f8283efe0dfd362b74c74c11bdf16d2ca`, checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser` on `probe/foundation-browser`. The checkout was at the exact target with zero changes before the review and after every command. Host spec `3f32506eb9bbbddc3a9500455d3fa177e23aef370cd3ff2dfbd0f7d8f8aa7574` and runtime probes spec `6615929b170d3681f0fc994985d9f5186316f87b6d0b7322fbcabe5e12f1555d` verified. Main README `f34eb76a9bd6818ccb3ae8243755c6e4598d93efccfe182d5d37bf550f254525` unchanged. The main checkout's output directory was not inspected. No source, spec or prior report edits, no commits, remote actions or additional agents. The prior complete review of `efa6af6` stands for unchanged behavior.

Verdict: clean. The low envelope boundary finding is closed. No new finding. Four observations, none blocking.

## Delta

One commit, `3221511`, two files, 142 insertions and 4 deletions. `adapters/web/src/program-client.ts` changes six lines in `request`. `adapters/web/test/program-client.test.mjs` is new.

## Correction, verified by reading

`ProgramClient.request` at `program-client.ts:103` now computes the next serial without committing it, builds one object typed `satisfies WorkerCall` at line 104, measures that object with the existing `programEnvelopeBytes` at line 105, checks caller capacity at line 106, commits the serial at line 108, registers the pending latch at line 115 and posts the same object through the existing `postWorkerControl` at line 117. A capacity refusal therefore precedes serial consumption and latch admission. Nothing else in the file changed. `worker.ts:78` still measures the received call with the same authority, so any call the client admits the worker admits, and the worker's terminal handling of an oversized ingress remains for calls that bypass the client. No cap changed. No measurement helper, protocol type or wrapper constructor was added.

## Failing before, passing after

Before, at `efa6af6`, my original `repro-three-realm.mjs` case 4 recorded a 65,535 byte bare action passing main, the wrapped call exceeding capacity in the worker, both the caller and an earlier open settling generation ended, and a main failure. The author's focused regression failed there with a missing expected exception.

After, at the exact target, the same original script throws the capacity error synchronously inside `ProgramClient.request` at its case 4 line, which is the corrected behavior and is preserved in `repro-three-realm-original-at-3221511.log`. The focused regression passes. My new probe `repro-envelope-boundary-review.mjs`, importing the unchanged prior harness, passes all four cases, exit 0:

- A. Real open with seed map shape at serial 3: wrapped 65,532 and 65,535 bytes admitted, 65,538 refused with the capacity error. The bare action of the refused call measures 65,439 bytes, which is the closed hole. The refusal posts nothing and leaves the snapshot unchanged. The posted objects have exactly the keys `kind, serial, action, args`, carry the caller's args reference, measure 65,535 and 65,532 through the authority, and serials post as 1 to 5 with no gap. Both near limit opens are refused by the preparer as already open, which proves worker ingress accepted them. An existing trigger for frame 4,096 applies with a voice, a following trigger applies at 768 with a voice, pending returns to zero, no main failure, no `program-failed`, worker not ended.
- B. Serial overhead is real. A filler that measures 65,535 at serial 9 is admitted as serial 9, the identical action is refused when the next serial would be 10, and one character less is admitted as serial 10 at 65,535. The refusal consumed no serial.
- C. With 768 callers pending, an oversized call is refused with the envelope error and a valid call with the caller capacity error, pending stays 768 and 768 calls were posted. After all settle, the next open is serial 769 and applies.
- D. Bypassing the client with a 65,538 byte call directly into the worker scope still ends the generation there with one `program-failed`, one main failure and a closed client, so ingress validation is unchanged.

## Browser, artifacts and carry forward

Fresh private headless and headed Chrome runs on the exact SHA, both exit 0, source clean before and after. Each: 22 cases, 88 channel comparisons with zero mismatches against the Node reference, lifecycle pass, native transfer refusal pass, credited transfer failure pass, null proof five of five, realtime pass with frames 1,408 to 25,216 across the 500 ms stall and 11 commands applied at their requested frames. Ten negative controls exit 1 with the intended error.

Artifact hashes are identical between my two runs and equal the author's manifest. Against my `efa6af6` review run, `null-test.html`, `program-worker.js` and `program-worklet.js` are byte identical and `index.html` and `program-test.html` differ. Both changed pages contain the corrected `request` body verbatim. The unchanged worker and worklet artifacts were still executed by the fresh runs, so prior direct transport and processor evidence carries forward on byte identity rather than on assumption.

Identity: for all 22 cases the pre sum Sound 1 hash equals my `efa6af6` run, the mixed channel 0 hash differs from that pre sum value and equals my `efa6af6` mixed value, and every channel matches the current Node reference.

## Author reports and evidence preservation

The build report was versioned to `_versions/audioface-foundations-runtime-host-browser-build.v1.md` before rewriting. The diff between v1 and current is the SHA, the fourth commit, the correction paragraph, the identity paragraph, two artifact hashes, the manifest path and the pending line. The identity wording in the build report, build digest and corrections digest now states that the 22 shared hashes are pre sum Sound 1 captures, that all 22 final mixed hashes differ from the old single runtime proof and that each matches the current Node reference. That matches the measurements above. The corrections digest is 291 words, distinguishes the source change from the two changed and three identical artifacts, and contains no em dash. The original build evidence directory has no file newer than 22:23 local, before the corrections brief. My review report, digest and evidence are unchanged.

## Observations, none blocking

- `program-client.test.mjs:65` restates the authority's serialized formula to label the refused size, because the authority throws above the cap. Test only. My probe needed the same device.
- The new test fakes and the `Port` fake in `game-audio.test.mjs:71` both record posted messages, with different dispatch models. Not equivalent code, but a shared test port would remove the second shape if a third appears.
- `{ kind, serial, ...action }` lets an untyped caller's own `kind` or `serial` key win the spread. Pre existing shape, excluded by the type, unchanged here.
- Browser runs recorded Node v24.20.0 from the login shell; probes and focused tests ran under v25.9.0, as before.

## Gates

| Gate | Result |
|---|---|
| `pnpm run typecheck` at target | exit 0 |
| Focused `program-client.test.mjs` | 1 pass, 0 fail |
| Original three realm probe at target | case 4 throws at the client, as corrected |
| New boundary probe, four cases | exit 0 |
| Headless proof | 22 cases, realtime pass, null 5/5, exit 0 |
| Headed proof | 22 cases, realtime pass, null 5/5, exit 0 |
| Negative controls, 10 | all exit 1 |
| Lead full gate log | 503 pass, 0 fail, lint, format, structure pass, exit 0 |
| Touched file sizes | 164 and 136 lines; author bounds probe 603 and 144 unchanged |

## Limits

One stall on one machine; no deadline or dropout claim. The bounds probe was not rerun; the touched files are far inside the limits. The three realm harness fakes the worker and node bridges; the direct port and all product code are real.

## Evidence

`/Users/alphab/.mdx/TMP/pstack/audioface-foundations/runtime-host-browser-corrections-review/`: `environment-before.txt`, `environment-after.txt`, `prior-review-evidence-hashes.txt`, `typecheck.log`, `focused-client.log`, `repro-three-realm-original-at-3221511.log`, `repro-envelope-boundary-review.mjs` and `.log`, `run-browser.sh` and `run-browser.log`, `browser-comparison.txt`, `headless-final/`, `headed-final/` and ten negative control directories with logs.
