# TM ports: why fix the port at all? — architecture & product-fit brainstorm

Date: 2026-06-23
Author: backend-engineer (independent brainstorm, read-only; `git status` clean at `main` `e3aaecf`)
Angle: architecture & product fit against the North Star
Premise interrogated: `transport-matters desktop` dies with "web UI port 8788 already in use"
because the `stable` channel is already running on fixed ports. Owner stopped a detect-and-attach
/ free-port-fallback patch and asked: **why fix the port at all?**

Inputs read: `~/.mdx/projects/transport-matters-north-star.md`, `./NOW.md`,
`~/.mdx/projects/tm-ports-scout-port-allocation.md`. Code already mapped by the scout (not re-walked).

---

## TL;DR

Fixing the port is the wrong frame. The collision is a **symptom of a conflated verb**: the desktop
command treats "start the control plane" and "open a viewer onto it" as one action. The control plane
is a **singleton per channel**, and its fixed, well-known address is not a bug to route around — it is
the **contract the North Star depends on**. The right move is to make `desktop` idempotent per channel:
consult the singleton registry the repo already maintains, attach a viewer when the channel is live,
start only when it is not. Keep fixed ports for the control plane. Keep dynamic ports for runs. Do not
add free-port fallback; do not generalize channels to N.

---

## 1. Is fixing the port the real problem, or a symptom?

**Symptom.** The real problem is one tier up: **the desktop launch path conflates two verbs and ignores
the singleton it already tracks.**

The system has **two distinct tiers of port identity**, and they are governed by opposite rules on
purpose:

| Tier | What it is | Cardinality | Port rule | Why |
|---|---|---|---|---|
| **Control plane** (the backend + web UI per channel) | the *observer/manager* — the ONE | singleton per channel | **fixed, well-known** (stable 8787/8788, preview 8797/8798) | twin clients must reach one knowable address |
| **Runs** (captured agents in canvas panes) | the *managed* — the MANY | unbounded, ephemeral | **dynamically allocated** (`RunManager` → `allocate_port_pair`) | disposable, discovered via Observe, never addressed directly |

This tiering maps **exactly** onto the North Star. The director (voice → MCP/CLI) and the human (⌘K)
are "twin clients of one control plane." A singleton at a stable address is what makes "one control
plane" addressable at all. The runs are the "MANY agents/panes/runs" the control plane launches and
projects; dynamic ports are correct there, and `RunManager` already does it correctly.

So the apparent inconsistency in the question — "desktop pins ports but `RunManager` allocates them" —
is **not** an inconsistency. It is correct tiering. The defect is narrower: the desktop start path
does not consult `desktop_runtime.py:read_live_desktop_record`, the per-channel singleton registry the
repo already writes and already reads from `channel_cmd.py:list_channels`/`stop`. It collides on the
port instead of recognizing "this channel's control plane is already up."

**Conflated verbs.** `desktop` means both "ensure the backend is running" and "open an Electron window
onto it." Running it twice should be idempotent on the first verb and additive on the second: ensure-up
is a no-op when up, attach-viewer can repeat. The fixed port is fine. The missing concept is
**ensure-then-attach** keyed on channel identity.

## 2. Why fixed ports are aligned with the North Star (not legacy debt)

"API-first, the UI is one client of two" forces a stable control-plane address into existence:

- The **director** is configured to reach the backend over MCP/CLI. A constant port is the simplest
  possible service discovery: a literal. Dynamic control-plane ports would push runtime discovery onto
  the anchor service — the one thing in the system that must be trivially reachable.
- The **human** browser/Electron loads a known URL (`www/vite.config.ts` proxies dev to 8788;
  `window.ts:rendererUrlForPort`). Randomizing it means every client scans a range to find "the" backend.
- **Observe** must be unambiguous. One backend per channel = one DB, one set of runs, one truth. Two
  backends on two ports (free-port fallback) = split-brain: two DBs, two run sets, and a director that
  cannot tell which is canonical. Note #168/#169 just hardened **test DB isolation** — the project is
  actively defending the "one store, isolated per channel" invariant, not relaxing it.

Fixed control-plane ports are the contract. The dynamism the system needs already lives exactly one tier
down, in runs.

## 3. Is "two channels" the right unit?

Yes, and it is a different question from ports. `stable`/`preview` is a **dogfooding isolation boundary**
(`docs/CHANNELS.md`): stable is the trusted daily driver, preview runs the working tree with isolated
home, DB, ports, and Electron identity. Cardinality two is not arbitrary — it is the trusted build plus
the build under test, a real single-user workflow. Each channel is itself a singleton control plane;
the channel is the isolation key (home + DB + ports + Electron identity), and the director does not care
about channels as a product concept. The port is *derived from* the channel; the channel is the identity.

Generalizing channels to N arbitrary instances would solve a problem no single-user has and would
explode the URL/dev-tooling/test contracts the scout enumerated (vite proxy, `channel-specs.json`,
`config.py` defaults, `CHANNELS.md`, a dozen test files). Out of scope, and against the grain.

## 4. Options + trade-offs

**A. Idempotent ensure-then-attach, keyed on channel (recommended).**
Desktop start consults the live desktop record first. Live + healthy channel → attach a hosted Electron
viewer to the existing backend URL (`spawn_detached_electron` already supports this). Stale record →
normal start. Unrelated process on the port → keep the precise port-conflict error.
*Pros:* uses machinery that already exists; fixes the actual UX (re-launch just works); preserves the
singleton contract and Observe's single source of truth; directly instantiates "the control plane is one
thing both clients reach." *Cons:* must define "attach vs refuse" default and a health/staleness check
(both already have helpers: `wait_for_port_ready`, `isBackendHealthy`).

**B. Free-port fallback for the control plane (the stopped patch — reject).**
*Pros:* `desktop` never errors. *Cons:* breaks the singleton contract; split-brain DB/runs; forces
client-side discovery of the anchor; contradicts the North Star's "one control plane"; undermines the
#168/#169 isolation work. This is dynamism applied to the wrong tier.

**C. Better error string only (insufficient).**
*Pros:* trivial. *Cons:* operator still stuck; describes the wall without opening a door. Leaves the
common "already running" case unrecoverable. A clearer message is a *byproduct* of A (the refuse branch),
never the whole fix.

**D. Generalize channels to N dynamic instances (reject — solves a non-problem).**
*Pros:* none for single-user. *Cons:* blows up every fixed-address contract; turns a deliberate
dogfooding boundary into arbitrary instance sprawl; pushes discovery everywhere.

## 5. Recommendation

**Option A.** Reframe the failure from "port allocation" to **singleton lifecycle**. The control plane is
a singleton per channel; `desktop` should mean "ensure the channel's control plane is up, then attach a
viewer." Concretely: consult `read_live_desktop_record` at the front of the desktop start path; on a
live, healthy channel attach a hosted viewer to the existing URL; on a stale record start normally; on an
unrelated listener keep the existing precise port error. Keep control-plane ports fixed (they are the
contract). Keep run ports dynamic (`RunManager` is already correct). The identity model needs no new
concept: **channel is the singleton key, the desktop record is its registry, runs are sub-identities
under it.** The machinery exists; it is simply not consulted on start.

Why this is the right thing and not a patch: it removes a category error (treating a singleton's stable
address as a resource to reallocate) and replaces it with the verb the North Star already implies
(ensure-then-attach onto one reachable control plane). It is the smallest change that makes the product
behavior correct *and* leaves the architecture more coherent than before.

## 6. What I would NOT do

- **Would not add free-port fallback to channel desktop start.** It breaks the singleton contract,
  creates split-brain DB/state, and forces every client to discover the anchor service. This is the patch
  the owner correctly stopped.
- **Would not make channels dynamic or generalize to N instances.** Two channels is a deliberate
  dogfooding boundary, not an arbitrary cap. Generalizing explodes the fixed-address contracts for zero
  single-user benefit.
- **Would not ship only a better error string.** Recovery behavior (attach, or refuse with the live URL
  and pid) is the product fix; the message is a side effect of it.
- **Would not collapse stable/preview into one channel.** The isolation (home + DB + ports + Electron
  identity) is real and is being actively hardened.
- **Would not duplicate port semantics further.** If anything, fold the desktop path's separate
  `_resolve_backend_ports` toward the shared seam over time, but that is cleanup, not the fix.
