# Comparator reassessment: `fix/comparator-truth` at `10165c99`

Read-only. No repo file touched, no branch write. Every verdict below was produced first-hand
through the repo interpreter (`cd api && uv run python`, 3.14) against the branch head, and where I
propose a change I ran it rather than describing it. Reproduction artifacts are listed at the end.

Scope correction, stated up front: the branch carries **36 commits** off `5591db86`, not 25. Eighteen
`test:` / `fix:` pairs plus two `style:` commits. The count matters to R2, so it is measured, not
quoted.

---

## R1. Diagnosis

**The hypothesis is right, and it is sharper than stated.** The comparator does model a tree as a
flat set, and it does handle the two axes through separate paths. But those are not two independent
weaknesses. They are one defect with two faces, and the four corrections have been alternating
between them.

There is a third live instance that neither reviewer filed. I found it by testing the invariant
rather than the case, which is the whole point.

### The mechanism, in one paragraph

`classify_aba` builds **two node universes from the same probe bytes**:

| Universe | Built from | Feeds | Membership rule |
|---|---|---|---|
| raw | `probe.raw_nodes`, `probe.inventory.leaves` | `observed_schema`, `pointer_evidence` | none: every pointer in any probe |
| masked | `mask_cross_launch_body(raw)` then a pop of `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` | `static_nodes`, `static_fingerprint` | present in ≥2 probes with one digest |

`compare_baseline_bundles` then produces one verdict by reconciling them: it computes changes on the
raw universe (`changed_pointers`, `unresolved_presence`, `removed_pointers`) and changes on the
masked universe (`static_changes`), and subtracts one from the other. Because the two universes do
not have the same membership, **any exclusion applied to one leaves the other armed**; and because
the reconciliation is a subtraction between sets of pointers drawn from a tree, it needs a
tree relation, which the code writes inline, from scratch, three separate times, in three different
directions:

- `unresolved_presence` keeps a pointer when **no ancestor of it** is in the set (drops descendants).
- `decided_static_changes` drops a pointer when it **is, or is an ancestor of**, an unresolved
  pointer (keeps descendants).
- the `changed_at` reason keeps a pointer when **no strict descendant of it** is in the set.

Rules 1 and 2 disagree about which direction survives, and rule 1 runs first. Every pointer rule 1
discards is exactly a pointer rule 2 then fails to protect. That is not a typo in one expression; it
is what happens when a subtree disposition has no representation and each site re-derives it.

### Why every correction landed in the middle and missed the edge

This is the part that answers "four sloppy briefs?" — no.

- **C1 → E2 → N6.** C1 bound the fingerprint to the masked raw body. E2 excluded launch identity by
  popping the extras keys **from `masked_body` only**, because that is where the fingerprint is
  built. The raw universe still carries `/previous_response_id`, so the key remains a live input to
  `changed_pointers` and `removed_pointers`. The exclusion was applied to the axis the brief named
  and to the universe the fix was standing in.
- **C2 → E1 → Grok #5.** Before E1, `decided_static_changes` subtracted the unresolved set by exact
  match, and the unresolved set contained the **whole** flickering subtree, so descendants were
  protected by accident. E1 added the shallowest-pointer collapse (to fix the reason string and the
  ancestor escalation) and thereby **deleted the accidental descendant protection**, then re-added
  protection for ancestors only. The correction moved the bug one level down. Opus chased this exact
  asymmetry and cleared it on the ground that "at 2/3 the descendant is still static in both
  bundles" — true when the descendant's value is unchanged, false when it changed, which is Grok's
  case and which I reproduced (P2 below).

Neither reviewer was wrong about the case in front of them. The code has no invariant to violate, so
a review can only find instances, and a fix can only close instances.

### The three live instances, measured at `10165c99`

| # | Case | Verdict at HEAD | D3 says |
|---|---|---|---|
| P1 | `/previous_response_id` present 3/3 → absent 0/3, nothing else changed | `breaking-drift` "demonstrated request fields were removed" | launch identity must not reach the verdict on **either** axis (Opus N6) |
| P2 | `/tools/0/cache_control` flickers out of probe B, and its child `/type` also changed value | `breaking-drift` at `/tools/0/cache_control/type`, `unresolved=()` | INSUFFICIENT at the flickering pointer (Grok #5) |
| P3 | a constant field carried 3/3 in the reference and **1/3** in the candidate | `breaking-drift` at `/feature` | INSUFFICIENT — "constant when present and absent at least once" |

**P3 is the unfiled third instance, and it is the cleanest proof that this is one defect.** The
presence refusal fires only when `value_evidence == EvidenceKind.STABLE`, and `_classify_pointer`
only emits `STABLE` when a pointer is carried by **at least two** probes. So the presence decision is
gated on a value-axis predicate that itself encodes a presence threshold. The same field, the same
kind of change, refuses at 2/3 and rules BREAKING at 1/3. Opus saw the 1/3 behaviour, correctly
established it was pre-existing rather than E1's doing, and declined to file it. Pre-existing is not
the same as unrelated: it is the same root cause, one round older.

Depth-independent, measured over presence ratio × depth × value change (16 cells, `sweep.py`):

```
HEAD 10165c99 : 4 violations of the D3 invariant  (top and nested, 1/3, both value cases)
```

### What the domain actually is, and why the flat set cannot hold it

`request_inventory::observe_request_json` emits a node per pointer whose digest **covers its whole
subtree** — the scout doc records this as "containers inherit variability", and it is why a fully
constant object contributes its own bytes once per level of depth to `static_nodes`. So a single
leaf event does not produce a pointer event; it produces **O(depth) correlated pointer events**, one
per ancestor. A per-pointer classification set has no way to say "this subtree is under
adjudication", so every rule that must respect adjudication has to rebuild the relation out of
string prefixes, and each rebuild is an independent chance to pick the wrong direction. Three sites,
three directions, two of them contradictory today.

The scout doc predicted precisely this, in D2:

> the two-axis split does not on its own fix the verdict. A corrected predicate is still required,
> and a determined caller can still write the wrong predicate over two fields.

The split was carried out **on the record** (`PointerEvidence.value_evidence` and `.presence` are
now two single-valued fields, correctly). It was never carried out **on the derivation** (still two
universes) or **on the decision** (the presence rule still reads the value axis). That is the root
cause, named: *the axes are separated in the type and joined in the code.*

### Root cause, as file+symbol

- `baseline_evidence::classify_aba` — builds `nodes_by_probe` / `leaves_by_probe` from unstripped raw
  nodes and `masked_nodes_by_probe` from the stripped, masked body. One exclusion rule, applied to
  one of two universes.
- `baseline_evidence::compare_baseline_bundles` — three inline pointer-prefix expressions standing
  in for one missing subtree relation, in three directions.
- `baseline_evidence::compare_baseline_bundles` (`unresolved_presence_changes`) and
  `baseline_evidence::_classify_pointer` — the presence refusal is conditioned on
  `value_evidence == STABLE`, whose emission requires ≥2 carrying probes.

Not the cause: the briefs. They named cases because the code offers nothing else to name. The
sixteen red/green brackets are honest and the gate is green because **the tests are case-shaped
too**; a case-shaped suite cannot fail on the symmetric counterpart of the case it pins.

---

## R2. The split question

**Answer: the split is real at symbol level, entangled at commit level, and worth less than it
costs. Do not split.**

### Which commits fall on each side

Comparator model and fingerprint semantics (15 commits):

```
1d2998bb + 46b205a4   fingerprint normalized requests      (superseded by caead545)
c6870c05 + 9a4a763f   separate value and presence evidence
e3bc0ab0 + caead545   fingerprint masked raw requests
44b37b6b + eda1af4f   rank decided drift first
330f1b17 + c3eef8da   surface refusal details              (comparator output + CLI plumbing)
0f1f6b27 + fcbd20da   resolve nested presence at leaves
22bbf888 + 47688c85   exclude launch identity extras
d2d0b376 + 10165c99   validate static evidence pair
0192c746              style: format comparator condition
```

Independent of the pointer model (21 commits):

```
86cfcc9e + b1a528d7   consume comparator outcomes          (store promotion + CLI exit)
e7f9b12c              require artifact schema version 2
3a6373db + b68afc8e   reuse shared JSON disciplines        (triage #5, #9, #10; -51/+12 lines)
5fa903af + 39f4ac6d   correlate by launch delivery         (triage #1)
a50cf740 + 13e94025   normalize complete transcript records (triage #3, #6)
23452d25 + ead2dd60   run session store preflight
84e372d1 + 9d8dcd16   defer workspace creation
7a259be0 + c2ce9985   accept bootstrap harvests
4290131a + 8f0c8e70   print breaking reasons
f29e8c16              style: repository formatting
```

### Is the split clean?

**At symbol level, yes.** The pointer model lives entirely in `classify_aba`, `_classify_pointer`,
`compare_baseline_bundles`, `_presence_refusal` and `_repeat_a_outcome`. Nothing in the capture,
correlation, transcript, preflight, canonicalization or store code reads a pointer classification.

**At commit level, no**, for three reasons that compound:

1. **Supersession inside the file.** `46b205a4` is overwritten by `caead545`; `eda1af4f` is
   overwritten by `fcbd20da`; `fcbd20da` is refined by `10165c99`. Dropping the comparator side is
   not dropping commits, it is reconstructing a state of `baseline_evidence.py` that never existed
   and that no test in the tree describes.
2. **TDD pairing.** Every fix has a red-test commit immediately below it. Dropping a fix orphans its
   test, so a split is 15 cherry-picks plus 15 test deletions plus a rebuild, not a range cut.
3. **Three non-comparator commits touch `baseline_evidence.py` anyway** — `e7f9b12c` (schema
   version literal), `39f4ac6d` (`ProbeEvidence` correlation fields), `f29e8c16` (formatting) — and
   `e7f9b12c`'s `Literal[2]` describes a shape that `caead545` and `c3eef8da` finish defining. The
   version number of the shipping half would be a lie about a shape it does not carry.

### What the shipping half would be worth on its own, honestly

Real, and less than it looks. It closes triage #1, #3, #5, #6, #9, #10, the preflight-ordering gap,
the bootstrap exit-1, and the promotion gate — all genuine, all invisible plumbing. Artifact churn
is free (the store is empty and this repo carries no backward-compat obligation), so "regenerate the
bundles after the comparator lands" costs nothing.

But its **headline** feature is `b1a528d7` + `8f0c8e70`: the drift verdict finally reaches the
operator as an exit code, and `baseline_store::promotes_baseline` now gates `current` on that
verdict. Wire that to `main`'s comparator and you get the worst configuration on the table.
`main`'s `classify_aba` builds `static_records` from **unmasked raw digests** of pointers classified
`(STABLE,)`, so `<cwd>` and `<current_date>` inside `/system` are in the fingerprint (triage #2,
`fingerprint-unmasked-volatiles`, reproduced live on `main` by the triage), and the same
`classifications == (EvidenceKind.STABLE,)` test silently means "stable AND 3/3" (triage #4,
`verdict-inconsistency`). Today those defects are inert because nothing reads the verdict. Ship the
consumer wiring without the comparator work and they become: **every re-harvest on a different day
or directory exits 1 as breaking drift and `current` never moves again.**

So the ship-now half's value is not independent of the held half. That is the entanglement that
matters, and it is semantic, not textual.

### Cost of executing the split

Rebase and reconstruct 36 commits into two chains; invent an intermediate `baseline_evidence.py`;
regenerate the red/green brackets for the shipping half; run the full gate; take a fresh review
round on a chain no reviewer has seen. That is at least one full correction round of work — the
thing the split was meant to avoid — and it delivers a half whose headline feature is wired to a
comparator with two live confirmed defects.

---

## R3. Options

### Option A — keep the shape, fix the instances

Fix Grok #5 (add the descendant direction to `decided_static_changes`), Opus N6 (strip extras on the
evidence axis), Opus N7 (name the removed pointers in the reason). Leave P3.

- Cost: small, one round.
- Deletes: nothing. Adds a fourth prefix expression in the third direction.
- Risk: the fifth instance. P3 is already sitting there unfiled, and it is reachable by any harness
  that emits a field in one probe out of three.
- Honest read: this is the option that has been taken four times.

### Option B — close the class in place, in the two symbols that already own it

Three edits, all inside `classify_aba` and `compare_baseline_bundles`. **Measured, not proposed:** I
applied these to a scratch copy of the module, ran the branch's own baseline suite and the full API
suite against the patched module by `sys.modules` substitution, and re-ran every probe.

1. **One universe.** Filter `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` where `nodes_by_probe` and
   `leaves_by_probe` are built, so both axes are derived from the same key set as the fingerprint.
   *Removes* the divergence between the two universes; makes N6 unrepresentable rather than fixed.
   (Value **masking** stays on the fingerprint axis only, correctly: the evidence axis compares
   classifications, not digests, which is why a `<cwd>`-only change already returns EXACT and why
   re-deriving the inventory here would re-hash for nothing — triage #10.) Nothing is lost from the
   artifact: `raw_request_base64` still carries the stripped keys verbatim.
2. **One relation.** One private predicate `_covers(ancestor, pointer)` used at all three sites, with
   the adjudication subtraction made symmetric (`_covers(pointer, unresolved) or
   _covers(unresolved, pointer)`). *Removes* three divergent inline prefix expressions and replaces
   them with one named relation; makes Grok #5 unrepresentable.
3. **One predicate.** Delete the `value_evidence == EvidenceKind.STABLE` conjunct from
   `unresolved_presence_changes`, leaving the presence refusal reading the presence axis only.
   *Removes* the hidden coupling that D2 named; closes P3.

Net `+20 / -8` lines in one existing file. No new module, file, type, helper class, adapter, command
or parallel path; one private function replacing three inline expressions. `compare_baseline_bundles`
stays well under 150 lines; the file stays under 700.

Measured result:

```
branch baseline suite (evidence + capture + harvest)   42 passed, 0 failed
full api suite under the patched module                see Verification below
D3 invariant sweep (16 cells, presence x depth x value) 0 violations   (HEAD: 4)
P1 3/3 -> 0/3 and 3/3 -> 2/3 launch identity            exact           (HEAD: breaking / insufficient)
P2 descendant of a flicker with a changed value         insufficient-evidence, unresolved=('/tools/0/cache_control',)
P3 constant field 3/3 -> 1/3                            insufficient-evidence, reference=3/3 candidate=1/3
```

Two things this option must carry, and one honest warning:

- Opus N7 still needs doing (`removed_pointers` prints a reason naming no field). It is not in this
  patch and it is not optional; it is the same class C4 already fixed one round earlier.
- The tests must be written **as the invariant, not the case**: a parameterisation over presence
  ratio × depth × value change, of the shape of `sweep.py`. A case-shaped test is what let three of
  these instances through a green gate.
- **I got this patch wrong twice before it was right**, and both errors were caught by running it,
  not by reading it. First I made `_covers` inclusive at all three sites, which collapsed the
  unresolved set to empty and reported `breaking at ` with an empty pointer. Then I required a
  pointer to be present on **both** bundles before it could be refused, which broke the *addition*
  direction (`0/3 → 2/3`) and failed two of the branch's own tests. Both mistakes are the same
  species as the four this document is about: right in the middle, wrong at the edge. That is
  evidence for the diagnosis and a warning for whoever implements it — this must land red-then-green
  against the sweep, not against three examples.

### Option C — model the disposition explicitly (a dispositioned pointer tree)

Give the comparator a real tree: parent/child links on the observed schema, one disposition per
node, propagation rules, verdict as a fold over the tree.

- What it would delete: the three prefix expressions, the two flat `dict[pointer, ...]` universes,
  the `static_nodes`/`pointer_evidence` split in the artifact.
- What it would cost: `artifact_schema_version` 3, a rewrite of `classify_aba` and
  `compare_baseline_bundles`, and a new production type — the thing the standing constraint forbids.
- **Ruled out on the brief's own terms.** It cannot be delivered incrementally: the artifact shape
  and both symbols change together, so there is no intermediate state with a green gate. And it
  deletes prefix arithmetic that Option B also deletes, at ten times the cost. Option B gets the
  invariant; Option C only gets it *typed*.

---

## R4. Recommendation

**Take Option B, on this branch, in one round, with no split, and add the invariant sweep as the
test.** Then merge the 36 commits as one branch.

Reasoning, in order of weight:

1. **The split loses on both terms.** It costs a full correction round to execute, and the half it
   would ship is the half whose value depends on the half it would hold. Shipping the consumer
   wiring on `main`'s comparator converts two inert confirmed defects (triage #2, #4) into a tool
   that exits 1 on a date change and freezes `current`. Holding the branch entire is strictly safer
   than holding half of it.
2. **The remaining work is smaller than a fourth round, and it is different in kind.** Rounds 1-4
   each closed an instance. Option B is three edits that each delete a conditional and make one
   instance class unrepresentable. It is measured: 42 branch tests green, the 16-cell invariant
   clean, all three live instances resolved, including one nobody had filed.
3. **Every open finding is fail-safe.** All three instances over-refuse or over-break; none promotes
   a bad baseline. Nothing here is a reason to hold the branch as unsafe — it is a reason to close
   the class before the tool goes into daily use, because a drift detector that cries breaking on a
   flickering field will be ignored, and an ignored detector is the same as no detector.
4. **The recurrence stops for a structural reason, not a diligence reason.** After Option B there is
   one relation used three times instead of three relations, one node universe instead of two, and a
   presence rule that does not read the value axis. The symmetric counterpart of each fixed case is
   fixed by construction, which is the only thing that stops a fifth brief producing a fifth
   instance.

Where I disagree with the framing: this was never "four sloppy briefs". It was four correct briefs
against code that can only be described case by case. The fix for that is the invariant test, and
the invariant test is only writable once the invariant exists in the code — which is edits 1-3.

---

## Verification

- Interpreter: `cd api && uv run python` / `uv run pytest` (3.14, repo venv). Ambient `python3` is
  3.13 and was not used for any judgement.
- Branch baseline suite against the patched module: **42 passed**
  (`test_baseline_evidence.py`, `test_baseline_capture.py`, `test_baseline_harvest.py`).
- Full API suite against the patched module: **identical to the control**. Patched:
  `3526 passed, 3 skipped, 298 errors`. Unpatched `10165c99`: `3526 passed, 3 skipped, 298 errors`.
  The 298 errors are pre-existing fixture errors in this shell, present on both sides and unaffected
  by the patch. I ran bare `uv run pytest -q`, not `just check` / `just test`; whoever implements
  this must run the repo recipes
- Nothing was demonstrated against a live harness. No `baseline_harvest --harness claude` run; the
  owner credential is unavailable. Every verdict here rests on unit evidence, as both review files
  also state.
- No repo file was modified. `git status` clean before and after; the patch exists only as
  `patched_evidence.py` in the scratchpad.

### Reproduction artifacts

All in
`/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/992bed90-2f62-4717-bcac-c50f37e345f7/scratchpad/`:

- `probe_axes.py` — P1, P2, P3 against the branch head.
- `patched_evidence.py` — the Option B patch applied to a copy of `baseline_evidence.py`.
- `patchplugin.py` — `sys.modules` substitution, loadable as `pytest -p patchplugin`.
- `probe_patched.py` — the same three probes against the patched module.
- `sweep.py` / `sweep_patched.py` — the 16-cell presence × depth × value invariant sweep, both sides.
