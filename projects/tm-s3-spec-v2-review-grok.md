# S3 Spec v2 Review — Grok (large-context lens)

- **Artifact**: `~/.mdx/projects/tm-s3-spec-v2.md`
- **Date**: 2026-07-24
- **Reviewer**: `multi-launch:general:1:3.3` (grok)
- **Lens**: gaps, edge cases, internal contradictions, over-engineering; cross-check superseded specs and cm decisions
- **Gates**: not run (spec review; no tree writes)
- **cm inputs**:
  - `019f918b-c4e0-7633-bfec-d7a86466fe28` Space/Workdir/OS-dir domain model (CONFIRMED)
  - `019f9016-6595-7470-b11c-745e15f687b7` Delete GCs tier-1 (no finalization gate)
  - `019f9195-e91b-76f3-b444-21d813dfe169` DEFERRED workdir health/status (status is a LOG)

## Verdict

**approve with majors** — domain cascade and finalization drop match the confirmed model; status is correctly out of scope. Three majors must land as short, explicit callouts (or adjudicated defaults) before S3a implementation, or implementers will re-invent scout machinery / re-open settled forks.

| Severity | Count | Summary |
|----------|------:|---------|
| blocker | 0 | — |
| major | 3 | stop order + stop-failure; dangling tier-1 coverage vs cm; `default_worktree_id` FK clear |
| minor | 4 | last/empty default workdir; session tombstones; create-workdir ownership; CMDK “switch” |
| nit | 2 | link/unlink retirement explicitness; baseline SHA drift |

## Lens checklist

| Check | Result |
|-------|--------|
| OS dir ≠ Workdir; Workdir N:1 Space; multi-Space = multiple workdirs | **PASS** — §0 table + diagram; cm 019f918b restated accurately |
| Delete cascades (Space→workdirs→canvases+runs; Workdir→canvases+runs); no orphan/refcount/catch-all | **PASS** — §2; non-goals §8 |
| Default Space undeletable, not catch-all | **PASS** — §0, §2, checklist §9 |
| Detection-only git; never rmtree user OS dir | **PASS** — §0, §2, non-goals, tests note §4 |
| Tier-1 GC on existing run-end teardown; no finalization / `run_capture_state` / coordinator | **PASS** — §3, §5, non-goals; scout finalization model not reintroduced |
| Workdir health/status DEFERRED; status is a LOG | **PASS** — §8 item + §8A (principles only, no schema/stream design) |
| Superseded specs overwritten (no silent re-import of computed-all / link-only Space delete) | **PASS** — v2 body clean; `tm-s2-s6-replan-architect.md` §3 and `tm-space-crud-spec-v1.md` §3–4 carry SUPERSEDED banners pointing at v2 |
| Over-engineering hunt (scout finalization barrier, deletion coordinator as product gate, purpose-specific preserve flags) | **PASS** — dropped; S3b is light latch + containment |
| Edge cases called by brief (active runs, shared OS dir, default delete, last workdir in default) | **PARTIAL** — shared OS dir + default lock covered; active-run stop policy and last-workdir empty default unstated (see majors/minors) |

## Confirmed-model coherence

v2 §0–§2 match cm **019f918b** entity/cardinality and cascade text almost line-for-line. Progressive disclosure (MCP full day 1; CMDK create-only until >1 Space) matches. Desktop/gateway-only scope matches.

v2 §5 matches the **finalization drop** in cm **019f9016** (no `run_capture_state`, no certified barrier). Single flag `Settings.dev_mode` / `TRANSPORT_MATTERS_DEV_MODE`; do not reuse `debug`/`channel`. Containment under `default_workspaces_root()`; skip custom `--storage-dir` outside (open fork A, settled as skip).

v2 §8A matches cm **019f9195**: out of S3; status = append-only LOG; health is OS-dir property with fan-out; no schema invented here.

## Superseded-spec leak scan

| Source | Stale claim | Leak into v2? |
|--------|-------------|---------------|
| `tm-s2-s6-replan-architect.md` §3 | Space delete cascades **links only**; worktrees survive under computed-all default; link/unlink M:N | **No** — banner SUPERSEDED; v2 §2 cascades workdirs |
| `tm-space-crud-spec-v1.md` §3–4 | `remove_worktree_link` leaves worktree in default; delete_space links-only | **No** — banner SUPERSEDED; v2 does not re-spec link/unlink as multi-Space story |
| `tm-s3-scout.md` finalization | `run_capture_state`, strict barrier, unfinalized skip GC | **No** — v2 §5 / non-goals kill it |
| Scout Space delete | Keep Worktree/Canvas rows after Space delete | **No** — v2 cascades workdirs |
| Scout Worktree delete FK note | Clear foreign `default_worktree_id` before delete | **Gap** — real seam still true at HEAD; v2 silent (M3) |

Body text under superseded banners remains historically wrong; that is fine if implementers treat banners as hard stops. v2 is the forward authority for S3 domain.

## Over-engineering hunt

Correctly **not** present in v2:

- Durable finalization / `run_capture_state` / commit barrier as GC gate
- Heavy `SpaceDeletionCoordinator` product object as the only path (scout)
- Soft-delete / reference-counted orphan collect / fall-back to Default
- Git `worktree add|remove|move` product ops
- Workdir health stream schema in this slice
- Purpose-specific “preserve tier-1” flag parallel to `dev_mode`

Lean shape that should stay: STEP-0 extract → domain-aligned ownership → cascade delete+stop (S3a) → latch GC on existing ExitStack (S3b). Do not re-import scout’s finalization tests as S3b acceptance criteria.

## Blockers

None. Domain model and finalization drop are sound enough that a careful implementer reading cm + v2 would not ship the wrong cascade or a finalization gate.

## Majors

### M1 — Active-run delete: stop order and stop-failure policy unstated

- **Spec**: §2 Delete workdir / Delete Space / Run-stop isolation; §3 teardown chain; §6 S3a “stop runs”
- **Exact text**: “Cascade: canvases … + stop **that workdir's** gateway-managed runs.” / “Cascade ALL of its workdirs → each workdir's canvases + runs” — no order, no failure mode.
- **Why major**: Deleting DB inventory while a managed run is still writing is a real race. cm **019f9016** already adjudicates: stop → drain → GC on teardown; **if a run will not stop, preserve its dir (sweep later)**; open fork D = best-effort continue. Scout’s “stop then commit DB mutation” order is still the safe shape even without a named coordinator. Without text, implementers re-open the fail-whole-delete vs best-effort fork or invent a coordinator to “be safe.”
- **Required addition (S3a)**: Explicit sequence — (1) list managed runs by space/workdir id, (2) request terminate, (3) DB cascade mutation (best-effort even if some stops fail), (4) GC only via run-end teardown for runs that actually settle; stuck-run dirs preserved. No second filesystem GC invent in S3a.

### M2 — Dangling / already-dead tier-1 coverage vs cm (sweep / multi-trigger)

- **Spec**: §5 “Trigger \| One: managed run teardown”; “Delete role: Ends runs → teardown fires GC; no parallel invent”; S3b row in §6
- **cm 019f9016**: run-end **and** target-delete GC **and** “separate maintenance command sweeps dangling orphan run dirs”; shared `storage/tier1_gc.py` primitive; S3b includes dangling-sweep.
- **Why major**: Teardown latch is the right **primary** and correctly kills finalization over-engineering. It does **not** reclaim: (a) pre-S3b leftover run dirs, (b) crash paths where `CapturedRunLease.close` never ran, (c) stop-failure preserves from M1. v2 neither restores the sweep nor **explicitly defers** it with a non-goal / later-slice line. That ambiguity will re-expand S3b toward scout weight or leave permanent disk leaks unowned.
- **Required addition**: Either (preferred for light S3b) keep single trigger + add non-goal / follow-on: “dangling sweep command deferred; not S3b acceptance”; or restore a minimal prod-only sweep as S3c one-liner. Shared `tier1_gc.py` is optional if ExitStack callback reuses `disk_helpers` containment — do not invent three GC copies.

### M3 — `default_worktree_id` cross-workdir FK clear missing from cascade notes

- **Spec**: §2 cascade canvases; §4 implementation notes (schema rename / N:1 ownership) — no FK ordering
- **HEAD fact** (scout + current store/models): user canvases may set `default_worktree_id` to **any owner worktree**; `canvas_default_worktree_fk` is deferred NO ACTION class behavior in the reshape era — delete of a workdir that is only a *default pointer* on a canvas anchored elsewhere can fail the transaction.
- **Why major**: Under confirmed multi-workdir same-OS-dir and multi-Space setups, cross-workdir defaults remain plausible. S3a `delete_workdir` that only `DELETE space_worktree` + rely on anchor cascade will hit FK failures scout already named. N:1 ownership does not remove the pointer problem.
- **Required addition (S3a STEP-0 / store)**: In the delete-workdir transaction, clear (or null) foreign `canvas.default_worktree_id` rows pointing at the target **before** deleting the workdir row; then cascade anchored canvas tree. Test: “default pointer from canvas on workdir A → workdir B; delete B succeeds; A’s default cleared.”

## Minors

### m1 — Last workdir in Default Space / empty Default

- **Spec**: §0 “need ≥1 Space to create any workdir”; §2 Default cannot be deleted
- **Gap**: Deleting the last workdir **inside** Default is unstated. Model implies empty Default is fine (Default exists so a Space always exists for future creates, not so it always holds workdirs).
- **Suggestion**: One line: empty Default allowed; deleting last workdir in Default is a normal workdir delete.

### m2 — Session / lifecycle tombstones after cascade

- **Spec**: silent
- **Scout / prior model**: sessions carry FK-free `space_id`/`worktree_id` stamps and survive inventory delete (tombstones for history).
- **Suggestion**: State that session + `run_lifecycle_event` rows are **not** cascade-deleted with workdir/space; affinity stamps remain historical. Avoids implementers adding FK CASCADE on session by accident.

### m3 — Create-workdir under N:1 (path identity + owning Space)

- **Spec**: §2 MCP “create/list/delete workdir”; §4 multi-Space = multiple workdir rows
- **Gap**: Create semantics (required `space_id` + OS path; detection-only validate path exists; second Space gets a **new** workdir id for same path) are implied by §0 but not operationalized. Rename of workdir/path move out of scope is fine; create ownership is day-1 MCP.
- **Suggestion**: Short create contract bullet: always takes owning `space_id`; never auto-joins Default via computed-all; duplicate path in same Space = upsert/idempotent or conflict (pick one).

### m4 — CMDK “switch” after >1 Space

- **Spec**: §2 “list/rename/delete/**switch** appear”
- **Gap**: “Switch” is not defined (active Space selection? focus?). Risk of scope creep into placement-panel UX.
- **Suggestion**: Define as “select active Space for desktop context” or drop the word until a UX slice owns it.

## Nits

### n1 — Explicit retirement of link/unlink API names

- §2 MCP lists create/list/delete workdir, not `space_link_worktree` / unlink. Good. One non-goal line (“no M:N link/unlink surface; membership is ownership”) would kill residual reading of space-crud-spec body under the SUPERSEDED banner.

### n2 — Baseline SHA

- Header baseline `7ffba78b`; branch has moved (affinity etc.). Fine for domain; re-stamp HEAD at implementation kickoff.

## Deferred status scoping

§8A is correctly **out of S3**. Headline principles match cm **019f9195** (LOG not snapshot; health on OS dir; live stream later). Draft state set and open questions stay in cm, not expanded into this spec. **No finding** that status leaked back into S3a/S3b deliverables.

## S3a / S3b split assessment

| Slice | v2 intent | Assessment |
|-------|-----------|------------|
| S3a | STEP-0 extract; N:1 ownership; delete cascade + stop; MCP+REST; tests | Sound **if M1 + M3 text land**; no filesystem |
| S3b | `dev_mode`; latch tier-1 + runtime-home GC on teardown; containment; light tests | Sound primary path; resolve M2 (defer sweep vs include) so S3b stays light |

## Recommended minimal v2 edits (for author, not this reviewer)

1. §2: stop-then-mutate order + best-effort stop-failure (M1).
2. §5 or §8: dangling sweep deferred/non-goal **or** S3c one-liner (M2).
3. §4 / S3a tests: clear foreign `default_worktree_id` (M3).
4. Optional minors: empty Default ok; session tombstones retained; create-workdir ownership bullet.

## Summary for orchestrator

Domain and cascade rewrite succeed; finalization and health correctly out. Three majors are missing operational edge adjudications already settled in cm (stop failure, dangling coverage ownership, FK clear). No blockers. Spec is close to Stuart-ready after short callouts, not a rewrite.
