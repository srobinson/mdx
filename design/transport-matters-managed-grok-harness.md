---
title: Transport Matters Managed Grok Harness
type: design
tags: [transport-matters, grok, harness, capture, canvas, provider-access]
summary: Caller first architecture for one truthful managed Grok turn through the shared Transport Matters stack
status: active
project: transport-matters
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Transport Matters Managed Grok Harness

## Decision

Promote Grok through the existing harness owners with four verifiable units. Grok remains discovery only until the final activation unit.

One optional combined refresh probe runs `grok models` once and projects authentication plus model catalog evidence. Provider access is absent from that result. A genuine captured provider outcome remains the only passive source of access truth.

Reuse the current Responses request and SSE primitives for Grok after extracting them from the Codex package. Keep strict provider adapters for route identity. Add explicit captured invocation and Runtime interaction registries with no default. Missing registrations fail before process spawn.

Use `GROK_HOME` for the native config boundary and `updates.jsonl` as the authoritative transcript source.

## Pinned evidence

This design targets `main` at `2f858fcc5a4f15cc2729e684f4b2516deb529ddf` and Grok `1.0.4 (d846eb93d94d)`.

1. Authenticated and isolated unauthenticated `grok models` calls both exit zero and return the same model catalog. Their first lines report different authentication states.
2. `grok models` proves authentication and catalog visibility. It does not prove provider access.
3. A bounded real turn succeeded through an explicit HTTP and HTTPS proxy with `SSL_CERT_FILE`.
4. The provider route is JSON `POST https://cli-chat-proxy.grok.com/v1/responses` with an SSE response.
5. Request keys include `input`, `model`, `reasoning`, and `tools`. Response events use `response.created` through `response.completed` families already handled by the current Responses parser.
6. One process may emit several `/v1/responses` requests plus settings, storage, trace, and telemetry traffic. Only a certified genuine activity request may elevate access.
7. Grok accepts `--session-id`, `--model`, `--reasoning-effort`, `--resume`, `--continue`, and an initial positional prompt.
8. `GROK_HOME` overrides the native config root. Sessions live under `${GROK_HOME}/sessions/<encoded-cwd>/<session-id>/`.
9. `updates.jsonl` is the authoritative ACP conversation stream. It carries `user_message_chunk`, `agent_message_chunk`, and `agent_thought_chunk` updates.

## Caller usage

Startup remains unchanged:

```python
await refresh_harness_state(evidence_store)
```

For Grok, refresh selects the optional combined capability:

```python
adapter = COMBINED_REFRESH_PROBES.get(harness_id)
if adapter is not None:
    result = await run_combined_refresh_probe(
        adapter=adapter,
        binary=observation.executable_path,
        connection=native_connection,
        base_env=env,
    )
    await write_authentication(result.authentication)
    if result.models is not None:
        await write_target_snapshot(result.models)
    return
```

The visible launch path remains:

```text
Canvas captured run intent
  -> Core POST /v1/runs with harness=grok
  -> Runtime RunManager
  -> Capture RPC prepare
  -> shared resolver snapshots and access assessment
  -> CaptureLeaseRegistry
  -> mitmdump plus Grok PTY
  -> genuine /v1/responses exchange
  -> ProviderAccessRecorder
  -> owned updates.jsonl
  -> normalized session events
  -> Canvas terminal and transcript panes
```

Canvas, Core transport, Runtime process ownership, resolver, exchange storage, session ingestion, and transcript rendering contain no Grok transport logic.

## State evidence types

```python
@dataclass(frozen=True, slots=True)
class CombinedRefreshEvidence:
    authentication: AuthenticationEvidence
    models: tuple[EnumeratedModel, ...] | None


@dataclass(frozen=True, slots=True)
class CombinedRefreshProbeAdapter:
    harness_id: HarnessId
    probe_revision: str
    command: tuple[str, ...]
    parse: Callable[[ProbeCapture], CombinedRefreshEvidence]


async def run_combined_refresh_probe(
    *,
    adapter: CombinedRefreshProbeAdapter,
    binary: str,
    connection: HarnessConnection,
    base_env: Mapping[str, str],
    timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
    run: Callable[..., Any] = subprocess.run,
) -> CombinedRefreshEvidence: ...
```

`models=None` means probe or parser failure and preserves the last complete target snapshot. `models=()` means a successful empty catalog and retires prior targets.

The result has no access field. The type prevents startup code from turning authentication or catalog visibility into entitlement.

`COMBINED_REFRESH_PROBES` registers Grok only. Grok appears in neither `AUTHENTICATION_PROBES` nor `MODEL_ENUMERATION_PROBES`. Claude and Codex retain their existing paths.

## Home, launch, and session ownership

Add `GROK_HOME` to the existing harness home environment map and `.grok` to the native directory map. Do not introduce a new home abstraction.

The first release supports native credentials. Credential copying, linking, runtime templates, and a Grok seeder remain outside this slice until a credential source fixture requires them.

Add a mint capable Grok launch profile using a caller owned UUID:

```python
class GrokLaunchProfile(LaunchProfile):
    harness = "grok"
    mints_session_id = True

    def prepare(...) -> str: ...
    def client_argv(...) -> list[str]: ...
```

The source descriptor and transcript locator share one path helper:

```python
def grok_updates_path(
    *,
    working_dir: Path,
    native_session_id: str,
    grok_home: Path,
) -> Path: ...
```

Replace the Claude branch and unconditional Codex fallback in captured invocation construction with an explicit registry:

```python
class CapturedInvocationBuilder(Protocol):
    harness: HarnessId

    def build(self, context: CapturedInvocationContext) -> InvocationFactory: ...
```

The registry contains Claude, Codex, and Grok entries. It has no default. Missing registration raises a stable unsupported harness error before mitmdump or the client starts.

## Shared Responses wire path

Extract provider neutral request, serializer, and SSE primitives from the Codex package. Parameterize only observed provider differences. Thin Codex and Grok adapters retain route identity and provider metadata.

```python
class GrokAdapter(ProviderAdapter):
    name = "grok"

    def matches(self, flow: Any) -> bool: ...
    def inbound_request(self, raw_body: bytes) -> InternalRequest: ...
    def outbound_request(self, request: InternalRequest) -> bytes: ...
    def inbound_response(self, raw_body: bytes, content_type: str) -> InternalResponse: ...
```

`matches` requires method `POST`, exact host `cli-chat-proxy.grok.com`, and path `/v1/responses` with an optional query.

HTTP admission becomes adapter driven. Preserve the Codex WebSocket path. Do not create a copied Grok codec package.

Share the existing Responses completion classifier only where the certified Grok fixture matches Codex semantics. Access elevation also requires `drives_activity=True`. Auxiliary and unknown requests produce no activity and no access observation.

## Transcript adapter

Add a Grok implementation of the existing transcript port. It tails `updates.jsonl` and normalizes ACP session updates.

```python
class GrokAdapter(TranscriptAdapter):
    provider = "grok"
    harness = "grok"
    transcript_reader_revision = "grok-transcript-reader-r1"
    session_bootstrap_revision = "grok-session-bootstrap-r1"

    async def bind(self, run: RunContext) -> SessionBinding: ...
    async def locate(self, binding: SessionBinding) -> FileTailSource | None: ...
    def normalize(self, record: RawRecord, ctx: TurnContext) -> NormalizedTurn | None: ...
    def is_certified_meta(self, record: RawRecord) -> bool: ...
```

The launcher owned UUID is both the native session id and managed binding key. Unknown update kinds follow the existing transcript drift path.

## Runtime interaction

Replace inferred Claude or Codex behavior with an explicit registry:

```typescript
export interface HarnessInteractionProtocol {
  readonly harness: RuntimeHarness;
  readonly revision: string;
  readonly breakSequence: string;
  createReadinessScanner(): HarnessReadinessScanner;
  submit(
    session: PtySession,
    text: string,
    deliveryId: string,
    surface: InputDeliverySurface,
  ): Promise<PromptInputAdapterOutcome>;
}

export function getHarnessInteractionProtocol(
  harness: RuntimeHarness,
): HarnessInteractionProtocol;
```

Claude and Codex move behind explicit entries without behavior changes. Grok readiness, paste, submit, question handling, and interrupt come from a recorded PTY fixture. The registry has no default.

## Activation rule

Keep `_GROK_DESCRIPTOR.launch` as `None` and keep Grok absent from every launchable public union until all registrations exist:

1. combined state probe;
2. compatibility release and route;
3. launch profile;
4. captured invocation builder;
5. wire adapter;
6. provider access classifier;
7. transcript adapter;
8. Runtime interaction protocol.

A release completeness test resolves every revision referenced by the Grok release. A TypeScript completeness test proves every public Runtime harness has one interaction protocol.

The final activation unit fills the descriptor and widens Python, Runtime, Core, and Canvas harness unions together.

## Implementation units

### Unit 1: state evidence

Add the combined probe types, runner, strict Grok parser, one process refresh path, exact release range support, and focused tests. Remove the r0 Grok probe. Keep access missing and Grok unlaunchable.

### Unit 2: captured protocols

Capture sanitized nested request, SSE, PTY, and ACP fixtures. Extract shared Responses primitives. Add the Grok wire adapter, activity classification, access classification, `GROK_HOME` handling, source path helper, and transcript adapter. Prove exchange and session normalization without public launch.

### Unit 3: managed process

Add `GrokLaunchProfile`, the captured invocation registry, Grok invocation builder, and Runtime interaction registry. Delete fallthroughs. Prove exact argv, environment, readiness, submit, interrupt, and failure before spawn when registration is absent.

### Unit 4: activation and product proof

Run release completeness tests. Fill the Grok descriptor. Widen Python and TypeScript launch unions. Add the Canvas label and provider entry. Execute one real first turn from `tm desktop` through Canvas.

## Module ownership

| Area | Existing owner | Change |
| --- | --- | --- |
| Detection | `capabilities.py` | Reuse |
| Probe vocabulary | `harnesses/probes/__init__.py` | Add combined types |
| Probe runner | `harnesses/probes/runner.py` | Add one capture runner |
| Grok parser | `harnesses/probes/grok.py` | Replace r0 stub |
| Refresh | `harnesses/state_refresh.py` | Optional registry path |
| Compatibility | `harnesses/compatibility.py` and embedded manifest | Exact Grok range, route, revisions |
| Home | `launch/environment.py`, runtime home owners | Add `GROK_HOME` and `.grok` |
| Launch | `cli/launch_profile.py` | Add Grok profile |
| Capture invocation | focused registry and Grok builder | Delete fallthrough |
| Wire | shared Responses primitives and thin adapters | Add strict Grok route |
| HTTP admission | `addon_handlers.py` | Adapter driven |
| Access | `provider_access_recorder.py` | Shared certified Responses outcome |
| Transcript | `index/adapters` | Add Grok `updates.jsonl` reader |
| Runtime input | interaction protocol registry | Remove inferred behavior |
| Core and Canvas | existing harness types and provider list | Widen last |

No feature code enters `resolver.py` or `RunManager.ts`. New production files target 300 lines. Focused test files target 500 lines. Files near the 700 line limit receive sibling modules.

## Required proof

The final live acceptance proves one identity chain:

```text
Canvas intent
  -> Runtime run id
  -> Capture RPC lease
  -> owned Grok session id
  -> genuine JSON /v1/responses request
  -> terminal response.completed SSE
  -> provider access observation
  -> updates.jsonl ACP records
  -> normalized TM session
  -> Canvas transcript pane
```

Verify:

1. one `grok models` subprocess during refresh;
2. independent authentication and model projections;
3. access missing before the real turn;
4. no activity or access from auxiliary requests;
5. available access after a genuine completed response;
6. matching terminal and durable transcript turns;
7. matching run, native session, TM session, Worktree, and Canvas identities;
8. an unsupported version refuses before spawn;
9. Claude and Codex regressions plus repository gates remain green.

## Explicit exclusions

This slice adds no database migration, credential seeder, runtime template support, descriptor home migration, resolved adapter plan, RPC revision handshake, or Grok specific Canvas component.

## Remaining fixture work

1. Capture sanitized nested request, tool, reasoning, output, usage, and provider error field vocabularies.
2. Identify the structural discriminator for the genuine user turn among several `/v1/responses` requests.
3. Record Grok PTY readiness, prompt submission, question mode, and interrupt behavior.
4. Certify ACP envelope, chunk ordering, record termination, and path encoding for a supplied session id.
5. Confirm that native authentication plus explicit proxy variables, `SSL_CERT_FILE`, and `GROK_HOME` are sufficient for managed launch.
