# Scout: "Usage limit" false positive on a healthy Claude run

Read-only investigation on main @ `e38bfa2e` (S1 merged at `42a2196d`).
Symptom: canvas `RunVitalsStrip` shows "Usage limit" on a healthy, idle
Claude run. Verdict up front: **Hypothesis 1 is the root cause, in a sharper
form than proposed — the classified 429 is not even a transient throttle on
real traffic; it is Claude Code's own deliberate quota-probe request, whose
EXPECTED response on a healthy account is a 429.** Hypothesis 2 is rejected
as a defect but explains the persistence: the sticky episode clears only on a
later successful turn terminal, so a 429 that lands while the run is idle
(exactly when the probe fires) latches the badge with nothing to clear it.

## The smoking gun: captured quota probes

Every `http_429` exchange in the live capture store is the same request —
Claude Code's quota probe:

- Request (`request.raw`, run `ab3cb696`, exchange `7e8f6798`):
  `{"model":"claude-fable-5","max_tokens":1,"messages":[{"role":"user","content":"quota"}], ...}`
  — one user message, literal text `"quota"`, `max_tokens: 1`.
- Response (`response.raw`):
  `{"type":"error","error":{"type":"rate_limit_error","message":"Error"},"request_id":"req_011Cd8..."}`
  — a 429 `rate_limit_error` with an empty-ish message.
- Four such exchanges exist across four runs in
  `~/.transport-matters/workspaces/` (all `msgs: 1, chars: 51`,
  stop_reason `http_429`), each at run start or between turns. In run
  `ab3cb696` the probe 429 at `00:05:10` is followed 38 seconds later by a
  perfectly healthy 115K-char `tool_use` turn.

This is how Claude Code reads its usage/rate-limit state (the `/status`
usage display): it sends a throwaway 1-token request and reads the
rate-limit headers off the 429. A healthy run therefore **routinely
produces a 429 on its own run_id**, at startup and while idle.

## Classification trace (Hypothesis 1 — CONFIRMED)

- `provider_conditions.py :: classify_provider_response_status` maps
  Anthropic `429 -> "usage_limit_reached"` unconditionally — no body, no
  header, no request-shape discrimination.
- The probe flows through `addon_handlers.py :: handle_http_request` like
  any `/v1/messages` request (it parses, gets a `RequestFlowState` with the
  run's id and a provisional exchange id), so
  `addon_handlers.py :: handle_response_headers` calls
  `live_status_observer.py :: LiveStatusObserver.observe_response_status`,
  which mints the sticky `usage_limit_reached` row for the run.
- Distinct real-world 429 classes the classifier cannot currently tell
  apart: (a) the quota probe's expected 429; (b) transient RPM/TPM
  throttles during heavy turns, which Claude Code auto-retries and which
  carry `retry-after`; (c) a genuine subscription usage cap — the only one
  that is a real `needs_you`. Claude Code's own "usage limit reached" UX is
  (c) only.

## Stickiness trace (Hypothesis 2 — works as designed; explains persistence)

The clear path functions when a turn follows:

- A later successful turn streams kind facts (overwriting the row) and ends
  with a genuine terminal (`stop_reason` via the classifier, provider_event
  not `flow_abort`, different generation), which pops the episode in
  `live_status_observer.py :: LiveStatusObserver._offer` and clears the row.
  The probe exchange's own finalize cannot null the row: the generation-scoped
  close (`session/dao_statements.py :: CLOSE_RUN_LIVE_STATUS_GENERATION_SQL`)
  targets the probe's generation while the row has moved on.

The failure shape is a 429 landing when NO successful turn follows — which
is precisely when the quota probe fires (startup before the first turn, or
mid-idle). Then:

- The sticky row survives (by design), the activity ingestion re-asserts it
  every reconcile (`wireCandidate.ts :: wireCandidateAdmitted` deliberately
  exempts provider conditions from assert-id suppression),
  `needsYouForStatus` yields `{kind: "usage_limit_reached"}`, and
  `RunVitalsStrip.tsx` renders "Usage limit" over an Idle run — matching the
  user's report (idle, 44,946 tokens, responded normally: the last turn
  succeeded BEFORE the latching 429).
- This stickiness is correct for a real cap; it converts the H1 misfire
  into a permanent badge. No change to the episode model is needed once the
  classification is fixed.

## Scope of the risk

- **429/Anthropic only.** Codex classifies no 429 (auth-only, upgrade
  scoped), so codex is unaffected. The 401 path is low-risk for both
  harnesses: nothing fires deliberate 401-expecting probes, and a transient
  401 is not routine — a 401 on the wire genuinely means credential failure.
  (The same "no clearing while idle" persistence applies to a MID-RUN 401
  by design, and that is the desired behavior there.)

## What the wire offers as a discriminator

- The response BODY of the probe's healthy 429 is
  `rate_limit_error` / `"Error"` — indistinguishable from a transient
  throttle by type alone. A genuine claude.ai usage cap is understood to
  carry the unified rate-limit vocabulary Claude Code itself consumes —
  `anthropic-ratelimit-unified-status` (`allowed` / `allowed_warning` /
  `rejected`) and `anthropic-ratelimit-unified-reset` headers — with the cap
  signaled by `rejected`. **This must be certified against a real capture
  before use** (the S1 rule for codex limit frames applies here equally):
  response headers are available live at `handle_response_headers`
  (`flow.response.headers`) but are NOT persisted for Anthropic exchanges
  today (`exchange_recorder_artifacts.py` stores bodies; only codex
  transport artifacts keep headers), so certification means one live header
  capture of the probe (healthy) and, when available, a capped account.

## Fix options

1. **RECOMMENDED — certify-then-classify (mirror the codex deferral):**
   stop minting `usage_limit_reached` from a bare Anthropic 429 now (delete
   the `429` mapping in `provider_conditions.py ::
   classify_provider_response_status`, keeping 401), and reintroduce it
   only keyed on the certified cap discriminator (unified-status `rejected`
   header and/or cap-shaped body) read at header time. Tradeoffs: the
   usage-limit signal goes dark for Anthropic until certified — honest,
   zero false positives, consistent with the spec's own
   certify-against-real-capture rule; the auth signal (the primary S1
   deliverable) is untouched.
2. **Request-shape exclusion (rejected):** skip classification when the
   request looks like the probe (`max_tokens <= 1`). Still misfires on
   routine transient throttles during real turns (auto-retried, recover);
   couples us to an undocumented probe shape.
3. **Stickiness softening (rejected):** auto-expire or clear-on-next-request.
   Timing machinery that flaps under a genuine cap and weakens the auth
   signal's correct latch — the wrong layer; the classification is the bug.

One-line root cause: `classify_provider_response_status` treats every
Anthropic 429 as a usage cap, and Claude Code's own quota probe guarantees a
429 on every healthy run at exactly the moments (startup, idle) when nothing
will ever clear the sticky badge.
