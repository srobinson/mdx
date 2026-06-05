# Comparator review (Grok)

Reviewed `fix/comparator-truth` at `0192c746ed82f972b51d389235e05d5358a8560a` against `main` `5591db86`. Worktree empty before the read and after this file. No repo writes.

`conditional: I sign off conditional on the following changes:`

1. Point `test_session_store_preflight_stops_before_capture_starts` at `.baseline-sources`, so a `source_home.mkdir` that runs before `check_session_store` fails the test.
2. Isolate the D3 pair in `test_presence_sampling_reports_insufficient_without_changing_static_membership`: keep `/static` on both sides, add only `/feature` in 3/3 vs 2/3, and add the mirror (unchanged `/static` missing from probe B reports INSUFFICIENT, not BREAKING).

## Findings

### 1. Major. Preflight test watches a directory production never creates

- Location: `api/src/transport_matters/test_baseline_capture.py:412`
- Observation: After a failed session store check the test asserts `workspace / ".baseline-homes"` is absent. `_source_home` writes `workspace / ".baseline-sources" / <bundle> / <model> / <label>` and has done so since `5591db86`.
- Impact: Move `source_home.mkdir` above `check_session_store` and CI stays green. The harvest then leaves source homes behind on a store that every other capture path refused. `prepared == []` still proves `prepare_captured_run` did not run. It does not prove the mkdir half of U7.
- Basis: Production order at `_capture_probe` is check (`baseline_capture.py:172-174`) then mkdir (`:177`) then `prepare_captured_run`. The test name and commit claim that order. The path in the assertion is the only `.baseline-homes` string in the tree.
- Caveat: Production order is correct today. The lock does not lock.
- Link: https://github.com/littleorgans/transport-matters/blob/0192c746ed82f972b51d389235e05d5358a8560a/api/src/transport_matters/test_baseline_capture.py#L411-L413

### 2. Major. D3 tests do not isolate 3/3 vs 2/3, and never run the mirror

- Location: `api/src/transport_matters/test_baseline_evidence.py:364-402`
- Observation: `candidate()` emits `{prompt, optional feature}` and drops the reference `/static` field (`_bundle` default at `:97-99`). `fully_observed` is BREAKING even when `/feature` is never added: a candidate that only drops `/static` already returns `breaking-drift` (`demonstrated request fields were removed`). There is no pair that keeps `/static` and only adds `/feature` in 3/3 vs 2/3, and no pair that keeps an unchanged field and drops it from probe B.
- Impact: A future comparator that again labels a 3/3 constant addition COMPATIBLE, or a B flicker BREAKING, can keep this test green as long as dropping `/static` still trips BREAKING and `STABLE` + `sometimes` still trips INSUFFICIENT. That is the original contradiction returning without a red test.
- Basis: I ran the isolated cases through `compare_baseline_bundles` with `cd api && uv run python`. Production is already right: same `/static`, add `/feature` in 3/3 → `breaking-drift`; in A1+A2 only → `insufficient-evidence` on `/feature`, fingerprints equal; drop `/static` from B only → `insufficient-evidence` on `/static`, fingerprints equal. The test file does not ask those questions.
- Caveat: `fully_observed.static_fingerprint == undersampled.static_fingerprint` and the undersampled `unresolved_pointers == ("/feature",)` assertion are real. They lock presence independent membership and the 2/3 refusal. They do not lock the 3/3 BREAKING claim or the mirror.
- Link: https://github.com/littleorgans/transport-matters/blob/0192c746ed82f972b51d389235e05d5358a8560a/api/src/transport_matters/test_baseline_evidence.py#L364-L402

## Key checks

1. Promotion. `write_baseline_bundle` promotes when `reference_bundle_id is None` (bootstrap) or `reference_outcome` is `exact` or `compatible-drift`. Compared `breaking-drift` and `insufficient-evidence` write the bundle and leave `current` on the prior reference. First harvest in `test_harvest_runs_fresh_correlated_aba_and_persists_bundle` is bootstrap INSUFFICIENT and becomes the second harvest's reference. Not a Blocker.
2. Version rejection. Pointer and bundle both reject `artifact_schema_version != 2` with `regenerate the baseline` (`baseline_store.py:67-68`, `:81-82`). Harvest calls `read_current_baseline` before any `_capture_probe`. Pointer schema is `int`, so a v1 pointer parses and hits the regenerate error rather than a pydantic miss.
3. D3 production. Two axis split plus presence independent `static_records` (`len >= 2`, one digest) make the old BREAKING vs COMPATIBLE flip unrepresentable. Isolated reproduction above. Tests do not pin it (finding 2).
4. Correlation. `_capture_probe` builds `launch_delivery_fields(prompt, delivery_id)` and the wait loop requires `extract_delivery_id(...) == delivery_id`. `extract_delivery_id` matches a whole user text block digest, not a substring. The title fixture writes `Generate a title for: {initial_prompt}` on both raw and IR. Under the parent unique substring correlator that is two hits and a raise.
5. Adapter context. `SessionBinding` matches `CapturedRunEvidenceSource._check_transcripts`: stem as `session_id`, empty cwd/slug/hash, adapter provider. The normalize loop is in the existing `_transcript_has_reply`, not a new facade, type, or file.
6. Preflight production. `check_session_store` runs before `source_home.mkdir` and `prepare_captured_run`. The test does not prove the mkdir half (finding 1). Workspace `mkdir` in `harvest_controlled_baseline` is the operator directory with `exist_ok=True`, not a source home.
7. Dead code. `request_contains_text` and `_json_has_assistant_role` are gone, including the inventory assertions. `_json_contains_text` remains and is the transcript prompt probe.
8. Red/green, independent of the mechanical sweep.
   - U0 (`86cfcc9e` / `b1a528d7`): honest. Promotion cases fail if `current` always moves. CLI cases fail if `main` still returns 0 and never prints `outcome=`.
   - U5 (`5fa903af` / `39f4ac6d`): honest. The wrap is in the test commit. The parent correlator raises on two substring hits. The fix commit also writes `request.ir.json` for title, so green is not "title skipped for a missing IR file."
   - U4 (`c6870c05` / `9a4a763f`): the 2/3 INSUFFICIENT line and the equal fingerprint line fail on the parent. The 3/3 BREAKING line does not, because dropping `/static` was already BREAKING (finding 2).
   - U7 (`23452d25` / `ead2dd60`): honest for "no prepare." Dead for "no source home."
   - U1 (`e7f9b12c`): combined, as the build record said. Not scored as a defect.

No new production file, helper, type, adapter facade, command, mask, parser, or parallel compatibility path. Files stay under 700 lines. `compare_baseline_bundles` and `_transcript_has_reply` stay under 150.

Presence short circuit before fingerprint is the D3 rule (INSUFFICIENT, not BREAKING or COMPATIBLE). I did not treat that as a defect.

## Counts

Blocker 0, Major 2, Minor 0.

## Correction round at `9d8dcd16`

Worktree empty. `0192c746` is still an ancestor. I did not rerun `just check` / `just test`. Proofs used `cd api && uv run python`.

`conditional: I sign off conditional on the following changes:`

1. After `mask_cross_launch_body`, drop the existing cross-launch extras keys (`client_metadata`, `previous_response_id`, `prompt_cache_key`) from the raw body before fingerprint membership. A Codex `x-codex-installation-id` change must stay EXACT.
2. A nested STABLE+sometimes flicker must not become BREAKING through a parent container. `cache_control` missing from probe B on an otherwise static tool must report INSUFFICIENT on that pointer, not `changed at /tools`.

### Own findings

1. Resolved. `test_session_store_preflight_precedes_workspace_and_source_home_creation` asserts `workspace` and `workspace / ".baseline-sources"` are absent (`test_baseline_capture.py:452-453`). Harvest no longer mkdir's the workspace. `check_session_store` still runs before `source_home.mkdir`.
2. Resolved. `_bundle_with_feature_presence` keeps `/static` and varies only `/feature`. `test_presence_sampling_reports_insufficient_without_changing_static_membership` is the 3/3 vs 2/3 pair. `test_unchanged_field_flickering_out_of_probe_b_is_insufficient` is the B-flicker mirror. `test_prompt_derived_field_addition_is_compatible` is the COMPATIBLE case.

### C1 judgment

The four wire scalars now BREAKING, and they name the pointer (`/max_tokens`, `/stream`, `/temperature`, `/model`). Tagged `<cwd>`, `<current_date>`, and `Today's date is` stay EXACT because `/system` is in `static_nodes` and its digest is the masked string. I checked that, not just the outcome.

The first fingerprint used `normalize_request(..., cross_launch=True)`. That projection dropped extras and stripped `cache_control` stamps. C1 bound only to `mask_cross_launch_body`. The masked raw tree keeps every other raw pointer.

That is the third way. Session-varying children (`session_id`, `prompt_cache_key`, `turn_id`) disagree across A1/B/A2 and stay out. Launch-stable leftovers stay in.

Proven:

- Codex `client_metadata.x-codex-installation-id` change → `breaking-drift` at that pointer. Same install, new session ids → EXACT. Real first-turn body: `api/tests/fixtures/codex_http_fallback/turn-0/transport.json:496-502`. The IR extras drop already excludes this object (`wire_normalization.py:207-211`). `test_wire_normalization` pins the drop.
- Codex `<root>` inside `workspace_roots` is not masked. `<cwd>` and `<current_date>` on the same string are. Date plus directory change → `breaking-drift` at `/instructions`. The C1 date/cwd test never feeds this shape.
- `cache_control` moved from `system[0]` to `system[1]`, both 3/3 → BREAKING at the system pointers. IR hashing strips that stamp. First-turn breakpoints may be stable. The hole is still there.

Claude `metadata.user_id` embeds `session_id`, so it differs per probe and does not enter membership.

C1 red/green: the scalar test is honest. Date/cwd on the red commit was EXACT because `_probe` defaulted `normalized_request` to `{messages: [prompt]}` and the helper rewrite stopped passing a real projection. Green is real. I proved `/system` membership and the masked digest at HEAD.

### New findings

### 3. Major. Masked raw fingerprint keeps launch-identity extras the IR drop already excluded

- Location: `api/src/transport_matters/baseline_evidence.py:232-241`
- Observation: `classify_aba` does `json.loads` → `mask_cross_launch_body` → `observe_request_json`. It never removes `client_metadata`, `previous_response_id`, or `prompt_cache_key`. Those keys stay in `static_nodes` when they agree on two probes.
- Impact: Re-harvest of the same Codex cell after a reinstall, or on another machine or CI agent, exits 1 as `breaking-drift` at `/client_metadata/x-codex-installation-id` with no request-shape change. `current` does not move.
- Basis: Independent `uv run python` against the live comparator. Fixture body cited above. The repo's own cross-launch test says those extras must not affect equality.
- Caveat: Same laptop, same Codex install compares clean. Per-probe session fields do not pollute. Fix is the existing extras set, not a new mask. Codex `<root>` and moving `cache_control` are the same class and still open; `<root>` needs a mask the C1 brief forbade.
- Link: https://github.com/littleorgans/transport-matters/blob/9d8dcd16e024648a9d69bc1a800cee8fa8f3c5ec/api/src/transport_matters/baseline_evidence.py#L232-L241

### 4. Major. C2 ranking turns a nested B-flicker into parent BREAKING

- Location: `api/src/transport_matters/baseline_evidence.py:351-362`
- Observation: `decided_static_changes = static_changes - unresolved_presence` matches pointers exactly. A child that is STABLE+sometimes is unresolved. Its parent drops out of candidate `static_nodes` because the subtree hash changed, stays `presence=always`, and is not subtracted. C2 returns BREAKING at the parent first. At `0192c746` unresolved presence ran first, so the child refusal won.
- Impact: `cache_control` present on a tool in A1 and A2 and missing in B reports `breaking-drift` at `/tools, /tools/0` with `unresolved=()`. D3 said that flicker is INSUFFICIENT. The top-level B-flicker test stays green because `/` is not static (the prompt varies).
- Basis: Independent `uv run python`. Candidate `static_nodes` kept `/tools/0/cache_control` and dropped `/tools`. Reason string was `changed at /tools, /tools/0`.
- Caveat: Fail-safe (no promote). First-turn `cache_control` may be 3/3 in practice. The ranking bug is not limited to that key.
- Link: https://github.com/littleorgans/transport-matters/blob/9d8dcd16e024648a9d69bc1a800cee8fa8f3c5ec/api/src/transport_matters/baseline_evidence.py#L351-L362

### Not scored

C3 store and CLI share `promotes_baseline`. Bootstrap exits 0. C4 persists and prints presence refusals with pointer and 2/3 vs 3/3. C5 and C6 hold, as above.

`BaselineBundle` grew required `static_nodes` and `reference_unresolved_pointers` on schema v2. An `0192c746` v2 file now fails pydantic, not `regenerate the baseline`. No live harvest landed on that SHA. I am not scoring a version bump.

`normalized_request` is still written and never read by compare. `compare_baseline_bundles` is 137 lines.

### Correction counts

Blocker 0, Major 2, Minor 0. Own findings 0 open.

## Final sign-off round at `10165c99`

Worktree empty. `9d8dcd16` and `5591db86` are still ancestors. I did not rerun `just check` / `just test`. Proofs used `cd api && uv run python`. Focused pytest on the new evidence, harvest, and wire tests: 29 passed.

`conditional: I sign off conditional on the following changes:`

1. A STABLE+sometimes descendant under a flickering object must remain INSUFFICIENT. `cache_control` missing from probe B, with `type` `ephemeral` on the reference and `5m` on A1+A2, must not report `breaking-drift` at `/tools/0/cache_control/type`.

### Own findings

1. Resolved. `classify_aba` pops `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` after `mask_cross_launch_body` (`baseline_evidence.py:246-247`). `normalize_request` filters the same tuple (`wire_normalization.py:44-48`, `:209`). Install id, `previous_response_id`, and `prompt_cache_key` value changes are each EXACT. `service_tier` `auto` to `priority` is BREAKING at `/service_tier`.
2. Resolved for the equal value case the E1 tests lock. Same `cache_control` object missing from B is INSUFFICIENT at `/tools/0/cache_control`. That flicker plus a 3/3 description change is BREAKING at `/tools/0/description`. A body with eleven tools, flicker at `/tools/10`, and a description change at `/tools/1` stays BREAKING at `/tools/1/description`. Finding 5 is the remaining E1 hole.

### E1 judgment

Equal value flicker is INSUFFICIENT at the leaf. A real sibling change still BREAKING. Adding a second tool 3/3 while tool 0 flickers is BREAKING at `/tools/1/name` and `/tools/1/description`. Both directions the brief asked for are proven.

The new tests feed `{type: ephemeral}` on both bundles. Child digests match, so `/tools/0/cache_control/type` never enters `static_changes`. That is why they stay green for finding 5.

`f"{ancestor}/"` does not treat `/tools/1` as a parent of `/tools/10`. I checked that before dropping it.

### E2 judgment

Per launch identifiers stay EXACT. A real extras field stays BREAKING. The constant sits beside `STRIPPED_REQUEST_EXTRAS_KEYS` and both call sites use it. `mask_cross_launch_body` returns a deepcopy, so the pop does not mutate the raw probe.

A new 3/3 child under `client_metadata` compares COMPATIBLE. The extras object going 3/3 to 0/3 is BREAKING removal. Both follow the specified fingerprint only pop plus the settled schema axis. I am not scoring them.

### E4

The deleted arm was `fingerprint !=` and `not static_changes`, reason `stable baseline fingerprint changed`. `classify_aba` writes both fields from one `canonical_digest` of sorted pointers. Harvest passes those two fields together. The new validator rejects construct and `read_baseline_bundle` of a disagreeing pair. That arm is unreachable for any legal harvest bundle, not merely hard to reach.

`model_copy(update={"static_fingerprint": ...})` still skips the validator. Compare then returns INSUFFICIENT. Harvest only `model_copy`s `reference_*` fields. Permuted `static_nodes` with a matching digest is a valid pair that now falls through to INSUFFICIENT; harvest never emits that order.

The old compare test is gone. The load reject is the remaining lock. Reintroducing the compare arm behind the validator would keep that test green.

### New findings

### 5. Major. E1 leaf collapse lets a descendant of a flicker BREAKING

- Location: `api/src/transport_matters/baseline_evidence.py:359-380`
- Observation: Unresolved presence keeps the shallowest STABLE+sometimes pointer and drops descendants. `decided_static_changes` then drops a static pointer only when it equals that leaf or is an ancestor of it. A child with a different 2/3 digest stays decided.
- Impact: Reference has `cache_control.type=ephemeral` on all three probes. Candidate has `type=5m` on A1+A2 and omits the object on B. Harvest exits 1 as `breaking-drift` at `/tools/0/cache_control/type` with `unresolved=()`. D3 says constant when present and absent at least once is INSUFFICIENT. A new `ttl` child on A1+A2 of that same flicker is also BREAKING at `/tools/0/cache_control/ttl`.
- Basis: Independent `uv run python` against the live comparator. Candidate evidence is STABLE+sometimes on both `/tools/0/cache_control` and `/tools/0/cache_control/type`. The leaf filter keeps only the object. `static_changes` still holds the type digest. `decided` is `{/tools/0/cache_control/type}`.
- Caveat: Does not promote. Equal value flicker, the case the new tests lock, stays INSUFFICIENT. At `9d8dcd16` this fixture was already BREAKING, at the parent containers. E1 moved the name to the child and still did not refuse.
- Link: https://github.com/littleorgans/transport-matters/blob/10165c99844c679316f3b819d0b138c184264c94/api/src/transport_matters/baseline_evidence.py#L358-L381

### Not scored

E3 prints `reason=` when the bundle does not promote and has no unresolved pointers. I ran `test_main_explains_breaking_reason`. The red assertion lived in `4290131a`; the print landed in `8f0c8e70`.

E5 builds real `BaselineBundle` values through `model_validate`. The `_HarvestedBundle(str)` double is gone. Replacing the double by itself would have stayed green on the parent.

`_presence_refusal` is an extract of the existing refusal block. `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` is the authorized promotion. Files stay under 700. `compare_baseline_bundles` is 131 lines.

No live `baseline_harvest --harness claude` run. The owner credential is unavailable. This sign-off is the code as filed.

### Final counts

Blocker 0, Major 1, Minor 0. Own findings 0 open.
