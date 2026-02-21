---
title: Multi-Agent Council Frameworks: Architecture, Consensus Mechanisms, and Production Considerations
type: research
tags: [multi-agent, council, deliberation, consensus, LLM, orchestration, nancy, architecture]
summary: Comprehensive survey of multi-agent council patterns, consensus mechanisms, and production trade-offs to inform council mechanism design for the Nancy orchestrator.
status: active
source: deep-research
confidence: high
created: 2026-03-08
updated: 2026-03-08
---

## Executive Summary

Multi-agent council frameworks -- where multiple LLM agents deliberate, vote, or debate to reach a decision -- have emerged as a significant research and engineering area over 2023-2025. The foundational result (Du et al., ICML 2024) showed multi-agent debate improves factuality and reasoning. However, subsequent benchmarking reveals the story is more nuanced: council patterns do not uniformly outperform single-agent baselines, and their effectiveness is strongly task-dependent. The key practical finding for Nancy: **heterogeneous model composition outperforms homogeneous ensembles**, **voting suits reasoning tasks while consensus suits knowledge tasks**, and **token cost multipliers of 5-10x demand careful architectural budgeting**.

The most production-relevant pattern for Nancy is a three-phase council: independent parallel proposals, anonymous peer critique with confidence-weighted ranking, and a designated synthesizer agent that aggregates into a final decision. This mirrors Karpathy's llm-council (15.4k stars), ReConcile (ACL 2024), and the D3 framework's MORE protocol.

---

## Detailed Findings

### 1. Foundational Research

#### 1.1 Du et al. "Improving Factuality and Reasoning through Multiagent Debate" (ICML 2024)

- arXiv: 2305.14325 | GitHub: composable-models/llm_multiagent_debate
- The canonical paper establishing that multiple LLM instances proposing and debating their responses over multiple rounds improves mathematical reasoning and reduces hallucinations.
- Experimental setup: **3 agents, 2 rounds** of debate. Agents share full response text between rounds and refine positions based on peer responses.
- Key mechanism: agents see all other agents' previous-round responses and revise their own answer. No anonymization in the base protocol.
- Performance scales with agent count and debate rounds, but with diminishing returns.
- Applicable to black-box models with no fine-tuning required -- same prompts across all tasks.
- Limitation identified by later work: it works on benchmarks but does not universally outperform self-consistency.

#### 1.2 "More Agents Is All You Need" (February 2024)

- arXiv: 2402.05120 | HN discussion: 39955725
- Finding: sampling the same LLM query N times and running majority vote scales performance monotonically, with most gain from the first 10 agents and diminishing returns after 20.
- Critically, this requires **no inter-agent communication** -- it is pure ensemble sampling.
- HN commenters correctly noted this is essentially the randomized algorithms insight applied to LLMs: if temperature > 0, running N times and picking majority improves output.
- Identified failure mode: when a model hallucinates consistently (not chaotically), majority voting fails -- it selects the most common wrong answer.
- Performance gain is correlated with task difficulty; harder tasks benefit more from more agents.

#### 1.3 Mixture-of-Agents (MoA) -- Together AI (June 2024)

- arXiv: 2406.04692 | GitHub: togethercomputer/MoA (2.9k stars)
- Architecture: layered graph where each layer has multiple LLM agents, each receiving all outputs from the prior layer as auxiliary context when generating its response.
- Identifies two distinct roles:
  - **Proposers**: generate diverse initial responses. WizardLM is an exemplary proposer -- diverse and useful as reference, poor as aggregator.
  - **Aggregators**: synthesize multiple inputs into higher-quality outputs. Strong aggregators: Qwen1.5, LLaMA-3-70B, GPT-4o.
- **Collaborativeness phenomenon**: LLMs generate better responses when shown other models' outputs, even if those outputs are lower quality than what the LLM could generate alone. This is the core empirical insight justifying layered architectures.
- Performance: MoA (6 proposers, 3 layers) achieves 65.1% on AlpacaEval 2.0 vs GPT-4o's 57.5%.
- MoA-Lite (2 layers) achieves 59.3% at 2x cost-efficiency vs GPT-4 Turbo.
- Ablation: more diverse proposers consistently outperform same-model multiple-temperature sampling at equal token budgets.

#### 1.4 ReConcile -- UNC Chapel Hill (ACL 2024)

- arXiv: 2309.13007
- Architecture: round-table conference model with **confidence-weighted voting** across diverse LLMs.
- Each round: each agent sees grouped answers from prior round plus their confidence scores plus human-style explanation demonstrations.
- Agents are explicitly prompted to convince others, not just update their own answers.
- **Confidence weighting**: agents that express higher confidence in prior rounds get proportionally higher weight in consensus calculation.
- Results: up to 11.4% improvement over single-agent baselines, 8% over GPT-4 on MATH benchmark, using mixed API + open-source + domain-specific models.
- Key finding: **diversity originating from different models is critical**. Mixing model families beats using the same model multiple times.
- Published at ACL 2024; one of the strongest empirical validations of the heterogeneous council approach.

#### 1.5 "Voting or Consensus?" -- ACL 2025 Findings

- arXiv: 2502.19130
- Task-dependent decision-making study across 7 benchmarks.
- **Voting beats consensus on reasoning tasks** (MuSR: +26.4%, SQuAD 2.0: voting 56.7% vs consensus 43.6% F1).
- **Consensus beats voting on knowledge tasks** (MMLU: +2.3%, MMLU-Pro: +4.9%).
- More discussion rounds _decrease_ accuracy -- agents drift from original tasks during extended dialogue.
- Novel methods proposed:
  - **All-Agents Drafting (AAD)**: forces independent initial solutions before any interaction (+3.3% over baseline MAD).
  - **Collective Improvement (CI)**: restricts communication to showing only solution differences between turns (+7.4%).
  - Both methods succeed by preserving answer diversity.
- Computational cost: multi-agent debates require approximately **5-10x the compute** of single-agent baselines.

#### 1.6 MAD Benchmarking (ICLR 2025 Blog Post)

- Reference: d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/
- Cross-framework benchmarking across 9 tasks revealed MAD **does not consistently outperform** chain-of-thought + self-consistency.
- Specific failure modes:
  - **Answer preservation problem**: MAD sometimes corrects wrong answers but equally often reverses correct answers. Net effect is often neutral.
  - **Multi-persona weakness**: once a judge decides one side is correct, debate terminates, preventing continued refinement.
  - **No consistent scaling**: more agents and more rounds do not reliably improve accuracy.
- Recommendation: MAD works best with **heterogeneous model combinations** (e.g., GPT-4o-mini + Llama 3.1-70b showed improvement where homogeneous pairings did not).
- Implication for Nancy: council is not a silver bullet; it needs careful task routing.

---

### 2. Framework Implementations

#### 2.1 karpathy/llm-council

- GitHub: github.com/karpathy/llm-council (15.4k stars)
- Description: Andrej Karpathy's Saturday hack implementing the three-phase deliberation pattern.
- Stack: FastAPI backend, React/Vite frontend, OpenRouter API, JSON file storage.
- Architecture (three stages):

  ```
  Stage 1: Parallel query -- all council models receive user query simultaneously.
           Responses collected; only successful responses included.

  Stage 2: Anonymous peer review -- model identities replaced with alphabetic labels
           ("Response A", "Response B"...) to prevent brand favoritism.
           Each model ranks all other models' responses by accuracy and insight.

  Stage 3: Chairman synthesis -- designated model receives all Stage 1 responses
           + all Stage 2 peer rankings with full anonymized context, produces
           consolidated final answer.
  ```

- Anonymous ranking implementation:
  ```python
  labels = [chr(65 + i) for i in range(len(stage1_results))]
  label_to_model = {f"Response {label}": result["model"]
                    for label, result in zip(labels, stage1_results)}
  ```
- Aggregate ranking: positions averaged across evaluators; lower average rank = better.
- Key insight from creator: "LLM identities are anonymized so the LLM cannot favor anyone."
- Performance: 4x slower (12s vs 3s), 4x higher API cost vs single model.
- Failure handling: gracefully continues with partial council if some models time out.
- Not designed for production; explicitly marked as ephemeral prototype.

#### 2.2 D3 -- Debate, Deliberate, Decide (October 2024)

- arXiv: 2410.04663
- The most architecturally complete adversarial council framework.
- **Agent roles**:
  - **Advocates**: generate arguments for assigned answers (anonymized, no model identity).
  - **Judge**: scores arguments on 1-20 scale across 6 criteria (relevance, accuracy, depth, clarity, reasoning, addressing opponent points); provides feedback guiding iterative refinement.
  - **Jurors**: diverse panel with assigned personas (e.g., "retired professor of ethics", "technology entrepreneur") independently evaluate final transcripts and vote.
- **Two protocols**:
  - **MORE (Multi-Advocate One-Round)**: k=3 advocates per answer argue in parallel; consolidated; judge evaluates once. Optimized for efficiency when one answer is clearly superior.
  - **SAMRE (Single-Advocate Multi-Round)**: single advocate per answer; iterative turn-based debate with judge feedback; more expensive but deeper analysis for closely matched options.
- **Budgeted stopping**: terminates when score gap stabilizes (convergence) OR token budget exceeded. Makes deep evaluation cost-predictable.
- Cost vs accuracy: D3-MORE at ~5,000 tokens per evaluation (vs ~1,250 baseline) delivers +12.6% absolute accuracy on MT-Bench (85.1% vs 72.5%).
- Bias reductions: positional bias drops from 81.7% to 96.2% swap-consistency; self-enhancement bias from 24.6% to 8.4%.

#### 2.3 AutoGen Group Chat (Microsoft)

- GitHub: microsoft/autogen (200k+ downloads in first 5 months of 0.4)
- Two major version lines: 0.2 (GroupChat API) and 0.4+ (actor model, event-driven).
- **GroupChat pattern (v0.2)**:
  - GroupChatManager selects next speaker via LLM or FSM transition rules.
  - Speaker selection methods: "auto" (LLM-driven), "round_robin", "random", "fsm" (finite state machine with explicit transition graph).
  - FSM mode (added Feb 2024): directed transition matrix fed into GroupChat. Each agent's `description` parameter describes transition conditions in natural language; LLM evaluates conditions to select next speaker.
  - StateFlow extension (Feb 2024): customizable speaker selection functions enabling arbitrary state machine behaviors.
- **v0.4 architecture (actor model)**:
  - Layered: Core (actor model, async messaging) -> AgentChat (team abstractions) -> Extensions (third-party integrations).
  - Teams: `RoundRobinGroupChat`, `SelectorGroupChat` (replaces v0.2 GroupChat).
  - Swarm pattern: agents delegate to other agents via tool calls; all share same message context.
  - Fully asynchronous, event-driven, typed throughout.
- AutoGen suits council patterns where agents need to communicate in conversational turns. Best framework for debate scenarios requiring back-and-forth.

#### 2.4 CrewAI Hierarchical Process

- GitHub: crewAIInc/crewAI
- Two process modes: `sequential` and `hierarchical`. A third "consensual process" is planned but not yet shipped (as of March 2026).
- **Hierarchical mode**: automatically creates a manager agent that allocates tasks among crew members based on their roles, reviews outputs, and escalates or recovers based on completion quality.
- Manager agent can be user-defined or auto-created.
- Less suited for deliberation/council than for task delegation -- it is more corporate management structure than round-table debate.
- The planned "consensual process" is the relevant upcoming feature for council-style coordination, but its architecture has not been published.

#### 2.5 LangGraph Supervisor Pattern

- GitHub: langchain-ai/langgraph-supervisor-py
- Architecture: graph-based where each agent is a node, edges represent control flow managed by a central supervisor node.
- Three-layer structure:
  - **Planner Layer**: supervisor/orchestrator that decides task dispatch.
  - **Agents Layer**: specialized worker agents, each with focused tool sets.
  - **Tooling Layer**: shared tools accessible to multiple agents.
- Supervisor coordinates via tool calls rather than a dedicated library; LangChain now recommends tool-calling supervisor over the older dedicated library approach.
- State flows through the graph; agents communicate by adding to shared graph state.
- Well-suited for sequential pipelines with conditional routing, not natural for simultaneous deliberation.

#### 2.6 OpenAI Swarm (experimental)

- GitHub: openai/swarm
- Superseded by OpenAI Agents SDK (production-ready replacement).
- Core concepts: **Agents** (LLM + instructions + tools) and **handoffs** (agent transfers active conversation to another agent).
- Stateless architecture -- no retained state between calls.
- Useful as a reference for handoff primitive design, not a council pattern.

#### 2.7 AI Council (browser-based, 2026)

- HN: news.ycombinator.com/item?id=47095909
- Purely static browser app; API calls go directly from browser to LLM providers.
- Supports mixing Ollama (local), OpenAI, Anthropic, Groq, Google in any combination.
- Same three-phase pattern as llm-council: independent responses, anonymous peer critique, Chairman synthesis.
- Key observations from creator:
  - Reasoning models emit intermediate thinking blocks; display a "Thinking..." indicator while stripping these.
  - Uncensored models produce meaningfully different critiques than safety-tuned alternatives.
  - "Peer review across models catches blind spots that a single model arguing with itself won't surface."

#### 2.8 Chorus (multi-agent epistemological debate, December 2025)

- HN: news.ycombinator.com/item?id=46191564
- Unconventional approach: instead of role-based agents, each agent operates under a distinct **epistemological framework** -- a set of rules about what counts as valid knowledge and what reasoning moves are allowed.
- Framework collision creates productive tension (e.g., metric-based validity vs narrative-based validity).
- Goal is structured disagreement producing novel insights, not consensus.
- 33 frameworks emerged organically through debates rather than manual design.
- Relevant for Nancy if council is meant to surface blind spots rather than converge on a single answer.

#### 2.9 chain-ml/council

- GitHub: chain-ml/council (846 stars)
- Primarily an enterprise LLM abstraction layer rather than a council deliberation framework despite the name.
- Provides unified interface across OpenAI, Anthropic, Google, Groq, Ollama.
- Built-in retry/error handling, usage monitoring.
- Not architecturally relevant to the council pattern -- naming is coincidental.

---

### 3. Topology Patterns

#### 3.1 Star Topology (Supervisor + Workers)

```
         [Supervisor / Chairman]
        /     |       |        \
   [A1]     [A2]    [A3]      [A4]
```

- Supervisor selects speakers, aggregates, synthesizes.
- Examples: AutoGen GroupChat with SelectorGroupChat, LangGraph supervisor, llm-council Stage 3.
- Strengths: clear control flow, single point of synthesis, easy to reason about.
- Weaknesses: supervisor is a single point of failure; supervisor bias shapes final output.

#### 3.2 Layered / Pipeline Topology (MoA Pattern)

```
Layer 1:  [P1] [P2] [P3] [P4] [P5] [P6]   (Proposers)
                       |
Layer 2:  [A1] [A2] [A3]                   (Aggregators see all L1 outputs)
                       |
Layer 3:  [Final Aggregator]
```

- Each layer processes all outputs from the prior layer.
- Examples: Together AI MoA (2-3 layers typical).
- Strengths: collaborativeness effect compounds across layers; diverse proposers provide rich input space.
- Weaknesses: token cost multiplies with each layer; slower than single-pass.

#### 3.3 Round-Table / Mesh Topology (Peer Debate)

```
[A1] <--> [A2] <--> [A3]
  \         |        /
   [A4] <--------> [A5]
```

- All agents see all other agents' outputs and respond in rounds.
- Examples: Du et al. multiagent debate, ReConcile round-table conference.
- Strengths: agents can directly rebut specific claims; richest information exchange.
- Weaknesses: quadratic communication growth with agent count; sycophancy and echo chamber risks.

#### 3.4 Adversarial / Advocate-Judge Topology (D3 Pattern)

```
[Advocate A]  [Advocate B]
      \            /
       [Judge Agent]
            |
    [Juror Panel: J1, J2, J3]
            |
      [Final Verdict]
```

- Explicit adversarial roles; judge enforces structure; juror panel diversifies final evaluation.
- Examples: D3 (arXiv 2410.04663), CourtEval (prosecutor/defender/grader).
- Strengths: bias-resistant through role separation; interpretable through explicit argument chains; positional bias reduction via anonymization.
- Weaknesses: most complex to implement; role assignment requires careful prompt engineering.

#### 3.5 Anonymous Peer Ranking (llm-council / AI Council Pattern)

```
Phase 1: Parallel independent proposals
         [A] [B] [C] [D] -> responses collected

Phase 2: Anonymous cross-review (each agent evaluates relabeled others)
         A sees "Response 1, Response 2, Response 3" (not knowing which is B, C, D)
         B sees "Response 1, Response 2, Response 3"
         ...

Phase 3: Aggregate ranking computed, Chairman synthesizes
```

- Strengths: eliminates brand bias in evaluation; computationally predictable (fixed 3 phases); graceful partial failure (continue with successful subset).
- Weaknesses: no iterative refinement; Chairman is a single point of synthesis bias.

---

### 4. Consensus Mechanisms

#### 4.1 Majority Voting

- Each agent produces an answer; most frequent answer wins.
- Baseline from "More Agents Is All You Need" (2024).
- Works well for well-defined tasks with clear correct answers.
- Fails when models share systematic biases (consistent hallucinations defeat voting).
- Implementation: Swarms framework has `MajorityVoting` module with multi-loop consensus building.

#### 4.2 Confidence-Weighted Voting

- Agents report confidence scores with their answers.
- Final answer weighted by confidence: `softmax(confidence_i) * vote_i`.
- Used in: ReConcile (confidence scores shown to all agents in subsequent rounds).
- More sophisticated: dynamically adjust weights based on each model's historical accuracy.
- Failure mode: LLMs are often poorly calibrated -- expressed confidence does not reliably track accuracy.

#### 4.3 Iterative Refinement with Convergence Detection

- Agents update positions across rounds until answers stabilize.
- AI Counsel (HN 45786800): evidence-based tools + convergence detection stops automatically when consensus detected.
- Risk: "Voting or Consensus?" paper found more rounds decrease accuracy due to topic drift.
- Mitigation: bound rounds (D3's budgeted stopping) or use AAD/CI to preserve diversity.

#### 4.4 Anonymous Ranked-Choice Aggregation

- Each agent ranks all other responses; positions averaged; lowest average rank wins.
- llm-council pattern: rank positions averaged across all evaluating agents.
- Anonymous labels prevent brand favoritism.
- Strengths: captures relative quality ordering, not just correctness; works for open-ended tasks.

#### 4.5 Adversarial Debate with Structured Adjudication

- D3 MORE/SAMRE: dedicated advocates argue; judge scores on multiple criteria; juror panel votes.
- Most expensive but most bias-resistant.
- Works best for evaluation tasks (judging LLM outputs) rather than generation tasks.

#### 4.6 Hierarchical Delegation (Not True Consensus)

- CrewAI hierarchical mode: manager decides, workers execute, manager validates.
- AutoGen supervisor: LLM selects next speaker based on conversation state.
- Not a consensus mechanism -- authority is concentrated in manager/supervisor.
- Faster, more predictable, but outputs reflect manager model's biases.

---

### 5. Production Considerations

#### 5.1 Token Cost Multiplication

- Single agent chat: baseline 1x.
- Single agent agentic (tools, loops): ~4x (Anthropic internal data).
- Multi-agent council: ~15x (Anthropic), or 5-10x per ACL 2025 research.
- Real framework measurements: MetaGPT 72% token duplication, CAMEL 86%, AgentVerse 53%.
- A $5-50 demo workflow can become $18,000-90,000/month at scale.
- Mitigation strategies:
  - MoA-Lite (2 layers instead of 3): 2x cost efficiency with comparable quality.
  - Selective routing: only invoke council for high-stakes or ambiguous decisions.
  - Token budgeting with hard limits (D3's budgeted stopping).
  - Memory consolidation: reduces context by 3.7x in some approaches.

#### 5.2 Latency

- llm-council benchmark: 12 seconds vs 3 seconds for single model (4x).
- Sequential debate rounds compound latency.
- Mitigation: parallel Phase 1 (all agents query simultaneously), only Phase 2 review is potentially sequential.
- For Nancy: council invocation should be an async background task with non-blocking status updates.

#### 5.3 Failure Handling

- **Partial failure (model unavailable)**: llm-council pattern -- "only include successful responses" -- council proceeds with available subset.
- **Cascading failure (error propagation)**: centralized coordination contains error amplification to ~4.4x vs 17.2x in uncoordinated "bag of agents" architectures.
- **Answer preservation failure**: council sometimes reverses correct answers. Mitigation: require supermajority to override initial answer (require 2/3 agreement to change from one agent's original output).
- **Sycophancy / echo chamber**: agents capitulate to majority regardless of correctness. Mitigations:
  - Anonymous peer review hides model identities.
  - Require agents to maintain position unless presented with new arguments (explicit debate rules).
  - Use heterogeneous models (different model families less likely to share biases).
  - Bounded rounds (sycophancy worsens with more rounds).

#### 5.4 Context Synchronization

- In star topology: supervisor holds shared state; agents receive curated context per-request.
- In mesh topology: each agent maintains own context; synchronization via explicit message passing. Coordination overhead grows as O(n^2) with agent count.
- Recommended architecture: single authoritative shared memory store (vector DB or key-value) readable by all agents, with namespace access control per agent role.
- For Nancy: helioy-bus is the existing inter-agent messaging primitive; council state can live in bus messages with a dedicated council coordinator agent managing state transitions.

#### 5.5 When NOT to Use a Council

Based on research synthesis:

- Tasks with clearly correct answers and reliable single-agent accuracy: council adds cost without benefit.
- Tasks requiring fast response (< 5 seconds): council latency is incompatible.
- Homogeneous model ensembles: diversity benefits disappear; cost multiplied without quality gain.
- Extended debate rounds on any task: more rounds tend to decrease accuracy.
- Tasks where models share systematic biases: voting amplifies shared errors.

Council adds clear value for:

- High-stakes decisions where cost of error exceeds council overhead.
- Tasks where different model families genuinely disagree (signaling genuine ambiguity).
- Evaluation tasks (judging output quality) rather than generation tasks.
- Knowledge-type tasks where consensus protocol suits (vs reasoning tasks where voting suits).

---

### 6. Rust-Specific Landscape

No mature Rust-native multi-agent council framework exists as of March 2026. The ecosystem has:

- **AutoAgents** (liquidos-ai/AutoAgents): multi-agent Rust framework with typed pub/sub communication and environment management. No deliberation/council primitives.
- **Kowalski** (v0.5.0): federation layer for multi-agent Rust orchestration -- registry and task-passing layers. No consensus mechanisms.
- **rusty_agent** (tmetsch/rusty_agent): basic multi-agent framework, no council patterns.

This is a gap. Nancy (nancyr) would be the first Rust-native orchestrator with deliberative council mechanics if implemented. The Python-centric nature of existing council implementations (llm-council, ReConcile, D3 are all Python) means Nancy has no direct port to draw from, but the architectural patterns translate cleanly to Rust async.

---

### 7. Society of Mind and Academic Foundations

Minsky's 1986 "Society of Mind" theory -- intelligence emerging from many small specialized processes rather than a monolithic mind -- is experiencing renewed relevance in LLM multi-agent research.

**Sibyl system**: explicitly implements a "multi-agent debate-based jury" directly inspired by Society of Mind, where several agent "jurors" discuss and refine answers before producing a final response. Results showed dramatic accuracy improvement on challenging QA problems.

**Modern instantiation**: the solver/critic/refiner loop (one agent proposes, another finds flaws, a third refines) is the practical modern equivalent of Minsky's "agent specialization." Practitioners report this loop consistently improves factual accuracy across diverse tasks.

**X-MAS research** (arXiv 2505.16997): "Diversity for the Win" -- heterogeneous LLM systems with mixed chatbot + reasoner architectures improved AIME-2024 from 20% to 50% for AgentVerse, 40% to 63% for DyLAN. The mechanism: different model architectures have complementary error profiles that don't compound.

---

## Sources Consulted

### Key Papers

- Du et al. "Improving Factuality and Reasoning through Multiagent Debate" -- arxiv.org/abs/2305.14325 (ICML 2024)
- Li et al. "More Agents Is All You Need" -- arxiv.org/abs/2402.05120 (Feb 2024)
- Wang et al. "Mixture-of-Agents Enhances LLM Capabilities" -- arxiv.org/abs/2406.04692 (June 2024)
- Chen et al. "ReConcile: Round-Table Conference Improves Reasoning" -- arxiv.org/abs/2309.13007 (ACL 2024)
- Hadi et al. "D3: Debate, Deliberate, Decide" -- arxiv.org/abs/2410.04663 (Oct 2024)
- Kaesberg et al. "Voting or Consensus? Decision-Making in Multi-Agent Debate" -- arxiv.org/abs/2502.19130 (ACL 2025)
- Smit et al. "Should we be going MAD?" -- proceedings.mlr.press/v235/smit24a.html (ICML 2024/ICLR 2025 blog)
- Rethinking MoA -- huggingface.co/papers/2502.00674 (Feb 2025)
- X-MAS: Heterogeneous LLM Multi-Agent Systems -- arxiv.org/abs/2505.16997

### GitHub Repositories

- karpathy/llm-council: github.com/karpathy/llm-council (15.4k stars)
- togethercomputer/MoA: github.com/togethercomputer/MoA (2.9k stars)
- microsoft/autogen: github.com/microsoft/autogen
- langchain-ai/langgraph-supervisor-py: github.com/langchain-ai/langgraph-supervisor-py
- composable-models/llm_multiagent_debate: github.com/composable-models/llm_multiagent_debate
- crewAIInc/crewAI: github.com/crewAIInc/crewAI
- openai/swarm: github.com/openai/swarm
- chain-ml/council: github.com/chain-ml/council (846 stars)
- liquidos-ai/AutoAgents: github.com/liquidos-ai/AutoAgents (Rust)

### HackerNews Discussions

- Show HN: Multi-agent deliberation plugin for Claude Code -- news.ycombinator.com/item?id=46737053
- Show HN: Chorus -- news.ycombinator.com/item?id=46191564
- Show HN: AI Council -- news.ycombinator.com/item?id=47095909
- More Agents Is All You Need -- news.ycombinator.com/item?id=39955725
- Don't Build Multi-Agents -- news.ycombinator.com/item?id=45096962

### Technical Analysis

- LLM Council Architecture Analysis -- akillness.github.io/posts/llm-council-complete-architecture-analysis/
- Multi-agent coordination failure modes -- galileo.ai/blog/multi-agent-coordination-strategies
- Token cost in multi-agent systems -- capgemini.com efficient token use article
- Why multi-agent fails in production -- techaheadcorp.com/blog/ways-multi-agent-ai-fails-in-production/
- MAD scaling analysis (ICLR 2025) -- d2jud02ci9yv69.cloudfront.net/2025-04-28-mad-159/blog/mad/

---

## Source Quality Assessment

**Confidence: High** for the architectural patterns and empirical results from peer-reviewed papers (Du et al., ReConcile, D3, Voting-or-Consensus). These have been through formal review and results are reproducible.

**Confidence: High** for the llm-council architecture -- the GitHub repo and community analysis are consistent and the implementation is readable.

**Confidence: Medium** for production cost estimates -- the 5-10x and 15x figures come from different methodologies and may not generalize to every workload.

**Confidence: Medium** for the Rust ecosystem assessment -- this area moves fast and new crates may have emerged after the search cutoff.

**Gaps**: No strong data on council patterns specifically in the context of code generation tasks (vs reasoning/QA benchmarks that dominate the literature). Nancy's use case -- multi-agent deliberation on code review, task decomposition, and spec validation -- is underrepresented in published research.

---

## Open Questions

1. Does the collaborativeness phenomenon (MoA) hold for code generation tasks specifically, or is it specific to text generation benchmarks?

2. What is the right council trigger threshold for Nancy? (e.g., only convene council when agent confidence is below X, or for decisions above a certain estimated impact).

3. How should council decisions be persisted for Nancy's session memory? Is a council decision "stronger" evidence for the git history than a single-agent decision?

4. Can helioy-bus serve as the coordination substrate for council message passing, or does its architecture need extension for the synchronization patterns council requires?

5. What is the appropriate council size for code review tasks? Research suggests diminishing returns after ~10 agents for reasoning, but code review may have different characteristics.

6. Should Nancy implement a "council of models" (different LLM providers) or a "council of roles" (same model with different system prompts/personas)? Research (ReConcile, X-MAS) strongly suggests different model families provide more meaningful diversity than persona variation.

---

## Actionable Takeaways

### For Nancy Council Design

**1. Adopt the three-phase pattern as the default council protocol:**

```
Phase 1: Parallel independent proposals (all council members query simultaneously)
Phase 2: Anonymous peer ranking (alphabetic relabeling, no model identity exposed)
Phase 3: Designated synthesizer aggregates rankings + original responses
```

This is validated by llm-council, AI Council, and implicitly by D3's MORE protocol. It has predictable cost (3 phases, fixed agent count), graceful degradation (continue with successful subset), and is implementable in pure async Rust with helioy-bus as the message substrate.

**2. Use heterogeneous model selection for the council:**
Compose the council from different model families (e.g., Anthropic Claude, Google Gemini, a local Ollama model). Homogeneous ensembles compound shared biases without adding genuine diversity. ReConcile and X-MAS both confirm this is the dominant source of council value.

**3. Match protocol to task type:**

- For reasoning/planning tasks (task decomposition, approach selection): use voting-style aggregation.
- For knowledge/factual tasks (spec validation, requirement confirmation): use consensus protocol.
- For evaluation tasks (code review quality assessment): use adversarial advocate/judge structure (D3 pattern).

**4. Bound rounds aggressively:**
More rounds decrease accuracy. The "Voting or Consensus?" paper found extended rounds cause topic drift. Cap council at 1-2 rounds of peer review maximum. Use convergence detection (when top-2 rankings agree) as early termination.

**5. Implement budgeted stopping with hard token limits:**
Borrow D3's mechanism: define a max token budget per council invocation. If budget exhausted before convergence, proceed with best available synthesis. Make council cost predictable and bounded.

**6. Make council an async background operation in Nancy:**
Council invocations should be non-blocking. Nancy dispatches council request to helioy-bus, continues other work, receives council verdict asynchronously. This is critical given 5-10x latency multiplier.

**7. Persist council decisions distinctly in session history:**
Tag council-derived decisions with metadata (which models participated, confidence scores, round count). This gives the git history a signal about decision reliability and lets future sessions weight council decisions more heavily.

**8. Start with the lightweight pattern, not the sophisticated one:**
Begin with parallel proposals + anonymous ranking + synthesis (llm-council pattern). This is the minimum viable council. Add adversarial advocate/judge (D3 pattern) only if the lighter pattern proves insufficient for specific task types.

**9. Treat the council as a routing decision, not a universal default:**
Research is consistent: council is not universally better. For routine, well-defined tasks with reliable single-agent accuracy, council is pure overhead. Build a council trigger mechanism (confidence threshold, task-type classifier, or explicit human invocation) rather than applying it to every decision.
