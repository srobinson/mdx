# S1 persistence reshape design review

Date: 2026-07-22  
Proposal baseline: `9ac8d10d2d5304bc579980636729d466e952f404`  
Verdict: **major concern**

## Summary

The Worktree anchored Canvas schema is a strong way to dissolve the M4 foreign key conflict. The persisted versus projected model split is also sound.

The proposal should not be approved with live detection as the authority for current Space membership. Immutable claim rows stabilize claim IDs, but they do not stabilize which claim a read selects. The proposed projection can place the same durable Worktree and Canvas under different Space IDs across concurrent or consecutive operations without any durable state change.

The minimal correction is to keep the Worktree anchored Canvas reshape while giving current membership a durable, generation stamped authority that only reconciliation changes. Reads can overlay live branch, HEAD, primary, and missing facts without making a fallible Git subprocess choose the owner Space.

## 1. Claim immutability does not make effective Space identity stable

Proposal sections 1 and 3 select the Git claim when live detection proves Git membership and the path claim otherwise. Both claims intentionally coexist. A single projection chooses one, but independent projections can choose different claims.

Current `detect_space` makes that instability concrete:

1. It runs `git rev-parse` with `allow_failure=True`.
2. Every nonzero result becomes `_plain_space`, regardless of whether the cause is a genuinely plain directory, unsafe repository ownership, permissions, corruption, or another Git failure.
3. Only process absence and timeout become structured errors at this first probe.

A focused probe returning Git exit code 128 with `fatal: detected dubious ownership` produced a plain `DetectedSpace` with no `repo_instance_key`. Under the proposal, that one observation selects path Space `P`. A later successful probe selects Git Space `G` again.

Consequences:

1. Two concurrent reads can expose the same Worktree and Canvas under different Space IDs.
2. Archive policy, owner scoped authorization, Canvas default membership, Director trees, and run or session stamps can disagree between operations.
3. The Git to plain walkthrough also fires for transient probe failure. A true repository removal and an indeterminate observation are not distinguished.
4. Locking by detection identity does not serialize the transition. Plain and Git observations use different lock keys, while reads take neither lock.

Required correction:

1. Model detection as `git`, `plain`, or `indeterminate`. An indeterminate result must never select the path claim.
2. Put current membership behind a durable claim selection or observation generation changed only by Director reconciliation. The row can represent the last successful observation rather than domain ownership.
3. Make one projection generation explicit across authorization, response assembly, claim stamping, and launch resolution.

## 2. Fail closed creates a transition bootstrap gap

The proposal says a detected group without its selected identity claim fails ordinary reads with `space_identity_missing`. This hides more than newly detected paths.

After a plain Worktree `W` with path claim `P` undergoes `git init`, detection selects a Git identity before claim `G` exists. `W`, its protected root, and its user Canvas subtree are already legitimate durable objects, yet ordinary list and point reads fail until reconciliation creates `G`.

The recovery path is underspecified:

1. The mutation route is `POST /spaces/{id}/worktrees/reconcile`.
2. The new Git Space ID is not yet known.
3. The old path Space is no longer the selected projection.
4. Current reconciliation first requires a Space snapshot to find a refresh path. Carrying that shape forward would make recovery depend on the projection that is failing.

An owner wide `list_spaces` can also be poisoned by one such group if `space_identity_missing` fails the whole projection index.

Required correction:

1. Define reconciliation by a durable Worktree ID or cwd, with authorization derived from the immutable path claim.
2. Reconciliation must bypass current projection when creating the missing Git claim.
3. Define whether owner wide reads omit only the unresolved group or fail the entire operation. The error must include a recoverable mutation target.
4. Add the plain to Git gap, process restart during the gap, and concurrent read plus reconcile to the required proof.

## 3. Owner wide live detection is an availability multiplier

Section 3 builds an owner wide projection for list, point get, Director tree, workspace caller resolution, and launch resolution. Even `get_canvas` or one launch therefore detects every existing Worktree path owned by that user.

Current Git detection can run two subprocesses per repository. Each has a two second timeout. A serial owner wide projection has a worst case delay approaching four seconds per Git repository. One timeout or `git worktree list` failure can abort unrelated reads for every Space.

This also defeats database pagination because grouping and sorting occur after all durable rows are loaded and detected. If a database connection or transaction is held while subprocess detection runs, slow Git probes also consume the session pool.

Required correction:

1. Scope point reads and launch resolution to the requested Worktree or Canvas anchor.
2. Use bounded parallel detection and isolate failures per repository.
3. Do not hold a database transaction or pooled connection across Git subprocesses.
4. Specify a last known observation or cache policy, freshness marker, and invalidation rule for owner wide list and Director surfaces.
5. Add latency and partial failure budgets to the required proof, including one timed out repository among healthy repositories.

## 4. Launch revalidation does not close the filesystem race

Section 1 says launch validates membership again at action time. The current launch seam resolves a Worktree while holding a database connection, returns a path, closes the connection, and spawns later. Git membership can change after any revalidation because the filesystem is outside the database transaction.

The proposal therefore cannot guarantee that a sibling default remains in the anchor's Space through spawn. Repeating the same projection narrows the window but does not make the decision atomic.

Required correction:

1. Define launch membership validation as snapshot semantics rather than an atomic guarantee.
2. Carry the chosen projection generation and detected identity fingerprint into the spawn seam and stamp them in launch facts.
3. Perform a final targeted probe immediately before spawn and reject a changed fingerprint, or launch the anchor Worktree when membership is uncertain.

## Lens answers

1. **Git versus path selection:** database uniqueness prevents duplicate claims for one identity key, but concurrent operations can select different effective Spaces. Claims never move is insufficient.
2. **Read projection:** fail closed can hide an existing, legitimately owned Worktree and Canvas tree after `git init` but before Git claim creation. The recovery route needs a durable target independent of current projection.
3. **M4 dissolution:** the Canvas anchor removes the original foreign key rollback. The walkthrough still has an availability gap and Git to plain can trigger on probe failure. Missing linked Worktrees stay in Git only while a live sibling's Git metadata reports them.
4. **Performance and blast radius:** owner wide detection on every point and list read is an availability and latency trap without scoping, bounded concurrency, and failure isolation.
5. **Default and launch:** fallback is coherent inside one projection. Cross operation consistency and launch atomicity remain unresolved.

## Recommendation

Approve the Worktree anchored Canvas schema and persisted versus projected model boundary. Revise the Space membership authority before implementation. M4 does not require current membership to be recomputed from Git on every read. A durable last successful membership claim, updated atomically by reconciliation, preserves the reshape's ID stability while avoiding identity flip flop, global read failure, and repeated Git subprocess cost.
