# Issue #524: challenge to the digest authorization shape

Companion to `tm-issue-524-cdp-attach-findings.md`. Same SHA, `b5735fabca0482f6f932882f5576b76130a9d78b`.
Reviewer: `transport-matters:general:1:4.2`. Date: 2026-09-01. No edits made.

## Verdict

The instincts are right and the mechanism is wrong. Keeping the raw bearer off the wire is correct.
Making TM own the upgrade is correct, and my transport findings depend on it. Accepting the SHA256
grant digest as the thing that proves authorization is the part to drop, because it converts a
stored lookup key into a live credential.

Recommendation: have the front mint its own short lived attach token, issued on the path that
already calls `require_director`. Reasoning below, then the alternative in full.

## Premise correction: the digest is not already held by MCP auth

The brief says the URL carries "only the SHA256 grant digest already held by MCP auth". Nothing
above the store ever holds it.

`ControlPlaneGrantStore.resolve` computes `digest_run_bearer(bearer)` as an argument to
`_RESOLVE_GRANT_SQL` and discards it. `ActiveControlPlaneGrantResolver.resolve` passes the bearer
straight through and returns a `ControlPlanePrincipal`. That principal carries `run_id`, `role`,
`workspace_id`, `owner`, `bypass_permissions`, `identity`, `space_id`, `worktree_id`, `canvas_id`,
and no credential of any kind. `ControlPlaneService.whoami` and the browsing fronts receive only the
principal; the bearer is never in scope at the service layer.

So emitting a digest bearing URL needs one of two changes, and both are worse than the problem
they solve:

- Widen `ControlPlanePrincipal` with the digest. Every code path that handles a principal then
  handles a credential. The principal is currently never serialized anywhere, which is a property
  worth keeping rather than one to start defending.
- Thread the raw bearer down to the response composition site. That puts the credential in more
  places, which is the opposite of the brief's goal.

## Q1: can the grant store resolve by digest without duplicating auth logic

Yes, cleanly, and that is the trap rather than the reassurance.

`_RESOLVE_GRANT_SQL` already reads `WHERE token_digest = %(token_digest)s`. The refactor is to
split `resolve` into `resolve_digest(digest)` holding the query and a one line
`resolve(bearer) -> resolve_digest(digest_run_bearer(bearer))`. No duplicated logic, no second
query, no second policy. The mechanism is genuinely easy.

Ease of implementation is not evidence of soundness here. The reason the refactor is trivial is
precisely the reason the design is unsafe: the digest is already the lookup key for the credential,
so treating it as the credential requires changing nothing. The database is doing exactly the same
comparison either way, and the only thing that changed is who is allowed to know the input.

## Q2: can REST and MCP derive the digest cleanly

Not without the widening described above, because neither holds the bearer at the point where the
response is built. Two further mechanical problems if it went ahead:

- `devtools_url` is composed in two places. The Gateway builds it in
  `packages/browsing/src/projections/browserPaneView.ts::devtoolsUrlFor` and
  `canvasPresentationView`; Python rewraps in
  `api/src/transport_matters/api/v1/controlplane_gateway_browsing.py::devtools_attach`, and
  `browser_panes` carries the Gateway's `devtools_url` through `BrowserPaneListView`. Under the
  "Gateway publishes bare, Python appends" split, the token bearing rewrite lands in both Python
  paths, and any consumer that reads the Gateway directly receives a URL that silently does not
  work. A URL that is valid from one front and inert from another is a bug waiting to be filed
  against the wrong component.
- `CdpAttachWire` in the attached case is `{kind, port, target_id}` with nowhere to carry a token.
  If the credential rides `devtools_url` alone, then `presentation.attach` stops being sufficient to
  attach while still being named attach. Either the wire gains the credential or the field gets an
  honest name. `browserPaneProof.ts` reads `attach.port` and `attach.target_id` and would need the
  URL instead, so the live gate will surface this immediately.

## Q3: the security hole

**The digest becomes bearer equivalent, and `control_plane_grant.token_digest` becomes replayable.**

`digest_run_bearer` is unsalted SHA256 with the docstring "one way lookup digests". The column
exists so that reading the grant table yields nothing usable. Accept the digest as an authenticator
and that guarantee inverts: the stored value becomes sufficient to act as the Director.

Why this matters more here than it would elsewhere:

- Channels are separate Postgres databases on the developer's own machine, reached over the same
  loopback the issue already declares untrusted ("loopback is not a trust boundary on a developer
  machine"). A local process that can reach the CDP front can generally reach Postgres too. The
  shape therefore adds a path that does not exist today: read one column, drive every Director's
  panes. Today that column is inert.
- It applies retroactively. Every existing dump, backup, and replica of that table becomes a
  credential store the moment the front starts accepting digests, with no change to any of them.
- It weakens a property TM currently gets for free, in exchange for a property TM can obtain
  another way. That trade is available at a better price.

There is no preimage risk. `mint_run_bearer` is `secrets.token_urlsafe(32)`, so the digest cannot be
reversed. The exposure is that reversing it stops being necessary.

## Q3: the lifecycle race

**Validating at HTTP discovery and WS upgrade does not deliver "a run without a Director grant
cannot reach it".**

Grant liveness today is checked per request, twice over. `ActiveControlPlaneGrantResolver` resolves
the row and then re-checks that the owning capture is live on every call. Revocation is tied to run
teardown: `api/src/transport_matters/captured/run.py` registers
`resource_stack.callback(persistence.revoke, grant.run_id)`, so the row is deleted when the run's
resource stack unwinds.

A CDP WebSocket is long lived by design. Under the proposed shape it is authorized once, at upgrade.
After that the run can end, the grant row can be deleted, and the capture can go away, while the
socket keeps full CDP control of every pane. The property holds at connect time and decays silently
from then on.

Concretely: an agent that connects while its run is live retains the ability to evaluate arbitrary
JavaScript in every pane for as long as it declines to disconnect. The stated criterion says a run
without a Director grant cannot reach it. This shape says a run that once had one never loses it.

Fixing this inside the digest shape means periodic re-validation plus forced socket closure on
revocation, which is most of the machinery of the alternative below, with the replay exposure still
attached.

## Canvas scoping is undefined for the caller that most needs it

`ControlPlanePrincipal.canvas_id` is `CanvasId | None`, and `ControlPlaneService._devtools` already
answers `no_canvas` when it is null. "An active Director grant scoped to the same canvas" therefore
has no meaning for a headless director with no canvas bound, which `docs/plans/BROWSER-PANE-PLAN.md`
records as an open question under "Open questions and risks". Decide it deliberately rather than
letting it fall out of a null check. Failing closed is defensible and should be stated; falling open
would make canvas scoping decorative.

## The API origin premise, with one correction

Sound. `desktop/src/backendHealth.ts::backendHealthUrl` is `http://127.0.0.1:{webPort}/health` and
`desktop/src/rendererUrl.ts::rendererUrlForPort` builds `/canvas` on that same origin, so the API and
the renderer route share an origin and the front can derive one from the other. Take the origin
rather than the route: `new URL(routeUrl).origin`.

One ordering constraint. The route URL belongs to a window, and today `DevtoolsEndpoint` is resolved
at app ready, before any window exists, then handed to `registerBrowserPaneHost`. Deriving the
front's origin from the main window inverts that order and makes the CDP fact depend on a window
having been created. Feed the front the origin from the same env the window resolves it from, so the
front's readiness stays independent of window lifecycle.

## Recommended alternative: the front mints its own attach token

Stop deriving a credential from the grant. Issue one.

1. On a Director gated read, Python asks the desktop front to mint an attach token scoped to
   `(canvas_id, run_id)` with a short TTL, and returns `ws://127.0.0.1:<front>/cdp?t=<token>`.
2. The front holds tokens in memory only. Nothing is persisted, so there is no table to replay and
   no backup that becomes a credential store.
3. The front validates on upgrade, and because it holds both the token and the socket, it closes
   live connections when the token is revoked or expires. Run teardown closes the socket rather than
   hoping a later check notices.
4. The grant check happens once, in Python, on the path that already calls `require_director`. No
   second authorization system, and no auth decision reachable by two different routes.

What this costs that the digest shape avoids: a channel from Python to the front for minting. That
is a real cost and it is the honest objection to this alternative. It is smaller than the cost of
making a stored digest into a credential, and it is the same channel the front will need anyway for
revocation, which the digest shape also requires and has not yet budgeted.

Worth noting: the token can ride the URL safely because `agent-browser connect` forwards a `ws://`
query string, which I verified live. That property was the reason the digest looked attractive, and
it serves a minted token equally well.

## What to gate on

- A test that a connection stays open across run teardown must fail before the fix, then pass. This
  is the property most likely to be quietly lost, because it looks correct at connect time. The
  observable is the socket, not the validation call.
- A test that `control_plane_grant.token_digest`, read straight from Postgres, does not authorize
  the front. This is the regression that the digest shape would have made unwriteable.
- `just browser-pane-proof` extended to assert `tab list` never names the app renderer, and that a
  connect without a valid token is refused.
