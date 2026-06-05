---
title: What the Baseline Bundle Must Contain to Remain Evidence — Scout Artifact Integrity
type: research
tags: [transport-matters, baselines, evidence, artifact-schema, request-schema, integrity, cleanup]
summary: Only the raw probe bytes are evidence. 79.7% of the store is a cache of derivations the reader already recomputes on every read, and the one derivation nobody recomputes has already gone stale, leaving #424 inert against all 16 stored bundles. Dedup is the wrong question, the schema split should carry the comparator's whole input rather than the schema alone, and the version bump is owed rather than merely affordable.
status: active
source: scout
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/transport-matters
commit: 13cee80c
created: 2026-08-23
updated: 2026-08-23
---

## Executive Summary

The bundle's integrity claim rests on one field per probe. `probes[].raw_request_base64` is
the evidence. Everything derived from it is recomputed and re-checked on every single read,
by `ProbeEvidence.validate_raw_evidence` and `BaselineBundle.validate_probe_contract`, so
storing those derivations buys nothing evidentiary. Measured across the operator's real
store: 79.7% of the compact bytes re-derive from the raw bodies with exact model equality.

Five findings change the shape of the cleanup.

1. **The dedup question is malformed.** Identical leaves are not repeat copies of evidence.
   The whole `inventory` and `raw_nodes` payload (20.37 MB, 47.2% of the store) is a pure
   function of the raw body it sits next to, verified as such on every read. Deduplicating
   it compresses a cache. Deleting it loses nothing and saves four times as much.
2. **The one derivation nobody recomputes has already gone stale, in production, silently.**
   `pointer_evidence` disagrees with today's `classify_aba` on 16 of 16 stored bundles, and
   `runtime_generated_pointers` on 14 of 16. Every bundle was minted 2026-08-21; #424
   changed the classifier on 2026-08-22 and did not bump `artifact_schema_version`.
3. **#424 is therefore inert against the operator's store.** Because
   `content_observations.excluded_pointers` is validated against the *stored*
   `runtime_generated_pointers`, the comparator still excludes `/system/2/text`. 41 of 45
   claude cross-model pairs report a different content finding count against a re-classified
   store. The model-dependent system prose that #424 exists to expose is still invisible.
4. **The comparator's real input is 1.73% of the store.** All 16 cells' gate input reduces
   to 748,643 bytes. Today `baseline_compare` reads 46.4 MB and spends 2.01 s reading to do
   0.37 s of comparing.
5. **The bump is owed, not merely affordable.** Zero bundles carry an operator acceptance, so
   nothing human-judged is destroyed, and the store already needs a re-harvest for
   correctness because of findings 2 and 3.

Recommendation in [Decision](#decision): delete the derived fields rather than dedup them,
publish a verifiable gate projection carrying the comparator's whole input rather than the
schema alone, and bump to 6 now while the bump costs 48 billed turns and no judgment.

## Measured Ground Truth

All measurements read-only against `~/.transport-matters/baselines` at `13cee80c`, through
the repo interpreter. Sizes are compact JSON bytes unless stated. On-disk (pretty) total is
56,230,184 B; compact total is 43,195,865 B across 16 bundles.

### Where the bytes are

| field | bytes | share |
| --- | ---: | ---: |
| `probes[].inventory` | 14,577,094 | 33.75% |
| `probes[].raw_request_base64` | 7,782,232 | 18.02% |
| `pointer_evidence` | 6,090,400 | 14.10% |
| `probes[].raw_nodes` | 5,797,173 | 13.42% |
| `content_observations` | 4,578,438 | 10.60% |
| `static_nodes` | 1,899,367 | 4.40% |
| `observed_schema` | 1,363,927 | 3.16% |
| `probes[].transcripts` | 962,816 | 2.23% |
| `request_schema` | 101,969 | 0.24% |
| everything else, including structural bytes | 42,449 | 0.10% |

The raw request bodies themselves are 5,836,559 B. Base64 costs 1,945,673 B, 4.5% of the
store, for a field the reader base64-decodes on every read anyway.

### What re-derives from the raw bodies

Rebuilt through the production functions and compared for full model equality, not the
`(pointer, value, sha256)` triple that `validate_raw_evidence` settles for.

| field | rebuilt by | matches |
| --- | --- | ---: |
| `probes[].inventory` | `build_request_inventory` | 16/16 |
| `probes[].raw_nodes` | `observe_request_json` | 16/16 |
| `request_schema` | `mint_request_schema` | 16/16 |
| `content_observations` | `build_content_observations` | 16/16 |
| `observed_schema` | `classify_aba` | 16/16 |
| `static_nodes`, `static_fingerprint` | `classify_aba` | 16/16 |
| `pointer_evidence` | `classify_aba` | **0/16** |
| `runtime_generated_pointers` | `classify_aba` | **2/16** (grok only) |

Bytes removed if every recomputable field goes: 34,415,281 B, **79.7%** of the store.

### Alternative shapes

| shape | bytes | share |
| --- | ---: | ---: |
| stored today | 43,195,865 | 100.0% |
| evidence only, derived fields deleted | 8,780,584 | 20.3% |
| evidence only, gzipped | 3,160,774 | 7.3% |
| comparator input, reduced to what the gate reads | 748,643 | **1.73%** |
| `request_schema` plus cohort coordinates alone | 114,865 | 0.27% |

Per-cell timings, `claude/best`, 4,477,021 B on disk:

| operation | ms |
| --- | ---: |
| `read_baseline_bundle` today, including all revalidation | 200.6 |
| re-mint `request_schema` from the raw bodies | 17.0 |
| re-run `classify_aba` | 104.7 |
| rebuild `content_observations` | 42.9 |

Whole-cohort gate cost today, through `read_current_baselines` and `compare_model_cohort`:
claude 10 cells, 46,430,536 B read, 2.01 s reading, 0.37 s comparing, 45 pairs, 2 classes.

## 1. The Integrity Claim

### What a reader is entitled to conclude

From one bundle a reader may conclude, and nothing more: *these exact bytes were sent on the
wire by harness H at version V, launching model M, resolving to wire model W, under a fully
pinned capture plan, from a Transport Matters checkout at `source_commit` whose worktree was
clean, across three probes correlated to their prompts by delivery id.*

Each clause has one carrier.

| clause | carrier |
| --- | --- |
| these exact bytes | `ProbeEvidence.raw_request_base64` with `raw_request_sha256` |
| harness, version, models | `BaselineCell`, cross-checked against `RequestInventory.capture` in `validate_probe_contract` |
| pinned capture plan | `BaselineCell.no_system_prompt`, `bypass_permissions`, `isolated_home`, `runtime_template` |
| which home, at which generation | `BaselineTemplateIdentity.content_digest`, the only one of its three digests taken over the bytes actually present |
| observed by which code | `BaselineBundle.source_commit`, produced by `certification_minting.require_clean_worktree` |
| which prompt produced which probe | `ControlledPrompts` plus `ProbeEvidence.prompt_sha256`, re-checked in `validate_probe_contract` |
| chain of custody back to the run | `delivery_id`, `run_id`, `exchange_id`, `correlation_method`, `TranscriptEvidence` |

Two guarantees sit underneath. `write_baseline_bundle` reads its own artifact back and
refuses on inequality, so a bundle that exists was written whole. `read_baseline_bundle`
revalidates the entire model on every read, and that validation recomputes the derived
fields from the raw bytes and refuses a mismatch.

### Does dropping repeat copies of identical leaves preserve that conclusion?

Yes, and the question understates the result. The leaves never carried the conclusion. They
are a projection of `raw_request_base64` that `validate_raw_evidence` rebuilds and compares
on every read, which is why they can never disagree with the raw body in a bundle that reads
at all. Storing them is caching, and deduplicating them is compressing a cache.

Two corrections to the premise are worth stating.

**`pointer_evidence.value_sha256_by_probe` cannot serve as the independent per-probe record
that rescues a dedup.** Since #424 those digests are taken over
`observe_request_json(canonical_json(_masked_request_body(probe)))`, so they are digests of
the *masked* node tree with the cross-launch identity keys dropped. They are not digests of
the stored leaf values and they are not comparable to `RequestStringLeaf.sha256`. Measured:
moving that axis to the masked body changed 12 pointer digests per claude bundle and 10 per
codex bundle. The field records a different object than the one a dedup would be dropping.

**The per-leaf payload is mostly constant, not mostly evidence.** Across 21,531 leaves in the
store: `provenance.kind` is `unknown` 21,531 times, `token_count.quality` is `estimate`
21,531 times. `api_role` and `tm_ir_section` do vary, and both are computed by
`request_inventory._provider_semantics` from the raw path and `capture.provider`, so both
recompute. There is no leaf field whose value is not a function of the raw body.

### The one place the claim is genuinely weaker than it looks

`validate_probe_contract` verifies `request_schema`, `content_observations` and the
`static_fingerprint`-to-`static_nodes` relation. It never verifies `observed_schema`,
`pointer_evidence`, `static_nodes` or `runtime_generated_pointers` against
`classify_aba(prompts, probes)`. Those four are accepted as written. Section 2 shows what
that cost.

## 2. A/B/A After Dedup

### Recomputation survives, provided the raw body survives

`classify_aba` reads two axes. The node axis comes from `_masked_request_body(probe)`, which
decodes `raw_request_base64` directly. The leaf axis comes from `probe.inventory.leaves`,
which is a pure function of the raw body and `inventory.capture`, proved above at 16/16 with
full equality. `build_content_observations` reads `_masked_request_body` only.

So: keep `raw_request_base64`, `cell`, `prompts` and `capture`, delete every derived field,
and `classify_aba`, the static and runtime-generated partition, `mint_request_schema` and
`build_content_observations` all still compute, today and for any future reader running the
code at `source_commit`. Nothing in the A/B/A mechanism reaches for a stored derivation.

The single dependency worth naming is `session.wire_normalization.mask_cross_launch_body`.
The masking is code, versioned by `source_commit`, and a future reader who wants the
classification exactly as it was minted needs that commit rather than a stored copy of the
answer.

### The real hazard runs the other way

The brief warns about a change that keeps today's computation working while destroying
tomorrow's ability to recompute. The store shows the mirror-image failure has already
happened, and it was caused by storing the derivation rather than by dropping it.

Every one of the 16 bundles was generated 2026-08-21. #424 (`a2401a29`, 2026-08-22) moved
the node axis to the masked body and did not touch `artifact_schema_version`. The result:

| harness | cells | `pointer_evidence` differs | fields that moved | `runtime_generated_pointers` stored-only |
| --- | ---: | ---: | --- | --- |
| claude | 10 | 10/10 | 12 digests, 2 classifications, 2 reasons | `/system/2/text` |
| codex | 4 | 4/4 | 10 digests, 3 classifications, 3 reasons | `/input/N/content/0/text` |
| grok | 2 | 2/2 | 1 digest | none |

Pointer sets are identical on every bundle, so no pointer appeared or vanished. What moved is
the classification of pointers that were always there.

### The consequence: #424 does not reach the operator's evidence

`validate_probe_contract` rebuilds `content_observations` with
`excluded_pointers=self.runtime_generated_pointers`, the *stored* one. Every read of a stored
claude bundle therefore still excludes `/system/2/text` from the content axis, which is the
exact pointer #424 was written to stop excluding.

Measured through `compare_content` over the real cohorts:

| harness | pairs | pairs whose content finding count changes under re-classification |
| --- | ---: | ---: |
| claude | 45 | **41** |
| codex | 6 | 0 |
| grok | 1 | 0 |

The hidden value is model-dependent, which is why it matters. At address
`('system', '/system[type:literal:text]/text')` the re-classified digest is
`f769d38…` for `best` and `opus`, `0c145e9…` for `default`, `opusplan` and `sonnet`,
`641e4f3…` for `fable`, `cda1614…` for `fable[1m]`, `d300ab4…` for `opus[1m]`,
`529bd7b…` for `sonnet[1m]`, `ba8ae47…` for `haiku`. Read from the stored bundles, none of
these exist and the address looks identical across all ten models.

So the answer to the brief's question is yes, A/B/A is fully reconstructible after dedup, and
the finding that matters is adjacent: the artifact already contains a superseded
classification that no validator catches, no version rejects, and the comparator silently
trusts.

## 3. Should `request_schema` Be Separable?

**Recommendation: publish a gate projection, not a schema.** The #427 and #428 pattern
applies, with one correction to what the small thing is.

### The schema alone does not free the gate

`baseline_comparison._compare_direction` reads two fields:
`compare_request_schema(reference.request_schema, candidate.request_schema)` and
`compare_content(reference.content_observations, candidate.content_observations)`.
`require_comparable_model_cohort` additionally reads `artifact_schema_version`, six `cell`
coordinates including `runtime_template`, and `prompts`; `has_mixed_source_commits` reads
`source_commit`.

Putting `request_schema` on the pointer, at 0.24% of the store, would leave
`content_observations` behind and the comparator would still open every bundle. The split has
to carry the comparator's whole input or it buys nothing.

### Sized honestly

| projection | bytes, all 16 cells | per cell |
| --- | ---: | ---: |
| `request_schema` plus cohort coordinates | 114,865 | 7.2 KB |
| plus `content_observations` verbatim | 4,693,687 | 293 KB |
| plus `content_observations` **reduced to what the gate reads** | 748,643 | 46.8 KB |

The reduction is not lossy for the gate. `compare_content` immediately folds the stored
leaves through `_content_values` into a `Counter` of value digests per `(group, address)`,
discarding `probe` and `pointer` after applying the exclusions. 18,612 stored leaves reduce
to 3,477 address entries, 14.1% of the field, and `compare_content` cannot tell the
difference.

748,643 bytes for the entire store, against the 46.4 MB and 2.01 s the comparator reads
today.

### Does it fragment the evidence?

No, because neither field is evidence. Both are recomputable from the raw bodies, at 17.0 ms
and 42.9 ms per cell, so a projection is a cache and a bundle remains the sole authority. That
is the same shape as #427 and #428: denormalize the small derived thing the consumer needs
into the cheap place, leave the authority where it is.

**Strongest objection**: a sidecar that disagrees with its bundle is worse than a slow read,
and this store has already proved that Transport Matters ships derived state that goes stale
silently and that nothing detects it. A projection that repeats the `pointer_evidence`
mistake gives the comparator a fast wrong answer.

**The mitigation that makes it acceptable**: the projection must carry the three
`raw_request_sha256` values and the `source_commit` it was minted from, so staleness is
detectable in the cheap read itself, and re-minting from the bundle verifies it. Under that
rule the projection is a cache with a validity token rather than a second source of truth.

## 4. Artifact Schema Version

**Assessment: genuinely near-free right now, and owed rather than merely affordable.**

### What a bump to 6 costs

- All 16 bundles become unreadable through `read_baseline_bundle`, which raises
  `unsupported baseline bundle schema; regenerate the baseline`.
- All 16 current pointers become unreadable too. `_CurrentBundlePointer` declares the same
  `BaselineArtifactSchemaVersion` literal, so `_read_pointer` raises
  `unsupported baseline current pointer schema; regenerate the baseline`. This is the part
  that is easy to miss: `read_current_baseline`, `read_current_baselines` and the new cheap
  `read_current_baseline_ref` stop returning `None` for a missing baseline and start raising
  for an old one. Any caller that treats absence as a normal state, including the staleness
  path added in #429, needs to survive that.
- 48 billed provider turns, three per cell across 16 cells.
- The comparator produces nothing until the re-harvest completes.

### What it forces, and why the bill is owed anyway

Nothing human-judged is destroyed. All 16 current pointers carry `accepted_by: null`, so no
`accept_degraded_baseline` decision exists to lose. All 16 also carry no `harness_version` and
still hold an absolute `path`, so they predate #427 and #428 and are due a rewrite regardless.

More decisively, sections 2 and 3 show the store is not merely old. It carries a superseded
classification, and the #424 fix does not reach 14 of its 16 bundles. A re-harvest is required
for the comparator to be correct, independent of any cleanup. The bump does not create that
cost, it names it.

### What would make it expensive later

- **An accepted bundle.** `accept_degraded_baseline` records an operator identity and
  timestamp, and there is no migration path for that judgment. The first accepted degraded
  baseline turns a free bump into a destroyed human decision.
- **Continuous capture.** Once launch-triggered capture keeps bundles flowing, the
  invalidation window stops being a one-off re-harvest and becomes a live gap in the gate.
- **Cell count.** 48 turns is linear in cells. Adding harnesses or models scales the bill
  directly.

### The structural point behind the bump

`artifact_schema_version` gates on exact equality and covers the artifact's *shape*. It has
never covered the artifact's *derivations*, which is why #424 could change what
`classify_aba` produces while every stored bundle stayed readable and wrong. A cleanup that
only bumps the number reproduces the same hazard on the next classifier change. Either the
derived fields leave the artifact, which is the recommendation, or the version has to cover
the code that produced them.

## Quality Map

### Sizing

| module | lines | longest unit | against the limits |
| --- | ---: | --- | --- |
| `baseline_evidence.py` | 612 | `BaselineBundle` 74, `classify_aba` 66 | under 700, but holding contracts, classification and content comparison |
| `request_schema.py` | 584 | `_compare_items` 57 | under 700 |
| `request_inventory.py` | 517 | `_make_leaf` 43 | comfortable |
| `baseline_capture.py` | 404 | `harvest_controlled_baseline` 125 | approaching the ~150 function guidance |
| `baseline_comparison.py` | 259 | none over 40 | comfortable |
| `baseline_store.py` | 242 | none over 40 | comfortable |

No module is over the hard limit. The pressure on `baseline_evidence.py` is cohesion rather
than length: it owns the frozen contracts, the A/B/A classifier and `compare_content`, and
deleting the derived fields would take roughly 200 lines out of it on its own.

### Dead code

- **`EvidenceKind.SESSION_GENERATED` can never be produced.** `_session_derived` requires
  every present leaf to carry `provenance.kind == "session-derived"`, but the only production
  caller of `build_request_inventory` is `baseline_capture._build_probe_evidence`, which
  passes no annotations, so every leaf gets `_unknown_provenance`. Measured: 0 of 12,777
  stored classifications are session-generated; 21,531 of 21,531 leaves are `unknown`. The
  branch, the enum member and the 2.48 MB of constant provenance that feeds it are all inert.
- **`RequestInventory.aggregate`, `RequestInventory.require_leaf`, `RequestTextAggregate` and
  `RequestLeafReference`** have no caller anywhere outside `request_inventory.py` and its
  tests. `aggregate` is the only caller of `require_leaf`, so the four form a closed unused
  cluster.
- **`LeafAnnotation` and `AuthoritativeTokenCount`**, with
  `_annotations_by_pointer`, `_authoritative_counts_by_pointer` and
  `_validate_annotation_against_provider`, exist to serve two `build_request_inventory`
  parameters that no production caller supplies. Roughly 90 lines of validated machinery for
  an unexercised path.
- **`model_dependence_assessed: Literal[False] = False`** is declared on both `AbaAnalysis`
  and `BaselineBundle`, set once in `baseline_capture`, and read by nothing.
- **`observed_schema`, `pointer_evidence`, `static_nodes`, `static_fingerprint` and
  `raw_nodes`** have no reader outside the writer that sets them and the bundle's own
  validator. No Python, TypeScript, JSON or Markdown consumer in the repo reads them. That is
  15.15 MB, 35.1% of the store. The authoritative field-consumer map belongs to the other
  scout; this is the evidentiary reading of it.

### Duplication

- **RFC 6901 escaping in three places**: `request_inventory._escape_pointer_token`,
  `request_schema._child_pointer`, and inline inside `baseline_evidence._content_address`.
  Three copies of `replace("~", "~0").replace("/", "~1")`, and `_covers` in
  `baseline_evidence` documents why that escaping is load-bearing.
- **The sha256 field pattern**: `request_inventory` already publishes
  `type Sha256Hex = Annotated[str, Field(pattern=...)]`, and `baseline_evidence` declares the
  same raw pattern inline five times, on `TranscriptEvidence.sha256`,
  `ProbeEvidence.prompt_sha256`, `ProbeEvidence.raw_request_sha256`,
  `ContentStringLeaf.value_sha256` and `BaselineBundle.static_fingerprint`. The alias is
  already imported from the same module for other names.
- **The probe order check** exists twice, in `_require_probe_order` and inline at the top of
  `BaselineBundle.validate_probe_contract`, with two different error strings for one rule.
- **`default_storage_root() / "baselines"`** is spelled out in both `baseline_harvest` and
  `baseline_compare`, while `storage_roots` already establishes the pattern with
  `WORKSPACES_DIRNAME` and `default_workspaces_root()`.

### Boundaries

Import cost, measured as new `transport_matters` modules per import:

| module | tm modules | of which `session` |
| --- | ---: | ---: |
| `request_inventory` | 4 | 0 |
| `request_schema` | 6 | 0 |
| `baseline_evidence` | 73 | 16 |
| `baseline_comparison` | 74 | 16 |
| `baseline_store` | 74 | 16 |

`request_inventory` and `request_schema` are clean leaves. `baseline_evidence` costs eighteen
times more, from exactly two imports: `adapters` (50 modules) used for the single
`get_adapter_for_provider(...).request_schema_profile` lookup in `validate_probe_contract`,
and `session.wire_normalization` (34 modules, and the source of all 16 session modules) used
for `mask_cross_launch_body`. A pure-contract module, by its own docstring, reaches into the
session package to read a bundle. Both dependencies are one function wide and both are worth
inverting if the comparator is ever to run somewhere cheap.

### One correctness gap outside the artifact

`certification_minting.require_clean_worktree` documents that callers "run this before
evidence collection and again immediately before the record write, rejecting a HEAD that
moved in between". `baseline_harvest` calls it once, before three real launches. A commit
landing during a capture yields a bundle whose `source_commit` is not the code that observed
it, which is precisely the guarantee the field exists to make.

### Grooming recommendation

Ordered by value, not effort.

1. Delete the write-only derived fields from `BaselineBundle` and `ProbeEvidence`, and
   recompute on demand. Removes 79.7% of the store, removes the staleness hazard at its root,
   and makes `validate_probe_contract` shorter rather than longer.
2. Delete `EvidenceKind.SESSION_GENERATED`, `_session_derived`, and the annotation and
   authoritative-count machinery, or wire them to a real caller. Today they are validated
   dead weight that also inflates every leaf.
3. Give the sha256 pattern and the RFC 6901 escaping one home each, and fold the duplicated
   probe-order check into `_require_probe_order`.
4. Invert the two heavy imports out of `baseline_evidence`: pass the profile in rather than
   resolving an adapter inside a validator, and move `mask_cross_launch_body` to a leaf.
5. Add `default_baselines_root()` beside `default_workspaces_root()` in `storage_roots`.
6. Call `require_clean_worktree` a second time before `write_baseline_bundle` and refuse a
   moved HEAD.
7. Delete `RequestInventory.aggregate`, `require_leaf`, `RequestTextAggregate`,
   `RequestLeafReference` and `model_dependence_assessed`.
8. Give `request_inventory.py` a module docstring. It is the only one of the six without one.

## Decision

**Do not dedup. Delete, then project.**

- **Evidence to keep**: `raw_request_base64` with its digest, `transcripts`, the correlation
  identifiers, `cell`, `prompts`, `source_commit`, `generated_at`, `bundle_id`,
  `artifact_schema_version`, and the reference-comparison fields. That is 8.78 MB, 20.3% of
  the store, and 3.16 MB gzipped.
- **Derivations to drop**: `inventory`, `raw_nodes`, `observed_schema`, `pointer_evidence`,
  `static_nodes`, `static_fingerprint`, `runtime_generated_pointers`. Recompute on demand at
  104.7 ms per cell. Storing them saves 105 ms and costs 79.7% of the store, a stale
  classification, and an inert bug fix.
- **Comparator input to publish in the cheap place**: `request_schema` plus the reduced
  content projection plus the cohort coordinates, 46.8 KB per cell and 748,643 B for the whole
  store, carrying the three `raw_request_sha256` values and the `source_commit` it was minted
  from so a reader can detect staleness without opening a bundle and verify by re-minting.
- **Bump to 6 in the same change.** The re-harvest is already owed for correctness, no
  operator acceptance exists to destroy, and every pointer needs rewriting for #427 and #428
  anyway. Handle the pointer-literal blast radius explicitly: a version-5 pointer under a
  version-6 reader raises rather than returning `None`.
- **Do not ship a version that covers only the shape again.** Either the derivations leave the
  artifact, which is this recommendation, or the version has to cover the classifier that
  produced them.

If only one thing ships: recomputing `pointer_evidence` instead of trusting the stored copy
is the fix that makes 41 of 45 claude comparisons start telling the truth.

## Notes

- Read-only throughout. No writes to `~/.transport-matters`, no commits, no provider turns,
  no backend starts. Measurement scripts live in the session scratchpad.
- Field-consumer mapping is deliberately out of scope and belongs to the parallel scout. The
  reader counts here are the minimum needed to argue evidentiary sufficiency.
- The 9.06 MB cross-probe repeat figure from the brief was taken as given and not re-derived.
  It is superseded rather than contradicted: the 20.37 MB it sits inside does not need to be
  stored at all.
- `grok` is the only harness whose stored `runtime_generated_pointers` still matches today's
  classifier.
  The masking still moved one grok pointer digest; it moved none that the A1-against-A2 test
  would have marked runtime-generated, which is why its exclusion set is unaffected.
