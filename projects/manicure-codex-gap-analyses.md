# Manicure Codex Gap Analysis

Date: 2026-04-18

## Summary

The Codex path is not matching the core product contract yet, and the gap is larger than lifecycle alone.

The intended behavior is:

- the user arms a breakpoint
- Manicure captures the outbound request before it reaches the upstream API
- the user can inspect and tamper with that request
- the UI shows the exchange as part of the live interception session

What happens today for Codex is materially different:

- Manicure does capture the initial Codex websocket request frame
- breakpoints can pause and rewrite that initial frame before upstream forward
- but exchange persistence happens only on websocket close
- so the UI remains empty during the live session
- and on shutdown the final persistence can race with process teardown and fail

There are also review blockers outside the lifecycle mismatch:

- release-time validation is broken and can return 500 instead of 422
- sensitive ChatGPT transport headers are being persisted and surfaced
- managed child processes inherit ambient proxy and trust env vars too broadly
- dropped websocket requests can still be persisted as exchanges

That makes the Codex implementation miss the core “arm and tamper before send” workflow, even though part of the interception machinery is already present.

So the right framing is:

- the primary product gap is lifecycle mismatch
- but the branch also has correctness and security blockers that must be fixed before acceptance

## Runtime Evidence

Workspace:

- `/Users/alphab/.manicure/workspaces/dev-helioy-fmm/6cc7a823`

Relevant log:

- `/Users/alphab/.manicure/workspaces/dev-helioy-fmm/6cc7a823/logs/mitmdump.log`

Observed in the live run:

- Manicure launched with storage root `/Users/alphab/.manicure/workspaces/dev-helioy-fmm/6cc7a823`
- Web UI came up on `http://127.0.0.1:52381`
- Codex traffic did route through the proxy
- The proxy saw `GET https://chatgpt.com/backend-api/codex/responses << 101`
- The addon logged `CODEX WS START`
- The addon logged `CODEX WS INIT ... captured initial client text frame bytes=103241 model=codex/gpt-5.4 msgs=1 tools=23`

This proves the Codex transport capture path is active and parsing real traffic.

Observed on shutdown:

- The log later shows `CODEX WS END ... close_code=1006`
- Persistence starts after websocket end
- The index row is appended
- The artifact write fails with `RuntimeError: Executor shutdown has been called`

Result on disk:

- `index.jsonl` exists and contains a Codex row
- no exchange artifact directory exists for that row

This is a partial-persistence failure, not a total capture failure.

## Primary Product Gap

The largest issue is not the shutdown race. The largest issue is lifecycle mismatch.

For Codex, the meaningful interception boundary is the first client `response.create` websocket frame, because that is the request that the user wants to tamper with before upstream sees it.

Today the code captures and can mutate that frame in `websocket_message()`, but persistence and UI exchange visibility happen only in `websocket_end()`.

That means:

- no live exchange appears while the request is in flight
- the user cannot rely on the exchange list as part of the interception workflow
- Codex does not behave like the rest of the product, where captured traffic becomes visible at request time

This is a showstopper for the breakpoint product contract.

## Additional Review Blockers

The lifecycle mismatch is not the only blocking issue.

Independent review of the implementation also surfaced:

### Broken release validation

- the breakpoint API currently uses a non-existent status constant
- invalid release paths can raise `AttributeError`
- provider mismatch and serialization failures can surface as 500 instead of 422

This is a correctness blocker for the live edit workflow.

### Sensitive transport persistence

- ChatGPT-authenticated Codex upgrade metadata is being stored too literally
- persisted transport artifacts can expose request headers that should be redacted or suppressed
- the exchange API and transport UI therefore risk surfacing auth material

This is a security blocker, not a polish issue.

### Launch environment leakage

- the managed child launch path inherits the ambient parent environment too broadly
- proxy and trust-related env vars outside Manicure control can still affect runtime behavior
- that makes capture and trust semantics host-environment dependent

This is a correctness and security blocker.

### Dropped websocket exchanges still persisting

- a dropped initial Codex websocket request can still be written to storage later at websocket shutdown
- that breaks user expectation and makes the exchange log misleading

This is a product correctness blocker.

## Current Codex Lifecycle

Relevant implementation:

- `api/src/manicure/addon.py`
- `api/src/manicure/codex_transport.py`

Current flow:

1. `websocket_start()` records handshake metadata.
2. `websocket_message()` captures the first client frame.
3. That frame is parsed into request IR.
4. The override pipeline runs.
5. If armed, breakpoint pause/edit/rewrite can happen before upstream forward.
6. If not armed, the possibly curated request is forwarded upstream.
7. No exchange is persisted yet.
8. Only when `websocket_end()` fires does `_persist_codex_exchange()` create the exchange row and artifacts.

This split explains why the UI stays empty during a live Codex session even though interception is already happening.

## Shutdown / Persistence Failure

Relevant implementation:

- `api/src/manicure/addon.py`
- `api/src/manicure/storage/disk.py`
- `api/src/manicure/cli/runner.py`
- `api/src/manicure/supervisor.py`

The failure mode is:

1. `_persist_exchange()` appends the index row first.
2. `_persist_exchange()` then writes the artifact directory second.
3. The artifact write uses `aiofiles`, which depends on the event loop’s default executor.
4. During process teardown, shutdown has already begun.
5. `aiofiles.open()` tries to use the executor after executor shutdown.
6. `write_exchange()` raises `RuntimeError: Executor shutdown has been called`.
7. The temp directory is cleaned up.
8. The index row survives, but the artifacts do not.

This is why a Codex row can exist in `index.jsonl` without a corresponding exchange directory.

Important nuance:

- this is not only an `aiofiles` bug
- it is fundamentally a shutdown-ordering bug
- `aiofiles` is just where the race becomes visible

Any late persistence work that depends on the loop’s executor is vulnerable in that window.

## UI Visibility and Run Scoping

Relevant implementation:

- `api/src/manicure/api/v1/exchanges.py`
- `www/src/api.ts`
- `www/src/hooks/useExchanges.ts`
- `www/src/components/routes/RecallView.tsx`

The exchange list endpoint is run-scoped by default:

- `/api/exchanges` filters by the current `run_id`
- `include_history=true` is required to see prior runs

The current frontend does not request history:

- it always fetches `/api/exchanges?limit=...&offset=...`
- there is no history toggle in the current exchange list flow
- the `Recall` route is still placeholder-only

This means a row can exist on disk and still be invisible after relaunch if it belongs to a prior run.

That was relevant in this investigation because after the failed shutdown persistence, the surviving index row was also easy to miss from the live UI path.

## Workspace Model

Relevant implementation:

- `api/src/manicure/workspace.py`
- `api/src/manicure/manifest.py`

Workspace identity is intentionally path-based, not adapter-based.

Current design:

- workspace identity is derived from canonical working directory
- storage root is `~/.manicure/workspaces/{slug}/{hash}/`
- both `manicure start` and `manicure codex` use the same workspace model
- exchange rows carry `provider` per entry rather than partitioning storage by adapter

So mixed-adapter storage is the intended design today.

This means the current architecture is:

- one project workspace
- one storage root
- one `index.jsonl`
- multiple providers/adapters within that same workspace

There is no current design split like:

- `~/.manicure/workspaces/claude/...`
- `~/.manicure/workspaces/codex/...`

Whether that should change is a product/architecture question, but it is not how the code is structured now.

## Findings Ordered by Severity

### 1. Sensitive transport artifacts can expose auth material

Severity: showstopper

Persisted ChatGPT-authenticated Codex transport metadata currently risks exposing sensitive request headers through disk artifacts, API responses, and the UI.

### 2. Breakpoint release validation is broken

Severity: showstopper

The release path can fail with a server error instead of returning a proper validation response, which breaks the edit-and-forward flow.

### 3. Codex exchanges materialize too late

Severity: showstopper

Codex exchanges are only persisted on websocket close. That is incompatible with the product’s interception contract, because the meaningful unit of work is the initial outbound request frame, not the end of the websocket stream.

### 4. Managed launch inherits proxy and trust env too broadly

Severity: high

Ambient environment leakage means the managed client may not actually be running under the proxy and trust conditions Manicure believes it configured.

### 5. Final Codex persistence can fail during shutdown

Severity: high

When shutdown starts before artifact writes complete, the index can be written without artifacts. This produces inconsistent storage and makes debugging/detail views unreliable.

### 6. Dropped websocket exchanges can still be persisted

Severity: high

A user-discarded Codex request can still appear as a normal stored exchange later at websocket shutdown.

### 7. Prior-run captures can be hidden from the UI

Severity: medium

The list API is run-scoped by default, and the frontend does not expose history yet. A real capture can therefore exist on disk and still be invisible in normal browsing.

### 8. Mixed-adapter behavior is under-tested

Severity: medium

The architecture intentionally supports mixed providers in one workspace, but there does not appear to be a focused test that seeds both Anthropic and Codex rows into the same workspace and validates listing/detail behavior across runs.

### 9. Handshake-failure artifacts are not fully authoritative

Severity: medium

Handshake-failure persistence currently reconstructs response bytes through decoded text, which can be lossy and can fail on non-UTF-8 bodies.

## Recommended Direction

No code changes are proposed in this note, only design direction.

The correct lifecycle for Codex should be:

1. capture the initial client websocket request frame
2. parse it into IR
3. run overrides
4. if armed, pause and allow edits before upstream forward
5. persist a provisional/live exchange immediately
6. show that exchange in the UI immediately
7. on websocket end, update/finalize the same exchange with transport summary and final response stats

Separately, shutdown hardening should make final persistence robust enough that a teardown race cannot leave an index row without artifacts.

Before that lifecycle work lands, the branch also needs immediate hardening on:

1. release validation correctness
2. transport artifact redaction
3. managed child environment sanitation
4. dropped websocket persistence behavior

## Recommended Execution Order

The current work should execute in this order:

1. Fix release validation so invalid edits fail correctly instead of 500ing.
2. Redact or suppress sensitive transport headers in persisted artifacts.
3. Sanitize managed child environment for proxy and trust correctness.
4. Fix dropped websocket requests being persisted as normal exchanges.
5. Preserve raw handshake-failure response bytes.
6. Implement provisional/live Codex exchange persistence at initial request capture.
7. Finalize that same exchange on websocket end instead of creating it only at close.
8. Harden shutdown ordering so persistence cannot leave index rows without artifacts.
9. Restore clean proxy-only `--no-codex` behavior.
10. Tighten websocket release UX and add transport visual coverage.
11. Improve prior-run/history visibility.
12. Add mixed-provider workspace and cross-run coverage.

## Bottom Line

The core issue is not “Codex was not captured.”

Codex was captured.

The actual gap is:

- capture and interception happen at the right moment
- persistence and UI visibility happen at the wrong moment

And then:

- final persistence is vulnerable to shutdown ordering
- surviving rows can also be hidden by run scoping

So the Codex path is not missing raw transport capture. It is missing the correct product lifecycle around that capture.

But it is also not ready for acceptance until the review blockers around validation, auth exposure, launch environment leakage, and dropped-flow persistence are resolved.
