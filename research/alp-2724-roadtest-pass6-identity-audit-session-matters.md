---
title: ALP-2724 Road-Test Pass 6 Identity Audit Finding
type: research
tags: [session-matters, alp-2724, linear-review, identity-matters, audit]
summary: Pass 6 found three substantive gaps around label mutation auth/audit, session-record MCP output schemas, and JSON label behavior.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Pass 6 reviewed the ALP-2724 road-test corrective wave against live Linear state and current source. I found one substantive issue and then verified two additional peer findings. The final pass 6 consensus is: preserve explicit auth/audit semantics for `sm label`, broaden session-record MCP output schemas to include `labels`, `namespace`, and `dir`, and bind JSON label behavior so `--show-labels` is human-render only while `--json` always emits the full `Session`.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Build system: Cargo plus `just`
- Current worktree: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/session-matters-worktrees/nancy-ALP-2724`
- fmm: `.fmm.db` present, but the warroom brief reported fmm MCP schema mismatch for this review, so source probing used filesystem reads and ripgrep.

## Architecture Context

`session-matters` exposes `sm` as the local CLI and `smd` as the daemon. Mutating daemon operations authorize through identity-matters and write identity audit rows through `IdentityClient::authorize`.

Relevant live source entry points:

- `crates/sm-daemon/src/handler.rs`: `label_one` authorizes label mutation with `Action::Link`; `delete_one` uses `Action::Kill`; `capture` uses `Action::Read`.
- `crates/sm-daemon/src/identity_client.rs`: `IdentityClient::authorize` delegates to the identity-matters stub authorizer and audit sink.
- `crates/sm-cli/tests/mcp_protocol_test.rs`: existing audit tests assert actions for run, link, logs, doctor, delete, mail, and nudge, but do not assert an audit row for label mutation.
- `lilo-im-core-0.1.0`: `Action` includes `Link` but no label-specific action.

## Detailed Findings

### Substantive gap: label mutation audit crosses the link-removal boundary

Live source shows label mutation currently uses the identity action named for link adoption:

- `crates/sm-daemon/src/handler.rs::label_one` calls `authorize(..., Action::Link, session_resource(target_id))` before applying `store.apply_label_mutation`.
- ALP-2752 removes `sm link` from CLI and MCP surfaces and deletes link protocol and daemon handling paths.
- ALP-2745 owns the label model and `sm get session --show-labels`, but its body does not name identity-matters authorization or audit preservation for `sm label`.
- ALP-2733 PER acceptance checks behavior and schema visibility, but does not require audit rows for label mutations.

This is execution-relevant. An implementer can remove link paths and still leave label audit rows as `Link`, or remove/rework the action and accidentally drop authorization/audit coverage for labels. Either outcome makes the mutation path hard to review because behavior tests can pass while audit semantics drift.

### Recommended Linear changes sent on bus

I sent a conditional signoff to the peer and CCed the orchestrator with this precise change:

1. Update ALP-2745 Scope, Affected files, Acceptance, and Verification to require explicit identity-matters authorization and audit coverage for `sm label` mutations. The implementation should preserve per-target authorization and audit rows after `sm link` removal, either by deliberately retaining the current identity action mapping or introducing the appropriate label-specific action if identity-matters supports it. Add a test querying the identity audit sink after `session_label` / `sm label` and asserting the expected mutation audit action.
2. Update ALP-2733 PER acceptance with the same audit check so review cannot close on behavior alone while audit semantics drift.


### Peer findings verified after initial signoff

The peer identified two additional substantive issues. I verified both against live source and sent consensus to the peer and orchestrator.

1. MCP output schema drift is broader than labels. `crates/sm-core/src/session.rs` defines `Session` with `namespace`, `dir`, and `labels`; `crates/sm-cli/src/mcp/generated_schema/session_get.json`, `session_list.json`, and `session_run.json` enumerate session-record output properties but omit all three. The ALP-2745 schema invariant should be renamed from a labels invariant to a session-record field invariant and require all three fields across all three schemas.
2. JSON label behavior is under-specified. `crates/sm-cli/src/cli/get.rs` serializes the full `Session` value for `--json` without consulting `--show-labels`, so the binding contract should say `--show-labels` is human-render only and `--json` always emits full sessions including labels. Add a regression test for labels in JSON without `--show-labels`.

## Dependencies

Key relevant dependencies:

- `lilo-im-core`: identity-matters action and resource model.
- `lilo-im-store`: audit sink and query helpers.
- `lilo-im-stub`: local authorizer used by `IdentityClient`.

## Relevance to Helioy

The finding protects Helioy's control-plane audit trail. Label mutations are operator metadata changes that affect selection and grouping. They should remain authorized and auditable after unrelated adoption terminology is removed from the CLI/MCP surface.

## Open Questions

- Should identity-matters add a dedicated `Action::Label`, or should session-matters deliberately continue using `Action::Link` as a broader metadata mutation action until identity-matters evolves?
- Should this audit expectation also apply to namespace mutations in the same PER checklist, or is current namespace authorization coverage sufficient for this wave?
