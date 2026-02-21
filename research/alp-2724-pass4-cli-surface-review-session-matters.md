---
title: ALP-2724 Pass 4 CLI Surface Review for session-matters
type: research
tags: [session-matters, linear, cli, review, helioy-bus]
summary: Pass 4 review found one substantive W2 gap: daemon selector errors can retain the agent noun unless handler.rs is in scope.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

A cold pass 4 review of the ALP-2724 Linear tree found one substantive blocker in ALP-2728. The planned `sm delete` noun rename covers the CLI enum and delete module, but omits daemon handler selector error labels that remain user visible after session-noun cleanup.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Workspace area reviewed: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters`
- Structural index: fmm available and used. `fmm_list_files` reported 100 indexed files and 15,034 LOC.
- Key review artifacts: Linear ALP-2724, ALP-2725, ALP-2726, ALP-2727, ALP-2728, ALP-2729, ALP-2730, ALP-2735, ALP-2731, ALP-2732, ALP-2733.

## Architecture

The CLI grammar is defined in `crates/sm-cli/src/cli/cli_def.rs` and dispatched by verb modules such as `crates/sm-cli/src/cli/delete.rs`. Runtime requests are routed through daemon handlers in `crates/sm-daemon/src/handler.rs`. Tool and help metadata still originate from `tools.toml`, which feeds the CLI build script and the shared runtime contract registry.

Relevant structural facts:

- `crates/sm-cli/src/cli/cli_def.rs:147-162` defines `DeleteResource::Agent(DeleteAgentArgs)` and `DeleteNamespaceArgs`.
- `crates/sm-cli/src/cli/delete.rs:8-19` imports `DeleteAgentArgs`, dispatches `DeleteResource::Agent`, and calls `delete_agent`.
- `crates/sm-daemon/src/handler.rs:255-260` handles delete requests and calls `resolve_selector(&request.selector, "agent")`.
- `crates/sm-daemon/src/handler.rs:371-372` handles label requests and also calls `resolve_selector(&request.selector, "agent")`.
- `crates/sm-daemon/src/handler.rs:557-574` renders that label into user-facing errors: `unknown {label} session` and `{label} selector matched no sessions`.
- `crates/sm-core/src/tool_contracts.rs:9-18` embeds `tools.toml` with `include_str!` and exposes `contract_registry()`.

## Key Patterns

- CLI shape changes require checking both clap grammar and daemon error strings. A CLI rename can compile and pass help tests while leaving stale nouns in RPC error paths.
- Per-resource tool metadata decomposition must account for both build-time CLI artifact generation and sm-core runtime registry embedding.
- The current test suite already has namespace lifecycle coverage under `crates/sm-cli/tests/cli_namespace_test.rs` and selector-scope coverage under `crates/sm-cli/tests/cli_selector_scope_test.rs`.

## Detailed Findings

### Finding 1: ALP-2728 omits daemon selector error labels

ALP-2728 scopes the W2 work to the CLI rename from `Agent` to `Session` and lists stable entry points in `cli_def.rs`, `delete.rs`, `selector_scope.rs`, generated help, and delete-related CLI tests. Live source shows user-facing daemon paths outside those entry points:

- `crates/sm-daemon/src/handler.rs:255-260` calls `self.resolve_selector(&request.selector, "agent")` for delete requests.
- `crates/sm-daemon/src/handler.rs:371-372` calls `self.resolve_selector(&request.selector, "agent")` for label requests.
- `crates/sm-daemon/src/handler.rs:557-574` interpolates that label into user-facing selector errors.

After the CLI surface becomes `sm delete session`, a missed delete handler label would produce errors such as `unknown agent session` for a missing id. The peer also identified the adjacent `sm label` handler path. `sm label` is not CRUD, but the underlying record is still a session and W2 must already open `handler.rs`; normalizing both labels is more consistent. If label is excluded, ALP-2728 should explicitly mark that boundary so drift is deliberate.

Recommended Linear change sent over bus:

1. Add `crates/sm-daemon/src/handler.rs` as an ALP-2728 stable entry point.
2. Add acceptance requiring handler selector errors touched by the rename to use session-consistent nouns after the rename, covering delete and preferably the adjacent label handler.
3. If label is intentionally out of scope, say so explicitly in ALP-2728.

### Non-blockers from requested probes

- W2 test coverage: current tests include `crates/sm-cli/tests/cli_selector_scope_test.rs:184-190`, which exercises `sm delete agent`. ALP-2728's broad instruction to confirm delete-related tests under `crates/sm-cli/tests/` should catch this direct update.
- W4b options: The body's two reconciliation options for the `include_str!` consumer are externally falsified by acceptance #2, #4, #5, and #7. The exact option is implementation-private but verifiable by reading `crates/sm-core/src/tool_contracts.rs` during PER.
- W4b parity oracle: The current committed generated artifacts are an acceptable pre-decomposition oracle. Acceptance #4 separately requires runtime registry equivalence against a committed pre-decomposition snapshot.
- W5 static check: Current scope is adequate because acceptance #6 requires scanning all `tools/*.toml` files and every generated artifact. A future generated artifact still needs review discipline, but this is not a present ALP-2724 blocker.
- PER #7: The artifact list matches W4b acceptance #3: generated CLI help, schema rs, schema JSON directory, generated instructions, and README sections via `tool_docs.rs`.
- Cross-worker lifecycle CLI tests: Existing namespace lifecycle tests and the full `just check && just build && just test` gate are sufficient once the daemon-label gap is added to W2.

## Dependencies

Critical dependencies and surfaces reviewed:

- `clap`: CLI subcommand grammar and rejection behavior.
- `tools.toml`: current monolithic help and tool contract source.
- `crates/sm-cli/build.rs`: generates CLI help, MCP schemas, MCP instructions, and README sections.
- `crates/sm-core/src/tool_contracts.rs`: shared runtime registry consumer for daemon MCP bridge and in-process handlers.
- `crates/sm-daemon/src/handler.rs`: daemon request handlers and selector error labeling.

## Relevance to Helioy

This review reinforces that Helioy CLI unification work must trace user-visible vocabulary through daemon error paths, not only clap grammar and generated help. The same pattern likely applies to future noun migrations across runtime, session, and namespace surfaces.

## Open Questions

- Whether the orchestrator will apply the ALP-2728 daemon-label acceptance update directly or ask for a peer round first.
- Whether W5 should later harden the static `AGENT_*` check with generated-artifact discovery rather than a curated artifact list. This is not blocking for the current ALP-2724 tree.

## Peer Convergence Update

Peer reply on topic `2724-review-pass4` converged on one round-1 substantive item: ALP-2728 must add `crates/sm-daemon/src/handler.rs` as a stable entry point, require delete-handler selector labels to use session-consistent nouns, and make an explicit include or exclude decision for the adjacent `label` handler at `handler.rs:372`. Acknowledged convergence over bus and committed to re-fetching live Linear before any clean sign-off.

## Final Sign-off Update

The orchestrator applied the consensus to ALP-2728. Live Linear re-fetch confirmed the issue now names `crates/sm-daemon/src/handler.rs` as a stable entry point, scopes both delete and label handler selector labels, and adds acceptance for session-consistent daemon error text plus tests for both paths. Clean sign-off was sent on topic `2724-review-pass4` with exact phrase: "I sign off on the ALP-2724 tree as currently filed".
