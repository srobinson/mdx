# Consolidation and closure pass

Snapshot: `535118346ca5d0584a7a4a3da28a55be532dc3bd`  
Corpus: 43 open issues, 18 comments, from [manifest.json](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/manifest.json:1>)  
Inputs read: [AUDIT-BRIEF.md](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/AUDIT-BRIEF.md:1>), [all-issues.md](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/all-issues.md:1>), [parent-links.json](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/parent-links.json:1>), [portfolio.md](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/portfolio.md:1>), [portfolio.json](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/portfolio.json:1>), every `issue-N.md` and `issue-N.json`.

## Result

One high confidence closure is defensible: merge #459 into #460. #459 is explicitly a back-pocket research note; #460 is the concrete experiment that produces its missing evidence. The research is valuable, so the benchmark, runtime checklist, gaps, and open questions must move into #460 before closure.

The other apparent reductions are retained as split, rewrite, defer, or umbrella work. No parent with pending children is counted as complete. No shared code path is treated as duplication. Projected count is 43 current, 1 closure candidate, 42 remaining after the recommended action.

## Recommended action

### #459 merge into #460

Classification: subset merge and abandoned scheduling note, not a completed implementation.

Survivor: #460, the `just-agent` A/B experiment under #455.

Acceptance transferred:

- The execution environment and result protocol checklist: sandbox and approval policy, known cwd and PATH, process lifecycle, output shaping, safety enforcement, and verification guidance.
- The just-bash benchmark table and reproduction method, including the explicit decision not to document `rg` in the kernel contract.
- End-to-end token and retry measurement, the eval taxonomy, provider acceptance of undeclared `tool_use`, and the Vercel Sandbox path for VM or process gaps.

No standalone work is lost because #459 explicitly says “Back pocket, not scheduled”, its comment points at #460, and every item under “Open work before this is more than a note” is the measurement and evaluation plan in #460. The survivor still must build the just-bash MCP server and run the experiment. Nothing is shipped by this closure.

Evidence: [#459](https://github.com/littleorgans/transport-matters/issues/459) header and comment; [#459](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/issue-459.md:1>) research and open-work sections; [#460](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/issue-460.md:1>) experiment, measurement, and acceptance; [PR #463](https://github.com/littleorgans/transport-matters/pull/463) and [PR #464](https://github.com/littleorgans/transport-matters/pull/464) are OPEN with no merge commit and do not alter this disposition.

Prerequisite edits before closing: amend #460 with the section below, retain the #455 parent relationship, and state that #459 is absorbed reference material. Then close #459 with the draft comment below. Do not close it against a future PR or imply the A/B result exists.

#### Local draft: proposed closing comment for #459

> Closing #459 as superseded by #460 after transferring its research record. #459 was explicitly a back-pocket, unscheduled note. Its just-bash benchmark, Codex execution-kernel checklist, process and isolation gaps, and open questions are now inputs to #460's concrete just-agent experiment.
>
> #460 owns the remaining work: build the just-bash MCP server, run the same-task A/B on an appropriate frontier model, measure request bytes and end-to-end tokens separately, classify failures, and report the result honestly. No implementation or experiment result is being declared complete by this closure.

#### Local draft: survivor body amendment for #460

> ## Kernel research inputs absorbed from #459
>
> The kernel decision must cover the execution environment and result protocol, not only a tool schema: sandbox and approval policy, known cwd and explicit workdir, shell and PATH guarantees, process lifecycle, output limits and truncation, structured patching, safety enforcement below the model, and verification guidance.
>
> Preserve the just-bash benchmark and its reproduction script. `sed`, `find`, `grep`, and `wc` matched native output in the recorded benchmark; `rg` was the outlier, so the tool contract must not document `rg` until that implementation gap is resolved. Keep the OverlayFs, ReadWriteFs, and Vercel Sandbox tradeoffs, including the lack of process lifecycle and hard VM isolation in just-bash.
>
> The experiment must measure end-to-end tokens, retries, wall clock, turns, success, and failure categories, alongside request bytes. It must answer whether a provider accepts a `tool_use` for an undeclared tool and whether a companion mechanism is needed for PTY or long-running work. These findings decide whether the portable kernel is worth building on and which controls #457 needs.

## Reconciliation of the named groups

| Group | Consolidation decision | Why |
| --- | --- | --- |
| #381, #384, #630 | Retain both parents for now. #381 has open #383 and #384; #630 has open #631, #632, and #633. Rewrite #384's settled lifecycle doctrine and hand its more precise overlay work to #455's children. | The parent relationship is active work tracking. Closing either parent would hide pending requirements. |
| #455, #456, #457, #458 | Retain #455 as the design parent and #456 through #458 as distinct delivery slices. Add real sub-issue links because the snapshot only records prose links. | Viewer, builtin enablement, and prompt regeneration have different acceptance and owners. PR #463 and #464 are in flight, not shipped. |
| #593 and #595 through #600 | Retain the parent and all six open children. #2 and #594 are closed, but the authority program is pending. | The child chain is explicit and ordered; a parent with pending children is not completed. |
| #477, #632, #633 | Retain #477 for the per-run status bar. Move only its overlapping “every rejection becomes advisory” wording into the #632 reconciliation, while preserving retired and entitlement exceptions according to the final owner ruling. | The status bar is a unique UI outcome. #632 owns target resolution; #633 owns first-launch verdicts. |
| #368, #611 | Retain both. #611 supplies purpose fixtures; #368 consumes purpose classification at the breakpoint pause branch. | Shared classification is a dependency, not duplicate user outcome. |
| #459, #460 | Merge #459 into #460, after the body amendment above. | #459 is a research record with no standalone schedule; #460 is the actionable experiment. |
| #496, #498 | Retain both and split internally. #496 owns summary and tool-part projection; #498 owns search coverage, scope signaling, filters, historical reads, and capture coverage. | Both improve recall but operate on different surfaces and have different failure modes. |
| #573 | Retain and remove only its shipped third item. | HEAD `53511834` is the merged #629 resident reconciliation fix. Binding overwrite and merged-queue semantics remain open. |
| #523, #611, #446 | Retain all three. #611 is an explicit split. #446 still needs a CLI boundary decision even though both entry points share `harvest_baseline`. | Shared capture code does not satisfy the CLI acceptance; publication still lacks tool-turn and envelope references. |
| #470, #632 | Retain both. #470 owns runtime provider-refusal storage; #632 owns launch resolution and retention. | They touch the same resolver evidence but answer different lifecycle questions. |

## Retained issue ledger

Every issue not in the action above appears once here.

| Issue | Disposition and retained requirement |
| --- | --- |
| #368 | Rewrite to consume existing request-purpose classification. Keep automatic auxiliary-turn passthrough, visible classification, and the pinning test. |
| #381 | Umbrella parent with pending #383 and #384. Move future power-user versioning out of the parent acceptance when links are refreshed. |
| #383 | Keep the optional first-full-turn HTML welcome report. It is distinct from #456's operator wire viewer; share the request projection. |
| #384 | Rewrite. Current code settles much of version lifecycle, while older-harness support and upgrade behavior remain. Hand overlay details to #455 and #457/#458. |
| #413 | Defer by owner decision. The specialist Codex `skills/` write-through question remains real and is not a generic name-set cleanup. |
| #446 | Keep. Single-cell debugging and degraded acceptance differ from cohort publication. Decide the CLI boundary before `certify --all`. |
| #448 | Defer, retain. Signed retrieval, key rotation, staged rollout, cache, kill switch, and release nudges are a real supply-chain outcome. |
| #455 | Umbrella parent for overlay work. Add real links to #456 through #460 and preserve its measured token and mechanism record. |
| #456 | Keep. Read-only wire-class viewer is independently useful and acceptance for later overlay slices. PR #463 and #464 are open. |
| #457 | Keep. Harness builtin subtraction and capability declaration have a distinct token outcome. Coordinate with #597's MCP catalog filter. |
| #458 | Keep. Prompt regeneration after tool decisions is a separate correctness requirement from tool subtraction. |
| #460 | Keep as #459 survivor. The MCP server and A/B evaluation remain open. |
| #470 | Keep and rewrite its identity key. Provider refusal must survive a home wipe in a provider-account-scoped session store and remain the sanctioned launch exclusion. |
| #471 | Keep. Durable, configurable log placement is an independent diagnostic outcome; current detached logs remain under the disposable channel home. |
| #472 | Keep. Canvas grant and bypass settings reset after a home wipe; fix before #598's consent persistence claim. |
| #477 | Keep after a split edit. Retain the per-run compatibility status bar; reconcile its overlapping advisory wording with #632. |
| #482 | Keep. In-app harness login is a distinct first-run outcome with an approved six-slice plan. Reconcile credential placement with disposable-home risks. |
| #496 | Keep and split summary selection from tool-part projection. The latter has unresolved truncation, pagination, and reuse decisions. |
| #498 | Keep and split search endpoint and backfill, scope signaling, filters, session-keyed reads, and capture-coverage investigation. |
| #504 | Defer until a second presenter exists. Current one-presenter behavior is exact; resolve pushState stack semantics at the trigger. |
| #515 | Keep. `watch_status` is an additive orchestration read over existing watch ownership and shadowing state. |
| #523 | Umbrella certification and corpus work remains open. The shipped release has 26 first-turn references, zero tool-turn references, and zero envelope schemas. |
| #555 | Keep. Grok observed-model suffix normalization and a regression are distinct; grok-4.5 behavior remains unverified. |
| #565 | Keep. Presenter registration and genuine Electron binding remain the browser integrity boundary and gate the security half of #603. |
| #573 | Rewrite after #629. Keep one-binding overwrite and Codex merged-queue outcome; remove resident reconciliation as completed scope. |
| #574 | Keep. The snapshot reader exists, but the pane capture verb and gateway ownership/post-mortem behavior remain open. |
| #592 | Keep. Content-anchored overrides address live cross-request data corruption; current positional selection remains. |
| #593 | Umbrella parent with open #595 through #600. Closed #2 and #594 do not complete the program. |
| #595 | Keep. Effective grant resolution is the policy foundation and has a finite, testable acceptance table. |
| #596 | Keep. Canonical ordered MCP catalog is a no-behavior-change registry refactor and prerequisite for #597. |
| #597 | Keep. Bounded call-time MCP discovery is a unique outcome and must distinguish its capability vocabulary from #457's harness tools. |
| #598 | Keep. Consent UX and policy freezing are distinct from persistence repair in #472. |
| #599 | Keep. MCP 2.1.1 SDK port is blocked on the target catalog and filter shape, not stale. |
| #600 | Keep. Transport relocation and legacy/modern real-client proof are the final authority integration gate. |
| #602 | Defer as a design note. Its two-agent Canvas workflow has a unique unresolved product decision; closing would lose it. |
| #603 | Keep and split internally. Ship diagnosability and a separate mint verb independently; gate any window change on #565. |
| #611 | Keep. Purpose fixtures are an explicit split from #523 and a regression guard for #368. |
| #624 | Keep. Error vocabulary preserves code and message for orchestration and should precede a frozen #596 tool schema. |
| #630 | Umbrella parent with pending #631 through #633. Reconcile its lifecycle boundary with #384 without closing either parent. |
| #631 | Keep. Refreshed Codex enumeration is the discovery fix for newly released models and interacts with #470 retention rules. |
| #632 | Keep and rewrite the entitlement bullet per its 2026-09-05 comment. Retain version-independent target offering and fail-open launchability. |
| #633 | Keep and split internally. Reference selection, first-launch state, durable queueing, retention, and diagnostics are distinct; owner ruling is needed on provisional degraded versus unknown. |

## Uncertainties and guardrails

- The refreshed Codex catalog has not been measured for the account-awareness premise in #632. Record that result on #470 before changing entitlement resolution.
- #633's provisional degraded posture conflicts with the ratified #384 and `CLAUDE.md` support semantics. This pass leaves the product decision open.
- The `certify --all` publication run is unassigned. The snapshot release still carries only first-turn references, so #523 and #633 cannot claim complete shape coverage yet.
- The state of #385 and #386 named in #381's historical implementation order is outside this manifest and was not used to close #381.
- No runtime or provider-spending probes were run. Code and git inspection was read only. HEAD proves #629 is shipped; PR #463 and #464 remain in flight.

## Completion

Reviewed 43 issues and all 18 manifest-counted comments. No source, GitHub issue, comment, label, or runtime state was changed.  
Report companion: [consolidation.json](</Users/alphab/.mdx/projects/tm-issue-audit-2026-09-05-fb442de3/consolidation.json:1>).
