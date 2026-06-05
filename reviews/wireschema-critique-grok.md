# Wire schema design critique

Attack surface: `tm-wire-schema-design.md` against `baseline_evidence.py`, `request_inventory.py`, and the owner comment on issue 382.

## BLOCKER. Merged `items` hides a new tool kind that a maintainer would flag

**Claim.** Collapsing every array element into one merged `items` schema, with scalars as JSON type names only, makes a new discriminant that uses a subset of the unioned keys `EXACT`. The design calls that "a 13th tool of a known shape". It is a new shape. The repo already refuses to merge those.

**Failure.** Reference first-turn Codex body, `tools` is one function tool:

```json
{"tools":[{"type":"function","name":"read_file","description":"Read a file","parameters":{"type":"object"},"strict":false}]}
```

`mint_request_schema` over the A/B/A triple unions `items.properties` to `{type, name, description, parameters, strict}` and `items.required` to that same set only if every element has every key. Candidate adds the hosted tool Codex already models next to `function` in `api/tests/fixtures/codex_response_create.json`:

```json
{"type":"local_shell"}
```

No new key. Every key it does send (`type`) is a string. `compare_request_schema` returns `EXACT`. `promotes_baseline` promotes. The content report may list an added index. Content never gates.

That is a new tool kind on the wire. `json_tags::record_type_token` exists so "two different unknown shapes never merge". `json_tags::literal_tag` and `codex/request_parser::CODEX_REQUEST_TAG_SPINE` already treat `type` / `role` as structural tags. `codex/request_parser::unknown_request_item_fields` already splits `input[]` by `literal_tag(item["type"])` and reports `input[]:local_shell` for an unknown kind. The merged `items` schema throws that split away.

Same hole on `input[]` content parts (`input_text` vs a new part that only has `type` + `text`) and on Anthropic `content` blocks.

**Fix.** Keep index collapse. Do not merge distinct discriminants. Encode `items` as `oneOf` of observed object shapes, keyed by `json_tags::record_type_token` at the `TagSpine` tag positions (`type`, `role`). A 13th `type: "function"` tool stays `EXACT`. A first `type: "local_shell"` is `DEGRADED`. Reuse `CODEX_REQUEST_TAG_SPINE` / `WIRE_ITEM_TAG_SPINE` for where those tags live. Do not hand-maintain `KNOWN_INPUT_ITEM_KEYS` inside the minted schema.

## BLOCKER. A1 != A2 on raw leaves blinds the content check

**Claim.** `runtime_generated_pointers` taken as every pointer where A1 and A2 differ is not sufficient, and it is not what `classify_aba` uses for the fingerprint today. Composite harness prose will differ across two fresh `source_home`s, so the system prompt pointer is marked generated and dropped. The content check then cannot answer the only question the owner asked it.

**Failure.** `baseline_capture::_source_home` is `workspace / .baseline-sources / {bundle} / {model} / {a1|b|a2}`. Claude's first-turn system text, as captured in `api/tests/fixtures/claude_messages/turn-0/request.ir.json`, embeds the runtime-home UUID, the scratchpad path, the proxy port, and the inspector port. A1 and A2 therefore differ at the system string leaf (`/system` or `/system/2/text`). The design excludes that pointer. A candidate that rewrites the static Claude Code preamble (the "You are Claude Code" block, the tool policy, the output style) produces an empty `ContentReport` for that leaf.

`session/wire_normalization::mask_cross_launch_body` and `_mask_cross_launch_text` already rewrite those exact substrings (`_CROSS_LAUNCH_MASKS`, `_RUNTIME_HOME_PATH`, `_GIT_STATUS_MASKS`). `classify_aba` already runs that masker before it builds `static_nodes`. The reuse map omits it.

What still escapes even after the masker: a generated scalar that happens to collide on A1 and A2 (same calendar day if a new date format evades the mask; a counter that starts at 0 in every fresh home). Those stay in the content report and look like prompt edits. They do not gate. The poison case above does lose real prompt edits.

A generated substring also poisons the whole leaf. One unmasked port in a 4k system string excludes the entire string.

**Fix.** Content reads only `mask_cross_launch_body(_decode_json(raw))`, then `request_inventory::observe_request_json`. `runtime_generated_pointers` is A1 versus A2 on that masked tree. That is the "one or two" fields the owner named (`client_metadata`, `prompt_cache_key`), not the system prompt. Reuse `mask_cross_launch_body`. Do not invent a second masker.

## BLOCKER. The gate still has a second representation sitting next to the raw body

**Claim.** The last attempt died because an exclusion was applied to one projection and TM ink on the other still gated. This design names a pure `mint_request_schema` and then leaves the capture path's IR dump in the bundle as a "proposed" delete. That is the same armed second representation.

**Failure.** `baseline_capture::_build_probe_evidence` still does:

- `build_request_inventory(..., internal_request=captured.request_ir)`
- `normalize_request(captured.request_ir, cross_launch=True)`
- `ProbeEvidence.normalized_request = normalized.model_dump(mode="json")`

`normalize_request` is the IR projection that carried `provider_data`, `tm_wire_index`, `input_item_raw`, `keep_raw`. The design does not say `compare_request_schema` / `compare_content` are forbidden from reading `ProbeEvidence.normalized_request`, `RequestStringLeaf.tm_ir_section`, or a body that has already been through `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`. An implementer who "also checks the normalized dump so we do not miss tools" rebuilds the scrap.

`RequestStringLeaf.tm_ir_section` is filled by `request_inventory::_provider_semantics`. That is the IR section map. Using it to decide "this pointer is a system prompt or a tool definition" puts IR in the content check.

**Fix.** Write the same invariant the scrapped spec had, over raw bytes this time.

| Check | Reads, and reads only |
| --- | --- |
| Structure | `mint_request_schema` over `_decode_json(probe.raw_request_base64)` for the three probes. No mask. No strip. No inventory. No IR. |
| Content | `observe_request_json` over `canonical_json(mask_cross_launch_body(decoded))`, minus A1/A2 mismatches on that masked tree. Pointers and digests only. |
| Deleted from `ProbeEvidence` in the same change | `normalized_request`. Stop calling `normalize_request` from `_build_probe_evidence`. |

`client_metadata` stays in the structure schema. It is on the wire. Its values are runtime-generated after the masker. Stripping it in `classify_aba` via `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` must not move into `mint_request_schema`.

## MAJOR. Required to optional is not BREAKING

**Claim.** The open decision picks `BREAKING` because "a consumer that assumed presence can now fail". TM is not a consumer of the request. The owner comment defines `BREAKING` as a field TM requires gone or retyped, or a body that does not parse. A property that is still in `properties` is not gone and is not retyped.

**Failure.** Reference A1/A2/B all send `max_tokens: 10` (`test_baseline_evidence::_wire_request`). Candidate B omits `max_tokens` because the harness now leaves the default implicit. Candidate schema still has `max_tokens` in `properties`, `required` no longer includes it. Gate is `BREAKING`. Autopilot refuses to promote a harness that still speaks the same keys.

With n=3, an 80% field looks required about half the time. The flip is a sampling artifact.

**Fix.** No structure finding. The schema records the optionality change. The verdict stays `EXACT`. `BREAKING` only when the name is absent from candidate `properties` (never observed) or `json_kind` sets are disjoint. If the three-way vocabulary is forced to speak, `DEGRADED` is still the wrong owner word (`DEGRADED` is new or unknown structure) and it still blocks promote.

## MAJOR. `required` at n=3 is an overclaim

**Claim.** `mint_request_schema` sets `required` to keys present in every observation of that node. Three bodies, two of them the same prompt, is not a contract. The original issue text already said the schema is observed from finite captures, not an exhaustive provider contract. The design then talks about consumers and `BREAKING`.

**Failure.** Three probes all include `temperature`. The next twenty live first-turns omit it whenever it equals the default. The minted schema says `temperature` is required. The next baseline mint that sees one omission flips the flag and, under the open decision, breaks. `baseline_evidence::PointerEvidence.presence` already stores `always` / `sometimes` and `presence_by_probe`. `_presence_refusal` already refused to decide this case and spelled the counts as `reference=3/3 candidate=2/3`. Deleting `INSUFFICIENT` without keeping those counts throws the honest output away.

Minting one schema from A1+B+A2 also makes every B-only key optional forever. Prompt-conditioned shape is not "the request shape".

**Fix.** Persist presence counts on the schema node (`3/3`, `2/3`). Do not emit JSON Schema `required` as if it were a provider guarantee. Mint the structural tree from A1+A2 (same prompt). Use B only to classify values for the content report. `BREAKING` stays "gone from `properties`" or retyped or unparseable.

## MAJOR. `request_schema.py` rewalks a tree `request_inventory` already walks

**Claim.** "JSON Schema over a request body: none" is true as a document type. The walk, the type names, the presence fold, and the pointer identity are not new.

**Failure.** `mint_request_schema` as specified is a recursive walk that unions keys, intersects presence, and names types. That is `request_inventory::_observe_native` plus a fold. Types are `json_tags::json_kind` (`request_inventory` already casts that to `JsonKind`). Presence is `JsonNodeObservation.present_in` / `PointerEvidence.presence`. Pointers are `request_inventory::_pointer`, `_escape_pointer_token`, `_pointer_tokens`. Digests are `RequestJsonNode.sha256` via `canonicalization::canonical_json`. A second walker will drift from `_decode_json` (duplicate keys, NaN) the first time someone calls `json.loads` in the new file, which is what `classify_aba` already does today.

**Fix.** No new walk. Decode once with a promoted `request_inventory::_decode_json`. Take `observe_request_json` nodes. Collapse index tokens to `*`. Fold kinds and presence. Emit the JSON Schema document from that fold. `compare_request_schema` walks the folded tree and cites `JsonPointer` values built by `_pointer`. Promote `_decode_json` as the design says, and point `classify_aba` at it in the same change.

## MAJOR. After the items union, dropping an optional nested key is `EXACT`

**Claim.** The compare table has no row for "reference has an optional property, candidate does not". Recursive items union makes almost every nested key optional, because `required` on `items` is the intersection across every tool and every message.

**Failure.** Reference tools are Agent (`input_schema.properties` includes `subagent_type`) and Read (`path`). Union `items.properties.input_schema.properties` contains both, and neither is required. Candidate drops `subagent_type` from Agent. The name disappears from the candidate union. It was not required, so the table does not fire `BREAKING`. It is not a new candidate key, so not `DEGRADED`. Verdict `EXACT`. Content may show a removed pointer. Content never gates.

The same table also does not say what happens when the candidate *requires* a key the reference has as optional, or when the candidate type set is a strict subset. Those will get implemented as `EXACT` by omission.

**Fix.** Complete the table. Optional property removed is a finding (`DEGRADED` if you want a gate, report-only if you do not). Write the missing rows before code. Recursing into `input_schema.properties` also contradicts the design's own "13th tool of a known shape is `EXACT`": a new Claude tool whose arguments introduce any new name is `DEGRADED` under the recursive rule. Pick one and write it down. Owner's words ("a new or unknown field is `DEGRADED`") say recurse and accept the 13th tool with a unique argument as `DEGRADED`. The `local_shell` case in the first blocker is still `EXACT` unless discriminants stay unmerged.

## MINOR. A1 == A2 does not mean the value is harness-stable

**Claim.** The A/B/A triple identifies values that *moved*, not every runtime-generated value.

**Failure.** Both probes run on 2026-08-19. A date format the masker does not know is equal on A1 and A2, so the system leaf stays in the content set. Tomorrow's candidate reports a system prompt change. No gate, noisy report. Same for any generated number that resets in a fresh home (`strict: false`, a zero counter).

**Fix.** Keep the masker as the first cut. Accept residual report noise. Do not try to grow A1 != A2 into a general generator detector.

## MINOR. Content does not say which probe body it reads

**Claim.** `compare_content(reference, candidate)` is underspecified once a bundle holds A1, B, and A2.

**Failure.** Implementer diffs "all stable pointers in the bundle". `/messages/0/content` is equal on A1 and A2 (prompt A) so it is not runtime-generated, and B holds prompt B. The report lists the controlled prompt as a tool or system change, or it folds B's extra keys into added pointers.

**Fix.** Compare A1 to A1, after the masker. B is not a content source.
