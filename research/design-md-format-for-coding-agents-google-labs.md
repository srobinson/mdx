---
title: DESIGN.md — agent-first format for describing a visual identity
type: research
tags: [agent-first, cli, design-tokens, spec, markdown-frontmatter, zod, linter, google-labs]
summary: Google Labs' DESIGN.md is a hybrid YAML-frontmatter-plus-prose format plus a TypeScript CLI/linter that gives coding agents a persistent, structured understanding of a design system.
status: active
source: github-researcher
confidence: high
created: 2026-04-22
updated: 2026-04-22
---

# DESIGN.md (google-labs-code/design.md)

## Executive Summary

DESIGN.md is a format specification and accompanying TypeScript CLI from Google Labs Code (the Stitch team) that describes a visual identity for coding agents. The format pairs YAML frontmatter design tokens (machine-normative) with markdown prose design rationale (why and how). The CLI lints token references, checks WCAG contrast, exports to Tailwind and DTCG, and emits the spec itself as structured context for agent prompts.

## Repo Facts

- URL: https://github.com/google-labs-code/design.md
- Homepage: https://stitch.withgoogle.com/docs/design-md/specification
- Stars / forks: 190 / 19
- License: Apache-2.0
- Primary language: TypeScript (Bun runtime, Turbo monorepo)
- Created: 2026-04-10. First commit last week. Active as of 2026-04-21.
- Format version: `alpha`. Expect churn.
- Contributors: 5 named (chelseayerong, David East, nitagoogler, Sam El-Husseini, xkxx). Classic small-team Google Labs drop.
- Package: `@google/design.md` (npm)

## Core Concept — quoting the README

> "A format specification for describing a visual identity to coding agents. DESIGN.md gives agents a persistent, structured understanding of a design system."

> "Tokens give agents exact values. Prose tells them *why* those values exist and how to apply them."

It is simultaneously:
1. A **file format** (YAML frontmatter + markdown sections with a canonical section order)
2. A **linter/CLI** (`@google/design.md`) that validates tokens, diffs versions, exports to Tailwind/DTCG
3. A **prompt pattern** — the `spec` command outputs the full specification as markdown/JSON for injection into agent prompts
4. An agent-first CLI philosophy embodied in its own source (see `.agents/skills/`)

## Architecture / Mechanics

### The format (docs/spec.md)

Two layers. YAML frontmatter (or fenced yaml code blocks) carries normative machine-readable tokens. Markdown body carries prose rationale, organized into eight canonical sections with a fixed order: Overview, Colors, Typography, Layout, Elevation & Depth, Shapes, Components, Do's and Don'ts. Sections are optional but must appear in order if present.

Token types:
- **Color** — `#` hex (sRGB)
- **Dimension** — number + unit, spec-standard units are `px`/`em`/`rem` (CLI tolerates the wider CSS set)
- **Token reference** — `{path.to.token}` (e.g. `{colors.primary}`) with composite refs permitted inside `components`
- **Typography** — object with `fontFamily`, `fontSize`, `fontWeight`, `lineHeight`, `letterSpacing`, `fontFeature`, `fontVariation`
- **Components** — map of component name to a fixed sub-token set (`backgroundColor`, `textColor`, `typography`, `rounded`, `padding`, `size`, `height`, `width`); variants are flat sibling entries (`button-primary`, `button-primary-hover`)

Unknown content rules are explicit: unknown sections and token names are preserved; duplicate section headings are fatal; unknown component properties accepted with warning.

### The CLI (packages/cli)

Four subcommands, built on `citty`. All commands accept stdin via `-` and default to JSON output.

- `lint` — parses YAML + markdown, resolves tokens, runs 8 lint rules, returns structured findings
- `diff` — token-level change detection between two DESIGN.md files; exit 1 on regression
- `export` — emits Tailwind theme config or DTCG `tokens.json`
- `spec` — dumps the spec itself as markdown or JSON, optionally with the live rules table appended. This is the "context packaging" command — designed to be piped directly into agent prompts.

### Lint rules (packages/cli/src/linter/linter/rules/)

| Rule | Severity | Checks |
|---|---|---|
| `broken-ref` | error | `{colors.primary}` that resolves to nothing |
| `missing-primary` | warning | no `primary` color defined |
| `contrast-ratio` | warning | component fg/bg below WCAG AA 4.5:1 |
| `orphaned-tokens` | warning | colors defined but never referenced |
| `missing-sections` | info | spacing/rounded missing when other tokens present |
| `missing-typography` | warning | colors present but no typography tokens |
| `section-order` | warning | sections out of canonical order |
| `token-summary` | info | per-section token counts |

### Pipeline

Source file → `ParserHandler` (unified/remark + `yaml` package, extracts frontmatter *and* fenced yaml blocks, merges them, errors on duplicate top-level sections) → `ModelHandler` (resolves token refs, builds a flat `symbolTable`, computes WCAG luminance per color) → `runLinter` (pure function over resolved state) → `TailwindEmitterHandler` / `DtcgEmitterHandler`. Each stage is its own `Spec + Handler` pair.

### Code architecture — the "Spec and Handler" pattern

The `.agents/skills/typed-service-contracts/SKILL.md` encodes the style explicitly. Every unit of work has:
- A `spec.ts` — Zod schemas for input, output, and an exhaustive discriminated-union error code enum; a `Result = Success | Failure` type; an interface with an `execute(input): Result` signature.
- A `handler.ts` — a class implementing the interface. Never throws. Catches all internal errors and maps them to the `Result` failure variant with `code`, `message`, optional `suggestion`, and `recoverable: boolean`.

This is parse-don't-validate + Result monad + vertical-slice architecture, done rigorously. Every directory under `linter/` (parser, model, linter, tailwind, dtcg, fixer) follows it.

## Notable Patterns Worth Remembering

1. **Single source of truth for a spec.** `spec-config.yaml` is the normative config. `docs/spec.md` and the CLI's lint rules are both generated from it by `bun run spec:gen`. The spec document and the enforcement mechanism cannot drift.

2. **The `spec` CLI command as prompt-context packaging.** Instead of asking humans to paste format docs into prompts, the tool emits its own specification via `npx @google/design.md spec --rules`. Agents can self-bootstrap by running a CLI. This is the same move as `cx_recall` or `fmm_file_outline` — the tool teaches the agent what it accepts.

3. **Hybrid normative-tokens + rationale-prose file.** The YAML is authoritative; prose gives the agent taste. Prose uses descriptive names ("Boston Clay") that correspond to systematic token names (`tertiary`). The agent reads prose for style decisions when no explicit token applies.

4. **Recoverable errors as a first-class field.** The error schema includes `recoverable: boolean`. Parse failures with `recoverable: true` return an empty design system and a warning finding rather than throwing. The consumer never has to try/catch; the contract is total.

5. **Agent DX scoring rubric.** `.agents/skills/agent-dx-cli-scale/SKILL.md` is a 7-axis 0–21 rubric for how agent-friendly any CLI is: Machine-Readable Output, Raw Payload Input, Schema Introspection, Context Window Discipline, Input Hardening, Safety Rails, Agent Knowledge Packaging. Independently reusable on any tool — including Helioy's own MCP surfaces.

6. **`preEvaluate` grades findings into an edit menu.** Findings are partitioned into `fixes` (errors), `improvements` (warnings), and `suggestions` (info) — a fix-plan an agent can iterate on rather than a flat log to parse.

7. **Dual YAML embedding modes.** Frontmatter *or* fenced ```yaml code blocks, merged, with duplicate top-level keys erroring. Lets the format degrade gracefully into renderers that do not support frontmatter.

8. **TDD skill and Ink skill shipped in-repo.** `.agents/skills/` carries `tdd`, `ink`, `agent-dx-cli-scale`, and `typed-service-contracts`. The repo is its own agent onboarding kit. Tracked via `skills-lock.json` with content hashes — skill dependencies are pinned like any other dep.

## Relevance to Helioy — concrete intersections

### helioy-tools plugin / MCP tools (direct methodological fit)
The Spec-and-Handler pattern is what every MCP tool in `helioy-tools` already wants to be. Each `cx_*`, `am_*`, `fmm_*`, `md_*` tool is an execute(input) → Result surface. Formalizing Zod specs + exhaustive error codes + `recoverable` would make the plugin's failure modes legible to agents, which is the difference between "tool failed" and "tool failed, here is the fix". Worth reading `spec.ts`/`handler.ts` pairs under `packages/cli/src/linter/*/` as templates.

### The `spec` command ↔ Helioy's self-documenting tools
Helioy MCP tools already take this shape implicitly (tool descriptions, parameter schemas). The explicit move design.md makes — a CLI subcommand that outputs "inject this into your agent context" — is one Helioy could copy. Example: `fmm spec`, `cm spec`, `am spec` commands that emit usage rules agents should load at session start. Right now that responsibility is scattered across SKILL.md files and MCP server instructions.

### create-spec skill ↔ DESIGN.md format
`helioy-tools:create-spec` produces SPEC.md. The DESIGN.md shape (YAML frontmatter for machine-normative fields, canonical markdown sections for rationale, unknown-content tolerance rules) is a workable template for SPEC.md if Stuart ever wants it lintable or diffable. Specifically: a SPEC.md frontmatter with `name`, `goals[]`, `out_of_scope[]`, `acceptance_criteria[]` and a canonical body-section order would let nancyr verify a spec before dispatching work.

### markdown-matters / ~/.mdx
DESIGN.md's parser treats YAML frontmatter as the normative layer and H2 sections as the navigational layer. This is exactly the structure markdown-matters indexes. A `md_design_check` tool (contrast, broken refs, section-order) could be a future plugin command for any frontmattered markdown in ~/.mdx that declares a `type:`.

### Agent DX CLI rubric ↔ helioy-tools audit
The 7-axis rubric in `agent-dx-cli-scale/SKILL.md` is directly applicable to every Helioy tool: do cm/am/fmm/md all return structured JSON? Accept raw payloads? Ship context files? Have dry-runs? Stuart could use this rubric as a one-page self-audit. Specifically flagged: "Schema Introspection" (score 3 requires live runtime schemas) and "Agent Knowledge Packaging" (score 3 requires versioned skills — helioy-plugins already does this).

### "Stuart owns what and why, Claude owns how"
The tokens-vs-prose split encodes exactly this. Tokens are the normative *what* (hex values, font sizes). Prose is the *why* (brand personality, when to apply). The agent handles the *how* (generating a UI from both). The format itself is a template for this operating model.

### Non-intersections
- Not relevant to attention-matters (no geometric memory angle)
- Not relevant to helioy-bus (no inter-agent messaging)
- Not relevant to nancy/nancyr orchestration (not a multi-agent tool)

## Dependencies Worth Noting

- **citty** — command definition framework, also used by nuxt tooling. Clean alternative to commander/yargs.
- **unified + remark-parse + remark-frontmatter + unist-util-visit + mdast types** — the whole stack markdown-matters already has opinions about.
- **yaml** (eemeli) — permissive YAML 1.2 parser.
- **zod 3.x** — schema parsing, error-code enums, input/output typing.
- **@json-render/core + @json-render/ink** — Vercel Labs experiment for rendering JSON specs to UI. Not load-bearing here but suggests the Google Labs team is eyeing JSON-driven UI generation as a companion.
- **tailwindcss** (devDep) — Tailwind is an emitter target, not a runtime dep.

## Verdict

**Borrow aggressively, don't adopt wholesale.** The DESIGN.md format itself only matters if Helioy generates UI, which is not a current thread. The valuable assets are the *patterns* — all transplantable:

1. The Spec-and-Handler architecture as a standard for helioy-tools MCP handlers. This is the single highest-leverage takeaway. Read `.agents/skills/typed-service-contracts/SKILL.md` and treat it as a design doc.
2. The Agent DX 7-axis rubric as a one-shot audit for every CLI and MCP tool in the ecosystem.
3. The `spec` subcommand pattern — a tool that emits its own contract as agent context — as a mechanism for every helioy-tools surface.
4. The single-source-of-truth spec-config generating both docs and enforcement — reusable any time Helioy ships a format.
5. The tokens-plus-prose hybrid as a template for SPEC.md, task specs, or anywhere Stuart needs machine-normative fields alongside human rationale.

Not useful: the actual DESIGN.md format, the Tailwind/DTCG emitters, the WCAG checks. Those are domain-specific to visual design.

## Sources Consulted

- `README.md` — format overview, CLI reference, linting rules
- `docs/spec.md` — full generated spec
- `packages/cli/src/linter/spec-config.yaml` — normative config
- `packages/cli/src/linter/lint.ts` — top-level lint pipeline
- `packages/cli/src/linter/parser/handler.ts` — remark + yaml parser
- `packages/cli/src/linter/model/spec.ts` — resolved token types, validation helpers
- `packages/cli/src/linter/linter/runner.ts` — rules runner + `preEvaluate` grading
- `packages/cli/src/commands/lint.ts`, `spec.ts` — citty subcommand shape
- `packages/cli/src/index.ts` — CLI entry
- `packages/cli/package.json` — dependency graph
- `.agents/skills/typed-service-contracts/SKILL.md` — architecture standard
- `.agents/skills/agent-dx-cli-scale/SKILL.md` — 7-axis scoring rubric
- `.agents/skills/tdd/SKILL.md`, `.agents/skills/ink/SKILL.md` — supporting skills
- `examples/atmospheric-glass/DESIGN.md` — real-world token count and shape
- `skills-lock.json`, `CONTRIBUTING.md`, `git log` — repo metadata

## Open Questions

- Whether the Stitch product feeds its own outputs into this format, or whether this is a standalone spec push. (Homepage points at Stitch docs — worth a follow-up if Helioy ever wants UI generation.)
- Whether `@google/design.md` has hit npm yet (package.json declares `publishConfig` pointing at wombat-dressing-room; version `0.1.1`).
- Whether there is a corresponding SPEC.md or CODE.md format from the same team. The naming suggests a family.
