---
title: "TM Rebuild Scout — Frontend Control Model (iterate vs rebuild)"
type: research
tags: [transport-matters, frontend, launcher, command-model, north-star, control-plane, scout]
summary: "Frontend ⌘K control model is a clean, pure, unit-tested model with a thin launch seam; the North Star gap is a missing shared operations seam + MCP client + server-side PROMPT/MANAGE verbs — extraction & addition, not a frontend redraw. Verdict: HYBRID."
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
baseline: "main @ HEAD e3aaecf (tree verified pristine; read-only scout)"
---

# TM Rebuild Scout — Frontend Control Model

## Verdict (top line)

**HYBRID — iterate (extract) the frontend control layer; build the missing control-plane verbs server-side. Do NOT rebuild the frontend.**

Single decisive piece of evidence: `commandModel.ts` is already a framework-free control model (its own docstring: *"No React, no stores"*), ~75% headless-drivable, and covered by a **494-LOC / 37-case pure unit suite** (`commandModel.test.ts`). The control model a rebuild would produce *already exists and is tested*. The North Star gap is not "logic trapped in the renderer that needs redrawing" — it is the **absence of (a) a shared operations seam both clients call, (b) a second (MCP/CLI) client adapter, and (c) server-side PROMPT/MANAGE verbs.** Those are extraction + net-new, and a frontend rebuild would have to build them anyway while discarding the one part that is correct.

---

## 1. Architecture map — where launch/scope/gesture/recommendation logic lives (Q1)

`commandModel.ts` (573 LOC) is the pure control model; React hooks consume it; one leaf in `CanvasSurface.tsx` executes the effect.

| Cluster (file · key symbols) | ~LOC | Purity | Coupling |
|---|---|---|---|
| Verb vocabulary — `LauncherCommand`, `LauncherEffect`, `RowAction`, `Lifecycle`, `Interaction` (`commandModel.ts`) | ~35 | **Pure** | discriminated unions only |
| Interaction tables — `COMMAND_INTERACTIONS`, `EFFECT_INTERACTIONS`, `interactionFor`, `RUN_AND_CLOSE` (`commandModel.ts`) | ~20 | **Pure** | static `RowAction → Interaction` lookup |
| NavFrame transforms — `pushFrame`, `popFrame`, `updateTopFrame`, `topFrame`, `createScopeNavFrame` (`commandModel.ts`) | ~50 | **Pure** | array transforms; *but the live stack is React `useState`* |
| Recommendation/launch decision — `templateSpawnHarness`, `recommendedSubtitle`, `vendorNativeHarness` (`commandModel.ts`) | ~60 | **Pure** | derivation over `RuntimeTemplateSummary` — the harness/vendor/model/effort choice computed as **data** |
| Row builders — `buildScopeRows`, `agentSpawnRows`, `buildCanvasRows`, `buildSettingsRows`, `buildSpaceRows`, `buildWorktreeRows`, `buildDeferredRows`, `filterRows`, `groupRows` (`commandModel.ts`) | ~250 | **Pure** | `(inputs, scope, query) → CommandRow[]`; no JSX |
| `useLauncherRows` (`useLauncherRows.ts`) | ~110 | **Mixed** | `useMemo`/`useEffect`, builds Ark `createListCollection`, takes `setHighlighted` |
| `useCommandCenter` incl. `useNavFrameStack`, `useLauncherActionInterpreter` (= `applyGesture`) (`useCommandCenter.ts`) | ~300 | **React** | `useState`/`useRef`, `document.activeElement`, `window` listeners, caret `selectionStart`; **live nav stack lives here** |
| Leaf executor — `useCanvasCommandHandler` (`CanvasSurface.tsx`) | ~55 | **React** | zustand actions, `window.history.replaceState`, `parseCanvasLaunchContext` — the only place a `LauncherCommand` becomes an effect |

**Headless-drivable fraction: ~75%.** All row/scope/recommendation derivation is pure and portable. The ~25% a headless director could *not* reproduce is render/focus mechanics, not decisions: the **nav-stack interpreter** (`applyGesture` + `useNavFrameStack` held in React state) and the **leaf executor** (`useCanvasCommandHandler`), which sources `worktreeId` + `bypassPermissions` from zustand (`useCanvasStore`, `useCapturedRunStore`) rather than from its caller — so the *fully assembled* spawn request only exists inside React.

---

## 2. North Star gap — is there a control-plane client seam? (Q2)

**Frontend seam verdict: PARTIAL (thin).** The only React-decoupled, headlessly-callable seam is `createCapturedRun` (`www/src/api.ts`) → `POST /v1/runs`. Everything above it — intent resolution, request-parameter sourcing, dispatch — is fused into React hooks/zustand. The decisive citation: the spawn dispatcher is a `useCallback` switch, `useCanvasCommandHandler` (`CanvasSurface.tsx`), whose `case "spawn"` calls the zustand action `addCapturedRun` → `useCapturedRunStore.ensureRun`, and `ensureRun` reads `get().bypassPermissions` from store state. **There is no shared typed operations layer that the palette and a director both call — the palette *is* the orchestrator.**

**Server-side control plane: it already exists for launch/lifecycle.** `RunManager` (`api/src/transport_matters/run_manager.py`) is a genuine domain service on `app.state.run_manager`; REST (`run_routes.py`) is a thin adapter. The UI is *already* just one HTTP/WS client of it.

| Verb | Backend (symbol) | UI client (`api.ts`) | On RunManager? |
|---|---|---|---|
| **Observe** runs | `list_runs`, `get_run`, `run_terminal_socket` (WS) | `listRuns`, `getRun`, `terminalSocket` | ✅ `.list/.get/.attach` |
| **Observe** transcript/spaces | `list_sessions`/`stream_session_*`, `list_spaces`/`list_space_worktrees`/`list_space_canvases`, `get_runtime_templates` | `fetch*` family | via SessionStore/SpaceStore (not RunManager) |
| **Launch** spawn | `create_run` → `POST /v1/runs` | `createCapturedRun` | ✅ `.spawn` |
| **Manage** terminate | `terminate_run` → `POST /v1/runs/{id}/terminate` | `terminateRun` | ✅ `.terminate` |
| **Manage** interrupt / arrange / focus / detach | **NONE** (raw PTY bytes, or client-only canvas-store mutations) | local store only | — |
| **Prompt** inject a turn | **NONE** | **NONE** | — |

Two structural facts decide feasibility:

1. **Launch decision is computed in the browser; only a thin spec is sent.** `CreateRunRequest` (`run_routes.py`) carries `harness`, `worktree_id`, `runtime_template` (a *string* the server re-resolves via `resolve_runtime_template`), `bypass_permissions`, `osc_color_replies`, `continue_from_session_id`, `idempotency_key`. Vendor/model/effort are **never sent** — they are client-side metadata from the template's `recommended_model`. This is the **parallel-implementation risk** the North Star warns about: a director would re-derive the spawn target unless it shares `templateSpawnHarness`/`recommendedSubtitle`.
2. **No MCP/CLI control surface exists** (zero `fastmcp`/MCP-server hits). REST + WS is the only client. The CLI is launch/diagnostic only; `cli/prompt.py` is launch-time `--append-system-prompt`, not turn injection.

**Could Workdir/Sessions be shared control-plane verbs given current shape?** Yes for the read side — `buildWorktreeRows`/`buildSpaceRows` already render server data (`fetchSpaces`/`fetchWorktrees`), and Workdir maps to Launch *placement* (the `worktree_id` already on `CreateRunRequest`). Sessions maps to **Observe** and would wrap the shipped transcript reader. Neither needs a frontend rebuild to become a verb; both need the *operations seam* (below) so the director shares the same call.

---

## 3. Quality map (Q3)

**No guardrail violations.** Largest file `commandModel.ts` 573 LOC (< 700); largest functions all < 150 LOC (`buildSettingsRows` ~40). Duplication is notably clean — the model/hook split is disciplined; the hook calls `buildScopeRows`/`filterRows`/`groupRows` rather than re-implementing them. Boundaries are clean: `commandModel.ts` imports no React and no stores (verified) — genuinely portable.

Findings (severity-ranked):

- **[MEDIUM] DRY/contract drift — `openScope`.** `keybindings/registry.ts` (`LauncherKeybindingTarget.openScope`) types the arg as `"agents" | "settings"`, while `useLauncherHotkeys.ts` (`LauncherHotkeyHandlers`) types it as `LauncherScope` (7 scopes). Two sources of truth for one contract; a third accelerator scope can't be added without editing both. No runtime bug today.
- **[MEDIUM] Dead module — `keybindings/format.ts::formatBinding`.** Sole export, **zero non-test consumers** (verified by grep); 88 LOC + a 42-LOC test maintained for nothing. Delete.
- **[LOW] `commandModel.ts::buildDeferredRows`** is a single-caller stub — only `buildScopeRows case "sessions"` uses it; the `sessions` domain ships as an enterable row that descends into one disabled "lands next" placeholder. Wired-but-empty scope (accretion residue).
- **[LOW] Doc drift — `DELETE /runs/{id}`.** Project `CLAUDE.md` says the canvas close affordance issues `DELETE /runs/{id}`; **that route does not exist** (verified — only `POST .../terminate`). Fix the doc or the claim.
- **[LOW] Scope-specific interaction divergence (coherence).** `cycle-theme`/`toggle-bypass-permissions` use `{enter:"commit-close", advance:"run-stay"}` so `↵` closes without firing and only `→` mutates — intentional and documented, but a per-command exception readers must learn.

**Test shape:** strong portability signal — `commandModel.test.ts` is a 494-LOC pure unit suite (37 cases) with no React; the hook layer is lightly covered. The control model is decoupled and independently tested — exactly the shape that makes it cheap to extract.

**Coherence verdict: mildly-accreted.** One coherent design (single `buildScopeRows` dispatch, single `interactionFor` table, uniform `enter`/`advance` lifecycle, exhaustive interpreter). Accretion is confined to edges: the 7-scope set grew slice-by-slice (`sessions` still deferred), the `openScope` contract was never re-unified, and `format.ts` is orphaned. This is an iterate target, not a rebuild target.

---

## 4. Reuse map — what carries into a server-side-control-plane rebuild (Q4)

**Carries unchanged / high value:**
- `commandModel.ts` — the entire pure grammar: `Lifecycle`/`Interaction`/`RowAction` model, `interactionFor`, NavFrame transforms, all `build*Rows`, and the recommendation derivation (`templateSpawnHarness`/`recommendedSubtitle`). This **is** the action-model verbs, and it is liftable. Moving `templateSpawnHarness` to share with the server (the `runtime_registry` already serves templates) is the cleanest kill of the parallel-implementation risk.
- `commandModel.test.ts` — 37 pure cases; the regression net for any extraction.
- The **Ark Combobox shell** (`CommandCenter.tsx`) and the presentational `CommandRow` data model — Ark owns input/highlight/ARIA; commandModel owns rows/actions/lifecycle. Correct boundary; keep.
- **Server side:** `RunManager` + `run_routes.py` (launch/lifecycle is already API-first), `createCapturedRun`, the `runtime-templates` read path.

**Wrong-shaped / must be lifted or built (not redrawn from scratch):**
- The **nav-stack interpreter** trapped in React (`useNavFrameStack` `useState` + `applyGesture` in `useCommandCenter.ts`) → lift into a framework-free reducer over the already-pure `pushFrame`/`popFrame`/`updateTopFrame`.
- The **leaf executor** (`useCanvasCommandHandler`) → replace with an `operations`/client module, e.g. `launchAgent({harness, runtimeTemplate, worktreeId, bypassPermissions})`, that both the palette and a director call (today `worktreeId`/`bypassPermissions` are pulled from zustand inside `ensureRun`).
- The **keybinding engine** (`engine.ts`/`registry.ts`): a data-driven `COMMANDS` registry but DOM-bound — `CommandContext` requires a `KeyboardEvent`, binding installs via `tinykeys(window, …)`, `run` bodies call `ctx.event.preventDefault()`. A director has no intent entry point; needs an intent path alongside the keyboard path.
- **Server net-new (required regardless of iterate/rebuild):** PROMPT verb (unbuilt — only raw PTY bytes today), MANAGE interrupt/arrange/focus (UI-only canvas concepts), a server-readable canvas/pane projection (North Star structural consequence #1), and a TM control MCP/CLI adapter (#2).

---

## 5. Cost asymmetry & adversarial check (Q5)

**Iterate/extract path** — lift the interpreter + executor into a framework-free `controlModel` reducer and an `operations` client module; share `templateSpawnHarness` with the server. Blast radius: `useCommandCenter.ts`, `CanvasSurface.tsx` (`useCanvasCommandHandler`), `capturedRunStore.ts`, plus the `operations` module — a handful of files, all guarded by the 494-LOC unit suite. Then add the MCP adapter over the existing `RunManager`, and build PROMPT/MANAGE server-side.

**Rebuild path** — re-derive a control model that is already pure, coherent, and tested; re-integrate Ark; re-author the 37-case suite; **and still** build the same server-side verbs + MCP adapter. Pays a large cost to recreate the correct part and gains nothing on the actual gap.

**Adversarial counter (steelman for rebuild):** under a maximalist North Star reading ("operations live in the API, never the UI"), even a clean client-resident model is "in the wrong place" — the row/recommendation logic arguably belongs server-side so palette and director literally share code. **But the conclusion is still not a frontend rebuild:** that argument says *relocate the model behind the control plane and keep the presentational shell* — a move, not a redraw, and the recommendation logic being pure data is exactly what makes the move cheap. A from-scratch frontend rebuild is strictly dominated: it discards the tested model and the correct Ark boundary while solving none of the server-side gap.

**VERDICT: HYBRID.** Iterate/extract the frontend control layer (lift interpreter + executor into a shared operations seam; share the recommendation derivation with the server); build the missing control-plane verbs (PROMPT, MANAGE interrupt/arrange/focus), the canvas/pane projection, and the MCP/CLI adapter greenfield server-side. The frontend control model is the asset, not the liability.

### Suggested plan (slice order)
1. **Extract `operations` client module** out of `ensureRun`/`useCanvasCommandHandler` — `launchAgent(spec)` taking an explicit spec (no zustand reads). Palette calls it; it is the seam a director inherits. (Unit suite + existing e2e protect this.)
2. **Lift the nav-stack interpreter** (`applyGesture` + live stack) into a framework-free reducer over the pure `pushFrame`/`popFrame` transforms; `useCommandCenter` becomes a thin React binding.
3. **Share `templateSpawnHarness`/recommendation** with the server's `runtime_registry` (or send vendor/model/effort on `CreateRunRequest`) to kill the parallel-implementation risk.
4. **Server net-new:** PROMPT verb on `RunManager` + route; MANAGE interrupt/arrange/focus; canvas/pane projection (workspaceId-keyed, soft refs); a TM control MCP adapter over the same domain services.
5. **Hygiene (cheap, do alongside):** delete `keybindings/format.ts`; unify the `openScope` contract; fix the `DELETE /runs/{id}` doc drift; design the `sessions` deferred scope as an Observe verb.

### Verification gates for the iterate slices
`cd www && pnpm test` (esp. `commandModel.test.ts`), `pnpm typecheck`, `pnpm lint`; `cd api && just check && just test`; existing launcher e2e. No slice ships without the pure-model suite green.
