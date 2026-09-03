# 504: Gateway-owned back stack for browser panes (multi-presenter history)

URL: https://github.com/littleorgans/transport-matters/issues/504
State: open
Labels: 
Updated: 2026-08-28T06:23:46Z

## Problem

Back and Forward on a browser pane step the native view's own history stack (`webContents.navigationHistory`), and each `WebContentsView` has its own. The Gateway stores a history step as pane state and broadcasts it to every registered presenter, and takes `can_go_back` / `can_go_forward` from whichever presenter reported last (`packages/browsing` `browserPaneView`, `BrowserPaneSessions`).

With one presenter (the desktop app today) this is exact. With two, each steps its own stack, which can diverge, and the strip's button state can come from a presenter that has since disconnected. Raised as finding #6 on #500 and deferred; noted in `docs/plans/BROWSER-PANE-PLAN.md`.

## Trigger

A second presenter becoming real (second desktop window, remote viewer). Not before.

## Proposed shape

The Gateway owns the back stack: `BrowserPane` gains `entries[]` and `index`; `open` / `navigate` push and truncate forward entries; `history` moves the index and issues a URL navigation; `reload` re-issues the current entry. `can_go_back` / `can_go_forward` are derived from the index, so every presenter converges on the same URL and the observation no longer reports them.

- Desktop: the history intent, `HostedView.documentSeq` stamping for history, and the `goBack` / `goForward` path are removed; everything is a URL load.
- Contract, Python, canvas: drop the history intent variant and the two booleans from the observation wire; keep them on the presentation as derived values. The strip reads the same fields.
- Open design question: in-page `pushState` observed from the presenter must append an entry or the stack drifts from what the user sees.

## Estimate

One PR, roughly the size of #500; likely removes more code than it adds.

## Sub issues
[]
