# Markdown Matters release re-smoke

Date: 2026-07-22

Branch: `design/federated-knowledge-layer`

Head: `3dfe8046282f8ba7dfdcecf078c71559c60691de`

Binary: `node dist/cli/main.js`, built locally from the head above

Isolated home: `/tmp/mdm-resmoke`

Mixed corpus: `/tmp/mdm-resmoke-corpus`

## Verdict

Overall: **BLOCKED**

| Section | Result | Summary |
|---|---|---|
| A. Wikilinks | PASS | Mixed syntax graph, backlinks, ambiguity, broken link, section edge, and heading regression all verified. |
| B. Standard links | PASS | Pure standard link and backlink resolve correctly. |
| C. Smokefix | FAIL | Generation publication semantics pass. Embedding provider query is blocked because `OPENAI_API_KEY` is unavailable after the requested shell setup. |
| D. Path coherence and Lever 1 | PASS | Scoped success, filter miss, query miss, and ordinary success guidance verified. |
| E. Embed and search | FAIL, blocked | First embed command exits 3 before vector creation because `OPENAI_API_KEY` is unavailable. |
| F. Broad real corpus | FAIL, blocked | Deliberately not run after the section C failure, as required by the stop condition. |

Tally: 3 PASS, 3 FAIL. Sections E and F are blocked by the section C failure.

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

## C. Smokefix: FAIL

Generation publication checks passed:

1. Before the no-op refresh, `current` was `gen-1`.
2. A no-op `mdm index` indexed zero documents, skipped all 11 as unchanged, reported `mutation.structural: false`, and left `current` at `gen-1`.
3. `mdm index --force` reprocessed all 11 documents and advanced `current` to `gen-2`, even though the logical structural mutation was false.

The configured provider query could not be verified because the required key is unavailable. The requested setup was run in both noninteractive and PTY shells:

```text
source /Users/alphab/.config/zsh/.zshrc
```

`OPENAI_API_KEY` remained absent. The key was also absent from the tmux global environment and launchctl environment.

Reproduction:

```text
source /Users/alphab/.config/zsh/.zshrc
MDM_HOME=/tmp/mdm-resmoke node dist/cli/main.js index --embed --json --pretty
```

Result:

```text
exit: 3
Error [E300]: OPENAI_API_KEY not set

export OPENAI_API_KEY=your-api-key
Or add to .env file in project root
```

The failed embed attempt did not publish a new generation. `current` remained `gen-2`.

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

## E. Embed and search: FAIL, blocked

Vector creation could not start because the active default OpenAI provider has no available `OPENAI_API_KEY`. No keyword, semantic, and hybrid post-embed comparison was attempted after the stop condition triggered.

## F. Broad real corpus: FAIL, blocked

The mandated report is the only write under `~/.mdx`. The real `~/.mdm` home was left untouched. The required full rebuild, embedding refresh, count confirmation, and hybrid search were not attempted after the section C failure.

## Repository integrity

The repository remains at the expected head. The tracked tree is clean. The three pre-existing untracked user paths remain unchanged:

```text
.serena/
LESSONS.md
markdown-matters.code-workspace
```
