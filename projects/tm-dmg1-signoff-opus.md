---
title: Sign-off findings — t3code DMG-1 (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, dmg, dmg-1, sign-off, review, packaging, electron-builder, python-standalone, reach-back]
summary: Opus independent sign-off on DMG-1 (standalone .app launch + reach-back closure + linux-portable smoke). Verdict SIGN-OFF with 3 must-fixes. The reach-back inventory is INCOMPLETE (channel-specs.json + assets have a workspace fallback R1-R5 omits), and R1's console-script entrypoint is relocation-fragile (breaks when the .app is installed to /Applications). Decomposition is clean, no scope creep. First-hand on main @ 4c20d35.
status: active
source: opus (5:2.3), first-hand on main @ 4c20d35
confidence: high
created: 2026-07-08
---

# DMG-1 plan sign-off (opus) — SIGN-OFF with 3 must-fixes

Reviewed the standalone `registerAppLifecycle` topology + the R1/R2/R3 seam + the smoke + electron-builder
layout first-hand. The decomposition and seam design are right; two of my must-fixes are things the plan's
reach-back inventory / entrypoint choice missed, both of which would ship broken.

## Confirmed sound

- **No scope creep.** The store (DMG-2) and update feed (DMG-3) are correctly deferred; DMG-1 scopes the
  smoke to a PROVIDED store (CI postgres, as `product-plane` already does). The load-before-capture caveat is
  a store-internal concern respected by using the real store — not a DMG-1 issue.
- **R2/R3 seams are right.** Setting `GATEWAY_ENTRY` in `registerAppLifecycle` fires `resolveGatewayEntry`'s
  override branch BEFORE its `pnpm-workspace.yaml` walk (verified gatewayProcess.ts); `resolveBundledResources`
  via `process.resourcesPath` (electron-builder sets it per-platform) is the correct single locator. In the
  DMG topology Electron spawns the gateway (execPath node) and sets `GATEWAY_URL` on the Python backend, so
  the Python-side gateway supervisor (D1-b) is dormant — no double-supervise, and R5 is correctly dev-only.
- **Smoke faithfulness (with one caveat, M2).** The scrubbed-env temp-dir linux-portable launch genuinely
  proves the MECHANISM (bundled Python boots the backend, bundled gateway spawns a PTY, no packages/ reach)
  and catches PATH/cwd/workspace reaches. macOS .app/DMG/signing as a Stuart-local gate is proportionate (CI
  can't sign; darwin bills ~10x). The structural "no packages/ + never resolves pnpm-workspace.yaml" assertion
  is a good guard.
- **electron-builder over @electron/packager** is right; removing the unused catalog entry is safe (grep
  confirms no use).

## Must-fix

### M1 — reach-back inventory is incomplete: channel-specs.json + assets have a workspace fallback

`desktop/src/env.ts::resolveChannelSpecsPath` prefers a co-located `./channel-specs.json` (produced by the
build's `scripts/copy-channel-specs.mjs` → `dist/channel-specs.json`, verified present) but FALLS BACK to the
WORKSPACE path `SOURCE_CHANNEL_SPECS_PATH = ../../api/src/transport_matters/channel-specs.json`. This is a
workspace reach the R1-R5 table omits, and `resolveDesktopChannelSpec` is called on the DMG path
(`registerAppLifecycle`, main.ts:345). Same class: `main.ts:61 PREVIEW_AMBER_ICON = join(moduleDir,
"../assets/preview-amber.png")` needs `assets/` co-located. Both are closed ONLY IF electron-builder's `files`
includes `dist/channel-specs.json` + `assets/`; if configured narrowly (e.g. `dist/**/*.js`), the co-located
copy is dropped, the workspace fallback fires, and the app throws resolving its channel spec BEFORE the
backend spawns. Add R6 to the inventory: electron-builder `files` must carry the build's co-located
`dist/channel-specs.json` and `assets/`. (The scrubbed-env temp-dir smoke is the backstop — launched outside
the checkout, a missing co-located copy makes the workspace fallback fail and the smoke fail — but relying on
the smoke to catch an un-inventoried reach-back is worse than inventorying it.)

### M2 — R1's console-script entrypoint is relocation-fragile (ships broken when installed to /Applications)

The plan sets `DESKTOP_BACKEND_BIN = Contents/Resources/python/bin/transport-matters` (the pip console script)
and invokes it directly. pip console scripts carry an ABSOLUTE interpreter shebang
(`#!/<build-path>/python/bin/python3`) fixed at build/install time. A macOS `.app` is relocatable
(`/Applications`, `~/Applications`, a `/Volumes/…` DMG mount), so the build-time shebang path will not match
the install location → the console script cannot find its interpreter → the backend never boots. Invoke
interpreter-first instead: `DESKTOP_BACKEND_BIN = .../python/bin/python3` with the entrypoint as an arg
(`python -m transport_matters …` if the wheel ships a `__main__`, else `python <console-script-path>
_desktop-backend …` — passing the interpreter makes the shebang irrelevant and relocation-safe). Critically,
the **linux-portable CI smoke will NOT catch this** (it launches from its own build/temp dir where the shebang
is still valid); this is a darwin-relocation-specific bug, so the Stuart-local macOS gate MUST test a MOVED
`.app` (build → move to /Applications → launch), not the in-place build.

### M3 — R4 (cwd) is load-bearing for the acceptance, not "minor"

`registerAppLifecycle` sets `workspaceDir = process.cwd()`; a Finder launch has `cwd = /`. The canvas run then
spawns the agent with cwd `/` — the `RUN_STARTED → EXITED` acceptance the smoke asserts can fail or misbehave
(an agent in `/` with no project, permission surprises). The plan files R4 as "minor / cosmetic," but since
DMG-1's acceptance IS "runs a canvas run," a valid run cwd is required. Default `workspaceDir` to a sane
packaged location (home, or a chosen dir) when `app.isPackaged`, and have the smoke launch with `cwd = /` (or
a scrubbed temp) to prove the packaged default actually produces a runnable directory.

## Notes

- The `just` macOS recipe (M2) should build the `.app`, MOVE it (simulate install), then run the standalone
  smoke against the moved copy — that is the only place the shebang-relocation and the .app-vs-portable
  `resourcesPath` layout are proven.
- Bundle size (~150-250 MB Python + Electron + mitmproxy) is worth stating as a DMG target; darwin-first is
  correct (Windows parked per WHEEL.md).

Strong plan overall. M1 (inventory gap) and M2 (relocation shebang) are the two that would ship broken; M3
makes the acceptance actually runnable.
