# cubicell-polarity-review

Seat: blast-radius / behaviour preservation. Target: `a7083972` on `refactor/polarity-record`, parent `6ee7d665`.

Source of truth: `git show a7083972:<path>` only. Read-only.

## Verdict

`review: clean` — pure refactor; hex tables identical across all roles and both rails; resolve path still O(1) property access at runtime; exhaustiveness is structural `satisfies Record`.

## 1. Identical resolution (walked)

Reconstructed BEFORE (positional `createPolarityConfig` + shared part maps + separate accent arg) and AFTER (per-polarity `ScenePartColors` tables + named config object). Same token constants (unchanged in this commit).

| Family | Polarity | theme | black | white | accent | background | contrast |
|--------|----------|-------|-------|-------|--------|------------|----------|
| artifact | black | `#ffffff` | `#050505` | `#ffffff` | `#c0fac0` | `#050505` | `#ffffff` |
| artifact | white | `#050505` | `#050505` | `#ffffff` | `#1c0c43` | `#ffffff` | `#050505` |
| workbench | black | `#d8d8d8` | `#262626` | `#d8d8d8` | `#c0fac0` | `#464646` | `#d8d8d8` |
| workbench | white | `#262626` | `#262626` | `#d8d8d8` | `#1c0c43` | `#464646` | `#262626` |

**0 diffs** across 24 cells (4 roles × 2 polarities × 2 families + background/contrast).

Workbench still inherits accent from the matching artifact rail via spread, then overrides only `black`/`white` into workbench greys — same net map as the old shared `workbenchPartColors` + polarity accent arg.

Grooming unchanged: workbench only, same `edgeLightnessDelta` / `faceLightnessDeltaById`.

`resolveCubePartColor` body unchanged: `theme` → `contrast`; else `partColors[color]`.

## 2. What zero test diffs prove

**Pins hard (would fail on rail swap or wrong hex):**

- `tests/editorAdapters.test.ts`
  - Full deep-equal of `scenePolarities.black` / `.white` including `partColors.accent` = `accent` vs `accentOnLight`.
  - `resolveCubePartColor("accent", …)` on artifact **and** workbench, both polarities.
  - Workbench theme/white/black remap to workbench greys (black polarity).
  - Artifact pure black/white samples.
- `tests/colorSpace.test.ts` — black↔white OKLab midpoint channels (numeric), shift direction by workbench theme contrast.
- `tests/instances.test.ts` — workbench edge shift vs artifact byte-identical theme; face value ramp on workbench only.

**Touches polarity but would not catch a silent rail swap alone:**

- Mesh/capacity/handoff tests that only pass `workbenchScenePolarities.black` as a fixture (any non-empty colour works).
- Morph/`partColors` tween map tests (token identity, not hex).

**Zero suite diffs** = behaviour-preserving relative to those pins. They **do** catch the failure mode this seat cares about (dark/light accent transposition), because editorAdapters asserts both rails by token. They do **not** deep-equal the full workbench polarity objects (only selected resolves), but accent + black/white workbench samples are covered.

A rail transposition that only flipped artifact background while leaving partColors would still fail the deep-equal on `scenePolarities.*`.

## 3. Runtime cost

Module graph for colour resolution:

```
themeTokens (const hexes)
  → scenePolarity tables (module init)
    → scenePolarities / workbenchScenePolarities (module init via createPolarityConfig)
      → resolveCubePartColor(color, polarity)  // per call: branch + property read
        → colorSpace.resolvePartColor / resolveLerpedPartColor  // per instance write
          → instancedPartMeshCore.writeColor
```

**Init only (new cost):**

- Two `satisfies Record<…>` table objects × two polarities.
- Workbench tables: object spread from artifact rail + two overrides (once each at load).
- `createPolarityConfig`: spreads config + grooming into a new config object once per polarity family entry (4 total) — same class of work as before (previously also built a new object and `{ ...partColors, accent }`).

**Not per-frame:**

- `resolveCubePartColor` still does no allocation, no spread, no table rebuild.
- No change to instance write path.

The ~34 B gzip bumps on editor-studio / shared-renderer / combined-delivery match nested static objects in the bundle, not a hot-path structure.

Note: after the refactor, `partColors` on a polarity config is a **reference** to the module table entry (spread of config copies the reference). Before, each config got a fresh `{ ...partColors, accent }` object. Observable only if something mutates `partColors` at runtime (nothing in-repo does). Hex reads identical.

## 4. Exhaustiveness is genuine

```ts
export type ScenePartColors = Record<Exclude<CubePartColor, "theme">, string>;

const artifactPartColorsByPolarity = { … } satisfies Record<ScenePolarity, ScenePartColors>;
const workbenchPartColorsByPolarity = { … } satisfies Record<ScenePolarity, ScenePolarityConfig["partColors"] extends infer _ ? ScenePartColors : never>;
// actual: satisfies Record<ScenePolarity, ScenePartColors>
```

- `ScenePartColors` is a **closed** `Record` over every non-`theme` `CubePartColor` member (currently `black` | `white` | `accent`). Omitting `accent` on either rail is a compile error under `satisfies`.
- Outer exports are `Record<ScenePolarity, ScenePolarityConfig>`, so a missing polarity key also fails.
- Not an index signature (`Record<string, string>`), not `Partial`, not optional fields.
- A future editor could still **lie** with `as ScenePartColors` or `as any` on a hand-built object; the structural force is on the checked table literals, which is the intended enforcement site. Probe confirmation (omit rail → typecheck fail) matches this.

## Files in commit

- `src/theme/scenePolarity.ts` — structure only (above).
- `budgets/initial-delivery.json` — budget ceilings adjusted for measured gzip deltas (editor/shared +~34 B; some capability budgets down).
