---
title: Baseline comparator build record
type: projects
tags: [transport-matters, baseline-capture, comparator, build]
summary: Commit, regression, gate, and live proof record for fix/comparator-truth
status: active
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

# Baseline comparator build record

Branch `fix/comparator-truth` starts at `5591db86` and ends at `9d8dcd16e024`.

## U0 consumer wiring

- Commits: `86cfcc9e`, `b1a528d7`
- Net line delta: `+34`
- Failing before: `test_main_reports_comparison_outcome_in_exit_code` failed because the CLI could not receive the outcome. `test_bundle_store_promotes_only_passing_comparisons` showed that BREAKING and INSUFFICIENT replaced current.
- Passing after: both tests passed, plus `test_harvest_runs_fresh_correlated_aba_and_persists_bundle`.
- Reuse: returned the existing `BundleRef` with the existing `DriftOutcome`. Bootstrap, EXACT, and COMPATIBLE promote. Compared BREAKING and INSUFFICIENT do not promote.

## U1 artifact version 2

- Commit: `e7f9b12c`
- Net line delta: `+36`
- Test and implementation share one commit because the version bump has no useful intermediate implementation state.
- Passing after: `test_version_one_bundle_load_requires_regeneration`, `test_version_one_current_pointer_requires_regeneration`, and `test_bundle_store_is_immutable_self_contained_and_hash_validated`.
- Reuse: changed `BaselineBundle` and `_CurrentBundlePointer` in place. Added no migration or compatibility reader.

## U2 canonicalization

- Commits: `3a6373db`, `b68afc8e`
- Net line delta: `-30`
- Failing before: `test_native_node_digests_use_shared_canonical_json` reproduced the `1.0` digest mismatch.
- Passing after: that test and all 18 request inventory tests passed. Focused mypy passed.
- Reuse: bound node digests to `canonical_json` and kinds to `json_kind`. Deleted `_canonical_json_bytes`, `_json_kind`, `_JsonObject`, and its deep copy.

## U3 fingerprint masks

- Commits: `1d2998bb`, `46b205a4`
- Net line delta: `+75`
- Failing before: `test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking` returned BREAKING.
- Passing after: the test returned EXACT, all baseline evidence tests passed, and focused mypy passed.
- Reuse: read `ProbeEvidence.normalized_request` and inventoried it with `observe_request_json`. Added no mask or pointer walker.

## U4 comparator axes

- Commits: `c6870c05`, `9a4a763f`
- Net line delta: `+118`
- Failing before: `test_presence_sampling_reports_insufficient_without_changing_static_membership`, `test_exact_comparison_reads_value_evidence`, and `test_removing_demonstrated_static_pointer_is_breaking` all failed with the contradictory verdicts.
- Passing after: all three and the full baseline evidence module passed. Focused mypy passed.
- Reuse: kept `EvidenceKind` for value evidence and put an inline presence literal on `PointerEvidence`. Added unresolved pointers to `BaselineComparison`. Added no new production type or decision table.

## U5 correlation

- Commits: `5fa903af`, `39f4ac6d`
- Net line delta: `+35`
- Failing before: `test_harvest_ignores_title_request_that_wraps_controlled_prompt` raised on the title side request.
- Passing after: the title request was ignored and only `owned000` was selected in all probes. The baseline, inventory, and evidence modules passed. Focused mypy passed.
- Reuse: used `read_captured_exchange`, `launch_delivery_fields`, and `extract_delivery_id`. Deleted `request_contains_text` and changed the method to `delivery-id`.

## U6 transcripts

- Commits: `a50cf740`, `13e94025`
- Net line delta: `+152`
- Failing before: `test_grok_user_then_assistant_updates_complete_transcript`, `test_malformed_complete_transcript_record_does_not_hide_reply`, `test_half_written_multibyte_tail_does_not_hide_reply`, and `test_raw_u2028_inside_complete_record_does_not_hide_reply` all failed.
- Passing after: all four and the full baseline capture module passed. Focused mypy passed.
- Reuse: used `iter_complete_records`, `get_adapter`, `SessionBinding`, `TurnContext`, and `TranscriptAdapter.normalize`. Deleted `_json_has_assistant_role`. Added no parser, adapter facade, or provider switch.

## U7 preflight

- Commits: `23452d25`, `ead2dd60`
- Net line delta: `+33`
- Failing before: `test_session_store_preflight_stops_before_capture_starts` showed that capture continued after a session store error.
- Passing after: the test proved that no proxy preparation, lease, or client supervisor started. The full baseline capture module and focused mypy passed.
- Reuse: called `CapturedRunDependencies.check_session_store` at `_capture_probe` entry. Added no preparation wrapper.

## C1 masked raw fingerprint

- Commits: `e3bc0ab0`, `caead545`
- Net line delta: `+39`
- Failing before: date and cwd changes remained EXACT, while changes to `max_tokens`, `stream`, `temperature`, and `model` also returned EXACT.
- Passing after: date and cwd changes remained EXACT. All four stable wire scalar changes returned BREAKING. The baseline evidence and wire normalization modules passed. Focused mypy passed.
- Reuse: renamed `_mask_cross_launch_body` to `mask_cross_launch_body`, used it with `observe_request_json`, and stored stable records as the existing `RequestJsonNode` type. Added no mask, walker, projection, or production type.

## C2 and C6 comparator precedence and coverage

- Commits: `44b37b6b`, `eda1af4f`
- Net line delta: `+96`
- Failing before: the mixed `/core` change and `/feature` flicker returned INSUFFICIENT. The isolated 3 of 3 addition, 2 of 3 addition, mirror flicker, and COMPATIBLE cases already passed.
- Passing after: the mixed case returned BREAKING and named `/core`. The four existing behavior locks remained green. The full baseline evidence module and focused mypy passed.
- Reuse: compared the persisted `RequestJsonNode` records by pointer. Added no decision table or new type.

## C3 bootstrap exit semantics

- Commits: `7a259be0`, `c2ce9985`
- Net line delta: `+25`
- Failing before: compared INSUFFICIENT and bootstrap INSUFFICIENT both exited 1.
- Passing after: bootstrap exited 0. Compared INSUFFICIENT still exited 1. The capture, harvest, and evidence modules passed. Focused mypy passed.
- Reuse: `promotes_baseline` now owns the rule used by both `write_baseline_bundle` and the CLI. `harvest_controlled_baseline` returns the existing `BaselineBundle` with its `BundleRef`.

## C4 actionable refusal details

- Commits: `330f1b17`, `c3eef8da`
- Net line delta: `+156`
- Failing before: the comparator emitted generic prose, the immutable bundle discarded `/feature`, and the CLI omitted the pointer and settlement rule.
- Passing after: the bundle persisted `/feature`. The comparison recorded `reference=2/3 candidate=3/3` and stated that both bundles must observe the pointer in all three probes. The CLI printed both the pointer and the rule. The three focused regressions, all 38 baseline tests, and focused mypy passed.
- Reuse: added one field to `BaselineBundle` using the existing `JsonPointer` type. Presence ratios come from the existing `presence_by_probe` evidence.

## C5 real preflight paths

- Commits: `84e372d1`, `9d8dcd16`
- Net line delta: `0`
- Failing before: the session store refusal left the workspace root behind. The corrected assertion watches the production `.baseline-sources` path.
- Passing after: neither the workspace nor `.baseline-sources` existed after refusal. The full baseline capture module and focused mypy passed.
- Reuse: removed the eager workspace `mkdir`. The existing source home creation now creates the workspace only after the preflight passes.

## Final gates

- Formatting commits: `f29e8c16`, `0192c746`, net line delta `-15`.
- Correction diff from `0192c746`: `+436`, `-120`, net `+316`.
- Final branch diff: `+1,044`, `-290`, net `+754`. Production net is `+143`; test net is `+611`.
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: all 12 red and green pairs passed, including the five correction pairs.
- `cd api && just check`: passed and left all 773 files unchanged. Mypy checked 773 source files.
- `cd api && just test`: 3,823 passed with 25 warnings in 40.90 seconds.

## Live proof

- Before: tree clean at `9d8dcd16e024`; default store absent.
- First command: `cd api && uv run python -m transport_matters.baseline_harvest --harness claude`.
- First exit: `1`.
- First outcome: none. Capture did not start and no version 2 bundle was written.
- Error: owner Claude credential unavailable. The command named `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login` as the required bootstrap.
- Second command: not run because the same credential blocker prevents capture.
- After: tree clean at the same HEAD. The default store remains absent.
