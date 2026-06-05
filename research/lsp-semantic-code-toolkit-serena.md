---
title: "Serena: LSP-Backed Semantic Code Toolkit (MCP) — Architecture & fmm Comparison"
type: research
tags: [mcp, lsp, code-intelligence, coding-agent, python, serena, fmm, symbol-tools]
summary: "Serena is an MCP server that gives coding agents IDE-grade semantic tools (find/edit symbols, references, refactors) by driving 40+ language servers through a unified LSP abstraction; contrasts sharply with fmm's persistent-index approach."
status: active
source: github-researcher
confidence: high
created: 2026-07-21
updated: 2026-07-21
---

# Serena (oraios/serena)

Repo: https://github.com/oraios/serena · MIT · Python 3.11–3.14 · ~26.6k stars, 1.77k forks (created 2025-03-23, actively pushed).
Package: `serena-agent` v1.6.1.dev0. Vendor: Oraios AI. ~59k LOC of Python under `src/`.

## Executive Summary

Serena is an MCP server that gives any MCP-capable coding agent (Claude Code, Codex, Cursor, JetBrains, etc.) "IDE for your agent" capabilities: symbol-level code retrieval, reference lookup, and structure-aware editing/refactoring. It does this by driving real **Language Server Protocol (LSP)** servers — 40+ languages, one adapter per language — through a single unified abstraction layer (`solidlsp`). The agent operates on **symbols and name-paths** (e.g. `MyClass/my_method`) rather than line numbers or grep, so cross-file renames and reference-aware edits collapse into one atomic call.

The most important structural insight for fmm: **Serena is a live, LSP-delegating façade, not an index.** It builds no persistent global symbol index. Instead it lazily calls `textDocument/documentSymbol` per file, caches the result keyed by file-content hash (pickle cache on disk), and delegates all cross-file semantics (references, definitions, implementations) to the language server at query time. This is the polar architectural opposite of fmm's precomputed Rust index — and the trade-offs between the two approaches are the key takeaway of this writeup.

## Architecture

Three layers, cleanly separated:

```
MCP client (LLM agent)
      │  MCP (stdio or HTTP/SSE)
┌─────▼───────────────────────────────────────┐
│ src/serena  — agent + tool surface + MCP     │  the "product"
│   agent.py, mcp.py, tools/*, config/*        │
├──────────────────────────────────────────────┤
│ src/solidlsp — unified LSP abstraction       │  reusable LSP client lib
│   ls.py (SolidLanguageServer ABC),           │
│   language_servers/*.py (one per language)   │
├──────────────────────────────────────────────┤
│ src/interprompt — multilingual Jinja prompt  │  prompt templating
│   factory (system prompts, tool descriptions)│
└──────────────────────────────────────────────┘
```

### Layer 1: `solidlsp` — the LSP abstraction (the reusable core)

- `SolidLanguageServer` (`src/solidlsp/ls.py`, ~3000 LOC) is an abstract base wrapping the full LSP lifecycle: process launch, `initialize` handshake, document open/close, request/response, diagnostics subscription, shutdown. `lsp_protocol_handler/server.py` is the JSON-RPC transport over the server's stdio.
- **One subclass per language server** in `language_servers/` (~90 files): `rust_analyzer.py`, `pyright_server.py`, `gopls.py`, `eclipse_jdtls.py`, `typescript_language_server.py`, etc. Each subclass supplies: how to locate/auto-install the binary (a `DependencyProvider` nested class), the launch command, language-specific `initialize` params, and capability overrides (e.g. `supports_implementation_request()`).
- **Auto-provisioning of language servers** is a standout: e.g. `RustAnalyzer.DependencyProvider` tries `rustup which rust-analyzer`, verifies the binary is functional (`--version`), and auto-installs via rustup if missing. `dependency_provider.py` centralizes download/unzip/uvx patterns. This is why Serena "just works" across 40+ languages with no manual toolchain setup — a large, underrated share of the engineering.
- **The `Language` enum** (`ls_config.py`) is the registry: each variant maps to an LS class via `get_ls_class()` and a source-filename matcher via `get_source_fn_matcher()`. Multiple servers per language are offered as distinct variants (`PYTHON` → pyright, `PYTHON_JEDI`, `PYTHON_TY`, `PYTHON_PYREFLY`; `CSHARP` vs `CSHARP_OMNISHARP`; `PHP` vs `PHP_PHPACTOR`/`PHP_PHPANTOM`).

### Layer 2: `serena` — agent, tools, MCP

- `SerenaAgent` (`agent.py`) owns lifecycle: active project, active tools, active modes, the language-server manager, dashboard, memory manager, task executor (single-threaded serialized execution via `TaskExecutor`).
- `mcp.py` adapts internal `Tool` objects into `FastMCPTool`s (built on the `mcp` SDK's `FastMCP`). It dynamically builds each MCP tool's JSON schema from the Python `apply()` signature + docstring, with an OpenAI-compatibility schema sanitizer and optional structured output toggling per client.
- **`LanguageBackend` abstraction**: the symbolic tools don't hard-depend on LSP. There are two interchangeable backends — the LSP backend (`solidlsp`) and a **paid JetBrains plugin backend** (`jetbrains/`, `project_server.py`) that reuses the IDE's own analysis engine. The tool surface is identical; the backend is swappable.

### Layer 3: `interprompt` — prompt factory

Jinja2-templated, multilingual prompt system. System prompts, onboarding prompts, and even **per-context tool descriptions** are generated from templates (`generated/generated_prompt_factory.py`). Modes/contexts inject Jinja that references `available_tools` and `tool_names[...]` so prompts adapt to whatever tool subset is active.

## Key Patterns Worth Learning From

### 1. Name-path symbol addressing (the core UX primitive)
Symbols are addressed by hierarchical **name-path**: `MyClass/my_method`, with `/`-prefix meaning absolute-from-root and support for substring matching and overload indices (`NamePathMatcher` in `symbol.py`). This is the abstraction that lets the agent say "edit `Foo/bar`" instead of "edit lines 40–55". It is stable across edits in a way line numbers are not. fmm's `fmm_read_symbol` / `fmm_lookup_export` occupy the same conceptual slot; Serena's name-path grammar (absolute vs relative, substring, overloads) is a richer addressing scheme worth studying.

### 2. Marker-class tool taxonomy + capability gating
Tools are plain classes with an `apply(self, ...) -> str` method; metadata comes from **marker mix-in classes** (`tools_base.py`):
- `ToolMarkerCanEdit` / `ToolMarkerSymbolicRead` / `ToolMarkerSymbolicEdit` — behavior category
- `ToolMarkerOptional` — disabled by default
- `ToolMarkerDoesNotRequireActiveProject` — usable before a project is activated
- `ToolMarkerBeta`

`apply_ex()` is the central dispatch wrapper: it checks the tool is active, that a project is active (unless marked otherwise), runs on the serialized task executor, catches exceptions into `ToolCallError`, logs, and length-limits output. Editing tools subclass `EditingToolWithDiagnostics`, which wraps every edit in a **before/after LSP diagnostics diff** context manager so the agent is told what compile errors its edit introduced or fixed. That "edit → immediately surface new diagnostics" loop is a strong pattern.

### 3. Context / Mode configuration system (dynamic tool + prompt shaping)
Two orthogonal config axes, both YAML + Jinja:
- **Contexts** (`config/contexts/*.yml`) = the client environment (claude-code, codex, ide, desktop-app, chatgpt, jetbrains…). A context declares `excluded_tools`, a system-prompt fragment, `single_project`, and quirks flags (e.g. `structured_tool_output: false` to work around a Claude Code bug).
- **Modes** (`config/modes/*.yml`) = the working posture (editing, planning, one-shot, interactive, onboarding, no-memories…). Modes further include/exclude tools and inject task-specific prompt guidance.

The `claude-code.yml` context is instructive: because Claude Code already has Read/Edit/Grep, Serena **excludes its own file tools** and ships an aggressive prompt forbidding the agent from using native Read/Edit on code files ("Read → FORBIDDEN for discovery. Use get_symbols_overview, then find_symbol"). The whole config layer exists to fit the tool surface to each host agent's existing capabilities and idiosyncrasies. This is a real lesson for any MCP server that coexists with a host agent's built-in tools: **overlap is a liability; explicitly cede or override.**

### 4. Onboarding + project memory system
Serena writes markdown **memory files** to `.serena/memories/` in the target repo (an `OnboardingTool` prompts the agent to explore the project and record build/test commands, conventions, structure). This repo's own `.serena/memories/` (`suggested_commands.md`, `tech_stack.md`, `task_completion.md`, `conventions.md`, `adding_new_language_support_guide.md`) is dogfooding. `MemoryManager` sandboxes reads/writes to the memories dir (with symlink-escape protection), supports global vs project-local memories, and read-only patterns. Conceptually parallel to Helioy's `cm` context store, but file-based and repo-local.

### 5. Two-tier symbol cache keyed by content hash
`SolidLanguageServer` maintains two pickle caches under `.serena/cache/<language_id>/`:
- **raw document-symbols cache** — the LSP `documentSymbol` response per file, keyed by file path + content hash, with an LS-specific cache-version fingerprint (bumping the version invalidates all entries).
- **high-level document-symbols cache** — the derived `DocumentSymbols` structure.
The recent commit history shows real care here: separating raw vs high-level fingerprints so that changing derived logic doesn't needlessly invalidate raw LSP results, and per-LS fingerprints for gopls/rust-analyzer. Cache staleness is detected by file-content change; a separate file-system polling mechanism was recently added because language servers weren't being notified of external edits, causing stale `find_referencing_symbols` results.

## Tool Surface (the MCP API)

Grouped by module in `src/serena/tools/`:
- **symbol_tools.py** (the heart): `get_symbols_overview`, `find_symbol` (by name-path, optional body), `find_referencing_symbols`, `find_implementations`, `find_declaration`, `get_diagnostics_for_file`, `get_diagnostics_for_symbol`, `replace_symbol_body`, `insert_after_symbol`, `insert_before_symbol`, `restart_language_server`. (Refactors `rename_symbol` / `safe_delete_symbol` are reference-aware and atomic.)
- **file_tools.py**: `read_file`, `create_text_file`, `list_dir`, `find_file`, `replace_content` (regex/string, with dry-run diff), `replace_in_files` (same edit across many files), `search_for_pattern`.
- **memory_tools.py**: `read_memory`, `list_memories`, `write_memory`.
- **workflow_tools.py**: `onboarding`, `initial_instructions` (the "Serena manual"), `serena_info`.
- **config_tools.py**: `activate_project`, `get_current_config`, mode switching.
- **cmd_tools.py**: `execute_shell_command`. **jetbrains_tools.py**: IDE-backed move/inline.

Note the deliberate design: **discovery is overview-first** (`get_symbols_overview` returns structure without bodies), then `find_symbol(..., include_body=True)` pulls only the needed symbol. This keeps tokens low on large files — the central efficiency argument.

## Dependencies (critical ones)

- `mcp==1.28.1` — the MCP Python SDK (`FastMCP` server). The whole external contract.
- `pygls==2.1.1` + `lsprotocol==2025.0.0` — used to *implement* one server (msl); the LSP client transport is hand-rolled in `lsp_protocol_handler/`.
- `flask` + `pywebview` + `pystray` — the local dashboard / log viewer / system-tray GUI.
- `jinja2` — prompt templating. `pydantic` — config + schemas. `tiktoken` — token counting for output limiting. `anthropic` — used in the self-evaluation harness, not the runtime path.
- Language servers themselves are **external binaries**, auto-downloaded/located at runtime, not Python deps.

## Relevance to fmm — LSP-driven vs index-driven

fmm and Serena solve the same problem — *give an AI agent symbol-level structural intelligence over a codebase via MCP* — with opposite architectures. This is the crux.

| Dimension | Serena (LSP-delegating) | fmm (persistent index) |
|---|---|---|
| Source of truth | Live language server per language | Own Rust-built index (`.fmm.db`) |
| Cross-file semantics (refs, defs, impls) | Delegated to LS at query time; fully accurate incl. types, generics, dynamic dispatch | Must be computed by fmm's own resolver (recall the phantom-edge resolver bugs) |
| Cold start | Slow first call (`request_full_symbol_tree` walks every file, one LSP `documentSymbol` each); mitigated by content-hash pickle cache | Index build up front, then O(1) queries |
| Per-query latency | LS round-trips; heavier | In-process index reads; very fast |
| Language breadth | 40+ languages ~free (someone else wrote the LS) | Each language needs fmm parser/resolver work |
| Semantic depth | Full IDE-grade (type-aware references) | Bounded by fmm's own analysis fidelity |
| Runtime footprint | Spawns real LS processes (memory, install deps) | Single Rust process, no external toolchain |
| Editing | Symbolic edits + reference-aware refactors validated by live LS diagnostics | Read/navigate focused; editing is not the core |
| Failure modes | LS crashes, ContentModified races, stale-file notifications (all seen in recent commits) | Resolver correctness, cache invalidation |

Concrete takeaways for fmm:

1. **Serena buys language breadth and semantic accuracy by not owning the analysis.** fmm's index-driven bet is the right one for *speed and zero-dependency footprint*, but it inherits the hard problem Serena outsources: correct cross-file resolution (fmm's own history of resolver phantom-edge fixes is exactly the class of bug LSP delegation avoids). Where fmm competes is latency and no-toolchain-required operation; where it must invest is resolver fidelity per language.

2. **Name-path addressing is a proven agent primitive.** Serena's `MyClass/my_method` grammar with absolute/relative/substring/overload semantics is more expressive than a flat symbol lookup. Worth benchmarking fmm's symbol-addressing ergonomics against it.

3. **Overview-first, body-on-demand is the token-efficiency core.** `get_symbols_overview` (structure, no bodies) → `find_symbol(include_body=True)` (one symbol). fmm's `fmm_file_outline` + `fmm_read_symbol` already mirror this; the pattern is validated.

4. **The context/mode config layer is the sharpest reusable idea.** Serena explicitly detects that its host agent (Claude Code) already has Read/Grep/Edit and *excludes its own overlapping tools*, then prompts hard to steer the agent to the semantic tools. fmm coexists with Claude Code's built-ins the same way; an explicit "what do we cede vs override, and how do we prompt the agent off grep" policy per host is directly applicable. fmm's own skill/prompt guidance is the analogue.

5. **Edit → diagnostics feedback loop.** `EditingToolWithDiagnostics` returns the before/after LSP diagnostic delta with every edit. fmm is navigation-first, but if it ever adds edit tools, surfacing structural breakage immediately is the pattern to copy — and fmm's index could cheaply detect broken references post-edit.

6. **Auto-provisioning is a huge, quiet cost.** Roughly a third of `solidlsp` is "find or install this language server." fmm sidesteps this entirely by building its own analysis — a real strategic advantage in install-friction terms that is easy to undervalue.

A plausible synthesis for a future fmm: index-driven for the fast path (outline, search, cheap references) with **optional LSP escalation** for the cases where full type-aware resolution matters, borrowing Serena's `solidlsp` provisioning patterns only where fmm's own resolver is weakest.

## Sources Consulted

- `README.md`, `pyproject.toml`, `CHANGELOG.md` (Unreleased + recent), `git log`
- `src/serena/tools/tools_base.py`, `symbol_tools.py`, `file_tools.py`, `workflow_tools.py` (tool taxonomy + surface)
- `src/serena/agent.py`, `mcp.py` (agent lifecycle, MCP adaptation)
- `src/serena/symbol.py` (name-path model, symbol retrieval)
- `src/solidlsp/ls.py` (SolidLanguageServer ABC, caching, `request_full_symbol_tree`, `request_document_symbols`), `ls_config.py` (Language enum registry), `language_servers/rust_analyzer.py` (LS wiring + auto-provision example)
- `src/serena/config/contexts/claude-code.yml`, `config/modes/editing.yml` (context/mode config)
- `src/serena/memories/memory_manager.py`, repo's own `.serena/memories/`

## Open Questions

- Exact eviction/size behavior of the pickle symbol caches on very large monorepos (cold-start cost at scale).
- How reference-aware refactors (`rename_symbol`) reconcile results across *multiple* language servers in a polyglot repo — is there a workspace-symbol merge, or strictly per-language?
- JetBrains backend parity: does the paid backend expose the identical tool surface with better accuracy, and what is the measured quality delta vs LSP?
- Real-world first-call latency of `request_full_symbol_tree` uncached — the number that most directly quantifies the index-vs-LSP trade-off for fmm's positioning.
