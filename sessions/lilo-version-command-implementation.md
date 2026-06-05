---
title: lilo version command implementation
type: sessions
tags: [backend, cli, littleorgans, generated-surface]
summary: Added top-level lilo version with human and JSON output backed by runtime VersionInfo metadata.
status: active
source: backend-engineer
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

## Summary

Implemented W5 `lilo version` on branch `refactor/cli-operator-namespaces` at commit `9a14a04`, then pushed the branch. The command reports client side compile time metadata only. It leaves the existing clap `lilo --version` semver one liner unchanged.

Reviewer `littleorgans:helioy-tools:rust-engineer:5:3.1` signed Phase B with `S|B|I sign off on the lilo-version as currently filed`.

## API Contract

CLI contract:

```text
lilo version [--output human|json]
lilo --version
```

Human output prints a readable block:

```text
lilo:
  version: <crate::VERSION>
  git_sha: <runtime git sha>
runtime:
  protocol_version: <runtime protocol version>
  capabilities:
    - <capability>
```

JSON output reuses `lilo_rm_core::VersionInfo` serialization:

```json
{
  "version": "0.8.0",
  "git_sha": "<sha>",
  "protocol_version": "0.6",
  "capabilities": ["structured_protocol_errors"]
}
```

`git_sha` is included because `VersionInfo` is the DRY serialization contract. `lilo --version` still prints `littleorgans <semver>`.

## Database Changes

None.

## Security Considerations

The command is client side only and does not open the daemon socket, issue RPC calls, read user controlled paths, or mutate state. JSON output goes to stdout and uses existing `serde` serialization.

## Performance Notes

No runtime dependency work is performed. The command reads compile time constants and formats an in memory `VersionInfo`, so startup cost is limited to normal CLI process startup.

Verified commands:

```text
cargo run -p xtask -- codegen
cargo run -p xtask -- codegen --check
cargo test -p lilo
cargo run -q -p lilo -- version
cargo run -q -p lilo -- version --output json
cargo run -q -p lilo -- version --output json | jq -e '.version and .protocol_version and (.capabilities | length > 0)'
cargo run -q -p lilo -- --version
cargo run -q -p lilo -- version --output human
fmm generate && fmm validate
just check && just build && just test
```

`just check && just build && just test` completed with 212 tests passed.

## Open Items

Reviewer noted a pre existing incremental build caveat: `git_sha` can show the cached `lilo-rm-core` build SHA during local incremental runs. Clean and CI builds bake the current HEAD. This behavior is shared by existing `version_info()` consumers and was left out of W5 scope.
