---
title: Claude offline/client-side token counting in TypeScript (2026)
type: research
tags: [anthropic, claude, tokenizer, typescript, token-counting, offline]
summary: No official Anthropic tokenizer for Claude 3/4 exists in 2026. Xenova/claude-tokenizer via transformers.js is the most practical TS option but is approximate. ctoc (grohan.co, Feb 2026) hits ~96% on a 36,495-token reverse-engineered vocabulary but has no TS port yet. Chars/3.5 heuristic is Anthropic's own official guidance and lands within ~10% for English prose.
status: active
source: deep-research
confidence: high
created: 2026-04-14
updated: 2026-04-14
---

## Executive Summary

Anthropic has not released an official tokenizer for Claude 3 or Claude 4 as of April 2026. The only official TS package, `@anthropic-ai/tokenizer`, is explicitly documented as "no longer accurate" for Claude 3+. For a TS frontend displaying per-block token counts, the practical state of the art is a two-tier approach: use `Xenova/claude-tokenizer` via `@xenova/transformers` for the default counter (browser-capable, ~within 10-15% for prose, worse for code and tool_use JSON), and batch-reconcile with the API's `count_tokens` endpoint on idle. The 3.5-chars-per-token heuristic that Anthropic itself documents is an acceptable fallback for small ephemeral blocks.

## Detailed Findings

### 1. Official Anthropic tokenizer status (April 2026)

There is still no official Anthropic tokenizer for modern Claude models. Three data points:

- `@anthropic-ai/tokenizer` on GitHub (anthropics/anthropic-tokenizer-typescript) carries an explicit warning in its README: "This package can be used to count tokens for Anthropic's older models. As of the Claude 3 models, this algorithm is no longer accurate, but can be used as a very rough approximation. We suggest that you rely on `usage` in the response body wherever possible." 8 total commits, ~100 stars, last touched well before Claude 3 landed.
- The official TS SDK `@anthropic-ai/sdk` exposes `client.messages.countTokens({ model, messages })`, which hits the `/v1/messages/count_tokens` API. This is the billing-grade ground truth but requires a network round-trip and counts against rate limits.
- On the Xenova/claude-tokenizer HuggingFace discussion thread, Xenova himself wrote: "they unfortunately haven't released the v3 tokenizer." That has not changed.

Anthropic's own docs recommend the character heuristic for offline estimation: "1 token ~= 3.5 English characters" with a disclaimer that the exact number varies by language.

### 2. Community tokenizers for Claude

**Xenova/claude-tokenizer (HuggingFace).** Pulled from the old Claude 2 era Python SDK, wrapped as a HuggingFace-compatible tokenizer. Runs in the browser and in Node via `@xenova/transformers` (now published as `@huggingface/transformers`). This is the most widely cited offline option in 2026 and remains the default in several tools because it is the best drop-in BPE approximation available. Accuracy is not officially benchmarked but community consensus places it closer than tiktoken; Xenova acknowledges it is not a true Claude 3/4 tokenizer.

**ctoc (Rohan Gupta, Feb 2026).** A 36,495-token reverse-engineered vocabulary recovered by probing Claude's `count_tokens` endpoint ~277K times over three days. Greedy longest-match tokenization over that vocabulary. Reported accuracy:
- English prose: 99.2%
- Mixed code + docs: 95.1%
- Python source: 96.1%
- Overall: ~96% vs the actual API

The reference implementation is C++ and the vocabulary file is published open source. No npm/TS port exists as of this research, but the approach is portable: ship the vocabulary JSON plus a ~100-line greedy tokenizer. This is the highest-signal recent result and worth tracking.

**Sander Land's analysis (tokencontributions.substack.com).** Claude's tokenizer is unusually "whole word": 8,311 of the 10,000 most common English words are single tokens in Claude 3, exceeding the combined coverage of Llama 3 + Mistral + Cohere + Gemma. Estimated vocabulary around 22K (Land's probe) to 65K+ (other probes). Not a standard BPE. Whole-word bias explains why character-count heuristics drift hard on code and JSON but stay close on prose.

**Outdated / skip:** `@lenml/tokenizer-claude` (npm 403 during research, unclear maintenance), `Jellyfishboy/claude-tokenizer` (Rust only), `javirandor/anthropic-tokenizer` (Python only, 2024), `claude-tokenizer.vercel.app` and `www.claudetokenizer.com` (both hit the live API, not offline).

### 3. Approximation heuristics people actually ship

- **Anthropic official heuristic:** `chars / 3.5` for English. Documented in their token-counting guide.
- **Common rule of thumb:** `chars / 4` or `words * 1.33`. Within ~10% of reality for English prose; drifts 15-25% on code; much worse on dense JSON.
- **Continue.dev (as of issue #9231):** uses GPT-4 `cl100k_base` tiktoken as a Claude proxy and users report ~35% miscalculation. Continue maintainers explicitly recommend using `usage.input_tokens` from API responses instead. This is the concrete production cautionary tale.
- **Claude Code itself:** does not estimate client-side. It relies entirely on `usage` fields returned from the API in the JSONL transcript. Tools like ccusage, tokscale, claude-usage-tracker all read the JSONL after the fact rather than estimating.
- **Cursor, Cline, Roo Code:** no evidence any of them ship a client-side Claude tokenizer. They rely on API response `usage` fields.

### 4. tiktoken-as-proxy accuracy

- HuggingFace-published analysis: Claude's vocabulary overlaps with `cl100k_base` at 70% (45.2K of 65K+ tokens), but the 30% that differs is concentrated in exactly the places that matter (whole-word tokens, non-Latin scripts, code). Result: tiktoken as a Claude proxy runs ~20-35% off in practice.
- Propel's 2025 guide suggests `p50k_base` as an approximation, but still warns it is only an estimate.
- In Continue.dev production, tiktoken proxy produced 130K estimated vs 200K actual (~35% under) at the top of the context window. This is the failure mode to avoid: tiktoken underestimates Claude tokens systematically because Claude has more whole-word tokens than cl100k.

### 5. BPE reimplementations / ported tokenizers

- `Xenova/claude-tokenizer` (HuggingFace, transformers.js compatible)
- `leafspark/claude-3-tokenizer` (HuggingFace, unverified accuracy, smaller user base)
- `Quivr/claude-tokenizer` (HuggingFace, derivative)
- ctoc vocabulary JSON (C++ today, trivially portable to TS)
- `veerashayyagari/llmsharp-tokenizers` (C# only)

### 6. TypeScript/JavaScript specifically

Viable options ranked by practicality for a browser frontend:

1. **`@huggingface/transformers` + `Xenova/claude-tokenizer`** (formerly `@xenova/transformers`). Browser and Node. Async init (loads ONNX-adjacent tokenizer files). Best available for a live UI counter.
2. **Port ctoc's greedy tokenizer to TS.** ~100 LOC + 36,495-entry vocabulary JSON. 96% accuracy per the grohan.co benchmarks. Highest accuracy offline, but requires a small engineering effort and the vocabulary file is ~500KB-1MB gzipped.
3. **`gpt-tokenizer` (niieani, npm).** Fastest tiktoken port for JS. Use only as a last-resort fallback; expect 20-35% error on Claude, worse on tool_use JSON.
4. **Character heuristic `chars / 3.5`.** Zero dependencies, ~10% off on prose, 25%+ on code. Fine for tiny UI affordances (per-keystroke deltas); bad for authoritative totals.
5. **`@anthropic-ai/tokenizer`.** Ignore for Claude 3/4. Only keep in mind if supporting Claude 2.

### 7. Known failure modes

- **Tool-use JSON blocks.** Heavy structured JSON tokenizes worse than prose in every offline method because Claude's tokenizer is whole-word-heavy and JSON is full of punctuation and short tokens. Expect 15-25% drift even with Xenova.
- **Code blocks.** Similar story. ctoc reports 96.1% on Python but that is best-case; obscure languages or dense symbols drift more.
- **System prompt caching.** API `usage` returns `cache_creation_input_tokens` and `cache_read_input_tokens` separately. No offline method estimates cache effects.
- **Multi-byte / CJK text.** Xenova/claude-tokenizer vocabulary includes only ~1,100 Chinese tokens plus minimal Korean/Cyrillic/Thai. Drift here is severe (30%+).
- **Very long messages.** Greedy tokenization stays accurate; drift is per-token, not cumulative.
- **Images, PDFs.** No offline method handles these; `countTokens` API is the only option.

## Concrete Recommendation for Your TS App

**Primary:** `@huggingface/transformers` with `Xenova/claude-tokenizer`. This runs in the browser, is actively used by dozens of tools, and is the best practical offline option until someone publishes a ctoc JS port.

```ts
import { AutoTokenizer } from '@huggingface/transformers';
const tokenizer = await AutoTokenizer.from_pretrained('Xenova/claude-tokenizer');
const tokens = tokenizer.encode(text).length;
```

**Secondary (high signal):** Fork or reimplement ctoc in TS. The vocabulary is public (grohan.co / GitHub). ~100 LOC greedy matcher + a 36K-entry vocabulary JSON gets you to 96% accuracy with no async model load.

**Authoritative reconciliation:** On idle or on save, fire a single `client.messages.countTokens(...)` API call per conversation to reconcile the displayed per-block estimates with ground truth. Display a delta indicator when the local estimate drifts >5% from the authoritative count.

**Fallback:** Anthropic's official `chars / 3.5` heuristic for per-keystroke updates where network-free, sub-millisecond response matters more than accuracy.

### Expected accuracy range

- Xenova/claude-tokenizer on English prose: within ~5-10% of the API.
- Xenova on code: 10-20% off.
- Xenova on dense tool_use JSON: 15-25% off.
- ctoc port (if built): 96%+ overall, 99%+ on prose.
- tiktoken proxy: 20-35% off (do not use).
- `chars / 3.5`: ~10% on prose, 20-30% on code.

## Sources Consulted

### GitHub / npm
- [anthropics/anthropic-tokenizer-typescript](https://github.com/anthropics/anthropic-tokenizer-typescript) (explicit Claude 3+ disclaimer)
- [javirandor/anthropic-tokenizer](https://github.com/javirandor/anthropic-tokenizer) (Python reverse-engineered, 2024)
- [Jellyfishboy/claude-tokenizer](https://github.com/Jellyfishboy/claude-tokenizer) (Rust)
- [niieani/gpt-tokenizer](https://www.npmjs.com/package/gpt-tokenizer)
- [continuedev/continue issue #9231](https://github.com/continuedev/continue/issues/9231) (production failure with tiktoken proxy)
- [Xenova/claude-tokenizer discussion #1](https://huggingface.co/Xenova/claude-tokenizer/discussions/1) (Xenova confirms no v3 tokenizer)

### HuggingFace
- [Xenova/claude-tokenizer](https://huggingface.co/Xenova/claude-tokenizer)
- [leafspark/claude-3-tokenizer](https://huggingface.co/leafspark/claude-3-tokenizer)

### Blog posts and analysis
- [Rohan Gupta — Reverse Engineering Claude's Token Counter (ctoc), Feb 2026](https://grohan.co/2026/02/10/ctoc/) (96% accuracy benchmark)
- [Sander Land — Whole words and Claude tokenization](https://tokencontributions.substack.com/p/whole-words-and-claude-tokenization) (vocabulary structure analysis)
- [Propel — Token Counting Guide 2025](https://www.propelcode.ai/blog/token-counting-tiktoken-anthropic-gemini-guide-2025)
- [Peta Muir — Counting Claude Tokens Without a Tokenizer](https://blog.gopenai.com/counting-claude-tokens-without-a-tokenizer-e767f2b6e632)

### Anthropic docs
- [Token counting](https://platform.claude.com/docs/en/build-with-claude/token-counting) (chars/3.5 heuristic)
- [messages.count_tokens API reference](https://platform.claude.com/docs/en/api/messages/count_tokens)

## Source Quality Assessment

High confidence on: Anthropic not having an official tokenizer (confirmed from multiple independent sources including Xenova's own admission). Xenova being the incumbent offline TS option. ctoc's 96% number (grohan.co is a single source but methodology is documented and reproducible; the 277K probe calls are a legitimate benchmark).

Medium confidence on: exact accuracy numbers for Xenova on tool_use JSON (no single published benchmark; figure is triangulated from Continue.dev incident and Sander Land's whole-word analysis).

Low signal from: Reddit (essentially zero substantive discussion on Claude offline tokenizers; the community fragments across HN, GitHub issues, and Substack). Twitter/X (also sparse).

## Open Questions

- Has anyone published a ctoc JS/TS port as of April 2026? Not found in search. Opportunity for a small npm package.
- Exact accuracy of Xenova tokenizer on Claude 4 specifically. No published benchmark; prior comparisons all target Claude 3.
- How much does the Claude 4.x vocabulary differ from 3.x? ctoc targets 4.x explicitly and found a ~36K vocabulary; Xenova is rooted in pre-3 vocabulary. This gap may widen.

## Actionable Takeaways

1. Wire `@huggingface/transformers` + `Xenova/claude-tokenizer` as the default counter. Initialize once, memoize per block.
2. Add a "reconcile with API" mechanism that fires on idle or explicit user action. Store the authoritative count; show a drift indicator when local and authoritative diverge.
3. For heavy tool_use blocks specifically, apply a 1.15-1.25x multiplier on the Xenova estimate to compensate for JSON/punctuation drift, or prioritize reconciling those blocks first.
4. Watch grohan.co and the ctoc repo for a JS port. If none appears in 2-3 months, porting ctoc to TS is a worthwhile investment: ~100 LOC + a JSON vocabulary, closes the accuracy gap to 96%+.
5. Do not ship tiktoken as a Claude proxy. The Continue.dev precedent is explicit.
