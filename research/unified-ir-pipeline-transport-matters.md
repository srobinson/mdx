---
title: Unified IR for Claude + Codex transcripts in Transport Matters
type: research
tags: [transport-matters, ir, codex, claude, session-store, anti-corruption-layer, pipeline]
summary: Both providers normalize into one NormalizedTurn IR at parse; persist/read/render are provider-agnostic. Verdict unified-and-identical.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-16
updated: 2026-06-16
---

# Unified IR for Claude + Codex transcripts

## Executive Summary

Transport Matters has a **single** internal representation for session transcripts.
Both Claude and Codex normalize into one type, `NormalizedTurn`, at the parse
stage. The DB stores that unified IR, and the read + render paths carry no
provider conditionals. **Verdict: unified-and-identical.** Provider survives only
as a label value (`provider`/`cli` strings), never as a structural fork in the
rendered body kinds.

## Pipeline (parse → persist → read → render)

### 1. Parse — unification happens HERE
- IR type: `NormalizedTurn` (`api/.../index/adapters/base.py`). Field
  `parts: list[ContentBlock]` reuses the shared block union in
  `transport_matters/ir.py` (`TextBlock`, `ToolUseBlock`, `ToolResultBlock`,
  `ThinkingBlock`, `ImageBlock`, `UnknownBlock`).
- `TranscriptAdapter.normalize(record, ctx) -> NormalizedTurn | None`
  (`adapters/base.py`) is the anti-corruption layer; one subclass per CLI.
  - `ClaudeAdapter.normalize` (`adapters/claude.py`): parts via
    `_content_to_parts` / `_block` / `_tool_result_content`.
  - `CodexAdapter.normalize` (`adapters/codex.py`): parts via
    `_payload_to_role_and_parts` / `_message_parts` / `_function_call_block` /
    `_function_call_output_block` / `_reasoning_block`. Codex reasoning maps to
    the same `ThinkingBlock` as Claude thinking.
- Provider-specific native structure is **erased at parse**.

### 2. Persist — unified IR lands in the DB (normalize-before-write)
- `build_event` (`session/ingest.py`) sets
  `EventRow.ir = NormalizedTurn.model_dump(mode="json")` via `_turn_ir`, plus
  `raw=dict(record)` (native bytes retained but not the read contract).
- Non-conversational records (`normalize` returns `None`) → `_meta_event` with
  `kind=EventKind.META, ir=None`.
- Same row shape for both providers: `EventRow` / `EventReadRow`
  (`session/models.py`), generic `ir` JSON column.

### 3. Read/project — provider-agnostic
- `_event_body(row)` (`api/v1/session_models.py`) reads `row.ir` via `_ir_parts`,
  classifies body from part `type` + `row.kind`/`row.role` only:
  - tool_use part → `TranscriptToolUseBody`
  - tool_result part → `TranscriptToolResultBody`
  - `kind != "turn"` OR `role == "system"` → `TranscriptWireInjectedBody`
  - `role == "user"` → `TranscriptUserBody`
  - else → `TranscriptAssistantBody`
- No `provider`/`cli` read. The alternate `project_timeline`
  (`session/timeline.py`, via `_message_item`/`_meta_item`/`_parts`) is likewise
  keyed on `EventKind`, not provider.

### 4. Render — identical contract
- `mapIrToChat.ts` (`mapSessionEventToTranscriptMessage` / `bodyBlocks` /
  `mapWireInjectedEvent`) consumes `SessionEventView` and branches **only** on
  `event.kind` and `event.body.kind`. No provider field on the view.

## meta / wire_injected classification (provider-neutral)

- **meta** decided at INGEST: `build_event` → `turn is None` → `_meta_event`
  (`kind=META`). Whether a record is conversational is each adapter's `normalize`
  returning `None`:
  - Claude skips `type ∉ {user, assistant}` (`_CONVERSATIONAL`).
  - Codex skips `type != "response_item"` (comment: session_meta / turn_context /
    event_msg skipped).
- **wire_injected** decided at READ: `_event_body` maps `kind=="meta"` →
  `TranscriptWireInjectedBody(label="meta")` (empty parts; meta has
  `ir=None`/`search_text=None`).
- A Codex session's opening `session_meta` produces the **same** meta →
  wire_injected result as Claude's, through the **same** `build_event` /
  `_event_body` machinery. Only per-provider difference: the *set* of native
  record types each adapter treats as non-conversational, encapsulated inside
  `normalize` (the ACL), never leaking downstream.

## Key Pattern

Classic **anti-corruption layer**: provider divergence is confined to the
`TranscriptAdapter.normalize` boundary. Everything after the adapter (persist,
read projection, websocket stream, React render) speaks one vocabulary
(`NormalizedTurn` → `ir` JSON → `TranscriptEventView`/`SessionEventView` →
`ChatItem`). `provider`/`cli` ride along as metadata labels, not control flow.

## Skip / loss analysis (demote vs drop)

**Nothing conversational is silently lost.** Every well-formed JSON record
becomes either a turn or a meta event in the DB, and its native bytes are
preserved twice: in `EventRow.raw` and in the Tier-1 byte-faithful snapshot.
`normalize() -> None` is a **demote**, never a **drop**.

### Skip set per adapter
- **Claude** (`ClaudeAdapter.normalize`, `_CONVERSATIONAL = {"user","assistant"}`):
  None for any `type` ∉ {user, assistant}. Concrete types (test_claude
  `_normalize_fixture`): `system`, `ai-title`, `file-history-snapshot`,
  `summary`. Also None if a user/assistant record lacks a str `uuid`.
- **Codex** (`CodexAdapter.normalize`, only `type=="response_item"` survives):
  None for `session_meta`, `turn_context` (model threaded forward via
  `model_hint` → `ctx.model`, not lost), and `event_msg` (subtypes
  `agent_message` = streaming delta, `token_count` = usage telemetry).
  `event_msg` is duplicative — the durable assistant text lands in a
  `message(assistant)` response_item. Unmapped `response_item` payloads
  (`custom_tool_call`, `web_search_call`, text-less content) are captured as
  `UnknownBlock(raw=...)`, not dropped.

### Demoted, not dropped
`ingest_records` (`index/tailer.py`) calls `build_record` for **every** record
(no `if turn is None: continue`). `turn is None` → `_meta_event` →
`EventRow(kind=META, ir=None, raw=dict(record))`. Proven by
`test_tees_non_conversational_records_normalize_drops`: a `session_meta` record
submits as `("meta", "session_meta")` with the native record in `EventRow.raw`.

### Upstream filters (none lose recoverable content)
1. **Malformed JSON** — `iter_complete_records` skips unparseable lines
   (`_log.warning("skipping malformed transcript record")`); trailing
   half-written line deferred to next read.
2. **Resume anchor** — `skip_until_user_text`/`skip_until_seen` via
   `is_replay_anchor` skips pre-anchor records on resume (already persisted in
   the prior run; dedup, not loss).
3. **Quarantine** — batch INSERT failure → `quarantine_window`
   (`session/quarantine.py`, `DeadLetterWrite` in `session/models.py`) with
   `raw_excerpt` + byte range + error. Failure path, not a type drop.

### Safety net: Tier-1 snapshot tee
The snapshot tee captures the transcript byte-faithfully regardless of
normalize — `test_tailer` asserts `b"".join(tees) == path.read_bytes()` (whole
file, no gaps), coupled to cursor advance (tee failure retries). So even
malformed-JSON lines survive in the raw byte copy, and any record currently
demoted to meta can be re-derived if `normalize` changes later.

## DEFECT: Claude `attachment` content lost from v1-rendered transcript

Verified against 824 real transcripts / 68,171 attachment records.

`type:"attachment"` is a standalone top-level Claude record (`parentUuid:null`, no
`message`), with an `attachment:{type,...}` payload. It is ∉
`ClaudeAdapter._CONVERSATIONAL` → `normalize` returns None → `_meta_event` →
`EventRow(kind=META, ir=None, raw=dict(record))`. Content lives **only** in
`EventRow.raw`.

**27 subtypes; most are framing (correctly meta):** output_style (47,160),
task_reminder (6,399), hook_success (5,562), command_permissions,
deferred_tools_delta, mcp_instructions_delta, date_change, etc.

**Content-bearing subtypes uniquely lost:**
- `file` (316): full file body (`content.file.content`) — @file / `/compact`
  re-injection. **Sole carrier** (verified: adjacent user turn has only the
  `/compact` command text).
- `queued_command` (2,282): user prompt typed while busy. **~36% sole carrier**
  (measured 318/886; 568 later duplicated in a user turn).
- `edited_text_file` (487), `selected_lines_in_ide` (53), `nested_memory` (117),
  `directory` (1): sole carrier.

**Why v1 renders nothing:** `_event_body` (`api/v1/session_models.py`) reads only
`row.ir`/`row.search_text` → meta = empty `TranscriptWireInjectedBody`. And
`EventReadRow` (`session/models.py`, v1 read DAO row) has **no `raw` field** (raw
bytes deliberately omitted from the API) — so the content is structurally
unreachable on v1. No `UnknownBlock` rescue: attachments are top-level records,
never blocks inside `message.content`, so `_block`'s unknown fallback never
fires. The alternate timeline surface `_meta_item` (`session/timeline.py`) DOES
read `row.raw`, but content-bearing subtypes aren't in its label maps → generic
collapsed "Native record" summary only.

**SUPERSEDED fix recommendation (selective allowlist — rejected by owner).** An
earlier pass recommended a selective `meta_blocks` adapter hook surfacing only
content-bearing subtypes. The owner rejected the allowlist: there is no "noise"
(hooks/output_style/task_reminder all carry real injected content), and
editorializing subtypes is exactly what's being removed. See reveal-all below.

## DECISION: transcript reveal-all (current direction)

Product thesis: the transcript UI beats the CLI terminal *because nothing is
hidden*. **Reveal-all by default**; curate by progressive **subtraction** via a
JSON-path denylist (empty by default).

**Converged design — non-destructive API + UI-side denylist:**
- Reveal-all + toggle force a **non-destructive API**: the full native `raw`
  payload reaches the client for every event. No destructive API drop (would
  kill toggle/reveal-all).
- Denylist is a **presentation default** applied UI-side (`mapIrToChat.ts`):
  render everything, collapse/dim denied records with a global toggle + per-card
  expand.
- B6 reconciliation: "no internals on the wire" governs Run/Session control-
  surface impl fields (proxyPort/homeDir). Transcript `raw` is the product
  **content** noun (wire-vs-transcript diff is the product) → curated-noun
  compliant. Mark `raw` as an intentional content field; never re-strip under a
  "curation" banner.

**Prerequisite seam** (raw IS persisted; only the read strips it — precedent:
`GET_EVENTS_WITH_RAW_FOR_OWNER_SQL` in `dao_statements.py`):
1. `session/dao_statements.py`: v1 list+stream reads use `GET_EVENTS_FOR_OWNER_SQL`
   (`EVENT_READ_COLUMNS`, drops raw via
   `EVENT_READ_COLUMN_NAMES = tuple(... if name != "raw")`) — include raw.
2. `session/models.py`: add `raw: JsonObject | None` to `EventReadRow` (omitted
   today — the structural root cause of v1 raw-blindness).
3. `session/dao_rows.py`: `event_read_row` (field-driven).
4. `api/v1/session_models.py`: `transcript_event_view` — add `raw: object | None`
   to `TranscriptEventView`, `raw=row.raw`. `_event_body` stays curated for
   turns; meta/empty fall back to raw in the UI.
5. `api/v1/session_routes.py`: `list_session_events` + stream
   `_load_event_frame_batches`/`_event_stream` inherit raw via
   `transcript_event_views`.
6. www: `api/sessionEvents.ts` add `raw`; `stream/mapIrToChat.ts` render full raw
   JSON for meta/empty cards. Python↔TS mirror-checked by
   `api/src/transport_matters/test_type_mirrors.py` — change together.

**Denylist:** dotted-path `{path, equals}` predicates against the native record
(discriminator at `raw.type` / `raw.attachment.type`); hide if any match;
default empty. Lives in `~/.transport-matters/transcript_denylist.json`, echoed
on capabilities/meta, matched UI-side.

**Blast radius:** read-only, small. No ingest/adapter/write change (raw already
stored), no new migration (raw column exists), demote-to-meta + ACL intact.
**First slice S1** (reveal-all, denylist empty): un-strip raw → carry to view →
render raw JSON for meta/empty cards. **S2:** UI denylist (additive).

## Open Questions

- The curated v1 body flattens `ThinkingBlock` into text parts (`_text_parts`
  keys on any `text` field), whereas `mapIrToChat.normalizeContentBlock`
  preserves `thinking` as a distinct block. The active curated render path uses
  the flattened body; the richer normalizer appears to serve a raw-ir consumer.
  Worth confirming which consumer drives `normalizeContentBlock`.
