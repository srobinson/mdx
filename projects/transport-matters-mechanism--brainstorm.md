# Transport Matters Overlay: Wire Mechanism Brainstorm

## Finding

Transport Matters already has the smallest useful overlay kernel. A request is parsed into an immutable provider neutral IR, typed overrides are applied before provider release, changed IR is serialized back onto the HTTP body or Codex websocket frame, and Tier 1 stores both the captured and curated forms. The breakpoint supplies an interactive editor, while the override store already carries edits into later exchanges within one process.

The new primitive therefore needs less mutation machinery than it first appears. The missing work is durable ownership, deterministic scope precedence, selectors that survive schema shape changes, evidence that identifies the exact overlay revision applied, and safe degradation when a provider or harness changes.

This report ranks 12 mechanisms that are worth considering and one mechanism Transport Matters should refuse to build. “Novel” marks ideas that appear genuinely new in the context of Transport Matters' dual wire and transcript evidence. It does not claim nobody anywhere has explored a related technique.

## Current mechanism

The HTTP path is `api/src/transport_matters/addon_handlers.py:handle_http_request`. It parses captured bytes, calls `api/src/transport_matters/request_pipeline.py:run_pipeline`, writes changed bytes through `api/src/transport_matters/request_diff.py:outbound_request_if_changed`, persists a provisional exchange, then optionally enters `api/src/transport_matters/pause_session.py:handle_breakpoint`. Release rewrites the live request and updates `RequestFlowState` before provider delivery.

The Codex websocket path is `api/src/transport_matters/addon_handlers.py:handle_codex_websocket_message`. It applies the same pipeline to each captured initial client frame. `api/src/transport_matters/pause_session.py:handle_websocket_breakpoint` can replace `message.content`, then `api/src/transport_matters/codex/exchange_derivation.py:rewrite_codex_provisional_exchange` repairs the stored provisional view.

The existing operation owner is `api/src/transport_matters/overrides/__init__.py:apply_overrides`. It supports tool removal, tool description replacement, system part removal or replacement, message block removal or replacement, tool result truncation, sampling changes, and nested provider extras changes. `api/src/transport_matters/overrides/state.py:OverrideStore` owns process resident state keyed by run and track.

Tier 1 persistence is already suitable for proof. `api/src/transport_matters/exchange_recorder/artifacts.py:build_request_artifacts` produces original raw bytes and IR plus curated raw bytes, curated IR, and an override audit when structure changes. `api/src/transport_matters/storage/disk.py:DiskStorageBackend._write_exchange_files` writes those artifacts. `api/src/transport_matters/session/wire_store.py:write_wire_exchange` normalizes the provider bound request into Postgres while raw bytes remain in Tier 1.

The current limits are concrete:

1. `OverrideStore` is memory only. `api/src/transport_matters/shared_proxy/manager.py:SharedProxyManager._rehydrate_locked` survives a child proxy restart from the API process mirror, but an API process restart loses that mirror and deregistration removes run overrides.
2. Scope is exact run and track identity. `run_pipeline` receives `run_id` and derives a `TrackAssignment`; it does not receive workspace, worktree, harness, or an explicit precedence stack.
3. Persistent targets are brittle. System and message targets use original list indices. Tool result targets use per turn IDs. Tool names are more stable, but still harness vocabulary rather than semantic capabilities.
4. `api/src/transport_matters/client_version.py:detect_client_version` is called only by `api/src/transport_matters/exchange_recorder/__init__.py:persist_unparsed_exchange`. Regular captures do not yet carry the decided every capture version stamp.
5. `api/src/transport_matters/counting.py:TokenCounter` is authoritative for Anthropic. Codex has no equivalent preflight counter in the current code.
6. `api/src/transport_matters/overrides/audit.py:OverrideAuditEntry` records kind, target, applicability, character delta, and optional curated value. It does not identify an overlay manifest, baseline shape, selector precondition, mismatch reason, or cache impact.

## Ownership and precedence

A durable overlay should have one policy owner in the product plane and one application owner in the capture plane.

The product plane should own revisioned overlay manifests, scope resolution, precedence, and baseline packages. The capture plane should receive an immutable compiled snapshot and remain the sole writer of provider bound request bytes through `run_pipeline` and `outbound_request_if_changed`. The breakpoint can author or preview policy, but it should not become a second policy store.

A workable precedence order is:

`shipped default < owner global < space < worktree or workspace < harness < model < run < track < one turn edit`

Conflicts at the same level should fail compilation. More specific policy should win only when the manifest states that scope. Composition must be deterministic and visible in the application audit.

No database or filesystem lookup belongs on the proxy hot path. Resolve durable policy when a run registers, compile again only when policy or observed schema shape changes, then send the complete snapshot over the existing shared proxy control channel.

## Consumer enumeration convention

The amendment to this brief requires consumer enumeration for feasibility claims. The inventories below cover production references found with repository searches. Tests, type only imports, and reexports are excluded. `InternalRequest` has 169 production references, so its consumers were not exhaustively enumerated. Any idea relying on that broad IR contract says so and names the narrower consumers that matter.

The main seam inventories are:

1. `run_pipeline` owner and consumers. Owner: `api/src/transport_matters/request_pipeline.py:run_pipeline`. Production consumers found: `addon_handlers.handle_http_request` and `addon_handlers.handle_codex_websocket_message`.
2. `apply_overrides` owner and consumers. Owner: `api/src/transport_matters/overrides/__init__.py:apply_overrides`. Production consumers found: `request_pipeline.run_pipeline`, `api/src/transport_matters/api/v1/breakpoint_routes.py:re_audit_flow`, and `api/src/transport_matters/api/v1/overrides.py:_update_scoped_paused_preview`.
3. Override state writers and readers. Owner: `api/src/transport_matters/overrides/state.py:OverrideStore`. Production writers found: `api/v1/overrides.patch_overrides`, `api/v1/overrides.delete_overrides`, `api/v1/overrides.toggle_overrides`, their `_restore_scope` rollback helper, and `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides`. Production readers found: `request_pipeline.run_pipeline`, `api/v1/breakpoint_routes.re_audit_flow`, `api/v1/overrides.get_overrides`, `_snapshot_scope`, and `_update_scoped_paused_preview`. The API route sync writer is `api/src/transport_matters/shared_proxy/manager.py:SharedProxyManager.set_overrides`, consumed by `api/v1/overrides._sync_shared_overrides`.
4. Changed byte serialization. Owner: `api/src/transport_matters/request_diff.py:outbound_request_if_changed`. Production consumers found: `pause_session._release_payload`, both live paths in `addon_handlers`, `api/src/transport_matters/codex/exchange_derivation.py`, and `exchange_recorder.artifacts.build_request_artifacts`.
5. Adapter serialization. Owner contract: `api/src/transport_matters/adapters/base.py:ProviderAdapter.outbound_request`. Production calls found outside the changed byte owner: `pause_session.handle_breakpoint`, `api/v1/breakpoint_routes._recount_tokens`, `api/v1/breakpoint_routes._validated_release_payload`, `api/v1/exchanges.get_pipeline_tokens`, and `exchange_recorder.stats.stamp_pipeline_tokens`. Provider implementations are `AnthropicAdapter.outbound_request` and `api/src/transport_matters/codex/request_serializer.py:serialize_codex_request` through `CodexAdapter.outbound_request`.
6. Request artifact construction. Owner: `exchange_recorder.artifacts.build_request_artifacts`. Production consumers found: `api/src/transport_matters/exchange_recorder/__init__.py` for fresh, provisional, refreshed, and unparsed HTTP persistence; and `api/src/transport_matters/codex/exchange.py` for Codex provisional and finalized persistence.
7. Tier 1 exchange reads. Owner contract: `api/src/transport_matters/storage/base.py:StorageBackend.read_exchange`, disk implementation `DiskStorageBackend.read_exchange`. Production consumers found: outbound publication and provisional refresh in `exchange_recorder`, Codex rewrite and finalize in `codex.exchange` and `codex.exchange_derivation`, `codex.repair_service`, and the detail and token routes in `api/v1/exchanges`.
8. Wire normalization. Owner: `api/src/transport_matters/session/wire_normalization.py:normalize_request`. The only production consumer found is `api/src/transport_matters/session/wire_store.py:write_wire_exchange`.
9. Token counting. Owner: `api/src/transport_matters/counting.py:TokenCounter.count` behind `TokenCountingClient`. Direct production consumers found: `counting.count_before_after`, `pause_session.fire_pause_count`, and `api/v1/breakpoint_routes._recount_tokens`. `count_before_after` is consumed by `exchange_recorder.stats.stamp_pipeline_tokens` and `api/v1/exchanges.get_pipeline_tokens`; `stamp_pipeline_tokens` is consumed by `exchange_recorder.artifacts.stamped_pipeline_stats`.
10. Message sanitation. Owner: `api/src/transport_matters/overrides/ops_messages.py:sanitize_curated_messages`. The only production consumer found is `overrides._sanitize_current_ir`, which is called once at the end of every `apply_overrides` run.
11. Wire drift detection. Owner: `api/src/transport_matters/drift_capture.py:detect_unknown_shapes`. Production consumers found: `WireDriftObserver._detect` and `api/src/transport_matters/harnesses/certification_evidence.py`.
12. Transcript tailing. Owner: `api/src/transport_matters/index/tailer.py:TranscriptTailer`. Construction and lifecycle consumers found in `api/src/transport_matters/addon_runtime.py`; cursor binding consumers found in `api/src/transport_matters/owned_transcript_binding.py`. Its internal adapter, dispatcher, and storage consumers were not exhaustively enumerated because the proposed firewall only needs its persisted transcript output, not a change to the tailer.
13. Binding identity. Owner: `api/src/transport_matters/shared_proxy/binding.py:ProxyRunBinding`. Consumers were not exhaustively enumerated. Relevant consumers were enumerated: `SharedProxyManager.register`, `api/src/transport_matters/shared_proxy/models.py:binding_payload_from_binding`, `api/src/transport_matters/shared_proxy/addon.py:SharedProxyBindingTable`, `addon_handlers` capture hooks, `shared_proxy.binding.resolve_run_storage`, and credential selection in `SharedProxyAddon.response`.
14. Cache metadata and usage. `api/src/transport_matters/ir.py:SystemPart.cache_hint` is written and read by `AnthropicAdapter._parse_system` and `AnthropicAdapter._system_part_to_dict`, then separated and reconstructed by `session.wire_normalization.normalize_system_part` and `reconstruct_system_part`. Cache usage is produced by Anthropic response parsing and Codex response parsing, projected by `exchange_recorder.stats.build_res_stats`, persisted by `storage.disk`, and written to Postgres by `session.wire_store._exchange_params`. The broad `UsageStats` and `ResStats` consumers were not exhaustively enumerated.

## Ranked ideas

### 1. Durable scoped overlay compiler

Value: 5/5. Feasibility: 4/5.

Store a revisioned manifest outside the addon process. Resolve scope and precedence into one immutable snapshot per run. On each request, select the model and shape specific compiled rule set, apply it once through the existing pipeline owner, and stamp the selected manifest and revision into the exchange audit.

This turns the current session resident override facility into a real overlay without introducing a second request writer. It also makes one turn breakpoint edits the most specific, temporary layer over durable policy.

Current support and consumers: seam inventories 1 through 6 enumerate the pipeline, override state, serialization, and persistence owners and their production consumers. `ProxyRunBinding` already carries run, harness, working directory, space, and worktree identity, but its full consumers were not enumerated; the relevant identity consumers are in inventory 13.

Missing: a product plane manifest store and contract, deterministic cross axis precedence, immutable compiled snapshots, durable enablement state, stable shape identifiers, overlay revision fields in `OverrideAudit` and `ExchangeArtifacts`, and a shared proxy control payload that replaces the complete snapshot atomically. Regular capture version stamping also remains missing.

### 2. Token budget governor for visible context [Novel]

Value: 5/5. Feasibility: 3/5.

Declare a budget partition rather than a list of deletions: reserve tokens for the current user turn, tool schemas, recent tool pairs, and response headroom; spend the remainder on replayed history. The compiler can truncate large tool results, remove complete old tool call and result pairs, collapse repeated harness reminders, and remove oldest replay first. Every decision is deterministic and audited.

For Anthropic, this can operate over explicit messages. Codex needs a separate continuity policy. Later Codex turns may carry `previous_response_id` in `provider_extras`, so trimming the visible `input` does not necessarily cap server side continuity. Removing that field can create a fresh context and must be treated as a high risk continuity break.

Current support and consumers: `InternalRequest.messages`, `ToolResultBlock`, and `provider_extras` are broad IR seams whose consumers were not exhaustively enumerated. Narrow support comes from `overrides.apply_truncate_tool_result`, `overrides.apply_message_block_toggle`, and `sanitize_curated_messages`; their pipeline consumers are inventories 2 and 10. Token counting consumers are inventory 9. Codex continuity fields are preserved by `api/src/transport_matters/codex/request_parser.py:KNOWN_REQUEST_EXTRA_KEYS` and serialized by `serialize_codex_request`; the complete IR consumer set was not enumerated.

Missing: a budget planner, protected component classes, whole message removal operations, pair aware age ordering, a Codex token estimator or provider count seam, explicit continuity semantics, and a maximum allowed delta guard. The first version should use local structural budgets and post delivery accounting, avoiding a blocking count call on the hot path.

### 3. Provenance firewall for harness injections [Novel]

Value: 5/5. Feasibility: 3/5.

Classify each wire component as transcript backed, shipped harness baseline, overlay supplied, or unknown. Suppression rules may target only known baseline injection families. Examples include a repeated reminder template, an unwanted harness policy suffix, or replayed scaffolding absent from the transcript. Unknown components pass through and raise local drift evidence.

This makes “suppress injected reminder” much safer than text search. A normalized template can ignore dynamic timestamps or paths while retaining a shipped baseline shape and content fingerprint as its precondition.

Current support and consumers: wire artifacts and reads are inventories 6 and 7; normalized component hashing is inventory 8; drift detection is inventory 11; transcript production is inventory 12. `ExchangeArtifacts` holds wire evidence and `TranscriptTailer` feeds transcript evidence, but the correlation consumers needed for a complete component origin graph were not enumerated because no such read surface exists today.

Missing: wire versus transcript component correlation, origin labels, shipped shape keyed injection families, normalized reminder templates, component level suppression selectors, and an application audit that distinguishes “matched and removed” from “shape drift, passed through.” Drift must remain local, alerting, and nonblocking as already decided.

### 4. Dynamic capability leases [Novel]

Value: 4/5. Feasibility: 4/5.

Expose only the tool schemas useful for the current phase. A planning turn might receive search and read tools. An implementation turn might add patch and shell tools. A verification turn might retain execution and browser tools. Leases can expire after one turn, after a tool result, or when the track state changes.

This reduces schema tokens and narrows the model's choice surface. It is steering, not enforcement. The harness still owns tool execution.

Current support and consumers: `overrides.apply_tool_toggle` can remove a tool by name and runs through inventory 2. `ToolDef` parsing and serialization consumers found are `AnthropicAdapter._parse_tools`, `AnthropicAdapter._tool_to_dict`, `codex.request_parser._parse_tools`, `codex.request_serializer._tool_to_dict`, `session.wire_normalization.normalize_tool_def`, `reconstruct_tool_def`, and `overrides.audit.tool_chars`. Track classification is owned by `api/src/transport_matters/track_manager.py:TrackManager`; relevant production consumers found are `request_pipeline.run_pipeline`, `exchange_recorder.persist_track_assignment`, `codex.exchange`, and flow state persistence. Internal `TrackManager` consumers were not exhaustively enumerated.

Missing: a capability vocabulary, a turn phase policy, lease state and hysteresis, required tool invariants, and evidence for a tool that was withheld but later needed. Start with static per workspace allowlists before adding phase inference.

### 5. Workspace, harness, and model substitutions

Value: 4/5. Feasibility: 4/5.

Compile placeholders and content fragments from trusted local configuration. A workspace can replace a generic coding constitution with its own, a harness can receive wording suited to its tool semantics, and a model can receive a shorter or more explicit form. Substitution should support append, prepend, replace by semantic selector, and delete.

The manifest must distinguish literal public prompt content from secrets. Secrets should never be eligible template inputs because substitution sends the result to the provider.

Current support and consumers: relevant binding identity consumers are inventory 13. Model and provider live on `InternalRequest`, whose consumers were not exhaustively enumerated. The narrower mutation and serialization consumers are inventories 1, 2, 4, and 5. Current operations can replace or remove an existing system part, but cannot add a new system part.

Missing: safe template variables, append and prepend operations, canonical workspace and worktree scope resolution, model predicates, size limits, secret source rejection, and conflict detection between replacement layers.

### 6. Local counterfactual replay lab [Novel]

Value: 4/5. Feasibility: 4/5.

Apply a candidate overlay to historical Tier 1 requests entirely on the machine. Report match rate, skipped selectors, structural and serialized diffs, character deltas, tool pair cascades, cache impact classification, and provider drift findings. Preserve the original artifacts and write no derived state unless the user explicitly saves a report.

This is the safest way to answer “what would this permanent rule have changed across the last hundred turns?” It can also reveal that a selector only matches one harness shape or that a tool removal deletes more paired content than expected.

Current support and consumers: Tier 1 reads are inventory 7; overlay application is inventory 2; adapter serialization is inventory 5; drift detection is inventory 11. `InternalRequest` consumers were not exhaustively enumerated. No provider call should occur during replay, so authoritative Anthropic counts are unavailable. Character accounting and exact byte deltas remain local.

Missing: a batch reader scoped by owner and workspace, an offline overlay compiler, deterministic replay reports, a no network execution boundary, and aggregate applicability metrics.

### 7. Cache aware mutation planner [Novel]

Value: 4/5. Feasibility: 3/5.

Before applying an overlay, classify its cache effect as preserved, partial bust, full bust, or unknown. Record the first changed component and the affected cache breakpoint. When two placements are semantically equivalent, prefer the placement that preserves the longest stable prefix. Never reorder instructions merely to save cache because order can change behavior.

For Codex, `prompt_cache_key` should remain provider owned unless a certified overlay rule explicitly changes it. An overlay revision may affect cache routing, but forcing a key without provider semantics could create surprising reuse or unnecessary misses.

Current support and consumers: cache metadata and usage consumers are inventory 14. `SystemPart.cache_hint` survives Anthropic round trips. `prompt_cache_key` survives in `codex.request_parser.KNOWN_REQUEST_EXTRA_KEYS` and `serialize_codex_request`. Actual cache read and creation tokens arrive in response usage and are persisted. The full provider data consumer set was not exhaustively enumerated.

Missing: provider specific cache segment analysis, first difference computation, prediction versus observed telemetry, overlay revision correlation, and an explicit unknown result for uncertified shapes.

### 8. Semantic capability translation packs

Value: 4/5. Feasibility: 3/5.

Let a manifest express `capability:shell = off` or `capability:browser = compact` rather than literal tool names. A shipped, shape keyed pack maps that intent to Claude or Codex tool names, schemas, descriptions, and any harness specific reminder. This lets one workspace policy survive harness changes without pretending their vocabularies are identical.

Current support and consumers: literal tool mutations run through inventories 2 and 4. Provider adapter serialization consumers are inventory 5. `api/src/transport_matters/harnesses/compatibility.py:HarnessCompatibilityRelease` already owns wire revision and schema digest declarations; its release consumers were not exhaustively enumerated. The shipped compatibility JSON already packages provider and harness evidence, though the decided overlay baseline identity must be schema shape rather than CLI version.

Missing: semantic capability IDs, per shape mappings, pack validation against shipped baselines, ambiguity handling when several tools share a capability, and a version to shape observation map stamped on every capture.

### 9. Tool contract steering

Value: 3/5. Feasibility: 4/5.

Patch tool descriptions and JSON Schema to remove irrelevant branches, require clearer arguments, constrain enumerations, or add workspace guidance. This can reduce schema tokens and improve calls. It can also tailor one broad harness tool into a narrower model facing contract.

Current support and consumers: `ToolDef.input_schema` is parsed, serialized, normalized, and counted by the exact consumers listed under idea 4. `overrides.apply_tool_description` already changes descriptions through inventory 2. No schema patch operation exists.

Missing: JSON Pointer or semantic schema selectors, schema patch validation, original schema hash preconditions, provider specific schema limits, and output evidence when the model emits arguments outside the advertised schema.

Important boundary: schema rewriting cannot be sold as a security control. The provider can emit invalid arguments and the harness may still execute them. Enforced policy belongs at the tool execution boundary.

### 10. Provider knob profiles

Value: 3/5. Feasibility: 4/5.

Persist named profiles for response budget, temperature, reasoning or thinking, tool choice, service tier, and provider context management. Select them by workspace, harness, model, and track role. This is useful for keeping background agents cheap or ensuring review agents retain a larger response budget.

Current support and consumers: `overrides.apply_sampling_set` and `overrides.apply_provider_extras_set` are dispatched only by `apply_overrides`; its consumers are inventory 2. Their serialized values flow through the adapter consumers in inventory 5. `apply_sampling_set` shape checks five common fields. `apply_provider_extras_set` accepts nested dotted paths. `InternalRequest.provider_extras` has broad consumers that were not exhaustively enumerated.

Missing: named durable profiles, model predicates, provider range validation, certified allowed paths for high impact fields, precedence across profile layers, and cost evidence.

### 11. Explicit model substitution

Value: 3/5. Feasibility: 3/5.

Route selected turns to another model within the same provider. Examples include a cheaper model for routine tool result digestion or a stronger model for review. Rules must be explicit, visible, and tied to a certified target catalog.

Current support and consumers: `api/v1/breakpoint_routes.release_flow` rejects provider changes but does not reject a model change. `_validated_release_payload` serializes the submitted IR through the provider adapter. The direct route consumer is FastAPI. Downstream adapter consumers are inventory 5. Model also feeds exchange identity, statistics, compatibility, and UI consumers; those consumers were not exhaustively enumerated, so feasibility remains medium rather than high.

Missing: a typed `model_set` operation, compatibility and entitlement checks, billing disclosure, response model reconciliation, model rejection handling, and a guarantee that a fallback cannot loop.

### 12. Context virtualization through a local recall tool [Novel]

Value: 5/5. Feasibility: 1/5.

Replace cold replay with a compact local index summary and a synthetic recall tool. The model asks for an older turn or artifact only when needed. Transport Matters resolves the request locally and injects a tool result into the next provider turn. This converts context from an eager payload into demand loaded memory.

Current support and consumers: request adapters can serialize `ToolDef` and tool result blocks through the idea 4 consumer list. Response adapters can observe tool calls. The broad response IR, control plane prompt delivery, and harness input consumers were not enumerated. More importantly, no current owner intercepts a synthetic provider tool call, executes it, and resumes the same harness conversation with a fabricated result.

Missing: a trusted tool execution owner, response side interception, call correlation, local history authorization, a followup turn protocol for both harnesses, loop limits, failure semantics, and a durable proof that fabricated tool results remain distinguishable from harness results. This is a later architecture project.

### 13. Refuse: blind wire to transcript parity

Value: 0/5. Feasibility: technically easy and product harmful.

Transport Matters should refuse a rule that automatically deletes every wire component absent from the transcript. Wire only content includes the system prompt, tool schemas, injected operational reminders, provider continuity fields, and replay the harness deliberately hides. Transcript absence says nothing about dispensability.

Current support and consumers: Tier 1 wire artifacts and transcript tailing are inventories 6, 7, and 12. The consumers required to prove semantic equivalence between every wire component and transcript record do not exist and therefore were not enumerated.

Build targeted suppression with shipped baseline provenance, explicit selectors, and fail open drift behavior. Do not offer global parity as an overlay mode.

## Hard parts

### Prompt cache invalidation

Any mutation inside a cached prefix can invalidate that prefix and everything that depends on it. The cost can exceed the token savings from a trimmed reminder. Current code preserves Anthropic cache hints and records actual cache read and creation tokens, but no pipeline stage reasons about prefix identity.

Every compiled application should record:

1. The original shape and component hashes.
2. The first changed component.
3. The cache breakpoint before and after that component.
4. Predicted impact: preserved, partial bust, full bust, or unknown.
5. Actual cache read and creation usage when the provider responds.

The compiler may move additive content only when placement is semantically equivalent under the shipped provider shape. Unknown shapes must report unknown cache impact and apply only rules whose preconditions still match.

### Token accounting

There are three different quantities:

1. Local structural size before and after, available for both providers through `count_chars_parts` and exact serialized byte length.
2. Provider preflight count, currently authoritative only for Anthropic through `TokenCounter`.
3. Billed or reported response usage after delivery, available from parsed provider responses.

The application audit should preserve all three without laundering an estimate into an exact token count. A live Anthropic overlay can count the same request that is already about to leave for the provider, but a blocking count adds latency and can be rate limited. A local replay lab must make no count call because historical user data must remain on the machine. Codex budgets need conservative local planning until an authoritative count seam exists.

### Provider shape changes

The decided baseline model is correct: shape is primary, every capture carries version, releases ship baselines, version observations accumulate a version to shape map, and drift alerts without blocking.

An overlay selector should therefore carry a shape ID plus local preconditions. Examples include tool name and schema hash, system role and normalized content hash, or message kind and neighboring anchors. When a precondition fails, the rule passes the original component through and emits a local mismatch. Index alone is never a durable selector.

The adapters already preserve unknown top level fields through `provider_extras` and unknown nested fields through `provider_data` or `UnknownBlock`. `WireDriftObserver` scans persisted bytes after capture. This is a sound fail open foundation. Overlay application needs to join that drift evidence to a specific manifest revision.

### Silent behavior degradation

The largest risk is a syntactically valid request that produces a worse agent. Current sanitation can amplify a local edit: removing one side of a tool pair causes `sanitize_curated_messages` to remove the orphan. A system rewrite can preserve schema validity while erasing a harness invariant. A tool schema can steer the model while leaving execution unrestricted.

Each live overlay should therefore carry:

1. Required component and capability invariants.
2. Maximum character and component deltas.
3. Selector applicability expectations.
4. An expiry or review horizon for high risk rules.
5. A kill switch resolved before the next request.
6. Per revision outcome evidence: stop reason, tool calls, tool errors when observable, retries, input and output tokens, cache use, and latency.

These signals support comparison and alerts. They do not prove causality. Automatic rollback should be limited to mechanical failures such as serialization errors, provider rejection, or a required invariant failing before send. Behavioral regressions should alert and require a human decision.

## Minimal kernel

A minimal manifest needs only:

```json
{
  "id": "workspace-context-policy",
  "revision": 3,
  "scope": {
    "worktreeId": "...",
    "harness": "claude",
    "model": "anthropic/claude-opus-4-8"
  },
  "baselineShape": "claude-wire-shape-...",
  "rules": [
    {
      "selector": {"kind": "system", "contentHash": "..."},
      "precondition": {"schemaHash": "..."},
      "operation": {"kind": "remove"},
      "onMismatch": "pass_and_alert"
    }
  ]
}
```

The capture snapshot adds resolved precedence and immutable operation order. Application follows one sequence:

`capture original bytes -> parse IR -> identify shape -> resolve compiled snapshot -> apply -> validate invariants -> serialize if changed -> persist original, curated, and revisioned audit -> release`

The existing pipeline can own the apply, serialize, persist, and release portion. The new work belongs before and around it.

## Recommended order

1. Build the durable manifest, scope resolver, stable selectors, and revisioned audit.
2. Build local counterfactual replay before enabling durable live application.
3. Ship low risk substitutions, static tool pruning, and provider knob profiles.
4. Add the token budget governor with explicit Codex continuity behavior.
5. Add provenance based reminder suppression.
6. Add cache impact prediction and dynamic capability leases after enough observed evidence exists.
7. Keep context virtualization out of the overlay slice until Transport Matters owns a real synthetic tool execution loop.

This order reuses the current request writer, keeps the capture hot path deterministic, and gives every later mechanism a local proof surface before it can affect a live agent.
