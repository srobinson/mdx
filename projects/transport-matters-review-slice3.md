### Code review

Reviewed the complete `104bfb4e82073e9e2d0fe39ccd1642b1d9831b8a..03af9b6f390dc0d886a807f8d06b4e4f99372116` delta. Found 15 candidate findings for triage: 3 high, 6 medium, and 6 low.

1. **High | `packages/browsing/src/service/BrowserPaneSessions.ts:204` | Title enrichment is not associated with the navigation sequence.**
   - Observation: `untitled` stores only one history entry ID per pane. Observations carry no navigation sequence, and the next nonloading observation consumes the current pending entry.
   - Impact: Request B, then request C or step Back before B settles. A late observation from B can persist B's title on C. Reconnecting the stream can produce the same corruption because `announce()` replays the presenter's last observation.
   - Basis: The approved contract requires the first observation after that navigation sequence. The current state cannot represent that relationship. The contracts and correctness passes independently found this defect.
   - Caveat: Fully sequential navigation works. The failure needs overlapping requests, Back, Reload, or presenter reconnection.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/service/BrowserPaneSessions.ts#L203-L217

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/contract/src/browsing/index.ts#L149-L162

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/desktop/src/app/browserPanes/BrowserPaneHost.ts#L87-L94

2. **Medium | `packages/browsing/src/service/BrowserPaneSessions.ts:102` | An open records the caller supplied title before any observation.**
   - Observation: `open()` passes `input.title` directly into the history record.
   - Impact: `browser_open(url, title="Trusted")` can retain `Trusted` as the history title when the page fails to load or never reports that title.
   - Basis: The approved entry contract says title comes from the first observation after the request sequence. Current router and session tests preserve the caller supplied behavior.
   - Caveat: A later successful observation with a nonnull title overwrites the provisional value, which hides the problem on ordinary loads.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/service/BrowserPaneSessions.ts#L100-L104

3. **High | `packages/browsing/src/service/BrowserPaneSessions.ts:101` | A failed history write leaves pane and history state mutated.**
   - Observation: Open and navigate mutate `panes` before the fallible history write and before emitting their event. `BrowserHistory.commit()` replaces in memory entries before calling `store.save()`.
   - Impact: A full disk, lost permission, or failed rename makes the request return 500 while the Gateway retains the pane or navigation without publishing its event. A failed remove also disappears from in memory GET results, then returns after restart.
   - Basis: The approved storage contract requires write through persistence on every change. A focused failing store probe confirmed that a thrown save leaves the new entry in `list()`.
   - Caveat: Healthy storage follows the intended path. The defect requires an I/O failure.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/service/BrowserPaneSessions.ts#L93-L112

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/service/BrowserHistory.ts#L49-L59

4. **Medium | `www/packages/canvas/src/workbench/chrome/browser-chrome-strip.css:69` | A populated history can reduce the native page to zero height.**
   - Observation: The history list may consume 16rem inside a nonshrinking strip. Rows have a 2rem minimum, the pane body may shrink to zero, and Canvas permits 240px high panes.
   - Impact: Opening seven or more rows in a small pane consumes the available height. The reservation reaches zero height, so native view placement becomes invisible instead of remaining below the strip.
   - Basis: The approved behavior says the native view moves down. The selected design shows a short three row viewport. The correctness and contracts passes independently traced this layout mechanism.
   - Caveat: Larger panes and shorter histories leave page area visible. The written spec does not state a numeric row limit.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/browser-chrome-strip.css#L67-L74

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/pane-window.css#L97-L102

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/pane-window.css#L142-L146

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/engine/planners/efficientLayout.ts#L18-L22

5. **Medium | `packages/browsing/src/adapters/browserHistoryStores.ts:72` | Startup loading does not restore cap, order, or wire valid values.**
   - Observation: The loader returns every structurally shaped row in file order. It does not sort or cap the collection. It accepts any string for `lastVisited` and `url`, plus zero or negative safe integers for `visitCount`.
   - Impact: A damaged, older, or edited file can expose more than 100 entries in the wrong order. The checked in fixture value `lastVisited: "t"` passes the Gateway loader, while Python requires a datetime and rejects the entire REST or MCP response.
   - Basis: Cap 100 and descending time order are approved invariants. The brief explicitly calls for corrupt startup handling. A focused Python model validation reproduced the cross language rejection.
   - Caveat: Files created exclusively by the healthy current writer remain canonical.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/adapters/browserHistoryStores.ts#L58-L96

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/adapters/browserHistoryStores.test.ts#L68-L79

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/api/src/transport_matters/api/v1/browsing_contracts.py#L138-L147

6. **Medium | `packages/browsing/src/domain/browserHistory.ts:27` | A trailing path slash survives whenever the URL has a query.**
   - Observation: Slash removal runs only when `parsed.search === ""`.
   - Impact: `https://example.com/docs/?q=1` and `https://example.com/docs?q=1` create separate entries with independent counts and times.
   - Basis: The approved normalization contract drops the trailing slash. A focused Node evaluation reproduced both distinct normalized values. All three review passes surfaced this condition.
   - Caveat: The phrase could be read as the final character of the complete href. The current domain comment and supplied example describe path normalization without that exception.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/domain/browserHistory.ts#L23-L28

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/domain/browserHistory.test.ts#L15-L20

7. **High | `api/src/transport_matters/api/v1/browsing_routes.py:139` | The approved REST delete endpoint is absent.**
   - Observation: The Python control plane exposes `POST /browser-history/remove` with a body. The approved route is `DELETE /browser-history/:id`.
   - Impact: A REST client following the owner approved contract receives 404 or 405. The REST skin also differs from the Gateway and Canvas proxy routes.
   - Basis: The Slice 3 spec explicitly applies GET and DELETE to REST alongside the other Python fronts.
   - Caveat: Existing browser control plane actions commonly use command style POST routes. The Gateway and Canvas proxy implement the approved DELETE path.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/api/src/transport_matters/api/v1/browsing_routes.py#L131-L147

8. **Medium | `desktop/src/env.ts:109` | Desktop channel home resolution disagrees with Python for a literal tilde override.**
   - Observation: Desktop joins the raw `TRANSPORT_MATTERS_HOME` string. Python expands `~` before appending the channel directory.
   - Impact: With a literal `TRANSPORT_MATTERS_HOME=~/tm`, packaged desktop gives the Gateway a relative `~/tm/.transport-matters*` path. Python uses an absolute home, so history can land relative to the packaged process or fail while other channel state uses the intended location.
   - Basis: The function comment says it mirrors Python, and the added test covers only an absolute override.
   - Caveat: Interactive shells commonly expand an unquoted tilde before launch. Launch services and programmatic environments can preserve the literal value.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/desktop/src/env.ts#L102-L111

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/api/src/transport_matters/storage_roots.py#L37-L44

9. **Medium | `www/packages/canvas/src/workbench/chrome/BrowserHistoryList.tsx:44` | Concurrent removals can restore stale rows or report a false failure.**
   - Observation: Every click starts an unrestricted DELETE and replaces the full local list from its response. There is no sequence guard or pending gate.
   - Impact: Two removals that resolve out of order can redraw a row already deleted on the server. Double clicking one remove control can display a failure after the first request succeeded.
   - Basis: The API returns a complete remaining snapshot, so response completion order controls local state. The toolbar already uses `latestAction` for the same ordering concern.
   - Caveat: Gateway mutations remain correct. The stale display requires concurrent requests and clears when the list is reopened.

   https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/BrowserHistoryList.tsx#L42-L48

10. **Low | `www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx:104` | Successful history retries do not clear an earlier history failure.**
    - Observation: Toolbar actions clear `failure` through `run()`. Opening history and removing entries bypass `run()`, and successful list or remove responses never clear the shared failure state.
    - Impact: A failed list followed by a successful reopen leaves the old amber error visible. A failed remove followed by a successful retry does the same.
    - Basis: The failure pill is shared across toolbar and history actions, but only toolbar actions implement latest action clearing.
    - Caveat: A later toolbar action clears the stale message.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx#L32-L45

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/BrowserChromeStrip.tsx#L84-L109

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/BrowserHistoryList.tsx#L30-L48

11. **Low | `packages/browsing/src/adapters/browserHistoryStores.ts:99` | The adapter reimplements the shared record coercion.**
    - Observation: Local `isRecord()` is equivalent to existing `@tm/common` `safeRecord()`.
    - Impact: Record shape behavior now has a second implementation that can drift from the shared boundary primitive.
    - Basis: `packages/AGENTS.md` makes `@tm/common` the single home for cross cutting coercions and explicitly prohibits rederiving an existing helper.
    - Caveat: The two current implementations behave equivalently.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/browsing/src/adapters/browserHistoryStores.ts#L97-L101

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/common/src/primitives.ts#L87-L94

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/packages/AGENTS.md#L57-L66

12. **Low | `www/packages/canvas/src/browsing/browserPaneClient.ts:141` | History transport DTOs escape the client boundary.**
    - Observation: Both history methods return `BrowserHistoryEntryWire[]` unchanged. `BrowserHistoryList` then casts `entry.id as BrowserHistoryEntryId`.
    - Impact: Snake case fields and unbranded IDs reach UI code. Transport changes can ripple through the component, and the type system cannot exclude another branded string ID at the remove call.
    - Basis: This client's own contract says wire in, domain out and says no snake case shape escapes the module. Existing pane reads map through `browserPaneRefFromWire`.
    - Caveat: The current component reads only `id`, `url`, and `title`, so the leaked snake case fields do not cause a current rendering failure.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/browsing/browserPaneClient.ts#L17-L22

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/browsing/browserPaneClient.ts#L138-L162

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/workbench/chrome/BrowserHistoryList.tsx#L75-L81

13. **Low | `docs/plans/BROWSER-PANE-PLAN.md:426` | The changed module map cites a nonexistent ID adapter.**
    - Observation: The plan names `adapters/ulidBrowserPaneId.ts`. This branch replaces the former UUID adapter with `adapters/uuidIds.ts`; no ULID adapter exists at the reviewed SHA.
    - Impact: A maintainer following the plan is directed to a dead symbol instead of the active composition seam.
    - Basis: The review brief requires documentation to cite live symbols.
    - Caveat: The stale name existed at baseline, although this branch edits the same module map line and changes the adapter shape again.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/docs/plans/BROWSER-PANE-PLAN.md#L424-L428

14. **Low | `www/packages/canvas/src/browsing/useBrowserPanePresentation.test.tsx:249` | The strip growth test can pass without observing the reservation.**
    - Observation: The test invokes the saved ResizeObserver callback directly. Its stub does not record observed elements, so removing `observe(reservation)` from production would still pass.
    - Impact: The focused proof verifies geometry after an artificial wake, while failing to prove that strip growth causes the wake in production.
    - Basis: ResizeObserver on the reservation is the approved general fix and the core behavior under test.
    - Caveat: The production code currently calls `observe(reservation)`. This finding concerns regression coverage.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/browsing/useBrowserPanePresentation.test.tsx#L234-L255

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/testUtils.tsx#L181-L197

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/canvas/src/browsing/useBrowserPanePresentation.ts#L242-L248

15. **Low | `www/packages/shell/tests/e2e/spawn-palette.spec.ts:197` | The shell browser fixture has no history routes or interaction.**
    - Observation: `mockBrowsingApis()` handles pane stream and open only. No shell end to end test exercises the History button, GET, DELETE, row navigation, or strip growth.
    - Impact: A broken Canvas to Python proxy integration can pass the current focused units and director proof. Clicking History under this fixture issues an unhandled request.
    - Basis: The review brief explicitly calls out end to end fixtures. Unit tests cover the layers separately, and the director proof covers MCP list and remove.
    - Caveat: This is an integration coverage gap rather than a demonstrated production failure.

    https://github.com/littleorgans/transport-matters/blob/03af9b6f390dc0d886a807f8d06b4e4f99372116/www/packages/shell/tests/e2e/spawn-palette.spec.ts#L192-L241

Verification was read only except for this authorized findings file. Focused probes reproduced queried trailing slash divergence, in memory mutation after a failed store save, and Python rejection of the loader's accepted timestamp. `git diff --check` passed. No builds, typechecks, broad suites, GitHub writes, or repository file writes were performed.
