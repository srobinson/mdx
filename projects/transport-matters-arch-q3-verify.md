# Transport Matters architecture Q3 verification

Date: 2026-05-28
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
Scope: Q3 only, Gemini CLI, OpenCode CLI, descriptor refactor, layout feasibility.

## Verdict

Corrected.

The core descriptor finding is right for launch behavior: `HarnessDescriptor` does not drive the current process launch path. `start_cmd.py` and `codex_cmd.py` hardcode proxy mode, trust bootstrap, and child environment policy.

Two corrections matter:

* The claim that descriptor data is consumed only by `api/v1/meta.py` is too narrow. The backend only uses it to build `/api/meta`, but the frontend API client also forwards `harnesses` from that response at `www/src/api.ts:313-330`. I found no active frontend behavior keyed by those fields beyond transport and typing.
* The “4 to 5 central files per CLI” count is accurate for a new wire protocol such as Gemini. It overstates a reuse only OpenCode path if OpenCode truly speaks `/v1/messages`, because `adapters/__init__.py` would not need an edit. If desktop launch support is in scope, add `desktop/src/backendProcess.ts` to the central touch points.

Verification run: `fmm validate` passed for all 352 indexed files.

## 1. Onboarding touch points

Confirmed with nuance.

### CLI registration

`cli/__init__.py` is a central edit point. It imports current launch functions at `api/src/transport_matters/cli/__init__.py:45-58`, defines the `claude` command at `api/src/transport_matters/cli/__init__.py:190-327`, and defines the `codex` command at `api/src/transport_matters/cli/__init__.py:330-460`. A new CLI subcommand needs a new Typer command plus command specific options or a generic command factory.

### Help text

`cli/help.py` is a central edit point. The root help hardcodes `claude` and `codex` at `api/src/transport_matters/cli/help.py:32-34`, the per command help blocks are hardcoded at `api/src/transport_matters/cli/help.py:59-168`, and `_SUBCOMMAND_HELP` maps command names at `api/src/transport_matters/cli/help.py:229-236`.

### Harness registry

`harnesses/__init__.py` is a central edit point. The descriptor type owns launch metadata fields at `api/src/transport_matters/harnesses/__init__.py:53-67`, the current Claude descriptor is `api/src/transport_matters/harnesses/__init__.py:78-102`, the current Codex descriptor is `api/src/transport_matters/harnesses/__init__.py:104-128`, and the registry tuple is `api/src/transport_matters/harnesses/__init__.py:130-136`.

### Adapter registry

`adapters/__init__.py` is a central edit point only when adding a new adapter. It imports `AnthropicAdapter` and `CodexAdapter` at `api/src/transport_matters/adapters/__init__.py:11-13`, then registers concrete adapter instances in `_adapters` at `api/src/transport_matters/adapters/__init__.py:16-19`. A Gemini wire adapter needs this edit. OpenCode does not if it can use `AnthropicAdapter` unchanged.

### WebSocket providers

A second WebSocket provider would hit central addon files unless the websocket hooks are generalized first.

`addon.py` imports Codex websocket handlers and flow predicates at `api/src/transport_matters/addon.py:13-24`; every websocket message is sent to `handle_codex_websocket_message` at `api/src/transport_matters/addon.py:76-77`; every websocket end is sent to `handle_codex_websocket_end` at `api/src/transport_matters/addon.py:79-80`; error handling is also Codex specific at `api/src/transport_matters/addon.py:88-94`.

`addon_handlers.py` imports Codex exchange and transport helpers at `api/src/transport_matters/addon_handlers.py:10-27`, handles Codex websocket messages at `api/src/transport_matters/addon_handlers.py:151-242`, handles Codex websocket close at `api/src/transport_matters/addon_handlers.py:245-283`, and handles Codex handshake failure at `api/src/transport_matters/addon_handlers.py:296-297`.

### Desktop launcher caveat

The draft count omits desktop. If “onboard CLI” includes desktop launch support, `desktop/src/backendProcess.ts` is another central file: supported clients are hardcoded at `desktop/src/backendProcess.ts:5-6`, and the backend launch command passes `options.client` as the first `transport-matters` argument at `desktop/src/backendProcess.ts:65-80`. Unsupported clients are rejected at `desktop/src/main.ts:238-247`.

## 2. Descriptor load bearing status

Confirmed for launch: decorative.

The backend serializes descriptors through `HarnessDescriptorResponse.from_descriptor` at `api/src/transport_matters/api/v1/meta.py:65-81`, then returns every descriptor from `/api/meta` at `api/src/transport_matters/api/v1/meta.py:105-112`.

The frontend API client reads that payload and forwards `raw.harnesses` at `www/src/api.ts:313-330`. That makes “only consumed by meta.py” too strict. It remains informational for launch because the CLI path never reads the descriptor registry.

Current launch code duplicates descriptor data by hand:

* Claude reverse proxy mode is built directly into the mitmdump argv with `reverse:{upstream}` at `api/src/transport_matters/cli/start_cmd.py:124-134`.
* Claude child environment directly injects `ANTHROPIC_BASE_URL` at `api/src/transport_matters/cli/start_cmd.py:140-143`.
* Codex explicit proxy mode is built directly into the mitmdump argv with `regular` mode at `api/src/transport_matters/cli/codex_cmd.py:208-218`.
* Codex child environment directly passes proxy URL and `CODEX_CA_CERTIFICATE` at `api/src/transport_matters/cli/codex_cmd.py:224-240`.
* Codex trust bootstrap directly resolves or creates the CA bundle at `api/src/transport_matters/cli/codex_cmd.py:72-140`.
* Codex shell environment excludes are hardcoded into command arguments at `api/src/transport_matters/cli/codex_cmd.py:174-176` and applied at `api/src/transport_matters/cli/codex_cmd.py:234-237`.

The descriptor tests assert the data surface, but no launch code consumes it. The grep check found descriptor and field references in `harnesses`, `api/v1/meta.py`, tests, and the separate Codex CLI shell policy helper. No current launch path calls `list_harness_descriptors()` or `get_harness_descriptor()`.

## 3. Harness and adapter decoupling

Confirmed.

The adapter registry does flow based selection only. `get_adapter(flow)` iterates registered adapters and calls `adapter.matches(flow)` at `api/src/transport_matters/adapters/__init__.py:22-32`. It receives no harness id and no launch descriptor.

HTTP request handling follows the same boundary. `handle_http_request()` classifies Codex HTTP fallback first, filters for `/v1/messages` or Codex HTTP, then calls `get_adapter(flow)` at `api/src/transport_matters/addon_handlers.py:66-80`. The later request state stores the selected adapter at `api/src/transport_matters/addon_handlers.py:97-110`.

The adapter matches are provider wire signatures:

* `AnthropicAdapter.matches()` accepts paths starting with `/v1/messages` at `api/src/transport_matters/adapters/anthropic.py:55-56`.
* `CodexAdapter.matches()` accepts Codex websocket or Codex HTTP Responses fallback at `api/src/transport_matters/codex/adapter.py:23-26`.
* Codex transport matching is host plus path based for `chatgpt.com` and `/backend-api/codex/responses` at `api/src/transport_matters/codex/transport.py:105-113`, with HTTP fallback discriminated by method and `Upgrade` header at `api/src/transport_matters/codex/transport.py:116-130`.

OpenCode reuse is feasible if OpenCode speaks Anthropic Messages over `/v1/messages`. The existing Anthropic adapter does not constrain host, so the harness and command are the main work. Caveat: the IR provider remains `anthropic` because `AnthropicAdapter.name = "anthropic"` at `api/src/transport_matters/adapters/anthropic.py:50-51`. A distinct OpenCode provider identity would need an adapter wrapper or provider metadata change.

Gemini needs a new HTTP adapter. The current registry only matches Anthropic Messages and Codex ChatGPT flows, so a `:generateContent` flow has no current adapter path.

## 4. Layout and import DAG

The proposed `providers/<name>/` layout is feasible only with strict submodule boundaries. Physical colocation alone is acceptable. A single package import that reexports descriptor, launch code, adapter, and websocket transport would erode the import DAG and could create cycles.

The current adapter layer is low in the DAG. `adapters/anthropic.py` imports `ProviderAdapter` and `ir` at `api/src/transport_matters/adapters/anthropic.py:13-30`. `codex/adapter.py` imports `ProviderAdapter`, Codex wire helpers, Codex transport predicates, and IR types at `api/src/transport_matters/codex/adapter.py:7-18`. Current CLI launch modules import CLI launch plumbing and do not import adapters or harness descriptors, as shown in `api/src/transport_matters/cli/start_cmd.py:13-26` and `api/src/transport_matters/cli/codex_cmd.py:16-36`.

A safe shape:

```text
transport_matters/
  adapters/
    registry.py
  providers/
    anthropic/
      adapter.py
      wire.py
    codex/
      adapter.py
      transport.py
      wire.py
    gemini/
      adapter.py
      wire.py
  harnesses/
    descriptors.py
    registry.py
  cli/
    launch.py
    harnesses/
      claude.py
      codex.py
      opencode.py
      gemini.py
```

Rules for that shape:

* Adapter modules may import `ir`, `adapters.base`, and provider wire helpers.
* Adapter registry may import provider adapter modules only.
* Harness modules may import descriptors, CLI launch runtime, trust helpers, and provider constants that are free of adapter imports.
* Harness registry may import harness modules only.
* Provider package `__init__.py` should be empty or metadata only. It should not import both adapter and CLI launch modules.

A simpler and safer alternative keeps the current horizontal layout: `adapters/gemini.py`, `harnesses/gemini.py`, and `cli/harnesses/gemini.py`. That avoids vertical package import temptation while still reducing shared edits through registries.

## 5. Migration cost and Codex risk

The draft estimate of 1 to 2 days is plausible only for a narrow descriptor driven launch refactor with no desktop work and no broad file relocation. I would plan 2 to 3 focused days for a safe migration because:

* `start_cmd.py` is 261 LOC and `codex_cmd.py` is 403 LOC, with different launch behavior.
* `launch_runtime.py` already holds 376 LOC of shared launch plumbing, so the elegant path is parameterizing existing primitives rather than replacing them.
* Codex has several behavior specific branches: explicit proxy mode, CA bundle generation, `shell_environment_policy.exclude`, `--force-http-fallback`, proxy only hints, and WebSocket plus HTTP fallback capture.
* CLI tests are broad: `api/src/transport_matters/cli/` includes print command, acceptance, storage, validation, pass through, child process, and Codex specific tests.

Risk to the released Codex path is moderate. The risky surface is not adapter parsing, it is process launch semantics and trust material. A staged migration reduces that risk:

1. Add characterization tests for current `transport-matters claude --print-command`, `transport-matters codex --print-command`, Codex CA behavior, shell policy args, and proxy only hints.
2. Make descriptors load bearing inside current command files, keeping external command names stable.
3. Extract generic launch after parity tests pass.
4. Move files or introduce auto discovery only after behavior parity is locked.
5. Add OpenCode first if it reuses `/v1/messages`; add Gemini after the adapter registry shape is settled.

Recommended gate after implementation: `fmm validate`, then `pytest api/src/transport_matters/cli api/src/transport_matters/harnesses api/src/transport_matters/adapters`, plus desktop tests if desktop client support is part of the change.
