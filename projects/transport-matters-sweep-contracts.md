# Design contracts scout — transport-matters

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` on `main` (`af52318d`).
Lens: docs guide, they do not promise. Code is source of truth. A passage that a code change would silently invalidate is a liability; delete, do not correct. Survivors are decisions, reasoning, direction, and open work.

Cluster total: **2,050 lines** across five docs.
Proposed net after dispositions: **~680 lines** (~**1,370 line cut**, ~67%).

---

## Summary

| Path | Lines | Decisions | Spec | Open work | Disposition | Target |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `docs/HARNESS-COMPATIBILITY.md` | 729 | ~25% | ~65% | ~10% | TRIM to ~200 (+ absorb publishing) | ~200 |
| `docs/LAUNCH-CONTRACT.md` | 465 | ~35% | ~55% | ~10% | TRIM to ~160 | ~160 |
| `docs/RUN-IDENTITY.md` | 429 | ~40% | ~50% | ~10% | TRIM to ~180 | ~180 |
| `docs/CONTROLPLANE.md` | 358 | ~30% | ~55% | ~15% | TRIM to ~140 | ~140 |
| `docs/COMPATIBILITY-PUBLISHING.md` | 69 | ~40% | ~50% | ~10% | MERGE into `HARNESS-COMPATIBILITY.md` | 0 |
| **Cluster** | **2050** | | | | | **~680** |

Proportions are judgmental volume shares, not precise counts. Every doc in this cluster is majority specification of shapes that already live (or will live) in code. The design value is real but concentrated in policy paragraphs, not in the struct dumps that surround them.

---

### `docs/HARNESS-COMPATIBILITY.md` (729 lines)

- **Content split:** decisions ~25% / specification ~65% / open work ~10%
- **Disposition:** TRIM to ~200 lines (then absorb the surviving ~15 lines from `COMPATIBILITY-PUBLISHING.md`)
- **Survives:**
  - **Purpose / Core policy:** optimistic range support; runtime drift as enforcement; advisory vs `COMPATIBILITY_ROLLOUT` enforcing posture; raw capture as insurance; support is product certification, never harness feature behavior.
  - **Ownership table:** which authority owns provider availability, native acceptance, product support, auth, access, local observation, agent preference, target selection, actuation, wire, session, transcript, home layout. This is the map code will not narrate.
  - **Stable harness identity vs release:** `HarnessDescriptor` owns durable harness facts; `HarnessCompatibilityRelease` is the immutable certification snapshot. Keep the *split*, not the field inventory.
  - **Target authority three axes:** product support tier (`tested` / `observed_unverified`), lifecycle (`active` / `deprecated` / `retired`), executor availability (`ready` / `unavailable` / `stale` / `probe_failed`). Intersection rule. Defaults only from tested + active + ready.
  - **Observation absence semantics:** complete may prove absence; partial can prove presence only; failed changes no prior availability.
  - **Auth and access are observational:** never authorize or block launch; provider rejection surfaces from the live run.
  - **Channel state independence:** stable and preview independent active pointers; blocks apply to new launches only; freeze never rewritten; clear only by signed supersession.
  - **Runtime drift philosophy:** attribute before enforce; `runtime_observable` vs `certification_gated` facet classes; harness feature behavior is out of scope; unattributable/capture-unsafe incidents pause the release.
  - **Historical read compatibility:** readers dispatch from recorded revisions; resume/fork is a new launch under active release requiring a bridge; unsupported historical data returns a hard failure, never a guessed parse.
  - **Signed data updates:** narrow surface; may select only already-installed adapter revisions; last verified cache survives retrieval failure.
  - **Open decisions:** signature trust root, re-mint of certification records, first Grok route, block GC / drift threshold, freshness windows, preview soak policy, publication SLO, historical reader retention.
- **Cuts:**
  - Full `HarnessCompatibilityRelease`, `HarnessRouteCompatibility`, `HarnessModelCompatibility`, `CompatibilityChannelState`, `VersionBlock`, `LocalHarnessObservation`, `LocalHarnessAccessObservation`, `LocalTargetObservation` struct dumps.
  - Per-facet field inventories under **Contract facets** (wire request/response, session bootstrap, transcript locator/reader, project layout, runtime home): replace with one paragraph each naming *what the facet is for*, not its closed field set.
  - **Outcome codes** closed catalogue (codes live in code / shared enum; doc should say "stable codes, rendered at presentation boundary" and name only the *policy-bearing* few if needed: advisory vs hard, enablement vs compatibility separation).
  - **Verification gates** numbered checklist (tests prove this; the doc should not inventory them).
  - **Publication** and **Harness release handling** process steps that duplicate `COMPATIBILITY-PUBLISHING.md` (fold the non-duplicate policy into one short section).
  - Claude/Codex enumeration shape details that restate adapter behavior (`ModelEnumerationProbeAdapter` expansion rules).
  - Concrete active release ids and baseline versions in **Open decisions** (those stale the day they ship); keep the open questions, drop the inventory of current pins or point at the channel state artifact.
  - **First run and startup inventory** UI choreography once it is productized; keep only "zero enabled installed harnesses disable launch; diagnostics remain accessible."
- **Load-bearing content at risk:**
  - Advisory → enforcing rollout posture and the rule that range/block mismatches stay flags until then.
  - Auth/access never gate launch.
  - Complete / partial / failed absence semantics.
  - Facet observability classification (`runtime_observable` vs `certification_gated`) and "harness feature behavior is not a facet."
  - Resume/fork = new launch + bridge requirement; no guessed historical parse.
  - Ownership table (who may not substitute for whom).
  - Blocks clear only by signed supersession; frozen runs retain release id and digest.
  - Optimistic support default (weekly harness releases without certification treadmill).

---

### `docs/LAUNCH-CONTRACT.md` (465 lines)

- **Content split:** decisions ~35% / specification ~55% / open work ~10%
- **Disposition:** TRIM to ~160 lines
- **Survives:**
  - **Purpose:** one application service for REST, MCP, Canvas, native, profile, evaluation; all produce the same durable launch facts.
  - **Six-stage pipeline** and what each stage *means* (request intent → intent → pinned resolution context → frozen semantic target → native actuation → client receipt). Not the struct fields inside each stage.
  - **Authority boundaries:** clients express intent only; they never choose adapter revision, compatibility release, catalog revision, executable path, or native argv.
  - **Durable claim and replay:** ledger key `(owner, dispatch_id, candidate_key)`; same key + same intent digest returns stored decision; different digest → `dispatch_conflict`; replay never consults current defaults; new dispatch id to retry after install/refresh.
  - **Resolution policy:** pure over pinned context; no FS/process side effects; explicit fields never fall back; defaults only tested+active+ready; unverified requires opt-in; auth/access never authorize or block; omitted connection uses sole or saved default else `connection_ambiguous`; effort belongs to harness+model edge.
  - **Capture RPC special case:** when model and effort both omitted, preserve harness home default and add no model/effort args (interactive canvas independence).
  - **Two compatibility checkpoints:** target resolution before a run exists; actuation gate after executable resolution writes run-scoped fact; shared rollout posture.
  - **Actuation ownership:** one `LaunchProfile` per harness; raw caller passthrough cannot override semantic fields; secrets in env delta never enter digests or sanitized facts.
  - **Claude effort advisory:** explicit Claude effort preserved as requested metadata with `effort_not_actuated` (product truth, easy to lose).
  - **PromptReceipt proof semantics:** `submitted` requires exactly one correlated provider exchange with positive response and no classified rejection; `model_rejected` wins over earlier outbound evidence; sticky Activity `needs-you-model-rejected`; roster reports `model=null`; later successful turn clears sticky; `run.ready` never upgrades proof.
  - **Versioning:** `spec_version` versions public semantic contract only; harness format changes create a compatibility release, not a new launch `spec_version`; flag-day ok prerelease, retain/migrate once external history exists.
  - **Open decisions:** durable transaction boundary; whether `brief_id` is public v1; which post-freeze failures are safely resumable; migration of process-resident ledger.
- **Cuts:**
  - Full `LaunchRequest`, `ResolvedTarget`, `FrozenLaunchSpec`, `LaunchActuation`, `LaunchResult` field inventories (types and tests own these).
  - **Failure contract** closed code table (same liability class as outcome catalogues elsewhere). Keep the *principle*: stable codes with structured details; human copy at presentation boundary.
  - **Verification** numbered checklist.
  - Request normalization bullet list once it is pure code behavior (retain only: requested model spelling stays in intent; alias resolution freezes separately so replay preserves caller spelling).
  - Runtime home and spawn step list that restates capture boundary code.
- **Load-bearing content at risk:**
  - One launch service / six-stage meaning.
  - Replay and `dispatch_conflict` rules; ledger durability across process restart as product intent (implementation may still be process-resident; open decision covers migration).
  - Explicit never fallback; defaults only tested+active+ready.
  - Auth observational only.
  - Capture omit-model path.
  - Prompt proof and `model_rejected` sticky semantics (shared with control plane; losing either side desyncs product story).
  - Claude `effort_not_actuated`.
  - Secrets never enter digests/receipts/catalogs/sanitized actuation.

---

### `docs/RUN-IDENTITY.md` (429 lines)

- **Content split:** decisions ~40% / specification ~50% / open work ~10%
- **Disposition:** TRIM to ~180 lines
- **Survives:**
  - **Field lifetime table:** `run_id` permanent; `name` reserved while active, retained in history; `agent_id` / `agent_revision` frozen for the run, nullable for native. Friendly name never prefixed with agent id. API keeps fields independent.
  - **Name sources:** `fixed` / `requested` / `generated` as durable provenance, not inferred from spelling.
  - **Platform fixed names policy:** only trusted TM platform profiles (`kind = "platform"`) may declare `fixed_name`; no closed enum of Director/Observer/etc.; user profiles cannot gain reserved handles; fixed handle is hard singleton per owner; catalog import derives reserved set; existing nonfixed lease stays valid if a new fixed collides.
  - **Generated names philosophy:** `moons-v1` immutable curated dictionary; cultural/pronunciation review; exclusions for control words, collisions, weak spoken forms; membership change = new dictionary revision. Keep *why moons*, not the exclusion laundry list that restates the dictionary artifact.
  - **Allocator decisions:** versioned shuffled cycle; owner+revision cursor; atomic claim; pool exhaustion fails with `name_pool_exhausted`; fixed launches ignore pool; cursor survives restart.
  - **Lease model decisions:** first successful ledger claim reserves; hold through gateway creation and process lifetime; definite pre-gateway failure releases; ambiguous after gateway retains until reconciliation; terminal persistence failure retains for repair; batch claims all names before first start; names immutable for run lifetime (rename out of first version).
  - **Name resolution outside `ResolvedTarget`:** identity is a sibling launch concern.
  - **Self identity:** one shared object, four projections (env JSON, runtime home env, harness instruction carrier, control plane `whoami`); harness carrier is adapter-only; native renders derived label while keeping `agent_id = null`; agent identity and `control_access` never imply each other; every captured launch gets a fresh operational home distinct from transcript discovery home.
  - **Public `RunRef`:** UUID or canonical active name; closed history commands require UUID; reuse of released name never rebinds a historical UUID.
  - **Evaluation blinding:** aliases are presentation/entitlement; never mutate frozen identity.
  - **Invariants** (compressed, not restated as a second full section after cuts).
- **Cuts:**
  - Canonical name syntax full grammar and character rules once owned by one validator (retain product constraints that *motivate* the grammar: spoken use, no UUID-shaped, denylist of control words).
  - Full lease struct field dump.
  - Dictionary exclusion bullet inventory that duplicates the committed dictionary artifact (the artifact is normative membership).
  - **Ownership** table with concrete file and symbol paths (`run_models.py::LaunchRequest`, `RunManager.ts`, `spawn.ts::titleForSession`, etc.): classic silent-invalidation inventory.
  - Roster JSON shape, product presentation mockups, Canvas chrome details.
  - **Verification** numbered checklist.
  - Public launch function sketch that duplicates `LAUNCH-CONTRACT.md`.
- **Load-bearing content at risk:**
  - Three-field separation and lifetimes.
  - Fixed name trust model (platform provenance only; no closed enum).
  - Lease hold-through-ambiguity and pre-gateway release rules.
  - Closed-run commands require UUID; names grant no control plane authority.
  - Self identity four projections from one object.
  - Evaluation aliases never rewrite identity.
  - `moons-v1` immutability and cultural curation intent (without the membership list).

---

### `docs/CONTROLPLANE.md` (358 lines)

- **Content split:** decisions ~30% / specification ~55% / open work ~15%
- **Disposition:** TRIM to ~140 lines
- **Survives:**
  - **Principles (all five):** twin skins / one service; identity never self-declared; push carries references, pull carries content; low token count is structural; every action attributed and persisted.
  - **Architecture shape (not paths):** Python service owns policy; Node gateway is a private resultful executor with no control-plane policy; REST and MCP are thin skins; gateway is a child of the Python server so service, subscriptions, and runs share one lifetime; conversation content durable in Postgres; voice has no special surface.
  - **Identity and entitlements:** TM mints run-scoped bearer at spawn; only digest persisted; grant fail-closed; resolve bearer→run→grant per request uncached; skins receive principal never token; `observer` = observe+watch, `director` = all verbs; visibility = grant workspace; grants are launch-time; revoke dies on next request; mid-run grant change takes effect on next launch.
  - **Verb intents (not parameter inventories):** observe pulls (whoami, workspace summary, roster, conversation); prompt fan-out with nudge vs interrupt; wait_for_reply on a delivery the director created; launch through the same capture seam as the UI; manage close/interrupt; watch push with damping and self-exclusion.
  - **Delivery and proof policy:** `submitted` requires durable wire exchange with positive response and no classified rejection; `model_rejected` wins; partial success per target; durable `control_plane_delivery` stores digest not raw text; provider-visible text is only the normalized user prompt.
  - **Provider conditions as needs_you, never gates:** auth expiry and usage limit surface live; never block launch. Distinguish operator question vs provider condition.
  - **Watch contract philosophy:** process-resident subscriptions die with API; logical completion owned by activity projection; damping first-class; self-exclusion structural; causal loop protection deferred (needs delivery-to-turn binding the in-memory plane cannot provide).
  - **Attribution:** one audit shape for human and agent; observe pull-only does not write audit; wait writes delivery-scoped outcome without copying prompt text; dispatch groups are experiment records from day one.
  - **Deferred, not dropped:** CLI skin; cross-workspace directors; rename/breakpoint/spend as manage verbs; runtime grant toggle; judge/eval verbs over dispatch groups.
- **Cuts:**
  - Conversation parameter inventory (cursors, `max_chars_per_message` bounds, page budgets, `limit` defaults, `shape=summary` rules, display-turn prefix-sum correspondence). These are code and tests.
  - Claude vs Codex paste/Enter/composer-redraw delivery micro-protocol (adapters own this; silent invalidation on every harness UI tweak).
  - Exact watch nudge text format.
  - Error code closed catalogue.
  - **Testing** inventory (unit/integration/corpus lists).
  - Package and module path inventory (`api/src/transport_matters/controlplane/`, `@tm/activity`, MCP mount path) beyond one architectural pointer if needed.
  - Migration locking detail for audit uniqueness constraint.
  - Launch verb's full replay/ledger restatement of `LAUNCH-CONTRACT.md` (point, do not re-specify).
- **Load-bearing content at risk:**
  - Twin skins / one service; no logic in skins.
  - Identity never self-declared; fail-closed grant mint at spawn.
  - Observer vs director; launch-time grants; workspace-bounded visibility.
  - Push refs / pull content; damping; self-exclusion; deferred causal damping.
  - Delivery proof semantics (shared with launch contract).
  - Provider conditions never gate launch.
  - One audit shape; fan-outs as experiment records.
  - Deferred list (direction markers).
- **Note on status line:** already says "current implementation reference" rather than "living design contract." Still over-promises field-level fidelity. After trim, status should match the rest of the cluster (see cross-cutting #2).

---

### `docs/COMPATIBILITY-PUBLISHING.md` (69 lines)

- **Content split:** decisions ~40% / specification ~50% / open work ~10%
- **Disposition:** MERGE into `docs/HARNESS-COMPATIBILITY.md`
- **Survives (into HARNESS, ~15 lines under a single "Publication lifecycle" heading):**
  - Publisher lifecycle is how releases are *produced*; harness compatibility is what an installed build *enforces*. Keep that ownership sentence.
  - Pipeline intent: detect → observe → certify → publish signed data → activate channel pointer.
  - Data-only update when every adapter fingerprint is already installed (no desktop rebuild; primary day-one model support path).
  - Product release first when certification needs new executable logic; new compatibility release then declares minimum product version.
  - Never bypass conformance for launch excitement; measure availability→observation→certification→activation; shortest *safe* path.
  - Certification never asserts harness feature behavior (already in HARNESS; one sentence is enough).
- **Cuts:**
  - Seven observability facets list (duplicate of HARNESS verification / certification content).
  - Field-level publication artifact list (catalog revision, evidence digest, channel pointer) once HARNESS already describes signed data updates.
  - Entire standalone file after merge.
- **Load-bearing content at risk:**
  - Data-only vs product-release gate.
  - Never bypass conformance.
  - Publisher-vs-enforcement ownership split (the reason this doc existed).
  - Without merge care, those three can vanish because HARNESS's current **Publication** section is thinner than this file on the data-only path and the "no bypass" rule.

---

## Cross-cutting answers

### 1. Overlaps and merges

**Yes: merge `COMPATIBILITY-PUBLISHING.md` into `HARNESS-COMPATIBILITY.md`.**

The publishing doc opens by declaring it owns the publisher lifecycle *behind* harness compatibility. That split of concerns is real; a second file is not required to express it. Concrete overlap:

| Publishing content | Already (or better) in HARNESS |
| --- | --- |
| Seven observability facets | Verification gates + runtime drift facet classes |
| Signed release + channel pointer | Signed data updates + Channel state |
| Optimistic / certify / activate flow | Harness release handling |
| "Never assert harness features" | Purpose + Core policy + facet scope |

What publishing adds that HARNESS currently understates: the **data-only day-one path**, the **product-release-first gate when adapters change**, and the **never bypass conformance** objective. Fold those into one short HARNESS section; delete the standalone file.

**Do not merge the other three pairs.**

| Pair | Relationship | Action |
| --- | --- | --- |
| HARNESS ↔ LAUNCH | LAUNCH consumes one certified release; shared rollout posture and many outcome codes | Keep separate; drop duplicated code tables; cross-link principles |
| LAUNCH ↔ RUN-IDENTITY | Launch freezes name + agent fields; identity is sibling of target | Keep separate; LAUNCH points at identity for names |
| LAUNCH ↔ CONTROLPLANE | Shared prompt proof, `model_rejected`, capture seam, process-resident ledger | Keep separate; CONTROLPLANE launch verb should point at LAUNCH, not restate it |
| RUN-IDENTITY ↔ CONTROLPLANE | `whoami` / roster project frozen identity | Keep separate; CONTROLPLANE names fields, RUN-IDENTITY owns lifetime rules |
| CONTROLPLANE ↔ HARNESS | Almost no content overlap | No action |

Outcome-code and field-shape duplication across HARNESS and LAUNCH is the secondary DRY problem. After trim, neither doc should carry a closed catalogue; both should name the *policy* (advisory vs hard; enablement vs compatibility) and let code own the enum.

### 2. Does "Status: living design contract" survive?

**No.** Under this lens it should go.

A contract is a promise by construction. "Living design contract" invites the exact maintenance burden the owner is rejecting: keep the doc synchronized with every field, route, and code path, or silently lie. Four of five docs use that phrase (`HARNESS-COMPATIBILITY`, `LAUNCH-CONTRACT`, `COMPATIBILITY-PUBLISHING`, and effectively the spirit of the others). `CONTROLPLANE` already chose "current implementation reference," which is better language and worse practice: it still sponsors the parameter inventories that make the file a second code base.

Recommended status treatment for this cluster after trim:

- Drop "living design contract" everywhere.
- Prefer either no status line, or a short marker such as **decisions and open work** / **design notes**.
- Keep an **Open decisions** (or **Deferred**) section as the only intentionally living part.
- Where a doc still carries implementation-adjacent rules that are product policy (lease ambiguity, proof semantics, rollout posture), state them as *product decisions*, not as a contract the reader should treat as complete.

`CONTROLPLANE`'s approved/locked dates can stay as historical provenance if useful; they do not license field-level inventory.

---

## Disposition bias check

Bias was hard toward cutting. Load-bearing items were flagged, not cut:

- Rollout posture and enablement/compatibility separation
- Auth/access never gate launch
- Observation completeness semantics
- Facet observability classes and out-of-scope harness features
- Resume/fork bridge rule and historical reader dispatch
- Launch pipeline meaning, replay rules, explicit-never-fallback
- Prompt proof and `model_rejected` sticky semantics
- Run identity field lifetimes, fixed-name trust, lease ambiguity, UUID-for-closed-history
- Control plane twin skins, grant model, push/pull, damping/self-exclusion
- Publisher data-only path and no-bypass rule (must survive the merge)

Nothing in the load-bearing set requires the ~1,370 lines proposed for deletion. Those lines are mostly struct dumps, closed code tables, verification checklists, path inventories, and harness-specific micro-protocols that fail the silent-invalidation test.

---

## Suggested trim order (for the implementer, not this scout)

1. Merge `COMPATIBILITY-PUBLISHING.md` into HARNESS (small, clarifies ownership).
2. Trim HARNESS (largest cut, highest liability density).
3. Trim LAUNCH and CONTROLPLANE in parallel (shared proof language; do once carefully).
4. Trim RUN-IDENTITY (most decision-dense; lightest relative cut).
5. Strip all "living design contract" status lines in the same pass.

Scout only; no edits applied.
