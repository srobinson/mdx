---
title: Manicure v0.0.1 Captures — Source Data for Landing Claims
project: manicure
type: measurement-log
date: 2026-04-14
source: Manicure v0.0.1 UI screenshots shared with orchestrator by Stuart
audit_status: pending
---

# Manicure Captures: Measurement Log

This file is the canonical source for every numeric claim on the manicure.sh landing page. If a number on the page is not traceable to a row in this file or a public source, it is invalid and must be removed.

Captures were taken from Manicure v0.0.1 running locally against real `claude-opus-4-6` sessions on 2026-04-14 and shared as screenshots with the orchestrator. Stuart has flagged that a **full audit is pending** — specifically:

- The `BUDGET` panel breakdown (SYSTEM / TOOLS / MESSAGES) and the `PIPELINE` delta figures are reported in **characters**, not tokens. Labels in the UI will be corrected in a future release.
- The `INPUT / CACHE_READ / OUTPUT` fields on the capture summary are reported in **tokens** (Anthropic API field names).
- Percentage deltas (`-39%`, `-44%`) are **unit-invariant** and valid regardless of whether the underlying counts turn out to be chars or tokens.

Until audit is complete, landing copy must:

- Use `INPUT / CACHE_READ / OUTPUT` figures directly when claiming "tokens."
- Cite `BUDGET` breakdown figures as characters, not tokens.
- Prefer percentage deltas over raw counts where the unit is uncertain.

---

## Capture A — Image 4 (warroom screenshot shared 2026-04-14)

Manicure v0.0.1 session in the `ARMED ONCE` state, three exchanges captured, the first-row exchange highlighted.

- Model: `claude-opus-4-6`
- Exchanges: 3
- Elapsed: 01:04
- Flow id: `37d2872f`
- Top-row summary: `148 tools`, `215.9K` input, `239` out, `TOOL_USE`
- Turn type: paused, post-override

**Pipeline panel (characters, pending audit):**

- SAVED: `-90.0K` (`-39%`)
- BEFORE: `230.2K`
- AFTER: `140.2K`
- Breakdown:
  - SYSTEM `27.3K` (unchanged)
  - TOOLS `177.0K → 98.3K` (`-44%`)
  - MESSAGES `26.0K → 14.6K` (`-44%`)
- Overrides: `112 overrides`
- User blocks: `5 blocks` (`3 MODIFIED`)

**Landing claims this capture supports:**

- `112 overrides · -39%` (Pillars Tamper micro-visual)
- `-39%` standalone (one override pass aggregate savings)
- `-44%` on tools (one override pass tool-schema savings, unit-invariant)
- `148 tools ride along` (tool count visible on row)
- `230.2K characters to deliver it` (ONLY when "characters" is the explicit unit)

**Landing claims this capture does NOT support:**

- `230,000 tokens` (this is characters, not tokens, pending audit)
- `177,000 tokens of tool schemas` (characters, not tokens)
- Any tool-count delta like `147 → 23` or `148 → N` (Manicure overrides adjust token budget, not tool count)

---

## Capture B — Image 5 (warroom screenshot shared 2026-04-14)

Manicure v0.0.1 session in the `ARMED ONCE` state, four exchanges captured, the first-row exchange highlighted.

- Model: `claude-opus-4-6`
- Exchanges: 4
- Captured: `Apr 14 · 09:37:41`
- Flow id: `f15a7aa5`
- State: `ARMED ONCE`

**Capture summary (tokens, Anthropic API field names):**

- `input_tokens`: `45,728`
- `cache_read_input_tokens`: `9,053`
- `output_tokens`: `412`
- System: `3 system messages`, `28 tools`

**Landing claims this capture supports:**

- `Your agent sends 45,728 tokens to deliver it.` (token-native hero subline, current)
- `28 tool schemas compete for the model's attention.` (hero subline, current)
- `9,053 tokens cache_read` (if cache economics are cited)
- `412 output tokens` (if response size is cited)

---

## Capture C — Image 6 (warroom screenshot shared 2026-04-14)

Same session as Capture B, post-`PIPELINE` delta computed.

- `PIPELINE`: `-38%`
- `BEFORE`: `232.1K` characters (Stuart flagged this figure as characters explicitly)
- `AFTER`: `144.2K` characters
- `TOOL_TOOLS`: `-78.6K`
- `MESSAGE_BLOCK_TOOLS`: `-13.0K`

**Landing claims this capture supports:**

- `-38%` aggregate delta (unit-invariant)
- `-78.6K chars tool-schema reduction` (when chars are the explicit unit)

**Landing claims this capture does NOT support:**

- `232.1K tokens` (explicitly characters per Stuart)

---

## Open items (resolve before ship)

1. Audit the Manicure v0.0.1 UI to decide: is the `BUDGET` panel reporting characters, tokens, or bytes? The labels should match the unit.
2. Once audit is complete, update this file with the definitive unit for each figure and revisit landing copy.
3. If Manicure emits token counts from the Anthropic API response `usage` field alongside char counts from byte inspection, the landing can cite both — but each claim must carry its unit explicitly.

---

## Citation format for landing copy

When the landing references a number from this file, comment or annotate it near the usage site like:

```tsx
// source: ~/.mdx/projects/manicure-captures-2026-04-14.md · Capture A · Pipeline panel
<span>112 overrides · -39%</span>
```

This keeps the traceability chain explicit in the codebase and survives future audits.
