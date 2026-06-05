# PR #306 adversarial review

Verdict: issue, P1 severity, one finding.

Scope: `main` at `f9f61bc3bfd2c9c27a06e8e339e9eb5498f9ce74` through PR head `1d6d98eb8ba6c2e23562b0a6732db8390e348674` on `feat/s2g-drift-vocabulary-gaps`.

## Finding

### P1: a non-string Codex event type stalls transcript ingestion

The new per-batch deduplication token stores raw JSON values from `record.type` and `payload.type` in a set. Those values are typed as arbitrary JSON. A Codex record such as `{"type":"event_msg","payload":{"type":[]}}` is valid JSON and is correctly rejected by both `normalize()` and `is_certified_meta()`. The next step attempts to hash the list in `drift_tokens` and raises `TypeError` at [tailer.py lines 254 to 260](https://github.com/littleorgans/transport-matters/blob/1d6d98eb8ba6c2e23562b0a6732db8390e348674/api/src/transport_matters/index/tailer.py#L254-L260).

The exception escapes `_plan_ingest_records`. The live poll path then classifies it as a transient commit failure, leaves the cursor unchanged, and retries the same window forever. The record and every later record in that transcript never reach the session store. Replay calls the same planner and fails the rebuild. Drift detection therefore changes capture flow and emits repeated generic failure evidence instead of one exact record-line signal.

Direct read-only reproduction on the PR head:

```text
record = {"type": "event_msg", "payload": {"type": []}}
_plan_ingest_records(...)
TypeError: cannot use 'tuple' as a set element (unhashable type: 'list')
```

The same failure occurs for object values. The new tests use string unknowns only, so they do not exercise this boundary. Normalize the token components to hashable vocabulary categories before set membership, then add a live poll regression test proving that a non-string nested type emits once, submits the record, and advances the cursor.

## Requested checks

### C2 Codex per-item vocabulary

The outer item-key closure is correctly connected. `unknown_request_item_fields()` reports unknown keys, unknown item types, and non-object list members. `_detect_unknown_shapes()` unions those findings with the existing envelope findings, and the observer emits `unknown_request_field` from exact request bytes. The scanner stays independent of the parser's raw preservation path.

All eight owned Codex 0.144.4 preview requests scanned clean with both the envelope and item scanners. The `generate` and `previous_response_id` additions are legitimate literal baseline keys, not a wildcard: `generate` occurs in two requests and `previous_response_id` occurs in four.

### C3 transcript meta allowlist

Claude and Codex both implement the new closed `is_certified_meta()` seam. Unknown string record types and unknown Codex `event_msg` payload types enter the planned drift spans. Live polling sends exact line bytes through the existing guarded `emit_transcript_drift` hook. Replay calls the shared planner but has no drift hook and does not consume `drift_spans`, so rebuild remains silent.

The four owned preview transcripts contained 114 records. Every record normalized to a turn or matched the new certified meta vocabulary. The P1 finding above covers the malformed JSON type boundary that this happy-path corpus does not contain.

### Mutation integrity and focused tests

Four runtime-only mutations were verified without source edits:

1. Unwiring the item scanner made the observer integration test fail.
2. Neutering the scanner made the unknown item-key test fail.
3. Dropping tailer emission made the exact-line drift test fail.
4. Accepting every adapter record as meta made both unknown-record classifier tests fail.

After restoring normal runtime behavior, the four focused files passed: `83 passed in 0.39s`. The user-reported local `just check && just test-affected` gate was green. GitHub Actions were not used for the verdict.

## Nonblocking provenance accuracy

The two new envelope keys are correct allowlist entries, but the comment saying they occur on every exchange is inaccurate. Across the eight owned requests, two carry `generate`, four carry `previous_response_id`, two carry neither, and none carries both. The sanitized fixture combines them. This does not change a key-presence vocabulary verdict, but the comment and fixture should describe conditional baseline fields accurately.

The comment saying `internal_chat_message_metadata_passthrough` is stamped on every item is also stronger than the owned captures establish. Its use as one exact globally allowed metadata key remains compatible with the requested outer-key contract.

## Tree integrity

The repository was pristine before review. No repository files, branches, refs, or indexes were modified by the reviewer or review agents. Final head and tree verification is recorded after this report is written.
