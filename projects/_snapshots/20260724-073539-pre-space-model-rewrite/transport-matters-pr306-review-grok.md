# Review: PR #306 / feat/s2g-drift-vocabulary-gaps (main..1d6d98eb)

- **Range**: `main..1d6d98eb` (HEAD `1d6d98eb`)
- **Branch**: `feat/s2g-drift-vocabulary-gaps`
- **Reviewer**: grok (read-only; no repo writes)
- **Date**: 2026-07-18
- **Topic**: `tm-s2g-evaluator-build`
- **Tree at verdict**: pristine

## Verdict

**Clean.** C2 (codex per-item wire vocabulary) and C3 (transcript meta allowlist) close the gaps by extending the existing scanners and `emit_transcript_drift` path; no parallel drift machinery. Envelope additions are two specific keys. Unknown item keys/types and unknown transcript record types surface as drift with tests.

## Scope

12 files, +512 / −3:

| Concern | Files |
|---------|--------|
| C2 wire | `codex/request_parser.py`, `drift_capture.py`, `test_drift_capture.py`, fixture `codex_response_create_certified_0144.json` |
| C3 transcript | `index/adapters/{base,claude,codex}.py`, `index/tailer.py`, adapter + `test_tailer_drift` tests |
| Stub | `test_addon_runtime.py` (`is_certified_meta` on fake adapter) |

## Cross-family focus

### (a) Reuse existing scanners + emit_transcript_drift — no parallel path

**C2**

- New pure detector `unknown_request_item_fields(raw_body)` sits beside `unknown_request_fields` in `request_parser.py`.
- `_detect_unknown_shapes` for codex **unions** envelope findings with item findings and feeds the existing `WireDriftObserver` → `unknown_request_field` emission path.
- No new observer, emitter, or store.

**C3**

- New adapter method `is_certified_meta` closes the skip half of the transcript contract.
- Live poll path calls existing `emit_transcript_drift(..., "transcript_record_shape_mismatch", excerpt, None)`.
- Replay/`ingest_records` still uses `_plan_ingest_records` but **does not** invoke the hook (drift_spans discarded), so rebuilds do not duplicate evidence — intentional and correct.

### (b) `generate` + `previous_response_id` are specific, not wildcards

- Added as named members of `KNOWN_REQUEST_EXTRA_KEYS` only.
- Certified fixture asserts both present and silent under `unknown_request_fields`.
- No prefix/regex/wildcard widening of the envelope set.
- Per-item vocab is a closed `dict[str, frozenset[str]]` of known item types; unknown types are not absorbed.

### (c) Unknown per-item key / unknown record type surface as drift

**Wire (proven in tests)**

- Unknown item key → `input[message].telemetry_blob` → `unknown_request_field` evidence.
- Unknown item type → `input[]:hologram`.
- Non-object item → `input[]:<non-object>`.
- Certified 0.144 shapes silent end-to-end through `WireDriftObserver`.

**Transcript (proven in tests)**

- Unknown type `hologram` → `transcript_record_shape_mismatch` with the exact record line as excerpt.
- Certified meta (attachment, file-history-snapshot, …) silent.
- Conversational user/assistant without uuid classified non-meta → shape drift (not silent skip).
- One emission per vocabulary token per batch (flood control).

## Notes (non-blocking)

- `except ValueError, UnicodeDecodeError:` is valid on the project's required Python ≥3.14 (tuple form without parens); older CPythons reject it, but `requires-python = ">=3.14"` matches.
- Per-item scan is top-level keys only (not nested content shapes); that matches the C2 gap statement.
- Item findings log the names then emit one `unknown_request_field` evidence row with full request bytes (same as envelope), which is the existing observer contract.

## Issues

None (0 bugs, 0 merge-blocking suggestions).

## Authoritative gate

| Gate | Result |
|------|--------|
| `just check` | **exit 0** — desktop typecheck+tests; www format/lint/typecheck; api ruff + mypy (641 files) |
| `just test` | **exit 0** — desktop **102**; www **1771** passed (1247+24+8+286+185+21); api **2960** passed |

Tree remained pristine after the gate.

## Summary line (bus)

`review: clean; gate: check+test green (api 2960, desktop 102, www 1771) findings: ~/.mdx/projects/transport-matters-pr306-review-grok.md`
