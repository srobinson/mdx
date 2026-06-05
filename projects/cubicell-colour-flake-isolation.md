# cubicell colour flake isolation (base main)

**Date:** 2026-08-05  
**Checkout:** `/Users/alphab/Dev/LLM/DEV/helioy/cubicell`  
**Branch / SHA:** `main` @ `72934382262c5d760b0329d9fb52f7d864cd6443`  
**Command:** `pnpm test` (= `vitest run tests --project unit`)  
**Topic:** `cubicell-colour-probe`

## Boundary

- Main repo only. Colour worktree not touched.
- No writes, no format/lint --fix, no commits, no branch changes.
- `git status --porcelain` empty before and after all three runs.

## Question

Do camera-track tests and `cubeInstanceSlots` fail intermittently on base, with the accent change nowhere in the tree?

## Answer

**No.** Base is green **3/3**. Neither camera-track failures nor a `cubeInstanceSlots` timeout appeared in any run.

## Verdict

**Caused by the change** (or by environment/load only present when reviewing the change). Base does not reproduce the reported flake pattern. This is a **Blocker** signal for merge until the change-side failures are explained or fixed. Do not treat those review failures as pre-existing flake on the evidence of this measurement alone.

## Summary table

| Run | Exit | Files | Tests | Failing test names |
|-----|------|-------|-------|--------------------|
| 1 | 0 | 187 passed | 2605 passed | *(none)* |
| 2 | 0 | 187 passed | 2605 passed | *(none)* |
| 3 | 0 | 187 passed | 2605 passed | *(none)* |

- camera-track flakes on base: **no**
- `cubeInstanceSlots` timeout on base: **no**

## Run 1 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:03:57
   Duration  20.72s (transform 22.08s, setup 39.03s, import 54.75s, tests 38.84s, environment 53.08s)
```

Full log: `/tmp/cubicell-flake-run1.out`  
EXIT: 0  
Failing tests: none.

## Run 2 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:04:19
   Duration  33.25s (transform 35.71s, setup 53.65s, import 80.32s, tests 81.98s, environment 93.05s)
```

Full log: `/tmp/cubicell-flake-run2.out`  
EXIT: 0  
Failing tests: none.

## Run 3 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:04:53
   Duration  19.21s (transform 29.97s, setup 37.82s, import 48.26s, tests 44.00s, environment 44.24s)
```

Full log: `/tmp/cubicell-flake-run3.out`  
EXIT: 0  
Failing tests: none.

## Notes

- Relevant camera-track files present and green in all runs (e.g. `cameraTrackSampleAt.test.ts`, `cameraTrackAuthority.test.ts`, `cameraTrack.test.ts`, `cameraTrackPersistence.test.ts`).
- No `cubeInstanceSlots` failure string in any of the three full logs.
- Tree still clean after runs: SHA `72934382262c5d760b0329d9fb52f7d864cd6443`, porcelain empty.

---

# Confound check (interleaved change vs base)

**Date:** 2026-08-05  
**Method:** Interleaved `pnpm test` three times each: change run N, then base run N.  
**Change:** `/Users/alphab/Dev/LLM/DEV/helioy/cubicell/.claude/worktrees/colour` @ `408b2687cd0393f533f3f77afd93d407ab29a6ae`  
**Base:** `/Users/alphab/Dev/LLM/DEV/helioy/cubicell` @ `72934382262c5d760b0329d9fb52f7d864cd6443`  
**Boundary:** no writes; both trees porcelain=0 before and after.

## Machine conditions

**busy** (not quiet). Load averages during the block:

| When | load averages |
|------|----------------|
| Start | 15.76 18.49 15.79 |
| Mid (change run 2) | 21.19 19.59 16.30 |
| Mid (change run 3) | 23.33 20.25 16.70 |
| End | 24.01 20.87 17.10 |

Observed concurrent load: Chrome (incl. many renderer helpers), VS Code helpers, Codex process, Virtualization VM, multiple agent runtimes. Not a clean machine, and load *rose* through the six runs.

## Results

| Pair | Change exit | Change counts | Change fails | Base exit | Base counts | Base fails |
|------|-------------|---------------|--------------|-----------|-------------|------------|
| 1 | 0 | 187 files / 2609 tests | none | 0 | 187 files / 2605 tests | none |
| 2 | 0 | 187 files / 2609 tests | none | 0 | 187 files / 2605 tests | none |
| 3 | 0 | 187 files / 2609 tests | none | 0 | 187 files / 2605 tests | none |

Notable change-side timings (still pass under load):

- `tests/cubeInstanceSlots.test.ts`: ~2241ms / 2397ms / 2342ms
- `tests/cameraTrackPlayback.test.tsx`: ~965ms / 1195ms / 885ms
- `tests/cameraTrackMount.test.tsx`: ~1036ms / 1087ms / 1448ms

No FAIL lines, no `Test timed out`, no camera-track failures, no `cubeInstanceSlots` timeout in any of the six logs.

Full logs: `/tmp/cubicell-confound/change-run{1,2,3}.out`, `/tmp/cubicell-confound/base-run{1,2,3}.out`

### Change run 1 raw tail

```
 Test Files  187 passed (187)
      Tests  2609 passed (2609)
   Start at  13:06:46
   Duration  17.89s (transform 23.38s, setup 32.21s, import 47.49s, tests 37.73s, environment 43.75s)
```

### Change run 2 raw tail

```
 Test Files  187 passed (187)
      Tests  2609 passed (2609)
   Start at  13:07:25
   Duration  19.22s (transform 24.75s, setup 32.89s, import 49.86s, tests 44.05s, environment 48.79s)
```

### Change run 3 raw tail

```
 Test Files  187 passed (187)
      Tests  2609 passed (2609)
   Start at  13:08:06
   Duration  20.14s (transform 26.00s, setup 34.70s, import 53.86s, tests 46.83s, environment 52.37s)
```

### Base re-run 1 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:07:05
   Duration  20.08s (transform 26.27s, setup 33.37s, import 52.25s, tests 47.60s, environment 49.97s)
```

### Base re-run 2 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:07:45
   Duration  20.09s (transform 29.16s, setup 37.03s, import 53.30s, tests 45.79s, environment 47.97s)
```

### Base re-run 3 raw tail

```
 Test Files  187 passed (187)
      Tests  2605 passed (2605)
   Start at  13:08:27
   Duration  20.10s (transform 25.67s, setup 33.87s, import 55.10s, tests 44.52s, environment 49.75s)
```

## Verdict (confound closed)

**contention.** Change **3/3 green** and base **3/3 green** under equal interleaved conditions while the machine was busy. The earlier reviewer failures (camera-track + `cubeInstanceSlots` timeout under warroom/browser load) do not reproduce as a change-specific regression in this measurement. The accent slice is **exonerated** on unit-suite flake grounds; a suite run under multi-agent saturation is not a reliable gate.

Combined with the prior base-only 3/3 green block: no evidence of a unit-test regression on either tree under the conditions exercised here.
