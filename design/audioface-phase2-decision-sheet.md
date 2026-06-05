# Audioface Phase 2 Decision Sheet

Repo at `556b7c8`, tree clean. Every owner and count below re-verified by read only grep and runtime import.

## Capability table

| Capability | Existing owner | Disposition |
|---|---|---|
| Patch to resolved value | `packages/core/src/patch-resolution.ts#resolvePatch`, `#PatchResolver` | reuse |
| Parameter address grammar | `packages/core/src/patches.ts#parseParameterAddress`, `#layerParameterAddress` | reuse |
| Parameter metadata | `packages/core/src/parameter-registry.ts#PATCH_CONTROL_REGISTRY`, 39 entries: 33 parameter, 6 structure | reuse |
| Patch validation | `packages/core/src/patch-validation.ts#validatePatch` | reuse |
| Engine lifecycle and injected context | `packages/engine/src/index.ts#createAudiofaceEngine` | reuse |
| Clock placement, six millisecond lead | `packages/engine/src/index.ts#resolveStartAt` | reuse |
| Tone, noise, FM construction | `packages/engine/src/index.ts#scheduleTone`, `#scheduleNoise`, `#scheduleFm` | reuse |
| Source lifetime and cancellation | `packages/engine/src/index.ts#startAndStop` | reuse |
| Offline render adapter | `scripts/audit/render.mjs#renderResolvedPlayback` | reuse |
| Acoustic measurement and gate | `scripts/audit/descriptors.mjs#measureAcousticFingerprint`, `scripts/golden-master/golden-master.mjs#createGoldenMaster` | reuse |
| Render boundary | `packages/core/src/playback.ts#toResolvedPlayback` | deviate: drops stable ids and structure |
| Master dynamics stage | `packages/engine/src/index.ts#createOutput` | deviate: no Patch address exists |
| Noise realization, `SRC-16` | `packages/engine/src/index.ts#getNoiseBuffer`, `#noiseBuffers` | deviate: formula is current acoustic anchor |
| Layer amplitude envelope, `AMP-04`, `AMP-05`, `AMP-06` | `packages/engine/src/index.ts#createLayerOutput` | refactor-first |
| Patch amplitude constants, `AMP-02`, `AMP-16.ramp-ms`, `AMP-16.epsilon` | none found, literals in `#createLayerOutput` line 203 and `#setVolume` | refactor-first |
| Output level and mute, `OUT-01`, `OUT-02` | `packages/core/src/playback.ts#outputParameterMap`, filtered out at `#toResolvedPlayback` | refactor-first |
| Context capability, `OUT-12.sample-rate`, `OUT-12.latency-hint` | `packages/engine/src/index.ts#createAudioContext` | refactor-first |
| Patch duration, `TIM-01` | `packages/core/src/patch-resolution.ts#deriveParameter` against `ResolvedPatch.durationMs` | refactor-first |
| Layer filter reach | `packages/engine/src/index.ts#connectFilter`, noise only | refactor-first |
| Deterministic offline noise | `scripts/audit/render.mjs#withDeterministicRandom`, global `Math.random` swap | refactor-first |
| Studio engine lifetime | `apps/studio/src/app/useStudioPlayback.ts#ensureEngine`, no unmount cleanup | refactor-first |
| Pitch fine tune and ratio, `PCH-03`, `PCH-09` | `packages/core/src/canonical-patches.ts#projectLegacyLayerFields` discards both | defer |
| Pitch envelope, `PCH-05`, `PCH-06` | none found | defer |
| Filter envelope, `FLT-14`, `FLT-15.attack-ms`, `FLT-15.decay-ms` | `packages/engine/src/index.ts#connectFilter`, static frequency only | defer |
| Impulse source, `SRC-30` | none found, rejected by `#requireImplementedLayer` | defer |
| Output chain DC block, `FXP-32` | none found, rejected by `#requireImplementedOutput` | defer |

## Contradictions

Two, both against the consumers scout.

1. `resolveStartAt` production status. Consumers scout: "1 site, a test only. No production caller", repeated in its grooming list as exported for a test. Engine scout: it owns the scheduling lead. Engine survives. `packages/engine/src/index.ts:68` calls it inside `playResolved`. It has one internal production caller and no external one. The function is load bearing; only the export is open.
2. `test/engine.test.mjs` assertion count. Consumers scout: "Five of its assertions call `readFileSync`". Verified: three tests call it, at lines 16, 33 and 42, carrying twelve regex assertions. The twelve patterns it then lists are correct; the count is not.

Cross checked clean, both scouts agreeing and both right: the 33 parameter keys with 12 current bindings, and `layer.decay` being read by neither `packages/engine/src/index.ts` nor `src/audioface.js`.

## Gate holes

- `tsc -b` includes `packages/**/*.ts` and `apps/studio` only, so `scripts/`, `test/`, root `src/` and `apps/lab` are unchecked and the entire render harness is untyped.
- `pnpm test` has no absolute acoustic anchor: `test/golden-master.test.mjs` parses `scripts/golden-master/baseline.jsonl` and counts 23 tokens, and never compares a fresh render to a committed value.
- The rendering tests in that file are self relative, comparing a quiet render against a loud one from the same code, so a uniformly changed engine stays green.
- `test/engine.test.mjs` asserts twelve regexes against engine source text, so a behavior preserving rename goes red while a behavior changing edit that keeps the strings goes green.
- `pnpm run validate` reads only root `src/`; `grep "packages/" src/validator.js bin/audioface.mjs` returns nothing.
- One of four `check` commands renders audio. `typecheck`, `test` and `validate` are all blind to sound.
- `AMP-06` is resolvable across 3 to 350 ms with zero acoustic effect, because no gate covers an address the engine never reads.
- Non canonical valid boundaries are ungated: resolved attack floors at 0.35 ms against the engine's 0.5 ms, resolved attack reaches 40 ms against a 4 ms minimum duration, and 500 ms delay plus 350 ms duration exceeds the 0.75 s `OFFLINE_RENDER_SECONDS` window.
- A rewrite that changes how often the engine draws from the swapped `Math.random` moves every noise fingerprint even with identical synthesis math.

## Grooming before the rewrite

- Delete `src/audioface.js#createAudiofaceEngine`, 157 lines carrying 9 declarations that share names with the package engine; sole consumer is `apps/lab/src/app.js:10`.
- Remove the root `package.json:13` export `"./audio": "./src/audioface.js"` in the same commit.
- Delete `packages/core/src/canonical-tokens.ts#resolveTokenDefinition`, declared at line 48, re-exported at `packages/core/src/index.ts:14`, zero call sites.
- Decide `packages/core/src/canonical-tokens.ts#AUDIOFACE_TOKENS`, `#listAudiofaceTokens`, `#getAudiofaceToken`: test only, and two Studio tests assert Studio avoids them.
- Decide `packages/engine/src/index.ts#AudiofaceEngineOptions` and `#PlayResolvedOptions`: exported, never imported by name anywhere.
- Fold `src/tokens.js#clamp`, `#clamp01` and `apps/lab/src/theme-workbench.js#clampVariationControl` into `packages/core/src/runtime.ts#clamp`.
- Replace the twelve source text regexes in `test/engine.test.mjs` with renders through `scripts/audit/render.mjs#renderResolvedPlayback`.
- Retire the same `readFileSync` pattern in `test/studio-dom.test.mjs` and `test/studio-sequence-audition.test.mjs` before it produces false red during the rewrite.
- Settle `test/lab-studio-audio-parity.test.mjs`, which pins `packages/core/src/playback.ts#resolvePlayback` to `src/themes.js#createAudioface().resolve` across two separate 23 token models.
- Deduplicate `scripts/audit/descriptors.mjs#energyWeightedCentroid` against `#energyWeightedMetric`, and the nine metric identities repeated across `descriptors.mjs` and `golden-master.mjs`.
- Repoint or retire `src/validator.js#validateProject` before `check` leans on it through the rewrite.

## The three hardest calls

1. Does the engine consume `ResolvedPatch` directly, or keep `packages/core/src/playback.ts#toResolvedPlayback` and the legacy `AudiofaceLayer` union? Direct consumption deletes the projection every rendered sound passes through, including all 230 golden fingerprints, and it is the same edit as retiring `AudiofaceTokenDefinition`, which six Studio files and the persisted `packages/core/src/token-library.ts#TokenLibraryEntry` shape depend on. Options: cut now and absorb the persistence migration, or ship the rewrite behind the projection and cut in Phase 3.

2. Does `scripts/golden-master/baseline.jsonl` stay frozen, or is deliberate drift accepted? Fixing silent `AMP-06`, `durationMs` derived from `TIM-03` alone while `TIM-01` uses `TIM-02 + TIM-03`, and the 0.5 ms attack floor under a 0.35 ms resolved minimum, each changes sound by definition. Options: correct the semantics and rewrite the baseline with a metric by metric reviewed diff, or preserve current sound exactly and record all three as intended behavior.

3. Do root `src/` and `apps/lab` survive? `test/lab-studio-audio-parity.test.mjs` binds new core resolution to a hand written legacy JS model that Phase 2 will not update, and `pnpm run validate` gates that model rather than what ships. Options: delete both stacks in the same wave, repoint `apps/lab` at `@audioface/engine` and keep parity as a real gate, or keep the spike and drop the parity test.
