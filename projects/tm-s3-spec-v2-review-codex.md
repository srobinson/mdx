# S3 specification v2 review

Verdict: **changes requested**

Counts: **1 blocker, 3 majors, 1 minor**

Reviewed `~/.mdx/projects/tm-s3-spec-v2.md` against `feat/multi-launch` at
`7ffba78b9feeafda5799cc5d032ee2712d4f8907` and Context Matters decision
`019f9016-6595-7470-b11c-745e15f687b7`.

No repository writes or gates were performed.

## Blocker

### B1. The mandatory N:1 replacement remains conditional and leaves the obsolete M:N surface alive

Spec citations:

- §4: **“Migration: may be required if HEAD schema cannot express N:1 workdir→space without computed-all; call out in S3a design/STEP-0.”**
- §4: **“Workdir belongs to one Space (store a owning `space_id` or equivalent N:1 edge...”**
- §4: **“Multi-Space same OS path = multiple workdir rows...”**
- §4: **“Surfaces: `SpaceStore` + `SpaceCrudService` + REST + MCP parity.”**

HEAD conclusively cannot express the confirmed model:

- `0030_space_crud_reset.py` keeps `space_worktree` independent of Space, makes
  `(owner, path)` and `(owner, workspace_slug, workspace_hash)` unique, and
  relates Spaces through `space_worktree_link`.
- `worktree_in_space(...)` gives the default Space computed membership of every
  owner Worktree.
- Store, service, REST, and MCP still expose link and unlink operations.

The required migration is therefore mandatory and breaking, not optional or
thin additive. The current uniqueness constraints also make two Workdir rows
for the same OS path impossible. An implementation could follow §4 while
leaving link routes or computed membership in parallel, violating the confirmed
model and the repository’s replacement rule.

Required revision: lock the replacement schema and deletion list. At minimum,
bind Workdir ownership to `space_id`, scope path and workspace identity
uniqueness by Space, remove `space_worktree_link`, remove
`worktree_in_space(...)`, and remove the link and unlink store, service, REST,
MCP, and test paths. State the exact create semantics for adding the same OS
path to another Space.

## Majors

### M1. S3a is not a PR-sized slice and STEP-0 is bundled with all behavior

Spec citation:

- §6: **“S3a | STEP-0 store extract; domain-aligned workdir↔space ownership; `delete_workdir` cascade canvases + stop runs; `delete_space` cascade all workdirs (default locked); MCP+REST; tests”**

This single slice combines a no-behavior extraction, a foundational schema and
identity rewrite, removal or replacement of existing CRUD contracts, cascade
deletion, Gateway side effects, two public surfaces, and all tests. Current
affected files already include `space/store.py` at 693 lines,
`space/service.py` at 596, `space_routes.py` at 564, `space_mcp.py` at 499,
plus a 420 line migration and large contract suites. This is not a bounded
review unit.

Required revision: make STEP-0 a preceding behavior-neutral slice. Then separate
the N:1 schema and CRUD replacement from delete plus managed-run orchestration.
Keep S3b as the independent teardown cleanup slice.

### M2. Delete does not bind to the existing Python run port or define best-effort failure semantics

Spec citations:

- §2: **“Cascade: canvases anchored under it (hierarchical subtree) + stop that workdir's gateway-managed runs.”**
- §7: **“Stop managed run | `RunManager.terminate` / POST `/v1/runs/{id}/terminate`”**
- §7: **“List by space/workdir | `RunManager.list` + gateway `list_runs`”**

The existing Python seam is already typed:
`RunManagementPort.list_runs(...)` and `terminate_run(...)`, implemented by
`RunRouteProxy`. The spec does not say that Space deletion receives this port,
lists by the target Space or Workdir before deleting its rows, and terminates
each returned run through that same port. It also omits the settled best-effort
policy when list or terminate is unavailable, times out, or has an unknown
outcome.

Required revision: specify the exact sequence and dependency. Reuse
`RunManagementPort`; list by the target id, terminate each run, continue the DB
cascade on stop failure, and rely only on run-end teardown for tier 1
collection. Do not add another HTTP client, process scan, coordinator, or
delete-time filesystem path.

### M3. The `dev_mode` defaults contradict the confirmed environment contract

Spec citation:

- §5: **“Default | False (prod-safe GC) in code; local sets env to preserve. CI stamp seam for build flags: unspecified today”**

The confirmed shape requires development launches to default to development
mode, production to default to collection, and CI to stamp the production
default. Leaving both the local writer and CI seam unspecified does not bind
that behavior and permits local runs to erase tier 1 data by default.

Required revision: retain the single
`TRANSPORT_MATTERS_DEV_MODE`/`Settings.dev_mode` flag, name the existing local
development launch scripts that set it true, and require CI to set the
production value explicitly. Add tests proving both tier 1 and runtime-home are
preserved in development mode and collected in production mode.

## Minor

### m1. The specification lists test subjects but no repository gate commands

Spec citations:

- §4: **“Tests: cascade workdir+space; default locked; same OS path two Spaces independent; run-stop scoped; OS path remains on disk.”**
- §6: **“MCP+REST; tests”**
- §6: **“containment; light tests”**

Required revision: add acceptance gates for every implementation slice using
the repository recipes `just check` and `just test`. `just test-affected` may be
listed as a local iteration aid, but it is not the final gate. Do not prescribe
bare `pytest` or `tsc`.

## Confirmed correct

- No finalization gate or `run_capture_state`.
- No Space deletion coordinator or second filesystem trigger.
- No second storage retention flag.
- Delete ends managed runs and tier 1 collection stays on run-end teardown.
- Detached CLI process control remains out of scope.
- Runtime-home and tier 1 cleanup share the existing teardown stack and occur
  after the capture process drain attempt.
- The user’s OS directory remains detection-only and untouched.
