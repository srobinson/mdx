# TM Startup Readiness — mechanical design (rev 2)

Revision incorporating all six conditions from `tm-startup-design-review.md`. Baseline
`ml/next` at `841e385b`. Inputs: both scout reports, `docs/ARCHITECTURE.md`, `NOW.md`,
`NORTHSTAR.md`. Every symbol named below was verified against the tree, including every
symbol the review introduced.

The acceptance bar: a builder implements this without making a design decision. Sections 2
to 6 are the interfaces in full; section 7 the move list; section 8 the slices; section 9
the hazard register; section 10 every settled question. Zero open questions.

Changes from rev 1, by review condition: (1) `checking` overall status, exact derivation
order, unknown-renders-as-checking; (2) owned `ProbeContext` factory with temp-pool
lifecycle, evidence-store construction, paged Workdir ruling, coalesced recheck groups with
an invocation-count test; (3) the real intent-terminal path — `TerminalEndpoint`, viewer
registry, pane identity owners, persistence exclusions, one-shot `onClose` latch; (4) S6
deleted (no ambient env sentinel), S5 depends on S2; (5) exact remedy catalog, Grok
excluded, item-level timestamps with newest-non-null aggregation, sanitized probe-failure
summaries, Python prefix owner, status-line remedy rule; (6) four additional real-boundary
proofs.

## 1. Decisions

### D-OWN. Ownership: a Python readiness package, not a Runtime module

`api/src/transport_matters/readiness/` — a policy composition package on the capture plane,
NOT a bounded context and NOT part of `packages/runtime`. (Survived adversarial review.)

1. **Doctor is a cold-start client.** `cli/diagnose.py:run_doctor` must rule with no
   server, gateway, or browser alive. A Runtime-owned registry is unreachable in exactly
   the states it diagnoses.
2. **Every probe already lives in Python.** `session_store_preflight.py:check_session_store`,
   `capabilities.py:detect_harnesses`, `harnesses/probes/runner.py:run_authentication_probe`,
   `harnesses/inventory.py:harness_inventory`, `harnesses/compatibility.py:compare_versions`.
3. **Director parity is free.** One method on
   `api/v1/controlplane_mcp.py:_McpControlPlaneAdapter` exposes the projection over MCP.
4. **ARCHITECTURE.md ruling.** "New product contexts do not extend the capture plane"
   governs bounded contexts; readiness owns no domain, events, or projections — it is the
   same species as `gateway_supervisor.py`. The serving-root rule ("the Gateway owns no
   domain") and the two-plane rule ("Python ... owns the Postgres session store") bind the
   other direction.

Runtime keeps the terminal seam (`PlainTerminalSessions`), extended by one additive input
(§5). The intent catalog stays Python; the gateway resolves opaque intent ids over the
existing capture RPC direction, the same crossing `prepareCapture` uses.

### D-XS. XState: no

(Survived review.) The registry evaluation is a pure ordered fold; the login-wait flow is
one recheck on the pane's one-shot close callback (§5d) plus a manual "Check again" button.
`runActivityMachine` earns its machine interpreting interleaved streams; nothing here
interleaves.

### D-SCOPE. What this design does and does not consolidate

In scope: the registry as the single verdict authority plus five clients — doctor, HTTP,
MCP, canvas gate, desktop failure modal.

Out of scope, deliberately:
- **Gateway process consolidation** (process scout slices 5–7). Reserved gate id
  `gateway_process` (not in the v1 registry); `gateway_supervisor.py` untouched. (Reviewer
  concurred the deferral is separable.)
- **The duplicated second migration pass.** Rev 1's S6 is DELETED per review condition 4:
  its env-var sentinel was an ambient, user-settable, URL-unbound cross-process protocol
  that leaks into the mitmdump child (`cli/launch_runtime.py:preflight_session_store_or_exit`
  runs in the parent; `captured_run.py:run_captured_run_on_local_tty` →
  `addon_runtime.py:load_runtime` starts the embedded server in the child). The existing
  advisory-locked, normally-no-op second pass in `main.py:_start_session_store` stays. A
  later consolidation design may specify a URL-bound, launcher-minted protocol with its own
  cross-process proof; not this one.
- The DB hard gate stays hard; `COMPATIBILITY_ROLLOUT` stays advisory; no keychain read or
  write anywhere; the parked no-DB/store-picker NOW item is untouched (it lands inside this
  seam later by relaxing the preflight, changing no contract).

## 2. The contract

### 2a. Python models — `api/src/transport_matters/readiness/models.py` (new)

Frozen pydantic v2 (`model_config = ConfigDict(frozen=True)`), builtins-only types. Exact
fields:

```python
GATE_STATUSES = ("ok", "needs_setup", "error", "unknown")
type GateStatus = Literal["ok", "needs_setup", "error", "unknown"]

GATE_POLICIES = ("hard", "advisory")
type GatePolicy = Literal["hard", "advisory"]

OVERALL_STATUSES = ("ready", "checking", "needs_setup", "blocked")
type OverallStatus = Literal["ready", "checking", "needs_setup", "blocked"]

GATE_IDS = ("session_store", "harness_install", "harness_version", "harness_auth",
            "workspace_inventory")
type GateId = Literal[...same five...]

STARTUP_STATUS_LINE_PREFIX = "TM_READINESS_V1 "   # THE Python owner of the literal

class CommandRemedy(BaseModel):
    kind: Literal["command"] = "command"
    command: str                  # exactly one executable command line

class TerminalRemedy(BaseModel):
    kind: Literal["terminal"] = "terminal"
    intent: str
    label: str

class UiRemedy(BaseModel):
    kind: Literal["ui"] = "ui"
    scope: Literal["workdir"]
    label: str

type Remedy = CommandRemedy | TerminalRemedy | UiRemedy   # discriminated on "kind"

class GateItem(BaseModel):
    item_id: str                  # harness id for harness gates; "" for singleton gates
    status: GateStatus
    summary: str
    detail: str | None = None
    remedy: Remedy | None = None
    observed_at: str | None = None   # ISO 8601; None = no stored evidence for this item

class GateResult(BaseModel):
    gate_id: GateId
    policy: GatePolicy
    status: GateStatus            # worst-of items: error > needs_setup > unknown > ok
    items: tuple[GateItem, ...]
    observed_at: str | None       # newest non-null item observed_at (via datetime.fromisoformat max); None if all None
    evidence: Literal["live", "stored"]

class ReadinessReport(BaseModel):
    generated_at: str
    overall: OverallStatus
    gates: tuple[GateResult, ...] # registry order, always all five
```

`derive_overall` (pure, `models.py`), exact order:
1. `blocked` — any gate with `policy == "hard"` and `status == "error"`.
2. `needs_setup` — any remaining gate with `status in ("needs_setup", "error")`.
3. `checking` — any gate with `status == "unknown"`.
4. `ready`.

An unobserved installation can never present as `ready` (review condition 1: fail-open
defect). Truth-table test includes the unknown-only case → `checking`, and the trap case
advisory-error → `needs_setup`, never `blocked`.

### 2b. Wire mirror — `packages/contract/src/readiness/` (new subpath `@tm/contract/readiness`)

House pattern of `packages/contract/src/space/` (wire.ts + index.ts + fixtures.ts +
testing.ts subpath, zero runtime deps, no root barrel):

- `wire.ts`: the four `as const` vocab arrays (including `"checking"`), all DTO types
  mirroring 2a field-for-field in snake_case (`gate_id`, `item_id`, `observed_at`,
  `generated_at`), `STARTUP_STATUS_LINE_PREFIX = "TM_READINESS_V1 "` (mirror of the Python
  owner; conformance below), and
  `type StartupStatusLine = { gate_id: string; summary: string; remedy_command: string | null }`.
- `fixtures.ts` + `testing.ts`: canonical sample objects, including one report whose only
  non-ok gates are `unknown` (the `checking` fixture, per condition 1).

**Conformance:** canonical sample JSON at
`packages/contract/src/readiness/fixtures/report.sample.json` (plus
`report.checking.sample.json`). TS test `packages/contract/src/readiness/readiness.test.ts`
parses both against the wire types and asserts vocab coverage including `checking`. Python
test `api/src/transport_matters/readiness/test_contract_fixture.py` loads the same files by
repo-relative path, asserts `ReadinessReport.model_validate` round-trips them, and asserts
`GATE_STATUSES`/`GATE_IDS`/`OVERALL_STATUSES` equal the fixtures' declared vocabulary. The
Python test also asserts the emitted status-line prefix equals the TS constant's value as
recorded in a `prefix` field inside `report.sample.json` — one fixture, both planes fail
closed on drift.

## 3. The registry

### 3a. Probe context — `api/src/transport_matters/readiness/context.py` (new)

The owned cold-start/warm-start lifecycle (review condition 2):

```python
@dataclass(frozen=True, slots=True)
class ProbeContext:
    session_pool: AsyncConnectionPool[AsyncConnection[DictRow]] | None
    database_url: str | None      # feeds ExecutorEvidenceStore / harness_inventory
    store_error: str | None       # preflight error text when no pool could be opened
    now: Callable[[], datetime]

@asynccontextmanager
async def open_probe_context(
    app_pool: AsyncConnectionPool[AsyncConnection[DictRow]] | None = None,
    *,
    now: Callable[[], datetime] | None = None,
) -> AsyncIterator[ProbeContext]:
```

Behavior, exactly:
- `now` defaults to `lambda: datetime.now(UTC)`.
- `app_pool is not None` (HTTP/MCP path): resolve `database_url` via
  `config.resolve_session_store_url(get_settings())`; yield
  `ProbeContext(app_pool, url, None, now)`. NEVER closes the app pool.
- `app_pool is None` (doctor path): run
  `session_store_preflight.py:check_session_store()` (read-only, 5 s timeout; it reads the
  same process-cached `get_settings()` — `ProbeContext` deliberately carries no settings
  field). Non-`None` error → yield `ProbeContext(None, None, error, now)`; DB-backed gates
  go `unknown`, `session_store` goes `error`. `None` → resolve `database_url`
  (`MissingDatabaseConfigError` cannot occur here; `check_session_store` already proved
  config), open a temporary pool via `session/pool.py:create_async_pool(database_url)`,
  yield `ProbeContext(temp_pool, url, None, now)`, and `await temp_pool.close()` in the
  `finally`.

Store construction inside gates (no other construction sites):
- Inventory read: `harness_inventory(ctx.session_pool, database_url=ctx.database_url or "", now=ctx.now)`
  (it constructs its own `ExecutorEvidenceStore` internally — `inventory.py:360`).
- Recheck evidence writer:
  `connections_store.py:ExecutorEvidenceStore(ctx.database_url or "", ctx.session_pool)` —
  identical to `main.py:262`.
- Space reads: `async with ctx.session_pool.connection() as conn:` →
  `space/service.py:SpaceCrudService(conn)`.

### 3b. Registry — `api/src/transport_matters/readiness/registry.py` (new)

```python
class GateProbe(Protocol):
    async def __call__(self, ctx: ProbeContext) -> tuple[GateItem, ...]: ...

type RecheckGroup = Literal["harness_full", "harness_auth"]

class GateDescriptor:             # frozen dataclass
    gate_id: GateId
    policy: GatePolicy
    probe: GateProbe
    recheck_group: RecheckGroup | None   # None = probe is already live

READINESS_GATES: tuple[GateDescriptor, ...]   # the single-sourced ordered registry

async def evaluate_readiness(ctx: ProbeContext,
                             gates: tuple[GateDescriptor, ...] = READINESS_GATES,
                             ) -> ReadinessReport
async def recheck_gates(ctx: ProbeContext, gate_ids: tuple[GateId, ...]) -> ReadinessReport
```

`evaluate_readiness` runs probes sequentially in registry order and never raises: a probe
exception is `logger.exception`-logged and becomes
`GateItem(item_id="", status="error", summary=PROBE_FAILURE_SUMMARIES[gate_id], detail=None)`
— `readiness/gates.py:PROBE_FAILURE_SUMMARIES: dict[GateId, str]` holds five fixed
literals (`"session store check failed; see server log"`,
`"harness inventory read failed; see server log"` for the three harness gates,
`"workspace inventory read failed; see server log"`). No exception text ever enters the
report (review condition 5).

**Recheck coalescing** (review condition 2): `recheck_gates` collapses the requested gates'
`recheck_group` values into a set, then:
- set contains `harness_full` → run `state_refresh.py:refresh_harness_state(evidence)`
  exactly once (a full pass already covers install, version, models, AND auth); do NOT also
  run the auth-only refresh.
- set is exactly `{harness_auth}` → run `state_refresh.py:refresh_authentication(evidence)`
  (new public, §3d) exactly once.
- gates with `recheck_group None` (`session_store`, `workspace_inventory`) contribute
  nothing (their probes are live).
Then re-evaluate all gates and return the fresh report. **Invocation-count test:** request
`("harness_install","harness_version","harness_auth")` → exactly one
`refresh_harness_state` call and zero `refresh_authentication`; request
`("harness_auth",)` → zero and one.

### 3c. The five descriptors

`readiness/gates.py` additionally owns:
```python
READINESS_HARNESSES = ("claude", "codex")   # launch-eligible only; Grok excluded (§10 Q13)
_LOCAL_OWNER = "local"                      # mirrors cli/space_bootstrap.py:bootstrap_cli_space's owner default
INSTALL_COMMANDS = {
    "claude": "npm install -g @anthropic-ai/claude-code",
    "codex":  "npm install -g @openai/codex",
}
```

| gate_id | policy | recheck_group | probe (composition only) |
| --- | --- | --- | --- |
| `session_store` | `hard` | None | `ctx.session_pool is not None` → ok, summary `"session store reachable"`, `observed_at=ctx.now().isoformat()`. Else (`ctx.store_error` set) → `error`, summary `"session store unavailable"`, `detail = ctx.store_error + "\n\n" + session_store_setup_help()`, remedy `None` (the help is multiline alternatives prose, not one command — condition 5). `evidence="live"` |
| `harness_install` | `advisory` | `harness_full` | `harness_inventory(...)` filtered to `READINESS_HARNESSES`; per item: `installation.confirmed_installed` → ok, summary `f"{harness} {raw_version or 'version unknown'}"`; observed-not-installed → `needs_setup`, remedy `CommandRemedy(INSTALL_COMMANDS[harness])`; never observed → `unknown`, summary `"not yet observed"`. `observed_at` from the installation row's stored timestamp; `evidence="stored"`. Pool `None` → one `unknown` item per harness, summary `"session store unavailable — no harness evidence"` |
| `harness_version` | `advisory` | `harness_full` | same read; per item: `compatibility.minimum_version is None` or `installation.normalized_version is None` → `unknown`; `compare_versions(normalized, minimum) < 0` → `needs_setup`, summary `f"v{raw} below supported minimum v{minimum}"`, remedy `CommandRemedy(INSTALL_COMMANDS[harness])` (the install command is the update command); else ok |
| `harness_auth` | `advisory` | `harness_auth` | same read; per native connection: `authentication_status == "authenticated"` → ok; `"login_required"`/`"expired"` → `needs_setup`, remedy `TerminalRemedy(intent=intent_for_connection(harness), label=f"Log in to {harness label}")` where labels are `"Claude Code"`/`"Codex"` from the existing descriptor labels; `None`/`"unknown"` → `unknown`. `observed_at` from the access observation row |
| `workspace_inventory` | `advisory` | None | pool `None` → single `unknown` item. Else `SpaceCrudService.count_spaces(owner=_LOCAL_OWNER)`; `0` → `needs_setup`. Else page `list_spaces(owner=_LOCAL_OWNER, limit=50, offset=k*50)` for `k` in `0..ceil(count/50)-1`, stopping early when any `SpaceSnapshot` has a non-empty worktree list; none found across ALL pages → `needs_setup` (a one-page read can misclassify an older populated Space — condition 2); else ok. `needs_setup` item: summary `"No Workdir yet — agents need one to launch into"`, remedy `UiRemedy(scope="workdir", label="Create your first Workdir")`. `evidence="live"`, `observed_at=ctx.now().isoformat()` |

### 3d. `state_refresh.py` changes (replaces rev 1's raw promotion)

1. Extract the per-connection auth tail of `_refresh_harness` (the
   `AUTHENTICATION_PROBES.get` + connection loop calling `_refresh_connection_access`)
   into private `_probe_connections_access(harness_id, *, evidence, connections, binary,
   release_id, harness_version, env, now, probe)`; `_refresh_harness` calls it — behavior
   byte-identical.
2. New public:
```python
async def refresh_authentication(
    evidence: EvidenceWriter,
    *,
    harness_ids: tuple[HarnessId, ...] | None = None,   # None = registered_harness_ids()
    executor_id: str | None = None,
    env: Mapping[str, str] = os.environ,
    now: Callable[[], datetime] | None = None,
    probe: ProbeRunner = run_authentication_probe,
) -> None
```
Body mirrors `_refresh_harness` MINUS `reconcile_native_connection` (connections are read
via `evidence.list_connections(executor_id=..., harness_id=...)`, never mutated) and MINUS
`_refresh_target_snapshot` (no model enumeration): detect via
`asyncio.to_thread(detect_harnesses)`, build and upsert the harness observation exactly as
`_refresh_harness` does (auth recheck legitimately refreshes install/version evidence too),
skip harnesses failing the same installed/versioned/embedded-entry guard, then
`_probe_connections_access` with the same per-connection try/except logging. Rev 1's
"promote `_refresh_connection_access`" is superseded and dropped.

## 4. Read and recheck surfaces

### 4a. HTTP — `api/src/transport_matters/api/v1/readiness_routes.py` (new)

Mounted in `api/v1/router.py`: `api_router.include_router(readiness_routes.router,
tags=["readiness"])` beside the `capabilities` include (final paths `/api/readiness`,
`/api/readiness/recheck`).

- `GET /readiness` → `async with open_probe_context(getattr(request.app.state,
  "session_pool", None)) as ctx: return await evaluate_readiness(ctx)`. 200 always.
- `POST /readiness/recheck`, body model `{"gates": tuple[GateId, ...]}` (min length 1;
  unknown id → 422 via pydantic) → `recheck_gates`; `Depends(require_http_origin)` like
  `runs_unavailable.py`.

### 4b. MCP — `api/v1/controlplane_mcp.py`

`_McpControlPlaneAdapter.readiness(self, *, recheck: tuple[str, ...] | None = None)`
following the `harnesses` method's `_invoke` pattern; `recheck` values validated against
`GATE_IDS`; registered in the FastMCP block beside `harnesses(view=...)`.

### 4c. Doctor — `cli/diagnose.py:run_doctor`

Replace the `session store` check block and the per-harness install lines with one loop
over `asyncio.run`-driven `open_probe_context(None)` + `evaluate_readiness` (or
`recheck_gates` on all five when the new `--recheck` typer flag, default False, is set —
live probes, real binaries, read-only). Formatting rules, exact:
- `ok` → `_ok(gate label, first item summary)`.
- `error` on `hard` → `_fail(label, detail or summary)` (session store keeps failing exit
  semantics; `detail` carries the full setup help).
- `needs_setup`/`error` on `advisory` → warn style (yellow, non-fatal), one line per item:
  `summary`; hint line = `CommandRemedy.command`, or for `TerminalRemedy` the catalog's
  `cli_hint` (`terminal_intents.py:TERMINAL_INTENTS[intent].cli_hint`), or for `UiRemedy`
  the literal `"open the app and press ⌘K → Workdir → Create new Workdir"`.
- `unknown` → warn `"not yet observed — run the app once or pass --recheck"`.
Grok: doctor's grok line is inherited from the deleted per-harness block; it is re-added as
a plain presence check OUTSIDE the registry loop, byte-compatible with today's
`warn missing grok` / `ok grok` output (readiness excludes grok; doctor's environment
diagnostics keep it — §10 Q13). Checks doctor keeps untouched: `python`, `mitmdump`,
`addon`, `node`, `gateway` entry, `web bundle`, `storage`, `proxy port`, `web port`, runs
report. `_session_store_failure` becomes unused → deleted.

### 4d. Desktop structured failure — the status line

- `cli/launch_runtime.py:preflight_session_store_or_exit`: before `raise typer.Exit(2)`,
  emit to stderr exactly one line:
  `STARTUP_STATUS_LINE_PREFIX + json.dumps({"gate_id": "session_store", "summary": error.split("\n", 1)[0], "remedy_command": None})`
  where `error` is `prepare_session_store()`'s returned string and the prefix is imported
  from `readiness/models.py` (condition 5: Python owner named; `remedy_command` is null
  because the session-store remedy is deliberately not a single command — the rule is
  `remedy_command` carries a value only when the selected remedy is exactly one
  `CommandRemedy`). Existing human-readable output unchanged; the line is additive.
- `desktop/src/backendProcess.ts`: retain the last 64 stderr lines on the exit watcher's
  rejection (field `recentOutput: string[]`, the `GatewayStartupError` shape precedent);
  new export `parseStartupStatusLine(output: string): StartupStatusLine | null` — LAST line
  starting with the prefix, `JSON.parse` in try/catch, structural field check, null on any
  failure. Type + prefix from `@tm/contract/readiness` (add `"@tm/contract": "workspace:*"`
  to `desktop/package.json` — zero-runtime by contract-package charter).
- `desktop/src/main.ts:showBackendStartupFailure`: parsed line present → modal body
  `summary` (+ `"\n\n" + remedy_command` only when non-null); else current behavior
  byte-for-byte.

## 5. The auth remedy — terminal intents, end to end

### 5a. Catalog — `api/src/transport_matters/readiness/terminal_intents.py` (new)

```python
class TerminalIntent:            # frozen dataclass
    intent_id: str
    argv: tuple[str, ...]
    env: Mapping[str, str]       # merged OVER the pane's base env
    cli_hint: str                # copy-paste equivalent, for doctor

TERMINAL_INTENTS: dict[str, TerminalIntent] = {
    "claude-native-login": TerminalIntent("claude-native-login",
        ("claude", "auth", "login"), {}, "claude auth login"),
    "codex-native-login": TerminalIntent("codex-native-login",
        ("codex", "login"), {}, "codex login"),
}

def intent_for_connection(harness_id: str) -> str
    # "claude" → "claude-native-login"; "codex" → "codex-native-login"; anything else → KeyError
    # (unreachable: callers iterate READINESS_HARNESSES)
```

Default home on purpose (§10 Q7). The browser never sees argv/env; it echoes `intent_id`
opaquely. Grep-guard test in S4: no `native-login` literal in `www/packages` outside
contract fixtures.

### 5b. Capture RPC resolve — Python

`api/v1/capture_rpc_routes.py` gains
`@router.get("/terminal-intents/{intent_id}")` → 404
`raise_api_error(404, "unknown_intent", ...)` when absent, else
`{"argv": [...], "env": {...}}`. Final path `/v1/capture/terminal-intents/{intent_id}`
(same mount as `/v1/capture/prepare`).

### 5c. Gateway

- `packages/runtime/src/adapters/CaptureRpcClient.ts` gains
  `resolveTerminalIntent(intentId: string): Promise<{argv: string[]; env: Record<string, string>}>`
  → `this.request("GET", "/v1/capture/terminal-intents/" + encodeURIComponent(intentId))`;
  error mapping identical to `prepareCapture`.
- `packages/runtime/src/service/PlainTerminalSessions.ts:OpenPlainTerminalInput` gains
  optional `command?: { argv: string[]; env: Record<string, string> }`; in `open`, when
  present: `argv: [...input.command.argv]` replaces the shell argv and
  `env: { ...browserPtyEnvironment(process.env), ...input.command.env }`. Fanout/exit
  behavior unchanged.
- `packages/runtime/src/server/plainTerminalConnection.ts`: query gains `intent?: string`;
  deps gain `resolveIntent?: (id) => Promise<{argv; env}>`. Intent present + no resolver →
  close `POLICY_VIOLATION` `"intent_unavailable"`; resolver rejects → close
  `POLICY_VIOLATION` `"unknown_intent"`; else thread `command` into `open`. The uncaptured
  stub gateway has no resolver → fails closed by construction.
- `packages/gateway/src/main.ts:createDefaultRuntimeRouterDeps` (and the captured-deps
  variant): `resolveIntent: (id) => captureRpc.resolveTerminalIntent(id)` when a capture
  RPC client exists.

### 5d. Browser (exact owners — review condition 3)

- `infrastructure/runtime/internal/terminalSocket.ts:terminalSocketUrl` gains optional
  trailing `intent?: string`; when set, append `&intent=${encodeURIComponent(intent)}`.
- `infrastructure/runtime/terminalTransport.ts:TerminalEndpoint` gains
  `| { kind: "intent"; intent: string }`; `terminalTransport.ts:urlFor` handles it by
  calling `terminalSocketUrl(cols, rows, window.location, endpoint.intent)`. `TerminalPane`
  keeps never calling `terminalSocketUrl` directly.
- `viewers/terminal/terminalSession.ts:TerminalSessionOptions` gains
  `onClose?: (info: TerminalTransportCloseInfo) => void`. `useTerminalSession` owns a
  one-shot latch: the FIRST involuntary transition to `closed` (whether reported via
  `onerror` or `onclose` — the adapter can fire both) invokes the callback exactly once;
  deliberate unmount consumes the latch silently. Tests: error-then-close → one call;
  unmount → zero calls.
- Pane ref: `model/paneRecords.ts` adds
  `{ kind: "intent-terminal"; owner: "local"; intent: string; title: string }` to the
  content-ref union AND to `paneRecords.ts:isPaneContentRef`. Exhaustive owners updated:
  `paneIdentity.ts:paneIdForRef` → `intent-terminal:${ref.intent}` (one pane per intent;
  respawn focuses), `paneIdentity.ts:titleForRef` → `ref.title`,
  `paneIdentity.ts:viewerIdForRef` → `"intent-terminal"`.
- Viewer: register `intent-terminal` in `viewers/registry.tsx:registry`, rendering through
  the existing lazy `TerminalPane` chunk with endpoint
  `{kind: "intent", intent: ref.intent}`. (Rev 1's `CanvasPaneLayer.tsx` renderer-switch
  instruction was wrong — the registry is the owner — and is withdrawn.)
- Persistence: exclude the kind in BOTH
  `canvasStore.persistence.ts:isPersistableCanvasPaneRef` and
  `canvasStore.persistence.ts:dockedForPersistedRecords` — an intent terminal never
  rehydrates open OR docked (plain terminals do not survive their socket).
- Spawn: `model/canvasActions.ts:spawnIntentTerminal(intent: string, title: string): PaneId`
  → `spawnPane({kind: "intent-terminal", owner: "local", intent, title}, {focus: true})`.
  No `requireWorktreeId` — identity-free by design.
- Recheck wiring: `TerminalPane`, when rendering an `intent-terminal` ref, passes
  `onClose` = fire `useReadinessRecheck` mutation with `["harness_auth"]` (hook from
  `@tm/core`, §6). One-shot latch above guarantees at most one recheck per pane life.

## 6. The canvas gate

- `@tm/core`: `core/src/transport.ts:fetchReadiness` (`requestApiJson("/api/readiness",
  "Failed to load readiness")`) and `recheckReadiness(gates)` (POST, detailAware). New
  `core/src/useReadiness.ts`: `useReadiness()` — react-query, key `["readiness"]` (added to
  `core/src/queryKeys.ts`), `refetchInterval: 30_000` while the last report's
  `overall !== "ready"` (a `checking` report therefore keeps polling — condition 1);
  `useReadinessRecheck()` — mutation, `onSuccess` writes the returned report into the query
  cache. Types from `@tm/contract/readiness`.
- `www/packages/canvas/src/workbench/StartupGatePanel.tsx`: `null` when no data or
  `overall === "ready"`. Otherwise one `canvas-alert`-family panel listing every gate item
  with `status !== "ok"`:
  - `unknown` items render as checking (spinner glyph + summary), no remedy button.
  - `CommandRemedy` → summary + `<code>` command, click = `navigator.clipboard.writeText`.
  - `TerminalRemedy` → button → `useCanvasStore.getState().spawnIntentTerminal(remedy.intent, remedy.label)`.
  - `UiRemedy` → button → `requestLauncherOpen(remedy.scope)`.
  - One "Check again" button → recheck `["harness_install","harness_version","harness_auth"]`
    (coalesces to one full refresh, §3b).
- `www/packages/canvas/src/launcher/launcherOpenRequest.ts`: non-persisted zustand store
  `{ request: {scope: LauncherScope; generation: number} | null;
  requestLauncherOpen(scope): void; consumeLauncherOpenRequest(): void }`. No storage key.
  `launcher/useCommandCenter.ts` subscribes in a `useEffect`: new generation → its internal
  `openScope(request.scope)` + consume. `buildSpaceRows` already leads the `workdir` scope
  with "Create new Workdir".
- Mount: first child of the `canvas-alert-stack` div in `workbench/CanvasWorkbench.tsx`.
- Suppression rule: `workbench/SessionCanvasRoute.tsx` suppresses the
  `worktreeResolutionFailed` alert and the `worktree_not_found` acting-context alert only
  when the readiness query reports `workspace_inventory.status === "needs_setup"`. All
  other failure codes keep their alerts (tested both directions, §9 G).

## 7. Move list (FROM → TO)

New files: `readiness/{__init__,models,context,registry,gates,rechecks,terminal_intents}.py`
+ colocated tests + `test_contract_fixture.py`; `api/v1/readiness_routes.py`;
`packages/contract/src/readiness/{wire.ts,index.ts,fixtures.ts,testing.ts,fixtures/*.json,readiness.test.ts}`;
`core/src/useReadiness.ts`; `canvas/src/workbench/StartupGatePanel.tsx`;
`canvas/src/launcher/launcherOpenRequest.ts`.

Edits, every one:
1. `cli/diagnose.py:run_doctor` — session-store block and per-harness block DELETED,
   replaced by the registry loop + the standalone grok presence line (§4c);
   `_session_store_failure` DELETED; `--recheck` flag added.
2. `harnesses/state_refresh.py` — extract `_probe_connections_access`; add public
   `refresh_authentication` (§3d). `_refresh_connection_access` stays private (rev 1's
   promotion withdrawn).
3. `credential_broker.py` — add public
   `OWNER_LOGIN_COMMAND = "CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login"`;
   `_WRITE_BACK_ERROR_MESSAGE` interpolates it. Not referenced by the v1 catalog (§10 Q7);
   minted now as broker slice 3's single source.
4. `cli/launch_runtime.py:preflight_session_store_or_exit` — status line emission (§4d).
5. `desktop/src/backendProcess.ts` — output retention + `parseStartupStatusLine`;
   `desktop/src/main.ts:showBackendStartupFailure` — structured rendering;
   `desktop/package.json` — add `@tm/contract`.
6. `www/packages/core/src/transport.ts:fetchCapabilities` — DELETE (dead export, zero www
   consumers; the HTTP endpoint stays). `queryKeys.ts` gains `readiness`.
7. `api/v1/capture_rpc_routes.py` — intent resolve route (§5b).
8. Gateway: `CaptureRpcClient.ts`, `PlainTerminalSessions.ts`,
   `plainTerminalConnection.ts`, `gateway/src/main.ts` — additive edits per §5c.
9. Canvas/browser: `terminalSocket.ts`, `terminalTransport.ts`, `terminalSession.ts`,
   `viewers/registry.tsx`, `paneRecords.ts`, `paneIdentity.ts`, `canvasActions.ts`,
   `canvasStore.persistence.ts`, `TerminalPane.tsx` — additive edits per §5d.
10. `SessionCanvasRoute.tsx` — suppression rule (§6). `CanvasWorkbench.tsx` — panel mount.

(Rev 1's item 11 — the S6 env sentinel — is DELETED per review condition 4.)

## 8. Slice plan

Five slices. Each is one PR, independently correct; the build loop gates on `just check` +
`just test-affected`, full `just check` + `just test` as the pre-merge authority. Order
S1 → S5 strictly; S5 requires S2 (it imports `@tm/contract/readiness` — condition 4's
dependency correction).

**S1 — readiness package + doctor (Python only).** models (incl. `checking`), context
factory, registry, gates, coalesced rechecks, `refresh_authentication` +
`_probe_connections_access` extraction, doctor loop + `--recheck` + grok presence line.
Proves: per-gate mapping tests from stored-evidence fixtures; `derive_overall` truth table
incl. unknown-only → `checking` and advisory-error → `needs_setup`; invocation-count
coalescing test; temp-pool lifecycle test (opened cold → closed on exit; app pool never
closed); paged-worktree test (worktrees only in page 2 → ok); sanitized-exception test;
doctor snapshot incl. the auth warn line; §9 perturbations; §9 B4 real-Postgres test.

**S2 — HTTP + MCP + contract subpath.** `readiness_routes.py`, MCP `readiness`, contract
subpath + both fixture conformance tests (incl. the checking fixture). Proves: 200 report;
recheck persists via fake writer; 422 unknown gate; origin guard; MCP tool test; prefix
conformance.

**S3 — terminal intents (Python + gateway).** Catalog, resolve route,
`resolveTerminalIntent`, `PlainTerminalSessions.command`, intent handling, deps threading.
Proves: real-PTY integration test through the command path (`/bin/echo`); unknown-intent
and no-resolver close-code tests; RPC 404 mapping; §9 B1 demos (Claude AND Codex) and the
composed-chain proof (§9 B6-4).

**S4 — canvas gate + login pane + recheck loop.** `useReadiness`/`useReadinessRecheck`,
`StartupGatePanel`, `launcherOpenRequest`, `TerminalEndpoint.intent`, one-shot `onClose`,
`intent-terminal` kind across all §5d owners, suppression rule, `fetchCapabilities`
deletion. Proves: panel render states from fixtures (ready → null; checking → spinner
rows; auth needs_setup → login button); dispatch tests (intent id from fixture, never a TS
literal — grep-guard; `requestLauncherOpen("workdir")`); one-shot close tests
(error-then-close → one recheck; unmount → zero); suppression both directions; persistence
exclusion (open AND docked) via old-snapshot-then-rehydrate; full
`pnpm --filter @tm/shell test` (new pane kind touches shared registries — structural rule).

**S5 — desktop structured failure (after S2).** Status line + parser + modal. Proves: exact
line format on a forced preflight failure (real captured stderr fixture, §9 B5); parser
valid/garbage/absent cases; modal assembly; `main.standalone.test.ts` untouched and green.

## 9. Hazard register

### B. Boundaries we do not control — real proof per touch point (condition 6 applied)

| # | Boundary | Proof that must exist |
| --- | --- | --- |
| B1 | `claude` AND `codex` interactive login TUIs in a PTY | Before S3 merges: TWO isolated-worktree eyeball demos, one per real installed binary, opening the intent pane, verifying the login screen paints, Ctrl-C cancels clean, STOPPING before any account interaction (no token exchange, no keychain write). Recorded as demo notes in the PR. The automated test uses `/bin/echo` for determinism; the demos cover the real binaries |
| B2 | `claude auth status --json` / `codex login status` via doctor `--recheck` | No new parsing (reuse `run_authentication_probe` adapters). ADDITIONALLY (condition 6): one read-only `doctor --recheck` run against both real installed binaries before S1 merges, output pasted in the PR — proves the newly exposed recheck path drives the real commands, not only fixtures. No login, no credential mutation |
| B3 | Keychain | Never touched. Grep-gate test in S1: `readiness/` imports neither `credential_broker` adapters nor `subprocess` (its only subprocess reach is the existing probe runner via `state_refresh`) |
| B4 | Postgres | S1 includes one integration test against the repository's REAL Postgres test store (the session-store test fixtures other suites use): cold `open_probe_context(None)` → all five gates evaluate, `session_store=ok`; plus the refused-connection case → `error` + gates `unknown` |
| B5 | Electron child stderr protocol | Versioned prefix, last-match-wins, additive. Parser fixtures include a REAL captured stderr from running `transport-matters start` against a dead DSN once (interleaved + truncated-line cases) |
| B6-4 | The composed intent chain (FastAPI route → Node `CaptureRpcClient.resolveTerminalIntent` → gateway WS → PTY) | One S3 integration test or recorded demo crossing the LIVE chain end to end with `/bin/echo`: real FastAPI serving the resolve route, real gateway process, real WS attach, bytes asserted. Unit-level RPC mapping alone does not prove the composed protocol |

### G. Guards that must be provably red-able

| Guard | Perturbation that turns it red |
| --- | --- |
| `unknown_intent` / `intent_unavailable` closes | `intent=bogus` → 1008 `unknown_intent`; resolver removed → 1008 `intent_unavailable` |
| Recheck persists, not just reports | Fake writer seeded `login_required` → recheck flips report AND `upsert_access_observation` received the row; writer that raises → gate stays `needs_setup` on stored evidence, never silently ok |
| `derive_overall` | Truth table: advisory `error` → `needs_setup` never `blocked`; hard `error` → `blocked`; unknown-only → `checking` never `ready` (the fail-open case that motivated condition 1) |
| One-shot `onClose` latch | Adapter fires `onerror` then `onclose` → exactly one recheck; deliberate unmount → zero |
| Status-line parser fallback | Garbage after prefix → null → modal shows raw message (parser can never worsen failure reporting) |
| Panel suppression | `workspace_inventory=ok` + acting-context `worktree_not_found` → stale-link banner still renders |
| Probe exception containment | Raising probe → fixed sanitized summary, other gates still evaluate, HTTP still 200, exception text absent from the report body |
| Coalescing | Invocation-count test (§3b) |
| Contract conformance | Mutate one enum literal on either plane → that plane's fixture test fails (verified once intentionally in the S2 PR, then reverted, noted in the PR description) |

### X. Two-plane crossings, single-sourced

1. `ReadinessReport` JSON: `readiness/models.py` ↔ `@tm/contract/readiness/wire.ts` via the
   shared sample fixtures, parsed by both planes' tests.
2. Intent ids: minted only in `terminal_intents.py`; opaque through wire and browser;
   grep-guard in S4.
3. Status line: prefix owned by `readiness/models.py:STARTUP_STATUS_LINE_PREFIX`, mirrored
   in `wire.ts`, equality asserted through the fixture's `prefix` field (§2b).
4. Intent resolve RPC: path literal once per plane at the established capture RPC seam,
   exactly like `/v1/capture/prepare`.

### O. Ordering hazards

- Background refresh race: first `GET /readiness` may precede `run_startup_refresh` →
  harness gates `unknown` → overall `checking` → panel shows checking rows and keeps
  polling (condition 1 closed the fail-open version of this).
- Recheck vs background refresh overlap: both funnel through the same evidence-store row
  upserts; last-writer-wins on single rows is the existing semantics.
- Double migration: UNCHANGED in this design (S6 deleted; the advisory-locked second pass
  stays — condition 4).
- Readiness route vs lifespan: routes serve only after lifespan yields; the probe reads
  `app.state.session_pool` defensively.
- Two alerts, one condition: suppression rule §6, tested both directions.

## 10. Settled questions

1. **Ownership** → Python `readiness/` (§1 D-OWN; survived review).
2. **XState** → no (§1 D-XS; survived review).
3. **Gate count** → five descriptors (survived review).
4. **Version ruling source** → stored `HarnessCompatibilityInfo` via `compare_versions`,
   not `match_release`.
5. **DB gate in the UI** → stays out of the canvas gate; the desktop modal (S5) is its
   surface; registry still carries it for doctor/MCP and the future no-DB mode.
6. **Recurring, not one-time** → re-evaluated every canvas mount + 30 s polling while
   unready; no onboarded flag anywhere.
7. **Which home does login remedy?** → the DEFAULT harness home (`claude auth login`, no
   `CLAUDE_CONFIG_DIR` override): today's launches consume default-home credentials
   (`cli/claude_home.py:ClaudeSeeder.seed` copies `oauthAccount` from the default config).
   Broker slice 3 adds a `claude-owner-login` intent to the same catalog and repoints
   `intent_for_connection`; its command single source (`OWNER_LOGIN_COMMAND`) is minted now
   (§7 item 3).
8. **Broker slice 2 relation** → zero shared files except the §7 item 3 constant
   extraction; the auth gate reads connection evidence, not broker state.
9. **Palette deep-link** → non-persisted zustand request store consumed by
   `useCommandCenter` (§6).
10. **New pane kind vs nullable worktreeId** → additive `intent-terminal` kind; existing
    terminal ref untouched; excluded from persistence in both named functions.
11. **`fetchCapabilities`** → deleted in S4; HTTP endpoint stays.
12. **Gateway-process consolidation** → deferred with reserved gate id (reviewer
    concurred).
13. **Grok** (new, condition 5) → excluded from readiness v1 via
    `READINESS_HARNESSES = ("claude", "codex")`: grok is not launch-eligible (no
    certification, no enumeration path — NOW.md), so a readiness verdict about it would be
    noise with no remedy. Doctor keeps its grok presence line as an environment diagnostic
    outside the registry, byte-compatible with today.
14. **`checking` overall** (new, condition 1) → fourth overall status; derivation
    `blocked > needs_setup > checking > ready`; polling predicate unchanged
    (`overall !== "ready"`).
15. **Session-store remedy** (new, condition 5) → `remedy: None` + full
    `session_store_setup_help()` prose in `detail`. No new remedy shape invented: doctor
    prints detail, the desktop modal shows the summary, and the canvas never renders this
    gate's failure (§10 Q5). `remedy_command` in the status line is null by the
    one-command rule.
16. **Install/update command literals** (new, condition 5) → owned by
    `readiness/gates.py:INSTALL_COMMANDS`: `npm install -g @anthropic-ai/claude-code`,
    `npm install -g @openai/codex` (the harnesses' official installers; no prior source in
    the repo — these literals are born single-sourced here). The update remedy reuses the
    install command.
17. **Auth-only recheck seam** (new, condition 2) → public
    `state_refresh.py:refresh_authentication` sharing the extracted
    `_probe_connections_access` with `_refresh_harness`; reads connections
    (`list_connections`), never reconciles them; upserts the fresh harness observation it
    detects (honest side effect, stated). Rev 1's raw promotion withdrawn.
18. **Timestamp aggregation** (new, condition 5) → `GateItem.observed_at` per item;
    `GateResult.observed_at` = newest non-null via `datetime.fromisoformat` comparison.
19. **Probe failure text** (new, condition 5) → fixed literals in
    `PROBE_FAILURE_SUMMARIES`; exception text goes to the server log only.
