---
title: am + cm vs context-mode snapshot-as-TOC gap analysis
type: research
tags: [helioy, attention-matters, context-matters, compaction, snapshot, mcp, context-mode, elv2]
summary: cm already emits runnable cx_recall/cx_get hints in recall trailers; the snapshot-as-TOC primitive lands as a new cx_snapshot tool plus a thin Helioy PreCompact hook. cx_change kind is not yet in the EntryKind enum.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## 1. Current compaction story

### What runs at PreCompact today

`/Users/alphab/Dev/LLM/DEV/helioy/helioy-plugins/plugins/helioy-tools/hooks/hooks.json:1-44` is the live plugin manifest. It registers `SessionStart`, `PostToolUse`, `Stop`, and an empty `SessionEnd`. There is no `PreCompact` entry. The widely-cited `am sync` PreCompact hook lives only in the draft at `helioy-plugins/plugins/helioy-tools/hooks/TMP/hooks.json:44-53` and is shadowed by a stray quote in the command string. It is not active.

The crew-level safety net at `helioy-plugins/plugins/helioy-tools/hooks/crew-precompact.sh:1-57` is wired only for helioy-crew coordinator agents via `agents/coordinator.md:8-12`. Comments at lines 5 and 39 assume a plugin-level PreCompact is doing `am sync`. Reality: nothing is. There is no global `/compact` integration today.

### What `am sync` actually does on PreCompact stdin

`attention-matters/crates/am-cli/src/sync.rs:32-56` defines `HookInput { session_id, transcript_path, hook_event_name }` and reads it from stdin. `extract_episodes` at `sync.rs:100-142` chunks the JSONL transcript into 5-exchange episodes and feeds them into `am_ingest`. This is the only existing wiring that touches the Claude Code transcript at compaction time, and it ingests prose, it does not produce a navigable snapshot.

### Closest existing analogues

| Need | Closest tool | Location | Shape |
|------|-------------|----------|-------|
| Batch persist conversation | `cx_deposit` | `cm-capabilities/src/deposit.rs` | Stores a structured exchange list |
| Substantive exchange capture | `am_buffer` | `am-cli` server | In-memory buffer, flushed at sync |
| Full state serialization (cm) | `cx_export` | `cm-capabilities/src/export.rs:77-116` | Pretty JSON: `{ entries, scopes, exported_at, count }` |
| Full state serialization (am) | `am_export` | `am-cli/src/server/system.rs:39-43` via `am_core::serde_compat::export_json` | v0.7.2 JSON of the entire DAE system |
| Two-phase progressive disclosure | `cx_recall` trailers | `cm-capabilities/src/projection/recall_view/trailers.rs:73-79` | Emits `# cx_get(id="...") for full bodies` and `# narrow: cx_recall(...)` lines |

The trailer at `recall_view/trailers.rs:79` is the most important precedent: cm already produces runnable MCP-tool-call placeholders inside its agent-facing output. The snapshot-TOC primitive is a generalization of that pattern, not a new invention.

## 2. Gap analysis

| Capability | Status | Notes |
|------------|--------|-------|
| Runnable tool-call placeholders in MCP output | partial, only in `cx_recall` trailers | `recall_view/trailers.rs:73-79`, `:97-106` already emit `cx_get(...)` and `cx_recall(...)` lines. No `am_query(...)` analogue. |
| XML-sectioned snapshot | missing | `cx_export` is JSON, `am_export` is JSON. Neither sections the output by topic. |
| Zero inline body (TOC, not summary) | partial in cm | `cx_get` trailer suppresses body when over `TOKEN_HINT_THRESHOLD = 1024` tokens (`trailers.rs:11`). `cx_export` and `am_export` still inline everything. |
| `cx_change` kind | missing | `cm-core/src/types/entry.rs:17-26` enumerates `Fact, Decision, Preference, Lesson, Reference, Feedback, Pattern, Observation`. No `Change`. SQL adapter at `cm-store/src/sqlite/entry.rs` follows the enum. |
| `/compact` global hook wiring | missing | `helioy-tools/hooks/hooks.json` has no `PreCompact`. Draft in `TMP/` is broken (trailing quote at line 49). |
| `am_snapshot` tool | missing | Surface in `am-cli/tools.toml` covers query, ingest, export, retrieve, salient, buffer, activate, feedback, batch, stats. No snapshot. |
| `cx_snapshot` tool | missing | Surface in `cm-cli/src/mcp/server.rs` covers recall, store, browse, get, deposit, update, forget, stats, export. No snapshot. |

Net: the convention is partly already lived inside cm. Generalizing it requires one new MCP tool per memory component plus a hook that calls them at PreCompact.

## 3. Where it lands

### Verdict: new `cx_snapshot` MCP tool, plus a thin Helioy hook that pairs it with `am_export`

Reasoning:

- cm owns structured project knowledge with stable IDs, scope paths, and recall semantics. A snapshot-TOC for cm is a list of section headers plus a runnable `cx_recall(...)` or `cx_get(id=...)` call per section. The trailer machinery at `cm-capabilities/src/projection/recall_view/trailers.rs:97-106` already knows how to emit those calls. Adding `cx_snapshot` reuses that primitive.
- am holds geometric memory keyed by occurrences and quaternions, which are not user-addressable identifiers. The right rehydration call for am is `am_query(text=...)`, not an id lookup. The snapshot section for an am topic is therefore a probe query, not an entry pointer. `am_export` already serializes the full state; a separate `am_snapshot` adds nothing structured beyond a list of probe queries.
- Cross-component glue is one shell hook plus one skill. The hook receives the Claude Code PreCompact JSON payload (`am-cli/src/sync.rs:32-40` shows the existing payload shape), invokes `cx_snapshot` for the active scope, optionally appends a small set of `am_query(...)` probes derived from session salient terms, and writes the XML-sectioned result to `~/.context-matters/snapshots/<session_id>.xml`. SessionStart on the next session reads it and the agent executes the embedded calls on demand.

The new tool surface, not the format, is what differs from `cx_export`. `cx_export` is byte-for-byte JSON for backup. `cx_snapshot` is XML-sectioned, agent-legible, and carries no inline bodies.

## 4. Adoption order

1. **Land `cx_change` in `EntryKind`.** Edit `cm-core/src/types/entry.rs:17-66` to add `Change` and its `as_str` / `FromStr` arms. Migrate the SQLite adapter at `cm-store/src/sqlite/entry.rs`. Without this, any snapshot that records "what changed in this session" has no canonical kind to file under and either pollutes `Fact` or leaks free-form tags.
2. **Agree the snapshot wire format.** XML-sectioned, one section per topic, each section ends in a single runnable MCP call. No prose summary, no inline bodies. Reuse the trailer-line shape from `recall_view/trailers.rs:97-106` so the format is byte-compatible with what `cx_recall` already emits.
3. **Add `cx_snapshot` capability and MCP tool.** New file `cm-capabilities/src/snapshot.rs` plus `cm-cli/src/mcp/tools/snapshot.rs`. Reuse `compute_drill_down_hint` and the trailer renderer.
4. **Wire the PreCompact hook.** Replace the broken stanza in `helioy-tools/hooks/TMP/hooks.json:44-53` and promote it into the live `hooks/hooks.json`. Hook script reads the PreCompact JSON, calls `cx_snapshot` and (optionally) emits a small set of `am_query(...)` probes from `am_salient`, writes the XML to a deterministic path keyed by `session_id`.
5. **Wire SessionStart restore advisory.** Extend the `SessionStart` line in `helioy-tools/hooks/hooks.json:5-10` to point the agent at the snapshot file when it exists, then let the agent execute the embedded calls on demand.

Step 1 is the only hard prerequisite. Steps 2 to 5 can proceed once the kind enum lands.

## 5. Verdict

**Adopt-now, gated on `cx_change`.** The recall trailer already proves the pattern works inside cm. The work is small, reuses existing primitives, and is the correct response to Claude Code compaction. Skipping it leaves Helioy with no global `/compact` story and a draft hook with a broken quote.

## 6. Concrete next steps

| File to touch | Change | Surface |
|---------------|--------|---------|
| `context-matters/crates/cm-core/src/types/entry.rs:17-66` | Add `Change` to `EntryKind` plus `as_str` / `FromStr` arms | core types |
| `context-matters/crates/cm-store/src/sqlite/entry.rs` | Mirror new kind in SQL adapter | store |
| `context-matters/crates/cm-capabilities/src/snapshot.rs` (new) | `SnapshotRequest`, `SnapshotView`, `snapshot()` function. Output is XML-sectioned text, each `<section>` ends in a single `cx_recall(...)` or `cx_get(id="...")` line | capability |
| `context-matters/crates/cm-cli/src/mcp/tools/snapshot.rs` (new) | MCP adapter mirroring `tools/export.rs` | tool surface |
| `context-matters/tools.toml` | New `[tools.cx_snapshot]` block | tool docs |
| `context-matters/crates/cm-cli/src/mcp/server.rs` | Dispatch `cx_snapshot` | router |
| `helioy-plugins/plugins/helioy-tools/hooks/hooks.json:1-44` | Add `PreCompact` array calling a new `compact-snapshot.sh` | hook |
| `helioy-plugins/plugins/helioy-tools/hooks/compact-snapshot.sh` (new) | Reads PreCompact stdin, calls `cx_snapshot`, optionally emits am probe lines, writes XML keyed by `session_id` | shell |
| `helioy-plugins/plugins/helioy-tools/hooks/hooks.json:5-10` | SessionStart message: point agent at snapshot file when present | hook |

MCP tool surface delta:

- New: `cx_snapshot(scope?: ScopeSelector, max_sections?: u32) -> { xml: string, sections: u32, generated_at: DateTime }`
- Unchanged: everything else.

Schema additions:

- `EntryKind::Change` (snake_case `change`) in `cm-core/src/types/entry.rs:17-26` and the SQL `as_str` / `FromStr` arms.

## 7. License note

context-mode is ELv2-licensed. No source from `mksglu/context-mode/src/session/snapshot.ts` may be copied into the Rust reimplementation. The convention being adopted is the snapshot-as-TOC pattern: XML-sectioned output with one runnable retrieval call per section, zero inline bodies. The Rust module header should carry one line of provenance:

```rust
//! Snapshot-as-TOC compaction primitive. Convention adopted from
//! mksglu/context-mode (ELv2). Independent reimplementation; no source lifted.
```

That is the only attribution required. Implementation reuses cm's own trailer renderer (`cm-capabilities/src/projection/recall_view/trailers.rs:97-106`) for the call-line shape, so the result is provably native code.
