# TM Startup Scout — the user-visible half

Scout 2 of 2. Scope: what the user sees and does from double-click to a running agent, the
first-Space answer, the owner's startup-gate shape, the PTY-hosted-login hypothesis, and the
single-startup-seam refactor map. Read-only against `ml/next` at `841e385b` (= origin/main).
Citations are `file:symbol`. The process/boot half belongs to scout 1.

## TL;DR

- The window appears only after backend + gateway pass health; until then the user sees
  **nothing** (packaged) and failures are a modal error box + quit. First paint inside the
  window is a bare `<div>Loading Transport Matters</div>`.
- A brand-new user (empty DB) lands on a zero-chrome canvas whose only guidance is a ⌘K hint
  that fades after 6.5 s, plus a **wrong error banner**: identity resolution returns
  `worktree_not_found` and the UI renders "The Worktree for this Canvas no longer exists" —
  a stale-link message shown to someone who never had a Worktree, with no create action.
- Explicit create paths exist and work: ⌘K → Workdir → "Create new Workdir" (bootstraps a
  Space when the inventory is empty) and the CLI launch bootstrap. No seeding rule holds:
  resolution never creates.
- **PTY hypothesis: confirmed, with a critical correction.** The harness's own login can be
  hosted in an existing pane today — but only via the **plain-terminal** path, not a
  captured run. A captured run both requires the identity triple (`POST /v1/runs` mandates
  `worktreeId`) and, worse, launches into a **managed ephemeral home** whose seeder copies
  credentials from the default home — logging in inside a captured pane authenticates the
  throwaway home, not the user. The plain terminal (`/api/terminal`) needs no identity and
  runs the user's real shell/env, so `claude` login lands in the real `~/.claude`. One small
  client rule to relax (details below).
- Startup on the front end is **many seams, not one**: desktop process gates, canvas identity
  ladder, launcher readiness rows — and the browser consumes **zero** harness readiness
  facts today (`fetchCapabilities` has no www caller; `authentication_status` appears
  nowhere in www). The facts a startup gate needs already exist on the control plane
  (`/api/capabilities`, `/v1/harnesses`, MCP `harnesses(view="launch")`); only the
  projection and presentation are missing. That is the refactor.

## 1. The user journey today, step by step

### A. Packaged app (double-click the DMG-installed .app)

1. `desktop/src/main.ts:registerDesktopLifecycleFromEnv` — applies channel identity
   (`applyChannelIdentity`: app name, user-data dir, preview dock icon), then forks on env:
   package-smoke, hosted `DESKTOP_ROUTE_URL`, else `registerAppLifecycle`.
2. `main.ts:registerAppLifecycle` → `app.whenReady()` → bundled resources found →
   `main.ts:startBundledStandalone` — workspace defaults to `$HOME`, no ambient-runtime
   discovery by design.
3. `main.ts:startBackendAndCreateWindow` launches Python backend + node gateway, then
   health-gates **both** (`Promise.allSettled` over `waitForLaunchedBackend` /
   `backendHealth.ts:waitForBackendHealth`). **The BrowserWindow is created only after both
   are healthy.** On screen during this: nothing but a bouncing dock icon. There is no
   splash, no progress surface.
4. Failure → `main.ts:showBackendStartupFailure` → `dialog.showErrorBox("Transport Matters
   failed to start", message)` → quit. The message is the raw child error (a Python
   traceback tail or the session-store preflight text). Actionable only by accident.
5. Window loads `window.ts:rendererUrlForPort` → `http://127.0.0.1:{port}/canvas`
   (`window.ts:createHostedWindow`, shows on `ready-to-show`; `allowedHostedPath` admits
   only `/` and `/canvas`). Renderer load failure → `window.ts:showHostedLoadFailure` modal.

### B. Canvas boot (what paints)

1. `canvas/src/main.tsx` — mounts window chrome (drag strip, channel badge), applies
   persisted theme, renders `canvas/src/app.tsx:CanvasApp`.
2. `CanvasApp` Suspense fallback: an unstyled `<div>Loading Transport Matters</div>` while
   the lazy `SessionCanvasRoute` chunk loads.
3. `workbench/SessionCanvasRoute.tsx:SessionCanvasRoute` mounts the workbench immediately
   (ambient backdrop, ⌘K `CommandCenter`, pane layer) and dispatches
   `initialize-from-launch` to the identity owner.
4. Identity ladder — `model/canvasIdentityOwner.ts:initializeFromLaunch`: URL tuple claim →
   persisted locator claim → `resolveWorkdir(meta.cwd)`. Claims verify via
   `space-client/spaceTransport.ts:verifyActingContext`; the cwd path resolves via
   `resolveWorkdirContext` → server
   `packages/space/src/service/SpaceContextService.resolveWorkdirContext` →
   `packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate`.
5. Resting state: zero chrome + `launcher/FirstRunHint.tsx:FirstRunHint` — a faint "⌘K to
   command" that shows once ever (localStorage `tm.launcher.hintSeen`) and fades after
   6.5 s. **This is the entire onboarding surface in the product.** (Search run:
   `onboarding|welcome|first-run|wizard|getting started` across `www/packages` — only
   `FirstRunHint.tsx` and a CommandCenter comment hit.)

### C. Brand-new user, empty database — what actually happens

`resolveWorkdirCandidate` over an empty inventory returns `worktree_not_found`
(`domain/actingContext.ts`, `candidates.length === 0` branch). The identity owner sets
`hydrationStatus: "blocked"`, `resolutionError: "worktree_not_found"`, and
`SessionCanvasRoute.actingContextErrorMessage` renders:

> "The Worktree for this Canvas no longer exists."

- Wrong message: the user never had a Worktree. It describes a stale link, not a first run.
- No action: the Retry button renders only for `transport_error`. There is no "create a
  Workdir" call to action anywhere in the alert path.
- The ⌘K palette still works (CommandCenter renders unconditionally in `CanvasWorkbench`),
  so the escape hatch exists — the user just has to know ⌘K, find the Workdir domain, and
  understand TM's Space/Workdir vocabulary cold.

### D. First Space / Worktree / Canvas — the explicit create paths (found, traced)

There are exactly two, both explicit, both NO-SEEDING-conformant:

1. **⌘K → Workdir domain.** `launcher/workdirRows.ts:buildSpaceRows` always leads with
   "Create new space" and "Create new Workdir" rows (also reachable from a drilled Space via
   `buildWorktreeRows`'s trailing create row, so a zero-worktree Space never dead-ends).
   Input is typed into the palette (`launcher/spaceCommandInput.ts:spaceCommandInputFor`),
   dispatched by `workbench/CanvasCommandDispatcher.ts:useCanvasCommandHandler` →
   `workbench/spaceCommandDispatcher.ts:dispatchSpaceMutation`.
   `createWorkdirWithBootstrap` handles the cold start: empty inventory → creates a Space
   named from the path tail, then `POST /v1/spaces/{id}/worktrees` (server mints the root
   canvas; `WorktreeSummary.rootCanvasId` comes back), activates the full triple, rolls the
   bootstrap Space back if the Workdir create fails. This path is complete and correct.
2. **CLI launch.** `cli/space_bootstrap.py:bootstrap_cli_space` — `transport-matters claude`
   detects the containing workdir, and if no owned Worktree matches, explicitly creates
   Space + Workdir via `SpaceCrudService` before launching. So a terminal-first user gets
   the triple as a by-product of their first capture.

Gap between them: the *desktop-first* new user is expected to discover path 1 with no
guidance beyond a 6.5-second hint, while the error banner actively misleads (C above).

Failure surfacing defect: `CanvasCommandDispatcher` catches `dispatchSpaceMutation` errors
with `console.error("Failed to update Space inventory:", …)` — a mistyped path in
create-workdir fails **silently** for the user. Same for `spawn` (`addCapturedRun` throw →
console only) and `spawn-terminal`.

## 2. Missing-prerequisite matrix (what the user is shown)

| Prerequisite missing | Where it's detected | What the user sees |
| --- | --- | --- |
| Postgres (packaged/dev desktop) | backend dies pre-health or degrades; spawn blocked at capture-prepare RPC | Either the startup modal (raw preflight text) or, if the backend degrades, a pane spawn failure string. `www` learns DB status nowhere (`db_status` grep: zero hits) — NOW.md already names this gap |
| Postgres (CLI launch) | `cli/launch_runtime.py:preflight_session_store_or_exit` | The one good story: red error + `session_store_setup_help()` actionable text, exit 2 before anything spawns |
| No gateway configured | `api/v1/runs_unavailable.py` | Explicit 503 `runtime_unavailable` detail on any run action; pane shows the spawn-error string |
| Harness not installed | Server knows (`api/v1/capabilities.py:get_capabilities`, `/v1/harnesses` inventory); templates carry `harness_not_installed` readiness | Native rows are **always enabled** (`templateRows.ts:agentSpawnRows`; the "Native agents are always available" copy is false here). User finds out only after spawning: `infrastructure/runtime/useCapturedRunBinding.ts:spawnErrorMessage` — "Claude Code captured run failed to start: <detail>". Specialist template rows *do* gate (disabled + "Install the required harness") — the vocabulary exists, natives just don't use it |
| Wrong harness version | Compatibility surface, advisory rollout (`harnesses/compatibility.py:match_release`) | Nothing. NOW.md: per-launch compatibility message is deliberately gated behind the control-plane UI redesign |
| Not authenticated | `harnesses/connections.py:AuthenticationStatus` (`login_required`/`expired`), exposed on `/v1/harnesses` and MCP `harnesses(view="launch")` (`api/v1/harness_launch_view.py:_authentication_status`) | Nothing pre-launch (grep `login_required|authentication` in www: zero hits). The harness's own login prompt appears inside the PTY pane after spawn — which *almost* rescues it, except the login lands in the wrong home (next section) |
| No Space/Worktree/Canvas | `resolveWorkdirCandidate` → `worktree_not_found` | The misleading stale-link banner, no CTA (§1C) |

## 3. The owner's shape, the PTY hypothesis, and a cleaner composite

### Owner's shape (recurring startup gate, presents the harness's own login)

Agrees with the code's grain. Every fact the gate needs is already served, credential-free,
by the control plane: installed + version (`/api/capabilities`), version-in-range
(compatibility pointer surface), auth status per connection (`/v1/harnesses`), Space
inventory emptiness (`/v1/spaces`). A recurring gate is right, not a one-time wizard: auth
expires (`expired` is a first-class `AuthenticationStatus`), versions drift, DBs move. The
gate should be a *projection re-checked on every desktop launch*, not a persisted
"onboarded" bit — the repo's own precedent is `ClaudeSeeder` stamping
`hasCompletedOnboarding: true` into managed homes, i.e. TM already treats onboarding flags
as state to be computed, not remembered.

### PTY hypothesis: confirmed via the plain terminal, refuted via captured runs

Two PTY paths exist, and they differ exactly where it matters:

**Captured run path — wrong vehicle for login, two blockers.**
1. *The chicken-and-egg is real.* `POST /v1/runs` requires `worktreeId`
   (`core/transport.ts:createCapturedRun` — "the Spaces rekey made worktreeId mandatory";
   gateway `runtime/src/server/runtimeRouter.ts` builds the full identity into
   `RunManager.createWithDisposition`). At the point startup needs a login, a new user has
   no triple. The client enforces it too: `canvasStore.addCapturedRun` throws on a canvas
   with no rooted worktree (`CanvasCommandDispatcher`'s try/catch comment).
2. *The disqualifier even after the triple exists:* a captured run launches under a managed
   ephemeral home — `launch_environment.py:HOME_DIR_ENV_BY_HARNESS` sets
   `CLAUDE_CONFIG_DIR`/`CODEX_HOME` to the run's `--agent-home-dir`, and
   `cli/claude_home.py:ClaudeSeeder.seed` copies `userID`/`oauthAccount` *from* the default
   home and forces `hasCompletedOnboarding`. Logging in inside that pane writes credentials
   into the throwaway managed home. The next run mints a fresh home and is unauthenticated
   again. Hosting login in a captured run would *appear* to work and silently fix nothing.

**Plain terminal path — free, today.** The gateway's plain terminal
(`runtime/src/server/plainTerminalConnection.ts:handlePlainTerminalConnection` →
`service/PlainTerminalSessions`) takes only `cols`/`rows`/optional `cwd` — **no identity
triple, server-side**. It spawns the user's real shell with the user's env, so an
interactive harness login executed there writes the real `~/.claude`/`~/.codex`. The canvas
already renders it as a pane (Developers → "Spawn terminal", `viewers/terminal`,
`infrastructure/runtime/internal/terminalSocket.ts:terminalSocketUrl` → `/api/terminal`).

The only blocker is a client-side placement rule: `model/canvasActions.ts:spawnTerminal`
calls `requireWorktreeId(getSpawnWorktreeId())` — a pane-record convention (terminal panes
anchor to a worktree for cwd), not a server constraint (the client does not even send `cwd`
today). A startup-gate terminal pane that passes an explicit `cwd` (`meta.cwd` or `$HOME`)
and skips the worktree anchor is a small, contained change. So: **the harness's own login
screens can run inside a pane TM already knows how to drive, with no auth UI built, and no
identity chicken-and-egg — provided the gate uses the plain-terminal seam.**

Sequencing note: auth comes *before* the first Space in the gate order, and the plain
terminal makes that possible; the captured-run path would have forced create-workdir first
and still botched the login home.

### Cleaner option to put beside the owner's shape

Keep the owner's flow, but make the gate itself **data served by the control plane**: one
readiness projection (new `GET /v1/startup` view, or extend `api/v1/meta.py` which NOW.md
already earmarks for `db_status`) returning ordered steps, each
`{id, status, detail, action}` — `db`, `harness_installed`, `harness_version`,
`harness_auth`, `first_workdir`. Reuse the runtime-template readiness vocabulary
(`ready | needs_setup | unavailable | invalid` + reason strings,
`templateRows.ts:readinessLabel` already renders it) instead of minting a new status enum.
The UI renders the steps; "Authenticate Claude Code" opens the plain-terminal login pane;
"Create your first Workdir" opens the existing ⌘K create input pre-focused. Trade-off
versus a pure client gate: one more read surface to maintain — but it is the only shape
where the director sees the same startup truth (below), and it collapses three roadmap
items (onboarding #2, no-DB store picker, this gate) onto one seam instead of three
bespoke flows touching the same facts.

### North Star conformance per step

- Detect / version / auth status: already programmatic — `/v1/harnesses`, MCP
  `harnesses(view="launch")`. A director can poll the same verdicts the gate renders.
- Create Space/Workdir: `POST /v1/spaces`, `POST /v1/spaces/{id}/worktrees`
  (`packages/space/src/server/spaceRouter.ts`); CLI bootstrap shares the service. Already
  two clients of one plane.
- Interactive login is inherently human; the programmatic complement already landed:
  `credential_broker.py:CredentialBroker` (#335) mints access tokens from the owner
  credential the human minted once. The gate is how the *owner* credential comes to exist;
  the broker is how the director uses it. Complementary, not conflicting.
- A UI-only gate (React state deciding "you may not pass") would violate the lens; a
  projection-driven gate cannot — the UI merely renders server verdicts any client can read.

## 4. Refactoring: where startup lives today (the seam inventory)

Verdict: **many seams, no owner.** Current owners, exhaustively:

**Desktop process plane** (ordered gates, well-factored, but hard-coded sequence):
`main.ts:registerDesktopLifecycleFromEnv` → `applyChannelIdentity` →
`registerAppLifecycle` (bundled/ambient fork) → `startBundledStandalone` /
`startAmbientOrManagedBackend` (discover → reclaim → managed) →
`startBackendAndCreateWindow` (dual health gate) → `showBackendStartupFailure`. Plus
`hostedLiveness.ts:registerHostedBackendLivenessPoll` (hosted-mode liveness) and
`backendProcess.ts:watchBackendExitBeforeReady`.

**Canvas boot**: `main.tsx` (chrome + theme), `app.tsx:CanvasApp` (Suspense fallback),
`SessionCanvasRoute` (identity dispatch, captured-run reconciliation
`reconcileCapturedRuns`, activity stream enablement, the alert stack).

**Identity**: `canvasIdentityOwner.ts:initializeFromLaunch` ladder + failure-code → message
map `SessionCanvasRoute.actingContextErrorMessage`.

**Readiness presentation**: `templateRows.ts:readinessLabel` (specialists only),
`commandRows.ts:asyncStatusRows` (the four-state loading/error/empty/populated grammar),
`CanvasWorkbench`'s `canvas-alert-stack`.

**Startup-relevant facts consumed by the browser: none.** Searches run:
`fetchCapabilities|useCapabilities` in www → sole hit is its own definition
(`core/transport.ts:fetchCapabilities`, whose doc comment cites a deleted "desktop lab" —
dead export); `login_required|authentication` in www → zero; `db_status` in www → zero.

**What the single seam should be** (bound to what exists, nothing invented):
1. Server: the readiness projection above (`api/v1/meta.py` extension or sibling view
   module beside `harness_launch_view.py` — that file is the pattern: a lean projection
   over the inventory service).
2. Client: one `StartupGate` component mounted in `SessionCanvasRoute` ahead of the alert
   stack, driven purely by the projection — an ordered registry of steps as *data*, each
   binding `status` → an existing affordance (plain-terminal pane, ⌘K create input,
   settings). The identity failure-code map folds into it as the `first_workdir` step, which
   kills the misleading `worktree_not_found` banner as a side effect.
3. Desktop keeps its process gates (they are pre-renderer by nature) but replaces the raw
   `showErrorBox` text with the same step vocabulary where it can (the preflight already
   emits good text on the CLI path — route it).

A proposal inventing a new client-side wizard framework, a new status enum, or a new
onboarding store would be a defect against this map; every needed part has an owner above.

## 5. Quality Map

| Area | Grade | Evidence |
| --- | --- | --- |
| Desktop boot lifecycle | A- | Clean forks, dual health gate with settled-pair handling, ordered shutdown finalizers, dense test files. Gap: zero on-screen feedback pre-window; modal shows raw child errors |
| Identity resolution | A machinery / D first-run UX | Generation-guarded ladder, locator fallback, NO-SEEDING held. But empty inventory renders a stale-link error with no CTA (`actingContextErrorMessage` has no `first run` awareness) |
| Launcher grammar | A | Pure row builders, four-state async pattern, create paths complete incl. empty-inventory bootstrap + rollback (`createWorkdirWithBootstrap`) |
| Mutation/spawn error surfacing | C | `console.error` black holes for create-space/create-workdir/spawn/spawn-terminal in `CanvasCommandDispatcher`; pane-level `spawnError` exists but only for the run path |
| Browser consumption of readiness facts | D | `fetchCapabilities` dead in www (stale doc comment); auth status, versions, compatibility all server-ready and browser-invisible; native spawn rows falsely "always available" |
| Startup as a seam | C | Scattered per §4; no single owner; three roadmap items (onboarding, no-DB picker, this gate) queued to touch the same facts separately |

Smaller defects worth a line: `FirstRunHint` is unrecoverable after one showing (localStorage
flag, no re-trigger); `window.ts:allowedHostedPath` hard-codes `/` + `/canvas` (fine today,
will bite a `/setup` route — another reason the gate should live *inside* `/canvas`, not at a
new path).

## Searches run (for "none found" claims)

- `onboarding|welcome|first-run|wizard|getting started` across `www/packages` → FirstRunHint only
- `fetchCapabilities|useCapabilities` across `www/packages` → definition only, no consumer
- `login_required|authentication` across `www/packages/{canvas,core}/src` → none
- `db_status|dbStatus` across `www/packages` + `api/v1/meta.py` → none
- fmm index absent in this worktree (`fmm generate` never run here); all searches via grep
