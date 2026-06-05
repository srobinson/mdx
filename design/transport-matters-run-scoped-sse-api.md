# Transport Matters Run Scoped SSE API Contract

Created: 2026-06-16

```typescript
type RunScopedStreamEvent =
  | ConnectedEvent
  | ExchangeEvent
  | ExchangeDeletedEvent
  | PausedEvent
  | PausedTokensEvent;

interface ConnectedEvent {
  type: "connected";
  run_id: string;
}

interface ExchangeEvent {
  type: "exchange";
  run_id: string;
  id: string;
  ts: string;
  provider: string;
  model: string;
  req: unknown;
  res?: unknown | null;
  pipeline?: unknown | null;
  mutated_manually?: boolean;
  flow_id?: string;
  codex_turn?: unknown;
  track_id?: string | null;
  parent_track_id?: string | null;
  track_display_name?: string | null;
  track_role?: "parent" | "subagent" | string | null;
  spawn_anchor?: unknown | null;
}

interface ExchangeDeletedEvent {
  type: "exchange_deleted";
  run_id: string;
  id: string;
  flow_id?: string;
}

interface PausedEvent {
  type: "paused";
  run_id: string;
  flow_id: string;
  transport: "http" | "websocket" | string;
  ir: unknown;
  original_tools?: unknown[];
  original_system?: unknown[];
  original_messages?: unknown[];
  original_sampling?: unknown;
  original_provider_extras?: Record<string, unknown>;
  audit?: unknown | null;
  paused_at_ms: number;
  tokens_before?: number | null;
  provisional_exchange_id?: string | null;
  track_id?: string | null;
  parent_track_id?: string | null;
  track_display_name?: string | null;
  track_role?: "parent" | "subagent" | string | null;
  spawn_anchor?: unknown | null;
}

interface PausedTokensEvent {
  type: "paused_tokens";
  run_id: string;
  flow_id: string;
  tokens_before: number;
}

// GET /v1/runs/{runId}/stream
// Server Sent Events. Each `data:` frame is one RunScopedStreamEvent.
// Subscribers only receive events whose run_id equals the path runId.
// Keepalive frames are SSE comments and have no JSON payload.
```
