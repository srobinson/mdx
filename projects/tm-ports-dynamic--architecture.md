# TM ports: steelmanning the DYNAMIC control-plane model against the North Star

Date: 2026-06-23
Author: backend-engineer (independent, read-only @ main `e3aaecf`; `git status` clean)
Brief: make the strongest HONEST case FOR dynamic control-plane ports, tie it to Spaces and the
director-spawns-many model, and sequence it. Cites are path+symbol (no file:line).
Companion: `tm-ports-why--architecture--brainstorm.md` (round 1), reconciliation on bus `tm-ports-why`.

---

## TL;DR

Dynamic is the right **long-term destination** as an **additive, discovery-backed INSTANCE concept
that sits alongside** fixed well-known channels, not as a replacement for them. It is **not required
today**: Spaces partitions runs *within one* control plane, and those runs already use dynamic ports;
the director that would spawn many control planes is deferred. The single thing that gates dynamic is a
**client-facing discovery seam** (generalize `cli/desktop_runtime.py::read_live_desktop_record` into a
queryable instance registry). Build the seam, ship idempotent launch on top of it, and leave the dynamic
flip as an additive option.

---

## 1. API-first lens: does "twin clients of one control plane" prefer discovery?

**Steelman for discovery (the honest strong case).** The deepest API-first claim is that clients
*discover* the system rather than *hardcode deployment facts* about it. A fixed well-known port is a
deployment fact baked into clients. The clearest tell is in the repo: `www/vite.config.ts::server.proxy`
literally hardcodes `localhost:8788`, and `desktop/src/window.ts::DEFAULT_WEB_PORT` ships a port constant.
A discovery seam is **strictly more general**: a discovery call that returns a constant *is* a fixed port,
whereas a fixed port is a discovery seam that has thrown away its generality. By the API-first lens,
discovery is therefore the principled mechanism and "well-known port" is one answer it can return.

The decisive asymmetry: the moment control-plane cardinality exceeds one-per-channel, a single fixed port
**cannot** address the instances at all. Discovery is the only mechanism that scales across N; fixed is the
degenerate case that works only at N=1.

**Honest counter (why fixed is not actually a violation today).** A well-known port is a legitimate,
battle-tested contract: `:443`, `:5432`, `:6379`. It is a transport address, not business logic, so it does
not breach the North Star's real rule ("operations live in the API, never the UI"). For a single-user tool
at one-or-two instances, a constant is the simplest possible discovery and costs almost nothing. Fixed
becomes a latent violation **only** if cardinality grows while clients still assume the constant. Today that
risk is dormant and confined to two client constants (the Vite proxy and the Electron fallback).

**Verdict on Q1:** API-first mildly prefers discovery as the general mechanism, but a well-known port is a
legitimate simplification at current cardinality. The latent debt is the two hardcoded client constants,
not the concept of a known address.

## 2. What dynamic enables that fixed forecloses

- **N control planes beyond the hardcoded two.** `channel.py::ChannelSpec` pins `stable`/`preview`; dynamic
  removes the cap.
- **A director spawning many isolated TM instances** — per-project, per-eval-rig, per-experiment fabrics,
  each with its own DB, capture root, and failure domain. This is the North Star's "director launches many"
  applied to the control plane itself, and fixed ports collide the instant you want two.
- **Zero collision-class.** The entire "web UI port 8788 already in use" bug category disappears: every
  instance gets a free pair from `cli/ports.py::allocate_port_pair`.
- **Hard per-Space / per-worktree isolation** *if* a Space ever needs to be its own process rather than a
  soft partition.

**Honest tie to Spaces (the claim I refuse to overstate).** Spaces as built does **not** push toward many
control planes. `run_manager.py::RunManager` is a **singleton** on `main.py::app.state.run_manager`
(constructed via `run_routes.py::create_run_manager`); `space_id`/`worktree_id` are **run keys** on
`run_models.py` and `captured_run_models.py`, and `RunManager` imports `transport_matters.space.models` to
*partition runs*, not to fork backends. The "many" in Spaces is **many runs under one control plane**, and
those runs **already** receive dynamic ports through
`captured_run_dependencies.py::allocate_port_pair` → `captured_run.py` → `run_manager.py::RunManager`. So
the dynamic-port machinery is already proven at the run tier; Spaces exercises it there.

Therefore fixed two-channel is a dead end **only on the many-control-planes axis**, and Spaces has not
reached that axis. The steelman for dynamic *control-plane* ports rests on the **future**
director-spawns-many-instances trajectory, which the North Star explicitly **defers** ("we do not pre-decide
the director's behavior; current focus: the UI adapter surface only"). Spaces makes that trajectory *more
plausible* (it is investing in isolation identity), but it does not *force* it yet.

## 3. Cost / risk of dynamic

- **Build a discovery layer.** A registry plus client-side resolution is real, non-trivial work and new
  failure modes (stale entries, discovery races, registry as a new source of truth to keep honest).
- **Lose human-memorable URLs.** `8788` is typeable for `curl`, dev, docs, and `docs/CHANNELS.md`; a random
  port is not. Dev friction is real and recurring.
- **More moving parts** on the one service that must be trivially reachable.
- **The singleton-per-channel invariant: preserved or lost?** Preserved **iff** dynamic is *additive* —
  keep "channel = singleton at a known port" as the default and add "instance = dynamic + discovered" as a
  new concept. **Lost** if channels themselves go dynamic: then `stable` has no stable address, the Vite
  proxy and `DEFAULT_WEB_PORT` and `CHANNELS.md` all break, and the dogfooding contract evaporates. The
  scout reached the same shape: model dynamic as a distinct instance concept with explicit URL discovery,
  never as silent channel fallback. Idempotent launch already guarantees one-backend-per-channel, so
  split-brain is foreclosed by launch discipline regardless of whether the port is fixed or dynamic.

## 4. Honest verdict + sequencing

**Verdict.** Dynamic, in its *safe additive form* (a discovery-backed instance concept beside fixed
well-known channels), is the right long-term destination, and it becomes mandatory the day the director
spawns more than one isolated control plane. It is **not** correct to flip today: the requirement is not
real, and fixed channels remain the human-memorable default even after dynamic lands. Fixed for now,
dynamic as destination, discovery as the bridge.

**What must exist before dynamic is safe.** A client-facing discovery seam. Today's substrate is partial:
`cli/desktop_runtime.py::read_live_desktop_record` is a per-channel filesystem record consumed only by
`channel_cmd.py` (list/stop), and `api/v1/meta` resolves the placeholder cwd, not the control-plane address.
No palette/director-facing surface enumerates or resolves running control planes.

**Clean order (each step ships value independently):**

1. **Discovery seam (the gate).** Generalize `read_live_desktop_record` from a per-channel record into a
   queryable instance **registry**, and expose enumerate/resolve to clients (the palette and the future
   director). This is the prerequisite; nothing dynamic is addressable without it.
2. **Idempotent desktop launch (already converged, ship now).** The first consumer of the seam: consult the
   registry, attach a viewer when the channel is live, start when not. In the same pass, retire the latent
   client constants — make `vite.config.ts` read the port from env/registry, keep `DEFAULT_WEB_PORT` as a
   pure fallback. This removes the collision UX and the API-first smell without any dynamic flip.
3. **Optional dynamic flip (additive, deferred).** Allow `cli/ports.py::allocate_port_pair` for a new
   *instance* launch concept behind a flag, addressed through the registry, while `stable`/`preview` keep
   their well-known ports as defaults. This lands only when the director-spawns-many requirement is real.

**Single prerequisite that gates dynamic:** a client-facing discovery seam generalizing
`cli/desktop_runtime.py::read_live_desktop_record` into a queryable instance registry. Build that, and
dynamic stops being a category error and becomes a config flag.

## What I would still NOT do

- Make **channels** dynamic (breaks dev tooling, human memory, the dogfooding contract).
- Flip dynamic **before** the discovery seam exists (unaddressable instances).
- Treat Spaces as a forcing function for many control planes (it partitions runs under one).
- Use dynamic to *fix the collision* (idempotent launch does that; dynamic is a capability axis, not a
  collision patch).
