# Space module placement — design panel (opus, DDD / bounded-context lens)

Panelist: opus architect, multilaunch warroom. Topic: `space-placement-panel`.
Question: does `space` stay in the Python capture plane (`api/src/transport_matters/space/` @3e3afa08)
or graduate to a product-plane node package `packages/space` (`@tm/space`), peer to Activity/Runtime?
Read: `docs/ARCHITECTURE.md` (two-plane rule) + the live `space` module + its real couplings.

## TL;DR

- **Placement: STAY Python (persistence/capture plane). Do NOT graduate the aggregate to `@tm/space`.**
- **Schema owner: PYTHON.** The organizational schema is a peer concern of the Python-owned Postgres
  store, in the same DB and the same migration chain, FK/stamp-coupled to the session store. A
  schema-owning `@tm/space` would be a two-writer distributed monolith.
- **Now/later: neither.** The aggregate never graduates. A thin TS *read* projection could exist later
  if a product view needs it, but that seam already exists (browser reads org state over REST via
  `@tm/core`), so it is YAGNI today.
- **Context map: add "Organization/Space" to the architecture's context *vocabulary* as a
  persistence-plane platform context — but keep it OUT of the Activity v1 producer table.**

I am disagreeing with the "graduate" framing. The domain shape looks like a product context; the
*ownership* is entirely persistence-plane.

## 1. Is `space` a bounded context? Yes. Does the canonical shape fit? Yes — that is the trap.

By pure domain, Space/Worktree/Canvas is a real bounded context: a durable organizational container
(Space), a durable path identity (Worktree) owning an anchored Canvas tree, with one load-bearing
invariant (`worktree_in_space`) and its own ubiquitous language, distinct from capture and session.
It already maps cleanly onto the canonical `@tm/<context>` skeleton:

| Canonical slot | Space today |
| --- | --- |
| `domain/` (aggregates + invariants) | `models.py` + the `worktree_in_space` predicate |
| `service/` | `SpaceCrudService` |
| `ports.ts` | the `SpaceStore` interface |
| `adapters/` | `store.py` (Postgres) |
| `projections/` | `projection.py` |
| `server/` | `space_routes.py` + `space_mcp.py` |
| `fixtures/` | `testing.py` |
| domain service | `detection.py` (filesystem classifier) |

**The shape matching is exactly why the "graduate" instinct fires — and exactly why it is misleading.**
The canonical shape describes a well-factored context; it does not decide which *plane* owns it.
Placement follows ownership, and ownership is decided by the durable seam, not the folder layout.

## 2. The load-bearing sub-decision: who owns the organizational schema? → PYTHON

The architecture's durable seam is explicit and one-directional:

> "product plane packages **read records from Postgres** and never read capture plane filesystem
> paths" … "Python … owns the Postgres session store" … "new product contexts do not extend it."

Product-plane contexts are **readers** of a Python-owned store. `space` is a **writer** of new
organizational tables and the **owner of migration 0030**, which is a linear link in the single
Alembic chain (`down_revision = 0029_native_connection_origin`). The coupling is not arms-length:

1. **The session store — the durable seam itself — is stamped with Space aggregate identities.**
   `session/models.py` carries `space_id: SpaceRef` and `worktree_id: WorktreeId` on session rows;
   the S2 plan adds the Canvas stamp group. The thing product packages are told to *read* is
   schema-coupled to Space. You cannot hand Space's tables to a separate owner without splitting
   ownership of rows the Python session store references.
2. **Resolution is synchronous, same-connection, at capture-claim time.** `launch_resolution.py` and
   `capture_rpc.py` call `SpaceCrudService(conn).resolve_launch_worktree(...)` on the capture path,
   in the same transaction that persists the run/session. That is intra-plane aggregate
   collaboration, not the by-id record read the product plane uses.
3. **`detection.py` reads the capture-plane filesystem** (`Path.resolve(strict=True)`, `.git`
   markers, `commondir`). The doc bars product-plane packages from exactly this ("never read capture
   plane filesystem paths"). Space's core domain service is, by the doc's own boundary definition, a
   capture-plane concern.

A schema-owning `@tm/space` therefore forces one of two broken topologies onto a single database:
either two deployables owning overlapping, cross-referencing schema with two migration chains, or a
product package reaching across the plane to write the Python-owned store. Both are the classic
distributed-monolith failure: an aggregate boundary that does **not** coincide with a deployment or
ownership boundary. **The organizational tables are a peer concern inside the Python-owned Postgres
store. Python owns the schema and its migrations. Full stop.**

## 3. Placement verdict: stay Python; it is a persistence-plane bounded context

`space` is a first-class bounded context, but a **persistence/capture-plane** one, not a product-plane
peer to Activity/Runtime. Keep it in `api/src/transport_matters/space/`. It already carries the
canonical shape; treat it as the reference persistence-plane context rather than forcing it across a
seam its ownership does not cross.

Outbound, `space` is nearly self-contained (production deps: only `workspace` identity and
`session.pool`). Inbound, it is woven into the persistence/capture core — `session/{models,async_dao,
backfill}`, `capture_rpc`, `run_lifecycle`, `shared_proxy/binding`, `index/adapters/base`, `main`.
The dependency gradient points *into* the capture plane, not out toward the product plane. Ownership
and coupling agree: it stays.

The product plane relates to Space the correct way already: Canvas (the browser shell) reads
organizational state over REST through `@tm/core` (`fetchSpaces`, `fetchCanvases`, …). That is the
arms-length read seam. No node context is required to make product surfaces consume Space.

## 4. Now / later, and what a future TS presence would (and would not) be

- **The aggregate + schema + migrations never graduate.** This is not gated on the Gateway — the
  Gateway governs serving/origin, not schema ownership. Nothing about a front-door origin flip changes
  who owns the organizational tables.
- **A thin `@tm/space` *read projection* could appear later**, migration-order, gated on two things:
  (a) a concrete product need — a Control-Center / Canvas organizational view not already served by
  `space_routes`; and (b) a stable by-id read seam from the Python org store. Until both exist it is
  YAGNI; the browser already reads what it needs over REST. If it ever ships, it is a projection
  *consumer*, never the schema owner.

## 5. Target context map: add Space to the vocabulary, not to the Activity producer table

The `| Context | Role in Activity v1 |` table is Activity-centric (Session/Runtime/Activity as
producers/interpreter). Space emits no Activity facts (no RunStarted/RunExited); it is orthogonal to
the event backbone. It correctly does **not** belong in that producer table.

But the architecture's broader context *vocabulary* (Session, Runtime, Activity, Comms, Recall,
Capture, Intervention, Log) omits the organizational context entirely, and that is a real gap. Space/
Worktree/Canvas is a named bounded context and deserves to be listed — as a **persistence-plane
platform context** (Python-owned, schema owner, filesystem-reading detection, resolved synchronously
at capture-claim time, orthogonal to the fact backbone). Recommend adding an "Organization" (or
"Space") row to the plane/vocabulary description in `ARCHITECTURE.md`, explicitly tagged persistence-
plane, so the doc stops implying every bounded context is a product-plane package. This closes the
"map omits it" gap without misfiling it as a product-plane peer.

## Answers to the four explicit questions

1. **Placement:** Stay Python (persistence/capture plane). It is a bounded context, but its ownership
   is persistence-plane, not product-plane. Do not graduate the aggregate.
2. **Schema owner:** Python. Same DB, same migration chain, FK/stamp-coupled to the session store;
   splitting creates a two-writer distributed monolith. The aggregate boundary is not a deployment
   boundary.
3. **If graduate:** The aggregate does not — now or migration-order-later. Only a read-side product
   projection might, gated on a real Canvas/Control-Center org-view need plus a stable by-id seam;
   YAGNI today (REST read seam already serves the browser). Not gated on the Gateway.
4. **Context map:** Add an "Organization/Space" context to the architecture's persistence-plane
   vocabulary. Keep it out of the Activity v1 producer table (it emits no Activity facts).
