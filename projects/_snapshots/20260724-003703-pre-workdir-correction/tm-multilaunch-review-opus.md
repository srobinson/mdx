# launch_batch v1 design — peer review (opus)

Reviewer: `multi-launch:general:1:2.2` (opus). Read-only.
Baseline: feat/multi-launch worktree @ `8c51797e01ef`, tree pristine before and after.
Design under review: `~/.mdx/projects/tm-multilaunch-design-v1.md`.
Governing authority: `LAUNCH-CONTRACT.md`. Cross-checked against scout + canvas-relationship digs.

## Verdict line

**Option A (client-side placement), defer B, reject hybrid. Conditional sign-off** (3 conditions below).

## Code-grounding verification

Every code claim in the design is CONFIRMED against real code. A design on a false reuse
map is the failure mode; this map is true.

| Design claim | Verdict | Evidence |
| --- | --- | --- |
| Run creation lacks `canvas_id` | CONFIRMED | `CreateManagedRunInput` (runManagerTypes.ts:9-39) has owner/space/worktree/workspace ids, no canvas. `ManagedRunFilters` (:52-57) filters owner/state/spaceId/worktreeId only. `captured_run_models.py::CapturedRunRequest` has `space_id`/`worktree_id`/`workspace_id`, no canvas (grep: zero `canvas` hits). |
| Client placement seam is `adoptCapturedRun`/`addCapturedRun` | CONFIRMED | `canvasActions.ts:89-90,131,148` declares both; adoption is the only run→pane bind path. |
| run→HOME is per-run at `_prepare_home_and_grant` | CONFIRMED | `captured_run_context.py:270`; `runtime_home_root = prepared.resolved_storage / "runtime-home"` (:281) with per-run `shutil.rmtree` cleanup (:294). 1:1, minted per run. |
| Space/Worktree/Canvas per `space.models` | CONFIRMED | `Space.space_id` (:121-125), `Worktree.worktree_id+space_id` (:142-147), `Canvas.canvas_id+space_id+default_worktree_id?` (:162-170). |

No wrong claim found in the domain-model section. The "run carries no canvas affinity" premise
the whole OPEN DECISION rests on is real.

## OPEN DECISION — A vs B vs hybrid

### The reframe that resolves it

The decision is posed as "canvas placement in v1," but the batch verb has **two distinct
grouping identities** and the doc slightly conflates them:

- **batch-as-a-unit** = `dispatch_id`. All N candidates share one dispatch (locked D2; ledger
  key `(owner, dispatch_id, candidate_key)`, contract line 120). This is **already
  server-owned and free**. Any "operate on the batch as a unit server-side" need is served by
  dispatch_id, not canvas.
- **canvas-as-a-group** = presentation placement of the resulting panes. A canvas holds panes
  from many batches and many non-batch spawns; it is not the batch. Today this is
  **client-primary** (localStorage keyed by canvasId; server `canvas.layout` is NOT synced
  live — canvas dig §1). Coupling batch semantics to canvas would be **new product policy, not
  an existing invariant** (canvas dig §6, verified).

Once separated, most of the "what we lose" pressure evaporates: it lands on canvas-as-a-group,
which no pane has server-side today.

### The 5 questions, answered concretely

**Q1 Durability / reload.** Client localStorage grouping survives a same-browser reload. It
does NOT survive a fresh/second client or a localStorage clear. BUT the ceiling that matters:
**runs are process-resident and die on API restart** (CLAUDE.md: "Runs are process-resident,
so they do not outlive an API restart"). A server `canvas_id` annotation cannot outlive the run
it annotates. So Option B buys **no durability beyond the run's own process lifetime** in v1 —
the grouping can't outlive the grouped. B's durability argument is largely null until runs
themselves become durable, which is a different, larger track.

**Q2 Multi-client / director drill.** Client-only means a second viewer cannot see the batch as
a canvas group. BUT cross-client canvas membership **does not exist for ANY pane today** (client
localStorage owns membership; server layout is not live). Option B would hand batch runs a
cross-client grouping key that no sibling pane has — a lonely half-feature. The director→worker
drill needs server-authoritative pane membership *in general*, which is the **parallel
canvas-layering track**, not something one `canvas_id` column on the run delivers.

**Q3 Query / filter / lifecycle.** "Stop the whole batch" / "reason about a batch as a unit" is
**already answered by dispatch_id** (server-owned). "List runs in canvas X" / "stop the whole
canvas" is a canvas-membership query — a canvas-layering feature, unrelated to batch, and not a
v1/L1/L2 batch requirement. No batch capability is lost by omitting `canvas_id`.

**Q4 Migration cost of deferring.** B is **clean-additive**: optional `canvas_id` on
`CreateManagedRunInput`/`CapturedRunRequest`/`RuntimeRunView`, new optional `ManagedRunFilters`
field, thread through `createWithDisposition`. No existing field changes meaning. Does A bake in
a client-authority assumption B must unwind? **No** — the dangerous coupling would be
client-minted *identity* (candidate/dispatch), and locked D2 already forbids exactly that
(server-minted candidate keys, no client dispatch_id, no palette `/v1/runs` N-loop). A's
adoption seam operates at the *presentation* layer and stays valid regardless of B. The
identity authority — the only expensive-to-unwind axis — is already fenced correctly.

**Q5 Contract fidelity.** `FrozenLaunchSpec` (contract lines 238-268) has **no canvas field**;
the contract's stated batch delta is "candidate key, one sealed workspace snapshot, optional
evaluation artifacts" (line 94-96) — canvas is not among them. So A does not violate the
contract; B would add something the contract does not ask for. Canvas-wise, A is contract-clean.

### Why hybrid is the worst option (reject)

"Server records `canvas_id` as an opaque affinity tag now" pays a **contract cost** — `canvas_id`
would enter the immutable, `spec_version`-governed `FrozenLaunchSpec` — for **near-zero v1
benefit** (no query surface, no cross-client sync). Worse, when the canvas-layering track lands
it will define the real run↔canvas relationship, and the dig shows that relationship is **not a
single column** (same worktree hosts panes across multiple canvases; a pane can move canvases). A
premature `canvas_id` is likely the wrong shape and gets migrated anyway. Hybrid = contract cost
now + wrong-shape risk later + no v1 value.

### Cheap-to-defer, on the record

Punting server-side is cheap because: (1) batch-as-unit identity is already `dispatch_id`;
(2) B is optional-field additive; (3) the only expensive coupling (client identity authority) is
already locked out by D2; (4) canvas cross-client/durable membership exists for no pane today;
(5) process-resident runs cap durability below what a server tag could add. This clears the
v1-is-critical-infra bar: A forecloses nothing that D2 hasn't already protected.

### Single biggest thing lost by punting server-side

**Cross-client / fresh-client reconstruction of "these N panes were one batch, placed in canvas
X."** The canvas grouping lives only in the launching browser's localStorage; a second viewer or
a cleared client cannot re-derive it. Acceptable for v1 because no pane has cross-client canvas
membership today, and the batch's server-truth identity (`dispatch_id`) is retained for every
server-side "batch as a unit" need.

## Secondary soundness (found substantive issues; not a rubber stamp)

**ISSUE 1 (blocking condition) — design is SILENT on the contract's mandated snapshot.**
`LAUNCH-CONTRACT.md` line 94-96 states launch_batch "adds an internal candidate key, **one
sealed workspace snapshot**, and optional evaluation artifacts." The design's L0 scope does
worktree isolation "via existing `Worktree`" and never reconciles with this sentence — neither
includes the snapshot nor records a deviation. The scout raised this explicitly as Stuart's open
decision (scout "Open decision for Stuart": contract-complete snapshot vs thin-verb + contract
clarification). `FrozenLaunchSpec.workspace_snapshot_id?` is optional, so shipping without it is
shape-compatible — but the prose stands unqualified. This is an **unrecorded intentional
deviation**. It also has an **eval knock-on**: a fair eval (L2) requires all candidates to start
from one sealed state; L0-without-snapshot cannot deliver that by pure reuse, so the design's
"eval falls out" claim quietly depends on snapshot substrate it never scopes.

**ISSUE 2 (blocking condition) — `canvas_ref` on the candidate contradicts Option A and pollutes
the profile shape.** The design puts `canvas_ref` as a field on `LaunchCandidate` (design §
"Candidate shape") AND declares "the batch input IS a launch profile." But Option A means the
server never learns canvas. If `canvas_ref` rides inside the server-bound candidate, the server
receives placement data it is told to ignore — an inconsistency. And persisting it into a named
profile bakes a **session-specific presentation handle** (canvasId can be `space:{id}`,
`workspaceHash`, or `direct-local` per `route.ts`) into a durable, replayable artifact that may
target a canvas absent in the replay context. Fix: split the **server launch-candidate**
(model/effort/prompt/worktree — the profile item) from a **client-side per-candidate placement
plan** (candidate→canvas) consumed via `adoptCapturedRun` after receipts. This keeps A
consistent and the profile shape clean.

**ISSUE 3 (minor) — three-axis "orthogonal" framing conflates layers.** Prompt and worktree are
launch-intent axes (they change what the run is / where it executes). Canvas is a presentation
axis (where the pane displays). Listing canvas as a peer launch axis is what produced Issue 2.
Reframe canvas as a placement dimension applied client-side post-receipt, not a launch axis.

**Sound and strong:** L0/L1/L2 + parallel canvas-layering scoping is clean and correctly
separated (canvas-layering as its own track, not smuggled into L0). Profile unification is sound
*conditional on Issue 2* (exclude canvas from the profile shape). D2 blast-radius
non-negotiables are correctly identified and code-grounded (ledger key + gateway idempotency;
scout-confirmed). HOME-isolation-is-free is correct and verified.

## Sign-off

I sign off on the v1 design conditional on:

1. **Record the snapshot reconciliation.** Design must explicitly choose and state the
   launch_batch↔`sealed workspace snapshot` posture: either fold the snapshot into L0, or
   declare "v1 leaves `workspace_snapshot_id` unset; candidates run against the live worktree;
   contract line 94-96 qualified accordingly" as a recorded deviation, and note the eval-fairness
   dependency this defers.
2. **Move `canvas_ref` out of the server candidate / profile shape.** Express canvas as a
   client-side per-candidate placement plan consumed via `adoptCapturedRun`; the server
   candidate carries model/effort/prompt/worktree only. Keeps Option A consistent and the durable
   profile shape free of session-specific presentation handles.
3. **State that batch-as-a-unit identity is `dispatch_id`, not canvas.** Make explicit in the doc
   so future "operate on the batch as a unit" needs reach for dispatch_id and do not
   mismotivate Option B.
