# Helioy Excalidraw Specs

Status: draft
Date: 2026-04-27

## Purpose

Specification for the visual diagrams that illustrate the Helioy ecosystem on helioy.com and elsewhere. The diagrams are vision/thesis renderings, not current-state inventories. They earn their place by arguing the autocatalytic-closure thesis through anatomy and motion, not by labeling boxes.

## Diagram Set

Master plus drill-downs. Open count.

| ID | Title | Purpose |
|----|-------|---------|
| MASTER | The Helioy Cell | Hero overview. Cell anatomy, organelles, manicure cockpit, host, sidecars, runtime-catalog, closure-matters loop. |
| DD1 | The Helix↔AM Dialogue | Two-channel exchange. Sync read/write plus triggered reasoning loop. Mathematical translation at the boundary. |
| DD2 | The Cell Membrane | transport-matters and token-matters as paired sidecars. Kill-switch flow. Respawn-with-summary. |
| DD3 | runtime-matters and runtime-catalog | Community sync down, PR up. Ready-to-go vs JIT runtime composition. Profile curation via the human plus Claude/Codex companion. |
| DD7 | Closure | Catalytic ring made fully visible. What each adapter produces, what consumes it, why removing one breaks the loop. closure-matters drives the evolutionary feedback into runtime-matters. |

## Component Inventory

The matters family rendered in the master.

### External

- **runtime-catalog**: community-maintained super-catalog of skills, MCP servers, prompts, agent profiles. runtime-matters syncs from it. User-requested additions create a branch and PR pushed back to origin.

### Manicure cockpit (top band of the canvas)

The Electron app that the human uses to operate Helioy. World-class delivery, code quality, attention to UX. Contains:

- **workflow-matters**: launcher. Defines workflow patterns.
- **orchestration-matters**: launcher. Decides which agents/cells instantiate for a workflow.
- **runtime-matters**: composer. Produces ready-to-go or JIT runtimes consumed by the launchers.
- **closure-matters**: evolutionary engine. Observes operational signals from the cell. Diagnoses, hypothesizes, tests, adopts mutations. Writes back into runtime-matters genome (skills, MCP servers, prompts, agent.md segments).
- **Owner figure**: the human. Curates runtime-matters profiles via Claude/Codex acting as their companion through skills.

Manicure is rendered as a top cockpit row. Arrows fan downward to capabilities.

### Host band

Claude Code, Codex, or another CLI. Launched by manicure with a runtime composed by runtime-matters. Demote to iconic treatment if the composition crowds.

### Cell membrane sidecars (paired bands hugging the cell)

- **transport-matters**: wire-level proxy. Intercepts API traffic between the host CLI and the LLM provider. Curates payloads through a deterministic pipeline.
- **token-matters**: token-budget sidecar. Realtime usage monitor. User-configurable ceilings trigger trimming, compaction, summarization. Kill switch respawns the CLI with a summarized context if the kill boundary is exceeded by N tokens. The 150k effective ceiling is configurable per model context window. Surfaces config and profile panels, realtime and historical graphs, mode history, tokens saved.

### Cell interior

- **Helix**: central synthesis engine. Proxy LLM that curates on read and write. Unified API across the adapters. Synthesizes one briefing from many sources.
- **attention-matters (AM)**: privileged position adjacent to Helix. Geometric memory on the S³ hypersphere. Two-channel dialogue with Helix:
  1. Synchronous read/write for context delivery.
  2. Triggered reasoning conversation (cron or similar) where Helix initiates dialogue with AM to reason over latest writes and formulate insights.
  Boundary carries mathematical translation, not text.
- **context-matters (cm)**: better representation of decisions. Distilled entries.
- **markdown-matters (mdm)**: better representation of documentation. Scoped sections.
- **frontmatter-matters (fmm)**: better representation of code. Topology.
- **knowledge-matters (km)**: better representation of relations. Triples.
- **history-matters**: better representation of past sessions. SQLite archive of prior Claude/Codex conversations, mineable by Helix.

Five adapters orbit Helix. AM sits adjacent with the prominent two-channel rendering.

### Out of the diagrams

helioy-bus, warroom, nancy. Current implementations of orchestration, not vision-aligned, not product-ready.

## Layout Decisions

| Decision | Choice |
|---|---|
| Diagram count | Master plus drill-downs, open count |
| Use case | Visually stunning, hero-grade |
| Aspect | Landscape 16:9 primary, square 1:1 crop |
| Title (master) | "The Helioy Cell" |
| Owner rendering | Lives inside manicure |
| Host band | Shown above cell, iconic if crowded |
| Adapter arrangement | AM privileged adjacent to Helix, five other adapters orbit |
| Catalytic ring | Subtle ring plus one or two exemplar edges in static export. Pulse animation reserved for the web-rendered version. |
| runtime-catalog placement | Top-left external. Sync down, PR up. |
| Soon vs shipped | Equal treatment. Vision diagram, no tier visual. |
| Sidecars | Twin bands: transport-matters and token-matters |
| Doctrine annotations in master | None. 65% boundary becomes token-matters enforcement. CRITIC becomes closure-matters. |
| Evidence artifacts in master | None. Save for drill-downs. |
| Cell membrane shape | Organic curve, biological |
| Background | Light cream / off-white |

## Helix↔AM Channel Detail

The relationship is dialogic, not read-only.

- Channel 1 (synchronous): Helix recall pulls AM context for the current task. Helix save writes perturbations back to AM.
- Channel 2 (asynchronous reasoning): triggered by cron or signal. Helix initiates a conversation with AM to reason over recent writes, formulate meaningful insights, and update the manifold accordingly.
- Both channels respect AM's mathematical nature. Helix translates ideas into AM's geometric representation (quaternion positions, geodesics, curvature) when feeding AM, and reads geometric structure back when synthesizing.

## closure-matters Detail

Feedback engine that closes the evolutionary loop.

```
operational signals (token-matters, history-matters, cm)
  → closure-matters (observe, diagnose, hypothesize, test, adopt)
  → writes back into runtime-matters genome
  → optionally PRs upstream to runtime-catalog
```

closure-matters supersedes the earlier "CRITIC distributed in infrastructure" framing from `identity/docs.llm/1010.THE_CRITIC.md`. It is now a first-class component.

## Naming

- `transport-matters` is the wire-level proxy. The repo currently named "manicure" will be renamed to transport-matters.
- `manicure` is the human-facing Electron cockpit app.

## Drill-Down Specs

### DD1: The Helix↔AM Dialogue

Renders the two channels distinctly. Channel 1 as a steady operational pulse. Channel 2 as a deeper periodic reasoning loop with a trigger marker. Boundary annotation showing the mathematical translation (concept → quaternion → SLERP → curvature → manifold update).

### DD2: The Cell Membrane

Twin sidecars in detail. transport-matters payload-curation pipeline (strip tools, truncate system parts, rewrite descriptions, drop thinking blocks). token-matters thresholds (warn, hard stop, eviction, kill switch). Respawn-with-summary trace.

### DD3: runtime-matters and runtime-catalog

Community super-catalog upstream. Sync down to local runtime-matters. User curation via Claude/Codex companion. PR up to origin. Profile composition (capability + instruction + hooks + MCP + settings) producing fingerprinted runtime builds. Ready-to-go vs JIT delivery paths.

### DD7: Closure

The autocatalytic ring rendered with full catalytic edges. For each adjacent pair: what one organelle produces that another consumes. closure-matters watching from the cockpit, signaling mutations into runtime-matters. The RAF graph as the hero, with annotations that map the diagram to RAF theory (Hordijk and Steel) and to Dittrich's Chemical Organisation Theory.

## Open Items

- Color palette: read `references/color-palette.md` from the excalidraw-diagram skill before generation. Override only if a Helioy-specific brand palette is provided.
- Visual aesthetic: organic biological shapes, light cream background, geometric clarity inside organelles.
- Animated web version of the master with pulsing catalytic ring is deferred. Static Excalidraw renders the ring as subtle plus exemplar edges.
- Whether to add identity/docs.llm as a node: omitted unless requested.
- Drill-downs beyond 1, 2, 3, 7: not planned. The Adapters drill-down (each as "better representation of X") and the Evolutionary Stack drill-down were considered and deferred.

## Decision Log

Single-letter answers from the brainstorm session, 2026-04-27.

| Q | Answer |
|---|--------|
| Q1 (count) | Master plus drill-downs, open count |
| Q2 (use case) | Visually stunning, hero-grade |
| Q3 (aspect) | D — landscape primary plus square crop |
| Q4 (Helix↔AM) | A with two workflows: sync R/W plus triggered reasoning conversation |
| Q5 (Owner) | C-leaning-D, resolved as: Owner lives inside manicure |
| Q6 (Host band) | A, iconic if crowded |
| Q7 (runtime-matters) | Composer of ready-to-go or JIT runtimes |
| Q7b (workflow/orchestration) | Launchers consuming runtime-matters |
| Q8 (orchestration layer) | A revised: surfaced through manicure, not contained |
| Q8b (runtime-catalog) | Community super-catalog, sync down, PR up |
| Q9 (manicure rendering) | A — top cockpit row, arrows fan down |
| Q10 (cell interior) | B — AM privileged adjacent to Helix |
| Q11 (catalytic ring) | C plus D — subtle ring plus exemplar edges in static, pulse in web |
| Q12 (runtime-catalog placement) | A — top-left external |
| Q13 (soon vs shipped) | A — equal treatment |
| Q14 (token-matters) | A1 — paired sidecar with transport-matters |
| Q14b (manicure surfaces) | Config and profile panels, realtime plus historical graphs, mode history, tokens saved |
| Q15 (drill-downs) | 1, 2, 3, 7 |
| Q16 (closure-matters name) | B — closure-matters |
| Q17 (title) | D — "The Helioy Cell" |
| Q18 (artifacts in master) | A — none |
