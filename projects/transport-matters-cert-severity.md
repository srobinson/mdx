# Certification severity scout — invented models and related deferrals

Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` @ `main` (`84d2c66d` at assignment).  
Read only. Mint not run. Report date: 2026-08-03.

Primary question (redirect): **how did a non-existent model name enter a sealed certification record?**  
Secondary: resolver / advisory / drift posture for the three NOW.md items (brief).

---

## 1. Primary finding: how `gpt-5-codex` got into a sealed record

### Verdict

`gpt-5-codex` was **hand-authored into the compatibility release catalog** as a placeholder target long before live model enumeration existed. The first real mint then **copied those catalog edges into the sealed plan and record**, and **proved launch-profile edge coverage against catalog-seeded target snapshots**, not against the CLI's live catalog. A real capture existed for a *different* model (`gpt-5.6-sol`); nothing required every certified model to appear in capture or live enumeration.

This is hand authorship plus a circular mint check, not a mint inventing names from thin air after enumeration existed.

### Provenance (git)

| When | Commit / PR | What happened |
|------|-------------|----------------|
| 2026-04-19 | `5c180fc5` — *ALP-1815: add ChatGPT-authenticated Codex support (#9)* | String `gpt-5-codex` enters the tree as **wire/fixture model id** for Codex IR tests (not a compatibility release). Culture: capture fixtures and tests use it as "the Codex model". |
| 2026-07-16 | `747e0577` — *feat(harnesses): compatibility releases and channel state (S2b) (#293)* | **First catalog authorship.** Embedded `compatibility_releases_v1.json` ships `codex-0.144.4-r1` with **one** target: `model_id` / `native_model_id` = `gpt-5-codex`, `accepted_efforts` = low/medium/high/xhigh, `support_tier` = `observed_unverified`. PR body describes embedding releases with observed_unverified targets; no claim of live enumeration. Digests resealed after hand edit (`scripts/reseal_compatibility_manifest.py`). |
| 2026-07-19 | `e5ae0b61` — *feat(harnesses): first real S2g certification records (claude 2.1.214, codex 0.144.4) (#308)* | **Rescope keeps the invented name.** Manifest becomes `codex-0.144.4-r2` with three targets: `gpt-5-codex` (keeps effort edges), plus hand-added `gpt-5.6-sol` and `gpt-5.4-mini` (model-only). Mint plan `api/plans/codex-0.144.4-r2.json` edge_refs copy that set. Sealed record `certification_records_v1/codex-0.144.4-r2.json` cites the same edges. |
| Same PR #308 | commit subject bullets | Explicit: *codex-0.144.4-r1 adds gpt-5.6-sol + gpt-5.4-mini as model-only edges (**gpt-5-codex keeps its effort edges**)*; *state_refresh seeds complete target snapshots **from the certified catalog*** because *no native model-enumeration probe exists yet*. |
| 2026-07-19 | `33618e43` — *feat(harnesses): enumerate live model catalogs (#309)* | Live enumeration replaces catalog seeding in `state_refresh`. **Too late for the sealed r2 records.** |

Subject line to quote for the inventing catalog step:

> `feat(harnesses): compatibility releases and channel state (S2b) (#293)`

Subject line to quote for sealing it into a "real" mint:

> `feat(harnesses): first real S2g certification records (claude 2.1.214, codex 0.144.4) (#308)`

ARCHITECTURE's line that records "still carry the older hand authored edges" is accurate: S2b hand-authored the edges; S2g mint sealed them.

### The gap that allowed it (exact symbols)

**Where model names enter a record**

1. **Release catalog** — hand JSON under `harnesses/compatibility_releases_v1.json`, field `targets[].model_id` / `native_model_id` (and `accepted_efforts`). Loaded as `CompatibilityReleaseEntry` / `HarnessModelCompatibility`.
2. **Mint plan** — `MintPlan` → `PlannedFacet.edge_refs` (`CertificationEdgeRef`: route_id, model_id, effort). Plan is caller-supplied JSON (`api/plans/codex-0.144.4-r2.json`).
3. **Record assembly** — `certification_minting.mint_outcome` → `_assemble_record` copies `plan.facets[*].edge_refs` onto `CertificationFacet.edge_refs` after suites run and runtime evidence collects. **No rewrite of model names from capture or enumeration.**

**What validation does (and does not) do**

| Check | Symbol | What it proves | Gap |
|-------|--------|----------------|-----|
| Plan edges == release catalog | `test_mint_plans.TestShippedMintPlans.test_edge_refs_cover_the_release_catalog_exactly` via `certification.release_edge_set` | Plan cites exactly the hand catalog | Circular with catalog |
| Record edges == release catalog | `certification._validate_edge_coverage` / `validate_certification_record` | Record cites exactly the hand catalog | Circular; never asks "is this model real?" |
| Launch options == release edges (mint runtime) | `certification_evidence.CapturedRunEvidenceSource._check_launch_profile` | `launch_options(snapshots)` edge set equals `release_edge_set(entry)` | At mint time of #308, `state_refresh._seed_target_snapshot` **wrote target rows from `entry.targets`**, so equality held by construction |
| Capture actuated ⊆ allowed models | same `_check_launch_profile` (exchange loop) | Every captured exchange model is in the certified set | Only **subset** of catalog must appear in capture. PR #308 evidence was **`gpt-5.6-sol`**, not `gpt-5-codex` |
| Live enumeration match | — | — | **Does not exist** |
| Model id in wire fixtures / probe output | — | — | **Does not exist** |

Plain answer: **nothing validates that a model name in the release or record was observed by the harness or by a real capture.** The mint accepts a caller-supplied catalog and plan on trust; the strongest edge check is self-consistency against that same catalog. When targets were catalog-seeded, even the "resolver edges" check was circular.

Relevant #308 code intent (from that commit's `state_refresh` addition; since replaced by live enum in #309):

- `_seed_target_snapshot` docstring: *Record target availability from the certified release catalog. No native model-enumeration probe exists yet, so … the release catalog is the availability authority.*

### Evidence run was real — catalog was not

PR #308 body: codex record minted over live run `6a731c46` with **gpt-5.6-sol**, 7 exchanges, real tool calls; facets 7/7 against owned Tier-1 + stored snapshots. That is genuine mint against an installed harness for *observability* facets.

It does **not** mean every edge in `launch_profile_resolved` was actuated. `_check_launch_profile` only requires actuated models ∈ certified set, not certified set ⊆ actuated set. `gpt-5-codex` and its four effort edges never needed a capture.

The plan still binds that run path:

- `api/plans/codex-0.144.4-r2.json` → `scenario_bindings[0].run_dir` under `~/.transport-matters-preview/.../6a731c46-...`
- That path is **absent on this machine today** (operator-local evidence, not in repo).

Certified wire fixture cited by the plan uses **`gpt-5.2-codex`**, not `gpt-5-codex` (`api/tests/fixtures/codex_response_create_certified_0144.json`), another sign edges are not driven from a single observed vocabulary.

---

## 2. Blast radius: full sealed catalog vs live enumeration

### Codex (`codex-0.144.4-r2`)

**Sealed targets (3 models, 6 edges)**

| model_id | accepted_efforts (edge shape) | Live today (`codex debug models --bundled`, CLI 0.146.0) | Live after probe filter (`visibility == "list"` in `probes.codex._parse_model_enumeration`) |
|----------|-------------------------------|----------------------------------------------------------|---------------------------------------------------------------------------------------------|
| `gpt-5-codex` | low, medium, high, xhigh (4 edges) | **absent** | **absent — invented / obsolete** |
| `gpt-5.6-sol` | model-only (1 edge, effort null) | list, real | **real** |
| `gpt-5.4-mini` | model-only | **hide** (exists but not listed) | **not enumerated** (filtered) |

**Live list models missing from sealed catalog (2026-08-03 on this host)**

| model_id | notes |
|----------|--------|
| `gpt-5.5` | NOW.md example; list |
| `gpt-5.6-terra` | list |
| `gpt-5.6-luna` | list |
| `gpt-5.2` | list |

**Hide models present in CLI JSON but not in list enumeration:** `gpt-5.4`, `gpt-5.4-mini` (in catalog), `codex-auto-review`.

**Count (codex)**

- **1 fully bogus sealed model** (`gpt-5-codex`) with **4 bogus effort edges**.
- **1 sealed model real but not on list path** (`gpt-5.4-mini`).
- **1 sealed model genuinely real and list-visible** (`gpt-5.6-sol`).
- **≥4 real list models missing** from certification today (catalog lag; harness version on host is 0.146.0 vs certified baseline 0.144.4 — lag is expected after #309 until re-mint, but the *invented* name is not lag).

### Claude (`claude-2.1.211-r2`)

**Sealed targets (4 model-only edges)**

| model_id |
|----------|
| `claude-opus-4-8` |
| `claude-fable-5` |
| `claude-sonnet-5` |
| `claude-haiku-4-5` |

**Live short-name enumeration** (`claude -p /model` / probe fixture shape):  
`sonnet`, `opus`, `haiku`, `fable`, `best`, `sonnet[1m]`, `opus[1m]`, `fable[1m]`, `opusplan`, `default` (+ full model IDs allowed by CLI text).

**String overlap of sealed ids with live short enum: zero.**  
These look like hand-chosen **full model ids** from the mint era (evidence run used fable-5), not aliases the enumeration probe emits. Whether each full id still resolves at Anthropic is a provider question; they are **not** invents in the same sense as `gpt-5-codex` (no evidence they never existed), but they **do not match the live enumeration vocabulary** the product now uses after #309. That is a second, related catalog identity failure: sealed names ≠ enum names.

**Efforts:** claude sealed edges are model-only (effort null). Live efforts from CLI: low, medium, high, xhigh, max, auto (probe expands globally).

### Combined invented / non-corresponding summary

| Class | Count | Entries |
|-------|------:|---------|
| Sealed models with **no** corresponding live list id (codex) | **1** | `gpt-5-codex` |
| Bogus **edges** under that model | **4** | low/medium/high/xhigh |
| Sealed models real-but-hidden (not enum path) | **1** | `gpt-5.4-mini` |
| Sealed models real and list-visible | **1** | `gpt-5.6-sol` |
| Live list models missing from codex seal (this host) | **4** | `gpt-5.5`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.2` |
| Claude sealed ids with zero short-enum string match | **4** | full ids listed above |
| **Primary invent count called out by NOW.md** | **1 model / 4 edges** | `gpt-5-codex` |

Interesting number: **one invented model, four sealed effort edges**; plus a **systemic** catalog that was never derived from enumeration (claude 4 + codex 3 = **7 sealed models**, of which only **1** cleanly matches today's codex list vocabulary).

---

## 3. The missing check

What would have caught this at mint time:

1. **Derive release targets from live `ModelEnumerationProbeAdapter` output** (or require plan/catalog ⊆ that set for the observed harness version), not from hand JSON alone.
2. **Require edge coverage from actuated capture** (or sampled launches), not only actuated ⊆ catalog.
3. **Forbid catalog-seeded target snapshots as evidence for `launch_profile_resolved`** once enumeration exists; only complete probe snapshots.

What exists today:

- Unit/plan coherence: `test_mint_plans` (plan ↔ catalog only).
- Digest / facet structure: `validate_certification_for_release`.
- Runtime facet checks that re-run production owners over one owned run: `certification_evidence` (still trusts catalog for expected edges).
- Live enum at runtime: `state_refresh._refresh_target_snapshot` + `probes.codex` / `probes.claude` (#309).
- **No** conformance kit or CI job comparing sealed `compatibility_releases_v1.json` / certification records to live enumeration.
- **No** workflow step named drift / catalog / cert under `.github/workflows/`.

That absence is the durable finding: **sealing self-consistent fiction remains possible until catalog provenance is checked against the harness.**

---

## 4. Secondary: resolver / advisory / drift (brief)

### Central ARCHITECTURE claim

Docs: resolver "intersects live target evidence with those edges until re-mint…".  
Code reality:

- `resolver._offered_targets` / `_decorate_target`: options come from **live** `target_observations`; matching edge only attaches `support_tier` / lifecycle / launch_adapter_revision. Missing edge → `observed_unverified`, not hard delete.
- Pure `resolve_target`: unverified explicit model → `target_unverified_opt_in_required` unless `allow_unverified_target`.
- **Launch path** `launch_target.resolve_launch_target_advisory` (used by `api/v1/capture_rpc_routes._resolve_launch_target`): converts `target_unverified_opt_in_required`, `invalid_effort`, and `target_unavailable`/`not_observed` into **advisories and still passes model/effort to the harness**. So stale edges do **not** suppress a live model on the capture launch path today.
- `invalid_effort` in `resolver._resolve_effort` is against **native observed efforts**, not certified `accepted_efforts` (ARCHITECTURE overstates certified∩observed for effort).
- `match_release` does **not** judge model membership; only version/blocks/route/target **blocks**.

### User outcomes today

| Ask | Outcome |
|-----|---------|
| Launch `gpt-5.5` on codex (live list, absent from seal) | Offered as `observed_unverified` / `requires_unverified_opt_in` in inventory. Capture launch **proceeds** with advisory (`target_unverified_opt_in_required` or resolved if opted in). Not `model_rejected`, not `invalid_effort` by default. Failure only if harness/provider rejects the name. |
| Invented `gpt-5-codex` | **Not offered** unless live enum returns it (it does not). Catalog alone does not invent a picker option after #309. Explicit request: `not_observed` → launch advisory still **passes through** to harness; user sees harness/provider failure, not a TM hard reject. |

### Item 3 — `COMPATIBILITY_ROLLOUT = "advisory"`

- Symbol: `compatibility_service.COMPATIBILITY_ROLLOUT` / `compatibility_enforcing`.
- Advisory: `gate_launch_preparation` records outcomes; internal failures → ungated; never raises. Resolver `_compatibility_disposition` turns non-compatible `match_release` into `CompatibilityAdvisory`.
- Enforcing: non-compatible → `HarnessCompatibilityRejected` / resolution rejection; unprovable gate fails closed.
- Enforcing flip **does not** currently reject unknown models via `match_release`; it would harden **version/block/release-unavailable** gates. Unverified-target hard fail on pure resolver already exists independent of rollout; launch wrapper still softens it.
- Stale records are **not** the main blocker for flipping version enforcement; **coverage of versions and honest catalog** still gate confidence. Item 1 does not fully block item 3 for version gates; it does block any claim that certified **model edges** are trustworthy.

### Item 2 — `detect_unknown_shapes`

- Exists: `drift_capture.detect_unknown_shapes`; runtime via drift emitter / tailer hooks; re-used by `certification_evidence`.
- `.github/workflows/ci.yml` (and all of `.github/`): **no drift job**, no reference to `detect_unknown_shapes`.
- Unit tests exercise it (`test_drift_capture.py`) inside normal pytest, which is not a dedicated "unknown shape fails the gate on fixtures" product CI contract beyond unit coverage.
- Class of failure that reaches main unnoticed without a CI drift gate: new wire request fields / response event types / nested tags that unit fixtures do not cover, then hit production parses. Runtime is advisory-only (never blocks launch).

### Coupling

| Link | Truth |
|------|--------|
| Fix 1 unblocks 3? | Partially. Re-mint fixes **honest model edges** and catalog lag; enforcing still needs deliberate coverage of version outcomes. |
| Fix 2 protects 1? | No. Drift is **wire/transcript shape**, not model catalog drift. Catalog re-rot is a different sensor (enum vs seal). |
| Three coupled? | Weakly: all sit under "certification truthfulness", but **mechanisms are distinct**. |

### Risk rank today (real user impact)

1. **Catalog invent / lag (item 1)** — **latent product-truth defect**: sealed artifacts assert models that are wrong or incomplete; launch still works via live enum + advisory pass-through. **Not** a hard multi-launch blocker on the current launch path. **Live defect of sealed evidence integrity** (the class that has bitten this repo before).
2. **No CI drift gate (item 2)** — **latent** schema-break risk; runtime advisory only.
3. **Advisory rollout (item 3)** — **intentional posture**; fine to defer; flip is one constant but needs honest confidence, not only re-mint.

**User-visible wrongness before multi-launch:** soft (inventory `observed_unverified` / advisories; picker not offering invented models). **Sealed-artifact wrongness:** hard and present — records claim `gpt-5-codex` edges without evidence. Multi-launch multiplies quiet lies about support metadata, not (today) hard suppression of live models.

### Re-mint claim ("run it, do not rebuild")

`api/scripts/mint_harness_certification_record.py` is real tooling, not a rebuild of the subsystem. But it is **not** a single clean "run and done" against current code without prerequisites:

- Clean worktree (`require_clean_worktree`).
- Plan with `scenario_bindings` pointing at **local** owned run dirs (codex path missing here).
- DB snapshots / refresh; historically catalog seed, now live enum.
- If evidence does not reproduce sealed digests → writes **successor** record and prints successor release JSON to hand-merge into `compatibility_releases_v1.json` + pointer flip + `--verify-activation`.
- Suites + fixture hashing + runtime evidence; not credentials-free.

So: run the pipeline, yes; free of real work, no. Updating the **hand catalog** (remove invents, add live list models) is a prerequisite edit before a honest re-mint, unless a new path derives targets from enumeration first.

---

## 5. Judgement the owner asked for

| Question | Answer |
|----------|--------|
| How did `gpt-5-codex` get there? | Hand-authored in S2b catalog from fixture culture; kept on rescope; sealed by mint with circular catalog-seeded edge proof; evidence capture used `gpt-5.6-sol` only. |
| How many other bogus entries? | **1 invented model, 4 effort edges.** Broader: **6 of 7 sealed models** fail clean list-enum correspondence today (4 claude id-form mismatches + gpt-5-codex + gpt-5.4-mini hidden). |
| Live defect vs defer? | **Sealed integrity is a live defect.** Launch suppression of real models is **not** the live failure mode under advisory + launch-target pass-through. Safe to defer for multi-launch *function*, not safe to trust cert edges as truth. |
| Fix class | Provenance check: catalog ⊆ live enum (or explicit full-id map); stop treating hand edges as evidence of observation; re-mint after catalog rewrite. |

---

## Paths / symbols (no line numbers)

- Catalog: `api/src/transport_matters/harnesses/compatibility_releases_v1.json`
- Records: `api/src/transport_matters/harnesses/certification_records_v1/{claude-2.1.211-r2,codex-0.144.4-r2}.json`
- Plans: `api/plans/{claude-2.1.211-r2,codex-0.144.4-r2}.json`
- Mint CLI: `api/scripts/mint_harness_certification_record.py`
- Assembly: `certification_minting.mint_outcome`, `_assemble_record`, `MintPlan` / `PlannedFacet.edge_refs`
- Edge math: `certification.release_edge_set`, `_validate_edge_coverage`, `validate_certification_for_release`
- Evidence: `certification_evidence.CapturedRunEvidenceSource._check_launch_profile`
- Historical seed: commit `e5ae0b61` `state_refresh._seed_target_snapshot` (removed by `33618e43`)
- Live enum: `state_refresh._refresh_target_snapshot`, `probes.codex._parse_model_enumeration`, `probes.claude` MODEL_ENUMERATION_PROBE
- Launch softness: `launch_target.resolve_launch_target_advisory`, `resolver.resolve_target`, `compatibility_service.COMPATIBILITY_ROLLOUT`
- Drift: `drift_capture.detect_unknown_shapes`
