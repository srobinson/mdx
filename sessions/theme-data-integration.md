---
title: Theme Data Integration
type: sessions
tags: [backend, frontend, theme-data, registry]
summary: Integrated the SPEC A theme registry into the main lab apply path, storage migration flow, and shared photo lookup factory.
status: active
source: backend-engineer
confidence: high
created: 2026-06-12
updated: 2026-06-12
---

## Summary

Implemented SPEC A slice 2 on branch `theme-data-integration`, PR #3. Initial integration commit was `b60823b`; fix round commit was `d509d74`. `src/main.ts` now creates a `ThemeRegistry` with the real ambient scene registry, a `photoCatalog` backed `ThemePhotoLookup`, and localStorage backed theme storage. Main applies validated `ThemeRegistrySnapshot.draftSettings` instead of mutating raw theme settings.

Key decisions:

1. The registry snapshot is the single source of truth for the panel and apply path.
2. Scene changes clear stale `sceneParams` before registry validation, preventing params from one scene from invalidating another scene.
3. Legacy `photoIndex` and `accentId` remain only in v0 migration and tests, not in live panel or apply code.
4. `applyThemeTokens` derives both CSS accent color and RGB channels from the serialized `ThemeAccent`, including OKLCH accents.
5. `createPhotoLookup(catalog)` in `src/theme/types.ts` is the shared factory for photo key lookup, default photo resolution, and v0 index to key migration lookup. It owns the preferred default key once through `THEME_DEFAULT_PHOTO_KEY`.

## API Contract

No HTTP API changed.

Theme panel contract now consumes registry state:

```typescript
interface ThemePanelContext {
  activeTab: PanelTab;
  setTab(tab: PanelTab): void;
  snapshot: ThemeRegistrySnapshot;
  accentCss(accent: ThemeSettings["accent"]): string;
  sim: LabSimSettings;
  scenes: readonly AmbientSceneDefinition[];
  sceneMetadata: readonly AmbientSceneMetadata[];
  photoCatalog: readonly PhotoEntry[];
  selectTheme(id: string): void;
  change(mutate: (settings: ThemeSettings) => void, rerender?: boolean): void;
  changeSim(mutate: (sim: LabSimSettings) => void): void;
}
```

Main apply flow contract:

1. Read `snapshot.draftSettings` from `ThemeRegistry`.
2. Validate with `validateThemeSettings` before applying.
3. Apply tokens through `applyThemeTokens(settings)`.
4. Resolve `settings.photoKey` through the shared `ThemePhotoLookup` from `createPhotoLookup(photoCatalog)`.
5. Apply params from `sceneRegistry.paramsFor(settings.sceneId)` using renderer neutral param ids.
6. Remount the panel only after the apply path succeeds.

Photo lookup contract:

```typescript
const photoLookup = createPhotoLookup(photoCatalog);
```

Consumers:

1. `src/main.ts` uses the shared lookup for apply and storage migration deps.
2. `src/theme/registry.ts` derives `DEFAULT_PHOTO_KEY` from the shared lookup.
3. `src/theme/theme-data.test.ts` and `src/theme/theme-main-integration.test.ts` consume the factory instead of duplicating lookup logic.

## Database Changes

No database changes.

Storage changes:

1. `createLocalThemeStorage` now detects non v1 legacy records.
2. Valid legacy v0 settings migrate through `migrateThemeSettingsV0`.
3. Migrated records are rewritten as v1 storage records under `little-background-lab.theme-studio.v1`.
4. Parse failures, invalid v1 records, and legacy migration failures still archive the raw record to the corrupt key prefix and return an empty v1 record.

## Security Considerations

1. Imported and stored themes remain strictly validated before use.
2. Legacy records validate after migration before save or apply.
3. Unknown scene ids, scene params, photo keys, accents, corners, borders, shadows, and out of range values are rejected through existing validation causes.
4. Main revalidates the registry draft immediately before applying UI state to avoid partial theme application.

## Performance Notes

1. Photo lookup is backed by a `Map` over the provided catalog, so key resolution is constant time.
2. Apply now iterates only params for the active scene rather than every scene metadata entry.
3. Files remain under the 700 line cap. `renderThemeTab` and `mountThemePanel` remain under 150 lines each.
4. No additional runtime dependencies were added.

## Verification

Commands run successfully after the initial integration and again after the fix round:

```bash
git diff --check
pnpm test
pnpm build
```

Latest results:

1. Vitest passed: 3 test files, 26 tests.
2. TypeScript and Vite production build passed.
3. Added a real integration test proving all five registered scenes can become validated drafts using the real scene registry and photo catalog.
4. Confirmed the default photo key string and lookup logic are no longer duplicated across main, registry, and tests.
5. Attempted Browser plugin verification during the initial integration, but the in app browser backend was unavailable with `Browser is not available: iab`.

## Open Items

1. Orchestrator owns the human road test for scene card selection and visual apply behavior.
2. SPEC B can later add save, rename, duplicate, delete, import, and export UI actions against the existing registry contract.
