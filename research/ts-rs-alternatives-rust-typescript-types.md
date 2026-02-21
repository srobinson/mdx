---
title: Alternatives to ts-rs for Rust-to-TypeScript type generation
type: research
tags: [rust, typescript, ts-rs, specta, typeshare, schemars, openapi, utoipa]
summary: ts-rs remains the lowest-friction option for small Axum+TS projects; each alternative has a specific niche where it outperforms ts-rs
status: active
source: quick-research
confidence: high
created: 2026-03-19
updated: 2026-03-19
---

## Summary

For a small single-user Axum project with a TypeScript frontend, ts-rs (v12.0.1, stable, Jan 2026) remains the best default. Each alternative has a specific niche that only applies if that niche's requirement is actually present.

## Details

### ts-rs (baseline)

- v12.0.1, Jan 31 2026, ~5.6M downloads, maintained by Aleph Alpha
- Derive macro, generates `.ts` files at test time
- Open issues are almost entirely feature requests (no barrel index.ts, no constants export, no serde-wasm-bindgen compat, race condition on parallel generation)
- Core functionality is stable

---

### Specta

- v2.0.0-rc.23, Mar 2 2026, ~792K downloads
- **NOT STABLE** -- v2 has been in RC since early 2025, 23 RCs with breaking changes between them
- Designed as a type-system layer for framework integrations (rspc, tauri-specta build on it)
- v2 adds multi-file export, branded types, format-agnostic core
- Use only if building an rspc-style RPC layer. Overkill for plain REST Axum.
- Risk: architectural redesign has stalled multiple times

---

### typeshare (1Password)

- v1.0.5, Jan 2 2026, ~6.8M downloads
- Stable, maintained by 1Password
- Polyglot: TypeScript, Swift, Kotlin, Scala, Go (experimental), Python (experimental)
- CLI-driven generation (no test harness required) -- better for build pipelines
- More restrictive annotation model than ts-rs; does not deeply mirror serde
- 70 open issues, 18 open PRs
- Advantage only materializes if you need multi-language output

---

### schemars + json-schema-to-typescript

- schemars v1.2.1, Feb 1 2026, ~193M downloads (very widely used as dependency)
- json-schema-to-typescript: npm, 3.3K GitHub stars, actively maintained
- Two-step pipeline: Rust -> JSON Schema -> TypeScript
- JSON Schema output has standalone value (ajv validation, OpenAPI integration, docs)
- Deepest serde attribute support of any option
- Downside: two tools, two build steps, type mapping bugs can originate in either layer
- Complex generics and recursive types have known rough edges in json-schema-to-typescript
- Only worth it if JSON Schema output is consumed by something else

---

### OpenAPI via utoipa (+ openapi-typescript/orval/hey-api)

- utoipa v5.4.0, Jun 2025, ~21.8M downloads, actively maintained
- Generates full OpenAPI 3.x spec from handler annotations
- Downstream: any OpenAPI toolchain works (openapi-typescript, orval, hey-api)
- Provides full API contract (routes, request/response, error shapes, auth) not just types
- Substantial annotation overhead on handlers
- Spec is not automatically verified correct against implementation
- Worth it only if the OpenAPI spec has standalone value (docs, external clients, contract testing)

---

### Manual duplication

- Zero dependencies, zero tooling
- Linear maintenance burden with type count and change frequency
- Viable at very small scale only

---

## Decision matrix

| Goal | Pick |
|---|---|
| Minimal friction, just need TS interfaces | ts-rs |
| Need OpenAPI spec anyway | utoipa + openapi-typescript |
| Targeting multiple client languages | typeshare |
| JSON Schema has standalone value | schemars + json-schema-to-typescript |
| RPC-style end-to-end type safety | specta + rspc (accept RC risk) |

## Sources

- crates.io API: ts-rs, specta, typeshare, schemars, utoipa
- https://github.com/specta-rs/specta/releases
- https://github.com/1Password/typeshare
- https://github.com/bcherny/json-schema-to-typescript
- https://github.com/Aleph-Alpha/ts-rs/issues

## Open Questions

- When will specta v2 stabilize? RC cadence suggests possibly mid-2026 but uncertain.
- Does aide (alternative to utoipa for Axum) have better ergonomics? Not investigated deeply.
- openapi-typescript vs orval vs hey-api quality comparison for generated TS client code -- not investigated.
