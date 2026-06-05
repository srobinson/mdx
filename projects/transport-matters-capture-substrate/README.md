# Capture & Retrieval Substrate — build slices

Navigable index of the **canonical spec**
`~/.mdx/projects/transport-matters-capture-substrate-spec.md` (whole, signed-off,
~2025 lines). The spec stays intact — its cross-references and supersession chains
(§7.3→§11.1, the rebuild-gate constants across §3.2/§10.5/§11.4) are load-bearing.
These briefs are the **build-facing lens**: each names the files, the spec sections
to read, the invariants that slice must not break, and the acceptance gate. An
implementing agent reads its slice brief + the cited sections, never the whole spec.

- **Companion records:** LEDGER (`…-LEDGER.md`, phase/decision history),
  spec-authoring brief (`…-BRIEF.md`, the MoE process that wrote the spec).
- **Convention:** full slice briefs are generated **just-in-time** as we reach each
  slice (avoids drift if the spec is touched). This README is the stable map.

## Critical path

`1 → 2 → 3` stands up the wire-only capture+query loop (already useful). **4** adds the
transcript half and the wire↔transcript **DIFF** that is the whole point (§1.1). **5**
adds codex — the last adapter for now; **6 (gemini + opencode) is PARKED**, outside the
claude+codex harness scope (revisit later). **7/8** complete liveness and lifecycle on the
claude+codex scope (7's opencode Pull-poll path defers with 6).

## Global invariants (every slice)

- **Identity is semantic.** `block.hash = blake2b-256(identity_canonical(part))`;
  `identity_canonical` strips `provider_data`/`cache_hint` uniformly and is **NOT**
  `canonical_block_json` verbatim (§3.3, §12). Role/stream/section/position live on the
  **edges**, never on the block, never in the hash.
- **Tier-1 first, tier-2 best-effort off the hot path.** The wire path never blocks on,
  nor fails because of, tier-2 (§7.1). Tier-2 is a rebuildable projection.
- **DAG:** no `storage → index` import (cycle). The sink is injected in `load_runtime()`
  (§6.4). Index core (`schema/blocks/models`) imports `ir` + `canonicalization` only.
  Declare `canonicalization` (layer 1) and `index` (after `storage`) in the `api/CLAUDE.md`
  import DAG.
- **#17 privacy boundary** (added to main 2026-06-04, AST-enforced by
  `test_private_import_boundary.py`): no non-test module imports a `_`-prefixed name/module
  from another module — promote to public. Every cross-module symbol in `canonicalization`
  and `index/` must be public; keep intra-module helpers `_`-prefixed.
- **Cross-thread push** only via `loop.call_soon_threadsafe` — `broadcast.emit` is
  event-loop-affine, the writer is an OS thread (§9.4).
- **Durable enumeration** globs `*/*/*/index.jsonl`, never `manifest.read_all()`
  (manifest is unlinked on exit) (§10.1).
- LOC ≤ 700/file, functions ≤ ~150 LOC; builtins-only typing; Pydantic v2; IR frozen.

## Slices

| # | slice | files (§ref) | acceptance |
|---|-------|--------------|------------|
| 1 | **Core store + writer** | `canonicalization.py` (extract, §12); `index/{schema,db,blocks,models}.py` (§3,§12); `index/sessions.py` (§7.5); `index/writer.py` (§6.3) | §13.1 unit: dedup / identity≠char-canonical / kind determinism / idempotent upsert + `n_tokens` COALESCE / session synth + partial-unique / GC mark-sweep + FK + FTS evict. §3.8 DDL already green. |
| 2 | **Wire ingest + sink** | `index/ingest.py` (`bind_exchange`/`build_wire_job`, §7.2); injected post-persist sink in `load_runtime()` (§6.4) | capture → `wire_exchange` row + ordered edges; wire-path latency unchanged (§7.1) |
| 3 | **Read / query API** | `index/queries.py` (§8.6); `api/v1/index_routes.py` (§8.7) registered in `router.py` | §13.2 capture→index→search round-trip; `get_block_bodies`; `exchange_raw_ref`→tier-1 |
| 4 | **claude transcript + tailer** | `index/adapters/claude.py` (§5.1); `index/tailer.py` (§9.2); `build_transcript_job` (§7.3) | §13.2 correlation join + live-tail(file); claude golden fixtures; first end-to-end pivot/DIFF |
| 5 | **codex adapter** | `index/adapters/codex.py` (§5.2) | codex golden fixtures; codex pivot; read-back session convergence |
| 6 | **gemini + opencode adapters** — ⏸️ **PARKED** (revisit later; outside the claude+codex harness scope) | `index/adapters/{gemini,opencode}.py` (§5.3/§5.4) | gemini Format A intra-record `toolCalls[]` + Format B cross-record `pending_calls`; opencode reshape + live-tail(pull) |
| 7 | **Live-tail completion** — `transcript_turn` DONE (4b); **`session_correlated` DEFERRED** (slice-7 decision, MoE dual sign-off: managed-mint left no NULL→non-NULL producer; revive on external-adoption/opencode + a UI consumer, COALESCE-guard `wire_exchange.session_id` first — see spec §9.4); opencode Pull-poll parked with 6. Shipped: codex §15-risk-2 doc fix. | ~~live-push (§9.4, done 4b)~~; ~~opencode poll (§9.3)~~ | n/a — no build; decision recorded |
| 8 | **Delete + GC + backfill** | `index/maintenance.py` (§10); `iter_run_dirs` durable enumerator (§10.1) | §13.2 backfill idempotence, run-delete + GC, reconcile |

## Status

- [x] 1 (#18)  · [x] 2 (#19)  · [x] 3 (#20)  · [x] 4a ★ (#21)  · [x] 4b (#22)  · [x] 5 (#25, codex)  · [x] 5b (#26, codex managed-mint / tail-race fix)  · [x] 5c (#27, claude managed-mint + DRY launch port)  · ⏸️ 6 (parked)  · [~] 7 (`session_correlated` DEFERRED — decision; transcript_turn done in 4b; codex doc fix)  · [~] 8 (8a #29 enumerate/delete/GC · 8b-i #30 own-transcript snapshot · 8b-ii #31 home_dir descriptor + durable sessions.json · 8c-i #32 replay core (rebuild from tier-1, killer-demo PROVEN on real data) · 8c-ii #33 boot auto-replay) — **🏁 SUBSTRATE COMPLETE**

  + road-test fixes #23 (provisional sink), #24 (raw_dir root). claude + codex both captured end-to-end, DIFF validated on real data.

  Road-test fixes on the claude path: #23 (provisional sink seam), #24 (raw_dir workspace root). claude DIFF + dedup validated on real data.

  Slice 4 COMPLETE — full claude path live end-to-end (wire + transcript tail + DIFF + query). Road-test checkpoint. Code-quality audit running.

  (Slice 4 split 2026-06-04 along data/liveness; HARD GATE passed — claude transcript sessionId == wire metadata.session_id on 9 paired sessions.)

Tick on merge. Update the LEDGER's "Current phase" when a slice lands.
