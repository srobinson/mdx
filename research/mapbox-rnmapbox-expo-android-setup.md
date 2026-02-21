---
title: Mapbox (@rnmapbox/maps) Setup for React Native Expo Android
type: research
tags: [mapbox, rnmapbox, expo, android, react-native, yarn-workspaces, EAS]
summary: Complete setup requirements for @rnmapbox/maps in an Expo RN 0.76 Android project with Yarn 4 workspaces — tokens, gradle, permissions, and monorepo gotchas.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

The correct library for Mapbox in Expo React Native is `@rnmapbox/maps` (not `expo-mapbox-gl`, which is unmaintained). As of late 2024/early 2025, Mapbox lifted the authentication requirement from their Maven repository, so a secret download token is no longer required for Android gradle builds — only a public access token is needed at runtime. The library cannot run in Expo Go and requires a custom dev client or local prebuild.

---

## 1. Tokens

### Public Token (required)
- Starts with `pk.ey...`
- Used at runtime: `Mapbox.setAccessToken('pk.ey...')` in your app code
- Safe to commit to source (treat with reasonable care, but not a secret)
- Source: your Mapbox account → Tokens → Default Public Token

### Secret / Download Token (was required, now optional)
- Starts with `sk.ey...`, requires the `DOWNLOADS:READ` scope
- **Mapbox lifted the Maven auth requirement** — the download token is no longer needed for the gradle Maven repo as of current SDK v11
- If you are running SDK v10 (older rnmapbox/maps versions), you may still encounter gradle config that expects it
- The rnmapbox config plugin exposes `RNMapboxMapsDownloadToken` in `app.json`, but this is now optional for Android
- **Known security issue**: Placing `RNMapboxMapsDownloadToken` in `app.json` causes `expo prebuild` to write it into `build.gradle` and `Podfile` — files that are typically committed. This can expose the token publicly. Prefer environment variables or `~/.gradle/gradle.properties` instead.

---

## 2. Configuring for Local Dev and EAS Builds

### app.json plugin config

```json
{
  "expo": {
    "plugins": [
      [
        "@rnmapbox/maps",
        {
          "RNMapboxMapsImpl": "mapbox",
          "RNMapboxMapsVersion": "11.x.x"
        }
      ]
    ]
  }
}
```

Omit `RNMapboxMapsDownloadToken` if Maven auth is no longer required (current state). If you must supply it, use an environment variable reference or store it in `~/.gradle/gradle.properties` as `MAPBOX_DOWNLOADS_TOKEN=sk.ey...`.

### Local dev builds

- Run `expo prebuild --clean` after any plugin config change
- Cannot use Expo Go — requires a custom dev client: `eas build --profile development` or `npx expo run:android`
- Public token can be stored in `.env` and injected via `expo-constants` or `process.env`

### EAS builds

- Store the public token as an EAS secret (`eas secret:create`) if you do not want it in source
- If Maven auth is still needed for your SDK version, add `MAPBOX_DOWNLOADS_TOKEN` as an EAS secret and reference it in `eas.json` under `env`
- The gradle config in `android/build.gradle` (added by prebuild) will read `MAPBOX_DOWNLOADS_TOKEN` from the environment

---

## 3. Android-Specific Config

### Gradle (android/build.gradle)

The rnmapbox config plugin handles this automatically during `expo prebuild`. The Maven repo is added under `allprojects.repositories`:

```groovy
maven {
    url 'https://api.mapbox.com/downloads/v2/releases/maven'
    // credentials block only needed if still using older SDK requiring auth
}
```

For SDK v11 (current), no credentials block is needed.

If doing it manually (managed workflow without prebuild), add to `settings.gradle` under `dependencyResolutionManagement.repositories` — this is where Android Gradle Plugin 7+ expects it.

### AndroidManifest.xml permissions

Location permissions are **optional** — only needed if you render the user's location on the map:

```xml
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />
<!-- Only if precise location is needed: -->
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
```

`ACCESS_FINE_LOCATION` requires `ACCESS_COARSE_LOCATION` to also be present. The rnmapbox config plugin does **not** automatically add these — add them manually to `AndroidManifest.xml` or via an Expo config plugin.

You still need to call `PermissionsAndroid.request()` at runtime before rendering `UserLocation`.

### Mapbox version

Default is SDK v11 for current rnmapbox/maps. Specify explicitly in `app.json` via `RNMapboxMapsVersion` to pin a version and avoid surprise upgrades.

---

## 4. Library Choice: @rnmapbox/maps vs expo-mapbox-gl

| Library | Status | Notes |
|---|---|---|
| `@rnmapbox/maps` | Active, maintained | The correct choice. Expo config plugin included. |
| `expo-mapbox-gl` | Unmaintained / abandoned | Do not use for new projects |
| `@react-native-mapbox-gl/maps` | Deprecated predecessor | Was renamed to `@rnmapbox/maps` |

Install: `expo install @rnmapbox/maps`

---

## 5. Yarn 4 Workspaces / Monorepo Gotchas

### PnP is incompatible — use node-modules linker

Yarn 4 defaults to Plug'n'Play (PnP). Metro does **not** support PnP. You must configure the monorepo to use the `node-modules` linker for the React Native workspace (or globally via `.yarnrc.yml`):

```yaml
nodeLinker: node-modules
```

Without this, Metro cannot resolve native modules and the build will fail.

### Metro auto-config (Expo SDK 52+)

Since SDK 52, `expo/metro-config` auto-detects monorepos. Remove these manual overrides from `metro.config.js` if migrating from older SDK:
- `watchFolders`
- `resolver.nodeModulesPath`
- `resolver.extraNodeModules`
- `resolver.disableHierarchicalLookup`

Run `npx expo start --clear` after removal.

### Isolated dependencies (SDK 53-54)

With SDK 53, disable isolated dependencies or you will hit native build errors and dependency conflicts. This affects Yarn 4 since it supports isolated installs. Add to your workspace root `.yarnrc.yml` or expo config as needed.

### Duplicate React Native versions

Monorepos must have exactly one copy of React Native and React. If both are hoisted, `yarn why react-native` to confirm. Duplicates cause runtime crashes with native modules like rnmapbox.

### Gradle path resolution

React Native uses hardcoded paths that break under monorepo hoisting. The prebuild-generated `android/app/build.gradle` should use Node-based resolution rather than relative paths:

```groovy
apply from: new File(["node", "--print",
  "require.resolve('react-native/package.json')"].execute(null, rootDir).text.trim(),
  "../react.gradle")
```

If your prebuild does not generate this pattern, you may need a custom `android/app/build.gradle` patch.

### rnmapbox has no specific monorepo documentation

The library's install docs contain no monorepo-specific guidance. All monorepo handling falls to Expo's standard monorepo config. The main risk is the PnP incompatibility and native module duplication.

---

## Sources

- [Install | @rnmapbox/maps](https://rnmapbox.github.io/docs/install)
- [GitHub: rnmapbox/maps](https://github.com/rnmapbox/maps)
- [plugin/install.md — rnmapbox/maps](https://github.com/rnmapbox/maps/blob/HEAD/plugin/install.md)
- [RNMapboxMapsDownloadToken token exposure issue #3605](https://github.com/rnmapbox/maps/issues/3605)
- [Get Started with the Maps SDK for Android | Mapbox Docs](https://docs.mapbox.com/android/maps/guides/install/)
- [Work with monorepos — Expo Documentation](https://docs.expo.dev/guides/monorepos/)
- [Yarn PnP incompatibility with Metro — Lightrun/Metro issue](https://lightrun.com/answers/facebook-metro-support-for-resolving-yarn-plug-n-play-modules)
- [Setting up React Native Monorepo With Yarn Workspaces — Callstack](https://www.callstack.com/blog/setting-up-react-native-monorepo-with-yarn-workspaces)

---

## Open Questions

- Whether `RNMapboxMapsDownloadToken` is fully dead for SDK v11 Android, or only dead for Maven downloads (the secret token may still be used for analytics/telemetry in some SDK builds — unconfirmed).
- Exact Expo SDK version in the target project — SDK 52 vs 53 changes Metro auto-config behavior.
- Whether the project's `android/` directory is committed (bare workflow) or generated (managed workflow with prebuild) — affects how gradle config is managed.
