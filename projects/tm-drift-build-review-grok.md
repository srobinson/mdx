---
title: Comparator-truth implementation review (Grok)
type: projects
tags: [transport-matters, baseline-capture, comparator, review, adversarial]
summary: Adversarial read-only review of e894fade..5224095f against tm-drift-spec revision 3. Two blockers (Codex client_metadata still gates; P3 prompt-byte correlation binds the wrong exchange).
status: active
project: transport-matters
confidence: high
created: 2026-08-19
updated: 2026-08-19
---

# Comparator-truth implementation review

**Verdict: the branch does not deliver the spec.** `compare_structure` and `compare_content` do read one projection, and they do not read raw bytes, inventory leaves, or presence counts. The projection still contains fields the spec declared unrepresentable, and P3 will persist the wrong exchange as probe evidence. `cd api && just check` / `just test` being green does not cover these inputs.

Reviewed: `fix/comparator-truth` at `5224095f`, range `e894fade..HEAD`. Interpreter: `cd api && uv run python`. Repo tree was not modified.

## Blocker

### B1. Codex `client_metadata` is in the projection and gates

**Where:** `codex/request_parser.py::parse_codex_request` maps `client_metadata` through `_parse_metadata` into `RequestMetadata.provider_metadata`. `baseline_evidence.py::masked_request` then dumps `request.metadata` verbatim. `session/wire_normalization.py::CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` names `client_metadata`, and `normalize_request` drops it only from `request_extras`. On Codex the key is in `MAPPED_REQUEST_KEYS`, so it never sits in extras. The strip is a no-op.

**Input:** two first-turn Codex bundles. Reference has no `client_metadata`. Candidate has

```json
"client_metadata": {
  "x-codex-installation-id": "install-a1",
  "x-codex-turn-metadata": {"turn": 1}
}
```

**Observed:** `compare_baseline_bundles` returns `DEGRADED`. Gained pairs include `/metadata/provider_metadata/x-codex-installation-id`, `/metadata/provider_metadata/x-codex-turn-metadata`, and `/metadata/provider_metadata/x-codex-turn-metadata/turn`. `promotes_baseline` is false. A same-shape value change (`"one"` to `"two"` on `x-codex-installation-id`) is `EXACT`, promotes, and lists `/metadata/provider_metadata/x-codex-installation-id` in `content.changed`. A new key on A1 only (`new_flag: true`) is `DEGRADED` at presence 1.

**Required:** spec §2, §3.2, and §8 instance 3 / D1. `client_metadata` is a declared sibling of `previous_response_id`. No pointer may name it. No presence of it may gain a pair. The same disease the spec was written to kill: an exclusion applied where the field no longer lives.

`previous_response_id` and `prompt_cache_key` on the same Codex envelope are dropped. Those two hold.

### B2. P3 prompt-byte fallback binds a foreign unparsed exchange

**Where:** `baseline_capture.py::_wait_for_correlated_exchange`. For `is_unparsed_request`, membership is `prompt.encode() in captured.request_raw`. Every such hit becomes a candidate. There is no check that the exchange is the probe's, and an unparsed hit is not discarded when a delivery-id match also exists.

**False positive, executed through `harvest_controlled_baseline`:** prompt `alpha`. Owned body `{"messages":[],"note":"\\u0061lpha"}` (adapter rejects; UTF-8 bytes of `alpha` are absent). Title body `{"messages": [], "note": "Generate a title for: alpha"}` (adapter rejects; contains `alpha`). Transcript has a user-then-assistant reply. Harvest succeeded. All three probes recorded `exchange_id=titletra-...` and the title bytes. The owned request was ignored.

**Required:** the fallback may attach only the probe's unparsed body. A title, warmup, or leftover exchange that quotes the prompt is not the probe.

**Also representable:** prompt `test` is a substring of `{"model":"latest"}`. Prompt `hello\nworld` is absent from `json.dumps({"note": "hello\nworld"})` (`b"hello\\nworld"`). The first is another false positive; the second is a false negative that times out with the fourth named cause. The spec names the escaped-prompt timeout. It does not name silently adopting a title request.

A parsed owned request plus an unparsed title that contains the prompt produces two candidates and raises `BaselineCorrelationError`. `test_baseline_capture.py::test_harvest_ignores_title_request_that_wraps_controlled_prompt` only covers a parsed title.

## Major

### M1. Nested `cache_control` reaches the structural gate

**Where:** `session/wire_normalization.py::normalize_message` runs `_strip_stamps` on `message.provider_data` and on `body["content"][i].provider_data` only. It does not enter `ToolResultBlock.content`. `adapters/anthropic.py::_parse_tool_result_sub_block` puts `cache_control` on a nested text part into `TextBlock.provider_data`.

**Input:** otherwise identical Anthropic bodies. Candidate nested block is `{"type":"text","text":"nested","cache_control":{"type":"ephemeral"}}`.

**Observed:** `DEGRADED`. Gained `/messages/*/content/*/content/*/provider_data`, `.../cache_control`, and `.../cache_control/type`. `normalize_message` leaves `cache_control` in the nested `provider_data`. `promotes_baseline` is false. Top-level text, tool, system (`cache_hint`), and tool_result-block-level `cache_control` are stripped and stay `EXACT`.

**Required:** spec §8 instance 2. `cache_control` is a stamp. It must not exist in the projection.

**This cell:** `BaselineCell.request_shape` is `first-turn`. `harvest_controlled_baseline` records the first correlated exchange of a fresh launch. That body has a user text block, not a `tool_result`. The hole is in the comparator. The contract fixture `_anthropic_body` injects a `tool_result` on every Anthropic case, so the production path for nested stamps is exercised only as a test scaffold, never stripped.

### M2. Stamps inside reattached `input_item_raw` name pointers and gate

**Where:** `baseline_evidence.py::masked_request` reattaches `provider_extras["input_item_raw"]` and runs `mask_cross_launch_body` only. It does not run `_strip_stamps`. `codex/request_parser.py::_parse_content` sets `keep_raw` when an `input_text` part has any key beyond `type` and `text`.

**Input:** first-turn Codex. Candidate part is `{"type":"input_text","text": prompt, "cache_control":{"type":"ephemeral"}}`. Reference has a clean part.

**Observed:** `DEGRADED`, no promote. Gained pairs include `/extras/input_item_raw`, `/extras/input_item_raw/*/raw/content/*/cache_control`, and the rest of the preserved item. Projection pointers include `/extras/input_item_raw/0/raw/content/0/cache_control`. The same for an item-level `tm_wire_index: 9` (`/extras/input_item_raw/0/raw/tm_wire_index`). `input_item_raw_stamped` stays out. Modelled `Message.provider_data["tm_wire_index"]` is stripped.

**Required:** spec §2. Nothing Transport Matters generated, and no `PROVIDER_DATA_STAMP_KEYS` name, may appear. This cell is first-turn Codex. An extra key on the user `input_text` part is a legal first request.

Reattachment of the parser's `{index, raw}` wrapper is what the spec asked for. The miss is that `_strip_stamps` is not applied to `raw`.

### M3. Every system or developer input item becomes overflow

**Where:** `codex/request_parser.py::_parse_system_message_item` always returns `keep_raw=True`. `_parse_input` therefore writes the item to `input_item_raw` even when the only keys are `type`, `role`, and `content` and every part is modelled `input_text`.

**Input:** Codex reference with one user message. Candidate adds `{"type":"message","role":"developer","content":[{"type":"input_text","text":"be concise"}]}` and keeps the user message.

**Observed:** `DEGRADED`. Gained `/extras/input_item_raw` and children, plus `/system/*/provider_data/role`. Content also lists `/system/1/text`. The developer text was modelled as `SystemPart`. The overflow exists only because the parser always preserves the item.

**Required:** spec §2. `input_item_raw` is the catch-all for items that cannot round-trip from modelled fields. A clean developer or system message can. Reattachment does not miss a parser route (`custom_tool_call`, `additional_tools`, non-object items, `function_call` with `id`, extra message keys all appear). It reattaches items the spec's list did not include, and those items are Transport Matters keep_raw, not harness overflow.

Reasoning extras correctly stay on `ThinkingBlock.provider_data` and are not reattached.

### M4. A loaded bundle can disagree with itself

**Where:** `baseline_evidence.py::ProbeEvidence.validate_raw_evidence` and `_require_ir_matches_bytes`. `BaselineBundle.validate_probe_contract`.

**Inputs that construct and load:**

1. Parsed Anthropic bytes. `inventory.capture.provider = "codex"`, `inventory.capture.model = "claude-test"`. `request_ir.provider` remains `anthropic`. `ProbeEvidence.model_validate` accepts. `write_baseline_bundle` / `read_baseline_bundle` round-trip the disagreement.
2. Same bytes. `inventory.capture.model = "other-model"` while `request_ir.model` is `anthropic/claude-test`. `ProbeEvidence` accepts. The bundle rejects only when `capture.model != cell.wire_model`, and it never requires `request_ir.model == cell.wire_model`.
3. `unparsed_request_ir(..., "anthropic", "1.0")` beside a body `parse_codex_request` accepts. `ProbeEvidence` accepts, because the Anthropic adapter raises.

**Required:** spec §6. Derived evidence must match its source. IR, bytes, inventory provenance, and cell identity cannot tell different stories. Bytes versus IR still match for parsed probes. Provenance does not.

`model_construct` can invent any combination. Production harvest and JSON load use validators. The load hole is the one that matters.

### M5. Several P2 tests pass for the wrong reason

**Where:** `test_baseline_comparator_contract.py` and `test_baseline_evidence.py`.

| Test | What it claims | Why it is green |
|---|---|---|
| `test_a_cross_launch_stripped_key_names_no_pointer_at_any_presence` | `client_metadata` cannot reach a verdict | Builds an Anthropic envelope. The key lands in `request_extras` and is stripped. Codex, where the key is metadata, is never built. B1 is invisible. |
| `test_a_provider_data_stamp_names_no_pointer_at_any_presence` | every stamp, any presence | `_stamped_body` writes the stamp onto `messages[0].content[0]` only. Nested `ToolResultBlock.content` (M1) and Codex `input_item_raw` (M2) are not in the case. |
| `test_a_modelled_value_at_every_cell_is_structure_exact_and_reported` | modelled pointer, every presence × depth × equality | Both sides always send `service_tier` under extras. That is overflow with a stable shape. `top_k` is constant. No modelled field is varied. |
| `test_projection_names_every_unmodelled_root_and_nothing_transport_generated` | list pinned to `ir.py` catch-alls; no TM names | Asserts `UNMODELLED_POINTER_ROOTS` equals a dict copy in the test, then asserts `masked_request` has eight top-level keys. It does not read `ir.py` fields. It does not assert a stamp pointer is absent. |
| `test_the_codex_parser_marker_names_no_pointer_at_any_presence` | marker never named | Adds `new_envelope`, which is `DEGRADED`. Asserts only that the substring `input_item_raw_stamped` is missing from gained pointers. |

Contract helpers do start from wire bytes and end at `compare_baseline_bundles`. That bar is met for the cases they actually encode. Spec §9 P2 also required the modelled / overflow / stripped / preserved-raw sweep, stamps at every presence, and a pin against `ir.py`. Those claims are not what the assertions test.

## Minor

### m1. Store tests construct `StructureCheck` by hand

**Where:** `test_baseline_evidence.py::test_bundle_store_promotes_only_unchanged_structure`, `test_exact_reference_helper_promotes`, `_exact_reference`.

They write a forged `BaselineReference.comparison` and check `write_baseline_bundle` / `read_current_baseline`. They would stay green if `compare_baseline_bundles` always returned `DEGRADED`. Spec §9 P2 forbids hand-built `StructureCheck` on the comparator cases. These are store tests. They still pin promotion to a forged outcome.

### m2. P3 false negative on JSON-escaped prompt text

**Where:** `baseline_capture.py::_wait_for_correlated_exchange`.

**Input:** prompt `hello\nworld`, body `json.dumps({"note": "hello\nworld"})` → `b'{"note": "hello\\nworld"}'`. `prompt.encode() in body` is false.

**Observed:** the unparsed exchange is counted in `unparsed_without_prompt` and times out with "did not contain the prompt bytes".

**Required:** spec §9 P3 names this timeout. Hunt 7 asked for a false negative. This is one. Default harvest prompts have no escapable characters, so today's CLI plan does not hit it.

### m3. Null skip at overflow roots is slightly broader than its comment

**Where:** `baseline_evidence.py::unmodelled_shape`.

It skips `node.kind == "null"` only when the collapsed pointer is exactly in `UNMODELLED_POINTER_ROOTS`. The comment talks about optional `provider_data`. The set also contains `/extras`, `/messages/*/content/*/raw`, `/messages/*/content/*/content/*/raw`, and `/metadata/provider_metadata`.

**Executed:** those four roots are never null in a `masked_request` projection (`extras` is always a dict; `UnknownBlock.raw` is a required dict; `provider_metadata` defaults to `{}`). A null *child* (`thinking: null` on the Anthropic envelope) is `DEGRADED` at `/extras/thinking`. Empty or missing `provider_data` dumps as null and is skipped, so adding a system part with no overflow is not a gain.

**Judgement:** the skip is right for the optional `provider_data` roots. It is not too narrow. It is only vacuously broad on the other roots.

### m4. Nine overflow roots match the `ir.py` catch-alls

**Where:** `ir.py::UNMODELLED_POINTER_ROOTS`.

The nine roots are `provider_extras`, every `provider_data`, both `UnknownBlock.raw` depths, and `RequestMetadata.provider_metadata`. `SystemPart.cache_hint`, `ToolDef.input_schema`, `ToolUseBlock.input`, and `ImageBlock.source` are modelled opaque, as the spec said. There is no third nest: `ToolResultBlock.content` cannot hold another `tool_result`.

Nothing missing, nothing unreachable in the comparator (the contract fixture supplies nested blocks). The first-turn harvest simply never produces the nested pair. Not a defect in the list.

## Nothing found

**`_collapse`.** Executed RFC 6901 keys `foo/bar` (`/foo~1bar/*`) and `tilde~key` (`/tilde~0key/*`), numeric object keys (`/obj/0` kept), empty-string keys (`//*`), nested arrays (`/arr/*/*`), and a literal `*` object key (`/also/*` on an object parent). Array indices collapse; object keys that happen to be digits do not. `_covers` on an uncollapsed pointer against a `*`-root is false, which is why a collapse failure would drop overflow rather than mis-merge it. No input found that collapses a non-index or leaves an index standing.

**Promote hole on a modelled value.** `max_tokens` 10 → 99 is `EXACT`, `content.changed` is `/sampling/max_tokens`, `promotes_baseline` is true. That matches the spec's reversal of "stable wire scalars are BREAKING".

**Second reader of raw bytes or inventory in a verdict.** `compare_structure` reads `unmodelled_shape` → `_projection_nodes` → `masked_request`. `compare_content` reads `_leaf_digests` of the same. `present_in` is report text. Inventory is stored and not read. The failures above are fields that should have been excluded from the one projection, plus a harvest correlator that feeds the wrong IR into that projection.

## Hunt 10: still representable

| Spec §8 claim | Still representable? |
|---|---|
| date / cwd inside `/system` cannot reach a verdict | No case found. Cross-launch masks still cancel those leaves. |
| `/tools/0/cache_control` flicker cannot reach a verdict | Tool-level stamp is stripped. Nested content (M1) and Codex raw (M2) still represent the same stamp. |
| `previous_response_id` and siblings cannot reach a verdict | `previous_response_id` and `prompt_cache_key` hold on Codex extras. `client_metadata` does not (B1). |
| presence counts cannot feed a verdict | Holds. Presence 1 of a new overflow key is `DEGRADED` by pair set difference. |
| 1/3 vs 1/3 value change is visible | Holds for a change on B (`test_a_value_change_in_one_probe_is_reported_by_the_label_that_carries_it`). A change on A1 only is classified runtime and excluded, which is §5. |
| non-JSON bytes are BREAKING | Holds when correlation attaches the right body. B2 can attach a different unparsed body instead. |
