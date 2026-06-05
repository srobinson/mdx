---
title: Baseline drift comparator replacement
type: projects
tags: [transport-matters, baseline-capture, comparator, spec]
summary: Two independent checks (structure gates, content reports) over exactly one projection of the request; the A/B/A triple only identifies runtime fields; revision 3 after architect review (C1 to C6, D1 to D2)
status: superseded
project: transport-matters
confidence: high
created: 2026-08-18
updated: 2026-08-19
superseded_by: github issue 382
---

> **SUPERSEDED 2026-08-19. Do not implement this spec.**
>
> This design derives the comparison from `ir::InternalRequest`. The owner's decision is that
> baseline drift compares **raw wire schemas per harness**, and that the IR is internal and is
> not diffed. Mapping raw request to IR is a separate concern, tracked by GitHub issue #392.
>
> This spec was implemented in full on `fix/comparator-truth` (P0 to P3, gates green, 3915
> tests) and then scrapped. Independent reviews returned 2 Blockers, 5 Majors, 4 Minors; four
> of them are one defect, TM's own IR bookkeeping (`provider_data`, `tm_wire_index`,
> `input_item_raw`, `keep_raw`) leaking into a gate that is supposed to be about what the
> harness sent. None of those keys exist on the wire.
>
> The implementation is parked on branch `scrap/ir-projection-comparator`.
> Findings: `tm-drift-build-review-grok.md`.
> Corrected requirements: GitHub issues #382 (bare HOME, the gating schema) and #383
> (default HOME, education). Salvageable: `runtime_fields` (A1 vs A2), parse-failure is
> BREAKING, raw bytes plus digest evidence. Do not recover `masked_request`,
> `unmodelled_shape`, `UNMODELLED_POINTER_ROOTS`, `_collapse`, or the P3 correlation fallback.

# Baseline drift comparator replacement

Branch `fix/comparator-truth` at `e894fade`. Read-only survey; every claim about adapter and normalizer behaviour below was executed through `cd api && uv run python` (3.14) against the branch head, or is cited to the symbol that proves it. Scope: `baseline_evidence.py`, the comparator seams in `baseline_capture.py`, `baseline_store.py`, `baseline_harvest.py`, and their tests. Everything else on the branch (consumer wiring, artifact versioning, canonicalization, delivery-id correlation, transcript adapter, session-store preflight, socket bounds) is untouched.

Revision 2 answered the architect review at `tm-drift-spec-review.md`: C1 (presence filter inside the structural gate) in §3.2 and §9 P2; C2 (Codex item-level catch-all gap) in §3.1 and §3.2; C3 (source of truth for persisted analysis) in §6; C4 (BREAKING misses non-JSON bytes) in §3.1 and §9 P3; C5 (`harness_version`) in §4; C6 (file size in P2a) in §9. Owner decisions now fixed: DEGRADED does not promote and exits 1; the adapter default-substitution blind spot stays out of scope.

Revision 3 answers findings 7 and 8. D1 (the byte scanner recreated a second structural universe): the scanner is gone; §1 states the stronger invariant and §2 defines the one projection; the Codex item gap is closed inside that projection by carrying the IR's own item-level catch-all, `provider_extras.input_item_raw`, instead of reading bytes (§2, §3.1 correction 3, §3.2). Choice and reason: of the two directions offered (masked overflow nodes own the envelope and exact bytes serve only the Codex item gap, or keep the whole scanner and subtract the shared strip constants from its findings) neither is taken, because both leave two representations of one request alive, and D2 needs the item values in the projection anyway, at which point a name-only byte scan is redundant. D2 (unknown Codex item values invisible to content): the same reattachment gives Check 2 the values under the same masks (§2, §4). §9 P2 now requires the sweep to start from wire bytes and call the production comparison. One deliberate loss is named in §3.1: a non-string Codex tag value that `_parse_message_item` defaults past is no longer reported; it is the adapter default-substitution class the owner excluded.

## 1. The invariant

The current comparator answers one question ("does this change matter") by inferring, from three probes, which values are volatile. Seven instances share one shape: a classification decides whether a value is compared, each classification owns a comparison path, and closing one path leaves the others armed.

Every instance chased on this branch reduces to the same disease: two representations of the request existed, an exclusion was applied to one, and the other stayed armed (the fingerprint against `raw_nodes`; raw digests against masked `static_nodes`; in revision 2, the normalized projection against the byte scanner). The replacement holds one invariant, and it is stronger than "presence appears in no verdict":

**Exactly one projection of the request exists, `masked_request(request_ir)`, and every verdict reads only it.**

Nothing else about a probe is readable by a check: not the raw bytes, not the unnormalized IR, not a probe count, not `present_in`. Two checks, never merged; the table shows what each reads and that nothing else exists to read.

| Check | Question | Reads, and reads only | Gates | Promotes |
|---|---|---|---|---|
| Structure | can TM still see the whole request | the (pointer, kind) pairs of the projection under the overflow roots, unioned over the candidate's probes; and, for a probe that has no projection because parsing failed, that fact (`is_unparsed_request(request_ir)`) | yes | only when EXACT |
| Content | what did the harness change | the leaf digests of the projection, label matched, minus the runtime set; and `BaselineCell` metadata, which is not part of the request | never | always |
| Runtime set (an input to content, not a verdict) | which leaves are launch-generated | the leaf digests of the projection for `A1` and `A2` | never | n/a |

The A/B/A triple keeps one job: name the pointers whose values differ between two launches of an identical setup.

## 2. The one projection: `masked_request`

There is no byte-level reader in the comparator. Raw bytes exist in a bundle for one purpose, to re-parse and validate `request_ir` on load (§6); after that no check touches them.

`masked_request(ir: InternalRequest) -> dict` assembles, per probe:

- `system`, `tools`, `messages`: the component bodies of `session/wire_normalization::normalize_request(ir, cross_launch=True)`. Stamps (`PROVIDER_DATA_STAMP_KEYS`) are already split into `position_meta` by `_strip_stamps` at the message, content-block, system-part and tool-def levels; launch prose is already masked by `_CROSS_LAUNCH_MASKS` inside `_component`; `cache_hint` is already nulled.
- `extras`: `mask_cross_launch_body(NormalizedWireRequest.request_extras | {"input_item_raw": ir.provider_extras["input_item_raw"]})`, the key included only when the IR carries it. `request_extras` already lacks `STRIPPED_REQUEST_EXTRAS_KEYS` and `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. The one key reattached is `input_item_raw`; the reason and the rule are next.
- `model`, `sampling`, `stream`, `metadata`: the IR dump verbatim. No harness prose lives here; session identity inside `metadata` is handled by the runtime set (§5).

Nodes come from the existing walker: `request_inventory::observe_request_json(canonical_json(masked).encode())` yields `(pointer, kind, sha256)` for every node. Pointers therefore read `/system/0/text`, `/tools/3/input_schema/properties/x/type`, `/extras/thinking/budget_tokens`, `/extras/input_item_raw/0/raw/phase`, `/metadata/provider_metadata/user_id`.

**Why `input_item_raw` is in the projection.** `codex/request_parser::_parse_input` writes a `{"index", "raw"}` entry to `provider_extras.input_item_raw` for exactly the input items it cannot round-trip from modelled fields: a `message` item with any key beyond `type`, `role`, `content` (`_parse_message_item`), or whose content holds a part with extra keys, a non-object part or an unknown part type (`_parse_content`); a `function_call` with any key beyond `type`, `call_id`, `name`, `arguments`; a tool output item per `_should_preserve_tool_output_raw`; a non-object item; an unknown item type. That list is the IR's item-level catch-all, the same role `provider_data` plays at the block level, and it is the only place an unknown key on a known Codex item survives (`reasoning` extras go to `ThinkingBlock.provider_data` instead and need nothing). `normalize_request` strips it under `STRIPPED_REQUEST_EXTRAS_KEYS` for a stated storage reason (the module docstring: it duplicates the request at 96 to 98 KB per turn and tier-1 raw remains the byte-fidelity source), which is a decision about the wire store, not about comparison semantics; the comparator has no tier-1 raw universe by the invariant, so its projection carries the catch-all. The rule that keeps this from becoming a second removal owner: the projection reattaches nothing TM generated. `input_item_raw_stamped` (a parser marker) stays out with the `tm_wire_index` and `cache_control` stamps; every key under `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` stays out; the reattached entries pass through `mask_cross_launch_body`, the same function `_component` applies to every message, system part and tool def, so a preserved item's prose is masked exactly as its modelled twin under `/messages`. A pinned test builds a Codex IR carrying every `PROVIDER_DATA_STAMP_KEYS` stamp, every cross-launch key and `input_item_raw_stamped`, and asserts that no pointer of `masked_request` names any of them.

Executed at the branch head: a Codex body carrying `previous_response_id` and two `message` items, one with `new_envelope: {"x": 1}`, parses to `request_extras == {}` under `cross_launch=True`, `provider_extras.input_item_raw == [{"index": 0, "raw": <that item>}]` with the plain item not preserved, `Message.provider_data == {"tm_wire_index": 0}` on the preserved item's projection, and `mask_cross_launch_body` over the entries rewrites the Run ID line inside the preserved item to `<run-id>`.

Consequences: an Anthropic request never has the key, so its projection is unchanged; a Codex value that lives in a preserved item is visible twice, at its modelled pointer under `/messages` and at its raw pointer under `/extras/input_item_raw`, which is report duplication and nothing else (both are leaves of the one projection and content never gates). `mask_cross_launch_body` keeps its public name with two callers, `_component` and `masked_request`; `baseline_evidence` stops importing `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. `drift_capture::detect_unknown_shapes`, `adapters/anthropic::unknown_request_fields` and `codex/request_parser::unknown_request_item_fields` are not reused: they read the unnormalized IR and the exact bytes, which is a second representation, and everything they name structurally is already a (pointer, kind) pair of the projection (envelope keys under `/extras/<key>`, item keys under `/extras/input_item_raw/*/raw/<key>`, unknown item and part types under `/messages/*/content/*/raw` and the raw entry). What they name and the projection cannot is one class, stated in §3.1.

## 3. Check 1: structure

### 3.1 The `InternalRequest` hypothesis, tested

Claim: `ir::InternalRequest` is TM's dependency set, `provider_extras` is the catch-all, so BREAKING is a failed population of a modelled field and DEGRADED is a landing in `provider_extras`.

Executed against `adapters/anthropic::AnthropicAdapter.inbound_request`:

| Wire change | IR result | Verdict on the claim |
|---|---|---|
| unknown key on a system part, tool, message, content block | `SystemPart.provider_data`, `ToolDef.provider_data`, `Message.provider_data`, `TextBlock.provider_data` each carry it | catch-all exists at every level; the name is `provider_data`, only the top level is `provider_extras` |
| unknown content block type | `UnknownBlock.raw` holds the block verbatim | catch-all |
| unknown key inside `metadata` | `RequestMetadata.provider_metadata` holds the whole raw dict | catch-all |
| `system` removed or renamed | `system=[]`; the renamed key lands in `provider_extras` | no failure; a rename is DEGRADED, the loss is content |
| `max_tokens` removed | `sampling.max_tokens=0` | silent default, no failure, no overflow |
| `max_tokens` renamed | `max_tokens=0` plus `provider_extras.max_output_tokens` | DEGRADED by the overflow half only |
| `max_tokens: "100"` | coerced to `100` | silent coercion |
| `model` removed | `anthropic/unknown` | silent default |
| `messages` removed or empty | `ValidationError` (`min_length=1`) | parse failure |
| `messages` or `tools` not a list of objects | `AttributeError` in the parser | parse failure |
| `max_tokens: "abc"` | `ValidationError` | parse failure |
| body is not JSON | `JSONDecodeError` | parse failure (see correction 2) |

`codex/request_parser::parse_codex_request`, by symbol:

| Wire change | IR result | Verdict on the claim |
|---|---|---|
| unknown envelope key | `provider_extras` | catch-all |
| unknown key on a `reasoning` item | `ThinkingBlock.provider_data` (`_parse_reasoning_item`) | catch-all |
| unknown item type, non-object item | `UnknownBlock.raw` (`_parse_input`) | catch-all |
| unknown key on a `message`, `function_call`, `function_call_output`, `tool_search_output` or `custom_tool_call*` item | `keep_raw` only: the whole item goes to `provider_extras.input_item_raw`, the projected `Message.provider_data` carries only the `tm_wire_index` stamp (`_parse_message_item`, `_parse_function_call`, `_should_preserve_tool_output_raw`) | catch-all, at the envelope: `input_item_raw` is the item-level overflow, and §2 carries it in the projection |
| non-string value in a tag position (`role: null`, `type: [..]`) | `json_tags::sanitize_tag_fields` reports it, keeps a null as `None` and rewrites an unhashable to `coerced_tag_marker`, then `parse_codex_request` discards the findings; what remains depends on the route: a marker in a content part type reaches `UnknownBlock.raw` and preserved raw (`_parse_content`), a null or marker on a role-bearing item is defaulted past by `_parse_message_item` with no `keep_raw` | visible where the route changes; silent default where `_parse_message_item` absorbs it (adapter class, out of scope, below) |

**Verdict: the hypothesis holds structurally and needs three corrections.**

1. The catch-all is present at every level, under four names. The unmodelled region of the IR is the union of `InternalRequest.provider_extras`, every `provider_data`, `RequestMetadata.provider_metadata`, and `UnknownBlock.raw`. These are the fields `ir.py` itself annotates as catch-alls; there is no hand-curated dependency list.
2. "Population of a modelled field fails" is almost never observable, because `AnthropicAdapter` substitutes defaults instead of failing (`model`, `max_tokens`, `stream`, `SystemPart.text`, `ToolDef.name`, `Message.role`, and pydantic coercion). BREAKING is therefore exactly the parse-failure seam that already exists: `request_pipeline::parse_request_ir` catches every exception from `adapter.inbound_request` over the decoded body, including `JSONDecodeError` for bytes that are not JSON, and `addon_handlers::handle_http_request` then persists `exchange_recorder/unparsed::unparsed_request_ir` (synthetic IR, `provider_extras.type == "transport.parse_failure"`, raw bytes preserved, no response IR ever written for that exchange). Modelled-field losses that the adapter absorbs (system emptied, `max_tokens` zeroed) are values, and Check 2 reports them.
3. The IR catch-all is complete for Anthropic (executed) and, for Codex, complete at the envelope, the `reasoning` item, unknown item types, and, through `input_item_raw`, unknown keys on known item types and unknown content parts. `input_item_raw` is stripped by `normalize_request` for storage size, so the projection reattaches it (§2). The completeness claim of Check 1 is therefore: the IR catch-alls, all of them projected, and nothing else is claimed. Revision 2 reused `unknown_request_item_fields` over the exact bytes for this level; revision 3 does not, because the projection now holds the same shape and the values with it, and a byte reader is a second representation by definition (D1).

The residual blind spot is honest and named, and it has one more member than before: a removal of `max_tokens` or `stream` reaches the comparator as a value change (reported, promoted), and TM's replay would send the default; a Codex tag position holding a non-string value that `_parse_message_item` routes past (`input.role:<null>`, `input.type:<array>` on a role-bearing item) leaves nothing in the IR, where the revision-2 byte scanner would have reported it. Both are the same defect: the parser substitutes a default instead of failing or preserving. The fix belongs there (`_parse_sampling` should let a missing `max_tokens` fail parsing; `_parse_message_item` should `keep_raw` when a tag position was non-string), which is adapter work outside this branch, and the owner has confirmed the class stays out. This spec adds no compensating path, and it says so rather than keeping a byte reader alive for one finding.

Opaque payload fields (`ToolDef.input_schema`, `ToolUseBlock.input`, `ImageBlock.source`, `SystemPart.cache_hint`) are modelled and carried without interpretation. They are Check 2 territory in full depth and are never treated as unmodelled.

### 3.2 Contract

**Invariant enforced (C1, D1):** the structural gate compares the union, over every candidate probe, of collapsed unmodelled (pointer, kind) pairs of `masked_request` against the same union over the reference; it reads no other representation of any probe, so presence appears in no verdict, and the only nodes absent from the comparison are the ones absent from the projection: the stamps `normalize_request` moves into `position_meta`, the `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` it drops, and the parser marker `input_item_raw_stamped`.

Both directions, stated plainly. A genuine provider addition observed in any single probe is a node of that probe's projection under an overflow root (an Anthropic or Codex envelope key at `/extras/<key>`; a Codex item key at `/extras/input_item_raw/*/raw/<key>`; a block or part key under `provider_data` or `raw`), reaches the comparison and gates. A field `normalize_request` strips (`previous_response_id`, `client_metadata`, `prompt_cache_key`, `cache_control`, `tm_wire_index`) is in no probe's projection, at any presence, and there is no other path into a verdict; a masked value cannot reach structure because structure reads no values.

Per bundle, computed at compare time from `ProbeEvidence` (never persisted, §6):

- `unmodelled_shape(bundle) -> tuple[JsonNodeObservation, ...]`: every masked node of any probe whose collapsed pointer falls under an **overflow root**, merged across the three probes into `JsonNodeObservation(pointer, kinds, present_in)` (existing type, reused). `kinds` is the union of kinds seen at that pointer; `present_in` is recorded for the report and read by no verdict. Collapse replaces every array index with `*`, so tool count and message count are invisible to structure. Overflow roots, transcribed from `ir.py`:

```
/extras
/system/*/provider_data
/tools/*/provider_data
/messages/*/provider_data
/messages/*/content/*/provider_data
/messages/*/content/*/raw
/messages/*/content/*/content/*/provider_data
/messages/*/content/*/content/*/raw
/metadata/provider_metadata
```

  A test pins this list against the catch-all fields of `ir.py` so the transcription cannot drift.

`compare_structure(reference, candidate) -> StructureCheck`:

- **BREAKING** when any candidate probe carries a parse-failure IR (`is_unparsed_request`, §7). Reason names the provider and, when present, `client_version`. Content is not compared and no projection is built for that probe.
- **DEGRADED** when `gained_shape` = {(pointer, kind) in candidate} minus {(pointer, kind) in reference} is non-empty. A new kind at a known pointer is a gained pair; a new pointer is a gained pair. Reason lists the pairs with the labels each was seen in.
- **EXACT** otherwise. Unmodelled structure that disappears is a reduction of blindness; Check 2 reports the removed leaves and it does not gate.

Nothing in this check reads a digest, a value, a presence count, a byte, or an unnormalized IR field.

Consequence, stated because it is the price of the invariant: an unmodelled field that flickers between launches (present in one candidate probe, absent from every reference probe) is DEGRADED, exits 1, and blocks promotion until TM absorbs it. That is what the owner asked DEGRADED to be: the list of structure TM has yet to model. The remedies are TM's, by existing seams: model the field in the IR, or, when it is launch-conditional envelope structure, add it to `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`, which is already the declaration of that class (`previous_response_id`, `client_metadata`, `prompt_cache_key`). No presence rule is added to absorb it silently.

Duplication note: a Codex item TM preserves raw shows its unknown key once, at `/extras/input_item_raw/*/raw/<key>`; if the same item also failed to parse into modelled blocks it shows again under `/messages/*/content/*/raw`. Two pointers for one gain, both in the one projection, one DEGRADED.

## 4. Check 2: content

`compare_content(reference, candidate, excluded) -> ContentDiff`, computed on the non-container nodes of `masked_request`, **label matched**: `A1` against `A1`, `B` against `B`, `A2` against `A2`. Prompt-derived pointers cancel by construction because both bundles run the same plan (§8 guarantees the plan matches before capture). A pointer is changed when, for any label, its digest or presence differs across bundles. Pointers in `excluded` (the union of both bundles' runtime sets, §5) are skipped.

Codex item values (D2): a value inside a preserved raw item, including a value under a key TM does not model, is a leaf at `/extras/input_item_raw/<i>/raw/...` of the projection (§2), masked by the same function as every message. When both bundles carry `input[message].new_envelope` and its leaf `x` moves from `1` to `2`, structure gains no pair and content lists `/extras/input_item_raw/<i>/raw/new_envelope/x`. "Check 2 reports what the harness changed" therefore holds for Codex item fields as it does for every other value in the projection, and nothing about the request is declared outside the content contract; the only exclusion is the runtime set, and it is printed.

Cell metadata (C5): `ContentDiff.cell` names the `BaselineCell` fields whose values differ between the bundles. By construction of `read_current_baseline` (keyed on harness, provider, launch model) only `harness_version` and `wire_model` can differ; `wire_model` also surfaces at `/model`, `harness_version` surfaces only here. A harness upgrade that emits identical request IR therefore reports `cell: (harness_version,)` and empty `changed`.

Output: `changed: tuple[JsonPointer, ...]` sorted, `excluded_runtime: tuple[JsonPointer, ...]`, `cell: tuple[str, ...]`. The CLI prints the changed pointers grouped by first segment (`system`, `tools`, `messages`, `extras`, `sampling`, `model`, `stream`, `metadata`) and the cell fields under `cell`. Values themselves stay in the two bundles.

Content never gates. Exit code and promotion do not read it. This is the owner's decision and it is what removes the inference engine: a value that changed for an unmasked reason is noise in a report, never a false verdict.

## 5. Runtime fields, and masks versus probes

`runtime_fields(probes) -> RuntimeFields`:

- `runtime`: masked leaf pointers whose digest or presence differs between `A1` and `A2`. Two launches of one setup; any difference is runtime-generated.
- `prompt_derived`: masked leaf pointers where `A1 == A2 != B`. Recorded as a fact for the report; no substring test, no classification, no consumer.

The relationship to the masks in `session/wire_normalization`:

- The masks are the source of truth. They work at substring precision inside a leaf (a Run ID line inside a 10 KB system part), which is what keeps that part comparable in Check 2. `runtime` works at leaf precision: a pointer in `runtime` is a leaf Check 2 cannot see at all.
- The probes validate the masks in one direction only. `runtime` non-empty means a mask has a hole or a runtime value has no mask. `runtime` empty does not prove the masks complete: date, cwd, branch and git-status masks are invisible to three same-day, same-directory launches and can only be validated across harvests, where a miss surfaces as content noise and never as a verdict.
- So: agree, with that asymmetry stated. Consequences for the report: a `runtime` member under `system`, `tools` or `messages` is a mask hole and is printed as "content blind at …"; a member under `metadata` or `extras` (session identity in `provider_metadata.user_id`) is routine and printed as runtime. Neither gates. Adding a mask for a structured field is a one-line change in `wire_normalization` when the operator wants the leaf back.

`repeat_a_outcome` has no successor. `runtime` is the fact it was approximating.

## 6. Data shapes and source of truth

Sketches only. Types marked (kept) exist today.

**Source of truth (C3).** Authoritative: `ProbeEvidence.raw_request_base64` (exact captured bytes) and `ProbeEvidence.request_ir`, the latter validated on every load against the former by re-parsing (below), which is the only reader of the bytes. Derived and never persisted: `masked_request`, `unmodelled_shape`, `RuntimeFields`, `ProbeAnalysis`; every verdict computes them from the two bundles' probes at compare time, so a mask or vocabulary correction applies retroactively and a stale or hand-edited analysis cannot exist. Persisted once as a decision record: `BaselineBundle.reference.comparison`, the output `harvest_controlled_baseline` computed and `write_baseline_bundle` acted on in the same process (`promotes_baseline` reads it to decide `current`, exactly as `reference_outcome` is read today). No later verdict reads it; it is recomputable by anyone from the two bundle files (`compare_baseline_bundles(read_baseline_bundle(reference.bundle_id), bundle)`), and the CLI prints from the freshly computed value, never from disk. Disagreement is therefore impossible by construction rather than detected by validation.

- `ProbeEvidence` (kept, reshaped): `+ request_ir: InternalRequest`; `inventory: RequestInventory | None` (None if and only if `is_unparsed_request(request_ir)`, P3); `- raw_nodes`; `- normalized_request`. Validator re-parses `raw_request_base64` through `adapters::get_adapter_for_provider(provider).inbound_request` and requires equality with `request_ir`, or, when `request_ir` is a parse-failure IR, requires the re-parse to raise (E4 pattern: derived evidence must match its source). `validate_raw_evidence` drops its `raw_nodes` clause and keeps the digest and inventory clauses (inventory clause skipped when None).
- `RuntimeFields`: `runtime: tuple[JsonPointer, ...]`, `prompt_derived: tuple[JsonPointer, ...]`.
- `ProbeAnalysis` (replaces `AbaAnalysis`, compute-time value, not a bundle field): `unmodelled_shape: tuple[JsonNodeObservation, ...]`, `runtime: RuntimeFields`. Printed by `main` for a bootstrap bundle and folded into the comparison otherwise.
- `DriftOutcome` (kept, members changed): `EXACT`, `DEGRADED`, `BREAKING`. `COMPATIBLE` and `INSUFFICIENT` deleted.
- `StructureCheck`: `outcome: DriftOutcome`, `gained_shape: tuple[JsonNodeObservation, ...]`, `reasons: tuple[str, ...]`.
- `ContentDiff`: `changed: tuple[JsonPointer, ...]`, `excluded_runtime: tuple[JsonPointer, ...]`, `cell: tuple[str, ...]`.
- `BaselineComparison` (kept, reshaped): `structure: StructureCheck`, `content: ContentDiff | None` (None when structure is BREAKING by parse failure).
- `BaselineReference`: `bundle_id: UUID`, `comparison: BaselineComparison`.
- `BaselineBundle` (kept, reshaped): `artifact_schema_version: Literal[3]`; `+ reference: BaselineReference | None`; `- observed_schema`, `- pointer_evidence`, `- static_nodes`, `- static_fingerprint`, `- repeat_a_outcome`, `- reference_bundle_id`, `- reference_outcome`, `- reference_reasons`, `- reference_unresolved_pointers`. No `unmodelled_shape` or `runtime` field is added (C3). Bootstrap is `reference is None`; the INSUFFICIENT sentinel and its validator clauses go. `validate_probe_contract` keeps the probe order, prompt digest and cell provenance rules (provenance rule applies to probes with an inventory) and drops the fingerprint recomputation.
- `baseline_store::promotes_baseline(bundle)`: `not any(is_unparsed_request(p.request_ir) for p in probes) and (reference is None or reference.comparison.structure.outcome is EXACT)`. DEGRADED does not promote (owner decision). Exit code is `0` iff it promotes. `_CurrentBundlePointer` and `read_baseline_bundle` move to version 3; no migration, no compatibility reader (store is empty, no back-compat obligation).

## 7. Deleted, by symbol

`baseline_evidence.py`:

- `EvidenceKind` (all five labels), `PointerEvidence`, `AbaAnalysis`, `classify_aba`, `_classify_pointer`, `_direct_prompt_pattern`, `_session_derived`, `_repeat_a_outcome`, `_presence_refusal`, `_covers`.
- `compare_baseline_bundles` as written: the two node universes, `changed_pointers`, `unknown_value_changes`, `unresolved_presence`, `static_changes`, `decided_static_changes`, `removed_pointers`, the four verdict paths and their precedence. Its name survives as the thin composition of the cell and prompt-plan guard, `compare_structure` and `compare_content`.
- `DriftOutcome.COMPATIBLE`, `DriftOutcome.INSUFFICIENT`, `BaselineComparison.unresolved_pointers`, `BaselineComparison.outcome` and `.reasons` as flat fields.
- `ProbeEvidence.raw_nodes`, `ProbeEvidence.normalized_request` and the `raw_nodes` clause of `validate_raw_evidence`.
- The import of `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`; `RequestStringLeaf` and `build_request_inventory` stay only for the probe validator. `mask_cross_launch_body` stays imported, now called by `masked_request` on the extras section (§2).

Elsewhere:

- `baseline_harvest::main`: the `reference_unresolved_pointers` and settlement-rule diagnostics.
- `baseline_capture::_build_probe_evidence`: the `observe_request_json` and `normalize_request` calls (the projection is derived at compare time).
- `test_baseline_comparator_invariants.py`: deleted whole. All seven tests exercise presence ratios, carrier sets, kind flips and mixed classifications, which are inputs to no verdict any more.
- `test_baseline_evidence.py`: delete `test_aba_classification_requires_direct_prompt_and_keeps_optionality_orthogonal`, `test_aba_marks_only_annotated_session_values_as_session_generated`, `test_bundle_load_rejects_static_fingerprint_that_disagrees_with_nodes`, `test_presence_sampling_reports_insufficient_without_changing_static_membership`, `test_presence_refusal_names_evidence_and_settlement`, `test_unresolved_presence_does_not_hide_an_unrelated_breaking_change`, both `test_nested_presence_flicker_*`, `test_unchanged_field_flickering_out_of_probe_b_is_insufficient`, `test_prompt_derived_field_addition_is_compatible`, `test_exact_comparison_reads_value_evidence`. Restate `test_stable_wire_scalar_changes_are_breaking` and `test_removing_demonstrated_static_pointer_is_breaking` as content facts that promote. Keep `test_date_and_cwd_only_changes_remain_exact_after_cross_launch_masking` and `test_cross_launch_extras_are_excluded_without_hiding_real_extras` (they become one-projection tests) and the store, version, and promotion tests with the new fields.
- `test_baseline_capture::test_harvest_persists_unresolved_comparison_pointers`: deleted; `test_harvest_runs_fresh_correlated_aba_and_persists_bundle` asserts the new bundle fields.
- `test_baseline_harvest::test_main_explains_unresolved_presence_pointer`: deleted; the other three adjust to the new outcome vocabulary.
- `/Users/alphab/.mdx/projects/tm-comparator-verify-brackets.sh`: retired; its 29 pairs describe paths that no longer exist.

Survivors, with reasons: `JsonNodeObservation` (reused for the shape; `present_in` is a report fact); `ProbeLabel`, `ControlledPrompts`, `BaselineCell`, `TranscriptEvidence` (evidence, not verdict); `RequestInventory` on the probe (its `capture` is the cell identity and its leaves are tier-1 evidence the certification path also reads); `_require_probe_order`. `DriftOutcome.INSUFFICIENT` does not survive anywhere: the one case that needed it, a mismatched prompt plan (Codex #3), moves in front of capture (§8).

New, and why nothing existing covers it: `masked_request` (assembles the projection from `normalize_request` output plus the four scalar sections and the reattached item catch-all; the wire-store projection deliberately omits those and must keep its identity), `unmodelled_shape` (the union and collapse over probes; the per-probe walker is reused), `runtime_fields`, `compare_structure`, `compare_content`, `is_unparsed_request` beside `unparsed_request_ir` (the sentinel is written there and read nowhere), and the overflow-root constant beside the IR. Nothing is added for JSON walking, canonicalization, masking, adapter lookup, or normalization, and nothing at all reads bytes for drift.

## 8. Acceptance: what each prior instance becomes

The seven the reviewers numbered, then the findings filed alongside them and the architect's blocker case. "Unrepresentable" means no verdict path can be built that reproduces it.

| # | Instance | Under the new design |
|---|---|---|
| 1 | date and cwd inside `/system` fingerprinted unmasked, BREAKING (C1, triage #2) | one projection, masked; a masked leaf compares equal; even unmasked it would be content. Unrepresentable: no value reaches a verdict |
| 2 | `/tools/0/cache_control` flicker BREAKING at `/tools` (E1) | `cache_control` is a stamp: `_strip_stamps` moves it into `position_meta` before the projection exists, so it is nowhere a check can read. Structure never sees it; content never sees it |
| 3 | `previous_response_id` and siblings reach the verdict on one axis (E2, N6, P1) | stripped once by `normalize_request`; there is no second axis to leave armed |
| 4 | constant field 3/3 in reference, 1/3 in candidate, BREAKING then INSUFFICIENT (P3) | content: reported at the labels where it is absent; promotes. If the field is unmodelled, no pair is gained, so structure is EXACT. No presence count feeds any verdict |
| 5 | 1/3 vs 1/3 value change, EXACT and promoted with nothing read (Grok 5, Codex 1) | label matched: `A1` vs `A1` differ, reported. Promotes, which is now correct because it is content and it is visible |
| 6 | maskable Run ID and cwd differences returned INSUFFICIENT while fingerprints matched (Grok 6) | there is no raw representation in the comparator; the masked leaves agree, `runtime` is empty, content is empty. Unrepresentable |
| 7 | prompt wrapper prose change EXACT and promoted (Grok 7) | `/messages/0/content/0/text` differs at every label; reported. `prompt_derived` is a fact, not an exclusion |
| + | removal suppressed by an unrelated 1/3 flicker (Codex 2) | no precedence: both are independent content facts, both printed |
| + | different prompt plan compares EXACT (Codex 3) | `harvest_controlled_baseline` reads `current` first (it already does) and refuses before the first launch when `reference.prompts != prompts`; `compare_baseline_bundles` raises on a mismatched cell or plan as a caller bug |
| + | refusal text names a presence rule the operator cannot satisfy (Grok minor, Codex 7) | reasons are rendered from the diff sets (gained pairs and findings with their labels, changed pointers by label); there is no rule prose to lie |
| + | `/tools/*/provider_data/new_mode` present in candidate A1 and A2 only, absent from the reference (architect blocker) | (pointer, kind) is in the candidate union and not the reference union: DEGRADED, exit 1, no promotion. The same holds when it is present in B only, or in one probe only |
| + | Codex `input[message].new_envelope` in all three probes (architect major, C2) | the item is preserved raw; `(/extras/input_item_raw/*/raw/new_envelope, object)` is a gained pair of the projection: DEGRADED |
| + | harness sends bytes that are not JSON | parse-failure IR persisted; P3 correlates it by prompt bytes; BREAKING, exit 1, `current` unchanged, reason names provider and client version |
| + | `previous_response_id` in candidate at presence 1, 2 or 3, absent from reference (D1) | `normalize_request` drops it before the projection exists and no byte reader remains; no pointer names it in either bundle; structure EXACT, promotes. The reverse (present in reference, absent from candidate) is identical |
| + | `input[message].new_envelope.x` present in both bundles, value `1` then `2` (D2) | same shape both sides, structure EXACT; content lists `/extras/input_item_raw/<i>/raw/new_envelope/x`; promotes, visibly |

C1's other half, "stable wire scalars are BREAKING" (`max_tokens`, `stream`, `temperature`, `model`), reverses on purpose: they are modelled values TM parses and replays, so they are content, reported and promoted. `wire_model` and `harness_version` differences are likewise content (§4); they are what a re-harvest exists to show.

The structural reason recurrence stops: one projection, `masked_request`, and no verdict reads anything else; content is not a verdict. A future reviewer can still find report noise; they cannot find a promote hole or a false gate built from a value, a count, or a second representation of the request, because there is no second representation to build it from.

## 9. Phased delivery

Each phase ends with `cd api && just check` and `cd api && just test` green, on this branch, additive commits, no rebase.

**P0. Prompt plan refusal before capture.** `harvest_controlled_baseline` compares `reference.prompts` to `prompts` after `read_current_baseline` and before the first `_capture_probe`; `main` already maps the exception to exit 1. Red test: a differing plan launches nothing. Independent of everything below.

**P1. Bundle carries the IR (v3).** `ProbeEvidence.request_ir` added and populated in `_build_probe_evidence` from `captured.request_ir`; version literals to 3 in `BaselineBundle`, `_CurrentBundlePointer`, `write_baseline_bundle`, `read_current_baseline`, `read_baseline_bundle`; the re-parse validator. Old comparator untouched and still green. Red test: v2 bundle and pointer are refused; a probe whose IR disagrees with its bytes is refused.

**P2. Replace the comparator in one verified phase (C6).** Additions and deletions land together so `baseline_evidence.py` never passes 700 lines: at `e894fade` it is 618 lines, the §7 deletions inside it span roughly 410 lines (`EvidenceKind` through `_repeat_a_outcome`), and the additions (`masked_request`, `unmodelled_shape`, `runtime_fields`, `compare_structure`, `compare_content`, the thin `compare_baseline_bundles`, six small types, the overflow-root constant) are on the order of 200 lines, so the phase lands near 410 lines with every function under 150. Contents: `DriftOutcome` to three members, `BaselineComparison` and `BaselineReference` reshape, `promotes_baseline` on structure only, `main` prints structure outcome, gained pairs with labels, runtime pointers, content pointers by section and cell fields; delete every symbol in §7 and the two test modules' obsolete cases; delete `test_baseline_comparator_invariants.py`.

Every P2 test starts from wire bytes and ends at the production comparison (D1): a cell is two byte bodies per probe label, parsed through `adapters::get_adapter_for_provider(provider).inbound_request` into `ProbeEvidence(raw_request_base64, request_ir, ...)`, assembled into two `BaselineBundle`s, and judged by `compare_baseline_bundles`; no test constructs a projection, a node set or a `StructureCheck` by hand, and no test calls `masked_request`, `unmodelled_shape` or `runtime_fields` to assert an outcome (they may be called to assert a pointer list). A strip applied anywhere except inside the production path therefore fails the cell instead of pinning the defect as correct.

Red tests, one file: overflow gain at each of the nine roots is DEGRADED and does not promote; a Codex message item gaining an unknown key is DEGRADED through `/extras/input_item_raw/*/raw/<key>`; overflow removal is EXACT and promotes with the leaves reported; masked Run ID leaves `runtime` empty and an unmasked one fills it, in a message and in a preserved raw item alike; label-matched wrapper change is reported; 1/3 vs 1/3 value change is reported; every key of `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`, every `PROVIDER_DATA_STAMP_KEYS` stamp and `input_item_raw_stamped` name no pointer of either bundle and gain nothing at presence 1, 2 or 3 in either direction; a Codex item whose unknown key exists in both bundles and whose leaf value changes is structure EXACT with the raw pointer in `changed` and promotes (D2); `harness_version` change reports under `cell`. The property sweep (presence 3/2/1 × leaf/nested/container × equal/changed value × modelled/overflow/stripped/preserved-raw) asserts four things, which is §3.2 written down: an overflow pair absent from the reference is DEGRADED at every presence 1, 2 and 3 with no promotion; a modelled pointer at every cell is structure EXACT and promotes with content reporting the change; a stamped or cross-launch-stripped node at every presence gains nothing and names no pointer; a preserved-raw leaf at every presence is structure EXACT when its shape is shared and its value change is in `changed`.

**P3. Parse failure surfaces as BREAKING (C4).** The delivery id is not in the wire body; `controlplane/envelope::extract_delivery_id` matches the launch prompt digest against a user text block of the IR, which a synthetic IR cannot satisfy. `_wait_for_correlated_exchange` therefore gains one fallback for entries whose IR `is_unparsed_request`: the probe correlates when the UTF-8 bytes of the controlled prompt occur in `captured.request_raw` (byte containment on the decoded body, valid for JSON and non-JSON alike; the default prompts contain no JSON-escaped characters, and a prompt that does simply fails to match and times out with a fourth named cause: "N unparsed exchange(s) did not contain the prompt bytes"). Such an entry is a candidate without a response IR (none is ever written for it) and still waits for the transcript reply, which the harness receives because the parse-failure seam never mutates the wire. `_build_probe_evidence` sets `inventory=None` for that probe (`build_request_inventory` cannot decode non-JSON and its provenance check cannot see the synthetic model); `is_unparsed_request` lands beside `unparsed_request_ir`; `compare_structure` returns BREAKING and `promotes_baseline` refuses even at bootstrap. Red tests: an unparsed probe over valid JSON the adapter rejects, and one over bytes that are not JSON, each yield a written bundle, `outcome=breaking-drift`, exit 1, `current` unchanged. Today both cases are fail-closed by accident (correlation timeout, no bundle); after P3 they are fail-closed by contract and say why. `baseline_capture.py` (469 lines) grows by a few dozen and stays well under 700.

## 10. Gates

- `cd api && just check` (format, lint, mypy) after every phase.
- `cd api && just test` after every phase; never bare `pytest`.
- Repo interpreter only: `cd api && uv run python`. Ambient `python3` is 3.13 and misreports PEP 758 syntax.
- No live harvest is required by this spec; the Claude 2.1.234 transcript blocker recorded in `tm-comparator-build.md` is unchanged and outside it.

## 11. Decisions, now fixed

- DEGRADED does not promote and exits 1 (owner confirmed). The gate doubles as the list of unmodelled structure TM has yet to absorb, including structure that flickers between launches (§3.2).
- The adapter's default substitution (§3.1) is out of scope (owner confirmed). `AnthropicAdapter._parse_sampling` failing on a missing `max_tokens` would route that removal into the parse-failure seam and make it BREAKING by the existing contract; `codex/request_parser::_parse_message_item` preserving raw on a non-string tag would route that case into `input_item_raw` and make it DEGRADED by this contract; both are separate later work.
