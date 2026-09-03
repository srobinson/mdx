# 446: baseline_harvest and baseline_publish overlap: decide the boundary or fold one into the other

URL: https://github.com/littleorgans/transport-matters/issues/446
State: open
Labels: 
Updated: 2026-08-24T02:28:56Z

`baseline_publish` (#444) now supersedes `baseline_harvest` for the normal workflow, and the two overlap enough to mislead. Not urgent; capturing it so it does not drift.

## Today

Both are dev-only entry points and they already **share the capture path** — `baseline_publish` imports `harvest_baseline` rather than reimplementing it. The split is:

**`baseline_harvest`** — one cell, manually targeted.
- `--harness --model --effort`, or no args to print the launch view
- Calls `harvest_controlled_baseline` for that cell, writes a bundle and current pointer
- `--accept-degraded` / `--accepted-by`: the operator-judgment path for accepting a degraded baseline
- Requires a clean worktree (stamps source identity)
- **Never mints a release reference.** Evidence only.

**`baseline_publish`** — a cohort, planned and bound.
- `--harness <id>` or `--all`
- `build_baseline_publish_plan` reads launch state once and plans **without spending**
- Prints the provider-turn budget, requires `--confirm-spend` or an interactive typed `publish`
- Resumes cells that already have evidence, captures only missing ones
- **Mints immutable reference bindings** into the release, which harvest cannot do

## The problem

Harvest is mostly subsumed. What it still uniquely offers is single-cell targeting for debugging and `--accept-degraded`. Both are plausible `publish` flags.

Leaving two overlapping CLIs is the failure mode worth avoiding: someone captures a cell with `harvest`, sees a bundle written, and wonders why no release changed.

`NOW.md` already describes `baseline_harvest` as internal tooling for pre-populating a reference matrix that no user ever runs.

## Decide one

1. **Fold in.** Move single-cell targeting and `--accept-degraded` onto `publish`; delete `harvest`'s CLI, keeping `harvest_baseline` as the shared capture function.
2. **Keep both, documented.** `harvest` becomes an explicitly debug-only entry point, with its docstring and `NOW.md` stating that `publish` is the workflow and `harvest` never changes a release.

Option 1 is the DRY answer. Option 2 is cheaper and may be enough given both are dev-only.

## Not in scope

The shared `harvest_baseline` capture path is correct and stays either way.

## Sub issues
[]
