# audit-runtime (ddac0df9) recovery assessment

Observed 2026-09-05 04:46:47Z. Read-only. Nothing mutated.
Follow-up to `latency-investigation.md`; scope limited to this one run.

## Verdict: retry loop, not a live slow request. Waiting is no longer justified.

Turn 67 has now been attempted **three times on the same payload**, each attempt closing
after ~29 minutes having delivered **zero frames, zero tokens and no stop reason**.

| attempt | issued | closed | wall | outcome |
| --- | --- | --- | --- | --- |
| turn 66 | 03:49:28 | 04:17:02 | 1653.8 s (27.6 min) | `ws_close_1011`, 0 in / 0 out |
| turn 67 #1 | 04:17:03 | 04:46:17 | 1754.2 s (29.2 min) | closed, **no stop_reason, no tokens** |
| turn 67 #2 | 04:46:18 | in flight | — | identical 821,410-byte payload |

The reissue is byte-identical: `request_raw_bytes = 821410` on both turn 67 attempts. The
harness is replaying the same request on a fixed ~29-minute cycle and getting nothing back.

**Last successful output was turn 65 at 03:49:20Z** (168,519 in / 154 out). This run has
produced no model output for 57 minutes.

## Why this is not the fleet incident

The four peer runs released and **produced real completions** (`347552a4` returned
`stop_reason=completed` with 4086 output tokens after its 2376 s wait). Thirty codex
exchanges have completed normally since 04:33Z, and `consolidation.json` was written at
04:41:10Z. The queue drained. This run did not benefit, because its failure is
deterministic and self-repeating, not a queue wait.

The likely reason is payload size. 821,410 bytes is **4x the largest successful request in
this run** (43,734 bytes) and **41x the last successful one** (20,035 bytes). It is the
full ~240k-token conversation replayed after the `ws_close_1011`. It fails at the same
~29-minute mark every time and returns nothing.

## Footer vs wire, requested vs effective effort

Stuart's footer reads `gpt-5.6-luna xhigh`. **The wire confirms it.** This is not a display
artifact.

`request_extras.reasoning.effort` census across all 71 exchanges of this run:

| effort on wire | count | first | last |
| --- | --- | --- | --- |
| `xhigh` | 70 | 03:28:54 | 04:46:18 |
| `low` | 1 | 03:28:59 | 03:28:59 (prewarm) |

The launch receipt in `runs.json` records `"effort": "high"`. Effective effort has been
`xhigh` on every substantive request since the first one. The footer is accurate; the
**launch receipt is what diverges from the wire**.

This is a real requested-vs-effective divergence worth filing separately. It is a
*contributing* factor, not the proximate cause: higher reasoning effort inflated tokens per
turn, which is consistent with this run reaching the fleet's highest context (247,078) and
highest turn count (279). It did not cause the retry loop, and it was already `xhigh`
during the run's healthy fast turns (8-12 s at 03:47-03:49).

## Report artifacts: none exist

No `runtime.md` and no `runtime.json` in the project directory. The only files written
since 04:15Z are `authority.md`, `consolidation.json` and the two latency artifacts.

**All of this run's research exists only in its transcript.** The largest output burst,
3,635 tokens at 03:48:04Z, was almost certainly the report being drafted in-message rather
than written to disk. That work is recoverable while the pane lives and is lost if the run
is closed.

## Recommended action: interrupt and re-prompt. Do not close, do not replace.

Waiting buys another 29-minute empty cycle. The evidence for waiting, which held in the
previous report, was that peers released with real completions. This run has now failed the
same turn three times.

Least disruptive sequence, preserving completed research:

1. **`interrupt(ddac0df9-ab44-4277-8ea4-bed514a51dda)`** to cut the in-flight 821 KB
   request. The transcript stays in the pane; nothing researched is lost.
2. **`nudge` immediately**, with a prompt that writes before it thinks. Suggested text:

   > Stop all further research. Write what you already have to
   > `/Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/runtime.md` and
   > `runtime.json` now, in one pass, covering issues 603, 565, 504, 482, 472, 471, 459,
   > 460. Mark any issue you did not finish as `status: incomplete` rather than omitting
   > it. Keep the write short. Do not read further files before writing.

   This converts transcript-only research into a durable artifact and shrinks the next
   request well below the size that is failing.
3. **Only if step 2 also fails to return**, the run is unrecoverable through the provider.
   Harvest its findings by reading the transcript directly via
   `conversation(ddac0df9-..., shape="summary")` and hand them to the orchestrator. Still
   do not close the pane until harvested.

Do not launch a replacement. A fresh run would re-do 279 turns of research from zero
against the same endpoint.

## Local CPU saturation (added 04:48Z on Stuart's evidence)

Stuart's Activity Monitor reading (0.00% idle, 82.59% user, 17.41% system, 2,594 processes,
23,026 threads) is confirmed and my earlier "nothing local is slow" was too strong. Measured
at 04:48:09Z on a 12-core host:

- **Load average 51.44 (1m) / 147.11 (5m) / 330.48 (15m)**. The 15-minute figure is 27x the
  core count. The steep decay 330 -> 147 -> 51 means the peak sat inside the stall window
  and is now draining.
- 2,600 processes, 22,185 threads.

### Attribution: the dominant consumer is not the audit

| pid | %CPU | elapsed | process | audit-related |
| --- | --- | --- | --- | --- |
| 64139 | **549.8** | 9d 02h | Apple `Virtualization.VirtualMachine.xpc` (with `com.docker.backend` 14.9%) | **no**, predates audit by 9 days |
| 48471 | **84.5** | 2d 10h | `~/.pyenv/versions/3.14.5/bin/python3` | **no**, predates audit by 2 days |
| 82261, 83341, 82426, 82614, 7217, 83809, 21060, 58054, 37889 | 70.6, 51.4, 48.4, 45.9, 42.7, 41.4, 40.2, 31.5, 26.2 (**~398% total**) | ~1h19m, matching the 03:28Z launch | transport-matters capture layer, ppid 94154 | yes |
| 409 | 18.8 | 19d | WindowServer | no |

The VM alone holds ~4.6 of 12 cores and the stray pyenv python another ~0.7. Roughly
**5.3 cores are consumed by processes that have nothing to do with this audit**, leaving
about 6.7 cores for nine concurrent agent runs whose capture layer alone wants 3.3.

### No leaked test subprocesses or parallel workers

Direct answer to the question asked: **none found.**

- `pytest`: 0 processes. `vitest`: 0. `jest`: 0.
- The `codex` harness binaries themselves are cheap (0.4-0.7% each) and their count matches
  the live run count with no orphans.
- The audit was read-only issue review and never invoked a test suite, so there is no
  worker fanout to reap. The high process and thread totals are the VM, Electron helpers
  under `node_modules`, and normal desktop load, not audit residue.

### How this changes the ddac0df9 diagnosis

It **weakens the clean "upstream only" attribution** and I am revising that claim. Under CPU
starvation the response-side streaming, capture and persistence path for an 821 KB request is
plausibly slow enough to contribute to an empty close. I cannot cleanly separate an upstream
stall from local starvation with the evidence available.

What survives unchanged is the discriminator for **this** run: the Sol investigator and the
orchestrator completed turns normally at 04:29-04:46Z on the same saturated host, and 30
codex exchanges completed since 04:33Z. Saturation degrades everything but only ddac0df9 is
looping on a byte-identical replay. Payload size remains the variable specific to this run.

The two now compound: an oversized request is exactly the request most likely to fail when
the machine has no headroom to stream and persist it.

### Added recommendation, ahead of the interrupt

**Step 0, least disruptive of all and it touches no agent:** reclaim the ~5.3 cores held by
non-audit processes. `Virtualization.VirtualMachine.xpc` (pid 64139, 549.8%, 9 days old, the
Docker VM) and the stray pyenv python (pid 48471, 84.5%, 2 days old) are the candidates.
Attribution only here as instructed, no process was signalled. Freeing that headroom may let
the in-flight retry complete without any agent being touched, and it improves the odds that
the step 2 re-prompt write succeeds.

If step 0 is declined or does not help within one retry cycle (~29 minutes), proceed with the
interrupt and re-prompt as written above.

## Evidence paths

- `postgres transport_matters_preview` → `wire_exchange` filtered to
  `run_id='ddac0df9-ab44-4277-8ea4-bed514a51dda'` (columns `ts`, `created_at`,
  `stop_reason`, `response_complete`, `input_tokens`, `output_tokens`,
  `request_raw_bytes`, `request_extras->'reasoning'->>'effort'`)
- `/Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/runs.json` (launch
  receipt recording `effort: high`)
- `/Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/` directory listing
  (absence of `runtime.md` / `runtime.json`; `consolidation.json` at 04:41:10Z)
- `/Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/latency-investigation.md`
  (fleet context; its "local infrastructure healthy" claim is superseded by the CPU section above)
- `uptime`, `ps -Ao pid,ppid,pcpu,etime,comm -r`, `ps -AM | wc -l` at 04:48:09Z

## Unverified boundaries

- Payload size as the failure trigger is inferred from the correlation between the
  821,410-byte replay and three consecutive empty ~29-minute closes. No upstream error body
  was returned to confirm it.
- Turn 67 attempt 1 closed with `response_complete = t` but no `stop_reason`, so the close
  reason is not recorded. It is not classified as `ws_close_1011` the way turn 66 was.
- The `high` to `xhigh` divergence is established on the wire against the launch receipt.
  Where the substitution happens, control plane or harness, was not traced.
- Upstream stall and local CPU starvation cannot be cleanly separated as causes of the empty
  ~29-minute closes. Both are present and both are plausible contributors.
- %CPU from `ps` is an average over process lifetime, not an instantaneous sample, so the
  long-lived VM and pyenv figures describe sustained load rather than the 04:45Z instant.
