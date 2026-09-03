# 448: Delivery channel: fetch signed compatibility updates, and nudge on a new TM release

URL: https://github.com/littleorgans/transport-matters/issues/448
State: open
Labels: 
Updated: 2026-08-24T03:49:49Z

The receiving half of out-of-band compatibility updates is built and tested. The delivery half does not exist. Until it does, updating a blessing means shipping a TM release and waiting for users to upgrade.

## What exists today

`harnesses/compatibility_store.py`:

- `embedded_compatibility_manifest()` loads `compatibility_releases_v1.json` as a **package resource**. It ships inside the wheel.
- `validate_channel_update()` is the entry point an update channel would call, with `_require_known_channels`, `_require_installed_revisions`, `_require_transport_matters_version`, `_require_digest_integrity`, `_require_certified_active_pointers`.
- `SignatureVerifier` is abstract, and the only concrete implementation is **`RejectAllSignatureVerifier`**.
- Manifest signatures are stubs (`"stub:embedded:stable:claude"`), consistent with nothing verifying them.

So: the safety checks are written, the door has a working lock, and there is no building attached to it.

## Why it matters

Harness releases are frequent — claude moved 2.1.237 → 2.1.241 inside a single working session. Without delivery, every harness release leaves users reading `above_ceiling` until a TM release is cut *and* installed. Blessings go stale on a multi-day cycle, which is the failure the compatibility system exists to prevent.

Per `docs/HARNESS-COMPATIBILITY.md`, the design already scopes updates narrowly: manifests, target descriptors, lifecycle state, digests, evidence references, channel pointers. No executable content.

## Scope

1. **Retrieval.** Where the manifest is served from, how often it is polled, and the offline story. The doc already requires that the last verified cache survives retrieval failure.
2. **A real `SignatureVerifier`**, replacing `RejectAllSignatureVerifier`, plus key distribution and rotation. This is a supply-chain boundary: the payload reaches machines running paid agents and holding captured prompts and source.
3. **Staged rollout via `channel_states`.** Bless on preview, watch, advance stable. Nothing currently writes `channel_states`; `reseal_compatibility_manifest.py` documents hand-editing JSON as the expected workflow.
4. **Remote kill switch.** `blocked_versions` should be usable to disable a specific bad harness version on every install without a release.
5. **New-release nudge.** Two distinct signals the user should receive, and they must not be conflated:
   - *Your harness version is now blessed* — arrives via a compatibility update, no upgrade needed.
   - *A new Transport Matters release is available* — an upgrade nudge, surfaced in the product.
   A user on an old TM build may be told a harness version is blessed while their installed adapter revisions cannot activate that release (`_require_installed_revisions`). That case must read as "upgrade TM to get this", never as a silent no-op.

## Not in scope

The authoring path (minting a release, sealing a successor, advancing channel state) is tracked separately. This issue is delivery and consumption only.

## Sub issues
[]
