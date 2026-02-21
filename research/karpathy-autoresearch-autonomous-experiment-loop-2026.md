---
title: "Karpathy's Autoresearch: Autonomous Experiment Loop Pattern"
type: research
tags: [autoresearch, karpathy, autonomous-agents, hill-climbing, llm-agents, experiment-loop, optimization]
summary: Autoresearch is a generalizable hill-climbing pattern where an LLM agent autonomously modifies code, runs time-boxed experiments against a single metric, keeps improvements, discards failures, and loops indefinitely.
status: active
source: deep-research
confidence: high
created: 2026-03-25
updated: 2026-03-25
---

## Executive Summary

Autoresearch is an open-source project released by Andrej Karpathy on March 7, 2026 that implements autonomous ML experimentation via a simple loop: an LLM agent modifies a single training file, runs a fixed 5-minute experiment, evaluates against one scalar metric (val_bpb), keeps improvements or discards failures, and repeats indefinitely. The core insight is that this pattern generalizes far beyond ML training to any domain with a measurable scalar metric. Karpathy describes it as "hill climbing with an LLM as the mutation function." The repo reached 30k+ GitHub stars in its first week. Shopify CEO Tobi Lutke independently applied it to the Liquid template engine, achieving 53% faster rendering and 61% fewer allocations overnight.

## 1. What It Is and What Problem It Solves

Autoresearch replaces the human researcher's manual experiment-design-evaluate cycle with an autonomous agent loop. The problem: a human researcher can run maybe 3-5 experiments per day. An agent running autoresearch does 12/hour, 100 overnight, 700 in two days.

The human's role shifts from writing code to writing `program.md`, the instruction document that guides the agent. Karpathy's framing: "You are not touching any of the Python files like you normally would as a researcher. Instead, you are programming the program.md Markdown files that provide context to the AI agents."

## 2. Architecture and How It Works

### Three Files

| File | Role | Who Edits |
|------|------|-----------|
| `prepare.py` | Data loading, tokenizer, eval function, constants | Nobody (immutable) |
| `train.py` | Complete GPT model + training loop (~630 lines) | Agent |
| `program.md` | Agent instructions ("super lightweight skill") | Human |

### The Loop (from program.md)

1. Review current git state
2. Modify `train.py` with experimental changes
3. Commit changes
4. Execute `uv run train.py > run.log 2>&1`
5. Extract results (`grep "^val_bpb:" run.log`)
6. If improved: keep the commit, advance branch
7. If not improved: `git reset` to previous state
8. Log results to `results.tsv` (commit hash, val_bpb, memory, keep/discard, description)
9. Repeat. "Do NOT pause to ask the human if you should continue."

### Setup Phase

- Create git branch `autoresearch/<tag>` from master
- Agent reads all three files for context
- Verify data in `~/.cache/autoresearch/`
- Initialize empty `results.tsv`
- First run establishes baseline with unmodified code

### Constraints Enforced by program.md

- Only `train.py` may be modified
- Cannot install new packages
- Cannot modify the evaluation function `evaluate_bpb`
- Kill any run exceeding 10 minutes (treat as failure)
- Architecture, optimizer, hyperparameters, batch size, model size are all fair game

## 3. Key Design Principles

### The Four Constraints (the real insight)

1. **One file** to modify. Keeps scope manageable, diffs reviewable
2. **One metric** to optimize (val_bpb, lower is better). Eliminates ambiguity about "better"
3. **Fixed evaluation budget** (5 minutes wall-clock). Makes every experiment directly comparable regardless of what changed
4. **Binary keep/discard rule**. No hedging, only forward progress

### Why These Constraints Matter

- Fixed time budget means platform-specific optimization: discovers the best model *your hardware can train in 5 minutes*
- val_bpb is vocabulary-size-independent, enabling fair comparison across architectural variations
- Single file constraint prevents the agent from drifting into infrastructure changes
- Git checkpoint at every step means the entire history is auditable and reversible

### Agent Choice

Explicitly agent-agnostic. Karpathy: "Claude/Codex or whatever you want." The instruction document format works with any coding agent.

### Not Hyperparameter Tuning

Karpathy distinguishes autoresearch from traditional HPO in three ways (from HN thread):
1. **Arbitrary code modification** - not parameter sweeps but actual code changes (architecture, optimizer logic)
2. **Sequential LLM execution** - the agent reasons about *why* a change might work, enabling efficient binary search rather than grid/random search
3. **Full automation** - zero human intervention during the loop

## 4. Results

### First Overnight Run (March 7-8, 2026)
- 126 experiments
- val_bpb: 0.9979 -> 0.9697
- Notable discovery: weight decay on everything + init scaling

### Extended Two-Day Run
- ~700 experiments with valid results
- ~20 additive improvements that transferred to larger models
- Time-to-GPT-2 benchmark: 2.02 hours -> 1.80 hours (11% efficiency gain)
- Agent independently discovered novel architecture tweaks (reordering QK Norm and RoPE)

### SkyPilot Cluster Scaling (16 GPUs)
- ~910 experiments submitted, ~700 with valid results
- val_bpb: 1.003 -> 0.974 (2.87% improvement)
- ~90 experiments/hour (9x over single GPU)
- ~8 hours wall-clock vs ~72 hours estimated sequential
- Cost: ~$300 compute + $9 API
- Agent emergently discovered: width matters more than any single hyperparameter, H200 vs H100 performance differences, and self-invented two-tier validation (screen on H100, validate on H200)

### Shopify/Liquid (Non-ML Application)
- Tobi Lutke ran autoresearch overnight on Liquid template engine
- 120 experiments, 93 commits
- 53% faster combined parse+render time
- 61% fewer object allocations
- All 974 unit tests passing

## 5. Known Limitations and Criticisms

### Low Creativity (GitHub Issue #22)
- Agents behave conservatively due to RLHF training
- Karpathy acknowledged agents feel "cagy and scared" on open-ended problems
- "Half capability issue and half skill issue"
- Agent self-identified problematic changes post-hoc (e.g., recognized random seed change was "weird")

### Hill Climbing / Local Optima
- Single-GPU version is pure greedy hill climbing
- Can get stuck at local optima where no single-step change improves the metric
- Fixed 5-minute window biases toward quick-to-manifest improvements; changes requiring longer training remain invisible

### Not True Self-Improvement
- The agent optimizes training code for a separate, smaller model
- It does not modify its own weights or capabilities
- Important distinction for safety discourse

### Creativity Ceiling
- Human researchers still needed for genuinely novel research directions
- The tool excels at methodical iteration, not paradigm shifts

### Proposed Mitigations
- Multiple loops from different starting points
- Randomization in experiment selection
- Meta-prompt optimization (second agent rewrites program.md based on results)
- Diversity directives rewarding novelty alongside improvement
- Periodic "reset" experiments from earlier checkpoints to escape local optima
- "Chief scientist" planning agent that identifies working approaches, reviews literature, and delegates experiments to execution agents

## 6. The Generalized Pattern ("Karpathy Loop")

Analyst Janakiram MSV defined the Karpathy Loop as three components:
1. An agent with access to modifiable files
2. A single objectively testable metric for optimization
3. Fixed time constraints for experiment execution

### Generalizing Beyond ML

Strip away LLM specifics and you have: pick one modifiable file, one measurable metric, one evaluation budget, and let the agent iterate autonomously. Karpathy himself: "*any* metric reasonably efficient to evaluate" could be autoresearched by agent swarms.

Documented applications beyond ML training:
- GPU kernel optimization (AutoKernel: Triton/CUDA kernels, ~40 experiments/hour)
- Template engine performance (Shopify Liquid)
- API response time
- Bundle size
- Test pass rate / coverage
- Build speed
- Memory usage
- Content headline click-through
- System prompt quality
- Terraform compliance
- Accessibility scores

### Community Forks

- **autoexp** - Generalized autonomous experimentation loop for any quantifiable metric
- **autoresearch-at-home** - SETI@home-style distributed version where multiple agents claim experiments, publish results, and pull global best configuration
- **AutoKernel** - Applied to GPU kernel optimization with KernelBench (250+ problems, 4 difficulty levels)

## 7. Karpathy's Broader Vision

### The "Loopy Era" (from No Priors podcast, March 2026)

- **2025 ("Vibe Coding")**: Users describe desired outcomes and receive working software
- **2026 ("Agentic Engineering")**: Humans direct and supervise agent teams rather than writing code directly

"Agents crossed a coherence threshold around Dec 2025," enabling reliable multi-day iteration cycles.

### Multi-Agent Research Community

"The next step for autoresearch is that it has to be asynchronously massively collaborative for agents (think: SETI@home style). The goal is not to emulate a single PhD student, it's to emulate a research community of them."

Current code synchronously grows a single thread of commits. The vision: agents on different machines explore different research directions, publish results (including failures), and pull the current global best. Karpathy noted that Git/GitHub is "almost but not really suited for this" because of its built-in assumption of one master branch.

### Frontier Lab Adoption

"All LLM frontier labs will do this. It's the final boss battle." He acknowledged "it's a lot more complex at scale of course" but emphasized "it's going to work."

## Sources Consulted

### Primary Sources
- [karpathy/autoresearch GitHub repo](https://github.com/karpathy/autoresearch) - README, program.md, issues, discussions
- [Karpathy announcement tweet](https://x.com/karpathy/status/2030371219518931079) - March 7, 2026
- [Karpathy SETI@home vision tweet](https://x.com/karpathy/status/2030705271627284816)
- [Karpathy clarification tweet](https://x.com/karpathy/status/2031137476438548874) - "you don't use it directly, it's just a recipe/idea"
- [GitHub Issue #22: Low creativity](https://github.com/karpathy/autoresearch/issues/22)
- [GitHub Discussion #43: Session report 0.9979 -> 0.9697](https://github.com/karpathy/autoresearch/discussions/43)

### In-Depth Technical Analysis
- [SkyPilot Blog: Scaling Autoresearch to GPU Cluster](https://blog.skypilot.co/scaling-autoresearch/) - 16-GPU results, phase analysis, cost breakdown
- [Mager.co: Autoresearch as Blueprint for Self-Improving Agents](https://www.mager.co/blog/2026-03-14-autoresearch-pattern/) - Generalized pattern analysis
- [NextBigFuture: Karpathy on Code Agents and the Loopy Era](https://www.nextbigfuture.com/2026/03/andrej-karpathy-on-code-agents-autoresearch-and-the-self-improvement-loopy-era-of-ai.html) - No Priors podcast summary

### Journalism / Analysis
- [VentureBeat: Autoresearch lets you run hundreds of AI experiments](https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai)
- [Fortune: The Karpathy Loop - 700 experiments, 2 days](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/)
- [DataCamp: Guide to AutoResearch](https://www.datacamp.com/tutorial/guide-to-autoresearch)
- [The New Stack: 630-line Python script ran 50 experiments overnight](https://thenewstack.io/karpathy-autonomous-experiment-loop/)

### HackerNews Discussions
- [HN: Autoresearch announcement (208 points, 58 comments)](https://news.ycombinator.com/item?id=47291123)
- [HN: Scaling Autoresearch](https://news.ycombinator.com/item?id=47442435)
- [HN: AutoKernel - Autoresearch for GPU Kernels](https://news.ycombinator.com/item?id=47332688)
- [HN: The Karpathy Loop - 700 experiments](https://news.ycombinator.com/item?id=47494216)

### Community Forks / Extensions
- [autoresearch-at-home](https://github.com/mutable-state-inc/autoresearch-at-home) - Distributed collaborative version
- [AutoKernel](https://github.com/RightNow-AI/autokernel) - GPU kernel optimization
- [autoexp gist](https://gist.github.com/adhishthite/16d8fd9076e85c033b75e187e8a6b94e) - Generalized for any metric

### Reddit
- No relevant threads found. The autoresearch community discussion lives on GitHub, HN, and X.

## Source Quality Assessment

**Confidence: HIGH**. Primary sources are Karpathy's own repo, tweets, and podcast appearances. Technical claims verified by independent reproduction (SkyPilot cluster run, Shopify/Liquid run). HN discussion includes direct responses from Karpathy. The only gap is that X/Twitter content cannot be directly fetched (JS-rendered), so tweet text is reconstructed from search snippets and secondary sources.

## Open Questions

1. **Long-horizon experiments**: The 5-minute budget biases toward quick wins. How does the pattern adapt when the evaluation itself takes hours (e.g., full training runs, integration test suites)?
2. **Multi-metric optimization**: Current pattern uses one scalar. How to handle Pareto-optimal tradeoffs (speed vs. accuracy vs. memory)?
3. **Coordination at scale**: Git's single-master assumption limits the SETI@home vision. What coordination primitive replaces it?
4. **Agent creativity**: RLHF-trained models are conservative. Does fine-tuning or prompting overcome this, or is it fundamental?
5. **Transferability**: Improvements found on 5-minute runs on small models may not transfer to production-scale training. The 11% Time-to-GPT-2 gain is promising but not guaranteed at frontier scale.

## Actionable Takeaways: Application to Geometric Memory System (am-core)

The autoresearch pattern maps directly to any Rust codebase with benchmarkable metrics. For attention-matters specifically:

### Candidate Metrics
- **Query recall quality** - given a known corpus, measure retrieval precision/recall against a gold standard
- **Geodesic distance accuracy** - benchmark SLERP and quaternion operations against reference implementations
- **Scoring composite quality** - end-to-end ingest-then-query with known-good expected neighborhoods
- **Performance** - `cargo bench` wall-clock for core operations (query, drift, Kuramoto coupling)
- **Memory efficiency** - peak RSS during ingest of a standard corpus

### How to Structure It
1. **Immutable evaluation harness** (analogous to `prepare.py`): a Rust binary or script that ingests a fixed corpus, runs a battery of queries, and outputs a single composite score
2. **Modifiable target** (analogous to `train.py`): one or more source files containing the scoring, drift, or coupling logic
3. **Instruction document** (analogous to `program.md`): markdown describing the architecture, what the agent may change, and how to interpret the metric
4. **Fixed time budget**: `cargo test` + `cargo bench` completes in a bounded window
5. **Git-based checkpoint**: same branch/commit pattern

### Key Adaptation Challenges
- Rust compilation adds latency to each experiment cycle (mitigate with incremental compilation, `cargo-nextest`)
- Multiple interacting modules (scoring, recency, activation) vs. Karpathy's single-file constraint. May need to scope to one module at a time
- The S3 manifold math has correctness invariants that a pure metric-optimization agent could violate (unit quaternion constraint, golden-angle distribution). The evaluation harness must encode these as hard constraints, not just the optimization metric
