# TM first-run: scout and proposal (fable seat)

Date: 2026-08-04. Read-only scout at `c03edbd9` in worktree `overlay-landing`.
Evidence base: source, `transport-matters doctor` on the installed product
(0.3.0.post1.dev377), `~/.mdx/projects/tm-print-vs-interactive.md`, and the
owner direction records of 2026-08-03 and 2026-08-04.

Cited as `path:Symbol`. Never line numbers.

---

## Part 1 — Scout: what exists per journey step

### Step 1: Install TM

EXISTS, out of scope. `transport-matters` installs as a uv tool; `doctor`,
`paths`, `desktop`, `claude`, `codex` all ship.

### Step 2: Run TM, state created silently, asks nothing

EXISTS, nearly whole.

- Readiness evaluator at the boundary, exactly the shape the 2026-08-04
  direction asks for: `api/src/transport_matters/captured/readiness.py:launch_readiness`
  returns `LaunchReadiness{ready, checks}` with per-check server-owned
  remediation from `infrastructure_guidance.py`. Route
  `api/v1/launch_readiness.py:get_launch_readiness` at `GET /v1/launch-readiness`.
  `ready` is infrastructure-only; zero installed harnesses is a valid ready state.
- Client gate: `www/packages/canvas/src/firstrun/useLaunchReadiness.ts:useLaunchReadiness`,
  rendered by `firstrun/FirstRunScreen.tsx:FirstRunScreen` (infrastructure mode:
  "Transport Matters is not ready", failed checks, remediation, Retry), mounted
  as `routeAlert` in `workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`.
- Channel homes and per-run storage are created on demand (`workspace.py:workspace_root`,
  `run_root`); no prompt anywhere.
- Gap, named honestly: the session store is still a Postgres URL the user must
  have. `cli/launch_runtime.py:preflight_session_store_or_exit` and
  `RunManager._ensure_session_store_available` (Python side:
  `run_manager.py`) block launches without it. "Asks nothing" ends where
  Postgres provisioning begins. Not solvable inside this journey; the readiness
  screen carries it as a check with remediation, which is the honest floor.

### Step 3: Detect harnesses, present them ticked

EXISTS, end to end. This step is essentially built.

- Registry, not hardcode: `harnesses/__init__.py:HarnessDescriptor` with
  `_DESCRIPTORS = (claude, codex, grok)`. Only a descriptor carrying a
  `HarnessLaunchBoundary` is launch-eligible; `grok` is registered
  discovery-only, which proves the add-a-harness path works. Adding a harness =
  widen `HarnessId`, add a descriptor, then extend the per-harness seams
  (`cli/launch_profile.py:HARNESSES`, `state_refresh.py:AUTHENTICATION_PROBES` /
  `MODEL_ENUMERATION_PROBES`, `credential_source.py:_CREDENTIAL_PROFILES`,
  `launch/environment.py:HOME_DIR_ENV_BY_HARNESS`). The journey never changes.
- Detection: `capabilities.py:detect_harnesses` (binary discovery +
  `probe_binary_version`, bounded, never raises). Verified live: `doctor`
  reports claude 2.1.221, codex 0.146.0, grok 0.2.118 on this machine.
- Sole producer of stored evidence: `harnesses/state_refresh.py:refresh_harness_state`,
  a lifespan task in `main.py`. Detects every registered harness, upserts
  installation evidence, enumerates models once per exact version (cached
  snapshot, which already answers "per-model capture only where variation is
  observed"), runs auth probes.
- Auth state: `harnesses/probes/__init__.py:AuthenticationProbeAdapter` with
  concrete probes `probes/claude.py:AUTHENTICATION_PROBE` (`auth status --json`),
  `probes/codex.py` (`login status`), `probes/grok.py` (stub, always
  `probe_adapter_pending`). Statuses land as
  `connections.py:AuthenticationStatus` = authenticated | login_required |
  expired | unknown. Probes are diagnostic, never launch gates; staleness is
  suppressed (`ConnectionDiagnosticsInfo.access_stale`). Credential file
  readiness is separate: `credential_source.py:harness_credential_error`
  (no minting), macOS Claude mints via `resolve_credential_path`.
- One read model: `harnesses/inventory.py:harness_inventory`, the single join
  behind `GET /v1/harnesses` (`api/v1/harnesses.py:get_harnesses`), the MCP
  view (`api/v1/harness_launch_view.py:project_harnesses_view`), and the UI.
- The presentation surface EXISTS: `firstrun/FirstRunScreen.tsx:FirstRunScreen`
  harness mode renders per-harness cards (`firstrun/harnessCards.ts:harnessCard`,
  facts Detected and Authenticated, `login_command` remediation, enable toggle
  via `PUT /v1/harnesses/{id}/enablement`), polling while the startup refresh is
  in flight (`useHarnessInventory.ts:inventoryPollInterval`, 3s). Today it is
  mounted only inside the ⌘K palette settings scope
  (`launcher/CommandCenter.tsx:CommandCenter`) and as the readiness alert.
  Nothing lands the user on it.

### Step 4: Capture a first turn

EXISTS as machinery; nothing invokes it for first contact.

- Capture seam: `captured/run.py:prepare_captured_run` (+ sibling
  `run_captured_run_on_local_tty` for the detached CLI path). Canvas chain,
  complete: `model/capturedRunStore.ts:useCapturedRunStore.ensureRun` →
  `core/src/transport.ts:createCapturedRunView` → `POST /v1/runs` →
  `api/v1/run_proxy.py:RunRouteProxy` → gateway →
  `runtime/src/server/runtimeRouter.ts:registerRunRoutes` →
  `runtime/src/service/RunManager.ts:RunManager.createWithDisposition` →
  `adapters/CaptureRpcClient.ts:prepareCapture` →
  `api/v1/capture_rpc_routes.py:prepare_capture` →
  `capture_rpc.py:CaptureLeaseRegistry.prepare_capture` → `prepare_captured_run`,
  PTY via `adapters/NodePtyAdapter.ts`, pane
  `viewers/terminal/CapturedRunPane.tsx:CapturedRunPane`.
- Interactive by construction: the pane is a real PTY, so the hard constraint
  (print is not wire-equivalent; measured 2026-08-04) is satisfied for free,
  and the harness's own dialogs render inside the pane where the user answers
  them. TM writes no trust state; the read-only-home rule holds.
- The launch contract already carries what a demo turn needs:
  `runtime/src/ports.ts:PrepareCaptureInput` has `initialPrompt` + `deliveryId`,
  `model`/`effort` optional, `harness` a string. Canvas affinity (spaceId,
  anchorWorktreeId, worktreeId, canvasId) is required and resolvable from a
  bare cwd: `model/canvasIdentityOwner.ts:resolveWorkdir` →
  `space/src/server/spaceRouter.ts` `POST /spaces/acting-context/resolve-workdir`.
  No new identity machinery needed.
- Canvas runs are never armed, verified: `breakpoint.py:arm` has exactly one
  production caller (`api/v1/breakpoint_routes.py:arm_breakpoint`), whose only
  client is the inspector bundle (`inspector/src/api.ts:armBreakpoint`). The
  canvas bundle contains zero breakpoint or override calls. The bypass is
  absence of a caller, not a guard.
- TM's own injection: `cli/prompt.py:inject_system_prompt` prepends
  `--append-system-prompt` with the run self-identity block, Claude only, ON by
  default for canvas runs (`RunManager.createNew` never sends `noSystemPrompt`
  though the field exists end to end). A first-turn reveal must switch it off
  or attribute it, or the reveal shows TM's own bytes as the agent's.

### Step 5: The reveal

EXISTS as components; the composition and the headline do not.

- Token bar: `inspector/src/components/detail/TokenBar.tsx:TokenBar`
  (cache read / cache write / input, hover cards, `TokenStat` legend).
- System parts, indexed, char-counted: `editor/SystemSection.tsx:SystemSection`.
- Tools: `editor/ToolsSection.tsx:ToolsSection` (count, per-tool and per-group
  chars). Headline counts also in `detail/ExchangeCard.tsx:ExchangeCard`.
- Char accounting, both planes: `overrides/audit.py:count_chars_parts` and
  `inspector/src/lib/charAccounting.ts:countCharsParts` (codepoint-exact).
- Before/after attribution: `editor/EditorLedger.tsx:CharsLedger` and
  `detail/CompressionBar.tsx:CompressionBar` (only meaningful once overrides
  exist; first-run has none).
- Read-only composition: `detail/InspectTab.tsx:InspectTab`; canvas-side fork
  `viewers/registry.tsx` viewer `provider-exchange` → `ArkExchangeViewer`, so
  the reveal can render in a canvas pane beside the terminal. Data is the
  main-origin per-run reads (`GET /v1/runs/{id}/exchanges…`), disk-backed and
  DB-independent. This matters because `RunManager.register` drops the per-run
  `webPort`; the per-run inspector origin is not addressable from the canvas.
- Inspector zero state: `inspector/src/routeLayout.tsx:WaitingScreen`, whose
  trigger is literally the first-run condition (no exchanges, nothing paused).
- NONE FOUND: an injected-reminder-beside-your-words view. The string
  `system-reminder` appears nowhere in product code (searches: `reminder|
  system.?reminder|injected` across www/packages, packages/, api/src;
  `extract_user_prompt_text` returns only the last renderable block). Closest
  raw material: `editor/BlockRow.tsx:BlockRow` already renders an injected
  reminder as an unlabelled sibling text row with its own char count.
- NONE FOUND: any demo / sample-run / first-turn affordance, any welcome or
  wizard surface, in either bundle or the CLI (searches: `demo|sample.?run|
  onboard|walkthrough|tour|first.?turn|tutorial|welcome|wizard|getting started`
  across api/src, packages, www, desktop; only `cli/claude_home.py` seeding
  Claude's own `hasCompletedOnboarding` into managed homes, and the decorative
  `launcher/FirstRunHint.tsx:FirstRunHint` ⌘K chip).

### The overlay, honestly

"TM takes over" takes over nothing today, confirmed at three layers:
`overrides/state.py:OverrideStore` is populated only by
`api/v1/overrides.py:patch_overrides`, whose only client is the inspector
breakpoint editor (`editor/BreakpointEditorActions.ts:useBreakpointEditorActions`),
which only exists after an arm that the canvas path never performs. The
overlays surface (`inspector/src/stores/overlaysStore.ts:useOverlaysStore`,
`routes/OverlaysView.tsx`) is curation only; no apply-at-intercept pipeline, no
versioning, no launch-spec field (`FrozenLaunchSpec`, `candidate_key`: not in
code). A first-run built on the reveal alone is the honest product today, and
the 2026-08-03 direction (overlay lives in Settings; first-run is one entry
point into surfaces Settings owns) says that is also the right order.

### Running-product observations

- `doctor` (run live): all checks pass; detects three harnesses; reports
  claude and codex credentials ready; grok gets a binary probe but no
  credential or auth line. Doctor never reads stored `AuthenticationStatus`.
- Desktop lands on `/canvas` (`desktop/src/window.ts:rendererUrlForPort`,
  allowed paths exactly `/` and `/canvas`). The canvas resting state is
  deliberately zero chrome: ambient backdrop plus a fading ⌘K hint. The
  inspector at `/` shows `WaitingScreen`. So today's true first screen is an
  empty canvas with no instruction that survives 6.5 seconds.
- Canvas→inspector navigation is dead-but-ready plumbing: a `goto` command
  exists in `launcher/commandTypes.ts` and `CanvasCommandDispatcher.ts:navigateToRoute`
  with zero producers.
- Note for other seats: a report that 22 Python files fail to parse at HEAD is
  a false positive. `except OSError, ValueError:` is PEP 758 syntax; the
  project pins `requires-python >= 3.14` and parses clean on 3.14.6 (verified).

---

## Part 2 — Proposals

Two proposals, one fork between them: whether TM spends the first turn itself
or waits for the user's first word. Everything else is shared, because the
scout shows one assembly is simply true: the landing surface exists
(FirstRunScreen), the capture chain exists (POST /v1/runs), the reveal
components exist (ArkExchangeViewer + accounting). What is missing is the
mount, the trigger, and the headline. No proposal below invents a capability
the scout found.

### Proposal A — Land on the lens (recommended)

The empty canvas becomes the first-run surface; TM runs one trivial turn on
one harness and reveals it before the user has typed anything.

**Screens, in order.**

1. **Launch.** `transport-matters desktop` → Electron opens `/canvas`. TM state
   is created silently (already true). If `launch_readiness` is not ready, the
   existing FirstRunScreen infrastructure mode renders with remediation and
   Retry. User does nothing unless infrastructure is genuinely theirs to fix
   (the Postgres check is the one honest ask).
2. **Harnesses, ticked.** New mount, existing component: when no captured run
   has ever existed for this owner (empty run list / no workspace history),
   the canvas resting state renders `FirstRunScreen` harness mode instead of
   the bare backdrop. Cards tick from Detected to Authenticated as
   `refresh_harness_state` lands; the 3s poll and the "checking" summary state
   already exist. User does nothing. Not-authed cards carry the exact login
   command; absent harnesses show as not detected. The screen is identical to
   the permanent ⌘K settings pane, which satisfies the standing rule that
   everything a startup flow does must be a settings flow.
3. **One keystroke.** A single button on that screen: "Show me what {harness}
   sends". Harness chosen by TM: first authenticated launch-eligible
   descriptor in registry order. No picker. (Fully automatic launch is
   possible with the same wiring, but the demo turn spends the user's own
   tokens, roughly a 15k-token context for Claude today; one explicit
   keystroke is the defensible consent. Owner's call; the code path is
   identical.)
4. **The turn runs where the user can see it.** The button calls the existing
   `ensureRun` → `POST /v1/runs` with `initialPrompt` = a trivial fixed prompt,
   `deliveryId` paired, `noSystemPrompt: true` (field exists end to end; only
   `RunManager.createNew` needs to pass it). A `CapturedRunPane` opens. The
   harness's own first-run dialogs, Claude's per-project trust gate included,
   appear inside that pane, which is the product's normal captured-run pane,
   so nothing looks broken; the copy above the pane says the agent is live
   here and anything it asks is the user's to answer. TM writes no trust state.
5. **The reveal.** On the first settled exchange (the workspace activity
   stream already signals it), a `provider-exchange` pane opens beside the
   terminal on that exchange, headed by a new headline strip:
   **"{contextTokens} tokens left your machine before you typed a word"**,
   itemized underneath by the existing composition: {N} system parts at {chars}
   chars, {T} tools at {chars} chars, session context at {chars} chars, token
   bar split cache read / cache write / input. For Claude Code 2.1.221 the
   measured magnitude is 3 system parts totalling 33.0k chars, a 21.9k-char
   session-start message, and 22 tool schemas; the user's own prompt is 34
   chars. That contrast is the money.

**The single fact that lands:** the first turn's context token total, with the
chars-you-did-not-write itemization one glance below it.

**Binds to (existing):** `FirstRunScreen` + `harnessCards` + `useHarnessInventory`
+ `useLaunchReadiness`; `harness_inventory` / `refresh_harness_state` /
`AuthenticationProbeAdapter`; `useCapturedRunStore.ensureRun` →
`PrepareCaptureInput` (`initialPrompt`, `noSystemPrompt`) → `prepare_captured_run`;
`resolveWorkdir` acting-context resolution; `CapturedRunPane`; viewer registry
`provider-exchange` / `ArkExchangeViewer`; `countCharsParts` /
`count_chars_parts`; `TokenBar` atoms; disk-backed `GET /v1/runs/{id}/exchanges…`.

**Genuinely new (complete list):**
1. The landing mount: render FirstRunScreen as the canvas resting state when
   no run history exists, replacing nothing (the zero-chrome canvas returns
   forever after).
2. The button and its harness-pick rule (first authed in registry order).
3. `noSystemPrompt` pass-through in `RunManager.createNew` (one field).
4. The reveal trigger: first exchange record → spawn `provider-exchange` pane.
5. The headline strip component over existing accounting.
Nothing else. Labelling injected reminders beside the user's words is a later
slice; `BlockRow` already shows them as rows, unlabelled, and the headline does
not depend on it.

**Smallest testable slice:** the landing mount alone. Fresh channel home,
`transport-matters desktop`, and the user sees their harnesses detected and
ticked live instead of an empty canvas. Every read it needs ships today.
Slice 2 adds the button, the run, and the reveal pane.

**Edge answers.** One authed vs many: same screen, cards are the loop; the demo
turn runs on exactly one harness, and every other harness gets its reveal
passively on its first real run, because TM is already in its path (the
2026-08-04 rule that user traffic is the corpus). Installed-not-authed: card
shows the login command, never blocks the others. Zero authed: the screen is
the blocked-on-user state and keeps polling; that matches the direction memo's
only product precondition. Slow: checking state + poll. Absent: not detected,
inert card. Harness dialog placement: inside the pane, answered by the present
user, framed by the copy.

**Risks to prove, not argue:** (a) `initialPrompt` delivery order against
Claude's trust dialog, unverified; if the prompt fires into the dialog, degrade
to Proposal B for that run (pane sits ready, headline waits for the user's
word). (b) Where the user's trust answer persists under the managed-home
overlay; TM must not write it, but must also not swallow it into an ephemeral
home so it is re-asked every capture. (c) The demo turn on codex: no TM
injection exists there (structurally clean), but incremental later-turn
payloads mean the reveal copy must describe turn one only.

### Proposal B — Same landing, no demo turn

Screens 1 and 2 identical. No button, no `initialPrompt`. The pane opens (or
the user opens one via ⌘K exactly as today) and the reveal pane spawns on the
first real exchange the user causes.

- Costs: the money moment waits for the user; the headline weakens from
  "before you typed a word" to "with your first word" (the itemization is
  identical, since the first turn's context is the same payload).
- Buys: zero unasked token spend, no prompt-vs-trust-dialog ordering risk, one
  less new behavior (drops new items 2 and 3; keeps 1, 4, 5).
- Forecloses nothing: A degrades to B per-run when delivery misbehaves, and B
  upgrades to A by adding the button later.

Worse than A because the brief's step 5 is explicit that the reveal lands
before the user types, and because "the product earns the money" should not be
contingent on the user thinking of something to say. B is the fallback shape,
not the target.

### Rejected: CLI-first reveal

`transport-matters claude` already captures interactively on the detached path
(`run_captured_run_on_local_tty`) and the inspector `WaitingScreen` is a ready
zero state, so a terminal-first journey is nearly free. Rejected as first
contact: the desktop lands on `/canvas` while this lands on `/`, splitting
first contact across two origins with no navigation between them (the `goto`
command has zero producers), and the $199 user was promised no thinking, not a
terminal. It remains the developer path it already is.

---

One number for the orchestrator: proposals=2 (plus one named rejection).
Biggest gap in one clause: every component of the journey exists, and no code
puts any of it in front of a first-time user.
