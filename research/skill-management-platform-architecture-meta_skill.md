---
title: "meta_skill (ms): Local-first Skill Management for AI Coding Agents"
type: research
tags: [dicklesworthstone, skills, ai-agents, rust, runtime-matters, configuration-management, mcp]
summary: "128K-line Rust CLI for skill lifecycle management: dual SQLite+Git persistence, hybrid search, bandit suggestions, multi-agent detection, composition/inheritance, bundle distribution, and MCP server. Directly comparable to runtime-matters."
status: active
source: github-researcher
confidence: high
created: 2026-04-24
updated: 2026-04-24
---

## Executive Summary

`meta_skill` (binary: `ms`) is a 128K-line Rust CLI that manages "skills" as the primary unit of operational knowledge for AI coding agents. It provides dual persistence (SQLite for queries + Git for audit), hybrid BM25/hash-embedding search, bandit-optimized suggestions, multi-agent detection and integration, skill composition via inheritance and includes, bundle-based distribution, progressive disclosure for context budget management, and an MCP server for native agent integration. Repository: `Dicklesworthstone/meta_skill`, 154 stars, Rust 2024 edition, created January 2026.

This is Jeffrey Emanuel's most ambitious Helioy-adjacent project. It overlaps significantly with `runtime-matters` in intent (managing what agents load) but diverges in scope: ms manages *skill content* (instructions, examples, rules), while runtime-matters manages *runtime configuration* (profiles, capabilities, hooks, MCP servers, settings). ms is a content management system for agent knowledge. runtime-matters is a configuration compiler for agent runtimes.

## Architecture

### Data Model

The core entity is a `SkillSpec`, a structured document with:
- **Metadata**: id, name, description, tags, version, author, license, dependencies, capabilities
- **Sections**: ordered list of `SkillSection`, each containing typed `SkillBlock`s
- **BlockTypes**: Rule, Code, Text, Pitfall, Checklist, Reference, Command, Output
- **Inheritance**: single `extends` field for parent skill (up to 5 levels deep, cycle-detected)
- **Composition**: `includes` field for composing content from multiple skills into target sections

Skills are stored as `SKILL.md` files with YAML frontmatter. The `SpecLens` module provides bidirectional spec-to-markdown mapping with round-trip verification.

**File:** `src/core/skill.rs` (core types), `src/core/spec_lens.rs` (round-trip compiler)

### Storage: Dual Persistence

Every skill is persisted twice:
1. **SQLite** (`ms.db`): queries, FTS, embeddings, usage tracking, feedback, experiments
2. **Git archive** (`archive/`): immutable history, diffs, audit trails

Transactional consistency is managed via `TxManager` (two-phase commit log). The schema has 20+ tables including `skills`, `skill_slices`, `skill_evidence`, `skill_usage`, `skill_experiments`, `build_sessions`, `cm_rule_links`, and security tables.

**Files:** `src/storage/sqlite.rs` (2255 lines), `src/storage/git.rs`, 12 migrations in `migrations/`

### Configuration System

Layered TOML configuration with deterministic precedence:
1. Built-in defaults (compiled)
2. Global config: `~/.config/ms/config.toml`
3. Project config: `.ms/config.toml`
4. Environment variables: `MS_*`
5. CLI flags

Uses a `Config` + `ConfigPatch` pattern: the full config has all defaults, patches are `Option<T>` wrappers that merge field-by-field. 15 config sections covering skill_paths, layers, disclosure, search, cass, cm, ru, cache, update, robot, agent_mail, security, safety, auto_load, output.

**File:** `src/config.rs` (1880 lines)

### Module Map (37 top-level modules)

| Module | Purpose | Lines (approx) |
|--------|---------|----------------|
| `core/` | Skill types, resolution, layering, packing, disclosure, dependencies | ~8K |
| `cli/` | 60+ CLI commands via clap derive | ~15K |
| `storage/` | SQLite + Git dual persistence | ~4K |
| `search/` | Tantivy BM25 + hash embeddings + RRF fusion | ~3K |
| `cass/` | CASS session mining and transformation | ~6K |
| `security/` | ACIP (prompt injection), DCG (command safety), path policy, secret scanner | ~3K |
| `agent_detection/` | Detect 9 AI coding agents on the system | ~1K |
| `bundler/` | Package/distribute/install skill bundles | ~2K |
| `sync/` | Multi-machine sync via Git + ru integration | ~3K |
| `meta_skills/` | Composed slice bundles with conditional inclusion | ~2K |
| `context/` | Project detection, working context, relevance scoring | ~2K |
| `suggestions/` | Bandit-optimized skill recommendations | ~2K |
| `import/` | Parse unstructured text into structured SkillSpec | ~2K |
| `output/` | Rich terminal output, themes, formatting | ~4K |
| `tui/` | Ratatui-based terminal UI | ~1K |

## Key Patterns

### 1. Agent Detection System

Detects 9 agent runtimes: Claude Code, Codex, Gemini CLI, Cursor, Cline, OpenCode, Aider, Windsurf, Continue. Each has a dedicated detector implementing an `AgentDetector` trait:

```rust
pub trait AgentDetector: Send + Sync {
    fn agent_type(&self) -> AgentType;
    fn detect(&self) -> Option<DetectedAgent>;
    fn get_config_path(&self) -> Option<PathBuf>;
    fn get_integration_paths(&self) -> Vec<PathBuf>;
}
```

Detection methods: config file presence, binary in PATH, running process, environment variable, VSCode extension. Integration status tracking: NotConfigured, PartiallyConfigured, FullyConfigured, Outdated.

**Files:** `src/agent_detection/mod.rs`, `src/agent_detection/detectors.rs`

### 2. Skill Composition (Inheritance + Includes)

Two composition mechanisms:
- **extends**: single inheritance chain (parent sections merged, child appends or replaces via flags)
- **includes**: multi-source composition into target sections (rules, examples, pitfalls, checklist, context)

Resolution order: inheritance chain first, then includes. Cached via `ResolutionCache`. Warnings for deep chains (>5), cycle detection, shadow detection.

**File:** `src/core/resolution.rs` (1355 lines), `docs/composition.md`

### 3. Progressive Disclosure

5 levels: Minimal (100 tokens), Overview (500), Standard (1500), Full (unlimited), Complete (with scripts/references). The `SkillSlicer` decomposes a spec into atomic slices typed as Policy, Rule, Example, Pitfall, Command, Reference, etc. The `ConstrainedPacker` then optimizes slice selection under a token budget using utility scores and coverage quotas.

Pack modes: Balanced, UtilityFirst, CoverageFirst, PitfallSafe. Pack contracts: Complete, Debug, Refactor, Learn, QuickRef, CodeGen.

**Files:** `src/core/slicing.rs`, `src/core/packing.rs`, `src/core/disclosure.rs`

### 4. Meta-Skills (Composed Slice Bundles)

Meta-skills are TOML-defined compositions referencing specific slices from multiple skills. Features:
- `PinStrategy`: LatestCompatible, ExactVersion, FloatingMajor, LocalInstalled, PerSkill
- `SliceCondition`: TechStack, FileExists, EnvVar, DependsOn
- `MetaDisclosureLevel`: Core, Extended, Deep
- Priority and required flags per slice reference

**Example:** `.ms/meta-skills/rust-safety.toml` composes slices from rust-error-handling, rust-memory-safety, rust-concurrency, etc. with priorities and conditional inclusion.

### 5. Layered Skill Resolution

Four-layer system: base, org, project, user. Skills at the same ID across layers are resolved via `ConflictStrategy` (PreferHigher, PreferLower, Interactive) and `MergeStrategy` (Auto, PreferSections, Replace). Produces `ResolvedSkill` with conflict details and diffs.

Overlays allow dynamic runtime modifications based on environment context.

**Files:** `src/core/layering.rs`, `src/core/overlay.rs`

### 6. Bundle Distribution

Binary package format (`MSBUNDLE1\0` header) with TOML manifest, SHA-256 checksums, optional Ed25519 signatures. Published to/downloaded from GitHub Releases. Install validates hashes and signatures before unpacking into the Git archive.

**Files:** `src/bundler/` (manifest, package, install, github, registry)

### 7. MCP Server

JSON-RPC over stdio (primary) or TCP. Exposes tools: search, load, evidence, list, show, doctor. Critical output safety: strips ANSI codes, validates JSON, blocks rich output in MCP mode regardless of env/config.

**File:** `src/cli/commands/mcp.rs` (1940 lines)

### 8. Context-Aware Suggestions

Project type detection via marker files (Cargo.toml, package.json, etc.) with confidence scores. Context fingerprinting from git state, recent files, and detected project type. Relevance scoring with weighted breakdown. Thompson sampling bandit with UCB exploration for adaptive recommendations.

**Files:** `src/context/`, `src/suggestions/`

## What meta_skill Got Right

1. **Dual persistence** is elegant. SQLite for fast queries, Git for provenance. runtime-matters uses git-managed workspace but no structured query layer. Adding SQLite for computed/cached data would be powerful.

2. **Progressive disclosure** solves the real context budget problem. Slicing skills into typed atoms and packing them under a token budget is sophisticated. The pack contract presets (Debug, Refactor, Learn) are genuinely useful abstractions.

3. **Agent detection trait** is clean and extensible. The `AgentDetector` trait with standardized detection methods (config, binary, process, env, extension) is a good pattern for runtime adapters.

4. **Config + ConfigPatch pattern** for layered configuration merging is well-designed. Field-by-field Option-based patching avoids the problems of generic map merging.

5. **Composition model** (extends + includes) gives skill authors both inheritance and mixin-style composition. The resolution cache prevents redundant computation.

6. **Meta-skills with conditional inclusion** (file_exists, env_var, tech_stack conditions) make bundle composition adaptive to project context.

7. **Comprehensive security layers**: ACIP for prompt injection, DCG for command safety, path policy, secret scanning. Defense-in-depth for a skill management system.

8. **Robot mode** as a first-class output concern. JSON output for machine consumption alongside human-readable output, with explicit detection of which mode to use.

## What meta_skill Got Wrong (or Where runtime-matters Has Advantage)

1. **Scope explosion**. 128K lines, 60+ CLI commands, 37 modules. The project tries to be everything: skill authoring, skill mining, skill distribution, skill suggestion, skill experimentation, session analysis, quality scoring, anti-pattern detection, TUI browser. This is a kitchen-sink problem. Many features feel bolted on rather than emergent from core abstractions.

2. **Skill-centric, not runtime-centric**. ms manages skill content (instructions, rules, examples) but does not compile runtime configurations. It cannot generate a complete Claude Code `settings.json` or Codex `config.yaml`. It tells agents what knowledge to use, not how the runtime should be configured. runtime-matters addresses the actual deployment problem: given a profile and capabilities, produce the correct runtime home.

3. **No overlay/profile system for runtime settings**. While ms has "overlays" for skill content modification, it has no concept of profiles that compose hooks, MCP servers, permissions, and settings. The overlay system modifies metadata (description, tags) but cannot control runtime behavior.

4. **Agent detection without agent configuration**. ms detects agents and generates a SKILL.md for them, but it cannot write or manage their native configuration files. The `setup` command is one-shot integration, not ongoing configuration management.

5. **CASS dependency**. The project originated as a CASS session miner and retains deep coupling to CASS session format. This limits its utility for users who do not use CASS.

6. **No source normalization pipeline**. ms discovers SKILL.md files in configured paths but does not normalize imported material across heterogeneous sources (GitHub repos, web catalogs, local files) into a canonical format with provenance tracking. runtime-matters' source import/normalize/edit-in-place model is more principled.

7. **SQLite is mandatory for basic operation**. The dual persistence model means every operation requires a database. This increases setup friction and makes the system less portable than a pure filesystem approach.

8. **Bandit optimization is premature**. Thompson sampling with UCB exploration for skill suggestion is engineering sophistication that provides marginal value over simple recency + tag matching for most users. The configuration surface area for the bandit (exploration_rate, learning_rate, cold_start_threshold, bandit_blend) suggests over-engineering.

## Relevance to runtime-matters

### Direct Parallels

| meta_skill Concept | runtime-matters Equivalent | Assessment |
|--------------------|-----------------------------|------------|
| SkillSpec | Capability manifest | ms models skill *content*; rm models *configuration*. Different layers. |
| Layers (base/org/project/user) | Profile composition hierarchy | Similar concept. ms uses layer priority with conflict resolution; rm compiles profiles without overlays. |
| AgentDetector trait | Runtime adapter | ms detects presence; rm needs to detect, read, write, launch. rm goes further. |
| Meta-skills (TOML composition) | Profiles | Both compose smaller units. Meta-skills compose *slices*; profiles compose *capabilities*. |
| Config + ConfigPatch | Manifest schema + compilation | ms patches config fields; rm compiles manifests into generated runtime homes. rm is more transformative. |
| Bundle distribution | Source import from catalogs | ms packages skills as binary bundles with signatures; rm imports from GitHub/web/local. Different distribution models. |
| `.ms/` project root | `RUNTIME_MATTERS_HOME` | ms walks up to find `.ms/`; rm uses a fixed home directory. |
| Disclosure levels | N/A | runtime-matters does not need progressive disclosure because it compiles configurations, not content. |

### Patterns to Adopt

1. **AgentDetector trait structure**. The trait with `detect()`, `get_config_path()`, `get_integration_paths()` is a clean starting point for runtime adapters. Add `read_config()`, `write_config()`, `launch()` methods for runtime-matters.

2. **Config + ConfigPatch pattern**. Strongly typed defaults with Option-based patches for layered merging is robust. Consider for profile composition in runtime-matters.

3. **Conditional inclusion model**. `SliceCondition` with `TechStack`, `FileExists`, `EnvVar`, `DependsOn` variants is directly useful for conditional capability inclusion in profiles.

4. **Robot mode as first-class concern**. Dual human/machine output with explicit format selection. Important for runtime-matters commands that may be called by agents.

5. **Project type detection**. Marker-file-based project detection with confidence scores could inform which profiles or capabilities are relevant to a project.

### Patterns to Avoid

1. **Scope sprawl**. 60+ commands is a maintenance burden. runtime-matters should stay focused on the core workflow: setup, sync, create-profile, compile, launch.

2. **SQLite as mandatory dependency**. Keep the filesystem as the source of truth. Use a database only for caching/indexing if needed.

3. **Dual persistence as default**. The Git + SQLite dual write adds complexity. runtime-matters already uses git-managed workspace; adding a second persistence layer should be a deliberate future decision, not a launch requirement.

4. **Bandit-based suggestion**. Over-engineered for the problem space. Simple heuristics serve better until there is strong evidence users need adaptive recommendations.

5. **CASS/session mining integration at the core level**. Keep external tool integrations as optional modules, not core dependencies.

### Key Insight

ms and runtime-matters operate at different layers of the same stack. ms manages "what should the agent know?" (skills, rules, examples). runtime-matters manages "how should the agent be configured?" (settings, hooks, MCP servers, permissions). They are complementary, not competitive. A complete system would use runtime-matters to configure the agent runtime and ms (or something like it) to manage the skill content that gets loaded into that runtime.

The most valuable thing to take from ms is the *agent detection* pattern and the *conditional composition* model. The least valuable is the content management machinery (search, slicing, packing, mining) which is orthogonal to runtime configuration.

## Dependencies (Notable)

- **rusqlite** (bundled SQLite): primary query store
- **tantivy**: BM25 full-text search
- **git2** (vendored OpenSSL): Git archive operations
- **ratatui + crossterm**: TUI
- **clap** (derive): CLI with 60+ commands
- **ring**: Ed25519 signature verification
- **tokio**: async runtime for MCP server
- **serde + toml + serde_yaml + serde_json**: multi-format serialization
- **rich_rust**: terminal styling library (also by Dicklesworthstone)
- **toon_rust (tru)**: another Dicklesworthstone utility crate

## Sources Consulted

- `README.md`, `AGENTS.md`, `CONTRIBUTING.md`
- `Cargo.toml`, `src/lib.rs`, `src/main.rs`, `src/app.rs`
- `src/config.rs` (full 1880 lines)
- `src/core/skill.rs`, `src/core/resolution.rs`, `src/core/layering.rs`, `src/core/overlay.rs`
- `src/core/disclosure.rs`, `src/core/slicing.rs`, `src/core/packing.rs`
- `src/agent_detection/mod.rs`, `src/agent_detection/detectors.rs`
- `src/bundler/` (mod, github, install)
- `src/meta_skills/types.rs`
- `src/sync/ru.rs`
- `src/context/detector.rs`
- `src/cli/commands/` (mod, mcp, load, setup)
- `src/skill_md/mod.rs`, `src/core/spec_lens.rs`
- `src/storage/mod.rs`
- `docs/composition.md`, `docs/bundles.md`, `docs/config_system.md`
- `migrations/001_initial_schema.sql`
- `.ms/meta-skills/rust-safety.toml`, `.ms/meta-skills/api-design.toml`
- `skills/examples/` (rust-complete SKILL.md)
- `BEST_PRACTICES_FOR_WRITING_AND_USING_SKILLS_MD_FILES.md`
- Git log (30 recent commits)

## Open Questions

1. How does ms handle version conflicts when multiple meta-skills depend on different versions of the same base skill? The PinStrategy system exists but the actual resolution logic was not fully traced.
2. What is the actual user adoption? 154 stars, but usage patterns and community contributions are unclear.
3. How does the MCP server handle concurrent access from multiple agents? The code mentions fallback to read-only search index, but database locking under concurrent MCP servers is unclear.
4. The `ru` (Repo Updater) integration suggests a companion tool. What is `ru` and is it open source? It appears to be a git repo syncer but is not in the same repository.
