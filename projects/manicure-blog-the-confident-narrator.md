---
title: The Confident Narrator
type: blog-draft
tags: [manicure, llm, hallucination, tools, reliability, context-engineering]
summary: When tool definitions are stripped from a request but the system prompt remains, an LLM fabricates execution with complete confidence. No uncertainty. No acknowledgment. A structural property of how these systems work.
status: draft
project: manicure
publication: https://knowmorecontext.substack.com/
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# The Confident Narrator

When you strip tool definitions from a request but leave the system prompt intact, something revealing happens. The model outputs tool_call blocks — as if executing tools. Then it narrates results. Confident, coherent, detailed results. From tools that were never called, returning data that was never retrieved.

**No uncertainty. No acknowledgment. No gap.**

### Why not just say "I don't have that tool"?

Five reasons, working together:

**Training coherence.** The model has never seen a conversation where the system prompt asserts tool availability and the tools array is empty. That's an adversarial input — a coherence violation the training distribution never prepared it for. It has no learned behavior for this edge case. It pattern-matches to the nearest familiar thing: system prompt says tool exists, so proceed as if it does.

**Instruction-following bias.** RLHF training rewards following instructions. "Use am_query to retrieve X" is an instruction. Responding "I can't — the tool isn't available" means refusing. The model resolves the conflict by complying with the instruction rather than reporting the structural reality.

**System prompt as ground truth.** When the system prompt's assertion ("you have these tools") conflicts with the structural evidence (empty tools array), the model weights the authoritative voice over the structural signal. The system prompt is the law. The tools array is circumstantial.

**Absence is invisible.** There is no signal in the input that distinguishes "tool defined but not yet called" from "tool stripped from the payload." The model cannot perceive absence. It has no mechanism to detect the contradiction.

**Narrative completion.** Autoregressive generation means: once the model outputs a tool_call block, a tool_result is the statistically expected next sequence. When no real result arrives, the model generates one — because that is what completion looks like. The narrative must close. It always closes.

### The implication

This is not a model-specific bug. It is a structural property. The model presents fabricated execution with identical confidence to real execution. No epistemic marker separates them.

The model does not panic. It does not notice. It simply generates what should come next — and what should come next, according to every training example it has seen, is a result.

**This makes the model's narration of its own tool use untrustworthy as a ground truth.** The only reliable record of what actually executed lives outside the model — at the transport layer, before the model ever sees the response.

That is what Manicure is for.
