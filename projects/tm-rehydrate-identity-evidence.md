# Reload → cannot launch: first-hand evidence (2026-07-25)

Live-product evidence gathered by Stuart + orchestrator against a running desktop.
Everything below was observed, not inferred. Do not re-litigate these facts; use
them as the ground truth your scout report must explain.

## Environment

- Build: `transport-matters 0.3.0.post1.dev355+g4e0f0e5da` (tip of `ml/s4-adoption`, `4e0f0e5d`).
- Store: freshly reset (`scripts/reset-channel-store.sh --force`), schema `0032_space_worktree_ownership`, 0 data rows, tier-1 capture swept.
- Desktop: `transport-matters desktop --foreground`, API on `127.0.0.1:8788`.
- Settings: Control plane access = **Director** (this is what injects MCP tools into spawned agents), bypass permissions on.

## The failure

After refreshing the desktop, a CMDK launch fails with:

```
Claude captured run failed to start: Canvas launches require spaceId, worktreeId, and canvasId
```

## Setup that preceded it (all worked)

1. Space **MS1** created via CMDK, worktree `.claude/worktrees/multi-launch` (`ml/s4-adoption`) selected. Both badged Current.
2. CMDK launched three panes: `Claude-1` (native claude), `Codex-1` (native codex), `Claude-2` (`tm/orchestrator`, MCP orchestrator). All live, correct vitals and status bars.
3. `Claude-2` launched two more via the MCP launch tool: `1d604766` (`tm/imagegen`, codex) and `fed85590` (`tm/codebase-mapper`, claude).
4. MCP `space_create` / `worktree_create` inventoried `…/helioy/cubicell` into MS1 and `…/helioy/manicure.sh` into MS2.

## Pre-reload capture: all three identity sources are incomplete

Captured first-hand while the desktop was still up.

1. **`GET /api/meta` on `:8788`** returns:
   ```json
   { "cwd": ".../.claude/worktrees/multi-launch",
     "workspace_id": "claude-worktrees-multi-launch/2043e1eb",
     "run_id": null, "space_id": null, "worktree_id": null, "canvas_id": null }
   ```
   All three identity fields null, while the DB holds worktree `747d7569-4f9a-4c34-9374-fb362f860e23` for exactly that `cwd`.

2. **Route URL** (from the `transport_matters.backend_started` event):
   `http://127.0.0.1:8788/canvas?owner=local&workspace_hash=2043e1eb` — carries no `spaceId`, `worktreeId`, or `canvasId`.

   **CORRECTED 2026-07-25 by scout cross-check.** That is the *boot* URL, before the
   app rewrites it. At *reload* the client did hold a scoped URL tuple: the `Current`
   badge requires a non-null `defaultWorktreeId`, and the server returning 400 rather
   than a `worktreeDefaults.ts:requireWorktreeId` throw requires a non-null
   `worktreeId`. So the failing state is **identity present but never verified**, not
   identity absent. Any fixture that boots from an empty URL tests the wrong state and
   will pass while the product stays broken.

3. **Persisted renderer state** (Electron local storage under
   `~/Library/Application Support/Transport Matters/Local Storage/leveldb`):
   persisted `contentRefs` carry `worktreeId` per pane, e.g.
   ```json
   {"kind":"captured-run","owner":"local","provider":"claude",
    "runKey":"claude:ff2a5d6f-…","worktreeId":"747d7569-4f9a-4c34-9374-fb362f860e23",
    "label":"Claude-1","suppressTerminalAutofocus":true}
   ```
   The strings `"spaceId"` and `"canvasId"` occur **zero times** across the entire
   local-storage tree, current `.log` and historical `.ldb` alike.

So a freshly rehydrated client holds `worktreeId` and nothing else. Two of the
three required fields are unavailable from every source it could consult.

## Post-reload observations

- **Selective pane survival.** The two MCP-launched runs (`1d604766`, `fed85590`)
  rehydrated and are operational. The three CMDK-launched runs (`Claude-1`,
  `Codex-1`, `Claude-2`) did not appear. All five were present in persisted
  `contentRefs` beforehand.
  `Claude-2` rules out agent metadata as the discriminator: it carried
  `agentId: "tm/orchestrator"` exactly like the survivors and still vanished. The
  discriminator is the launch path.
- **MCP launch still works post-reload; CMDK launch does not.** So the server can
  resolve a complete valid identity for a launch. That capability exists and is
  exercised on every MCP launch; it is simply not offered to the client.
- **The worktree is still badged `Current` post-reload.** Re-selecting it does
  nothing (no-op / early return), so the obvious user recovery has no effect.
- **Switching to the other worktree and back fully recovers.** Launches work
  again, and every pane returns with the layout restored. Persistence is sound
  end to end; the identity-verification path that a worktree *transition* runs is
  never run on rehydrate.

## What the scout must explain

1. Which symbol produces the launch triple on the CMDK path, and which one on the
   MCP path. Name both owners, and where they diverge.
2. Why rehydrate does not run the verification that a worktree transition runs.
   Name the guard or early return that makes re-selecting the current worktree a
   no-op, and whether it is the same shape as the `activateSpace`
   already-active early return in `CanvasCommandDispatcher`.
3. Why the three CMDK-launched panes did not rehydrate while the two MCP-launched
   ones did, given all five were persisted.
4. Whether `_resolve_launch_worktree` (removed from `get_meta` by #321,
   `df052e65`) is genuinely part of the answer, or a red herring now that we know
   the client recovers on its own once a transition fires.

## Hard constraints on any fix

- **No seeding.** Nothing may create a Space, workdir, canvas, or row as a side
  effect of resolving identity. No `resolve_cwd(create=True)`, no create-on-read.
  Standing veto.
- **One command surface.** CMDK "Create new Workdir" / launch and the MCP
  equivalents must reach the same seam, with both as thin adapters. Identical
  behaviour should be a property of the design, not maintained by hand on two
  paths.
- No plasters, no quick fixes. Identify the regression.

## Separate findings from the same session (NOT this slice)

Logged so they are not lost. Do not scope them into the rehydrate work.

- MCP mutations do not refresh CMDK's worktree inventory live: after
  `worktree_create`, CMDK showed MS1 `1 worktree` / MS2 `0 worktrees` while the
  server held MS1=2, MS2=1. Correct after reload, so it is live-refresh
  staleness. The new **Space** MS2 *did* propagate live; the worktrees did not.
- `worktree_list` is Space-wide but `worktree_get` refuses anything outside the
  caller's own worktree (`space_mismatch`). A client can enumerate IDs it cannot
  read. Same asymmetry for `canvas_list` / `canvas_get`.
- `launch` with `effort: xhigh` and no catalog model for the vendor fails
  `target_unavailable: no_default_target` instead of merging with the harness
  default. Hit twice (tm/codebase-mapper).
- No `canvas_delete` exists; test canvases are permanent residue.
- `canvas_update` with no fields bumps `updatedAt`.
- `space_crud_failed` collapses distinct user-correctable input errors into one
  generic message.
- Workspace slug generation takes a fixed-length path tail, so slugs can open
  with a meaningless UUID fragment.
- MCP-launched panes are titled by run-id prefix and show `0 tok` vitals.
- Electron renderer has no CSP, or one with `unsafe-eval`.

Full control-plane API sweep: cm entry `019f9828-2eb6-73d2-911d-8e2d74bcf92e`.
