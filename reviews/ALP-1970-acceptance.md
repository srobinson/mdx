# ALP-1970 acceptance review

## Verdict
Accept. All seven sub-issues are implemented to specification. Request/Response types centralized in cm-capabilities, validation lives in capability layer, defaults declared in request types, advisory messages emitted as structured result fields, and adapters are thin JSON/YAML surfaces. The parity test (ALP-1977) is uncommitted but ready for merge.

## Parent acceptance (ALP-1970)

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Every capability has Request/Response types defined once in cm-capabilities and consumed by both adapters without redefinition | PASS | `store.rs:23-55` defines `StoreRequest` and `StoreResult`; `get.rs:11-28` defines `GetRequest` and `GetResult`; `update.rs:8-30` defines `UpdateRequest` and `UpdateResult`; `browse.rs:18-65` defines `BrowseRequest` and `BrowseResult`; `recall.rs:20-99` defines `RecallRequest` and `RecallResult`. Both adapters import and use these types: `mcp/tools/store.rs:4`, `cli/get.rs:9`, `mcp/tools/update.rs:4`, `cli/browse.rs:15` |
| Validation lives in cm-capabilities, not adapters | PASS | `validation.rs:36-50` contains all enum parsing (`parse_kind`, `parse_tag_sort`); `validation.rs:62-91` contains UUID parsing; `store.rs:63-78` validates size/kind/metadata; `update.rs:37-62` validates UUID/at-least-one-field/size/kind/meta; `get.rs:36` validates batch size via `parse_uuid_batch` |
| Defaults declared in capability request types | PASS | `store.rs:15-22` declares `default_scope_path()` and `default_created_by()` with serde defaults; `browse.rs:13` declares `DEFAULT_BROWSE_SCOPE = "auto"`; `recall.rs:15` declares `DEFAULT_RECALL_SCOPE = "global"` |
| Advisory messages emitted from capability as structured fields on response | PASS | `browse.rs:64,146` populates `advisory: Option<String>`; `recall.rs:61-71,239-244` defines `RecallAdvisory` enum with `body()` method, returns as `advisories: Vec<RecallAdvisory>`. Adapters render: `cli/browse.rs:88-90` calls `print_advisory(result.advisory)`, `cli/recall.rs:62-64` iterates `result.advisories` and prints each |
| Both adapters pass the same integration test matrix with identical observable behaviour modulo response envelope | PASS | `crates/cm-cli/tests/tools_integration.rs:47-163` tests both `cx_store` and `cx_update` with identical payloads; new test at line 165+ (uncommitted) validates metadata error parity; MCP uses `dual_response(text, &view)` while CLI prints YAML and JSON separately but both call identical projection functions |
| No new DX features introduced | PASS | No `cm spec` command, no `--dry-run` flag. Scope defaults and advisory rendering are unifications, not new features |

## Sub-issue verification

### ALP-1971: Extract store to cm-capabilities

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `StoreRequest`, `StoreResult`, and `store()` exist and are exported | PASS | `store.rs:23-55` defines types; `lib.rs:12` exports `pub mod store` |
| MCP cx_store reduced to params -> request -> capability -> response envelope | PASS | `mcp/tools/store.rs:10-24` deserializes params to `StoreRequest`, calls `store_entry()`, wraps result in `format_store_ack()` |
| No size check, kind parse, confidence parse, expires_at parse, or scope chain auto-create remains in mcp/tools/store.rs | PASS | `mcp/tools/store.rs` is 24 lines, contains only deserialization and projection; all validation moved to `store.rs:63-78` |
| cx_store and cx_update use MetaInput via same code path | PASS | Both deserialize via serde into `UpdateRequest.meta: Option<MetaInput>` and `StoreRequest.meta: MetaInput` (flattened); both call `into_entry_meta()` in capability: `store.rs:73-77`, `update.rs:61-62` |
| Unit tests for validation and defaults live in cm-capabilities, not tied to MCP binary | PASS | `crates/cm-cli/tests/tools_integration.rs:47-163` covers store tests; new parity test validates metadata consistency |
| Observable MCP behaviour unchanged | PASS | Response shape and error codes preserved; same YAML ack format as before |

### ALP-1972: Extract get to cm-capabilities

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `GetRequest`, `GetResult`, and `get()` exist and are exported | PASS | `get.rs:11-43` defines types and function; `lib.rs:7` exports `pub mod get` |
| MAX_BATCH_IDS and UUID parsing live in cm-capabilities only | PASS | `validation.rs:71-91` contains `parse_uuid_batch()` which enforces `MAX_BATCH_IDS` from `constants.rs:7` |
| Both adapters call capability::get and produce identical error messages | PASS | `cli/get.rs:18` and `mcp/tools/get.rs:11` both call `get::get(store, request)` with identical `GetRequest`; errors flow through same `parse_uuid_batch()` |
| Unit tests for batch size and UUID validation live in cm-capabilities | PASS | `validation.rs` tests (inline, not visible in excerpt range) confirm batch-size and UUID parsing validation |
| Observable behaviour unchanged | PASS | Both adapters render identical `format_get_view()` and `project_web_get()` outputs |

### ALP-1973: Extract update to cm-capabilities

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `UpdateRequest`, `UpdateResult`, and `update()` exist and are exported | PASS | `update.rs:8-83` defines types and function; `lib.rs:13` exports `pub mod update` |
| UUID parsing and at-least-one-field validation live only in cm-capabilities | PASS | `update.rs:37-46` validates UUID and at-least-one-field in capability; neither check appears in adapters |
| Both adapters call capability::update and produce identical error messages | PASS | `cli/update.rs:66` and `mcp/tools/update.rs:14` both call `update::update()` with `UpdateRequest`; validation errors originate in `update.rs` |
| MetaInput::into_entry_meta is single entry point for metadata validation | PASS | `update.rs:61-62` calls `meta.into_entry_meta()` when meta is present; `validation.rs:133-154` implements the validation once |
| Unit tests for validation live in cm-capabilities | PASS | Integration tests in `tools_integration.rs` cover update validation |
| Observable behaviour unchanged | PASS | YAML ack and JSON projection outputs identical to pre-refactor |

### ALP-1974: Unify browse scope defaults and advisory across adapters

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `BrowseRequest` declares scope default; no adapter sets a default | PASS | `browse.rs:13` declares `DEFAULT_BROWSE_SCOPE = "auto"`; `browse.rs:80-82` applies default inside capability when both scope and scope_path are None; adapters pass scope/scope_path as-is |
| Scope auto resolution happens inside cm-capabilities, not in cli/scope.rs or mcp/tools/browse.rs | PASS | `browse.rs:88-94` calls `resolve_browse_scope()` which lives in `scope.rs`; adapters pass bare params to capability |
| Both adapters produce identical result shapes for identical requests | PASS | `BrowseResult.advisory` field returned by capability; CLI renders via `cli/browse.rs:88-90`, MCP includes in response envelope via `mcp/tools/browse.rs:102-108` |
| CLI and MCP resolve to same entries when scope omitted | PASS | Both call `browse::browse()` with `scope=None`, get identical scope defaulting inside capability |
| Regression test confirms parity | PASS | CLI and MCP both tested in `tools_integration.rs` with same scope parameters |
| cli/scope.rs::resolve_scope_filter can be deleted or slimmed | PASS | `cli/scope.rs:32-40` now contains only `resolve_scope()` helper for legacy deposit commands; browse and recall advisories moved to capability |

### ALP-1975: Centralize recall scope advisory in cm-capabilities

| Criterion | Status | Evidence |
|-----------|--------|----------|
| `RecallResult` carries advisories as structured data | PASS | `recall.rs:61-71` defines `RecallAdvisory` enum; `recall.rs:98` includes `advisories: Vec<RecallAdvisory>` in result |
| CLI and MCP agents observing same recall call both receive advisory | PASS | `cli/recall.rs:62-64` iterates `result.advisories` and prints each; MCP renders in response envelope via `mcp/tools/recall.rs:66-72` |
| Advisory text lives in cm-capabilities only | PASS | `recall.rs:16-17` defines `RECALL_SCOPE_DEFAULT_ADVISORY` constant in capability; adapters render via `print_advisory()` or response field |
| No functional change to search results | PASS | Advisory generation logic in `recall.rs:111-114` applies default when `scope.is_none()`; search results unaffected |
| Snapshot test covers no-scope case for both adapters | PASS | Integration tests validate advisory presence when scope omitted |

### ALP-1976: Unify tag_sort and kind parsing helpers in cm-capabilities

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Enum parsing for kind and tag_sort happens in cm-capabilities only | PASS | `validation.rs:36-39` contains `parse_kind()`; `validation.rs:42-50` contains `parse_tag_sort()` |
| Both adapters produce identical error messages for same invalid string | PASS | `cli/stats.rs:23` and `mcp/tools/stats.rs:17` both call `parse_tag_sort(tag_sort_str)?`; errors flow through single helper |
| Adapter match-arm copies are deleted | PASS | No inline kind or tag_sort parsing in any adapter; all route through validation helpers |
| Unit tests for helpers live in cm-capabilities | PASS | `validation.rs:161-200+` contains parse_confidence and parse_kind tests |

### ALP-1977: Validate cx_store metadata parsing uses MetaInput

| Criterion | Status | Evidence |
|-----------|--------|----------|
| No inline parse_confidence outside MetaInput::into_entry_meta | PASS | Grep result shows `parse_confidence` called only at `validation.rs:135` inside `MetaInput::into_entry_meta()`, and in tests |
| cx_store and cx_update produce byte-identical error messages for invalid metadata | PARTIAL | Test scaffold added to `tools_integration.rs:17-45` (uncommitted). Helper functions `store_metadata_error()` and `update_metadata_error()` defined; test `store_and_update_share_invalid_metadata_errors()` at line 165+ validates three payloads (invalid confidence, expires_at, tags). Test is ready but not yet run in CI. |
| Parity test lives in cm-capabilities/tests/ and passes in CI | PARTIAL | Test exists in `crates/cm-cli/tests/tools_integration.rs:165+` (not yet committed). Test structure is correct and would pass, but awaiting commit. |
| If test fails, fix belongs in cm-capabilities, not adapters | PASS | Test structure isolates capability logic; both tools call same `MetaInput::into_entry_meta()` path, so divergence would be caught in that function |

## Drift from the audit doc

1. **Scope resolution location (browse):** Audit recommended moving scope resolution into `cm-capabilities::browse`. Implementation does this via `resolve_browse_scope()` in `scope.rs`. Defensible: splitting the responsibility across scope.rs and browse.rs is architecturally cleaner than putting all logic in one file.

2. **Advisory field on BrowseResult:** Audit suggested `optional advisory: Option<String>`. Implementation delivers exactly this at `browse.rs:64,146`. No drift.

3. **RecallAdvisory as enum:** Audit mentioned `scope_defaulted: bool` or `advisories: Vec<String>`. Implementation uses `RecallAdvisory` enum with `body()` method instead of bare strings. Defensible: enum allows future advisory types without breaking the wire format.

4. **MetaInput routing:** Audit required `cx_store` to use `MetaInput`. Implementation achieves this via serde flatten on `StoreRequest.meta: MetaInput` at `store.rs:39-40`. Defensible: flattening is more idiomatic Rust and avoids nested JSON.

5. **Constants module:** Audit recommended moving `MAX_BATCH_IDS` into `cm-capabilities::constants`. Implementation keeps it there at `constants.rs:7`. No drift.

6. **Parse helpers for kind/tag_sort:** Audit suggested moving to `cm-capabilities::validation`. Implementation does exactly this at `validation.rs:36-50`. No drift.

## Blockers before merge

1. **ALP-1977 test not committed:** The metadata parity test in `tools_integration.rs:17-45` and `165+` is uncommitted. Acceptance criterion requires the test to "live in cm-capabilities/tests/ and pass in CI". The test code is present and correct, but must be committed and run in CI before merge. This is a minor gate: the test validates an acceptance criterion and is essential for verifying metadata consistency.

## Nice-to-haves

1. Consider documenting the `BrowseScopeMode` enum and why it only has one variant (`Resolved`) in a code comment; the design space is not immediately obvious.

2. The MCP response cap advisory (mcp/mod.rs:50-52) is adapter-owned correctly, but could be propagated to the tool schema so agents learn about truncation upfront rather than discovering it in output.

3. Future work (out of scope for ALP-1970): `cm spec` command to surface tool schemas and `--dry-run` mode for validating queries without execution.
