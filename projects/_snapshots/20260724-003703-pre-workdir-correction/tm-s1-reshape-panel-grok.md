# S1 reshape design panel (Grok)

Date: 2026-07-22  
Input: `~/.mdx/projects/tm-s1-reshape-proposal.md` (v3)  
Baseline cited: `9ac8d10d`  
Lens: whole-model coherence + migration/schema realism  
No code changes.

## Verdict

**Major concerns** (not a full reject). The durable Space / runtime repo-group split is directionally coherent and dissolves the plain→Git rebinding problem (M4). Several cross-section joints are half-specified and will bite implementation unless locked before build.

One-line: `panel: concern major §3/§5 same-Space rules and principal→Space resolution lack a membership predicate after canvas.space_id / worktree.space_id are removed`

---

## 1. Whole-model coherence

### What coheres

| Theme | Sections | Assessment |
| --- | --- | --- |
| Durable org vs runtime Git label | Decision, §1–2, §4–6 | Consistent. `repo_group_key` projected only; detection must not write junction. |
| Default Space computed membership | §1, §5, §6 | Consistent: no junction rows; all owner Worktrees visible under default. |
| Canvas anchored to Worktree | §3, §6–7 | Consistent: drop `canvas.space_id`; tree lives under `anchor_worktree_id`; multi-Space appearance is projection. |
| Detection write boundary | §1 invariant, §5, proof 3–4, 8, 10 | Consistent: reconcile upserts path identity + roots only; never membership. |
| Director = Space switcher | Decision, §7 | Consistent with prior “no Director canvas row.” S1 only ensures default Space. |
| Root pair triggers | §3, proof 5–6 | Same reciprocal idea as current 0030, re-keyed on `(owner, anchor_worktree_id)` instead of `(owner, space_id)`. |

### Contradictions / half-specified joints

**A. “Same durable Space” without a Space on Canvas or Worktree (§3 three-axis + pane rules)**

- Stated: `default_worktree_id` may target another Worktree **in the same durable Space**; panes may target multiple Worktrees **in its Space**; cross-Space pane placement rejected.
- After drop of `canvas.space_id` and (implied) `space_worktree.space_id`, there is **no single Space on the Canvas row**. Membership is “all Spaces whose links (or default computation) include `anchor_worktree_id`.”
- Under S1-only-default-Space, “same Space” is vacuous (everything is in the default). Once named Spaces exist, the predicate must be explicit, e.g.:
  - “caller’s selected Space contains both anchor and target Worktree,” or
  - “exists at least one common Space,” or
  - “target is any owner Worktree” (weak).
- **Gap:** §3 asserts same-Space rules without defining the membership predicate or where it is enforced (service only vs DB). Not a contradiction with §1 for S1-only-default, but a **dangling cross-section contract** for Space CRUD and for any S1 code that pretends to enforce cross-Space pane rejection.

**B. Principal / MCP workspace → `allowed_space_id` (§5 reads, §7, vs baseline code)**

- Today `resolve_workspace_caller` maps `principal.workspace_id` → `space_id` via worktree row’s `space_id` (`get_space_for_workspace`).
- Proposal removes Space from Worktree. Doc never defines the replacement:
  - always default Space in S1?
  - union of Spaces containing that path Worktree?
  - sticky last-selected Space?
- S1 ships MCP Space-scoped reads. Without this mapping, the caller model in §4–5 is incomplete.

**C. Migration inventory incompleteness (§3 vs §5 vs mail brief)**

- §5: delete Space-keyed Git claims / `mark_missing_worktrees` / conflict updates that assign repo groups.
- §3 lists worktree column drops and junction/canvas; does **not** list `DROP space_git_identity` or `space` column reshape (`archived` → `is_default`, nullable `name`).
- Proof §8.1 says “restores durable Space” without enumerating identity table removal.
- **Half-specified migration surface** relative to the runtime-only Git claim. Implementers will invent the drop list.

**D. Default Space uniqueness (§1 schema)**

- `is_default boolean` with no partial unique `(owner) WHERE is_default`.
- Idempotent “ensure default Space” (§5, proof 2) needs a hard uniqueness rule or an explicit singleton claim algorithm. Missing from schema block.

**E. Inconclusive classification on reconcile write path (§2 vs §5)**

- Reads: isolate inconclusive path, no writes.
- Reconcile: classify → upsert path identities. Behavior when stage-1 is `inconclusive` (skip, fail closed, leave prior row) is not stated. Risk of half-applied reconcile.

**F. MCP `refresh` “should leave the contract” (§5)**

- Ambiguous: keep flag as no-op, remove flag, or keep Director reconcile only via separate tool. Minor wording gap; not model-breaking if read = no write.

**G. Stamps (§3 durable stamps vs external brief “uuid→text”)**

- Proposal: stamps remain FK-free UUID Space/Worktree/Canvas, unchanged.
- Ignore brief wording if it implies text repo labels; **proposal itself is consistent** that stamps stay durable UUIDs, not `repo_group_key`.

### No internal contradiction on plain→Git (§6)

The walkthrough matches the invariant: labels change, IDs and membership do not. Pair FK rollback class of bugs dissolves as claimed.

---

## 2. Migration 0030 realism (off 0029, drop-and-recreate)

### Applicable shape (inferred, must be explicit in migration plan)

Assuming **rewrite 0030 content** (baseline already has a different 0030; private reset OK):

1. Drop `canvas`, `space_worktree`, `space_git_identity` (and dependent FKs/triggers/functions from prior 0030 drafts).
2. Reshape or recreate `space` with `is_default`, nullable `name` (drop `archived` if removed).
3. Create `space_worktree` without `space_id`, without four runtime columns; keep path/workspace uniqueness, root_canvas_id, provenance, lifecycle.
4. Create `space_worktree_link`.
5. Create `canvas` with `anchor_worktree_id`, parent scoped by `(owner, anchor_worktree_id)`, shape CHECK, pair triggers on anchor axes.
6. Deferred root FK `(owner, worktree_id, root_canvas_id)` → `(owner, anchor_worktree_id, canvas_id)` NO ACTION.
7. Anchor FK ON DELETE CASCADE; default_worktree FK deferred NO ACTION.
8. Session/run stamp columns remain nullable UUID-ish free columns (no new FK).

### Consistency

- Circular root pair remains DEFERRED; same transaction insert still works (proof 6).
- Dropping runtime columns is compatible with projection-only branch/HEAD/primary/missing.
- Junction empty in S1 is fine (table reserved).
- **Not fully specified for apply:** explicit `space_git_identity` drop; `space` column list; downgrade symmetry; trigger function rewrite for anchor axes (current function uses `space_id`).

### Applyable off 0029?

**Yes, if 0030 is a clean rewrite** from foundation tables at 0029 (`space`, `space_git_identity`, legacy worktree/canvas from 0006).  
**Risk:** environments that already applied intermediate 0030 shapes need full reset (stated product posture allows no backfill). Document “replace revision body; wipe local DBs.”

### Stamp “uuid→text”

Proposal keeps UUID stamps. Do **not** widen to text repo keys in 0030 without a separate decision; that would reintroduce identity ambiguity.

---

## 3. ~52 symbols realism

Rough production surface if built as written:

| Area | Likely symbols (order of magnitude) |
| --- | --- |
| Migration 0030 + triggers | 5–10 |
| Detection classifier + enrichment | 10–20 |
| Models Stored/Projected + records | 8–12 |
| Store (membership reads, ensure default, upsert, roots, drop git claim) | 12–20 |
| `projection.py` | 5–10 |
| Service (reconcile, reads, caller resolve rewrite) | 10–15 |
| REST/MCP adapters | 8–12 |
| Launch resolution / stamps call sites | 3–6 |
| `@tm/core` DTOs/transport | 5–10 |
| Browser switcher/read plumbing | 5–15 (if counted) |

**52 production symbols is a floor, not a ceiling.** Under-counted if browser Space switcher, `resolve_workspace_caller`, session list filters, director projection rewrite, and test-only helpers are excluded. Not a design falsifier; treat as **~1.5–2×** for planning and slice the detection classifier + migration as separate risk.

Proof list of 12 items is better scoping than the symbol count.

---

## 4. Persisted git / membership leaks (“runtime it is”)

### Clean relative to claim

- Dropping `branch_name`, `head_oid`, `is_primary`, `missing` from durable Worktree.
- No detection writes to `space_worktree_link`.
- `repo_group_key` only on projected DTO.
- Stamps stay durable Space/Worktree UUIDs, not repo group strings.
- Root name frozen at create from path/slug, not branch.

### Residual leak risks

1. **`workspace_slug` / `workspace_hash`** remain durable path identity (correct) but must not be overloaded as “git repo key.” Keep generation path-canonical, not common-dir-canonical, or plain→Git would still rewrite identity — doc says path identity fields refresh on upsert; confirm hash is **path-stable** across `git init` at same path (if hash is path-based, OK; if ever derived from git common dir, **contradicts** §6).
2. **Any remaining `space_git_identity` or claim table** would reintroduce Space←Git authority; must be dropped and call sites deleted (§5 says so; migration list incomplete).
3. **Conflict upsert that rewrites organizational fields** must not reappear; doc forbids; code review must enforce.

Primary residual design leak: **path identity upsert semantics** must guarantee path-stable IDs across Git classification change (implied by §6, not proven in schema text).

---

## 5. Findings ranked

| Sev | Section | Fact |
| --- | --- | --- |
| **Major** | §3 three-axis + pane rules | “Same durable Space” for `default_worktree_id` / panes has no formal membership predicate after removing `space_id` from Canvas/Worktree. |
| **Major** | §5 / §7 caller model | MCP/control-plane `workspace_id` → `allowed_space_id` undefined once Worktree loses `space_id`. |
| **Major** | §3 vs §5 / §8.1 | Migration omits explicit `space_git_identity` drop and `space` column reshape while reconciling deletes Space-keyed Git claims. |
| **Major** | §1 schema | `is_default` lacks uniqueness / singleton constraint for ensure-default. |
| **Major** | §2 vs §5 | Inconclusive classification behavior on reconcile write path unspecified. |
| Minor | §5 | MCP `refresh` “leave the contract” ambiguous (no-op vs remove). |
| Minor | §9 | ~52 symbols under-counts detection + caller rewiring + browser. |
| Watch | §3 / §6 | Path `workspace_*` stability across plain→Git must be guaranteed or M4 returns as ID churn. |

---

## 6. Recommendation

**Do not block the organizational direction.** Lock before implement:

1. S1-only: single default Space; `allowed_space_id` = that default; same-Space checks = owner Worktree set (document as temporary).
2. Post–Space-CRUD: explicit membership predicate for defaults and panes (caller-selected Space recommended).
3. Migration checklist: drop `space_git_identity`; reshape `space`; rewrite pair triggers on anchor axes; reset local DBs.
4. `UNIQUE (owner) WHERE is_default` (or equivalent claim).
5. Reconcile: inconclusive → no durable write (or fail closed); never flip path identity to a new ID on `git init`.
6. Plan symbols against the 12 proofs, not the “52” headline.

Until (1)–(5) are one-liners in the proposal, treat as **major open design**, not implementation-ready.
