---
title: littleorgans monorepo migration — shared brief for MoE planning panel
type: brief
tags: [littleorgans, monorepo, migration, moe, brief]
summary: Canonical brief consumed by two parallel expert agents (Claude and Codex) producing independent migration plans. Includes drivers, current state, constraints, references, expected output shape.
status: active
created: 2026-05-25
---

# Brief: littleorgans monorepo migration plan

## What you are doing

You are one of two parallel expert agents producing an INDEPENDENT migration plan for collapsing four Rust sub-repos into a single monorepo at `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`. A peer agent on a different model runtime is producing their own plan in parallel; you do not see their work. Stuart will synthesise both into a merged proposal.

You are not constrained to agree with the other agent or to adopt assumed defaults. Your job is to think it through yourself and produce a complete plan with stated tradeoffs.

## The drivers (Stuart's stated reasons, verbatim)

1. **Versioning is becoming a pain.** Coordinating per-crate releases (`lilo-rm-core@0.7.1`, `lilo-rm-client@0.7.1`, `lilo-im-core@0.1.1`, `lilo-im-store@0.1.1`) across separate repos with separate release-plz configs is breaking down. Dual-axis versioning in runtime-matters (workspace `0.3.1` vs the `rm-contract` version-group at `0.7.1`) compounds it.
2. **None of the `littleorgans/*-matters` family are meaningful as separate entities.** identity-matters, runtime-matters, session-matters, schedule-matters are facets of one substrate, not standalone products.
3. **One set of standards for releases/docs/help/CLI etc.** Today each repo has its own conventions. Want unified.
4. **Stop polluting `$HOME`.** Today's `~/.rtm/`, `~/.sm/`, `~/.agm/` (and probably more) are scattered. Target: single `~/.lilo/` namespace covering sockets, config, sqlite databases, logs.
5. **Single binary runtime rather than manage `rtm`, `sm`, etc. separately.** Today there are multiple CLIs (`rtm`, `sm`) and multiple daemons (`rtmd`, `smd`). One binary instead.

## Current state on disk

Working directory: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/`

The parent dir is NOT a git repo. It contains four sub-repos as siblings:

| Sub-repo | Status | Crates of note | Published on crates.io |
|---|---|---|---|
| `identity-matters/` | git, remote `github.com/littleorgans/identity-matters`. Workspace v0.1.1. release-plz `publish=false` at workspace level. | `lilo-im-core`, `lilo-im-stub`, `lilo-im-store` | `lilo-im-core@0.1.1`, `lilo-im-store@0.1.1` |
| `runtime-matters/` | git, remote `github.com/littleorgans/runtime-matters`. Workspace v0.3.1, plus `version_group = "rm-contract"` pinning `lilo-rm-*` at 0.7.1. Released 0.7.1 recently. | `rtm-core`, `rtm-client`, `rtm-paths`, `rtm-platform`, `rtm-launchers`, `rtm-store`, `rtm-daemon`, `rtm-cli` | `lilo-rm-core@0.7.1`, `lilo-rm-client@0.7.1` |
| `session-matters/` | git, remote `github.com/littleorgans/session-matters`. Released 0.2.8 most recently. CLI `sm`, daemon `smd`. | (inspect yourself) | (inspect yourself) |
| `schedule-matters/` | **Not a git repo.** Just a directory. Inspect to determine state and propose disposition. | (inspect yourself) | (inspect yourself) |

Each sub-repo has its own `CLAUDE.md` / `TLDR.md` / `PROJECT.md`. Read them. Worktree sibling dirs (`*-matters-worktrees`) exist but are empty.

`transport-matters` is **outside** this directory today, per the parent CLAUDE.md. It is **not in scope** for this migration; mention only if your plan touches the bus contract with it.

## Constraints and preferences from Stuart's memory

- **No backcompat in Helioy refactors.** Stuart is the sole consumer; break the format, replace cleanly. No deprecation windows. Applies to source layout, runtime data layout, CLI surface, everything.
- **DRY, zero tolerance.** Migration must not produce parallel implementations. Old paths get deleted, not left as transitional. A PR that introduces duplication is not complete.
- **Refactoring thresholds.** No file >700 LOC. No function >~150 LOC. Holds for new code in the monorepo.
- **Crate naming.** Public published crates use `lilo-` prefix. Internal-only crates may drop it. The published namespace `lilo-*` on crates.io is owned by Stuart and continues from current versions; SemVer must monotonically increase.
- **Polyglot future.** Rust + TypeScript + Python all first-class. Moon (moonrepo.dev) is the chosen build orchestrator. The four sub-repos today are pure Rust; the monorepo target shape will eventually include Electron + web + Python tooling.
- **The crates.io publish surface decision is parked.** Clean-slate vs preserve-history for git is parked; you should propose a default but flag it as still-to-decide.
- **One repo, multiple visibilities.** Per the direction doc, the monorepo lives at `github.com/littleorgans/<repo-name-TBD>` as a private repo in the same org that holds the future public MIT mirrors. The repo name is not yet decided; propose one.

## Reference documents (READ THESE)

1. `~/.mdx/projects/helioy-product-direction.md` — locks the umbrella direction. Sixteen decisions including: littleorgans monorepo, Moon, MIT public mirrors, cascading release, single version, single GitHub org, brand-locked across registries. The target tree there (`apps/`, `products/`, `infrastructure/`, `helix/`, `packages/`) is the future shape including components NOT in this migration. Your plan covers the narrower current scope.
2. `~/.mdx/research/kubernetes-monorepo-layout-patterns.md` — fresh research on how kubernetes/kubernetes lays out its codebase and what transfers to a four-substrate Rust monorepo. Read this before designing the layout. The applicability section is the load-bearing part for our case.
3. `~/.mdx/research/helioy-electron-baseline.md` — baseline spec, partially superseded by the direction doc but relevant for the Electron / TS / Python side of the monorepo.
4. Each sub-repo's root markdown (`CLAUDE.md` / `TLDR.md` / `PROJECT.md`).
5. `~/.mdx/workflows/moe-local-batch.md` — execution workflow for landing N small refactors. Your plan should decompose into phases that this workflow (or a similar one) can execute later, as a series of small commits per phase.

## What your plan must cover

Number these sections in your output exactly. Skip nothing. If a section is unanswerable, write "Open question — see §10".

1. **Target directory layout** for `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`. Concrete tree. Top-level dirs, where each current sub-repo lands, where Moon configs live, where shared crates go, where TS and Python slots reserve. Justify against k8s research.

2. **Cargo workspace shape.** Single workspace or workspace-of-workspaces? Crate naming convention (`lilo-*` public surface, internal-only naming). How `rtm-shim` lives if `rtm` becomes `lilo`. Whether the `lilo-rm-core` / `lilo-rm-client` publish-pair stays a pair, collapses, or expands. Future TS package shape (npm workspaces? pnpm? whatever Moon prefers). Python package slot (uv? poetry? PEP 621?).

3. **Binary surface.** What binaries does the monorepo produce? Single multi-call `lilo`? Multiple? How the CLI subcommands fold current `rtm` and `sm` verbs. How daemons fold (one unified `lilod` mode? separate daemons spawned by `lilo`?). What the binary's `main` looks like at a high level. State this clearly because it shapes everything else.

4. **Versioning model.** One workspace version for everything? How that interacts with the existing crates.io publish surface (`lilo-rm-core@0.7.1` etc. cannot regress). What `release-plz.toml` looks like for the unified workspace. What the first monorepo release version is. Whether the v0.7.x line continues for publish crates while the workspace runs a separate version, or whether everything aligns.

5. **`~/.lilo/` data layout.** Directory tree under `~/.lilo/`. Subdirs per substrate? Flat? Sockets, sqlite databases, logs, config files. How today's `~/.rtm/`, `~/.sm/`, etc. map. Migration policy: no backcompat means existing user state can be wiped; how to communicate that and at what point in the migration. Whether the daemon supports an env-var override for the root path (for tests).

6. **Unified standards.** Specific calls on: CLI framework (clap derive base? what does the `Cli` enum look like for the merged `lilo` command?), error type (one workspace error crate? thiserror per crate?), logging (`tracing-subscriber` config), JSON output flag, exit codes, help format, README shape, docs structure, CHANGELOG strategy, CI pipeline (GitHub Actions + Moon).

7. **Git history strategy.** Either preserve per-subtree (mechanics: `git subtree add` vs `git filter-repo` + merge with `--allow-unrelated-histories`), or clean slate (mechanics + crates.io continuity), or hybrid (tag origin repos at HEAD, archive, start fresh). State your recommended default and why. Flag what Stuart still has to decide.

8. **Migration sequence.** Numbered phases. Each phase: scope, exit criteria, what can be tested at end. Land-by-land sequence so the substrate is never broken for more than one phase. Specifically: where Moon scaffolding lands, where each sub-repo lands (and in what order), where `lilo` binary first appears, where `~/.lilo/` cutover happens. Aim for phases that map to single PRs.

9. **What ships first.** The single concrete first commit/PR you would land tomorrow morning. Be specific: `cd /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/`, `mkdir littleorgans && cd littleorgans && git init`, then... fill in the rest.

10. **Risks and unknowns.** What can go wrong, what you couldn't decide without more input. Explicit open questions Stuart must answer before phase N.

11. **schedule-matters status.** It is not a git repo. Inspect it (`ls -la /Users/alphab/Dev/LLM/DEV/helioy/littleorgans/schedule-matters/`, read any markdown there). Propose disposition: scaffolded fresh in the monorepo, deferred, absorbed into session-matters, dropped.

12. **The four GitHub repos.** Per direction doc, public repos at `littleorgans` org become MIT mirrors pushed from the monorepo on release. But those repos ARE the current sources of truth. Propose disposition for `github.com/littleorgans/{identity,runtime,session}-matters`: archive on day of migration, repurpose as mirrors, delete. State the cascading-release wiring shape (does a release in the monorepo push to each mirror? how?).

## Output

Write your plan to:
- `/Users/alphab/.mdx/projects/littleorgans-monorepo-migration--claude.md` if you are running on the Claude side, OR
- `/Users/alphab/.mdx/projects/littleorgans-monorepo-migration--codex.md` if you are running on the Codex side.

Your launching prompt will tell you which side you are on. Use this frontmatter:

```yaml
---
title: littleorgans monorepo migration — <yourside> independent plan
type: project-plan
tags: [littleorgans, monorepo, migration, moon, brainstorm, <yourside>]
summary: <one paragraph summary of your plan's load-bearing decisions>
status: draft
source: <yourside>
confidence: <high|medium|low>
created: <today's date>
---
```

Target length 4000-8000 words. Concrete file paths, command lines, Cargo.toml snippets, directory trees where useful. Honest about tradeoffs. If you can't decide something, say so and put it in §10.

The aim is a plan another engineer could execute, not a wishlist.

## How to work

- Read the references first (§"Reference documents" above).
- Inspect the actual sub-repos. `fmm` is available; use it for structural questions (`.fmm.db` exists at the littleorgans level). Don't reread huge files; spawn a research subagent or use fmm tools.
- Spend at least one pass on each section. Don't dash-and-fill.
- Write the artifact. Save it. End.
- Do NOT push to any remote. Do NOT modify any code in the sub-repos. Plan-only.
- Independent work. You do not see the peer agent's artifact and you should not try to find it.
