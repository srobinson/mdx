---
title: Manicure token accounting audit
date: 2026-04-14
author: manicure:helioy-tools:backend-engineer:1:2.1
status: investigation (no code changes)
scope: api/src/manicure, www/src
---

# Manicure token accounting audit

## 1. Summary

Manicure captures four Anthropic usage fields in the response IR but drops one (`cache_creation_input_tokens`) at the storage boundary. The UI, compounding the loss, sums `input + output + cache_read` and labels it "tokens" — a quantity with no principled meaning. The canonical context-window cost is `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`, which is what the user's statusline shows and what Manicure silently disagrees with.

Pipeline savings are tracked in characters, not tokens, and converted to an `tokens_approx = |chars_delta| // 4` estimate that undercounts by roughly 35% against the observed 2.63 chars/token ratio seen in captured traffic. The character counter itself is a hybrid (plain text for `system`, `json.dumps` for tools, Pydantic `model_dump_json` for messages) and is not wire-byte accurate.

Historical data is recoverable. The full UsageStats object is preserved in each exchange's `response.ir.json` artifact, so a backfill pass over the index JSONL can repopulate `cache_creation_input_tokens` without replaying traffic. Only the computed totals currently displayed to users are wrong.

This report confirms the two bugs named in the brief, documents three additional defects along the same code path, evaluates tokenizer options, and proposes an ordered fix plan with per-file test impact.

## 2. Anthropic usage semantics

From the Messages API reference (`platform.claude.com/docs/api/messages`) and the prompt caching guide (`platform.claude.com/docs/agents/prompt-caching`):

| Field                          | Meaning                                                                                                         |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `input_tokens`                 | Non-cached input tokens processed this request. Billed as fresh input.                                          |
| `output_tokens`                | Tokens the model generated in the response. Billed as output.                                                   |
| `cache_creation_input_tokens`  | Tokens written into the prompt cache this turn. Billed at the write rate (125% of input).                       |
| `cache_read_input_tokens`      | Tokens served from the cache this turn. Billed at the read rate (10% of input).                                 |

Two derivations follow:

- **Total context tokens for the turn** = `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. This is what fits into the model's window. `output_tokens` is produced, not consumed, so including it conflates context cost with generation cost.
- **Billable cost** is a weighted sum across the four fields; Manicure does not need cost today but should keep the data intact for future use.

The `/v1/messages/count_tokens` endpoint (`platform.claude.com/docs/api/messages-count-tokens`, transcript cached at `~/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-manicure/13de326c-1e6e-453b-b093-ab7f188fa07d/tool-results/toolu_019taVNQFnhkrSWbixJXyqvz.txt`) returns a single `{input_tokens: N}` — it does not preserve the cache split and it does not use prompt caching at all. It is free, tier-limited (tier 1: 100 RPM, tier 2: 2000 RPM, tier 3: 4000 RPM, tier 4: 8000 RPM), and works with the full `messages` + `system` + `tools` shape Manicure already has in IR form. It is the right tool for validating a pipeline override's "before" count, but it cannot reconstruct the cache breakdown post hoc.

SSE streaming emits usage in two places: `message_start.message.usage` carries `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens` at turn start; `message_delta.usage` carries the running `output_tokens` (Anthropic's public docs describe this as cumulative). This distinction matters for bug 3 below.

## 3. Current data flow (file:line)

```
mitmproxy response
   → adapters/anthropic.py:_inbound_response_{json,sse}      # builds ResponseIR + UsageStats
   → addon.py:_build_res_stats  /  _parse_sse_stats          # builds ResStats for the index
   → storage/disk.py (IndexEntry → index.jsonl)              # on-disk authority
   → server routes → www /api/exchanges → React TokenBar/ExchangeCard
```

Points of interest:

- **`api/src/manicure/ir.py:148-154`** — `class UsageStats` carries all four fields as `int` with default `0`. Capture is correct.
- **`api/src/manicure/adapters/anthropic.py:140-146`** — JSON response path reads all four fields verbatim.
- **`api/src/manicure/adapters/anthropic.py:165-243`** — SSE path; `message_start` sets three fields (input, cache_creation, cache_read), `message_delta` updates `output_tokens`. This adapter is the authoritative parser and matches the public SSE schema.
- **`api/src/manicure/storage/base.py:43-51`** — `class ResStats` omits `cache_creation_input_tokens`. This is the first lossy boundary.
- **`api/src/manicure/addon.py:56-80`** — `_build_res_stats` maps `UsageStats → ResStats` and drops the field (not present in target).
- **`api/src/manicure/addon.py:83-142`** — `_parse_sse_stats` reimplements SSE parsing independently of the adapter, with `+=` accumulation over `message_delta.usage`, and also never sets `cache_creation`.
- **`api/src/manicure/addon.py:287-296`** — `_build_pipeline_stats` sets `tokens_approx = abs(audit.chars_delta) // 4`; propagates through index as `pipeline.tokens_approx`.
- **`api/src/manicure/overrides.py:121-151`** — `OverrideAudit` records `chars_before/after` per category; `count_chars_parts` implements the hybrid plain-text / JSON / model-dump-json measurement.
- **`api/src/manicure/storage/disk.py:~40-180`** — writes `response.ir.json` with the full `ResponseIR` (UsageStats intact) plus the lossy `IndexEntry.res` into `index.jsonl`.
- **`www/src/types.ts:11-18`** — TS `ResStats` mirrors the lossy Python type. Field absent.
- **`www/src/types.ts:165-170`** — TS `UsageStats` includes `cache_creation_input_tokens`, but the UI never reads the full IR into a UsageStats; it consumes `entry.res` (ResStats) only.
- **`www/src/components/detail/TokenBar.tsx:12`** — `const total = input + output + cache;` (misleadingly named `cache`; the argument comes from `cache_read_input_tokens`).
- **`www/src/components/detail/ExchangeCard.tsx:26`** — `tokenTotal = res.input_tokens + res.output_tokens + res.cache_read_input_tokens`; same formula.
- **`www/src/components/detail/ExchangeCard.tsx:93-98`** — passes `(input, output, cache_read)` triple into `TokenBar`.
- **`www/src/components/editor/EditorActions.tsx:243-453`** — `TokenLedger` component displays `*_chars_before/after` as if they were tokens; the visual denomination is characters.
- **`www/src/components/ExchangeList.tsx:74-80`** — list row shows `req.total_chars` as KB and `res.output_tokens`; does not surface cache fields at all.

## 4. Bugs found

### Bug 1 — `ResStats` drops `cache_creation_input_tokens` (reported)

- **Files**: `api/src/manicure/storage/base.py:43-51`, `api/src/manicure/addon.py:56-80`, `api/src/manicure/addon.py:83-142`, `www/src/types.ts:11-18`.
- **Symptom**: The index JSONL row for every exchange is missing the cache-write count; only the full `response.ir.json` artifact has it. The UI cannot render a correct context-window total from the list payload.
- **Severity**: High. Drives bug 2 and breaks the statusline ↔ Manicure agreement that motivated this audit.
- **Nature**: Schema omission plus mechanical mapping omission. Reversible (see §8).

### Bug 2 — UI "total tokens" formula uses `output_tokens` in place of `cache_creation_input_tokens` (reported)

- **Files**: `www/src/components/detail/TokenBar.tsx:12`, `www/src/components/detail/ExchangeCard.tsx:26`, `www/src/components/detail/ExchangeCard.tsx:93-98`.
- **Symptom**: The "Tokens" chip on an exchange card sums `input + output + cache_read`. For a response that returned e.g. 400 output tokens against a 40k context, the widget shows `~40.4k` where the correct context figure is `~40k + cache_creation`. The statusline reads `~80k` because it correctly includes cache_creation; users see two disagreeing figures for the same request.
- **Severity**: High. Misleading top-line metric.
- **Nature**: Formula defect; fix is local once bug 1 lands.

### Bug 3 — duplicate SSE parser in addon with `+=` accumulation (new)

- **Files**: `api/src/manicure/addon.py:83-142` (addon copy), `api/src/manicure/adapters/anthropic.py:165-243` (adapter copy).
- **Symptom**: Two independent SSE parsers run on the same event stream. The adapter is authoritative and well-tested; the addon copy exists only to build `ResStats` during the mitmproxy response hook. It uses `+=` against `message_delta.usage.output_tokens` on every delta.
- **Concern**: Anthropic SSE emits the `message_delta.usage` value as the running total, not an increment (confirmed against the adapter's own logic at `anthropic.py:213-221`, which does `stats.output_tokens = delta["usage"]["output_tokens"]`). If the addon is accumulating a cumulative value, it overcounts on any stream with more than one delta. Requires verification against a real captured stream before we can call this confirmed (see §9).
- **Severity**: Medium. Possibly correct by coincidence if the stream only ever emits one delta, but the divergence from the adapter is itself the defect.
- **Nature**: Duplication. Best fix is to delete the addon's parser and reuse the adapter's `ResponseIR` + `UsageStats`, which already has the correct fields at that layer.

### Bug 4 — `tokens_approx = |chars_delta| // 4` undercounts pipeline savings (new)

- **File**: `api/src/manicure/addon.py:287-296`.
- **Symptom**: Fixed heuristic of 4 chars per token. On an exchange where the override saves 10,000 chars, the UI reports `2500` tokens saved. Observed chars/token ratio on recent captured traffic is closer to 2.63, so the real figure is nearer 3,800 — a ~35% understatement.
- **Concern**: The ratio is not universal; code-heavy contexts tokenize denser, prose tokenizes thinner. A fixed constant is always wrong; only the direction varies.
- **Additional concern**: The field is named `tokens_approx` but the UI widget the brief's screenshot showed (compression bar) uses it as an authoritative label. The name's approximation hint is lost in the presentation.
- **Severity**: Medium. The UI distinguishes "chars" from "tokens_approx" and presents both, so sophisticated users can reconcile. Casual users will mistrust the tool.

### Bug 5 — `count_chars_parts` hybrid measurement is not wire-accurate (new)

- **File**: `api/src/manicure/overrides.py:140-151`.
- **Symptom**: The function measures `system` as plain-text `len()`, tool blocks as `len(json.dumps(schema))`, and messages as `len(model_dump_json(...))`. None of these equal wire bytes or semantic token count. They are useful as a self-consistent internal metric (before/after on the same measure) but misleading if consumed as an external reference.
- **Severity**: Low. Internal consistency is preserved as long as both sides of a diff use the same function. Becomes a problem the moment a value leaks into user-facing "tokens".
- **Nature**: Design choice that accreted. Could be replaced by a single canonical serializer (e.g. always `ResponseIR.model_dump_json()` on the relevant slice) or reframed as "bytes" in the UI.

## 5. Tokenizer evaluation

Four candidates for deriving a token count from a client-side payload.

### 5.1 `/v1/messages/count_tokens`

- **Input**: `{model, messages, system?, tools?}`. Accepts the same shape Manicure already holds as IR.
- **Output**: `{input_tokens: N}`. Single figure; no split between fresh/cached.
- **Pricing**: Free.
- **Rate limits**: 100/2000/4000/8000 RPM at tiers 1-4. Comfortable for an inspection tool; unsuitable for autoscaled production traffic.
- **Caching**: Request does not populate the prompt cache, so it is safe to call alongside the real request.
- **Fit for Manicure**: Best option for validating the "before" side of a pipeline override in real time (armed breakpoint has the IR; a single call gives an authoritative count). Not a fit for back-fill against historical exchanges without re-serializing every row, and still cannot recover the cache_creation split.

### 5.2 `tiktoken` or other OpenAI BPE libraries

- **Reality**: Trained on OpenAI vocabularies. Wrong vocabulary for Claude models. Off-by-20-to-40% on typical mixed payloads.
- **Recommendation**: Do not adopt. Whatever consistency it offers is against the wrong target.

### 5.3 Third-party `claude-tokenizer` ports

- **Reality**: A handful of JS/Python ports exist for Claude 2-era models; none are officially maintained by Anthropic and none cover Sonnet 4 / Opus 4 / Haiku 4 reliably. Silent drift on model updates.
- **Recommendation**: Do not adopt.

### 5.4 Self-calibration from observed chars/token ratios

- **Mechanism**: Every completed exchange gives us ground truth (`UsageStats.input_tokens + cache_creation + cache_read`) and the `chars_before` we already measure. Store a rolling per-model ratio. Apply it when estimating pipeline savings in tokens.
- **Pro**: Zero external dependency. Self-correcting. No rate limit.
- **Con**: Only works once there are N completed exchanges for the current model.
- **Recommendation**: Adopt as a replacement for the `// 4` constant. First exchange on a new model falls back to 4; subsequent exchanges use `chars_saved * tokens_total / chars_total` from the same turn, EMA-blended across history.

**Combined recommendation**: (5.1) for live breakpoint validation, (5.4) for historical pipeline savings. Do not ship (5.2) or (5.3).

## 6. Proposed fix plan

Ordered by minimum diff and maximum signal. Each step is independently shippable.

1. **Add `cache_creation_input_tokens: int = 0` to `ResStats`** (`api/src/manicure/storage/base.py:43-51`). Pydantic default makes this backward compatible; old JSONL rows load with 0. Also update `www/src/types.ts:11-18`.

2. **Map the field in `_build_res_stats`** (`api/src/manicure/addon.py:56-80`). One line.

3. **Delete `_parse_sse_stats`** (`api/src/manicure/addon.py:83-142`) and build `ResStats` from the adapter's `ResponseIR.usage` at the mitmproxy response hook. Bug 3 dissolves — one parser, one source of truth. If the hook runs before the adapter has finished parsing, serialise the adapter's SSE output first and derive `ResStats` downstream, rather than duplicating the parser.

4. **Fix UI totals** (`www/src/components/detail/TokenBar.tsx:12`, `www/src/components/detail/ExchangeCard.tsx:26, 93-98`). New formula: `context_tokens = input + cache_creation + cache_read`. Label: "context tokens". Show `output_tokens` as a separate, secondary metric ("+ {n} generated") since it is not a context-window cost. Rename the `cache` prop to `cache_read` in `TokenBar` so the source of truth is visible.

5. **Backfill the index** (`api/src/manicure/storage/disk.py`). On read, if `res.cache_creation_input_tokens` is missing or 0 and `response.ir.json` exists, re-hydrate from the artifact and rewrite the row. Lazy backfill avoids a blocking migration; N exchanges get corrected as the user browses.

6. **Replace `tokens_approx`** (`api/src/manicure/addon.py:287-296`). Two paths:
   - Short term: keep the name, swap the divisor for the rolling per-model ratio (§5.4). Add a `TokensRatioEstimator` in `storage/` (sync, pure — pipeline action rules apply).
   - Long term: drop `tokens_approx` entirely, expose only `chars_delta`, and let the UI label compression as "bytes saved". Simpler, and consistent with the statusline/Manicure split of roles (statusline owns tokens; Manicure owns pipeline diffs).

7. **Optional — count_tokens in the breakpoint flow**. When the breakpoint is armed and has an IR, kick off `count_tokens` alongside the pause. Surface the result as an authoritative "before" count in the override editor. Free, accurate, and gives the user a real number where they currently see a heuristic.

8. **Rename UI labels that conflate chars and tokens**. `www/src/components/editor/EditorActions.tsx:243-453` displays characters in a component called `TokenLedger`. Either rename to `CharsLedger` or switch to actual tokens using (7).

Steps 1, 2, and 4 deliver the user-visible fix for the reported bug. Steps 3, 5, 6, 7, 8 are quality improvements along the same seam.

## 7. Test impact

| File | Lines | Change needed |
| ---- | ----- | ------------- |
| `api/src/manicure/test_addon_phases.py` | 144-263 | `tokens_approx == 50` assertion rebases onto new ratio model. `_parse_sse_stats` fixtures delete if step 3 lands; otherwise add `cache_creation_input_tokens` expectations. |
| `api/src/manicure/adapters/test_anthropic.py` | 234-331 | `SAMPLE_RESPONSE` already has all four usage fields; assertions may need to confirm `ResStats` carries `cache_creation_input_tokens` through. `SSE_WITH_THINKING_STREAM` only sets `output_tokens` in `message_delta` — confirms §9's assumption once turned into an assertion on cumulative semantics. |
| `api/src/manicure/storage/test_disk.py` | ~110 | Add `cache_creation_input_tokens` field to fixtures. Add round-trip test for the backfill path (step 5). |
| `api/src/manicure/test_overrides.py` | 727, 731, 739 | Update any hard-coded expected chars if `count_chars_parts` semantics change (not proposed above, but flag in case). |
| `www/src/components/ExchangeList.test.tsx` | 22-29 | Fixture `res` object needs `cache_creation_input_tokens: 0` once TS type gains the field. |
| `www/tests/visual/fixtures.ts` | 53, 64 | Same — add the field to `mockExchanges[n].res`. Screenshots for token-bar regress if the formula changes; Playwright visual suite will surface the diff. |

No new test files required; all extensions land next to existing coverage.

## 8. Historical data impact

The good news: `response.ir.json` on disk is complete. Every exchange's `UsageStats` is preserved with all four fields (confirmed via `api/src/manicure/adapters/anthropic.py:140-146` and `storage/disk.py` write path). Only the derived index row is lossy.

Three migration options:

- **(a) None**. After step 1, old rows deserialize with `cache_creation_input_tokens = 0`. UI totals under-report the cache-write portion for historical exchanges. Acceptable if the dev workflow only cares about going-forward behaviour.
- **(b) Lazy backfill** (recommended; step 5 above). On exchange read, if the field is zero and the artifact exists, rehydrate from `response.ir.json` and rewrite the index row. Amortised cost, no blocking migration.
- **(c) Eager rewrite**. One-shot pass over `index.jsonl` rehydrating every row from its artifact. Straightforward to implement as a CLI subcommand (`manicure reindex`), useful if a user wants accurate totals for a large existing backlog.

For `chars_before/chars_after`, there is no backfill path — those measurements depend on an `OverrideAudit` that only exists when a pipeline rule fires. No historical correction is possible; forward behaviour is the only lever.

## 9. Open questions

1. **Cumulative vs incremental `message_delta.usage.output_tokens`**. The adapter at `anthropic.py:213-221` assigns (`=`), the addon at `addon.py:~120` accumulates (`+=`). Anthropic's public docs say the value is cumulative, but a captured real streaming response would close the question. Run one streaming call against the proxy and dump the raw SSE before landing step 3.

2. **`count_tokens` cache semantics on our exact payloads**. The endpoint docs say it does not use prompt caching, but do not say whether a message already-cached at Anthropic's end is reflected in the count. If the count ignores any caching and always returns "as-if-fresh" input tokens, great — it gives a stable "before" reference. If it implicitly reflects cache state, the number is not a pure function of the IR and the contract changes. Worth confirming with a deliberate back-to-back test.

3. **Whether to surface cost, not just tokens**. Once the four fields survive to the UI, synthesising a dollar figure is a ~20-line addition. Out of scope for this fix, but worth deciding if a "Cost" chip should replace or accompany the "Context tokens" chip.

4. **Chars-as-tokens relabelling**. `TokenLedger` (`www/src/components/editor/EditorActions.tsx:243-453`) and the compression bar's "saved" value both present chars as if they were tokens. Is the right move to rename the component and labels, or to migrate the underlying metric to true tokens via count_tokens / self-calibrated ratio? The first is honest; the second is useful. Not both required.

5. **Per-adapter discipline**. Only `AnthropicAdapter` is registered today (`api/src/manicure/adapters/__init__.py`). If OpenAI/Gemini adapters land, each will have its own usage shape. The fix plan should leave the type system honest: `UsageStats` already carries the Anthropic-specific cache fields. Either generalise to a provider-tagged union, or acknowledge the Anthropic-shaped names as the canonical cross-provider schema and translate at ingress.

---

*Investigation only; no code changed. Sources cited inline via `path:line`. Backing research transcripts at `/Users/alphab/.claude/projects/-Users-alphab-Dev-LLM-DEV-helioy-manicure/13de326c-1e6e-453b-b093-ab7f188fa07d/tool-results/`.*
