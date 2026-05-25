---
title: ALP-2812 Pass 2 Identity Import Review for littleorgans
type: research
tags: [littleorgans, linear, moe-review, identity, phase-2]
summary: Live pass 2 review found stale version and PATH contracts, non-falsifying PER metadata checks, LOC proof drift, and public brand metadata leakage risk.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-26
updated: 2026-05-26
---

## Executive Summary

This review audited the ALP-2812 Phase 2 identity import issue set against the current littleorgans checkout on branch `chore/justfile-playbook-parity`. The issue set is broadly aligned with the intended import shape, but several acceptance and review checks do not match the current command contract or project rules.

The most immediate blocker is stale version and PATH language: current `lilo --version` output is `littleorgans 0.8.0` or `littleorgans 0.8.0+<sha>`, while ALP-2829, ALP-2827, and ALP-2828 still assert `lilo 0.8.0` and say `lilo` is not on PATH.

## Project Metadata

- Language: Rust 1.90, Cargo workspace, edition 2024.
- Build orchestration: Cargo, Moon, Just.
- Current branch: `chore/justfile-playbook-parity`.
- fmm state: `.fmm.db` exists in the monorepo and `fmm validate` passed for 11 indexed files.
- Source import repo: `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/identity-matters` at `e01affa2a6400f3194e1ae236aee04019c1dd3e6`.
- Source import repo fmm state: `.fmm.db` exists but was built with fmm 0.2.9, while current fmm is 0.3.0. I did not regenerate it during this read-only review. I used shell based symbol and manifest probes for that repo.

## Architecture

Current monorepo structure is still Phase 1 scale:

- `crates/lilo`: published CLI binary crate.
- `crates/lilo-common`: common diagnostics, logging, and exit codes.
- `crates/lilo-paths`: path resolution for `LILO_HOME`, socket, pid, DB, and runtime paths.
- `tools/xtask`: unpublished workspace tool crate.

fmm reported 11 indexed files and 1,107 LOC, grouped under `crates/` and `tools/`. Key current source entry points:

- `crates/lilo/src/main.rs:10` defines `VERSION` from `LILO_CLI_VERSION`.
- `crates/lilo/build.rs:7-19` emits the version string and optionally appends the git SHA.
- `crates/lilo/tests/version.rs:11-13` asserts the displayed package name is `littleorgans`.
- `justfile:3` resolves `LILO_LOCAL_BIN` to `~/.cargo/bin/lilo` by default.
- `justfile:16-17` maps `just test` to `cargo nextest run --workspace`.
- `scripts/check-loc-limit.sh:15-19` is the authored LOC enforcement path.

The Phase 2 identity import target shape matches the locked architecture:

- Published crates under `crates/lilo-im-core`, `crates/lilo-im-stub`, `crates/lilo-im-store`.
- Internal service crate under `internal/identity/service` with `publish = false`.
- W4 service factory shape is consistent with `CLAUDE.md:70-73` and synthesis rev03, which place non-published substrate code under `internal/<substrate>/<role>` and require `IdentityService::build` style composition.

## Key Patterns

- fmm is useful for the current monorepo and should remain part of structural review. It is not currently usable for the source identity repo without regeneration because of a version mismatch.
- The root justfile is the operator surface. Direct Cargo checks are useful diagnostics, but closeout proof should include the justfile commands required by `CLAUDE.md:168-171`.
- For generated or enforcement surfaces, avoid duplicating shell logic in Linear issue bodies. Point review issues at the authored script or generator instead.

## Detailed Findings

### F c1: Version and PATH contract drift

Evidence:

- `crates/lilo/tests/version.rs:11-13` expects `littleorgans {version}`.
- `cargo run -q -p lilo -- --version` printed `littleorgans 0.8.0`.
- `lilo --version` printed `littleorgans 0.8.0+f4d05ff`.
- `justfile:3` sets `LILO_LOCAL_BIN` to `~/.cargo/bin/lilo` by default.
- `justfile:22-23` defines the `just lilo` wrapper over `cargo run -p lilo --bin lilo --`.
- `justfile:29-53` defines install recipes that install and then run the target binary.

Risk:

ALP-2829, ALP-2827, and ALP-2828 still assert `lilo 0.8.0` and say `lilo` is not on PATH. Executors and reviewers will fail against current observable behavior.

Required change:

Update gate, W5, and PER version and PATH assertions to the current `littleorgans 0.8.0[+sha]` contract and the installed `lilo` precondition.

### F c2: PER internal crate count command is non-falsifying

Evidence:

- Current command result: `cargo metadata --no-deps --format-version=1 | jq -e '[.packages[] | select(.publish == [] or .publish == null) | .name] | length'` returned status 0 and `4` on Phase 1.
- Cargo metadata serializes publishable crates with `publish = null`; current `lilo`, `lilo-common`, and `lilo-paths` appear in that result.
- `tools/xtask/Cargo.toml` has `publish = false`, which serializes as `[]`.
- ALP-2826's own W4 acceptance correctly checks `.publish == []` for `lilo-identity-service`.

Risk:

The PER integration check can pass while counting public crates as internal. It also checks only that a number exists, not that the count or set matches expectation.

Required change:

Compare the exact expected internal set using `.publish == []`, for example Phase 2 should include `xtask` and `lilo-identity-service`, plus any other explicitly internal crates added by then.

### F c3: LOC proof drifts from the authored enforcement path

Evidence:

- `scripts/check-loc-limit.sh:15-19` prunes `.git`, `.moon/cache`, `.nancy`, and `target`, then checks `*.rs`, `*.ts`, `*.tsx`, `*.js`, `*.jsx`, and `*.py`.
- ALP-2828 contains an ad hoc `find` query checking `*.rs`, `*.md`, `*.toml`, `*.yml`, and `*.yaml`, pruning only `target` and `.git`.
- A temporary probe showed the PER query catches a 701 line `.md` and a `.nancy/*.rs` file, but misses a 701 line `.py` file that the native script catches.

Risk:

PER and CI can approve different LOC surfaces. The review issue should not duplicate the enforcement logic with a divergent selector.

Required change:

Make PER run `bash scripts/check-loc-limit.sh`, or update that script once and have PER call the same source of truth.

### F c4: Public brand metadata can leak internal project naming

Evidence:

- `CLAUDE.md:18-23` says the broader project name stays internal and user visible names, package names, UI copy, public docs, and mirror output use littleorgans or `lilo`.
- `CLAUDE.md:37-39` says public organization, mirrors, binary, domain, docs, and install story converge on littleorgans and `lilo`; internal project framing stays internal.
- Source manifests carry public `helioy` metadata:
  - `identity-matters/crates/im-core/Cargo.toml:3` uses `Helioy v1 IAM` in the description.
  - `identity-matters/crates/im-core/Cargo.toml:11`, `im-stub/Cargo.toml:11`, and `im-store/Cargo.toml:11` include `helioy` in crate keywords.
- ALP-2823, ALP-2824, ALP-2825, and ALP-2828 require source or metadata preservation, which would forbid correcting that public metadata during import.

Risk:

Published crates can ship internal brand metadata, and PER can reject the correction as a non-verbatim import.

Required change:

Authorize public-facing metadata and documentation normalization to littleorgans and `lilo`, or record an explicit human exception if preserving the old public metadata is intended.

## Non-findings

- PER worker mirror depth is materially complete. W1 through W5 acceptance bullets are mirrored, sometimes with useful extra checks from each worker's capability section. No silent acceptance drop was found.
- W4's `internal/identity/service` crate remains the cleanest target shape against the current source. `StubAuthorizer` borrows an `AuditSink`, while `SqliteAuditSink` owns a database path and exposes query APIs. A separate service crate can choose owned sink plus per-call authorizer construction without a self-referential struct.
- Source provenance currently matches: identity-matters HEAD is `e01affa2a6400f3194e1ae236aee04019c1dd3e6`.
- Current monorepo `.fmm.db` is present and validates cleanly.

## Dependencies

Critical runtime and verification dependencies observed in live source:

- `clap` for the CLI.
- `serde` and `serde_json` for output and status JSON.
- `thiserror` for crate boundary errors.
- `tracing` and `tracing-subscriber` for logging.
- `cargo-nextest` is installed and used by `just test`.
- `moon` 2.2.5 is installed and orchestrates CI tasks.
- `jq` 1.8.1 is installed and used by metadata and doctor checks.
- `fmm` 0.3.0 is installed and validates the monorepo index.

Identity source dependency contracts from `identity-matters/Cargo.toml` include `async-trait`, `chrono`, `insta`, `nix`, `rusqlite` with `bundled`, `tempfile`, `tokio`, and `uuid` with `serde` and `v7`.

## Relevance to Helioy

The import plan is a good test of the monorepo's public and internal boundary rules. The main Helioy specific risk is public metadata leakage from the old identity source. Phase 2 should normalize public metadata now, because v0.8.0 is pre-release and breaking changes are allowed.

## Open Questions

- Whether the orchestrator and peer accept the four pass 2 findings as substantive.
- Whether public source content should be normalized during import, or whether Stuart wants a one-off exception for existing identity crate metadata.
- Whether W5 should include `just check && just build && just test` explicitly, or rely on the issue's narrower Cargo and Moon commands plus project-wide closeout rules. I did not send this as a separate bus finding because the four findings above were more directly tied to the requested probes.

## Bus Reconciliation Update

After the initial findings were sent, the peer replied with three findings on the same topic:

- Peer c1 matched the version and PATH contract drift finding.
- Peer c2 matched the non-falsifying PER internal crate count finding.
- Peer c3 matched the LOC enforcement drift finding.

I replied on the bus with:

```text
A|accept:c1,c2,c3|reject:none|missing:c4
```

I then sent conditional signoff covering all four substantive changes:

```text
S|I sign off conditional on the following changes: 1. c1 update ALP-2829/2827/2828 version and PATH assertions to current `littleorgans 0.8.0[+sha]` and installed `lilo` contract. 2. c2 tighten PER internal-publish check to `publish == []` with an exact expected set or remove as redundant with W4. 3. c3 replace PER LOC inline find with `bash scripts/check-loc-limit.sh` or make the script the single broadened source of truth. 4. c4 authorize public metadata/docs normalization from internal Helioy/identity-matters wording to littleorgans/`lilo`, or record an explicit human exception.
```

## Peer Agreement Update

The peer subsequently accepted all four findings:

```text
A|accept:c1,c2,c3,c4|reject:none|missing:none
```

They independently verified c4 by checking the identity source manifests and the root brand rules in `CLAUDE.md`. The peer agreed that ALP-2823's metadata preservation requirement and ALP-2828's no-rewrite rule would compel publishing internal `helioy` branding unless the issues authorize metadata normalization or record an explicit human exception.

## Peer Conditional Signoff Update

The peer sent conditional signoff on the same four changes:

1. Replace stale `lilo 0.8.0` assertions with the current `littleorgans 0.8.0` or tolerant `littleorgans 0.8.0+sha` contract, and drop stale "lilo is not on PATH" prose.
2. Tighten or drop ALP-2828's internal crate count check so it does not count `publish = null` crates.
3. Replace ALP-2828's inline LOC `find` block with `bash scripts/check-loc-limit.sh`.
4. Resolve the public `helioy`/`Helioy` metadata leak by authorizing manifest metadata normalization during import or recording an explicit human exception.

Peer noted that pass 2 exit condition is not met on round 1 because four conditional changes remain. A pass 2 verification round is required after the orchestrator applies changes.

## Verify Round Update

A VERIFY v1 message reported that c1 through c4 had been applied across ALP-2829, ALP-2823, ALP-2824, ALP-2825, ALP-2827, and ALP-2828. I re-read live Linear for ALP-2812, ALP-2829, ALP-2823, ALP-2824, ALP-2825, ALP-2826, ALP-2827, and ALP-2828 with relations.

Verification result:

- c1 was applied. Gate, W5, and PER now use the `littleorgans 0.8.0[+sha]` version contract and `command -v lilo` precondition.
- c2 was applied. PER now checks the exact internal crate set with `.publish == []`: `lilo-identity-service` and `xtask`.
- c3 was applied. PER now calls `bash scripts/check-loc-limit.sh` as the single source of truth for the 700 LOC cap.
- c4 was applied. W1, W2, W3, gate, and PER now authorize the narrow metadata normalization to drop public `helioy` branding while keeping broader `Identity Matters` framing out of scope.

I sent:

```text
V|I sign off on ALP-2812 Phase 2 identity import gate artifact as currently filed
```

## Final Consensus Update

The peer sent a final V-clean verification after re-fetching all eight Linear IDs and re-checking source-of-truth surfaces:

```text
V|I sign off on ALP-2812 Phase 2 identity import gate artifact as currently filed.
```

Peer verification confirmed:

- c1 landed: current `lilo --version` contract and PATH precondition are reflected in ALP-2827, ALP-2828, and ALP-2829.
- c2 landed: ALP-2828 now checks the exact `publish == []` internal set expected at the Phase 2 endpoint.
- c3 landed: ALP-2828 now uses `bash scripts/check-loc-limit.sh` for the 700 LOC cap.
- c4 landed: imported identity crate manifests have a narrow authorized metadata normalization exception to drop public `helioy` branding while leaving `Identity Matters` framing out of scope.

Exit condition is met. Both panes are V-clean. The ALP-2812 Phase 2 identity import gate artifact is consensus-ready for execution.
