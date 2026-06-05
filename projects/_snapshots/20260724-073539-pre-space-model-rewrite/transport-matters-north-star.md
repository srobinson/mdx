# Transport Matters — North Star: the director-operated agent fabric

Date: 2026-06-18
Status: NORTH STAR (the lens; not a slice plan)
Owner: Stuart (what/why), Claude (how)
Bus topic of record: tm-launcher-proposal (launcher seam) · this doc is the umbrella vision
Related: `~/.mdx/projects/tm-launcher-design.md` (§11 decomposition, launch data-model) ·
`~/.mdx/projects/tm-ui-component-strategy.md` (Ark UI palette) ·
`~/.mdx/research/2026-06-local-voice-chat-realtime.md` (voice intake, deferred) ·
cm decisions (`north-star`, `provider-taxonomy`, `agent-first launcher`) · repo `NOW.md`

---

## The vision

**The human operates agents by voice.** They speak intent; a **director agent** —
addressed over **MCP or CLI** — holds full context of every workspace, canvas, and
pane, and knows how to **launch, manage, and prompt** the specialist agents running
inside Transport Matters. The desktop is where you *watch* the fabric work; control is
conversational, not click-by-click.

This is the destination the launcher, the ephemeral homes, and the capture substrate
are all stepping stones toward. It is `tm-launcher-design.md §11` ("a director delegates
to specialist ephemeral agents") made the organizing principle rather than a footnote.

## The principle it forces: API-first, the UI is one client of two

The **director** (voice → agent → MCP/CLI) and the **human** (⌘K palette) are **twin
clients of one control plane**. Anything the human can do through the UI, the director
must be able to do programmatically. Therefore operations live in the **API**, never in
the UI. The palette *renders* the control plane; the director *drives* it. No UI-only
logic, ever.

This single constraint is the lens. It is a gift: it forbids the most common desktop
mistake (business logic trapped in the renderer) and makes every capability reusable by
machine and human alike.

## The control plane: four verbs

Every TM control capability is one of these, exposed as an API (REST/WS for the human
client, MCP/CLI for the director), sitting on the same domain services
(`api/.../run_manager.py::RunManager`, the session store, the canvas projection):

- **Observe** — read workspaces / canvases / panes / runs with live state and recent
  transcript. This is the director's "full context."
- **Launch** — `spawn(agent → harness/vendor/model/effort, placement)`. The launcher,
  expressed as an API. Extends `api/.../api/v1/run_routes.py::CreateRunRequest`.
- **Manage** — interrupt / detach / terminate / arrange / focus.
- **Prompt** — inject a turn/input into a running agent's run. The director *talks to*
  agents, not just launches them. New first-class verb.

## Structural consequences (what the lens forces into existence)

1. **A server-side canvas/pane projection.** `NOW.md` (B6 spec D2 / resume-S6 gate) parked
   canvas layout as client-side zustand (`www/src/session-canvas/model/canvasStore.ts`)
   *until a consumer exists beyond one browser profile*. **The director is that consumer.**
   Pane/canvas state needs a server-readable projection — keyed by `workspaceId`, capture
   ids as soft refs, a projection/sync-target (not necessarily the owner) — exactly the
   shape D2 sketched. This unparks on schedule, not as scope creep.
2. **A TM control MCP/CLI — a new bounded context (the director's hands).** An MCP server
   (and `tm` verbs) over `RunManager` + sessions + the canvas projection, exposing
   observe/launch/manage/prompt. Distinct surface from the human REST/WS, same operations
   underneath. It mirrors the helioy-bus/warroom pattern turned inward onto TM's own runs.
3. **The launch request carries the full target.** harness/vendor/model/effort + placement
   (per the `provider-taxonomy` decision), so the director and the palette specify a spawn
   identically.

## The lens — apply to every architectural and design decision

Before shipping any operation or surface, it must pass:

1. **Is it an API the director can call, or is it trapped in the UI?** If UI-only, it is
   not done.
2. **Can the director *observe* the state this produces?** If it mutates the fabric, the
   change must be readable through Observe.
3. **Is the human UI a thin client of the same operation, or a parallel implementation?**
   Parallel implementations are a DRY failure and a lie the director will trip over.
4. **Does it respect the bounded contexts?** TM owns runs + capture + control. It does
   **not** own the director's cognition (that is a client) nor agent curation (that is
   agent-runtimes, behind the `capabilities.json` seam).
5. **Does it keep the zero-config path fast?** The voice/recommendation-default path is
   the 99% case; overrides and evals are progressive disclosure, never a tax on the
   common spawn.

## How current work instantiates the lens

- **⌘K launcher palette** = **client #1 of the Launch verb.** Agent-first,
  recommendation-default, `↵` spawn / `→` expand. The job is to build Launch as an API the
  director inherits, not "palette UI."
- **Provider taxonomy** (harness/vendor split) = the Launch verb's target vocabulary.
- **Desktop = zero-chrome canvas.** You watch the fabric; control is ⌘K (human direct) +
  voice→director. No persistent button row. (A faint, fading first-run ⌘K hint softens
  discoverability without adding chrome.)
- **Ephemeral homes (Slices 1–4, merged)** = the disposable specialist agents the director
  launches; durable history in Postgres is the Observe substrate.
- **Wire/transcript capture** = the audit + replay layer the director's Observe reads;
  it stays TM's core mission, the control plane sits on top of it.

## Sequencing discipline

We do **not** pre-decide the director's behavior. The prerequisite layers (control-plane
operations, the UI adapter, the canvas projection) get built first; the questions of what
the director can / should / should not do resolve in natural order as that substrate lands.
Deciding them early would be guessing without the layers that make the answer obvious.

**Current focus: the UI adapter surface only** — the human ⌘K palette / launcher / canvas
as **client #1** of the control plane, built API-first so later adapters inherit the
operations. Voice-to-text is a much-later, separate adapter.

## Resolved leans

- **Director locus = C (hybrid), ratified.** The director is always a *client* of the
  control plane, never TM internals. The shipped default director is a **fleet home** (a
  director skill in agent-runtimes whose required capability is the TM control MCP); the MCP
  stays open for BYO directors and eval rigs. TM core builds only the control plane; the
  director is a fleet member, swappable.

## Deferred by design (resolved as prerequisite layers land)

- **Prompt scope** — launch + first prompt vs boundary-gated later turns vs full
  puppeteering. Design *intent* when it arrives: turn-oriented (deliver a turn to run R at a
  safe boundary), TM-mediated and provenance-stamped, with byte-level PTY as the human's
  attach escape hatch. Not decided now.
- **Voice intake** — a later adapter feeding the director; client/OS dictation vs TM-built.
  Research: `~/.mdx/research/2026-06-local-voice-chat-realtime.md`. Orthogonal to the
  backend, out of current scope.
- **Intent channel** — `tm-launcher-design.md §11`'s "internal bus" (explicit aggregate)
  vs a projection over capture. Resolves once Prompt's shape is real.

## What this is NOT

- Not TM absorbing the director's brain — the director is a swappable client.
- Not TM absorbing agent curation — that stays agent-runtimes behind the seam.
- Not a replacement for the capture mission — Observe is built *on* the wire/transcript
  TM already owns.
