# Audioface Scout: Slice 2 Flow Persistence

Date: 2026-08-17
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/audioface` at `main` `73f6fc6`, tree clean
Lenses: `/code-review` (correctness, reuse) and `/code-hygiene` (seams, thresholds, duplication)
Baseline: focused suite (`token-library`, `studio-token-library-store`, `sequence-editor-core`, `sequence-timeline-core`, `studio-sequence-audition`, `studio-dom`, `studio-token-authoring`) passes, 90/90.

Goal under scout: a designer creates a new flow, names it, edits steps, saves it, reloads Studio, finds it again with `TokenAssetId` step references intact; missing library assets after reload surface deliberately.

## Reuse Map

### Reuse (use as is)

| Need | Existing symbol | Notes |
|---|---|---|
| Sequence model | `packages/core/src/sequences.ts` `SequenceDraft<Id>`, `SequenceStepDraft<Id>` | Already generic over `TokenAssetId`. Studio state is `SequenceDraft<TokenAssetId>` (`apps/studio/src/app/useSequenceAudition.ts` `SequenceAuditionState.draft`). No widening needed. |
| Step editing with asset resolution | `packages/core/src/sequence-editor.ts` `normalizeSequenceDraft`, `updateSequenceStep`, `duplicateSequenceStep`, `deleteSequenceStep`, `getSequenceStep`, `nearestSequenceStepKey` | Asset aware overloads take `TokenDefinitionResolver<Id>`. `finalizeDraft` re-sorts and uniquifies keys, so a persisted draft can be normalized on load through the same path. `deleteSequenceStep` guarantees non-empty steps. |
| Projection and playback | `packages/core/src/sequence-timeline.ts` `buildSequenceTimeline`, `resolveSequenceStepPlayback`; `packages/core/src/sequence-graph.ts` `buildSequenceGraph` | Both preserve `Id`. `buildSequenceTimeline` memoizes resolution per id via `resolveOnce`. |
| Asset resolution | `packages/core/src/token-assets.ts` `createTokenAssetCatalog`, `TokenDefinitionResolver`, `resolveCanonicalTokenAsset`, `TokenAssetId` | One resolver already feeds editing, timeline, graph, audition, and full Play (`useSequenceAudition` passes `authoring.resolver` everywhere; pinned by `test/studio-sequence-audition.test.mjs` "studio sequence state resolves token assets through one catalog"). |
| Runtime discriminator | `packages/core/src/token-library.ts` `isTokenLibraryId`; `packages/core/src/tokens.ts` `toTokenId` | Together they validate any `TokenAssetId` string at a parse boundary without inspecting prefixes by hand. |
| Persisted store pattern | `packages/stores/src/tokenLibraryStore.ts` `createTokenLibraryStore`, `TOKEN_LIBRARY_STORE_STORAGE_KEY`, `TOKEN_LIBRARY_STORE_VERSION` | Zustand `persist` with `partialize`, `migrate`, custom `merge`, loss aware hydration (`hydratePersistedLibrary`, `QuarantinedTokenLibraryEntry`, `writesBlocked`, `rawPersistedPayload`), factory plus module singleton (`useTokenLibraryStore`), injectable `StateStorage` for tests. Storage key convention `audioface.<slice>.v1` with `version: 1`. |
| Store test harness | `test/studio-token-library-store.test.mjs` `createMemoryStorage`, the "module-scoped store hydrates existing persisted entries at import time" pattern | Reload proof is already scripted: seed store, `createTokenLibraryStore({ storage })` again, assert entries and `hydrationError`. |
| Studio persistence rule | `LESSONS.md` "Do not introduce storage adapter patterns"; `ARCHITECTURE.md` "packages/stores owns persisted app state" | A second Zustand persisted slice in `packages/stores` is the ruled home. `test/studio-dom.test.mjs` "studio token library state is behind a persisted package store" forbids `packages/storage`, `Repository`, `Adapter`, and Studio side storage files. |
| Focused authoring hook shape | `apps/studio/src/app/useTokenAuthoring.ts` `useTokenAuthoring`, `TokenAuthoringOptions`, `TokenAuthoringState`; `apps/studio/src/app/useEventHandler.ts` `useEventHandler` | Established pattern for a store backed hook composed by `useSequenceAudition` with identity stable callbacks. A `useFlowLibrary` (name open) hook follows it. |
| Store subscription and blocked writes UI | `useTokenAuthoring` selectors `entries`, `hydrationError`, `writesBlocked`, `quarantinedEntries.length`, `dropQuarantinedEntries`; `apps/studio/src/components/editor/TokenEditor.tsx` props `hydrationError`, `onDropQuarantined` | Same diagnostics vocabulary should surface for the flow slice. |
| Entropy and timestamps | `useTokenAuthoring` `createTokenLibraryId("user", crypto.randomUUID())`, `new Date().toISOString()` | Studio supplies entropy and time to pure core factories. Reuse the same call sites style for flow ids and `createdAt`/`updatedAt`. |
| Fixture flows | `packages/core/src/sequence-fixtures.ts` `SEQUENCE_FIXTURE_IDS`, `getSequenceFixture`, `listSequenceFixtures`, private `fixture` | Canonical flows with default `TokenId` references compile into `SequenceDraft<TokenAssetId>` state. `SequenceAudition.tsx` `flowOptions` lists them. |
| Error surface | `apps/studio/src/components/StudioErrorBoundary.tsx`; `SequenceAudition.tsx` header error strip fed by `SequenceAuditionState.error` | Non fatal errors go to the strip; render time throws go to the boundary. |
| Editor reset keyed on identity | `apps/studio/src/app/useTokenEditor.ts` `useTokenEditor(source, sourceId)` | Pattern for keeping a draft while the saved object refreshes; a flow label editor can copy the `sourceId` effect idea instead of a new mechanism. |
| Gate | `package.json` `pnpm run check` (`tsc -b`, `node --test`, `audioface validate`) | Repository gate. |

### Existing infra to build on (adapt, do not copy)

| Need | Existing symbol | Adaptation |
|---|---|---|
| Sequence schema | `packages/core/src/score-schema.ts` `sequenceStepDraftSchema`, `sequenceDraftSchema` (private, zod) | Only zod description of a `SequenceDraft` in the repo. Its `tokenId` is `idSchema` (`z.string().min(1)`), so it accepts any string. Export a sequence schema owner (move to a `sequence-schema.ts` or export from `sequences.ts` neighbour) with a `tokenId` refinement through `isTokenLibraryId` or `toTokenId`, and let `score-schema.ts` import it. `zod` is already a `@audioface/core` dependency. |
| Parse result idiom | `packages/core/src/score-validation.ts` `safeParseScoreDraft`, `parseScoreDraft`, `ScoreValidationResult`, `ScoreDraftValidationError` | Discriminated `ok` result plus throwing parse. Suitable for the storage boundary of persisted flows. See "Similar checked and rejected" for the competing token library idiom. |
| Loss aware hydration machinery | `tokenLibraryStore.ts` `hydratePersistedLibrary`, `MIGRATION_HYDRATION` symbol, `migratePersistedLibrary`, `migratedHydration`, `persistableLibraryState`, `resolveStorage`, `requireString`, `errorMessage`, `TokenLibraryHydrationResult` | Generic over "an array of persisted entries recovered by a throwing per entry recover function". Extract into a shared module in `packages/stores` before a second store exists, then have both stores consume it. See Quality Map Q1. |
| Blank factory | `packages/core/src/token-library.ts` `createBlankTokenLibraryEntry` (`id`, `createdAt`, `updatedAt` defaults to `createdAt`) | Mirror as `createBlankSequenceDraft` or a library entry factory in core: takes explicit id and one starter step; validates through the shared normalizer. |
| Opaque origin qualified id | `token-library.ts` `TOKEN_LIBRARY_ID_PATTERN`, `parseTokenLibraryId`, `createTokenLibraryId(origin, entropy)` | If flows adopt origin qualified ids (`user:<uuid>`), the parser and pattern should be shared rather than re-declared per entity. Today the pattern is token library private. |
| Catalog composition | `token-assets.ts` `createTokenAssetCatalog` (canonical first, authored second, frozen snapshots) | The same shape (`assets` list plus `resolve`) fits a sequence catalog: fixtures first, persisted flows second. Fixture flows would be the locked "canonical" analogue. |
| Event time store read | `useTokenAuthoring` `resolveCommittedAsset` reading `useTokenLibraryStore.getState()` | The same idiom lets a save handler select the just persisted flow before the next render. |
| Copy while dirty | `apps/studio/src/app/authoringEntries.ts` `buildCopyEntry` | Model for "save carries the live draft"; a flow save must persist the current in memory `SequenceDraft`, not the fixture. |

### Similar checked and rejected

| Candidate | Why rejected |
|---|---|
| Hand rolled validator idiom `token-library.ts` `validateTokenLibrary` / `TokenLibraryValidationIssue` (`valid` boolean, string codes) as the flow validator | Second validation idiom beside zod based `score-validation.ts`. Sequence step fields are already described in zod (`score-schema.ts`). Adding a third hand rolled sequence validator duplicates field rules. Note the two idioms already coexist; do not add a third. |
| Persisting flows inside `tokenLibraryStore.ts` as an extra field | Breaks single responsibility, complicates `partialize` and `writesBlocked` semantics which are keyed to token entries, and couples two aggregates with different lifecycles. |
| Storing `sourceTokenId` fallback for missing assets | Forbidden by Slice 1 constraint "Lookup never falls back from a missing library asset to its canonical `sourceTokenId`" and pinned by `test/studio-sequence-audition.test.mjs` "studio playback resolves sequence steps through a required resolver" (`doesNotMatch /sourceTokenId/`). |
| Root spike `src/sequences.js`, `src/sequence-editor.js` | Reference only per `LESSONS.md`; Studio must not import them. |
| `ScoreDraft.sequences` (`packages/core/src/scores.ts`) as the flow library | Score Mode is a separate bounded context; Slice 1 ruled Score contracts stay on `TokenId`. |
| Cross store validation at hydration (sequence store checking token store for asset existence) | No cross store invariant exists today; stores hydrate independently and the catalog is composed in Studio (`useTokenAuthoring`). Asset presence is a runtime resolution concern, not a persistence validity concern. |

### None found (searches run)

- No sequence or flow persistence anywhere: `rg -n "sequenceLibrary|flowLibrary|SequenceLibrary|FlowLibrary" packages apps/studio/src test` returned nothing.
- No `SequenceDraft` parser or validator outside `score-schema.ts`/`score-validation.ts`: `rg -n "parseSequenceDraft|validateSequenceDraft|sequenceDraftSchema" packages` hits only `score-schema.ts` (private).
- No sequence identity type beyond `SequenceFixtureId` and free `SequenceDraft.id: string`: `rg -n "SequenceId|toSequenceId" packages apps/studio/src` returned nothing.
- No use of `removeLibraryEntry`, `replaceLibrary`, or `clearLibrary` in Studio: `rg -n "removeLibraryEntry|replaceLibrary|clearLibrary" apps/studio/src` returned nothing. Studio has no delete UI for library entries, so today a persisted flow can only reference a missing asset after manual storage edits, a cleared library from another tab, or a future delete action.
- No shared `errorMessage`, `assertNever`, or `clamp` owner in core (see Quality Map).

## Quality Map

### Q1. Persistence machinery is token specific but generic in shape (duplication risk, must groom first)

`packages/stores/src/tokenLibraryStore.ts` (357 lines) mixes three responsibilities: token specific validation (`recoverPersistedEntry`, `userLibraryError`, `userLibraryEntryError`), generic loss aware hydration (`hydratePersistedLibrary`, `TokenLibraryHydrationResult`, `QuarantinedTokenLibraryEntry`, `MIGRATION_HYDRATION`, `migratePersistedLibrary`, `migratedHydration`, `isMigratedTokenLibraryState`, `persistableLibraryState`), and platform plumbing (`resolveStorage`, `requireString`, `errorMessage`). A second persisted slice written by copy would duplicate about 150 lines and two subtle invariants (the migration symbol trick and the raw payload write through in `partialize`). Recommendation: extract the generic hydration and plumbing into a `packages/stores` module (for example `persistedLibrary.ts`) parameterized by a per entry recover function and an entry id accessor, keep token rules in `tokenLibraryStore.ts`, then build the flow store on the shared owner. `test/studio-dom.test.mjs` "studio token library state is behind a persisted package store" pins `create<TokenLibraryStoreState>()(`, `persist(`, `partialize`, `migrate`, `validateTokenLibrary`, and the storage key string inside `tokenLibraryStore.ts`; those survive extraction as long as the store file still calls them.

### Q2. Missing asset is fatal for the whole app (correctness, design driver)

`apps/studio/src/app/useTokenAuthoring.ts` `selectedAsset` memo throws `Unknown Audioface token asset: <id>` when the selected step's asset is absent; `StudioErrorBoundary` then replaces the entire Studio. `buildSequenceTimeline` and `resolveSequenceStepPlayback` also throw through the resolver, so any persisted flow that references a missing `TokenLibraryId` would crash on the first render after reload. Fixtures cannot hit this today because canonical ids always resolve. Slice 2 introduces the first durable path to a dangling reference. This is the design decision D3 below.

### Q3. Flow identity is fixture bound

`useSequenceAudition` state is `Partial<Record<SequenceFixtureId, SequenceDraft<TokenAssetId>>>`; `flowId`, `selectFlow`, `resetFlow` are typed to `SequenceFixtureId`; `SequenceAudition.tsx` builds `flowOptions` from `SEQUENCE_FIXTURE_IDS` at module level and casts the select value. `SequenceDraft.id` is a free string with fixture ids in kebab case and `seed` convention `${draft.id}:${key}` (both `sequence-fixtures.ts` `fixture` and `sequence-editor.ts` `duplicateSequenceStep`). A user flow needs an identity that is not a `SequenceFixtureId` and a seed convention that keeps deterministic variation. Decision D1.

### Q4. Duplicated helpers

- `assertNever` is declared eight times: `packages/core/src/{score-timeline,tokens,sequence-fixtures,score-fixtures,sound-fingerprint,score-validation}.ts`, `packages/engine/src/index.ts`, `apps/studio/src/app/studioHelpers.ts`. Core already has `runtime.ts` (`isRecord`, `deepFreeze`) as the natural owner.
- `clamp` logic exists three times: `sequence-editor.ts` `clampNumber`, `tokens.ts` `clamp` (with fallback), `studioHelpers.ts` `clamp` (identical to `clampNumber`).
- `error instanceof Error ? error.message : <fallback>` appears in `tokenLibraryStore.ts` `errorMessage`, `useStudioPlayback.ts` (twice), `useTokenAuthoring.ts` `persistEntry`, `StudioErrorBoundary.tsx`.
- Two validation result idioms in core: `TokenLibraryValidationResult` (`valid`) and `ScoreValidationResult` (`ok`). Not a blocker, but Slice 2 must not add a third.

Grooming recommendation: consolidate `assertNever` and `clamp` into `packages/core/src/runtime.ts` (export through `index.ts`) and `errorMessage` into `runtime.ts` or the extracted store module, in a mechanical slice before feature code. Optional for Slice 2 but cheap and reduces the surface the flow work touches.

### Q5. Boundary and hygiene notes

- `resolveCommittedAsset` (`useTokenAuthoring.ts`) rebuilds a full catalog, including `validateTokenLibrary` over every entry and `deepFreeze`, per call. Event time only today; a flow save that resolves many steps this way would multiply the cost. Prefer passing the memoized resolver or reading the store once per event.
- `apps/studio/src/app/useSequenceAudition.ts` is 250 lines and already composes theme, playback, authoring, playhead, and flow selection. Adding flow library actions inline would breach cohesion well before 700 lines. Slice 1 precedent: extract a focused hook (`useTokenAuthoring`). Do the same for flow library state.
- `ARCHITECTURE.md` "Token Library Ownership" still says "Invalid local data falls back to an empty user library"; Slice 1 replaced that with loss aware hydration. Doc drift; update alongside the new store section.
- `SequenceStepList.tsx` renders `event.tokenId` raw, so a library step shows `user:<uuid>`. Pre-existing UX wart, becomes more visible once user flows persist library references.
- Studio structural tests are source regex based (`test/studio-sequence-audition.test.mjs`, `test/studio-dom.test.mjs`). Several pin exact call shapes in `useSequenceAudition.ts` (`updateSequenceStep(draft, key, patch, authoring.resolver)` and siblings, `getSequenceFixture`, `resolveCommittedAsset`). Extraction of flow state into a new hook will require moving or replacing those assertions; plan for it rather than discovering it at gate time.
- No file over 700 lines and no function over 150 lines in scope. Largest in scope: `packages/core/src/token-library.ts` 514, `packages/stores/src/tokenLibraryStore.ts` 357, `packages/core/src/sequence-timeline.ts` 251, `useSequenceAudition.ts` 250.

## Plan

### Decisions needed (Stuart)

- **D1 Flow identity and vocabulary.** Options: (a) origin qualified opaque id `user:<uuid>` mirroring `TokenLibraryId` with a shared parser, fixtures staying on `SequenceFixtureId` and treated as locked canonical flows; (b) free `string` id with uuid entropy and no origin. Recommendation: (a), because it reuses `parseTokenLibraryId` semantics, gives a runtime discriminator between fixture and user flows, and matches `PRODUCT_PROGRESSION.md` "Token Library Boundary" (canonical locked, user authored separate). Also settle the ubiquitous language: Studio says "Flow", core says "Sequence". Recommendation: core keeps `Sequence*` names, Studio UI copy keeps "Flow", store and hook names follow core (`sequenceLibraryStore`, `useSequenceLibrary`) so the package vocabulary stays single.
- **D2 Persisted shape.** Options: (a) persist `SequenceDraft<TokenAssetId>` plus envelope (`id`, `label`, `createdAt`, `updatedAt`, `origin`, `locked`) as a `SequenceLibraryEntry`, mirroring `TokenLibraryEntry`; (b) persist bare drafts. Recommendation: (a) for parity with the token store, timestamps for ordering, and a lock flag for fixtures if they ever enter the catalog.
- **D3 Missing asset surfacing.** Persistence validates shape only (D2); asset presence is resolved at runtime through the catalog. Options: (a) keep whole app fatal (current behavior, rejected by the goal); (b) mark the sequence unplayable and unselectable with a visible reason, keep it in the list; (c) per step "missing asset" state: timeline event and node editor show the dangling `TokenAssetId`, step is skipped in playback, node editor offers reassign, `useTokenAuthoring` selected asset becomes nullable instead of throwing. Recommendation: (c) because the designer keeps their flow and can repair it, and it removes the boundary crash from Q2. Requires core support: a resolver that can report absence without throwing (for example a `tryResolve` on the catalog or a projection that tolerates unresolved steps) and a `SequenceTimelineEvent` state for unresolved steps. Confirm whether the timeline should skip or hold a placeholder slot for the missing step.
- **D4 Save model.** Options: (a) explicit Save button, in memory edits stay session only until saved (matches token editor `dirty` and `canSave`); (b) autosave every edit. Recommendation: (a) for symmetry with the token slice and the ruled loss aware store, with a `dirty` indicator per flow.
- **D5 New flow starter.** Which single step seeds a blank flow (`deleteSequenceStep` keeps drafts non empty). Recommendation: one step on a canonical neutral token (`button.press` is the existing Studio fallback in `useSequenceAudition` `selectedAssetId`), label `Untitled Flow`, `delayMs` 0, velocity 0.5, seed `${id}:${key}`.
- **D6 Fixture reset semantics for user flows.** `resetFlow` restores the fixture; for a user flow it should restore the last saved draft. Confirm.

### Ordered steps (each bound to the reuse map)

1. **Groom stores (Q1).** Extract generic loss aware hydration and plumbing from `tokenLibraryStore.ts` into a shared `packages/stores` module; `tokenLibraryStore.ts` keeps token rules and its public API unchanged. Gate: `test/studio-token-library-store.test.mjs` and `test/studio-dom.test.mjs` unchanged and green.
2. **Optional groom (Q4).** Move `assertNever`, `clamp`, `errorMessage` to `packages/core/src/runtime.ts` and export; migrate the eight and three call sites. Gate: `pnpm run check`.
3. **Core: sequence schema and parser.** Export a sequence draft schema with asset aware `tokenId` refinement (`isTokenLibraryId` or `toTokenId`), have `score-schema.ts` consume it, add `safeParseSequenceDraft`/`parseSequenceDraft` following `score-validation.ts` idiom. Add the library entry type and factories per D1/D2/D5 next to `token-library.ts` patterns (`createSequenceLibraryId`, `createBlankSequenceLibraryEntry`, `updateSequenceLibraryEntry`, `validateSequenceLibrary`), sharing the origin id parser. Export from `packages/core/src/index.ts`. Tests: new `test/sequence-library.test.mjs` covering parse rejection of bad asset ids, factory outputs, timestamp rules, and that fixtures still compile through defaults.
4. **Core: tolerant resolution (D3).** Add non throwing lookup to `token-assets.ts` catalog and an unresolved step state in `sequence-timeline.ts`/`sequence-graph.ts` projections, without changing `resolveSequenceStepPlayback` error text for the throwing path. Tests: extend `test/sequence-timeline-core.test.mjs` "asset aware sequence failures report the exact missing asset" with the tolerant variant.
5. **Stores: `sequenceLibraryStore.ts`.** Built on step 1's shared module, key `audioface.sequenceLibrary.v1`, version 1, `partialize`, `migrate`, `merge`, quarantine and `writesBlocked` semantics identical to the token store, injectable storage, module singleton. Export from `packages/stores/src/index.ts`. Tests: new `test/studio-sequence-library-store.test.mjs` reusing the `createMemoryStorage` and reload patterns; must include the "reload preserves `TokenAssetId` step references" case and the mixed valid and invalid quarantine case.
6. **Studio: focused hook.** Add `useSequenceLibrary` (name per D1) under `apps/studio/src/app` following `useTokenAuthoring`: store subscription, memoized sequence catalog (fixtures first, saved flows second), create, rename, save, select, `dirty`, `canSave`, blocked writes, and event time selection via `getState()`. `useSequenceAudition` composes it and drops the `SequenceFixtureId` keyed drafts map. Update `SequenceAudition.tsx` flow select to the catalog and add name and Save controls (placement per layout owner). Change `useTokenAuthoring` selected asset to nullable per D3 and route the missing state to `SequenceNodeEditor` and `TokenEditor`.
7. **Tests: replace pinned shapes.** Move `test/studio-sequence-audition.test.mjs` assertions that name `getSequenceFixture` and the drafts map to the new hook; add behavior tests for the hook's pure helpers where possible; add structural checks that the store lives in `packages/stores` and Studio has no storage files (extend the existing `studio-dom` test rather than a new one).
8. **Docs.** Add the sequence library to `ARCHITECTURE.md` "packages/stores" and fix the stale "falls back to an empty user library" sentence; add a `PRODUCT_PROGRESSION.md` entry for the flow library boundary.
9. **Gates.** Focused suite from Slice 1 plus the two new test files, then `pnpm run check`. Studio acceptance proof: create flow, name, edit steps including a library asset step, save, reload, find it, play it; then delete or clear the library asset (via devtools until a delete UI exists) and confirm the D3 surfacing without a boundary crash.

### Tests and gates summary

- Focused: `node --test test/sequence-library.test.mjs test/studio-sequence-library-store.test.mjs test/token-library.test.mjs test/studio-token-library-store.test.mjs test/sequence-editor-core.test.mjs test/sequence-timeline-core.test.mjs test/sequence-graph-core.test.mjs test/studio-sequence-audition.test.mjs test/studio-dom.test.mjs test/studio-token-authoring.test.mjs`
- Repository: `pnpm run check`
- Thresholds: keep `useSequenceAudition.ts` and the new hook each well under 700 lines; the extracted store module and `sequenceLibraryStore.ts` under 300 each by construction.

## Dispositions (orchestrator, 2026-08-17)

Recorded per finding after the surface-and-decide gate. The Slice 2 spec binds to these.

- Q1 persistence machinery: **Refactor first.** Slice 2a extracts the generic loss aware hydration and plumbing into a shared `packages/stores` module before any flow code. Token store public API and pinned structural tests unchanged.
- Q4 duplicated helpers: **Refactor first**, inside Slice 2a. `assertNever`, `clamp`, `errorMessage` move to `packages/core/src/runtime.ts` and all call sites migrate; the old copies are deleted in the same PR.
- Q2 / D3 missing asset: **(c) per step missing asset state.** Selected asset becomes nullable; the timeline holds a placeholder slot for the unresolved step so timing is preserved; playback skips it; node editor shows the dangling `TokenAssetId` and offers reassign. No boundary crash for a dangling reference.
- Q3 / D1 identity and vocabulary: **(a) origin qualified opaque id** sharing the `TokenLibraryId` parser semantics; fixtures stay on `SequenceFixtureId` as locked canonical flows. Core keeps `Sequence*` names; Studio UI copy says "Flow"; store and hook names follow core (`sequenceLibraryStore`, `useSequenceLibrary`).
- D2 persisted shape: **(a) `SequenceLibraryEntry` envelope** (`id`, `label`, `createdAt`, `updatedAt`, `origin`, `locked`) around `SequenceDraft<TokenAssetId>`, mirroring `TokenLibraryEntry`.
- D4 save model: **(a) explicit Save** with `dirty` and `canSave` per flow, matching the token editor.
- D5 blank starter: **accepted** as recommended (one `button.press` step, label `Untitled Flow`, `delayMs` 0, velocity 0.5, seed `${id}:${key}`).
- D6 reset: **user flow reset restores the last saved draft**; fixture reset unchanged.
- Q5 `resolveCommittedAsset` cost: **Reuse** the memoized resolver or read the store once per event; no per step catalog rebuild.
- Q5 `useSequenceAudition` cohesion: **Refactor during the slice** by extracting `useSequenceLibrary`, mirroring `useTokenAuthoring`.
- Q5 `ARCHITECTURE.md` drift: **fix during the slice** with the new store section.
- Q5 `SequenceStepList` raw `user:<uuid>` label: **defer** with reason; it is a display concern that a later library browser slice owns. Record it in the spec's out of scope list.
- Q5 pinned structural tests: **plan the move** in the spec; each relocated assertion is listed by test name.

Slicing: Slice 2a groom (Q1 + Q4, mechanical PR), Slice 2b packages (core schema, entry factories, tolerant resolution, `sequenceLibraryStore`), Slice 2c studio (hook, components, tests, docs, acceptance proof).
