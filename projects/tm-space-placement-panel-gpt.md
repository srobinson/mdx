# Space placement design panel

Reviewed on 2026-07-23 against `feat/multi-launch` at `3e3afa08065a3d963b67c118ad0f6f6762dbc770`.

## Decision

| Question | Verdict |
| --- | --- |
| Placement | Graduate Space to `packages/space` as `@tm/space`, later, through one atomic ownership cutover. Keep the implementation cohesive in Python until the cutover gates are met. Do not adopt an enduring hybrid. |
| Schema owner | At the target, `@tm/space` owns the Space schema, migrations, reads, and writes for `space`, `space_worktree`, `space_worktree_link`, and `canvas`. Python continues to own capture and session schemas. |
| Timing | Migration order later. Begin contract and port work now only if it is part of the explicit cutover program. Production ownership moves after schema, launch resolution, and principal handoff gates pass. |
| Context map | Add one Space bounded context. Document Worktree and Canvas as Space owned aggregates. Do not model them as three independent contexts. |

The destination follows the two plane rule. Space is a product organization context, while the Python plane is reserved for capture, Tier 1, Inspector, and the session store. Leaving Space CRUD and migrations in Python permanently would extend the capture plane with a new product context. Moving only the HTTP router would leave domain and data authority in Python and reduce `@tm/space` to a facade.

The timing follows the current durable seam. `docs/ARCHITECTURE.md:5-17` currently permits product packages to read Postgres records and assigns the Postgres session store to Python. A schema owning product context changes that contract. The architecture and database ownership model must be ratified before code moves.

## Current ownership and coupling

Space is cohesive today, but its consumers cross both planes.

1. Domain and durable writes are Python owned. `SpaceCrudService` composes detection, authorization, projection, and `SpaceStore` (`api/src/transport_matters/space/service.py:84-113`). `SpaceStore` writes all four Space tables (`api/src/transport_matters/space/store.py:59-169`, `426-505`). Alembic migration `0030_space_crud_reset` creates their constraints, triggers, and predicates in the Python migration chain (`api/migrations/versions/0030_space_crud_reset.py:11-75`, `106-342`).

2. Capture and session paths consume Space identity. Startup resolves the current checkout and backfills session identity (`api/src/transport_matters/main.py:230-245`, `368-369`). Capture preparation resolves a Worktree when the caller supplies an id without a directory (`api/src/transport_matters/api/v1/capture_rpc_routes.py:304-312`). Run meta also resolves the launch checkout (`api/src/transport_matters/api/v1/meta.py:143-163`). These are migration consumers, not evidence that Space belongs to capture.

3. The schema already contains a useful ownership seam. `session.space_id` and `run_lifecycle_event.space_id` are text stamps (`api/migrations/versions/0030_space_crud_reset.py:37-45`). They have no foreign key to the Space tables. All relational constraints remain within the four Space tables. This permits Space schema ownership to move while Python retains opaque identity stamps.

4. REST and MCP share the Python service. `/v1/spaces` mounts directly in FastAPI (`api/src/transport_matters/main.py:531-567`). The MCP adapter builds a `CrudCaller` from the authenticated control plane principal and calls the same service (`api/src/transport_matters/api/v1/space_mcp.py:82-190`). This is a valuable behavioral convergence that the migration must preserve.

5. The Gateway already demonstrates both required product plane seams. `@tm/activity` reads the Python owned Postgres records through a Node adapter, and `@tm/runtime` invokes Python capture through `CaptureRpcClient`. The Gateway composes their routers without owning either domain (`packages/gateway/src/main.ts`, `packages/gateway/src/app.ts`). `@tm/space` should follow that package shape and expose its router through its public barrel.

## Postgres durable seam

The target needs explicit table ownership inside the shared Postgres deployment.

| Owner | Durable authority |
| --- | --- |
| `@tm/space` | Space, Worktree, membership, and Canvas tables; their constraints, functions, triggers, and migrations |
| Python capture plane | Session, transcript, wire, lifecycle, intervention, control plane, and other capture tables; Tier 1 artifacts |
| Cross plane contract | Opaque `space_id` and `worktree_id` values stamped into capture and session records; no cross owner foreign keys |

Prefer a dedicated PostgreSQL schema and database role for Space. A table allowlist plus a separate migration ledger is the minimum acceptable boundary. One release must transfer migration authority from Alembic to the Node migration chain. Dual writers and dual migration chains are prohibited.

This requires a small architecture amendment. Replace the blanket statement that product packages only read Postgres with a per schema rule: each context may read and write its owned schema; Python alone writes capture and session schemas; cross context references use opaque ids or published facts. Existing Activity reads remain read only because Activity does not own the source tables.

The four Space tables should move together. Their invariants are relational and cyclic, including protected root Canvas pairs and named Space membership. Splitting Canvas or Worktree storage from Space would create distributed transactions around one aggregate boundary.

## Filesystem detection

Filesystem access does not justify capture plane placement. The detector inspects user checkout paths, `.git` markers, common directories, and `git worktree list` (`api/src/transport_matters/space/detection.py:77-130`, `149-174`, `200-230`, `273-290`). It does not read Tier 1 run directories or capture artifacts.

Move detection into a Node filesystem adapter behind an `@tm/space` port. The Gateway is a local process and can receive the same checkout access as Python. Cutover requires:

1. A fixture corpus for plain directories, primary worktrees, linked worktrees, worktree deletion, malformed `.git` files, symlinks, permission failures, and Git timeout behavior.
2. Parity for canonical path and workspace identity derivation across Python and TypeScript.
3. One production detector after cutover. A shadow comparison is acceptable before release, with the Node result excluded from writes.
4. Packaging proof that the embedded Gateway can invoke Git and inspect the selected checkout under the same user identity.

## MCP principal blast radius

MCP authorization is the highest risk migration seam. The current bearer resolver binds a stored grant to a live capture lease and verifies matching workspace identity before producing `ControlPlanePrincipal` (`api/src/transport_matters/capture_rpc.py:317-336`). That principal carries run id, role, workspace id, owner, permission posture, and run identity (`api/src/transport_matters/controlplane/models.py:41-54`). Space mutation authorization derives from those server resolved facts.

`@tm/space` must never accept owner, role, or workspace authority from MCP tool arguments. Two safe arrangements exist:

1. Keep the MCP transport adapter in Python initially. It authenticates the bearer, then calls an internal `@tm/space` service endpoint with a short lived, server authenticated principal envelope. Python retains no Space domain rules or database writes.
2. Move the MCP transport only after Gateway can resolve or introspect the control plane bearer against the live Python capture registry with fail closed semantics.

The first arrangement is the lower risk cutover. A transport adapter remaining in Python does not constitute split domain ownership. The adapter must be thin, and conformance tests must prove identical authorization and error behavior across REST and MCP.

## Target dependency shape

`@tm/space` owns Space, Worktree, and Canvas invariants, checkout detection, projections, authorization policy, persistence, and `/v1/spaces`. `@tm/contract/space` owns browser wire DTOs and stable error codes. Browser packages consume only that contract.

Runtime resolves `worktree_id` through the public `@tm/space` service before capture preparation, then sends Python the canonical directory plus opaque Space and Worktree ids. Python records those facts and performs capture. This removes the Space database dependency from capture preparation.

Session continues to stamp opaque ids. Historical backfill must finish before cutover, or use an internal Space resolution endpoint during a bounded migration window. Startup checkout reconciliation moves to the Gateway. Run meta should consume already stamped launch facts or query the internal Space service, with no direct Python Space store.

## Migration gates and order

1. Ratify the per schema Postgres ownership rule in `docs/ARCHITECTURE.md` and assign one migrator per schema.
2. Add `@tm/contract/space` for ids, DTOs, and errors. Add cross language conformance fixtures before changing behavior.
3. Build `@tm/space` with pure domain logic, ports, projections, Node Postgres adapter, filesystem detector, and Fastify router. Keep production writes disabled.
4. Prove detector and projection parity against the corpus and representative local repositories.
5. Move launch resolution ahead of capture RPC. Prove Runtime launches by Worktree id while Python receives canonical cwd and identity stamps.
6. Finish or redirect startup reconciliation, session backfill, and run meta consumers.
7. Implement the authenticated MCP principal handoff. Prove observer and director permissions, owner isolation, workspace binding, expired grants, stopped runs, and identity service failure.
8. Transfer the four tables, constraints, migration ledger, and database role in one release. Enable the Node writer and disable Python Space writes atomically.
9. Route `/v1/spaces` through the Gateway, delegate the Python MCP skin to `@tm/space`, and remove Python Space domain, store, detector, routes, and migration responsibility in the same migration program.
10. Run API contract, database migration, launch, MCP authorization, packaging, and end to end Canvas tests before declaring the cutover complete.

## Documentation change

Extend the target context map with:

| Context | Charter |
| --- | --- |
| Space | Truth owner for durable user organization, checkout identity, named Space membership, Worktree lifecycle, and the persisted Canvas tree |

Add an aggregate note under that row:

* `Space` is the top level organization aggregate.
* `Worktree` is path and checkout identity owned by Space.
* persisted `Canvas` is a Space owned tree anchored to a Worktree.

The documentation currently also uses Canvas for the browser product shell. Qualify the two terms as `Canvas shell` and `Canvas aggregate` wherever both appear. Runtime depends on Space resolution for launch. Session and Capture consume opaque identity stamps and never import the Space domain.

## Final recommendation

Graduate later through an atomic cutover. `@tm/space` should become the schema owning product context. Python should keep Space cohesive until the database ownership rule, launch resolution port, detector parity, and authenticated MCP principal handoff are proven. Any hybrid exists only as a bounded migration bridge with one writer and one domain authority at every step.
