---
title: Autonomous LLM Research Loop - autoresearch (Karpathy)
type: research
tags: [ml-training, autonomous-agents, pytorch, optimizer, gpt, research-automation]
summary: Karpathy's autoresearch is a 1,017-LOC autonomous LLM research setup where an AI agent iterates on a GPT training script in 5-minute experiments, keeping improvements and discarding regressions.
status: active
source: codebase-analyst
confidence: high
created: 2026-03-11
updated: 2026-03-11
---

## Executive Summary

autoresearch is Andrej Karpathy's experiment in autonomous ML research. The core idea: give an AI coding agent a small but real GPT training setup, let it modify hyperparameters and architecture freely, train for 5 minutes per experiment, and keep or discard changes based on a single metric (validation bits per byte). The human writes the agent instructions in `program.md`; the agent owns the code. Two Python files, 1,017 LOC total. Derived from [nanochat](https://github.com/karpathy/nanochat), simplified to single-GPU, single-file.

## Project Metadata

| Field | Value |
|---|---|
| Language | Python 3.10 |
| Framework | PyTorch 2.9.1 (CUDA 12.8) |
| Package manager | uv |
| Total LOC | 1,017 (629 train.py + 388 prepare.py) |
| Dependencies | torch, kernels (FA3), rustbpe, tiktoken, pyarrow, requests, matplotlib, pandas, numpy |
| Hardware target | Single NVIDIA GPU (optimized for H100) |
| License | MIT |

## Architecture

The project has exactly three functional artifacts:

```
prepare.py   (388 LOC)  Read-only infrastructure: data download, BPE tokenizer training,
                         dataloader, evaluation metric. The agent never touches this.

train.py     (629 LOC)  The entire research surface: GPT model definition, Muon+AdamW
                         optimizer, training loop, all hyperparameters. The agent modifies
                         only this file.

program.md   (114 lines) Agent instructions. The human's "code" -- defines the research
                         protocol, experiment loop, logging format, constraints.
```

Supporting files: `analysis.ipynb` (experiment result visualization), `pyproject.toml`, `progress.png`.

### Separation of Concerns

The architecture enforces a clean boundary: `prepare.py` owns the evaluation metric and data pipeline (immutable ground truth), while `train.py` is the agent's sandbox. This prevents the agent from gaming the metric or modifying the data pipeline. The fixed 5-minute wall-clock budget (`TIME_BUDGET = 300`) makes every experiment directly comparable regardless of what the agent changes.

## Key Components

### 1. GPT Model (`train.py:123-290`)

A modern GPT implementation with several notable features beyond vanilla transformers:

- **Value Embeddings (ResFormer)**: Alternating layers get a separate `nn.Embedding` that feeds into the value path with a learned per-head gate. The gate uses a narrow projection (32 channels from input) through sigmoid, scaled by 2 so initialization at zero gives neutral (1.0) gating. See `has_ve()` at line 46 and `CausalSelfAttention.forward()` lines 82-86.

- **Residual stream with x0 skip**: The forward pass maintains both a running residual `x` and the original embedding `x0`, mixing them per-layer with learned scalars: `x = resid_lambda[i] * x + x0_lambda[i] * x0` (line 276). Initialized at `resid=1.0, x0=0.1`.

- **Sliding window attention**: Configurable pattern string (default `"SSSL"`) where S = half-context window and L = full context. Last layer always uses full context. Implemented via Flash Attention 3's `window_size` parameter (line 92).

- **RoPE**: Standard rotary position embeddings, precomputed at 10x sequence length.

- **RMS Norm everywhere**: Applied as `F.rms_norm` before attention and MLP (pre-norm), plus on Q and K after projection (QK-norm), plus on initial embedding and before the LM head.

- **Squared ReLU activation**: `F.relu(x).square()` in the MLP (line 106). Simpler than SwiGLU, reportedly competitive.

- **Logit softcapping**: `15 * tanh(logits / 15)` before the loss (lines 281-284). Prevents logit explosion.

- **Model sizing from depth**: A single `DEPTH` parameter controls the entire model. Width = `DEPTH * ASPECT_RATIO` (default 64), rounded up to the nearest `HEAD_DIM` (128). So depth=8 gives dim=512, 4 heads. This is a thoughtful design that lets the agent search a 1D model size space.

### 2. Muon + AdamW Optimizer (`train.py:355-425`)

A hybrid optimizer that applies different algorithms based on parameter shape:

- **Muon** for 2D matrix parameters (transformer weights): Uses Nesterov momentum followed by "polar express" orthogonalization (Newton-Schulz iterations with precomputed polynomial coefficients, lines 296-301). Then NorMuon variance reduction with a second momentum buffer. Finally, cautious weight decay where decay only applies when `grad * param >= 0` (line 351).

- **AdamW** for everything else (embeddings, scalars, biases): Standard implementation with bias correction.

Both optimizer steps are `@torch.compile(dynamic=False, fullgraph=True)` for kernel fusion.

Key implementation detail: Muon groups parameters by shape and stacks them into a single tensor for batched processing (lines 407-408). This avoids per-parameter kernel launches.

CPU 0-D tensors are used for hyperparameters (`_adamw_lr_t`, etc., lines 361-370) to prevent `torch.compile` recompilation when schedule values change across steps.

### 3. Data Pipeline (`prepare.py`)

- **Data source**: `karpathy/climbmix-400b-shuffle` on HuggingFace, downloaded as Parquet shards.
- **Tokenizer**: BPE trained with `rustbpe` (Rust-based), wrapped in tiktoken encoding. Vocab size 8192, GPT-4 style split pattern. Serialized as pickle.
- **Dataloader** (`make_dataloader`, lines 275-336): BOS-aligned with best-fit packing. Every row starts with BOS. Documents packed greedily: find largest document that fits remaining space, crop shortest if none fits. Claims 100% utilization (no padding). Uses pinned memory + async GPU transfer.
- **Evaluation metric**: Bits per byte (BPB). Vocab-size-independent, so architectural changes that alter vocab size remain comparable. Sums per-token cross-entropy in nats, divides by total bytes, converts to bits. Special tokens excluded.

### 4. Agent Protocol (`program.md`)

The experiment loop:

1. Establish baseline (run unmodified train.py)
2. Edit train.py with an idea
3. Git commit
4. Run `uv run train.py > run.log 2>&1`
5. Extract val_bpb from log
6. If improved: keep commit, advance branch
7. If worse: `git reset` to previous state
8. Log to `results.tsv` (untracked)
9. Repeat forever

Constraints: no new packages, no modifying prepare.py, no modifying evaluation, no pausing to ask the human. The agent runs autonomously until manually stopped. Expected throughput: ~12 experiments/hour, ~100 overnight.

## Patterns and Conventions

### "Program the Programmer" Pattern

The human writes Markdown instructions (`program.md`) that define the agent's research protocol. The agent writes Python. This inverts the typical human-writes-code workflow. The README calls program.md a "super lightweight skill" -- essentially a prompt that encodes a research methodology. The observation is that iterating on the *instructions* (what to try, when to keep/discard, how to log) is itself a form of meta-research.

### Single-Knob Model Scaling

Model size is controlled by a single integer (`DEPTH`). Everything else derives from it: width = depth * 64, heads = width / 128. This collapses a multi-dimensional hyperparameter search into 1D, giving the agent a tractable search space while preserving reasonable aspect ratios.

### Time-Budget Normalization

Training always runs for exactly 300 seconds of wall-clock time (excluding the first 10 warmup steps, which cover torch.compile compilation). This means the metric captures compute-efficiency: a larger model that trains fewer steps competes fairly against a smaller model that trains more steps. The downside is results are not comparable across different hardware.

### LR Scaling by Model Dimension

Learning rates are scaled by `(model_dim / 768)^{-0.5}` (line 247). This accounts for the fact that wider models need smaller learning rates, and means the hyperparameters were tuned at dim=768 and automatically adjust when the agent changes model size.

### Cautious Weight Decay

Weight decay is only applied where gradient and parameter agree in sign: `mask = (g * params) >= 0` (line 351). This prevents decay from fighting the gradient direction. Combined with a linear decay schedule: `weight_decay * (1 - progress)`.

### GC Management for Training Stability

Python's garbage collector is explicitly managed (lines 592-597): collect once after step 0, then freeze and disable. Periodic collection every 5000 steps. This avoids ~500ms GC stalls during training.

### Compile-Friendly Optimizer

Both `adamw_step_fused` and `muon_step_fused` use `@torch.compile(dynamic=False, fullgraph=True)`. Hyperparameters are passed via 0-D CPU tensors (updated in-place with `.fill_()`) rather than as Python scalars, preventing recompilation when learning rate schedules change.

## Data Flow (End-to-End)

```
HuggingFace (Parquet shards)
  |
  v  [prepare.py: download_data]
~/.cache/autoresearch/data/shard_*.parquet
  |
  v  [prepare.py: train_tokenizer]
~/.cache/autoresearch/tokenizer/tokenizer.pkl + token_bytes.pt
  |
  v  [prepare.py: make_dataloader]
Best-fit packed batches [B, T+1] -> inputs [B, T], targets [B, T]
  |  (pinned CPU memory -> async GPU copy)
  v
GPT.forward(x, targets)
  |
  |  Embedding -> norm -> N x (residual mix + Block(attn + mlp)) -> norm -> lm_head -> softcap
  v
Cross-entropy loss
  |
  v  [gradient accumulation over micro-steps]
MuonAdamW.step()
  |  (Muon for matrices, AdamW for embeddings/scalars)
  v
LR/momentum/WD schedules (time-based, not step-based)
  |
  v  [after TIME_BUDGET seconds]
evaluate_bpb() -> final val_bpb metric
```

## Interesting Implementation Details

1. **Flash Attention 3 with hardware detection** (lines 20-23): Checks CUDA capability; uses `varunneal/flash-attention-3` on Hopper (sm_90), falls back to `kernels-community/flash-attn3` on other architectures. Loaded via the `kernels` package's `get_kernel()` JIT mechanism.

2. **Polar Express orthogonalization**: The Muon optimizer orthogonalizes gradients using Newton-Schulz iterations with precomputed polynomial coefficients (lines 296-301). Handles tall vs wide matrices differently (lines 325-334), always multiplying the smaller dimension to minimize FLOPs.

3. **Meta-init pattern** (lines 481-484): Model is created on `torch.device("meta")` (no memory allocated), then `to_empty(device=device)` materializes on GPU, then `init_weights()` fills values. This avoids a CPU-to-GPU copy of the initialized weights.

4. **Epoch tracking through the generator**: The dataloader yields `(inputs, targets, epoch)` where epoch increments when training data wraps around. Threaded through the entire training loop for logging.

5. **Analysis notebook**: `analysis.ipynb` reads `results.tsv` and generates a progress chart showing kept vs discarded experiments, running minimum BPB, and per-experiment annotations. This is the human's view into what happened overnight.

## Limitations and Trade-offs

1. **NVIDIA-only**: Requires CUDA GPU. Flash Attention 3 is the hard dependency. The README acknowledges this and points to community forks for MPS/CPU.

2. **Single GPU**: No distributed training. Deliberate simplification for the autonomous agent use case. The entire codebase fits in one file.

3. **Non-portable results**: Because training time is wall-clock, results on an H100 are not comparable to an RTX 4090. The metric measures "best model your hardware can produce in 5 minutes."

4. **No checkpointing or resumption**: Each experiment starts from scratch. If the agent crashes mid-loop, all in-flight work is lost (though the git branch preserves kept results).

5. **Sequential experiments only**: One experiment at a time. No parallel exploration, no population-based training. The program.md could be extended for multi-agent setups but the current design is single-threaded.

6. **Agent-dependent quality**: The quality of results depends entirely on the AI agent's ability to propose good modifications. The program.md is "intentionally kept as a bare bones baseline" -- the meta-research of writing better agent instructions is left to the user.

7. **Greedy hill climbing**: The keep/discard protocol is strictly greedy. There is no mechanism for the agent to backtrack multiple steps, explore orthogonal directions, or maintain a Pareto frontier of competing approaches.

## Dependencies

| Package | Purpose |
|---|---|
| `torch==2.9.1` | Core framework, CUDA 12.8 wheels |
| `kernels>=0.11.7` | JIT Flash Attention 3 kernel loading |
| `rustbpe>=0.1.0` | Fast BPE tokenizer training (Rust) |
| `tiktoken>=0.11.0` | Tokenizer runtime (wraps rustbpe output) |
| `pyarrow>=21.0.0` | Parquet file reading for training data |
| `requests>=2.32.0` | Data shard download |
| `matplotlib`, `pandas`, `numpy` | Analysis notebook |

## Relevance to Helioy

The `program.md` pattern is directly relevant to nancy/nancyr agent orchestration. It demonstrates a minimal viable "skill" format: a Markdown file that encodes a complete autonomous research protocol. The experiment loop (modify, run, evaluate, keep/discard, log) maps naturally to a nancy worker pattern. The key insight is that the human's leverage comes from programming the agent's *methodology*, not the code itself.

The analysis.ipynb pattern (post-hoc visualization of autonomous agent results) could inform how nancy surfaces agent work products to humans.

## Open Questions

1. How does the agent's exploration strategy evolve over many runs? Does it converge to local optima, or does it find genuinely novel architectures?
2. What does an optimized `program.md` look like? The README hints that iterating on the instructions is the real research, but no advanced examples are provided.
3. Could multiple agents explore different branches simultaneously and merge the best results? The git branch structure supports this but the protocol does not.
4. What is the practical ceiling for 5-minute training improvement over baseline? How much of the gain comes from hyperparameter tuning vs architectural changes?
