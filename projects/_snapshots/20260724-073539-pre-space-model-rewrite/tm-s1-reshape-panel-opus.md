# S1 reshape v3 — design panel (opus, aggregate/domain-model lens)

Reviewed `tm-s1-reshape-proposal.md` v3: durable Space (org container) ⇿ M:N `space_worktree_link` ⇿ durable Worktree (path identity) → anchored Canvas tree; git-ness is a runtime `repo_group_key` label; detection never writes Space membership; default Space = computed-all owner Worktrees; Director subsumed by the Space switcher. No code yet.

**Verdict: aggregate sound, one MAJOR — the "same Space" predicate is internally contradictory under M:N.** My prior §2 concern is folded (line 124 pins #4 to `NO ACTION DEFERRABLE INITIALLY DEFERRED`; proof #6 adds the cascade proof) and the three-axis invariant is now explicit. The M:N topology is coherent and correctly kills M4. The one real defect is a definitional gap that does not block the S1 slice (only the default Space exists in S1) but must be resolved in the model before named-Space semantics are built.

---

## MAJOR — the "same Space" / "cross-Space" predicate is undefined under M:N (§3, lines 116 vs 140/143)

The proposal contradicts itself. Line 116: "A Canvas appears in **every** Space that references its anchor Worktree." But line 140: `default_worktree_id` "may target another Worktree in **the same durable Space**," and line 143: "A Canvas may contain panes targeting multiple Worktrees in **its Space**. Cross-Space pane placement is rejected." Under M:N a Canvas has no single "its Space" — its anchor Worktree is in the computed-all default Space **plus** every named Space that links it. So "same Space," "its Space," and "cross-Space rejected" have no well-defined referent.

This predicate is load-bearing for three operations: (a) `default_worktree_id` validity, (b) pane-placement acceptance/rejection, (c) launch-target + authorization scoping. In the old strict-containment model it was an O(1) scalar compare (`canvas.space_id == target.space_id`). Under M:N it becomes a membership question against a set of Spaces, and the proposal never says which set.

Failure mode if left ambiguous: two implementers pick different predicates — one checks "shares a named Space with the anchor," another checks "same owner" (default-Space-scope) — and pane placement / launch validation / authz diverge across REST, MCP, and the launch path, silently allowing or denying the same target depending on code path.

Recommended resolution (and I believe the only one consistent with computed-all default): **placement and launch-target scope is OWNER-scoped, not named-Space-scoped.** Because the default Space computes membership over *all* owner Worktrees, any two owner Worktrees are always co-resident in the default Space, so "same Space" for placement collapses to "same owner." Named Spaces are then **view filters**, not placement constraints. Re-express line 143 as "cross-owner pane placement is rejected; named Spaces filter the view, they do not constrain which Worktrees a Canvas's panes may target." Authorization is per-request: a caller scoped to Space S may reach Canvas C iff C's anchor Worktree is a member of S (junction for named, computed-all for default); that read-scope check is well-defined and separate from placement. Define the one canonical membership predicate `worktree_in_space(worktree_id, space_id)` (computed-all when `is_default`, junction otherwise) and route authz, placement, and launch validation through it.

Not an S1 blocker: S1 ships only the default Space (named-Space CRUD is deferred), so every placement is trivially owner-scoped and the ambiguity cannot bite yet. But the schema and the predicate are designed now; nail it before named Spaces arrive or it becomes rework across the authz + launch surface.

---

## Sub-question verdicts

**1. Aggregate coherence under M:N — coherent, modulo the MAJOR.** Worktree is the aggregate root that owns its Canvas tree (`anchor_worktree_id`, cascade on worktree delete); Space is a peer durable aggregate that *references* Worktrees via the junction and owns none of their lifecycle; a Canvas's Space-appearance is derived (in every Space referencing its anchor). This is a clean two-aggregate model (Worktree-owns-Canvas, Space-references-Worktree) and is more honest than the old strict containment. The only invariant that "breaks" versus strict containment is exactly the same-Space predicate above — it was a scalar, now it is a set-membership question that must be defined once.

**2. worktree_root + ">=1 Canvas per Worktree" + computed-all — SOUND.** The ">=1" invariant is Worktree-level (`root_canvas_id NOT NULL` + unique, idempotent `ensure_worktree_root`) and is untouched by M:N. Computed-all guarantees every Worktree (and its root) appears in the default Space with no junction row, which is precisely what lets `reconcile_detection` create a Worktree without ever writing membership — the invariant that keeps M4 dead. Correct and elegant.

**3. #4 root FK + cascade + pair trigger under the new topology — SOUND (my prior concern folded).** #4 is now `NO ACTION DEFERRABLE INITIALLY DEFERRED` (line 124); #5 anchor FK CASCADE drives worktree-delete; proof #6 asserts the cascade commits and lone/direct root delete fails at deferred pair validation. One addition: the worktree-delete state machine must also remove the Worktree's `space_worktree_link` rows. Specify `space_worktree_link.worktree_id` FK as `ON DELETE CASCADE` (line 44 says "owner-scoped foreign keys" but no ON DELETE action), and extend proof #6 to assert the junction memberships for the deleted Worktree are gone (and that a named Space may legitimately become empty).

**4. Director subsumed by Space — CORRECT, no distinct top view needed.** The computed-all default Space *is* the everything-view that the earlier virtual Director provided; named Spaces are curated subsets; the switcher is the presentation. No Director Canvas row and no super-root above Spaces are required — the default Space plays that role. This also cleanly avoids the cross-Space-parent / same-space-FK problem that killed a persisted global Director row, because Spaces do not parent Canvases (Worktrees own them).

**5. default = computed-all vs materialized links — RIGHT CALL.** Computed-all is what makes "detection never writes the junction" achievable for the common case (new Worktrees appear via computation, zero junction writes), avoids junction bloat, and never drifts. Materialized links only for curated named subsets is the correct split. One schema gap: enforce **one default Space per owner** — add a partial unique `UNIQUE (owner) WHERE is_default` (line 34 declares the boolean but no constraint prevents two defaults, which would make computed-all membership ambiguous).

---

## Minors

- **m1** `space_worktree_link.worktree_id` (and `space_id`) FK `ON DELETE` action unspecified (line 44). Worktree delete needs CASCADE on the worktree side; Space delete (later slice) needs CASCADE on the space side. State both; add junction-cleanup to proof #6.
- **m2** No `UNIQUE (owner) WHERE is_default` on `space` (line 34). Two default Spaces would make computed-all membership ambiguous and the switcher nondeterministic.
- **m3** Confirm the primary-protection guard reads **projected** `is_primary` at delete/launch time (§5 says so, line 185–187) — `is_primary`/`missing` are now projection-only, so a temporarily unobservable Git repo projects `is_primary=false`; the "fail closed for destructive/launch actions" rule (line 186) must cover that window so an unobservable primary is not deletable.

## Net

Approve the M:N aggregate. It is coherent, kills M4 by construction, and realizes the virtual-Director decision cleanly. Gate approval on defining the single canonical `worktree_in_space` membership predicate (resolving the line-116-vs-140/143 contradiction, owner-scoped placement recommended), plus the two schema constraints (junction FK ON DELETE CASCADE, one-default-per-owner). None of these block the S1 slice, which ships only the default Space.
