# Overlay Registry Slice 4 — source facts

- **SHA**: `cdfac164aaf5f36a463e9fbc1c8359375109cfea` (`feat(overlay): add registry product context (#376)`)
- **Spec**: `~/.mdx/projects/transport-matters-spec-overlay-registry.md` § Slice 4 (Capture validation and accepted cache)
- **Scope of this note**: live writers/readers and precedence only. No design beyond the settled spec.

## Slice 4 settled scope (spec)

Extend capture RPC with validate, install, and metadata ports; validate through shared compatibility rules and production verifier; persist one accepted cache under `ChannelSpec.home` with atomic writes; retain last valid entry after any invalid candidate; expose only sanitized metadata to the product context.

---

## 1. Capture RPC

### Live surface (today)

| Layer | Symbol | Role |
| --- | --- | --- |
| Python routes | `api/src/transport_matters/api/v1/capture_rpc_routes.py` `APIRouter(prefix="/capture")` | Mounted product-internal RPC |
| Routes | `POST /prepare`, `POST /{run_id}/release`, `GET /{run_id}/health` | Only live capture operations |
| Domain registry | `api/src/transport_matters/capture_rpc.py` `CaptureLeaseRegistry` | prepare/release/health/grants; no overlay methods |
| Payload writer | `capture_spawn_spec_payload` | Serializes spawn identity for TypeScript |
| TS client | `packages/runtime/src/adapters/CaptureRpcClient.ts` `CaptureRpcClient` | `prepareCapture`, `releaseCapture`, `captureHealth` only |
| TS port | `packages/runtime/src/ports.ts` `CapturePort` | Same three methods; **no overlay install/status** |
| Composition | `packages/gateway/src/main.ts` `createDefaultRuntimeRouterDeps` | `TRANSPORT_MATTERS_CAPTURE_RPC_URL` → `CaptureRpcClient`; else `StubCaptureAdapter` |
| Stub | `packages/runtime/src/adapters/StubCaptureAdapter.ts` | In-process spawn without Python |

### Writers / readers

| Direction | Who writes | Who reads |
| --- | --- | --- |
| Prepare body | Runtime `RunManager` → `CaptureRpcClient.prepareCapture` | `PrepareCaptureRequest.to_domain` → `CaptureLeaseRegistry.prepare_capture` |
| Spawn response | `capture_spawn_spec_payload` | `CaptureRpcClient` field parsers |
| Release / health | Runtime | `release_capture` / `capture_health` |

### Slice 4 gap (facts)

- **No** capture RPC routes for overlay validate, install, or accepted metadata.
- **No** TS `CapturePort` methods for overlay.
- Spec: validation/install/metadata are **loopback implementation ports**, not remote product API routes. They belong on this capture RPC seam, not on `/v1/overlays/*`.

### Relevant tests

- `api/src/transport_matters/test_capture_rpc.py`
- `api/src/transport_matters/api/v1/test_capture_rpc_routes.py`
- `api/src/transport_matters/api/v1/test_capture_rpc_request_validation.py`
- `api/src/transport_matters/api/v1/test_capture_rpc_worktree_resolution.py`
- `packages/runtime/src/adapters/CaptureRpcClient.test.ts`
- `packages/runtime/src/service/captureRpcLifecycle.test.ts`
- `packages/gateway/src/main.test.ts` (“selects the capture RPC client when TRANSPORT_MATTERS_CAPTURE_RPC_URL is set”)

### Second-writer risk

Low today (no overlay persistence). **High once Slice 4 lands** if any second path validates or writes accepted bytes outside the capture-plane install owner.

---

## 2. `ChannelSpec.home`

### Live owners

| Symbol | Role |
| --- | --- |
| `api/src/transport_matters/channel.py` `ChannelSpec.home: Path` | Sole channel home field |
| `resolve_channel_spec` / `activate_channel` / `all_channel_specs` | Resolution and activation |
| `api/src/transport_matters/channel-specs.json` | Package-owned homes |

### Homes (precedence: package JSON only)

| Channel id | `homeDir` | Resolved home |
| --- | --- | --- |
| `stable` | `.transport-matters` | `Path.home() / ".transport-matters"` |
| `preview` | `.transport-matters-preview` | `Path.home() / ".transport-matters-preview"` |
| `dev` | `.transport-matters-dev` | `Path.home() / ".transport-matters-dev"` |

Build: `_build_channel_spec` sets `home = Path.home() / homeDir`. Distinct homes enforced by `_validate_channel_specs`.

### Spec precedence for accepted cache root

1. Derive once from `ChannelSpec.home`
2. Under `overlay-cache/v1`
3. Stable / preview / dev remain isolated by home
4. TypeScript receives an **opaque local port** and must never derive `~/.transport-matters` or channel paths

### Live readers of `ChannelSpec.home` (non-overlay)

Many existing owners (settings, runtime registry, desktop, CLI). **None** currently append `overlay-cache/v1`. No live symbol implements the overlay accepted cache path.

### Relevant tests

- `api/src/transport_matters/test_channel.py` (home isolation, electron user data under home)

### Second-writer risk

If TypeScript invents a parallel cache root, channel isolation and Python path ownership break. Spec forbids TS path derivation.

---

## 3. Accepted overlay state

### Live product status (Gateway / `@tm/overlay`)

| Symbol | Role |
| --- | --- |
| `packages/overlay/src/service/OverlaySyncService.ts` `statusByRelease: Map` | In-memory product status by release key |
| `schedule` / `refresh` / `statuses` | Writer of map; `statuses()` is product read |
| `packages/overlay/src/projections/status.ts` | `emptyOverlayStatus` (`PASSTHROUGH` + `cache_miss`), `refreshedStatus`, `passthroughStatus`, `hasAcceptedArtifact` |
| `hasAcceptedArtifact` | `artifact !== null && mode !== "PASSTHROUGH"` |
| `packages/overlay/src/gatewayDeps.ts` `NO_ACCEPTED_CACHE` | Default `OverlayCandidatePort`: `currentStatus` → empty; `installCandidate` → empty for release (**discards bytes**) |
| `packages/gateway/src/main.ts` | `createOverlayGatewayDeps({ artifactRoot, registryBaseUrl })` — **does not inject candidates** |

### Live disk accepted cache

**None.** No `overlay-cache` path, metadata record, or revalidation-on-restart owner exists under `ChannelSpec.home`.

### Spec ownership (settled)

- Capture plane **owns** accepted cache bytes and metadata.
- Gateway fetches registry bytes and schedules refresh; it does **not** validate or persist artifacts (`OverlayCandidatePort` comment in `ports.ts`).
- Failed candidate must not overwrite last known valid entry.
- Restart: revalidate held entry before activation; invalid → `PASSTHROUGH`, keep as diagnostic evidence, never execute.

### Precedence for “held” status during refresh

In `OverlaySyncService.refresh`:

1. `candidates.currentStatus(release)` (or empty on throw)
2. Registry fetch with ETag = `held.artifact?.contentSha256 ?? null`
3. `resolveResult` → write `statusByRelease`

### Second-writer risk (highest)

| Writer | What it mutates | Conflict |
| --- | --- | --- |
| Capture plane install (Slice 4 target) | Durable accepted cache under channel home | Spec sole durability owner |
| `NO_ACCEPTED_CACHE.installCandidate` (current default) | Nothing durable; returns empty status | Silent no-op if real adapter not wired |
| `OverlaySyncService.statusByRelease` | Product-visible mode/reason | Can show `PASSTHROUGH` while durable cache still holds last valid (e.g. 403 → `account_unavailable`); acceptable only if durable owner is capture plane and product status is projection |

**Risk**: implementing durable cache in TypeScript *or* leaving `NO_ACCEPTED_CACHE` in production leaves two incomplete “accepted” stories. Spec requires one durable owner: capture plane via `OverlayCandidatePort`.

---

## 4. Signature verification

### Shared production verifier (one engine)

| Symbol | Role |
| --- | --- |
| `api/src/transport_matters/harnesses/signature_verification.py` `SignatureVerifier` | ABC |
| `KeyringSignatureVerifier` | Ed25519 verify against packaged keyring |
| `RejectAllSignatureVerifier` | Fail-closed when unconfigured |
| `build_signature_verifier` | Keyring data → verifier or reject-all |
| `packaged_trusted_keyring` | Embedded trust root |
| `production_signature_verifier` | **Sole production verifier factory** |

### Overlay validation owner

| Symbol | Role |
| --- | --- |
| `api/src/transport_matters/harnesses/compatibility_store.py` `validate_overlay_artifact` | Shared signed update owner for overlay |
| `validate_channel_update` | Sibling owner for compatibility channel updates (same verifier helpers) |
| `_require_trusted_signature` | Common signature gate |
| `_require_newer_revision` / `_require_unexpired` / `_require_minimum_transport_matters_version` / `_require_matching_digest` | Shared rules |

### Overlay signature payload / digest

| Symbol | Role |
| --- | --- |
| `api/src/transport_matters/overlay_artifact.py` `overlay_signature_payload` | Canonical JSON excluding only `signature.value` |
| `overlay_content_payload` / `compute_overlay_content_digest` | Content digest excludes revision, digest, signature |
| `canonical_json` / `canonical_digest` in `canonicalization.py` | Sole canonicalization |

### Validation order inside `validate_overlay_artifact`

1. Strict Pydantic schema (`extra=forbid`)
2. Schema version constants
3. Tenant subject match
4. Exact harness + harness_version match
5. Trusted signature (`production_signature_verifier` default)
6. Monotonic revision vs `current_revision`
7. Expiry vs trusted `now`
8. Minimum Transport Matters version
9. Content digest match

### Precedence: who must call verification

Spec: capture-plane install validates through shared rules + configured `SignatureVerifier`. Product context (`@tm/overlay`) must **not** re-verify. Disk registry (`createDiskOverlayRegistryRouter`) serves raw bytes with **no** signature check (transport only).

### Relevant tests

- `api/src/transport_matters/harnesses/test_signature_verification.py` (production keyring, shared with compatibility, tamper/unknown key/algorithm, resigning)
- `api/src/transport_matters/harnesses/test_overlay_artifact.py` (digest, signature, expiry, tenant, tuple, revision, managed ops)
- `api/src/transport_matters/harnesses/test_compatibility_store.py`

### Second-writer / second-engine risk

Any new TypeScript or Python verifier for overlay install would violate “no second verification engine.” Compatibility and overlay already share `SignatureVerifier` and `production_signature_verifier`.

---

## 5. `OverlayCandidatePort`

### Contract

```ts
// packages/overlay/src/ports.ts
export interface OverlayCandidatePort {
  currentStatus(release: OverlayReleaseKey): Promise<OverlayStatus>;
  installCandidate(candidate: OverlayCandidateInput): Promise<OverlayStatus>;
}
export interface OverlayCandidateInput {
  bytes: Uint8Array;
  etag: string | null;
  refreshedAt: string;
  release: OverlayReleaseKey;
}
```

Comment on port: Slice 3 fail-safe adapter; **Slice 4 binds validating cache RPC**; product context never validates or persists artifacts.

### Live implementations

| Implementation | Location | Behavior |
| --- | --- | --- |
| `NO_ACCEPTED_CACHE` | `gatewayDeps.ts` | Empty status; install ignores bytes |
| Test fakes | `OverlaySyncService.test.ts` | Record installs / return held accepted |

**No** production adapter that talks to capture RPC.

### Readers

| Reader | Use |
| --- | --- |
| `OverlaySyncService.currentStatus` | Pre-fetch held status (catch → empty) |
| `OverlaySyncService.resolveResult` (candidate branch) | `installCandidate` then `refreshedStatus(installed, …)` |

### Writers of input

`OverlaySyncService.resolveResult` only, after `registry.fetchCurrent` returns `{ kind: "candidate", bytes, etag }`.

### Relevant tests

- `packages/overlay/src/service/OverlaySyncService.test.ts` (delivers 200 bytes; 304 never installs; 403 maps even with held)

---

## 6. Refresh result resolution

### Scheduler / registry fetch

| Symbol | Role |
| --- | --- |
| `OverlaySyncService.schedule` | Dedup via `inFlight` Map keyed by `overlayReleaseKey` |
| `fetchWithRetry` | Up to 3 attempts; only retries `unavailable`; default exponential backoff + jitter |
| `HttpOverlayRegistry.fetchCurrent` | `GET v1/overlay-artifacts/current?harness&harness_version`; Accept media type; optional Bearer + If-None-Match |
| `DISABLED_REGISTRY` | Empty base URL → `{ kind: "disabled" }` |
| Disk server | `createDiskOverlayRegistryRouter` serves packaged `docs/overlays` (or module `overlays`) |

### Gateway composition

`createOverlayGatewayDeps` → `registryPort(config)`:

1. Missing/empty `registryBaseUrl` → `DISABLED_REGISTRY`
2. Else `HttpOverlayRegistry({ baseUrl })`

`runGatewayProcess` passes `runtime.env[OVERLAY_REGISTRY_URL_ENV]` (`TRANSPORT_MATTERS_OVERLAY_REGISTRY_URL`). Python sole URL resolver: `config.resolve_overlay_registry_url` (env over TOML).

### `resolveResult` mapping (live)

| `OverlayRegistryResult.kind` | Outcome |
| --- | --- |
| `candidate` | `installCandidate`; on throw → `PASSTHROUGH` + **`artifact_invalid`** (held artifact fields preserved in projection helpers only if already on `held`) |
| `not_modified` | `refreshedStatus(held)` — no install |
| `disabled` | `PASSTHROUGH` + `disabled` |
| `forbidden` | `PASSTHROUGH` + `account_unavailable` (**always**, even if held accepted) |
| `unauthorized` | If `hasAcceptedArtifact(held)` → refresh timestamp only; else `account_unavailable` |
| `missing` | Held accepted → retain; else `artifact_missing` |
| `not_acceptable` | Held accepted → retain; else `artifact_invalid` |
| `unavailable` (incl. catch) | Held accepted → retain; else `registry_unavailable` |

### Product HTTP

| Route | Handler | Behavior |
| --- | --- | --- |
| `GET /v1/overlays/status` | `createOverlayRouter` | `sync.statuses()` |
| `POST /v1/overlays/refresh` | same | `schedule` fire-and-forget; **202** |

### Failure mapping gap (fact)

Install exceptions collapse to `artifact_invalid`. Finer reasons (`signature_untrusted`, `revision_rollback`, `artifact_expired`, …) require `installCandidate` to **return** an `OverlayStatus` with the correct reason rather than throw, unless resolution is extended. Spec PASSTHROUGH vocabulary lives in contract; capture install is the natural reason author for validation failures.

### Relevant tests

- `OverlaySyncService.test.ts` (dedupe, retry, candidate delivery, 304, 403)
- `httpOverlayRegistry.test.ts`, `diskOverlayRegistry.test.ts`
- `overlayRouter.test.ts`
- `packages/gateway/src/app.test.ts` (overlay mount + disk registry bytes)
- `packages/gateway/src/main.test.ts` (registry URL into overlay context)

---

## 7. Contract DTOs

### TypeScript owner (product/browser wire)

| Path | Symbols |
| --- | --- |
| `packages/contract/src/overlay/wire.ts` | Modes, dispositions, PASSTHROUGH reasons, override kinds, artifact document, status DTOs, branded ids |
| `packages/contract/src/overlay/index.ts` | Production barrel (no fixtures) |
| `packages/contract/src/overlay/fixtures.ts` + `testing.ts` | Shared fixture / test helpers |
| `packages/contract/fixtures/overlay-artifact-v1.json` | Cross-language fixture |

Key exports: `OVERLAY_MODES`, `OVERLAY_ARTIFACT_DISPOSITIONS`, `OVERLAY_PASSTHROUGH_REASONS`, `OverlayArtifactDocument`, `OverlayReleaseKey`, `OverlayStatus`, `OverlayStatusResponse`, `asOverlayArtifactId`, `asOverlayTenantSubject`.

### Python mirror

| Path | Symbols |
| --- | --- |
| `api/src/transport_matters/overlay_artifact.py` | `OVERLAY_*` constants, `OverlayArtifactDocument`, managed operation validators, digests |
| Shared fixture conformance | Python `test_overlay_artifact.py::test_shared_fixture_matches_python_vocabularies` vs TS `overlay.test.ts` |

### Who constructs product status vs artifact document

| DTO | Live constructors |
| --- | --- |
| `OverlayStatus` / `OverlayStatusResponse` | `OverlaySyncService` + `projections/status.ts`; future: capture install returns status |
| `OverlayArtifactDocument` | Python validation/parse only today; TS types for wire, not a second runtime validator |
| Registry bytes | Disk/HTTP transport; document validation deferred to capture install (Slice 4) |

### Relevant tests

- `packages/contract/src/overlay/overlay.test.ts`
- `api/src/transport_matters/harnesses/test_overlay_artifact.py`
- Fixture media: `docs/overlays/production-overlay-artifact-v1.json`, `packages/contract/fixtures/overlay-artifact-v1.json`

### Second-writer risk

Duplicate mode/reason literals outside `@tm/contract/overlay` and Python `overlay_artifact` constants. Spec requires single-sourced `PASSTHROUGH` with conformance tests (already present for closed vocabularies).

---

## Atomic write primitives (reuse for accepted cache)

| Symbol | Behavior |
| --- | --- |
| `api/src/transport_matters/atomic_io.py` `write_atomic_bytes` | temp + fsync + `replace`; default mode `0o600` |
| `write_atomic_json` | JSON indent via `write_atomic_bytes` |
| `write_atomic_bytes_once` | create-only via `os.link` |
| `remove_atomic_write_residue` | cleans abandoned temps |

Spec write recipe: temporary file, file sync, atomic replace, directory sync, restrictive mode. Live `write_atomic_bytes` covers temp/fsync/replace/mode; directory fsync is not explicit in the helper (callers must not invent a second atomic stack).

---

## Duplication and second-writer summary

| Seam | Live duplication? | Slice 4 risk |
| --- | --- | --- |
| Signature verification | No second engine; overlay + compatibility share verifier | Do not add TS or alternate Python verifier |
| Accepted cache durability | **Missing** (only `NO_ACCEPTED_CACHE`) | Capture RPC install must be sole durable writer |
| Product status map | In-memory only | Must project capture metadata, not re-validate |
| Capture RPC overlay ports | **Missing** | Extend existing capture router/client; do not mount as public product routes |
| Channel home / cache path | Home exists; `overlay-cache/v1` does not | Path derivation only in Python from `ChannelSpec.home` |
| Contract DTOs | TS + Python mirrors + shared fixture | Keep single vocabulary owners |
| Refresh ETag | `content_sha256` as ETag on disk registry; install must not treat ETag as auth | Spec: ETag efficiency only |

---

## Highest-risk seam

**`OverlayCandidatePort` → capture-plane validate/install under `ChannelSpec.home`**

Why:

1. Production still binds `NO_ACCEPTED_CACHE`, which **discards candidate bytes** while refresh and status routes look live.
2. Spec assigns durable accepted state exclusively to the capture plane; any TS disk cache or dual write under channel home creates a second writer.
3. `resolveResult` collapses install throws to `artifact_invalid`, so validation reason fidelity depends on install returning sanitized `OverlayStatus` through the same port.
4. Capture RPC and `CapturePort` currently have zero overlay operations; Slice 4 must extend that one seam without a parallel product route or second verifier.

