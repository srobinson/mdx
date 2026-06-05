---
title: Transport Matters Captured Run Terminal API
type: design
tags: [transport-matters, backend, api, websocket, captured-run]
summary: WebSocket contract for captured Claude and Codex terminal panes.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

# Transport Matters Captured Run Terminal API

## Endpoints

```ts
// Existing Claude route, preserved for the merged frontend.
// WS /api/captured-runs/claude/terminal?cols=80&rows=24&cwd=/path

// Provider parameterized route for backend PR-a.
// WS /api/captured-runs/{cli}/terminal?cols=80&rows=24&cwd=/path
```

`cli` is a strict allowlist:

```ts
type CapturedRunCli = "claude" | "codex";
```

Any other path value is rejected before launch. It must never select an arbitrary binary or launch profile.

## Query parameters

```ts
interface CapturedRunTerminalQuery {
  cols?: number; // integer, default 80, min 1, max 500
  rows?: number; // integer, default 24, min 1, max 200
  cwd?: string; // optional workspace directory, defaults to backend cwd
}
```

## Ready frame

```ts
interface CapturedRunReadyFrame {
  type: "captured-run.ready";
  cli: CapturedRunCli;
  runId: string;
  cwd: string;
  storageDir: string;
  proxyPort: number;
  webPort?: number;
}
```

Nested desktop panes use external web runtime, so `webPort` is omitted. The live desktop web process owns the UI and API socket.

## Security contract

```ts
interface CapturedRunTerminalOriginPolicy {
  requiredOriginHeader: true;
  requiredHost: "localhost:<web_port>" | "127.0.0.1:<web_port>" | "[::1]:<web_port>";
  allowedWhen: "host-is-loopback-and-origin-is-same-origin" | "host-is-loopback-and-origin-is-configured-cors-origin";
  rejectCode: 1008;
}
```

The server validates origin before accepting the WebSocket and validates `cli` before preparing or spawning a captured run.

## Launch semantics

```ts
interface CapturedRunLaunchSemantics {
  webRuntime: "external";
  startsNestedWeb: false;
  promptInjection: false;
}
```

Claude nested panes keep the existing route and launch behavior, except they run without a nested web sidecar. The spawned Claude client receives `ANTHROPIC_BASE_URL` pointing at the captured proxy port.

Codex nested panes run the real Codex CLI through the existing Codex launch profile. The spawned Codex client receives explicit HTTPS proxy environment and ChatGPT auth remains native to Codex. No API key flow is introduced.

## Terminal frames

The binary and resize frame contract matches `/api/terminal`:

```ts
type TerminalInputFrame = ArrayBuffer;
type TerminalOutputFrame = ArrayBuffer;

interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}
```
