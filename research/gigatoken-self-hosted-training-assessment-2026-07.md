# GigaToken assessment for Helioy self hosted training

**Date:** 2026-07-23  
**Status:** Research assessment  
**Source:** [marcelroed/gigatoken](https://github.com/marcelroed/gigatoken) at commit [`542367a`](https://github.com/marcelroed/gigatoken/commit/542367a3efed134883fb4f1140b49c04e6fad3a3)

## Executive conclusion

GigaToken is a credible candidate for Helioy's future offline training data pipeline. It should remain outside Transport Matters, Markdown Matters, and shared runtime infrastructure until a measured tokenization workload justifies adoption.

The useful boundary is narrow:

> Convert a large, finalized text corpus into exact model specific token IDs before self hosted training.

GigaToken accelerates this conversion. It does not reduce prompt tokens, extend context windows, compress agent state, improve retrieval, or lower provider billing.

The recommended action is a bounded training data preparation spike when Helioy has a representative corpus of at least 10 GB and a selected base model. No production dependency is warranted before then.

## What GigaToken does

GigaToken is a Rust tokenizer exposed primarily through Python. It implements BPE tokenization with:

- SIMD optimized pretokenization
- Parallel file and batch processing
- Persistent caches for previously encoded text fragments
- Hugging Face compatibility
- Tiktoken compatibility
- Direct loading of supported Hugging Face model tokenizers
- Text, JSONL, and Parquet oriented input paths

Its native API minimizes Python interaction and reads files directly in Rust. This is the path behind the largest performance claims. Compatibility adapters trade some throughput for easier adoption.

The project reports throughput between roughly 1 GB/s and 25 GB/s across modern ARM and x86 systems, depending on tokenizer and hardware. Reported gains over Hugging Face range from roughly 10 times to more than 1,000 times. The tiktoken comparisons range from roughly 50 times to 681 times in the published benchmark. These measurements use an 11.9 GB OpenWebText corpus and should be treated as workload specific. See the [benchmark and methodology](https://github.com/marcelroed/gigatoken#benchmarks).

## Relevant use cases

### Strong fit

1. **Pretraining corpus preparation**

   Tokenize hundreds of gigabytes or terabytes once, then persist packed token shards for repeated training runs.

2. **Continued pretraining**

   Apply the exact tokenizer of a selected base model to a domain corpus before continued training.

3. **Large scale supervised fine tuning**

   Preprocess very large instruction, code, or multimodal text datasets when tokenization becomes a material part of pipeline time.

4. **Training data experiments**

   Retokenize the same corpus for several candidate base models and compare compression ratio, sequence utilization, and training cost.

5. **High volume local inference**

   Reduce tokenizer CPU use when a self hosted model server handles enough concurrent requests for tokenization to limit throughput.

### Weak fit

- Normal hosted API calls
- Agent prompt assembly
- Context compaction
- Provider billing estimates
- Small fine tuning datasets
- Interactive document search
- Workloads dominated by embedding or model inference

## Proposed Helioy training boundary

```text
Source repositories and documents
             |
             v
Extract, normalize, license filter, deduplicate
             |
             v
Freeze a versioned training corpus
             |
             v
GigaToken with the selected model tokenizer
             |
             v
Pack fixed length sequences and write durable shards
             |
             v
Self hosted trainer
```

This keeps responsibilities clean:

- Markdown Matters may help discover, parse, and structure Markdown content.
- A training data component owns filtering, licensing, deduplication, corpus versioning, sequence packing, and shard manifests.
- GigaToken performs model specific tokenization inside that component.
- The trainer consumes immutable token shards and never depends on live document parsing.

GigaToken should be an implementation detail of the training data component. It should not become a general Helioy token service.

## Value by current Helioy surface

| Surface | Current value | Reason |
|---|---:|---|
| Self hosted training pipeline | High potential | Bulk, exact tokenization is a direct prerequisite for durable training shards. |
| Continued pretraining | High potential | Retokenizing a large domain corpus can become a meaningful preprocessing cost. |
| Large supervised fine tuning | Conditional | Valuable when datasets reach many gigabytes. Small datasets do not justify integration. |
| Transport Matters | None | Transport uses Anthropic's authoritative count endpoint and needs provider specific request semantics. |
| Markdown Matters | Negligible | Production paths use a cheap synchronous token approximation. The exact tiktoken helper has no current non test production callers. |
| MDM semantic indexing | Negligible | Parsing, embeddings, persistence, retrieval, reranking, and synthesis dominate this workflow. |
| Agent context management | None | Faster token ID generation does not improve retrieval or compaction quality. |

Relevant current code:

- [Transport Matters authoritative token counting](/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/api/src/transport_matters/counting.py)
- [Markdown Matters token utilities](/Users/alphab/Dev/LLM/DEV/helioy/markdown-matters/src/utils/tokens.ts)

## Local smoke test

A local comparison used the 127 tracked Markdown files in Markdown Matters:

| Measurement | Result |
|---|---:|
| Input size | 2.25 MB |
| GPT2 token count | 739,851 |
| Exact per document parity | Passed |
| Initial GigaToken call | About 119 ms |
| Initial tiktoken call | About 58 ms |
| Warm GigaToken call | About 5 ms |
| Warm tiktoken call | About 53 ms |

The warm cache advantage was clear. The absolute saving was about 50 ms across the entire tracked Markdown corpus. This workload is too small to justify integration and demonstrates why adoption must follow profiling.

The test also exposed a maturity issue. The documented `Tokenizer(tiktoken.Encoding)` constructor failed with a `TypeError` in version 0.9.0. Loading the equivalent Hugging Face GPT2 tokenizer worked and produced exact counts.

## Adoption risks

### Young public API

Version 0.9.0 was published on 2026-07-21 and is classified as beta. The rapid release cadence indicates that the public surface is still settling. See [PyPI release history](https://pypi.org/project/gigatoken/).

### Python first integration

Python is the supported public surface. There is no Node binding. The Rust core is not yet published as a versioned crate with a documented minimum Rust version. See [issue 30](https://github.com/marcelroed/gigatoken/issues/30).

### Output and shard writing

The native API produces token arrays, but file sinks are listed as unfinished. Helioy would still need a deliberate sequence packer, shard writer, manifest, integrity checks, and resume semantics.

### Service memory bounds

GigaToken retains worker tokenizers and their pretoken caches for the tokenizer lifetime. The caches grow as new text fragments appear. This is useful for offline throughput, but risky for an unbounded long lived service. A bounded concurrent count API remains an open request. See [issue 29](https://github.com/marcelroed/gigatoken/issues/29).

### Exact special token behavior

An open issue reports incorrect special token IDs when loading raw `o200k_base` ranks through the generic tiktoken loader. Training data corruption at this boundary would be unacceptable. See [issue 31](https://github.com/marcelroed/gigatoken/issues/31).

### Tokenizer coverage

WordPiece is unsupported. SentencePiece tokenizers receive smaller gains. The target model must be selected before the performance case can be judged.

## Recommended pilot

Run a spike only after these inputs exist:

1. A selected base model and immutable tokenizer revision.
2. A representative corpus of at least 10 GB.
3. A proposed sequence length and packing policy.
4. A defined output shard format.
5. A baseline implementation using the model's canonical tokenizer.

### Benchmark matrix

Measure GigaToken against the canonical tokenizer on:

- 10 GB representative corpus
- 100 GB projected corpus, if available
- Cold process
- Warm process
- Native file API
- Compatibility API
- Production CPU architecture

Record:

- Input bytes per second
- Tokens per second
- Wall time
- CPU time
- Peak resident memory
- Cache growth over time
- Output allocation size
- Shard writing throughput
- Total pipeline throughput

### Correctness gate

Performance is irrelevant without exact output parity. The pilot must:

1. Compare every token ID for a diverse deterministic sample.
2. Include all special tokens used by the trainer.
3. Include code, Markdown, JSON, Unicode, CJK text, emoji, invalid UTF-8 policy, long repeated strings, and very long documents.
4. Compare packed sequences and attention boundaries, not only raw counts.
5. Decode sampled token streams through the canonical tokenizer and verify round trips where supported.
6. Pin the tokenizer files, GigaToken version, corpus revision, and benchmark code.

Any mismatch blocks adoption.

### Memory gate

For offline jobs, set a process memory ceiling and measure cache behavior across heterogeneous shards. Prefer a fresh process per bounded corpus partition if retained caches cause unpredictable growth.

### Integration shape

Prefer a standalone Python data preparation command with explicit inputs and immutable outputs:

```text
training-corpus prepare
  --corpus manifest.json
  --tokenizer <pinned model revision>
  --sequence-length <n>
  --output <versioned shard directory>
```

The command should support:

- Dry run statistics
- Resume after interruption
- Atomic shard publication
- Content addressed manifests
- Per shard checksums
- Canonical tokenizer validation mode
- GigaToken acceleration behind a selectable backend

Keeping the canonical tokenizer as a validation backend prevents the optimization from becoming the authority.

## Adoption trigger

Adopt GigaToken when all conditions hold:

1. Tokenization consumes at least 10 percent of training data preparation wall time, or one sustained CPU core.
2. The recurring workload is at least hundreds of megabytes, preferably gigabytes.
3. The target tokenizer is supported and exact parity passes.
4. Peak memory remains within a declared ceiling.
5. The native path improves total pipeline time after shard writing is included.
6. The integration remains confined to training data preparation.

## Decision

**Current decision:** Do not add GigaToken to existing Helioy products.

**Training decision:** Treat GigaToken as the leading acceleration candidate for future self hosted training data preparation.

**Next action:** When the base model and first representative corpus are selected, run the bounded pilot above before designing permanent infrastructure.
