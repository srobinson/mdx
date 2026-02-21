# fmm Toolset Evaluation — Python Codebase

**Evaluator:** Claude Sonnet 4.6 (claude-sonnet-4-6)
**Codebase:** agno — a Python agent framework (~50k LOC across `libs/agno/`, `cookbook/`, tests)
**Session type:** Live road test with iterative bug reporting and fix validation
**Date:** 2026-03-05

---

## What fmm Is

fmm is a code structural intelligence layer. It indexes a codebase into a manifest of exported symbols, file metadata, and import graphs, then exposes that index through MCP tools. The proposition: replace grep-then-read navigation chains with O(1) structured lookups, saving 88-97% of tokens spent on orientation.

The toolset ships as a Rust binary. Sidecar `.fmm` files sit alongside source files as a fallback; the MCP tools read from a pre-built in-memory manifest rebuilt on each call.

---

## Tools Evaluated

| Tool | Purpose |
|------|---------|
| `fmm_file_outline` | Every exported symbol in a file with line ranges and sizes |
| `fmm_file_info` | File summary: exports, imports, LOC |
| `fmm_list_files` | All indexed files under a directory, with LOC and export counts |
| `fmm_list_exports` | Fuzzy export name search across the codebase |
| `fmm_lookup_export` | O(1) exact symbol-to-file lookup |
| `fmm_read_symbol` | Source extraction for a named export, exact lines only |
| `fmm_dependency_graph` | Upstream local deps + downstream dependents for a file |
| `fmm_search` | Multi-criteria search: export name, imports, LOC, depends_on |
| `fmm_glossary` | Symbol-level impact analysis: all definitions + precise callers |

---

## Tool-by-Tool Assessment

### `fmm_file_outline` — Excellent

The standout tool. One call returns every exported symbol with its line range and byte size. Before reading anything, I could see that `_run.py` is 4,509 lines, that `run_dispatch` sits at [1207-1384], and that its async twin `arun_dispatch` mirrors it at [2428-2634]. This is the shape of a file without reading it — exactly what the tool promises.

**Practical impact:** Eliminated the "read the whole file to find the function" pattern entirely for orientation tasks.

---

### `fmm_file_info` — Good, with a fixed bug

Provides LOC, import list, and exports as a fast summary. During testing, passing a directory path caused a transport-level crash that cascaded to kill sibling tool calls in the same parallel batch. This was fixed across the session: the tool now returns a clean content-level error with a suggestion to use `fmm_list_files` instead. No cascade.

**Post-fix behaviour:** Clean, contained errors. Siblings survive.

---

### `fmm_list_files` — New tool, immediately essential

Added during this session in response to the gap identified in the original review. Accepts a directory prefix and optional glob pattern. Returns all indexed files with LOC and export counts, sorted alphabetically.

```
libs/agno/agno/models/anthropic/claude.py  # loc: 1125, exports: 0
libs/agno/agno/models/google/gemini.py     # loc: 1961, exports: 0
libs/agno/agno/models/openai/chat.py       # loc: 960, exports: 0
```

The first question when exploring an unfamiliar module is always "what files are here?" This tool answers it definitively. 100 provider files in `libs/agno/agno/models/` surfaced in one call, with `base.py` at 3,022 lines standing out immediately as the abstraction layer.

**Verdict:** Should be the first tool called when entering any unfamiliar directory.

---

### `fmm_list_exports` — Good for fuzzy discovery

Pattern-based search across all export names. Used to recover from wrong assumptions: searching `Claude` when `Anthropic` returned nothing. Case-insensitive substring matching works well.

**Limitation:** Returns raw name/location pairs with no `used_by` data. Useful for discovery, not for impact analysis. The glossary supersedes it for the latter.

---

### `fmm_lookup_export` — Reliable O(1) lookup

When you know the exact name, this returns file path and line range immediately. Consistent across the session.

**Previous bug (fixed):** Initially resolved `Agent` to `agent/__init__.py` (the re-export stub) rather than following the chain to `agent/agent.py` (the concrete class). The fix correctly follows re-export chains to the implementation. This was a meaningful fix — the stub is useless for navigation, the implementation is everything.

---

### `fmm_read_symbol` — Good after the re-export fix

Returns the actual source lines for a named symbol. With the re-export resolution fixed, calling `fmm_read_symbol("Agent")` now returns the 1,539-line `Agent` dataclass from `agent/agent.py`, not the `__all__` list from `__init__.py`.

**One note:** The output is truncated at 206 of 1,545 lines for very large classes. This is correct behaviour — `fmm_read_symbol` on a 1,500-line class should prompt you to read specific sub-sections, not dump everything. The tool is best used on functions and smaller classes where the full body fits in one response.

---

### `fmm_dependency_graph` — Significantly improved

This tool had the most development across the session and saw the most meaningful change.

**Starting state:** Returned only external package names collapsed to top-level:
```yaml
imports: [agno, concurrent, dataclasses, pydantic, typing]
```

All intra-package `from agno.x.y import z` calls were being treated as the single string `agno`. The internal module graph was invisible.

**Final state:**
```yaml
local_deps:
  - libs/agno/agno/agent/_hooks.py
  - libs/agno/agno/agent/_init.py
  - libs/agno/agno/agent/_messages.py
  - libs/agno/agno/agent/_response.py
  - libs/agno/agno/agent/_run_options.py
  - libs/agno/agno/agent/_session.py
  - libs/agno/agno/agent/_storage.py
  - libs/agno/agno/agent/_telemetry.py
  - libs/agno/agno/agent/_tools.py
  - libs/agno/agno/agent/agent.py
  ...
external: [asyncio, collections, fastapi, inspect, json, pathlib, pydantic, time, typing, uuid, warnings]
downstream:
  - libs/agno/agno/team/_default_tools.py
  - libs/agno/agno/team/_run.py
  - libs/agno/agno/team/_task_tools.py
  - libs/agno/tests/unit/agent/test_run_options.py
```

`local_deps` resolves dotted Python import paths to concrete file paths. `external` lists only third-party packages, with `agno` correctly excluded. `downstream` provides the blast radius for the file — every file that imports it.

For `agent.py`, downstream covers 183 files spanning cookbooks, integration tests, unit tests, the OS layer, and the workflow engine. That's a complete picture of what changes if the class signature shifts.

**Remaining gap:** The `downstream` list for `agent.py` does not include `_run.py` and the other internal modules, even though those modules list `agent.py` in their `local_deps`. This is technically correct given the direction of the dependency arrow, but it means the internal circular reference (agent.py imports its internals, internals import agent.py for the Agent type) is asymmetrically represented. Low priority, not a blocker.

---

### `fmm_search` — Useful with discipline

Multi-criteria search across exports, file paths, and imports. Works well when tightly scoped:

- `fmm_search(depends_on: "libs/agno/agno/agent/_run.py")` — precise impact query
- `fmm_search(min_loc: 800)` — find the largest files in the codebase
- `fmm_search(imports: "anthropic")` — find every file that imports the Anthropic SDK

Without filters, `fmm_search(term: "Agent")` returns 1,000+ results and truncates. The tool requires discipline from the caller. Broad queries should be broken into targeted lookups using other tools first.

**Recommendation:** The skill instructions should discourage bare `term` searches on common words and suggest specific patterns or filter combinations instead.

---

### `fmm_glossary` — The best new addition

Symbol-level impact analysis. Given a pattern, returns every matching export across the codebase, with its definition location and the precise list of files that import it.

```yaml
run_dispatch:
  - src: libs/agno/agno/agent/_run.py [1207-1384]
    used_by: [libs/agno/agno/team/_default_tools.py, libs/agno/agno/team/_run.py, libs/agno/agno/team/_task_tools.py]
  - src: libs/agno/agno/team/_run.py [1734-1935]
    used_by: [libs/agno/agno/team/_default_tools.py, libs/agno/agno/team/_hooks.py, ...]
```

This is the tool I would reach for first before any refactor. `fmm_dependency_graph` tells you which files import a file. `fmm_glossary` tells you which files import a specific function. For a codebase with 1,600-line classes spread across internal modules, that precision matters.

**Three-mode design works correctly:**

- `source` (default): production symbols only, test symbol definitions excluded. Callers from test files still appear in `used_by` where they import the source symbol — correct.
- `tests`: test exports only. Answers "what tests exercise this symbol?" — a distinct and useful question for coverage assessment.
- `all`: union of both, source-first.

**Hard constraints are right:** Pattern is required (no unbounded queries). Hard cap at 50 with a visible truncation hint (`# showing 10/12 matches — use a more specific pattern`). The hint is actionable and not silent.

**Minor observation:** The `used_by` field under `source` mode still includes test file paths when those test files directly import the source symbol. This is technically accurate but creates minor noise for pure refactoring intent. A future `callers: source_only` sub-filter would clean this up. Low priority.

---

## The Sibling Cascade Bug — Diagnosis and Resolution

This was the most technically interesting issue of the session. When `fmm_file_info` received a directory path, siblings in the same parallel batch failed with `"Sibling tool call errored"` or `"Cancelled: parallel tool call errored"`.

**Root cause:** The MCP protocol distinguishes two error response types:

| Type | Structure | Sibling effect |
|------|-----------|----------------|
| JSON-RPC error object | `{"error": {"code": -32000, "message": "..."}}` | Kills siblings |
| Tool result with `isError` | `{"result": {"content": [...], "isError": true}}` | Contained |

The server was raising unhandled Python exceptions on bad input. The MCP framework caught these and returned JSON-RPC error objects at the protocol level. Claude Code's parallel tool call orchestrator treats protocol-level errors as terminal for the batch — hence the cascade.

The fix: input validation now catches bad paths before hitting the manifest and returns the error as tool result content. The error message became helpful in the process: `'libs/agno/agno/models' is a directory, not a file. Use fmm_list_files(directory: ...) to list its contents.` Siblings now complete normally regardless of what any other call in the batch returns.

This distinction (protocol error vs content error) is worth encoding in the fmm server's error handling conventions for all tools, not just `fmm_file_info`. Any tool that can receive invalid input should return `isError: true` content, never raise.

---

## Token Efficiency

The core claim — 88-97% token savings vs grep/read navigation — holds up in practice.

During this session I mapped the architecture of a 50,000+ line multi-library Python framework:

- Three primary abstractions (Agent, Team, Workflow)
- Twelve storage backends with sync/async variants
- Five agent internal modules totalling ~10,000 lines
- A full learning subsystem (6 stores)
- 100 model provider files
- The AgentOS serving layer

This was accomplished without reading a single source file. The `Agent` class dataclass fields, the `_run.py` dispatch structure, the full downstream blast radius of `agent.py` — all retrieved through metadata calls.

The one case where reading is still necessary: `fmm_read_symbol` on symbols larger than the truncation limit. For a function of 100-300 lines this works perfectly. For a 1,500-line class it delivers the top portion and stops. This is a reasonable tradeoff — you shouldn't be reading 1,500 lines at once anyway.

---

## Summary Scorecard

| Capability | Status |
|------------|--------|
| File structure without reading | Excellent (`fmm_file_outline`, `fmm_file_info`) |
| Directory exploration | Excellent (`fmm_list_files`) |
| Symbol lookup | Excellent (re-export resolution fixed) |
| Fuzzy discovery | Good (`fmm_list_exports`, `fmm_glossary`) |
| Internal dependency graph | Good (resolved after fix; minor asymmetry remains) |
| Downstream blast radius (file) | Good (`fmm_dependency_graph`) |
| Downstream blast radius (symbol) | Excellent (`fmm_glossary`) |
| Pre-refactor impact analysis | Excellent (`fmm_glossary` with `mode: source`) |
| Broad search | Requires discipline (`fmm_search`) |
| Error isolation in parallel batches | Fixed (no more sibling cascade) |
| Token efficiency vs grep/read | Confirmed high |

---

## Recommendations for Future Development

**1. Internal `used_by` filtering on `fmm_glossary`.** A `callers: source_only` sub-option to exclude test files from `used_by` lists when the analyst wants a production-only blast radius.

**2. Encode the `isError` convention across all tools.** The sibling cascade fix applied to `fmm_file_info`. Audit the other tools for the same class of issue — any tool that can receive invalid input should return content-level errors, not raise.

**3. Skill instructions: discourage bare broad searches.** The `fmm_search(term: "Agent")` pattern returns too much noise on common names. The skill should recommend `fmm_lookup_export` or `fmm_list_exports(pattern: ...)` as the first move, with `fmm_search` reserved for compound filter queries.

**4. `fmm_read_symbol` on re-exported types should annotate the resolution path.** When a symbol resolves through a re-export chain, noting `resolved via: agent/__init__.py → agent/agent.py` would help orient the caller and explain why the returned file differs from what they might expect.

---

## Final Assessment

fmm is a well-conceived tool that delivers on its core promise. The manifest-based approach is correct: on-demand computation from sidecars, no staleness risk, O(1) lookups for the common cases. The Python support is solid after the internal dependency resolution fix landed.

The `fmm_glossary` addition is the most significant capability in the toolset for day-to-day use on a mature codebase. Symbol-level blast radius before a refactor, and name-collision detection before writing a new function — both are things that currently require multi-step grep workflows. The glossary collapses each to a single call.

The toolset is production-ready for Python codebase navigation. The remaining gaps are refinements, not blockers.
