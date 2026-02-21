---
title: Non-Greedy Exploration Strategies for autoresearch's Hill-Climbing Loop
type: research
tags: [hyperparameter-optimization, pbt, evolutionary-search, bandit, tpe, bayesian-optimization, autoresearch, autonomous-agents]
summary: Five well-established exploration strategies that address greedy hill climbing's local optima problem, analyzed for tractability with LLM agents as the optimizer.
status: active
source: quick-research
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Summary

autoresearch's current loop is greedy hill climbing on a single linear branch: modify, run, keep if better, discard if worse, repeat. This misses: (a) non-monotonic improvement paths where a temporary regression leads to a better basin, (b) exploiting knowledge from multiple simultaneous experiments, and (c) schedule-based hyperparameter dynamics that are only discoverable when you can compare across parallel runs. Five concrete replacements or augmentations follow.

---

## 1. Population-Based Training (PBT)

**Source**: Jaderberg et al., DeepMind, 2017. arXiv:1711.09846.

### Core Mechanism

Maintain N workers (agents), each training their own model with their own hyperparameters. Periodically (e.g., every fraction of the time budget), each worker evaluates. The bottom 20-25% of workers by performance execute **exploit**: copy the weights AND hyperparameters from a randomly selected top-20% worker's checkpoint. Then immediately execute **explore**: perturb those copied hyperparameters with random noise (multiply by 0.8 or 1.2, or resample from prior). Training resumes from the copied weights, not from scratch.

The key insight is that PBT discovers a **schedule** of hyperparameter settings rather than a fixed set. A worker might start with a high LR, exploit a checkpoint from a worker that happened to use low LR after 3 minutes, then mutate to a medium LR -- discovering a decay schedule that no individual trial would find.

### What it solves that greedy hill climbing misses

- Greedy search finds a fixed configuration; PBT finds a trajectory through hyperparameter space over the course of training.
- Workers that perform worse early can recover by copying better workers. There is no permanent discard.
- Hyperparameter schedules (LR warmup, warmdown, WD decay) emerge naturally without being hand-specified.

### Practical overhead

- **Minimum workers**: 10-20 for the exploit/explore to be meaningful (bottom 20% needs to be at least 2 workers).
- **Communication**: Workers must be able to read each other's checkpoints. A shared filesystem or checkpoint directory suffices. No direct inter-process communication.
- **Synchronization**: Semi-synchronous. Workers run independently; evaluation and exploit/explore happen at fixed wall-clock intervals. Slower workers just skip a round.

### Tractability with LLM agents

**High, with modification.** For autoresearch specifically:
- Replace "copy weights" with "copy the train.py config section from the better agent's current branch."
- Replace "perturb hyperparameters" with the LLM proposing a small mutation to those copied values.
- The exploit operation is a `git diff` + apply; the explore is an LLM edit to the hyperparameter block.
- Multiple agents run on separate git branches (via `git worktree`), each writing to a shared `results.tsv` or separate result files merged by a coordinator.
- Minimum: 4-8 LLM agents. At ~12 experiments/hour per agent, 8 agents = 96 experiments/hour with population dynamics.

---

## 2. Evolutionary Strategies (Tournament Selection + Crossover + Mutation)

**Source**: Genetic algorithms literature; AgileRL framework for RL hyperparameter evolution.

### Core Mechanism

Maintain a population of configurations (chromosomes). Each generation:

1. **Tournament selection**: Sample k configurations at random; the one with the best fitness (lowest val_bpb) wins and becomes a parent. Repeat to get N parents.
2. **Crossover**: Combine two parent configs by randomly selecting each hyperparameter from either parent. E.g., parent A has `lr=0.001, depth=8, batch=512`; parent B has `lr=0.003, depth=12, batch=256`. Offspring might be `lr=0.001, depth=12, batch=256`. In code terms, crossover two train.py configs by taking each parameter stochastically from one or the other parent.
3. **Mutation**: With probability p (e.g., 0.1-0.3), replace a parameter with a sampled value from its prior. Common mutations: scale by 0.8 or 1.2, swap activation function, add/remove a layer, change optimizer parameter.
4. Replace the bottom half of the population with the newly generated offspring.

Unlike PBT, evolutionary strategies do NOT transfer trained weights -- offspring start training from scratch with a new configuration. This is more expensive (no warm start) but handles discontinuous search spaces (e.g., changing architecture depth) where weight transfer is invalid.

### What it solves

- Crossover explores combinations that neither parent has tried -- it is combinatorial exploration, not just local perturbation.
- Tournament selection maintains diversity by not always selecting the single global best.
- Handles discrete search spaces (architecture topology) naturally where gradient-based methods fail.

### Practical overhead

- **Population size**: 10-50. Smaller populations converge faster but have less diversity.
- **Generations**: Each generation requires N full training runs. With 5-minute runs, a generation of 10 = 50 minutes. Feasible overnight.
- **Communication**: None during training. Coordinator reads all results after each generation and selects parents.
- **Workers needed**: One per population member if running in parallel, or one serialized if sequential.

### Tractability with LLM agents

**High for mutation, moderate for crossover.** The LLM can:
- Implement mutation naturally (it already proposes hyperparameter changes).
- Implement tournament selection by reading results.tsv and picking the winner from a random sample.
- Implement crossover by reading two parent train.py files and interleaving parameters.

The challenge is that crossover requires two parent train.py files to be semantically aligned. If agents have diverged in code structure significantly, crossover becomes code merging, which is harder. Constraint: keep train.py modifications to a clearly delimited "hyperparameter block" and "architecture block" to make crossover tractable.

---

## 3. Multi-Armed Bandit: UCB and Thompson Sampling / Hyperband

**Source**: Hyperband (Li et al., 2018, JMLR v18); UCB and Thompson Sampling literature.

### Core Mechanism

**Framing**: Treat each hyperparameter configuration as an "arm." Pulling the arm = running a 5-minute experiment. Reward = negative val_bpb (higher is better for the bandit framing). The problem: you have a budget of M experiments and want to maximize total reward.

**UCB (Upper Confidence Bound)**: For each arm i, compute score = mean_reward_i + sqrt(2 * ln(total_pulls) / pulls_i). Always pull the arm with the highest score. The second term is an exploration bonus that shrinks as you pull an arm more. Naturally balances exploitation (high mean) with exploration (uncertainty due to few pulls).

**Thompson Sampling**: Maintain a Beta(alpha_i, beta_i) distribution over each arm's reward probability. At each step, sample one value from each arm's distribution. Pull the arm with the highest sample. Update the distribution with the observed reward. This is Bayesian: arms with high uncertainty get sampled from their distribution more variably, which gives them a chance to win.

**Hyperband**: Combines bandit logic with Successive Halving. Start with n configurations, each given r_min resources (e.g., 1 minute of training). Keep the top 1/eta fraction, give them eta times more resources. Repeat. This runs multiple brackets with different (n, r_min) tradeoffs simultaneously, eliminating the need to choose between "many short runs" vs "few long runs" -- you run both.

For autoresearch: one "pull" = 5-minute run, which is an indivisible unit (the time budget is fixed). Pure Hyperband requires fractional budgets, so it does not directly apply. However, Successive Halving applied over multiple rounds (early stopping via a shorter TIME_BUDGET in prepare.py) would be needed to fully implement it.

### What it solves

- UCB/Thompson: Tells you WHICH of a predefined set of configurations to try next given results so far. Better than random search because it is optimistic -- it preferentially re-runs configurations that looked promising but have high uncertainty.
- Hyperband: Eliminates bad configurations early so budget concentrates on promising ones. Gets results ~5x faster than random search in equivalent budget.

### Practical overhead

- **UCB/Thompson with fixed arms**: Requires predefined arm set (configuration library). Coordinator reads results after each experiment, updates statistics, selects next arm. Single worker is sufficient.
- **Hyperband**: Needs at least eta=3 workers for meaningful parallel successive halving. With sequential runs, it degenerates to one-at-a-time elimination which still works but loses parallelism.
- **Communication**: Coordinator-only. Workers just report val_bpb; coordinator decides next experiment.

### Tractability with LLM agents

**Very high for the coordinator role.** The LLM can:
- Maintain a results.tsv with past experiments.
- Compute UCB scores explicitly (the math is simple).
- Select next experiment as the config with highest UCB score.
- Propose a set of K candidate configurations upfront (arm library), then have the bandit select among them.

The key limitation: bandit assumes a fixed arm set. It cannot propose genuinely novel configurations not in the initial set. Pairing bandit selection with an LLM that proposes new arms when all existing ones have low uncertainty would be a natural hybrid.

---

## 4. Tree-Structured Parzen Estimators (TPE) / Bayesian Optimization

**Source**: Bergstra et al., 2011 (NeurIPS). Implemented in Hyperopt and Optuna.

### Core Mechanism

After k experiments, TPE builds two kernel density estimates from the results:
- **l(x)**: density over hyperparameter configs that achieved val_bpb below the gamma-th percentile (the "good" configs). Built as a mixture of Gaussians centered on each observation in this set.
- **g(x)**: density over configs above the gamma-th percentile (the "bad" configs). Same construction.

To propose the next config, TPE samples N candidates from l(x) and selects the one that maximizes **l(x) / g(x)** -- the expected improvement ratio. This favors candidates that are likely under the good distribution and unlikely under the bad distribution.

The "tree-structured" part refers to handling hierarchical hyperparameter spaces (e.g., "if optimizer=Adam, then tune beta1 and beta2; if optimizer=Muon, those params don't exist"). Each conditional is a separate tree node with its own density estimates.

Typical gamma values: 0.15-0.25 (top 15-25% are "good").

### What it solves

- After each experiment, the model of the search space improves. Early experiments are exploratory; later experiments concentrate on high-EI regions.
- Handles dependencies between hyperparameters (tree structure) that grid search and random search ignore.
- Requires no parallel workers: this is fundamentally a sequential algorithm that improves with more observations.
- Has well-characterized convergence: outperforms random search after ~15-20 observations, strongly outperforms after 50+.

### Practical overhead

- **Workers**: 1. This is sequential by design.
- **Communication**: None. Just a growing list of (config, val_bpb) observations.
- **Computational cost**: Density estimation is O(n^2) in number of observations but n is small (hundreds of experiments overnight). Negligible vs 5-minute training runs.
- **Implementation**: Optuna (Python) implements TPE natively. One call to `study.ask()` returns the next config; `study.tell(trial, val_bpb)` records the result.

### Tractability with LLM agents

**Moderate.** There are two viable approaches:

1. **Delegated to Optuna**: The LLM calls Optuna's TPE sampler for a specific hyperparameter space (defined by bounds on lr, depth, batch_size, etc.). Optuna returns a concrete config; the LLM applies it to train.py. Clean separation of search logic from implementation.

2. **LLM as implicit TPE**: The LLM reads all past results and proposes the next config. LLMs have implicit "common sense" priors about training dynamics (e.g., "LR usually needs to be in 1e-4 to 1e-2 range") that are roughly equivalent to a prior distribution. This has been noted in the HPO literature as actually competitive with formal TPE for small-n regimes. No infrastructure needed.

The challenge with formal TPE: the search space must be pre-specified with explicit parameter bounds. Architectures are partially discrete (depth, window pattern), partially continuous (lr, WD), partially categorical (activation function). Defining this space upfront requires knowing what parameters are in scope, which reduces the LLM's flexibility to explore novel ideas.

---

## 5. Git-Based Branching for Parallel Exploration

**Source**: Git worktree documentation; agent workflow patterns; lakeFS branching for ML; DVC experiments.

### Core Mechanism

Use `git worktree` to create N independent working directories, each on their own branch, sharing the same `.git` object store. Each agent/worker:
1. Gets its own branch: `git worktree add ../autoresearch-agent-N autoresearch/mar5-agentN`
2. Runs its own experiment loop independently, committing to its own branch.
3. Writes results to a shared `results.tsv` or per-agent result file.

A coordinator (human or a separate LLM agent) periodically:
1. Reads all branch tips.
2. Identifies the best-performing branch by val_bpb.
3. Optionally: cherry-picks specific commits from other branches onto the best branch (if the changes are modular and composable).
4. Optionally: creates a new branch from the best branch's tip and distributes it to all agents as their new starting point (PBT-style exploit).

For a pure exploration tree: treat the git DAG as the search tree. Each node is a commit (one experiment). Branching = exploring a different direction from a shared ancestor. Merging = combining two independently discovered improvements.

**Prior art**: DVC Experiments (branches per experiment, comparison tooling), lakeFS (metadata-pointer branching for zero-copy dataset isolation), and the AgileRL framework all follow this pattern. The autoresearch program.md already uses one branch per run; the extension is running multiple branches in parallel.

### What it solves

- Enables parallel exploration of orthogonal hypotheses simultaneously (e.g., "try larger model" vs "try better optimizer" vs "try different attention pattern").
- The git history becomes an experiment tree, not a linear sequence. The best path can be reconstructed by cherry-picking.
- Separate branches = no interference between agents modifying train.py simultaneously.

### Merge strategies

| Strategy | When to use |
|---|---|
| Cherry-pick best commit | When the improvement is modular (e.g., a specific hyperparameter change independent of others) |
| Fast-forward best branch | When one branch dominates across the board |
| Manual review at sync point | When changes conflict but are complementary |
| New branch from best tip + redistribute | PBT-style: periodically reset all agents to the current best, then diverge again |

### Practical overhead

- **Workers**: N (one per worktree). Overhead per worker is disk space (shared objects, minimal) + one GPU.
- **Communication**: Shared filesystem for `results.tsv` or per-agent result files. Coordinator wakes up periodically to read results and trigger redistributions.
- **Complexity**: Low for pure parallel exploration (no coordination). Higher if implementing PBT-style periodic redistribution.

### Tractability with LLM agents

**High.** The autoresearch program.md already uses git branches. Extending to multiple worktrees:
- Each agent needs its working directory and branch name.
- A coordinator agent (or the human) runs `git log --all --oneline` + `grep val_bpb` to build a picture of the experiment tree.
- Cherry-picking specific changes between branches is something LLMs can do (read diff, apply to another branch, resolve conflicts).

The missing piece is a coordinator protocol: who decides when to redistribute, which branch to favor, and how to handle conflicting improvements. This is exactly the kind of logic that belongs in an updated `program.md`.

---

## Comparison Table

| Strategy | Parallel workers needed | Communication overhead | Handles non-monotonic paths | LLM tractability | Best for autoresearch |
|---|---|---|---|---|---|
| PBT | 10-20 | Checkpoint sharing | Yes (weight transfer) | High | High (weight copy becomes config copy) |
| Evolutionary | 10-50 | Result broadcast | Yes (crossover recombines) | High | High (but crossover needs structured config) |
| UCB/Thompson | 1 (sequential) | None | No | Very high | High as coordinator logic |
| Hyperband | 3-5 | None | No | High (with Optuna) | Moderate (needs fractional budget) |
| TPE | 1 (sequential) | None | No | High (delegate to Optuna or implicit) | High (best with structured param space) |
| Git branching | N (1 per GPU) | Shared FS | Yes (via cherry-pick) | High | High (direct fit to current architecture) |

---

## Recommendations for autoresearch

### Lowest effort, high return: UCB coordinator

Add to `program.md`: before proposing the next experiment, compute UCB scores over the last N experiments, categorized by type (lr experiments, depth experiments, optimizer experiments, attention experiments). Preferentially propose the type with highest UCB score. This is 10 lines of logic added to the existing loop, no infrastructure change.

### Medium effort: Git worktree parallel branches

Run 2-4 agents on separate worktrees. Each runs the existing loop independently. Add a nightly coordinator step: find the branch with best val_bpb, cherry-pick any modular improvements from other branches. This fits the existing autoresearch architecture cleanly.

### Higher effort, highest ceiling: PBT-style redistribution

Implement exploit/explore in `program.md`: every K experiments, each agent reads all other agents' current val_bpb from a shared file. Bottom 25% agents copy the train.py hyperparameter block from a top-25% agent, then mutate it. This is PBT adapted to LLM agents where "weights" = hyperparameter state in a config block, not trained model weights.

---

## Sources

- [Population Based Training of Neural Networks (arXiv:1711.09846)](https://arxiv.org/abs/1711.09846)
- [DeepMind PBT Blog Post](https://deepmind.google/discover/blog/population-based-training-of-neural-networks/)
- [Hyperband: A Novel Bandit-Based Approach to Hyperparameter Optimization (JMLR 2018)](https://jmlr.org/papers/volume18/16-558/16-558.pdf)
- [Algorithms for Hyper-Parameter Optimization, Bergstra et al. 2011 (TPE)](http://papers.neurips.cc/paper/4443-algorithms-for-hyper-parameter-optimization.pdf)
- [AgileRL Evolutionary Hyperparameter Optimization](https://docs.agilerl.com/en/latest/evo_hyperparam_opt/index.html)
- [Optuna TPE Tutorial](https://hub.optuna.org/samplers/tpe_tutorial/)
- [Git Worktrees for Parallel Agent Workflows](https://elchemista.com/en/post/how-to-leverage-git-trees-for-parallel-agent-workflows)
- [lakeFS Iterative Fine-Tuning and Parallel Experiments](https://lakefs.io/blog/iterative-fine-tuning/)

## Open Questions

1. For PBT adapted to LLM agents: does copying hyperparameters without copying weights provide meaningful signal? The value of PBT's exploit is that you get a warm-started model, not just its hyperparameters. An LLM agent copying only the config gets the configuration but starts training from scratch -- this is closer to evolutionary search than true PBT.
2. What is the right "periodicity" for PBT exploit in the autoresearch context? With 5-minute indivisible runs, the natural checkpoint is after each run. But the bottom 25% threshold requires at least 4 agents.
3. Can the LLM propose a structured hyperparameter space (for TPE/Optuna) that still allows architectural exploration? Architectural changes (depth, window pattern, activation) are discrete and change code structure, not just values. TPE's tree structure handles this in theory but requires upfront space definition.
