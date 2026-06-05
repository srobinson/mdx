# tm-1b-review-fable — PR#354 review (scout-fidelity pass)

Reviewed head `849cb42f` against baseline `0913b3bf`, read-only. Tree note: the shared checkout
carries one uncommitted file, `LESSONS.md` (a process note, outside PR scope); everything else
pristine, HEAD equals the PR head.

## Fidelity verdict

The build is the slice that was planned. It composed every named binding rather than
reimplementing: `captured/readiness.py` calls `session_store_preflight.check_session_store`,
`credential_source.harness_credential_error(require_shared=False)`,
`launch/binaries.resolve_client_binary` / `resolve_mitmdump_executable`,
`gateway_supervisor.resolve_node_binary` / `resolve_gateway_entry`, and stored enablement via
`HarnessEnablementStore.list_intents`. `launch/environment.resolve_native_harness_home` is a
genuine move, not a parallel implementation: `cli/claude_home.default_claude_home` and
`cli/codex_home.default_codex_home` now delegate to it. The ratchet was paid:
`cli/credential_source.py` is deleted with no shim and zero leftover `cli.credential_source`
imports; the two resolvers moved to `launch/binaries.py` with `cli/launch_runtime.py` keeping
only the `_resolve_client_binary_or_exit` adapter; `captured/dependencies.py` updated; nothing
new landed in `cli/`. Flag retirement is complete against grok's enumeration (route helper
deleted, all `SessionCanvasRoute` sites converted, test producer replaced; only module-name
comments in `fetchStatus.ts`/`commandTypes.ts` remain, which grok classified as mentions;
`FirstRunHint` untouched). The exclusions held: no doctor serialization, no watcher, no
monitor, no taxonomy, no tm_events payload or activity projection. The doctor fix is exactly
its one thing: `_warn` accumulator, "passed with N warning(s)" summary, exit 0, pinned
observably in `cli/test_diagnose.py` including `"all checks passed" not in stdout` over a warn.
Predicate language never over-promises: model docstring, screen lede, and footnote all state
the spawn can still fail typed.

## Findings

**F1 — Major, correctness/performance. `api/v1/launch_readiness.py:get_launch_readiness`
runs synchronous blocking I/O on the event loop.** `captured/readiness.py:launch_readiness` is
`async` but calls `check_session_store` (a synchronous psycopg connect; seconds on an
unreachable BYO host) and, on macOS for Claude, `harness_credential_error` →
`SecurityOwnerCredentialStore.read`, which shells `security(1)` with a 2s timeout — directly on
the loop, with no thread offload. api/CLAUDE.md's async boundary rule says route I/O is async.
Every canvas mount fetches this route (`useLaunchReadiness({fresh: true})`), so a slow DB or a
hung keychain stalls every concurrent API request, including run routes and capture RPC.
Failure scenario: DB configured to an unreachable host, user opens the desktop, every API
consumer freezes for the connect timeout on each route mount. Fix shape: run the evaluation in
a worker thread (`anyio.to_thread.run_sync`) or make the two sync calls offloaded inside
`launch_readiness`.

**F2 — Major, product semantics (owner decision surface).
`SessionCanvasRoute.tsx:launchReady` gates the whole workbench on the full predicate.**
`ready = all(infrastructure) and any(harness_ready)`, and `if (!launchReady) return
<FirstRunScreen />`. NOW.md's startup model says "TM fully operational with zero harnesses
installed is a valid state, and the UI must say so rather than treating it as failure.
Launching requires both stages; nothing else does." Under this gate a user whose only harness
is uninstalled, disabled, or credential-dead (the nuke case) loses the entire workbench —
history, transcripts, persisted canvases — behind a screen whose only affordance is retry.
Detection and offered re-auth was the requirement; a hard lock on non-launch capability is
stronger than the requirement and contradicts NOW's two-stage rule. If the owner wants the
hard lock, record it as a deviation; otherwise gate the workbench on the infrastructure
checks and surface harness readiness as the screen's advisory rows plus a proceed affordance.

**F3 — Minor, UX. First-run masthead flashes on every healthy mount.** `launchReady` is false
while the query is loading, so every desktop start renders `FirstRunScreen` ("First run"
masthead, rise animation) until the fetch returns — compounded by F1's latency. A neutral
loading branch in `SessionCanvasRoute` (or holding the previous verdict until the first result)
removes the flash.

**F4 — Minor, consistency. Doctor and predicate now disagree about the same credential.**
`cli/diagnose.py:_report_credential_readiness` still calls `harness_credential_error(source)`
with the default `require_shared=True` while `captured/readiness.py:_credential_check` passes
`require_shared=False`. On a bootstrapped-but-never-launched fleet home the screen says the
Claude credential is ready and doctor warns it unavailable, reviving the one-predicate
two-answers split this area exists to close. One-line dispatch change plus a test.

No other findings. Style, naming, and CI-gated concerns not flagged per brief.
