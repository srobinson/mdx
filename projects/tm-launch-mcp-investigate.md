# Launch + MCP investigate (ml/s3-cmdk @ 0c76d520)

Status: **read-only**  
Branch: `ml/s3-cmdk` @ `0c76d520`  
Question: Stuart desktop report — "I cannot launch an agent via CMDK. I cannot test MCP."  
No tree writes.

---

## Summary classifications

| Problem | Class | One line |
|---------|-------|----------|
| **1. Agent launch via CMDK** | **REGRESSION** | Spawn affordance exists; S3-schema removed desktop inventory auto-seed + requires rooted `worktreeId`, so fresh desktop `defaultWorktreeId` stays null and spawn dies. |
| **2. MCP testability** | **SETUP** | Space MCP tools are mounted and registered; testing needs a granted run (`observer`/`director`) plus an MCP client (the agent), not a separate desktop surface. |

---

## 1. Agent launch via CMDK

### Classification: **REGRESSION**

Not "ABSENT spawn command". The Agents CMDK path still launches. What broke for a live Electron desktop is the **precondition**: a rooted worktree on the canvas after the S3 N:1 / no-default-bootstrap reshape.

### End-to-end path (present)

| Step | File + symbol | Behavior |
|------|----------------|----------|
| CMDK rows | `www/packages/canvas/src/launcher/templateRows.ts` `buildAgentRows` / `agentSpawnRows` | Agents scope: native claude/codex + specialists; action `{ kind: "command", command: { kind: "spawn", harness, agentId? } }` |
| Also | `commandRows.ts` (`cmd:spawn-empty-pane`, `cmd:spawn-terminal`) | Empty pane / bare terminal; terminal also needs rooted worktree |
| Dispatch | `useCommandCenter` → `onCommand` → `CanvasCommandDispatcher` | `case "spawn"` |
| Spawn gate | `CanvasCommandDispatcher` → `useCanvasStore.addCapturedRun` | Comments: throws without rooted worktree |
| Rooted check | `model/worktreeDefaults.ts` `requireWorktreeId` | Error: `"Cannot spawn a captured run without a rooted worktree"` |
| Pane create | `model/canvasActions.ts` `addCapturedRun` / `spawnCapturedRunPane` | Needs `worktreeId ?? defaultWorktreeId` |
| HTTP | `www/packages/core/src/transport.ts` `createCapturedRunView` | `POST /v1/runs` with mandatory `worktreeId` (comment: Spaces rekey; no launch-worktree fallback) |
| Runtime | `packages/runtime` `RunManager.createNew` → `capturePort.prepareCapture` | cwd from resolved worktree on capture path |
| PTY pane | `viewers/terminal/CapturedRunPane.tsx` + `useCapturedRunBinding` | After pane opens, `ensureRun` POSTs |

**CMDK launch affordance:** **PRESENT** (`LauncherCommand.kind === "spawn"`, Agents domain).  
**Not** only select-space/select-worktree/create-*; those are inventory. Launch is Agents → spawn.

### Does launch need Space → Worktree → Canvas?

Yes for a successful captured run:

1. **Client gate:** `defaultWorktreeId` or per-spawn `command.worktreeId` (`requireWorktreeId`).
2. **Server:** `POST /v1/runs` requires `worktreeId`; capture prepare resolves checkout via worktree ownership (`launch_resolution.resolve_run_worktree` / `SpaceCrudService.resolve_launch_worktree`).
3. **create_workdir** (`store_worktree_ops.ensure_worktree_root` + service create path) **does** auto-create a **worktree_root Canvas** and returns `rootCanvasId`.  
   `spaceCommandDispatcher.createWorkdir` then `activateWorktree({ spaceId, worktreeId, canvasId: rootCanvasId })`, which roots the canvas.  
   So inventoring a workdir **does** produce a launchable canvas **if** the user completes create-workdir (path required today; folder-picker still future).

Fresh install with **zero** Spaces:

- No meta seed (below) → `defaultWorktreeId === null`
- No inventory rows to select-worktree
- Spawn → throw → only `console.error` in dispatcher (non-fatal; feels like "nothing happened")

### S3 impact (why REGRESSION)

| Change | Evidence | Effect |
|--------|----------|--------|
| Removed lifespan auto-resolve | Pre-S3 `main._resolve_current_space` → `SpaceCrudService.resolve_cwd(..., create=True)` (gone in `df052e65` S3-schema) | Desktop API no longer materializes default Space/Workdir from process cwd at startup |
| No backend default Space | cm / S3-schema: 0..N equal spaces | Expected model, but desktop has no replacement seed |
| Meta affinity only from launch_fields | `api/v1/meta.py` `get_meta` → `affinity_from_launch_fields(settings.launch_fields)` | Desktop backend **strips** `LAUNCH_FIELDS` (`cli/desktop_cmd.py` `DESKTOP_BACKEND_STALE_ENV_KEYS`); meta `space_id`/`worktree_id` stay **null** |
| Canvas roots from meta | `SessionCanvasRoute` `adoptDefaultWorktree(meta.spaceId, meta.worktreeId)` only when URL has no worktree | With null meta, no automatic root |
| worktreeId mandatory | `transport.ts` `createCapturedRunView` comment | Explicit; no silent fallback to launch cwd |

CLI detached launch still bootstraps via `cli/space_bootstrap.bootstrap_cli_space` (create_space + create_workdir when empty). **Desktop API process does not call that.**

### What would make launch work

1. **Immediate user path:** CMDK create-workdir with an absolute path (creates Space if empty, activates root canvas) **or** select-worktree when inventory already exists → then Agents → spawn.  
2. **Product fix (desktop seed):** On desktop backend start (or first canvas open), compose the same approach-A bootstrap as CLI (`bootstrap_cli_space` / create_space + create_workdir for work_dir) and either set process `launch_fields` affinity for meta **or** have the UI adopt first owned worktree from `GET /v1/spaces`.  
3. **UX:** Surface spawn errors in UI (today only `console.error`); seed default worktree when sole Space has one worktree.  
4. Optional: folder picker scout path for create-workdir path entry.

Not required: reintroducing M:N default Space or computed membership.

---

## 2. MCP

### Classification: **SETUP**

(with launch as a hard dependency; not a missing S3 tool registration)

### Is the space/workdir MCP surface wired?

**Yes.**

| Piece | File + symbol |
|-------|----------------|
| Mount | `main.py` mounts FastMCP at `/mcp` (`create_control_plane_mcp`, `ControlPlaneMcpAuthApp`) |
| Space tools | `controlplane_mcp.create_control_plane_mcp` → `register_space_mcp_tools` |
| Tools | `space_mcp.register_space_mcp_tools`: `space_list`/`space_get`/`space_create`/`space_rename`/`space_delete`, `worktree_list`/`worktree_get`/`worktree_create`/`worktree_delete`, canvas_* |
| Auth | Bearer via `ControlPlaneMcpAuthApp` + `ControlPlaneTokenVerifier`; principal from grant (`CaptureRpcService.resolve_control_plane_grant` → live `space_id`/`worktree_id` on `ControlPlanePrincipal`) |
| Tests | `api/v1/test_space_mcp.py`, controlplane action skins allowlist includes space/worktree tools |

S3-schema/delete **did not** remove MCP registration; they reshaped tools (link/unlink gone; create/delete workdir + space delete present on this branch).

### How is MCP invoked / tested?

MCP is the **control-plane HTTP MCP server** consumed by a **granted captured run**, not a desktop UI panel.

1. User sets control plane grant before spawn: CMDK Settings cycles `controlPlaneGrant` (`capturedRunStore.cycleControlPlaneGrant`; options `none` \| `observer` \| `director`).  
2. **Default is `none`** (`packages/contract` `DEFAULT_CONTROL_PLANE_GRANT = "none"`). With `none`, `prepare_control_plane_grant` returns `None` — **no MCP client seeded into the agent home**.  
3. With `observer` or `director`, capture prepare (`controlplane/provisioning.prepare_control_plane_grant` + `seed_control_plane_client`) writes run-local MCP config pointing at `{web}/mcp` with a minted bearer.  
4. Agent harness then calls tools over MCP. Bound reads use principal `space_id`/`worktree_id`; director mutations use owner director tools.

There is **no** "Test MCP" button in canvas. External exercise = MCP Inspector / curl against `/mcp` with a valid run bearer, or a live granted agent.

### Gap vs Stuart "cannot test MCP"

| Factor | Class | Note |
|--------|-------|------|
| Grant left at `none` | **SETUP** | Must cycle grant to observer/director before spawn |
| No agent running | **depends on §1** | Launch regression blocks the normal MCP client (the agent) |
| Expectation of desktop MCP console | **SCOPE-GAP** | Product never exposed an in-canvas MCP tester; tools are agent-facing |
| Tools missing after S3 | **not found** | Registered on this branch |

### What would make MCP testable

1. Fix or manually satisfy launch (§1) so a pane agent starts.  
2. Settings → cycle control plane grant to **director** (or observer for reads).  
3. Spawn agent; use tools from inside the agent (or extract bearer and hit `/mcp`).  
4. Optional product: first-run hint that grant must be non-none for MCP; seed director in dev channel.

---

## Cross-check: not pure SCOPE-GAP on launch

| Hypothesis | Verdict |
|------------|---------|
| "No CMDK launch command" | False — `spawn` / Agents rows exist |
| "create_workdir doesn't make a canvas" | False — `ensure_worktree_root` + activateWorktree |
| "S3 deleted RunManager path" | False — still `POST /v1/runs` + prepareCapture |
| "S3 broke MCP registration" | False — `register_space_mcp_tools` still called |
| "Fresh desktop has nothing to launch into without manual inventory" | **True** — REGRESSION vs pre-S3 lifespan resolve_cwd seed |

---

## Bus reply line

`done: launch=REGRESSION, mcp=SETUP spawn-exists but rooted-worktree seed broken post-S3; MCP mounted needs grant≠none+agent ~/.mdx/projects/tm-launch-mcp-investigate.md`
