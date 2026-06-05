---
title: Transport Matters Terminal Pane API
type: design
tags: [transport-matters, backend, api, websocket, terminal]
summary: WebSocket contract for one browser terminal pane backed by one local PTY.
status: active
source: backend-engineer
confidence: high
created: 2026-06-09
updated: 2026-06-09
---

# Transport Matters Terminal Pane API

## Endpoint

```ts
// WebSocket
// WS /api/terminal?cols=80&rows=24
```

## Query parameters

```ts
interface TerminalConnectQuery {
  cols?: number; // integer, default 80, min 1, max 500
  rows?: number; // integer, default 24, min 1, max 200
}
```

## Security contract

```ts
interface TerminalOriginPolicy {
  requiredOriginHeader: true;
  requiredHost: "localhost:<web_port>" | "127.0.0.1:<web_port>" | "[::1]:<web_port>";
  allowedWhen: "host-is-loopback-and-origin-is-same-origin" | "host-is-loopback-and-origin-is-configured-cors-origin";
  rejectCode: 1008;
}
```

The server validates the WebSocket `Origin` header before accepting the
handshake. The request `Host` header must be a loopback host on the configured
web port before same origin or configured origin checks are considered. This
prevents DNS rebinding from making an attacker controlled host look same origin.

## Binary frames

```ts
// Client to server
// Raw terminal input bytes for the PTY stdin. Control bytes such as 0x03
// are forwarded to the PTY line discipline.
type TerminalInputFrame = ArrayBuffer;

// Server to client
// Raw terminal output bytes from the PTY master.
type TerminalOutputFrame = ArrayBuffer;
```

## Text control frames

```ts
interface TerminalResizeFrame {
  type: "resize";
  cols: number;
  rows: number;
}
```

A resize frame applies `TIOCSWINSZ` to the PTY. Invalid control frames are
protocol errors and close the socket.

## Lifecycle

One socket owns one PTY and one child shell process. The child is launched as a
session leader with the PTY slave as its controlling terminal and default terminal
signal dispositions, so foreground jobs receive line discipline signals such as
SIGINT from Ctrl C. The server terminates the child process group and closes the
PTY master when the socket disconnects or the child exits.
