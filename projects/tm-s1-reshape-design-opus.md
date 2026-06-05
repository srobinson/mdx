# S1 persistence reshape — design review (opus, aggregate/domain-model lens)

Reviewed `tm-s1-reshape-proposal.md` (v1; identity-claim registry dropped per orchestrator, Space is a pure runtime projection). Focus on the three surviving parts. No code yet.

**Verdict: design sound, one major to nail in v2 (§2 root FK ON DELETE action).** No fundamental structural flaw. The reshape correctly separates the three axes the old model conflated, and the anchor-FK-CASCADE approach dissolves M4 *and* dissolves M1 more cleanly than the current deferred-trigger fix — provided the root FK delete action is specified correctly.

---

## §1 — Canvas anchored to one Worktree: SOUND, does not over-constrain

Stuart's canvas = "a group of panes in a workdir; user switches canvas in the same workdir." The concern is whether `anchor_worktree_id NOT NULL` (single, inherited by descendants) forecloses "a canvas groups panes across >1 worktree."

It does not, because the proposal keeps three axes orthogonal:
- **anchor_worktree_id** = organizational/tree home + lifecycle cascade unit. One per canvas subtree.
- **default_worktree_id** = durable launch preference; explicitly "may choose another durable Worktree while both are members of the same current projection" (line 117) and "does not define tree ownership" (line 115).
- **pane `contentRef.worktreeId`** = execution placement. Panes are browser-side and explicitly out of scope (line 254), so each pane keeps its independent worktree target.

A canvas anchored to W can therefore hold panes/runs against W2 whenever W2 is in the anchor's current projected Space — exactly the spec §2 capability ("a descendant Canvas may launch runs against another stable Worktree in the same Space"). Cross-*Space* panes were never an intended capability (Stuart's "in a workdir" is singular; spec bounds to "same Space"), and the anchor→Space projection correctly bounds panes to the anchor's Space. No capability is lost.

Recommendation (not a flaw): state the invariant explicitly in v2 so no builder narrows it — "anchor_worktree_id is organizational/lifecycle home only; a canvas's panes and default_worktree_id may target any Worktree in the anchor's current projected Space; anchor never constrains pane placement." Also confirm intended: deleting the anchor Worktree cascades the whole canvas subtree (via #5) even if some panes targeted a still-alive sibling Worktree. This is identical to the locked per-worktree-root model (not a regression), but it is the one surprising consequence of single-anchor, so it should be an acknowledged UX semantic, not an accident.

## §2 — Pair trigger + parent FK + subtree cascade: SOUND shape, one MAJOR detail

The parent FK on `(owner, anchor_worktree_id, parent_canvas_id) → canvas(owner, anchor_worktree_id, canvas_id)` correctly forces a subtree to share one anchor (cross-anchor reparent fails, proof #2), matching spec §2. The deferred pair trigger (worktree names a `worktree_root` canvas with matching anchor + default; root names the reciprocal worktree; user canvas can never satisfy) is a clean shrink of the current trigger. The deferred root pair still holds.

**MAJOR — specify constraint #4 `ON DELETE NO ACTION DEFERRABLE INITIALLY DEFERRED`, not RESTRICT, and prove the cascade interaction.** #4 (`space_worktree.root_canvas_id → canvas`) is described only as "deferred for pair creation"; its `ON DELETE` action is unspecified. The proposal newly adds #5 (`canvas.anchor_worktree_id → space_worktree` **CASCADE**), so a privileged worktree delete cascades the root canvas (and its subtree) automatically. During that delete both the worktree row and its root canvas are removed in one transaction; the root canvas is the *referenced* row of #4. If #4 is `RESTRICT`, the #5-cascade deletion of the root while the worktree logically still references it can fire an immediate restriction — re-creating the exact M1 deadlock in a new form. If #4 is `NO ACTION DEFERRABLE INITIALLY DEFERRED`, the check defers to commit (both gone → no dangling → passes) while still blocking a *direct* root delete (worktree survives → dangling at commit → rejected), which is the intended root protection. §6 lists direct-root-delete-fails but lists **no** worktree-delete-cascade proof. v2 must (a) name #4 as NO ACTION deferred and (b) add a proof: "privileged worktree delete cascades root + user subtree via the anchor FK and commits; direct/lone root delete still fails at commit." This is the same class of bug that already cost S1 a round; the anchor-CASCADE design is better but only if #4's action is pinned.

Minor note: with #5 as CASCADE, any `space_worktree` row deletion nukes its canvas subtree. That destructive power is correct only because worktree deletion always runs through the guarded Slice-6 state machine; keep raw `space_worktree` deletes off every other path.

## §3 — default_worktree_id as durable pref with anchor fallback: SOUND

Durable stored preference + read-time fallback to `anchor_worktree_id` when the preferred worktree drifts out of the anchor's current Space (no row rewrite) + action-time revalidation on launch/claim + set-time validation on mutation. Three checkpoints, coherent, no hidden inconsistency:
- The FK #6 (`default_worktree_id → space_worktree`, NO ACTION deferred) guarantees the stored default references a real worktree *row*; the projection check guarantees it is in the same *Space*. Two independent validations, not conflated.
- On worktree delete, surviving user-canvas defaults are explicitly cleared before commit (#6); roots never survive their worktree's deletion (cascaded by #5), so the pair-trigger's root-default-pin is never left dangling.
- The anchor is always in the canvas's Space by definition, so the fallback target is always in-Space. If even the anchor worktree is `missing` in projection, launch legitimately fails at revalidation — a degraded-but-correct outcome, not an inconsistency.

## Adjacent note (not one of the three, low)

Dropping `is_primary` and `missing` from `space_worktree` to projection-only means "primary Worktree deletion always fails" and launch's missing/archived rejection now depend on **live** detection at action time. If git is temporarily unobservable, `is_primary` projects false and `missing` projects true; the delete path revalidates live, so this is acceptable, but v2 should confirm the primary-protection guard reads projected `is_primary` at delete time (not a stored flag, which no longer exists).

---

## Net

Approve the reshape shape. It gives durable identity to the facts TM owns, makes Git grouping a runtime projection (dissolving M4), preserves Canvas/transcript history, and the anchor-FK-CASCADE dissolves M1 more naturally than the deferred trigger. Gate approval on v2 pinning constraint #4 to `NO ACTION DEFERRABLE INITIALLY DEFERRED` with a worktree-delete-cascade proof, and stating the anchor-vs-pane/default axis separation as an explicit invariant.
