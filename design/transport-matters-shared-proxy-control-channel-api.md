---
title: Transport Matters shared proxy control channel API
type: design
tags: [transport-matters, backend, shared-proxy, control-channel]
summary: Typed Unix-domain-socket contract for Tier 2 Slice 5 shared proxy machinery.
status: active
source: backend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Transport Matters shared proxy control channel API

Internal API only. The channel is a local Unix domain socket owned by the API process and the shared proxy subprocess. Each request is one UTF-8 JSON object terminated by `\n`; each response is one UTF-8 JSON object terminated by `\n`. Every mutation is acknowledged after the subprocess has applied the state and completed the relevant accept-probe.

```typescript
type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue };
type ProxyModeKind = "reverse" | "regular";

interface SharedProxyBindingPayload {
  runId: string;
  cli: string | null;
  workingDir: string | null;
  storageRoot: string | null;
  listenPort: number;
  upstream: string | null;
  agentHomeDir: string | null;
  ownedNativeSessionId: string | null;
  ownedSourceDescriptor: string | null;
  launchFields: { [key: string]: JsonValue };
  defaultClientPassthrough: string[];
  breakpointSkipModels: string[];
  modeKind: ProxyModeKind;
}

interface OverrideScopePayload {
  runId: string | null;
  trackId: string | null;
}

interface OverrideValue {
  kind:
    | "tool_toggle"
    | "tool_description"
    | "system_part_toggle"
    | "system_part_text"
    | "message_block_toggle"
    | "message_text"
    | "truncate_tool_result"
    | "sampling_set"
    | "provider_extras_set";
  target: string;
  value: string | boolean | number | null;
}

interface OverrideSnapshotPayload {
  enabled: boolean;
  overrides: OverrideValue[];
}

type SharedProxyControlRequest =
  | { type: "ping" }
  | { type: "register_listener"; binding: SharedProxyBindingPayload }
  | { type: "deregister_listener"; runId: string }
  | { type: "set_overrides"; scope: OverrideScopePayload; payload: OverrideSnapshotPayload };

interface SharedProxyControlAck {
  ok: true;
  proxyGeneration: number;
  modeGeneration: number;
  overridesGeneration: number;
}

interface SharedProxyControlError {
  ok: false;
  code: string;
  message: string;
}
```

Security notes:

- The socket is filesystem local, not TCP reachable.
- The socket parent is created with owner-only permissions and the socket is chmodded `0600`.
- Payloads are Pydantic validated before dispatch.
- Registration fails closed on duplicate run ids, duplicate listen ports, unsupported modes, and reverse listeners without an upstream.
