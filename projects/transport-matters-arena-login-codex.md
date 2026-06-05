# In app harness login driver

## Problem

A failed credential readiness check must offer one action that runs the harness login in Transport Matters, preserves the harness terminal interaction, and reports the resulting credential state to people and director agents. Python already owns credential home selection and readiness. The gateway already owns PTYs. The design must join those owners without placing executable argv or environment data in the browser, without creating run capture state, and without teaching Transport Matters any vendor login protocol. Existing seams are `api/src/transport_matters/credential_source.py::resolve_harness_credential_source`, `api/src/transport_matters/captured/readiness.py::launch_readiness`, `packages/runtime/src/ports.ts::PtyPort`, and `packages/runtime/src/service/TerminalFanout.ts::TerminalFanout`.

## Usage (caller's view)

### Director control plane

The director reads the action from canonical readiness, chooses an id once, and uses that id for every retry. Terminal attachment is optional unless the flow needs input or the fallback URL.

```ts
const readiness = await controlPlane.getLaunchReadiness();
const action = readiness.checks
  .find((check) => check.action?.kind === "harness_login")
  ?.action;
if (action === undefined) throw new Error("no login action available");

const sessionId = loginSessionId(crypto.randomUUID());
await controlPlane.putLoginSession(sessionId, { harnessId: action.harnessId });

// Repeating the PUT with the same id returns the same session.
const result = await controlPlane.waitForLoginSession(sessionId);
```

For interactive use, the director connects to
`/v1/login-sessions/{sessionId}/terminal?cols=120&rows=30`. Binary client frames are stdin. Existing resize text frames keep their current shape. The gateway sends the terminal snapshot first, then live output, then a final session frame before closing the socket.

### Palette and first run

Both surfaces call one app scoped coordinator. The coordinator starts the session, opens its pane, watches the session after the pane detaches, and refreshes readiness when the gateway publishes the final result.

```ts
const startLogin = useHarnessLoginCoordinator();

await startLogin(check.action); // action.kind is "harness_login"
```

The pane shows unchanged PTY output. A browser fallback URL therefore remains visible and selectable without an output parser. Paste and typed input use `www/packages/canvas/src/viewers/terminal/terminalSession.ts::useTerminalSession`.

### Gateway spawn

The public request contains a session id and harness id. The gateway obtains the executable specification from Python over its existing backend origin.

```ts
const prepared = await loginControl.prepare({ harnessId });
if (prepared.kind === "already_ready") return finishAlreadyReady(prepared);

const env = applyEnvironmentPatch(
  browserPtyEnvironment(process.env, harnessId),
  prepared.spawn.environment,
);
const pty = await ptyPort.spawn({
  argv: prepared.spawn.argv,
  cwd: prepared.spawn.cwd,
  env,
  cols: DEFAULT_TERMINAL_COLS,
  rows: DEFAULT_TERMINAL_ROWS,
});
```

`LoginSessions` subscribes to `PtySession.onExit`, rechecks the credential through `LoginControlPort`, stores the result, then closes terminal attachments. No success text is inspected.

## Shape

### Python domain and readiness action

Replace every stored `login_command: str` with one structured value. The display command is a property of that value. The executable environment is represented as a patch so no ambient secret value crosses the internal API.

```py
LoginCommandVerification = Literal["verified", "unverified"]

@dataclass(frozen=True, slots=True)
class LoginEnvironmentPatch:
    set: Mapping[str, str]
    unset: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class HarnessLoginSpec:
    argv: tuple[str, ...]
    home_env: str
    home: Path
    verification: LoginCommandVerification

    @property
    def display_command(self) -> str:
        raise NotImplementedError

    def environment_patch(self) -> LoginEnvironmentPatch:
        raise NotImplementedError

CLAUDE_FLEET_LOGIN_SPEC = HarnessLoginSpec(
    argv=("claude", "auth", "login"),
    home_env="CLAUDE_CONFIG_DIR",
    home=Path("~/.claude-auth"),
    verification="verified",
)

class HarnessLoginAction(BaseModel):
    kind: Literal["harness_login"] = "harness_login"
    harness_id: HarnessId
    label: str
    display_command: str
    command_verification: LoginCommandVerification
```

`NativeCredentialSource.login` and `KeychainCredentialSource.login` hold `HarnessLoginSpec`. `api/src/transport_matters/credential_source.py::_CREDENTIAL_PROFILES` holds argv plus verification. Source resolution adds the selected native home, or `CLAUDE_FLEET_LOGIN_SPEC` on macOS. Claude and Codex are verified. Grok has `argv=("grok", "login")` and `verification="unverified"`.

`LaunchReadinessCheck` gains `action: HarnessLoginAction | None`. `api/src/transport_matters/captured/readiness.py::_credential_check` adds the action only when the credential predicate fails. Delete `HarnessInventoryItem.authentication_command`; first run reads the display command from this readiness action. No second command string or legacy response path remains.

The internal Python boundary exposes two operations:

```py
class PrepareLoginRequest(BaseModel):
    harness_id: HarnessId

class PrepareLoginResult(BaseModel):
    # Discriminated union in the implementation: already_ready | spawn.
    pass

@router.post("/prepare")
async def prepare_login(request: PrepareLoginRequest) -> PrepareLoginResult:
    raise NotImplementedError

@router.post("/evaluate")
async def evaluate_login(request: PrepareLoginRequest) -> CredentialEvaluation:
    raise NotImplementedError
```

`prepare_login` reuses `launch_readiness` to make a stale action converge without a spawn. Its spawn branch resolves `HarnessLoginSpec`. `evaluate_login` calls `launch_readiness` again and extracts the named harness credential check. This preserves the existing predicate owner and leaves the recorded triple readiness evaluation refactor out of scope.

### Gateway session model

The gateway is the only login session writer. Python owns no live session table. The public model uses branded ids and discriminated states.

```ts
type LoginSessionId = string & { readonly __brand: "LoginSessionId" };
type LoginArgv = readonly [string, ...string[]];

interface LoginSessionBase {
  id: LoginSessionId;
  harnessId: RuntimeHarness;
  createdAt: string;
}

interface LoginFailure {
  code: string;
  message: string;
  retryable: boolean;
}

type CredentialEvaluation =
  | { kind: "ready" }
  | { kind: "unavailable"; code: string; detail: string };

type PreparedLogin =
  | { kind: "already_ready" }
  | {
      kind: "spawn";
      spawn: {
        argv: LoginArgv;
        cwd: string;
        environment: { set: Readonly<Record<string, string>>; unset: readonly string[] };
        verification: "verified" | "unverified";
      };
    };

type LoginSessionView =
  | (LoginSessionBase & { state: "starting" })
  | (LoginSessionBase & { state: "running"; startedAt: string })
  | (LoginSessionBase & { state: "evaluating"; exit: PtyExitEvent })
  | (LoginSessionBase & {
      state: "finished";
      finishedAt: string;
      result: LoginResult;
    });

type LoginResult =
  | { kind: "already_ready" }
  | { kind: "credential_ready"; exit: PtyExitEvent }
  | { kind: "credential_unavailable"; exit: PtyExitEvent; code: string; detail: string }
  | { kind: "process_failed"; exit: PtyExitEvent; code: string; detail: string }
  | { kind: "cancelled_before_spawn" }
  | { kind: "cancelled"; exit: PtyExitEvent; code: string; detail: string }
  | { kind: "readiness_unavailable"; exit: PtyExitEvent; failure: LoginFailure }
  | { kind: "start_failed"; stage: "prepare" | "spawn"; failure: LoginFailure };

type AttachedLoginTerminal =
  | { kind: "live"; snapshot: TerminalStateSnapshot; attached: AttachedTerminal }
  | {
      kind: "finished";
      snapshot: TerminalStateSnapshot;
      session: Extract<LoginSessionView, { state: "finished" }>;
    };

interface LoginControlPort {
  prepare(input: { harnessId: RuntimeHarness }): Promise<PreparedLogin>;
  evaluate(input: { harnessId: RuntimeHarness }): Promise<CredentialEvaluation>;
}

class LoginSessions {
  start(input: { id: LoginSessionId; harnessId: RuntimeHarness }): Promise<LoginSessionView> {
    throw new Error("not implemented");
  }
  get(id: LoginSessionId): LoginSessionView | null {
    throw new Error("not implemented");
  }
  attach(id: LoginSessionId, terminal: TerminalSize): Promise<AttachedLoginTerminal> {
    throw new Error("not implemented");
  }
  cancel(id: LoginSessionId): Promise<LoginSessionView | null> {
    throw new Error("not implemented");
  }
  closeAll(): Promise<void> {
    throw new Error("not implemented");
  }
}
```

`start` claims both maps before its first `await`: one record by id and one active id by harness. The same id and harness returns the existing record. The same id with another harness returns `login_session_conflict`. A new id while that harness is active returns `login_in_progress` with the active id. A new id after completion replaces that harness's prior result and disposes its emulator. The maps therefore hold at most one session per supported harness.

Each running record owns `PtySession`, `TerminalEmulator`, and `TerminalFanout`. The emulator preserves the fallback URL and prompt output when process start wins the race with browser attachment. Socket detachment leaves the process running. `DELETE` requests cancellation. Gateway shutdown kills every live PTY through `packages/gateway/src/main.ts::closeGatewayResources`.

Final outcome gives the credential predicate priority. A ready predicate produces `credential_ready` for any exit code. An unavailable predicate produces `cancelled`, `process_failed`, or `credential_unavailable` from cancel intent and `PtyExitEvent`. A failed reevaluation produces `readiness_unavailable`. This keeps process evidence separate from the product outcome.

The public control plane is:

```text
PUT    /v1/login-sessions/{session_id}             { harness_id }
GET    /v1/login-sessions/{session_id}
DELETE /v1/login-sessions/{session_id}
WS     /v1/login-sessions/{session_id}/terminal
```

The Python origin proxies these routes. The gateway parses ids, harnesses, JSON, and internal RPC responses at their boundaries. Internal methods receive domain types.

### Frontend composition

Add `{ kind: "harness-login"; harnessId; sessionId; label }` to `PaneContentRef`. `LoginPane` is lazy beside `TerminalPane` and `CapturedRunPane` in `www/packages/canvas/src/viewers/registry.tsx`. `TerminalEndpoint` gains `{ kind: "harness-login"; sessionId }`. The terminal connection reuses snapshot replay, binary stdin, resize frames, paste registration, selection copy, and close handling.

`HarnessLoginCoordinator.start(action)` generates the id once, performs the idempotent PUT, opens or focuses the pane, and watches GET until `finished`. The ordered final terminal frame can settle the same query sooner. Completion updates the login query, invalidates `launchReadinessKey` and `harnessInventoryKey`, and leaves the finished pane available as evidence. The watcher is app scoped, so closing the pane does not strand stale launcher state.

`RowAction` gains `{ kind: "harness-login"; action: HarnessLoginAction }`. First run cards and palette rows dispatch that action through the same coordinator.

### Module map and implementation order

- Add `api/src/transport_matters/harness_login.py` for `HarnessLoginSpec`, display derivation, environment patch derivation, verification, and `CLAUDE_FLEET_LOGIN_SPEC`.
- Refactor `api/src/transport_matters/credential_broker.py::_WRITE_BACK_ERROR_MESSAGE` first. It interpolates `CLAUDE_FLEET_LOGIN_SPEC.display_command`. `api/src/transport_matters/claude_fleet_auth.py` and credential source import the same constant.
- Replace `credential_source.py::login_command` with `HarnessLoginSpec`. Delete the inventory command field and derive the readiness action from the spec.
- Add `api/src/transport_matters/api/v1/login_control.py` for gateway preparation and evaluation.
- Extract the HTTP and WebSocket bridge mechanics from `api/src/transport_matters/api/v1/run_proxy.py::RunRouteProxy` into a reusable gateway proxy module before adding `login_proxy.py`. Run proxy remains below 700 lines.
- Refactor `packages/runtime/src/adapters/CaptureRpcClient.ts` into a backend RPC client shared by `CapturePort` and `LoginControlPort`. Shared request, timeout, error, and JSON parsing stay in one implementation.
- Add `packages/runtime/src/service/LoginSessions.ts`, `server/loginRoutes.ts`, and `server/loginTerminalConnection.ts`. Register them through `RuntimeRouterDeps` without touching `RunManager`.
- Extract `www/packages/canvas/src/firstrun/FirstRunScreen.tsx::CardView` as `HarnessCardItem` before adding the sign in action. Add the coordinator, pane, endpoint, and palette action in separate modules.
- Leave `cli/home_constants.py` duplication and the three readiness evaluations unchanged. Both are outside this execution path.

This public interface is deep: four control plane operations hide command resolution, environment isolation, PTY replay, concurrency, cancellation, and credential reevaluation. Callers know only the harness action and session id. No public option exposes argv, home, or gateway stages.

## Synthesis decision

## Tradeoffs accepted

- We accept process local session history in exchange for one live state owner and no partial database records. A gateway restart loses the session id, then startup readiness reports the actual credential state.
- We accept one active login per harness in exchange for deterministic home writes and simple retry behavior.
- We accept one internal Python request at start and one after exit in exchange for keeping harness facts and credential predicates out of TypeScript.
- We accept the PTY output as the fallback URL contract in exchange for avoiding vendor output parsers. Emulator replay and copy selection preserve that output.

## Alternatives considered

- Browser supplied argv and env makes the gateway implementation smaller. It exposes executable policy to an untrusted boundary and forces every caller to understand home selection, so it loses on interface depth.
- Python owned session state requires a second PTY host or callback synchronization with the gateway. Both shapes split one lifecycle across processes and expose more coordination to callers.
- A modal attached to a plain terminal socket avoids a new pane kind. It loses output before attachment, couples process lifetime to UI lifetime, and adds a new dialog system. A replayable pane fits the existing canvas model and survives temporary detachment.

## Open questions and risks

- Does `grok login` honor `GROK_HOME` in the currently supported binary? Until a real probe proves both, should the UI show the unverified action with a warning or suppress its primary button?
- Should explicit cancellation escalate from `SIGTERM` after a bounded grace period, and which existing gateway shutdown policy should define that period?
- Does every supported desktop route keep the app scoped login coordinator mounted while panes close and reopen? If any route tears it down, where should its query watcher move so readiness invalidation remains guaranteed?

## Next implementation step

Build and test the Python `HarnessLoginSpec` plus readiness action first, including the shared Claude fleet constant refactor, before exposing any gateway route.
