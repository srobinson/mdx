# PR#232 review — t3code P1 slice 2: harden desktop backend shutdown

- **Branch/head:** `feat/desktop-s2` @ `13df87c`
- **Baseline:** `main` @ `cb2bf6f` (cited via `git show main:<path>`)
- **Scope:** Electron desktop backend teardown — `graceThenForce`, `DesktopBackendManager`, `DesktopLifecycle`, `DesktopShutdown`, `main.ts` wiring.
- **Method:** xhigh adversarial pass, 3 independent read-only finders (signal/process, coordinator/orphan-paths, cleanup/tests/sweep) + first-hand verification of every candidate against the code. Working tree verified pristine before and after.
- **Verdict:** No Blocker. **1 Major (latent), 4 Minor.** The core design is sound: SIGTERM→grace→SIGKILL→reap escalation is correct, `requestQuit` idempotency holds, every owned-backend quit path converges on the coordinator, OS-branching is correct, and no orphan was found on any reachable path.

---

## Findings

### 1. [Major — latent] `DesktopShutdown.#runShutdown`: a rejecting finalizer wedges the app permanently un-quittable
`desktop/src/app/DesktopShutdown.ts:44` (`#runShutdown`)

```ts
async #runShutdown(): Promise<void> {
  for (const finalizer of this.#finalizers) {
    await finalizer();          // <- no try/catch/finally
  }
  this.#allowQuit = true;
  this.#appSource.quit();
}
```

`handleBeforeQuit` calls `event.preventDefault()` then `void requestQuit()`. If any finalizer rejects, control never reaches `#allowQuit = true` or `appSource.quit()`. The quit was already prevented, so the app does not quit. `requestQuit` caches the now-rejected promise in `#shutdown` (`DesktopShutdown.ts:36`), so every subsequent `before-quit → handleBeforeQuit → requestQuit` returns the same rejected promise and never retries. Net: the GUI is permanently un-quittable, remaining finalizers never run, and `void this.requestQuit()` (`DesktopShutdown.ts:32`) swallows the rejection as an unhandled promise rejection.

This is a **new** failure mode introduced by this PR: the baseline `before-quit` handlers never called `preventDefault` (`git show main:desktop/src/main.ts:253`), so cleanup could never wedge the app open.

**Reachability:** not triggerable with the current single finalizer `() => backendManager.stop()` → `graceThenForce`, which never rejects (the executor never calls `reject` and `child.kill("SIGTERM"|"SIGKILL")` cannot throw on valid signals; `.finally` does only field assignments). So it is latent today. It is flagged Major because `DesktopShutdown` is a reusable teardown coordinator whose whole contract is an arbitrary `finalizers[]` array, and a PR whose stated purpose is hardening should not ship an extension point that turns a throwing finalizer into an un-quittable app. **Fix:** wrap the finalizer loop in `try { … } finally { this.#allowQuit = true; this.#appSource.quit(); }` (and log/swallow per-finalizer errors) so quit always proceeds.

### 2. [Minor] `DesktopBackendManager` never observes a spontaneous backend exit; `#backend` goes stale
`desktop/src/backend/DesktopBackendManager.ts:25` (`#backend`)

There is no `child.once("exit", …)` anywhere in the manager. If the Python backend crashes on its own after readiness (`watchBackendExitBeforeReady` only covers the pre-readiness window and is disposed in `main.ts:208`), `#backend` stays non-null. Consequences: `currentBackend` reports a dead process as live, and a future `start()` would throw "already running." On quit, `graceThenForce` still handles the dead child gracefully (`child.kill` returns `false` on the reaped handle → immediate `settle`, no stale signal, no hang), so there is no orphan or bad-signal delivery. Low impact today because there is no auto-restart path; worth a `once("exit")` that clears `#backend` for correct liveness/relaunch.

### 3. [Minor] `stopLaunchedBackend` default is an unreachable parallel stop path that bypasses manager ownership
`desktop/src/main.ts:596` (`stopLaunchedBackend`), used as the default at `desktop/src/main.ts:217`

`startBackendAndCreateWindow` defaults `stopBackend` to `stopLaunchedBackend`, which calls `graceThenForce(backend.child)` directly. The only production caller (`registerAppLifecycle`, `main.ts:341`) overrides it with `() => backendManager.stop()`, and the only failure-path test injects its own `stopBackend` stub. So the default is never executed. If it ever were, it would kill the child while `DesktopBackendManager` still holds `#backend` (ownership never cleared), leaving stale state — the same class of issue as finding 2. Altitude/dead smell: either route the default through the manager or make `stopBackend` a required dependency so there is one teardown path.

### 4. [Minor] No integration test covers the real owned-backend quit convergence
`desktop/src/main.ts:281` (`finalizers: [() => backendManager.stop()]`)

The load-bearing wiring — `registerAppLifecycle`'s finalizer driving `graceThenForce` on the actually-launched child, plus the re-entrant `app.quit() → before-quit → handleBeforeQuit(allowQuit=true)` — is unverified end to end. `DesktopShutdown`/`DesktopLifecycle` unit tests use stub finalizers; `main.test.ts`/`main.reclaim.test.ts` assert launch only and never trigger a quit after a backend is spawned. This is exactly the behavior the PR removed `bindBackendQuitCleanup` to re-establish (stop the owned backend on every quit); a future change to the finalizer wiring could silently reintroduce the orphan with all tests green.

### 5. [Minor] DRY: duplicated `getWindowCount` closure
`desktop/src/main.ts:257` and `desktop/src/main.ts:346`

The refactor writes `getWindowCount: () => BrowserWindow.getAllWindows().length` as an identical closure literal at two call sites (baseline had one inline usage inside `bindHostedWindowLifecycle`). Per repo `CLAUDE.md` ("DRY: no compromise … zero tolerance"), extract a single module-scope helper (e.g. `const mainWindowCount = () => BrowserWindow.getAllWindows().length`) shared by both.

---

## Checked and clear (adversarial coverage, no issue found)

- **`graceThenForce` escalation & timer:** every settle path (exit / error / SIGTERM-returns-false / SIGKILL-returns-false / synchronous-exit-during-kill) is guarded by `settled`, clears `forceTimer`, and removes both listeners. No double-resolve, no leaked/late SIGKILL to a reaped/reused pid, no unhandled `error` (listener registered before first `kill`), correct `child.kill` boolean handling. The only non-settling case is a post-SIGKILL unkillable process = slice-5/out-of-scope.
- **2s grace value:** aligned to spec, with the prior 3s explicitly noted in the inline comment (`graceThenForce.ts:41-42`) — not a silent divergence.
- **Removed `stopBackendProcess` `if (child.killed) return` guard:** not a regression; the new boolean handling of `child.kill` covers the already-exited case.
- **Idempotency / concurrent triggers:** `requestQuit` caches `#shutdown`; the re-entrant `app.quit()` correctly passes the `#allowQuit` guard on the second `before-quit`. `DesktopBackendManager.stop()` dedups via `#stopping` with the `this.#backend === backend` clear-guard. No double-teardown, no race.
- **Orphan closure (both origins):** (a) missing SIGINT/SIGTERM handlers → now registered in `registerShutdownHooks`; (b) SIGTERM-only stop → now `graceThenForce` escalates to SIGKILL. Every owned-backend quit path (before-quit, SIGINT, SIGTERM, window-all-closed, health-startup-failure) converges on the coordinator; the hosted path owns no manager backend.
- **OS-branching:** SIGINT/SIGTERM registered only when `platform !== "win32"`; window-all-closed gated `!== "darwin"` via the single consolidated `shouldQuitOnWindowAllClosed` (no duplicate gate); `processSource ?? process` sound.
- **Removed-symbol blast radius:** `stopBackendProcess`, `bindBackendQuitCleanup`, `AppQuitSource` deleted with zero stale importers. `MainWindowOptions` moved to `window.ts`; `HostedWindowOptions extends MainWindowOptions { preloadPath: string }` preserves the required-`preloadPath` shape. `main.reclaim.test.ts` `cancel`→`dispose` mock is a correction (real `BackendExitWatcher` uses `dispose()` on both baseline and HEAD). `main.ts` is 651 lines (< 700); no new file > 700; no function > 150; no em dashes in new code.
