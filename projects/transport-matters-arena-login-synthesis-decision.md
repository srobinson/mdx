# Synthesis decision: in-app harness login driver (orchestrator adjudication)

Judges split: claude verdict base=D (7 grafts), codex verdict base=B (4 grafts). The orchestrator adopts **D (opus) as base**. The deciding property: in D the verdict is a pure function of process state plus a fresh `_credential_check`, and the exit code is evidence only. B keeps the credential outcome in a gateway state machine fed by a prepare/evaluate RPC back into Python, which inverts the call graph and pulls a `CaptureRpcClient` refactor into the slice. B's genuine advantages (app-scoped watcher, env patch, typed failure coverage) graft onto D cleanly.

## Grafts (binding)

1. Harness-keyed public identity: `/v1/logins/{harness}` only. No `attempt_id`, session id, or home path on any public surface. Starting twice rejoins the live attempt (idempotent). Attempt ids stay internal gateway evidence.
2. `output_tail`: bounded raw PTY text (late-attach replay for a reopened pane). No URL regex, no vendor text parser. Directors read the fallback URL from the tail.
3. App-scoped watcher (B's coordinator idea) so a detached pane never strands the launcher; driven by D's `wait_ms` long poll; on settle invalidate `launchReadinessKey` and `harnessInventoryKey`.
4. Spawn environment as a patch `{set, unset}` applied over `browserPtyEnvironment(process.env)` in the gateway. `unset` computed in Python by the existing `probe_environment` policy (competing home and credential keys). Never ship the backend environ (C) and never supply a partial env that drops `PATH` (D's defect, per `NodePtyAdapter.processEnvironment`).
5. `command_verification: "verified" | "unverified"` on the login spec; grok is `unverified` until the binary is observed.
6. `LaunchReadinessCheck.action: {kind: "harness_login", harness_id, display_command}` so card and palette derive the button from readiness. `authentication_command` on inventory becomes `spec.display` until its last reader moves.
7. `login_outcome` is a pure function over private domain process evidence (not a gateway transport type) and the fresh credential check. Outcomes: `succeeded | failed | cancelled | spawn_failed | lost`, each with `exit_code` evidence where a process ran. `lost` covers a gateway restart: records are process-local; a missing record with the credential now ready reads as `succeeded` (the predicate is the verdict), a missing record with the credential still unavailable reads as `lost`. No tombstone store.
8. Fleet-constant refactor first: one owner for `CLAUDE_FLEET_AUTH_HOME` / `CLAUDE_FLEET_BOOTSTRAP_COMMAND` importable by `credential_broker.py` without a cycle (D's verified path).

## Rejected

- B's prepare/evaluate RPC from gateway into Python; B's client-minted session id and `login_session_conflict`; B's eight-variant result and `starting`/`evaluating` public states.
- A's nonzero-exit-means-failed rule; A's shared wire types in `packages/common`.
- C's stored `display` field, `harness` on the spec, backend environ shipping, separate status/readiness reads.
- D's `verificationUrl` regex, `LoginAttempt.home`, `GatewayHttpTransport` rename.
- Any modal. The surface is a lazy pane behind `viewers/registry.tsx`, on `useTerminalSession` with a `login` endpoint kind (hook change required, per codex verdict on replay selection).

## Decisions taken by the orchestrator (revisable by the human)

- Cancel = terminate the process group, so callback servers and browser launchers die with the login.
- Director surface for this slice: HTTP only (`POST/GET/DELETE /v1/logins/{harness}`, `POST /v1/logins/{harness}/input`). MCP tool wrapping is a follow-up.
- Grok `unverified`: action rendered disabled with the reason, never a primary button.
- One live login per harness per gateway is the contract.

## Amendment 1 (human decision, 2026-08-27)

- Verified empirically: `CLAUDE_CONFIG_DIR=<absent dir> claude auth status` creates the directory (`.claude.json`, lock, `backups/`); `claude --version` does not. `claude auth login` therefore creates its own home. TM never `mkdir`s a harness home. `fleet_home_unavailable_reason` must stop treating an absent fleet home as unavailable for the purpose of spawning a login; absence is the first-run state the login fixes. It stays a reason for the credential predicate (no credential yet).
- The Claude fleet home moves out of `~/.claude-auth` into the channel home: default `default_storage_root() / "claude-auth"` (`config.py::default_storage_root`), so stable, preview, and dev each own a fleet home, consistent with channels sharing nothing. Env override: `TRANSPORT_MATTERS_CLAUDE_AUTH_HOME` declared in `env_keys.py` beside `HOME` (same `ENV_PREFIX` convention). `CLAUDE_FLEET_AUTH_HOME` stops being a module constant and becomes a resolver `claude_fleet_auth_home(env) -> Path`; the display command derives from it. Keychain service name derives from `sha256(config_dir)`, so the move invalidates any existing `~/.claude-auth` login; no migration (private repo, no users).
- Slice 1 absorbs this: the fleet-constant refactor becomes the resolver, tests pin default, override, and per-channel distinctness.
