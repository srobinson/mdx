---
title: 'Arena candidate (grok): harness-keyed login driver'
type: projects
tags: [transport-matters, login-driver, arena, credential, pty]
summary: Login is an exclusive control-plane resource keyed by harness. Python owns LoginSpec. The gateway owns the PTY. Clients send a harness id.
status: draft
project: transport-matters
related: [transport-matters-scout-login-driver, transport-matters-arena-login-brief]
confidence: high
created: 2026-08-27
updated: 2026-08-27
---

# Login driver

## Problem

`credential_unavailable` is diagnosed and copied as a shell string. Nothing runs it. NOW.md 1.3 wants TM to spawn each harness's own login against the right home, complete on process exit, then re-read the credential predicate. The director and the palette are twin clients of one control plane (`docs/NORTHSTAR.md`). `PtyPort.spawn` wants argv and env. `NativeCredentialSource.login_command` / `KeychainCredentialSource.login_command` are display strings. The gateway already hosts sibling PTYs via `PlainTerminalSessions` and `handlePlainTerminalConnection`. The browser reaches them only through `RunRouteProxy`. A client-supplied argv on that WS would let the UI spawn arbitrary processes and would force the director to reconstruct harness facts. The occupancy rule on `PlainTerminalSessions` (socket close kills the PTY) would abort an OAuth callback when the viewer unmounts.

## Usage (caller's view)

Director (MCP, same verbs as HTTP):

```
login(harness="claude")
# -> {harness, status:"running", display:"CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login",
#     command_verified:true, output_tail:""}

# paste-code path, if the PTY asks
login_write(harness="claude", text="ABCD-1234\n")

# poll. Do not call login() again to poll; that would start a new attempt after exit.
login_status(harness="claude")
# -> {status:"exited", exit_code:0, output_tail:"...https://..."}  # URL is in the tail. Never parsed.

# verdict is the predicate, never the exit code
GET /v1/launch-readiness
# claude_credential check.ready == true
```

Palette / first-run card (`FirstRunScreen.tsx::CardView`):

```
const view = await postJson("/v1/logins/claude", {})
openPane({ kind: "harness-login", harness: "claude" })  // lazy registry pane
# on WS close: invalidateQueries(launchReadinessKey, harnessInventoryKey)
# if still running, the card says "Signing in. Reopen terminal." Sign in POSTs again (adopts).
```

Gateway spawn (Python is the only caller; public JSON never carries argv):

```
await transport.request_http("POST", "/v1/logins", spec_body)
# spec_body from resolve_login_spec. Gateway LoginSessions.open or adopt.
```

Cancel is `DELETE /v1/logins/{harness}` / `login_cancel`. Closing the pane detaches. The process keeps running until exit or DELETE.

## Shape

**LoginSpec replaces `login_command`.** One structured value. Display is derived. Callers that printed the string print `spec.display`. Encoded per type-system-discipline and encode-lessons-in-structure. Keeping both would recreate the `_WRITE_BACK_ERROR_MESSAGE` drift.

```python
# credential_source.py (login_command fields deleted)
@dataclass(frozen=True, slots=True)
class LoginSpec:
    harness: str
    argv: tuple[str, ...]
    env: dict[str, str]          # HOME_DIR_ENV_BY_HARNESS[h] = home, via probe_environment
    cwd: str
    display: str                 # derived; never stored on its own
    command_verified: bool       # False only for grok this slice

def resolve_login_spec(harness: str, *, native_home: Path) -> LoginSpec:
    raise NotImplementedError
    # source = resolve_harness_credential_source(harness, native_home=native_home)
    # home = source.owner_home if KeychainCredentialSource else source.credential_path.parent
    # env = probe_environment(harness_id=harness, home_dir=str(home), base_env=os.environ)
    # argv = profile.argv  # ("claude","auth","login") | ("codex","login") | ("grok","login")
    # display = " ".join(f"{k}={v}" for k,v in env.items() if k in HOME_DIR_ENV_BY_HARNESS) + " " + " ".join(argv)
```

Grok is a first-class harness with `command_verified=False`. The driver still spawns. UI copy may caveat. Nothing refuses.

**Public identity is the harness id.** Channel and home are implied by the backend that resolved the spec. One live login per harness. Foundational-thinking and model-the-domain: occupancy is a map `harness -> session`, a phase union, no uuid.

```python
LoginPhase = Literal["running", "exited", "cancelled", "spawn_failed"]

class LoginView(BaseModel):
    harness: str
    status: LoginPhase
    display: str
    command_verified: bool
    exit_code: int | None = None       # set only when exited
    spawn_error: str | None = None     # set only when spawn_failed
    output_tail: str = ""              # last 4KiB of PTY utf-8. Fallback URL lives here.
    # no logged_in. The driver does not know. launch_readiness does.
```

Illegal combinations do not compile. `exit_code` without `exited` is a constructor error in the Python model (validators) and unrepresentable in the TS union below.

```ts
export type LoginView =
  | { harness: HarnessName; status: "running"; display: string; commandVerified: boolean; outputTail: string }
  | { harness: HarnessName; status: "exited"; exitCode: number; display: string; commandVerified: boolean; outputTail: string }
  | { harness: HarnessName; status: "cancelled"; display: string; commandVerified: boolean; outputTail: string }
  | { harness: HarnessName; status: "spawn_failed"; reason: string; display: string; commandVerified: boolean };
```

**Two owners, no shared row.** Gateway `LoginSessions` owns the live PTY, fanout, occupancy, last tombstone. Python owns LoginSpec and `launch_readiness`. Python does not persist login rows. GET proxies the gateway and, after a terminal close, the client re-reads `GET /v1/launch-readiness`. Separate-before-serializing-shared-state.

**Idempotent POST** (make-operations-idempotent). Running: return the live view, ignore a second spec. Exited/cancelled/spawn_failed: spawn a new generation. Gateway crash: map empty, POST starts fresh. Two Codex logins cannot race on `127.0.0.1:1455` because occupancy is exclusive.

**Public HTTP (Python `api/v1/logins.py`).** Boundary-discipline: parse harness, reject unknown, never take argv from the client.

- `POST /v1/logins/{harness}` -> LoginView (start or adopt)
- `GET /v1/logins/{harness}` -> LoginView or 404
- `DELETE /v1/logins/{harness}` -> cancelled
- `POST /v1/logins/{harness}/stdin` `{text}` -> 204 (director paste)
- `WS /api/logins/{harness}/terminal?cols&rows` attach only. Missing session closes with `login-not-started`.

Python resolves `LoginSpec`, wraps nothing else, `POST`s argv/env/cwd to the gateway via `RunRouteProxy.request_http` (the existing `GatewayRunTransport`). The gateway login HTTP is a peer of `create_run` in `controlplane_gateway_runs.py`. Trusted process, same trust as `/v1/runs`.

**Gateway `LoginSessions`** (new, sibling of `PlainTerminalSessions`, same `NodePtyAdapter` instance from `createDefaultRuntimeRouterDeps`). Reuses `browserPtyEnvironment`, `TerminalFanout`, `pumpAttachment`, `socketDataToBytes`, `parseTerminalResizeFrameText`. Does not reuse socket-owned occupancy. Deliberate deviation from the scout's PlainTerminal clone: NOW.md 1.3 says own id and `PtySession.onExit` as completion. A viewer unmount is not completion.

```ts
export class LoginSessions {
  constructor(opts: { ptyPort: PtyPort; clock: Clock }) {}
  async open(input: { harness: RuntimeHarness; argv: readonly string[]; env: Record<string, string>; cwd: string; cols?: number; rows?: number }): Promise<LoginHandle> {
    throw new Error("not implemented");
    // adopt if running; else spawn via ptyPort, wrap env with browserPtyEnvironment(env, harness)
    // session.onExit -> tombstone {exited, exitCode}, close attachments with reason `login-exited:${code}`
  }
  snapshot(harness: RuntimeHarness): LoginView | undefined { throw new Error("not implemented"); }
  write(harness: RuntimeHarness, bytes: Uint8Array): void { throw new Error("not implemented"); }
  cancel(harness: RuntimeHarness): void { throw new Error("not implemented"); } // kill, tombstone cancelled
  attach(harness: RuntimeHarness, terminal: { cols: number; rows: number }): AttachedTerminal { throw new Error("not implemented"); }
  async closeAll(): Promise<void> { throw new Error("not implemented"); }
}
```

`RuntimeRouterDeps` gains optional `logins?: LoginSessions`. `registerLoginRoutes` next to `registerTerminalRoutes`. Join `installShutdownHandlers` / `closeGatewayResources`. Tests copy `plainTerminalConnection.test.ts` onto `FakePtyPort`.

**Readiness action.** `LaunchReadinessCheck.remediation` stays doctor prose. Add `action: { kind: "login"; harness_id: HarnessId } | None`. `_credential_check` sets it when `harness_credential_error` is not None. `CardView` and `launchBlockedReason` enable Sign in from `action`, and stop parsing `authentication_command` as the verb. Inventory `authentication_command` remains the derived `spec.display` so existing copy still has a string.

**Frontend.** `TerminalEndpoint` gains `{ kind: "login"; harness: HarnessName }`. `terminalSocket.ts` builds `/api/logins/${harness}/terminal`. New `PaneContentRef` kind `"harness-login"`. `LoginPane` wraps `useTerminalSession` behind `registry.tsx` (xterm stays lazy). Palette effect `login-claude` | `login-codex` | `login-grok` on `LauncherEffect` / `EFFECT_INTERACTIONS` / `useCommandCenter.ts::effectSink`. Stdin is the existing binary WS path.

**Grooming during the slice (dispositions).** Move `CLAUDE_FLEET_AUTH_HOME` to `launch/environment.py`. Drop `CLAUDE_FLEET_BOOTSTRAP_COMMAND`. `credential_broker.py::_WRITE_BACK_ERROR_MESSAGE` imports `resolve_login_spec("claude").display`. Extract `RunRouteProxy._forward_ws` / `_bridge_websockets` before the third WS route (`run_proxy.py` is 628). Extract `CardView` from `FirstRunScreen.tsx` (623) before the Sign in button. Deferred with reason, off the path: triple readiness evaluation, `home_constants` duplicates.

**Interface depth.** Public surface is harness id plus four verbs and one attach. Hidden behind it: home selection (keychain vs native), `probe_environment`, display derivation, exclusive occupancy, fanout, browser PTY env, WS bridge, tombstones. Callers never coordinate argv, env, or spawn. Call chain stays director/palette -> `logins.py` -> `LoginSessions` -> `PtyPort`.

**Red flags.** Shallow? No. Leakage? argv stays off the public JSON. Temporal modules? No, `LoginSessions` owns occupancy across start, attach, exit. Pass-through? `logins.py` adds spec resolution. `login_status` is a read of the same object, not a wrapper around readiness.

**Deliberately unused from the reuse map.** `POST /v1/runs`, `RunManager`, `cli/`, `cli/codex_cmd.py::run_codex`, `_capture_probe`, `Supervisor.spawn`, `CapturedRunPane`, `createCapturedRun`, Ark `Dialog`. Overlay worksheet `! <command>` is struck after ship.

## Synthesis decision

## Tradeoffs accepted

- We accept a Python-to-gateway HTTP spawn (mirroring `create_run`) in exchange for a public API that cannot carry argv and a gateway that stays ignorant of credential files.
- We accept a tombstone on GET after exit in exchange for a director that can poll without racing a respawn.
- We accept `output_tail` as raw PTY text in exchange for never parsing a fallback URL or matching `Login successful.`
- We accept detach-does-not-kill in exchange for OAuth that survives a pane close, plus a Reopen path on the card.
- We accept grok on the same driver with `command_verified=False` in exchange for one occupancy map rather than a two-harness special case.

## Alternatives considered

- **Browser fetches a login spec and passes argv on the WS query** (scout option a). Smaller gateway. The public surface becomes a spawn API. The director must reconstruct argv. Lost on leakage and API-first.
- **CapturePort RPC so the gateway asks Python for the spec, WS connect spawns.** One socket starts login. `capture_rpc_routes.py` is already 670 lines and the director still lacks HTTP stdin, status, and cancel. Lost on depth. HTTP would still be added.
- **Socket-owned PTY cloned from `PlainTerminalSessions`.** Least new code. Viewer unmount kills Codex's callback server. Lost on occupancy.
- **Ark Dialog hosting xterm.** No dialog primitive exists. It would block the canvas during a browser round trip. Lost on experience-first.

## Open questions and risks

- Does the grok CLI honour `grok login` with `GROK_HOME` the way `_CREDENTIAL_PROFILES` claims, or does the unverified flag need a follow-up once someone runs the binary?
- Is 4KiB of `output_tail` enough for Codex's fallback URL, or does the ring need to match `TerminalFanout`'s attachment queue?
- Should a running login appear on `roster`, or does a separate GET keep login out of the captured-run list on purpose?

## Next implementation step

Move `CLAUDE_FLEET_AUTH_HOME` into `launch/environment.py`, replace `login_command` with `LoginSpec` in `credential_source.py`, point `_WRITE_BACK_ERROR_MESSAGE` at `spec.display`, and lock it with new `test_credential_source.py`.
