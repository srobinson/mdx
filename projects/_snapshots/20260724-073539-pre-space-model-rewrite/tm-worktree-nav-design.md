---
title: Worktree navigation in the ⌘K launcher — the coherent model
type: design
status: recommendation
owner: Stuart (what/why), Claude (how)
bus_topic: tm-worktree-nav
date: 2026-06-25
source: codebase-analyst (scout/design, read-only)
confidence: high
related:
  - ~/.mdx/projects/transport-matters-north-star.md
  - ./NOW.md
  - cm decisions: spaces (#161-166), ports relaunch reclaim (#179/#180)
---

## TL;DR

**Selecting a worktree in ⌘K should SPAWN-INTO, never SWITCH-DESKTOP.**

Selecting a worktree is the **Launch verb pointed at a worktree**, opening isolated work as
coexisting panes inside the one control plane. It must not relaunch or repoint the whole
desktop. The single-fixed-port constraint is a property of the **per-channel desktop app**,
not of worktrees. Per-run canvas panes are already independently isolated (own port pair, own
proxy, own PTY, own run dir via `allocate_port_pair`), and `CreateRunRequest.worktree_id`
already carries a per-worktree target. Git-worktree isolation maps cleanly onto coexisting
isolated panes. A destructive whole-app relaunch would throw that isolation away and serialize
parallel worktrees one-at-a-time, defeating the entire reason worktrees exist.

The good news: the code is already shaped this way. The work is conceptual clarity plus closing
one affordance gap, not a rebuild.

## The tension as posed

The launcher offers worktree navigation. Git worktrees promise **isolation**: parallel
checkouts of one repo (e.g. `context-matters` `main` alongside a `nancy/ALP-2640` worktree
where an agent works). The desktop is **one app on one fixed port per channel** (#179/#180:
relaunch reclaims the port and switches the single desktop to a different workdir). So
"navigating a workdir" by switching the single desktop reads as destructive and one-at-a-time,
which appears to fight the isolation worktrees promise.

The tension is real as framed, but it rests on a conflation. There are **three distinct layers**
that each move a "workdir," at three different granularities. The fixed-port destructiveness
lives at only one of them, and it is the wrong one to drive from worktree selection.

## What the code actually does today (the reframing)

Three layers move a workdir. They are separate mechanisms, not competitors:

**Layer 1 — Channel-app launch (OS / port-binding).** `transport-matters desktop --workdir X`
per channel. One fixed port per channel (`stable`, `preview`). Relaunching at a *different*
workdir reclaims the port and restarts the single desktop. This is the destructive,
one-at-a-time switch. Code: `desktop_cmd.py::run_desktop_reclaim` →
`desktop_recovery.py::prepare_desktop_runtime_for_launch_or_exit` → `_serves_requested_work_dir`
→ `recover_desktop_runtime_or_exit`. This layer answers "which project does this channel's
daily-driver desktop watch."

**Layer 2 — Canvas rooting (view / default context).** ⌘K `select-worktree` does **not** touch
layer 1. It updates the `worktree_id` URL param and calls
`useCanvasStore.initializeCanvas(...)`, re-rooting the canvas's `defaultWorktreeId` in place.
Code: `commandModel.ts` (`select-worktree`, `buildWorktreeRows`) →
`CanvasSurface.tsx` handler → `canvasStore.ts`. This is a cheap, non-destructive default-context
change. **The destructive relaunch is not what worktree selection does today.**

**Layer 3 — Run / pane spawn (the Launch verb, isolated).** Each captured run / canvas pane
gets its **own** port pair (`cli/ports.py::allocate_port_pair`), own proxy, own PTY, own run
dir, spawned through `captured_run.py::prepare_captured_run` and `RunManager._spawn_new_admitted`.
N runs coexist inside the one `app.state.run_manager` singleton. `CreateRunRequest.worktree_id`
(→ `SpawnRun.resolved_worktree: ResolvedWorktree`) targets a specific worktree. Routes:
`POST /v1/runs`, `GET /v1/runs`, `POST /v1/runs/{id}/terminate`, `WS /runs/{id}/terminal`.

**Confirmed fact:** the single-fixed-port constraint is a **per-channel-app** property (layer 1).
**Per-run panes are independently isolated, multi-port** (layer 3). They do not share the
fixed-port limitation.

The Spaces model (#161-166) already encodes coexistence: one **Space** = one git-repo instance
(`repo_instance_key` = sha256 of the git-common-dir), holding **N Worktrees** (per-checkout,
uuid4 `WorktreeId`). A **Canvas** belongs to one Space and carries a mutable, nullable
`default_worktree_id`; a **Pane** can carry its own `worktreeId`, overriding the canvas default.
This is precisely the shape for "worktrees coexist as isolated work within one Space / one
canvas / one control plane." Worktree CRUD is deferred (detect-only cut), but **selection among
detected worktrees is live** and is all SPAWN-INTO needs.

## The candidate models and trade-offs

### Model 1 — SWITCH-DESKTOP (reject)

Selecting a worktree reclaims and restarts the single per-channel desktop pointed at that
workdir. One at a time; switching destroys the prior view.

- Fights git-worktree isolation: serializes parallel worktrees the user opened worktrees to run
  in parallel.
- Fights the single control plane: spinning per-worktree desktop processes fragments Observe
  into many control planes; the director can no longer see the whole fabric from one place.
- Fights the north star: relaunch is a coarse CLI/electron action awkward for the director; the
  desktop is meant to be a zero-chrome surface you *watch*, not a single-document window you
  swap.
- Already not what the launcher does. Adopting it would be a regression toward destructiveness.

This model misapplies layer-1 plumbing to a layer-2/3 job.

### Model 2 — SPAWN-INTO (recommended)

The desktop is one control plane. Selecting a worktree opens or focuses isolated work for that
worktree **within** the desktop: it sets the canvas's default worktree (layer 2) and/or spawns
an isolated run/pane targeting that worktree (layer 3). Worktrees coexist as panes; isolation is
preserved by per-run ports/PTY/run-dir; nothing is destroyed.

- Honors worktree isolation through per-run isolation. N worktree agents run concurrently as
  isolated panes.
- Honors the single control plane: everything stays inside `RunManager`, observable through one
  Observe surface.
- Is literally the Launch verb (`CreateRunRequest.worktree_id`), so the director inherits it for
  free. API-first, no UI-trapped logic.
- Works inside the detect-only cut: needs only selection among detected worktrees, which exists.

### Model 3 — Hybrid (the correct framing, not a third competitor)

Keep both mechanisms, each at its own granularity. **Layer 1 relaunch stays valid for its real
job**: repointing a whole channel's daily-driver desktop at a different *project* (you are done
with project A, point `stable` at project B). That is coarse and infrequent, and being
one-at-a-time is correct there because you run one daily-driver desktop per channel by design.
**Worktree selection inside ⌘K is SPAWN-INTO** (layers 2 and 3). The error to avoid is driving
the layer-1 relaunch from layer-2/3 worktree selection. So the "hybrid" is not a blend of the
two on the same action; it is keeping each mechanism at its correct layer.

## Recommendation: SPAWN-INTO, expressed as two clean verbs

Worktree selection should resolve into two non-collapsed actions, never a desktop relaunch:

1. **Root the canvas here** (layer 2, navigation). Sets `defaultWorktreeId` = the worktree that
   new spawns default into. Non-destructive: existing panes persist. This is what `select-worktree`
   does today and should keep doing.
2. **Spawn a run/pane here** (layer 3, Launch). Opens an isolated captured run / canvas pane
   targeting the chosen worktree (`CreateRunRequest.worktree_id`). N worktrees' work coexists.

Separating "root" from "spawn into" dissolves the tension: rooting is the cheap default-context
selector, spawning is where git-worktree isolation is honored by per-run isolation. Neither is a
whole-app switch.

## What the "Current" badge implies, and should mean

Today the badge marks the worktree where `worktree.worktreeId === activeWorktreeId`, and
`activeWorktreeId` is `useCanvasStore(state => state.defaultWorktreeId)`. So "Current" already
means **the canvas's rooted / default worktree**, the default target for new spawns. That is
exactly the SPAWN-INTO mental model and it contradicts SWITCH-DESKTOP. The badge should read as
"new spawns land here," a soft default any individual spawn can override, **not** "the desktop is
currently showing only this worktree." A copy or affordance tweak to communicate "default spawn
target" would remove the last bit of SWITCH-DESKTOP ambiguity.

## What would have to be true (prerequisites)

1. **Re-rooting must be non-destructive to existing panes.** SPAWN-INTO depends on
   `initializeCanvas(...)` preserving open panes when `defaultWorktreeId` changes. Verify this
   in `canvasStore.ts`; if re-rooting resets panes, that is a bug to fix, because coexistence is
   the whole point.
2. **Close the per-spawn worktree-target affordance.** `CreateRunRequest.worktree_id` exists, but
   the ⌘K path to "spawn agent X into worktree W as a new pane" (targeting a non-default worktree
   per spawn) needs to be wired or confirmed. Spawning currently defaults to the rooted worktree;
   explicit per-spawn targeting is the gap.
3. **Badge semantics communicate "default spawn target."** Small copy/affordance change so the
   badge is not misread as a destructive active-view marker.
4. **Director parity.** "Spawn into worktree W" must be the same API verb the human ⌘K uses
   (it is: `worktree_id` on the run request), so the director inherits it. No relaunch-shaped
   action that fragments the fabric the director observes.
5. **No new dependency on worktree CRUD.** SPAWN-INTO needs only selection among detected
   worktrees, which is live in the detect-only cut. Worktree creation/lifecycle stays deferred.

## Why this composes (the lens)

- **API-first / UI is one client of two:** SPAWN-INTO is the Launch verb already in the API.
  SWITCH-DESKTOP would be electron/CLI relaunch logic trapped outside the control plane.
- **One control plane / Observe:** all work stays inside `RunManager`, one observable fabric.
- **Git-worktree isolation:** honored by per-run port/PTY/run-dir isolation; worktrees run in
  parallel as panes.
- **Spaces identity:** one Space (shared git-repo history) holds N isolated Worktrees; coexistence
  is the model's native shape. "Two checkouts share history" = one Space, many Worktrees.
- **Zero-chrome watch surface:** you watch many worktrees' panes at once; you do not swap a
  single-document desktop.

## Open questions to verify next

- Does `initializeCanvas` preserve panes across a `defaultWorktreeId` change, or reset them?
  (Prerequisite 1; the one claim I did not read line-by-line.)
- Is per-spawn worktree targeting already reachable from ⌘K, or only the rooted-default path?
  (Prerequisite 2.)
- Should layer-1 channel relaunch ever be reachable from inside the running desktop, or stay a
  CLI-only/project-level action? Recommendation: keep it CLI/project-level to avoid reintroducing
  the destructive path into in-app worktree selection.
