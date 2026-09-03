# Catalog backlog audit

Snapshot: `535118346ca5d0584a7a4a3da28a55be532dc3bd`  
Assigned issues: #630, #631, #632, #633, #470, #477, #448, #446  
Audit posture: read only. Historical provider observations are reported as issue evidence; current code findings are independently cited.

## Recommended order

1. **Live catalog refresh and fail open target resolution**: #631, then #632 with the #470 entitlement boundary. This restores discovery and launch continuity for new models and patch releases.
2. **First launch verification**: #633. It must produce an explicit verification phase and eventual verdict without turning missing evidence into a structural degradation.
3. **Per run launch status**: #477. Keep the UI and status data work after the resolver and verdict contracts settle.
4. **Compatibility update delivery**: #448. Strategic, high risk supply chain work. It is independent of the immediate discovery repair.
5. **Baseline CLI boundary**: #446. Small documentation and command surface cleanup.

Parent tracking in #630 is not additional implementation work.

## Issue findings

### #630, harness discovery epic

**Disposition:** `umbrella`  
**Canonical work:** `harness-discovery-verdicts`  
**Priority:** P1  
**Effort:** S for tracking only  
**Confidence:** High

The parent identifies three separate defects and already has the correct child split: probe/catalog recovery (#631), resolver semantics (#632), and first launch verdicts (#633). Current code confirms all three seams remain open. Codex uses only `debug models --bundled` and filters visibility to `list` (`harnesses/probes/codex.py:113-149`). Resolver selection requires matching target and installed versions (`harnesses/resolver.py:342-376`). Verification skips capture for an in-range version (`launch_verification.py:215-229`) and writes a verdict only when an exact release reference exists (`support_verdict_store.py:60-79`).

Rewrite the parent outcome so discovery never acts as compatibility permission. Preserve separate hard conditions such as missing executable, disabled harness, retired target, and the sanctioned entitlement exclusion. The issue's historical `gpt-6-astra` and Claude timeout observations were not reproduced because the brief forbids live provider probes.

### #631, Codex enumeration

**Disposition:** `keep`  
**Canonical work:** `live-catalog-refresh`  
**Priority:** P1  
**Effort:** M  
**Confidence:** High

This is a distinct, actionable producer defect. The shipped live-catalog work (#309, commit `33618e43`) and stored startup refresh (#304, `04300cf2`) are present, but the current Codex adapter still points at the bundled catalog. `run_model_enumeration_probe` has one shared five second timeout, returns `None` for nonzero, parser, and subprocess failures, and has no structured fallback result (`runner.py:48,201-234`). State refresh caches a complete snapshot for an unchanged version and does not rerun Codex enumeration (`state_refresh.py:329-365`).

Keep the proposed primary refreshed command, bundled fallback, all visibility values, a separate enumeration timeout, sanitized typed failures, and partial merge semantics. Do not persist upstream picker visibility. The store already has atomic complete versus partial snapshot semantics (`connections_store.py:427-483`), so storage changes should be limited to the result and refresh contract. Acceptance should include refresh on unchanged CLI versions and preservation of omitted models after a partial result.

### #632, retained targets and launchability

**Disposition:** `keep` with rewrite  
**Canonical work:** `fail-open-target-resolution`  
**Priority:** P1  
**Effort:** L  
**Confidence:** High

The version and release filters are current code: `_offered_targets` requires the installed version and active release attribution (`resolver.py:342-376`), and explicit probe failure still rejects (`resolver.py:448-465`). `ResolvedTarget.harness_version` currently carries target observation provenance (`resolver.py:164-185,541-564`), so the proposed separation of installed version from observation provenance is necessary.

The latest comment on #632 supersedes its body on entitlement. The vendor catalog is not sufficient evidence: #470's comment records Codex 0.153.2 listing `gpt-5.2` while the provider returns a 400 refusal. Retain `account_entitlement_unavailable` in launch resolution, move its evidence source to #470's session store, and remove only the baseline-attempt read from resolver snapshots. Do not merge this into a blanket advisory rule.

After #470's storage contract is defined, offer retained executor and harness scoped target rows across installed version changes, preserve target provenance, and create a `VerificationCell` for absent or failed enumeration. Retired targets, authored blocks, disabled harnesses, and known entitlement refusals remain explicit exclusions. The proposed tests in #632 are the right integration proof. #631 is useful sequencing, but the true dependency is the entitlement boundary in #470.

### #633, first launch verification

**Disposition:** `keep` with rewrite  
**Canonical work:** `first-launch-verification`  
**Priority:** P2  
**Effort:** L  
**Confidence:** High

The missing verdict is structural, not merely display. `support_verdict_store._matching_reference` requires exact route, model, and shape identity (`support_verdict_store.py:224-246`); reads iterate only release references (`:122-177`). In-range launches skip capture, even when the model has no release reference (`launch_verification.py:215-229`). The two-worker admission path drops work when capacity is full (`launch_verification_support.py:112-128`; `verification_executor.py:17-51`).

The provisional state proposal conflicts with #384's three owner comments and with `SupportState`: #384 says comparator failure leaves status unchanged and retries, while `support_state.py:63-73` has only `blessed` and `degraded`, with no state before comparison. Rewrite the contract to add a separate verification phase or assessment status. Pending, running, missing reference, and failed capture must remain explicit and must not manufacture `missing_properties`. A completed candidate comparison can then produce `blessed` or `degraded`, with exact reference precedence, sibling alternatives, envelope pairing, request shape separation, candidate identity, and durable queueing as acceptance requirements.

The queue must deduplicate cells, persist saturation instead of dropping it, recover pending work after restart, and recheck evidence under the existing cell lock before spending. Provider refusal should feed the #470 entitlement path when it matches the closed classifier, while the verification assessment records its own outcome.

### #470, entitlement exclusions

**Disposition:** `keep` with scope correction  
**Canonical work:** `runtime-entitlement-exclusions`  
**Priority:** P1  
**Effort:** M  
**Confidence:** High

Current enforcement reads `account_entitlement_excluded_models` from channel-home baseline attempts (`resolver_snapshots.py:123-153`; `baseline_attempts.py:397-418`). The exact Codex refusal classifier is already narrow and provider specific (`baseline_attempts.py:353-394`). #449, commit `db6131c3`, shipped this disk-backed behavior, but the issue's home-wipe failure remains.

Move recognized provider/model refusal evidence into the session store, with atomic upsert and a read path used by resolver snapshots. The account scope needs an explicit identity. Provider plus model alone is unsafe if two provider accounts share a machine; executor id alone loses the intended cross-home survival. Define the account key from the credential or route identity before implementation. Keep unknown 400s transient. Prove that a home wipe preserves the exclusion and that a different account does not inherit it.

### #477, launch status bar

**Disposition:** `keep` with rewrite  
**Canonical work:** `launch-status-surface`  
**Priority:** P2  
**Effort:** M  
**Confidence:** High

This is downstream UX and data plumbing, not a duplicate of #632. The capture path already serializes launch advisories into `launch_fields` (`capture_rpc_routes.py:515-564`), but the web `RunVitalsStrip` consumes activity status only (`www/packages/canvas/src/workbench/chrome/RunVitalsStrip.tsx:36-77`). Support verdicts are release/model/version artifacts, not per-run facts.

Remove the blanket requirement that every resolver rejection becomes advisory. It conflicts with #470's sanctioned entitlement exclusion and with existing enablement and infrastructure gates. After #632 and #633 define the backend matrix, carry range position, verification phase/state, and advisories into the per-run activity projection. Acceptance must distinguish advisory target recognition from hard launch prerequisites and show pending, blessed, degraded, no reference, and refusal truthfully.

### #448, compatibility delivery

**Disposition:** `keep`  
**Canonical work:** `compatibility-update-delivery`  
**Priority:** P2  
**Effort:** L  
**Confidence:** High

The receiving contract exists, but there is no production delivery path. `compatibility_store.py:85-171` exposes validation and an abstract verifier whose concrete `RejectAllSignatureVerifier` rejects every mutable update. The documentation still lists trust root, transport, staged rollout, and preview policy as open decisions (`docs/HARNESS-COMPATIBILITY.md:258-335`).

Keep retrieval, verified last-cache retention, real signature verification with rotation, channel rollout, blocked-version delivery, and distinct product-release nudges in scope. PR #375 (`0b536cc8`) installed trust for overlay artifacts; it does not implement compatibility manifest trust or polling, so it is not shipped evidence for this issue. Authoring and manifest minting remain an external dependency, as the issue states. High supply chain risk warrants staged rollout and fail-closed activation tests.

### #446, harvest and publish boundary

**Disposition:** `keep` with documentation-first rewrite  
**Canonical work:** `baseline-cli-boundary`  
**Priority:** P3  
**Effort:** S  
**Confidence:** High

The capture path is already shared: `baseline_publish.py` imports `harvest_baseline` (`:16-18`) and passes each planned cell to it (`:151-164`). The distinction is real. `baseline_harvest` is one-cell evidence capture and degraded acceptance (`baseline_harvest.py:85-133`); `baseline_publish` plans spend, resumes missing cells, and mints release bindings (`baseline_publish.py:93-165`; `baseline_publish_plan.py:98-176`).

Keep both dev-only commands and choose the cheaper option 2 from the issue: document harvest as debug-only evidence that never changes a release, make publish the normal workflow, and make help text state the boundary. Folding the CLI would add risk without removing the shared implementation duplication, which is already absent.

## Reconciliation

- #630 is a parent only. #631, #632, and #633 are implementation packages; no parent work should be counted twice.
- #632's latest comment reverses its entitlement-removal bullet. #470 owns runtime provider/model refusal evidence and the retained launch exclusion.
- #633's provisional `degraded` state conflicts with #384's ratified rule that missing comparison evidence is a retry trigger, not a verdict. Use a verification phase separate from `SupportState`.
- #477 overlaps #632 only where it proposes changing resolver rejection policy. Keep #477 for per-run status and UI projection after the backend matrix is settled.
- #470 must define provider-account scope. A global provider/model exclusion can leak one account's refusal into another account.
- #448 is compatibility-data delivery. #446 is local baseline authoring ergonomics. Neither subsumes the other.

## Evidence boundaries

Read in full: all eight assigned issue bodies and their two assigned comments; #384's body and all three owner comments; `AUDIT-BRIEF.md`, `AGENTS.md`, `LESSONS.md`, `manifest.json`, `assignments.json`, and the assigned issue JSON/Markdown artifacts.

Current code and tests checked include the Codex probe, probe runner, state refresh, evidence store, resolver, resolver snapshots, launch target, launch view, launch verification, support verdict, compatibility store, baseline harvest/publish paths, and the RunVitalsStrip activity path. Shipped history checked includes #293 (`747e0577`), #299 (`506e0409`), #304 (`04300cf2`), #309 (`33618e43`), #310 (`b992b376`), #312 (`9f1a60a7`), #375 (`0b536cc8`), #436 (`d4ce12a5`), #444 (`a150064a`), #449 (`db6131c3`), #476 (`defd681b`), #479 (`75e13ed8`), #604 (`f56672bf`), and #608 (`974d0481`).

No live harness, provider, token-spending, GitHub mutation, or repository mutation was performed. The repository was clean at the audited SHA.

Completion: assigned issue count 8; assigned comments read 2; source SHA `535118346ca5d0584a7a4a3da28a55be532dc3bd`.
