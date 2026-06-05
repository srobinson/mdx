# Review: startup activity signal (feat/startup-activity-signal)

Diff: main (955a1260)..HEAD, commits d9fa072e (api) and 5ae46d2b (canvas).
Reviewer: startup-status:general:1:3.2. Gates not re-run; orchestrator reported all three green.

Counts: 0 blocker, 1 medium, 6 minor. Hypothesis (b) refuted. (a), (c), (d) confirmed with
refinements below.

## Verified against the brief

- Truthfulness. `harness_inventory_activity` returns None when both tasks are None, when both
  are done (cancelled and failed tasks are `done()`), and reports `refreshing` ahead of
  `verifying_access` while both are live. Non-desktop backends never create the verification
  task, so they only ever report `refreshing` or nothing. `test_inventory_resolves_at_v1`
  covers the no-task case (`activity is None`).
- Overlap test. `test_inventory_reports_the_active_startup_pass_without_misreporting_overlap`
  creates both futures before the first GET and asserts `refreshing`, then resolves refresh
  and asserts `verifying_access`, then resolves both and asserts None. It does exercise both
  tasks live simultaneously, not each alone. The MCP test does the same for both views.
- Blast radius. Five callers reach `harness_inventory`, not four: `capabilities.py` goes
  through `inventory_for_request`. `harness_enablement`, `baseline_harvest`, and
  `capabilities` project items and keep their shape. REST `/v1/harnesses` and the MCP full
  view gain `activity: null` when idle. The MCP launch view uses `exclude_if=_empty`, so its
  idle shape is unchanged byte for byte and `activity` appears only when a pass is live.
  The TS mirror (`activity: HarnessInventoryActivity | null`) is honest to the wire and the
  three fixtures (rootShell, visual canvas, transport test) were updated.
- Regression test. `polls while either reported startup pass is active after observations
  settle` asserts the poll interval value for all-observed plus live activity. On main
  `inventoryPollInterval` ignores `activity` and returns false for that input, so the test
  fails without the change. It does not merely assert the field exists. The inverted test
  (`does not infer background activity from missing observations`) pins the removal of the
  heuristic.
- FirstRunScreen.tsx is 622 lines. No spinner library, no new animation primitive, no em
  dashes, no narrating comments in the diff.

## Findings, ranked by value

### 1. Medium. Stale activity is rendered during an errored refetch

`useHarnessInventory.ts` derives `activity` from `query.data?.activity`, and
`FirstRunScreen.tsx` renders the `startup-activity` note above `SectionBody`, outside the
status switch. react-query retains the last successful `data` when a refetch fails
(confirmed against `@tanstack/query-core` 5.101.2 in the workspace: after a success then a
throwing refetch, `isError` is true and `data.activity` is still the old phase). So when a
poll fails mid-verification the screen shows the `Harness inventory unavailable` alert and,
directly above it, `Verifying provider access with real harness turns` from stale evidence,
and the live region carries the same stale message. Items are already hidden in that state
by `deriveFetchStatus`; the activity note is the one piece of stale data that survives.

Fix: derive `activity` the way `status` is derived, null on error:
`activity: query.isError ? null : (query.data?.activity ?? null)`. Leave
`inventoryPollInterval` reading the raw query data so the interval keeps ticking and the
screen recovers without a manual retry. Add one FirstRunScreen test: success with a live
phase, then a failing refetch, assert the note is absent while the alert shows.

### 2. Minor. (c) The `??` in the live region defers announcements and duplicates text

Judgment on the orchestrator's question: an error during startup activity is not silent.
`statusAnnouncement` already returns an empty string for `error` and the error branch is
`role="alert"`, so the region never carried error text. What `startupActivityMessage ??
statusAnnouncement(...)` does is defer `N harnesses reported.` and `No harnesses
registered.` until the pass ends (the transition to None announces them then), and it
renders the same sentence twice in the reading order: once in the visually hidden
`sr-status` region and once in the visible note.

Fix: compose rather than replace. The live region announces both facts in one string
(`[statusAnnouncement(status, items), startupActivityMessage].filter(Boolean).join(" ")`),
nothing is suppressed, and retry recovery still announces the count. Keep the always
mounted `sr-status` region as the announcement channel (a conditionally mounted live region
can miss its mount time announcement, which is why routing through the existing region was
the right call). Drop `aria-busy` from the visible note: nothing in `firstrun.css` keys on
it, it is not a live region, and on a plain paragraph it is a test hook dressed as
semantics. The test can assert on the note text.

### 3. Minor. (a) Confirmed: `hasUnobservedInstallation` is dead

Zero consumers in `www/packages`, tests included. Delete it in this slice.

### 4. Minor. (d) Confirmed: the two getattr pair is duplicated

`api/v1/harnesses.py` and `api/v1/controlplane_mcp.py` both read `harness_refresh_task` and
`harness_access_verification_task` off `app.state`. Keep `harness_inventory_activity`
pure over two futures. Add one caller side helper in `api/v1/harnesses.py`, which already
names `harness_refresh_task` in the refresh route and already exports
`inventory_for_request` to `capabilities.py`:

    def startup_activity(app: FastAPI) -> HarnessInventoryActivity | None:
        return harness_inventory_activity(
            getattr(app.state, "harness_refresh_task", None),
            getattr(app.state, "harness_access_verification_task", None),
        )

`controlplane_mcp` imports it. A third pass then lands in one place. No import cycle:
`harnesses.py` imports nothing from `controlplane_mcp`.

### 5. Minor. Pin the sampling order

In `inventory_for_request` the activity is sampled before `harness_inventory` reads the
evidence, purely because it is an argument expression. That order is what guarantees a
`null` activity is never paired with a pre-refresh snapshot; reversed, a client would stop
polling on stale rows and the screen would settle on `Not yet checked`. Nothing pins it.
The helper from finding 4 is the natural home: one sentence in its docstring stating that
it must be sampled before the evidence read, and why.

### 6. Minor. `data.activity?.phase !== undefined` reads as a workaround

It peeks inside the object to decide whether the object exists. The contract header says
every field is present and idle arrives as `null`, and the hook already normalises with
`?? null`. Write the intent: `data.activity != null` (the idiom already used in
`@tm/core`, and it keeps the same defensive posture as the sibling
`data.harnesses === undefined` guard), or `!== null` if that guard is considered dead too.

### 7. Minor. Name the phase on the TS side

Python declares `HarnessInventoryActivityPhase`; the TS mirror inlines the union and two
call sites (`STARTUP_ACTIVITY_MESSAGES` and the hook test) reach for
`HarnessInventoryActivity["phase"]`. Every other enum in `harnessInventory.ts` is a named
alias. Export `HarnessInventoryActivityPhase` and use it.

## Refuted: (b) lost recovery path

No real state is newly stranded.

- No session pool: 503, no data, no poll in either version.
- Refresh callable absent, or the refresh pass failed: no rows will ever arrive. The old
  heuristic polled every 3s against nothing, forever; the new code stops. The way forward is
  the same as before: `Safe Refresh`, whose handler calls `retryInventory()` after the POST.
- First fetch after both passes completed: rows are complete, activity None, nothing to poll
  for. Because activity is sampled before the read (finding 5), None is never reported
  ahead of the rows.
- Cached under `staleTime` (remount within 30s): `refetchInterval` is independent of
  staleness. The cached response's own `activity` drives the interval, so a live phase
  ticks once and refreshes; an idle phase means nothing was running when cached.
- Failing poll mid pass: the interval reads retained data, so polling continues and
  recovers by itself (which is also why finding 1 should not null the data the interval
  reads).

Backend restart while the screen is open was not covered by the old heuristic either (all
observed, no poll), so it is not a regression of this slice.
