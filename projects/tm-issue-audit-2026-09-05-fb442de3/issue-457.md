# 457: Canvas Overlay: builtin tool enablement via capability library and agent-runtimes [tools]

URL: https://github.com/littleorgans/transport-matters/issues/457
State: open
Labels: enhancement
Updated: 2026-08-25T11:57:14Z

Parent: #455. Depends on: #456 (viewer, as the acceptance surface).

## Outcome

An agent's builtin tool surface is declared per runtime and applied to the wire. Tools the runtime does not enable never reach the provider.

This is the largest single lever in Canvas Overlay: tool definitions are 77% of a claude request (145,491 of 188,341 bytes, ~36k tokens every request), 80% of grok, 54% of codex.

## Three pieces

**1. Capability declaration in agent-runtimes** (new concept in that repo)

`runtime.toml` has `[skills]` and `[mcp]` but no `[tools]`. Add it, following the existing bare-bool convention:

```toml
[tools]
shell     = "v1"    # enabled, our overlay content v1
file-read = true    # enabled, harness's own definition untouched
web-fetch = false   # explicitly disabled
# absent           = not enabled under default:drop
```

Keys are **capability names, not harness tool names**: `shell`, not `bash`, because codex calls it `exec` and grok calls it `run_terminal_command`. One declaration resolves across all three harnesses, exactly as `[skills]` and `[mcp]` already resolve per platform.

Enable-vs-disable is one field, a default plus exceptions. `{default: keep, drop: [...]}` is a denylist; `{default: drop, keep: [...]}` an allowlist. Default `drop` is recommended so savings are deterministic across harness releases; it is only safe once regeneration exists (see #458). Either posture, drift reports tools the overlay has no opinion on.

**2. Tool overlay library**

Our content per tool, authored once and composed by enablement rather than copied into each overlay. Keyed per harness beneath the capability, because schemas genuinely differ. Each entry pins the tool schema digest it was authored against, so certification drift flags a stale entry instead of letting a silent capability loss rot: if claude adds a parameter to Bash and our stored version omits it, the model loses access to it with no signal.

**3. Application**

Resolution at apply time uses the **wire** model, since the addon never sees the launch alias (`launch_fields` does not carry it and wire→launch is many-to-one: `default`, `opusplan`, `sonnet`, `sonnet[1m]` all put `claude-sonnet-5` on the wire). Harness comes from `harnesses:harness_id_for_wire_provider(ir.provider)`.

Two apply points: `addon_handlers:handle_http_request` (claude, grok, codex HTTP fallback) and `handle_codex_websocket_message` (codex production traffic). Byte splicing, never decode-and-reserialize. All-or-nothing per request, failing open with the original bytes.

Tools live in three different homes: claude `/tools[]` (30 flat objects keyed by `name`), grok `/tools[type:function]` (27, keyed by `name`), codex nested inside an `additional_tools` input item. The region locator is authored per wire class and validated against the certified schema.

## Scope discipline

**Dropping unused tools only.** Replacing a kept tool's *content* with a shorter description is a behavioural claim about how the model chooses and calls that tool, and belongs behind evals. This issue ships the subtractive half, which has no behavioural question and carries most of the value.

Per the plane rule: declaration, library, validation and resolution in TypeScript. Python gets only the byte splicer inside the mitmproxy process, with no schema knowledge and no product vocabulary. Overlay state reaches the proxy over the existing control socket, mirroring `SharedProxyManager.set_overrides`.

## Acceptance

- A runtime declaring a reduced `[tools]` set launches with only those tools on the wire, verified by byte-diffing the captured request against the same launch without the overlay: changes confined to the tool region, everything else byte-identical.
- Measured token reduction reported per harness against the certified baseline.
- A capability declared once resolves correctly on all three harnesses.
- A stale library entry (tool schema digest moved) is reported, not silently applied.
- An unresolvable target forwards the original bytes untouched.
- `just check` and `just test` green.

## Note

Prefer configuration over interception wherever the harness offers a knob. `ENABLE_TOOL_SEARCH` is confirmed to defer tool schemas on claude; where an equivalent exists natively it should be used ahead of splicing.

## Comment by srobinson at 2026-08-25T11:57:14Z (updated 2026-08-25T11:57:14Z)

https://github.com/littleorgans/transport-matters/issues/457#issuecomment-5410025265

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]
