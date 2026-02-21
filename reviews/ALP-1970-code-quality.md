# ALP-1970 code quality and KISS review

## Verdict

Ship with polish. The refactor successfully pushes CLI and MCP adapter logic into cm-capabilities and achieves nearly universal adapter thinness. Request/response design is clean and serde-aligned. Three fixable idiom nits: unnecessary clones, a micro-abstraction in scope resolution, and inconsistent error message patterns across adapters.

## What's good

- Adapters are genuinely thin. CLI handlers average 30-35 real logic lines (not counting comments or whitespace). MCP tools average 15-25 lines. Parse surface input, call capability, render result. No bleed.
- Request types (StoreRequest, GetRequest, UpdateRequest) use serde defaults cleanly. No constructor gymnastics. Field validation pushed to capability layer where it belongs.
- Capability input validation is comprehensive and centralized in validation.rs. Parser functions are reused across CLI and MCP paths, eliminating drift.
- Error handling consistent. CmError enum covers all paths, cm_err_to_string provides human-readable recovery guidance across adapters.
- Scope resolution logic is well-isolated in scope.rs. BrowseScopeMode and ScopeResolution types cleanly model the domain concept.
- Test coverage is behavior-focused, not scaffold-heavy. Tests in tests/*.rs exercise real domain logic: validation, defaults, metadata parsing, scope creation.

## KISS violations

1. `crates/cm-capabilities/src/scope.rs:155-234` – The `resolve_auto_scope` function mixes score computation, candidate collection, and confidence rating in one 80-line function. Score thresholds and confidence bands (200, 100, 30, 10) are hardcoded across two functions (score_candidate, confidence_for) creating informal coupling. Suggestion: extract score_candidate as a stateless utility; move thresholds to module-level constants with inline documentation.

2. `crates/cm-cli/src/cli/browse.rs:81` – `include_resolution: include_resolution.then_some(true)`. Mapping a bool to Option<bool> where bool already signals presence. Simpler: `include_resolution: include_resolution.then(|| ())` or restructure the field to be non-optional.

3. `crates/cm-capabilities/src/scope.rs:25-49` – BrowseScopeMode is a single-variant enum (only "resolved" supported). Document clearly that this is forward-reserved and will accept more modes later, or collapse to a unit struct with a const fn for now.

## Adapter thinness check

| handler | logic lines | verdict |
|---------|-------------|---------|
| cm-cli browse | 28 | pass (parse 14 + call 2 + render 12) |
| cm-cli recall | 20 | pass (parse 12 + call 2 + render 6) |
| cm-cli get | 12 | pass (parse 1 + call 2 + render 9) |
| cm-cli update | 35 | pass (parse 20 for stdin/meta + call 2 + render 13) |
| cm-cli stats | 10 | pass (parse 2 + call 2 + render 6) |
| cm-mcp browse | 40 | pass (parse/validate 28 + call 2 + render 10) |
| cm-mcp recall | 28 | pass (parse/validate 18 + call 2 + render 8) |
| cm-mcp get | 8 | pass (parse 1 + call 2 + render 5) |
| cm-mcp update | 8 | pass (parse 2 + call 2 + render 4) |
| cm-mcp stats | 8 | pass (parse 2 + call 2 + render 4) |

All handlers well under 20 real logic lines. Parse costs in MCP/browse/recall are legitimately due to nested scope/mode/kind validation that cannot be further thinned without moving parse logic back to capability layer (where it would bloat that layer instead). Current split is correct.

## Error handling

1. Error message consistency drift: `cm-cli` adapters use `anyhow!("{e}")` to wrap CmError as strings, while MCP tools use `cm_err_to_string(e)` function. Both paths should use the centralized cm_err_to_string from capabilities for byte-identical error messages. crates/cm-cli/src/cli/{get,update,browse,recall,stats}.rs all call `.map_err(|e| anyhow!("{e}"))` which bypasses cm_err_to_string guidance.

2. No .unwrap() or .expect() in capability code outside tests (pass). Project-wide unwrap/expect audit shows only test fixtures and projection code (safe, clearly intentional).

3. Validation error messages are canonical and user-facing, with recovery hints in cm_err_to_string. However, CLI handlers flatten them through anyhow, losing opportunity for structured error recovery. Not a blocker but inconsistent with parent intent.

## Dead code and leftovers

1. `crates/cm-capabilities/src/scope.rs:236-263` – CwdParts::from_path. Struct definition is minimal but over-parameterized. `has_cwd` bool is redundant when `basename.is_some()` exists. Simplify by removing has_cwd and testing basename directly.

2. No #[allow(dead_code)] overrides found. No TODO or FIXME comments found. No unused pub exports identified (all public symbols are used in projection or adapters).

## Rust idiom nits

- `crates/cm-cli/src/cli/{browse,recall}.rs:84,58` – Unnecessary clones: `request.clone()` passed to browse/recall functions. Both functions take ownership of request anyway, so clone is defensive and harmless but signals the caller is unsure of the contract. Remove clones; functions can move the request directly. browse and recall both mutate their parameter (browse moves to effective_request, recall declares mut), so the clones are safe but redundant.

- `crates/cm-capabilities/src/validation.rs:127-154` – MetaInput::into_entry_meta uses nested match on Option fields. Could use Option::map more idiomatically: replace the confidence/expires_at match blocks with map chains for brevity. Current code is readable as-is but less Rustic.

- `crates/cm-capabilities/src/scope.rs:249-254` – Path component iteration collects to Vec and then indexes. Better: use nth directly on the reverse iterator without collecting.

- `crates/cm-cli/src/mcp/tools/browse.rs:62-85` – Repeated match/map pattern for optional string parsing. Introduce a small helper: `parse_optional_string(s, parser)` to reduce repetition.

## Test quality

Tests are behavior-focused and exercise real domain logic, not mocks. store_tests.rs validates defaults, validation, metadata parsing, supersedes handling, and scope auto-creation at the capability level. browse_scope_tests.rs and recall_scope_order_tests.rs test nondeterministic scope resolution and ordering guarantees. Format tests (browse_format_tests.rs, recall_format_tests.rs, get_format_tests.rs) verify text and web projection consistency, covering the edge cases where adapters could diverge. Metadata parity tests ensure CLI and MCP wire shapes roundtrip correctly. No obviously redundant assertions detected.

5 specific notes:
1. store_tests.rs::store_rejects_oversized_body_before_writing validates boundary (MAX_INPUT_BYTES + 1), good.
2. browse_scope_tests.rs tests auto-scope resolution against multiple scope trees with varying project/repo matching. Deterministic and covers real usage.
3. validation.rs tests exercise all parse_kind/confidence/tag_sort enum variants explicitly, no fallback coverage gaps.
4. Meta round-trip tests ensure empty JSON object and fully populated object both parse without assertion burden.
5. Format tests snapshot output shapes but do not assert on exact text content, allowing safe refactoring of presentation.

## Blockers before merge

1. Error message consistency (finding #1 in error handling section). CLI adapters should route CmError through cm_err_to_string instead of anyhow! wrapping to ensure byte-identical error messages across CLI and MCP. This is a stated acceptance criterion for the parent refactor.

2. Update store.rs, get.rs, and update.rs with module-level doc comments clarifying that these modules own input validation and defaults so adapters stay thin. Current docs are clear but scattered; consolidating the intent at the module level would reinforce the architecture.

No other blockers. The violations listed under KISS, idiom, and dead code are polish-level improvements that do not impact correctness or maintainability.
