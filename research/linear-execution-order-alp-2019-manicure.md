---
title: ALP-2019 Linear Execution Order Review for Manicure
type: research
tags: [linear, manicure, alp-2019, planning, exchange-list]
summary: Proposed ALP-2019 child order is workable but creates avoidable rework around fixture sharing, nested spawn anchors, and test refactors.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

The proposed ALP-2019 child issue order should be rejected as the final Nancy sequence. It respects the explicit ALP-2036 to ALP-2039 to ALP-2032 chain, but it runs several test and refactor tasks before the schema shape and shared fixture are stable.

## Project Metadata

- Project: `manicure`
- Working tree inspected: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm status: `.fmm.db` present and `fmm validate` reports 256 indexed files up to date
- Relevant areas: Python backend under `api/src/manicure`, React TypeScript frontend under `www/src`

## Architecture Notes

- `api/src/manicure/storage/base.py:102-132` defines `IndexEntry`; current anchor fields are flat at lines 120-122.
- `www/src/types.ts:46-65` mirrors frontend `IndexEntry`; current anchor fields are flat at lines 53-55.
- `www/src/hooks/useExchanges.ts:46-52` contains `adoptAnchor`, currently using nullish coalescing assignment and therefore directly targeted by ALP-2032 and ALP-2039.
- `www/src/components/exchangeListRows.ts:26-90` contains projection logic. ALP-2031 and ALP-2033 both touch this area.
- `api/src/manicure/test_track_manager_lifecycle.py` asserts flat anchor fields in multiple tests, notably around lines 318-326 and 458-466, so ALP-2037 should not run before schema churn.
- `api/src/manicure/codex/exchange.py:100-119` persists `assignment_index_fields(track_assignment)` before setting provisional state at lines 133-136, supporting the view that ALP-2028 is likely verify-only.

## Recommended Order

1. ALP-2030 Document or decide `spawn_order` semantics across multi-response track spawns
2. ALP-2036 Share `makeEntry` test fixture across ExchangeList tests
3. ALP-2039 Nest spawn anchor fields as `SpawnAnchor` on `IndexEntry`
4. ALP-2032 Tighten anchor field optionality between `IndexEntry` and `ExchangeTrack`
5. ALP-2035 Extract emit-track-assignment-anchors helper
6. ALP-2029 Add spawn anchor coverage to disk cache backfill tests
7. ALP-2031 Surface diagnostic when subagent anchor falls outside fetched window
8. ALP-2033 Document depth semantics for nested inline subagent rows
9. ALP-2034 Replace DOM-selector assertions in ExchangeList tests with row-projection assertions
10. ALP-2038 Convert `exchangeListRows.test.ts` to table-driven cases
11. ALP-2037 Convert `test_track_manager_lifecycle.py` to table-driven cases
12. ALP-2028 Persist Codex provisional spawn anchors before finalization, verify or close

## Risky Proposed Placements

- ALP-2029 before ALP-2039 writes coverage against the flat anchor shape, then ALP-2039 rewrites the schema to nested `spawn_anchor`.
- ALP-2031 before ALP-2036 adds or renames frontend row tests before fixture consolidation, creating unnecessary test fixture churn.
- ALP-2037 before ALP-2039 and ALP-2035 refactors backend lifecycle tests that currently assert flat anchor fields, then schema and helper changes can invalidate the table.
- ALP-2032 is too far from ALP-2039. Both touch `adoptAnchor`; the optionality fix should follow the nested shape change immediately.
- ALP-2034 before ALP-2038 is correct and should be preserved.

## Merge and Split Recommendations

- Consider merging ALP-2035 into ALP-2039 if one backend worker owns the schema migration. If kept separate, run ALP-2035 immediately after ALP-2039 or after ALP-2032.
- Keep ALP-2029 separate from ALP-2039 unless ALP-2039 expands to own disk cache backfill explicitly. The current separation is valid, but ALP-2029 should test the final nested shape.
- ALP-2030 is a decision fork. If it chooses track-local monotonic ordering, split implementation and regression into a separate issue. If it keeps response-local ordering, leave it as documentation only.
- ALP-2028 should be verify-only at execution time. If the premise proves false, close it. If it proves true, rewrite before implementation.

## Linear Relation Suggestions

- ALP-2036 blocks ALP-2039.
- ALP-2036 blocks ALP-2031 and ALP-2038 if fixture churn is to be minimized.
- ALP-2039 blocks ALP-2032.
- ALP-2039 blocks ALP-2035.
- ALP-2039 blocks ALP-2029.
- ALP-2030 blocks ALP-2037.
- ALP-2031 blocks ALP-2038.
- ALP-2034 blocks ALP-2038.
- ALP-2028 should be related to ALP-2021 and ALP-2029, not a blocker unless verification finds a real durability gap.

## Relevance to Helioy

This order keeps Nancy execution closer to a dependency graph rather than a priority list. It stabilizes shared fixtures, then schema shape, then correctness, then diagnostics, then cleanup refactors.

## Open Questions

- Whether ALP-2030 will remain documentation-only or become a behavior change.
- Whether ALP-2035 should be merged into ALP-2039 to avoid touching the same backend write sites twice.
