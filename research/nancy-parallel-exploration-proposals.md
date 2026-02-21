---
title: "Beyond Greedy Hill Climbing: Parallel Exploration for Autonomous ML Research"
type: research
tags: [nancy, autoresearch, parallel-exploration, orchestration, proposals]
summary: Actionable proposals for extending nancy's orchestrator to support non-greedy, parallel exploration strategies inspired by autoresearch's limitations.
status: active
source: research-synthesizer
confidence: high
created: 2026-03-13
updated: 2026-03-13
---

## Problem Statement

Autoresearch runs a pure greedy hill climber: modify train.py, run 5 minutes, keep if val_bpb improved, discard otherwise. This creates three structural failure modes:

1. **Multi-step improvements are impossible.** If Step A degrades val_bpb by 0.002 but enables Step B to improve it by 0.01, the agent discards Step A and never reaches Step B.
2. **No memory across discards.** Code is `git reset` on failure. The agent can manually grep git history but has no structured access to what was tried, what failed, or why.
3. **No parallel exploration.** One agent, one branch, one experiment at a time. Orthogonal hypotheses ("bigger model" vs "better optimizer") are serialized when they could run concurrently.

Nancy already has the building blocks to address all three: worktrees, file-based IPC, role-tagged issues, and an orchestrator supervision loop. The gap is a coordination protocol that manages multiple workers exploring different branches and synthesizes their results.

## Proposal Structure

Three tiers, ordered by implementation effort. Each tier subsumes the previous one.

---

## Tier 1: Structured Memory + UCB Steering (Single Agent)

**Effort:** 1-2 days. No infrastructure changes.
**Workers:** 1 (existing loop).
**What it solves:** Failure modes #1 (partially) and #2.

### Mechanism

Add a `memory.json` file that the agent maintains alongside `results.tsv`. After each experiment, the agent writes:

```json
{
  "experiment_id": "exp-042",
  "commit": "a1b2c3d",
  "category": "optimizer",
  "subcategory": "lr_schedule",
  "val_bpb": 1.0423,
  "delta_bpb": +0.0012,
  "status": "discard",
  "hypothesis": "Cosine annealing with warm restarts",
  "observation": "Training loss decreased faster but final val_bpb worse, likely overfitting",
  "related_experiments": ["exp-038", "exp-039"],
  "tags": ["lr", "schedule", "cosine"]
}
```

Before proposing the next experiment, the agent reads `memory.json` and computes a UCB-style exploration score per category:

```
score(category) = mean_improvement(category) + sqrt(2 * ln(total_experiments) / count(category))
```

Categories with few experiments get an exploration bonus. Categories with consistent improvements get exploited. The agent biases its next proposal toward the highest-scoring category.

### What changes in program.md

```markdown
After each experiment:
1. Record structured metadata in memory.json (category, hypothesis, observation)
2. Compute UCB scores across experiment categories
3. Bias your next experiment toward the highest-scoring underexplored category
4. If a category has 3+ consecutive failures, deprioritize and note why

Before proposing an experiment:
1. Read memory.json for all past attempts
2. Check if this exact idea (or close variant) was already tried
3. If revisiting a failed category, explain what's different this time
```

### Partial fix for multi-step improvements

Add a "shelved" status alongside "keep" and "discard":

```markdown
If val_bpb worsened by less than 0.005 AND the change is a structural prerequisite
for a follow-up idea, SHELVE the commit instead of discarding:
1. git stash (preserve the code)
2. Record in memory.json with status "shelved" and a note about the intended follow-up
3. After 3 more experiments, revisit shelved changes and attempt the follow-up
```

This allows the agent to tolerate small regressions when it has a theory about why the regression enables a larger improvement.

### Nancy integration

None required. This is purely a `program.md` enhancement. Nancy workers already execute instructions from issue descriptions. The structured memory file lives in the worktree.

---

## Tier 2: Parallel Branch Exploration (Multiple Agents)

**Effort:** 1-2 weeks. Requires nancy orchestrator changes.
**Workers:** 2-4 concurrent agents, each on a separate GPU or time-sliced.
**What it solves:** All three failure modes.

### Mechanism

The orchestrator spawns N workers, each in its own git worktree and branch. Workers run the standard experiment loop independently. Periodically (every K experiments, configurable), the orchestrator runs a **redistribution step**:

1. Read `results.tsv` from all workers.
2. Rank workers by best val_bpb achieved.
3. Bottom 25% of workers: reset to the top worker's current branch tip + apply a random perturbation.
4. Top 25%: continue unmodified.
5. Middle 50%: cherry-pick any modular improvements from the top worker that don't conflict with their current direction.

```
    Worker A (optimizer focus)     Worker B (architecture focus)
    branch: explore/optimizer      branch: explore/architecture
    ┌─────────────────────┐        ┌─────────────────────────┐
    │ exp-01: lr=0.001 ✓  │        │ exp-01: depth=12 ✓      │
    │ exp-02: lr=0.0005 ✗ │        │ exp-02: depth=16 ✗      │
    │ exp-03: warmup=0.1 ✓│        │ exp-03: window=SSLL ✓   │
    └─────────────────────┘        └─────────────────────────┘
              │                              │
              └──────────┬───────────────────┘
                         ▼
                   Orchestrator
              (redistribution step)
                         │
              ┌──────────┴──────────┐
              ▼                     ▼
    Worker A keeps its branch   Worker B cherry-picks
    (best performer)            Worker A's warmup change
                                onto its architecture branch
```

### What nancy needs

**1. Multi-worker spawning.** The orchestrate command needs a `--workers N` flag that creates N tmux panes, each with its own worktree and branch.

```bash
nancy orchestrate ALP-200 --workers 4 --strategy parallel-explore
```

**2. Worker identity.** Each worker gets an ID (worker-0 through worker-N) injected into its prompt. Workers write results to `results-{worker_id}.tsv`.

**3. Redistribution protocol.** A new orchestrator action, triggered on a timer or after K total experiments across all workers:

```bash
nancy redistribute ALP-200 --strategy pbt
```

The redistribution reads all result files, ranks workers, and executes branch operations (cherry-pick, reset, fast-forward). This is a coordinator-only action; workers are paused during redistribution.

**4. Shared result aggregation.** A `results-combined.tsv` that merges all worker results with worker_id as a column. The analysis notebook reads this for a unified view.

**5. Message routing by worker ID.** The existing `comms/` directory structure extends to `comms/worker-0/inbox/`, `comms/worker-1/inbox/`, etc. The orchestrator can send directives to specific workers or broadcast to all.

### Cherry-pick strategy

The key insight: autoresearch experiments are often **modular**. A learning rate change and an architecture change touch different regions of `train.py`. Cherry-picking between branches is tractable when:

- Changes are in different functions or hyperparameter blocks
- The agent maintains clean, atomic commits (one idea per commit)
- Conflicts are rare because workers are assigned orthogonal exploration directions

When changes conflict (two workers both modified the optimizer), the orchestrator picks the version from the better-performing worker.

### Worker specialization via Linear issues

Nancy already supports role tags on issues. Extend this to exploration directions:

```
ALP-200: Autonomous ML Research (parent)
  ALP-201: [explore:optimizer] Optimize learning rate schedules and optimizer config
  ALP-202: [explore:architecture] Explore model depth, width, attention patterns
  ALP-203: [explore:data] Experiment with batch size, sequence length, data packing
  ALP-204: [explore:regularization] Try dropout, weight decay variants, augmentation
```

Each worker picks up one sub-issue and focuses its experiments within that domain. The orchestrator handles cross-pollination during redistribution.

---

## Tier 3: Full Population-Based Training Protocol (Adapted for LLM Agents)

**Effort:** 3-4 weeks. Significant orchestrator rework.
**Workers:** 8-16 concurrent agents.
**What it solves:** All failure modes + discovers hyperparameter schedules (time-varying configs).

### Why PBT matters here

Standard PBT copies both trained weights and hyperparameters from top performers to bottom performers. LLM agents cannot transfer trained weights (each experiment trains from scratch). But they can transfer something more valuable: **code**.

In autoresearch, "weights" are ephemeral (discarded after each 5-minute run), but **the code that produced them persists**. PBT-for-agents transfers the `train.py` configuration from top performers to bottom performers, then mutates it. This is closer to evolutionary search than classical PBT, but retains PBT's key advantage: underperforming agents recover by learning from better agents rather than being permanently stuck.

### Protocol

```
INITIALIZE:
  For i in 0..N-1:
    Create worktree worker-{i} on branch explore/worker-{i}
    If i > 0: Apply random perturbation to train.py hyperparameter block
    Start worker loop

EVERY K EXPERIMENTS (orchestrator checks):
  1. Collect val_bpb from all workers' latest completed experiment
  2. Rank workers by best val_bpb

  EXPLOIT (bottom 25%):
    For each bottom worker b:
      Select random top-25% worker t
      Copy t's current train.py hyperparameter block to b's train.py
      git commit -m "PBT exploit: copied config from worker-{t}"

  EXPLORE (bottom 25%, after exploit):
    For each bottom worker b:
      Mutate 1-3 hyperparameters:
        - Continuous params: multiply by uniform(0.8, 1.2)
        - Discrete params: sample neighbor (depth +/- 1, etc.)
        - Categorical params: resample (activation, window pattern)
      git commit -m "PBT explore: mutated {param_names}"

  CONTINUE:
    Resume all workers

MERGE (every M redistribution cycles):
  1. Identify the globally best worker
  2. Cherry-pick any non-conflicting improvements from other workers
  3. Create a new "best-known" branch at this merged state
  4. Optionally reset all workers to this merged state for a fresh generation
```

### What nancy needs (beyond Tier 2)

**1. Config extraction and injection.** A utility that reads the hyperparameter block from one `train.py` and writes it into another. The block is well-delimited in autoresearch (lines 429-450). This could be:
- A simple sed/awk script for the known format
- An LLM call that reads both files and produces the merged version

**2. Mutation operator.** A function (or LLM prompt) that takes a hyperparameter config and produces a perturbed variant. For continuous params, multiply by a random factor. For discrete/categorical, sample from a predefined neighborhood.

**3. Population state tracking.** A `population.json` maintained by the orchestrator:

```json
{
  "generation": 7,
  "workers": [
    {
      "id": "worker-0",
      "branch": "explore/worker-0",
      "best_bpb": 1.0312,
      "experiments_run": 42,
      "last_exploit_from": null,
      "status": "running"
    },
    {
      "id": "worker-3",
      "branch": "explore/worker-3",
      "best_bpb": 1.0489,
      "experiments_run": 38,
      "last_exploit_from": "worker-0",
      "status": "running"
    }
  ],
  "global_best": { "bpb": 1.0312, "worker": "worker-0", "commit": "f4e5d6c" }
}
```

**4. Generational lifecycle.** The orchestrator manages generations: a generation ends when all workers have completed K experiments. Between generations, exploit/explore/merge steps run. Workers are paused during transitions.

**5. Convergence detection.** If the top 50% of workers are within 0.001 val_bpb of each other for 3 consecutive generations, the population has converged. The orchestrator can:
- Increase mutation magnitude to escape the basin
- Reset half the population to random configs
- Declare convergence and report the best result

### Hardware constraint

Each worker needs a GPU for its 5-minute training run. With 8 workers and 1 GPU, experiments run 8x slower (40 minutes per generation vs 5 minutes). The protocol still works but loses the throughput advantage.

Options:
- Multi-GPU machine (8x H100 = 8 parallel workers)
- Cloud burst (spin up N GPU instances for the experiment session)
- Time-sliced: round-robin workers on 1-2 GPUs, accept slower generations

---

## Comparison Matrix

| Capability | Autoresearch (current) | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|---|
| Memory across experiments | results.tsv only | Structured memory.json + UCB | Per-worker memory + shared aggregation | Population state + generational history |
| Multi-step improvements | Impossible | Shelving mechanism | Cherry-pick across branches | Exploit/explore transfers partial progress |
| Parallel exploration | None | None | 2-4 workers, orthogonal directions | 8-16 workers, population-based |
| Escape local optima | Cannot | UCB biases toward underexplored areas | Workers explore different basins | Mutation + exploit recovers stuck workers |
| Hyperparameter schedules | Fixed config per run | Fixed config per run | Fixed config per run | Emerges from generational evolution |
| Infrastructure cost | 1 GPU, 0 coordination | 1 GPU, 0 coordination | 2-4 GPUs, nancy orchestrator | 8+ GPUs, full population manager |
| Implementation effort | Exists | 1-2 days | 1-2 weeks | 3-4 weeks |

## Recommended Path

**Start with Tier 1 immediately.** Zero infrastructure cost, validates whether structured memory and UCB steering measurably improve experiment quality. Run overnight, compare plateau behavior against vanilla autoresearch.

**Build Tier 2 when Tier 1 plateaus.** The nancy orchestrator changes (multi-worker spawning, redistribution protocol, message routing by worker ID) are independently valuable for any multi-agent workflow, not just autoresearch. This is reusable infrastructure.

**Evaluate Tier 3 based on Tier 2 results.** If 4 parallel workers with cherry-pick redistribution already escape local optima effectively, full PBT may be unnecessary complexity. If workers converge to the same basin despite orthogonal initial directions, PBT's exploit/explore mechanism becomes the differentiator.

## Open Questions

1. **GPU economics.** What's the cost-per-experiment on cloud GPUs? At $2/hr for an H100, 8 workers running overnight (12 hours) costs ~$192. Is the improvement in val_bpb worth this vs running 1 worker for 12 hours?
2. **Cherry-pick reliability.** How often do autoresearch experiments produce clean, modular commits? If most changes touch multiple parts of train.py, cherry-picking becomes fragile and Tier 2's redistribution simplifies to "reset to best branch."
3. **LLM as implicit Bayesian optimizer.** Does an LLM reading memory.json and proposing the next experiment outperform formal TPE? The LLM has priors about ML training dynamics that Optuna lacks. Worth benchmarking.
4. **Convergence timescale.** How many experiments before the greedy loop plateaus? If it's 200+, the overnight window may be sufficient and parallelism is less valuable. If it's 30-50, parallelism pays off quickly.
