# Adversarial review of tm-startup-design.md

Verdict: conditional signoff. Six design changes are required before the
artifact is mechanical enough to build without local decisions.

Baseline reviewed: `841e385ba4abd60f46dd83d6b2de0a75aa880111`.

## Decisions that survive review

1. Python ownership survives the two plane challenge. `cli/__init__.py:doctor`
   calls `cli/diagnose.py:run_doctor` without starting FastAPI, Gateway, or a
   browser. The client is genuinely cold. Readiness is operational composition
   over existing facts and owns no domain, events, projections, or durable
   aggregate. That fits the `docs/ARCHITECTURE.md` rule that Python receives no
   new product context. HTTP and MCP remain twin clients of one projection.
2. No XState survives. The server report is derived state. A terminal end
   causes one live recheck, and the panel retains a manual recheck. The user can
   leave the terminal open without creating a state transition. Section 5d
   still needs the one shot callback contract named in condition 3.
3. Five descriptors survive. Install presence and supported version have
   independent evidence, summaries, and remedies. Splitting the former combined
   harness gate is a real product ruling.
4. Gateway process consolidation can remain deferred. S1 through S5 can produce
   correct readiness and remedy behavior while current Electron and Python
   supervisors remain. The deferral in sections 1 and 10.12 is separable from
   these slices.

## Required changes

### 1. Give `unknown` an honest overall state

Sections 2a, 6, and 9 currently contradict each other.
`readiness/models.py:derive_overall` ignores `unknown`, so a report with a live
session store, a Workdir, and three unobserved harness gates becomes `ready`.
`core/src/useReadiness.ts:useReadiness` then stops polling, and
`workbench/StartupGatePanel.tsx:StartupGatePanel` renders `null`. Section 9 says
the same report renders as checking and polls until refresh finishes.

Amend the complete contract as follows:

* Add `"checking"` to `OVERALL_STATUSES` and `OverallStatus` in
  `readiness/models.py` and `@tm/contract/readiness`.
* Make `derive_overall` order exact: `blocked` for a hard error, then
  `needs_setup` for any remaining error or needs setup result, then `checking`
  for any unknown result, then `ready`.
* Keep the existing `overall !== "ready"` polling predicate.
* Render unknown items as checking in `StartupGatePanel`.
* Add the unknown only truth table case to S1 and the cross plane fixture to S2.

This resolves the startup refresh race without a new machine.

### 2. Complete the cold start database and recheck interfaces

The central interface in section 3 cannot run its own five descriptors as
written.

* `readiness/registry.py:ProbeContext` says `session_pool` is `None` for doctor.
* `harnesses/inventory.py:harness_inventory` requires a nonoptional
  `AsyncConnectionPool`.
* `space/service.py:SpaceCrudService` requires an `AsyncConnection`, so
  `count_spaces` and `list_spaces` cannot be called from the stated context.
* `harnesses/state_refresh.py:refresh_harness_state` requires an
  `EvidenceWriter`, which `ProbeContext` does not carry or construct.
* `session_store_preflight.py:check_session_store` reads global
  `get_settings()` rather than `ctx.settings`.
* Section 4a constructs `now=datetime.now(UTC)`, while `ProbeContext.now` is a
  callable.

Add the complete owned context factory to the design, including its exact file,
fields, and close behavior. It must reuse an app pool without closing it, open
and close a temporary pool for cold doctor when Postgres is reachable, and
leave DB backed gates `unknown` when no pool can exist. Name how
`ExecutorEvidenceStore` is constructed for rechecks and how
`SpaceCrudService` acquires its connection. The Workdir ruling must page
`SpaceCrudService.list_spaces` through `count_spaces` and test whether any
snapshot has worktrees; inspecting only one page can misclassify an older
populated Space.

Also specify recheck coalescing. The current descriptors call full
`refresh_harness_state` once for `harness_install`, again for
`harness_version`, then run the authentication recheck even though each full
refresh already probes auth. The panel's Check again action therefore performs
three authentication passes. Add a single sourced recheck identity and coverage
contract so install plus version plus auth executes one full refresh, while auth
alone executes one targeted access refresh. Add an invocation count test.

### 3. Write the actual intent terminal path and its one shot end contract

Sections 5d, 7, and S4 name a renderer switch in
`CanvasPaneLayer.tsx`, but the real owner is
`viewers/registry.tsx:registry`. Two other required interfaces are absent from
the move list:

* `infrastructure/runtime/terminalTransport.ts:TerminalEndpoint` owns endpoint
  URL selection. `TerminalPane` never calls `terminalSocketUrl` directly.
* `viewers/terminal/terminalSession.ts:TerminalSessionOptions` exposes no close
  callback. Its socket adapter can report `closed` from `onerror` and later
  from `onclose`, so a direct callback can recheck twice.

Amend section 5d with these exact changes:

* Add `{ kind: "intent"; intent: string }` to `TerminalEndpoint`.
  `terminalTransport.ts:urlFor` passes its intent to
  `terminalSocket.ts:terminalSocketUrl`.
* Add `onClose?: (info: TerminalTransportCloseInfo) => void` to
  `TerminalSessionOptions`. `useTerminalSession` owns a one shot latch and
  invokes it once for the first involuntary closed status. Deliberate unmount
  remains silent.
* Register `intent-terminal` in `viewers/registry.tsx:registry`, render it
  through `TerminalPane`, and remove the nonexistent CanvasPaneLayer branch
  instruction.
* Name all exhaustive owners:
  `paneRecords.ts:isPaneContentRef`,
  `paneIdentity.ts:paneIdForRef`,
  `paneIdentity.ts:titleForRef`,
  `paneIdentity.ts:viewerIdForRef`, and the viewer registry.
* Exclude both open and docked intent terminals through
  `canvasStore.persistence.ts:isPersistableCanvasPaneRef` and
  `canvasStore.persistence.ts:dockedForPersistedRecords`.

S4 must test an error followed by close and assert one recheck, plus deliberate
unmount and assert zero.

### 4. Remove the unsafe S6 environment sentinel and correct slice dependency

Section 7 says `TRANSPORT_MATTERS_STORE_PREPARED=1` is set in preflight and read
in lifespan, then section 9 says there is no new process protocol. Captured CLI
launch disproves that claim:
`cli/launch_runtime.py:preflight_session_store_or_exit` runs in the parent,
`captured_run.py:run_captured_run_on_local_tty` launches mitmdump, and
`addon_runtime.py:load_runtime` starts the embedded FastAPI server in the child.
The environment variable is a new cross process protocol. It is also ambient,
user settable, and unbound to the database URL whose migration was proven.
An unrelated or stale value can suppress
`main.py:_start_session_store` calling `session/migrate.py:apply_migrations`.

Delete S6 from this design and retain the existing advisory locked, normally
no op second migration guard. The slice is cleanup rather than a prerequisite
for readiness, and removing it preserves the stated Gateway process deferral.
A later consolidation can specify a URL bound, launcher minted protocol with
its own cross process proof.

Section 8 also says S5 may land any time after S1, while S5 imports
`StartupStatusLine` from the contract subpath created by S2. Change that
dependency to S5 after S2. The strict order S1 through S5 remains valid.

### 5. Finish and sanitize every remedy and timestamp decision

Sections 2a, 3, 4c, and 4d still leave field values for a builder to invent.

* `session_store_setup_help()` is multiline prose containing two alternative
  setup paths, so it cannot populate one executable `CommandRemedy.command`.
* `cli/diagnose.py:run_doctor` has no existing install hint for Claude, Codex,
  or Grok. Section 3's instruction to copy existing hint text has no source.
* `harnesses/__init__.py:list_harness_descriptors` includes Grok, while
  `terminal_intents.py:intent_for_connection` defines only Claude and Codex.
  Grok is explicitly not launch eligible.
* A harness gate contains multiple item timestamps, but
  `GateResult.observed_at` has one value and no aggregation ruling.
* `readiness/registry.py:evaluate_readiness` publishes `str(exc)` through HTTP,
  MCP, doctor, and the UI. An arbitrary adapter or database exception is not a
  safe user facing contract.
* The Python owner and symbol for `TM_READINESS_V1` are absent, and "first
  command line" selection from session store help has no algorithm.

Write the exact remedy catalog into the design. Restrict v1 actionable harness
items to launch eligible Claude and Codex, with literal install and login
commands. Keep full session store setup prose in `detail`; add an exact
noncommand remedy shape if the UI needs to present alternative setup paths.
Define item level `observed_at`, then derive the gate timestamp as the newest
non-null item timestamp. On probe exception, log the exception and publish a
fixed sanitized summary with no exception text.

Define `readiness/models.py:STARTUP_STATUS_LINE_PREFIX` as the Python source for
the emitted literal and keep the TS conformance assertion. The status line must
carry a remedy only when the selected remedy is exactly one command.

### 6. Extend the real boundary proof matrix

Section 9 does not yet meet its own rule for every touched external boundary.

* B1 proves only the installed Claude login TUI, while
  `terminal_intents.py:TERMINAL_INTENTS` adds both Claude and Codex.
* B2 uses a spy and captured parser fixtures. It does not execute the newly
  exposed doctor recheck path against either current installed binary.
* B4 does not require the readiness gate to use the real Postgres test store.
* The intent resolver adds a Python to Gateway RPC and a Gateway WebSocket to
  PTY chain. Unit level RPC mapping plus direct `/bin/echo` service coverage
  does not prove their composed protocol.

Require before merge:

1. End to end isolated intent pane demos for the real installed Claude and
   Codex binaries, stopping before account interaction and recording clean
   cancellation.
2. Read only `doctor --recheck` evidence for the installed Claude and Codex
   status commands, with no login or credential mutation.
3. One S1 integration test against the repository's real Postgres test store,
   plus a refused connection case.
4. One S3 integration test or demo that crosses the live FastAPI intent route,
   Node `CaptureRpcClient.resolveTerminalIntent`, Gateway terminal WebSocket,
   and a real `/bin/echo` PTY.

B5 already names an adequate real child stderr capture. The keychain remains
outside scope and needs no proof in these slices.

## Mechanical slice checks

Random slice S3 fails the current bar because
`terminalTransport.ts:TerminalEndpoint`, `terminalSession.ts:TerminalSessionOptions`,
and `viewers/registry.tsx:registry` are missing from its interface and move
list.

Random slice S6 fails the current bar because the chosen environment flag
crosses into the mitmdump child, has no database binding, and contradicts its
own "no new process protocol" claim.

With the six conditions above incorporated, the ownership, gate count,
state model, Gateway deferral, and remaining slice structure are suitable for
signoff.
