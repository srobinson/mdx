---
title: fmm Capability Assessment — TypeScript (NestJS monorepo)
date: 2026-03-06
tags: [fmm, evaluation, ts, typescript, nestjs]
---

# fmm Capability Assessment: TypeScript

**Codebase**: NestJS monorepo (`nestjs/nest`) — 1,667 files, 108,654 LOC. Packages, integration tests, and sample apps. Six sub-trees: `packages/` (820 files, 77k LOC), `integration/` (494 files, 23k LOC), `sample/` (336 files, 7k LOC), `tools/`, `hooks/`, root.
**Method**: All navigation via fmm MCP tools only — no grep, no source file reads for discovery.

---

## Chosen Subjects

| Role | Symbol / Name | Why chosen |
|------|--------------|------------|
| Core class | `NestContainer` (`packages/core/injector/container.ts`) | Highest downstream count in the codebase: 58 direct dependents. The module registry — everything that builds or resolves the DI graph passes through it. |
| Dispatch method | `Injector.loadInstance` (`packages/core/injector/injector.ts` [128, 205]) | The entry point for resolving any DI-managed instance. Every provider, controller, and middleware creation routes through it. 78 LOC vs 1109 in the full file. |
| Collision name | `ContextType` | Defined in two distinct source files: the barrel (`packages/common/index.ts`) and the original interface (`packages/common/interfaces/features/arguments-host.interface.ts`). Classic TS re-export collision — glossary has to track both separately. |
| Common dependency | `@nestjs/common` | Present in imports for every non-trivial source file. Used as the baseline filter in cross-cutting search tasks. |

---

## Tool-by-Tool Evaluation

### `fmm_list_files`
**What it claims**: List all indexed files under a directory prefix with LOC, export count, and downstream dependent count.
**What it actually does**: Delivers exactly that. First call with no arguments returned a clean summary line (`1,667 files · 108,654 LOC · largest: ...`) and sorted output by LOC descending. Pagination via `offset` works correctly — requesting `offset=200` on a 258-file directory returned files 201–210 with an accurate total. `group_by=subdir` collapses results into directory buckets with file count and total LOC per bucket. `filter=source` excludes test files cleanly.

`sort_by="downstream"` is the standout sort mode. It surfaces files by blast radius rather than size — and the results are striking. In `packages/core/`, `runtime.exception.ts` (9 LOC) ranks #6 with 22 downstream dependents. `request-constants.ts` (2 LOC) has 7 downstream. `adapters/index.ts` (1 LOC) has 7. These files are invisible under `sort_by="loc"` but are genuinely high-risk to touch. This sort mode is the right first call before any refactoring pass.

`sort_by="modified"` surfaces recently touched files with date stamps per entry — useful for resuming work or reviewing recent changes.

**Limitations or surprises**: `group_by="subdir"` groups by the first path segment from the repo root, not by the immediate child of the `directory` parameter. When scoped to `directory="packages"`, all 820 files share the same first segment — `packages/` — so they collapse into a single useless bucket. The root-level call works correctly (6 buckets: `packages/`, `integration/`, `sample/`, etc.) because the first segment varies there. The fix: when `directory` is specified, group by the next path segment relative to that prefix — `path[len(directory):]` — so `directory="packages"` yields `packages/core/`, `packages/common/`, `packages/microservices/`, etc.

**Verdict**: Solid and fast; `sort_by="downstream"` is genuinely valuable for pre-refactoring orientation; all known bugs fixed as of 0.1.26.

### `fmm_file_info`
**What it claims**: File summary: exports, imports, LOC.
**What it actually does**: This tool does not exist in the current deployment. The MCP server exposes 8 tools, not 9 — `fmm_file_info` is absent. Its functionality is covered by `fmm_file_outline` (which includes LOC, imports, and dependencies in its header) and `fmm_lookup_export` (which returns the same metadata indexed by symbol name).
**Limitations or surprises**: Either removed, renamed, or the evaluator prompt references an older version. `fmm_file_outline` fills the gap adequately.
**Verdict**: Not present — functionality distributed across `fmm_file_outline` and `fmm_lookup_export`.

### `fmm_file_outline`
**What it claims**: Every export in a file with line ranges and sizes.
**What it actually does**: Delivers a spatial table-of-contents for the file. The baseline case (no `include_private`) returns all public exports with exact `[start, end]` line ranges and sizes. The headline capability is `include_private: true` — an on-demand tree-sitter parse that exposes private and protected members under each class, annotated with `# private`. On `injector.ts` this revealed all 13 private methods (`getInquirerId`, `resolveScopedComponentHost`, `isDebugMode`, `getContextId`, etc.) with their exact ranges — information unavailable from the index alone.

The header includes LOC, external imports, and local dependencies. The class-level summary line (`1024 lines, 29 public methods, 13 private methods, 2 private fields`) is a compact structural fingerprint.
**Limitations or surprises**: None material. The `include_private` flag is the standout feature — it turns a basic outline into a full API inventory including implementation details.
**Verdict**: The most useful orientation tool in the set; `include_private` elevates it significantly beyond a simple ToC.

### `fmm_lookup_export`
**What it claims**: O(1) exact symbol-to-file lookup.
**What it actually does**: Exactly what it claims. `fmm_lookup_export("NestContainer")` returned file path, line range, all sibling exports in the same file, external imports, local dependencies, and LOC in a single round trip. `fmm_lookup_export("GhostOracle")` on a non-existent symbol returned a clean `ERROR: Export 'GhostOracle' not found` with no crash, no hallucination.
**Limitations or surprises**: The metadata returned is richer than advertised — you get imports, dependencies, and LOC alongside the location, making it a viable first-call substitute for the absent `fmm_file_info`. No limitations observed.
**Verdict**: Flawless. One call to find any symbol, with enough metadata to plan the next move.

### `fmm_list_exports`
**What it claims**: Fuzzy export name search across the codebase.
**What it actually does**: Case-insensitive substring match against all export names. `pattern="Service"` returned 235 results. `pattern="Context"` returned 199. `pattern="handle"` returned 128. Scoping via `directory` works — `fmm_list_exports(pattern="Module", directory="packages/core/injector")` correctly limited to 95 results from that subtree. Results include class method entries in `ClassName.method` notation, which enables precise pattern targeting.

Single-character query `pattern="s"` returned 2,348 total matches. Results are sorted alphabetically by name — `s` matches anything containing the letter and sorting is lexicographic, not by relevance to the pattern.
**Limitations or surprises**: Alphabetical sort regardless of match quality. For short patterns (`"re"` → 965 results, `"s"` → 2,348) this produces unmanageably large unranked dumps where the most relevant results are invisible without pagination. For longer patterns (`"Controller"`) the set is naturally small enough that alphabetical is fine.

Regex patterns are supported — added in 0.1.26. Patterns containing metacharacters (`^`, `$`, `[`, `(`, `\`, `.`, `*`, `+`, `?`, `{`) are compiled as regex; plain strings retain case-insensitive substring behaviour.

```
fmm_list_exports(pattern="^re")        → 3 results: repl, requestProvider, rethrow
fmm_list_exports(pattern="re")         → 965 results (substring, all names containing "re")
fmm_list_exports(pattern="Controller$") → 62 results: class-level exports ending in Controller
```

`^re` vs `"re"` is the definitive demonstration: 3 results vs 965. The caller encodes intent in the pattern — no ranking heuristic needed. `Controller$` correctly excludes method entries like `AdvancedGrpcController.stream` while including `DependenciesScanner.insertController` (which genuinely ends with "Controller").

**Verdict**: Excellent — regex support cleanly solves the short-pattern noise problem; plain string fallback preserves existing behaviour.

### `fmm_read_symbol`
**What it claims**: Source extraction for a named export, exact lines.
**What it actually does**: Pulls exact source from the sidecar without reading the full file. `fmm_read_symbol("Injector.loadInstance")` returned lines 128–205 (78 LOC) from a 1,109 LOC file — a 93% reduction in tokens loaded. The dotted `ClassName.method` notation works for both public and private methods (private methods discovered via `fmm_file_outline(include_private=true)` are accessible the same way).

When a symbol exceeds the 10KB cap, `truncate=true` (the default) does not cut off mid-source — it degrades gracefully into a structured method index: every public method with exact line ranges and LOC, plus a prompt to use dotted notation or `truncate: false`. On `Injector` (1,024 lines), the response was a clean per-method table. Symbols under the 10KB threshold return complete source under either setting; the flag has no effect there.

`line_numbers: true` prepends absolute line numbers — anchored to the file, not relative to the extracted block. `Injector.loadInstance` starts at line 128; with `line_numbers: true`, every line carries its actual file position (128, 129, ... 205). When working across `fmm_file_outline` output and source simultaneously, this makes cross-referencing unambiguous. For multi-step analysis workflows it is the glue that prevents off-by-one errors when switching between tools.
**Limitations or surprises**: None material. The graceful truncation fallback means the default is always safe — no surprise wall-of-text on large classes.
**Verdict**: The primary surgical read tool — dotted method notation, 93% token reduction, graceful structured fallback on large classes, and absolute line number anchoring make it the right default for any source inspection.

### `fmm_dependency_graph`
**What it claims**: Upstream local deps and downstream dependents with blast radius.
**What it actually does**: Returns two lists — `local_deps` (what this file imports from the local codebase) and `downstream` (what depends on it). Depth defaults to 1 (direct only). `depth=2` adds transitive entries annotated with their depth level. `depth=-1` for full transitive closure is available. Circular dependencies are flagged explicitly with a `# circular` annotation inline — immediately visible without reading any source.

On `container.ts`: 15 upstream local deps, 58 downstream at depth=1. On `injector.ts` at `depth=2`: 27 upstream, 48 downstream entries across both depths — several circulars flagged. Circularity detection is reliable and explicit.
**Limitations or surprises**: The `downstream` list mixes source files and test files with no filtering option — unlike `fmm_list_files` which has a `filter` parameter. For blast-radius analysis before a production change, you have to mentally filter test files yourself.
**Verdict**: Reliable and precise for direct blast radius; circular detection is a genuine strength; a `filter` option on downstream would improve production-change analysis.

### `fmm_search`
**What it claims**: Multi-criteria search with exports, imports, LOC, and `depends_on` filters.
**What it actually does**: Multiple modes. `imports` filter finds all files importing a given package — `imports="@nestjs/common", min_loc=500` returned the 24 largest files that import it. Three-filter AND works correctly: `imports="rxjs", min_loc=300, export="handle"` returns empty (correct — no matching files); `imports="rxjs", min_loc=300, export="Server"` returns `ServerGrpc` and `ServerKafka` precisely. Previously the `export` filter was silently ignored when combined with others; that bug is fixed.

`depends_on` with a file path computes the full transitive closure of dependents. `depends_on="packages/core/injector/container.ts"` returned 254 results — essentially the entire non-trivial codebase. Accurate but not actionable at this scale.
**Limitations or surprises**: `depends_on` on foundational files produces results so broad they are useless for rename decisions. `fmm_dependency_graph(depth=1)` is the right tool for direct dependents. The distinction between transitive (`fmm_search depends_on`) and direct (`fmm_dependency_graph`) is easy to miss.
**Verdict**: Powerful for filtered multi-criteria discovery; AND semantics correct; `depends_on` on central files use `fmm_dependency_graph` instead.

### `fmm_glossary`
**What it claims**: Symbol-level impact analysis — all definitions and callers.
**What it actually does**: Two distinct behaviours based on pattern format. Bare name (`"loadInstance"`) → file-level `used_by`, listing all files that import the containing file. Dotted name (`"Injector.loadInstance"`) → call-site precision, with a second tree-sitter pass filtering to files that actually invoke that method.

On `Injector.loadInstance` with `mode="source"`:
```
(no external source callers)
# 15 files import injector.ts — none call loadInstance directly
# 8 test callers found (rerun with mode: tests)
```
When no source callers are found, the tool proactively hints that test callers exist and tells you exactly how to find them. One call gives a complete picture. `mode="tests"` returned 2 test files; the hint reports 8 test callers — callers are call sites, not files. `injector.spec.ts` calls `loadInstance` multiple times. Both counts are correct and serve different purposes.

On `ContextType` with `mode="all"`: correctly returned 2 distinct definitions (barrel and interface file) with separate, disjoint `used_by` lists. Rename blast radius correctly separated: 12 files for the barrel re-export, 5 files for the original interface.
**Limitations or surprises**: The `limit` cap (default 10, hard cap 50) is a real constraint for broad patterns. The distinction between bare-name (file-level) and dotted-name (call-site) behaviour is not obvious from the tool description alone — it requires testing to discover.
**Verdict**: Best-in-class — call-site precision via dotted notation, cross-mode hints, and correct multi-definition disambiguation make this the defining capability of the toolset.

---

## Task Results

### Task 1: Directory Exploration

`fmm_list_files()` with no args: 1,667 files, 108,654 LOC, 6 top-level buckets via `group_by=subdir`.

| Directory | Files | LOC | Largest file |
|-----------|-------|-----|-------------|
| `packages/` | 820 | 77,197 | `kafka.interface.ts` (1,325) |
| `integration/` | 494 | 23,522 | `custom-versioning-fastify.spec.ts` (967) |
| `sample/` | 336 | 7,215 | — |
| `tools/` | 15 | 697 | — |

Within `packages/core/` (258 files, 29,099 LOC): top 5 by LOC are `injector.ts` (1,109), `instance-wrapper.spec.ts` (1,023), `injector.spec.ts` (882), `scanner.spec.ts` (756), `scanner.ts` (755). Test files routinely exceed their implementation counterparts in LOC throughout the codebase.

`group_by=subdir` on `packages/` correctly returns 9 sub-package buckets: `packages/core/` (258 files, 29k LOC), `packages/microservices/` (195 files, 24k LOC), `packages/common/` (237 files, 16k LOC), etc. — fixed in 0.1.26.

### Task 2: Symbol Lookup and Source Read

```
fmm_lookup_export("NestContainer")
→ file: packages/core/injector/container.ts, lines: [31, 367]
  15 local deps, 58 downstream, loc: 367
```

`fmm_read_symbol("NestContainer")` returned the full 337-line class — no `truncate: false` needed, as 337 lines sits under the 10KB threshold. Public API: `addModule`, `replaceModule`, `addDynamicMetadata`, `addProvider`, `addController`, `bindGlobalScope`, `getDynamicMetadataByToken`, `registerRequestProvider`, and 15+ others. Private fields include `globalModules`, `modules`, `dynamicModulesMetadata`, `internalProvidersStorage`, `_serializedGraph`.

`fmm_read_symbol("Injector.loadInstance")` returned exactly lines 128–205 (78 LOC) from a 1,109 LOC file. Token reduction: 93%. The method body shows the full lifecycle: contextId resolution, isPending/circular check, settlement signal allocation, constructor param resolution, property injection, and error cleanup.

### Task 3: Dependency Analysis

`fmm_dependency_graph("packages/core/injector/container.ts")`:
- **15 upstream local deps**: `application-config`, `discoverable-meta-host-collection`, error exceptions, `compiler`, `instance-wrapper`, `internal-core-module`, `module`, `modules-container`, two opaque key factories, `serialized-graph`, `request-constants`
- **58 downstream dependents**: guards, helpers, injector internals, middleware, routers, nest-application, scanners, and cross-package test files from `packages/microservices` and `packages/websockets`
- **1 circular**: `packages/core/injector/module.ts` flagged with `# circular`

`fmm_file_outline("packages/core/injector/container.ts", include_private=true)`:
- `NestContainer`: 337 lines, 31 public methods, 2 private methods, 7 private fields
- Private methods: `setModule` [163, 185] and `shouldInitOnPreview` [364, 366]

The two tools are complementary. `fmm_dependency_graph` answers "what is connected to this file and at what scope?" `fmm_file_outline` answers "what is inside this file and where exactly?" Together they cover the full pre-change due-diligence surface.

### Task 4: Impact Analysis

Target: rename `Injector.loadInstance`.

```
fmm_glossary("Injector.loadInstance", mode="all")
→ used_by: [injector.spec.ts, nested-transient-isolation.spec.ts]

fmm_glossary("Injector.loadInstance", mode="source")
→ (no external source callers)
  # 15 files import injector.ts — none call loadInstance directly
  # 8 test callers found (rerun with mode: tests)

fmm_glossary("Injector.loadInstance", mode="tests")
→ used_by: [injector.spec.ts, nested-transient-isolation.spec.ts]
```

15 files import `injector.ts` — the naive blast radius. The dotted-notation pass narrows it to 0 source callers and 2 test files. `loadInstance` is invoked only internally within `Injector` itself (`loadController`, `loadProvider`, `loadInjectable`, `loadMiddleware` — all within the same file). A rename requires updating 2 test files and the internal call sites, not 15 files.

`mode="source"` proactively hints that 8 test callers exist. Note the distinction: 2 test **files** vs 8 test **callers** — `injector.spec.ts` calls `loadInstance` multiple times. The hint count is call-site precision; the `used_by` list is file-level. Both are correct.

### Task 5: Name Collision Check

```
fmm_glossary("ContextType", mode="all")
→ src: packages/common/index.ts [13-65]
    used_by: 12 files (decorators, pipes, test files, core)

  src: packages/common/interfaces/features/arguments-host.interface.ts [1-1]
    used_by: 5 files (exception filters, execution context, interfaces index)
```

Classic TypeScript barrel collision. Both definitions indexed, `used_by` lists correctly disjoint. Renaming the interface definition touches 5 files; renaming the barrel re-export touches 12. fmm correctly separates the two blast radii.

### Task 6: Cross-Cutting Search

**imports + min_loc:**
```
fmm_search(imports="@nestjs/common", min_loc=500)
→ 24+ files over 500 LOC importing @nestjs/common
```
Mix of implementation and test files. Filter works; no source/test separation.

**depends_on:**
```
fmm_search(depends_on="packages/core/injector/container.ts")
→ 254 results (full transitive closure)
```
Accurate but not actionable. `fmm_dependency_graph(depth=1)` at 58 entries is the right tool here.

**Three-filter AND:**
```
fmm_search(imports="rxjs", min_loc=300, export="handle")  → (no results) ✓
fmm_search(imports="rxjs", min_loc=300, export="Server")  → ServerGrpc, ServerKafka ✓
```
AND semantics correct. `handle` returns empty because no matching files exist — not a false negative. `Server` returns exactly the two files matching all three criteria.

### Task 7: Coverage Check

```
fmm_glossary("Injector.loadInstance", mode="tests")
→ packages/core/test/injector/injector.spec.ts (882 LOC)
   packages/core/test/injector/nested-transient-isolation.spec.ts (272 LOC)
```

Implementation: 78 LOC. Test coverage: 882 + 272 = 1,154 LOC. Ratio ~15:1. Coverage is concentrated — `injector.spec.ts` is the primary suite, `nested-transient-isolation.spec.ts` targets the transient scope circular isolation edge case.

---

## Freeform Experiments

### Experiment 1: Non-existent symbol lookup

```
fmm_lookup_export("GhostOracle")
→ ERROR: Export 'GhostOracle' not found
```

Clean failure, no hallucination. Agents that pipeline `fmm_lookup_export` → `fmm_read_symbol` must handle this error case explicitly.

### Experiment 2: Single-character pattern breadth test

```
fmm_list_exports(pattern="s", limit=5)
→ 2,348 total matches
   First 5: Abstract, AckGateway.onPush, AclOperationTypes, AclPermissionTypes, AclResource
```

2,348 results for `"s"`. First results start with 'A', not 'S' — substring matching with lexicographic sort. Single-character patterns are useful for counting vocabulary size, not for discovery. The regex proposal (`^s`) would fix the relevance problem without breaking longer patterns.

### Experiment 3: Depth-2 dependency graph on the heaviest file

```
fmm_dependency_graph("packages/core/injector/injector.ts", depth=2)
→ 27 upstream local deps at depth 1-2
   48 downstream entries including multiple # circular annotations
```

Depth annotation per entry works correctly. Circulars flagged at every depth level where they appear. The circular subgraph centred on the exceptions module is visible without reading any source.

### Experiment 4: Private method inventory via `include_private`

```
fmm_file_outline("packages/core/injector/injector.ts", include_private=true)
→ Injector: 1024 lines, 29 public methods, 13 private methods, 2 private fields
  Private: getInquirerId [964, 968], getEffectiveInquirer [977, 989],
  resolveScopedComponentHost [991, 1005], isInquirerRequest [1007, 1012],
  isInquirer [1014, 1019], addDependencyMetadata [1021, 1031],
  getTokenName [1033, 1035], printResolvingDependenciesLog [1037, 1056],
  printLookingForProviderLog [1058, 1072], printFoundInModuleLog [1074, 1088],
  isDebugMode [1090, 1092], getContextId [1094, 1104], getNowTimestamp [1106, 1108]
```

Without `include_private`, a 1,109 LOC class appears to have only 29 public methods. The private inventory reveals 13 more. All are accessible via dotted notation: `fmm_read_symbol("Injector.getContextId")` works without reading the full file.

### Experiment 5: Multi-definition glossary disambiguation

```
fmm_glossary("ContextType", mode="all")
→ Two distinct src entries, separate used_by lists (disjoint)
```

Barrel re-export (`index.ts`, 12 importers) and original interface definition (`arguments-host.interface.ts`, 5 importers) tracked separately. No conflation. Importers correctly associated with the specific file they import from.

### Experiment 6: `sort_by="modified"` — recent activity surface

```
fmm_list_files(directory="packages", sort_by="modified", limit=20)
→ packages/common/test/decorators/render.decorator.spec.ts  loc: 17  modified: 2026-03-06
  packages/microservices/events/index.ts                    loc: 6   modified: 2026-03-06
  packages/core/hooks/on-app-shutdown.hook.ts               loc: 74  modified: 2026-03-06
  ...all 20 results dated 2026-03-06
```

Works as advertised. Date granularity is day-level — files modified earlier the same day are not differentiated by time. Fine for resuming work; too coarse for forensic diff archaeology on a busy repo.

**`directory: "."` — fixed in 0.1.26**

```
fmm_list_files(directory=".", sort_by="modified")
→ 1,667 files · 108,654 LOC  ← correctly resolves to repo root
```

Previously returned `0 files · 0 LOC` — a path normalisation bug where `"."` was not resolved to the index root. Fixed: `"."` now correctly behaves identically to omitting `directory`.

### Experiment 7: `sort_by="downstream"` — blast-radius orientation

```
fmm_list_files(directory="packages/core/", sort_by="downstream")
→ container.ts          367 LOC  ↓ 58 downstream   ← #1
  instance-wrapper.ts   544 LOC  ↓ 56 downstream
  module.ts             680 LOC  ↓ 43 downstream
  application-config.ts 150 LOC  ↓ 37 downstream
  injector.ts          1109 LOC  ↓ 23 downstream
  runtime.exception.ts    9 LOC  ↓ 22 downstream   ← #6
  ...
  request-constants.ts    2 LOC  ↓  7 downstream
  adapters/index.ts       1 LOC  ↓  7 downstream
```

`sort_by="loc"` would bury `runtime.exception.ts` (9 LOC) at the bottom of 258 files. `sort_by="downstream"` puts it at #6. A 9-line file with 22 direct dependents is a high-risk touch point that size-based sorting makes invisible.

**Documentation gap**: Neither the CLI help nor the SKILL.md capture this use case. The CLI shows only `--sort-by loc`. The SKILL.md says *"Always pass `sort_by: 'loc'`"* — which actively steers agents away from the more useful sort for pre-refactoring orientation. Both need a `sort_by: "downstream"` example in the refactoring workflow.

### Experiment 8: Graceful truncation on large class

```
fmm_read_symbol("Injector", truncate=true)  ← default
→ # Injector would exceed the 10KB response cap (1024 lines, 29 public methods)
  methods:
    constructor                     [92, 107]   # 16 lines
    loadPrototype                   [109, 126]  # 18 lines
    loadInstance                    [128, 205]  # 78 lines
    ...
  # Use dotted notation: fmm_read_symbol("Injector.constructor")
  # Use truncate: false for full source
```

Instead of cutting off mid-source, the default gracefully degrades into a structured method index — every public method with exact line ranges and LOC. The fallback is itself a useful navigation artefact. `truncate: false` is the explicit override when full source is genuinely needed.

### Experiment 9: Pagination verification

```
fmm_list_files(directory="packages/core", sort_by="loc", offset=200, limit=10)
→ showing: 201-210 of 258
   Files range from 12 LOC (silent-logger.ts) to 9 LOC (runtime.exception.ts)
```

Pagination is accurate — total count stable across pages, offset arithmetic correct. The tail of the distribution is single-digit files: tiny exception classes and constants. Stark contrast with the 1,109 LOC injector at the head.

---

## Summary Scorecard

| Tool | Verdict |
|------|---------|
| `fmm_list_files` | Solid; `sort_by="downstream"` is the standout mode; `group_by="subdir"` and `"."` bugs fixed in 0.1.26 |
| `fmm_file_info` | Not present in current deployment |
| `fmm_file_outline` | Exceptional — `include_private` reveals full method inventory with exact ranges |
| `fmm_lookup_export` | Flawless — O(1), rich metadata, clean error on miss |
| `fmm_list_exports` | Excellent — regex support added in 0.1.26; `^re` returns 3 results vs 965 for `"re"` |
| `fmm_read_symbol` | Excellent — dotted notation, 93% token reduction, graceful structured truncation fallback, absolute line numbers |
| `fmm_dependency_graph` | Reliable — circular detection explicit and accurate; no source/test filter on downstream |
| `fmm_search` | AND semantics correct; `depends_on` on central files too broad — use `fmm_dependency_graph` instead |
| `fmm_glossary` | Best-in-class — call-site precision, cross-mode hints, correct multi-definition disambiguation |

---

## Overall Assessment

**Production-ready for TypeScript navigation?** Yes, with known rough edges.

**What's genuinely good**: `fmm_glossary` with dotted notation is the defining capability. Knowing that `Injector.loadInstance` has 0 external source callers despite 15 files importing `injector.ts` is the difference between a correct rename and a risky one. The cross-mode hint (`# 8 test callers found — rerun with mode: tests`) means one call gives a complete picture. `fmm_file_outline(include_private=true)` surfaces the full method inventory of a class — public and private — with exact line ranges, enabling surgical reads without touching the full file. `fmm_read_symbol` with graceful truncation fallback means the default is always safe: large classes get a structured method index rather than a wall of text. `sort_by="downstream"` on `fmm_list_files` is the most actionable orientation mode before a refactoring pass — small files with outsized blast radius are invisible to LOC sort.

**What's missing or broken**: `fmm_file_info` is absent from the deployment — covered in practice by `fmm_file_outline` and `fmm_lookup_export`, but the documentation discrepancy is a liability. `sort_by="downstream"` is undocumented in both the CLI help and SKILL.md, with the SKILL.md actively recommending against it. The `group_by="subdir"` relative-path bug, `directory: "."` path normalisation bug, and `fmm_list_exports` short-pattern noise were all fixed in 0.1.26.

**The honest summary**: fmm is production-viable for TypeScript navigation. The index-backed tools are fast and accurate. The structural analysis tools give reliable spatial context. `fmm_glossary` with call-site precision is genuinely exceptional — no grep-based workflow can provide this level of rename safety in a single call. The bugs are real but all narrow in scope: two path/grouping issues, one missing tool, one documentation gap. None are blockers. Fix `"."` normalisation and the `group_by` relative-path bug and the tool is clean.
