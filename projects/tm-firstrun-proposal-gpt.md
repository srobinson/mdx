# Transport Matters first turn onboarding

Date: 2026-08-04

Source: `overlay-landing` at `c03edbd96e30d5c2917994897686bd4223f40065`

Scope: read only scout plus one recommended proposal. Current facts are separated from proposed work.

## Verdict

The reveal can ship with real product value now. A captured interactive request already contains the surprising material, and Inspector already itemizes most of it. The missing product is an API owned coordinator that joins install state, harness inventory, a visible PTY launch, wire and transcript proof, and a selected Inspector exchange.

The complete zero configuration journey also requires local Postgres provisioning. The current desktop creates a settings scaffold and migrates a reachable database, but it cannot start without an operator supplied Postgres server.

I recommend one automatic flow for every launch eligible registry entry. It shows readiness without asking for a harness choice, opens native setup in a visible pane when required, reveals the first successful capture immediately, and continues the remaining captures as a queue.

## Part 1: source scout

### Owner map

| Journey step | Current status | Owning source and symbol | Verified behavior | Search terms |
| --- | --- | --- | --- | --- |
| Install and run desktop | EXISTS | `api/src/transport_matters/cli/__init__.py:desktop`, `api/src/transport_matters/cli/desktop_cmd.py:run_desktop_detached`, `api/src/transport_matters/cli/desktop_cmd.py:serve_desktop_backend` | `transport-matters desktop` starts the backend and Electron. The backend runs session store preflight before serving. | `desktop`, `_desktop-backend`, `preflight_session_store_or_exit` |
| Silent settings state | EXISTS, partial | `api/src/transport_matters/config.py:Settings.load`, `api/src/transport_matters/config.py:ensure_settings_scaffold`, `api/src/transport_matters/session_store_preflight.py:prepare_session_store` | Materialized startup writes the channel `settings.toml` scaffold and applies migrations to a reachable store. | `materialize`, `settings.example.toml`, `apply_migrations` |
| Local database service | NONE FOUND | Current guidance lives in `api/src/transport_matters/session_store_preflight.py:session_store_setup_help` | Fresh startup requires a configured Postgres server. Guidance sends the user to Docker or another server plus `channel ensure-db`. No packaged `postgres`, `pg_ctl`, or `initdb` supervisor was found. | `embedded postgres`, `pg_ctl`, `initdb`, `ensure-db`, `docker compose` |
| Tier 1 capture state | EXISTS | `api/src/transport_matters/storage/disk.py:DiskStorageBackend.__init__` | The capture store creates its root and persists exchange artifacts under the channel home. | `mkdir`, `DiskStorageBackend`, `persist_exchange` |
| Automatic launch context for a fresh cwd | NONE FOUND | Existing mutation owners are `api/src/transport_matters/space/service.py:SpaceCrudService.create_space`, `api/src/transport_matters/space/worktree_mutations.py:create_workdir`; current read owner is `packages/space/src/service/SpaceContextService.ts:resolveWorkdirContext` | Captured Canvas runs require verified Space and Worktree identity. The current unscoped route resolves an existing mapping and reports failure when none exists. Manual creation exists in the command center. No automatic first run context writer was found. | `actingContext`, `resolveWorkdirContext`, `create-space`, `create-workdir`, `unscoped` |
| Harness registry | EXISTS | `api/src/transport_matters/harnesses/__init__.py:list_harness_descriptors`, `list_launch_eligible_descriptors`, `get_launch_boundary` | One static registry owns display name, command, launch eligibility, proxy mode, environment policy, and wire provider. Claude Code and Codex are launch eligible. Grok is discovery only. | `HarnessDescriptor`, `_DESCRIPTORS`, `launch eligible`, `wire_provider` |
| Installation detection | EXISTS | `api/src/transport_matters/capabilities.py:detect_harnesses`, `detect_harness_descriptor`, `probe_binary_version` | Registry entries are resolved on PATH and receive a bounded `--version` probe. | `detect_harnesses`, `resolve_runnable_binary`, `--version` |
| Authentication and model detection | EXISTS, diagnostic | `api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state`, `_refresh_harness`; `api/src/transport_matters/harnesses/probes/runner.py:run_authentication_probe`, `run_model_enumeration_probe` | Startup refresh writes installation, connection authentication, and model observations. Each subprocess has a five second bound. Failures isolate per harness and retain last known evidence. Both live access adapters explicitly return `access_status="unknown"`, so this path does not prove provider responsiveness. | `AUTHENTICATION_PROBES`, `MODEL_ENUMERATION_PROBES`, `access_status`, `DEFAULT_PROBE_TIMEOUT_S` |
| Stored inventory read model | EXISTS | `api/src/transport_matters/harnesses/inventory.py:harness_inventory`, `_harness_item`; `api/src/transport_matters/api/v1/harnesses.py:get_harnesses` | `GET /v1/harnesses` joins descriptors, installation, enablement, compatibility, connections, authentication, targets, launch options, and remediation. It performs no live probes. | `harness_inventory`, `/v1/harnesses`, `connections`, `targets` |
| Inventory UI | EXISTS, hidden in settings | `www/packages/canvas/src/firstrun/FirstRunScreen.tsx:FirstRunScreen`, `www/packages/canvas/src/firstrun/useHarnessInventory.ts:useHarnessInventory`, `www/packages/canvas/src/firstrun/harnessCards.ts:harnessCard`, `www/packages/canvas/src/launcher/CommandCenter.tsx:CommandCenter` | The default screen shows cards with enablement toggles, Detected, and Authenticated facts. Production mounts it inside the command center Settings scope. The resting Canvas does not open it automatically. | `FirstRunScreen`, `Harnesses`, `settings`, `FirstRunHint` |
| Infrastructure readiness | EXISTS | `api/src/transport_matters/captured/readiness.py:launch_readiness`, `_infrastructure_checks`, `_harness_checks`; `www/packages/canvas/src/firstrun/useLaunchReadiness.ts:useLaunchReadiness` | `GET /v1/launch-readiness` checks Postgres, mitmdump, Node, Gateway, harness enablement, binary, and credential readability. Its top level `ready` covers infrastructure. Zero ready harnesses remains operational. | `launch-readiness`, `credential_check`, `infrastructure` |
| Visible controlled pane | EXISTS | `packages/runtime/src/service/RunManager.ts:RunManager.createNew`, `www/packages/canvas/src/viewers/terminal/CapturedRunPane.tsx:CapturedRunPane` | Runtime prepares capture, spawns the real client in a PTY, and exposes terminal attachment to Canvas. | `ptyPort.spawn`, `CapturedRunPane`, `terminal WebSocket` |
| Interactive startup prompt | EXISTS below the Canvas client | `packages/runtime/src/server/runtimeRouter.ts:registerRunRoutes`, `packages/runtime/src/adapters/CaptureRpcClient.ts:CaptureRpcClient.prepareCapture`, `api/src/transport_matters/api/v1/capture_rpc_routes.py:prepare_capture`, `api/src/transport_matters/captured/run.py:prepare_captured_run` | Runtime accepts paired `initialPrompt` and `deliveryId` and threads both into capture. The harness receives the prompt as its native positional startup prompt. It does not use print mode. | `initialPrompt`, `deliveryId`, `prepareCapture`, `initial_prompt` |
| Canvas launch client for initial prompt | NONE FOUND | Current owner is `www/packages/core/src/transport.ts:createCapturedRunView` | The browser create options omit model, effort, initial prompt, delivery ID, and observational capture policy even though Runtime accepts most of them. | `CreateCapturedRunOptions`, `initialPrompt`, `deliveryId` |
| First prompt wire proof | EXISTS for the director path | `api/src/transport_matters/controlplane/launch_service.py:ControlPlaneLauncher._execute`, `_subscribe_to_delivery`, `_resolve_first_prompt`; `api/src/transport_matters/controlplane/delivery_proof.py:DeliveryProofObserver` | The service subscribes before run creation and returns a prompt receipt with the matching wire exchange ID. It requires a director principal and an existing Workdir affinity, so a fresh local UI cannot impersonate this caller. | `first_prompt`, `DeliveryProof`, `wire_exchange_id`, `require_director` |
| Full first turn proof | EXISTS as internal harvest logic | `api/src/transport_matters/baseline_harvest.py:_capture_cell` | The harvester waits for the exact prompt in raw wire bytes, settled response IR, tool schemas, and an owned transcript containing both prompt and assistant output. It runs detached and unattended, so its launch presentation cannot serve onboarding. Its completion algorithm can be extracted. | `prompt_complete`, `transcript_complete`, `response_ir`, `has_tool_schemas` |
| Automatic first turn coordinator | NONE FOUND | No production owner | No source joins inventory, visible native setup, an initial prompt, full proof, reveal selection, and completion state. | `first run capture`, `first turn reveal`, `onboard capture`, `reveal first turn` |
| Inspector exchange summary | EXISTS | `www/packages/inspector/src/components/detail/ExchangeCard.tsx:ExchangeCard`, `www/packages/inspector/src/components/detail/TokenBar.tsx:TokenBar` | The summary renders proportional cache read, cache write, and input tokens, plus system part count, tool count, message count, generated tokens, and pipeline state. It has no first run headline. | `contextTokens`, `TokenBar`, `system messages`, `tools` |
| Inspector exact itemization | EXISTS | `www/packages/inspector/src/components/detail/InspectTab.tsx:InspectTab`, `www/packages/inspector/src/components/editor/SystemSection.tsx:SystemSection`, `www/packages/inspector/src/components/editor/ToolsSection.tsx:ToolsSection`, `www/packages/inspector/src/components/editor/MessagesSection.tsx:MessagesSection` | The read only detail reuses editor rows. System parts are indexed with exact character counts and cache hints. Tools and message blocks are individually expandable. | `SystemPartRow`, `SizeDelta`, `ToolsSection`, `MessagesSection` |
| Direct run and exchange reveal route | NONE FOUND | Current root is `www/packages/inspector/src/app.tsx:BrowserAppShell` | Inspector takes `runId` from `/v1/meta` and selected exchange from its UI store. There is no explicit first run route carrying a proven run ID and exchange ID. | `meta.runId`, `selectedId`, `ExchangeDetail`, `exchangeId` |
| Canvas exchange fork | EXISTS, insufficient for this reveal | `www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx:ArkExchangeViewer`, `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel` | Canvas can render a provider exchange and a total token readout. Its locked read only fork omits Inspector's proportional token hero, indexed character deltas, and edit attribution. | `provider-exchange`, `ArkExchangeViewer`, `tabReadout` |
| Durable onboarding receipt | NONE FOUND | `www/packages/canvas/src/launcher/FirstRunHint.tsx:FirstRunHint` owns only a decorative local storage flag | The current flag records that the transient Command K hint appeared. It carries no capture proof, harness identity, model identity, or completion state. | `launcherHintSeen`, `firstRunCompleted`, `onboarding receipt` |
| First run overlay content | NONE FOUND | Read owner is `api/src/transport_matters/request_pipeline.py:run_pipeline`; process store is `api/src/transport_matters/overrides/state.py:OverrideStore` | Breakpoint APIs can write process overrides, but no first run path populates them. The persisted browser overlay store says pipeline application is a later slice. A first reveal must describe observation only. | `OverrideStore.upsert`, `overlaysStore`, `apply-at-intercept`, `first run` |

### Interactive mode evidence

`~/.mdx/projects/tm-print-vs-interactive.md` proves that print mode is the wrong capture.

For Claude Code 2.1.221 on the measured machine:

| Field | Print | Interactive |
| --- | ---: | ---: |
| Entry point | `sdk-cli` | `cli` |
| System part characters | 74 / 62 / 27,515 | 70 / 57 / 32,870 |
| Tools | 20 | 22 |

The interactive third system part is 5,355 characters larger. The two interactive only tools are `Artifact` and `AskUserQuestion`. The normalized requests differ even though model, prompt, cache placement, and core generation settings match.

The production launch test `api/src/transport_matters/captured/test_run_web_separation.py:test_prepare_captured_run_threads_native_prompt_into_each_harness_argv` verifies that the initial prompt is a positional argument for every supported interactive harness.

### Running product inspection

I ran the backend, Gateway, and browser surface from this checkout, then inspected `/canvas`, the command center Settings scope, and `/`.

Observed at this SHA:

* Canvas opened on the existing session picker. There was no automatic setup or reveal.
* Command K, then Settings, showed Claude Code 2.1.221, Codex 0.146.0, and Grok 0.2.118 as installed and enabled. Each card said `No connection registered` in this dev channel. Grok was marked discovery only.
* Inspector opened on `Waiting for exchanges`, with Arm and Show history. There was no first run instruction.
* `GET /v1/launch-readiness` returned infrastructure ready and successful binary and credential readability checks for the two launch eligible entries.
* `GET /v1/harnesses` returned installed rows but no stored connections in this dev channel. This demonstrates the intended distinction between fresh readiness checks and the stored inventory snapshot.

## Part 2: recommended proposal

### Proposal 1: automatic first verified reveal

One flow serves one harness, many harnesses, and future registry entries. Registry order determines presentation. No harness chooser appears.

#### Screen 1: Starting Transport Matters

User sees:

* `Preparing local history`
* `Finding your agents`
* One row per registry entry with Detected, Signed in, and Responsive facts

TM does:

1. Start a channel scoped local Postgres child, initialize it on first launch, then let `prepare_session_store` run the existing migrations. The desktop child supervisor owns its lifetime. Remote Postgres remains an operator override.
2. Resolve the launch cwd. If the owner has no matching Space and Worktree, invoke the existing Space mutation owners to create a default Space, Worktree, and root Canvas atomically. Then ask `SpaceContextService.resolveWorkdirContext` for the receipt.
3. Await the existing startup harness refresh and stream its stored observations. The UI reads one server status. It does not start subprocess probes.
4. Select every installed, enabled, launch eligible entry. Discovery only and absent entries remain visible but do not enter the capture queue.

State handling:

* Installed and authenticated: ready for capture.
* Installed with login required or unknown authentication: ready for a visible native setup pane. Authentication remains diagnostic.
* Slow probe: show Checking until the adapter deadline, then Unknown and continue with other entries.
* Absent: show Not installed and the descriptor owned remediation. Continue with other entries.
* No usable entry: leave Canvas available, persist a deferred receipt, and retry inventory on the next launch. Do not claim onboarding complete.

The Responsive fact becomes checked only after the demo turn has a correlated response and owned transcript. The existing auth probes cannot provide this fact.

#### Screen 2: Finish native setup

This screen appears only when the next queued client presents native trust, login, or first run UI.

User action:

* Respond directly inside the real harness terminal.

TM action:

* Open the existing captured PTY under a small frame: `Finish setup here. Your first request will continue automatically.`
* Use bypass permissions off and control plane grant none.
* Keep the native harness home read only.
* Create one isolated journey home per harness for proxy and credential routing. Omit `hasCompletedOnboarding`, project trust, and dangerous mode suppression from this capture profile. The harness owns state created after the human acts.
* Keep one visible setup pane at a time. Already ready captures can proceed before an unknown or slow entry.

This requires a capture profile in the existing runtime home owner. The current `ClaudeSeeder.seed` and Codex trust merge preaccept native dialogs inside the run home, so the normal managed launch profile cannot be reused unchanged.

#### Screen 3: Capturing your first turn

TM action:

1. Launch the real interactive client through `RunManager.createNew` and `prepare_captured_run`.
2. Pass a deterministic trivial prompt as the native positional startup prompt. `Reply with OK.` is sufficient.
3. Set an observational capture profile: no TM system reminder, no override content, bypass off, grant none.
4. Subscribe to delivery proof before creating the run.
5. Require all four completion facts: prompt found in raw request bytes, response IR settled, tool schema material present, and the owned transcript contains the prompt plus assistant output.
6. Record the resulting run ID and wire exchange ID on the first run receipt.

The current control plane launch path and baseline harvester each own part of this algorithm. Extract one verified launch primitive beneath their caller specific policy. The director keeps its principal and audit rules. First run receives a local owner policy. This avoids a second launch and proof implementation.

Model cardinality comes from wire adapter evidence:

* A harness whose normalized first request is exact across observed models contributes one representative default model.
* A harness whose normalized first request varies contributes one capture per observed model.
* The UI asks for no model choice. Additional model captures continue after the first reveal and appear as model tabs only when more than one result exists.

The current harvester already computes `exact` versus `varies` from normalized digests. Persist that result as certification metadata consumed by the wire adapter. Do not branch on harness IDs in the coordinator.

#### Screen 4: The reveal

Open Inspector directly on the proven run and exchange.

Headline:

> **32,997 characters of system instructions went with a 34 character prompt.**

This is the measured interactive Claude capture. Production renders the current user's captured values. With the proposed `Reply with OK.` prompt, the comparator is 14 characters. The general headline contract is:

> **{system instruction characters} characters of system instructions went with a {demo prompt characters} character demo prompt.**

If a wire adapter represents equivalent preprompt material outside `system`, that adapter supplies the canonical first turn summary. The UI consumes normalized categories and never checks a harness ID.

Itemization reuses Inspector:

* Cache read, cache write, and input tokens from `TokenBar`
* Indexed system parts with exact characters and cache hints from `SystemSection`
* Tool count and expandable definitions from `ToolsSection`
* Automatic context and the demo prompt beside each other in `MessagesSection`
* The settled response and transcript proof

Add a narrow first turn header and explicit run plus exchange route to Inspector. Keep the existing `ExchangeCard` and `InspectTab` as render owners. Avoid copying their logic into the Canvas Ark fork.

The honesty line is direct:

> TM observed this request and sent it unchanged. No overlay was applied.

The release value is the reveal itself. No savings, enforcement, or intervention claim appears while the first run override set is empty.

#### One harness and many harnesses

The journey remains one queue.

* One ready entry: capture it and reveal immediately.
* Several ready entries: reveal the first successful result immediately. Continue remaining entries and varied model partitions in registry order.
* A later native setup dialog: show its status chip and return to its terminal when the user chooses Continue setup.
* A failed entry: preserve its reason beside successful reveal tabs. It never erases earlier proof.

#### New owners and precedence

| Concern | Writer | Reader | Precedence |
| --- | --- | --- | --- |
| Harness facts | Existing `refresh_harness_state` | Existing `harness_inventory` plus first run status API | Latest completed observation wins. Unknown remains unknown. |
| Launch eligibility and order | Existing harness registry | First run coordinator | Registry plus enablement and compatibility gates win. UI has no parallel allowlist. |
| Fresh context | Existing Space mutation services behind one new atomic ensure verb | `SpaceContextService.resolveWorkdirContext` | Existing owner records win. Create only after resolve reports absent. |
| Interactive capture | Existing `RunManager` and `prepare_captured_run` | First run coordinator | Capture profile changes policy inputs. It does not create another launcher. |
| First turn proof | Extracted shared verifier using `DeliveryProofObserver` plus baseline completion checks | First run receipt and Inspector route | Wire ID, settled response, and owned transcript must all agree. |
| Completion | New `FirstRunReceiptStore`, channel and owner scoped | Startup route | `revealed` wins over pending. Deferred retries when inventory changes. Failed attempts retain evidence and may be retried idempotently. |
| Reveal | Existing Inspector detail components | Human and any API client reading the same exchange | Captured IR and usage are authoritative. Presentation derives the headline. |

#### Genericity work required

The current registry direction is correct, but the unchanged future harness journey does not exist yet. Hard coded closed unions remain in:

* `api/src/transport_matters/harnesses/__init__.py:HarnessId`
* `api/src/transport_matters/captured/models.py:CapturedRunHarness`
* `api/src/transport_matters/controlplane/run_models.py:LaunchHarness`
* `packages/runtime/src/ports.ts:PrepareCaptureInput.harness`
* `packages/runtime/src/server/runtimeRouter.ts:harnessFromBody`
* `www/packages/core/src/types/capabilities.ts:HarnessName`
* `www/packages/canvas/src/model/paneRecords.ts:CAPTURED_RUN_PROVIDERS`
* Probe and runtime home adapter maps

Replace product boundary allowlists with registry validated string identity and adapter lookup. Keep capability specific behavior in the inventory entry and wire adapter. A new harness then adds an inventory descriptor and a wire adapter with launch, probe, home, prompt, normalization, reveal summary, and variance metadata. The coordinator and screens remain unchanged.

#### Smallest coherent first slice

Ship the reveal path behind a healthy existing session store:

1. Add an API owned first run coordinator and receipt.
2. Reuse existing inventory for one representative ready registry entry.
3. Add the observational capture profile that leaves native setup visible.
4. Expose `initialPrompt` and `deliveryId` through the product launch API.
5. Extract full first turn verification from the baseline harvester.
6. Add an Inspector route for explicit run and exchange identity plus the dynamic headline.
7. Prove one interactive request, response, and owned transcript end to end.

This slice validates the product moment. Local Postgres provisioning, automatic Space context, multiple harness queueing, and variance driven model expansion complete the zero configuration journey next.

#### Acceptance evidence

The journey is complete only when an integration test and a live packaged run prove:

* Fresh channel state materializes without shell instructions.
* No file under the native harness home changes.
* A native trust or login dialog remains usable in the visible PTY.
* The launched command is interactive and contains the deterministic positional prompt.
* Delivery ID resolves to one wire exchange.
* That exchange has response IR and a correlated owned transcript.
* Inspector opens that exact run and exchange.
* The headline equals captured IR, and every itemized total reconciles.
* Exact model families capture once. Varied families capture each observed model.
* A slow, absent, or unauthenticated entry cannot block a successful reveal from another entry.
* The first run pipeline audit reports zero applied overrides.

### Why one proposal

A harness chooser adds a decision before the product has shown value. A detached harvest hides trust and login UI. Waiting for every harness delays the first reveal behind the slowest entry. Rebuilding the reveal in Canvas duplicates Inspector's established render owners. The automatic verified queue avoids each cost and preserves a single generic journey.
