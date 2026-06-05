# Startup gate review

Reviewed `bfb35ee365c387cd3108e3a75eea4edfdc4aacce` against `84d2c66d7bd048e36cadf6e2ac91cc5a48d9f16d` in a clean detached worktree.

## P1: Infrastructure failures render an unrelated screen with no recovery action

Location: `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, symbol `SessionCanvasRoute`; `www/packages/canvas/src/firstrun/FirstRunScreen.tsx`, symbols `FirstRunScreen`, `HarnessSection`, and `SectionBody`; `www/packages/canvas/src/firstrun/useLaunchReadiness.ts`, symbol `useLaunchReadiness`.

Every loading, unreadable, or red infrastructure result replaces the workbench with `FirstRunScreen`. That screen receives no readiness checks and renders only harness inventory. Its readiness invalidation is reachable from the inventory error Retry button or a harness enablement mutation.

When Node, mitmdump, or the gateway is unavailable while harness inventory succeeds, the empty or populated inventory screen shows no failed infrastructure check, remedy, or Retry action. The empty branch says Transport Matters is running while the route is gated on `ready: false`. The Command Center readiness retry is inside the hidden workbench.

Impact: the user is blocked without the reason and cannot recheck after fixing the dependency except by reloading the application. This violates `NOW.md` symbols `Phase 1 first run` and `The startup model`, which require every reported state to carry an in app fix. A session store failure commonly also makes inventory fail and exposes Retry, but a persistent absent store still has no in app repair beyond repeating the same request.

## P2: A remount in one renderer reuses cached readiness

Location: `www/packages/canvas/src/firstrun/useLaunchReadiness.ts`, symbol `useLaunchReadiness`; `www/packages/core/src/queryClient.ts`, symbol `queryClient`; `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx`, symbol `SessionCanvasRoute`.

Readiness uses the shared module scoped QueryClient with infinite staleness and disables mount, reconnect, and focus refetches. After one result is cached, unmounting and remounting `SessionCanvasRoute` in the same renderer issues no new readiness request. Cached green can reopen the workbench after infrastructure fails, and cached red can preserve the gate after recovery.

No persisted onboarding or readiness key exists. A full reload or replacement renderer creates a new QueryClient and rechecks, so the run fifty process restart scenario is covered. The gap applies to route or component reuse within one renderer.

## Historical test evidence

- The infrastructure aggregate test is genuine historical red. At `84d2c66d`, the focused missing binary cases pass while asserting `ready is False`; the new contract requires `True`.
- The red infrastructure screen test is genuine historical red. The base test explicitly requires the workbench to remain visible when readiness fails; the branch requires the startup gate instead.
- The new zero harness DOM assertion that the workbench opens is historical green by itself because the base route always rendered the workbench. The backend aggregate test supplies the behavioral red for that semantic split.
- Current route tests assert the visible workbench or remediation surface, rather than only an intermediate field. They do not assert a visible failing infrastructure reason, recovery action, or red to green transition through user interaction.

## Verified behavior

- `launch_readiness` now treats session store, mitmdump, Node, gateway, and unreadable enablement state as infrastructure. Harness installation, enablement, and credential checks remain in `checks` without folding into `ready`.
- `templateRows.ts`, symbol `launchBlockedReason`, still blocks native and specialist rows on global or matching harness failures. With zero installed harnesses, both native rows are disabled and carry no spawn action.
- The capture preparation path independently rejects `harness_not_installed` and `harness_disabled`, so an unavailable harness cannot start through the server path.
- No other readiness response consumer was found outside Canvas and core transport.
- Exact head verification passed 16 Python readiness tests, 51 route, launcher, and shell tests, plus 3 focused first run and readiness hook tests. The invalid detached frontend and temporary archive commands were discarded.
