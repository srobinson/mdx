---
title: Runtime RPC identity gating
type: sessions
tags: [backend, runtime, identity, security, littleorgans]
summary: Runtime direct RPC dispatch now authorizes and audits through the shared identity client before runtime work.
status: active
source: backend-engineer
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Summary

Implemented runtime daemon identity gating for direct RPC dispatch in the ALP-2817 worktree. The runtime socket now extracts peer credentials, builds a local principal, authorizes each `RuntimeRpc` through identity policy, and only dispatches authorized calls. Runtime `Spawn` and `Kill` paths write audit rows before runtime work. Shim callbacks use a named local-only policy and audit as `Action::ShimCallback` so callback audit trails remain distinct from true daemon operations.

The identity client used by session handling was moved into `lilo-identity-service` and shared by session and runtime. SQLite immediate transaction helpers were moved into `lilo-db` to remove duplicate transaction code. Reviewer follow-up folds added `Action::ShimCallback`, restored exact app MCP audit assertions, moved runtime test-only dependencies to `[dev-dependencies]`, consolidated the subsequence assertion helper into shared session test support, and removed dead runtime authorization arms behind explicit delegated-path `unreachable!` handling. The non-exhaustive wildcard fallback also fails closed with `unreachable!` so future `RuntimeRpc` variants cannot silently map to `Action::Daemon`.

## API Contract

No external HTTP or GraphQL API changed. Internal RPC authorization mapping was added for runtime daemon dispatch:

```typescript
type RuntimeAuthorization = {
  principal: "local-os-user";
  resource: "runtime" | "session";
  action:
    | "spawn"
    | "kill"
    | "nudge"
    | "logs"
    | "list"
    | "read"
    | "doctor"
    | "daemon"
    | "shim_callback";
  audit: "allow" | "deny";
};
```

`RuntimeRpc::Spawn` uses a transaction scoped to the spawn session id and runtime resource. Mutating and read operations map to the closest identity action before dispatch. Shim launch, ready, and exit callbacks use `Action::ShimCallback` and a session-scoped resource.

## Database Changes

No schema migration was added. Runtime authorization writes to the existing identity audit table through `IdentityClient::authorize` and `IdentityClient::authorize_in_tx`.

Shared DB helpers added in `lilo-db`:

- `begin_immediate_tx`
- `finish_immediate_tx`

These keep session and runtime mutation authorization on the same transaction pattern.

## Security Considerations

Direct runtime RPC calls are no longer an unaudited bypass. Peer credentials are read from the Unix socket and converted into a local principal. Non-local principals are denied before runtime work. Denials are committed so audit evidence survives the rejected request. Allowed local requests are also audited before dispatch.

The shim callback path remains callable only by the local daemon identity and is isolated behind `authorize_shim_callback`, which documents why callback authorization differs from caller-driven runtime RPCs. The dedicated `ShimCallback` action improves audit readability without weakening local-only policy.

## Performance Notes

Authorization adds one identity policy check and audit write per runtime RPC. Spawn authorization uses the same immediate transaction pattern as session spawn so audit and runtime state remain ordered. No long-running runtime work happens while a denied request is executing.

Verification completed after reviewer folds:

- `fmm generate && fmm validate`
- `cargo build -p lilo-runtime-daemon`
- `cargo test -p lilo-im-core`
- `cargo test -p lilo-runtime-daemon`
- `cargo test -p lilo-session-daemon -p lilo-session-app`
- `cargo test -p lilo-session-app --test mcp_protocol_test`
- `cargo clippy --workspace -- -D warnings`
- `just check && just build && just test`

## Open Items

- Reviewer round-3 signoff is pending on the focused fail-closed wildcard fix.
- The current stub identity policy still only distinguishes the local OS user. Future policy expansion can refine runtime operator actions without changing the runtime dispatch hook.
