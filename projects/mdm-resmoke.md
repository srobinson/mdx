# Markdown Matters release re-smoke

Date: 2026-07-22

Branch: `design/federated-knowledge-layer`

Head: `3dfe8046282f8ba7dfdcecf078c71559c60691de`

Binary: `node dist/cli/main.js`, built locally from the head above

Isolated home: `/tmp/mdm-resmoke`

Mixed corpus: `/tmp/mdm-resmoke-corpus`

## Verdict

Overall: **PASS**

| Section | Result | Summary |
|---|---|---|
| A. Wikilinks | PASS | Mixed syntax graph, backlinks, ambiguity, broken link, section edge, and heading regression all verified. |
| B. Standard links | PASS | Pure standard link and backlink resolve correctly. |
| C. Smokefix | PASS | No-op suppression, forced publication, and active provider query behavior all verified. |
| D. Path coherence and Lever 1 | PASS | Scoped success, filter miss, query miss, and ordinary success guidance verified. |
| E. Embed and search | PASS | Isolated vectors built and keyword, semantic, and hybrid searches returned the intended document. |
| F. Broad real corpus | PASS | Version 3 rebuild, embedding refresh, counts, and real hybrid search completed successfully. |

Tally: 6 PASS, 0 FAIL.

## Build gate

`git pull --ff-only` reported the branch was current at the expected head.

`pnpm install --frozen-lockfile` completed successfully with the lockfile unchanged.

`pnpm build` completed successfully. Both the ESM build and declaration build passed.

## A. Wikilinks: PASS

Initial command:

```text
MDM_HOME=/tmp/mdm-resmoke node dist/cli/main.js index /tmp/mdm-resmoke-corpus --json --pretty
```

Result:

```text
documentsIndexed: 11
sectionsIndexed: 12
linksIndexed: 11
totalDocuments: 11
totalSections: 12
totalLinks: 10
mutation.structural: true
```

The expected ambiguity diagnostics were reported. Bare `[[Note]]`, `[[Note|Readable alias]]`, and `[[Note#Heading]]` selected root `Note.md` over `folder/Note.md`. `[[Ambiguous]]` selected `near/Ambiguous.md` over `deep/nested/Ambiguous.md`, proving shortest path selection.

`mdm links Source.md --json` returned:

```text
Standard.md
Note.md
folder/Note.md
near/Ambiguous.md
```

This proves standard Markdown and wikilink edges coexist in the same source graph.

Backlink checks:

```text
backlinks Standard.md: HeadingLink.md, Source.md
backlinks Note.md: Source.md
backlinks Source.md: Note.md, Standard.md
```

The persisted edge for `[[Note#Heading]]` was:

```json
{
  "documentPath": "/private/tmp/mdm-resmoke-corpus/Note.md",
  "sectionId": "bb3d92b61ee1-heading-L3"
}
```

The persisted broken link state contained `/tmp/mdm-resmoke-corpus/Nope.md` in both `brokenBySource` and `broken`.

`mdm links HeadingLink.md --json` returned `Standard.md`, and `mdm backlinks Standard.md --json` returned `HeadingLink.md`. This verifies the standard link inside a heading regression.

## B. Standard links: PASS

The pure standard source contains only `[Only standard syntax](./PureTarget.md)`.

```text
mdm links PureStandard.md: PureTarget.md
mdm backlinks PureTarget.md: PureStandard.md
```

## C. Smokefix: PASS

Generation publication checks passed:

1. Before the no-op refresh, `current` was `gen-1`.
2. A no-op `mdm index` indexed zero documents, skipped all 11 as unchanged, reported `mutation.structural: false`, and left `current` at `gen-1`.
3. `mdm index --force` reprocessed all 11 documents and advanced `current` to `gen-2`, even though the logical structural mutation was false.

The key was loaded from the ancestor direnv environment at `/Users/alphab/Dev/LLM`:

```text
eval "$(direnv export zsh 2>/dev/null)"
```

The key presence check passed without exposing its value.

The isolated embedding refresh used the configured active provider and advanced `current` from `gen-2` to `gen-3`. `mdm stats` reported provider `openai`, model `text-embedding-3-small`, and 11 vectors. No provider override was supplied.

A semantic query for `how do astronomers navigate by stars` completed without a provider crash and returned `Note.md` with similarity `0.5268514752388`.

## D. Path coherence and Lever 1: PASS

Scoped keyword search for `scopefiltertoken` under `/tmp/mdm-resmoke-corpus/scope` returned only `/private/tmp/mdm-resmoke-corpus/scope/Inside.md`. The same term also exists in `Outside.md`, which did not leak into the result.

An empty path scope returned the friendly filter miss pointer:

```json
{
  "error": "No indexed documents found.",
  "path": "/private/tmp/mdm-resmoke-corpus/empty",
  "guidance": "Run: mdm index /private/tmp/mdm-resmoke-corpus/empty"
}
```

A corpus query miss returned:

```text
no matches for "zyzzyvaresmokemissing" across 11 indexed documents
```

A successful keyword search for `astrolabe` returned `Note.md`, heading `Heading`, line 5.

## E. Embed and search: PASS

`mdm index --embed` on the isolated corpus advanced `current` from `gen-2` to `gen-3`. Statistics after publication:

```text
documents: 11
sections: 12
vectors: 11
provider: openai
model: text-embedding-3-small
dimensions: 512
embedding tokens: 319
embedding cost: 0.00000638 USD
```

Post-embed search checks:

| Mode | Query | Evidence |
|---|---|---|
| Keyword | `astrolabe` | Returned `Note.md`, heading `Heading`, line 5. |
| Semantic | `how do astronomers navigate by stars` | Returned `Note.md` with similarity `0.5268514752388`. |
| Hybrid | `star navigation instrument` | Returned `Note.md`; embeddings and BM25 were both available. |

## F. Broad real corpus: PASS

Before rebuilding, the real home was at `gen-3` and the new binary reported the expected version mismatch: index version 3 required, version 2 found.

The version 3 structural command completed successfully:

```text
MDM_HOME=/Users/alphab/.mdm node dist/cli/main.js index /Users/alphab/.mdx --json --pretty
```

Result:

```text
documentsIndexed: 2186
sectionsIndexed: 37087
linksIndexed: 670
totalDocuments: 2186
totalSections: 37087
totalLinks: 587
errors: 0
excluded: 72
hidden: 39
mutation.structural: true
```

The rebuild published `gen-4`. Nine malformed frontmatter warnings included direct `mdm fix --write` guidance and were skipped. The index result itself contained no processing errors.

`mdm index --embed` then completed successfully. Compatible OpenAI vectors were already present in the rebuilt generation, so the refresh skipped all 2,186 unchanged documents and retained `gen-4` without another publication.

Final real statistics:

```text
documents: 2186
sections: 37087
total tokens: 11222561
vectors: 35222
provider: openai
model: text-embedding-3-small
dimensions: 512
embedding tokens: 7047254
embedding cost: 0.14094508000000003 USD
```

The final hybrid search for `atomic generation swap` completed with semantic and keyword channels available. It returned five results. The top result was `7.2 Atomic generation swap` in the federated knowledge layer design, with similarity `0.7134530711174011` and both semantic and keyword sources.

## Repository integrity

The repository remains at the expected head. The tracked tree is clean. The three pre-existing untracked user paths remain unchanged:

```text
.serena/
LESSONS.md
markdown-matters.code-workspace
```
