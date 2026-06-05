# Space CRUD review: `e116ffb6`

Reviewed range: `6453364a..e116ffb6`

Verdict: 0 blockers, 0 majors, 6 minors. Builder trust: **trust**.

The implementation follows the locked Space model and the Section 3 through 9 contract. Store,
service, REST, MCP, and `@tm/core` use the intended shared authorities. The remaining findings are
bounded edge, concurrency, and proof gaps. None undermines the core Space CRUD design.

## Findings

### Minor 1: the typed client cannot consume the Space pagination cursor

Location: `www/packages/core/src/spaceTransport.ts:67`

`SpaceListResponse` exposes `nextCursor`, but `fetchSpaces()` accepts no cursor or limit and always
requests `/v1/spaces`. Named Space creation is unbounded while the REST endpoint defaults to 50
items. After 50 named Spaces plus the default, at least one durable Space is unavailable through
the typed inventory fetcher even though the server returns a continuation cursor.

Impact: a public mutation can produce state that the public typed read path cannot fully enumerate.
The newest created Space remains visible because the server sorts by `updated_at`, but an older
Space falls off the only page the client can request.

Basis: producer to consumer feedback loop and the Section 6 requirement that mutation callers
reconcile through `fetchSpaces`.

Caveat: pagination and `fetchSpaces()` predate this commit. A caller can use the generic request
helper or REST endpoint directly.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/www/packages/core/src/spaceTransport.ts#L61-L72

### Minor 2: one Space list response can mix two committed database states

Location: `api/src/transport_matters/api/v1/space_routes.py:262`

`list_spaces()` reads inventories, performs filesystem projection, then runs `count_spaces()` as a
second SQL statement. PostgreSQL `READ COMMITTED` gives those statements separate snapshots. A
concurrent create can produce default only `items` with `showSwitcher=true`; a concurrent delete can
produce the inverse.

Impact: the switcher can transiently disagree with the inventory returned in the same response.

Basis: create and delete are now first class concurrent producers, and projection widens the race
window between the two reads.

Caveat: the split read existed at the baseline. A later refetch converges.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/api/src/transport_matters/api/v1/space_routes.py#L253-L275

### Minor 3: `validate_display_name` accepts PostgreSQL's forbidden NUL byte

Location: `api/src/transport_matters/space/models.py:28`

Input such as `"A\u0000B"` passes trimming, nonempty, surrogate, and length validation. A focused
database probe then raised:

```text
psycopg.DataError
sqlstate=None
PostgreSQL text fields cannot contain NUL (0x00) bytes
```

Impact: REST Space create or rename escapes the typed `invalid_request` contract as an unhandled
server error. MCP catches the same exception as generic `space_crud_failed`, so the two surfaces also
lose error parity.

Basis: Space name validation is a Section 4 deliverable. Reject U+0000 in the shared validator and
cover create and rename red first.

Caveat: this finding is specific to embedded U+0000. The probe did not implicate other control
characters or Unicode separators. The shared Canvas validator inherited the same behavior.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/api/src/transport_matters/space/models.py#L27-L39

### Minor 4: UUID failure wording has two authorities

Location: `api/src/transport_matters/api/v1/space_mcp.py:338`

MCP `_crud_id` synthesizes `invalid_request` messages independently from REST `_parse_space_id`,
`_parse_worktree_id`, and `_parse_canvas_id`. Current messages match, but the exact REST and MCP
parity contract can drift when either adapter changes. The parity test exercises service failures,
not invalid UUID failures.

Impact: a future wording change can violate the locked identical code and message contract while
the existing cross surface test remains green.

Basis: the project DRY rule and Section 5 error parity.

Caveat: the REST parsers predate this commit, and the new generic MCP helper improves duplication
inside MCP itself.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/api/src/transport_matters/api/v1/space_mcp.py#L330-L339

### Minor 5: create and rename transport fixtures do not satisfy `SpaceSummary`

Location: `www/packages/core/src/spaceTransport.test.ts:93`

The create and rename fixtures contain only `spaceId` and `label`. `SpaceSummary` also requires
`isDefault`, `createdAt`, `updatedAt`, and `worktrees`. Because `stubApiTransport` accepts `unknown`,
TypeScript does not check fixture completeness.

Impact: removing or renaming a required response field can leave these transport tests green.

Basis: Section 8 requires response parsing coverage for create and rename. Declare the fixtures with
`satisfies SpaceSummary` or use a shared complete fixture.

Caveat: the REST lifecycle test verifies `isDefault` and `worktrees` on create, and both mutation
routes reuse `_space_summary`.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/www/packages/core/src/spaceTransport.test.ts#L92-L114

### Minor 6: reconciliation never proves named membership is unchanged

Location: `api/src/transport_matters/space/test_service.py:157`

The lifecycle test links, reads, and unlinks a named Space without reconciling detection. The
reconciliation tests use only the computed default Space. No test links a named Space, discovers or
refreshes worktrees, then proves the junction remains byte stable and excludes newly detected
siblings until the user links them.

Impact: a later reconcile change that prunes named links or enrolls detected siblings can pass the
current suite despite violating the load bearing model invariant.

Basis: model `019f8a57` states that detection and reconcile never read or write organizational
membership.

Caveat: current production reconciliation does not touch the junction. This is a proof gap, not a
reproduced state mutation.

https://github.com/littleorgans/transport-matters/blob/e116ffb60c037ce3cf950cc70c2c232681bc53aa/api/src/transport_matters/space/test_service.py#L157-L180

## Triaged observations

- Explicit named Space launch without membership is working as designed. Model `019f8a57` makes
  launch and placement owner scoped; named Spaces are view filters.
- The MCP principal continues to resolve owner scoped reads through the computed default. The
  orchestrator confirmed principal expansion is outside this slice.
- A concurrent Space delete between unlink validation and link deletion can be linearized after the
  validation read. The absent link postcondition holds, so the 204 acknowledgement is compatible
  with the specified idempotent removal semantics.
- The two reciprocal default membership triggers can race if a future switch default writer is
  added without row locking. There is no such producer in this slice. The future switch slice must
  establish its own transactional serialization.

## Builder trust

**Trust.** The change shows strong craftsmanship and no shortcut in the core path:

- All five store writes are owner scoped and reuse the shipped row mapper, junction, trigger, and
  membership predicate.
- SQL predicates enforce default rename and delete immutability atomically.
- Link maps concurrent Space and Worktree deletion through named foreign key constraints.
- Existing bound reads fail closed after `allowed_space_id` becomes optional. Every preexisting
  production constructor still supplies a concrete Space.
- REST mutations use the origin trust boundary and expose no owner override.
- MCP mutations derive an owner scoped unbound caller and delegate to the shared service.
- Browser bodies are camel case, identifiers are encoded, and shared HTTP helpers are reused.
- Tests cover durable cascade behavior, idempotency, the REST write to read lifecycle, origin
  rejection, MCP caller derivation, cross surface service error parity, and exact browser requests.
- No migration or parallel authority was introduced. Changed files remain at or below 700 lines;
  no changed function approaches 150 lines.

The commit combines tests and production in one local commit. Repository history cannot prove the
claimed red first sequence, although the resulting tests emphasize observable end states and include
a focused concurrent deletion regression.

## Verification boundary

- Reviewed the complete `6453364a..e116ffb6` diff at full SHA
  `e116ffb60c037ce3cf950cc70c2c232681bc53aa`.
- `git diff --check 6453364a..e116ffb6` passed.
- Builder reported `just check` and `just test-affected` passed. Broad gates were not rerun during
  this read only review.
- A temporary PostgreSQL table probe reproduced the exact NUL failure above and rolled back.
- The tracked repository remained clean at the reviewed SHA during review.
