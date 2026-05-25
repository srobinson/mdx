---
title: Phase 2 identity import gate review
type: research
tags: [littleorgans, linear, moe-review, identity, rust]
summary: Live review of ALP-2812 Phase 2 identity import gate found selector, verification, and code contract defects before execution.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

A live MoE review directive for ALP-2812 was received over helioy-bus and answered with six substantive findings. The issue set is not ready for execution as filed because W2 can be selected before its test dependency exists, the post execution review lacks its W5 blocker edge, and several verification commands are not exit status meaningful in the current repo environment.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans`
- Branch: `main`
- Current monorepo fmm: `.fmm.db` present and `fmm validate` passed for 10 indexed files.
- Current monorepo layout from fmm: `crates/` has 9 indexed Rust files, `tools/` has 1 indexed Rust file.
- Current workspace version and edition: root `Cargo.toml` uses version `0.8.0` and edition `2024`.
- Source repository: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters`
- Source repository HEAD: `e01affa2a6400f3194e1ae236aee04019c1dd3e6`, matching the Linear provenance expectation.
- Source repository fmm note: `.fmm.db` exists but was built with fmm `0.2.9`; local fmm is `0.3.0`. I did not regenerate the index during this read only review, and used targeted shell inspection for source details.

## Architecture

Phase 2 imports the identity substrate into the new littleorgans monorepo:

- `identity-matters/crates/im-core/` to `crates/lilo-im-core/`, published.
- `identity-matters/crates/im-store/` to `crates/lilo-im-store/`, published, rusqlite preserved.
- `identity-matters/crates/im-stub/` to `crates/lilo-im-stub/`, published.
- New internal factory crate at `internal/identity/service/`, unpublished.

The intended worker flow is W1 core, W2 store, W3 stub, W4 service, W5 acceptance, then ALP-2828 post execution review. Current source shows a hidden W2 to W3 dependency through store tests, so the filed diamond ordering does not match executable reality.

## Key Patterns

- Linear relation edges matter as much as prose. Selector release depends on `blockedBy`, not only the gate body's `Required order:` line.
- Verification snippets must be run against current command output, not just read for intent.
- Imported source APIs can invalidate issue prose. `StubAuthorizer` borrows its audit sink, so service composition should be expressed as observable behavior rather than as a prescriptive owned shape.

## Detailed Findings

### F1: W2 can be selected before its test dependency exists

Live Linear showed ALP-2824 is blocked only by ALP-2823. Current identity source shows `im-store` tests require `lilo-im-stub`:

- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters/crates/im-store/Cargo.toml:29-33` declares `lilo-im-stub.workspace = true` as a dev dependency.
- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters/crates/im-store/tests/audit.rs:10` imports `StubAuthorizer`.
- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters/crates/im-store/tests/audit.rs:37-38` constructs `StubAuthorizer::new(&sink, process_uid)`.

Risk: Nancy can select W2 before W3, but W2 cannot satisfy `cargo test -p lilo-im-store` until `lilo-im-stub` exists in the monorepo.

Required change sent on bus: make ALP-2824 blocked by ALP-2825 and update the gate Required order, or remove W2's test requirement until after W3 lands.

### F2: PER is structurally unblocked

Live Linear showed ALP-2828 `relations.blockedBy=[]`, while ALP-2829 says `ALP-2827 before ALP-2828`.

Risk: the selector can release post execution review before W5 acceptance, commit, push, and fmm regeneration.

Required change sent on bus: add ALP-2827 as a blocker of ALP-2828 and add the reciprocal `blocks` edge.

### F3: ALP-2827 package presence jq checks are wrong

Current repo command evidence:

```text
jq -e '([.packages[].name] - ["lilo-im-core","lilo-im-store","lilo-im-stub","lilo-identity-service"]) | (length < [.packages[].name] | length)' /tmp/littleorgans-metadata.json
status=5
jq: error: Cannot index array with string "packages"
```

The acceptance expression using `inside([...]) | not` returned `true` before the four packages exist, so it does not prove package presence.

Required change sent on bus: replace with a required names subtraction against `[.packages[].name]` and assert the missing set length is zero.

### F4: `lilo` is not on PATH in the current repo environment

Command evidence:

```text
command -v lilo
# empty
lilo --version
# status 127, command not found
cargo run -q -p lilo -- --version
# lilo 0.8.0
```

Risk: ALP-2827 and ALP-2828 depend on an implicit PATH install that the repository does not provide.

Required change sent on bus: verify the repo built binary with `cargo run -q -p lilo -- --version` and `cargo run -q -p lilo -- doctor --output json`, or build and call `./target/debug/lilo`.

### F5: ALP-2824 cargo tree greps are not exit status meaningful

Current cargo tree output for an existing package shows direct dependencies with tree prefixes:

```text
lilo v0.8.0 (.../crates/lilo)
├── clap v4.6.1
├── lilo-common v0.8.0 (.../crates/lilo-common)
├── serde v1.0.228
└── serde_json v1.0.150
```

ALP-2824 uses `grep -q '^rusqlite'`, which will not match box prefixed cargo tree dependency lines. Its `grep -vq '^sqlx'` shape succeeds when any non sqlx line exists, so it does not prove absence.

Required change sent on bus: use a grep that matches package text in the depth 1 output, such as `grep -F 'rusqlite v'`, and use a negated grep for `sqlx v`.

### F6: ALP-2826 service composition overprescribes a self referential shape

Current source contract:

- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters/crates/im-stub/src/lib.rs:11-18` defines `StubAuthorizer<'a, S>` with `audit_sink: &'a S`.
- `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters/crates/im-store/src/sqlite/audit.rs:52-61` defines owned `SqliteAuditSink` and `connect` construction.

ALP-2826 asks for `IdentityService` to hold the composed `Authorizer` plus audit sink. Taken literally, this points workers at a self referential service shape. The issue also says the composition shape is the worker's call, so the durable fix is to remove the holding prescription and require observable behavior instead.

Required change sent on bus: allow a non self referential shape, such as creating a `StubAuthorizer` per authorization call, and keep acceptance focused on factory construction plus an authorization call that writes an audit row.

## Dependencies

Identity source dependencies were verified from `identity-matters/Cargo.toml` and crate manifests:

- Common identity deps: `async-trait`, `chrono`, `nix`, `serde`, `serde_json`, `thiserror`, `tokio`, `uuid`.
- Store specific dep: `rusqlite = { version = "0.37", features = ["bundled"] }`.
- Test deps: `insta`, `tempfile`, plus `lilo-im-stub` for store tests.

## Relevance to Helioy

This review protects the Nancy selector contract. The immediate reusable lesson is that clean looking gate prose can still be unsafe when test dependencies encode a hidden worker order and Linear relation edges do not mirror that order.

## Peer Consensus State

The peer replied on `alp2812-review-pass1` and concurred with all six findings I sent. I accepted the peer's two findings on workspace homepage inheritance and fmm CLI precheck, then sent a conditional signoff covering the full eight change set. The peer also sent conditional signoff on the same eight changes and reported no additional substantive findings.

Consensus changes required before clean verification:

1. Fix W2 to W3 ordering or defer W2 store tests until W3.
2. Add the ALP-2827 to ALP-2828 blocker edge.
3. Replace broken ALP-2827 package presence jq checks.
4. Make ALP-2827 and ALP-2829 `lilo` checks repo resident.
5. Replace ALP-2824 cargo tree rusqlite and sqlx greps.
6. Remove the ALP-2826 owned composed authorizer plus sink prescription.
7. Resolve workspace homepage inheritance.
8. Add an fmm CLI precheck or gate precondition.

## Verification After Linear Edits

A `VERIFY v1` message on `alp2812-review-pass1` reported that the eight consensus changes were applied. I re-read live Linear with `includeRelations` for ALP-2812, ALP-2829, and ALP-2823 through ALP-2828. The edited state matches the consensus set: the worker order is W1 to W3 to W2 to W4 to W5 to PER, ALP-2828 is blocked by ALP-2827, broken jq checks were replaced, `lilo` checks use `cargo run -q -p lilo --`, cargo tree greps are exit-status meaningful, ALP-2826 no longer prescribes owning both a borrowed authorizer and sink, homepage inheritance is handled by adding workspace homepage, and fmm tool preconditions are present. I sent `V|I sign off on ALP-2812 Phase 2 identity import gate artifact as currently filed`.

## Peer Final Signoff

The peer sent `V|verified|all 8 changes properly applied; no citation drift; no new defects` and signed off on ALP-2812 Phase 2 identity import gate as currently filed. Both review panes have now verified the amended Linear state and signed off clean after the orchestrator's edits.

## Open Questions

- A fresh pass should rerun after edits because the MoE workflow exits only on a clean round one pass or a smell test stop.
