# 624: control plane: run failures the vocabulary cannot name lose their code and message, so an idempotency conflict reads as an invalid request

URL: https://github.com/littleorgans/transport-matters/issues/624
State: open
Labels: bug, P3
Updated: 2026-09-04T17:23:58Z

The Gateway's run routes reject with codes the control plane has no word for. Each one falls
back to a code derived from the HTTP status and a synthetic message, so a precise condition
the server already named arrives as a coarser one, and the reason it computed is dropped.

This is the residue #617 did not reach. #617 fixed the two losses it found and this branch
widened the recognized set twice more, always by carving a hole in the same generic default.
The remaining codes cannot be carved in, because the control plane cannot say them.

## Observed

Creating a run with an idempotency key already used for a different launch:

```
launch(...)
  -> {"failure":{"detail":{"code":"invalid_request",
      "message":"gateway run request failed with 409"}}}
```

`RunManager` raised `RunManagerError("idempotency_conflict", "idempotency key was already
used for a different launch request")` (`runManagerSupport.ts`, `RunManager.createWithDisposition`).
`replyRunManagerError` sent both faithfully as `{error, message}`. Neither survives.

The caller learns that something about the request was invalid, which is the same answer a
malformed body gets, and cannot tell that retrying with a fresh key would work.

## The five codes and what each becomes

`RunManagerErrorCode` in `runManagerSupport.ts` is the whole vocabulary the run routes
answer with, plus a capture RPC `upstreamCode` passed through by `RunManagerError`.
`gateway_response_error` in `controlplane/action_policy.py` derives the code from the status
whenever the body's code is unrecognized, which is all five.

| gateway code | status | caller sees | the message that is dropped |
| --- | --- | --- | --- |
| `idempotency_conflict` | 409 | `invalid_request` | idempotency key was already used for a different launch request |
| `run_terminated` | 409 | `invalid_request` | run `<id>` was terminated |
| `run_not_attachable` | 409 | `invalid_request` | run `<id>` is `<state>` |
| `launch_failed` | 500 | `delivery_failed` | the spawn or capture RPC failure, verbatim |
| `run_manager_closed` | 503 | `delivery_failed` | run manager is closed |

Three distinct conditions collapse onto `invalid_request`, which already means "you sent
something malformed". A caller cannot branch on any of them.

## Why the message goes with the code

`gateway_error_from_response` in `api/v1/controlplane_gateway_errors.py` keeps the body's
message only when the body's code is one the caller accepts, and replaces it otherwise. That
gate is deliberate and should stay: a control plane error is a pair, and forwarding a message
while deriving its code from the HTTP status would describe one failure in two vocabularies.

The consequence is that a message cannot be rescued on its own. The code has to become
sayable first, and then the message follows for free.

## Two remedies, not one

Not every gateway code needs a new word.

**Alias.** `run_manager_closed` is what `control_plane_unavailable` already means, and a
capture RPC `worktree_not_found` is a `not_found`. These need a gateway-code to
control-plane-code mapping at the run front, not a wider union. The message survives because
the code was recognized, which is the existing rule working as intended.

**Promote.** `idempotency_conflict`, `run_terminated` and `run_not_attachable` name
conditions the control plane has no way to express and a caller would act on differently.
These belong in `ControlPlaneErrorCode`.

`launch_failed` is the one that needs a decision rather than a default. Its message is
whichever OS or capture RPC error text the launch produced, so promoting it publishes
machine-generated internal text to every skin. `test_run_proxy_keeps_non_enablement_gateway_failures_opaque`
pins today's behaviour with `spawn /private/path EACCES` as its example. Whether that example
is a warning or an accident of drafting is not recorded anywhere: PR #301 introduced both the
parser and that test in one commit, the parser's docstring says only "Preserve hard enablement
codes from the gateway before generic mapping", and neither the PR body nor any doc mentions
leaks. The only documented opacity policy is `invoke_control_plane` in `controlplane/errors.py`,
and that one covers unexpected Python exceptions, not gateway bodies.

## Not the fix

Forwarding the message whenever the body carries one, and leaving the code status-derived.
It is the smaller change and it is wrong: the pair stops agreeing, so a caller reading
`invalid_request` alongside a message about a terminated run has to decide which half to
believe.

Widening `_RUN_ACCEPTED_CODES` in `api/v1/controlplane_gateway_runs.py` to admit the five
strings. `accepted_codes` is typed `Collection[ControlPlaneErrorCode]`, so a code that is not
in the union cannot be admitted without lying to the type, and `GatewayResponseError.code`
would then carry a value no skin can render.

## Outcome

A caller that hits a run condition the server named reads that condition, and can branch on it.

## Scope

- Add the promoted codes to `ControlPlaneErrorCode` in `controlplane/errors.py`, and to
  `CONTROL_PLANE_ERROR_STATUS` in `api/v1/controlplane_routes.py` with the status each maps to.
- Map the aliased gateway codes onto existing control plane codes at the run front, so their
  messages survive the same gate every recognized code passes.
- Extend `_RUN_ACCEPTED_CODES` to the promoted codes.
- Decide `launch_failed` explicitly, and record the decision where the next reader will find it.

## Acceptance

- An idempotency conflict returns its own code and the message `RunManager` wrote.
- A gateway code with no control plane meaning still returns the status-derived code and the
  generic message, so the default stays closed.
- The REST status map still exhausts the vocabulary, which
  `test_rest_status_map_exhausts_the_control_plane_error_vocabulary` already enforces.

## Blast radius

- `ControlPlaneErrorCode` is a closed union rendered into the MCP tool output schemas through
  `ControlPlaneFailure` and `ControlPlaneErrorDetails`, so promotion changes the published
  agent contract.
- `CONTROL_PLANE_ERROR_STATUS` must gain every new code or
  `test_rest_status_map_exhausts_the_control_plane_error_vocabulary` fails. That test is the
  guardrail; `control_plane_error_handler` falls back to 500 rather than raising, so an
  unmapped code degrades quietly rather than crashing.
- `LaunchTerminalError` in `controlplane/launch_ledger.py` stores a `ControlPlaneErrorCode` and
  round-trips it, so persisted ledger rows carry the wider vocabulary.
- No browser mirror of the union exists. The codes are not enumerated anywhere under `www/`.

## Map for the next agent

```
RunManagerError raised            packages/runtime/src/service/RunManager.ts
  the five codes                  packages/runtime/src/service/runManagerSupport.ts
replyRunManagerError sends both   packages/runtime/src/server/runtimeRouter.ts
_typed_run_request                api/v1/controlplane_gateway_runs.py
  >> code unrecognized            gateway_error_from_response, api/v1/controlplane_gateway_errors.py
  >> message replaced             same call
gateway_response_error            controlplane/action_policy.py
  >> code derived from status     same function
control_plane_failure             controlplane/errors.py
```

## Verified

Every symbol above was read on this branch at `29ee0af8`. The status column is
`RUN_MANAGER_HTTP_STATUS` in `runtimeRouter.ts` read against `gateway_response_error`; the
messages are the literals at each `new RunManagerError(...)` site. `run_not_found` is
deliberately absent from the table: those three routes send a bare code with no message, and
404 already maps to `not_found`, so nothing is lost there today.


## Sub issues
[]
