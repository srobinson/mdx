# Reuse Map

Baseline: clean `main` at `9faf83d9cc2fbe3fbd2c9ee98ecbea687b2e1a13` (`feat: tab the side pane with node, token, and theme editors`). This scout is read only for the repository. No builds or tests were run.

**Reuse**

- `packages/core/src/token-library.ts` :: `copyTokenToLibrary` is the canonical Copy to Library operation. It clones the recipe, preserves canonical provenance, creates an editable entry, and derives its fingerprint.
- `packages/core/src/token-library.ts` :: `createTokenLibraryEntry` is the common construction boundary for a completed authored definition. Reuse it beneath new blank and update operations so cloning and fingerprint generation stay in one owner.
- `packages/core/src/token-library.ts` :: `listCanonicalTokenLibraryEntries`, `createCanonicalTokenLibrary`, and `validateTokenLibrary` provide the locked canonical pack and the current library validation vocabulary.
- `packages/core/src/tokens.ts` :: `cloneAudiofaceTokenDefinition`, `calculateAudiofaceTokenDuration`, and `resolveAudiofaceToken` already own recipe cloning, derived duration, and themed resolution.
- `packages/core/src/playback.ts` :: `resolveTokenPlayback` is the definition based route into `ResolvedPlayback`. Extend this shared route for raw and themed modes so inspection, recording, and engine scheduling continue to consume the same object.
- `packages/engine/src/index.ts` :: `AudiofaceEngine.playResolved` already ignores token origin and schedules resolved layers through the master gain and limiter. No engine fork is required for user assets or raw audition.
- `packages/stores/src/tokenLibraryStore.ts` :: `useTokenLibraryStore`, `saveLibraryEntry`, `removeLibraryEntry`, `replaceLibrary`, and Zustand `persist` already provide the required shared Studio state, upsert behavior, browser persistence, versioning, and reload seam.
- `packages/core/src/sequence-editor.ts` :: `updateSequenceStep`, `duplicateSequenceStep`, `deleteSequenceStep`, `normalizeSequenceDraft`, and selection continuity helpers remain reusable after token lookup becomes asset aware.
- `packages/core/src/sequence-timeline.ts` :: `buildSequenceTimeline` and `resolveSequenceStepPlayback`, plus `packages/core/src/sequence-graph.ts` :: `buildSequenceGraph`, remain the correct timeline, graph, and sequence playback pipeline after they receive one authoritative definition resolver.
- `apps/studio/src/app/useTokenEditor.ts` :: `useTokenEditor` and its edit operations are reusable after the hook accepts a selected definition or library entry instead of calling the canonical catalog itself.
- `apps/studio/src/app/useStudioPlayback.ts` :: `useStudioPlayback`, `auditionTokenDefinition`, and `auditionFlow` already centralize engine lifecycle, flow cancellation, scheduling, error state, and last playback state.
- `apps/studio/src/components/editor/TokenEditor.tsx` :: `TokenEditor` is the correct home for Copy to Library, New from Blank, Save, Raw Audition, and Themed Audition actions once state is supplied by the active authoring hook.
- `apps/studio/src/components/sequence/SequenceNodeEditor.tsx` :: `SequenceNodeEditor` remains the step asset picker after its module level canonical list is replaced by injected canonical and user asset options.
- `apps/studio/src/components/inspector/SignalInspector.tsx` :: `SignalInspector` can show the raw and themed resolved layer comparison once it is remounted on the live Sequence Audition surface.

**Existing infra**

- `apps/studio/package.json` :: `dependencies` already declares `@audioface/stores`; Studio currently leaves that dependency unused.
- `packages/stores/src/tokenLibraryStore.ts` :: `TOKEN_LIBRARY_STORE_STORAGE_KEY` and `TOKEN_LIBRARY_STORE_VERSION` establish the persisted payload boundary.
- `test/token-library.test.mjs` :: token library cases cover canonical locking, copy behavior, custom entry construction, resolution, ownership, and fingerprint validation.
- `test/studio-token-library-store.test.mjs` :: store cases provide a synchronous memory storage harness and prove the current valid save and reload path.
- `test/core-playback.test.mjs`, `test/sequence-editor-core.test.mjs`, `test/sequence-timeline-core.test.mjs`, and `test/sequence-graph-core.test.mjs` :: direct package tests are the right behavioral level for the widened asset path.
- `package.json` :: `test` and `check` define the required `node --test` convention and the complete `pnpm run check` gate, which runs typecheck, the full Node suite, and contract validation.

**Similar checked and rejected**

- `src/timeline.js` :: `buildSequenceTimeline` and `resolveTimelineToken` demonstrate resolver injection. The dependency inversion is useful. Direct reuse is rejected because root `src` is the spike and Studio may consume package APIs only.
- `packages/core/src/token-library.ts` :: `resolveLibraryToken` performs themed definition resolution but carries no playback intent, asset lookup, raw mode, or sequence context. Extending `resolveTokenPlayback` avoids a parallel playback path.
- `apps/studio/src/components/tokens/TokensExplorer.tsx` :: `TokensExplorer` is a possible presentation base for a later library browser. Its module level `listAudiofaceTokens` result makes it unsuitable as the Slice 1 asset source without refactoring.
- `apps/studio/src/app/useStudioSession.ts` :: `useStudioSession` is the superseded orchestration generation. Adding authoring behavior there would duplicate the active `useSequenceAudition` path.
- `packages/core/src/scores.ts` :: `ScoreDraft`, `MotifDraft`, token clips, and selectors should retain their current canonical boundaries during this sequence authoring slice. Widening every `TokenId` across Score would expand scope without helping the approved proof.

**None found**

- No core blank token or valid starter entry factory exists.
- No unique user asset ID allocator or opaque asset ID model exists. `packages/core/src/token-library.ts` :: `copyTokenToLibrary` defaults to one deterministic `user:<canonical id>` value, so a second copy overwrites the first through store upsert.
- No single canonical plus custom definition index or resolver exists.
- No raw playback resolver or identity theme exists. `packages/core/src/tokens.ts` :: `resolveAudiofaceToken`, `resolveMetrics`, and `resolveLayer` always apply action, material, macro, velocity, and variation policy.
- No loss aware persisted library hydration or quarantine path exists.

# Quality Map

**Measurements**

The named core, store, and Studio app files are all below 700 lines. `apps/studio/src/app/useSequenceAudition.ts` :: `useSequenceAudition` spans about 180 lines, beyond the repository function threshold, and already owns flow drafts, selection, timeline, graph, playback, playhead animation, theme editing, token editing, and audition throttling. It must be decomposed before Slice 1 behavior is added.

**Asset identity and type boundary**

`packages/core/src/tokens.ts` :: `TokenId` is a branded string rather than a literal union. `toTokenId` validates syntax, while `getAudiofaceToken` gives the type its current canonical catalog meaning. Expanding that type to accept `user:` and `team:` values would weaken every canonical caller.

`packages/core/src/token-library.ts` :: `TokenLibraryEntry.id` already carries origin qualified asset identity. `TokenLibraryEntry.token.id` is semantic recipe identity, and `sourceTokenId` is canonical provenance. A copied user entry can therefore share its inner token ID with the canonical source. Sequence steps must retain the full library asset reference.

Introduce a separate `TokenAssetId = TokenId | TokenLibraryId`. Parameterize `packages/core/src/sequences.ts` :: `SequenceStepDraft` and `SequenceDraft`, with `TokenId` as the default, so Studio can use `SequenceDraft<TokenAssetId>` while `packages/core/src/scores.ts` :: `ScoreDraft` remains canonical. Apply the same parameter to `packages/core/src/sequence-editor.ts` :: `SequenceStepPatch` and the timeline and graph projections. Keep `AudiofaceTokenDefinition.id`, `ResolvedToken.id`, `TokenLibraryEntry.sourceTokenId`, DOM bindings, Score token clips, and Score selectors as `TokenId`.

Keep `packages/core/src/playback.ts` :: `PlaybackIntent.tokenId` semantic. Add optional asset identity metadata for sequence and recorder provenance rather than forcing an origin qualified ID into canonical playback callers. Studio should compose a pure `TokenDefinitionResolver` from `getAudiofaceToken`, `listCanonicalTokenLibraryEntries`, and `useTokenLibraryStore.entries`, then pass it into sequence editing, timeline projection, and flow playback. Core must never import `@audioface/stores`.

The current `TokenLibraryId` is coupled to the recipe slug through `TOKEN_LIBRARY_ID_PATTERN`, `tokenLibraryIdTokenId`, and `token_id_mismatch`. This blocks opaque IDs and makes repeated copies collide. Slice 1 should decouple stable asset identity from editable semantic identity. Require the caller to supply a distinct origin qualified asset ID, or add one pure ID construction boundary with entropy supplied by Studio.

**Persistence correctness**

`packages/stores/src/tokenLibraryStore.ts` :: `persistedLibraryOrEmpty` must change in Slice 1. It converts malformed data, one invalid entry, or a stale derived fingerprint into an empty library with `status: "ready"` and `error: null`. Mixed valid and invalid entries disappear together, and a later mutation can replace the recoverable raw payload with the empty in memory state. That behavior conflicts with the promise that authored work can be saved and reloaded.

The minimum Slice 1 behavior is to preserve the raw persisted payload, surface a hydration error, and block a later write from silently replacing it. Per entry quarantine and recovery UI can follow if costly. Valid entries should survive an invalid sibling where feasible. `test/studio-token-library-store.test.mjs` :: `token library store falls back to empty entries for invalid persisted data` currently asserts the unsafe behavior and must be replaced.

`packages/core/src/token-library.ts` :: `validateTokenLibrary` also treats the fingerprint as persisted authority even though it is derived data. Save and migration should regenerate it through one core update operation. Validation currently omits several persisted fields, including complete token metadata, top level duration consistency, waveform, filter type, delay, attack, decay, timestamps, and some finite number checks. Slice 1 must validate every field produced by its blank and edit paths.

`packages/stores/src/tokenLibraryStore.ts` :: `saveLibraryEntry` expects a complete entry and does not refresh timestamps or fingerprint. `packages/core/src/token-library.ts` :: `createTokenLibraryEntry` preserves a supplied fingerprint, so spreading an old entry into it can retain stale derived data. Add one core update operation that preserves identity, provenance, creation time, and lock state while cloning the edited definition, regenerating duration and fingerprint, and accepting the new update time as an explicit input.

**Raw playback boundary**

`packages/core/src/playback.ts` :: `resolveTokenPlayback` always applies themed resolution. A neutral `ThemeSnapshot` cannot produce authored values because `packages/core/src/tokens.ts` :: `resolveMetrics` and `resolveLayer` still apply action and material profiles plus gain, duration, pitch, envelope, Q, and variation transforms.

Add an explicit `PlaybackMode` with `raw` and `themed` at the shared core playback boundary. Raw mode must preserve the saved definition's layer objects by value. Theme settings and step velocity must not alter those layers when exactness is the contract. `ResolvedPlayback` should record the mode so the inspector and recorder describe the result accurately. The existing engine limiter remains the final output safety stage.

Per asset persisted `raw`, `inherit`, and `blend` modes can be deferred. Slice 1 still needs both explicit Raw Audition and Themed Audition actions over the same saved entry.

**Duplication, dead code, and grooming**

- `apps/studio/src/app/useStudioSession.ts` :: `useStudioSession` duplicates theme, editor, and audition coordination now owned by `useSequenceAudition`.
- `apps/studio/src/app/useSelectedToken.ts` :: `useSelectedToken` is reachable only through the superseded session.
- `apps/studio/src/app/useSequenceAudition.ts` :: `THEME_AUDITION_INTERVAL_MS` and `shouldAuditionThemeControl` are imported from the otherwise superseded session. Move the policy to the active owner or a focused shared module.
- `apps/studio/src/components/audition/AuditionPanel.tsx` :: `AuditionPanel`, `apps/studio/src/components/inspector/SignalInspector.tsx` :: `SignalInspector`, and `apps/studio/src/components/tokens/TokensExplorer.tsx` :: `TokensExplorer` are unmounted scaffolding. Reuse the inspector and optionally the explorer in this slice, then remove any remaining unmounted path.
- `packages/core/src/sequence-timeline.ts` :: `buildEventBase` resolves the same token through `getAudiofaceToken` and `resolveSequenceStepPlayback`. Adding category to `ResolvedToken`, or returning the selected definition with the resolved playback, lets the timeline derive metadata from one resolution.
- `packages/core/src/token-library.ts` :: `TOKEN_LIBRARY_ID_PATTERN`, `tokenLibraryIdOrigin`, and `tokenLibraryIdTokenId` repeat parsing work. Consolidate them behind one parser and a runtime discriminator for `TokenAssetId`.
- `packages/core/src/token-library.ts` :: `resolveLibraryToken` has no production caller and overlaps `resolveTokenPlayback`. Remove it when the shared playback mode lands.
- `test/studio-dom.test.mjs` :: Studio structure cases preserve superseded files, prohibit a now justified authoring hook, and assert that the editor does not consume the store. Replace those assertions with the approved workflow contract.
- `test/studio-sequence-audition.test.mjs` :: source text assertions can continue to protect composition and audio clock scheduling, but they cannot prove save, reload, asset resolution, or raw layer equality.

Recommended grooming order: remove the superseded orchestration, extract focused token authoring state from the oversized active hook, consolidate asset lookup and ID parsing, then add the Slice 1 workflow. This keeps one authoring path and one playback path.

# Plan

**Decisions needed**

1. Approve `TokenAssetId` as a separate sequence reference type while keeping `TokenId` canonical. Recommended shape: generic sequence types defaulted to `TokenId`, with Studio explicitly using the wider asset type. This prevents an incidental Score Mode expansion.
2. Approve opaque, origin qualified `TokenLibraryId` values decoupled from `AudiofaceTokenDefinition.id`. Studio should supply entropy to a pure core constructor. Remove the deterministic default from `copyTokenToLibrary` so repeated copies cannot overwrite each other.
3. Define New from Blank as a valid audible starter rather than an empty layer array, which current validation rejects. Add a core factory with explicit defaults for category, action, material, accent, semantic ID, and one editable layer. The exact starter character is a product choice; the factory and validation ownership belong in core.
4. Define raw as exact saved layers with no theme or velocity transform. Keep the existing engine limiter and selected Studio volume. Persisted per asset `raw`, `inherit`, and `blend` policy moves to a later slice.
5. Approve loss aware hydration in this slice. The minimum acceptable policy preserves raw data, surfaces an error, and prevents silent overwrite. Per entry quarantine is preferred if it fits without creating a second persistence model.
6. Decide whether `TokensExplorer` becomes the combined library browser now. The smaller Slice 1 path is to inject canonical and user assets into `SequenceNodeEditor` and add library actions to `TokenEditor`, then revisit the explorer.

**Ordered implementation**

1. Groom the active Studio boundary. Move the 110 ms audition throttle out of `useStudioSession`, remove the superseded session and selection hook, and extract a focused authoring hook from `useSequenceAudition`. Reuse: `useStudioPlayback`, `useStudioTheme`, and `useTokenEditor`.
2. Separate asset identity from semantic token identity in core. Add `TokenAssetId`, one runtime parser or discriminator, generic sequence reference types, and a pure canonical plus custom resolver contract. Keep Score and DOM token types canonical. Reuse: `TokenLibraryEntry.id`, `listCanonicalTokenLibraryEntries`, and `getAudiofaceToken`.
3. Decouple `TokenLibraryId` from recipe slug identity and require unique IDs for copies. Add core blank and update entry operations. The update operation must preserve identity and provenance, refresh duration, fingerprint, and timestamps, and validate the result. Reuse: `copyTokenToLibrary`, `createTokenLibraryEntry`, `cloneAudiofaceTokenDefinition`, `calculateAudiofaceTokenDuration`, and `createSoundFingerprint`.
4. Replace `persistedLibraryOrEmpty` with loss aware hydration. Regenerate derived fingerprints through migration where safe, retain recoverable valid entries, preserve rejected raw data, expose an error state, and block accidental overwrite. Reuse: the existing Zustand store, version, storage key, actions, and memory storage test harness.
5. Add `raw` and `themed` to the shared core playback route. Raw returns a `ResolvedPlayback` whose layer values equal the authored definition. Themed continues through `resolveAudiofaceToken`. Record the mode and optional asset identity on the playback object. Reuse: `resolveTokenPlayback` and `AudiofaceEngine.playResolved`; remove the overlapping `resolveLibraryToken` wrapper.
6. Wire `useTokenLibraryStore` into the new active authoring hook. Compose canonical and persisted entries once, derive the selected entry from the selected sequence step, and make `useTokenEditor` accept that selected definition. Add Copy to Library, New from Blank, Save, and reload state. Keep timestamps explicit and prevent save while hydration is in error.
7. Route every sequence consumer through the same resolver. Update `SequenceStepPatch`, `updateSequenceStep`, `normalizeSequenceDraft`, `buildSequenceTimeline`, `buildSequenceGraph`, `resolveSequenceStepPlayback`, `SequenceNodeEditor`, and `auditionFlow`. Missing asset references must fail with one precise core error.
8. Add Raw Audition and Themed Audition in `TokenEditor`. Remount `SignalInspector` with `lastPlayback` so the user can verify which mode played and inspect the actual layer object. Sequence Play must resolve the saved library entry rather than the canonical source token.
9. Replace superseded source shape assertions with focused behavior tests, then retain only the structural checks that protect thin app composition, audio clock scheduling, cancellation, and package boundaries.

**Tests and gates**

Run the focused package and Studio suite during implementation:

```sh
node --test \
  test/token-library.test.mjs \
  test/studio-token-library-store.test.mjs \
  test/core-playback.test.mjs \
  test/sequence-editor-core.test.mjs \
  test/sequence-timeline-core.test.mjs \
  test/sequence-graph-core.test.mjs \
  test/score-timeline.test.mjs \
  test/studio-sequence-audition.test.mjs \
  test/studio-dom.test.mjs
```

Required focused cases:

- Copy preserves canonical data and creates distinct asset identities on repeated copies.
- Blank creation yields a valid, audible entry in the current layer model.
- Saving an edit refreshes duration, fingerprint, and update time while preserving asset ID, provenance, and creation time.
- A fresh store reloads the saved definition and asset identity.
- Mixed valid and invalid persisted entries remain recoverable and surface an error.
- Raw playback layers deep equal the saved definition. Themed playback differs predictably.
- Raw mode ignores theme and velocity transforms while preserving output limiter safety.
- Sequence normalization, timeline projection, graph projection, step audition, and full Play retain and resolve a user asset ID.
- Two user or team assets with the same semantic `TokenId` resolve to their own saved definitions.
- Unknown asset references fail with the exact asset ID in the error.
- Existing canonical fixtures, Score timeline behavior, DOM bindings, and canonical playback remain typed and behaviorally unchanged.

Run the repository gate after focused tests:

```sh
pnpm run check
```

Final acceptance proof in Studio:

1. Copy a canonical token and create one token from blank.
2. Edit each token and save.
3. Reload Studio and confirm both entries and authored values survive.
4. Assign a saved user asset to a sequence step.
5. Press Play and confirm the saved definition resolves rather than its canonical source.
6. Audition Raw and Themed, then compare `ResolvedPlayback.token.layers` with the saved definition. Raw must match by value; themed must show the declared transforms.
