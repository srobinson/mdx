# 592: Positional system and message overrides misapply on Codex continuation requests carrying previous_response_id

URL: https://github.com/littleorgans/transport-matters/issues/592
State: open
Labels: 
Updated: 2026-09-02T10:30:15Z

## Summary

System and message overrides are addressed by position. Codex continuation requests carry `previous_response_id` and contain only the new input for that turn, so their positions do not line up with the initial request the operator authored against. `run_pipeline` in `api/src/transport_matters/request_pipeline.py` applies every override in scope to every request, so a positional override authored on the first request rewrites the wrong item on every later one.

Observed live on branch `feat/overlay-registry`: a `message_text` override on `msg:0:blk:0`, authored against the full initial request where that block was the AGENTS.md instructions, matched the user's fresh prompt on the next request and replaced "Can you review the codebase" with the prior AGENTS.md text.

## Mechanism

- `message_block_target` and `system_target` in `api/src/transport_matters/overrides/targets.py` mint targets of the form `msg:{i}:blk:{j}` and `sys:{i}`. The inspector mints the same targets through `messageBlockTarget` in `www/packages/inspector/src/lib/overrideTargets.ts`, called from `BlockRow.tsx`, `MessagesSection.tsx`, `GlobalSection.tsx`, and `InspectTab.tsx`.
- `apply_overrides` in `api/src/transport_matters/overrides/__init__.py` dispatches the four positional kinds `system_part_toggle`, `system_part_text`, `message_block_toggle`, `message_text` to `ops_messages.py`, which resolves the index against whatever `ir.system` and `ir.messages` the current request happens to carry.
- On the WebSocket transport, only the first `response.create` frame carries the full context. Each later frame sets `previous_response_id` and sends only the delta. The HTTPS Responses fallback behaves the same way. `previous_response_id` reaches the IR through `provider_extras`, and `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS` in `api/src/transport_matters/request_extras.py` already names it as a continuation identity key.
- Tool overrides are unaffected. `tool_toggle` and `tool_description` match by tool name via `tool_target`, and `truncate_tool_result` matches by `tool_use_id` via `tool_result_target`.

## Reproduction with fresh captures

Run `dda34ad8-090a-4790-b78e-64a263595b7b`, captured 2026-09-02 on the preview channel. Codex `0.152.1`, model `gpt-5.6-sol`, WebSocket transport.

Capture root:

```
~/.transport-matters-preview/workspaces/dev-helioy-transport-matters/ecd9b0df/dda34ad8-090a-4790-b78e-64a263595b7b/
```

| exchange | `previous_response_id` | `sys:0` | `msg:0:blk:0` |
| --- | --- | --- | --- |
| `20260902T094637Z-69b93589` | absent | "You are Codex, an agent based on GPT-5…" | developer `additional_tools` item (see #369) |
| `20260902T094654Z-cfffac8f` | set | none | tool result |
| `20260902T094721Z-f84d914f` | set | `<skills_instructions>` developer message | user text "list your tm identity info" |

An operator who authors `system_part_text` on `sys:0` against exchange `69b93589` intends to edit the Codex base prompt. On exchange `f84d914f` the same target is the skills instructions block. An operator who authors `message_text` on `msg:0:blk:0` against `69b93589` hits the user's prompt on `f84d914f`. The pipeline applies both without any check.

Each exchange directory holds `request.ir.json` and `request.audit.json`. With overrides disabled, `request.audit.json` shows `entries: []` and equal before and after character counts, which is the baseline a regression test should hold for continuation requests carrying positional overrides.

## Code map

- `api/src/transport_matters/request_pipeline.py`: `run_pipeline`. Called from `api/src/transport_matters/addon_handlers.py` for both the HTTP and WebSocket request paths.
- `api/src/transport_matters/overrides/__init__.py`: `apply_overrides`, `_apply_override_value`, `_PRIORITY`.
- `api/src/transport_matters/overrides/ops_messages.py`: `apply_system_part_toggle`, `apply_system_part_text`, `apply_message_block_toggle`, `apply_message_text`, `codex_has_tool_result_only_turn`.
- `api/src/transport_matters/overrides/targets.py`: `system_target`, `message_block_target`, `parse_system_index`, `parse_message_target`, `adjust_system_index`, `adjust_blk_index`.
- `api/src/transport_matters/overrides/state.py`: override store and scope.
- `api/src/transport_matters/request_extras.py`: `CROSS_LAUNCH_STRIPPED_REQUEST_EXTRAS_KEYS`.
- `api/src/transport_matters/codex/request_parser.py`: `parse_codex_request` leaves `previous_response_id` in `provider_extras`.
- `www/packages/inspector/src/lib/overrideTargets.ts`: `messageBlockTarget`.

## Settled design: content anchored positional overrides

Position is not an identity. The Codex continuation is the loudest case, but `adjust_system_index` and `adjust_blk_index` in `targets.py` already exist because indices shift after removals inside one request, and overlays are saved as reusable bundles meant to apply across exchanges and runs where positions are never guaranteed. The fix is to resolve positional overrides by the content they were authored against, with the index kept as a hint.

Shapes compared:

| shape | what it does | verdict |
| --- | --- | --- |
| Drop positional kinds on continuation (branch `1d5c9b72`) | `run_pipeline` filters the four kinds when `previous_response_id` is set | Safe and small, but Codex specific, loses recurring block overlays, and fixes only this one drift. |
| Scope overrides by request shape | Record initial versus continuation at authoring time and apply only to the same shape | Continuation shapes vary (tool result only, user turn with developer message), so the rule stays positional inside each shape and still misfires. |
| Content anchor (chosen) | Each positional override carries a digest of the block it was authored against. Apply resolves by anchor. | Provider neutral. Survives continuations, removals, and reordering. A miss is explicit and audited. |

Design:

- `Override` in `api/src/transport_matters/overrides/__init__.py` gains `anchor: str | None`. For `system_part_toggle`, `system_part_text`, `message_block_toggle`, and `message_text` it is required and holds a short digest over role, block type, and original text. `SystemPart` and `TextBlock` are the only anchorable shapes, which matches what `apply_system_part_text` and `apply_message_text` accept today. The store boundary rejects a positional override without an anchor.
- One digest function, defined twice and pinned equal: `block_anchor` in `api/src/transport_matters/overrides/targets.py` and `blockAnchor` in `www/packages/core`. A shared fixture of blocks and expected digests is checked by a test on each side.
- The inspector computes the anchor where it mints the target, next to `messageBlockTarget` in `www/packages/inspector/src/lib/overrideTargets.ts`, called from `BlockRow.tsx`, `MessagesSection.tsx`, `GlobalSection.tsx`, and `InspectTab.tsx`. The block is already in hand, so nothing new crosses the wire at authoring time.
- One resolver in `api/src/transport_matters/overrides/ops_messages.py` replaces the four index lookups. Order: the block at the stored index whose anchor matches, then a unique anchor match anywhere in `ir.system` or `ir.messages`, then miss. The index stays as the fast path and as the tie breaker when a block recurs.
- A miss is recorded, never silent. `OverrideAuditEntry` in `api/src/transport_matters/overrides/audit.py` gains `reason: str | None`, set to `anchor_miss` when a positional override finds no block. `applied` stays false.
- No provider branch. `previous_response_id` never enters the pipeline. On a Codex continuation the base prompt anchor is absent and the skills block anchor is present, and the resolver does the right thing for both without knowing what a continuation is.
- No legacy path. The persisted bundles in `www/packages/inspector/src/stores/overlaysStore.ts` are the only durable copies and the overlay store is still pre-release. Anchorless positional entries are dropped on load with a console warning.

What this buys beyond this defect: a saved overlay becomes portable across runs, harness versions, and the initial versus continuation split, and the audit gives a truthful answer when a block the operator edited no longer exists. That is the property the overlay registry needs and cannot get from indices.

## Prior art, unmerged

Commit `1d5c9b72` on `feat/overlay-registry`. The branch is 144 commits behind `main`. Treat it as a design reference.

It added `_is_codex_continuation` to `request_pipeline.py`, which reads `previous_response_id` from `provider_extras` for `provider == "codex"`, and had `run_pipeline` drop the four positional kinds from the override list before calling `apply_overrides` on a continuation. Named tool overrides stayed eligible. It added `test_codex_continuation_does_not_replay_positional_overrides` to `test_request_pipeline.py`. Verification at the time: exact replay of the captured initial request applied all six intended text overrides, exact replay of the captured continuation applied zero positional overrides and preserved the user prompt byte for byte.

The branch shape is not the one to implement. It is Codex specific, it loses recurring block overlays such as the skills instructions message, and it leaves every other positional drift unaddressed. See the settled design below.

## Acceptance

- `Override` carries a required `anchor` for the four positional kinds. The store rejects a positional override without one.
- `block_anchor` and `blockAnchor` produce identical digests over a shared fixture, proven by a test on each side.
- Positional overrides resolve by anchor in `ops_messages.py` with index as hint. A miss produces an `OverrideAuditEntry` with `applied: false` and `reason: anchor_miss`. Nothing is rewritten on a miss.
- A regression test in `test_request_pipeline.py` replays exchange `69b93589` and exchange `f84d914f` from run `dda34ad8` with a `system_part_text` anchored to the Codex base prompt and a `message_text` anchored to the AGENTS.md block stored in scope. The initial request applies both. The continuation applies neither, audits two `anchor_miss` entries, and serializes byte identical to the capture.
- A second test authors a `system_part_text` anchored to the skills instructions block against exchange `f84d914f` and shows it applies on that continuation and misses on exchange `69b93589`.
- Tool overrides and `truncate_tool_result` are unchanged and still apply on continuations.
- Behaviour is identical on the WebSocket transport and the HTTPS Responses fallback, with no reference to `previous_response_id` anywhere in the override path.
- The inspector mints the anchor alongside every positional target and shows an audit miss where it shows applied overrides today.
- `overlaysStore.ts` drops anchorless positional entries on load with a console warning. No compatibility shim.


## Sub issues
[]
