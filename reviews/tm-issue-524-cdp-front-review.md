# Issue #524 pane CDP front: review of PR #564

Reviewed SHA `97cd1f8beae6ddfe00c48671606972b5fc2f18b6`. New head `ad39e38ae3246898c7d59f22f977d0c91c730de2`.
Reviewer: `transport-matters:general:1:4.2`. Date: 2026-09-01.
Repo: transport-matters, branch `fix/524-pane-cdp-endpoint`, shared checkout.

The architecture holds. Electron main owning an in process, pane only CDP front is the right
answer to #524, the process wide switch is gone completely, and the live proof drives a real
Electron shell through a real agent-browser. What follows is what the review changed and what it
did not.

## Fixed on this branch

### 1. Three peer behaviours ended the whole app

Main runs no supervisor. An uncaught exception or an unhandled rejection in the main process ends
Transport Matters, taking every canvas, pane, and harness window with it. The front raised one in
three places, all verified by running the code at `97cd1f8b`:

| trigger | what escaped | reachable by |
| --- | --- | --- |
| peer resets while `authorizeUpgrade` awaits the grant | `Error: read ECONNRESET`, uncaught exception | agent-browser exiting during the round trip |
| peer sends a frame ws rejects | `RangeError: Invalid WebSocket frame: RSV1 must be clear`, uncaught exception | any attached client with a protocol bug |
| peer stops sending an attach body | `Error: aborted`, unhandled rejection | a client or an issuer timeout mid request |

The first needs no misbehaviour. Node removes its own `error` listener from the socket before it
emits `upgrade`, so from that moment the socket is the front's to guard, and the authorization
round trip holds it for as long as the control plane takes to answer. Ctrl-C in agent-browser at
that instant is enough.

Cause in each case is the same shape: an I/O primitive with no error handling. `ws` emits `error`
on the accepted socket for any frame the peer gets wrong, and an `EventEmitter` with no `error`
listener throws. `void handleHttpRequest(...)` had no `catch`, and `readJsonBody`'s `for await`
rejects when the peer dies mid body.

Fix: an `error` listener on the raw upgrade socket and on the accepted WebSocket, a `catch` on the
HTTP handler, and the body read treats an aborted stream as an unreadable body.

### 2. The single use capability was not single use

`authorizeUpgrade` read the token, awaited the grant check, and deleted the token afterwards. Two
upgrades racing on one token both read it before either deleted it, so both passed. Fixed by
spending the capability before the first await.

### 3. `unregister` touched a debugger whose contents were gone

`register` guards `contents.isDestroyed()`; `unregister` did not, and `BrowserPaneHost` calls it
from the `destroyed` event, where every Electron `webContents` member throws. The call site wrapped
it in `void promise.then(...)` with no `catch`, so the throw would have become an unhandled
rejection, which is fault class 1 again. Guarded, and the call site now catches.

### 4. Target teardown and lifecycle

`Target.detachedFromTarget` now reaches sessions attached to a departing target, and
`Target.targetDestroyed` is limited to clients that enabled discovery, which is what Chrome does.
`dispose` closes connections rather than waiting out an idle keep alive during quit.
`POLICY_VIOLATION` records why it is spelled locally instead of imported from `@tm/common`: a value
import of a devDependency fails `scripts/assert-packaged-imports.ts`.

### 5. Tests

`browserPaneDevtoolsFront.test.ts` had one test for a 609 line security surface, and `options.now`
was injectable with nothing using it, so capability lifetime and replay were unproven. Seven tests
added. Six fail against `97cd1f8b` and pass at `ad39e38a`; the seventh (expiry) passed already and
was uncovered. The fault tests watch `uncaughtException` and `unhandledRejection` on the process,
because surviving is the observable, not a return value.

## Not changed: three questions for the owner

### A. Python forwards the caller's raw bearer to an endpoint a presenter declares

`HttpDevtoolsAccessIssuer.issue` POSTs `Authorization: Bearer <the caller's director bearer>` to
`view.devtools_url`. That URL comes from `canvasDevtoolsFor`, which returns the first composited
presenter with a live url. Presenter registration is the Gateway's SSE stream, which listens on
127.0.0.1 with no authentication, so any local process can register as a composited presenter for
any canvas and declare `devtools_url=http://127.0.0.1:<its own port>`. The next Director
`browser_panes` or `whoami` hands it a live control plane credential.

Note that `canvasDevtoolsFor` deliberately does not use the presenter that observed the pane, so
the invariant `cdpAttachFor` documents ("a port from one presenter is never paired with a target id
from another") does not cover the endpoint the bearer goes to.

The plan doc already rejects "Publishing the Director bearer in a URL leaks a durable credential
through process arguments, logs, and browser tooling." This is the same concern through a different
channel: the bearer now travels to an address chosen by unauthenticated input.

Before the PR the declaration could misdirect a Director's automation. It could not take a
credential. That part is new.

Proposed direction, for agreement before anyone builds it: Python should not send the bearer.
Mint a short lived opaque grant nonce server side, hand that to the front, and have the front
present the nonce back to `/v1/controlplane/devtools-authorize`. A rogue endpoint then receives a
value scoped to one canvas and one socket that is useless anywhere else, and the per command
recheck keeps working unchanged.

### B. `devtools-authorize` reads `canvas_id` and does not verify it

`_ = body.canvas_id` discarded the field; only the Director role was checked. This is consistent
with the rest of browsing, where `resolve_canvas_id` lets a Director name any canvas, so it is not
an escalation past `browser_open`. It does mean "targets and commands are Canvas scoped" is a
routing property of the front, not an authorization boundary.

Left as is, deliberately: binding it to `principal.canvas_id` would refuse an attach to a canvas
`browser_open` already serves, and that is an authorization semantics change, not a review fix. The
route now carries a docstring saying so and a test records the cross canvas answer, so the next
reader sees a decision rather than an oversight. Say the word if the capability should be narrower
than the verbs, and it is a two line change plus the test.

### C. Every CDP command costs a loopback HTTP round trip and a Postgres query

`authorize` fetches `/v1/controlplane/devtools-authorize`, which runs
`require_control_plane_principal`, whose resolver is documented as running "for every request,
without caching" and executes `_RESOLVE_GRANT_SQL` against Postgres. The front serializes commands
on `client.queue`, so a snapshot pays that cost once per command, in sequence.

The plan's rejected alternatives weigh "before every CDP command" against "only at WebSocket
upgrade". A third option was not weighed: bounded freshness, for example a grant cached for a few
hundred milliseconds per socket. Revocation would then close the socket within that bound instead
of instantly. Worth a decision rather than a silent default, because the current default puts a
database query on every `Runtime.evaluate`.

## Gate evidence at `ad39e38a`

- `just check`: pass. ruff format, ruff check, mypy over 871 files, every JS typecheck.
- `just test`: pass. 4,459 Python tests; `just test-js` summaries 204, 1557, 33, 31, 293, 67, 236, 71, 24.
- `TRANSPORT_MATTERS_DATABASE_URL=postgresql://tm:tm@localhost:55432/transport_matters just browser-pane-proof`:
  pass end to end. Real Electron shell, agent-browser 0.35.2, target `5BE1B2ACC9B1C74A70F0144E89657F06`,
  snapshot, navigate, history back, reload replacing the document, close, Space deleted.
- Local HEAD, `origin/fix/524-pane-cdp-endpoint`, and PR #564 head all `ad39e38a`.
- GitHub CI still does not start; the check annotation names an account payment or spending limit.

## Checked and found sound

Bearer never appears in the capability URL. Capability TTL is enforced on both the upgrade and
`/json/version`. The front's target registry contains registered panes only, so the app renderer is
absent by construction rather than by filtering. `Target.createTarget`, `Target.closeTarget`, and
`Target.createBrowserContext` are refused, which is correct for a pane only front even though
agent-browser can issue them. `_capability_origin` pins the returned url to the origin that issued
it. `loopbackOrigin` in main handles the bracketed IPv6 hostname that `URL` produces, and
`_loopback_origin` handles the unbracketed one `urlsplit` produces. The Vite dev server proxies
`/v1`, so the dev mode route url authorizes correctly. `ws` is correctly a production dependency
while `agent-browser` and `playwright` are devDependencies, and the packaged import guard covers
the distinction.

---

# Addendum: proposed design for finding A

Written 2026-09-01 in reply to the peer's rejection of a transferable nonce. Nothing implemented;
this is the flow to agree on first.

## The peer is right about relay, and right that a trust root is missing

A bare nonce is transferable. A rogue that receives one can find the genuine front by scanning
loopback and probing `/json/version?tm_attach=<nonce>`, which the genuine front answers with its
own `webSocketDebuggerUrl`. Seconds of work. So the nonce alone does not close A.

## Why a launcher-shared per-launch secret cannot be the root

Two facts, both read from source:

1. **There is no common launcher in the hosted path.** `desktopRuntime.ts` shells out to
   `transport-matters` for runtime status, and `backendStartup.ts::liveRuntimeRoute` attaches the
   desktop to a runtime already in state `live`. The user starts the backend from the CLI; Electron
   joins it later. Neither is the other's parent and no ancestor is shared. A secret the launcher
   passes down covers the managed path and the dev script, and silently fails exactly where a user
   is most likely to be.
2. **A secret at rest does not survive this adversary.** The adversary that makes A a blocker is a
   process running as the user with no grant, or a lesser grant, that registers a presenter and
   harvests a Director bearer belonging to another run. Harness processes run unsandboxed as the
   user. Same-user code reads any file under the home and any other process's environment. A shared
   secret is visible to precisely the party it is meant to exclude.

So the smallest design must need no shared secret at all.

## Proposed flow

The move is to stop Python contacting the declared endpoint, and to bind the capability to the
endpoint Python was told about.

**Mint.** A Director calls `browser_panes` or `whoami`. Python resolves the canvas, reads the
declared `devtools_url` origin R from the presenter view, and mints capability C: random, held in
an in-process store (the backend is single process, `__main__.py` and `desktop_cmd.py` pass no
`workers`) against `{run_id, canvas_id, origin R, issued_at, opened}`. Python returns
`ws://R/devtools/browser/tm?tm_attach=C` to the Director. **Python sends nothing to R.**

**Open.** The Director connects. The front reads C from the query and POSTs
`{capability: C, origin: <its own endpointUrl>}` to `/v1/controlplane/devtools-authorize`, with no
`Authorization` header. Python checks the store: C exists, the issue window has not lapsed, the
reported origin equals R, and the run's grant is still a live Director. It answers `{canvas_id}`.
The front scopes the connection to that canvas and refuses a second upgrade on the same C.

**Keep.** Before every CDP command the front revalidates C the same way. The issue window bounds
when a socket may be opened; the live grant bounds how long it may stay open. That is the same pair
of properties the current design has, with the raw bearer removed from both.

## The peer's five questions

1. **Who mints each secret.** Python mints C. The front mints nothing. There is no second secret.
2. **How the genuine front and the verifier receive it.** They do not. Python is the only verifier
   and already holds the store. The front receives C from whoever connects to it and relays it.
   Removing distribution removes the bootstrap problem rather than solving it.
3. **Packaged, hosted, and dev.** Identical, because nothing is shared out of band. This is the
   property a launcher-passed secret cannot have, per the hosted path above.
4. **What a rogue loopback presenter observes.** Nothing from Python; Python never contacts the
   declared endpoint again. It sees C only if a Director's client connects to the URL it declared.
5. **Why it cannot redeem or relay.** Redeem: C is not a credential. Presenting it to Python
   returns a canvas id and a yes or no, and grants nothing; the rogue already had C. Relay: C is
   bound to R. The genuine front reports its own origin G when it validates, truthfully, because G
   is computed from the port it is actually listening on. Python refuses G against a capability
   issued for R, so a relayed C opens nothing on the real panes.

## What this also fixes, and what it costs

The canvas becomes server asserted. The front learns the canvas from Python's answer instead of
taking it from its caller, which closes finding B on the capability path without touching the
Director cross canvas semantics the owner accepted.

Net code: deletion in the desktop. `POST /tm/devtools/attach`, the front's token store, its TTL and
purge, and `HttpDevtoolsAccessIssuer` with its httpx client and `_capability_origin` check all go.
One network hop per `browser_panes` and `whoami` goes with them. Python gains a small capability
store. Revocation is unchanged, and the front's registry still contains panes only, so the app
renderer stays absent by construction.

## Residual risk, stated plainly

A rogue presenter can still misdirect a Director's automation to a fake front, if it wins
`canvasDevtoolsFor` by registering first. That is a spoof of the pane surface. It exists today,
before and after this change, it leaks no credential, and it exposes no renderer. Closing it means
authenticating presenter registration, which is a larger separate piece and which, against a
same-user adversary, has the same secret-at-rest floor described above. Worth its own issue, not
worth blocking A on.

---

# Addendum 2: finding A implemented

Head `e3e61d6f1f710601d156fef58b4a73790fc9d5e6`, agreed direction implemented on the branch.

## The flow that shipped

Python mints a capability against the run, the resolved Canvas and the normalized declared origin,
returns `ws://<declared origin>/devtools/browser/tm?tm_attach=...` to the Director, and contacts
nothing. The front presents the capability back to `POST /v1/controlplane/devtools-authorize`,
naming the origin it is itself listening on and carrying no credential. Python spends the one
opening atomically, refuses any other origin, re-reads the Director grant by the run the capability
names, and answers with the Canvas. The front scopes the connection to that answer and asks again
before every command.

## The requested invariants, and where each is proved

| invariant | code | test |
| --- | --- | --- |
| mint only for a live Director, recording run, canvas, normalized origin, expiry, unopened | `devtools_access.py::issue_browser_pane_access`, `_mint`, `DevtoolsCapabilityStore.mint` | `test_devtools_access.py`, `test_browsing_skins.py::test_devtools_authorization_refuses_a_grant_that_is_not_a_director` |
| unopened to opened is atomic | `DevtoolsCapabilityStore.open`, no await between the read and the write | `test_a_capability_opens_once_so_racing_upgrades_cannot_both_win`, desktop `opens once when two upgrades race for one capability` |
| Canvas comes only from the server | `browserPaneDevtoolsFront.ts::authorizeUpgrade` takes `canvasId` from the answer | desktop `scopes a connection to the canvas the control plane names, never its caller` |
| origin mismatch refused against the front's own endpoint | front sends `endpointUrl`; `browsing_routes.py::devtools_authorize` normalizes and compares | `test_a_capability_minted_for_a_rogue_origin_cannot_open_the_genuine_front`, desktop `refuses a capability relayed from a rogue origin` |
| uncached Director check before every command, socket closed on failure | `handleCdpMessage` stage `command`, `resolve_devtools_principal` | desktop revocation close (1008) and the per-command ask count; `revoked` 401 in the route test |
| bounded and purged, never persisted, no bearer anywhere | `MAX_CAPABILITIES`, `_purge`, in-process dict | `test_minting_purges_lapsed_capabilities_and_refuses_past_the_cap`, `test_an_idle_socket_ages_out_and_a_busy_one_does_not` |
| ws url compatible with agent-browser 0.35.2 | fixed `/devtools/browser/tm` path, query preserved | the live proof |
| a rogue origin observes and redeems nothing usable | Python contacts no declared endpoint | the skin test mints against `127.0.0.1:9333` with nothing listening there and still succeeds |

The bearer is gone from the path entirely, which took the MCP bearer ContextVar and the request
bearer reader with it. The desktop is a net deletion: the front's attach endpoint, token store, TTL
and purge, and its whole HTTP surface, plus `HttpDevtoolsAccessIssuer`, its httpx client, and one
network hop per `browser_panes` and `whoami`.

Finding B is closed on this path as a side effect: the front no longer takes a Canvas from its
caller. The Director cross-canvas verb semantics the owner accepted are untouched.

## Gate evidence at `e3e61d6f`

- `just check`: pass.
- `just test`: pass. 4,468 Python tests; JS summaries 204, 1557, 33, 31, 293, 67, 236, 71, 24.
- `just browser-pane-proof`: pass end to end at this exact head, agent-browser 0.35.2, target
  `18C5719B657E4FFC71762FC12672DAC5`.
- Local HEAD, origin, and PR #564 head all `e3e61d6f`.
