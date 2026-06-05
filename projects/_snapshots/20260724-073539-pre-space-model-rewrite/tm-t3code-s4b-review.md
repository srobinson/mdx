---
title: Review — t3code P1 slice 4b — ScrollbackRing + TerminalFanout re-port (PR#237)
type: projects
tags: [transport-matters, t3code, p1, slice-4b, code-review, scrollback, fanout, resume-from-seq, runtime]
summary: Adversarial parity review of PR#237 (feat/scrollback-s4b @ 45e86c5) vs main. Production ring/fanout logic is a faithful, correct port — 0 blocker, 0 major. 7 minor findings (2 test-coverage gaps, 2 faithfulness edges, 1 efficiency, 1 DRY, 1 buffer-aliasing) + 2 forward notes for 4c. All gates green.
status: active
source: opus fresh adversarial review, baseline main, head 45e86c5, tree pristine
confidence: high — parity verified line-by-line against run_terminal.py + the scout contract; 3 independent finder passes + manual pass converge
created: 2026-07-07
---

# Review — slice 4b: ScrollbackRing + TerminalFanout parity (PR#237)

**Verdict: CLEAN PORT with 7 minors.** The production logic (`ScrollbackRing`,
`TerminalFanout`, `TerminalQueue`) is a behaviour-faithful, correct re-port of
`api/src/transport_matters/run_terminal.py`. No Blocker, no Major. Every focus
area in the brief holds:

- **Byte-cap eviction** matches Python `_trim` exactly: whole-chunk `shift()`
  oldest-first while `total > cap`, same `>` boundary, `total` decremented by the
  evicted chunk's stored bytes; the just-stored chunk always survives (it is
  `<= cap` by the tail-slice step). Cap holds after every append.
- **Sequence arithmetic**: `seq`/`nextSeq += 1` run unconditionally before any
  early return, so seq advances on empty data and the `maxBytes === 0` path;
  monotonic from 0, no gaps/dupes; `floorSeq` uses `?? null` (a real `seq === 0`
  floor is returned, not nulled).
- **Resume-from-seq**: `attach()` is fully synchronous — `snapshot()` → read
  `nextSeq` → register, no await/microtask between — so `startSeq === nextSeq`,
  every snapshot seq `< startSeq`, and the queue then delivers exactly seqs
  `>= startSeq`. The single most fragile invariant is intact. Evicted-floor:
  late attach receives the surviving snapshot + `truncated`, no under-floor path.
- **Raw-byte fidelity**: stores `Uint8Array`, caps by `byteLength`, tail-slices
  by bytes via a copying `Uint8Array.from(subarray(...))` (no 2 MiB backing-buffer
  retention); `copyBytes` copies off the producer buffer on append (R3).
- **Purity**: `domain/terminal/ScrollbackRing.ts` imports only the `Clock` type,
  no IO/timers; `randomUUID` lives in the service layer (correct). No serving/WS
  wiring crept in.
- **Gates**: `just check` (tsc + ruff + mypy) exit 0; Python suite 1830 passed;
  `@tm/runtime` vitest 46/46.

Counts: **0 Blocker · 0 Major · 7 Minor**. Plus 2 forward notes scoped to 4c.

---

## Findings (ranked, all Minor)

### M1 — `TerminalQueue` waiter fast-path gives +1 effective slot vs `asyncio.Queue`
`packages/runtime/src/service/TerminalFanout.ts` — `TerminalQueue.tryPush` (~line 31-40)

`tryPush` hands an item straight to a parked `take()` waiter and returns `true`
without it ever occupying a buffer slot. A real `asyncio.Queue(maxsize=N)` leaves
a put item in `_queue` and only *schedules* the woken getter, so the next
`put_nowait` at the boundary can still see `qsize() >= N` and raise `QueueFull`.

Concrete divergence: `TerminalQueue(1)` with a parked waiter — `tryPush(A)`
delivers A directly (items stays `[]`), then `tryPush(B)` buffers B and returns
`true`. `asyncio.Queue(1)` with a parked getter — `put_nowait(A)` leaves A in
`_queue`, `put_nowait(B)` raises `QueueFull`. So an attachment that Python would
slow-close (`retryable-overload`) survives in TS.

Scope/severity: **latent** — no 4b path parks a waiter (the fanout never calls
`take()`; tests drain via `tryTake`); it manifests only once the 4c WS pump does
`await take()`. Arguably the *more correct* behaviour (delivering to a ready
consumer is not overload). Surfaced because it is a genuine semantic divergence
from the asyncio baseline that the parity suite does not cover. Disposition is
the orchestrator's: accept as benign/better, or match asyncio by counting the
waiter delivery toward capacity. If accepted, a 4c parity test should park a real
consumer to pin the intended semantics.

### M2 — `attachmentId` uses `??`, diverging from Python `or` on empty string
`packages/runtime/src/service/TerminalFanout.ts` — `attach()` `attachmentId: input.attachmentId ?? randomUUID()...` (~line 113)

Python: `attachment_id or uuid4().hex` coerces falsy `""` to a fresh UUID. TS
`input.attachmentId ?? ...` keeps `""`, so `attach({attachmentId: ""})` registers
under key `""`; a second such attach silently *replaces* the first (orphaning its
queue with no close item). This is the same `??`-vs-`or` falsy gap the scout
flagged as R4 — and the builder *did* handle it for `queueMaxSize` (via
`queueSizeWithDefault` treating `0` as default) but not for `attachmentId`, so the
two coercion paths are inconsistent. Low reachability (routes always generate
ids). Fix: a truthy check (`input.attachmentId || randomUUID()...`) to match the
baseline, or document the intentional `??` divergence.

### M3 — Eviction tests can't distinguish whole-chunk eviction from partial-slicing
`packages/runtime/src/domain/terminal/ScrollbackRing.test.ts` — "evicts whole chunks..." (~line 8) and "returns snapshots that do not track later trims" (~line 53)

Contract §4a mandates "evict whole chunks oldest-first … No partial slicing of
the oldest chunk." Both eviction tests use chunk sizes where evicting the whole
oldest chunk lands *exactly* at the cap, so a regression that shaved bytes off the
oldest chunk to hit the cap yields an identical snapshot and stays green. No test
constructs the distinguishing case: oldest chunk strictly larger than the
overshoot (e.g. cap 5, stored `[aaa(seq0), bb(seq1)]`, append `c(seq2)` →
whole-chunk gives snapshot seqs `[1,2]`; partial-slice gives `[0,1,2]` with a
corrupted seq0 fragment). The whole-chunk invariant is currently unpinned. Add a
non-uniform eviction case asserting the evicted chunk vanishes whole.

### M4 — `truncated` is never asserted `false`; the sticky flag's default is unpinned
`packages/runtime/src/domain/terminal/ScrollbackRing.test.ts` — every `truncated` assertion (~line 21, 36, 50)

All assertions expect `truncated === true`. A regression that sets the sticky
flag spuriously (on every append, or on an empty append at `maxBytes === 0`, which
I3 forbids) passes the whole suite — the `maxBytes === 0` test appends empty then
non-empty and only checks the final `true`. Add an assertion that a within-cap
ring stays `truncated === false`, and that an empty append does not flip it.

### M5 — `append` allocates a throwaway map-copy per PTY read
`packages/runtime/src/service/TerminalFanout.ts` — `append()` `Array.from(this.attachmentMap.values())` (~line 128)

`append` runs per 8 KiB PTY read (the hottest path). The broadcast loop only
`tryPush`es and never mutates the map (closes are deferred to the second loop over
`overloadedAttachmentIds`), and `tryPush`'s waiter callback is a native promise
resolver (microtask-deferred, cannot synchronously mutate the map). Iterating
`this.attachmentMap.values()` live is therefore safe and drops the per-chunk
allocation — exactly the shape the scout prescribed ("iterate `Map.values()`
live, keep the deferred-close list"). (`closeAll`'s `Array.from(keys())` copy is
correct and must stay — it *does* mutate mid-iteration.)

### M6 — `Clock` interface duplicated across packages (known R5)
`packages/runtime/src/ports.ts` — `interface Clock { now(): Date }` (~line 64)

Byte-identical to `packages/activity/src/ports.ts::Clock`; `@tm/common` owns none.
`packages/AGENTS.md`: "The moment a primitive is needed by a second package it
belongs in `@tm/common`, not copied. Duplication across packages is a defect."
Runtime is that second consumer. This is the scout's R5 (promoting touches
`@tm/activity`, blast radius beyond the slice; spec §7 lists `Clock` in runtime
`ports.ts`), explicitly left as the orchestrator's call — surfaced here so the
deferral is a conscious decision, not an oversight. Recommend: promote to
`@tm/common` with `@tm/activity` re-exporting, or record the deferral as a tracked
follow-up with the reason.

### M7 — Stored ring chunk aliases the broadcast live chunk's mutable buffer
`packages/runtime/src/domain/terminal/ScrollbackRing.ts` — common path `storedData = liveData` (~line 88)

In the non-oversize path the chunk pushed to the ring and the chunk returned/
broadcast to every viewer share one `Uint8Array` (`storedData === liveData`).
Faithful to Python — but Python's `bytes` is immutable, whereas `Uint8Array` is
not, so any consumer that mutates a received broadcast chunk's `data` would
corrupt stored scrollback and every other viewer's bytes. Benign today (the
pipeline treats `data` as read-only; `snapshot()` deep-copies for replay), so
**Low** — but R3 ("the ring must own its bytes") argues for isolation, and no test
proves stored/broadcast independence (the oversize test's `source.fill(0)` proves
copy-from-*source* only). Optional: give the stored chunk its own copy, or add a
test asserting a mutated broadcast chunk does not perturb `snapshot()`.

---

## Notes for 4c (out of 4b scope — not findings)

- **R1 slow-viewer close deliverability.** `closeAttachment` `tryPush`es the close
  item onto a still-full queue in the overload path, so it is dropped — the Python
  bug reproduced faithfully. The builder added an out-of-band `closedReason` on the
  attachment, but a 4c reader blocking on `take()` never observes it and inherits
  the frozen-tab defect. `TerminalFanout.test.ts` (~line 91-92) pins the drop, so a
  future in-band fix will fail that assertion and look like a regression. Confirm
  this is the locked R1 disposition before 4c.
- **Abandoned-waiter item loss.** If a 4c consumer calls `take()` then abandons the
  returned promise (cancel/abort), a later `tryPush` resolves a dead promise and the
  item (including a close item) is lost — `asyncio.Queue.get()` on cancellation
  re-wakes the next getter and retains buffered items. Latent property of
  `TerminalQueue`; only bites once 4c adds a cancellable consumer.

## Evidence
- `git status --porcelain` empty; `HEAD == 45e86c545ecea31a07e40fa014525456412fee30`.
- `just check`: tsc (all packages) + ruff + mypy (461 files) — exit 0.
- `just test`: Python 1830 passed.
- `pnpm --filter @tm/runtime test`: 6 files, 46 tests passed.
