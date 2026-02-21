# agent-matters Runtime Profiles

## Purpose

`agent-matters` is a local first profile system for coding agents.

It separates agent capability inventory from runtime specific config directories. Today, Claude and Codex bind skills, MCP servers, hooks, agent definitions, and instructions from static `.claude` or `.codex` directories. That makes profiles hard to compose, audit, trim, reuse, and launch precisely.

`agent-matters` makes `.claude` and `.codex` generated runtime homes. The source of truth is a curated catalog of capabilities, profile manifests, runtime defaults, source imports, and overlays.

## Core Model

### Vocabulary

`Capability`
: Any typed unit that can change agent behavior.

Examples:

- `skill:playwright`
- `mcp:linear`
- `hook:session-logger`
- `instruction:helioy-core`
- `agent:github-researcher`
- `runtime-setting:codex-defaults`

`Profile`
: A named composition of capabilities, ordered instructions, scope constraints, and runtime support.

Examples:

- `github-researcher`
- `linear-triage`
- `rust-debugger`

`Runtime adapter`
: A compiler target for one agent runtime, initially `codex` and `claude`.

`Build`
: Immutable fingerprinted runtime home generated from resolved profile content.

`Runtime pointer`
: Stable path for launching a profile without remembering a fingerprint.

`JIT profile`
: Temporary profile created by the resolver for a specific task, workspace, and runtime. MVP JIT is local only and uses approved catalog capabilities.

### Product Boundary

`agent-matters` owns:

- capability catalog
- profile manifests
- source adapters
- overlays
- profile resolution
- dependency validation
- runtime compilation
- generated builds
- stable runtime pointers
- manual launch instructions

`agent-matters` does not own in MVP:

- Manicure transport interception
- provider payload curation
- direct process ownership
- GUI editing
- importing existing `.claude` or `.codex` installations

Manicure, warroom, and future tools consume `agent-matters` profiles. `agent-matters` does not depend on those tools.

## Source Of Truth

Files are canonical. TOML manifests define contracts. A generated JSON index provides fast exact lookup.

Authoring model:

- files remain editable by hand
- CLI is the canonical safe tooling
- `doctor` validates and explains broken state
- a future GUI may be stateless over the same files and CLI contracts

Manifest format:

- TOML
- one `manifest.toml` per capability or profile directory

Generated state lives outside the catalog repo under `~/.agent-matters`.

## Repository Shape

Authorable repo:

```text
agent-matters/
  catalog/
    skills/
    mcp/
    hooks/
    instructions/
    agents/
    runtime-settings/

  profiles/

  vendor/
    skills.sh/

  overlays/
    skills/
    mcp/
    hooks/
    instructions/
    agents/
    runtime-settings/

  defaults/
    runtimes.toml
    markers.toml

  crates/
    agent-matters-core/
    agent-matters-capabilities/
    agent-matters-cli/
```

User generated state:

```text
~/.agent-matters/
  builds/
    codex/
      github-researcher/
        3f8a91c2/
          home/

    claude/
      github-researcher/
        a91bb002/
          home/

  runtimes/
    github-researcher/
      codex -> ../../builds/codex/github-researcher/3f8a91c2/home
      claude -> ../../builds/claude/github-researcher/a91bb002/home

  indexes/
```

The stable runtime path is directly usable as the runtime home:

```bash
CODEX_HOME=~/.agent-matters/runtimes/github-researcher/codex codex -C /path/to/repo
CLAUDE_CONFIG_DIR=~/.agent-matters/runtimes/github-researcher/claude claude /path/to/repo
```

## Rust Crate Boundaries

Follow the established `context-matters` pattern, especially `crates/cm-capabilities`.

### `agent-matters-core`

Pure domain and shared contracts.

Owns:

- `CapabilityId`
- `ProfileId`
- `RuntimeId`
- `CapabilityKind`
- `ProfileKind`
- provenance
- requirements
- scope constraints
- diagnostics
- manifest structs
- pure validation rules

Does not own:

- CLI argument parsing
- human rendering
- filesystem mutation
- runtime process spawning

### `agent-matters-capabilities`

Application use case boundary.

This crate is named after the Helioy pattern. It is separate from the domain entity `Capability`.

Owns:

- request and result types
- profile list, show, compile, and use workflows
- capability list, show, and overlay diff workflows
- source search and import workflows
- doctor workflow
- JIT resolver workflow
- projections for human and JSON output
- orchestration across catalog, profiles, sources, compiler, and runtime adapters

This crate allows future clients to reuse behavior without duplicating logic:

- CLI
- Manicure
- warroom
- desktop UI
- future MCP or HTTP surfaces if needed

### `agent-matters-cli`

Thin terminal adapter.

Owns:

- clap definitions
- config loading entrypoint
- command dispatch
- stdout and stderr rendering
- exit code mapping
- shell completions
- generated help

The CLI must not contain domain rules.

## Domain Modules

Suggested module map inside `agent-matters-core`:

```text
domain/
  capability.rs
  profile.rs
  runtime.rs
  requirement.rs
  provenance.rs
  scope.rs
  diagnostic.rs

manifest/
  capability.rs
  profile.rs
  defaults.rs

catalog/
  paths.rs
  index.rs
  overlay.rs
  vendor.rs

runtime/
  adapter.rs
  build.rs
  fingerprint.rs
```

Suggested module map inside `agent-matters-capabilities`:

```text
profiles/
  list.rs
  show.rs
  compile.rs
  use_profile.rs

capabilities/
  list.rs
  show.rs
  diff.rs

sources/
  search.rs
  import.rs
  skills_sh.rs
  mcp_registry_spec.rs

doctor.rs
jit.rs
projection/
  text.rs
  json.rs
```

## Profile Schema

Minimal profile manifest:

```toml
id = "github-researcher"
kind = "persona"
summary = "Focused research agent for inspecting GitHub repositories."

capabilities = [
  "skill:github",
  "mcp:context-matters",
]

instructions = [
  "instruction:helioy-core",
  "agent:github-researcher",
]

[scope]
paths = ["~/Dev/LLM/DEV/helioy"]
github_repos = ["srobinson/helioy"]
enforcement = "warn" # none | warn | fail

[runtimes]
default = "codex"

[runtimes.codex]
enabled = true
model = "gpt-5.4"

[runtimes.claude]
enabled = true
model = "claude-sonnet-4.5"

[instructions_output]
markers = "html-comments" # html-comments | top-notice | none
```

Rules:

- Profile IDs are simple public IDs.
- `kind` is metadata in MVP.
- MVP profile kinds are `persona`, `task`, and `launcher`.
- `capabilities` lists included capabilities.
- `instructions` lists ordered instruction fragments and agent definitions for compiled `AGENTS.md`.
- `instructions` entries are included automatically and do not need to be repeated in `capabilities`.
- Runtime support is explicit through `[runtimes.<name>] enabled = true`.
- Runtime default resolves from profile first, user config second.
- If runtime remains ambiguous, `profiles use` fails with available options.

## Capability Schema

Minimal capability manifest:

```toml
id = "mcp:linear"
kind = "mcp"
summary = "Linear MCP server for issue and project management."

[files]
manifest = "server.toml"

[runtimes.codex]
supported = true

[runtimes.claude]
supported = true

[requires]
env = ["LINEAR_API_KEY"]
capabilities = []
```

Imported or derived capabilities also include provenance:

```toml
[origin]
type = "external"
source = "skills.sh"
locator = "playwright"
version = "1.4.2"
```

Rules:

- Capability IDs use kind prefixed simple IDs.
- Provenance is required for imported or derived capabilities.
- Capability runtime compatibility uses runtime table maps.
- Requirements in MVP include required capabilities and required environment variables.
- Dependencies are validate only at compile time.
- Authoring tooling may suggest adding missing dependencies.
- Final profile manifests must explicitly include every required capability.

## Overlays And External Sources

External and user authored content are first class distinctions.

External import model:

```text
external source schema
  -> source adapter
  -> normalized agent-matters capability schema
```

MVP source adapter:

- `skills.sh` through `npx skills find`

Designed next source:

- MCP Registry at `https://registry.modelcontextprotocol.io/`

Import storage:

- raw upstream records are preserved under `vendor`
- normalized internal manifests are created for catalog use
- local modifications are full copy overlays
- diff tooling compares overlay against vendor source

MVP overlay model:

- full modified copies
- no structured patch language
- no profile level include filters

Profile curation:

- whole capability by default
- variants are separate capabilities
- no profile level trimming language in MVP

## Runtime Defaults

Runtime config precedence, lowest to highest:

1. runtime adapter defaults
2. repo defaults
3. user defaults from `~/.agent-matters/config.toml`
4. included `runtime-setting` capabilities
5. profile runtime table overrides

Defaults should handle most profiles. Profiles should usually declare enabled runtimes and only override unusual settings.

`doctor` and `profiles show` should expose fully resolved runtime config so defaults remain visible.

## Runtime Compilation

Compilation input:

- profile manifest
- included capability manifests
- included files
- ordered instruction fragments
- relevant defaults
- source overlays
- runtime adapter version
- policies that affect output

Fingerprint includes resolved content and adapter versions.

Fingerprint excludes:

- credential file contents
- machine specific auth symlink targets
- current env var values

Generated homes:

- Codex home is usable through `CODEX_HOME`
- Claude home is usable through `CLAUDE_CONFIG_DIR`
- credential files are symlinked by adapter allowlist
- auth links do not affect the content fingerprint

Adapter credential allowlist:

- Codex starts with `auth.json`
- Claude starts with `.credentials.json`

Adapter allowlists are validated by `doctor`.

## CLI

Canonical binary:

```bash
agent-matters
```

Optional local alias:

```bash
alias agent=agent-matters
```

Do not rely on `agent` in public docs or machine contracts.

MVP command groups:

```text
profiles
capabilities
sources
doctor
```

Command style is noun first:

```bash
agent-matters profiles list
agent-matters profiles show github-researcher
agent-matters profiles compile github-researcher --runtime codex
agent-matters profiles use github-researcher /path/to/repo --runtime codex

agent-matters capabilities list
agent-matters capabilities show skill:playwright
agent-matters capabilities diff skill:playwright

agent-matters sources search skills.sh playwright
agent-matters sources import skills.sh:playwright

agent-matters doctor
```

Output:

- human output by default
- `--json` for machine output
- predictable exit codes
- generated help and completions following `context-matters`

`profiles compile`:

- validates profile structure
- warns on missing required env vars
- creates or reuses fingerprinted build
- updates stable runtime pointer
- prints build path, runtime pointer, fingerprint, warnings

`profiles use`:

- accepts optional positional path
- defaults path to current working directory
- resolves runtime from flag, profile default, then user default
- fails if runtime remains ambiguous
- validates scope
- validates required env vars
- compiles or reuses generated home
- prints manual launch instructions
- does not spawn the runtime in MVP

Example:

```bash
agent-matters profiles use github-researcher ~/Dev/LLM/DEV/helioy --runtime codex
```

Output should include:

```text
Profile: github-researcher
Runtime: codex
Fingerprint: 3f8a91c2
Runtime home: ~/.agent-matters/runtimes/github-researcher/codex

Manual launch:
CODEX_HOME=~/.agent-matters/runtimes/github-researcher/codex codex -C ~/Dev/LLM/DEV/helioy
```

## JIT Profiles

MVP JIT:

- created through a resolver command
- input is task text, workspace path, and runtime
- uses approved local capabilities only
- no external search during JIT
- no import during JIT
- outputs session cache artifacts
- promotion to authored profile is explicit future work

Ambiguous or low confidence resolver output:

- returns candidate profiles and reasons
- does not silently choose

## Doctor

MVP `doctor` validates:

- TOML syntax
- required fields
- duplicate IDs
- missing files
- broken references
- runtime compatibility
- dependency requirements
- required env var presence
- overlay target existence
- vendor record presence for imported capabilities
- generated JSON index freshness
- runtime adapter auth symlink allowlists

Generated cache validation can be added after compile behavior is proven.

## Coding Standards

Standards from day one:

- single responsibility per module
- target file size around 250 lines
- hard file size ceiling around 500 lines
- domain code is pure where practical
- filesystem mutation lives in explicit writer modules
- CLI presentation contains no domain logic
- runtime adapters do not parse profile TOML directly
- source adapters transform external records into internal schema
- use request and result structs for every public use case
- colocate unit tests with implementation
- use integration tests for CLI and compiler workflows
- use fixtures for manifests, imports, overlays, and generated homes
- prefer test first for rules, regressions, and compiler behavior

## MVP Workstreams

Use this as the Linear three tier structure:

Tier 1:

- Linear project: `agent-matters`

Tier 2 parent issues:

- Foundation and CLI shell
- Catalog, schemas, overlays, and index
- Profile resolution and validation
- Runtime compiler and generated homes
- Codex and Claude adapters
- Sources and `skills.sh` import
- Doctor and diagnostics
- JIT local resolver
- Future backlog

Tier 3 child issues:

- small TDD implementation tasks under each parent
- each child should map to one module or one externally observable behavior

## Future Work

Important features outside MVP:

- import existing `.claude` and `.codex` installations
- inspect installed plugins and convert them into catalog capabilities
- MCP Registry adapter implementation
- process owning launch command
- optional `profiles browse` interactive picker
- stateless Electron GUI over the same files and CLI contracts
- profile deduplication and inheritance
- profile promotion workflow for JIT outputs
- capability variants authoring helper
- generated cache validation and rollback UX

## Current Decisions

- Repo name is `agent-matters`.
- Canonical CLI binary is `agent-matters`.
- Optional local alias may be `agent`.
- Implementation language is Rust.
- Follow `context-matters` crate and CLI patterns.
- Create `agent-matters-capabilities` as the use case crate.
- TOML manifests are canonical contracts.
- Generated JSON index is derived state.
- Runtime homes are generated artifacts.
- Stable launch paths live under `~/.agent-matters/runtimes`.
- Immutable builds live under `~/.agent-matters/builds`.
- MVP does not own runtime process spawning.
- MVP provides manual and machine readable launch instructions.
- Codex uses `CODEX_HOME`.
- Claude uses `CLAUDE_CONFIG_DIR`.
- Manicure discovers and consumes `agent-matters`; `agent-matters` does not depend on Manicure.
