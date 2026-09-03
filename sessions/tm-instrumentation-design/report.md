# Observability as a first-class concern

Investigation and design. No code changed; working tree clean.

Reviewed at `3c2c6c4e` on `fix/support-derivation-causes`.

## Answer first

The thesis is half right, and the half that is wrong is the expensive half.

Logging and latency measurement share **one destination policy and one
correlation vocabulary**. They do not share a production API, and forcing them
onto one would make both worse. The two record kinds have opposite cost models:
a log line must be always on, durable through SIGKILL, and cheap at low rate; a
latency mark must be off by default, lossy on crash, and cheap at 60 Hz. A
substrate that satisfies both at once satisfies neither well.

So: build the shared boundary once (a diagnostics destination resolver plus the
existing id vocabulary), ship #471 against it standalone, and add a separate
trace recorder later that reuses the destination and adds nothing to #471's
path. #471 is not rework under this design; it is step one of it.

There is a second finding that changes the order of work. The prior evidence
already bounds the server side of the terminal round trip at 1.3 ms median and
the PTY reply at 0.85 ms. If perceived key-to-pixel latency is tens of
milliseconds, then almost all of it is inside one process, the renderer, and
**the first measurement needs no cross-process substrate at all**. Build the
renderer-local probe first. It costs about a day, it partitions the budget, and
it tells you whether the cross-process substrate is warranted. Nobody has
established where the bottleneck is, and the cheapest instrument that can
establish it should not wait behind the general one.

---

## 1. What exists today

### 1.1 Python backend: logging

One formatter, one config, one helper.

- `api/src/transport_matters/logging.py:6` — `JSONFormatter`, 23 lines. Emits
  `timestamp`, `level`, `message`, `logger`, optional `exception`, optional
  `request_id`.
- `api/src/transport_matters/logging.py:20` — the `request_id` branch is
  **dead**. Nothing in the tree ever sets `record.request_id`; the only
  occurrences of the string are the formatter itself. Grep confirms zero
  producers.
- `api/src/transport_matters/logging.py:26` —
  `log_best_effort_startup_failure`, the documented workaround for mitmproxy's
  `ErrorCheck` addon, which watches the **root logger** and calls `sys.exit(1)`
  if anything reaches it at ERROR during addon startup. This is load-bearing and
  constrains any redesign: the Python log spine cannot be replaced by a bespoke
  emitter, because third-party code (mitmproxy, uvicorn, alembic, httpx) reaches
  it through `logging` and mitmproxy inspects it.
- `api/src/transport_matters/main.py:109` — `LOG_FORMAT`,
  `"%(asctime)s %(levelname)-8s %(message)s"`.
- `api/src/transport_matters/main.py:113` — `LOG_CONFIG`: one `console`
  StreamHandler on root, uvicorn loggers stripped of their own handlers and made
  to propagate.
- `api/src/transport_matters/main.py:525-534` — `create_app` deep-copies
  `LOG_CONFIG`, sets root level from `settings.debug`, swaps in `JSONFormatter`
  when `settings.log_json`, then `dictConfig`.
- `api/src/transport_matters/config.py:68` — `log_json: bool = False`. It is
  the only logging-related setting. `env_keys.py` does not name it, so
  `TRANSPORT_MATTERS_LOG_JSON` works only through pydantic's `env_prefix`.

Call-site inventory: 81 `getLogger(__name__)` declarations across 83 modules
that import `logging`. Naming is inconsistent — `shared_proxy/*` uses `LOGGER`,
most of the rest uses `logger`.

One outlier: `api/src/transport_matters/shared_proxy/subprocess.py:290` calls
`logging.basicConfig(level=logging.INFO)` in its `main()`. The shared proxy
subprocess therefore ignores `log_json` and the debug level entirely.

### 1.2 Python backend: log destination

There is no log destination abstraction. There are three unrelated file paths
and one fd-inheritance rule.

- `api/src/transport_matters/desktop_runtime.py:33` — `_LOG_FILENAME = "desktop.log"`.
- `api/src/transport_matters/desktop_runtime.py:161` — `desktop_log_path(storage_dir)`
  returns `<storage_dir>/runtime/desktop.log`. Six non-test callers:
  `cli/desktop_cmd.py:350`, `cli/tail_cmd.py:35`, `cli/_helpers.py:88`,
  `cli/desktop_runtime.py:16`, and the re-export in `api/v1/desktop_runtime.py`.
- `api/src/transport_matters/shared_proxy/process.py:83` — the shared proxy
  subprocess writes `<runtime_dir>/logs/shared-mitmdump.log`.
- `api/src/transport_matters/cli/runner.py:121` — `mitmdump_log_path(storage_dir)`
  returns `<storage_dir>/logs/mitmdump.log` for the per-run embedded proxy.

The detached desktop log is **not** produced by the logging framework. It is
produced by an fd redirect at spawn:
`cli/desktop_cmd.py:352-362` opens the file `"ab"` and passes the handle as
`stdout`, with `stderr=subprocess.STDOUT`. That is why it also captures:

- interpreter-level tracebacks written directly to fd 2,
- uvicorn output that does not route through the configured handlers,
- **the gateway child**, because `gateway_supervisor.py:298-311` spawns it with
  inherited stdout/stderr and documents exactly that ("stdout/stderr are
  inherited so gateway output lands in the host's log").

This is the single most important structural fact for #471. The log's coverage
comes from process-tree fd inheritance, not from `logging`. Any "make foreground
persist" that adds a `FileHandler` produces a strictly poorer artifact.

There is already one primitive for "spawn a child with a log file":
`api/src/transport_matters/supervisor/core.py:65` — `ProcessSupervisor.spawn(...,
log_path=...)`, which opens the path for append and wires it to the child's
stdout and stderr, and rejects ambiguous stdio policies (`core.py:151-167`). The
shared proxy and the per-run mitmdump both go through it. `desktop_cmd.py` does
its own `Popen` and does not.

The desktop foreground path (`cli/__init__.py:401`, `cli/desktop_cmd.py:158`)
runs uvicorn in-process via `serve_desktop_backend` (`desktop_cmd.py:444`) with
`log_config=LOG_CONFIG`, so its records go to the console StreamHandler and
nowhere else. The issue's claim is accurate.

`scripts/reset-channel-store.sh:327` wipes the channel home with
`find "$STORAGE_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf {} +`. The log is
inside it. The issue's second claim is accurate. Note that today the wipe *is*
the retention policy; moving the destination out of the home removes it and
creates an unbounded-growth problem the issue does not mention.

### 1.3 Node: gateway and runtime

No logger. `console.*` only, 43 occurrences repo-wide outside tests, and the
gateway's process runtime injects three of them:
`packages/gateway/src/main.ts:103-105,122` — `error`, `log`, `warn` as
`console.*`. Fastify is constructed without a logger. There is no request log,
no structured field, no correlation id.

One real telemetry object exists: `packages/activity/src/telemetry.ts` —
`ActivityTelemetry`, a counter class (`droppedRecords`, `reconcileFailures`,
`wireAdmitted`, `wireRefused`, `wireRetracted`) with an injected
`ActivityLogger` port defaulting to `console.warn`. Its stated purpose is to be
"the single `transport-matters doctor` source". It is wired only in
`packages/activity/src/gatewayDeps.ts:26-35`. `snapshot()` has no HTTP surface
that I could find; the doctor command (`cli/diagnose.py:187 run_doctor`) does
not read it.

This is the closest thing to an existing observability abstraction in the repo,
and the `ActivityLogger` interface (`telemetry.ts:7`) is the natural shape for a
Node-side logger port. Extend it rather than invent beside it.

### 1.4 Timing and metrics

Effectively none.

`grep` for `performance.now|process.hrtime|perf_counter|monotonic()` outside
tests returns:

- Python: 20 hits, **all** of them `time.monotonic()` used as a deadline in a
  wait loop (`loopback.py:45`, `launch_verification.py:386`,
  `shared_proxy/manager.py:279`, `supervisor/core.py:321`, …). Zero are
  measurements.
- Browser: 5 hits in two files.
  `www/packages/canvas/src/ambient/createAmbientBackground.ts:345,377` measures
  WebGL render time into an EMA;
  `createAmbientBackground.ts:383-387` maintains an fps EMA;
  `createAmbientBackground.ts:257` exposes both through `getStats()`.
  **`getStats()` has no consumer.** The only other reference is its declaration
  in `ambient/types.ts:89`. It is the one piece of renderer frame instrumentation
  that already exists and it is dead.
  `www/packages/canvas/src/browsing/useBrowserPanePresentation.ts:111,114` uses
  `performance.now()` as a rAF settle deadline, not a measurement.
- Node: zero.

No `duration_ms` is ever computed for a TM operation. The two hits in
`session/timeline.py:504` and `index/adapters/test_codex.py:213` read a
`duration_ms` **the harness wrote** into its own transcript.

### 1.5 Persisted timing

`wire_exchange` (`api/migrations/versions/0008_wire_store.py:70-98`) carries
`ts` and `created_at` and token counts. There is **no** request duration, no
TTFB, no first-token time. Provider latency is not measured anywhere despite the
system holding the request and response bytes.

The one deliberate database-level performance affordance is
`api/src/transport_matters/session/migrate.py:41` — `pg_stat_statements`,
installed best effort, explicitly "diagnostic only: nothing reads it at runtime",
motivated by a real incident ("the 2026-09-05 reconcile pass saturation was
attributable only from a shutdown log"). That comment is the whole problem in
one sentence.

### 1.6 Tracing

None. No OpenTelemetry, no Prometheus, no statsd, no Sentry, no Datadog in any
`package.json`, `pyproject.toml`, or lockfile.

There is a CDP front, but it is scoped to browser panes by construction:
`desktop/src/browserPaneDevtoolsFront.ts` holds a `canvasId -> webContents`
registry, and the only caller of `front.register(...)` is
`desktop/src/app/browserPanes/registerBrowserPaneHost.ts:49`, which registers
pane contents. The main window's own `webContents` is never registered
(`desktop/src/main.ts:87` passes the window to `registerBrowserPaneHost`, which
attaches pane hosts to it). Python mints capabilities against it
(`api/src/transport_matters/api/v1/devtools_access.py`) and never contacts the
front directly.

This is a **policy** limit, not a capability limit. `webContents.debugger`
attaches to any webContents including the renderer. Extending the existing front
to register the canvas renderer under its own target id is a small, in-pattern
change and is the cheapest route to Chromium `Tracing.*` on the desktop
renderer.

### 1.7 Existing correlation ids

The vocabulary already exists and is sufficient. Nothing new needs inventing.

| Id | Home | Reach |
| --- | --- | --- |
| `run_id` | `env_keys.RUN_ID`, `Settings.run_id` | every process |
| `session_id` | session store, universal key | Python, Postgres |
| `exchange_id` | `wire_exchange` | Python, product plane |
| `delivery_id` | control-plane delivery | Python, gateway |
| `attachmentId` | `TerminalFanout.ts:147`, minted at `:195` | gateway only |
| `runtime_id` | gateway process identity | gateway, Postgres |
| `workspace_id`, `canvas_id` | workspace/canvas | browser, Python |

Two facts make the terminal path measurable without inventing anything:

1. `TerminalFanout.append` already stamps every PTY chunk with a monotonic
   `seq` and an `emittedAt` (`TerminalFanout.ts:206-212`, fields declared at
   `:31,:33`). `attachmentPump.ts:47-49` then discards both and sends only
   `item.data`. The measurement already exists and is thrown away one line
   before the socket.
2. `attachmentId` accepts an injected value —
   `TerminalFanout.ts:168` (`attachmentId?: string | null`),
   `runManagerTypes.ts:66`, honoured at `TerminalFanout.ts:195`. Nothing supplies
   it today; `runTerminalConnection.ts` never sets it, so every attachment gets a
   random uuid. The seam for a browser-minted join key is already cut.

### 1.8 The terminal path, verified end to end

    keydown
      -> xterm onData                     terminalSocket.ts:142
      -> encoder.encode + socket.send     terminalSocket.ts:102-110
      -> [WS] Python uvicorn              run_proxy.py:488 /v1/runs/{id}/terminal
      -> _downstream_to_upstream          run_proxy.py, 1:1 frame forward
      -> [WS] Node gateway                runTerminalConnection.ts:87
      -> RunManager.write                 RunManager.ts:364
      -> NodePtyAdapter.write             NodePtyAdapter.ts:149-158
      -> pty
    ...
      -> TerminalEmulator.append          TerminalEmulator.ts:147
      -> TerminalFanout.append (seq, emittedAt)
      -> attachment queue -> pumpAttachment     attachmentPump.ts:47
      -> [WS] Python _upstream_to_downstream
      -> [WS] browser socket.onmessage    terminalSocket.ts:127-140
      -> term.write(bytes)                terminalSocket.ts:139
      -> xterm parse -> render -> compositor -> presented

Two properties I verified in source because the design leans on them:

- **Framing is 1:1 and typed.** `_downstream_to_upstream` forwards `bytes` as
  bytes and `text` as text with no batching; `_upstream_to_downstream` does the
  same via `send_bytes` / `send_text`. Both are plain `while True` relays.
- **Query strings survive.** `forward_terminal` (`run_proxy.py:372-379`) passes
  `websocket.url.query` verbatim to the gateway target;
  `_plain_terminal_target` (`:387-391`) reparses and re-encodes it while adding
  `cwd`. So a `?attach=<id>` parameter minted in the browser reaches the gateway
  unchanged.

Together these give an **ordinal join**: the k-th binary frame the browser
receives on an attachment (after `run.terminal.scrollback-end`) is chunk
`startSeq + k` in the fanout. No in-band marker is needed, and none is possible
— PTY frames are opaque bytes and injecting a marker upstream would reach the
shell.

---

## 2. Does one substrate serve both pressures?

### 2.1 Where they genuinely converge

- **Destination policy.** Both need "where does diagnostic output for this
  channel go", configurable, defaulting inside the channel home for
  compatibility, able to point outside it so a wipe does not destroy it. Today
  there are four unrelated answers (§1.2) and none is configurable.
- **Correlation vocabulary.** Both need `run_id` and friends on every record.
  A log line without a run id is as useless as a span without one.
- **Neither belongs in Postgres.** The session store is product truth. The
  architecture already charters `Facts` and `Log` as product event backbones
  (`docs/ARCHITECTURE.md:238-249`); `Log` is "durable ordered history for evals,
  labels, and audit". Operational diagnostics are a different kind and must not
  squat on that charter or that database.
- **Both span the same five processes** and are useless if per-process.

### 2.2 Where the seam genuinely falls

| | Log record | Latency mark |
| --- | --- | --- |
| Default state | always on | off |
| Rate | ~1/s | 10–60/s per pane |
| Value peaks | at a crash | during a controlled session |
| Durability need | must survive SIGKILL | may be lost on crash |
| Consumer | a human reading a file | a script computing percentiles |
| Producer in browser | none needed | the whole point |
| Third-party producers | uvicorn, mitmproxy, alembic, gateway child | none |
| Capture mechanism | fd inheritance | in-process buffer |

The last two rows are decisive.

A log substrate's coverage requirement is *other people's output*: a Python
traceback at interpreter exit, the gateway child's stdout, mitmdump's stderr. No
structured-event bus can capture those, because those processes will never call
into it. The only mechanism that captures them is a file descriptor. So the log
sink is irreducibly an fd-level artifact, and the framework is `logging` plus
`dup2`.

A trace substrate's cost requirement is *per-record cost at 60 Hz in a
renderer*. Routing that through `logging` (lock acquisition, `%`-formatting,
`isoformat()`, `json.dumps`, a synchronous write) is one to two orders of
magnitude too expensive, and in the browser there is no `logging` at all. The
browser is where the missing measurement lives, so a design that assumes the log
spine is available has excluded the one process that matters.

### 2.3 Verdict

**Separable, with one small shared piece.** Say it plainly rather than forcing a
merge:

- Shared and worth building once: a **diagnostics destination resolver** and the
  **id vocabulary** on every record.
- Not shared: the production API, the buffering strategy, the arming model, the
  file format, and the reader.

Stuart's framing — "structured events with a configurable sink, of which a log
line and a latency span are two shapes" — is right about the sink and wrong
about the shapes. They are two shapes with opposite cost and durability
requirements, and unifying the producer would make the log slower and the trace
less complete. Unifying the *destination* costs one function and buys both.

---

## 3. Design

### 3.0 Shape comparison

No existing precedent settles this, so three structurally distinct shapes.

**Shape A — live event bus.** Diagnostic events from every process ride the
existing `tm_events` NOTIFY channel and the `inspector_relay` bridge into the
backend, land in a new Postgres table, and render in the Inspector.

- For: reuses real machinery; live; one place; correlation is natural because
  Postgres already holds the ids.
- Against: the NOTIFY payload cap already forced a doorbell-and-pull design for
  inspector events (`session/inspector_relay_contracts.py:21`), and diagnostic
  volume is an order above that. Writing to the channel database on the
  measurement path perturbs the thing being measured — the incident that
  motivated `pg_stat_statements` was database saturation. It squats on the
  `Log` charter. And the cost when disabled is not zero: the plumbing is
  permanent and reaches every process. Highest blast radius, worst fit.

**Shape B — everything is a log record.** Stuart's thesis taken literally. One
emitter; a latency mark is `logger.info("mark", extra={...})`; the sink is the
file #471 makes configurable.

- For: exactly one concept; #471 subsumes measurement; nothing new to learn.
- Against: fails in the browser, which has no log spine and is where the data
  is. Fails on cost at 60 Hz. Drags always-on durability onto a hot path.
  Cannot capture the gateway child or interpreter tracebacks any better than
  today, so it does not even fully solve the log half. Inverts both cost models
  at once.

**Shape C — two producers, one destination and one vocabulary. Selected.**

- A destination resolver, one setting, channel-scoped, used by every diagnostic
  artifact including today's four log paths.
- A log spine that stays `logging` in Python and becomes the existing
  `ActivityLogger` port in Node, both writing through the resolver.
- A trace recorder, per process, off by default, ring-buffered in memory,
  flushed as NDJSON into a per-session subdirectory of the same destination.
- An offline joiner script that reduces the NDJSON set to a stage table.

- For: each half is sized to its own cost model. #471 ships alone against the
  resolver and is not rework. The trace recorder adds zero code to the log path
  and zero cost when unarmed. Deletion path is clean: remove the recorder,
  keep the resolver. No new process, no new transport, no new table.
- Against: two APIs rather than one. The joiner is offline, so there is no live
  latency view. Both are acceptable: a diagnostic session is run a handful of
  times per release, and the prior evidence workflow was already offline
  (`sample-live.py --seconds 100`, then a report).

Shape C wins because it is the only one that is honest about the browser and
about fd inheritance at the same time.

### 3.1 The shared piece: diagnostics destination

One function, one setting, one env key.

    # api/src/transport_matters/diagnostics_paths.py   (new, ~60 lines)
    def diagnostics_dir(channel: str, *, settings: Settings | None = None) -> Path
    def diagnostics_path(channel: str, name: str) -> Path

- `Settings.diagnostics_dir: Path | None = None`
  (`api/src/transport_matters/config.py`, beside `log_json`).
- `env_keys.DIAGNOSTICS_DIR = f"{ENV_PREFIX}DIAGNOSTICS_DIR"`, and while there,
  add the missing `LOG_JSON` key so the two logging settings are both named.
- Default: `<channel home>/runtime`. Today's behaviour, byte for byte.
- Resolution is channel-scoped when overridden:
  `$TRANSPORT_MATTERS_DIAGNOSTICS_DIR/<channel-id>/`, so one override does not
  collapse three channels' logs into one file. This mirrors the existing home
  rule in `env_keys.py:18-23` for `TRANSPORT_MATTERS_HOME`.

Every existing diagnostic path moves onto it:

| Today | Under the design |
| --- | --- |
| `desktop_runtime.desktop_log_path` (`:161`) | `diagnostics_path(channel, "desktop.log")` |
| `shared_proxy/process.py:83` | `diagnostics_path(channel, "shared-mitmdump.log")` |
| `cli/runner.py:121` | per-run; stays under the run's storage, unchanged |
| trace NDJSON (new) | `diagnostics_dir(channel) / "trace" / <session>/` |

The per-run mitmdump log deliberately stays with its run: it is run evidence,
not channel diagnostics, and moving it would break run bundles.

### 3.2 Event shape

Two record kinds, one envelope. NDJSON, one file per process per session.

    {"k":"mark","t":1757289981.1234,"m":91234.5678,"p":"renderer",
     "n":"term.out.parsed","id":{"run":"…","attach":"…","seq":18342},"v":{}}

    {"k":"note","t":…,"m":…,"p":"gateway","n":"attachment.overloaded",
     "id":{"run":"…","attach":"…"},"v":{"queued":512}}

- `t` — wall clock seconds, float. The **only** cross-process join axis.
- `m` — process-monotonic milliseconds. The only axis used for durations
  *within* one process.
- `p` — process tag: `renderer` | `backend` | `gateway` | `proxy` | `electron`.
- `n` — event name, a closed vocabulary declared in one shared table (mirroring
  the `ir_coverage_tables` pattern: a declared table, not free strings).
- `id` — a subset of §1.7. Absent keys mean "not applicable", never "unknown".
- `v` — small scalars only. No bodies, no user text, no headers. This is a
  hard boundary, not a convention: the redaction rules that govern
  `transport_redaction` exist because diagnostic surfaces leak.

No `span` kind. Spans imply a parent/child tree this system does not have and
would have to invent. Two marks and a subtraction are honest; a span is a
promise about causality the recorder cannot keep across a WebSocket.

**Clock rule.** Everything is on one host, so `CLOCK_REALTIME` is the common
domain and is sub-millisecond stable within a host. Each process therefore emits
both readings at every mark; the joiner uses `t`, and any within-process
duration uses `m`. The renderer's wall reading is
`performance.timeOrigin + performance.now()`. Cross-host is out of scope; every
hop here is loopback.

### 3.3 Where marks are produced

All at seams that already exist. No new call graphs.

| Process | File and line | Marks |
| --- | --- | --- |
| renderer | `terminalSocket.ts:142` (onData), `:109` (send) | `term.in.key`, `term.in.send` |
| renderer | `terminalSocket.ts:138-139` (onmessage) | `term.out.recv` |
| renderer | `terminalSession.ts` via `term.write(data, cb)` | `term.out.parsed` |
| renderer | rAF after the parse callback | `term.out.frame` |
| backend | `run_proxy._downstream_to_upstream` | `bridge.up` |
| backend | `run_proxy._upstream_to_downstream` | `bridge.down` |
| gateway | `runTerminalConnection.ts:87-90` | `pty.in.recv` |
| gateway | `RunManager.ts:364` / `NodePtyAdapter.ts:158` | `pty.in.write` |
| gateway | `TerminalFanout.ts:206` | already stamped: reuse `seq`/`emittedAt` |
| gateway | `attachmentPump.ts:47-49` | `pty.out.send` (carries `seq`) |

`attachmentPump` is the important one. It currently drops `seq` and `emittedAt`
one line before the socket. The recorder reads them instead of re-deriving
anything.

The mitmproxy subprocess is **not** on this path. The same recorder serves it
later for provider latency (marks around `request_pipeline` and the first
response byte), which is how `wire_exchange` would finally get a TTFB it does
not have today (§1.5). Out of scope here; the shape supports it.

### 3.4 Crossing the process boundaries

The system has five boundaries. Each is handled by an existing mechanism.

1. **Browser to Python (WS).** The browser mints `attachmentId` and puts it in
   the socket URL. `run_proxy` forwards the query verbatim (verified, §1.8).
   One line in `terminalSocket.ts:85`.
2. **Python to gateway (WS).** Same query, already forwarded. The gateway route
   reads `attach` and passes it into `AttachTerminalInput.attachmentId`, a
   parameter that already exists and is currently always undefined
   (`runManagerTypes.ts:66`). One line in `runTerminalConnection.ts`.
3. **Gateway to PTY.** `seq` already exists; nothing to add.
4. **Downstream frames to the browser.** The **ordinal join** (§1.8), not an
   in-band marker: the browser counts binary frames after
   `run.terminal.scrollback-end` and maps ordinal k to `startSeq + k`. The
   gateway reports `startSeq` once, in the existing `run.terminal.ready` frame,
   as one new field. This is why the sketched "sequence-marked shared terminal
   path" cannot be in-band and does not need to be.
5. **Renderer to Electron main.** Only needed for the CDP trace, and the
   existing bridge already carries it: one message kind on
   `BROWSER_PANE_CHANNEL` (`desktop/src/bridgeKeys.cts`), or nothing at all if
   the trace is started from the main process by the CLI. Prefer the latter: the
   renderer should not be able to start a whole-app trace.

The renderer writes its NDJSON by POSTing its flushed buffer to the backend at
session end. It is same-origin — the renderer loads from the backend's port
(`desktop/src/rendererUrl.ts`), so no CORS, no IPC, no new transport. One
endpoint, `POST /api/v1/diagnostics/trace/{session}`, accepting NDJSON, writing
into the session directory. Bounded body size, rejected when no session is
armed.

### 3.5 Sinks and configuration

    <diagnostics_dir>/<channel>/
      desktop.log                       # today's file, now relocatable
      shared-mitmdump.log
      trace/
        2026-09-08T14-02-11Z-a3f9/
          renderer.ndjson
          backend.ndjson
          gateway.ndjson
          manifest.json                 # session id, channel, commit, versions, ids
          report.md                     # produced by the joiner

`manifest.json` records what the prior evidence report recorded by hand: commit,
version, PIDs, ports, clean-tree assertion. That report
(`tm-preview-live-performance-evidence/report.md`) is the specification for what
a session must capture; the manifest makes it mechanical.

### 3.6 Arming, and cost when disabled

**Arming.** One env var naming the session directory:
`TRANSPORT_MATTERS_DIAG_SESSION=<absolute path>`. Present at process start means
armed. Absent means the recorder module never allocates a buffer and every emit
site is a single predicted branch.

The renderer cannot read env. It reads a flag once at pane mount from a small
endpoint (`GET /api/v1/diagnostics/session` returning `{"session": null | "…"}`)
and again on socket reconnect.

First increment: arming requires a backend restart, which is exactly how the
prior evidence sessions worked. Live arming by CLI (`transport-matters diagnose
trace --seconds 60`) is a later refinement and needs a way to reach already
mounted panes; do not build it before the restart-based version has proved
useful.

**Cost when disabled.**

- TypeScript: `if (!DIAG) return;` against a module-level const. Monomorphic,
  perfectly predicted, inlinable.
- Python: `if _RECORDER is None: return`. Same.
- No formatting, no allocation, no timestamp read on the disabled path. The
  timestamp read must be *inside* the guard — `performance.now()` is cheap but
  not free at 60 Hz across several sites.

The strongest evidence of zero cost is absence, not a benchmark: with the env
unset, assert the session directory is never created and the recorder's buffer
is never allocated, and show the round-trip medians are within noise of the
uninstrumented build (§5).

### 3.7 The renderer-local probe, which comes first

Independent of everything above, and the reason to reorder the work.

The prior evidence bounds backend at 1.307 ms median / 2.670 ms p95 and the PTY
reply at 0.847 ms median. If key-to-pixel is perceptibly slow, the remainder is
inside the renderer. A probe that lives entirely in `terminalSession.ts` and
`terminalSocket.ts`, using `performance.now()` and no cross-process anything,
partitions the budget into four numbers:

1. keydown to `socket.send`
2. `socket.send` to `onmessage` (the whole round trip, server included)
3. `onmessage` to xterm's write callback (parse)
4. write callback to the next rAF, and separately to the following
   `PerformanceObserver` `event` entry (paint)

Stage 4 is where the honesty is required. `term.write(data, cb)` fires when the
parser has consumed the bytes — already used at `terminalSession.ts:214` for
exactly this ordering reason. It is **not** paint. The next rAF is "the frame
that contained this render was scheduled", still not presentation. Actual
presentation has exactly two credible sources on this stack: the Event Timing
API (`PerformanceObserver` on `event`, whose `duration` reaches the presented
frame but is quantised to 8 ms and only anchors on the input event), and
Chromium tracing over CDP. Say which one produced each number in any report.

If this probe shows stage 4 dominating, the answer is the CDP trace (§3.8), not
a cross-process substrate. If it shows stage 2 dominating beyond the 1.3 ms the
backend already accounts for, then the cross-process substrate earns its keep.
Either way the next step is decided by evidence rather than by a guess about
where the bottleneck is.

The dead `getStats()` (`createAmbientBackground.ts:257`) becomes this probe's
frame-rate source instead of being deleted: it already maintains fps and
frame-time EMAs and needs a consumer.

### 3.8 The deep instrument

For "why is the renderer hop slow", the answer is Chromium's own tracer, not a
homegrown one. Two routes, both in-pattern:

- **Extend the existing CDP front** (`desktop/src/browserPaneDevtoolsFront.ts`)
  to register the canvas renderer's `webContents` under its own target, gated by
  the same Director capability that already governs pane attachment
  (`api/v1/devtools_access.py`). This gives `Tracing.*`, `Performance.*` and
  `Runtime.*` on the renderer with no new process, no new auth model, and the
  existing origin-binding guarantee intact.
- **`contentTracing`** in the Electron main process, started and stopped by a
  CLI command, writing a Chromium trace into the session directory. Whole-app,
  including GPU and compositor threads, which the per-renderer CDP session does
  not fully cover.

Prefer the CDP extension first: it reuses a built, reviewed, capability-gated
surface. Add `contentTracing` only if the compositor and GPU threads turn out to
matter. I could not verify `contentTracing` behaviour in this app's packaging;
no code exercises it today.

Both are opt-in, both write into the same session directory, and neither is
correlated with the marks. That is fine and should be stated: the marks localise
the hop, the trace explains it.

---

## 4. What #471 becomes, and can it ship first

Yes, standalone, and the larger design subsumes it with no rework because the
larger design's only claim on it is the resolver.

### Increment 1 (ships alone)

1. `Settings.diagnostics_dir`, `env_keys.DIAGNOSTICS_DIR`, `env_keys.LOG_JSON`.
2. New `diagnostics_paths.py` with `diagnostics_dir` / `diagnostics_path`.
3. `desktop_log_path` deleted; all six callers migrated to
   `diagnostics_path(channel, "desktop.log")` in the same change. No adapter, no
   deprecation window — the DRY rule in CLAUDE.md is explicit about this.
   `DesktopRuntimeRecord.log_path` already carries the resolved path, so
   `tail` on a *running* desktop can read the record rather than re-deriving,
   which also fixes the case where the destination changed between launch and
   tail. That is a genuine improvement the issue does not ask for and should be
   taken while the code is open.
4. `shared_proxy/process.py:83` moves onto the resolver.
5. `--foreground` persistence, done at fd level.

### The foreground mechanism, specifically

Not a `FileHandler`. Parity with the detached log requires the same fd-level
coverage (§1.2), so:

- Before uvicorn starts, `os.pipe()`; `dup2` the read end's counterpart over
  fd 1 and fd 2; hold the original fds; run a daemon drain thread that reads
  the pipe and writes each chunk to **both** the saved original fd and the log
  file, flushing per chunk.
- The gateway child then inherits the redirected fds and lands in the same file,
  exactly as detached does.
- Line-oriented flush keeps the loss window on SIGKILL to at most a partial
  line. State that boundary; do not claim crash-proof.
- Roughly 40 lines, and directly testable: write to fd 2 from a subprocess,
  assert both the tty capture and the file received it.

Alternative considered and rejected: re-exec under `tee`. It works, but it
complicates the PTY and signal handling that `supervisor/core.py:138-167`
already gets right, and it makes `--foreground` behave differently from every
other foreground path in the CLI.

### Retention, which the issue does not mention

Once the destination can live outside the channel home, the wipe stops being the
retention policy and the file grows without bound across restarts. Add a
size-capped rotation (default 32 MB, keep 3) in the same change. Without it,
#471 trades one operational problem for another.

### Acceptance, restated against the issue

- Foreground run produces a readable log file: yes, fd-level, including the
  gateway child.
- Destination outside the home survives a wipe: yes;
  `reset-channel-store.sh` derives paths from the app's own channel resolution
  (`scripts/reset-channel-store.sh:32-35`), so it will not sweep a directory the
  resolver reports as outside `STORAGE_ROOT`. Worth an explicit test, since that
  script's guardrail is "unexpected shapes abort".
- `tail` resolves the same path: yes, through the resolver and preferentially
  through the runtime record.

### Increment 2 (later, independent)

Renderer-local probe (§3.7). No backend change, no new endpoint, no id plumbing.
Answers where the desktop bottleneck is.

### Increment 3 (only if increment 2 points outward)

Trace recorder, `attachmentId` plumbing, ordinal join, NDJSON sink, joiner
script.

### Increment 4 (only if increment 2 points inward)

CDP registration of the renderer target (§3.8).

---

## 5. Proving it

### 5.1 That the instrumentation is correct

Attribution is the property that matters, and it is the one nobody tests.

1. **Synthetic hop injection.** Behind a test-only env var, insert a
   deterministic 25 ms delay at one named hop. Assert the joined report
   attributes ~25 ms to that hop and leaves its neighbours unchanged. Repeat per
   hop. This is the only real proof that a stage boundary is where the code
   claims it is.
2. **Ordinal-join invariant.** A gateway test that appends N chunks and asserts
   the socket received exactly N binary sends in order (`attachmentPump`), and a
   Python test that the WS bridge forwards N frames as N frames with types
   preserved (`run_proxy._upstream_to_downstream`). The join is unsound without
   both; today neither is pinned.
3. **Clock-domain bound.** Assert every record carries both `t` and `m`, and
   that within one process `|Δt − Δm|` stays under a stated bound across a
   session. A violation means the wall clock stepped and the join is suspect.
4. **Conservation.** The sum of hop durations must reconcile with the
   end-to-end round trip. Report the residual as a number in every session
   report rather than letting it hide inside a stage.
5. **Vocabulary totality.** Event names come from one declared table, checked by
   a test, following the `ir_coverage_tables` precedent. An undeclared name is a
   test failure, not a silent record.

### 5.2 That disabled overhead is negligible

1. **Absence.** With the env unset: the session directory is never created, the
   recorder buffer is never allocated, and the diagnostics endpoint returns
   `{"session": null}`. Assert all three.
2. **Round-trip parity.** Run the existing raw-mode PTY probe with the recorder
   code present-and-disabled and compare against the pre-change build. Report
   both medians and p95s, not a pass/fail.
3. **Frame parity.** Renderer: assert `getStats().fps` is unchanged within noise
   over a fixed workload with the probe disabled.

### 5.3 Reuse the harness that already exists

`/Users/alphab/.mdx/sessions/tm-preview-live-performance-evidence/` holds
`probe-pty.py`, `sample-live.py`, `audit-replay.py`, and `probe-watch.py`. These
are the repo's only real measurement harness and they are **outside version
control**, with observed ports and PIDs baked in (the report says so explicitly).

Move them to `scripts/perf/` with runtime discovery replacing the hardcoded
ports, and make the joiner a sibling. This is the lever CLAUDE.md asks for: the
next performance session should be a command, not a re-derivation. It is also
strictly DRY — writing a new sampler beside these would be the duplication the
project has zero tolerance for.

---

## 6. Migration and deletion

Replaced and deleted in the same change as their replacement:

| Deleted | Reason |
| --- | --- |
| `desktop_runtime.desktop_log_path` (`:161`) and `_LOG_FILENAME` (`:33`) | superseded by the resolver; six callers migrated |
| `logging.py:20-21` `request_id` branch | dead: zero producers repo-wide |
| `shared_proxy/subprocess.py:290` `logging.basicConfig` | replaced by the shared config so the subprocess honours `log_json` and level |

Kept but given a consumer:

| Kept | Change |
| --- | --- |
| `createAmbientBackground.getStats()` (`:257`) and `ambient/types.ts:89` | currently dead; becomes the renderer probe's frame source |
| `ActivityTelemetry` (`packages/activity/src/telemetry.ts`) | its `ActivityLogger` port (`:7`) becomes the Node log port; `snapshot()` gets the doctor surface it was written for |
| `TerminalFanout` `seq`/`emittedAt` (`:31,:33`) | stop discarding them in `attachmentPump.ts:47` |
| `AttachTerminalInput.attachmentId` (`:168`) | stop leaving it undefined |

Tidied while open: `LOGGER` versus `logger` module constants across
`shared_proxy/*` and the rest.

No parallel implementation and no adapter. Every migration above is a rename
with a countable caller list.

---

## 7. What I could not verify

- **The actual desktop paint latency.** Unmeasured. Every statement in this
  document about where the bottleneck sits is a hypothesis derived from the
  server-side bounds in the prior evidence, not an observation. §3.7 exists
  precisely to settle it.
- **`contentTracing` in this app's packaging.** No code exercises it; I did not
  run Electron. The CDP route is verified as a code path but not exercised
  against the main window.
- **Whether xterm's write callback lands before or after its render pass** in
  the pinned version. `terminalSession.ts:214` uses it as an ordering barrier
  for resize, which implies parse-complete, but I did not read the xterm source.
  Stage 3 versus stage 4 attribution depends on this.
- **WebSocket message fragmentation.** I verified message-level 1:1 forwarding
  in `run_proxy`. Both `starlette` and `websockets` reassemble fragments into
  whole messages before delivery, so ordinal parity should hold, but I did not
  test it under frames large enough to fragment. Test 5.1.2 covers it.
- **Whether `ActivityTelemetry.snapshot()` has any HTTP surface.** I found no
  reader; I did not exhaustively search the gateway route tree.
- **`pg_stat_statements` availability** on any non-compose Postgres. The
  migration comment says a managed role may lack the privilege.
