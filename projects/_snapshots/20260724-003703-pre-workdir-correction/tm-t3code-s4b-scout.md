---
title: Scout — t3code P1 slice 4b — ScrollbackRing + TerminalFanout re-port (Python → TS)
type: projects
tags: [transport-matters, t3code, p1, slice-4b, scout, runtime, scrollback, fanout, resume-from-seq]
summary: Recon for re-porting the seq'd byte-capped scrollback ring + multi-viewer terminal fanout from api run_terminal.py into packages/runtime (domain=pure ring, service=fanout), preserving resume-from-seq. Reuse Map, Quality Map, verified entry points, the exact behaviour contract, placement plan, ordered build plan with parity suite, risks, build order.
status: active
source: fable scout (Mode 1), baseline main @ f56fe24, clean tree
confidence: high — every contract claim verified by direct read; finder candidates 1-vote verified against the source
created: 2026-07-07
---

# Scout — slice 4b: scrollback ring + fanout parity (multi-viewer resume-from-seq)

Recon only; no source edits. Spec ref: `tm-t3code-p1-spec.md` (§5 row 2, §7, §8 slice 4b,
§9 parity tests). Citations are file + symbol, never line numbers.

**Headline correction to the brief:** `ScrollbackRing` and `TerminalFanout` do NOT live in
`run_manager.py`. They live in `api/src/transport_matters/run_terminal.py`;
`run_manager.py` imports and drives them. Second correction: **there is no client
resume cursor anywhere in the system.** "Resume-from-seq" is an attach-time server-side
contract (atomic snapshot + `start_seq`, queue delivers exactly seqs ≥ `start_seq`), not a
cursor a viewer sends. The browser WS URL carries only `cols`/`rows`
(`www/packages/canvas/src/infrastructure/runtime/internal/terminalSocket.ts::runTerminalSocketUrl`).

---

## 1. Reuse Map

Verdict: **greenfield port.** No TS ring, seq'd chunk, bounded async queue, or fanout
exists anywhere in the repo (searched `packages/*`, `www/packages/*`, `desktop/src`
for ring/circular/scrollback/evict/deque, seq/cursor/monotonic, queue/channel/backpressure/
bounded, fanout/broadcast/subscribers, overload/retryable — no owners).

| Capability | Existing owner | Disposition |
| --- | --- | --- |
| Byte-capped ring | none found (closest: private 64 KiB pre-subscriber holdover buffer in `packages/runtime/src/adapters/NodePtyAdapter.ts::NodePtySession.bufferPendingData` — not seq'd, not snapshottable, not extractable) | build new in `src/domain/` |
| Seq-stamped chunk | none found (adjacent pattern only: session-event SSE seq/gap-resume in `www/packages/canvas/src/infrastructure/stream/useSessionEventStream.ts` — JSON events, client-side, different context; mirror the idea, do not import) | build new |
| Bounded per-subscriber queue | none found (the `capturedRunStore.ts` spawn semaphore is not a data queue) | build new in `src/service/` |
| Multi-listener fanout with per-listener state | none found; canonical in-repo attach/detach idiom to mirror: `packages/activity/src/projections/workspaceActivity.ts::subscribeWorkspaceActivity` | build new |
| Slow-viewer close semantics | none found; `RunErrorFrame` in `packages/common/src/terminalContract.ts` has no `retryable` field | build new (domain close type) |
| Clock injection | `packages/activity/src/ports.ts::Clock` (`{ now(): Date }`) — the repo's only clock seam; spec §7 already plans `Clock` in runtime `ports.ts` | reuse the shape; see §7 risk R5 for the promote-to-common question |
| Terminal wire frames | `packages/common/src/terminalContract.ts` (`RunTerminalReadyFrame` already carries `scrollback.replayedBytes` + `truncated`) | reuse at 4c; 4b emits no frames |
| Teardown sweep helper | `packages/common/src/closeAll.ts::closeAll` | optional, fits shutdown sweep only (per-attachment close-item semantics are richer) |
| Safe wire coercions | `packages/common/src/primitives.ts` | reuse at 4c if a cursor param ever lands |

Target dirs: `packages/runtime/src/domain/` and `src/service/` **do not exist yet**
(current: `index.ts`, `ports.ts`, `adapters/`, `server/`). `@tm/activity` is the canonical
shape reference (`packages/AGENTS.md`): pure vocabulary + arithmetic in `domain/`
(cf. `usage.ts`, `runActivityContext.ts`), stateful orchestration in `service/`
(cf. `runActor.ts`, `activityIngestion.ts`). The 4b seam in the existing stub:
`packages/runtime/src/server/runtimeRouter.ts` hardcodes
`scrollback: { replayedBytes: 0, truncated: false }` and echoes WS input.

## 2. Quality Map (existing area)

Measurements: `run_manager.py` 682 LOC (**18 under the 700 hard limit** — any 4b-adjacent
Python edit of 18+ lines trips the refactor-first rule; 4b should add zero Python lines),
`run_routes.py` 627, `terminal_bridge.py` 320, `run_terminal.py` 213, `run_models.py` 207.
No function near 150 LOC. TS side: nothing near limits.

Duplication (Python, all dies at slice 4e — record, do not groom):
- `PTY_READ_CHUNK_SIZE = 8192` declared in both `pty_session.py` and `terminal_bridge.py`.
- Terminal size defaults declared in both `pty_session.py` (`DEFAULT_TERMINAL_COLS/ROWS`) and `terminal_bridge.py` (`DEFAULT_COLS/ROWS`); TS single home already exists (`terminalContract.ts`).
- PTY-EOF idiom (`os.read` + `errno in {EIO, EBADF}`) duplicated in `terminal_bridge.py::bridge_websocket_to_pty.read_ready` and `run_manager.py::RunManager._handle_pty_readable`.
- `asyncio.wait`/cancel/gather bridge scaffold duplicated between `terminal_bridge.py::bridge_websocket_to_pty` and `run_routes.py::bridge_attached_run_terminal`.
- `run_terminal.py::TerminalQueueItem` alias exists but `run_routes.py::_send_attachment_output` re-spells the union. TS port: one exported name.

Dead/unread surface (port-relevant — see §4 for what the mandate keeps anyway):
- `AttachedTerminal.start_seq`: set, never read by any production caller or test.
- `TerminalAttachment.closed_reason`: only read by a `test_run_manager_lifecycle.py` assertion; the same info travels in the queued `AttachmentClosed`.
- `AttachmentClosed.retryable`: no production reader — `run_routes.py::_send_attachment_output` string-matches `SLOW_VIEWER_CLOSE_CODE` instead. TS port should key on `retryable`/a typed code union, not a magic string.
- `PtyChunk.emitted_at`: constructed, never consumed downstream.
- `attach(attachment_id=…, queue_maxsize=…)` overrides: test-only callers.
- `RunManager._close_all_attachments`: one-line passthrough.
- `terminal_bridge.py` re-exports `_WinsizeSetter` (aliased private name in `__all__`), shim residue, no importer.

Efficiency notes (shape guidance for the TS port):
- Double `PtyChunk` allocation per read in the common path of `ScrollbackRing.append` (live + identical stored chunk) — TS: allocate once when stored bytes === input bytes.
- `tuple(self.attachments.values())` copy per chunk in `TerminalFanout.append` — unnecessary (closes are already deferred past the loop); TS: iterate `Map.values()` live, keep the deferred-close list.
- `run_terminal_ready_frame` O(n)-sums snapshot bytes per attach — TS `attach` should capture `totalBytes` at snapshot time (the ready frame needs `replayedBytes` anyway).
- Keep: `_total_bytes` O(1) counter (recompute would be O(chunks) per `ManagedRun.view`); keep: `snapshot()` copy (replay awaits between sends while `_handle_pty_readable` can trim the deque — same hazard in TS if replay yields).

Boundary: `ScrollbackRing` is already pure (clock default is its only impurity);
`TerminalFanout` owns `asyncio.Queue` — the impure half. Close-code vocabulary is scattered
(`"retryable-overload"` in run_terminal.py; `"run-start-failed"`, `"run-ended"` inline in
run_manager.py; wire `"attachment_overloaded"` inline in run_routes.py) — TS: one exported
close-code union next to the fanout.

**Grooming recommendation: none.** Every Python finding lives in code slated for deletion
at 4e; nothing blocks the port. Spend the findings on the TS design.

## 3. Verified entry points (claimed → actual)

| Claimed (brief/spec) | Actual (verified) |
| --- | --- |
| `ScrollbackRing`/`TerminalFanout` in `run_manager.py` | `api/src/transport_matters/run_terminal.py` (all of: `PtyChunk`, `AttachmentClosed`, `TerminalQueueItem`, `ScrollbackRing`, `TerminalAttachment`, `AttachedTerminal`, `TerminalFanout`, `DEFAULT_SCROLLBACK_BYTES`, `DEFAULT_ATTACHMENT_QUEUE_SIZE`, `SLOW_VIEWER_CLOSE_CODE`) |
| "current Python run-terminal transport" | producers/consumers: `run_manager.py::RunManager._handle_pty_readable` (append), `::attach/_detach/_close_all_attachments`; `api/v1/run_routes.py::run_terminal_socket`, `::bridge_attached_run_terminal`, `::_send_attachment_output`, `::run_terminal_ready_frame`; view fields via `run_models.py::ManagedRun.view`. Full importer set: `run_manager.py`, `run_models.py` (TYPE_CHECKING only), `run_routes.py`, plus tests. `api/v1/run_proxy.py::run_terminal` is a name coincidence (byte-transparent WS forwarder, no import) |
| Client resume-from-seq cursor | does not exist; WS query is `cols`/`rows` only (`terminalSocket.ts::runTerminalSocketUrl`); ready/scrollback-end frames are ignored as informational by `CapturedRunPane.tsx::AttachedRunTerminal` |
| `packages/runtime/src/domain` + `src/service` | do not exist yet; create per `docs/ARCHITECTURE.md` "Canonical context package" (spec §7 names `domain/terminal/ScrollbackRing.ts`, `service/TerminalFanout.ts`) |
| Parity gates | root `justfile`: `just check` + `just test` (verbatim; both already include `@tm/runtime` typecheck/test) |
| Existing direct unit tests of ring/fanout | **none** — coverage is integration-only via `test_run_manager.py`, `test_run_manager_lifecycle.py`, `api/v1/test_run_routes*.py` (inventory in §6) |

## 4. The behaviour contract to preserve (the crux)

Source of truth: `run_terminal.py`, read line-by-line; every claim below verified directly.
Constants: `DEFAULT_SCROLLBACK_BYTES = 2 * 1024 * 1024` (2 MiB),
`DEFAULT_ATTACHMENT_QUEUE_SIZE = 256`, `SLOW_VIEWER_CLOSE_CODE = "retryable-overload"`.
`RunManager` passes both through per run and feeds `append` from 8 KiB PTY reads
(`pty_session.py::PTY_READ_CHUNK_SIZE`).

### 4a. ScrollbackRing (→ `domain/terminal/ScrollbackRing.ts`, pure)

State: FIFO of stored chunks, `total_bytes`, `next_seq` (from 0), sticky `truncated` flag.
Constructor: injected clock; `max_bytes < 0` → error; `max_bytes == 0` allowed
(store-nothing mode).

`append(data, emitted_at?)` → returns the **live chunk**:
1. `emitted = emitted_at or clock()`; `seq = next_seq`; `next_seq += 1`. **Seq advances on
   every append** — including empty data and the `max_bytes == 0` path.
2. Live chunk = `PtyChunk(seq, data, emitted)` with the **full, unsliced** data.
3. `max_bytes == 0`: nothing stored; `truncated = true` iff data non-empty; return live chunk.
4. `len(data) > max_bytes`: `truncated = true`; stored data = **tail slice**
   `data[-max_bytes:]`. Else stored data = data.
5. If stored data non-empty: store `PtyChunk(same seq, stored_data, emitted)`, add to
   `total_bytes`, then trim: **evict whole chunks oldest-first** while
   `total_bytes > max_bytes`, setting `truncated = true` per eviction. No partial slicing of
   the oldest chunk. The just-stored chunk always survives (it is ≤ max_bytes by step 4).
   **Empty data is never stored** but still consumes a seq (snapshot seq gap).

`snapshot()` → immutable copy of stored chunks, oldest→newest.
Properties: `max_bytes`, `total_bytes`, `next_seq`, `truncated`.

Invariants (all port-hazards if broken):
- I1: seq monotonic from 0; no reuse, no reset; advances on every append.
- I2: `total_bytes ≤ max_bytes` after every append; permanently 0 when `max_bytes == 0`.
- I3: `truncated` is sticky, set by: oversize tail-slice, any trim eviction, any non-empty append at `max_bytes == 0`. Never cleared.
- I4: **same seq, two payloads**: on an oversize append the stored chunk and the broadcast live chunk share a seq but differ in bytes. `replayedBytes` (ready frame) counts stored bytes; live viewers saw the full bytes. A porter who single-sources the chunk will either break the cap or truncate live output.
- I5: snapshot never contains an empty chunk; queues can receive one (see 4b).

### 4b. TerminalFanout (→ `service/TerminalFanout.ts`)

State: the ring + insertion-ordered map `attachment_id → TerminalAttachment{id, queue, cols, rows, connected_at, closed_reason}`.

`attach(cols, rows, attachment_id?, queue_maxsize?)` → `AttachedTerminal{attachment, scrollback, start_seq}`:
- Take `snapshot()`, read `start_seq = ring.next_seq`, create the attachment
  (id = supplied or generated; bounded queue, maxsize = supplied or default — note Python's
  `or`: **0 coerces to the default**), register it — **all synchronously, no await**. This
  atomicity is the entire resume guarantee (see 4c).
- Duplicate `attachment_id` **silently replaces** the prior attachment; the old queue is
  orphaned with no close item (its reader hangs until its socket dies). Latent hazard, no
  production path hits it (routes always generate ids).

`append(data, emitted_at)` → `(live_chunk, overloaded_ids)`:
1. `ring.append`, then `put_nowait(live_chunk)` to **every** attachment in registration
   order (iterated over a copy). Broadcast is unconditional — empty chunks are broadcast
   even though never stored (I5).
2. Queue-full attachments are collected, then closed **after** the loop with
   code `retryable-overload`, `retryable = true`.
3. Caller usage: `run_manager.py::_handle_pty_readable` discards the live chunk
   (`_, closed_attachment_ids`) and sets `viewerless_since` **only when the slow-closes
   removed the last viewer and state is RUNNING**.

`close_attachment(id, code, retryable, message)` → bool: pop from map (absent → false,
idempotent — `RunManager.attach`'s rollback relies on this), set `closed_reason`, then
best-effort `put_nowait(AttachmentClosed{code, retryable, message})` suppressing queue-full.
`close_all(code, retryable, message)`: close every attachment (iterated over a copy).
Manager close codes: `"run-start-failed"` (retryable false), `"run-ended"` (retryable false).
`detach(id)` → bool: pop only, **never enqueues a close item** (safe today only because the
WS bridge is itself the detacher, in its `finally`).

**Confirmed latent defect (the port's one deliberate divergence candidate):** in the
overload path the close item is put on the same still-full queue within the same
synchronous callback — no reader can drain in between — so the suppress **always** fires
and the slow viewer never receives its close. Downstream,
`run_routes.py::_send_attachment_output`'s `attachment_overloaded` JSON branch is
unreachable via this path; the popped attachment's reader drains the backlog then blocks
forever on an orphaned queue (later `close_all` cannot reach it). Wire effect today: a slow
viewer's terminal freezes with no error until the client disconnects.
`test_run_manager_lifecycle.py::test_slow_viewer_is_closed_without_stopping_run` implicitly
documents the drop (it asserts the queued item is still the data chunk).

### 4c. Resume-from-seq — exact semantics incl. the evicted floor

- There is **no cursor parameter**. Resume = attach: the viewer receives
  `scrollback` (backlog snapshot) + `start_seq`, and the queue then delivers **exactly the
  seqs ≥ start_seq, in order, exactly once**. Snapshot seqs are all < `start_seq`.
- The guarantee holds **only** because attach (snapshot → read next_seq → register) and
  append are both synchronous and atomic on the event loop. Any await/microtask between
  snapshot and registration in TS opens a lost-chunk window (or, ordered the other way, a
  duplicate-delivery window). **This is the single most fragile invariant in the port.**
- Evicted floor: the ring floor is the seq of the oldest stored chunk. A late attach never
  reaches under it — it simply receives the surviving snapshot plus `truncated = true`
  (surfaced at the wire as `scrollback.replayedBytes` + `truncated` in
  `run_routes.py::run_terminal_ready_frame`, contract type
  `terminalContract.ts::RunTerminalScrollback`). There is no under-floor error path because
  there is no cursor to be under the floor. A future client cursor (4c+ work, additive)
  would filter the snapshot to seqs ≥ cursor and fall back to full-snapshot+truncated when
  cursor < floor — design for that without building it.
- Replay ordering downstream (context for 4c, not 4b scope):
  `bridge_attached_run_terminal` sends ready frame → snapshot bytes → `scrollback-end`
  → then starts the queue reader. Chunks appended during replay wait in the already
  registered queue; nothing is dropped or duplicated, but a queue that fills **during**
  replay slow-closes the attachment before its reader ever starts.
- `start_seq` has no production reader today (Quality Map), but it is the observable half
  of the resume contract and the spec mandates preserving resume-from-seq
  (spec §5 "re-port, preserve behaviour"): **port it**.

### 4d. Bytes semantics

Data is raw PTY bytes (`os.read`) end to end; slice 4a made the TS adapter byte-faithful
(`ports.ts::PtySession.onData` delivers `Uint8Array`). The TS ring must store
`Uint8Array`, cap by `byteLength`, tail-slice by bytes. Two TS-specific traps with no
Python equivalent: (a) the ring must **own** its bytes — copy on append if the source
buffer can be reused/pooled by the producer (node-pty Buffers), and (b) a tail slice must
not retain the full backing buffer (`subarray` is a view; use a copying slice for stored
oversize chunks). Seqs fit safely in `number`.

## 5. Placement plan

Per `docs/ARCHITECTURE.md` "Canonical context package" + spec §7:

- `packages/runtime/src/domain/terminal/ScrollbackRing.ts` — pure: the ring + `PtyChunk` +
  the close-code vocabulary (`AttachmentClosed`, a typed close-code union incl.
  `"retryable-overload"`, `"run-ended"`, `"run-start-failed"`). No IO, no timers; clock
  injected (`Clock { now(): Date }`, the `activity/src/ports.ts::Clock` shape; spec §7
  already lists `Clock` in runtime `ports.ts`). Colocated test.
- `packages/runtime/src/service/TerminalFanout.ts` — the fanout + `TerminalAttachment` +
  `AttachedTerminal` + the bounded queue. The queue primitive is runtime-local until a
  second package needs it (`packages/AGENTS.md` promotion rule). Colocated test.
- Export both through `packages/runtime/src/index.ts` (single import surface; the
  import-graph boundary test fails closed on deep imports).
- Wire frames stay in `@tm/common/terminalContract.ts`; 4b emits no frames. The server stub
  (`runtimeRouter.ts`) is untouched until 4c.
- Queue shape recommendation: a minimal bounded queue with synchronous
  `tryPush(item): boolean` and async `take(): Promise<item>` (the `asyncio.Queue` analogue
  4c's WS pump will need). Alternative (hygiene finding): a fully synchronous bounded
  buffer with server-owned delivery — defensible, but the async take matches the Python
  consumption shape (`_send_attachment_output`) and keeps 4c mechanical. Builder's call;
  parity tests must pass either way since they assert observable queue contents.

## 6. Plan (ordered steps + parity suite)

Baseline main @ f56fe24. Gates per step: `just check` + `just test` (verbatim — both
already cover `@tm/runtime`). No Python changes anywhere in this slice.

1. `domain/terminal/ScrollbackRing.ts`: chunk type, close vocabulary, ring exactly per §4a
   (single-allocation when stored bytes === input bytes; capture-at-snapshot `totalBytes`
   for the future ready frame).
2. `service/` bounded queue + `TerminalFanout.ts` exactly per §4b, with the attach
   atomicity of §4c (no await anywhere in attach/append).
3. Barrel exports in `src/index.ts`.
4. Parity suite (Vitest, colocated). The spec-mandated pair first:
   - **byte-cap eviction**: fill past cap → oldest whole chunks evicted, `totalBytes ≤ cap`,
     `truncated` sticky, newest chunk always survives;
   - **two-attachment late-join resume-from-seq**: attach A, append k chunks, attach B →
     B's snapshot = the surviving chunks (all seqs < B.startSeq), B's queue receives exactly
     seqs ≥ B.startSeq in order exactly once, A saw everything live; append during a
     simulated replay window is queue-delivered, never lost/duplicated.
   Then the zero-coverage behaviours the Python suite never pinned (each is a
   port-divergence trap): oversize append tail-slice + live/stored divergence (I4);
   `maxBytes == 0` (seq still advances, truncated on non-empty, snapshot stays empty);
   empty append (seq consumed, not stored, still broadcast); queue overflow → attachment
   removed with `retryable-overload`, remaining viewers and ring unaffected, close-item
   delivery per the §7 R1 decision; `closeAttachment`/`detach` idempotency (double-close
   no-op); detach enqueues nothing; `closeAll` mid-iteration safety; truncated stickiness;
   snapshot immutability while the ring trims.
5. Mirror-check the Python integration expectations that touch ring state so 4c inherits
   them cleanly: replayed-bytes accounting (`test_run_routes.py::test_post_get_attach_detach_and_terminate`),
   scrollback-then-live ordering (`test_run_manager_lifecycle.py::test_reattach_receives_scrollback_then_live_output`),
   attach-before-PTY-start (`test_run_manager.py::test_start_on_attach_registers_viewer_before_pty_start`),
   headless drain (`test_run_manager.py::test_headless_run_drains_pty_output_into_scrollback`),
   slow-viewer close (`test_run_manager_lifecycle.py::test_slow_viewer_is_closed_without_stopping_run`).

## 7. Open risks / decisions

- **R1 (decision, recommendation attached): faithful bug vs fix — the undeliverable
  slow-viewer close (§4b).** Byte-for-byte parity means reproducing a zombie: the slow
  viewer never learns it was closed. Recommendation: preserve every observable ring/fanout
  behaviour (attachment removed, backlog intact, other viewers unaffected, code
  `retryable-overload`) but make the close signal **always deliverable** (out-of-band
  per-attachment closed state alongside the in-band item, or reserve delivery for the close
  item). This unblocks 4c from inheriting the frozen-tab defect and changes no wire
  behaviour in 4b (nothing is served). Builder brief should lock this.
- **R2: attach/append atomicity under TS async idioms** — the resume guarantee dies if
  attach or append ever awaits between snapshot/registration or ring-append/broadcast.
  Keep both fully synchronous; the parity suite's late-join test must be written to fail on
  an inserted await (assert no gap and no duplicate around the attach boundary).
- **R3: buffer aliasing/retention** (§4d) — copy-on-append vs trusting the 4a adapter's
  buffers; tail slices must not pin 2 MiB backing buffers. Needs an explicit decision in
  the builder brief; default safe choice is copy-on-append.
- **R4: Python `or` vs TS `??`** — `queue_maxsize or default` and `emitted_at or clock()`
  coerce falsy (0) to the default. Decide the TS meaning of `queueMaxsize: 0` (recommend:
  reject or treat as default explicitly; never accidentally unbounded).
- **R5: `Clock` home** — `activity/src/ports.ts::Clock` + an identical runtime `Clock`
  = the `packages/AGENTS.md` "second consumer ⇒ @tm/common" rule firing on a two-line
  interface. Promoting touches `@tm/activity` (blast radius beyond the slice). Recommend:
  promote to `@tm/common` in this PR only if the activity change stays a pure re-export;
  otherwise runtime-local now, promotion as an immediate follow-up. Orchestrator's call.
- **R6: `emitted_at` consumers** — none exist today; the spec's contract preservation says
  keep the field (cheap, and 4c's future frames may want it). Keep, do not extend.
- **R7 (out of scope, note for 4c):** non-slow closes (`run-ended`) reach the wire as a
  silent normal WS close today (no JSON) — a 4c parity fact, not a 4b concern; and
  `run_proxy.py`'s WS forwarder must stay close-code-transparent through the cutover.

## 8. Recommended build order

1 → 2 → 3 → 4 in §6 as one PR (pure logic + tests, no serving, no Python). Write the
spec-mandated parity pair (byte-cap eviction, late-join resume) test-first against §4's
contract, then the trap tests, then step 5's mirror-check. Small blast radius (new files +
barrel only); orchestrator-weight verification per the review-weight rule, no adversarial
loop needed. **Build-ready** once R1 (fix vs faithful) and R3 (copy policy) are locked in
the builder brief — both have recommendations above.
