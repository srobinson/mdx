---
title: ALP 2707 Pass 1 Issue Review for fmm Outline Density
type: research
tags: [fmm, linear, alp-2707, moe-review, issue-review]
summary: Pass 1 found PER mirroring gaps and implementation prescription leaks; all consensus edits were applied and the amended tree received clean sign off.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-22
updated: 2026-05-22
---

## Executive Summary

Round 1 of the ALP 2707 MoE issue review found no selector shape defect and no false schema migration precondition. The review initially found PER mirroring gaps and implementation prescription leaks; after the orchestrator amended ALP 2709, ALP 2718, ALP 2721, and ALP 2722, the amended filed tree received clean pass 1 sign off.

## Project Metadata

Language: Rust workspace.

Primary commands from `CLAUDE.md`: `just test`, `just check`, `just ci`. Direct `cargo test` is forbidden because config tests require nextest isolation.

Index status: `.fmm.db` is valid and current. `fmm validate` reported all 399 files indexed and up to date.

## Architecture Context

Relevant source paths verified live:

* `crates/fmm-store/src/schema.rs`
* `crates/fmm-store/src/connection.rs`
* `crates/fmm-cli/src/cli/sidecar.rs`
* `crates/fmm-core/src/format/yaml_formatters.rs`
* Parser entry points under `crates/fmm-core/src/parser/builtin/{rust,typescript,python}/`
* Cross language fixtures under `crates/fmm-core/tests/parser_cross_language/fixtures/`

The current schema path is real. `ensure_schema` reads the stored schema version, drops all tables when a mismatched schema exists, creates the schema, then writes the current version. `open_or_create` calls `ensure_schema`, and `fmm generate` calls `SqliteStore::open_or_create`, so a schema bump will trigger this path on the next generate run.

Query paths are separate. `open_db` checks schema version and bails on mismatch. It does not recreate the database.

## Detailed Findings

### Structural integrity

No blocker found.

ALP 2709 authorizes execution parent `ALP-2708`, and every issue listed in its `Execute:` line is a direct child of `ALP-2708`. ALP 2708 contains ALP 2717, ALP 2718, ALP 2719, ALP 2720, ALP 2721, and ALP 2722.

The prose order matches the Linear relation graph:

* ALP 2717 blocks ALP 2718, ALP 2719, ALP 2720, and ALP 2721.
* ALP 2718, ALP 2719, ALP 2720, and ALP 2721 block ALP 2722.
* ALP 2722 is blocked by those four parser and renderer workers.

### Implicit schema precondition

No blocker found.

ALP 2709 and ALP 2717 claim the existing schema mismatch path drops and recreates on schema bump. Current source supports that claim:

* `crates/fmm-store/src/schema.rs`, `ensure_schema`: reads the version, drops all tables if there is an existing mismatched schema, then recreates.
* `crates/fmm-store/src/connection.rs`, `open_or_create`: calls `schema::ensure_schema`.
* `crates/fmm-cli/src/cli/sidecar.rs`, `generate`: calls `SqliteStore::open_or_create` before staleness work.

Query paths surface mismatch through the existing error path via `open_db` and `check_schema_version_match`.

### PER scope mirroring

Resolved after amendment.

Initial finding: ALP 2722 `## Must verify` summarized worker acceptance rather than mirroring it bullet for bullet. Consensus retained these required edits:

* ALP 2717 carryover: query paths detecting schema mismatch must report through the existing error path and must not perform a full reindex.
* ALP 2719 and ALP 2720 carryover: TypeScript and Python declaration kind mappings must be mirrored explicitly, not summarized.
* ALP 2718, ALP 2719, ALP 2720 carryover: existing Rust, TypeScript, and Python parser tests pass unchanged in behavior, with new fields additive.

The earlier proposed W1 mid state item, fresh `fmm_file_outline` remains unchanged at the end of ALP 2717, was dropped because it is not gate close verifiable after ALP 2721 lands. Live re-fetch confirmed the amended ALP 2722 now includes the schema query path mirror, per-language mapping bullets, and parser additive guarantee.

### Implementation prescription leaks

Resolved after amendment.

Initial finding: several issue bodies specified mechanics rather than observable behavior. Live re-fetch confirmed:

* ALP 2709 and ALP 2721 now state the observable freshness contract and leave the mechanism to the worker.
* ALP 2718 now describes signatures as source-derived declaration header text with body bytes and docstrings excluded.
* ALP 2722 now verifies signature fidelity without requiring raw byte slice implementation mechanics.

## Dependencies

Critical dependencies observed in the audited source:

* `rusqlite` and `anyhow` in storage and schema paths.
* `fmm_store` and `fmm_core` in CLI generate paths.
* Tree sitter backed parser modules for Rust, TypeScript, and Python.

## Relevance to Helioy

This pass reinforces two Helioy planning patterns: PER issues must mirror all worker acceptance criteria, and worker bodies should avoid implementation mechanics unless they are a public contract. It also confirms that fmm structural tools are reliable in this repo for live source verification.

## Open Questions

None for pass 1. The orchestrator applied all five consensus edits, and this pane emitted the exact clean sign off: `I sign off on the ALP-2707 filed tree as currently applied (pass-1)`.
