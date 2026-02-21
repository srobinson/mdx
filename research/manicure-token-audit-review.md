---
title: manicure token-accounting rework — pre-merge review
branch: feat/token-accounting-rework
reviewer: engineering-code-reviewer
reviewed_at: 2026-04-14
audit_spec: ~/.mdx/research/manicure-token-audit.md
verdict: SHIP
---

# Summary

**Verdict: SHIP.**

The branch executes the 8-step plan from `manicure-token-audit.md`. All five
bugs called out in the audit are fixed, the design pivot away from heuristic
`chars // 4` conversion to a real-tokens-or-honest-chars policy is clean, and
the import DAG, async boundary, and file-size rules all hold.

Test baseline is green on both stacks. One low-severity DRY observation (the
context-tokens formula repeats in three UI spots) is the only note worth
flagging, and it is not a blocker.

# Baseline

| Stack | Files | Tests | Result |
| ----- | ----- | ----- | ------ |
| api (pytest) | — | 228 | passed in 0.48s |
| www (vitest) | 11 | 49  | passed in 1.40s |

Branch diff: 32 files changed, 1790 insertions(+), 281 deletions(-).

No TODO / FIXME / XXX / stale `print` or `console.log` / debugger statements
introduced on the branch.

# Correctness

All five audit bugs are resolved against spec.

1. **Cache-creation dropped at the SSE boundary** — `addon.py._parse_sse_stats`
   is fully removed; both paths go through `adapters/anthropic.py`. The JSON
   path at `adapters/anthropic.py:145` and the SSE `message_start` path at
   `adapters/anthropic.py:194` both populate `cache_creation_input_tokens`.
   `storage/base.py:ResStats` carries the field with a `0` default, so legacy
   rows read back cleanly.
2. **Context-total formula** — all three UI consumers use
   `input + cache_creation + cache_read`:
   - `www/src/components/detail/TokenBar.tsx:16`
   - `www/src/components/detail/ExchangeCard.tsx:30-32`
   - `www/src/components/ExchangeList.tsx:47-51`
   No remaining site adds `output_tokens` into the context total. Output
   renders separately on the exchange card (`+{n} tokens generated`) and the
   response breakdown.
3. **Heuristic `tokens_approx = chars // 4` excision** — `grep` for
   `tokens_approx` on the branch returns only a policy comment explaining
   the removal. The `PausedHeader` now renders real tokens from
   `tokens_before` (null-safe with an em-dash) and the per-line ledgers
   label characters honestly (`EditorActions.tsx:253` `CharsLedger`).
4. **Lazy backfill for legacy cache_creation** — `storage/disk.py:92-136`
   `_backfill_cache_creation` uses an O(1) pre-indexed directory lookup and
   writes atomically via `.tmp` rename. Idempotent: it only rewrites rows
   missing the field.
5. **Live `count_tokens` on curated IR** — `counting.py:TokenCounter` wraps
   `/v1/messages/count_tokens` with a 256-entry LRU, caches on
   `(model, system, messages, tools, auth-subset)`, and returns `None` on
   429 / 5xx / 4xx / network / JSON-decode / missing-key / non-int. The
   breakpoint flow wires it in at `api/v1/breakpoint_routes.py:35-54`
   (`_recount_tokens`) and again on re-audit, persisting back to the
   `PausedFlow` via `breakpoint.py:109-120 set_tokens_before` (race-guarded).
   The initial pause count fires via `addon.py:142-171 _fire_pause_count`
   fire-and-forget, emitting a `paused_tokens` SSE event consumed by
   `useExchangeStream.ts:105-114` (with its own race guard).

Async boundary holds: I/O (`count_tokens` HTTP, backfill disk writes) is
async; pure builders (`_build_res_stats`, override application) stay sync.

Import DAG is intact: `counting.py` is a clean leaf imported by
`breakpoint_routes` and `addon`, no back-edges.

# DRY

**Low — context-tokens formula repeats in three places.**

`input + cache_creation + cache_read` appears at:
- `www/src/components/detail/TokenBar.tsx:16`
- `www/src/components/detail/ExchangeCard.tsx:30-32`
- `www/src/components/ExchangeList.tsx:47-51`

Each occurrence is correct and well-commented (the `ExchangeList.tsx` site
has a seven-line block comment justifying "context vs output"). Consolidation
into a `contextTokens(res: ResStats)` helper in `lib/formatting.ts` would
remove the repetition, but the math is trivial and the duplication is
currently load-bearing for in-place readability. Not a merge blocker.

No other notable duplication. The dismissable panel infra (`DismissablePanel`)
is correctly extracted as a reusable component with a stable localStorage
key prefix.

# Execution

- **File size rule respected.** No file touched on this branch exceeds the
  700-LOC ceiling from CLAUDE.md. Largest new file: `test_addon_phases.py`
  at 574 LOC. `addon.py` sits at 548 LOC post-changes. `test_overrides.py`
  at 740 LOC is pre-existing and untouched on this branch.
- **Test coverage targets the right seams.**
  - `test_counting.py` (246 LOC) exercises every failure mode of the wrapper
    (429 / 5xx / 4xx / network / malformed JSON / missing key / non-int)
    plus cache bounds and auth-header forwarding.
  - `test_addon_phases.py` covers the two new async phases with identical /
    distinct / failure / preserves-on-None cases, and includes a regression
    guard at line 288 (`test_build_res_stats_forwards_all_usage_fields`) to
    prevent the original cache-creation drop from silently returning.
  - `test_disk.py` covers backfill with four cases including the atomic
    rewrite and idempotency.
  - `test_breakpoint.py` has `test_re_audit_fires_counter_when_registered`
    and `test_re_audit_skips_counter_when_auth_missing` for the graceful
    degradation path.
- **Cache key design is right.** Auth-subset fold-in
  (`_AUTH_HEADER_KEYS = {x-api-key, authorization, anthropic-version,
  anthropic-beta}`) prevents cross-tenant cache poisoning while keeping the
  key stable across request jitter.
- **Race protections present.** `set_tokens_before` guards against re-audit
  racing the initial pause count; `useExchangeStream.ts` guards the
  `paused_tokens` SSE event against arriving after forward.
- **SSE and forward paths preserved.** `_fire_pause_count` is
  fire-and-forget, so a slow or failing `count_tokens` cannot stall the
  pause. The 45s forward-timeout in `BreakpointEditor.tsx` remains
  untouched.

# Deviations from plan

One intentional, documented deviation, already aligned with the audit spec:

- **Fallback is raw chars with a one-time explainer, not a heuristic
  `chars // 4` conversion.** The audit (and the repo-level project memory
  `project_tokens_vs_chars_display.md`) explicitly call this out as the
  correct policy. `BreakpointEditor.tsx:195-204` adds the
  `editor.chars-vs-tokens` `DismissablePanel` that explains the line-item
  units. The chars-vs-tokens split is enforced: per-override and
  per-category counts are chars; header Tokens / response breakdown /
  pipeline totals are tokens. Honest, no silent 4x lie.

No unplanned scope creep. The brief's "cost chip" focus item is
**not a deviation**: audit §9.3 explicitly lists cost chip as out-of-scope
and the branch correctly omits it.

# Out-of-scope

Deferred by the audit and correctly not attempted on this branch:
- Per-request cost chip (audit §9.3).
- Persisting `tokens_before` / `tokens_after` into the completed-exchange
  index for historical reporting (only live pause + re-audit persist today).
- Deduplicating the three-site context-tokens formula (low-severity DRY;
  safe follow-up).

# Sign-off

Ship. The rework lands the five correctness fixes, honors the
real-tokens-or-honest-chars policy, keeps the async / DAG / file-size
rules, and brings strong targeted test coverage for the new failure modes.
