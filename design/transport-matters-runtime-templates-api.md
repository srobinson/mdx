# Transport Matters runtime templates API contract

Created: 2026-06-18
Status: active

## Scope

Browse read side only. The endpoint reads generated runtime template metadata and
does not inject launch flags, change run creation payloads, evaluate overrides,
or write to runtime homes.

## Domain types

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
```

## Endpoint

```typescript
// GET /v1/runtime-templates
interface ListRuntimeTemplatesResponse {
  items: RuntimeTemplateSummary[];
}
```

## Errors

```typescript
interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

Registry read or parse failures return HTTP 500 with
`code: "runtime_template_registry_error"`. Missing roots return
`{ "items": [] }`.

## Registry roots

The reader scans these roots in order:

1. `~/.agent-runtimes/runtimes/`, provenance `agent-runtimes`.
2. `~/.transport-matters/runtimes/`, provenance `tm-fleet`.

The root is currently flat in real data, but template names are already safe
relative paths, so enumeration tree walks directories that contain both
`runtime.toml` and `capabilities.json`.
