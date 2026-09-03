---
title: Audioface foundation worklet proof hygiene
type: projects
tags: [audioface, foundations, testing, worklet, hygiene]
summary: Shared ramp references and clean source enforcement verified at 30b15bc.
status: active
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
---

# Worklet proof hygiene

Delivered local commit `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21`, parent `ea487fbb031ec467c24d06ea60008387fc9cb7c7`, on `probe/foundation-integrated`. Integrated was clean before editing and at closeout. Four test and verification files changed, with 84 insertions and 43 deletions. Production code, fixtures, oracle, specifications, dependencies, and other checkouts are unchanged. No additional agents, remote actions, or independent approval of this correction.

Worktree: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`.

Evidence directory: `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-proof-hygiene/`. Paths below are relative to that directory unless stated otherwise.

## Shared authority

Search found the existing general command constructor in `program-runtime.test.mjs`, a cutoff constructor in `program-worklet-support.mjs`, and matching closed-form equations in both consumers. The existing `test/foundations/program-support.mjs` now owns `command`, `cutoff`, and `cutoffAt`. The cutoff constructor reuses the general constructor. Both consumers import the same cutoff and reference helpers. The old definitions and equations were deleted.

The reference equation preserves its original inputs and arithmetic: 2000 before frame 300, 2000 plus 400 times the clamped 128-frame fraction, then 2400 minus 300 times the clamped 96-frame fraction beginning at frame 480. Scheduled runtime ramp commands remain separately specified. The helper never calls the runtime's automation evaluator. The ten oracle cases still use the unchanged hand-wired DSP oracle. Ramp and capacity references continue to share production DSP with the observed runtime.

TypeScript and hygiene guidance directed reuse of the existing support module, deletion of the copies, and source validation at the CLI boundary. No new support layer was introduced.

## Clean source and artifact enforcement

`scripts/verify-program-worklet.mjs` now records and enforces source state at startup, immediately before browser launch, and after browser close. Each snapshot uses `git status --porcelain=v1 --untracked-files=all`. Startup must be clean. Subsequent snapshots must remain clean and retain the initial HEAD.

The verifier invokes the existing `pnpm --filter @audioface/app-web build` command before hashing or loading pages. Build output goes to the caller's artifact directory as `build.log`. This overwrites stale ignored build output using the existing build implementation. All three page hashes are recomputed after browser close and compared with the freshly built hashes. No second build system or freshness claim based on timestamps was added.

Failures preserve `result.json` and `commands.json`, plus any captures already obtained. Dirty startup fails before build or browser launch. A closeout failure clears `passed`, records `sourceError`, and sets exit 1. Existing browser errors retain their original diagnostics. The verifier never deletes source files.

The CLI remains `node scripts/verify-program-worklet.mjs headless|headed OUTPUT [sample|processor-error|timeout]`. Every run here placed OUTPUT outside the checkout. Ignored generated pages remain allowed. A nonignored output file inside the checkout would itself make the source check fail.

## Checker probes

`probe.mjs` wraps Fable's unchanged `program-worklet-review/probes/fake-agent-browser.cjs` and reuses its real control capture. These probes test verifier behavior through a stand-in browser. Separate real browser evidence follows.

| Probe | Verifier exit | Evidence |
| --- | --- | --- |
| Baseline with untracked sentinel | 0, incorrectly passed | `baseline-untracked/result.json` |
| Final clean source | 0, 22 cases | `final-clean/result.json` |
| Final untracked sentinel | 1, preflight refusal | `final-untracked/result.json` |
| Final staged sentinel | 1, preflight refusal | `final-tracked/result.json` |
| Sentinel created by browser close | 1, closeout refusal | `final-close-dirty/result.json` |
| Page modified by browser close | 1, artifact mismatch | `final-close-artifact/result.json` |

Reproduce with `node /Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-proof-hygiene/probe.mjs final SCENARIO`, where SCENARIO is `clean`, `untracked`, `tracked`, `close-dirty`, or `close-artifact`. Each driver run asserts the expected verifier exit. The baseline command was run before source edits.

The driver refuses an existing `.worklet-hygiene-owned-sentinel`. It removes only its own sentinel, including its temporary index entry for the staged case. No user files were removed. The deliberate ignored page mutation was repaired by the next real verifier's mandatory build. That run recovered the expected artifact hash and passed. Final sentinel absence is recorded in `comparison.json`.

## Exact commit gates and browser proof

All final gates ran at `30b15bcf8ff3f42b5afd25c296cc0e8afd633e21` with no later source edits.

| Command | Result | Evidence |
| --- | --- | --- |
| `node --test test/foundations/program-runtime.test.mjs test/foundations/program-worklet.test.mjs` | 45 passed, 0 failed, 0 skipped | `focused-final.log` |
| `pnpm run check` | Exit 0, 394 passed, 0 failed, 0 skipped; typecheck, lint, formatting and structure passed | `check-clean-final.log` |
| `pnpm --filter @audioface/app-web build` | Exit 0 | `build-final.log`, each browser run's `build.log` |
| Existing `program-runtime-proof.mjs` | Exit 0; sizing and legacy proof retained | `runtime-size-recheck.json` |
| Verifier, headless | Exit 0, 22 cases | `headless/`, `headless.log` |
| Verifier, headed | Exit 0, 22 cases | `headed/`, `headed.log` |
| Verifier with `sample` | Exit 1; one mismatch at frame 364, maximum difference 0.7578050792217255 | `negative-sample/`, corresponding `.log` |
| Verifier with `processor-error` | Exit 1, explicit processorerror | `negative-processor-error/`, corresponding `.log` |
| Verifier with `timeout` | Exit 1, explicit timeout | `negative-timeout/`, corresponding `.log` |

Real browser invocations used `node scripts/verify-program-worklet.mjs MODE /Users/alphab/.mdx/TMP/pstack/audioface-foundations/worklet-proof-hygiene/MODE`, from integrated. Negative invocations used headless mode, `negative-FAULT` as the output directory, and FAULT as the last argument. Each `commands.json` retains the exact `agent-browser --session ... --json` calls, including `--headed` for that mode and the final successful `close`.

Each mode captured 22 sets of 48000 samples at 48000 Hz and 44100 Hz, with 375 actual callbacks per case and quantum 128. All samples matched Node and the appropriate reference exactly. All 22 sample hashes also match the reviewed base. The unchanged shipping null page remained in the existing verifier workflow and passed all five events in each mode. No page errors occurred. The headed screenshot was inspected and shows all 22 cases passing.

Observed environment: Node v24.20.0, V8 13.6.233.17-node.53, Darwin arm64, pnpm 10.17.1, agent-browser 0.36.0, reduced Chrome and HeadlessChrome 152 user agents.

## Executable hashes

`comparison.json` verifies these hashes and the unchanged sample hashes across both modes.

| Page | Reviewed base SHA-256 | Final SHA-256 |
| --- | --- | --- |
| `program-test.html` | `b2ae817d4b6fc607ad285d8ea1a105aff238d3bca2f0dcba24c9968d79b6648e` | `f75cb67f10edfe99436de17c09cb5c95fe4574bfc91be7622d905fe48538c5cf` |
| `index.html` | `8db6ed638ad32095d5b8a3c3979beed48900a4dd840d2b4f07f0ea49f67c2a31` | Same |
| `null-test.html` | `b484bf05971c65357c7566dd7fd9cc61d68f2ac4a014d8183a2d88888a1cf38a` | Same |

Modified file sizes are 217, 484, 67, and 252 lines. Their maximum function sizes are 36, 41, 15, and 51 lines, respectively. The existing parser-based sizing proof supplied these measurements.

## Limits and development notes

The Git checks are snapshots around the operation. They do not lock the checkout or detect a change made and reverted between snapshots. Ignored dependencies and the installed toolchain are outside Git status enforcement. Rebuilding and comparing hashes binds the observed pages to this build invocation; it provides no hermetic build or toolchain attestation.

Browser evidence remains offline sample equality. It establishes no real-time deadline, browser heap, device, wire protocol, worker preparation, active replacement, or shipping host migration claim. No such behavior changed.

An initial formatting command incorrectly selected unavailable Prettier and exited 254 without editing files. The repository's actual `oxfmt` command was then used. Initial focused and full gates passed. A first final full gate overlapped the deliberately dirty checker probes; `check-clean-final.log` repeats the entire gate after sentinel cleanup, with no source mutation probes running.

Independent review of this correction remains pending. The previous unit's clean review is preserved as evidence for its own SHA.

The Markdown index refresh rejected `/Users/alphab/.mdx/projects` as outside its configured root. Index roots were left unchanged. The report and digest were verified directly on disk.
