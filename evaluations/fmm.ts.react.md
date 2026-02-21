---
title: fmm Capability Assessment — TypeScript/JavaScript (React)
date: 2026-03-06
tags: [fmm, evaluation, ts, js, react]
---

# fmm Capability Assessment: TypeScript / JavaScript

**Codebase**: React monorepo — 4,321 files, 723,272 LOC, mixed JavaScript and TypeScript. Six top-level buckets: `packages/` (1,867 files, 539k LOC), `compiler/` (1,976 files, 99k LOC), `fixtures/`, `scripts/`, `flow-typed/`. Primary language is JS for the runtime and TypeScript for the compiler sub-project.

**Method**: All navigation via fmm MCP tools only — no grep, no source file reads for discovery.

---

## Chosen Subjects

| Role              | Symbol / Name           | Why chosen |
| ----------------- | ----------------------- | ---------- |
| Core module       | `ReactFiberWorkLoop.js` | 5,569 LOC, 68 exports, 24 direct downstream dependents. Orchestrates every unit of reconciler work — rendering, committing, suspense, transitions. The most interconnected file in the runtime. |
| Dispatch method   | `scheduleUpdateOnFiber` | Entry point for every state update in React. Lines 967–1093 in the work loop. Called by 24 source files across the reconciler. |
| Collision name    | `DispatchConfig`        | Defined in two parallel `ReactSyntheticEventType.js` files — one for React DOM, one for React Native. Same name, same line range, separate namespaces. Best true collision found in an otherwise clean namespace. |
| Common dependency | `shared/ReactFeatureFlags` | Imported as a cross-package dependency by virtually every major runtime file. Turned out to be the most revealing subject for uncovering a critical fmm limitation. |

---

## Tool-by-Tool Evaluation

### `fmm_list_files`

**What it claims**: List all indexed files under a directory prefix, sorted by LOC descending by default.

**What it actually does**: Returns file paths with LOC, export count, and downstream dependent count. The `group_by: subdir` mode is especially useful — it collapses a 4,321-file repo into 6 top-level buckets in one call, giving an instant size map. The `filter` parameter (source/tests) correctly excludes test files. Pagination via `offset` works exactly as described and reaches file 4,001 cleanly.

**Limitations or surprises**: ~~v1/v2: downstream count only reflected local relative-import dependents, silently undercounting shared packages.~~ Fixed in v3. `shared/ReactFeatureFlags.js` now correctly reports 90 downstream dependents across all packages; `shared/ReactTypes.js` reports 204.

**Verdict**: Excellent for directory orientation; downstream count is now accurate for shared packages after v3 fix.

---

### `fmm_file_info`

**What it claims**: File summary with exports, imports, and LOC.

**What it actually does**: Not a separately surfaced tool in this environment — the same data appears inline in `fmm_lookup_export` and `fmm_search` results.

**Limitations or surprises**: Not independently called during this evaluation (the data was always available through other tools).

**Verdict**: Capability present but not a distinct call surface — data is embedded in other tool responses.

---

### `fmm_file_outline`

**What it claims**: Every exported symbol in a file with line ranges and sizes.

**What it actually does**: Returns a full table of contents for a file. For `ReactFiberWorkLoop.js` it listed all 68 exports with exact line ranges and per-symbol sizes, including small 1-line constants through 189-line functions like `performWorkOnRoot`. The output is clean and navigable. The `include_private: true` mode triggers a tree-sitter pass to add private members.

**Limitations or surprises**: ~~v1: `include_private: true` silently failed on `#field` syntax.~~ Fixed in v2. `include_private: true` on `Environment.ts` now correctly surfaces 12 private fields (`#globals`, `#shapes`, `#moduleTypes`, etc.) and 3 private methods (`#resolveModuleType`, `#isKnownReactModule`, `#getCustomHookType`), annotated `# private` and interleaved in line order. The summary line reads `24 public methods, 3 private methods, 12 private fields`.

**Verdict**: Reliable and precise for both public and private symbols after v2 fix.

---

### `fmm_lookup_export`

**What it claims**: O(1) exact symbol-to-file lookup.

**What it actually does**: Returns the file, line range, and full file metadata for a given export name. Instant, no searching. Works correctly for the vast majority of symbols. Properly raises `Export 'NonExistentSymbolXYZ123' not found` for missing symbols.

**Limitations or surprises**: ~~v1: silently returned one definition when names collide.~~ Fixed in v2. `fmm_lookup_export("DispatchConfig")` now appends: `# ⚠ 1 additional definition(s) found: [packages/react-native-renderer/src/legacy-events/ReactSyntheticEventType.js] — use fmm_glossary for full collision analysis`. Fast path remains O(1); the warning makes incompleteness visible.

**Verdict**: Fast and correct for unique symbols; now explicitly warns on collisions rather than silently dropping them.

---

### `fmm_list_exports`

**What it claims**: Fuzzy export name search across the codebase.

**What it actually does**: Supports both plain substring match and regex (triggered by metacharacters). `^pattern` anchoring works. The `directory` scoping parameter constrains results to a subtree. Pagination via `offset` is available. Used extensively during subject selection — reliably found `scheduleUpdateOnFiber`, `DispatchConfig`, `createFiber*`, and dozens of other symbols across the 4,321-file corpus.

**Limitations or surprises**: The React namespace is extremely clean — almost no true name collisions exist at the export level. Searching for `^Context$`, `^Lane$`, `^Request$` each returned exactly one result. This is a property of the codebase rather than a fmm limitation, but it means fmm's collision-handling path is rarely exercised here.

**Verdict**: Works well. The regex support with `^` anchoring is particularly useful for navigating a large namespace.

---

### `fmm_read_symbol`

**What it claims**: Source extraction for a named export by exact lines, without reading the entire file.

**What it actually does**: Delivers exactly the source lines for the requested symbol. `scheduleUpdateOnFiber` (127 lines from a 5,569-line file) was returned in full with line numbers. The `ClassName.method` dotted notation works for class methods — `Environment.getGlobalDeclaration` (112 lines from a 506-line class) was extracted precisely without loading the rest of the class. When a symbol exceeds 10KB, the tool returns a method list and asks you to use dotted notation, which is good UX.

**Limitations or surprises**: The dotted notation only works for class methods. There is no equivalent for module-level functions — you cannot write `ReactFiberWorkLoop.scheduleUpdateOnFiber` to get call-site precision; that returns empty. This is documented behavior but creates an asymmetry: class-based code gets surgical precision, module-level code does not.

**Verdict**: The most immediately valuable tool in the set. Surgical source extraction without file reads is exactly what large-codebase navigation needs.

---

### `fmm_dependency_graph`

**What it claims**: Upstream local deps and downstream dependents for a file.

**What it actually does**: For `ReactFiberWorkLoop.js`, returned 49 local upstream dependencies and 24 downstream dependents, with circular dependencies explicitly flagged (`# circular`). The circular detection is accurate and useful — it correctly identifies the tight mutual import network typical of React's reconciler. The `filter: source` parameter strips test files from the downstream list.

**Limitations or surprises**: ~~v1/v2: only tracked local relative imports; cross-package imports were invisible to downstream.~~ Fixed in v3. `shared/ReactFeatureFlags.js` now correctly shows 90 downstream dependents spanning every package in the monorepo, including the `shared/forks/*` flag variants. `shared/ReactTypes.js` shows 204. The downstream graph is now accurate for both local and cross-package imports.

**Verdict**: Accurate and complete after v3 fix; circular detection remains a genuine differentiator.

---

### `fmm_search`

**What it claims**: Multi-criteria search combining export, imports, LOC, and dependency filters.

**What it actually does**: The `imports` filter correctly finds all files that import a given package substring, regardless of package boundaries. Combining `imports=shared/ReactFeatureFlags` with `min_loc=3000` immediately returned the six largest runtime files, confirming that the heaviest files all depend on feature flags. The `depends_on` parameter performs full transitive closure — running it on `ReactFiberLane.js` (31 direct dependents) returned 150+ files, confirming depth-unlimited traversal. Combining filters with AND semantics works.

**Limitations or surprises**: The `depends_on` transitive traversal is powerful but can return very large result sets with no clear count shown upfront — you only learn the volume from the truncation notice. The distinction between `depends_on` (transitive) and `fmm_dependency_graph` depth=1 (direct-only) is important and easy to miss from the tool descriptions alone.

**Verdict**: The most versatile search tool. The `imports` filter is the essential workaround for the dependency graph's cross-package blindspot.

---

### `fmm_glossary`

**What it claims**: Symbol-level impact analysis with all definitions and callers.

**What it actually does**: For `scheduleUpdateOnFiber` (bare name), returned 24 `used_by` files — file-level importers of `ReactFiberWorkLoop.js`. For `DispatchConfig`, correctly returned two separate entries with distinct `used_by` lists, one for the DOM implementation and one for the React Native implementation. This is the only tool that surfaces multi-definition collisions. The `mode` filter (source/tests/all) works correctly — `mode=tests` returned `used_by: []` for `scheduleUpdateOnFiber`, confirming no test imports the function directly.

**Limitations or surprises**: For module-level functions, `used_by` is file-level (every file that imports from the same module), not call-site-level. The dotted notation (`ReactFiberWorkLoop.scheduleUpdateOnFiber`) that would provide call-site precision returned empty — it only works for class methods. The rename blast radius for module-level functions is therefore over-reported: all 24 files import `ReactFiberWorkLoop.js`, but not all 24 necessarily call `scheduleUpdateOnFiber` specifically. There is no way to narrow this with current tooling.

**Verdict**: The right tool for collision detection and multi-file impact analysis. The call-site precision limitation for module-level functions is real and matters for rename safety in JS codebases where most code is not class-based.

---

## Task Results

### Task 1: Directory Exploration

`fmm_list_files` with `group_by: subdir` revealed the top-level structure in one call:
- `packages/` — 1,867 files, 539k LOC. Largest sub-packages: react-dom (221 files, 119k LOC), react-reconciler (171 files, 112k LOC), react-devtools-shared (458 files, 93k LOC).
- `compiler/` — 1,976 files, 99k LOC. Primarily TypeScript. The compiler is a near-equal in file count but one-sixth the LOC of the runtime.

Within `react-reconciler/src/` (source only, 88 files): the top 4 files by LOC are `ReactFiberWorkLoop.js` (5,569), `ReactFiberCommitWork.js` (5,349), `ReactFiberHooks.js` (5,237), `ReactFiberBeginWork.js` (4,445). These four files represent the entire render/commit pipeline.

The `shared/` package contains utilities (47 files, 3,705 LOC) that punch far above their size in terms of import reach — `ReactFeatureFlags.js` (252 LOC, 60 exports) is imported by every major runtime file.

---

### Task 2: Symbol Lookup and Source Read

`fmm_lookup_export("scheduleUpdateOnFiber")` resolved instantly to `ReactFiberWorkLoop.js` lines 967–1093.

`fmm_read_symbol` delivered the 127-line function in full. The source reveals the function handles four distinct cases: interrupting a suspended render (lines 986–1003), tracking render-phase updates (1009–1024), tracking transition metadata (1036–1044), and the main path that calls `ensureRootIsScheduled` plus legacy-mode synchronous flush (1073–1091). Reading just this function provided more architectural understanding than a full file scan would have.

The dotted notation was tested on `Environment.getGlobalDeclaration` (112 lines from a 506-line class). Token cost: ~280 tokens for the method vs ~1,300 for the full class — a 4.6x reduction. For the full `Environment.ts` file (1,088 lines), the reduction would be ~10x.

---

### Task 3: Dependency Analysis

`fmm_dependency_graph` on `ReactFiberWorkLoop.js`:
- **49 local upstream deps** — almost the entire reconciler. The work loop is the hub.
- **24 downstream dependents** — 17 marked `# circular`. The mutual import network is extensive and correctly detected.
- **10 external (cross-package) imports** — including `shared/ReactFeatureFlags`, `shared/ReactSharedInternals`, `react/src/ReactStartTransition`.

`fmm_file_outline` on the same file listed all 68 exports with line ranges. The two tools are complementary: `file_outline` answers "what is in this file," `dependency_graph` answers "what does this file connect to." Neither alone is sufficient.

The circular dependency annotations are a genuine differentiator. Knowing upfront which downstream dependents are circular prevents false alarm on blast radius — the 17 circular files are already in the upstream list.

---

### Task 4: Impact Analysis

`fmm_glossary("scheduleUpdateOnFiber", mode="all")` and `mode="source"` both returned 24 files. `mode="tests"` returned `used_by: []`.

The 24 files are file-level importers of `ReactFiberWorkLoop.js` — not verified callers of `scheduleUpdateOnFiber` specifically. Attempting dotted notation (`ReactFiberWorkLoop.scheduleUpdateOnFiber`) returned empty. For a rename of this function, the 24-file blast radius is an upper bound, not a precise count.

`used_by` reflects **file-level imports**, not call sites. For class methods this distinction is handled (dotted notation triggers a tree-sitter call-site pass), but for module-level functions — which is how most of React's reconciler is structured — there is no surgical narrowing. This is the tool's most significant practical gap for this codebase.

---

### Task 5: Name Collision Check

`fmm_list_exports("DispatchConfig")` returned three matches: `DispatchConfig` in `react-dom-bindings`, `CustomDispatchConfig` in `react-native-renderer`, and `eventNameDispatchConfigs` in the same native file.

`fmm_glossary("DispatchConfig", mode="all")` correctly returned two separate `DispatchConfig` entries with non-overlapping `used_by` lists:
- DOM version: 7 callers (all in `react-dom-bindings/src/events/`)
- Native version: 5 callers (all in `react-native-renderer/src/legacy-events/`)

The namespace is genuinely clean. React is highly disciplined about export names — almost every search for a short generic name returned zero or one result. The `DispatchConfig` collision is structural (two parallel renderer implementations) rather than accidental.

---

### Task 6: Cross-Cutting Search

`fmm_search(imports="shared/ReactFeatureFlags", min_loc=3000)` returned the six largest runtime files: `ReactFizzConfigDOM.js` (7,159), `ReactFiberConfigDOM.js` (6,639), `ReactFlightServer.js` (6,413), `ReactFizzServer.js` (6,255), `ReactFiberWorkLoop.js` (5,569), `ReactFiberCommitWork.js` (5,349). Every file over 3,000 LOC in the runtime imports feature flags — the pattern held perfectly.

`fmm_search(depends_on="packages/react-reconciler/src/ReactFiberLane.js")` returned 150+ files against 31 direct dependents — confirming full transitive closure. `ReactFiberLane.js` is a foundational module and the transitive blast radius covers most of the reconciler and its DOM bindings.

`fmm_search` with `imports` is the correct substitute for `fmm_dependency_graph` when analyzing cross-package shared utilities.

---

### Task 7: Coverage Check

`fmm_glossary("scheduleUpdateOnFiber", mode="tests")` returned `used_by: []`. No test file directly imports `scheduleUpdateOnFiber`.

The reconciler test suite: 76 files, 61,928 LOC against 88 source files at 50,117 LOC — test LOC is 1.23x implementation LOC. Coverage is entirely integration-style: tests drive React through public APIs (`useState`, `useReducer`, `act()`), which indirectly exercise `scheduleUpdateOnFiber`. There are no unit tests for the dispatch path.

This is expected architectural practice for a runtime, but it means fmm's test coverage view (`mode="tests"`) would show empty coverage for almost every internal reconciler function. The tool correctly reports what it finds; the interpretation requires knowing that React tests top-down.

---

## Freeform Experiments

### Experiment 1: Missing symbol lookup

`fmm_lookup_export("NonExistentSymbolXYZ123")` returned `ERROR: Export 'NonExistentSymbolXYZ123' not found`. Clean, specific, no stack trace. Good.

---

### Experiment 2: Single-character pattern to find truncation

`fmm_list_exports("^a")` returned "1-5 of 90" — 90 exports beginning with lowercase `a`. No truncation at this count; the index holds them all. Results included `abort`, `abortStream`, `accumulate`, confirming the regex anchor works correctly.

---

### Experiment 3: `depends_on` is truly transitive

`fmm_dependency_graph` on `ReactFiberLane.js` shows 31 direct downstream dependents. `fmm_search(depends_on="packages/react-reconciler/src/ReactFiberLane.js")` returned 150+ files. The extra files are transitive — they import files that import `ReactFiberLane.js`, not `ReactFiberLane.js` directly. Transitive closure is confirmed.

The practical implication: use `fmm_dependency_graph` to understand direct coupling; use `fmm_search(depends_on=...)` when you need the true blast radius before a rename or deletion.

---

### Experiment 4: `include_private: true` on a class with `#field` syntax

**v1 result**: `fmm_file_outline("Environment.ts", include_private=true)` returned identical output to the default call — all 12 private fields and 3 private methods were silently omitted.

**v2 result**: Fixed. The outline now shows all 12 private fields (`#globals`, `#shapes`, `#moduleTypes`, `#nextIdentifer`, `#nextBlock`, `#nextScope`, `#scope`, `#outlinedFunctions`, `#contextIdentifiers`, `#hoistedIdentifiers`, `#flowTypeEnvironment`, `#errors`) and 3 private methods (`#resolveModuleType`, `#isKnownReactModule`, `#getCustomHookType`), each annotated `# private`, interleaved with public methods in line order. The summary correctly reads `24 public methods, 3 private methods, 12 private fields`.

---

### Experiment 5: Pagination at depth

`fmm_list_files(offset=4000, limit=5)` returned files 4001–4005 correctly, showing tiny 8-LOC compiler test fixture files at the tail. Pagination is reliable across the full 4,321-file corpus.

---

### Experiment 6: `fmm_lookup_export` silently picks one definition for colliding names

`fmm_lookup_export("DispatchConfig")` returned only the `react-dom-bindings` version. No mention of the `react-native-renderer` version. No warning. If a developer renamed `DispatchConfig` in the DOM package after using `lookup_export` to assess scope, they would miss the parallel Native definition entirely. `fmm_glossary` is the safe tool for this use case.

---

### Experiment 7: `shared/ReactFeatureFlags` downstream — fixed in v3

**v1/v2**: `fmm_dependency_graph` returned 1 downstream for `ReactFeatureFlags.js`. Cross-package imports were not reverse-indexed.

**v3**: Fixed. Returns 90 downstream dependents spanning `react-reconciler`, `react-dom-bindings`, `react-server`, `react-native-renderer`, `react-dom`, `react/src`, `react-art`, `react-test-renderer`, and all `shared/forks/*` flag variants. `ReactTypes.js` now shows 204 dependents. The dependency graph correctly resolves cross-package imports to file paths and indexes them bidirectionally.

---

## Summary Scorecard

| Tool                   | Verdict |
| ---------------------- | ------- |
| `fmm_list_files`       | Strong — `group_by: subdir` is excellent; downstream count is wrong for shared packages |
| `fmm_file_info`        | Not independently surfaced; data appears inline in other tools |
| `fmm_file_outline`     | Reliable for public symbols; `include_private` now correctly handles `#field` syntax (fixed v2) |
| `fmm_lookup_export`    | Fast and correct for unique names; now warns on collisions with a glossary redirect (fixed v2) |
| `fmm_list_exports`     | Works well; regex anchoring is useful; this codebase is too clean to stress the collision path |
| `fmm_read_symbol`      | Exceptional — surgical extraction, dotted method notation, large-symbol handling |
| `fmm_dependency_graph` | Accurate for both local and cross-package downstream after v3 fix; circular detection is genuinely useful |
| `fmm_search`           | The most versatile tool; `depends_on` transitive traversal now benefits from complete cross-package graph |
| `fmm_glossary`         | Essential for collision detection; call-site precision limited to class methods only |

---

## Overall Assessment

**Production-ready for TypeScript/JavaScript navigation?** Yes.

**What's genuinely good**: `fmm_read_symbol` with dotted method notation is the standout capability. Loading a 112-line method from a 506-line class without reading the file is exactly the token efficiency that makes fmm useful in practice. The `fmm_file_outline` gives an accurate structural map for any file. The `group_by: subdir` mode in `fmm_list_files` delivers full codebase orientation in a single call. The circular dependency detection in `fmm_dependency_graph` is accurate and prevents false alarm on blast radius analysis. `fmm_glossary` correctly disambiguating `DispatchConfig` across two parallel renderer implementations was the most impressive result — the tool found a real structural pattern that `lookup_export` silently missed.

**What's missing or broken**: All three original bugs are now resolved across v2 and v3. The one structural limitation that remains is call-site precision for module-level functions — `fmm_glossary` with dotted notation only narrows to actual callers for class methods. For module-level functions like `scheduleUpdateOnFiber`, `used_by` is file-level (all importers of the containing file), which over-reports the rename blast radius. This is a meaningful gap for JS codebases where most code is not class-based.

**The honest summary**: fmm earns its place in the toolchain for large JS/TS codebases. The source extraction quality alone — finding and reading exactly the 127 lines of `scheduleUpdateOnFiber` from a 5,569-line file without any grep or full-file read — justifies the indexing cost. For oriented code exploration, it removes the token overhead of traditional file-by-file reading entirely.

Three silent failure modes were identified during initial evaluation. All three have been fixed across v2 and v3: `fmm_lookup_export` now warns on name collisions with a glossary redirect; `include_private` now correctly surfaces `#field` private syntax; `fmm_dependency_graph` now resolves cross-package imports bidirectionally, making `shared/ReactFeatureFlags.js` correctly show 90 downstream dependents instead of 1. The fix progression was responsive and targeted — each issue was addressed at the right layer without over-engineering.

The one remaining gap is call-site precision for module-level functions. Renaming `scheduleUpdateOnFiber` still requires manually reviewing which of the 24 file-level importers actually call it, versus importing other symbols from the same module. This is a harder problem for JS/TS (no static dispatch, module-level functions don't have a class receiver to anchor the tree-sitter query to) and is the honest frontier of what static analysis can do here without a full type-aware language server pass.
