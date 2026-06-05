# Scout S4: client-side login detection (never-reaches-the-wire auth_required)

Read-only scout against main (branch `fix/anthropic-usage-limit-discriminator`
= main + the merged-pending PR #302 429 fix; nothing here depends on that
delta). Goal: reuse map for the LEAN slice, detect a harness's client-side
"Not logged in" in PTY output and mint the SAME `auth_required` needs_you S1
produces, with zero parallel signal machinery.

**Recommendation up front: lean claude-first.** Claude is the only harness
with a real, confirmed client-side pattern. The Node seam already runs a
per-harness stateful output scanner at the exact pump we need, the Node to
Python bridge channel already exists (capture RPC), and the Python condition
plane needs only one new public entry method beside an existing non-HTTP
precedent. Codex and grok interactive logged-out output exists in no capture
we own and must not be guessed (two guessed-pattern burns this cycle: the
nonexistent `anthropic-ratelimit-unified-status` header, and the codex
probe stdout/stderr misread). Defer them exactly like the usage-limit
deferrals, keyed on real captures.

## 1. Capture pump owner

- `packages/runtime/src/service/RunManager.ts :: RunManager.register` installs
  the single `session.onData` pump per managed run. It already calls
  `run.inputAdapter.observe(data)` (a per-harness matcher) on every chunk
  BEFORE appending to the emulator and fanout, and it does so unconditionally
  at registration, so visible AND hidden panes are covered (attachment state
  only affects the fanout consumers, not the pump).
- The per-harness matcher precedent is exact:
  `packages/runtime/src/service/HarnessPromptInputAdapter.ts ::
  HarnessPromptInputAdapter.observe` wraps
  `packages/runtime/src/domain/tuiReadiness.ts :: TuiReadinessScanner`, a
  stateful, carry-buffered, harness-parameterized scanner fed every chunk
  until it latches (used today for composer readiness via OSC 0 titles).
  A login detector is a sibling domain scanner with the same shape: latch
  once, carry across chunk boundaries, per-harness pattern table.
- Chunk-safe text matching helpers already exist but are module-private:
  `HarnessPromptInputAdapter.ts :: compactTerminalText` /
  `visibleTerminalText` strip ANSI control sequences before matching. The
  claude login line will arrive interleaved with escapes, so the detector
  must match compacted visible text; promoting these helpers into
  `packages/runtime/src/domain/` (beside `tuiReadiness.ts`) is the DRY move.
- Event fan-out precedent from the same pump: `RunManager.register` raises
  readiness events to `readinessListeners`
  (`RunManager.onReadinessChange`), consumed via
  `packages/gateway/src/main.ts` (readiness wired into the activity deps).
  A login detection event can ride the identical listener shape.

## 2. Needs_you minting reuse (the key)

S1's wire chain, end to end, with the one seam a PTY detection plugs into:

- Mint: `api/src/transport_matters/live_status_observer.py ::
  LiveStatusObserver.observe_response_status` classifies via
  `provider_conditions.py :: classify_provider_response_status` and calls the
  private `LiveStatusObserver._offer_condition`, which writes the sticky
  `run_live_status` row through `SessionWriter.submit_run_live_status`.
- **Non-HTTP minting precedent already exists**:
  `live_status_observer.py :: LiveStatusObserver.observe_codex_handshake_rejection`
  is a public method that mints a condition with no HTTP flow tap, taking
  `run_id` plus an explicit generation identity (there, the persisted
  handshake exchange id). A PTY-triggered detection calls a sibling public
  method (e.g. `observe_harness_client_condition(run_id, generation,
  condition)`) that delegates to the same `_offer_condition`. Module privacy
  rules require the public wrapper; nothing else changes. `track_role=None`
  as in the handshake path.
- Generation identity is the one design point: a client-side detection has
  no wire exchange. It needs a stable synthetic generation (e.g. a detection
  event UUID minted once per latch). That id flows into the row and into the
  Node activity assert id (`packages/activity/src/service/runActivityEvents.ts`
  builds `live:{runId}:{generation}:{seq}` for `provider-condition` events),
  so dedupe/reassert semantics work unchanged.
- Downstream is then untouched and identical to a wire 401:
  - Node activity: `runActivityEvents.ts` maps the row kind to a
    `provider-condition` event; `packages/activity/src/domain/runActivityMachine.ts`
    drives the needs_you tier; `packages/contract/src/activity/wire.ts ::
    needsYouForStatus` yields `{kind: "auth_required"}`.
  - Pane pill: `www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`
    renders from the same activity status.
  - Launcher watch / wait_for_reply:
    `api/src/transport_matters/controlplane/delivery_wait.py ::
    _provider_condition` reads the target's needs_you kind and uses it as the
    resolution reason for deliveries, including deliveries that never bound a
    prompt cursor ("rejected before it existed" is literally the documented
    case in that module). A PTY-minted condition resolves a hung first
    delivery the same way a wire 401 does.
- Bridge (Node detection to Python mint): the loopback channel exists today.
  `packages/runtime/src/adapters/CaptureRpcClient.ts :: CaptureRpcClient`
  already calls Python for `prepareCapture` / `releaseCapture` /
  `captureHealth` / prompt-delivery arming, served by
  `api/src/transport_matters/capture_rpc.py`. The lean slice adds ONE RPC
  (e.g. `reportClientCondition(runId, condition, detectionId)`) on this
  existing port pair; no new transport, no parallel signal path. This is the
  only genuinely new seam in the slice.

## 3. Episode / clear-on-success parity

Confirmed identical by construction, because parity lives below the minting
seam:

- Sticky and dedupe: `LiveStatusObserver._offer_condition` keys the open
  episode on the condition alone. If the wire 401 already minted
  `auth_required`, a subsequent PTY detection of the same condition emits
  nothing (and vice versa), so double-detection is inherently safe.
- Clear and rearm: `LiveStatusObserver._offer` pops the episode only on a
  genuine terminal (`fact.terminal`, `provider_event != "flow_abort"`) from
  a DIFFERENT generation. After the user runs `/login` and sends a message,
  that successful wire turn is exactly such a terminal: the PTY-minted
  condition (synthetic generation) clears and the classifier rearms,
  byte-for-byte the wire-401 lifecycle. No PTY-side clear logic is needed or
  wanted; do not build one.

## 4. Per-harness patterns: real vs needs-capture

| Harness | Client-side logged-out evidence | Status |
| --- | --- | --- |
| claude | `Not logged in · Please run /login` (0 tokens, 0s), confirmed from a live run this cycle | REAL, buildable now |
| codex | none for the interactive TUI | NEEDS REAL CAPTURE |
| grok | none at all | NEEDS REAL CAPTURE |

- claude: the confirmed line is the detector pattern. Match on compacted
  visible text (the middot arrives inside a styled TUI frame). Note the
  certified structured pre-launch probe also exists,
  `api/src/transport_matters/harnesses/probes/claude.py ::
  AUTHENTICATION_PROBE` (`claude auth status --json`, `loggedIn` field), but
  that is S2 launch-time enablement evidence, not run-time detection; it is
  corroboration, not the signal.
- codex: the ONLY real capture we own is the non-interactive CLI probe,
  `harnesses/probes/codex.py` (`codex login status`, `Not logged in` on
  stderr, exit 1, built from a real binary capture after the stdout/stderr
  misread). That certifies the subcommand, NOT what the interactive TUI
  prints when a captured run is logged out. No tier-1 artifact helps: tier-1
  stores wire bytes and transcripts, never PTY output, and the scrollback
  ring is in-memory only. Defer codex behind a real logged-out TUI capture
  from Stuart's authenticated environment (log out, launch captured codex,
  save the pane output).
- grok: `harnesses/probes/grok.py` is an explicit r0 stub documenting the
  exit-code trap (`grok models` exits 0 in both auth states, parser pending
  S2h). Nothing certified anywhere, interactive or otherwise. Same deferral,
  same capture recipe.

## 5. Relation to S2d.1 startup_prompt_rejected

Distinct planes, by explicit design, with a knife-edge worth stating:

- `api/src/transport_matters/harnesses/drift_emitter.py ::
  observe_prompt_receipt` mints `startup_prompt_rejected` only when a
  PromptReceipt FAILS with a reason in
  `controlplane/prompt_models.py :: HARNESS_REJECTION_PROMPT_REASONS`
  (currently the unminted `harness_rejected_prompt`; the classifier is a
  documented gap). That is launch-contract drift evidence: the harness
  refused the actuation.
- The logged-out case is the opposite shape: the PTY ACCEPTS the prompt
  (`HarnessPromptInputAdapter.submitPrompt` resolves `accepted_by_pty`),
  claude answers locally with the login demand, and no wire turn ever forms.
  The delivery hangs open with no rejection receipt, so S2d.1 machinery
  never fires. `prompt_models.py` states the vocabularies are deliberately
  disjoint (provider conditions must never feed the drift plane).
- Overlap verdict: DISTINCT. S4 fills precisely the gap S2d.1 cannot see
  (accepted actuation, client-side refusal, silent wire). The two can
  coexist on one incident without contention because they key on different
  receipts and write to different planes.

## Scope recommendation

**Lean claude-first.** Slice contents: one domain scanner in
`packages/runtime/src/domain/` (claude pattern only, table extensible),
observe hook beside the readiness call in `RunManager.register`, one new
capture RPC on the existing `CaptureRpcClient`/`capture_rpc.py` port pair,
one public `LiveStatusObserver` method delegating to `_offer_condition` with
a synthetic detection generation. Everything downstream (row, activity
event, pill, launcher needs_you, episode clear) is untouched S1 machinery.
Full S4 (codex + grok matchers) adds only guessed patterns today; gate each
harness behind a real logged-out TUI capture, mirroring the codex
limit-frame and anthropic real-cap deferrals. Needed from Stuart when ready:
logged-out interactive launches of codex and grok under capture, pane text
saved.
