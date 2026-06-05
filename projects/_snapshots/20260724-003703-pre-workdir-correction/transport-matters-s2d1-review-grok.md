# Adversarial review — PR#297 S2d.1 drift-emitter seam wiring

**Target:** `main...feat/s2d1-drift-emitter-wiring` (`c8fe0094`…`bd546b07`)  
**Tree check:** `feat/s2d1-drift-emitter-wiring` @ `bd546b07`, working tree clean (porcelain empty).  
**Diff source:** local range diff (equivalent to `gh pr diff 297`; GitHub 503 on fetch).  
**Scope:** 26 files, +2088/−39. Read-only pass; gates not run.  
**Lens:** live-path invisibility (blocker-class), scout S2d.1 plan, S2f boundary, DAG, redaction/dedup, hygiene on the 26 files only.

## Summary

The four seams are structured correctly for live-path safety: shared `DriftEmitter` swallow/count/log, fire-and-forget `submit` / discarded-future `submit_from_thread`, controlplane port inversion, index injection only, post-persist wire sink, bootstrap documented-gap stub, closed operational prompt reasons, closed adapter allowlists, sha256 digest only to Postgres, no S2f block creation. Per-seam “emitter raises / hook raises ⇒ live path unchanged” coverage exists.

No blocker-class live-path hazard found. Two Majors: deterministic evidence ids are incompatible with wall-clock `observed_at` under store full-row equality (restart / multi-process / seen-cap re-emit raises and is counted as failure), and `startup_prompt_rejected` is only reachable under `FakeDeliveryProof` (production `DeliveryProofSubscription` never returns `status="failed"`).

## Issues

### Issue 1 — Severity: Major
- **File:** `api/src/transport_matters/harnesses/drift_emitter.py:145` (with `blocks_store.py:186`)
- **Description:** `evidence_fields` always sets `observed_at=datetime.now(UTC).isoformat()` while `evidence_id` is deterministic over `kind:detail:run:digest` only. Store `record_drift_evidence` does `ON CONFLICT DO NOTHING` then full `DriftEvidence` equality. A re-emit of the same observation (process restart, addon+API if ever shared, or after `_SEEN_EVIDENCE_CAP` clear) almost always has a different `observed_at`, so the conflict path raises `ValueError` instead of the claimed idempotent no-op. Swallowed by `_emit` (live path still safe) but produces failure logs, increments the failure counter, and can skip the audit mirror on the retry path. Process-local `_seen` masks this only within one process lifetime before cap clear.
- **Suggestion:** Treat identity content for conflict checks as the durable payload (exclude `observed_at`), or pin `observed_at` out of the equality contract (compare digest/kind/detail/run/harness/capture_safe only), or stop minting a new wall clock when building fields for a deterministic id. Add a store-level test: same id, different `observed_at` ⇒ clean no-op, no raise.
- **Status:** open

### Issue 2 — Severity: Major
- **File:** `api/src/transport_matters/controlplane/launch_service.py:283` (production proof: `delivery_proof.py:81–135`)
- **Description:** `startup_prompt_rejected` is wired after `_resolve_first_prompt`, and `test_prompt_drift.test_failed_launch_first_prompt_emits_startup_prompt_rejected` is green only because `FakeDeliveryProof` can return `status="failed"`. Real `DeliveryProofSubscription.resolve` yields only `submitted` or `unknown` (`proof_unavailable` / `proof_deadline` / `duplicate_provider_requests`). A harness that never opens a wire exchange for the startup prompt becomes `unknown`/`proof_deadline`, which the observer correctly refuses as non-failed — so production never records `startup_prompt_rejected`. Post-launch `actuation_rejected` via failed gateway/input outcomes remains real.
- **Suggestion:** Either document this as a second bootstrap-style gap (no production failed first-prompt signal yet), or teach the launch/proof path a real failed receipt when the harness rejects the initial prompt, and acceptance-test against that production path rather than only the fake.
- **Status:** open

### Issue 3 — Severity: Minor
- **File:** `api/src/transport_matters/index/tailer.py` (700 LOC exact)
- **Description:** File sits on the hard 700-line ceiling after the injected hook (+`_emit_drift`). Scout required the injection pattern specifically to avoid breaching the limit; one more line forces a mandatory pre-add refactor. Behavior of the injection is correct and minimal.
- **Suggestion:** Extract `_emit_drift` + locator call into a tiny sibling helper or shrink a nearby private before the next touch.
- **Status:** open

### Issue 4 — Severity: Minor
- **File:** `api/src/transport_matters/harnesses/drift_emitter.py:191–197`
- **Description:** `_already_seen` marks the id before a successful store write, with no lock. A failed first emit permanently suppresses that observation for the process until the set is cleared at cap; concurrent thread+loop access is racy (store idempotency limits damage).
- **Suggestion:** Mark seen only after successful `_emit`, or use a lock and a “in-flight” state; document intentional loss-on-failure if kept.
- **Status:** open

### Issue 5 — Severity: Minor
- **File:** `api/src/transport_matters/codex/request_parser.py:82–90`
- **Description:** Unknown request detection is envelope `provider_extras` only. Scout noted per-item `extra_fields` as part of codex partial detectability; item-level alien keys do not emit. Fixtures keep envelope silent — good — but item drift is invisible.
- **Suggestion:** Follow-up allowlist over stamped input item extras, or explicitly note out of S2d.1 scope in the plan.
- **Status:** open

## Live-path safety checklist (blocker-class)

| Seam | Fire-and-forget | Swallow | Emitter-raises / hook-raises test | Notes |
| --- | --- | --- | --- | --- |
| Wire (`WireDriftObserver` + exchange sink) | `create_task` → `submit` | sink fan-out + `_emit` | `test_emitter_failure_is_invisible_to_the_sink_path` | Post-persist only; adapters pure detectors; closed allowlists; fixtures pinned silent |
| Transcript (`on_drift` + `make_tailer_drift_hook`) | `submit_from_thread` (future discarded) | hook try/except + tailer `_emit_drift` try/except | `test_raising_hook_leaves_quarantine_flow_byte_identical` | Storage-plane gated in hook; no index→harnesses import |
| Bootstrap (`record_session_rejection`) | `submit` | emitter | `test_emitter_failure_is_invisible_to_the_registry` | Documented gap; no production classifier; no false prepare-time emission |
| Actuation (`PromptDriftObserverPort`) | sync `observe` → `submit` after receipt | emitter | `test_emitter_failure_is_invisible_to_prompt_delivery` | Operational closed set; `unknown` never drift; not awaited before return |

## DAG / S2f / redaction / identity

- **DAG:** Production controlplane imports only `drift_observer.PromptDriftObserverPort` (no harnesses). Index has no harnesses import. `capture_rpc` / `main` / `addon_runtime` / `drift_capture` may import harnesses. Pass.
- **S2f:** Seam modules do not call `match_release`, `block_from_evidence`, `attribute_drift_evidence`, or `create_block`. Resolved context left unset in `evidence_fields`. Pass.
- **Redaction:** Only `evidence_digest` (sha256 of excerpt) constructed for store fields; raw excerpt not passed into `DriftEvidence`. Pass.
- **Executor identity:** Home-scoped uuid via atomic hard-link mint; no config; shared helper. Pass (new source, no prior machine-id to reuse).
- **Hygiene (26 files):** New modules well under 700; `service.py` 687; `tailer.py` at 700 (Minor). Shared `DriftEmitter` + generalized failure counter — DRY. No new function over ~150 LOC in the added surface.

## Craftsmanship verdict

Tight seam wiring with honest ports and real invisibility tests; ship-quality shape undercut by deterministic-id/`observed_at` idempotency friction and a hollow `startup_prompt_rejected` production path.
