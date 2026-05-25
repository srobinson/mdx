# littleorgans Build Plan and Sequencing Roadmap

> **What this is:** a sequencing roadmap across the matters family, the "what gets worked on
> when." It is deliberately at milestone altitude, not line-level TDD. Each phase becomes its
> own granular implementation plan (the executable unit) when we start it, drilled against the
> real crates. Companion to `~/.mdx/projects/littleorgans-cockpit-architecture.md`.

**Goal:** Stand up the cockpit control tower in dependency order, primitives before consumers,
with schedule-matters as the near-term focus.

**Sequencing principle:** build bottom-up. A layer is only built once the layer it sits on is
real. Dependencies point down (per the architecture doc), so the build order is the tower read
from the floor up.

---

## Build-state snapshot (ground truth, 2026-05-31)

| Layer | State | Evidence |
|-------|-------|----------|
| runtime-matters (rm) | **exists** | `lilo-rm-core`: spawn, nudge, capture, lifecycle, target validation |
| session-matters (lilod) | **exists** | `internal/session`: mail, messaging, daemon with reconcile / lifecycle / spawn_request / events |
| wire, port, db, identity | **exists** | `internal/{wire,port,db,identity}` |
| lilo CLI | **exists** | session cmds: run, create, get, delete, label, mail, nudge, capture, logs, wait, mcp; substrate namespaces: runtime / session / identity |
| agent-matters | **exists, separate repo** | `agent-matters/` catalog + resolve/compile/use; Codex+Claude adapters only |
| transport-matters | **exists, separate repo** | capture backbone, migrating in |
| schedule-matters | **greenfield** | no tmux / pane / placement code |
| orchestration-matters | **greenfield** | — |
| workflow-matters | **greenfield** | — |

Note: the drive-and-tail surface already exists and is clean. `lilo` exposes **mail, nudge**
(drive), **capture, logs** (tail), and **wait** (condition) as unified **session commands**.
The runtime namespace is the raw substrate beneath them: "runtime spawn never creates session
records." So schedule-matters and orchestration build on an existing primitive surface; there
is no consolidation task. `wait` is worth flagging now as the condition primitive orchestration
gates will use.

---

## Two tracks

The work splits into two mostly-independent tracks that converge late.

- **Control track:** schedule-matters → orchestration-matters → workflow-matters. Drives agents.
- **Read/UI track:** transport-matters (capture) → SQL read model → cockpit GUI. Shows agents.

agent-matters feeds the control track (roles). The tracks converge at orchestration (needs roles
and the read path to observe agents) and at the cockpit (shows orchestrated sessions).

```
 control:   [P1 schedule] → [P4 orchestration] → [P5 workflow]
                 ▲                ▲
 roles:     [P3 agent-matters integrate]
 read/UI:   [P2 transport capture → SQL] ───────────→ [P6 cockpit + shell decision]
```

---

## Phase 1 (near-term focus): schedule-matters

The multiplexing and placement primitive. Build on the existing runtime spawn/nudge/capture and
the lilod reconcile/lifecycle patterns. Each work item below is a milestone, not a step.

1. **tmux integration.** Create and own tmux session / window / pane via control commands,
   driving and reading agents through the existing session primitives (mail, nudge, capture).
   Acceptance: schedule-matters can create a session, add windows and panes, and list them by
   stable id.
2. **Stable-ID model, never positional.** A schedule-matters pane UID in the store, bound to the
   live tmux `%pane_id`; positional `s:w.p` derived for display only. Acceptance: a window
   insert/delete leaves every occupant binding intact.
3. **Occupant binding.** Bind an opaque occupant token to a pane UID. Acceptance: an agent placed
   in a pane is found by token after arbitrary window churn.
4. **Placement authority.** Route `lilo run` through schedule-matters (replace today's direct
   spawn). Acceptance: no path places an agent into a pane except schedule-matters.
5. **Thin session manifest + reconciler.** The declarative multi-agent topology (identity +
   topology only), reconciled into tmux. Model on the existing lilod `reconcile`. Acceptance:
   `lilo create session` applies a manifest; schedule-matters materializes and owns it.
6. **Pane-death event.** Detect a killed pane, emit `orphaned(token)`, no policy decision.
   Acceptance: killing a pane surfaces an orphaned event to watchers.
7. **restartPolicy seam (Never only).** restartPolicy lives on the agent record; Never is the
   only behavior built now. The Always/resume hook is stubbed for orchestration to fill in P4.
   Acceptance: a bare `lilo run` agent dies with its pane; the resume hook exists, unimplemented.

Decision gate inside P1: none blocking. Output: schedule-matters owns placement end to end.

---

## Phase 2: transport-matters capture (read/UI track)

Migrate transport-matters in and stand up the cockpit's read pipeline. Independent of P1, can run
in parallel.

- Migrate the capture backbone (transcripts over wire) and the transcript service (CLI jsonl
  tail) into littleorgans.
- Normalize into the canonical model; write to SQL.
- Stand up the hourly/nightly schema-CI build that tracks CLI version and transcript schema drift.
- Per-CLI transcript adapters: claude first, then codex, gemini, opencode.

Decision gate: **per-CLI resume semantics** (does `--resume` continue or fork the jsonl) is
resolved here, in the adapters.

---

## Phase 3: agent-matters integration (roles)

Bring the role compiler into the control track.

- Migrate / wire agent-matters (catalog, resolve → compile → use) so littleorgans can consume it
  programmatically, not only via its CLI.
- Add the missing runtime adapters: **gemini and opencode** (today only Codex and Claude).
- Collapse the per-CLI adapters into **one declarative table** `{agent, config_dir, hook_file,
  hook_format, events, version}` feeding install, launch, and state detection (herdr
  `integration/mod.rs` + cmux `AgentHookDef`); agent-matters owns provisioning, runtime-matters
  the launch adapter.
- Wire the instantiation chain: agent-matters compiles a fingerprinted runtime home, `use`
  activates it, schedule-matters launches the CLI against it. Launch stays with schedule-matters.
- Carry the role fingerprint into the agent's durable identity so resume can restore the exact
  environment.

Decision gate: **agent-matters its own design session** before this phase is drilled (the
catalog/profile model, JIT resolve, security-policy-to-settings compilation).

---

## Phase 4: orchestration-matters (conductor)

The first real consumer of resume and of cross-agent sharing. Build on P1 (placement) + the
clean primitive surface (tail/nudge/mail) + P3 (roles).

- The orchestrator spec: sessions + agents + configs. Produces schedule-matters requests.
- The conductor loop: tail participants, nudge/mail each per the pattern's gates.
- Formalize the warroom patterns as the pattern vocabulary (peer-consensus first).
- Composable units: agent or sub-orchestrator; the JIT-profile standup is itself a
  sub-orchestrator; enforce the acyclic-at-runtime rule.
- **Build restartPolicy Always here** (native `--resume`), filling the P1 seam.

Decision gate: the **cross-agent transcript sharing brainstorm** (architecture doc section 13)
should land before or early in this phase, since it is the read substrate orchestration stands on.

---

## Phase 5: workflow-matters

The DAG above orchestration. Smallest of the control layers if the layers below are clean.

- The thin DAG of orchestrators: flow + message interchange between them.
- Ride the existing linear-workflows contract. No new format.
- Trigger relationship both directions (workflow ↔ orchestrator), acyclic at runtime.

---

## Phase 6: cockpit and the shell decision (read/UI track)

- **Decision gate first: shell technology** (Electron vs Tauri vs native), with the mass-market
  weights re-applied (architecture doc section 10). Blocks GUI build.
- Build the graphical cockpit on the SQL read model from P2.
- Mass-market default surface plus the first-class raw-pane escape hatch.
- Curated orchestrations (parameterized templates) as the mass-market entry to P4/P5.

---

## Critical path and what to start now

Critical path to a usable control plane: **P1 → P3 → P4**. P2 runs alongside and is the
prerequisite for any GUI. P5 and P6 follow.

Start now, in P1, in this order: item 1 (tmux integration), item 2 (stable-ID model), item 3
(occupant binding). Those three are the load-bearing core; 4 through 7 build on them.

**Next drill-down:** turn Phase 1 into a granular TDD implementation plan, modeled on the
existing `internal/session` reconcile and `lilo-rm-core` spawn patterns. That plan is the
executable unit and needs a read of those crates first.
