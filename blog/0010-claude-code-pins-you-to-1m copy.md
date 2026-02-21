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

The shape of the workload matters. Single-source, self-reinforcing context (one document, repeated themes, dense cross-references, a tight argumentative spine) is where the NIAH single-needle score stays at 89% across the full window. The model finds the one fact in the one document, even at 1M.

Multi-fact retrieval over heterogeneous context is the failure mode. Multiple files, multi-topic threads, scattered facts the model has to stitch into an answer. MRCR v2 8-needle drops 33 points at 256K between Opus 4.6 and 4.7, and 46 points at 1M. NIAH-2 at 1M sits at 56%.

Code generation is this shape by construction. The model is holding a function signature from one file, a type from a second, a convention from CLAUDE.md, the failing test output in the terminal scroll, and an import that resolves to a fourth file the last compaction may have summarised away. Every line of the diff has to stay consistent with every fact, and the facts live in different places. When the consistency breaks, you see it as a hallucinated method on an imported module, a type that no longer matches the schema, a CLAUDE.md constraint the model used to follow and now does not. Most readers will have blamed the model. The system card points elsewhere.

My empirical floor on Opus 4.7 sits below the system-card threshold. Past about 150K, response latency stretches and quality degrades noticeably on heterogeneous workloads. Anthropic publishes the multi-needle collapse at 256K and 1M. The lived experience drops earlier than that.

The tokenizer compounds the problem. A "200K" prompt that ran on Opus 4.6 prose lands closer to 240K to 270K on Opus 4.7 because the same text counts as more tokens. The pin pushes you into the multi-needle degradation band before the visible character count suggests you should be there.

The harness decided your window is 1M. The system card says the multi-fact retrieval ceiling is well below that. Three live issues on the public tracker compound the pin: compaction loop near 200K (`github.com/anthropics/claude-code/issues/50888`), CLAUDE.md instruction adherence drift across multi-turn sessions (`#53459`), and a `/context` denominator bug that under-reports the window on Max (`#49931`). No Anthropic-staff replies on any of them at time of writing.

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

The dial the picker hides has a single canonical name:

```bash
export CLAUDE_CODE_DISABLE_1M_CONTEXT=1
```

Set the variable. Restart Claude Code. The harness pins back to 200K, regardless of which Opus or Sonnet variant `/model` resolves to.

The variable does not appear in `claude --help`. The picker does not surface it. It is documented at `code.claude.com/docs/en/env-vars`, on a page the CLI does not link to from any of its surfaces. I went looking after `claude --help` came up dry, and found it on the env-vars page on the second pass.

A handful of companion knobs from the same page are worth knowing in the same beat:

| Knob | What it does |
|------|---------------|
| `/model opusplan` | Hybrid orchestration. Opus plans, Sonnet executes. Mixed window, mixed quota burn. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Pulls auto-compact earlier than the platform default. Override is clamped to a value computed against the effective window, so it only moves the trigger earlier. |
| `DISABLE_AUTO_COMPACT` | Set to `1` to disable automatic compaction. The manual `/compact` command remains available. Use when you want explicit control over when compaction occurs. |
| `DISABLE_COMPACT` | Set to `1` to disable all compaction, both automatic and the manual `/compact` command. |
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

## Where the dial went

The choice between 1M and 200K still exists. The picker stopped surfacing it, and the explicit headers that used to gate 1M have retired. The path through is one environment variable, on a docs page the CLI does not link to.

The defaults question pivots on workload shape. Single-source, self-reinforcing context holds up at 1M on Opus 4.7. Multi-fact retrieval over heterogeneous context drops 33 points at 256K and 46 points at 1M between Opus 4.6 and 4.7, per Anthropic's own system card. Most Claude Code sessions are the second shape. The harness pinned the window where the model regressed.

Context rot is real, and Anthropic says so themselves. The next teardown digs into how to tell which shape your session is in, and what to do when the harness pins you to the wrong one.

I publish the teardowns at knowmorecontext.substack.com. Token matters.
