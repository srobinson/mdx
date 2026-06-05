# SCOUT-DOMAIN: baseline comparator (`verdict-inconsistency`, `dual-canonical-json`)

Repo `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` at `main` `5591db86`, tree clean before
and after (read-only pass; the only write is this file). Interpreter `cd api && uv run python`
(3.14). Triage findings 4 and 5 from `tm-390-triage.md` taken as given; every claim below was
re-observed first-hand through two throwaway probes so the lattice is built from the code, not
from the doc.

**Revision 2.** D3 is decided: report INSUFFICIENT and re-probe. D3 now carries the decided answer
and its cost, D2 carries a one-line reconciliation, D5 carries each reader's obligation under the
decision and names two blockers. D1 and D4 are unchanged.

---

## Reuse Map

**Reuse.**

- `canonicalization::canonical_json` / `canonical_digest` / `json_string`: layer 1, stdlib only,
  already the discipline `baseline_evidence::classify_aba` uses for `static_fingerprint`. It is the
  right home for the second (byte-faithful) discipline too; see D4.
- `json_tags::json_kind`: the total JSON-kind mapping. Kept, not merged; see D4 for why the
  contracts are opposite.
- `request_inventory::Sha256Hex` / `JsonPointer` / `NonEmptyText`: public annotated types.
  `baseline_evidence` already imports from this module yet re-declares
  `Field(pattern=r"^[0-9a-f]{64}$")` four times (`TranscriptEvidence.sha256`,
  `ProbeEvidence.prompt_sha256`, `ProbeEvidence.raw_request_sha256`,
  `BaselineBundle.static_fingerprint`). Fold into `Sha256Hex` in the same slice.
- `provider_conditions::classify_provider_response_status`: the repo's own idiom for this exact
  problem shape: a small Literal vocabulary, one pure classifier, and a docstring that states which
  way the classifier is deliberately biased and why. The comparator fix should follow this shape.
- `StrEnum` + frozen pydantic models: the vocabulary idiom already used throughout
  `baseline_evidence`.

**Existing infra.**

- `baseline_store::write_baseline_bundle` / `read_baseline_bundle` / `read_current_baseline`: whole-model round trip, so any field change to `PointerEvidence` / `AbaAnalysis` /
  `BaselineBundle` is an artifact-schema change carried by `artifact_schema_version`.
- `ProbeEvidence.validate_raw_evidence`: recomputes `observe_request_json(raw)` and compares to the
  stored `raw_nodes` on every construction. This is the mechanism that turns a canonicalization
  change into a store-invalidation event (D4).
- `baseline_harvest::main`: the only CLI entry; `--output` defaults to
  `storage_roots::default_storage_root() / "baselines"`.
- `session/wire_normalization::_CROSS_LAUNCH_MASKS`: owned by triage finding 2, not this scope, but
  it is the seam any future "mask before fingerprinting" work reuses. Named here so the other scout
  and I do not both invent one.

**Similar, checked and rejected.**

- `request_diff::request_unchanged` / `outbound_request_if_changed`: IR-level equality for the
  overlay path. No pointer identity, no evidence axes, no outcome vocabulary. Not a comparator seam.
- `harnesses/compatibility::match_release`, `harnesses/certification*`: a verdict discipline over
  release records, digest-based and already on `canonical_digest`. Different aggregate (harness
  release compatibility, not per-request drift); no shared vocabulary to reuse beyond
  `canonical_digest`, which is already imported.
- `json_tags::record_type_token` / `literal_type_tokens`: collision-proof tag tokens. Solves a
  different problem (unhashable tag values at a parse boundary); the comparator's kinds already come
  from a closed Literal.

**None found (searches run).**

- No existing two-axis "value stability x presence" model anywhere in the repo:
  `rg "structurally.optional|presence_by_probe|STRUCTURALLY"`, `rg "class .*\(StrEnum\)"` across
  `src/transport_matters` (24 enums, none of this shape).
- No decision-table or state-machine helper to reuse: `rg "decision.table|transition|Machine"` in
  `api/src` returns only `flow_state.py` (run lifecycle, unrelated aggregate).
- No second consumer of the comparator anywhere: `rg "static_fingerprint|observed_schema|
  DriftOutcome|RequestJsonNode|observe_request_json|raw_nodes"` across the repo returns only
  `baseline_evidence.py`, `baseline_capture.py`, `request_inventory.py` and the two colocated test
  modules. No FastAPI route, no CLI print, no `www/` or `packages/` TypeScript consumer, no entry in
  `test_type_mirrors.py`, no migration.

---

## Quality Map

**Duplication.**

- The load-bearing one is not a helper, it is a *representation*: `request_inventory::_JsonObject`
  is a private parallel JSON tree that the layer-1 canonicalizers cannot see, so
  `request_inventory::_canonical_json_bytes` hand-rolls a second serializer and
  `request_inventory::_json_kind` hand-rolls a second kind mapping to walk it. Fix the
  representation and one of the two copies collapses on its own.
- `_canonical_json_bytes` calls a nested `plain()` that deep-copies the whole subtree, and
  `_observe_native` calls it at every node. The duplicate serializer is also the O(bytes x depth)
  cost measured in triage finding 10.
- `baseline_evidence::_require_probe_order` and `BaselineBundle.validate_probe_contract` run the
  identical `labels != (A1, B, A2)` check in one module.
- Three consumers each re-derive the two evidence axes from one flat tuple with different ad-hoc
  algebra: `classify_aba` (`== (EvidenceKind.STABLE,)`), `compare_baseline_bundles`
  (`set(...) <= allowed`), `_repeat_a_outcome` (`set(...) <= allowed`). This is the duplication that
  causes the defect, not merely accompanies it.
- `Sha256Hex` re-declared four times in `baseline_evidence` (see Reuse Map).

**Boundary.**

- `canonicalization` is correctly layer 1. `request_inventory` importing it would not create a cycle
  (`canonicalization` imports nothing from `transport_matters`); today `request_inventory` imports
  neither `canonicalization` nor `json_tags`, which is why both duplicates exist.
- Module privacy holds: `_JsonObject`, `_canonical_json_bytes`, `_json_kind` are private and only
  used inside `request_inventory`. Promoting the serializer means moving it to `canonicalization`
  under a public name, not exporting a private one.
- `compare_baseline_bundles` reaches into `candidate.pointer_evidence` and `observed_schema` and
  reassembles dicts at the call site. The evidence record should answer its own questions
  (`is_static`, `value_evidence`), rather than the comparator re-deriving them.

**Dead code.**

- `EvidenceKind.MODEL_DEPENDENT` is declared and never emitted or read anywhere
  (`rg MODEL_DEPENDENT` = one hit, the declaration). `AbaAnalysis.model_dependence_assessed:
  Literal[False]` already records that the axis is unassessed, so the enum member is a trap: it sits
  inside a type whose consumers do set-algebra over the whole member set.
- `(PROMPT_DERIVED, STRUCTURALLY_OPTIONAL)` is unreachable by construction:
  `_direct_prompt_pattern` returns False unless all three labels are present, which is exactly the
  condition that suppresses the `STRUCTURALLY_OPTIONAL` append. Probe-confirmed: a prompt-shaped
  value present in two of three probes classifies `(UNKNOWN, STRUCTURALLY_OPTIONAL)`.
- Both `SESSION_GENERATED` tuples are unreachable on the live path (triage finding 7: no caller
  passes `annotations`), so live classification is five tuples wide, not seven.

**Grooming recommendation.**

`baseline_evidence.py` is 435 lines and `request_inventory.py` 547, both under the 700 guardrail;
`classify_aba` and `compare_baseline_bundles` are each well under 150 lines. No decomposition is
warranted and none is proposed. This file's problem is modelling, not size, and splitting it would
scatter the invariant across more files. The one structural move worth making is downward, not
sideways: the byte-faithful serializer belongs in layer 1 beside its sibling discipline.

---

## Plan

**Decision taken (rev 2).** A presence change on a pointer whose value is constant whenever it
appears reports INSUFFICIENT and prompts a re-probe. The rest of this plan is mechanical.

**Decisions still open, both small and both named in place.** (a) D4: whether request node digests
keep byte-faithful number rendering (`1` and `1.0` distinct) or adopt the shared collapsing
discipline. Recommendation: keep byte-faithful, because `RequestJsonNode` exists to record what was
on the wire. (b) D3: the promotion policy for the `current` pointer, and the threshold at which
repeated probes promote a presence claim from SOMETIMES to ALWAYS.

**Proposed steps, bound to the reuse map.**

1. Replace `PointerEvidence.classifications: tuple[EvidenceKind, ...]` with two single-valued
   fields: `value_evidence` (STABLE | PROMPT_DERIVED | SESSION_GENERATED | UNKNOWN) and `presence`
   (ALWAYS | SOMETIMES). Two `StrEnum`s in `baseline_evidence`, following the
   `provider_conditions` idiom already in the Reuse Map. `EvidenceKind` and its dead
   `MODEL_DEPENDENT` member are deleted, not kept alongside. This shrinks the representable state
   space from 64 tuples to 8, of which 7 are emitted, and makes "exactly one value claim" a type
   guarantee rather than an accident of the if/elif chain.
2. Make `static_records` membership presence-independent (D3 shows only this removes the
   contradiction) and express it as one predicate owned by `PointerEvidence`, so the three consumers
   stop re-deriving it. `_repeat_a_outcome` and `compare_baseline_bundles` read that predicate.
3. Fix the three comparator predicates that no type change fixes: the EXACT branch must read the
   evidence axes (today a PROMPT_DERIVED leaf degrading to UNKNOWN returns EXACT); a pointer removed
   in the candidate must be judged against the *reference's* evidence, since the candidate by
   definition has none (today `pointer in candidate_evidence` fails and the answer is INSUFFICIENT);
   and `changed_pointers` builds the candidate schema dict once instead of `next(...)` per pointer.
   Additions are judged by candidate evidence, removals by reference evidence: the asymmetry is the
   domain fact the current conjunct misses.
4. Delete `request_inventory::_canonical_json_bytes` by moving the byte-faithful discipline into
   `canonicalization` beside `canonical_json`, and give `_JsonObject` a `Mapping` interface so the
   shared serializer walks it directly and the per-node `plain()` deep copy disappears. This adds no
   capability: it relocates one that exists today, which is why it does not violate the
   no-new-helper rule. `_json_kind` stays (D4 justifies it).
5. Bump `artifact_schema_version` to 2 in `BaselineBundle` and `baseline_store`. No migration:
   `/Users/alphab/.transport-matters/baselines` does not exist on this machine, so zero bundles are
   at risk, and steps 1 and 4 both change the artifact.
6. **Close the two blockers named in D5, which the decided disposition makes load-bearing.** Give
   `BaselineComparison` a field naming the unresolved pointers (typed with `JsonPointer` from the
   Reuse Map); make the `current` promotion in `baseline_store::write_baseline_bundle` conditional
   on the outcome; and make `baseline_harvest::main` read the verdict and exit non-zero on anything
   that is not EXACT or COMPATIBLE. The CLI change needs the comparison to reach it, so
   `harvest_controlled_baseline` returns the outcome alongside the `BundleRef` rather than the CLI
   re-reading the bundle it just wrote.

Sequence: 4 first (pure, no verdict semantics), then 1, then 2 and 3 together with the tests below,
then 6. Step 4 alone changes every stored node digest, so it must land while the store is empty.
Step 6 is not optional polish under the decided disposition: INSUFFICIENT becomes the routine
outcome on a healthy cell, and an outcome that nothing reads is indistinguishable from success.

**Tests and gates.**

- The property test that proves the fix and must fail before it: the same harness change classifies
  to the same verdict whether the added field appears in two or three probes. Today it returns
  BREAKING and COMPATIBLE respectively.
- The mirror case, currently unreported anywhere: a field the harness did not change at all, which
  merely flickers out of probe B, returns BREAKING. Assert it does not.
- COMPATIBLE and INSUFFICIENT have no assertions in the repo today
  (`test_baseline_evidence::test_bundle_comparison_reports_exact_and_breaking_drift` is the only
  comparison test and covers only EXACT and BREAKING). Add one case per outcome.
- A removed pointer that the reference observed absent at least once asserts INSUFFICIENT **and**
  that the comparison names that pointer as unresolved. Today the same outcome arrives for the wrong
  reason (the `pointer in candidate_evidence` conjunct fails and the reference is never consulted),
  so asserting the outcome alone would pass against the unfixed code.
- A removed pointer the reference observed in every probe asserts BREAKING, so the two removal cases
  are pinned apart.
- A classification degradation (PROMPT_DERIVED to UNKNOWN with identical schema and fingerprint)
  asserts not-EXACT.
- `baseline_harvest::main` exits non-zero on a BREAKING bundle and on an unresolved presence delta,
  and `write_baseline_bundle` leaves `current` pointing at the prior reference in both cases. Both
  fail against current code (`main` returns 0 for every outcome).
- `test_canonicalization.py` gains the byte-faithful number cases (`1.0`, `-0.0`, `1e21`) so the two
  disciplines are pinned against each other in one place.
- Gates: `cd api && just check` and `cd api && just test`. A bare `pytest` lies in this repo. Per the
  brief I ran neither; the 26 baseline tests were reported green on this commit by the triage pass.

---

## Domain Model

### D1. The lattice

`_classify_pointer` emits exactly one value claim from an if/elif chain, then optionally appends
`STRUCTURALLY_OPTIONAL`. Seven tuples are reachable; the eighth is unreachable by construction and
`MODEL_DEPENDENT` is never emitted at all. All rows below were observed by running `classify_aba`,
not read off the source.

| Tuple | Emitted when | Domain claim | In `static_fingerprint`? | `compare_baseline_bundles` |
|---|---|---|---|---|
| `(STABLE,)` | all three probes carry it, one distinct digest | value is constant across A/B/A | **yes** | inside `allowed`; a change here is COMPATIBLE, but its presence in the fingerprint means the change usually never reaches that branch and returns BREAKING first |
| `(STABLE, STRUCTURALLY_OPTIONAL)` | two probes carry it, digests equal | constant whenever present, absent at least once | no | inside `allowed`; change returns COMPATIBLE |
| `(PROMPT_DERIVED,)` | all three carry it, A1 == A2 != B, and the string values contain prompt A, prompt B, prompt A | value is a function of the prompt | no | inside `allowed`; COMPATIBLE |
| `(SESSION_GENERATED,)` | all three carry it, digests differ, every present leaf is annotated `session-derived` | value is minted per session | no | inside `allowed`; COMPATIBLE. Live-unreachable (finding 7) |
| `(SESSION_GENERATED, STRUCTURALLY_OPTIONAL)` | one or two probes carry it, annotated | per-session and sometimes absent | no | inside `allowed`; COMPATIBLE. Live-unreachable |
| `(UNKNOWN,)` | all three carry it, digests differ, no prompt or session proof | probes do not prove the value source | no | **outside** `allowed`; forces INSUFFICIENT if this pointer is among the changed |
| `(UNKNOWN, STRUCTURALLY_OPTIONAL)` | fewer than three carry it and the carried digests are not all equal | unproven source and sometimes absent | no | outside `allowed`; forces INSUFFICIENT |
| `(PROMPT_DERIVED, STRUCTURALLY_OPTIONAL)` | never |, |, | unreachable: the prompt pattern requires all three labels, which is exactly what suppresses the optional append |
| `MODEL_DEPENDENT` (any) | never |, |, | declared, never emitted, never read |

Three facts the table does not show, all probe-confirmed:

- **Containers inherit variability.** A node's digest covers its whole subtree, so every ancestor of
  a varying leaf is `(UNKNOWN,)`, and the document root is `(UNKNOWN,)` in every real A/B/A run
  because the prompt differs by design. Conversely a fully constant object is `(STABLE,)` *and* so
  is each of its descendants, so the fingerprint hashes the same bytes once per level of depth.
- **`allowed` is the complement of one member.** The four-element allowlist in
  `compare_baseline_bundles` is `{PROMPT_DERIVED, SESSION_GENERATED, STRUCTURALLY_OPTIONAL, STABLE}`,
  which given that `MODEL_DEPENDENT` is never emitted means exactly "does not contain UNKNOWN". The
  set is written as an enumeration of everything except one member, which hides what it tests.
- **The live lattice is five tuples wide**, not seven, because no live caller passes annotations.

### D2. The structure

The contradiction is not a wrong constant. It is that `classifications: tuple[EvidenceKind, ...]`
unions two independent claims into one flat set:

- *why the value varies* (STABLE / PROMPT_DERIVED / SESSION_GENERATED / UNKNOWN), exactly one of
  which is always emitted, and
- *whether the node is always there* (`STRUCTURALLY_OPTIONAL` or nothing).

Because they share one container, every consumer has to reconstruct the axes, and each does it
differently. `classify_aba` writes `item.classifications == (EvidenceKind.STABLE,)`, which reads
like a test on the value axis and is in fact a test on both: it silently means "stable AND present
in all three probes". That hidden conjunct is the whole defect. `compare_baseline_bundles` and
`_repeat_a_outcome` then flatten in the other direction, with `set(...) <= allowed` over a set that
mixes members from both axes, so "stable" and "sometimes missing" are interchangeable evidence for
the same conclusion.

**Choice: split the axes into two single-valued fields on `PointerEvidence`.** `value_evidence:
ValueEvidence` and `presence: PresenceEvidence`. Reasons, in order of weight:

1. It deletes branches rather than adding indirection: three tuple/set-algebra expressions become
   three field reads, and the hidden conjunct in `classify_aba` becomes a written predicate a
   reviewer can disagree with.
2. It makes the "exactly one value claim" invariant a type guarantee. Today that invariant is
   maintained only by the shape of an if/elif chain, and nothing stops a future edit appending a
   second value claim; the state space is 64 tuples for 7 emitted states.
3. The repo already believes in this model. The existing test is named
   `test_aba_classification_requires_direct_prompt_and_keeps_optionality_orthogonal`. The domain
   language says orthogonal; the type says union.
4. It costs one artifact-schema field rename, which the store is already empty for.

**Rejected: a discriminated union / state machine over pointer disposition** (seven members). It
would make the unreachable combination unrepresentable, which the two-axis split does not, but it
buys that by naming seven states where the domain has two questions, and it deletes no branch. Not
worth the indirection.

**Rejected: a decision table keyed by (reference class, candidate class, presence delta).** The
comparator has four outcomes and roughly a dozen live input combinations; a table would move the
logic into data without removing a single conditional, and the repo's own idiom for this shape
(`provider_conditions::classify_provider_response_status`) is a documented pure function, not a
table.

**Reconciliation with the decided D3 (rev 2).** The split holds unchanged and the presence axis
stays two-valued: undersampling is a property of the probe set size, not of the pointer, so at
n = 3 every SOMETIMES pointer is undersampled and a third state would be constant-valued and carry
no information. The decision changes what the comparator *does* with SOMETIMES, not what
classification *records*; the per-probe detail an operator needs is already in
`PointerEvidence.presence_by_probe`.

**Said plainly, as asked:** the two-axis split does not on its own fix the verdict. A corrected
predicate is still required, and a determined caller can still write the wrong predicate over two
fields. What the split buys is that the wrong predicate becomes *visible* instead of arriving as a
side effect of tuple equality, and that the three consumers stop each inventing their own. If the
answer to D3 is "presence never affects fingerprint membership", the minimal fix is genuinely a
one-line predicate change; I would still take the split, because that one line is currently correct
by coincidence in three places and the fourth consumer has not been written yet.

### D3. The semantics decision, decided: report INSUFFICIENT and re-probe

**The decision.** When a pointer's value is identical in every probe that carried it but at least
one probe did not carry it, a later presence change is neither COMPATIBLE nor BREAKING. The
comparator refuses to rule and reports INSUFFICIENT, because three probes cannot distinguish
demonstrated optionality from undersampling and the comparator must not assert a fact it does not
have. The repo precedent is real and verified, not just cited: migration
`0034_wire_request_divergence` adds `request_wire_bytes` as a *nullable* integer with no default,
and `session/wire_store::WireExchangeWrite.request_wire_bytes` defaults to `None`, so an unmeasured
body reads as unknown rather than as zero bytes. Presence-delta-with-constant-value is the same
shape: absent evidence must not render as a verdict.

**The finding this rests on, accepted as filed.** `static_records` membership becomes
presence-independent, the fingerprint covers value stability only, and presence deltas are judged on
the schema axis. Both failure directions were reproduced: one added constant field present in 3/3
probes returns `breaking-drift` while the same field present in 2/3 returns `compatible-drift`; and
a field the harness did not change at all, which merely flickers out of probe B, returns
`breaking-drift` from nothing.

#### What the outcome member costs

**Reuse, no new member.** `DriftOutcome.INSUFFICIENT` already exists and already means exactly this:
`compare_baseline_bundles` returns it on the fall-through and on a cell-coordinate mismatch, and
`_repeat_a_outcome` returns it when the A/A leg cannot be explained. Reuse it. No new enum, no new
module, no new type is warranted, consistent with the Reuse Map.

**The one place it would be overloaded, and the discriminator that already exists.**
`BaselineBundle.reference_outcome` uses INSUFFICIENT for a second, narrower meaning: *there was no
reference bundle at all*. `baseline_capture::harvest_controlled_baseline` sets
`reference_outcome=DriftOutcome.INSUFFICIENT` with reason `"no reference bundle exists"` on the
bootstrap path, and `BaselineBundle.validate_probe_contract` enforces that bootstrap bundles carry
it. Those are different claims: "nothing to compare against" versus "compared, and refused to rule".
They are already distinguishable without adding anything, because the validator constrains only one
direction: `reference_bundle_id is None` implies INSUFFICIENT, never the converse. So
`reference_bundle_id is not None and reference_outcome is INSUFFICIENT` unambiguously means
*compared and undecided*. Every reader must test both fields, and that requirement should be stated
on the model rather than rediscovered per reader. `AbaAnalysis.repeat_a_outcome` is a third use of
the member but on a different field, so it cannot be confused with either.

**What INSUFFICIENT must carry to be actionable rather than merely honest.** `BaselineComparison`
carries `outcome` and `reasons: tuple[str, ...]`, and every reason emitted today is a fixed prose
constant (`"changed request evidence is not classified strongly enough"`). The operator therefore
receives a refusal with no subject: nothing names which pointer caused it, and nothing says what
would settle it. Three things are needed, two of which already exist and merely need surfacing:

1. **Which pointers forced the refusal.** Add one field to `BaselineComparison` naming them, typed
   with `request_inventory::JsonPointer`, which the Reuse Map already lists. This adds a field to an
   existing model, not a new type or module, which is why it does not deviate from reuse-first.
2. **The presence evidence for each, from both bundles.** Already recorded: each side's
   `PointerEvidence.presence_by_probe` says exactly which probes carried the pointer, so "carried by
   2 of 3 reference probes, 3 of 3 candidate probes" is a formatting job, not new evidence.
3. **What would settle it.** This is where the disposition must be honest about its own limit: *no
   finite number of probes proves optionality*, because absence of a field in one probe is never
   evidence that it is genuinely conditional. What re-probing can do is promote the reference's
   presence claim from SOMETIMES to ALWAYS, which makes the delta decidable on the value axis alone.
   So the actionable number the comparator can state is the observed ratio plus the promotion rule
   it would apply, never a count that ends in certainty. The threshold for that promotion (how many
   consecutive probes carrying the pointer are enough) is a second, much smaller human decision;
   it is named here and not taken.

**The cost, stated plainly.** Today's live path already yields `repeat_a_outcome =
insufficient-evidence` for every bundle (triage finding 7, no caller passes annotations). Adding a
second routine source of INSUFFICIENT to `reference_outcome` means the common verdict on a healthy
cell becomes "undecided" until both that finding and the re-probe loop below are fixed. That is
acceptable and is the point of the decision, but it means INSUFFICIENT stops being an exception
path and becomes the default one, which is precisely why the two blockers in D5 are blockers: a
default-path outcome that no reader reads is indistinguishable from success.

#### The re-probe loop: is it expressible today?

**No. The A/B/A triple is structural, in seven places.** `ProbeLabel` is a three-member `StrEnum`;
`AbaAnalysis` and `BaselineBundle` type `probes` as `tuple[ProbeEvidence, ProbeEvidence,
ProbeEvidence]`; `harvest_controlled_baseline` builds a literal three-entry `plan`;
`_require_probe_order` and `BaselineBundle.validate_probe_contract` both assert the exact tuple
`(A1, B, A2)`; `classify_aba` iterates `for label in ProbeLabel`; `_direct_prompt_pattern` requires
all three labels present and is *defined* in terms of A1 == A2 != B; and `_repeat_a_outcome`
compares A1 against A2. The prompt-derivation proof is not merely sized to three probes, its
semantics are the A/B/A shape, so widening the probe set is not a parameter change.

**Which fix, and the smallest change.** Not a wider probe set: that touches all seven sites plus the
artifact schema plus the prompt-derivation proof, and buys nothing the operator cannot get from a
second harvest. The operator-driven second harvest is the right lever, and most of it already works:
every harvest writes a new immutable bundle into
`<output>/bundles/<harness>/<provider>/<model>/<uuid>.json`, so re-probe evidence is *already*
accumulating on disk. Two things stop it from settling anything, and only the second is a code
change:

- `baseline_store` has no enumeration. It exposes `write_baseline_bundle`, `read_baseline_bundle`
  and `read_current_baseline` only, so nothing can read the cell's history even though the history
  is right there in one directory per cell.
- **`write_baseline_bundle` repoints `current` unconditionally**, with no branch on
  `reference_outcome`. The bundle that was just declared undecided (or breaking) becomes the
  reference for the next harvest. A re-probe therefore cannot accumulate evidence against a fixed
  reference; it overwrites the thing it was supposed to be compared against.

**Smallest change: make the `current` promotion conditional on the outcome** in
`baseline_store::write_baseline_bundle`, so an INSUFFICIENT or BREAKING bundle is still written and
still immutable but does not become the new reference. That is one branch in one function, against a
redesign of `ProbeLabel` and the artifact schema. Enumeration of the cell directory can follow later
if a presence tally across harvests is wanted; it is not needed for the loop to become sound.
Whether promotion should be automatic on EXACT/COMPATIBLE only, or always operator-confirmed, is a
policy question for you, not a scout call. Not implemented, per the brief.

### D4. Canonicalization

**`_canonical_json_bytes` cannot simply be deleted in favour of `canonical_json`.** Two blockers and
one real reason to differ, all observed:

- `canonical_json(parsed_tree)` raises `TypeError: Unsupported char-accounting JSON value:
  _JsonObject`. The inventory parses into a private `_JsonObject` dataclass (to reject duplicate keys
  and hold pair order), which is not a `Mapping`, so the shared serializer cannot walk it. The
  `plain()` conversion inside `_canonical_json_bytes` exists only to bridge that gap; deleting the
  function relocates the deep copy rather than removing it. Giving `_JsonObject` a `Mapping`
  interface removes it for real, and removes the per-node subtree copy that triage finding 10
  measured.
- Number rendering genuinely differs, and not only for `1.0`: `1.0` renders `1.0` vs `1`, `-0.0`
  renders `-0.0` vs `0`, `1e+21` renders `1e+21` vs `1e21`, `1e-07` renders `1e-07` vs `1e-7`.
  Strings, escaping, non-ASCII, U+2028, surrogate-pair emoji, object key ordering and nested arrays
  are byte-identical between the two, so number rendering is the entire delta.
- The consequence is a collision, not a reformat: `canonical_json(1) == canonical_json(1.0)`, so
  under the shared discipline `{"temperature": 1}` and `{"temperature": 1.0}` produce one digest.
  `RequestJsonNode` documents itself as "one native JSON node with its RFC 6901 identity and exact
  value digest", and a harness switching an integral float to an int is a real wire change. That is
  a semantics decision, not a cleanup, which is why it is raised in the Plan and not decided here.
  Recommendation: keep byte-faithful rendering and move it into `canonicalization` under a name that
  says which discipline it is, so one layer-1 module owns both and a future canonicalization fix has
  one home.

**`_json_kind` should not be deleted in favour of `json_tags::json_kind`.** `json_kind(parsed_tree)`
returns `"_JsonObject"`, not `"object"`, and its return type is `str` while `RequestJsonNode.kind`
is the closed `JsonKind` Literal, so the substitution turns a load-bearing `TypeError` into either a
wrong tag or a pydantic validation error at construction. The deeper reason is that the two have
opposite contracts by design: `json_tags::json_kind` is deliberately *total* because it is a
deserialization-boundary sanitizer that must never raise, and `_json_kind` is deliberately *partial*
because it is a strict-parser assertion that an unexpected node type must abort. Six lines of
identical mapping with opposite totality guarantees is not a copy to consolidate. It stays.

**Digests that would change value if we consolidate the serializer.**

Changed: `RequestJsonNode.sha256` for every number node whose Python value is an integral float, a
negative zero, or exponent-form, *and* for every ancestor container of such a node, up to and
including the document root. Confirmed on a realistic body: with `"temperature": 1.0` present, both
`/temperature` and the root node move; `/max_tokens`, `/model` and `/stream` do not. Those digests
are persisted in `ProbeEvidence.raw_nodes`, three probes per bundle. `AbaAnalysis.static_fingerprint`
and `BaselineBundle.static_fingerprint` are `canonical_digest` over records containing those digests,
so they move with them. Real Anthropic bodies carry `"temperature": 1.0`, so this is not hypothetical.

Unchanged: `RequestInventory.raw_sha256`, `ProbeEvidence.raw_request_sha256`,
`TranscriptEvidence.sha256`, `ProbeEvidence.prompt_sha256`, `RequestStringLeaf.sha256` and
`AuthoritativeTokenCount.sha256`. All six are sha256 over raw bytes or over the raw string value,
never over canonical JSON.

**What on disk or in Postgres depends on them.** Postgres: nothing. No baseline module imports
`session`, storage, or any Postgres path, and no migration references baselines. On disk: bundles
under `<output>/bundles/<harness>/<provider>/<model>/<uuid>.json` plus the
`<output>/current/...json` pointer, where `<output>` defaults to
`default_storage_root() / "baselines"`. That directory (`/Users/alphab/.transport-matters/baselines`)
does not exist on this machine, so **zero bundles are at risk today**.

That matters more than the value change itself. Because `ProbeEvidence.validate_raw_evidence`
re-derives `observe_request_json(raw)` and compares it to the stored `raw_nodes` on every model
construction, a bundle written under the old discipline does not merely disagree with a new one, it
fails to load at all with "raw request nodes do not match embedded bytes". And
`baseline_capture::harvest_controlled_baseline` reads the current pointer *before* launching
anything, so one stale bundle bricks that cell exactly the way triage finding 8 describes. Consolidate
now, while the store is empty, and bump `artifact_schema_version`.

### D5. Blast radius

Every reader, by symbol. The surface is entirely contained in four modules and two colocated test
modules; there is no route, no CLI output, no TypeScript mirror, no database.

**`static_fingerprint`**: written by `baseline_evidence::classify_aba` (into `AbaAnalysis`); carried
by `baseline_evidence::BaselineBundle`; populated by `baseline_capture::harvest_controlled_baseline`;
read only by `baseline_evidence::compare_baseline_bundles`, twice (the EXACT conjunct and the
BREAKING short circuit); asserted in
`test_baseline_evidence::test_bundle_comparison_reports_exact_and_breaking_drift`.

**`observed_schema`**: the same shape. Written by `classify_aba`, carried by `AbaAnalysis` and
`BaselineBundle`, populated by `harvest_controlled_baseline`, read by `compare_baseline_bundles` in
the EXACT conjunct and in the `changed_pointers` comprehension, asserted in the same single test.
Note it deliberately carries only `(pointer, kinds, present_in)`, which is why classification
degradation is invisible to the EXACT branch.

**`DriftOutcome`**: declared in `baseline_evidence`; carried by `AbaAnalysis.repeat_a_outcome`,
`BaselineBundle.repeat_a_outcome`, `BaselineBundle.reference_outcome`, `BaselineComparison.outcome`;
produced by `compare_baseline_bundles` and `_repeat_a_outcome`; enforced by
`BaselineBundle.validate_probe_contract` (bootstrap bundles must be INSUFFICIENT); imported and set
by `baseline_capture::harvest_controlled_baseline`; asserted in `test_baseline_evidence`. Members are
persisted as strings inside the bundle JSON, so renaming one invalidates stored bundles.

**Per-reader obligation under the decided D3 (rev 2).** Every reader, and what each must do when it
receives INSUFFICIENT for a presence delta:

| Reader | Obligation | Status |
|---|---|---|
| `compare_baseline_bundles` | Producer. Must name the unresolved pointers in the comparison rather than emitting prose only (D3). | change required |
| `_repeat_a_outcome` | Nothing. It writes a different field (`repeat_a_outcome`); the member cannot be confused with `reference_outcome`. | unchanged |
| `BaselineBundle.validate_probe_contract` | Nothing, and it must keep enforcing bootstrap ⟹ INSUFFICIENT, because that one-directional rule is what makes `reference_bundle_id is not None` the discriminator for "compared and undecided". | unchanged, load-bearing |
| `baseline_capture::harvest_controlled_baseline` | Must stop promoting an undecided bundle to reference. It writes the comparison into the bundle and then calls `write_baseline_bundle` with no branch on the outcome. | **BLOCKER** |
| `baseline_store::write_baseline_bundle` | The mechanism of the above: repoints `current` unconditionally. Promotion must become conditional (D3, smallest change). | **BLOCKER** |
| `baseline_harvest::main` | Must surface the outcome and exit non-zero on anything that is not EXACT or COMPATIBLE. It never reads `reference_outcome` at all: it prints `written: <harness>/<model> <path>` and returns 0 on every outcome. | **BLOCKER** |
| `test_baseline_evidence` | Only EXACT and BREAKING are asserted anywhere in the repo; INSUFFICIENT for a presence delta has no test. | change required |

**Readers that silently pass on INSUFFICIENT, named as blockers.** Two, and they compound:

1. `baseline_harvest::main` is the entire operator-facing surface, and it does not read the verdict.
   Its `try` block catches exceptions from `harvest_controlled_baseline`; a bundle that compared
   BREAKING against its reference is not an exception, so the CLI prints `written:` and returns 0.
   This is not specific to the new disposition: **BREAKING already exits 0 today**. The drift signal
   is computed, persisted, and then discarded before it reaches a human. Note that
   `harvest_controlled_baseline` returns a `BundleRef` (`bundle_id`, `path`) and not the comparison,
   so the CLI cannot read the outcome without either re-reading the written bundle or widening that
   return value.
2. `baseline_store::write_baseline_bundle` promotes every bundle to `current` regardless of outcome,
   so the undecided or breaking observation silently becomes next harvest's baseline. Combined with
   (1), a real breaking change is reported nowhere and has erased its own reference by the next run.

There is no reader that *misinterprets* INSUFFICIENT, because there is no other reader at all: no
FastAPI route, no CLI branch, no `www/` or `packages/` consumer, no `test_type_mirrors.py` entry, no
Postgres column. The failure mode is not misreading the outcome, it is that nothing reads it.

**Transitively, because bundles round-trip whole models**: `baseline_store::write_baseline_bundle`
(which re-reads and re-validates what it just wrote), `read_baseline_bundle`, `read_current_baseline`,
and `baseline_harvest::main`. Any field added to or removed from `PointerEvidence`, `AbaAnalysis` or
`BaselineBundle` is an artifact-schema change even when no verdict logic moves.

**`RequestJsonNode` / `observe_request_json` / `raw_nodes`**: defined in `request_inventory`,
produced at `baseline_capture::_build_probe_evidence`, validated at
`ProbeEvidence.validate_raw_evidence`, consumed at `classify_aba`. `request_inventory` itself is
imported by nothing outside `baseline_capture`, `baseline_evidence` and their tests.
