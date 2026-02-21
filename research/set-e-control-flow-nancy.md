---
title: Nancy set-e lifecycle control flow diagnosis
type: research
tags: [nancy, bash, set-e, control-flow, alp-2420]
summary: Nancy epilogue uses a nonzero return code as a normal continue signal, which exits under the current set -e entrypoint before the caller can capture it.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-15
updated: 2026-05-15
---

## Executive Summary

Nancy's start loop has a Bash control flow bug. `_start_iteration_epilogue` returns `2` to mean continue, but `cmd::start` calls it as a standalone command under `set -euo pipefail`, so Bash exits before `local epilogue_status=$?` can run.

The apparent iteration 7 versus iteration 8 paradox is explained by live pane evidence. Iteration 8 began from a fresh `_worker` invocation, so it did not prove that iteration 7's epilogue return survived `set -e`.

## Project Metadata

* Project: Nancy autonomous task execution loop
* Language: Bash shell framework plus Python analysis helpers
* Entry point: `./nancy`
* Runtime Bash: `/opt/homebrew/bin/bash`, GNU Bash `5.3.9(1)-release`
* Build and checks: `Justfile` provides `check`, `build`, and `test`
* fmm status: `.fmm.db` exists and `fmm validate` passed for 19 indexed files. fmm indexes the Python and test subset only. `src/cmd/start.sh` and `src/cmd/start_dispatch.sh` are missing from the fmm index, so those shell files were inspected with targeted numbered reads after fmm orientation.

## Architecture

The relevant path is:

1. `./nancy` sets `set -euo pipefail` at line 6 and dispatches `start` to `cmd::start` at lines 63 to 104.
2. `cmd::start` prepares the loop, calls `_start_run_iteration`, then dispatches on `turn["action"]` at `src/cmd/start.sh:613-644`.
3. `_start_run_iteration` writes selector state, chooses worker or reviewer mode, runs the active agent, then sets `turn["action"]="epilogue"` at `src/cmd/start_dispatch.sh:165-290`.
4. `_start_iteration_epilogue` handles stop files, optional review, completion, pause waiting, archives comms, sleeps, then returns `2` for normal continuation at `src/cmd/start_dispatch.sh:292-350`.

## Key Patterns

* The loop already uses an explicit action map for `_start_run_iteration`: `return`, `pause`, and `epilogue` are data in `_turn`, while the function returns `0` for normal lifecycle routing.
* The epilogue diverges from that pattern by encoding normal lifecycle routing in a nonzero function return.
* In Bash with `set -e`, a nonzero function return is safe to inspect only when the call is in a conditional or `||` context. Those contexts also suppress `errexit` inside the callee, which can hide real setup failures.

## Detailed Findings

### Reproduction

A minimal script using `/opt/homebrew/bin/bash` with `set -euo pipefail` confirmed that a standalone function returning `2` exits immediately. A second repro matching `src/cmd/start.sh:625-637` printed the epilogue body, did not print the captured status, and exited with status `2`.

Guarded variants such as `if f; then ...; else status=$?; fi` and `f || status=$?` can capture the status. That is not a clean structural fix because Bash ignores `errexit` inside functions invoked in those contexts.

### Iteration 7 paradox

There are two pause paths:

* Null selected work uses `_start_handle_null_selection`, which returns `2` for `agent_stuck` and `product_decision` at `src/cmd/start_dispatch.sh:59-67`. Its caller guards the return at `src/cmd/start_dispatch.sh:193-209`, then `cmd::start` waits and continues at `src/cmd/start.sh:620-622`.
* `workflow_repair` is selected work. It bypasses the null-selection branch, records repair at `src/cmd/start_dispatch.sh:212-265`, runs an agent, then reaches epilogue through `turn["action"]="epilogue"` at `src/cmd/start_dispatch.sh:286-289`.

The live ALP-2408 pane showed this command immediately before iteration 8:

```text
cd ... && NANCY_CURRENT_TASK_DIR=... /Users/alphab/Dev/LLM/DEV/TMP/nancy/nancy _worker ALP-2408
```

It then printed `Starting Nancy: ALP-2408` and `Iteration #8`. A continuous loop would not print the start banner again. Iteration 8 was a new worker process after the session count reached 7.

The same pane later showed the active failure shape: `Iteration #8 completed`, `Legacy code review hook skipped for gate aware mode: execution`, `Starting next iteration in 2s...`, and then a shell prompt. That maps to `src/cmd/start_dispatch.sh:344-349`, where the epilogue returns `2`.

### Latent bugs found

* `src/cmd/start.sh:625-626` cannot capture any nonzero epilogue status under `set -e`. The `case 2) continue` branch at `src/cmd/start.sh:627-633` is unreachable for the normal continue signal.
* `_start_handle_null_selection` return `2` is safe in the general null-selection caller at `src/cmd/start_dispatch.sh:195`. The `final_completion` call at line 187 is standalone, but that branch should return `0`.
* `_start_selection_has_no_issue` can return `2` at `src/cmd/start_dispatch.sh:25-27`, but no call site was found in the two start files.
* `_start_wait_while_paused` lacks an explicit `return 0` after resume at `src/cmd/start.sh:158-160`, so it returns the status of `log::info`.
* `_start_run_iteration` is invoked through `|| return $?` at `src/cmd/start.sh:615`. Bash suppresses `errexit` inside that function, so unguarded setup operations inside `src/cmd/start_dispatch.sh:240-280` can be masked.
* `local var=$(...)` appears on important paths such as `src/cmd/start.sh:51`, `83`, `86`, `248`, `260`, and `263`. Bash `local` can mask command substitution failures.
* `((sidecar_active == 1)) && sidecar::stop ...` at `src/cmd/start.sh:314` and `511` has context-sensitive failure behavior. Guarded callers can swallow stop failures, while standalone contexts can exit on the right side of `&&`.

### Verification performed

* Confirmed `.fmm.db` exists and `fmm validate` passes.
* Confirmed `src/cmd/start.sh` and `src/cmd/start_dispatch.sh` are absent from the fmm index.
* Reproduced standalone `return 2` behavior on the actual Bash runtime.
* Reproduced the exact epilogue caller shape from `cmd::start`.
* Captured ALP-2408 tmux pane evidence showing iteration 8 started from a fresh `_worker` invocation.
* Ran `bash -n ./nancy src/cmd/start.sh src/cmd/start_dispatch.sh`, which passed.
* Verified the investigation left the target worktree clean with `git status --short`.

## Dependencies

* Bash `set -euo pipefail` semantics are the central dependency.
* `tmux` pane history provided live process evidence.
* fmm provided initial topology, but not shell symbol indexing for the target files.
* `Justfile` check exists, but only `bash -n` was run because this was a read-only diagnosis.

## Relevance to Helioy

Nancy is part of the Helioy autonomous work loop. This bug can stop relay execution after a successful worker turn, leaving Linear and `.nancy` state stale until a fresh worker is started. The clean repair should preserve Nancy's ability to run unattended across selected work, workflow repair, and blocker modes.

## Structural Recommendation

Use explicit lifecycle data instead of nonzero function returns for normal loop control. Extend the existing `_turn` pattern or pass a separate epilogue nameref so `_start_iteration_epilogue` returns `0` for normal outcomes and sets `action=continue` or `action=complete` in data. Reserve nonzero returns for real failures.

A caller guard such as `_start_iteration_epilogue ... || epilogue_status=$?` is a tactical hotfix, but it places the whole callee in an `errexit` ignored context. Using `if` has the same downside. Disabling `set -e` for the loop body would broaden the risk. Data-driven lifecycle state is the most consistent and safest shape.

## Open Questions

* Whether the immediate branch should ship a tactical caller guard first, then refactor lifecycle signaling in a follow-up.
* Whether tests should add a full `cmd::start` loop harness under `set -e` to prove the continue path reaches the next iteration.
* Whether shell fmm support or generated outlines should be added so Bash control flow can be analyzed with the same structural tooling as the Python subset.
