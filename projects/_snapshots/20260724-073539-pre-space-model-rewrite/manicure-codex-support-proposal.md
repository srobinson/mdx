---
title: Manicure Codex Support Proposal
type: projects
tags: [manicure, codex, chatgpt, mitmproxy, websocket, proxy, proposal, technical-spec]
summary: Proposal for mainstream Codex support in Manicure, centered on ChatGPT-authenticated websocket traffic over chatgpt.com/backend-api/codex/responses with process-scoped proxy trust.
status: active
project: manicure
confidence: high
created: 2026-04-17
updated: 2026-04-17
---

# Manicure Codex Support Proposal

See `~/.mdx/projects/manicure.md` for product framing and `~/.mdx/projects/manicure-spec.md` for the current core architecture.

## TL;DR

Manicure should support Codex through the path real users actually use: ChatGPT-authenticated Codex CLI traffic to `wss://chatgpt.com/backend-api/codex/responses`.

The transport model is viable. Codex can run through a local HTTPS proxy, trust a process-scoped CA bundle via `CODEX_CA_CERTIFICATE`, and complete a normal `codex exec` session while proxied. This avoids system keychain changes and keeps the trust change local to the spawned Codex process.

API key mode remains useful as an internal validation harness because `openai_base_url` works cleanly there. It should not define the product.

## Product premise

Codex support only matters if it matches normal user behavior. The relevant user path is ChatGPT login, not API key login.

That changes the architectural assumption from the original Manicure plan. Claude support fits a localhost reverse proxy with no client trust changes. Mainstream Codex support does not. Codex needs an HTTPS proxy path plus a process-scoped trust override.

## Findings from transport experiments

### Confirmed facts

1. `openai_base_url` is a real Codex config knob.
2. In API key mode, `openai_base_url="http://127.0.0.1:<port>"` works and Codex successfully uses websocket transport on `/responses`.
3. In ChatGPT-authenticated mode, sending that same traffic to `api.openai.com/v1/responses` fails with `401 Unauthorized`.
4. `chatgpt_base_url` is also a real knob, but in `codex exec` it only redirected auxiliary traffic such as:
   - `/backend-api/plugins/featured`
   - `/backend-api/wham/apps`
   - `/backend-api/codex/analytics-events/events`
5. The actual ChatGPT-authenticated model path for `codex exec` is `wss://chatgpt.com/backend-api/codex/responses`.
6. Without trusting the proxy CA, Codex fails TLS with `UnknownIssuer`.
7. With `HTTPS_PROXY`, `HTTP_PROXY`, and `CODEX_CA_CERTIFICATE` pointed at a merged CA bundle, Codex successfully completes a proxied `codex exec` session through `chatgpt.com/backend-api/codex/responses`.

### Operational conclusion

The real product path is now clear:

1. Mainstream Codex support should target ChatGPT auth on `chatgpt.com`.
2. API key mode should remain available only as an internal test harness and fallback development path.
3. Codex support should be treated as a separate transport mode from Claude, not a thin second adapter on the existing reverse proxy design.

## Proposed support model

### Goal

Ship Codex support that lets a user run Codex normally while Manicure:

1. captures request and response traffic,
2. normalizes request payloads into the internal IR,
3. applies rule pipeline edits,
4. optionally pauses at a breakpoint for manual editing,
5. forwards the edited request upstream,
6. records the resulting response stream.

### Primary mode

Support `codex exec` and interactive Codex sessions launched under a Manicure-managed HTTPS proxy.

The proxy arrangement should be:

1. Manicure starts `mitmdump` in explicit proxy mode on localhost.
2. Manicure generates a merged CA bundle that includes the system roots plus the mitmproxy CA.
3. Manicure launches Codex with:
   - `HTTPS_PROXY=http://127.0.0.1:<port>`
   - `HTTP_PROXY=http://127.0.0.1:<port>`
   - `CODEX_CA_CERTIFICATE=<generated bundle path>`
4. Codex connects to `chatgpt.com/backend-api/codex/responses` through the local proxy.

This keeps the trust boundary process-scoped. No global certificate install is required.

### Secondary mode

Preserve API key transport support behind an explicit development or validation mode:

1. `openai_base_url`
2. API key auth
3. `/v1/responses` websocket transport

This mode is useful for local adapter development, fixture generation, and transport debugging.

## Architecture proposal

### 1. Launch model

Add a Codex-specific launch path instead of forcing Codex into the Claude startup model.

Proposed CLI shape:

```bash
manicure start --client codex
```

or:

```bash
manicure codex
```

Responsibilities of the launch path:

1. start the Manicure API and UI,
2. start `mitmdump` in explicit proxy mode,
3. ensure the mitmproxy CA exists,
4. generate the merged CA bundle,
5. spawn Codex with the required proxy and trust environment,
6. clean up the temporary CA bundle on exit.

### 2. Transport handling

Claude and Codex should use different transport strategies under the same product surface.

| Client | Transport mode | Upstream shape | Trust requirement |
|---|---|---|---|
| Claude | reverse proxy | `https://api.anthropic.com/v1/messages` | none on client |
| Codex, ChatGPT auth | explicit HTTPS proxy | `wss://chatgpt.com/backend-api/codex/responses` | process-scoped CA bundle |
| Codex, API key | reverse proxy or local websocket forwarder | `https://api.openai.com/v1/responses` | none if plain localhost base URL |

The core product can remain provider-neutral at the IR layer while acknowledging that the network transport differs by client.

### 3. Adapter model

The adapter boundary needs to expand from simple request body translation to stream-aware session handling.

Proposed split:

1. `AnthropicAdapter`
   - existing HTTP request and response model
2. `CodexChatGPTAdapter`
   - websocket session handler for `/backend-api/codex/responses`
   - initial `response.create` frame parsing
   - stream event capture
3. `CodexOpenAIAdapter`
   - internal validation harness for `/v1/responses`
   - same IR target, different auth and upstream assumptions

The important design choice is to keep one logical Codex IR mapping while allowing separate transport front doors.

### 4. IR implications

The current IR is biased toward Anthropic request bodies. Codex support requires an OpenAI-style request mapping for the initial websocket payload.

Confirmed top-level shape from captured `response.create` frames includes:

1. `type`
2. `model`
3. `instructions`
4. `input`
5. `tools`
6. `tool_choice`
7. `parallel_tool_calls`
8. `reasoning`
9. `store`
10. `stream`
11. `include`
12. `service_tier`
13. `prompt_cache_key`
14. `text`
15. `client_metadata`

Required IR work:

1. map `instructions` into internal system content,
2. map `input` items into internal messages,
3. map tool definitions into internal tools,
4. preserve unmapped transport or provider fields in `provider_extras`,
5. support round-trip serialization back into the outgoing `response.create` frame.

### 5. Breakpoint semantics

For Codex, the breakpoint should pause after the initial `response.create` payload is captured and normalized, but before the edited frame is sent upstream.

That implies a different hold point from Claude:

1. accept client websocket upgrade,
2. receive the first client text frame,
3. normalize and run pipeline,
4. optionally hold for UI edits,
5. send the edited frame upstream,
6. relay upstream websocket traffic back to the client.

This is still request-side editing. It just happens inside a websocket session instead of a plain POST.

### 6. Storage and artifacts

Codex exchanges should write richer transport artifacts than Claude:

1. client upgrade request headers,
2. upstream upgrade response headers,
3. initial client `response.create` frame,
4. normalized IR snapshot before rules,
5. normalized IR snapshot after rules,
6. edited IR snapshot if breakpoint was used,
7. upstream event stream, either full or summarized,
8. audit metadata describing rule application and byte or token deltas.

The model-facing editor should still operate on the IR, not on raw websocket frames.

## UX proposal

### Desired user flow

```bash
manicure codex
```

Manicure then:

1. starts the local proxy and UI,
2. opens or prints the UI URL,
3. spawns Codex in a child process with proxy env vars already set,
4. captures Codex traffic automatically.

This is the cleanest experience because it avoids asking the user to export proxy variables manually.

### Alternative user flow

For users who want to run Codex themselves:

```bash
eval "$(manicure codex env)"
codex
```

This should print the three required environment variables plus any temporary CA bundle path.

## Scope recommendation

### In scope for Codex V1

1. ChatGPT-authenticated capture for `codex exec`
2. request-side websocket breakpoint on the initial `response.create` frame
3. rule pipeline application to `instructions`, `input`, and `tools`
4. live log entry creation for Codex exchanges
5. process-scoped CA bundle generation
6. explicit proxy launch and cleanup

### Out of scope for Codex V1

1. response-side frame editing
2. every auxiliary ChatGPT endpoint
3. connector-specific request semantics
4. non ChatGPT authenticated desktop or browser Codex variants
5. long-lived session recovery beyond simple reconnect handling

## Risks and open questions

### 1. Upstream contract volatility

`chatgpt.com/backend-api/codex/responses` is a product endpoint, not a stable public API contract. It may change without notice.

Mitigation:

1. keep the adapter loss-tolerant through `provider_extras`,
2. preserve raw frames alongside normalized IR,
3. maintain a fixture corpus from real captures.

### 2. Auxiliary service traffic

Codex also calls side endpoints such as plugins, app discovery, analytics, and related service surfaces. Some of these may be required for a complete session.

Mitigation:

1. start with pass-through support for auxiliary traffic,
2. focus editing only on `/backend-api/codex/responses`,
3. expand coverage later if a required dependency emerges.

### 3. Trust bundle portability

The merged CA bundle approach worked locally. It should be validated across macOS and Linux before it becomes the default.

Mitigation:

1. centralize bundle generation,
2. test on at least one Linux environment,
3. offer diagnostics when trust bootstrap fails.

### 4. Interactive session behavior

`codex exec` is the cleanest first target. Fully interactive Codex sessions may have additional reconnect, keepalive, or side channel behavior.

Mitigation:

1. ship against `codex exec` first,
2. expand test coverage to interactive mode next,
3. log reconnect behavior explicitly.

## Implementation plan

### Phase 1. Transport bootstrap

1. add a Codex launcher path in the CLI,
2. add CA bundle generation and cleanup,
3. add explicit proxy startup for Codex mode,
4. add child-process environment injection for Codex.

### Phase 2. Minimal pass-through capture

1. detect `/backend-api/codex/responses`,
2. capture websocket upgrade metadata,
3. capture the initial client `response.create` frame,
4. forward unchanged traffic upstream,
5. record artifacts to disk.

### Phase 3. IR round-trip

1. implement Codex request parsing into IR,
2. implement loss-tolerant serialization back to `response.create`,
3. add fixture-based round-trip tests.

### Phase 4. Pipeline and breakpoint

1. run existing subtractive rules on Codex IR,
2. hold and release the initial request frame from the UI,
3. show byte and token deltas.

### Phase 5. Product hardening

1. validate on interactive Codex sessions,
2. improve reconnect handling,
3. add diagnostics for trust and proxy failures,
4. document the architecture and support boundaries.

## Recommendation

Proceed with Codex support as a distinct transport mode centered on ChatGPT-authenticated websocket traffic. Keep the existing provider-neutral IR strategy, but stop assuming that all providers fit the same network pattern.

The critical product insight from the experiments is simple: Codex support is viable, but only if Manicure owns the launch path, proxy configuration, and process-scoped trust bootstrap for the Codex child process.

That is the right V2 path for `manicure`.
