---
title: 'Arena verdict (claude judge): in-app harness login driver'
type: review
tags: [transport-matters, login-driver, arena, verdict]
summary: Base D (opus). Graft harness-keyed identity from A/C, raw tail instead of a URL regex from A/C, the app-scoped completion watcher from B, the env patch shape from B, and the grok verification flag from B/C. Reject B's gateway-to-Python RPC inversion and C's full-environment spawn body.
status: active
created: 2026-08-27
---

Baseline `main` at `83f3decf`. Every symbol below was checked with `git grep main`.

## Scorecard

| Axis | A claude | B codex | C grok | D opus |
| --- | --- | --- | --- | --- |
| 1 Constraints | Pass, but director has no stdin path (WS only, no input route) | Pass; stdin for director is WS binary frames only | Pass; stdin route, harness id only | Pass; stdin route, MCP tools, long poll |
| 2 Reuse Map | Bound; inherits scout's `HarnessCardItem` error; no `probe_environment` | Bound; adds `LoginControlPort` RPC client (recorded); ignores existing `terminal_bridge.py` | Bound; uses `probe_environment`; deviation from socket-owned shape recorded | Bound; deviation from option (a) recorded; refactor-first table |
| 3 Red flags | DELETE route is pass-through; raw `tail` on JSON | Temporal split `prepare`/`evaluate`; `starting`/`evaluating` states and `start_failed.stage` expose stages | `display` stored beside argv/env (dup); GET is pass-through to gateway | URL regex on PTY bytes; `attemptId` plus `homeKey` dual identity |
| 4 Depth | 3 verbs + WS; `useHarnessLogin.start()` hides all | 4 ops but caller mints ids and handles `login_in_progress` conflict | 5 verbs; deepest gateway class, thinnest Python | 4 routes + 2 MCP tools; `login(wait_ms)` is one call end to end |
| 5 Idempotency | Per harness, join | Per client id + per harness; second browser must adopt the returned id | Per harness, adopt; exclusive occupancy covers port 1455 | Per home; live blocks, exited yields |
| 6 Outcome / re-read | `exit 0 && ready`; nonzero is `failed` even if credential landed; re-read only on socket close | Predicate has priority; app-scoped watcher survives pane close (only candidate) | No verdict; client re-reads readiness; re-read only on socket close | Pure `login_outcome(process, credential)`; re-read only on socket close |
| 7 Citations | 1 defect | 0 defects | 0 defects | 0 defects, corrects the scout |

## Red flags per candidate

- A `Usage`: `HarnessCard.tsx (extracted from FirstRunScreen.tsx per disposition 3)` references `HarnessCardItem`, which does not exist. A `Shape/login_routes.py`: `cancel_login` forwards to the gateway with no added policy (pass-through). A `Shape/LoginView.tail`: raw ANSI bytes on the control-plane JSON.
- B `Shape/Python domain`: `prepare_login` and `evaluate_login` are one owner's knowledge split by execution order (temporal decomposition). B `Gateway session model`: `state: "starting" | "evaluating"` and `start_failed.stage: "prepare" | "spawn"` publish internal stages (shallow module). B `Module map`: proposes extracting a "reusable gateway proxy module" without noting `api/v1/terminal_bridge.py` already holds origin and close helpers, and proposes refactoring `CaptureRpcClient` into a shared backend client, the widest blast radius of the four.
- C `Shape/LoginSpec`: `display: str` is a stored field on the same dataclass as `argv`/`env`, the drift the candidate says it is removing. C `Shape/LoginSpec`: `env = probe_environment(..., base_env=os.environ)` returns `dict(base_env)` minus home keys (verified in `probes/runner.py`), so the spawn body ships the whole backend environment to the gateway. C `Public HTTP`: GET proxies the gateway snapshot with no Python policy (pass-through).
- D `Text may buy affordances`: `verificationUrl` from a regex over the first 64 KiB. Xterm wraps at `cols`, and both harnesses print long URLs, so the bytes can split across lines and ANSI; the regex will miss in the common case the director needs it. D `Module map`: renames `GatewayRunTransport` to `GatewayHttpTransport`, scope outside the slice. D `Shape/LoginAttempt.home`: absolute path on the browser wire, not needed by either client.

## Citation defects

- A: `FirstRunScreen.tsx::HarnessCardItem`. Does not exist; the component is `FirstRunScreen.tsx::CardView` (B, C, D cite it correctly; D calls out the scout error).
- B, C, D: none found. Verified: `RunRouteProxy.forward_http` / `request_http` / `_forward_ws` / `_bridge_websockets` / `_close_upstream` / `_close_downstream`; `controlplane_gateway_runs.py::GatewayRunTransport` and `create_run`; `controlplane_mcp.py`; `commandTypes.ts::LauncherEffect` / `RowAction`; `paneRecords.ts::PaneContentRef`; `TerminalEmulator` / `TerminalStateSnapshot`; `TerminalFanout::AttachedTerminal`; `ports.ts::PtyExitEvent`; `RunInputDelivery.ts::RuntimeHarness`; `claude_fleet_auth.py::fleet_home_unavailable_reason` (returns "does not exist" when the dir is absent, so D's macOS question is real); `launch/environment.py` imports `env_keys`, `capabilities`, `channel` only, so D's no-cycle claim holds.

## Base: D (opus)

D is the only candidate whose verdict cannot lie: `login_outcome` is a pure function of process state and a fresh `_credential_check`, and the exit code is evidence only. A demotes a landed credential to `failed` on a nonzero exit; C offers no outcome on the resource at all. D is also the only design a director can drive in one call (`login(harness, wait_ms)` long poll rejoins or starts, `login_input` pastes), it lands the fleet-constant refactor first with a verified no-cycle path, and it is the only candidate that audited the scout and found its citation error. Its two substantive faults are graftable: the URL regex (replace with a raw tail, keeping the type quarantine) and the readiness re-read that fires only on socket close, so a pane detached mid-flow leaves the launcher stale until manual retry. A, C, and D all share that second hole; B alone closes it.

## Grafts

1. Take harness-keyed public identity from A/C (`/v1/logins/{harness}`, no `attempt_id` on any surface) because D's `homeKey` index already collapses to one record per harness and the `attemptId` scan is a second identity for nothing; attempt ids stay internal evidence only.
2. Take `output_tail` (bounded raw PTY text) from A/C in place of D's `verificationUrl` regex because it survives wrapping and ANSI, needs no parser, and the type quarantine D argued for holds trivially when nothing is extracted.
3. Take B's app-scoped `HarnessLoginCoordinator` watcher because closing the pane must not strand the launcher; drive it from D's `wait_ms` long poll rather than a GET loop, and invalidate `launchReadinessKey` and `harnessInventoryKey` on settle.
4. Take B's `environment: {set, unset}` patch shape for the spawn body because the gateway applies it over `browserPtyEnvironment(process.env)`; no candidate should ship the backend's environ (C does).
5. Take the grok verification flag from B/C (`command_verification: "verified" | "unverified"` on the spec, surfaced on the action) because D's "let it exit nonzero" leaves the card promising an action nobody has observed working.
6. Take C's `probe_environment` for computing the `unset` list (competing home and credential keys) so the stripping policy has one owner.
7. Take B's `LaunchReadinessCheck.action: {kind: "harness_login", harness_id, display_command}` so the card and palette derive the button from readiness, not from the inventory string; keep `authentication_command` as `spec.display` (C) until the last reader moves.

## Reject

1. B's `LoginControlPort` prepare/evaluate RPC from the gateway back into Python: inverts the call graph, teaches the gateway the credential outcome, and pulls a `CaptureRpcClient` refactor into the slice.
2. B's client-minted `LoginSessionId` with `login_session_conflict` / `login_in_progress` responses: caller coordination for a resource that is singular per harness.
3. B's eight-variant `LoginResult` and `starting`/`evaluating` states: D's five outcomes plus `exit_code` evidence cover every case.
4. C's stored `display` field and `harness` on `LoginSpec`: derive `display` as a property (A/D).
5. A's `nonzero exit -> failed` rule: contradicts "the predicate is the verdict".
6. D's `GatewayHttpTransport` rename and `LoginAttempt.home`: out of scope and needless on the wire.
7. Any modal (all four rejected it; keep the lazy pane behind `viewers/registry.tsx`).

## Open questions

- macOS Claude first login: `~/.claude-auth` absent makes `fleet_home_unavailable_reason` fail before spawn. Does `claude auth login` create `CLAUDE_CONFIG_DIR` itself (then spawn regardless), or must TM `mkdir` (writing into a harness home)?
- Cancel semantics: `DELETE` kills the PTY, not the browser child. Is an orphaned browser tab acceptable, or should cancel kill the process group?
- Does the director surface stay HTTP plus MCP (D), or HTTP only for this slice?
- Is one live login per harness per gateway acceptable once a multi-operator gateway exists?
- Grok: who runs the binary to flip `unverified` before the card shows a primary button?
