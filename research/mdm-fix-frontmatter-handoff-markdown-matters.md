---
title: mdm fix frontmatter handoff in markdown-matters
type: research
tags: [markdown-matters, mdm, frontmatter, cli, handoff]
summary: Bus handoff requested six local commits for mdm fix, but this session was read-only and only validated scope and branch state.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

A bus handoff on topic `mdm-fix-frontmatter` requested continuation of `mdm fix` work on branch `feat/mdm-fix-frontmatter`. I inspected the working tree and relevant symbols, then replied to the sender that this session is constrained read-only for target codebase edits and cannot create the requested commits.

## Project Metadata

- Project: `markdown-matters`
- Language: TypeScript
- Package manager: pnpm
- Structural index: fmm available, 166 indexed files and 45,426 LOC
- Active branch: `feat/mdm-fix-frontmatter`

## Architecture

Relevant files identified with fmm:

- `src/parser/parser.ts`: exports `parse` at lines 293 to 364 and `parseFile` at lines 372 to 396.
- `src/cli/commands/fix-cmd.ts`: exports `fixCommand` at lines 55 to 169.
- `src/parser/frontmatter-fix.ts`: exports `fixFrontmatter` at lines 35 to 96, with private repair helpers at lines 98 to 146.
- `src/parser/frontmatter-fix.test.ts`: test file for frontmatter repair logic.

The current `parse` implementation catches malformed YAML at `src/parser/parser.ts:306-316`, logs a warning at lines 313 to 315, and leaves `frontmatter = {}` with `markdownContent` unchanged after a parse failure.

The current `fixCommand` implementation accepts `path`, `--write`, `--json`, and `--pretty` at `src/cli/commands/fix-cmd.ts:55-69`, scans files at lines 74 to 92, writes changed files at lines 94 to 107, emits JSON at lines 109 to 125, and prints dry-run summaries at lines 127 to 165.

## Detailed Findings

Unread bus message from `mdmtest:general:1:1.1` asked this agent to perform these tasks, one commit each:

1. Add a `mdm fix --write` hint to malformed frontmatter warnings in `src/parser/parser.ts:314`.
2. Add per-file line diffs to `mdm fix` dry-run output in `src/cli/commands/fix-cmd.ts`, skipping diffs for `--json`.
3. Refuse `--write` on dirty tracked git files, add `--force` alias `-f`, and skip dirty checks during dry run.
4. At index time, strip malformed frontmatter fences from body content and try tolerant `yaml.parseDocument` recovery.
5. Commit the prior session's existing work first, then the four new tasks, for six local conventional commits total.

Observed working tree before any edits:

```text
## feat/mdm-fix-frontmatter
 M package.json
 M pnpm-lock.yaml
 M src/cli/commands/index.ts
 M src/cli/main.ts
?? src/cli/commands/fix-cmd.ts
?? src/parser/frontmatter-fix.test.ts
?? src/parser/frontmatter-fix.ts
```

Existing diff confirms `yaml` was added to `package.json` and `pnpm-lock.yaml`, `fixCommand` was exported from `src/cli/commands/index.ts`, and `fixCommand` was added to `src/cli/main.ts` subcommands.

## Dependencies

- `yaml ^2.8.0` is already present in the uncommitted `package.json` diff and locked as `2.8.3`.
- `gray-matter` remains the primary frontmatter parser in `src/parser/parser.ts`.
- `@effect/cli` drives command definitions in `src/cli/commands/fix-cmd.ts`.

## Relevance to Helioy

This work improves Markdown knowledge base hygiene by repairing malformed YAML frontmatter and reducing body index pollution when frontmatter is invalid. It is directly relevant to `~/.mdx` reliability and markdown indexing quality.

## Open Questions

- A writable implementation agent needs to apply the requested code changes and create the six local commits.
- The exact diff rendering format should be validated against CLI output conventions after implementation.
- Dirty git detection needs tests or a controlled integration check around tracked dirty, tracked clean, untracked, and non-git files.
