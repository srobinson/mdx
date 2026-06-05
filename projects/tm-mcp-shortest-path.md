# MCP shortest path (manual Space/Worktree/Canvas tool exercise)

Date: 2026-07-25  
Repo: transport-matters worktree `.claude/worktrees/multi-launch`  
Branch notes: investigation against tree at `ml/s3-cmdk` @ `0c76d520` (logic matches feat/multi-launch capture/MCP core at `97a80f56`).  
Mode: **read-only** (only this report file written).

---

## Q1. Bearer origin

| Fact | Evidence |
|------|----------|
| **Mint** | `controlplane/tokens.mint_run_bearer` → `secrets.token_urlsafe(32)` |
| **When** | `controlplane/provisioning.prepare_control_plane_grant` only if `ControlPlaneGrantOption.role()` is non-`None` (observer/director) |
| **Called from** | `captured_run_context._prepare_home_and_grant` during capture prepare (`write=True`) |
| **Persisted** | Digest only: `digest_run_bearer` (SHA-256) via `ControlPlaneGrantStore.persist` → table `control_plane_grant` (`CONTROL_PLANE_GRANT_TABLE`) |
| **Bound to** | **Per captured run**: columns `run_id`, `role`, `workspace_id`, `token_digest` |
| **Lifetime lifetime** | Run-scoped. Plaintext bearer is written once into that run’s overlay home (e.g. Claude `.mcp.json` headers) via `cli/claude_home.apply_claude_control_plane_client`. On lease teardown, `captured_run._persist_control_plane_grant` stacks `persistence.revoke(run_id)` |
| **Resolver** | `main` lifespan: `app.state.control_plane_grant_resolver = ActiveControlPlaneGrantResolver(grant_store, capture_registry.resolve_control_plane_grant)` |
| **Resolve path** | `ActiveControlPlaneGrantResolver.resolve` → `ControlPlaneGrantStore.resolve` (SELECT by `token_digest`) → `CaptureLeaseRegistry.resolve_control_plane_grant` |
| **Live-capture gate** | `capture_rpc.CaptureLeaseRegistry.resolve_control_plane_grant`: requires **in-process** lease + facts for `run_id`, matching `workspace_id`, and `lease.alive()`; else **None** (401 path) |
| **Principal** | `ControlPlanePrincipal(run_id, role, workspace_id, owner, …, space_id, worktree_id)` from live capture facts — not a long-lived owner session token |

**Implication:** A row in `control_plane_grant` alone is not enough; the capture must still be **alive in the same API process** that serves `/mcp`.

---

## Q2. Grant mutation outside the UI

Searches: `control_plane_grant`, `controlPlaneGrant`, `ControlPlaneGrantOption`, `prepare_control_plane_grant`, `mint_run_bearer`, typer options with `grant`, `env_keys` / `CONTROL_PLANE`, routes matching `/grant`.

| Surface | Found? | Detail |
|---------|--------|--------|
| **HTTP** | **Yes** | (1) `POST /v1/runs` body `controlPlaneGrant` (`packages/runtime/.../runtimeRouter.ts` → `RunManager.createNew` → capture prepare). (2) `POST /v1/capture/prepare` body `controlPlaneGrant` (`api/v1/capture_rpc_routes.PrepareCaptureRequest`). Grant is set **at prepare time**, not patched later. |
| **Control-plane service launch** | **Yes** | `controlplane/launch_service` threads `grant: ControlPlaneGrantOption` into the gateway create payload (`controlPlaneGrant`). Still creates a capture with grant; not a free-floating token API. |
| **CLI flag / subcommand** | **none found** | `cli/start_cmd.run_start` builds `CapturedRunRequest(...)` **without** `control_plane_grant` → model default `ControlPlaneGrantOption.NONE` (`captured_run_models`). No typer Option for grant on `claude`/`codex`. |
| **Env var** | **none found** | No grant key in `env_keys` / settings for default grant. |
| **Direct DB write** | **technically possible, not a product path** | `ControlPlaneGrantStore.persist` / table `control_plane_grant`. Without a matching **live** `CaptureLeaseRegistry` entry, `resolve_control_plane_grant` returns `None`. No admin HTTP to insert grants. |
| **Frontend** | Known | `capturedRunStore.cycleControlPlaneGrant` only affects **subsequent** `POST /v1/runs` options; does not re-grant an existing run. |

**No** “set this existing run to director” endpoint. Grant is immutable for a run’s life after prepare.

---

## Q3. CLI path (`transport-matters claude`)

| Step | Behavior | Evidence |
|------|----------|----------|
| Space bootstrap | **Yes** — `bootstrap_cli_space_or_exit` → create_space + create_workdir when empty | `cli/start_cmd.run_start` |
| Affinity on request | space_id / worktree_id / canvas_id + launch_fields affinity | same |
| Default grant | **`none`** | `CapturedRunRequest.control_plane_grant` default; start_cmd does not override |
| MCP seed | **No** when grant is none — `prepare_control_plane_grant` returns `None` if `role()` is None | `provisioning.prepare_control_plane_grant` |
| Grant persistence on local TTY path | Local `run_captured_run` path typically has `control_plane_grants=None` | `captured_run` helpers; non-none grant without store raises `control plane grant persistence is unavailable` (`_persist_control_plane_grant`) |

**Verdict:** CLI launch **bootstraps inventory** and runs a real agent, but **does not** mint a bearer or attach MCP **today**. Raising grant without desktop **cannot** be done via CLI flag; would require API capture path (canvas/gateway/`POST /v1/capture/prepare`) with `controlPlaneGrant` set and a live registry-backed capture.

---

## Q4. No-agent path (external MCP client / curl)

| Question | Answer |
|----------|--------|
| Drive `/mcp` with only a bearer, no agent process? | **Only if a live capture lease exists** for that bearer in the **same** API process. External MCP Inspector / client is fine as the **MCP peer**; the **grant still requires an alive capture** (`CaptureLeaseRegistry.resolve_control_plane_grant`). |
| Bearer with no capture at all? | **No** — store hit may succeed, then `resolve_active` returns `None` → unauthorized. |
| Origin / host gating on `/mcp` | Mounted in `main` at `/mcp` behind `ControlPlaneMcpAuthApp` + exact-path wrapper. Auth is **Bearer**, not `require_http_origin` (that’s for Space REST mutations). `TrustedHostMiddleware` allows `localhost` / `127.0.0.1` / `::1` by default (`config.trusted_hosts`). CORS is present for browser clients. Loopback hostnames work. |
| Simple `curl` JSON-RPC? | FastMCP **streamable HTTP** session protocol — use an MCP client (Inspector, SDK), not a one-shot REST POST, unless you implement the MCP session handshake. |

---

## Q5. Shortest sequence TODAY + desktop nav prerequisite

### Verdict

**Desktop navigation fix is NOT a hard prerequisite for testing Space MCP tools.**  
It is only required for the **in-desktop** “cycle grant → Agents spawn → agent uses tools” UX.  
The hard prerequisites are: **running backend with session store + grant store**, a **live capture with `controlPlaneGrant` ≠ none**, and a **valid bearer** while that capture is alive.

### Shortest concrete path (no desktop nav)

Assumes desktop backend (or equivalent API+gateway) already up with session store, as in normal `transport-matters` desktop use. Ports are examples; use the live web/gateway ports from the desktop record / logs.

1. **Inventory via trusted REST** (Origin required on mutations):
   ```bash
   # Origin/host must match trusted local front (e.g. http://127.0.0.1:WEB_PORT)
   curl -sS -X POST "http://127.0.0.1:WEB/v1/spaces" \
     -H "Origin: http://127.0.0.1:WEB" -H "Host: 127.0.0.1:WEB" \
     -H "Content-Type: application/json" \
     -d '{"name":"mcp-test"}'
   # note spaceId from JSON
   curl -sS -X POST "http://127.0.0.1:WEB/v1/spaces/SPACE_ID/worktrees" \
     -H "Origin: http://127.0.0.1:WEB" -H "Host: 127.0.0.1:WEB" \
     -H "Content-Type: application/json" \
     -d '{"path":"/absolute/path/to/existing/dir"}'
   # note worktreeId + rootCanvasId
   ```
   Evidence: `space_routes.create_space` / `create_workdir` + `require_http_origin`; create path calls `ensure_worktree_root`.

2. **Spawn a grant-bearing capture** (gateway `POST /v1/runs`, not desktop CMDK):
   ```bash
   curl -sS -X POST "http://127.0.0.1:GATEWAY/v1/runs" \
     -H "Content-Type: application/json" \
     -d '{
       "harness":"claude",
       "workspaceId":"slug/hash-or-whatever-runtime-expects",
       "spaceId":"SPACE_ID",
       "worktreeId":"WORKTREE_ID",
       "canvasId":"ROOT_CANVAS_ID",
       "controlPlaneGrant":"director",
       "idempotencyKey":"mcp-manual-1"
     }'
   ```
   Evidence: `runtimeRouter` POST `/runs` passes `controlPlaneGrant`; capture prepare requires canvas affinity for `launchKind: canvas` (`capture_rpc_routes._resolved_domain_request`); non-none grant sets `control_plane_url` to `{web}/mcp` and mints bearer.

3. **Recover the plaintext bearer** from the run’s runtime home (Claude):
   ```bash
   # under the run storage dir created for that runId:
   jq -r '.mcpServers[].headers.Authorization' .../runtime-home/.../.mcp.json
   # expect: Bearer <token>
   ```
   Evidence: `apply_claude_control_plane_client` writes `headers.Authorization`.

4. **Call MCP tools** with an MCP client pointed at:
   - URL: `http://127.0.0.1:WEB/mcp`
   - Header: `Authorization: Bearer <token>`
   - Keep the run **alive** (do not terminate) while testing.
   - Exercise e.g. `space_list`, `space_create`, `worktree_create`, `worktree_list`, canvas tools (`space_mcp.register_space_mcp_tools`).

5. **Optional in-agent check** after that: if the same run’s client is Claude, it already has the MCP server seeded and can invoke tools without Inspector — still requires grant ≠ none at prepare.

### Alternate shorter-if-desktop-already-rooted

If inventory is already rooted and user only fixes grant:

1. Settings cycle control plane grant to **director** (`cycleControlPlaneGrant`).  
2. Agents → spawn (needs `defaultWorktreeId`).  
3. Use agent MCP tools.  

That path is **blocked today** by the rooted-worktree seed regression (see `tm-launch-mcp-investigate.md`); it is **not** the only MCP path.

### Desktop nav vs MCP

| Need | Desktop select-worktree / nav fix |
|------|-----------------------------------|
| Manual MCP tool exercise + real DB mutations | **No** — REST inventory + `POST /v1/runs` with director + MCP client |
| In-desktop agent spontaneously has MCP | **Yes** (plus grant ≠ none) — UX only |

---

## Quick reference

| Item | Symbol |
|------|--------|
| Mint | `controlplane.tokens.mint_run_bearer` |
| Prepare grant | `controlplane.provisioning.prepare_control_plane_grant` |
| Store table | `control_plane_grant` / `ControlPlaneGrantStore` |
| Resolver | `ActiveControlPlaneGrantResolver` + `CaptureLeaseRegistry.resolve_control_plane_grant` |
| MCP mount | `main.create_control_plane_mcp` → `/mcp` |
| Space tools | `space_mcp.register_space_mcp_tools` |
| Canvas affinity required | `capture_rpc_routes._resolved_domain_request` (`canvas_affinity_required`) |
| CLI default grant | `CapturedRunRequest.control_plane_grant = NONE` |

---

## Bus one-liner target

`done: ~/.mdx/projects/tm-mcp-shortest-path.md — desktop nav not required; need live capture+director grant+bearer`
