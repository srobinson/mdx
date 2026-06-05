---
title: Federated search design for markdown-matters
type: research
tags: [markdown-matters, mdm, federation, semantic-search, mcp, architecture]
summary: mdm should add a named registry plus project mounts and reuse indexes through search-time multi-index merge.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-21
updated: 2026-06-21
---

## Executive Summary

markdown-matters already has per-root `.mdm/` structural indexes, provider/model/dimension embedding namespaces, CLI search, and MCP search. The missing layer is project-level composition over already-built indexes, with source-qualified federated results.

Full design artifact: `/Users/alphab/.mdx/TMP/mdm-federated-design--analyst.md`.

## Project Metadata

- Language: TypeScript ESM.
- Runtime: Node `>=18.0.0`.
- Build: `tsup`, `pnpm build`, `pnpm test`, `pnpm typecheck`.
- Key dependencies: Effect, `@effect/cli`, MCP SDK, hnswlib-node, OpenAI SDK, wink BM25, chokidar, smol-toml.
- fmm: `.fmm.db` present. `fmm validate` passed on 2026-06-21.

## Architecture

- Storage is hardcoded under `.mdm`: `config.json`, `indexes/documents.json`, `indexes/sections.json`, `indexes/links.json`, and cache paths. See `src/index/types.ts:getIndexPaths`.
- Embeddings are namespaced under `.mdm/embeddings/<provider>_<model>_<dimensions>/` with `.mdm/active-provider.json`. See `src/embeddings/embedding-namespace.ts`.
- Config resolution is local `.mdm.toml`, then `~/.mdm/.mdm.toml`, then defaults. See `src/config/loader.ts:loadConfigFileWithStatus` and `loadDetailed`.
- `[[sources]]` exists as a raw global config half-step for `mdm init --global` and `mdm index --all`, not as a project search composition model. See `src/config/loader.ts:readGlobalSources` and `src/cli/commands/index-cmd.ts:indexCommand`.
- CLI search resolves one index root and calls single-root hybrid, keyword, or semantic search. See `src/cli/commands/search.ts:searchCommand`.
- MCP roots itself in `process.cwd()` and passes that root to each tool handler. `md_search` is semantic-only today. See `src/mcp/server.ts:main`, `src/mcp/handlers.ts:handleMdSearch`.

## Key Patterns

- Keep built indexes beside the markdown they describe.
- Add a thin federation layer rather than a consolidated index.
- Use a named global registry and project mounts.
- Default search scope should be local plus configured project mounts when federation is enabled. Without federation config, preserve current local behavior.
- Merge at search time with rank-based RRF. Preserve raw similarity for diagnostics.
- Strictly require provider, model, and dimensions compatibility in the first semantic federation slice.

## Detailed Findings

Recommended first slice:

1. Add `FederationConfig` and project `[[federation.mounts]]`.
2. Implement `src/federation/resolve.ts` for local plus direct mounted roots.
3. Implement `src/federation/search.ts` for semantic fanout over compatible roots.
4. Merge results by RRF and return source-qualified `mdm://<index>/<path>#<sectionId>` URIs.
5. Wire CLI and MCP to the same service only when federation is active.
6. Use `/Users/alphab/.mdx` as the first mounted reuse target. The live index already has `openai_text-embedding-3-small_512` and should not be re-indexed.

## Dependencies

Critical dependencies are hnswlib-node for vector search, Effect for typed error workflows, MCP SDK for server tools, and smol-toml for config. None block the first federation slice.

## Relevance to Helioy

This directly supports Helioy's desired knowledge layer: projects can search their own markdown plus `~/.mdx` and selected project indexes without moving files. The design keeps source ownership local and gives agents a unified search surface through both CLI and MCP.

## Open Questions

- Should `[[sources]]` be removed immediately or kept as migration input?
- Should `index.indexDir` be wired before federation or deferred?
- Should MCP `md_context` require `mdm://` URIs for mounted contexts?
