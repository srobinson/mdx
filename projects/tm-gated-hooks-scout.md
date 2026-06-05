# Scout: needs_you{gated{permission}} via Claude Code hooks

**Type:** read-only reuse map / feasibility  
**Agent:** grok (`transport-matters:general:1:2.3`)  
**Date:** 2026-07-10  
**Repo branch at scout:** `realtime-slice5-empty-at-spawn` (local WIP unrelated; no writes)

**Product ask:** when launched Claude Code blocks on a client-side permission dialog ("This command requires approval / Do you want to proceed?"), surface **Needs You** instead of the current wire-driven **Tools**. Signal is **wire-impossible** (permission pause never hits the provider); target = Claude Code **hooks**.

---

## CRUX

**Yes.** Transport Matters already builds a **per-run writable Claude overlay** (`settings.json` is overlay-copied, not a symlink into the user's home) and already merges managed keys into that file. Inject `hooks` there at the same seam as proxy env. Thread `TRANSPORT_MATTERS_RUN_ID` (already on child env + settings env). Route the hook to the **loopback web/API plane** with a **new gate signal endpoint** (capture RPC today is only prepare/release/health — reuse its lease/origin posture or a sibling under `/v1`).

---

## 1. Launch path — inject without touching user config

### Spawn seam

| Symbol | Role |
|--------|------|
| `cli.claude` (`api/src/transport_matters/cli/__init__.py`) | `transport-matters claude` → `run_start` |
| `prepare_captured_run` (`captured_run.py`) | Shared prepare: lock, proxy, spawn spec + lease (CLI + capture RPC + canvas) |
| `build_claude_captured_invocation` (`captured_claude.py`) | Claude-specific argv/env factory |
| `CaptureLeaseRegistry.prepare_capture` (`capture_rpc.py`) | Canvas/runtime path → same `prepare_captured_run` |
| `build_launch_env` / `build_managed_child_env` (`launch_environment.py`) | Shared env; `TRANSPORT_MATTERS_RUN_ID`, harness, home, storage |

Flow: prepare → runtime home overlay → `apply_claude_proxy_env_settings` (when `runtime_home_dir` set) → `ManagedClient` with `CLAUDE_CONFIG_DIR` = overlay.

### Per-run home isolation (injection safe)

| Fact | Evidence |
|------|----------|
| Child home is **managed overlay**, not `~/.claude` | `CLAUDE_CONFIG_DIR` → `…/runtime-home/claude` via `build_managed_child_env` |
| `settings.json` is **copied** into overlay (never symlink) | `home_constants._CLAUDE_OVERLAY_COPIED_NAMES` includes `_CLAUDE_SETTINGS_FILENAME` |
| Existing merge-only settings writer | `apply_claude_proxy_env_settings` writes overlay `settings.json` `env` keys (`ANTHROPIC` route, `TRANSPORT_MATTERS_RUN_ID`, `AGENT_HOME_DIR`, `NO_PROXY`) — "Merge only: preserves unrelated settings… never touches the source home" |
| Skip-dangerous seed | `_ensure_claude_skip_dangerous_prompt` / `ClaudeSeeder.seed` also write overlay `settings.json` |
| Template overlays can include a `hooks/` directory | `_CLAUDE_TEMPLATE_CONTENT_NAMES` includes `"hooks"` (scripts), separate from settings hooks JSON |

### Cleanest injection point

**Extend the overlay `settings.json` merge at `apply_claude_proxy_env_settings` (or a sibling `apply_claude_gate_hooks` called from the same place in `build_claude_captured_invocation`).**

Reasons:
1. Already runs only when `runtime_home_dir is not None` (managed launch).
2. Already atomic JSON write, merge-only, source-home safe.
3. Same moment `run_id` and proxy URL are known.
4. CC loads hooks from `settings.json` under `CLAUDE_CONFIG_DIR` (user-settings scope for that process) without mutating the operator's real `~/.claude/settings.json`.

Optional script assets: write under `runtime_home_dir/hooks/tm-gate.sh` (overlay-local) and reference with absolute path, or use CC **`type: "http"`** hooks to avoid shell.

**Not recommended:** project `.claude/settings.json` (pollutes repo); user home hooks (global side effect); `--settings` unless product already owns that argv (passthrough can pass it; managed path should not require user cooperation).

**Caveat:** `bypass_permissions=True` (capture RPC / launch field) skips permission dialogs — gated will not fire by design.

---

## 2. Hook sink — how the capture plane receives the signal

### Existing capture RPC surface

`api/src/transport_matters/api/v1/capture_rpc_routes.py`:

| Route | Purpose |
|-------|---------|
| `POST /capture/prepare` | Start proxy + return spawn spec |
| `POST /capture/{run_id}/release` | Tear down lease |
| `GET /capture/{run_id}/health` | Liveness |

**No gate/signal route today.** Capture RPC is lease lifecycle for Runtime, not activity facts. Mutating routes use `require_http_origin` (loopback origin matching web port).

### Identity already available to the hook

| Channel | Key / value |
|---------|-------------|
| Process env (launch) | `TRANSPORT_MATTERS_RUN_ID` via `build_launch_env` → child base env (**not** stripped by `build_managed_child_env`) |
| Overlay settings `env` | same `RUN_ID` + `AGENT_HOME_DIR` written by `apply_claude_proxy_env_settings` |
| Hook stdin JSON | `session_id`, `cwd`, `tool_name` / tool input (event-specific), `permission_mode`, etc. (CC docs) |
| Not automatic | `CAPTURE_RPC_URL` is for the **gateway** child (`gateway_supervisor`), not the Claude client |

Also available unless stripped: `TRANSPORT_MATTERS_WEB_PORT` (not in managed-child strip sets) — hook can target loopback web.

### Lowest-friction sink options (ranked)

| Rank | Sink | Pros | Cons |
|------|------|------|------|
| **1** | **New HTTP route on existing FastAPI** e.g. `POST /v1/runs/{run_id}/gate` or `POST /capture/{run_id}/gate` + CC **`type: "http"`** hook | Matches CC HTTP hooks; origin gate reuses `require_http_origin`; no shell; body = hook JSON | New route + writer path |
| **2** | Command hook: `curl`/python one-liner → same route | Works if HTTP hooks blocked by policy | Shell, quoting, dependency on curl |
| **3** | Direct `SessionWriter.submit_run_live_status` via a tiny `transport-matters gate` CLI on PATH | Reuses writer | CLI packaging; needs DB/session loop access from hook process |
| **4** | File drop under run storage + tailer | No HTTP | New watcher; latency; not DRY with existing doorbell model |

**Recommendation:** **HTTP hook → new loopback gate endpoint → SessionWriter (or thin gate upsert) → `tm_events` NOTIFY → ActivityIngestion.** Do **not** overload prepare/release semantics; add a dedicated gate admission sibling.

Hook handler must **not** return `permissionDecision: allow/deny` unless product intends to auto-answer the dialog — default should exit 0 / empty decision so the **user** still approves in the TTY while TM only observes.

---

## 3. State plane — machine is not ready; UI vocabulary is reserved

### What already ships

| Layer | Status |
|-------|--------|
| `activityStatuses` includes `"needs-you-gated"` | `packages/contract/src/activity/wire.ts` — **RESERVED**, comment: no derivation source until gate slice |
| `activityStatusTier("needs-you-gated")` → `"needs_you"` | same file |
| `needsYouForStatus` | returns `{ kind: "asked" }` **only** for `needs-you-asked`; gated → **null** until gate slice adds `{ kind: "gated"; … }` |
| `runActivityMachine` | **no** `needs-you-gated` state node; comment: unreachable like pre-live starting path; `WIRE_RETRACTED_TRANSITIONS` has no gated restore |
| `wireStatusFromMachineState` | no case for gated (wire vocab without machine mapping) |
| Live wire kinds | `LIVE_STATUS_KINDS` = `reasoning` \| `running_tool` \| `generating` only (`live_status.py`) |

### Wire plane behavior today (why "Tools" sticks)

Permission pause is **after** the model already emitted tool_use on the wire. Live producer asserts `running_tool` → machine `running-tools` → UI Tools. Nothing client-side can change that without a non-wire signal.

### Plane recommendation

| Approach | Verdict |
|----------|---------|
| **Reuse `run_live_status` with new kind e.g. `permission` / `gated`** | Attractive (doorbell + admit-once + mid-turn path exist) but kinds are **wire-block vocabulary**; generation fence is **exchange-scoped**. Gate is client-side and can outlive/coexist with a live tool assert — admission must **prefer gated over live tool**, and clear must not wait on generation close. Feasible if kind is clearly non-wire and admission priority is explicit. |
| **Separate `run_gate_status` (or lifecycle-adjacent fact)** | Cleaner separation of wire overlay vs client gate; more migration/NOTIFY surface. |
| **Transcript / activity_event record kind** | Durable, but permission dialog is not transcript-native; latency and mapping awkward. |

**Cleanest reuse:** extend the **live admission plane** (store row + NOTIFY + `reconcileWireSnapshot` sibling or priority step) with a **client gate fact**, **not** the wire tee/classifier. Prefer either:

1. **New live kind** `permission` on `run_live_status` (seq-monotonic, admit-once, **priority above** `running_tool` / generating / reasoning), cleared to `kind=null` on resolution; **or**
2. Parallel single-row `run_permission_gate` with the same doorbell pattern.

Machine work (gate slice): add `needs-you-gated` state, transitions, retract restore target, `needsYouForStatus` → `{ kind: "gated", toolName?: … }`, projection/SSE already generic.

Priority rule (design-critical): while gated is open, **do not** let a still-standing live `running_tool` re-win on re-reconcile.

---

## 4. Which CC hooks — request vs resolution

From official Hooks reference (`https://code.claude.com/docs/en/hooks`):

### Assert gated (permission dialog appears)

| Event | Matcher / notes | Fit |
|-------|-----------------|-----|
| **`PermissionRequest`** | Fires **when a permission dialog appears**; matcher = **tool name**; can allow/deny/ask via JSON; exit 2 denies | **Primary assert** — exact semantic match |
| **`Notification`** | matcher `permission_prompt` (also idle_prompt, elicitation_*, agent_needs_input, …) | **Secondary / corroborating** — desktop-notify path; less tool structure |
| `PreToolUse` | Before tool execution; can decide allow/deny **before** normal permission flow | Fires for **every** tool, not only gated; bad sole assert (noise). Useful bracket only if paired with PermissionRequest |

### Clear gated (dialog resolved)

| Event | Meaning | Fit |
|-------|---------|-----|
| **`PostToolUse`** | Tool succeeded after approval | **Primary clear** (approved path) |
| **`PostToolUseFailure`** | Tool failed after running | Clear (gate is over) |
| **`PermissionDenied`** | Auto-mode classifier denial | Clear / stay non-gated |
| **`Notification`** matchers `elicitation_complete` / `elicitation_response` | Elicitation lifecycle | Secondary; not identical to Bash permission |
| User dismiss / deny in dialog | May not emit PostToolUse | Need PermissionRequest decision path or timeout / next UserPromptSubmit safety clear |

**Recommended pair:**

1. **Assert:** `PermissionRequest` (all tools matcher `*` or omit) — observe only (no decision JSON).
2. **Clear:** `PostToolUse` + `PostToolUseFailure` + `PermissionDenied` (and optionally `UserPromptSubmit` as sticky-clear safety).

`Notification` / `permission_prompt` alone is weaker (no tool id guarantee) but useful as belt-and-suspenders for "needs attention" UX.

PreToolUse does **not** replace PermissionRequest for "dialog is up".

---

## 5. Config feasibility (CC behavior)

| Question | Answer |
|----------|--------|
| Does launched CC honor injected hooks non-interactively? | Hooks are declarative in settings JSON under the active config dir (`CLAUDE_CONFIG_DIR` = overlay). No `/hooks` UI required. Command/HTTP hooks run with session env; stdin/body = JSON event. |
| Settings locations | User `~/.claude/settings.json`, project `.claude/settings.json`, local, managed, plugins — **overlay path = user settings for that process** when `CLAUDE_CONFIG_DIR` points at runtime-home. |
| Tool / permission context on hook? | Yes: tool events include `tool_name`, `tool_input`, `session_id`, `cwd`, `permission_mode`, etc. PermissionRequest is a first-class event with tool matcher. |
| HTTP hooks? | `type: "http"`, POST body = same JSON; decision via 2xx JSON body. Ideal for TM loopback. |
| Side effects | Hook must not auto-allow unless product wants it; silent exit keeps TTY permission UX. |
| `disableAllHooks` / enterprise `allowManagedHooksOnly` | Can block user/project hooks — risk if user disables hooks globally **in the overlay copy**. TM can force-set hooks after copy and avoid enabling disableAllHooks. Managed policy hooks are out of scope. |
| Bypass permissions launches | No dialog → no signal (correct). |

---

## Reuse map (file + symbol)

| Concern | Reuse |
|---------|--------|
| Launch + overlay | `prepare_captured_run`, `build_claude_captured_invocation`, `prepare_runtime_home_overlay`, `apply_claude_proxy_env_settings`, `ClaudeSeeder` / `_ensure_claude_skip_dangerous_prompt` |
| run_id env | `env_keys.RUN_ID`, `build_launch_env`, settings env merge |
| Lease / canvas prepare | `CaptureLeaseRegistry`, `capture_rpc_routes` prepare/release/health |
| Origin gate for POST | `require_http_origin` |
| Live store + doorbell | `SessionWriter.submit_run_live_status`, `RUN_LIVE_STATUS_PAYLOAD_TYPE`, Activity `readLiveStatusForRun` / `reconcileWireSnapshot` |
| Status vocabulary | `activityStatuses`, `activityStatusTier`, `needsYouForStatus` (extend) |
| Machine | `runActivityMachine` + folds (new state); wire retract table |
| UI | existing Needs You tier / vitals path once status + `needs_you` payload exist |

---

## Non-goals / risks

- **Codex:** different permission model; scout is Claude Code hooks. Codex may need a later harness-specific signal.
- **Native home launches** (`runtime_home_dir is None`): no safe settings merge today without touching user home — gated feature should require managed overlay (already the canvas/TM claude path).
- **Sticky Tools if clear missed:** admit-once + explicit clear hooks; optional silence/UserPromptSubmit clear.
- **Priority vs live tool:** design must document gated beats `running_tool` while open.
- **Subagents:** PermissionRequest may fire for subagent tools; decide parent vs child run_id (hooks see session; TM run_id is process-level — usually one run per process).

---

## Suggested build slices (design input only)

1. **Inject:** merge TM hooks into overlay `settings.json` at `apply_claude_proxy_env_settings` seam; ship HTTP or command hook pointing at loopback.
2. **Sink:** `POST …/gate` (assert/clear) → store + NOTIFY; origin-gated; body carries tool metadata.
3. **Product plane:** machine `needs-you-gated` + `needsYouForStatus` gated variant + admission priority over live tool.
4. **Tests:** dialog fixture / hook stdin fixtures; assert→clear; bypass_permissions no-op; overlay does not mutate source home.

---

## Verdict

| Question | Answer |
|----------|--------|
| Can we inject a Notification/PermissionRequest hook into launched CC without disturbing user config? | **Yes** — overlay-copied `settings.json` + existing merge writer |
| Can we route it to the capture plane per-run? | **Yes** — `TRANSPORT_MATTERS_RUN_ID` already threaded; need **new** HTTP sink (capture RPC lacks gate today) |
| Is the machine ready? | **No** — status reserved; state unreachable until gate slice |
| Best assert/clear events | **PermissionRequest** assert; **PostToolUse** / failure / **PermissionDenied** clear |
