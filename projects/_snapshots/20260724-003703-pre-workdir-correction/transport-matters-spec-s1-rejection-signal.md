# Spec S1: provider-condition prompt-rejection signal (launcher-facing, real time)

Status: build brief. Scouted against `main` @ `506e0409`. Citations are
file + symbol, never line numbers. Companion slice: S2 enablement
(`transport-matters-spec-s2-enablement.md`), independent — do not couple.

## Goal

When a captured run's turn is rejected by the provider with an auth or
usage-limit condition, the agent that launched it learns in real time through
the ALREADY-BUILT control-plane pipe (`wait_for_reply`, `watch`), and the human
activity plane shows the same condition — all from ONE wire-failure
classification seam. Today a 401/429-failed turn resolves nothing:
`wait_for_reply` times out `pending`, `watch` stays silent. This slice adds the
missing producer; it adds no new channel, verb, or surface.

## Inputs

- Scout report: `~/.mdx/projects/transport-matters-scout-harness-auth.md`
  (Reuse Map + Delta sections).
- Fixed product decisions: auth is never a launch gate; the launcher agent is
  the primary consumer; the human toast/inbox is a later slice (S3).

## Decisions already made — do not redesign

1. **Classify once at the wire seam.** Anthropic: HTTP 401 (`auth_required`)
   and 429 (`usage_limit_reached`) at `addon_handlers.py ::
   handle_response_headers` header time. Codex: WS upgrade 401/403
   (`auth_required`) at the transport point where
   `codex/transport.py` records `response_status_code`.
2. **Fan out from the classification into the existing planes**: resolve the
   run's OPEN control-plane deliveries with the reason, and mint a NEW
   needs_you kind on the activity plane, so the launcher is served by the
   existing `wait_for_reply` / `watch` verbs and the human by the same
   activity/SSE signals.
3. **Reason enum `{auth_required, usage_limit_reached}` is a SEPARATE additive
   reason set** in `controlplane/prompt_models.py`. Do NOT extend
   `HARNESS_REJECTION_PROMPT_REASONS`: that set is harness CONTRACT evidence
   feeding the S2d drift seam (`harnesses/drift_emitter.py ::
   ActuationDriftObserver`); reusing it mints false drift evidence on every
   expired login. `PromptReceipt.reason` is an open string; the sets are
   classification frozensets, so this is additive.
4. **DRY the codex recognition vocabulary**: hoist the 401/403 auth-rejected
   status recognition so the live classifier and `codex/diagnostics.py ::
   build_codex_transport_diagnostics` (`chatgpt_auth_rejected`) share one
   owner. One vocabulary, two consumers (live + post-hoc diagnostic).

## Phasing (spec explicitly, ship in this slice unless marked follow-up)

- NOW: Anthropic `auth_required` (401) + `usage_limit_reached` (429).
- NOW: codex `auth_required` (WS upgrade 401/403).
- FOLLOW-UP (documented in the code where the codex classifier lives): codex
  `usage_limit_reached`. There is NO limit-frame constant in
  `codex/protocol.py`; do not guess one. It requires certification against a
  REAL codex wire capture first (same lesson as the codex stderr probe: unit
  fixtures from an assumed channel passed everything and shipped a
  misclassification).
- OUT until S2h: grok (no wire substrate; no adapter registered).

## Reuse map — the signal chain, end to end

Detection (addon capture process):

- `addon_handlers.py :: handle_response_headers` — has
  `flow.response.status_code` plus `RequestFlowState` (`run_id`, `provider`,
  `provisional_exchange_id`, track role) before any body bytes. Genuinely
  live; the 401/429 classification needs no chunk tap.
- Codex rejected upgrade — requirement and constraint (mechanism can settle
  at build): a rejected upgrade (non-101, 401/403) never produces WS
  messages, and NONE of the message-path identities exist at that moment —
  the upgrade GET creates no `RequestFlowState`, `codex/transport.py ::
  CodexTransportState` carries no `run_id` and gains
  `provisional_exchange_id` only after a client frame, and the handshake
  persistence path mints a SEPARATE exchange id. The spec therefore
  requires: (1) **response-path binding resolution** — resolve the run
  identity on the upgrade-response path itself (the proxy's run binding,
  the same source `LiveStatusObserver` uses via `binding_for_run_id` /
  `ProxyRunBinding`), not from message-path state; (2) **one generation
  identity** — the classification signal and the persisted handshake
  exchange must share a single generation/exchange id, not two
  independently minted ones. The prod-path emission test must assert that
  same identity end to end (signal id == persisted handshake exchange id),
  which fails if the two paths mint separately.
- Installed-observer pattern to mirror: `live_status_observer.py ::
  LiveStatusObserver`, wired once in `addon_runtime.py`, best-effort, never
  blocks the proxy, run-binding via `binding_for_run_id`.

Signal transport (recommended binding — rides a fully built channel):

- Extend `live_status.py :: LiveStatusKind` and `session/models.py ::
  RunLiveStatusKind` with the two provider-condition kinds; publish through
  the existing `SessionWriter.submit_run_live_status` →
  `RUN_LIVE_STATUS_PAYLOAD_TYPE` (`session/notify_payloads.py`) → `tm_events`
  → activity ingestion. Builder may substitute a dedicated payload type only
  if kind-extension proves unworkable; the constraint is one channel, already
  wired end to end, no parallel pipeline.
- **Migration (this slice owns revision `0025_provider_condition_kinds`)**:
  the `run_live_status.kind` column carries a DB CHECK constraint
  (`run_live_status_kind_check`); the kind extension REQUIRES a migration
  extending it. Precedent to mirror:
  `api/migrations/versions/0011_run_live_status_asked.py` (drop + re-add the
  named constraint with the widened value set). Revision id constraint:
  Alembic's `version_num` column is `String(32)`, so the slug must be ≤32
  chars — `0025_provider_condition_kinds` is 29. `down_revision` is
  whatever main's migration head is AT MERGE TIME (today
  `0024_drop_observation_identity`); do NOT hardcode a dependency on S2's
  revision — the slices are independent, and whichever merges second rebases
  its `down_revision` onto the other's head and re-verifies
  `session/testing.py :: EXPECTED_MIGRATION_HEAD_REVISION` plus the stepwise
  walk in `session/test_migration_roundtrip.py`.
- **Stickiness caution — three layers, all required**: (1) the observer lane:
  flow teardown emits a terminal stop (`LiveStatusObserver._finish_tap`,
  `flow_abort`) and `_offer` holds `ASKED` against subsequent rows — the new
  kinds need the same lane treatment; (2) the activity machine: mirror how
  `asked` survives stream end (`runActivityContext.ts` holds
  `needs-you-asked`); (3) **the durable projection**: `session/writer.py ::
  submit_wire_exchange` unconditionally clears the durable live kind at
  finalize, and a finalized 401/429 exchange projects only a response error —
  so a restart or activity reconciliation would silently drop the condition.
  The finalize path must preserve (or re-mint) the provider-condition kind so
  reconciliation and API restart re-project it. The test list requires a
  restart/reconcile test for exactly this.

Activity plane (gateway-side TS; the enum was designed for this):

- `packages/contract/src/activity/wire.ts` — `activityStatuses`,
  `activityStatusTier`, `ActivityNeedsYou` union, `needsYouForStatus`. The
  reserved `needs-you-gated` comment documents the intended extension pattern:
  additive status + payload variant through "this single derivation".
  Recommended shape: two statuses (`needs-you-auth-required`,
  `needs-you-usage-limit`) with payload kinds `{kind: "auth_required"}` /
  `{kind: "usage_limit_reached"}` so `needsYouForStatus` stays a pure function
  of status. Builder may adjust naming, not the purity or additivity.
- `packages/activity/src` — ingestion (`service/activityIngestion.ts`,
  `ports.ts :: RunLiveStatus`), machine (`domain/runActivityEvent.ts`,
  `domain/runActivityMachine.ts`, `domain/runActivityContext.ts` — see how
  `record.question_asked` reaches `needs-you-asked`), projection
  (`projections/workspaceActivity.ts`).
- Python mirrors: `controlplane/activity.py` (`ActivityStatusTier`,
  `GatewayActivityRun.needs_you`). Caution: `test_type_mirrors.py` currently
  pins only `ActivityStatusTier`; status and needs_you payload are open
  Python containers, so the mirror guard this spec relies on DOES NOT EXIST
  yet for them. In scope: extend `test_type_mirrors.py` to pin the
  `ActivityStatus` value set and the needs_you payload kinds against the
  contract package, so the next enum change cannot drift silently.
- Canvas ripple (in scope, minimal): adding `ActivityStatus` members forces
  the status fixtures (`packages/contract/src/activity/fixtures.ts`) and the
  Canvas vitals label mapping
  (`www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx`, which
  derives from `activityStatusTier`) to acknowledge the new statuses. Land
  the minimal label/fixture updates here so nothing crashes or renders a raw
  enum string; the human toast/inbox and any richer rendering stay in S3.

Launcher consumption (pipe is built; TWO targeted extensions are in scope):

- **Delivery store change (required — "zero store changes" was wrong)**:
  `controlplane/delivery_wait.py :: _resolve_deliveries` resolves only the
  active correlated prompt and skips deliveries without a `prompt_cursor`
  binding. A codex run whose HANDSHAKE is rejected never produces the wire
  exchange the claim/bind path correlates on
  (`delivery_wait.py :: _claim_deliveries`,
  `delivery_store.py :: claim / bind / finish`), so the launcher's targeted
  wait would stay `pending` forever. Spec: extend the resolution path so a
  provider-condition signal for a run resolves that run's OPEN deliveries
  (claimed or not yet bindable) to `needs_you` with the classified reason —
  via `delivery_store.py :: finish` (or `note` + finish), keyed by run, not
  by prompt cursor. Thread the reason into the `WaitForReplyResult` the agent
  sees (`delivery_wait.py :: _result`).
  **Cursorless constraint**: finishing an unbound delivery leaves both
  conversation cursors null, and `_result` currently RAISES ("terminal
  delivery is missing its conversation range") on a terminal delivery
  without a range — so the naive finish would turn the launcher's wait into
  an exception, not a resolution. Requirement: define a cursorless
  provider-condition result shape (a `WaitForReplyResult` variant that
  carries the reason and no conversation range) or a valid synthetic range;
  either way the required test asserts the launcher's wait ACTUALLY RESOLVES
  with the returned result — no raise, no timeout. Exact mechanism can
  settle at build.
- **Watch envelope change (required)**: `controlplane/envelope.py ::
  format_watch_envelope` discards `WatchFact.status` for `needs_you` facts,
  so the watcher would learn "needs you" but never the reason. Extend the
  needs_you rendering to carry the new status/reason; the test list requires
  proving the reason reaches the watcher through the PTY push
  (`watch_delivery.py :: WatchDeliveryLoop`), not just that a fact was
  minted.
- MCP verbs: `api/v1/controlplane_mcp.py :: wait_for_reply`, `watch` —
  no verb signature changes expected.

Boundaries — do not double-handle:

- `counting.py` has its own count_tokens sidecar 429 skip: separate plane,
  untouched.
- `exchange_recorder_artifacts.py :: tag_http_error_status` tags `http_429` /
  `http_401` stop reasons at finalize: keep as-is; it is the durable record,
  not the live signal.
- Drift seams and `HARNESS_REJECTION_PROMPT_REASONS`: untouched (decision 3).

## Deliverables

1. Wire failure classifier (new module beside `live_status_observer.py`, or an
   extension of it — builder's call; installed in `addon_runtime.py`) covering
   the two seams and the phased matrix above, with **episode dedup defined
   as**: one signal per run per condition; the episode CLOSES when a
   subsequent turn for that run succeeds (a successful terminal exchange, the
   same signal the activity machine treats as recovery), and the classifier
   REARMS on close. Note the cited `DriftEmitter` `_seen` idiom is
   process-lifetime with no reset — mirror its best-effort scheduling, not its
   memory; the episode state must support 401 → success → 401 re-fire.
2. Provider-condition reason set in `controlplane/prompt_models.py`.
3. Activity chain extension: contract enum + payload variants + machine
   transitions + Python mirrors (including the new `test_type_mirrors.py`
   status/payload pinning) + minimal Canvas fixture/label updates.
4. Delivery resolution + watch envelope extensions per the launcher
   consumption section.
5. Migration `0025_provider_condition_kinds` (CHECK constraint widening;
   slug ≤32 chars per Alembic `version_num String(32)`) + head bump +
   roundtrip walk step.
6. Shared codex auth-rejected recognition vocabulary, consumed by both
   `codex/diagnostics.py` and the classifier.
7. Contract docs: `CONTROLPLANE.md` and `CONTROLPLANE-OBSERVATION-PLAN.md`
   still define needs_you as an operator question or gate; update the
   needs_you definition to include the provider-condition kinds, in context
   (`.archive/` untouched).
8. Documented follow-up marker for codex usage-limit certification.

## Out of scope

Human toast/inbox UI and any overview rendering beyond the minimal Canvas
fixture/label updates (S3), gateway PTY matcher + bridge (S4), enablement
(S2), grok, probe wiring, any drift vocabulary change.

## Tests (required; assert the observable end-state the agent sees, not an
intermediate mapping — a passing intermediate assertion has shipped a false
fix here before)

- A 401-failed turn resolves a waiting launcher's `wait_for_reply` as
  `needs_you` with `auth_required` — no silent timeout. Include the codex
  handshake-rejection case specifically: a wait targeted at a run whose WS
  upgrade 401s resolves (the delivery-store extension is what this proves).
- A 429-failed turn resolves as `usage_limit_reached`.
- The watch path delivers the REASON through the PTY push: the watcher's
  rendered envelope carries the provider-condition kind, asserted at the
  delivery output, not at fact minting.
- Prod-path emission: a codex 401/403 upgrade driven through the real addon
  handler entry point emits the signal — a test that FAILS if the
  RequestFlowState/binding handoff is missing (a classifier unit with a faked
  handoff does not satisfy this).
- Per-seam classifier units: Anthropic header-time classification; codex
  upgrade-status classification.
- Episode dedup + rearm: second 401 in the same episode emits nothing;
  401 → successful turn → 401 re-fires; same for 429.
- Stickiness across all three layers: the condition survives flow teardown,
  AND survives finalize + restart/reconciliation (`submit_wire_exchange` must
  not clear it — persist-then-reproject test, not a fresh in-memory
  round-trip).
- Reason-boundary: assert the provider-condition set is disjoint from
  `HARNESS_REJECTION_PROMPT_REASONS`, and that a classified 401/429 emits
  ZERO drift evidence (no `DriftEvidence` row, no drift audit action).
- Mirror guard (`test_type_mirrors.py`, extended) green.

## Completion line

Done when: a director agent prompting a captured run whose provider returns
401 gets a real-time `needs_you(auth_required)` resolution on
`wait_for_reply` and a watch PTY push carrying the reason, 429 likewise as
`usage_limit_reached`, the condition is visible on the AGENT-FACING activity
reads (`workspace_summary` / `roster` via the MCP verbs) and survives an API
restart, and all gates pass. The human overview UI is NOT part of this
completion line (S3); only the minimal Canvas fixture/label updates land
here.

## Verification gate

`just check` + `just test-affected` (content-judged, not exit-code-through-a-
pipe). Blast radius spans `api/`, `packages/{contract,activity}`,
`www/packages/canvas` (fixtures + `RunVitalsStrip` labels), and the root
contract docs (`CONTROLPLANE.md`, `CONTROLPLANE-OBSERVATION-PLAN.md`) — the
full `just test` must run before merge (grok's pre-merge gate covers this;
the builder runs it directly if landing outside the warroom flow).

## Plan-text note

`RUNTIME-SURFACING-S2-PLAN.md` S2f item 4 retirement is assigned to slice S2
(it owns the launch-gating plan text). This slice changes no plan text.
