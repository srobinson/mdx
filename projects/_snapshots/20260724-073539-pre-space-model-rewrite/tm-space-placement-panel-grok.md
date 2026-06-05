# Space placement panel (Grok) — whole-repo coupling + blast radius

Date: 2026-07-23  
Head under review: `feat/multi-launch` @ `3e3afa08`  
Authority: `docs/ARCHITECTURE.md` (two-plane rule; product packages under `packages/*`; canonical `@tm/<context>`; "migration order, not final vocabulary")  
Lens: whole-repo coupling, edge counts, migration-order feasibility  
Not a build. No gate run.

## 0. Short answer

| Question | Verdict |
|----------|---------|
| Placement | **Stay in Python now; graduate later.** Not a stable hybrid. |
| Schema owner | **Python session-store Alembic now.** Schema-owning `@tm/space` only after a product-plane schema rail exists. |
| Timing | **Migration-order later.** Gates: Gateway as origin, capture launch inverted behind a port, schema ownership pattern proven. |
| Rough cost | **Large** (multi-PR / multi-week). Domain rewrite + identity decoupling + schema move + MCP host. Not a rename. |
| Context map | **Yes** — add **Space** as a product context; Worktree/Canvas are its aggregates, not peer contexts. |

Space is a **product context by nature** (durable org container, VSCode multi-root semantics). It currently lives in the capture plane because that is where Postgres, launch resolution, and MCP already are. Architecture explicitly allows this as migration order, not final vocabulary.

---

## 1. Edge map (concrete, not ideal)

### 1.1 Module mass at `3e3afa08`

| Area | LOC (approx) | Role |
|------|-------------:|------|
| `api/.../space/` domain (models/store/service/detection/projection/identity) | ~2.1k prod | Domain + FS detection + SQL |
| `api/.../space/` tests | ~2.8k | |
| Skins: `space_routes` + `space_mcp` + `space_contracts` | ~910 | REST + MCP + DTO leaf |
| Migration `0030_space_crud_reset` | ~430 | Schema authority (with 0006 ancestry) |
| Browser: `www/packages/core/spaceTransport*` | ~360 | HTTP client only |
| Canvas consumers | useSpaces / workdirRows / route / canvasState | Read models + nav identity |

Outbound from Space domain (prod): **only** `transport_matters.workspace` (path slug/hash) plus psycopg via the injected connection. Space does **not** import mitmproxy, wire, or transcript parsers. In isolation it is already a clean domain package that happens to be written in Python.

### 1.2 Inbound production edges → `transport_matters.space` (17 files)

Classified:

| Kind | Count | Files | Coupling strength |
|------|------:|-------|-------------------|
| **Identity types only** (`SpaceId` / `WorktreeId` / stamps) | **10** | `session/models`, `session/async_dao`, `captured_run_models`, `capture_rpc`, `capture_rpc_routes`, `shared_proxy/{models,binding}`, `run_lifecycle`, `index/adapters/base`, `api/v1/ids` | Soft: branded IDs + free-form stamp fields. Capture plane treats `session.space_id` as **text** (`SpaceRef`), not a FK to live Space rows. |
| **Service calls** (load-bearing) | **4** | `main.py` (startup `resolve_cwd` + session backfill wiring), `api/v1/meta.py` (launch worktree on run meta), `api/v1/launch_resolution.py` (spawn-time worktree resolve for runs + capture RPC), `session/backfill.py` | Hard: spawn and identity repair fail closed without Space service. |
| **Skin adapters** | **3** | `space_routes`, `space_mcp`, `space_contracts` | Medium: product API surface; movable with Gateway. |

Plus **test/importer** fan-out (~15 more modules) that would move with any package split.

**Controlplane:** no production import of Space domain. MCP tools are co-registered on the same FastMCP server; principal/auth is shared, domain is not.

**Product plane → Space:** browser only, via HTTP:

- `@tm/core` `spaceTransport` (fetch + mutations)
- `@tm/canvas` `useSpaces`, `useCanvases`, `workdirRows`, route/canvasState identity (`spaceId` / `worktreeId` strings)

No Node package imports Python. Canvas never talks SQL.

**Gateway:** mounts `@tm/activity` + `@tm/runtime` only. **Zero** Space routes. Python remains origin for `/v1/spaces*`.

### 1.3 Edge counts each way (summary)

```
Capture plane → Space domain
  10 identity-only  +  4 service  +  3 skins   =  17 prod importers

Space domain → Capture plane
  workspace.py only (path identity)            =  1 real dep
  (+ session pool injected, not imported as domain)

Product plane → Space
  HTTP client (@tm/core) + Canvas consumers    =  ~1 transport + ~6–8 canvas files
  No reverse: Space does not import browser packages

Gateway ↔ Space
  0 edges today
```

Blast radius of a naive "move the folder" is dominated by the **4 service callers** and the **shared Alembic head**, not by the 10 type importers.

---

## 2. What would have to move for `@tm/space`

Canonical shape from ARCHITECTURE.md: `domain/`, `service/`, `ports/`, `adapters/`, `server/`, `projections/`, `index.ts`.

| Piece | Move cost | Why |
|-------|-----------|-----|
| **DTO / wire contract** (`SpaceSummary`, list envelope, camelCase) | **Cheap** | Already split as `space_contracts.py` + TS types in `@tm/core`. Promote to `@tm/space` (or `@tm/contract/space`) without moving logic. |
| **REST router** (`/v1/spaces*`) | **Medium** | Pattern exists (`createRuntimeRouter` / `createActivityRouter`). Needs Gateway mount + origin flip so Canvas still same-origin. |
| **MCP tools** (9 space tools today: 4 reads + 5 mutations) | **Medium–hard** | Tools live on Python FastMCP with control-plane principal resolution. Product-plane MCP host does not exist yet; dual registration would fork agent contract. |
| **Git / FS detection** (`detection.py` ~350 LOC) | **Hard / machine-local** | Walks `.git`, classifies git/plain/inconclusive. Must run on the machine that owns the checkout (desktop host). Node can do this, but capture spawn still needs the answer **in-process** today. |
| **Domain service + store** (~1.3k LOC) | **Hard** | SQL is tuned to session-store Postgres (triggers, `worktree_in_space`, CASCADE). Rewrite in TS adapters is feasible but not mechanical. |
| **Schema + Alembic `0030`** | **Load-bearing** | Single migration chain in Python owns `space`, `space_worktree`, `space_worktree_link`, `canvas`, SQL functions/triggers. Session stamps deliberately **not** FK-bound (`space_id` text). Splitting schema ownership without a dual-write or freeze protocol risks the whole session store. |

### 2.1 Hybrid (domain/service in TS, schema+detection behind Python port)

**Unstable as an end state; acceptable only as a thin temporary port after Gateway origin.**

Why it doubles the seam:

1. Capture spawn still needs `resolve_launch_worktree` / `resolve_session_cwd` **before** mitmproxy binds. That path is Python today and synchronous with the pool. A hybrid leaves a permanent Python port **or** adds a hop (Python → Gateway → `@tm/space` → Postgres) on the hottest launch path.
2. Detection is local FS. Hosting it only in Node while Python still writes membership/reconcile means two writers or a fake "Python is dumb cache" story.
3. Schema stays Python-owned → TS service becomes a second ORM over tables it does not migrate. Drift surface multiplies (exactly what single Alembic avoids).
4. MCP either stays Python (domain half-moved) or splits (agent contract forks).

Hybrid is a **straddle**, not a context. Prefer either stay complete in Python, or graduate complete behind ports — not half.

---

## 3. Architecture fit

From `docs/ARCHITECTURE.md`:

- *Python is the capture plane… new product contexts do not extend it.*
- *TypeScript is the product plane… bounded contexts live as pnpm packages…*
- *Migration order, not final vocabulary. Until the Gateway exists, Python remains the origin…*

**Space is not capture truth** (not wire, not transcript, not breakpoint). It is **placement / org identity** that capture **stamps** onto sessions and runs. That makes it a product context in the target map, currently staged in Python because:

1. Gateway is not yet the origin (Python still fronts product routes).
2. Runtime graduated first; Space was not on that migration path.
3. Launch resolution is still a Python capture-plane concern.
4. Schema lives in the capture session-store chain by history (0006 → 0030).

So: **identity of the domain says graduate; edges and rails say stay until migration order catches up.**

---

## 4. Explicit answers

### 4.1 Placement verdict (grounded in edges)

**Stay (now) / graduate (later). Reject hybrid as stable.**

- **17** production importers, of which **4** are hard service edges on the launch and startup path.
- Product plane already treats Space as a remote HTTP API (`@tm/core`), which is the correct long-term skin shape.
- Moving domain to `@tm/space` without inverting those 4 callers does not reduce blast radius; it relocates it behind a network hop on spawn.
- Edge asymmetry (almost no outbound deps) means the package *could* extract cleanly once callers sit behind a port — the blocker is callers + schema + Gateway, not spaghetti inside Space.

### 4.2 Schema-ownership verdict

**Python (session-store Alembic) remains owner now.**

Long-term, if Space is a product context, **schema-owning `@tm/space`** is coherent with the two-plane rule (context owns domain + projections + store). That is **not** free today:

- No second migration authority exists beside `api/migrations`.
- Capture stamps must remain FK-free text (already true) so capture can survive schema moves.
- Any schema move needs freeze of 0030 head, a transfer protocol, and capture regression on stamp + launch.

Do **not** invent dual writers. One owner at a time.

### 4.3 Now vs later + gates + rough cost

**Later (migration order).** Do not graduate as the next build slice after Space-CRUD.

| Gate | Why required |
|------|----------------|
| **G1. Gateway is origin** | Space REST must mount as `@tm/space` `src/server` under Gateway; Python reverse-proxies frozen capture only. Today Python is still origin. |
| **G2. Capture launch inverted** | `launch_resolution` / `meta` / `main.resolve_cwd` / backfill call a **port** (HTTP or in-proc FFI), not `SpaceCrudService` import. Until then, domain must stay co-located with capture. |
| **G3. Schema rail** | Either product-plane migrations own Space tables with capture as consumer, or a published freeze + move of 0030 with dual-read window. Prefer one owner. |
| **G4. MCP host decision** | Product contexts either gain an MCP surface or Space tools remain a thin Python skin over the port (acceptable interim). |

**Rough cost after gates:** large.

| Band | Work |
|------|------|
| S (days) | Extract shared ID brands + DTOs to `@tm/contract` / `@tm/space` types; browser imports them. No runtime move. |
| M (1–2 weeks) | `@tm/space` server router + Gateway mount; Python proxies `/v1/spaces*` temporarily. Domain still Python behind proxy. |
| L (multi-week) | Rewrite store/service/detection in TS; invert 4 capture callers; migrate or freeze schema; MCP plan; delete Python domain. |

Cheapest **useful** prep (now, without graduating): keep Space domain frozen as a package-shaped Python module (already almost is), stop growing capture imports beyond identity stamps, and put new product UX only on the HTTP surface.

### 4.4 Context map

**Yes — extend the target context map:**

| Context | Role |
|---------|------|
| **Space** | Durable org container (VSCode multi-root). Owns Worktree path identity and Canvas tree as aggregates. Producer of placement ids that Session/Runtime stamp. |
| Session | (existing) transcript records |
| Runtime | (existing) run lifecycle |
| Activity | (existing) status / overview |

Dependencies: Runtime/Session may **reference** Space/Worktree ids; they must not import Space internals. Canvas is a **surface**, not a context. Worktree and Canvas are **not** separate contexts — they are Space aggregates (matches model of record 019f8a57).

Optional doc note: "Workspace" (`workspace_id` path slug/hash) remains a **capture-plane path identity** distinct from durable Space — do not rename them into one vocabulary without an explicit cutover.

---

## 5. Risk of deciding wrong

| Wrong call | Failure mode |
|------------|----------------|
| Graduate now | Double write paths during spawn; half-migrated MCP; schema drift; multi-week stall on a green Space-CRUD head. |
| Hybrid forever | Permanent two-language service with capture still owning truth; every Space feature pays twice. |
| Stay forever | Contradicts "new product contexts do not extend Python"; Canvas/org product will keep growing REST/MCP on the capture plane. |

Correct posture: **stay complete until gates, then graduate complete.**

---

## 6. Recommendation to Stuart

1. **Merge Space-CRUD in Python** without blocking on placement (placement is orthogonal to the green gate).
2. **Record Space on the target context map** as a future product context; do not open `@tm/space` this slice.
3. **Prep only:** (a) identity brands/DTOs extractable; (b) no new capture-plane importers of `SpaceCrudService` beyond the existing four; (c) after Gateway origin flip and Runtime-style launch inversion, schedule Space as the next context extraction.
4. **Schema stays Python** until a deliberate schema-ownership project, not as a side effect of a package rename.

---

## 7. Independence note

This panel did not re-run the merge gate. Coupling numbers are from live tree at `3e3afa08` via import graph scan of `api/src` and product packages. Runtime/Activity under `packages/*` used as the migration precedent: Gateway already mounts them; Space has no equivalent mount or port inversion yet.
