# TM overlay server service, v1 architecture

## Thesis

Keep publication online and request mutation offline. The service resolves tenancy and exact harness releases into a signed effective overlay. The Gateway refreshes that artifact in the background. The capture plane applies only a verified local match, so no provider request ever waits on the network.

## Verified starting point

The current source establishes these constraints:

- `api/src/transport_matters/overrides/__init__.py:Override` is the executable instruction shape: `kind`, `target`, and scalar `value`.
- `api/src/transport_matters/overrides/__init__.py:apply_overrides` is the single transformation engine. It preserves original index semantics, applies fixed kind priority, and produces `OverrideAudit`.
- `api/src/transport_matters/overrides/audit.py:OverrideAudit` is request dependent evidence. It records each attempted operation, whether it applied, and before and after character totals.
- `api/src/transport_matters/request_pipeline.py:run_pipeline` is the request mutation gate. A disabled store or any failure forwards the original IR.
- `api/src/transport_matters/overrides/state.py:OverrideStore` owns current in process, run and track scoped breakpoint edits.
- `www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` owns browser drafts and confirmed local bundles. Its own comment says application at intercept is outside that slice.
- `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:BreakpointEditor.handleSaveAsOverlay` already converts the current breakpoint `Override[]` into a draft.
- `api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation` already performs the bounded harness observation at launch.
- `api/src/transport_matters/harnesses/compatibility_service.py:CompatibilityGateDecision.normalized_version` already carries the normalized observed version. The overlay feature must not run a second version probe.
- `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` already proves the useful signed update rules: strict schema, trusted signature, monotonic sequence, expiry, minimum TM version, and digest integrity.
- `api/src/transport_matters/harnesses/compatibility_store.py:RejectAllSignatureVerifier` confirms that no production trust root exists yet. Mutable signed data is currently rejected.
- `api/src/transport_matters/channel.py:ChannelSpec.home` and `api/src/transport_matters/storage_roots.py:default_storage_root` own channel isolated homes. Stable resolves to `~/.transport-matters`; preview and dev remain isolated.
- The repository has owner scoped local records and bearer protected control plane grants. It has no account, organization, seat, entitlement, or remote tenant authority. `owner="local"` must never be promoted into cloud identity.

## Ownership and process split

### Cloud overlay service

The cloud service owns accounts, entitlements, tenant authorization, immutable overlay artifacts, mutable publication pointers, signing, and publication audit history. Overlay bytes never ship in the TM binary or release.

Store three resources:

1. `OverlayArtifact`
   - Immutable and content addressed by `document_digest`.
   - Holds one strict overlay document with one or more request variants.
   - May be deduplicated across publications because tenant access is checked through the pointer, never by artifact digest alone.
2. `OverlayPublication`
   - Mutable signed pointer keyed by tenant subject and exact harness release.
   - Fields: subject, `harness_id`, exact normalized `harness_version`, `sequence`, status, artifact digest, publication time, expiry, minimum TM version, and detached signature.
   - Status is `active`, `empty`, `paused`, or `revoked`. A signed empty or revoked pointer safely supersedes an older active cache.
3. `OverlayPublicationEvent`
   - Append only audit record for create, publish, supersede, revoke, signer, actor, and prior sequence.

The service materializes one effective artifact for a seat. Layer precedence is fixed server side:

1. TM managed baseline
2. Organization publication
3. Seat personalization

Within a matching request variant, later layers replace earlier values by the existing override key `(kind, target)`. The client receives one final document and has no tenant merge policy.

### Local product plane

A new `@tm/overlay` context under `packages/overlay` owns account aware remote fetch, conditional refresh, upload, cache metadata, and the local status API. It follows the canonical context package shape. The Gateway only constructs and mounts it.

`packages/gateway/src/main.ts:runGatewayProcess` starts and closes the sync service. `packages/gateway/src/app.ts:buildGateway` mounts its router. `api/src/transport_matters/gateway_supervisor.py:plan_gateway_supervision` passes the resolved channel cache directory explicitly, which avoids a second TypeScript implementation of channel path rules.

The Gateway is the only network caller and the only disk writer for the remote catalog. Writes use a temporary file, file sync, atomic rename, directory sync, and mode `0600`. The cache file is a cross process contract with one writer.

### Local capture plane

The capture plane owns verification and application. It reads the last complete cache, verifies it before activation, retains the last verified in memory value across invalid replacements, and never makes a remote call.

`api/src/transport_matters/request_pipeline.py:run_pipeline` remains the one request gate. It asks one resolver for the effective `Override[]`, then calls `api/src/transport_matters/overrides/__init__.py:apply_overrides` once.

Precedence at that seam is explicit:

1. Signed effective service overlay
2. Explicit breakpoint edits in `api/src/transport_matters/overrides/state.py:OverrideStore`

Breakpoint edits win by `(kind, target)` because they are the human's current action. They remain ephemeral. Saving and publishing moves the standing policy to the service. This keeps the browser draft store and the in process breakpoint store from becoming competing durable writers.

The single `Enable optimization` preference gates the resolver. When off, `run_pipeline` forwards the original IR. There are no per artifact enable switches. Entitlement loss, missing cache, expired pointer, invalid signature, unknown schema, unmatched fingerprint, and revoked publication all produce an identity result with a reason. They never prevent provider traffic.

## Resource keying

### Server keys

The remote lookup key is:

`(org_id, seat_id, harness_id, exact_harness_version)`

- `org_id` and `seat_id` come only from verified access token claims.
- The service never accepts either identity as a query parameter or request body authority.
- `harness_id` and exact normalized `harness_version` are explicit request parameters.
- Exact equality is the v1 rule. A `2.1.224` artifact never applies to `2.1.225`, even if the versions appear adjacent.
- Channel is absent from the service key. Channel selects the local cache root. It is a TM installation concern rather than overlay content identity.
- Project `cwd` is absent from the service key. Existing `OverlayScope` is a local editor scope and machine paths are unsuitable tenant identity. Publishing promotes the draft to organization scope.

### Local selectors

Model and request fingerprint resolve locally inside the signed artifact. Neither causes a network request.

Each variant contains:

- `fingerprint_schema_version`
- `request_fingerprint`
- optional exact `model_ids`
- `overrides: Override[]`

The fingerprint is `canonical_digest` over the harness controlled request skeleton: provider, ordered system content digests, ordered tool name plus description plus schema digests, message role and block kind structure, and provider extra keys. User text, assistant text, tool arguments, and tool results are excluded. `api/src/transport_matters/canonicalization.py:canonical_digest` supplies canonical hashing.

Resolution order is exact fingerprint plus exact model constraint, exact fingerprint with no model constraint, then no match. There is no nearest version, nearest model, or fuzzy fingerprint fallback. Sparse Codex turns naturally select a sparse variant or produce a visible no op.

This split keeps tenancy and release assignment server side while keeping model details and live request topology off the fetch path.

## Overlay document and versioning

The service returns a signed envelope containing one publication pointer and its artifact:

```json
{
  "envelope_schema_version": 1,
  "publication": {
    "org_id": "org_123",
    "seat_id": "seat_456",
    "harness_id": "claude",
    "harness_version": "2.1.225",
    "sequence": 18,
    "status": "active",
    "artifact_digest": "<sha256>",
    "minimum_transport_matters_version": "1.0.0",
    "published_at": "2026-08-07T00:00:00Z",
    "expires_at": "2026-08-14T00:00:00Z",
    "signature": "ed25519:key-2026-01:<base64url>"
  },
  "artifact": {
    "document_schema_version": 1,
    "override_schema_version": 1,
    "artifact_id": "ova_123",
    "revision": 4,
    "source": "effective",
    "harness_id": "claude",
    "harness_version": "2.1.225",
    "variants": [
      {
        "fingerprint_schema_version": 1,
        "request_fingerprint": "<sha256>",
        "model_ids": [],
        "overrides": [
          {"kind": "tool_toggle", "target": "tool:WebSearch", "value": false}
        ]
      }
    ],
    "document_digest": "<sha256>",
    "signature": "ed25519:key-2026-01:<base64url>"
  }
}
```

Version fields have separate jobs:

- Envelope schema version controls transport shape.
- Document schema version controls artifact fields.
- Override schema version controls the existing `Override` vocabulary.
- Fingerprint schema version controls selector construction.
- Artifact revision is immutable history for one logical artifact.
- Publication sequence prevents rollback for one server key.
- Exact harness version controls release applicability.
- Minimum TM version prevents an older client from interpreting a newer contract.

The document embeds the existing `Override` shape unchanged. `OverrideAudit` stays out of the signed document because it depends on the actual request. The client generates it on every application through `apply_overrides`. The exchange should record artifact id, revision, digest, fingerprint, and match reason beside that audit so applied and no op outcomes are attributable.

## Signing and verification

Reuse the compatibility mechanism, with a shared trust primitive rather than a second implementation.

1. Extract the generic `SignatureVerifier` contract from `api/src/transport_matters/harnesses/compatibility_store.py:SignatureVerifier` into a pure source root owner such as `api/src/transport_matters/signed_artifacts.py:SignatureVerifier`.
2. Add `Ed25519SignatureVerifier` there. Its trusted public key ring ships with TM. Public keys are safe distribution content; overlay documents remain service content. The `signature` string carries algorithm and key id without changing the verifier call shape.
3. Keep canonical bytes under `api/src/transport_matters/canonicalization.py:canonical_json` and `canonical_digest`.
4. Refactor the monotonic pointer, expiry, and digest checks shared with `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` into the same pure owner. Compatibility and overlays add their domain specific schema and applicability checks around it.
5. Verify artifact signature, artifact digest, pointer signature, pointer sequence, expiry, subject claims, exact harness tuple, supported schemas, and minimum TM version before activation.

Trusted local time is required. Expired or unprovable publications stop mutating and forward the original request. A network outage may continue using an unexpired verified cache. This is fail closed for mutation and fail open for provider traffic.

The service signing key stays in KMS or HSM. The publication transaction commits the artifact, pointer sequence, audit event, and signature together. Key rotation publishes a new key id before use and keeps old public keys through the maximum artifact lifetime.

## Fetch and cache protocol

Remote endpoint:

`GET /v1/overlay-publications/current?harness_id=claude&harness_version=2.1.225`

Request headers:

- `Authorization: Bearer <TM account access token>`
- `If-None-Match: "<held-etag>"` when cached
- `X-TM-Client-Version: <version>` for diagnostics only; compatibility still lives in the signed document

Response rules:

- `200` returns the signed effective envelope and `ETag`.
- `304` means the held signed envelope remains current.
- Missing, revoked, or paused content returns `200` with a newer signed pointer carrying that status. A bare `404` cannot safely retire an old active cache.
- Authentication and entitlement failures return `401` or `403`. The client keeps only an unexpired verified cache and surfaces account state.

The Gateway refreshes:

1. At process start after account identity is available.
2. In the background on every launch, using `If-None-Match` and deduplicating concurrent refreshes for the tuple.
3. Immediately when the authoritative observed harness version changes.
4. On a bounded periodic timer while the app remains open, with jitter and exponential backoff.

Launch never awaits these calls. It reads the exact tuple from the local verified cache. Cold cache means identity for that launch or request. A completed refresh becomes eligible for subsequent requests.

Use the authoritative version already produced by `gate_launch_preparation`. Carry `CompatibilityGateDecision.normalized_version` through `api/src/transport_matters/captured/models.py:CapturedRunSpawnSpec`, `api/src/transport_matters/capture_rpc.py:capture_spawn_spec_payload`, `packages/runtime/src/adapters/CaptureRpcClient.ts:CaptureRpcClient.prepareCapture`, and `packages/runtime/src/service/RunManager.ts:RunManager.createNew`. Runtime then calls the overlay sync port. This avoids another `--version` subprocess.

Cache path:

`<ChannelSpec.home>/overlay-cache/v1/<org-seat-hash>/<harness_id>/<harness_version>/envelope.json`

For stable this is under `~/.transport-matters`. Preview and dev remain under their own homes. The raw account ids need not appear in directory names. Store the ETag next to the envelope or in a small metadata file. ETag is a refresh hint only; signatures authorize content.

## Ad hoc recording and organization publication

The upload path reuses the current inspect, edit, and save workflow:

1. Breakpoint editing continues through `api/src/transport_matters/api/v1/overrides.py:patch_overrides` and `OverrideStore` for live preview.
2. `BreakpointEditor.handleSaveAsOverlay` passes the current `Override[]`, original request fingerprint, observed harness id and version, and optional model selector into `useOverlaysStore.createDraft`.
3. The user confirms organization publication in the overlay route. Local project `cwd` is displayed as provenance but is never the cloud scope key.
4. The browser calls the local `@tm/overlay` Gateway router. The Gateway holds the account token and calls the remote publish endpoint. Provider credentials and browser storage never carry this token.
5. The remote service validates the strict override schema, exact harness tuple, fingerprint format, size limits, tenant permission, and optimistic sequence. It creates an immutable artifact, advances the organization publication, signs both, and returns the effective envelope.
6. The publishing seat atomically caches the returned envelope. Other seats converge through their next conditional refresh.
7. The local draft records server artifact id, revision, digest, and publish status. It does not become a second active execution source.

Only override values and selector digests are uploaded. Raw captured requests, user messages, tool arguments, tool results, wire bytes, and `OverrideAudit` are excluded. Replacement text inside an override may still be sensitive, so organization publication is explicit, encrypted at rest, auditable, and restricted to publish capable members.

## Smallest v1 remote API

### 1. Read current effective publication

`GET /v1/overlay-publications/current?harness_id=<id>&harness_version=<exact>`

- Scope: `overlays:read`
- Tenant and seat: access token claims
- Conditional: `If-None-Match`
- Returns: signed effective envelope or `304`

### 2. Publish or revoke an organization overlay

`POST /v1/org-overlay-publications`

- Scope: `overlays:publish`
- Tenant: access token claim
- Headers: `Idempotency-Key`, `If-Match` with the held organization publication ETag
- Body: status, exact harness tuple, document schema versions, local variants, and optional source exchange reference hashed locally
- Returns: created artifact metadata, advanced organization sequence, and the caller's signed effective envelope
- `status="revoked"` advances a signed tombstone without requiring a separate delete endpoint

No public artifact by digest endpoint exists in v1. It would complicate tenant authorization and allow enumeration. Operator publication of TM managed baselines can use the same service command internally with a service principal.

Authentication uses short lived TM account access tokens issued by the account service. Required claims are `sub` as seat id, `org_id`, entitlement, scopes, issuer, audience, expiry, and token id. The overlay service validates these on every call. Refresh tokens remain in the desktop account credential owner, outside this context and outside harness homes. Claude and Codex provider credentials are never reused.

## New harness release rollout, example 2.1.225

1. TM records representative `2.1.225` exchanges and produces variants for each supported request fingerprint and model constraint.
2. The service validates and signs the artifact, then advances the managed publication for `(harness=claude, version=2.1.225)`.
3. A client launch observes `2.1.225` through the existing compatibility gate. The local exact tuple has no older version fallback, so it forwards unchanged while scheduling refresh.
4. The Gateway issues a conditional GET. A `200` envelope passes signature, digest, subject, sequence, expiry, schema, minimum client, and exact tuple checks before atomic activation.
5. Subsequent matching requests apply the overlay. Unmatched sparse or model specific requests remain unchanged and carry a no match audit reason.
6. Clients with a held artifact receive `304`. Clients still on earlier harness versions continue using their exact version artifacts.
7. A bad overlay is superseded or revoked by a higher signed sequence. Offline clients stop applying it at signed expiry even if they cannot refresh.

This yields convergence without launch blocking, live push infrastructure, or coupling overlay availability to the TM package release.

## Repo binding map

| Responsibility | Existing seam | Binding |
|---|---|---|
| Product context composition | `packages/gateway/src/main.ts:runGatewayProcess` | Construct and close `OverlayService`; pass account, fetch, clock, and cache ports. |
| Local API mount | `packages/gateway/src/app.ts:buildGateway` | Mount the `@tm/overlay` router through the package export only. |
| Channel cache root | `api/src/transport_matters/channel.py:ChannelSpec.home` | Resolve stable, preview, and dev isolation once. |
| Gateway environment | `api/src/transport_matters/gateway_supervisor.py:plan_gateway_supervision` | Pass the resolved overlay cache directory to the product plane. |
| Existing harness observation | `api/src/transport_matters/harnesses/compatibility_service.py:gate_launch_preparation` | Keep the one bounded version probe. |
| Version result | `api/src/transport_matters/harnesses/compatibility_service.py:CompatibilityGateDecision.normalized_version` | Carry the exact normalized version into the capture response. |
| Cross plane launch result | `api/src/transport_matters/captured/models.py:CapturedRunSpawnSpec` | Add normalized harness version as source owned launch evidence. |
| Capture response serialization | `api/src/transport_matters/capture_rpc.py:capture_spawn_spec_payload` | Serialize that field once. |
| Runtime parse | `packages/runtime/src/adapters/CaptureRpcClient.ts:CaptureRpcClient.prepareCapture` | Parse and expose the field through `CapturedRunSpawnSpec`. |
| Launch refresh trigger | `packages/runtime/src/service/RunManager.ts:RunManager.createNew` | Notify the overlay sync port after capture preparation, without awaiting refresh. |
| Canonical signature bytes | `api/src/transport_matters/canonicalization.py:canonical_json` | Reuse for artifact and pointer payloads. |
| Content digest | `api/src/transport_matters/canonicalization.py:canonical_digest` | Reuse for documents and request fingerprints. |
| Trust contract | `api/src/transport_matters/harnesses/compatibility_store.py:SignatureVerifier` | Extract to a shared pure owner and implement Ed25519 once. |
| Signed update rules | `api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update` | Extract generic signature, sequence, expiry, and digest validation; retain compatibility specific checks locally. |
| Request mutation gate | `api/src/transport_matters/request_pipeline.py:run_pipeline` | Resolve one effective list locally and preserve identity on every failure. |
| Transform engine | `api/src/transport_matters/overrides/__init__.py:apply_overrides` | Apply the merged list once. No second transform engine. |
| Request evidence | `api/src/transport_matters/overrides/audit.py:OverrideAudit` | Continue producing request dependent applied and no op evidence; attach publication provenance. |
| Live breakpoint state | `api/src/transport_matters/overrides/state.py:OverrideStore` | Keep only explicit ephemeral run and track edits, with highest local precedence. |
| Live edit transport | `api/src/transport_matters/api/v1/overrides.py:patch_overrides` | Preserve breakpoint editing and preview. |
| Draft creation | `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:BreakpointEditor.handleSaveAsOverlay` | Capture the edited `Override[]` plus release selectors. |
| Draft lifecycle | `www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` | Keep local draft and publish status; never become the managed apply source. |

## Explicit exclusions for v1

- No overlay bytes embedded in the TM distribution.
- No network call from `run_pipeline`, mitmproxy hooks, or provider request handling.
- No version ranges or nearest version fallback.
- No cloud key based on local project path.
- No raw exchange upload.
- No client side tenant merge precedence.
- No push channel. Launch conditional refresh plus bounded background polling is sufficient.
- No second override interpreter or audit implementation.

