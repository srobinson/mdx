---
title: Parallel dev/preview/stable installs — channel conventions for Transport Matters
type: research
tags: [transport-matters, electron, release-channels, packaging, electron-updater]
summary: How VS Code, Chrome, Discord, Slack and electron-builder ship coexisting channels; recommends a two-rung preview→stable ladder keyed on one channel value that fans out to every state root.
status: active
confidence: high
created: 2026-06-20
updated: 2026-06-20
---

# Coexisting channels: what the wild has converged on

External-research voice. Web-sourced; URLs at bottom.

## (a) The real naming tiers and what each actually means

Two distinct vocabularies exist. Treat them separately.

**Browser/Chromium ladder (4 rungs):** `Canary → Dev → Beta → Stable`. Canary = daily, minimal testing, *expected* to break, ships as a permanently-separate side-by-side app. Dev = 1–2×/week. Beta = ~weekly, what's next with low risk. Stable = everyone. These four words are genuine conventions.

**App-store/IDE ladder:** Microsoft uses `Insiders` (daily, "beta channel" for new ideas) vs `Stable`. Discord uses `Canary` (most unstable, frequent) → `PTB` ("Public Test Build", the middle ground) → `Stable`. "Insiders" and "PTB" are brand-specific inventions; "Canary/Beta/Stable" are portable.

**Updater ladder (electron-builder):** the *implementation* tiers are `alpha → beta → latest`. "latest" is the magic word for stable (no suffix). These are real and load-bearing, not cosmetic.

Invented/vanity words to avoid as primary tier names: `Insiders`, `PTB` (brand-owned). Safe, self-explaining words: `stable`, `preview`, `beta`, `dev`, `nightly`, `canary`.

## (b) How each isolates identity + user data so installs coexist

The universal mechanism is **a distinct app identity per channel**, which in turn forks the data directory:

- **VS Code:** different *product name* ("Code" vs "Code - Insiders") → different AppData folders (`%APPDATA%\Code` vs `…\Code - Insiders`), different extensions dir (`.vscode` vs `.vscode-insiders`), separate Settings-Sync service, separate CLI alias (`code` vs `code-insiders`).
- **Chrome:** channels "don't share installation locations or user profiles." Canary keeps its own install root + own profile by design.
- **Discord:** fully separate installs; separate update subdomains (`discord.com`, `ptb.discord.com`, `canary.discord.com`).
- **electron-builder (Station pattern):** a second config file (`electron-builder-canary.yml`) sets a **different `appId` and `productName`**, plus a separate update feed/repo. "the name of the app and the appId are different, which guarantees that the two apps remain isolated when running."

The Electron mechanics worth knowing: `app.getPath('userData')` = appData + app name, and Electron prefers `productName` over `name`. So changing `productName`/`name` per channel auto-forks userData. Caveat: there's a documented inconsistency (`appData` reads `name`, `logs` reads `productName`), so the robust move is to **set the userData path explicitly** rather than trust derivation.

**Counter-example (Slack):** *no* separate install — beta is an in-app release-channel toggle (Preferences → Advanced). One app, no coexistence. This is the "switch, don't fork" model; wrong for Stuart, who wants two running side by side.

## (c) How the channel is shown in the UI

Consistent across all: **icon color** is the primary signal. VS Code Insiders = green (vs blue). Discord Canary = orange (vs purple). Chrome Canary = gold/dark. Plus the channel word in the product name/title bar ("Code - Insiders"). Cheap, unmistakable, no menu-diving.

## (d) Install + promotion tooling

electron-updater is the convergence point. Channel is inferred from the **version's pre-release suffix**: `1.4.0` → `latest`, `1.4.0-beta.2` → `beta`, `1.4.0-alpha.1` → `alpha`. Set `generateUpdatesFilesForAllChannels: true` to emit all metadata. Subscription is a downhill ladder: an alpha user receives alpha+beta+latest; beta receives beta+latest; latest receives only stable. `allowPrerelease` defaults true when the running version has a pre-release component. **Promotion = re-tag the same commit without the suffix.** That is the entire ladder.

## Recommendation for Transport Matters

A Python-wheel-launched Electron app has *more* state to fork than a plain Electron app: CLI entry point, `~/.transport-matters/` root, Postgres DB (`DATABASE_URL`), the `127.0.0.1:{port}/canvas` server, **and** Electron identity. The single design rule: **one `channel` value fans out to every root.** Don't isolate five things by hand; isolate one variable.

**Two rungs, not four.** One developer doesn't sustain Canary/Dev/Beta/Stable. Use **`stable` (the "driving" install) and `preview` (in-development)**. "preview" beats "insiders"/"canary": plain English, not brand-owned, reads correctly in a title bar. Keep `beta`/`alpha` only as the *updater channel implementation* under the hood.

**Channel selection:** a `--channel preview` flag / `TM_CHANNEL` env on the CLI (simplest for one dev), or a separately-named wheel (`transport-matters-preview`) if you want two `pipx` entry points. The flag approach is lighter and avoids double-publishing to PyPI.

**Fan-out from `channel`:**
- Storage: `stable` keeps `~/.transport-matters/` (back-compat); `preview` → `~/.transport-matters-preview/` (or `…/channels/preview/`).
- Postgres: suffix the DB name (`transport_matters` vs `transport_matters_preview`) or honor a per-channel `DATABASE_URL`. Never share — schema drift in preview must not corrupt the driving DB.
- Port: already dynamic `{port}`; just ensure the two instances pick independently (they will).
- Electron: `appId` `com.littleorgans.transport-matters` vs `…-preview`; distinct `productName`; **explicit** userData path under the channel root; distinct accent/icon color.
- Badge: title "Transport Matters — Preview" + colored dot/accent and a tinted dock icon (follow VS Code-green / Discord-orange precedent).

**Promotion ladder:** develop on `preview`, versioned `X.Y.Z-preview.N` → publishes to the updater `beta` channel; the preview install auto-updates itself. To promote, build the *same commit* with the suffix dropped → publishes to `latest`; the stable "driving" install picks it up. Exactly electron-updater's beta→latest, two rungs, zero bespoke tooling.

## Sources
- VS Code Insiders: https://code.visualstudio.com/insiders/ · https://code.visualstudio.com/blogs/2016/02/01/introducing_insiders_build · https://code.visualstudio.com/docs/setup/portable · https://code.visualstudio.com/brand
- Chrome channels: https://developer.chrome.com/docs/web-platform/chrome-release-channels · https://support.google.com/chrome/a/answer/9300510 · https://chromium.googlesource.com/playground/chromium-org-site/+/master/getting-involved/dev-channel/index.md
- Discord builds: https://support.discord.com/hc/en-us/articles/360035675191-Discord-Testing-Clients · https://www.minitool.com/news/discord-canary-ptb-stable.html
- Slack (in-app channel, no coexistence): https://slack.com/help/articles/226192087-Join-Slack%E2%80%99s-desktop-app-beta-program
- electron-builder/updater channels: https://www.electron.build/tutorials/release-using-channels.html · https://www.electron.build/configuration.html · https://github.com/electron-userland/electron-builder/issues/4988 · https://medium.com/getstation/canary-releases-for-electron-applications-acf3ebecade7
- Electron userData derivation: https://www.electronjs.org/docs/latest/api/app · https://github.com/electron/electron/issues/8073 · https://github.com/electron/electron/issues/14470
