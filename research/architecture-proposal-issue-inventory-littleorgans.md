---
title: Littleorgans Architecture Proposal Issue Inventory
type: research
tags: [littleorgans, architecture, github, issues, planning]
summary: No GitHub issues or milestones exist, so all six architecture proposals are clear of existing issue duplicates.
status: active
source: codebase-analyst
confidence: high
created: 2026-08-14
updated: 2026-08-14
---

# Architecture proposal issue inventory

## Executive summary

The repository has **zero open issues and zero closed issues**. None of the six architecture proposals duplicates an existing GitHub issue. GitHub Issues is enabled, but the repository has only the nine default labels and has no milestones or established issue title convention.

The architecture plan still has two internal scope collisions to manage. Proposals 1 and 6 both mention stale topology prose. Proposals 3 and 5 both change the in-process launch seam and the delivery sequence groups them as one typed launch command. These are proposal relationships, not existing issue duplicates.

## Scope and snapshot

- Repository: [`littleorgans/littleorgans`](https://github.com/littleorgans/littleorgans)
- Repository visibility: public
- Issues: enabled
- Default branch: `main`
- Local HEAD inspected: `eac686d0384546b53dfa73e7f89a0206dd4403eb`
- Proposal source: [`docs/architecture/review/README.md`](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md)
- Inventory date: 2026-08-14
- Scope: read only GitHub issue metadata and the proposal landing page

## Complete issue scan

| State | Count | Result |
| --- | ---: | --- |
| Open issues | 0 | No overlap candidates |
| Closed issues | 0 | No historical title or scope precedent |
| All issues | 0 | No existing issue can duplicate a proposal |

`gh issue list --state open --limit 1000` returned an empty array. `gh issue list --state all --limit 1000` also returned an empty array. A GraphQL repository query independently reported `issues(states: OPEN).totalCount = 0` and `issues(states: CLOSED).totalCount = 0`.

GitHub issue and pull request numbers share a namespace. `gh issue view 1` resolved pull request [#1](https://github.com/littleorgans/littleorgans/pull/1), not an issue. There is therefore no issue available for a meaningful per-issue `gh issue view` inspection. The REST `/issues` endpoint returned one open issue-like record, which was that pull request; filtering records with a `pull_request` field left zero issues.

## Proposal verdicts

| Proposal | Source | Existing overlapping open issues | Duplicate verdict | Suggested title if an issue is created | Usable existing label | Milestone |
| --- | --- | --- | --- | --- | --- | --- |
| 1. Remove the old process topology | [Lines 75 to 93](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L75-L93) | None | **No duplicate** | `Remove the legacy Session and Runtime process topology` | `enhancement` | None exists |
| 2. Repair the package publication graph | [Lines 95 to 113](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L95-L113) | None | **No duplicate** | `Repair the publishable package dependency graph` | `enhancement` | None exists |
| 3. Add the opaque launch payload | [Lines 115 to 134](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L115-L134) | None | **No duplicate** | `Add an opaque payload to Session launch requests` | `enhancement` | None exists |
| 4. Restore the Session to Runtime boundary | [Lines 136 to 151](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L136-L151) | None | **No duplicate** | `Restore Runtime ownership behind the Session execution port` | `enhancement` | None exists |
| 5. Keep internal calls typed | [Lines 153 to 164](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L153-L164) | None | **No duplicate** | `Preserve typed identifiers across in-process Runtime calls` | `enhancement` | None exists |
| 6. Correct active documentation | [Lines 166 to 177](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L166-L177) | None | **No duplicate** | `Correct active architecture documentation for Postgres and lilod` | `documentation` | None exists |

### Scope boundaries that prevent new duplicates

1. **Proposals 1 and 6:** Proposal 1 explicitly includes stale topology prose, while Proposal 6 covers active documentation drift. Give topology prose to one issue. The clean boundary is for Proposal 1 to own only documentation required to describe the topology deletion, while Proposal 6 owns the wider Postgres, completed phase, and historical plan cleanup.
2. **Proposals 3 and 5:** Both change the Session execution request and Runtime port. The proposed delivery sequence groups them under “Typed launch command” at [lines 179 to 188](https://github.com/littleorgans/littleorgans/blob/eac686d0384546b53dfa73e7f89a0206dd4403eb/docs/architecture/review/README.md#L179-L188). Either create one combined implementation issue, or keep two issues with distinct acceptance: Proposal 3 owns opaque payload semantics and round trip fidelity; Proposal 5 owns typed identifiers, targets, and signals.
3. **Proposal 4:** This uses the same port seam as Proposals 3 and 5, but its acceptance is distinct. It owns Runtime lifecycle mutation and event publication, plus removal of concrete Runtime store and service dependencies from Session.

## Labels

The repository has nine labels, all matching GitHub defaults. See the [repository label list](https://github.com/littleorgans/littleorgans/labels).

| Label | Current description | Use for this plan |
| --- | --- | --- |
| `enhancement` | New feature or request | Best available label for Proposals 1 through 5 |
| `documentation` | Improvements or additions to documentation | Proposal 6 |
| `question` | Further information is requested | Optional discussion issues for unresolved choices, not delivery issues |
| `bug` | Something isn't working | Avoid unless the issue documents current incorrect behavior rather than convergence work |
| `duplicate` | This issue or pull request already exists | Triage only |
| `wontfix` | This will not be worked on | Triage only |
| `invalid` | This doesn't seem right | Triage only |
| `help wanted` | Extra attention is needed | Not useful for the current owned plan |
| `good first issue` | Good for newcomers | Not suitable for these cross-boundary architecture changes |

No `architecture`, `refactor`, `internal`, `release`, `v0.8.0`, `session`, `runtime`, or `transport` label exists. Creating labels was outside the read only scope.

## Milestones

The repository has **zero milestones**, open or closed. No milestone can be assigned without first creating one. The proposal source scopes the work to v0.8.0, but there is no GitHub milestone named `v0.8.0`.

## Title convention

There is no established issue title convention because the repository has no issue history. The proposal headings use short imperative phrases. The suggested titles above retain that structure, name the affected seam, and omit `Proposal N` because proposal numbering is specific to the discussion document.

If the plan creates separate delivery issues, use this convention:

```text
<Imperative verb> <specific owned seam or outcome>
```

Do not use broad titles such as `Architecture cleanup`, which would make Proposals 1, 4, 5, and 6 difficult to distinguish.

## Verification evidence

Commands executed against `littleorgans/littleorgans`:

```sh
gh auth status
gh repo view littleorgans/littleorgans \
  --json nameWithOwner,url,isPrivate,defaultBranchRef,description,hasIssuesEnabled

gh issue list --repo littleorgans/littleorgans --state open --limit 1000 \
  --json number,title,url,labels,milestone,body,createdAt,updatedAt,author,assignees

gh issue list --repo littleorgans/littleorgans --state all --limit 1000 \
  --json number,title,state,url,labels,milestone,createdAt,closedAt

gh issue view 1 --repo littleorgans/littleorgans \
  --json number,title,state,url

gh label list --repo littleorgans/littleorgans --limit 1000 \
  --json name,description,color

gh api --paginate \
  'repos/littleorgans/littleorgans/milestones?state=all&per_page=100'

gh api graphql -F owner=littleorgans -F name=littleorgans \
  -f query='query($owner:String!,$name:String!){repository(owner:$owner,name:$name){open:issues(states:OPEN){totalCount} closed:issues(states:CLOSED){totalCount} labels(first:100){totalCount} milestones(first:100){totalCount}}}'

gh api --paginate \
  'repos/littleorgans/littleorgans/issues?state=open&per_page=100'
```

Observed evidence:

```text
gh issue list, open: 0
gh issue list, all: 0
GraphQL open issues: 0
GraphQL closed issues: 0
REST open issue records after excluding pull requests: 0
Labels: 9
Milestones: 0
gh issue view 1: pull request #1, not an issue
```

## Final planning verdict

All six proposals are clear to create from a GitHub duplication perspective. There are no existing issue URLs to attach because no issue exists. Before issue creation, decide whether Proposals 3 and 5 become one typed launch issue, and give topology prose a single owner between Proposals 1 and 6.
