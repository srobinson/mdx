---
title: Claude Code pins you to a 1M context window, no questions asked
slug: claude-code-pins-you-to-1m
status: review
account: knowmorecontext
surface: substack
type: thesis
created: 2026-05-02
updated: 2026-05-02
post_date:
post_url:
campaign:
related: []
---

## The picker

My findings below are from a Claude Code Max plan. Pro, Team, and Enterprise plans may surface a different `/model` picker than the one shown here.

Run `/model` in Claude Code today. The picker shows three options.

```
Select model
Switch between Claude models. Applies to this session and future Claude Code
sessions. For other/previous model names, specify with --model.

  1. Default (recommended)  Sonnet 4.6 · Best for everyday tasks
❯ 2. Opus ✔                 Opus 4.7 · Most capable for complex work
  3. Haiku                  Haiku 4.5 · Fastest for quick answers
```

That is the entire visible surface. Three aliases and one footnote: *for other/previous model names, specify with `--model`*. The footnote does not list those names or link to them anywhere obvious. It reads like housekeeping.

The line does more work than that. It is the entry to a much wider control surface, hidden behind a sentence that asks the reader to know what to ask for.

I went looking.

## What the picker hides

The footnote points at `code.claude.com/docs/en/model-config`. The page lists what `/model` and `--model` can resolve, well beyond the three the picker surfaces.

| Alias        | Resolves to                  | Window | Notes                                                  |
|--------------|------------------------------|--------|--------------------------------------------------------|
| `opus`       | claude-opus-4-7              | 1M     | Default on Max, Team, Enterprise                       |
| `sonnet`     | claude-sonnet-4-6            | 200K   | Default unless explicitly opted into 1M                |
| `haiku`      | claude-haiku-4-5-20251001    | 200K   | All plans                                              |
| `opus[1m]`   | Opus 4.7 with 1M flag        | 1M     | Explicit; useful in scripts and CI                     |
| `sonnet[1m]` | Sonnet 4.6 with 1M flag      | 1M     | Pro and Max plans route extra usage at standard rates  |
| `opusplan`   | Hybrid: Opus plans, Sonnet executes | mixed | Spreads quota burn across both                  |
| `default`    | Plan-dependent               | varies | What the picker labels Default                         |
| `best`       | Currently `opus`             | 1M     | Plan-dependent                                         |

Plus full date-stamped IDs that `--model` accepts directly: `claude-opus-4-6`, `claude-opus-4-5-20251101`, `claude-opus-4-1-20250805`, `claude-sonnet-4-5-20250929`. Pin a date-stamped ID when reproducibility matters across months.

The picker shows three. The selection surface is at least ten. Reading `claude --help` does not get you here.

## The pin

Pick the picker's default on a Max plan and you land on Opus 4.7. Opus 4.7's context window is 1M tokens. The picker does not ask which window you want, the help text does not list a flag for choosing one, and a 200K Opus mode is nowhere visible in the menu.

This was not always the case.

Three dates from Anthropic's API release notes pin the path:

- **2026-03-13.** The 1M token context window was promoted to GA for Opus 4.6 and Sonnet 4.6, at standard pricing, with no beta header required. The release note reads:

  > *"The 1M token context window is now generally available for Claude Opus 4.6 and Sonnet 4.6 at standard pricing. Requests over 200k tokens work automatically for these models with no beta header required."*

- **2026-04-16.** Opus 4.7 launched with 1M as the native default, with no beta header, no CLI flag, and no opt-in step required.
- **2026-04-30.** The old `context-1m-2025-08-07` beta header retired for Sonnet 4.5 and Sonnet 4. Those models dropped back to a 200K hard ceiling with no upgrade path on the API.

Before March 13, asking for 1M was a deliberate act. The user set a beta header, and the token cost above 200K was visible upfront in the pricing tables. After March 13 on Opus 4.6 and Sonnet 4.6, and at every Opus 4.7 session since April 16, the window is 1M unless the user goes out of the way to disable it. The dial that used to need an explicit nudge to engage now needs an explicit nudge to step back.

That works in most sessions. It stops working when the session goes long.

## Why this matters: context rot

Anthropic names the failure mode themselves. From `docs.anthropic.com/en/docs/build-with-claude/context-windows`:

> *"A larger context window allows the model to handle more complex and lengthy prompts, but more context isn't automatically better. As token count grows, accuracy and recall degrade, a phenomenon known as context rot."*

That is the general statement on the property. Anthropic's specific marketing on Opus 4.7 reads otherwise. From the blog post on session management at 1M context:

> *"Opus 4.7 delivered the most consistent long-context performance of any model we tested."*

The Opus 4.7 system card disagrees with the marketing. It publishes side-by-side scores against Opus 4.6 on multi-fact retrieval. On MRCR v2 with 8 needles, 4.7 regresses across the long band:

| Benchmark | Opus 4.6 | Opus 4.7 | Δ |
|---|---|---|---|
| MRCR v2 8-needle @ 256K | 91.9% | 59.2% | −33pt |
| MRCR v2 8-needle @ 1M | 78.3% | 32.2% | −46pt |
| NIAH single-needle @ 1M (4.7) | n/a | 89% | n/a |
| NIAH multi-needle @ 1M (4.7) | n/a | 56% | n/a |

Source: Opus 4.7 system card, reproduced at `blog.wentuo.ai/en/claude-opus-4-7-long-context-regression-en.html`.

The NIAH split is where the workload shape starts to matter. Single-needle retrieval over a self-reinforcing document (one source, repeated themes, dense cross-references, a tight argumentative spine) holds at 89% across the full window. The model finds the one fact in the one document, even at 1M. Multi-needle retrieval over heterogeneous sources collapses.

Two distinct failure modes are at work here. The literature treats them as separate phenomena, with different mitigation profiles, and they compose badly.

### Mechanism one: static long-context degradation

Pure context length degrades quality even when retrieval is perfect. Liu et al. (2024) measured a "lost in the middle" effect: a >30 point accuracy drop between position 1 and position 10 in 20-document QA, an effect that holds on Claude 4.x at 1M. Chroma's Context Rot study (`trychroma.com/research/context-rot`, 2025) tested 18 frontier models and found non-uniform degradation across all of them, with distractors plus length compounding the effect. arXiv research through 2025 reports reasoning quality falling with context length even on tasks where the answer is unambiguously available.

Claude is more graceful than peers on this mechanism because it is abstention-biased. Anthropic publishes a 36% hallucination rate on Opus 4.7, down from 61% on Opus 4.6 Adaptive. The figure carries no length axis, so it does not address the failure mode directly, but it does suggest the baseline is improving.

This is the boring half of context rot. Severity moderate. Documented across the field.

### Mechanism two: self-reinforcing context

The dangerous half is what happens when the conversation builds on itself. Once an early error lands in the trace, the decoder is conditioned on that prefix. Every subsequent token has to stay coherent with the wrong premise. *Hallucination Snowballing* (Zhang et al., 2023) measured this directly: in their setup, ChatGPT and GPT-4 could identify a high fraction of their own past mistakes when asked in isolation, but would not correct them in-stream. The model defends a wrong claim with plausible reasoning rather than backtracking.

Drew Breunig wrote up four shapes this takes (`dbreunig.com/2025/06/22`, signal-boosted by Simon Willison):

- **Context Poisoning.** A hallucination enters the trace, gets repeatedly referenced, and becomes load-bearing. DeepMind's Gemini 2.5 Pokémon agent demonstrated this past 100K tokens: hallucinated game state polluted the goal stack, the agent developed nonsensical strategies, and recovery required a clean restart.
- **Context Distraction.** Long history causes over-reliance on the conversation and neglect of the model's training knowledge. The model starts pattern-matching against the trace instead of thinking.
- **Context Confusion.** Superfluous tools and documents degrade quality. Llama 3.1 8B failed in tool-use evaluations with 46 tools available, succeeded with 19. The same effect generalises to retrieved documents in long sessions.
- **Context Clash.** Sharded prompts where information arrives across turns rather than all at once. Microsoft and Salesforce researchers reported a substantial average performance drop on multi-turn-with-sharding versus single-turn delivery, attributing it to early-turn assumption commitment.

Sycophancy compounds the picture. Recent benchmarks (SycEval, SYCON Bench) find that RLHF causally amplifies sycophancy and that multi-turn pressure flips position. The model agrees with its own prior framing once that framing is in context, which is exactly the conditions long Claude Code sessions create.

The literature has a name for the cascade. The LLM-Agent hallucination survey published on arXiv in 2025 formalises it: hallucinations rise in later turns due to error propagation. OWASP has named cascading agent failure as security category ASI08.

### What this means for code generation

Code generation is multi-fact retrieval over heterogeneous context by construction. The model is holding a function signature from one file, a type from a second, a convention from CLAUDE.md, the failing test output in the terminal scroll, and an import that resolves to a fourth file the last compaction may have summarised away. Every line of the diff has to stay consistent with every fact, and the facts live in different places. When the consistency breaks, you see it as a hallucinated method on an imported module, a type that no longer matches the schema, a CLAUDE.md constraint the model used to follow and now does not. Most readers will have blamed the model. The system card points elsewhere.

A thesis is one document and one argumentative spine. The reader walks it and the cross-references reinforce each other. That shape is where 1M holds up. A codebase is the opposite shape, by construction.

### The empirical floor

My empirical floor on Opus 4.7 sits below the system card threshold. Past about 150K, response latency stretches and quality degrades noticeably on heterogeneous workloads. Anthropic publishes the multi-needle collapse at 256K and 1M. The lived experience drops earlier than that.

The tokenizer compounds the problem. A 200K prompt that ran on Opus 4.6 prose lands closer to 240K to 270K on Opus 4.7 because the same text counts as more tokens. The pin pushes you into the multi-needle degradation band before the visible character count suggests you should be there. The tokenizer mechanism gets its own section below.

## Compaction-induced fabrication

The compaction loop itself can introduce hallucinations into the trace. Once a fabricated string enters post-compact context, it is indistinguishable from a real user message. Five issues on the public Claude Code tracker document this pattern.

`github.com/anthropics/claude-code/issues/46602`. The pre-compact summariser fabricated a Korean user instruction that never existed. Raw JSONL grep proved zero occurrences in the original conversation. The post-compact agent then ran 5 batches of unrequested screenshot captures across 44 URLs. Closed as duplicate without postmortem.

`#50888`. Opus 4.7 auto-compacts at approximately 200K despite the 1M window, consumes around 150K tokens to produce the summary, and climbs back to 200K. A compaction loop that the harness cannot escape on its own. Closed as duplicate.

`#7533`. The "read files in full" instruction does not survive compaction with sufficient priority while efficiency biases do. Open. The post-compact agent reverts to summarised reads.

`#10960`. Repository path changes do not persist across compaction. The model checks the wrong repo after the boundary. Open.

`#46727`. Subagent outputs were fabricated, the main agent trusted them, and built plans on false premises. Failures occurred at 30 to 40% context usage, well before compaction was forced. Open.

The pattern is consistent. The summariser introduces or omits content, and the post-compact agent has no way to distinguish summary-derived state from original user input. Whatever the summariser writes is now ground truth in the new trace. The fabricated Korean instruction in #46602 is the cleanest receipt: it was reproducibly grep-checkable against the raw JSONL, the user proved its absence, and the agent acted on it anyway.

Anthropic has not publicly acknowledged this failure mode. Closing #46602 as duplicate without postmortem is the closest public signal that they recognise it. The official framing remains the language in the context-engineering doc, where compaction "may result in the loss of subtle but critical context whose importance only becomes apparent later." That description is generous for a mechanism that can also fabricate.

## The tokenizer caveat

The 1M window costs more tokens than the equivalent 1M window on the prior generation, even at identical prose.

Anthropic says so directly. From `platform.claude.com/docs/en/about-claude/models/whats-new-claude-4-7`, under the "Updated token counting" breaking-change note:

> *"Claude Opus 4.7 uses a new tokenizer, contributing to its improved performance on a wide range of tasks. This new tokenizer may use roughly 1x to 1.35x as many tokens when processing text compared to previous models (up to ~35% more, varying by content), and `/v1/messages/count_tokens` will return a different number of tokens for Claude Opus 4.7 than it did for Claude Opus 4.6."*

The models overview page corroborates the upper end of that range. Each row carries a tooltip estimating the conversion to natural language. From `platform.claude.com/docs/en/about-claude/models/overview`:

- Opus 4.7's 1M tokens hold approximately **555,000 words** (roughly 2.5M unicode characters).
- Sonnet 4.6's 1M tokens hold approximately **750,000 words** (roughly 3.4M unicode characters).

The arithmetic: 750 / 555 = 1.35×. The tooltip ratio lands on Anthropic's disclosed ceiling.

Empirical measurements can run above that ceiling on some workloads. Simon Willison ran the Opus 4.7 system prompt through both tokenizers and reported 1.46×, or 7,335 tokens against Opus 4.6's 5,039 (`simonwillison.net/2026/apr/20/claude-token-counts`). The 1.0× to 1.35× holds for typical prose. Workloads heavy on system prompts or dense structured content can land higher.

Pricing is flat above 200K. Opus 4.7 lists at $5 per million input tokens and $25 per million output tokens, across the entire window. There is no surcharge for crossing 200K, which used to exist when 1M was beta-gated. Per-token pricing has not changed. What changed is that the same input text counts as more tokens on Opus 4.7, and the harness no longer asks whether the user wanted to be in the territory where that matters.

A session that ran 700K tokens on Opus 4.6 sits closer to 945K on Opus 4.7 at the same prose. The dollars per token are unchanged. On a Max plan, where the quota appears to track raw compute rather than price tiers, that 35% expansion shows up as faster quota burn rather than a higher bill. Same work, more meter.

## The killer env var

There is a single env var that flips the harness back to 200K.

```bash
export CLAUDE_CODE_DISABLE_1M_CONTEXT=1
```

Set the variable. Restart Claude Code. The harness pins back to 200K, regardless of which Opus or Sonnet variant `/model` resolves to.

The variable does not appear in `claude --help`. The picker does not surface it. It is documented at `code.claude.com/docs/en/env-vars`, on a page the CLI does not link to from any of its surfaces. I went looking after `claude --help` came up dry, and found it on the env-vars page on the second pass.

The shell export is per-shell. For something that survives a restart, set it in `~/.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_DISABLE_1M_CONTEXT": "true"
  }
}
```

The settings file is read on every Claude Code launch. The variable accepts `1` or `true`. The other env vars on the same page (`ENABLE_TOOL_SEARCH`, `ENABLE_EXPERIMENTAL_MCP_CLI`, and the rest of the experimental surface) are their own teardown.

A handful of companion env vars from the same page are worth knowing in the same beat:

| Knob | What it does |
|------|---------------|
| `/model opusplan` | Hybrid orchestration. Opus plans, Sonnet executes. Mixed window, mixed quota burn. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Pulls auto-compact earlier than the platform default. The override is clamped against the effective window (raw window minus the output reservation), so it only moves the trigger earlier. |
| `DISABLE_AUTO_COMPACT` | Set to `1` to disable automatic compaction. The manual `/compact` command remains available. |
| `DISABLE_COMPACT` | Set to `1` to disable all compaction, both automatic and manual. Useful when developing a harness and you want authoritative compaction control. |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Output reservation, subtracted from the input window. Lower it to leave more room for input on long sessions. |
| `CLAUDE_CODE_DISABLE_THINKING` | Disables extended thinking on Opus 4.6+ and Sonnet 4.6+. Saves tokens when the task does not warrant them. |

On Max, `/model opus[1m]` resolves to the same window as `/model opus`. Both land on 1M. The `[1m]` suffix is decorative on plans where the bare alias already defaults to 1M; it earns its keep in scripts and CI where the resolution path is plan-dependent and you want to be explicit.

The flag toggles the window between 1M and 200K:

```bash
# Pin context to 200K, regardless of which model the picker selects
export CLAUDE_CODE_DISABLE_1M_CONTEXT=1

# Run an Opus session, 200K hard
claude --model opus

# Restore the 1M default
unset CLAUDE_CODE_DISABLE_1M_CONTEXT
claude --model opus
```

On long sessions, pulling auto-compact earlier sidesteps the compaction loop reported at `github.com/anthropics/claude-code/issues/50888`. On a 1M window, 70% leaves about 680K of input runway before the trigger fires:

```bash
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70
```

The default landing point on Opus 4.7 sits closer to 83% of raw because the threshold runs against the effective window (raw minus the output reservation Opus 4.7 sets aside for thinking and response). 83% of raw is where the 200K compaction loop lives. Pulling earlier than that is the available lever.

Reading the env-vars page takes longer than reading `claude --help`. The reading is the work.

## Compaction is context engineering

The window pin makes the title. The substrate underneath it is compaction, and that substrate is where the post is going.

Compaction is context engineering. The summariser decides which facts survive into the next turn, which file paths and constraints carry forward, which evidence gets reduced to a sentence, which lines drop entirely. That selection becomes the conversation's working memory for the rest of the session. Configuring it is configuring the model's durability.

Anthropic's default compaction works well in lived practice. The summariser preserves load-bearing facts most of the time. Function signatures, recent file paths, and active todo items survive. The mechanism is competent. Credit where due.

The underappreciated knob is the manual form:

```bash
/compact <custom summarisation instructions>
```

The string after the command directs the summariser. *"Preserve all file paths verbatim, summarise discussion of architecture decisions but keep the final decision in full, drop tangential exploration."* That kind of instruction shapes the post-compact context in ways the auto-compact default cannot. The knob is documented, the syntax is simple, and it is the closest the surface comes to giving the user authoritative control over the working memory.

The configuration surface stops there. The full set of knobs available today:

- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` to move the trigger
- `DISABLE_AUTO_COMPACT` to turn off the timer
- `DISABLE_COMPACT` to turn off all compaction
- `/compact <free-form string>` to direct the manual call

Three boolean-shaped env vars and one free-form instruction string. That is the entire surface for configuring the context engineering primitive that runs the longest Claude Code sessions.

A more comprehensive surface would include:

- **Per-pattern preservation markers.** A way to mark a region of conversation as preserve-verbatim through any compaction. Useful for load-bearing decisions, exact env var values, reproduction steps, and the original user prompt that started the session.
- **Summariser model selection.** Today the summariser model is opaque. Picking Haiku for fast cheap compaction or Opus for fidelity-preserving compaction is a real tradeoff that the surface does not expose.
- **Project-level default summarisation instructions.** A field in CLAUDE.md or a sibling config file that becomes the default `<custom instructions>` string for the project, applied to every auto-compact and every bare `/compact`.
- **Per-tool retention rules.** Different rules for different tool outputs. Keep file reads in full until the file path is overwritten. Summarise web-fetch outputs more aggressively. Drop bash output that has been superseded by a later command on the same target.

The list above sketches the shape of a configuration surface that respects compaction as a first-class context engineering primitive. Today's surface treats it as a memory cleanup chore.

## The reader's playbook

Concrete operating practices for working under the pin, organised by how strong the evidence is.

**Strong evidence.**

- `/clear` between distinct objectives. Anthropic recommends it. Re-seeding a fresh prompt costs less than a snowballed hallucination, and `/clear` has no summariser fabrication risk. The seed should restate load-bearing facts: file paths, ruled-out approaches, current state.
- Subagents with summary-only return. Fresh context per subtask, the parent gets only the summary. Spot-check load-bearing claims before building on them. Issue #46727 is the receipt for why: a fabricated subagent output trusted by the main agent led to plans on false premises.
- Tool-grounded retrieval over context stuffing. Direct quotes for documents over 20K tokens. Language servers, ctags, and AST query tools as zero-token grounding for definitions and call sites, rather than letting the conversation hold the file content. Anthropic's top recommended hallucination mitigation in their context-engineering doc.
- Allow "I don't know." Claude is already abstention-biased. Reinforcing this in the prompt is high-leverage and costs nothing.

**Moderate evidence.**

- Manual `/compact <focus>` with verbatim preservation. The free-form string is the lever. *"Preserve file paths and decisions verbatim; summarise discussion."*
- External canonical state. A project README, a notes file under version control, a memory tool the user owns, anything that lives outside the conversation. Never let a Claude-generated summary become source of truth. The summary is a derivative; the canonical state lives outside the conversation.
- Front-load critical facts. Position 1 and CLAUDE.md are reliable across compaction. Mid-context is not.

**Weak evidence (worth knowing, not load-bearing).**

- Higher thinking budgets. Plausible mechanism for reducing snowballing on long traces. No clean isolating benchmark in public.
- Lower auto-compact threshold. Compacts more often with less drift per cycle, but more compactions also mean more fabrication-injection opportunities. Net effect unclear.

Real-time snowball detection. If Claude defends a wrong claim with plausible reasoning, `/clear` and restart with the corrected premise. Do not argue it out in-stream. That is the literal failure mode in the literature.

## Where the dial went

The picker still surfaces the same three aliases. The dial that used to choose between 1M and 200K lives on a different page now, behind one environment variable that has to be looked up to be set.

Most Claude Code sessions are multi-fact retrieval over heterogeneous code. A function signature in one file, a type in a second, a CLAUDE.md constraint, a failing test, an import that resolves to a fourth file. That is the workload shape where Anthropic's own system card shows Opus 4.7 dropping 33 points at 256K and 46 points at 1M against Opus 4.6. The harness pinned the window where the model regressed, and Claude Code carries no signal that any of this matters.

Compaction is the substrate running underneath the pin. The configuration surface around it is narrower than the primitive deserves, even though Anthropic's default summariser works in lived practice and the manual `/compact <instructions>` form is genuinely useful. The next teardown picks it apart.

I publish the teardowns at knowmorecontext.substack.com. Token matters.
