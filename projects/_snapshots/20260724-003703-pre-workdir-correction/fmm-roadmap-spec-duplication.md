---
title: fmm Roadmap Duplication Detection Spec
type: spec
tags: [fmm, roadmap, duplication, clones, spec, json_contract, schema]
summary: Two tier duplication roadmap for cheap structural clusters first, then body level clone clusters.
status: draft
source: backend-engineer
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/fmm
head: 5f8a1296d72f507a2e4bd1950001a442dc6b31fc
fmm_version: 0.3.6
created: 2026-06-17
updated: 2026-06-17
inputs:
  - ~/.mdx/projects/fmm-roadmap-spec-foundations.md
  - docs/superpowers/specs/2026-05-29-find-similar-design.md
  - ~/.mdx/projects/fmm-eval-claude--brainstorm.md
---

# fmm duplication detection spec

This spec defines two separate capabilities.

1. Tier 1, `fmm dupes`, ships first. It is a cheap repo wide structural duplication audit that reuses the existing `find_similar` scorer in batch and clustering mode.
2. Tier 2, `fmm clones`, ships later. It adds body level fingerprints and LSH to catch copy paste under different names and signatures.

## Grounding

* Foundations file: `~/.mdx/projects/fmm-roadmap-spec-foundations.md` is binding for the report envelope, deterministic JSON, generated metadata, and schema lifecycle rules. This spec defines only the `results` payloads for duplication reports. It does not redefine `FmmReportEnvelope`.
* Foundations schema rule: current index data in `.fmm.db` is regeneratable. Index schema bumps are acceptable when current index data changes. Historical snapshots remain outside `.fmm.db` per the foundations decision for `.fmm-snapshots.db`.
* Find similar design: the requested `docs/FIND_SIMILAR_DESIGN.md` path is absent in this checkout. The current checked in find similar design is `docs/superpowers/specs/2026-05-29-find-similar-design.md`. It explicitly deferred batch duplication audit as `fmm dupes`, and locked the v1 ranker to deterministic name token overlap, signature shape, declaration kind, and dependency neighborhood. No embeddings.
* Evaluation gap: `~/.mdx/projects/fmm-eval-claude--brainstorm.md` identifies repo wide duplication scan as the largest code health gap. `find_similar` is probe based today.
* Live verification: `fmm dupes` and `fmm clones` are not current commands. `fmm similar dependency_graph --limit 3 --json` returns ranked structural matches from the existing scorer.

## Current code facts

* `crates/fmm-core/src/similarity.rs` owns the ranker.
  * `find_similar` scans candidates, applies directory and test filters, calls `score_against`, threshold gates, sorts deterministically, then truncates.
  * `score_against` computes the existing weighted score from `name`, `shape`, `kind`, and optional `neighborhood` signals.
  * `collect_candidates` builds candidates from `Manifest.files`, file exports, file methods, line ranges, signatures, and declaration kinds.
  * `tokenize_name` is the single name tokenizer.
  * `SimilarMatch`, `Signals`, `SimilarOptions`, and `SymbolProbe` are the current public data types.
* `crates/fmm-core/src/parser/types.rs` is the typed parser output seam.
  * `ExportEntry` carries symbol name, lines, signature, visibility, declaration kind, parent class, and relationship kind.
  * `Metadata` carries exports, imports, dependencies, dependency kinds, named imports, namespace imports, and LOC.
  * `ParseResult` carries `Metadata` plus optional custom fields.
  * `Parser` returns `ParseResult` from a tree sitter backed language parser.
* `crates/fmm-core/src/types.rs` is the store serialization seam.
  * `PreserializedRow` carries file level JSON columns plus `ExportRecord` and `MethodRecord` vectors.
  * `serialize_file_data_inner` maps parser output into persisted export and method rows.
* `crates/fmm-store/src/schema.rs` is schema v6.
  * `exports` and `methods` already persist `start_line`, `end_line`, `signature`, `visibility`, and `declaration_kind`.
  * `files` already persists `content_hash`, but only at file granularity.
* `crates/fmm-store/src/writer.rs` and `crates/fmm-store/src/reader/exports.rs` persist and reload exports and methods.
* `crates/fmm-cli/tools.toml` is the CLI and MCP source of truth. New report tools must be added there, then generated help and schema are rebuilt.
* `crates/fmm-cli/src/cli/mod.rs::Commands` is already over the repo line limit. Any implementation that adds `dupes` or `clones` must first split this CLI declaration instead of appending variants to the oversized file.
* `crates/fmm-cli/src/mcp/mod.rs` currently returns MCP tool output as text content. JSON report tools should serialize the envelope as the text payload unless the MCP transport is changed in a separate foundations implementation.

## Shared report contract

Envelope fields come from the foundations spec. The following types define only `results`.

```typescript
type Lines = [number, number];

interface DuplicateMember {
  name: string;
  file: string;
  lines: Lines;
  signature?: string;
  kind?: string;
}

interface DuplicateCluster {
  score: number;
  members: DuplicateMember[];
}

interface DuplicateReportStats {
  candidates: number;
  blocks: number;
  comparisons: number;
  clusters: number;
}

interface DupeClustersResult {
  clusters: DuplicateCluster[];
  stats: DuplicateReportStats;
}

interface CloneClustersResult {
  clusters: DuplicateCluster[];
  stats: DuplicateReportStats & {
    fingerprintedSymbols: number;
    lshBuckets: number;
  };
}
```

Sorting is deterministic.

1. Clusters sort by `score` descending, then member count descending, then first member `file`, `name`, and `lines` ascending.
2. Members sort by `file`, `name`, then `lines` ascending.
3. Scores are rounded to two decimals for human output and emitted as stable numeric values in JSON.

## Field traceability

| Result field | Tier 1 source | Tier 2 source |
| --- | --- | --- |
| `clusters[].score` | `crates/fmm-core/src/similarity.rs::score_against` through the new batch pair scorer | New `crates/fmm-core/src/clones.rs::clone_similarity` using persisted shingle fingerprints |
| `members[].name` | `crates/fmm-core/src/similarity.rs::collect_candidates` from `Manifest.files` exports and methods | New symbol fingerprint rows derived from `crates/fmm-core/src/parser/types.rs::ExportEntry` |
| `members[].file` | `crates/fmm-core/src/manifest/mod.rs::Manifest` file map keys | New `symbol_fingerprints.file_path` sidecar rows referencing `files.path` |
| `members[].lines` | `crates/fmm-core/src/manifest/mod.rs::ExportLines` and method line ranges | New symbol fingerprint rows copied from `ExportEntry.start_line` and `ExportEntry.end_line` |
| `members[].signature` | `crates/fmm-core/src/manifest/file_entry.rs::SymbolMetadata` | New symbol fingerprint rows copied from `ExportEntry.signature` |
| `members[].kind` | `crates/fmm-core/src/manifest/file_entry.rs::SymbolMetadata` and `crates/fmm-core/src/parser/types.rs::DeclarationKind` | New symbol fingerprint rows copied from `ExportEntry.declaration_kind` |
| `stats.candidates` | Candidate count from batch collection | Loaded fingerprint row count after filters |
| `stats.blocks` | Structural block count | LSH bucket count with at least two symbols |
| `stats.comparisons` | Pair comparisons after structural blocking | Pair comparisons after LSH candidate generation |

## Tier 1: `fmm dupes`, v1

### Goal

Find likely structural duplicate symbols across the current index without new persisted data. This is the deferred batch form of `find_similar`.

### Non goals

* No body similarity.
* No embeddings.
* No schema change.
* No per language parsing beyond what `similarity.rs` already uses.

### Core design

Add a batch API that reuses the existing ranker rather than copying score logic.

Recommended shape:

```rust
pub struct DupeOptions {
    pub directory: Option<String>,
    pub kinds: Vec<String>,
    pub min_score: f64,
    pub limit: usize,
    pub include_tests: bool,
}

pub fn find_dupe_clusters(manifest: &Manifest, opts: &DupeOptions) -> DupeClustersResult
```

Implementation notes:

1. Refactor `similarity.rs` so `collect_candidates`, pair neighborhood scoring, and `score_against` feed both `find_similar` and `find_dupe_clusters`. Keep one scorer.
2. Preserve `find_similar` behavior and tests.
3. For each accepted candidate pair, add an undirected edge with the existing score and signals.
4. Use union find to turn accepted edges into clusters.
5. Cluster score is the highest accepted edge score in that cluster. This is simple, deterministic, and stable under union order.

### Blocking strategy

The v1 scan must not compare every symbol with every other symbol.

1. Build all candidates once by reusing `collect_candidates`.
2. Filter by directory, kind, and test policy before blocking.
3. Compute name tokens with `tokenize_name` and signature shape with the existing signature shape helper.
4. Build document frequency per `(declaration_kind, token)` over candidates.
5. For each candidate, choose at most four block keys:
   1. Up to three rarest non empty name tokens under its declaration kind.
   2. One deterministic name shingle key when two or more tokens exist.
   3. If there is no usable name token, a fallback shape key from declaration kind, arity, and return type.
6. Bucket key shape: `(declaration_kind_or_unknown, key_kind, key_value)`.
7. If a bucket exceeds the internal maximum size, split it by signature shape. If it still exceeds the maximum, skip only the overflow comparisons and add a diagnostic to the envelope.
8. Generate unique unordered pairs from buckets. De duplicate pairs by stable `(file, name, lines)` member keys before scoring.

Complexity target:

* Candidate collection: `O(N)`.
* Blocking: `O(N * K)` where `K <= 4`.
* Scoring: `O(P)` where `P` is the number of unique pairs emitted by bounded buckets. With a bucket cap, `P` is bounded by `N * K * max_bucket_size`, not `N^2`.
* Memory: `O(N * K + E)` where `E` is accepted edges.

### Thresholds

Use `similarity.rs::DEFAULT_THRESHOLD` as the initial v1 default so `dupes` and `similar` share semantics. Keep `--min-score` public. Add a named `DEFAULT_DUPES_LIMIT` for report cluster count.

Open item: before implementation, calibrate whether repo wide reports need a stricter default than probe mode. Do not change the score formula to solve report noise.

### CLI surface

```text
fmm dupes [--dir <prefix>] [--kind <kind>]... [--min-score <float>] [--limit <n>] [--include-tests] [--json]
```

Text output is a compact cluster report. `--json` emits the foundations envelope with `results: DupeClustersResult`.

### MCP surface

Add `tools.fmm_dupe_clusters` in `crates/fmm-cli/tools.toml`.

Parameters mirror the CLI:

* `directory?: string`
* `kind?: string | string[]`
* `min_score?: number`
* `limit?: number`
* `include_tests?: boolean`

MCP returns the serialized foundations envelope in the existing text content wrapper.

### Tests

* Unit test blocking does not create duplicate pairs and remains bounded on a synthetic many symbol fixture.
* Unit test clustering is order independent.
* Regression test a known real clone outranks a same shape coincidence, inherited from the find similar design.
* CLI snapshot for text output.
* JSON double run byte equality under the foundations envelope.
* MCP schema snapshot after updating `tools.toml`.

## Tier 2: `fmm clones`, v2

### Goal

Detect copy pasted bodies even when names and signatures differ. Tier 2 adds new index data and a different similarity path, then reports clusters in the same result shape.

### Non goals

* No raw source storage.
* No embeddings.
* No cross language clone matching by default.
* No replacement for Tier 1. `dupes` remains the cheap structural signal.

### Fingerprint data model

Add typed parser output:

```rust
pub struct SymbolBodyFingerprint {
    pub symbol_key: String,
    pub language_id: String,
    pub start_line: usize,
    pub end_line: usize,
    pub declaration_kind: Option<DeclarationKind>,
    pub signature: Option<String>,
    pub token_count: u32,
    pub shingle_count: u32,
    pub exact_body_hash: String,
    pub minhash: Vec<u64>,
    pub shingle_hashes: Vec<u64>,
    pub fingerprint_version: u32,
}
```

Attach it as typed metadata, preferably `Metadata.symbol_fingerprints: Vec<SymbolBodyFingerprint>`, instead of hiding it in untyped `custom_fields`. `ParseResult` already carries typed metadata from every parser, and `serialize_file_data_inner` is the existing bridge to storage.

Persist in a sidecar table rather than widening both `exports` and `methods`.

```sql
CREATE TABLE IF NOT EXISTS symbol_fingerprints (
    file_path TEXT NOT NULL REFERENCES files(path) ON DELETE CASCADE,
    symbol_key TEXT NOT NULL,
    language_id TEXT NOT NULL,
    start_line INTEGER NOT NULL,
    end_line INTEGER NOT NULL,
    signature TEXT,
    declaration_kind TEXT,
    token_count INTEGER NOT NULL,
    shingle_count INTEGER NOT NULL,
    exact_body_hash TEXT NOT NULL,
    minhash TEXT NOT NULL,
    shingle_hashes BLOB NOT NULL,
    fingerprint_version INTEGER NOT NULL,
    PRIMARY KEY (file_path, symbol_key, start_line, end_line)
);
CREATE INDEX IF NOT EXISTS idx_symbol_fingerprints_kind
    ON symbol_fingerprints(declaration_kind);
CREATE INDEX IF NOT EXISTS idx_symbol_fingerprints_version
    ON symbol_fingerprints(fingerprint_version);
```

Schema impact: this is current index data, so bump `.fmm.db` `SCHEMA_VERSION` when v2 lands. No `.fmm-snapshots.db` change is required. The sidecar is regenerated by `fmm generate` and dropped by index schema reset like other current index tables.

Store loading:

* Add `FmmStore::load_symbol_fingerprints` rather than loading fingerprint BLOBs into `Manifest` for every navigation tool.
* Implement it in SQLite and memory stores.
* `fmm clones` and `fmm_clone_clusters` use that store method directly.

### Fingerprint computation

For each executable symbol body captured by a language parser:

1. Use the existing tree sitter parse tree for the source file.
2. Select the body node for functions and methods. Include tests only when configured.
3. Walk the subtree in source order.
4. Ignore comments and whitespace.
5. Normalize identifiers to `ID` and string, numeric, and template literals to `LIT`.
6. Preserve language keywords, operators, delimiters, and control flow tokens.
7. Prefix the stream with `language_id` for same language matching.
8. Build contiguous `k` gram shingles over normalized tokens.
9. Hash shingles with a stable hash implementation that lives in `fmm-core`, not the current private CLI freshness helper.
10. Store exact body hash, sorted unique shingle hashes, and a fixed length minhash signature.

Initial constants should be explicit and versioned:

* `FINGERPRINT_VERSION = 1`
* `K_GRAM = 7`
* `MINHASH_SIZE = 128`
* `LSH_BANDS = 32`
* `LSH_ROWS = 4`

Changing any constant increments `FINGERPRINT_VERSION`.

### LSH clustering

1. Load filtered `symbol_fingerprints` rows.
2. Skip bodies below `--min-tokens` to avoid boilerplate clusters.
3. Split each minhash signature into `LSH_BANDS` bands of `LSH_ROWS` values.
4. Bucket key: `(fingerprint_version, language_id, band_index, hash(band_values))`.
5. Generate unique unordered candidate pairs only within shared LSH buckets.
6. Verify each candidate pair with exact Jaccard over the stored shingle hash sets.
7. Accept pairs at or above `--min-similarity`.
8. Union accepted pairs into clusters.
9. Cluster score is the highest exact Jaccard score in the cluster.

Complexity target:

* Index time: `O(total_symbol_tokens + symbol_count * MINHASH_SIZE)`.
* Query bucket build: `O(S * LSH_BANDS)`.
* Verification: `O(C * average_shingle_set_merge)` where `C` is candidate pairs emitted by LSH, not all symbol pairs.
* Memory: `O(S * LSH_BANDS + C)` plus loaded shingle sets.

Large buckets are capped with diagnostics exactly like Tier 1. The report should expose comparison counts so performance regressions are visible.

### CLI surface

```text
fmm clones [--dir <prefix>] [--kind <kind>]... [--min-similarity <float>] [--min-tokens <n>] [--limit <n>] [--include-tests] [--json]
```

Defaults:

* `--min-similarity`: `0.82`
* `--min-tokens`: `40`
* `--limit`: report cluster limit, same semantics as `dupes`

Open item: calibrate these defaults on fixture repos before marking v2 ready. The constants are part of `FINGERPRINT_VERSION` only when they affect persisted fingerprints.

### MCP surface

Add `tools.fmm_clone_clusters` in `crates/fmm-cli/tools.toml`.

Parameters mirror the CLI:

* `directory?: string`
* `kind?: string | string[]`
* `min_similarity?: number`
* `min_tokens?: number`
* `limit?: number`
* `include_tests?: boolean`

MCP returns the serialized foundations envelope in the existing text content wrapper.

### Tests

* Parser fixture that copies a body under two different names and signatures. Tier 1 may miss it; Tier 2 must find it.
* Fixture with identical shape but different body. Tier 2 must not cluster it above threshold.
* Round trip test for `symbol_fingerprints` in SQLite and memory stores.
* LSH test proving candidate generation is stable and bounded.
* Fingerprint version test proving changed constants invalidate old rows.
* JSON double run byte equality under the foundations envelope.
* MCP schema snapshot after updating `tools.toml`.

## Implementation order

1. Tier 1 core: refactor `similarity.rs` for shared pair scoring, add `find_dupe_clusters`, blocking, and union clustering.
2. CLI hygiene: split `crates/fmm-cli/src/cli/mod.rs::Commands` before adding any new command variants.
3. Tier 1 surfaces: `tools.toml`, CLI command, MCP tool, envelope output, text formatter.
4. Tier 1 tests and gates: `just test`, `just check`.
5. Tier 2 data: typed `SymbolBodyFingerprint`, parser extraction helpers, `PreserializedRow` extension, schema bump, store read and write.
6. Tier 2 core: LSH bucket generation, exact Jaccard verification, union clustering.
7. Tier 2 surfaces: `tools.toml`, CLI command, MCP tool, envelope output, text formatter.
8. Tier 2 tests and gates: `just test`, `just check`.

## Open questions

1. The requested `docs/FIND_SIMILAR_DESIGN.md` path is absent. Confirm whether `docs/superpowers/specs/2026-05-29-find-similar-design.md` is now the canonical design path.
2. Tier 1 default `--min-score`: inherit `similarity.rs::DEFAULT_THRESHOLD` for v1 unless calibration proves a stricter default is needed.
3. Tier 2 thresholds: `0.82` similarity and `40` normalized tokens are proposed defaults that need fixture calibration before v2 ships.
4. Cross language clones: default is same language only. Decide later whether a `--cross-language` flag is worth the false positive risk.
5. Storage budget: v2 stores exact shingle hashes to verify LSH candidates. If database size becomes excessive, evaluate compressed BLOB encoding before dropping exact verification.
