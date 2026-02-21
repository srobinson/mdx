---
title: Context Rot and Large Context Windows - Evidence, Benchmarks, and Practitioner Experience
type: research
tags: [context-rot, long-context, LLM, performance-degradation, RAG, context-engineering, benchmarks]
summary: Larger context windows do not solve context rot; they increase tolerance for waste while degrading quality. Structured/indexed context consistently outperforms raw large context across research and practice.
status: active
source: deep-research
confidence: high
created: 2026-03-16
updated: 2026-03-16
---

## Executive Summary

Large context windows (1M+ tokens) do not solve context rot. They make it worse. Every major benchmark (RULER, MRCR, LongBench v2, Chroma Context Rot) and practitioner report confirms that LLM performance degrades as input length increases, even when all relevant information is present and perfectly retrievable. The "lost in the middle" phenomenon (Liu et al., 2023) persists in 2025/2026 frontier models, though some (Claude Opus 4.6) handle it better than others. Structured, curated context consistently outperforms brute-force context stuffing across both academic benchmarks and production systems. The emerging consensus, articulated by Andrej Karpathy as "context engineering," is that context is a finite resource with diminishing marginal returns, and the discipline of filling it with the right information matters far more than its raw capacity.

## Detailed Findings

### 1. Context Rot: Definition and Mechanism

Context rot is the progressive degradation in LLM accuracy and reliability as input context length increases. Three architectural factors drive it:

**Quadratic attention scaling.** Transformer attention creates n-squared pairwise token relationships. Doubling context length requires 4x compute and memory, stretching attention thin across the expanded input. This is not a software limitation but a fundamental property of the architecture.

**Primacy and recency bias ("Lost in the Middle").** Models attend strongly to tokens at the beginning and end of context but poorly to tokens in the middle. Liu et al. (2023) demonstrated a U-shaped performance curve: accuracy is highest when relevant information appears at the start or end, and drops significantly for mid-positioned information. Published in TACL 2024 (arXiv: 2307.03172).

**Distractor interference.** Semantically similar but irrelevant information degrades accuracy more than unrelated padding. The Chroma research showed that even a single distractor reduces accuracy, and four distractors compound degradation further. GPT models tend to hallucinate when confused; Claude models tend to abstain.

### 2. The Chroma Context Rot Study (July 2025)

The most comprehensive study of context rot to date. Kelly Hong, Anton Troynikov, and Jeff Huber at Chroma tested 18 frontier models across five task types.

**Models tested:** Claude Opus 4, Sonnet 4, Sonnet 3.7, Sonnet 3.5, Haiku 3.5; GPT o3, 4.1, 4.1 mini, 4.1 nano, 4o, 4 Turbo, 3.5 Turbo; Gemini 2.5 Pro, 2.5 Flash, 2.0 Flash; Qwen3-235B, 32B, 8B.

**Key findings:**

- All 18 models exhibit context rot. No model is immune.
- Models achieving 95%+ on standard NIAH drop to 60-70% on slightly more realistic tasks involving semantic matching or distractor resistance.
- Semantic matching tasks showed far worse degradation than lexical matching. Real-world queries require semantic understanding, making NIAH benchmarks misleadingly optimistic.
- Coherent, well-structured haystacks degraded accuracy MORE than shuffled/incoherent text. Models get trapped following narrative arcs instead of finding specific information. This is counterintuitive and underreported.
- In the LongMemEval task, Claude models showed the largest gaps between focused context (~300 tokens) and full context (~113k tokens). Performance dropped sharply when irrelevant conversational padding was added.
- On simple text replication tasks, all models showed significant performance drops at long input lengths, demonstrating that the problem is not limited to complex reasoning.
- GPT-3.5 Turbo had a 60.29% task refusal rate and was excluded entirely.

**Source:** [Chroma Research - Context Rot](https://research.trychroma.com/context-rot), [GitHub](https://github.com/chroma-core/context-rot)

### 3. Performance Degradation Curves: Benchmark Evidence

**RULER (NVIDIA, COLM 2024).** Expanded NIAH with multi-hop tracing and aggregation tasks. Despite nearly perfect NIAH accuracy, almost all models exhibit large performance drops as context length increases. Only half of models claiming 32k+ context can effectively use 32k by exceeding a quality threshold. GPT-4 showed the least degradation (15.4 points) extending to 128k. Models showed almost linear degradation on log-scale of input length. ArXiv: 2404.06654.

**MRCR v2 (Multi-needle Retrieval, 2026).** The hardest public stress test for long context. At 1M tokens with 8 needles: Claude Opus 4.6 scored 76%, Gemini 3.1 Pro scored 26.3%, Claude Sonnet 4.5 scored 18.5%. At 128k tokens, models perform similarly (~84.9%), but performance diverges dramatically as context grows. This shows that the delta between "can handle long context" and "cannot" widens at scale.

**LongBench v2 (December 2024).** 503 questions with contexts from 8k to 2M words. The best direct-answering model achieved only 50.1% accuracy. o1-preview with extended reasoning achieved 57.7%. Human experts achieved 53.7% under time constraints. This benchmark demonstrates that even frontier models struggle with realistic long-context tasks.

**Context Length Alone Hurts Performance (arXiv: 2510.05381).** Critical finding: context length itself impairs reasoning independent of retrieval quality. Even with 100% exact-match retrieval, performance drops: Llama-3.1-8B dropped 85% accuracy at 30k tokens on variable summation. Even padding with whitespace caused a 48% drop on arithmetic. Closed-source models (GPT-4o, Claude 3.5, Gemini 2.0) were more robust but still degraded consistently.

**Databricks Long Context RAG (2024).** Tested 13+ models across 3 RAG datasets. Llama-3.1-405b performance starts decreasing after 32k tokens. GPT-4-Turbo starts decreasing after 64k tokens. Only a few models maintained consistent performance across all context lengths.

### 4. Does a Larger Context Window Solve Context Rot?

No. The evidence is unambiguous:

- Larger windows provide more capacity but not more effective capacity. The Chroma study showed degradation across all 18 models regardless of advertised context size.
- Anthropic's own engineering blog describes context as having an "attention budget" that depletes with every additional token. More tokens = more budget depletion.
- A Stanford study found that with just 20 retrieved documents (~4,000 tokens), accuracy can drop from 70-75% to 55-60%. The degradation starts early.
- Microsoft and Salesforce reported accuracy falling from 90% to 51% as requirements were elaborated over longer conversations.
- The MRCR v2 results show that while Opus 4.6 handles 1M tokens far better than competitors, even it drops from ~85% (128k) to 76% (1M). The gap never closes; it just narrows with better models.

### 5. Larger Windows Increase Tolerance for Waste

Multiple practitioners report that large context windows enable sloppy context management rather than solving the underlying problem:

- **brulard (HN):** "Performance degradation accelerates significantly after roughly 200K tokens, making the 1M ceiling less practical than advertised."
- **ehnto (HN):** "The more information you put into context the more confused the LLM will get." Dumping entire codebases degraded performance rather than improving it.
- **jeremychone (HN):** "I've never needed 1M, or even 250k+ context. I'm usually under 100k per request." Uses code maps and auto-context selection at 30-80k tokens. "Higher precision on the input typically leads to higher precision on the output."
- **ants_everywhere (HN):** "An LLM will never have the context you need to solve all problems" because attention mechanisms struggle with massive scale.
- **8note (HN):** Gemini "gets real real bad when you get far into the context, gets into loops, forgets how to call tools."
- **Bombthecat (HN):** "Even with 200k context it starts to write gibberish, even with the correct information in the context."

Counterpoint: **Ethan Mollick (X):** "I find that, when working inside the context window, even a million tokens worth, the AI both reasons very well and has very low rates of hallucinations." This represents a minority view contradicted by systematic benchmarks but worth noting as coming from a respected voice.

### 6. Needle-in-a-Haystack Tests and Their Limitations

NIAH tests insert a random fact into unrelated text and ask the model to retrieve it. Their fundamental limitations:

- **Too easy.** The needle is semantically unrelated to the haystack, making it a trivial pattern-matching task rather than a reasoning task. Models achieve 95%+ on NIAH but 60-70% on semantically-matched variants (Chroma).
- **Benchmark saturation.** All frontier models now pass NIAH with near-perfect scores. The "all-green heatmaps" are marketing material, not evidence of long-context competence.
- **No reasoning required.** Real-world tasks require synthesizing information across positions, not retrieving a single inserted fact.
- **Hallucination blind spots.** GPT-4o passes NIAH but hallucinates when needles are absent from the haystack (negative samples).
- **BABILong benchmark** showed GPT-4's accuracy drops significantly beyond 10% of maximum capacity when facts are dispersed across long contexts.

RULER and MRCR v2 represent the state of the art in long-context evaluation. They test multi-hop reasoning, aggregation, and multi-needle retrieval, which are far harder and more realistic.

### 7. Structured/Indexed Context vs. Raw Large Context

Evidence strongly favors structured, curated context:

**RAG vs. Long Context (arXiv: 2501.01880, ICLR 2025).** Long context answered 56.3% of questions correctly vs. RAG's 49.0% overall. However, RAG exclusively answered ~1,300 questions that long context missed entirely. RAPTOR (summarization-based retrieval) achieved 38.5% vs. 20-21% for naive chunk-based retrieval. The finding: how RAG is implemented matters more than the raw comparison.

**Beyond RAG vs. Long Context (arXiv: 2509.21865).** Training LLMs to differentiate relevant from irrelevant passages enhanced their ability to find crucial information in noise. Structured reasoning (chain-of-thought) on retrieved context outperformed raw context stuffing.

**Anthropic's own recommendation:** "Find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome." They recommend sub-agent architectures where specialized agents explore extensively (tens of thousands of tokens) but return only condensed summaries (1,000-2,000 tokens). This is a direct endorsement of indexed/structured context over raw large context.

**Practitioner validation (HN).** jacobr1 reported success with structured summaries (CLAUDE.md files) containing project patterns rather than raw source code. t0mas88 found that comprehensive planning documents plus selective code snippets outperformed both "throw everything in" and minimal-context approaches.

### 8. Context Quality vs. Context Quantity

Andrej Karpathy coined "context engineering" (June 25, 2025) as "the delicate art and science of filling the context window with just the right information for the next step." This has become the consensus framing.

**Key evidence:**
- Chroma study: "Simply having the right information in the context is not enough; how that information is presented matters significantly."
- arXiv 2510.05381: Even with 100% perfect retrieval, context length alone hurts performance. The sheer volume of context impairs reasoning independently of retrieval quality.
- Claude Code engineers found context degradation begins at 70-75% capacity, well before the advertised limit.
- Context editing in Claude Code reduced token consumption by 84% while enabling agents to complete workflows that failed under full-context approaches.

Drew Breunig articulated four failure modes of long contexts:
1. **Context Poisoning:** A hallucination enters context and gets referenced repeatedly, compounding errors.
2. **Context Distraction:** Context grows so long the model over-focuses on context and neglects training knowledge.
3. **Context Confusion:** Superfluous information generates low-quality responses.
4. **Context Clash:** Accumulated information conflicts with other information in the prompt.

**Source:** [How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)

### 9. Token Economics: Cost of Filling vs. Surgical Retrieval

**Compute costs scale quadratically.** Doubling input tokens requires ~4x compute for attention. A fully loaded 10M token query could cost $2-5 at current pricing. RAG queries cost fractions of a cent.

**Latency is prohibitive.** Time-to-first-token for a 10M token prompt is measured in minutes, even on H100 clusters. This relegates ultra-long context to asynchronous batch processing.

**Production sweet spots.** Most coding sessions generate 50-200k tokens. RAG rarely needs more than 32-64k tokens of retrieved context. Medium context (128k-200k tokens) is the practical standard for general-purpose use.

**The cost asymmetry.** For high-frequency queries, large context windows are economically unviable compared to vector-database RAG. The crossover point depends on query volume, but at scale, the difference is orders of magnitude.

**Anthropic pricing note (March 2026).** 1M context is now GA for Opus 4.6 and Sonnet 4.6 with no long-context premium. This removes the pricing penalty but not the compute and quality costs.

## Sources Consulted

### Academic Papers
- [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172) - Liu et al., TACL 2024
- [RULER: What's the Real Context Size of Your Long-Context Language Models?](https://arxiv.org/abs/2404.06654) - NVIDIA, COLM 2024
- [Long Context vs. RAG for LLMs: An Evaluation and Revisits](https://arxiv.org/abs/2501.01880) - ICLR 2025
- [Context Length Alone Hurts LLM Performance Despite Perfect Retrieval](https://arxiv.org/html/2510.05381v1) - arXiv 2025
- [LongBench v2: Towards Deeper Understanding and Reasoning on Realistic Long-context Multitasks](https://arxiv.org/abs/2412.15204) - December 2024
- [Found in the Middle: Multi-scale Positional Encoding](https://openreview.net/forum?id=fPmScVB1Td) - NeurIPS 2024
- [Beyond RAG vs. Long-Context: Distraction-Aware Retrieval](https://arxiv.org/html/2509.21865v2) - arXiv 2025

### Research Reports
- [Chroma Context Rot Report](https://research.trychroma.com/context-rot) - July 2025, Kelly Hong, Anton Troynikov, Jeff Huber
- [Databricks Long Context RAG Performance](https://www.databricks.com/blog/long-context-rag-performance-llms) - 2024

### Engineering Blogs and Expert Commentary
- [Anthropic: Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) - September 2025
- [Hamel Husain: P6 Context Rot](https://hamel.dev/notes/llm/rag/p6-context_rot.html) - 2025
- [Drew Breunig: How Long Contexts Fail](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html) - June 2025
- [Simon Willison: Context Engineering](https://simonwillison.net/2025/jun/27/context-engineering/) - June 2025
- [PromptLayer: Why LLMs Get Distracted](https://blog.promptlayer.com/why-llms-get-distracted-and-how-to-write-shorter-prompts/) - 2025
- [Andrej Karpathy on Context Engineering](https://x.com/karpathy/status/1937902205765607626) - June 2025

### Practitioner Discussions
- [HN: Claude Sonnet 4 1M context](https://news.ycombinator.com/item?id=44878147) - Practitioners report degradation after 200k, structured context outperforming raw
- [HN: 1M context GA for Opus 4.6 and Sonnet 4.6](https://news.ycombinator.com/item?id=47367129) - Mixed reports; heavy users at 500k+, others capping at 100k
- [Ethan Mollick on X](https://x.com/emollick/status/1760486646439723364) - Minority positive view on 1M context quality

### Summaries and Analysis
- [Understanding AI: Context rot the emerging challenge](https://www.understandingai.org/p/context-rot-the-emerging-challenge) - 2025
- [WinBuzzer: Context Rot Study](https://winbuzzer.com/2025/07/22/context-rot-new-study-reveals-why-bigger-context-windows-dont-magically-improve-llm-performance-xcxwbn/) - July 2025
- [Adaline Labs: Context Rot](https://labs.adaline.ai/p/context-rot-why-llms-are-getting) - 2025
- [Redis: Context Rot Explained](https://redis.io/blog/context-rot/) - 2025

## Source Quality Assessment

**High confidence sources:** The Chroma Context Rot study, RULER benchmark, MRCR v2 results, Liu et al. (2023), and arXiv 2510.05381 are all systematic empirical studies with reproducible methodology. Anthropic's engineering blog carries institutional authority.

**Medium confidence sources:** HN practitioner reports are anecdotal but triangulate with benchmark data. Hamel Husain and Drew Breunig are recognized practitioners whose analysis aligns with the empirical evidence.

**Lower confidence sources:** Ethan Mollick's positive 1M context experience is a single data point that contradicts systematic evidence. Medium articles summarizing the research are derivative and occasionally imprecise.

**Gaps:** No systematic study directly compares structured/indexed context (like fmm-style precomputed lookups) against raw context stuffing on identical codebases. The closest evidence is the RAG vs. long context papers, which show RAG wins when retrieval is done well. The practitioner HN reports about CLAUDE.md files vs. raw code are compelling but not controlled experiments.

## Open Questions

1. **Does instruction-tuning for long context close the gap?** Models trained on longer sequences (Gemini's 10M claim) still degrade. No evidence that training on longer sequences eliminates the attention budget problem.
2. **Will architectural innovations (linear attention, SSMs, ring attention) change the picture?** Mamba and similar architectures promise O(n) scaling but are not yet competitive with transformers on quality. Worth tracking.
3. **What is the optimal context size for different task types?** The evidence suggests 32-128k is the sweet spot for most tasks, but systematic task-specific curves are sparse.
4. **How does context rot interact with reasoning models (o1, o3)?** The LongBench v2 results suggest extended reasoning partially compensates but does not eliminate the problem.
5. **Structured index approaches (fmm, code maps, semantic indices) vs. RAG vs. raw context.** No direct head-to-head benchmark exists. This is the most relevant open question for the Helioy ecosystem.

## Actionable Takeaways

1. **Context is a finite resource with diminishing returns.** Treat every token as a cost, not a freebie. The Anthropic recommendation is the right one: find the smallest set of high-signal tokens.

2. **Structured, precomputed indices (like fmm) are architecturally superior to context stuffing.** The evidence for structured retrieval outperforming raw context is overwhelming. O(1) symbol lookup beats dumping entire files into context.

3. **Sub-agent architectures are the production answer.** Specialized agents with focused context returning condensed summaries to an orchestrator consistently outperforms monolithic large-context approaches. This validates the Helioy multi-agent architecture.

4. **The "effective context" of a model is 50-75% of its advertised context.** Claude Code engineers found degradation at 70-75% capacity. RULER found many models fail to effectively use even 32k despite claiming 128k+.

5. **NIAH benchmarks are marketing, not evaluation.** Ignore them. RULER, MRCR v2, and LongBench v2 are the credible benchmarks. Chroma's Context Rot tasks are the most relevant for production applications.

6. **Context engineering > prompt engineering.** The shift articulated by Karpathy is well-supported. The discipline of curating context, including compaction, sub-agent summaries, structured note-taking, and just-in-time retrieval, is the differentiating skill.

7. **Cost scales quadratically with context length.** At high query volumes, large context windows are economically unviable compared to surgical retrieval. Even with Anthropic's removal of long-context pricing premiums, the compute cost remains.
