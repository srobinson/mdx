# First-run journey: scout + proposals (grok)

Date: 2026-08-04  
Branch context: `feat/overlay-landing` worktree  
Mode: read-only scout; tree pristine  
Product process: not running (`:8787` health unreachable); on-screen claims are from source + prior capture evidence under `~/.transport-matters/workspaces/…`

Governing: `docs/process/WARROOM.md`, `docs/ARCHITECTURE.md`, root `CLAUDE.md` / `Agents.md`, `NOW.md` Phase 1, print-vs-interactive evidence at `~/.mdx/projects/tm-print-vs-interactive.md`.

---

## Part 1 — Scout (journey steps)

### Journey map (human order)

| Step | Intent | Verdict |
|---|---|---|
| 1 | Install TM | EXISTS (packaged product; out of journey code scope) |
| 2 | Run TM; create own state silently; ask nothing | PARTIAL |
| 3 | Detect harnesses (installed / authed / responsive); present them ticked | EXISTS (inventory + first-run surface) |
| 4 | Capture a first **interactive** turn so the user sees what is sent | EXISTS (capture seam) + PARTIAL (no first-run orchestrator; canvas does not drive a demo prompt) |
| 5 | Reveal: unexpected number, itemized | EXISTS (Inspector) |

### Step 2 — silent state, ask nothing

| Capability | Status | Owner |
|---|---|---|
| Channel home + starter `settings.toml` materialization | EXISTS | `config.Settings.load` (materialize) |
| Session store preflight before desktop window | EXISTS | `cli/launch_runtime.preflight_session_store_or_exit`, `session_store_preflight.check_session_store` / `prepare_session_store` |
| Cold start with no DB URL | **BLOCKS** | Starter settings have no database URL; backend exits; Electron shows startup failure modal (`desktop` start path). Not silent. Confirmed by prior cold-run scout and still matches `NOW.md` gate language. |
| Infrastructure readiness API for in-product remediation | EXISTS | `captured/readiness.launch_readiness` → `GET /v1/launch-readiness` → `core.transport.fetchLaunchReadiness` → `firstrun/useLaunchReadiness` |
| Infra gate on canvas | EXISTS | `workbench/SessionCanvasRoute` renders `FirstRunScreen` with `infrastructure` when `launchReadiness.data.ready !== true` |
| Store picker (docker / BYO / managed) | **NONE FOUND** | Searched firstrun, desktop, settings flows; `NOW.md` still names it; no product writer for store choice beyond config file / doctor remediation strings |

**Searches:** `onboarding|first.?run|FirstRun`, `launch_readiness`, `session_store`, `database_url`, firstrun package tree, `NOW.md` Phase 1.

### Step 3 — harness detection and presentation

| Capability | Status | Owner |
|---|---|---|
| Static harness registry (not hardcoded only to two forever: third stub exists) | EXISTS | `harnesses.__init__`: `list_harness_descriptors`, `_CLAUDE_DESCRIPTOR`, `_CODEX_DESCRIPTOR`, `_GROK_DESCRIPTOR` (`grok` discovery-only, `launch=None`) |
| Live install detection | EXISTS | `capabilities.detect_harnesses` / `resolve_runnable_binary` / `probe_binary_version` |
| Startup refresh → stored observations (sole producer of inventory rows) | EXISTS | `harnesses/state_refresh.run_startup_refresh` / `refresh_harness_state` |
| Auth / access probes (diagnostic, never launch-gate) | EXISTS | `harnesses/probes/claude`, `…/codex`, `…/grok`; wired from `state_refresh` via `AUTHENTICATION_PROBES` |
| Inventory join (read model) | EXISTS | `harnesses/inventory.harness_inventory` → `GET /v1/harnesses` → `core.transport.fetchHarnessInventory` |
| Credential source dispatch (where credential lives) | EXISTS | `credential_source.resolve_harness_credential_source`, `harness_credential_error`, `login_command` on inventory items |
| Live credential readiness on readiness API | EXISTS | `captured/readiness._credential_check` (uses `require_shared=False` path via `harness_credential_error`) |
| First-run harness cards (installed + authenticated facts) | EXISTS | `firstrun/harnessCards.harnessCard`, `installationState`, `authenticatedFact`, `inventorySummary` |
| First-run screen | EXISTS | `firstrun/FirstRunScreen` |
| Where it appears on product | EXISTS | (a) infra remediation banner: `SessionCanvasRoute`; (b) Settings scope empty query: `launcher/CommandCenter` embeds bare `FirstRunScreen` |
| Enablement toggle | EXISTS | `FirstRunScreen` PUT `/v1/harnesses/{id}/enablement` |
| Zero harnesses = valid state copy | EXISTS | `SUMMARY_NOTES.none_installed` in `FirstRunScreen` |

**Honest surface note:** cards show stored probe auth, with footnote that probes report and never gate. Spawn gating uses `launch_readiness` checks via `launcher/templateRows.launchBlockedReason` (infra + per-harness enablement/binary/credential).

### Step 4 — launch into a pane TM controls + capture seam

| Capability | Status | Owner |
|---|---|---|
| Capture prepare seam | EXISTS | `captured/run.prepare_captured_run` → `CapturedRunSpawnSpec` + `CapturedRunLease` |
| Managed client argv (interactive path, not print) | EXISTS | `captured/claude` / `captured/codex` via `LaunchProfile.client_argv`; `initial_prompt` threaded onto argv (`captured/test_run_web_separation.test_prepare_captured_run_threads_native_prompt_into_each_harness_argv`) |
| Runtime create run (product plane) | EXISTS | `packages/runtime` `RunManager` + `createRuntimeRouter` `POST /runs` accepts `initialPrompt` + `deliveryId` together |
| Browser spawn API | EXISTS | `core.transport.createCapturedRun` / `createCapturedRunView` |
| Canvas spawn path | EXISTS | `model/capturedRunStore.ensureRun` → `createCapturedRunView`; launcher rows `templateRows.agentSpawnRows` → spawn command |
| Canvas passes demo `initialPrompt` | **NONE FOUND** | `createCapturedRun` body fields: harness, acting context, worktree, agentId, name, bypassPermissions, controlPlaneGrant, continueFromSessionId, idempotencyKey. No `initialPrompt`. |
| Control-plane launch with prompt | EXISTS | `controlplane/launch_service` + `/v1/controlplane/launch` (API/MCP path; not first-run UI) |
| PTY pane + terminal WS | EXISTS | Runtime `PtyPort` / terminal connection; canvas captured-run pane attach |
| Canvas runs never arm breakpoint | EXISTS (product invariant) | Root TLDR: canvas path never arms; turns go straight through |
| Internal baseline harvest | EXISTS (not user-facing) | `baseline_harvest._capture_cell` uses `prepare_captured_run` + trivial prompt; internal matrix tooling per `NOW.md` |
| First-run “capture a turn for me” orchestrator | **NONE FOUND** | No firstrun → spawn → wait first exchange → open Inspector sequence |

**Interactive constraint (evidence, not code):** print ≠ interactive on the wire. Interactive Claude: system parts 70/57/32,870, 22 tools; print: 74/62/27,515, 20 tools. Source: `~/.mdx/projects/tm-print-vs-interactive.md` + live IR under run `d4e6d372-…` (interactive) vs `1c7b2005-…` (print).

**TM must not write harness trust/home state:** `NOW.md` and home overlay design treat harness home as read-only to us; credential link/mint only. No scout contradiction found that writes trust for first-run.

### Step 5 — Inspector reveal

| Capability | Status | Owner |
|---|---|---|
| Exchange list + detail | EXISTS | `inspector` `ExchangeList`, `ExchangeTurnCard`, `ExchangeDetail` |
| Token bar (cache read / cache write / input) | EXISTS | `detail/TokenBar.TokenBar` + `contextTokens` |
| System parts with index + char sizes | EXISTS | `editor/SystemSection` + `detail/atoms.SizeDelta` (`part.text.length`) |
| Tools section with char accounting | EXISTS | `editor/ToolsSection` |
| Messages section | EXISTS | `editor/MessagesSection` |
| Char accounting library | EXISTS | `inspector/lib/charAccounting` (`CharBreakdown`, canonical JSON sizes) |
| Index entry stats (`system_parts`, `tools_count`) | EXISTS | exchange index / storage stats (`exchange_recorder/stats`, IR fields) |
| Inspect tab reuses editor sections read-only | EXISTS | `detail/InspectTab` + synthetic overrides for curated view |
| Arm / edit / release loop | EXISTS (complete for non-canvas) | breakpoint editor stack under `components/editor/*` |
| Pipeline savings tab | EXISTS | `ExchangeCard` pipeline tab when savings/overrides present |

**On-screen without a run:** empty Inspector / empty exchange list. The money moment needs one captured exchange first.

### Overlay / “TM takes over”

| Capability | Status | Owner |
|---|---|---|
| Run-scoped override store | EXISTS, empty until written | `overrides/state.OverrideStore` (`get_store`); process-local; starts with no overrides |
| Apply overrides at intercept | EXISTS for run-scoped pipeline | breakpoint routes + pipeline apply path (`api/v1/breakpoint_routes` reads store) |
| Persistent Overlays product view | EXISTS as **curation shell** | `routes/OverlaysView`: empty state explicitly says apply-at-intercept does not live here yet |
| Pre-populated overlay content for first run | **NONE FOUND** | No seed, no default strip, no harvest-applied overlay on first launch |

**Honesty:** reveal can ship. “TM takes over” (standing edit of the payload) cannot ship on empty store + Overlays apply gap. First money moment is observation, not control.

### Running product check

- `~/.transport-matters/settings.toml` exists; DB URL points at local Postgres `55432`.
- Channel home has workspaces and prior captures (including print/interactive evidence runs).
- Backend health on channel ports **not answering** in this session → no live UI screenshot. Scout relies on source-owned screens + stored IR.

---

## Reuse map (bind only these)

| Need | Bind to |
|---|---|
| Infra gate | `launch_readiness` + `FirstRunScreen(infrastructure=…)` |
| Harness list / ticks | `harness_inventory` + `harnessCards` + `FirstRunScreen` |
| Spawn | `createCapturedRun` / `RunManager` / `prepare_captured_run` |
| Demo prompt delivery | Runtime `initialPrompt`+`deliveryId` (extend browser client; controlplane already has launch+prompt) |
| Reveal UI | Inspector `TokenBar`, `SystemSection`, `ToolsSection`, `charAccounting` |
| Auth remediation string | inventory `authentication_command` / credential `login_command` |
| Never invent harness list in UI | `list_harness_descriptors` only |

---

## Part 2 — Proposals

### One right answer: **Reveal-first auto-demo** (Proposal A)

Everything else either adds decisions the human rejected, or pretends overlay control ships when the store is empty.

#### Why not the alternatives

| Alternative | Why worse |
|---|---|
| **Harness picker first, then “generate baseline” copy** | Forces a choice the human said may already be too much; “baseline” language hides the product value. |
| **Print-mode silent capture** | Falsifies the wire (measured). Earns the wrong number. |
| **Overlay-first / “TM takes over” on day one** | Override store empty; Overlays view is curation-only for apply. Ships a lie. |
| **Settings-only inventory with manual spawn** | Exists today; never reaches the money moment without operator craft. |
| **N parallel harness demos before any reveal** | Multiplies trust dialogs, cost, and waiting; delays the number. |

#### Screens (order)

1. **Boot / infra**  
   - User: nothing (or paste a connection string if store missing — only forced question until store picker exists).  
   - TM: materialize channel home; `launch_readiness`; if not ready, existing `FirstRunScreen` infrastructure cards with server-owned remediation.  
   - Bind: `SessionCanvasRoute` gate already.

2. **Harness strip (display, not a quiz)**  
   - User: nothing.  
   - TM: startup refresh fills inventory; cards show installed/authed as facts (ticked when good). No enablement toggles required for the demo path; default enablement remains.  
   - Bind: `FirstRunScreen` / `harnessCards` (can be a compact strip above the demo, not Settings-only).

3. **Capture stage (one ready harness)**  
   - User: answers the harness’s own first-run/trust UI **in the PTY pane** if it appears; does not type a product prompt.  
   - TM: spawns **interactive** captured run via existing seam with a trivial `initialPrompt` (same class as harvest’s `"Reply with OK."` / compare’s fixed line). Waits for first exchange finalize.  
   - Bind: `prepare_captured_run` + Runtime `initialPrompt`/`deliveryId`; **new:** canvas/first-run caller that passes them; **new:** wait-on-first-exchange using existing exchange stream/index.

4. **Reveal**  
   - User: looks. Optionally expands parts.  
   - TM: opens Inspector on that exchange, Inspect tab, system + tools expanded enough to land the number.  
   - Bind: existing Inspector; **new:** deep-link / auto-select first exchange + first-run framing chrome (“what your agent sent before you asked for work”).

5. **After (explicit non-goals of the first slice)**  
   - Overlay edit, standing policies, multi-harness comparison: later.  
   - User may continue in the same pane for real work; capture already on.

#### Single number / fact the reveal leads with

**Headline (Claude interactive, measured today):**  
**32,870 characters of system instructions in one block — before your words matter.**

Itemization under it (same exchange, no new math):

| Line | Measured (interactive Claude, evidence IR) |
|---|---|
| System part `[2]` | 32,870 chars |
| All system parts | 32,997 chars (70 + 57 + 32,870) |
| Tools | 22 tools (~70k JSON chars of schemas) |
| User/context messages | present; trivial prompt is a rounding error |
| Your typed intent | a few dozen chars |

Codex: same **screen shape**, numbers from that capture; do not hardcode Claude figures into UI — compute from IR via `charAccounting` / part lengths / `tools.length`.

#### Explicit answers (required)

**One authed harness vs many**  
Same flow, optional loop. First slice: **one** harness (first launch-eligible with binary + credential ready, registry order). Many: sequential “next ready harness” reuses the same capture→reveal without a multi-select UI. Parallel demos foreclose calm trust handling.

**Where the harness’s own first-run dialog appears**  
Inside the **captured PTY pane** TM already owns. Product chrome frames it: “Your agent is starting — accept its prompts here.” Not a broken blank canvas: pane is primary during capture; reveal opens when first request is on disk. TM never auto-dismisses trust and never writes trust into the user harness home.

**Installed but not authed / slow / absent**

| State | Behaviour |
|---|---|
| Absent | Neutral fact on card; skip for demo; if **all** absent, stop with existing zero-harness copy (valid TM state). |
| Installed, not authed | Do not spawn; show `authentication_command` remediation (existing card path); optional later: login driver per `NOW.md` 1.3 (sibling PTY, not this slice). |
| Slow probe | Keep pending facts; demo gates on **live** readiness checks (`launch_readiness` credential/binary), not probe age. |
| Slow first turn | Capture stage stays on pane + “watching the wire…”; reveal only after exchange exists. |
| Infra down | Existing infrastructure `FirstRunScreen`; no harness theater. |

**Reveal headline for a never-seen-this user**  
Not “baseline complete.”  
**“This is what your coding agent sends on your behalf — 32,870 characters of system instructions alone.”**  
Subhead: tools count + total system chars. Token bar when response usage arrives (secondary).

#### What is genuinely new (smallest surface)

1. First-run **orchestrator** (product plane): when infra ready and at least one harness launchable, enter capture→reveal instead of dumping the user on empty canvas.  
2. Wire `initialPrompt` + `deliveryId` through `createCapturedRun` (browser already half-ready; Runtime accepts it).  
3. Wait for first exchange + open Inspector focused on it with first-run framing.  
4. Copy only: frame PTY trust as expected; never call it baseline generation.

No new harness detection, no new Inspector sections, no OverrideStore population, no print path.

#### Smallest testable first slice

1. Operator has DB + one authed Claude (or Codex).  
2. Open product past infra gate.  
3. First-run path auto-spawns interactive captured run with trivial prompt (or one explicit “Show me what it sends” control if zero-click auto-spend is too aggressive — see fork).  
4. Accept any on-pane trust dialog.  
5. Inspector shows system part sizes + tool count for exchange 1.  
6. Prove: IR is interactive shape (entrypoint `cli` / tool set includes interactive-only tools when Claude), not print.

Acceptance metric: user can point at the 32k system block without opening a terminal or knowing mitmproxy.

#### Fork inside A (only real product fork)

| | A1 Zero-click after gate | A2 One intentional click |
|---|---|---|
| User action | none after install/auth | one “Show me what it sends” |
| Cost | spends a provider turn unprompted | one decision, still not harness choice |
| Forecloses | pure silence | pure zero-decision purity |
| Recommendation | **A2** for first ship: respects “user is present” and consent for a network call; still no harness menu |

Many-harness loop and overlay takeover are **not** forks of the first slice; they are later layers.

#### What ships on reveal alone (honest ceiling)

**Ships:** surprise number, itemized system/tools/messages, live interactive truth, Inspector inspect/arm path available for later turns (arm still canvas-off).  
**Does not ship:** standing overlay that “takes over,” default strip of tools, cost optimization, multi-harness comparison matrix.

That is enough to earn the $199 moment. Control is the upsell of trust after the number lands.

---

## Gaps ranked (build order)

1. **No first-run orchestrator** linking inventory → interactive capture → Inspector reveal.  
2. **Browser spawn omits `initialPrompt`** despite Runtime support.  
3. **Cold DB / store picker** still forces out-of-band config (silent run incomplete).  
4. **Login driver in-app** still plan-level (`NOW.md` 1.3); cards only show shell commands.  
5. **Overlay content empty** — do not sequence behind reveal.

---

## Quality notes (scout)

- Duplication risk: any new “doctor” UI that reimplements harness cards or readiness checks is a defect; bind existing APIs.  
- Hardcoding Claude/Codex numbers or names in first-run logic is a defect; registry + IR-derived metrics only.  
- Print harvest must not be reused as the user demo path.  
- Canvas never arms: first-run reveal is observe-only; do not promise hold/edit on that path.

---

## Done criteria for this document

- Scout cites path+symbol, EXISTS vs NONE FOUND.  
- One primary proposal; alternatives rejected with cost.  
- Explicit answers on multi-harness, trust UI, degraded states, headline.  
- Ceiling honesty: reveal yes, takeover no.
