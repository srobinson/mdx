# S4 adoption prove and persistence regression A/B

## Final feature prove at `350ce173`

The final browser and gate pass ran on branch `ml/s4-adoption` at exact head
`350ce17362ca688a836e0032ca20f9e9d1f22442`. The backend, gateway, and Vite
listeners all belonged to the shared `multi-launch` worktree. The tracked tree
was clean before and after the pass.

The Transport Matters MCP functions were unavailable in this runtime, so
control-plane launches used the authenticated `/v1/controlplane/launch` REST
twin against the same backend and control authority.

### Adoption and disconnected recovery

- `s4-live-350ce`, run `464e8211-d6a1-435b-969f-f3719785a531`, appeared in the
  already open Canvas without a prompt or refresh. Its pane showed
  `MCP orchestrator · Claude`, `0 tok`, elapsed time, `Idle`, and a live Claude
  terminal.
- The browser context was then closed before launching `s4-race-350ce`, run
  `5544b90f-f0a2-4e76-bd82-136f1b20eec1`. A fresh context opened the rooted
  Canvas and recovered the run through one Space inventory request and the
  `claude-worktrees-multi-launch/2043e1eb` activity stream. The recovered pane
  showed the same real agent metadata and populated vitals.
- A clean 1600 by 900 cold start showed no alert, no document overflow, and no
  browser console or page errors.

### Current Worktree session scope

The rendered Workdir control switched between both real Worktrees:

| Selected Worktree | Picker | Command centre Sessions |
| --- | --- | --- |
| `ml/s4-adoption` | two `MULTI-LAUNCH-SESSION-MARKER` rows only | two `MULTI-LAUNCH-SESSION-MARKER` rows only |
| `main` | one `MAIN-WT-SESSION-MARKER` row only | one `MAIN-WT-SESSION-MARKER` row only |

Switching back to `ml/s4-adoption` restored only the two multi-launch rows.
Hover plus Enter did not activate the first Worktree row in the browser driver.
A real pointer click did, changed the rooted URL immediately, and produced the
correct picker and command centre data. This was an input-driver focus issue,
not a product switch failure.

### Close lifecycle

`s4-close-350ce`, run `980d08a7-c813-49bf-861b-96fedad3799b`, was adopted with
real metadata and vitals. Hovering its header exposed the close control. The
real click sent
`POST /v1/runs/980d08a7-c813-49bf-861b-96fedad3799b/terminate`.
The server then reported `TERMINATED` with `endReason: explicit`. The pane
remained absent after `ml/s4-adoption` to `main` to `ml/s4-adoption`, then a
full reload.

### Space retry and concurrent failures

On a fresh rooted Canvas, two forced 503 responses from `/v1/spaces` produced
the persistent message:

`Couldn’t resolve the selected Worktree. Activity and session history are unavailable.`

The Retry control hit-tested to the visible button. Its real click caused Space
inventory attempt three, cleared the alert, restored the two multi-launch
sessions, and reopened:

`/v1/workspaces/claude-worktrees-multi-launch%2F2043e1eb/activity/stream?owner=local`

For the simultaneous state, `s4-alert-350ce`, run
`9952a36e-8393-479b-bc05-ffdcdc9d5ac7`, was first adopted normally. The active
`["spaces"]` query was reset in the browser solely to remove its warm cache,
then `/v1/spaces` was forced to return 503 twice. The first termination request
was also forced to return 503. The live alert stack showed both complete,
readable messages:

- `Couldn’t stop s4-alert-350ce. This agent is still running.`
- `Couldn’t resolve the selected Worktree. Activity and session history are unavailable.`

The centre of the termination retry resolved through `elementFromPoint` to a
button whose accessible name was `Retry stopping s4-alert-350ce`. Its real
click sent termination attempt two. The server reported `TERMINATED` with
`endReason: explicit`, the termination alert disappeared, and the Worktree
alert remained.

The normal cold start had no alert. The failure alert existed only under the
forced inventory failures.

### CMDK

A preliminary CMDK launch from a stale reload-only Canvas store surfaced
`Canvas launches require spaceId, worktreeId, and canvasId`. This is the
already accepted missed-rehydrate defect and was not investigated further.

After selecting `Workdir` then `S4Prove` then `ml/s4-adoption` through rendered
controls, CMDK `Agents` launched `MCP orchestrator` successfully. The server
returned 201 for run `05364cef-e1c0-42c4-b996-1484a036ec57`, and the Canvas
rendered `Claude-1`, `MCP orchestrator · Claude`, `0 tok`, and `Ready`.

All five proof runs finished `TERMINATED` with `endReason: explicit`.
The headed browser session was closed.

### Authoritative gates

Exact command:

```text
just check
```

Exit: `0`. Raw tail:

```text
uv run ruff format src/
697 files left unchanged
uv run ruff check src/ --fix
All checks passed!
uv run mypy src/
Success: no issues found in 697 source files
CHECK_EXIT=0
```

Exact command:

```text
just test
```

Exit: `0`. The shell suite reported `172 passed` files and `1309 passed` tests,
so the documented `rootShell.test.tsx` timing flake did not occur. Raw final
tail:

```text
[gw2] [100%] PASSED tests/integration/test_shared_proxy_subprocess.py::test_shared_proxy_manager_respawns_and_rehydrates_live_bindings

============================ 3416 passed in 40.09s =============================
TEST_EXIT=0
```

Raw logs:

- `/tmp/tm-s4-350ce-just-check.log`
- `/tmp/tm-s4-350ce-just-test.log`

### Final artifacts

- `/tmp/tm-s4-350ce-clean-cold.png`
- `/tmp/tm-s4-350ce-live-adoption.png`
- `/tmp/tm-s4-350ce-race-recovery.png`
- `/tmp/tm-s4-350ce-sessions-multi.png`
- `/tmp/tm-s4-350ce-sessions-main.png`
- `/tmp/tm-s4-350ce-spaces-failure.png`
- `/tmp/tm-s4-350ce-spaces-retry-success.png`
- `/tmp/tm-s4-350ce-concurrent-alerts.png`
- `/tmp/tm-s4-350ce-cmdk-launch.png`

## Current result

The visible pane loss and retiling reproduce at all three requested commits:

| Commit | Stored snapshot after reload | Visible result |
| --- | --- | --- |
| `f9d58972` | Version 1 refs, order, and pane rectangles remain exact | Transcript pane does not remount; canvas uses a fresh layout |
| `991b698c` | Version 1 refs, order, and pane rectangles remain exact | Transcript pane does not remount; canvas uses a fresh layout |
| `9c9b06f8` | Version 1 refs, order, and pane rectangles remain exact | Transcript pane does not remount; canvas uses a fresh layout |

The tested transcript rectangle was `{x:812,y:64,width:724,height:872}` before
reload and remained exactly that value in localStorage after reload at every
commit. The persisted ref and order were also exact.

The symptom therefore exists at the oldest tested point, `9c9b06f8`, and
affects PR #323. The two visible effects have one cause in this scenario: the
valid stored Canvas snapshot is missed during rehydrate, so its transcript pane
does not mount and the remaining runtime panes receive a fresh layout. No pane
ref, rectangle, or order was deleted from storage.

## Valid A/B method

Each commit used the same sequence:

1. Serve the exact commit from a separate detached worktree and unique Vite
   origin, proxied to the same real desktop backend.
2. Start a fresh Playwright browser context with no prior localStorage.
3. Select `Workdir`, enter `S4Prove`, and activate `ml/s4-adoption` through the
   rendered command centre. This establishes the verified
   `space_id/worktree_id/canvas_id` route and Canvas storage key.
4. Click the `MULTI-LAUNCH-SESSION-MARKER` session row itself to open a durable
   `transcript:` pane.
5. Move and resize that pane through pointer input.
6. Read
   `transport-matters-canvas:32886ca5-74a8-4c3a-a53e-c2fec3bd5a88`,
   reload, then compare stored refs, rectangles, order, and rendered pane IDs.

Storage version is `CANVAS_STORE_STORAGE_VERSION = 1` at `9c9b06f8`,
`991b698c`, and `f9d58972`. No tested profile carried a snapshot written by an
older build.

## Invalid first witness and correction

The first reported failure used `Spawn pane`, which creates
`dev-blank:Pane-1`. The persistence contract deliberately excludes
`dev-blank` refs. It also used camel case query parameters, so the route never
established a verified durable Canvas identity. Visible DOM rectangles then
changed under the documented browser dependent auto fit. That witness was a
driver limitation and was retracted immediately.

The corrected witness uses a persistable transcript pane, the real snake case
route contract, verified Worktree selection, and the stored world rectangles
rather than absolute screen geometry.

## Artifacts

- `/tmp/tm-s4-f9d58972-exact-durable-before.png`
- `/tmp/tm-s4-f9d58972-exact-durable-after.png`
- `/tmp/tm-s4-991b698c-durable-before.png`
- `/tmp/tm-s4-991b698c-durable-after.png`
- `/tmp/tm-s4-9c9b06f8-durable-before.png`
- `/tmp/tm-s4-9c9b06f8-durable-after.png`

The throwaway worktrees and their Vite processes were removed. The shared
branch advanced externally from `f9d58972` to `350ce173` while the A/B ran, so
the final `f9d58972` result was repeated from its own detached worktree. The
shared worktree was clean at `350ce173` after cleanup. No repository source was
edited by the integrator.

Full `just check` and `just test` were not run in this A/B. The persistence
failure brief replaced the broader feature prove, and the shared branch moved
while the isolated comparison was running.

## Earlier integrator evidence, not revalidated in this A/B

At `61edaa98`, the prior integrator observed:

- live MCP adoption of `mcpliveadopt` without refresh;
- `MCP orchestrator · Claude` metadata and populated vitals;
- reconnect snapshot recovery for runs launched while the browser was closed;
- a CMDK Claude launch after selecting the Worktree.

That earlier round recorded `just check` ending with
`Success: no issues found in 697 source files` and `just test` ending with
`3416 passed in 35.43s`. Those gates do not apply to the current head.
