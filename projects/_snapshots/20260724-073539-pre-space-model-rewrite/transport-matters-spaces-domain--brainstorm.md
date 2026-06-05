# Transport Matters — Spaces domain model (brainstorm)

Date: 2026-06-21
Status: BRAINSTORM (Mode 4) — design proposal, not a slice plan
Lens: domain modeling / ubiquitous language / UX + director-API surfacing
Grounding: `api/.../workspace.py`, `api/.../run_models.py`, `api/.../session/models.py`,
`www/src/session-canvas/model/{paneRecords,canvasStore}.ts`, north-star + NOW.md (all verified)

---

## TL;DR (the verdict in six lines)

1. **"Canvas" is the right word — but it is NOT the level below Space.** Canvas is a
   *view*, not a *unit of work*. Stuart's intuition fused two things: the work area
   (**Worktree**) and the viewport over it (**Canvas**). Split them.
2. The level below Space is the **Worktree** (a working area where agents actually run).
   **Today's path-derived `Workspace` already lives at this granularity** — so the capture
   spine needs *no re-keying*. Space is a brand-new layer **above** it.
3. **Recommended hierarchy: orthogonal axes.** `Space → Worktree` is the capture/identity
   spine; `Space → Canvas` is the view axis; they meet at the **Pane**. Neither
   worktree nor canvas owns the other.
4. Repo-ness is detected per startup from `git --git-common-dir` (the natural **Space**
   identity for a repo) and persisted server-side, additively.
5. Migration is **additive, zero storage re-key**: keep `workspace_slug/hash` and
   `~/.transport-matters/workspaces/{slug}/{hash}/`, add a `Space` record + `space_id` ref.
6. One naming call is Stuart's: **keep `Workspace` as the leaf** (zero churn) vs **rename
   leaf → `Worktree`** (kills the Space/Workspace homophone, mechanical rename, no re-key).

---

## 1. What the code says today (grounded)

| Concept | Symbol / file | Identity / shape | Granularity |
|---|---|---|---|
| **WorkspaceId** | `workspace.py` frozen dataclass | `slug` (last 3 path segs, sanitized ≤40) + `hash` = `blake2b(canonical_posix, 4)` + `root` (resolved CWD). Pure value object. **No git detection at all.** | **One canonical path** |
| **ManagedRun** | `run_models.py` | `run_id`, `cwd: Path`, `state`, `spawn_spec`, `terminal` (PTY), `terminal_output` (scrollback ring), `lease`, timestamps. Roots at `workspaces/{slug}/{hash}/{run_id}/`. Workspace derived from `cwd`. | Per spawn, under a path |
| **SessionRow** | `session/models.py` Pydantic | `session_id` PK, `run_id`, **`workspace_slug` + `workspace_hash`** (soft-ref), `cwd`, `provider`, `harness`, `owner="local"`, `native_session_id`. | Per transcript, soft-refs path |
| **CanvasModel** | `www/.../canvasStore.ts` | `id`, `owner="local"`, `workspaceHash \| null`, `cwd \| null`, `layout` (EngineLayoutState), `panes`. zustand→localStorage, single key, in-app keyed by `(workspaceHash, cwd)`. | One path's view |
| **PaneRecord** | `paneRecords.ts` | `paneId`, `viewerId` ∈ {terminal, captured-run, session-timeline, subagent-timeline, provider-exchange, resource, session-picker}, `contentRef`. | A viewer |

Free to redefine (confirmed cold): **`workdir`** = CLI `--work-dir` param only, no domain
meaning; **`worktree`** = test-fixture-only; **`space`** = dnd coordinate term only.

**The load-bearing observation:** identity = canonical path means **each git worktree
directory is already its own `Workspace`** (different path → different hash → separate
history). There is no concept today that groups them. So "two checkouts share history"
means *same path resolved two ways*, not *two worktrees of one repo*. Stuart is asking for
the missing grouping layer.

## 2. Proposed ubiquitous language

- **Space** — *a project or area of work the human cares about.* May or may not be a git
  repo; repo-ness is **detected and persisted every startup**. The top aggregate. Groups
  Worktrees and Canvases. Identity: the repo's `git-common-dir` (if a repo) else the
  canonical directory path. Holds: name, `is_repo`, repo metadata, worktree set.
- **Worktree** — *a concrete working directory belonging to a Space, where agents run and
  capture is rooted.* For a repo Space these are the git worktrees (main + `git worktree
  add`); for a non-repo Space there is exactly one (the directory itself = the Space's
  default area). **This is today's path-derived `Workspace` identity, unchanged.** Owns
  Runs, Sessions, tier-1 capture. Carries: path, branch (if repo), `is_primary`.
- **Run** — *a live spawned agent process inside a Worktree.* Unchanged
  (`ManagedRun`/`RunManager`).
- **Session** — *a transcript event record for a Run.* Unchanged (`SessionRow`); already
  soft-refs the Worktree via `slug+hash`; gains an optional `space_id`.
- **Canvas** — *a Space-scoped spatial view: a saved arrangement of Panes over a Space's
  runs / sessions / resources.* One Space → many Canvases (saved dashboards). **Orthogonal
  to Worktrees** — a Canvas may show panes from several Worktrees of its Space.
- **Pane** — *one viewer inside a Canvas* (the 7 existing viewer types). Each pane resolves
  to a **worktree-rooted** content ref. The Pane is where the view axis and the capture
  axis intersect.

## 3. Stuart's question, answered directly

**Is "Canvas" the right word for the level below Space? — No, because that level is two
things, and Canvas is only one of them.**

- Keep **"Canvas"** for the *spatial viewing surface*. It is the shipped noun
  (`CanvasModel`, `session-canvas/`, the zero-chrome desktop), it is already first-class in
  the north star ("every workspace, canvas, and pane"), and it is an *accurate* metaphor:
  an infinite pan/zoom surface where you arrange viewers (`EngineLayoutState`, viewport,
  dnd). Alternatives considered and rejected — *View / Board / Workbench / Desk / Scene* —
  none beats the shipped, accurate noun. Renaming would be churn for churn.
- But the work multiplicity under a Space is **Worktrees**, not Canvases. "One Space → many
  Canvases" is a *viewing* multiplicity (several saved arrangements of the same project).
  "One Space → many Worktrees" is the *work* multiplicity (main branch + feature branch
  worked at once). Conflating them is the trap; the fix is to name both.

**Where do worktrees sit relative to Canvas? — Beside, not nested.** Worktree is the
*capture/placement* axis; Canvas is the *viewing* axis; they intersect at the Pane (a Pane
= a viewer bound to a worktree-rooted content ref). This mirrors TM's founding instinct —
two orthogonal streams (wire vs transcript) — and the north star's "canvas projection keyed
by workspaceId, capture ids as soft refs."

## 4. Repo detection + persistence (the explicit requirement)

On every launch/startup, for the resolved cwd:

```
git -C <cwd> rev-parse --is-inside-work-tree --show-toplevel --git-common-dir --abbrev-ref HEAD
git -C <cwd> worktree list --porcelain          # enumerate sibling worktrees + branches
```

- **Space identity** = `is_repo ? hash(realpath(git_common_dir)) : hash(canonical_cwd)`.
  The `git-common-dir` is shared by *all* worktrees of one repo — it is the natural Space
  key. A non-repo directory is a degenerate single-Worktree Space.
- **Worktree identity** = today's `hash(canonical toplevel/cwd)` — **unchanged value**, so
  existing runs/sessions keep their history.
- **Persist a Space record** (server-side, the Observe substrate): `{space_id, name,
  is_repo, repo_common_dir, default_branch, origin?, worktrees: [{workspace_hash, path,
  branch, is_primary}], detected_at}`. On each startup, reconcile the worktree list (adds /
  removes from `git worktree list`); a removed worktree keeps its history, marked detached.
- **Storage:** new `spaces` (+ `space_worktrees`) tables in Postgres; mirror a `space.json`
  in tier-1 for the no-DB degraded mode (NOW.md no-DB track). API owns it; director reads
  via MCP, www via REST — no UI-only logic. Cheap (a few git calls), honest each startup.

## 5. The hierarchy fork (Stuart's "canvas-owns-worktrees vs worktree-owns-canvases")

**Option 1 — Worktree owns Canvases** (`Space → Worktree → Canvas → Panes`)
Strict nesting; a Canvas is bound to one worktree path. **Closest to today**
(`CanvasModel.cwd` already pins a canvas to a path) → smallest model change.
*Trade-off:* no single view spans worktrees; comparing main vs feature means switching
canvases / windows. Good if "a canvas = the desk for this branch."

**Option 2 — Canvas owns Worktrees** (`Space → Canvas → Panes`, worktree is a pane attr)
The Canvas is the project cockpit; worktrees are just placement targets for the runs shown
as panes. One canvas, panes from many worktrees. *Trade-off:* bigger change — `cwd` moves
off the canvas down to pane/run; each pane carries its own worktree ref; "which worktree is
this canvas in" loses meaning. Richest "watch the whole project" view; matches the
zero-chrome desktop vision.

**Option 3 — Orthogonal axes (RECOMMENDED).**
`Space → Worktree` (capture/identity spine) **and** `Space → Canvas` (view), meeting at the
**Pane**. Neither owns the other. A Canvas defaults to one worktree's filter (the common
case, identical to today) but *may* pin panes across worktrees of the same Space (Option 2's
power) without forcing the canvas to "own" worktrees, and keeps Option 1's clean capture
spine without trapping the view inside it.

| | Opt 1 nest | Opt 2 cockpit | Opt 3 orthogonal |
|---|---|---|---|
| Model change | smallest | largest | small-medium |
| Cross-worktree view | ✗ | ✓ | ✓ (opt-in per pane) |
| Capture spine clarity | ✓ | muddied | ✓ |
| Matches north-star projection | partial | partial | ✓ (workspaceId-keyed + soft refs) |
| Director mental model | nested walk | view-first | placement vs view cleanly split |

**Recommend Option 3.** It is the only one where the two real concerns (where work runs vs
how the human looks at it) stay independent, which is exactly what keeps "no UI-only logic"
honest: launch/observe/manage/prompt all key off `Space + Worktree + Run`; Canvas is a
director-readable *projection*, never a place logic hides.

## 6. Director + ⌘K surfacing (observe / launch / manage / prompt)

The ⌘K palette has disabled "Workdir + Sessions" scope stubs (NOW.md). Map them onto the
new nouns; the voice director reads the *same* operations over MCP:

- **Space scope** (replaces the "Workdir" stub): pick/observe a Space — `is_repo` badge,
  branch set, active runs across worktrees, saved canvases. `observe(space_id) → {worktrees:
  [{branch, runs}], canvases: [...]}` is the director's "full context" at project grain.
- **Worktree granularity** (the missing *placement* axis): `launch(agent, into=Worktree)`.
  For a multi-worktree repo Space, the palette inserts a worktree/branch sub-step; for a
  single-worktree Space it is skipped (zero-config fast path preserved — north-star lens #5).
- **Run granularity** (unchanged): `prompt(run_id, turn)`, `manage(run_id, action)`.

Net: **Space and Worktree become first-class placement nouns**, not just Run — which is
precisely what the launcher's "Workdir" placeholder was gesturing at, and what the director
needs to launch into the right branch by voice.

## 7. The one naming decision (Stuart's call — what/why)

The leaf aggregate ("a working area in a Space") needs a name:

- **(A) Keep `Workspace` as the leaf** — zero rename, zero re-key, purely additive Space
  layer; "worktree" becomes a *git-species descriptor* on a Workspace ("this Workspace is
  git worktree `feature-x`"). **Cost:** the Space/Workspace near-homophone. *Lowest blast
  radius; recommended on DRY/churn grounds.*
- **(B) Rename leaf `Workspace → Worktree`** — kills the homophone, makes the multiplicity
  Stuart wants first-class in the vocabulary. **Cost:** mechanical rename of the type name
  + UI strings (the identity *value* — slug+hash+root — is byte-identical, **no data
  migration**); slight awkwardness calling a non-repo Space's single area a "worktree."

I lean **(A)** for minimal blast radius, but this is a what/why call. Either way the
*storage* (`workspace_slug/hash`, `workspaces/{slug}/{hash}/`) stays put.

## 8. Migration / blast radius

- **Additive, zero re-key.** Keep `workspace_slug`, `workspace_hash`, the on-disk
  `workspaces/{slug}/{hash}/{run}/` tree, and the `WorkspaceId` value computation.
- **New:** `spaces` / `space_worktrees` tables; an optional `space_id` column on
  `SessionRow` (nullable, backfillable by running git detection over each existing `cwd`).
- **www:** `CanvasModel` keeps `workspaceHash`; gains an optional `spaceId`. Under Option 3,
  a pane's `contentRef` carries its worktree ref (most already imply it via the run/session).
- **Repo detection** is a new small service at launch-resolve time (`launch_runtime.py` /
  `RunManager` seam) + a startup reconcile. No change to capture bytes.

## 9. Open questions

1. **Non-repo "worktree"** wording — is "default area / main worktree" acceptable for a
   non-repo Space, or does that push toward keeping `Workspace` (Option 7A)?
2. **Canvas ↔ Space binding** — is a Canvas always exactly one Space, or can a "scratch"
   canvas hold panes across Spaces? (Recommend one-Space for now; cross-Space is a later
   power-user surface.)
3. **Worktree lifecycle ownership** — does TM ever *create* git worktrees (`git worktree
   add` as a Manage verb), or only detect/observe ones the user makes? (Detect-only first;
   create is a natural later Launch/Manage extension.)
4. **Space naming** — auto from repo `origin`/dir name vs user-editable label persisted on
   the Space record.
5. **Identity when a worktree moves** — path-derived hash changes if a worktree dir is
   moved; the Space's `git-common-dir` is stabler. Worth a stable per-worktree id keyed off
   git worktree metadata rather than path? (Defer; path identity is fine for v1.)
