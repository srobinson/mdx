---
title: Product-plane serving topology & ubiquitous language — where the P1 run host slots
type: projects
tags: [transport-matters, architecture, product-plane, control-center, runtime, gateway, naming, p1, topology, ddd]
summary: 'Independent design + naming proposal. Verifies that "Control Center serving" is doc-only and aspirational, and that Control Center is a product SURFACE (Activity''s Canvas face), not a serving process or a bounded context. Argues the P1 "TS host / run host" is DISTINCT from Control Center serving: it is the serving surface of the Runtime context (@tm/runtime), the RunStarted/RunExited producer, tightly coupled to the frozen Python capture sidecar via the bind/release RPC. Proposes the target topology as ONE product-plane gateway (composition root, origin) that mounts each context''s router (Activity read surface + Runtime run/terminal) and reverse-proxies the frozen Python capture plane; P1''s Python-front-door choice is the interim seam and flips at the target. Recommendation = distinct-run-host, with a doc cleanup of the confused "Control Center serving" line and a package placement of the host at packages/runtime per the placement rule.'
status: proposal
source: opus — independent pass (parallel to a second agent; no cross-read)
confidence: high
created: 2026-07-04
---

# Product-plane serving topology & ubiquitous language

**Proposal for Stuart. Read-only pass; he owns the naming and the architecture.**
Citations are **file + symbol**, never line numbers. Every code claim below was
re-verified against the current tree, not taken from the spec on faith.

The trigger: `docs/ARCHITECTURE.md` "Two plane rule" lists a product-plane surface
called **"Control Center serving"**; the P1 spec (`tm-t3code-p1-spec.md`) stands up
a new **"TS host / run host"** serving the run lifecycle + terminal. **Are they the
same thing?** The short answer is no, and the reason is a category confusion in the
doc that this proposal untangles.

---

## 1. What "Control Center serving" means today — verified

**It is aspirational and doc-only.** A tree-wide search for `control center` /
`control-center` / `controlCenter` (case-insensitive) returns **exactly one hit**:
the sentence in `docs/ARCHITECTURE.md` "Two plane rule" —

> "TypeScript is the product plane. Activity, **Control Center serving**, future
> Comms, Recall, orchestration, and other new contexts live as pnpm workspace
> packages."

There is **no** package, module, route, class, or symbol named Control Center
anywhere in `api/`, `packages/`, `www/`, or `desktop/`. It is a name in a design
doc, nothing else.

**What the name actually points at (from cm + the Activity spec):** the Activity
spec (`tm-activity-spec.md`) is titled **"Control Center v1"**, and its slice 4 is
the **"canvas Control Center face"** (cm decision `019f24f9`, "Activity (Control
Center v1) spec approved"; resume checkpoint `019f293a`). So in the ubiquitous
language as it actually stands:

> **Control Center = the Canvas-facing SURFACE of the Activity context** — the pane
> where run status / overview / usage rollups are shown to the operator.

That single fact resolves the whole question. "Control Center serving" in the
two-plane rule is a **loose phrase for serving the Activity read surface** that backs
the Control Center face. It is not, and was never, a name for a run/terminal host.

**Verified serving today** (`api/src/transport_matters/main.py::mount_frontend_bundles`):
Python is the origin. It serves the canvas bundle at `/canvas` (+ the `/canvas-lab`
page) and the inspector bundle at `/` as the catch-all. Nothing TypeScript serves any
HTTP surface yet; `@tm/activity` exists (`packages/activity/src`, canonical shape:
`domain/ events.ts ports.ts service/ adapters/ projections/ server/ index.ts`) but its
`server/` is not yet mounted anywhere. The product plane has **zero live serving
processes** today.

---

## 2. Product-plane serving topology

### 2.1 The two concerns are different bounded contexts, not one

The P1 host and "Control Center serving" sit at **opposite ends of the Activity event
backbone**, and `docs/ARCHITECTURE.md` "Target context map" already draws the line:

| Concern | Context | Role | Direction |
| --- | --- | --- | --- |
| Serve the **Control Center** face | **Activity** (`@tm/activity`) | downstream interpreter of run status/overview/usage; reads Postgres records | **consumer** |
| Serve **run lifecycle + terminal** (the P1 host) | **Runtime** | spawns/terminates runs, owns the PTY, binds capture; **emits RunStarted/RunExited** | **producer** |

The doc's own rule forbids fusing them: *"Dependencies point downstream only.
Producers never import Activity. No module outside Activity computes Activity status."*
The run host **is** the Runtime producer — verified: run lifecycle facts are built and
emitted from `api/src/transport_matters/run_manager.py` (`build_n_event`, the `emit_n`
sink) and committed by `session/writer.py`. When P1 moves the run lifecycle to TS, the
TS host **becomes** the Runtime producer. Fusing it with Activity's read surface would
wire a producer into its own consumer — exactly the cycle the two-plane rule bans.

So: **the P1 "TS host" is the serving surface of the Runtime context. "Control Center
serving" is the serving surface of the Activity context. They are two different
contexts and must stay two packages.** The P1 spec author invented "TS host / run
host" precisely because "Control Center serving" did not obviously mean "the run
host" — the confusion is real, and the resolution is that they were never the same.

### 2.2 One origin, many routers — not one fused server, not N processes

"Distinct contexts" does **not** mean "a separate OS process per context." The right
target is the shape Python already runs: **one composition root that mounts many
routers.** Verified in `api/src/transport_matters/main.py::create_app`, the Python
origin mounts *separate* routers under sibling paths —

- `run_routes.router` at `/v1` — the 5 run routes (verified: `POST` create, `GET`
  list, `GET /{run_id}`, `POST /{run_id}/terminate`, `WS /{run_id}/terminal`)
- `exchanges.run_router` at `/v1/runs/{run_id}/exchanges` (capture artifacts)
- `meta.run_router` at `/v1/runs/{run_id}/meta` (capture metadata)
- `session_routes.router`, `space_routes.router`, `stream.router`, … at `/v1`

The product plane wants the same discipline: each context owns its `src/server/`
router (canonical shape), and a **product-plane gateway** (composition root) mounts
them into one origin. Several routers, one origin. This is the missing noun in the
doc.

### 2.3 The reverse-proxy to the frozen Python capture plane

The capture plane is frozen (two-plane rule; cm `019f270c`). Its **data** stays Python
forever: exchange bytes (`exchanges.run_router`, consumed by
`www/packages/core/src/transport.ts::fetchExchange`), run meta
(`meta.py::get_run_meta` → `transport.ts::fetchMeta`), the live inspector feed
(`api/v1/stream.py::stream_run` at `/v1/runs/{run_id}/stream`), and the breakpoint
plane (`pause_session.py`, `breakpoint.py`). Whoever is the origin **reverse-proxies
those routes to the Python sidecar** and never reimplements them.

Note the separation the scout surfaced: the inspector *bundle* (static JS/HTML) is a
browser artifact; who serves the files is independent of who serves the inspector's
*data*. The origin can serve the inspector bundle while proxying its data to Python.

### 2.4 Target topology (and where P1's interim choice fits)

```
                         ┌───────────────── browser ─────────────────┐
                         │  Canvas bundle (Control Center face,       │
                         │  launcher, terminal panes)  •  Inspector   │
                         └───────────────────┬───────────────────────┘
                                             │ same-origin, relative paths
                    ┌────────────────────────▼─────────────────────────┐
                    │        PRODUCT-PLANE GATEWAY  (origin)            │
                    │  composition root — mounts context routers,      │
                    │  serves canvas + inspector bundles               │
                    │   ├─ @tm/runtime  server/  → /v1/runs (5 routes)  │
                    │   ├─ @tm/activity server/  → status/overview SSE  │
                    │   └─ (future: Comms, Recall, Log, orchestration)  │
                    └───────┬───────────────────────────┬──────────────┘
                            │ capture bind/release RPC   │ reverse-proxy
                            │ (Runtime → Python)         │ (capture reads)
                    ┌───────▼───────────────────────────▼──────────────┐
                    │      PYTHON CAPTURE SIDECAR  (frozen)             │
                    │  mitmproxy, addon, Codex transport, breakpoint,   │
                    │  exchange recorder, IR/normalization              │
                    │  routes it still owns: exchanges, meta,           │
                    │  /v1/runs/{id}/stream, breakpoint                 │
                    │  Postgres session store + Tier-1 disk  ← the      │
                    │  durable inter-plane boundary                     │
                    └──────────────────────────────────────────────────┘
```

**P1's interim topology is the mirror image of the target's front door, and that is
fine.** P1 (spec §1, §2b) keeps **Python as the origin** and reverse-proxies only the
5 run routes *out* to the TS host, because flipping the origin is more work than P1
needs. That is a migration scaffold, not the destination:

| | Origin / front door | Serves bundles | Run routes | Capture reads |
| --- | --- | --- | --- | --- |
| **Today** | Python | Python | Python (`run_routes.router`) | Python |
| **P1 interim** | Python | Python | **`@tm/runtime`** (Python reverse-proxies 5 routes to it) | Python |
| **Target** | **Gateway (TS)** | Gateway | `@tm/runtime` (mounted router) | Python (gateway reverse-proxies) |

The arrow flips once: in P1 the frozen plane is the front door proxying *to* the new
context; at the target the new gateway is the front door proxying *to* the frozen
plane. The P1 host is the **first tenant** of the eventual gateway, not the gateway
itself.

---

## 3. Ubiquitous names

Four distinct nouns; the doc currently collapses two of them.

| Name | Kind | Definition | Serving |
| --- | --- | --- | --- |
| **Control Center** | product **SURFACE** | the Canvas face where Activity status/overview/rollups are shown | rendered by the canvas bundle; not a process |
| **Activity** (`@tm/activity`) | bounded **CONTEXT** | downstream read model: run status, overview, usage | its `src/server/` router — *this* is what "Control Center serving" should mean |
| **Runtime** (`@tm/runtime`) | bounded **CONTEXT** | run lifecycle + terminal transport + capture bind; the P1 "TS host" | its `src/server/` router — the 5 run routes + terminal WS |
| **Product-plane gateway** | serving **PROCESS** (app / composition root) | the origin that mounts context routers, serves bundles, reverse-proxies the frozen Python plane | is the serving process; not a context |

**Is Control Center a process, a context, or a surface? A surface — argue it.** The
only evidence in the codebase and cm names it as the Canvas *face* of Activity (spec
"Control Center v1"; slice 4 "canvas Control Center face"). Surfaces are what users
look at; contexts are where invariants live; processes are what listen on a port. A
surface name must not be reused for a process, because doing so overloads it — which
is the exact failure that made the P1 author coin "TS host" rather than say "Control
Center serving." Keep Control Center as the surface; give the process its own name.

**Is the P1 TS host = "Control Center serving"?** **No.** The P1 host serves the
**Runtime** context (run lifecycle + terminal, a producer). "Control Center serving,"
read correctly, is the **Activity** context's read surface (a consumer). Different
context, different direction, different downstream coupling (Runtime → Python capture
RPC; Activity → Postgres records only).

**Relationship to Canvas / Inspector:** Canvas is the browser product shell that
hosts the Control Center surface (and the launcher and terminal panes). Inspector is
the frozen capture-plane product; its data stays Python. Both bundles are served by
the origin — Python in P1, the gateway at the target.

**Doc fix (recommended).** In `docs/ARCHITECTURE.md` "Two plane rule", the list
"Activity, Control Center serving, future Comms, Recall …" is a category error:
Control Center is Activity's surface, not a sibling context. Replace with the contexts
that actually serve — **Activity** and **Runtime** — and add a one-line "Product-plane
gateway" note describing the composition-root-plus-reverse-proxy origin. This removes
the ambiguity that spawned the "TS host" coinage.

---

## 4. Package topology

`docs/ARCHITECTURE.md` "Product package placement": *node service packages live under
the repo root `packages/*`; browser packages remain under `www/packages/*`.* This
**resolves P1's open Q6** ("new top-level `host/` vs `desktop/src/host/`"): **neither.**
The run host is a node service context and belongs at **`packages/runtime/`** as
`@tm/runtime`, in the canonical context shape (`packages/activity/src` already models
it):

| P1 spec §7 file (flat `host/src/*`) | Canonical home in `packages/runtime/src/` | Slot |
| --- | --- | --- |
| `RunHttpServer.ts` | `server/` | HTTP + SSE serving (the 5 routes + terminal WS) |
| `RunManager.ts` | `service/RunManager.ts` | use cases / actor orchestration |
| `terminal/ScrollbackRing.ts` | `domain/terminal/` | pure seq/byte-cap ring, no IO |
| `terminal/TerminalFanout.ts` | `service/` | multi-viewer attach orchestration |
| `terminal/PtyAdapter.ts` (port) | `ports.ts` (`PtyPort`) | input/output interface |
| `terminal/NodePtyAdapter.ts` | `adapters/` | port implementation |
| `capture/CaptureRpcClient.ts` | `adapters/` (impl of a `CapturePort` in `ports.ts`) | bind/release RPC to Python |
| `platform/JobObject.ts` | `adapters/platform/` | OS-specific adapter |
| `wire/terminalContract.ts` | shared contract package (crosses the TS↔browser boundary) | per the magic-string rule, single-sourced |
| RunStarted / RunExited | `events.ts` | facts this context emits (Runtime = producer) |

The flat `host/src/*` layout the spec sketched should be **reshaped into the canonical
domain/service/ports/adapters/server split** before it lands, so the run host is a
first-class `@tm/*` context like Activity, not a bespoke folder. The boundary rule
holds: other packages import only `packages/runtime/src/index.ts`.

The **gateway** is an *app / composition root*, not a bounded context, so it is not a
`@tm/<context>` package. Home it as `packages/gateway/` (a thin composition app) or an
`apps/`-style member when it is built. **P1 does not need the gateway** — Python is the
interim origin — so `@tm/runtime` is the only new package P1 must create. The terminal
wire contract wants a shared home now (a `packages/contracts` or `@tm/common`
addition) because it crosses into the canvas browser package.

---

## 5. Recommendation

**`distinct-run-host`.** The P1 "TS host" and "Control Center serving" are **not** the
same surface and must not be unified. Concretely:

1. **Name the P1 host the `Runtime` context**, `packages/runtime/` (`@tm/runtime`), in
   the canonical context shape. It is the RunStarted/RunExited producer the doc's
   context map already anticipates. Retire the ad-hoc "TS host / run host" phrasing.
2. **Read "Control Center serving" as the Activity read surface** (`@tm/activity`
   `src/server/`), backing the **Control Center** *surface* (Canvas face). Fix the
   `docs/ARCHITECTURE.md` two-plane list so Control Center is not listed as a sibling
   context of Activity.
3. **Introduce one product-plane gateway** as the target origin: a composition root
   that mounts `@tm/runtime` + `@tm/activity` routers, serves the canvas + inspector
   bundles, and reverse-proxies the frozen Python capture plane (exchanges, meta,
   `/v1/runs/{id}/stream`, breakpoint). P1's "Python stays the front door" is the
   interim seam; the origin flips to the gateway at the target.

**Rationale:** it obeys the two-plane dependency rule (producer never fused with its
consumer), matches the cohesion boundary (terminal/PTY/capture changes vs
status/rollup changes are different reasons to change, with different downstream
coupling), keeps "Control Center" meaning one thing (a surface), and gives the origin
the noun the doc is missing (a gateway) instead of overloading a surface name onto a
process.

**Where the other reviewer may disagree — `unify-as-control-center`.** A defensible
counter: the operator sees *one* Control Center; put run lifecycle + activity status
behind *one* serving process and call it "Control Center serving," reusing the name the
doc already blessed. My rebuttal: that fuses the Runtime producer with the Activity
consumer (banned by "Producers never import Activity"), and overloads a **surface**
name onto a **process**. The legitimate half of that view — *one origin* — is already
satisfied by §2.2's gateway, which co-hosts both context **routers** in one origin
**without** fusing the **contexts**. The disagreement collapses to: fuse the contexts
(reject) vs co-host their routers (accept). I accept co-hosting; I reject fusion. The
secondary axis of disagreement is purely naming — whether the origin should borrow
"Control Center" (I argue no: it reintroduces the exact ambiguity that produced the
"TS host" coinage) or take a neutral "gateway" (I argue yes).

---

*Author: opus, independent pass. All code claims verified against the current tree:
the single `control center` hit in `docs/ARCHITECTURE.md`; the three separate routers
in `main.py::create_app`; the 5 routes on `run_routes.router`; lifecycle emission from
`run_manager.py`; bundle serving in `mount_frontend_bundles`; the canonical context
shape in `packages/activity/src`. Proposal only; no code edited.*
