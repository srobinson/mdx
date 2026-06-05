# Audioface Scout: Consumers and the Gate

Scope: `packages/engine` and everything downstream of it, plus the `pnpm run check` gate.
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/audioface` at `556b7c8c281b06be725d96c4c9eed192e9a7ce20`.
Mode: warroom Mode 1, scout and plan. No solution design. No repository writes.

Tree state verified before and after every command in this report: `git status --porcelain --untracked-files=all` empty, HEAD unchanged at `556b7c8`.

Gates observed live, read only:

| Command | Result |
|---|---|
| `node --test` | 295 tests, 295 pass, 0 fail, 1.67 s |
| `node bin/audioface.mjs validate` | passed, exit 0, "shipping tokens: 23" |
| `node scripts/golden-master/runner.mjs` | "Golden master matches 23 tokens across 10 render cases and 230 fingerprints", 0.97 s |
| `tsc -b` | not run, it writes `node_modules/.cache/tsc/packages.tsbuildinfo` and the write boundary forbids it |

---

## Reuse Map

Every capability a rewritten engine will need, with its existing owner as file plus symbol.

### The engine's own surface

`packages/engine/src/index.ts` exports five symbols. External reference counts come from a repo wide grep excluding `node_modules`, `.git`, and `docs`.

| Exported symbol | External consumers | Owner to keep or retire |
|---|---|---|
| `createAudiofaceEngine` | 3 code sites | Load bearing. The single construction point. |
| `AudiofaceEngine` (type) | 1 code site | Load bearing. Studio types its ref on it. |
| `resolveStartAt` | 1 site, a test only | Pure helper, `currentTime + 0.006 + max(0, offsetMs)/1000`. No production caller. |
| `AudiofaceEngineOptions` (type) | none | Never imported by name outside the engine file. |
| `PlayResolvedOptions` (type) | none | Never imported by name outside the engine file. Only a regex in `test/engine.test.mjs` names it. |

Internal owners inside the engine that a rewrite must re-own: `scheduleLayer`, `scheduleTone`, `scheduleNoise`, `scheduleFm`, `createLayerOutput`, `connectFilter`, `startAndStop`, `getNoiseBuffer`, `createOutput`, `createAudioContext`.

### Q1. Caller inventory of `packages/engine`

Three code callers. Two resolution declarations. Three transitive consumers.

**Direct, by package specifier `@audioface/engine`:**

1. `apps/studio/src/app/useStudioPlayback.ts`
   Imports `createAudiofaceEngine` and type `AudiofaceEngine`.
   Calls all four methods: `resume`, `setVolume`, `playResolved` (both with and without `{ offsetMs }`), `stopAll`.
   Constructs with `{ volume }` only, in `ensureEngine`. Never injects a `context`.

**Direct, by relative path `packages/engine/src/index.ts`:**

2. `scripts/audit/render.mjs`
   Imports `createAudiofaceEngine` inside `renderResolvedPlayback`.
   Constructs with `{ context }` or `{ context, volume }` where `context` is an `OfflineAudioContext` from `node-web-audio-api`. Calls `playResolved(playback)` with no options. Never calls `resume`, `setVolume`, or `stopAll`.

3. `test/engine.test.mjs`
   Imports `createAudiofaceEngine` and `resolveStartAt`.
   Also reads `packages/engine/src/index.ts` with `readFileSync` and asserts regexes against the source text. See Quality Map.

**Resolution declarations that must move with any rename:**

- `apps/studio/package.json`, dependency `"@audioface/engine": "workspace:*"`.
- `tsconfig.strict.json`, `compilerOptions.paths` entry `"@audioface/engine"`.

**Transitive consumers, through `scripts/audit/render.mjs#renderResolvedPlayback`:**

- `scripts/golden-master/golden-master.mjs` (`fingerprintToken`, `createGoldenMaster`)
- `scripts/audit/stage2.mjs` (`pnpm run audit:stage2`)
- `test/golden-master.test.mjs`

Nothing else in `packages/`, `apps/`, `scripts/`, `test/`, or `src/` reaches the engine. `apps/lab` does not: it uses its own copy, see Quality Map item 1.

### Playback input contract the engine consumes

| Capability | Owner |
|---|---|
| Playback envelope type | `packages/core/src/playback.ts#ResolvedPlayback` |
| The only field the engine reads | `playback.token.layers`, type `readonly AudiofaceLayer[]` |
| Layer union | `packages/core/src/tokens.ts#AudiofaceLayer` with `ToneLayer`, `NoiseLayer`, `FmLayer` |
| Resolved token shape | `packages/core/src/tokens.ts#ResolvedToken` |
| Exhaustiveness guard | `packages/core/src/runtime.ts#assertNever`, called by the engine's `scheduleLayer` |
| Volume scalar | `packages/core/src/tokens.ts#UnitInterval` |

The engine reads only `playback.token.layers`. It ignores `intent`, `mode`, `theme`, `token.metrics`, and `token.duration`. Layer fields consumed: `type`, `delay`, `duration`, `gain`, `attack`, `waveform`, `frequency`, `endFrequency`, `carrier`, `modulator`, `modIndex`, `filter.type`, `filter.frequency`, `filter.q`. `decay` is present on the layer types and never read.

### Patch resolution the rewrite will need

| Capability | Owner |
|---|---|
| Patch to resolved patch | `packages/core/src/patch-resolution.ts#resolvePatch` |
| Patch plus token to playback | `packages/core/src/playback.ts#resolvePatchPlayback` |
| Canonical token id to playback | `packages/core/src/playback.ts#resolvePlayback` |
| Resolved patch to legacy playback | `packages/core/src/playback.ts#toResolvedPlayback` |
| Patch to legacy definition | `packages/core/src/canonical-patches.ts#projectPatchToAudiofaceTokenDefinition` |
| Canonical patch and token corpus | `packages/core/src/canonical-patches.ts#CANONICAL_PATCH_TOKEN_PAIRS`, `#CANONICAL_PATCHES` |
| Legacy definition to patch | `packages/core/src/canonical-patches.ts#migrateTokenDefinition` |
| Semantic metric resolution | `packages/core/src/semantic-tokens.ts#resolveMetrics`, `#tokenResolveOptions` |
| Material coefficients | `packages/core/src/semantic-tokens.ts#MATERIAL_PROFILES` |
| Parameter address vocabulary | `packages/core/src/patches.ts#toParameterAddress`, `#parseParameterAddress` |
| Parameter registry | `packages/core/src/parameter-registry.ts` |
| Patch validation | `packages/core/src/patch-validation.ts#validatePatch` |

### Offline rendering and measurement

| Capability | Owner |
|---|---|
| Offline render of a `ResolvedPlayback` | `scripts/audit/render.mjs#renderResolvedPlayback` |
| Sample rate and window constants | `scripts/audit/render.mjs#OFFLINE_SAMPLE_RATE` (48000), `#OFFLINE_RENDER_SECONDS` (0.75) |
| Deterministic noise | `scripts/audit/render.mjs#withDeterministicRandom`, `#createDeterministicRandom` (sha256 seeded xorshift, replaces `Math.random`) |
| Acoustic descriptors | `scripts/audit/descriptors.mjs#measureAcousticFingerprint`, `#ACOUSTIC_QUANTIZATION`, `#describeSignal` |
| Fingerprint of one token and case | `scripts/golden-master/golden-master.mjs#fingerprintToken` |
| Full baseline build | `scripts/golden-master/golden-master.mjs#createGoldenMaster` |
| Render case matrix | `scripts/golden-master/golden-master.mjs#GOLDEN_MASTER_RENDER_CASES` (10 cases) |
| Tolerances | `scripts/golden-master/golden-master.mjs#ACOUSTIC_TOLERANCES` (9 metrics) |
| Comparison | `#compareAcousticFingerprints`, `#compareGoldenMasters`, `#formatGoldenMasterReport` |
| Committed baseline | `scripts/golden-master/baseline.jsonl` (231 lines: 1 metadata, 230 entries) |
| Runner and exit code | `scripts/golden-master/runner.mjs`, `#hasChanges` |

### Studio playback surface

| Capability | Owner |
|---|---|
| Engine lifetime and all four calls | `apps/studio/src/app/useStudioPlayback.ts#useStudioPlayback`, `#ensureEngine`, `#playResolved` |
| Canonical token audition | `#auditionToken` via `packages/core/src/playback.ts#resolvePlayback` |
| Draft definition audition | `#auditionTokenDefinition` via `packages/core/src/playback.ts#resolveTokenPlayback` |
| Flow audition with offsets | `#auditionFlow` via `packages/core/src/sequence-timeline.ts#resolveSequenceStepPlayback` |
| Cancellation | `#stopFlow` via engine `stopAll` |
| Layer rendering in the UI | `apps/studio/src/components/inspector/SignalInspector.tsx` |
| Layer formatting helpers | `apps/studio/src/app/studioHelpers.ts` |

### Q5. What Studio depends on, and what breaks

Studio touches the engine at exactly one file, `apps/studio/src/app/useStudioPlayback.ts`.

Symbols from `@audioface/engine`: `createAudiofaceEngine`, `AudiofaceEngine`.
Methods invoked: `resume()`, `setVolume(theme.volume)`, `playResolved(playback)`, `playResolved(playback, { offsetMs: step.delayMs })`, `stopAll()`.

Symbols from `@audioface/core` in the same file: `resolvePlayback`, `resolveTokenPlayback`, `resolveSequenceStepPlayback`, `toUnitInterval`, `errorMessage`, and types `AudiofaceTokenDefinition`, `PlaybackMode`, `PlaybackSource`, `ResolvedPlayback`, `SequenceDraft`, `ThemeSnapshot`, `TokenAssetId`, `TokenAssetLookup`, `TokenId`.

Would a change to the engine's public surface break Studio?

- Renaming or resigning `createAudiofaceEngine` or `AudiofaceEngine`: breaks, one file.
- Removing or resigning any of the four methods: breaks. `stopAll` and the `offsetMs` option have Studio as their only production caller.
- Changing the `AudiofaceLayer` union: breaks `apps/studio/src/components/inspector/SignalInspector.tsx`, which switches on `layer.type` with `assertNever` and reads layer fields directly, and `apps/studio/src/app/studioHelpers.ts`. Neither imports the engine, so this break is invisible from the engine's import graph.
- Changing `AudiofaceEngineOptions` beyond `{ volume }`: no Studio impact. Studio never passes a `context`.
- Changing context creation, resume semantics, or the master and limiter graph: no Studio type impact.

One non type coupling: `test/studio-dom.test.mjs` asserts the literal string `createAudiofaceEngine` appears in the playback hook source and does not appear in the app source. A rename fails that test on text, not on behavior.

### Q2. Where `AudiofaceTokenDefinition` lives, and what stands in the way

Declared once: `packages/core/src/tokens.ts#AudiofaceTokenDefinition`.
Sibling helpers in the same file: `#cloneAudiofaceTokenDefinition`, `#resolveAudiofaceToken`, `#calculateAudiofaceTokenDuration`.
Re-exported from `packages/core/src/index.ts`.

**Constructed by:**

- `packages/core/src/canonical-patches.ts#definitionFromRecipe`, from `packages/core/src/token-recipes.ts#TOKEN_RECIPES` (23 recipes, verified by import).
- `packages/core/src/canonical-patches.ts#projectPatchToAudiofaceTokenDefinition`, the Patch to legacy adapter. Signature `(patch, token, validationDomain: "authored" | "resolved" = "authored")`, returns `LegacyProjectionResult`, failing with `LegacyProjectionIssue` code `processor_not_projectable`.
- `packages/core/src/canonical-tokens.ts#AUDIOFACE_TOKENS` via its private `mustProject`.
- `packages/core/src/playback.ts#mustProject` and `#resolveRawToken`.
- `packages/core/src/token-library.ts`, entry projection in the library validation and view paths.
- `packages/core/src/token-assets.ts#CANONICAL_ASSETS`, `#createTokenAssetCatalog`.

**Load bearing consumers. These block the Phase 3 deletion.**

1. `packages/core/src/playback.ts#toResolvedPlayback`. Every sound the system renders, including the golden master, passes through `projectPatchToAudiofaceTokenDefinition(..., "resolved")` inside this function. The Patch model does not reach the engine directly today. This is the choke point.
2. `packages/core/src/playback.ts#resolveTokenPlayback` and `#resolveRawToken`, calling `packages/core/src/tokens.ts#resolveAudiofaceToken`. This is a second, non Patch resolution path.
3. `packages/core/src/sequence-timeline.ts#resolveSequenceStepPlayback` and `#resolveStepWithDefinition`, which call `resolveTokenPlayback`. Studio's flow playback and the whole timeline projection ride this path, so Studio flow audio never touches `resolvePatch`.
4. `packages/core/src/token-assets.ts`. `TokenDefinitionResolver` and `TokenAssetLookup` are typed to return `AudiofaceTokenDefinition`. Studio's asset catalog is built on these.
5. `packages/core/src/token-library.ts#TokenLibraryEntry` carries `readonly token: AudiofaceTokenDefinition`, and the persisted store shape flows from it. User saved assets on disk are in this shape.
6. `packages/core/src/sound-fingerprint.ts#createSoundFingerprint` accepts `AudiofaceTokenDefinition | ResolvedToken`.
7. Studio, six files: `app/useTokenEditor.ts` (every mutator returns one), `app/useTokenAuthoring.ts`, `app/useSequenceAudition.ts`, `app/useStudioPlayback.ts`, `app/authoringEntries.ts`, `components/sequence/SequenceNodeEditor.tsx`.

**Legacy consumers, safe to retire:**

- `packages/core/src/canonical-tokens.ts#resolveTokenDefinition`. Exported from `packages/core/src/index.ts`. Zero call sites anywhere in the repo. Dead.
- `packages/core/src/canonical-tokens.ts#AUDIOFACE_TOKENS`, `#listAudiofaceTokens`, `#getAudiofaceToken`. No production consumer. Only tests call them, and `test/studio-dom.test.mjs` and `test/studio-sequence-audition.test.mjs` assert with `assert.doesNotMatch` that Studio does not use them.

**What stands in the way today, stated plainly.** The engine's input type is the legacy layer union. `ResolvedPlayback.token` is a `ResolvedToken`, which is `AudiofaceTokenDefinition` minus `category` plus `material`, `duration`, and `metrics`. Deleting `AudiofaceTokenDefinition` requires the engine to accept a resolved Patch shape directly, which removes `toResolvedPlayback`'s projection, which is the same edit as the Phase 2 rewrite. The three secondary blockers are persistence (`token-library.ts`), the asset catalog types (`token-assets.ts`), and the non Patch resolution path (`resolveTokenPlayback`, used by Studio's editor and by every sequence timeline).

### Q4. What the golden master renders through

Both. The harness resolves through `resolvePatch` and renders through the real engine.

Chain, in order:

1. `scripts/golden-master/runner.mjs` calls `createGoldenMaster`.
2. `scripts/golden-master/golden-master.mjs#createGoldenMaster` iterates `packages/core/src/canonical-patches.ts#CANONICAL_PATCH_TOKEN_PAIRS` across `#GOLDEN_MASTER_RENDER_CASES`.
3. `#fingerprintToken` calls `packages/core/src/playback.ts#resolvePatchPlayback`.
4. `resolvePatchPlayback` calls `packages/core/src/semantic-tokens.ts#resolveMetrics`, then `packages/core/src/patch-resolution.ts#resolvePatch`, then `packages/core/src/playback.ts#toResolvedPlayback`.
5. `toResolvedPlayback` calls `packages/core/src/canonical-patches.ts#projectPatchToAudiofaceTokenDefinition` in `"resolved"` domain.
6. `scripts/audit/render.mjs#renderResolvedPlayback` builds an `OfflineAudioContext` and calls `packages/engine/src/index.ts#createAudiofaceEngine`, then `playResolved` inside `withDeterministicRandom`.
7. `scripts/audit/descriptors.mjs#measureAcousticFingerprint` measures the rendered buffer.
8. `#compareGoldenMasters` compares against `scripts/golden-master/baseline.jsonl`.

Determinism depends on the engine. `withDeterministicRandom` swaps `Math.random`, and the engine's `getNoiseBuffer` is the consumer of that randomness. A rewrite that changes when or how often the engine draws random values changes every noise fingerprint even if the synthesis math is identical.

**If a rewritten engine changed a sound, the precise file and command that goes red:**

- Command: `pnpm run audio:golden`, that is `node scripts/golden-master/runner.mjs`.
- File that fails: `scripts/golden-master/baseline.jsonl`, compared entry by entry.
- Failure surface: `runner.mjs#hasChanges` sets `process.exitCode = 1` and `formatGoldenMasterReport` prints one line per drifted metric as `<tokenId> [<caseId>] <metric>: expected ..., actual ..., delta ..., tolerance ...`.
- Blast size: 230 fingerprints, 23 tokens times 10 render cases, 9 metrics each.

A second, weaker red exists inside `pnpm test`: `test/golden-master.test.mjs`, the case named "golden cases bind shipping token playback to Patch playback", asserts exactly 230 comparisons where `resolvePatchPlayback` and `resolveTokenPlayback` agree. That fails if the rewrite changes resolution without changing the legacy projection in step. It does not fail on engine scheduling changes, because it never renders.

### Q3. What `pnpm run check` gates, command by command

`"check": "pnpm run typecheck && pnpm test && pnpm run validate && pnpm run audio:golden"` in `package.json`.

**1. `pnpm run typecheck` = `tsc -b`**
`tsconfig.json` references `tsconfig.packages.json` and `apps/studio/tsconfig.json`.
`tsconfig.packages.json` includes `packages/**/*.ts` only, extending `tsconfig.strict.json` (strict, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noUnusedLocals`, `verbatimModuleSyntax`, `skipLibCheck: false`).
Covered: `packages/*`, `apps/studio`.
Not covered: root `src/`, `scripts/`, `test/`, `apps/lab`. All of those are `.js` or `.mjs`. The golden master harness, the offline renderer, and the descriptors are therefore untyped.

**2. `pnpm test` = `node --test`**
41 test files, all under `test/`. Observed 295 tests, 295 pass.
Only two of them reach the engine: `test/engine.test.mjs` and `test/golden-master.test.mjs`.

**3. `pnpm run validate` = `node bin/audioface.mjs validate`**
Runs `src/validator.js#validateProject`. Its entire input is the legacy root `src/` model: `src/tokens.js#TOKENS`, `src/themes.js#ACTION_PROFILES`, `src/catalog.js#validateCatalog`, `src/sequences.js#listSequences`, `src/timeline.js#buildSequenceTimeline`, `src/sequence-graph.js#validateSequenceGraph`, `src/sequence-editor.js`, `src/contracts.js#buildAudiofaceContract`. It checks required contract files, the JSON schema's required fields, generated contract fields, absence of audio binaries, and token, verb, sequence, and timeline invariants.
It contains no reference to `packages/core` or `packages/engine`.

**4. `pnpm run audio:golden` = `node scripts/golden-master/runner.mjs`**
The acoustic comparison described in Q4.

**Where the holes are.** If the engine's rendered output changed:

| Gate command | Still passes? | Why |
|---|---|---|
| `pnpm run typecheck` | Yes | Types are unchanged by a scheduling or synthesis change. |
| `pnpm test` | Yes, unless the change also removes a pinned source string | Neither engine touching test compares against committed values. |
| `pnpm run validate` | Yes | Validates the legacy `src/` model. Never reaches the engine or core. |
| `pnpm run audio:golden` | No, goes red | The only absolute acoustic anchor. |

One of four gate commands is an acoustic gate. Three are blind to sound.

Specific holes, with evidence:

- **`pnpm test` has no absolute acoustic anchor.** Grepping `baseline` across `test/` returns only `test/golden-master.test.mjs` cases that parse the baseline, count entries and token ids, reject a non finite metric, and round trip serialization. None compare a freshly rendered fingerprint to a committed value. The rendering tests in that file are self relative: determinism compares two renders of the same input, and the perturbation cases compare a perturbed render against an unperturbed one from the same code. All of that stays green under a uniformly changed engine.
- **`test/engine.test.mjs` tests source text, not behavior.** Five of its assertions call `readFileSync("packages/engine/src/index.ts", "utf8")` and match regexes: `createDynamicsCompressor`, `currentTime \+ 0\.006`, `linearRampToValueAtTime`, `new WeakMap<AudioContext, AudioBuffer>`, `source\.loop = true`, `node\.stop\(start \+ duration \+ 0\.025\)`, `PlayResolvedOptions`, `offsetMs`, `resolveStartAt\(currentContext\.currentTime, options\?\.offsetMs\)`, `new Set<AudioScheduledSourceNode>\(\)`, `addEventListener\("ended"`, `tracked\.delete\(node\)`. This inverts the intended signal: a behavior preserving refactor fails, a behavior changing edit that keeps the strings passes.
- **`validate` protects the wrong copy.** It reports "shipping tokens: 23" from `src/tokens.js#TOKENS`, while the shipped model has its own 23 in `packages/core/src/token-recipes.ts#TOKEN_RECIPES`. Both counts verified by direct import.
- **The harness itself is untyped and ungated by `tsc`.** A mistake in `scripts/golden-master/golden-master.mjs` or `scripts/audit/render.mjs` has no compiler check behind it.

---

## Quality Map

Guardrail check on the consumer layer. Nothing exceeds 700 LOC. Largest files: `apps/lab/src/app.js` 654, `packages/core/src/parameter-registry.ts` 669, `packages/core/src/canonical-patches.ts` 649, `src/tokens.js` 649, `packages/core/src/score-timeline.ts` 591. `packages/engine/src/index.ts` is 258 with a 12 line manifest. Studio's largest source is `components/editor/TokenEditor.tsx` at 299. No function in the engine approaches 150 lines.

The problems are not size. They are parallel implementations and tests that assert on text.

### Q6. Remove before the rewrite lands

**1. Two engines. `src/audioface.js#createAudiofaceEngine` duplicates `packages/engine/src/index.ts#createAudiofaceEngine`.**
Function for function: `scheduleToken` against `scheduleLayer`, plus `scheduleNoise`, `scheduleTone`, `scheduleFm`, `createLayerOutput`, `connectFilter`, `startAndStop`, `getNoiseBuffer`, and the same limiter settings, the same `0.34` default master gain, the same `currentTime + 0.006` lead, the same `+ 0.025` stop margin, the same `white * 0.66 + low * 2.4` noise shaping.
Divergences: the legacy copy has no `stopAll`, no source tracking, no `offsetMs`, and carries an extra `play(tokenOrId, options)` that resolves through `src/tokens.js#resolveToken`.
Only consumer: `apps/lab/src/app.js`. Highest priority deletion. Leaving it means the rewrite ships a second, stale scheduler that nothing regenerates and no acoustic gate covers.

**2. Two token models, 23 tokens each, pinned to each other by a test.**
`src/tokens.js#TOKENS` (649 lines) against `packages/core/src/token-recipes.ts#TOKEN_RECIPES` to `#CANONICAL_PATCH_TOKEN_PAIRS`.
`test/lab-studio-audio-parity.test.mjs` asserts that `packages/core/src/playback.ts#resolvePlayback` produces the same resolved token as `src/themes.js#createAudioface().resolve` for every token, and that the variation seed model matches.
This is the rewrite's sharpest hazard. It binds new core resolution to a hand written legacy JS implementation that the Phase 2 work has no intention of updating. Decide its fate before the rewrite, not during.

**3. `pnpm run validate` gates only the legacy model.** See Q3. Either repoint `src/validator.js#validateProject` at `packages/core`, or retire the command from `check` as part of the same wave that deletes root `src/`. Leaving it is a gate that costs time and proves nothing about what ships.

**4. Dead export: `packages/core/src/canonical-tokens.ts#resolveTokenDefinition`.** Exported from `packages/core/src/index.ts`, zero call sites in `packages/`, `apps/`, `scripts/`, `test/`, or `src/`.

**5. Test only exports.** `AUDIOFACE_TOKENS`, `listAudiofaceTokens`, `getAudiofaceToken` in `packages/core/src/canonical-tokens.ts` have no production consumer. Two Studio tests assert that Studio deliberately avoids them.

**6. Unused engine type exports.** `AudiofaceEngineOptions` and `PlayResolvedOptions` in `packages/engine/src/index.ts` are never imported by name anywhere. Keep them only if the rewrite intends them as public vocabulary.

**7. `resolveStartAt` has no production caller.** Its only external reference is `test/engine.test.mjs`. It is a genuinely pure helper and a good seam, but today it is exported for a test.

**8. Duplicated `clamp` family.** `packages/core/src/runtime.ts#clamp` against `src/tokens.js#clamp` and `src/tokens.js#clamp01`. A third variant, `apps/lab/src/theme-workbench.js#clampVariationControl`. The `packages/` side was already consolidated by the flow persistence slice 2 work; the root `src/` side was not.

**9. Source text tests across three files.** `test/engine.test.mjs`, `test/studio-dom.test.mjs`, and `test/studio-sequence-audition.test.mjs` use `readFileSync` plus `assert.match` and `assert.doesNotMatch` against production sources. Named patterns include `createAudiofaceEngine`, `resolvePlayback`, `resolveTokenPlayback`, `resolveSequenceStepPlayback\(draft, step, lookup, nextTheme, at\)`, `cloneAudiofaceTokenDefinition`, `source: AudiofaceTokenDefinition \| null`, `token: AudiofaceTokenDefinition \| null`. Every one of these fails on a behavior preserving rename. They will produce a wave of false red during the rewrite and train the team to edit tests to match code.

**10. Two resolution paths to the same sound.** `resolvePatchPlayback` (Patch) and `resolveTokenPlayback` (legacy definition) both produce a `ResolvedPlayback`. `test/golden-master.test.mjs` proves they agree across 230 cases. Studio uses the Patch path for canonical token audition and the legacy path for draft editing and for every sequence step. Two paths, one output contract, one test holding them together. The rewrite should collapse them, and until it does, any engine change has to keep both honest.

### Boundary observations

- Direction is clean where it counts. `packages/engine` depends on `@audioface/core` only. `packages/core` never imports the engine. Studio depends on both. No cycle.
- Two import styles reach the same module: `@audioface/engine` from Studio, and the relative path `../../packages/engine/src/index.ts` from `scripts/audit/render.mjs` and `test/engine.test.mjs`. Only the package specifier is covered by `tsconfig.strict.json` paths, so a package move breaks the script and the test silently until runtime.
- `apps/lab` imports root `src/` directly and never imports any workspace package. Root `src/` imports nothing from `packages/`. They are two disjoint stacks sharing a repo, joined only by `test/lab-studio-audio-parity.test.mjs`.
- The engine's only impurity is `createAudioContext` and `Math.random` in `getNoiseBuffer`. Everything else takes its context as an argument, which is why `scripts/audit/render.mjs` can drive it offline. Preserve that property.

---

## Plan

Ordered so each step ends verifiable and no step depends on a later one.

**Step 0. Freeze the acoustic anchor.**
Confirm `pnpm run audio:golden` is green at the pre rewrite commit and record the exact line. Observed at `556b7c8`: "Golden master matches 23 tokens across 10 render cases and 230 fingerprints."
Gate: `node scripts/golden-master/runner.mjs`, exit 0.

**Step 1. Close the gate holes before touching the engine.**
The rewrite needs a gate that fails for the right reason. In order:
1a. Replace the `readFileSync` regex assertions in `test/engine.test.mjs` with behavioral tests driven through `scripts/audit/render.mjs#renderResolvedPlayback` and an `OfflineAudioContext`. The rendering path already exists and is used by `test/golden-master.test.mjs`, so this is reuse, not new machinery.
1b. Add one test under `test/` that compares freshly rendered fingerprints against `scripts/golden-master/baseline.jsonl`, so `pnpm test` alone carries an absolute acoustic anchor. `#compareGoldenMasters` and `#parseGoldenMasterText` already exist.
1c. Decide on `pnpm run validate`: repoint at `packages/core` or drop it from `check`. Do not leave it validating a model that is scheduled for deletion.
Gate: `pnpm test` and `pnpm run audio:golden` both green, and 1a's new tests demonstrably fail when a layer gain is perturbed.

**Step 2. Delete the duplicate engine and settle the parity test.**
Remove `src/audioface.js` and repoint `apps/lab/src/app.js` at `@audioface/engine`, or retire `apps/lab` outright. Then take an explicit decision on `test/lab-studio-audio-parity.test.mjs`: keep it and accept that root `src/` must track every core change, or delete it together with the legacy model it pins.
Gate: `pnpm run check`, plus a manual `pnpm run start:lab` smoke if `apps/lab` survives.

**Step 3. Remove dead and test only surface.**
`packages/core/src/canonical-tokens.ts#resolveTokenDefinition`. Then decide on `AUDIOFACE_TOKENS`, `listAudiofaceTokens`, `getAudiofaceToken`, and on the engine's unused type exports.
Gate: `pnpm run typecheck` and `pnpm test`.

**Step 4. Write the engine contract down before rewriting.**
State the input contract explicitly: which fields of `ResolvedPlayback` the engine may read, and the four methods it must expose. Today the answer is `playback.token.layers` and `resume`, `setVolume`, `playResolved`, `stopAll`. Two callers construct with `{ volume }`, one with `{ context }` or `{ context, volume }`.
Gate: none. This is the artifact the rewrite reviews against.

**Step 5. Rewrite the engine against the frozen baseline.**
Every intermediate commit keeps `pnpm run audio:golden` green, or the drift is accepted deliberately with `--update` and the diff to `scripts/golden-master/baseline.jsonl` reviewed metric by metric. Note that `runner.mjs --update` prints the accepted drift before writing, which is the review surface.
Gate: `pnpm run check` on every commit.

**Step 6. Collapse the two resolution paths, then retire `AudiofaceTokenDefinition`.**
Migrate in this order, because each consumer is a separate blast radius:
`toResolvedPlayback` first, since it is the choke point every render passes through.
Then `resolveTokenPlayback` and `resolveRawToken`, which unblocks `sequence-timeline.ts#resolveStepWithDefinition` and Studio's editor and flow audition together.
Then `token-assets.ts` (`TokenDefinitionResolver`, `TokenAssetLookup`) and `token-library.ts` (`TokenLibraryEntry.token`), which is where persisted user data lives and needs a migration, not a retype.
Then `sound-fingerprint.ts#createSoundFingerprint`.
Studio last, six files, led by `app/useTokenEditor.ts`.
Only after all of them: delete `projectPatchToAudiofaceTokenDefinition`, `LEGACY_OPTIONAL_PRESENCE`, `LegacyProjectionResult`, `LegacyProjectionIssue`, and the type itself.
Gate: `pnpm run check` at each sub step, plus a Studio smoke covering token audition, draft edit audition, and flow playback with a non zero step delay, since `offsetMs` and `stopAll` have Studio as their only production caller.

### Searches run

`grep -rn "@audioface/engine\|packages/engine"` across `*.ts`, `*.tsx`, `*.js`, `*.mjs`, `*.json`, `*.md`, excluding `node_modules` and `.git`.
`grep -rn "AudiofaceTokenDefinition"` and `"projectPatchToAudiofaceTokenDefinition"` repo wide.
`grep -rn` per symbol for `createAudiofaceEngine`, `AudiofaceEngine`, `AudiofaceEngineOptions`, `PlayResolvedOptions`, `resolveStartAt`, `resolveAudiofaceToken`, `resolveTokenPlayback`, `resolveTokenDefinition`, `resolvePatchPlayback`, `resolvePlayback`, `resolveSequenceStepPlayback`, `toResolvedPlayback`, `createRawAudiofaceMetrics`, `cloneAudiofaceTokenDefinition`, `AUDIOFACE_TOKENS`, `listAudiofaceTokens`, `getAudiofaceToken`, `TOKEN_RECIPES`, `assertNever`, `clamp`, `clamp01`, `errorMessage`, `resolveToken`.
`grep -rn "baseline\|compareGoldenMasters" test/` and `grep -rln "render.mjs\|packages/engine" test/`.
`git ls-files` with `wc -l` for every package, `apps/studio`, `apps/lab`, root `src/`, `scripts/`, `test/`.
Counts confirmed by direct import: `TOKEN_RECIPES.length` is 23, `src/tokens.js#TOKENS.length` is 23.

No capability listed in the Reuse Map is marked "none found". Every one has a named owner.
