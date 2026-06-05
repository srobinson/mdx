---
title: "Transport Matters Arena (opus): the login driver"
type: design
tags: [transport-matters, login-driver, credential, pty, gateway, arena]
summary: A login is an attempt on a credential predicate. TM starts it server-side, the gateway owns the process and never takes argv from a client, and the verdict is the predicate re-read after exit, never the exit code and never the text.
status: draft
source: architect arena Phase B, runner claude-opus
created: 2026-08-27
---

## Problem

`GET /v1/launch-readiness` reports `*_credential_unavailable` and offers prose: run this command
yourself. NOW.md 1.3 says TM runs any command TM can run. The harnesses own their login flows, so
the work is **driving someone else's interactive process from two clients at once** (the ⌘K palette
and the director agent) and then deciding, honestly, whether it worked. Four Phase A constraints
make the shape non-obvious.

- The knowledge is split and stays split: `credential_source.py::_CREDENTIAL_PROFILES` plus
  `launch/environment.py::HOME_DIR_ENV_BY_HARNESS` own command and home, and only the gateway owns
  a PTY (`ports.ts::PtyPort`, `service/PlainTerminalSessions.ts`).
- The browser reaches the gateway only through `api/v1/run_proxy.py::RunRouteProxy`. Whatever the
  browser can put on that wire, the gateway will execute.
- The predicate that decides success (`captured/readiness.py::_credential_check`) is Python's, and
  reads a home `resolve_native_harness_home` takes from ambient env.
- API-first: a director with no terminal must still complete a paste-code login, so the
  verification URL and stdin are control-plane data, not pixels.

The load-bearing sentence: **the process exit is a trigger, the credential predicate is the
verdict.** `claude auth login` can exit 0 after the user closes the browser tab, and can exit
non-zero after writing a perfectly good credential. Every type below is arranged so no code can
mistake one for the other.

## Usage (caller's view)

**The director (MCP, one call does the whole thing).**

```python
attempt = await login(harness="claude", wait_ms=120_000)
# LoginAttempt(outcome="running", verification_url="https://claude.ai/oauth/authorize?...",
#              display_command="CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login", ...)
await login_input(attempt.attempt_id, text="A1B2-C3D4")     # paste-code prompts
final = await login(harness="claude", wait_ms=120_000)       # idempotent: rejoins, does not respawn
# LoginAttempt(outcome="authenticated", credential=LaunchReadinessCheck(ready=True, ...))
```

Same surface over HTTP: `POST /v1/logins {harness}`, `GET /v1/logins/{id}?wait_ms=`,
`POST /v1/logins/{id}/input {text}`, `DELETE /v1/logins/{id}`.

**First run (the terminal is the expanded state of the readiness card, not a destination).**

```tsx
const { attempt, start, cancel } = useLoginAttempt(card.harnessId);
// inside HarnessCard, directly under the failing "Authenticated" fact:
{attempt === null
  ? <button onClick={() => void start()}>Sign in to {card.title}</button>
  : <LoginTerminal attempt={attempt} onCancel={cancel} />}
```

`LoginTerminal` renders the PTY and a copyable `attempt.verificationUrl` above it. On socket close
the hook re-reads `GET /v1/logins/{id}` once for the verdict, then invalidates `launchReadinessKey`
and `harnessInventoryKey`. The card re-renders green. There is no modal.

**The palette** opens the same component in a pane: `{ kind: "login", harness: "codex" }`. The ref
carries the harness and no attempt id, so a restored pane calls `start()` and idempotency rejoins
the live attempt or opens a fresh one.

**The gateway** is called by Python only, never by a client:

```ts
const facts = await loginSessions.start({
  harness: "claude",                      // opaque tag; the gateway never branches on it
  homeKey: "/Users/x/.claude-auth",       // identity of the attempt
  argv: ["claude", "auth", "login"],
  env: { CLAUDE_CONFIG_DIR: "/Users/x/.claude-auth" },
});
```

## Shape

### The identity of an attempt is the home it writes to

Two `claude auth login` processes against one home are two writers on the operator's credential
store, so "what happens if it runs twice" cannot be "nothing". `LoginSessions` keys its live index
by `homeKey` and `start` is idempotent against it: a **running** attempt for that home is returned
unchanged, an **exited** record is replaced. Live blocks, exited yields. That is also the whole
reaping policy, since the map then holds at most one record per home (three exist): bounded by
construction, no TTL, no sweeper, per make-operations-idempotent and
separate-before-serializing-shared-state. Lookup by `attemptId` scans that map; at three entries a
second index costs more than it saves.

### Argv never crosses a client boundary

The browser sends `{harness}` to Python; Python resolves argv and env from the credential seam and
calls the gateway over the existing private HTTP path. The bridge in `run_proxy.py` gains exactly
one route, the attach WebSocket, carrying an attempt id and a terminal size and nothing executable.
Handing argv to the gateway from the browser query string (the scout's option (a)) would turn a
same-origin socket into arbitrary local process execution; the plain terminal's fixed `$SHELL` is
not the same exposure. A fourth `CapturePort` RPC (option (b)) inverts the call graph: the gateway
would ask Python for facts to serve a caller who already came from Python. **Recorded deviation
from the Reuse Map's recommendation of (a), on that reason.**

### Python, `credential_source.py` (the shell string is replaced, not doubled)

```python
@dataclass(frozen=True, slots=True)
class LoginCommand:
    """The harness's own login rendered as something spawnable, and its prose."""
    harness: str
    argv: tuple[str, ...]
    home_env: tuple[str, str]       # (CLAUDE_CONFIG_DIR, /Users/x/.claude-auth), always set
    @property
    def display(self) -> str:
        """`codex login`; the env prefix appears only when home is not the native default."""
        raise NotImplementedError

def resolve_login_command(source: CredentialSource) -> LoginCommand:
    """Derive argv + home from the resolved source. The one owner of both."""
    raise NotImplementedError
```

`_CredentialProfile.login_command: str` becomes `login_argv: tuple[str, ...]`; every prose site
(`_native_credential_failure`, `_keychain_credential_failure`,
`inventory.py::build_harness_inventory.authentication_command`) reads `.display`. `home_env` always
carries the home the predicate itself resolved, closing a real hole: a login writing `~/.codex`
while the predicate reads a `CODEX_HOME` from the operator's shell reports failure after
succeeding.

This dissolves the recorded duplicate at its root rather than papering it. `CLAUDE_FLEET_AUTH_HOME`
moves to `launch/environment.py` (which imports neither `credential_broker` nor
`claude_fleet_auth`, so no cycle); `CLAUDE_FLEET_BOOTSTRAP_COMMAND` stops being declared and
becomes `resolve_login_command(claude_keychain_credential_source()).display`;
`credential_broker.py::_WRITE_BACK_ERROR_MESSAGE` composes that same value. Refactor lands first,
before the driver.

### Python, `api/v1/logins.py` (the verdict)

```python
class LoginOutcome(StrEnum):
    RUNNING = "running"; AUTHENTICATED = "authenticated"
    UNAUTHENTICATED = "unauthenticated"; SPAWN_FAILED = "spawn_failed"; CANCELLED = "cancelled"

class LoginAttempt(BaseModel):
    """What both clients read. No exit code appears on the verdict, only as evidence."""
    model_config = ConfigDict(frozen=True)
    attempt_id: str
    harness_id: HarnessId
    home: str
    display_command: str
    outcome: LoginOutcome
    verification_url: str | None     # affordance only; nothing branches on it
    credential: LaunchReadinessCheck # freshly evaluated by _credential_check, not cached
    exit_code: int | None
    detail: str

def login_outcome(process: GatewayLoginProcess, credential: LaunchReadinessCheck) -> LoginOutcome:
    """Pure. The predicate decides; the exit only says a decision may now be made."""
    raise NotImplementedError
```

All four routes return the same `LoginAttempt` with a freshly evaluated `credential`, so a caller
can never hold a stale verdict and never needs a second request to learn what changed. Python
stores **nothing**: the gateway echoes back the harness tag it was given, and the predicate is
re-read per request. Restart-safe by having no state to lose, per
single-source-of-truth-per-invariant.

`login_outcome` is the only place the two facts meet, and it is pure, per boundary-discipline: the
route is the shell, the decision is a function with two arguments and a test file.

### Gateway, `packages/runtime/src/service/LoginSessions.ts`

```ts
export type LoginProcessState =
  | { status: "running" }
  | { status: "exited"; exitCode: number | null; signal: number | null }
  | { status: "spawn_failed"; message: string }
  | { status: "cancelled" };

export interface LoginAttemptFacts {
  attemptId: string; harness: string; homeKey: string; startedAt: string;
  process: LoginProcessState;
  /** First https:// URL in the opening output. An affordance; never a completion signal. */
  verificationUrl: string | null;
}

export class LoginSessions {
  /** Idempotent per homeKey: a live attempt is rejoined, an exited one replaced. */
  start(input: LoginSpawnInput): Promise<LoginAttemptFacts>;
  facts(attemptId: string): LoginAttemptFacts | undefined;
  /** Resolves when the process settles or the timeout lapses; serves the long poll. */
  settled(attemptId: string, timeoutMs: number): Promise<LoginAttemptFacts | undefined>;
  attach(attemptId: string, size: TerminalSize): AttachedTerminal | undefined;
  write(attemptId: string, data: Uint8Array): void;
  cancel(attemptId: string): LoginAttemptFacts | undefined;
  closeAll(): Promise<void>;
}
```

Built from the pieces `PlainTerminalSessions` already proves: the shared `NodePtyAdapter` from
`main.ts::createDefaultRuntimeRouterDeps`, `browserPtyEnvironment` over the supplied env,
`TerminalFanout` for the attachment, `session.onExit` latching the exit fact.
`server/loginTerminalConnection.ts` mirrors `plainTerminalConnection.ts` (binary frames are stdin,
one text frame kind resizes) with one difference: the socket **attaches** to an attempt it did not
create, so closing the socket does not kill the login. A closed tab must not cancel an OAuth
redirect the user is mid-way through; only `DELETE` and gateway shutdown cancel. `LoginSessions`
joins `closeGatewayResources`.

Interface depth: seven methods hide the spawn, the per-home idempotency index, the fanout, the
exit latch, the bounded URL scan, and the attach/detach asymmetry. Nothing about PTYs reaches
Python or the browser, and no gateway wire type is re-exported past `api/v1/logins.py`.

### Text may buy affordances, never verdicts

`Never match on "Login successful."` is a rule about **verdicts**, and it holds absolutely. The URL
scan is the opposite case: if the regex misses, the URL is still on screen and the flow still
works, so the failure mode is degradation rather than a lie. It is also not optional, because a
director that cannot read the URL cannot log in at all. The types keep the two apart:
`verificationUrl` is nullable, `login_outcome` does not take it, and the scan is bounded to the
first 64 KiB and the first match.

### Module map

| File | Change |
|---|---|
| `launch/environment.py` | receives `CLAUDE_FLEET_AUTH_HOME` (breaks the constant cycle) |
| `credential_source.py` (253) | `LoginCommand`, `resolve_login_command`, `login_argv` replaces `login_command` |
| `claude_fleet_auth.py`, `credential_broker.py` (668) | `CLAUDE_FLEET_BOOTSTRAP_COMMAND` and `_WRITE_BACK_ERROR_MESSAGE` compose the derived display |
| `api/v1/logins.py` **new** (~180) | four routes, `LoginAttempt`, `login_outcome` |
| `api/v1/gateway_logins.py` **new** (~110) | typed gateway client on the existing `GatewayRunTransport` Protocol, renamed `GatewayHttpTransport` |
| `api/v1/terminal_bridge.py`, `api/v1/run_proxy.py` (628) | extract `_forward_ws`/`_bridge_websockets`/`_close_*` first, then one route: `WS /api/logins/{id}` |
| `api/v1/controlplane_mcp.py` | tools `login`, `login_input` |
| `runtime/src/service/LoginSessions.ts` **new** (~200) | above |
| `runtime/src/server/loginTerminalConnection.ts` **new** (~90) | attach pump |
| `runtime/src/server/runtimeRouter.ts`, `gateway/src/main.ts` | `logins?` dep, `registerLoginRoutes`, construct, join `closeGatewayResources` |
| `canvas/src/login/` **new** | `LoginTerminal.tsx`, `useLoginAttempt.ts`; a leaf both firstrun and the pane import |
| `canvas/src/firstrun/HarnessCard.tsx` **new** | `CardView` extracted out of `FirstRunScreen.tsx` (623) first, then the action |
| `terminalTransport.ts`, `internal/terminalSocket.ts` | `{kind:"login"; attemptId}` endpoint + URL builder |
| `paneRecords.ts`, `viewers/registry.tsx`, `commandTypes.ts` | login pane ref behind the lazy xterm boundary; `{kind:"login"; harness}` command |

The scout's `FirstRunScreen.tsx::HarnessCardItem` does not exist under that name; the symbol to
extract is `CardView`.

## Synthesis decision

## Tradeoffs accepted

- We accept a two-step start-then-attach (instead of one create-on-connect socket like
  `/v1/terminal`) in exchange for keeping argv off every client wire and giving the director a
  plain request/response it can actually call.
- We accept one text scan in the gateway in exchange for a director that can complete a browser
  login; the scan is quarantined from every verdict by type.
- We accept that Python holds no attempt state and re-reads the predicate on every request, in
  exchange for having nothing to invalidate, migrate, or lose on restart. The predicate is a
  `stat` or a keychain read, not a launch.
- We accept that closing the login pane leaves the process running, in exchange for never
  cancelling an OAuth redirect the user is mid-way through. `DELETE` is the explicit cancel.
- We accept refactoring `run_proxy.py`, `FirstRunScreen.tsx` and the fleet constant before any
  driver code, in exchange for not landing new code into three near-cap files.

## Alternatives considered

- **Browser passes `{argv, env}` on the attach socket** (Reuse Map option (a)). Smallest diff, one
  round trip. Lost on interface depth in the wrong direction: it exposes the gateway's most
  dangerous internal (process spawn) on the widest surface TM has, and the director would have to
  learn argv assembly to use it.
- **A fourth `CapturePort` RPC so the gateway asks Python for the spec** (option (b)). Keeps argv
  private, but inverts the call graph so the gateway calls back into the origin that called it, and
  it grows `capture_rpc_routes.py` (670) with a method that has nothing to do with capture.
- **Verdict from the exit code** (the text rule satisfied). Half the size, wrong on the two cases
  that matter: a cancelled browser tab exiting 0, a written credential exiting non-zero.
- **An Ark `Dialog` hosting the terminal.** Rejected on experience before cost: a modal hides the
  readiness fact the user is trying to fix. Inline expansion of the card keeps cause and cure on
  one screen, and needs no new primitive.
- **Persisting attempts in Postgres** so history survives restart. Rejected as premature: nothing
  reads login history, and a store adds a second writer to a verdict the predicate already owns.

## Open questions and risks

- Does `grok login` exist? `_CREDENTIAL_PROFILES` asserts it and nothing has verified it. The
  design carries no per-harness flag: an unknown subcommand exits non-zero, the predicate still
  fails, the PTY shows why. Acceptable degradation, or should Grok withhold the action until
  someone runs the binary?
- The macOS Claude login writes to `~/.claude-auth`, and `fleet_home_unavailable_reason` fails when
  that directory is absent. Should `POST /v1/logins` create it (TM writing into a harness home,
  against "read-only to us"), or return `spawn_failed` with the `mkdir` in its detail?
- `claude auth login` may open a browser as a child process. Killing the PTY on `DELETE` will not
  reap it. Is an orphaned browser tab acceptable, or does cancel need a process group kill?
- Should `POST /v1/logins/{id}/input` accept raw bytes as well as `{text}`? Codex's paste flow is
  text; a future harness may want control characters, and widening later is a contract change.
- The gateway's HTTP port has no authentication of its own; this design's safety rests on it being
  loopback-bound and on no bridged route carrying argv. Should the gateway's `POST /v1/logins` also
  require the origin header the Python client sends?

## Next implementation step

Land the refactor commit first: move `CLAUDE_FLEET_AUTH_HOME` into `launch/environment.py`,
replace `_CredentialProfile.login_command` with `login_argv`, and add `LoginCommand` +
`resolve_login_command` with a new `test_credential_source.py` asserting that
`resolve_login_command(claude_keychain_credential_source()).display` is the exact string
`credential_broker.py` and `inventory.py` both now compose.
