---
title: "Automated Review Pipeline for Nancy Work"
type: design
tags: [nancy, automation, review, linear, workflow]
summary: "Design for automating the post-execution review cycle: verify Nancy's work, reopen failures, and create PRs without manual intervention."
status: draft
project: nancyr
created: 2026-03-14
updated: 2026-03-14
---

# Automated Review Pipeline

## Problem

After Nancy executes a batch of sub-issues and marks a parent "Worker Done", a human currently must:

1. Identify the source research document
2. Fetch all sub-issues
3. Verify each implementation against the research
4. Run `just check` and `just test`
5. Reopen failed issues with precise instructions
6. Re-trigger Nancy for failures
7. Create the PR on clean pass

This is mechanical, repeatable, and fully agent-executable. The human should only touch the final PR.

## Target State

```
Nancy works on sub-issues
        ↓
Last sub-issue → Worker Done → parent auto-transitions
        ↓
Review pipeline fires automatically
        ↓
Failures reopened → Nancy resumes → reviewer re-checks
        ↓
Clean pass → PR created → Stuart reviews PR
```

Stuart's only touchpoint is the PR review.

---

## Pipeline Stages

### Stage 1: Trigger

**Signal:** Parent issue transitions to "Worker Done".

**Options:**
- Linear webhook → Nancy dispatch endpoint
- Nancy polling loop on parent issue status
- Post-execution hook: Nancy marks the last sub-issue done, then self-triggers the reviewer

Simplest path for current Nancy (bash MVP): Nancy polls the parent status after each sub-issue completion. When all subs are "Worker Done", it fires the review role.

### Stage 2: Context Assembly

The reviewer needs four things, all derivable from the parent issue:

| Input | Source |
|-------|--------|
| Research document path | Parse `Source: ~/.mdx/research/...` line from parent description |
| Sub-issue list | `list_issues` filtered by `parentId` |
| Worktree path | Convention: `<repo>-worktrees/nancy-<parent-id>` |
| Acceptance criteria | Parse `## Acceptance Criteria` block from parent description |

No human input required — everything is encoded in the issue at creation time.

### Stage 3: Verification

The review agent:

1. Reads the research document
2. For each sub-issue, verifies the implementation in the worktree against the spec
3. Runs `just check` — must be zero warnings
4. Runs `just test` — must be zero failures
5. For each sub-issue: pass or fail, with reason

**Review philosophy:** Good faith only. Flag glaringly wrong or critically omitted items. Not nits. If in doubt, pass.

### Stage 4: Feedback

**On failures:**
- Reopen the specific sub-issue to "Todo"
- Update description with precise, actionable fix instructions
- Revert parent to "In Progress"
- Nancy picks up the reopened sub-issues in the next cycle

**On clean pass:**
- Proceed to Stage 5

The loop runs until the parent achieves a clean pass.

### Stage 5: PR Creation

On clean pass, the reviewer:

1. Pushes the branch if not already pushed
2. Constructs PR title: `feat: <curated summary of what changed>`
3. Constructs PR body: per-issue summary grouped by concern area
4. Creates the PR via `gh pr create`
5. Posts the PR URL as a comment on the parent Linear issue

---

## Worktree Naming Convention

Critical dependency: the reviewer must locate the worktree without being told.

**Convention:** `<repo-root>-worktrees/nancy-<ISSUE-ID>`

Example: `attention-matters-worktrees/nancy-ALP-1312`

Nancy must create worktrees using this convention. If the worktree is absent (Nancy worked directly on the branch), fall back to a git worktree list lookup.

---

## Nancy Integration Points

### New role: `reviewer`

Nancy gains a `reviewer` execution role alongside `worker`. The role:

- Accepts a parent issue ID
- Executes the pipeline above
- Returns: clean pass or list of reopened issues

### Trigger in Nancy orchestrator

```
after all subs reach Worker Done:
  if parent.has_review_trigger:
    dispatch reviewer(parent_id)
  else:
    mark parent Worker Done
```

The `has_review_trigger` flag could be a label (e.g., `needs-review`) applied at issue creation time by the linear-workflow skill.

### Re-queue on failure

When reviewer reopens sub-issues, Nancy's next orchestration cycle picks them up naturally — they appear as "Todo" children of an "In Progress" parent. No special handling needed.

---

## What Makes This Generic

The pipeline is domain-agnostic. Any parent issue with:

- A `Source:` line pointing to a research/design document
- Sub-issues with clear acceptance criteria
- A worktree at the expected path
- A `just check` + `just test` or equivalent build command

...can be reviewed automatically. The reviewer agent prompt is parameterized by issue ID, not by content.

---

## Open Questions

1. **Build command discovery:** `just check` + `just test` works for Rust workspaces. How does the reviewer know which command to run for other stacks? Options: encode in parent issue, detect from repo (Justfile, Makefile, package.json), or default to a per-project config in `~/.mdx/projects/`.

2. **Partial clean passes:** If 7 of 8 sub-issues pass and 1 fails, should the PR be created for the passing work, or should the entire batch wait? Current answer: wait. Simpler and avoids partial-state PRs.

3. **Review depth:** The current reviewer does structural verification (was it implemented?) plus build/test. It does not run property-based tests or benchmarks separately. Benchmark verification (as seen in ALP-1343) requires explicit acceptance criteria in the parent.

4. **Linear webhook vs. polling:** Webhooks are cleaner but require an endpoint. Nancy's current bash architecture polls. Design should support both.

---

## Implementation Sequence

1. Standardize worktree naming convention in Nancy (prerequisite)
2. Add `reviewer` role to Nancy orchestrator
3. Add `Source:` and `## Acceptance Criteria` as required sections in the linear-workflow skill (so every parent issue is reviewer-compatible)
4. Wire trigger: Nancy fires reviewer after last sub-issue completes
5. Wire re-queue: reviewer reopens → Nancy natural pickup
6. Wire PR creation: reviewer creates PR on clean pass
