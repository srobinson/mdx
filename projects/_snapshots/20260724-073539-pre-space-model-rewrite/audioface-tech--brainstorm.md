# Audioface technical evolution brainstorm

## Highest leverage move

Stabilize a versioned Audioface sound spec plus deterministic resolver as the portable core, then make Rust, npm, and PyPI ship that same contract.

## Ranked ideas

1. Make the sound spec the product boundary.

   Define `audioface.schema.json` with `specVersion`, `tokens`, `materials`, `themeControls`, `presets`, `sequences`, and `layerPrimitives`. The spec owns semantic token names, ranges, layer types, theme resolution semantics, and sequence timing. Web Audio scheduling stays outside the spec.

   Example contract:

   ```json
   {
     "$schema": "https://audioface.dev/spec/v0.1/audioface.schema.json",
     "specVersion": "0.1.0",
     "tokens": {
       "button.press": {
         "action": "press",
         "material": "ceramic",
         "layers": [{ "type": "noise", "duration": 0.014, "gain": 0.18 }]
       }
     }
   }
   ```

   `AUDIO.md` should become generated narrative documentation over this contract, so agents read the same truth that runtimes validate.

2. Move token and theme resolution into a Rust core crate.

   The existing split between `src/tokens.js`, `src/themes.js`, and `src/audioface.js` is the right boundary. Port resolution, clamping, seeded variation, material profiles, presets, and sequence validation into a Rust crate named `audioface`. The crate should not play sound. It compiles semantic intent into a stable `ResolvedToken`.

   Rust API shape:

   ```rust
   use audioface::{AudiofaceSpec, PlayOptions, Theme};

   let spec = AudiofaceSpec::bundled();
   let theme = Theme::builder()
       .material("ceramic")
       .density(0.4)
       .politeness(0.72)
       .contrast(0.48)
       .build()?;
   let resolved = spec.resolve("button.press", &theme, PlayOptions::new().seed(12))?;
   ```

   Core responsibilities: parse, validate, normalize, resolve, serialize, generate fixtures, and expose schema metadata.

3. Use npm as the browser runtime and adapter surface.

   The npm package `audioface` should wrap the wasm resolver and own playback. It includes the Web Audio scheduler, TypeScript types, bundled default spec, JSON schema export, SSR safe construction, and framework adapters through subpath exports.

   Browser API:

   ```ts
   import { createAudioface } from "audioface";

   const audioface = await createAudioface({
     preset: "studio",
     volume: 0.34,
     autoResume: true
   });

   audioface.play("button.press", { velocity: 0.8 });
   audioface.setTheme({ material: "glass", contrast: 0.6 });
   audioface.setVolume(0.22);
   audioface.mute();
   audioface.dispose();
   ```

   Adapter exports can stay inside one npm package at first:

   ```ts
   import { useAudioface } from "audioface/react";
   import { createAudiofaceStore } from "audioface/svelte";
   import { useAudiofacePlugin } from "audioface/vue";
   import "audioface/element";
   ```

   Those adapters should only bind lifecycle, gesture unlock, and theme context. They should not duplicate resolver or scheduler logic.

4. Use PyPI for design system tooling, validation, and agents.

   The PyPI package `audioface` should expose native Rust bindings through PyO3 plus a CLI. Its job is contract work, not playback.

   Python API:

   ```py
   from audioface import Spec, Theme

   spec = Spec.bundled()
   theme = Theme(material="ceramic", density=0.4, politeness=0.72)
   token = spec.resolve("button.press", theme, seed=12)
   spec.write_audio_md("AUDIO.md")
   ```

   CLI shape:

   ```sh
   audioface validate AUDIO.md audioface.json
   audioface resolve --token button.press --theme studio --seed 12
   audioface export-fixtures fixtures/audioface-v0.1
   audioface audit-design-system design-tokens.json
   ```

   This makes Audioface useful in Python based build pipelines, documentation generation, agent checks, and CI without pretending Python is a realtime audio target.

5. Keep one package per registry until pressure proves otherwise.

   Package strategy:

   `crates.io/audioface`: canonical spec types, resolver, validator, fixture generator, serde models, optional `wasm` and `python` features.

   `npm/audioface`: browser runtime, Web Audio scheduler, wasm resolver, TypeScript types, schema exports, default themes, framework subpath adapters, web component.

   `pypi/audioface`: Python bindings, CLI, validation tools, documentation generation, fixture comparison, agent facing inspection helpers.

   Avoid splitting npm into `@audioface/core`, `@audioface/react`, and `@audioface/web` before there is actual install size or release cadence pressure. Subpath exports preserve clean boundaries without multiplying packages.

6. Treat SSR and gesture unlock as first class runtime states.

   `createAudioface()` should be safe during SSR and static rendering. Server execution returns a disabled controller that can resolve metadata but cannot schedule sound. Browser hydration upgrades it after the first user gesture.

   Runtime states:

   ```ts
   type AudiofaceState = "server" | "locked" | "ready" | "muted" | "disposed";
   ```

   API implications:

   ```ts
   const audioface = createAudioface({ theme, ssr: true });
   audioface.resolve("command.confirm");
   await audioface.unlock(event);
   audioface.play("command.confirm");
   ```

   Do not queue sounds that occurred before unlock by default. The low fatigue promise is better served by silence than delayed surprise playback.

7. Version the spec separately from package releases.

   Every resolved token should carry `specVersion`, `resolverVersion`, and `tokenVersion`. Packages can patch bugs without changing the sound contract. Any semantic change to token math, layer primitives, material profiles, or default presets increments the spec.

   Compatibility rule:

   ```ts
   audioface.supportsSpec("0.1");
   audioface.resolve("button.press", { specVersion: "0.1.0" });
   ```

   Runtimes should reject unknown spec majors and warn on unknown token ids with a typed error:

   ```ts
   class AudiofaceTokenError extends Error {
     code = "UNKNOWN_TOKEN";
     tokenId: string;
   }
   ```

8. Build deterministic CI around resolver fixtures and acoustic snapshots.

   The Rust resolver should generate golden JSON for every preset, material, token, sequence, and seed. npm and PyPI must compare their outputs against those fixtures exactly.

   CI layers:

   ```sh
   cargo test
   npm test
   python -m pytest
   audioface export-fixtures fixtures/current
   audioface compare-fixtures fixtures/current fixtures/golden
   ```

   Browser audio tests should use `OfflineAudioContext` and compare envelope, duration, peak, RMS, and coarse spectral buckets. Avoid strict PCM hashes across engines because browser DSP differences will create false failures.

## Concrete public surface

```ts
type AudiofaceToken =
  | "button.press"
  | "button.release"
  | "toggle.snap"
  | "list.select"
  | "command.confirm"
  | "field.reject"
  | "panel.dock"
  | "panel.undock"
  | "slider.tick"
  | "drag.start"
  | "drag.end"
  | "toast.arrive";

type AudiofaceTheme = {
  material?: "ceramic" | "rubber" | "plastic" | "glass" | "metal" | "wood" | "paper";
  density?: number;
  politeness?: number;
  contrast?: number;
  mechanical?: number;
  warmth?: number;
  variation?: number;
  volume?: number;
};

type Audioface = {
  play(token: AudiofaceToken, options?: PlayOptions): ResolvedToken;
  resolve(token: AudiofaceToken, options?: PlayOptions): ResolvedToken;
  sequence(id: string): AudiofaceSequence;
  setTheme(theme: AudiofaceTheme): void;
  setVolume(value: number): void;
  mute(value?: boolean): void;
  unlock(event?: Event): Promise<void>;
  dispose(): void;
};
```

This keeps the product promise intact: semantic UI sound tokens, themeable tactile identity, zero audio files, and a tiny runtime surface.
