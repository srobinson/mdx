# Overlay Registry Slice 4 — scout report

- Branch: `feat/overlay-registry-capture-cache` at base `cdfac164aaf5f36a463e9fbc1c8359375109cfea`
- Inputs: `.warroomagents/fable5.md`, `docs/ARCHITECTURE.md`, spec § "Slice 4: Capture validation and accepted cache", live source, cm ratification record (019fe082), orchestrator source-fact pass (cross-checked after this map was drawn independently)
- Every owner below was validated against source at the base SHA. Citations are `file:symbol`.

## Slice 4 scope (settled)

Extend the capture RPC with validate, install, and metadata ports; validate through the shared compatibility rules and the production verifier; persist one accepted cache under `ChannelSpec.home` with atomic writes; retain the last valid entry after any invalid candidate; expose only sanitized metadata to the product context. Dependency satisfied: Slice 2 production trust landed (`feat(overlay): install production signature trust (#375)`), Slice 3 landed (`#376`).

## Reuse Map

A new implementation for any capability below is a defect.

| Capability | Owning symbol | Binding |
| --- | --- | --- |
| Overlay artifact validation (strict schema, tenant, exact tuple, signature, monotonic revision, expiry, min TM version, content digest — in that order) | `api/src/transport_matters/harnesses/compatibility_store.py:validate_overlay_artifact` | Already exists from Slice 1. Test-only callers today; Slice 4's install port is its first production caller. Do not wrap it in a second validator. |
| Production verifier | `api/src/transport_matters/harnesses/signature_verification.py:production_signature_verifier` | lru_cache singleton over `build_signature_verifier(packaged_trusted_keyring())`; falls back to `RejectAllSignatureVerifier` when no keyring is packaged. `validate_overlay_artifact` already defaults to it when `verifier=None`. Same engine as compatibility; no second engine in either language. |
| Canonical signature payload and content digest | `api/src/transport_matters/overlay_artifact.py:overlay_signature_payload`, `overlay_artifact.py:compute_overlay_content_digest`, over `api/src/transport_matters/canonicalization.py:canonical_json` | Reuse as is. |
| Artifact document model and closed vocabularies | `api/src/transport_matters/overlay_artifact.py:OverlayArtifactDocument`, `OVERLAY_PASSTHROUGH_REASONS`; TS mirror `packages/contract/src/overlay/wire.ts` with fixture conformance tests | Single sourced. The cache metadata record must speak these vocabularies, never new literals. |
| Channel isolated cache root | `api/src/transport_matters/channel.py:ChannelSpec.home`, resolved through `api/src/transport_matters/storage_roots.py:default_storage_root` | `default_storage_root` is the existing boundary honoring `TRANSPORT_MATTERS_HOME`; deriving from `ChannelSpec.home` directly would bypass the override the channel isolation tests rely on. Cache root = resolved home + `overlay-cache/v1`. Resolved once in Python; TypeScript never sees a path. |
| Atomic writes with restrictive mode and residue recovery | `api/src/transport_matters/atomic_io.py:write_atomic_bytes` (temp + fsync + replace, default mode 0o600), `write_atomic_json`, `remove_atomic_write_residue` | One atomic stack. Gap: no directory fsync (spec requires it). Extend `atomic_io` in place; do not build a second writer. |
| Capture RPC seam (Python) | `api/src/transport_matters/api/v1/capture_rpc_routes.py:router` (`APIRouter(prefix="/capture")`), `api/src/transport_matters/capture_rpc.py:CaptureLeaseRegistry` | New validate/install/metadata operations extend this router. They are loopback implementation ports, never mounted as `/v1/overlays/*` product routes. |
| Capture RPC seam (TypeScript) | `packages/runtime/src/adapters/CaptureRpcClient.ts:CaptureRpcClient` (routes under `/v1/capture/...`) | Extend the existing client; keep the `CapturePort` shape discipline. |
| Product-plane binding point | `packages/overlay/src/ports.ts:OverlayCandidatePort` (`currentStatus`, `installCandidate`) | The port comment names Slice 4 as the binder. Today `packages/overlay/src/gatewayDeps.ts:NO_ACCEPTED_CACHE` silently discards candidate bytes, and `packages/gateway/src/main.ts:runGatewayProcess` injects no `candidates`. Slice 4 replaces that default with a capture RPC backed adapter. |
| Reason fidelity at the port | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService.resolveResult` | Install exceptions collapse to `artifact_invalid`. The install port must return an `OverlayStatus` carrying the true reason (`signature_untrusted`, `revision_rollback`, `artifact_expired`, ...) rather than throw. |
| Sanitized metadata contract | `packages/contract/src/overlay/wire.ts:OverlayArtifactMetadata`, `OverlayArtifactReference`, `OverlayStatus` | The RPC metadata response projects into these DTOs. No operation values, no tokens. |
| Installed TM version for the min-version rule | `api/src/transport_matters/__init__.py:__version__` | Pass as `installed_transport_matters_version`. |
| Test signing helpers | `api/src/transport_matters/harnesses/test_overlay_artifact.py:_sign_raw`, `_seal_raw` | A second test file needs them; promote to a shared test-support module rather than copy. |

### New surfaces with no current owner (justified)

- **Accepted cache store (Python, capture plane).** No `overlay-cache` path, metadata record, or restart revalidation owner exists anywhere (searched: `grep -rn "overlay-cache\|overlay_cache"` across `api/` and `packages/` — none found). Candidate home: a new source-root module beside `overlay_artifact.py` (fits the import DAG: channel → atomic_io → overlay_artifact → compatibility_store).
- **Expected tenant subject owner.** `validate_overlay_artifact` requires `expected_tenant_subject`; the only live value is the test literal `"local-development"` in `harnesses/test_signature_verification.py`, which is also the signed `tenant_subject` of the packaged `docs/overlays/production-overlay-artifact-v1.json`. Slice 4 needs one production constant owner in Python. Cache keys use a digest of this signed subject per spec.
- **Directory fsync** added to `atomic_io`, not beside it.

## Current writer / reader / precedence map

| State | Writer(s) today | Readers | Precedence |
| --- | --- | --- | --- |
| Accepted cache bytes + metadata | **None — does not exist.** After Slice 4 the capture install port is the sole writer. | After Slice 4: metadata port, restart revalidation | Higher valid revision replaces lower for the exact tuple; an invalid candidate never replaces a valid entry |
| Packaged artifact bytes | Offline commit beneath `docs/overlays/` | `packages/overlay/src/adapters/diskOverlayRegistry.ts:createDiskOverlayRegistryRouter` (byte for byte, ETag = quoted `content_sha256`, no signature check — transport only) | Immutable after publication |
| Product status by release | `packages/overlay/src/service/OverlaySyncService.ts:OverlaySyncService` in-memory `statusByRelease` (via `schedule`/`refresh`) | `packages/overlay/src/server/overlayRouter.ts` status route | Projection only; after Slice 4 it must project capture-plane truth, never own it |
| Trust keyring | Packaged `trusted_signing_keys_v1.json` | `signature_verification.py:packaged_trusted_keyring` → verifier singleton | Package embedded; absent keyring selects reject-all, `APPLY` unreachable |
| OverrideStore scopes (context, untouched) | `api/src/transport_matters/api/v1/overrides.py:patch_overrides`, `api/v1/breakpoint_routes.py`, and the fifth writer `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides` (child replica clear-then-upsert replay, parent authoritative) | `api/src/transport_matters/request_pipeline.py:run_pipeline`, shared proxy | Live edit precedence; layering arrives in Slice 6 |
| Compatibility run facts (context, untouched) | `api/src/transport_matters/harnesses/compatibility_facts.py:write_compatibility_facts` | Capture, replay, audit | Write once; Slice 6 evolves it |

Second-writer watchpoints for review: (1) any durable overlay state written from TypeScript, or `NO_ACCEPTED_CACHE` left bound in production, creates two incomplete accepted-state stories; (2) any second path that validates or writes accepted bytes outside the one capture-plane install owner.

## Quality Map

- Python unit tests are colocated (`api/CLAUDE.md`); integration under `api/tests/integration/`. Private imports allowed in tests only, enforced by `test_private_import_boundary.py`.
- Existing coverage to build on: `harnesses/test_overlay_artifact.py` (validation matrix, fixture conformance), `harnesses/test_signature_verification.py` (production keyring, tamper/unknown key, shared compatibility+overlay keyring), `test_capture_rpc.py` + `api/v1/test_capture_rpc_routes.py` (+ request-validation and worktree-resolution siblings), `test_channel.py` (home isolation), TS: `OverlaySyncService.test.ts` (dedupe, retry, candidate delivery, 304, 403), `diskOverlayRegistry.test.ts`, `httpOverlayRegistry.test.ts`, `overlayRouter.test.ts`, `packages/gateway/src/app.test.ts`, `main.test.ts`, `CaptureRpcClient.test.ts`.
- Gates: `just check` and `just test` verbatim (`just test-affected` inner loop); `@tm/overlay` is already in the `just check` typecheck fanout. CI is the verdict.

## Decision 4 — exact grace ladder (ratified)

Stuart ratified the recommendation as written on 2026-08-08 ("build it", cm 019fe082): 14-day signed grace deadline, pre-wired, clock-rollback-safe.

1. On entitlement failure (`403`), the exact cached, signature-valid artifact remains usable until the **earliest** of:
   a. the signed grace deadline carried with the tenant resolved artifact (14 days);
   b. the artifact's `expires_at`;
   c. a harness version change (the exact tuple no longer matches).
2. During grace the human surface shows the lapse and the deadline.
3. At that earliest instant the state is `PASSTHROUGH`.
4. A local clock derived grace value or an unsigned `403` never extends authority; only signed timestamps are evaluated, so a clock rollback cannot extend the deadline.

Slice 4 obligations under the ladder: never delete or overwrite the cache on `403`; record the last acquisition reason in metadata so later slices can freeze `account_unavailable`; grant ETag and status codes no authority. The signed grace deadline field does **not** exist in the schema at this base (verified: `grep -rn "grace"` over `packages/contract` and overlay Python hits only unrelated shutdown code). Adding it is contract-owner schema work, not a Slice 4 invention; per the spec's slice plan, Slice 4 entitlement tests pin immediate `PASSTHROUGH` on `403` with cache retained and not applied.

## Minimal tests-first plan

Write each test failing before its implementation. Order:

1. **Cache store (Python, new colocated test module beside the new store):** channel isolation across stable/preview/dev via `TRANSPORT_MATTERS_HOME` (pattern from `test_channel.py`); atomic write recovery from residue plus 0o600 file mode and directory fsync; invalid candidate (bad signature, rollback revision, tampered digest, expired) cannot replace the held valid entry; restart revalidation through `production_signature_verifier` (absent keyring selects reject-all and the held entry cannot activate); serialized metadata contains no account token and no operation values; ETag equality or mismatch changes nothing about acceptance. Reuse the promoted `_sign_raw`/`_seal_raw` helpers.
2. **Capture RPC ports (pattern from `api/v1/test_capture_rpc_routes.py`):** validate/install returns sanitized identity, ETag, and outcome reason; metadata read returns `OverlayArtifactMetadata`-shaped data only; no route is reachable as a product API.
3. **TS adapter (`packages/overlay/src/adapters`):** the capture RPC backed `OverlayCandidatePort` returns an `OverlayStatus` with the true validation reason instead of throwing, and `currentStatus` projects capture metadata; `OverlaySyncService.test.ts` already pins the delivery contract.

Gates after each step: `just check`, `just test`, then CI.

## No-touch boundary: OverrideStore

Slice 4 must not modify or call any of: `api/src/transport_matters/overrides/state.py:OverrideStore` (and `get_store`), `api/src/transport_matters/api/v1/overrides.py:patch_overrides` / `_snapshot_scope` / `_sync_shared_overrides`, `api/src/transport_matters/overrides/__init__.py:apply_overrides`, `api/src/transport_matters/request_pipeline.py:run_pipeline`, `api/src/transport_matters/shared_proxy/manager.py:SharedProxyManager.set_overrides`, or the fifth writer `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides`. Slice 4 ends at sanitized metadata exposure; managed layer install and per-run freeze are Slices 6 and 7. Any import of `transport_matters.overrides` from the new cache or RPC code is a review defect marker (the existing `overlay_artifact.py` import of the `Override` union is the one sanctioned contract dependency).

## Cross-check against the orchestrator source-fact pass

The independent map agrees with `~/.mdx/projects/transport-matters-overlay-s4-source-facts.md` on every shared claim (capture RPC surface, channel homes, missing cache owner, verifier singleness, port contract, reason-fidelity gap, directory-fsync gap). This report adds two facts that pass omits: the ratified Decision 4 grace ladder and the missing production owner for `expected_tenant_subject`, plus the `default_storage_root` override subtlety for channel isolation tests.

## None found (searches run)

- No accepted cache, `overlay-cache` path, or metadata record: `grep -rn "overlay-cache\|overlay_cache"` over `api/`, `packages/`.
- No grace field in any schema: `grep -rn "grace"` over `api/src`, `packages/overlay`, `packages/contract` (only process shutdown grace hits).
- No production `expected_tenant_subject` owner: `grep -rn "local-development"` (test literal and packaged fixture only).
- No non-test caller of `validate_overlay_artifact`: `grep -rln "validate_overlay_artifact"` (definition plus three test files).
