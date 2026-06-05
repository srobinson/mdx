---
title: Runtime templates read side implementation
type: sessions
tags: [backend, transport-matters, runtime-templates, api]
summary: Implemented the Transport Matters runtime template browse reader and endpoint, then hardened malformed registry enumeration.
status: active
source: backend-engineer
confidence: high
created: 2026-06-18
updated: 2026-06-18
---

## Summary

Implemented the runtime template browse read side on branch `feat/runtime-templates-read-side`, PR#143. Initial implementation landed in commit `0de83ed`. Follow up hardening landed in commit `c118b68`.

Key decisions:

- `runtime_registry.py` owns registry roots, safe name resolution, capabilities parsing, and listing because it already owned the external runtime registry seam.
- `runtime_templates.py` owns typed shared value objects for capabilities, recommendations, summaries, and harness to vendor compatibility.
- Enumeration tree walks directories containing both `runtime.toml` and `capabilities.json`, matching resolver support for nested safe relative template names.
- Ordered roots are external agent curation at `~/.agent-runtimes/runtimes/` followed by shipped TM fleet at `~/.transport-matters/runtimes/`. First root wins duplicate names.
- Discovery is total for malformed entries. A degenerate root level `capabilities.json` plus `runtime.toml` is skipped during enumeration, while named lookup keeps raising for invalid template names.
- Claude and Codex are the live supported harnesses. Opencode and pi remain forward compatible parse targets. The pi vendor set is provisional.

## API Contract

```typescript
type RuntimeTemplateVendor = "anthropic" | "openai";
type RuntimeTemplateHarness = "claude" | "codex" | "opencode" | "pi";
type RuntimeTemplateEffort = "low" | "medium" | "high" | "xhigh";

interface RecommendedModelDefault {
  harness?: RuntimeTemplateHarness;
  vendor?: RuntimeTemplateVendor;
}

interface RecommendedVendorModel {
  model?: string;
  effort?: RuntimeTemplateEffort;
}

interface RecommendedModel {
  default?: RecommendedModelDefault;
  by_vendor?: Partial<Record<RuntimeTemplateVendor, RecommendedVendorModel>>;
}

interface RuntimeTemplateSummary {
  name: string;
  vendors: RuntimeTemplateVendor[];
  required_capabilities: string[];
  recommended_model: RecommendedModel | null;
}

interface ListRuntimeTemplatesResponse {
  items: RuntimeTemplateSummary[];
}
```

Endpoint:

- `GET /v1/runtime-templates`
- Missing roots return `{ "items": [] }`.
- Registry parse failures return the standard API error shape with `code: "runtime_template_registry_error"`.
- Malformed discovered template names are skipped during listing so one bad entry cannot fail the browse endpoint.

## Database Changes

None.

## Security Considerations

- Template names still pass the existing safe relative path validation.
- Resolved template directories must remain under their registry root after symlink resolution.
- The reader exposes only metadata from `capabilities.json`, never template file bodies or credentials.
- TM does not write into `~/.agent-runtimes/`.
- Launch time template secret validation stays in runtime home planning.

## Performance Notes

- Filesystem listing runs off the event loop via `asyncio.to_thread` at the FastAPI route boundary.
- Parsing is synchronous and pure after file read.
- Missing roots short circuit to empty results.
- Current runtime roots are small. No cache was added.

## Verification

- `cd api && just check`
- `cd api && just test`, 1570 passed
- Focused regression before fix: degenerate root listing and endpoint tests failed with `ValueError: invalid runtime template name: '.'`
- Focused regression after fix: `cd api && just test src/transport_matters/test_runtime_registry.py::test_list_runtime_templates_skips_degenerate_root_entry src/transport_matters/api/v1/test_runtime_template_routes.py::test_runtime_templates_endpoint_skips_degenerate_root_entry`, 2 passed
- Earlier focused suite: `cd api && just test src/transport_matters/test_runtime_registry.py src/transport_matters/api/v1/test_runtime_template_routes.py`, 24 passed
- Real artifact probe parsed `imagegen`, `research`, and `codebase-mapper` from `~/.agent-runtimes/runtimes/`

## Open Items

- Confirm the pi harness vendor set with Stuart.
- Future launch flag injection and run creation payload extensions remain out of scope for this slice.
