---
title: TM preview performance investigation continuation
type: sessions
tags: [transport-matters, preview, performance, incident, continuation]
summary: Recovered Astra conversation and profiler evidence, with independently reproduced verification queue CPU cost.
status: active
project: transport-matters
created: 2026-09-08
updated: 2026-09-08
---

# Recovery and scope

The conversation and diagnostic evidence have been recovered outside TM. The operator was told the desktop can be closed. Closing it may terminate running agents. No further live application access is required to read this handoff.

The recovered original task explicitly requested diagnosis only and a read only shared checkout. Preserve that boundary until the operator authorizes implementation. This recovery modified no repository files or database state. HEAD was e0ce33a66c0abb19d5da717aba81b4d824a21c5b, with a clean working tree.

The actual run ID is `6853a1d4-06ec-4059-8574-c6538f39eeb5`. The ID pasted into the rescue session was malformed. Native Codex session: `4b1245f0-bba9-4dfd-969b-242dcc08dc83`. TM transcript session: `16df9bcd-cd43-5a2c-8d8d-f3bde9563a04`.

Evidence directory: `/Users/alphab/.mdx/sessions/tm-preview-performance-rescue-evidence/`.

The 734439 byte native transcript and TM transcript matched exactly. All 205 JSONL records parsed, through 2026-09-08T00:03:23.294Z. The last assistant message said the continuation had not been saved and it would try CX. This rescue successfully saved the files instead.

# Evidence preserved

- `transcript.jsonl` and `native-transcript.jsonl`: full conversation, including tool calls and results.
- `conversation.txt`: readable user and assistant messages.
- `sample_stacks.py` and `sample-stacks.results`: original operator supplied sampler and 10.01 second capture, 189 passes.
- `verification-queue/`: copied queue for independent read only reproduction.
- `queue-reproduction.json`: five fresh measurements against the copied queue.
- `desktop.json`, `process-snapshot.txt`, `desktop-log-tail.txt`: live runtime identity, CPU snapshot and final 2 MB of logs at rescue time.
- `sessions.json`, `run-manifest.json`, `checksums.json`: ownership metadata and SHA256 hashes for the original copied files.

The original sampler remains at `/tmp/tm-performance.XtOeB0/sample_stacks.py`; the original results remain at `/tmp/tm-performance.results`. A second copy of this continuation is next to the sampler at `/tmp/tm-performance.XtOeB0/CONTINUATION.md`.

# Findings verified during rescue

## Backend queue consumes half a core while every request is finished

`api/src/transport_matters/launch_verification_queue.py:46` validates every request JSON through `VerificationRequest.model_validate_json`. Its `list` method does this for every retained request. `LaunchVerificationQueue._scan` at line 159 calls that synchronous method on its asyncio loop, then skips finished requests after parsing. The default sleep interval is 0.1 seconds.

The preserved queue contains 13 requests, all finished. Five scans took 121.44, 114.08, 111.67, 116.02 and 112.62 ms wall time. Median CPU time was 114.05 ms. A 114 ms scan plus 100 ms sleep predicts 53.28% of one CPU core. The live rescue snapshot measured backend PID 59710 at 54.0% CPU. This independently reproduces Astra's earlier measurement of 120.4 ms per scan and 56.2% average backend CPU.

Operator supplied stacks include `VerificationRequestStore.read`, Pydantic validation, request schema serialization, digest validation and recursive canonicalization. This corroborates the queue measurement.

The terminal WebSocket bridge in `api/src/transport_matters/api/v1/run_proxy.py:420` and forwarding loops at line 548 execute on the Python backend event loop. Synchronous queue work can therefore delay both input and output forwarding. Exact end to end keystroke delay remains unmeasured.

## Shared proxy repeatedly rebuilds accumulated Codex traffic during streaming

`api/src/transport_matters/addon_handlers.py:394` awaits `rewrite_codex_provisional_exchange` for noninitial, nonterminal server messages when a provisional exchange exists.

`api/src/transport_matters/codex/exchange_derivation.py:357` rereads the index entry and exchange, builds transport artifacts, advances or replays derived state, then persists the exchange before returning. This executes within the proxy message hook.

Operator supplied stacks for PID 59716 show `DiskStorageBackend.read_exchange`, `build_codex_transport_artifacts`, JSON decode and payload canonicalization, transport message fact construction, and `DiskStorageBackend._write_transport_json` through `persist_exchange`. Thirteen samples explicitly show transport serialization and persistence in the rewrite hook; ten show exchange validation and read; other stacks cover accumulated transport reconstruction. The report lists only the top fifteen stacks and includes empty samples, so avoid treating these counts as a complete CPU attribution.

The rescue CPU snapshot measured proxy PID 59716 at 103.8%. Astra's earlier 33 second sample measured 102.5% average. The source and stacks establish expensive work on the streaming forwarding path. An isolated scaling benchmark and a measured before/after fix have not been completed. Do not label quadratic total work as benchmark proven yet.

# Measurements recovered from Astra

These are prior measurements preserved in the transcript, not repeated during rescue except for the queue and instantaneous CPU checks above.

- 33 second sample: proxy 102.5% CPU, backend 56.2%, Electron renderer 12.4%, Node gateway 2.0%.
- Postgres: 15 idle connections, no lock waiters, empty notification queue at observation time.
- 90 health probes: Python endpoint median 114 ms, p95 190 ms; direct Node endpoint median 0.77 ms, p95 0.96 ms.
- Queue JSON totaled about 2.34 MB.
- Terminal output reaches xterm directly. React markdown rendering is not the per chunk terminal path.
- Unrelated processes were also busy. Rescue snapshot included PerfPowerServices around 161% and a VS Code extension process around 99%. They may aggravate responsiveness but do not account for the reproduced TM defects.

# Runtime and recovery notes

Verified runtime descriptor: preview channel, home `/Users/alphab/.transport-matters-preview`, backend PID 59710, shared proxy PID 59716, web listener 8798, configured proxy port 8797, version `0.3.0.post1.dev573+ge0ce33a66`. Only 8798 was observed listening among those two ports during rescue. Do not infer a listener from the descriptor alone.

The transcript search skill's `/api/sessions` example returned HTTP 404. Current source uses `/v1/sessions`. Recovery used the native and snapshot files directly, avoiding any dependence on the overloaded service or database credentials.

Live stack sampling requires macOS task port access. The operator already ran the privileged sampler and supplied its output. No additional sudo request is needed to analyze that capture. The sampler's label says main thread, but its loop iterates every thread returned by RemoteUnwinder; do not assume the label proves thread selection.

# Next work

1. Diagnose the queue polling design so finished history and large immutable pinned schemas are not fully revalidated on every 100 ms idle scan. Preserve startup discovery, concurrent backend correctness, admission, retry and lock ownership.
2. Measure proxy cost against increasing frame counts using an isolated copy or fixture. Establish which repeated parsing, serialization and writes dominate. Preserve breakpoint re-audit, provisional inspection, final artifacts and crash recovery when designing the repair.
3. With implementation authorization, add meaningful regression tests and apply fixes in an isolated worktree. The shared original checkout must remain untouched under the recovered diagnostic scope.
4. Verify real input latency and token forwarding separately from screen painting. A distinct renderer issue remains possible because the main shell renderer was not directly profiled through DevTools.
5. Required implementation delivery proof for this repository is `just check` and `just test`, followed by live preview measurements under comparable load. No code fix or performance resolution is claimed by this recovery.
