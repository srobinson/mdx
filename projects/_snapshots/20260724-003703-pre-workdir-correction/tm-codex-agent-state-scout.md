# Codex Agent State Wire Scout

Scout target: `transport-matters` main at `78869965a3f5250df7199c99472c2225620db909`.

Verdict: `gated=impossible` on the authenticated model websocket alone. `asked=live` is achievable from the structured `request_user_input` tool call, although the shipped producer reaches asked through finalized exchange ingestion after `response.completed`.

Evidence corpus:

- `~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/d35a3b13-bf99-4314-ad5e-b445656bed79/20260711T024123Z-ffbc0826/request.raw`
- `~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/d35a3b13-bf99-4314-ad5e-b445656bed79/20260711T024123Z-ffbc0826/transport.json`
- `~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/d35a3b13-bf99-4314-ad5e-b445656bed79/20260711T024133Z-062b19e3/request.raw`
- `~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/d35a3b13-bf99-4314-ad5e-b445656bed79/20260711T024133Z-062b19e3/transport.json`

The first raw request advertises `request_user_input` as a function tool with required `questions`; it also advertises `exec` as a custom tool and `wait` as a function tool. Its server frames are `codex.rate_limits`, `codex.response.metadata`, `response.created`, `response.in_progress`, and `response.completed`. The second turn contains reasoning and assistant message item lifecycles, text deltas, and `response.completed`. Neither captured turn contains a tool invocation, approval request, permission request, or gated tag. Websocket response bytes live in each `transport.json` message's `payload_text` and `payload_json`; websocket exchanges intentionally have no separate `response.raw`.

The exact installed client is `codex-cli 0.144.1`. Its tagged source separates the model wire from the local agent protocol:

- [`codex-rs/codex-api/src/common.rs::ResponseEvent`](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/codex-api/src/common.rs) contains output item, tool input delta, text, reasoning, created, completed, and metadata events. It has no approval pending event.
- [`codex-rs/protocol/src/models.rs::ResponseItem`](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/protocol/src/models.rs) tags model output as message, reasoning, function call, custom tool call, local shell call, tool search call, web search call, image generation call, compaction, and corresponding outputs. It has no approval pending item.
- [`codex-rs/protocol/src/protocol.rs::EventMsg`](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/protocol/src/protocol.rs) separately defines local `ExecApprovalRequest`, `ApplyPatchApprovalRequest`, `RequestPermissions`, and `RequestUserInput` events.
- [`codex-rs/core/src/tools/handlers/shell.rs::run_exec_like`](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/tools/handlers/shell.rs) computes the approval requirement from local policy, permission profile, requested sandbox permissions, cached grants, and command policy after the model emits a tool call.
- [`codex-rs/core/src/tools/handlers/request_user_input.rs::RequestUserInputHandler`](https://github.com/openai/codex/blob/rust-v0.144.1/codex-rs/core/src/tools/handlers/request_user_input.rs) receives the model function call, emits the local user input request, and awaits the answer.

## Reuse Map

| Capability | Existing owner | Reuse judgment |
|---|---|---|
| Recognize the authenticated Codex Responses websocket | `api/src/transport_matters/codex/transport.py::is_codex_websocket_flow` | Reuse unchanged. |
| Capture each client and server frame | `api/src/transport_matters/codex/transport.py::record_codex_websocket_message`, `codex_websocket_payload`, `build_codex_transport_artifacts` | Reuse unchanged. The live signal is already available before exchange finalization. |
| Route server frames into live classification | `api/src/transport_matters/addon_handlers.py::handle_codex_websocket_message` | Reuse unchanged. It already passes every server JSON object and the provisional generation. |
| Own Codex event and item tags | `api/src/transport_matters/codex/protocol.py::CODEX_OUTPUT_ITEM_ADDED_EVENT_TYPE`, `CODEX_OUTPUT_ITEM_DONE_EVENT_TYPE`, `CODEX_TOOL_CALL_ITEM_TYPES`, `codex_tool_call_key` | Extend this owner only if a named ask helper is useful. Do not add a second tag vocabulary. |
| Parse completed Codex output items | `api/src/transport_matters/codex/response_parser.py::parse_codex_response_payloads`, `_parse_output_items`, `_tool_use_block` | Reuse. Function and custom tool calls already become `ToolUseBlock` with name and call id. |
| Parse Codex request frames and tool definitions | `api/src/transport_matters/codex/request_parser.py::parse_codex_request`, `_parse_tools`, `_parse_function_call` | Reuse. Preserve `additional_tools`; the captured request places `request_user_input` there. |
| Reframe HTTP fallback response bytes | `api/src/transport_matters/sse.py::IncrementalSseFrames` | Reuse. HTTP fallback payloads have the same response tags after SSE removal. |
| Tee streamed HTTP bytes without changing the response | `api/src/transport_matters/response_stream.py::install_response_tee` | Reuse unchanged. |
| Classify provider payloads into live facts | `api/src/transport_matters/live_status.py::LiveStatusFact`, `CodexLiveClassifier` | Extend. Codex reasoning, running tool, and generating are already provider specific behind a provider neutral fact. |
| Serialize latest wins live writes | `api/src/transport_matters/live_status_observer.py::LiveStatusObserver`, `observe_codex_payload`, `_offer` | Reuse unchanged once the fact vocabulary grows. |
| Commit and notify live rows | `api/src/transport_matters/session/writer.py::SessionWriter.submit_run_live_status` | Reuse unchanged. |
| Reject closed generation stragglers and close the exact finalized generation | `api/src/transport_matters/session/dao_statements.py::UPSERT_RUN_LIVE_STATUS_SQL`, `CLOSE_RUN_LIVE_STATUS_GENERATION_SQL`; `api/src/transport_matters/session/writer.py::SessionWriter.submit_wire_exchange` | Reuse unchanged. Add the new live kind to the database check constraint through a new migration. |
| Read the applied live row into Activity | `packages/activity/src/adapters/postgresRecords.ts::PostgresActivityReader.readLiveStatusForRun` | Reuse with the expanded shared kind contract. |
| Own cross provider ask tool names | `packages/activity/src/adapters/harnessRegistry.ts::askToolNames`, `isAskToolName` | Reuse. It already contains `request_user_input`. |
| Derive asked from the finalized exchange | `packages/activity/src/service/runActivityEvents.ts::wireCandidateFromSnapshot` | Keep as the durable fallback after `response.completed`. |
| Translate a live row into a domain candidate | `packages/activity/src/service/runActivityEvents.ts::liveCandidateFromRow` | Extend with live asked. |
| Admit, resolve, and mint wire assertion events | `packages/activity/src/domain/wireCandidate.ts::WireCandidate`, `wireCandidateAdmitted`, `wireCandidateEvent` | Extend with live asked by reusing the existing `record.question_asked` fold and tool call resolution rule. |
| Prefer live state, then finalized exchange state | `packages/activity/src/service/activityIngestion.ts::ActivityIngestion.reconcileWireSnapshot` | Reuse unchanged if live asked maps into the existing candidate contract. |
| Own the asked state and its fold | `packages/activity/src/domain/runActivityMachine.ts::runActivityMachine`; `packages/activity/src/domain/runActivityContext.ts::foldQuestionAsked` | Reuse. The asked machine state already exists. |
| Own public needs you vocabulary and tiering | `packages/contract/src/activity/wire.ts::activityStatuses`, `activityStatusTier`, `needsYouForStatus` | Reuse. `needs-you-gated` is reserved, while its payload and producer remain absent. |
| Emit a live asked fact from Codex output item frames | **none found** | Searches: `rg 'LiveStatusKind|RUN_LIVE_STATUS_KINDS|request_user_input|asked' api/src/transport_matters packages/activity`; current live kinds are reasoning, running tool, and generating. |
| Observe authoritative approval pending on the authenticated model websocket | **none found** | Searches: `rg -i 'approval|permission|gated'` across both captured `transport.json` files and repository Codex transport code; exact `0.144.1` `ResponseEvent` and `ResponseItem` tags also contain no approval pending variant. |
| Apply a gated candidate, machine state, and structured payload | **none found** | Searches: `rg 'needs-you-gated|gated' packages/activity packages/contract`; only the reserved public status and comments exist. There is no candidate, event, machine state, or `{kind: "gated"}` payload. |

Existing reuse anchors: **20**.

## Quality Map

### Wire facts

- The model websocket is a Responses API stream. `response.output_item.added` and `response.output_item.done` carry typed tool items with name and call id. The captured response proves these item lifecycle tags arrive before `response.completed` for reasoning and message items. The installed type owner applies the same lifecycle to function and custom tool items.
- `request_user_input` is part of the captured request's advertised tool set. A returned function call is therefore the authoritative model request to ask the operator. It can be classified at `response.output_item.added` when name and call id are present, with `response.output_item.done` as the complete fallback.
- Shell and patch approval is a local decision. The same model tool call can run immediately, be denied, or open an approval prompt depending on local policy, sandbox result, command policy, cached grants, and permission profile. A model frame cannot distinguish those outcomes.
- A possible `request_permissions` function call does not make the general gated state authoritative on this wire. It can be rejected by local validation and it does not cover shell or patch approvals. No captured request advertises it and no captured response invokes it.

### Shipped realtime slices

- Slice 1 (`4361d36`) owns `run_live_status`, identity only notification, and the generation fence. This is provider neutral and directly reusable.
- Slice 2 (`d464f83`) owns the provider neutral fact plus provider specific classifiers. The abstraction is sound. Its vocabulary excludes needs you states.
- Slice 3 (`bcfb48d`) owns the nonblocking producer tap, latest wins lane, abort terminal, and subagent guard. The Codex websocket hook is already live.
- Slice 4 (`fa6d4da`) owns Activity live row reads, candidate admission, retraction, and reconnect recovery. It prefers live rows over finalized snapshots. Its live candidate vocabulary excludes asked and gated.

### Product behavior today

- Asked is durable but currently enters through `wireCandidateFromSnapshot` after exchange finalization. The producer never writes a live asked row.
- The public contract accepts `needs-you-gated` only as a reserved status and tier. `needsYouForStatus` has no gated payload. The Activity machine has no gated state and says so explicitly.
- Closing a live generation at `response.completed` can hand live asked to the finalized asked snapshot. Regression coverage must prove this handoff never flashes idle, running tools, or null needs you.
- `runActivityMachine.ts` is 638 lines and `runActivityContext.ts` is 606 lines. A gated state can approach the 700 line limit. Keep the existing asked path small; if gated adds a full transition family, extract the cohesive wire assertion transition table before crossing the threshold.

### Evidence limits

The local Transport Matters corpus has two Codex websocket turns. It proves the request tool advertisement, raw frame ownership, tag order, and absence of approval tags in those turns. It contains no actual ask, exec, permission, or approval response item. A fixture for the implementation slice must come from a real captured Codex turn that invokes `request_user_input`; synthetic payloads alone do not close this evidence gap.

## Plan

### Decisions

1. Keep `needs_you{gated}` authoritative. Under that definition, the authenticated model websocket cannot produce it. Choose whether Transport Matters may add a local Codex control plane source. Without that scope expansion, leave gated reserved.
2. Treat `request_user_input` as asked as soon as a named output item arrives. Use item done when item added lacks a stable name or call id. Preserve the finalized exchange path as recovery and durable fallback.
3. Keep provider parsing separate from product vocabulary. Codex tag recognition belongs in `CodexLiveClassifier`; Activity receives provider neutral live kinds.

### PR 1: live Codex asked producer

- Extend `LiveStatusKind`, `LIVE_STATUS_KINDS`, `RunLiveStatusKind`, and the Postgres check constraint with `asked` through a new migration.
- Special case `request_user_input` in `CodexLiveClassifier` while continuing to classify every other supported tool call as running tool.
- Carry the tool call id through `LiveStatusFact` and `LiveStatusObserver`.
- Add a redacted real byte fixture containing `response.output_item.added`, any argument deltas, `response.output_item.done`, and `response.completed` for `request_user_input`.
- Prove duplicate frames, item done fallback, terminal clearing, abort clearing, subagent suppression, and closed generation rejection.

### PR 2: live asked product admission

- Update the shared PG contracts and `PostgresActivityReader` kind validation.
- Add a live asked candidate in `liveCandidateFromRow` and `WireCandidate`.
- Reuse `record.question_asked`, `foldQuestionAsked`, the existing asked machine state, and resolved tool call admission.
- Prove the live to finalized handoff, answer before delayed live write, reconnect replay, retraction, silence stall interaction, and no idle flash.
- Keep `wireCandidateFromSnapshot` as the recovery path when live observation is absent.

### PR 3: gated source boundary, conditional

- If the product authorizes a local Codex source, capture local `EventMsg::ExecApprovalRequest`, `ApplyPatchApprovalRequest`, and `RequestPermissions` plus their resolutions. Do not infer pending from an `exec`, `apply_patch`, or `request_permissions` model call.
- Adapt those local events into the existing live row, writer, notification, and generation fence. The authenticated websocket observer remains unchanged.
- If the local event stream cannot be obtained without replacing the launch architecture, stop after a bounded spike and keep `gated=impossible` for the current transport boundary.

### PR 4: gated product state, conditional on PR 3

- Add the provider neutral gated live kind and structured gate metadata required by the chosen local source.
- Extend `ActivityNeedsYou` with `{kind: "gated"}`, `needsYouForStatus`, the wire candidate, Activity machine state, wire status mapping, retraction targets, and projections.
- Preserve one owner for needs you payload derivation and one machine path. Extract the wire assertion transition family if needed to keep files below the repository limit.
- Prove pending, approve, deny, cancel, run exit, stale generation, reconnect, and asked versus gated precedence.

Verification gates for implementation slices: the repository recipes `just check` and `just test`, plus focused Python and Activity tests during the inner loop.
