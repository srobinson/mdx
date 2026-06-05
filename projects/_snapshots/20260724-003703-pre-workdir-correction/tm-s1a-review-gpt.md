# S1a review: concurrency, state, probes, and trust

Reviewed range:
`d7bfb9acbbb2bc193541fd8a18c2db73d07079b8..bcb36c9c029756ecf294a00d1378294b4d49b0a8`

Scope: S1a Python persistence sink. This review was read only. No tests,
builds, migrations, type checks, or repository gates ran.

## Verdict

**Blockers: 0. Majors: 1. Minors: 1.**

The database write once design is sound. PostgreSQL row conflict
serialization, the shared `canvas_id` predicate, input validation, and the
backfill update guard prevent snapshot mixing in every requested schedule.

The slice does not clear review because the new ingest helper reads undeclared
attributes that arbitrary flat `launchFields` can install on a
`SessionBinding`. A caller controlled Canvas snapshot can therefore cross the
new immutable sink when the binding also carries valid Space and Worktree
identity. The reserved nested carrier scrub tested by this change does not
protect that flat path.

## Findings

### Major 1: flat caller launch fields can become an immutable affinity stamp

Location:
[`session/ingest.py:101`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/session/ingest.py#L101-L107)

Supporting path:

- [`capture_rpc_routes.py:134`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/api/v1/capture_rpc_routes.py#L134-L178)
  accepts an arbitrary `launchFields` mapping and carries it unchanged into
  `CapturedRunRequest`.
- [`addon_runtime.py:336`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/addon_runtime.py#L336-L343)
  expands the mapping into `SessionBinding.model_copy(update=...)`.
- `SessionBinding` does not declare the six new Canvas and snapshot fields.
  Pydantic `model_copy(update=...)` nevertheless stores unknown update keys on
  the copied model without validation.
- The changed `_binding_affinity()` uses `getattr()` for all eight affinity
  names. It therefore consumes those undeclared caller supplied attributes,
  validates the resulting full group, and sends it to the upsert.

An isolated read only probe against the actual functions demonstrated the
crossing:

```text
unknown_canvas_attr 00000000-0000-4000-8000-000000000003
persistable_affinity {
  'space_id': '00000000-0000-4000-8000-000000000001',
  'worktree_id': '00000000-0000-4000-8000-000000000002',
  'canvas_id': '00000000-0000-4000-8000-000000000003',
  'parent_canvas_id': None,
  'canvas_name': 'forged name',
  'canvas_path': '[{"canvasId":"forged","name":"forged","kind":"user"}]',
  'worktree_path': '/forged/path',
  'worktree_branch_name': 'forged/branch'
}
```

Concrete impact: a capture caller can supply flat `canvas_id`,
`parent_canvas_id`, `canvas_name`, `canvas_path`, `worktree_path`, and
`worktree_branch_name` keys. When the binding has valid trusted `space_id` and
`worktree_id`, the first session upsert stores the forged snapshot. The write
once rule then prevents a later trusted ingest or reingest from repairing the
tombstone.

This violates the confirmed S1 trust contract:

- Caller supplied names, paths, branches, and snapshot fields are ignored.
- The trusted carrier is injected after caller launch field merges.
- Affinity fields reach `SessionBinding` only from validated `RunContext`.

Caveat: the current dedicated `build_proxy_run_binding()` still leaves Space
and Worktree identity null, so that path rejects a forged full group today.
The shared proxy binding shape already supports the two trusted identifiers,
and the next S1 threading slice is intended to populate them. S1a has created
the persistent trust crossing before that threading lands.

Recommended correction:

1. Read affinity only from declared, validated binding fields. A
   `model_dump()` based source naturally excludes undeclared
   `model_copy(update=...)` extras.
2. Exclude every flat affinity field, plus the reserved nested carrier, from
   the arbitrary launch field overlay.
3. Decode the reserved carrier only after server resolution has replaced any
   caller value.
4. Add a regression that starts from raw `PrepareCaptureRequest.launchFields`
   and proves flat and nested forgeries cannot reach `session_params`.

The same boundary currently erases a partial group when `canvas_id` is absent,
because `_binding_affinity()` returns eight nulls before calling the validator.
That is part of the same root cause. Existing Space and Worktree only bindings
must remain eligible for backfill, while any declared new snapshot field should
force complete group validation.

### Minor 1: a guarded backfill no op is reported as resolved

Locations:
[`session/backfill.py:146`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/session/backfill.py#L146-L161)
and
[`session/async_dao.py:198`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/session/async_dao.py#L198-L228)

`update_session_space_identity()` discards the update row count. Its caller
increments `resolved_count`, `resolved_in_batch`, and possibly `missing_count`
without knowing whether `AND canvas_id IS NULL` matched.

Schedule:

1. Two backfill passes select the same unstamped session.
2. Pass A commits its complete stamp.
3. Pass B waits on the row, then PostgreSQL rechecks its predicate against the
   committed row.
4. Pass B updates zero rows but reports `resolved=1`.

A live full upsert winning between backfill selection and update produces the
same false feedback.

Impact: startup logs can double count resolved or missing sessions and claim
durable progress by a pass that wrote nothing. Stored data remains atomic and
write once. These counters currently feed logging only.

Recommended correction: return whether the guarded update affected a row and
increment the success counters only when it did.

## Requested pressure tests

### Concurrent first writers with different full snapshots

**Holds. Exactly one complete snapshot wins.**

The conflict target is one `session_id`. PostgreSQL serializes conflicting
`INSERT ... ON CONFLICT DO UPDATE` operations. After the first full writer
commits, the second writer evaluates every affinity assignment against the
committed row.

All eight assignments use the same predicate at
[`session_statements.py:70`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/session/session_statements.py#L70-L116):

```sql
"session".canvas_id IS NULL AND EXCLUDED.canvas_id IS NOT NULL
```

The first full writer changes all eight fields. The second sees stored
`canvas_id` present and takes all eight stored branches. If the first
transaction aborts, the other insert wins. No schedule permits column level
interleaving or a mixed group.

### Legacy partial row replacement

**Holds and matches the confirmed semantics.**

For a legacy row with `space_id` and `worktree_id` present but `canvas_id`
null, a validated full incoming snapshot makes the shared predicate true.
Every affinity assignment takes `EXCLUDED`, including Space and Worktree.
Neither legacy value survives. This prevents a legacy fragment from mixing
with a new Canvas snapshot.

The replacement can clobber a different legacy Space or Worktree value, but
that is intentional. The legacy pair was not a complete frozen snapshot. The
new full group is the first authoritative stamp.

### `validate_affinity_group` boundary

**The actual function behaves correctly for the requested cases.**

An isolated function probe produced:

```text
canvas set, canvas_name null: reject ValueError
canvas null, canvas_name set: reject ValueError
all null: accept None
```

The six required fields are enforced. `parent_canvas_id` and
`worktree_branch_name` remain legitimately nullable.

For mapping inputs, omission of either nullable field is interpreted as null.
That matches the current Pydantic defaults, and the trusted serializer emits
both fields explicitly. If wire presence must be distinguished from observed
null later, that carrier contract needs a separate presence check.

### Backfill selection and update races

**Stored data holds. Feedback has the minor defect above.**

The update at
[`session_statements.py:204`](https://github.com/littleorgans/transport-matters/blob/bcb36c9c029756ecf294a00d1378294b4d49b0a8/api/src/transport_matters/session/session_statements.py#L204-L218)
writes all eight fields in one statement and retains `AND canvas_id IS NULL`.
PostgreSQL rechecks the condition after a row lock wait.

- Two backfill passes: the first applied update wins, and the second changes no
  row.
- Backfill before live upsert: the live conflict path sees a present
  `canvas_id` and preserves the backfill group.
- Live upsert before backfill: the guarded backfill changes no row.

No schedule double writes or mixes stored values.

### Present snapshot with null branch

**Holds.**

Presence is determined only by stored `canvas_id`. A stored null
`worktree_branch_name` therefore takes the stored branch of the same shared
predicate. Later reingest with a nonnull branch cannot fill or flip it.

### STEP 0 SQL extraction

**Holds.**

`session_statements.py` owns each extracted session SQL constant once.
`dao_statements.py` explicitly reexports those names as the compatibility
facade. `async_dao.py` and `controlplane_statements.py` consume the focused
module directly. Repository search found no stale production session insert,
update, or duplicate constant.

Current relevant sizes:

| File | Lines |
| --- | ---: |
| `session/affinity.py` | 100 |
| `session/session_statements.py` | 284 |
| `session/dao_statements.py` | 507 |
| `session/writer.py` | 682 |

The extraction respects the repository thresholds and avoids a second SQL
authority.

## Test rigor and base authenticity

The final tests are strong for sequential write once behavior, legacy partial
replacement, hard delete tombstones, ordinary backfill, migration shape, and
database end state.

Base analysis:

- The modified foundation partial group test, ingest identity test, shared
  proxy database test, and migration test are genuine behavioral or schema
  failures at `d7bfb9ac`.
- The new affinity suite and `session.affinity` module land in the same commit.
  At base the suite fails collection because the module is absent. Base SQL
  makes the individual behavioral failures inferable, but repository history
  cannot prove red first execution or sequencing.
- All production and tests landed in one commit. Local red first work may have
  happened, but git history cannot establish it.

The missing adversarial regressions are material to delegation confidence:

1. Two connections racing different first full snapshots.
2. A stored full snapshot with null branch followed by a nonnull branch.
3. Backfill paused after selection while a live upsert wins.
4. Raw flat and nested `launchFields` forgery through the real binding boundary.

The current SQL proves the first three data invariants. The fourth exposes the
major trust defect.

## Builder trust

**CONDITIONAL.**

Craftsmanship is strong in the database core. The single sentinel design is
simple and correct, the migration is exact, the extraction is clean, the
backfill reuses authoritative Canvas and Worktree projections, and the main
tests observe persisted outcomes.

Expanded delegation should remain bounded for now. The implementation missed
an explicitly important ingress trust boundary, and its forgery test exercises
the unused nested scrub helper rather than the live flat `launchFields`
overlay. Concurrency and nullable sentinel regressions are also absent even
though the static implementation is correct.

This is a strong storage implementation with one consequential cross boundary
miss. Fix the trust path and add the hostile ingress regression before using
this slice as evidence for unsupervised large delegation.

## Final state

Reviewed HEAD:
`bcb36c9c029756ecf294a00d1378294b4d49b0a8`

The tracked repository was clean at review start. No repository gates ran.
