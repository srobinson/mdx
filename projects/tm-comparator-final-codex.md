# Final adversarial review: `fix/comparator-truth`

Reviewed branch `fix/comparator-truth` at
`427720220d6143eda17b26c2650c3d6f48069533`, based on
`5591db86a2c979e3d0f3d314b65d11bdc0bf9778`.

The repository tree was pristine immediately before this verdict. No pull request exists for the
branch. I did not repeat the reported full check, full test, or 21 bracket runs. Focused
reproductions used `cd api && PYTHONDONTWRITEBYTECODE=1 uv run python` and left the repository
pristine.

## Verdict

Conditional. I found 1 Blocker, 3 Major findings, and 3 Minor findings.

## Findings

### 1. Blocker: matching partial carrier sets bypass presence refusal and can promote a changed value

Location: `api/src/transport_matters/baseline_evidence.py:350`

`changed_pointers` compares schema, `value_evidence`, and the coarse `presence` value. It does not
compare the stored value digests. The exact return at line 360 runs before presence refusal, and
presence refusal only considers pointers already in `changed_pointers`.

When reference and candidate carry `/feature` in the same partial probe set, both evidence records
have the same schema and classifications. A changed value carried in A1 and A2 on both sides
returns BREAKING with no unresolved pointer. A changed value carried only in A1 on both sides
returns EXACT with no unresolved pointer. EXACT is promotable through
`baseline_store.promotes_baseline`, so the candidate replaces `current` and the observed value
change disappears from future comparisons.

Focused result:

```text
present in 2/3 on both sides, value one -> two: breaking-drift, promotes false
present in 1/3 on both sides, value one -> two: exact, promotes true
```

The repository invariant says a pointer carried by fewer than all three probes cannot distinguish
optionality from undersampling. Its refusal text requires all three probes on both bundles. The 16
cell sweep at `test_baseline_comparator_invariants.py:92` fixes the reference at 3 of 3 and only
varies candidate presence, so this quadrant is absent. The test is useful and non-tautological,
but its whole input space claim is false.

Caveat: matching partial carrier sets could be treated as settled evidence under a different
contract. That would contradict the current test name, prose, and refusal reason.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_evidence.py#L341-L365

### 2. Major: unrelated partial presence suppresses a demonstrated field removal

Location: `api/src/transport_matters/baseline_evidence.py:415`

The comparator returns a presence refusal before it evaluates `removed_pointers` at line 421.
Static changes receive precedence at line 400, while structural removals outside the static
fingerprint do not.

A reference with prompt derived `/echo` in all probes returns BREAKING when the candidate removes
`/echo`. Add an unrelated `/feature` to one candidate probe and the same comparison returns
INSUFFICIENT for `/feature`; the proven removal vanishes from the verdict. Commit `236ebbf3`
introduced this path by correctly widening presence refusal to 1 of 3 evidence without extending
the existing decided drift precedence to removals.

Focused result:

```text
remove /echo: breaking-drift
remove /echo plus /feature in 1/3: insufficient-evidence, unresolved=/feature
```

Both outcomes prevent promotion, so this fails closed. The operator is still directed to collect
more evidence after the comparator already proved a breaking structural removal.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_evidence.py#L400-L432

### 3. Major: a different controlled prompt plan compares as EXACT

Location: `api/src/transport_matters/baseline_evidence.py:318`

The cell comparison key omits `reference.prompts` and `candidate.prompts`. Prompt derived values
also stay outside the static fingerprint. Two bundles with identical harness coordinates and
different prompt A and prompt B values therefore compare as EXACT when their request structure and
stable nodes match.

Focused result:

```text
reference prompts alpha/bravo, candidate prompts charlie/delta
prompts_equal=false, probe prompt digests all differ, outcome=exact
```

`baseline_harvest` exposes both prompts as command line options and stores one `current` pointer per
harness, provider, and launch model. A run with changed prompt options can therefore compare and
promote across different experiment inputs instead of refusing the mismatched cell.

Caveat: prompt derived bytes are deliberately excluded from the stable fingerprint. I found no
contract that authorizes the controlled prompt plan itself to change across a comparison. The
original acceptance record calls for deterministic prompt A and prompt B.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_evidence.py#L312-L334

### 4. Major: the schema readiness probe escapes its error contract and its timeout

Location: `api/src/transport_matters/session_store_preflight.py:53`

`_reachable_database_url` opens a bounded Psycopg connection and closes it. `check_session_store`
then calls `current_revision`, which opens a second SQLAlchemy connection without the five second
preflight timeout. Exceptions from that connection or the `alembic_version` query are not caught,
despite the `str | None` contract and callers that convert returned text into structured readiness
failures.

A role can pass `SELECT 1` and lack permission on `alembic_version`. A connection can also fail or
stall between the two probes. In those cases launch readiness raises instead of returning a failed
session store check. A focused injected `sqlalchemy.exc.OperationalError` propagated unchanged.

The head equality check correctly closes the observed behind schema failure and reuses the
migration owner's `migration_head` and `current_revision` symbols. The defect is the missing error
and timeout boundary around that reused query.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/session_store_preflight.py#L45-L58

### 5. Minor: the amended migration test no longer covers the immediate predecessor

Location: `api/src/transport_matters/cli/test_launch_preflight.py:164`

The renamed test genuinely pins the surviving no migration claim. It provisions head, downgrades,
expects an error, then proves the revision stayed unchanged. A check that applies migrations would
fail the final assertion.

The consolidation did relax one part of the preceding regression. The deleted
`test_session_store_preflight.py` used `command.downgrade(..., "-1")`, which always exercised the
immediate predecessor of the packaged head. The surviving test downgrades to fixed revision
`0017_wire_delivery_id`, while the current head is `0034_wire_request_divergence`. A future special
case that mistakenly accepts only head minus one would pass this test.

Current production compares exact equality, so this is a coverage regression rather than a live
runtime defect.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/cli/test_launch_preflight.py#L143-L175

### 6. Minor: every schema mismatch is diagnosed as behind

Location: `api/src/transport_matters/session_store_preflight.py:53`

The condition is plain inequality, but the returned message always says the store is behind and
recommends `channel ensure-db`. A database stamped by a newer checkout, a divergent revision, or an
unknown revision receives the same diagnosis. The recommended command cannot move an ahead store
back to this build's head.

The refusal remains safe. The operator receives an incorrect cause and a remediation that cannot
converge.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/session_store_preflight.py#L48-L58

### 7. Minor: removed pointer diagnostics still identify no field

Location: `api/src/transport_matters/baseline_evidence.py:421`

`removed_pointers` is computed and then discarded. The BREAKING reason remains the constant
`demonstrated request fields were removed`, so the CLI tells the operator that removal occurred
without naming the pointer. This is the previously recorded Opus N7 and remains present at the
reviewed head.

The outcome and promotion decision are correct. The diagnostic omits the evidence subject after
the branch made other BREAKING and INSUFFICIENT outcomes actionable.

https://github.com/littleorgans/transport-matters/blob/427720220d6143eda17b26c2650c3d6f48069533/api/src/transport_matters/baseline_evidence.py#L421-L432

## Requested checks

The subtree relation is now owned by one `_covers` predicate. All three comparator tree decisions
use it in the required direction, and repository search found no earlier equivalent helper. The
raw evidence and masked fingerprint still need separate node records because their value digests
differ, but both use the same excluded top level key set. I found no fifth prefix expression or
duplicate key constant.

The invariant sweep fails four 1 of 3 cases on the preceding production code for the intended
reason, because the old refusal required `value_evidence == STABLE`. It is not tautological. Its
reference presence is fixed at 3 of 3, which causes finding 1.

The writability correction reuses existing migration ownership and prevents the real behind schema
failure before capture. Head equality is a necessary schema readiness check. It does not prove
general DML privileges, disk capacity, or every later write, and finding 4 covers the immediate
contract break in the schema query itself.

The new timeout messages correctly distinguish no matched exchange from a matched exchange with no
transcript reply. I found no additional defect in that delta.

Production growth is net 63 lines in the last round and net 245 lines over the branch. The growth
does not add a production file, public type, adapter facade, command, or parallel path. `_covers`
earns its nine lines by replacing three independent subtree expressions. The nested identity
filter prevents duplicate node and leaf rules. Files remain below 700 lines and functions remain
below 150 lines. I found no unearned abstraction in the production growth.
