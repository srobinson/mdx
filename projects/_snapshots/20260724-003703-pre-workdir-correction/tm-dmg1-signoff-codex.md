# DMG-1 Plan Signoff - Codex

Verdict: SIGN-OFF with 4 must-fixes.

Scope reviewed:

- Plan: `~/.mdx/projects/tm-t3code-dmg-scout.md`
- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Base verified: `main` / `origin/main` / `HEAD` all at `4c20d3502b3ac7e18caf86a5b7f9bacec3526364`
- Tree before findings write: clean on `main`

The plan's core shape is correct: DMG-1 should be the standalone Electron app path, with python-build-standalone plus the wheel, electron-builder, bundled resources, and a full app smoke against a provided store. DMG-2 store bundling and DMG-3 update feed should stay out of this slice.

## Must-fixes

1. Add the missed prelaunch PATH reach-back in `desktopRuntime.ts`.

   The plan covers R1, where `desktop/src/backendProcess.ts::buildBackendLaunch` spawns the backend as a bare `transport-matters` command. It misses an earlier reach-back in the same Finder-launch path: `registerAppLifecycle` calls runtime status and reclaim before it builds the backend launch, and `desktop/src/desktopRuntime.ts` hardcodes `STATUS_COMMAND = "transport-matters"` for both `channel status` and `_desktop-reclaim`.

   In a bought app with no system `transport-matters` on PATH, `readDesktopRuntimeStatus` swallows the failed status command and returns null, then `reclaimDesktopRuntime` runs `_desktop-reclaim` through the same missing PATH command. That exception is caught by `registerAppLifecycle` and shows the backend startup failure before the bundled backend can ever launch.

   Required build input: `resolveBundledResources()` must feed the runtime status and reclaim command path too, not only the backend child command and `GATEWAY_ENTRY`. Either add a shared desktop backend command resolver used by `desktopRuntime.ts` and `backendProcess.ts`, or explicitly bypass status and reclaim in packaged standalone mode. Add a unit test for packaged mode with PATH scrubbed that proves no bare `transport-matters` command is executed before launch.

   Evidence: `desktop/src/main.ts:366-420`, `desktop/src/desktopRuntime.ts:4-6`, `desktop/src/desktopRuntime.ts:121-149`, `desktop/src/backendProcess.ts:69-82`.

2. Make the resource resolver apply before every consumer, not only before child spawn.

   The proposed `resolveBundledResources()` seam is right, but the plan says `registerAppLifecycle` sets `GATEWAY_ENTRY` before `launchGateway` and passes the backend interpreter into `buildBackendLaunch`. That is too late if the same resources are needed by runtime status and reclaim, and it is fragile if only the child launch options get patched.

   Required build input: compute packaged resources once at the start of `registerAppLifecycle`, before runtime discovery. Thread the resulting env or command overrides through:

   - runtime status and reclaim
   - `resolveBackendStartupOptions`
   - `startBackendAndCreateWindow`
   - backend launch
   - gateway launch

   The tests should assert that `GATEWAY_ENTRY` and the backend binary are present in the env passed to both child launchers and to the runtime discovery layer.

   Evidence: `desktop/src/main.ts:343-420`, `desktop/src/main.ts:225-245`, `desktop/src/backendProcess.ts:62-94`, `desktop/src/gateway/gatewayProcess.ts:113-160`.

3. The bundled app smoke must consume the exact wheel artifact and a materialized Python install.

   The plan says to extend the desktop xvfb job and bundle python-build-standalone plus the wheel, but it does not pin the desktop packaging smoke to the exact wheel that CI's `package` job already built and uploaded. The current desktop job has no dependency on that package artifact. If DMG-1 builds another wheel inside the desktop job, or copies only a raw `.whl` into Resources, the smoke can prove a different artifact than the release chain and still miss a bad wheel install layout.

   Required build input: make the standalone app packaging step consume the `wheel` artifact from the `package` job, then build a staged Python runtime by installing that wheel and its dependencies into the python-build-standalone prefix before electron-builder copies it with `extraResources`. Before electron-builder runs, assert:

   - the backend executable path exists and is executable
   - importing `transport_matters` resolves under the staged Python prefix
   - `transport_matters/gateway/main.js` exists under the staged install
   - `www/`, `canvas/`, and `gateway/` are present in the installed package

   That keeps DMG-1's outer proof chained to the inner wheel gate.

   Evidence: `.github/workflows/ci.yml:323-456`, `.github/workflows/ci.yml:469-510`, `.github/workflows/ci.yml:270-315`, `WHEEL.md:29-44`, `WHEEL.md:79-87`.

4. Specify the full app smoke inputs so CI does not depend on a real Claude install or an existing runtime.

   The plan says the linux-portable smoke launches from a temp dir with a scrubbed env and asserts `RUN_STARTED -> EXITED`. In the full app path, `POST /v1/runs` goes through the backend capture RPC, which resolves and starts a harness. CI does not have a real Claude CLI. The existing wheel spawn test handles this by creating a fake `claude` binary on PATH; DMG-1 needs the same explicit setup for the outer app smoke.

   Required build input: the standalone app smoke should create a temp fake `claude` that prints and exits 0, prepend only that temp bin plus any bundled Python script directory needed by the app, set `TRANSPORT_MATTERS_DATABASE_URL` to the provided Postgres service, set `TRANSPORT_MATTERS_HOME` and storage under a temp directory, and run with cwd outside the checkout. The smoke should fail if the package-smoke branch runs, if the app attaches to a preexisting runtime, or if any launched command path resolves under the repo checkout. Then drive `POST /v1/runs` and poll `/v1/runs/{id}` to `EXITED`.

   Evidence: `desktop/src/packageSmoke.ts:43-64`, `desktop/src/packageSmoke.ts:87-96`, `packages/runtime/src/server/runtimeRouter.ts:46-85`, `packages/runtime/src/server/runtimeRouter.ts:190-201`, `api/src/transport_matters/api/v1/capture_rpc_routes.py:175-212`, `api/tests/integration/test_gateway_wheel_spawn.py:33-52`, `api/tests/integration/test_gateway_wheel_spawn.py:72-113`.

## Nice-to-fix

1. Keep the new desktop resource seam in the explicit TypeScript build list.

   `desktop/tsconfig.json` uses an explicit `include` list. If `resolveBundledResources()` lands in a new source file, it must be added there or the emitted desktop package can miss it. A unit test can still compile through `tsconfig.test.json`, so this is worth calling out in the implementation checklist.

   Evidence: `desktop/tsconfig.json:17-32`, `desktop/tsconfig.test.json:1-6`.

2. Name the smoke separately from the existing preload package smoke.

   The existing `package:smoke` command is useful preload coverage and should not be overloaded with the standalone app acceptance test. A separate command such as `package:standalone-smoke` or `dmg:smoke` would keep the shell-only preload check and the real bundled runtime check distinct in CI output.

   Evidence: `desktop/package.json:7-14`, `desktop/src/packageSmoke.ts:17-20`, `.github/workflows/ci.yml:314-315`.

## Clean Scope

No objection to the locked decisions:

- python-build-standalone plus installed wheel is the right DMG-1 Python path.
- electron-builder is the right packaging tool for `.app`, `.dmg`, signing, and later update work.
- DMG-2 store bundling and DMG-3 update feed should remain deferred.
- The load-before-capture caveat is a store and launch-order concern for DMG-2; DMG-1 is fine if its smoke uses an explicit provided Postgres URL and proves capture RPC reaches `RUN_STARTED -> EXITED`.

## Verification

Commands run:

- `git status --short --branch`
- `git rev-parse HEAD main origin/main`
- `rg` for electron-builder, packager, python-build-standalone, DMG/update terms, backend and gateway resource symbols
- Targeted line reads of `LESSONS.md`, the DMG scout plan, `WHEEL.md`, `ci.yml`, `desktop/src/main.ts`, `desktop/src/backendProcess.ts`, `desktop/src/gateway/gatewayProcess.ts`, `desktop/src/desktopRuntime.ts`, `desktop/src/packageSmoke.ts`, `desktop/scripts/package-smoke-build.mjs`, `desktop/package.json`, `desktop/tsconfig*.json`, `api/src/transport_matters/cli/desktop_cmd.py`, `api/src/transport_matters/cli/desktop_viewer.py`, `api/src/transport_matters/main.py`, `api/src/transport_matters/api/v1/capture_rpc_routes.py`, `api/src/transport_matters/capture_rpc.py`, `api/src/transport_matters/captured_run.py`, `api/src/transport_matters/captured_claude.py`, `packages/gateway/src/app.ts`, `packages/runtime/src/server/runtimeRouter.ts`, and `api/tests/integration/test_gateway_wheel_spawn.py`.

No repo code changes were made.
