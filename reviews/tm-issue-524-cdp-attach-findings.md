# Issue #524 CDP attach: independent architecture findings

Repo: transport-matters. Validated against `main` at `b5735fabca0482f6f932882f5576b76130a9d78b`, working tree clean.
Author: `transport-matters:general:1:4.2`. Date: 2026-08-31.

## Validation of main

`git rev-parse HEAD` matches the requested SHA. `just test-js` (the full JS gate) exits 0.
Every claim below about behaviour is either read from source at that SHA or produced by a live
experiment described in Evidence.

## The one fact that changes the design

**The per pane CDP target id does not need `--remote-debugging-port`.**

`BrowserPaneHost::resolveTargetId` reads the target id through `view.webContents.debugger`, which
is an in process CDP client. It has no dependency on the remote debugging HTTP server.

Proved by running a minimal Electron app that mirrors `resolveTargetId` exactly, twice:

| launch | `remote-debugging-port` | target id returned |
| --- | --- | --- |
| A | absent | `A72F6D3C1D73A99313A96E99A2D176F0` |
| B | present | `BE8103A2FD27E42F8A57E9C9FCD8FDA2` |

So a packaged build already has, for free and with zero exposure, a full CDP channel to every pane
and to no other web contents. The process wide port buys exactly one thing: a loopback transport
that carries that channel to an external client. The gap is transport, and nothing else.

This is what makes an app owned front cheap rather than speculative. Main is not being asked to
invent access it lacks. It is being asked to publish access it already holds.

## Architecture map

Read path, control plane to wire:

- `desktop/src/devtoolsPort.ts::applyDevtoolsSwitch` is the only parser of `ENV.DEVTOOLS_PORT`.
  Unset appends no switch and returns null. Called from `desktop/src/main.ts` before app ready.
- `desktop/src/devtoolsPort.ts::probeDevtoolsEndpoint` turns that port into a `DevtoolsEndpoint`
  by `GET /json/version`. A null port short circuits to `{kind:"unavailable", reason:"devtools_disabled"}`.
- `desktop/src/app/browserPanes/registerBrowserPaneHost.ts` answers the preload's `devtools` query
  with that endpoint. The renderer declares it when it registers as a presenter.
- `packages/browsing/src/domain/presenters.ts::cdpAttachFor` pairs the presenter's port with the
  observation's `target_id`, and only while the presenter that produced the id is registered,
  composited and live. `canvasDevtoolsFor` picks the canvas wide port.
- `packages/browsing/src/projections/browserPaneView.ts::browserPaneView` and `canvasPresentationView`
  serialize both onto the wire.
- `api/src/transport_matters/api/v1/controlplane_gateway_browsing.py::devtools_attach` feeds
  `whoami.devtools_url` via `controlplane/service.py`.

Target id origin: `desktop/src/app/browserPanes/BrowserPaneHost.ts::resolveTargetId`, a momentary
`webContents.debugger` attach at view creation, detached in a `finally`.

Spawners that set the env key, in the whole repo: `scripts/local-desktop-dev-mode.sh` (default
18790) and `desktop/src/browserPaneProofSupport.ts::buildBrowserPaneProofEnv`. Nothing else.
`api/src/transport_matters/env_keys.py::DEVTOOLS_PORT` only mirrors the name; no Python spawner
sets it. The issue's account of the launch path inconsistency is accurate.

## Compatibility constraints for `agent-browser connect`

Captured by putting a logging CDP proxy between `agent-browser` and a real Electron endpoint and
recording every frame. This is the exact contract a replacement front must satisfy.

**HTTP.** One request only: `GET /json/version`. The response must carry `webSocketDebuggerUrl`.
`/json/list` is never called; the tab list comes from CDP, not HTTP.

**WebSocket, browser level session.** In order observed:

```
Target.setDiscoverTargets   -> server emits Target.targetCreated per target
Target.getTargets
Target.attachToTarget       -> Target.attachedToTarget carrying a sessionId
Browser.getVersion
```

**WebSocket, per target sessions.** Everything after attach is `sessionId` routed and needs no
interpretation by a front: `Runtime.evaluate`, `Runtime.enable`, `Runtime.callFunctionOn`,
`Page.enable`, `Network.enable`, `Target.setAutoAttach`, `Runtime.runIfWaitingForDebugger`.

Three consequences:

1. A front that filters `Target.targetCreated`, `Target.getTargets` and `Target.attachToTarget`
   to pane targets controls everything. A session cannot exist for a target the front refused to
   attach, so no per session filtering is needed.
2. `agent-browser connect` accepts a full `ws://` URL and forwards its query string. Verified: a
   connect to `ws://127.0.0.1:PORT/devtools/browser/<id>?tm_token=director-bearer-xyz` succeeded
   and listed tabs. A Director bearer can therefore ride the connect URL and be checked at the
   WebSocket upgrade, before any CDP frame is proxied. This answers the issue's open compatibility
   question: no change to `agent-browser` is required, for either the port form or the URL form.
3. `Browser.getVersion` must be answered. A front that proxies only `Target.*` will hang.

**`webContents.debugger` and an external client coexist.** Main held a persistent
`debugger.attach("1.3")` on a pane target while `agent-browser` attached over the port to that same
target and read its DOM successfully. Chromium's flattened multi session support makes both live at
once. This settles the open question recorded in `docs/plans/BROWSER-PANE-PLAN.md` under "Open
questions and risks" ("Does `webContents.debugger.attach("1.3")` at creation conflict with an
`agent-browser` client already attached over the port?"). The answer is no, in both directions.

## Security findings

**1. The app renderer is not merely exposed, it is the default tab.** With the dev script's port
set, `agent-browser connect <port>` followed by `tab list` returns the app renderer first and marks
it `active: true`. A `get text h1` with no tab selection read the renderer's content. So today the
documented developer workflow lands an agent on the Transport Matters renderer unless the operator
knows to switch tabs. The plan's accepted tradeoff understates this: it says the renderer is
"exposed as a CDP target too", and in practice it is the one you get by default.

**2. The Director grant does not gate CDP access, and cannot.** Two separate gaps:

- `controlplane_gateway_browsing.py::list_browser_panes_for` is documented "the observe verb: any
  grant may list" and calls no `require_director`. It returns `presentation.attach`, which carries
  the port and the target id. `devtools_attach`, which feeds `whoami.devtools_url`, takes no
  principal at all. So any grant learns the endpoint.
- More fundamentally, the endpoint is a raw unauthenticated Chromium port. Knowing it is sufficient
  to use it. No grant check anywhere in TM can affect that.

`require_director` today gates the mutating verbs (`browser_open`, `browser_navigate`,
`browser_history`, `browser_reload`, `browser_close`, `remove_browser_history_entry`) and nothing
about attachment. The issue's verification criterion "a run without a Director grant cannot reach
it" is therefore not a regression test on existing behaviour. It is a new property, and it is only
achievable if TM owns the transport. That is an argument for the app owned front, not a detail of it.

## Corrections to the issue text

- **`desktop/scripts/browser-pane-attach.sh` does not exist.** It appears in the plan's module map
  and slice list but was never landed; the live gate that replaced it is `just browser-pane-proof`,
  driving `desktop/src/browserPaneProof.ts`. Verification criterion 4 should name that recipe.
  Note that the proof allocates its own devtools port through `freeLoopbackPort` and injects the
  env key, so it will keep passing unchanged after a redesign and proves nothing about the default.
  Criterion 4's intent needs restating as: the proof passes without `buildBrowserPaneProofEnv`
  setting `ENV.DEVTOOLS_PORT`.
- The issue's framing that "enabling the current mechanism by default would be wrong" is correct and
  is now demonstrated rather than argued. See Security finding 1.

## Recommended implementation boundary

**Recommendation: app owned CDP front, backed by in process `webContents.debugger`, with no
`--remote-debugging-port` at all.**

The front is a loopback HTTP and WebSocket server owned by main, serving:

- `GET /json/version`, authenticated, returning a `webSocketDebuggerUrl` on the same server.
- A browser level WebSocket that TM implements: `Browser.getVersion`, `Target.setDiscoverTargets`,
  `Target.getTargets`, `Target.attachToTarget`, and the `Target.targetCreated`,
  `Target.attachedToTarget`, `Target.targetInfoChanged`, `Target.detachedFromTarget` events. Its
  target set is exactly the panes `BrowserPaneHost` holds.
- Per session passthrough into that pane's `webContents.debugger`, routed by a TM minted sessionId.

Why this shape rather than the alternatives:

- It excludes the app renderer by construction, not by filtering. There is no process wide port, and
  main attaches debuggers only to pane views. The renderer is unreachable rather than hidden, which
  is the difference between a policy and a boundary.
- It is the only option that can honour the Director grant, because TM owns the upgrade handshake.
  The bearer rides the connect URL, which `agent-browser` already forwards.
- It preserves `cdpAttachFor` untouched. The presenter identity check stays exactly as written; only
  the meaning of `DevtoolsEndpoint.port` changes from "Chromium's port" to "TM's front's port".
  Requirement 3 of the issue is satisfied by not touching the code that implements it.
- The capability it depends on is proved, not assumed: target ids without a port, and coexistence of
  in process and external sessions.

Rejected, with reasons:

- **Ephemeral supervised port plus a filtering proxy.** Cheaper, and it is what the issue lists
  second. It leaves the renderer live on a loopback port whose only protection is that the number is
  not published. On a developer machine any local process can scan 64k ports. That is defence in
  depth, not a trust boundary, and the issue itself says loopback is not a trust boundary. It also
  cannot authenticate, since the real Chromium port stays open beside the proxy.
- **Panes in a separate Electron process with its own port.** Would use the OS process boundary as
  the filter, which is more elegant than any shim. It does not work: a `WebContentsView` must live
  in the process of the `BrowserWindow` it composites into, so composited panes cannot move out.
- **First class opt in setting with UI.** Does not address the exposure. It documents a hazard
  rather than removing one, and the issue's own framing is that the mechanism must change first.

Scope estimate for the front: roughly 300 to 400 lines in one new desktop module, plus the
`DevtoolsEndpoint` production path moving from `probeDevtoolsEndpoint` to the front's own readiness.
`devtoolsPort.ts` is then deleted whole, along with `ENV.DEVTOOLS_PORT` and its `env_keys.py` mirror.
Deleting the old path in the same wave matters here: leaving the env var as an escape hatch
reintroduces the exposure the work exists to remove.

Sequencing that keeps each step verifiable:

1. Land the front behind the existing env key, serving pane targets only. Prove it with
   `just browser-pane-proof` unchanged except that the port it sets is now TM's.
2. Add bearer authentication on the upgrade, and extend the proof to assert a connect without the
   Director bearer is refused and that `tab list` never names the app renderer.
3. Remove `--remote-debugging-port`, `devtoolsPort.ts`, and the env key. Make the front's port
   ephemeral and app allocated, as the gateway and web ports already are. The proof stops setting
   any port. This is the step that closes the launch path inconsistency in item 4, because there is
   then only one posture and no spawner can diverge from it.

Two smaller items, independent of the above and worth landing either way:

- `CdpUnavailableReason` in `packages/contract/src/browsing/index.ts` should lose `devtools_disabled`
  once the front is the only path, or gain a remedy bearing member. Both `CDP_UNAVAILABLE_REASONS`
  and `CANVAS_DEVTOOLS_UNAVAILABLE_REASONS`, and their `browsing_contracts.py` mirrors, change
  together.
- `list_browser_panes_for` and `devtools_attach` publish the endpoint to any grant. Whatever the
  transport becomes, decide deliberately whether the attach fact is observe scope or director scope.
  It is currently observe scope by omission rather than by decision.

## Evidence

All experiments ran against `desktop/node_modules/.bin/electron` (Electron 43.0.0) and the
`agent-browser` on PATH, in a scratch directory, with every process and session torn down after.

1. Target id without a port: minimal app mirroring `resolveTargetId`, run with and without the
   switch. Both returned a target id.
2. Renderer exposure: stand in app with one `BrowserWindow` titled `TM-APP-RENDERER` and one
   `WebContentsView` titled `TM-PANE`. `/json/list` listed both as type `page`.
   `agent-browser tab list --json` returned the renderer first with `active: true`, and
   `agent-browser get text h1` with no tab selected read the renderer's content.
3. Protocol trace: a logging proxy recorded the HTTP path and every CDP method in both directions
   for a `connect` plus `tab list` plus `snapshot`.
4. Coexistence: the stand in held `debugger.attach("1.3")` on the pane target for its whole life
   (`mainHoldsAttach: true`); `agent-browser` then attached to that target and read its DOM.
5. Token forwarding: `agent-browser connect "<browser ws url>?tm_token=director-bearer-xyz"`
   connected and listed tabs, proving the query string reaches the server.

Not verified, and worth proving in slice 1: `Target.setAutoAttach` fidelity through a TM minted
session for out of process iframes and workers. Every other method in the trace is a direct
passthrough.
