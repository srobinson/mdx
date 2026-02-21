---
title: Natural Seam Refactor Candidates in Manicure
type: research
tags: [manicure, refactor, tests, frontend, backend]
summary: The largest candidates should be decomposed by semantic ownership, test scenario families, and reusable fixture builders rather than by arbitrary size.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Manicure is a provider neutral context control plane for coding agents. The listed refactor candidates are large because they mix independent scenario families, reusable fixtures, and component logic in single files. The safest decomposition is by natural seams: provider, behavior family, fixture ownership, and UI row responsibility.

The strongest production refactor is `www/src/components/editor/SamplingSection.tsx`. The strongest test refactors are `api/src/manicure/codex/test_transport_turns.py`, `api/src/manicure/test_track_manager.py`, and `www/src/components/editor/SamplingSection.test.tsx` because their existing test names already reveal separable behavior families.

## Project Metadata

| Area | Finding |
| --- | --- |
| Repository | `manicure` |
| fmm | `.fmm.db` is present in this worktree |
| API language | Python 3.12 plus 3.13 support |
| API framework | FastAPI, mitmproxy, Typer, aiofiles |
| API tests | pytest, pytest asyncio |
| Web language | TypeScript, React 19 |
| Web build | Vite 8, Tailwind CSS 4 |
| Web tests | Vitest, React Testing Library, Playwright |
| Web package manager | pnpm 10.8.1 |

Sources: `api/pyproject.toml`, `www/package.json`, `www/vite.config.ts`, `www/playwright.config.ts`, `README.md`.

## Architecture Context

The codebase has two indexed top level areas: `api/` with 167 files and 35,782 LOC, and `www/` with 89 files and 17,482 LOC. The API captures and derives Claude and Codex turn artifacts. The web UI renders exchange lists, details, breakpoint editing, and visual regression fixtures.

Relevant dependency facts:

1. `www/src/components/editor/SamplingSection.tsx` depends on `HelpBubble`, `samplingShared`, `overrides`, and `types`. It is used by `BreakpointEditor` and its own test file.
2. `www/src/components/editor/samplingShared.ts` is only 75 LOC and is already shared by `SamplingSection.tsx` plus `detail/mutations.ts`.
3. `www/tests/visual/fixtures.ts` feeds five visual specs.
4. `api/src/manicure/codex/test_transport_turns.py` depends on `test_transport_support`, `ManicureAddon`, Codex transport state, flow state, and storage.
5. `api/src/manicure/test_track_manager.py` is imported by `test_track_manager_lifecycle.py`, so helper moves need a compatibility import or a dedicated support module.

## Refactor Principle

Decompose along stable reasons to change:

1. UI presentation versus override state transition logic.
2. Test harness versus scenario assertions.
3. Provider specific scenarios: Anthropic, Codex, generic.
4. Fixture data families: index rows, detail records, transport timelines, visual setup.
5. Lifecycle phases: open, finalize, repair, migrate, diagnose.

Do not split solely because a file is large. Keep colocated code when a reader needs the whole file to understand one behavior.

## Candidate Ranking

| Priority | File | Current size | Natural seam | Risk | Recommendation |
| --- | ---: | ---: | --- | --- | --- |
| 1 | `www/src/components/editor/SamplingSection.tsx` | 681 LOC | controller logic, row components, shared override commands | Medium | Extract logic first, then rows |
| 2 | `api/src/manicure/codex/test_transport_turns.py` | 816 LOC | websocket turn lifecycle families | Low | Split tests by lifecycle, keep helpers in support |
| 3 | `api/src/manicure/test_track_manager.py` | 682 LOC | provider traces and shared trace builders | Low to medium | Split provider suites, preserve downstream helper imports |
| 4 | `www/src/components/editor/SamplingSection.test.tsx` | 761 LOC | existing describe blocks | Low | Split after component seams settle |
| 5 | `www/tests/visual/fixtures.ts` | 684 LOC | data fixture families | Medium | Split data, retain barrel export |
| 6 | `www/src/hooks/useExchangeStream.test.tsx` | 704 LOC | SSE event families and store effects | Low | Split by existing describe groups |
| 7 | `api/src/manicure/codex/test_repair.py` | 685 LOC | fixture factories, rebuild, migrate, diagnostics | Low | Move builders, then split cases |
| 8 | `www/src/components/ExchangeList.test.tsx` | 963 LOC | track tree behavior versus anchored ordering | Low | Split when ExchangeList behavior is stable |

## Detailed Findings

### `SamplingSection.tsx`: production logic mixed with four UI row families

Evidence:

1. `SamplingSection` spans lines 140 to 681.
2. Local input mirror state sits at lines 149 to 155 and 186 to 189.
3. Override status checks sit at lines 191 to 199.
4. Commit handlers sit at lines 201 to 269.
5. Reset handlers sit at lines 271 to 285.
6. Thinking transition logic sits at lines 287 to 342.
7. Display and effort transitions sit at lines 344 to 376.
8. The render body starts at line 409, with row groups at 421, 464, 507, and 555.
9. `buildCommit` is already an isolated helper at lines 60 to 72.

Natural seams:

1. `useSamplingOverrides.ts`
   * Owns local input mirrors and commit handlers for `max_tokens`, `temperature`, `top_p`, `top_k`, and `stop_sequences`.
   * Owns `buildCommit` or exports it from `samplingShared.ts` if reuse with mutation code is useful.

2. `useThinkingOverrides.ts`
   * Owns thinking mode, budget memory, display, effort, and their override batches.
   * Moves lines 173 to 189 and 248 to 376 out of the component.

3. `SamplingNumberField.tsx` or private row components
   * Owns label, help bubble, reset button, input class, and validation text.
   * This removes repeated label plus input blocks from lines 423 to 461 and 557 to 677.

4. `ThinkingControls.tsx`
   * Owns thinking, budget, display, and effort controls.
   * Keeps provider extras behavior separate from generic sampling fields.

Suggested first cut:

1. Extract hooks without changing JSX.
2. Run `pnpm --dir www test -- SamplingSection.test.tsx`.
3. Extract row components after the hooks are stable.
4. Run `pnpm --dir www typecheck` and the SamplingSection test.

Expected result: the exported `SamplingSection` becomes a coordinator around row components, likely under 250 LOC.

### `SamplingSection.test.tsx`: existing describe blocks are the split plan

Evidence:

1. Test harness helper `renderSection` is lines 17 to 43.
2. Click helpers are lines 53 to 64.
3. Current behavior groups start at lines 68, 180, 246, 345, 416, 577, 635, and 688.

Natural seams:

1. `SamplingSection.render.test.tsx`
2. `SamplingSection.commits.test.tsx`
3. `SamplingSection.reset.test.tsx`
4. `SamplingSection.thinking.test.tsx`
5. `SamplingSection.providerExtras.test.tsx`
6. `SamplingSection.testSupport.tsx` for `renderSection`, `clickThinking`, `clickDisplay`, and `clickEffort`.

Do this after `SamplingSection.tsx` extraction so tests can move around the new abstractions rather than lock in the old monolith.

### `test_transport_turns.py`: websocket lifecycle scenario families

Evidence:

The file has ten async tests and imports shared helpers from `test_transport_support`. Test names reveal clear groups:

1. Completion and finalization: lines 31, 146, 290.
2. Turn separation and websocket end behavior: lines 343 and 443.
3. Pause and stale state behavior: lines 528 and 756.
4. Tool result and tool search output derivation: lines 591 and 640.
5. Derivation failure preserving open sidecars: line 203.

Natural split:

1. `test_transport_turn_completion.py`
2. `test_transport_turn_close.py`
3. `test_transport_turn_pause.py`
4. `test_transport_turn_derivation.py`

Move only duplicated message builders into `test_transport_support.py`. Keep scenario assertions close to their tests.

### `test_track_manager.py`: provider traces are the seam

Evidence:

1. Shared constants sit at lines 19 to 22.
2. Shared builders sit at lines 25 to 78.
3. Provider neutral equivalence test starts at line 81.
4. Anthropic reference and fan out tests start at lines 103, 313, 352, and 393.
5. Codex reference and fan out tests start at lines 176 and 477.
6. Collision safety test starts at line 605.
7. `test_track_manager_lifecycle.py` imports this file, so a split can break downstream imports unless helpers are preserved.

Natural split:

1. `test_track_manager_support.py` for constants and builders.
2. `test_track_manager_anthropic.py` for Anthropic spawn and continuation traces.
3. `test_track_manager_codex.py` for Codex agent id and call id traces.
4. `test_track_manager_core.py` for provider neutral and collision cases.

Compatibility step: make `test_track_manager.py` either disappear after imports are adjusted, or keep a tiny compatibility layer during the first commit if downstream tests import helpers by old path.

### `www/tests/visual/fixtures.ts`: fixture families need a barrel

Evidence:

1. `mockPausedFlow` spans lines 18 to 57.
2. `mockExchanges` spans lines 59 to 179.
3. `mockExchangeDetails` spans lines 189 to 585.
4. `SetupOptions` is lines 587 to 598.
5. `setupVisualTest` is lines 610 to 684.
6. Five specs import this file directly.

Natural split:

1. `fixtures/time.ts`: `FROZEN_NOW` and derived clock constants.
2. `fixtures/pausedFlow.ts`: `mockPausedFlow`.
3. `fixtures/exchanges.ts`: `mockExchanges` plus stable ids.
4. `fixtures/details.ts`: `mockExchangeDetails`, likely with transport timeline builders.
5. `fixtures/setup.ts`: `setupVisualTest` and `SetupOptions`.
6. Keep `fixtures.ts` as a barrel re exporting the same public names, so five downstream specs remain untouched.

This is a low behavior risk change if the barrel preserves export names.

### `useExchangeStream.test.tsx`: EventSource harness and event families

Evidence:

1. EventSource mock and store reset sit at lines 10 to 36.
2. `makePausedFlow`, `fireSSE`, and `makeWrapper` sit at lines 38 to 97.
3. Behavior groups start at lines 99, 195, 550, and 595.

Natural split:

1. `useExchangeStream.testSupport.tsx`: EventSource mock, `fireSSE`, `makeWrapper`, `makePausedFlow`.
2. `useExchangeStream.race.test.tsx`
3. `useExchangeStream.validation.test.tsx`
4. `useExchangeStream.forwarding.test.tsx`
5. `useExchangeStream.pausedTokens.test.tsx`

This split is safe because the hook dependency graph is narrow: `react query`, `uiStore`, `types`, and `useExchangeStream`.

### `test_repair.py`: fixture builders versus repair behaviors

Evidence:

1. Storage fixture is lines 36 to 38.
2. Transport and IR builders are lines 41 to 156.
3. Rebuild tests start at lines 159 and 373.
4. Live timeline parity starts at line 238.
5. Audit only safety starts at line 305.
6. Migration and identity starts at line 421.
7. Diagnostics start at lines 534 and 592.
8. Non turn transport safety starts at line 657.

Natural split:

1. `test_repair_support.py`: `_message`, `_codex_transport`, `_close`, `_codex_ir`, `_live_codex_derivation`.
2. `test_repair_rebuild.py`
3. `test_repair_migration.py`
4. `test_repair_diagnostics.py`
5. `test_repair_safety.py`

Keep private helper names if only tests use them. The refactor target is locality, not public API shape.

### `ExchangeList.test.tsx`: track tree behavior versus anchored ordering

Evidence:

1. `makeEntry` is lines 7 to 36.
2. General `ExchangeList` tests start at line 38.
3. Anchored ordering tests start at line 643.
4. `rowOrder` is lines 644 to 647.

Natural split:

1. `ExchangeList.trackTree.test.tsx`: root tracks, subagent tracks, stubs, selected state.
2. `ExchangeList.ordering.test.tsx`: anchored ordering and row order helper.
3. `ExchangeList.testSupport.ts`: `makeEntry` plus small builders for parent, child, stub, and selected entries.

The existing `describe` boundary at line 643 is already the first seam. Avoid over splitting until the source component itself is inspected for matching seams.

## Recommended Execution Order

1. Split test support modules where behavior should not change.
2. Run targeted tests after each file family.
3. Extract `SamplingSection` hooks and keep its tests unchanged.
4. Split `SamplingSection` tests once the component has smaller interfaces.
5. Split visual fixtures through a barrel so visual specs keep their imports.

## Verification Commands

Use targeted checks before broader checks:

```bash
pnpm --dir www test -- SamplingSection.test.tsx
pnpm --dir www test -- ExchangeList.test.tsx useExchangeStream.test.tsx
pnpm --dir www typecheck
uv run --project api pytest api/src/manicure/codex/test_transport_turns.py api/src/manicure/codex/test_repair.py api/src/manicure/test_track_manager.py
```

After decomposing files, update test paths in commands to the new file names and run:

```bash
pnpm --dir www test
uv run --project api pytest api/src/manicure/codex api/src/manicure/test_track_manager*.py
```

## Relevance to Helioy

This refactor improves Manicure as a Helioy control plane component by making Codex and Claude trace behavior easier to audit. The seams also match Helioy operational boundaries: transport capture, track assignment, artifact repair, UI override editing, and visual regression fixtures.

## Open Questions

1. Should `samplingShared.ts` become the canonical home for all override command builders, or should UI only helpers stay under `SamplingSection`?
2. Should Python test helpers use private names, or should support modules expose public factory names for readability?
3. Should visual fixtures remain TypeScript objects, or should larger transport timelines move to JSON fixture files?
