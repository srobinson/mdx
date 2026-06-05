---
title: Tier 2 Slice 8 and 9 shared proxy cutover and load test
type: sessions
tags: [backend, transport-matters, tier-2, shared-proxy, load-test]
summary: External API and canvas runs now require the shared proxy, with an opt-in caveated 50-run load harness.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

## Summary

Implemented Tier 2 Slices 8 and 9 on `feat/tier2-slice8-9-cutover-loadtest` and completed the fix round on top of `f9d44c2`.

Key decisions:

- `WEB_RUNTIME_EXTERNAL` runs now require the shared proxy subprocess. If it is unavailable, launch returns `proxy_start_timeout` with a machine readable error rather than using a per-run proxy fallback.
- `WEB_RUNTIME_EMBEDDED` launches still use `prepare_captured_run()`, preserving standalone CLI behavior, per-run storage, breakpoint state, and pause session behavior.
- An explicit embedded regression now proves breakpoint arm, outbound pause, release, and request rewrite after the cutover through the per-run path.
- The heavy shared proxy load harness is opt-in through `cd api && just shared-proxy-load-test --runs 50 --requests-per-run 2 --ws-echo-samples 100 --pool-limit 50` and is outside default pytest collection.
- `NoopTokenCounter` is available behind `TRANSPORT_MATTERS_DISABLE_TOKEN_COUNTER=1` so local load and diagnostic runs avoid upstream token counting.
- The load harness now treats missing CPU samples as indeterminate, logs failed request causes, uses the dispatcher's public shard routing helper, and emits caveats in the verdict.

PR: https://github.com/littleorgans/transport-matters/pull/139
Head after fix round: `ec9c76d`

## API Contract

No public request or response schema changed.

Existing external launch behavior now has stricter failure semantics:

```typescript
// POST /v1/runs
interface CreateRunRequest {
  cli: "claude" | "codex";
  cwd?: string;
  terminal?: { cols: number; rows: number };
  oscColorReplies?: boolean;
  continueFromSessionId?: string;
  idempotencyKey?: string;
  runtimeTemplate?: string;
}

interface ApiError {
  code: "proxy_start_timeout" | string;
  message: string;
  details?: unknown;
}
```

When the shared proxy cannot serve external API or canvas runs, the route returns HTTP 503 with:

```json
{
  "detail": {
    "code": "proxy_start_timeout",
    "message": "shared proxy unavailable: <reason>"
  }
}
```

Embedded CLI launches are not part of this API surface and keep the per-run proxy path.

## Database Changes

No schema or migration changes.

Session writer load behavior was tested through the existing `ShardedCommitDispatcher` path. `commit_shard_index()` is now the public routing helper used by both the dispatcher and the load harness, so the no-HOL probe uses the same shard selection as production code.

## Security Considerations

- External runs fail closed when the shared proxy manager is absent. They do not silently start a per-run proxy outside the canvas control plane.
- The load harness drives local mock upstream traffic only.
- The harness sets `TRANSPORT_MATTERS_DISABLE_TOKEN_COUNTER=1`, which installs `NoopTokenCounter` and clears the process global counter so no Anthropic token count calls or real credentials are needed.
- Existing breakpoint and pause session behavior is preserved for embedded CLI runs and now has explicit post-cutover test coverage.
- Failed harness requests now log exception details with run id, cli, and sequence.

## Performance Notes

Verification on 2026-06-17:

- `cd api && just check && just test`: passed, 1541 pytest items.
- `cd api && uv run python -m pytest src/transport_matters/test_cli_web_control_plane.py src/transport_matters/index/test_tailer_dispatcher.py tests/integration/test_shared_proxy_load_harness_unit.py -q`: passed, 15 tests.
- `cd api && just shared-proxy-load-test --runs 50 --requests-per-run 2 --ws-echo-samples 100 --pool-limit 50`: passed.

Latest load metrics:

- 50 mixed Claude and Codex runs.
- 100 total requests.
- Zero failed requests and zero contamination.
- Capture correctness: 100 entries, 0 missing, 0 wrong run entries.
- Register p95: 96.5 ms.
- Request p95: 937.8 ms.
- Harness loop websocket echo p95: 0.2 ms.
- Session writer HOL: 1 poison session, 49 healthy sessions completed before poison.
- Pool usage max: 50 of 50.
- Shared proxy CPU peak: 223.8 percent.
- Verdict: one shared subprocess saturates around 50 on this host, bounded pool recommended, directional not tight bound.

Harness caveats:

- Terminal websocket echo measures harness event-loop contention and bypasses the proxy.
- Codex forward-proxy traffic uses plain HTTP to the mock origin.
- Requests use a fresh client and connection close, so no keep-alive inflates cold-handshake CPU.

## Open Items

- Decide the bounded shared proxy pool shape and routing key before raising concurrency beyond 50.
- Replace the synthetic websocket echo probe with a direct terminal route latency probe if future load acceptance requires the exact `/v1/runs/{id}/terminal` path under live proxy load.
- Keep the load harness opt-in until runtime, CPU, and local mitmproxy dependencies are acceptable for default CI.
