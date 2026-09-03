# 482: First run: in-app harness login driver (NOW.md 1.3)

URL: https://github.com/littleorgans/transport-matters/issues/482
State: open
Labels: enhancement
Updated: 2026-08-26T21:17:34Z

## Why

Launch readiness already reports `credential_unavailable` per harness (`captured/readiness.py::_credential_check` -> `/v1/launch-readiness` -> `templateRows.ts::launchBlockedReason`), but the only remediation is a terminal command. NOW.md Phase 1 says every reported state must carry an action that fixes it in the app. This issue delivers that action: TM spawns the harness's own login flow against the right home, shows it, and re-reads readiness on exit.

## Design

Architect design package, arena-synthesized and adjudicated: [`docs/plans/LOGIN-DRIVER-PLAN.md`](https://github.com/littleorgans/transport-matters/blob/main/docs/plans/LOGIN-DRIVER-PLAN.md). It owns the usage (director HTTP calls, palette and first-run card, gateway spawn), the type sketch, the slice order, tests, and gates. Where this issue and the plan disagree, the plan wins on shape and this issue wins on scope.

Load-bearing decisions:

- Exit is the trigger, the credential predicate is the verdict. `login_outcome` is a pure function of process evidence plus a fresh `_credential_check`; outcomes `succeeded | failed | cancelled | spawn_failed | lost`. Never match on `Login successful.` text.
- Public identity is harness-keyed: `POST/GET/DELETE /v1/logins/{harness}`, `POST /v1/logins/{harness}/input`. Start twice rejoins. No attempt id, home path, argv, env, or PTY types on any public surface.
- The fallback URL is read from a bounded raw `output_tail`; nothing parses it.
- Gateway sibling composition: `LoginSessions` over `ptyPort`, env as a `{set, unset}` patch over `browserPtyEnvironment(process.env)`, called by Python only. Never through `POST /v1/runs`, `RunManager`, or `cli/`.
- An app-scoped `HarnessLoginCoordinator` watches `GET ?wait_ms` and invalidates `launchReadinessKey` and `harnessInventoryKey` on settle; closing the pane detaches, never cancels. Lazy pane behind `viewers/registry.tsx`, no modal.
- `LaunchReadinessCheck.action {kind: "harness_login"}` drives the card and palette button; grok ships `command_verification: "unverified"` and renders disabled until the binary is observed.
- Claude fleet home moves to `default_storage_root() / "claude-auth"` (per channel) with env override `TRANSPORT_MATTERS_CLAUDE_AUTH_HOME`; `claude auth login` creates the directory itself (verified), so TM never mkdirs a harness home. Existing `~/.claude-auth` logins are invalidated (keychain service name derives from the config dir); no migration.
- `login_command` shell string is replaced by a structured `LoginSpec`; display derived. Fleet constants get one owner importable by `credential_broker.py`.

## Slices (one PR each, in order)

1. Fleet home resolver and `LoginSpec` (Python only, no wire change).
2. `action` on the readiness check; shared unset-key policy with `probe_environment`; grok unverified.
3. Gateway `LoginSessions`, routes, login terminal connection (`FakePtyPort` tests).
4. Python routes, `login_outcome` truth table, bridge extraction from `run_proxy.py` then the login WS.
5. `CardView` extraction from `FirstRunScreen.tsx` (mechanical).
6. Frontend driver: coordinator, pane, card button, palette row; inventory drops `authentication_command`.

Gates verbatim per slice: `just check`, `just test`, `pnpm --filter @tm/runtime test`, `pnpm --filter @tm/gateway test`, `pnpm --filter @tm/shell test`.

## Open questions (plan section "Open questions and risks")

- `GET` before any start returns `lost` when the credential is unavailable; acceptable for the director, or should the frontend treat pre-`POST` `lost` as idle?
- Cancel: SIGTERM to the process group, then SIGKILL after which grace period?
- Codex binds `127.0.0.1:1455`; should `spawn_failed` carry a port-in-use hint?
- Should the gateway login routes require the origin header the Python client sends?
- MCP tool wrapping of the director surface is a follow-up to this issue.

## Not in scope

`transport-matters codex -- login` stays CLI remediation. The startup gate (store picker, doctor at every start) is a separate Phase 1 item.

## Comment by srobinson at 2026-08-26T21:17:34Z (updated 2026-08-26T21:17:34Z)

https://github.com/littleorgans/transport-matters/issues/482#issuecomment-5431228269

Plan peer-reviewed (codex, independent of the synthesizing model): conditional sign-off with five corrections applied in 7e29c9bf (dropped `LoginSpec.harness`, acyclic shared owner as a new leaf `tm/harness_login.py`, env patch precedence so the active home key survives, internal attempt identity as a stale `onExit` guard, `verification` removed from the gateway types), then a clean sign-off on `docs/plans/LOGIN-DRIVER-PLAN.md` as filed.

## Sub issues
[]
