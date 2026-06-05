# Optional git-worktree isolation review (opus)

Date: 2026-07-22
Reviewer: multi-launch opus (read-only)
Baseline: `feat/multi-launch` @ `b094e80d69ad7d57c5bba0ff8f4d71a986a837f2`, tree pristine (only `.serena/` untracked), re-verified after review. No writes.

## Recommendation

**Defer the isolation-as-launch-parameter; add-now one cheap forward-compatible seam.** Do not add a per-candidate isolation launch directive until the batch/eval consumer that needs it is being built (adding it before then couples a heavy ephemeral lifecycle to an unbuilt caller). But **add now**, inside the already-approved worktree-create work (spec Slice 6), a `origin`/ownership provenance marker on `space.models.Worktree`, set at the create boundary. Retrofitting ownership onto an inventory that already conflates created and detected rows is painful and unsafe once created worktrees exist without the flag.

## Biggest risk

`space.models.Worktree` has no TM-owned marker (`worktree_id, space_id, owner, path, workspace_slug, workspace_hash, branch_name, head_oid, is_primary, missing, archived, detected_at, created_at, updated_at`), and the approved spec's create path "reconciles detection" after `git worktree add` (spec §9), folding a created worktree into the same detected inventory. Detection also rewrites observed facts on every match (`SpaceStore._upsert_worktree` sets `archived=false` on match — the scout's finding #11). **Without an ownership marker that is set at create and preserved through detection reconciliation, auto-cleanup cannot distinguish a TM-created ephemeral checkout from a user's real detected worktree, so `git worktree remove` can destroy a user checkout and its uncommitted work** — the exact data-loss the spec's dirty-check guards, defeated the moment cleanup runs automatically instead of via explicit user delete.

## 1. Add now or defer

- **What it buys (real):** per-candidate isolated writable checkouts so N parallel launches don't collide editing the same files. For the batch/eval axis this is a genuine unblock: `launch_batch` (LAUNCH-CONTRACT, `launch_batch` candidate key) running multiple *writable* candidates against one repo would corrupt shared working-tree state without isolation. The need is real once candidates write.
- **What it costs:** it crosses today's "only detect, never create" invariant. Note the primitive itself is *already coming*: the approved CRUD spec adds `GitWorktreePort.create/move/remove` and executes "one typed `git worktree add`" as explicit user CRUD (spec §9, Slice 6), plus the delete lease + `git worktree remove` state machine (§10–11, Slices 7–8). So isolation would **reuse** that primitive, not invent one. The genuinely new cost is the **ephemeral lifecycle**: auto-create-on-launch, ownership tracking, and auto-cleanup with a dirty-work policy.
- **Why defer the parameter:** the consumer (writable batch/eval) is not yet built. Adding an isolation directive to `controlplane.run_models.LaunchRequest` now, before anything consumes it, is speculative surface on the hottest contract (the same one Slice 3 is already threading `canvas_id` through). Land the manual primitive (spec v1), add the provenance seam, and introduce the launch directive in the batch/eval slice where it is exercised end-to-end.

## 2. Where the parameter belongs

- **Category distinction first.** `canvas.default_worktree_id` (`space.models.Canvas.default_worktree_id`), pane `contentRef.worktreeId` (terminal/captured-run refs require it), and the launch's resolved `worktree_id` (`api/v1/launch_resolution.resolve_run_worktree`) are all **selectors of an existing checkout**. Isolation is a **constructor of a new checkout**. Conflating "use worktree X" with "make me a fresh worktree" is a category error — a `default_worktree_id` cannot express "create one."
- **The CHOICE belongs at the run/launch level.** Opt-in is per-execution: `LaunchRequest` (and its batch candidate) gains an optional isolation directive, e.g. `worktree_isolation: none | ephemeral(base_ref)`. When set, the launch service *creates* a worktree via the spec's `GitWorktreePort.create`, yielding a `worktree_id` that then flows through the **existing** selection path (`resolve_run_worktree` → `RunManager` create → run `worktree_id`). One level owns the decision; the *result* is an ordinary `worktree_id`, so nothing downstream changes.
- **Resolution chain:** selection can inherit (run → pane `worktreeId` → canvas `default_worktree_id`), and that chain already exists implicitly. Isolation should be a *distinct* optional directive layered on top, not a fourth value in the same field. Canvas MAY carry an optional default isolation *policy* ("new runs here isolate"), but the constructor still executes at launch.
- **Space: no.** Space is repo identity (`SpaceStore._claim_git_space`); isolation is per-execution and does not belong on the container.

## 3. Ownership / lifecycle

- **Opt-in creation is compatible with "never AUTO-created"** only if the trigger is a genuine explicit per-launch choice. It does extend "only detect, never create" from explicit CRUD (spec) to launch-time, which the owner must sign off as an acceptable widening.
- **Cleanup owner = the worktree lifecycle lease.** The spec already introduces `worktree_lifecycle_lease` (§10) binding resource lifetime to a worktree. An ephemeral isolation worktree's natural cleanup trigger is: last lease released **and** `origin=created` **and** clean → auto `git worktree remove`. Reuse the lease; do not invent a second lifetime mechanism.
- **Owned vs detected marker (the linchpin):** add `space.models.Worktree.origin: detected | created` (or an `ephemeral`/`created_by_run_id` field). Cleanup rule: `created` → may `git worktree remove`; `detected` → de-inventory only, **never** `rm`. Two hard requirements: (a) set `origin=created` at the create boundary in `GitWorktreePort.create` before detection reconciliation runs; (b) detection reconciliation (`_upsert_worktree`) must **preserve** `origin`, exactly as the scout demanded user-archive intent be stored separately from detected facts (finding #11) — a re-observed created worktree must not silently become `detected`, or the cleanup rule inverts into a data-loss bug.
- **Dirty-on-cleanup policy:** even for owned ephemerals, auto-cleanup must honor the spec's dirty check (§11 step 6–7). An isolated candidate that produced uncommitted results the user wants is not garbage. Default: block auto-remove on dirty, surface for explicit disposition; never silently `--force`.

## 4. Coherence

- **Locked-root canvas tree:** orthogonal. A worktree is a checkout axis; the canvas tree is placement. No conflict. One guard: do not let `canvas.default_worktree_id` point at an ephemeral worktree — `canvas_default_worktree_fk ON DELETE SET NULL` means routine ephemeral cleanup would repeatedly null canvas defaults. Defaults should reference stable (detected or long-lived) checkouts only.
- **Durable transcript stamp:** the canvas stamp (spec §7.2) is unaffected, but `session.worktree_id` (0006, FK-less) already records the run's worktree. An ephemeral worktree that is removed leaves **every** isolated run's `session.worktree_id` dangling — systematically, not occasionally. If isolation-run history must stay meaningful, denormalize the worktree path/branch into the session at capture (same immutable point-in-time pattern the canvas stamp uses), rather than storing only a soon-dead `worktree_id`.
- **Run→canvas affinity:** unaffected. The run keeps its `canvas_id`; the worktree is a separate axis. No foreclosure.
- **Foreclosure:** adding isolation forecloses nothing and helps batch/eval. Doing it *without* the ownership marker forecloses safe auto-cleanup and risks destroying user work — that is the failure mode to avoid, not the feature itself.

## Net

Defer the isolation launch-parameter to the batch/eval slice that consumes it (place the *choice* on the run/launch level, an optional Canvas default *policy*, never on Space; let the result flow as an ordinary `worktree_id`). Land now, within the approved Slice 6 create work, the `origin` provenance marker set at the create boundary and preserved through detection reconciliation, plus the cleanup rule (`created` may `rm`, `detected` de-inventory only). That single cheap addition is what makes the later isolation feature safe; everything else can wait for its consumer.
