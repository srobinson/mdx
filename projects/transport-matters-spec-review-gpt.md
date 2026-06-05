# Architect review: S1 rejection signal and S2 enablement

Reviewed against `main` at `506e04093e7075fa8f1e2ff5f6eb760b556a8879`.

## S1 provider condition rejection signal

### BLOCKER

- issue BLOCKER S1:Signal_transport extending run_live_status kinds omits the CHECK constraint migration and conflicts with S2 claiming the sole next revision after 0024

### HIGH

- issue HIGH S1:Detection the Codex rejected upgrade uses the response handler without RequestFlowState or a specified binding and generation handoff, so a classifier unit can pass while production 401 or 403 emits nothing

- issue HIGH S1:Stickiness submit_wire_exchange unconditionally clears the durable live kind and a finalized 401 or 429 projects only response_error, so observer lane and activity machine stickiness cannot survive reconciliation or restart

- issue HIGH S1:Launcher_consumption the existing resolver skips deliveries without prompt_cursor and only resolves the active correlated prompt, while the synthetic Codex handshake request cannot claim its delivery, so zero delivery store changes leaves the targeted wait pending

### MEDIUM

- issue MEDIUM S1:Watch_tests WatchFact retains status but format_watch_envelope discards it for needs_you, and the stated fact level test does not prove the launcher receives the reason through PTY

- issue MEDIUM S1:Dedup the cited DriftEmitter pattern has process lifetime memory and no recovery reset, so the spec must define an episode close and prove 401 success 401 and 429 success 429 rearm

- issue MEDIUM S1:Blast_radius adding ActivityStatus members forces Canvas RunVitalsStrip labels and status fixtures despite Human UI being out of scope and the completion line requiring the overview

- issue MEDIUM S1:Python_mirrors test_type_mirrors only pins ActivityStatusTier while status and needs_you are open Python containers, so the claimed status and payload guard does not exist

- issue MEDIUM S1:Contract_docs CONTROLPLANE and CONTROLPLANE_OBSERVATION_PLAN still define needs_you as an operator question or gate and are absent from the deliverables

### LOW

- issue LOW S1:Reason_boundary the separate provider condition set is correct but required tests omit disjointness and no drift emission

## S2 enablement

### BLOCKER

- issue BLOCKER S2:Semantics version compatible eligibility and default enablement contradict the locked advisory compatibility posture because an incompatible no row harness currently launches

### HIGH

- issue HIGH S2:Retirement_sweep removing access evidence leaves required ResolvedTarget.access_observation_revision without a producer and leaves LAUNCH_CONTRACT and HARNESS_COMPATIBILITY auth authority semantics active

- issue HIGH S2:Launch_gate the hard toggle read has no fail closed store failure rule and its new domain error has no capture RPC, CLI, or MCP translation and boundary tests, allowing an explicit disable to fail open or surface as 500

- issue HIGH S2:Retirement_test repository wide grep zero for authentication_probe_failed contradicts the retained probe and access observation vocabulary

### MEDIUM

- issue MEDIUM S2:Store the toggle authority and natural key omit executor scope, so one shared database row can disable another installation

- issue MEDIUM S2:Write_semantics enable validation observes the PATH binary while prepare_launch may use bin_override, so compatibility at toggle time has no stable executable identity

- issue MEDIUM S2:REST_surface a write only route plus installed only capabilities exposes no persisted enablement read for reload or S3

### LOW

- issue LOW S2:Topology connection_missing is only a lower level ConnectionResolutionOutcome and does not currently exist in ResolutionRejectionCode, so saying it stays is ambiguous

## Review evidence

evidence main 506e04093e7075fa8f1e2ff5f6eb760b556a8879 and both spec digests unchanged, tracked tree pristine
