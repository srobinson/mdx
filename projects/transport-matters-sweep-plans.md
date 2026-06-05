# Scout report: `docs/plans/` (transport-matters)

Tree: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` at `af52318d` (main).
Lens: docs guide; code is truth; plans that describe shipped work are stale roadmaps.
Assessed: 4 docs, 2,070 lines. Proposed net cut from this cluster: **~1,160 lines**.

## Summary

| Path | Lines | Status | Disposition | Proposed lines after |
|------|------:|--------|-------------|---------------------:|
| `docs/plans/CONTROLPLANE-OBSERVATION-PLAN.md` | 444 | **SHIPPED** | **ARCHIVE** → `docs/plans/.archive/` | 0 active |
| `docs/plans/RUNTIME-SURFACING-S1-PLAN.md` | 609 | **STILL AHEAD** | **KEEP AS IS** | ~609 |
| `docs/plans/RUNTIME-SURFACING-S2-PLAN.md` | 313 | **PARTIALLY SHIPPED** (most substrate; open: enforcing flip, Grok E2E, two seams) | **TRIM** to ~90 | ~90 |
| `docs/plans/RUNTIME-SURFACING-PLAN.md` | 704 | **PARTIALLY SHIPPED** (S0 wedge + S2 substrate; S1/S3–S5 still ahead) | **TRIM** to ~180 | ~180 |
| **Cluster total** | **2070** | | | **~879** |

`NOW.md` does **not** name any of these plans. Current focus is first-run/settings (#353/#354), launch truthfulness, and `launch_batch`. Living contracts: `docs/CONTROLPLANE.md`, `docs/HARNESS-COMPATIBILITY.md`, `docs/LAUNCH-CONTRACT.md`.

---

### `docs/plans/CONTROLPLANE-OBSERVATION-PLAN.md` (444 lines)

- **Status:** SHIPPED
- **Evidence:**
  - S1 conversation: PR `#287` (`feat: add durable conversation observation`); `ControlPlaneService.conversation` reads the gateway conversation port, not `read_store.timeline`; skins on REST/MCP.
  - S2 watch: PR for canonical watch completion; `controlplane/watch.py` and siblings (`watch_models`, `watch_registry`, `watch_delivery`); Activity cursors and display turns live in the control plane.
  - S3 correlated wait: PR `#290` (`feat(controlplane): add correlated reply waits`); migration `0019_control_plane_delivery`; modules `delivery_store.py`, `delivery_wait.py`, `delivery_binding.py`, `delivery_proof.py`; `ControlPlaneService.wait_for_reply` plus REST/MCP skins.
  - Product contract already relocated into `docs/CONTROLPLANE.md` (conversation paging, `max_chars_per_message`, `rotated=true`, delivery ledger without raw prompt text, wait outcomes, subscribe-then-reread correctness).
  - `NOW.md` does not reference this plan; open work is delivery *claim* path quality (`envelope._extract_launch_delivery_id` vs `LivePromptDeliveryBindings.claim`), not observation product design.
- **Disposition:** ARCHIVE (historical record, move to `docs/plans/.archive/`)
- **Survives:** Nothing as an active plan. Decisions already live in `CONTROLPLANE.md`.
- **Cuts:** Entire file from the active tree (444 lines). Keep the archive only if git history alone is insufficient for archaeology.
- **Decision rescue:** None. The durable contracts (opaque conversation positions, display turns vs cursors, ambient watch vs delivery-scoped wait, delivery ledger stores digest not text, actor-scoped wait) are already in `CONTROLPLANE.md`. The plan's implementation sequence and verification matrices are historical.

---

### `docs/plans/RUNTIME-SURFACING-S1-PLAN.md` (609 lines)

- **Status:** STILL AHEAD
- **Evidence:**
  - Plan completion criteria require: content-addressed `AgentRevision` / `RuntimeBuild`, atomic catalog import, deletion of `capabilities.json` scans and the `RuntimeTemplate*` contract family.
  - **Absent in TM code:** no symbols `AgentRevision`, `RuntimeBuild`, `AgentCatalogSnapshot`, `RuntimeBuildRef` under `api/src/transport_matters` (ripgrep empty).
  - **Still present:** `runtime_registry.py` scans `runtime.toml` + `capabilities.json`; exports `RuntimeTemplateCapabilities`, `RuntimeTemplateListing`, `RuntimeTemplateSummary`, `RuntimeTemplateRef`, `RuntimeTemplateRegistryError`.
  - `agent_catalog.py` is an 18-line adapter: `load_agent_catalog` → `list_runtime_templates` → `AgentCatalogResult`. Not the immutable package importer described.
  - PR `#286` (`feat: surface managed agent runtimes`) is the S0-shaped wedge, not the package cutover.
  - External compiler path `~/.agent-runtimes/bin/generate.py` and source runtimes exist; production templates still ship `capabilities.json` beside `runtime.toml` (no `.packages/` / `.catalog/` publish tree in the default registry).
  - `NOW.md` does not schedule S1; multi-launch path assumes current catalog/readiness seams.
- **Disposition:** KEEP AS IS
- **Survives:** Whole document as the marker of the source → lock → revision → build → catalog cutover. This is legitimate plan content under the lens: direction code cannot state.
- **Cuts:** None recommended now. Optional later: drop the multi-step "Implementation sequence" file choreography if it starts lying after partial compiler work; keep Outcome, Source contract, Digest domains, Ownership, Flag day cutover, Completion criteria.
- **Decision rescue (only if this plan is later archived without shipping):**
  1. Domain-separated digest preimages (`tm.agent-source.v1`, `tm.agent-revision.v1`, `tm.runtime-build.v1`, …) and canonical JSON rules.
  2. Flag day cutover: no dual-read window; compiler + TM coordinated; delete `RuntimeTemplate*` and source scans in one delivery.
  3. Namespace authority is physical index source (`tm/*` built-in bundle vs `user/*` shared index), never package-asserted.
  4. Credential-free `RuntimeBuild` allowlist (no auth, sessions, trust, proxy keys in package trees).
  These do not appear in TM contracts today; they live only here (and partially in the external agent-runtimes tree).

---

### `docs/plans/RUNTIME-SURFACING-S2-PLAN.md` (313 lines)

- **Status:** PARTIALLY SHIPPED — substrate largely landed; enforcing rollout, Grok end-to-end, and two documented seams remain
- **Evidence (shipped):**
  - Descriptors: `harnesses/__init__.py` registers `claude`, `codex`, `grok`; `launch=None` on grok (discovery ≠ launch eligibility).
  - S2b releases: `compatibility_releases_v1.json` with active channel pointers for claude and codex on stable/preview; PRs `#293`–`#294`.
  - S2c observations/probes/connections: `harnesses/probes/`, `connections.py`, `connections_store.py` (`#294`, `#295`).
  - S2d blocks + drift: `blocks.py`, `blocks_store.py`, `drift_emitter.py` (`#296`, `#297`).
  - S2e compatibility facts + versioned reader dispatch: `compatibility_facts.py`; `historical_contract_unsupported` in `index/adapters` (`#298`).
  - S2f resolver + advisory gate: `resolver.py` (`launch_options`), `compatibility_service.py` with `COMPATIBILITY_ROLLOUT = "advisory"` (`#299`); enablement hard gate `#301`.
  - S2g inventory + certification path: `inventory.py`, `/v1/harnesses`, MCP projection (`#303`–`#308`); canvas harness cards `#353` and settings/readiness surface `#354` (product shape evolved from "setup route" to CommandCenter settings; plan text still says first-run setup route).
  - Access/authentication remain diagnostic in contract and code; enablement is the hard user gate.
- **Evidence (not shipped / open):**
  - `COMPATIBILITY_ROLLOUT` is still `"advisory"`; enforcing branch exists and is tested but not the shipped build state (plan S2g "flip to enforcing" incomplete).
  - S2h Grok: descriptor + probe only; no launch boundary, no wire/transcript adapters under `adapters/`, no grok release or channel state in embedded manifest (tests assert grok has no release).
  - Plan-documented follow-ups still true in spirit: session bootstrap production classifier gap (`CaptureLeaseRegistry.record_session_rejection` exists; harness exit taxonomy incomplete); wire drift still envelope-centric vs Codex per-item `extra_fields` (partially closed by S2g PR-A `#306` for vocabulary, but plan note remains a liability if treated as current open work without recheck).
  - Plan still lists implementation of items that already exist (descriptors, inventory, resolver) as future work → stale roadmap risk.
- **Disposition:** TRIM to ~90 lines
- **Survives:**
  - One-paragraph outcome: compatibility authority + inventory + pure resolver + one gate service.
  - Explicit remaining markers only: (1) one-way flip `advisory` → `enforcing` as a TM release property; (2) Grok launch profile + adapters + certified release + activation; (3) any still-true seam gaps after a fresh code check (bootstrap taxonomy, item-level wire allowlist) as bullets not prose.
  - Pointers to `HARNESS-COMPATIBILITY.md` and `COMPATIBILITY-PUBLISHING.md` as living contracts.
  - Decision already permanent in code/docs: discovery vs launch eligibility; access never authorizes launch; signature stub rejects unsigned cache updates.
- **Cuts:**
  - All shipped sub-slice narratives S2a–S2f and most of S2g as "to do" text (~200+ lines).
  - Probe contract tables, ownership tables, and data placement already mirrored in `HARNESS-COMPATIBILITY.md` / code modules.
  - Completion criteria checklist items that code already satisfies.
  - Delivery notes that chronicle PR splits (historical).
- **Decision rescue:** None unique outside living contracts. The advisory→enforcing one-way build-level rollout is already in `HARNESS-COMPATIBILITY.md` and `compatibility_service.COMPATIBILITY_ROLLOUT`. Access-never-authorizes-launch is in the contract. Keep those docs; do not rehome from the plan.

---

### `docs/plans/RUNTIME-SURFACING-PLAN.md` (704 lines)

- **Status:** PARTIALLY SHIPPED
  - S0 purposeful discovery/launch: partial (managed templates + catalog skins exist; not the package model).
  - S1: not shipped (see S1 plan).
  - S2: substrate partial (see S2 plan); product UX for first-run now lives in `NOW.md` Phase 1, not this file.
  - S3 Frozen semantic launch: **still ahead**. No `FrozenLaunchSpec` symbol in Python. Process-resident `LaunchLedger` / candidate-scoped identity (`#345`) is a stand-in NOW explicitly flags, not the contract freeze.
  - S4 batch: **still ahead**. No `launch_batch` implementation; `NOW.md` Phase 3 is the live marker.
  - S5 labels/judge: **still ahead**. No experiment/rubric/label product surface.
- **Evidence:**
  - Linked contracts exist and are more current for freeze (`LAUNCH-CONTRACT.md`) and harness authority (`HARNESS-COMPATIBILITY.md`).
  - `NOW.md` owns multi-launch path, first-run, delivery claim truthfulness, fleet close filters; never links this plan.
  - Public ops table lists `harness_inventory`, `launch_options`, `launch_batch` as peers; first three (inventory/options/catalog) exist; batch does not.
  - Large middle sections restate product UX and object models already (or better) expressed in contracts and NOW.
- **Disposition:** TRIM to ~180 lines
- **Survives:**
  - Outcome: purpose-first catalog + native launch + isolated evaluation as destination.
  - Slice map only for work still ahead: **S1** (→ child plan), **S3** freeze/replay (→ `LAUNCH-CONTRACT.md` + open ledger identity gap), **S4** batch isolation (→ `NOW.md` Phase 3 + contract isolation rules not in NOW), **S5** labels/judge (nowhere else).
  - Isolated evaluation constraints that `NOW.md` does not hold: sealed `WorkspaceSnapshot` / `BriefArtifact` before any candidate starts; isolated worktrees; blinded aliases; judge entitlement boundaries. These are direction markers, not shipped promises.
  - Invariants that are not duplicated in contracts (keep a short list; drop any already in LAUNCH-CONTRACT / HARNESS-COMPATIBILITY).
- **Cuts:**
  - Full first-run harness card UX and check tables (superseded by `NOW.md` Phase 1 and shipped canvas settings).
  - Detailed public DTO sketches for inventory already implemented.
  - S0/S2 implementation lists presented as future work.
  - Object ownership table rows that only restate the two contracts.
  - Verification matrices for shipped slices.
- **Decision rescue before heavy trim:**
  1. **Evaluation isolation rules** (seal workspace + brief before spawn; no shared writable tree; partial failure after start is a candidate outcome) — not in `NOW.md` (NOW only says wrap single launch). Worth keeping in the trimmed plan or relocating into `LAUNCH-CONTRACT.md` / a short eval note if S4 is far out.
  2. **S5 label/judge entitlement model** (blinded aliases, rubric artifacts, judge never copies candidate runtime homes) — unique to this doc; keep as a short STILL AHEAD block.
  3. No need to rescue S2 product prose or the frozen-spec field dump; `LAUNCH-CONTRACT.md` owns freeze shape.

---

## Cross-cutting: unique decisions that would be lost

Only content that is **not already** in `CONTROLPLANE.md`, `HARNESS-COMPATIBILITY.md`, `LAUNCH-CONTRACT.md`, or `NOW.md`:

| Decision | Lives today | Action |
|----------|-------------|--------|
| Domain-separated agent package digests + flag-day cutover + physical index authority | S1 plan only (TM tree) | **Keep S1 plan**; do not archive until cutover or rehome to agent-runtimes + a short TM import note |
| Evaluation isolation + S5 judge entitlement | Umbrella plan only | **Keep in trimmed umbrella** |
| Observation contracts (conversation/watch/wait) | Already in `CONTROLPLANE.md` | Safe to archive observation plan |
| Compatibility rollout / access probes / blocks | Already in `HARNESS-COMPATIBILITY.md` + code | Safe to trim S2 plan hard |
| Multi-launch sequencing and first-run | Already in `NOW.md` | Do not keep duplicate roadmap in umbrella |

**No decision needs emergency relocation before archive of the controlplane observation plan.**

---

## Recommended execution order (for the orchestrator, not done by this scout)

1. Archive `CONTROLPLANE-OBSERVATION-PLAN.md`; retarget any remaining links (`CONTROLPLANE.md` still points at it as "approved next slices" — that sentence is itself stale and should become a past-tense pointer or drop).
2. Trim `RUNTIME-SURFACING-S2-PLAN.md` to remaining markers only.
3. Trim `RUNTIME-SURFACING-PLAN.md` to still-ahead slices + eval/S5 markers; delete shipped product UX.
4. Leave `RUNTIME-SURFACING-S1-PLAN.md` intact until package cutover ships or is abandoned.

**Proposed net line cut: ~1,160 of 2,070 (~56%).**
