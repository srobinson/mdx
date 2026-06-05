# Control plane S6b review

Reviewed branch `controlplane-s6b-canvas-adoption` at `51de739df6b096d25d3c1ec04a27e8c2626bf2eb` against base `0f4178c` and scout section 2.

Verdict: **2 blockers, 2 minors. Builder trust is conditional.** The design is compact and the focused tests are thoughtful, but two missing adversarial sequences break the central adoption guarantee.

The repository was pristine before review. The supplied green gate was accepted and was not rerun. No repository files, git state, tests, builds, GitHub comments, or messages to other bus agents were produced. This report is the only authorized external write.

## Blockers

### 1. Lookup uncertainty becomes terminal, so successful runs can disappear forever

Confidence: 98 for the normal 404 race, 96 for outage exhaustion.

The normal producer order creates a real visibility window:

1. Python awaits `RUN_STARTED` emission before returning the prepared capture ([capture_rpc.py lines 185 to 190](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/api/src/transport_matters/capture_rpc.py#L185-L190)).
2. The gateway then awaits PTY spawn and only afterward registers the run ([RunManager.ts lines 316 to 327](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/packages/runtime/src/service/RunManager.ts#L316-L327), [RunManager.ts lines 469 to 505](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/packages/runtime/src/service/RunManager.ts#L469-L505)).
3. During that window, `getRun` converts the gateway 404 into `null` ([transport.ts lines 464 to 475](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/core/src/transport.ts#L464-L475)).
4. S6b maps that `null` to `gone` immediately ([capturedRunAdoption.ts lines 125 to 140](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L125-L140)). Every later frame returns early because the candidate already exists ([capturedRunAdoption.ts lines 84 to 103](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L84-L103)).

The same terminalization occurs after a temporary transport outage. Five attempts are bounded correctly, but exhaustion calls `finish(entry, "gone")` ([capturedRunAdoption.ts lines 141 to 159](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L141-L159)). A later delta or reconnect snapshot cannot rearm the retained candidate. Immediate failures exhaust after 3.75 seconds; repeated lookup timeouts exhaust after about 18.75 seconds.

Impact: a successful service launch can remain invisible until route remount. A gateway outage longer than one retry burst has the same result.

The unit test encodes the wrong normal race by asserting that a missing lookup is terminal ([capturedRunAdoption.test.ts lines 104 to 123](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.test.ts#L104-L123)). No test exercises `RUN_STARTED`, then 404, then registered and running.

Required repair: distinguish positive lifecycle truth from lookup uncertainty. Terminal state or snapshot disappearance can settle `gone`. A visible candidate that receives 404, timeout, or transport failure needs a bounded retry burst followed by a dormant state with no timers. A later frame or fresh snapshot generation can rearm one bounded burst under a cooldown. This preserves the no spin requirement and the feedback loop.

### 2. Split persistence can leave a live run with no pane and no repair path

Confidence: 95.

`adoptCapturedRun` writes `capturedRunStore` membership first, then writes the independently persisted canvas counter and pane ([canvasActions.ts lines 142 to 150](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/canvasActions.ts#L142-L150)). A quota failure, malformed canvas cache recovery, reset, or crash that preserves only the first store produces a remembered live run without an open or docked pane.

The reconciler cannot heal that state:

- Production `hasRun` checks only `capturedRunStore` membership ([SessionCanvasRoute.tsx lines 184 to 194](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L184-L194)).
- Membership alone is immediately classified as adopted ([capturedRunAdoption.ts lines 93 to 100](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L93-L100)).
- The startup reconciler only prunes stale mappings and never recreates a missing pane ([SessionCanvasRoute.tsx lines 94 to 118](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L94-L118)).
- The route adapter reports adoption success unconditionally after calling the canvas action ([SessionCanvasRoute.tsx lines 190 to 193](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L190-L193)).

This repeats a known persistence loss class. `LESSONS.md` requires coupled persistence operations behind one typed port. Prior captured canvas history also contained an explicit restore loop that rebuilt panes from persisted run keys.

Impact: the durable run survives, but Canvas permanently hides it until membership is manually removed or the backend run ends.

Required repair: adoption success must mean both the run mapping and an open or docked pane exist. The idempotent action should repair a missing pane when the run ID is already present. The reconciler should query that composite invariant, or one persistence authority should own the coupled transition. Add a regression that seeds a run record without a pane, applies repeated activity frames, and proves exactly one pane is rebuilt without spawning.

## Minors

### 3. The slice adds to a file already beyond the hard size limit

Confidence: 100.

`canvasStore.test.ts` was 910 lines at base. This commit adds 46 lines and leaves it at 956. The governing instruction requires refactoring a file already over 700 lines before adding code, including tests. The added adoption cases are at [canvasStore.test.ts lines 179 to 223](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/canvasStore.test.ts#L179-L223).

### 4. Attachability policy is duplicated

Confidence: 95.

The new reconciler repeats the exact `STARTING` or `RUNNING` policy ([capturedRunAdoption.ts lines 185 to 190](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L185-L190)) already owned by `isAttachableRun` in the route ([SessionCanvasRoute.tsx lines 180 to 182](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/workbench/SessionCanvasRoute.tsx#L180-L182)). This is a direct violation of the project zero duplication rule. Move the shared run state policy to one model owner and reuse it from pruning and adoption.

## Persistence and trust boundary audit

The pre S6b persistence test is honest. It writes a raw version 4 localStorage snapshot, calls `persist.rehydrate()`, adopts a new run, and proves the remembered record, minimized flag, OSC setting, bypass setting, and both run entries survive ([capturedRunStore.test.ts lines 433 to 467](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunStore.test.ts#L433-L467)). This is not a fresh round trip.

Keeping storage version 4 is correct because S6b adds actions and behavior but does not change the persisted byte shape. `partialize` remains `{runs, oscColorReplies, bypassPermissions}` ([capturedRunStore.ts lines 278 to 298](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunStore.ts#L278-L298)). The existing tolerant migration preserves older records and defaults missing settings.

The external input boundary is handled well. The activity candidate requires exact `launch_kind: "service"`, a recognized harness, and a bounded safe run ID. Adoption then requires an exact run ID and harness match from `getRun`, an attachable managed state, and a bounded safe worktree ID ([capturedRunAdoption.ts lines 173 to 190](https://github.com/littleorgans/transport-matters/blob/51de739df6b096d25d3c1ec04a27e8c2626bf2eb/www/packages/canvas/src/model/capturedRunAdoption.ts#L173-L190)). Malformed, unknown, mismatched, and terminal responses are rejected before persistence.

The existing activity stream and value based captured run membership helper are reused cleanly. No parallel stream or new server channel was introduced. The central contract miss comes from reconciling the scout prose against the actual producer ordering: 404 cannot be terminal during the `RUN_STARTED` to gateway registration window.

## Builder trust verdict

**Conditional.** The implementation shows good local craft: narrow production scope, a dedicated state machine, bounded backoff, cancellation, exact trust validation, no persisted shape churn, and an honest old snapshot test. The build missed two system invariants that the slice exists to protect: uncertain lifecycle observations must remain recoverable, and adoption spans two independently persisted stores. The tests validate the local model but do not falsify it against producer ordering or partial durability. Trust should be restored after both blockers have adversarial regressions and the two hard hygiene issues are resolved.
