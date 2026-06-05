---
title: "Architect design: in-app harness login driver"
type: design
tags: [transport-matters, login-driver, credential, pty, gateway, NOW-1.3]
summary: A login is an attempt on a credential predicate, keyed by harness. Python owns the spec and the verdict, the gateway owns one PTY per harness behind an attach-only terminal with a raw replay ring, an app-scoped watcher carries the outcome back to the launcher, and no client ever sends argv. Exit is the trigger, the predicate is the verdict.
status: active
source: arena synthesis (base D opus, grafts from A, B, C), orchestrator adjudication
baseline: main 83f3decf
created: 2026-08-27
---

Every cited symbol was checked against `main` at `83f3decf`. Paths are repo-relative; `api/src/transport_matters/` is shortened to `tm/`, `packages/runtime/src/` to `runtime/`, `www/packages/canvas/src/` to `canvas/`.

## Problem

`GET /v1/launch-readiness` reports `*_credential_unavailable` and hands the operator a shell string. NOW.md 1.3 wants TM to run that command itself: spawn the harness's own login against the right home, treat process exit as completion, then re-read the credential predicate. The knowledge is split and stays split. `tm/credential_source.py::_CREDENTIAL_PROFILES` and `tm/launch/environment.py::HOME_DIR_ENV_BY_HARNESS` own command and home; only the gateway owns a PTY (`runtime/ports.ts::PtyPort`, `runtime/service/PlainTerminalSessions.ts`); the predicate `tm/captured/readiness.py::_credential_check` is Python's. The browser reaches the gateway only through `tm/api/v1/run_proxy.py::RunRouteProxy`, so whatever the browser can put on that wire the gateway will execute. The palette and the director are twin clients of one control plane, so a director with no terminal must still complete a paste-code login. The load-bearing sentence: **the process exit is a trigger, the credential predicate is the verdict.** `claude auth login` can exit 0 after the user closes the browser tab and can exit non-zero after writing a good credential. Every type below is arranged so no code can mistake one for the other.

## Usage (caller's view)

Director, HTTP only this slice. One call starts or rejoins; the same call long-polls for the verdict.

```
POST /v1/logins/claude?wait_ms=0
  -> {harness_id:"claude", outcome:"running",
      display_command:"CLAUDE_CONFIG_DIR=~/.transport-matters/claude-auth claude auth login",
      command_verification:"verified", output_tail:"...https://claude.ai/oauth/...", exit_code:null,
      credential:{id:"claude_credential", ready:false, ...}}
POST /v1/logins/claude/input   {text:"A1B2-C3D4\n"}          # paste-code prompts
GET  /v1/logins/claude?wait_ms=120000                            # returns early when the process settles
  -> {outcome:"succeeded", exit_code:0, credential:{ready:true, ...}}
DELETE /v1/logins/claude -> {outcome:"cancelled", ...}
```

The URL is read from `output_tail`, raw PTY text. Nothing parses it. Starting twice while running returns the live attempt.

First run card and palette share one app-scoped coordinator. The button comes from readiness, never from an inventory string.

```tsx
const login = useHarnessLogin();                       // context from HarnessLoginCoordinator
const action = check.action;                           // LaunchReadinessCheck.action, kind "harness_login"
<button disabled={action.command_verification === "unverified"} onClick={() => void login.start(action)}>
  Sign in to {card.title}
</button>
```

`start` posts, opens the pane `{ kind: "harness-login", harness }`, and watches `GET ?wait_ms` until the outcome settles. Closing the pane detaches; the watcher keeps going and invalidates `launchReadinessKey` and `harnessInventoryKey` on settle. The card re-renders from the server's verdict. No modal.

Gateway, called by Python only:

```ts
const record = await logins.start({
  harness: "claude",
  argv: ["claude", "auth", "login"],
  cwd: homedir(),
  environment: { set: { CLAUDE_CONFIG_DIR: "/Users/x/.transport-matters/claude-auth" }, unset: ["CODEX_HOME", "GROK_HOME", ...] },
  verification: "verified",
});
```

## Shape

### Identity is the harness

One live login per harness per gateway. `LoginSessions` keys its map by `RuntimeHarness`; `start` returns a running record unchanged and replaces a settled one. Live blocks, settled yields. The map holds at most three entries, so there is no TTL and no sweeper (per make-operations-idempotent). No attempt id, session id, or home path appears on any public surface; the harness home is the write target and is private to Python.

### Argv never crosses a client boundary

Browser and director send `{harness}`. Python resolves argv and the environment patch from the credential seam and calls the gateway over the private HTTP path `RunRouteProxy.request_http` already provides. The bridge gains one WebSocket route carrying a harness and a terminal size. Recorded deviation from the scout's option (a), on that reason.

### Python: the spec (`tm/credential_source.py`)

`login_command: str` is deleted from `NativeCredentialSource`, `KeychainCredentialSource`, and `_CredentialProfile`. One structured value replaces it; the string is derived.

```python
type LoginCommandVerification = Literal["verified", "unverified"]

@dataclass(frozen=True, slots=True)
class LoginEnvironmentPatch:
    set: Mapping[str, str]
    unset: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class LoginSpec:
    """The harness's own login rendered as something spawnable. argv is exec, never shell."""
    harness: str
    argv: tuple[str, ...]
    home_env: str                     # HOME_DIR_ENV_BY_HARNESS[harness]
    home: Path                        # the home the predicate itself resolved
    verification: LoginCommandVerification

    @property
    def display(self) -> str:
        """`codex login`; the env prefix appears only when home is not the native default."""
        raise NotImplementedError

    def environment_patch(self) -> LoginEnvironmentPatch:
        """set = {home_env: home}; unset = stripped_environment_keys(home_dir=str(home))."""
        raise NotImplementedError

def resolve_login_spec(source: CredentialSource) -> LoginSpec:
    """Derive argv, home and verification from the resolved source. The one owner of all three."""
    raise NotImplementedError
```

`_CredentialProfile` gains `login_argv: tuple[str, ...]` and `verification`; grok is `unverified` until the binary is observed. Every prose site (`_native_credential_failure`, `_keychain_credential_failure`, `tm/harnesses/inventory.py::harness_inventory` for `authentication_command`) reads `resolve_login_spec(source).display`. `home` always carries the home the predicate resolved, closing a real hole: a login writing `~/.codex` while the predicate reads `CODEX_HOME` from the operator's shell reports failure after succeeding.

The Claude fleet home moves into the channel home. `tm/claude_fleet_auth.py::CLAUDE_FLEET_AUTH_HOME` stops being a module constant and becomes a resolver; `CLAUDE_FLEET_BOOTSTRAP_COMMAND` is deleted; `tm/credential_broker.py::_WRITE_BACK_ERROR_MESSAGE` composes `resolve_login_spec(claude_keychain_credential_source()).display`. One owner for the string that drifted.

```python
# tm/env_keys.py, beside HOME
CLAUDE_AUTH_HOME = f"{ENV_PREFIX}CLAUDE_AUTH_HOME"      # TRANSPORT_MATTERS_CLAUDE_AUTH_HOME

# tm/claude_fleet_auth.py
def claude_fleet_auth_home(env: Mapping[str, str] | None = None) -> Path:
    """env[CLAUDE_AUTH_HOME] when set, else default_storage_root() / "claude-auth"."""
    raise NotImplementedError
```

`tm/storage_roots.py::default_storage_root` already keys on the channel, so stable, preview, and dev each own a fleet home, consistent with channels sharing nothing. `storage_roots` imports only `env_keys` and `channel`, so `claude_fleet_auth` can import it without a cycle. `KeychainCredentialSource.owner_home`, the broker, and `LoginSpec.home` all read the resolver.

Absence of the fleet home is the first-run state the login fixes. Verified on 2026-08-27: `CLAUDE_CONFIG_DIR=<absent dir> claude auth status` creates the directory itself, so `claude auth login` creates its own home. TM never `mkdir`s a harness home. `fleet_home_unavailable_reason` keeps reporting an absent home to the credential predicate (there is no credential yet) and stops being consulted on the spawn path: `start_login` resolves the spec and spawns regardless of whether the home exists.

The `unset` policy has one owner. `tm/launch/environment.py` gains `stripped_environment_keys(*, home_dir: str | None) -> frozenset[str]` (every `HOME_DIR_ENV_BY_HARNESS` value, plus `HARNESS_CREDENTIAL_ENV_KEYS` when `home_dir` is explicit) and `tm/harnesses/probes/runner.py::probe_environment` calls it instead of inlining the loops. The backend environ never leaves the backend.

### Python: readiness action (`tm/captured/readiness.py`)

```python
class HarnessLoginAction(BaseModel):
    model_config = ConfigDict(frozen=True)
    kind: Literal["harness_login"] = "harness_login"
    harness_id: HarnessId
    display_command: str
    command_verification: LoginCommandVerification

class LaunchReadinessCheck(BaseModel):
    ...                                   # existing fields unchanged
    action: HarnessLoginAction | None = None
```

`_credential_check` sets `action` when the predicate fails. `remediation` stays doctor prose. Inventory `authentication_command` becomes `spec.display` and is removed once `canvas/firstrun/harnessCards.ts::harnessCard` stops reading it (slice 6).

### Python: the verdict (`tm/api/v1/logins.py`, `tm/api/v1/gateway_logins.py`)

```python
class LoginOutcome(StrEnum):
    RUNNING = "running"; SUCCEEDED = "succeeded"; FAILED = "failed"
    CANCELLED = "cancelled"; SPAWN_FAILED = "spawn_failed"; LOST = "lost"

# gateway_logins.py: private domain evidence parsed from the gateway JSON at the boundary.
type LoginProcessEvidence = (
    ProcessRunning | ProcessExited | ProcessCancelled | ProcessSpawnFailed | ProcessMissing
)   # ProcessExited(exit_code: int); ProcessCancelled(exit_code: int | None); ProcessSpawnFailed(message: str)

class LoginView(BaseModel):
    """What both clients read. exit_code is evidence; outcome is the verdict."""
    model_config = ConfigDict(frozen=True)
    harness_id: HarnessId
    outcome: LoginOutcome
    display_command: str
    command_verification: LoginCommandVerification
    output_tail: str                  # bounded raw PTY text; the fallback URL lives here
    exit_code: int | None
    credential: LaunchReadinessCheck  # freshly evaluated by _credential_check on every read
    detail: str

def login_outcome(process: LoginProcessEvidence, credential: LaunchReadinessCheck) -> LoginOutcome:
    """Pure. running -> RUNNING. Otherwise credential.ready -> SUCCEEDED (missing record included).
    Not ready: exited -> FAILED, cancelled -> CANCELLED, spawn_failed -> SPAWN_FAILED, missing -> LOST."""
    raise NotImplementedError

async def start_login(harness_id: HarnessId, wait_ms: int = 0) -> LoginView: ...      # POST /v1/logins/{harness}
async def read_login(harness_id: HarnessId, wait_ms: int = 0) -> LoginView: ...       # GET, long poll
async def cancel_login(harness_id: HarnessId) -> LoginView: ...                        # DELETE
async def write_login_input(harness_id: HarnessId, body: LoginInputBody) -> LoginView: ...  # POST .../input
```

Python stores nothing. Every route resolves the spec, calls the gateway through `GatewayRunTransport` (`gateway_logins.py` is a peer of `tm/api/v1/controlplane_gateway_runs.py::create_run`), parses the record into `LoginProcessEvidence`, re-reads `_credential_check`, and composes `login_outcome`. A gateway restart empties the map; `ProcessMissing` with a ready credential is `SUCCEEDED`, with an unavailable credential is `LOST`. No tombstone store, nothing to migrate. `login_outcome` is the only place the two facts meet, and it is pure (per boundary-discipline: the route is the shell, the decision is a function with a test file). Unknown harness is 404 at the route boundary; `wait_ms` is clamped there.

The bridge: `RunRouteProxy._forward_ws`, `_bridge_websockets`, `_close_upstream`, `_close_downstream` move to `tm/api/v1/terminal_bridge.py` as module functions before the third WebSocket route `WS /api/logins/{harness}/terminal` is added beside `forward_plain_terminal`.

### Gateway (`runtime/service/LoginSessions.ts`)

```ts
export type LoginProcessState =
  | { status: "running" }
  | { status: "exited"; exitCode: number }
  | { status: "cancelled"; exitCode: number | null }
  | { status: "spawn_failed"; message: string };

export interface LoginSpawnInput {
  harness: RuntimeHarness;
  argv: readonly [string, ...string[]];
  cwd: string;
  environment: { set: Readonly<Record<string, string>>; unset: readonly string[] };
  verification: "verified" | "unverified";
}

export interface LoginRecordView {
  harness: RuntimeHarness;
  startedAt: string;
  process: LoginProcessState;
  verification: "verified" | "unverified";
  /** Last `tailBytes` of raw PTY output, UTF-8 decoded. Affordance, never a verdict. */
  outputTail: string;
}

export const LOGIN_EXITED_CLOSE_CODE = "login-exited";

export class LoginSessions {
  constructor(options: { clock: Clock; ptyPort: PtyPort; tailBytes?: number; attachmentQueueSize?: number }) {
    throw new Error("not implemented");
  }
  /** Idempotent per harness: a running record is returned, a settled one replaced. */
  start(input: LoginSpawnInput): Promise<LoginRecordView> { throw new Error("not implemented"); }
  view(harness: RuntimeHarness): LoginRecordView | undefined { throw new Error("not implemented"); }
  /** Resolves when the process settles or timeoutMs lapses; serves the long poll. */
  settled(harness: RuntimeHarness, timeoutMs: number): Promise<LoginRecordView | undefined> {
    throw new Error("not implemented");
  }
  /** Replays the raw ring, then live output. Closing the attachment never kills the login. */
  attach(harness: RuntimeHarness, size: TerminalSize): AttachedTerminal | undefined {
    throw new Error("not implemented");
  }
  write(harness: RuntimeHarness, data: Uint8Array): void { throw new Error("not implemented"); }
  /** SIGTERM to the process group (-pid) so callback servers and browser launchers die with the login. */
  cancel(harness: RuntimeHarness): LoginRecordView | undefined { throw new Error("not implemented"); }
  closeAll(): Promise<void> { throw new Error("not implemented"); }
}
```

Built from what `PlainTerminalSessions` already proves: the shared `NodePtyAdapter` from `packages/gateway/src/main.ts::createDefaultRuntimeRouterDeps`, `runtime/service/BrowserPtyEnvironment.ts::browserPtyEnvironment(process.env, harness)` with the patch applied on top (so `PATH` survives; `runtime/adapters/NodePtyAdapter.ts::processEnvironment` treats a supplied env as complete), `runtime/service/TerminalFanout.ts` for the attachment, `PtySession.onExit` latching the exit fact. One raw ring buffer (64 KiB) serves both `outputTail` and late-attach replay, so no `TerminalEmulator` snapshot and no replay mode in the browser hook. `runtime/server/loginTerminalConnection.ts` mirrors `runtime/server/plainTerminalConnection.ts` (binary frames are stdin via `socketDataToBytes`, `parseTerminalResizeFrameText` resizes, `pumpAttachment` pumps) with one difference: the socket attaches to a record it did not create, so closing it detaches. Only `cancel` and gateway shutdown kill. `runtime/server/loginRoutes.ts` registers `POST/GET/DELETE /v1/logins/:harness`, `POST /v1/logins/:harness/input`, `WS /v1/logins/:harness/terminal`; `runtime/server/runtimeRouter.ts::RuntimeRouterDeps` gains `logins?: LoginSessions`; `main.ts` constructs it beside `plainTerminals` and adds it to `closeGatewayResources`.

Interface depth: seven methods hide the spawn, the per-harness idempotency map, the env patch, the fanout, the ring, the exit latch, the group kill, and the attach/detach asymmetry. The gateway never learns what a credential is.

### Frontend

`@tm/core`: `www/packages/core/src/types/launchReadiness.ts` gains `HarnessLoginAction` and `action` on the check; a new `types/harnessLogin.ts` holds `LoginView`; `transport.ts` gains `startHarnessLogin`, `readHarnessLogin(harness, waitMs)`, `cancelHarnessLogin`; `queryKeys.ts` gains `harnessLoginKey(harness)`.

```ts
// canvas/login/HarnessLoginCoordinator.tsx, mounted once in canvas/app.tsx::CanvasApp
export interface HarnessLogin {
  start(action: HarnessLoginAction): Promise<void>;   // POST, open or focus pane, watch until settled
  cancel(harness: HarnessName): Promise<void>;
}
export function HarnessLoginCoordinator({ children }: { children: ReactNode }): JSX.Element {
  throw new Error("not implemented");
}
export function useHarnessLogin(): HarnessLogin { throw new Error("not implemented"); }
```

The watcher loops `readHarnessLogin(harness, 30_000)` while `outcome === "running"`, writes each view into `harnessLoginKey`, and on settle invalidates `launchReadinessKey` and `harnessInventoryKey`. It lives in the coordinator, so a closed pane never strands the launcher.

`canvas/model/paneRecords.ts::PaneContentRef` gains `{ kind: "harness-login"; harness: HarnessName }`. `canvas/viewers/registry.tsx` registers a lazy `canvas/login/LoginPane.tsx` beside `TerminalPane` (xterm stays behind the lazy boundary). `canvas/infrastructure/runtime/terminalTransport.ts::TerminalEndpoint` gains `{ kind: "harness-login"; harness: HarnessName }` and `internal/terminalSocket.ts` gains `loginTerminalSocketUrl`. `canvas/viewers/terminal/terminalSession.ts::useTerminalSession` needs the endpoint kind only; the raw ring replays as ordinary output. `LoginPane` shows `display_command`, the outcome chip from `harnessLoginKey`, a Cancel button, and the terminal.

`canvas/firstrun/FirstRunScreen.tsx::CardView` is extracted to `canvas/firstrun/HarnessCard.tsx` first. `HarnessSection` passes the matching readiness check's `action` to the card; the card renders the button under the failing `authenticated` fact, disabled with the reason when `command_verification` is `unverified`. `canvas/launcher/commandTypes.ts::RowAction` gains `{ kind: "harness-login"; action: HarnessLoginAction }` with interaction `run-close`; `canvas/launcher/templateRows.ts` emits the row where `launchBlockedReason` names a credential check that carries an action; `canvas/launcher/useCommandCenter.ts::fire` dispatches to the coordinator.

### Deliberately not done

No URL regex, no text matching, no Python process table, no attempt history, no modal, no change to `POST /v1/runs`, `RunManager`, `cli/`, or `CaptureRpcClient`. TM writes nothing into a harness home. MCP tool wrapping is a follow-up.

## Synthesis decision

Judges split (claude base D, codex base B). The orchestrator adopted **D (opus)** because its verdict is a pure function of process evidence plus a fresh `_credential_check`, with the exit code as evidence only; B kept the outcome in a gateway state machine fed by a prepare/evaluate RPC back into Python, inverting the call graph and pulling a `CaptureRpcClient` refactor into the slice. Binding grafts, all applied above: harness-keyed identity with no ids on the wire (A, C); `output_tail` and late-attach replay instead of D's URL regex (A, C); B's app-scoped watcher driven by D's `wait_ms`; B's `{set, unset}` env patch over `browserPtyEnvironment(process.env)` with `unset` from the `probe_environment` policy (C) and never the backend environ; `command_verification` (B, C); `LaunchReadinessCheck.action` (B); `login_outcome` over private domain evidence with `lost` for a missing record and no tombstone; fleet-constant refactor first (D). Rejected: B's RPC, client-minted ids, eight-variant result and `starting`/`evaluating` states; A's nonzero-exit-means-failed rule and shared wire types in `packages/common`; C's stored `display`, `harness` on the spec, backend environ shipping, and separate status/readiness reads; D's regex, `LoginAttempt.home`, and `GatewayHttpTransport` rename; any modal. Orchestrator decisions: cancel kills the process group; HTTP only for the director this slice; grok `unverified` renders disabled with the reason; one live login per harness per gateway. Amendment 1 (human, 2026-08-27): `claude auth login` creates its own home, TM never `mkdir`s a harness home, and the fleet home moves to `default_storage_root() / "claude-auth"` behind `claude_fleet_auth_home(env)` with the `TRANSPORT_MATTERS_CLAUDE_AUTH_HOME` override.

## Tradeoffs accepted

- We accept a two-step start-then-attach in exchange for keeping argv off every client wire and giving the director a request/response it can call.
- We accept one raw ring buffer in the gateway in exchange for a director that can read the fallback URL and a reopened pane that sees it, with no parser and no emulator snapshot.
- We accept that Python holds no attempt state and re-reads the predicate on every request, in exchange for nothing to invalidate, migrate, or lose on restart. `lost` is the honest name for a missing record with an unready credential.
- We accept that closing the pane leaves the process running, in exchange for never cancelling an OAuth redirect mid-flight. `DELETE` is the explicit cancel and it takes the process group with it.
- We accept a watcher loop in the coordinator (one long poll every 30 s while running) in exchange for no push channel and no dependency on a socket staying open.
- We accept grok on the same driver, disabled until observed, in exchange for one occupancy map and no special case.
- We accept three preparatory refactors (fleet home resolver, WS bridge extraction, `CardView` extraction) in exchange for not landing new code into near-cap files.
- We accept that moving the fleet home invalidates any existing `~/.claude-auth` login, in exchange for per-channel fleet homes. `tm/credential_broker.py` derives the keychain service name from `sha256` of the config dir, so the old entry is simply never read again. No migration: private repo, no users.

## Alternatives considered

- **Browser passes `{argv, env}` on the attach socket** (scout option a). Smallest diff. Exposes process spawn on the widest surface TM has and makes the director learn argv assembly. Lost on interface depth in the wrong direction.
- **Gateway asks Python for the spec over a fourth `CapturePort` RPC** (option b, and B's prepare/evaluate). Keeps argv private but inverts the call graph, teaches the gateway the credential outcome, and grows `capture_rpc_routes.py`. Lost on ownership.
- **Verdict from the exit code.** Half the size and wrong on the two cases that matter: a closed browser tab exiting 0, a written credential exiting non-zero.
- **Socket-owned login cloned from `PlainTerminalSessions`.** Least new code. A viewer unmount kills Codex's callback server and a socketless director gets no verdict.
- **Ark `Dialog` hosting xterm.** No primitive exists, it blocks the canvas during a browser round trip, and it hides the readiness fact the user is fixing.
- **Persisting attempts in Postgres.** Nothing reads login history; a store adds a second writer to a verdict the predicate already owns.

## Open questions and risks

- Cancel escalation: after SIGTERM to the group, should the gateway send SIGKILL after a bounded grace, and which existing shutdown policy defines the period?
- `GET /v1/logins/{harness}` before any start returns `lost` when the credential is unavailable (the gateway cannot tell never-started from restarted). Is that acceptable for the director, or should the frontend alone treat `lost` before its own `POST` as idle?
- Codex binds `127.0.0.1:1455`; exclusive occupancy covers two TM logins and leaves an operator's own `codex login` in another terminal uncovered. Should `spawn_failed` carry a port-in-use hint?
- Is one live login per harness acceptable once a multi-operator gateway exists?
- Should `POST .../input` accept raw bytes as well as `{text}`? Widening later is a contract change.
- The gateway HTTP port has no authentication; safety rests on loopback binding and no bridged route carrying argv. Should the gateway's login routes also require the origin header the Python client sends?

## Next implementation step

Land slice 1: replace `CLAUDE_FLEET_AUTH_HOME` with `claude_fleet_auth_home(env)` over `default_storage_root`, declare `env_keys.CLAUDE_AUTH_HOME`, replace `login_command` with `LoginSpec` and `resolve_login_spec` in `tm/credential_source.py`, point `_WRITE_BACK_ERROR_MESSAGE` and inventory at `.display`, and add `tm/test_credential_source.py` pinning argv, home, verification, and display for all three harnesses.

## Slices

Each slice is one PR. The gate recipe is the full one; run it verbatim.

1. **Fleet home resolver and `LoginSpec`** (Python only, no behaviour change on the wire).
   Files: `tm/env_keys.py`, `tm/claude_fleet_auth.py`, `tm/credential_source.py`, `tm/credential_broker.py`, `tm/harnesses/inventory.py`, `api/conftest.py`, `tm/cli/test_diagnose.py`, `tm/cli/test_home_seed_credentials.py`, `tm/harnesses/test_inventory.py`, `tm/test_credential_broker.py`, new `tm/test_credential_source.py`, new `tm/test_claude_fleet_auth.py`.
   Tests: `claude_fleet_auth_home` default under each channel, env override, and per-channel distinctness; `resolve_login_spec` per harness and platform; `display` equals the string `_WRITE_BACK_ERROR_MESSAGE` and inventory render; no `CLAUDE_FLEET_AUTH_HOME` or `CLAUDE_FLEET_BOOTSTRAP_COMMAND` symbol remains.
   Gate: `just check`, `just test`.

2. **Readiness action and the unset policy.**
   Files: `tm/captured/readiness.py`, `tm/launch/environment.py` (`stripped_environment_keys`), `tm/harnesses/probes/runner.py`, `tm/captured/test_readiness.py`, `tm/api/v1/test_launch_readiness.py`, `www/packages/core/src/types/launchReadiness.ts`.
   Tests: `action` present only when the predicate fails; `probe_environment` output unchanged (existing tests) with the key policy shared; grok action is `unverified`.
   Gate: `just check`, `just test`.

3. **Gateway `LoginSessions`, routes, terminal connection.**
   Files: new `runtime/service/LoginSessions.ts`, `runtime/server/loginRoutes.ts`, `runtime/server/loginTerminalConnection.ts`, plus `runtime/server/runtimeRouter.ts`, `runtime/index.ts`, `packages/gateway/src/main.ts`, tests beside each on `runtime/testSupport/fakePty.ts::FakePtyPort`.
   Tests: idempotent start (running rejoined, settled replaced); env patch over `browserPtyEnvironment` keeps `PATH`; ring replays on late attach and bounds `outputTail`; detach does not kill; cancel signals the group; `settled` resolves on exit and on timeout; `closeAll` reaps.
   Gate: `pnpm --filter @tm/runtime test`, `pnpm --filter @tm/gateway test`, `just check`.

4. **Python routes, verdict, bridge.**
   Files: new `tm/api/v1/logins.py`, `tm/api/v1/gateway_logins.py`, `tm/api/v1/test_logins.py`; `tm/api/v1/terminal_bridge.py` and `tm/api/v1/run_proxy.py` (bridge extraction, then `WS /api/logins/{harness}/terminal`); `tm/api/v1/test_run_proxy.py`, `tm/api/v1/test_terminal_bridge.py`; router registration where `launch_readiness.py` is mounted.
   Tests: `login_outcome` truth table including `ProcessMissing`; routes never forward client argv; unknown harness 404; `wait_ms` clamp; existing proxy tests unchanged after the extraction.
   Gate: `just check`, `just test`.

5. **`CardView` extraction** (mechanical, frontend only).
   Files: `canvas/firstrun/FirstRunScreen.tsx`, new `canvas/firstrun/HarnessCard.tsx`, `canvas/firstrun/FirstRunScreen.test.tsx`.
   Tests: existing first-run suite green, no behaviour change.
   Gate: `pnpm --filter @tm/shell test`, `just check`.

6. **Frontend driver: core transport, coordinator, pane, card button, palette row.**
   Files: `www/packages/core/src/transport.ts`, `queryKeys.ts`, new `types/harnessLogin.ts`, `index.ts`; new `canvas/login/HarnessLoginCoordinator.tsx`, `canvas/login/LoginPane.tsx`; `canvas/app.tsx`, `canvas/model/paneRecords.ts`, `canvas/viewers/registry.tsx`, `canvas/infrastructure/runtime/terminalTransport.ts`, `canvas/infrastructure/runtime/internal/terminalSocket.ts`, `canvas/viewers/terminal/terminalSession.ts`, `canvas/firstrun/HarnessCard.tsx`, `canvas/firstrun/harnessCards.ts` (drop `authenticationCommand`), `canvas/launcher/commandTypes.ts`, `commandRows.ts`, `templateRows.ts`, `useCommandCenter.ts`; then `tm/harnesses/inventory.py` drops `authentication_command`.
   Tests: coordinator invalidates both keys on settle with the pane closed (persist-then-settle, asserting the card re-renders); pane ref round-trips through `paneRecords.contract.test.ts`; palette row fires the coordinator and closes; unverified action renders disabled with reason; endpoint URL builder.
   Gate: `pnpm --filter @tm/shell test`, `just check`, `just test`.
