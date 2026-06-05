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

Branch `fix/comparator-truth` starts at `5591db86` and ends at `e894fadee134293cd9b504d84703af74f735020f`.

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

## E1 and N4 nested presence

- Commits: `0f1f6b27`, `fcbd20da`
- Net line delta: `+104`
- Failing before: a nested `cache_control` flicker returned BREAKING at `/tools, /tools/0`. A real description change beside the flicker named `/tools`, `/tools/0`, and `/tools/0/description`.
- Passing after: the flicker returns INSUFFICIENT at `/tools/0/cache_control`. The real change stays BREAKING and names only `/tools/0/description`. All 25 evidence tests and focused mypy passed at the green commit.
- Shared cause: container digests inherit changes from optional descendants. The comparator now collapses presence descendants, excludes unresolved pointers and their ancestors from decided drift, and reports only decided pointers with no changed descendant.
- Reuse: moved the existing presence diagnostic block into `_presence_refusal` to keep `compare_baseline_bundles` at 133 lines. Added no decision table or production type.

## E2 cross launch extras

- Commits: `22bbf888`, `47688c85`
- Net line delta: `+34`
- Failing before: changes to `client_metadata`, `previous_response_id`, and `prompt_cache_key` returned BREAKING. The control change to `service_tier` also returned BREAKING.
- Passing after: the three launch identity extras return EXACT. The `service_tier` change still returns BREAKING at `/service_tier`. The evidence, wire normalization, private import, and focused mypy checks passed.
- Reuse: promoted the existing inline keys to public `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. Both `normalize_request` and the masked raw fingerprint consume it. Added no mask or duplicate key set.

## E3 and E5 CLI evidence

- Commits: `4290131a`, `8f0c8e70`
- Net line delta: `+18`
- Failing before: a real BREAKING bundle exited 1 but printed no reason.
- Passing after: BREAKING prints `reason=stable baseline fingerprint changed at /tools/0/description`. The existing INSUFFICIENT output still prints its pointer and settlement rule. All harvest and capture tests passed with focused mypy.
- Reuse: the CLI matrix now builds validated `BaselineBundle` instances through the existing `_bundle` test factory. The `str` subclass double is gone. `promotes_baseline` is evaluated once for both diagnostics and exit status.

## E4 static evidence validation

- Commits: `d2d0b376`, `10165c99`
- Net line delta: `0`
- Failing before: `read_baseline_bundle` accepted a stored `static_fingerprint` that disagreed with `static_nodes`.
- Passing after: `BaselineBundle.validate_probe_contract` recomputes the canonical digest and rejects the mismatch. The evidence, capture, and harvest modules passed with focused mypy.
- Choice: validated the stored pair because the fingerprint is derived from the nodes. Deleted the comparator branch that only inconsistent bundles could reach.

## Final gates

- Formatting commits: `f29e8c16`, `0192c746`, net line delta `-15`.
- Correction diff from `0192c746`: `+436`, `-120`, net `+316`.
- Round 2 diff from `9d8dcd16`: `+239`, `-83`, net `+156`.
- Final branch diff: `+1,219`, `-309`, net `+910`. Production net is `+182`; test net is `+728`.
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: all 16 red and green pairs passed. The four round 2 pairs reproduced 2, 1, 1, and 1 failing tests before their fixes, then passed all 5 after their fixes.
- `cd api && just check`: passed and left all 773 files unchanged. Mypy checked 773 source files.
- `cd api && just test`: 3,827 passed with 25 warnings in 43.32 seconds.

## Live proof

- Before: tree clean at `10165c99844c`; default store absent.
- First command: `cd api && uv run python -m transport_matters.baseline_harvest --harness claude`.
- First exit: `1`.
- First outcome: none. Capture did not start and no version 2 bundle was written.
- Error: owner Claude credential unavailable. The command named `CLAUDE_CONFIG_DIR=~/.claude-auth claude auth login` as the required bootstrap.
- Second command: not run because the same credential blocker prevents capture.
- After: tree clean at the same HEAD. The default store remains absent.

## Live proof (credentialed)

Owner Claude credential present at `~/.claude-auth`. `claude` at `/Users/alphab/.local/bin/claude`,
`mitmdump` at `/Users/alphab/.pyenv/shims/mitmdump`. Tree clean at `10165c99844c` before and after;
no repo file modified.

### Result

**Run 1 failed in the capture path. Run 2 was not attempted, because run 1's blocker is
infrastructure and re-running would burn owner credits to reproduce the same failure.**

- Command: `cd api && uv run python -m transport_matters.baseline_harvest --harness claude`
- Exit: `1`
- Stderr: `claude/sonnet: no unique completed exchange resolves to the delivery for claude/sonnet/a1`
- Bundle written: **no**. `~/.transport-matters/baselines` does not exist.
- `current` promoted: **no**. Nothing to promote.
- Cell reached: `claude` / `anthropic` / `sonnet` (`anthropic/claude-sonnet-5`), probe `a1` only.
  Probes `b` and `a2` never ran.

The message is a 180-second timeout fall-through in
`baseline_capture::_wait_for_correlated_exchange`, not a correlation ambiguity. See attribution
below: the correlation was in fact correct.

### What the run actually produced

The capture path got further than any prior attempt. Credentials worked, the proxy captured real
Anthropic traffic, and the model answered. Run dir:
`~/.transport-matters/workspaces/hps7m0000gn-t-transport-matters-baseline/4e45b4a7/bea95b76-8f72-4b8d-8f63-8a0137393ee3`
(three complete exchanges, each with `request.raw`, `request.ir.json`, `response.ir.json`,
`response.raw`).

| Exchange | Shape | Response | What it is |
|---|---|---|---|
| `b422e844` | 1 message, 51 chars, no system, no tools | `http_429` | the `quota` preflight request |
| `94c924da` | 3 system parts, 14 tools, 42,708 tokens | `end_turn`, 7 output tokens, 5 chars | **the owned turn** (the 5-char reply is `ALPHA`) |
| `c0d36742` | 3 system parts, 1 message, 276 chars | `end_turn`, 16 output tokens | **the Claude title side request** |

The title request's first user block is
`<session> Reply with exactly ALPHA. </session>  Write the ti…` — it carries the controlled prompt
**verbatim**, which is exactly the U5 collision.

### U5: proven live, and this is the thing no unit test could prove

Replayed the real captured set through `controlplane/envelope::extract_delivery_id` with
`launch_delivery_fields("Reply with exactly ALPHA.", …)` (`probe_u5.py`, read-only):

```
b422e844  complete=True  tools=0   msgs=1  match=False  first_user='quota'
94c924da  complete=True  tools=14  msgs=2  match=True   first_user="<system-reminder> As you answer…"
c0d36742  complete=True  tools=0   msgs=1  match=False  first_user='<session> Reply with exactly ALPHA. </session>  Write the ti…'
candidates matching the delivery: 1 -> ['94c924da']
```

**Exactly one candidate, and it is the right one.** The title side request was present, carried the
prompt verbatim, and was correctly rejected — `_has_prior_assistant_activity` plus the whole-block
digest do the work a substring correlator could not. Under the parent correlator this is two hits
and a raise. U5 is proven against real traffic.

### U7: proven insufficient, live

The session store is **one migration behind head** and the preflight let the run proceed anyway.

```
check_session_store()          -> None          (passes)
database                        -> localhost:55432/transport_matters   (channel: stable)
db revision                     -> 0033_provider_access_evidence
expected head                   -> 0034_wire_request_divergence
wire_exchange request columns   -> request_extras, request_metadata, request_raw_bytes, request_kind
```

Consequence, from the run's own proxy log (`logs/mitmdump.log`, the only error class in 182 lines,
six occurrences):

```
psycopg.errors.UndefinedColumn: column "request_wire_bytes" of relation "wire_exchange" does not exist
[08:23:38.961] wire exchange emission failed exchange=b422e844 … failures=1
… failures=6
```

`session_store_preflight::check_session_store` proves **reachability only**; it calls
`_reachable_database_url()` and returns its error. `prepare_session_store` is the sibling that runs
`apply_migrations`, and the capture path (`baseline_capture::_capture_probe`) calls the former. So
U7's preflight stops a run against an absent store and waves through a store that cannot accept a
single write. The run then burned three real Anthropic calls and 180 seconds before failing with a
message about correlation.

### U6: not exercised

No transcript snapshot was produced: `<run_dir>/transcripts/` does not exist and no `*.jsonl` was
written there, so `transcript_complete` was never true and the loop timed out with its unique
candidate already in hand. `_transcript_has_reply` therefore never ran on real data. U6 is neither
proven nor disproven by this run.

**What I cannot prove, stated plainly.** I cannot show from surviving artifacts *why* the tailer
produced nothing. `sessions.json` records the session as `minted: true` with a `file_tail` source
descriptor pointing at `<run_dir>/runtime-home/claude/projects/…/767c123e-….jsonl`, but the overlay
`runtime-home` is removed at teardown, so the native transcript is gone. The snapshot writer is
disk-only (`storage/transcript_snapshot::make_transcript_snapshot_writer`) and does not require a
successful Postgres write, so the schema failure is not automatically the cause; it may act through
session registration (`addon_runtime::_register_owned_cursor`), or the tailer may never have found
the file. The only error in the log is the schema mismatch.

### Observation, not filed as a finding and not fixed

`_wait_for_correlated_exchange` returns one message for four distinct states: no candidate, several
candidates, a candidate with no transcript, and an incomplete artifact set. Here it reported a
correlation failure for an infrastructure failure, which is the most expensive possible
misattribution — 180 seconds and three billed calls per probe. The loop already knows which
condition it is in.

### What is needed to complete the live proof

Bring the stable-channel session store at `postgresql://…@localhost:55432/transport_matters` from
`0033_provider_access_evidence` to head `0034_wire_request_divergence`. That is the single specific
thing. The backend applies it itself on startup via
`session_store_preflight::prepare_session_store(materialize=True)`; `transport-matters channel
ensure-db stable` is the repo's provisioning entry point for the same store. I did not run either,
did not start any service, and did not modify the store.

Once the store is at head, the two-run proof can be attempted again from a clean state. Nothing
observed in this run contradicts the branch: U5 is proven correct, the wire capture and credential
path work end to end, and the failure is a preflight that checks reachability where it needed to
check schema head.

### Artifacts

- Run dir (evidence preserved, untouched):
  `~/.transport-matters/workspaces/hps7m0000gn-t-transport-matters-baseline/4e45b4a7/bea95b76-8f72-4b8d-8f63-8a0137393ee3`
- `probe_u5.py` in
  `/private/tmp/claude-501/-Users-alphab-Dev-LLM-DEV-helioy-transport-matters/992bed90-2f62-4717-bcac-c50f37e345f7/scratchpad/`
- Source homes from the attempt:
  `$TMPDIR/transport-matters-baseline/.baseline-sources/93d59f2c-6fab-4889-bc06-66407c6cf42c/sonnet/a1`
  (empty, as `a1` never completed)

## Unblock, re-run, and Option B

Tree clean before and after. Branch `fix/comparator-truth`, `10165c99844c` → `427720220d61`,
eleven additive commits, no rebase and no force-push.

### T1. Store migrated

`transport-matters channel ensure-db stable`, run after reading migration `0034` and confirming it
is two nullable `ADD COLUMN`s with no default, no update and no backfill.

```
database transport_matters: exists
session store at head (0034_wire_request_divergence)
db revision -> 0034_wire_request_divergence   head -> 0034_wire_request_divergence
new columns -> ['request_body_decoding_diverged', 'request_wire_bytes']
```

The database already existed; the command only migrated. Proven by the next run: **zero psycopg
errors in the proxy log, against six on the previous run.**

### T2. Re-run: the store blocker is gone, a second blocker is underneath it

**Run 1: exit 1, no bundle written, `current` not promoted.** Run 2 not attempted, and the reason is
structural rather than budgetary: run 2 is defined as an exact comparison against run 1's bundle, and
run 1 wrote no bundle. A second harvest would repeat run 1 identically.

```
claude/sonnet: no unique completed exchange resolves to the delivery for claude/sonnet/a1
```

Same message, different cause. What the run proved:

- **The wire path is healthy.** Three exchanges captured, zero store errors, the model answered.
- **U5 confirmed again, on an independent capture.** The title side request was present and carried
  the prompt verbatim; `extract_delivery_id` matched exactly one exchange, the owned 14-tool turn.

```
b1d1b249  tools=0   msgs=1  match=False  first_user='quota'
19876559  tools=0   msgs=1  match=False  first_user='<session> Reply with exactly ALPHA. </session>  Write the ti…'
f2ff59e7  tools=14  msgs=2  match=True   first_user="<system-reminder> As you answer the user's questions…"
candidates matching the delivery: 1 -> ['f2ff59e7']
```

- **U6 still not exercised, and now the reason is identified.** The launched client was alive during
  the run as pid 72389:
  `claude --model sonnet --dangerously-skip-permissions --session-id 9a96998c-… "Reply with exactly ALPHA."`
  and the overlay home was its config dir (`runtime-home/claude/sessions/72389.<hash>.key`). The
  client created `runtime-home/claude/projects/-private-var-…-transport-matters-baseline/` and wrote
  only an empty `memory/` inside it. `9a96998c-eb0d-4b53-b65a-174cbb3b6e39` exists **nowhere on
  disk**, in the overlay or the owner home, during the run or after teardown. The descriptor
  `sessions.json` records, and the tailer watches, a path the CLI never created.

  `cli/launch_profile::ClaudeLaunchProfile.prepare` carries the comment "claude --session-id CREATES
  the transcript (verified)". Against Claude Code **2.1.234** that no longer holds for this launch
  shape. `transcript_complete` can therefore never become true, so `_transcript_has_reply` is
  unreachable in a live run.

  This is harness drift, upstream of the branch, and fixing it is adapter work outside this
  branch's constraint. It is the next blocker for a live baseline, and it is exactly the class of
  change Transport Matters exists to detect.

  Ruled out on the way: the two `~/.claude/projects/…-api/*.jsonl` files written during each run are
  the model enumeration probe's own sessions (they carry `/effort` and `/model` commands and the api
  cwd), not the controlled probe.

### T3. Option B, plus the two live findings

| Unit | Red | Green | Bracket |
|---|---|---|---|
| B1a launch identity on both axes | `21f95323` 9 failed / 3 passed | `5f5223cd` 12 passed | PASS |
| B1b refused subtree | `9a9d3179` 2 failed / 1 passed | `36b3a9a4` 3 passed | PASS |
| B2 presence invariant, 16 cells | `9cce3f7d` 4 failed / 12 passed | `236ebbf3` 16 passed | PASS |
| B3 store schema in preflight | `2b935f8b` 1 failed | `058a6bf4` 1 passed | PASS |
| B4 timeout cause | `265d7548` 2 failed | `72ef3708` 2 passed | PASS |

**B1**, the three edits, each deleting a conditional:

1. `classify_aba` filters `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` where `nodes_by_probe` and
   `leaves_by_probe` are built, so both axes derive from one key set. Value masking stays on the
   fingerprint axis, correctly: the evidence axis compares classifications, not digests.
2. `_covers` replaces three inline prefix expressions in `compare_baseline_bundles`, and the
   adjudication subtraction runs in both directions.
3. The presence refusal drops its `value_evidence == STABLE` conjunct.

**Net line delta, measured and not as hoped.** Production `+77 / -14`, net `+63` across three files;
`baseline_evidence.py` alone is `+47 / -12`, of which 9 added lines are comments and 7 are the
`_covers` definition and docstring. The executable delta there is `+26 / -8`. It is not negative.
What went down is the count of hand-rolled subtree relations, 3 → 1, and the number of node
universes, 2 → 1. Two of the three edits are pure deletions; the growth is the shared relation, its
one docstring, and the formatter expanding two dict comprehensions across lines.

**B2** is `test_baseline_comparator_invariants.py`: presence 3/2/1/0 × top-level/nested × same/changed
value, plus the launch-identity and refused-subtree invariants. Separate module because
`test_baseline_evidence.py` was at 689 lines against the repository's 700-line limit; it imports the
existing `_bundle` and `_probe` rather than restating them, which the private-import boundary
permits for tests and which `test_baseline_harvest` already does.

**B3** is a schema-version check, not a write probe, and the reasoning is worth stating: the failure
was a schema mismatch; a write probe would need a real table and a side effect to prove anything;
and `apply_migrations` already treats head equality as its own definition of ready. `check_session_store`
now returns an error naming the head revision and the command that fixes it.

The repository already owned this behaviour, asserting the opposite half of it:
`test_capture_reachability_check_does_not_run_migrations` pinned both "does not migrate" and "returns
None when behind head" under one name. The first claim survives and is kept; the second is what the
live run disproved. Renamed to
`test_capture_store_check_refuses_a_behind_head_store_without_migrating`, asserting both halves, and
the standalone module added mid-round was removed rather than left as a second home for one fact.
Its bracket is verified in both places: as committed (`2b935f8b` → `058a6bf4`), and by restoring
`session_store_preflight.py` to `058a6bf4^` under the amended test, which fails and then passes.

**B4** keeps the last candidate set outside the wait loop and names which half is missing: a matched
delivery with no transcript reply, or no matching exchange at all. On this branch's own live run the
new message would have pointed at the transcript on the first read.

### Gates

- `cd api && just check`: ruff format, ruff check, mypy — clean, 774 source files.
- `cd api && just test`: **3,860 passed** in 47.69s, against 3,827 before the round (+33 cases).
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: **ALL BRACKETS PROVEN**, 21 pairs.
  The script needed two corrections to run the new pairs, both of which make it more honest for the
  existing ones too: test paths are now repo-relative (the `cli/` suite is not flat under
  `src/transport_matters/`), and it exports `TRANSPORT_MATTERS_TEST_DATABASE_URL` the way the repo
  recipe does, without which every database-backed test errors instead of running.

### Incident, disclosed

While proving one bracket I ran `git stash push <file>` on a file that had no uncommitted changes.
That silently created no entry, and the following `git stash pop` applied an unrelated pre-existing
stash (`stash@{0}`, "WIP on main", touching `TLDR.md`), which conflicted. Nothing was lost: the pop
failed, so the entry was never dropped and is still on the stack, and `TLDR.md` was restored with
`git checkout HEAD --`. The remaining bracket proof was done by writing the parent revision of the
production file directly instead. Verify a stash push produced an entry before popping.

### Still open

- The Claude 2.1.234 transcript behaviour above, which blocks any live baseline.

## Final builder round

Tree clean at `427720220d6143eda17b26c2650c3d6f48069533` before the round. Final head
`bf9b26307dcf393ad3950689eab5045868401ca9` contains eleven additive commits. The branch was not
rebased or force pushed.

### Findings and brackets

| Unit | Red commit | Green commit | Proof |
| --- | --- | --- | --- |
| F1 and G1, full presence cross product | `aef3e384` | `0c7a6a70` | 3 failed and 93 passed, then 96 passed |
| F2 and F7, removal precedence and pointer | `000b2079` | `44085572` | 1 failed, then 1 passed |
| F3, controlled prompt plan | `0d580ed6` | `a6975ae6` | 1 failed, then 1 passed |
| F4, F5, and F6, schema preflight | `6040622e` | `abdba73c` | 2 failed, then 2 passed; the full preflight module passed 10 tests |
| F8, request without response | `76470f9c` | `4c965ac0` | 1 failed, then 1 passed |

The G1 sweep contains 96 cells. It varies reference presence and candidate presence independently
over 3, 2, 1, and 0 carriers. It also varies leaf, nested leaf, and container placement, with equal
and changed values. Every cell calls `compare_baseline_bundles` and `promotes_baseline`.

The red F1 commit failed only the three changed 1 of 3 against 1 of 3 cells. Leaf, nested leaf, and
container placements all returned `EXACT` and promoted. The green commit returns
`INSUFFICIENT` and prevents promotion. The matching unchanged cells remain `EXACT` and promote.
The settled 2 of 3 changed value cells remain `BREAKING`.

`compare_baseline_bundles` now reads stored probe digests for terminal pointers whose value source
remains `UNKNOWN`. This closes the missing 1 of 3 comparison without importing launch identity
through ancestor digests or changing classified prompt and session values.

Demonstrated removals now take precedence over an unrelated presence refusal when the reference
observed the removed pointer in all three probes. The reason names every removed pointer. The prompt
plan is part of the comparison key, so different controlled inputs return `INSUFFICIENT` and cannot
promote.

`current_revision` accepts an optional timeout. The bounded path applies the timeout to both the
connection and the PostgreSQL statement. `check_session_store` converts SQLAlchemy failures to its
string error contract. A mismatch message names both revisions and gives separate older, newer, and
divergent guidance. The migration regression now downgrades by `-1`, captures the immediate
predecessor, and proves that the capture check does not migrate it.

The correlation wait now tracks request matches before `response.ir.json` exists. Timeout messages
distinguish an unmatched delivery, a matched request without a response IR, and a completed exchange
without a transcript reply.

No production file, helper, type, adapter, command, or parallel path was added. Production changed by
31 net lines. Tests changed by 182 net lines. `baseline_evidence.py` is 617 lines and
`compare_baseline_bundles` is 149 lines.

### Final gates

- `cd api && just check`: passed. Ruff left 774 files unchanged, lint passed, and mypy found no
  issues.
- `cd api && just test`: 3,945 passed with 24 warnings in 43.87 seconds.
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: all 26 pairs proven. The five new
  pairs appear in the table above.
- Focused comparator run: 139 passed.
- Focused preflight run: 10 passed, including the immediate predecessor migration test.
- Focused capture run: 11 passed.

No live harvest was run. The known Claude 2.1.234 transcript blocker remains outside this round.

## Round seven

Tree clean at `bf9b26307dcf393ad3950689eab5045868401ca9` before the round. Final head
`e894fadee134293cd9b504d84703af74f735020f` contains six additive commits. The branch was not
rebased or force pushed.

### Findings and brackets

| Unit | Red commit | Green commit | Proof |
| --- | --- | --- | --- |
| H1, H2, and H3, comparator sweep | `ede52d9e` | `d50a5190` | 12 failed and 198 passed, then 210 passed |
| H1 and H3, mixed masked classifications | `f454b7bf` | `d50a5190` | 12 failed, then 12 passed |
| H4, all schema probe bounds | `fcb8f6dc` | `a93b3fed` | 1 failed, then 1 passed |

The round seven sweep contains 222 cells:

- 192 cells vary reference and candidate presence independently over 3, 2, 1, and 0 carriers.
  They also vary equal and changed values, equal and changed JSON kinds, and leaf, nested leaf, and
  container placement.
- 18 cells give each probe a separate value. They vary matching presence over 3, 2, and 1 carriers,
  maskable and nonmaskable text, and all three placements. Both bundles classify the tested pointer
  as `UNKNOWN`.
- 12 cells place `STABLE` and `UNKNOWN` evidence on opposite sides. They vary both directions,
  matching presence over 3 and 2 carriers, and all three placements.

Every cell calls `compare_baseline_bundles` and `promotes_baseline`. At `bf9b2630`, the sweep failed
six H1 cells and six H2 cells. The H1 cells were maskable `UNKNOWN` evidence at matching 3 of 3 and
2 of 3 presence. The H2 cells were matching 2 of 3 kind changes across both value states. All
placements failed. The nonmaskable `UNKNOWN` cells already refused. The mixed classification sweep
also failed in both directions.

For H1, `compare_baseline_bundles` now ignores raw classification and digest differences when both
bundles already hold the pointer in `static_nodes`. The existing masked fingerprint owns that
verdict. Raw `UNKNOWN` differences still reach comparison when either bundle lacks the masked static
node, so genuine nonmaskable disagreement remains `INSUFFICIENT` and cannot promote. The change adds
no mask, walker, or projection.

For H2, unresolved partial presence now requires different carrier sets. A matching 2 of 3 kind
change therefore reaches the existing static fingerprint verdict and returns `BREAKING`. Matching
1 of 3 value disagreement remains `INSUFFICIENT` through the raw `UNKNOWN` evidence check.

For H4, bounded `current_revision` now supplies all four connection protections used by the launch
gate: connection timeout, statement timeout, TCP keepalive settings, and TCP user timeout. The
single `timeout` argument caps each mechanism. Two protections were insufficient because an
accepted TCP connection can stop responding before PostgreSQL can enforce the statement timeout.

No production file, helper, type, adapter, command, or parallel path was added. Production changed
by 6 net lines. Tests changed by 146 net lines. `baseline_evidence.py` is 618 lines,
`compare_baseline_bundles` is 149 lines, and the expanded invariant test file is 425 lines.

### Round seven gates

- `cd api && just check`: passed. Ruff left 774 files unchanged, lint passed, and mypy found no
  issues in 774 source files. The first run caught the fixed length tuple annotation in the expanded
  fixture. Commit `e894fade` corrected the annotation, and the repeated gate passed.
- `cd api && just test`: 4,072 passed with 25 warnings in 48.87 seconds.
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: all 29 pairs proven and the script
  ended with `ALL BRACKETS PROVEN`.
- Focused comparator run: 265 passed.
- Focused preflight run: 11 passed with the required test database setting.
- `git diff --check bf9b2630..e894fade`: passed.

No live harvest was run. The known Claude 2.1.234 transcript blocker remains outside this round.
