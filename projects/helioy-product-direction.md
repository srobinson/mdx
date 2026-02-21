---
title: Helioy Product Direction (v0)
type: project-direction
tags: [helioy, littleorgans, product-direction, monorepo, moon, electron, matters-family, helix, public-mirrors, distribution, living-doc]
summary: The shape of Helioy as a product. littleorgans is the integrated Electron app; every *-matters and Helix migrate into one polyglot monorepo (Moon) under a private repo; each release cascades into per-*-matters releases on public MIT mirrors under a new `littleorgans` GitHub org. Standalone Electron binaries per product *-matters from the same source. Source of decisions: conversation with Stuart on 2026-05-16. Updates frequently.
status: active
confidence: high
created: 2026-05-16
updated: 2026-05-16
---

# Helioy Product Direction (v0)

## Names and what they mean

- **Helioy** is the project. **Internal only.** Zero public visibility in v0. Reserved for a future enterprise tier. Does not appear on the marketing site, in package names, in user-visible UI, or in public mirror copyrights. Continues to exist as the strategic frame, the cm scope (`global/project:helioy`), the internal name, and the umbrella.
- **littleorgans** is the integrated product. THE Electron app. Closed source. **The only public face.**
- **littleorgans.com** is the marketing domain. **Owned by Stuart** (confirmed 2026-05-16). The public web surface for the product, the *-matters mirrors, and eventually the enterprise sign-up funnel.
- **littleorgans GitHub org** is **owned by Stuart** (confirmed 2026-05-16). Holds the *-matters mirror repos plus the private monorepo (mixed-visibility). Brand locked across both registries (domain + org).
- **\*-matters family** is the set of components inside the monorepo: products (transport-matters, runtime-matters) and infrastructure (cm, am, fmm, helioy-bus, knowledge-matters, others). Each one also has a public mirror under the `littleorgans` org.
- **Helix** is the central agent that orchestrates the cognitive organs. It moves into the monorepo with the rest of the family. Its presence inside littleorgans.app is **config and/or route-driven**; nothing is always-present. Visual model deferred (see open items).

The previous framing — three Helioy.app icons coexisting on the dock — is retired. There is one default install: **littleorgans.app**. Standalone product apps exist for users who want only one product.

## TL;DR — ten decisions

| # | Decision | Date |
| --- | --- | --- |
| 1 | littleorgans is the integrated product Electron app; everything Helioy is one repo, one release. | 2026-05-16 |
| 2 | All *-matters (products + infrastructure) and Helix migrate into the littleorgans monorepo. Single source of truth. | 2026-05-16 |
| 3 | Polyglot build tool: **Moon** (moonrepo.dev). Rust + TypeScript + Python all first-class. | 2026-05-16 |
| 4 | View model: workspaces with peel-off; main workspace can peel into other workspaces with easy return. Concrete design **deferred**. | 2026-05-16 |
| 5 | Helix moves into the monorepo too. Internal consumer of cm/am/fmm/helioy-bus via workspace deps, not via published packages. | 2026-05-16 |
| 6 | Release flow: the littleorgans repo cuts one main release per version. That release cascades into per-*-matters releases on each public mirror, each mirror running its own release workflow. | 2026-05-16 |
| 7 | Public mirror license: **MIT**. Calling-card open source. Anyone free to fork. Not maintained (no PRs accepted). | 2026-05-16 |
| 8 | Standalone product *-matters ship as separate Electron binaries (transport-matters.app, runtime-matters.app, ...). Same source as littleorgans.app, built with a `--surface=...` switch. Per-product bundleId, icon, userData, auto-update channel. | 2026-05-16 |
| 9 | Versioning: **one version for everything** in v0 (littleorgans v1.2.3 = every artifact at v1.2.3). Door open to per-artifact semver later. | 2026-05-16 |
| 10 | Existing public *-matters repos (under `srobinson`) are **archived**. New mirrors live under the new `littleorgans` GitHub org. Clean slate; very little continuity to preserve. | 2026-05-16 |
| 11 | The private monorepo lives in the **same `littleorgans` GitHub org** as the public mirrors. Mixed-visibility org: one private source, many public mirrors as siblings. | 2026-05-16 |
| 12 | **Helioy as a public brand has zero visibility in v0.** Reserved for a future enterprise tier. Nothing user-visible or public-facing carries the Helioy name. The name continues internally (cm scope, strategic framing, file-memory). | 2026-05-16 |
| 13 | **Helix surface inside littleorgans.app is config and/or route-driven.** No always-present element. Concrete visual model deferred. Rules out the always-present chat sidecar pattern. | 2026-05-16 |
| 14 | **littleorgans.com domain is owned** by Stuart. Brand domain locked. Marketing site, mirror docs, and eventual enterprise funnel all live here. | 2026-05-16 |
| 15 | **`littleorgans` GitHub org is owned** by Stuart. Brand locked across both registries. Private monorepo and public mirrors both live here. | 2026-05-16 |
| 16 | **Package-registry claim sweep complete.** `littleorgans` published as a placeholder on npm, PyPI, and crates.io. Combined with the domain and GitHub org, the brand is locked across all five registries. | 2026-05-16 |

## The shape, in one diagram

```
littleorgans monorepo (PRIVATE)
├── apps/
│   ├── electron-shell/        the Electron 40+ shell, one binary regardless of surface
│   ├── server/                Effect backbone (Bun + Node dual)
│   └── web/                   single React 19 bundle for browser + Electron renderer
├── products/                  the user-facing *-matters
│   ├── transport-matters/
│   ├── runtime-matters/
│   └── (future products)
├── infrastructure/            the *-matters that are libraries / CLIs
│   ├── context-matters/       (cm)
│   ├── attention-matters/     (am)
│   ├── fmm/
│   ├── helioy-bus/
│   └── knowledge-matters/
├── helix/                     the orchestrator
├── packages/                  shared baseline primitives
│   ├── contracts/             Effect Schema spine
│   ├── shared/                stateless utilities
│   ├── client-runtime/        renderer-side Effect Atoms
│   └── design/                tokens, base-ui wrappers, Header + StatusBar
└── .moon/                     build orchestration

cascades on release →

littleorgans org (PUBLIC, MIT, read-only)
├── transport-matters/    mirror, release workflow, transport-matters.app binary
├── runtime-matters/      mirror, release workflow, runtime-matters.app binary
├── cm/                   mirror, release workflow, cm CLI binary
├── am/                   mirror, release workflow, am CLI binary
├── fmm/                  mirror, release workflow, fmm CLI binary
├── helioy-bus/           mirror, release workflow, helioy-bus CLI binary
├── knowledge-matters/    mirror, release workflow
└── (others as added)
```

Note: directory names are illustrative. Actual layout follows the migration plan (open item).

## Release flow

Single trigger, multi-target output.

1. A release is cut in the private littleorgans monorepo with a version tag (e.g., `v0.1.0`).
2. The Moon-driven CI builds:
   - **littleorgans.app** integrated Electron binary
   - **N standalone Electron binaries**, one per product *-matters (transport-matters.app, runtime-matters.app, ...)
   - **M CLI binaries**, one per infrastructure *-matters (cm, am, fmm, helioy-bus, ...)
   - **Helix runtime** as an internal artifact (not separately released; consumed by all of the above)
3. For each *-matters in the family, a release workflow runs:
   - Pushes the relevant source subtree to the corresponding public mirror under `littleorgans` org
   - Tags the mirror with `v0.1.0`
   - Creates a GitHub Release on the mirror with the binary(ies) for that *-matters
   - Updates the mirror's README and CHANGELOG with the v0.1.0 notes scoped to that *-matters
4. From outside, each mirror looks like a real active project with regular releases.

## What still survives from the locked baseline spec

`helioy-electron-baseline.md` §7 locked twelve baseline parameters on 2026-05-15. Most survive this direction shift intact:

- Q1 Effect Schema everywhere — unchanged
- Q2 fd3 + stdin-JSON bootstrap fallback — unchanged
- Q5 WebSocket + Effect RPC — unchanged
- Q6 Atom-first renderer — unchanged
- Q8 File-based routing — unchanged
- Q9 React Compiler in dev and CI — unchanged
- Q10 Effect 4 beta + patches — unchanged
- Q11 Shared primary hue, Geist vendored, Lucide everywhere — unchanged
- Q12 Header + StatusBar primitives — unchanged (Header probably grows the workspace selector)

The 35 numbered patterns in §2–§5 of the baseline spec are pattern citations; they survive regardless of monorepo topology.

## What needs revision in the baseline spec

Three Qs and three sections need updating against this direction:

| Section / Q | What changes |
| --- | --- |
| §1 blueprint | Replaces the three-package single-app shape with the littleorgans monorepo tree above. The `apps/` directory now holds `electron-shell` + `server` + `web` (still the t3code three-app shape, just renamed). New top-level dirs: `products/`, `infrastructure/`, `helix/`. New `packages/design/`. |
| Q3 shell topology | "One shell, three packaged identities" becomes "one Electron shell binary, ONE integrated identity (littleorgans.app) plus N standalone product identities (one Electron binary per product *-matters, same source, `--surface=...` switch)." |
| Q4 auto-update target | Still GitHub Releases, but per *-matters mirror under the `littleorgans` org, plus one for the integrated littleorgans.app. The integrated binary's update channel is independent from the standalones'. |
| Q7 backend topology | The `EnvironmentConnection` seam still holds, but the renderer now has multiple "products" inside it as workspaces. Each workspace may have its own `EnvironmentConnection`, or share one with the others. Open item. |
| §8 application to surfaces | The "three surfaces" framing is replaced. There is one integrated surface (littleorgans) hosting multiple product workspaces, plus N standalone product binaries from the same source. transport-matters is the first product workspace; runtime-matters is next. |
| §9 next steps | Replaces "stand up @helioy/baseline" with "stand up littleorgans monorepo with Moon, then migrate". |

The baseline spec will be revised when this direction doc stabilises further.

## Open items

Numbered for tracking. Each is genuinely undecided and needs another pass.

1. **View model specifics.** Workspaces with peel-off is the direction. What is the visual model? A left sidebar of organs/products? A top tab strip? A workspace switcher in the title bar? Deferred until we start designing the shell. (#13 narrows this: nothing always-present.)
2. **Helix visual model.** Decision #13 says config-and-route-driven, no always-present element. The concrete renderer pattern (a `/helix/...` route? A summonable command palette? An optional persistent panel that the user toggles?) is still open.
3. **Migration sequencing.** Which *-matters migrate first? Likely order: empty monorepo scaffold first, then one trivial product to validate the polyglot story, then a real product (transport-matters per existing need), then infrastructure as they are needed.
4. **What is in the mirror beyond code.** Code obviously. Binary releases attached to GitHub Releases — yes. Docs subdirectory? Release notes scoped to the *-matters? CHANGELOG file? Marketing landing page? README badges? Define the "good mirror" spec.
5. **CI shape.** Moon + cascading per-*-matters release workflows + cross-language testing + Electron build matrix. The CI plan is non-trivial. Probably GitHub Actions with Moon as the orchestrator.
6. **Per-artifact naming and branding.** "transport-matters" is the product. Is the Electron binary called "Transport Matters.app" or "transport-matters.app"? Per-product icons. Per-product colour treatment within the shared design system.
7. **Public copyright + attribution string.** Public mirrors are MIT, but the copyright line ("Copyright (c) 2026 ____") needs an entity. Stuart Robinson personally? An LLC? Cannot be "Helioy" per #12. Probably the entity that will eventually hold the enterprise commercial rights.
8. **Existing dependency consumers.** Anyone currently pinning `srobinson/cm` etc. needs to know to switch sources. A migration announcement is small but worth doing.
9. **Helix's Rust footprint.** Helix today is Rust-shaped per existing cm context. Moon handles Rust crates natively. Confirm Helix's actual current language stack before committing to Moon-as-primary.
10. **Internal-vs-external naming hygiene.** Per #12, Helioy stays internal. Need a quick rule for what is permitted in user-visible strings, package names, error messages, README copy, mirror commit messages. Probably: nothing public mentions Helioy. The cm scope `global/project:helioy` stays internal.

## What this direction enables

A few things become possible that were not before:

- **Atomic releases**: one version number across the whole family. "Are you on v0.1.0?" has one answer.
- **Tight cross-component refactors**: a change in cm that affects how Helix consumes context is one PR in one repo, not a coordinated multi-repo dance.
- **Single CI**: one pipeline runs polyglot lint + test + build + package for everything. No fan-out across repos.
- **Open-source-as-distribution**: each *-matters has a public face without taking on a maintenance burden. The mirrors are marketing surface; the monorepo is the work.
- **One brand surface**: every Helioy thing the public sees lives under the `littleorgans` org. Coherent identity.

## What this direction costs

- **Polyglot CI is real work**: Moon helps, but cross-language test + build for Rust + TS + Python + Electron in one pipeline is a several-week setup.
- **No tactical multi-repo escape hatches**: if something needs to ship out-of-band from littleorgans, there is no good way to do it. Everything ties to the monorepo's release cadence.
- **Larger repo means slower clones, larger CI machines, more careful PR scoping.** Not a problem for solo-builder Stuart now; will become real if the team grows past one.
- **Existing community / stargazers around `srobinson/cm` etc. are walked away from.** Small loss per #10 in decisions table; worth naming.
- **The "you can fork" mirror promise needs to be real.** If the mirror is a git push from the monorepo, can a fork actually `cargo build` against it? Each mirror must be self-buildable, not require monorepo context. This is a non-trivial CI constraint.

## Next moves (recommended order)

1. Settle open item #1 (where the private monorepo lives) and #8 (org availability). 5-minute decisions; both are blocking.
2. Settle open item #2 (Helix's visibility). Shapes the renderer.
3. Sketch open item #4 (migration sequence) at a high level. Pick first 2 to migrate.
4. Revise `~/.mdx/research/helioy-electron-baseline.md` against this direction (§1, Q3, Q4, Q7, §8, §9).
5. Stand up the empty littleorgans monorepo: Moon scaffolding, three apps + four packages (`contracts`, `shared`, `client-runtime`, `design`), one trivial product workspace as a smoke test.
6. Migrate first real product (likely transport-matters) end-to-end. Validate that the mirror generation + standalone Electron build + integrated view all work.
7. Iterate from there.

## Source

This document captures a conversation with Stuart on 2026-05-16. Each decision came one-at-a-time via `AskUserQuestion`. The shape preserves Stuart's framing rather than reinterpreting it. Related: `~/.mdx/research/helioy-electron-baseline.md` (the locked baseline spec, partially superseded by §"What needs revision in the baseline spec" above).
