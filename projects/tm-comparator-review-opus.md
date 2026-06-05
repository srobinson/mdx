---
title: fix/comparator-truth adversarial review (Opus)
type: projects
tags: [transport-matters, baseline-capture, comparator, review]
summary: Peer-consensus review of fix/comparator-truth at 0192c746 against main 5591db86
status: active
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

# Review: `fix/comparator-truth` @ `0192c746`

Reviewer: Opus, independent leg of a two-reviewer peer consensus. Baseline `main` `5591db86`.
Tree verified pristine at `0192c746ed82` before and after (`git status --short` empty both times).
No repo writes; the only writes are this file and two scratchpad probes. Interpreter
`cd api && uv run python` (3.14). I did not re-run `just check` / `just test`; the orchestrator
reported them green at head.

**Verdict: 1 Blocker, 3 Major, 2 Minor.** The five defects and the preflight gap are genuinely
fixed and the correlation, transcript, preflight and version work is sound. The comparator itself
is not yet truthful: the fingerprint fix (U3) narrowed the compared surface far past date/cwd
masking, and the outcome wiring (U0) disagrees with itself in two places.

---

## B1. Blocker — the stable fingerprint no longer covers sampling, streaming, or model; a real wire change reports EXACT and auto-promotes

`api/src/transport_matters/baseline_evidence.py::classify_aba` (lines 222-227, 250-269)

U3 moved `static_records` from `probe.raw_nodes` onto
`observe_request_json(canonical_json(probe.normalized_request))`. `normalized_request` is
`normalize_request(..., cross_launch=True).model_dump(mode="json")`
(`baseline_capture.py::_build_probe_evidence`, line 439), and
`session/wire_normalization.py::NormalizedWireRequest` carries exactly four fields:
`system_set`, `tools_set`, `messages`, `request_extras`. `InternalRequest.sampling`,
`.stream`, `.metadata` and `.model` are not in that projection and are not in
`provider_extras` either.

The consequence is larger than the intended date/cwd masking: **after U3 no cross-bundle
comparison reads any raw request digest at all.** `raw_nodes` and `raw_request_sha256` are still
captured and persisted, but `compare_baseline_bundles` reads only `static_fingerprint`
(normalized), `observed_schema` (pointer / kinds / present_in) and `pointer_evidence`
(value_evidence / presence). A top-level scalar that changes value between harvests keeps the same
pointer, the same kind, the same presence, and is constant within each A/B/A run, so it is
identical on every axis the comparator inspects.

Observed, through the repo interpreter, with three probes per bundle and a realistic
`normalize_request(..., cross_launch=True)` projection:

```
max_tokens 8192 -> 16384     -> exact   fingerprint_equal=True
stream true -> false         -> exact   fingerprint_equal=True
temperature 1.0 -> 0.7       -> exact   fingerprint_equal=True
```

and the raw evidence that is captured but never compared:

```
raw pointers:            ['', '/max_tokens', '/messages', '/messages/0', '/messages/0/content',
                          '/messages/0/role', '/model', '/stream', '/temperature']
normalized top-level:    ['messages', 'request_extras', 'system_set', 'tools_set']
request_extras:          {}
```

This is a regression against `main`. On `5591db86` the same pointer classified `(STABLE,)`
(present in 3/3, one digest), entered `static_records` from `raw_nodes`, and moved the
fingerprint, so the change returned `breaking-drift`.

**Failure scenario.** Claude Code ships a release that raises `max_tokens` from 8192 to 16384.
The operator runs `uv run python -m transport_matters.baseline_harvest --harness claude`. The
comparator reports `outcome=exact`, `main` exits 0, and because EXACT promotes
(`baseline_store.py::write_baseline_bundle`, line 39) the drifted bundle becomes the new
reference. The change is now baked into `current` and no later harvest can ever surface it. The
artifact's headline claim — "this request is unchanged" — is false for every field the IR models
as structure rather than content.

**Direction.** The masking requirement was "date and cwd must not read as drift", not "compare
only system, tools and messages". Fingerprinting the raw nodes with the cross-launch masks applied
to the raw prose, or fingerprinting the union of the normalized projection and the raw scalar
leaves outside it, both preserve U3's test while restoring coverage. Whichever is chosen, the
`raw_nodes` that are persisted per probe should either be compared or stop being persisted.

---

## M2. Major — one unresolved presence delta suppresses a decided BREAKING verdict, and names the wrong pointer

`api/src/transport_matters/baseline_evidence.py::compare_baseline_bundles` (lines 328-355)

The INSUFFICIENT-on-presence branch is evaluated **before** the fingerprint check. Any single
pointer that is `(STABLE, sometimes)` on either side short-circuits the whole comparison, even
when the value axis has already produced a decided answer. The two axes were split precisely so
that presence uncertainty and value stability are judged independently; this ordering lets the
presence axis veto the value axis.

Observed:

```
core v1->v2 AND one unrelated field flickers:
  outcome              = insufficient-evidence
  reasons              = ('presence changes require another controlled probe',)
  unresolved_pointers  = ('/feature',)
  fingerprint_changed  = True          <-- decided, and never reported

control, same change alone:
  outcome  = breaking-drift  reasons = ('stable baseline fingerprint changed',)
```

**Failure scenario.** A harness update changes a stable system-prompt value (breaking) in the same
release that makes one optional field intermittent. The operator is told "presence changes require
another controlled probe" and is pointed at `/feature`, the one pointer that is *not* the problem.
They re-probe; the breaking change reproduces every time and is reported nowhere, because the
flicker reproduces too. Exit code 1 and non-promotion are correct, so nothing is silently lost,
but the diagnostic actively misdirects and BREAKING becomes unreachable on any cell that has one
intermittent field. Per D3 that is the routine state of a healthy cell.

Test the fingerprint first and return BREAKING, or return BREAKING with the unresolved pointers
attached, so the strongest decided verdict wins.

---

## M3. Major — the first harvest of any cell exits 1; the store and the CLI read `reference_outcome` under different rules

`api/src/transport_matters/baseline_harvest.py::main` line 93, against
`api/src/transport_matters/baseline_store.py::write_baseline_bundle` line 39

`write_baseline_bundle` uses the discriminator the domain analysis established:
`reference_bundle_id is None` means bootstrap and promotes; `INSUFFICIENT` with a reference means
"compared and undecided" and does not. `main` reads `reference_outcome` alone:

```python
return 0 if outcome in {DriftOutcome.EXACT, DriftOutcome.COMPATIBLE} else 1
```

`harvest_controlled_baseline` sets `reference_outcome=DriftOutcome.INSUFFICIENT` with
`("no reference bundle exists",)` on the bootstrap path (`baseline_capture.py` lines 143-144), and
`BaselineBundle.validate_probe_contract` (line 201) makes that mandatory. So the bootstrap harvest
writes a correct version 2 bundle, promotes it to `current`, prints
`outcome=insufficient-evidence`, and exits 1.

`test_baseline_capture.py::test_harvest_runs_fresh_correlated_aba_and_persists_bundle` documents
exactly this sequence (`assert outcome == "insufficient-evidence"` on the first harvest,
`assert second_outcome == "exact"` on the second), and
`test_baseline_harvest.py::test_main_reports_comparison_outcome_in_exit_code` pins
`INSUFFICIENT -> 1` with no bootstrap case, so the branch's own tests lock the behaviour in.

**Failure scenario.** The scout's own acceptance procedure is "the first run writes version 2, the
second reports an exact comparison". On a fresh machine the first run exits 1. Any wrapper, CI
step or operator reading the exit code concludes the baseline harvest failed and that the new
reference is untrustworthy, when it succeeded. The live proof in the build record never reached
this point (credential blocker), so it has never been observed.

`main` needs the same discriminator the store uses, which requires the bootstrap fact to reach it:
return the `BaselineBundle` (or a `(ref, outcome, is_bootstrap)` triple) rather than the outcome
alone.

---

## M4. Major — `unresolved_pointers` is computed and discarded; the refusal reaches the operator with no subject

`api/src/transport_matters/baseline_evidence.py::BaselineComparison` line 162, populated at
lines 346 and 377

D3 made naming the unresolved pointers a requirement, not polish: "the operator therefore receives
a refusal with no subject". The field was added and is populated correctly. It is then dropped
everywhere:

- `baseline_capture.py::harvest_controlled_baseline` (lines 149-155) copies only
  `reference_bundle_id`, `reference_outcome` and `reference_reasons` into the bundle.
  `BaselineBundle` has no field for the pointers, so they are not persisted.
- `harvest_controlled_baseline` returns `(BundleRef, DriftOutcome)`, so the CLI cannot see them.
- `baseline_harvest.py::main` prints `written: ... outcome=insufficient-evidence <path>`.

`rg unresolved_pointers` over the whole repo returns three hits in `baseline_evidence.py` and one
test assertion. There is no production reader.

**Failure scenario.** The operator hits the routine INSUFFICIENT that D3 predicted becomes the
common verdict. They get `outcome=insufficient-evidence` on stdout and, if they open the bundle,
`reference_reasons: ["presence changes require another controlled probe"]`. Nothing tells them
which pointer to re-probe or what its presence ratio was, which is the exact condition D3 required
this branch to remove. Persist the pointers on `BaselineBundle` beside `reference_reasons` and
print them.

---

## m5. Minor — no test asserts the comparator returns COMPATIBLE, and COMPATIBLE grants promotion

`api/src/transport_matters/test_baseline_evidence.py`

`rg COMPATIBLE` over both baseline test modules returns two hits, both parametrized enum inputs
(`test_bundle_store_promotes_only_passing_comparisons`, `test_main_reports_comparison_outcome_in_exit_code`).
Neither runs `compare_baseline_bundles`. The COMPATIBLE branch (lines 368-373: changed pointers,
equal fingerprint, no removals, every candidate `value_evidence != UNKNOWN`) has no test, and it
is one of only two outcomes that repoint `current`. The scout's test plan asked for one case per
outcome; EXACT, BREAKING and INSUFFICIENT landed, COMPATIBLE did not.

---

## m6. Minor — the mirror case named in the brief is not pinned by a test

`api/src/transport_matters/test_baseline_evidence.py::test_presence_sampling_reports_insufficient_without_changing_static_membership`

That test covers the original contradiction (a constant field added in 3/3 vs 2/3 probes: BREAKING
vs INSUFFICIENT, with `assert fully_observed.static_fingerprint == undersampled.static_fingerprint`
proving presence-independent membership). It does not cover the mirror the triage reproduced: a
field the harness did not change at all which merely flickers out of probe B, previously
`breaking-drift` from nothing. I verified the fixed code handles it:

```
reference field in 3/3, candidate same value in 2/3
  -> insufficient-evidence, unresolved=('/feature',), fingerprint_equal=True
```

Correct, and unpinned. Same gap for the removal pair the scout specified: a removed pointer the
reference observed absent at least once should be INSUFFICIENT and named (the code does this via
the presence branch), while
`test_removing_demonstrated_static_pointer_is_breaking` covers only the always-present half.

---

## Checked and clear

**1. Promotion.** Promotes iff `reference_bundle_id is None` or `reference_outcome` in
{EXACT, COMPATIBLE}. Compared BREAKING and INSUFFICIENT do not promote. The bootstrap arm is safe
because `BaselineBundle.validate_probe_contract` (line 201) forces bootstrap bundles to
INSUFFICIENT, so `reference_bundle_id is None` cannot smuggle in a BREAKING promotion. All four
compared outcomes are parametrized in `test_bundle_store_promotes_only_passing_comparisons`; the
bootstrap arm is exercised by the two-harvest test. Correct as filed. (The exit-code half of the
same field is M3.)

**2. Version rejection.** `read_baseline_bundle` json-decodes first and rejects
`artifact_schema_version != 2` with "unsupported baseline bundle schema; regenerate the baseline"
before `BaselineBundle.model_validate`; `read_current_baseline` rejects a non-2 pointer with
"unsupported baseline current pointer schema; regenerate the baseline". Both name regeneration.
`harvest_controlled_baseline` calls `read_current_baseline` before the probe plan and before any
`prepare_captured_run`, so rejection precedes every live launch. Covered by
`test_version_one_bundle_load_requires_regeneration` and
`test_version_one_current_pointer_requires_regeneration`.

**3. D3 correctness.** The two-axis split does make the reported contradiction unrepresentable
rather than relocating it: `static_records` membership is now `len(normalized_nodes) >= 2 and one
distinct digest`, with no presence conjunct, so the 3/3 and 2/3 bundles produce an identical
fingerprint (asserted in the test, and re-observed by me). The verdicts then differ on the
presence axis alone: 3/3 is a genuinely new always-present constant (BREAKING via fingerprint),
2/3 refuses to rule (INSUFFICIENT, pointer named). The mirror case behaves per the decision;
see m6 for the coverage gap, and M2 for the one place presence and value evidence are still
entangled.

**4. Correlation.** Real. `_capture_probe` builds `launch_delivery_fields(prompt, delivery_id)` and
threads both into `_wait_for_correlated_exchange`, which now parses each completed candidate with
`read_captured_exchange` and matches `extract_delivery_id(captured.request_ir,
launch_fields=...) == delivery_id`. `extract_delivery_id` is not mocked in the test. The restored
fixture does wrap the controlled prompt: the title exchange's request is
`{"messages": [{"content": f"Generate a title for: {request.initial_prompt}"}]}` and its IR carries
the wrapped text, so under the deleted substring correlator it would have matched, produced two
candidates, and raised `BaselineCorrelationError`. The test asserts only `owned000` is selected in
all three probes. `correlation_method` is now `Literal["delivery-id"]`.

**5. Adapter context.** Follows the precedent, not a facade. `_transcript_has_reply` builds the
same `SessionBinding` shape as
`harnesses/certification_evidence.py::CapturedRunEvidenceSource._check_transcripts`, field for
field, including the deliberate `cwd=""` / `workspace_slug=""` / `workspace_hash=""` and
`provider=adapter.provider`, substituting `path.stem` for the snapshot stem and file mtime for
`facts.recorded_at`. No adapter method, provider switch, or wrapper type was added, and
`_json_has_assistant_role` plus the raw line reader were deleted in the same commit. The
`parent_id` / `parent_seq` / `model` threading duplicates ~10 lines of
`index/record_ingest.py::plan_ingest_records` bookkeeping, but that function requires a
`TailCursor` and a `build_record` callback and returns writes and drift spans, so it is not
callable as a boolean predicate; the scout reached the same conclusion. Acceptable as filed.

**6. Preflight order.** `capture_dependencies.check_session_store()` is the first statement of
`_capture_probe`, before `source_home.exists()`, `source_home.mkdir`, `prepare_captured_run` and
the supervisor. `test_session_store_preflight_stops_before_capture_starts` asserts the raise plus
`not (workspace / ".baseline-homes").exists()`, `prepared == []`, `closed == []`,
`terminated == []`. It is a genuine preflight.

**7. Dead code.** `request_inventory::request_contains_text` and
`baseline_capture::_json_has_assistant_role` are both gone with their assertions;
`_json_contains_text` remains and is still called. `_JsonObject`, `_canonical_json_bytes` and
`_json_kind` were also removed, `EvidenceKind.MODEL_DEPENDENT` and
`EvidenceKind.STRUCTURALLY_OPTIONAL` are deleted rather than left orphaned, and no unused import
survives. No orphan found. One note on the substitution rather than a finding: D4 argued
`_json_kind` should stay because `json_tags::json_kind` returns `str` against the closed `JsonKind`
Literal and is deliberately total where the inventory's was deliberately partial. Deleting
`_JsonObject` removed the wrong-tag half of that objection, but the totality half stands and is now
papered over with `cast("JsonKind", json_kind(value))` (`request_inventory.py` line 246), which
converts a would-be `TypeError` into a pydantic `ValidationError`. Unreachable in practice, since
`json.loads` with these hooks can only yield the six JSON types.

**8. Red/green honesty (independent spot-check of two brackets).** Every unit is a test-only commit
followed by a fix commit; I verified the pairing by `git show --stat` across all seven paired
units.

- **U7** (`23452d25` test, `ead2dd60` fix). The fix commit touches `baseline_capture.py` only, +3
  lines, so the shipped test is byte-identical to the red one. Before it, `_capture_probe` never
  called `check_session_store`; nothing in the call path raises `RuntimeError("session store
  unavailable")`, and the test also asserts `prepared == []`. It could not have passed. Clean.
- **U4** (`c6870c05` test, `9a4a763f` fix). The fix commit does edit the test file, so I read the
  edit: it is a mechanical rename of `classifications` to `(value_evidence, presence)` in the three
  pre-existing tests plus the same rename inside one new test. The red versions were genuinely red:
  `test_presence_sampling_...` asserts the 3/3 and 2/3 fingerprints are equal, which the old
  `classifications == (EvidenceKind.STABLE,)` membership filter made false;
  `test_removing_demonstrated_static_pointer_is_breaking` asserts BREAKING where the old
  `pointer in candidate_evidence` conjunct returned INSUFFICIENT (the exact mechanism triage
  finding 4 described); and the red form of `test_exact_comparison_reads_value_evidence` degraded
  `classifications` on a model the old EXACT branch never read.
- Caveat worth recording rather than a finding: U0, U3, U5 and U6 also amend tests in their fix
  commits. For U6 this is unavoidable — the red tests call `_transcript_has_reply(path, prompt)`
  and the fix adds required `harness=` / `run_id=` keywords — but it does mean the shipped test text
  never executed against the pre-fix code in those four units.
- The two trailing `style(...)` commits (`f29e8c16`, `0192c746`) are pure reformatting; I read both
  diffs in full and no assertion, condition or branch changes.

**Not re-litigated.** Presence semantics, presence-independent `static_records` membership,
artifact schema version 2 with hard v1 rejection, and the no-new-production-surface rule. No
violation of any of the four found: no production file, helper, type, adapter facade, command,
mask, parser or parallel compatibility path was added, and `EvidenceKind` was reused for the value
axis with an inline `Literal["always", "sometimes"]` for presence.

---

## Reproduction artifacts

Scratchpad, not committed, no repo file touched:
`/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/3548f697-2ef7-4304-9ae1-75037453294d/scratchpad/probe_comparator.py`
— B1 (P1), m6 (P2), M2 (P3 and its P4 control), built on
`test_baseline_evidence::_probe` / `_bundle` and a real
`normalize_request(..., cross_launch=True)` projection.

## Sign-off

conditional (round 1, superseded by the delta round below): I sign off conditional on the following changes: 1. `classify_aba` must fingerprint a
surface that includes the request scalars `normalize_request` drops (`sampling`, `stream`,
`metadata`), so a `max_tokens`, `temperature` or `stream` change cannot report EXACT and promote
itself to `current`. 2. `compare_baseline_bundles` must not let an unresolved presence delta
suppress a decided fingerprint change; BREAKING wins, or is reported alongside the unresolved
pointers. 3. `baseline_harvest::main` must exit 0 on the bootstrap harvest, using the same
`reference_bundle_id is None` discriminator `write_baseline_bundle` already uses. 4.
`BaselineComparison.unresolved_pointers` must reach a reader: persisted on `BaselineBundle` and
printed by the CLI. 5. A test must assert `compare_baseline_bundles` returns COMPATIBLE. 6. A test
must pin the mirror presence case (unchanged constant field flickering out of one probe reports
INSUFFICIENT, not BREAKING).

---

# Delta re-verification: `0192c746` → `9d8dcd16`

Tree verified pristine at `9d8dcd16e024` before and after (`git status --short --branch` shows the
branch line only). `0192c746` and `5591db86` both confirmed ancestors of HEAD by
`git merge-base --is-ancestor`. Ten correction commits, five test/fix pairs. I did not re-run
`just check` / `just test`; the orchestrator reported them green. Deltas only; I did not re-review
the parts of the diff no correction touched.

**Verdict: 1 Major, 4 Minor.** All six of my round-1 findings are resolved. C1 is materially
better than the first attempt and I could not find a way to make it miss a wire change. C2 is
where the new defect is: it fixed the top-level case and left the nested case inverted, so a
routine presence flicker inside `system`, `tools` or `messages` now reports a false
`breaking-drift` naming the container.

## Round-1 findings: resolution

| # | Finding | Status | Evidence |
|---|---|---|---|
| B1 | Fingerprint dropped sampling / stream / model | **Resolved** | `baseline_evidence.py::classify_aba` now decodes `probe.raw_request_base64`, applies `mask_cross_launch_body`, and inventories that. Re-ran my round-1 probe unchanged: `max_tokens 8192→16384`, `stream true→false`, `temperature 1.0→0.7` all now `breaking-drift`, `fingerprint_equal=False`. Pinned by `test_stable_wire_scalar_changes_are_breaking` over all four scalars. |
| M2 | Presence refusal suppressed a decided BREAKING | **Resolved** | `compare_baseline_bundles` now computes `static_changes` / `decided_static_changes` and returns BREAKING before the presence branch. My round-1 P3 (breaking + unrelated flicker) now returns `breaking-drift` naming `/core`; P4 control unchanged. Pinned by `test_unresolved_presence_does_not_hide_an_unrelated_breaking_change`. See N1 for the case this fix does not reach. |
| M3 | Bootstrap harvest exited 1 | **Resolved** | `baseline_store.py::promotes_baseline` is now the single rule; `write_baseline_bundle` and `baseline_harvest.py::main` both call it. The exit matrix gained the `(INSUFFICIENT, reference_bundle_id=None) → 0` arm in `test_main_reports_bootstrap_and_comparison_outcomes`. |
| M4 | `unresolved_pointers` computed and discarded | **Resolved** | `BaselineBundle.reference_unresolved_pointers` persists them, `harvest_controlled_baseline` returns the bundle, `main` prints `unresolved=…` and `settle=…`. Round-tripped through disk in `test_presence_refusal_names_evidence_and_settlement` and `test_harvest_persists_unresolved_comparison_pointers`. The refusal reason now carries the ratios (`reference=2/3 candidate=3/3`) and the settlement rule. |
| m5 | No COMPATIBLE test | **Resolved** | `test_prompt_derived_field_addition_is_compatible` drives `compare_baseline_bundles` to COMPATIBLE. |
| m6 | Mirror presence case unpinned | **Resolved** | `test_unchanged_field_flickering_out_of_probe_b_is_insufficient` asserts equal fingerprints, INSUFFICIENT, and `unresolved_pointers == ("/static",)`. Correct for a top-level field; N1 is the same case one level down. |

## C1 judged adversarially

The question asked was whether the masked raw body covers every raw request pointer and whether
the date/cwd masking survived. Both hold, and I could not construct a third failure in the unsafe
direction.

- **Coverage is total, not projected.** `classify_aba` inventories
  `canonical_json(mask_cross_launch_body(raw_body))`, so the node set is the whole wire document:
  root, every container, every leaf. I confirmed the pointer set is identical to
  `probe.raw_nodes` — `mask_cross_launch_body` rewrites string *values* only (the loop assigns
  `container[key] = _mask_cross_launch_text(value)` and never touches a key), so masking cannot
  add, drop or rename a pointer. That matters beyond tidiness: `decided_static_changes` subtracts
  `unresolved_presence`, which is derived from the *unmasked* `raw_nodes`, so the two sets have to
  live in one pointer space. They do.
- **Masking survived.** `test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking`
  now feeds the raw wire body instead of a normalized projection and still returns EXACT, so both
  directions land in one commit as briefed.
- **The masks are anchored, not broad.** `_CROSS_LAUNCH_MASKS` are line- or tag-anchored
  (`^- Run ID: "…"`, `<cwd>…</cwd>`, `<current_date>…</current_date>`, the scratchpad line, the
  git-status block). Nothing in them can swallow a harness prose change, and the Claude build
  suffix is deliberately left unmasked.
- **Cross-launch volatility that masking does not cover is caught by the intra-bundle filter, not
  missed.** A node enters `static_nodes` only if every probe that has it agrees on the digest, so
  anything varying per launch (session ids, delivery ids, ports, the prompt itself, every
  container above it) is excluded from the fingerprint on both sides rather than compared. That is
  the correct honest surface and it is what makes the raw body safe to fingerprint.
- **The residual risks all fail safe (false BREAKING, no promotion), and I am not filing them as
  findings.** Two exist. First, the raw body compares `system` and `tools` positionally, where
  `normalize_request` compared them as sets, so a stable reordering across launches reads as drift;
  reordering is arguably real drift, and per-probe reordering is already excluded by the
  intra-bundle filter. Second, machine-specific prose that no mask targets and that is stable
  within a run makes a baseline non-portable across machines. Both are properties of the design the
  mask comment already states, and both refuse rather than promote.
- **One structural gap remains, filed as N3:** `static_fingerprint` and `static_nodes` are stored
  as an unvalidated pair.

## N1. Major (new, introduced by C1 + C2) — a presence flicker one level below the root reports `breaking-drift` instead of `insufficient-evidence`, and names the container

`api/src/transport_matters/baseline_evidence.py::compare_baseline_bundles`, the
`decided_static_changes = tuple(sorted(static_changes - set(unresolved_presence)))` subtraction
(line 356)

C1 widened the fingerprint node space to the whole document, so every **container** is now a
static node whose digest covers its whole subtree. When one optional key flickers out of probe B,
that key stays static in both bundles (present in A1 and A2 with one digest), but every ancestor
container becomes non-static in the candidate, because its own digest now differs between probes.
Those ancestors are not in `unresolved_presence` — their evidence is `presence="always"` — so the
subtraction does not remove them and they land in `decided_static_changes`, which is now tested
first.

The round-1 mirror case and its new regression test are both **top-level**, where the only ancestor
is the root, and the root is already excluded from `static_nodes` because the A and B prompts
differ. That is the whole reason the fix looks correct. One level down it inverts:

```
nested: /tools/0/cache_control present 3/3 -> present 2/3, nothing else changed
  outcome    = breaking-drift
  reasons    = ('stable baseline fingerprint changed at /tools, /tools/0',)
  unresolved = ()
  ref  static pointers = ['/system', '/tools', '/tools/0', '/tools/0/cache_control',
                          '/tools/0/description', '/tools/0/name']
  cand static pointers = ['/system', '/tools/0/cache_control',
                          '/tools/0/description', '/tools/0/name']

control, same flicker at top level: /cache_control 3/3 -> 2/3
  outcome    = insufficient-evidence
  unresolved = ('/cache_control',)
```

The two differing static nodes are exactly `/tools` and `/tools/0`, the ancestors. No leaf changed
value.

**Failure scenario.** A Claude release makes `cache_control` on the last tool intermittent, or
drops one `<env>` line from the system block on some launches. Nothing about the request contract
changed. The operator runs `baseline_harvest`; the CLI prints
`outcome=breaking-drift` with no diagnostics at all (see N2), and the bundle records "stable
baseline fingerprint changed at /tools, /tools/0". The operator is told the tool definitions broke.
They diff the tools, find them byte-identical in every probe that has them, and have no path to the
real answer, which is "re-probe, one pointer is intermittent". This is the same class of false
`breaking-drift`-from-nothing that D3 exists to remove, and because every optional field in a real
Anthropic body lives inside `system`, `tools`, `messages` or `metadata`, the top-level fix covers
close to none of the real cases.

**Direction.** Subtract ancestors as well as exact matches: drop from `decided_static_changes` any
pointer that is a prefix of an unresolved pointer. That keeps the M2 fix intact — I checked the
mixed case where `/tools/0/description` genuinely changes *and* `/tools/0/cache_control` flickers:
the leaf `/tools/0/description` is not an ancestor of the unresolved pointer, so it survives the
subtraction and the verdict stays BREAKING, correctly attributed to the leaf.

## N2. Minor (new) — BREAKING never prints a reason, so the pointer attribution C2 added is invisible

`api/src/transport_matters/baseline_harvest.py::main`

`diagnostics` is populated only when `bundle.reference_unresolved_pointers` is non-empty, and every
BREAKING branch of `compare_baseline_bundles` returns `unresolved_pointers=()`. So the new
`stable baseline fingerprint changed at /core` attribution — the whole point of C2's second half —
never reaches stdout. The operator gets `written: claude/… outcome=breaking-drift <path>` and must
open the JSON to learn which pointer moved. C4 gave the refusal a subject and left the harder
verdict without one.

**Failure scenario.** A harness release changes one system-prompt line. The harvest exits 1 with a
bare `outcome=breaking-drift`. CI logs the line, the operator sees a red run with no field named,
and the drift is diagnosed by hand. Printing `bundle.reference_reasons` on any non-promoting
outcome fixes it in one line.

## N3. Minor (new) — `static_fingerprint` and `static_nodes` are stored as an unvalidated pair, leaving one comparator branch unreachable by construction

`api/src/transport_matters/baseline_evidence.py::BaselineBundle.validate_probe_contract`, against
`compare_baseline_bundles` line 363

`static_fingerprint` is now `canonical_digest([node.model_dump(mode="json") for node in
static_nodes])`, so it is fully derived from a field stored beside it, and nothing checks the pair
on load. `ProbeEvidence.validate_raw_evidence` validates every other digest in the artifact against
its embedded bytes, and U1's own test calls the bundle "immutable, self-contained and
hash-validated", so this is the one derived value in the bundle that is taken on trust.

The consequence is visible in the comparator: `if reference.static_fingerprint !=
candidate.static_fingerprint and not static_changes` can only fire for a bundle whose stored
fingerprint disagrees with its stored nodes, which `classify_aba` cannot produce. It is a defensive
branch against an inconsistency the model should reject at the boundary instead, and it cannot be
covered by a test that goes through the public constructor.

**Failure scenario.** A bundle is hand-edited or partially corrupted so that `static_nodes` loses
an entry while `static_fingerprint` is left alone. `read_baseline_bundle` accepts it and it becomes
the reference. The EXACT gate reads the stale fingerprint, the BREAKING attribution reads the
truncated nodes, and the two halves of the comparator disagree about what the baseline says. Add
the equality check to `validate_probe_contract` and the defensive branch can be deleted.

## N4. Minor (new) — the BREAKING attribution lists every ancestor of the changed pointer

`api/src/transport_matters/baseline_evidence.py::compare_baseline_bundles`, `changed_at`
(line 358)

`decided_static_changes` is the raw set of differing static pointers, which for any nested change
includes the leaf and every container above it. A change to one tool description reports
`changed at /tools, /tools/0, /tools/0/description`; N1's flicker reports `/tools, /tools/0`. On a
real body with a multi-thousand-token system block, a single leaf change produces a reason string
listing its whole ancestor chain, and the pointer that actually moved is the last one rather than
the only one. Reporting only pointers with no strict descendant in the set gives the operator the
one line they need. (Observed in the same runs: a synthetic body where the root itself is static
renders the root pointer as an empty string, `changed at , /core`. Unreachable in production, since
the A and B prompts always differ, but it is the same missing filter.)

## N5. Minor (new) — the harvest CLI exit matrix is proven against a `str` subclass masquerading as a bundle

`api/src/transport_matters/test_baseline_harvest.py::_HarvestedBundle`

The double is `class _HarvestedBundle(str)` with four attributes attached in `__new__`, standing in
for a `BaselineBundle`. Subclassing `str` is vestigial: it exists so `assert f"outcome={outcome}"
in stdout` keeps working now that the CLI prints `bundle.reference_outcome` rather than the outcome
it was handed. The result is a test that pins the bootstrap-versus-compared exit rule — the rule
M3 was about — against an object with no structural relationship to the model whose fields the rule
reads. `SimpleNamespace`, or a real `BaselineBundle`, costs the same and does not lie about the
type. The store-side rule is separately covered against real bundles by
`test_bundle_store_promotes_only_passing_comparisons`, and both sides now call one
`promotes_baseline`, so the exposure is small.

## Corrections examined and found clean

- **C3.** `promotes_baseline` is one function, called by `write_baseline_bundle` and by `main`, so
  the store and the CLI cannot diverge again. `harvest_controlled_baseline` returning
  `(BundleRef, BaselineBundle)` is what makes that possible without a new type or a triple.
- **C5.** `resolved_workspace.mkdir(parents=True, exist_ok=True)` is gone from
  `harvest_controlled_baseline`, and the workspace is now created as a by-product of
  `source_home.mkdir(parents=True)` in `_capture_probe`, which runs after `check_session_store`.
  The renamed test asserts `not workspace.exists()`, which is strictly stronger than the
  `.baseline-sources` assertion Grok asked for. Nothing between the harvest entry and the first
  probe touches the workspace path: `read_current_baseline` works off `output`.
- **C6 / m5 / m6.** The three D3 tests each isolate one variable and I re-derived each verdict
  independently. The authorised pass-before-fix cases are as briefed and I am not counting them as
  a red/green violation.
- **Artifact shape.** `static_nodes` and `reference_unresolved_pointers` were added to
  `BaselineBundle` without a version bump, so a v2 bundle written between `0192c746` and
  `9d8dcd16` now fails `model_validate` with a raw pydantic error rather than the branch's
  "regenerate the baseline" message. Not filed: the branch is unmerged, no v2 artifact has been
  published, and the live proof shows no store was ever written.
- **Layering.** `baseline_evidence` importing `mask_cross_launch_body` from
  `session.wire_normalization` reuses the existing seam rather than copying it, adds no new
  production symbol beyond making one name public, and introduces no cycle:
  `session.wire_normalization` does not import the baseline modules.
- **`normalized_request` is now write-only.** `_build_probe_evidence` still populates it and
  nothing reads it. I am not filing it: it sits beside `transcripts`, which is also captured
  evidence rather than compared evidence, and dropping it would be a v2 shape change for no
  behavioural gain. Worth a note only because it is the projection the first C1 attempt trusted;
  leaving it in the artifact invites a future reader to compare it again.

## Reproduction artifacts (round 2)

`/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/3548f697-2ef7-4304-9ae1-75037453294d/scratchpad/probe_corrections.py`
— N1 (nested flicker versus the top-level control), plus the static-pointer dumps quoted above.
The round-1 script `probe_comparator.py` was re-run unchanged at `9d8dcd16` to evidence B1 and M2
as resolved. Both are scratchpad files; no repo file was touched.

## Sign-off (delta round, superseded by the final round below)

conditional: I sign off conditional on the following changes: 1. `compare_baseline_bundles` must
not report `breaking-drift` for a presence flicker below the root; exclude ancestors of
`unresolved_pointers` from `decided_static_changes`, not just exact matches, so a flicker inside
`system`, `tools` or `messages` reaches the same INSUFFICIENT verdict the top-level case already
reaches. 2. `baseline_harvest::main` must print `reference_reasons` for a non-promoting outcome, so
the pointer attribution C2 added is visible to the operator on a BREAKING verdict. 3.
`BaselineBundle.validate_probe_contract` must assert `static_fingerprint` equals the digest of
`static_nodes`, after which the `and not static_changes` branch in `compare_baseline_bundles` can be
deleted. 4. The BREAKING reason must name only the pointers with no strict descendant in the
changed set, not the whole ancestor chain. 5. `_HarvestedBundle` must stop subclassing `str`.

---

# Final round: `9d8dcd16` → `10165c99`

Eight commits, four red/green pairs. `git merge-base --is-ancestor` confirms both `5591db86` and
`9d8dcd16` are still ancestors of `10165c99`; no history was rewritten. Tree pristine at
`10165c99` before and after this pass; my only writes are this file and three scratchpad probes.
Gate and bracket results are the orchestrator's, independently verified, and I did not re-run them.

## Round-2 findings: resolution

| # | Finding | Status | Evidence |
|---|---|---|---|
| N1 | Major. Presence flicker below the root reports `breaking-drift` at the containing pointer. | **Resolved** | `compare_baseline_bundles`: `unresolved_presence` now collapses a flickering subtree to its shallowest pointer, and `decided_static_changes` excludes any pointer that is an ancestor of an unresolved pointer, not just an exact match. Measured: nested `/tools/0/cache_control` 3/3 → 2/3 now returns `insufficient-evidence` with `unresolved=('/tools/0/cache_control',)`. |
| N2 | Minor. BREAKING never prints a reason. | **Resolved** | `baseline_harvest::main` gained an `elif not promotes` arm printing `reason=<reference_reasons>`. `promotes_baseline` is now evaluated once and reused for both the diagnostic and the exit code. |
| N3 | Minor. `static_fingerprint` and `static_nodes` stored as an unvalidated pair. | **Resolved** | `BaselineBundle.validate_probe_contract` recomputes `canonical_digest` over `static_nodes` and raises `static fingerprint does not match static nodes`. The unreachable comparator branch is deleted. |
| N4 | Minor. BREAKING attribution lists every ancestor of the changed pointer; the root renders as an empty string. | **Resolved** | The reason now filters `decided_static_changes` to pointers with no strict descendant in the set. Measured: `/tools/0/description` alone, and the root-level case that previously read `changed at , /core` now reads `changed at /core`. |
| N5 | Minor. `class _HarvestedBundle(str)` masquerading as a bundle in the CLI matrix. | **Resolved** | `test_baseline_harvest._harvested_bundle` builds a real `BaselineBundle` through `model_validate`, so the exit-code table is now subject to `validate_probe_contract`. |

## E1 judged in both directions

Both directions hold.

- **Flicker must be INSUFFICIENT.** Nested `/tools/0/cache_control` 3/3 → 2/3 returns
  `insufficient-evidence`, naming the flickering leaf and the 3/3 versus 2/3 ratio.
- **A real container change must stay BREAKING.** Verified on four shapes beyond the branch's own
  tests: a flicker plus a changed sibling leaf (`/tools/0/description`); a flicker plus a newly
  added sibling key (`/tools/0/input_schema/type`); a flicker where the flickering value itself also
  changed (`/tools/0/cache_control/ttl`); and the whole tool entry removed. All four return
  `breaking-drift` and name only the deepest changed pointers.

The prefix arithmetic is sound. `_pointer` in `request_inventory` RFC 6901 escapes `/` as `~1`, so
`f"{ancestor}/"` cannot straddle a key that contains a slash, and `/tools/1` is not treated as an
ancestor of `/tools/10`.

One asymmetry I chased and cleared. The collapse keeps only the shallowest flickering pointer, so a
descendant of an unresolved pointer is no longer protected by the exact-match rule. It does not
matter: at 2/3 the descendant is still static in both bundles (`len(masked_nodes) >= 2`) so it is
not a static change at all, and if its value also changed then BREAKING at that descendant is the
correct verdict.

A flicker to 1/3 still returns `breaking-drift`, but this is not E1's doing and I am not filing it.
A single observation makes `_classify_pointer` return `EvidenceKind.UNKNOWN`, so the pointer never
enters `unresolved_presence_changes`, which requires `STABLE`. I loaded `baseline_evidence.py` from
`9d8dcd16` alongside the current module and ran both over the same bundles: `9d8dcd16` returns
`breaking-drift` for the 1/3 case too, at both top level and nested. It is pre-existing, depth
independent, and sits inside the dispositioned presence semantics.

## E2 judged in both directions: one direction is unproven

- **A real extras change must stay BREAKING.** Proven. A `service_tier` change beside a changed
  launch identity returns `breaking-drift` naming `/service_tier`.
- **A per-launch identifier must stay EXACT.** Proven **only for a value change.** Changing
  `client_metadata`, `previous_response_id` and `prompt_cache_key` together, including a value
  nested inside `client_metadata`, returns `exact`. The masked-body `pop` removes the whole
  top-level key, so depth inside the stripped container is covered.

  It is **not proven, and is false, for a presence change**, which is finding N6 below.

## New findings

### N6. Major. Launch identity is stripped from the fingerprint but not from the evidence axis, so its presence still drives the verdict

`classify_aba` pops `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` from `masked_body` only. The
`observed_schema` and `pointer_evidence` axes are still built from `probe.raw_nodes`, which are
unmasked and unstripped, so `/previous_response_id` and its siblings remain live inputs to
`changed_pointers`, `unresolved_presence` and `removed_pointers` in `compare_baseline_bundles`.
E2 therefore neutralised launch identity on the value axis and left it armed on the presence axis.

Measured, holding everything else constant and varying only where `previous_response_id` appears:

```
absent 0/3  -> present 3/3 : compatible-drift
present 3/3 -> present 2/3 : insufficient-evidence  unresolved=('/previous_response_id',)
present 3/3 -> absent  0/3 : breaking-drift         "demonstrated request fields were removed"
```

The third line is the E2 defect restated: a launch identity key that stops being sent reports
BREAKING, blocks promotion and exits 1. The second line is worse in one respect, because the
refusal asks the operator to make a launch identity key appear in all three probes, which is not
something an operator can settle. The branch's own test varies only the value of these keys, never
their presence, which is why the gate is green.

Reachability, stated honestly. `previous_response_id` is exactly the key whose presence depends on
whether a request is the first of a session; the cell pins `request_shape="first-turn"` and each
probe is a fresh source home, so within one cell the presence should be uniform. The realistic
trigger is a harness upgrade that starts or stops emitting one of these three keys, which is the
event baseline drift capture exists to detect and the event that must not be reported as BREAKING.

Direction: apply one strip rule to both axes. Excluding the same three keys where `nodes_by_probe`
and `leaves_by_probe` are built in `classify_aba` keeps `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`
as the single source of truth and removes the keys from `observed_schema` and `pointer_evidence`
as well as from the fingerprint. Filtering inside `compare_baseline_bundles` instead would leave
the artifact recording evidence the comparator silently ignores.

### N7. Minor. `removed_pointers` is computed and discarded

In `compare_baseline_bundles`, `removed_pointers` is built, tested for truth, and then dropped:
the reason is the constant `"demonstrated request fields were removed"` and
`unresolved_pointers` is left empty. E3 now prints that reason, so the operator gets
`reason=demonstrated request fields were removed` with nothing naming which field. This is the same
defect class C4 fixed for `unresolved_pointers` one round earlier, on the branch immediately below
it. The fix is the shape the branch already uses elsewhere: name the pointers in the reason.

## E4: the deleted branch was genuinely unreachable, and no coverage was lost

`validate_probe_contract` is a `model_validator(mode="after")`, so it runs on every construction of
`BaselineBundle`, both direct construction in `harvest_controlled_baseline` and `model_validate` on
read. The two production construction sites cannot desync the pair: `harvest_controlled_baseline`
passes `analysis.static_nodes` and `analysis.static_fingerprint` from the same `AbaAnalysis`, and
the one production `model_copy` (`baseline_capture.py`, after `compare_baseline_bundles`) updates
only the four `reference_*` fields. So `reference.static_fingerprint != candidate.static_fingerprint
and not static_changes` was unreachable by construction, not merely hard to reach.

No coverage was lost, and the threat model improved. The deleted test forged the mismatch with
`model_copy`, which bypasses pydantic validators and which no production code uses for those
fields. The replacement forges it on disk and asserts `read_baseline_bundle` raises, which is the
reachable corruption path. The deleted test also carried a trivial identical-bundle EXACT
assertion; EXACT remains asserted twice, in both cases in the stronger form of EXACT despite a
change (`test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking` and
`test_cross_launch_extras_are_excluded_without_hiding_real_extras`), and I confirmed the trivial
case still returns `exact` by probe.

## Examined and clean

- **E3.** The `elif not promotes` arm cannot fire on a bootstrap bundle, which promotes, so the
  bootstrap exit-0 semantics C3 established are intact.
- **E5.** `_harvested_bundle` goes through `model_validate`, so the parametrised exit-code table is
  now constrained by the bootstrap and unresolved-pointer invariants rather than asserting against
  a `str`. Importing `_bundle` across two test modules is permitted by the repo's own private
  import boundary test, which is green.
- **E2 layering.** Promoting the inline key set to `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`
  leaves one definition consumed by both `normalize_request` and `classify_aba`. No duplicate set.
- **Standing caveat.** Nothing here was demonstrated against a live harness; the owner Claude
  credential is unavailable and `baseline_harvest --harness claude` exits 1 before capture. Every
  verdict in this file, mine and the branch's, rests on unit evidence.

## Reproduction artifacts (final round)

All in
`/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/3548f697-2ef7-4304-9ae1-75037453294d/scratchpad/`,
no repo file touched: `probe_round3.py` (E1 and E2 both directions, plus the 1/3 case and its
top-level control), `probe_edges.py` (E1 direction 2 on four shapes, and the root attribution),
`probe_extras.py` (N6, the three presence transitions), `probe_regression.py` with `old_evidence.py`
(`git show 9d8dcd16:...` loaded alongside the current module to establish that the 1/3 case is
pre-existing).

## Sign-off (final round)

conditional: I sign off conditional on the following changes: 1. `classify_aba` must exclude
`CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` when it builds `nodes_by_probe` and `leaves_by_probe`,
not only when it builds the masked fingerprint body, so a launch identity key that starts or stops
being sent cannot reach `changed_pointers`, `unresolved_presence` or `removed_pointers`; today
`present 3/3 -> absent 0/3` on `previous_response_id` returns `breaking-drift` and `3/3 -> 2/3`
returns `insufficient-evidence`, both of which E2 was meant to prevent. 2. The test that locks this
must vary the presence of those keys across bundles, not only their values, in both the disappearing
and the flickering direction. 3. The `removed_pointers` BREAKING reason in
`compare_baseline_bundles` must name the removed pointers, since E3 now prints that reason to the
operator and the constant string identifies no field.
