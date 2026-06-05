---
title: NOW.md verification — frontend/UI (launcher) + session transcripts
type: research
tags: [transport-matters, now-md, launcher, www, transcripts, verification]
summary: Launcher build order is shipped on main (#144–#153); only workdir/sessions launcher scopes + backend recommended_model reader genuinely remain. Transcript browse/view shipped; denylist/search/import correctly pending; onboarding purely forward-looking.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-19
updated: 2026-06-19
---

# NOW.md verification — frontend/UI domain

Verified read-only against `main` @ `343a8cc` (clean). Domain: `www/` frontend (the launcher) + session transcript read surface. Verdicts: **TRUE-CURRENT** (accurate, still forward/WIP), **STALE-WRONG** (contradicts code), **DONE-AS-PENDING** (complete on main but doc frames it as open).

## Crux: the "#2 Desktop cleanup" launcher build order

NOW.md line 61 build order: `RouteSwitcher → Ark Menu pilot → Agents scope (⌘A + launcher) → root command-center shell → Canvas/Settings/Workdir/Sessions`. Owner suspects this is stale history. **Confirmed: the first four steps + Canvas + Settings are all shipped; only Workdir/Sessions launcher scopes remain as placeholders.**

| Claim | Verdict | Evidence |
|---|---|---|
| Build step 1: "RouteSwitcher" (pending) | DONE-AS-PENDING | `session-canvas/components/RouteSwitcher.tsx` exists and predates #144 (only `3 +-` lines touched in #144 `89e5869`); `routeLayout RouteLayout`, `components/RouteRail` also present. |
| Build step 2: "Ark `Menu` pilot" (pending) | DONE-AS-PENDING | Ark UI wired and in production use; landed as `Combobox`+`Portal`, **not `Menu`**: `CommandCenter.tsx` imports `Combobox`/`Portal` from `@ark-ui/react`, `useLauncherRows.ts` imports `createListCollection`. `@ark-ui/react@^5.37.2` in `www/package.json` (added in #144 `89e5869`). The "Menu" name is inaccurate; the Ark pilot itself is done. |
| Build step 3: "Agents scope (⌘A + launcher, load-bearing slice)" (pending) | DONE-AS-PENDING (frontend) | `commandModel buildAgentRows`/`agentSpawnRows` emit real spawn actions (`{kind:"spawn", harness, runtimeTemplate}`), native-first + specialists; recommendation-default via `recommendedSpawnHarness`/`recommendedSubtitle` reading `template.recommended_model.default.harness`/`by_vendor`/`vendor`; four states via `AgentsStatus`/`agentsStatusRows` (loading/error/empty/populated, native always available). Shipped #144 `89e5869`. Live data still depends on a backend reader (see below). |
| Build step 4: "root command-center shell" (pending) | DONE-AS-PENDING | `session-canvas/launcher/CommandCenter.tsx` + `useCommandCenter` + `useLauncherHotkeys` (⌘K toggles root) shipped #144 `89e5869`; domains-first root + footer/divider/scroll/a11y polish #145 `b9db8a8`; mounted via `session-canvas/components/CanvasSurface`. |
| Build step 5: "Canvas" scope (pending) | DONE-AS-PENDING | `commandModel buildCanvasRows` (reset-view, focus-picker, goto-lab). |
| Build step 5: "Settings" scope (pending) | DONE-AS-PENDING | `commandModel buildSettingsRows` (cycle-theme + canvas gesture modifier). |
| Build step 5: "Workdir" scope (pending) | TRUE-CURRENT | Genuinely deferred: `commandModel buildScopeRows` case `"workdir"` → `buildDeferredRows("Workdir")` = single disabled "Workdir lands next / internals to come" row. |
| Build step 5: "Sessions" scope (launcher) (pending) | TRUE-CURRENT | Genuinely deferred: `buildScopeRows` case `"sessions"` → `buildDeferredRows("Sessions")` disabled placeholder. (Note: distinct from the shipped transcript viewer in #3 below — the launcher *scope* is a stub; the canvas transcript reader is live.) |
| "Headless layer: Ark UI per component strategy" | TRUE-CURRENT | Ark UI is the headless layer in production (`Combobox` powers the launcher list). |
| Data dep: "`cli`→`harness` rename ✓ DONE" | TRUE-CURRENT | Frontend consumer confirms: `commandModel`/`types/runtimeTemplates.ts` speak `harness` (`recommended_model.default.harness`, `isCapturedRunHarness`, `templateSpawnHarness`). |
| Data dep: "read-side reader does not yet surface `recommended_model.default`/`by_vendor`" | TRUE-CURRENT (backend) | Out of frontend domain (`capabilities.py`), but frontend is already wired to consume it via `GET /v1/runtime-templates` (`api.ts`, `useRuntimeTemplates.ts`). The remaining work is purely backend reader + the uncommitted `capabilities.json` v2; the UI consumer is ready. |
| #2 header: "UI now the focus" (framed as upcoming) | DONE-AS-PENDING | The UI largely shipped across #144 `89e5869`, #145 `b9db8a8`, keybinding registry #146–#149 (`133ae06`/`fe13788`/`468a40a`/`e6951ff`), nav frame #152 `543b357`, interaction model #151 `e03eb23`, theme cycling #153 `d22d114`. The build order reads as not-started; it is ~90% shipped. |

## #3 Session transcripts (read surface)

| Claim | Verdict | Evidence |
|---|---|---|
| "browse + view ✓ shipped (#124/#125/#126), render turns as chat UI" | TRUE-CURRENT | Accurately written as shipped: `session-canvas/viewers/transcript-chat/TranscriptChatPane.tsx` + `TranscriptMessage.tsx`, registered in `viewers/registry` (id `transcript-chat`, prefix `transcript:`); browse via `session-canvas/hooks/useSessions`, `session-canvas/api/sessionClient`; `session-canvas/stream/mapIrToChat`. |
| "Complete visibility / full `nativePayload`, no subtype filtered" | TRUE-CURRENT | Reveal-all surface present in the transcript-chat viewer pipeline (`mapIrToChat`, `nativePayload`); matches #125/#126 cm "Transcript reveal-all". |
| "S2 — denylist (next): `transcript_denylist.json` UI presentation filter" | TRUE-CURRENT | Genuinely not built: zero `denylist`/`transcript_denylist` references anywhere in `www/`. Parking-lot-correct. |
| "search — pending" | TRUE-CURRENT | No transcript-search code in `www/`. |
| "import — pending" | TRUE-CURRENT | No transcript-import code in `www/`. |

## #1 User onboarding

| Claim | Verdict | Evidence |
|---|---|---|
| "First-run welcome flow in the desktop" (whole section forward-looking) | TRUE-CURRENT | Nothing built. The only "first-run" artifact is `session-canvas/launcher/FirstRunHint.tsx` — a decorative, aria-hidden ⌘K discoverability hint on the canvas (localStorage `tm.launcher.hintSeen`), unrelated to the onboarding welcome flow (CLI detection / first-frame baseline / guided ENV walk). No drift-baseline or guided-walk code exists. |

## Launcher: what's done vs what's left

The launcher described in NOW.md #2 is essentially shipped on `main`, contrary to the build order's framing. The zero-chrome ⌘K command center (#144), domains-first root with a11y polish (#145), keybinding registry/platform/gesture engine (#146–#149), and the action/nav-frame/interaction-model/theme refactors (#151–#153) are all merged. `RouteSwitcher`, the Ark UI pilot (as `Combobox`, not `Menu`), the root shell, and the Agents/Canvas/Settings scopes are live; the Agents scope is a real spawn launcher with recommendation-default logic, native-always-present, and the four loading/error/empty/populated states. **What genuinely remains:** (1) the **Workdir** and **Sessions** launcher scopes, which today are disabled `buildDeferredRows` placeholders ("…lands next"); and (2) the **backend** `capabilities.py` read-side reader that surfaces `recommended_model.default`/`by_vendor` (plus the uncommitted `capabilities.json` v2) — the frontend Agents recommendation-default already consumes this shape via `GET /v1/runtime-templates`, so the gap is data-plumbing, not UI. The build order should be rewritten as a short "remaining: Workdir/Sessions scope internals + recommended_model data dep" note rather than a five-step plan.
