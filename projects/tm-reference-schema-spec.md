---
title: Transport Matters Release Reference Schema Spec
type: projects
tags: [transport-matters, harnesses, compatibility, certification, baseline, request-schema, support-state, spec]
summary: What a release ships as its reference request schema, who consumes the support verdict in production, how the reference is authored and certified, and what stays out
status: active
project: transport-matters
confidence: high
created: 2026-08-23
updated: 2026-08-23
---

# Transport Matters Release Reference Schema Spec

Slice B. This names the artifact, the production caller, the authoring flow, the migration
answer, and the exclusions. It does not restate `~/.mdx/projects/tm-reference-schema-plan.md`,
which remains the reuse map, and it does not re-derive the settled constraints in the brief.

## Inspection boundary

Read at `6d02aa866ac8568e8b0a79af2ad962533b6b207b`, branch `fix/verification-unknown-compatibility`,
clean tree. HEAD moved during the pass: an earlier read saw `91b42f02` on `test-rendezvous-budget`.
Another agent owns the working tree this phase and this pass wrote nothing to the repository,
no store, no home, no backend, and made no provider call. One measurement ran `uv run python`
over a committed fixture and touched no state.

Two corrections to the brief's premises, both material:

- `TLDR.md` (which `CLAUDE.md` symlinks to) carries no blessing sections at this SHA. Its five
  sections cover channels, executor ids, startup refresh, missing targets, and bundle reads.
  The blessing contract is in `docs/HARNESS-COMPATIBILITY.md`, under **Identity and release**.
  That document and the brief disagree on one point, which becomes Open Decision 1.
- `SupportState` is not the first verdict shipped without a caller. `baseline_staleness.assess_baseline_staleness`
  has no production caller either: every reference outside its own module is a test or a
  docstring. Its docstring claims "the launch gate and the inventory projection both ask the
  question". Neither does. Two inert verdicts is a pattern, and the caller below is specified so
  this slice does not add a third.

## 1. The artifact a release ships

**The artifact is `request_schema.RequestSchema`**, exactly as `baseline_projection.GateProjection`
already carries it. No new schema shape, no second minter, no release-specific serialization.

**Produced by** `baseline_projection.project_baseline`, which selects the profile from the
adapter (`get_adapter_for_provider(bundle.cell.provider).request_schema_profile`) and calls
`request_schema.mint_request_schema` over the three raw request bodies of one controlled
baseline bundle. The reference is the `gate.request_schema` of a bundle captured at the top of
the blessed range. Nothing else mints it.

**Where it lives: inside `compatibility_releases_v1.json`, as a fourth array on the release
entry.** Not a sidecar.

`compatibility.CompatibilityReleaseEntry` is `release`, `routes`, `targets`. Add `references`
as its peer, and add the same key to `compatibility.release_digest_payload`, which enumerates
its three collections explicitly and would otherwise silently omit the new one. One file, one
digest, one load. A sidecar would need its own digest binding and its own integrity gate to say
the same thing, which is a second contract for no gain.

Three facts settle the placement against the size objection:

- `compatibility_store.embedded_compatibility_manifest` is `@lru_cache(maxsize=1)`. The manifest
  parses once per process, not per resolution.
- Measured cost: minting a `RequestSchema` from `api/tests/fixtures/codex_response_create.json`
  (2,130 bytes of request) yields 8,892 bytes of compact JSON. The plan's measurement over 16
  real cells averaged 7.2 KB. The manifest is 16,805 bytes today, so a full 16 cell cohort takes
  it to roughly 130 KB.
- `_require_digest_integrity` and `_require_certified_active_pointers` already run at embedded
  load. Inlining puts the references behind both without new machinery.

**Vocabulary module.** `harnesses/compatibility.py` is 649 lines, 51 from the hard limit. The
reference model goes in a new pure module, `harnesses/release_reference.py`, and `compatibility.py`
takes a field, an import, and the cross reference validator only.

**One reference, per launched model**, keyed to match what the launch path can look up:

| field | source | why |
| --- | --- | --- |
| `route_id` | `HarnessModelCompatibility.route_id` | one route's blessing grants none to another |
| `launch_model_id` | `BaselineCell.launch_model` | the alias the operator launched, so an alias repoint stays visible |
| `canonical_model_id` | matching target edge | binds the reference to a certified edge |
| `effort` | `VerificationCell.effort`, nullable | see Open Decision 2 |
| `observed_harness_version` | `BaselineCell.harness_version` | proves capture at the ceiling |
| `request_schema` | `GateProjection.request_schema` | the reference itself |
| `request_schema_digest` | `canonicalization.canonical_digest` | verdict addressing and invalidation |

Entry validation requires unique `(route_id, launch_model_id, effort)`, an existing route, an
existing target edge, and `observed_harness_version == compatibility.blessed_ceiling(release)`.

**Naming hazard to close in the same change.** `HarnessCompatibilityRelease.schema_digests`
already holds three harness level opaque digests keyed `wire_request`, `wire_response`,
`transcript`. A per model `request_schema_digest` is a different fact at a different grain.
Name that distinction in the field docstring, and do not extend `schema_digests`.

**Do not reuse the bundle's own reference fields.** `baseline_evidence.BaselineBundle` already
carries `reference_bundle_id`, `reference_outcome`, `reference_findings`, and
`reference_content_report`, written by `baseline_capture.harvest_controlled_baseline` when a
peer bundle is passed. That is bundle to bundle model dependence, a different question with a
different authority. The release reference must never be written into those fields.

## 2. The production caller of SupportState

Two call sites, one write and one read. Both are required: a verdict nobody reads is what
`assess_baseline_staleness` already is.

### Write site

**`launch_verification.LaunchVerificationCoordinator._verify_under_lock`**, immediately after
the `has_baseline_bundle_for_version` durable evidence check and before
`finish_baseline_attempt` records `SUCCEEDED`.

That is the only place three facts are known at once: a fresh candidate bundle, the concrete
`VerificationCell` the launch exercised, and the installed version proved equal to the captured
version by the check directly above. The method already runs off the launch path under
fire and proceed, so the assessment costs the operator no latency, and it already owns a cell
lock, so two launches cannot race one verdict.

The sequence is: `project_baseline(bundle).gate.request_schema` for the candidate, the matching
`release_reference` for the reference, `support_state.assess_support_state(reference=, candidate=)`,
then write the verdict. Argument order is the contract; the reference is the release's, always
on the left.

A capture with no matching reference writes no verdict. That is the same answer
`verification_cell.NoVerificationCell` gives, for the same reason: naming a verdict against a
reference that does not exist would file evidence about a comparison nobody made.

**Verdict home**, per the brief:

```text
<channel home>/baselines/verdicts/<release digest>/<launch model>/<normalized version>.json
```

Addressed and validated by `release_id`, `release_digest`, `route_id`, `launch_model_id`,
`effort`, `normalized_harness_version`, `reference_schema_digest`, `candidate_bundle_id`,
`candidate_schema_digest`, and a support deriver digest. A changed release, reference, candidate,
or deriver is a cache miss, re-derived from the signed release and the immutable bundle. This is
the rule `baseline_projection_store.read_gate_projection` already applies to derived state, and
the verdict follows it rather than inventing a second staleness policy.

### Read site

**`harnesses/resolver_snapshots.resolver_snapshots_for_harness`** loads the verdicts for the
harness into `ResolverSnapshots`. `harnesses/resolver.launch_options` then decorates each
`LaunchOption` with a support state, and `api/v1/harness_launch_view` projects it onto
`LaunchModelView` and `LaunchModelDeviation`.

Reading through the snapshot preserves the property `launch_options` documents about itself:
pure over the same snapshots `resolve_target` consumes. The resolver must not grow a filesystem
read. Cost is one small JSON read per cell, which is the cost `baseline_staleness` already
justifies in its module docstring: sixteen current pointers total 4,263 bytes against 56 MB of
bundles.

### What the operator sees

Today a version above the blessed ceiling surfaces as `HarnessCompatibilityInfo.range_position ==
"above_ceiling"` and nothing more. `compatibility.match_release` documents that state as "due for
wire schema comparison"; no code performs the comparison, and no surface reports its result.

After this slice, the launch picker shows, per model:

- **blessed**, when the installed version's captured schema carries everything the reference
  carries. Additional properties are listed as findings and do not change the state.
- **degraded**, with the missing pointers, when it does not.
- **nothing at all**, when no comparison has run. Absence of a verdict is a third answer and
  never a synonym for either state, matching `SupportState`'s own docstring.

`above_ceiling` therefore stops being a dead end. The operator learns whether the new version is
actually supportable, per model, which is the question the whole chain exists to answer and
cannot currently ask.

## 3. The authoring flow

Publishing a blessing stays a deliberate operator act. Four steps, three of them existing.

**Step 1. Capture the cohort. Billed.** The operator launches each cell of the target harness at
the version being blessed. `launch_verification.LaunchVerificationCoordinator` already captures
A/B/A per cell through `baseline_capture.harvest_controlled_baseline`, three provider turns per
cell, and records the attempt through `baseline_attempts`. A full claude cohort is ten aliases.
There is no offline path for a first release: the shipped certification records retain one way
digests only, both shipped mint plans cite run directories that no longer exist, and all three
channel homes contain no `baselines` directory, verified at this SHA.

**Step 2. Publish the projections.** `uv run python -m transport_matters.baseline_publish --harness <id>`,
which calls `baseline_projection_store.publish_gate_projections` and prints the deriver digest.
Existing script, unchanged.

**Step 3. Assemble the release references.** One new operator path that reads each current gate
projection, refuses a cohort whose cells disagree on harness version, source identity, runtime
template, or provider, and emits the `references` array plus the certification provenance for
each entry.

This extends `scripts/mint_harness_certification_record.py` rather than adding a fourth argparse
shell. `baseline_compare.main` and `baseline_publish.main` are already a 0.945 similarity pair; a
third copy is the duplication this repository does not tolerate.

**Step 4. Certify and activate.** `MintPlan` gains immutable bundle bindings beside its existing
`scenario_bindings`. `certification.CertificationRecordV1` gains a reference evidence collection
binding each release reference key to its bundle id, observed version, source identity, deriver
digest, three `probe_request_sha256` values, and canonical schema digest.
`certification.validate_certification_for_release` requires exact key and digest equality between
record and release. `_require_certified_active_pointers` then refuses to activate a pointer whose
release ships a reference the record does not vouch for.

That closes the current hole where `scripts/reseal_compatibility_manifest.py` can make a hand
edited release self consistent. Resealing proves package integrity; it proves nothing about where
a schema came from. With the binding in place a hand edited reference cannot activate.

**What it writes:** bundles and projections under the channel home, one certification record
under `harnesses/certification_records_v1/`, and one edited `compatibility_releases_v1.json`.
**What it bills:** three provider turns per cell, at the operator's own quota. Nothing else in
this slice makes a provider call.

## 4. The migration answer

**No data migration. Two package contract bumps. Zero on disk bumps.**

- **`manifest_schema_version` 1 to 2, required.** `_CompatibilityModel` is `extra="forbid"`, so an
  older reader cannot parse a manifest carrying `references`, and a newer reader must not accept a
  v1 entry that omits them. Replace all three embedded releases in one change.
- **`CertificationRecordV1.schema_version` 1 to 2, required**, for the reference evidence
  collection. Migrate the three embedded records with the manifest, in the same change. No
  parallel v1 and v2 authoring path: the repository is pre release and a staged duplicate contract
  buys nothing.
- **`BaselineArtifactSchemaVersion` stays at 8.** #437 moved it from 7 for `StructureDelta`.
  Nothing in this slice changes bundle shape. Do not bump it again.
- **The verdict artifact takes no schema version at all.** It is addressed by the digests it
  validates against, including a support deriver digest, so a changed shape is already a cache
  miss. `GateProjection` documents exactly this reasoning and this artifact follows it. A second
  constant could only agree or go stale.
- **Nothing on disk to migrate.** All three channel homes were checked at this SHA:
  `~/.transport-matters`, `~/.transport-matters-preview`, and `~/.transport-matters-dev` each
  contain `electron-user-data`, `executor-id`, `runtime`, `settings.toml`, and `workspaces`, and
  no `baselines` directory. There are no bundles, no projections, no attempts, and no verdicts to
  carry forward. The window where bumps are free is open now and closes at the first capture.

One prerequisite defect, not a migration but a blocker for the read site. `resolver_targets.decorate_target`
matches a target edge on `(route_id, observation.native_model_id)`. The claude probe emits CLI
selectors (`opus`, `sonnet`) while `compatibility_releases_v1.json` names canonical ids
(`claude-opus-4-8`), so zero of ten claude targets currently match an edge and every one falls
back to `observed_unverified`. A reference keyed the same way inherits the same miss. Fix the
identity join before or with the read site, or claude verdicts will be written and never found.

## 5. Deliberately out of scope

- **Widening the shipped range from a local verdict.** See Open Decision 1. This slice reports
  against the range and never edits a signed release.
- **Gating.** No launch is refused, delayed, or altered by a verdict. The ceiling never refuses,
  and this slice does not become the exception.
- **Physical deduplication of reference schemas.** Roughly 130 KB parsed once per process does not
  justify content addressing inside the package. If it later does, every model still keeps an
  explicit logical reference; a protocol class never becomes the storage key.
- **`baseline_comparison.fold_model_equivalence_classes` and `compare_model_pair`.** Peer
  diagnostics, unchanged. The worst of both fold must never reach `assess_support_state`.
- **The `request schema -> IR -> overlay` significance map.** `support_state` presumes today that
  any missing property degrades the overlay. Deciding which lost properties Transport Matters
  actually models is the work its `additional_properties` queue exists to feed, and it is not this
  slice.
- **A Postgres representation of verdicts.** `harness_drift_evidence` cannot express blessed with
  no finding, and a current pointer is an unstable key for a version decision. A query cache keyed
  by the same digests may come later and must never become the authority.
- **Retrofitting the three shipped releases.** Their evidence is gone. They get new references
  from a fresh cohort or none.
- **`assess_baseline_staleness` finding its caller.** Named above as precedent and left alone.

## Open decisions for the owner

**1. Does a local blessed verdict extend the blessed range, or only report against it?**
The brief says verification lazily extends the range for an unknown installed version.
`docs/HARNESS-COMPATIBILITY.md` says a declared `maximum_version` is the publisher's explicit
blessing, "recorded when the wire schema comparator cleared versions the certification run never
observed, which is how a later release widens its range without re-certifying at every version it
covers". Those describe different owners of the extension: the operator's machine, or the next
published release. A signed release cannot be edited locally, so if the verdict extends anything
it extends a local overlay that `blessed_ceiling` does not see.
*Recommendation:* the verdict reports, and a subsequent release widens `maximum_version` using
verdicts as its evidence. This keeps one authority for the range and needs no new local override
of signed data.

**2. Is the reference keyed per model, or per model and effort?**
`verification_cell.VerificationCell` carries `effort`. `baseline_evidence.BaselineCell` does not,
and neither does the baseline store key. A per effort reference multiplies both the billed cohort
and the package by the effort count; a per model reference silently assumes schema invariance
across accepted efforts, which no current certification record proves.
*Recommendation:* record `effort` on the reference, capture the default effort only for the first
release, and require an explicit evidence pass before claiming invariance. This is a spend
decision as much as a correctness one.

**3. Advisory or eventually enforcing?**
This slice ships advisory, matching the ceiling's own rule. Whether `degraded` should ever
withhold a launch, or only ever inform, changes what the verdict is for.
*Recommendation:* advisory permanently for `degraded`, since the operator launching a degraded
version is how the next reference gets captured.

**4. Which cohort, and who authorizes the spend?**
A first v2 release requires live capture of every cell it blesses. Ten claude aliases, three
codex, two grok, at three provider turns each, is 45 turns against the operator's own quota. All
three harnesses at once, or one harness first.
*Recommendation:* codex first. Three cells, nine turns, and the fixture corpus for the responses
profile is already the best covered in the repository.

## Verification of the claims in this spec

Every structural claim was read at the SHA above. The three that were measured rather than read:

- `RequestSchema` compact size, minted live from `api/tests/fixtures/codex_response_create.json`
  through `mint_request_schema(profile=RequestSchemaProfile.RESPONSES, ...)`: 8,892 bytes.
- `compatibility_releases_v1.json`: 16,805 bytes, `manifest_schema_version` 1, three releases,
  nine target edges, every one `support_tier: observed_unverified`.
- Channel homes: no `baselines` directory in any of the three, listed above.

The claim that `assess_baseline_staleness` and `SupportState` have no production callers is a
grep over `api/` for each symbol, excluding tests: every hit is a test module or a docstring.
