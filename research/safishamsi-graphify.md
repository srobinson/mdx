---
title: "graphify: Skill-Based Knowledge Graph Builder for AI Coding Assistants"
type: research
tags: [knowledge-graph, code-intelligence, claude-code-skill, tree-sitter, leiden, mcp, graphrag, python]
summary: "Senior-engineering review of safishamsi/graphify (35.4K stars). A Python CLI plus skill packaging that converts mixed-corpus folders into a NetworkX graph via tree-sitter AST plus LLM-subagent semantic extraction, with Leiden community detection, MCP-based graph queries, and one-click installers for 14+ AI coding assistants."
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

`graphify` (PyPI: `graphifyy`) is a Python knowledge-graph builder that doubles as a slash-command skill across 14+ AI coding assistants (Claude Code, Codex, Cursor, Copilot CLI, Gemini CLI, Aider, Trae, Kiro, Antigravity, etc.). It runs a deterministic tree-sitter AST pass over 25 languages, dispatches parallel LLM subagents over docs/papers/images/transcripts, merges the results into a NetworkX graph, applies Leiden community detection, and emits an interactive HTML viz, a `graph.json`, an Obsidian vault, and a `GRAPH_REPORT.md`. Distribution is the moat: install hooks across nearly every AI coding tool with copy-paste install commands. Engineering quality is high in the extraction core and security helpers, but undermined by file gigantism (`extract.py` at 3,440 lines, `__main__.py` at 1,506 lines), CI configured against branches that no longer exist (`v5` is the default branch; CI triggers on `v1..v4` and `main`), and a single-author bus-factor of 1.

## Repository Snapshot

| Field | Value |
|---|---|
| Stars | 35,414 |
| Forks | 3,934 |
| Default branch | `v5` (last push 2026-04-25) |
| Created | 2026-04-03 |
| License | MIT |
| Primary language | Python (616 KB) |
| Open issues | 71 |
| PRs (lifetime) | 112 |
| Maintainer | safishamsi (sole committer in last 50 commits) |
| Funding | GitHub Sponsors + Gumroad book ("The Memory Layer") |
| Homepage | graphifylabs.ai |

The star/age ratio (35K stars in roughly 3 weeks) indicates aggressive distribution: 28 README translations, Trendshift badge, and skill-installer support for almost every AI coding assistant on the market.

## Architecture

### Pipeline (from `ARCHITECTURE.md` lines 7-31)

```
detect()  ->  extract()  ->  build_graph()  ->  cluster()  ->  analyze()  ->  report()  ->  export()
```

Stages communicate through plain Python dicts and NetworkX graphs. No shared state. Side effects confined to `graphify-out/`. Each stage maps to a single module function.

### Module Layout (`graphify/`, 9,765 LOC total)

| File | LOC | Role |
|---|---|---|
| `extract.py` | 3,440 | Per-language AST extraction (25 languages) plus dispatcher |
| `__main__.py` | 1,506 | CLI plus 14+ platform installers |
| `export.py` | 1,044 | HTML/SVG/JSON/GraphML/Cypher/Obsidian writers |
| `analyze.py` | 540 | God nodes, surprises, knowledge-gap reporting |
| `detect.py` | 511 | File walk plus `.graphifyignore` plus extension routing |
| `serve.py` | 373 | MCP stdio server (7 tools) |
| `ingest.py` | 297 | URL fetch plus oEmbed for tweets |
| `watch.py` | 240 | Watchdog-based incremental rebuild |
| `build.py` | 234 | Extraction-dict-to-NetworkX, dedup, shrink-guard merge |
| `wiki.py` | 227 | Per-community markdown article generator |
| `report.py` | 181 | `GRAPH_REPORT.md` rendering |
| `cache.py` | 178 | SHA256 file-content cache |
| `cluster.py` | 137 | Leiden (graspologic) with Louvain (networkx) fallback |
| `security.py` | 205 | URL validation, path guard, label sanitizer |

`graphify/skill.md` (1,377 lines) is the orchestrator prompt that the AI assistant executes when the user types `/graphify`. The skill dispatches AST and semantic subagents in parallel, manages the cache, and merges results.

### Three-Pass Extraction (README lines 64-70)

1. **AST pass (deterministic, no LLM).** `extract.py` dispatches per-language extractors built on a shared `LanguageConfig` dataclass (`extract.py:24-63`). Cross-file call resolution via `_resolve_cross_file_imports` (`extract.py:2577`).
2. **Transcription pass.** Local `faster-whisper` over audio/video, prompted by current corpus god nodes for domain-aware ASR.
3. **Semantic pass (LLM subagents).** The skill spawns parallel subagents per uncached doc/paper/image, each returning the same `{nodes, edges}` dict that the AST pass produces. Confidence is tagged `EXTRACTED`, `INFERRED`, or `AMBIGUOUS`.

### Storage and Output

`graphify-out/` contains `graph.json`, `graph.html`, `GRAPH_REPORT.md`, optional Obsidian vault, optional `wiki/` (one markdown article per Leiden community). Designed to be committed to git for team workflows (README lines 173-188).

### Hook-Based Always-On Mode

For Claude Code: writes a CLAUDE.md section plus a `PreToolUse` hook in `settings.json` that fires before every Glob/Grep call (`__main__.py:39-51`). When `graphify-out/graph.json` exists, the hook injects an `additionalContext` reminder telling the assistant to read `GRAPH_REPORT.md` first. Equivalent shims exist for Codex (`hooks.json`), OpenCode (plugin), Gemini CLI (`BeforeTool`), Cursor (`alwaysApply: true` rule), and Kiro (steering with `inclusion: always`). Tools without hook support get `AGENTS.md` injection.

## Quality Assessment

### Strengths

**Honest confidence labels in the data model.** Every edge carries `EXTRACTED`, `INFERRED`, or `AMBIGUOUS` (validated in `validate.py`, surfaced in `report.py` and `serve.py:301-311`). This is the right primitive for a hybrid AST-plus-LLM extractor and prevents the usual "looks authoritative, secretly hallucinated" failure mode.

**`LanguageConfig` dataclass for language extension.** `extract.py:24-63` defines a single dataclass that captures the per-language tree-sitter knobs (node-type sets, name fields, body fallbacks, import handler hook, function-name resolver hook, extra walk hook). `_extract_generic` (`extract.py:654`) dispatches against it, which is genuinely the right abstraction. Adding a new language is documented as five concrete steps in `ARCHITECTURE.md:57-63`.

**Security helpers are real, not theater.** `security.py:26-64` validates URL schemes, resolves hostnames, blocks RFC1918/loopback/link-local IPs, blocks GCP metadata endpoints (`metadata.google.internal`), and re-validates redirect targets via `_NoFileRedirectHandler` (lines 67-76). `safe_fetch` streams with a 50 MB cap (lines 87-128). Symlink traversal is explicit (`os.walk(..., followlinks=False)` per SECURITY.md line 39). Tree-sitter byte slices use `errors="replace"` so malformed source files degrade rather than crash.

**Build-time data hygiene.** `build_from_json` (`build.py:42-106`) auto-canonicalizes legacy `source` to `source_file`, normalizes IDs so LLM-extracted edges survive minor casing/punctuation drift versus AST-extracted node IDs (`_normalize_id`, `build.py:32-39`), and silently skips dangling external imports while warning on real schema errors. `deduplicate_by_label` (`build.py:135-178`) collapses duplicates from parallel subagents using normalized labels and prefers shorter non-chunk-suffixed IDs. `build_merge` (`build.py:181-234`) refuses to overwrite a graph with a smaller one without explicit `prune_sources` (issue #479 fix).

**Test surface matches module surface.** 27 test files, one per module, covering 4,273 test LOC. Pure unit tests with no network or filesystem side effects outside `tmp_path` (`ARCHITECTURE.md:78-84`). Fixtures cover all 25 languages.

**Maintenance velocity.** 50 commits since 2026-04-17 (10 days), most reference issue numbers, most ship same-day after a community report. The CHANGELOG is detailed and actionable.

**Distribution is the moat.** Skill-mode integration with 14+ assistants, install commands that write the right always-on hook for each platform, and 28 README translations. The friction to onboard is one shell command.

### Weaknesses

**File gigantism violates Helioy's 700-line rule by 5x.** `extract.py` is 3,440 lines and contains 41 top-level functions ranging from `_import_python` to `extract_elixir`. There is one obvious refactor: each per-language block (`extract_go` at 1,874, `extract_rust` at 2,073, `extract_zig` at 2,250, `extract_powershell` at 2,413, `extract_objc` at 2,795, `extract_elixir` at 2,993) should live in `extract/<lang>.py` with a registry pattern. The current structure means a single language change forces a full-file diff. `__main__.py` (1,506 lines) similarly bundles every platform installer; `_PLATFORM_CONFIG` plus a separate `installers/<platform>.py` would cut this in half.

**CI is configured against dead branches.** `.github/workflows/ci.yml:5-6` triggers on `["v1", "v2", "v3", "v4", "main"]`. The default branch is `v5`. The README CI badge points at `branch=v4` (line 11). New commits on `v5` do not run CI. Pull requests targeting `v5` do not run CI. This is a quietly broken state that matters for a 35K-star project with 112 lifetime PRs.

**Bus factor of 1.** All 50 visible commits are by `Safi`. There are no other committers in the shallow history. The CHANGELOG (#480 closed PRs would suggest community participation) shows community PR fixes being re-implemented by Safi rather than merged directly.

**SECURITY.md overstates a mitigation.** `SECURITY.md:34` claims path traversal in the MCP server is mitigated by `security.validate_graph_path()`. `serve.py:11-29` does not import or call `validate_graph_path`; `_load_graph` does only `Path(graph_path).resolve()` plus a suffix and existence check. The function is defined and unit-tested (`tests/test_security.py:140-164`) but unused in the actual MCP entrypoint. The user-controlled CLI argument keeps the practical risk low, but the security doc is wrong about the code.

**Default-branch naming churn.** Branches `v1..v5` exist as moving defaults rather than tags. Star History badge (README line 19) and CI badge both reference older branches. This makes external links rot every few weeks and reflects an unusual release model that may confuse contributors.

**One vendored "tree-sitter-objc" hard dependency in pyproject.toml** for a 25-language extractor means `pip install graphifyy` pulls 23 tree-sitter wheels even for users who only need Python. Optional-dependency groups exist for `mcp`, `pdf`, `office`, `video`, etc., but not for language extractors. A `[python-only]` extra would shrink the default install footprint considerably.

**The skill prompt does the heavy lifting.** `graphify/skill.md` is 1,377 lines of bash-heavy orchestration that the assistant executes in the user's terminal. Errors here surface as the assistant printing weird messages or running the wrong Python interpreter. The recovery model is "rerun the skill," which is fine until the cache or partial state poisons subsequent runs.

**The PyPI name mismatch (`graphifyy` versus `graphify`) is awkward** and noted in the README (lines 85-87) as a defensive workaround against name squatting. It will continue to confuse users for the lifetime of the project.

### Notable Patterns

**Skill-as-orchestrator, library-as-primitives.** The Python library exposes pure functions (`detect`, `extract`, `build`, `cluster`, `analyze`, `report`, `export`). The skill prompt orchestrates them via shell commands in the assistant's terminal. The CLI is a thin shim. This means three execution surfaces (library, CLI, skill) all feed the same primitives. It is a clean separation that matches MCP server design (`serve.py`) where 7 tools wrap library functions over a JSON-RPC stdio transport.

**Hook injection as always-on UX.** The PreToolUse hook (`__main__.py:39-51`) is one of the cleaner patterns in the repo: a one-line bash conditional that fires before Glob/Grep, checks for `graphify-out/graph.json`, and emits `additionalContext` JSON if present. This is exactly the pattern Helioy could use to wire `cm`/`am`/`fmm` into Claude Code without users explicitly invoking them.

**Graph as similarity signal, no embeddings.** Leiden runs on the existing graph. `semantically_similar_to` edges (extracted by LLM subagents and tagged INFERRED) are already in the graph and influence community detection directly. There is no separate vector store. README line 68 frames this as a deliberate choice; for code corpora with strong AST structure, this is reasonable.

**Three-layer dedup.** Per-extractor `seen_ids`, NetworkX add_node idempotence, and explicit `seen` set in the skill before `build()`. Documented in `build.py:1-21`. Worth copying.

## Dependencies

- **`networkx`** — graph storage, traversal, Louvain fallback. Pinned only by lower bound.
- **`tree-sitter` 0.23+** plus 21 language grammars — AST extraction. Hard dependencies.
- **`graspologic`** (optional, `[leiden]`) — Leiden partitioning. Falls back to NetworkX Louvain when absent. Constrained to `python_version < '3.13'` due to upstream.
- **`mcp`** (optional) — MCP server. The library imports lazily.
- **`faster-whisper` plus `yt-dlp`** (optional, `[video]`) — local audio/video transcription with corpus-derived prompts.
- **`pypdf`, `html2text`, `python-docx`, `openpyxl`** (optional) — document extractors.
- **`watchdog`** (optional, `[watch]`) — incremental filesystem rebuild.
- **`matplotlib`** (optional, `[svg]`) — SVG export.

No LLM SDK is a direct dependency. The semantic pass runs inside the host AI assistant via subagent dispatch, so graphify itself never makes Anthropic/OpenAI API calls. This is unusual and clever; it means the user's existing assistant subscription pays for the LLM cost.

## Relevance to Helioy

There are concrete ideas here worth lifting and concrete pitfalls to avoid.

**Lift: PreToolUse hook pattern for cm/am/fmm.** `__main__.py:39-51` is the minimum viable always-on hook. Helioy already has `cm`/`am`/`fmm` MCP servers; what is missing is a one-shot installer that writes the equivalent of graphify's hook to `~/.claude/settings.json` so the assistant gets reminded to query memory before raw filesystem search. The graphify install code shows the exact JSON shape and matcher syntax (`Glob|Grep`).

**Lift: confidence-tagged edges.** Helioy memory layers (`am`, `cm`) already separate facts from inferences in some places. graphify's three-tier `EXTRACTED`/`INFERRED`/`AMBIGUOUS` is the simplest workable schema and surfaces directly in user-facing outputs. Worth copying for any future memory-graph design in `attention-matters` or `context-matters`.

**Lift: skill-as-orchestrator pattern.** `skill.md` runs everything as bash via the assistant's terminal. Helioy's skills (per `~/.claude/CLAUDE.md`) follow a different pattern; graphify shows that pure-bash orchestration with library primitives can scale to a 1,377-line skill if the library is cleanly factored. Counter-evidence for the "skills should be thin" assumption.

**Avoid: file gigantism.** `extract.py` at 3,440 lines is the anti-pattern Helioy explicitly forbids ("New files should never be more than +-700 lines"). graphify shows what the failure mode looks like: per-language dispatch trapped in a single module, no clean way to add a 26th language without conflict.

**Avoid: documenting mitigations that don't exist in code.** SECURITY.md claims `validate_graph_path` is used in the MCP server. It is not. Helioy security docs should match grep results or stop existing.

**No direct overlap.** graphify is a code-and-corpus knowledge graph for human consumption via assistant tools. Helioy components (`cm`, `am`, `fmm`) are agent-memory primitives. The use cases differ. graphify is what an external user installs; Helioy is what Stuart uses to build other things.

## Sources Consulted

- `README.md` (lines 1-200, primary)
- `ARCHITECTURE.md` (full)
- `SECURITY.md` (full)
- `pyproject.toml` (full)
- `.github/workflows/ci.yml` (full)
- `graphify/security.py` (full)
- `graphify/build.py` (full)
- `graphify/cluster.py` (full)
- `graphify/serve.py` (full)
- `graphify/extract.py` (lines 1-120; symbol map of full file)
- `graphify/__main__.py` (lines 1-200, 900-1100; symbol map of full file)
- `graphify/analyze.py` (lines 1-120)
- `graphify/skill.md` (lines 1-120)
- `tests/test_extract.py` (lines 1-80)
- `CHANGELOG.md` (lines 1-60)
- `git log` (50 commits, 2026-04-17 to 2026-04-25)
- `gh issue list` (top 20 open, top 5 closed)
- `gh repo view` metadata

## Open Questions

- Why is the PyPI package `graphifyy` rather than `graphify`? README explains it as a defense against squatters, but the unilateral squat by `graphifyy` itself is unexplained.
- The 35K stars in 24 days is an outlier even for AI-coding-assistant tooling. Trendshift badge and aggressive cross-promotion are visible in the commit log. What is the organic-versus-promoted ratio?
- What is the `worked/` directory? It contains `example/`, `httpx/`, `karpathy-repos/`, `mixed-corpus/` subdirs that look like demo corpora but are not referenced from README or tests.
- What was on `v1`-`v4`? The branch-as-version pattern is unusual and the branches still exist on the remote. Is there ongoing parallel work or are these effectively tags?
