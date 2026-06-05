# Transport Matters docs sweep — integrity verification

- **Verifier role:** structural integrity + TLDR judgement (not content-loss audit)
- **Branch:** `docs/sweep` head `1c3e339b5d30a345a3b041d9a8cbb370470957f4` vs `main` `af52318d`
- **Worktree:** detached `/tmp/tm-sweep-int` (removed after report)
- **Constraint:** read-only except worktree add/remove

## Verdict

**Issue (medium):** `docs/PERFORMANCE.md` has zero inbound markdown links after the sweep deleted its only referrer, `docs/TEST.PERFORMANCE.md`.

Everything else in scope is clean: link resolution, deleted-path references, TLDR agent contract, NOW pure-TODO shape, DESIGN pointer, branch file scope.

---

## 1. Link and reference integrity

### Relative markdown links

- **Links checked:** 35 unique relative markdown links across non-symlink `.md` files (excluding `api/tests/fixtures/**`, `NOTES/`, `TMP/`, `**/.archive/**`, `.warroomagents/`)
- **Broken:** 0
- Upward traversals from `docs/plans/` (e.g. `../LAUNCH-CONTRACT.md`, `../../NOW.md`) resolve
- `docs/process/` has no outbound relative doc links

### Deleted / moved path references

Searched code, tests, docs, `.github/`, justfiles, `pyproject.toml`, `package.json`, and other text tooling for:

| Term | Non-excluded hits | fixtures | NOTES/TMP | `.archive/` content |
|------|-------------------|----------|-----------|---------------------|
| `COMPATIBILITY-PUBLISHING` | 0 | 0 | 0 | 0 |
| `TEST.PERFORMANCE` | 0 | 0 | 0 | 0 |
| `CONTROLPLANE-OBSERVATION-PLAN` | 0 | 0 | 0 | 0 |
| old root `docs/plans/CONTROLPLANE-OBSERVATION-PLAN.md` as a live path | 0 (file lives only at `docs/plans/.archive/CONTROLPLANE-OBSERVATION-PLAN.md`, R100 rename) | | | |

`api/src/transport_matters/harnesses/certification.py` docstring was repointed from `COMPATIBILITY-PUBLISHING.md` to `HARNESS-COMPATIBILITY.md` (allowed exception).

Bare path mentions outside markdown links that fail to resolve under repo root:

- `NOW.md` → `~/.mdx/projects/tm-tier2-bounded-pool-design.md` (intentional home-path design note, not a repo link)
- `docs/NORTHSTAR.md` → `~/.mdx/projects/transport-matters-north-star.md` (same)

---

## 2. TLDR.md priority judgement

### Symlinks

| Path | Target | Resolves |
|------|--------|----------|
| `CLAUDE.md` | `TLDR.md` | yes |
| `AGENTS.md` | `TLDR.md` | yes |
| `Agents.md` | `TLDR.md` | yes |

Line count: **89 → 63** (matches brief).

### Required concepts (agent with no other context)

| Concept | Present? | Where |
|---------|----------|--------|
| Workspace identity by canonical path | yes | Mental Model: identity is the canonical target path, not the slug |
| Wire-versus-transcript distinction | yes | turn definition; difference is the product |
| Where Tier-1 lives | yes | `<channel home>/workspaces/{slug}/{hash}/{run}/` |
| What a breakpoint is | yes | holds next outbound turn for review/edit before release |
| Owner / Space / Worktree / Canvas hierarchy | yes | Hierarchy paragraph + domain packages |
| Pointer to `docs/ARCHITECTURE.md` | yes | header “Decisions” link |

Also still present and useful: launch paths, channels isolation, Postgres/`SessionWriter`, canvas vs CLI + `prepare_captured_run`, process-resident runs, capture vs product planes, `doctor`, tree orientation for placement.

### Cuts that an agent would actually need?

**None that rise to a mistake-risk finding.** Notable removals and why they are acceptable:

- **Route inventory** (`/runs`, `WS /runs/{id}/terminal`, `DELETE /runs/{id}`, dock minimize vs close) — correctly cut; belongs in architecture/API docs, not every-turn TLDR.
- **Changelog substrate** (`#259`, migration `0008_wire_store`, “retired legacy index…”) — correctly cut; residual one-liner (“wire bytes written; need a read surface”) is enough.
- **WWW naming essay** (shell dev-composer, gateway wheel embed D1-b) — thinned to tree orientation. Placement still clear; deep packaging detail lives under ARCHITECTURE/WHEEL.
- **“No sudo / no system proxy”** install posture — mild loss for ops onboarding, not for in-repo coding mistakes; QUICKSTART/CHANNELS cover install.

### Still present that is changelog or route inventory?

**No.** Remaining “status” lines are durable product truth (wire store write-only; Codex incremental payloads), not PR archaeology. Tree orientation is placement, not a route list.

**Judgement:** TLDR remains a safe every-session load for agents about to write code here.

---

## 3. NOW.md pure-TODO

- Line count: **496 → 356**
- Structure: North Star → multi-launch goal → Phases 1–5 open work → Deferred with re-entry triggers → Parking lot
- **No “recently completed” section** and no residual `SHIPPED` / “Slice N shipped” headings (those existed on `main` under Phase 1.2 / 1.4 and are gone)
- Only “shipped” word hits:
  - Meta rule: file is not a history of shipped work
  - Product decision: matrix is “not shipped with releases” (distribution posture, not a completion log)
- Local unit loop goal is a single parking-lot bullet: “Local unit loop of 30 seconds or less, without removing slower regression coverage from the full gate” — **no historical timings or counts** attached
- (Unrelated open-work estimate still in Phase 5 for the bounded proxy pool: `~4 engineer-days / ~650 LoC / 3 PRs` — not on the 30s goal; not a pure-TODO violation of the stated rule)

**Judgement:** NOW is strictly live work + deferred parking lot.

---

## 4. Orphans and DESIGN pointer

### DESIGN.md

- `docs/ARCHITECTURE.md` links: “Visual principles: [DESIGN.md](./DESIGN.md)”
- Inbound confirmed: `docs/ARCHITECTURE.md` → `docs/DESIGN.md`

### Docs with zero inbound markdown links (HEAD)

| Path | Sweep-introduced? | Notes |
|------|-------------------|--------|
| `docs/PERFORMANCE.md` | **yes** | On `main`, sole inbound was `docs/TEST.PERFORMANCE.md`. Deleting that file left PERFORMANCE unreachable. No replacement pointer from ARCHITECTURE, NOW, README, or PERFORMANCE’s peers. |
| `docs/WHEEL.md` | no (pre-existing) | Zero inbound on `main` as well |
| `docs/process/WARROOM.md` | no (pre-existing) | Process doc; no in-repo markdown hub |
| `docs/process/AGENT-PROFILES.md` | no (pre-existing) | Same |

Other zero-inbound files are expected entry points or package-local agent files (`TLDR.md`, `README.md`, `LESSONS.md`, `**/CLAUDE.md`, fixture READMEs), not product docs the sweep was meant to re-home.

**Finding:** PERFORMANCE orphan is the integrity miss for check 4.

---

## 5. Branch file scope

`git diff --name-status af52318d..HEAD` (18 paths):

- Docs/root markdown only, plus rename `docs/plans/CONTROLPLANE-OBSERVATION-PLAN.md` → `docs/plans/.archive/CONTROLPLANE-OBSERVATION-PLAN.md`
- Deletes: `docs/COMPATIBILITY-PUBLISHING.md`, `docs/TEST.PERFORMANCE.md`
- **Single non-doc change:** `api/src/transport_matters/harnesses/certification.py` — one-line docstring path repoint (`COMPATIBILITY-PUBLISHING.md` → `HARNESS-COMPATIBILITY.md`)
- **No test changes, no fixture changes, no other code**

**Judgement:** scope rule held.

---

## Summary table

| Check | Result |
|-------|--------|
| Relative md links resolve | pass (35 checked, 0 broken) |
| No live refs to deleted/moved paths | pass |
| TLDR symlinks | pass |
| TLDR agent contract | pass |
| NOW pure-TODO | pass |
| DESIGN inbound from ARCHITECTURE | pass |
| No unexpected code/test/fixture edits | pass |
| No orphans | **fail** — `docs/PERFORMANCE.md` |

## Suggested fix (out of verifier scope)

Add one durable inbound to `docs/PERFORMANCE.md` (e.g. from `docs/ARCHITECTURE.md` or a single line under NOW’s deferred/parking area if performance work is live), mirroring the DESIGN pointer pattern used in this sweep.
