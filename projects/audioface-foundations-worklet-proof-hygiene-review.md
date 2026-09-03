---
title: Audioface foundations worklet proof hygiene review
type: projects
tags: [audioface, foundations, testing, worklet, hygiene, review, verification]
summary: Independent verification of the four file test and verifier delta at 30b15bc on the frozen browser worktree; shared ramp helpers are the one authority with unchanged mathematics, the verifier's clean source and artifact gates behave as claimed under five probe scenarios, and fresh headed and headless proofs keep all 22 sample hashes identical to the reviewed base.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-worklet-proof-hygiene, audioface-foundations-program-worklet-review, audioface-foundations-program-runtime-corrections-review]
confidence: high
---

# Audioface foundations worklet proof hygiene review

Checkout `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/browser`, branch `probe/foundation-browser`, HEAD `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21`, sole parent `ea487fbb031ec467c24d06ea60008387fc9cb7c7`. Four files, +84/−43, all under `scripts/` and `test/foundations/`. Tree pristine before and after, 0 tracked or untracked changes. Evidence: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-proof-hygiene-review/`. Author report and evidence were read and left untouched. Nothing inside any checkout was written except the probe's own sentinel and the ignored build output, both removed or rebuilt before closeout.

## Verdict

**Review clean.** No finding. Two observations, neither blocking.

| Requirement | State | Evidence |
|---|---|---|
| Command, cutoff and closed form shared in `program-support.mjs`; duplicates removed; mathematics unchanged | Met | Diff, `wc.txt`, focused tests |
| Verifier rejects tracked and untracked dirt at preflight and closeout, HEAD change, artifact change; keeps diagnostics; uses the existing build | Met, HEAD change untested | `probe-chain.log`, `final-*/result.json` |
| Hash checks cover the executed page | Met | Page inspection below |
| Snapshot versus lock limits explicit | Met | Author report, restated below |
| Author probe rerun safely; clean pass, preflight fails, closeout fails, artifact fail, rebuild pass | Met | `probe-chain.log`, `headless/` |
| Fresh headed and headless proof; 22 hashes equal reviewed base; three negatives exit 1 | Met | `comparison.json`, `negative-*/result.json` |

## Delta

**Shared helpers.** `program-support.mjs` gains `command`, `cutoff` and `cutoffAt`. `cutoff` delegates to `command` with placement `a.biquad`, key `FLT-10` and a linear ramp when frames are given. `cutoffAt` is the closed form: 2000 before 300, 2000 plus 400 times the clamped 128 frame fraction from 300, 2400 minus 300 times the clamped 96 frame fraction from 480. Both expressions are byte level identical to the two deleted copies in `program-runtime.test.mjs` and `program-worklet-support.mjs`. The old local `edit` built the same ramp object, so the migrated call sites `cutoff(2400, 128)` and `cutoff(2100, 96)` are equivalent. `cutoffAt` is pure arithmetic and never touches the runtime's ramp evaluator, so the reference stays independent of the code it checks. The ten oracle cases still use `renderOracle`. No fixture, oracle, production or contract file changed.

**Verifier.** `sourceState` runs `git rev-parse HEAD` and `git status --porcelain=v1 --untracked-files=all`; `assertSource` requires an empty status and the starting SHA. The state is taken at startup, after the build and before launch, and after close. The build is the repository's own `pnpm --filter @audioface/app-web build`, logged to `build.log` in the caller's output directory; the three page hashes are taken from the fresh build and compared again after close. A preflight failure happens before the build and before any browser command, and `launched` guards the close so no session is opened. Every failure still writes `result.json` and `commands.json`; the dirty status text is preserved in `dirty`, `beforeBrowser` and `finalSource`, and `sourceError` is recorded separately from `error`. Ignored paths, including `apps/web/dist/`, are exempt from the dirt check by `.gitignore`, which is what the build needs.

**Hygiene.** Modified files are 217, 484, 67 and 252 lines. No new module, no second build authority, no second reference. Verifier structure, environment isolation and command logging are unchanged from the parent.

## Executed page coverage

The rebuilt `dist/program-test.html` contains one `<script>` and zero `src` attributes; the worklet module is loaded from a data URL embedded in that page, and there is no `fetch`. The one external reference is a Google Fonts stylesheet, which carries no executable code and does not affect the samples. The verifier hashes exactly the file it opens through `file://`, so the page hash covers all executed code. The Node side references (`renderProof`, `proofReference`, fixtures, oracle) live in tracked source and are covered by the status check. The residual gap is the window between the post build hash and the browser open, closed only by the after close rehash. A change made and reverted inside that window, an ignored dependency change, or a toolchain change is not detected. The author states these limits; I confirm them.

## Probe scenarios

The author's `probe.mjs` was copied to the review directory with one edit: its hard coded root now points at the frozen browser worktree instead of integrated. Outputs land beside the copy, so the author's evidence is untouched (directory mtime 13:38:29, before this review). The probe wraps my earlier `fake-agent-browser.cjs` stand-in and my control capture, so the browser is fake and the verifier logic is real.

| Scenario | Verifier exit | Where it stopped | Recorded |
|---|---|---|---|
| clean | 0, 22 cases | completed | build, artifacts, three clean states |
| untracked sentinel | 1 | preflight, no build, no launch | `dirty: "?? .worklet-hygiene-owned-sentinel"` |
| staged sentinel | 1 | preflight, no build, no launch | `dirty: "A  .worklet-hygiene-owned-sentinel"` |
| sentinel written at close | 1 | closeout | start and pre launch clean, `finalSource` dirty |
| page appended at close | 1 | closeout | `finalArtifacts.program-test.html` `cd0ab634…` versus `f75cb67f…` |

After every scenario the checkout reported 0 changes and no sentinel. The page was left mutated after the last scenario by design. The next real headless verifier rebuilt it, hashed `f75cb67f…` again and passed, which is the rebuild pass the brief asks for. A HEAD change during proof was not exercised because it needs a commit or ref move, which this brief forbids; the check is a string comparison of the two SHAs and is read as correct.

## Browser proof at target

Run from the browser worktree with outputs outside the checkout.

| Run | Exit | Result |
|---|---|---|
| headless | 0 | 22 cases, 0 mismatches against Node and reference, 22 of 22 sample hashes equal to the ea487fb reviewed base, 375 callbacks, quantum 128, null page pass on 5 rows |
| headed | 0 | same, screenshot shows all 22 rows PASS |
| sample fault | 1 | one mismatch at frame 364, maximum difference 0.7578050792217255 |
| processor error fault | 1 | `48000-nested: processorerror` |
| timeout fault | 1 | `48000-nested: timeout` |

Every run started and ended with SHA `30b15bc` and an empty status, and before and after artifact hashes were equal, including the negative runs. Built pages: `index.html` `8db6ed63…` and `null-test.html` `b484bf05…` are byte identical to the reviewed base, so the shipping and null compatibility evidence carries forward; `program-test.html` is `f75cb67f…`, matching the author. `commands.json` shows 11 agent-browser calls per passing run, headed runs carrying `--headed`, each ending in a successful `close`. No verifier session remained; the two sessions listed afterwards belong to the user's terminal.

## Gates

| Command | Result | Log |
|---|---|---|
| `node --test` on `program-runtime.test.mjs` and `program-worklet.test.mjs` | 45 pass, 0 fail, 0 skip | `focused-30b15bc.tap` |
| `node --test` on all `test/foundations` and `packages/engine` test files | 180 pass, 0 fail, 0 skip | `foundations-engine-30b15bc.tap` |
| `pnpm run typecheck` | exit 0 | `typecheck-30b15bc.log` |
| Build | exit 0 inside every verifier run | `*/build.log` |
| Lead `pnpm run check` at the same SHA on integrated | 394 pass, 0 fail, 0 skip, lint, format, structure pass | `worklet-proof-hygiene-lead-check-30b15bc.log` |

## Observations (not findings)

- `program-runtime.test.mjs` still builds `FLT-10` commands longhand at five sites (lines 241, 291, 295, 314 and 331) that `cutoff` now expresses. These lines are unchanged from the parent and outside the two consumers the brief named. Line 246 uses a differently anchored ramp segment and is not a copy of `cutoffAt`. A later hygiene pass can fold the five sites in.
- If a caller passes an output directory inside the checkout that is not ignored, the empty directory passes preflight because Git does not report empty directories, and the run fails at the pre launch check once `build.log` exists. The author documents this behaviour; it is acceptable for a prototype verifier.

## Clean tree

Browser `30b15bc`, integrated `30b15bc`, composition `41699f4`, runtime `9204eaa`, main `10ba9fc`, all 0 changes and 0 untracked at 06:49 UTC. The only checkout writes were the probe sentinel, removed by the probe, and the ignored `apps/web/dist/` pages, rebuilt by the verifier.

## Limitations

1. Node v25.9.0 here versus the author's v24.20.0; both pass, neither is pinned.
2. The HEAD change refusal is verified by reading, not by execution.
3. Probe scenarios use a fake browser; real browser evidence is the separate five verifier runs.
4. Load average 9 to 11, uncontrolled; no timing claims.
5. Browser proof is offline sample equality only, as before.
6. The lead full gate is the lead's artifact, run on integrated at the same SHA.
