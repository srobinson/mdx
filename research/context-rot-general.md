---
title: "Context Rot in AI/LLM Systems: Definitions, Causes, Consequences, and Mitigation"
type: research
tags: [context-rot, llm, context-engineering, attention-degradation, rag, agents]
summary: "Context rot is the measurable degradation in LLM output quality as input context grows, coined June 2025 on HN, validated by Chroma across 18 frontier models, with 15-30% accuracy drops and 20%+ token cost increases documented."
status: active
source: deep-research
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

Context rot is the performance degradation LLMs exhibit as input context length increases, even when task complexity remains constant. The term was coined by HN user Workaccount2 on June 18, 2025, and popularized by Simon Willison the same day. Chroma's technical report (July 2025) validated the phenomenon across all 18 frontier models tested, including GPT-4.1, Claude Opus 4, and Gemini 2.5 Pro. The concept has rapidly expanded beyond in-session token degradation to encompass stale documentation fed to agents (AGENTS.md rot), conflicting context across sessions, and compounding errors in multi-step agentic workflows.

## 1. Definition and Scope

### 1.1 The Core Phenomenon

Context rot describes the measurable decline in LLM accuracy, coherence, and reasoning quality as the number of input tokens increases. The degradation is continuous, not cliff-edge. Models become unreliable well before hitting advertised context limits.

**Key insight from Chroma research**: "Models do not use their context uniformly; instead, their performance grows increasingly unreliable as input length grows." This holds across all 18 frontier models tested.

**Anthropic's framing** (September 2025 engineering blog): "As the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases." They describe an "attention budget" analogous to human working memory, depleted by every additional token.

### 1.2 Two Distinct But Related Meanings

The term has come to encompass two related failure modes:

1. **In-session context rot**: Performance degradation within a single LLM interaction as the context window fills with conversation history, tool outputs, and dead ends.

2. **Cross-session context rot**: Stale, outdated, or contradictory information persisted in system prompts, AGENTS.md files, RAG indexes, or memory stores that silently degrades agent performance over time.

Drew Breunig (dbreunig.com, June 2025) formalized four sub-patterns:
- **Context Poisoning**: Hallucinations or errors embed in context, get repeatedly referenced, compound over time
- **Context Distraction**: Accumulated context causes the model to over-rely on history rather than training knowledge
- **Context Confusion**: Superfluous content triggers irrelevant tool calls or document usage
- **Context Clash**: New information conflicts with existing context (Microsoft/Salesforce study: sharded prompts dropped o3 from 98.1% to 64.1% accuracy)

### 1.3 Origin of the Term

**Workaccount2** on Hacker News (June 18, 2025): "They poison their own context. Maybe you can call it context rot, where as context grows and especially if it grows with lots of distractions and dead ends, the output quality falls off rapidly."

**Simon Willison** amplified the term the same day on his blog (simonwillison.net/2025/Jun/18/context-rot/), crediting Workaccount2. The term achieved rapid adoption across the AI engineering community within weeks.

## 2. Causes

### 2.1 Architectural Causes (In-Session)

**Attention mechanism limitations**: LLMs create n-squared pairwise relationships for n tokens. At 10K tokens, 100 million relationships. At 100K tokens, 10 billion. At 1M tokens, 1 trillion. Each 10x context increase reduces per-token attention weight by approximately 10x. (Source: Morph, morphllm.com/context-rot)

**Lost-in-the-middle effect**: Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172, July 2023; published TACL 2024). Performance is highest when relevant information appears at the beginning or end of context. Accuracy drops 15-20 percentage points for information positioned in the middle. This is the foundational paper that first documented the U-shaped performance curve.

**Training data mismatch**: Models develop attention patterns from training distributions that favor shorter sequences. They have "less experience with, and fewer specialized parameters for, context-wide dependencies" at extended lengths. (Source: Anthropic engineering blog)

**Position encoding extrapolation**: Models encounter token positions they were never trained on. Adaptation techniques like RoPE interpolation enable longer contexts but introduce "degradation in token position understanding." (Source: Anthropic)

### 2.2 Behavioral Causes (Agent Workflows)

**Dead-end accumulation**: Every failed tool call, discarded approach, and debugging tangent stays in the context window. Josh Owens (joshowens.dev) documented a case where a 5-minute Tailwind tangent consumed 2,000 tokens and measurably degraded subsequent task performance.

**Automatic compaction artifacts**: When context hits ~95% capacity, the model summarizes to create space. This compression "flattens distinctions between abandoned and current approaches," potentially reintroducing superseded design patterns. (Source: Josh Owens)

**Context poisoning loops**: The Gemini 2.5 Pokemon agent case study showed the model becoming "fixated on achieving impossible or irrelevant goals" when false information about game state persisted in context. Beyond 100K tokens, the agent preferred "repeating actions from its vast history rather than synthesizing novel plans." (Source: Drew Breunig, citing Google DeepMind)

### 2.3 Cross-Session / Documentation Rot

**AGENTS.md staleness**: An ETH Zurich study (Gloaguen, Mundler, Muller, Raychev, Vechev; February 2026) tested four agents across SWE-bench and found:
- LLM-generated context files reduced task success by 2-3% while increasing token costs by over 20%
- Human-written files improved success by ~4% but increased costs by up to 19%
- Real-world AGENTS.md files that haven't been updated in months perform worse than no context file at all

**agents-lint** (github.com/devGiacomo, 2026) was built to detect this. Common findings during testing: "absolute home-directory paths that only work on the author's machine, monorepo commands copy-pasted into single-package projects, and framework references to APIs removed two major versions ago."

## 3. Real-World Consequences

### 3.1 Accuracy Degradation (Quantitative)

| Metric | Source | Finding |
|--------|--------|---------|
| Middle-position accuracy drop | Liu et al. 2023 (TACL 2024) | 15-20 percentage points vs. start/end positions |
| 20-document retrieval accuracy | Stanford study cited by Redis | Drops from 70-75% to 55-60% |
| Performance drop (middle vs. edges) | Liu et al. (cited by Morph) | >30% accuracy decrease |
| Sharded prompt accuracy drop | Microsoft/Salesforce study (cited by Breunig) | o3 dropped from 98.1% to 64.1% (39% average decline) |
| All 18 frontier models tested | Chroma 2025 | Every model exhibited degradation |
| Practical reliability threshold | Multiple practitioners | 130K tokens usable out of 200K advertised |
| Manus pre-rot threshold | Manus team | 128K-200K tokens, well below 1M advertised limits |

### 3.2 Token Waste and Cost

- A 20-turn conversation can consume 5,000-10,000 tokens when only 500-1,000 tokens of recent context would suffice (Source: Redis blog)
- LLM-generated AGENTS.md files increase inference costs by >20% while reducing accuracy (Source: ETH Zurich)
- Coding agents spend "over 60% of their first turn just retrieving context" (Source: Morph)
- Signal-to-noise ratio drops to 2.5% in typical multi-file agent searches (Source: Morph)
- 10x token variance observed on equivalent tasks depending on context management strategy (Source: Morph)

### 3.3 Agent Task Failure

- Doubling task duration quadruples failure rate (non-linear relationship) (Source: Morph)
- 35-minute threshold identified where all agents' success rates decrease (Source: Morph)
- Subagent architecture showed 90.2% improvement over single-agent Opus 4, using 15x more total tokens but distributed across isolated windows (Source: Morph, citing Anthropic)

### 3.4 Developer Experience

HN user **milchek**: In Cursor, longer conversations yield worse outputs. Best results come from "clear, explicit instructions and plan up front for a discrete change."

HN user **lifthrasiir**: Noticeable context rot in Gemini 2.5 Flash starting around 50K-100K tokens.

HN user **zwaps**: "Gemini loses coherence and reasoning ability well before the chat hits the context limitations."

Josh Owens documented Hour 3 of an RSS feed development session where Claude began "suggesting rebuilding systems already completed hours earlier" and compaction occasionally resurrected superseded architectural decisions.

### 3.5 Failure Mode Differences Across Models

Chroma's research revealed models fail differently:
- **Claude models** tend to abstain (refuse to answer) when uncertain under long contexts
- **GPT models** hallucinate confident incorrect answers based on distractors
- **All models** showed degradation; the mode of failure varies

## 4. Who Is Talking About This

### 4.1 Primary Research

- **Chroma** (Kelly Hong et al.): "Context Rot: How Increasing Input Tokens Impacts LLM Performance" (July 2025). Tested 18 frontier models. The foundational technical report. GitHub: chroma-core/context-rot. https://research.trychroma.com/context-rot
- **Liu et al.**: "Lost in the Middle: How Language Models Use Long Contexts" (arXiv:2307.03172, July 2023; TACL 2024). The precursor paper that identified the U-shaped performance curve.
- **ETH Zurich** (Gloaguen, Mundler, Muller, Raychev, Vechev): Study on AGENTS.md file impact (February 2026). Quantified cross-session context rot in agent configuration files.
- **Microsoft/Salesforce**: Sharded prompt study showing 39% average performance decline from context clash (cited by Breunig).

### 4.2 Engineering Blogs and Thought Leaders

- **Simon Willison** (simonwillison.net): Popularized the term on June 18, 2025. Tagged under context-engineering.
- **Drew Breunig** (dbreunig.com): Formalized the four failure patterns (Poisoning, Distraction, Confusion, Clash) in "How Long Contexts Fail" (June 22, 2025). Later published "How to Fix Your Context" (June 26, 2025). Also did an O'Reilly Radar podcast on context engineering.
- **Anthropic** engineering blog: "Effective Context Engineering for AI Agents" (September 2025). Describes context rot as a core challenge and introduces compaction, structured notes, and sub-agent architectures.
- **Hamel Husain** (hamel.dev): Summarized Chroma findings with practical recommendations.
- **Josh Owens** (joshowens.dev): Detailed practitioner account of context rot in Claude Code sessions.
- **Talon Miller** (Redis blog, December 2025): Comprehensive technical explainer with detection methods and solutions.
- **Morph** (morphllm.com): Quantitative analysis of agent token usage and WarpGrep system claiming 70% context rot reduction.

### 4.3 Industry Responses (Products/Tools)

- **Letta** (formerly MemGPT): Sleeptime agents that asynchronously rewrite context blocks. Sarah Wooders (Letta co-founder, X post June 2025): "context rot is a good term and something we've seen a lot with long-running agents. @Letta_AI solves it by using sleeptime agents to re-write context blocks asynchronously."
- **Morph WarpGrep**: RL-trained context retrieval subagent. Claims 70% context rot reduction, 28% faster than self-search, 0.73 F1 score in 3.8 steps.
- **CRoM** (Context Rot Mitigation): Open-source token-aware prompt packing system for RAG pipelines. GitHub Show HN, minimal traction.
- **agents-lint** (devGiacomo): CLI tool detecting stale paths and references in AGENTS.md files. Five checks: filesystem validation, npm scripts verification, dependency checking, framework pattern detection, structure analysis.
- **LangChain**: Published `how_to_fix_your_context` repository on GitHub based on Breunig's work.

### 4.4 Community Discussions

**Hacker News** (primary venue for context rot discussion):
- HN item 44310054: Origin thread where Workaccount2 coined the term (June 2025)
- HN item 44564248: Chroma report discussion, multiple practitioner reports
- HN item 45155543: CRoM Show HN
- HN item 45802808: "Fight context rot with context observability"
- HN item 46693985: "Ask HN: How do you keep system context from rotting over time?"
- HN item 47189911: agents-lint Show HN
- HN item 46849977: "Beating context rot in Claude Code with GSD"

**Reddit**: Essentially zero direct discussions using the term "context rot." The AI engineering community discussing this topic lives on HN and X, not Reddit.

**X/Twitter**:
- Sarah Wooders (@sarahwooders): Letta's sleeptime agent solution
- Chroma (@trychroma): Technical report announcement
- Matt Palmer (@mattppal): Video breakdown of Chroma paper
- Morph (@morphllm): WarpGrep announcement claiming 70% reduction
- Multiple practitioners amplifying the Anthropic context engineering blog

## 5. Quantitative Data Summary

### Accuracy Impact
- 15-20pp drop for middle-positioned information (Liu et al.)
- >30% accuracy drop middle vs. edges (Liu et al., broader dataset)
- 39% average performance decline from sharded/conflicting context (Microsoft/Salesforce)
- 2-3% task success reduction from LLM-generated AGENTS.md files (ETH Zurich)

### Cost Impact
- >20% token cost increase from LLM-generated AGENTS.md (ETH Zurich)
- Up to 19% cost increase from human-written AGENTS.md (ETH Zurich)
- 60% of first-turn tokens spent on context retrieval in coding agents (Morph)
- 10x token variance on equivalent tasks (Morph)
- 5,000-10,000 tokens consumed in 20-turn conversation where 500-1,000 would suffice (Redis)

### Agent Performance
- Doubling task duration quadruples failure rate (Morph)
- 90.2% improvement using subagent architecture vs. single agent (Morph/Anthropic)
- 35-minute threshold where agent success rates decline (Morph)
- Signal-to-noise ratio: 2.5% in multi-file searches (Morph)

### Practical Thresholds
- ~50K-100K tokens: noticeable degradation reported by practitioners
- ~130K tokens: practical reliability ceiling for 200K-token models
- 128K-200K tokens: Manus "pre-rot threshold" for frontier models
- 100K+ tokens: Gemini Pokemon agent began repeating actions over novel planning

## 6. Mitigation Strategies (Documented)

### Session-Level
- **Frequent context resets**: `/clear` in Claude Code, fresh sessions for each task
- **Manual compaction**: `/compact` before automatic triggering
- **Scope boundaries**: One objective per session
- **Context pruning**: Manually removing dead-end explorations (requested feature; not widely available)

### Architectural
- **Subagent architecture**: Spawn fresh-context specialized agents for discrete tasks (Anthropic's recommended approach; 90.2% improvement documented)
- **Sleeptime agents**: Asynchronous context rewriting between interactions (Letta/MemGPT)
- **JIT retrieval**: Pull only relevant context at the moment needed, not upfront
- **Semantic caching**: Reuse previous results for semantically similar queries (Redis LangCache)

### Documentation/Cross-Session
- **Durable external documentation**: CLAUDE.md, decision logs, markdown files that persist across sessions without consuming tokens
- **agents-lint**: Automated staleness detection for agent configuration files
- **Limit AGENTS.md to non-inferable details**: ETH Zurich recommendation

### Retrieval
- **RAG with tight retrieval windows**: Shrink the haystack before feeding to the model
- **WarpGrep**: RL-trained retrieval subagent (Morph)
- **Cross-encoder fallback**: Secondary verification for uncertain retrievals

## Sources Consulted

### Technical Reports
- [Chroma: Context Rot - How Increasing Input Tokens Impacts LLM Performance](https://research.trychroma.com/context-rot) (July 2025)
- [Liu et al.: Lost in the Middle - How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) (arXiv July 2023, TACL 2024)
- [ETH Zurich: AGENTS.md study](https://www.marktechpost.com/2026/02/25/new-eth-zurich-study-proves-your-ai-coding-agents-are-failing-because-your-agents-md-files-are-too-detailed/) (February 2026)

### Engineering Blogs
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (September 2025)
- [Drew Breunig: How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) (June 2025)
- [Redis: Context Rot Explained](https://redis.io/blog/context-rot/) (December 2025, Talon Miller)
- [Josh Owens: Context Rot - Why Your AI Gets Dumber the Longer You Use It](https://joshowens.dev/context-rot/)
- [Morph: What Is Context Rot?](https://www.morphllm.com/context-rot)
- [Hamel Husain: P6 Context Rot](https://hamel.dev/notes/llm/rag/p6-context_rot.html)
- [Adaline Labs: Context Rot - Why LLMs Are Getting Dumber?](https://labs.adaline.ai/p/context-rot-why-llms-are-getting)

### Blog Posts and Commentary
- [Simon Willison: Context Rot (quoting Workaccount2)](https://simonwillison.net/2025/Jun/18/context-rot/) (June 2025)
- [Simon Willison: How to Fix Your Context](https://simonwillison.net/2025/Jun/29/how-to-fix-your-context/) (June 2025)
- [Inkeep: Fighting Context Rot](https://inkeep.com/blog/fighting-context-rot)

### X/Twitter Posts
- [Sarah Wooders on sleeptime agents and context rot](https://x.com/sarahwooders/status/1935485477563548015) (June 2025)
- [Chroma technical report announcement](https://x.com/trychroma/status/1944835468551708905)
- [Morph WarpGrep announcement](https://x.com/morphllm/status/1994484969050444103)

### Hacker News Threads
- [HN 44310054: Origin of "context rot" term](https://news.ycombinator.com/item?id=44310054)
- [HN 44564248: Chroma report discussion](https://news.ycombinator.com/item?id=44564248)
- [HN 46693985: Ask HN - keeping system context from rotting](https://news.ycombinator.com/item?id=46693985)
- [HN 47189911: agents-lint Show HN](https://news.ycombinator.com/item?id=47189911)
- [HN 45155543: CRoM Show HN](https://news.ycombinator.com/item?id=45155543)

### Tools and Repositories
- [GitHub: chroma-core/context-rot](https://github.com/chroma-core/context-rot)
- [GitHub: langchain-ai/how_to_fix_your_context](https://github.com/langchain-ai/how_to_fix_your_context)
- [agents-lint](https://giacomo.github.io/agents-lint/)
- [Letta sleeptime agents docs](https://docs.letta.com/guides/agents/architectures/sleeptime)

## Source Quality Assessment

**High confidence**: Chroma's technical report (18 models, reproducible methodology, open-source toolkit), Liu et al. (peer-reviewed TACL publication), Anthropic's engineering blog (first-party), ETH Zurich study (academic rigor).

**Medium confidence**: Practitioner reports on HN (consistent across multiple independent users but anecdotal), Morph's quantitative claims (product marketing context, numbers not independently verified), Drew Breunig's taxonomy (well-reasoned but based on case studies not controlled experiments).

**Low confidence**: Reddit (zero relevant results; the community does not discuss this topic there), product blog posts from Redis/Box/Milvus (marketing-adjacent, derivative of primary sources).

**Gap**: No peer-reviewed study specifically measures the dollar cost of context rot in production systems. The ETH Zurich study comes closest with its 20%+ token cost increase finding. Most cost figures are extrapolations.

## Open Questions

1. **Quantified dollar cost**: No study measures the total cost of context rot in production agent deployments (wasted tokens + developer time debugging regressions + failed task retries).
2. **Model-specific degradation curves**: Chroma tested 18 models but detailed per-model degradation curves at specific token counts are not publicly available in granular form.
3. **Compaction quality**: How much information loss occurs during automatic compaction, and does the loss pattern differ across models?
4. **Cross-session rot prevalence**: How many production AGENTS.md / CLAUDE.md files are stale? The agents-lint tool exists but no large-scale survey has been published.
5. **Sleeptime agent effectiveness**: Letta claims asynchronous context rewriting solves the problem, but no independent benchmark validates this against alternatives.
6. **Recursive Language Models**: A Medium post proposes RLMs as a solution, but this appears speculative with no implementation evidence.

## Actionable Takeaways

1. **Context rot is empirically validated**. Every frontier model exhibits it. Treat it as a design constraint, not a theoretical risk.
2. **The practical context limit is 60-70% of advertised capacity**. Design systems assuming 130K usable tokens for a 200K-token model.
3. **Subagent architecture is the highest-impact mitigation**. Anthropic's own data shows 90.2% improvement. Isolate context windows per task.
4. **AGENTS.md files can hurt more than help**. ETH Zurich data shows LLM-generated context files reduce performance. Keep them minimal and run automated freshness checks.
5. **The term has strong community adoption**. Safe to use in technical writing without extensive definition. HN, X, and engineering blogs all recognize it.
6. **Reddit is not a source for this topic**. The discussion lives on HN, X, and engineering blogs.
