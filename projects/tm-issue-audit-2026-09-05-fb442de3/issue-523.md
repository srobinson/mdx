# 523: Harness request audit: publish the captured shapes, build the control matrix, export the corpus

URL: https://github.com/littleorgans/transport-matters/issues/523
State: open
Labels: 
Updated: 2026-09-03T20:24:00Z

## Problem

Transport Matters certification proves request shapes for a controlled probe. Request overlays need evidence for the complete interactive request lifecycle and for the model visible content each harness, runtime, workspace and user action contributes.

Since this issue was written, the capture primitive gained the tool turn and the envelope. Neither has ever been published. The remaining work is therefore narrower and differently shaped than the original body described.

## Already delivered

Cold start facts, current at `6d8e21dc`.

- **The tool turn is a captured shape.** #394 closed through #604. `RequestShape` carries `FIRST_TURN` and `TOOL_TURN` as a coordinate of every cell, and the probe provokes exactly one call to the harness's own shell tool: [baseline_plan.py:33](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/baseline_plan.py#L33). The original claim in this issue, that the capture primitive "rejects multiple completed exchanges for one delivery", no longer holds. The limit now is exactly one tool call, one result and one result request; more fails the probe.
- **The envelope is a captured schema.** #393 delivered `project_request_envelope` and `mint_envelope_schema`, and `GateProjection` carries `envelope_schema` beside the body schema: [transport_envelope.py:84](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/transport_envelope.py#L84), [baseline_projection.py:112](https://github.com/littleorgans/transport-matters/blob/main/api/src/transport_matters/baseline_projection.py#L112).
- **Nothing published uses either.** Across all seven certification records at HEAD: **26 `first-turn` references, zero `tool-turn`, zero `envelope_schema`**. The gate compares what a release carries, so both shapes are currently invisible to it.
- **Empty capture is legible.** #519 closed through #609: a run that captured nothing now says so on the roster.

The gap is publication, not machinery.

## Cut from this issue

**The raw overlay executor follow up is cancelled.** This issue previously ended with "Defer raw request overlay execution to a following issue." That issue should not be opened.

The architecture recommendation reviewed at `6d8e21dc` concludes that a raw semantic executor requires a second per harness parser for roles, tool namespaces, anchors and request classes, duplicating what the adapters already own, and that its one genuine advantage, retaining every unknown JSON value across an edit, is obtained instead by generalizing preserved raw write back. See #384 and the `request schema -> IR -> overlay` contract.

Consequence for this issue: capture evidence no longer has to be shaped for a raw executor's selectors. It has to serve the support gate, the IR coverage declaration and the control matrix.

## What remains

### 1. Dependency: the certification publication

Not owned here. A full `certify --all` run publishes the `tool-turn` and envelope references, and
that run is sequenced ahead of this issue.

It matters here because until a release carries both, a launch at an unknown version compares the
body of one shape and answers for nothing else. Every profile below assumes the gate already grades
two shapes per target. Do not start items 2 through 4 against a manifest that still carries 26
`first-turn` references and nothing else.

### 2. `native-control` matrix

Unchanged from the original scope and still entirely unbuilt. One controlled experiment per harness control, each recording the native flag or config value, interactive or headless applicability, precedence, the actual raw request delta, and whether the control removes model context or only gates execution.

#### Claude

`--system-prompt`, `--append-system-prompt`, `--tools`, `--allowedTools`, `--disallowedTools`, `--disable-slash-commands`, `--safe-mode`, `--bare`, `--mcp-config`, `--strict-mcp-config`, `--setting-sources`

#### Codex

Runtime profile and `-c` overrides, developer instruction configuration, project document discovery, feature flags, plugin configuration, MCP configuration, sandbox and approval controls, web search, model and reasoning effort. Use `codex debug prompt-input` as a provider free diagnostic. Raw captured requests remain the wire authority.

#### Grok

`--system-prompt-override`, `--rules`, `--agent`, `--allow`, `--deny`, `--disable-web-search`, `--no-subagents`, native skill, plugin and MCP configuration, compatible Claude and Cursor source imports, model and reasoning effort. Use `grok inspect --json` as a provider free discovery diagnostic. Grok `--tools` and `--disallowed-tools` are headless only and outside the interactive product path. Record that limitation in the matrix.

### 3. `runtime-overlay` and `interactive-direction` profiles

`runtime-overlay`: launch from a controlled agent runtime with known instructions, skills, MCP configuration, plugins, workdir fixtures and harness configuration, to attribute model visible nodes to the runtime.

`interactive-direction`: capture a controlled lifecycle where a human director interrupts and redirects an active harness. This exists to stop later capture or overlay design from assuming single shot headless execution. Human direction stays a product requirement, and Grok headless mode is not adopted to gain its headless only flags.

### 4. Request class vocabulary

The audit vocabulary must identify at least bootstrap, primary user request, tool continuation, follow up, auxiliary or title generation, human interruption, human redirect, and compaction. A harness version emits several classes, so applicability cannot rest on harness and version alone.

Manual Codex 0.150.1 captures show bootstrap requests carrying tools in an `input` item of `type: "additional_tools"`, primary requests carrying separate developer content nodes for runtime instructions, skills, permissions, collaboration mode and plugin instructions, tool continuations carrying `custom_tool_call_output`, and later turns receiving a different skills inventory from the first. #607 has since lifted top level namespace tools into the IR.

### 5. Capture derived request purpose fixtures

Split out to #611. Raised from #557 and PR #559, it reads the captures this issue produces but
changes no publish path, and it is sequenced ahead of the rest of this issue.

### 6. Public audit export

Immutable versioned audit artifacts for complete interactive turns, with a sanitized public projection. Host the capture history in a separate repository so this one does not grow. Astro on GitHub Pages is the first deployment target. Provider access and capture stay local; public CI validates and publishes committed artifacts without provider credentials.

## Retained product decisions

- Preserve the A/B/A `intrinsic-first-turn` baseline as the structural compatibility baseline.
- Keep manual capture as a supported source of empirical evidence.
- Bind observations to harness, exact harness version, model, effort, capture profile and request class.
- Record complete controlled node content and publish a sanitized projection.
- Defer the choice between harness native controls and raw request overlays until the empirical control matrix exists.
- Do not introduce a byte splicer.

## Suggested sequencing

The two items that were sequenced ahead of this issue have left it. The publication is the certify
run, and the fixtures are #611.

What remains is program sized and starts after both:

1. Item 4, the request class vocabulary, because items 2 and 3 classify against it.
2. Items 2 and 3, the control matrix and the runtime and direction profiles.
3. Item 6, the public export, once there is a corpus worth publishing.

Each should become a child issue when started.


## Comment by srobinson at 2026-08-31T14:04:35Z (updated 2026-08-31T14:04:35Z)

https://github.com/littleorgans/transport-matters/issues/523#issuecomment-5479504649

## Capture derived classifier fixtures

#557 and PR #559 exposed a contract this audit system should own.

Synthetic `make_request_ir()` fixtures prove classifier behavior against shapes we wrote by hand. They do not become stale visibly when a new harness version changes its traffic. The current launch comparison catches structural schema drift, but request purpose also depends on values such as tool presence, token budget, beta headers, and request class. A harness can preserve its schema while changing those values.

Each new audit capture should generate a small, sanitized request purpose fixture keyed by harness, exact version, model, capture profile, and request class. The projection should retain only the request IR and headers read by the provider classifier. Full raw captures remain outside this repository.

The generator needs a check mode. A changed capture projection should fail the check until the fixture and its expected purpose are reviewed. Classifier replay should then assert:

- primary agent requests classify as `True`
- known housekeeping and auxiliary requests classify as `False`
- no captured request class capable of prompt collision rests on `None`

This gives the synthetic unit tests a measured source and a clear invalidation path. It also preserves the structural compatibility baseline while adding the behavioral check #557 needs.

Related: #557 and PR #559.

## Sub issues
[]
