# 455: Canvas Overlay: control the system prompt and builtin tool surface per harness

URL: https://github.com/littleorgans/transport-matters/issues/455
State: open
Labels: enhancement
Updated: 2026-08-25T11:57:12Z

Parent: #381. Related: #392 (raw→IR hardening, parked behind this), #454 (grok serializer defect), #384.

Full record of the design session of 2026-08-25. Supersedes the first draft of this issue; `docs/plans/RAW-OVERLAY-PLAN.md` (branch `docs/raw-overlay-plan`) holds the delivery detail and needs a pass to match the scope below.

## What Canvas Overlay is

A Canvas Overlay changes what the harness puts on the wire, for two regions only:

1. **System prompts and system messages** — disable or replace.
2. **Builtin tools** — disable or replace.

Nothing else. No metadata, sampling, thinking config, reasoning, output_config, context management. The goal is token optimization and control of the agent's tool surface, and everything outside those two regions is noise.

## The measurement that sets the scope

Measured from the certified captures (claude 2.1.241, codex 0.149.1, grok 1.0.5, first probe of each class representative):

| harness | body | system prompt | tools | injected system | real user | untouched meta |
| --- | --- | --- | --- | --- | --- | --- |
| claude | 188,341 | 29,891 (15.9%) | **145,491 (77.2%)** | 11,313 (6.0%) | 25 | 1,621 (0.9%) |
| codex | 56,680 | 23,138 (40.8%) | **30,359 (53.6%)** | 491 (0.9%) | 25 | 2,667 (4.7%) |
| grok | 44,268 | 6,057 (13.7%) | **35,569 (80.3%)** | 2,065 (4.7%) | 52 | 525 (1.2%) |

Prompt + tools + injected system is **95–99%** of the request body. What is excluded is under 1% on claude and grok.

**Tools dominate.** Claude ships 145KB of tool schemas (~36k tokens) on every request. Controlling which builtin tools an agent has is the single largest lever, which is why it leads delivery.

## Where the content actually lives

- **claude**: `system[]` is 3 parts (70 / 57 / **29,764** chars). The big part is a monolith with 19 markdown sections; runtime content is *inside* the string ("Types of memory" alone is 7,217 chars). Tools are 30 flat objects in `/tools[]` keyed by `name`. Two injected system surfaces: the first content block of `messages[0]` (593 chars, `<system-reminder>`) and a `role: system` message (10,720 chars, the **agent catalog**). Both are confirmed schema branches (`role:literal:system`, `role:literal:user`).
- **codex**: `/instructions` is empty in practice; the prompt is `input[]` items with `role: developer` (17,730 chars) plus runtime blocks cleanly split into their own content parts with XML anchors (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`). `/tools` is empty — tools live nested in an `additional_tools` input item.
- **grok**: `input[]` with `role: system`, content a **plain string** (6,057 chars). 27 tools in `/tools[type:function]` keyed by `name`.

Consequence: the same product noun has three different homes, so the region locator is authored per wire class and validated against the certified schema, never derived.

## Decisions taken

- **Raw, never IR, on the write path.** The IR write path reserializes whole bodies and is already fidelity-broken for grok (#454). The IR stays the read model (Canvas, transcripts, counting) and raw→IR hardening (#392) continues on that basis.
- **Wire class is the unit.** Structural equivalence partitions each release's reference schemas: claude 2, codex 2, grok 1. Five classes today. Class identity is structural (`compare_request_schema` EXACT), **never `request_schema_digest`** — verified, one claude class carries two digests because `opusplan` and `sonnet` differ only in tools enumerated at capture (84 vs 90).
- **Class schemas come from the shipped manifest** (`compatibility_releases_v1.json` `references[]`), not from local baseline bundles, which exist only on a machine that ran a certification capture.
- **Editing happens AT opaque roots.** `_inside_opaque` is strictly-below, so an opaque root survives minting as an editable leaf, and those roots are exactly the product surface. Removing a tool is a structural array-member removal and is *not* an opaque-root edit.
- **The schema is a locator, not a conformance check.** An overlay is a deliberate deviation from what the harness sends. The schema tells us where things are and whether our targets still exist.
- **Fail open, all or nothing.** Per NOW.md: a miss forwards the original bytes untouched, never half-overlaid.
- **TypeScript by default.** Artifact, catalog, validation, resolution and UI in TS. Python only for what must run inside the mitmproxy process: a dumb matcher and byte splicer with no schema knowledge and no product vocabulary. Application is **byte splicing**, not decode-and-reserialize (every writer in the codebase sorts keys).
- **Canvas, not Inspector.** Inspector's existing Overlays route stays and is improved separately; IR→Inspector Overlay is parked.

## Overlay content has two halves, and one depends on the other

- **Fixed content replacement** — static text we author, replacing a block.
- **Runtime generated content** — rendered from the overlay's own decisions. Claude's 10,720-char agent catalog is derived from what agents/tools exist; disabling a tool while leaving the prose that teaches it produces a lying prompt.

**Subtraction without regeneration degrades the agent.** The two halves ship together. Generation runs in TS when the decision changes (not per request) and the proxy verifies the request's actual tool set matches what the render assumed, failing open on mismatch.

Generation inputs include the platform, not only the tool set: shell, OS, available binaries and paths differ per machine, so the same overlay renders different text on macOS and Linux.

## Tool control model

A single tool overlay library, authored once, composed by per-runtime enablement:

- **Library**: our content per tool, keyed per harness because schemas genuinely differ. Each entry pins the tool schema digest it was authored against, so certification drift flags stale entries rather than letting a silent capability loss rot.
- **Enablement**: declared per runtime in agent-runtimes, **capability-level** (`shell`, not `bash`), so one declaration resolves across claude/codex/grok exactly as `[skills]` and `[mcp]` already do.
- **Gap to close**: agent-runtimes has `[skills]` and `[mcp]` but no `[tools]`. That is a new concept in that repo.
- **Enable vs disable is one field**, a default plus exceptions: `{default: keep, drop: [...]}` is a denylist, `{default: drop, keep: [...]}` an allowlist. Recommended default is `drop` (allowlist) so savings are deterministic; only safe once generation exists. Either way drift reports "N tools appeared your overlay has no opinion on".
- **Versioning**, following the `[mcp]` bare-bool convention:
  ```toml
  [tools]
  shell     = "v1"    # enabled, our overlay v1
  file-read = true    # enabled, harness content untouched
  web-fetch = false   # explicitly disabled
  # absent           = not enabled under default:drop
  ```
- **Risk split**: dropping unused tools is a pure win with no behavioural question. Replacing a kept tool's content is a behavioural claim and belongs behind evals.

## The mechanism boundary

**An overlay can subtract and rewrite. It cannot add executable capability.** The harness executes tools locally, so a tool we invent has nothing behind it. Adding capability is the MCP layer's job. Enforcement (sandboxing, approval policy) is the runtime's job. Three mechanisms, three owners:

- prefer **configuration** where the harness offers a knob (MCP servers, skills, `ENABLE_TOOL_SEARCH`)
- use **overlay** for what has no knob (builtin tool schemas, system prompt, injected system messages)
- use **MCP** to add anything genuinely new

Open empirical question: does a provider accept a `tool_use` for a tool that was not declared in the request's `tools` array? If yes, stripping schemas plus an MCP `describe_tool` reimplements `ENABLE_TOOL_SEARCH` for every harness, since the harness's executor still implements the tool.

## Evidence from the codex runtime (first-hand, 2026-08-25)

Asked a live codex-runtime agent how `exec` works in practice. Findings, verified against our capture where checkable:

- **Codex does not have three tools.** It has three *top-level* tools, and `exec` carries a **26,383-character description** (87% of codex's tool payload) documenting a nested API: `apply_patch`, `exec_command`, `write_stdin`, `update_plan`, `view_image`, `web__run`, MCP resource access, goal lifecycle. Tool definitions moved from structured schemas into prose.
- **The saving is still real**: 30,359 vs claude's 145,491 tool bytes (4.8×); whole request 56,680 vs 188,341 (3.3×), with a *smaller* system prompt.
- `exec` is a **fresh V8 isolate per call**, no filesystem or network API, state only via explicit `store`/`load`. The persistent node REPL is a separate MCP tool. Shell work goes through nested `exec_command`, returning a `session_id`; `wait` resumes a yielded JS cell, `write_stdin` polls a live shell session.
- **Costs**: three quoting layers (JS → JSON → shell) drive retries; no typed intent, so inspection and destruction look identical to policy; parsing human-oriented stdout burns tokens; portability depends on shell/OS/PATH/binaries; broad commands flood and truncate, hiding the decisive error.
- **A structured edit primitive is load-bearing.** Its own system prompt forbids `sed -i` and requires `apply_patch`.
- **Transplanting needs the execution environment and result protocol, not the schema**: sandbox and approval policy, known cwd plus explicit `workdir`, shell/PATH/binary guarantees, process lifecycle (session id, polling, stdin, PTY, cancellation), output shaping (token limits, truncation markers, chunking), safety teaching *with enforcement below the model*, a structured edit primitive, verification guidance.
- **Suggested eval boundary**: a small kernel rather than pure exec — exec + structured patch + async process control + explicit user interaction + typed media/web where shell cannot preserve semantics.
- **Measurement warning**: count total request **and response** tokens plus behavioural success, not tool-definition bytes. Cost moves into the system prompt, command construction, stdout and retries.

Useful consequence for us: **codex's entire tool surface is one editable string**, the easiest overlay target of the three, where claude's is 30 separate objects.

## Back pocket: a portable exec kernel

Not scheduled. Recorded so the option is not re-derived.

[`just-bash`](https://github.com/vercel-labs/just-bash) (Vercel Labs, beta) is a virtual bash environment with an in-memory filesystem, written in TypeScript for agents. It answers most of codex's transplant checklist by **dissolving the OS from the contract** rather than teaching it: commands are implemented in TS, so the same `sed`, `grep`, `jq`, `awk` behave identically on every machine, and GNU vs BSD, missing binaries, PATH and locale all disappear. Filesystem classes are the policy boundary (`InMemoryFs`, `OverlayFs` = reads real disk / writes to memory, `ReadWriteFs`, `MountableFs`), network is off by default with URL and method allow-lists, and `defineCommand` would let us add a structured `apply_patch` in TS. Core shell also runs in the browser, so Canvas could preview a kernel's behaviour client-side.

Gaps and caveats:

- **No process lifecycle**: exec-and-return only, no session id, no `write_stdin`, no PTY. Dev servers, test watchers and anything streaming have no equivalent.
- **No VM isolation** (their words): hardened against prototype pollution, but a policy boundary rather than a hard one against a hostile agent. They point to [Vercel Sandbox](https://vercel.com/docs/vercel-sandbox) for a full VM with arbitrary binary execution — the natural companion when hard isolation or real binaries are required.
- Real edits need `ReadWriteFs`, which spends much of the sandbox benefit. `OverlayFs` is the interesting middle for exploration and planning.
- Beta software.

**Benchmarked against this repo (api/, ~850 Python files) on 2026-08-25**, OverlayFs over the real tree, output identical to native in every case:

| operation | just-bash | native | ratio |
| --- | --- | --- | --- |
| read file slice (`sed -n`) | 6ms | 7ms | 0.8× |
| list files (`find` + `wc`) | 248ms | 199ms | 1.2× |
| **grep** (`grep -rn`) | 142ms | 87ms | 1.8× |
| count lines (`xargs wc`) | 49ms | 21ms | 2.3× |
| **rg** (`rg -n`) | 3,700ms | 40ms | **93×** |

Verdict: performance is a non-issue **except for `rg`**, which is consistently ~26× slower than `grep` doing the identical job *inside just-bash itself* — an implementation quirk, not a limit of the approach. Since we would own the kernel's prose contract, the mitigation is simply not to document `rg`.

## Sequencing

Tool control is the priority; it carries most of the value on its own.

1. **#456** — read-only Canvas surface showing the raw request per harness wire class. Uses data we already ship. Identifies runtime-generated content visually and is the acceptance surface for everything after.
2. **#457** — capability library, agent-runtimes `[tools]`, enablement applied to the wire.
3. **#458** — re-render runtime prompts from the tool decision so subtraction never leaves lying prose.
4. **#459** — back-pocket exec kernel, gated on evals.

## Open questions

- Overlay scope: this issue treats an overlay as global per (harness, class). NOW.md places overlays in the launch specification (`FrozenLaunchSpec` / `candidate_key`), where N candidates differing by overlay is the same verb as N differing by model. **"When to apply an overlay" is explicitly still open** and decides the storage and API shape.
- Does a provider accept a `tool_use` for an undeclared tool (see mechanism boundary)?
- End-to-end token comparison (kernel vs native tools, same task, counting retries) needs either the overlay or a standalone agent loop; request-byte savings alone would be misleading.

## Comment by srobinson at 2026-08-24T20:04:22Z (updated 2026-08-24T20:04:22Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5400666941

Delivery plan drafted at `docs/plans/RAW-OVERLAY-PLAN.md` (branch `docs/raw-overlay-plan`), corrected after an architect review round that found six blockers. The corrections changed the design materially; recording them here so the issue body is not read as current:

1. **Source of truth is the shipped manifest, not the local baseline store.** The issue implied minting class schemas from certified bundles. That evidence exists only on a machine that ran a certification capture (verified: no `baselines` directory in the stable or dev home). Classes come from `compatibility_releases_v1.json` `references[]`, which ship schemas and digests in the wheel. Consequences to carry: releases before the current three have `references: []`, and there is no dev channel state, so overlays are dark on dev.
2. **Class identity is structural, never `request_schema_digest`.** Verified: one claude class carries two digests. `opusplan` and `sonnet` are structurally identical and differ only in `observation_count` at `/tools` (84 vs 90 tools enumerated at capture). Pinning an overlay to a digest would judge it stale for a member of its own class.
3. **Editing happens AT opaque roots.** `_inside_opaque` is strictly-below, so an opaque root survives minting as an editable leaf. Those roots are exactly the product surface: claude `/system[type:text]/text`, `/tools[]/description`; codex `/instructions`, `/tools[type:*]/description`. The first draft had this inverted and would have locked the entire feature.
4. **The comparator's pointers cannot address one location.** `_child_pointer` appends property keys only, array branches are carried in a `branch_tag` overwritten per level, and indices are absent: `/tools/description` names all ninety tool descriptions. The plan introduces a real `SchemaAddress` (property / branch / member selector incl. `where(key,value)`) plus a resolver with an explicit cardinality contract. This is what makes the value-addressed IR verbs expressible.
5. **Application is byte splicing, not decode-and-reserialize.** Every writer in the codebase sorts keys, so a round trip re-emits and reorders the whole body, failing this issue's own acceptance criterion.
6. **Fail open, all or nothing.** Per NOW.md: a miss forwards the original bytes untouched rather than applying a partial overlay.

Also folded in: two apply points (codex production traffic is WebSocket; the `--force-http-fallback` body is not described by the certified class), precedence against the downstream IR pipeline, class resolution by wire model (the addon never sees the launch alias), propagation to the proxy subprocess over the existing control socket, and the form seeded from the operator's own captured exchange since the release ships schemas without bodies.

New finding, sibling of #454: grok's message content is a plain string at `/input[type:message]/content` with `opaque=false`, because the RESPONSES opaque roots assume codex's array-of-parts shape. Grok's prose is classified differently from codex's identical prose. Noted for the gate owner, not handled by this plan.

Three decisions are left open for the owner in the plan: plane ownership for the artifact store and CRUD (ARCHITECTURE.md says new product contexts do not extend the Python plane), overlay scope (global vs the launch-specification scoping NOW.md describes), and whether the shipped-but-inert Inspector Overlays route is hidden or accepted as a duplicate.

## Comment by srobinson at 2026-08-25T11:56:34Z (updated 2026-08-25T11:56:34Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5410018564

## Experiment, 2026-08-25: the two verbs are already available on claude as CLI flags

Captured claude's real request bytes at three configurations by pointing `ANTHROPIC_BASE_URL` at a local sink that records the body and returns 500. **Zero provider spend.** All three arms are `-p` (sdk-cli entrypoint), so they are directly comparable.

| configuration | total | tools | system | messages |
| --- | --- | --- | --- | --- |
| `claude -p` (default) | 114,619b | 21 (56,991b) | 27,856b | 28,664b |
| `--tools ""` | 123,737b | 86 MCP (87,062b) | 26,990b | 8,588b |
| `--tools "" --strict-mcp-config --mcp-config empty --system-prompt "..."` | **5,717b** | **0 (2b)** | **203b** | 4,859b |

**A 20× smaller request, achieved with pure configuration and no overlay machinery.**

The flags that do it:

- `--tools <names...>` — "Specify the list of available tools from the built-in set. Use `""` to disable all tools, `default` to use all tools, or specify tool names." Confirmed on the wire: every builtin disappears.
- `--system-prompt <prompt>` — replaces the system prompt outright. Claude's 27,720-char prompt became our 67 chars. Two parts survive and are not removable by flag: the 74-char billing header and a 62-char "You are a Claude agent, built on Anthropic's Claude Agent SDK."
- `--strict-mcp-config --mcp-config <file>` — only the MCP servers we name.

### The subtle finding: deferral is itself a builtin tool

`--tools ""` alone made the request **bigger** (123,737 vs 114,619). Cause: `ToolSearch` and `DeferredToolPlaceholder` are *builtin* tools, so disabling all builtins disables MCP tool deferral, and all 86 MCP tool schemas inline. Under the default config only 21 tools ship because deferral is doing the work.

Consequence: "disable all builtins" can cost tokens unless MCP tools are also constrained. The two levers interact and must be reasoned about together.

### What this changes

For **claude**, the wholesale form of both Canvas Overlay verbs is already available natively, and per the mechanism-boundary rule (prefer configuration over interception) we should use the flags rather than splice.

The overlay's remaining value on claude is **granularity**, which the flags cannot express:

- keep a tool but replace its content (`--tools` is include/exclude only)
- keep the system prompt but drop or replace one section (`--system-prompt` is wholesale)
- regenerate derived prose (#458) to match a partial tool set

For **codex** there are no equivalent flags at all, and for **grok** there is only `--disallowed-tools` (a denylist, no allowlist, no prompt replacement). So cross-harness parity remains overlay work.

### Unblocked

The `just-agent` experiment (#(just-agent)) needs no overlay machinery. The only missing piece is an MCP server exposing a bash tool.

## Comment by srobinson at 2026-08-25T11:57:12Z (updated 2026-08-25T11:57:12Z)

https://github.com/littleorgans/transport-matters/issues/455#issuecomment-5410025021

See #460: the `just-agent` A/B experiment (all builtins off, our system prompt, one just-bash tool). Unblocked on claude today via native flags — measured floor 5,717 bytes vs 114,619 default, zero provider spend. Only missing piece is the just-bash MCP server.

## Sub issues
[]
