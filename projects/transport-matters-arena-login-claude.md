---
title: 'Arena candidate (claude): in-app harness login driver'
type: design
tags: [transport-matters, login-driver, arena, architect, NOW-1.3]
summary: Login is addressed by harness, not by session id. Python owns the spec and the outcome verdict; the gateway owns one PTY per harness behind an attach-only terminal with scrollback; the pane is a canvas pane that detaches without killing. Completion is process exit composed with the credential predicate, never text.
status: candidate
source: arena runner claude
created: 2026-08-27
---

## Problem

A `*_credential_unavailable` readiness check must carry an action that fixes it in the app. The
fix is the harness's own login command run against the right home, so the work is transport and
verdict, not authentication. Three constraints shape it. The PTY lives in the gateway, but the
control plane, the credential predicate, and every harness fact live in Python; a director must
start a login and learn its outcome through `/v1` alone. `login_command` is a shell string and
`PtyPort.spawn` takes argv plus env, so the spec must be structured before anything spawns
(Quality Map disposition 2). And the existing sibling shape, `PlainTerminalSessions`, binds a
PTY's life to one socket, which is wrong for a login: a pane closed mid-flow must not kill a
browser callback in progress, and a director that never opens a socket must still get a verdict.

## Usage (caller's view)

Director, control plane only:

```
POST /v1/harnesses/codex/login            -> 200 {harness:"codex", attempt:"…", state:"running",
                                                  display:"codex login", started_at:…}
POST /v1/harnesses/codex/login            -> 200 same attempt (idempotent while running)
GET  /v1/harnesses/codex/login            -> 200 {…, state:"running", tail:"…open https://auth… "}
GET  /v1/harnesses/codex/login            -> 200 {…, state:"succeeded", exit_code:0,
                                                  readiness:{id:"codex_credential", ready:true}}
DELETE /v1/harnesses/codex/login          -> 200 {…, state:"cancelled"}
GET  /v1/harnesses/grok/login             -> 404 login_not_started
```

`tail` is the last N KiB of raw PTY text, so the fallback URL is readable without parsing. The
verdict composes exit with the predicate: exit 0 alone is never success.

Palette, in the readiness card:

```ts
// HarnessCard.tsx (extracted from FirstRunScreen.tsx per disposition 3)
const login = useHarnessLogin(harnessId);            // wraps POST + pane open + readiness refetch
<button onClick={login.start} disabled={login.state === "running"}>Sign in</button>
// commandRows.ts: EFFECT_INTERACTIONS["login-harness"] = { enter: "run-stay", advance: "none" }
```

`useHarnessLogin.start` posts, then opens `{ kind: "login", harnessId }` as a canvas pane. The
pane is `useTerminalSession({ endpoint: { kind: "login", harnessId } })`; on socket close with
reason `login-exited` it invalidates `launchReadinessKey` and `harnessInventoryKey` and the card
re-renders from the server's verdict. Closing the pane detaches; the login keeps running.

Gateway, spawn:

```ts
// packages/gateway/src/main.ts
const logins = new LoginSessions({ clock, ptyPort });           // same NodePtyAdapter as runs
// runtimeRouter: registerLoginRoutes(app, { logins })
// POST /v1/logins {harness, argv, env, cwd?} -> LoginView ; GET/DELETE /v1/logins/:harness
// WS   /v1/logins/:harness/terminal?cols&rows  (attach, scrollback replay, detach on close)
```

Python bridge: `RunRouteProxy.forward_http` for the three HTTP verbs, one `@router.websocket`
for the terminal, after the WS helpers leave `run_proxy.py` (disposition 3).

## Shape

Data structures first. The identity of a login is the harness. There is at most one live login
per harness per gateway; a second start joins it. This makes `POST` idempotent without a client
token, makes "pane closed mid-flow" a non-event (the PTY is not socket owned), and makes the
frontend key trivial (`login:<harness>` pane id). Attempt ids exist for evidence, not addressing.

```python
# api/src/transport_matters/credential_source.py  (replaces login_command: str)
@dataclass(frozen=True)
class LoginSpec:
    """What TM spawns to obtain a credential. argv is exec, never shell."""
    argv: tuple[str, ...]
    env: Mapping[str, str]          # only the home key: {CLAUDE_CONFIG_DIR: "~/.claude-auth"}
    @property
    def display(self) -> str:
        """`KEY=value cmd args`, the one string prose and inventory render."""
        raise NotImplementedError

# _CredentialProfile.login_argv replaces login_command; the darwin claude source sets
# env={HOME_DIR_ENV_BY_HARNESS["claude"]: str(owner_home)}, native sources set the
# native home key from resolve_native_harness_home. One derivation, no parser.
def login_spec(source: CredentialSource) -> LoginSpec: ...
```

```python
# api/src/transport_matters/launch/environment.py
CLAUDE_FLEET_AUTH_HOME = Path("~/.claude-auth")   # moved here; credential_broker and
                                                  # claude_fleet_auth both import it (disposition 1)
# claude_fleet_auth.CLAUDE_FLEET_BOOTSTRAP_COMMAND becomes login_spec(claude_keychain_credential_source()).display
```

```python
# api/src/transport_matters/harnesses/login_driver.py   (new, pure policy, no I/O)
LoginState = Literal["running", "succeeded", "exited_unready", "failed", "cancelled", "spawn_failed"]

class LoginView(BaseModel):
    harness: HarnessId
    attempt: str
    state: LoginState
    display: str
    exit_code: int | None
    tail: str                      # bounded raw PTY text; the fallback URL lives here
    readiness: LaunchReadinessCheck | None   # present once the process has exited
    started_at: datetime
    ended_at: datetime | None

def login_verdict(exit: GatewayLoginExit, check: LaunchReadinessCheck) -> LoginState:
    """exit 0 and check.ready -> succeeded; exit 0 and not ready -> exited_unready;
    nonzero -> failed; killed by DELETE or shutdown -> cancelled. Never reads output."""
    raise NotImplementedError
```

```python
# api/src/transport_matters/api/v1/login_routes.py   (new)
@router.post("/harnesses/{harness}/login")
async def start_login(harness: HarnessId, request: Request) -> LoginView:
    # 404 unknown harness; readiness code harness_not_installed short-circuits as spawn_failed
    # source = resolve_harness_credential_source(...); spec = login_spec(source)
    # proxy.request_http("POST", "/v1/logins", body=GatewayStartLogin(harness, *spec))
    raise NotImplementedError
@router.get("/harnesses/{harness}/login")
async def read_login(...) -> LoginView:
    # gateway view; if exited, run _credential_check(harness) and login_verdict(...)
    raise NotImplementedError
@router.delete("/harnesses/{harness}/login")
async def cancel_login(...) -> LoginView: ...
```

Python holds no login state. The view is derived on every read from the gateway's record plus a
fresh predicate evaluation, so a stale backend cannot lie (derive, do not sync, per
single-source-of-truth). The gateway is the only writer of process state; Python is the only
writer of the verdict. Two actors, disjoint state, merge at the read boundary.

```ts
// packages/common/src/loginContract.ts
export interface GatewayStartLogin { harness: string; argv: string[]; env: Record<string,string>; cwd?: string }
export type GatewayLoginExit = { kind: "exited"; code: number } | { kind: "killed"; by: "cancel" | "shutdown" }
export interface GatewayLoginView { harness: string; attempt: string; startedAt: number; exit: GatewayLoginExit | null; tail: string }
export const LOGIN_EXITED_CLOSE_CODE = "login-exited";
```

```ts
// packages/runtime/src/service/LoginSessions.ts
/**
 * One PTY per harness, addressed by harness. Not socket owned: attachments come and
 * go, the process ends on its own exit, a cancel, or gateway shutdown. Keeps a
 * TerminalEmulator so late attachers (a reopened pane, a director) replay the
 * fallback URL. The exited record survives until the next start so GET after exit
 * still returns the verdict inputs.
 */
export class LoginSessions {
  constructor(options: { clock: Clock; ptyPort: PtyPort; tailBytes?: number });
  /** Idempotent: a running login for this harness is returned, not respawned. */
  start(input: GatewayStartLogin): Promise<GatewayLoginView>;
  view(harness: string): GatewayLoginView | undefined;
  attach(harness: string, size: TerminalSize): AttachedTerminal | undefined;
  cancel(harness: string): GatewayLoginView | undefined;
  closeAll(): Promise<void>;                  // joins closeGatewayResources
  // spawn env = browserPtyEnvironment({ ...process.env, ...input.env }, input.harness)
  // onExit -> record exit, fanout.closeAll({ code: LOGIN_EXITED_CLOSE_CODE, retryable: false })
}
```

```ts
// packages/runtime/src/server/loginRoutes.ts
export function registerLoginRoutes(app: FastifyInstance, deps: { logins: LoginSessions }): void;
// POST /v1/logins, GET|DELETE /v1/logins/:harness, WS /v1/logins/:harness/terminal
// WS body reuses pumpAttachment / parseTerminalResizeFrameText; 404 close when no session.
// RuntimeRouterDeps gains `logins?: LoginSessions`, third optional dep.
```

```ts
// www/packages/core/src/transport.ts
export function startHarnessLogin(harnessId: HarnessName): Promise<LoginView>;
export function readHarnessLogin(harnessId: HarnessName): Promise<LoginView>;
export function cancelHarnessLogin(harnessId: HarnessName): Promise<LoginView>;
export const harnessLoginKey = (harnessId: HarnessName) => ["harness-login", harnessId] as const;

// www/packages/canvas/src/infrastructure/runtime/terminalTransport.ts
export type TerminalEndpoint = { kind: "local" } | { kind: "captured-run"; runId: string }
                             | { kind: "login"; harnessId: HarnessName };
// terminalSocket.ts: loginTerminalSocketUrl(harnessId, cols, rows) -> /api/logins/{h}/terminal

// www/packages/canvas/src/firstrun/login/useHarnessLogin.ts
export function useHarnessLogin(harnessId: HarnessName): {
  state: LoginState | "idle"; display: string | null; start(): Promise<void>; cancel(): Promise<void>;
};
// start: mutate startHarnessLogin -> openPane({ kind: "login", harnessId }) (pane id `login:<h>`,
// reopening focuses). On pane close reason login-exited: invalidate harnessLoginKey,
// launchReadinessKey, harnessInventoryKey.

// www/packages/canvas/src/firstrun/login/LoginPane.tsx  (lazy in viewers/registry.tsx)
// Header: display command, state chip, Cancel. Body: xterm via useTerminalSession.
```

Load bearing decisions. Harness as identity removes a session id from every public surface and
resolves double start and mid-flow pane close by construction (idempotent transitions). Attach
with scrollback rather than socket ownership is why "PTY output is enough" holds for the URL:
whoever attaches, whenever, sees it; `tail` gives the director the same bytes without a socket.
Verdict in Python keeps the gateway ignorant of credentials and homes; it receives argv and env
and reports exit. Readiness reaches the launcher by invalidation, the pattern
`FirstRunScreen.tsx::HarnessSection.retry` already uses; no push channel is added. Validation
sits at three boundaries only: harness id in the Python route, `GatewayStartLogin` shape in the
gateway route, terminal size on the WS. Inside, types carry the invariants.

Interface depth. The public surface is three HTTP verbs on one resource and one WS. Behind it:
spec derivation, home selection per platform, idempotent spawn, scrollback replay, bounded tail,
exit capture, verdict composition, shutdown reaping. The palette hook hides all of it behind
`start()` and a state. The only thing exposed is `display`, which the card wants anyway.

Deliberately not done: no URL parsing, no output matching, no Python side process table, no
attempt history, no modal, no change to `POST /v1/runs`, `RunManager`, or `cli/`. TM writes
nothing into a harness home; the harness's own command does.

## Synthesis decision

## Tradeoffs accepted

- We accept one login per harness at a time in exchange for an id-free surface and idempotency
  by construction. Two operators on one gateway share the attempt; the second sees the first.
- We accept that Python re-evaluates the predicate on every `GET` after exit in exchange for a
  stateless backend that cannot report a stale verdict.
- We accept a `tail` of raw bytes on a JSON view in exchange for never parsing harness output.
  Readers see ANSI noise; the contract stays text agnostic.
- We accept that the exited record is overwritten by the next start in exchange for no history
  store. The verdict was already reflected into readiness, which is the durable surface.
- We accept a fourth hop for the WS (browser, FastAPI bridge, Fastify, PTY) because the bridge
  is the only door the browser has today; the HTTP verbs ride the same bridge.
- We accept that grok's `grok login` is unverified: the spec is derived for three harnesses, the
  route works for three, and the docs mark grok's command as unverified until the binary is
  observed honouring it.

## Alternatives considered

- Socket owned login, `PlainTerminalSessions` with argv (the scout's step 2). Smallest diff, but
  the pane closing kills the login mid callback, and a director with no socket gets no verdict.
  Fails API-first; hides nothing the attach shape does not, and exposes socket lifetime as policy.
- Gateway owns the verdict (gateway calls Python readiness through a fourth `CapturePort` RPC).
  Concentrates state in one process, but teaches the gateway what a credential is and grows the
  670 line `capture_rpc_routes.py`. Verdict belongs beside the predicate.
- Browser assembles the spawn spec from `GET /v1/harnesses` and opens the WS directly. No Python
  route, but the director then has no control plane path, and the browser becomes the second
  owner of argv and env. Rejected on API-first and single source of truth.
- Modal instead of pane. Blocks the canvas, needs a new Ark `Dialog` plus CSS, and a modal that
  survives close-without-kill is a pane with worse ergonomics.

## Open questions and risks

- Is one live login per harness acceptable for the multi-operator gateway, or should the
  identity be harness plus operator once owners exist on this surface?
- Codex binds `127.0.0.1:1455`; a second `codex login` on the same host fails on bind. Does the
  idempotent join cover this, or should `spawn_failed` carry a port-in-use hint?
- Should `LaunchReadinessCheck.remediation` gain a structured action, or does the frontend
  mapping of `*_credential_unavailable` plus `harness_id` to the login effect stay derived?
- Does moving `CLAUDE_FLEET_AUTH_HOME` into `launch/environment.py` avoid the import cycle the
  Quality Map names, or does `environment.py` already import from the broker chain?
- Claude on macOS logs into `~/.claude-auth`; the mint is access only and the broker still needs
  write back verification. Does a succeeded login change the readiness verdict immediately, or
  only after the next mint?

## Next implementation step

Replace `login_command: str` with `LoginSpec` in `credential_source.py`, derive `display`, move
`CLAUDE_FLEET_AUTH_HOME` so `_WRITE_BACK_ERROR_MESSAGE` imports it, and add
`test_credential_source.py` pinning argv, env, and display for all three harnesses.
