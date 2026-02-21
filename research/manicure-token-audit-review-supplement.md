---
title: manicure token-accounting rework — supplement review (3 follow-up commits)
branch: feat/token-accounting-rework
reviewer: engineering-code-reviewer
reviewed_at: 2026-04-14
commits: a95a7f7..c384456
prior_review: ~/.mdx/research/manicure-token-audit-review.md
audit_spec: ~/.mdx/research/manicure-token-audit.md
verdict: ship
---

# Summary

**Verdict: SHIP.** One real but low-severity correctness issue (the engineer's
own self-flag) is worth fixing in a follow-up, but nothing here blocks merge.
The three commits address the remaining gaps cleanly: the DRY note from the
prior review is resolved, historical rows can now recover real token counts
on demand, and the UI degrades safely to the existing chars rendering when
the recount cannot run.

# Baseline

| Stack | Files | Tests | Delta vs prior review |
| ----- | ----- | ----- | --------------------- |
| api (pytest) | — | 237 | +9 (all in `TestGetPipelineTokens`) |
| www (vitest) | 12 | 52 | +1 file, +3 tests (`ExchangeCard.test.tsx`) |

Commits delivered: 3, matches the "one conventional commit per logical
change" rule in the brief. Messages and subjects follow the existing
`type(scope): summary` convention.

# Self-flagged caveats

### 1. Partial-stamp sticky state — REAL ISSUE, low severity

The engineer's flag is correct. Walking the code:

- When curated differs from original, `exchanges.py:176-179` issues two
  concurrent `count_tokens` calls via `asyncio.gather`. If one succeeds and
  the other returns None (e.g. rate-limit jitter hitting one RTT but not
  the other), the result is `(42, None)` or `(None, 42)`.
- `exchanges.py:185-193` persists whenever *either* side is non-null
  (by design: "both-null is indistinguishable from never-tried, so we
  skip the write to leave it retryable").
- But the short-circuit at `exchanges.py:122-129` and `139-146` also fires
  when *either* side is non-null. So the partial stamp is treated as
  "already stamped" on every subsequent open — the null side never
  recovers.
- The UI side compounds it: `ExchangeCard.tsx:24-25` gates
  `needsTokenRecount` on `pipeline.tokens_before === null &&
  pipeline.tokens_after === null` (both must be null). So for a
  `(42, null)` row the UI won't even request a refetch.
- The same write path exists for live flows at `addon.py:506-513` →
  `_stamp_pipeline_tokens` at `addon.py:314-322` which returns
  `(tokens_before, tokens_after)` verbatim. A partial live-flow failure
  writes the mixed result directly to the index, triggering the same
  stuck-state on first endpoint open.

Two clean fixes, either of them alone resolves it:

- **Server short-circuit to `and`** (retry until both real). Partial
  persists remain correct as a progress signal, and the retry recomputes
  both sides. Simplest change.
- **Tighten persist guard to `and`** (only write when both are real).
  Rows sit at `(null, null)` until a clean round-trip succeeds. Matches
  the mental model of "stamped = authoritative for both."

Severity: low. Failure mode only triggers under partial RTT failure on a
divergent pipeline, which is rare in practice, and the UX degradation is
"one side of the pipeline view shows an em-dash" rather than anything
incorrect. **Not a merge blocker**; flag for follow-up.

**Missing test coverage**: no case exercises the `(real, None)` or
`(None, real)` mixed result. A `_CountingStub` that alternates return
values would catch a future regression.

### 2. `_compute_locks` growth — BENIGN

The reasoning in the comment at `exchanges.py:23-28` holds. An
`asyncio.Lock` is closer to 200–300 bytes than "a few bytes", but the
bound is real: the dict only grows with rows that actually enter the
compute path (already-stamped rows short-circuit before `_lock_for`),
and that set is bounded by archive size. For a 10k-archive session
where every exchange is opened, the ceiling is ~2–3 MB. Acceptable for
a dev tool; eviction would add complexity without a corresponding
problem to solve. Minor cosmetic nit: the comment's "few bytes" could
say "a couple hundred bytes each."

### 3. Auth handling — CLEAN

No leak paths found. Full trace:

- `addon.py:424` snapshots filtered auth on every inbound `/v1/messages`
  flow via `_relevant_auth_headers`, which restricts to the four keys
  `{x-api-key, authorization, anthropic-version, anthropic-beta}` at
  `counting.py:30-37`. No `cookie`, no `user-agent`, no arbitrary
  headers ever enter `_recent_auth`.
- Module-global `_recent_auth` at `counting.py:130`. Never serialised,
  never yielded to an endpoint response, never logged.
- `addon.py:474` clears it in `done()` alongside the counter teardown.
  Process death also clears it.
- `exchanges.py:149` is the only `get_recent_auth()` reader; the return
  value flows only into `counter.count(payload, auth)` which uses it as
  the outbound request headers to api.anthropic.com.
- `PipelineTokensResponse` at `exchanges.py:85-87` carries only
  `tokens_before` and `tokens_after`. No auth in the browser payload.
- `IndexEntry` and `ExchangeArtifacts` at `storage/base.py:63-89` have
  no header fields. `request_raw` is the HTTP *body* (populated via
  `flow.request.get_text().encode()` at `addon.py:99-102`), not the
  headers, so auth does not land in the on-disk artifacts.
- Log audit: `counting.py` only logs status codes and at most
  `response.text[:200]` of Anthropic's error replies, which do not
  echo request headers. `exchanges.py:192` logs the exchange id only.

One subtle cross-tenant note worth keeping in mind but not a blocker:
`_recent_auth` is a single global overwritten on every inbound request,
so a multi-credential session (proxy forwarding two different API keys
in one session) would see the last-seen auth replay the historical
recount. The counting cache keys on auth (`counting.py:99-115`) so the
cached count stays tenant-correct, but a *newly issued* recount against
credential A's billing would fire for credential B's historical
exchange. The product is a single-user local dev tool so this is not a
real concern today — worth flagging only if multi-tenant support is
ever on the roadmap.

# Correctness

- **Endpoint semantics match the audit spec's "real tokens or honest
  chars, no heuristic" rule.** `exchanges.py:90-198` returns 200 with
  `{null, null}` in every non-fatal degraded case (counter not
  registered, no cached auth, counter returns None, artifacts missing)
  and the UI at `ExchangeCard.tsx:36-54` transparently keeps the chars
  rendering. No chars/4 estimate anywhere in the new code.
- **Merge order is correct.** `ExchangeCard.tsx:36-37` reads
  `pipeline?.tokens_before ?? pipelineTokensQuery.data?.tokens_before ?? null`
  → stored value wins, lazy response fills the null case, null remains
  null for fallback. Same for `tokens_after`.
- **Gating is right.** `ExchangeCard.tsx:29` gates the query on
  `cardTab === "pipeline" && needsTokenRecount` so idle rows and rows
  that already have stored counts never hit the endpoint. `staleTime:
  Number.POSITIVE_INFINITY` prevents spurious refetches in a session.
- **The endpoint's 404 semantics are defensible.** Nonexistent exchange
  → 404. Exchange with `pipeline is None` → 404 ("no pipeline record to
  count twice"). Everything else → 200 with null/null or real values.
- **Counter-failure retry path preserved.** `exchanges.py:185-193`
  deliberately does not persist a both-null result, so a retry after
  the counter recovers still has a chance to stamp. Test
  `test_counter_failure_returns_nulls_without_persisting` locks this
  in.

One minor note on the optimization at `exchanges.py:166-179`: the
byte-equality check on the outbound payload is a good cheap dedupe, but
it mirrors logic already living in `addon.py:309-322
_stamp_pipeline_tokens`. Future-future-future dedup opportunity — not
for now.

# DRY

Excellent. The prior review's low-severity observation (the three-site
context-tokens duplication) is resolved:

- `lib/formatting.ts:20-23` `contextTokens(src: UsageStats | null)` is
  the single home for the formula and the "why" comment.
- `TokenBar.tsx:14` uses it.
- `ExchangeCard.tsx:60` uses it (new callsite after `res` became a
  first-class variable).
- `ExchangeList.tsx:45` uses it.
- No other file reimplements `input + cache_creation + cache_read`;
  grep confirms the only textual reference is in the helper's own
  doc comment.

`TokenBar`'s prop collapse from `{input, cacheCreation, cacheRead}` to
`{usage: UsageStats}` is correctly threaded through `ExchangeCard.tsx:128`
(`<TokenBar usage={res} />`). No pass-through residue.

`DiskStorageBackend.update_pipeline_tokens` at `storage/disk.py:172-199`
reuses the existing `_rewrite_index` helper under the existing
`_index_lock` — same atomic pattern as `_backfill_cache_creation` at
`storage/disk.py:92-136`. No parallel write path.

The lazy endpoint reuses the shared `TokenCounter` via `get_counter()`.
No parallel HTTP client. Payload building reuses `AnthropicAdapter`.

# Execution quality

- **File sizes.** All files changed on this leg stay well under the
  700-LOC ceiling: `exchanges.py` at 198 LOC (was 84), `test_exchanges.py`
  at 448 LOC (was 179), `disk.py` at 296 LOC (was 267), `counting.py` at
  229 LOC (was 204), `ExchangeCard.tsx` at 253 LOC (was ~200),
  `ExchangeCard.test.tsx` new at 132 LOC.
- **Concurrency pattern is correct for single-process.** Per-exchange
  `asyncio.Lock` with double-check inside the lock is the right shape:
  winner computes, writes, releases; loser re-reads and short-circuits
  on the now-stamped state. The meta-lock `_compute_locks_meta` guards
  dict mutation against the meta-level race (two handlers simultaneously
  trying to lazy-create the same per-id lock). `test_concurrent_callers_share_one_counter_call`
  at `test_exchanges.py:400-447` drives both paths under a gated stub
  and asserts `stub.calls == 1`. Solid.
- **Atomic persistence.** `_rewrite_index` at `storage/disk.py:138-150`
  writes to `.tmp` and renames; POSIX `rename` is atomic within a
  filesystem, so a mid-write crash leaves `index.jsonl` intact. The
  `_index_lock` is shared with `append_index`, so a live exchange
  append cannot interleave with a lazy update on the same instance.
- **Multi-process**: not addressed, but manicure is a single-process
  mitmproxy addon co-hosting uvicorn. No concern for the intended
  runtime.
- **Error handling.** All the usual expected failure modes degrade to
  `{null, null}` at 200: missing counter, missing auth, artifact
  read failure, counter returns None. Persist failure at
  `exchanges.py:186-193` is logged via `logger.exception` and the
  endpoint still returns the computed values — the round-trip is not
  wasted, just not cached. Correct split: lazy compute is observable
  even when backing storage fails.
- **Types.** `PipelineTokensResponse` is a Pydantic v2 model (`BaseModel`
  + default serialization). `update_pipeline_tokens` is declared on the
  ABC at `storage/base.py:113-127` with a proper docstring spelling out
  the atomicity contract — downstream backends cannot silently cheat.
  Annotations are complete.
- **Async boundary holds.** I/O (endpoint handler, `count_tokens`,
  disk write) is async. Pure work (payload equality, model_copy,
  response assembly) is sync. The `adapter.outbound_request` call is
  sync because adapter parsing is pure (the CLAUDE.md rule).

# Security — auth handling

Re-stating the clean findings from "Self-flagged caveats §3":

- Headers filtered to the four-key allowlist before ever entering
  `_recent_auth`.
- Never persisted: no field in `IndexEntry`, `ExchangeArtifacts`, or
  any log line carries header values.
- Never reflected to the browser: `PipelineTokensResponse` is
  token-numbers-only; `CORS allow-headers` at `config.py:39` accepts
  `Authorization` as a request header but that is about what the UI
  can send *to* manicure, not about manicure responding with auth.
- Cleared at addon shutdown.

The in-memory module singleton is session-scoped and dies with the
process. No leak channels identified.

# Plan adherence

Brief specified:
- One conventional commit per logical change, 3 commits → ✓ delivered
  exactly 3: `refactor(www)`, `feat(api)`, `feat(www)`.
- Subjects align with the logical split: helper extraction first,
  server capability second, UI consumer last.
- No unrelated scope in the diff: only files described in the brief
  are touched.

# Open questions

None. The one real finding (sticky partial stamp) has a clear fix
path and is documented by the engineer; the rest is clean.

# Sign-off

**Ship.** One follow-up ticket should capture the partial-stamp sticky
state (§Self-flagged caveats #1) so the fix does not get lost.
