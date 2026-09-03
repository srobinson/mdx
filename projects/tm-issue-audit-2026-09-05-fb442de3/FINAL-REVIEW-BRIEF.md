# Independent final grooming review

Review the concrete proposal in proposed-grooming.json, with github-edit-drafts.md and consolidation.md. Use proposed-grooming.md only as the human view; avoid rereading duplicate content. Original descriptions/comments are issue-N.md; manifest.json owns the 43-issue universe and SHA. Supporting evidence is in portfolio.md, partial reports and recovered-conversations. This is a final review and correction, not another broad audit.

Stuart values consolidation and defensible closures highly, followed by a priority/value ordered backlog. Main orchestrator preserves context; do detailed checks here. No source/GitHub changes, no agents/messages, no runtime or provider probes, no product tests. CPU indexes are being fixed by another Astra and are outside scope.

Check all 43 dispositions and all 25 packages for justified scope, preserved acceptance criteria, dependencies and no double counted effort. Specific issues:
- #459 into #460 only after unique research deliverables are transferred; do not falsely imply completed implementation.
- #381 into #630 is a new conditional restructuring, not a proven duplicate. #630 is a focused discovery regression epic; #381 owns broader Autopilot. Do not broaden a narrow bug parent merely to gain a closure. Recommend retain unless scope coherence justifies it.
- OD-1 claims storing unknown but displaying 'degraded, verification pending' preserves a single meaning of degraded everywhere. Challenge this contradiction. Default to truthful pending/unknown presentation; preserve the #633 policy conflict as an explicit owner question if needed. Do not claim contradictory labels satisfy both contracts.
- #633 need not wait for certify --all when first-turn-only references suffice under missing-shape policy.
- #384 still has unimplemented owned-overlay obligations. Do not erase them as parent overhead.
- #573 resident reconciliation shipped in #629, while queue/binding and potential restart gaps remain. Separate source inference from runtime proof.
- #470/#632 need latest entitlement decision and correct account identity; provider is not account.
- #457/#597 need sequencing for tool economy, not an unproven blanket dependency across all harnesses.
- Ten owner decisions is excessive if ordinary engineering judgments are included. Tool count invariants, naming and dependency bookkeeping should normally be resolved by engineering. Leave only true product-policy conflicts for Stuart.
- proposed-grooming.json is 1221 lines. All final files must be <=700 lines; compact JSON per record.
- Open PRs #463/#464 are in-flight, not shipped. Preserve unique issue outcomes.

Write only these new final artifacts in this directory:
1. grooming-review.md: verdict, material corrections and evidence, <=200 lines.
2. final-grooming.json: same schema as proposed-grooming.json, corrected; exactly 43 distinct issue_dispositions.
3. final-grooming.md: lead with consolidation/closures and open-count impact (conditional separately), then ranked work with issue links, value/dependencies, then complete 43-issue ledger and only genuine owner questions.
4. final-github-edit-drafts.md: exact corrected local amendment and closing-comment drafts.
5. verify-final-grooming.py: adapt/reuse verify-proposal.py where practical, checking exact coverage, valid package refs/dependencies, cycles, rank consistency, survivors/preconditions, snapshot identity and line limits. Keep proposed originals intact.

Prefer narrow verification of consequential disputes and state uncertainty rather than widening the investigation. Save a useful first result early. Target one bounded turn of about 10 minutes. Final response <=1200 words: signoff/blockers, closure count, top work order, genuine owner decisions, paths and verification result. Finish: done: final-grooming.md final-grooming.json final-github-edit-drafts.md grooming-review.md; 43/43 coverage. Existing workspace watch notifies the orchestrator.

