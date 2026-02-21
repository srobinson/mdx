---
title: Manicure Inspect tab — message-block index-shift cascade bug
date: 2026-04-17
branch: feat/inspect-diffs
kind: research
---

# Summary

`detectMessageMutations` in `www/src/components/detail/mutations.ts:131` pairs original and curated content blocks by raw array index. The server pipeline at `api/src/manicure/overrides.py` does not mask-then-send; it **pops** blocks (`_apply_message_block_toggle`, lines 300-318) and **drops whole messages** that go empty (`_sanitize_curated_messages`, lines 491-551). Every block downstream of a drop therefore shifts left in the curated array, which the detector sees as a cascade of edits whose "curated" side is the *next* original's content. The authoritative fix is to stop diffing structurally and drive the mutation set from `pipeline.overrides_applied` (the audit), which already records originals-indexed targets and deterministic priority order.

# Key findings

## 1. Root cause confirmed, file:line

- Detector pairs by raw index: `mutations.ts:160` (`paired = Math.min(origBlocks.length, curatedBlocks.length)`), then `mutations.ts:162-175`.
- Server pops blocks on toggle: `overrides.py:313-315` (`new_content.pop(blk_idx)`).
- Server applies overrides in **deterministic** priority order: `overrides.py:46-56` (`_PRIORITY`); `message_block_toggle` = 6, `message_text` = 7 — toggles always run before text edits.
- Server adjusts *subsequent* overrides' block indices via `_adjust_blk_index` (`overrides.py:562-574`), but the client never sees this map and recomputes a (wrong) one by index pairing.
- Server drops emptied messages: `overrides.py:548-550`.
- Persisted audit is ground truth: `api/src/manicure/addon.py:291` (`overrides_applied=list(audit.entries)`) → written via `ExchangeArtifacts` → surfaced to the UI as `detail.entry.pipeline.overrides_applied` (`www/src/types.ts:187`, `www/src/components/detail/ExchangeCard.tsx:190`).

## 2. Screenshot math reproduces the bug exactly

Given the five rows the UI shows (message originally had 5 blocks):

- orig sizes: ~388, 2763, 5540, 6347, 6299, plus a small trailing block; but the UI renders 5 originals with sizes 388 / 2763 / 5540 / 6299 / ("Hi" 27 as trailing disabled block).
- The detector pairs `min(5, curated.length=4) = 4` and compares:
  - i=0: 388 vs curated[0]=2763  → "edited" (curated text = orig[1])
  - i=1: 2763 vs curated[1]=5540 → "edited" (curated text = orig[2])
  - i=2: 5540 vs curated[2]=6347 → "edited" (curated text = orig[3])
  - i=3: 6299 vs curated[3]=27   → "edited" (curated text = orig[4] = "Hi")
  - i=4: 4>=paired              → "disabled"
- That gives 4 edits + 1 disabled = **5 MODIFIED**, which matches the header exactly.

Inferred underlying edit: **one block was disabled** (orig[0] — a `SessionStart:startup hook success` system-reminder) by the user. Every subsequent row is a false positive. The user's "only edited 3" claim is consistent with a single toggle-off plus two genuine text edits further down, but we cannot recover which are real from the current synthesized overrides — the real server audit can.

## 3. `detectSystemPartMutations` has the same class of bug in principle

- `_apply_system_part_toggle` also pops: `overrides.py:219-231`.
- `detectSystemPartMutations` (`mutations.ts:20-51`) pairs by raw index, same pattern.
- In practice system parts rarely get dropped (the editor mostly edits rather than toggles them off), but an `enable: false` override on any non-tail system index will cascade the same way. **Must be reworked with the same audit-driven approach.**

## 4. `detectToolMutations` is immune

- Pairs by `name`, not index: `mutations.ts:75` (`new Map(curatedTools.map((t) => [t.name, t]))`). Tool identity is stable across pops, so renaming is impossible and disables surface as missing names. No change needed.

## 5. Edge cases

- **Passthrough (no audit)**: `addon.py:542` persists `request_curated_ir=curated_ir if curated_ir != ir else None`. When there is no override store activity and no manual edit, `request_curated_ir` is `None` and the client has nothing to diff. InspectTab already handles this (`InspectTab.tsx:107`, `const baseRequest = originalRequest ?? curatedRequest`). **No diff required in this case.**
- **Bypass on (`store.enabled == False`)**: `addon.py:118-119` returns `(ir, None)`; no audit; `curated == ir` so `request_curated_ir=None` again. Same handling.
- **Manual edit at breakpoint (`mutated_manually: true`)**: `_resolve_paused_flow` (`addon.py:131-141`) returns `pf.mutated_ir` when it structurally diverges from `pf.curated_ir`. The mutation **does not produce audit entries** — the audit is computed from the store's overrides in `_run_pipeline` *before* the pause, and never re-run after the breakpoint edit. So the audit reflects pipeline intent, not the actual final IR. Manual edits are an audit blind spot: the client must still fall back to structural diff for these rows.
- **`truncate_tool_result`**: `overrides.py:249-297` *does* mutate text content (replaces tool-result text in place). Audit entry has `kind=truncate_tool_result`, `target=toolresult:{id}`. Detector currently never flags it (tool-result blocks are non-text — `blockTextIfText` returns `undefined`, skip). Should be surfaced as a modified block in the Inspect tab to match the other content mutations, but it will **not** cascade because it neither adds nor removes blocks, only shrinks text.
- **Whole-message drop**: audit records the `message_block_toggle` entries that caused the message to empty out. Sanitization (`overrides.py:548-550`) is a derived consequence; no audit entry for the message drop itself. Detector must compute the message drop from summing the per-block drops against original message content.
- **Orphan tool-pair sanitization**: `_sanitize_curated_messages` (`overrides.py:532-547`) also drops tool_use/tool_result halves whose twin went missing. Any surviving-half case implies a bug in the editor's pair-tandem wrapping (`MessagesSection.tsx:68-92`), but defensive handling in the detector is cheap — treat orphan sanitizations as additional disables, deriving them from the `use_ids`/`result_ids` pair set.

# Recommended fix

## Algorithm (client-side, audit-first)

```
function detectMessageMutationsFromAudit(
  original, curated, auditEntries, mutatedManually
):
  if !auditEntries:
    # Passthrough OR manual-only edit. Manual edits skip the audit (see
    # edge cases). Structural diff is fallback, but the pop-cascade only
    # bites when blocks are dropped. Manual editing in the breakpoint
    # editor currently cannot drop blocks structurally (only toggle =
    # which goes through overrides, which go through the audit before
    # pause), so the surviving case is "text edits only, no shifts" —
    # index pairing is safe.
    return legacyDetectMessageMutations(original, curated)

  # Compute original->curated block-index map by replaying toggles in
  # priority order. We only need block toggles (priority 6) since
  # nothing else changes block layout.
  shiftMap = Map<(msgIdx, blkIdx), { curatedMsgIdx, curatedBlkIdx } | "dropped">
  droppedPerMsg = Map<msgIdx, Set<blkIdx>>

  sortedToggles = auditEntries
    .filter(e => e.kind === "message_block_toggle" && e.applied)
    # Apply order is deterministic by (_PRIORITY[kind], originalOrder).
    # All message_block_toggles share priority 6, so original order wins.
    # We must replay in that same order to reproduce the pop.
    .preserveOriginalOrder()

  for e in sortedToggles:
    (m, b) = parseTarget(e.target)  # "msg:M:blk:B"
    droppedPerMsg.getOrCreate(m).add(b)

  # Now derive surviving-message index shifts from whole-message drops
  # (sanitization). Need the original message to know if all blocks went.
  droppedMessages = Set<msgIdx>
  for (m, dropped) in droppedPerMsg:
    if dropped.size == original.messages[m].content.length:
      droppedMessages.add(m)
    # Also include messages where remaining blocks are all orphaned
    # tool halves or empty-text — but this requires a second pass that
    # mirrors _sanitize_curated_messages. If we can't prove, leave to
    # structural fallback.

  curatedMsgIdxFor = (m: number): number | "dropped" =>
    if droppedMessages.has(m): return "dropped"
    return m - count(m' < m : droppedMessages.has(m'))

  curatedBlkIdxFor = (m, b): number | "dropped" =>
    if droppedPerMsg.get(m).has(b): return "dropped"
    return b - count(b' < b : droppedPerMsg.get(m).has(b'))

  mutations = []

  # 1. Every applied toggle becomes a "disabled" mutation at the
  #    ORIGINAL (M, B). The detail view renders against original blocks
  #    (InspectTab.tsx:110) so no index translation is needed for the
  #    target string — it is already "msg:M:blk:B".
  for e in auditEntries where e.kind === "message_block_toggle" && e.applied:
    (m, b) = parseTarget(e.target)
    mutations.push({ msgIdx: m, blkIdx: b, kind: "disabled" })

  # 2. For message_text overrides, we know the original target and the
  #    curated slot where the replacement landed. The audit does NOT
  #    carry the curated text, so we must look it up in curated IR:
  for e in auditEntries where e.kind === "message_text" && e.applied:
    (m, b) = parseTarget(e.target)
    mPrime = curatedMsgIdxFor(m)
    bPrime = curatedBlkIdxFor(m, b)
    if mPrime === "dropped" || bPrime === "dropped":
      continue  # shouldn't happen: a text edit on a dropped block
                # wouldn't be marked applied=true
    curatedBlock = curated.messages[mPrime]?.content[bPrime]
    curatedText = (curatedBlock?.type === "text") ? curatedBlock.text : undefined
    if curatedText !== undefined:
      mutations.push({ msgIdx: m, blkIdx: b, kind: "edited", curatedText })

  # 3. truncate_tool_result: locate the tool_result block in ORIGINAL
  #    by tool_use_id to emit a synthesised mutation. We need a new
  #    SystemSection/MessagesSection override kind or an InspectTab-
  #    local treatment because the existing message_text path targets
  #    text blocks. Easiest: render the truncation as a new row-level
  #    "modified" treatment that diffs block content. Defer surfacing
  #    until the cascade fix lands — out of scope for MVP.

  # 4. Manual-edit fallback: if mutatedManually, run legacy structural
  #    diff on top of the audit-derived mutations AND merge, preferring
  #    audit-derived where they exist. Manual edits can only change
  #    TEXT, not structure, so the cascade doesn't apply — index pairing
  #    is safe here.

  return mutations
```

Replace `detectMessageMutations` with the audit-first version and keep the legacy structural variant as a private `legacyDetectMessageMutations` (rename + unexport) used only as the passthrough/manual fallback. Thread `pipeline.overrides_applied` and `entry.mutated_manually` from `InspectTab.tsx` down to `buildSyntheticOverrides`.

Do the same rework for `detectSystemPartMutations` using `system_part_toggle` / `system_part_text` audit entries and `_adjust_system_index` logic (`overrides.py:557-559`).

## Index resolution summary

`(M, B) original → (M', B') curated` is:

1. `M' = M - (count of whole messages dropped before M)`.
2. `B' = B - (count of blocks in message M that were dropped before B)`.
3. Either yields `"dropped"` if `M` itself was emptied or `B` itself was toggled off. "Emptied" means every applied block toggle in message M exhausted the original content.

This mirrors `_adjust_system_index` (`overrides.py:557-559`) and `_adjust_blk_index` (`overrides.py:562-574`) one-for-one — the client is replaying what the server already did.

## Edge-case behaviour table

| Case | Audit present? | Behaviour |
|---|---|---|
| Pure passthrough (no overrides, no manual) | No | `request_curated_ir` is null. Nothing to diff. |
| Bypass mode | No | Same as passthrough. |
| Override-only mutation | Yes | Audit drives all mutation detection. No structural diff. |
| Manual-only (no overrides) | No (store empty) | Structural diff fallback. Text-only edits are safe against index pairing. |
| Override + manual edit on top | Yes (for override half only) | Audit covers overrides. Structural diff on top of the *curated-post-override* baseline would be needed to pick up manual edits — **this is a pre-existing gap**; see recommendation below. |
| `truncate_tool_result` applied | Yes | Defer: current UI has no surface for truncated tool-result diff. Flag as TODO; fix cascades first. |

## Server-side changes: recommended but optional

Two server-side improvements would make the client trivially correct and should be considered:

1. **Carry curated value in `OverrideAuditEntry`**: add `curated_value: str | None` populated after apply for `message_text`, `system_part_text`, `tool_description`, and `truncate_tool_result`. This removes the client-side need to walk `shiftMap` to look up curated text and closes the manual-edit gap implicitly (any post-audit mutation shows as an extra diff against a cached `curated_before_manual`). Cost: marginal audit-entry size growth; benefit: removes a whole class of bugs from any future frontend surface that wants to render the diff.
2. **Persist a second audit after `_resolve_paused_flow`**: when `mutated_manually==True`, re-run `apply_overrides([], pf.curated_ir)` against `pf.mutated_ir` as structural diff and append the resulting entries to `audit.entries`. This unifies manual-edit detection into the same data path. Out of scope for this fix, but worth a follow-up ticket.

If we take option 1, the fix collapses to: iterate audit entries, emit mutations using `curated_value` directly, no shiftMap needed. Smaller client patch, no risk of replay drift.

# Confidence assessment

- **High confidence**: root cause (audit-verified pops + index-pair detector), `detectToolMutations` immunity, `detectSystemPartMutations` same-class vulnerability, screenshot-math reproduction.
- **High confidence**: the audit is sufficient for override-driven mutations given deterministic `_PRIORITY`.
- **Medium confidence**: manual-edit fallback behaviour — I have not exhaustively enumerated every path that could surface a `request_curated_ir` structurally different from `request_ir` without a store override (e.g., a future feature). Current code paths appear safe.
- **Low confidence / unexplored**: whether any of the UI rendering downstream of synthesised `Override[]` (specifically `MessagesSection` computing `modifiedCount` at `MessagesSection.tsx:109-115`) depends on the current false-positive behaviour. The fix must not regress the correct-case visualization. Suggest a `mutations.test.ts` suite that exercises the exact pop-cascade scenario from the screenshot before touching production code.

# Next steps, ranked by impact

1. Land the audit-driven rewrite of `detectMessageMutations` and `detectSystemPartMutations`; add regression tests covering "drop block 0 of a 5-block message" and "drop whole message 1 of 3".
2. Decide on server-side `curated_value` in `OverrideAuditEntry` (biggest long-term simplification). If yes, rewrite only emits mutations from audit; no replay needed.
3. Open a follow-up ticket for `truncate_tool_result` Inspect-tab surfacing once the cascade fix is in.
4. Open a follow-up for unifying manual-edit detection into the audit pipeline.

# Citations (file:line)

- `www/src/components/detail/mutations.ts:131-179` — buggy detector
- `www/src/components/detail/mutations.ts:20-51` — same-class bug in system-part detector
- `www/src/components/detail/mutations.ts:66-93` — tool detector (safe, immune)
- `www/src/components/detail/InspectTab.tsx:63-94` — synthesised-overrides producer
- `www/src/components/detail/InspectTab.tsx:107-114` — renders originals with synthesised overrides overlaid
- `www/src/components/editor/MessagesSection.tsx:109-115` — modifiedCount chip driven by override count
- `api/src/manicure/overrides.py:46-56` — deterministic apply priority
- `api/src/manicure/overrides.py:300-318` — block pop
- `api/src/manicure/overrides.py:463-485` — message-text index-adjust usage
- `api/src/manicure/overrides.py:491-551` — whole-message sanitization
- `api/src/manicure/overrides.py:557-574` — `_adjust_system_index`, `_adjust_blk_index` (mirror of what client must do)
- `api/src/manicure/overrides.py:121-143` — `OverrideAuditEntry` model (no curated value today)
- `api/src/manicure/addon.py:131-141` — `_resolve_paused_flow` manual-edit gap
- `api/src/manicure/addon.py:291` — audit entries persisted to `PipelineStats.overrides_applied`
- `api/src/manicure/addon.py:542` — `request_curated_ir` persisted only when different
- `api/src/manicure/storage/base.py:34-45` — `PipelineStats` schema
- `api/src/manicure/storage/base.py:80-89` — `ExchangeArtifacts` schema
- `www/src/types.ts:65-82` — `OverrideAuditEntry`, `OverrideAudit` TS shapes
- `www/src/types.ts:186-195` — `PipelineStats` TS shape (audit available to UI)
