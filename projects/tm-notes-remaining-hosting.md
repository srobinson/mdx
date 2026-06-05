---
title: TM NOTES Work-Remaining Audit — VPS / Remote Hosting slice
type: research
tags: [transport-matters, vps, remote-hosting, plan-b, run-manager, auth, durability, work-remaining]
summary: Verified NOTES/captured-canvas/09-vps-hosting.md against committed code; subscription-auth seam is DONE in-repo, all other VPS capabilities are REMAINING and mostly later/maybe.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# VPS / Remote Hosting — Work Remaining

**Slice owner:** `transport-matters:helioy-tools:codebase-analyst:1:3.6`
**Note audited:** `NOTES/captured-canvas/09-vps-hosting.md` (Draft v0.1, 2026-06-09; mechanism-gap addendum 2026-06-13)
**Method:** Every claim verified against committed code (`git log`, fmm symbol reads, grep). NOTES/ is gitignored scratch, so the note's own status lines were treated as claims, not evidence. cwd = repo root.

> The note is explicitly **future direction, not yet scheduled**. With one exception (the subscription-auth seam, which already shipped for the local desktop case), every capability it proposes is **REMAINING**. Most are gated on actually deciding to host remotely ("later/maybe"); one is a cheap near-term down-payment.

## Status at a glance

| # | Capability | Status | Horizon | Confidence |
|---|-----------|--------|---------|-----------|
| 1 | Subscription auth seam on a managed home (`AGENT_HOME_DIR` + home-seed) | **DONE** (in-repo seam) | shipped | high |
| 1b | VPS-specific auth transfer (sftp auth files into a Docker home) | **WONT_DO** in-repo (operational recipe) | n/a | high |
| 2 | Network exposure + real auth on `/api/runs` | **REMAINING** (seam clean) | later/maybe | high |
| 3 | Server-restart durability (reparent/rediscover runs) | **REMAINING** | later/maybe | high |
| 4 | Detached PTY holder surviving server death | **REMAINING** | later/maybe | high |
| 5 | Workspace provisioning (clone/mount repo) | **PARTIAL** (CLI detect done) | later/maybe | high |
| 6 | Multi-tenancy / isolation | **REMAINING** | later/maybe (only if >1 operator) | high |
| 7 | Persist `ScrollbackRing` to disk (durability down-payment) | **REMAINING** | near-term candidate | high |

---

## 1. Subscription auth on a remote host — DONE (seam in-repo); VPS transfer is out-of-repo

The note marks this "SOLVED (tested + verified)" and identifies the `TRANSPORT_MATTERS_AGENT_HOME_DIR` launch seam as the carrier. **The seam exists and is wired end to end in committed code.**

- The managed-home setting exists: `Settings.agent_home_dir` — `config.py:102` (`agent_home_dir: Path | None`).
- The env key exists: `env_keys.AGENT_HOME_DIR = f"{ENV_PREFIX}AGENT_HOME_DIR"` — `env_keys.py:43`.
- It is threaded into the launch env: `launch_environment.py:139` (`env[env_keys.AGENT_HOME_DIR] = str(home_dir)`), into the addon runtime `addon_runtime.py:82`, and into captured-run spawns `api/v1/run_routes.py:241` (`home_dir=settings.agent_home_dir`).
- The auth-file seeder is real: `cli/home_seed.py` copies the exact fields the note names — Claude `.claude.json` `userID` + `oauthAccount` (`home_seed.py:119-122`, `_CLAUDE_CONFIG_FILENAME = ".claude.json"` at `:31`) and Codex `auth.json` (`_CODEX_AUTH_FILENAME = "auth.json"` at `:34`). Public entry `seed_home_dir` — `home_seed.py:162`.

**What remains (1b, out-of-repo):** the VPS step itself — sftp the operator's auth files onto a remote Docker home before the seeder runs — is an operational/deployment recipe, not a code deliverable. There is no Docker/VPS/provisioning subsystem in the repo (`absent: grep -rn "Dockerfile|docker run|sftp" api/src --include=*.py -> 0 functional hits`). Classify as WONT_DO for repo work; it rides on the shipped seam.

---

## 2. Network exposure + real auth on `/api/runs` — REMAINING (the seam is already clean)

The note: Plan-B is loopback-only by design; VPS needs a public bind behind real auth (tokens/sessions/TLS), and the `/api/runs` seam must stay swappable. **Verified: today is loopback-only with origin gates and no real auth; the gate is already isolated as a swappable dependency, so the note's "keep the seam clean" guidance is currently satisfied.**

Current state (all present, loopback-only):
- API server binds loopback: `uvicorn.run(host="127.0.0.1", ...)` — `__main__.py:11`.
- Proxy binds loopback: `--listen-host 127.0.0.1` — `cli/launch_runtime.py:336`.
- DNS-rebinding defense, loopback hosts only: `app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)` — `main.py:196`; `trusted_hosts = ["localhost","127.0.0.1","::1"]` — `config.py:126`.
- Origin gate is a swappable FastAPI dependency: `require_http_origin` — `run_routes.py:169`, applied via `Depends(require_http_origin)` on `POST /runs` (`:288`) and `DELETE /runs/{id}` (`:342`); WS uses `terminal_bridge.origin_allowed(...)` (`run_routes.py:362`).
- **No real auth exists:** `absent: grep -rni "bearer|api_key|api_token|tenant" api/src --include=*.py (non-test) -> 0 functional hits` (only `transport_redaction.py` redacting upstream provider headers and `cors_headers` listing the `Authorization` header name).

Remaining work (later/maybe; needed only when hosting remotely):
- Add an auth layer (token/session/TLS) as an additional `Depends`/middleware alongside `require_http_origin`. The injection point is clean today — do not entangle origin/loopback logic into the route bodies. Anchor: `run_routes.py:169` (`require_http_origin`), `main.py:196` (middleware stack).
- Add an opt-in public bind path (the `host=` is hardcoded `127.0.0.1` at `__main__.py:11`; would need to become configurable, gated behind the auth layer).
- Extend `trusted_hosts` for the public hostname (config seam already documented at `config.py:120-126`).

---

## 3. Server-restart durability — reparent/rediscover runs — REMAINING

The note: a long-lived VPS wants runs to survive redeploy/restart via the run-dir manifest. **Verified: runs are purely process-resident; nothing rediscovers them on boot.**

- Runs live in an in-memory dict on the manager: `RunManager.spawn` registers `self._runs[run.run_id] = run` and starts an in-process drain task `asyncio.create_task(self._drain_run(run))` — `run_manager.py:237-305`. No serialization of run state.
- No startup rediscovery/reparent: `absent: grep -n "rediscover|reparent|reattach|from_manifest|load_runs|scan_runs" run_manager.py main.py -> 0 hits` (the only `recover` hits in `main.py:92-94` concern the Postgres session store, not runs).
- The run-dir manifest exists as a per-run discovery index only (`manifest.py`, `launch_manifest.py`, written via `cli/runner.py` / `captured_run.py`), but `RunManager` never reads it to rebuild `_runs`. Confirms the note's "manifest = discovery index, not recovery."

Remaining work (later/maybe):
- On API startup, scan the run-dir manifests and rebuild `RunManager._runs` for runs whose host process is still alive — depends on capability #4 (a surviving PTY holder) to be attachable, not merely discoverable. Anchor: `run_manager.py:212` (`RunManager.__init__`), `manifest.py`.

---

## 4. Detached PTY holder surviving server death — REMAINING (the deeper blocker)

The note (2026-06-13 addendum): the shipped run is a direct in-process subprocess of the API server, so the PTY master fd dies with the server; reparent/rediscover also needs a detached run-host (`setsid`/`dtach`-style) owning the PTY + child + proxy out of process. **Verified exactly.**

- The PTY master fd is created and held in the server process: `spawn_pty_process` does `master_fd, slave_fd = pty.openpty()` then `subprocess.Popen(...)` and returns `TerminalPty(master_fd=master_fd, ...)` — `pty_session.py:65-96`. `RunManager.spawn` pulls it in via `asyncio.to_thread(self._spawn_pty, ...)` — `run_manager.py:251`.
- The `os.setsid()` at `pty_session.py:101` is the **child's** `preexec_fn` (job-control session leader via `prepare_terminal_child`), **not** a detached holder process. The master fd remains in the server.
- No detached run-host / daemon: `absent: grep -n "dtach|daemoniz|double.fork|os.fork" api/src --include=*.py (non-test) -> only the child-side os.setsid at pty_session.py:101`.

Remaining work (later/maybe; prerequisite for #3 to be useful):
- Introduce a detached run-host process that owns the PTY master, the agent child, and the proxy, surviving API restart, with a re-attach handshake the new server uses. Anchor: `pty_session.py:65` (`spawn_pty_process`), `run_manager.py:237` (`RunManager.spawn`).

---

## 5. Workspace provisioning — PARTIAL (CLI detection done; clone/mount absent)

The note: the VPS needs the repo present (clone/mount) + the CLIs installed; the capabilities provider already detects claude/codex. **Verified: detection is done; provisioning is not — the cwd must already exist.**

- CLI detection DONE: `capabilities.py` — `detect_cli` (`:142`), `detect_clis` (`:157`), `resolve_cli_binary` via `shutil.which` (`:80`). Confirms the note's "capabilities provider already detects claude/codex."
- No repo provisioning: the run cwd must already exist — `_validated_existing_dir` rejects a non-existent dir (`run_routes.py:196-212`, checks `working_dir.exists()` / `is_dir()`); `RunManager` clones/mounts nothing. `absent: grep -n "git clone|mount|checkout|provision" run_manager.py run_routes.py workspace.py -> 0 provisioning hits`.

Remaining work (later/maybe):
- Add a workspace-provisioning step (clone/mount the target repo into the run cwd, ensure the CLI binary is installed) before spawn. Anchor: `run_routes.py:196` (`_validated_existing_dir`), `capabilities.py:157` (`detect_clis`).

---

## 6. Multi-tenancy / isolation — REMAINING (single-operator today; gated on >1 operator)

The note: run ownership + isolation, only if >1 operator; Docker-per-run/per-tenant is the natural unit. **Verified: no ownership/tenant model exists.**

- Runs are a flat in-memory dict keyed only by `run_id` — `RunManager._runs` (`run_manager.py:212-305`); no per-operator scoping on any route (`list_runs`, `get_run`, `stop_run` take no principal — `run_routes.py:298,323,338`).
- `absent: grep -rni "tenant|owner_id|principal|account_id" run_manager.py run_routes.py -> 0 hits`.

Remaining work (later/maybe — explicitly only if >1 operator):
- Introduce run ownership + isolation (Docker-per-run or per-tenant). Anchor: `run_manager.py:212` (`RunManager`), `run_routes.py:298` (`list_runs`). Lowest priority; gated on a second operator existing.

---

## 7. Persist `ScrollbackRing` to disk — REMAINING (cheapest near-term down-payment)

The note (DRIFT, 2026-06-13): `ScrollbackRing` is in-memory-only; persisting it into the run dir is the cheap durability down-payment (survives restart for replay even before PTY survival is solved). **Verified.**

- `ScrollbackRing` is a pure in-memory `deque` with no disk path: `run_terminal.py:51-112` (`self._chunks: deque[PtyChunk]`, `snapshot()` returns a tuple, no file I/O).
- `absent: grep -rn "scrollback" api/src --include=*.py (non-test) | grep -i "write|disk|persist|json|dump|open(" -> 0 hits`.

Remaining work (near-term candidate — smallest, decoupled from #3/#4):
- Persist the ring (or a periodic snapshot) into the per-run dir and replay it on attach after restart. Anchor: `run_terminal.py:51` (`ScrollbackRing`), `run_routes.py:392` (`run_terminal_ready_frame`, where scrollback is replayed today).

---

## Net assessment

The note is an accurate map of the VPS gap. One item already shipped (the `AGENT_HOME_DIR` + home-seed subscription-auth seam, capability #1). Everything else is unbuilt and correctly characterized:

- **Near-term, cheap, standalone:** #7 (persist scrollback) — the only item not gated on a remote-hosting decision.
- **Later/maybe, ordered by dependency:** #4 (detached PTY holder) is the load-bearing blocker; #3 (rediscover) depends on it; #2 (auth + public bind) is independent and has a clean injection seam already; #5 (provisioning) is independent; #6 (multi-tenancy) is lowest priority and gated on a second operator.

The two "keep the seam clean" guidances the note gives are both currently satisfied in committed code: the origin/loopback gate is a swappable `Depends` (#2), and the manifest is a standalone recovery substrate not entangled with in-memory assumptions (#3).
