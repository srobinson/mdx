---
title: Sign-off findings — t3code P1 Slice D1-a (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-d1-a, sign-off, review, packaging, wheel, node-pty, esbuild]
summary: Opus independent sign-off on D1-a (build @tm/gateway distributable + embed in the wheel). Verdict GO-WITH-FIXES. The node-pty prebuild-loader assumption is VERIFIED against the installed source. 3 must-fix — sharpest is that esbuild must BUNDLE node-pty's JS (not --external:node-pty) or the prebuilds-beside-main.js layout breaks. First-hand on main @ 81cca42.
status: active
source: opus (5:2.3), first-hand on main @ 81cca42
confidence: high
created: 2026-07-08
---

# D1-a plan sign-off (opus) — GO-WITH-FIXES

Verified the load-bearing assumption (node-pty prebuild loader) against the actual installed source
and the www/canvas embed precedent. Strong, well-researched plan; the risks are concentrated in the
esbuild strategy and the exec-bit round-trip. 3 must-fix.

## Confirmed sound (independently verified on main @ 81cca42)

- **node-pty loader resolution is exactly as claimed.** `node-pty@1.2.0-beta.14/lib/utils.js::loadNativeModule`
  does a DYNAMIC `require("${r}/${d}/pty.node")` over `dirs=['build/Release','build/Debug',
  'prebuilds/${platform}-${arch}']` × `relative=['..','.']` — `..` (unbundled) then `.` (bundled, comment
  says so). spawn-helper: `unixTerminal.js` → `path.resolve(__dirname, native.dir + '/spawn-helper')`. So with
  the bundle's `__dirname`, the `.` branch finds `./prebuilds/${plat}-${arch}/pty.node` + spawn-helper beside
  main.js. Verified layout: `prebuilds/{darwin-arm64,darwin-x64,linux-arm64,linux-x64,win32-*}` present;
  `darwin-arm64/spawn-helper` is `-rwxr-xr-x` (0755), `pty.node` present. N-API (no Electron rebuild) correct.
- **Embed precedent is a clean mirror.** `api/pyproject.toml` `[tool.hatch.build.targets.wheel] artifacts` globs
  `src/transport_matters/{www,canvas}/**`; `api/justfile::build` runs `uv build` then echoes wheel-listing
  presence; root `justfile::build` (91-95) runs inspector/canvas builds before `cd api && just build`. Adding a
  `gateway/**` glob + `pnpm --filter @tm/gateway build` step is a faithful extension.
- **D1-a is genuinely behavior-free.** `main.py::mount_frontend_bundles` mounts only canvas/www `if dir.exists()`;
  there is NO `gateway/` reference anywhere in the running app. Nothing imports or mounts the bundle in D1-a — so
  "degrade if gateway/ absent" is a D1-b concern (when the launcher reads it), not D1-a's; absence is a non-event now.
- **pnpm-deploy fallback is correctly named** (§9) as the escape hatch if esbuild fights the dep graph.

## Must-fix

### M1 — esbuild must BUNDLE node-pty's JS, NOT `--external:node-pty` (the load-bearing correctness)

The `.` (bundled) resolution branch resolves `require("./prebuilds/...")` relative to the CALLER's `__dirname`.
That becomes the bundle dir (→ prebuilds/ beside main.js) ONLY if node-pty's JS is INLINED into main.js. If the
build marks `--external:node-pty`, node-pty's JS stays in node_modules and its `__dirname` is
`node_modules/node-pty/lib` → prebuilds would have to live there, NOT beside main.js → the shipped layout
breaks with "Failed to load native module: pty.node". Correct config: bundle node-pty's JS, and external ONLY
`*.node` (the dynamic `require(dir + "/pty.node")` is a computed string esbuild cannot bundle anyway, so it
stays a runtime require regardless — `--external:*.node` is belt-and-suspenders). Confirm esbuild's CJS output
leaves `__dirname` as the output-file dir (default for `--platform=node --format=cjs`), and prove it with the
acceptance spawn.

### M2 — the wheel-check must HARD-ASSERT spawn-helper's exec bit, not echo presence

spawn-helper is 0755 in the package (verified); macOS node-pty spawn fails EACCES without it. The www/canvas
wheel-check is a SOFT presence echo (`grep index.html`) because SPA bundles carry no exec-bit invariant — the
gateway does. Two round-trips must preserve the bit: (1) the copy node_modules→`gateway/prebuilds/` (use a
mode-preserving copy, e.g. `cp -R`/`-p`, not a tool that defaults 0644), (2) the wheel zip (hatchling stamps the
on-disk mode, so the copy must not drop it first). The D1-a gate must unzip the built wheel and FAIL (not warn)
if `prebuilds/{darwin,linux}-*/spawn-helper` lacks mode & 0o111. A presence-echo alone ships a silent EACCES.

### M3 — add the gateway build to BOTH root justfile `build` AND `install-local`, before `cd api && just build`

Root `build` (91-95) and `install-local` (109+) both order the frontend builds before `cd api && just build`.
The gateway esbuild step (→ `gateway/{main.js,prebuilds/**}`) must be added to BOTH before uv build — missing
`install-local` (the path Stuart actually runs to install the tool) ships a wheel with a stale/absent gateway/
even though the acceptance passed via `build`.

## Notes (should-address; not blocking)

- **Name the specific esbuild externals to try first** before the pnpm-deploy fallback: pg lazily
  `require('pg-native')` / `require('pg-cloudflare')` (absent in pure-JS use) — likely needs
  `--external:pg-native --external:pg-cloudflare` or esbuild errors resolving them; pino/thread-stream worker
  transports (fastify's default logger) reference `__dirname`-relative worker files that break bundled — confirm
  the gateway sets `logger:false`/console (the plan claims transports unused) or external pino.
- **Acceptance should run the bundle from the INSTALLED-WHEEL location**, not only the source tree, so the
  exec-bit + prebuild round-trip is proven by a real node-pty spawn (source-tree run proves the bundle; installed
  run proves the PACKAGED layout). The plan runs the source-tree main.js + a separate stat — an installed-wheel
  spawn covers both at once.
- **Reinforce the build-time assert** (plan §9): node-pty is a beta pin (1.2.0-beta.14) and the prebuild layout
  is the whole strategy — assert `prebuilds/${platform}-${arch}` exists in the installed package BEFORE the copy,
  so a beta bump that moves the layout fails the build instead of shipping a prebuild-less wheel.

Scope discipline clean: D1-node/D1-win decisions are correctly deferred (D1-a is decision-free), POSIX-only glob
now (win32 defer per D1-win), one universal py3-none-any wheel. The node-pty research is accurate and I verified
it end-to-end; M1 is the easy-to-get-wrong knob.
