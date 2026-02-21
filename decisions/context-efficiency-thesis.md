---
title: "Context Efficiency Thesis: Navigation, Not Memory"
type: decisions
tags: [architecture, context-window, fmm, attention-matters, navigation, thesis]
summary: "The founding thesis behind Helioy: maximize signal-to-noise ratio of tokens in the context window by compressing navigation (fmm) and eliminating rediscovery (attention-matters)"
status: active
project: helioy
confidence: high
created: 2026-02-02
updated: 2026-02-21
---

# Context Efficiency Thesis

> Origin: Three progressive reframes during a single session on 2026-02-02, captured in the original `MEMORY_PROPOSAL.md`. This document preserves the intellectual arc that became Helioy's founding thesis.

## The Problem

LLMs have limited context windows. This is the number one blocker for LLMs being truly useful. Everything in Helioy is an attempt to work around or solve this constraint.

## Project Lineage

Each project emerged from hitting the ceiling of the one before it:

```
Context window is too small — the root constraint
  └─ Nancy: keep the LLM working despite the limit (orchestration)
     └─ mdcontext: LLMs produce markdown nobody reads — make it searchable (search)
        └─ fmm: what if code itself had metadata LLMs could navigate? (navigation)
           └─ attention-matters: what if the agent had persistent memory across sessions? (memory)
```

## Three Reframes

### Reframe 1: Memory (naive)

Agents rediscover the same things every iteration. Distill logs into structured YAML memory files that the next session loads at start. Search traces, discovery artifacts, durable vs discardable knowledge.

**Flaw:** Loading memory into the prompt IS consuming the context window. Even 50 lines of YAML is tokens the agent can't use for the actual task.

### Reframe 2: Navigation (subagent model)

You cannot feed the LLM memory. The LLM must navigate TO memory on demand. Spawn subagents for lookups — parent burns ~20 tokens per query, subagent burns 2000 exploring then its context is discarded.

**Flaw:** It's a black box. Summarization is lossy. The parent still needs enough context to make decisions. It's just moving the problem.

### Reframe 3: Signal-to-Noise Ratio (the thesis)

**The hard truth: there is no external memory system.** Everything the agent "knows" must be in the context window. The only lever is how valuable each token is.

Token categories in a typical agent session:

- **Task tokens** — the actual work. HIGH VALUE.
- **Navigation tokens** — figuring out what's where. LOW VALUE. This is what fmm compresses.
- **Rediscovery tokens** — learning things a previous iteration already knew. ZERO VALUE.
- **Boilerplate tokens** — system prompts, tool schemas. FIXED COST.

## The Answer

| Token category     | Solution                                                 | Status                                     |
| ------------------ | -------------------------------------------------------- | ------------------------------------------ |
| Navigation tokens  | **fmm** — compress 500-line files into 10-line sidecars  | Proven (33% total savings in experiment 1) |
| Rediscovery tokens | **attention-matters** — geometric memory across sessions | Built, in production                       |
| Task tokens        | Maximize by reducing the above                           | Ongoing                                    |
| Boilerplate tokens | Prompt engineering, diminishing returns                  | Not prioritized                            |

## The Virtuous Cycle

```
Smaller files
  → cheaper sidecars
    → cheaper navigation
      → more free context for task work
        → better code output
          → smaller, better-structured files
```

fmm isn't just navigation — it's a forcing function for better code architecture, because the economics of the context window reward small, well-documented, single-purpose files.

## Experimental Evidence

See: [fmm-experiment-1-alp479-vs-480](/research/fmm-experiment-1-alp479-vs-480.md)

- Navigation is 41-52% of all tokens (the dominant cost center)
- fmm condition was 33% more token-efficient
- Agent ignored sidecars entirely (0/55 usage) — led to MCP server approach
- Instruction compliance is the key barrier to tool adoption

## What This Decided

1. **fmm as MCP server** — agent uses it because it's the most convenient path, not because instructions say to
2. **attention-matters** — geometric memory engine to eliminate rediscovery across sessions
3. **Independent repos** — each tool (fmm, am, mdcontext) is a standalone library, composed via plugin
4. **CLI wrapping as default** — adapter pattern keeps each tool's context cost minimal
