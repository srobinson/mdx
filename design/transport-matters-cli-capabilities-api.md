---
title: Transport Matters CLI Capabilities API
type: design
tags: [backend, transport-matters, api, cli]
summary: Contract for exposing Claude and Codex CLI availability through the core provider and API.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

# Transport Matters CLI Capabilities API

## Entity definitions

```typescript
type CliName = "claude" | "codex";

interface CliCapability {
  installed: boolean;
  path: string | null;
  version: string | null;
}

interface CapabilitiesResponse {
  clis: Record<CliName, CliCapability>;
}

interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}
```

## Endpoint contract

### GET /api/capabilities

Returns current local CLI availability for `claude` and `codex`.

```typescript
interface GetCapabilitiesRequest {}

interface GetCapabilitiesResponse extends CapabilitiesResponse {}
```

Example response:

```json
{
  "clis": {
    "claude": {
      "installed": true,
      "path": "/opt/homebrew/bin/claude",
      "version": "1.0.0"
    },
    "codex": {
      "installed": false,
      "path": null,
      "version": null
    }
  }
}
```

## Provider contract

```typescript
function detect_clis(): Record<CliName, CliCapability>;
```

The provider is package root core code. API code imports it directly. CLI launch and doctor code consume the same resolver path.

## Error behavior

The endpoint should not fail because a CLI is missing or a version probe times out. Missing binaries, non runnable candidates, failed version probes, and timed out version probes return `installed: false` or `version: null` as appropriate.

## Security and performance

The provider uses fixed binary names only: `claude` and `codex`. No client input is executed. Version probes use argument arrays, no shell, and a short timeout.
