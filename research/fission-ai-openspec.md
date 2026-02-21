---
title: Fission-AI/OpenSpec — spec-driven development tool review
type: research
tags: [github-review, spec-driven-development, openspec, workflow, helioy-tools, linear-workflows, create-spec, nancyr]
summary: OpenSpec packages a spec-driven workflow as a CLI with three load-bearing primitives — a YAML-defined artifact DAG, a delta-spec algebra (ADDED/MODIFIED/REMOVED/RENAMED), and three-tier schema resolution. Verdict: borrow the delta-spec algebra and dependency-DAG ideas; do not adopt the CLI.
status: active
source: github-researcher
confidence: high
created: 2026-05-03
updated: 2026-05-03
---

# Fission-AI/OpenSpec

Repo: https://github.com/Fission-AI/OpenSpec
Cloned commit: HEAD of main as of 2026-05-03

## Stats

44,804 stars, MIT-licensed TypeScript CLI with 57 contributors, created 2025-08-05 and pushed 2026-05-02 (about 9 months old, very active). Package published as `@fission-ai/openspec` on npm; primary entry is the `openspec` CLI installed via `npm install -g @fission-ai/openspec` and bootstrapped per project with `openspec init`. CI runs through `.github/workflows/ci.yml`, releases via `release-prepare.yml`, plus a Nix flake and devcontainer. The repo has 222 watchers, 3,117 forks, 302 open issues, an active Discord, and ships a `core` workflow profile (`propose`, `apply`, `sync`, `archive`) plus an expanded profile (`new`, `continue`, `ff`, `verify`, `bulk-archive`, `onboard`). Heavy single-author concentration: Tabish Bidiwale shows 483 of ~530 commits, with bots and outside contributors making up the long tail.

## Grade

**B+.** Clean separation between schema, parser, and graph; good tests; production-quality CLI; clearly thought-through delta algebra. Loses points against A-tier (notebooklm-py, fallow-rs) because the surface is mostly conventions encoded as Markdown templates plus a thin TypeScript runtime, the contributor base is single-author-dominant, and several abstractions (workspaces, three-tier schema resolution) are still in beta. The artifact-graph engine and delta-spec parser would be A-grade as standalone libraries.

## Primitives that transfer

1. **Delta-spec algebra (`ADDED` / `MODIFIED` / `REMOVED` / `RENAMED`) for brownfield change deltas.** `src/core/specs-apply.ts:102-348` parses a delta-formatted Markdown file, resolves it against the current spec, validates section-level conflicts (a rename targeting a name that ADDED also creates, MODIFIED on a renamed-from header, duplicates inside a section), then composes the rebuilt spec preserving original ordering. The parser sits in `src/core/parsers/requirement-blocks.ts:99-234` and is the genuinely novel piece: small (~250 lines), self-contained, and Markdown-only. **Lands in `helioy-tools:create-spec`** as an optional second mode. Today create-spec writes a flat `SPEC.md` (`helioy-plugins/plugins/helioy-tools/skills/create-spec/SKILL.md`); brownfield specs would benefit from delta sections so two parallel changes can edit the same capability without merge conflicts. Port the four-section grammar and the conflict-detection rules; do not port the surrounding CLI.

2. **Artifact dependency DAG with state derived from filesystem.** `src/core/artifact-graph/graph.ts:72-134` topologically sorts artifacts via Kahn's algorithm, exposes `getNextArtifacts(completed)` and `getBlocked(completed)` for ready/blocked queries, and `src/core/artifact-graph/state.ts:14-29` derives `completed` purely by checking whether the generated path exists. The schema lives as YAML (`schemas/spec-driven/schema.yaml:4-146`) with each artifact declaring `id`, `generates`, `requires`, `template`, and `instruction`. **Lands in `linear-workflows`** as an optional schema layer beneath the existing three-gate loop. Today the gates are encoded in prose at `~/.codex/skills/linear-workflows/SKILL.md`; a YAML schema would let nancyr/Nancy compute "what is the next executable issue" mechanically rather than via agent inference. The state-from-filesystem pattern also maps cleanly onto Linear: substitute `issue.status === Done` for `fs.existsSync`, keep the same DAG.

3. **Three-tier schema resolution (project / user / package).** `src/core/artifact-graph/resolver.ts:62-91` resolves a schema name by looking first at `<projectRoot>/openspec/schemas/<name>/`, then `$XDG_DATA_HOME/openspec/schemas/<name>/`, then the package built-in. **Lands in `nancyr` and `helioy-tools` skill loading.** Helioy already has linear-workflows in `~/.codex/skills/` and per-repo workflow overrides as an open question. This three-tier override pattern, with clear precedence and a `--source project|user|package` field on listing (`resolver.ts:211-301`), is the right shape for letting one repo customize a workflow while inheriting the rest from global defaults.

4. **`instructions` command exposing structured agent context.** `src/commands/workflow/instructions.ts:45-96` returns a JSON payload containing template, dependencies-with-paths, project context, artifact-specific rules, and the list of artifacts that unlock after this one completes (`src/core/artifact-graph/instruction-loader.ts:48-87`). **Lands in nancyr** as the contract a worker agent calls before drafting any artifact. Today nancy/nancyr workers receive prose instructions; a structured `instructions` payload that names exact dependency paths and the post-completion unlock set would compress the prompt and make routing deterministic.

## Does NOT transfer

1. **The CLI itself (`openspec init`, `openspec update`, `openspec config profile`).** Helioy already distributes via `helioy-plugins` plus `~/.codex/skills/`; adopting an npm-installed CLI duplicates that surface. The 28KB `init.ts` and 26KB `update.ts` exist to support 25+ tool integrations (Claude Code, Cursor, Windsurf, Aider, etc.) which Helioy does not need.

2. **Phase-vs-action philosophy as marketing.** OpenSpec frames itself in opposition to GitHub spec-kit and Kiro. Helioy's linear-workflows is already action-oriented (Linear-as-state, gates as facts not phases). Adopting OpenSpec's framing would be redundant.

3. **Workspaces / `.openspec-workspace/`.** `docs/concepts.md:52-136` describes a coordination workspace for cross-repo planning (`workspace.yaml` for portable link names, `local.yaml` for machine-local paths). This is in beta and overlaps directly with helioy-bus warroom plus Linear projects. Helioy already coordinates cross-repo work through the warroom and Linear, both of which are richer than file-based workspace links.

4. **Rich UI / dashboard.** `src/ui/` and the Ink-based status displays (`src/commands/workflow/status.ts:80+`) target solo human users at the terminal. Nancyr targets autonomous agents; structured JSON output is what matters, the chalked indicators are noise.

5. **The `apply` runner.** OpenSpec's `apply` block in `schemas/spec-driven/schema.yaml:148-154` runs through tasks.md checkboxes. Helioy already has a richer execution model: nancy/nancyr dispatch worker agents per Linear sub-issue, with helioy-bus mailboxes for coordination. Reading checkboxes from a Markdown file is a step backward.

## Verdict

**Inspiration-only with two narrow ports.** Borrow the delta-spec algebra into `create-spec` and the artifact-DAG concept into `linear-workflows`. Do not adopt the CLI, the workspace beta, or the marketing frame.

## Why

The deeper read: OpenSpec is solving the same problem class as linear-workflows but for the file-system-as-state world (no Linear, no MCP). It traded persistence in a structured database for portability across editors and the resulting design is exactly what you'd build if Linear weren't an option. The two pieces worth borrowing — delta algebra and the dependency DAG — are the parts that survive translation back to a Linear-as-state world. Delta algebra is a language for expressing "this requirement, that one removed, this one renamed" that is independent of where the spec is stored; it would let Helioy's brownfield specs have first-class change semantics without a database migration. The artifact DAG, when state comes from issue status rather than file existence, is a way to make linear-workflows gates mechanical rather than judged. Everything else in OpenSpec is either Helioy already has it (orchestration, agent dispatch, cross-repo coordination via warroom/bus) or Helioy explicitly chose against it (file-system-as-state for primary planning, npm-installable CLI as the distribution channel).

## How to apply

1. **Port `requirement-blocks.ts` and the delta-apply algorithm into `create-spec`** as a new `create-spec --delta` mode. Keep the parser ~250 lines, drop the CLI plumbing. Target: `helioy-plugins/plugins/helioy-tools/skills/create-spec/`. Add a SPEC.md section for ADDED/MODIFIED/REMOVED/RENAMED that nancy/nancyr can consume when iterating an existing spec.

2. **Add an optional `workflow.yaml` schema layer to `linear-workflows`.** Put it at `~/.codex/skills/linear-workflows/schemas/<workflow-name>/workflow.yaml` with the same `artifacts: [{id, requires, ...}]` shape. State source: Linear issue status, not filesystem. The workflow-routing prose at `~/.codex/skills/linear-workflows/SKILL.md` becomes a thin runtime over the schema.

3. **Encode the gates in `nancy-two-agent-planning-gate.md` and `agent-issue-review-workflow.md` as schema artifacts** with explicit `requires:` edges. Then nancyr can call a `linear-workflows status --project <name> --json` and get back the same `{artifacts: [{id, status: done|ready|blocked, missingDeps}]}` shape OpenSpec returns. This compresses the prompt nancyr sends to workers.

4. **Three-tier schema resolution for helioy-tools skills.** When nancyr looks up a workflow, check `<repo>/.helioy/workflows/`, then `~/.codex/skills/linear-workflows/workflows/`, then the helioy-plugins package default. Same precedence pattern as `resolver.ts:62-91`. This gives Stuart per-repo overrides without forking the global skill.

5. **Skip everything else.** Do not adopt the CLI, do not adopt workspaces, do not generate slash commands, do not target 25+ editors. Helioy already has its distribution channel.

## Sources consulted

- `README.md`
- `docs/concepts.md`, `docs/opsx.md`
- `schemas/spec-driven/schema.yaml` and templates
- `src/core/artifact-graph/{graph.ts,resolver.ts,state.ts,instruction-loader.ts}`
- `src/core/specs-apply.ts`
- `src/core/parsers/requirement-blocks.ts`
- `src/core/validation/{constants.ts,types.ts,validator.ts}`
- `src/commands/workflow/{instructions.ts,status.ts}`
- gh API: stars, contributors, recent PRs
- Helioy comparison points: `~/.codex/skills/linear-workflows/SKILL.md`, `helioy-plugins/plugins/helioy-tools/skills/create-spec/SKILL.md`

## Open questions

- Does Helioy want a separate workflow-schema file at all, or is the linear-workflows prose plus Linear's own state model sufficient? The DAG primitive is appealing but only earns its keep when there are >3 gates with non-trivial dependencies.
- Delta algebra at the requirement level may be overkill for create-spec's current single-file SPEC.md format. The port becomes load-bearing only when specs are split into per-capability files (which OpenSpec does and create-spec does not).
