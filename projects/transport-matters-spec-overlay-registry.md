# Overlay Registry v1

Status: chartered specification

Date: 2026-08-07

## Goal

Deliver curated request overlays independently of Transport Matters releases while preserving a local, deterministic request path.

The registry publishes signed immutable artifacts for one tenant, harness, and exact harness version. The Gateway refreshes artifacts asynchronously. The capture plane validates, caches, freezes, and applies them through existing owners. No provider request waits for the registry.

The safety invariant is absolute:

> If an artifact cannot be selected, validated, frozen, parsed, or applied, the registry layer enters `PASSTHROUGH` and forwards the original bytes. Launch proceeds.

This includes a cold cache, registry outage, expired artifact, bad signature, unknown harness version, off catalog model, new model, unmatched request fingerprint, unrecognized payload vocabulary, and application failure.

Every `PASSTHROUGH` reason has a durable recording owner. V1 also exposes the current mode and reason to a human through a minimal visible chip. A recorded state with no visible surface is incomplete.

## Decisions

These decisions are binding and are not reopened by this specification.

1. Overlay artifacts are signed and immutable. The registry key is the tenant resolved tuple `(harness, exact_harness_version)`. Model is not part of the remote key.
2. Artifact format is online ready. Registry transport is local for v1. Application is always local. The Gateway refreshes asynchronously with ETag support. The accepted cache lives under the channel home, which is `~/.transport-matters` for stable. One accepted artifact revision is frozen for each run.
3. Release keyed artifacts flow from the registry to clients. Per user recorded overlays remain local. They never upload automatically. Deliberate publication is outside v1.
4. Every unavailable, invalid, unknown, or unsupported registry condition resolves to `PASSTHROUGH`. The original bytes are forwarded. Overlay availability never blocks a launch, a new harness release, or a new model.
5. Catalog membership is advisory. An unknown or off catalog model may select a model independent variant only when the local request fingerprint and every preimage check match. Otherwise that request uses `PASSTHROUGH`.
6. The deferred remote server is a registry. It authenticates, resolves tenancy, and returns static signed bytes. It performs no inference, request inspection, overlay generation, or computation on user data. The v1 disk adapter serves the same signed bytes through existing loopback Gateway trust.
7. A run never changes artifact revision after its facts are frozen. A refresh completed during a run becomes eligible for a later run.
8. V1 has two active layers: existing live breakpoint edits above one frozen managed artifact. Precedence is resolved once by `OverrideStore`, never by call order or by the shared proxy. Browser recorded overlay drafts have no shipped apply path and remain deferred.

### Decision log

- `2026-08-08`, source 'live demo evidence, run 163c35b4': managed validation permits `message_block_toggle` and `message_text` only for published preimages of harness injected boilerplate. The operations reuse the existing `Override` union and add no envelope fields.
- `2026-08-08`, source 'live demo evidence, run 163c35b4': system parts and message blocks use canonical content digest targets in both managed and live layers. Positional `system:{index}` and `msg:{message}:blk:{block}` targets are rejected.
- `2026-08-08`, source 'disk-backed bridge, Stuart 2026-08-08, KISS': v1 serves git versioned artifact files through the existing local TypeScript Gateway. The deferred remote registry uses the same HTTP contract, so migration changes only the resolved base URL.

## Architecture and ownership

### Plane placement

The local product context is `@tm/overlay` under `packages/overlay`. It follows the canonical context package shape and owns:

- one registry HTTP client for the local disk bridge and deferred remote service;
- ETag refresh scheduling, deduplication, backoff, and status;
- the disk backed registry adapter mounted by `packages/gateway/src/app.ts:buildGateway`;
- the local product API;
- delivery of downloaded bytes to the capture plane over the existing local capture RPC seam.

The registry base URL has one resolver in `api/src/transport_matters/config.py`. Environment value `TRANSPORT_MATTERS_OVERLAY_REGISTRY_URL` wins over `[overlay].registry_url` in `settings.toml`. V1 release packaging supplies the supervised local Gateway origin. Python passes the resolved URL to the Gateway. TypeScript consumes that value and performs no configuration precedence of its own. A later remote registry changes only this base URL.

`@tm/contract/overlay` is the only product and browser wire contract. It owns the status DTOs, artifact metadata DTOs, branded aggregate identifiers, and the closed `PASSTHROUGH` reason vocabulary. The Gateway constructs and mounts `@tm/overlay` through its package export. It owns no overlay domain logic.

The capture plane extends existing owners only. It owns:

- strict signed artifact validation;
- accepted cache persistence under `ChannelSpec.home`;
- exact harness release selection from the existing compatibility observation;
- per run freeze in compatibility facts;
- effective snapshot installation in `OverrideStore`;
- local request application through `run_pipeline` and `apply_overrides`.

V1 artifact documents are versioned beneath `docs/overlays/` in the Transport Matters repository and ship with the release. Commit `ca3eaec7` establishes the Claude and Codex worksheets that supply exact captured befores and per field preimages. The local Gateway adapter reads the packaged artifact bytes without rewriting them and serves the registry contract below. The accepted bridge cost is explicit: while artifacts ride the release, responding to a harness release requires a Transport Matters release.

The remote registry remains a deferred separate deployable boundary. Whether it shares a deployment with accounts and licensing is an open decision below.

### Writers and precedence

| State | Sole writer | Readers | Precedence |
| --- | --- | --- | --- |
| Published artifact bytes | Offline publication pipeline, committed beneath `docs/overlays/` for v1 | Local Gateway disk adapter; deferred registry service | Immutable after publication; served byte for byte from the packaged file |
| Registry tenant mapping | Registry administration | Registry resolver | Latest authorized mapping selects one immutable artifact |
| Accepted local cache | Capture plane validator | Capture preparation, local status adapter | Higher valid revision replaces lower valid revision for the exact tuple |
| Frozen run artifact reference | `write_compatibility_facts` | Capture, replay, audit, Inspector | Write once; divergent rewrite rejected |
| Managed run overrides | `OverrideStore` managed layer install | `run_pipeline`, shared proxy snapshot | Below live breakpoint edits |
| Live breakpoint edit | `patch_overrides` | `OverrideStore`, paused preview, shared proxy | Highest for the same `(kind, target)` |
| Browser recorded overlay draft | `useOverlaysStore` | Inspector draft UI | No active precedence in v1; acquisition and apply remain deferred |

The shared proxy receives one effective snapshot. It transports state and has no precedence policy.

## Reuse bindings

A new implementation for a capability in this table is a specification defect.

| Field or behavior | Existing owner | Binding |
| --- | --- | --- |
| Strict schema, signature, monotonic revision, expiry, minimum TM version, and digest checks | `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` | Extract or extend its shared signed update rules. An overlay validator is a domain wrapper over those rules, with no second verification engine. |
| Trust verifier contract and current production swap point | `api/src/transport_matters/harnesses/compatibility_store.py:SignatureVerifier`, `api/src/transport_matters/harnesses/compatibility_store.py:RejectAllSignatureVerifier` | Production `APPLY` is unreachable while the rejecting verifier remains. Slice 2 installs the selected trust root at this swap point before cache, freeze, or application slices. Compatibility and overlay artifacts use the same verifier contract and keyring. |
| Harness and exact normalized version selection | `api/src/transport_matters/harnesses/compatibility.py:match_release` | Reuse its channel, harness, release, and normalized version facts. Do not add a second version parser, probe, or catalog gate. Overlay applicability may become `PASSTHROUGH`; launch remains advisory. |
| Per run artifact identity and immutable freeze | `api/src/transport_matters/harnesses/compatibility_facts.py:CompatibilityFactArtifact`, `api/src/transport_matters/harnesses/compatibility_facts.py:compatibility_fact_artifact`, `api/src/transport_matters/harnesses/compatibility_facts.py:write_compatibility_facts` | Evolve the existing schema and builder to admit unresolved compatibility evidence and a required overlay outcome. Every gated run writes through this owner. Do not add a sibling run freeze file or mutable run registry. |
| Managed and live layer ownership | `api/src/transport_matters/overrides/state.py:OverrideStore` | Extend the store with managed and live layers plus one effective composition rule. Do not add a second active overlay store. |
| Atomic scope snapshot, rollback, preview, and shared proxy synchronization | `api/src/transport_matters/api/v1/overrides.py:patch_overrides`, `api/src/transport_matters/api/v1/overrides.py:_snapshot_scope`, `api/src/transport_matters/api/v1/overrides.py:_sync_shared_overrides` | Extract one reusable atomic snapshot install path. Managed freeze and user edits both use it. |
| Request mutation gate and failure behavior | `api/src/transport_matters/request_pipeline.py:run_pipeline` | Resolve one effective list locally. Every resolver or application failure returns the original IR. |
| Override execution order and request audit | `api/src/transport_matters/overrides/__init__.py:apply_overrides` | Apply once. Keep operation ordering, original index semantics, sanitization, and audit in this owner. |
| Startup harness discovery and best effort scheduling | `api/src/transport_matters/harnesses/state_refresh.py:refresh_harness_state`, `api/src/transport_matters/harnesses/state_refresh.py:run_startup_refresh` | Emit exact observed tuples to the product refresh port after the existing pass. Do not create another startup detector or binary probe. Refresh failure remains isolated and cannot fail startup. |
| Launch exact version owner and cross plane carry | `api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation`, `api/src/transport_matters/harnesses/compatibility_service.py:CompatibilityGateDecision.normalized_version`, `api/src/transport_matters/cli/launch_runtime.py:prepare_launch`, `api/src/transport_matters/captured/context.py:_prepare_launch_state` | The compatibility gate remains the sole production version source. Captured launch carries its result through `LaunchPreparation.compatibility`, `CapturedRunSpawnSpec.harness_version`, `capture_spawn_spec_payload`, TypeScript `CapturedRunSpawnSpec.harnessVersion`, `CaptureRpcClient`, and `RunManager.createNew` to the Overlay refresh scheduler. No caller probes again. |
| Channel isolated cache root | `api/src/transport_matters/channel.py:ChannelSpec.home` | Resolve the cache path once in Python. TypeScript receives an opaque local port and never derives `~/.transport-matters` or channel paths. |
| Registry base URL and precedence | `api/src/transport_matters/config.py:Settings`, planned `api/src/transport_matters/config.py:resolve_overlay_registry_url`, planned `api/src/transport_matters/env_keys.py:OVERLAY_REGISTRY_URL` | Add `[overlay].registry_url` and `TRANSPORT_MATTERS_OVERLAY_REGISTRY_URL`. Environment wins over TOML in the one Python resolver. The resolved URL is passed to the Gateway; TypeScript never resolves configuration again. |
| V1 registry transport | `packages/gateway/src/app.ts:buildGateway` | Mount the `@tm/overlay` disk adapter over packaged files beneath `docs/overlays/`. It serves the same endpoint, artifact bytes, status semantics, and ETag contract as the deferred remote registry. |
| Canonical signature bytes and request selector digests | `api/src/transport_matters/canonicalization.py:canonical_json`, `api/src/transport_matters/canonicalization.py:canonical_digest` | Reuse the current canonicalization rules. No second JSON canonicalizer or hash format. |
| Shared proxy transport | `api/src/transport_matters/shared_proxy/manager.py:SharedProxyManager.set_overrides` | Continue sending one flat effective snapshot. The manager does not merge sources. |
| Local draft lifecycle | `www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` | Retain drafts and confirmation locally. Source states that apply at intercept is unshipped. V1 adds no acquisition or activation path for these drafts. |

### Artifact field traceability

| Artifact field | Contract owner | Existing implementation owner |
| --- | --- | --- |
| `artifact_schema_version` | planned `@tm/contract/overlay:OverlayArtifactDocument` | `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` strict schema and supported version rule |
| `override_schema_version` | planned `@tm/contract/overlay:OverlayArtifactDocument` | `api/src/transport_matters/overrides/__init__.py:Override`, validated before `api/src/transport_matters/overrides/__init__.py:apply_overrides` |
| `artifact_id`, `revision`, `issued_at`, `expires_at`, `minimum_transport_matters_version`, `content_sha256` | planned `@tm/contract/overlay:OverlayArtifactDocument` | `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` identity, monotonic sequence, time, version, and digest rules |
| `tenant_subject` | planned `@tm/contract/overlay:OverlayTenantSubject` | authenticated capture RPC install boundary plus `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` domain wrapper |
| `harness`, `harness_version` | planned `@tm/contract/overlay:OverlayReleaseKey` | `api/src/transport_matters/harnesses/compatibility.py:match_release` and its normalized version result |
| `disposition` and every `PASSTHROUGH` reason | planned `@tm/contract/overlay:OVERLAY_MODES`, `@tm/contract/overlay:OVERLAY_PASSTHROUGH_REASONS` | `api/src/transport_matters/request_pipeline.py:run_pipeline` identity return and `api/src/transport_matters/harnesses/compatibility_facts.py:CompatibilityFactArtifact` freeze |
| `variants[].request_fingerprint` | planned `@tm/contract/overlay:OverlayVariant` | `api/src/transport_matters/canonicalization.py:canonical_digest`, selected before `api/src/transport_matters/request_pipeline.py:run_pipeline` |
| `variants[].model_ids` | planned `@tm/contract/overlay:OverlayVariant` | local selector before `api/src/transport_matters/request_pipeline.py:run_pipeline`; no catalog owner or remote key |
| `variants[].operations[].override` | existing `api/src/transport_matters/overrides/__init__.py:Override` | `api/src/transport_matters/overrides/state.py:OverrideStore` composition and `api/src/transport_matters/overrides/__init__.py:apply_overrides` execution |
| `variants[].operations[].override.target` for system parts and message blocks | existing `api/src/transport_matters/overrides/__init__.py:Override.target` | `api/src/transport_matters/canonicalization.py:canonical_digest`; managed and live layers resolve the same canonical content digest target against the original IR |
| `variants[].operations[].preimage_sha256` | planned `@tm/contract/overlay:ManagedOverlayOperation` | `api/src/transport_matters/canonicalization.py:canonical_digest`, checked atomically before `api/src/transport_matters/overrides/__init__.py:apply_overrides` |
| `provenance.publisher`, `provenance.author`, `provenance.author_kind`, `provenance.approver`, signature algorithm, `signing_key_id`, and signature value | planned `@tm/contract/overlay:OverlayArtifactDocument` | `api/src/transport_matters/harnesses/compatibility_store.py:SignatureVerifier` and its `api/src/transport_matters/harnesses/compatibility_store.py:RejectAllSignatureVerifier` swap point; run reference in `api/src/transport_matters/harnesses/compatibility_facts.py:CompatibilityFactArtifact`; exchange attribution in `api/src/transport_matters/overrides/audit.py:OverrideAudit` |

### New surfaces with no current owner

Current source has no registry client, disk registry adapter, accepted overlay cache, or overlay product context. The only justified new domain surface is `@tm/overlay` plus its `@tm/contract/overlay` contract. `packages/gateway/src/app.ts:buildGateway` remains the HTTP composition owner. Generic HTTP, coercion, and lifecycle primitives continue to come from `@tm/common` and existing Gateway patterns.

## V1 API surface

### Registry transport contract

`api/src/transport_matters/config.py:resolve_overlay_registry_url` is the sole base URL resolver. It validates `Settings.overlay_registry_url` from `TRANSPORT_MATTERS_OVERLAY_REGISTRY_URL` or `[overlay].registry_url`, in that precedence order. V1 packaging supplies the supervised local Gateway base URL. A missing value disables refresh and yields `PASSTHROUGH`; there is no second resolver. `gateway_supervisor.py:plan_gateway_supervision` carries the resolved URL into the Gateway process. Both planes use this resolved value. Switching to the remote registry changes only the resolved base URL and no client code.

The v1 disk adapter mounted by `packages/gateway/src/app.ts:buildGateway` serves packaged files beneath `docs/overlays/`. Its endpoint shape, artifact document bytes, content type, status meanings, and ETag behavior are the registry contract. `If-None-Match` compares against the local file artifact digest and returns `304` on equality. The deferred remote service must be byte compatible with a local `200` response.

`GET /v1/overlay-artifacts/current?harness=<opaque>&harness_version=<exact>`

Request:

- `Authorization: Bearer <short lived TM account access token>`
- `If-None-Match: "<held content digest>"` when a cache entry exists
- `Accept: application/vnd.transport-matters.overlay+json;version=1`

The tenant and seat derive only from verified token claims. Neither appears as client supplied authority in the query or body. `harness` is an opaque string. `harness_version` is the exact normalized version produced by the compatibility owner. Model, request fingerprint, project path, workspace identity, and provider account data are absent.

Responses:

| Status | Meaning | Client behavior |
| --- | --- | --- |
| `200` | One static signed artifact for the resolved tenant and exact tuple | Validate locally. Promote only after full validation. |
| `304` | Held artifact digest remains current | Revalidate held metadata before use. Keep the accepted cache. |
| `401` | Account token is absent or invalid | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`. |
| `403` | Account lacks entitlement or `overlays:read` | Enter `PASSTHROUGH` immediately. Retain cache bytes for diagnostics but do not apply them. Open Decision 4 may replace this baseline with a signed grace rule. |
| `404` | No artifact has been published for the exact tuple | Keep any still valid accepted cache. A `404` never revokes signed state. Otherwise `PASSTHROUGH`. |
| `406` | No supported artifact schema representation | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`. |
| `5xx` or network failure | Registry unavailable | Keep an unexpired accepted cache. Otherwise `PASSTHROUGH`. |

Revocation or intentional disablement is a newer signed artifact whose disposition is `PASSTHROUGH`. An unsigned status code cannot retire a held signed artifact.

No mutation endpoint ships in v1. Operator publication writes signed immutable files beneath `docs/overlays/` and commits them for a later TM release. The deferred remote publication pipeline writes the same immutable bytes plus tenant mappings. Deliberate user or organization publication is outside v1.

### Local product API

`GET /v1/overlays/status`

Returns the refresh and cache status for every observed harness tuple. An optional `run_id` returns the frozen run reference when one exists. The response carries `mode`, `reason`, exact harness tuple, artifact reference, source, last refresh time, and cache age. It never includes artifact operation values.

`POST /v1/overlays/refresh`

Accepts one exact observed harness tuple, schedules a deduplicated background refresh, and returns `202` immediately. It never waits for the registry transport. The existing startup refresh calls this through an injected local port. Runtime may call the same service method after capture preparation reveals a new exact version.

The Gateway mounts both routes from `@tm/overlay`. Browser and director clients consume the same API.

### Local capture RPC

The existing capture RPC gains internal operations to validate and install a downloaded artifact and to read accepted cache metadata. These operations are loopback implementation ports. They are not mounted as remote product API routes.

Validation delegates to `validate_channel_update` shared rules and the configured `SignatureVerifier`. Accepted bytes are written atomically under `ChannelSpec.home`. The RPC returns sanitized artifact identity, ETag, and validation outcome. It never returns signing keys or account tokens.

### Authentication

The registry access token must carry issuer, audience, expiry, token id, subject, tenant, entitlement, and scope. The registry validates every request. Provider credentials, Claude credentials, Codex credentials, runtime home secrets, and capture grants are never accepted as registry authentication.

The local Gateway and capture RPC retain their existing loopback trust and process supervision boundaries. Remote account tokens stay in the product account credential owner and never enter harness homes, run facts, request audits, or browser storage.

## Artifact document

Illustrative v1 document:

```json
{
  "artifact_schema_version": 1,
  "override_schema_version": 1,
  "artifact_id": "ovl_01",
  "revision": 18,
  "tenant_subject": "tenant_subject_01",
  "harness": "claude",
  "harness_version": "2.1.225",
  "disposition": "APPLY",
  "minimum_transport_matters_version": "1.0.0",
  "issued_at": "2026-08-07T00:00:00Z",
  "expires_at": "2026-08-21T00:00:00Z",
  "variants": [
    {
      "variant_id": "variant_01",
      "request_fingerprint_schema_version": 1,
      "request_fingerprint": "<sha256>",
      "model_ids": [],
      "operations": [
        {
          "override": {
            "kind": "tool_toggle",
            "target": "tool:WebSearch",
            "value": false
          },
          "preimage_sha256": "<sha256>"
        }
      ]
    }
  ],
  "provenance": {
    "publisher": "tm",
    "author": "curator_01",
    "author_kind": "tm_curator",
    "approver": "policy_04",
    "publication_id": "pub_01"
  },
  "content_sha256": "<sha256>",
  "signature": {
    "algorithm": "<selected trust algorithm>",
    "signing_key_id": "<selected key id>",
    "value": "<signature>"
  }
}
```

### Contract rules

- Unknown fields are rejected.
- Every schema version is a strict positive integer.
- `artifact_id` is a branded aggregate identifier in the Overlay domain. Revision, variant id, publication id, ETag, event id, and reason remain plain scalar values.
- `harness` remains an opaque string. There is no closed model or harness catalog in the Overlay domain.
- `harness_version` must equal the exact normalized observed version. Version ranges and nearest version fallback are forbidden.
- `tenant_subject` is derived from the authenticated resolution and signed into the document. The client verifies it against the current account subject.
- `publisher`, `author`, `author_kind`, `approver`, `publication_id`, and `signing_key_id` are signed provenance fields. The signer may differ from the author and approver.
- Revision is strictly increasing for `(tenant_subject, harness, harness_version)`. Equal or lower revisions cannot replace an accepted cache.
- `expires_at`, minimum TM version, content digest, and signature are validated before acceptance.
- `ETag` equals `content_sha256`. ETag supports refresh efficiency and grants no trust.
- `PASSTHROUGH` artifacts have an empty `variants` list.
- `APPLY` artifacts contain unique variant ids and no duplicate `(kind, target)` keys inside one variant.
- The canonical signature payload excludes only the signature value. Canonical bytes come from `canonical_json`.
- System part targets use `system:sha256:{canonical_digest}`. Message block targets use `msg:sha256:{canonical_digest}`. The digest covers the complete canonical system part or message block from the original IR. A target is missing when no part hashes to it.
- Managed message operations add no envelope fields. `message_block_toggle` and `message_text` remain values of `variants[].operations[].override`, with the existing sibling `preimage_sha256` guard.
- `api/src/transport_matters/request_pipeline.py:run_pipeline` narrows its `OverrideAudit | None` return contract: the disabled store and exception branches return a real zero delta `OverrideAudit` carrying `store_disabled` and `application_failed`, respectively, and `api/src/transport_matters/exchange_recorder/artifacts.py:build_request_artifacts` persists that object as `request_audit`.

### Managed operation policy

The signed document is declarative data. It cannot carry scripts, templates, regular expressions, remote URLs, executable code, or provider credentials.

Managed v1 operations may:

- disable an existing tool;
- disable an existing harness system part;
- disable an existing harness injected message block through `message_block_toggle` when the exact preimage digest matches;
- replace an existing tool description, harness system part, or harness injected message block through `tool_description`, `system_part_text`, or `message_text`, respectively, when the exact preimage digest matches and canonical character count does not increase.

Managed v1 operations may not:

- add or enable a tool, message, or system part;
- The validation boundary forbids targeting `messages[]` except for `message_block_toggle` and `message_text` operations when the target block's canonical content digest equals the operation's published `preimage_sha256`; a published preimage can match only harness injected boilerplate, including system reminder blocks and hook text, never genuine user text, so user speech remains protected by construction.
- target tool arguments or tool results;
- change sampling or provider extras;
- carry project paths, workspace ids, provider account ids, or machine ids;
- apply partially after a selector or preimage mismatch.

Browser recorded overlay drafts retain the existing broader `Override` vocabulary in local storage. They have no acquisition or apply path in v1. The managed subset is enforced at the artifact validation boundary.

### Local selectors

The remote artifact contains variants. Variant selection happens on the client and sends no selector data back to the registry.

The request fingerprint is `canonical_digest` over harness controlled structure only: provider, ordered system part digests, ordered tool name, description and schema digests, message role and block kind structure, and provider extra keys. User text, assistant text, tool arguments, and tool results are excluded.

System part and message block targets are content addressed against the original IR before any mutation. `system_part_toggle` and `system_part_text` resolve `system:sha256:{canonical_digest}`. `message_block_toggle` and `message_text` resolve `msg:sha256:{canonical_digest}`. No positional fallback exists. A target is missing when no system part or message block hashes to the target digest.

The managed layer first requires the exact request fingerprint, then resolves every content digest target and checks every `preimage_sha256` atomically. A request fingerprint mismatch records `fingerprint_unmatched`. A missing target or preimage mismatch records `preimage_mismatch`, and none of the managed variant applies. The live standing edit layer uses the same content digest target resolution. It has no request fingerprint or separate preimage field, so a missing target produces no mutation and a zero delta audit entry.

Resolution order:

1. Exact request fingerprint plus exact model id.
2. Exact request fingerprint with an empty `model_ids` list.
3. `PASSTHROUGH`.

There is no nearest model, model family, or fuzzy fingerprint fallback. An off catalog model may match rule 2. Catalog membership never affects launch.

### Initial identity publication

The first published artifact operations are identity operations derived from the worksheets at commit `ca3eaec7`: every after equals its captured before, and every operation carries that field's published preimage. They are real `APPLY` operations. Audit records them as applied with zero character delta, serialized provider bytes remain unchanged, and the chip shows `Optimization · APPLY · optimized`. This proves fetch, verification, cache, freeze, apply, audit, and human status before any payload change. Token savings begin only when a later signed artifact first publishes an after that differs from its captured before.

## Client behavior

### Refresh

The Gateway schedules refresh:

1. after the existing startup harness state pass reports an exact normalized version;
2. after capture preparation carries a `CompatibilityGateDecision.normalized_version` that differs from the last scheduled tuple;
3. after an explicit local refresh request.

`gate_launch_preparation` is the sole production owner of the launch version. Its production caller is `cli/launch_runtime.py:prepare_launch`; captured runs reach it through `captured/context.py:_prepare_launch_state`. The captured cross plane carry is explicit:

`CompatibilityGateDecision.normalized_version` → `LaunchPreparation.compatibility` → `CapturedRunContext.prepared.compatibility` → `CapturedRunSpawnSpec.harness_version` → `capture_spawn_spec_payload.harnessVersion` → TypeScript `CapturedRunSpawnSpec.harnessVersion` → `CaptureRpcClient` → `RunManager.createNew` → `OverlaySyncService.schedule`.

The new fields extend existing DTO owners. `RunManager.createNew` schedules refresh after capture preparation and does not await it. A null normalized version schedules no remote fetch and records `harness_version_unknown`. No participant runs `--version` again.

Concurrent refreshes for one tuple collapse into one task. The client uses bounded timeouts, exponential backoff, and jitter. Startup and launch never await the task. V1 has no push channel and no mandatory periodic timer.

The Gateway fetches bytes. The capture plane validates and owns the accepted cache. A failed candidate never overwrites a last known valid entry.

### Cache

The cache root is derived once from `ChannelSpec.home`, under `overlay-cache/v1`. Stable, preview, and dev remain isolated. Raw tenant and seat identifiers do not appear in filenames. Cache keys use a digest of the signed tenant subject plus opaque harness and exact version.

Writes use a temporary file, file sync, atomic replace, directory sync, and restrictive file mode. A metadata record stores ETag, accepted revision, content digest, expiry, validation time, and refresh time. Account tokens and operation audit values are absent.

On restart, the capture plane revalidates a held entry before activation. An unreadable or invalid entry yields `PASSTHROUGH` and remains diagnostic evidence. It is never executed.

### State machine

| Mode | Entry | Request behavior | Exit |
| --- | --- | --- | --- |
| `PASSTHROUGH` | No accepted exact artifact, disabled artifact, unknown version, invalid candidate, expired cache, entitlement failure, unmatched selector, unrecognized payload, or application failure | Forward original bytes. Record a stable reason. Launch continues. | A valid exact artifact becomes accepted for a later run. |
| `VERIFIED` | A locally accepted artifact exists for the exact tuple | No request uses it until run freeze. | Capture preparation freezes it, or expiry and revocation return the tuple to `PASSTHROUGH`. |
| `FROZEN` | One accepted revision is recorded for a run and its managed snapshot is installed | Each recognized request selects and validates one variant locally. Successful application emits audit. Any request level failure uses `PASSTHROUGH` for that request. | Run exit only. Refresh cannot mutate the run. |

`PASSTHROUGH` reasons are a closed Overlay owned union in `@tm/contract/overlay`. Required v1 reasons include `disabled`, `cache_miss`, `registry_unavailable`, `account_unavailable`, `artifact_missing`, `artifact_expired`, `artifact_invalid`, `signature_untrusted`, `revision_rollback`, `harness_version_unknown`, `exact_release_unavailable`, `store_disabled`, `model_unmatched`, `fingerprint_unmatched`, `payload_unrecognized`, `preimage_mismatch`, and `application_failed`.

The literal `PASSTHROUGH` is single sourced in `@tm/contract/overlay` and mirrored into Python through one contract fixture with a conformance test. No alternative spelling appears in state, API, audit, or UI copy.

Every reason has one recording home:

| Reasons | Recording owner | Rule |
| --- | --- | --- |
| `disabled`, `cache_miss`, `registry_unavailable`, `account_unavailable`, `artifact_missing`, `artifact_expired`, `artifact_invalid`, `signature_untrusted`, `revision_rollback`, `harness_version_unknown`, `exact_release_unavailable` | `api/src/transport_matters/harnesses/compatibility_facts.py:CompatibilityFactArtifact` through `compatibility_fact_artifact` and `write_compatibility_facts` | Required per run outcome, including absent release and unresolved observation |
| `store_disabled`, `model_unmatched`, `fingerprint_unmatched`, `payload_unrecognized`, `preimage_mismatch`, `application_failed` | `api/src/transport_matters/overrides/audit.py:OverrideAudit` and `api/src/transport_matters/overrides/audit.py:identity_audit`, persisted by `api/src/transport_matters/exchange_recorder/artifacts.py:build_request_artifacts` as `request_audit` | Required per request zero delta outcome, including disabled store and caught application exception branches |

The accepted cache metadata retains the last acquisition reason so capture preparation can freeze `registry_unavailable`, `account_unavailable`, or `artifact_missing` even when no document exists. Request reasons never rewrite the frozen run artifact.

### Per run freeze

Choice for v1: extend the existing compatibility fact artifact and writer contract to admit unresolved outcomes. No other freeze owner is introduced.

`CompatibilityFactArtifact` becomes schema v2 with required `run_id`, `harness_id`, `recorded_at`, and overlay outcome fields. Resolved compatibility evidence moves into an optional nested value. `release_id`, release digests and revisions, normalized version, executable path, and observation revisions may be absent only when the recorded reason explains why resolution failed.

`compatibility_fact_artifact` accepts `CompatibilityGateDecision`, optional release, optional observation, and the overlay resolution. It returns a valid artifact for every registered gated run. `compatibility_service.py:_record` removes its current release plus installed observation write condition and calls the evolved builder for every `CompatibilityGateDecision`. `harness_version_unknown` and `exact_release_unavailable` therefore have the same atomic writer and audit mirror as resolved runs.

`gate_launch_preparation` receives an injected local overlay resolver. It invokes that resolver after compatibility observation and before `_record`. The resolver reads accepted cache only and performs no registry I/O. Missing or unresolved version facts produce `PASSTHROUGH`. `None` remains reserved for an unregistered harness, client disabled launch, or dry run. An advisory internal failure attempts a minimal unresolved outcome through the same fact writer before launch proceeds.

Capture preparation performs a local lookup after the existing harness observation and before provider traffic:

1. Resolve the exact normalized harness version through `match_release` facts.
2. Select the accepted cache entry for the tenant, harness, and exact version.
3. Revalidate identity, revision, expiry, digest, and signature.
4. Record `PASSTHROUGH` or the accepted artifact reference in `CompatibilityFactArtifact`.
5. Install the managed layer through the existing atomic override snapshot path.
6. Freeze facts with `write_compatibility_facts`.
7. Continue launch regardless of the overlay outcome.

Steps 4 through 6 form one staged capture operation. The fact payload is prepared before state changes. The effective snapshot is installed before provider traffic, then the fact file is atomically published. Any install or publish failure restores or disables the managed scope and yields `PASSTHROUGH`. A run may never retain managed mutations without the matching frozen artifact reference.

The compatibility fact schema records:

- overlay mode and reason;
- artifact id, revision, content digest, tenant subject digest, harness, and exact version when present;
- accepted source, which is `cache` for run application;
- freeze time;
- managed operation count and selected variant ids without operation values.

An identical retry is idempotent. Divergent facts are rejected. The rejection changes overlay state to `PASSTHROUGH` for launch and never blocks the harness process.

### Composition and application

`OverrideStore` owns two active v1 layers, strongest first:

1. live breakpoint edit;
2. frozen managed artifact.

The strongest value wins for the same `(kind, target)`. System part and message block targets in both layers are canonical content digests. Composition happens before `run_pipeline` reads the store. `apply_overrides` still owns operation execution order after source composition.

Managed `fingerprint_unmatched` handling and atomic preimage checks remain mandatory. A mismatch applies none of the managed variant. An existing live breakpoint edit may still apply only when its content digest target exists in the current request, and retains its own audit. Without a matching live edit, the request result is `PASSTHROUGH` with byte identical provider traffic.

`run_pipeline` calls `apply_overrides` once with the effective list. Any exception returns the original IR. HTTP and Codex WebSocket handlers retain the original raw frame unless a curated IR was produced successfully.

Audit extends the existing `OverrideAudit` output with artifact reference, source layer, selected variant, `publisher`, `author`, `author_kind`, `approver`, `signing_key_id`, and `PASSTHROUGH` reason. `identity_audit` gains the same zero delta outcome fields so caught failures remain visible. Audit never stores account tokens or rejected artifact operation values.

V1 renders the current mode and reason through a minimal existing product surface chip, for example `Optimization · PASSTHROUGH · artifact missing`. Inspector binds the chip to `www/packages/inspector/src/components/ExchangeDetail.tsx:ExchangeDetail`; Canvas binds it to `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel`. Each plane consumes the shared status contract through its existing data seam. Inspector never imports Canvas. The chip reads `GET /v1/overlays/status`, introduces no new policy, and must match the recorded reason.

## Privacy boundary

The registry receives only:

- short lived TM account credential;
- opaque harness string;
- exact normalized harness version;
- supported artifact representation;
- conditional ETag.

The client never uploads automatically:

- raw wire requests or responses;
- transcripts or terminal output;
- user, assistant, tool argument, or tool result content;
- system prompts or local tool descriptions;
- breakpoint drafts, local recorded overlays, audits, or request fingerprints;
- provider credentials, cookies, runtime homes, environment variables, project paths, workspace ids, repository names, or machine identifiers.

Artifact generation uses TM controlled harness corpus outside the registry request path. The registry performs tenant lookup and static byte delivery only.

## Open decisions for Stuart

These decisions remain open. Implementation starts after Stuart records each choice.

### 1. Org channel in v1

Choice: ship the vendor managed layer plus current local breakpoint behavior, or include an organization publication channel.

Recommendation: ship vendor plus local in v1. Here local means current live breakpoint editing; recorded overlay drafts remain inert. This satisfies the privacy split, removes organization precedence from the first registry release, and keeps deliberate publication outside scope. Preserve channel in the artifact provenance schema so an org channel can be added without changing request application.

### 2. Registry and accounts topology

Choice: one deployable service, or separate registry and licensing or accounts services.

Recommendation: when remote transport ships, start with one deployable service containing registry, identity, entitlement, and audit modules behind explicit interfaces. Keep the access token contract independent of deployment so the modules can split later without changing clients. The signing authority remains a separate trust boundary under either choice.

### 3. Trust root mechanics

Choice: key custody, rotation, accepted algorithms, revocation, and the meaning of re signing immutable artifacts. This also determines how a later org channel receives authority.

Recommendation: ship an offline root public key with TM, use a constrained online intermediate held in KMS or HSM for artifact signatures, and distribute root signed keyset updates. Keep old verification keys through the longest artifact lifetime. Re signing preserves the immutable content digest and creates a new signed envelope revision. A later org channel should use a separately delegated org key with an explicit scope, never the vendor signing key.

### 4. Entitlement lapse and offline grace

Choice: enter `PASSTHROUGH` immediately on entitlement failure, or allow a bounded cached artifact grace window before `PASSTHROUGH`.

Pending decision, the deterministic v1 baseline is immediate `PASSTHROUGH` on `403`. The cache stays on disk for diagnostics and cannot apply.

Recommendation: use a signed grace deadline carried with the tenant resolved artifact. A lapsed seat may use the exact cached artifact until the earliest of the signed grace deadline, artifact expiry, or harness version change. The human surface shows the lapse and deadline throughout grace. After that instant the state is `PASSTHROUGH`. A local clock derived grace value or an unsigned `403` never extends authority.

## Explicitly out of v1

- Automatic or silent upload of any local recorded layer.
- Acquisition, activation, or request application of browser recorded overlay drafts.
- Deliberate user or organization publication endpoints and curation UI.
- Server side overlay generation, analysis, personalization, inference, or request fingerprinting.
- Per request registry calls, live push, streaming registry updates, or request time entitlement checks.
- Version ranges, nearest version, model family fallback, fuzzy selectors, or cross version artifact reuse.
- A second override interpreter, audit engine, version probe, signature validator, active overlay store, or per run freeze file.
- Remote scripts, templates, regular expressions, executable logic, or emergency unsigned artifacts.
- Billing, checkout, seat administration UI, and license metering details.
- A UI redesign beyond the required minimal human visible mode and reason chip.
- Backward compatibility migration for draft formats. The product is pre release.
- Organization channel implementation until Open Decision 1 is resolved.

## PR sized slice plan

Each slice is independently reviewable. `just test-affected` is the inner loop. `just check` and `just test` are required local gates for every slice. CI is the verdict.

Open Decision 3 must be recorded before Slice 2. Slice 1 uses a test only verifier and cannot make production `APPLY` reachable. Slice 2 is a hard dependency of Slices 4, 6, 7, and 8. No production cache, freeze, or application slice begins while `RejectAllSignatureVerifier` remains the packaged verifier. Pending Open Decision 4, all entitlement tests use immediate `PASSTHROUGH` on `403`.

### Slice 1: Contract and shared signed validation

Scope:

- add `@tm/contract/overlay` with DTOs, branded aggregate ids, modes, reasons, provenance, and fixtures;
- evolve the Python Pydantic artifact contract with strict fields;
- refactor shared signed update rules under `validate_channel_update` without changing its authority;
- exercise valid signatures only through an explicit test verifier;
- retain `RejectAllSignatureVerifier` as the production verifier for this slice.

Tests:

- TypeScript and Python fixture parity;
- unknown field and unknown schema rejection;
- bad digest, signature, expiry, tenant, exact tuple, and minimum version rejection;
- equal or lower revision rollback rejection;
- signed `PASSTHROUGH` artifact acceptance through the test verifier;
- `author`, `author_kind`, `approver`, `publisher`, and `signing_key_id` round trip;
- import graph enforcement for `@tm/contract/overlay`.

Gates: `just check`, `just test`, then CI.

### Slice 2: Production trust root and verifier swap

Scope:

- implement the trust root, keyring, algorithms, rotation, and re signing semantics selected in Open Decision 3;
- install the production verifier at the existing `SignatureVerifier` swap point;
- use the same verifier for compatibility and overlay signed updates;
- retain `RejectAllSignatureVerifier` only as the safe fallback when no trusted root is configured;
- prove one packaged production fixture reaches validation without a test override.

Tests:

- packaged trusted fixture accepted by the production verifier;
- tampered payload, unknown key, revoked key, unsupported algorithm, and invalid signature rejected;
- rotation and re signing behavior matches the recorded decision;
- missing trust configuration selects `RejectAllSignatureVerifier` and keeps `APPLY` unreachable;
- compatibility and overlay validators share the same keyring and canonical bytes.

Gates: `just check`, `just test`, then CI. Production `APPLY` work remains blocked until this CI passes.

### Slice 3: Overlay product context, configuration, and local disk registry bridge

Scope:

- add canonical `packages/overlay` context shape;
- add `Settings.overlay_registry_url`, `[overlay].registry_url`, `env_keys.py:OVERLAY_REGISTRY_URL`, and `config.py:resolve_overlay_registry_url`;
- pass the one resolved URL through Gateway supervision so TypeScript performs no precedence logic;
- implement one registry HTTP adapter behind a port;
- mount a disk adapter through `packages/gateway/src/app.ts:buildGateway` that serves packaged artifact files beneath `docs/overlays/` with the registry endpoint and ETag contract;
- implement ETag refresh scheduling, deduplication, timeout, backoff, and sanitized status;
- mount the router through `packages/gateway` package exports only;
- keep account token ownership outside browser and harness homes.

Tests:

- environment URL wins over TOML and missing URL disables refresh;
- Python and TypeScript consume the same resolved base URL;
- local `200` bytes equal the packaged artifact file, matching `If-None-Match` returns `304`, and changing the base URL selects a remote fixture without client changes;
- `200`, `304`, `401`, deterministic `403`, `404`, `406`, timeout, and `5xx` behavior;
- one in flight fetch per exact tuple;
- no model, request fingerprint, path, provider identity, or user content on the request;
- Gateway mount and local status or refresh route contract;
- context boundary and deep import rejection.

Gates: `just check`, `just test`, then CI.

### Slice 4: Capture validation and accepted cache

Dependency: Slice 2 production verifier CI is green.

Scope:

- extend the capture RPC with validate, install, and metadata ports;
- validate through the shared compatibility rules and production verifier;
- persist one accepted cache under `ChannelSpec.home` with atomic writes;
- retain the last valid entry after any invalid candidate;
- expose only sanitized metadata to the product context.

Tests:

- channel isolation for stable, preview, and dev;
- atomic write recovery and restrictive permissions;
- invalid candidate cannot replace valid cache;
- restart revalidation through the production verifier;
- ETag has no authorization effect;
- account token and operation values never persist in metadata.

Gates: `just check`, `just test`, then CI.

### Slice 5: Refresh seam, exact version carry, and launch advisory behavior

Scope:

- extend `refresh_harness_state` with the injected overlay refresh notification;
- preserve `run_startup_refresh` failure isolation;
- carry `CompatibilityGateDecision.normalized_version` across `LaunchPreparation`, Python and TypeScript `CapturedRunSpawnSpec`, `capture_spawn_spec_payload`, and `CaptureRpcClient`;
- schedule `OverlaySyncService` from `RunManager.createNew` after capture preparation without awaiting it;
- keep every refresh asynchronous and outside launch authority.

Tests:

- startup schedules each observed exact tuple once;
- captured launch carries the gate produced version unchanged through every DTO and parser;
- no second binary probe occurs on the refresh path;
- one harness refresh failure does not suppress other harnesses;
- registry outage cannot fail startup;
- null normalized version and a newly observed exact version both launch in `PASSTHROUGH`;
- off catalog and unknown models never enter the remote key and never block launch.

Gates: `just check`, `just test`, then CI.

### Slice 6: Unresolved run facts and two layer snapshot composition

Dependency: Slice 2 production verifier CI is green.

Scope:

- evolve `CompatibilityFactArtifact` to schema v2 with optional resolved evidence and required overlay outcome;
- make `compatibility_fact_artifact` and `compatibility_service.py:_record` write every gated outcome, including unresolved release and observation;
- extend `OverrideStore` with managed and live layers only;
- extract one atomic snapshot install helper from the existing overrides API path;
- send one effective flat snapshot through `SharedProxyManager.set_overrides`.

Tests:

- `harness_version_unknown` and `exact_release_unavailable` both write durable facts;
- every acquisition `PASSTHROUGH` reason maps to the compatibility fact artifact;
- identical freeze retry is idempotent and divergent rewrite is rejected;
- late refresh never changes a frozen run;
- live edit wins over managed for duplicate keys;
- no local recorded overlay acquisition or apply path exists in v1;
- install rollback restores or disables the managed snapshot;
- shared proxy restart rehydrates the same effective snapshot;
- no sibling run fact file or second active store exists.

Gates: `just check`, `just test`, then CI.

### Slice 7: Local application, audit, and human state

Dependency: Slice 2 production verifier CI is green.

Scope:

- resolve exact local variants and preimages before application;
- **Content hash target pinning:** migrate live standing edits for system parts and message blocks from positional targets to `canonical_digest` content targets, using the same target resolver as the managed layer;
- pass one effective list through `run_pipeline` and `apply_overrides`;
- `api/src/transport_matters/request_pipeline.py:run_pipeline` narrows its `OverrideAudit | None` return contract: the disabled store and exception branches return a real zero delta `OverrideAudit` carrying `store_disabled` and `application_failed`, respectively, and `api/src/transport_matters/exchange_recorder/artifacts.py:build_request_artifacts` persists that object as `request_audit`.
- extend `OverrideAudit` and `identity_audit` with reason plus `publisher`, `author`, `author_kind`, `approver`, and `signing_key_id`;
- expose frozen run state through the local status API; bind the Inspector chip to `www/packages/inspector/src/components/ExchangeDetail.tsx:ExchangeDetail` and the Canvas chip to `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel`, with no cross plane import;
- prove Claude HTTP and Codex WebSocket behavior through the real capture seam.

Tests:

- matching managed variant applies once with complete provenance audit;
- fingerprint, model, payload vocabulary, and preimage mismatches produce recorded `PASSTHROUGH`;
- managed `message_block_toggle` and `message_text` apply only to a matching harness injected block preimage; a genuine user block remains unchanged and records `preimage_mismatch`;
- live demo regression from run `163c35b4`: a title turn standing edit pinned to its system part digest does not apply to the main turn shape and cannot produce the observed `chars_delta -17574`;
- a missing live system part or message block content target produces no mutation and a zero delta audit entry;
- disabled store and caught application failure branches produce zero delta `identity_audit` values with `store_disabled` and `application_failed`, and `build_request_artifacts` persists each as `request_audit`;
- malformed or unrecognized HTTP and Codex payloads preserve original bytes;
- application exception preserves original bytes;
- a new model and a new harness version launch and run in `PASSTHROUGH`;
- cached artifact works during registry outage;
- cold cache and outage still launch;
- status API, Inspector `ExchangeDetail`, and Canvas `ExchangeInspectPanel` show the same `PASSTHROUGH` reason;

Gates: `just check`, `just test`, then CI.

### Slice 8: Identity artifact release and end to end proof

Dependency: Slices 1 through 7 are green.

Scope:

- publish signed identity artifacts beneath `docs/overlays/` from the `ca3eaec7` worksheets, with each after equal to its captured before and each field carrying its worksheet preimage;
- package the files and serve them through the local Gateway disk adapter;
- prove fetch, verify, cache, freeze, apply, audit, and chip through the real capture seam.

Tests:

- applied identity operations appear in request audit with zero character delta;
- HTTP bytes and Codex WebSocket frames equal the captured pre application bytes;
- Inspector and Canvas chips show `Optimization · APPLY · optimized`;
- packaged `desktop · standalone` reaches an exited captured run through the local disk registry.

Gates: `just check`, `just test`, then CI. The packaged `desktop · standalone` job is the end to end verdict.

## Completion criteria

V1 is complete when all statements below are proven.

1. The v1 local Gateway disk adapter and deferred authenticated remote registry return the same static signed immutable artifact bytes selected by tenant, opaque harness, and exact normalized version, with identical endpoint and ETag semantics.
2. Registry, account, entitlement, signature, cache, selector, vocabulary, and application failures converge on exact state `PASSTHROUGH`.
3. Every `PASSTHROUGH` provider request preserves the original HTTP bytes or Codex WebSocket frame.
4. A launch never waits for registry I/O and never fails because an overlay is missing, invalid, stale, unknown, or unmatched.
5. Unknown and off catalog models remain launchable. Model is absent from the remote key and catalog membership remains advisory.
6. An unrecognized or newly released harness version remains launchable. It uses `PASSTHROUGH` until an exact signed artifact is locally accepted for a later run.
7. Production `APPLY` is reachable only through the trust root and verifier installed at the existing `SignatureVerifier` swap point. `RejectAllSignatureVerifier` remains the safe no trust fallback.
8. The accepted cache is signature verified, revision protected, channel isolated, atomically written, and retained across registry outage.
9. Every registered gated run freezes an overlay outcome in the evolved `CompatibilityFactArtifact`, including `harness_version_unknown` and `exact_release_unavailable`. No sibling freeze file exists.
10. Every enumerated `PASSTHROUGH` reason lands in either the per run compatibility fact artifact or the per request `OverrideAudit` and exchange `request_audit`, including `store_disabled` and `application_failed` from `run_pipeline`.
11. `OverrideStore` is the only active composition owner. V1 has two active layers, live breakpoint edit above frozen managed artifact. Shared proxy and request handlers contain no merge policy.
12. Browser recorded overlay drafts remain local and have no v1 acquisition, activation, or application path.
13. `run_pipeline` and `apply_overrides` remain the only request mutation and execution path.
14. Artifact and exchange provenance carries `publisher`, `author`, `author_kind`, `approver`, and `signing_key_id`.
15. The client sends no model, request fingerprint, captured bytes, transcript, content, path, provider identity, or local recorded overlay to the registry.
16. The server performs no computation on user data and exposes no v1 mutation endpoint.
17. One `config.py` resolver owns registry base URL precedence. Environment wins over TOML, both planes consume the resolved value, and remote migration changes only that URL.
18. The current `PASSTHROUGH` mode and reason reach a human through the required minimal chip owned by `www/packages/inspector/src/components/ExchangeDetail.tsx:ExchangeDetail` and `www/packages/canvas/src/viewers/resource/ArkExchangePanels.tsx:ExchangeInspectPanel`. Recorded but unseen state fails completion, and Inspector never imports Canvas.
19. Cross package and cross language literals, especially `PASSTHROUGH`, have one contract owner and passing conformance tests.
20. Managed and live system part and message block operations use canonical content digest targets with no positional fallback. Managed request fingerprint and atomic preimage guards remain mandatory.
21. The signed identity artifact traverses fetch, verify, cache, freeze, apply, audit, and chip. Audit records applied operations with zero character delta, wire bytes remain unchanged, and the chip shows `Optimization · APPLY · optimized`.
22. Every slice passes `just check` and `just test`. CI passes, including `desktop · standalone`.
