# 456: Canvas: raw request viewer per harness wire class

URL: https://github.com/littleorgans/transport-matters/issues/456
State: open
Labels: enhancement
Updated: 2026-08-25T11:42:07Z

Parent: #455. First slice of Canvas Overlay, and the acceptance surface for every slice after it.

## Outcome

A read-only Canvas surface that shows the raw provider request for a chosen harness and model, grouped by wire equivalence class, with the two regions Canvas Overlay cares about broken out and measured: **system prompts / system messages** and **builtin tools**.

Read-only on purpose. No artifact store, no apply engine, no proxy changes. It exists so the shape of the problem is visible before anything mutates it.

## Why this first

- It runs on data we already ship. Class schemas come from `compatibility_releases_v1.json` `references[]`; request bodies come from the operator's own captured exchanges.
- It makes runtime-generated content identifiable by eye, which is the input to the regeneration slice.
- It is the user-acceptance surface: every later change is judged by looking at this view before and after.

## What it shows

Select harness → select model (resolved to its wire class, five classes today) → the request, with:

- **Region breakdown with byte and token counts.** System prompt, builtin tools, injected system messages, real user content, untouched remainder. The certified reference numbers for comparison (claude 145,491 tool bytes / 77.2%, codex 30,359 / 53.6%, grok 35,569 / 80.3%).
- **System prompt structure.** claude's `system[]` parts individually, and the internal section outline of the 29,764-char part (19 markdown headings) so the operator can see that "Types of memory" is 7,217 chars on its own. codex's `input[]` developer items with their XML-anchored runtime blocks (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`). grok's single system string.
- **Injected system messages.** claude's `<system-reminder>` block in `messages[0]` and the `role: system` agent catalog (10,720 chars). codex's `<environment_context>`. grok's `<user_info>`.
- **Tool list with per-tool cost.** Name, description size, schema size, sorted by bytes, so the expensive tools are obvious. codex's nesting inside the `additional_tools` item and its 26,383-char `exec` description shown as what it is.
- **What is addressable.** Editable targets marked per the certified schema, so it is clear up front what a later overlay could and could not touch.

## Scope

- Canvas pane registered through the enforced path (`model/paneRecords.ts` + its contract test, the three switches in `model/paneIdentity.ts`, `viewers/registry.tsx`, `viewers/registry.test.ts`, and the launcher pair dispatched via `workbench/CanvasCommandDispatcher.ts`).
- TypeScript throughout, per the plane rule. A `/v1/harnesses/{id}/wire-classes` read endpoint exposes classes, members and schemas; the request body comes from the operator's captured exchanges through the existing exchange endpoints.
- No import from `@tm/inspector`; the read-only `viewers/resource/primitives/JsonTree.tsx` idiom is the model for structure display.
- With no captured exchange yet for a class, the view lists the class's addressable targets and their kinds with nothing to prefill, and says so.

## Acceptance

- All five current wire classes render with correct region breakdowns, cross-checked against the certified reference figures.
- The claude system prompt's section outline and the codex runtime blocks are visible without reading raw JSON.
- Per-tool costs are sortable and the total matches the measured tool region.
- `just check` and `just test` green (the latter runs the shell suite).

## Sub issues
[]
