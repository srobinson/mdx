# mdcontext: Security and QA Audit

**Date:** 2026-03-13
**Scope:** ~90 source files, ~42 test files

## Executive Summary

mdcontext is a well-structured TypeScript/Node.js tool with strong type safety (Effect-TS, strict tsconfig), a disciplined error taxonomy, and thoughtful separation of concerns. The security posture is above average for a developer tool of this scope. API key handling uses Effect's `Redacted` type, process spawning uses safe argument arrays, and directory traversal has a root boundary check in link resolution.

**3 high severity, 5 medium severity, 4 low severity findings.**

---

## HIGH Severity

### SEC-01: ReDoS via User-Supplied Regex

**Locations:**
- `src/search/searcher.ts:132` (heading filter)
- `src/search/searcher.ts:257` (content filter)
- `src/search/searcher.ts:270` (heading filter, content search)

User-supplied strings passed directly to `new RegExp()`. The MCP server's `md_keyword_search` tool exposes the `heading` parameter, documented as "(regex)". A catastrophic backtracking pattern like `(a+)+$` blocks the Node.js event loop indefinitely, freezing the entire MCP server process for all connected agents.

**Remediation:** Wrap in try/catch, enforce max pattern length (~200 chars), consider `safe-regex2` or escape user input for substring matching.

---

### SEC-02: MCP Server Path Traversal

**Locations:**
- `src/mcp/server.ts:271-273` (`md_context`)
- `src/mcp/server.ts:299-301` (`md_structure`)
- `src/mcp/server.ts:426-428` (`md_index`)
- `src/mcp/server.ts:459-461` (`md_links`)
- `src/mcp/server.ts:500-501` (`md_backlinks`)

All path-accepting handlers use:

```typescript
const resolvedPath = path.isAbsolute(filePath)
  ? filePath                        // accepts any absolute path
  : path.join(rootPath, filePath)   // ../../../etc/passwd works
```

No validation checks that the resolved path stays within `rootPath`. A malicious AI agent can invoke `md_context` with `path: "/etc/passwd"` or `path: "../../.ssh/id_rsa"` to read arbitrary files.

**Positive contrast:** `src/index/indexer.ts:175` correctly validates `resolved.startsWith(rootPath)`. Apply this pattern to all MCP handlers.

---

### SEC-03: Dynamic Code Execution via Config Files

**Location:** `src/config/file-provider.ts:136-137`

```typescript
const fileUrl = `file://${filePath}`
const module = await import(fileUrl)
```

The config loader performs dynamic `import()` on JS/TS files. `findConfigFile` (line 76-93) walks up the directory tree from cwd to filesystem root, testing six config file names at each level. A malicious `mdcontext.config.js` placed in any parent directory executes arbitrary code.

**Remediation:** Limit traversal to git root. Log which config file is loaded. Consider JSON-only for untrusted environments.

---

## MEDIUM Severity

### SEC-04: Glob-to-Regex Incomplete Escaping

**Locations:**
- `src/embeddings/semantic-search.ts:179-181, 385-388, 820, 1026`

```typescript
const regex = new RegExp(
  `^${pattern.replace(/\*/g, '.*').replace(/\?/g, '.')}$`,
)
```

Only `*` and `?` are replaced. Other regex metacharacters (`.`, `+`, `(`, `)`, `[`, `]`, `^`, `$`, `|`, `\`) are not escaped. Inconsistent with `path-matcher.ts:25` which correctly escapes all special chars first. `docs/v2.0/*.md` matches `docs/v2X0/file.md` because `.` is unescaped.

### SEC-05: API Key Exposure in Debug Error Output

**Location:** `src/cli/error-handler.ts:465`

```typescript
yield* Console.error(`Error: ${JSON.stringify(error, null, 2)}`)
```

In debug mode, full error objects are serialized. If the `cause` chain contains HTTP request context from the OpenAI SDK, API keys could appear in output.

### SEC-06: Symlink Traversal Without Boundary Check

**Location:** `src/config/schema.ts:65-67`, `src/index/indexer.ts:101-108`

The `followSymlinks` option (default false) exists but when enabled, no validation ensures symlink targets remain within `rootPath`.

### SEC-07: postinstall Runs execSync with npx

**Location:** `scripts/rebuild-hnswlib.js:46`

```javascript
execSync("npx node-gyp rebuild", { cwd: hnswlibDir, stdio: "inherit" })
```

Supply chain risk during `pnpm install`. Compromised node-gyp dependencies execute with full user privileges.

### SEC-08: Untrusted Index File Deserialization

**Locations:** `src/index/storage.ts:79`, `src/embeddings/vector-store.ts:521`

`JSON.parse` and `msgpack.decode` with unchecked `as T` assertions. No runtime schema validation on loaded index data. Committed `.mdcontext/` directories in repositories could contain malicious structures.

---

## LOW Severity

- **SEC-09:** Absolute paths in error messages reveal directory structure and usernames.
- **SEC-10:** Raw `console.warn`/`console.error` at `src/embeddings/semantic-search.ts:563`, `src/embeddings/vector-store.ts:456`, `src/mcp/server.ts:610` bypasses Effect log level filtering.
- **SEC-11:** `hnswlib-node ^3.0.0` is a C++ native addon. Memory safety issues could cause crashes or exploitable conditions.
- **SEC-12:** `src/index/storage.ts:112` truncates SHA-256 to 16 hex chars (64 bits). Intentional collisions feasible at 2^32 birthday bound.

---

## Positive Security Observations

1. **Effect `Redacted<string>` for API keys** across all providers. Keys only unwrapped at the HTTP client boundary.
2. **`spawn()` with argument arrays** in `src/summarization/cli-providers/claude.ts:56` with explicit security comment. No shell injection risk.
3. **Link resolution boundary check** at `src/index/indexer.ts:175`: `if (!resolved.startsWith(rootPath)) return null`.
4. **TypeScript strict mode** with `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, `noImplicitReturns`, `noFallthroughCasesInSwitch`.
5. **Exhaustive error matching** with `Match.exhaustive` in the CLI error handler.
6. **Secure config defaults:** `followSymlinks: false`, hidden files skipped, `node_modules`/`.git`/`dist`/`build` ignored.

---

## Test Coverage Assessment

| Module | Test Files | Key Gaps |
|--------|-----------|----------|
| cli | 4 | No tests for `main.ts`, most command handlers |
| config | 6 | Good coverage, strong precedence testing |
| embeddings | 10 | Missing `vector-store.ts` tests, no auth edge cases |
| errors | 1 | Adequate |
| index | 1 (ignore-patterns only) | **No tests for `indexer.ts`, `storage.ts`, `watcher.ts`** |
| search | 6 | Good coverage |
| summarization | 5 | Good coverage |
| **MCP server** | **0** | **Critical gap. No test file for `src/mcp/server.ts`** |

### Missing Security Test Scenarios

1. MCP path traversal (absolute paths, `../` sequences, symlinks)
2. ReDoS patterns (catastrophic backtracking in heading/content regex)
3. API key redaction verification in serialized errors
4. Symlink boundary tests when `followSymlinks` is enabled
5. Config file traversal boundary (malicious config in parent directory)
6. Malformed index file tests (corrupt JSON, unexpected schema)
7. MCP tool input validation (missing fields, excessive limits, type confusion)

---

## Remediation Priority

| Priority | Timeline | Items |
|----------|----------|-------|
| P0 | 1 week | SEC-02 (MCP path traversal), SEC-01 (ReDoS) |
| P1 | 30 days | SEC-04 (glob escaping), SEC-05 (debug key exposure), MCP server test suite |
| P2 | 90 days | SEC-03 (config traversal limit), SEC-06 (symlink validation), SEC-08 (schema validation), vector-store/indexer tests |
