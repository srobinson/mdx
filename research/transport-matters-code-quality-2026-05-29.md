# Transport Matters - Code Quality Audit: DRY & Dead Code

| Field | Value |
| --- | --- |
| Date | 2026-05-29 |
| Repo | transport-matters |
| Branch | feat/arch-corrections |
| Method | parallel per-partition finders -> per-finding adversarial verification -> cross-module + orphan sweep -> completeness critic -> supplemental harnesses pass |
| Tools | fmm (structural index), ripgrep (repo-wide refs), ruff (F401/F811/F841) |

"Confirmed" means the finding survived an adversarial verifier that actively tried to disprove it (false-positive guard, alternative-explanation search, and a check that the proposed fix would not add more coupling than it removes).

## Executive summary

The codebase is in good overall health: ruff is clean repo-wide, so there is no lint-level dead code, and the duplication that exists is mostly small and local rather than structural rot. The largest DRY clusters are the Codex parser/serializer family (model prefix normalization, content-loop parsing, the `__raw_arguments__` wire sentinel, and content-type tokens all duplicated across `request_parser`, `response_parser`, and `request_serializer`) and the override/addon cluster (char-accounting, scope derivation, and the override-target grammar reimplemented across Python and TypeScript). Two findings are high severity because they carry correctness risk, not just maintenance cost: the char-accounting formula diverges between Python `model_dump_json` and TS `JSON.stringify`, and the exchange storage-path slug is hand-built at seven sites that omit the trailing `Z` the real on-disk directory uses. Real dead code is modest: 17 confirmed dead findings, almost all "exported but no consumer", unused compatibility shims (`turn_boundary.py`, `_run_with_retry`), unreachable guard branches, and four orphaned CSS classes. None of it is load-bearing, and decorator routes, entry points, and dynamic dispatch were deliberately treated as live. The single highest-leverage cleanup is to give the cross-language override-target grammar and char-accounting formula one canonical owner with a shared fixture test, since those are the only duplications where drift fails silently and misleads the user. After that, the cheap structural wins are the Codex model-prefix helper, the exchange storage-path helper, and deleting the `turn_boundary.py` shim.

## Scoreboard

| Metric | Count |
| --- | --- |
| Candidates raised | 83 (79 main + 4 harnesses) |
| Confirmed | 83 |
| Confirmed DRY | 64 |
| Confirmed dead | 19 |
| Uncertain | 1 |
| Rejected (transparency) | 7 |

By severity across all 83 confirmed findings:

| Severity | Count |
| --- | --- |
| High | 2 |
| Medium | 33 |
| Low | 48 |

## DRY findings

### High

### Char-accounting formula duplicated across Python (override_audit/override_ops_messages) and TS (EditorLedger/ToolsSection) with a JSON-serialization divergence risk
- `api/src/transport_matters/override_audit.py:40-51` (count_chars_parts)
- `api/src/transport_matters/override_ops_messages.py:34-44` (count_chars)
- `www/src/components/editor/EditorLedger.tsx:21-34` (countCharsParts)
- `www/src/components/editor/ToolsSection.tsx:60,131`

The same char-accounting algorithm (system text, tool name+description+schema, message-block JSON) lives in four places across both languages, and the message/tool sizes use TS `JSON.stringify` versus Python `model_dump_json`, which differ in key ordering and whitespace. Because the editor presents these as the authoritative pre/post override budget, a silent mismatch misleads the user about how much context an override removes.
**Fix:** Pick one canonical serialization, collapse the two Python copies into `count_chars_parts`, route both TS sites through `countCharsParts`, and add a cross-language fixture test asserting equal totals.
(confidence: high)

### Exchange storage-path literal hand-built at 7 recorder/codex sites, bypassing DiskStorageLayout and diverging on the slug format
- `api/src/transport_matters/exchange_recorder.py:254,262,394,405,464,475`
- `api/src/transport_matters/codex/exchange.py:103,126,229,254,534,541,593,601`
- `api/src/transport_matters/storage/disk_layout.py:28,77-83,110-111,142-143` (DiskStorageLayout)

`DiskStorageLayout` owns the exchange directory naming (slug format `%Y%m%dT%H%M%SZ` with trailing `Z`, `short_id`, `new_exchange_dir`), but recorder and codex hand-build the index `path` with `strftime('%Y%m%dT%H%M%S')` (no `Z`) at seven sites, so the recorded `IndexEntry.path` can differ from the directory actually created. This is a latent path-mismatch bug, not just style.
**Fix:** Route every `IndexEntry.path` through a `DiskStorageLayout` method, delete the local `ts_slug` lines, and add a test asserting the path matches the created directory.
(confidence: high)

### Medium

### _normalise_model / _denormalise_model and the "codex/" prefix duplicated across three files
- `api/src/transport_matters/codex/request_parser.py:79-82` (_normalise_model)
- `api/src/transport_matters/codex/response_parser.py:315-318` (_normalise_model)
- `api/src/transport_matters/codex/request_serializer.py:75-78` (_denormalise_model)

`_normalise_model` is byte-identical in two files, the serializer holds its exact inverse, and the `"codex/"` literal is bare in all three. A prefix-scheme change must touch three places and the copies can silently diverge.
**Fix:** Add one `CODEX_MODEL_PREFIX` constant plus `normalise_codex_model`/`denormalise_codex_model` helpers in `protocol.py` and delete the three local copies.
(confidence: high)

### _parse_user_content and _parse_assistant_content are near-identical content loops
- `api/src/transport_matters/codex/request_parser.py:206-230` (_parse_user_content)
- `api/src/transport_matters/codex/request_parser.py:233-258` (_parse_assistant_content)

Both share the same scaffold (string/non-list short-circuits, UnknownBlock loop, type-dispatch, `keep_raw` bookkeeping) and differ only in the accepted text token and one role-specific branch (image vs refusal).
**Fix:** Extract one `_parse_content(raw, *, text_types, extra_block_handlers)` helper parameterized by the role-specific branches and have both call it.
(confidence: high)

### __raw_arguments__ wire sentinel and tool-argument decoding duplicated across parser and serializer
- `api/src/transport_matters/codex/request_parser.py:262-271` (_parse_function_call)
- `api/src/transport_matters/codex/response_parser.py:287-298` (_parse_tool_arguments)
- `api/src/transport_matters/codex/request_serializer.py:183-196` (_tool_use_to_dict)

The `"__raw_arguments__"` sentinel is a cross-module round-trip contract written by both parsers and read by the serializer, yet it is a bare literal in all three, and the decode logic itself is duplicated between the two parsers.
**Fix:** Introduce a named constant (e.g. `RAW_TOOL_ARGUMENTS_KEY`) and a shared `decode_tool_arguments(value)` helper, reused in both parsers and referenced in the serializer guard.
(confidence: high)

### _resolve_claude_path and _resolve_codex_path are near-identical binary resolvers
- `api/src/transport_matters/cli/start_cmd.py:33-61` (_resolve_claude_path)
- `api/src/transport_matters/cli/codex_cmd.py:43-69` (_resolve_codex_path)

Both share the same shape (disabled short-circuit, resolve via override-or-`which`, red not-found message, install hint, `Exit(2)`) and differ only by binary name, disabled flag, and hint text.
**Fix:** Extract one `resolve_client_binary(*, name, bin_override, disabled, which, not_found_hint)` helper in `launch_runtime.py`; each command passes its own name and hint.
(confidence: high)

### run_start and run_codex duplicate the launch orchestration preamble, --print-command block, and mitmdump argv base
- `api/src/transport_matters/cli/start_cmd.py:181-261` (run_start)
- `api/src/transport_matters/cli/codex_cmd.py:318-403` (run_codex)
- `api/src/transport_matters/cli/start_cmd.py:124-136` (_build_start_invocation argv)
- `api/src/transport_matters/cli/codex_cmd.py:208-222` (_build_codex_invocation argv)

The two commands run the identical six-step resolution sequence, wire `run_with_workspace_manifest` identically, copy-paste the `--print-command` block verbatim, and share the mitmdump argv base except for the `--mode` value and an optional fallback addon.
**Fix:** Hoist the shared preamble into `launch_runtime.py` (`prepare_launch(...)`), and extract `print_invocation(...)` and `build_mitmdump_argv(...)` helpers so both commands parameterize mode and extra addons.
(confidence: high)

### Scope derivation reimplemented 3 ways: _scope_for_paused_flow, _scope_from_params, and override_state.normalize_scope
- `api/src/transport_matters/api/v1/breakpoint_routes.py:45-48` (_scope_for_paused_flow)
- `api/src/transport_matters/api/v1/overrides.py:56-59` (_scope_from_params)
- `api/src/transport_matters/api/v1/overrides.py:62-63` (_paused_scope)
- `api/src/transport_matters/override_state.py:22-27` (normalize_scope)

Three functions compute the identical (run_id-or-LEGACY, track_id-or-run_id) scope tuple; `_scope_from_params` is a redundant wrapper over `normalize_scope`, and `_scope_for_paused_flow` is a line-for-line duplicate of `_paused_scope` in a second file.
**Fix:** Delete `_scope_from_params`, call `normalize_scope((run_id, track_id))` directly at the route sites, and keep a single shared `_scope_for_paused_flow(pf)` that delegates to it.
(confidence: high)

### "Fetch paused flow or raise 404" block duplicated 4x in breakpoint_routes
- `api/src/transport_matters/api/v1/breakpoint_routes.py:135-140` (get_paused_flow)
- `api/src/transport_matters/api/v1/breakpoint_routes.py:182-185` (release_flow)
- `api/src/transport_matters/api/v1/breakpoint_routes.py:203-206` (release_flow_unmodified)
- `api/src/transport_matters/api/v1/breakpoint_routes.py:231-236` (re_audit_flow)

Four handlers open with the identical get_paused/get/None-check sequence that differs only in the error-message wording, and the inconsistent wording is itself a symptom of the copy-paste.
**Fix:** Add one `async _require_paused_flow(flow_id) -> bp.PausedFlow` helper raising one canonical `NotFoundError`, and call it from all four handlers.
(confidence: high)

### Atomic write-via-NamedTemporaryFile boilerplate duplicated between _write_entry_json and _rewrite_transport_json
- `api/src/transport_matters/storage/disk_helpers.py:44-55` (_write_entry_json)
- `api/src/transport_matters/storage/disk_helpers.py:191-206` (_rewrite_transport_json)

Both methods perform the identical 11-line atomic write (NamedTemporaryFile -> `model_dump_json(indent=2)` -> `replace`), differing only in the model variable. They are also the only durable fsync-safe writers in the module, so keeping them in sync matters.
**Fix:** Extract one `_atomic_write_model_json(self, path, model)` helper and have both call it.
(confidence: high)

### _normalise_model / _denormalise_model reimplemented per provider (prefix is the only difference)
- `api/src/transport_matters/adapters/anthropic.py:273-283` (_normalise_model / _denormalise_model)
- `api/src/transport_matters/codex/request_parser.py:79-82` (_normalise_model)
- `api/src/transport_matters/codex/request_serializer.py:75-78` (_denormalise_model)
- `api/src/transport_matters/codex/response_parser.py:315-318` (_normalise_model)

Four functions implement the identical "ensure/strip a `<provider>/` prefix" logic differing only by the literal prefix string, and the codex copies already drift toward each other rather than a single source.
**Fix:** Add shared `normalise_model(model, provider)` / `denormalise_model(model, provider)` helpers taking the provider as a parameter, and delete the four copies.
(confidence: high)

### SSE `data:` line extraction loop duplicated across anthropic and codex response parsing
- `api/src/transport_matters/adapters/anthropic.py:195-205` (_inbound_response_sse line loop)
- `api/src/transport_matters/codex/response_parser.py:50-72` (_parse_sse_event_payloads)

Both providers parse a buffered SSE byte stream with the same boilerplate (decode, skip non-`data:` lines, strip prefix, skip `[DONE]`/empty, `json.loads` with decode-error skip); anthropic inlines it while codex factored it but does not share it.
**Fix:** Extract a shared `iter_sse_data_objects(raw_body) -> Iterator[dict]` into `adapters/_wire.py` and have both consume it.
(confidence: high)

### Anthropic response-content blocks parsed twice: _parse_content_block vs _parse_response_content
- `api/src/transport_matters/adapters/anthropic.py:379-422` (_parse_content_block)
- `api/src/transport_matters/adapters/anthropic.py:548-589` (_parse_response_content)

The text / tool_use / thinking branches are written twice with the same guard conditions and provider-data key-sets; the comments even cross-reference each other ("for parity with"), confirming manual sync. The response variant is a strict subset of the request variant.
**Fix:** Have `_parse_response_content` delegate to per-type helpers shared with `_parse_content_block`, centralizing each (type, key-set) definition.
(confidence: high)

### Scope-from-params fallback logic duplicated in two route helpers, re-deriving normalize_scope
- `api/src/transport_matters/api/v1/breakpoint_routes.py:45-48` (_scope_for_paused_flow)
- `api/src/transport_matters/api/v1/overrides.py:56-63` (_scope_from_params)
- `api/src/transport_matters/override_state.py:17-27` (normalize_scope)

`_scope_for_paused_flow` and `_scope_from_params` are byte-for-byte the same run_id-or-legacy / track_id-or-run_id fallback, which `normalize_scope` already encodes, so the same policy lives in three places. (Overrides-cluster view of the v1-routes scope finding.)
**Fix:** Add one `scope_from_params(run_id, track_id)` in `override_state.py` returning `normalize_scope((run_id or LEGACY_SCOPE_ID, track_id))` and import it in both route files.
(confidence: high)

### _persist_http_exchange and _finalize_http_provisional_exchange are near-identical end to end
- `api/src/transport_matters/exchange_recorder.py:318-441` (_persist_http_exchange)
- `api/src/transport_matters/exchange_recorder.py:530-652` (_finalize_http_provisional_exchange)

Two ~120-line functions share their body almost line-for-line (response extraction, http error-stats override, codex transport block, stats building, token stamping, emit), differing only in minting a new entry versus `model_copy`ing an existing one. Any change to response handling or token stamping must be made twice.
**Fix:** Extract `_extract_response`, `_derive_codex_http`, and `_stamped_pipeline_stats` helpers so both reduce to extract -> derive -> build stats -> assemble entry (new vs copy) -> persist -> emit.
(confidence: high)

### Codex HTTP derivation + transport block duplicated verbatim between the two persist paths
- `api/src/transport_matters/exchange_recorder.py:355-374` (_persist_http_exchange codex block)
- `api/src/transport_matters/exchange_recorder.py:564-583` (_finalize_http_provisional_exchange codex block)

The `if ir.provider == 'codex':` derivation block (lazy import, transport artifacts, `derive_codex_http_turn`, turn-list summary) is identical across both functions except the timestamp source.
**Fix:** Pull it into one `_codex_http_derive(...)` helper called from both sites with the appropriate `ts`.
(confidence: high)

### stamp_pipeline_tokens try/except block copied in both HTTP persist functions
- `api/src/transport_matters/exchange_recorder.py:377-392` (_persist_http_exchange)
- `api/src/transport_matters/exchange_recorder.py:586-601` (_finalize_http_provisional_exchange)

Both functions contain the identical guard wrapping a try/except that calls `_relevant_auth_headers` and `stamp_pipeline_tokens` with the same failure log string.
**Fix:** Extract `_maybe_stamp_tokens(...)` and call it from both.
(confidence: high)

### Exchange storage path literal `exchanges/{ts_slug}-{exchange_id[:8]}/` repeated across recorder and codex/exchange
- `api/src/transport_matters/exchange_recorder.py:254,262 / 394,405 / 464,475`
- `api/src/transport_matters/codex/exchange.py:103,126 / 229,254 / 534,541 / 593,601`

The paired `ts_slug = strftime(...)` + `path=f"exchanges/{ts_slug}-{exchange_id[:8]}/"` idiom appears at 7 distinct sites, scattering the on-disk directory contract as a literal across two files. (Core-runtime view of the cross-module storage-path finding.)
**Fix:** Add one `exchange_dir_path(ts, exchange_id) -> str` helper near `IndexEntry`/storage base and replace all 7 sites.
(confidence: high)

### ExchangeArtifacts curated-IR triple repeated at every persist site
- `api/src/transport_matters/exchange_recorder.py:413-424` (_persist_http_exchange)
- `api/src/transport_matters/exchange_recorder.py:481-487` (_persist_http_provisional_exchange)
- `api/src/transport_matters/exchange_recorder.py:619-621` (_finalize_http_provisional_exchange model_copy)
- `api/src/transport_matters/codex/exchange.py:137-146 / 269`

The request-side artifact fields (`request_curated_raw=outbound_request_if_changed(...)`, `request_curated_ir=_persistable_curated_ir(...)`, `request_audit=audit`) are assembled identically at every persist site, with the curated-raw line alone appearing 4+ times.
**Fix:** Add a `build_request_artifacts(adapter, ir, curated_ir, audit, raw_req)` builder so the curated-IR derivation lives in one place.
(confidence: high)

### blockTarget helper defined identically in three editor files
- `www/src/components/editor/BlockRow.tsx:13-15` (blockTarget)
- `www/src/components/editor/MessagesSection.tsx:24-26` (blockTarget)
- `www/src/components/editor/GlobalSection.tsx:28-30` (blockTarget)

`function blockTarget(msgIdx, blkIdx) { return \`msg:${msgIdx}:blk:${blkIdx}\`; }` is copied byte-for-byte into three files, and the same literal is also inlined in `detail/InspectTab.tsx:125`. The string is a wire contract parsed downstream, so divergence silently breaks override targeting.
**Fix:** Extract `blockTarget` (and a matching parser) into a shared module and import it in all three editor files plus InspectTab.
(confidence: high)

### tool_result override-target construction duplicated in BlockRow and MessagesSection
- `www/src/components/editor/BlockRow.tsx:43` (toolResultTarget)
- `www/src/components/editor/MessagesSection.tsx:28-31` (toolResultTarget)

The `toolresult:${block.tool_use_id}` target string and its `block.type === "tool_result"` guard are duplicated; BlockRow inlines it, MessagesSection wraps it in a local helper. Like blockTarget, this is a parsed wire target that must stay in lockstep.
**Fix:** Co-locate a single `toolResultTarget(block)` helper with the extracted `blockTarget` and import it in both files.
(confidence: high)

### Four near-identical filter+map override-batch builders in ToolsSection
- `www/src/components/editor/ToolsSection.tsx:215-220` (groupAll)
- `www/src/components/editor/ToolsSection.tsx:222-227` (groupNone)
- `www/src/components/editor/ToolsSection.tsx:321-326` (checkAll)
- `www/src/components/editor/ToolsSection.tsx:328-333` (uncheckAll)

Four functions (plus `dropAllMcp` as a fifth variant) share the same skeleton: filter the tool list by `tool_toggle` state, map to a `{ kind, target: \`tool:${name}\`, value }` batch, and dispatch if non-empty. They differ only by source array and enable/disable direction.
**Fix:** Introduce a `bulkToggle(tools, enable, extraFilter?)` helper and a `toolTarget(name)` helper, and route all five builders through them.
(confidence: high)

### EDIT|DIFF tab bar and diff renderer duplicated within TextOverrideEditor
- `www/src/components/editor/TextOverrideEditor.tsx:109-170` (readOnly branch)
- `www/src/components/editor/TextOverrideEditor.tsx:185-272` (editable branch)

The readOnly and editable paths each render a near-identical EDIT|DIFF tablist and a byte-identical diff `<pre>` mapping parts to `<ins>`/`<del>`/`<span>`; the only real difference is the editable path adds a RESET button and a textarea. About 60 lines of structural duplication in one file.
**Fix:** Extract a `DiffPre({ parts })` component and an `EditDiffTabBar({ view, onView, trailing? })`, and render the textarea once behind a `readOnly` flag.
(confidence: high)

### pluralize() is defined identically in CodexTimeline and CodexTransportPanel
- `www/src/components/detail/CodexTimeline.tsx:41-43` (pluralize)
- `www/src/components/detail/CodexTransportPanel.tsx:112-114` (pluralize)

Both files declare an identical `pluralize(count, singular, plural)` returning `${count.toLocaleString()} ${count === 1 ? singular : plural}`, and several other detail components hand-roll the same `!== 1 ? 's'` logic inline.
**Fix:** Hoist one `pluralize()` into `www/src/lib/formatting.ts` and import it in both Codex files.
(confidence: high)

### Context-tokens formula re-inlined in ExchangeTurnCard instead of calling contextTokens() helper
- `www/src/components/ExchangeTurnCard.tsx:164` (panelMetrics)
- `www/src/lib/formatting.ts:38-41` (contextTokens)

`panelMetrics` computes `input + cache_creation + cache_read` by hand, which is exactly the canonical `contextTokens()` helper already imported elsewhere. If the formula changes, this row's "Total" silently drifts.
**Fix:** Import `contextTokens` and use `formatCount(contextTokens(res))` for the total metric.
(confidence: high)

### Raw TanStack query-key tuples for exchanges/exchange/turn-content repeated as untyped literals across hooks
- `www/src/hooks/exchangeStreamEvents.ts:230-237, 261-268`
- `www/src/hooks/useExchanges.ts:177`
- `www/src/hooks/useExchangeStream.ts:51`
- `www/src/hooks/useTurnContent.ts:7`

The same query keys are hand-written as raw arrays across multiple hooks (and `ExchangeDetail.tsx:175`); a typo in any boolean flag or key string silently breaks SSE cache propagation. No query-key factory exists.
**Fix:** Add a query-key factory (`exchangesKey`, `exchangesPrefix`, `exchangeKey`, `turnContentKey`) in `lib/queryKeys.ts` and replace the raw literals.
(confidence: high)

### types.ts IR interfaces are a hand-maintained mirror of the Python Pydantic IR (no codegen)
- `www/src/types.ts:433-529` (ContentBlock/Message/InternalRequest/etc.)
- `api/src/transport_matters/ir.py:19-176` (Pydantic IR models)

The entire IR block in `types.ts` duplicates the Pydantic models field-for-field with no codegen step, and it is already drifting: Python `Message.provider_data` (ir.py:111) is absent from the TS `Message` interface.
**Fix:** Generate the TS IR interfaces from the FastAPI OpenAPI schema or add a contract test; at minimum reconcile the `Message.provider_data` drift now.
(confidence: high)

### OverrideKind enum mirrored member-for-member in Python and TypeScript with no codegen
- `api/src/transport_matters/overrides.py:67-77` (OverrideKind Literal)
- `www/src/types.ts:305-314` (OverrideKind union)

The 9-member override-kind enumeration is declared twice across the language boundary in the same order with no shared schema; adding or renaming a kind de-syncs the server dispatch from the editor UI and fails as a runtime no-op rather than a compile error.
**Fix:** Treat the override-kind set as one contract: generate the TS union from the Python Literal or share a JSON schema, and add a test asserting the member lists match.
(confidence: high)

### Override target-prefix grammar defined in Python override_targets.py and re-hardcoded across 7 www files
- `api/src/transport_matters/override_targets.py:24-57` (parse_* functions)
- `www/src/components/detail/mutations.ts:86-93,226-228`
- `www/src/components/editor/samplingShared.ts:7-16` (THINKING_TARGET/SAMPLING targets)
- `www/src/components/editor/MessagesSection.tsx:25,30`
- `www/src/components/editor/GlobalSection.tsx:29`
- `www/src/components/editor/BlockRow.tsx:14`
- `www/src/components/detail/InspectTab.tsx:96-138`
- `www/src/components/editor/ToolsSection.tsx:92,207-225,323-330`

The override `target` string grammar (`tool:`, `system:`, `toolresult:`, `sampling:`, `provider_extras:`, `msg:{i}:blk:{j}`) is a wire contract owned by Python but reconstructed and parsed by hand across at least 7 TS files; any drift is rejected as an unapplied override with no error surfaced.
**Fix:** Add one `www/src/lib/overrideTargets.ts` with build/parse helpers byte-compatible with `override_targets.py`, route all sites through it, and add a shared fixture test against both parsers.
(confidence: high)

### InternalRequest/IndexEntry test builders (_make_ir, _make_index_entry) copy-pasted across Python test files despite an established *_support.py shared-helper convention
- `api/src/transport_matters/test_breakpoint.py:27-36` (_make_ir)
- `api/src/transport_matters/storage/test_disk.py:32-41` (_make_ir)
- `api/src/transport_matters/storage/test_disk_cache_backfill.py:37-46` (_make_ir)
- `api/src/transport_matters/test_exchange_recorder_emit.py:22-31` (_make_ir)
- `api/src/transport_matters/storage/test_disk.py:44-60` (_make_index_entry)
- `api/src/transport_matters/storage/test_disk_cache_backfill.py:49-65` (_make_index_entry)

An `_make_ir` builder is defined ten times and `_make_index_entry` three times, several byte-identical, while the repo already exposes shared `make_ir`/`make_index_entry` in `*_support.py` modules imported by 4+ other tests. The `storage/` package simply did not adopt the convention. (Surfaced by the completeness-critic test pass.)
**Fix:** Add `storage/test_disk_support.py` exposing `make_ir`/`make_index_entry`, reuse the existing `test_override_support.make_ir` for the root duplicates, and delete the inline copies.
(confidence: high)

### HarnessCapabilities fields duplicated verbatim by meta.py HarnessCapabilitiesResponse
- `api/src/transport_matters/harnesses/__init__.py:36-51` (HarnessCapabilities)
- `api/src/transport_matters/api/v1/meta.py:38-49` (HarnessCapabilitiesResponse)

All 11 boolean fields of the `HarnessCapabilities` dataclass are re-declared field-for-field as a Pydantic `HarnessCapabilitiesResponse`, then populated reflectively via `HarnessCapabilitiesResponse(**asdict(...))`. Adding or renaming a flag means editing two parallel 11-field declarations in lockstep, and the splat breaks only at runtime if they drift. (Supplemental harnesses pass.)
**Fix:** Collapse to one source of truth: make `HarnessCapabilities` a frozen Pydantic model reused in the meta response, or derive the response from the dataclass via pydantic dataclass / `create_model`.
(confidence: high)

### Low

### response_parser reimplements assistant/reasoning text extraction that protocol.py already centralizes
- `api/src/transport_matters/codex/response_parser.py:239-245` (_message_blocks)
- `api/src/transport_matters/codex/response_parser.py:250-259` (_reasoning_block)
- `api/src/transport_matters/codex/protocol.py:248-276` (codex_assistant_item_text / codex_reasoning_item_text)

`protocol.py` exposes the canonical text extractors and `derivation_engine.py` already uses them, but `response_parser` re-walks the same structures inline with the same literal sets, so the WS-derivation and HTTP-SSE paths can drift.
**Fix:** Have `_message_blocks` and `_reasoning_block` delegate text extraction to the protocol helpers, keeping only block-wrapping local.
(confidence: high)

### Normal websocket close codes hardcoded in diagnostics.py instead of CODEX_NORMAL_CLOSE_CODES
- `api/src/transport_matters/codex/diagnostics.py:93` (build_codex_transport_diagnostics)
- `api/src/transport_matters/codex/protocol.py:30` (CODEX_NORMAL_CLOSE_CODES)

`diagnostics.py` inlines `(None, 1000, 1001)` while `protocol.py` defines `CODEX_NORMAL_CLOSE_CODES = frozenset({1000, 1001})`, used everywhere else; the one inlined copy can drift.
**Fix:** Import `CODEX_NORMAL_CLOSE_CODES` and test membership against it.
(confidence: high)

### Codex content-type tokens (input_text/output_text/text/refusal) scattered as bare literals across five files
- `api/src/transport_matters/codex/protocol.py:257-261`
- `api/src/transport_matters/codex/request_parser.py:197,220,247-253`
- `api/src/transport_matters/codex/response_parser.py:240-244`
- `api/src/transport_matters/codex/request_serializer.py:95,174-177`
- `api/src/transport_matters/codex/preserved_raw.py:238-246`

The wire tokens `input_text`/`output_text`/`text`/`input_image`/`refusal` appear as raw literals in five files with the same membership test repeated; `protocol.py` names the event-type tokens but not these content-block tokens.
**Fix:** Define the content-type tokens as named constants/frozensets in `protocol.py` and reference them from the parser, serializer, and preserved_raw.
(confidence: medium)

### _resolve_mitmdump duplicated verbatim in cli/__init__.py and diagnose.py
- `api/src/transport_matters/cli/__init__.py:97-102` (_resolve_mitmdump)
- `api/src/transport_matters/cli/diagnose.py:32-37` (_resolve_mitmdump)

Both define a byte-identical `_resolve_mitmdump()` wrapping `resolve_mitmdump_executable(...)`, whose defaults already match the passed arguments, so both wrappers add nothing.
**Fix:** Drop both wrappers and call `resolve_mitmdump_executable()` directly, or hoist one shared default into `launch_runtime.py`.
(confidence: high)

### _workspaces_root duplicated in instances.py and paths.py
- `api/src/transport_matters/cli/instances.py:40-42` (_workspaces_root)
- `api/src/transport_matters/cli/paths.py:45-47` (_workspaces_root)

Two identical private helpers each just `return default_workspaces_root()`, adding no behavior over the imported function.
**Fix:** Delete both wrappers and call `default_workspaces_root()` at the use sites.
(confidence: high)

### "read_exchange / FileNotFoundError -> NotFoundError" block duplicated in get_exchange and get_turn_content
- `api/src/transport_matters/api/v1/exchanges.py:156-159` (get_exchange)
- `api/src/transport_matters/api/v1/exchanges.py:212-215` (get_turn_content)

Both handlers begin with the identical try/`read_exchange`/except-`FileNotFoundError`-raise-`NotFoundError` block; the third occurrence in `get_pipeline_tokens` is intentionally different and stays separate.
**Fix:** Extract `async _load_exchange_or_404(storage, exchange_id)` and call it from both raising sites.
(confidence: high)

### Not-found message templates duplicated as inline f-strings (5x flow, 4x exchange)
- `api/src/transport_matters/api/v1/breakpoint_routes.py:139,185,197,206,210,264`
- `api/src/transport_matters/api/v1/exchanges.py:159,163,215,257`

The same human-facing "Flow ... not found" and "Exchange ... not found" copy is re-typed at every call site, and the existing Flow-wording inconsistency is a symptom.
**Fix:** Centralize the messages behind the `_require_paused_flow` / `_load_exchange_or_404` helpers or module-level template functions so each string exists once.
(confidence: high)

### Inline exchange_id[:8] in _backfill_cache_creation bypasses DiskStorageLayout.short_id
- `api/src/transport_matters/storage/disk.py:159,165` (_backfill_cache_creation)
- `api/src/transport_matters/storage/disk_layout.py:142-143` (short_id)

The short-id policy is centralized in `DiskStorageLayout.short_id` but `_backfill_cache_creation` re-derives it twice with raw slicing, so a short-id length change silently breaks the backfill path.
**Fix:** Use `self._layout.short_id(exchange_id)` and reuse `find_exchange_dir` so the `[:8]` length lives only in the layout.
(confidence: high)

### Repeated `if block.provider_data: d.update(block.provider_data)` merge boilerplate on serialize
- `api/src/transport_matters/adapters/anthropic.py:313-314, 342-343, 449-450, 460-461, 470-471, 481-482, 487-488, 492-493`
- `api/src/transport_matters/codex/request_serializer.py:243-244` (_thinking_to_dict)

The "build base dict, then merge provider_data back" round-trip restore step appears 8+ times across anthropic serialization helpers and again in the codex serializer.
**Fix:** Add a `restore_provider_data(d, obj)` helper doing the None-check and update, called at each return.
(confidence: high)

### count_chars duplicates count_chars_parts char-accounting logic
- `api/src/transport_matters/override_ops_messages.py:34-47` (count_chars)
- `api/src/transport_matters/override_audit.py:40-51` (count_chars_parts)

`count_chars` and `count_chars_parts` implement identical IR char-accounting; the only difference is one returns a total and the other the (system, tools, messages) tuple, from which the total is trivially recoverable.
**Fix:** Remove `count_chars` (also dead, see dead findings) so `count_chars_parts` is the single source of truth.
(confidence: high)

### Tool char-count formula duplicated across count_chars_parts and apply_tool_toggle
- `api/src/transport_matters/override_audit.py:43-45` (count_chars_parts)
- `api/src/transport_matters/override_ops_messages.py:63-67` (apply_tool_toggle)

The per-tool cost expression `len(name) + len(description) + len(json.dumps(input_schema))` is written verbatim in both, so a cost-model change must be made in lockstep or the audit delta diverges.
**Fix:** Extract a `tool_chars(tool) -> int` helper and call it from both.
(confidence: high)

### Identical JSON-decode try/except in sampling_set and provider_extras_set branches
- `api/src/transport_matters/overrides.py:258-267` (apply_overrides sampling_set branch)
- `api/src/transport_matters/overrides.py:269-279` (apply_overrides provider_extras_set branch)

Both metadata branches decode the JSON value with the identical try/`json.loads`/except pattern, varying only in the `parse_*`/`apply_*` calls.
**Fix:** Extract a `_decode_json_payload(value)` helper (or have the `apply_*` functions own the decode), so both branches share one path.
(confidence: high)

### Index-shift arithmetic duplicated between adjust_system_index and adjust_blk_index
- `api/src/transport_matters/override_targets.py:60-64` (adjust_system_index)
- `api/src/transport_matters/override_targets.py:67-79` (adjust_blk_index)

Both compute the same offset-after-removals shift; `adjust_blk_index` adds a per-message lookup and a None guard, but the load-bearing arithmetic is identical.
**Fix:** Factor a private `_shift_after_removals(index, removed)`; `adjust_system_index` returns it directly, `adjust_blk_index` adds its guard then delegates.
(confidence: medium)

### apply_overrides is ~197 lines with nine structurally parallel dispatch branches
- `api/src/transport_matters/overrides.py:116-313` (apply_overrides)

`apply_overrides` exceeds the 150-line ceiling with nine if/elif branches that each parse the target, type-check, call the matching `apply_*`, and set the result; the per-kind `_PRIORITY` dict already hints at a handler-registry shape.
**Fix:** Move toward a dict-of-handlers keyed by `OverrideKind`; at minimum split the metadata and content branches into helpers to bring the function under 150 lines.
(confidence: medium)

### handle_breakpoint and handle_websocket_breakpoint share ~80% scaffolding
- `api/src/transport_matters/pause_session.py:181-259` (handle_breakpoint)
- `api/src/transport_matters/pause_session.py:262-336` (handle_websocket_breakpoint)

Both run the same pause lifecycle (acquire serializer, compute track fields, `bp.pause`, emit payload, `wait_for` timeout, `pop_paused`, dropped/released branches, resolve), with genuine differences only in HTTP auth/fire-count versus codex transport threading.
**Fix:** Factor the common lifecycle into a `_run_pause(...)` helper (or context manager yielding the popped flow) with transport-specific pre/post hooks.
(confidence: high)

### NOOP_OVERRIDE no-op default repeated in three section files
- `www/src/components/editor/MessagesSection.tsx:179` (NOOP_OVERRIDE)
- `www/src/components/editor/ToolsSection.tsx:303` (NOOP_OVERRIDE)
- `www/src/components/editor/SystemSection.tsx:101` (NOOP_OVERRIDE)

`const NOOP_OVERRIDE = () => {};` is declared module-level in three files purely as the default for the optional `onOverride` prop.
**Fix:** Export one typed `noopOverride` from a shared editor util and import it in all three sections.
(confidence: high)

### override-count label ternary copy-pasted across four section components
- `www/src/components/editor/ToolsSection.tsx:232, 319`
- `www/src/components/editor/SystemSection.tsx:131`
- `www/src/components/editor/MessagesSection.tsx:212-216`
- `www/src/components/editor/SamplingSection.tsx:78`

The `readOnly ? "modified" : count === 1 ? "override" : "overrides"` expression appears five times, each paired with an `overrides.filter(...).length` count rendered in an amber chip; this is the most-repeated pattern in the partition.
**Fix:** Add an `overrideCountLabel(count, readOnly)` helper or an `<OverrideCountChip>` component and call it from all five sites.
(confidence: high)

### Tool character-count formula duplicated between ToolsSection and EditorLedger
- `www/src/components/editor/ToolsSection.tsx:59-61` (toolCharCount)
- `www/src/components/editor/EditorLedger.tsx:23-26` (countCharsParts)

The per-tool size formula `t.name.length + t.description.length + JSON.stringify(t.input_schema).length` is implemented as `toolCharCount` and re-implemented inline in the ledger's reducer; both feed user-facing totals meant to agree.
**Fix:** Export `toolCharCount` and call it from `countCharsParts`, or move the formula to a shared lib.
(confidence: high)

### ROLE_TONE duplicates SECTION_TONE's user/assistant entries; its only use is a dead fallback
- `www/src/components/detail/ContentBlocks.tsx:104-107` (ROLE_TONE)
- `www/src/components/detail/atoms.tsx:39-44` (SECTION_TONE)
- `www/src/components/editor/MessagesSection.tsx:112` (tone)

`ROLE_TONE` is byte-identical to the user/assistant entries in `SECTION_TONE`, and its sole consumer is `SECTION_TONE[role] ?? ROLE_TONE[role]` where `role` is always user/assistant, so the fallback branch is unreachable. Duplicated constant and dead branch.
**Fix:** Delete `ROLE_TONE` and its import; replace line 112 with `const tone = SECTION_TONE[message.role];`.
(confidence: high)

### K-suffix number formatting duplicated between CompressionBar.fmtK and TokenStat
- `www/src/components/detail/CompressionBar.tsx:13` (fmtK)
- `www/src/components/detail/TokenBar.tsx:94-97` (TokenStat.display)

Both implement the same K-suffix rule (threshold 1024, `/1024` to one decimal, `toLocaleString` fallback); the two bars render side by side so the formatting must stay in lockstep but is maintained twice.
**Fix:** Extract a shared `formatCompactChars(value)` into `lib/formatting.ts` and call it from both.
(confidence: high)

### Identical en-US toLocaleTimeString option block triplicated
- `www/src/components/detail/CodexTimeline.tsx:45-51` (formatEventTime)
- `www/src/components/detail/CodexTransportPanel.tsx:23-36` (formatTimestamp)
- `www/src/components/ExchangeDetail.tsx:219-223` (timeStr)

The `{ hour, minute, second: '2-digit' }` options passed to `toLocaleTimeString('en-US', ...)` appear in three places, differing only in null/NaN guarding.
**Fix:** Add one `formatClockTime(ts)` to `lib/formatting.ts` performing the guard and format, and use it in all three sites.
(confidence: high)

### Preview truncation at 220 chars reimplemented with inconsistent ellipsis
- `www/src/components/detail/CodexTransportPanel.tsx:76-89` (payloadPreview)
- `www/src/components/detail/ContentBlocks.tsx:25-31` (blockSummary)
- `www/src/components/editor/SystemSection.tsx:64` (preview)

A 220-char truncate-and-ellipsize is implemented three times with the same magic length, but the Transport panel uses three ASCII dots while the others use the ellipsis glyph, so the marker is visually inconsistent.
**Fix:** Add a `truncatePreview(text, max = 220)` helper with one ellipsis convention and a named `PREVIEW_MAX`, and route all three through it.
(confidence: medium)

### Atmospheric placeholder layout (spinning backdrop + hero stack) duplicated across 4 sites; TraceView and RecallView are near-identical files
- `www/src/routeLayout.tsx:82-116` (WaitingScreen)
- `www/src/components/routes/TraceView.tsx:11-42` (TraceView)
- `www/src/components/routes/RecallView.tsx:11-43` (RecallView)
- `www/src/components/routes/OverlaysView.tsx:91-126` (Atmosphere / EmptyState)

The same scaffold (aria-hidden `spin-gentle h-[90vh] w-[90vh]` backdrop plus a centered hero column with `h-[64px] w-[64px]` icon, uppercase heading, caption) is repeated in four files; TraceView and RecallView differ only in title/caption/copy/accent and are essentially one cloned component. Largest duplication surface in the partition.
**Fix:** Extract a `<RouteAtmosphere title label body? footer? accent? />` primitive and collapse TraceView/RecallView into a single data-driven "coming soon" view.
(confidence: high)

### DepthStyle and TrackDepthStyle re-declared identically and both shadow exported AgentRailStyle
- `www/src/components/ExchangeTurnCard.tsx:8-12` (DepthStyle)
- `www/src/components/TrackHeader.tsx:6-10` (TrackDepthStyle)
- `www/src/lib/agentPalette.ts:3-6` (AgentRailStyle)

`DepthStyle` and `TrackDepthStyle` are byte-identical types declared under different names, and both fully overlap the exported `AgentRailStyle`; the style-object construction is duplicated too.
**Fix:** Export one `DepthRailStyle = AgentRailStyle & { '--track-depth': string }` from `agentPalette.ts` and use it in both, optionally adding a `depthRailStyle(...)` builder.
(confidence: high)

### Relative 'Xm/Xh/Xd ago' time formatting reimplemented in ExchangeTurnCard and OverlaysView
- `www/src/components/ExchangeTurnCard.tsx:45-65` (formatRelativeTime / formatElapsedTime)
- `www/src/components/routes/OverlaysView.tsx:76-89` (formatCreatedAt)

Both convert a timestamp into the same `<60s` / `Xm` / `Xh` / `Xd ago` ladder, recomputing thresholds independently; there is no shared time-formatting helper.
**Fix:** Add `relativeTime(ts)` (and optionally `elapsedTime(ts)`) to `lib/formatting.ts` and have both components call it.
(confidence: high)

### Count + pluralization logic hand-rolled in this partition while a pluralize() helper already exists (and is itself duplicated)
- `www/src/components/TrackHeader.tsx:23-25` (turnLabel)
- `www/src/components/routes/OverlaysView.tsx:60-74` (summarizeOverrides)
- `www/src/components/detail/CodexTimeline.tsx:41-42` (pluralize)
- `www/src/components/detail/CodexTransportPanel.tsx:112-113` (pluralize)

The `${count.toLocaleString()} ${count === 1 ? singular : plural}` pattern is a duplicated `pluralize` helper in detail/, and the same idea is re-open-coded in `turnLabel` and `summarizeOverrides`; no shared pluralize lives in `lib/`.
**Fix:** Promote one `pluralize(count, singular, plural?)` into `lib/formatting.ts`, delete the detail copies, and route the open-coded sites through it.
(confidence: medium)

### Exchange-list cache upsert and delete duplicate the same dual-query-key (live + history) mutation structure
- `www/src/hooks/exchangeStreamEvents.ts:229-238` (upsertExchangeCache)
- `www/src/hooks/exchangeStreamEvents.ts:256-268` (applyExchangeDeletedEvent)

Both mutate the same two caches (`["exchanges", false]` live, `["exchanges", true]` history) and clean up the paired per-exchange caches, differing only in the array transform and invalidate-vs-remove.
**Fix:** Extract `mutateExchangeLists(queryClient, transform)` and `dropExchangeDetail(queryClient, id)` so both sites differ only by the transform.
(confidence: high)

### compareTs and inner compareTrack duplicate ISO-timestamp descending-comparison logic in useExchanges.ts
- `www/src/hooks/useExchanges.ts:36-41` (compareTs)
- `www/src/hooks/useExchanges.ts:144-157` (compareTrack inner)

Both parse two ISO timestamps via `new Date(x).getTime()`, guard with `Number.isNaN`, and return a descending difference; the numeric-descending core is copy-pasted with minor tie-break variation.
**Fix:** Extract `compareIsoDesc(aTs?, bTs?)` (or `tsMillis(s)`) that both comparators call for the timestamp portion.
(confidence: high)

### Every api.ts endpoint repeats the same res.ok-check + JSON-parse boilerplate (17 functions)
- `www/src/api.ts:83-88` (fetchExchanges)
- `www/src/api.ts:90-96` (fetchExchange)
- `www/src/api.ts:98-104` (fetchTurnContent)
- `www/src/api.ts:134-142` (fetchPipelineTokens)
- `www/src/api.ts:172-178` (fetchOverrides)
- `www/src/api.ts:180-193` (patchOverrides)
- `www/src/api.ts:216-222` (fetchBreakpointStatus)
- `www/src/api.ts:286-292` (fetchPausedFlowDetail)
- `www/src/api.ts:313-330` (fetchMeta)

All 17 endpoints hand-roll `request -> if (!res.ok) throw -> return json as T`; the throw line appears 13 times and the parse 10 times, and `throwWithDetail` already abstracts the error path for only 4 of them.
**Fix:** Add `requestJson<T>(path, init?, fallback)` and `requestVoid(path, init?, fallback)` private helpers and route all endpoints through them.
(confidence: high)

### Inline packaged-child-process type duplicated within packageSmoke.ts
- `desktop/src/packageSmoke.ts:34-36` (SpawnPackagedExecutable return type)
- `desktop/src/packageSmoke.ts:144-146` (waitForExit child parameter type)

The structural type `Pick<EventEmitter, "once"> & { kill?: (signal?) => boolean }` is written character-for-character twice in the same file, so a signature drift in one diverges silently.
**Fix:** Extract a named `PackagedChildProcess` type and use it for both the return type and the `waitForExit` parameter.
(confidence: high)

### Backend handshake env var names hardcoded on both sides (desktop TS literals must match api Pydantic env_prefix + fields)
- `desktop/src/backendProcess.ts:84-85`
- `desktop/src/main.ts:88-91,207-209,228`
- `api/src/transport_matters/config.py:21,30-39` (Settings env_prefix/proxy_port/web_port/storage_dir)

The desktop launcher and api backend communicate via `TRANSPORT_MATTERS_*` env vars whose names are hardcoded independently on each side; a rename on either side breaks the launch handshake silently (backend falls back to defaults).
**Fix:** Define the env var names once and share them (a desktop constants module referenced by both files, or a build/test check against the `config.py` field names).
(confidence: high)

### makeEntry IndexEntry fixture re-implemented inline in two TS tests despite shared __test-utils__/exchangeList.ts helper
- `www/src/components/__test-utils__/exchangeList.ts:13-34` (makeEntry canonical)
- `www/src/hooks/useExchanges.test.ts:13-34` (makeEntry inline duplicate)
- `www/src/app.test.tsx:22-44` (makeEntry inline variant)

A shared `makeEntry(overrides)` already exists and is imported by four sibling tests, but two other tests re-declare their own for the same `IndexEntry` shape, so any field added to `IndexEntry` must be touched in three places. (Surfaced by the completeness-critic test pass.)
**Fix:** Import the shared `makeEntry` in both tests (passing differing fields as overrides) and delete the inline copies; consider hoisting the fixture to a top-level `www/src/__test-utils__`.
(confidence: high)

### Claude/Codex descriptors repeat identical capability and pass-through scaffolding
- `api/src/transport_matters/harnesses/__init__.py:78-128` (_CLAUDE_DESCRIPTOR / _CODEX_DESCRIPTOR)

The two descriptor literals repeat the full 11-kwarg `HarnessCapabilities` scaffolding where 8 of 11 flags are identical and `pass_through_policy` matches, so each new harness must restate every unchanging flag. (Supplemental harnesses pass.)
**Fix:** Introduce a `_DEFAULT_CAPABILITIES` base plus `dataclasses.replace(...)` for the differing flags, or a table-driven builder. Low priority with only two harnesses.
(confidence: medium)

## Dead code findings

### Medium

### turn_boundary.py is an orphan backward-compat re-export shim with no production consumers
- `api/src/transport_matters/codex/turn_boundary.py:1-36`
- `api/src/transport_matters/codex/test_turn_boundary.py:5-11`

Dead kind: file. Documented as "Compatibility exports", it only re-exports symbols owned by `protocol.py`; repo-wide search finds exactly one importer, its own test. Live code imports those symbols straight from `protocol.py`, so the shim is unreachable from production.
**Fix:** Repoint `test_turn_boundary.py` imports to `protocol` and delete `turn_boundary.py`.
(confidence: high)

### _run_with_retry is an unused compatibility shim with zero call sites
- `api/src/transport_matters/cli/runner.py:299-348` (_run_with_retry)
- `api/src/transport_matters/cli/runner.py:43` (__all__ entry)
- `api/src/transport_matters/cli/__init__.py:56,74` (import + __all__)

Dead kind: function. Documented as a compatibility adapter but never called; `rg` and fmm show no caller in source or tests. The live commands call `_run_client_with_retry` directly, leaving this exported as inert surface.
**Fix:** Delete `_run_with_retry` and its `__all__`/import entries, plus the now-unused `build_managed_child_env` import at `runner.py:26`.
(confidence: high)

### detectSamplingOverridesStructural is exported but never used in production
- `www/src/components/detail/mutations.ts:299-350` (detectSamplingOverridesStructural)

Dead kind: function. A 52-line exported function whose only non-test importer of `mutations.ts` (InspectTab) imports seven sibling detectors but not this one; fmm and `rg` confirm test-only usage. The Inspect tab's synthesized overrides therefore never reflect sampling/thinking edits. Either dead code or an unfinished feature.
**Fix:** Wire it into `buildSyntheticOverrides` in InspectTab, or delete it plus `encodeReadOnlyOverrideValue` and the test block. Confirm intent with the owner before deleting.
(confidence: high)

### codex/turn_boundary.py is a dead compatibility re-export shim referenced only by its own test
- `api/src/transport_matters/codex/turn_boundary.py:1-36` (module)
- `api/src/transport_matters/codex/test_turn_boundary.py:1-117` (module)

Dead kind: file. (Cross-module view of the same shim.) Re-exports 13 names that live canonically in `protocol.py`; every real consumer imports from `protocol`, the shim is not in `__init__.__all__`, not in pyproject, and not loaded dynamically. A leftover parallel import path from the ALP-2336 namespace rename where the migration finished but the old path was never deleted.
**Fix:** Delete `turn_boundary.py` and its test; if any assertion is unique, move it into a protocol-level test.
(confidence: high)

### Low

### DiskStorageBackend._exchange_dir is never called and ignores its artifacts param
- `api/src/transport_matters/storage/disk.py:492-494` (_exchange_dir)

Dead kind: function. Zero call sites (verified by `rg` and fmm); its body just delegates to `new_exchange_dir`, so the `artifacts` parameter is dead too. All real callers use `_layout.new_exchange_dir` / `exchange_dir_for_write` directly.
**Fix:** Delete the `_exchange_dir` method.
(confidence: high)

### count_chars in override_ops_messages.py is never referenced anywhere
- `api/src/transport_matters/override_ops_messages.py:34-47` (count_chars)

Dead kind: function. Zero call sites in the entire repo (fmm `used_by: []`, `rg` finds only the definition); not in any `__all__`. The live path uses `count_chars_parts` instead.
**Fix:** Delete `count_chars`; any total is the sum of the `count_chars_parts` tuple.
(confidence: high)

### groupTools and pluginLabel exported but have no external callers
- `www/src/components/editor/ToolsSection.tsx:45-57` (groupTools)
- `www/src/components/editor/ToolsSection.tsx:33-37` (pluginLabel)

Dead kind: export. Both are `export`ed with docstrings claiming the detail view reuses them, but `rg` and fmm confirm only intra-file references. The functions are live internally; the `export` keyword and its documented rationale are dead.
**Fix:** Drop the `export` from both (and trim the docstrings), or wire up the detail-view import to make the export real.
(confidence: high)

### TokenBar re-checks context > 0 after already returning when context === 0
- `www/src/components/detail/TokenBar.tsx:15, 24` (TokenBar)

Dead kind: branch. `context` is a sum of three non-negative counts and the `context === 0` early return at line 15 already fires, so the `{context > 0 && (...)}` wrapper at line 24 is always true and its false branch is unreachable.
**Fix:** Drop the redundant `context > 0 &&` wrapper and render the bar unconditionally below the early return.
(confidence: high)

### ExchangeList trackStubs prop and buildExchangeTrackTree fallback are reachable only from tests
- `www/src/components/ExchangeList.tsx:13,142,156-159` (ExchangeList)

Dead kind: branch. The optional `trackStubs` prop and the `trackTree ?? buildExchangeTrackTree(...)` fallback are never exercised outside tests; the sole production caller always passes a precomputed `trackTree`. A parallel tree-building path that duplicates `useExchanges` and exists only because tests bypass the hook.
**Fix:** Have tests render through the same `trackTree` contract the app uses and drop the `trackStubs` prop + inline fallback, or document the standalone build path; do not leave both paths silently divergent.
(confidence: medium)

### createBrowserExchangeStreamSource factory and its 3 exported interfaces have no external/test consumers
- `www/src/hooks/useExchangeStream.ts:7-32` (ExchangeStreamSourceHandlers / ExchangeStreamSource / BrowserExchangeStreamSourceOptions)
- `www/src/hooks/useExchangeStream.ts:21-30` (createBrowserExchangeStreamSource)

Dead kind: function. The factory and its three exported interfaces have zero file-level importers; the factory is called once internally, and the hook's tests stub the global `EventSource` directly. A handler-injection seam designed for an alternative stream source that does not exist.
**Fix:** Inline the `EventSource` construction into the `useEffect` (or one private helper), delete the three exported interfaces and the exported factory, and inline the options type.
(confidence: high)

### Unreachable parts.length===0 branch in displayCwd
- `www/src/lib/formatting.ts:21` (displayCwd)

Dead kind: branch. By line 21 `trimmed` is non-empty (line-18 guard) and trailing separators are stripped (line 17), so `parts` always has >=1 element and the `parts.length === 0` branch never executes. The existing `"/"` test is satisfied by the line-18 guard, not this branch.
**Fix:** Delete line 21; the subsequent length-1 / length>=2 logic covers all reachable inputs.
(confidence: high)

### Dead re-export block in main.ts (window.ts symbols re-exported but never imported)
- `desktop/src/main.ts:25-31` (re-export from ./window.js)

Dead kind: export. `main.ts` is the Electron entrypoint; nothing imports from it except `main.test.ts`, which imports the symbols it needs directly from `./window.js`. fmm confirms the re-exported entries have no consumers. `DEFAULT_WEB_PORT`/`rendererUrlForPort` are independently imported for internal use, so removing the re-export does not affect runtime.
**Fix:** Delete the `export { ... } from ./window.js` block; the symbols remain exported from `window.ts` for any future consumer.
(confidence: high)

### DEFAULT_PROXY_PORT exported but used only inside main.ts
- `desktop/src/main.ts:24` (DEFAULT_PROXY_PORT)

Dead kind: export. Referenced only once, internally; fmm and `rg` find no other reference. The `export` keyword is dead surface; the constant itself is live.
**Fix:** Drop the `export` modifier (module-local const), unless deliberate public-API symmetry with `DEFAULT_WEB_PORT` is intended.
(confidence: high)

### SectionRule component in detail/atoms.tsx is exported but never used
- `www/src/components/detail/atoms.tsx:46-52` (SectionRule)

Dead kind: function. Repo-wide `rg` returns only the definition; zero JSX usages, imports, or test references. `atoms.tsx` is imported by 6 files but none reference `SectionRule`. A fully dead exported component.
**Fix:** Delete the `SectionRule` function.
(confidence: high)

### count_chars in override_ops_messages.py is defined but never called
- `api/src/transport_matters/override_ops_messages.py:34-47` (count_chars)

Dead kind: function. (Cross-module confirmation of the same orphan.) `rg` for the exact token under `api/src/transport_matters` returns only the definition; the codebase uses `count_chars_parts` instead.
**Fix:** Delete `count_chars`; callers needing a total can sum the `count_chars_parts` tuple.
(confidence: high)

### stopSeqsEqual is exported from samplingShared.ts but consumed only inside the same module
- `www/src/components/editor/samplingShared.ts:58-64` (stopSeqsEqual)

Dead kind: export. Referenced only at `samplingShared.ts:72` inside the same file; no other module imports it (fmm and `rg` confirm). The function is reachable, so only the public export surface is unnecessary.
**Fix:** Drop the `export` keyword so the module's public API reflects what is actually consumed.
(confidence: medium)

### Four CSS classes in index.css are never applied (.accent-tick, .armed-glow, .hairline-y, .noise)
- `www/src/index.css:341-350` (.noise)
- `www/src/index.css:402-417` (.hairline-y)
- `www/src/index.css:545-556` (.accent-tick)
- `www/src/index.css:656-658` (.armed-glow)

Dead kind: const. Of 30 hand-authored selectors, these four have zero use sites (verified by extracting every class name and grepping all TS/TSX, HTML, and public assets, plus dynamic-className fragment searches). `.armed-glow` is also a content-duplicate of the live `.arm-toggle` box-shadow. (Surfaced by the completeness-critic pass.)
**Fix:** Delete the four rules (and their `::after`/`::before` and comment headers), or wire any still-wanted affordance to its one call site.
(confidence: high)

### HarnessCapabilities by-id lookup get_harness_descriptor has no production caller
- `api/src/transport_matters/harnesses/__init__.py:139-146` (get_harness_descriptor)

Dead kind: function. The only production consumer (`api/v1/meta.py:111`) iterates `list_harness_descriptors()` and never resolves by id; whole-repo `rg` excluding the defining file and `test_registry.py` returns nothing, with no entry points or dynamic dispatch. It is in `__all__`, so may be intentional forward-looking public API. (Supplemental harnesses pass.)
**Fix:** Owner's call: keep if intentionally public for the planned apply-at-intercept slice; otherwise drop the by-id lookup and keep `list_harness_descriptors` as the sole accessor.
(confidence: medium)

### UnsupportedHarnessError is never raised from a production path
- `api/src/transport_matters/harnesses/__init__.py:70-75` (UnsupportedHarnessError)

Dead kind: class. Raised only inside `get_harness_descriptor` (itself with no production caller) and asserted only in `test_registry.py`; whole-repo `rg` excluding def+test returns nothing, and it is not translated at the FastAPI layer. (Supplemental harnesses pass.)
**Fix:** Life is coupled to `get_harness_descriptor`: keep if that lookup is retained, remove if it is dropped. Do not keep independently.
(confidence: medium)

## Prioritized action list

Ordered by leverage (impact / effort). The cheapest high-impact dedups come first.

1. Give the cross-language override-target grammar one owner: add `www/src/lib/overrideTargets.ts` (build/parse helpers byte-compatible with `override_targets.py`), which also kills the `blockTarget` triplication and `toolResultTarget` duplication in `BlockRow.tsx`/`MessagesSection.tsx`/`GlobalSection.tsx`/`InspectTab.tsx`. Silent-drift correctness risk, modest effort.
2. Unify the char-accounting formula and serialization: collapse `count_chars`/`count_chars_parts` (`override_ops_messages.py`, `override_audit.py`), route `EditorLedger.tsx`/`ToolsSection.tsx` through one `countCharsParts`, fix the `JSON.stringify` vs `model_dump_json` divergence, and add a cross-language fixture test. High-severity correctness fix.
3. Fix the exchange storage-path slug: add one `exchange_dir_path(ts, exchange_id)` (or a `DiskStorageLayout` method) and replace the 7 hand-built sites in `exchange_recorder.py` and `codex/exchange.py`, eliminating the trailing-`Z` mismatch. High-severity, kills two findings at once.
4. Add `CODEX_MODEL_PREFIX` + `normalise_codex_model`/`denormalise_codex_model` in `protocol.py` and delete the four copies across `request_parser.py`/`response_parser.py`/`request_serializer.py` and the per-provider copy in `adapters/anthropic.py`. Cheap, closes two model-prefix findings.
5. Delete the dead compatibility shims: `turn_boundary.py` + its test, `_run_with_retry` (+ `__all__`/import entries and the orphaned `build_managed_child_env` import), and the dead `count_chars`. Pure subtraction, zero risk.
6. Drop dead export surface and unreachable branches: `groupTools`/`pluginLabel`/`stopSeqsEqual` exports, `DEFAULT_PROXY_PORT` export, the `main.ts:25-31` re-export block, `SectionRule`, `_exchange_dir`, `displayCwd` line 21, the `TokenBar` `context > 0` wrapper, and the four orphaned CSS classes. All near-zero effort.
7. Deduplicate the two HTTP persist paths in `exchange_recorder.py`: extract `_extract_response`, `_codex_http_derive`, `_maybe_stamp_tokens`, and `build_request_artifacts` so `_persist_http_exchange` and `_finalize_http_provisional_exchange` stop diverging. Higher effort, removes ~120 lines of parallel logic and several smaller findings.
8. Consolidate the www formatting/util helpers into `lib/formatting.ts`: `pluralize`, `relativeTime`/`elapsedTime`, `formatClockTime`, `formatCompactChars`, `truncatePreview`, and `contextTokens` reuse in `ExchangeTurnCard`. Many low findings collapse into one shared module.
9. Add a query-key factory (`lib/queryKeys.ts`) and route `api.ts` through `requestJson`/`requestVoid` helpers; both remove broad copy-paste across hooks and the 17 endpoint functions.
10. Wire `detectSamplingOverridesStructural` into the Inspect tab or delete it (owner decision), and decide the fate of the harnesses public API (`get_harness_descriptor` / `UnsupportedHarnessError`) since both are in `__all__`.
11. Adopt the shared test-builder convention: add `storage/test_disk_support.py` and reuse `__test-utils__/exchangeList.ts` so `_make_ir`/`_make_index_entry`/`makeEntry` stop being copy-pasted across test files.
12. Lower-priority structural cleanups: collapse `TraceView`/`RecallView` behind a `RouteAtmosphere` primitive, refactor `apply_overrides` under the 150-line ceiling, and collapse the `HarnessCapabilities` / response duplication and descriptor scaffolding.

## Uncertain (needs human judgment)

| Finding | Locations | Reason |
| --- | --- | --- |
| Provider-extras capture done three ways: shared helper exists but top-level captures and codex inline it | `adapters/anthropic.py:50-60,88-90,167-170`; `codex/request_parser.py:60-62,332-334`; `codex/response_parser.py:261-263` | The in-file cleanup (hoist the response `mapped_keys` to a module-level frozenset, share one helper for anthropic's two top-level captures) is a clear win, but the cross-module half of the fix (route codex through the anthropic helper) would add adapter-to-codex coupling and a None/empty + sort-order vs insertion-order mismatch worse than duplicating a trivial one-liner. Half-right, half-harmful. |

## Rejected candidates (transparency)

These were flagged by a finder but disproven by the adversarial verifier, documenting that the verification step works.

| Candidate | Partition | Why rejected |
| --- | --- | --- |
| _run_children wrapper is exercised only by its own tests, never by production code | api/cli | Not unreachable: it is in `__all__`, documented as a public re-export, and exercised by `test_runner.py` as public API. A maintainability smell, not dead code, and the false-positive guard explicitly protects `__all__`/test-only-public symbols. |
| Counter+provider guard for count_tokens partially duplicated between _recount_tokens and get_pipeline_tokens | api/v1-routes | The heavy shared logic is already extracted into `counting.count_before_after`. What remains diverges in guard shape, control-flow position (pre- vs in-lock), and return type (bare `None` vs three typed reason responses); a shared predicate cannot reproduce the reason strings or lock placement. |
| index.jsonl line-by-line JSON parsing hand-rolled in two places | api/storage | Shared shape is trivial (~3 lines) but everything load-bearing diverges: sync (`__init__`) vs async (lock-held), single-object `json.loads` vs multi-object `raw_decode` loop, and continue-and-delete vs break-and-build. A third per-purpose reader confirms this is the deliberate norm. |
| Canonical JSON encode `json.dumps(..., separators, sort_keys).encode()` duplicated | api/adapters | Superficial one-liner match across three different intents (Anthropic wire body, Codex wire body, cache-key hash). Anthropic and Codex do not share a wire format, and the real shared canonicalizer (`codex/json_utils.py`) deliberately uses a different pattern. |
| ResStats and UsageStats redeclare the identical four token fields | www/lib+stores+api | Intentional layer mirroring of two distinct Python models on opposite sides of the IR->storage DAG (`ir.py` UsageStats, `storage/base.py` ResStats), which deliberately do not share a base. A TS base would invent a relationship the source models avoid. |
| OverrideMutateResponse and ToggleResponse repeat the {enabled, audit, curated_ir} shape | www/lib+stores+api | Three DTOs mapping to three distinct REST endpoints; the shared surface is two fields whose nullability is load-bearing (re-audit guarantees non-null, mutate/toggle may be null and the consumer coalesces). A shared base would couple independent contracts and still exclude the third. |
| Two near-identical dialog.showErrorBox error-dialog helpers | desktop/src | Only a single `showErrorBox` line is shared; inputs, message construction, and side effects diverge (`showBackendStartupFailure` also calls `quitApp()`). Two call sites in different modules encoding different intent; dedup adds cross-module coupling worse than the one-line repeat. |

## Coverage & method

Partitions/paths swept (14 total, including the supplemental harnesses pass):

1. `api/codex` (`api/src/transport_matters/codex/`)
2. `api/cli` (`api/src/transport_matters/cli/`)
3. `api/v1-routes` (`api/src/transport_matters/api/`)
4. `api/storage` (`api/src/transport_matters/storage/`)
5. `api/adapters` (`api/src/transport_matters/adapters/`)
6. `api/overrides-cluster` (`overrides.py`, `override_ops_*.py`, `override_state.py`, `override_targets.py`, `override_audit.py`, `addon*.py`, `force_http_fallback_addon.py`)
7. `api/core-runtime` (`supervisor.py`, `track_manager.py`, `exchange_recorder.py`, `exchange_stats.py`, `counting.py`, `ir.py`, `request_pipeline.py`, `pause_session.py`, `breakpoint.py`, `config.py`, `main.py`, and the rest of the runtime root)
8. `api/harnesses` (`api/src/transport_matters/harnesses/`) - supplemental pass over a module the main run missed
9. `www/editor` (`www/src/components/editor/`)
10. `www/detail` (`www/src/components/detail/`)
11. `www/components` (`www/src/components/`, `routeLayout.tsx`, `app.tsx`)
12. `www/hooks` (`www/src/hooks/`)
13. `www/lib+stores+api` (`www/src/lib/`, `www/src/stores/`, `api.ts`, `types.ts`, `browserIdentity.ts`)
14. `desktop/src` (`desktop/src/`)

Tools: fmm (structural index), ripgrep (repo-wide reference checks), ruff (F401/F811/F841).

Caveats:
- Tests were excluded from the DRY sweep except for the dedicated completeness-critic pass, which surfaced the test-builder duplications (`_make_ir`/`_make_index_entry`, `makeEntry`) and the orphaned CSS classes.
- Decorator routes, entry points, and dynamic dispatch were deliberately treated as live and never flagged dead.
- ruff was already clean repo-wide, so no lint-level dead code (unused imports/redefinitions/unused locals) is reported here.
- `main.tsx`, `index.css` (beyond the unused-selector check), and any generated files were out of scope.
