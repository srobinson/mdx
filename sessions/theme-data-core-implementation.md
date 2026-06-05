---
title: Theme data core implementation
type: sessions
tags: [backend, theme, registry, validation, storage]
summary: Implemented SPEC A theme data core with versioned types, validation, migration, storage, registry orchestration, and tests.
status: active
source: backend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

Implemented SPEC A Slice 1 on branch `theme-data-core` in commit `1a03e94`.

Key decisions:

- Added `src/theme/types.ts` as the public schema contract for `ThemeDefinition`, `ThemeSettings`, registry entries, import results, lookup interfaces, limits, and accent helpers.
- Added strict validation in `src/theme/validate.ts` with exact per-cause error strings from the spec.
- Added `src/theme/migrate.ts` for v0 settings migration from `photoIndex` and `accentId` into `photoKey` and `accent`.
- Added `src/theme/storage.ts` for localStorage persistence, v1 record loading, stored theme validation, and corrupt record archival.
- Added `src/theme/registry.ts` for curated themes, draft state, save, rename, duplicate, delete, export, import, collision suffixing, and curated immutability.
- Added `src/theme/import-export.ts` for JSON parse and serialization helpers.
- Refactored shared token constants out of `src/theme/theme.ts` into `src/theme/types.ts` while preserving existing imports for the current UI slice.
- Added Vitest and unit coverage in `src/theme/theme-data.test.ts`.

PR creation remains blocked because the checkout has no git remote configured. `git push -u origin theme-data-core` fails because `origin` does not exist, and `gh pr create` reports `no git remotes found`.

## API Contract

Public theme JSON is `ThemeDefinition`:

```ts
interface ThemeDefinition {
  schema: 1;
  id: string;
  name: string;
  author?: string;
  source: "curated" | "user" | "community";
  settings: ThemeSettings;
}

interface ThemeSettings {
  sceneId: string;
  sceneParams: Record<string, number>;
  photoKey: string;
  accent: { id: AccentId } | { oklch: { l: number; c: number; h: number } };
  cornerId: CornerId;
  veil: number;
  borderId: BorderId;
  glass: boolean;
  glassAmount: number;
  shadowId: ShadowId;
}

type ImportResult =
  | { ok: true; theme: ThemeDefinition }
  | { ok: false; error: { cause: ImportErrorCause; message: string } };
```

Registry API:

```ts
interface ThemeRegistry {
  snapshot(): ThemeRegistrySnapshot;
  selectTheme(id: ThemeId): ThemeRegistrySnapshot;
  updateDraft(mutator: (settings: ThemeSettings) => void): ThemeRegistrySnapshot;
  saveDraft(name?: string): ThemeRegistrySnapshot;
  renameTheme(id: ThemeId, name: string): ThemeRegistrySnapshot;
  duplicateTheme(id: ThemeId): ThemeRegistrySnapshot;
  deleteTheme(id: ThemeId): ThemeRegistrySnapshot;
  exportTheme(id: ThemeId): string;
  importTheme(json: string): ImportResult;
}
```

## Database Changes

No database changes.

Persistent client storage uses localStorage key `little-background-lab.theme-studio.v1` with this record shape:

```ts
interface ThemeStorageRecordV1 {
  schema: 1;
  activeThemeId: string | null;
  themes: ThemeDefinition[];
}
```

Corrupt records are archived under `little-background-lab.theme-studio.corrupt.<timestamp>` before the primary key is removed.

## Security Considerations

- Theme import parses untrusted JSON and validates every field before registry state changes.
- Public theme JSON stores data only: scene id, renderer-neutral scene params, stable photo key, accent data, and material settings.
- Unknown scenes, scene params, photos, accents, corners, borders, shadows, unsupported schemas, malformed OKLCH values, and range violations are rejected with exact machine-readable causes.
- Curated themes cannot be renamed, deleted, or overwritten by import collisions.
- Import rejection and storage save failure leave active theme state unchanged.

## Performance Notes

- Registry snapshots clone public data to avoid accidental mutation by callers.
- Validation is deterministic and single pass over `sceneParams`.
- Storage loading validates each persisted theme once and recovers corrupt records by clearing the primary key.
- All new files remain under the 700 line limit. Registry orchestration is split into small methods instead of one large function.

## Open Items

- PR could not be opened until a git remote is configured for this checkout.
- SPEC B still needs to consume `ThemeRegistrySnapshot` and stop using `THEME_PRESETS` directly.
- SPEC C still needs to provide the canonical scene registry implementation that backs the `AmbientSceneRegistry` interface used by this slice.
- `src/main.ts` was intentionally unchanged per slice instructions.

## Verification

- `pnpm test`: 11 tests passed.
- `pnpm build`: TypeScript and Vite production build passed.
- `git diff --check`: passed.
