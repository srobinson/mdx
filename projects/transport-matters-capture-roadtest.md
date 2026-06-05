---
title: Transport Matters — capture-substrate road-test playbook
type: runbook
tags: [transport-matters, capture-substrate, road-test, claude, diff, api]
summary: Copy-paste commands to exercise the live wire+transcript capture, the /api/index query surface, and the wire↔transcript DIFF against a real claude session.
status: active
created: 2026-06-04
updated: 2026-06-04
---

# Capture-substrate road-test playbook

Exercise the real end-to-end: launch a claude session through the proxy, watch tier-2
populate, and inspect the **wire↔transcript DIFF** (the whole thesis). Endpoints are
API-only for now (no UI yet) — curl + sqlite.

Requires `jq` and `sqlite3`. Make sure the running binary is built from `main` (the
live-capture fix is `#23` / `1516f95`): `git -C <repo> checkout main && git pull`, and if you
use a built (non-editable) install, `just install-local`.

```bash
# Pin the ports + a couple of vars so the rest copy-pastes cleanly.
export W=8765                                   # web/API port
DB=~/.transport-matters/index.db                # machine-global tier-2 index
```

## 1. Launch (real claude session through the proxy)

```bash
# In a project dir you'll actually work in (so there's real traffic):
transport-matters claude --web-port $W ~/some-project
# It prints: proxy URL, web UI URL, workspace CWD. Now HAVE A CONVERSATION —
# a few turns, ideally with a tool call or two and some "think hard" so you get
# thinking blocks. Leave this running; run the rest in another terminal.
```

## 2. Smoke test — did tier-2 populate?

```bash
sqlite3 "$DB" "
  select 'wire_exchange', count(*) from wire_exchange
  union all select 'transcript_turn', count(*) from transcript_turn
  union all select 'session', count(*) from session
  union all select 'block', count(*) from block
  union all select 'exchange_block(edges)', count(*) from exchange_block
  union all select 'turn_block(edges)', count(*) from turn_block;"
```

Expect non-zero everywhere. If all zero → capture isn't firing (the #23 class of bug); grab
the run's `mitmdump.log` and shout.

## 3. Live events (SSE) — watch turns land in real time

```bash
curl -N localhost:$W/api/stream
# Keep this open and send another message in claude. You should see, within ~250ms:
#   data: {"type": "exchange", ...}            <- wire side
#   data: {"type": "transcript_turn", ...}     <- transcript side (slice 4b)
# ": keepalive" lines between events are normal.
```

## 4. Find your session

```bash
curl -s localhost:$W/api/index/sessions | jq .
# Grab the session_id for your run:
export SID=$(curl -s localhost:$W/api/index/sessions | jq -r '.[0].session_id')
echo "SID=$SID"
```

## 5. Timelines — wire vs transcript, side by side

```bash
# Wire stream (what hit the provider), ordered by seq:
curl -s "localhost:$W/api/index/sessions/$SID/timeline?stream=wire&with_bodies=true" | jq .

# Transcript stream (what the harness recorded):
curl -s "localhost:$W/api/index/sessions/$SID/timeline?stream=transcript&with_bodies=true" | jq .

# Paginate a big session by seq range:
curl -s "localhost:$W/api/index/sessions/$SID/timeline?stream=transcript&seq_from=0&seq_to=10" | jq .
```

## 6. Search (two-phase FTS5: hits, then bodies)

```bash
# Phase 1 — metadata + snippet + bm25 rank (no bodies):
curl -s -X POST localhost:$W/api/index/search -H 'content-type: application/json' \
  -d '{"q":"<a distinctive word from your conversation>"}' | jq '.hits'

# With structured filters (all optional, AND-combined) + inline bodies for the top hits:
curl -s -X POST localhost:$W/api/index/search -H 'content-type: application/json' -d '{
  "q":"function OR error",
  "filters":{"stream":"transcript","kind":"text","cli":"claude"},
  "mode":"occurrence",
  "limit":20
}' | jq '.hits'

# block mode = dedup view: "this content appears in N places across runs"
curl -s -X POST localhost:$W/api/index/search -H 'content-type: application/json' \
  -d '{"q":"system","mode":"block"}' | jq '.hits'
```

## 7. ★ THE DIFF — what the harness believed vs what hit the wire

```bash
# Three block-id buckets:
curl -s "localhost:$W/api/index/sessions/$SID/diff" | jq .
#   { "wire_only": [ids...], "transcript_only": [ids...], "shared": [ids...] }

# Make wire_only HUMAN-READABLE — fetch the bodies of blocks that ONLY hit the wire.
# This is the payoff: injected system reminders, additive replay, real tool schemas
# the transcript never recorded.
curl -s "localhost:$W/api/index/sessions/$SID/diff" \
 | jq -c '{ids: .wire_only}' \
 | curl -s -X POST localhost:$W/api/index/blocks -H 'content-type: application/json' -d @- \
 | jq -r '.[] | "── [\(.kind)] ──\n\(.text)\n"'

# Same for transcript_only (what the harness thinks it sent but the wire didn't show):
curl -s "localhost:$W/api/index/sessions/$SID/diff" \
 | jq -c '{ids: .transcript_only}' \
 | curl -s -X POST localhost:$W/api/index/blocks -H 'content-type: application/json' -d @- \
 | jq -r '.[] | "── [\(.kind)] ──\n\(.text)\n"'
```

**What to confirm:** `wire_only` should surface the things the harness hides — `system`
reminders, `tool_def` schemas (full tool definitions), cache markers / additive replay.
`shared` should contain your actual message text and tool results (identical content →
**one** block deduped across both streams). `transcript_only` is usually small.

## 8. Pivot — which wire exchange ↔ which transcript turn

```bash
curl -s "localhost:$W/api/index/sessions/$SID/pivot" | jq .
#   [{ "exchange_id":..., "turn_id":..., "shared_blocks": N }, ...] ranked by overlap
```

## 9. Raw bytes (always from tier-1, never copied into the index)

```bash
EXID=$(curl -s "localhost:$W/api/index/sessions/$SID/timeline?stream=wire" | jq -r '.[0].entity_id')
curl -s "localhost:$W/api/index/exchanges/$EXID/raw?part=request"  | head -c 2000; echo
curl -s "localhost:$W/api/index/exchanges/$EXID/raw?part=response" | head -c 2000; echo
```

## 10. Direct SQLite (deeper than the API)

```bash
# Block dedup in action — content shared across BOTH streams (the §3.3 linchpin):
sqlite3 "$DB" "
  select b.id, b.kind, substr(b.text,1,60) as text,
         (select count(*) from exchange_block where block_id=b.id) as wire_refs,
         (select count(*) from turn_block     where block_id=b.id) as turn_refs
  from block b
  where exists (select 1 from exchange_block where block_id=b.id)
    and exists (select 1 from turn_block     where block_id=b.id)
  limit 20;"

# Per-section wire block counts (system/tools/messages/response):
sqlite3 "$DB" "select section, role, count(*) from exchange_block group by section, role;"

# Transcript turn DAG (parent_id chain) + sidechain/subagent turns:
sqlite3 "$DB" "select seq, role, is_sidechain, substr(turn_id,1,8), substr(parent_id,1,8)
               from transcript_turn where session_id='$SID' order by seq;"

# Token/char accounting on the wire side:
sqlite3 "$DB" "select seq, model, req_system_chars, req_tools_chars, req_messages_chars,
               req_tokens, res_tokens, stop_reason from wire_exchange
               where session_id='$SID' order by seq;"

# Session correlation state. Managed claude is now MINTED (slice 5c #27): cli='claude', minted=1
# (TM owns the uuid via `claude --session-id`). codex: minted=0 (synth session_id). A claude session
# TM did NOT launch (you passed your own --session-id) stays minted=0 = native-adopt fallback.
sqlite3 "$DB" "select session_id, provider, cli, minted, native_session_id from session;"
```

## 11. What to probe (edge cases worth a look)

- **Block dedup across streams** — pick a sentence you typed; confirm it's ONE block id
  referenced by both an `exchange_block` and a `turn_block` row (§10 query above). That's the
  content-addressed identity working.
- **tool_use / tool_result** — run a tool in claude; confirm the `tool_use` (id+name+input)
  and `tool_result` appear, and that the same call dedups across wire+transcript.
- **thinking blocks** — ask claude to "think hard"; confirm `kind=thinking` blocks land and
  that the DIFF treats them sanely (the `signature` is stripped from identity, so identical
  thinking text dedups).
- **multi-turn ordering** — `seq` should be monotonic per session on both streams.
- **subagent / sidechain** — if you trigger a subagent, its turns should carry
  `is_sidechain=1` under the same `session_id`.
- **re-correlation** — an exchange captured before its session was known starts with
  `session_id=NULL`; once correlated it backfills `session_id` AND `seq` (the slice-2 fix).
  Check there are no `wire_exchange` rows with a non-null `session_id` but null `seq`:
  `sqlite3 "$DB" "select count(*) from wire_exchange where session_id is not null and seq is null;"`  → should be 0.

## 12. Reset between runs

```bash
# tier-2 is a rebuildable projection — safe to nuke; it re-creates schema on next launch.
rm -f ~/.transport-matters/index.db ~/.transport-matters/index.db-wal ~/.transport-matters/index.db-shm
# (tier-1 raw capture under ~/.transport-matters/workspaces/ is the source of truth; leave it.)
```

## Notes / current limits

- **codex IS captured** as of slice 5 (#25), via **managed-mint** as of slice 5b (#26):
  `transport-matters codex` mints the session id, pre-seeds the rollout at the exact owned path, and
  launches `codex resume <id>` — no read-back glob, no tail race (the slice-5 read-back era could
  miss the rollout if codex wrote it after cursor registration). On a real run the session row
  should carry `cli='codex'` + a non-empty `source_descriptor`, and `transcript_turn` should be
  non-zero. Caveats: (a) **reset index.db between test runs** (`rm ~/.transport-matters/index.db*`)
  — it's machine-global + additive, so rows from a prior/pre-fix run will confuse the read;
  (b) non-conversational codex requests (`request_kind:memory`, the initial window-handshake frame)
  correctly carry no session id and stay **uncorrelated** (NULL `session_id`) — you may see several
  per session, that's expected, not a bug; the real conversation turns correlate.
- **No UI** for `/api/index` yet — curl/sqlite is the surface.
- `pivot`/`diff` are exact for claude + codex (session-id correlation). gemini/opencode are parked
  (slice 6).
