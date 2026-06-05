# S5 MAX Review: prompt delivery and B1 causal damping

## Verdict

**HOLD. Three Blockers and four Majors.**

B1 does not hold under the active turn race or across the two WATCH event
sources. The implementation proves counter arithmetic in controlled unit tests,
but it does not bind a PTY acceptance to a specific turn boundary. A cached
Activity state can choose the wrong completion budget, Python arms the ledger
only after the delivery response returns, and wire completion can clear the
marker before the corresponding Activity state delta arrives. The last case can
keep reciprocal `state_changed` watches actuating each other indefinitely.

`needs_you` remains unsuppressed by causality. `dispatch_id` remains
observational. The director gate, envelope safety, fanout receipt shape, and S4
nudge reuse are sound.

## Scope and baseline

- Branch: `controlplane-s5-prompt`
- Reviewed head: `5b3222336666806f276ba3872e18563255c2a49a`
- Base and merge base: `3dfa33e86166bec27f9b69a1d6367c157e84ad82`
- Diff: 36 files, 1,831 insertions, 300 deletions
- Initial `git status --porcelain=v1`: empty
- Final status before this document: empty
- `git diff --check 3dfa33e..5b32223`: empty
- No builds or test suites were run because the brief prohibited repository
  writes and mutating checks. One no bytecode, pure ledger probe was run and is
  recorded below.

The findings below are branch introduced unless a scope note says otherwise.
Every reported finding cleared the 80 confidence threshold required by the
review workflow.

## Blockers

### B1. PTY acceptance and ledger arming have no shared turn boundary

**Severity:** Blocker  
**Confidence:** 95/100  
**Scope:** S5 causal binding

The gateway accepts the prompt at
[`RunManager.deliverInput`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/runtime/src/service/RunManager.ts#L415-L440).
Python records ancestry only after the HTTP await returns in
[`ControlPlaneWatchEngine._flush_serialized`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch.py#L567-L637)
and
[`ControlPlaneService._deliver_prompt_target`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L245-L281).
The independent wire task can call
[`consume_turn`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch.py#L418-L443)
at any point during that await. The receipt carries a state label, but no turn
index, generation, acceptance timestamp, or other boundary that
[`CausalAncestryLedger.consume_turn`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/causality.py#L78-L90)
can match.

Failing active turn interleaving:

1. B is working and has no pending ledger entry.
2. The gateway samples `working` and successfully writes A's nudge to B's PTY.
3. B's already active turn completes while Python still awaits the gateway
   response.
4. The wire consumer processes that completion with empty ancestry, so the
   completion can create a reciprocal fact.
5. The HTTP response reaches Python. Python now arms B for two completions.
6. B's induced completion spends the first slot.
7. A later unrelated human completion spends the stale second slot and is
   suppressed.

The reverse ordering also fails. A completion whose database read began before
the write can resume after `mark_delivery` and spend a causal slot. The ledger
therefore binds to observation order instead of the acceptance boundary.

### B2. `state_at_write` is a stale Activity cache, not acceptance time state

**Severity:** Blocker  
**Confidence:** 90/100  
**Scope:** S5 production wiring

Production derives `state_at_write` through
[`currentRunActivity`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/gateway/src/main.ts#L142-L165).
That method is a bare lookup in the
[`WorkspaceActivityProjections.byRun` cache](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/activity/src/projections/workspaceActivity.ts#L151-L159).
The cache changes only after the Activity actor applies asynchronously reread
store state and emits a projection at
[`WorkspaceActivityProjections.run` and `store`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/activity/src/projections/workspaceActivity.ts#L188-L223).
Activity itself documents that NOTIFY is only a doorbell and that reconciliation
rereads the store in
[`ActivityIngestion`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/activity/src/service/activityIngestion.ts#L95-L101).

Failing stale idle interleaving:

1. B's cached projection says idle.
2. B starts a human turn and is genuinely working, but the new state has not yet
   committed, notified, reconciled, and updated `byRun`.
3. A delivers a watch nudge. The gateway returns `state_at_write: idle`.
4. The ledger allocates one completion at
   [`causality.py:68`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/causality.py#L63-L76).
5. B's already active turn consumes that slot.
6. The queued, induced turn completes without ancestry and can notify A.

The opposite stale direction also fails. Actual idle with cached active allocates
two slots, so the induced completion leaves a stale slot that suppresses a later
human completion and its state changes. The callback is sampled immediately
before `tryWrite`, but the sampled value has no freshness guarantee and no PTY
or harness synchronization.

### B3. Wire completion clears suppression before the same turn's Activity delta

**Severity:** Blocker  
**Confidence:** 96/100  
**Scope:** S5 causal suppression across the authoritative WATCH topology

An idle delivery creates one pending completion. On completion,
[`consume_turn`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/causality.py#L78-L90)
removes `_pending` and retains ancestry only in `_latest_turn`.
[`active_ancestry`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/causality.py#L92-L94)
reads `_pending` only. Activity suppression then uses that pending only result in
[`_record_activity_delta`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch.py#L481-L514).

Failing reciprocal loop:

1. A causally nudges idle B. B receives ancestry `{A}` with one completion.
2. B's idle to working Activity delta arrives while pending and is suppressed.
3. B completes. The Python wire consumer runs first and removes B's final
   pending slot.
4. Gateway Activity SSE later reports the same turn's working to idle change.
5. `active_ancestry(B)` is now empty, so the idle `state_changed` is buffered
   back to A.
6. A handles that nudge and repeats the same sequence toward B.

This ordering can continue indefinitely. The working receipt case has the same
hole after its second and final tagged completion. The two event paths are
explicitly independent in
[`CONTROLPLANE.md`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/CONTROLPLANE.md#L138-L161),
so their relative arrival order cannot be assumed.

The existing state test sends Activity before any completion. The reciprocal
test subscribes only to `turn_completed`. Neither exercises the failing cross
source order.

## Majors

### M1. An accepted input with a lost response remains causally unmarked

**Severity:** Major  
**Confidence:** 80/100  
**Scope:** S5 causal integration over a preexisting ambiguous transport class

After the request is sent, a non-connect `httpx.RequestError` is explicitly
classified as an unknown outcome in
[`RunRouteProxy.deliver_watch_nudge`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/api/v1/run_proxy.py#L172-L208)
and
[`RunRouteProxy.deliver_input`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/api/v1/run_proxy.py#L210-L245).
Watch drops the attempted facts at
[`watch.py:610-620`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch.py#L598-L620),
and prompt returns a failed receipt at
[`service.py:265-280`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L258-L281).
Neither path marks causal ancestry.

If the gateway accepted the PTY write and only the response was lost, the input
still actuates a turn. That turn completes without ancestry and can restart a
reciprocal watch chain. The no retry rule correctly avoids duplicate input, but
causal safety needs a conservative marker for the ambiguous accepted case. The
prompt receipt also says `failed` even though the code explicitly knows the
acceptance result is unknown.

### M2. Delivered prompts can deterministically bypass mandatory audit persistence

**Severity:** Major  
**Confidence:** 100/100  
**Scope:** S5 prompt action contract

Prompt delivery sends a terminal safe envelope, then audits the original raw
text. `_terminal_safe_text` neutralizes control characters at
[`envelope.py:107-128`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/envelope.py#L107-L128),
while `prompt()` passes the original `text` to audit at
[`service.py:186-193`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L170-L194).
[`prompt_action`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/prompt_audit.py#L19-L42)
stores that raw value in the migration's PostgreSQL
[`text` column](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/migrations/versions/0013_control_plane_actions.py#L20-L39).

A prompt such as `continue\u0000now` is delivered safely as `continue now`.
PostgreSQL rejects code zero in `text`, as documented in its
[character type contract](https://www.postgresql.org/docs/17/datatype-character.html).
The audit insertion therefore fails. `_audit_prompt` catches every persistence
failure and still returns delivered receipts at
[`service.py:283-304`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L283-L304).
The branch test deliberately locks in that behavior at
[`test_prompt.py:120-135`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/test_prompt.py#L120-L135).

The result is accepted bytes, a delivered receipt, and no
`control_plane_action` row. This violates the locked requirement that every
action is attributed and persisted in
[`CONTROLPLANE.md`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/CONTROLPLANE.md#L11-L25)
and the persisted fanout contract at
[`CONTROLPLANE.md:163-169`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/CONTROLPLANE.md#L163-L169).
S4 watch registration and removal use fail closed audit before mutation; prompt
explicitly weakens that precedent. A durable intent plus outcome finalization,
or an equivalent outbox design, is required because PTY bytes cannot be rolled
back after audit failure.

### M3. The working at delivery integration proof does not cross a real boundary

**Severity:** Major, verification blocker  
**Confidence:** 100/100  
**Scope:** S5 race proof and builder trust

[`test_reciprocal_watch_loop_delivers_once_each_then_goes_silent`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/test_watch.py#L380-L429)
injects a literal state through `gateway.delivery_states`.
[`FakeGateway.deliver_watch_nudge`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch_test_support.py#L79-L95)
simply pops that value. The test waits until both fake deliveries have returned
before publishing any completion, which excludes the completion before mark
race by construction.

The TypeScript state test also injects a mutable callback in
[`RunManagerNudge.test.ts`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/runtime/src/service/RunManagerNudge.test.ts#L196-L215).
The Python proxy test injects a mocked HTTP payload. Runtime router tests return
`unknown`. No integration test joins a real Activity projection, production
gateway sampling, accepted PTY write, HTTP response, Python ledger mark, and an
interleaved completion. No reciprocal loop test exists under
`api/tests/integration/`, the location required by
[`api/CLAUDE.md`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/CLAUDE.md#L31-L38).

The current tests prove ledger arithmetic and adapter serialization. They do not
prove the boundary race named by the acceptance criterion.

### M4. The new input validator duplicates the existing control scan

**Severity:** Major under the repository's hard DRY rule  
**Confidence:** 100/100  
**Scope:** S5 code hygiene

[`validRuntimeInput`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/runtime/src/service/RunManager.ts#L31-L40)
duplicates the full UTF-16 code unit loop in
[`hasTerminalControl`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/packages/runtime/src/service/RunManager.ts#L42-L48).
The only policy variation is that prompt input permits line feed. The supplied
root repository instruction explicitly requires minor variation to be a
parameter and states that a pull request introducing duplication is incomplete.
One shared scan with an explicit line feed policy is the natural shape.

## Verified clean seams

- The director gate runs before prompt validation, gateway lookup, or delivery at
  [`service.py:119-133`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L119-L133).
- Expected per target delivery failures remain receipt data. `asyncio.gather`
  preserves target order, and the per target helper converts gateway failures at
  [`service.py:170-194`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L170-L194)
  and
  [`service.py:245-281`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/service.py#L245-L281).
- S4 nudge now uses the same `RunManager.deliverInput` and `PtySession.tryWrite`
  path. Single line validation, terminal control rejection, carriage return
  submission, 202 or 404 behavior, ConnectError retention, ambiguous outcome
  dropping, and missing watcher cleanup remain intact.
- Multiline prompt input uses bracketed paste plus a trailing carriage return.
  Interrupt mode sends the harness break, waits, then submits under the shared
  input queue. Claude Esc matches the specification. Current Codex supports Esc
  interruption, so the Codex break mapping is not a finding.
- Prompt and watch text both pass through `_terminal_safe_text`. Control and
  format categories are neutralized before the runtime boundary. The UTF-16
  budget matches the runtime's 4,096 code unit limit.
- `needs_you` is buffered without an ancestry guard at
  [`watch.py:506-514`](https://github.com/littleorgans/transport-matters/blob/5b3222336666806f276ba3872e18563255c2a49a/api/src/transport_matters/controlplane/watch.py#L506-L514).
  It remains unsuppressed.
- Complete symbol search found `dispatch_id` only in minting, envelope display,
  result serialization, and audit persistence. Causality, watch consumption,
  gateway delivery, and runtime input do not parse or depend on it.
- Hard file and function thresholds pass. `test_run_proxy.py` is 700 lines,
  `RunManager.test.ts` is 696, `watch.py` is 689, `RunManager.ts` is 679, and
  `test_watch.py` is 667. `ControlPlaneService.prompt` spans 77 lines,
  `RunManager.deliverInput` spans 26, and
  `CausalAncestryLedger.mark_delivery` spans 31.
- The extractions into `causality.py`, `prompt_models.py`, `prompt_audit.py`,
  `watch_delivery.py`, and `watch_registry.py` have coherent ownership. No new
  file exceeds 700 lines.

## Builder trust verdict

**Medium trust for bounded implementation. Sizeable boundary heavy scope still
requires a staff concurrency review and a real integration gate.**

Positive evidence:

- The builder followed the reuse map. One resultful input primitive owns nudge,
  interrupt, bracketed paste, submit, and immediate PTY closure detection.
- Policy remains in Python. The gateway remains a private executor. REST and MCP
  remain thin skins.
- Terminal envelope safety, director authorization, fanout receipt ordering,
  dispatch identity, and file decomposition show strong local craft.
- Several S4 hygiene problems were improved. The engine wide audit stall was
  removed, duplicated watcher cleanup was consolidated, and flush scheduling was
  named directly.

Trust limiting evidence:

- The core acceptance claim is a concurrency claim, but the tests replace every
  concurrency boundary with injected values and favorable ordering.
- The implementation treats asynchronous Activity cache state as acceptance
  truth and has no turn generation or linearization token.
- The two authoritative WATCH event paths are tested separately even though
  their relative order determines correctness.
- Mandatory audit persistence was consciously weakened and locked in by a test.
- The first input extension copied an existing validation loop despite the
  repository's explicit zero duplication rule.

The slice has good structure and weak race proof. I would keep this builder on
bounded work with adversarial review until it demonstrates full boundary tests
for actuation, completion, Activity propagation, and audit persistence.

## Read only verification evidence

Observed commands and results:

```text
git branch --show-current
controlplane-s5-prompt

git rev-parse HEAD
5b3222336666806f276ba3872e18563255c2a49a

git rev-parse main
3dfa33e86166bec27f9b69a1d6367c157e84ad82

git status --porcelain=v1
<empty>

git diff --check 3dfa33e..5b32223
<empty>
```

The no bytecode ledger probe exercised the exact B3 state transition:

```text
before_completion ['run-a']
completion ['run-a']
after_completion []
EXIT=0
```

All three parallel reviewers independently reported an empty worktree before
review and again before their verdicts. None ran builds, tests, or repository
writes.
