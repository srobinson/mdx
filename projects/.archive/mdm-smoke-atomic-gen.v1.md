# MDM Atomic Generation Live Smoke Report

Date: 2026-07-21

Verdict: **BLOCKED, 5 of 7 checks passed**

Repository: `/Users/alphab/Dev/LLM/DEV/helioy/markdown-matters`

Branch: `design/federated-knowledge-layer`

Head: `29247fe5533b2f93e56c802fcaad8ff63a4b7d71`

Execution surface: built CLI and built MCP server on the real filesystem. No Vitest invocation was used.

Isolation:

- Temporary home root: `/private/tmp/mdm-smoke-home.KkFptp`
- `MDM_HOME`: `/private/tmp/mdm-smoke-home.KkFptp/mdm-home`
- Temporary corpus: `/private/tmp/mdm-smoke-corpus.GH3G2y`
- Real user home check: `/Users/alphab/.mdm` was absent.
- Cleanup check: both temporary roots reported `exists=false` after the run.

## Bounded result

PASS: INDEX + LAYOUT: Initial publish created `gen-1`, a `current` pointer containing exactly `gen-1`, manifest, structural indexes, BM25 artifacts, four vectors, active provider metadata, and lease directories.

FAIL: SEARCH: Keyword search and both ignore mechanisms worked. Wiki links produced zero links and zero backlinks. Hybrid search ignored a valid active vector namespace and returned keyword only with `embeddingsAvailable: false`. Semantic and hybrid results also omitted line numbers.

PASS: EDIT TO FLIP: Editing one section published `gen-2`, flipped `current`, returned the new term at line 3, removed the old term, changed the document hash, and changed only the rebuilt section vector request.

PASS: REAPER: Old generations entered the grace gate and were removed after the configured grace period. Final inspection contained only the live generation and an empty staging directory.

PASS: CONCURRENCY AND PER REQUEST LEASE: One running built MCP server observed `gen-3`, stayed alive while a separate CLI process published `gen-4`, then observed `gen-4` and returned the updated heading.

PASS: DURABILITY SANITY: An index was interrupted after its embedding request started. `current` remained `gen-5`, no `gen-6` was published, staging was empty, and every current artifact remained regular and nonempty.

FAIL: IDEMPOTENCE: An unchanged refresh reported zero documents and zero sections indexed but advanced `current` from `gen-4` to `gen-5`.

## Blocking findings

### 1. Wiki links are not indexed

The requested corpus used `[[docs/guide]]`, `[[README]]`, and `[[notes/target]]`.

Initial index output reported `linksIndexed: 0` and `totalLinks: 0`. Public `links` and `backlinks` commands both returned empty arrays.

Expected: cross document wiki links resolve in both directions.

Observed: no link graph edges were created.

### 2. Hybrid search ignores active embeddings

The active namespace contained four valid vectors. `mdm stats` and `mdm embeddings list` both reported them. Direct semantic search with `--provider ollama` returned semantic matches from the active namespace.

The equivalent hybrid command with `--provider ollama` reported:

```json
{
  "semanticResults": 0,
  "keywordResults": 1,
  "combinedResults": 1,
  "bm25Available": true,
  "embeddingsAvailable": false,
  "sources": ["keyword"]
}
```

Expected: hybrid search combines semantic and keyword results.

Observed: the semantic side was unavailable despite a valid active namespace.

### 3. Custom embedding base URL is ignored by CLI query generation

Generation 1 vector metadata persisted:

```json
{
  "provider": "openai",
  "providerModel": "smoke-embed",
  "providerBaseURL": "http://127.0.0.1:57391/v1",
  "dimensions": 512,
  "vectorCount": 4
}
```

Direct semantic search then contacted the public OpenAI endpoint and failed:

```text
Error [E319]: Embedding generation failed
  401 Incorrect API key provided: smoke-key. You can find your API key at https://platform.openai.com/account/api-keys.
```

The same failure remained when `MDM_EMBEDDINGS_BASEURL` was set. MCP did honor its loaded config base URL, so the per request lease check was completed with the local Ollama transport.

### 4. Unchanged refresh publishes a new generation

Before the unchanged refresh, `current` was `gen-4`.

The command reported:

```json
{
  "documentsIndexed": 0,
  "sectionsIndexed": 0,
  "linksIndexed": 0,
  "totalDocuments": 4,
  "totalSections": 4,
  "totalLinks": 0,
  "duration": 5,
  "errors": [],
  "skipped": {
    "unchanged": 4,
    "excluded": 2,
    "hidden": 0,
    "total": 6
  }
}
```

After the command, `current` contained `gen-5`.

Expected: the content hash short circuit leaves `current` unchanged.

Observed: an empty refresh published a new generation.

## Generation timeline

| Generation | Cause | Result |
|---|---|---|
| `gen-1` | Initial corpus index with embeddings | Published complete artifact set |
| `gen-2` | Edited `SAPPHIRE-V1` to `EMERALD-V2` | Published, current flipped, one vector rebuilt |
| `gen-3` | Switched active provider to the local Ollama transport | Published four Ollama vectors for MCP smoke |
| `gen-4` | Separate process edited heading and term during live MCP session | Published, same MCP server observed update |
| `gen-5` | Unchanged refresh | Published unexpectedly, idempotence failure |
| `gen-6` | Delayed embedding request interrupted with `Ctrl+C` | Never published, current stayed `gen-5` |

## Setup and build evidence

Repository check:

```text
## design/federated-knowledge-layer...origin/design/federated-knowledge-layer
?? LESSONS.md
29247fe (HEAD -> design/federated-knowledge-layer, origin/design/federated-knowledge-layer) docs: align CLI guidance with MDM_HOME generation model (#69)
```

Build command:

```sh
npx --yes pnpm@10.28.0 build
```

Build output:

```text
> markdown-matters@0.3.4 build /Users/alphab/Dev/LLM/DEV/helioy/markdown-matters
> tsup src/cli/main.ts src/mcp/server.ts src/index.ts --format esm --dts --external @huggingface/transformers

CLI Building entry: src/index.ts, src/cli/main.ts, src/mcp/server.ts
CLI Using tsconfig: tsconfig.json
CLI tsup v8.5.1
CLI Target: es2022
ESM Build start
ESM dist/chunk-ZBHW5YOT.js     2.97 KB
ESM dist/index.js              3.65 KB
ESM dist/init-toml-S3NANOKN.js 155.00 B
ESM dist/mcp/server.js         17.46 KB
ESM dist/chunk-RCY24ODN.js     1.18 KB
ESM dist/cli/main.js           193.15 KB
ESM dist/chunk-TRD3ME32.js     33.17 KB
ESM dist/chunk-C2T7BYIS.js     213.81 KB
ESM dist/chunk-CXEISPBQ.js     17.57 KB
ESM Build success in 81ms
DTS Build start
DTS Build success in 5015ms
DTS dist/cli/main.d.ts        20.00 B
DTS dist/mcp/server.d.ts      3.14 KB
DTS dist/index.d.ts           35.84 KB
DTS dist/schema-Cvqn9Inc.d.ts 4.65 KB
```

## Corpus

```text
/private/tmp/mdm-smoke-corpus.GH3G2y/.gitignore
/private/tmp/mdm-smoke-corpus.GH3G2y/.mdmignore
/private/tmp/mdm-smoke-corpus.GH3G2y/README.md
/private/tmp/mdm-smoke-corpus.GH3G2y/docs/guide.md
/private/tmp/mdm-smoke-corpus.GH3G2y/ignored-by-mdmignore/hidden.md
/private/tmp/mdm-smoke-corpus.GH3G2y/nested/ignored/secret.md
/private/tmp/mdm-smoke-corpus.GH3G2y/nested/visible/reference.md
/private/tmp/mdm-smoke-corpus.GH3G2y/notes/target.md
```

Ignore controls:

```text
.gitignore:
nested/ignored/

.mdmignore:
ignored-by-mdmignore/
```

## Check 1: Index and layout

Command:

```sh
MDM_HOME=/private/tmp/mdm-smoke-home.KkFptp/mdm-home \
OPENAI_API_KEY=smoke-key \
node /Users/alphab/Dev/LLM/DEV/helioy/markdown-matters/dist/cli/main.js \
  index /private/tmp/mdm-smoke-corpus.GH3G2y \
  --embed \
  --provider openai \
  --provider-base-url http://127.0.0.1:57391/v1 \
  --provider-model smoke-embed \
  --json --pretty
```

Output:

```text
Adding /private/tmp/mdm-smoke-corpus.GH3G2y and refreshing manifest index...
{
  "documentsIndexed": 4,
  "sectionsIndexed": 4,
  "linksIndexed": 0,
  "totalDocuments": 4,
  "totalSections": 4,
  "totalLinks": 0,
  "duration": 16,
  "errors": [],
  "skipped": {
    "unchanged": 0,
    "excluded": 2,
    "hidden": 0,
    "total": 2
  }
}
```

Embedding transport output:

```text
EMBED model=smoke-embed inputs=4 dimensions=512 format=base64
```

Initial pointer and manifest:

```text
current="gen-1"
manifest:
[[dir]]
path = "/private/tmp/mdm-smoke-corpus.GH3G2y"
```

Initial tree:

```text
/private/tmp/mdm-smoke-home.KkFptp/mdm-home
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/current
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/active-provider.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/bm25.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/bm25.meta.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/embeddings
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/embeddings/openai_smoke-embed_512
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/embeddings/openai_smoke-embed_512/vectors.bin
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/embeddings/openai_smoke-embed_512/vectors.meta.bin
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/indexes
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/indexes/documents.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/indexes/links.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/indexes/sections.json
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/leases
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/gen-1/leases/open
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/manifest.toml
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/staging
```

## Check 2: Search, ignore filtering, and links

Keyword command output:

```text
Using index from 2026-07-21 17:37
  Sections: 4
  Embeddings: yes (4 vectors)

[keyword] Content search: "ORBITAL-ALPHA"
Results: 1

  /private/tmp/mdm-smoke-corpus.GH3G2y/README.md:1
    # Atomic Generation Smoke (42 tokens)

    2:
  > 3: The root marker is ORBITAL-ALPHA.
    4:
```

Hybrid output with OpenAI active namespace:

```json
{
  "mode": "hybrid",
  "modeReason": "--mode hybrid",
  "query": "cobalt launcher",
  "stats": {
    "mode": "hybrid",
    "modeReason": "--mode hybrid",
    "semanticResults": 0,
    "keywordResults": 1,
    "combinedResults": 1,
    "bm25Available": true,
    "embeddingsAvailable": false,
    "reranked": false,
    "totalAvailable": 1
  },
  "results": [
    {
      "path": "/private/tmp/mdm-smoke-corpus.GH3G2y/docs/guide.md",
      "heading": "Operations Guide",
      "score": 0.01639344262295082,
      "bm25Score": 2.609,
      "sources": ["keyword"]
    }
  ]
}
```

After switching to a local Ollama active namespace, direct semantic search succeeded with two results. It returned `Atomic Generation Smoke` at similarity `0.6089716124534607` and `Mutable Target` at similarity `0.23860907554626465`.

The equivalent hybrid search still degraded:

```json
{
  "semanticResults": 0,
  "keywordResults": 1,
  "combinedResults": 1,
  "bm25Available": true,
  "embeddingsAvailable": false,
  "sources": ["keyword"]
}
```

Git ignored query:

```json
{
  "mode": "keyword",
  "query": "NEVER-INDEX-GIT-IGNORED",
  "results": []
}
```

MDM ignored query:

```json
{
  "mode": "keyword",
  "query": "NEVER-INDEX-MDM-IGNORED",
  "results": []
}
```

Outgoing links:

```json
{
  "file": "/private/tmp/mdm-smoke-corpus.GH3G2y/README.md",
  "links": []
}
```

Backlinks:

```json
{
  "file": "/private/tmp/mdm-smoke-corpus.GH3G2y/docs/guide.md",
  "backlinks": []
}
```

## Check 3: Edit, flip, and vector reconciliation

Generation 1 target vector summary:

```json
{
  "sectionId": "6b9b08fe31fa-mutable-target-L1",
  "documentHash": "4f50dc958d917c41",
  "embeddingSha256": "ca435fce4c458ccc7a4a6c278ce348d104194c3edc3ecfb12ccfdfe82209d437",
  "providerBaseURL": "http://127.0.0.1:57391/v1",
  "vectorCount": 4
}
```

Edited content:

```text
SAPPHIRE-V1 -> EMERALD-V2
```

Reindex output:

```text
Refreshing manifest index...
{
  "documentsIndexed": 1,
  "sectionsIndexed": 1,
  "linksIndexed": 0,
  "totalDocuments": 4,
  "totalSections": 4,
  "totalLinks": 0,
  "duration": 15,
  "errors": [],
  "skipped": {
    "unchanged": 3,
    "excluded": 2,
    "hidden": 0,
    "total": 5
  }
}
```

Embedding transport output:

```text
EMBED model=smoke-embed inputs=1 dimensions=512 format=base64
```

Generation 2 target vector summary:

```json
{
  "sectionId": "6b9b08fe31fa-mutable-target-L1",
  "documentHash": "f70cf3a5e4818ca3",
  "embeddingSha256": "4f30a14b758a6447c1a7dfa9fda86b6ce8139b2ae774c9b4f3fbf0bb85e45064",
  "providerBaseURL": "http://127.0.0.1:57391/v1",
  "vectorCount": 4
}
```

Pointer and generations immediately after flip:

```text
current="gen-2"
entries=["current","gen-1","gen-2","manifest.toml","staging"]
```

New content search:

```text
[keyword] Content search: "EMERALD-V2"
Results: 1

  /private/tmp/mdm-smoke-corpus.GH3G2y/notes/target.md:1
    # Mutable Target (41 tokens)

    2:
  > 3: The release codename is EMERALD-V2.
    4:
```

Stale content search:

```json
{
  "mode": "keyword",
  "query": "SAPPHIRE-V1",
  "results": []
}
```

## Check 4: Reaper

Generation 1 initially entered the expected grace gate:

```text
gen-1/leases/closed type=Directory
gen-1/leases/.reap-state = ready
```

After the grace interval and subsequent real CLI and MCP reads, generation 1 was removed. Final state after all checks:

```text
current=gen-5
generations=gen-5
staging=[]
```

## Check 5: Same server MCP lease

The client spawned the real server:

```text
node /Users/alphab/Dev/LLM/DEV/helioy/markdown-matters/dist/mcp/server.js
```

The server received `MDM_HOME=/private/tmp/mdm-smoke-home.KkFptp/mdm-home` and the local Ollama embedding configuration.

First request on the live server:

```text
MCP_BEFORE generation=gen-3 result={"content":[{"type":"text","text":"Found 1 results for \"EMERALD-V2\":\n\n1. **Mutable Target** (23.5% match)\n   /private/tmp/mdm-smoke-corpus.GH3G2y/notes/target.md"}]}
MCP_READY_FOR_FLIP
```

A separate CLI process edited the heading and term, then published generation 4:

```text
Refreshing manifest index...
{
  "documentsIndexed": 1,
  "sectionsIndexed": 1,
  "linksIndexed": 0,
  "totalDocuments": 4,
  "totalSections": 4,
  "totalLinks": 0,
  "duration": 13,
  "errors": [],
  "skipped": {
    "unchanged": 3,
    "excluded": 2,
    "hidden": 0,
    "total": 5
  }
}
```

Second request on the same live server:

```text
MCP_AFTER generation=gen-4 result={"content":[{"type":"text","text":"Found 1 results for \"TOPAZ-V3\":\n\n1. **MCP Refreshed Target** (17.2% match)\n   /private/tmp/mdm-smoke-corpus.GH3G2y/notes/target.md"}]}
MCP_SERVER_PID=42366
MCP_CLOSED_CLEANLY
```

Observed generations: `gen-3` then `gen-4` on the same MCP process.

## Check 6: Durability sanity and interrupted publish

Before interruption, `current` contained `gen-5`.

The source was changed to `INTERRUPT-PENDING`, then index was pointed at a local embedding endpoint with a 15 second response delay. The endpoint confirmed that the production index process reached the embedding phase:

```text
EMBED model=smoke-embed inputs=1 dimensions=512 format=base64
```

The index process then received `Ctrl+C`.

Immediate inspection:

```text
current=gen-5
entries=["current","gen-4","gen-5","manifest.toml","staging"]
staging:
/private/tmp/mdm-smoke-home.KkFptp/mdm-home/staging
```

No `gen-6` existed. The source was restored to `TOPAZ-V3`.

Final keyword evidence:

```text
[keyword] Content search: "TOPAZ-V3"
Results: 1

  /private/tmp/mdm-smoke-corpus.GH3G2y/notes/target.md:1
    # MCP Refreshed Target (48 tokens)

  > 3: The release codename is TOPAZ-V3.
```

Interrupted content query:

```json
{
  "mode": "keyword",
  "query": "INTERRUPT-PENDING",
  "results": []
}
```

Final live generation validation:

```json
{
  "generation": "gen-5",
  "homeEntries": ["current", "gen-5", "manifest.toml", "staging"],
  "stagingEntries": [],
  "active": {
    "namespace": "ollama_smoke-embed_512",
    "provider": "ollama",
    "model": "smoke-embed",
    "dimensions": 512
  },
  "vectorMetadata": {
    "provider": "ollama",
    "model": "smoke-embed",
    "dimensions": 512,
    "count": 4
  },
  "counts": {
    "documents": 4,
    "sections": 4,
    "links": 0
  },
  "required": [
    { "file": "active-provider.json", "size": 159, "regular": true },
    { "file": "bm25.json", "size": 2535, "regular": true },
    { "file": "bm25.meta.json", "size": 77, "regular": true },
    { "file": "indexes/documents.json", "size": 2095, "regular": true },
    { "file": "indexes/sections.json", "size": 1803, "regular": true },
    { "file": "indexes/links.json", "size": 307, "regular": true },
    { "file": "embeddings/ollama_smoke-embed_512/vectors.bin", "size": 8864, "regular": true },
    { "file": "embeddings/ollama_smoke-embed_512/vectors.meta.bin", "size": 3695, "regular": true }
  ]
}
```

## Check 7: Idempotence

Before command:

```text
current=gen-4
```

Command:

```sh
MDM_HOME=/private/tmp/mdm-smoke-home.KkFptp/mdm-home \
node /Users/alphab/Dev/LLM/DEV/helioy/markdown-matters/dist/cli/main.js \
  index --embed --provider ollama --provider-model smoke-embed --json --pretty
```

Output:

```text
Refreshing manifest index...
{
  "documentsIndexed": 0,
  "sectionsIndexed": 0,
  "linksIndexed": 0,
  "totalDocuments": 4,
  "totalSections": 4,
  "totalLinks": 0,
  "duration": 5,
  "errors": [],
  "skipped": {
    "unchanged": 4,
    "excluded": 2,
    "hidden": 0,
    "total": 6
  }
}
```

After command:

```text
current=gen-5
generations=gen-3,gen-4,gen-5
```

The reaper later reduced this to the live `gen-5`, but the pointer advance itself is the idempotence failure.

## Cleanup and isolation proof

All CLI and MCP invocations that could read or write database state used the explicit isolated `MDM_HOME`. The one early harness invocation with a relative binary path failed in Node module resolution before application startup.

Real home check:

```text
path=/Users/alphab/.mdm absent
```

Temporary cleanup verification:

```text
/private/tmp/mdm-smoke-home.KkFptp exists=false
/private/tmp/mdm-smoke-corpus.GH3G2y exists=false
```

Repository check after cleanup:

```text
## design/federated-knowledge-layer...origin/design/federated-knowledge-layer
?? LESSONS.md
29247fe (HEAD -> design/federated-knowledge-layer, origin/design/federated-knowledge-layer) docs: align CLI guidance with MDM_HOME generation model (#69)
```

No tracked repository files were changed.
