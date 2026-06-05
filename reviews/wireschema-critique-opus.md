---
title: Critique, raw wire schema drift design (issue 382)
reviewer: opus, independent architecture critic
date: 2026-08-19
target: ~/.mdx/projects/tm-wire-schema-design.md
verdict: 3 blockers, 9 majors, 4 minors
---

Read as of the revision carrying the Reuse Map and the `normalized_request` note.

# BLOCKERS

## B1. The array collapse deletes `required` inside every heterogeneous array, so a removed field TM parses reads `EXACT`

**Claim under attack.** "array: `items` is the union over every element of every observation. Array
indices collapse." Combined with "`required` is the keys present in every observation of that node",
`required` at a collapsed array position is the intersection over every element of every array.

**Why that is wrong.** The arrays that carry the request are heterogeneous by construction. Codex
`input[]` holds `message`, `function_call`, `function_call_output`, `reasoning`, `additional_tools`
items. Anthropic `tools[]` holds custom tools (`name`, `description`, `input_schema`) beside server
tools (`type`, `name`, `max_uses`). Anthropic `content[]` holds `text`, `tool_use`, `tool_result`
blocks. Intersecting keys across those shapes collapses `required` to the tag field alone, or to
nothing. `required` is the only input to the `BREAKING` rule "a reference-required property is absent
from candidate `properties`". Empty `required` means no `BREAKING` verdict is reachable inside any
array.

**Concrete failure.** Reference capture of Codex: `input` contains one `message` item
(`type`, `role`, `content`) and one `function_call_output` item (`type`, `call_id`, `output`).
Minted `/input/items.required = {"type"}`, because `role` is absent from the
`function_call_output` element. A new Codex release renames `role` to `author` on every message
item. Candidate `/input/items.properties` gains `author` and loses nothing that was required.
Verdict: `DEGRADED` for the new property, never `BREAKING`. `codex/request_parser::parse_codex_request`
and `KNOWN_INPUT_ITEM_KEYS["message"]` both read `role`; TM stops resolving roles on the next
release and the gate that exists to catch it says "new field, take a look".

**Second concrete failure, the other direction.** Anthropic 12 custom tools, reference
`/tools/items.required = {"name", "description", "input_schema"}`. The next harness release adds a
`web_search_20250305` server tool, which carries no `description`. `description` drops out of the
candidate intersection. Verdict: `BREAKING`. Nothing broke. The owner classified adding a tool as
content. The same mechanism produces both a false negative and a false positive.

**Third.** In a first-turn capture most arrays hold exactly one element (`messages` has one user
message, its `content` one text block). For those the collapse does nothing at all: the union over
"every element of every observation" is the union over three copies of one element. The mechanism is
inert exactly where the design says it is load bearing, and destructive exactly where the array is
real.

**Fix.** Group array elements by their discriminator before unioning, and mint one sub-schema per
discriminator token. The discriminator is `type`, falling back to `role`, falling back to the absent
marker. `json_tags::record_type_token` already returns the collision-proof hashable token for exactly
this (`("literal", "message")` vs `("kind", "array")`), and
`codex/request_parser::unknown_request_item_fields` already groups raw input items by `type` and
reports `input[<type>].<key>`. Under discriminated grouping the design's own goal survives intact: a
13th tool of a known shape adds no group and no key, so `EXACT`; a tool that gains a field is still
the structural signal; a new server tool is a new group, so `DEGRADED`; and `description` stays
required for the group that always carried it, so the false `BREAKING` disappears. See M9 for why
this also dissolves the open decision.

## B2. `runtime_generated_pointers` is pointer-granular over string leaves that mix volatile and stable text, so the content check excludes the system prompt

**Claim under attack.** "`repeat_a_outcome` becomes `runtime_generated_pointers`. Its real job is
naming the one or two runtime-generated values" and "`compare_content` over stable pointers only,
excluding `runtime_generated_pointers`".

**Why that is wrong.** A pointer names a whole JSON string leaf. The harness system prompt is one
leaf holding megabytes of stable instruction text with a handful of per-launch substrings embedded in
it. Any one volatile substring makes A1 differ from A2, which marks the entire leaf runtime
generated, which excludes the entire system prompt from the content report. The content check exists
to answer "was a system prompt or tool definition updated". It excludes its own primary subject.

**Concrete failure.** `baseline_capture::_source_home` gives each probe its own HOME
(`.baseline-sources/<bundle_id>/<model>/<label>`), and each probe gets its own proxy port from
`allocate_port_pair`. Claude Code's system prompt embeds a per-session scratchpad path and the
run's working environment. A1 and A2 therefore differ at `/system/0/text`. That pointer joins
`runtime_generated_pointers`. Claude Code 2.2 rewrites half the system prompt. `compare_content`
reports nothing at that pointer, forever, on every harness version.

**Second failure, the container digest.** `RequestJsonNode.sha256` is computed for every node
including containers, so the digest at `""` (root) differs A1 versus A2 whenever any leaf does. If
`runtime_generated_pointers` is minted by the plain rule "A1 digest != A2 digest" the set contains
the root, and any subtree exclusion built on `_covers` then excludes the whole document. The current
`baseline_evidence::_repeat_a_outcome` avoids this by skipping nodes whose kinds are `array` or
`object`; the design's replacement drops that rule without naming it.

**Fix.** Two changes. First, restrict `runtime_generated_pointers` to non-container nodes explicitly,
and say so in the design. Second, reuse `session/wire_normalization::mask_cross_launch_body` in the
content path, which is the existing substring-level answer to this exact problem: it already masks
run id, run name, runtime home, proxy URL, inspector URL, `<cwd>`, `<timezone>`, `<current_date>`,
"Today's date is", the scratchpad directory line, the `gitStatus` block and recent commit lines,
while deliberately preserving the Claude billing build suffix. `baseline_evidence::classify_aba`
already applies it to the raw body. Compare masked leaf values, and keep pointer-level exclusion only
for leaves that stay volatile after masking.

## B3. Recursive minting into `tools[].input_schema` makes a tool-definition edit gate, which is the defect that killed the last attempt

**Claim under attack.** `mint_request_schema` is "a recursive observed JSON Schema" with
`additionalProperties: false` at every object node, and the structure verdict gates.

**Why that is wrong.** `tools[].input_schema` (Anthropic) is itself a JSON Schema authored by the
harness. Minting recursively means TM mints a schema of that schema and gates on it. The owner's
table says the content check, "was a system prompt or tool definition updated", never gates. Under
this design a tool definition edit produces a structural verdict.

**Concrete failure.** Claude Code adds an optional `timeout` property to the Bash tool's
`input_schema`. Candidate gains `/tools/items/properties/input_schema/properties/properties/properties/timeout`.
Rule: "candidate has a property the reference lacks" -> `DEGRADED` -> `promotes_baseline` returns
False -> `baseline_harvest.main` exits 1. A pure content change has gated. This is the same shape as
the four rev3 blockers: something that is not the harness's request contract reaches the verdict.
It will fire on essentially every harness release, because tool schemas change more often than
envelopes do.

**Also opaque and unlisted:** provider `metadata` bags, `tool_use.input` (arbitrary per-call user
data), `function_call.arguments` (JSON encoded inside a string, so its shape is invisible to the
walker anyway), and `reasoning.encrypted_content`.

**Fix.** The structure walker needs a notion of opaque subtrees: positions where minting records
`type` and stops recursing, leaving the subtree to the content report. Derive the boundary from
per-provider raw pointer knowledge that already exists rather than a new hand table:
`request_inventory::_provider_semantics` already classifies raw pointers per provider without
touching the IR (it takes a pointer and the decoded body). If the design prefers not to reuse a
section vocabulary whose names read IR-flavoured, state the opaque set explicitly in the design and
test it; do not leave it unstated.

# MAJORS

## M4. The verdict table is not total, and one of the gaps hides a retype

**Claim under attack.** Six rows: identical, new property, strict superset type set, required
property absent, disjoint type sets, does not parse.

**Why that is wrong.** The real lattice at a node is the cross product of presence
(both / reference only / candidate only), requiredness (required / optional, each side), and the
relation between type sets (equal / strict subset / strict superset / disjoint / overlapping and
neither). The table covers five points of that space and leaves the rest with no verdict. A walker
implemented from this table will fall through to `EXACT` for every uncovered case.

**Concrete failure.** Reference `/metadata/user_id` observed as `{"string", "null"}` (one probe sent
null). A new harness version sends an object there: candidate `{"object", "null"}`. Not a strict
superset. Not disjoint, because `null` is common. No row matches. Verdict `EXACT`. A retype of a
field TM reads passed the gate because both versions could also send null.

**Second gap.** Reference `{"string", "array"}` for `/system`, candidate `{"array"}` only. Strict
subset, no row, `EXACT`. That is the harness narrowing a field TM's parser branches on.

**Fix.** Replace the two type-set rows with elementwise set arithmetic, which is total by
construction: any type name in candidate and absent from reference -> `DEGRADED`; any type name in
reference and absent from candidate -> record the finding, do not gate; empty intersection ->
`BREAKING`. Then enumerate the presence and requiredness product explicitly. There is precedent in
this repo for proving totality by test rather than by prose: `test_json_tags_totality`, and the
parametrised sweeps in `test_baseline_comparator_invariants`.

## M5. `StructureVerdict` and `DriftOutcome` are the same enum declared twice, and the prescribed `_covers` reuse inverts the layering

**Claim under attack.** `request_schema.py` is a "top-level leaf" that "knows nothing about
baselines, probes or the IR"; it returns `StructureVerdict`; separately `DriftOutcome` becomes
exactly `EXACT` / `DEGRADED` / `BREAKING`. The Reuse Map lists `baseline_evidence::_covers` as
**Reuse**.

**Why that is wrong.** Two enums with identical members in two modules is the duplication this repo
does not tolerate, and it forces a translation function between them at the one call site. Worse,
`baseline_evidence` must import `request_schema` to call `compare_request_schema`, so
`request_schema` importing `_covers` from `baseline_evidence` is an import cycle. `_covers` is also
private, and the Reuse Map does not say who promotes it.

**Concrete failure.** The implementer writes `from transport_matters.baseline_evidence import _covers`
in `request_schema.py`, `baseline_evidence` imports `mint_request_schema`, and the module graph
cycles at import time. The fallback is a second local copy of `_covers`, which is the duplication the
map was written to prevent.

**Fix.** One enum, declared in the leaf, imported by `baseline_evidence`. `_covers` moves to the
same pure pointer leaf beside `request_inventory::_pointer` and `_pointer_tokens` as a public symbol,
and `baseline_evidence` imports it from there. This is the shape the codebase already uses for
cross-layer leaves (`canonicalization`, `json_tags`, both declared as layer 1).

## M6. Deleting `INSUFFICIENT` removes the only answer for "these two bundles are not comparable", with no replacement

**Claim under attack.** "`COMPATIBLE` and `INSUFFICIENT` are deleted."

**Why that is wrong.** `baseline_evidence::compare_baseline_bundles` returns `INSUFFICIENT` in its
first branch when the cell coordinates or the controlled prompt plans differ. That is not a drift
verdict, it is a refusal, and the new three-member vocabulary has no member that can carry it.
`EXACT` would be a lie, `BREAKING` would be a false alarm, `DEGRADED` would silently not promote for
a reason that has nothing to do with the harness.

**Concrete failure.** A maintainer runs the harvester with `--prompt-a` changed. The comparison
returns `DEGRADED` or `EXACT` depending on what the implementer picks; either way the artifact
records a drift verdict for two captures that were never comparable.

**Fix.** Refuse rather than classify, and reuse the shape that already exists:
`baseline_capture::harvest_controlled_baseline` already raises `ValueError` when
`reference.prompts != prompts` (commit `afe74039`, "refuse a plan the reference lacks"). Move the
cell-coordinate check to the same refusal path so `compare_baseline_bundles` is total over comparable
inputs and undefined over incomparable ones. Then the three-member enum is honest.

## M7. The bundle records none of the launch conditions that shape the request, so TM's own configuration can still reach the gate

**Claim under attack.** The design treats "TM ink" as a payload problem, solved by minting from raw
bytes.

**Why that is wrong.** The raw body is genuinely clean today: `request_pipeline` captures
`decoded_http_body_bytes(flow.request)` before `run_pipeline`, and correlation rides
`launch_delivery_fields` (a prompt digest and a UUID held outside the body), so no TM identifier is
injected. The leak vector is upstream of the body. `baseline_capture::_capture_probe` launches with
`no_system_prompt=True`, `bypass_permissions=True`, `launch_kind=SERVICE`, a bare per-probe HOME, and
`control_plane_grants=capture_dependencies.control_plane_grants`. Every one of those changes what the
harness sends. `BaselineCell` records harness, provider, harness_version, launch_model, wire_model,
request_shape. It records none of the conditions.

**Concrete failure.** `captured/invocations.py` writes `.mcp.json` into the runtime home when
`control_plane_granted`. `baseline_harvest.main` calls `default_claude_run_dependencies()` with no
arguments, so grants are `None` today and no MCP config is written. `capture_rpc` and `main.py` pass
a real `services.grant_store`. The moment a baseline is harvested through a granted path, TM's own
MCP tool definitions land in `tools[]` and become the reference schema. The next ungranted harvest
loses them: `/tools/items` required keys change and tool shapes disappear. Verdict `BREAKING`,
attributed to the harness, caused entirely by TM. That is precisely the rev3 defect class, relocated
from the payload to the launch conditions, and the artifact carries nothing that would let a
maintainer diagnose it.

**Fix.** Put the capture conditions in the cell (or a sibling `CapturePlan`), including
`no_system_prompt`, `bypass_permissions`, `control_plane_granted`, and whether a HOME was bare. Refuse
comparison when they differ, through the M6 refusal path. `source_commit` is already recorded and is
also not compared; decide explicitly whether a TM commit change invalidates comparability.

## M8. `EXACT`-only promotion with `DEGRADED` for any new field leaves the store with no forward door

**Claim under attack.** "`promotes_baseline` becomes `reference_outcome is None or reference_outcome
is EXACT`."

**Why that is wrong.** Every real harness release adds fields. Under the new rules every such
release is `DEGRADED`, which does not promote, so the current pointer stays pinned to the first
capture ever taken. The next capture compares against that same ancient reference and is `DEGRADED`
again, permanently, and `baseline_harvest.main` returns 1 every time. The old vocabulary had a
release valve in `COMPATIBLE`; the new one has none, and the design does not name what replaces it.

**Concrete failure.** Bootstrap on Claude Code 2.1.0. 2.1.1 adds one optional envelope field:
`DEGRADED`, exit 1, pointer unchanged. 2.1.2 through 2.4.0 each report the same accumulated
`DEGRADED` against 2.1.0, and the diff a maintainer reads grows monotonically less informative. The
only way out is deleting the current pointer file by hand.

**Fix.** The owner ruled that `DEGRADED` does not auto-promote, which is right. The design still owes
the operator path: an explicit accept step (a harvester flag, or a separate promote command) that
writes the current pointer for a reviewed `DEGRADED` bundle and records who accepted it. Without it
the gate jams closed on first contact with a real release cadence.

## M9. `mint_request_schema` has no representation for a position observed with two container kinds

**Claim under attack.** The node rules are given as three disjoint cases: object, array, scalar, and
"`type` is the sorted set of observed JSON type names" appears only under scalar.

**Why that is wrong.** The union at one position can span containers. Anthropic `system` is a bare
string in some harness versions and an array of blocks in others. Anthropic message `content` is a
string for a simple user turn and an array of blocks otherwise; the array collapse puts both at
`/messages/items/properties/content`. The design's node model cannot express "string or array here",
so minting either crashes, silently keeps the first shape, or silently keeps the last.

**Concrete failure.** One capture where the probe A body sends `content` as a string and probe B
sends it as a one-element array. Whichever branch is written first wins, and the reference schema
records a shape that half the observations contradict. Every later comparison inherits the error.

**Fix.** One node type: a set of observed JSON type names plus optional `properties` and `required`
(populated when `object` is observed) plus optional `items` (populated when `array` is observed).
Reuse `json_tags::json_kind` for the names, as the Reuse Map already says. Make the union operation
total over the six kinds and test it that way.

## M10. `required` over three probes is two independent conditions in a first-turn-only cell, and the artifact is labelled as a JSON Schema

**Claim under attack.** "`required` is the keys present in every observation of that node", presented
as a JSON Schema with `additionalProperties: false`.

**Why that is wrong.** The three probes are A1, B, A2 over two distinct prompts, and A1 and A2 are
deliberately replicates: the design's own `runtime_generated_pointers` depends on them being the same
stimulus. So `required` is minted over two independent conditions, both first-turn, both
`no_system_prompt`, both bare HOME, both bypass-permissions. `BaselineCell.request_shape` is
`Literal["first-turn"]`, which is the artifact admitting the domain.

**Concrete failure of the label.** A maintainer takes the published schema, which says
`additionalProperties: false` and `required: ["type", "text"]` on content blocks, and validates real
traffic against it. Every second-turn request fails, because `tool_use` and `tool_result` blocks were
never observed. The schema was never wrong; the word `required` in a JSON Schema means "the API
requires this", and here it means "present in both conditions of one controlled first-turn capture".

**Concrete failure of the value.** `cache_control` on a first-turn message is present in all three
probes and therefore required. A harness release that sets `cache_control` only above a token
threshold drops it from a short controlled prompt. Verdict `BREAKING` for a field the provider
documents as optional.

**Fix.** Do not overstate: carry `observation_count` and per-node presence counts in the artifact so
the evidence is readable, keep `request_shape` visible next to the schema, and name the internal
field for what it measures (`present_in_every_observation`) even if the exported JSON Schema
projection spells it `required`. Say in the design that the artifact is valid for the controlled cell
only.

## M11. The structure check is body-only, so the most common real harness change is invisible

**Claim under attack.** "Did the shape of the request change" answered by a schema over the request
body.

**Why that is wrong.** A harness changes its request by adding an `anthropic-beta` header, changing
the endpoint path, adding a query parameter, or switching content encoding at least as often as it
changes the body. None of that is in the body. `ProbeEvidence` persists `raw_request_base64`,
inventory, nodes, normalized request and transcripts, and no headers, even though
`request_pipeline::capture_request_flow_state` already captures `original_headers` through
`capture_http_request_artifacts` and the transport snapshot is derived by `derive_http_transport`.
Note also that `decoded_http_body_bytes` has already decoded content encoding, so the "raw wire body"
is post-decode by construction.

**Concrete failure.** Claude Code 2.2 ships `anthropic-beta: context-1m-2025-08-07` and sends a
byte-identical body. Verdict `EXACT`. Baseline promotes. TM's upstream forwarding, token accounting
and model assumptions are all now operating under a beta contract nobody recorded.

**Fix.** Either state explicitly in the design that headers and target are out of scope for #382 and
open the follow-up, or extend `ProbeEvidence` with the captured request headers and target, and mint
a second small schema over the header name set with the same three verdicts. Do not leave it
unmentioned; a reader of this design will believe request drift is covered.

## M12. Missed reuse: the discriminated per-item structural diff already exists in this repo

**Claim under attack.** The Reuse Map row "JSON Schema over a request body -> none -> Genuinely new.
Confirmed absent from all of `api/src`", and the note that
`codex/request_parser::KNOWN_INPUT_ITEM_KEYS` is "a hand-maintained allowlist ... they answer
different questions and neither replaces the other".

**Why that is wrong.** The allowlist and the minted schema do answer different questions, so that
half is fair. What the map misses is the *mechanism*, which is not new:
`codex/request_parser::unknown_request_item_fields` already reads the exact raw request bytes,
already groups array elements by their `type` discriminator (with the documented fallback that a
role-only item is a `message`), already handles non-string and non-object tags through
`json_tags::literal_tag` and `json_kind`, and already emits findings under a stable
discriminator-keyed address, `input[<type>].<key>`. That is B1's fix, working, in this repo, over raw
bytes, today. The design instead invents an index-collapsing union that loses per-shape `required`.

**Second miss, in the Known Limitation.** "Content pointers keep concrete array indices, so
reordering tools reports as changes ... semantic identity for tools is provider-specific and is not
worth the coupling yet." The repo has already paid that coupling: `KNOWN_INPUT_ITEM_KEYS`,
`CODEX_REQUEST_TAG_SPINE`, `adapters/anthropic::KNOWN_REQUEST_EXTRA_KEYS`, and
`request_inventory::_anthropic_semantics` / `_codex_semantics` are all provider-specific raw-pointer
knowledge that already ships. Declining the coupling does not avoid it, it duplicates the concept in
a weaker form and accepts permanent report noise for a problem the repo already solved.

**Fix.** Mint array sub-schemas per discriminator token using `json_tags::record_type_token`, and
address content findings by discriminator plus stable key rather than by array index. Then the
"Known Limitation" section can be deleted rather than accepted.

# MINORS

## m13. `artifact_schema_version` 2 -> 3 is three literals and one of the readers raises rather than re-bootstraps

`BaselineBundle.artifact_schema_version` is `Literal[2]`, `baseline_capture` passes `2` positionally
at construction, `baseline_store::write_baseline_bundle` writes a separate hardcoded
`"artifact_schema_version": 2` into the current pointer, and `read_current_baseline` and
`read_baseline_bundle` each compare against a literal `2`. The design says "2 becomes 3" as if it
were one number. Also, "the store already hard-rejects a foreign version with regenerate the
baseline" understates the behaviour: `read_current_baseline` raises `ValueError`, and
`harvest_controlled_baseline` calls it before capturing anything, so an existing v2 store makes the
harvester die at startup rather than bootstrap a fresh v3 baseline. **Fix:** one named constant for
the artifact version, one for the pointer version if they are allowed to differ, and either delete
the stale pointer on a version mismatch or state that regeneration is a manual step with the exact
command.

## m14. `compare_content` does not say whose `runtime_generated_pointers` it excludes, and the two halves of the artifact address nodes differently

The reference bundle and the candidate bundle each mint their own set. Excluding only the candidate's
lets a pointer that was volatile in the reference and coincidentally stable in the candidate leak
into the report. Use the union, and say so. Separately, structure addresses nodes by collapsed path
while content addresses them by concrete index, so no finding from one half can be joined to the
other; a reader who sees `DEGRADED` at `/tools/items/properties/foo` cannot mechanically find the
content lines for it.

## m15. `BaselineComparison.unresolved_pointers` and its validators become dead state, and the CLI prints them

With `INSUFFICIENT` deleted there is no producer for `unresolved_pointers`, yet
`BaselineBundle.reference_unresolved_pointers`, the validator "only insufficient comparisons may have
unresolved pointers", the validator "bootstrap bundle reference outcome must be insufficient
evidence", and the `diagnostics` branch in `baseline_harvest.main` that formats them all still exist.
The design changes two of these implicitly and does not mention the CLI at all. Name the full blast
radius: `baseline_evidence` validators, `baseline_store::promotes_baseline`,
`baseline_harvest.main` diagnostics and exit code, and `test_baseline_comparator_invariants`.

## m16. A1 versus A2 misses low-entropy runtime values and cannot classify anything that only probe B sends

Two residual gaps beyond B2. First, a runtime-generated value with low entropy (a counter that is 0
in both A probes, an hour-truncated timestamp, a boolean) compares equal and is reported as stable
content forever. Second, a pointer present only in probe B has A1 absent and A2 absent, so the A1/A2
leg says "stable" about a field it never observed; the current
`baseline_evidence::_repeat_a_outcome` has the same hole. Neither is fatal, both belong in the design
as stated limits of the method rather than as silent behaviour.

# Verified, no finding

- `raw_request` is genuinely pre-pipeline: `request_pipeline` captures
  `decoded_http_body_bytes(flow.request)` before `run_pipeline`, and
  `exchange_recorder::build_request_artifacts` persists that byte string as `request_raw` while the
  curated bytes go to a separate `request_curated_raw`. The design's premise that
  `ProbeEvidence.raw_request_base64` is harness-authored holds.
- Correlation adds nothing to the body: `controlplane/envelope::launch_delivery_fields` carries a
  UUID and a prompt digest as launch fields, and `extract_delivery_id` recovers the delivery by
  matching a prompt digest against message text. No TM identifier is injected into the request.
- `no_system_prompt=True` does suppress TM's own `--append-system-prompt` injection
  (`cli/explicit_proxy`), so TM's identity block is absent from baseline captures.
- Deleting `ProbeEvidence.normalized_request` is safe. Its only readers are
  `baseline_capture::_build_probe_evidence` (the producer) and `test_baseline_evidence`. No web,
  CLI or store consumer reads it. The cross-launch masking it carried is independently applied to
  the raw body inside `classify_aba`, so nothing is lost.
