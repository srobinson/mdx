---
title: Parallel dev/preview/stable install conventions for Electron + CLI-launched desktop apps
type: research
tags: [electron, release-channels, packaging, electron-updater, transport-matters, desktop]
summary: VS Code, Chrome, Discord and electron-builder all isolate coexisting channels via a distinct app identity that forks the data dir; promotion is a version-suffix ladder (alpha→beta→latest). Recommendation for a wheel-launched Electron app is a two-rung preview→stable ladder keyed on one channel variable.
status: active
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Parallel channel install conventions (Electron + CLI desktop apps)

## Executive Summary

Every desktop app that ships coexisting channels (VS Code, Chrome, Discord) isolates them the same way: a **distinct app identity per channel** (product name + app id), which forks the user-data directory and lets installs run side by side. The channel is shown to users primarily through **icon color** and the channel word in the title. Promotion is governed by **version pre-release suffixes** mapped to an `alpha → beta → latest` updater ladder (electron-builder/electron-updater). Slack is the counter-model: an in-app toggle, single install, no coexistence.

## Detailed Findings

### Naming tiers (two vocabularies)
- **Chromium ladder (genuine, 4 rungs):** Canary (daily, expected to break, permanently side-by-side) → Dev (1–2×/week) → Beta (~weekly) → Stable. Source: Chrome for Developers, Google support.
- **IDE/app vocabularies:** VS Code `Insiders` (daily, "beta channel" for new ideas) vs `Stable`. Discord `Canary` → `PTB` (Public Test Build, middle ground) → `Stable`. "Insiders" and "PTB" are brand-owned inventions; Canary/Beta/Stable are portable.
- **Updater implementation tiers:** electron-builder uses `alpha`, `beta`, `latest` (latest = stable, no suffix). These are load-bearing, not cosmetic.

### Isolation mechanism (the core finding)
- VS Code: product name "Code" vs "Code - Insiders" → distinct AppData (`%APPDATA%\Code` vs `…\Code - Insiders`), distinct extensions dir, separate Settings-Sync, separate CLI alias (`code` vs `code-insiders`).
- Chrome: channels "don't share installation locations or user profiles." Canary designed side-by-side.
- Discord: fully separate installs; separate update subdomains (discord.com / ptb.discord.com / canary.discord.com).
- electron-builder (Station pattern): a second config (`electron-builder-canary.yml`) sets a **different `appId` and `productName`** + separate update feed. "the name of the app and the appId are different, which guarantees that the two apps remain isolated when running."
- Electron mechanics: `app.getPath('userData')` = appData + app name, with `productName` preferred over `name`. Changing product name per channel auto-forks userData. **Caveat:** documented inconsistency — `appData` reads `name`, `logs` reads `productName` (electron issues #8073, #14470). Robust fix: set the userData path explicitly per channel.

### UI distinction
Icon color is the universal primary signal: VS Code Insiders green vs Stable blue; Discord Canary orange vs purple; Chrome Canary gold/dark. Plus the channel word in product name/title bar.

### Promotion tooling (electron-updater)
- Channel inferred from version pre-release suffix: `1.4.0`→latest, `1.4.0-beta.2`→beta, `1.4.0-alpha.1`→alpha.
- `generateUpdatesFilesForAllChannels: true` emits all channel metadata.
- Subscription ladder: alpha user gets alpha+beta+latest; beta gets beta+latest; latest gets only stable.
- `allowPrerelease` defaults true when the running version has a pre-release component.
- **Promotion = re-tag the same commit without the suffix.** That is the whole ladder. Source: electron.build release-using-channels, issue #4988.

### Counter-model: Slack
Beta is an in-app release-channel toggle (Preferences → Advanced), single app, no separate coexisting install. "Switch, don't fork." Wrong fit when two instances must run simultaneously.

## Transport Matters application

A Python-wheel-launched Electron app forks more state than a plain Electron app: CLI entry point, `~/.transport-matters/` root, Postgres `DATABASE_URL`, the `127.0.0.1:{port}/canvas` server, and Electron identity. Design rule: **one `channel` value fans out to every root**; isolate one variable, not five by hand.

Recommendation (single developer):
- Two rungs: `stable` ("driving") + `preview` (in-dev). "preview" over "insiders/canary" — plain English, not brand-owned, reads in a title bar. Keep `beta`/`alpha` only as the hidden updater channel.
- Channel selection via `--channel preview` / `TM_CHANNEL` env (lightest), or a `transport-matters-preview` wheel for a second pipx entry point.
- Fan-out: storage `~/.transport-matters/` (stable, back-compat) vs `~/.transport-matters-preview/`; Postgres DB-name suffix or per-channel `DATABASE_URL` (never shared — schema drift risk); dynamic port (already safe); Electron `appId` `…transport-matters` vs `…-preview`, distinct productName, explicit userData path, tinted icon + "— Preview" title badge.
- Promotion: develop on `preview` versioned `X.Y.Z-preview.N` (updater `beta`); promote by building the same commit without the suffix → `latest`; stable install auto-updates. Mirrors electron-updater beta→latest, zero bespoke tooling.

## Sources Consulted

**Docs/official**
- https://code.visualstudio.com/insiders/ · /blogs/2016/02/01/introducing_insiders_build · /docs/setup/portable · /brand
- https://developer.chrome.com/docs/web-platform/chrome-release-channels · https://support.google.com/chrome/a/answer/9300510 · https://chromium.googlesource.com/.../dev-channel/index.md
- https://support.discord.com/hc/en-us/articles/360035675191-Discord-Testing-Clients
- https://slack.com/help/articles/226192087-Join-Slack%E2%80%99s-desktop-app-beta-program
- https://www.electron.build/tutorials/release-using-channels.html · /configuration.html
- https://www.electronjs.org/docs/latest/api/app

**Community/issues/blogs**
- https://github.com/electron-userland/electron-builder/issues/4988 (allowPrerelease/channel clarification)
- https://medium.com/getstation/canary-releases-for-electron-applications-acf3ebecade7 (Station two-config pattern)
- https://github.com/electron/electron/issues/8073 · /issues/14470 (userData path derivation quirks)
- https://www.minitool.com/news/discord-canary-ptb-stable.html

## Source Quality Assessment

High confidence. Official docs corroborate the isolation-by-identity pattern across four independent vendors; electron-builder docs + issue #4988 confirm the suffix→channel ladder. The one soft spot is the exact Electron userData derivation (vendor-version dependent), which is why the recommendation says set the path explicitly rather than rely on derivation.

## Open Questions
- Squirrel.Windows/Mac specifics beyond what electron-updater abstracts (not separately verified; electron-updater wraps it).
- Whether Transport Matters wants a third "nightly" rung later — deferred; two rungs fit one developer.
- Postgres isolation choice (separate DB vs schema vs full `DATABASE_URL`) depends on the existing connection-management code.

## Actionable Takeaways
1. Introduce a single `channel` concept (`stable`|`preview`) threaded from the CLI through every state root.
2. Use version pre-release suffix `-preview.N` → updater `beta`; promote by dropping the suffix.
3. Visually badge: tinted icon + "— Preview" title. Follow the green/orange precedent.
4. Set the Electron userData path explicitly; do not rely on productName derivation.
5. Never share the Postgres DB between channels.
