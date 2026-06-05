# TM slice 1b review — correctness and blast radius (Opus, second reviewer)

PR#354 `feat/launch-readiness-doctor-gate`, head `849cb42f`, baseline `main` at `0913b3bf`.
Read-only pass. Scope per brief: failure path, the moves, side-effect freedom of the
predicate, `require_shared=False`, code reuse. Plan fidelity belongs to the other reviewer.

Tree state at verdict: HEAD is `849cb42f` as briefed, nothing staged, no PR file modified.
`LESSONS.md` carries one uncommitted line ("no enumerated scaffolding in prose"), outside
the PR's 39 files. Flagging it because a dirty shared tree usually means a concurrent edit.

Counts: 3 Blocker, 4 Minor.

---

## Blocker 1 — the predicate does blocking network, subprocess and filesystem work on the event loop

`api/src/transport_matters/api/v1/launch_readiness.py::get_launch_readiness` is `async def`
and awaits `captured/readiness.py::launch_readiness`, which calls its collaborators inline:

- `_infrastructure_checks` → `session_store_preflight.check_session_store()` → a real
  `psycopg.connect(database_url, connect_timeout=5)` plus `SELECT 1`. Synchronous TCP.
- `_credential_check` → `harness_credential_error` → on darwin
  `SecurityOwnerCredentialStore(...).read()` → `subprocess.run("/usr/bin/security",
  "find-generic-password", "-a", …, "-w", …)`, one process spawn per evaluation.
- `_client_binary_check` / `resolve_mitmdump_executable` → `shutil.which` across every PATH
  entry, plus `is_runnable_candidate` stats.
- `_read_enablement` → `harnesses/executor_identity.py::local_executor_id()`, blocking file
  I/O, and on a first-ever run a write (Minor 4).

Nothing is wrapped. The repo already knows these calls must leave the loop:
`capture_rpc.py:158` is `store_error = await asyncio.to_thread(self._dependencies.check_session_store)`
and `credential_refresh.py:63` is `await asyncio.to_thread(_mint, broker_factory)`.

**Failure scenario.** Postgres is unreachable — the exact condition readiness exists to
report. Each `GET /v1/launch-readiness` parks the single event loop for the full 5 s connect
timeout. The canvas fires this query on every mount and, because `useLaunchReadiness` sets
`staleTime: 0` and the shared client (`core/src/queryClient.ts`) does not disable
`refetchOnWindowFocus`, on every window focus and network reconnect. During each stall
every `WS /runs/{id}/terminal`, every activity SSE stream and every other API request is
frozen. On darwin add a `security(1)` spawn per evaluation, and a keychain ACL prompt if the
calling binary is not trusted on the item.

Invisible to CI: `captured/test_readiness.py` monkeypatches `check_session_store`,
`resolve_mitmdump_executable`, `resolve_node_binary`, `resolve_gateway_entry`,
`resolve_client_binary` and the credential seam, and `api/v1/test_launch_readiness.py`
replaces `launch_readiness` wholesale. No test executes a real collaborator.

**Direction.** `await asyncio.to_thread(...)` around the synchronous block, matching
`capture_rpc.py`. Reachability could instead reuse the async pool already passed in rather
than opening a second, synchronous connection.

## Blocker 2 — launch readiness gates the observability surface, not just launching

`readiness.py::launch_readiness` returns
`ready = all(check.ready for check in infrastructure) and any(harness_ready)`, and
`SessionCanvasRoute.tsx` renders `if (!launchReady) return <FirstRunScreen />`.
`FirstRunScreen` offers only "Retry launch readiness". There is no bypass.

**Failure scenario.** A machine with no launch-eligible harness installed: `any([])` and
`any([False, …])` are both false, so `ready` is false forever, and the canvas is replaced by
the first-run screen permanently. The session picker, previously captured transcripts and
exchange inspection are all unreachable, though none of them needs a harness. The same PR's
`FirstRunScreen.tsx` states the opposite in `SUMMARY_NOTES.none_installed`: "No harnesses are
installed. That is a valid state: Transport Matters is fully operational without them."
The same lockout follows from a harness disabled by operator intent
(`harness_disabled`) or a logged-out harness (`harness_not_installed` /
`*_credential_unavailable`) — states that block a *launch*, not a *look*.

Infrastructure failures are a different case: `session_store_unavailable` plausibly does
justify closing the workbench. The harness-level terms do not.

**Direction.** Split the verdict. Infrastructure readiness gates the workbench; harness
readiness gates the launch affordance and belongs on the launch path's typed failure, which
already exists.

## Blocker 3 — a transient readiness error retracts an already-granted mount

`launchReady = readiness.status === "populated" && readiness.data?.ready === true`, and
`fetchStatus.ts::deriveFetchStatus` returns `"error"` whenever `isError` is true, regardless
of retained data. Verified against the installed `@tanstack/query-core@5.101.2`: the reducer's
`case "error"` sets `status: "error"` while preserving `data` (its own comment: "flag existing
data as invalidated if we get a background error"), and `shouldFetchOn` with an undefined
`refetchOnWindowFocus` returns true for a stale query, which `staleTime: 0` guarantees.

**Failure scenario.** The workbench is open with live panes. The user switches away and back
(or the machine wakes, or `refetchOnReconnect` fires) while the API is restarting. The focus
refetch fails past `retry: 1`, `status` flips to `"error"`, `launchReady` goes false, and
`SessionCanvasRoute` unmounts `CanvasWorkbench` mid-session: xterm instances disposed,
terminal websockets closed, `useWorkspaceActivityStream` disabled, `useRunVitalsStore` cleared
on unmount, captured-run reconciliation re-run on the way back. Server-side runs survive
(`stopRun` is only reached from the explicit close affordance), but the whole UI is replaced by
a first-run screen because one HTTP request failed.

Failing closed at first mount is defensible and the copy states it honestly. Retracting a
mount already granted, on a *transport* error rather than a *verdict*, is not: it converts
every backend blip into a full-app takeover.

**Direction.** Latch the grant. Only a definitive `ready === false` should close the
workbench; `status === "error"` with a prior grant should keep it open (and may surface a
banner). No test covers the readiness-errors path at the route level — the three new
`SessionCanvasRoute` tests all return a well-formed body.

## Minor 4 — the predicate is not side-effect free: readiness can mint the executor id

`readiness.py` opens with "Fresh, read-only evidence" and `LaunchReadiness`'s docstring calls
it read-only prerequisites, but `_read_enablement` calls
`harnesses/executor_identity.py::local_executor_id()`, whose docstring is "minting it on first
use": `path.parent.mkdir(parents=True, exist_ok=True)`, `candidate.write_text(...)`,
`os.link(...)`, `candidate.unlink(...)`.

**Failure scenario.** A fresh install — precisely the first-run case this gate serves — hits
`GET /v1/launch-readiness`, and the GET creates the channel storage root and writes
`executor-id`. Harmless in effect (the id is stable, and launch would mint the same one), but
the stated contract of the module is false, and a route documented as evaluating without
materializing state materializes state. Either resolve the id read-only here and let launch
mint, or drop the read-only claim from both docstrings.

## Minor 5 — "not yet known" renders as "not ready"

The same expression makes `status === "loading"` mount the full first-run chrome, so the
masthead and skeleton flash on every canvas mount and reload until the request lands, which
under Blocker 1 can be seconds. Distinguish unknown from known-not-ready.

## Minor 6 — `gateway_unavailable` is minted inline over an existing code with a different meaning

`readiness.py::_infrastructure_checks` writes `code="gateway_unavailable"` as a bare literal.
`api/v1/errors.py::GATEWAY_UNAVAILABLE_CODE` already owns that exact string for a different
condition: the gateway HTTP transport being unreachable (`run_proxy.py`,
`controlplane_gateway_*.py`). The harness codes are handled correctly, reusing the
`exceptions.py` literals (`harness_not_installed`, `harness_disabled`,
`harness_enablement_unavailable`) and the `CredentialErrorCode` from the credential path. The
four infrastructure codes are the exception: raw strings on a `code: str | None` field, so
neither the collision nor a future typo is catchable.

## Minor 7 — two names for one constant after the move

`cli/home_constants.py` now reads `_CLAUDE_CREDENTIAL_FILENAME = CLAUDE_CREDENTIAL_FILENAME`
and `_CODEX_AUTH_FILENAME = CODEX_CREDENTIAL_FILENAME`, keeping the private aliases alive for
existing CLI call sites. One value, two module-level names, and `home_constants` becomes a
pass-through for them. Repoint the remaining consumers and delete the aliases.

---

## Verified clean

- **No import cycles, no missed callers.** `api/.venv/bin/python -c "import
  transport_matters.captured.readiness, transport_matters.credential_source,
  transport_matters.cli.home_constants, transport_matters.cli.launch_runtime,
  transport_matters.main"` imports cleanly. No remaining importer of
  `transport_matters.cli.credential_source` anywhere in `api/` or `www/`; every
  `resolve_mitmdump_executable` / `resolve_client_binary` caller
  (`cli/diagnose.py`, `cli/launch_runtime.py`, `captured/dependencies.py`,
  `captured/readiness.py`) points at `launch/binaries.py`, and the one test that patches by
  string patches `cli.diagnose.resolve_mitmdump_executable`, which still resolves.
- **No plane violation.** `captured/readiness.py` imports `launch/`, `harnesses/`,
  `credential_source`, `gateway_supervisor`, `session_store_preflight`. It does not reach
  into `cli/`. The new root-level `credential_source` is imported by `cli/` and by
  `captured/`, which is the direction the move was made for.
- **No behaviour drift in the moved resolvers.** `default_claude_home` /
  `default_codex_home` were "env key wins, else `Path.home()/.claude|.codex`"; the extracted
  `launch/environment.py::resolve_native_harness_home` is byte-for-byte that rule, so
  `assert_claude_client_credential_identity`'s security-relevant fallback is unchanged.
  `credential_source.py` moved with only the `home_constants` import inverted.
- **`require_shared=False` reads and never mints.** Minting lives solely in
  `_mint_claude_credential`, reached only from `resolve_credential_path`. The
  `require_shared=False` branch runs `fleet_home_unavailable_reason` then
  `SecurityOwnerCredentialStore.read()` and skips `shared_access_credential_error`. The
  default stays `True`, so `resolve_credential_path` and
  `assert_claude_client_credential_identity` are untouched and Codex's fail-closed
  `NativeCredentialSource.credential_path.is_file()` path is unchanged.
  Consequence worth stating, not a defect: on darwin, Claude readiness can pass while the
  launch that requires shared access fails. The screen's own copy already claims only that.
