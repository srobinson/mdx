# Transport Matters documentation sweep loss audit

## Scope and verdict

Target: `af52318d2950f56efce3113fbe2abd73aba72ec4..1c3e339b5d30a345a3b041d9a8cbb370470957f4` in a pristine detached worktree.

Verdict: **issue**. The sweep removes eight decisions, rationales, or pieces of open work that have no equivalent in the target tree.

I classified all 300 deletion hunks, covering 4,012 removed lines in 15 documents. Removed implementation inventories, field lists, route and error tables, timings, counts, verification checklists, and records of completed work are excluded from the findings below.

## Findings

### High: name conflict errors lost their visibility boundary

What was lost: a name conflict may include the holder run id only when the caller can observe that run. This prevents a failed name claim from disclosing an otherwise invisible run.

Source: `af52318d:docs/RUN-IDENTITY.md`, symbol `Lease model`.

Current state: `1c3e339b:docs/RUN-IDENTITY.md`, symbols `Lease model` and `Public run references`, retain owner and workspace scoping but omit the conflict disclosure rule. No equivalent rule exists in current documentation, application code, or tests.

Restore at: `docs/RUN-IDENTITY.md`, symbol `Lease model`, beside the conflict and reconciliation semantics.

### High: historical reader removal lost its migration precondition

What was lost: a historical reader may be removed only after a deterministic migration produces an equivalent supported artifact and retains the raw evidence. The current open question about retention duration does not preserve this safety condition.

Source: `af52318d:docs/HARNESS-COMPATIBILITY.md`, symbol `Historical read compatibility`.

Current state: `1c3e339b:docs/HARNESS-COMPATIBILITY.md`, symbol `Historical read compatibility`, preserves recorded revision dispatch, the resume or fork bridge, and `historical_contract_unsupported`. Symbol `Open decisions` retains the future retention horizon but no migration requirement. No equivalent rule exists elsewhere in the target tree.

Restore at: `docs/HARNESS-COMPATIBILITY.md`, symbol `Historical read compatibility`, before `Open decisions`.

### Medium: failed batch preparation no longer requires lease cleanup

What was lost: batch preparation claims all candidate names before any process starts, and a preparation failure releases every candidate lease. The target preserves the claim timing but drops the all leases cleanup decision.

Source: `af52318d:docs/RUN-IDENTITY.md`, symbol `Lease model`.

Current state: `1c3e339b:docs/RUN-IDENTITY.md`, symbol `Lease model`, says batch preparation claims all names before the first start. `1c3e339b:docs/plans/RUNTIME-SURFACING-PLAN.md`, symbol `Eval isolation (must survive)`, says preparation failure starts no candidate. Neither states that every claimed lease is released. S4 remains ahead, so code cannot recover this contract.

Restore at: `docs/RUN-IDENTITY.md`, symbol `Lease model`, immediately after the batch claim rule.

### Medium: the minimum supported version lost its retirement policy

What was lost: `minimum_version` rises only when Transport Matters retires a superseded schema. This is the policy that prevents a routine baseline refresh from silently dropping older compatible harness versions.

Source: `af52318d:docs/HARNESS-COMPATIBILITY.md`, symbols `Core policy` and `Harness compatibility release`.

Current state: `1c3e339b:docs/HARNESS-COMPATIBILITY.md`, symbols `Core policy` and `Identity and release`, define optimistic open range support and the minimum field but omit the condition for raising it. No equivalent survives elsewhere.

Restore at: `docs/HARNESS-COMPATIBILITY.md`, symbol `Core policy`, beside the optimistic range rule.

### Medium: setup mutations lost explicit user confirmation

What was lost: install, update, and sign in actions belong to versioned code adapters and require a user click plus confirmation before external mutation. Compatibility data may select an installed adapter or trusted URL but may never supply a command.

Source: `af52318d:docs/plans/RUNTIME-SURFACING-PLAN.md`, symbol `First run harness setup`.

Current state: `1c3e339b:NOW.md`, symbols `Phase 1` and `One login driver, because the harnesses already do the work`, preserve in application remediation and the harness owned login flow. `1c3e339b:docs/HARNESS-COMPATIBILITY.md`, symbol `Signed data updates`, preserves the no executable content boundary. The explicit user initiation and confirmation requirement exists nowhere.

Restore at: `NOW.md`, symbol `One login driver, because the harnesses already do the work`, as the action safety rule for the active first run work.

### Medium: desktop update and signing sequencing disappeared

What was lost: ship a notify only version feed first, add silent in place updates only after Apple signing and notarization, and treat signing as its own release gate. This was open distribution work, including the reason silent updates depend on identity and notarization.

Source: `af52318d:docs/WHEEL.md`, symbols `Updates`, `The packaging track`, and `Signing / notarization`.

Current state: `1c3e339b:docs/WHEEL.md` deliberately narrows to artifact verification. No current document carries the update sequence. `justfile` retains only an implementation comment that DMG signing is a later slice, which does not preserve the product rollout decision.

Restore at: `NOW.md`, symbol `Parking lot, unscheduled`, as one compact distribution marker with its signing dependency. Keep `docs/WHEEL.md` focused on verification.

### Medium: commercial positioning and price were deleted

What was lost: the proposed single player purchase, optional subscription, target customer spend band, seat scaling, and enterprise tier relationship. These are product positioning decisions and open price posture. They cannot be reconstructed from code.

Source: `af52318d:docs/NORTHSTAR.md`, symbol `Positioning and price`.

Current state: `1c3e339b:docs/NORTHSTAR.md`, symbols `The product` and `Teams and identity`, preserve the product and enterprise value but omit the commercial model. No equivalent survives elsewhere.

Restore at: `docs/NORTHSTAR.md`, a compact `Positioning` symbol after `The product`, clearly marked as current hypothesis if the price remains unsettled.

### Low: the generated name dictionary lost its curation rationale

What was lost: the curation policy for `moons-v1`, including spoken ambiguity, ASCII loss, technology, model, product, and command collisions, and the named reason `io`, `pan`, `titan`, and `atlas` are excluded. The membership artifact can show absence but cannot explain it.

Source: `af52318d:docs/RUN-IDENTITY.md`, symbol `moons-v1 dictionary`.

Current state: `1c3e339b:docs/RUN-IDENTITY.md`, symbol `Generated names`, preserves NASA provenance, cultural and pronunciation review, normative membership, and immutable revisions. The remaining selection rationale exists nowhere, and the dictionary artifact has not landed because S3 remains ahead.

Restore at: `docs/RUN-IDENTITY.md`, symbol `Generated names`, as a short curation policy rather than a copied membership list.

## Required survival checks

All named must survive content is present and legible:

| Required content | Surviving path and symbol |
| --- | --- |
| Advisory to enforcing rollout; flip ships in a release | `docs/HARNESS-COMPATIBILITY.md`, `Rollout posture`; `docs/plans/RUNTIME-SURFACING-S2-PLAN.md`, `One way flip to enforcing` |
| Authentication and access never gate launch | `docs/HARNESS-COMPATIBILITY.md`, `Enablement, compatibility, and auth`; `docs/LAUNCH-CONTRACT.md`, `Resolution` |
| Complete, partial, and failed absence semantics | `docs/HARNESS-COMPATIBILITY.md`, `Observation absence semantics` |
| Prompt proof and sticky `model_rejected` | `docs/LAUNCH-CONTRACT.md`, `Result, receipt, and prompt proof`; `docs/CONTROLPLANE.md`, `Prompt`, `Launch`, and `Watch` |
| Resume or fork bridge and recorded revision reader dispatch | `docs/HARNESS-COMPATIBILITY.md`, `Historical read compatibility` |
| Fixed name platform trust and lease retention through ambiguity | `docs/RUN-IDENTITY.md`, `Platform fixed names` and `Lease model` |
| Publisher data only versus product release gate | `docs/HARNESS-COMPATIBILITY.md`, `Publication lifecycle` |
| Seal `WorkspaceSnapshot` and `BriefArtifact` before spawn | `docs/plans/RUNTIME-SURFACING-PLAN.md`, `Eval isolation (must survive)` |
| S5 blinded judge entitlement | `docs/plans/RUNTIME-SURFACING-PLAN.md`, `Blinded judge entitlement (must survive)` |
| Platform verification ownership and Linux versus macOS rationale | `docs/WHEEL.md`, `Platform ownership` and `What the proof means` |

## Owner protected files

The three protected files are byte identical between base and target:

| Path | Git blob |
| --- | --- |
| `docs/process/WARROOM.md` | `90b72874e75de26ab6255d5910c349de9d2cb925` |
| `docs/process/AGENT-PROFILES.md` | `d46733f79700629771903c3e1936898ac65aec97` |
| `docs/plans/RUNTIME-SURFACING-S1-PLAN.md` | `b1b475753ba76b6d06af2a61c1261307426367f8` |

`git diff --check af52318d..1c3e339b -- '*.md'` also passes.
