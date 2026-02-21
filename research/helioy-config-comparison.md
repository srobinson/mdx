---
title: Config Management Comparison: mdcontext vs attention-matters
tags: [config, effect-ts, architecture, mdcontext, attention-matters, helioy]
date: 2026-03-14
---

# Config Management Comparison: mdcontext vs attention-matters

## Executive Summary

mdcontext has a 6-file, ~700-line config system built on Effect's `Config` and `ConfigProvider` abstractions. attention-matters has a single 265-line `config.rs` using serde + TOML. Both projects solve the same problem. One takes 10x the code to do it. The complexity delta is the root cause of confusion.

---

## 1. attention-matters: Config System

### Schema Definition

A single file: `crates/am-store/src/config.rs`.

Two structs define the schema:

- `FileConfig` (private, serde `Deserialize`, all `Option` fields): the wire format for TOML deserialization
- `Config` (public, concrete types, `Default` impl): the resolved runtime config

`BudgetConfig` exists separately in `am-core/src/compose.rs` as a function parameter struct. It has its own `Default` impl and is constructed inline at call sites. It is not part of the config file system at all.

### Loading

One function: `config::load() -> Config`.

1. Start with `Config::default()`
2. Find a config file (CWD, then `$AM_DATA_DIR`, then `~/.attention-matters/`)
3. Parse TOML, apply each present field over the default
4. Apply env vars (`AM_DATA_DIR`, `AM_GC_ENABLED`, `AM_DB_SIZE_MB`, `AM_SYNC_LOG_DIR`)
5. Return the fully resolved `Config`

File format: TOML only. One filename: `.am.config.toml`.

### Precedence

```
Environment variables  (highest)
Config file            (middle)
Compiled defaults      (lowest)
```

Three levels. No CLI flag layer because the CLI does not expose config overrides as flags.

### Consumption

`Config` is a plain struct passed as `&Config` to functions that need it:

```rust
fn open_store(_cli: &Cli) -> Result<BrainStore> {
    let config = load_config();
    BrainStore::open(&config)
}
```

No dependency injection framework. No service tags. No layers. The config is loaded once at CLI startup and threaded through as a function argument.

### What Can Be Configured

10 fields total across two sections:

- `data_dir`, `gc_enabled`, `db_size_mb`, `sync_log_dir` (top level)
- `retention.grace_epochs`, `retention.retention_days`, `retention.min_neighborhoods`, `retention.recency_weight` (nested section)

### Defaults

`Config::default()` and `RetentionPolicy::default()` provide concrete values. The `FileConfig` uses `Option<T>` for every field, so missing keys simply retain the default.

### Validation / Errors

Parse errors are logged via `tracing::warn!` and the file is silently skipped. Invalid env var parsing (e.g., non-boolean for `AM_GC_ENABLED`) is silently ignored because the `if let Ok(...)` chain drops parse failures. The system always produces a valid `Config`.

### Self-Documentation

`generate_default_toml()` produces a fully commented config template. Users can `am config init` to create their config file.

---

## 2. mdcontext: Config System

### Schema Definition

`src/config/schema.ts` (~600 lines).

Uses Effect's `Config` combinators to define 7 config sections:

- `IndexConfig`, `SearchConfig`, `EmbeddingsConfig`, `SummarizationConfig`, `AISummarizationConfig`, `OutputConfig`, `PathsConfig`

Each section uses `Config.all({...})` with `Config.withDefault()` on every field. The top-level `MdContextConfig` nests them via `Config.nested()`.

A parallel `defaultConfig` object duplicates every default value as a plain JS object.

Types are inferred from the Config combinators using `Config.Config.Success<typeof X>`.

### Loading

Multiple entry points:

1. `loadConfigFile(startDir)`: walks up directories to git root looking for config files
2. `loadConfigFromPath(configPath)`: loads from explicit path
3. `createFileConfigProvider(config)`: wraps a parsed config in a ConfigProvider
4. `loadFileConfigProvider(startDir)`: combines search + provider creation

Supported file formats: `.ts`, `.js`, `.mjs`, `.json`, `.mdcontextrc`, `.mdcontextrc.json` (6 variants).

TS/JS files are loaded via `dynamic import()`. JSON files via `fs.readFileSync` + `JSON.parse`.

### Precedence

```
CLI flags              (highest)
Environment variables  (MDCONTEXT_*)
Config file            (middle)
Config.withDefault()   (lowest)
```

Four levels. The precedence chain is implemented in `precedence.ts` by flattening all sources into a single `Map<string, string>` and creating a `ConfigProvider.fromMap()`.

### Consumption

Three different patterns are used:

1. **Effect Context.Tag DI**: `ConfigService` is a tagged service. Code does `yield* ConfigService` to access config. Requires a `Layer` to be provided.

2. **ConfigProvider ambient**: `MdContextConfig` (the schema) is also a `Config<T>`, which reads from the ambient `ConfigProvider`. The CLI uses `Effect.withConfigProvider(provider)` to inject it.

3. **Direct extraction helpers**: `config-layer.ts` defines `getSearchConfig()`, `getIndexConfig()`, `getOutputConfig()` that extract sections from a full config object passed as a plain argument.

Additionally, `getConfig`, `getConfigSection`, and `getConfigValue` are Effect-wrapped accessors that read from the `ConfigService` tag.

### What Can Be Configured

~45 fields across 7 sections, covering indexing, search, embeddings, summarization, AI summarization, output formatting, and paths.

### Defaults

Defaults exist in two places:

1. Inside the `Config.withDefault()` calls on each combinator
2. In the `defaultConfig` plain object

These must be kept in sync manually. They serve different purposes: the combinator defaults are used when resolving from a ConfigProvider; the object defaults are used when constructing a `ConfigService` layer directly (tests, fallbacks).

### Validation / Errors

- `ConfigError` (custom error class) is thrown for file loading failures
- Effect's `Config` combinators handle type validation (e.g., `Config.number` rejects non-numeric strings)
- `config-layer.ts` has imperative validation (`validateConfigFileExists`, `validateConfigObject`) that calls `process.exit(1)` on failure
- The `makeCliConfigLayer` function catches all errors and falls back to defaults silently

### Env Var Mapping

`precedence.ts` maintains `CONFIG_SCHEMA_KEYS`, a parallel declaration of every config key per section. A compile-time type assertion checks completeness against the schema. Env vars follow the pattern `MDCONTEXT_SECTION_KEY` (all lowercase).

---

## 3. Comparison

### Where the Philosophies Agree

Both projects follow the same precedence model: env vars override file config, file config overrides defaults. Both use "all fields optional in the wire format, all fields required in the resolved type" as their fundamental pattern. Both guarantee a valid config object at runtime regardless of what the user provides.

### Where They Diverge

| Aspect | attention-matters | mdcontext |
|--------|------------------|-----------|
| Language | Rust | TypeScript (Effect) |
| File count | 1 file | 6 files |
| Line count | ~265 | ~700+ |
| Schema definition | serde structs | Effect Config combinators |
| Wire format type | `Option<T>` struct | `PartialMdContextConfig` (deep partial) |
| Resolved type | concrete struct | inferred from Config combinators |
| File formats | TOML only | TS, JS, MJS, JSON, rc, rc.json |
| DI mechanism | function argument | Effect Context.Tag + Layer |
| Precedence layers | 3 | 4 (adds CLI flags) |
| Default duplication | none | yes (combinator defaults + plain object) |
| Schema key duplication | none | yes (`CONFIG_SCHEMA_KEYS` + schema definition) |
| Env var mapping | 4 explicit `env::var()` calls | programmatic mapping from `CONFIG_SCHEMA_KEYS` |
| Error handling | log and skip | mixed (Effect errors + process.exit) |

### Root Cause of the Confusion

The mdcontext config system is confusing because it has **three competing mechanisms doing the same job**, and the boundaries between them are unclear.

**Mechanism 1: Effect ConfigProvider (the "pull" model)**

`MdContextConfig` in `schema.ts` is an `Effect.Config<T>`. When you write `yield* MdContextConfig`, Effect pulls config values from the ambient `ConfigProvider`. This is the idiomatic Effect approach. The schema, defaults, and type inference are all unified in one place.

**Mechanism 2: ConfigService tag (the "push" model)**

`ConfigService` in `service.ts` is a `Context.Tag` that holds a fully resolved `MdContextConfig` object. Code accesses it via `yield* ConfigService`. This is also idiomatic Effect, but it is a different mechanism from ConfigProvider. The config is resolved once and pushed into the context as a concrete value.

**Mechanism 3: Plain object passing (the "escape hatch")**

`config-layer.ts` defines extraction functions (`getSearchConfig`, `getIndexConfig`) that take a `MdContextConfig` as a plain argument and return section subsets. `withCliOverride` handles individual flag overrides outside the Effect system entirely.

The confusion arises because:

1. **ConfigProvider and ConfigService are both used, but they serve overlapping roles.** ConfigProvider resolves config from sources. ConfigService holds the resolved config. The bridge between them is `ConfigServiceLive`, which does `Layer.effect(ConfigService, MdContextConfigSchema)`. The schema is used to pull from ConfigProvider, and the result is pushed into ConfigService. This two-step dance exists solely because Effect's Config and Context.Tag are separate abstractions that don't compose automatically.

2. **Defaults are declared twice.** The `Config.withDefault()` calls define what happens when a ConfigProvider is missing a key. The `defaultConfig` object defines what the `ConfigServiceDefault` layer provides when no ConfigProvider is configured at all. These serve logically distinct purposes, but practically they must always agree. Any drift is a silent bug.

3. **The env var mapping requires a third declaration of the schema.** `CONFIG_SCHEMA_KEYS` lists every config key per section. The type-level completeness check validates against the generated mapping, but the schema itself (`schema.ts`) is the source of truth for types and defaults. Adding a config field requires touching three files: `schema.ts` (add the combinator), `precedence.ts` (add to `CONFIG_SCHEMA_KEYS`), and `schema.ts` again (add to `defaultConfig`).

4. **CLI main.ts has its own parallel config loading path.** The `main.ts` file does not use `makeCliConfigLayer` from `config-layer.ts`. It calls `createConfigProviderSync` directly, then manually resolves `MdContextConfig` with `Effect.withConfigProvider`, then creates a `Layer.succeed`. This duplicates the logic in `config-layer.ts` lines 29-65.

5. **Error handling is schizophrenic.** `file-provider.ts` returns Effect errors. `config-layer.ts` calls `process.exit(1)`. `makeCliConfigLayer` catches everything and falls back silently. There is no consistent error propagation strategy.

### What attention-matters Gets Right

- One file, one `load()` function, one path through the code. No ambiguity about how config gets from disk to runtime.
- The `Option<T>` wire format and concrete resolved type are the minimum viable abstraction for "partial input, complete output."
- No duplication of defaults or schema keys.
- `generate_default_toml()` provides self-documentation without maintaining a separate default object.

### What mdcontext Gets Right

- The type-level completeness check for env var mapping is a genuine safety net.
- Supporting multiple config file formats (especially `.ts`) allows typed, code-complete config authoring.
- The ConfigService tag enables genuine DI for testing without environment pollution.

---

## 4. Recommendations

### For mdcontext: Collapse to Two Layers

The config system should have exactly two abstractions:

1. **Resolution**: Turn sources (file, env, CLI) into a `MdContextConfig` object. This is a function, not a service.
2. **Injection**: Make the resolved config available to the Effect runtime. This is a `Context.Tag` + `Layer`.

Concretely:

**A. Remove the ConfigProvider intermediary.** Instead of building a `ConfigProvider` (a `Map<string, string>`) and then parsing it through `Config` combinators, load the config file as a partial object, read env vars as a partial object, merge CLI flags as a partial object, and deep-merge them all with defaults. The `mergeWithDefaults` function already exists. Use it as the single resolution path.

**B. Eliminate `defaultConfig` as a separate declaration.** Generate it from the schema, or define the schema from it. One source of truth. If the `Config` combinators are retained for ConfigProvider compatibility, write a test that asserts `defaultConfig` matches `Effect.runSync(MdContextConfig.pipe(Effect.withConfigProvider(ConfigProvider.fromMap(new Map()))))`.

**C. Eliminate `CONFIG_SCHEMA_KEYS`.** If the ConfigProvider intermediary is removed (recommendation A), this mapping is unnecessary. Env var reading can iterate `process.env`, strip the prefix, and use a `flatCase -> camelCase` transform. The schema types provide compile-time safety.

**D. Consolidate the CLI config path.** `main.ts` and `config-layer.ts` should share one code path for config resolution. The `makeCliConfigLayer` function should be the single entry point.

**E. Pick one error strategy.** Either propagate Effect errors and let the CLI runner handle them, or validate eagerly and `process.exit`. Mixing both creates dead code paths and untestable error handling.

### For the Helioy Ecosystem

Both projects would benefit from a shared config philosophy:

```
1. Define a schema type (concrete, with defaults)
2. Define a wire type (all-optional version of the schema)
3. Load: file -> wire type -> merge with defaults -> schema type
4. Inject: pass as argument (Rust) or Context.Tag (Effect-TS)
```

This is what attention-matters already does. mdcontext should converge toward it, using Effect idioms where they add genuine value (the Context.Tag for DI, typed config file support) and dropping the machinery that exists only because Effect's ConfigProvider system was adopted wholesale when it was not needed.

The ConfigProvider abstraction makes sense for libraries that need to compose config from arbitrary sources at the framework level. mdcontext is an application. It knows exactly what its config sources are. The indirection through `ConfigProvider.fromMap` with string serialization/deserialization is pure overhead.

### Estimated Impact

Removing the ConfigProvider intermediary and consolidating defaults would reduce the config system from ~700 lines across 6 files to approximately ~300 lines across 3 files (schema, loading, service). The mental model goes from "three mechanisms" to "load then inject." Every new config field requires editing one file instead of three.
