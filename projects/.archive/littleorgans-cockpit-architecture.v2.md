# littleorgans: Cockpit and Session Architecture

Status: living draft. Started 2026-05-30, model captured 2026-05-31. Owner: Stuart. Locks what
is decided, marks what is open. Companion to `~/.mdx/research/electron-vs-tauri-2026.md`,
`~/.mdx/research/helioy-electron-baseline.md`, and `~/.mdx/projects/helioy-product-direction.md`.
Prior versions in `.archive/`.

---

## 1. Product thesis

littleorgans is a **mass-market graphical cockpit that drives multiple terminal-based agent
CLIs** (claude, codex, gemini, opencode) running under a multiplexer. The market gap it fills:
the existing agent multiplexers (cmux on ghostty, herdr as a Rust TUI) are developer-targeted
terminal tools. littleorgans targets the non-technical mass market with a graphical surface
over the same agent CLIs.

Two audiences, two tiers, one control plane:

- **Mass market (default):** a graphical app. The agent's work is rendered as structured
  output, not raw terminal. The human picks curated orchestrations; they do not author specs.
- **Power user (escape hatch, first-class):** the raw terminal pane, tmux, the `lilo` CLI, and
  hand-authored orchestrator and workflow specs. Always one keystroke away, a designed feature.

---

## 2. The layer stack

```
   Graphical cockpit          the human surface (curated for mass market)
        ▲
   workflow-matters           thin DAG of orchestrators: flow + message interchange between them
        ▲  triggers / is triggered by
   orchestration-matters      conducts a coordinated multi-agent session; expert client of the
                              layers below; spec = sessions + agents + configs
        ▲  composes
   agent-matters              the role: a curated CLAUDE_CONFIG_DIR (prompt, CLAUDE.md, skills, tools)
        ▲  rendered onto
   agent CLIs                 claude · codex · gemini · opencode   (the engines)
        ▲  placed + driven by
   schedule-matters           placement: session / window / pane (sole authority)
   session-matters            durable identity + lifecycle; primitives: nudge · mail · capture
        ▲  over
   wire + runtime daemon      transport and process supervision
```

An agent is **(engine + role + session-id)**: the CLI is the engine, agent-matters is the role,
the session-id is the durable handle. Placement, coordination, and sequencing stack above.

---

## 3. The universal seam: wire

Every surface is a `wire` client: native terminal with tmux, a TUI, the graphical cockpit, a
future browser tab. None is privileged. They all speak `wire` to the daemons and render
sessions.

`wire` is transport-agnostic by design. Local (v1): `wire` over a unix socket to local
daemons. Future builds: `wire` over the network to a remote daemon. The lock-in risk lives in
the protocol, not in the shell tech, so the shell choice stays reversible.

---

## 4. Agent integration: drive and tail

The integration surface is the CLI's own persisted transcript, not an SDK and not ANSI
scraping. The CLIs already do the expensive work of persisting structured state; littleorgans
consumes it.

**Input (UI to CLI): drive the real CLI.**
- Inject into the running session (tmux send-keys, or a cleaner per-CLI channel where one
  exists). The agent runs for real and unmodified.
- The interactive complexity is removed upstream, not reconstructed at runtime:
  - Approval gates are bypassed via each CLI's settings.
  - Menus do not arise because littleorgans controls the CLIs' built-in tools through the
    compiled agent-matters role settings (section 8), not at runtime.
- littleorgans owns a **security layer that compiles declarative policy down to each CLI's own
  settings**, surfaced to the user as education rather than enforced as a runtime interceptor.
  Those settings live in the agent-matters role config (section 8).
- With gates and menus gone, input collapses to prompt injection.

**Output (CLI to UI): tail the transcript.**
- Tail the session file the CLI already writes (`~/.claude/projects/<proj>/<session>.jsonl`
  for Claude Code, the equivalent for each other CLI), normalize it, write to SQL, sync to the
  UI.

**Per-CLI adapters** fall out of this. Three in total:
- a **transcript adapter** reading structured events out,
- a **settings adapter** that renders the agent-matters role's policy into each CLI config,
- a **launch/resume adapter** (section 7).

All keyed off the same session-id, all versioned by the scheduled build in section 5.

The drive and tail halves are not bespoke. At the agent grain they are the session-matters
primitives **mail and nudge** (drive) and **capture** (tail), section 8.

---

## 5. transport-matters: the capture backbone

transport-matters is the **two-way wire capture and intercept** layer. It delivers raw
transcripts over `wire` and can pause-and-edit, watch, breakpoint, tamper, and overlay the
stream, and it maintains a canonical internal model. It is **not** the owner of security policy
or built-in-tool control; that is agent-matters. Its defining mechanism is an **hourly/nightly
build that is schema CI for CLI formats**:

1. detects when a new CLI version drops with a new transcript schema,
2. reports current support status (supported / not yet supported),
3. forces an update so littleorgans absorbs the new schema and regains full support.

This turns the fragility of tracking four moving CLI formats into a build rather than a hope.
The same workflow extends to transcript normalization. The brittle Python-to-TS DTO mirror
flagged in the migration gap audit is this canonical model under another name.

Migration note: bringing transport-matters into littleorgans is not a generic port. It is
standing up the cockpit's read pipeline.

**Channel separation (the dual-socket rule).** `wire` carries control as clean JSON;
transport-matters carries the high-bandwidth transcript stream on its own framed channel. The
two never merge, and the stream is never base64-stuffed into the control envelope. herdr ships
exactly this as two sockets: JSON `herdr.sock` for control, length-prefixed binary
`herdr-client.sock` for frames.

---

## 6. The session model

**schedule-matters owns multiplexing**: session, window, pane. It is a reconciler.

Current state: today both `lilo create session` and `lilo run` route through `spawn_session`
(`internal/session/app/src/cli/run.rs:15-39`); both spawn. The declarative-manifest and
place-into-existing-pane model below is the **post-schedule-matters target**, not today's code.

- `lilo create session` files a **request**, a declarative manifest of desired state.
  schedule-matters materializes and owns a new tmux session behind it. Multi-agent.
- `lilo run` is an imperative single-agent **create-and-place**. Only an explicit
  place-into-an-existing-pane mode is exec-shaped.

This is the **apply / run / exec duality** that Kubernetes already proved:

| Verb | Nature | Analogue |
|------|--------|----------|
| `create session` | apply a declarative manifest, multi-agent | `kubectl apply` |
| `lilo run` | imperative single-agent create-and-place | `kubectl run` |
| `lilo run` into an explicit existing pane | run in a live pane | `kubectl exec` |

**The session manifest is the proto-CRD.** schedule-matters reconciles it into tmux today and
into pods in the v2 build tomorrow. The payload shape carries the weight because it is the
single artifact that survives the jump to K8s. The manifest is **thin: identity and topology
only**. It carries no coordination and no workflow.

**schedule-matters is the sole placement authority.** Nothing places an agent into a pane
except schedule-matters, declarative or imperative. `kubectl run` and `exec` both go through the API
server, and `lilo run` does not bypass schedule-matters: once scheduling lands, `lilo run`
becomes a thin client that asks it to place an agent. The direct spawn
that exists today is interim. This dissolves any notion of "an agent schedule-matters did not
spawn": it places all of them and therefore always holds the occupancy binding.

---

## 7. Placement, identity, and agent lifecycle

### Never address by position
A tmux positional address (`1:2.1`, that is session:window.pane) is an array index. tmux
renumbers those on every window insert and delete, so binding an agent to `1:2.1` binds it to
an index in a list that reorders underneath it. That is the entire source of "the agent's
location is now incorrect." tmux already provides stable identity: `%pane_id`, `@window_id`,
`$session_id`, minted at creation and never renumbered or reused for the server's life.
`send-keys -t %3` finds the pane wherever it drifted.

### Identity is layered; bind at the durable layer
```
   agent occupant token        opaque, the agent's identity
        ↓ bound to
   schedule-matters pane UID    its own, in its store, survives tmux server restart
        ↓ currently realized as
   tmux %pane_id  (%3)          survives window churn, dies on server restart
        ↓ derived for display only, never stored
   positional address  (1:2.1)
```
schedule-matters binds an **opaque occupant token to a pane UID** and stays blind to what the
agent is. It manages panes; the agent is an occupant; location follows for free because the
binding rides stable identity, not position. Window insert, delete, and renumber need no action.

### Pane death is the only event that needs reconciliation
When a pane is killed the binding dangles. schedule-matters emits `orphaned(token)` and stops.
It never decides to relocate or tear down, because it does not know the agent's worth. The
owner decides, one layer up.

### Death versus resume is a restart policy, owned above schedule-matters
The agent's durability never came from the pane. It comes from the CLI persisting its session
(Claude Code writes the session jsonl and resumes with `claude --resume <session-id>`; the
others have their own). An agent is **(CLI + session-id)**; the pane is its current body. The
session-id is the same handle transport-matters already tails, so resume reuses existing
machinery.

| Agent | restartPolicy | On pane death |
|-------|---------------|---------------|
| `lilo run` (bare) | Never | dies with the pane (the default) |
| managed (a controller wants it durable) | Always / OnFailure | place into a new pane, `--resume` from session-id |

schedule-matters owns the **mechanism, never the policy**. restartPolicy is **not** a field on
the thin session manifest; it rides on the agent's own record (session-matters), which keeps
the manifest as thin as decided.

restartPolicy Always invokes the CLI's native `--resume` as the **baseline** resurrection
mechanism. That is deliberately the simple path. Because littleorgans owns the transcript
independently of the CLI, it can do far more than a native resume, but those richer capabilities
are a separate subsystem and a separate brainstorm (section 14), not part of placement
reconciliation.

### Scope
The model supports resume from day one because the seam is cheap. Building it waits for the
first controller that wants a durable agent, which is orchestration-matters. Design the seam
now, build resume then. Bare `lilo run` stays Never.

---

## 8. The control tower: agent-matters, orchestration, workflow

Three layers stack above placement. Each is a controller over the layer below, and the whole
tower has one rule: dependencies point **down**. A lower layer never knows its consumers.

### agent-matters — the role
An agent's engine is the CLI; its **role** is a curated `CLAUDE_CONFIG_DIR`, runtime-generated
or persisted, bundling system prompt, CLAUDE.md, skills, tools, and settings, crafted for a
specific job (reviewer, lead, worker). agent-matters is **CLI-agnostic**: the role is defined
once, and the per-CLI settings adapter from section 4 renders it into each engine's config
format. The security policy compiles into exactly that config. This finally separates four
things that used to blur: engine, role, placement, coordination.

agent-matters deserves its own design session; it is slotted here, not yet fully specified.

The per-CLI adapters (transcript-out, settings-in, launch/resume, state detection) should
collapse into **one declarative table** per agent, `{agent, config_dir, hook_file, hook_format,
events, version}`, feeding install, launch, and detection from the same row. agent-matters owns
provisioning; runtime-matters owns the launch adapter (herdr `integration/mod.rs` + cmux
`AgentHookDef`).

### session-matters — durable identity and the agent primitives
session-matters owns the durable agent (token, CLI, session-id, restartPolicy, desired state)
and three primitives: **nudge** (signal), **mail** (inject a message), **capture** (read the
transcript). These are drive and tail at the agent grain: mail and nudge are the write half,
capture is the read half. **This is where the deprecated helioy-bus functionality lands.** There
is no separate message bus; inter-agent communication is these primitives composed.

### orchestration-matters — the conductor
An **orchestrator spec combines sessions, agents, and configs**. orchestration-matters is
intimate with the session api and with agent-matters: it selects roles, requests their
placement through schedule-matters, and **conducts** the result. It tails participants and
nudges or mails each in turn, routing one agent's output into another's input according to the
pattern's gates.

- It is an **expert client** of the layers below, not a reimplementation of them. It composes
  and reads the session api, agent-matters, and the nudge/mail/capture primitives; it never
  owns placement or duplicates the primitives. That is what keeps it from becoming a god-object.
- Its vocabulary is the existing **warroom patterns**: peer-consensus, lead and worker,
  parallel, brainstorm, code-review. The patterns survive; their old implementation over
  helioy-bus is what drive-and-tail mediation replaces.
- It is the **first consumer of resume** and the first consumer of cross-agent transcript
  sharing (section 14), because coordination outlives any single agent process.
- An orchestrator is a **composable unit**: a coordinated unit is either an agent or a
  sub-orchestrator, handled by the same machinery. Hierarchical orchestration for free.
- Orchestrators **defer to other orchestrators**. When a role has no pre-authored profile, the
  orchestrator does not call agent-matters `resolve` directly; it stands up a sub-orchestrator
  (an orchestrator spec) whose job is the JIT profile standup, and `resolve` is invoked from
  inside it. Everything dynamic flows through an orchestrator spec, including producing a role.

Canonical case, peer-consensus: two agents, cross-check one artifact, explicit sign-off before
it counts. Placement gives the two panes. capture and mail carry their exchange.
orchestration-matters is the part that says they must agree, and holds the gate until they do.

### workflow-matters — the flow
A workflow is a **thin DAG that describes the flow and message interchange between
orchestrators**. It sits above orchestration: orchestrators are the nodes, the edges are flow
and interchange. This is the Argo shape, an orchestrator is a unit of coordinated work that
runs to a result, a workflow is a DAG of those units. A workflow **may or may not be triggered
by an orchestrator**, and an orchestrator may trigger a workflow.

The differentiator, precisely: **orchestration is one live coordinated session**, a shared
conductor holding gates over agents that run together; **workflow is a DAG of independent
orchestrator runs** joined by edge handoff, with no shared live session. Sub-orchestrators are
nested conductors *within* a session; workflow nodes are *independent* runs.

- The workflow slice rides the existing **linear-workflows** contract. No new format.

### The dependency direction and the acyclic rule
```
   workflow-matters        DAG of orchestrators
        │ produces
   orchestration-matters   composes agents into coordinated sessions
        │ produces
   schedule-matters requests ──> tmux session / window / pane
```
(Section 2 reads bottom-up by "sits on"; this reads top-down by "produces". Same tower,
opposite arrow, because dependency and production run in opposite directions.)

- One input contract for schedule-matters: the session/topology manifest.
- Producers: the `lilo` CLI directly and orchestration-matters. workflow-matters does **not**
  produce schedule requests directly; it triggers orchestrators, and orchestration requests
  placement.
- Zero upward knowledge. The primitive cannot be corrupted by its consumers.

Workflow and orchestrator may reference and trigger each other, and an orchestrator may contain
sub-orchestrators. The one discipline that keeps this from eating itself: **specs may
cross-reference freely, but a resolved run must be a DAG.** Recursion bottoms out at agents.

### The human layer
Whether the orchestrator is the human-facing layer maps onto the two tiers. **Power users**
author orchestrator and workflow specs directly, so the orchestrator is their interface.
The **mass market** never authors; they pick a **curated orchestration**, a shipped template
parameterized at launch. So the orchestrator is the power-user surface, and a curation layer
over it is the mass-market surface. Same curation theme as agent-matters: curated roles,
curated orchestrations.

---

## 9. K8s and the v2 relationship

littleorgans is the **local-first learning plane**. Docker transport already exists. It may
never itself deploy to K8s.

K8s is the v2 endgame as a **separate build** that inherits the contracts littleorgans proves
out: the session manifest as proto-CRD, `wire`, the canonical event model, the restartPolicy
and resume semantics from section 7, and the controller tower from section 8 (runtime-matters
already drafts as a kubelet analog). K8s vocabulary in v1 is a forward contract, not a
deployment path this build walks.

**The full mapping** (the matters family as a K8s control plane):

| Product | Owns | K8s analogue |
|---|---|---|
| agent-matters | persona, config, hooks (the role) | PodSpec |
| identity-matters | IAM | ServiceAccount + RBAC |
| session-matters | control plane: sessions, channels, MCP, spawn API | API server + etcd |
| schedule-matters | placement / multiplexing (session/window/pane) | kube-scheduler |
| runtime-matters | per-host runtime substrate: daemon + shim + launcher | kubelet + CRI |
| orchestration-matters | controllers: reconcile observed vs desired | Deployment / Job controllers |
| workflow-matters | choreography: DAGs, state machines | Argo |
| transport-matters | wire-level observation | service-mesh observability |

---

## 10. Shell technology (OPEN)

Electron vs Tauri vs a native surface. Re-opened by the mass-market constraint and not yet
decided.

- Mass-market polish raises the weight on **render consistency** (a non-technical user reads a
  glitch as "broken"; bundled Chromium guarantees pixel-identical rendering, the tri-webview
  does not) and on **mature signing, notarization, auto-update**. Both favor Electron.
- The **Rust chassis alignment** (Tauri host is a Cargo crate under the existing Moon and
  cargo-dist toolchain) favors Tauri.
- Because the mass path is a SQL-fed design-system app and the terminal is the escape hatch,
  terminal-emulation performance now matters only for the power-user lens, which weakens the
  native-terminal argument for the mass surface.

Prior analysis: `~/.mdx/research/electron-vs-tauri-2026.md` plus the Codex review. Both predate
the terminal-UI and mass-market framing, so their weights need revisiting before this is decided.

---

## 11. Component map (matters family)

| Component | Owns | Status |
|-----------|------|--------|
| agent-matters | the role: curated CLAUDE_CONFIG_DIR (prompt, CLAUDE.md, skills, tools, settings), CLI-agnostic; compiler model decided | littleorgans integration open |
| transport-matters | two-way wire capture + intercept; canonical model; schema-CI build; NOT the security/tool-policy owner | exists, migrating in |
| schedule-matters | multiplexing (session/window/pane); sole placement authority; occupant-token to pane-UID binding | reserved / greenfield (no crate yet) |
| session-matters | durable agent identity + lifecycle; primitives nudge / mail / capture (the deprecated bus lands here) | exists |
| orchestration-matters | conductor: composes agents into coordinated sessions; spec = sessions + agents + configs; warroom patterns | specified, to build |
| workflow-matters | thin DAG of orchestrators (flow + message interchange); linear-workflows contract | specified, to build |
| runtime daemon (runtime-matters) | process supervision, launchers, platform (kubelet analog) | exists |
| identity-matters | identity and auth | exists |

Deprecated: **helioy-bus**. Only the matters family makes the cut; its messaging role is now
session-matters nudge/mail/capture.

---

## 12. Open questions and next steps

1. **agent-matters littleorgans integration.** The compiler model (capabilities and profiles,
   resolve → compile → use, content-addressed runtime home) is already decided (sec 14) and
   implemented in the sibling agent-matters repo. Open here is integration only: wiring it into
   littleorgans, the gemini and opencode runtime adapters (today Codex and Claude), and the
   resolve → compile → use → place chain. Collapse the per-CLI adapters (transcript, settings,
   launch, detection) into one declarative table feeding install, launch, and detection.
2. **Transcript service owner + persistence model.** Who tails the CLI jsonl and persists it,
   and where the service sits: **between transport-matters and session-matters** (capture is a
   session-matters primitive, sec 8; schedule-matters is placement-only). This supersedes the
   earlier transport ↔ schedule framing; owner accepted the flip. Persistence is a dual store:
   raw plus canonical in Postgres jsonb, local read-model in SQLite
   (`internal/session/store/src/sqlite`, confirmed), joined by session-id. The control/stream channel split is settled (section 5): wire = control
   JSON, transport-matters = the framed stream channel. Open: the service's exact owner and the
   precise substrate boundary.
3. **Session manifest field-level schema.** The proto-CRD's actual fields.
4. **Per-CLI resume semantics.** Does `--resume` continue the same session jsonl or fork a new
   session-id? Affects transcript continuity in the read path. Resolve per CLI in the adapter.
5. **Shell technology decision** (section 10), after the mass-market weights are re-applied.
6. **Manifest and multi-agent cutover.** When `run` and `create` stop sharing `spawn_session`
   and the thin declarative manifest plus place-into-existing-pane model lands (the section 6
   target).

Resolved:
- The session-matters versus schedule-matters boundary (durable identity vs placement, meeting
  at the occupant token).
- The composition direction between workflow and orchestration: **workflow sits above
  orchestration** as a DAG of orchestrators. Not a peer strategy.
- The inter-agent communication substrate: **session-matters nudge/mail/capture**, not a bus.

---

## 13. Deferred brainstorm: transcript-owned resume and cross-agent sharing

Status: OPEN, flagged for its own brainstorm. littleorgans captures the transcript two ways:
**HTTP over `wire` via transport-matters** (canonical, live) and **the CLI jsonl via the
transcript service** (on-disk tail). Owning it independently of the CLI opens a capability
ladder above the baseline:

1. **Native resume** (baseline, used by restartPolicy Always): the CLI's own `--resume`.
2. **Owned-transcript resume**: reconstruct from the canonical transcript, independent of the
   CLI's session file; replay from a point, branch and fork, edit history.
3. **Cross-agent handoff**: the canonical model is CLI-agnostic, so a claude transcript can
   seed codex, gemini, or opencode. Context portability across CLIs.
4. **Cross-agent sharing, live**: agents reading or subscribing to each other's transcripts as
   shared context. The standout, and the read substrate orchestration-matters stands on.

Talking points for the dedicated brainstorm:
- Where the canonical transcript store lives, and its relationship to context-matters and
  knowledge-matters as memory substrates.
- The session graph: branches, forks, merges, and what identity a forked or handed-off session
  carries.
- Permission and isolation: which agent may read whose transcript.
- How owned-transcript resume degrades cleanly to native resume when the richer path is unwanted.
- Whether cross-agent handoff is a translation at the canonical layer or a replay into the
  target CLI's own input.

The lifecycle in section 7 uses only rung 1.

---

## 14. Decisions log

- 2026-05-30 transport-matters is **in scope** for migration into littleorgans (prior
  out-of-scope phase is over).
- 2026-05-30 Agent integration is **drive and tail**: drive the real CLI, tail its persisted
  transcript. No SDK, no ANSI scraping.
- 2026-05-30 Security is a **policy-to-settings compiler**, educational, not a runtime gate.
- 2026-05-30 transport-matters is the **capture backbone** with an hourly/nightly schema-CI
  build tracking CLI version and schema drift.
- 2026-05-30 The session manifest is **thin** (identity + topology). Producers compile down to
  schedule-matters requests; schedule-matters is blind to all of them.
- 2026-05-30 `create session` = apply a declarative multi-agent manifest;
  `lilo run` = imperative single-agent create-and-place (explicit existing-pane variant is exec-shaped).
- 2026-05-30 schedule-matters is the **sole placement authority**; `lilo run` routes through it
  once scheduling lands (interim direct spawn today).
- 2026-05-30 **Never store positional tmux addresses.** Bind occupant token to a
  schedule-matters pane UID, realized as the stable tmux `%pane_id`.
- 2026-05-30 Pane death emits `orphaned(token)`; schedule-matters reports, the owner decides.
- 2026-05-30 **restartPolicy**: `lilo run` = Never; managed agents = Always / OnFailure (resume
  from session-id). Lives on the agent's record, not the thin manifest.
- 2026-05-30 **Resume** reuses CLI session persistence; native `--resume` is the baseline.
  Richer transcript-owned resume deferred (section 13).
- 2026-05-30 littleorgans is the **local-first learning plane**; K8s is a separate v2 build.
- 2026-05-31 **agent-matters** is a layer: the role as a curated CLI-agnostic CLAUDE_CONFIG_DIR
  (prompt, CLAUDE.md, skills, tools, settings). The settings adapter renders its role policy
  into each CLI config. Compiler model decided; only littleorgans integration remains.
- 2026-05-31 **helioy-bus is deprecated.** Only the matters family makes the cut. Inter-agent
  communication is the session-matters primitives **nudge / mail / capture**.
- 2026-05-31 **orchestration-matters** is the conductor: spec = sessions + agents + configs; an
  expert client of the layers below; tails and nudges/mails to coordinate; warroom patterns are
  its vocabulary; a composable unit (agents or sub-orchestrators).
- 2026-05-31 **workflow sits above orchestration**: a thin DAG of orchestrators describing flow
  and message interchange. Either may trigger the other.
- 2026-05-31 **Acyclic rule**: specs may cross-reference (orchestrator to sub-orchestrator,
  workflow to orchestrator, both directions), but a resolved run must be a DAG. Recursion
  bottoms out at agents.
- 2026-05-31 **Human layer**: power users author orchestrator and workflow specs; the mass
  market picks curated orchestrations parameterized at launch.
- 2026-05-31 **Orchestrators defer to orchestrators**: a missing role is produced by standing up
  a JIT-profile-standup sub-orchestrator, not by a direct agent-matters `resolve` call.
  Everything dynamic flows through an orchestrator spec. agent-matters is a compiler (catalog of
  capabilities and profiles → fingerprinted runtime home); the runtime home is a content-addressed
  image, and `use` activates it while launch stays with schedule-matters.
- 2026-05-31 **MoE peer review (Claude + Codex)** applied: apply/run/exec analogy corrected
  (`lilo run` ≈ `kubectl run`); workflow-matters is not a direct schedule producer, plus an
  orchestration-versus-workflow differentiator; transport-matters is two-way and not the
  policy/tool owner; schedule-matters reclassified greenfield. Transcript-service neighbor
  accepted as session-matters (owner confirmed the flip).
- 2026-05-31 **herdr leverage applied** (`~/.mdx/research/ogulcancelik-herdr.md`; ideas only,
  AGPL): the dual-socket rule (wire control JSON vs transport-matters framed stream);
  schedule-matters = kube-scheduler completing the K8s mapping; the per-CLI adapters collapse
  into one declarative table. Corroborates `lilo wait` as the gate primitive and SQLite plus the
  versioned-snapshot migration pattern. The transcript-tail design obviates herdr's ~3k-line
  screen-scrape detector; we keep only its evidence-arbitration pattern.
