# Transport Matters Codex spawn performance diagnosis

Date: 2026-06-17

## Summary

The shared proxy path is not the user visible Codex slowdown.

In the empirical probe, the shared proxy listener registration for Codex regular mode completed in 2.93 ms, faster than Claude reverse mode at 5.63 ms. The parent control request, which bounds mode update plus TCP accept readiness plus core binding registration, was 2.43 ms for Codex and 5.12 ms for Claude.

The small Transport Matters delta before PTY handoff is about 99 ms. Codex spawn returned in 121.20 ms, Claude in 22.53 ms. That difference is in context preparation, mostly Codex owned session preparation at 84.54 ms and Codex CA bundle resolution at 10.40 ms.

The large operator visible delay is after Transport Matters spawns the Codex PTY. Codex renders its banner and input composer quickly, then spends time in its own MCP startup. A focused probe saw `Starting MCP servers` at 1.334 s. The full probe still showed Codex MCP startup status after 60 s. The idle Codex run captured no ChatGPT websocket exchange files, only the pre seeded transcript `session_meta`, so idle startup was not waiting on a ChatGPT websocket turn.

Classification: mostly inherent Codex CLI startup, specifically MCP server startup from the copied Codex configuration. Transport Matters can improve clarity and shave about 100 ms, but shared proxy regular mode is not the cause.

## Evidence collected

Commands run, all without code changes:

```text
api/.venv/bin/python /tmp/tm_spawn_perf_probe.py > /tmp/tm_spawn_perf_probe.out 2> /tmp/tm_spawn_perf_probe.err
api/.venv/bin/python /tmp/tm_codex_chunk_probe.py > /tmp/tm_codex_chunk_probe.out 2> /tmp/tm_codex_chunk_probe.err
api/.venv/bin/python /tmp/tm_context_phase_probe.py > /tmp/tm_context_phase_probe.out 2> /tmp/tm_context_phase_probe.err
git status --short
```

Observed exits: all probe commands exited 0. `git status --short` was empty.

Probe artifacts:

```text
/tmp/tm_spawn_perf_probe.py
/tmp/tm_spawn_perf_probe.out
/tmp/tm_codex_chunk_probe.py
/tmp/tm_codex_chunk_probe.out
/tmp/tm_context_phase_probe.py
/tmp/tm_context_phase_probe.out
```

Real run evidence left in Transport Matters storage:

```text
Claude probe run: ~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/7a4084d9-d08c-4a94-a63f-55eb6d136f2f
Codex probe run:  ~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/42a1f042-461a-417d-bb2c-c3cd71a03628
Codex chunk run:  ~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/50a850c1-b1f7-47c6-b638-768875a4e957
```

The Codex probe run had no exchange files after idle startup. Its transcript contained only a `session_meta` line. That matches the conclusion that no ChatGPT websocket turn had started before user input.

## Phase timeline

Shared proxy manager startup was common process startup, not per run: 1.126 s in the probe.

| Phase | Claude | Codex | Delta | Meaning |
|---|---:|---:|---:|---|
| Port allocation | 0.057 ms | 0.124 ms | +0.067 ms | Noise |
| Build captured run context | 9.38 ms | 110.54 ms | +101.16 ms | Small Transport Matters Codex overhead |
| Finish shared preparation | 7.49 ms | 4.25 ms | 3.25 ms faster | Codex not slower here |
| Shared proxy register | 5.63 ms | 2.93 ms | 2.70 ms faster | Regular mode registration was faster than reverse |
| Control request: register listener | 5.12 ms | 2.43 ms | 2.69 ms faster | Bounds mode update plus accept probe plus core registration |
| PTY spawn | 4.88 ms | 5.05 ms | +0.17 ms | Same order |
| `RunManager.spawn` returned | 22.53 ms | 121.20 ms | +98.67 ms | Small pre PTY Codex overhead |
| First terminal output | 676 ms | 497 ms | 179 ms faster | Codex was not slower to first bytes |
| Codex MCP ready | Not applicable | Not observed within 60 s full probe | Dominant visible delay | Codex CLI own startup |

Context subphase probe:

| Context phase | Claude | Codex | Delta |
|---|---:|---:|---:|
| `prepare_launch` | 1.73 ms | 0.56 ms | 1.17 ms faster |
| `prepare_runtime_home` | 7.47 ms | 6.81 ms | 0.66 ms faster |
| `prepare_managed_session` | 0.38 ms | 84.54 ms | +84.16 ms |
| Codex CA resolution | 0 ms | 10.40 ms | +10.40 ms |
| Total context build | 9.71 ms | 102.50 ms | +92.79 ms |

## Source path comparison

Claude invocation path:

* `api/src/transport_matters/captured_claude.py::build_claude_captured_invocation`, lines 92 to 98, builds per run mitmdump argv with `mode=f"reverse:{upstream}"`.
* In shared proxy mode the per run argv is discarded, but the context still carries Claude upstream and `_infer_mode_kind` maps that to reverse mode.
* Lines 110 to 115 build the child env with `ANTHROPIC_BASE_URL` pointing at the proxy URL.

Codex invocation path:

* `api/src/transport_matters/cli/codex_cmd.py::build_codex_invocation`, lines 228 to 235, builds regular mitmdump argv for the legacy per run path.
* In shared proxy mode the per run argv is discarded, but `_infer_mode_kind` maps `cli == "codex"` to regular mode.
* Lines 239 to 245 build the child env with proxy variables and `CODEX_CA_CERTIFICATE`.

Shared proxy mode selection:

* `api/src/transport_matters/shared_proxy/models.py::SharedProxyBindingPayload.mode_spec`, lines 47 to 52, emits `regular@127.0.0.1:{port}` for Codex and `reverse:{upstream}@127.0.0.1:{port}` for Claude.
* `api/src/transport_matters/shared_proxy/models.py::_infer_mode_kind`, lines 183 to 189, chooses `regular` for `cli == "codex"` and `reverse` when an upstream exists.

Shared proxy registration and readiness:

* `api/src/transport_matters/shared_proxy/subprocess.py::SharedProxySubprocess.register_listener`, lines 98 to 111, applies modes, waits for TCP accept readiness, then registers the runtime binding with the shared core.
* `api/src/transport_matters/shared_proxy/subprocess.py::wait_for_tcp_accept`, lines 205 to 210, only tests TCP acceptance on `127.0.0.1:{port}`. It does not perform HTTP CONNECT, TLS, WebSocket, or ChatGPT auth.
* Therefore regular mode readiness cannot include the ChatGPT websocket handshake. The timing proves it is not slow anyway.

RunManager handoff:

* `api/src/transport_matters/run_manager.py::RunManager._spawn_new_admitted`, lines 300 to 319, awaits preparation and then spawns the client PTY.
* In the probe, this returned in 121.20 ms for Codex. Everything after that is inside the Codex process and its terminal output.

Codex specific preparation:

* `api/src/transport_matters/cli/launch_profile.py::CodexLaunchProfile.prepare`, lines 169 to 176, pre seeds a Codex rollout before launch.
* `api/src/transport_matters/cli/codex_session.py::resolve_codex_cli_version`, lines 110 to 117, shells out to `codex --version`. This is the main measured 84 ms Transport Matters Codex preparation cost.
* `api/src/transport_matters/cli/codex_cmd.py::_resolve_codex_ca_certificate_or_exit`, lines 81 to 91, creates or resolves the CA bundle for Codex.

Codex MCP source:

* `api/src/transport_matters/cli/home_overlay.py::_copy_overlay_local_files`, lines 390 to 394, copies Codex `config.toml` into the per run overlay.
* `api/src/transport_matters/cli/codex_home.py::CodexSeeder.seed`, lines 32 to 44, copies auth, relocates hook trust state, and merges project trust. It does not start MCP servers.
* The MCP servers shown by the Codex TUI come from the Codex configuration that Transport Matters copies into the overlay. Codex owns the startup of those servers.

ChatGPT websocket check:

* `api/src/transport_matters/codex/transport.py::is_codex_websocket_flow`, lines 103 to 111, classifies the ChatGPT Codex websocket at host `chatgpt.com` and path `/backend-api/codex/responses`.
* The idle Codex probe produced no exchange directory, only the transcript `session_meta`. No ChatGPT websocket turn was captured during startup.

## Delta classification

### Transport Matters controlled, small

Codex has about 100 ms of extra Transport Matters preparation before PTY spawn:

1. `prepare_managed_session`: 84.54 ms. This includes `codex --version` and rollout seeding.
2. Codex CA bundle resolution: 10.40 ms.
3. The rest is sub millisecond or similar to Claude.

This is real, but it is too small to explain the roadtest complaint.

### Shared proxy controlled, not the problem

Regular mode registration and readiness were faster than Claude reverse mode in this probe. The accept probe is a TCP connect only, not CONNECT or WebSocket. There is no evidence of a shared proxy regular mode penalty.

### Codex inherent, dominant

The visible delay is Codex's own startup after PTY spawn. The TUI output shows MCP server startup status. The focused probe saw the status at 1.334 s and later redraws through 25 s. The full probe still had Codex in MCP startup after 60 s.

The likely blocking units are the configured Codex MCP servers, not ChatGPT auth. This matches the user visible status text: `Starting MCP servers`.

## Ranked improvement options

1. Surface the real phase in the UI. Impact: high clarity. Effort: small. Mark the run as Transport Matters ready when the PTY is spawned, then show a separate Codex client startup state when the terminal output contains `Starting MCP servers`.
2. Cache Codex CLI version per API process. Impact: small, about 80 ms. Effort: small. Replace per spawn `codex --version` with a cached value keyed by binary path and mtime.
3. Cache or reuse the Codex CA bundle per shared proxy manager. Impact: very small, about 10 ms. Effort: small to medium. Must preserve trust correctness when environment changes.
4. Provide a lean Codex runtime template for captured panes. Impact: potentially high. Effort: medium. A template with fewer MCP servers would reduce Codex startup, but changes user capability and must be explicit.
5. Add a Codex prewarm or pool. Impact: high if feasible. Effort and risk: high. It must handle cwd, CODEX_HOME, owned session id, PTY ownership, auth state, and lifecycle isolation.
6. Tune shared proxy regular mode readiness. Impact: negligible. The measured control request was 2.43 ms, so this is not worth pursuing for this report.

## Answer

Mostly inherent Codex CLI startup, specifically MCP server startup from Codex configuration. Transport Matters can make the phase visible and remove about 100 ms of prep overhead, but the shared proxy regular listener path is not the bottleneck.
