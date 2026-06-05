---
title: Final review of fix/comparator-truth at bf9b2630
type: projects
tags: [transport-matters, baseline-capture, comparator, review]
summary: Delta verification of eleven commits after 42772022; sixth instance is 3/3 UNKNOWN maskable drift refused while fingerprints match
status: active
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

# Delta verification: `fix/comparator-truth` @ `bf9b2630`

Reviewer: Grok. Delta only, from prior review head `427720220d6143eda17b26c2650c3d6f48069533` to `bf9b26307dcf393ad3950689eab5045868401ca9`. `5591db86` and `42772022` are ancestors. Tree empty before the read and again before this verdict. No repo write. Interpreter `cd api && uv run python` (3.14). I did not rerun `just check` / `just test` / the 26 brackets.

**Verdict: 1 Major, 1 Minor.** Both of my findings at `42772022` are closed. The Blocker is closed in both directions. The 96-cell table is internally consistent for the cells it builds. The sixth instance is a regression in the new UNKNOWN digest clause: three launches whose only disagreement is a maskable Run ID, cwd, or date are UNKNOWN on the evidence axis and STABLE on the fingerprint, so compare now returns INSUFFICIENT while the fingerprints match. A 2/3 kind change is the other cell the product cannot name. The schema probe bound is two of the four launch-gate socket limits.

The original review at `42772022` follows the delta section.

---

## Delta findings

### 1. Major. Sixth instance: the UNKNOWN digest clause compares the unmasked universe

**Location:** `api/src/transport_matters/baseline_evidence.py:360-368` (UNKNOWN vs UNKNOWN `value_sha256_by_probe`). Evidence digests are raw (`:242-247`, `:523`). `static_nodes` are masked (`:256-300`). The lock that cannot see the cell is `test_baseline_comparator_invariants.py:118` (one scalar value per bundle, so 3/3 is always STABLE) and `test_baseline_evidence.py:397` (`test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking`, STABLE 3/3 only).

**Observation:** A controlled harvest is three launches. A system string that carries Run ID, cwd, or date is a different raw digest on each probe and one masked digest on the fingerprint. `_classify_pointer` therefore marks it UNKNOWN + always. `classify_aba` still puts it in `static_nodes` because the masked hashes agree. The new clause fires whenever those raw maps differ across harvests. `changed_pointers` becomes nonempty, the EXACT short circuit fails, presence is `always` so `_presence_refusal` does not run, the candidate is still UNKNOWN so COMPATIBLE does not run, and compare returns INSUFFICIENT `"changed request evidence is not classified strongly enough"`. The fingerprints are equal.

Measured through the live comparator:

```
3/3 same raw cwd within harvest, different cwd across
  outcome=exact promote=True  fp_equal=True  evidence=stable

3/3 A1=A2!=B cwd vs a different pair
  outcome=insufficient-evidence promote=False  fp_equal=True
  reasons=('changed request evidence is not classified strongly enough',)
  evidence=unknown always  n_digests=2  static=['/note', '/static']

3/3 three distinct Run ID lines vs three others
  outcome=insufficient-evidence promote=False  fp_equal=True
  evidence=unknown always  n_digests=3

3/3 UNKNOWN identical mixed pair on both harvests
  outcome=exact promote=True
```

The same INSUFFICIENT result holds for intra-harvest date disagreement. Before `0c7a6a70` the pair `(UNKNOWN, always)` matched, fingerprints matched, and this cell was EXACT.

The other cell the product cannot name, same split. Matching 2/3 carriers, both STABLE, both in `static_nodes`: number `1` vs `2` is BREAKING via the fingerprint. `string` vs `number` enters `changed_pointers` through schema inequality, then `_presence_refusal` swallows the fingerprint hit. Presence did not change. Reason text claims it did. Executed in `/tmp/tm-final-grok/probe_kinds.py`.

**Impact:** A rerun whose only request drift is launch-scoped identity, the thing `mask_cross_launch_body` exists to ignore, no longer promotes. The operator is told the evidence is too weak. The next harvest compares against the old `current` forever. The fifth instance was the raw universe dropping a digest the operator needed. This fix reads that universe for every UNKNOWN leaf and undoes the mask on the live 3/3 shape. The 96-cell sweep cannot form it: one value per bundle makes 3/3 STABLE, which is the slice `test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking` already pins.

**Basis:** Executed at HEAD `bf9b2630` with `cd api && uv run python /tmp/tm-final-grok/probe_mask_unknown.py`. Mask patterns are `wire_normalization.py:221-246`. Repo date/cwd exactness test is STABLE-only (`test_baseline_evidence.py:397-422`).

**Caveat:** Fail-closed. If the raw disagreement is not a mask target, INSUFFICIENT is the intended UNKNOWN-always outcome. 1/3 maskable drift is the same clause and also refuse; that shape is rarer than three distinct launches. I am not asking for a rewrite of the comparator. The clause needs to compare masked leaf digests, or ignore UNKNOWN leaves that are in `static_nodes` on both sides.

https://github.com/littleorgans/transport-matters/blob/bf9b26307dcf393ad3950689eab5045868401ca9/api/src/transport_matters/baseline_evidence.py#L355-L375

https://github.com/littleorgans/transport-matters/blob/bf9b26307dcf393ad3950689eab5045868401ca9/api/src/transport_matters/test_baseline_evidence.py#L397-L422

---

### 2. Minor. The schema probe bound omits the launch-gate socket limits

**Location:** `api/src/transport_matters/session/migrate.py:63-71` (`current_revision` `connect_args`), called from `session_store_preflight.py:55`.

**Observation:** F4 was an unbounded second connection after `_reachable_database_url`. This round adds `timeout=5` and catches `SQLAlchemyError`. `create_engine` receives `connect_timeout` and `statement_timeout` only. `session/pool.py:connect` already documents that a launch path which must not stall passes four bounds: connect timeout, statement timeout, keepalives, and `tcp_user_timeout`. The compatibility gate does (`harnesses/launch_gate_connection.py`). The new test asserts `timeout == 5` and never reads the socket args.

**Impact:** A handshake or a running `alembic_version` query now dies at 5s. A socket that accepts and then goes dark does not: `statement_timeout` never starts, and there is no keepalive or user timeout. That is the hang F4 named, one layer later. Capture still sits in `check_session_store` until the kernel drops the TCP session.

**Basis:** New in `abdba73c`. `pool.connect` already owns the four-bound recipe. `MigrationContext` needs a SQLAlchemy connection, so the reuse is `current_revision` plus the same `connect_args` the gate already knows. They reused the symbol and reimplemented a thinner bound inside it.

**Caveat:** Permission errors and a slow query are now structured failures, which F4 also asked for. `apply_migrations` still calls `current_revision` unbounded; that path is older.

https://github.com/littleorgans/transport-matters/blob/bf9b26307dcf393ad3950689eab5045868401ca9/api/src/transport_matters/session/migrate.py#L63-L77

---

## Requested checks

### 1. Prior findings

**Major (1/3 vs 1/3 value change EXACT, promotes).** Closed. `changed_pointers` now includes UNKNOWN vs UNKNOWN digest inequality when the pointer has no descendants (`baseline_evidence.py:360-368`). Leaf, nested, and container:

| cell | outcome | promote |
| --- | --- | --- |
| 1/3 vs 1/3 same value | EXACT | true |
| 1/3 vs 1/3 value changed | INSUFFICIENT | false |

Container changed reports `/feature/value`. Nested reports `/outer/inner/feature`.

**Minor (request without `response_ir` reported as no exchange).** Closed. `_wait_for_correlated_exchange` keeps `matched_requests` on request IR plus delivery match, and `candidates` only when `response_ir` exists (`baseline_capture.py:277-315`, `:341-345`). `test_correlation_timeout_names_matched_request_without_response` pins the third message. Production `read_captured_exchange` does not require `response_ir`.

### 2. Sweep semantics

`_expected_presence_outcome` matches live `compare_baseline_bundles` on all 96 constructed cells (recomputed, 0 mismatches). The table was written in `aef3e384` before the UNKNOWN digest fix, with 1-vs-1 changed already INSUFFICIENT, so it encodes the desired rule rather than then-current EXACT. `0c7a6a70` only added the container leaf pointer assertion.

No constructed cell asserts a wrong outcome for the body it builds. 0-vs-0 `value_changed=True` is EXACT because the field is absent on both sides. 2-vs-0 is INSUFFICIENT; that matches the presence rule, and 2-vs-2 value BREAKING remains the settled fingerprint exception.

Missing dimensions the product cannot express:

- **intra-bundle raw agreement on a maskable string.** Finding 1. One value per bundle forces 3/3 STABLE, which stays EXACT. Three launches with distinct Run IDs are UNKNOWN always and now refuse.
- **kinds / schema.** Same split. 2/3 `1` vs `2` is BREAKING; 2/3 `string` vs `number` is INSUFFICIENT.
- **carrier identity.** `_carriers(2)` is always A1+A2, `_carriers(1)` is always A1. 1/3 A1 vs 1/3 B, same value, is INSUFFICIENT. The docstring already says "matching partial carrier set."

### 3. Sixth instance

Finding 1. I did not find a remaining EXACT promote of an unmasked request-field value change. I did find a missing EXACT: maskable-only UNKNOWN 3/3, which was EXACT before `0c7a6a70`.

### 4. New in these eleven commits

Removal now requires `presence == "always"` and runs before presence refusal (`:426-438`). `test_proven_removal_precedes_unrelated_refusal_and_names_pointer` holds; the reason names `/prompt`. Prompt plans sit in the cell key (`:324-336`); mismatched plans refuse and do not promote. `check_session_store` passes `timeout=5` into `current_revision`, catches `SQLAlchemyError`, and no longer calls every mismatch "behind". The behind-head test downgrades `-1` and pins the revision it actually left. The bound itself is finding 2. Identity presence 3/2/1/0 stays EXACT. Sibling `/core` 3/3 value change beside a 3-to-1 flicker stays BREAKING. The 1/3 value-change path also emits the presence-refusal reason even though presence did not change; outcome is the intended INSUFFICIENT, so I am not scoring that separately from finding 1's mechanism.

`compare_baseline_bundles` is 147 lines. `baseline_evidence.py` is 617. No new production file.

### 5. Blocker, both directions

Confirmed at leaf, nested, and container. Unchanged matching 1/3 is EXACT and promotes. Changed matching 1/3 is INSUFFICIENT and does not.

### Settled, not re-raised

Presence INSUFFICIENT semantics. Presence-independent fingerprint membership for matching 2/3 value. Schema v2 hard v1 rejection. U6 transcript gap. Sign-off still does not cover an end-to-end harvest.

---

# Prior review: `fix/comparator-truth` @ `42772022`

Reviewer: Grok. Independent of the other final-round reviewer. Baseline `main` `5591db86`. Head `427720220d6143eda17b26c2650c3d6f48069533`. Last-round window is the eleven commits after `10165c99`. Tree verified empty (`git status --porcelain`) before the read and again before this verdict. `5591db86` and `10165c99` are both ancestors. No repo write. The only write is this file. Interpreter `cd api && uv run python` (3.14). I did not rerun `just check` / `just test`; the orchestrator already reported those green.

**Verdict at 42772022: 1 Major, 1 Minor.** Closed at `bf9b2630`. Kept below as the artifact that round produced.

---

## Findings

### 1. Major. Fifth instance: a 1/3 vs 1/3 value change is EXACT and promotes

**Location:** `api/src/transport_matters/baseline_evidence.py:360` (`EXACT` short circuit), `:342` (`changed_pointers`), `:289` (`static_nodes` needs two carrying probes). The lock that missed the cell is `api/src/transport_matters/test_baseline_comparator_invariants.py:92` (reference always `present=3`).

**Observation:** Option B collapsed extras-key membership and the three prefix expressions. It left value comparison on the fingerprint universe only. `changed_pointers` compares schema and the `(value_evidence, presence)` pair. It never reads `value_sha256_by_probe`. `static_nodes` requires `len(masked_nodes) >= 2` and one digest. A pointer carried by one probe of three is in `pointer_evidence` as `UNKNOWN` + `sometimes` and is absent from `static_nodes`. When both harvests show that same `present_in` set and the observed digest moves, `changed_pointers` is empty, the fingerprints match on `/static` alone, and compare returns EXACT.

Measured with the repo helpers (`_probe` / `_bundle`) through the live comparator:

```
ref 1/3 A1 feature="one"  sha256=49e9fcfb…
cand 1/3 A1 feature="two" sha256=b85d38dc…
  outcome    = exact
  reasons    = ('observed schema and stable baseline fingerprint match',)
  unresolved = ()
  static     = ['/static'] on both sides
  fp equal   = True
```

The same cell at nested `/outer/inner/feature` is also EXACT. The 2/3 vs 2/3 value change is BREAKING, because that pointer is in `static_nodes` on both sides. That matches the settled presence-independent membership rule. The 1-probe column has no such backstop.

`_repeat_a_outcome` already compares A1 vs A2 digests inside one bundle (`baseline_evidence.py:596`). The inter-bundle compare has no counterpart.

The 16-cell sweep never asks this question. Every cell builds the reference at `present=3`. Reintroducing `value_evidence == STABLE` on the presence gate would fail the 1/3 column of that sweep. A compare that returns EXACT for 1/3 vs 1/3 with disagreeing hashes would stay green.

**Impact:** The operator reruns a cell whose optional field appeared on A1 only, with a new value. Harvest prints `outcome=exact`, exits 0, and `promotes_baseline` moves `current` (`baseline_store.py:53-57`). The next harvest has nothing to compare against. The artifact's claim that schema and the stable fingerprint match is true of those two fields and false of the request: `/feature` changed, the hashes are in the bundle, and nothing read them.

This is the same shape as the four earlier instances. An exclusion (fingerprint membership, `>= 2`) applied to one universe leaves the other armed, and the case-shaped lock pins the slice they just fixed.

**Basis:** Executed through `cd api && uv run python` against HEAD `classify_aba` / `compare_baseline_bundles`. Digests quoted above are from that run. Intra-bundle digest compare is `_repeat_a_outcome` only. `rg value_sha256_by_probe` in production has those two sites.

**Caveat:** The hole is older than this round. The EXACT short circuit and the digest-blind `changed_pointers` already existed at `10165c99`. This round claimed the class is now structurally impossible. The 1/3 column was the last presence-gate miss (P3). They closed presence-ratio 3/3 → 1/3 and left value-change 1/3 → 1/3. A field that is stably 1/3 with the same `present_in` on both harvests is narrower than the earlier extras and flicker cases. The unsafe direction is new relative to those: the earlier leftovers over-broke. This one promotes.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_evidence.py#L341-L364

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/test_baseline_comparator_invariants.py#L91-L114

---

### 2. Minor. The timeout split still reports a matched request without `response_ir` as "no captured exchange"

**Location:** `api/src/transport_matters/baseline_capture.py:294` and `:341`

**Observation:** The last-round wait loop keeps the last `candidates` list and splits the timeout into "matched N, no transcript reply" vs "no captured exchange resolves." Membership in `candidates` requires `request_raw`, `request_ir`, and `response_ir`. `read_captured_exchange` can classify a delivery from the request half alone (`certification_run_reader.py:177-179`; `response_raw` is optional). An index entry whose request files exist and match the delivery, and whose `response.ir.json` never appears, is `continue`d and never enters `candidates`. After the deadline the loop raises the unmatched message.

The new test pins `owned_exchange=False` and `transcript_reply=False` (`test_baseline_capture.py:468-480`). It does not pin request-matched / response-absent.

**Impact:** A probe that wrote the owned request and then stalled on the response still spends the timeout, then tells the operator nothing arrived. They debug launch, proxy, or store. The request that matched the delivery is already on disk. This is the same "one message, two causes" defect the live harvest hit, one artifact later.

**Basis:** Last-round comment at `:333` names two causes. `read_captured_exchange` does not require `response_ir`. The wait loop does, before the delivery test.

**Caveat:** The live miss this round fixed (matched delivery, no transcript) is now named, and that is the expensive path they actually hit. A recorder that only indexes an exchange once `response_ir` exists would make this state rare. Still a third condition the loop can see and then forget.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_capture.py#L293-L343

---

## Key checks

### 1. The class claim

Three of the four Option B claims hold as written.

- **One relation.** `_covers` is the only prefix test in `classify_aba` and `compare_baseline_bundles`. Collapse, bidirectional static exclusion, deepest `changed_at`, and identity membership all call it. `/tools/1` is not an ancestor of `/tools/10`.
- **One extras-key set.** `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` is the single source. Evidence drops those subtrees with `_covers`. Fingerprint `pop`s the same keys after `mask_cross_launch_body`. Identity presence 3/3, 2/3, 1/3, 0/3, including `client_metadata` as an object, is EXACT on HEAD. Two node maps remain (`nodes_by_probe` vs `masked_nodes_by_probe`) so date and cwd masking can stay on the fingerprint axis. That split is the settled mask, not a live extras leak.
- **Presence gate.** `unresolved_presence_changes` reads `presence == "sometimes"` only. 3/3 → 1/3 and 3/3 → 2/3 refuse at both depths, value same or changed.

The remaining join is finding 1. Value deltas of non-static pointers have no inter-bundle predicate. Closing extras membership and the STABLE conjunct does not make a fifth instance unrepresentable.

Probed and matching the stated rule, so not filed: 2/3 → 2/3 value BREAKING (fingerprint membership); 2/3 vs 2/3 on different probe sets INSUFFICIENT; sibling `/core` change beside a flicker BREAKING at `/core`; 0/3 → 3/3 BREAKING; 0/3 → 1/3 and 0/3 → 2/3 INSUFFICIENT; identity appear and disappear EXACT.

### 2. The amended test

Honest, and stronger than the parent.

At `10165c99`, `test_capture_reachability_check_does_not_run_migrations` downgraded to `0017_wire_delivery_id`, asserted `check_session_store() is None`, and asserted the revision was still `0017`. The `None` half was the live lie.

HEAD `test_capture_store_check_refuses_a_behind_head_store_without_migrating` (`cli/test_launch_preflight.py:143`) still pins the revision at `0017` after the check. It adds an at-head `None` before the downgrade, and asserts the error names `EXPECTED_MIGRATION_HEAD_REVISION`. Restoring `check_session_store` to reachability only would fail `assert error is not None` first. The launch neighbour still migrates (`test_launch_preflight_migrates_before_process_start`). Harvest still calls this function first (`baseline_capture.py:174`). The deleted mid-round `test_session_store_preflight.py` was a second home for the same fact; folding it here removed that parallel.

`058a6bf4` inverted the old assertion and left that assertion in the tree until `42772022`. HEAD is consistent. I am not scoring the three-commit gap as a defect on the branch as filed.

### 3. The writability preflight

Proves what the live run needed. No new production symbol.

`check_session_store` now compares `current_revision(database_url)` to `migration_head()` and returns a string that names the head and `channel ensure-db`. Those two helpers already exist in `session/migrate.py`. `apply_migrations` uses the same equality as its no-op. Capture must not call `apply_migrations`; extracting a third wrapper would have violated the standing no-new-helper rule. Reusing the primitives is the right shape.

The docstring says the function proves the store can accept this build's writes. The body never writes. A role that can `SELECT 1` and read `alembic_version` and cannot `INSERT` into `wire_exchange` still returns `None`. Any `current != head`, including `None` and a store ahead of the packaged scripts, is reported as "behind {head}". Diagnose already splits uninitialised from behind. For the billed harvest (reachable, one revision stale) the new check would have stopped the run and named the fix. I am not scoring the read-only-role hole; a write probe would be a new contract.

### 4. The invariant test

Not tautological. Incomplete as a class lock.

`test_presence_decides_only_when_every_probe_agrees` drives real bundles through `classify_aba` and `compare_baseline_bundles`. Expected outcomes are a table: 3/3 is the value axis, 0/3 is BREAKING, 1/3 and 2/3 are INSUFFICIENT. At `10165c99` the presence gate still required `STABLE`, so the 1/3 column (four cells: top and nested, same and changed value) would fail by becoming BREAKING. Reintroducing that conjunct would fail the same four cells. `_carriers(2)` is always A1+A2 and `_carriers(1)` is always A1; that compression still hits the count-based STABLE leak.

The module claims to pin the rule over every ratio. The reference is always 3/3. Finding 1 lives in the untested half of that grid.

`test_nothing_inside_a_flickering_subtree_is_decided` is a real subtree lock (unchanged, value-changed, and added descendant). `test_launch_identity_presence_never_reaches_the_verdict` pins extras presence 3/2/1/0. Those two hold.

### 5. Net growth

The disclosed `+77 / -14` production delta is real. `_covers` plus its docstring replace three inline prefix expressions and serve a fourth call site (identity). That helper earns its place. The rest of the last-round production growth is the identity filter, the schema compare, the timeout split, and comments that restate the last bugs. No new production file, type, adapter, command, or parallel path. `baseline_evidence.py` is 604 lines. `compare_baseline_bundles` is 135. The new test module exists because `test_baseline_evidence.py` is at 689. It imports `_bundle` / `_probe` rather than restating them.

Growth did not close finding 1. The missing predicate is a read of `value_sha256_by_probe` on the EXACT path, not another abstraction.

### 6. Last eleven commits as suspect code

The three Option B pairs compose on the cases they name. Identity never reaches either axis. A `sometimes` presence-ratio change refuses before `removed_pointers`. A refused pointer takes ancestors and descendants out of decided static together.

The timeout pair introduced finding 2. The schema pair is the one last-round production change I would ship as is.

Opus N7 (`removed_pointers` reason names no field) is unchanged. This round only kept identity keys out of that set. It is a reporting gap, not a fifth instance of the two-universe class, and I am not re-raising it.

### 7. Settled, not re-raised

Presence INSUFFICIENT semantics. Presence-independent fingerprint membership (this is why 2/3 → 2/3 value BREAKING is correct). Artifact schema version 2 with hard version 1 rejection. U6 transcript gap under Claude Code 2.1.234.

---

## Reproduction

Scratch only, no repo file touched:

- `/tmp/tm-final-grok/probe_class.py` — full reference-presence × candidate-presence × value matrix, nested copy, identity 2/3, sibling+flicker, 2/3 on different probe sets.
- `/tmp/tm-final-grok/probe_more.py` — `client_metadata` object presence transitions, and the 1/3 vs 1/3 hashes quoted in finding 1.
- `/tmp/tm-final-grok/baseline_evidence_10165c99.py` — parent module, used to read the old STABLE conjunct. Loading it as a pydantic module failed on an undefined `JsonPointer` forward ref; the 1/3 pre-fix failure is from that conjunct plus the reassessment's 16-cell count at `10165c99` (4 violations, the 1/3 column).

```
cd api && uv run python /tmp/tm-final-grok/probe_class.py
cd api && uv run python /tmp/tm-final-grok/probe_more.py
```

Delta probes (HEAD `bf9b2630`):

```
cd api && uv run python /tmp/tm-final-grok/probe_delta.py
cd api && uv run python /tmp/tm-final-grok/probe_more_delta.py
cd api && uv run python /tmp/tm-final-grok/probe_kinds.py
cd api && uv run python /tmp/tm-final-grok/probe_mask_unknown.py
```

---

## Sign-off

At `bf9b2630`: `review: issue 1 Major 1 Minor api/src/transport_matters/baseline_evidence.py`

At `42772022` (closed): `review: issue 1 Major 1 Minor api/src/transport_matters/baseline_evidence.py`
