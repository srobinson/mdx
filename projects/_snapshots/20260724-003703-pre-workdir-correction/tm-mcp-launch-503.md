# MCP launch 503 root cause

Status: verified on 2026-07-20 against `feat/launch-verdict-surface` at `a18e2cb76f6d`.
The investigation was read only except for one controlled gateway create that failed before
spawn. No live run or repository file was changed.

## Verdict

The MCP launch fails in target resolution inside the capture RPC. The configured gateway is
reachable and correctly addressed.

The concrete rejection is:

```json
{
  "error": "connection_unavailable",
  "message": "launch target resolution failed (connection_unavailable): reason=no_connection_registered"
}
```

PR #311 caused the launch regression for requests carrying `model` or `effort`. It added the
resolver to capture preparation while the production system has no writer that registers a
`HarnessConnection`. The preexisting empty connection catalog became a hard launch gate.

## Failing path

1. Run `09e6d63c-a570-4e64-968e-33be28aa05b5` has its Transport Matters MCP URL set to
   `http://127.0.0.1:8798/mcp` in its generated `.mcp.json`.
2. Backend `8798` owns the desktop control plane and supervises gateway `60365`. The gateway
   has `TRANSPORT_MATTERS_CAPTURE_RPC_URL=http://127.0.0.1:8798`.
3. `ControlPlaneLauncher._execute` calls `RunRouteProxy.create_run`, which posts to gateway
   `60365`.
4. The gateway `RunManager` calls `POST /v1/capture/prepare` on backend `8798`.
5. `capture_rpc_routes._resolved_domain_request` invokes `_resolve_launch_target` whenever
   `model` or `effort` is present.
6. `resolver_snapshots_for_harness` reads zero registered connections. Target observations are
   present: 10 for Claude and 7 for Codex.
7. `resolver._select_connection` rejects before route or target selection with
   `connection_unavailable`, reason `no_connection_registered`.
8. The capture route maps that rejection to HTTP 503. The gateway preserves its status and code.
9. Python `run_proxy._run_request_error` preserves only the three
   `HARNESS_ENABLEMENT_ERROR_CODES`. `connection_unavailable` is outside that vocabulary, so it
   becomes `gateway run request failed with 503`. `gateway_response_error` then maps the uncoded
   503 to `delivery_failed`.

This explains the apparent contradiction. The request reaches a healthy gateway, then returns
from the resolver through that gateway as HTTP 503. The 503 does not indicate gateway transport
failure.

## Live evidence

The MCP target and process bindings were inspected from the generated runtime home and live
process environments:

```text
MCP URL:             http://127.0.0.1:8798/mcp
desktop backend:     127.0.0.1:8798
desktop gateway:     127.0.0.1:60365
gateway capture RPC: http://127.0.0.1:8798
```

Read probes to the gateway and its Python proxy both returned HTTP 200 and the same run list:

```text
GET http://127.0.0.1:60365/v1/runs?owner=local  200
GET http://127.0.0.1:8798/v1/runs?owner=local   200
```

A controlled direct create on gateway `60365`, matching the MCP launch fields and carrying
`model=claude-opus-4-8`, returned the structured 503 above. It failed before spawn, so there was
no run to terminate.

The persisted control plane audit contains three failures for the same actor at 19:53, 20:03,
and 20:13 UTC. Each records `gateway run request failed with 503`, confirming the later masking
boundary.

## Why canvas works

Canvas `createCapturedRunView` sends harness, worktree, identity, permission, grant, continuation,
and idempotency fields. It sends no `model` or `effort`.

`capture_rpc_routes._resolved_domain_request` explicitly returns before resolver consultation when
both fields are absent. The harness home selects its native default, so CMDK and canvas launches
continue through the same healthy desktop gateway.

## Why `harnesses` says `target_unavailable`

The full inventory reports zero connections and zero launch options for Claude and Codex, while
their installation and target observations are healthy. The lean launch projection sees no
launchable option. `harness_launch_view._unavailable_reason` then falls through to the generic
`target_unavailable` string.

That value is a projection fallback. The actual resolver rejection reached by explicit launch is
`connection_unavailable` before target selection.

## Regression boundary

Commit `3ae57012`, PR #311, changed capture preparation from unconditional pass through to resolver
consultation for explicit model or effort. Its integration test seeds a connection before testing
explicit target launch, then asserts HTTP 503 after deleting that connection.

Repository search finds `ExecutorEvidenceStore.persist_connection` in its definition and test
setup only. No production path registers a connection. The empty live catalog is therefore the
current product state, rather than a failed refresh. Startup refresh can probe existing connections
but cannot create one.

## Architecture question

The MCP path uses the desktop backend and desktop gateway that created the run. Each captured run
also starts a pane local backend and, because gateway supervision remains enabled without an
explicit shared URL, a pane local gateway. For this run those endpoints are `60483` and `60520`.
They are healthy but absent from the MCP launch path.

Stuart should decide whether captured run backends should suppress gateway supervision or point at
the desktop gateway. The current fan out duplicates gateway processes and obscures ownership, but
it does not cause this 503.

## Root cause statement

MCP explicit target launch is rejected by the resolver because the live executor has no registered
connections. PR #311 made that previously inert catalog gap a hard gate. The gateway URL is correct
and reachable; error vocabulary narrowing hides `connection_unavailable` as a generic gateway 503.
