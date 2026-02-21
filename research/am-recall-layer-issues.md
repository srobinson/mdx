---
title: "AM Recall Layer — Known Issues & Fix Plan"
type: research
tags: [attention-matters, am-core, recall, memory, fix-plan]
summary: "Analysis of remaining recall issues in attention-matters and specific code-level fixes needed"
status: active
project: am
confidence: high
created: 2026-02-21
updated: 2026-02-21
---

# AM Recall Layer — Known Issues & Fix Plan

## Context

The AM math engine (quaternions, SLERP, IDF, Kuramoto coupling, drift) is production-ready — verified by full audit Feb 2026. The problems are in the **recall/retrieval** path, not storage.

All memory is stored in a single `brain.db` — one product, one unified brain. No project boundaries.

## Issue 1: Recency Decay Too Weak

**Status**: PARTIALLY FIXED

**What exists**: `compose.rs` has `RECENCY_DECAY_RATE = 0.01` and `days_since_episode()` with a Julian day parser. Score formula: `score *= 1.0 / (1.0 + days * 0.01)`.

**The problem**: At 0.01, a 30-day-old memory only decays to 77% of its original score. A 365-day-old memory still retains 27%. Stale context competes too effectively with recent context.

**What exists in code** (`compose.rs`):

- `RECENCY_DECAY_RATE: f64 = 0.01`
- `days_since_episode()` — parses episode timestamp, computes Julian day difference
- `parse_days_ago()` — extracts YYYY-MM-DD from timestamp string
- Applied in `score_neighborhoods()` post-processing

**Fix needed**:

- Increase `RECENCY_DECAY_RATE` to 0.05-0.1 (30-day memory decays to 40-60% instead of 77%)
- Or switch to exponential decay: `score *= exp(-days * rate)`
- Conscious recency boost already exists (position-based, newer = higher score) — that's good

## Issue 2: Buffer Threshold of 3 Loses Short Sessions

**Status**: PARTIALLY MITIGATED — orphan flush exists but threshold still too high

**What exists**: `server.rs:21` — `BUFFER_THRESHOLD = 3`. `am_buffer` checks `buffer_size >= BUFFER_THRESHOLD` to trigger episode creation. `am_query()` flushes orphaned buffer at next session start.

**The orphan flush works**: When `am_query` is called, it checks `buffer_count()` and if > 0, drains and creates an episode. So 1-2 exchange sessions DO get persisted — but only when the NEXT session starts with `am_query`. If no next session happens, the buffer sits there.

**Fix needed**:

- Reduce `BUFFER_THRESHOLD` from 3 to 2

## Issue 3: Important Discoveries Buried Under General Noise

**Status**: PARTIALLY ADDRESSED

**What exists**: `compose.rs` — compose_context returns top 1 conscious, top 2 subconscious, top 1 novel. That's only 4 neighborhoods max per query.

**What's good**: Decision/Preference types get `DECISION_FLAT_SCORE = 100.0` which ensures they always rank high. Session dedup via `session_recalled` prevents re-surfacing same content.

**The problem**: With only top-1 conscious recall, if you have 200 conscious memories (marked salient), only the single best-matching one surfaces. Important insights that are tangentially related get buried.

**Fix options**:

- Increase conscious recall from top-1 to top-3 (or configurable)
- Use budgeted composition (`compose_context_budgeted`) by default with a reasonable token budget
- Weight conscious memories higher in the scoring — they were explicitly marked important

## Issue 4: Query Returns Too Few Results

**Status**: RELATED TO ISSUE 3

**What exists**: `compose_context()` hardcodes: 1 conscious + 2 subconscious + 1 novel = max 4 results. `compose_context_budgeted()` exists and can include more, but it's not the default path.

**The problem**: At session start, you want rich context — not 4 fragments. The budgeted version exists but the MCP server may not be using it.

**Fix needed**:

- Make the MCP server use `compose_context_budgeted()` with a default budget of ~2000 tokens
- Or increase the hardcoded limits in `compose_context()` to 3 conscious + 4 subconscious + 2 novel
- The `am_query` MCP tool already accepts `max_tokens` parameter — verify the server dispatches to `compose_context_budgeted()` when max_tokens is provided

## Architecture Reference

### Recall Pipeline (`am-core`)

```
query text
  → tokenize (tokenizer.rs)
  → activate words across both manifolds (system.rs: activate_word)
  → drift activated occurrences toward each other (query.rs: drift_and_consolidate)
  → compute interference between manifolds (query.rs: compute_interference)
  → Kuramoto phase coupling (query.rs: apply_kuramoto_coupling)
  → compute surface (surface.rs: compute_surface)
  → rank candidates by IDF-weighted activation + recency (compose.rs: rank_candidates)
  → select top-N per category (compose.rs: compose_context)
  → format output string
```

### Key Scoring Formula (`compose.rs:score_neighborhoods`)

```
base_score = sum(idf_weight * activation_count)  per occurrence in neighborhood
recency_decay = 1.0 / (1.0 + days_old * 0.01)
final_score = base_score * recency_decay
```

For decisions: `final_score = DECISION_FLAT_SCORE (100.0)` — always surfaces.

### Store Layer (`am-store/src/store.rs`)

- SQLite-backed: episodes → neighborhoods → occurrences
- Single brain.db — unified memory, no project boundaries
- Conversation buffer: separate table, drained at threshold
- GC: evicts cold occurrences, preserves conscious
- Full save/load roundtrip verified

## Priority Order for Fixes

1. **Issue 4 + 3**: Use budgeted composition by default, increase recall counts → most visible impact
2. **Issue 1**: Increase recency decay rate → stale context stops competing
3. **Issue 2**: Reduce buffer threshold or flush on session end → short sessions stop being lost
