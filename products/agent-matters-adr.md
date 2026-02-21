# runtime-matters ADR

Status: living draft  
Date: 2026-04-23

This file records product architecture decisions for `runtime-matters` as they
are made. Each record should stay short enough to be useful during product
design and implementation.

## ADR 000: product name is runtime-matters

Status: accepted

Decision:

The product name is `runtime-matters`.

Context:

The product is increasingly centered on runtime homes, runtime configuration,
runtime plugin installation, runtime source material, and generated runtime
assembly. `runtime-matters` describes the product boundary more precisely than
the previous `agent-matters` name.

Consequences:

- Product language should use `runtime-matters`.
- The rename affects CLI naming, npm package naming, repository naming, plugin
  names, docs, generated home paths, environment variables, and user facing
  prompts.

Reserved npm package names:

```text
runtime-matters@0.0.0
runtime-agents@0.0.0
runtime-catalog@0.0.0
runtime-plugins@0.0.0
```

## ADR 000A: catalog repository name is runtime-catalog

Status: accepted

Decision:

The curated catalog repository name is:

```text
runtime-catalog
```

The runtime managed plugin repository name is:

```text
runtime-plugins
```

Context:

The curated catalog repository contains source backed reusable material such as
profiles, capabilities, source skills, runtime specs, fixtures, and tests. The
`catalog` suffix describes that boundary better than `plugins`, `runtimes`, or
`sources`.

The runtime plugin repository contains Codex, Claude, and future runtime
managed plugins. It is the artifact installed through each runtime's own plugin
commands.

`runtime-catalog` contains curated sources for `runtime-matters`; it does not
copy the full `RUNTIME_MATTERS_HOME` layout.

Consequences:

- `runtime-catalog` is the catalog repository name.
- `runtime-plugins` is the runtime managed plugin repository name.
- `runtime-catalog` should be structured around curated sources, not around
  installed runtime plugin packages or generated runtime state.

## ADR 001: runtime-matters is agent operated

Status: accepted

Decision:

`runtime-matters` is a deterministic runtime compiler and local manager operated
primarily by an active AI agent. The human facing CLI should bootstrap,
validate, synchronize, and provide escape hatches. The product workflow should
live in `runtime-plugins` and source backed material from `runtime-catalog`.

Context:

The user should not need to learn a large command tree to create profiles,
import sources, compile runtime homes, or explain generated output.

Consequences:

- The core must expose deterministic operations with clear output.
- Agent skills own interpretation, planning, source discovery, and explanation.
- The CLI should stay small for normal users.

## ADR 002: use one RUNTIME_MATTERS_HOME

Status: accepted

Decision:

Use one root directory, `RUNTIME_MATTERS_HOME`, defaulting to
`~/.runtime-matters`. Do not introduce a separate `RUNTIME_MATTERS_STATE`.

Context:

Users may want to version control their runtime-matters home. A second state root
adds configuration surface and makes the product harder to explain.

Consequences:

- Authored, imported, and generated material live under one home.
- Internal directory layout must make versionable and generated material clear.
- Git support is handled by the home repository, `.gitignore`, and layout, not
  another env var.

## ADR 003: make RUNTIME_MATTERS_HOME version control friendly

Status: accepted

Decision:

`RUNTIME_MATTERS_HOME` should be safe to put under git when the user chooses.
Generated and machine local paths should be clearly named and ignored by
default.

Recommended shape:

```text
RUNTIME_MATTERS_HOME/
  runtime-matters.json
  profiles/
  capabilities/
  skills/
  instructions/
  hooks/
  mcp/
  runtime-settings/
  sources/
  generated/
  cache/
  logs/
  locks/
```

Default version control policy:

```text
commit:
  runtime-matters.json
  profiles/
  capabilities/
  skills/
  instructions/
  hooks/
  mcp/
  runtime-settings/
  sources/

ignore:
  generated/
  cache/
  logs/
  locks/
```

Context:

The home contains both authored intent and local operational state. Those need
different treatment without splitting them into separate roots.

Consequences:

- `init` should ask for `RUNTIME_MATTERS_HOME`, defaulting to
  `~/.runtime-matters`.
- `init` prepares the home for git by initializing a repository and writing a
  `.gitignore`.
- Generated runtime homes and indexes belong under `generated/`.

## ADR 004: sources use a flat namespace

Status: accepted

Decision:

Do not group `sources/` by source type in the filesystem. The source schema
encodes type, runtime, connector, locator, and provenance.

Example:

```text
sources/
  local-home-claude-default/
  local-home-codex-default/
  local-home-codex-runtime-matters/
  skills-sh/
  mcp-sh/
  github-garrytan-gstack/
```

Each source directory contains a manifest such as `source.json`.

Context:

Runtime homes, local paths, web catalogs, git repositories, and `runtime-catalog`
material are all sources. Grouping by type in the path duplicates schema and
makes later changes awkward.

Consequences:

- Source ids need a stable naming convention.
- Exact local paths and external locators belong in `source.json`.
- The source directory name is a stable id, not a complete description.

## ADR 005: local runtime homes are sources

Status: accepted

Decision:

Existing `.codex`, `.claude`, and project local runtime homes are represented
as sources.

Example source manifest:

```json
{
  "id": "local-home-codex-default",
  "kind": "local-runtime-home",
  "runtime": "codex",
  "locator": "/Users/alphab/.codex"
}
```

Context:

Existing runtime homes may contain valuable accumulated practice. `sync`
imports that material into `runtime-matters` rather than treating runtime homes
as disposable legacy config.

Consequences:

- `sync` should preserve and normalize material from existing runtime homes.
- The original path belongs in source metadata.
- Generated runtime homes remain under `generated/`, separate from imported
  local runtime sources.

## ADR 006: named external sources are not hardcoded in core

Status: accepted

Decision:

The core must not hardcode named external sources such as `skills.sh` or
`mcp.sh`.

Named sources are represented as source records plus source skills from
`runtime-catalog` or local source material.

Context:

Hardcoding named sources defeats the point of an agent operated source system.
Users and agents need to discover and add new sources without changing Rust
core code.

Consequences:

- `skills.sh` should be a curated source skill, not a Rust match arm.
- Adding `mcp.sh` means adding a source skill and source record.
- The core validates normalized bundles, writes catalog material, records
  provenance, updates indexes, and runs doctor checks.

## ADR 007: git repositories are imported through temporary clones

Status: accepted

Decision:

`runtime-catalog` and other git repositories should be cloned into a
temporary location for import, then discarded. They should not become long lived
checkouts inside `RUNTIME_MATTERS_HOME` by default.

Context:

Long lived nested git checkouts complicate version control, updates, forks, and
the mental model for `RUNTIME_MATTERS_HOME`.

Consequences:

- `sources/` stores source records, import metadata, provenance, and drift
  review snapshots when needed.
- Top level typed directories store normalized compileable material.
- `generated/` stores rebuildable output.
- Working forks are explicit contribution workspaces, not normal import state.

## ADR 008: runtime-catalog is source material

Status: accepted

Decision:

`runtime-catalog` is treated as source material. Its value is curated profiles,
capabilities, source skills, runtime specs, fixtures, tests, and contribution
patterns.

Context:

The product value is not only the runtime compiler. It is also a curated
ecosystem of agent skills and source skills that can improve through PRs.

Consequences:

- First run can register and resolve `runtime-catalog` material.
- The source record captures repository URL, revision, connector, and
  provenance.
- User discovered sources can become source skills and be proposed as PRs to
  `runtime-catalog`.

## ADR 009: init prepares RUNTIME_MATTERS_HOME for git by default

Status: accepted

Decision:

`npx runtime-matters init` should create a git ready `RUNTIME_MATTERS_HOME` by
default. It should write a `.gitignore` that keeps authored material visible and
keeps generated, cache, log, and lock files out of version control.

Context:

Version control is part of the value of `runtime-matters`. Users should be able
to review, share, branch, and roll back the authored state that defines their
agent runtime configuration.

Consequences:

- `init` should not ask whether to write `.gitignore`; it should do it.
- The generated `.gitignore` should be conservative and documented.
- Authored paths such as `runtime-matters.json`, `profiles/`, `skills/`,
  `instructions/`, `hooks/`, `mcp/`, `runtime-settings/`, and `sources/`
  should remain versionable by default.
- Generated paths such as `generated/`, `cache/`, `logs/`, and `locks/` should
  be ignored by default.

## ADR 010: init imports detected sources through selection

Status: accepted

Decision:

`init` should detect existing runtime homes and other obvious local sources,
then present them in a selectable interface. All detected sources should be
selected by default. The user can use spacebar selection to exclude sources
before import.

Context:

Auto import is the right default because existing runtime homes contain the
user's accumulated agent practice. At the same time, users need a simple way to
exclude stale, private, experimental, or unwanted sources during bootstrap.

Consequences:

- `init` needs a minimal interactive terminal UI.
- `ratatui` is an appropriate dependency for the selection surface.
- The source selection screen should show source id, type, locator, runtime
  when relevant, and import status.
- Non interactive mode should still exist for automation and should default to
  importing all detected sources unless configured otherwise.

## ADR 011: init selects supported runtimes through the same UI model

Status: accepted

Decision:

`init` should display all supported runtimes in the same minimal interactive
terminal UI. Detected runtimes should be selected by default. Unsupported or
not detected runtimes should remain visible with status so the user understands
what `runtime-matters` can manage.

Context:

The user should not need to know which runtimes `runtime-matters` supports before
running setup. Runtime selection and source selection should feel like one
bootstrap flow.

Consequences:

- The runtime selection screen should show runtime id, display name, detected
  status, path or config root when known, and support status.
- Detected runtimes are selected by default.
- Users can toggle runtime selection with the same spacebar interaction used
  for source selection.
- Non interactive mode should default to all detected supported runtimes.

## ADR 012: source material snapshots are transient by default

Status: accepted

Decision:

`sources/<source-id>/` should store source metadata and provenance, not copied
source payloads by default. Fetched or cloned source material is a transient
artifact used during import and discarded after normalized catalog material is
written.

Context:

The durable value is the source record and the normalized catalog output. Raw
source checkouts and fetched payloads add storage noise and version control
churn unless the product has a specific preservation need.

Consequences:

- Git repositories are cloned into temporary locations for import.
- Web or API source payloads are fetched into temporary locations for import.
- `sources/<source-id>/source.json` records locator, connector, revision or
  content hash when available, provenance, and import history.
- If future workflows require preserving raw source payloads, that should be an
  explicit policy or command, not the default.

## ADR 013: curated material is imported into typed directories

Status: accepted

Decision:

Curated source skills, profiles, and capabilities from `runtime-catalog` are
imported into top level typed directories when selected. The imported entity
gets a local id that includes the source namespace when needed to avoid
collisions.

Context:

Once material is imported, it is local durable material and can be edited in
place. Provenance and sync metadata keep track of where it came from.

Consequences:

- Top level typed directories such as `skills/`, `profiles/`, and `mcp/` are
  the local runtime material.
- `sources/<source-id>/` records source identity, provenance, import metadata,
  and sync state.
- Local ids should be source namespaced when imported entities may collide.
- Example: `skills/anthropics-skills-frontend-design/`.

## ADR 014: activation never overwrites existing runtime homes

Status: accepted

Decision:

`runtime-matters` must never overwrite the user's existing global `.codex`,
`.claude`, or other runtime home during activation. Generated runtime homes are
created under `RUNTIME_MATTERS_HOME/generated/` and activated by pointing the
runtime at that generated home for the selected workspace or launch context.

Context:

Existing runtime homes are user systems. They may contain valuable manual
configuration and should be treated as source material to import, not as
targets to overwrite.

Consequences:

- Activation writes only managed generated paths and runtime pointers under
  `RUNTIME_MATTERS_HOME`.
- Launch instructions should use runtime supported environment variables,
  flags, or workspace scoped configuration rather than replacing global homes.
- `sync` can read existing runtime homes, but activation cannot mutate them.
- Any command that would touch an existing user runtime home must be blocked
  unless it is an explicit import or read only inspection.

## ADR 015: init installs the operator skill into the current runtime home

Status: superseded by ADR 016

Decision:

`init` must install the `runtime-matters` operator skill into the user's current
runtime home for each selected runtime. This is the bootstrap step that lets the
active agent learn how to operate `runtime-matters`.

Runtime home discovery should follow the runtime adapter's configured rules.
For current Codex and Claude support, discovery should prefer explicit runtime
environment variables such as `CODEX_HOME` and the Claude project or config
home. If those are not set, discovery should use `XDG_CONFIG_HOME` where the
runtime supports it, then fall back to the runtime's conventional default under
the user's home directory.

Context:

Generated runtime homes are used after `runtime-matters` is operating, but the
first install has to reach the user's current runtime so the agent can load the
operator skill. Without this step, the user would have to manually teach Codex
or Claude how to use `runtime-matters`.

Consequences:

- This is an explicit bootstrap exception to the activation rule.
- The write must be additive and scoped to the operator skill install.
- `init` should show the target runtime home before writing.
- `init` should never replace the user's existing runtime home or generated
  runtime config wholesale.
- Each runtime adapter owns its discovery rules so adding a new CLI runtime is
  a data driven adapter task rather than a one off hardcoded path change.

## ADR 016: install runtime plugins through runtime managed plugin commands

Status: accepted

Decision:

`runtime-matters` does not manage Codex, Claude, or future runtime homes directly
during bootstrap. The relationship is inverted: each runtime remains
responsible for its own plugin system, and `runtime-matters init` uses that
runtime's managed plugin commands to install `runtime-plugins`.

Context:

Writing directly into runtime homes makes `runtime-matters` responsible for
runtime internals and conflicts with the boundary that user runtime homes are
not managed by `runtime-matters`. Codex and Claude should own their plugin
installation paths and semantics.

Consequences:

- `init` should discover selected runtimes and call their supported plugin
  install commands.
- The installed artifact is `runtime-plugins`, not an ad hoc copied skill
  directory.
- Runtime adapters own plugin command discovery and invocation.
- Adding a new CLI runtime should mean adding an adapter that knows how to
  detect the runtime and install plugins through that runtime's own mechanism.
- Runtime homes are not registered as managed sources merely because plugins
  were installed. Source registration and sync remain separate user selected
  operations.

## ADR 017: init performs initial sync selection and sync remains repeatable

Status: accepted

Decision:

`init` should include an initial source discovery and selection step after
runtime plugin installation. Runtime homes and other obvious local sources are
shown as selectable sources during bootstrap.

`runtime-matters sync` should also remain a repeatable command for later source
discovery, import, and reconciliation.

Context:

First run should get the user to a useful managed home immediately. Later, the
user may change runtime homes, add new local sources, or want to reconcile
drift. The same source selection model should support both moments.

Consequences:

- `init` performs plugin installation first, then offers initial source
  selection and sync.
- `sync` reuses the same source discovery and selection UI where appropriate.
- Runtime homes are registered as sources only when selected during initial
  sync or later sync.
- Non interactive `init` defaults to selecting all detected supported runtimes
  and all detected sources unless flags or config say otherwise.

## ADR 018: init runs doctor before and after bootstrap

Status: accepted

Decision:

`init` should run doctor twice with different scopes.

Before mutation, `init` runs a preflight doctor to check whether bootstrap can
proceed. After runtime plugin installation and initial sync, `init` runs a full
doctor to verify the completed setup.

Context:

Preflight catches blockers before writes happen. Full doctor verifies the
system the user will actually use after bootstrap.

Consequences:

- Preflight doctor should check binary health, `RUNTIME_MATTERS_HOME`
  accessibility, runtime detection, runtime plugin command availability, git
  availability where needed, and basic permissions.
- Full doctor should check home layout, runtime plugin installation, selected
  source records, indexes, catalog validity, generated paths, warnings, and
  blockers.
- `init` should stop before mutation on preflight blockers.
- `init` should finish with a concise health result and next prompt after full
  doctor passes or reports non blocking warnings.

## ADR 019: init hands off through human readable get-started

Status: accepted

Decision:

After successful bootstrap, `init` should display `runtime-matters get-started`
as the next step. The get started surface should provide the short prompts that
trigger installed `runtime-matters` skills in Codex, Claude, or other selected
runtimes.

`get-started` is a human readable onboarding surface. It should not provide a
JSON output contract.

Context:

The post install handoff should be memorable and repeatable. Embedding a long
prompt list directly in `init` makes the output noisy and harder to revisit.

`get-started` exists to hand the user from installation into agent operation. It
is not a machine integration point.

Consequences:

- `runtime-matters get-started` becomes the reusable onboarding surface.
- `init` should print a concise success summary and point to
  `runtime-matters get-started`.
- The get started output can show short prompts such as setting up a repo,
  creating a profile, syncing sources, discovering a source, and explaining the
  active runtime.
- Runtime specific prompt wording can be added by runtime adapters when
  needed.
- Future structured integrations should use dedicated command surfaces rather
  than overloading `get-started`.

## ADR 020: runtime support is scoped by runtime and separated by concern

Status: accepted

Decision:

Adding support for a new CLI runtime should be a simple path. Runtime support
should be grouped under the runtime id while separating concerns into small
declarative specs.

Example shape:

```text
runtimes/
  codex/
    runtime.json
    detect.json
    plugin.json
    launch.json
    mappings.json

  claude/
    runtime.json
    detect.json
    plugin.json
    launch.json
    mappings.json
```

Context:

A single monolithic adapter makes each runtime harder to understand. Global
registries for each concern make new runtime support scattered. Runtime scoped
files keep ownership local while letting detection, plugin install, launch, and
mapping rules evolve independently.

Consequences:

- Adding a runtime should usually mean adding a new `runtimes/<runtime-id>/`
  directory.
- Detection, plugin install, launch behavior, skill exposure, and vocabulary
  mappings should be separate specs.
- The declarative model should be tried first.
- Runtime specific code should only be added when the runtime needs behavior
  the specs cannot express.

## ADR 021: runtime integration installs a skill library

Status: accepted

Decision:

Runtime integration installs `runtime-plugins`, a curated skill library,
not a single operator skill.

Example shape:

```text
runtime-plugins/
  skills/
    get-started/
    setup-repo/
    sync-sources/
    create-profile/
    discover-source/
    explain-runtime/
    review-plan/
    validate-home/
```

Context:

The product workflow is a lifecycle, not one monolithic command center. A
library of narrow skills is closer to how agents should operate and closer to
the `gstack` precedent.

Consequences:

- Product language should say skill library or plugins, not singular operator
  skill.
- Source skills live in `runtime-catalog`; `runtime-plugins` can use them
  through normal runtime resolution.
- `get-started` should point users at short prompts that trigger specific
  skills.
- The plugin library becomes the primary agent facing product surface.

## ADR 022: profile authoring is skill library driven in MVP

Status: accepted

Decision:

Profile authoring should be driven by the skill library in MVP. The
`create-profile` skill drafts and writes local profile material under
`profiles/` after user review. The core validates, indexes, compiles, and
diagnoses the result.

Context:

Profile creation is intent work. The active agent is better suited to inspect
the repository, choose source backed material, draft the profile, and explain
the decision. The core should guard deterministic boundaries rather than own a
large profile authoring command before the workflow proves it needs one.

Consequences:

- Do not add `profile plan/apply` as an MVP requirement.
- Keep profile manifests as authored files under `profiles/`.
- Provide strong validation, doctor checks, indexing, compile, and explain
  behavior for profiles.
- Add structured profile authoring commands later only if the skill driven
  workflow proves too loose.

## ADR 023: runtime-plugins is also source backed catalog material

Status: accepted

Decision:

`runtime-plugins` has two roles.

First, it is the runtime managed plugin package installed into Codex, Claude,
and future runtimes through each runtime's own plugin command.

Second, it is represented as source backed material in `runtime-catalog`. This
allows generated `runtime-matters` runtimes to include the `runtime-plugins`
capability through normal runtime resolution.

Context:

Bootstrap plugin installation and generated runtime composition are different
flows. Bootstrap installs `runtime-plugins` into the user's active runtime so
the agent can operate the system. Generated runtimes should be able to include
the same plugin capability without special casing the package in core.

Consequences:

- `runtime-catalog` should contain a source record for `runtime-plugins`.
- `runtime-catalog` should expose a capability that lets profiles include
  `runtime-plugins` in generated runtime homes.
- `runtime-plugins` should not be hardcoded in the core as a privileged source
  or capability.
- Runtime adapters decide how the `runtime-plugins` capability is rendered for
  each runtime.

## ADR 024: no overlays, edit imported material in place

Status: accepted

Decision:

Do not introduce an overlay abstraction. Imported material is copied into the
appropriate top level typed directory and edited in place.

Example:

```text
~/.runtime-matters/
  sources/
    anthropics-skills/
      source.json

  skills/
    anthropics-skills-frontend-design/
      skill.json
      SKILL.md
```

Context:

Overlays add a merge and resolution model before the product needs one. The
simpler model is that imported material becomes local durable material with
provenance. Users and agents can edit the files directly.

Consequences:

- There is no top level `overlays/` directory.
- Imported entities should use source namespaced local ids when needed.
- Direct edits make the imported entity locally dirty relative to its last
  import baseline.
- Sync owns dirty detection and update safety.
- If users want a separate derivative, the agent can copy an imported entity to
  a new local id.

## ADR 025: sync stores metadata and materializes drift snapshots on demand

Status: accepted

Decision:

`sources/<source-id>/` stores source records, import metadata, provenance, and
hashes by default. It does not store full source payloads or every imported
baseline by default.

When sync detects local dirtiness or upstream drift, it can materialize a drift
snapshot with only the files needed for review.

Context:

The product needs safe sync, `--show-diff`, and `--force` without turning
`sources/` into a full vendor tree. Most imported entities will not drift, so
storing every baseline up front is unnecessary.

Consequences:

- Sync compares baseline hashes, current local hashes, and current upstream
  hashes.
- If local material is dirty, sync skips it and prints a clear message.
- `--show-diff` shows review information from a drift snapshot when available.
- Drift snapshots may include baseline, upstream, and local copies for the
  affected entity only.
- Source connectors may reconstruct baseline content from a revision when the
  source supports it.
- `--force` can overwrite a dirty local entity with current upstream material
  and update import metadata.

## ADR 026: source ids include source kind

Status: accepted

Decision:

Source ids should include the source kind for collision resistance and
readability.

Examples:

```text
github-anthropics-skills
github-garrytan-gstack
local-home-codex-default
local-home-claude-default
web-skills-sh
web-mcp-sh
```

Imported entity ids should include the source id when needed to avoid
collisions.

Example:

```text
skills/github-anthropics-skills-frontend-design/
```

Context:

Different source kinds can expose similar names. Including kind in the source
id makes provenance clearer and reduces id collisions without requiring users
to inspect metadata.

Consequences:

- Source id generation should be deterministic.
- Exact locators remain in `sources/<source-id>/source.json`.
- Agents should use the generated source id in imported entity ids when there
  is collision risk or when provenance should remain visible in the path.

## ADR 027: source research detects native tooling

Status: accepted

Decision:

Source research should look for source native tooling, including `npx`
commands, CLIs, JSON output modes, list commands, search commands, and update
commands.

Source skills may use native tooling in controlled temporary workspaces for
search, inspection, fetch, and normalization. Native tooling must not mutate the
user's Codex, Claude, or other runtime homes during `runtime-matters` import.

Context:

Large catalogs such as `https://skills.sh/` are a different class of source.
The source can expose tens of thousands of skills and may provide a native CLI,
for example `npx skills`, with search, list, add, update, and JSON list
capabilities. Importing or indexing the full catalog locally is the wrong
default.

Consequences:

- Large remote catalogs should be searched remotely and imported selectively.
- `sources/<source-id>/source.json` should record native tooling when detected.
- Source skills can stage native tool operations in temp directories or fake
  runtime homes to prevent user runtime mutation.
- If source native tooling only supports install style operations, the source
  skill must redirect those operations into controlled temp locations before
  extracting selected entities.
- Imported entities are copied into top level typed directories such as
  `skills/` with source namespaced local ids.
- Sync uses source metadata, import hashes, and source native update mechanisms
  when available.

## ADR 028: manifests use JSON Schema and agents commit every change

Status: accepted

Decision:

`runtime-matters` metadata and manifests should use JSON files validated by JSON
Schema. Users interact with runtime material through agents and CLI commands,
not by hand editing manifest files.

`RUNTIME_MATTERS_HOME` is a git managed workspace. Agents should commit every
successful change they make to the home.

Context:

JSON gives agents and validators a strict machine friendly contract. Git gives
the home time travel, auditability, and a clear integrity boundary.

Consequences:

- Top level config should be `runtime-matters.json`.
- Entity manifests should use typed JSON files, for example `skill.json`,
  `profile.json`, `mcp.json`, and `source.json`.
- JSON Schema is the contract for home config, sources, imports, skills, MCP
  servers, profiles, runtime targets, generated runtime manifests, and drift
  records.
- `init` should initialize git in `RUNTIME_MATTERS_HOME` if needed.
- Agent workflows should check `git status --short` before mutation.
- Unexpected dirty git state should be treated as human or external tampering
  and requires user confirmation before proceeding.
- Agent initiated edits should update import metadata when an imported entity
  becomes locally modified.
- After validation succeeds, the agent commits the change so the user can
  review history and roll back.

## ADR 029: entity manifests use separate typed schemas

Status: accepted

Decision:

Use separate typed JSON schemas and manifest files for each entity kind.

Examples:

```text
skills/<id>/skill.json
mcp/<id>/mcp.json
profiles/<id>/profile.json
instructions/<id>/instruction.json
hooks/<id>/hook.json
runtime-settings/<id>/runtime-setting.json
sources/<id>/source.json
```

Common fields can be shared through schema definitions, but the primary storage
shape should not be one generic `capability.json` with a large optional field
set.

Context:

Skills, MCP servers, profiles, instructions, hooks, runtime settings, and
sources have different validation requirements and different agent workflows.
Typed schemas produce clearer validation, better command output, and better
agent behavior.

Consequences:

- Inventory commands should be typed first: `skills list`, `mcp list`,
  `profiles list`, `sources list`, and `runtimes list`.
- `capabilities list` can exist as a discovery and help surface that explains
  available entity types and shows examples.
- Schema docs can be generated per entity type.
- Validation errors can be specific to the entity kind instead of coming from a
  broad generic capability schema.
