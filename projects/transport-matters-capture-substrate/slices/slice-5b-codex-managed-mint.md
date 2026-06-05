# Slice 5b — codex managed-mint launch + delete `locate` (tail-race fix)

**Goal:** eliminate the codex transcript tail RACE by **owning** the codex session id
and rollout path at launch time. Delete the read-back discovery path (`locate` glob) —
it is unreachable dead code given the proxy-injection invariant, not code to relocate.

**Supersedes:** the read-back half of slice 5 (#25). Wire capture from #25 stays; this
slice changes how the transcript side is located and correlated. **Depends on:** #25
merged. **Branch:** off current `main` (was `33e087a`).

## Root cause (road-test #3)

A real `transport-matters codex` run captured wire (4 exchanges) but `transcript_turn=0`.
Codex wrote the rollout ~1s AFTER the cursor registered (first wire frame), so the
one-shot `locate()` glob missed, fell back to a dead root path, and never retried →
permanent miss. Intermittent: an earlier run won the race (12 turns). Three defects,
all symptoms of guessing at a path TM does not own:
- one-shot `locate` (tailer per-poll), `tailer.py:210-211`
- dead-root fallback on glob-miss, `codex.py:72-76`
- `_poll_cursor` early-return-on-missing-path, `tailer.py:141-143`

## Locked decision (Stuart; reviewer concurred) — DELETE, do not quarantine

"External observed codex" is **unreachable on the wire**: codex only routes through the
TM proxy because `transport-matters codex` injected the proxy env + CA cert. Therefore
**any wire frame ⇒ TM launched it ⇒ TM owns the uuid + path.** Discovery is never
needed for anything TM sees. `locate` is dead code.

## Build shape (managed-mint)

1. **Launcher** mints `native_session_id = uuid4()` per codex process; computes the exact
   rollout path `~/.codex/sessions/YYYY/MM/DD/rollout-<ts>-<native>.jsonl`; writes the
   **minimal valid** `session_meta` JSONL first — one record, `payload.{id,timestamp,cwd,
   originator="codex-tui",cli_version}` (verified: `codex resume <uuid>` works on that
   record alone); then launches `codex resume <native>`.
2. Persist `source_descriptor = {"kind":"file_tail","path":...,"format":"codex_rollout",
   "encoding":"utf-8"}` **and** `cli="codex"` on the **session row BEFORE cursor
   registration**. This is what kills the empty-session-row symptom directly.
3. **Tailer reads `source_descriptor` only** and byte-offset tails from 0. "File exists,
   no `response_item` yet" = a normal poll no-op, **NOT** a locate miss.

## DELETE (all of it solved a problem we no longer have)

- `CodexAdapter.locate` glob method (`index/adapters/codex.py`).
- the dead-root fallback (`codex.py:72-76`).
- the per-poll locate in the tailer (`tailer.py:210-211`).
- the `_poll_cursor` early-return-on-missing-path (`tailer.py:141-143`).
- the retry-locate idea (never build it).
- the window-id phantom handling — TM owns the id now, it never reads a transient first-frame id.

## Residual (OUT OF SCOPE — YAGNI)

Resolving the full filename when **resuming a PRE-EXISTING session TM did not seed** is a
launch-time, **race-free** (the file must exist for `resume` to succeed), one-shot resolve
that lives in the **launcher**, never a per-cursor adapter poll. Only if TM ever supports
resuming external sessions. Do not build it now.

## Invariants (must not break)

- **#17 privacy boundary** (AST-enforced): no cross-module `_`-prefixed imports; every
  cross-module symbol public.
- **DAG:** adapters import `ir` (+ sibling adapters) only; the launcher/wire seam uses the
  injected sink — no `storage → index` import.
- **ONE iterate path:** reuse slice-4b `iter_complete_records` (FileTail, partial-line safe);
  no new iterator.
- `normalize` unchanged: ingests only `response_item`; skips `session_meta`/`turn_context`/
  `event_msg`; `turn_context` is only a model hint; `parts` reuse `ir.ContentBlock` verbatim.
- `binding.native_session_id` = the owned uuid used by `codex resume`; `session_id =
  synth_session_id(run_id,"codex",native)` — wire and transcript MUST converge on the same
  `session_id` (the §7.2 contract the pivot/diff depend on).
- LOC ≤ 700/file, functions ≤ ~150.

## Files (RE-CONFIRM current line numbers against main before editing)

- **launcher** — where `transport-matters codex` builds the codex run/env (confirm the
  module; this is where mint + seed-write + `codex resume` go). Persist `source_descriptor`
  + `cli` onto the binding here.
- `index/adapters/codex.py` — delete `locate` + fallback; keep `bind`/`normalize`.
- `index/tailer.py` — delete per-poll locate + the missing-path early-return; read
  `source_descriptor` and byte-offset tail only.
- session-row population (`cli`, `source_descriptor`) before cursor registration.

## Regression (ALL required)

- **(a) deterministic** — seed the minimal rollout, register the cursor from the descriptor,
  append one `response_item`, poll, assert **exactly one** transcript job from the exact path.
- **(b) concurrency** — 5 managed codex sessions in the **same cwd**, unique uuid/path, one
  response each, assert **zero cross-binding** and **no newest-glob behavior**.
- **(c) negative** — a phantom wire id with no owned descriptor stays harmlessly pending
  (no busy-spin, no error).
- **(d) REAL PROOF** (this is what catches what unit tests miss) — multiple
  `codex resume <uuid>` instances: each session row `cli="codex"` + non-empty
  `source_descriptor`, wire rows bind to the owned session, transcript turns tail from the
  matching file. State the evidence.

## Acceptance

`just ci` green + the real multi-instance proof above. Dual MoE sign-off → orchestrator
gates + PRs + squash-merges.

## Spec fast-follow (post-merge, do NOT block the fix)

§5.2 codex read-back → managed-mint; §15 risk 2 (read-back tail-startup lag) eliminated;
§11.1 cursor note. Update LEDGER + README status on merge.
