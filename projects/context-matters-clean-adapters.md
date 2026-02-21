# context-matters: clean adapters audit

The context-matters workspace implements a structured context store served as both a CLI and MCP server. This audit examines the boundary between the capability layer (`cm-capabilities`) and the two thin adapters (`cm-cli` and MCP) to expose logic drift — specifically, where validation, defaults, trimming, and error mapping should live in the capability layer but have migrated to adapters or duplicated across them.

## Layering principle

The architecture assigns:
- **cm-capabilities:** owns request/response types, validation rules, defaults, token/byte trimming, advisory messages, error handling, and projection logic. It is channel-neutral and callable from both CLI and MCP with identical semantics.
- **cm-cli/cli and cm-cli/mcp:** surface-only adapters. Their role is input parsing (clap for CLI, JSON deserialization for MCP), optionally reading stdin/environment, and delegating to capability functions. They render output via shared projection types that live in cm-capabilities.

Acceptance criteria: every capability should have request and response types in cm-capabilities. Both adapters should construct those types identically and call the same capability function. Validation, defaults, and error mapping must not duplicate or diverge across adapters.

## Drift map

| Capability | Request type lives in | Response type lives in | Validation | Defaults | Trimming/budgeting | Advisory logic | Verdict |
|---|---|---|---|---|---|---|---|
| recall | cm-capabilities:recall.rs:RecallRequest | cm-capabilities:recall.rs:RecallResult | capability-only | capability-only (limit clamp in validation.rs:clamp_limit) | capability-only (max_tokens budget loop at recall.rs:151) | CLI-only (scope default advisory in cli/scope.rs:resolve_scope) | **minor drift** |
| browse | cm-capabilities:browse.rs:BrowseRequest | cm-capabilities:browse.rs:BrowseResult | duplicated (scope resolution in both cli/browse.rs:52 + mcp/tools/browse.rs:64, kind parsing duplicated) | CLI has resolve_scope_filter with advisory (cli/scope.rs:52), MCP defaults scope to "auto" (mcp/tools/browse.rs:66) | capability-only (limit clamp) | duplicated (CLI in cli/scope.rs:52, MCP prints no advisory) | **major drift** |
| get | none (direct ContextStore call) | projection-only (format_get_view + project_web_get) | duplicated (validation in cli/get.rs:24 + mcp/tools/get.rs:21) | none | duplicated (MAX_BATCH_IDS check in cli/get.rs:27 + mcp/tools/get.rs:24) | none | **major drift** |
| store | none (MCP-only, CLI is stub) | projection-only (format_store_ack) | MCP-only (size checks in mcp/tools/store.rs:67, scope parse, kind parse, confidence parse, expires_at parse, scope chain auto-create) | MCP-only (default_scope, default_created_by in shared.rs:110/115) | MCP-only (scope chain at mcp/tools/store.rs:92) | none | **major drift** |
| update | none (direct ContextStore call) | projection-only (format_update_ack) | duplicated (size checks, UUID parse, at-least-one-field check in both cli/update.rs:40 + mcp/tools/update.rs:40, kind parse, meta parse via shared MetaInput) | none | none | none | **minor drift** |
| deposit | cm-capabilities:deposit.rs:DepositRequest | cm-capabilities:deposit.rs:DepositResult | capability-only | CLI uses resolve_scope (cli/scope.rs:59), MCP uses default_scope via serde default (mcp/tools/deposit.rs:30) | capability-only (max exchanges check at deposit.rs:79) | CLI-only (scope advisory from resolve_scope) | **minor drift** |
| forget | cm-capabilities:forget.rs:ForgetRequest | cm-capabilities:forget.rs:ForgetResult | capability-only | none | capability-only | none | **clean** |
| export | cm-capabilities:export.rs:ExportRequest | cm-capabilities:export.rs:ExportView | capability-only | CLI default "json" at export.rs:38, MCP via serde default (mcp/tools/export.rs:24) | none | none | **minor drift** |
| stats | cm-capabilities:stats.rs:StatsRequest | cm-capabilities:stats.rs:StatsResult | duplicated (tag_sort parse in both cli/stats.rs:21 + mcp/tools/stats.rs:12) | none | none | none | **minor drift** |

## Findings

### 1. Browse scope defaults and advisory diverge between adapters

**What:** CLI browse uses `resolve_scope_filter` (cli/scope.rs:56) which returns `None` when `--scope` is omitted and prints advisory to stderr. MCP browse defaults `scope` to "auto" (mcp/tools/browse.rs:66) when neither scope nor scope_path is provided, skipping the CLI advisory entirely. The two adapters silently implement different default strategies.

**Which adapter:** CLI + MCP (divergent behavior)

**Impact:** An agent calling `cx_browse` without scope gets "auto" resolution (local cwd) by default. A CLI user calling `cm browse` without scope gets no filter (all scopes) with a stderr advisory. Same capability, opposite semantics. This creates a false equivalence: agents may assume CLI `--help` explains MCP defaults.

**Fix direction:** Move scope resolution logic into `cm-capabilities::browse::browse` as a new `BrowseRequest` field or helper. Settle on one default (probably "auto" for agents, but mark as explicit in the request). Make the advisory live in capability as an optional return field, not adapter-specific stderr.

### 2. Store capability missing entirely from cm-capabilities

**What:** The `cx_store` tool owns validation (size checks at mcp/tools/store.rs:67, scope parse, kind parse, confidence parse, expires_at parse, scope chain auto-creation at mcp/tools/store.rs:92), defaults (default_scope, default_created_by via serde defaults), and error mapping. No corresponding `cm_capabilities::store::store` function exists. The CLI is a stub that points to the Curator UI. All write logic is MCP-only.

**Which adapter:** MCP only

**Impact:** The MCP tool is doing heavy lifting (validation + defaults + error handling) that should be in the capability layer. If a future CLI handler is needed, it will duplicate this logic. New adapters cannot reuse a canonical store flow. The validation/default/error semantics are not testable outside the MCP binary.

**Fix direction:** Create `cm-capabilities::store` module with a `StoreRequest` type (holding title, body, kind, scope_path, created_by, metadata fields) and a `store(store: &impl ContextStore, request: StoreRequest, ctx: &WriteContext) -> Result<StoreResult, CmError>` function. Move validation (size checks, kind/confidence/expires_at parsing, scope chain auto-create) into the capability. MCP becomes a pure JSON-RPC adapter: deserialize params into StoreRequest, call capability::store, serialize StoreResult.

### 3. Get and update call ContextStore directly, validation/UUID parsing duplicated across adapters

**What:** `cm get` (cli/get.rs:23) and `cm update` (cli/update.rs:31) call `store.get_entries` and `store.update_entry` directly without routing through a capability function. UUID parsing (cli/get.rs:42 vs mcp/tools/get.rs:44, cli/update.rs:40 vs mcp/tools/update.rs:36) is duplicated in both adapters. The "at least one field provided" validation for update is duplicated (cli/update.rs:74 vs mcp/tools/update.rs:40).

**Which adapter:** CLI + MCP (both)

**Impact:** Validation logic is fragmented. If UUID parsing semantics change (e.g., accepting short IDs), both adapters must be updated. An agent and CLI user calling the same operation may see different error messages if validation diverges. The absence of a canonical request type makes it harder to reason about the operation's contract.

**Fix direction:** Create `cm-capabilities::get` module with `GetRequest { ids: Vec<String> }` and `GetResult { entries: Vec<Entry> }` types. Create `cm-capabilities::update` module with `UpdateRequest { id: String, ...fields }` and `UpdateResult`. Move UUID parsing, validation (batch size, at-least-one-field), and error formatting into the capability layer. Both adapters become wrappers: parse CLI args or MCP JSON into request types, call capability functions, render results via projection helpers.

### 4. Recall scope default advisory is CLI-only

**What:** When recall's `--scope` is omitted, the CLI handler (cli/recall.rs:38) calls `resolve_scope(None)` which returns "global" and prints advisory to stderr. The MCP handler (mcp/tools/recall.rs:45) parses scope as `Some(sp)` when provided or `None` otherwise, delegating to capability::recall which resolves `None` as "global" internally (recall.rs:302 onwards in the ScopeResolve branch). The advisory does not exist on the MCP side.

**Which adapter:** CLI only

**Impact:** CLI users see guidance ("searching 'global'") that MCP users never hear. The scope default is capability-side (correct), but the advisory message is adapter-side (inconsistent). Agents cannot surface the same advisory without reimplementing it.

**Fix direction:** Move the advisory text and logic into `cm-capabilities` (e.g., as a field in `RecallResult` or a separate return value from `recall()` indicating whether a default was applied). Adapters render it directly without reimplementing message text.

### 5. Browse and stats tag/kind parsing duplicated

**What:** `cm browse` (cli/browse.rs:72) and `cx_browse` (mcp/tools/browse.rs:95) both parse the `kind` string to `EntryKind`. `cm stats` (cli/stats.rs:21) and `cx_stats` (mcp/tools/stats.rs:12) both parse `tag_sort` string ("name" or "count") to the `TagSort` enum. The parsing logic is duplicated.

**Which adapter:** CLI + MCP (both)

**Impact:** If the enum variants change or validation rules tighten, both adapters must be updated. Error message wording may diverge. The canonical set of valid values lives nowhere — it's implicit in both adapters' match statements.

**Fix direction:** Move parsing helpers into `cm-capabilities`. For browse, add a `kind: Option<String>` -> `Option<EntryKind>` helper. For stats, add a `parse_tag_sort(s: &str) -> Result<TagSort, String>` helper. Both live in validation.rs or a dedicated parsing module. Adapters call the helpers; capability owns the parsing contract.

### 6. Store and update metadata parsing uses shared MetaInput but validation is MCP-first

**What:** The `MetaInput` struct (validation.rs:42) was defined in cm-capabilities to be reused across adapters. It deserializes wire JSON and projects to `EntryMeta` via `into_entry_meta()` which validates confidence and expires_at. MCP calls this directly (mcp/tools/update.rs:30, mcp/tools/store.rs:82). CLI `cm update` does the same (cli/update.rs:61). However, the MCP `cx_store` handler (mcp/tools/store.rs:76) manually parses confidence (delegating to `parse_confidence` from validation.rs) instead of using `MetaInput`. The two write tools use different deserialization paths.

**Which adapter:** MCP (cx_store divergent from cx_update)

**Impact:** `cx_store` bypasses `MetaInput`, potentially diverging in error handling for invalid confidence or expires_at. If `MetaInput` gains new validation rules, `cx_store` will not benefit. The inconsistency suggests an incomplete refactor.

**Fix direction:** Refactor `cx_store` to deserialize metadata via `MetaInput` the same way `cx_update` does, not via inline parsing. Ensure both tools call identical deserialization code.

### 7. Recall max_tokens trimming is capability-only (good pattern)

**What:** The `--max-tokens` parameter (recall.rs:23) is part of `RecallRequest`. The trimming loop (recall.rs:151) lives in the capability, applying budget to the final result set after post-filtering and sorting. Both CLI and MCP pass max_tokens and get the same trimming behavior.

**Which adapter:** None (correctly capability-owned)

**Impact:** This is the clean pattern. Token budgeting happens once, in the same place, for all callers. Agents and CLI users get identical trimming. If trimming logic changes, one edit fixes both channels.

**Verdict:** `clean` — this is the pattern other capabilities should follow.

### 8. MCP response capping is adapter-specific, not capability-owned

**What:** MCP responses are capped at 16 KB (mcp/mod.rs:51) via `cap_response()` (mcp/mod.rs:84). The capability layer emits full results; the MCP adapter truncates them. CLI has no equivalent cap — it prints full YAML and JSON. The advisory message `"[Truncated: response exceeded 16 KB cap...]"` is MCP-specific.

**Which adapter:** MCP only

**Impact:** This is correctly adapter-owned (MCP has network constraints that CLI does not). However, the decision to cap should be visible in the tool schema (documented in the tool's description). Currently agents learn about truncation only by seeing it in output, not from the schema upfront.

**Verdict:** `adapter-owned` — correct placement because it reflects MCP protocol constraints, not capability semantics. No drift.

## Specific questions answered

### 1. Where does recall's --max-tokens trimming happen?

**Answer:** Capability-only, in `cm-capabilities::recall::recall` at lines 151-160. The trimming loop applies the budget after post-filtering by kinds/tags and sorting by scope depth. Both adapters call the same function and get identical results. This is the correct pattern.

### 2. Where does "default to global scope when none specified" live?

**Answer:** Divided across layers. CLI: `cm recall` calls `resolve_scope(None)` (cli/scope.rs:41) which returns "global" + prints advisory. Capability: `recall::recall` receives `request.scope = Some(ScopePath::parse("global"))` from CLI, or `None` from MCP, then routes `None` to the `ScopeResolve` branch (recall.rs:320 onwards) which calls `store.resolve_context(sp=None, ...)`. The capability does not explicitly default; it hands `None` to the store trait. MCP does not print an advisory. The decision to default is implicit, not declared anywhere as a coherent rule.

**Drift:** CLI defaults + advises in adapter. Capability does not own the default. MCP silently uses default. This is minor drift but confusing — the default should be explicit in `RecallRequest` with an optional advisory field in `RecallResult`.

### 3. Are StoreRequest, RecallRequest, BrowseRequest, DepositRequest, UpdateRequest, ForgetRequest defined once in cm-capabilities and reused?

**Answer:** 
- `RecallRequest` (recall.rs:17): defined in cm-capabilities, reused by both adapters. Clean.
- `BrowseRequest` (browse.rs:14): defined in cm-capabilities, reused by both adapters. Clean.
- `DepositRequest` (deposit.rs:63): defined in cm-capabilities, reused by both adapters. Clean.
- `ForgetRequest` (forget.rs:38): defined in cm-capabilities, reused by both adapters. Clean.
- `StoreRequest`: **does not exist**. MCP `cx_store` deserializes `CxStoreParams` (mcp/tools/store.rs:18) and constructs `NewEntry` directly. CLI is a stub.
- `UpdateRequest`: **does not exist**. Both adapters deserialize `CxUpdateParams` / clap args and construct `UpdateEntry` directly.
- `GetRequest`: **does not exist**. Both adapters deserialize `CxGetParams` / clap args and call `store.get_entries` directly.

**Missing request types:** store, update, get. These bypass the capability layer entirely, or in store's case, exist only in MCP.

### 4. Does MCP tool description prose live in cm-capabilities or is it hand-written in mcp/?

**Answer:** Hand-written in adapter. Each MCP tool has doc comments in its handler file (mcp/tools/*.rs). There is no `spec()` function or doc attribute in cm-capabilities that generates tool descriptions. Tool descriptions are generated by `build.rs` (implied by `CLAUDE.md` note on `tools.toml`) but the source is not visible in this audit. The MCP tool names and descriptions are likely in a separate `tools.toml` or `build.rs` config not examined here.

**Drift:** The tool descriptions (parameter definitions, help text) should live in cm-capabilities as Rust types or doc attributes so they stay in sync with request types. Currently they are hand-written and liable to diverge.

### 5. Does validation.rs get called from both adapters?

**Answer:** Partially. 
- `clamp_limit` (validation.rs:17): used by both recall CLI (cli/recall.rs:51) and recall MCP (mcp/tools/recall.rs:55), browse CLI (cli/browse.rs:87), browse MCP (mcp/tools/browse.rs:100), deposit CLI (not explicitly, uses resolve_scope), deposit MCP (not used).
- `check_input_size` (validation.rs:9): used by recall CLI (cli/recall.rs:35), recall MCP (mcp/tools/recall.rs:39), used in MCP store (mcp/tools/store.rs:67) but NOT called from CLI store (which is a stub).
- `parse_confidence` (validation.rs:22): used only in MCP store (mcp/tools/store.rs:76) and MCP update (via export to mcp/tools/mod.rs:28).
- `MetaInput` (validation.rs:42): used in MCP update (mcp/tools/update.rs:30) and CLI update (cli/update.rs:61).

**Summary:** validation.rs is not uniformly called from both adapters. Some functions are shared, others are MCP-only. There is no systematic validation layer that both adapters depend on — it is ad-hoc.

### 6. Is the JSON output renderer shared between adapters?

**Answer:** Yes, partially. All projection helpers (format_recall_view, project_web_recall, etc.) live in cm-capabilities::projection. Both CLI and MCP call the same projection functions and get byte-identical output. However:
- Write-tool acks (format_store_ack, format_update_ack, format_forget_ack, format_deposit_ack) are shared.
- Read-tool text formatters (format_recall_view, format_browse_view, format_get_view, format_stats_view) are shared.
- Web/JSON projectors (project_web_recall, project_web_browse, project_web_get, project_web_stats) are shared.
- MCP wraps these in its own response envelope (dual_response, yaml_response, json_response in shared.rs:60-88).

**Verdict:** `clean` — the core projection logic is shared. Adapters differ only in their response envelope (YAML vs JSON vs dual).

## Cleanup recommendation

Prioritized by leverage (effort to fix × impact on API/agent clarity):

1. **Extract store to cm-capabilities::store** (high leverage). Currently MCP owns all store validation, defaults, scope auto-create. Move to capability. Benefits: (a) future CLI handler can reuse it; (b) new adapters inherit the same behavior; (c) validation is testable without MCP binary; (d) agent clarity improves (single source of truth). Effort: medium (move ~100 lines from mcp/tools/store.rs to new store.rs module, wire MetaInput deserialization consistently).

2. **Extract get and update to cm-capabilities** (high leverage). Both are currently direct ContextStore calls with duplicated validation. Create GetRequest/GetResult and UpdateRequest/UpdateResult types. Move UUID parsing, batch size checks, at-least-one-field validation into capability. Effort: medium (50 lines per module, moving existing code from adapters).

3. **Unify browse scope defaults** (medium leverage). Browse scope semantics diverge: CLI no-filter vs MCP auto-resolve. Decide on a single default (recommend auto-resolve for agents, explicit in request). Move scope resolution logic into BrowseRequest or a helper function in cm-capabilities. Effort: small (reorganize existing code, add scope default to BrowseRequest).

4. **Centralize recall scope advisory** (low leverage). Move scope-default advisory from CLI to capability. Add optional `scope_defaulted: bool` or `advisories: Vec<String>` field to RecallResult. Both adapters render it. Effort: small (message text already stable, just needs to move).

5. **Unify tag_sort and kind parsing** (low leverage). Extract parse helpers for TagSort and EntryKind into validation.rs or a new parsing module. Both adapters call the helpers. Effort: very small (10 lines).

6. **Document tool schema generation** (clarity, not leverage). Audit where tool descriptions (parameter names, help text, outputSchema) are defined. If hand-written in adapter, migrate to cm-capabilities or build.rs so they stay in sync with request types. Effort: small to medium (depends on current setup).

Do not implement:
- `cm spec` command to show tool schemas (future DX feature, out of scope)
- `--dry-run` validation mode (future feature, out of scope)
- Response streaming or paginated MCP output (protocol change, out of scope)

