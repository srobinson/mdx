# PR #297 adversarial review

## Verdict

Issue: 0 Blocker, 5 Major, 1 Minor.

Craftsmanship verdict: The seam inversion and focused tests are coherent, but retry identity, operational outcome classification, lifecycle ownership, evidence provenance, and explicit repository hygiene are not merge ready.

## Review boundary

- PR: `#297`, open, non-draft, human-authored, with no existing reviews or comments.
- Base: `main` at `c8fe0094cb02d89a45d9c84acfe22ed6407756fc`.
- Head: `feat/s2d1-drift-emitter-wiring` at `bd546b07477e03225afee03216ed156799e1fa0d`.
- The working tree was clean and on the pinned head at initial and final preflight.
- `gh pr diff 297` returned HTTP 503 on repeated attempts. Review used the equivalent verified local commit range `c8fe0094cb02d89a45d9c84acfe22ed6407756fc...bd546b07477e03225afee03216ed156799e1fa0d`.
- No gates were run, per the read-only shared-tree brief.

## Major findings

### 1. Deterministic evidence IDs collide with regenerated immutable content

Confidence: 95/100.

`api/src/transport_matters/harnesses/drift_emitter.py:75-93` derives the evidence ID from kind, detail, run, and digest. `evidence_fields()` then adds a fresh `observed_at` and an exchange-specific `exchange_id` at lines 133-148. On primary-key conflict, `api/src/transport_matters/harnesses/blocks_store.py:172-188` accepts only full model equality.

The second reconstruction of the same logical drift after process restart or `_seen` eviction therefore reuses the same ID with different content. The store raises instead of performing the documented idempotent no-op. Different exchanges carrying the same unknown shape have the same collision once the process-local suppression no longer hides it.

There is also an unrecoverable partial-write path. `emit_drift_evidence()` writes the store row before the audit action at `blocks_store.py:222-238`. If the audit write fails, the emitter has already marked the ID as seen. A later process replay regenerates the timestamp, fails the store equality check, and can never repair the missing audit mirror. The live path survives because the exception is swallowed, but durable evidence and audit consistency are lost.

Acceptance condition: make every field under a deterministic ID replay-stable, or include every varying field in identity. Add a test that reconstructs evidence after restart with a fresh timestamp and a test that retries after a store-success, audit-failure split.

### 2. Normal Transport Matters delivery failures are recorded as harness contract drift

Confidence: 95/100.

`api/src/transport_matters/harnesses/drift_emitter.py:50-61` recognizes only five operational reasons. `ActuationDriftObserver` at lines 221-250 converts every other failed receipt for a known harness into `launch_contract_drift`.

The live delivery contract defines normal Transport Matters outcomes in `packages/runtime/src/service/RunInputDelivery.ts:12-24`: `invalid_input`, `adapter_busy`, `pty_closed`, `pty_acceptance_timeout`, `run_not_ready`, `run_not_running`, and `run_settling`, in addition to `run_not_found`. The implementation returns these during ordinary readiness, shutdown, settling, validation, and queue conditions at lines 97-131. `api/src/transport_matters/api/v1/controlplane_gateway_input.py:51-62` also returns `delivery_binding_unavailable` and `delivery_binding_failed` from Transport Matters infrastructure.

A prompt sent before TUI readiness, while a run settles, after PTY closure, during adapter contention, or during a binding failure therefore creates durable harness drift evidence. These are expected operational failures and say nothing about the certified harness contract. This poisons the compatibility evidence plane and can influence later block creation once attribution becomes available.

Acceptance condition: consume one shared typed outcome taxonomy and classify explicit harness-shaped rejections positively. Add one negative test for every operational outcome produced by the runtime and gateway, especially `run_not_ready`, `run_settling`, `adapter_busy`, and both binding failures.

### 3. Drift tasks and sink registration have no shutdown owner or drain

Confidence: 95/100.

`api/src/transport_matters/drift_capture.py:103-132` retains wire detector tasks. `api/src/transport_matters/harnesses/drift_emitter.py:103-180` retains loop tasks and discards thread-handoff futures. `start_drift_capture()` returns a `DriftCaptureRuntime` containing the emitter, observer, tailer hook, and unregister callback at `drift_capture.py:239-273`.

`api/src/transport_matters/addon_runtime.py:429-530` keeps that runtime only in the local `drift` variable. Neither `SessionCaptureRuntime` nor `CaptureRuntime` owns it. `close_capture_runtime()` at lines 632-666 drains the tailer and existing observers, closes the writer and shared pool, and only then clears exchange sinks. It cannot unregister drift first or await its detector, emitter, or thread-submitted work. The API lifespan has the same gap at `api/src/transport_matters/main.py:410-438`: it closes the session pool without draining `drift_emitter`.

A final persisted exchange or the tailer's shutdown drain can schedule drift work while teardown closes the pool it needs. Depending on timing, the evidence write fails, is cancelled, or remains orphaned. The resulting loss occurs specifically at the last observations of a run, where shutdown coverage matters most.

Acceptance condition: make drift runtime an owned field, unregister producers first, await detector tasks, await emitter tasks and thread futures, then close the pool. Apply the same ownership and drain order to the API lifespan. Add a shutdown test with pending wire and tailer emissions.

### 4. Wire evidence digests do not identify the durable raw evidence

Confidence: 95/100.

The evidence contract in `api/src/transport_matters/harnesses/blocks.py:115-136` says the raw capture stays in the run directory and only its digest rides in `DriftEvidence`. The slice scout is more explicit at `~/.mdx/projects/transport-matters-scout-s2d1.md:249-252`: `evidence_digest` is the SHA-256 of the raw evidence excerpt that stays in the run directory, and `capture_safe` states whether that raw evidence was durably captured tier 1.

For wire drift, `api/src/transport_matters/drift_capture.py:148-185` hashes a newly synthesized JSON object containing only unknown field names or event names, then sets `capture_safe=True`. That JSON object is never persisted in the run directory. The full request and response artifacts are durable, but their bytes do not match the recorded digest.

Consequently, a later reader cannot retrieve durable bytes and verify the evidence digest. It must rerun current detector logic to recreate a summary, which defeats raw evidence survival across parser revisions. `exchange_id` locates the source exchange but cannot establish which stored bytes the digest authenticates.

Acceptance condition: hash the exact persisted raw request or response excerpt, or persist the exact canonical excerpt and hash those stored bytes. Set `capture_safe=True` only when the artifact matching `evidence_digest` is durable. Add a test that resolves a recorded digest to exact tier 1 bytes.

### 5. The production wiring duplicates emitter assembly and extends an already oversized lifespan

Confidence: 95/100.

`api/src/transport_matters/main.py:254-439` contains a roughly 186 line `lifespan()` function after this change. It was already roughly 170 lines on the base, so the repository rule required decomposition before adding more orchestration. The new block at lines 311-316 also independently assembles the same `DriftEmitter`, `ExecutorBlockStore`, `ControlPlaneAuditWriter`, and `local_executor_id()` combination assembled in `api/src/transport_matters/drift_capture.py:249-273`.

This is a direct violation of the hard function-size threshold and the zero-tolerance DRY rule in `AGENTS.md`. It also contributed to the lifecycle defect above because the two construction paths have no shared ownership contract.

Acceptance condition: extract one shared emitter factory or runtime owner and decompose lifespan startup into a focused helper. Both production call sites should consume the same constructor and shutdown contract.

## Minor finding

### 6. The new tailer test imports private helpers from a sibling test suite

Confidence: 95/100.

`api/src/transport_matters/index/test_tailer_drift.py:17` imports `_binding`, `_cursor`, and `_user_line` from `index/test_tailer.py`. `api/CLAUDE.md:51-57` permits private imports in tests only from the module under test or a shared test-support module. A sibling test suite is neither, so these tests are coupled to private implementation details of another test file.

Acceptance condition: move the shared builders into an explicit test-support module with public names, then import them from both suites.

## Filtered observation

The synchronous `local_executor_id()` filesystem access inside the async lifespan was scored 70/100 and excluded by the review threshold. It is a real convention concern, but startup-only impact did not meet the bar for a retained finding.
