# TM first run: scout and proposal

Date: 2026-08-04. Seat: opus. Read-only; tree untouched.

Symbols are cited `path::SYMBOL`. Numbers come from real captured runs under
`~/.transport-matters/workspaces/`, not estimates.

---

# Part 1 — Scout

## 1.0 What a first-time user sees today

The desktop shell loads `/canvas` (`desktop/src/main.ts`, asserted in
`desktop/src/main.test.ts`); the web origin `/` serves the Inspector bundle
(`main.py::mount_frontend_bundles`).

On `/canvas` a first-time user gets: an empty zero-chrome canvas, and a faint
`⌘K to command` hint that fades after 6.5s and never returns
(`canvas/src/launcher/FirstRunHint.tsx::FirstRunHint`). If infrastructure is
broken, a non-blocking banner appears above it
(`workbench/SessionCanvasRoute.tsx::SessionCanvasRoute` → `routeAlert`).

That is the entire first run. **There is no journey, no capture, no reveal.**
The word "firstrun" names a module, not a flow.

## 1.1 Step 1 — install

Nothing to scout.

## 1.2 Step 2 — run, creates state silently, asks nothing

**EXISTS.** `config.py::ensure_settings_scaffold` writes
`~/.transport-matters/settings.toml` from the packaged template on first run.
Channel homes are created per channel.

**GAP: the database is not silent.** `config.py::resolve_database_url` raises
`config.py::MissingDatabaseConfigError` when neither
`TRANSPORT_MATTERS_DATABASE_URL` nor `settings.toml`'s `database.url` is set.
The browser can only *read* that failure as
`LaunchReadinessCheck{id:"session_store"}` and render the server's copy-paste
shell guidance (`infrastructure_guidance.py::session_store_unavailable_remediation`).
**NONE FOUND:** any UI that configures a connection string, any route that
performs infrastructure repair. Searched `grep -rni "database_url|databaseUrl|
connection string|postgres" www/packages` (zero non-test hits) and every
`@router.post|put` under `api/v1/`. NOW.md's docker / BYO-string / managed
picker is unbuilt.

## 1.3 Step 3 — detect installed, authed, responsive harnesses

**EXISTS, and better than the UI currently uses.**

One route already answers the whole question, live, per request:
`GET /v1/launch-readiness` → `api/v1/launch_readiness.py::get_launch_readiness`
→ `captured/readiness.py::launch_readiness`. Per launch-eligible descriptor it
emits three checks (`readiness.py::_harness_checks`):

| check id | source | means |
|---|---|---|
| `{h}_enablement` | `harnesses/enablement_store.py::HarnessEnablementStore` | operator intent |
| `{h}_binary` | `readiness.py::_client_binary_check` → `shutil.which` | installed; code `harness_not_installed` |
| `{h}_credential` | `readiness.py::_credential_check` | **authed** |

The credential check calls the canonical predicate,
`credential_source.py::harness_credential_error` (returns `None` when ready).
This is the seam NOW.md names, not probe output. Installed-but-not-authed is
therefore exactly `{h}_binary.ready && !{h}_credential.ready`, distinguishable
from absent today.

It is registry-driven: `readiness.py::_harness_checks` iterates
`harnesses/__init__.py::list_launch_eligible_descriptors()`. No name branch.

**The defect: the first-run UI throws this away.**
`firstrun/FirstRunScreen.tsx::infrastructureFailures` filters to
`!check.ready && check.harness_id === null`. Every harness-scoped check is
discarded, and only *failures* survive. The harness cards render a second,
weaker source instead — `GET /v1/harnesses` →
`harnesses/inventory.py::harness_inventory`, whose auth fact is dated probe
evidence. Its own code says so: `firstrun/harnessCards.ts::authenticatedFact`
carries "Probe outcomes never gate a launch … the credential predicate that
will feed this fact directly is PR#352's seam", and the screen footnote reads
"Authentication reflects the last stored probe. It reports; it never gates."

So step 3's correct data is already on the wire and unrendered.

**Cost note.** `capabilities.py::detect_harnesses` shells out
(`subprocess.run([path,"--version"])`, `DEFAULT_VERSION_TIMEOUT_S = 2.0`) and is
uncached. Readiness does not call it; `GET /v1/agents` does.

**Where it is rendered:** the harness cards live inside the ⌘K palette under the
`settings` scope with an empty query (`launcher/CommandCenter.tsx`). A settings
panel, not a journey.

## 1.4 Step 4 — capture a first turn

**EXISTS in full. Nothing new is needed to make a turn happen.**

- Seam: `captured/run.py::prepare_captured_run` → `(CapturedRunSpawnSpec,
  CapturedRunLease)`. It starts mitmdump; the caller spawns `spec.client.argv`.
- Startup prompt: `captured/models.py::CapturedRunRequest.initial_prompt`,
  paired with `delivery_id`
  (`api/v1/capture_rpc_routes.py::PrepareCaptureRequest.paired_initial_prompt`).
  Argv assembly at `cli/launch_profile.py::_initial_prompt_argv`.
- Control-plane verb: `controlplane/service.py::ControlPlaneService.launch(...,
  first_prompt=...)` → `controlplane/launch_service.py`, returning
  `controlplane/run_models.py::LaunchResult.first_prompt: PromptReceipt`. The
  field's own description: *"Optional native startup prompt. Omission preserves
  interactive startup."* This is API-first by construction — the director can
  call the same verb.
- Pane path: `canvas/src/model/canvasActions.ts::spawnCapturedRunPane` →
  `capturedRunStore.ts::ensureRun` → `POST /v1/runs` →
  `api/v1/run_proxy.py::RunProxy.forward_http` →
  `runtime/src/server/runtimeRouter.ts` →
  `runtime/src/service/RunManager.ts::RunManager.createNew` →
  `CaptureRpcClient.prepareCapture` → `prepare_captured_run` →
  `runtime/src/adapters/NodePtyAdapter.ts::NodePtyAdapter.spawn`. Terminal over
  WS: `runtime/src/server/runTerminalConnection.ts::handleRunTerminalConnection`,
  protocol in `packages/common/src/terminalContract.ts`.

**Interactive is free.** There is no print mode in the seam. `-p` is reachable
only through `CapturedRunRequest.passthrough`, which nothing in canvas or the
gateway populates (`RunManager.createNew` never sets it). The downstream stack
assumes a TUI: `runtime/src/domain/tuiReadiness.ts::TuiReadinessScanner` latches
on the harness's OSC-0 composer title. The brief's hardest constraint costs zero.

**Canvas runs are never armed — confirmed.**
`RunManager.register` sets `view.state = "RUNNING"` unconditionally once
`ptyPort.spawn` resolves, and `runtime/src/domain/runtimeRun.ts::RuntimeRunState`
has no armed/paused member. The breakpoint (`api/v1/breakpoint_routes.py::arm_breakpoint`)
is a global proxy-flow gate driven only from `www/packages/inspector/src/api.ts`.

## 1.5 Step 5 — the reveal

**The data EXISTS and is already computed at capture time. The screen does not.**

Every exchange writes `entry.json` beside its bytes
(`storage/disk_helpers.py`, models `storage/base.py::ReqStats` / `::ResStats` /
`::PipelineStats`, built by `exchange_recorder/stats.py::build_req_stats` /
`::build_res_stats`). A real first turn from this machine, run
`d4e6d372…`, exchange `e1de0139…`, Claude Code 2.1.221, sonnet-5, prompt
`Reply exactly TM_PRINT_COMPARE_OK.`:

```
system      32,997 chars   25.8%   (3 parts; part 2 alone is 32,870)
tools       68,357 chars   53.5%   (22 tools)
messages    26,523 chars   20.7%
  of which the user's own words:  34 chars   0.027%
total      127,877 chars
tokens_before 45,687   (count_tokens estimate)
provider-billed input, turn 1: 45,649
  = input_tokens 2 + cache_creation 45,647 + cache_read 0
```

Two facts worth the whole product:

- **Tool schemas are the largest block, larger than the system prompt.** 53.5%.
- **20,983 of those 68,357 tool chars (16.4% of the entire payload) are one MCP
  server the user installed themselves.** No hosted reference matrix can know
  that. This is why the reveal must be a capture.

**Rendering already exists — in the Inspector, which canvas may not import.**
`inspector/src/components/detail/TokenBar.tsx::TokenBar` (the proportional
cache-read / cache-write / input bar, denominator
`www/packages/core/src/formatting.ts::contextTokens`),
`editor/SystemSection.tsx::SystemPartRow` (indexed parts with char counts),
`editor/ToolsSection.tsx::ToolsSection` (count, per-group chars, per-tool
`lib/charAccounting.ts::toolChars`). Per-turn aggregates exist at
`ExchangeTurnCard.tsx::panelMetrics` and `ExchangeDetail.tsx::tabReadout`.

Constraint: `www/packages/canvas/CLAUDE.md` — canvas **never imports
`@tm/inspector`**, enforced by an import-graph test and a dep-lint test; the
Ark fork `viewers/resource/ArkExchangeViewer.tsx` is the locked decision. So a
canvas reveal reuses the *data contract*, not those components.

**NONE FOUND:** cost in dollars anywhere (searched `usd|dollar|price_per|
per_million` across `www/`, `api/src` — zero). No whole-run or whole-workspace
aggregate in the Inspector. Empty state today is
`inspector/src/routeLayout.tsx::WaitingScreen` ("Waiting for exchanges").

**Codex caveat.** `pipeline.tokens_before` is `null` for every codex entry:
`counting.py::TokenCounter` posts to `api.anthropic.com/v1/messages/count_tokens`.
Chars are harness-general; the *pre-flight* token estimate is Anthropic-only.
Provider-billed usage in `ResStats` exists for both (a sampled codex turn:
`input_tokens 15,107`, `cache_read 9,984`). **Any harness-general headline must
come from the response, not the estimate.**

## 1.6 The overlay's honest state

The brief's premise "the run-scoped OverrideStore is never populated" is
**refuted**. `overrides/state.py::OverrideStore` is scoped by `(run_id,
track_id)` and is written on every editor edit:
`inspector/src/components/editor/BreakpointEditorActions.ts::useBreakpointEditorActions`
→ `PATCH /api/overrides?run_id&track_id` → `api/v1/overrides.py::patch_overrides`
→ `store.upsert(scope)` → forwarded to the proxy process via
`api/v1/overrides.py::_sync_shared_overrides` →
`shared_proxy/subprocess.py::set_overrides`. Reapplied to every later turn by
`request_pipeline.py::run_pipeline` → `overrides/__init__.py::apply_overrides`;
`release_flow` never clears it. Pinned by
`api/v1/test_overrides_shared_proxy.py::test_patch_for_registered_run_forwards_snapshot`.

What is genuinely absent, and what bounds the first-run promise:

1. **Nothing is applied before turn 1.** Both descriptors declare
   `HarnessCapabilities(overlay_before_work=False)`
   (`harnesses/__init__.py::_CLAUDE_DESCRIPTOR`, `::_CODEX_DESCRIPTOR`). Both
   declare `tool_schema_overlay=True` — the 53% block is editable, from turn 2.
2. **Nothing persists across runs.** The store is two in-memory dicts; `grep -rniE
   "overlay|override" api/migrations` → zero tables. The Overlays view is
   localStorage-only and never reaches the backend — `stores/overlaysStore.ts`
   states "The apply-at-intercept pipeline … arrive in later slices".

**So the honest first-run promise is: see it now, edit it from the next turn of
this run. Not "TM takes over".** Saying more than that would be a lie the code
can falsify today.

## 1.7 What "nothing hardcoded" costs today

The registry is real and good: `harnesses/__init__.py::HarnessDescriptor` +
`::HarnessLaunchBoundary` + `::HarnessCapabilities`, accessors
`::list_launch_eligible_descriptors` etc., mirrored to
`shared/harness_descriptors_v1.json` with conformance tests. Adding a harness
*should* be one descriptor plus adapters.

It is not, yet. Six closed unions duplicate the registry and each needs a hand
edit: `harnesses/__init__.py::HarnessId`, `captured/models.py::CapturedRunHarness`,
`controlplane/run_models.py::LaunchHarness`, `runtime_templates.py::RuntimeTemplateHarness`,
`activity/src/adapters/harnessRegistry.ts::HARNESSES`,
`www/packages/core/src/types/capabilities.ts::HarnessId`. Plus name branches on
the journey's own path, including
`runtimeRouter.ts` (`harness === "claude" || harness === "codex"`, and
`DEFAULT_HARNESS = "claude"`), `BrowserPtyEnvironment.ts`, `tuiReadiness.ts`,
`canvas/src/model/paneRecords.ts::isHarnessName`, and
`harnesses/compatibility_store.py::INSTALLED_ADAPTER_REVISIONS` (hardcodes
`for harness in ("claude","codex")`, so a new harness silently gets none).

**This is the biggest structural gap the journey exposes, and it is orthogonal
to first run.** Do not fix it inside a first-run slice.

## 1.8 The login driver

**NONE FOUND.** No code spawns `claude auth login` or `codex login`. Searched
`loginDriver|LoginDriver|login_driver|startLogin|runLogin|authLogin` (0 hits),
and every non-test `login` occurrence is either a display string
(`credential_source.py::_CREDENTIAL_PROFILES[*].login_command`,
`claude_fleet_auth.py::CLAUDE_FLEET_BOOTSTRAP_COMMAND`) or the read-only codex
status probe (`harnesses/probes/codex.py::AUTHENTICATION_PROBE`, argv
`("login","status")`).

Today the product prints the command and asks the user to type it:
`FirstRunScreen.tsx::CardView` renders "Run `<command>` to sign in." That is the
one place first run currently violates NOW.md §1.3 ("TM runs any command TM can
run. The user is never asked to type one").

**The seam NOW.md specifies already exists.**
`runtime/src/service/PlainTerminalSessions.ts::PlainTerminalSessions` is a
non-captured PTY composition on the gateway — its own docstring: *"Deliberately
NOT runs: no capture lease, no lifecycle, no owner or REST surface — one
WebSocket owns one shell."* It spawns through the same
`runtime/src/ports.ts::PtyPort` and reuses `TerminalFanout` for backpressure.
Wired browser-side at `ws://…/api/terminal` →
`run_proxy.py::RunProxy.forward_plain_terminal` →
`server/plainTerminalConnection.ts::handlePlainTerminalConnection`.
A login driver is that composition with `argv = login_command` and completion on
`PtySession.onExit`, then re-read `harness_credential_error`. Exactly what §1.3
describes, and it does not touch `RunManager` or `cli/`.

---

# Part 2 — Proposals

## Proposal A — The first turn is the product (recommended)

One screen, one button, one number. Everything below binds to a symbol that
exists, except where marked NEW.

### Screens, in order

**0. Nothing.** App opens on `/canvas`. `useLaunchReadiness` already runs. If
infrastructure fails, the existing banner and its server-owned remediation
appear, unchanged. This is the re-entrant gate NOW.md asks for and it already
ships.

**1. "See what your agent sends."** Shown when the workspace has zero
exchanges. It lists every launch-eligible harness *from the readiness checks
already on the wire* — not from the probe inventory — as one line each:

- `{h}_binary.ready && {h}_credential.ready` → "Claude Code · ready"
- binary ready, credential not → "Claude Code · sign in" + a button that spawns
  `login_command` in a pane (NEW, §1.8 seam)
- binary not ready → "Codex · not installed", greyed, no error tone
  (`readiness.py` already treats zero harnesses as `ready=True`)

**The user does nothing.** One primary button: *Show me*. No toggles, no
harness picker, no model picker. TM picks every ready harness.

**2. The capture.** For each ready harness, in sequence, TM launches a captured
run into a visible canvas pane with `initial_prompt` set to a trivial fixed
prompt. The pane is *framed*, not hidden: "Claude Code is starting in your
project. Answer anything it asks." The harness's own trust dialog renders in the
pane because the pane is a real PTY. A spinner over a hidden terminal is what
would look broken.

**3. The reveal.** Fires on the first `entry.json` for the run.

> **You typed 34 characters. Claude Code sent 45,649 tokens before it answered.**
>
> Tools 53% · System prompt 26% · Context 21% · Your words 0.03%
>
> The largest single block is your own MCP server: 10 tool schemas, 20,983
> characters, 16% of everything sent.

Then the itemization, and one honest call to action: **Edit the next turn** →
arms the breakpoint on this run. Not "apply an overlay".

### The single number

**Provider-billed input tokens on turn one**, from `ResStats`:
`input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. This is
already the definition of `www/packages/core/src/formatting.ts::contextTokens`.

Chosen over `pipeline.tokens_before` because that is `null` for codex
(`counting.py` is Anthropic-only) and because billed usage is provider truth,
not an estimate. The char split beside it is harness-general and free.

### Binds to

`GET /v1/launch-readiness` · `readiness.py::launch_readiness` ·
`credential_source.py::harness_credential_error` ·
`harnesses/__init__.py::list_launch_eligible_descriptors` ·
`ControlPlaneService.launch(first_prompt=)` or `POST /v1/runs` +
`CapturedRunRequest.initial_prompt` · `captured/run.py::prepare_captured_run` ·
`RunManager.createNew` · `NodePtyAdapter` · `storage/base.py::ReqStats`/`::ResStats` ·
`core/src/formatting.ts::contextTokens` · `breakpoint_routes.py::arm_breakpoint` ·
`RunInputDelivery.ts::RunInputReadinessGate`.

### Genuinely new

1. One canvas screen sequencing the above, driven by the readiness payload.
   Small: `FirstRunScreen` already renders a check list; this renders the checks
   it currently discards, plus a button.
2. The reveal card. Data exists; canvas cannot import the Inspector's components
   (locked), so it reuses the contract via the `ArkExchangeViewer` lineage.
3. The login driver, `PlainTerminalSessions` composed with `login_command`.
4. A "zero exchanges in this workspace" trigger.

### Smallest testable first slice

**The reveal card alone, over existing captured history.** No launcher, no
login driver, no journey. One card in canvas that takes the newest exchange in
the workspace and renders the headline plus the three-way split. Testable today
against 426 `entry.json` files already on this machine.

If that number does not make a user lean in, nothing downstream is worth
building. Ship it first for that reason, not because it is easy.

## Proposal B — Comparison first

Same spine, but capture *every* ready harness before revealing anything, and
lead with the difference: "Claude Code sends 45,649 tokens. Codex sends 25,091.
Same prompt."

Costs: doubles time-to-value, doubles the number of harness dialogs the user
must answer, and needs both harnesses authed to say anything at all. Forecloses
nothing.

Weaker as a *first* reveal: a comparison presumes the reader already has a sense
of scale. 45,649 tokens for 34 characters is shocking with no baseline; "45,649
vs 25,091" invites the reader to pick a side instead of seeing the problem.

**Verdict: build it, second.** It is Proposal A's loop with the reveal deferred
to the end, so it costs one flag once A ships.

## Proposal C — Reveal without capturing (rejected)

Show the payload from the hosted reference matrix, so the reveal is instant and
needs no launch, no dialog, no auth.

Rejected on evidence. The matrix is unbuilt and deferred (NOW.md, "The reference
matrix, hosted"). More importantly it would be *wrong for the user who is
looking at it*: in the measured turn, 20,983 of 68,357 tool characters belong to
an MCP server that user installed. A reference figure would undercount them by
roughly a sixth and would never surface the one block they can actually act on.

"Here is what your agent is actually sending" is the product. A generic number
is a different, weaker product.

---

## The four questions, answered

**One authed harness versus many.** Same flow, with a loop over the readiness
checks — the loop *is* the flow, and at N=1 nothing about the screens changes.
Capture **sequentially**, never in parallel: each harness may raise its own
dialog, and two at once is the broken screen. The reveal takes N rows and leads
with the largest.

**Where the harness's own dialog appears.** In the pane, because the pane is a
real PTY (`NodePtyAdapter` → `TerminalEmulator` → xterm). It does not look
broken if TM says beforehand what is about to happen and keeps the terminal
visible. TM already distinguishes "spawned" from "ready for input" —
`tuiReadiness.ts::TuiReadinessScanner` latches on the composer title and
`RunInputDelivery.ts::RunInputReadinessGate` holds delivery until then — so the
trivial prompt is not sent until the dialog is answered. Nothing new.

**Installed but not authed, slow, or absent.**
*Absent*: `{h}_binary` fails with `harness_not_installed`; render as a neutral
fact, never a failure. Zero harnesses is already `ready=True` in
`readiness.py::launch_readiness` and the copy for it already exists
(`FirstRunScreen.tsx::SUMMARY_NOTES.none_installed`).
*Installed, not authed*: `{h}_credential` fails. The only place first run asks
for anything. Today it prints a command string, which violates NOW.md §1.3; the
fix is the login driver over the existing `PlainTerminalSessions` seam.
*Slow*: readiness is a `which` plus a file stat and is fast. The **capture** is
slow — a model round trip. So the reveal is asynchronous and the pane is what
the user watches meanwhile. Never block on it.

**The reveal's headline.** *"You typed 34 characters. Claude Code sent 45,649
tokens before it answered."* Then the split, then the line that names the
largest block as something the user installed and can change.

---

## One thing that blocks a demo

Neither `api/src/transport_matters/www/` nor `.../canvas/` exists in this
worktree; both are build outputs and both mounts are `.exists()`-guarded, so an
unbuilt tree serves no UI at all.

### Retracted: the "22 files do not parse" finding

An earlier revision of this document claimed 22 files under `api/src` fail to
parse (unparenthesized multi-exception `except`, e.g. `capabilities.py:150`).
**That was wrong.** `api/pyproject.toml` sets `requires-python = ">=3.14"`, and
PEP 758 makes `except A, B, C:` valid from Python 3.14. The error came from
running `ast.parse` under a 3.13 interpreter that happened to be first on PATH
at the repo root; under the project's own interpreter every file parses, and
`uv run pytest src/transport_matters/captured/test_readiness.py` passes 17/17.
Nothing is broken. Recorded rather than deleted because the claim was already
sent to the orchestrator.
