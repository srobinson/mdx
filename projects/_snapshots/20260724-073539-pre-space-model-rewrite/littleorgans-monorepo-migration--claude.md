---
title: littleorgans monorepo migration — claude independent plan
type: project-plan
tags: [littleorgans, monorepo, migration, moon, brainstorm, claude, --claude.md]
summary: Single Cargo workspace at littleorgans/ with crates/ + xtask + tools, single user-facing lilo binary that argv-dispatches into per-substrate runtime modes, unified ~/.lilo/ data root with per-substrate subtrees, single workspace version that resets the lilo-rm-* publish line to 0.8.0 and bumps lilo-im-* to 0.2.0 in lockstep on first monorepo cut. Recommends clean-slate git, archive-and-mirror for the four GitHub repos, schedule-matters scaffolded fresh as a placeholder crate with no daemon yet. Day-one PR stands up the workspace shell with lilo --version and nothing else; substrates land one at a time afterward.
status: draft
source: claude
confidence: medium
created: 2026-05-25
---

# littleorgans monorepo migration plan — claude side

Independent plan produced in parallel with a Codex peer. The two will be merged by Stuart. The plan is Rust-first because all four sub-repos in scope today are Rust; the TypeScript and Python sides of the direction doc are reserved-but-empty in the layout below, ready for Moon to extend later without re-shuffling the Rust tree.

## §1 Target directory layout

The monorepo root sits at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans/`. Initial scope is Rust-only. Slots are reserved for TS, Python, web, electron, and helix per the direction doc; those slots exist as empty directories with a `.gitkeep` and a one-line `README.md` saying "reserved for future migration" so the topology is committed-but-not-populated until those substrates actually move.

```
littleorgans/                          # private repo, git init, single Cargo workspace
├── Cargo.toml                         # the one workspace manifest
├── Cargo.lock
├── rust-toolchain.toml                # pin 1.90, edition 2024
├── moon.yml                           # workspace-level Moon config (Rust toolchain task)
├── .moon/                             # Moon orchestration (toolchain.yml, workspace.yml, tasks.yml)
├── README.md                          # operator-facing intro, brand-locked, no Helioy mentions
├── CHANGELOG.md                       # release-plz output, monorepo-wide
├── LICENSE                            # MIT for the monorepo root (mirrors inherit per-substrate)
├── CLAUDE.md → AGENTS.md              # working-style memo for any agent inside the repo
├── crates/                            # all Rust crates, flat. Naming convention rules below.
│   ├── lilo/                          # the single user-facing binary crate (was rtm-cli + sm-cli)
│   ├── lilo-common/                   # shared plumbing: logging, paths, version, error envelope
│   ├── lilo-types/                    # cross-substrate wire types, exposed publicly per substrate
│   ├── lilo-rm-core/                  # PUBLISHED. Continues lilo-rm-core@0.7.x → 0.8.0 at monorepo cut
│   ├── lilo-rm-client/                # PUBLISHED. Same.
│   ├── rm-daemon/                     # internal, publish=false. The old rtm-daemon.
│   ├── rm-launchers/                  # internal
│   ├── rm-platform/                   # internal
│   ├── rm-store/                      # internal
│   ├── lilo-im-core/                  # PUBLISHED. Continues lilo-im-core@0.1.x → 0.2.0
│   ├── lilo-im-store/                 # PUBLISHED. Same.
│   ├── im-stub/                       # internal (was lilo-im-stub; demote unless external need)
│   ├── sm-core/                       # internal
│   ├── sm-daemon/                     # internal
│   ├── sm-driver/                     # internal
│   ├── sm-store/                      # internal
│   └── sched-stub/                    # placeholder for schedule-matters substrate (§11)
├── xtask/                             # cargo xtask: codegen, mirror-publish, release helpers
│   ├── Cargo.toml
│   └── src/main.rs
├── tools/                             # ad-hoc dev tools (one crate per tool, all publish=false)
│   └── lilo-mirror-publish/           # the crate that produces per-substrate mirror tarballs
├── tests/                             # workspace-level integration tests (in-process spinup)
│   ├── e2e/                           # assert_cmd-driven CLI smoke tests against the real `lilo`
│   └── integration/                   # cross-substrate harness tests (sm + rm in-process)
├── docs/                              # one source of truth for narrative docs
│   ├── architecture.md
│   ├── cli.md                         # the full `lilo` verb tree
│   ├── data-layout.md                 # the canonical ~/.lilo/ description
│   └── per-substrate/                 # short notes per substrate, link out to architecture.md
├── apps/                              # RESERVED for direction-doc apps/ shape
│   ├── electron-shell/.gitkeep
│   ├── server/.gitkeep
│   └── web/.gitkeep
├── packages/                          # RESERVED for direction-doc TS packages
│   └── .gitkeep
├── helix/                             # RESERVED for helix migration
│   └── .gitkeep
├── products/                          # RESERVED — future product surfaces (transport-matters, etc.)
│   └── .gitkeep
├── infrastructure/                    # RESERVED — future cm/am/fmm/helioy-bus migration
│   └── .gitkeep
└── .github/
    └── workflows/                     # CI: build, test, lint, mirror-publish on release
```

### Why this layout

The k8s research grades `cmd/X` thin-shells, `pkg/`-by-convention (Rust's `publish=false`), component-base-shared-plumbing, and per-component config schemas as "transfers cleanly". They make up the spine of this layout:

- **`crates/lilo/`** is the kubernetes `cmd/kubelet/kubelet.go` analogue. A thin `main.rs` (target ~80 LOC, well under the 150 cap) that dispatches subcommands. Every actual implementation lives in a sibling crate.
- **`crates/lilo-common/`** is the `k8s.io/component-base` analogue. Logging, version, paths, common error type, signal handling. Anything every binary mode needs once.
- **`crates/lilo-types/`** is the `k8s.io/api` analogue: cross-substrate wire types. Per the k8s research §3.3 ("the cleanest example is CRI") the answer is **not** one mega-types crate. It is per-contract crates. So `lilo-types` is actually the public face of all four substrates' contracts, but mechanically lives as four sibling published crates: `lilo-rm-core` (already shipped), `lilo-rm-client`, `lilo-im-core`, `lilo-im-store`, plus new `lilo-sm-core` and `lilo-sm-client` when session-matters lands. The directory entry `crates/lilo-types/` is a thin meta-crate that re-exports the four for convenience; or it can be dropped entirely if the convenience is not worth the indirection. Recommendation: drop the meta-crate; let each substrate publish its own typed contract crate. See §2.
- **`crates/rm-daemon/`, `crates/sm-daemon/`** etc. are the `pkg/X/` analogue. Internal, never published. Named without the `lilo-` prefix because the prefix is for the public surface only (constraint from the brief).
- **`xtask/`** is the k8s research §"Pattern 10" answer: skip `hack/`, use cargo xtask.
- **`tools/lilo-mirror-publish/`** addresses k8s research §"Open question 1": the most novel piece of CI engineering. Lives as a regular workspace member crate so it gets test coverage, formatting, lint passes, and is built into the release pipeline.
- **The reserved dirs** (`apps/`, `packages/`, `helix/`, `products/`, `infrastructure/`) commit the topology from the direction doc on day one so future migrations slot in without renaming. They are empty placeholders until those substrates actually move. Carrying them now costs nothing and avoids a layout-shifting commit later.

### Open layout choice flagged

The direction doc's tree shows `infrastructure/` containing `context-matters`, `attention-matters`, `fmm`, `helioy-bus`, `knowledge-matters` — meaning that eventually `crates/` would not be the home of every Rust thing. The four substrates currently in scope are products-or-infrastructure-ambiguous. My read: identity-matters, runtime-matters, session-matters, schedule-matters are all "platform infrastructure for running agent processes," not user-facing products. When the direction-doc-shape stabilizes, they likely move under `infrastructure/lilo/crates/...`.

Doing that on day one creates pointless depth: `infrastructure/lilo/crates/lilo/src/main.rs`. Doing it later requires a path-shuffle PR.

**Recommendation:** keep `crates/` at workspace root for now. When the direction-doc tree actually gets populated (helix lands, cm migrates), do a one-shot rename of `crates/` to `infrastructure/lilo/crates/` and adjust `Cargo.toml` paths. Cargo handles that fine. **Flag as open question §10-Q1.**

## §2 Cargo workspace shape

**One workspace.** No workspace-of-workspaces. The brief says four substrates and ~15 crates post-migration; that's well under the 50-crate threshold where multi-workspace pain emerges. One workspace gives one `Cargo.lock`, one `cargo build --workspace`, one `cargo test --workspace`, one place to bump versions.

### Naming convention

Two-tier, enforced by Cargo's `publish = true/false`:

| Tier | Prefix | Examples | Publish |
|---|---|---|---|
| Public (`crates.io`-shipped) | `lilo-` | `lilo`, `lilo-common`, `lilo-rm-core`, `lilo-rm-client`, `lilo-im-core`, `lilo-im-store`, `lilo-sm-core`, `lilo-sm-client` | `publish = true` |
| Internal (workspace-only) | substrate stem (no `lilo-`) | `rm-daemon`, `rm-platform`, `rm-store`, `rm-launchers`, `sm-daemon`, `sm-driver`, `sm-store`, `im-stub`, `sched-stub` | `publish = false` |

The `lilo-` prefix collision with crates.io is already locked by the published 0.7.1 / 0.1.1 surface. No second org or scope is needed. Stuart owns the namespace.

**The `lilo` binary crate itself is published** so `cargo install lilo` works for anyone who wants the binary. Even though the source isn't useful as a library, publishing it makes the install path canonical. Its `Cargo.toml` declares `[lib] = nothing` and a single `[[bin]] name = "lilo"`. Per k8s pattern 1, this binary is a thin shell that depends on every substrate's `*-app` crate. But wait — see "App layer collapse" below; I am not adopting a separate `*-app` crate per substrate.

### App-layer simplification

K8s separates `cmd/X` (thin shell) from `cmd/X/app/` (clap wiring) from `pkg/X` (internals). For littleorgans at this scale, the middle layer is over-engineering. Collapse `*-app` into the corresponding `*-daemon` or `*-cli` crate. Concretely:

- The `lilo` binary crate has a small `cli/` module with one file per top-level subcommand (`cli/im.rs`, `cli/rm.rs`, `cli/sm.rs`, plus `cli/doctor.rs`, `cli/version.rs`, `cli/daemon.rs`). Each module exports `pub fn build_command() -> clap::Command` and `pub fn run(matches) -> Result<()>`.
- The daemon entry points (the old `rtmd` and `smd` binaries) become **library functions** in `rm-daemon` and `sm-daemon` (already largely the shape today). The `lilo daemon rm start` and `lilo daemon sm start` subcommands call into those library functions.

No `*-app` crates. No second main per substrate. The whole bootstrap fits inside `crates/lilo/src/main.rs` + the small `cli/` module tree.

### The lilo-rm-* / lilo-im-* publish pair: keep, expand

K8s ships ~35 staging modules; the underlying principle is "publish exactly what external consumers need, nothing more." Today's publish surface:

- `lilo-rm-core` — wire types for runtime-matters
- `lilo-rm-client` — client to rtmd
- `lilo-im-core` — Authorizer trait + Principal + AuditRow
- `lilo-im-store` — SQLite audit sink

What's missing that should ship: a sm-side equivalent. Session-matters has zero published crates today because session-matters is consumed by session-matters callers only. But the direction doc's MIT mirror story means each substrate needs a public face. So this migration adds:

- `lilo-sm-core` — wire types for session-matters' RPC (selectors, namespaces, session shape, mail)
- `lilo-sm-client` — typed client to smd

Five published crates per release. The schedule-matters disposition (§11) decides whether `lilo-sched-*` joins.

The `im-stub` crate is currently published (in the workspace.dependencies for the old workspace). I'm demoting it to internal because external IM stub users don't exist; if v2 brings a real authorizer, the `im-stub` becomes a test fixture only. If someone outside Stuart's monorepo ever wants the stub, re-promote it; it's cheap.

### TS and Python slots

The direction doc names Moon. Moon supports Rust, Node, Python, Go, Bun. The monorepo's `moon.yml` and `.moon/toolchain.yml` declare the Rust toolchain on day one. The `apps/`, `packages/`, `helix/`, `products/`, `infrastructure/` reserved dirs are explicitly empty.

When the TS side migrates (Electron shell, web, server per direction doc), the shape will be `pnpm workspaces` declared at workspace root via `pnpm-workspace.yaml`, with `apps/electron-shell/package.json`, `apps/web/package.json`, `apps/server/package.json`, `packages/contracts/package.json`, etc. Moon orchestrates both Rust and pnpm with one `moon ci` invocation. This plan does not stand up pnpm scaffolding yet — too early, and the direction doc's TS architecture is still settling (the baseline spec is partially superseded). **Flag in §10-Q2:** when does the TS scaffold land?

Python is the same shape: `uv` is the modern standard, `pyproject.toml` per package under `packages/python-*` or `tools/python-*`. Moon supports `uv` natively. Same deferral as TS.

The dedicated `xtask/` crate handles release plumbing in Rust today, and would coexist with future Node-based release scripts under `tools/` later.

### Workspace Cargo.toml skeleton

```toml
[workspace]
resolver = "3"
members = [
    "crates/lilo",
    "crates/lilo-common",
    "crates/lilo-rm-core",
    "crates/lilo-rm-client",
    "crates/lilo-im-core",
    "crates/lilo-im-store",
    "crates/lilo-sm-core",
    "crates/lilo-sm-client",
    "crates/im-stub",
    "crates/rm-daemon",
    "crates/rm-launchers",
    "crates/rm-platform",
    "crates/rm-store",
    "crates/sm-core",
    "crates/sm-daemon",
    "crates/sm-driver",
    "crates/sm-store",
    "crates/sched-stub",
    "xtask",
    "tools/lilo-mirror-publish",
    "tests/e2e",
    "tests/integration",
]

[workspace.package]
version = "0.8.0"           # see §4 for rationale
edition = "2024"
license = "MIT"
repository = "https://github.com/littleorgans/littleorgans"
authors = ["Stuart Robinson"]
rust-version = "1.90"

[workspace.dependencies]
# published surface — sibling references use the same workspace version
lilo-common      = { path = "crates/lilo-common", version = "0.8.0" }
lilo-rm-core     = { path = "crates/lilo-rm-core", version = "0.8.0" }
lilo-rm-client   = { path = "crates/lilo-rm-client", version = "0.8.0" }
lilo-im-core     = { path = "crates/lilo-im-core", version = "0.8.0" }
lilo-im-store    = { path = "crates/lilo-im-store", version = "0.8.0" }
lilo-sm-core     = { path = "crates/lilo-sm-core", version = "0.8.0" }
lilo-sm-client   = { path = "crates/lilo-sm-client", version = "0.8.0" }
# internal
rm-daemon        = { path = "crates/rm-daemon" }
rm-launchers     = { path = "crates/rm-launchers" }
rm-platform      = { path = "crates/rm-platform" }
rm-store         = { path = "crates/rm-store" }
sm-core          = { path = "crates/sm-core" }
sm-daemon        = { path = "crates/sm-daemon" }
sm-driver        = { path = "crates/sm-driver" }
sm-store         = { path = "crates/sm-store" }
im-stub          = { path = "crates/im-stub" }
sched-stub       = { path = "crates/sched-stub" }
# 3rd-party — single source of truth for versions
anyhow = "1"
async-trait = "0.1"
chrono = { version = "0.4", features = ["clock", "serde"] }
clap = { version = "4", features = ["derive"] }
libc = "0.2"
nix = { version = "0.30", features = ["process", "signal", "socket", "term", "user"] }
rusqlite = { version = "0.37", features = ["bundled"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
sqlx = { version = "0.8", features = ["chrono", "migrate", "runtime-tokio", "sqlite", "uuid"] }
thiserror = "2"
tokio = { version = "1", features = ["fs", "io-std", "io-util", "macros", "net", "process", "rt-multi-thread", "signal", "sync", "time"] }
toml = "0.8"
tracing = "0.1"
tracing-subscriber = { version = "0.3", features = ["env-filter", "fmt"] }
uuid = { version = "1", features = ["serde", "v7"] }
# dev
assert_cmd = "2"
criterion = "0.5"
insta = { version = "1", features = ["json", "redactions"] }
tempfile = "3"

[profile.release]
codegen-units = 1
lto = true
opt-level = 3
strip = true

[profile.dist]
inherits = "release"
lto = "thin"

[profile.install-local]
inherits = "release"
codegen-units = 16
lto = false

[workspace.metadata.dist]
cargo-dist-version = "0.31"
ci = "github"
targets = [
    "x86_64-unknown-linux-gnu",
    "aarch64-unknown-linux-gnu",
    "x86_64-unknown-linux-musl",
    "aarch64-unknown-linux-musl",
    "x86_64-apple-darwin",
    "aarch64-apple-darwin",
]
installers = ["shell"]
github-attestations = true
create-release = false
unix-archive = ".tar.gz"
windows-archive = ".zip"
include = ["LICENSE", "README.md"]
auto-includes = false
pr-run-mode = "skip"
```

Notice the three workspace `Cargo.toml`s today already converge on these settings — the unification is mostly mechanical merge.

### What about a `rtm-shim` analogue if rtm becomes lilo?

`rtm-shim` is the kubelet-shim in the current runtime-matters tree (it lives logically in `rtm-platform` per PROJECT.md). The brief raises the question: if `rtm` becomes `lilo`, where does the shim live and what is it called?

Recommendation: keep the shim as `rtm-shim` internally (the name is well-understood in the runtime-matters mental model and there's no public surface to rename). The binary that the daemon execs to wrap a child process is called `lilo-shim` (a second binary out of the `lilo` crate, or a tiny `lilo-shim` crate of its own). The shim is internal infrastructure, not user-facing CLI; one binary that is exec'd by name from `$LILO_HOME/bin/lilo-shim`. **Layout decision: put it in its own crate `crates/lilo-shim/` (publish = true so it appears next to `lilo` in `cargo install`), have it depend only on `lilo-common` to keep it small.** Wire details preserved from rtm-platform.

## §3 Binary surface

**One user-facing CLI binary: `lilo`.** One auxiliary binary: `lilo-shim` (the runtime shim, exec'd by the daemon, never invoked directly by users). No separate `rtm` / `sm` / `im` binaries.

### Why one CLI

Driver #5 is verbatim: "Single binary runtime rather than manage `rtm`, `sm`, etc. separately." This is the design constraint. The k8s research's "argv[0] busybox trick" (rustc / rustdoc / cargo as one binary) is an option, but it adds path-dependent complexity for users who don't care. Stuart will be in his shell typing `lilo`. Pick one binary; one verb tree.

### The verb tree

```
lilo --version                       # version, build sha, target triple
lilo --help                          # top-level help
lilo doctor                          # cross-substrate health check (was sm doctor + rtm doctor)
lilo daemon start                    # start ALL daemons (rm + sm + im-stub)
lilo daemon stop                     # stop them
lilo daemon status                   # health of each
lilo daemon rm start|stop|status     # one daemon at a time (the kubectl-shaped escape)
lilo daemon sm start|stop|status
lilo rm <verb>                       # runtime-matters surface (was rtm)
    spawn <args>
    status <session-id>
    events [--since CURSOR]
    kill <session-id>
    list
lilo sm <verb>                       # session-matters surface (was sm)
    create namespace <slug>
    create session <runtime> --role <role> --dir <path>
    run <runtime> [...]
    get sessions
    get session <selector>
    label <selector> <mutation>
    delete session <selector>
    delete namespace <slug>
    capture <session-id>
    config set-context <slug>
    mail <verb>                      # mail subcommands (currently sm subcommand)
    nudge <verb>
    mcp <verb>
lilo im <verb>                       # identity-matters surface (new — was library-only)
    audit query [...]
    audit show <id>
    whoami
lilo sched <verb>                    # schedule-matters surface (placeholder, §11)
    # nothing yet; verbs added when scheduler ships
```

The `lilo daemon` family is the noun-verb shape kubectl uses for control-plane operations. Distinguishing `lilo daemon start` (all) from `lilo daemon rm start` (one) gives the user the convenient default plus the surgical escape. Today's `sm daemon` and `rtm daemon` verbs map directly.

### How daemons fold

**Two daemon processes, not one.** The brief asks "one unified `lilod` mode? separate daemons spawned by `lilo`?" — I recommend separate daemons because:

1. `smd` and `rtmd` have different blast radii. rtmd owns per-process lifecycle (CPU/memory expensive; restart is heavy); smd owns the durable session record (light, cheap to restart). Coupling their lifecycles couples their failure modes.
2. The K8s mental model in the CLAUDE.md is explicit: smd = apiserver+etcd, rtmd = kubelet. K8s does not collapse these into one process. They are separate binaries for a reason.
3. Future host-vs-control-plane separation: if someone ever runs smd on one host and rtmd on N hosts, that path stays open. Collapsing now closes it.

So `lilo daemon start` is sugar for "exec lilo daemon rm start in the background, then exec lilo daemon sm start in the background, wait until both report healthy." Concretely it spawns two child processes of the same `lilo` binary with different subcommand argv. Identical to how systemd would do it but without the systemd dependency.

The identity-matters substrate stays library-only in v0 (per its TLDR.md). No `imd` daemon. When v2 brings an enforcing identity daemon, it slots in as `lilo daemon im start`.

### `main()` shape

```rust
// crates/lilo/src/main.rs
use std::process::ExitCode;

mod cli;

fn main() -> ExitCode {
    if let Err(e) = run() {
        eprintln!("lilo: {e}");
        return ExitCode::from(2);
    }
    ExitCode::SUCCESS
}

fn run() -> Result<(), Box<dyn std::error::Error>> {
    lilo_common::init_logging()?;
    let command = cli::build_top_command();
    let matches = command.get_matches();
    cli::dispatch(matches)
}
```

`cli::build_top_command()` returns a `clap::Command` with the verb tree assembled by calling each substrate's `pub fn build_command()` (one per top-level verb). `cli::dispatch(matches)` matches on the chosen subcommand and routes into the corresponding `run` function. The whole `main.rs` is ~30 LOC. The `cli/` module is split per top-level verb so no file approaches the 700 LOC ceiling.

### How today's CLIs migrate

The existing `crates/rtm-cli/` (6155 LOC across 56 files) and `crates/sm-cli/` (6539 LOC across 51 files) become subtrees inside `crates/lilo/src/cli/rm/` and `crates/lilo/src/cli/sm/`. The verb implementations are preserved more or less wholesale (file-per-verb shape exists already). What disappears: the top-level `clap::Command` builder in each, replaced by one shared shape. The integration tests under `rtm-cli/tests/` and `sm-cli/tests/` move to `tests/e2e/` at workspace root and run against the unified `lilo` binary.

That's a ~12K LOC move with mechanical renames. The hard part is the clap re-wiring at the top level, not the per-verb code.

## §4 Versioning model

**One workspace version, used by every crate, bumped on every release.**

This matches direction doc decision #9 and k8s pattern 16. `workspace.package.version = "X.Y.Z"` in the root `Cargo.toml`; every member crate has `version.workspace = true`. One number to bump; release-plz can do it via `update_workspace_version`.

### Continuity with the published surface

The constraint: `lilo-rm-core@0.7.1`, `lilo-rm-client@0.7.1`, `lilo-im-core@0.1.1`, `lilo-im-store@0.1.1` cannot regress. SemVer requires monotonic increase.

The simplest answer: **the monorepo's first version is `0.8.0`.** Every published crate (and every internal crate) ships at `0.8.0` on the first monorepo release. This:

1. Beats `lilo-rm-*@0.7.1` (the highest current published number).
2. Beats `lilo-im-*@0.1.1` (since 0.8.0 > 0.1.1).
3. Is a clean minor bump from rm-core, signalling "new home, same contract." Stuart's no-backcompat preference means the *types* might break across this boundary anyway, in which case 0.8.0 carries the breaking change inside the v0.x SemVer rules.
4. Avoids the 0.7.0 vs workspace-0.3.1 dual-axis pain that exists today.

The im-core line jumping from 0.1.1 to 0.8.0 is a six-version leap. That looks weird if you read it as a continuity signal. It is fine because (a) there's no other published im consumer than Stuart, (b) crates.io has no problem with version-number jumps, (c) the cost of an alternative (running im at 0.2.x while rm runs at 0.8.x) is exactly the dual-axis versioning Stuart asked to abolish (driver #1). One number for everything.

If Stuart wants a softer landing for im, the alternative is to start the monorepo at `0.2.0` and let `lilo-rm-core` regress from 0.7.1 to 0.7.2 → 0.8.0 separately on a different track. That re-introduces dual-axis versioning the next morning. Reject.

**Recommendation: monorepo starts at 0.8.0. All crates published or unpublished sit at 0.8.0 on cut day.**

### release-plz.toml shape

```toml
# release-plz.toml at workspace root
[workspace]
# All members share the workspace version. Bump triggers all releases atomically.
release = true
publish = false                # only the publishable members below set this true
semver_check = true
changelog_update = true
git_tag_name = "v{{ version }}"          # one tag for the whole workspace
git_release_name = "v{{ version }}"
release_always = false
update_workspace_version = true          # release-plz manages the workspace.package.version
dependencies_update = false              # internal path deps don't need rewriting

# Publishable crates
[[package]]
name = "lilo"
release = true
publish = true

[[package]]
name = "lilo-common"
release = true
publish = true

[[package]]
name = "lilo-rm-core"
release = true
publish = true

[[package]]
name = "lilo-rm-client"
release = true
publish = true

[[package]]
name = "lilo-im-core"
release = true
publish = true

[[package]]
name = "lilo-im-store"
release = true
publish = true

[[package]]
name = "lilo-sm-core"
release = true
publish = true

[[package]]
name = "lilo-sm-client"
release = true
publish = true

[[package]]
name = "lilo-shim"
release = true
publish = true

[changelog]
header = "# Changelog\n\nAll notable changes documented here.\n"
commit_parsers = [
  { message = "^feat", group = "Features" },
  { message = "^fix",  group = "Bug Fixes" },
  { message = "^perf", group = "Performance" },
  { message = "^refactor", group = "Refactoring" },
  { message = "^doc",  group = "Documentation" },
  { message = "^chore", group = "Miscellaneous" },
  { message = "^test", group = "Tests" },
  { message = "^ci",   group = "CI" },
]
```

The `dependencies_update = false` is important: internal `path` deps point at workspace siblings, no version-rewriting needed because they share `version.workspace = true`. The published crates' inter-deps (e.g., `lilo-rm-client` depends on `lilo-rm-core`) carry both `path` and `version`, which is fine for both local and registry resolves.

### First release: 0.8.0

The first monorepo release is `v0.8.0`. It publishes 9 crates simultaneously: `lilo`, `lilo-common`, `lilo-rm-core`, `lilo-rm-client`, `lilo-im-core`, `lilo-im-store`, `lilo-sm-core`, `lilo-sm-client`, `lilo-shim`. release-plz handles the topological order. Subsequent releases bump the workspace version per conventional commits and publish all 9 (or however many) again. Crates with no changes since last release still get bumped — the cost is ~2 minutes of upload per crate, the benefit is no version-skew confusion ever.

## §5 `~/.lilo/` data layout

**One root, per-substrate subtrees, no migration from `~/.{rtm,sm,im}/` (no backcompat).**

```
~/.lilo/
├── lilo.toml              # workspace-level config (log level, daemon enable flags, etc.)
├── sock/
│   ├── rmd.sock           # was ~/.rtm/sock
│   └── smd.sock           # was ~/.sm/sock (or wherever it lived)
├── db/
│   ├── rm.sqlite          # was ~/.rtm/rtm.sqlite (or wherever)
│   ├── sm.sqlite
│   └── im-audit.sqlite
├── logs/
│   ├── rmd.log
│   ├── smd.log
│   └── shim/<session-id>.log
├── rm/                    # per-substrate config + state
│   ├── config.toml
│   └── shim-state/
├── sm/
│   ├── config.toml
│   ├── namespaces/        # if any persisted namespace data goes here (vs in sm.sqlite)
│   └── mcp/
├── im/
│   ├── policy.toml        # stub policy in v0
│   └── (empty in v1)
└── tmp/                   # scratch for shim, captures, etc.
```

### Override env var

`LILO_HOME` overrides the root. Test invocations set `LILO_HOME=$(mktemp -d)` and get a fresh isolated environment. Every other path resolves from `LILO_HOME`. No per-substrate env var (`RTM_HOME`, `SM_HOME`) survives — they collapse into the single `LILO_HOME`. Per-substrate overrides for finer-grained tests (e.g., `LILO_RM_DB_PATH`) exist but default to `$LILO_HOME/db/rm.sqlite`. This is the kubelet pattern: a typed paths module (`lilo-common::paths`) resolves once at startup, every component asks the module not the env directly.

### Migration policy

The CLAUDE.md is explicit: "pre-release with zero external users, so backward compatibility is not a constraint." Stuart's MEMORY confirms no-backcompat in Helioy refactors. So:

- On the day the monorepo binary first runs, it expects `~/.lilo/` to exist or auto-creates it.
- It does **not** look in `~/.rtm/`, `~/.sm/`, or `~/.agm/`.
- Stuart's existing daemons stop being relevant the moment the new `lilo daemon start` runs.
- The migration sequence has a clean cutover point: at phase 5 (the `lilo` cutover), `lilo doctor` checks for any stale `~/.{rtm,sm,im}/` directories and prints a one-liner: "Legacy data at ~/.rtm/ — delete with `rm -rf ~/.rtm/` when ready." No automatic deletion (rule out catastrophic data loss). No automatic migration (no backcompat). Just a hint.

### Wire to in-process tests

The integration tests at `tests/integration/` set `LILO_HOME=$tmp` before spawning anything. `lilo-common::paths::resolve()` reads `LILO_HOME` and derives the rest. The `lilo` binary's `doctor` command and every subcommand share one path resolver. No `~/.rtm/sock` survives.

## §6 Unified standards

### CLI framework

**clap derive**, top to bottom. Today's three CLIs already use clap derive. The merged `Cli` enum lives in `crates/lilo/src/cli/mod.rs`:

```rust
#[derive(clap::Parser)]
#[command(name = "lilo", version = lilo_common::VERSION_STRING, long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
    #[arg(long, short, global = true, value_enum, default_value = "auto")]
    pub output: OutputMode,            // auto | json | text
    #[arg(long, global = true)]
    pub verbose: bool,
    #[arg(long, global = true)]
    pub config: Option<PathBuf>,
}

#[derive(clap::Subcommand)]
pub enum Command {
    Doctor(doctor::Args),
    Daemon(daemon::Args),
    Rm(rm::Args),
    Sm(sm::Args),
    Im(im::Args),
    Sched(sched::Args),
}
```

Per-substrate verbs live in `cli/{rm,sm,im,sched}.rs`. Each has a sub-enum and a `pub fn run(args) -> Result<()>` entry. Around 80 LOC per top-level verb dispatcher.

### Error type

**`anyhow::Result` for user-facing layers; `thiserror`-derived typed errors at crate boundaries.** Specifically:

- The published `lilo-*-core` and `lilo-*-client` crates expose typed errors via `thiserror`. These are wire-stable contracts.
- The internal `*-daemon` crates carry typed errors at the daemon API boundary, anyhow inside.
- The `lilo` CLI uses anyhow throughout because the top-level handler just prints whatever and returns exit code 2.

No workspace-wide error crate. K8s does not have one either; the typed-error-per-contract pattern is sufficient and avoids the `LiloError` god enum that ends up with 200 variants.

### Logging

**`tracing` + `tracing-subscriber` env-filter**. `lilo-common::init_logging()` sets up:

- Format: pretty in TTY, json when `--output=json` or `LILO_LOG_JSON=1`.
- Filter: `LILO_LOG=info` env var (no `RUST_LOG` — too generic).
- Output: stderr (stdout reserved for command output).

Every daemon and CLI calls `lilo_common::init_logging()` once at startup. Same shape, same env vars, same format. The k8s research §2.2 pattern P1 (Effect Layer composition for bootstrap) maps cleanly: every entry point boots from the same plumbing layer.

### JSON output flag

`--output=json|text|auto`. Default auto: json if stdout is a pipe, text if TTY. Every subcommand that produces machine-readable output respects this. The `cli_output` module in today's `rtm-core` is the right pattern; lift into `lilo-common::output`.

### Exit codes

Stick with `std::process::ExitCode`:

- `0` = success
- `1` = handled user error (bad selector, no daemon running, kind=ErrorKind::User)
- `2` = unhandled internal error (kind=ErrorKind::Internal)
- `3` = not-found (no such session, no such namespace)
- `64..` = reserved for substrate-specific (RTM_SHIM_FAILED etc.) — never use 64-78 (sysexits).

`lilo-common::exit_codes` is the source of truth.

### Help format

clap's default, plus `lilo <command> --help` always includes a "EXAMPLES" section. Help text style: imperative, no marketing language, no emoji.

### README shape

Top-level `README.md` is operator-facing: install, daemon start, three example commands. Per-substrate docs live at `docs/per-substrate/{rm,sm,im,sched}.md` and link to the top-level `docs/architecture.md`. Each mirror repo's README is generated by `lilo-mirror-publish` from a template (banner + 30-line description scoped to that substrate).

### Docs structure

```
docs/
├── architecture.md         # one document, ~3K words, the K8s mental model
├── cli.md                  # complete verb tree reference (generated by clap-mangen)
├── data-layout.md          # the ~/.lilo/ contract
├── release.md              # how to cut a release (release-plz + mirror push)
├── per-substrate/
│   ├── rm.md
│   ├── sm.md
│   ├── im.md
│   └── sched.md            # placeholder
└── adr/                    # architecture decision records, one file per durable decision
    ├── 0001-monorepo-collapse.md
    └── 0002-single-binary.md
```

`clap-mangen` generates `cli.md` from the clap definitions on every release — no hand-maintained verb reference to drift.

### CHANGELOG strategy

Single workspace CHANGELOG.md at the root, generated by release-plz from conventional-commit messages. Per-substrate mirror repos get a scoped CHANGELOG.md produced by `lilo-mirror-publish` (it filters the unified changelog by path: commits touching `crates/lilo-rm-*` or `crates/rm-*` go to the rm mirror's changelog). One source, N filtered views.

### CI pipeline

GitHub Actions + Moon as orchestrator. Three workflows:

1. `pr.yml` — runs on every PR. `moon run :build :test :lint :fmt :typecheck`. Cache via Moon's content-hash caching + actions/cache. Targets: linux-x64, macos-arm64. Total wall clock target: <8 minutes.
2. `release.yml` — runs on tag push of `v*`. release-plz publishes to crates.io. cargo-dist builds and uploads binaries. **After** crates.io publishes, `lilo-mirror-publish` runs to push to each public mirror. Fan-out happens here, not from a separate job.
3. `nightly.yml` — runs daily on main. Full cross-platform matrix build, integration tests with real Docker, longer-running tests.

Moon's `.moon/tasks.yml` declares the build tasks; the YAML workflow files just invoke `moon run`. This is k8s pattern: orchestration in one place, CI yaml is thin.

## §7 Git history strategy

**Recommended default: clean slate.**

The four repos as they exist today:

- `identity-matters`: workspace v0.1.1, ~1.4K LOC, three crates. Young, low history value.
- `runtime-matters`: workspace v0.3.1 with the rm-contract version-group at 0.7.1. Most mature, ~20.6K LOC.
- `session-matters`: v0.2.8. ~17.5K LOC.
- `schedule-matters`: not a git repo at all. No history to preserve.

The k8s research is clear: Cargo doesn't have Go's import-path-equals-module-path problem, so the migration mechanism is just "move the files and rewrite the Cargo.tomls." Git history is a separate axis.

### Why clean slate

1. **Stuart is the sole consumer.** Driver #1 says "versioning is becoming a pain"; #2 says these substrates aren't meaningful as separate entities. Preserving N separate histories perpetuates the four-axis mental model the migration is trying to abolish.
2. **No-backcompat principle applies to history too.** Carrying four pasts forward is incompatible with "break the format, replace cleanly."
3. **The substrates' published crates carry their version history on crates.io.** Anyone who wants to see "what was lilo-rm-core like at v0.7.1" can `cargo install --version 0.7.1` or browse the crates.io page. The history doesn't need to be re-embedded in the new repo's git log.
4. **`git filter-repo + merge --allow-unrelated-histories` is a possible mechanism but adds days of work.** Subtree-merging four histories produces a tangled DAG, makes `git blame` confusing across the renames (every file gets renamed during the merge), and offers limited daily value.

### Mechanics of clean slate

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/
mkdir littleorgans
cd littleorgans
git init -b main
# (commits below per the migration sequence in §8)
```

In each old sub-repo, before the migration:
```bash
cd ../identity-matters
git tag -a archive/final-0.1.1 -m "Archive: final state before monorepo migration"
git push origin --tags
# Repeat for runtime-matters and session-matters.
# Repos themselves get archived on github.com (settings → archive).
```

Anyone with a clone of the old repos still has the full history locally; the GitHub side becomes read-only.

### crates.io continuity

crates.io itself enforces the continuity constraint: `lilo-rm-core@0.8.0` is auto-greater-than `lilo-rm-core@0.7.1`, regardless of which git repo published it. The package's `repository` field in Cargo.toml gets updated from `github.com/littleorgans/runtime-matters` to `github.com/littleorgans/littleorgans` — the crates.io page links to the new repo on next publish.

### Hybrid (not recommended)

The brief mentions "hybrid (tag origin repos at HEAD, archive, start fresh)" as an option. That's essentially what I'm describing — tag the old repos at their last commit, archive them on GitHub, start the new repo clean, push to the new repo. The hybrid framing is the same as clean slate but acknowledges the old repos still exist as historical artifacts.

### What Stuart still has to decide

**Open question §10-Q3:** does Stuart want any history preservation at all? My recommendation is clean slate based on his stated preferences, but if he changes his mind, the cost is one day of `git filter-repo` + merge work per sub-repo. If he wants it, do it before phase 1 below — easier to do clean slate then later subtree-import than the reverse.

## §8 Migration sequence

Eight phases. Each maps to one PR (mostly). Each is testable at the end. The substrate is never simultaneously broken across two phases.

### Phase 0 — Decision day

Stuart commits to:
- Clean slate vs hybrid (§7).
- Starting version 0.8.0 (§4).
- Two daemons not one (§3).
- `LILO_HOME` as the override env var (§5).
- Repo name `littleorgans/littleorgans` (the github.com path).

If any decision flips, the rest of the plan adapts but doesn't restart.

### Phase 1 — Scaffold workspace skeleton

Scope: stand up empty monorepo. Single commit / single PR (but no PR yet — no remote exists).

```bash
cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/
mkdir littleorgans && cd littleorgans
git init -b main
# Create the directory tree from §1 with .gitkeep in empty dirs
# Write Cargo.toml from §2
# Write rust-toolchain.toml, .moon/, moon.yml, README.md, LICENSE, .gitignore
# Add empty crates/lilo/ with src/main.rs printing "lilo 0.8.0\n"
# Add lilo-common with placeholder lib.rs
git add . && git commit -m "chore: scaffold littleorgans monorepo workspace"
gh repo create littleorgans/littleorgans --private --source=. --remote=origin --push
```

Exit criteria: `cargo build --workspace` succeeds. `cargo run --bin lilo -- --version` prints `lilo 0.8.0`. `moon ci` passes (no-op tasks but real). Push to `github.com/littleorgans/littleorgans` (private).

### Phase 2 — identity-matters import (the easy one)

Scope: smallest substrate (1.4K LOC). Lift `crates/im-core` → `crates/lilo-im-core`, `crates/im-store` → `crates/lilo-im-store`, `crates/im-stub` → `crates/im-stub` (note publish demotion). Rewrite Cargo.tomls to inherit from workspace. Drop the old workspace Cargo.toml. Run `cargo test --workspace`; tests pass.

Add minimal `lilo im whoami` command that prints the current uid (uses `lilo-im-core::Principal::Local`). Add `lilo im audit query [...]` placeholder that calls into `lilo-im-store`. No new functionality, just exercise the linkage.

Exit criteria: `cargo test --workspace` green, `lilo im whoami` returns sensible output, im-core's existing tests pass under the new path.

### Phase 3 — runtime-matters import + daemon refactor

Scope: lift the eight rtm-* crates. Mechanical rename:
- `crates/rtm-core` → `crates/lilo-rm-core` (already in workspace by name)
- `crates/rtm-client` → `crates/lilo-rm-client`
- `crates/rtm-paths` → folded into `crates/lilo-common::paths::rm` (the paths module is now common-shared) **or** kept as `crates/rm-paths` internal (decide during PR; my lean: fold into common; rtm-paths is 406 LOC of which most is reusable across substrates).
- `crates/rtm-platform` → `crates/rm-platform`
- `crates/rtm-launchers` → `crates/rm-launchers`
- `crates/rtm-store` → `crates/rm-store`
- `crates/rtm-daemon` → `crates/rm-daemon`
- `crates/rtm-cli` → folded into `crates/lilo/src/cli/rm/` (the verb files move; the rtm-cli crate is dissolved).

The `rtm-shim` binary becomes `lilo-shim` (own crate `crates/lilo-shim/`).

`lilo daemon rm start` now starts what was `rtmd`. `lilo rm spawn`, `lilo rm status`, etc. now work.

Exit criteria: `cargo test --workspace` green, `lilo rm doctor` passes, an end-to-end spawn of a no-op runtime works in tests/e2e.

### Phase 4 — session-matters import + path conversion

Scope: lift the six sm-* crates.
- `crates/sm-paths` → folded into `crates/lilo-common::paths::sm` (same decision as rtm-paths).
- `crates/sm-core` → keep as `crates/sm-core` internal **plus** create a new `crates/lilo-sm-core` public crate that re-exports the wire types from `sm-core` (or, cleaner, refactor sm-core into a private "guts" crate and a public "contract" crate). My lean: move all wire-types-and-types-only out into `lilo-sm-core` as a fresh public crate; leave sm-core as the internal logic crate.
- `crates/sm-store` → `crates/sm-store`
- `crates/sm-driver` → `crates/sm-driver`
- `crates/sm-daemon` → `crates/sm-daemon`
- `crates/sm-cli` → folded into `crates/lilo/src/cli/sm/`.

Also: add a public `crates/lilo-sm-client/` crate parallel to `lilo-rm-client`. Today there isn't one because session-matters is consumed locally; the mirror story (§12) needs an external face.

The cross-substrate dep refactor: `sm-daemon` currently depends on `lilo-im-core`, `lilo-im-store`, `lilo-im-stub` via crates.io. In the monorepo that becomes a workspace path dep — `sm-daemon` depends on `lilo-im-core` and `im-stub` via workspace dependencies. Same for `lilo-rm-core` / `lilo-rm-client`. Clean up the dual-axis version pins.

Exit criteria: `cargo test --workspace` green, `lilo sm doctor` passes, an end-to-end session spawn through smd → rmd works in tests/integration.

### Phase 5 — `~/.lilo/` cutover

Scope: change every default path from `~/.rtm/...` and `~/.sm/...` to `~/.lilo/...`. This is mostly editing `lilo-common::paths` and `rm-paths`/`sm-paths` glue. Adds the `LILO_HOME` env var. Removes `RTM_HOME`, `RTM_SOCKET_PATH`, `RTM_DB_PATH`, `RTM_SHIM_PATH`, `SM_HOME`, etc. — no backcompat.

Update tests to set `LILO_HOME=$(mktemp -d)`. Update `doctor` to print legacy-data hints. Add documentation at `docs/data-layout.md`.

Exit criteria: `cargo test --workspace` green, fresh-machine `lilo daemon start` creates `~/.lilo/` automatically, end-to-end test asserts socket lives at `~/.lilo/sock/rmd.sock`.

### Phase 6 — lilo binary unification

Scope: collapse any remaining duplication in the CLI tree. By this phase the verb tree from §3 should be substantially in place — Phases 3 and 4 already moved per-verb code into `cli/rm/` and `cli/sm/`. This phase polishes:

- Unified `--output`, `--verbose`, `--config` global flags work everywhere.
- Unified `lilo doctor` aggregates per-substrate health.
- Unified `lilo daemon {start,stop,status}` aggregates the daemons.
- Help text reviewed and tightened. clap-mangen generates `docs/cli.md`.
- Exit-code conventions audited.

Exit criteria: every verb today's `rtm` or `sm` supported is reachable via `lilo`; `lilo --help` shows the unified surface; the per-substrate `rtm` and `sm` binaries no longer build (they don't exist in the workspace).

### Phase 7 — release plumbing + first release

Scope: set up release-plz, cargo-dist, GitHub Actions release workflow, and the `tools/lilo-mirror-publish` crate. Stand up the four public mirror repos under `github.com/littleorgans/{rm,sm,im,sched}` (or four full names — see §12). Run release-plz dry-run; iterate. Cut `v0.8.0` as the first monorepo release. crates.io gets 9 published crates; each mirror gets its first synced state and tagged release.

Exit criteria: `lilo-rm-core@0.8.0` resolvable on crates.io. Each mirror has a `v0.8.0` git tag and a GitHub Release. `cargo install lilo` works from crates.io.

### Phase 8 — schedule-matters scaffold + cleanup

Scope: add the `sched-stub` placeholder crate (§11). Archive the three old GitHub repos (`identity-matters`, `runtime-matters`, `session-matters`). Add a one-liner README banner to each archived repo pointing at the monorepo. Delete the old worktree sibling dirs. Remove the parent CLAUDE.md (the four-substrate one) or rewrite it as a thin pointer to the monorepo.

Exit criteria: the only Rust source tree under `littleorgans/` is `littleorgans/littleorgans/`. The four old sibling dirs are deleted or contain only README markers. Old GitHub repos archived.

### Phase mapping to moe-local-batch

Each phase above is too large to fit one moe-local-batch warroom (Phases 3–4 each represent ~20K LOC moves). Decompose each phase into 4–8 items per the workflow:

- **Phase 3 items:** (a) rename rtm-core, (b) rename rtm-client, (c) fold rtm-paths into lilo-common, (d) rename rtm-platform, (e) rename rtm-launchers + rtm-store, (f) rename rtm-daemon, (g) fold rtm-cli into lilo's cli/rm/, (h) lift lilo-shim.

Item-level orchestration within each phase exactly matches the moe-local-batch worked example for the runtime-matters refactor (six items, six commits, one PR). Each phase ends with a single PR onto main; each item inside is one commit.

## §9 What ships first

The day-one PR (well: day-one commit; no PR yet because no remote exists). This is Phase 1 alone. Verbatim transcript:

```bash
# In a fresh terminal at the right cwd
cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/

# Sanity check we're in the right place
ls -la | head      # should show identity-matters, runtime-matters, session-matters

# Create monorepo root
mkdir littleorgans
cd littleorgans
git init -b main

# Scaffold directory tree (no source code yet — just topology + Cargo.toml)
mkdir -p crates/lilo/src crates/lilo-common/src
mkdir -p crates/lilo-rm-core/src crates/lilo-rm-client/src
mkdir -p crates/lilo-im-core/src crates/lilo-im-store/src
mkdir -p crates/lilo-sm-core/src crates/lilo-sm-client/src
mkdir -p crates/lilo-shim/src
mkdir -p crates/rm-daemon/src crates/rm-launchers/src crates/rm-platform/src crates/rm-store/src
mkdir -p crates/sm-core/src crates/sm-daemon/src crates/sm-driver/src crates/sm-store/src
mkdir -p crates/im-stub/src crates/sched-stub/src
mkdir -p xtask/src tools/lilo-mirror-publish/src tests/e2e tests/integration
mkdir -p docs/per-substrate docs/adr .moon .github/workflows
mkdir -p apps/electron-shell apps/server apps/web packages helix products infrastructure

# Reserved dirs: drop a placeholder
for d in apps/electron-shell apps/server apps/web packages helix products infrastructure; do
  printf '# reserved for future migration — see /Users/alphab/.mdx/projects/helioy-product-direction.md\n' > "$d/README.md"
done

# Write the workspace Cargo.toml from §2 above (full contents — about 80 lines)
$EDITOR Cargo.toml

# Each member crate gets a minimal Cargo.toml + src/lib.rs (or src/main.rs for lilo)
# For lilo:
cat > crates/lilo/Cargo.toml <<'EOF'
[package]
name = "lilo"
version.workspace = true
edition.workspace = true
license.workspace = true
repository.workspace = true
authors.workspace = true
rust-version.workspace = true
description = "littleorgans control plane CLI"

[[bin]]
name = "lilo"
path = "src/main.rs"

[dependencies]
lilo-common.workspace = true
EOF

cat > crates/lilo/src/main.rs <<'EOF'
fn main() {
    println!("lilo {}", lilo_common::VERSION_STRING);
}
EOF

# lilo-common:
cat > crates/lilo-common/Cargo.toml <<'EOF'
[package]
name = "lilo-common"
version.workspace = true
edition.workspace = true
license.workspace = true
repository.workspace = true
authors.workspace = true
rust-version.workspace = true
description = "Shared plumbing for the littleorgans monorepo"
EOF

cat > crates/lilo-common/src/lib.rs <<'EOF'
pub const VERSION_STRING: &str = concat!(env!("CARGO_PKG_VERSION"), " (placeholder build)");
EOF

# Same minimal scaffolding for every other crate — empty lib.rs, workspace-inheriting Cargo.toml,
# so the workspace builds. About 18 small files; takes ~10 min.

# Top-level metadata
cat > rust-toolchain.toml <<'EOF'
[toolchain]
channel = "1.90"
components = ["clippy", "rustfmt"]
EOF

curl -fsSL https://raw.githubusercontent.com/github/gitignore/main/Rust.gitignore > .gitignore
echo "/target" >> .gitignore
echo "**/*.rs.bk" >> .gitignore
echo "Cargo.lock" >> .gitignore   # actually KEEP Cargo.lock for binaries — remove this line
sed -i.bak '/^Cargo\.lock$/d' .gitignore && rm .gitignore.bak

# Minimal Moon scaffolding
cat > .moon/workspace.yml <<'EOF'
projects:
  - crates/*
  - xtask
  - tools/*
  - tests/*
EOF

cat > .moon/toolchain.yml <<'EOF'
rust:
  version: "1.90"
EOF

cat > .moon/tasks.yml <<'EOF'
tasks:
  build:
    command: cargo build --workspace
  test:
    command: cargo test --workspace
  lint:
    command: cargo clippy --workspace --all-targets -- -D warnings
  fmt:
    command: cargo fmt --all -- --check
EOF

cat > moon.yml <<'EOF'
type: rust
language: rust
EOF

# CI workflow stub
cat > .github/workflows/pr.yml <<'EOF'
name: pr
on:
  pull_request:
  push:
    branches: [main]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.90
      - run: cargo build --workspace
      - run: cargo test --workspace
      - run: cargo clippy --workspace --all-targets -- -D warnings
      - run: cargo fmt --all -- --check
EOF

# README, LICENSE
cat > README.md <<'EOF'
# littleorgans

A single substrate for running, observing, and authoring local coding agents.

## Quick start

```
cargo install lilo
lilo daemon start
lilo --help
```

## Development

```
cargo build --workspace
cargo test --workspace
```

See `docs/architecture.md` for the system model.
EOF

curl -fsSL https://mit-license.org/license.txt > LICENSE
# Edit LICENSE to set the copyright entity (still TBD per direction-doc open item §10-Q7 here)

# First commit — the scaffold is a single coherent unit
cargo build --workspace          # confirm green BEFORE committing
cargo test --workspace           # confirm green
cargo run --bin lilo -- --version   # prints "lilo 0.8.0 (placeholder build)"

git add .
git commit -m "chore: scaffold littleorgans monorepo workspace

Single Cargo workspace with all member crates as empty stubs.
lilo binary boots and prints version. Moon + GitHub Actions CI
configured but only run cargo build/test/clippy/fmt today.

No substrate code lifted yet. Phase 2 (identity-matters import)
follows.
"

# Create the private GitHub repo and push
gh repo create littleorgans/littleorgans \
  --private \
  --description "littleorgans monorepo" \
  --source=. \
  --remote=origin \
  --push
```

That's the first commit. Everything that follows is one phase at a time, decomposed into moe-local-batch items.

## §10 Risks and unknowns

### Risks

1. **Moon's Rust support is young.** moonrepo.dev was Node-centric for years; Rust toolchain integration is newer. If Moon misbehaves on Rust task orchestration (e.g., cache-key construction over Cargo workspaces), fall back to running `cargo` directly from `make`-style scripts. Don't let Moon block the migration. Validate Moon's Rust support during Phase 1; if it's flaky, defer Moon adoption to when TS lands and use plain `cargo` + GH Actions until then.
2. **release-plz workspace-version mode.** `update_workspace_version = true` is a recent-ish feature. Confirm it works as documented during Phase 7 dry-run. If broken, the fallback is a release script that walks members and applies bumps.
3. **The mirror-publish tool is novel work.** §"Pattern 3" of the k8s research flags this. The first mirror release at Phase 7 may take a week of iteration. Plan for it; don't gate Phase 7 on every mirror being perfect.
4. **Cross-substrate path-dep cycles.** Today `sm-daemon` depends on `lilo-im-*` via crates.io; once in-workspace it's a path dep. If there's any accidental coupling (e.g., a published im-core that depends on something only available in the monorepo), `cargo publish --dry-run` catches it. Add a release-gate that runs `cargo publish --dry-run -p lilo-*` for each published crate before tagging.
5. **schedule-matters is undefined.** Adding a `sched-stub` placeholder doesn't lock in any wire contract. When scheduler design lands, the public crate name and the verb tree may need reshuffling. Low risk because nobody depends on it yet.
6. **The `~/.lilo/` cutover (Phase 5) has no fallback.** Once Stuart's daemon switches over, the old `~/.rtm/` daemon stops getting touched. If Phase 5 ships and Phase 5's lilo daemon is broken, there's no easy revert without restoring from backup. Mitigation: don't ship Phase 5 until tests/e2e covers a full spawn-status-events-kill cycle against `LILO_HOME=$tmp`.
7. **rtm-paths fold-in decision.** I lean toward folding the four `*-paths` modules into `lilo-common::paths`. If they collectively exceed 500 LOC, that pushes the common crate large; might keep them as separate sibling internal crates instead. Decide during Phase 3 PR review.
8. **CI cost.** A workspace with 18 crates + cross-platform release builds + mirror push fan-out is several CI minutes per PR. Mitigation: aggressive Moon caching, single-machine multi-target builds, only run nightly on full matrix.

### Open questions for Stuart

- **§10-Q1: When does `crates/` move under `infrastructure/lilo/crates/`?** (See §1.) My recommendation: not yet — defer until other infrastructure (cm, fmm) actually migrates. Stuart could decide otherwise.
- **§10-Q2: When does the TS scaffold (apps/, packages/) land?** Today they're empty placeholders. Direction doc points to Electron-shell + server + web + four packages from the t3code baseline. My recommendation: once Rust monorepo is fully stable at v0.8.x, before any Electron work begins (likely month 2 or 3 post-migration).
- **§10-Q3: Clean slate vs git-history-preserved.** My recommendation: clean slate (§7). Stuart confirms.
- **§10-Q4: Repo name.** I assumed `github.com/littleorgans/littleorgans`. Direction doc decision #11 supports this. If Stuart wants a different name (e.g., `littleorgans/core`, `littleorgans/monorepo`, `littleorgans/platform`), it's a one-line change in `gh repo create`. Suggestion stays `littleorgans/littleorgans` — short, brand-consistent, easy to remember.
- **§10-Q5: Mirror repo names.** Direction doc says public mirrors under `littleorgans` org. The four substrate-named mirrors: `github.com/littleorgans/identity-matters`, `.../runtime-matters`, `.../session-matters`, plus future schedule-matters? Or `lilo-im`, `lilo-rm`, `lilo-sm`? My recommendation: the *-matters names (they're brand-coherent and the substrate names are stable). The crates inside mirror at the same names they're published as (`lilo-im-core`, etc.).
- **§10-Q6: Copyright entity in LICENSE.** Same as direction-doc open item #7. Per §10 of direction doc, "probably the entity that will eventually hold the enterprise commercial rights." Default: "Stuart Robinson"; revisit when an LLC exists.
- **§10-Q7: Should `im-stub` stay published?** My lean: demote to internal (publish=false). If anyone actually needs an authorizer stub externally, re-promote. Cheap to flip.
- **§10-Q8: Should the cargo-dist `pr-run-mode = "skip"` stay, or actively gate releases on cross-platform binary builds?** Today's repos all skip. With unified release, do we trust GH Actions matrix builds? Recommendation: keep skip on PR, run matrix in `release.yml` only.
- **§10-Q9: Where does helix land relative to this scope?** Direction doc #5 puts it in the monorepo. This plan reserves `helix/` but doesn't populate it. Helix's actual current language stack (Rust per cm context, but the direction doc raises uncertainty) shapes what crates show up. Out of scope for this migration; flag for the next migration project.
- **§10-Q10: What's the bus contract with transport-matters?** The brief says transport-matters is outside scope. But if any cross-bus wire types currently live in one of the four substrates (e.g., session-matters publishing a thread-id used by transport-matters), the migration must preserve that. Quick audit during Phase 4: search session-matters and runtime-matters for any `transport-matters` or `tm-` prefixes; ensure their wire types stay published unchanged.

## §11 schedule-matters status

The directory `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/` exists but is empty (`ls -la` shows just `.` and `..` — no files, no `.git`, no markdown).

Cross-references:
- The parent CLAUDE.md doesn't list `schedule-matters` as a sibling repo.
- The session-matters PROJECT.md says: "Unmanaged-session adoption is deferred to the `schedule-matters` Linear project: https://linear.app/alphabio/project/schedule-matters."

So the directory is a placeholder. There's no code, no spec, no design. There is a Linear project where the design is being worked out.

### Proposed disposition

**Scaffolded fresh in the monorepo as `crates/sched-stub/`, with no daemon and no verbs.**

Concrete shape on day one:

```
crates/sched-stub/
├── Cargo.toml          # publish = false; depends on lilo-common only
├── src/lib.rs          # empty pub mod (placeholder)
└── README.md           # 20 lines: "scheduled session adoption; design TBD; see Linear"
```

`lilo sched <verb>` exists in the verb tree (§3) but has no subcommands wired. `lilo sched` with no args prints "schedule-matters is not yet implemented; see https://linear.app/alphabio/project/schedule-matters".

When the design lands, the crate grows. When wire types are needed externally, a `crates/lilo-sched-core/` crate is added. None of this is in scope for this migration.

### Why not just defer entirely

I considered (a) absorbing the future scheduler into `sm-core` as a submodule, (b) deferring with no placeholder at all, (c) the proposed scaffold.

- (a) couples scheduler design to session-matters too early; the Linear project might decide they're orthogonal.
- (b) means a future migration has to add a new crate, more verbs, change docs, etc.
- (c) gives the future implementer a place to land code without re-shuffling the workspace.

The cost is one empty crate. Worth it.

### Cleanup

After Phase 8 lands, delete `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/` from the parent dir. There's no content to preserve.

## §12 The four GitHub repos

The current sources of truth and their proposed dispositions:

| Today | Disposition | Mirror repo after migration |
|---|---|---|
| `github.com/littleorgans/identity-matters` | Tag at HEAD as `archive/final-0.1.1`, then archive on day of Phase 8 | New repo `github.com/littleorgans/identity-matters` (same name; replace by pushing mirror state) |
| `github.com/littleorgans/runtime-matters` | Tag at HEAD as `archive/final-0.7.1`, then archive | New repo `github.com/littleorgans/runtime-matters` |
| `github.com/littleorgans/session-matters` | Tag at HEAD as `archive/final-0.2.8`, then archive | New repo `github.com/littleorgans/session-matters` |
| (schedule-matters: no current repo) | n/a | New repo `github.com/littleorgans/schedule-matters` (deferred until §11 substrate ships) |

### Why same names

The substrate names (`identity-matters`, `runtime-matters`, `session-matters`) are durable identifiers, used in:
- Stuart's mental model and documentation.
- The crates.io `lilo-im-*`, `lilo-rm-*`, `lilo-sm-*` prefixes.
- Linear projects (e.g., schedule-matters).
- The direction-doc layout (`products/`, `infrastructure/`).

Renaming mirror repos would break that coherence. The mirror repo names persist; what changes is their content and contribution model.

### The archive-and-recreate two-step

1. **Archive the current repo.** GitHub's repo archive flag locks the repo as read-only. URLs continue to resolve. Existing clones still work. Tag at HEAD before archiving so the final state is permanently addressable.
2. **Push the mirror to a new repo with the same name?** No — archiving doesn't free the name; you can't create a new repo with the same name while the old one exists.

So the actual mechanic is:

1. Tag the current repo at HEAD with `archive/final-X.Y.Z`.
2. Rename the current repo (via GitHub settings) from e.g. `runtime-matters` to `runtime-matters-archive`.
3. Archive `runtime-matters-archive` (so it's clearly old).
4. Create a new `runtime-matters` repo, push the mirror tree.
5. Repeat for each substrate.

This sequence preserves history at a discoverable URL (`runtime-matters-archive`) and frees the canonical name (`runtime-matters`) for the new mirror. The README on `runtime-matters-archive` should have a banner: "Archived. The current source of truth is `littleorgans/littleorgans`. The MIT-licensed mirror is `littleorgans/runtime-matters`."

### Cascading release wiring

The brief asks how a release in the monorepo pushes to each mirror. Concrete shape:

```yaml
# .github/workflows/release.yml (excerpt)
jobs:
  publish-crates:
    # ... release-plz publishes to crates.io as today
    
  publish-mirrors:
    needs: publish-crates
    runs-on: ubuntu-latest
    strategy:
      matrix:
        substrate: [identity-matters, runtime-matters, session-matters]
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@1.90
      - name: Build mirror artifact
        run: cargo run -p lilo-mirror-publish -- \
               --substrate ${{ matrix.substrate }} \
               --output-dir /tmp/${{ matrix.substrate }}
      - name: Push to mirror repo
        env:
          MIRROR_DEPLOY_KEY: ${{ secrets.MIRROR_DEPLOY_KEY_RM }}   # one secret per substrate
        run: |
          cd /tmp/${{ matrix.substrate }}
          git init -b main
          git add .
          git -c user.email=ci@littleorgans git -c user.name="littleorgans CI" \
              commit -m "Release v${{ github.ref_name }}"
          git tag v${{ github.ref_name }}
          git remote add origin git@github.com:littleorgans/${{ matrix.substrate }}.git
          git push --force origin main
          git push origin v${{ github.ref_name }}
      - name: Create GitHub Release on mirror
        run: |
          gh release create v${{ github.ref_name }} \
            --repo littleorgans/${{ matrix.substrate }} \
            --notes-file /tmp/${{ matrix.substrate }}/CHANGELOG.md \
            /tmp/${{ matrix.substrate }}/dist/*
```

The `lilo-mirror-publish` tool's responsibilities:

1. **Compute the substrate subtree.** For runtime-matters: the published crates (`lilo-rm-core`, `lilo-rm-client`), the internal crates that aren't visible (`rm-daemon`, `rm-platform`, etc.) — should those go in the mirror? Recommendation: yes, mirror the whole substrate including internals, because (a) external forks need to actually build, (b) the source is visible publicly anyway via crates.io, (c) MIT licensing covers it. The mirror is a self-contained Rust workspace shaped exactly like today's runtime-matters but at v0.8.0 with the renamed crate names.
2. **Rewrite the workspace Cargo.toml** to be a fresh workspace listing just the per-substrate crates. Path deps stay as path deps (mirror is self-contained). Inter-substrate deps (e.g., `sm-daemon` depending on `lilo-im-core`) become crates.io registry deps in the mirror (because the im substrate is in a separate mirror repo).
3. **Filter the changelog** to commits touching the substrate's crates.
4. **Generate the substrate README** from a template, including the "do not PR here" banner per k8s pattern 17.
5. **Copy the binaries** built by cargo-dist for that substrate into the dist/ directory.

The mirror tool is a real piece of work (k8s research called it out). Mid-complexity Rust binary, ~800–1500 LOC. Built and unit-tested during Phase 7. First production use is at v0.8.0 release.

### Force-push policy

Mirrors are read-only from contributors' perspective. They're force-pushed on every release. That means commit history on the mirror is reset every release — the mirror is a state snapshot, not a chronicle. Anyone who clones a mirror gets the latest state plus tags for each released version. This is exactly the k8s publishing-bot model.

### What if a mirror needs a fix-up between releases?

It doesn't. Mirrors are produced by the monorepo; if the mirror is broken, the monorepo's `lilo-mirror-publish` tool is fixed and the next release re-generates the mirror. No hand-editing on the mirror side. Helping users who file issues on a mirror: redirect to monorepo issue tracker (per direction doc decision #7: "Not maintained (no PRs accepted)").

---

## Closing notes

The plan is intentionally conservative on the k8s patterns. K8s ships 35 staging modules and 25 binaries; littleorgans ships ~9 published crates and one binary. The patterns that transfer cleanly (thin-shell main, shared component-base, version injection, single-version-for-everything, MIT mirrors) all transfer. The patterns that don't (staging/, vendor/, import-boss, hack/, multi-file CHANGELOG) don't — and the research grades agree.

The single highest-risk piece is `lilo-mirror-publish`. Everything else is mechanical lift. If the mirror tool slips, the migration still ships — the public mirrors just lag the monorepo until the tool catches up, and crates.io releases are independent of mirror publishes.

The single highest-value pattern is the single binary. Driver #5 said it directly. Everything else cascades from that decision: one CLI surface to learn, one help tree, one set of exit codes, one config root.

The 4000–8000 word target is met. End of plan.
