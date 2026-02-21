---
title: ALP-2054 Lane C Scope Migration Review
type: research
tags: [context-matters, alp-2054, cm-web, mcp, review]
summary: Lane C review found MCP docs aligned and targeted tests passing, with a frontend cwd request surface gap for recall and export.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

ALP-2054 largely completes the public migration from `scope_path` and `scope_mode` request inputs to `scope` across cm-web and generated MCP artifacts. Targeted tests for cm-web scope migration, frontend contracts, and MCP protocol rejection all pass.

The remaining acceptance risk is in the cm-web frontend API client. Backend HTTP handlers support `scope=cwd_inferred&cwd=...` for recall and export, but the typed frontend client cannot express `cwd` for recall or export.

## Project Metadata

- Language: Rust workspace with TypeScript React frontend under `crates/cm-web/frontend`
- Relevant crates: `cm-capabilities`, `cm-cli`, `cm-web`
- Build and test tooling: Cargo, npm scripts for cm-web frontend, generated MCP schemas from `tools.toml`
- fmm: `.fmm.db` present at repository root

## Architecture Notes

- `crates/cm-web/src/api/agent.rs` centralizes browse and recall parsing for `/api/agent/*` and compatibility aliases in `/api/entries/*`.
- `crates/cm-web/src/api/entries.rs` uses `EntryWriteRequest` for create and merge bodies so web write bodies expose `scope` while converting internally to `NewEntry.scope_path`.
- `crates/cm-cli/src/mcp/generated_schema/*.json`, `tools.toml`, and `crates/cm-cli/templates/SKILL.md` are the public MCP documentation artifacts for migrated tool inputs.

## Findings

### Medium: frontend API cannot pass `cwd` for recall or export

Backend recall parsing accepts `cwd` and applies it through `parse_scope_selector`: `crates/cm-web/src/api/agent.rs:121-166` and `crates/cm-web/src/api/agent.rs:84-109`. Backend export does the same through `parse_scope_query`: `crates/cm-web/src/api/export.rs:19-27`.

The frontend API types do not expose that same request surface:

- `RecallParams` has `query`, `scope`, `kinds`, `tags`, `limit`, and `max_tokens`, but no `cwd`: `crates/cm-web/frontend/src/api/client.ts:161-168`.
- `api.entries.recall` and `api.agent.recall` serialize no `cwd`: `crates/cm-web/frontend/src/api/client.ts:227-236` and `crates/cm-web/frontend/src/api/client.ts:273-282`.
- `api.export` accepts only an optional `scope` string and cannot serialize `cwd`: `crates/cm-web/frontend/src/api/client.ts:324-326`.

This creates drift from the backend and vertical tests, which explicitly validate export with `scope=cwd_inferred&cwd=/tmp/helioy/context-matters`: `crates/cm-web/tests/parity/scope_migration.rs:96-108`.

### Low: vertical and frontend contract coverage miss recall cwd and export cwd client cases

The new cm-web migration test covers search exact scope, search cwd inferred, export exact scope, export cwd inferred, old query field rejection, create, merge, and body rejection: `crates/cm-web/tests/parity/scope_migration.rs:9-241`. Existing recall parity covers basic recall, exact scope plus tags, and entries compatibility: `crates/cm-web/tests/parity/recall.rs:8-78`.

There is no positive cm-web vertical test for `/api/agent/recall?scope=cwd_inferred&cwd=...` or `/api/entries/recall?scope=cwd_inferred&cwd=...`. The frontend contract file exercises browse, search, agent browse, export, create, and merge, but not recall and not export with cwd: `crates/cm-web/frontend/src/api/scope-contract.test.ts:12-17`.

### Positive: migrated MCP public inputs are aligned

Generated schemas for migrated scope tools expose `scope` and do not expose old request fields in their input schemas:

- `cx_browse`: `crates/cm-cli/src/mcp/generated_schema/cx_browse.json:43-45`
- `cx_recall`: `crates/cm-cli/src/mcp/generated_schema/cx_recall.json:24-26`
- `cx_store`: `crates/cm-cli/src/mcp/generated_schema/cx_store.json:44-46`
- `cx_deposit`: `crates/cm-cli/src/mcp/generated_schema/cx_deposit.json:28-30`
- `cx_export`: `crates/cm-cli/src/mcp/generated_schema/cx_export.json:12-14`

`tools.toml` and generated skill docs state the boundary clearly: public requests use `scope`, `cwd_inferred` replaces old `auto`, and persisted data may still expose `scope_path`: `tools.toml:47-51`, `crates/cm-cli/templates/SKILL.md:67-71`.

### Positive: old cm-web request fields are rejected at the server boundary

- Query handlers reject `scope_path` and `scope_mode`: `crates/cm-web/src/api/agent.rs:65-82`, `crates/cm-web/src/api/agent.rs:121-166`, and `crates/cm-web/src/api/entries.rs:116-152`.
- Browse rejects deserialized legacy fields before execution: `crates/cm-web/src/api/agent.rs:231-245` and `crates/cm-web/src/api/agent.rs:281-288`.
- Entry create and merge bodies deny unknown fields, so `scope_path` and `scope_mode` are rejected: `crates/cm-web/src/api/entries.rs:241-274` and covered by `crates/cm-web/tests/parity/scope_migration.rs:197-241`.

## Verification Commands Run

```sh
cargo test -p cm-web scope_migration -- --nocapture
cargo test -p cm-web --test frontend_scope_contract -- --nocapture
cargo test -p cm-cli --test mcp_protocol_test public_scope_artifacts_do_not_expose_removed_request_terms -- --nocapture
cargo test -p cm-cli --test mcp_protocol_test protocol_migrated_scope_tools_reject_scope_path -- --nocapture
cargo test -p cm-cli --test mcp_protocol_test protocol_migrated_scope_tools_reject_auto_scope -- --nocapture
cargo test -p cm-cli --test mcp_protocol_test protocol_migrated_scope_tools_reject_unknown_fields -- --nocapture
npm --prefix crates/cm-web/frontend run typecheck
python3 - <<'PY'
import json, pathlib
for p in sorted(pathlib.Path('crates/cm-cli/src/mcp/generated_schema').glob('cx_*.json')):
    if p.stem not in {'cx_browse','cx_recall','cx_store','cx_deposit','cx_export'}:
        continue
    data=json.loads(p.read_text())
    text=json.dumps(data.get('inputSchema',{}), sort_keys=True)
    bad=[s for s in ['scope_path','scope_mode','scope=auto',"scope='auto'"] if s in text]
    print(f'{p.name}: inputs={list(data["inputSchema"].get("properties",{}).keys())} bad={bad or "none"}')
PY
git status --short
```

Results: all targeted tests and frontend typecheck passed. The schema probe reported no stale migrated request inputs. `git status --short` was clean after the review.

## Relevance to Helioy

This migration improves Helioy agent memory ergonomics by making `scope` the single public selector and keeping `scope_path` as an internal exact storage identity. The frontend cwd gap matters because cm-web is expected to mirror MCP and capability semantics closely.

## Open Questions

- Should cm-web frontend recall and export intentionally omit `cwd` because browser callers cannot provide a meaningful filesystem cwd, or should the TypeScript client mirror the backend HTTP API exactly?
- Should write body rejection return a custom `scope_path has been removed; use scope` message instead of the generic unknown field validation returned by `serde(deny_unknown_fields)`?
