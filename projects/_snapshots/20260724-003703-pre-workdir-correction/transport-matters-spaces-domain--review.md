# Transport Matters — Spaces model: adversarial review (domain / naming / UX / director lens)

Reviewer: Claude `codebase-analyst` pane (`transport-matters:helioy-tools:codebase-analyst:1:4.1`)
Mode: Mode-1 peer consensus, independent adversarial pass. No coordination with the other pane.
Date: 2026-06-21
Repo state at review: `main` @ `2323169`, working tree pristine (verified before and after).
Artifact under review: `~/.mdx/projects/transport-matters-spaces--proposal.md` (LOCKED model), with
supporting `-spaces-domain--brainstorm.md` and `-spaces-feasibility--brainstorm.md`.

All code claims verified against the live tree via fmm + grep. Evidence cites file + symbol, never line-only.

---

## Verdict: CONDITIONAL sign-off

The orthogonal Space → {Worktree, Canvas} model is sound and the four locked decisions hold. Two
**Major** findings are corrections to the *filed model's prose and contract*, not to the core
shape: a stated invariant that the live pane refs falsify (F1), and a Decision-2 violation that the
live + contracted API already commits (F2). One Minor (F3) and one positive resolution that should
edit the doc (F4). None reject the locked nouns or axes.

---

## F1 — Major — The "every Pane is worktree-rooted" invariant is false for `terminal` and `resource(url|path)` panes

**Claim under test** (proposal, "Recommended model in one paragraph"): *"A Pane is a viewer bound to a
worktree-rooted run/session/resource — the point where the two axes meet."* The domain brainstorm §2
repeats it: *"Each pane resolves to a worktree-rooted content ref."*

**Evidence (live `PaneContentRef`, `www/src/session-canvas/model/paneRecords.ts`, symbol `PaneContentRef` [70–102]):**
- `terminal` ref = `{ kind: "terminal"; owner: "local"; label?: string }` — carries **no** `sessionId`,
  `runId`, `runKey`, or worktree field. It cannot resolve a worktree from its own ref.
- `resource` has a `{ source: "url"; url }` variant (inherently worktree-less) and a `{ source: "path"; path }`
  variant (an arbitrary filesystem path, not necessarily inside any worktree).
- The session/run-backed refs (`session-timeline`, `subagent-timeline`, `provider-exchange`,
  `captured-run`, `resource` via `sessionId`) *do* resolve a worktree indirectly through the session/run → `cwd` → `WorkspaceId`. Those degrade gracefully: a pruned/moved worktree keeps its session row (soft links, history preserved) and renders the existing `placeholder` viewer (`ViewerId` [40–47]). **That half of the model is fine.**

**Why it bites the LOCKED choice specifically.** Today the gap is masked because `CanvasModel`
(`paneRecords.ts`, symbol `CanvasModel` [50–58]) pins the **whole canvas** to one path via
`workspaceHash: string | null` + `cwd: string | null`, so a bare `terminal`/`url` pane inherits the
canvas's single cwd. But Decision 4 + Option 3 (the locked axes) explicitly enable *cross-worktree
canvases*: domain brainstorm §2 ("a Canvas may show panes from several Worktrees of its Space"),
Option 3 table ("Cross-worktree view ✓ (opt-in per pane)"), feasibility ("A Canvas can contain panes
from multiple Worktrees"). The moment a canvas spans worktrees, the single-cwd fallback evaporates and
a `terminal` pane (which *is* a live PTY process, i.e. it has a real placement) has no field to say
which worktree it runs in. The director's `launch(agent, into=Worktree)` and "observe active runs
across worktrees" (proposal §6) both require per-pane worktree attribution that the `terminal` ref
cannot supply.

**Root tension.** The feasibility doc already half-saw this ("Pane refs may carry `worktreeId` when a
pane has a launch target") and the schema already carries the graceful-degradation hook
(`canvas.default_worktree_id` / `Canvas.defaultWorktreeId`). But (a) `worktreeId` is *optional* and
*absent from the live `terminal` ref*, and (b) the proposal's one-paragraph model states worktree-rooting
as an **invariant**, contradicting its own schema's "default" fallback.

**Recommendation (one of):**
1. Make `worktreeId` a **required** soft-ref on every *spawnable/live-process* pane (`terminal`,
   `captured-run`), keeping it optional only for genuinely external `resource(url)`; OR
2. Soften the model's prose from "every Pane is worktree-rooted" to "a Pane resolves its worktree via
   its run/session ref, else inherits the Canvas's `defaultWorktreeId`; `resource(url)` panes are
   worktree-less by design" — and promote `Canvas.defaultWorktreeId` from schema detail to a named part
   of the domain model so the fallback is explicit, not implied.

The spec must pick one; the filed prose currently promises an invariant the code does not hold.

---

## F2 — Major — `workspaceId` leaks onto the director/API product surface, contradicting Decision 2

**Claim under test** (Decision 2, LOCKED): *"The Space/Workspace homophone exists only in code, never in
the product surface."*

**Evidence (live):** `api/src/transport_matters/api/v1/run_routes.py`, symbol `RunViewModel` [110–122]:
`workspace_id: str = Field(serialization_alias="workspaceId")`, populated by `_workspace_id_for_view`
([383–384]) → `workspace_id(view.cwd)`, and emitted on **every** run response
(create / list / terminate — `workspace_id=_workspace_id_for_view(view)` at [407]). So the run API
already serves `workspaceId` to its consumers today.

**Evidence (locked-forward contract):** the feasibility doc's API contract — carried forward into the
spec per Decision 3 — keeps `workspaceId` on **both** response interfaces: `interface Worktree { worktreeId; spaceId; workspaceId; ... }` and `interface Run { runId; spaceId; worktreeId; workspaceId; ... }`.

**The leak.** The voice director and ⌘K palette *are* the product surface (proposal §6, recommended-model
paragraph). They consume this API. A director therefore sees `spaceId`, `worktreeId`, **and**
`workspaceId` on the same `Run`/`Worktree` object — the precise three-way Space/Workspace/Worktree
homophone Decision 2 claims to have eliminated. "Internal storage key, never in product surface" is not
actually achieved by the contract as filed; it is contradicted by it.

**Recommendation:** drop `workspaceId` from public API responses — `worktreeId` already addresses the
path, and `WorkspaceId` is a derived Tier-1 storage key the director never needs. If it must remain for
Tier-1 addressing on some internal path, keep it out of the `Run`/`Worktree` *response* DTOs (or alias
it to a non-homophonic name). Either way, Decision 2's "never in the product surface" needs the contract
edited to match, or the decision text softened to "never as a *primary* product noun."

---

## F3 — Minor — "Space" collides with the existing `Space` gesture-modifier in the same ⌘K palette

**Claim under test** (proposal §6 / Decision context): the new top-level **Space** scope lands in the
command launcher (the ⌘K "Workdir" stub becomes "Space + Worktree scopes"). The domain brainstorm
dismissed the homophone risk as "`space` = dnd coordinate term only."

**Evidence:** the launcher's Settings scope already renders a row titled `Canvas gesture modifier: Space`
(`www/src/session-canvas/launcher/commandModel.ts`, `buildSettingsRows` [313–325], `title:
\`Canvas gesture modifier: ${modifier}\``), where `Space` is one of `CANVAS_GESTURE_MODIFIERS`
(`www/src/keybindings/gestureModifier`; asserted in `commandModel.test.ts` ["Settings scope reflects
Space as the current canvas gesture modifier"]). So "Space" is **already a user-facing palette string**
(the spacebar pan/zoom modifier), not merely an internal coordinate term — the brainstorm understated it.

**Severity rationale (Minor, not Major):** the gesture row's title is fully qualified ("Canvas gesture
modifier: Space"), so it is distinguishable from a top-level Space *scope* header. The collision is
cosmetic and resolvable with scope chrome / labels, but it lives in the exact surface (the launcher) the
proposal routes Space into, so it warrants a conscious labeling decision rather than silent acceptance.

**Recommendation:** confirm the Space scope presents with disambiguating chrome (scope label, e.g. a
"Project / Space" header), and verify no settings query like "space" surfaces both the scope and the
gesture-modifier row ambiguously. One-line check during the launcher slice.

---

## F4 — Positive (probe-#4 resolved) — "Canvas" is correct; strike the "rename → Surface" fallback as a dead option

**Claim under test** (Decision/agreement #4, and the proposal's residual escape hatch): keep "Canvas";
Codex's fallback "if the UI stays confusing: rename → `Surface`."

**Finding:** the locked "keep Canvas" is right, and the **Surface fallback is foreclosed by live code** —
it is not actually available. "Surface" is already a heavily shipped noun *for the canvas's own rendered
drop layer*: the React component is `CanvasSurface.tsx` (`www/src/session-canvas/components/CanvasSurface.tsx`),
`useCanvasDropTargets.ts` references "surface" ~14×, and `viewers/terminal/terminalSession.ts` ~9×.
Renaming `Canvas → Surface` would collide head-on with `CanvasSurface` (which means *the surface of the
canvas*), producing worse confusion than the problem it tries to solve. Combined with Canvas being the
shipped data noun (`CanvasModel`, `CanvasId`, route `parseCanvasLaunchContext`) and an accurate
pan/zoom metaphor, Canvas is the only clean choice.

**Recommendation:** the locked decision needs no change, but the proposal should **delete the
"rename → Surface" fallback line** rather than carry it as a live option — it is structurally unavailable
and would mislead the spec. (Non-blocking doc hygiene.)

---

## Probes that came back clean (positively justified, no issue)

- **Director / cmd-K parity (probe 3) for Space/Worktree/Run.** Observe / launch / manage / prompt all key
  cleanly off the three nouns; the `WorkspaceId`-keyed capture spine stays addressable. The one gap worth
  a sentence: the **Canvas axis has no director *verb*** in the locked enumeration (it is "director-readable
  projection" only). That is consistent with detect-only-first + "Canvas store is a sync target, not owner,"
  so I am **not** filing it — but the spec should state explicitly that the director can *observe/select* a
  Canvas yet not *create/mutate* one, so the absence is a decision rather than an oversight.
- **Graceful degradation for session/run panes whose worktree was pruned/moved.** Soft links
  (`SessionRow.workspace_slug` / `workspace_hash`, no FK — `api/.../session/models.py` symbol `SessionRow`
  [58–82], confirmed no `space_id`/`worktree_id` today) + the existing `placeholder` viewer mean history
  survives and the pane renders a placeholder. Invariant holds for this class. (The *only* unhandled class
  is the non-session panes of F1.)

---

## Net

Sign off **conditional on F1 and F2** (model prose / API contract corrections), with F3 as a launcher-slice
check and F4 as a doc-hygiene delete. The locked nouns (Space / Worktree / Canvas / Pane), the orthogonal
axes, uuid4 identity, detect-only-first, and one-Space-per-Canvas all stand.
