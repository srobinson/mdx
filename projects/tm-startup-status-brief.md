# Brief: surface startup background activity on the first-run screen

Issue #399 phase 3, step 2 of `docs/plans/AUTOPILOT-WIRE-PLAN.md`. Worktree
`.claude/worktrees/startup-status`, branch `feat/startup-activity-signal`, based on main
at 772d6468. Node deps are already installed there; do not run a bare `pnpm install`.

Owner's ask, verbatim: "we should surface a realtime status to the user of what is
happening. just a small visual indication that work is happening in the background."

Keep it small. This is a status signal, not a redesign of the first-run screen.

## Why this is not cosmetic

`www/packages/canvas/src/firstrun/useHarnessInventory.ts` polls only while
`hasUnobservedInstallation(items)` is true, and its own docstring admits the inference:
"the backend's fire-and-forget startup refresh is (or should be) in flight, and it
completes with no client signal".

Since #402 there are two startup passes, and they run in sequence:

1. `state_refresh:refresh_harness_state`, which writes the observation rows.
2. `access_verification:verify_provider_access`, which launches one real harness turn
   each, concurrently, up to `DEFAULT_VERIFICATION_TIMEOUT_S = 120.0`.

`hasUnobservedInstallation` goes false the moment pass 1 lands. So polling stops, the
screen goes quiet, and pass 2 then runs for up to two minutes launching real processes
with no indication at all. The screen currently looks settled precisely when the slowest
work is happening. That is the defect to fix, and it is the acceptance criterion.

## Design

**Report the truth from the server. Do not infer harder on the client.**

The two passes are `asyncio.Task`s the lifespan already stores:
`app.state.harness_refresh_task` and `app.state.harness_access_verification_task`. Their
`done()` is the source of truth. Either may be None (no session pool, or verification not
enabled, since `settings.startup_access_verification` is False outside the desktop backend).

Add a closed activity model to `harnesses/inventory.py` and hang it off
`HarnessInventoryResponse` as an optional field defaulting to None. Optional matters:
`harness_inventory(pool)` has four production callers (`api/v1/harnesses`,
`api/v1/controlplane_mcp`, `api/v1/harness_enablement`, `baseline_harvest`) and a required
field breaks three of them.

Keep `harness_inventory` pure over the pool. The activity comes from app state, so the
caller that has app state supplies it. Design the seam so a caller passes it in rather than
the inventory reaching for a global.

**Two surfaces, not one.** `NOW.md`'s North Star: "API-first, the UI is one client of two...
anything the UI can do, the director must do programmatically. No UI-only logic." So the
MCP harness view gets the same field if it can reach app state cheaply. If it cannot, say so
and leave it, rather than inventing a second mechanism.

**Client.** Drive the poll off the reported activity instead of `hasUnobservedInstallation`
where the two disagree; the real signal supersedes the inference. Render a small indication
that work is in flight, naming which pass, because "checking what is installed" and
"verifying provider access by running a real turn" are different waits and the second is the
long one. Reuse whatever live-region and busy affordance `FirstRunScreen` already has;
`useHarnessInventory` references one. Do not add a spinner library or new animation
primitives.

**Honesty rule.** The indicator must be off when nothing is running. It must not appear
merely because evidence is missing, and it must not appear on backends where verification
never runs. A signal that lies is worse than none.

## Constraints

- `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` is 606 lines. The 700 limit is hard.
  If your change would push it over, extract rather than append.
- No narrating comments. A comment earns its place only by explaining a non-obvious why.
- Match the surrounding style. The client mirrors the API model; keep
  `www/packages/core/src/types/harnessInventory.ts` in step with the Python model, and note
  its "Mirrors HarnessInventoryResponse" header comment.
- Never use em dashes.

## Gates, all verbatim, all must pass

    cd api && just check
    cd api && just test
    pnpm --filter @tm/shell test

The frontend suite is the full one, not a targeted vitest filter. Never bare pytest.

## Tests

- The activity field reports refreshing while pass 1 is live, verifying while pass 2 is
  live, and neither when both are done or absent.
- The response still serializes for a caller that supplies no activity (the MCP and
  enablement paths must not change shape unexpectedly).
- The client polls while activity is live even when every harness already has an
  observation. This is the regression that motivates the slice; it must fail without the
  change.
- The indicator is absent when nothing is running.

## Out of scope

- Rendering `compatibility.outcome`, the version-prompt UI, and the comparator. That is
  step 3 (#399 phase 4).
- Rework of the per-harness "Test access" button.
- Any change to the verification pass itself.
