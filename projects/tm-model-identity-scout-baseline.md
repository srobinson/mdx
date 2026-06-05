# Model identity, baseline and comparator side

Scout of `transport-matters` at `main` `03dc8d62`, read only. Every claim below was produced
either by reading the module named beside it or by a read only run against the live stable
store `~/.transport-matters/baselines` using `api/.venv/bin/python`. Nothing was written to
the repository or to the store.

## Answers

### 1. The fold, and whether EXACT is an equivalence relation

**EXACT proved transitive on the live store, and it is transitive by construction, not by luck.**

By construction. `request_schema:compare_request_schema` emits a gating outcome for exactly
seven differences: disjoint kind sets (breaking), an added kind (degraded), an added object
property (degraded), a removed observed property (breaking), an added array branch (degraded),
a removed observed branch (breaking), a changed discriminator grouping (degraded). Two findings
carry `outcome=None` and never gate: removed kinds, and lowered property presence.
`baseline_comparison:compare_model_pair` runs both directions and folds them with
`request_schema:report_outcome`, so each non gating one way finding meets its gating mirror in
the other direction (a removed kind is an added kind reversed). What survives is: a pair is
EXACT if and only if, recursively, kind sets are equal, property key sets are equal, array
branch key sets are equal, and the `opaque` flags agree. `present_in` and `observation_count`
are invisible to the relation. That is equality of a projection, and equality of a projection is
reflexive, symmetric and transitive.

Empirically, over the live cells at `03dc8d62`:

| harness | cells | pairs | reflexive | directional asymmetry | transitivity violations |
| --- | --- | --- | --- | --- | --- |
| claude | 10 | 45 | all EXACT | none | none of 1000 ordered triples |
| codex | 4 | 6 | all EXACT | none | none of 64 |
| grok | 2 | 1 | all EXACT | none | none of 8 |

The partition, 16 cells into 5 classes:

    claude  {best, default, fable, fable[1m], opus, opus[1m], opusplan, sonnet, sonnet[1m]} | {haiku}
    codex   {gpt-5.5} | {gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra}
    grok    {grok-4.5, grok-4.6}

What the class boundary actually is, from the gating findings: haiku sends
`/thinking/budget_tokens`, omits `/output_config`, and omits the `messages[role:literal:system]`
branch. `gpt-5.5` omits `/reasoning/context` and carries top level `/instructions` and `/tools`,
which the 5.6 cells move into the `input[type:literal:additional_tools]` branch. Both are real
protocol generation changes, and neither is legible from a model name.

Minimum honest fold: union find over the `ModelPairComparison` tuple already returned by
`baseline_comparison:compare_model_cohort`, joining on `outcome is DriftOutcome.EXACT`, then
assert that every intra class pair is EXACT and every inter class pair is not. That assertion is
the equivalence check itself, O(n squared) on a cohort of ten, and it makes the primitive refuse
an ill defined partition rather than return one. One function and one frozen dataclass in
`baseline_comparison`. No new comparison logic, no second definition of EXACT.

### 2. Re keying blast radius

Every production reader of `launch_model` and of the cell key:

- `baseline_evidence:BaselineCell.launch_model`, the field.
- `baseline_capture:harvest_controlled_baseline`, mints the cell and looks the reference up by it.
- `baseline_capture:_require_comparable_capture_plan`, requires the same `launch_model` on the reference.
- `baseline_store:_bundle_path`, the on disk path `bundles/<harness>/<provider>/<quote(launch_model)>/<bundle_id>.json`.
- `baseline_store:_write_current` and `_current_path`, the pointer path `current/<harness>/<provider>/<quote(model)>.json`.
- `baseline_store:read_current_baseline`, keyed lookup by `model=`.
- `baseline_store:read_current_baselines`, sort key.
- `baseline_comparison:compare_model_pair` (sort key and pair labels), `_compare_direction` (direction labels), `require_comparable_model_cohort` (error text).
- `baseline_compare:_print_report`, the `cell launch_model=... wire_model=...` line.

Nothing outside those six modules. Searching the package for imports of `baseline_evidence`,
`baseline_store`, `baseline_capture`, `baseline_comparison`, `baseline_compare` and
`baseline_harvest` returns hits only inside those modules and their co located tests: no API
route, no canvas reader, no CLI subcommand, no `pyproject` script, no justfile recipe.

Cost if a class became the unit of capture: schema breaking. `_CurrentBundlePointer` is
`extra="forbid"`, `read_baseline_bundle` refuses any `artifact_schema_version` other than
`BASELINE_ARTIFACT_SCHEMA_VERSION` 5, and both path builders would change shape, so the store
goes to version 6 and every stored cell is unreadable. Re capture is 16 cells at three real
probe turns each, 48 turns.

**That cost is not the reason to refuse it. Re keying disarms the gate.** A class name derived
from structure is content addressed by the very thing the gate watches. Key the store by it and
the first genuine protocol change makes the next capture miss its reference:
`read_current_baseline` returns `None`, `harvest_controlled_baseline` mints a bootstrap bundle
with `reference_outcome=None`, `baseline_store:promotes_baseline` returns True, and the drift is
promoted as the new current baseline with no comparison ever run. The alias is what the launcher
knows before a capture exists, so the alias must stay the storage key. The class is a derived
view.

One further constraint on any cross version reading of a class:
`baseline_comparison:_ModelCohortCoordinates` includes `harness_version`, and
`require_comparable_model_cohort` refuses a cohort that varies it. Nothing in this layer can
compare cells across harness versions today, so a class is scoped to one
`(harness, provider, harness_version)` and is matched across an upgrade by membership, never by
identity.

### 3. Trustworthiness of `wire_model`

Read from the request body. Not circular, so not a blocker.

The chain: `baseline_capture:_build_probe_evidence` sets `RequestCaptureProvenance.model` from
`captured.request_ir.model`, where `captured` comes from
`harnesses/certification_run_reader:read_captured_exchange`, which validates the persisted
`request.ir.json` bytes. The IR's model is parsed from the body by the provider adapter:
`adapters/anthropic:AnthropicAdapter.inbound_request` reads `data["model"]`,
`codex/request_parser:parse_codex_request` reads `data.get("model")`, and
`grok/adapter:GrokAdapter.inbound_request` re prefixes the codex parse. `model_ids:normalise_model`
only adds the provider prefix. `harvest_controlled_baseline` requires all three probes to observe
one wire model, and `baseline_evidence:BaselineBundle.validate_probe_contract` re checks
`capture.model == cell.wire_model` on every read of every bundle.

The only launch derived value in the cell is `launch_model`, taken from
`harnesses/probes:EnumeratedModel.model_id`. The data itself proves the two are independent: ten
claude aliases resolve to four wire models with a fan in no launch argument could produce
(`default` and `opusplan` both to `anthropic/claude-sonnet-5`; `best`, `opus` and `opus[1m]` all
to `anthropic/claude-opus-5`).

One caveat, not a blocker. A body that fails to parse yields `f"{prefix}unknown"` from
`adapters/anthropic:AnthropicAdapter.inbound_request` or from
`exchange_recorder/unparsed:unparsed_request_ir`, and that string would be stored as a wire
model. No live cell carries it.

### 4. Existing partition logic

**None found.** Searches run, all under `api/src/transport_matters`, tests excluded:
`equivalence|partition|protocol_generation|generation_id|equivalent` (only string `partition()`
calls in `transport_redaction`, `client_version`, `workspace`, `space/detection`,
`session/artifacts`, `harnesses/certification_evidence`, `storage/disk_layout`);
`groupby|union_find|disjoint_set` (no hits); `alias` (pydantic field aliases only);
`wire_model` (five production hits, all inside `baseline_capture`, `baseline_compare`,
`baseline_evidence`).

Per module, as the brief asked. `baseline_evidence`: `classify_aba` classifies pointers within
one cell across its three probes; `compare_content` compares two cells and never groups.
`request_schema`: `mint_request_schema` and `compare_request_schema` are per cell and per pair.
`drift_capture`, read in full: `detect_unknown_shapes` and `WireDriftObserver` classify unknown
request fields and unknown server event types per exchange for the addon, with no cross cell
notion at all. Harness state: `harnesses/connections:LocalTargetObservation` carries
`native_model_id`, `native_efforts` and `native_default_effort` and no wire model.

The only cross cell operation that exists is `baseline_comparison:compare_model_cohort`, which
produces unordered pairs through `itertools.combinations`. Nothing folds them.

A boundary note for the other scout: the alias to wire model mapping exists **only** inside a
captured `BaselineCell`. The launch and enumeration side has no wire model anywhere.

### 5. What names a class

No existing digest names a class, and no structural digest can be the durable lookup key.

`static_fingerprint` is rejected by evidence. It is `canonical_digest` over the masked
`static_nodes` in `baseline_evidence:classify_aba`, so it moves with content. Live values inside
the single claude class of nine: `best` and `opus` share `af601284cf53`, `default` and `opusplan`
share `828f88382996`, `sonnet` is `7da40d44c60a`, `opus[1m]` is `11aba891f700`. Eight distinct
fingerprints inside one class.

`canonical_digest(bundle.request_schema.model_dump(mode="json"))` is content stable, because an
opaque node carries no children by `RequestSchemaNode.validate_shape`. It still disagrees with
the comparator: it hashes `observation_count` and `present_in`, which `compare_request_schema`
treats as non gating. Demonstrated read only by taking the live grok schema, scaling every count
proportionally, and comparing: pair outcome `exact`, digests unequal. On today's 16 cells the
naive digest happens to reproduce the same five groups because every cohort has three probes with
identical presence. That is a coincidence of the current data, not a contract.

Recommendation: name a class by its members, with the lexicographically smallest `launch_model`
as representative, scoped to `(harness, provider, harness_version)`. If a digest is later wanted
for display or for an artifact, extract the comparator significant projection out of
`compare_request_schema` first so structural identity has exactly one definition. Adding a second
digest that approximates EXACT is the defect this repo would pay for later.

### 6. Cheapest first slice

Validated, with one correction and one amendment to the stated payoff.

Validated: pure functions over stored bundles, no capture change, no re keying. The fold is about
twenty lines against `compare_model_cohort` and it is the only way to see real cardinality before
committing to anything.

Correction: **the alias resolution reader is not a new capability and must not become a new
symbol.** `BaselineCell` already carries `launch_model` and `wire_model` together, and
`baseline_compare:_print_report` already prints both on its `cell` line. A projection over
`read_current_baselines` output is one comprehension. A named reader for it would be exactly the
kind of addition the Reuse Map rules out.

What the slice reveals that we do not already know:

1. That EXACT is an equivalence relation on the live cohorts at all, so a partition is well
   defined. The whole design rests on this and it was unproven before this scout.
2. That the class axis is orthogonal to both alias and wire model **in both directions**. One
   claude class spans three wire models; codex splits four wire models into two classes. Neither
   name is the axis, and now that is a measurement rather than a claim.
3. Cardinality, 16 cells into 5 classes, and the specific pointers that draw each boundary.

Amendment: the eight redundant claude cells are not the prize, and dropping them is the one thing
the partition cannot license. An alias re pointing to another generation is the most likely event
a harness release actually produces, `default` and `opusplan` resolving to sonnet today is exactly
that shape, and it is observable only by capturing that alias. Fold at report and gate time, keep
capture per alias. The win is a gate that fires once per class and names its members, instead of
nine alias level alarms for one protocol change.

### 7. Sizing

Production files this work would touch, current counts:

    baseline_evidence.py    617   (83 lines of headroom)
    request_schema.py       584
    drift_capture.py        480
    baseline_capture.py     404
    baseline_harvest.py     187
    baseline_store.py       183
    baseline_comparison.py  157
    baseline_compare.py      90
    model_ids.py             13

Co located tests: `test_baseline_evidence.py` 506, `test_baseline_capture.py` 290,
`test_baseline_harvest.py` 282, `test_request_schema.py` 227, `test_baseline_comparison.py` 219,
`test_baseline_compare.py` 136. All under the limit; no refactor first debt here.

Functions near the 150 line limit: `baseline_capture:harvest_controlled_baseline` at 127 lines is
the only one in reach, and it is the wrong home for any of this work anyway.
`baseline_harvest:main` is 95. Everything else in these modules is under 50.

Placement follows from those numbers and from the layering: the fold is pure and cross cell, so it
belongs in `baseline_comparison`, which already owns the cross cell contracts and has room.
Rendering belongs in `baseline_compare:_print_report`. Neither `baseline_evidence` nor
`request_schema` should receive this work.

## Reuse Map

- Reuse: `baseline_comparison:compare_model_cohort` already validates the cohort and returns every
  unordered pair with a symmetric `outcome`. It is the only input the fold needs. Do not re walk
  the store, do not re compare schemas.
- Reuse: `baseline_comparison:require_comparable_model_cohort` and `_ModelCohortCoordinates`
  already pin every coordinate other than model identity, harness version included. The fold
  inherits its scope from them and must not restate the coordinate list.
- Reuse: `request_schema:report_outcome` is the single severity fold, already promoted public and
  already used by `compare_model_pair`. A class summary over member pairs uses it, never a second
  severity order.
- Reuse: `request_schema:DriftOutcome.EXACT` is the join predicate. The relation is read off
  `ModelPairComparison.outcome`, never recomputed from findings.
- Reuse: `baseline_store:read_current_baselines` already enumerates the channel resolved current
  pointers, validates each pointer and bundle through `_read_current_pointer` and
  `read_baseline_bundle`, and returns them sorted. It is the only store entry point the slice
  needs.
- Reuse: `baseline_evidence:BaselineCell.launch_model` and `.wire_model` already carry the alias
  to wire mapping per cell, and `baseline_compare:_print_report` already prints both. The alias
  resolution view is a projection over these, not a new component.
- Reuse: `baseline_comparison:comparison_diagnostics` is the existing structure and content
  finding formatter, shared today by `baseline_compare` and `baseline_harvest`. Class level output
  reuses it for the representative pair.
- Reuse: `canonicalization:canonical_digest` is the repository digest helper, used by
  `baseline_evidence:classify_aba`, `harnesses/compatibility`, `harnesses/certification` and
  `harnesses/compatibility_facts`. If a class digest is ever added it uses this, over a projection
  extracted from `compare_request_schema`, never a fresh hash.
- Reuse: `baseline_compare:main` is the command pattern: standalone `argparse`, `main(argv)`,
  `--harness` and `--output` defaulting to `default_storage_root() / "baselines"`, stderr plus
  exit 2 for unusable evidence, plain `key=value` output. Class output extends this command; no
  new module, no new entry point.
- Existing infra: `storage_roots:default_storage_root` keeps stable, preview and dev separate. The
  invocation is `cd api && .venv/bin/python -m transport_matters.baseline_compare --harness X`.
  `api/pyproject.toml` registers only `transport-matters`; neither the comparator nor the
  harvester belongs in the user CLI.
- Similar checked and rejected: `baseline_evidence:AbaAnalysis.static_fingerprint` looks like a
  class name and is not one; see answer 5 for the live counter evidence.
- Similar checked and rejected: `baseline_capture:_require_comparable_capture_plan` pins the same
  `launch_model` on purpose, so it is the wrong shape for anything whose varying axis is model
  identity, and it must not be relaxed to admit a class.
- Similar checked and rejected: `harnesses/connections:LocalTargetObservation` records
  `native_model_id` and efforts per observed target. It is the launch side vocabulary and carries
  no wire evidence, so it cannot host or name a class.
- None found: no partition, equivalence, grouping or dedupe of cells by observed compatibility
  anywhere in the package. Searches listed in answer 4.

## Quality Map

- **Correction to an accepted blind spot, highest value finding here.** The brief records that the
  1M selection is invisible in the request body. It is not. The raw bodies of `opus` and
  `opus[1m]` differ at `/system/2/text`, which contains
  `You are powered by the model named Opus 5 (1M context). The exact model ID is claude-opus-5[1m].`
  The gate cannot see it because of a mismatch inside `baseline_evidence:classify_aba`:
  `_classify_pointer` builds pointer evidence from **raw** probe nodes, while `static_nodes` in the
  same function builds from `session/wire_normalization:mask_cross_launch_body` masked nodes.
  `/system/2/text` also carries a per probe workspace path and scratchpad path, so on raw values
  A1 differs from A2, `_runtime_generated_pointers` marks the pointer runtime generated, and
  `build_content_observations` then excludes it. Verified read only: masked A1 equals A2 for both
  bundles, and re running `build_content_observations` with that one pointer un excluded produces
  a `system` group finding between `opus` and `opus[1m]`. So this is a classification versus
  masking mismatch, fixable with no capture change and no new machinery, and the masked comparison
  is already trusted by `static_nodes` in the same function. It widens what content findings carry;
  content never gates, because `compare_model_pair` folds only `structure.outcome`, so the exposure
  is report noise and not a false gate. Scope this as its own change, not as part of the fold.
- **Effort blind spot, confirmed and now demonstrated on live data.**
  `baseline_capture:_run_probe` passes `effort=model.default_effort` and `BaselineCell` has no
  effort field, so effort is neither pinned nor compared. Live: `gpt-5.6-sol` was captured at
  `reasoning.effort="low"` while `gpt-5.6-luna` and `gpt-5.6-terra` are `"medium"`, and all three
  sit in one class. `/reasoning/effort` matches no `_OPAQUE_ROOTS` entry for the RESPONSES profile,
  so its value is invisible to structure and to content alike. The cohort is therefore already
  mixed on an uncontrolled coordinate. If a class is to mean protocol generation, effort must be
  pinned at capture or become a cell coordinate; leaving it is a standing correctness hole in the
  meaning of the partition, not only in drift detection.
- Duplication: `baseline_evidence:classify_aba` and `baseline_evidence:build_content_observations`
  each contain the same masked probe body preparation verbatim: base64 decode of
  `probe.raw_request_base64`, `decode_json`, the same `raw request body must be a JSON object`
  guard, `mask_cross_launch_body`, then a pop loop over
  `request_extras:CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. One private helper in that module
  removes both copies. The same exclusion additionally exists in two more shapes, as a pointer
  prefix set in `classify_aba`'s `identity_roots` and `carries_request_evidence`, and as a path
  prefix test in `request_schema:_inside_cross_launch_identity`. The vocabulary is shared through
  `request_extras`; the four applications of it are not.
- Boundary: `mask_cross_launch_body` masks string values in place and does not drop the identity
  keys, which is why both call sites follow it with a pop loop. If the helper above is added, the
  question of whether dropping belongs inside the mask should be answered explicitly rather than by
  a third caller repeating it; that change reaches `session/wire_normalization` and its own
  consumers, so it is not free.
- Boundary: the fold is only defined inside one harness version, by
  `require_comparable_model_cohort`. Any plan text that speaks of a class surviving a harness
  upgrade must say how membership is re established, because the comparator cannot answer it.
- Dead code: `baseline_evidence:AbaAnalysis.model_dependence_assessed` and
  `BaselineBundle.model_dependence_assessed` are both `Literal[False]` with the single writer
  `baseline_capture:harvest_controlled_baseline` and no production reader. Still true at
  `03dc8d62`. The fold must not add a sixth flag beside them; removal belongs to an artifact
  schema cleanup, not here.
- Sizing: no refactor first debt in the touched set. `baseline_evidence` at 617 is the closest to
  the limit and receives nothing in this plan.

## Plan

Decision needed from the owner, one item. Whether the class is a **report and gate granularity**
only, which is what the evidence supports, or whether it is eventually meant to reduce capture.
This scout recommends the former and shows in answer 6 why dropping alias captures blinds the
system to the most likely real event. Everything below assumes the former.

Slice 1, the fold. Pure, additive, no storage change.

1. Add to `baseline_comparison` one frozen dataclass naming a class by its members and its
   representative, and one function folding `tuple[ModelPairComparison, ...]` into
   `tuple[<class>, ...]` by union find on `outcome is DriftOutcome.EXACT`. It asserts that every
   intra class pair is EXACT and every inter class pair is not, and raises `ValueError` naming the
   offending triple otherwise. Reuses `compare_model_cohort` output, `DriftOutcome` and
   `report_outcome`. No new module.
2. Extend `baseline_compare:_print_report` with a class section: one line per class carrying the
   representative, the member aliases, the distinct wire models in the class, and the count. Keep
   the existing per cell and per pair lines unchanged; the alias to wire view is the existing
   `cell` line, not a new reader.
3. Tests in `test_baseline_comparison.py` (219 lines, room): a two class cohort folds to two
   classes; a cohort whose pairs are all EXACT folds to one; a synthetic non transitive relation
   raises and names the triple; a single cell cohort is refused by the existing cohort validator
   before the fold is reached. Test in `test_baseline_compare.py` for the rendered class lines.
4. Gates: `just check` then `just test`, with `just test-affected` as the local loop. Focused
   command while iterating:
   `cd api && .venv/bin/python -m pytest -n0 src/transport_matters/test_baseline_comparison.py src/transport_matters/test_baseline_compare.py`.
   Behavioural proof beyond unit tests: run
   `cd api && .venv/bin/python -m transport_matters.baseline_compare --harness claude` against the
   live store and confirm it reports two classes with `haiku` alone, `--harness codex` two, and
   `--harness grok` one.

Slice 2, unmask the 1M signal. Independent of slice 1 and separately reviewable.

5. In `baseline_evidence:classify_aba`, classify pointer evidence from the masked probe bodies
   that `static_nodes` already uses, so a pointer whose only per launch variation is masked prose
   stops being marked runtime generated. Land the shared masked body helper from the Quality Map
   in the same change, since both call sites are already touched. Regression: two bundles differing
   only in the `(1M context)` prose produce a `system` group content finding, and the pair outcome
   stays EXACT because content does not gate.

Slice 3, pin effort. Needs the owner's call on capture cost before it is planned in detail, since
pinning effort or adding it as a cell coordinate invalidates the current cohort and forces a re
capture. Recorded here as the standing hole in the meaning of a class, not proposed as work.

Explicitly not proposed: re keying the store by class, a class digest, a new alias resolution
symbol, and any change to `baseline_capture:_require_comparable_capture_plan`. Answers 2, 5 and 6
give the evidence for each refusal.
