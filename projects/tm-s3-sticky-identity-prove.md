# S3 sticky identity prove — cold start walkthrough

- Worktree: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch`
- Branch/HEAD: `ml/s3-cmdk` @ `699fb5786091ae5da1c86c688baa7ec714662084`
- Reset method: stopped `transport-matters-desktop-dev` (tmux window kill + free ports 18787/18788/18789/15173), then `./scripts/reset-channel-store.sh --channel stable --yes` (drop/recreate `transport_matters` on `localhost:55432`, alembic head `0032_space_worktree_ownership`, tier-1 sweep). Verified `space=0 worktree=0`.
- App: `local-desktop-dev-mode.sh` (needed `CLAUDE_CODE_OAUTH_TOKEN` set so empty `backend_env_args[@]` does not trip `set -u` at line 144). Backend 18788, gateway 18789, vite 15173, Electron attached.
- Drive surface: `agent-browser` session `tm-s3-prove` against renderer `http://127.0.0.1:15173/canvas` (same URL Electron loads).

## Evidence

### (a) Empty DB offered Create new space
CMDK → Workdir with empty inventory:
- options: `Create new space`, `Create new Workdir`
- `GET /v1/spaces` → `{"items":[],"nextCursor":null,"showSwitcher":false}`
- screenshot: `/tmp/tm-s3-workdir-empty.png`

### (b) After create space, palette stays open with new item
Created name `ProveSpace` via combobox "Space name" + Enter.
Post-submit list still open:
- `Create new space`, `Create new Workdir`, `ProveSpace 0 worktrees Current`, Rename/Delete rows
- API: `spaceId=11139564-dbd1-4a19-8fa6-7919d09f9f97` label ProveSpace
- screenshot: `/tmp/tm-s3-after-space.png`

### (c) Create new Workdir targets Current space
ProveSpace was badged `Current`. Submitted path:
`/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch`
Result worktree attached under that same `spaceId`:
- `worktreeId=d9b06f68-15c0-4ea8-9f60-0a1766139a6a`
- `rootCanvasId=8751de28-402b-4ecc-a49f-5a4c3eb23e17`
- branch `ml/s3-cmdk`, path multi-launch
- palette: `ProveSpace 1 worktree Current`

### (d) POST /v1/runs body (fetch wrap on renderer)
```json
{"harness":"claude","spaceId":"11139564-dbd1-4a19-8fa6-7919d09f9f97","worktreeId":"d9b06f68-15c0-4ea8-9f60-0a1766139a6a","canvasId":"8751de28-402b-4ecc-a49f-5a4c3eb23e17","name":"Claude-1","bypassPermissions":false,"controlPlaneGrant":"none","idempotencyKey":"b65f90e9-9e46-4fff-92bc-eef3eae8f800"}
```
All three IDs populated. `worktreeId` matches the selected worktree row `ml/s3-cmdk` under ProveSpace.

### (e) Pane appeared and agent ran
- UI pane `Claude-1` with terminal input; Claude MCP server approval prompt rendered (ark-ui MCP discovered).
- `GET /v1/runs` → one RUNNING run `61142457-ceb2-4390-8c4a-58659049f1e6` with same spaceId/worktreeId, harness claude, name claude-1.
- No `canvas_affinity_required` rejection.
- screenshot: `/tmp/tm-s3-after-spawn.png`

## Verdict for prove
pass — cold start create space → create workdir on Current → select worktree → spawn Claude with sticky spaceId/worktreeId/canvasId; pane live.

## Gate

### just check
```
uv run ruff format src/
697 files left unchanged
uv run ruff check src/ --fix
All checks passed!
uv run mypy src/
Success: no issues found in 697 source files
EXIT:0
```

### just test
```
============================ 3416 passed in 41.35s =============================
EXIT:0
```

Tree remained clean at 699fb578 after both jobs.

---

# Re-prove at 9c9b06f8 (review fix round)

Reset: `./scripts/reset-channel-store.sh --channel stable --yes` then `local-desktop-dev-mode.sh` (renderer http://127.0.0.1:15173/canvas). Drive: agent-browser session `tm-s3-reprove2`.

## (a) Enter on Current Space preserves canvas/URL/store

Built canvas: ProveSpace + worktree multi-launch + spawned Claude-1.

**Before Enter on Current ProveSpace:**
- href: `.../canvas?space_id=f48af777-...&worktree_id=5c75b69d-...&canvas_id=25f1cf21-...`
- bodyHasClaude: true; localStorage canvas cache len 830

**After Enter on row `ProveSpace 1 worktree Current`:**
- href unchanged with all three params intact
- bodyHasClaude: true; Minimize/Close Claude-1 + Terminal input still present
- cache len still 830
- screenshot: `/tmp/tm-s3-reprove-a-after-current-enter.png`

## (b) Zero-worktree ArrowRight scoped Create Workdir

Created `EmptyZero` (0 worktrees, spaceId `0f902cdd-8a94-437f-9790-43b45626e482`). ArrowRight → WORKTREE scope showed **only** actionable `Create new Workdir` (not "No matches").
Submitted path `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` from that scoped row.
API after: EmptyZero worktrees = that path (`worktreeId e1c1fe5f...`); ProveSpace still holds multi-launch only.
screenshot: `/tmp/tm-s3-reprove-b-zero-wt-scope.png`

## (c) Top-level Create new Workdir targets Current

Cold-start: ProveSpace badged Current → top-level Create new Workdir with multi-launch path → worktree landed on ProveSpace `f48af777...` (not elsewhere).

## (d) Cold-start + POST /v1/runs reconfirm

Empty DB offered Create new space. After ProveSpace + worktree select + Agents→Claude Native:

```json
{"harness":"claude","spaceId":"f48af777-b36a-4a06-b3b1-f7128cb25e75","worktreeId":"5c75b69d-a3a0-4a5d-8e22-98fa5f01251a","canvasId":"25f1cf21-09b6-401c-b5af-7466769931b1","name":"Claude-1","bypassPermissions":false,"controlPlaneGrant":"none","idempotencyKey":"efec7847-037b-44ef-a376-6dfcd3091dea"}
```

Run RUNNING `26bc841b-...` with matching spaceId/worktreeId. No canvas_affinity_required.


## Gate at 9c9b06f8

### just check
```
uv run ruff check src/ --fix
All checks passed!
uv run mypy src/
Success: no issues found in 697 source files
EXIT:0
```

### just test
```
============================ 3416 passed in 36.70s =============================
EXIT:0
```

Tree pristine at 9c9b06f8 after re-prove.
