# PR #357 user facing review

Reviewed base `84d2c66d7bd048e36cadf6e2ac91cc5a48d9f16d` through exact head
`4ab2612bef92289cfd6e8f8987427387b78d9649` in a detached worktree.

## Findings

### High: a recovered session store can leave the user permanently locked out

Locations: `api/src/transport_matters/main.py:_start_session_store`,
`api/src/transport_matters/main.py:lifespan`,
`api/src/transport_matters/captured/readiness.py:_read_enablement`, and
`www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`.

The backend establishes `app.state.session_pool` once during lifespan startup. A
transient connection or listener failure leaves that process state as `None`; no
request path recreates it. After Postgres recovers, Retry can make
`check_session_store()` green, but the readiness route still receives the same
`None` pool. `_read_enablement` therefore returns
`harness_enablement_unavailable`, overall readiness stays red, and
`SessionCanvasRoute` continues withholding the workbench.

The UI tells the operator to fix the store and retry, but this state requires a
backend restart. No restart control is present. This is the permanent locked door
the review brief asked to find.

A configuration repair has a second process lifetime lock. The preflight obtains
the database URL through `api/src/transport_matters/config.py:get_settings`, which
is cached with `lru_cache`. Retry refetches readiness but does not clear backend
settings. Adding or correcting the configured URL therefore also requires a
backend restart, exactly as the displayed setup guidance eventually admits.

The frontend retry test replaces the second response with an artificial green
payload. No test covers the production sequence of lifespan pool failure, store
recovery, and Retry.

### High: launch prerequisites are enforced at the product visibility boundary

Location: `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`.

Every initial loading state, readiness transport error, malformed or absent
payload, and failed infrastructure check replaces `CanvasWorkbench` with the
startup gate. The collapse is the predicate
`launchReadiness.data?.ready === true`: it cannot distinguish a reported red
check from an unknown result. The removed subtree owns saved panes, transcript
panes, captured run panes, Activity, and the Command Center. Missing Node,
mitmdump, or the gateway prevents new captured runs, but it does not invalidate
those existing reads or views.

The failing `frontend e2e` job demonstrates this reachable unknown state. Its Vite
shell has no backend, so `GET /v1/launch-readiness` fails and all 16 specs wait for
an absent `.canvas-route-shell` even though no infrastructure check reported red.
The production query inherits one automatic retry. If the endpoint recovers
during that attempt the gate clears. After the attempt fails, infinite staleness
plus disabled mount, reconnect, and focus refetches leave the gate closed until
the user presses Retry. If the endpoint remains unavailable, Retry can never open
the product.

`www/packages/canvas/src/launcher/templateRows.ts:launchBlockedReason` already
enforces the appropriate fail closed boundary by disabling native and specialist
spawn actions for global and matching harness failures. A nonblocking alert or
remediation pane can preserve visibility while that action seam remains closed.
The current route gate conflicts with `LESSONS.md`, which requires readiness to
fail open for product visibility and fail closed at the action it qualifies.

The route tests accurately assert that loading, a 503, and a red payload hide the
workbench. They prove the user visible behavior, but that behavior is the design
defect. Treating unknown as unavailable is correct at the spawn action because
launch safety is unproven. Unknown is not evidence that persisted content or the
window is unsafe, so it cannot justify unmounting the product.

### High: every current remedy still requires work outside the app

Locations: `api/src/transport_matters/infrastructure_guidance.py`, and
`www/packages/canvas/src/firstrun/FirstRunScreen.tsx:InfrastructureSection`.

Mitmdump, Node, and gateway guidance tells the user to install or reinstall from
a terminal. Session store guidance tells the user to run Docker and
`transport-matters` commands or edit configuration. A broken gateway override
must also be changed outside the app. The only rendered control is Retry, which
rechecks state and performs none of these remedies.

This falls short of `NOW.md:Phase 1`, which says every reported first run state
must carry an action that fixes it in the app without a terminal. It also means a
nontechnical user remains locked out of all saved product content whenever one
of these checks is red.

### Medium: the visual gate does not contain route side effects

Location: `www/packages/canvas/src/workbench/SessionCanvasRoute.tsx:SessionCanvasRoute`.

The readiness return appears after session and Space lookups, activity streaming,
identity initialization, transcript insertion, adoption reconciliation, and
captured run reconciliation. Those effects continue, including persisted pane
pruning, while the user sees only a blocking screen. The original startup gate
guarded the effects. This change restores the visual return without restoring the
effect boundary, so hidden Canvas state can change behind the gate.

### Medium: remediation is not required for a failed global check

Locations: `api/src/transport_matters/captured/readiness.py:LaunchReadinessCheck`,
and `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:InfrastructureSection`.

`LaunchReadinessCheck.remediation` defaults to `None` for every check shape. A
future failed check with `harness_id=None` can therefore be constructed without
guidance, and the browser deliberately renders nothing when remediation is null
or empty. The future check test supplies remediation manually, so it proves
payload passthrough rather than the producer invariant. The locked door can gain
a silent new red state without any boundary failure.

## Verified nonfindings

- The two new frontend tests assert rendered guidance and workbench visibility.
- Zero installed harnesses leaves infrastructure `ready` and keeps the workbench
  open. Per harness failures still disable their matching spawn rows.
- The `ready` semantic change has no unmodified browser consumer. Canvas uses
  individual checks for spawn gating and the aggregate only for the new route
  gate.
- Fresh readiness imports pass at the reviewed head. The circular import from the
  prior delta is closed by `product_identity.py`.

Focused evidence at the reviewed head: 19 Python readiness tests and 86 frontend
route, launcher, hook, and transport tests passed with caches disabled.
