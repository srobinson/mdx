# littleorgans: Cockpit and Session Architecture

Status: living draft. Started 2026-05-30. Owner: Stuart. Captures the architecture worked out
in conversation, locks what is decided, and marks what is still open. Companion to
`~/.mdx/research/electron-vs-tauri-2026.md`, `~/.mdx/research/helioy-electron-baseline.md`, and
`~/.mdx/projects/helioy-product-direction.md`.

---

## 1. Product thesis

littleorgans is a **mass-market graphical cockpit that drives multiple terminal-based agent
CLIs** (claude, codex, gemini, opencode) running under a multiplexer. The market gap it fills:
the existing agent multiplexers (cmux on ghostty, herdr as a Rust TUI) are developer-targeted
terminal tools. littleorgans targets the non-technical mass market with a graphical surface
over the same agent CLIs.

Two audiences, two tiers, one control plane:

- **Mass market (default):** a graphical app. The agent's work is rendered as structured
  output, not raw terminal.
- **Power user (escape hatch, first-class):** the raw terminal pane, tmux, the `lilo` CLI.
  Always one keystroke away, a designed feature and not an afterthought.

The default experience is graphical; the terminal demotes to a power-user lens.

---

## 2. The layer stack

```
   Graphical cockpit        mass-market GUI                       (the new layer)
        ▲ sits on
   Agent CLIs               claude · codex · gemini · opencode    (rich terminal TUIs)
        ▲ sits on
   Multiplexer              schedule-matters owns session/window/pane (tmux today)
        ▲ sits on
   Control plane            wire · runtime + session daemons (lilod)
```

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
  - Menus do not arise because littleorgans controls the CLIs' built-in tools through
    transport-matters.
- littleorgans owns a **security layer that compiles declarative policy down to each CLI's own
  settings**, surfaced to the user as education rather than enforced as a runtime interceptor.
- With gates and menus gone, input collapses to prompt injection, which send-keys handles.

**Output (CLI to UI): tail the transcript.**
- Tail the session file the CLI already writes (`~/.claude/projects/<proj>/<session>.jsonl`
  for Claude Code, the equivalent for each other CLI), normalize it, write to SQL, sync to the
  UI.

**Per-CLI adapters** fall out of this, a clean symmetry. Two here, a third in section 7:
- a **transcript adapter** reading structured events out,
- a **settings adapter** writing security and tool policy in.

Both are versioned by the scheduled build in section 5.

---

## 5. transport-matters: the capture backbone

transport-matters delivers raw transcripts over `wire` and maintains a canonical internal
model. Its defining mechanism is an **hourly/nightly build that is schema CI for CLI formats**:

1. detects when a new CLI version drops with a new transcript schema,
2. reports current support status (supported / not yet supported),
3. forces an update so littleorgans absorbs the new schema and regains full support.

This turns the fragility of tracking four moving CLI formats into a build rather than a hope.
The same workflow extends to transcript normalization. The brittle Python-to-TS DTO mirror
flagged in the migration gap audit is this canonical model under another name.

Migration note: bringing transport-matters into littleorgans is not a generic port. It is
standing up the cockpit's read pipeline.

---

## 6. The session model

**schedule-matters owns multiplexing**: session, window, pane. It is a reconciler.

- `lilo create session` does not create a session. It files a **request**, a declarative
  manifest of desired state. schedule-matters materializes and owns a new tmux session behind
  it. A create-session request is **multi-agent**.
- `lilo run` mutates a live session: one agent into an already-existing pane. Imperative.

This is the **apply versus exec duality** that Kubernetes already proved:

| Verb | Nature | Analogue |
|------|--------|----------|
| `create session` | apply a declarative manifest, multi-agent | `kubectl apply` |
| `lilo run` | imperative mutation of a live session, single agent into an existing pane | `kubectl exec` |

**The session manifest is the proto-CRD.** schedule-matters reconciles it into tmux today and
into pods in the v2 build tomorrow. The payload shape carries the weight because it is the
single artifact that survives the jump to K8s.

**schedule-matters is the sole placement authority.** Nothing places an agent into a pane
except schedule-matters, declarative or imperative. `kubectl exec` does not bypass the API
server, and `lilo run` does not bypass schedule-matters: once scheduling lands, `lilo run`
becomes a thin client that asks it to place an agent into an existing pane. The direct spawn
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
agent is. "Indirect management" is exact: it manages panes, the agent is an occupant, and
location follows for free because the binding rides stable identity, not position. Window
insert, delete, and renumber require no action.

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

schedule-matters owns the **mechanism, never the policy**. Its interface gains one verb, place
a token with an optional resume handle, and one event, `orphaned`. restartPolicy is therefore
**not** a field on the thin session manifest; it rides on the agent's own record, which keeps
the manifest as thin as decided.

This is the third per-CLI adapter: **transcript-out, settings-in, launch/resume**, all keyed
off the same session-id.

restartPolicy Always invokes the CLI's native `--resume` as the **baseline** resurrection
mechanism. That is deliberately the simple path. Because littleorgans captures the transcript
two ways and owns it independently of the CLI, it can do far more than a native resume, but
those richer capabilities are a separate subsystem and a separate brainstorm (section 13), not
part of placement reconciliation.

### Scope
The model supports resume from day one because the seam is cheap. Building it waits for the
first controller that wants a durable agent, which is orchestration-matters. Design the seam
now, build resume then. Bare `lilo run` stays Never.

---

## 8. The pipeline and the dependency direction

The session manifest is **thin: identity and topology only** (how many panes and windows,
which CLI in each, which repo and cwd). It does not carry orchestration or workflow.

orchestration-matters and workflow-matters are **separate animals with separate specs**. They
**compile down into schedule-matters requests** depending on their requirements.
**schedule-matters does not know or care about either.**

```
   workflow-matters        (own spec: task DAG, rides linear-workflows contract)
            \
             >── generate ──> schedule-matters requests ──> tmux session/window/pane
            /
   orchestration-matters    (own spec: coordination, rides warroom patterns)
```

- One input contract for schedule-matters: the session/topology manifest.
- Many producers: the `lilo` CLI directly, orchestration-matters, workflow-matters.
- Zero upward knowledge. The primitive cannot be corrupted by its consumers.

**Reuse constraints (no new formats):**
- the workflow slice rides the existing **linear-workflows** contract,
- the orchestration slice rides the existing **warroom** patterns (peer-consensus, lead and
  worker, parallel).

---

## 9. K8s and the v2 relationship

littleorgans is the **local-first learning plane**. Docker transport already exists. It may
never itself deploy to K8s.

K8s is the v2 endgame as a **separate build** that inherits the contracts littleorgans proves
out: the session manifest as proto-CRD, `wire`, the canonical event model, and the
restartPolicy and resume semantics from section 7. K8s vocabulary in v1 is a forward contract,
not a deployment path this build walks.

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

Prior analysis: `~/.mdx/research/electron-vs-tauri-2026.md` plus the Codex review
(`electron-vs-tauri-2026-codex-review.md`). Both predate the terminal-UI and mass-market
framing, so their weights need revisiting before this is decided.

---

## 11. Component map (matters family)

| Component | Owns | Status |
|-----------|------|--------|
| transport-matters | capture backbone: transcripts over wire, canonical model, schema-CI build | exists, migrating in |
| schedule-matters | multiplexing (session/window/pane); sole placement authority; binds occupant token to pane UID; reconciles pane death | scaffold |
| session-matters (lilod) | durable agent identity and lifecycle: token, CLI, session-id, restartPolicy, desired state | exists |
| orchestration-matters | agent coordination spec; compiles to schedule requests; first consumer of resume | planned |
| workflow-matters | workflow / task DAG spec (linear-workflows); compiles to schedule requests | planned |
| runtime daemon | process supervision, launchers, platform | exists |
| identity-matters | identity and auth | exists |

---

## 12. Open questions and next steps

1. **Next exploration: orchestration-matters and workflow-matters specs.** They are the two
   separate animals above schedule-matters. Define each spec and exactly how it compiles to a
   schedule-matters request. orchestration-matters is also the first consumer of resume.
2. **Capture-and-sync service exact placement**, between transport-matters and schedule-matters.
   Leaning: transport-matters owns the stream, schedule-matters owns when panes exist; the
   sync service sits in their overlap. Confirm once orchestration and workflow are mapped.
3. **Session manifest field-level schema.** The proto-CRD's actual fields.
4. **Per-CLI resume semantics.** Does `--resume` continue the same session jsonl or fork a new
   session-id? Affects transcript continuity in the read path. Resolve per CLI in the adapter.
5. **Shell technology decision** (section 10), after the mass-market weights are re-applied.

Resolved: the session-matters versus schedule-matters boundary (was open question 2). See
section 7 and the component map. session-matters owns the durable agent, schedule-matters owns
placement, they meet at the occupant token.

---

## 13. Deferred brainstorm: transcript-owned resume and cross-agent sharing

Status: OPEN, flagged for its own brainstorm. littleorgans does not lean on the CLI's native
resume alone, because it captures and owns the transcript two ways:

- **HTTP over `wire` via transport-matters** — the canonical, normalized stream, captured live.
- **The CLI-generated transcript via the transcript service** — the on-disk jsonl, tailed.

Owning the transcript independently of the CLI opens a capability ladder above the baseline:

1. **Native resume** (baseline, used by restartPolicy Always): the CLI's own `--resume` from
   its session-id. Same agent, same CLI, continues its own session.
2. **Owned-transcript resume**: reconstruct context from littleorgans' captured canonical
   transcript, independent of the CLI's session file. Survives a lost or incompatible session
   file; enables replay from a point, branch and fork, edit history.
3. **Cross-agent handoff**: the canonical model is CLI-agnostic, so a transcript captured from
   one agent (claude) can seed another (codex, gemini, opencode). Context portability across
   CLIs.
4. **Cross-agent sharing, live**: multiple agents reading or subscribing to each other's
   transcripts as shared context. A supervisor seeing its sub-agents, peers sharing a working
   context. The standout, and the canonical transcript is what makes it possible.

Talking points for the dedicated brainstorm:
- Where the canonical transcript store lives, and its relationship to context-matters and
  knowledge-matters as memory substrates.
- The session graph: branches, forks, merges, and what identity a forked or handed-off session
  carries.
- Permission and isolation: which agent may read whose transcript.
- How owned-transcript resume degrades cleanly to native resume when the richer path is unwanted.
- Whether cross-agent handoff is a translation at the canonical layer or a replay into the
  target CLI's own input.

Not decided here. The lifecycle in section 7 uses only rung 1.

---

## 14. Decisions log

- 2026-05-30 transport-matters is **in scope** for migration into littleorgans (prior
  out-of-scope phase is over).
- 2026-05-30 Agent integration is **drive and tail**: drive the real CLI, tail its persisted
  transcript. No SDK, no ANSI scraping.
- 2026-05-30 Security is a **policy-to-settings compiler**, educational, not a runtime gate.
- 2026-05-30 transport-matters is the **capture backbone** with an hourly/nightly schema-CI
  build tracking CLI version and schema drift.
- 2026-05-30 The session manifest is **thin** (identity + topology). orchestration-matters and
  workflow-matters are separate specs that compile down to schedule-matters requests;
  schedule-matters is blind to both.
- 2026-05-30 `create session` = apply a declarative multi-agent manifest;
  `lilo run` = imperative single-agent mutation into an existing pane.
- 2026-05-30 schedule-matters is the **sole placement authority**; `lilo run` routes through it
  once scheduling lands (interim direct spawn today).
- 2026-05-30 **Never store positional tmux addresses.** Bind occupant token to a
  schedule-matters pane UID, realized as the stable tmux `%pane_id`. Stable identity, not
  position. This is the fix for location drift on window insert and delete.
- 2026-05-30 Pane death emits `orphaned(token)`; schedule-matters reports, the owner decides.
- 2026-05-30 **restartPolicy**: `lilo run` = Never (dies with the pane); managed agents =
  Always / OnFailure (resume from session-id). Lives on the agent's record, not the thin
  manifest.
- 2026-05-30 **Resume** reuses CLI session persistence (the session-id transport-matters
  already tails). Seam designed now, built when orchestration-matters lands.
- 2026-05-30 littleorgans is the **local-first learning plane**; K8s is a separate v2 build
  that inherits the contracts.
- 2026-05-30 Resolved the session-matters vs schedule-matters boundary: durable agent identity
  vs placement, meeting at the occupant token.
- 2026-05-30 restartPolicy Always invokes the CLI's native `--resume` as the baseline
  resurrection mechanism (leaning). Richer transcript-owned resume is deferred (section 13).
- 2026-05-30 Transcript is captured two ways (HTTP over wire via transport-matters, and the CLI
  jsonl via the transcript service); littleorgans owns it independently of the CLI.
  Transcript-owned resume and cross-agent transcript sharing are flagged for a dedicated
  brainstorm (section 13).
