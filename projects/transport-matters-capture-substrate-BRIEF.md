# MoE Spec Brief: Transport Matters Capture & Retrieval Substrate (items 1+2)

## Mission

Produce ONE implementation-ready spec, by consensus, for persisting and searching
both HTTP wire payloads and CLI transcripts. This is the keystone storage work for
Transport Matters. Two backend-engineer experts (different models) co-author and
adversarially review until both sign off.

Output spec path (author is the SOLE writer of this file):
`~/.mdx/projects/transport-matters-capture-substrate-spec.md`

## Phased build — respawn for fresh context (orchestrator-managed)

To keep both models in fresh context and avoid running out of context on a long
spec, the spec is built in FOUR phases. Each phase runs in its OWN warroom (a fresh
MoE pair); the orchestrator kills and respawns between phases. The durable handoff
is two files on disk, never carried context:

- the spec itself (accumulates approved sections), and
- the LEDGER `~/.mdx/projects/transport-matters-capture-substrate-LEDGER.md`
  (orchestrator-maintained: phase status, locked decisions, approved sections,
  open escalations).

A fresh pair reads spec + LEDGER + this brief COLD and continues. Everything
load-bearing must live in those files. Do not assume any cross-phase memory.

Phases (each builds on the approved prior sections):

- Phase A — Foundations: sections 1 (scope), 2 (domain model), 3 (exact DDL + block
  hashing + PRAGMAs), 12 (module/file layout). Locks schema + vocabulary.
- Phase B — Adapters: sections 4 (adapter port + dataclasses incl. NormalizedTurn),
  5 (claude/codex/gemini/opencode concrete adapters grounded in real samples).
- Phase C — Engine + data paths: sections 6 (indexer process model), 7 (write path),
  8 (read/query API).
- Phase D — Lifecycle + verification: sections 9 (live-tail), 10 (delete + GC),
  11 (migration/backfill), 13 (test plan), 14 (phasing), 15 (open risks).

Context hygiene within a phase: write to the file, keep bus messages terse, do not
re-read large files you have already summarized. If a pane nears its context limit
BEFORE sign-off, finish the current write, post a one-line `M`
"near-limit, checkpoint saved", and the orchestrator will respawn a fresh pane for
the SAME phase pointing at the partial file + LEDGER.

CURRENT PHASE is named in the LEDGER. Produce ONLY the current phase's sections.
Do not draft later phases.

## Roles

- AUTHOR: `transport-matters:helioy-tools:backend-engineer:1:3.1` (Claude). Writes
  and owns the spec file. Applies agreed changes.
- REVIEWER: `transport-matters:helioy-tools:backend-engineer:1:3.2` (Codex).
  Adversarial co-author: critiques, proposes concrete changes, never writes the file.
- ORCHESTRATOR (me): `transport-matters:general:1:2.1`. I decide escalated design
  tradeoffs. I do not relay between you. Debate peer-to-peer.

## Read first (do not trust this brief alone; read the code and real samples)

1. `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/NOTES/roadmap.md` — the
   resolved design for items 1+2 lives here (hybrid two-tier store, adapter matrix,
   schema sketch, write/read/delete/concurrency). This spec MAKES THAT CONCRETE.
2. Current storage layer: `api/src/transport_matters/storage/` (`base.py`,
   `disk_layout.py`, `disk.py`), `exchange_recorder.py`, `ir.py`,
   `manifest.py`, `workspace.py` (note: `workspace.py` already uses `blake2b` —
   reuse it for block hashing), `counting.py`, `exchange_stats.py`.
3. Codex path: `api/src/transport_matters/codex/` (exchange handling, derived
   events/turn), `addon_handlers.py`, the websocket capture.
4. HTTP server + live push: `api/src/transport_matters/api/`, `broadcast.py`,
   `sse.py` (the existing SSE surface the UI consumes).
5. Real transcript samples to ground the normalized turn model:
   - claude: `~/.claude/projects/<cwd-slug>/<uuid>.jsonl` (e.g.
     `~/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-littleorgans-littleorgans/0c721f8e-84a0-48b5-b3bc-f256d07cb67f.jsonl`)
   - codex: `~/.codex/sessions/`, `~/.codex/session_index.jsonl`
   - gemini: `~/.gemini/` (history, projects.json), and `gemini --help` (`--session-id`)
   - opencode: `opencode --help`, `opencode export <id>` JSON shape

## Decisions already made — DO NOT re-debate (escalate via E only if code reality contradicts)

- Store topology: HYBRID TWO-TIER. Tier-1 = existing per-run dir
  `{slug}/{hash}/{run_id}/` stays the source of truth for raw bytes (largely
  unchanged). Tier-2 = ONE shared machine-level SQLite at
  `~/.transport-matters/index.db` (WAL), a rebuildable derived index. Tier-2 is pure
  projection: nuke and replay tier-1 to rebuild.
- Both streams are first-class and never collapsed. The analysis value is the DIFF
  between transcript (what the harness/human believes) and wire (what hit the
  provider).
- Dedup is via a GLOBAL content-addressed `block` table (blake2b). One FTS index
  over blocks covers both streams.
- Search depth: FTS5 lexical (BM25) FIRST. Vector / sqlite-vec is explicitly a
  LATER optional slice, OUT of this spec's core (mention as a forward hook only).
- Correlation: per-provider adapter (anti-corruption layer, the transcript-side twin
  of `ir.py`). Binding strategies: claude + gemini MINT (`--session-id <uuid>` we
  generate); codex READ-BACK / proxy-derived (already captured via the proxied
  websocket); opencode API/EXPORT. We own the session uuid where we can mint it, so
  it becomes the universal correlation key.
- Single-user repo, NO backward-compat. Schema changes may nuke the index freely.
  Respect CLAUDE.md limits: new files <=700 LOC, functions <=~150 LOC.

## The spec must contain (precise, numbered)

1. Scope & non-goals. Explicitly out: realtime compaction (item 3), vector search,
   UI work.
2. Domain model / ubiquitous language: session, run, wire_exchange, transcript_turn,
   block, correlation key. One paragraph each, crisp.
3. EXACT SQLite DDL for tier-2: every table (`block`, `session`, `wire_exchange`,
   `transcript_turn`, `exchange_block`, `turn_block`), the FTS5 virtual table config
   (which columns, tokenizer, external-content vs standalone), all indexes, and the
   connection PRAGMAs (WAL, foreign_keys, busy_timeout, synchronous). Define the
   block hash input precisely (raw bytes vs canonical JSON; reconcile with existing
   `char_accounting` canonicalization) and the `block.kind` enumeration.
4. Provider adapter PORT: the exact Python interface (Protocol/ABC) with method
   signatures and the dataclasses it returns: `SessionBinding`, `TranscriptSource`
   (file-tail vs pull/api variants), `NormalizedTurn` (full field list), the
   `normalize(native_record) -> NormalizedTurn` contract.
5. Concrete adapters: claude (MINT `--session-id`, deterministic jsonl path
   derivation, jsonl line -> NormalizedTurn mapping grounded in the real sample),
   codex (proxy-derived, reuse existing capture, thread_id/session_id), gemini (MINT,
   locate under ~/.gemini), opencode (api/export). For gemini/opencode, fully spec
   bind+locate; ground record-normalization against real samples where available and
   FLAG explicitly where a sample could not be obtained (no guessing presented as
   fact).
6. The single machine-level INDEXER: process model (in-proxy thread vs separate
   daemon vs direct writes under busy_timeout — pick one and justify), how the proxy
   and adapters feed it, single-writer WAL discipline, batching, idempotent upserts
   (the upsert keys).
7. Write path: wire capture -> tier1 raw (unchanged) + tier2 upsert; transcript
   adapter -> tier1 source + tier2 upsert. State idempotency keys for re-ingest.
8. Read path / query API: search (FTS + structured filters, two-phase metadata-then-
   bodies), session-timeline reconstruction from blocks, wire<->transcript pivot
   (join on session_id, sharpened by shared block-hash match), raw fetch via
   `raw_path`. Define the Python query surface and/or the HTTP endpoints under `api/`.
9. Live-tail: the watch mechanism per source shape (jsonl file watch for
   claude/gemini, the live websocket for codex, poll/SSE for opencode), and how new
   rows reach the UI through the existing `broadcast.py`/`sse.py`.
10. Delete + GC: run-delete evicts tier2 `WHERE run_id=?`; block GC mark-and-sweep;
    periodic vacuum reconcile against existing run dirs; the rebuild-from-tier1
    procedure.
11. Migration from today: index.jsonl + artifact dirs. What changes in tier-1 (aim:
    minimal). First-boot backfill that replays existing run dirs into tier-2.
12. Module / file layout under `api/src/transport_matters/` (respect the LOC limits).
    Propose concrete package + file names.
13. Test plan: unit (block dedup, idempotent upsert, GC mark-sweep), integration
    (capture -> index -> search round-trip; correlation join; live-tail), per-adapter
    normalization fixtures from the real samples.
14. Phasing: a sensible build order (e.g. schema+indexer+wire -> claude transcript
    adapter -> search API -> codex -> gemini/opencode -> live-tail -> GC), each phase
    independently shippable and testable.
15. Open risks / decisions deferred to orchestrator (list anything you cannot resolve
    from code + these decisions).

## Protocol (adapted from moe-local-batch; spec-writing variant)

Typed, terse bus messages. NEVER paste the spec, DDL, or long prose into the bus —
reference the file path; the peer reads the file directly. Topic: `tm-capture-spec`.

1. AUTHOR sends `D` = a short outline line (sections + the 2-3 load-bearing design
   choices) to REVIEWER, and an `M` one-liner to orchestrator.
2. REVIEWER responds to the outline: agree-to-proceed or a `B` block (substantive
   issue) to AUTHOR, `M` to orchestrator.
3. AUTHOR writes the full spec to the path, sends `DRAFT ready <path>` to REVIEWER,
   `M` to orchestrator.
4. REVIEWER reads the FILE (not memory), sends `B` blocks (one per substantive issue,
   with concrete required change) or a sign-off, to AUTHOR, `M` to orchestrator.
5. AUTHOR applies fixes, notifies REVIEWER, `M` to orchestrator.
6. Converge: both emit the EXACT phrase below. After 2 review rounds without
   convergence, `E`-escalate the contested point to orchestrator and await my call.

Adversarial discipline: find at least one substantive issue or positively justify
"none found". Do not perform agreement.

Sign-off phrase (exact, both must emit it on the same final shape):
`I sign off on the capture-substrate spec as currently filed`

Block phrase:
`Substantive issue blocking sign-off: <one line>`

Escalation:
`E|<decision needed>|<options>` to orchestrator `transport-matters:general:1:2.1`.

Mail discipline (no CC on the bus): send a one-line `M` to
`transport-matters:general:1:2.1` at each milestone (outline sent, draft ready,
blocks raised, fixes applied, signed off). One line, status not narrative.
