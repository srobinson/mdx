# Scout S3: the human surface

Read-only, main @ `e38bfa2e` (S1 merged `ebb03542`, S2 merged `42a2196d`).
Citations file + symbol. Headline: **the data plane for S3 is already fully
client-resident — the workspace activity SSE delivers every run's needs_you
(including hidden runs) into `runVitalsStore`, and S2's enablement REST is
exactly the settings-list payload — so S3 is almost pure UI, and its one hard
call is the SHAPE of the global surface (toast vs overview) in a codebase
with a deliberate anti-toast precedent.**

## 1. What already exists

- **Per-pane badge (shipped in S1)**: `www/packages/canvas/src/workbench/
  chrome/RunVitalsStrip.tsx` renders "Login needed" / "Usage limit" from
  `useRunVitalsStore((s) => s.byRunId[runId])`, mounted through the
  `PaneChrome.tsx` strip slot on captured-run panes. That is the badge the
  user saw in the 429 report.
- **The feed is workspace-wide, not pane-wide**:
  `infrastructure/stream/useWorkspaceActivityStream.ts` subscribes once per
  workspace to SSE `/v1/workspaces/{id}/activity/stream`
  (`@tm/core transport.ts :: workspaceActivityStreamUrl`, served by the
  gateway's `packages/activity/src/server/activityRouter.ts` through
  `api/v1/run_proxy.py`), snapshot-on-connect then deltas, and
  `SessionCanvasRoute.tsx` folds every frame into
  `model/runVitalsStore.ts :: byRunId` (an `ActivityWireRun` per run,
  `needs_you` payload included) plus `rollup`
  (`ActivityWorkspaceRollup.status_counts` — the needs-you counts already
  arrive precomputed).
- **No overview UI exists**: nothing renders `rollup` or iterates
  `byRunId` beyond the per-pane strip. `workbench/dock/PaneDock.tsx` is a
  count-badged chip listing minimized panes — no vitals, no needs-you.
- **A hidden pane surfaces NOTHING today**: minimized runs keep streaming
  into `byRunId` (the store is fed by the workspace stream, not by pane
  mount), but no component reads a non-visible run's entry. Runs with no
  pane at all (director-launched) likewise sit silently in the store. That
  silent-data-present gap is S3's core job — and it means S3a needs zero
  new backend: the signal is already in the browser.
- **Snapshot-on-connect covers replay**: a standing provider condition is a
  sticky durable row the activity plane re-projects, so every fresh SSE
  snapshot re-delivers it. A present-conditions inbox needs no durable
  inbox store; only dismissed/history semantics would need (client) state.

## 2. Surfacing (toast / inbox)

- **Subscribe**: the existing workspace activity SSE — no new stream, no
  tm_events work. A global needs-you surface is a selector over
  `runVitalsStore` (`tier === "needs_you"` via `activityStatusTier`, reason
  from `needs_you.kind`), covering hidden and pane-less runs for free.
- **Resolve action (confirmed)**: attach by run id —
  `model/capturedRunStore.ts :: adoptRun` binds a known runId to a pane
  (dedup via `capturedRunKeyForRunId`), then the ordinary attach path
  (`useTerminalSession` → WS `/v1/runs/{id}/terminal` →
  `RunManager.attach` scrollback replay). A minimized pane restores from
  the dock by pane key. Both affordances exist; the surface only needs to
  invoke them.
- **The UX flag**: `www` has NO toast/notification/inbox component or store
  anywhere, and pane states carry deliberate "errors render as a dedicated
  pane state … never a generic toast" comments
  (`viewers/placeholder/paneState.tsx`, `viewers/resource/resourceState.ts`).
  A toast is a genuine departure Stuart must bless, not a default.

## 3. Settings menu (S2 enablement)

- **S2 shipped exactly the settings payload**:
  `api/v1/harness_enablement.py :: get_harness_enablement`
  (`GET /v1/harnesses/enablement` → `HarnessEnablementResponse` with
  per-harness `enabled / configured / installed / eligible / path /
  version`, explicit `resolution: "default_path"` and
  `bin_override_evaluated: false`) and `set_harness_enablement`
  (`PUT /v1/harnesses/{harness_id}/enablement`). A settings UI can bind
  TODAY — no S2g dependency.
- **Binding point**: the launcher settings scope —
  `launcher/commandRows.ts :: buildSettingsRows` (⌘, opens
  `openScope("settings")`); `bypassPermissions` / `controlPlaneGrant` rows
  are the toggle precedent. Server state (not localStorage) via the REST
  pair; the row set needs a small fetch-backed store since existing settings
  rows are client-local.
- **S2g overlap, flagged**: S2g plans `harness_inventory()` +
  `/v1/harnesses` + a first-run setup screen with per-harness cards
  (installation, enablement, compatibility, authentication, access,
  target). An S3 settings menu (list + toggle + version) is a strict subset
  built on a surface that already exists; S2g later extends the same rows
  with compatibility/auth/access columns from the inventory. Building the
  simple menu now does not create throwaway work — the S2g screen is a
  different, richer surface (first-run cards), and the toggle plumbing is
  shared either way.

## 4. Probe wiring

- `harnesses/probes/runner.py :: run_authentication_probe` still has zero
  production callers. The settings UI cannot invoke it directly — probes
  run subprocesses server-side — so opportunistic settings-open probing
  needs a small REST endpoint (natural home: beside the enablement read in
  `api/v1/harness_enablement.py`, e.g. an auth-status read that runs the
  cheap local probes for codex/claude with the existing 5s bound, grok only
  on explicit ask). Alternative: defer all auth display to S2g's inventory
  ("nonblocking startup refresh with authentication and access rendered as
  diagnostics" is S2g item 4), keeping S3 settings enablement-only.

## UX decision points for Stuart

1. **THE BIG ONE — shape of the global needs-you surface.** Options:
   (a) transient toast + persistent inbox (the original S3 sketch; real
   departure from the anti-toast precedent); (b) a persistent control-plane
   overview element instead — e.g. a needs-you chip in the top band beside
   the `PaneDock` chip (same "count-badged chip with a menu" pattern,
   zero new UI vocabulary), whose menu lists blocked runs with reasons and
   attach actions; (c) both, with the toast reserved for tier transitions.
   The rollup counts and per-run reasons are already in the store either
   way. Recommendation: (b) first — it reuses the dock's exact interaction
   pattern and honors the no-generic-toast culture; add (c)'s transient
   layer only if the chip proves too quiet.
2. **Placement/home** if (a) or (c): where toasts live, whether the inbox
   is a dock-menu sibling or a launcher scope.
3. **Settings now vs S2g**: build the enablement rows now on the shipped
   REST (recommended; shared plumbing, no throwaway) or wait for S2g's
   inventory screen.
4. **Auth status in settings**: add the small probe endpoint now
   (settings-open opportunistic display) or leave auth display entirely to
   S2g diagnostics. Leaning defer: it keeps S3b enablement-pure and avoids
   pre-empting S2g's inventory shape — but it is a product call.

## Proposed slice breakdown

Two independent, parallel slices:

- **S3a — needs-you surfacing** (www-only): global selector over
  `runVitalsStore`, the chosen surface from decision 1, attach/restore
  actions via `adoptRun` + dock restore. No backend work. Test shape:
  hidden-run condition appears on the surface; attach resolves it;
  dismissed state (if any) is client-local.
- **S3b — settings menu** (www + trivial API glue): launcher settings rows
  backed by `GET/PUT /v1/harnesses/enablement`; disabled harness shows why
  (`installed`/`eligible` fields); optional probe endpoint per decision 4.
  Extended later by S2g, not replaced.

One-line reply headline: the single biggest call is decision 1 — toast+inbox
versus a persistent needs-you chip in the dock's pattern; everything else is
plumbing that already exists.
