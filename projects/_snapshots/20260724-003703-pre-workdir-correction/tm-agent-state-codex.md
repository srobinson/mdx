# Transport Matters agent lifecycle derivation

Date: 2026-07-10

Research scope: Claude Code transcript feasibility, Codex protocol leverage, wire signals, and a harness independent lifecycle proposal. No Transport Matters repository files were changed.

## Executive finding

The canonical state must be driven by explicit lifecycle facts. Silence, an ended model response, and an alive process are insufficient evidence for `needs_you`.

Claude Code permission state is only partially present in the transcript. The journal contains the model tool call, the configured permission mode, and sometimes a later denial result. It contains no record for the pending permission dialog itself. The same applies to plan review as a local gate. `ExitPlanMode` can identify the model's intent when that tool call is present, but the pending and resolved dialog states are local harness facts.

Codex has excellent structured lifecycle facts in its live protocol. `EventMsg::ExecApprovalRequest`, `EventMsg::ApplyPatchApprovalRequest`, `EventMsg::RequestPermissions`, and `EventMsg::RequestUserInput` are explicit blocking events. Codex app server improves this further with `thread/status/changed`, whose active flags are `waitingOnApproval` and `waitingOnUserInput`. These flags are maintained by request guards and clear when the request resolves, the turn completes, the turn is interrupted, or the thread shuts down.

There is one important boundary. Codex deliberately excludes approval requests and user input requests from the on disk rollout. They are transient live events. Transport Matters can leverage them only through a live app server integration or an observer hook. Parsing the rollout alone cannot recover permission waits.

Recommended direction:

1. Define a harness independent reducer over versioned evidence events.
2. Treat explicit attention requests as keyed leases, never as an inference from inactivity.
3. Use transcripts for durable turn, tool, question, completion, and usage facts.
4. Use structured harness hooks for local permission prompt onset where supported.
5. Use PTY recognition as the resolution signal and fallback for current interactive TUI launches.
6. Evaluate Codex app server as the preferred high fidelity Codex provider because it already owns the exact state machine Transport Matters needs.

## Claude Code transcript probe

### Corpus

Probe target: `~/.claude/projects/**/*.jsonl`

Installed harness: Claude Code `2.1.205`

Observed corpus:

| Measure | Result |
| --- | ---: |
| Transcript files | 2,015 |
| JSONL records | 334,383 |
| Assistant records with `stop_reason=tool_use` | 90,865 |
| Assistant records with `stop_reason=end_turn` | 9,057 |
| User records | 70,684 |
| `system/turn_duration` records | 5,249 |
| `permission-mode` records | 13,571 |
| Explicit `permission_request`, `approval_request`, or `prompt` record types | 0 |

`permission-mode` has only `type`, `sessionId`, and `permissionMode`. It records configuration, not a pending prompt:

| Mode | Records |
| --- | ---: |
| `bypassPermissions` | 13,450 |
| `default` | 101 |
| `acceptEdits` | 20 |

All 13,758 top level `mode` records in this corpus have `mode=normal`.

### What is journaled

| Fact | Journal evidence | Lifecycle value |
| --- | --- | --- |
| Model is requesting a tool | Assistant content block `type=tool_use`; assistant `stop_reason=tool_use` | `working.acting`, subject to a local gate |
| Tool completed or was rejected | User content block `type=tool_result`, linked by `tool_use_id` | Clears the tool call after completion |
| Model ended its turn | Assistant `stop_reason=end_turn` | `idle`, unless an attention lease remains open |
| Model asked a structured question | `tool_use name=AskUserQuestion` | Opens `needs_you.question` |
| Question was answered or rejected | Matching `tool_result` | Closes `needs_you.question` |
| Permission policy | Top level `permission-mode` | Context only, never current state |
| Turn duration and hook summaries | System records | Telemetry and corroboration |

There are 277 actual `AskUserQuestion` tool calls. Every one has `stop_reason=tool_use`. This is a clean transcript signal for `needs_you.question` while no matching `tool_result` exists.

The corpus contains denial aftermath for multiple tools. The phrase pair `user doesn't want to proceed` and `tool use was rejected` occurs in 89 files. Correlating matching results to their tool calls found 39 Bash results, 86 AskUserQuestion results, 30 Agent results, and smaller counts for other tools. This proves that a denial can appear later as a `tool_result`. It does not expose the interval while the dialog is waiting, and approval normally produces only the ordinary tool result.

### What is absent

No top level transcript record identifies a permission dialog as pending. The last durable record at that moment is commonly the assistant tool call. That shape is identical for an auto approved tool, a tool currently executing, and a tool blocked on permission.

The corpus contains zero actual `tool_use name=ExitPlanMode` blocks. The string appears in 518 files only through attachments and text. The local corpus therefore cannot directly demonstrate a plan review sequence. Official Claude Code documentation confirms that `ExitPlanMode` presents a permission dialog and that a `PermissionRequest` hook fires when that dialog is about to be shown. It also documents a `Notification` hook with `notification_type=permission_prompt`. See the [hooks reference](https://code.claude.com/docs/en/hooks) and [hooks guide](https://code.claude.com/docs/en/hooks-guide).

Conclusion: `CC permission-in-transcript = partial`. The tool request and denial aftermath are durable. The pending permission or plan review gate is absent.

### Claude Code acquisition options

| Option | Strength | Limitation |
| --- | --- | --- |
| Transcript only | Stable questions, tool calls, results, turn ends | Cannot identify a pending permission dialog |
| Wire plus transcript | Adds request in flight and Anthropic `stop_reason` truth | Local approval still occurs after the model response |
| Observer `PermissionRequest` hook | Structured prompt onset with session, permission mode, tool name, and tool input | No matching callback for the user's approval; hook availability and schema vary by version |
| `Notification(permission_prompt)` hook | Simple structured onset and user facing message | Coarser than `PermissionRequest`; no resolution event |
| PTY recognizer | Sees the actual local dialog and its disappearance | Render grammar changes across versions and terminal sizes |

The best current Claude Code provider is transcript plus a side effect only observer hook plus PTY fallback. The hook must return an empty success and must never decide the permission request. PTY screen change or subsequent durable progress clears the lease.

## Codex protocol probe

### Source and version

Durable research clone: `~/.mdx/research/openai-codex`

| Ref | SHA |
| --- | --- |
| `main` at probe time | `cbdee7976b3717e3e0b7fbe83e2aa2843f1aa500` |
| Installed `codex-cli 0.144.0` tag, `rust-v0.144.0` | `767822446c7a594caa19609ca435281a9ec67e0d` |

The tag and `main` had no changes in the protocol, app server protocol, or exec event files inspected here. They were 28 repository commits apart.

### Authoritative source files

All paths are relative to the research clone.

| Path | Authority |
| --- | --- |
| `codex-rs/protocol/src/protocol.rs` | `Submission`, `Op`, `Event`, `EventMsg`, `TurnStartedEvent`, `TurnCompleteEvent`, deltas, hook events |
| `codex-rs/protocol/src/approvals.rs` | Exec and patch approval request payloads |
| `codex-rs/protocol/src/request_user_input.rs` | Structured user question and answer payloads |
| `codex-rs/protocol/src/request_permissions.rs` | Structured permission profile requests |
| `codex-rs/protocol/src/items.rs` | Durable `TurnItem`, including `PlanItem` |
| `codex-rs/protocol/src/config_types.rs` | `ModeKind`, including plan collaboration mode |
| `codex-rs/rollout/src/policy.rs` | Exact durable versus transient rollout policy |
| `codex-rs/core/src/session/mod.rs` | Emission of approval and user input events; event persistence handoff |
| `codex-rs/app-server/src/bespoke_event_handling.rs` | Mapping from core `EventMsg` requests to blocking JSON RPC server requests |
| `codex-rs/app-server/src/thread_status.rs` | Authoritative active, idle, error, waiting on approval, and waiting on input state machine |
| `codex-rs/app-server-protocol/src/protocol/common.rs` | JSON RPC method names and request or notification unions |
| `codex-rs/app-server-protocol/src/protocol/v2/thread.rs` | `ThreadStatus`, `ThreadActiveFlag`, and status notifications |
| `codex-rs/app-server-protocol/src/protocol/v2/turn.rs` | Turn status and notifications |
| `codex-rs/app-server-protocol/src/protocol/v2/item.rs` | Structured item lifecycle and plan items |
| `codex-rs/app-server-protocol/src/export.rs` | TypeScript and JSON Schema generation |
| `codex-rs/app-server-protocol/schema/` | Checked in generated JSON Schema and TypeScript |
| `codex-rs/exec/src/exec_events.rs` | Reduced `codex exec --json` event surface |

The official [protocol v1 document](https://github.com/openai/codex/blob/rust-v0.144.0/codex-rs/docs/protocol_v1.md) describes `EventMsg` as non exhaustive and explicitly warns that variants will be added. The [app server README](https://github.com/openai/codex/blob/rust-v0.144.0/codex-rs/app-server/README.md) documents version matched schema generation and its request lifecycle.

### Lifecycle carrying core events

| `EventMsg` variant | Canonical meaning |
| --- | --- |
| `TurnStarted`, serialized as `task_started` in v1 | `working.thinking` |
| `TurnComplete`, serialized as `task_complete` in v1 | `idle`, unless a derived plan review lease opens |
| `TurnAborted` | Terminal turn interruption; normally `idle` after abort is settled |
| `Error` | `failed` when the error affects the turn |
| `AgentMessage`, `AgentReasoning`, reasoning deltas | `working.thinking` and visible progress |
| `ExecCommandBegin`, `ExecCommandEnd` | `working.acting` and action completion |
| `PatchApplyBegin`, `PatchApplyEnd` | `working.acting` and action completion |
| `McpToolCallBegin`, `McpToolCallEnd` | `working.acting` and action completion |
| `WebSearchBegin`, `WebSearchEnd` | `working.acting` and action completion |
| `ItemStarted`, `ItemCompleted` | Generic action item lifecycle |
| `ExecApprovalRequest` | Opens `needs_you.permission` |
| `ApplyPatchApprovalRequest` | Opens `needs_you.permission` |
| `RequestPermissions` | Opens `needs_you.permission` |
| `ElicitationRequest` | Opens `needs_you.permission` or `needs_you.question`, based on request kind |
| `RequestUserInput` | Opens `needs_you.question` |
| `PlanUpdate`, `PlanDelta`, completed `PlanItem` | Structured plan production; not a dedicated plan approval event |
| `TokenCount` | Usage telemetry, not lifecycle state |
| `ShutdownComplete` | `stopped` |

Codex has no dedicated `PlanApprovalRequest` variant. A reasonable derived rule is: a completed turn in plan collaboration mode that contains a completed plan item opens `needs_you.plan_review`. The next user submission, mode change, or turn start closes it. This rule needs a captured plan mode fixture before implementation.

### Explicit blocking facts

Core emits these events before waiting:

* `EventMsg::ExecApprovalRequest`
* `EventMsg::ApplyPatchApprovalRequest`
* `EventMsg::RequestPermissions`
* `EventMsg::RequestUserInput`
* `EventMsg::ElicitationRequest`

App server maps them to server initiated JSON RPC requests:

| Core event | App server method |
| --- | --- |
| `ExecApprovalRequest` | `item/commandExecution/requestApproval` |
| `ApplyPatchApprovalRequest` | `item/fileChange/requestApproval` |
| `RequestPermissions` | `item/permissions/requestApproval` |
| `RequestUserInput` | `item/tool/requestUserInput` |
| `ElicitationRequest` | `mcpServer/elicitation/request` |

When a request arrives, `thread_status.rs` increments a guarded counter. It publishes:

```text
thread/status/changed
status.type = active
status.activeFlags = [waitingOnApproval | waitingOnUserInput]
```

The guard decrements when the response handler releases it. Turn completion, interruption, shutdown, and system error also clear active request counts. This is the cleanest available source for true Codex lifecycle state.

### Rollout persistence caveat

Installed local corpus:

| Measure | Result |
| --- | ---: |
| Rollout files | 3,679 |
| JSONL records | 1,415,044 |
| Files with `task_started` | 3,342 |
| Files with `task_complete` | 3,060 |
| Files with `turn_aborted` | 864 |
| Files with persisted explicit approval request event | 0 |

`codex-rs/rollout/src/policy.rs::should_persist_event_msg` explicitly classifies all five blocking request events as transient. The rollout does persist `TurnStarted`, `TurnComplete`, `TurnAborted`, `TokenCount`, `ThreadSettingsApplied`, and selected completed items. It also persists raw Responses API `FunctionCall` and `FunctionCallOutput` items.

One Codex `0.121.0` rollout contains 64 `response_item/function_call` records named `request_user_input` and 64 correlated outputs. This older raw shape can support question leases. No corresponding `event_msg/request_user_input` is durable because the policy filters it.

Therefore:

* Codex transcript is strong for turns, raw function calls, answers, completed items, usage, and errors.
* Codex transcript is insufficient for a permission wait.
* Core `EventMsg` and app server are strong for live permission waits.
* `codex exec --json` is also insufficient. Its public `ThreadEvent` union contains thread start, turn start or completion or failure, item start or update or completion, and error. It does not contain approval request events.

## Wire feasibility

| State fact | Claude wire | Codex wire |
| --- | --- | --- |
| Model request is in flight | Clean | Clean |
| Model response completed | Clean via Messages response completion | Clean via Responses `response.completed` |
| Model emitted a tool call | Clean via `stop_reason=tool_use` plus tool block | Clean via Responses output `function_call` or custom tool item |
| Model ended without a tool | Clean via `stop_reason=end_turn` | Clean via completed assistant message and no pending output call |
| Structured question | `AskUserQuestion` tool call | `request_user_input` function call |
| Local exec or patch approval prompt | Absent | Absent |
| Local plan review prompt | Model intent may be visible as `ExitPlanMode`; pending dialog absent | No dedicated wire or core plan approval event |
| User resolved a local approval | Absent until later tool progress | Absent until later tool progress |

Anthropic documents `end_turn` and `tool_use` as Messages API stop reasons in its [stop reason guidance](https://docs.anthropic.com/en/api/handling-stop-reasons). OpenAI documents `response.completed` and structured function call output items in the [Responses streaming reference](https://platform.openai.com/docs/api-reference/responses-streaming/response/completed).

Wire is authoritative for model activity. It cannot be authoritative for a local harness dialog that occurs after the model response.

## Canonical lifecycle vocabulary

```text
starting
working { phase: thinking | acting | compacting | unknown }
needs_you { kind: question | permission | plan_review, request_id?, since }
idle
stopped { exit_code? }
failed { code?, message? }
unknown { reason }
```

Definitions:

| State | Definition |
| --- | --- |
| `starting` | Harness process exists, but no session start or turn fact has arrived |
| `working.thinking` | A turn is active and no action item is currently executing |
| `working.acting` | A tool, command, patch, MCP call, or equivalent action is active |
| `working.compacting` | A structured compaction event is active |
| `needs_you.question` | An explicit structured user input request is unresolved |
| `needs_you.permission` | An explicit approval or permission request is unresolved |
| `needs_you.plan_review` | A plan has been presented under a harness specific review contract and awaits the next user decision |
| `idle` | Process is alive, no turn is active, and no attention request is open |
| `stopped` | Process exited normally or was intentionally stopped |
| `failed` | Process or active turn reached a terminal error |
| `unknown` | Available signals conflict, the harness version is unsupported, or a required capability is absent |

`unknown` is preferable to a false `needs_you` state.

## Reducer design

Normalize every plane into evidence events:

```text
LifecycleEvidence {
  run_id
  harness
  harness_version
  source: wire | transcript | hook | pty | process
  source_sequence
  observed_at
  kind
  correlation_id?
  confidence
  raw_schema_version
}
```

The reducer owns attention leases keyed by correlation ID. Examples are Claude `tool_use_id`, Codex `call_id`, and app server request ID.

Rules:

1. Process exit closes all leases and produces `stopped` or `failed`.
2. An explicit unresolved attention lease outranks working and idle facts.
3. Matching answer, approval resolution, tool result, request guard release, or new turn input closes its lease.
4. A turn start produces `working.thinking`.
5. Action begin and end events switch between `working.acting` and `working.thinking` without ending the turn.
6. Turn completion produces `idle` unless it opens a plan review lease.
7. PTY matches may open an unkeyed lease only when a versioned recognizer has positive evidence. Prompt disappearance, durable progress, or process exit clears it.
8. Time alone never creates `needs_you`. An expired or contradictory lease degrades to `unknown` and increments a drift counter.

Each published state should include its winning evidence, observed time, confidence, and any degraded capability. This makes incorrect state diagnosable.

## Acquisition designs and tradeoffs

### Option A: Current TUI launch plus transcript, hook, PTY, and wire

This keeps the current user experience.

* Transcript provides durable turns, tools, questions, results, and usage.
* Wire provides request in flight and model completion.
* Managed home injection installs a side effect only `PermissionRequest` observer for both harnesses where supported.
* PTY recognizes local prompts and their disappearance.

Benefits: smallest product change, compatible with the current terminal pane, and usable for Claude Code and Codex.

Costs: hook support can be disabled, prompt resolution still needs PTY or later progress, and PTY grammars require versioned fixtures.

### Option B: Codex app server provider

Run Codex through app server and consume generated JSON RPC types.

Benefits: exact active, idle, error, waiting on approval, and waiting on input state; explicit request IDs; explicit `serverRequest/resolved`; no terminal scraping for lifecycle.

Costs: this is a different launch and UI integration from the existing Codex TUI. It should be treated as a product architecture decision, not a parser change.

### Option C: Transcript and wire only

Benefits: smallest implementation.

Costs: cannot solve the reported bug class. Permission waits remain indistinguishable from running tools. Reject this option.

### Option D: Patch or fork Codex to export its event queue

Benefits: complete fidelity while retaining a custom TUI path.

Costs: permanent harness maintenance burden. Reject while app server and hooks exist.

## Codex schema leverage

Do not bind Transport Matters directly to Codex Rust enums. The core protocol is non exhaustive and primarily an in process contract. Consume the app server JSON Schema or generated TypeScript instead.

Validated with installed Codex `0.144.0`:

```text
codex app-server generate-json-schema --out <dir>
codex app-server generate-ts --out <dir>
```

The commands generated 267 JSON files and 598 TypeScript files. Generated `ServerRequest.ts` and `ServerNotification.ts` checksums exactly match the files checked into tag `rust-v0.144.0`. The generated request union includes all five blocking request methods. The notification union includes `thread/status/changed`, `turn/started`, `turn/completed`, `item/started`, `item/completed`, token usage, and plan updates.

Proposed release process:

1. Record `codex --version` in launch facts.
2. Resolve the matching `rust-v<version>` tag when available.
3. Generate JSON Schema from the installed binary during adapter certification.
4. Store a checksum and a minimal supported schema snapshot with the harness bundle.
5. Diff discriminants and required fields against the prior certified version.
6. Run generic fixtures for turn, tool, question, exec approval, patch approval, permission request, plan, error, interrupt, and exit.
7. Extend only the version ranged mapping table when a compatible event is added.
8. Mark an unknown version best effort. Count unknown methods or fields at runtime and surface them through doctor and the UI.

Expected maintenance is low for additive releases: regenerate, diff, add fixtures for new discriminants, and certify. A renamed or removed lifecycle event requires a new mapping range. The schema generator makes this measurable rather than heuristic.

## Proposed first implementation boundary

1. Build the lifecycle reducer and evidence contract with no harness branches in the domain.
2. Add Claude and Codex transcript adapters for durable turn, question, result, completion, error, and usage facts.
3. Add versioned `PermissionRequest` observer hooks to the managed Claude and Codex homes. Hooks emit onset only and never decide.
4. Add PTY recognizers for permission and plan review prompts, plus prompt disappearance.
5. Add evidence provenance and an `unknown` fallback.
6. Prototype a Codex app server provider separately. Compare its `thread/status/changed` output against the TUI provider using the same reducer fixtures.

The product can ship the reducer before deciding whether Codex app server replaces the TUI path. The domain contract and state vocabulary remain the same.

## Required validation fixtures

Per supported harness version, capture these sequences:

* Start, idle, user turn, thinking, clean completion, idle.
* Auto approved tool start and completion.
* Tool permission prompt, approve, execution start, completion.
* Tool permission prompt, deny, model recovery.
* Structured question, answer, resumed work.
* Structured question, cancel or reject.
* Plan mode entry, plan presentation, approval, rejection, and next turn.
* Interrupt during thinking, tool execution, question, and permission.
* Harness crash and clean exit.
* Transcript lag, duplicate records, out of order plane arrival, and unsupported version.

Conformance must assert both state and winning evidence at every step. This prevents a later mapping change from silently turning idle into `needs_you` again.
