---
title: pbakaus/impeccable — one skill, 23 commands, multi-harness fan-out
type: research
tags: [claude-code, skills, plugin-architecture, command-taxonomy, transport-matters, manicure, frontend-design]
summary: One SKILL.md routes 23 sub-commands via a categorized table and reference/ docs; pin.mjs fans the same skill out to 11 harness directories.
status: active
source: github-researcher
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Repo Stats

- Author: Paul Bakaus (`pbakaus`).
- Stars: 22,408. Created 2025-11-16, ~5.5 months old. Apache 2.0.
- Primary language JavaScript / Bun runtime; Node engine `>=18`.
- LOC, all tracked text files: **229,366** (includes `bun.lock` 94k and minified vendor JS).
  - Skill payload alone (SKILL.md + 35 reference docs + scripts + metadata): ~6,800 LOC.
- Tests: 17 test files in `tests/` covering anti-pattern detection, framework fixtures, live-iteration server, build, CLI, Windows path handling.
- CI: `.github/workflows/ci.yml` runs `bun run test` and `bun run build` on push/PR to main.
- Distribution: hybrid — `npx impeccable skills install` downloads a versioned bundle from `impeccable.style`; also a Claude Code marketplace plugin in `.claude-plugin/`.

## Calibrated Grade: B+

Sits at the same tier as obra/superpowers. Rationale against the established scale:

- **Above graphify (B):** Real CI, real test suite (17 files), versioned skill release pipeline, multi-harness installer, working browser extension and live-iteration server. Not a prototype.
- **Above superpowers (B+) for craft, but ties for pattern transfer:** superpowers wins on installation slickness via marketplaces; impeccable wins on actually shipping a non-trivial runtime (`live.mjs` HMR, `detect-antipatterns` browser+node), versioned bundle download, and harness-agnostic install. Equal in giving Helioy two or three transferable primitives.
- **Below notebooklm-py / mngr (A−):** Single-domain (frontend design). The architecture choices serve that domain well, but the skill scaffolding is thinner than mngr's structured workflow vocabulary. Several reference docs lean into prescriptive aesthetic taste rather than reusable harness primitives.

The 22k stars are a marketing-and-niche-fit outcome. Discount them when grading. The grade is the engineering, and it's B+ work.

## Skill Taxonomy: One Skill, 23 Commands, Five Categories

The plugin manifest (`.claude-plugin/plugin.json:9`) declares exactly one skill: `impeccable`, version 3.0.4. Every user-facing command is a sub-command of that single skill, dispatched by `SKILL.md` based on the first argument word.

### The single skill

`source/skills/impeccable/SKILL.md` is a 178-line routing document. The frontmatter (`SKILL.md:1-9`) declares `name: impeccable`, an exhaustive `description` listing every verb the skill responds to, `argument-hint: "[{{command_hint}}] [target]"`, and `allowed-tools: Bash(npx impeccable *)`. There is no per-command frontmatter file; the skill IS the command set.

### The 23 commands and their categories

Declared canonically in two places that must agree:

1. The Markdown table at `SKILL.md:132-156` (rendered to the user as the command menu when no argument is passed; see routing rule 1 at `SKILL.md:162`).
2. The `VALID_COMMANDS` array in `source/skills/impeccable/scripts/pin.mjs:34-39`.

Five orthogonal categories, picked for verb intent:

| Category | Commands | Count |
|---|---|---|
| Build | `craft`, `shape`, `teach`, `document`, `extract` | 5 |
| Evaluate | `critique`, `audit` | 2 |
| Refine | `polish`, `bolder`, `quieter`, `distill`, `harden`, `onboard` | 6 |
| Enhance | `animate`, `colorize`, `typeset`, `layout`, `delight`, `overdrive` | 6 |
| Fix | `clarify`, `adapt`, `optimize` | 3 |
| Iterate | `live` | 1 |

That is 23. Plus two management commands `pin` / `unpin` (`SKILL.md:158`, scripted via `pin.mjs`) which are not counted as design verbs.

### Layout convention

Flat namespace. Every command name is one word, lowercase, verb form. There is no `polish-card` or `audit:perf` sub-namespacing. Categories are descriptive metadata in the routing table, not part of the invocation path. `{{command_prefix}}impeccable <command> [target]` is the only call shape.

### Hierarchy: routing, not nesting

Hierarchy is implemented through document loading, not directory structure:

- Top-level: `SKILL.md` itself (gates, shared design laws, routing rules).
- Per-command: `reference/<command>.md` (35 files in `reference/`, 23 user-invokable plus 12 shared support docs like `heuristics-scoring.md`, `cognitive-load.md`, `color-and-contrast.md`, `typography.md`, `personas.md`, `brand.md`, `product.md`).
- Routing logic: `SKILL.md:160-168` ("Routing rules"). Three branches: no arg → render menu; first word matches → load that reference; else → general invocation with shared laws.

Sub-references are pulled in by other references (e.g. `reference/critique.md:25` reads `cognitive-load.md`, `:35` reads `heuristics-scoring.md`). The 12 shared docs are libraries, not commands, and never appear in the routing table.

### Pin/unpin: per-harness fan-out without owning a registry

`scripts/pin.mjs:24-27` enumerates 11 harness directory names: `.claude .cursor .gemini .codex .agents .trae .trae-cn .pi .opencode .kiro .rovodev`. Pinning a command writes a stub SKILL.md (with `<!-- impeccable-pinned-skill -->` marker, `pin.mjs:43`) into every harness dir that already contains an impeccable install (`pin.mjs:73-77`). Unpin only removes files containing the marker (`pin.mjs:166-171`), so user skills are safe.

## Three Transferable Primitives

### 1. Routing-table SKILL.md as the command index — for **manicure / transport-matters**

A single SKILL.md can fan out to N sub-commands by declaring a routing table and parking implementation in `reference/<verb>.md`. The table at `SKILL.md:132-156` doubles as: (a) the menu rendered to the user on bare invocation, (b) the dispatch table read by the LLM at `SKILL.md:160-168`, (c) the documentation surface, and (d) the source of truth that `pin.mjs:34-39` mirrors. One file declares all three meanings.

For transport-matters, where the surface area is "ferry payloads between agents/systems," this is the right shape. A `transport` skill with verbs like `route`, `relay`, `broadcast`, `inspect`, `replay`, `schedule`, `seal` (or whatever the message-bus API ends up being) lives as one SKILL.md plus per-verb references. Keep verbs orthogonal, one word each, categorized by intent (move / observe / transform / govern). Resist the urge to namespace; flat verbs scale to 25 cleanly when the routing table holds the structure.

### 2. Pin-style fan-out installer with a content marker — for **helioy-plugins**

`pin.mjs:43` plants `<!-- impeccable-pinned-skill -->` inside every generated SKILL.md, then `pin.mjs:166-171` only deletes files containing that marker. This is a clean answer to "how do I install something into someone else's directory and still safely uninstall it later." The discovery loop (`pin.mjs:73-78`) is also notable: scan for harness dirs that already contain the parent install, write only into those, never seed a harness the user has not opted into.

helioy-plugins should adopt both behaviors when distributing skills across `.claude`, `.cursor`, etc. The marker pattern beats a sidecar manifest because the file IS its own provenance record.

### 3. Three-state preflight gate as a single emitted line — for **nancyr** and **cm**

`SKILL.md:13-32` defines five named gates (Context / Product / Command / Craft / Image) and requires the agent to emit a single deterministic line before any mutation:

```
IMPECCABLE_PREFLIGHT: context=pass product=pass command_reference=pass shape=pass|not_required image_gate=pass|skipped:<reason> mutation=open
```

This is a cheap structural protocol: the agent declares its precondition state in machine-readable form, the orchestrator can grep for it, and divergence between intended and actual state becomes an assertion rather than a vibe check. nancyr can adopt the same shape for agent-handoff preflight (each Rust task posts a `NANCYR_PREFLIGHT:` line to the event log before doing work). cm can use it as a recall-completeness signal (`CM_PRECALL: scope=pass freshness=pass conflict=none`).

The win is the format itself. One line, named gates, `pass | <reason>` per gate. No JSON, no schema, greppable.

## Skip List

- **Aesthetic prescriptions in `SKILL.md:69-128`** ("Shared design laws," anti-pattern bans). High craft, but they are taste declarations specific to frontend design. Not transferable to a transport / orchestration / memory layer. Cite them as evidence that single-skill plugins can be opinionated without fragmenting; do not import the rules.
- **The `live.mjs` HMR variant browser** (`scripts/live-server.mjs`, `scripts/live-inject.mjs`). Impressive engineering for an interactive design loop. Helioy has no surface that needs browser-based variant generation. Skip unless attention-matters grows a visual editing layer.
- **The hosted `impeccable.style` API** (`bin/commands/skills.mjs:18`, `:34-37`). The CLI fetches the command list from a hosted endpoint. Helioy should not depend on a hosted service for tool discovery. Local, file-based discovery only.
- **Multi-version skill bundle download via fetch + zip extract** (`bin/commands/skills.mjs` `downloadAndExtractBundle`). Solves a problem helioy-plugins solves differently (marketplaces). Not a regression, just a different distribution story.
- **The 12 shared support docs as a pattern in itself**. Splitting `cognitive-load.md`, `heuristics-scoring.md`, etc. out of command files makes sense for a domain with shared evaluation rubrics. transport-matters likely will not benefit; routing verbs share less common substrate than design verbs do.

## Sources Consulted

- `.claude-plugin/plugin.json` — single-skill plugin manifest, version 3.0.4.
- `source/skills/impeccable/SKILL.md` — routing table, gates, shared laws.
- `source/skills/impeccable/scripts/pin.mjs` — multi-harness fan-out, marker-based safe uninstall.
- `source/skills/impeccable/scripts/command-metadata.json` — descriptions consumed by pinned-skill generator.
- `source/skills/impeccable/scripts/load-context.mjs` — PRODUCT.md / DESIGN.md loader pattern.
- `source/skills/impeccable/reference/{audit,critique}.md` — command implementation shape; sub-reference loading.
- `bin/cli.js`, `bin/commands/skills.mjs` — installer architecture, hosted-API dependency.
- `.github/workflows/ci.yml` — CI scope.
- `package.json` — distribution shape, exports.

## Open Questions

- How does the routing table stay in sync between `SKILL.md:132-156` and `pin.mjs:34-39`? Manual today; would benefit from a single source generator.
- Does the `reference/<command>.md` lazy-load actually save tokens in practice, or do most invocations preload the parent SKILL.md plus reference plus 1-2 shared docs? Worth measuring before adopting the pattern in transport-matters.
- The `argument-hint: "[{{command_hint}}] [target]"` template suggests a build step substitutes per-harness prefixes. Where is that templating done? Likely `scripts/build.js` — out of scope for this review but relevant if helioy-plugins copies the pattern.
