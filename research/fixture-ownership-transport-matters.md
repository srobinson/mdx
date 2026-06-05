---
title: Fixture Ownership Handoff for Transport Matters Issues 594 and 598
type: research
tags: [transport-matters, runtime-policy, schema-v4, fixtures, github-issues]
summary: Issue 594 now owns every schema valid shared fixture required for independent delivery, while issue 598 consumes those fixtures and owns only authority scenario values.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-03
updated: 2026-09-03
---

## Executive Summary

Transport Matters consumes generated runtime policy artifacts from .agent-runtimes, projects them through its Python catalog, and exposes the result to TypeScript Canvas code. Issues 594 and 598 now assign fixture ownership at that boundary: 594 delivers schema valid API and Canvas fixtures, while 598 changes fixture values only for its consent scenarios.

## Project Metadata

| Area | Current stack |
| --- | --- |
| API | Python 3.14, FastAPI, Pydantic, psycopg, Alembic, pytest |
| Product plane | TypeScript, React, Ark UI, Zustand, Vitest, Playwright |
| Build | uv and Hatch for Python, pnpm 11.18 for Node |
| Runtime floor | Python 3.14 and Node 20.19 |
| Indexed topology | 1,805 files, 328,632 LOC across api, www, packages, and desktop |

Sources: api/pyproject.toml, package.json, www/packages/canvas/package.json, and www/packages/shell/package.json.

## Architecture

The relevant producer and consumer flow is:

    .agent-runtimes capabilities.json
      -> RuntimeTemplateCapabilities
      -> RuntimeTemplateListing.summary
      -> RuntimeTemplateSummary
      -> REST and MCP catalog responses
      -> TypeScript RuntimeTemplateSummary
      -> Canvas launcher rows

Issue 594 owns schema version 4 parsing, validation, transport, and catalog projection. Issue 598 owns Canvas consent presentation and launch behavior after the policy resolver and catalog filter blockers land.

## Key Patterns

### Schema changes must migrate independent fixtures

A required catalog field affects more than the central parser tests. Route tests and shared TypeScript fixtures construct complete artifacts or complete RuntimeTemplateSummary objects, so they must move with the schema consumer change.

### Shared fixtures belong to the earliest independently landable issue

commandModel.testSupport.ts is imported by seven Canvas test files. Four exported runtime fixtures are complete catalog objects: research, codexSpec, unsupported, and vendorMismatch at www/packages/canvas/src/launcher/commandModel.testSupport.ts:13-87. Adding required fields in issue 594 keeps its TypeScript contract change independently typecheckable. Issue 598 can then clone or override only the values needed for consent scenarios.

## Detailed Findings

### API route fixtures

api/src/transport_matters/api/v1/test_runtime_template_routes.py contains three inline schema version 3 artifacts at current lines 38-59, 121-136, and 142-157. The first route response assertion is at lines 64-93. The degenerate root case and its valid nested runtime assertion are at lines 162-180.

Issue 594 now requires:

1. Migrating every inline artifact to schema version 4 with the producer's minimum valid policy.
2. Extending test_runtime_templates_endpoint_response_shape.
3. Extending test_runtime_templates_endpoint_skips_degenerate_root_entry.
4. Proving the REST projection preserves the requested grant and ordered capability list.
5. Including the route test file in focused API verification.

### Canvas shared fixtures

The four full runtime fixtures are defined at:

- research, www/packages/canvas/src/launcher/commandModel.testSupport.ts:13-32
- codexSpec, www/packages/canvas/src/launcher/commandModel.testSupport.ts:34-53
- unsupported, www/packages/canvas/src/launcher/commandModel.testSupport.ts:55-66
- vendorMismatch, www/packages/canvas/src/launcher/commandModel.testSupport.ts:68-87

FMM reports direct downstream imports from:

- CommandCenter.spaces.test.tsx
- commandModel.test.ts
- commandRows.canvas.test.ts
- commandRows.developers.test.ts
- commandRows.test.ts
- templateRows.test.ts
- workdirRows.test.ts

The existing callers treat the runtime fixtures as catalog inputs and assert derived rows, commands, readiness, or navigation. Representative coverage is in templateRows.test.ts:82-410, commandRows.test.ts:207-215, and commandModel.test.ts:6-17. No existing assertion needs to change solely because issue 594 adds the required policy fields. Canvas typecheck is the focused proof that all complete objects satisfy the expanded contract.

### Corrected issue ownership

Issue 594 now names both omitted fixture surfaces in its changes, tests, and verification:

- api/src/transport_matters/api/v1/test_runtime_template_routes.py
- www/packages/canvas/src/launcher/commandModel.testSupport.ts

Issue 598 now states that it consumes the valid shared fixtures delivered by 594. It does not own introducing the required policy fields and changes only scenario specific values.

### Verification

Both live GitHub bodies match the prepared corrected bodies exactly.

| Issue | Parent | Blocked by | Blocking | Labels | State |
| --- | --- | --- | --- | --- | --- |
| 594 | 593 | .agent-runtimes 2 | 595 | enhancement, P2 | open |
| 598 | 593 | 595, 597 | none | enhancement, P2 | open |

Titles, labels, parent relationships, blockers, milestones, scopes, acceptance criteria, and exclusions remain intact. Both bodies contain no line anchors and no em dash characters. The repository worktree remained clean.

## Dependencies

- .agent-runtimes issue 2 owns schema version 4 field names, capability identifiers, combination rules, and deterministic ordering.
- Transport Matters issue 595 owns effective authority resolution.
- Transport Matters issue 597 owns filtered MCP discovery.
- @tm/contract owns the grant and capability vocabulary used by TypeScript.
- @tm/core owns the browser catalog type consumed by Canvas.

## Relevance to Helioy

This handoff establishes a reusable rule for staged contract changes: the first consumer issue owns all fixtures required for independent compilation and testing. Later product issues own only behavior and scenario specific values.

## Open Questions

The producer field names and capability vocabulary remain unresolved until .agent-runtimes issue 2 lands. Issue 594 should copy the landed contract exactly rather than preselect names or infer policy.
