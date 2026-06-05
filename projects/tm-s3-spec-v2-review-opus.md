# S3 spec v2 — Opus architect review (domain-model / cascade lens)

Reviewer: `multi-launch:general:1:3.4` (Opus)
Target: `~/.mdx/projects/tm-s3-spec-v2.md`
Authority: cm `019f918b-c4e0-7633-bfec-d7a86466fe28` (domain model CONFIRMED) + `019f9016-6595-7470-b11c-745e15f687b7` (delete/GC CONFIRMED)
Date: 2026-07-24

## Verdict: APPROVE-WITH-CHANGES

The confirmed domain model is stated faithfully. §0–§2 and §4 match the CONFIRMED entity/cardinality/cascade model exactly. No lingering orphan / reference-count / catch-all-default language survives as live behavior — every occurrence ("No orphaning to Default", "No reference-counting", "not computed-all membership", "orphan fall-back (superseded)") is a **prohibition**, not a live rule. Workdir is never conflated with OS dir (§0 line 20, §4 line 112). TM is correctly detection-only everywhere git worktree is named (§1 line 48, §6 line 147, §8 line 169) — no claim TM runs `git worktree add/remove/move`. No write-once / identity contradiction with S1.

No blockers: nothing in the spec **contradicts** the confirmed model. The two majors are completeness/contract-clarity gaps against the settled decisions that will misdirect a builder if left implicit.

Counts: **0 blockers, 2 majors, 2 minors.**

---

## Majors

### M1 — Cascade "delete runs" does not state that session / wire IR history is PRESERVED
- **Where:** §2 "DELETE workdir" (line 57 "stop **that workdir's** gateway-managed runs") and "DELETE Space" (line 64). §4 test list (line 120).
- **Problem:** The spec says delete "cascades … + runs" and the header framing is "hard-delete DB rows", but it never says WHICH rows. The CONFIRMED delete decision (`019f9016…`) DB-side note is explicit: *"keep normalized IR … don't delete DB IR."* So on delete the run process is **stopped** and (S3b) its tier-1 raw is GC'd, but the persisted session/wire transcript IR in the session store is **retained**. The spec's silence sits between two authoritative signals (brief: "hard-delete DB rows"; cm: "don't delete DB IR") and a builder will guess. This is the single most likely footgun — wrongly hard-deleting transcript history.
- **Fix:** State in §2 that cascade delete hard-deletes the **inventory** rows (space / workdir / canvas) and stops runs, while **session / wire transcript IR is intentionally retained** (only tier-1 raw is reclaimed, S3b). Add a test asserting session IR survives a workdir/space delete.

### M2 — S3b omits the dangling-run-dir SWEEP command and the shared `storage/tier1_gc.py` primitive
- **Where:** §5 table (Trigger row, line 128: "One: managed run teardown") and §6 slicing S3b (line 145). §7 reuse table names only `storage.disk_helpers (optional)` (line 161).
- **Problem:** The CONFIRMED decision defines S3b as *"dev_mode flag + tier1_gc primitive + run-end & target-delete triggers + dev-gate runtime-home + **dangling-sweep command**"* and mandates *"one storage/tier1_gc.py … reused by run-end, target-delete, and the sweep. **Not three copies.**"* It also rules: *"if a run won't stop, preserve its dir (sweep later)."* The spec drops both the sweep command and the named shared primitive. Without the sweep, the "run won't stop → preserve dir" branch has **no reclamation path** — that is disk-level orphaning, which the model forbids. The DRY constraint (one primitive, not three) is also unstated, inviting the exact triplicated-rmtree the decision prohibits.
- **Fix:** Add the dangling-sweep maintenance command and the shared `storage/tier1_gc.py` primitive (best-effort staged rmtree, dev-gated, containment-checked, dedup by canonical path) to S3b in §5/§6/§7, and state the "won't-stop → preserve → swept later" branch.

---

## Minors

### m1 — Canvas "anchored to exactly one workdir" invariant not cited (S1b `canvas_worktree_mismatch`)
- **Where:** §0 line 27 ("Canvas — anchored to a workdir").
- **Problem:** Cascade correctness ("delete workdir → its canvases") is only unambiguous because a canvas belongs to **exactly one** workdir. The spec states anchoring but never invokes the S1b `canvas_worktree_mismatch` invariant that guarantees the "exactly one". The chain in line 29 implies it; making it explicit closes the cascade contract.
- **Fix:** Note the canvas↔workdir anchor is enforced by the S1b `canvas_worktree_mismatch` invariant (exactly one worktree per canvas), which is what makes the delete-workdir canvas cascade well-defined.

### m2 — Target-delete active-run ordering/"won't-stop" branch under-specified
- **Where:** §2 line 59 ("Tier-1 GC: via run-end teardown when those runs terminate"), §5 line 128.
- **Problem:** The CONFIRMED ordering rule is captured for the happy path (teardown GC fires after drain, §3), but the target-delete-of-active-run sequence the decision spells out — *"stop → run ends+drains → then GC; if a run won't stop, preserve its dir (sweep later)"* — is not stated. Pairs with M2.
- **Fix:** State the target-delete sequence explicitly (stop → drain → GC; non-stopping run → preserve, defer to sweep).

---

## Confirmed-faithful (for the record)
- Workdir → Space N:1; OS dir → workdir 1:N; multi-Space same path = multiple workdir rows (§0, §4). ✓
- Delete Space cascades ALL workdirs, no orphaning to Default, no ref-counting, no fall-back (§2). ✓
- Default Space auto + undeletable + NOT catch-all; bootstrap ≥1 Space (§0, §4). ✓
- MCP full CRUD day 1; CMDK "Create new space" only until >1 Space (§2, §4). ✓
- OS dir never touched; TM detection-only (§0, §1, §6, §8). ✓
- dev_mode flag: net-new `Settings.dev_mode` → `TRANSPORT_MATTERS_DEV_MODE`, don't reuse `debug`/`channel` (§5). ✓
