---
title: "AM Conscious Recall Bug — Root Cause Analysis"
type: research
tags: [attention-matters, am-core, conscious-recall, scoring, bug-analysis]
summary: "Root cause analysis of why the same conscious memory surfaces on every query regardless of relevance"
status: active
project: am
confidence: high
related:
  [
    am-recall-layer-issues,
    am-rust-implementation-fidelity,
    dae-core-mathematical-foundations,
  ]
created: 2026-03-04
updated: 2026-03-04
---

# AM Conscious Recall Bug — Root Cause Analysis

## The Symptom

The same conscious memory (`[PREFERENCE] Stuart requires ALL conventions to be followed...`) surfaces on **every** `am_query` call regardless of query content. Queries about "casual greeting", "fmm motivation", "what have we been working on" — all return the identical conscious recall.

## The Pipeline Trace

### Step 1: Activation (system.rs:182)

`activate_word(word)` does exact case-insensitive string matching against `word_occurrence_index`. For EVERY matching occurrence (conscious or subconscious), `activation_count` is incremented. There is **no relevance gate** at this stage — any single word match activates.

### Step 2: Scoring (compose.rs:911-1048)

Score formula for each neighborhood:

```
base = sum(IDF_weight(w) * activation_count(w))  for each activated occurrence
density_bonus = activated_count / query_token_count
score = base * (1 + density_bonus)
```

Then type-specific multipliers:

```
if type == Decision || type == Preference:
    score = max(score * 3.0, 15.0)    // DECISION_MULTIPLIER = 3.0, DECISION_FLOOR = 15.0
```

### Step 3: The Bug

The `DECISION_FLOOR = 15.0` guarantees that ANY Decision or Preference with even a single word overlap scores at minimum 15.0.

The tokenizer (`tokenizer.rs:14`) has **no stop-word removal**. Words like "always", "use", "the", "tools", "files", "reading" are all indexed.

The Preference memory in question contains: "Stuart requires ALL conventions to be followed, not just the ones that feel convenient. Specifically: (1) Always invoke helioy-tools:fmm skill BEFORE reading source files — use fmm_read_symbol..."

This text contains high-frequency words that appear in virtually any technical query:

- "use" — appears in most queries
- "always" — common
- "files" — common in dev contexts
- "reading" — common
- "source" — common

Even though IDF weights for these words are low (they appear in many neighborhoods), the `DECISION_FLOOR = 15.0` overrides the IDF-based score. Result: this memory ALWAYS scores >= 15.0 on any technical query.

### Step 4: Selection (compose.rs:268-390)

Top-1 conscious selection. Since this Preference consistently scores >= 15.0 (often the highest-scoring conscious memory), it wins every time.

### Step 5: Diminishing Returns — Exempt

Decision and Preference types are **exempt from diminishing returns** (compose.rs:242-258):

```rust
if type != Decision && type != Preference:
    score *= 1.0 / (1.0 + recall_count)
```

So even after being recalled 50 times in a session, this memory's score is never reduced.

## Contributing Factors

### Factor 1: `_is_conscious` parameter is dead code

In `score_neighborhoods` (compose.rs:914), the `_is_conscious` parameter is prefixed with underscore and **never used**. Both conscious and subconscious go through identical scoring. The system has no way to apply conscious-specific relevance gating.

### Factor 2: Interference is computed but unused

The original DAE's phasor interference mechanism — the elegant gate between conscious and subconscious manifolds — is **fully implemented** in `query.rs` (lines 306-370) but the composition pipeline ignores it. Both `_surface` and `_interference` are prefixed with underscore and unused in `compose_context`. The geometric relevance gate exists in code but isn't wired into output selection.

### Factor 3: No minimum overlap threshold

There is no requirement for a minimum number of query tokens to match. A single common word like "use" is sufficient to activate and score a conscious memory.

### Factor 4: Pre-activation of conscious occurrences

Conscious memories are pre-activated at creation (system.rs:236-238): every occurrence starts with `activation_count = 1`. Combined with repeated query activation, these counts compound over time, making the base score (`IDF * activation_count`) higher with each session.

### Factor 5: Conscious recency boost compounds the problem

Conscious neighborhoods get a positional recency boost (compose.rs:975-989):

```
recency = 1.0 + (index / conscious_count)
```

But this doesn't help relevance — it just means recently-added conscious memories score even higher, which doesn't prevent old dominant memories from winning when they have the floor guarantee.

## The Root Cause (Summary)

**`DECISION_FLOOR = 15.0` + no stop-word filtering + no minimum overlap threshold + exemption from diminishing returns = any Preference/Decision containing common English words will dominate conscious recall on every query.**

## Candidate Fixes

### Fix 1: Remove or lower DECISION_FLOOR

The floor guarantees a minimum score regardless of actual relevance. Removing it lets IDF weighting do its job — memories matching only common words would score low naturally.

### Fix 2: Add minimum overlap threshold

Require that a minimum fraction of query tokens match before a conscious memory qualifies. e.g., `if activated_count / query_token_count < 0.15: skip`.

### Fix 3: Wire in interference gating

The phasor interference mechanism already exists. Use it: only include conscious memories where interference is constructive (positive). This is the original DAE's intended gate.

### Fix 4: Apply diminishing returns to ALL types

Remove the Decision/Preference exemption. If a memory has been recalled 10 times in a session, it should be penalized regardless of type.

### Fix 5: IDF floor for activation

Don't activate occurrences whose IDF weight is below a threshold (e.g., `weight < 0.05`). This prevents common words from triggering activation at all.

### Recommended approach

Fix 3 (wire in interference) is the most principled — it restores the original DAE's geometric philosophy. Fix 1 (remove DECISION_FLOOR) is the quickest win. Fix 2 (minimum overlap) is a reasonable pragmatic addition. These three are complementary.
