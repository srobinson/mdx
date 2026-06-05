---
title: Codex managed-mint launch (capture-substrate slice 5b) — tail-race fix
type: sessions
tags: [backend, transport-matters, capture-substrate, codex, managed-mint, tail-race]
summary: Eliminated the codex transcript tail race by owning the rollout at launch (mint uuid + pre-seed session_meta + codex resume) instead of globbing for it; deleted the locate read-back path.
status: active
source: backend-engineer
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

## Summary

The codex transcript tail RACED: TM globbed `~/.codex/sessions` for a rollout codex wrote
~1s AFTER the cursor registered (first wire frame), so the one-shot `locate()` glob missed,
fell back to a dead path, and never retried → `transcript_turn=0` + an empty codex session row.

**Managed-mint fix (supersedes the read-back half of slice 5 #25):** `transport-matters codex`
now OWNS the codex session. The launcher mints `native_session_id=uuid4()`, pre-seeds the minimal
`session_meta` rollout at the exact path codex will append to, persists `source_descriptor` + `cli`
onto the codex session row, and launches `codex resume <native>`. The tailer reads the owned
`source_descriptor` and byte-tails from 0 — no discovery. "Any wire frame ⇒ TM launched it ⇒ TM
owns the uuid + path," so the read-back glob is unreachable dead code and was deleted.

Branch `feat/capture-slice-5b-codex-managed-mint` @ `558234a` (off main `33e087a`). Dual MoE
sign-off (author backend-engineer:3.1 + reviewer:3.2). `cd api && just ci` green (1124).

## API / Contract

New `TRANSPORT_MATTERS_*` env contract (CLI → mitmdump addon subprocess, via Pydantic `Settings`):
- `TRANSPORT_MATTERS_CLI` — harness cli ("codex"), stamped onto the session row.
- `TRANSPORT_MATTERS_CODEX_NATIVE_SESSION_ID` — the minted uuid (== the wire-observed thread id).
- `TRANSPORT_MATTERS_CODEX_SOURCE_DESCRIPTOR` — JSON `FileTailSource` of the owned rollout.

`SessionBinding.source_descriptor` codec: `encode_source_descriptor` / `decode_source_descriptor`
(index/adapters/base.py) — one definition for the launcher (encode) + tailer (decode).
`TranscriptAdapter.locate` is now a non-abstract default-`None` hook (claude overrides; codex does not).

## Database Changes

No schema change. The `session` row's nullable enrichment cols (`cli`, `source_descriptor`) are now
populated for managed-codex sessions: `bind_exchange` stamps them onto the wire binding when the wire
id matches the owned native uuid; both `_write_wire` and `_write_transcript` `upsert_session`
(COALESCE on the enrichment cols), so the row is non-empty regardless of which stream lands first.

## Security / Correctness

- A codex wire id TM did NOT seed (forked subagent thread / stray) gets no descriptor → registers
  NO cursor (stays pending), never a glob. Owned-id match guards descriptor stamping.
- Order: `make_index_sink` submits the wire job BEFORE scheduling cursor registration (reviewer
  block). Empty-row is impossible by construction (both bindings carry values + idempotent upsert),
  not by ordering; both orderings are tested.

## Verification

- Unit regressions: (a) deterministic descriptor tail, (b) 5-session same-cwd zero cross-binding,
  (c) phantom→pending, + bind_exchange stamp + sink order + transcript-first row population.
- **(d) REAL codex 0.137.0 proof** (isolated `CODEX_HOME`): `codex exec resume <uuid>` against a
  249-byte seeded session_meta → APPENDED to the same file (→25KB, no fork, 5 response_items);
  multi-instance same-cwd → each tailed its own file, zero cross-binding. Confirms the load-bearing
  assumption (resume continues the owned file). See cm lesson "codex resume appends to a pre-seeded
  minimal session_meta rollout".

## Open Items

- Resuming a PRE-EXISTING session TM did not seed (race-free launch-time resolve) is OUT OF SCOPE
  (YAGNI) until TM supports external-session resume.
- Spec fast-follow (post-merge, non-blocking): §5.2 read-back → managed-mint; §15 risk 2 eliminated;
  §11.1 cursor note; LEDGER + README status.
- `cli="codex"` is set unconditionally for the codex launcher (incl proxy-only) — accepted (no
  descriptor ⇒ no cursor).
