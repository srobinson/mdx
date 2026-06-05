# Canvas director road-test: design review for adoption

Owner-facing writeup for Stuart. Sources: scout map
(`tm-controlplane-s7-canvas-director-scout.md`) and the locked control-plane
spec (`CONTROLPLANE.md`). This is a product decision brief, not a reuse map.

**Decision in front of you:** adopt a narrow Canvas change so a human can spawn
a *director* pane that already has authenticated control-plane tools, then
road-test multi-agent drive from that pane. The verbs and trust model are
already built; the missing piece is one spawn-time grant propagation path.

---

## 1. What it enables

You open Canvas, choose the director affordance when launching a pane, and that
agent arrives with workspace-scoped authority over peer runs. From its own
session it can list agents, launch more, prompt (including fan-out), read a
peer's transcript to summarize, watch for state changes, interrupt mid-turn,
and stop a run.

That is the first concrete slice of the Northstar director vision: a human
speaks (or types) on a director pane; the director drives the canvas through
the same operations the product already implements for agents. No separate
control surface for agents; one service, MCP as the agent skin.

---

## 2. End-to-end flow

1. **Canvas `director` affordance.** Spawn stays spawn-scoped: a three-state
   control (off / observer / director) on the launch path. Selecting director
   does not change global settings; it only tags that create request.
2. **POST body carries `controlPlaneGrant=director`.** The browser threads the
   field through the existing captured-run pipeline into `POST /v1/runs`.
   Default when omitted remains `none` (today's behavior).
3. **Backend mints a workspace-scoped director grant.** Capture prepare sees
   the grant, fails closed if persistence fails, stores only the token digest,
   and binds role + workspace identity to the run.
4. **Control-plane MCP is seeded into the run home.** Claude gets `.mcp.json`
   (plus invocation flags); Codex gets the run-local MCP server entry. The raw
   bearer lives only in that home, never re-exposed on later APIs.
5. **Director tools are live, scoped to that workspace's runs.** Every MCP call
   resolves bearer → run → grant per request. Tool arguments never establish
   identity. The director can drive peers in its workspace; nothing outside.

Service-launched children still adopt into Canvas via the existing activity
reconciler (already shipped). The road-test stays on the run-scoped MCP
principal from first spawn through every action; the human REST / palette
control-plane client is not required for this scenario.

---

## 3. The seven capabilities

| Capability | What the director does | Verb |
|---|---|---|
| List / state | See who is live and how they are tiered (working, idle, needs you, stalled, exited) | `roster()` / `workspace_summary()` |
| Launch | Start another captured run in the workspace (optional child grant: none / observer / director) | `launch(...)` |
| Prompt (incl. fan-out) | Send the same text to one or many runs; nudge (next turn) or interrupt (break then submit) | `prompt(targets, text, mode)` |
| Read transcript to summarize | Pull a filtered conversation (tools/thinking stripped); `shape="summary"` for a cheap cut | `conversation(run_id, shape="summary")` then the director synthesizes |
| Watch | Subscribe to turn completed, state changed, or needs you for a run or the whole workspace | `watch` / `unwatch` |
| Interrupt | Break mid-turn without new text (steering text uses `prompt` in interrupt mode) | `interrupt(run_id)` |
| Kill | Terminate a run (TERM → grace → KILL, PTY and capture release) | `stop(run_id)` |

All seven already exist behind the MCP skin. They become usable from Canvas
only after the pane receives an authenticated director grant at spawn.

---

## 4. Trust posture

**Grants default OFF.** A normal Canvas agent has no control-plane MCP config
and no peer authority. That is intentional and remains the default after this
work.

**Roles**

| Role | May do |
|---|---|
| none | Capture only; no control plane |
| observer | Observe + watch |
| director | Observe, watch, prompt, launch, manage (interrupt / stop) |

**A director CAN**

- Act only inside the grant's workspace (canonical slug/hash identity).
- Prompt, launch, interrupt, and stop runs visible in that workspace.
- Delegate by launching a child with a narrower or equal grant.
- Leave an audit trail: every action is attributed and persisted with the same
  shape used for humans.

**A director CANNOT**

- Reach other workspaces (cross-workspace grants are a later model, same shape).
- Self-declare identity (token is minted at spawn; skins receive a resolved
  principal only).
- Get a mid-run promotion (grants are launch-time; change means next launch).
- See raw peer PTY scrollback via control plane (transcript projection only;
  no server-side semantic summary; the director writes the summary).
- Rely on "prompt someone and automatically get woken when they reply" without
  an explicit watch (see deferred).

**Workspace boundary** is the hard product edge for the road-test. Visibility
and action scope are the grant's `workspace_id`, the same key activity already
uses.

---

## 5. Explicitly deferred (edges the owner should see)

These are parked on purpose, not accidental holes.

| Item | Status | Why it is OK for the road-test |
|---|---|---|
| **B1 reciprocal auto-wake** | Deferred (slice 22 / durable causal damping). Prompting a peer does **not** register an automatic wake-back path. | Director calls `watch("workspace", …)` before fan-out, or polls `roster` / `conversation`. Explicit WATCH push already works once subscribed. |
| **Self-mint gate on `POST /v1/runs`** | Ungated today: any local create can request `controlPlaneGrant=director`. | Acceptable for single-user desktop. Harden later with human auth so only a real operator (or a further policy) can mint the first director. |
| **Human ⌘K / palette control-plane auth** | Entirely parked for this scenario. | Road-test uses the MCP principal on the director run, not the human REST skin. Twin skins remain the architecture; this PR does not unblock palette REST as a prerequisite. |

Also still later (from the locked design, not blocking this road-test): CLI
skin, cross-workspace directors, rename / breakpoint / spend as manage verbs,
runtime grant toggle, judge/eval over `dispatch_id` groups.

---

## 6. Limitations to road-test around

1. **Watch is opt-in.** After fan-out, if you care about "peer hit needs you,"
   subscribe first. Do not expect prompt origin to create reciprocal wake.
2. **Conversation is transcript-shaped, not terminal-shaped.** Summaries are
   director-side synthesis over filtered messages; no raw PTY dump, no
   server-written narrative.
3. **Delivery receipts are honest but mechanical.** `delivered` means the PTY
   accepted bytes, not that the harness finished the work. `unknown` means the
   gateway broke mid-request; no silent retry.
4. **Subscriptions die with the API process**, same lifetime as runs. Restart
   clears watches; re-subscribe after restart.
5. **First director still needs the Canvas grant affordance.** Backend already
   accepts `controlPlaneGrant: "director"`; without the browser thread, the
   normal product path cannot mint the first director (handcrafted create can
   prove the backend only).
6. **Adoption of service-launched panes** depends on the existing Canvas
   reconciler; verify in the live desktop that a director-launched child
   appears as a pane.

---

## Adoption recommendation (for the road-test PR)

Ship the **one propagation gap**, nothing else:

- Shared grant vocabulary on a browser-safe contract surface.
- Thread `controlPlaneGrant` from launcher command → create body (default
  `none`).
- Three-state spawn affordance (off / observer / director).
- Contract tests at the real seams; keep B1 and human auth out of the PR.

Then road-test on desktop Canvas: director pane → MCP present → roster,
launch, fan-out prompt, conversation summary, workspace watch, interrupt,
stop → confirm child adoption.

**Verdict for Stuart:** the control plane already implements director power
under a fail-closed, workspace-scoped grant model. Adopting the Canvas
affordance unlocks the live multi-agent story without widening trust defaults.
The edges (no auto reciprocal wake, ungated local mint, no human ⌘K path yet)
are explicit and acceptable for a single-user road-test if you treat them as
known constraints rather than surprises.
