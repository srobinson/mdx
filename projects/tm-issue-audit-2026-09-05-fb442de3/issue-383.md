# 383: Welcome report: explain the first full provider request in HTML

URL: https://github.com/littleorgans/transport-matters/issues/383
State: open
Labels: enhancement
Updated: 2026-08-19T01:54:06Z

Parent: #381
Depends on: #370, #382

## Outcome

Provide an optional, one-off TM welcome and onboarding report that demonstrates the problem using the user's real first full provider-bound request.

Value proposition:

> Let me show you how much junk your harness sent with your request and will send repeatedly.

The user may skip the report during onboarding and invoke it later.

## Request selection

Use the first full user turn. Exclude auxiliary traffic such as:

- prewarm
- title generation
- token counting
- health checks
- other harness housekeeping

Selection evidence must be explicit. Do not assume the first chronological exchange is the first full turn.

## HTML report

Safely render:

- the complete captured request
- total bytes, characters, and tokens
- exact token counts when authoritative and clearly labelled estimates otherwise
- totals by API role: system, developer, user, assistant, tool, and metadata
- totals by provenance: user-authored, user-configuration-derived, session-derived, static harness, provider metadata, and unknown
- every textual leaf with exact JSON Pointer, digest, counts, role, provenance, confidence, and evidence
- observed facts separately from inferred classifications

The report is read only. It does not apply or author an overlay.

## Experience

- Available during first-time onboarding.
- Skippable without blocking launch.
- Reopenable later from the product.
- Large fields remain inspectable without making the report unusable.
- Sensitive content stays local and is escaped safely.

## Acceptance

- A real TM launch produces the report from the selected first full turn.
- The report clearly compares the user's prompt footprint with the complete provider request footprint.
- Static harness claims are backed by controlled baseline evidence; otherwise they remain unknown or lower confidence.
- Claude and Codex reports consume the same request inventory contract.
- Skipping the report does not block or alter the harness request.
- Reopening the report later renders the same persisted evidence.


## Comment by srobinson at 2026-08-19T01:54:06Z (updated 2026-08-19T01:54:06Z)

https://github.com/littleorgans/transport-matters/issues/383#issuecomment-5336550536

Prior art on disk: local branch `slice/native-capture-home`, checked out at `.claude/worktrees/harvest-gates`. Three commits, unmerged, and on a stale base (its diff against main would remove everything merged since, including #395).

Worth reading before starting this issue, particularly `1ce1e1ea fix(capture): use native homes for baseline harvest`, which is the same idea this issue asks for: capturing through the real HOME rather than a fresh empty one.

The other two are adjacent harvest-reliability fixes rather than capture design:

- `ca714eae fix(supervisor): close the pre-registration orphan window on both PTY spawn paths` shares `_rollback_failed_pty_spawn` between both spawn paths, makes the drain thread join deterministic before the master fd closes (a recycled fd could otherwise write one harvest cell's bytes into another's capture), and makes `baseline_harvest._capture_cell` report child exit instead of burning the full timeout. That last part is directly relevant to the slow-failure mode described in #397.
- `92ba19ab fix(harvest): require a trusted current workdir`.

It also carries one file main does not have: `api/tests/integration/test_captured_proxy_post.py`.

Treat it as a source to read and cherry-pick from, not a branch to merge. Rebasing it would be a fight.

## Sub issues
[]
