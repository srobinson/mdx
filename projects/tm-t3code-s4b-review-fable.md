---
title: Review (fable, 2nd vote) — PR#237 s4b ScrollbackRing + TerminalFanout port
type: projects
tags: [transport-matters, t3code, p1, slice-4b, code-review, pr-237, parity]
summary: Independent second review of PR#237 (feat/scrollback-s4b @ 45e86c5 vs main) against the exact Python behaviour contract from the fable scout doc. Parity verdict clean on all four weighted axes (eviction, resume-from-seq, dropped semantics, raw bytes); 3 Major + 7 Minor quality findings, none a behaviour regression.
status: active
source: fable (scouted s4b; reviewed independently of opus). Diff read 100% line-by-line; contract oracle = tm-t3code-s4b-scout.md §4; 3 finder angles via subagents, candidates verified against first-hand reads
confidence: high
created: 2026-07-07
---

# Review — PR#237 `feat(runtime): port scrollback ring and fanout` @ 45e86c5

Preconditions verified: `git rev-parse HEAD` = 45e86c5 = `origin/feat/scrollback-s4b`,
tree pristine, CI 7/7 pass, local `pnpm --filter @tm/runtime typecheck` clean and
`test` 46/46 pass (observed). No writes to the tree. Citations: file + symbol.

## Parity verdict on the four weighted axes — CLEAN

Verified against my scout contract (`tm-t3code-s4b-scout.md` §4), by direct comparison of
`packages/runtime/src/domain/terminal/ScrollbackRing.ts` +
`src/service/TerminalFanout.ts` with `main:api/src/transport_matters/run_terminal.py`,
independently re-confirmed by a parity-drift finder:

1. **Byte-cap eviction: exact.** Whole-chunk oldest-first eviction (`ScrollbackRing.trim`),
   input tail-slice only when a single append exceeds the cap (strict `>`, so
   `byteLength === maxBytes` stores whole — matches Python), new chunk always survives,
   `totalBytes ≤ maxBytes` post-append, cap default 2 MiB, `truncated` sticky with the
   same three set-points (oversize slice, trim eviction, non-empty append at cap 0).
   Floor updates via shift; the new `floorSeq` getter is additive, not drift.
2. **Resume-from-seq: exact.** `TerminalFanout.attach` = snapshot → `startSeq = nextSeq`
   → register, fully synchronous (no await/microtask — the R2 atomicity hazard from the
   scout doc is avoided); snapshot seqs all < `startSeq`; queue delivers exactly seqs ≥
   `startSeq` in order once. Evicted-floor boundary preserved: no cursor parameter exists
   (matches Python — resume is attach-time), late joiner gets the surviving snapshot +
   sticky `truncated`; the late-join test (`TerminalFanout.test.ts` "gives late
   attachments the surviving scrollback...") pins floor 1 / startSeq 3 exactly per contract.
3. **Dropped/changed semantics: none that break the contract.** Seq advances on every
   append incl. empty data and `maxBytes === 0`; empty chunks broadcast but never stored;
   `queue_maxsize`/`emitted_at` falsy coercions mapped correctly (`0 → default`,
   `undefined → clock()`); per-attachment bounded queues (256 default) with deferred
   slow-close `retryable-overload` after the broadcast loop; `detach` enqueues nothing;
   `closeAttachment` pop-then-best-effort-enqueue, idempotent; duplicate-id silent
   replacement reproduced; `closedReason`/`startSeq` field parity kept. Scout decision
   **R1 resolved as faithful**: the structurally undeliverable overload close item is
   reproduced (and the slow-viewer test pins the drop) — see F1/F2 for where the fix
   belongs when it is taken.
4. **Raw-byte fidelity: preserved, with ownership hardening.** `Uint8Array` end to end,
   byte-length cap arithmetic, copying tail slice (no backing-buffer retention — scout R3
   resolved as copy-on-append). One asymmetry in the copy discipline is finding F2.

The mandated parity pair from the spec (§9) plus most scout trap tests exist and pass:
eviction, late-join resume, oversize live/stored divergence (incl. a `source.fill(0)`
ownership assertion), `maxBytes === 0`, empty append, overflow close, close/detach
idempotency, closeAll, `queueMaxSize: 0` coercion, snapshot immutability across trims.

## Findings — 3 Major, 7 Minor (none a behaviour regression; all verified)

**F1 (Major, design/correctness — `service/TerminalFanout.ts::TerminalQueue.take`)
CONFIRMED. No close/cancel seam on the async take; detached or closed readers can hang
forever holding their closure.** Python consumers escape `queue.get()` via asyncio task
cancellation; the TS `take()` promise is unresolvable once its attachment is
detached/closed (nothing will push; `detach` flushes no waiters; in the overload path the
close item is dropped because the queue is full — faithful, but here the flaw becomes
API). Failure: the 4c WS handler loops `await queue.take()`; peer disconnects → `detach`
→ the in-flight take leaks (or the reader hangs) with no unwind mechanism. 4c must
otherwise race every take against an external signal. Fix belongs in this API now
(a `close()` that rejects/resolves waiters with the `AttachmentClosed`, or an
AbortSignal-taking `take`) — it is also exactly the seam that makes the R1 overload close
deliverable if that recommendation is ever taken.

**F2 (Major, correctness hazard — `domain/terminal/ScrollbackRing.ts::append`)
CONFIRMED aliasing / PLAUSIBLE failure. Stored chunk aliases the broadcast chunk's
mutable `Uint8Array` (and `Date`) in the common path.** When `byteLength ≤ maxBytes`,
`storedData === liveData`, so ring storage, all N attachment queues, and the returned
`TerminalFanoutAppendResult.chunk` share one mutable buffer. Python was immune (`bytes`
immutable). The class otherwise pays for defense everywhere else (input copy on append,
deep-clone on snapshot), so the one aliased edge reads as an oversight, not a policy.
Failure: any 4c-era consumer that mutates, zero-fills, or transfers `chunk.data` after
send silently corrupts scrollback replay for every later attach — invisible until replay.
Fix: pick one immutability convention (see F5) — either store a dedicated copy, or
readonly-by-convention chunks with a single owned copy at the boundary.

**F3 (Major, conventions — `ports.ts::Clock` + `domain/terminal/ScrollbackRing.ts`
import) CONFIRMED. `Clock` re-declares `packages/activity/src/ports.ts::Clock`
verbatim, and its consumption creates the repo's first domain→ports import edge.**
`packages/AGENTS.md`: "The moment a primitive is needed by a second package it belongs in
`@tm/common`, not copied. Duplication across packages is a defect." Repo CLAUDE.md DRY:
"Never re-declare a type that already lives somewhere else." Both barrels now export
`Clock`; a module wiring both contexts must alias, and the copies can drift. Direction:
no `activity/src/domain/*` file imports its ports (`activity/ports.ts` imports FROM
domain); `ScrollbackRing.ts` importing `../../ports` inverts the canonical direction
(`docs/ARCHITECTURE.md`: "`src/domain/` pure domain logic... no IO"). This was scout risk
R5; one move fixes both: promote `Clock` to `@tm/common`, import it in both ports files
(activity edit is a pure re-export). Cheaper in-slice alternative: declare `Clock` in
domain and re-export through ports. Note the clock's ring-side default path is nearly
dead anyway — every production caller passes `emittedAt` — so making `emittedAt`
required deletes the edge entirely.

**F4 (Minor, parity drift — `service/TerminalFanout.ts::attach`) CONFIRMED. Empty-string
`attachmentId` is kept as a key; Python minted a uuid.** Python `attachment_id or
uuid4().hex` regenerates on `""`; TS `input.attachmentId ?? randomUUID()...` registers
under `""`. Combined with silent duplicate replacement, every empty-id attach evicts the
previous viewer, whose reader then hangs (F1). Reachable the moment 4c passes through a
client-supplied id/query param. One-line fix that also adds reuse:
`nonEmptyString(input.attachmentId) ?? ...` (`@tm/common/primitives`).

**F5 (Minor, efficiency — `ScrollbackRing.snapshot` + `append` + `NodePtyAdapter`)
CONFIRMED. The copy discipline is inverted: heavy copies where Python shares, one shared
buffer where a copy matters (F2).** `snapshot()` deep-copies every chunk's bytes + Date
per call — up to a 2 MiB memcpy per viewer attach/reconnect (reconnect-after-overload is
a designed flow); Python does a shallow container copy of immutable chunks. Meanwhile the
hot append path pays two full memcpys per PTY chunk (`NodePtyAdapter.ptyDataToBytes`
already allocates per chunk; `copyBytes` copies again). This plus F2 plus the `copyDate`
cluster is one decision, not three: define chunk immutability once (owned copy at a
single boundary, readonly chunks by convention), then snapshot can go shallow and one of
the two hot-path copies can go.

**F6 (Minor, simplification — `ScrollbackRing.append`) CONFIRMED. `storedData !==
liveData` reference equality is the truncation signal.** It works only because
`tailSlice` happens to allocate; a refactor to `subarray` (the natural "optimization")
silently breaks `truncated` with no test failing on the mechanism. Python sets the flag
explicitly in the oversize branch; do the same.

**F7 (Minor, altitude — `domain/terminal/ScrollbackRing.ts` close-code exports)
CONFIRMED. The ring file owns fanout/run-lifecycle vocabulary it never produces.**
`RUN_ENDED_CLOSE_CODE` / `RUN_START_FAILED_CLOSE_CODE` are `run_manager.py` literals in
Python; the ring closes nothing, and `TerminalFanout` imports its own close vocabulary
from the ring module. Home them beside the fanout (or `domain/terminal/closeCodes.ts`);
`@tm/common/terminalContract.ts` is the wire home if the browser ever parses them.

**F8 (Minor, API surface — `index.ts`) CONFIRMED. Barrel exports the wrong edge of the
surface: `ScrollbackRingOptions` is missing while the `TerminalQueue` class leaks.**
The boundary test (`importGraphBoundary.test.ts`, runtime covered) fails deep imports
closed, so a 4c caller naming the ring's options type is stuck; conversely `TerminalQueue`
(an implementation detail — consumers receive queues via `TerminalAttachment.queue`) is
now a public API commitment. Also speculative surface on a parity-mandated port:
`TerminalCloseCode`'s `(string & {})` open union and `floorSeq` have no consumer;
acceptable if kept deliberately, trim if not.

**F9 (Minor, parity nod — `TerminalFanout.ts::positiveQueueSize`, `queueSizeWithDefault`,
`ScrollbackRing` constructor) CONFIRMED divergence, deliberate-looking, keep with a nod.**
Python treats negative queue maxsize as unbounded (`asyncio.Queue(maxsize=-1)`) and
accepts float/huge `max_bytes`; TS throws `RangeError` on negative/float sizes and
non-safe-integer `maxBytes`, and fanout construction with `attachmentQueueSize: 0` throws
where Python yielded unbounded queues (overload-close unreachable). Strictly stricter and
better — but it flips "never disconnects (unbounded)" into "cannot construct", so the
RunManager re-port (4c+) must not forward Python-style sentinel values. Record; no code
change requested.

**F10 (Minor, in-file DRY — `service/TerminalFanout.ts`) CONFIRMED. The size guard is
written twice and run twice, and `copyDate` is re-implemented inline.** `TerminalQueue`'s
constructor guard duplicates `positiveQueueSize` (near-identical messages), and
fanout-validated sizes are re-validated by the queue constructor;
`attach`'s `connectedAt: new Date(this.clock.now().getTime())` re-implements the ring's
private `copyDate`. One shared guard + one shared (or deleted, per F5) copy helper.

## Findings JSON

```json
[
  {"file": "packages/runtime/src/service/TerminalFanout.ts", "line": 46, "summary": "TerminalQueue.take() has no close/cancel seam; detached or closed readers hang forever and leak", "failure_scenario": "4c WS handler loops `await queue.take()`; peer disconnects -> detach() -> in-flight take() never settles; reader closure, queue, and chunks leak; in the overload path the dropped close item makes the hang the only outcome", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/domain/terminal/ScrollbackRing.ts", "line": 88, "summary": "Stored chunk aliases the broadcast chunk's mutable Uint8Array/Date whenever the append is not oversize", "failure_scenario": "any consumer that mutates/zero-fills/transfers chunk.data after send corrupts ring storage; every later attach replays garbage scrollback, invisible until replay", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/ports.ts", "line": 64, "summary": "Clock re-declares @tm/activity's identical Clock (packages/AGENTS.md: cross-package duplication is a defect) and its use adds the repo's first domain->ports import edge", "failure_scenario": "both barrels export Clock -> alias collisions for dual-context consumers and silent drift; ScrollbackRing.ts imports ../../ports where the canonical direction (activity) is ports->domain", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/service/TerminalFanout.ts", "line": 113, "summary": "Empty-string attachmentId is kept as a map key where Python minted a uuid (?? vs or)", "failure_scenario": "4c passes an empty client-supplied id -> all such viewers collide on key \"\", each attach silently evicts the previous one whose reader then hangs (F1)", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/domain/terminal/ScrollbackRing.ts", "line": 105, "summary": "snapshot() deep-copies up to 2 MiB per viewer attach and the hot path double-copies every PTY chunk (adapter already allocates)", "failure_scenario": "reconnect storm pays a 2 MiB memcpy + per-chunk allocations per attach; every 8 KiB chunk is copied twice (NodePtyAdapter.ptyDataToBytes + copyBytes); one immutability convention removes both", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/domain/terminal/ScrollbackRing.ts", "line": 89, "summary": "truncated flag depends on storedData !== liveData reference inequality instead of the oversize condition", "failure_scenario": "refactoring tailSlice to return a subarray view (or memoizing) silently stops setting truncated; no test fails on the mechanism", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/domain/terminal/ScrollbackRing.ts", "line": 6, "summary": "run-ended/run-start-failed close codes and AttachmentClosed live in the ring file, which never closes anything (Python homes them in run_manager)", "failure_scenario": "cohesion inversion: service imports its own vocabulary from domain's ring module; run-manager port (4c+) churns the domain file to touch lifecycle codes", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/index.ts", "line": 46, "summary": "Barrel omits ScrollbackRingOptions while leaking the TerminalQueue implementation class (plus speculative floorSeq/open-union surface)", "failure_scenario": "consumer naming the ring options type is blocked by the import-graph boundary test and must re-declare it (DRY defect); TerminalQueue's tryPush/take shape becomes a public commitment for free", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/service/TerminalFanout.ts", "line": 168, "summary": "Strictness divergences from Python: negative/zero/float sizes throw where asyncio meant unbounded, non-safe-integer maxBytes rejected", "failure_scenario": "RunManager re-port forwarding Python sentinel values (queue_maxsize=-1 'unbounded', attachment_queue_size=0) flips 'never disconnects' into constructor crash; keep, but do not forward sentinels", "verdict": "CONFIRMED"},
  {"file": "packages/runtime/src/service/TerminalFanout.ts", "line": 20, "summary": "Positive-integer guard written twice and executed twice per attach; copyDate re-implemented inline in attach", "failure_scenario": "same value validated in queueSizeWithDefault/positiveQueueSize and again in the TerminalQueue constructor with near-identical messages; copy-semantics drift between the two files", "verdict": "CONFIRMED"}
]
```

## Notes (not findings)

- R1 (scout) resolved as **faithful**: the undeliverable overload close is reproduced and
  test-pinned; my standing recommendation to make it deliverable now lives inside F1's fix.
- Casing note for 4c: router error codes are snake_case, close codes kebab-case (inherited
  from Python) — decide the wire vocabulary before both freeze into the WS contract.
- `attachments` ReadonlyMap exposes mutable attachment values (writable `closedReason`,
  capable `queue`) — parity with Python's raw dict; the TS type implies more safety than
  it provides. Fold into F8's surface pass if taken.
- Verified preserved (so silence is not ambiguity): seq-on-every-append, cap-0 semantics,
  empty-chunk broadcast-not-store, eviction/floor, truncated set-points, attach atomicity,
  close/detach idempotency and asymmetry, deferred slow-close after broadcast, constants
  (2 MiB / 256 / `retryable-overload`), uuid shape (32 hex), `closeAll` copy iteration.

## Verdict

**review: issue — 0 Blocker / 3 Major / 7 Minor.** Parity to the Python contract is clean
on all four weighted axes; nothing here is a behaviour regression, CI is 7/7, and the
parity suite covers the scout trap list well. The Majors are API-design and conventions
defects in brand-new public surface (cheapest to fix now, before 4c consumes it): F1 the
missing take-cancellation seam, F2 the aliased mutable chunk, F3 the Clock
duplication/boundary inversion.
