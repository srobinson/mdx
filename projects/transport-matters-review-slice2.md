# Browser chrome Slice 2 adversarial review

Reviewed branch `feat/browser-chrome-strip` at `7953a4a56c6eff05aa77a7b8c29e3ce81df448ad` against `main` at `c8bc9f9e33b699e80d8db6eb9bb2915a62685864`. The branch had no pull request at review time.

## High

### 1. Consecutive history steps collapse into one native navigation

Location: `packages/browsing/src/domain/browserPane.ts:101` and `www/packages/canvas/src/browsing/presentation.ts:118`

Observation: Each Back or Forward request increments `navigationSeq`, but replaces the pane's sole `navigation` value with one delta. The Canvas stream handler mirrors only that latest value. Its presentation driver samples the store on the next animation frame. Two stream deltas received before that frame therefore become one placement carrying only the later sequence and one delta.

Impact: With at least three history entries, two quick Back clicks or concurrent `browser_history` calls can advance the Gateway from sequence N to N+2 while Desktop receives only N+2. `BrowserPaneHost` calls `goBack()` once, so one accepted navigation disappears. There is no scheduling contract requiring an animation frame between SSE messages.

Basis: The sequence gate prevents replay, but the state shape cannot represent more than one pending imperative step. Existing tests assert the Gateway emits both deltas. They do not cover coalescing through `applyBrowserPaneFrame` and the animation frame presentation driver.

Caveat: The defect does not appear when Desktop receives a placement between every history response.

Links: [domain intent replacement](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/packages/browsing/src/domain/browserPane.ts#L96-L103), [animation frame sampling](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/www/packages/canvas/src/browsing/presentation.ts#L118-L124)

### 2. A retained history intent cannot reconstruct a recreated native view

Location: `desktop/src/app/browserPanes/BrowserPaneHost.ts:105`

Observation: A `HostedView` created while the current placement is a history intent starts with `url: ""`. `#navigate` marks the sequence applied, invokes history on the new view's empty stack, and returns without loading a page.

Impact: After a Back or Forward command becomes the retained Gateway state, a renderer crash, host recreation, or new presenter snapshot creates a blank view and consumes the intent. The pane remains blank until a later URL navigation or Reload. This breaks the host's stated crash reconstruction behavior.

Basis: `BrowserPanePlacement` carries either a URL or a history delta, so a history placement contains no reconstructable URL. The crash regression covers only a URL intent. The history regression starts with an existing loaded view. The source comment at `HostedView.url` explicitly records the blank state.

Caveat: Replaying the frame into the same live view is safe because its applied sequence and history remain intact.

Links: [blank initial URL](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/desktop/src/app/browserPanes/BrowserPaneHost.ts#L102-L109), [history intent consumption](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/desktop/src/app/browserPanes/BrowserPaneHost.ts#L127-L134)

## Medium

### 3. Pane global history state is applied to presenter local history stacks

Location: `packages/browsing/src/projections/browserPaneView.ts:32` and `packages/browsing/src/service/BrowserPaneSessions.ts:101`

Observation: History availability comes from the pane's last observation without checking that its `presenterId` is still registered. The adjacent CDP projection performs that membership check. A history command then becomes pane global state and is broadcast to every presenter, although each `WebContentsView` owns a separate history stack.

Impact: When an observing presenter disconnects, Canvas can keep Back or Forward enabled from its stale facts. A replacement presenter may send that intent into an empty stack. With two live composited presenters, one delta is applied to both potentially divergent stacks, and whichever presenter reports last determines the pane's shared URL and button state.

Basis: The presenter service explicitly supports multiple registrations and rebroadcasts panes when presenters join or leave. URL intents converge views on an authoritative target. History deltas and history availability remain local to each native view.

Caveat: A single presenter whose native view survives a brief reconnect will usually refresh the observation through `announce()` before a user acts.

Links: [stale availability projection](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/packages/browsing/src/projections/browserPaneView.ts#L29-L35), [global history emission](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/packages/browsing/src/service/BrowserPaneSessions.ts#L101-L105)

### 4. The director proof can pass before Desktop reloads the page

Location: `desktop/src/browserPaneProof.ts:257`

Observation: Before Reload, the proof has already observed page one. `browser_reload` synchronously increments the Gateway sequence. The following poll accepts that new Gateway sequence together with the unchanged, previously stored page one URL.

Impact: The proof passes on its first read if Canvas never forwards the reload placement or Desktop ignores it. It therefore cannot support the claimed end to end parity for Reload.

Basis: Navigate and history wait for changed shell owned facts. Reload waits only for desired Gateway state plus an observation that was true before the command. No fresh observation timestamp, load marker, or page side counter is required.

Caveat: Desktop unit coverage asserts that repeated URL intents call `loadURL`. This finding concerns the black box proof's ability to catch integration failures.

Link: [reload predicate](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/desktop/src/browserPaneProof.ts#L250-L259)

### 5. Reload behavior conflicts with the assigned Slice 2 contract

Location: `packages/browsing/src/domain/browserPane.ts:92`

Observation: Slice 2 defines Reload as `navigateBrowserPane(pane, pane.url)`. The implementation instead promotes `pane.observed.observedUrl` into the desired URL whenever an observation exists.

Impact: After a redirect, in page navigation, or history step, Reload changes authoritative desired state to the last observation. A later recreated presenter opens that observed location rather than the prior desired URL. This can preserve transient redirect or history destinations across reconstruction.

Basis: The supplied Slice 2 specification is explicit. The branch's updated plan, MCP description, and tests instead say to reload the page shown, so the implementation and its internal documentation consistently override the assigned contract.

Caveat: This may be an intentional product decision. It still needs an owner level specification update or a code change before the slice can be judged against the supplied contract.

Link: [reload implementation](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/packages/browsing/src/domain/browserPane.ts#L87-L94)

### 6. The outer resize target is clipped at the viewport's right and bottom edges

Location: `www/packages/canvas/src/workbench/chrome/pane-window.css:178`

Observation: The browser pane handle moves eight pixels outside the pane frame. `overflow-clip-margin` opens the frame's own paint clip, but the ancestor `.canvas-viewport` still has `overflow: hidden`. When a pane is flush with the viewport's right or bottom edge, that outer band is clipped. The remaining inner part sits under the native view apart from the narrow border ring.

Impact: A composited browser pane at either viewport edge loses nearly all of the reachable resize target. The corner can become impractical to grab at a position allowed by the free move layout.

Basis: The changed handle spans eighteen pixels inside and eight pixels outside the frame. The native view covers the body, and the outer viewport clips descendants. No layout constraint keeps panes eight pixels inside the viewport.

Caveat: The owner's road test proves the normal corner works. This mechanism is specific to panes flush with the right or bottom viewport edge.

Links: [outer handle](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/www/packages/canvas/src/workbench/chrome/pane-window.css#L172-L191), [viewport clip](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/www/packages/canvas/src/workbench/canvas.css#L52-L58)

## Low

### 7. Asynchronous strip failures are silent to assistive technology

Location: `www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx:65`

Observation: Navigation, history, Reload, and close failures appear asynchronously in a plain `span` without an alert, status role, or live region.

Impact: Screen reader users receive no announcement after an action fails. The status text exists visually, but focus has already returned to the Canvas after address submission.

Basis: The earlier browser pane failure surface uses an alert role. The new strip test checks text and CSS class only.

Caveat: A user can encounter the text through later navigation. The state change itself is not announced.

Link: [status rendering](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx#L64-L71)

### 8. Overlapping strip actions expose failures by settlement order

Location: `www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx:32`

Observation: Every action starts an untracked promise. A newer invocation clears `failure`, but an older promise can reject later and overwrite the current state.

Impact: A later successful action can still leave the failure pill from an earlier request. Two failures can be displayed in the reverse of invocation order, and the pill does not identify the responsible action.

Basis: Controls remain active while requests are pending. `run` has no operation token or serialization.

Caveat: Every displayed rejection corresponds to a real failed request. The ambiguity is whether the product intends to retain any outstanding failure or only the latest action's result.

Link: [untracked action runner](https://github.com/littleorgans/transport-matters/blob/7953a4a56c6eff05aa77a7b8c29e3ce81df448ad/www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx#L30-L38)

## Review coverage

The full 57 file fixed commit diff was inspected across contract, Gateway browsing, Desktop main, Python API and MCP fronts, Canvas, tests, proof, and plan documentation. The production Desktop imports from `@tm/contract` remain type only. Placement and observation boundaries validate the new union, sequence, delta, and boolean fields. The reuse map is followed, `BrowserPaneSubtitle` is fully removed, changed files remain under 700 lines, and `git diff --check` is clean. Per review policy, no build, type check, or broad test command was run. The only repository worktree change remains the owner's excluded `transport-matters.code-workspace` edit.
