# MDM DB Foundation Scout Report

Baseline: `4b07518bf626e06c25fb591646acaa8fffdf6ea4`

Scope: Section 5 and Section 7.1 of `docs/superpowers/specs/2026-06-22-federated-markdown-knowledge-layer-design.md`. Manifest, ingest orchestration, signature policy, vector import, generation swap, partition search, and federation are excluded.

## Reuse Map

### Home and config

- Reuse: `src/config/loader.ts` `loadTomlFileWithStatus` is the existing TOML read and parse owner. Every config tier must call it.
- Reuse: `src/config/loader.ts` `mergePartials` is the existing keyed deep merge. Promote it for the home, portable project, local project, environment, and CLI precedence chain.
- Reuse: `src/config/loader.ts` `readEnvVars`, `mergeWithDefaults`, `loadDetailed`, and `validateConfig` already own environment decoding, defaults, validation, and CLI overlay.
- Reuse: `src/config/schema.ts` `defaultConfig` is the sole default value owner. The obsolete `index.indexDir` and `paths.cacheDir` fields must be removed there and from their projections rather than shadowed with new settings.
- Reuse: `src/config/service.ts` `ConfigServiceLive` and `makeConfigLayerFromOptions` already expose config through Effect layers. The merge change stays below this boundary.
- Existing infra: `smol-toml` is already the TOML parser. No parser or config provider is needed.
- None found: a shared MDM home resolver. Searches run: `rg 'os\.homedir|homedir\(|MDM_HOME' src` and `rg 'realpathSync|realpath\(' src`. `resolveMdmHome` belongs in new neutral owner `src/home.ts`.
- None found: a result shape for several merged config files. Searches run: `rg 'sourceFiles|ConfigFileLoadResult|sourceFile' src/config src/cli`. Extend the existing loader result instead of adding a parallel loader.

### Index directory and persistence

- Reuse: `src/index/types.ts` `getIndexPaths` is the structural index layout owner. Change its input from a source root plus implicit `.mdm` to an explicit DB index directory.
- Reuse: `src/index/storage.ts` `createStorage` is the storage construction seam. Split its current `rootPath` conflation into `sourceRoot` and `indexRoot` while preserving all JSON load and save APIs.
- Reuse: `src/index/storage.ts` `writeJsonFile` already performs temp file plus rename writes. Canonical key migrations must reuse it for structural indexes.
- Reuse: `src/embeddings/embedding-namespace.ts` `getEmbeddingsDir`, `getNamespaceDir`, and `getActiveProviderPath` already own embedding namespace paths. Move them mechanically, then make them consume the DB index directory.
- Reuse: `src/embeddings/embedding-namespace.ts` `getLegacyVectorPath`, `getLegacyMetaPath`, and `getLegacyMetaJsonPath` already own legacy flat paths. Keep these explicitly source rooted for Plan 2 import. They must not call `dbIndexDir`.
- Reuse: `src/embeddings/vector-store.ts` `HnswVectorStore.getIndexDir`, `getVectorPath`, and `getMetaPath` already centralize HNSW paths inside the class. Repoint these methods rather than adding factory specific path logic.
- Reuse: `src/search/bm25-store.ts` `createBM25Store` and `bm25IndexExists` already own BM25 persistence. Both must derive paths from `getIndexPaths`.
- Reuse: `src/embeddings/hnsw-cache.ts` `hnswCacheKey` is the existing cache identity. Feed it the canonical DB index root.
- Similar checked and rejected: `src/cli/utils.ts` `findIndexRoot` discovers legacy parent `.mdm` directories. Consolidated DB lookup has one home, so this implementation is obsolete and must be removed rather than adapted into a second lookup path.
- None found: a DB index directory abstraction distinct from the legacy import directory. Searches run: `rg 'INDEX_DIR|path\.join\([^)]*["\x27]\.mdm["\x27]' src --glob '*.ts'`. Add `dbIndexDir` beside `resolveMdmHome` and delete the ambiguous `INDEX_DIR` export once callers migrate.

### Canonical document identity

- Reuse: `src/mcp/adapter.ts` `resolveAndValidatePath` contains the existing boundary aware lexical and realpath checks. Extract its neutral path containment predicate into `src/db/canonical.ts`; keep MCP result shaping in the adapter.
- Reuse: `src/parser/parser.ts` `parse` already derives document and section IDs from its `path` option. Pass the canonical document key into this existing seam.
- Reuse: `src/index/indexer.ts` `walkDirectory`, `flattenSections`, `resolveInternalLink`, and `buildIndex` are the current discovery and index mutation pipeline. Decompose them mechanically, then canonicalize before parse and merge.
- Reuse: `src/index/storage.ts` `DocumentIndexSchema`, `SectionIndexSchema`, and `LinkIndexSchema` are the runtime persistence contracts. Version and extend these schemas; do not create unvalidated sidecar identity data.
- Reuse: `src/embeddings/vector-store.ts` `VectorIndexSchema` and its MessagePack fallback migration are the vector metadata codec. Extract the codec so canonical migration and live load share one implementation.
- Reuse: `src/search/bm25-store.ts` `BM25Store.load` and `BM25Store.save` already own the serialized `sectionMap`. Add key rewrite through this owner.
- Reuse: `src/search/path-matcher.ts` `matchPath` remains the glob matcher for user filters. It is wrong shaped for security or directory membership because it performs case insensitive regex matching and has no inode context.
- Similar checked and rejected: `src/parser/parser.ts` `parseFile` reads and parses a file but does not expand `~`, canonicalize with realpath, capture inode identity, or provide deterministic hardlink selection.
- None found: a canonical document key type, inode identity record, case sensitivity probe, deterministic hardlink grouping, or shared source file resolver. Searches run: `rg 'DocumentKey|st_dev|st_ino|dev:|ino:|resolveSourceFile|caseSensitive' src` and `rg 'realpath' src`. These capabilities belong together in `src/db/canonical.ts`.
- None found: an index wide relative key migration. Searches run: `rg 'migrat.*document|rewrite.*document|relative.*canonical|documentPath.*migrat' src`. Add one canonical migration owner that reuses the structural writers, vector codec, and BM25 store.

### Source reads that must converge on one resolver

- Reuse: `src/db/canonical.ts` `resolveSourceFile` will be the single owner introduced by this plan. Every source content read below must call it.
- Existing caller: `src/index/indexer.ts` `buildBM25Index`.
- Existing caller: `src/search/searcher.ts` `searchContent` and `searchWithContent`.
- Existing caller: `src/duplicates/detector.ts` `createFileContentCache`.
- Existing caller: `src/embeddings/semantic-search-build.ts` `collectSectionsToEmbed`.
- Existing caller: `src/embeddings/semantic-search.ts` `semanticSearchWithContent`.
- Existing caller: `src/embeddings/semantic-search-pipeline.ts` `attachContextToResults` Effect block.
- Existing caller: `src/cli/commands/search.ts` `filterResultsByRefineTerms`.
- Searches run: `rg 'path\.join' src/index/indexer.ts src/search/searcher.ts src/duplicates/detector.ts src/embeddings/semantic-search-build.ts src/embeddings/semantic-search.ts src/embeddings/semantic-search-pipeline.ts src/cli/commands/search.ts` and `rg 'documentPath|docPath'` over the same files.

### Tests and gates

- Reuse: co located Vitest suites under `src/**/*.test.ts` are the project convention. Add focused suites beside new owners.
- Reuse: `src/index/storage.test.ts`, `src/config/loader.test.ts`, `src/embeddings/embedding-namespace.test.ts`, `src/embeddings/vector-store.test.ts`, `src/index/indexer.test.ts`, and `src/search/searcher.test.ts` cover the existing contracts.
- Existing infra: `package.json` defines `pnpm test`, `pnpm typecheck`, `pnpm build`, `pnpm check`, and `pnpm quality`.
- Similar checked and rejected: `src/config/loader.test.ts` is already 696 lines. New precedence coverage belongs in `src/config/config-precedence.test.ts` to respect the 700 line limit.
- None found: an architecture guard for touched file size and forbidden direct source path joins. Searches run: `rg 'module.*size|700|resolveSourceFile' src --glob '*.test.ts'`. Add narrow tests for the touched surface only.

## Quality Map

### Duplication and parallel implementation

- `src/config/loader.ts` `loadConfigFileWithStatus` and `readGlobalSources`, `src/cli/commands/index-cmd.ts` `indexCommand`, `src/cli/commands/init-cmd.ts` `initCommand`, and `src/cli/commands/config-cmd.ts` `initCommand` compute the global home independently. Disposition: refactor during the home slice. All consume `resolveMdmHome`.
- `src/index/types.ts` `getIndexPaths`, embedding namespace path helpers, `HnswVectorStore` path methods, `createBM25Store`, `bm25IndexExists`, `src/search/cross-encoder.ts` `rerank`, `src/cli/commands/search.ts` reranker initialization, and `src/cli/utils.ts` index discovery append `.mdm` independently. Disposition: refactor during the index directory slice. All DB paths consume `dbIndexDir` or `getIndexPaths`; legacy import helpers alone retain `.mdm`.
- Boundary checks are repeated by `src/mcp/adapter.ts` `resolveAndValidatePath` and `src/index/indexer.ts` `walkDirectory` and `resolveInternalLink` using string prefix tests. Disposition: refactor during canonical identity. Extract a neutral boundary aware predicate.
- Source file reconstruction is repeated in every caller listed in the Reuse Map. Disposition: refactor during canonical migration. All call `resolveSourceFile`.
- File content caches in `src/duplicates/detector.ts`, `src/embeddings/semantic-search-pipeline.ts`, and `src/cli/commands/search.ts` are similar but have distinct error and result policies. Disposition: defer cache unification. Their path resolution still converges now.

### Boundary and design issues

- `src/index/storage.ts` `IndexStorage.rootPath` represents both corpus root and storage root. A consolidated DB requires separate `sourceRoot` and `indexRoot`. Disposition: refactor first in the storage slice.
- `src/index/types.ts` `INDEX_DIR` represents both the active DB root and the legacy per project import directory. Disposition: refactor first. Replace it with explicit DB and legacy owners.
- `src/index/indexer.ts` `buildIndex` stores root relative keys while every downstream source read reconstructs them from a root. Changing only the stored string would misread absolute keys. Disposition: one atomic canonical key slice covering schemas, writers, readers, vector metadata, BM25 metadata, and migration.
- `src/parser/parser.ts` `parse` hashes the supplied path into document IDs. Canonicalize and deduplicate hardlinks before parsing so the surviving key deterministically drives new IDs.
- `src/index/indexer.ts` `resolveInternalLink` returns a root relative string and accepts missing targets. Missing targets have no realpath or inode, so they cannot satisfy the canonical document key contract. Disposition: decision needed below.
- `src/cli/utils.ts` `findIndexRoot` and `getIndexInfo` assume a project or parent `.mdm`. Disposition: remove the parent walk and inspect the selected DB home.
- `src/search/cross-encoder.ts` `rerank` chooses a model cache from `process.cwd()`, while explicit initialization uses the searched directory. Disposition: refactor during the home slice to one DB cache location.

### Dead code and obsolete paths

- `src/config/schema.ts` `IndexConfig.indexDir` and `PathsConfig.cacheDir` are validated and displayed but never consumed by runtime storage. Disposition: remove during the index directory slice. DB home owns both paths.
- `src/index/storage.ts` `IndexConfig`, `loadConfig`, and `saveConfig` preserve one `rootPath` in `config.json`. The v2.2 DB layout has no single source root or `config.json`. Disposition: remove during storage separation; use structural index existence.
- `src/cli/commands/init-cmd.ts` `initLocal`, `.mdm` gitignore mutation, and `src/cli/commands/index-cmd.ts` the local index sentinel create project indexes forbidden by Section 5. Disposition: remove during CLI home wiring. Local init may create project config only.
- `src/cli/utils.ts` `findIndexRoot` is a legacy per project index discovery path. Disposition: remove during CLI home wiring.

### Sizing

- `src/embeddings/embedding-namespace.ts` is 947 lines and `src/embeddings/vector-store.ts` is 823 lines. Disposition: refactor first, before DB path edits.
- `src/index/indexer.ts` is 855 lines, `src/search/searcher.ts` is 845 lines, and `src/cli/commands/search.ts` is 1316 lines. Canonical migration touches all three. Disposition: refactor first, before source resolution edits.
- `src/index/indexer.ts` `buildIndex`, `src/search/searcher.ts` `searchContent`, and the search command Effect handler exceed the approximate 150 line function limit. Disposition: decompose by ownership in the same mechanical refactor commits.
- `src/config/loader.test.ts` is 696 lines. Disposition: add new config tests in a new focused file.

### Grooming recommendation

Refactor first. Mechanical module extraction must keep public exports stable and pass focused existing tests before home or canonical behavior changes. Then remove obsolete local index paths and dead config during the relevant behavior slices. Cache unification and unrelated oversized files remain outside this plan.

## Surface Gate

### Reuse dispositions

- Reuse `loadTomlFileWithStatus`, `mergePartials`, `readEnvVars`, `mergeWithDefaults`, and config validation. No second loader.
- Reuse `getIndexPaths`, `createStorage`, structural JSON writers, embedding namespace paths, vector metadata codec, BM25 store, and HNSW cache after separating their source and DB root inputs.
- Reuse parser path based IDs by supplying the canonical key before parse.
- Reuse the MCP boundary algorithm by extracting its neutral predicate to the lower DB canonical boundary.
- Reuse every existing source content pipeline and replace only its path reconstruction with `resolveSourceFile`.

### Quality dispositions

- Refactor first: the five oversized touched source files and their oversized functions.
- Refactor during: home duplication, index path duplication, source path joins, and boundary prefix checks.
- Remove during: dead index path config, structural `config.json`, local `.mdm` init and sentinel, and parent index discovery.
- Defer: file content cache unification because error semantics differ and it does not block the canonical resolver.

### Decision needed

Choose the persisted representation for unresolved internal links. Recommended: resolved `LinkIndex.forward` and `LinkIndex.backward` values use `DocumentKey`; `LinkIndex.broken` uses a separate absolute, tilde expanded, lexically normalized `DeclaredPath` because a missing target has no realpath or inode. This avoids fabricating a canonical document identity.

## Plan

1. Add narrow architecture tests, then mechanically decompose every oversized touched module while preserving exports and behavior.
2. Add `resolveMdmHome`, `dbIndexDir`, and explicit legacy index directory ownership. Separate source and DB roots in storage and route every DB path through the abstraction.
3. Replace local or global config selection with ordered per key merging: home, portable project, local project, environment, then CLI. Wire every home consumer to `resolveMdmHome`.
4. Remove local project index creation, parent index discovery, dead index path config, and structural single root config.
5. Add canonical document key primitives, inode identity, case comparison, deterministic hardlink grouping, and the neutral boundary predicate.
6. Version structural, vector, and BM25 persistence for canonical keys. Provide an atomic migration primitive for Plan 2 ingest and import.
7. Canonicalize and hardlink deduplicate before parsing. Store the selected key across documents, sections, resolved links, vectors, BM25, CLI results, and MCP references.
8. Replace every direct source path join with `resolveSourceFile`. Add structural and behavioral regression tests.
9. Run focused tests after each slice, then the complete package gates.

## Tests and Gates

- Focused refactor gates: `pnpm exec vitest run src/architecture/db-foundation-boundaries.test.ts src/embeddings/embedding-namespace.test.ts src/embeddings/vector-store.test.ts src/index/indexer.test.ts src/search/searcher.test.ts src/cli/cli.test.ts`.
- Home and config gate: `pnpm exec vitest run src/home.test.ts src/config/config-precedence.test.ts src/cli/commands/config-cmd.test.ts src/cli/commands/init-cmd.test.ts src/cli/commands/index-sentinel.test.ts`.
- Canonical identity gate: `pnpm exec vitest run src/db/canonical.test.ts src/db/canonical-migration.test.ts src/index/indexer.test.ts src/index/storage.test.ts src/search/searcher.test.ts src/duplicates/detector.test.ts src/embeddings/vector-store.test.ts`.
- Direct join absence gate: `rg -n 'path\.join\([^)]*(documentPath|docPath|r\.documentPath)' src`. Expected exit code: 1.
- Size gate: `wc -l src/embeddings/embedding-namespace.ts src/embeddings/vector-store.ts src/index/indexer.ts src/search/searcher.ts src/cli/commands/search.ts` plus every new split module. Every listed file must be at most 700 lines.
- Repository tests: `pnpm test`.
- Type gate: `pnpm typecheck`.
- Build gate: `pnpm build`.
- Formatting and lint gate from `package.json`: `pnpm check`.
- Package quality gate: `pnpm quality`.
