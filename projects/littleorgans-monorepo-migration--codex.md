---
title: littleorgans monorepo migration: codex independent plan
type: project-plan
tags: [littleorgans, monorepo, migration, moon, brainstorm, codex]
summary: Collapse identity, runtime, session, and the empty schedule placeholder into a private Moon driven Rust first monorepo named littleorgans, with one Cargo workspace, one physical lilo binary, one lilod daemon mode, one ~/.lilo data root, one v0.8.0 version line for all artifacts, and generated public MIT mirrors for each current source repo.
status: draft
source: codex
confidence: medium
created: 2026-05-25
---

# littleorgans monorepo migration plan

This plan covers the narrower current migration: four Rust subdirectories under `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/` moving into one new monorepo at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans/`. It deliberately reserves the future TypeScript, Electron, web, and Python shape from the product direction docs without migrating those surfaces now.

The load bearing recommendation is simple: create a clean private source repo, keep Cargo as the Rust package authority, let Moon orchestrate tasks across Rust, TypeScript, and Python, cut a single physical binary named `lilo`, and convert the existing public repos into generated mirrors after the monorepo becomes source of truth.

## 1. Target directory layout

Recommended repository name: `littleorgans/littleorgans`. The local path already implies this name, it matches the product direction, and the GitHub shape `github.com/littleorgans/littleorgans` is clear: org equals public ecosystem, repo equals private integrated source.

Concrete target tree:

```text
/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans/
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── release.yml
│       └── mirror-release.yml
├── .moon/
│   ├── workspace.yml
│   ├── toolchains.yml
│   └── tasks/
│       ├── rust.yml
│       ├── typescript.yml
│       └── python.yml
├── apps/
│   ├── desktop/                  # reserved for Electron shell
│   ├── server/                   # reserved for Effect server backbone
│   └── web/                      # reserved for React renderer
├── crates/
│   ├── lilo/                     # only user installed Rust binary package
│   │   └── src/
│   │       ├── main.rs           # thin shell, version and command dispatch
│   │       ├── cli.rs            # top level clap enum
│   │       └── hidden.rs         # shim and daemon internals, not public help
│   ├── lilo-common/              # shared plumbing, version, logging, errors
│   ├── lilo-paths/               # ~/.lilo and endpoint resolution
│   ├── lilo-types/               # cross substrate base types and ids
│   ├── lilo-client/              # public client for lilod after daemon merge
│   ├── lilo-rm-core/             # published, moved from runtime rtm-core
│   ├── lilo-rm-client/           # published, moved from runtime rtm-client
│   ├── lilo-im-core/             # published, moved from identity im-core
│   ├── lilo-im-store/            # published, moved from identity im-store
│   └── lilo-im-stub/             # published, moved from identity im-stub
├── internal/
│   ├── runtime/
│   │   ├── app/                  # current rtm-cli command implementation as library
│   │   ├── daemon/               # current rtm-daemon, refactored into RuntimeService
│   │   ├── launchers/            # claude and codex launch specs
│   │   ├── paths-compat-tests/   # temporary migration tests only, no shipped code
│   │   ├── platform/             # tmux, process, signal, watcher support
│   │   └── store/                # runtime lifecycle store
│   ├── session/
│   │   ├── app/                  # current sm-cli command implementation as library
│   │   ├── daemon/               # current sm-daemon, refactored into SessionService
│   │   ├── driver/               # runtime delegation, in process first, socket client for tests
│   │   └── store/                # session, namespace, mail persistence
│   ├── identity/
│   │   └── service/              # v1 authorizer composition over im crates
│   └── schedule/
│       └── README.md             # reserved, no Rust crate until a model exists
├── packages/
│   ├── contracts/                # reserved npm package, Effect Schema contracts
│   ├── shared/                   # reserved npm package, stateless utilities
│   ├── client-runtime/           # reserved npm package, renderer state primitives
│   └── design/                   # reserved npm package, tokens and UI primitives
├── python/
│   └── lilo-tools/               # reserved uv project for tooling that earns Python
├── tests/
│   ├── integration/              # in process lilod, runtime, session, identity scenarios
│   └── e2e/                      # assert_cmd real binary smoke tests
├── tools/
│   ├── xtask/                    # Rust task binary for codegen and release checks
│   ├── mirror-publish/           # generated mirror staging and Cargo rewrite tool
│   └── schemas/                  # generated MCP, CLI, and mirror metadata outputs
├── docs/
│   ├── architecture/
│   │   ├── runtime.md
│   │   ├── session.md
│   │   ├── identity.md
│   │   └── daemon-composition.md
│   ├── reference/
│   │   ├── cli.md                # generated from one command registry
│   │   ├── mcp.md                # generated from one tool registry
│   │   └── data-layout.md
│   ├── mirrors/
│   │   ├── identity-matters.md
│   │   ├── runtime-matters.md
│   │   └── session-matters.md
│   └── provenance/
│       └── imported-repos.md     # source SHAs, tags, and migration date
├── Cargo.toml
├── Cargo.lock
├── rust-toolchain.toml
├── justfile
├── package.json                  # reserved pnpm workspace root
├── pnpm-workspace.yaml           # reserved, active when TS appears
├── pyproject.toml                # reserved, uv workspace root
├── release-plz.toml
├── CHANGELOG.md
├── README.md
├── LICENSE
└── AGENTS.md
```

This layout copies the Kubernetes patterns that transfer and rejects the ones that are scale artifacts. The tree has a `cmd` equivalent in `crates/lilo`: a tiny binary shell that delegates to app and service crates. It has a `component-base` equivalent in `lilo-common`. It has a shared contract surface in `lilo-types`, the existing public `lilo-rm-*` and `lilo-im-*` crates, and eventually `lilo-client`. It does not use a Rust `staging/` directory because Cargo can publish workspace members from any path. The mirror problem is solved by generated mirror staging under `tools/mirror-publish`, not by changing source layout.

The future polyglot direction remains visible. `apps/` and `packages/` match the product direction and Electron baseline. They should land as empty directories with README stubs only if the first scaffold wants a durable placeholder. No TypeScript source should be invented in this migration. The same applies to `python/`: reserve the uv shape, but do not add a Python package until a real tool exists.

## 2. Cargo workspace shape

Use one Cargo workspace. Do not use workspace of workspaces. Rust already has a single lockfile, shared dependency declarations, shared version inheritance, and package scoped publish controls. A workspace of workspaces would recreate the current coordination problem inside one git repo.

Root `Cargo.toml` shape:

```toml
[workspace]
resolver = "3"
members = [
  "crates/*",
  "internal/runtime/*",
  "internal/session/*",
  "internal/identity/*",
  "tools/xtask",
  "tools/mirror-publish",
]
exclude = [
  "apps/*",
  "packages/*",
  "python/*",
]

[workspace.package]
version = "0.8.0"
edition = "2024"
license = "MIT"
rust-version = "1.90"
authors = ["Stuart Robinson"]
repository = "https://github.com/littleorgans/littleorgans"
homepage = "https://littleorgans.com"

[workspace.dependencies]
anyhow = "1"
async-trait = "0.1"
chrono = { version = "0.4", features = ["serde"] }
clap = { version = "4", features = ["derive"] }
indexmap = { version = "2", features = ["serde"] }
rusqlite = { version = "0.37", features = ["bundled"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sqlx = { version = "0.8", features = ["chrono", "migrate", "runtime-tokio", "sqlite", "uuid"] }
thiserror = "2.0"
tokio = { version = "1", features = ["fs", "io-std", "io-util", "macros", "net", "process", "rt-multi-thread", "signal", "sync", "time"] }
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt", "json"] }
uuid = { version = "1", features = ["serde", "v7"] }
```

Public crates use the `lilo-` prefix and publish from `crates/`. Internal crates live under `internal/` and set `publish = false`. That gives Cargo a native enforcement boundary: a public crate cannot accidentally publish a dependency on a private crate.

Keep the currently published crates as real packages because crates.io continuity matters:

| Current crate | Target path | Target package name | Publish | First monorepo version |
| --- | --- | --- | --- | --- |
| `lilo-rm-core@0.7.1` | `crates/lilo-rm-core` | `lilo-rm-core` | yes | `0.8.0` |
| `lilo-rm-client@0.7.1` | `crates/lilo-rm-client` | `lilo-rm-client` | yes | `0.8.0` |
| `lilo-im-core@0.1.1` | `crates/lilo-im-core` | `lilo-im-core` | yes | `0.8.0` |
| `lilo-im-store@0.1.1` | `crates/lilo-im-store` | `lilo-im-store` | yes | `0.8.0` |
| `lilo-im-stub@0.1.1` | `crates/lilo-im-stub` | `lilo-im-stub` | yes | `0.8.0` |

Do not collapse `lilo-rm-core` and `lilo-rm-client` during the migration. The split is useful: one crate owns wire and lifecycle types, the other owns the client shell. They currently map to the Kubernetes API and client-go split. Collapsing them would save one package name but would make downstream consumers depend on socket client machinery when they only need types. Later, once `lilod` is the only daemon, add `lilo-client` as the integrated client. Keep `lilo-rm-client` as a runtime scoped public client until a release proves `lilo-client` covers the same need.

Do not create `lilo-sm-core` in the first migration unless there is a concrete external consumer. Session currently has a workspace release and a binary surface, but no meaningful published client crate in the active repo. Its `sm-core` protocol can move to `internal/session/app` and `internal/session/daemon` until an external contract is deliberately exposed.

`rtm-shim` should not become its own binary. The shim becomes a hidden subcommand of the same `lilo` binary:

```text
lilo __runtime-shim --session-id <uuid> --socket <endpoint>
```

The runtime service spawns `std::env::current_exe()` with that hidden command. This preserves the reliable shim process without shipping a second executable.

TypeScript should use pnpm workspaces when real TS lands because pnpm is the cleanest fit for Moon, explicit workspaces, and the Electron baseline's package split. Root files to reserve:

```yaml
# pnpm-workspace.yaml
packages:
  - apps/*
  - packages/*
```

Python should use uv and PEP 621. Root `pyproject.toml` can reserve a workspace later, but the first migration should not add a Python package. When it does, use `python/lilo-tools/pyproject.toml` with a normal `[project]` section and let Moon call `uv run` tasks.

Moon config should use current Moon file names: `.moon/workspace.yml`, `.moon/toolchains.yml`, project level `moon.yml`, and shared tasks under `.moon/tasks/*.yml`. This matches the official Moon workspace, toolchain, task, and project documentation: `https://moonrepo.dev/docs/config/workspace`, `https://moonrepo.dev/docs/config/toolchain`, `https://moonrepo.dev/docs/config/tasks`, and `https://moonrepo.dev/docs/config/project`.

## 3. Binary surface

Ship one physical binary: `lilo`.

Do not ship `rtm`, `sm`, `rtmd`, or `smd` as separate installed binaries in the first monorepo release. The goal is to stop managing multiple CLIs and daemons. A busybox style argv alias is technically cheap, but it weakens the design signal and keeps old mental models alive. Tests may create local symlinks to exercise migration scenarios, but releases should present `lilo` only.

Top level public surface:

```text
lilo --version
lilo doctor [--output human|json]
lilo daemon start [--foreground] [--socket <path>] [--home <path>]
lilo daemon stop
lilo daemon status [--output human|json]
lilo run <runtime> --role <role> --dir <path> [--target <target>] [--detach]
lilo create session <runtime> --role <role> --dir <path>
lilo create namespace <slug>
lilo get session [--selector <selector>] [--show-labels] [-A]
lilo get namespace [<slug>]
lilo delete session <selector>
lilo delete namespace <slug>
lilo label <selector> <key=value|key->
lilo mail send --to <selector> --body <text>
lilo mail read --for <selector> [--peek]
lilo mail check --for <selector>
lilo nudge --to <selector>
lilo capture <session-id>
lilo logs <selector>
lilo wait <selector> --for <condition>
lilo mcp
```

Runtime level operator commands remain available, but they move under an explicit runtime namespace because most users should go through sessions:

```text
lilo runtime spawn --session-id <uuid> --runtime <claude|codex> --target <target>
lilo runtime status [--session-id <uuid> ...]
lilo runtime events [--since <cursor>]
lilo runtime kill <session-id>
lilo runtime doctor
```

This keeps the proven `rtm` diagnostic and lifecycle surface for staff level debugging while making session control the default user story.

Daemon surface: one process mode inside `lilo`, with process label `lilod` in logs and pid files.

```text
lilo daemon start
  -> initializes lilo-common
  -> resolves ~/.lilo through lilo-paths
  -> opens one socket at ~/.lilo/run/lilod.sock
  -> opens one SQLite database at ~/.lilo/data/lilo.db
  -> composes IdentityService, RuntimeService, SessionService
  -> starts runtime reconciliation and session event loops
  -> serves one RPC envelope with session, runtime, identity, and MCP methods
```

High level `main.rs`:

```rust
fn main() -> std::process::ExitCode {
    lilo_common::process::run_blocking(async {
        let cli = lilo::cli::Cli::parse();
        let ctx = lilo_common::Context::from_cli(&cli.global).await?;

        match cli.command {
            Command::Daemon(cmd) => internal_daemon::run(cmd, ctx).await,
            Command::Runtime(cmd) => runtime_app::run(cmd, ctx).await,
            Command::Session(cmd) => session_app::run(cmd, ctx).await,
            Command::Run(cmd) => session_app::run_imperative(cmd, ctx).await,
            Command::Doctor(cmd) => doctor::run(cmd, ctx).await,
            Command::Mcp(cmd) => mcp::run(cmd, ctx).await,
            Command::Hidden(hidden) => hidden::run(hidden, ctx).await,
        }
    })
}
```

The app crates build clap command fragments and request values. They do not open SQLite, touch tmux, inspect Docker, or authorize. The daemon and service crates own mechanism. This is the Kubernetes `cmd/X` split translated to Rust.

## 4. Versioning model

Adopt one version for every artifact now. The first monorepo release should be `0.8.0`.

Reasoning:

1. `lilo-rm-core` and `lilo-rm-client` are already published at `0.7.1`. A workspace version lower than `0.7.1` would regress the public runtime crates.
2. The migration is a breaking pre-1.0 change. For 0.x crates, the next minor line is the right signal.
3. Jumping identity crates from `0.1.1` to `0.8.0` is acceptable because the stated product direction says one version for everything in v0.
4. Session binary releases move from `0.2.8` to `0.8.0` for the same reason.

Every workspace package uses `version.workspace = true` unless an external generator forces otherwise. There is no runtime `0.7.x` line after the migration. If a critical patch is needed before the migration lands, cut it in the old runtime repo first, then set the monorepo first version to the next minor after that patch.

`release-plz` remains the crate publisher and changelog updater. Its own docs say multi package workspaces default to package specific tags such as `<package>-v<version>`, and a single package can use `v<version>` tags: `https://release-plz.dev/docs/usage/release`. For this monorepo, use release-plz to publish crates and produce package release metadata, then have the monorepo release workflow create the single source tag `v0.8.0` and attach binary artifacts. That avoids fighting release-plz over one tag for many publishable crates.

Proposed `release-plz.toml`:

```toml
[workspace]
release = false
publish = false
semver_check = true
changelog_update = true
release_always = false
git_tag_name = "{{ package }}-v{{ version }}"
git_release_name = "{{ package }} v{{ version }}"

[[package]]
name = "lilo-rm-core"
release = true
publish = true
version_group = "lilo-v0"

[[package]]
name = "lilo-rm-client"
release = true
publish = true
version_group = "lilo-v0"

[[package]]
name = "lilo-im-core"
release = true
publish = true
version_group = "lilo-v0"

[[package]]
name = "lilo-im-store"
release = true
publish = true
version_group = "lilo-v0"

[[package]]
name = "lilo-im-stub"
release = true
publish = true
version_group = "lilo-v0"

[[package]]
name = "lilo-client"
release = true
publish = true
version_group = "lilo-v0"

[changelog]
header = """# Changelog\n\nAll notable changes documented here.\n"""
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix", group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring", default_scope = "internal" },
  { message = "^docs?", group = "Documentation", default_scope = "internal" },
  { message = "^chore", group = "Miscellaneous", default_scope = "internal" },
  { message = "^test", group = "Tests", default_scope = "internal" },
  { message = "^ci", group = "CI", default_scope = "internal" },
]
```

If `lilo-client` is not ready in the first release, omit it. Do not publish placeholder crates just to fill the shape.

The release workflow should have these gates:

```text
moon run :fmt-check
moon run :clippy
moon run :test
moon run :build
cargo semver-checks check-release -p lilo-rm-core
cargo semver-checks check-release -p lilo-rm-client
cargo semver-checks check-release -p lilo-im-core
cargo publish -p <each public crate> --dry-run
cargo dist plan
cargo dist build
```

Then, on a release tag `v0.8.0`:

1. Run release-plz release for publishable crates.
2. Run cargo-dist for `lilo` binary artifacts.
3. Run `tools/mirror-publish` to stage and push public mirrors.
4. Create one private monorepo GitHub Release with the integrated changelog.
5. Create or update public mirror releases with scoped artifacts and scoped notes.

## 5. `~/.lilo/` data layout

Use one data root and one daemon endpoint:

```text
~/.lilo/
├── config/
│   ├── lilo.toml                 # global daemon, output, runtime defaults
│   ├── namespaces.toml           # current namespace context, if kept as file
│   └── agents/
│       ├── default.toml          # former ~/.agm style agent config slot
│       └── *.toml
├── run/
│   ├── lilod.sock
│   └── lilod.pid
├── data/
│   ├── lilo.db                   # one SQLite database
│   └── events/
│       ├── runtime.jsonl         # retained if JSONL event log remains valuable
│       └── daemon.jsonl
├── logs/
│   ├── lilod.log
│   ├── sessions/
│   │   └── <session-id>.log
│   ├── runtimes/
│   │   └── <session-id>/
│   │       ├── shim.log
│   │       └── runtime.log
│   └── mcp/
├── cache/
│   ├── manifests/
│   └── docker/
└── tmp/
```

Map old roots directly:

| Old path | New path | Policy |
| --- | --- | --- |
| `~/.rtm/sock` | `~/.lilo/run/lilod.sock` | replaced |
| `~/.rtm/db.sqlite` | `~/.lilo/data/lilo.db`, runtime tables | wiped by default |
| `~/.rtm/logs` | `~/.lilo/logs/runtimes` | wiped by default |
| `~/.rtm/events.jsonl` | `~/.lilo/data/events/runtime.jsonl` | wiped by default |
| `~/.sm/sock` | `~/.lilo/run/lilod.sock` | replaced |
| `~/.sm/sm.pid` | `~/.lilo/run/lilod.pid` | replaced |
| `~/.sm/sm.db` | `~/.lilo/data/lilo.db`, session tables | wiped by default |
| `~/.agm` | `~/.lilo/config/agents` | manually copied only if wanted |

No automatic migration is required because there are zero external users and Stuart explicitly accepts clean breaks. The first release notes should say:

```text
The monorepo cutover replaces ~/.rtm, ~/.sm, and ~/.agm with ~/.lilo. Stop old daemons, remove old state if desired, then start lilod. Existing local sessions and mail are not migrated.
```

Support these environment overrides:

| Variable | Purpose |
| --- | --- |
| `LILO_HOME` | root override for tests, CI, and isolated local runs |
| `LILO_SOCKET_PATH` | explicit Unix socket path for operators and e2e tests |
| `LILO_DB_PATH` | explicit SQLite path for store tests only |
| `LILO_LOG` | tracing filter, equivalent to `RUST_LOG` but product scoped |

Do not keep `RTM_HOME`, `SM_HOME`, `RTM_SOCKET_PATH`, or `SM_NAMESPACE` as supported aliases. If tests need to prove old variables are ignored, add negative tests. If the CLI sees old variables, `lilo doctor` can warn, but runtime behavior should not branch on them.

Use one SQLite database unless performance or locking proves otherwise. The tables should be prefixed by substrate:

```text
runtime_lifecycle
runtime_events_cursor
session_sessions
session_namespaces
session_mail
identity_audit
identity_policy_reserved
```

The runtime JSONL event stream is the only exception I would preserve as a separate file because its append only cursor behavior is a proven design and it decouples event delivery from SQLite write contention. If the daemon merge makes SQLite event tables simpler, delete JSONL during the migration instead of keeping both.

## 6. Unified standards

CLI framework: keep clap derive. One top level `Cli` owns global flags, one `Command` enum owns public verbs, and hidden operational commands are marked `hide = true`.

```rust
#[derive(Parser)]
pub struct Cli {
    #[command(flatten)]
    pub global: GlobalArgs,
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    Doctor(DoctorArgs),
    Daemon(DaemonArgs),
    Run(RunArgs),
    Create(CreateArgs),
    Get(GetArgs),
    Delete(DeleteArgs),
    Label(LabelArgs),
    Mail(MailArgs),
    Nudge(NudgeArgs),
    Capture(CaptureArgs),
    Logs(LogsArgs),
    Wait(WaitArgs),
    Runtime(RuntimeArgs),
    Mcp(McpArgs),
    #[command(hide = true, name = "__runtime-shim")]
    RuntimeShim(RuntimeShimArgs),
}
```

Generated surfaces: both runtime and session already have generated help, MCP schema, README sections, and snapshots. Unify that under one authored registry in `tools/` plus `xtask codegen`. Do not hand edit generated docs. The authored source should be one of:

```text
tools/cli.toml
tools/mcp.toml
tools/output.toml
```

or one typed Rust registry if TOML becomes too weak. The rule matters more than the file format: edit one authored contract, regenerate help, MCP schema, README sections, and snapshots together.

Errors: use `thiserror` in library and service crates, `anyhow` only in binary or app boundary code. `lilo-common` should expose a shared `Diagnostic` type for stable user and JSON errors. Preserve typed domain errors for cursor expiry, selector errors, spawn conflict, Docker preflight, namespace errors, and authorization denial.

Logging: use `tracing` everywhere. `lilo daemon start` writes human logs to stderr when foregrounded and structured JSON logs to `~/.lilo/logs/lilod.log` by default. Global flags:

```text
--log-filter <directive>      # default from LILO_LOG, then RUST_LOG, then info
--log-format human|json       # daemon default json, CLI default human
--quiet
--verbose
```

JSON output: every read command accepts `--output human|json`, with `--json` as a short alias only if it does not complicate clap. JSON output must be stable and snapshot tested. Human output can improve over time.

Exit codes:

| Code | Meaning |
| ---: | --- |
| 0 | success |
| 1 | unexpected internal failure |
| 2 | typed domain negative, such as not found, selector empty, cursor expired, spawn conflict |
| 3 | configuration or input validation failure |
| 4 | daemon unavailable or protocol incompatible |
| 5 | authorization denied, reserved for identity enforcement |

Help format: keep kubectl shaped nouns for CRUD and imperative verbs for workflows. The visible nouns are `session` and `namespace` first. Runtime subcommands are explicit operator tools. Help tests must assert no blank descriptions and no dead aliases.

Docs: root `README.md` is the operator manual. `docs/architecture` contains authored architecture. `docs/reference` contains generated CLI, MCP, and data layout references. Every mirror gets a generated README with a banner that says source lives in the private monorepo and PRs are not accepted there.

CHANGELOG: one root `CHANGELOG.md` for the monorepo. Public mirror changelogs are generated filtered views of the root changelog. Do not keep separate hand edited changelogs per substrate.

CI: GitHub Actions should call Moon as the orchestrator. Moon is the task graph layer, Cargo is the Rust compiler and package layer. Initial shared tasks:

```yaml
# .moon/tasks/rust.yml
fileGroups:
  sources:
    - 'crates/**/*.rs'
    - 'internal/**/*.rs'
    - 'tools/**/*.rs'
    - 'Cargo.toml'
    - 'Cargo.lock'

tasks:
  fmt:
    command: 'cargo fmt --all'
    options:
      cache: false
  fmt-check:
    command: 'cargo fmt --all -- --check'
  clippy:
    command: 'cargo clippy --workspace --all-targets -- -D warnings'
  build:
    command: 'cargo build --workspace'
    inputs:
      - '@group(sources)'
    outputs:
      - 'target/debug'
  test:
    command: 'cargo nextest run --workspace'
    inputs:
      - '@group(sources)'
  loc:
    command: 'bash scripts/check-loc-limit.sh'
```

Moon should install or verify Rust, Node, and Python toolchains through `.moon/toolchains.yml`, but Cargo commands remain plain and reproducible locally.

## 7. Git history strategy

Recommended default: clean slate monorepo with explicit provenance, not merged git history.

Mechanics:

1. For each current source repo, record `git remote -v`, `git rev-parse HEAD`, `git status --short`, and the latest tags in `docs/provenance/imported-repos.md`.
2. Tag the old repositories at their final source of truth commit:

```bash
git -C identity-matters tag pre-monorepo-2026-05-25
git -C runtime-matters tag pre-monorepo-2026-05-25
git -C session-matters tag pre-monorepo-2026-05-25
```

3. Push those tags before changing repo disposition.
4. Initialize `littleorgans/littleorgans` as a new private repo.
5. Copy source into the new layout with normal commits grouped by migration phase.
6. Keep the old repos available as historical references, then repurpose their `main` branches as generated mirrors only after the monorepo release pipeline proves mirror generation.

Why clean slate: the current repositories are small, pre-release, and already have public tags for published crates. Preserving three unrelated git histories inside the new private repo will complicate blame, inflate the initial migration, and make every future path move harder to reason about. The valuable continuity is crate version continuity, release tags, and source provenance, not local commit hashes inside the new repo.

Alternative if Stuart decides history matters: use `git filter-repo --to-subdirectory-filter` for each source repo, then merge with `--allow-unrelated-histories`.

```bash
git clone git@github.com:littleorgans/runtime-matters.git /tmp/runtime-filter
git -C /tmp/runtime-filter filter-repo --to-subdirectory-filter imported/runtime-matters
git remote add runtime-filter /tmp/runtime-filter
git fetch runtime-filter
git merge runtime-filter/main --allow-unrelated-histories
```

Then move files from `imported/runtime-matters` to the target layout in follow up commits. This preserves blame but doubles migration noise. I would only do it if Stuart expects to audit old history frequently from the new private repo.

Open decision: clean slate versus preserved history is still parked by the brief. My recommendation is clean slate, but the first phase should not destroy the option. Tag old repos and record SHAs before importing anything.

## 8. Migration sequence

Each phase should be one PR against the new monorepo after Phase 1. Old repos remain source of truth until the final cutover. Within the new monorepo, do not ship a release until the old `rtm`, `sm`, `rtmd`, and `smd` surfaces have been removed or folded into `lilo`.

### Phase 0: Decision and source freeze checkpoint

Scope: no code. Decide repo name, history strategy, first version, and whether `lilo` ships without argv aliases.

Exit criteria:

- `docs/provenance/imported-repos.md` lists final SHAs and tags for identity, runtime, and session.
- Current dirty files are understood. Today `identity-matters` has untracked `AGENTS.md`, `CLAUDE.md`, and `TLDR.md`; `runtime-matters` has untracked `MAP.md`. Decide whether those become source docs before import.
- `schedule-matters` is recorded as empty and not a git repo.

Tests: none beyond verification commands and git status capture.

### Phase 1: Scaffold monorepo

Scope: create `littleorgans/`, root Cargo workspace, root Moon config, `crates/lilo`, `crates/lilo-common`, `crates/lilo-paths`, `tools/xtask`, `scripts/check-loc-limit.sh`, README, LICENSE, AGENTS.

Exit criteria:

- `lilo --version` prints `0.8.0` plus git SHA when enabled.
- `lilo doctor` exists as a stub that reports no daemon.
- `moon run :fmt-check`, `moon run :clippy`, `moon run :build`, and `moon run :test` work for the empty workspace.
- CI runs the same commands.

Tests: cargo unit tests for `lilo-paths`; assert `LILO_HOME` temp override.

### Phase 2: Import identity crates

Scope: move `lilo-im-core`, `lilo-im-store`, and `lilo-im-stub` into `crates/`; update package metadata to workspace values; move default audit path to `lilo-paths`; keep public APIs otherwise recognizable.

Exit criteria:

- Identity tests pass.
- `cargo publish -p lilo-im-core --dry-run`, `lilo-im-store`, and `lilo-im-stub` succeed locally.
- Audit store defaults to `~/.lilo/data/lilo.db` or an explicit `LILO_DB_PATH` in tests.

Tests: existing identity tests plus new path tests for `LILO_HOME`.

### Phase 3: Import runtime contracts and client

Scope: move `lilo-rm-core` and `lilo-rm-client` into `crates/`; move runtime private crates under `internal/runtime`; keep the runtime service buildable but do not expose `rtm` binary.

Exit criteria:

- `lilo-rm-core` and `lilo-rm-client` compile at version `0.8.0`.
- Current wire snapshot tests pass or are intentionally updated for the breaking version.
- Private runtime crates are `publish = false`.
- No source file exceeds 700 LOC after path moves.

Tests: runtime core snapshots, wire tests, typed client tests, launcher tests, store tests.

### Phase 4: Import session crates

Scope: move session private crates under `internal/session`; split the current 700 LOC `sm-daemon/src/mcp_tools.rs` before adding code to it; update direct `lilo-rm-*` dependencies to workspace path dependencies; keep session protocol internal.

Exit criteria:

- Session tests pass under the monorepo.
- Legacy workspace selector tests are either deleted or rewritten as negative tests for the new `dir` only grammar.
- `SM_HOME`, `SM_NAMESPACE`, and old `.sm` assumptions are gone from production code.

Tests: session CLI tests, daemon handler tests, MCP schema snapshots, selector scope tests.

### Phase 5: Cut over paths to `~/.lilo`

Scope: replace `rtm-paths` and `sm-paths` production use with `lilo-paths`; delete old env var support; update docs and snapshots.

Exit criteria:

- Only `LILO_*` env vars influence production path resolution.
- `lilo doctor` reports the unified root, socket, database, logs, Docker, tmux, and agent config status.
- Existing path tests are ported to `lilo-paths` and old path crates are deleted or reduced to test fixtures before release.

Tests: path unit tests, doctor snapshot tests, CLI e2e with temp `LILO_HOME`.

### Phase 6: Introduce unified `lilo` command surface

Scope: move current `rtm-cli` and `sm-cli` command modules into runtime and session app libraries; implement the top level `lilo` command; remove public `rtm` and `sm` binaries.

Exit criteria:

- `cargo build --workspace` emits one installed binary target, `lilo`.
- `lilo run`, `lilo create session`, `lilo get session`, `lilo runtime spawn`, and `lilo runtime events` call real app code.
- Hidden shim command works through `std::env::current_exe()`.
- Help snapshots reflect `lilo`, not `rtm` or `sm`.

Tests: CLI help snapshots, command behavior tests, hidden shim tests.

### Phase 7: Compose one daemon

Scope: refactor runtime daemon into `RuntimeService`; refactor session daemon into `SessionService`; compose them with `IdentityService` inside `lilo daemon start`. Replace session to runtime local socket calls with an in process service call when co-resident. Keep the `lilo-rm-client` socket path for external client compatibility until `lilo-client` replaces it.

Exit criteria:

- One socket accepts all daemon RPC.
- Runtime reconciliation and session event loop run under one cancellation scope.
- Session spawn mints UUIDv7, authorizes through identity, delegates to runtime service, persists session, and returns the session record.
- `lilo daemon stop` drains both services cleanly.

Tests: in process integration tests for spawn, list, events, mail, nudge, kill, logs, doctor. Real binary e2e starts daemon in temp `LILO_HOME` and runs one fake runtime.

### Phase 8: Release and mirror tooling

Scope: build `tools/mirror-publish`; generate self buildable mirrors for identity, runtime, and session; wire GitHub Actions release cascade.

Exit criteria:

- `tools/mirror-publish --dry-run --version 0.8.0` produces three staging directories.
- Each staging directory has a concrete `Cargo.toml`, `Cargo.lock` if needed, README banner, LICENSE, CHANGELOG, and enough source to `cargo build` in isolation.
- Mirror release dry run prints git commands without pushing.

Tests: mirror staging tests and `cargo build` inside temp staging dirs.

### Phase 9: Cutover release

Scope: merge final release PR, tag `v0.8.0`, publish crates, publish binary artifacts, push mirrors, archive or repurpose old source repos.

Exit criteria:

- `cargo search` shows public crates at `0.8.0`.
- GitHub Release `v0.8.0` exists in private monorepo.
- Public mirrors have generated `main`, tag `v0.8.0`, scoped README, and scoped release notes.
- Old daemons are stopped locally and `lilo doctor` is green.

Tests: install release artifact, run `lilo doctor`, run fake runtime smoke, run one session mail round trip.

## 9. What ships first

First PR tomorrow morning should be the scaffold only. No source migration. No daemon merge. No mirror pushes.

Commands:

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans
mkdir littleorgans
cd littleorgans
git init
mkdir -p .moon/tasks crates/lilo/src crates/lilo-common/src crates/lilo-paths/src tools/xtask/src scripts docs/provenance
cat > rust-toolchain.toml <<'TOML'
[toolchain]
channel = "1.90"
components = ["rustfmt", "clippy"]
TOML
```

Create `Cargo.toml` with workspace version `0.8.0`, three starter crates, and shared dependencies. Create `crates/lilo/src/main.rs` as a thin clap shell with `--version` and `doctor`. Create `lilo-paths` with `LILO_HOME` resolution and tests. Create `lilo-common` with version and tracing stubs only.

Create `.moon/workspace.yml`:

```yaml
projects:
  - 'crates/*'
  - 'internal/*/*'
  - 'tools/*'

vcs:
  manager: git
  defaultBranch: main

runner:
  archivableTargets:
    - ':build'
    - ':test'
```

Create `.moon/toolchains.yml`:

```yaml
rust:
  version: '1.90.0'
node:
  version: '24.0.0'
  packageManager: 'pnpm'
python:
  version: '3.13.0'
```

The Node and Python versions are placeholders to verify Moon shape, not a commitment to TS or Python source in PR 1. If Moon rejects exact field names during live setup, prefer `moon toolchain info rust`, `moon toolchain info typescript`, and `moon toolchain info unstable_python` over guessing.

Create `justfile`:

```make
set shell := ["bash", "-cu"]

default:
    @just --list

fmt:
    cargo fmt --all

fmt-check:
    cargo fmt --all -- --check

clippy:
    cargo clippy --workspace --all-targets -- -D warnings

build:
    cargo build --workspace

test:
    cargo nextest run --workspace

check-loc:
    bash scripts/check-loc-limit.sh

check: fmt clippy check-loc
```

Create `scripts/check-loc-limit.sh` by adapting the existing repo scripts, but make it root aware and fail on any new source file above 700 LOC or function above the agreed threshold if the function checker exists. If the old scripts only enforce file LOC, ship file LOC in PR 1 and add function checks later.

Create `docs/provenance/imported-repos.md` with current remotes, tags, and SHAs. Do not copy source yet.

Acceptance for PR 1:

```bash
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo build --workspace
cargo nextest run --workspace
bash scripts/check-loc-limit.sh
./target/debug/lilo --version
./target/debug/lilo doctor --output json
```

This first PR proves the repo can exist, can build, can use Moon, can run the local Rust gate, and can version itself. It creates no migration ambiguity.

## 10. Risks and unknowns

1. **History strategy remains a Stuart decision.** I recommend clean slate with provenance, but preserving history through `git filter-repo` is still possible before Phase 1 imports source.

2. **Release-plz may not be enough for one human release.** Release-plz is good for crates.io package publishing, but its documented multi package default is package scoped tags. The monorepo still needs one root tag and one binary release. Phase 8 must validate this workflow before cutover.

3. **The unified daemon is real architecture work.** Folding `smd` and `rtmd` into one process is not a path move. Session currently delegates to runtime over `~/.rtm/sock`; the monorepo target should call an in process runtime service while retaining a public client boundary. This is the critical path.

4. **Mirror generation can become a hidden build system.** Each mirror must be self buildable. Rewriting path dependencies into registry dependencies and flattening workspace inherited fields must be tested like product code.

5. **Current dirty docs need a call.** `runtime-matters/MAP.md` is valuable and should be imported under `docs/architecture/runtime.md` or `docs/provenance/runtime-map.md`. `identity-matters` has untracked TLDR symlink targets. Decide before freezing SHAs.

6. **Session has a file at the hard line cap.** `session-matters/crates/sm-daemon/src/mcp_tools.rs` is exactly 700 LOC. Any migration phase that adds to it must split it first.

7. **Public crate set has a small mismatch with the brief table.** Current crates.io search shows `lilo-im-stub@0.1.1` as published. Treat all `lilo-im-*` crates as public and monotonic.

8. **No backcompat makes docs and local cleanup important.** The code should not read old env vars or migrate old DBs, but release notes must tell Stuart to stop old daemons and expect fresh state.

9. **Transport-matters is out of scope.** The parent docs say it is orthogonal and outside this directory. Do not pull it into this migration. Only preserve session IDs and observable process boundaries so transport can correlate later.

10. **Moon Rust support needs a live smoke.** The config names are verified against current Moon docs, but field details should be validated in PR 1 with the installed Moon version.

11. **Schedule semantics are undefined.** The directory is empty. Do not invent scheduler code during a migration.

Open questions Stuart must answer before the named phase:

| Question | Blocks |
| --- | --- |
| Use clean slate history? | Phase 1 import commits |
| Is `github.com/littleorgans/littleorgans` the private repo name? | Phase 1 remote setup |
| Is `0.8.0` accepted as the first monorepo version? | Phase 1 Cargo metadata |
| Should releases ship only `lilo`, with no `rtm` or `sm` symlinks? | Phase 6 |
| Should runtime JSONL events survive, or move fully into SQLite? | Phase 7 |
| Should old public repos be force rewritten as mirrors, or keep old history on main and push mirrors to a new branch? | Phase 8 |

## 11. schedule-matters status

Inspection result:

```text
/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/
```

The directory exists, is empty, and is not a git repo. There are no markdown files, manifests, source files, or releases to migrate.

Disposition: defer code, reserve concept.

Do not absorb schedule into session-matters during this migration. The session PROJECT doc names unmanaged session adoption as deferred to the schedule-matters Linear project and says adoption should return only with a coherent reconcile model. That is a product design statement, not an empty directory to fill.

Add only this placeholder if the target tree wants to show the future slot:

```text
internal/schedule/README.md
```

Suggested content:

```markdown
# schedule

Reserved for scheduler owned binding, adoption, and reconciliation workflows. No runtime code lives here until the scheduler model is specified.
```

No `lilo-schedule-*` crate in the first migration. No mirror release for schedule until it has source, tests, and a public story.

## 12. The four GitHub repos

Current source repos:

```text
github.com/littleorgans/identity-matters
github.com/littleorgans/runtime-matters
github.com/littleorgans/session-matters
```

`schedule-matters` has no git repo on disk, so there is no current GitHub source repo to preserve from this migration.

Recommended disposition for the three current repos: repurpose them as public read only mirrors after the monorepo cutover, do not delete them.

Mechanics on migration day:

1. Push a final source tag to each old repo: `pre-monorepo-2026-05-25`.
2. Create a branch such as `archive/pre-monorepo-main` pointing at the old source main.
3. Disable normal PR flow or add a banner that PRs are not accepted there.
4. After the monorepo release job generates mirror content, push generated mirror `main` to the same repo name.
5. Tag each mirror with the monorepo version, such as `v0.8.0`.
6. Attach scoped release artifacts and notes.

The mirror README banner should be explicit:

```markdown
# runtime-matters

This repository is a generated MIT mirror of the private littleorgans monorepo. Source changes are made in `github.com/littleorgans/littleorgans` and pushed here on release. Pull requests against this mirror are not accepted.
```

Cascading release shape:

```text
private monorepo tag v0.8.0
  -> build and test full workspace
  -> publish crates.io packages
  -> build lilo binary with cargo-dist
  -> tools/mirror-publish --version 0.8.0 --mirror runtime-matters
       -> stage runtime source subset
       -> rewrite Cargo.toml workspace fields to concrete package fields
       -> replace path deps on public crates with registry deps at 0.8.0
       -> generate README, CHANGELOG, LICENSE
       -> run cargo build in staged mirror
       -> push to github.com/littleorgans/runtime-matters main
       -> tag runtime mirror v0.8.0
       -> create GitHub Release with runtime scoped notes
  -> repeat for identity-matters and session-matters
```

Mirror rules should be data, not shell conditionals:

```toml
[[mirror]]
name = "runtime-matters"
repo = "git@github.com:littleorgans/runtime-matters.git"
paths = [
  "crates/lilo-rm-core",
  "crates/lilo-rm-client",
  "internal/runtime",
  "docs/mirrors/runtime-matters.md",
  "LICENSE",
]
public_crates = ["lilo-rm-core", "lilo-rm-client"]
binaries = ["lilo"]

[[mirror]]
name = "identity-matters"
repo = "git@github.com:littleorgans/identity-matters.git"
paths = [
  "crates/lilo-im-core",
  "crates/lilo-im-store",
  "crates/lilo-im-stub",
  "internal/identity",
  "docs/mirrors/identity-matters.md",
  "LICENSE",
]
public_crates = ["lilo-im-core", "lilo-im-store", "lilo-im-stub"]

[[mirror]]
name = "session-matters"
repo = "git@github.com:littleorgans/session-matters.git"
paths = [
  "internal/session",
  "docs/mirrors/session-matters.md",
  "LICENSE",
]
binaries = ["lilo"]
```

The session mirror is the trickiest because it has no current public crate split. The mirror should still be self buildable. It can include enough `crates/` dependencies to build `lilo` with session features, or it can be a source and binary release mirror with no crates.io package. The mirror tool must prove the generated repo builds in isolation before any push.

Do not delete the current repositories. Deletion loses provenance and breaks any external links, even if the project has no external users. Repurposing preserves the public URL while changing the source of truth.
