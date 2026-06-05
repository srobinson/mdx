# Atomic generation swap scout and plan

Audit target: `design/federated-knowledge-layer` at `95b33b12450f370b536d44de4ff865909c627035`, aligned with its origin branch. No pull request exists for this branch. The tracked tree was clean before and after the audit. The pre-existing untracked `LESSONS.md` was left untouched.

Scope: design §7.2, with an explicit coupling decision for §6.1. This is a greenfield plan. It contains no compatibility, migration, import, or direct-root fallback path.

## Reuse Map

### Capability ownership

| Capability | Existing owner | Verified behavior | Reuse decision |
| --- | --- | --- | --- |
| Logical home resolution | `src/home.ts:resolveMdmHome`; `src/home.ts:dbIndexDir` | `resolveMdmHome` normalizes the configured home. `dbIndexDir` currently resolves that home as the physical database root. | Keep `resolveMdmHome` as the logical home authority. Stop using `dbIndexDir` as a physical data root once generations land. Physical reads and writes must receive an explicit generation root. |
| Structural paths | `src/index/types.ts:getIndexPaths` | Builds document, section, link, cache, and parsed paths beneath an explicit root. | Reuse against a generation root after removing the inert cache and parsed directory members. Do not make it resolve `current`. |
| Embedding paths | `src/embeddings/embedding-namespace-paths.ts:getEmbeddingsDir`; `src/embeddings/embedding-namespace-paths.ts:getNamespaceDir`; `src/embeddings/embedding-namespace-paths.ts:getVectorPath`; `src/embeddings/embedding-namespace-paths.ts:getMetaPath`; `src/embeddings/embedding-namespace-paths.ts:getActiveProviderPath` | Builds embedding paths beneath a supplied root. | Reuse against a staged or leased generation root. Consolidate vector file constants here and remove the flat vector layout. |
| Generation and `current` paths | none found | Search: `rg -n -e generationRoot -e generationId -e currentGeneration -e readCurrent -e 'gen-[0-9]' src tests`. No root generation grammar, pointer parser, containment validator, or current generation resolver exists. | Add one strict path owner. Accept only `gen-<positive integer>` pointer contents and verify containment beneath the normalized home. |
| Whole set build coordination | `src/index/manifest-refresh.ts:refreshManifestIndex`; `src/index/manifest-build.ts:buildManifestIndex`; `src/index/index-build.ts:buildDiscoveredIndex`; `src/cli/commands/index-run.ts:runIndexCommand`; `src/mcp/handlers.ts:handleMdIndex` | Manifest refresh can mutate `manifest.toml`, then structural state, vector pruning, and BM25 are written. CLI embedding refresh runs later. MCP does not run the same embedding step. No owner commits the complete logical database. | Retain the build operations, but run all selected operations inside one generation writer transaction with an explicit staged root. Make CLI and MCP use the same coordinator. |
| Structural whole set serialization | `src/index/index-state.ts:saveIndexState`; `src/index/storage.ts:createStorage`; `src/index/storage.ts:writeJsonFile` | Documents, sections, and links are saved sequentially. Each JSON file gets a temporary file and rename, but the set has no commit boundary. | Reuse only as serializers into an unpublished staging generation. Restrict raw writer access so callers cannot bypass the generation writer. |
| BM25 serialization | `src/search/bm25-store.ts:BM25StoreImpl.save` | Writes `bm25.json`, then `bm25.meta.json`. | Reuse against the staged generation. Publish both files with the complete set. |
| Vector serialization | `src/embeddings/vector-store.ts:HnswVectorStore.save`; `src/embeddings/vector-store-codec.ts:writeVectorIndex`; `src/embeddings/semantic-search-build.ts:saveEmbeddingBuild` | Writes HNSW binary, vector metadata, then active provider. Active provider failure is caught and downgraded to a warning. | Reuse codec and store mechanics against staging. Make active signature failure fatal. Remove flat path and mutable namespace construction before routing generation roots through this owner. |
| Active signature persistence | `src/embeddings/embedding-namespace-catalog.ts:readActiveProvider`; `src/embeddings/embedding-namespace-catalog.ts:writeActiveProvider`; `src/embeddings/embedding-namespace-catalog.ts:getActiveNamespace` | Active provider is a direct file write. A read can discover a namespace and persist it when the file is missing. Parsed JSON is cast without schema validation. | Make reads pure and schema validated. Only the generation writer may create or change signature state. |
| File fsync and directory fsync | none found | Search: `rg -n -e fsync -e fdatasync -e 'FileHandle\\.sync' -e syncSync -e O_DIRECTORY src tests`. No durability primitive or directory sync adapter exists. | Add a tested filesystem durability adapter. It must sync every generation file, required directories, the pointer temporary file, and the home directory around renames. Unsupported platform behavior must fail clearly. |
| Atomic rename | `src/index/storage.ts:writeJsonFile` | Uses a same-directory temporary JSON file and `fs.rename` for one file. No whole set or pointer rename exists. `src/search/bm25-store.ts:BM25StoreImpl.save`, `src/embeddings/vector-store-codec.ts:writeVectorIndex`, and `src/embeddings/embedding-namespace-catalog.ts:writeActiveProvider` do not share this helper. | Reuse the same-directory temporary file principle. Put whole set publication in the new generation writer. Do not generalize `writeJsonFile` into commit authority. |
| Pointer read | none found | Search: `rg -n -e readCurrent -e currentGeneration -e 'generation pointer' -e 'current pointer' -e 'readFile.*current' -e 'join\\(.*current' src tests`. | Add one pointer decoder used by reader, writer, and reaper. No implicit pointer reads inside low level stores. |
| Reader lease directory and reaper gate | none found | Search: `rg -n -e '\\bleases?\\b' -e '\\breaper\\b' -e 'boot.?id' -e 'process.?start' -e 'PID reuse' -e 'pid reuse' -e 'process\\.kill' -e '/proc/' -e sysctl -e wmic src tests`. No lease, gate, process identity, liveness, or reaper implementation exists. | Add a dedicated reader protocol and process identity adapter. The gate close and lease insertion operations must be filesystem atomic. |
| Writer serialization | none found | Search: `rg -n -e 'writer lock' -e proper-lockfile -e '\\bflock\\b' -e 'exclusive writer' -e 'compare.?and.?swap' src tests package.json pnpm-lock.yaml`. CLI and MCP can both reach refresh, and the watcher retains another direct writer. | Add an exclusive home writer lock based on an atomic filesystem operation and process identity. Hold it across preflight, manifest mutation, generation allocation, build, sync, publish, and reap scheduling. |
| Structural read cache | `src/index/storage.ts:indexCache`; `src/index/storage.ts:readJsonFileCached` | Unbounded process map keyed by full file path and validated with file modification time. Generation paths would distinguish entries, but reaped paths remain resident. | Reuse with explicit eviction by generation when reaping. A bounded cache can replace the map if eviction ownership would otherwise remain fragmented. |
| HNSW read cache | `src/embeddings/hnsw-cache.ts:hnswCacheKey`; `src/embeddings/hnsw-cache.ts:getHnswCacheEntry`; `src/embeddings/hnsw-cache.ts:invalidateHnswCache` | Unbounded process map keyed as root plus namespace. Same process writers invalidate it. A long lived MCP process does not observe a separate process rebuild when the root is stable. | Change the key to exactly `home::namespace::gen`. Evict the generation when it is reaped. Defer broader cross-home LRU policy only if explicit generation eviction proves bounded for this release. |

### Reader entrypoints and lease scope

A lease belongs to the logical operation, not to an individual file load. The following physical readers are reusable only when passed the root from one acquired read session:

| Data | Physical owners | Composing owners that need one shared session |
| --- | --- | --- |
| Structural JSON | `src/index/storage.ts:loadDocumentIndex`; `src/index/storage.ts:loadSectionIndex`; `src/index/storage.ts:loadLinkIndex`; `src/index/storage.ts:readJsonFileCached` | `src/search/content-search.ts:searchContent`; `src/search/content-search.ts:searchWithContent`; `src/search/context.ts:getContext`; `src/duplicates/detector.ts:detectExactDuplicates`; `src/duplicates/detector.ts:detectDuplicates`; `src/index/link-index.ts:getOutgoingLinks`; `src/index/link-index.ts:getIncomingLinks`; `src/index/link-index.ts:getBrokenLinks`; `src/embeddings/semantic-search-pipeline.ts:postProcessResults`; `src/embeddings/semantic-search.ts:semanticSearchWithContent` |
| BM25 | `src/search/bm25-store.ts:BM25StoreImpl.load`; `src/search/bm25-store.ts:readStoredFiles`; `src/search/bm25-store.ts:bm25Search`; `src/search/bm25-store.ts:bm25IndexExists` | `src/search/hybrid-search.ts:hybridSearch`; `src/search/hybrid-search.ts:detectSearchModes`; `src/search/content-search.ts:search` |
| Vectors and signature | `src/embeddings/vector-store-codec.ts:loadVectorIndex`; `src/embeddings/vector-store.ts:HnswVectorStore.load`; `src/embeddings/embedding-namespace-catalog.ts:readActiveProvider`; `src/embeddings/embedding-namespace-catalog.ts:listNamespaces` | `src/embeddings/semantic-search-pipeline.ts:loadVectorStoreForActive`; `src/embeddings/semantic-search-pipeline.ts:prepareSearchPipeline`; `src/embeddings/semantic-search-stats.ts:getEmbeddingStats`; `src/search/hybrid-search.ts:hybridSearch` |
| Direct bypass | `src/cli/utils.ts:getIndexInfo` | Reads and parses the section index directly. Replace this bypass with schema validated storage through the same session. |

User facing database readers that must acquire exactly one session per request are `src/cli/commands/search.ts:searchCommand`, `src/cli/commands/search-mode.ts:runSearchCommand`, `src/cli/commands/stats.ts:statsCommand`, `src/cli/commands/duplicates.ts:duplicatesCommand`, `src/cli/commands/links.ts:linksCommand`, `src/cli/commands/backlinks.ts:backlinksCommand`, `src/cli/commands/embeddings.ts:embeddingsCommand`, `src/mcp/handlers.ts:handleMdSearch`, `src/mcp/handlers.ts:handleMdKeywordSearch`, `src/mcp/handlers.ts:handleMdLinks`, and `src/mcp/handlers.ts:handleMdBacklinks`. The long lived MCP server needs one lease per request. A startup lease would pin one generation and serve stale data.

Source only entrypoints `src/cli/commands/tree.ts:treeCommand`, `src/cli/commands/context.ts:contextCommand`, `src/mcp/handlers.ts:handleMdm`, and `src/mcp/handlers.ts:handleMdStructure` do not read the database and need no generation lease.

The reader boundary is currently split. `src/cli/commands/search-mode.ts:runSearchCommand` passes the source root to `src/search/hybrid-search.ts:hybridSearch` and `src/embeddings/semantic-search-pipeline.ts:prepareSearchPipeline`, where it is treated as a BM25 and vector root. Structural loaders separately resolve the configured home through `src/home.ts:dbIndexDir`. `src/mcp/handlers.ts:handleMdSearch` has the same source-root versus database-root conflict. Introduce explicit `sourceRoot` and leased `indexRoot` values before adding lease calls. Hidden `current` resolution inside loaders would preserve this defect.

## Quality Map

### Correctness and boundary findings

| Severity | Finding | Evidence | Required grooming |
| --- | --- | --- | --- |
| P0 | Four independent commit authorities can expose a mixed database after a crash or to a concurrent reader. | `src/index/index-state.ts:saveIndexState`; `src/search/bm25-store.ts:BM25StoreImpl.save`; `src/embeddings/vector-store.ts:HnswVectorStore.save`; `src/embeddings/embedding-namespace-catalog.ts:writeActiveProvider`; orchestration in `src/index/manifest-build.ts:buildManifestIndex` and `src/cli/commands/index-run.ts:runIndexCommand` | Preserve serializers. Move commit authority, fsync, and pointer publication into one generation writer. |
| P0 | Per-loader generation resolution would still mix generations inside one result. | `src/search/hybrid-search.ts:hybridSearch`; `src/embeddings/semantic-search-pipeline.ts:postProcessResults`; `src/embeddings/semantic-search.ts:semanticSearchWithContent`; `src/cli/commands/search-mode.ts:runHybridMode`; `src/cli/commands/search-mode.ts:runSemanticMode` | Acquire one read session above composition and thread its explicit root through every nested read. |
| P0 | A read mutates active signature state. | `src/embeddings/embedding-namespace-catalog.ts:getActiveNamespace`; `src/embeddings/embedding-namespace-catalog.ts:writeActiveProvider` | Delete write-on-read fallback. Treat missing or invalid signature as a clear read error. |
| P0 | Active provider persistence can fail while embedding build reports success. | `src/embeddings/semantic-search-build.ts:saveEmbeddingBuild` | Make signature persistence part of staged validation. Abort publication on failure. |
| P0 | Current root ownership is internally inconsistent. | `src/cli/commands/search-mode.ts:runSearchCommand`; `src/search/hybrid-search.ts:hybridSearch`; `src/embeddings/semantic-search-pipeline.ts:prepareSearchPipeline`; `src/home.ts:dbIndexDir`; `src/mcp/handlers.ts:handleMdSearch` | Split source and index roots. Require a branded or structurally distinct generation session at database boundaries. |
| P0 | Concurrent writers can lose updates and collide on generation allocation. `manifest.toml` also has an unlocked read, modify, write sequence. | `src/manifest.ts:appendManifestDirectory`; `src/index/manifest-refresh.ts:refreshManifestIndex`; `src/cli/commands/index-run.ts:runIndexCommand`; `src/mcp/handlers.ts:handleMdIndex`; `src/index/watcher.ts:watchDirectory` | Add one cross-process writer lock. Keep manifest append and generation publication inside its critical section. |
| P0 | A normal content edit can retain stale vectors when section identifiers survive. A forced rebuild with zero eligible sections can also leave prior vectors. | `src/index/manifest-build.ts:buildManifestIndex`; `src/embeddings/vector-prune.ts:pruneVectorNamespaces`; `src/cli/commands/index-embeddings.ts:runEmbeddingRefresh`; `src/embeddings/semantic-search-build.ts:buildEmbeddings` | During staged validation, reconcile by content hash and remove or mark semantic state unavailable when a complete valid vector set cannot be produced. A forced zero result must publish an empty valid vector state, not copied stale files. |
| P1 | HNSW and structural caches accumulate entries across generations. The HNSW key omits explicit home and generation identity. | `src/embeddings/hnsw-cache.ts:hnswCacheKey`; `src/index/storage.ts:indexCache` | Use `home::namespace::gen`, and evict every cache entry owned by a reaped generation. |
| P1 | Public and dormant writers can bypass the future transaction. | Re-exports in `src/index/index.ts`; direct build in `src/index/watcher.ts:watchDirectory`; public construction in `src/index/storage.ts:createStorage` | Narrow exports. Require all active database writes to enter through the generation writer. Keep serializers injectable for tests, not as user entrypoints. |

### §6.1 coupling findings

The §6.1 contract is absent. `src/embeddings/embedding-namespace-paths.ts:generateNamespace` creates one directory per signature. `src/embeddings/embedding-namespace-catalog.ts:listNamespaces`, `src/embeddings/embedding-namespace-catalog.ts:switchNamespace`, `src/embeddings/embedding-namespace-catalog.ts:removeNamespace`, and `src/cli/commands/embeddings.ts:embeddingsCommand` expose multiple resident signatures and switching. `src/embeddings/semantic-search-build.ts:prepareEmbeddingRuntime` creates and activates a requested namespace without comparing it with an existing database signature.

The current guards verify dimensions only. `src/embeddings/vector-store.ts:HnswVectorStore.load` and `src/embeddings/semantic-search-pipeline.ts:prepareSearchPipeline` accept a different provider or model when dimensions match. `src/embeddings/vector-store.ts:HnswVectorStore.add` leaves width rejection to the native library and reports a generic store failure. No owner implements `--reembed`, `--rewrite-signature`, a destructive confirmation, a no cost new home path, a costed rebuild path, or a before-and-after signature summary. Searches run: `rg -n "reembed|rewrite-signature|Nothing changed|second database|signature mismatch" src test tests docs`.

The preflight must run before `src/index/manifest-refresh.ts:refreshManifestIndex` calls `src/manifest.ts:appendManifestDirectory`; otherwise the required “nothing changed” result is false. §6.1 shares the writer authority and staging seam with §7.2. Its signature model, three-path UX, cost and time quantification, destructive confirmation, help, errors, and deletion of multiple namespace management are a distinct change set.

### Duplication and dead surface

1. `src/embeddings/vector-store.ts:HnswVectorStore` duplicates vector filenames and supports both flat and namespaced layouts. Production calls mostly use `src/embeddings/vector-store.ts:createNamespacedVectorStore`; `src/embeddings/vector-prune.ts:pruneVectorNamespaces` constructs the flat form and mutates the namespace. Remove the flat layout and require namespace at construction.

2. Provider, model, and dimensions recur across `src/embeddings/embedding-namespace-catalog.ts:ActiveProvider`, `src/embeddings/embedding-namespace-catalog.ts:EmbeddingNamespace`, `src/embeddings/vector-store.ts:VectorIndex`, `src/embeddings/semantic-search-build.ts:EmbeddingRuntime`, and `src/config/schema.ts:EmbeddingsConfig`. §6.1 should add one `EmbeddingSignature` owner rather than another shape.

3. `src/cli/commands/embeddings.ts:switchSubcommand` repeats active provider write and display branches. The single signature contract makes switch and remove behavior obsolete. Delete it when §6.1 lands instead of refactoring parallel behavior.

4. `src/index/types.ts:getIndexPaths` exposes `cache` and `parsed`; `src/index/storage.ts:initializeIndex` creates the parsed directory. Production searches found no reader or writer for either directory beyond creation. Searches run: `rg -n "\\.cache|\\.parsed|paths\\.cache|paths\\.parsed|/cache|/parsed" src --glob '!**/*.test.ts'`. Remove both during the generation path reshape.

5. `src/search/context.ts:getContext` and `src/index/link-index.ts:getBrokenLinks` have no production callers, but they are programmatic exports. Treat them as supported read entrypoints until the public API decision is explicit.

6. Design §17 still mentions same-signature vector import while §6.2 and §18 define fresh embedding with no migration. Follow §18. Correct the stale design wording in the implementation documentation pass. Do not add import code.

### Sizing risks

No production TypeScript file currently exceeds 700 lines. The primary pressure points are:

| File | LOC | Risk |
| --- | ---: | --- |
| `src/cli/help.ts` | 668 | §6.1 flags and help would cross the hard limit. Extract command help before adding text. |
| `src/index/index-build.ts` | 651 | Keep generation coordination outside this serializer. |
| `src/errors/index.ts` | 646 | Put generation and signature error families in focused modules. |
| `src/embeddings/semantic-search-build.ts` | 637 | Extract persistence and runtime preparation before adding generation or signature logic. |
| `src/embeddings/vector-store.ts` | 593 | Remove flat layout before adding generation context. |
| `src/cli/error-handler.ts` | 558 | `formatError` is 226 lines. Extract feature-specific formatting before §6.1 touches it. |
| `src/cli/commands/embeddings.ts` | 532 | `switchSubcommand` is about 200 lines. Delete superseded switch and remove flows for §6.1. |
| `src/embeddings/semantic-search-pipeline.ts` | 482 | Keep lease acquisition above the pipeline and pass a session in. |
| `src/search/hybrid-search.ts` | 451 | `hybridSearch` is 157 lines. Decompose before threading a read session through it. |

Test pressure also matters. `src/errors/errors.test.ts` and `src/embeddings/provider-errors.test.ts` already exceed 700 lines. Do not add generation or signature cases to them. Create focused test files and split an existing test file before modifying it.

### Grooming recommendation

Before §7.2 implementation, decompose `src/search/hybrid-search.ts:hybridSearch`, remove flat vector paths, make active signature reads pure, and extract embedding persistence from `src/embeddings/semantic-search-build.ts:saveEmbeddingBuild`. During §7.2, split source root from database root, narrow raw writer exports, remove inert cache and parsed paths, and add architecture guards. Before §6.1, extract help and error ownership, define the shared signature type, and delete multiple namespace switching and removal.

The focused existing gate passed: `pnpm exec vitest run src/home.test.ts src/index/storage.test.ts src/search/bm25-store.test.ts src/embeddings/vector-store.test.ts src/index/manifest-build.test.ts src/architecture/db-foundation-boundaries.test.ts`. Result: 6 files and 95 tests passed. These tests prove existing local behavior, including per-file atomic writes. They do not prove generation atomicity, lease safety, durability, or signature enforcement.

## Plan

### Scope decision

Implement §7.2 alone in Plan 3. Implement §6.1 immediately after it on the shared generation writer seam.

This order closes the existing mixed database and stale reader risk first. It also creates the transaction boundary required to prove §6.1’s no write mismatch outcome. Combining both sections would add a new cross-process lease and reaper protocol, durability work, root boundary repair, cache identity, signature vocabulary, three CLI paths, estimation, destructive confirmation, help extraction, error extraction, and deletion of the current namespace model in one change. The combined blast radius is too large for one independently provable plan.

Plan 3 must expose a preflight hook before any manifest or staging write. Plan 4 can attach §6.1 without reopening commit authority. This is the only intentional coupling.

### Locked design decisions

1. `current` is a regular file beneath the normalized home. Its entire content is one strict `gen-<positive integer>` name.

2. Each generation is immutable after publication. Low level serializers may mutate only an unpublished staging directory.

3. A read session owns `home`, `generation`, `indexRoot`, and one lease. Every file used to produce one logical result comes from that root.

4. A reader prepares a complete lease record, then atomically inserts it into `gen-<n>/leases/open/`. A reaper closes admission by atomically renaming `leases/open` to `leases/closed`. The reader rereads `current` and the gate state. It releases and retries when the generation changed or admission lost the race. A reader that linearized before gate close remains represented in the closed directory and is protected.

5. A lease records PID, process start identity, and boot identity where the platform exposes it. A matching live process is retained indefinitely. Age is never abandonment evidence. Only a dead process or a reused PID may be removed. Invalid or unreadable identity is retained conservatively.

6. The reaper never deletes `current`. It closes the candidate gate, waits for leases and the configured grace interval, checks current again, and deletes only when no protected lease remains. Reaping is eventual and cannot block a successful publish on a live reader.

7. One cross-process writer lock protects manifest mutation, generation number allocation, staging, fsync, publication, and reap scheduling. Lock recovery uses the same PID and process identity rule as leases. Age alone cannot recover a lock.

8. A new generation seeds immutable files from current when incremental build semantics require prior state. Use independent copies. Do not hard link files that current serializers may rewrite. Never seed gates, leases, temporary files, or process caches.

9. First use with no `current` builds a fresh `gen-1`. Existing direct-root artifacts are ignored. There is no migration, import, cleanup, or fallback behavior.

10. HNSW cache identity is exactly `home::namespace::gen`. Reaping evicts both HNSW and structural cache entries for that generation.

### Implementation sequence

1. **Groom the touched boundaries.** Decompose `src/search/hybrid-search.ts:hybridSearch`. Remove flat vector construction from `src/embeddings/vector-store.ts:HnswVectorStore` and `src/embeddings/vector-prune.ts:pruneVectorNamespaces`. Make `src/embeddings/embedding-namespace-catalog.ts:getActiveNamespace` read only. Extract persistence from `src/embeddings/semantic-search-build.ts:saveEmbeddingBuild`. Keep every new file below 700 lines and every function below about 150 lines.

2. **Add generation path and durability owners.** Create focused modules such as `src/db/generation-paths.ts` and `src/db/fs-durability.ts`. Reuse `src/home.ts:resolveMdmHome`, `src/index/types.ts:getIndexPaths`, and embedding path helpers against explicit roots. Implement strict pointer decoding, containment, staging names, same-home renames, recursive file and directory sync, and platform-specific durability errors.

3. **Add process identity, writer lock, and reader lease primitives.** Create `src/db/process-identity.ts`, `src/db/generation-reader.ts`, and `src/db/generation-writer.ts`, with a small facade if needed. Use injectable filesystem, clock, and process identity adapters for deterministic races and PID reuse tests. Keep gate check plus lease insertion and gate close as atomic filesystem transitions.

4. **Build and publish a complete generation.** Under the writer lock, run optional preflight before all writes, append the manifest if requested, allocate one generation, seed required immutable artifacts, run the build callback against staging, validate the complete artifact set, sync it, rename staging to `gen-<n>`, sync the home, write and sync a temporary pointer, rename it to `current`, then sync the home again. On any failure before pointer rename, leave current unchanged and remove or later reap the unpublished generation.

5. **Unify all writers.** Refactor `src/index/manifest-refresh.ts:refreshManifestIndex` to accept the staged index root. Make `src/cli/commands/index-run.ts:runIndexCommand` keep structural, vector pruning, BM25, embedding refresh, and active signature in one transaction. Make `src/mcp/handlers.ts:handleMdIndex` call the same coordinator. Remove or disable the direct path in `src/index/watcher.ts:watchDirectory`. Narrow `src/index/index.ts` exports so raw writers cannot become an alternate user path.

6. **Route all readers through one session.** Introduce separate `sourceRoot` and `indexRoot` parameters. Wrap each database CLI command and MCP handler listed in the Reuse Map with one acquire and release scope. Pass the session through hybrid, semantic, content enrichment, statistics, duplicate, link, and backlink composition. Replace `src/cli/utils.ts:getIndexInfo` direct JSON parsing. Leave source only commands outside the lease protocol.

7. **Make caches generation aware and add reaping.** Change `src/embeddings/hnsw-cache.ts:hnswCacheKey` to `home::namespace::gen`. Give both caches generation eviction. After publish and at startup, scan noncurrent generations, close their gates, retain live matching leases without time limit, apply grace to eligible generations, recheck current, evict cache entries, and delete.

8. **Enforce logical whole set coherence.** In staging, reconcile vectors by content hash, clear stale vectors when no sections are eligible, validate vector binary, metadata, dimensions, and active signature as one set, and make any active signature write failure fatal. This uses `src/embeddings/vector-prune.ts:pruneVectorNamespaces`, `src/embeddings/semantic-search-build.ts:buildEmbeddings`, and `src/embeddings/semantic-search-build.ts:saveEmbeddingBuild` without adding §6.1 UX.

9. **Prepare the §6.1 seam without implementing its UX.** The writer API begins with a pure optional preflight that runs before `src/manifest.ts:appendManifestDirectory` and before generation creation. No Plan 3 command introduces `--reembed` or `--rewrite-signature`. Plan 4 adds a single `EmbeddingSignature` owner, strict persisted decoding, full provider/model/dim comparison, no cost new home path, costed rebuild path, destructive rewrite confirmation, both signatures, cost and time quantification, and removal of switch/remove namespace behavior.

### Tests and gates

1. **Paths and bootstrap:** no current builds fresh `gen-1`; strict pointer grammar rejects traversal, absolute paths, whitespace variants, zero, and malformed names; direct legacy root artifacts are ignored.

2. **Pointer failure injection:** fail after every structural, BM25, vector, metadata, signature, file sync, directory sync, generation rename, and pointer temporary step. Before pointer rename, current remains old. After pointer rename, the new generation validates as complete.

3. **Lease race barriers:** pause readers after current read, before lease insertion, after insertion, and before current reread. Race gate close and pointer flip at every barrier. Assert retry or one protected generation, with no unleased read.

4. **Process identity:** verify current process identity, a dead child, simulated PID reuse, boot identity change, malformed records, and a live matching process held beyond grace. Assert that age alone never permits deletion.

5. **Reaper:** assert current is never closed or deleted; a noncurrent gate closes once; a live lease pins indefinitely; release permits deletion after grace; current changes during reap cancel deletion; release works whether the lease is under open or closed.

6. **Concurrent processes:** run reader and writer subprocesses with generation marker sets. Every result is all old or all new. Hold an old lease across publication and prove its generation remains until release. Run two writers that append different paths and prove unique generation allocation with no lost manifest update.

7. **Cache identity:** the same namespace in two generations yields different `home::namespace::gen` keys. A long lived MCP process observes a pointer flip made by another process. Reaping evicts old vector and structural entries.

8. **Writer routing:** architecture tests reject direct configured-home data reads outside generation modules, raw writes from CLI or MCP, write-on-read signature behavior, and a direct watcher writer. Active signature failure aborts publication.

9. **Vector coherence:** an edit that retains a section ID updates or invalidates its vector by content hash. A forced build with zero eligible sections publishes an empty valid vector state. Vector binary, metadata, and active signature cannot publish independently.

10. **Size and duplication:** extend `src/architecture/db-foundation-boundaries.test.ts` for generation boundaries, unique signature vocabulary, no flat vector layout, production files below 700 lines, and touched functions below about 150 lines. Put concurrency and fault tests in new focused files.

11. **Verification order:** run focused generation, process identity, storage, BM25, vector, manifest, CLI, MCP, and architecture tests. Then run `npx --yes pnpm@10.28.0 test`, `npx --yes pnpm@10.28.0 typecheck`, `npx --yes pnpm@10.28.0 build`, and `npx --yes pnpm@10.28.0 check`. Keep the existing macOS, Ubuntu, and Windows matrix on Node 20 and 22.

12. **Dogfood gate:** use an isolated temporary `MDM_HOME` and a real corpus. Build, search through CLI and MCP, rebuild from a second process, hold and release leases, force failures, restart the MCP process, and reap. Do not point the new writer at a live home until all automated and isolated dogfood gates pass.
