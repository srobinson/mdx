---
title: Capture Substrate Slice 4a — Claude Transcript Adapter + the DIFF
type: sessions
tags: [backend, capture-substrate, sqlite, tier-2, slice-4a, transport-matters, moe, transcript, diff, milestone]
summary: The §4 adapter port + canonical SessionBinding reconcile + claude adapter + build_transcript_job + the first real wire↔transcript DIFF; dual MoE sign-off (zero blockers) at ac121ee.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# Capture Substrate Slice 4a — Claude Transcript Adapter + the DIFF ★ MILESTONE

Warroom MoE. Author = backend-engineer (`:3.1`); reviewer = Codex (`:3.2`); orchestrator = `:2.1`.
Branch `feat/capture-slice-4-claude-transcript-tailer`, tip **ac121ee**, off main (slices 1-3 merged
@ #18/#19/#20). Slice 4 was split (orchestrator-approved): **4a = adapter + DIFF** (this); 4b = tailer
+ live event. Dual clean sign-off, **zero blockers** (first slice with none).

## ⚠️ HARD GATE — verified firsthand (the correlation linchpin)

The whole DIFF rests on claude's transcript `sessionId` == the wire `metadata.session_id`. Verified
on real data before coding: **9 paired sessions** on this machine where wire `metadata.session_id`
(parsed from `metadata.user_id` JSON, `anthropic.py:516-521`) == claude transcript `sessionId` (==
filename stem). So claude is correlated by its **native** session id used **directly**, `minted=False`
— `--session-id` minting stays deferred (slice-2 decision A). If this ever fails, STOP + escalate.

## Summary / decisions (for 4b + slice 5)

- **§4 port** (`index/adapters/base.py`): `TranscriptAdapter` ABC (async `bind`/`locate`, sync
  `normalize`) + frozen `SessionBinding` / `TranscriptSource`(`FileTailSource`|`PullSource`) /
  `RunContext` / `TurnContext` / `NormalizedTurn`. `NormalizedTurn.parts: list[ir.ContentBlock]`
  verbatim → identical content dedups to one `block.hash` across streams (the pivot linchpin).
  Adapters import **ir only** (+ stdlib).
- **SessionBinding reconciled to ONE definition** in `adapters/base.py` (DRY; slices 1/2 staged a copy
  in `sessions.py`). New shape: `session_id` (RESOLVED by the binder), provider, run_id, cwd,
  workspace_slug, workspace_hash, started_at, cli(nullable), native_session_id, minted(bool),
  source_descriptor. **`resolve_session_id` removed** — the binder resolves: claude/anthropic use the
  native id directly; codex/opencode synth (`synth_session_id`, still in `sessions.py`). `synth` can't
  live in adapters (ir-only), so read-back synth happens in `ingest.bind_exchange` / the tailer, not
  the adapter — **slice 5 codex must synth outside the adapter too.**
- **Import graph:** `sessions`/`ingest` import `SessionBinding` from `adapters.base` (a leaf importing
  only ir → no cycle). `adapters/__init__.get_adapter(cli)` imports concrete adapters **lazily** to
  keep `base` a clean leaf. `schema → sessions → adapters.base → ir`.
- **claude adapter** (`claude.py`): `bind` = native id direct (`minted=False`); `locate` = deterministic
  `~/.claude/projects/<cwd-slug>/<session_id>.jsonl` (`cwd.replace("/","-")`); `normalize` = skip
  `type ∉ {user,assistant}`, map `message.content` per §5.1 (str→TextBlock; list→6 content kinds),
  `thinking.signature`→`provider_data` (stripped from identity), `turn_id=uuid`, `parent_id=parentUuid`,
  `is_sidechain=isSidechain`, `ts=timestamp`, `model=message.model`. Never emits system/tool_def (§4.1.4).
- **Wire correlation fix** (`ingest.bind_exchange`): anthropic now binds `native_session_id` +
  `session_id=metadata.session_id` (direct) + `minted=False` — converges with the transcript (PK value
  unchanged from slice-2; flag/native column moved). `upsert_session` COALESCEs cli/native/source_descriptor
  so wire + transcript enrich one session row without clobbering (the transcript supplies cli=claude).
- **`build_transcript_job`** (§7.3): session upsert → `transcript_turn` upsert (PK `turn_id`) →
  `turn_block` edges (delete+reinsert; the **turn's** role on every edge). `seq` is the source ordinal
  (not MAX+1 — supplied by the caller/tailer).
- **The DIFF** (§8.4): proven — wire (system+message+response) + transcript (shared+transcript-only)
  under one session_id → `session_diff` buckets shared / wire_only / transcript_only exactly;
  `session_pivot` reports the wire-exchange ↔ transcript-turn correspondence (shared_blocks).

## Tests / fixtures

11 new tests vs real temp SQLite. The claude golden fixture (`api/tests/fixtures/claude_transcript.jsonl`)
is **structurally faithful to the real envelope** (verified) but **synthetic content** (repo privacy —
transport-matters is public). Slice-1/2 session tests reconciled to the new SessionBinding.

## Open Items (slice 4b)

- `index/tailer.py`: `TranscriptTailer` + `TailCursor` + the §9.3 FileTail iterate seam (stat, seek
  byte_offset, split on `\n`, parse complete records only, **advance byte_offset only past the last
  `\n`**, leave the trailing partial). The record-iterate fn is the ONE path shared with §11 backfill.
- `index/writer.py`: `transcript_turn` live event via `loop.call_soon_threadsafe` ONLY (§9.4 — the
  writer is an OS thread; never a direct broadcast.emit from the thread).
- Tailer started in `load_runtime`; claude cursor registered after the first wire frame reveals
  `session_id` (read-back; §15 risk-2 one-frame startup lag accepted).
