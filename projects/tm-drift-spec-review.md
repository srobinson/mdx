---
title: Architecture review of the baseline drift comparator replacement
type: projects
tags: [transport-matters, baseline-capture, comparator, architecture-review]
summary: The seven historical failures are unrepresentable, but the proposed structural gate retains a promotion hole based on presence and misses Codex input item drift
status: active
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

# Architecture review of the baseline drift comparator replacement

Reviewed `/Users/alphab/.mdx/projects/tm-drift-spec.md` against branch `fix/comparator-truth` at `e894fadee134293cd9b504d84703af74f735020f`.

Verdict: conditional. I found 1 Blocker, 3 Major issues, and 2 Minor issues. All seven historical instances are unrepresentable under the intended replacement contracts. The acceptance argument still fails at the class level because `stable shape` decides whether observed unmodelled structure reaches the only gating comparison.

The repository was pristine before the review, after the focused probes, and before this file was written. I made no repository changes.

## Findings

### 1. Blocker: the structural gate still drops evidence by presence classification

Spec contract: `/Users/alphab/.mdx/projects/tm-drift-spec.md::compare_structure` and `::unmodelled_shape`.

`stable shape` includes an overflow entry only when `present_in` contains all three labels. `compare_structure` reads only that filtered set. This directly contradicts the invariant that no verdict reads a presence count. Presence classification still decides whether a pointer's kind is compared at all.

Consider a provider field `/tools/*/provider_data/new_mode` that is absent from the reference and present in candidate A1 and A2. The same prompt produced the field twice, so this is demonstrated prompt dependent structure rather than a one launch flicker. Candidate B lacks it. The candidate entry has `present_in=(A1, A2)`, never enters `stable shape`, and `compare_structure` returns EXACT. `baseline_store::promotes_baseline` then promotes the candidate. Check 2 reports the leaf but cannot prevent promotion by design.

The same failure occurs for a field present only in B. A provider can add unmodelled structure for one request shape while the structural check says TM still sees the whole request. This recreates the seven round defect class inside the new gate: a classification decides whether evidence reaches comparison.

The acceptance sweep in P2b would encode this bug. It asserts structure EXACT for every 3, 2, 1, or 0 presence cell. The structural property must instead cover observed provider additions by label or by the union of labels. Volatile TM stamps already leave the projection through `session/wire_normalization.py::normalize_request`, `_strip_stamps`, and `_mask_cross_launch_text`. Provider structure does not need the same presence filter.

### 2. Major: the Codex catch all is incomplete in the proposed universe

Source: `api/src/transport_matters/codex/request_parser.py::_parse_input`, `::_parse_message_item`, `::unknown_request_item_fields`; `api/src/transport_matters/session/wire_normalization.py::normalize_request`.

Unknown fields on a known Codex input item do not survive in the item IR. `_parse_message_item` sets `keep_raw`; `_parse_input` stores the full item only in `InternalRequest.provider_extras["input_item_raw"]` and stamps the projected message with `tm_wire_index`. `normalize_request` strips both `input_item_raw` and `input_item_raw_stamped`. The proposed `masked_request` therefore contains neither the unknown key nor its shape.

Focused proof at the named head:

```text
wire: input[message].new_envelope={"x":1}
InternalRequest.provider_extras: input_item_raw contains new_envelope
Message.provider_data: {"tm_wire_index": 0}
normalize_request(..., cross_launch=True).request_extras: no input_item_raw
normalized message body: no new_envelope
```

A stable three probe addition at this level is invisible to both checks and promotes as EXACT. The claim that `provider_data`, `provider_metadata`, `provider_extras`, and `UnknownBlock.raw` form a complete catch all is therefore false for Codex.

The repository already owns the missing detector. `codex/request_parser.py::unknown_request_item_fields` scans the exact captured bytes and reports unknown keys, unknown item types, items that are not objects, and coerced tag kinds. Its docstring names this exact ownership gap. The redesign must reuse that capability or change normalization so each nonduplicated raw field enters the shared universe. Adding a second hand written item vocabulary would violate the repository's reuse rule.

### 3. Major: persisted analysis has no stated source of truth contract

Source: `api/src/transport_matters/baseline_evidence.py::ProbeEvidence.validate_raw_evidence` and `::BaselineBundle.validate_probe_contract`.

The spec correctly requires `ProbeEvidence.request_ir` to reparse from `raw_request_base64`. It then persists `BaselineBundle.unmodelled_shape` and `BaselineBundle.runtime`, but never requires those fields to match the reparsed probes. It also says that `validate_probe_contract` drops the current fingerprint recomputation.

The spec says the projection is derived at compare time, while its data shapes and P2a phase store the derived analysis on the bundle. It does not say whether `compare_structure` and `compare_content` recompute and ignore the stored fields, or trust them. Either interpretation leaves an integrity problem:

- If comparison trusts the fields, a stale or malformed `unmodelled_shape` can turn DEGRADED into EXACT, and an arbitrary `runtime` pointer can suppress content.
- If comparison recomputes, the persisted report can disagree with the decision unless bundle validation rejects the mismatch.

This artifact controls automatic promotion. The design must name one authority. The simplest contract is to derive both analyses from `ProbeEvidence.request_ir` during validation or comparison, then either omit the redundant stored fields or validate exact equality before any verdict reads them.

### 4. Major: BREAKING does not cover the full parse failure seam

Source: `api/src/transport_matters/request_pipeline.py::parse_request_ir`, `api/src/transport_matters/addon_handlers.py::handle_http_request`, `api/src/transport_matters/exchange_recorder/unparsed.py::unparsed_request_ir`, `api/src/transport_matters/baseline_capture.py::_wait_for_correlated_exchange`, `::_json_contains_text`, and `::_build_probe_evidence`.

The source path matches the spec for valid JSON that the adapter rejects. `parse_request_ir` catches every adapter exception; `handle_http_request` persists `unparsed_request_ir`; the sentinel is `provider_extras.type == "transport.parse_failure"`.

P3 only correlates a parse failure by decoding the raw body and searching its JSON values for the delivery id. `_build_probe_evidence` also calls the strict JSON walker. A JSON decode failure reaches the persisted parse failure seam but cannot pass either operation. Focused proof:

```text
AnthropicAdapter.inbound_request(b"{not-json") -> JSONDecodeError
observe_request_json(b"{not-json") -> ValueError
```

That candidate still ends as a correlation timeout with no bundle, no `StructureCheck`, and no BREAKING reason. The stated meaning, "TM can no longer parse it," includes this trigger because `parse_request_ir` catches it. The design must either narrow the BREAKING contract to valid JSON adapter failures or add byte level delivery correlation and a probe shape that can carry raw evidence that is not JSON.

### 5. Minor: `harness_version` drift has no content path

Source: `api/src/transport_matters/baseline_evidence.py::BaselineCell`.

Section 8 says `harness_version` differences are content. `masked_request` contains request IR sections only, and `ContentDiff.changed` contains JSON pointers grouped under request sections. `harness_version` lives in `BaselineCell`; no specified pointer or report field carries its difference.

A harness upgrade that emits identical request IR produces empty content even though the candidate records a new version. Add an explicit comparison fact for cell metadata, or remove the claim that Check 2 reports it. `wire_model` does not share this problem because `masked_request.model` carries it.

### 6. Minor: P2a does not prove file size compliance

Source: `api/src/transport_matters/baseline_evidence.py::compare_baseline_bundles` and the P2a and P2b phases in the spec.

`baseline_evidence.py` is 618 lines and `compare_baseline_bundles` is 149 lines at the named head. P2a adds `masked_request`, `runtime_fields`, overflow analysis, new data shapes, and `compare_content` while retaining the old comparator. P2b performs the deletion later. The project limit leaves 82 lines of headroom, and the spec does not name another owner module for the P2a additions.

The delivery plan must combine the P2a addition with the P2b deletion in one verified phase, or assign the new checks to a named module that stays under 700 lines. Leaving placement to implementation risks an intermediate commit that violates a hard repository rule.

## Seven case acceptance check

All seven historical instances are unrepresentable under the intended contracts:

1. Date and cwd changes under `/system` pass through one masked projection. Values cannot affect `StructureCheck`.
2. `cache_control` leaves the body through `wire_normalization.py::_strip_stamps`. The old `/tools` fingerprint path is deleted.
3. `previous_response_id`, `client_metadata`, and `prompt_cache_key` leave the projection once through `normalize_request`. No raw comparison axis survives.
4. A 3 of 3 to 1 of 3 modeled field change reaches label matched content and has no presence verdict.
5. A 1 of 3 to 1 of 3 value change is read by the matching label and reported. Promotion is now the declared content policy.
6. Maskable Run ID, cwd, and date changes have no raw digest path. The masked leaves compare equal.
7. Prompt wrapper prose compares by label. `prompt_derived` is recorded and has no exclusion role.

This conclusion is limited to the seven exact instances. Finding 1 shows that their common failure class remains representable for unmodelled structure.

## Other requested judgments

The adapter blind spot belongs in adapter work under the owner's fixed semantics. A missing nondefault `max_tokens` or `stream` value becomes a content change and reports before promotion. A renamed field also lands in top level extras and should become DEGRADED once the structural gate is corrected. The operator loses the previous warning after promotion, but content never gating is an owner decision. The comparator should not create a raw wire exception solely for these defaults.

The deletion plan is real and sufficient for the old inference engine. Repository search shows `EvidenceKind`, `PointerEvidence`, `AbaAnalysis`, `classify_aba`, `repeat_a_outcome`, `DriftOutcome.INSUFFICIENT`, and the old reference fields confined to the named comparator, capture, store, CLI, and tests. The spec removes or reshapes each caller. The replacement property tests should survive; tests for obsolete classification outcomes should go.

Reuse is mostly sound. `normalize_request`, `observe_request_json`, `JsonNodeObservation`, `_json_contains_text`, adapter lookup, and the unparsed sentinel seam all have clear owners. Finding 2 is the exception: `unknown_request_item_fields` already owns Codex item level drift and the spec overlooks it.

The focused historical probes reproduced the named current outcomes at `e894fade`. Two older scratch scripts also exposed their known staleness: `probe_class.py` cannot rebuild the copied `10165c99` Pydantic model, and `probe_delta.py` calls an earlier helper signature. Neither error affects the source and contract findings above.

## Revision 2 delta review

Reviewed revision 2 at the same branch head. Verdict: conditional, with 1 Blocker and 1 Major issue. The seven original instances remain unrepresentable. The revision removes every probe count and presence ratio from the verdict. Two new adversarial instances remain.

### 7. Blocker: the raw scanner bypasses the cross launch projection

Source: `api/src/transport_matters/session/wire_normalization.py::normalize_request`, `api/src/transport_matters/adapters/anthropic.py::unknown_request_fields`, and `api/src/transport_matters/drift_capture.py::detect_unknown_shapes`.

The candidate union fixes the original presence filter. A genuine `new_provider_field` observed in 1, 2, or 3 candidate probes survives in `/extras` and in the scanner findings. Each case produces a gained pair or finding and therefore DEGRADED. A tool `cache_control` stamp observed in 1, 2, or 3 probes leaves through `_strip_stamps` and produces no scanner finding. A masked Run ID also produces no overflow or scanner finding.

The cross launch direction still fails. `normalize_request` removes `previous_response_id` through `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. The Anthropic half of `detect_unknown_shapes` then calls `unknown_request_fields` on the unnormalised IR and reports `previous_response_id`. A reference without the key and a candidate with the key in 1, 2, or 3 probes therefore has:

```text
normalized candidate extras union: ()
reference findings union: ()
candidate findings union: (previous_response_id,)
gained_findings: (previous_response_id,)
result under compare_structure: DEGRADED
```

This field is explicitly outside the cross launch projection, so DEGRADED is a false gate. The byte scanner has recreated a second structural universe after the spec says `normalize_request` is the only removal owner.

The clean correction is to let masked overflow nodes own envelope structure and use exact bytes only for the Codex item gap. Reusing `detect_unknown_shapes` whole duplicates envelope detection and bypasses the mask. If the whole composition must remain, `wire_findings` must remove envelope findings that `normalize_request` removed through the shared constants. The P2 sweep must build raw `ProbeEvidence` and call the production `compare_structure`; otherwise its cross launch assertion can skip this path.

### 8. Major: Codex unknown item values remain invisible to content

Source: `api/src/transport_matters/codex/request_parser.py::parse_codex_request`, `::unknown_request_item_fields`, `api/src/transport_matters/session/wire_normalization.py::normalize_request`, and `api/src/transport_matters/drift_capture.py::detect_unknown_shapes`.

Revision 2 closes the structural addition gap for an unknown key on a known Codex item. It does not expose that key's value to Check 2. A source-real pair with `input[message].new_envelope.x` changing from `1` to `2` produced:

```text
raw bytes equal: false
masked projections equal: true
reference findings: (input[message].new_envelope,)
candidate findings: (input[message].new_envelope,)
findings equal: true
```

The raw item lives only in `provider_extras.input_item_raw`, which `normalize_request` removes. `unknown_request_item_fields` returns the field name without its value. When a bootstrap reference already contains the unknown key, a later value change has no gained shape, no gained finding, and no content pointer. The comparison reports no change and promotes.

Check 2 needs a value observation for Codex item fields that exist only in preserved raw input, with the same masking rules as the main projection. The narrower alternative is to state that values inside unknown Codex item fields are outside the content contract. That alternative would contradict the current claim that Check 2 reports what the harness changed. Add a P2 cell where the unknown key exists in both bundles and its leaf value changes.

### Revision 2 sweep judgment

The new 1, 2, and 3 probe expectations encode the correct structural answers for a genuine overflow gain. They also encode the correct answers for stamps and masked values. The cross launch expectation conflicts with the current `detect_unknown_shapes` composition, as finding 7 proves. The sweep also omits the already present unknown item value case in finding 8. Both cases must use raw bytes and the production comparison path.

### Closure of the other findings

- C2 is closed for structural additions by `drift_capture.py::detect_unknown_shapes`, which reuses `codex/request_parser.py::unknown_request_item_fields`. Its value path remains open as finding 8.
- C3 is closed. `/Users/alphab/.mdx/projects/tm-drift-spec.md::ProbeEvidence` makes raw bytes and reparsed IR authoritative, while `::ProbeAnalysis` stays compute time only.
- C4 is closed at the specification level. `/Users/alphab/.mdx/projects/tm-drift-spec.md::P3` adds raw prompt byte correlation and permits `inventory=None`; `baseline_capture.py::_transcript_has_reply` accepts an assistant API error record as a reply.
- C5 is closed by `/Users/alphab/.mdx/projects/tm-drift-spec.md::ContentDiff.cell`, which gives `BaselineCell.harness_version` an explicit report path.
- C6 is closed by the merged P2 phase. It deletes the inference engine and adds both checks in one verified commit, with a stated target near 430 lines.

Presence conclusion: no verdict reads `JsonNodeObservation.present_in`, a probe count, or a presence ratio. Structural set membership still gates, as intended for genuine provider additions. Finding 7 shows that a stripped field can enter that set through the byte scanner.
