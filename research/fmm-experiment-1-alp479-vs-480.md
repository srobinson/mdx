---
title: "Experiment 1: fmm Navigation Efficiency (ALP-479 vs ALP-480)"
type: research
tags: [fmm, experiment, navigation, token-efficiency, context-window]
summary: "A/B experiment proving navigation dominates agent context window (41-52%) and fmm yields 33% token savings, but agent ignored sidecars entirely (0/55 usage)"
status: active
project: fmm
confidence: medium
created: 2026-02-02
updated: 2026-02-21
---

# Experiment 1: fmm Navigation Efficiency

**Task:** OpenClaw #5606 — voice call extension
**Repo:** openclaw/openclaw (3071 files)
**Date:** 2026-02-02
**Analyzer:** `nancy src/analyze` (ALP-487)

## Comparison Table

```
                           Control (no fmm)    Treatment (fmm)
                           ──────────────────  ─────────────────
Reads before first edit:   25                  40
Greps before first edit:   2                   0
Unique files discovered:   15                  24
Navigation tokens:         ~30,292             ~15,884
Navigation % of total:     52%                 41%
Time to first edit:        iter1 @ 48%         iter1 @ 13%
Sidecar lookups:           n/a                 0/55
Task complete:             yes                 yes
Total iterations:          3                   4
Total tokens:              ~58,310             ~39,111
```

## Per-Iteration Detail

### Control (ALP-480, no fmm)

| Iteration    | Nav Calls | Nav Tokens | Total Tokens | First Edit |
| ------------ | --------- | ---------- | ------------ | ---------- |
| iter1        | 20        | 24,816     | 51,187       | seq 95     |
| iter2        | 18        | 2,763      | 2,763        | no edits   |
| iter2-review | 18        | 2,713      | 4,360        | seq 85     |

### Treatment (ALP-479, fmm available)

| Iteration    | Nav Calls | Nav Tokens | Total Tokens | First Edit |
| ------------ | --------- | ---------- | ------------ | ---------- |
| iter1        | 39        | 3,040      | 24,134       | seq 151    |
| iter2        | 9         | 1,391      | 1,391        | no edits   |
| iter3        | 8         | 1,286      | 1,286        | no edits   |
| iter3-review | 13        | 10,167     | 12,300       | seq 64     |

## Key Findings

1. **Treatment used 33% fewer total tokens** (39k vs 58k) despite having more iterations.

2. **Treatment reached first edit much earlier** within iter1 (13% vs 48%). Agent oriented faster even with more navigation calls (39 vs 20).

3. **Zero sidecar usage.** 0/55 navigation lookups used fmm tools or read `.fmm` files. All were raw reads/greps. Confirms the instruction compliance problem — agent ignores sidecar instructions under task pressure.

4. **More nav calls in treatment, but fewer nav tokens.** 69 total nav calls vs 56 for control, yet ~16k nav tokens vs ~30k. Treatment's nav calls were lighter-weight.

5. **Navigation dominated both conditions.** 52% (control) and 41% (treatment). Navigation is the largest cost center in both. Validates the thesis.

## Caveats

- Single experiment pair (n=1). Not statistically significant.
- Control and treatment worked on the same GitHub issue but in different repo states.
- "No edits" iterations appear to be sessions that ran out of context or were interrupted.
- Token counts are `input_tokens + output_tokens` only; cache tokens tracked separately.

## What This Led To

The zero sidecar usage finding directly motivated:

- Building fmm as an MCP server (agent uses it because it's the most convenient path)
- The fmm skill with instructions loaded at decision points
- Attention-matters as the answer to the broader memory/rediscovery problem

## Raw Data

Original experiment data preserved at `/Users/alphab/Dev/LLM/DEV/docs/experiments/ALP-479-vs-480.json`
