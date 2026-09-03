# 603: CDP attach capability expires 30s after minting, and a refused attach gives a bare 401

URL: https://github.com/littleorgans/transport-matters/issues/603
State: open
Labels: bug, browser, P1
Updated: 2026-09-02T17:38:02Z

A CDP attach capability expires 30 seconds after minting, and minting is only available as a side effect of listing panes. An agent that reads the pane listing, decides what to do, then connects, routinely arrives after the window has closed and gets an unexplained `401`.

## Observed

Road testing #601, driving the inspector from an orchestrator run:

1. `browser_panes` returned `devtools_url` carrying a freshly minted capability.
2. A few tool calls later, the CDP client connected and the WebSocket handshake failed with `Unexpected server response: 401`.
3. Nothing in the failure named the cause. Working out that the capability had lapsed meant reading `api/src/transport_matters/api/v1/devtools_access.py`.
4. Calling `browser_panes` again and connecting in the same step succeeded immediately.

The controls in `DevtoolsCapabilityStore` are three:

- `open()` spends the capability once and refuses a second open (`devtools_access.py:94`).
- The capability is bound to the origin it was minted for, and the front must present it back naming the origin it is actually listening on.
- `OPEN_WINDOW_SECONDS = 30.0` bounds how long an unspent capability stays live.

Live sessions are not affected: `keep()` refreshes `last_seen` on every command and only `IDLE_SECONDS = 600` of total silence retires a socket. The cost is entirely at the door, and it lands hardest on an agent, whose read-then-act gap is exactly where the 30 seconds goes.

Because `open()` is one shot, a dropped socket also cannot be re-attached with the token in hand. Every reconnect means re-enumerating panes.

## Threat the window actually covers

The front is loopback bound, and `loopback_origin` (`devtools_access.py:225`) refuses to mint for any other host, so a remote holder of the capability cannot reach the socket to spend it. A capability that lands in a transcript or a provider log is not reachable from where it lands. What remains is local replay: session files on disk are readable by any process running as the same user, including the codex and grok runs this workspace launches with shell access. That is a real path, but `open()` being one shot already closes replay more decisively than the window does.

The window's distinct contribution is narrow: it bounds a minted-but-never-spent capability. Weighed against the friction it creates for the in-app browser's whole purpose, which is live debugging of a locally running server, the trade is not obviously worth it.

## Outcome

Attaching to a pane is predictable, and a refused attach says why.

## Scope

- Decide whether `OPEN_WINDOW_SECONDS` earns its place given that one-shot spend and origin binding already carry the security weight. Options: drop it; or widen it substantially.
- Give a refused attach a distinguishable reason. A bare `401` on the WebSocket handshake is indistinguishable from a wrong origin, an already-spent capability, and an unknown one.
- Consider a mint verb separate from the pane listing, so re-attaching after a dropped socket does not require re-enumerating panes.

## Acceptance

- List panes, wait past the current window, attach, and the outcome is either success or a refusal naming the cause.
- Re-attaching after a dropped socket does not require a fresh `browser_panes` call, or the issue records why it must.
- `just check` and `just test` green.


## Sub issues
[]
