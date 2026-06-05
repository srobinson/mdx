---
title: Codex breakpoint edit-forward reconcile failure diagnosis and fix
type: sessions
tags: [backend, transport-matters, codex, serializer, breakpoint, debugging]
summary: Diagnosed pre-existing preserved-raw reconcile failure on agent-home Codex runs; fixed via wire-index stamps (PR#190)
status: active
source: backend-engineer
confidence: high
created: 2026-07-02
updated: 2026-07-02
---

## Summary

`transport-matters codex --agent-home-dir ...` + arm breakpoint + edit + forward failed with 422 "Codex serializer could not reconcile preserved raw input item at index 2". Verdict: pre-existing on main, not a PR#189 regression (all implicated modules outside PR#189's diff; reproduced on unmodified main with the real paused bytes). Fixed on `fix/codex-serializer-reconcile` (a59807a, PR#190).

## Root cause

Newer Codex CLIs stamp `internal_chat_message_metadata_passthrough` on every input message, so the parser preserves every message raw. Edits that drop a message (block toggle off, text cleared → `sanitize_curated_messages` removes it) left an unclaimable preserved entry under per-kind FIFO matching, and the reconciler raised. Companion defect: multi-part developer/system messages splintered into one item per part on re-emit, so even unedited pass-through mutated the wire (3 items → 7).

## Fix

Identity over heuristics, contained to `api/src/transport_matters/codex/`:
- Parser stamps each preserved item's wire index into owning `Message`/`SystemPart` `provider_data` (`tm_wire_index`) plus `provider_extras["input_item_raw_stamped"]`.
- Reconcile claims by exact index; kind-heuristic fallback for rebuilt messages; leftovers = operator deletions (dropped). Unstamped legacy IRs keep the strict raise.
- System parts sharing a stamp regroup into one wire item; stamps/marker stripped before emit; `materialize_input_items` gap-tolerant in stamped mode.

## Verification

Fixture `codex_response_create_agent_home.json` + 5 adapter tests + 7 unit tests; real-bytes replay through the release path (pass-through now wire-transparent, all deletion edits forward, no stamp leak); `cd api && just ci` green (1783 passed).

## Open items

- Live authenticated end-to-end repro pending Stuart (unit-level replay used exact production bytes).
- Diagnosis doc: repo `TMP/debug-codex-serializer.md`.
