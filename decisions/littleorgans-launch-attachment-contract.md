---
title: Littleorgans launch attachment contract
type: decisions
tags:
  - littleorgans
  - issue-35
  - issue-41
  - launch-attachment
  - session
  - runtime
  - schedule
  - transport
summary: Locks one typed JSON launch attachment and its ownership, compatibility, redaction, persistence, and delivery limits.
status: active
project: littleorgans
confidence: high
created: 2026-08-16
updated: 2026-08-16
---

# Littleorgans launch attachment contract

## Decision

The occupant launch spec is the full concrete Runtime request plus one optional
launch attachment. The Runtime request field is `launch_attachment`.
`lilo-rm-core` owns one `LaunchAttachment` with exactly these fields:

```rust
pub struct LaunchAttachment {
	pub kind: String,
	pub version: u32,
	pub value: serde_json::Value,
}
```

The one attachment contains the capture lease and all other Transport prepare
data inside `value`. `LaunchEnv` carries only already typed process environment
and does not form a second envelope.

Transport owns the meaning of each version for each `kind`. Its first written
version is `1`. Session, Schedule, and Runtime carry every `u32` unchanged.
Attachment versions are unrelated to `RUNTIME_PROTOCOL_VERSION`.

Session, Schedule, and Runtime deserialize the outer typed object and copy it.
Only Transport interprets `kind`, `version`, or `value`.

Equality means semantic `LaunchAttachment` value equality after a clone, a
Runtime request JSON round trip, recovery from `spawn_request_json`, and receipt
by `RuntimeService::spawn` through each Runtime adapter. The contract excludes
lexical whitespace, JSON object member order, and other lexical spellings.

## Serialization and compatibility

`LaunchAttachment` uses `deny_unknown_fields`. Unknown keys inside `value`
remain part of the JSON value. Neither the external Session `SpawnRequest` nor
Runtime `SpawnRequest` uses `deny_unknown_fields`.

Runtime `SpawnRequest.launch_attachment` uses
`#[serde(default, skip_serializing_if = "Option::is_none")]`. A missing key
decodes as `None`, and writers omit `None`. A present malformed attachment fails
Runtime request deserialization. Because `list_pending_spawn_intents` applies
the row decoder to every pending row, that method returns an error instead of
silently producing `None`.

## Session ownership

Session attaches a launch attachment only after minting `SessionId` and after
Identity authorizes the operation. The external Session `SpawnRequest` never
accepts the field. Raw `lilo runtime spawn` keeps it absent. Issue 41 must prove
missing field compatibility through a literal old `spawn_request_json` value
read by the existing row decoder.

## Transaction ordering

Session mints `SessionId`, Identity authorizes the operation, and Transport
prepares the launch attachment. Session then adds the attachment and builds the
complete Runtime request. Transaction A atomically records the authorization
audit, the pending Session intent with that complete request, and the pending
Runtime `Forking` lifecycle.

The current v0.8 path sends the complete request to Runtime after Issue 41 adds
the field. The target path sends the occupant launch spec to Schedule, which
places the occupant and passes the spec to Runtime. Runtime starts the shim and
returns the `Running` lifecycle. Transaction B inserts the `Running` Session
row, persists that lifecycle, and resolves the intent. Session appends the
Runtime `Running` event only after Transaction B commits.

## Runtime ownership and delivery limit

Issue 41 adds `LaunchAttachment` to `lilo-rm-core`. It threads the optional
field only through `SpawnLaunch`, `runtime_spawn_request`, both Runtime
adapters, Runtime `SpawnRequest`, and intent JSON. Each adapter must deliver an
equal value to `RuntimeService::spawn`. Runtime receives and retains the
attachment on Runtime `SpawnRequest` at that endpoint.

Issue 41 does not add the attachment to `LaunchSpec`, the shim protocol, the
child process, environment variables, files, Schedule, or Transport delivery.
A later Transport proof must choose and verify any child delivery mechanism.

## Persistence and disclosure

Session persists the full attachment only through the existing
`session_spawn_intents.spawn_request_json` field. The value follows the current
retention rule for pending, resolved, and aborted rows. Issues 35 and 41 add no
table, encryption, cleanup job, or attachment specific deletion.

Transport must not place provider credentials, API keys, or bearer secrets in
the attachment under this retention rule. Issue 41 requires a manual redacted
`Debug` implementation. Logs, CLI output, API projections, and errors may show
presence, `kind`, and `version`. They never show `value`.

## Vocabulary

| Term | Meaning |
| --- | --- |
| Occupant launch spec | The concrete Runtime request plus the optional launch attachment. |
| Launch attachment | The optional `kind`, `version`, and `value` field. |
| Capture lease | Transport owned content inside `value`. |
| Pane snapshot | Terminal output returned by `lilo capture` or diagnostic `lilo runtime capture`. |
| Provider capture or wire capture | Transport observation of harness to provider traffic. |

Provider traffic commands belong under a future `lilo transport ...`
namespace after implementation proves real verbs. Transport has no spawn
command.

## Candidate judgment

The GPT candidate is the base. It supplied the `serde_json::Value`
representation, semantic equality, Runtime ownership, redacted `Debug`, and
the Issue 41 endpoint.

The Grok candidate supplied two accepted grafts. Architecture facts live under
one canonical system heading, with context documents limited to local
ownership. Issue 41 proves missing field compatibility through literal old
`spawn_request_json` read by the store decoder.

The decision rejects Grok's `OpaqueJson`, `RawValue`, `raw_value` feature,
`LaunchAttachmentError`, and `try_new` validation. They add types and policy
without improving the accepted semantic equality contract. The decision also
rejects derived `Debug`, a second execution field, a type in `lilo-common`, and
delivery through `LaunchSpec` or the child process.

## Consequences

The design adds one optional field to the existing durable Runtime request. It
does not create a second payload store or teach Session, Schedule, or Runtime
how Transport divides a lease from other preparation data. Evolution remains
inside the versioned JSON value.

Required capture, capture failure policy, Transport process design, child
delivery, Transport record ownership, and cleanup remain outside this lock.

## Verification status

The Issue 35 documentation passed `just check`, `just build`, `just test`, and
`just test-doc` on 2026-08-16. Implementation remains pending. Issue 41 must
implement the type and forwarding path, then prove the literal old JSON case,
semantic equality, adapter parity, redaction, and normal absent launch behavior.

## Sources

- `/Users/alphab/.mdx/projects/littleorgans-scout-launch-payload-docs.md`
- `/Users/alphab/.mdx/projects/littleorgans-scout-launch-payload-runtime.md`
- `/Users/alphab/.mdx/TMP/pstack/issue35-launch-payload/candidate-gpt.md`
- `/Users/alphab/.mdx/TMP/pstack/issue35-launch-payload/candidate-grok.md`
- `/Users/alphab/.mdx/TMP/pstack/issue35-launch-payload/judgment.md`
- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans-worktrees/issue-35/docs/architecture/system.md`
