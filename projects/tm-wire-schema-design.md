---
title: Raw wire schema drift, design for issue 382
status: reviewed
revision: 2
date: 2026-08-19
reviewed_by: opus, gpt, grok (independent, no coordination)
---

# Raw wire schema drift

Owner's ruling (#382): the schema is minted from the **raw wire body**. The IR is internal and is
never diffed. Raw-to-IR mapping is #392 and is out of scope, and the harness certification gate
hangs off #392 rather than this issue.

Revision 2 folds in three independent critiques. Every claim below that a reviewer disputed has
either changed or is defended in **Decisions**.

## The two checks are a partition, not two passes

This is the load-bearing idea and revision 1 did not have it.

Structure and content do not both walk the whole body. They **partition** it.

- **Structure owns the envelope.** The protocol frame: which keys exist, which item variants exist,
  what kind each position holds. It gates.
- **Content owns the payload.** Text and definitions authored by the harness: the system prompt, tool
  descriptions, tool argument schemas, message text. It never gates.

The boundary between them is one declared set of **opaque pointers**. Structure records the kind at
an opaque pointer and stops recursing. Content starts there.

Without this, minting recurses into `tools[].input_schema`, which is a JSON Schema the harness
authored. Adding an optional `timeout` to the Bash tool then reads as new structure, `DEGRADED`, and
refuses to promote. Tool schemas change on nearly every harness release, so the gate would fire on
essentially every release for a pure content edit. That is the same defect class that killed
revision 3 of the previous spec: something that is not the request contract reaching the verdict.

Opaque roots, declared per provider, matched by prefix:

| Provider | Opaque at | Why |
| --- | --- | --- |
| anthropic | `/system/*/text`, `/tools/*/description`, `/tools/*/input_schema`, `/messages/*/content/*/input`, `/messages/*/content/*/text`, `/metadata` | harness-authored text and schemas |
| codex | `/instructions`, `/tools/*/description`, `/tools/*/parameters`, `/input/*/content/*/text`, `/input/*/arguments`, `/input/*/output`, `/input/*/encrypted_content` | same, plus JSON-in-a-string arguments the walker cannot see into anyway |

## One traversal

`request_inventory::_observe_native` already walks a decoded body emitting pointer, kind and digest.
Minting must not add a second walk. Two walkers over the same bytes drift the first time someone
calls bare `json.loads` in the new file, which `baseline_evidence::classify_aba` already does today.

Extract the visitor in `_observe_native` into one public traversal that yields, per node, the decoded
value, the **typed path**, the RFC 6901 pointer and the JSON kind. Rebuild `observe_request_json` on
it, and build minting on it.

The typed path matters and fixes a live bug. `request_inventory::_pointer_tokens` coerces every
decimal token to an integer without consulting the parent container, so a tool schema containing
`{"properties": {"0": {...}}}` has its object key `0` read as an array index. Collapsing array
indices by string-rewriting pointers inherits that bug. Array position is resolved only from the
actual parent container.

Promote `request_inventory::_decode_json` to public in the same change and point `classify_aba`,
`codex/request_parser` and `adapters/anthropic` at it. It is the strict door that rejects duplicate
keys and NaN; three call sites bypass it today.

## `request_schema.py`, a top-level leaf

Pure over raw JSON. It imports `json_tags` and `canonicalization` and nothing else from the tree.
It knows nothing about baselines, probes, harnesses, or the IR.

### The node

One node type, total over the six JSON kinds. Not three disjoint cases.

```
kinds: frozenset[str]            # from json_tags::json_kind, never a single value
properties: {key: node} | None   # present when "object" was observed
present_in: {key: int}           # per key, how many observations of this node carried it
items: node | {tag: node} | None # present when "array" was observed
observation_count: int
opaque: bool
```

A position can be observed with two container kinds. Anthropic `system` is a bare string in some
harness versions and an array of blocks in others; message `content` is a string for a simple user
turn and an array otherwise. `kinds` is a set and `properties` and `items` coexist.

### Arrays branch per discriminator

Established by probing real captures, not by argument. `api/tests/fixtures/codex_response_create.json`
shows `input[]` is a discriminated union on `type`: `message`, `reasoning`, `function_call`,
`function_call_output`, `custom_tool_call_output`, plus an untagged plain message carrying only
`content` and `role`.

Collapsing those five into one union gives `required` as the empty intersection and `properties` as a
soup of every variant's keys. A `function_call` that stops sending `name` is then not breaking,
because `name` was never required in the soup, and a brand new variant built from already-seen keys
reads `EXACT`. A new variant is the single highest-value drift signal TM exists to catch.

Group an array's object elements by `json_tags::record_type_token` over the first present tag key,
preferring `type`, then `role`, then one untagged bucket. The repo already does exactly this in
`codex/request_parser::unknown_request_item_fields`, which groups raw input items by `type` with the
documented role-only fallback and addresses findings as `input[<type>].<key>`. That mechanism is
reused rather than reinvented.

Guard: more than twelve branches at one array means the key is not a discriminator, and the array
falls back to a single unioned `items`.

### `required` is not minted

Three probes, two of them the same prompt, is not a provider contract. #382's own text says the
schema is observed from finite captures and is not an exhaustive contract.

The artifact carries `present_in` counts and `observation_count`, never a bare `required` flag. An
80% field looks required about half the time at n=3, so a required flag would flip on sampling noise.
The exported JSON Schema projection may spell `required` for keys at full presence, but nothing
gates on it.

## Comparison

### The gate cannot see anything but schemas

```
compare_request_schema(reference: RequestSchema, candidate: RequestSchema) -> StructureReport
```

It takes **schemas, not bundles**. This is a type-level guarantee, and it is the most important
change in revision 2. Revision 1 kept `compare_baseline_bundles(reference, candidate)`, which leaves
`ProbeEvidence.inventory`, `RequestStringLeaf.tm_ir_section`, `PointerEvidence.tm_ir_sections` and
`normalized_request` all reachable from the function that produces the verdict. Every one of the four
blockers that killed the last attempt was TM bookkeeping reaching a gate. Making it unreachable by
construction is stronger than any rule saying not to read it.

`ProbeEvidence.normalized_request` is deleted. It is produced by
`session/wire_normalization::normalize_request`, which is IR-derived, and it has no business in a raw
wire bundle.

### The relation is total by construction

Revision 1 gave six rows and left the rest of the lattice undecided, which an implementer resolves as
`EXACT` by omission. Elementwise set arithmetic instead, at every node:

| Observation | Verdict |
| --- | --- |
| a kind in candidate, absent from reference | `DEGRADED` |
| a property in candidate, absent from reference | `DEGRADED` |
| an array branch tag in candidate, absent from reference | `DEGRADED` |
| a property name in reference, absent from candidate `properties` entirely | `BREAKING` |
| an array branch tag in reference, absent from candidate | `BREAKING` |
| kind sets disjoint | `BREAKING` |
| body does not parse | `BREAKING` |
| a kind or property in reference, still present, at lower presence | finding, no verdict |

Precedence `BREAKING` > `DEGRADED` > `EXACT`. Every finding carries its pointer, the branch tag when
it has one, and a reason. No verdict is produced by an unexplained enum.

Not comparable is **not a verdict**. It raises. `baseline_capture::harvest_controlled_baseline`
already refuses a mismatched prompt plan this way at `afe74039`; the cell-coordinate and capture-plan
checks join that same refusal path, which leaves `compare_request_schema` total over comparable
inputs and removes the need for an `INSUFFICIENT` member.

## Content

```
compare_content(reference: ContentObservations, candidate: ContentObservations) -> ContentReport
```

Over string leaves at and under the opaque roots, grouped as system, tools, and other. Returns a
report. Contributes to no outcome and is not reachable from promotion logic.

Values are compared **after `session/wire_normalization::mask_cross_launch_body`**, which already
masks run id, run name, runtime home, proxy and inspector URLs, `<cwd>`, `<timezone>`,
`<current_date>`, the scratchpad line, the gitStatus block and recent commit lines.
`baseline_evidence::classify_aba` already applies it to the raw body.

This is what makes the content check work at all. A harness system prompt is one string leaf holding
stable instruction text with a handful of per-launch substrings embedded in it. Under a plain
pointer-level rule, one volatile substring marks the whole leaf runtime-generated and excludes the
entire system prompt from the report, forever, on every version. The content check would exclude its
own primary subject.

Residual runtime exclusions, after masking:

- Only **non-container** nodes. `RequestJsonNode.sha256` is computed for containers too, so a plain
  "A1 digest differs from A2" rule puts the root pointer in the set and a subtree exclusion then
  swallows the whole document. The existing `_repeat_a_outcome` avoids this by skipping `array` and
  `object` kinds; revision 1 dropped that rule silently.
- The **union** of exclusions from both bundles, not the candidate's alone.
- `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` stays excluded.

Known residue: a runtime value that happens to be equal across A1 and A2 within one bundle escapes
detection, for example a date or working directory shared by both probes. Masking covers the known
cases; the rest surfaces as a content finding, which never gates, so the failure mode is a noisy
report rather than a false verdict.

Content is addressed by **discriminator plus key** (`tools[function].description`), not by array
index. Revision 1 accepted permanent reordering noise as a limitation; discriminator addressing
removes it, and the repo already addresses findings this way.

## Bundle and store

`artifact_schema_version` 2 becomes 3. No migration; both readers already hard-refuse a foreign
version with "regenerate the baseline".

`BaselineCell` gains the **capture plan**: `no_system_prompt`, `bypass_permissions`, and whether the
HOME was bare. The raw body is genuinely clean today, but the leak vector is upstream of the body:
two captures taken under different launch conditions are not comparable, and nothing currently
records the conditions. Mismatch takes the refusal path.

`promotes_baseline` becomes `reference_outcome is None or reference_outcome is EXACT`.

**The accept path is required, not optional.** Every real harness release adds fields, so every real
release is `DEGRADED` and does not promote. Without an explicit accept step the current pointer pins
to the first capture ever taken, every later capture compares against that same ancient reference,
and the harvester returns 1 forever. A reviewed `DEGRADED` bundle is promoted by an explicit
operator action that records who accepted it. The gate must have a forward door or it jams closed on
first contact with a real release cadence.

## Decisions

1. **BREAKING is wire-only and TM-blind.** Decided from the two schemas alone. TM-dependency cannot
   be an input, because the raw-to-IR mapping is #392.
2. **Required to optional does not gate.** Revision 1 said `BREAKING`. That was wrong and it
   contradicted decision 1: the justification was "a consumer that assumed presence can now fail",
   which assumes TM consumes the field, which decision 1 forbids. TM is not a consumer of the
   request. A property still in `properties` is neither gone nor retyped. At n=3 the flip is a
   sampling artifact. It is recorded as a presence-count change and reported, and it does not gate.
   `BREAKING` requires the name to be absent from candidate `properties` entirely, or kind sets to be
   disjoint, or the body not to parse.
3. **The outcome decides baseline promotion only.** Certification gates on #392, per the owner:
   certification asks whether TM can still handle a harness version, which is a mapping question.
4. **Arrays branch per discriminator.** Proven on real captures before any production code.

## Out of scope for this issue, and tracked

**Headers, endpoint path and query.** The structure check is body-only. A harness ships
`anthropic-beta: context-1m-2025-08-07` with a byte-identical body and the verdict is `EXACT`. That
is a real miss for a drift detector, and it is a separable slice with its own capture plumbing:
`ProbeEvidence` persists no headers, though `request_pipeline::capture_request_flow_state` already
captures `original_headers`. Note also that `decoded_http_body_bytes` has already decoded content
encoding, so the "raw wire body" is post-decode by construction. Tracked separately. It is stated
here so no reader of this design believes request drift is fully covered.
