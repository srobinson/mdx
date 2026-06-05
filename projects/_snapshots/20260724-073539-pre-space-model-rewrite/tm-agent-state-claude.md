# TM agent-state derivation — ideation (claude/Fable lean)

Warroom ideation, 2026-07-10. Scope: (a) canonical state model, (b) 3-plane
source-of-truth mapping, (c) PTY-capture probe. Divergent options, not a
converged spec.

## 0. What exists today (probe-backed baseline)

The live derivation is **transcript-only**. `@tm/activity` folds Postgres
transcript rows into an XState machine:

- Vocabulary: `activityStatuses` in `packages/contract/src/activity/wire.ts`
  (symbol `activityStatuses`): `starting | thinking | running-tools |
  needs-you | stalled | exited`. Flat, no sub-types.
- Machine: `packages/activity/src/domain/runActivityMachine.ts` +
  `runActivityContext.ts`. Event alphabet: `run.started/exited` (lifecycle),
  `record.turn_open / tool_use / tool_result / tool_error /
  assistant_turn_ended / question_asked / transcript_error`, `usage.recorded`.
- Harness parsers: `packages/activity/src/adapters/transcriptRecords.ts`.
  Claude: `AskUserQuestion` tool_use → question-asked; `stop_reason ===
  "end_turn"` → turn-end. Codex: `request_user_input` function_call →
  question-asked; `task_started/task_complete` event_msgs → turn open/end.
- Stall: 10-minute silence timeout (`DEFAULT_STALL_TIMEOUT_MS`), plus
  transcript-error.

Why it is often wrong, concretely:

1. **Permission gate invisibility.** Claude Code writes the assistant
   `tool_use` row to the JSONL *before* the local permission prompt. The
   machine sees a pending toolCallId and reports `running-tools` while the
   agent is actually blocked on "Do you want to proceed? 1. Yes … 3. No".
   Timing cannot disambiguate a slow tool from a blocked gate. The gate never
   touches wire or transcript until answered.
2. **Plan-mode approval** is a tool call (`ExitPlanMode`) on wire/transcript,
   but the approve/reject pause renders only in the TUI. Same blind spot.
3. **end_turn conflation.** `turn-end → needs-you` treats "finished cleanly,
   idle" the same as "explicitly asked you something". These are different
   urgencies and should be different states.
4. **Transcript lag.** JSONL rows land after streaming; wire knows a turn
   started/ended first.

## (a) Canonical state model

### The vocabulary

Two axes, not one flat enum. Axis 1 is the **phase** (mutually exclusive
lifecycle); axis 2 is the **attention reason** (why a human is needed), which
only exists when phase is a waiting phase.

Phases:

- `starting` — launch accepted, first turn not yet open.
- `working.thinking` — a wire request is in flight / response streaming.
- `working.running-tools` — turn continuing, tool executing, no gate pending.
- `gated` — the harness is **blocked on a local pause-gate** (sub-typed below).
- `asked` — the agent **explicitly asked the user** via a model-level ask
  (AskUserQuestion / request_user_input) and awaits an answer.
- `idle` — turn ended cleanly; nothing asked; awaiting the next prompt. Today
  this is mislabeled `needs-you`.
- `held` — TM's own breakpoint holds the next outbound request. TM is the
  first-party source here; no inference at all.
- `exited` — process gone, with `exit_reason`.
- `unknown/stale` — honesty state: signals conflict or all planes silent past
  a liveness horizon (replaces the crude 10-min `stalled` where possible; see
  liveness heartbeat in (b)).

`needs_you` becomes a **derived flag**, not a state: `needs_you = phase in
{gated, asked}` (and arguably `held`). `idle` is attention-optional; the UI
can badge it differently. This preserves the wire enum as a projection for
compat while fixing the conflation.

Gate sub-types (the `gated.reason`):

- `permission` — tool approval prompt (per-tool, "don't ask again" variants).
- `plan-review` — plan-mode approval gate.
- `question` — could fold `asked` in here as a third reason; kept separate
  above because its source of truth differs (model-level vs local-render).
- `auth` — login/token-expiry prompts (real occurrence: `/login` gates,
  OAuth re-auth). Renders only in PTY.
- `unknown-gate` — the menu-shaped-prompt detector fired but no signature
  matched. First-class citizen: this is the drift alarm, not an error.

### Shape options (diverge deliberately)

- **Option A — flat enum extension.** Add `needs-you:question | permission |
  plan-review` as statuses. Cheapest; breaks `status_counts` consumers;
  keeps conflation pressure (every new gate mints a status).
- **Option B — status + nullable `attention` field.** Wire stays
  `ActivityStatus`, plus `attention: {reason, since_ts} | null`. Backwards
  compatible, one added wire field, rollups unchanged. Boring, safe.
- **Option C — structured gate object (bold).** `gate: {kind, prompt_text,
  options: [{key, label}], detected_at, source_plane, confidence}`. The PTY
  parser already has to read the rendered menu to classify it, so carrying
  the payload is nearly free — and it makes the state **actionable**: the
  desktop can render the actual question with its options remotely, and
  answering writes the keystroke to the PTY (`RunManager.write` exists
  today). Turns state derivation from a dashboard into a remote-control
  surface. Risk: prompt shape drift now affects payload fidelity, not just
  classification; needs the confidence field and a degrade-to-Option-B path.

Recommendation to synthesize against: B as the wire contract now, with C's
gate payload as an optional extension block, so the vocabulary does not need
a second migration when gate actuation lands.

## (b) Three-plane source-of-truth mapping

There is a fourth plane worth naming: **TM's own control plane** (run
lifecycle from RunManager, breakpoint holds, proxy request-in-flight). It is
first-party truth, never inference.

| State | Truth plane | Corroborating | Notes |
|---|---|---|---|
| starting | control (run.started) | PTY (banner) | |
| working.thinking | **wire** (request open / response streaming) | transcript (lagging) | proxy sees request open+close exactly |
| working.running-tools | transcript (tool_use w/o result) | PTY (spinner) | only trustworthy when PTY shows **no gate** |
| gated.permission | **PTY only** | — | invisible to wire+transcript by construction |
| gated.plan-review | PTY (gate render) | wire (`ExitPlanMode` tool_use = arm signal) | wire narrows *when* to look |
| gated.auth | **PTY only** | wire (401s) | |
| asked (question) | **wire** (`AskUserQuestion` / `request_user_input` block) | transcript, PTY | earliest + most structured on wire |
| idle | wire (`stop_reason end_turn`) + PTY (no gate, input box) | transcript | |
| held | **control** (breakpoint) | — | zero inference |
| exited | control (PTY exitCode / releaseCapture facts) | transcript | |
| unknown/stale | absence across all planes | — | see liveness below |

Fusion rule sketch: **control-plane facts override everything; a detected PTY
gate overrides wire/transcript activity; wire beats transcript on timing;
transcript beats wire on content richness.** Practically: keep the existing
transcript machine as the spine, and let two overlay inputs (wire turn
cursor, PTY gate detector) assert/clear overlay states with provenance and
confidence attached. That keeps replay determinism (transcript machine stays
pure) while overlays are explicitly marked as live-only signals.

**Plane availability is per-run, not global.** Canvas runs have all planes.
Detached CLI runs (`transport-matters claude` in the user's own terminal)
inherit the user's real TTY — no PTY plane (verified: the CLI foreground path
spawns the harness as a plain subprocess; only canvas runs go through
node-pty in `packages/runtime`). Codex adds wire opacity variations. So the
state model needs a `plane_coverage` notion: the same fused state carries
different confidence for a canvas run (gate detection available) vs a
detached run (gates structurally invisible → the honest output for a pending
tool_use with no result is `running-tools OR gated (undetectable)`, which the
UI can render as "possibly waiting on you"). Bold option: offer an opt-in
PTY-wrapped detached launch (script/pty interposition) to close the gap;
tradeoff is TTY fidelity risk in arbitrary user terminals.

**Liveness heartbeat (cheap win).** While a harness works, its TUI repaints
continuously (spinner, token ticker, "esc to interrupt"); `ScrollbackRing`
chunks already carry `emittedAt`. PTY-chunk recency is a liveness signal that
beats the 10-minute transcript-silence stall: a run whose PTY went quiet
mid-turn is stalled in seconds, and a gate render is *itself* PTY activity,
so gates never false-positive as stalls. Wire keeps its role for detached
runs.

## (c) PTY-capture probe findings + snapshot mechanism

### What exists (all server-side, one process)

- Ring: `packages/runtime/src/domain/terminal/ScrollbackRing.ts` — byte
  chunks `{seq, data: Uint8Array, emittedAt}`, default 2 MiB
  (`DEFAULT_SCROLLBACK_BYTES`), truncation tracked, `snapshot()` clones.
- Ownership: one `TerminalFanout` per run (`fanout.scrollback`), inside
  `RunManager` (`packages/runtime/src/service/RunManager.ts`). Every PTY byte
  flows through `session.onData` → `fanout.append`.
- Reachability: **yes, in-process.** The gateway composition root
  (`packages/gateway/src/app.ts`, `buildGateway`) mounts activity and runtime
  routers on one Fastify instance, so the activity ingestion loop and the
  scrollback rings are co-resident. Contexts must not import each other, so
  the seam is a port: runtime exposes a `TerminalObservationPort`
  (`tailBytes(runId, n)` / `onQuiescence(runId, cb)`), wired at the gateway
  like existing deps; or runtime emits gate events onto the same event path
  activity already consumes. Precedent for byte-level parsing on this stream
  already exists: `OscColorResponder` subscribes to `session.onData` today.
- Existing surfaces: attach replays the ring over `WS /runs/{id}/terminal`;
  no server-side parsing of ring content yet.

### Snapshot + parse: three trigger options

1. **Turn-end snapshot (the brief's baseline).** Wire plane marks response
   close → wait a short render-settle (~200-500 ms) → `tailBytes(~16-64 KiB)`
   → parse. Pro: cheap, anchored to a real boundary. Con: misses gates that
   appear *mid-turn* (permission prompts fire between tool_use and
   tool_result — exactly the state we most need); turn-end is when gates are
   *least* likely.
2. **Quiescence-triggered detector (preferred).** Debounce on ring appends:
   whenever the PTY goes quiet for ~300 ms while the transcript machine says
   a turn is open, snapshot the tail and parse. A rendered gate is precisely
   "output burst, then silence awaiting input", so quiescence is the natural
   trigger; it also feeds the liveness heartbeat for free. Cost: a debounce
   timer per run (trivial next to CaptureHealthMonitor's per-run poller).
3. **Continuous streaming matcher.** Per-chunk incremental matching
   (OscColorResponder-style). Lowest latency, highest coupling to escape
   sequences; overkill unless gate latency must be sub-100 ms.

### Parsing: render, don't regex raw bytes

Raw chunks are ANSI-laden and cursor-addressed; regexing them is the fragile
path. Feed the tail into a **headless VT screen** (`@xterm/headless` — same
engine the canvas viewer already renders with, so server parse fidelity
matches what the human literally sees; xterm is already in the workspace
catalog) and match against the **rendered final screen lines**. This
single move buys most of the version resilience: TUI reflows, color changes,
and redraw strategies vanish; only the text of the prompt matters.

### Resilience tiers (drift strategy)

- **Tier 1 — versioned gate-signature packs, as data.** Per harness, a list
  of `{gate_kind, matchers, option_extractors, min_version, max_version}`.
  TM already observes the harness version first-hand on the wire
  (client-version headers / UA), so pack selection is exact, and a version
  TM has never seen is *detectable the moment it appears* — flag
  "unverified pack" instead of silently misparsing.
- **Tier 2 — structural gate heuristic.** Harness-agnostic shape matcher: a
  question line + numbered/bulleted options + cursor parked awaiting input.
  Catches new gate types and new harnesses as `unknown-gate` (still flips
  needs_you, which is the product truth even unclassified).
- **Tier 3 — LLM tail classifier (bold).** On unknown-gate or low
  confidence, ship the rendered tail lines to a small model: gate or not,
  which kind, extract options. Pennies per event at gate frequency; makes
  new-harness onboarding nearly free. Never on the hot path — async upgrade
  of an already-flipped `unknown-gate`.
- **Corpus + canary.** Every detected gate stores its rendered-tail fixture
  (tier-1 run dir is the natural home). New harness version → replay corpus
  against the new pack → drift caught in CI, not by a user staring at a
  wrong badge. Onboarding a new harness = record fixtures of its gates once,
  write a pack, done; tiers 2/3 cover the interim.

### Bold extension: gates as remote-actionable

Once the parser extracts options, `RunManager.write` can answer them. The
state subsystem's gate payload (Option C above) is then the *contract for
remote gate answering* from the desktop or even a phone notification. Worth
keeping in view while choosing the vocabulary shape, so we don't design a
read-only enum we immediately outgrow.

## Cross-cutting: harness onboarding as a capability descriptor

Everything per-harness above (transcript parser, wire markers, gate pack,
plane coverage) wants one home: a **harness descriptor** — data + small
adapters, versioned, declaring "which planes exist for this harness, which
states each plane can prove, which signature pack applies to which version
range". `harnessRegistry.ts` is the embryo. New harness = new descriptor;
new version = new pack entry + corpus replay. The state machine core never
changes.

## Headlines

- Split today's `needs-you` into `gated` (sub-typed: permission,
  plan-review, auth, unknown) / `asked` / `idle`; ship as status +
  attention/gate payload, not a wider flat enum.
- Permission and plan gates are **PTY-only truths**; the ring
  (`ScrollbackRing`, 2 MiB, per-run, in the same gateway process as
  activity) is reachable through a port today — quiescence-triggered
  snapshot into a headless xterm screen, matched by versioned gate packs
  with a structural-heuristic + LLM fallback, and every detection stores its
  own regression fixture.
- PTY plane exists only for canvas runs; the model needs per-run plane
  coverage and honest confidence, and PTY-chunk recency should replace the
  10-minute stall timeout where the plane exists.
