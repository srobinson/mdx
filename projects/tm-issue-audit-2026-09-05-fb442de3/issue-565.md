# 565: Authenticate Canvas presenter registration and bind it to the genuine Electron instance

URL: https://github.com/littleorgans/transport-matters/issues/565
State: open
Labels: bug, browser
Updated: 2026-08-31T21:24:56Z

## Problem

The Gateway accepts Canvas presenter registration through an unauthenticated loopback SSE route. A caller chooses the Canvas, presentation capability and devtools origin in the request:

- [`GET /canvases/:canvasId/browser-panes/stream`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/server/browsingRouter.ts#L98-L125)
- [`presenterDeclaration`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/server/browsingRouter.ts#L269-L293)

The Canvas devtools selection then takes the first composited presenter with a live endpoint:

- [`canvasDevtoolsFor`](https://github.com/littleorgans/transport-matters/blob/e3e61d6f1f710601d156fef58b4a73790fc9d5e6/packages/browsing/src/domain/presenters.ts#L60-L73)

A same-user local process can register first for a known Canvas, claim `composited`, and advertise a loopback endpoint it controls. A later Director `browser_panes` or `whoami` read can then direct automation to that fake presenter.

## Impact

The fake presenter can misdirect or deny browser automation and fabricate the pane surface an agent observes. This is an integrity and availability problem: an agent may believe it is driving a genuine browser pane while it is connected to an impersonator.

[#524](https://github.com/littleorgans/transport-matters/issues/524) and [PR #564](https://github.com/littleorgans/transport-matters/pull/564) contain the damage. Python never sends a Director bearer to the declared endpoint, attach capabilities are bound to the declared origin, and a capability intercepted at a fake origin cannot be relayed to the genuine front. The spoof therefore gains no control-plane credential, genuine pane access, or app-renderer access.

The endpoint selection itself remains unauthenticated and predates PR #564.

## Design constraints

A static launcher secret does not cover every launch path. In hosted mode, Electron may join a runtime that the CLI started earlier, so there is no common parent process to distribute a per-launch secret.

Harness processes also run unsandboxed as the same user. A durable secret in the channel home or another process environment would be readable by the process this boundary needs to exclude.

The trust bootstrap needs to work across packaged, hosted and development launches without relying on a same-user secret at rest.

## Work to scope

1. Define the identity of a genuine Electron presenter and the authority that can attest it.
2. Authenticate presenter registration and reconnection before it enters the live presenter set.
3. Bind the declared devtools origin and browser-pane observations to that authenticated presenter instance.
4. Prevent an unauthenticated competing presenter from winning `canvasDevtoolsFor` selection.
5. Preserve multiple legitimate Canvas windows, renderer reloads, desktop restarts and presenter failover.
6. Keep the pane-only CDP front and the origin-bound Director capability from PR #564 unchanged unless the new identity boundary can simplify them without weakening revocation or renderer isolation.
7. Record the chosen trust model and rejected alternatives in `docs/plans/BROWSER-PANE-PLAN.md`.

## Verification

- A rogue loopback process registers for the same Canvas before the genuine renderer and cannot become the selected composited presenter.
- A rogue process cannot publish a devtools origin or pane observation under a genuine presenter identity.
- A genuine packaged desktop registers, reconnects after renderer reload, and resumes presentation.
- A hosted desktop can join an already-live runtime and authenticate without a common launcher.
- Multiple genuine Canvas windows remain independently addressable.
- Revoking or closing a presenter removes its observations and devtools origin from selection.
- `just check` and `just test` pass.


## Sub issues
[]
