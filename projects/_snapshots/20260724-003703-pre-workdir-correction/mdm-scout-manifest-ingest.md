# MDM Manifest Ingest Scout

Baseline: `c15e8690f3aceba6dc768594336c8b2b26061d6d`

Scope: design Sections 6, 6.2, 6.3, and the existing Section 7.1 canonical identity. Source review was read only. The only repository change from this pass is the separately authorized plan document.

## Reuse Map

### Manifest parse and append

- Existing owner: none for `$MDM_HOME/manifest.toml`. `rg -n "manifest" src` returned no matches.
- Reusable parser: `src/config/loader.ts:88` `loadTomlFileWithStatus` already centralizes file existence, UTF-8 reading, and `smol-toml` parsing. Its result is hard typed as `PartialMdmConfig`, so manifest code must not cast through that config shape.
- Reusable dependency: `smol-toml@1.6.1` exports both `parse` and `stringify`. A neutral TOML file loader can be extracted once and reused by config and manifest owners. `stringify({ dir: [entry] })` can encode an appended block safely without hand escaping TOML strings.
- Reusable home owner: `src/home.ts:10` `resolveMdmHome` and `src/home.ts:31` `dbIndexDir` already select and create the active database home.
- Retired parallel implementation: `src/config/loader.ts:530` `GlobalSource`, `src/config/loader.ts:540` `readGlobalSources`, and `src/cli/commands/init-cmd.ts:49` `appendSource` still implement the retired `[[sources]]` model. Production has no caller for `readGlobalSources`; only its barrel export and one test remain. These must be deleted when the manifest owner lands.
- Searches run: `rg -n "manifest" src package.json`, `rg -n "\[\[sources\]\]|readGlobalSources|GlobalSource" src`, `rg -n "loadTomlFileWithStatus|parseToml|smol-toml" src`.

### Multi-directory walk with recurse and depth

- Existing owner: `src/index/file-discovery.ts:189` `discoverFiles` walks exactly one `rootPath`.
- Reusable core: `src/index/file-discovery.ts:94` `walkDirectory`, `src/index/file-discovery.ts:91` `isMarkdownFile`, the contained symlink guard using `isPathWithin`, and typed `DirectoryWalkError` handling.
- Missing capability: `FileDiscoveryOptions` has only `changedPaths` and `followSymlinks`. There is no directory list, `recurse`, current depth, or maximum depth.
- Required extension: retain one walk per manifest directory because recurse, depth, and ignore scope differ per entry. Aggregate all returned paths before canonical grouping. `recurse=false` and `depth=0` both mean top-level markdown only. A positive depth counts descended directory levels below the manifest path.
- Watch seam: `src/index/watcher.ts:79` is also one root and duplicates `isMarkdownFile` at line 76. Its static chokidar ignore conversion cannot represent nested inheritance. Manifest watching belongs to the later freshness work; Plan 2 should reject `--watch` rather than claim partial semantics.
- Searches run: `fmm outline src/index/file-discovery.ts`, `fmm deps src/index/file-discovery.ts --depth 2`, `rg -n "discoverFiles\(|isMarkdownFile" src`.

### Per-level ignore re-anchoring

- Existing owner: `src/index/ignore-patterns.ts:118` `createIgnoreFilter` with `ignore@7` and current type precedence `CLI/config > .mdmignore > .gitignore > defaults`.
- Current anchoring: root only. It reads one `.gitignore` and one `.mdmignore` from `rootPath`, adds their raw text to one `Ignore` instance, and tests every path relative to the walk root. Nested ignore files are never read.
- Minimal extension: preserve a scoped `ignore@7` instance for each ignore file. Test a candidate relative to the directory containing that file. Evaluate ancestor to descendant within the git tier, then ancestor to descendant within the mdm tier, then CLI/config. Use `Ignore.test()` so an explicit negation can override a lower or earlier decision. This avoids rewriting gitignore syntax by hand.
- Traversal rule: test a directory before loading its nested ignore files. If an ancestor excludes it, do not descend and do not read its ignore files. Pass a trailing slash when testing directories so `folder/` patterns work.
- Existing test gap: the directory-only test uses `build/`, but the built-in `build` rule independently makes `shouldIgnore('build')` true. A direct `ignore@7` probe showed `ignore().add('build/').ignores('build')` is false unless the directory candidate carries `/`. The test does not prove the intended behavior.
- Parallel implementation: `getChokidarIgnorePatterns` parses and converts patterns separately. It returns negations unchanged even though the comment says chokidar handles them differently. That path cannot match the required nested semantics and should remain outside Plan 2.
- Searches run: `fmm outline src/index/ignore-patterns.ts`, `rg -n "createIgnoreFilter|shouldIgnore|getChokidarIgnorePatterns|createFilterFunction" src`, plus a read-only `ignore@7` `test()` probe for directory and negation behavior.

### Content-hash incremental cache

- Structural owner: `src/index/storage.ts:279` `computeHash`; `src/index/index-build.ts:184` computes it; `src/index/types.ts:35` persists it on `DocumentEntry`.
- Structural key: the cache is keyed by canonical `DocumentKey`, then guarded by content hash, mtime, canonical aliases, comparison key, and inode identity in `sourceMatchesEntry`. Plan 1 already replaced relative keys. The cache survives this plan as long as the same canonical survivor is selected.
- Cross-root requirement: canonical grouping must receive the union of every root's discovered files. Sequential calls to `buildIndex` cannot guarantee the lexicographically least survivor or complete hardlink aliases across roots.
- Embedding defect: `src/embeddings/semantic-search-build.ts:395` loads only `getEmbeddedIds()`. `readSectionsToEmbed` skips an existing section ID at line 292. Section IDs derive from canonical path, heading, and line, not content. Editing section text without moving the heading leaves the ID unchanged, so the current code does not re-embed changed content.
- Required extension: persist each source document hash in `VectorEntry`, expose existing hashes by section ID, remove stale or hash-mismatched entries, and reuse only entries whose stored document hash equals `DocumentEntry.hash`.
- Searches run: `rg -n "computeHash|existing?.hash|getEmbeddedIds|embeddedIds" src`, `fmm outline src/parser/parser.ts`, `fmm outline src/embeddings/semantic-search-build.ts`.

### Canonical dedup and inode-aware membership

- Existing owner: `src/db/canonical.ts:144` `canonicalizeSourceFile`, line 187 `fileIdentityKey`, line 190 `selectCanonicalSource`, line 262 `belongsToAnyPrefix`, and line 267 `resolveSourceFile`.
- Existing ingest hook: `src/index/file-discovery.ts:59` `canonicalizeDiscoveredFiles` caches case sensitivity per device, groups by `(device,inode)`, calls `selectCanonicalSource`, keeps every discovered canonical and declared alias, and sorts survivors.
- Reuse decision: call `canonicalizeDiscoveredFiles` once on the union of all manifest discoveries. Do not create a second dedup implementation in the manifest layer.
- Membership: the stored `paths` and `identity` already retain hardlink membership aliases. A full manifest refresh must prune state by the discovered inode set so removed manifest roots, newly ignored files, and deleted files disappear from documents, sections, links, vectors, and BM25.
- Link seam: `resolveInternalLink` currently permits targets inside one root. Consolidated construction must pass all resolved manifest roots and resolve a link only when the target identity is in the discovered corpus. This permits links across manifest roots while keeping excluded or out-of-depth targets out of the graph.
- Searches run: `fmm outline src/db/canonical.ts`, `rg -n "canonicalizeDiscoveredFiles|fileIdentityKey|selectCanonicalSource|belongsToAnyPrefix" src`, and Plan 1 history from commits `a17ca25`, `c151d8c`, and `3a24104`.

### Consolidated write

- Structural owner: `src/index/index-build.ts:426` `buildIndex`, `src/index/index-state.ts:228` `saveIndexState`, and `src/index/storage.ts:239` `writeJsonFile`.
- Existing database target: CLI passes `dbIndexDir(resolveMdmHome({ create: true }))` as `indexRoot`, so all roots can share one storage location.
- Blocking single-root assumption: `buildIndex` performs discovery, canonical grouping, mutable-state reconciliation, parse, and save inside one call. Calling it once per root saves partial state repeatedly, does not prune manifest removals, and cannot dedup hardlinks across roots before survivor selection.
- Minimal hook: extract a corpus build phase that accepts all resolved roots and one canonicalized discovery. Keep `buildIndex(root, options)` as the single-root adapter for existing callers. Add `buildManifestIndex(manifest, options)` above it to discover each root, union paths, canonicalize once, prune stale state, parse once, and call `saveIndexState` once.
- BM25 owner: `src/index/bm25-build.ts:28` rebuilds from the structural indexes, but skips solely because a BM25 store exists. Manifest refresh must force a BM25 rebuild after the consolidated structural save until a BM25 content fingerprint exists.
- Embedding owner: `buildEmbeddings` already removes section IDs absent from the structural index and writes one namespaced store under the database root. After the document-hash fix, it can incrementally refresh the consolidated corpus without vector import.
- Atomicity seam: `saveIndexState` writes documents, sections, and links sequentially. Direct writes to `dbIndexDir(resolveMdmHome())` are accepted for Plan 2. Generation swap remains Section 7.2 work.
- Searches run: `fmm outline` and `fmm deps` for `index-build.ts`, `index-state.ts`, `storage.ts`, `bm25-build.ts`, and `semantic-search-build.ts`; `rg -n "buildIndex\(|buildBM25Index\(|buildEmbeddings\(" src`.

## Quality Map

### Duplication and parallel implementations

1. `[[sources]]` remains as a dead public config API and a live `mdm init` writer even though the spec retires it. Replace it with the manifest owner in the same task.
2. Markdown extension detection is duplicated in `file-discovery.ts` and `watcher.ts`. The watcher should import the existing exported helper.
3. Ignore semantics are implemented twice: `ignore@7` for indexing and hand converted chokidar globs for watching. The second path cannot express nested negation. Plan 2 should not expand it.
4. TOML file reading and parsing is embedded in the config loader. A second manifest reader would duplicate the same failure handling. Extract one neutral TOML document loader.
5. Legacy vector paths exist in `home.ts` and `embedding-namespace-paths.ts`; per-source vector import logic exists in `embedding-namespace-migration.ts`; JSON metadata auto-migration exists in `vector-store-codec.ts`. The spec explicitly forbids these compatibility paths.

### Boundary and design issues

1. `DocumentIndex.rootPath` and `IndexStorage.sourceRoot` encode one corpus root. A consolidated index has many source roots. Persistent index state should not nominate one root; the manifest owns corpus roots.
2. `buildIndex` owns both discovery and persistence. A manifest orchestration layer cannot aggregate before canonical dedup without extracting a corpus build seam.
3. Full non-force builds report missing stored aliases but retain them. Manifest source-of-truth refresh requires pruning everything absent from the complete discovery.
4. Link containment is one-root. Consolidated link resolution needs the full manifest root set and the discovered identity map.
5. `md_index` in `src/mcp/handlers.ts:203` directly calls the single-root builder and bypasses the manifest. It must route through the same append-and-refresh use case as the CLI.
6. `buildBM25Index` and embedding cost/build functions infer the active home internally while accepting a source root parameter. Plan 2 needs an explicit database index root at their orchestration boundary.

### Dead code and correctness risks

1. `readGlobalSources` has no production caller.
2. `createFilterFunction` is test-only.
3. `embedding-namespace-migration.ts` is exported but has no production caller. Its whole purpose conflicts with Sections 6.2 and 18.
4. `getLegacyVectorPath`, `getLegacyMetaPath`, and `getLegacyMetaJsonPath` exist only for the forbidden migration path and its tests.
5. The embedding delta cache can silently retain stale vectors when text changes but section identity stays stable.
6. The root-only directory ignore test is a false positive for `build/` because the default `build` rule masks the missing slash handling.
7. `getChokidarIgnorePatterns` preserves `!` strings without implementing negation semantics.

### Sizing

- All named index files are below 700 lines. Measured: `index-build.ts` 525, `file-discovery.ts` 218, `ignore-patterns.ts` 304, `index-state.ts` 262, `storage.ts` 400, `types.ts` 153, and `watcher.ts` 191.
- `src/cli/commands/index-cmd.ts` is 506 lines, but `indexCommand` spans 453 lines. It must be decomposed before manifest behavior is added.
- `src/embeddings/semantic-search-build.ts` is 540 lines, but `buildEmbeddings` spans 208 lines. The header claims the orchestrator is under the 150-line cap; it is not. Decompose it while adding content-hash reuse.
- No other under-limit owner needs structural movement for Plan 2.

### Grooming recommendation

1. Land a typed manifest owner and delete `[[sources]]` in one PR.
2. Extend the existing ignore and walk owners in place. Do not add a second walker or pattern engine.
3. Extract one corpus-build seam, then add the manifest orchestrator above it. Keep the stable `indexer.ts` facade.
4. Delete vector import and metadata migration paths. Add a narrow stale source-index cleanup with an active-home safety guard.
5. Make vector reuse document-hash aware before wiring consolidated embed.
6. Split CLI declaration, execution, output, and embedding UX before changing no-arg semantics.

## Plan

### Decisions needed

1. **Missing or empty manifest:** recommend failing `mdm index` with an actionable message. Do not silently index the current directory. `mdm index <dir>` creates or appends first.
2. **Depth conflict:** recommend accepting `depth=0` as top-level only and rejecting `recurse=false` with a positive `depth`. This keeps one unambiguous bound.
3. **Append representation:** recommend storing the absolute declared path, without realpath replacement, and treating the same lexical declared path as idempotent. This preserves symlink retarget detection and permits intentional aliases.
4. **Watch in Plan 2:** recommend rejecting `mdm index --watch` with manifest guidance. Correct multi-root watching and dynamic nested ignores belong to the later freshness plan.

### Ordered implementation

1. Add the neutral TOML loader and typed manifest read/append owner. Move `mdm init` registration to `manifest.toml` and delete every `[[sources]]` API and test.
2. Extend `ignore-patterns.ts` with scoped ancestor chains and `file-discovery.ts` with recurse and depth. Preserve type precedence and load nested files only after a directory passes ancestor filters.
3. Extract the complete-corpus build seam from `buildIndex`. Add `buildManifestIndex` to discover every manifest root, canonicalize the union once, prune stale state, resolve cross-root links by discovered inode, save once, and rebuild BM25 in the active db root.
4. Delete per-source vector import and JSON metadata compatibility. Remove each source's stale `.mdm` index before discovery, except when that path is the active database home.
5. Add `documentHash` to vector entries and reuse embeddings only when section ID and document hash match. Decompose the overlong embedding orchestrator during this change.
6. Decompose `index-cmd.ts`, make its path argument optional, append when present, refresh the whole manifest in every case, and route MCP `md_index` through the same use case. Reject Plan 2 watch mode. Pass the database root to cost, embedding, and BM25 operations.

### Tests and gates

- Manifest tests: missing file, valid defaults, tilde expansion, invalid entry, idempotent append, escaped paths, retired `[[sources]]` absence.
- Discovery tests: recurse false, depth 0/1/2, nested root-relative rules, nested negation, type precedence, ignored-directory short circuit, defaults, directory slash handling.
- Consolidation tests: two roots in one document index, overlap dedup, cross-root hardlink aliases, lexicographic survivor, manifest removal pruning, ignore-change pruning, cross-root links, one BM25 store.
- Freshness tests: unchanged structural files skip, changed content reparses, unchanged vectors reuse, same-ID changed content re-embeds, stale vector removal.
- Cleanup tests: old per-source `.mdm` deletion, active home never deleted, no migration or legacy vector symbols in production.
- CLI and MCP tests: no-arg refresh, path append plus full refresh, missing manifest error, optional argument behavior, no `[[sources]]`, watch rejection, active home writes only.
- Per task: focused Vitest file, then `npx --yes pnpm@10.28.0 typecheck`.
- Final gates: `npx --yes pnpm@10.28.0 test`, `typecheck`, `build`, and `check`; `git diff --check`; all touched and new files at most 700 lines; modified functions near 150 lines or less.
