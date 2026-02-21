---
title: Linear sortOrder field API behavior and query ordering
type: research
tags: [linear, graphql, sortorder, api, ordering, pagination]
summary: sortOrder is a Float (not integer), manually set only with one team-config exception, API queries default to createdAt order (not sortOrder), and PaginationOrderBy only accepts createdAt or updatedAt.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

`sortOrder` on Linear issues is a `Float!` representing manual drag-and-drop position. The API's `orderBy` parameter accepts only `createdAt` (default) and `updatedAt` — it does NOT accept `sortOrder`. Query result order is deterministic by `createdAt` desc by default, not by manual sort order. Linear does recalculate `sortOrder` automatically under one documented condition: the per-team "reorder issues when moved to a new status" setting.

---

## Details

### 1. Is sortOrder manual-only, or does Linear recalculate it automatically?

**Mostly manual, with one automatic exception.**

- `sortOrder` is set explicitly when a user drags an issue to a new position in a list or board view. The drag operation calls `issueUpdate` with the new `sortOrder` float.
- Linear has a per-team setting: **"reorder issues when moved to a new status"**. When enabled, moving an issue to a new workflow state triggers an automatic `sortOrder` update to position the issue at the top (or bottom) of the destination column. This is the only documented case where Linear recalculates `sortOrder` without explicit user drag input. A bug in Linear's team-copy feature (fixed in a changelog) — where this setting was not correctly copied when cloning team settings — confirms its existence as a real, persistent config option.
- Moving an issue between kanban columns does NOT automatically recalculate `sortOrder` when the view is sorted by a property other than manual order. In those modes, position within a column is computed on the fly from the sort field, and `sortOrder` is untouched.
- Linear's changelog (2022-08-18) makes this distinction explicit: when issues are ordered by a property (priority, date, etc.), dragging between columns moves the issue to that column but its within-column position is determined by the sort property, not stored in `sortOrder`.

### 2. Does the GraphQL API guarantee stable return order for issues queries?

**Yes, but it is stable by `createdAt`, not by `sortOrder`.**

From the schema (line 31680 of `packages/sdk/src/schema.graphql`):

```
By which field should the pagination order by. Available options are createdAt (default) and updatedAt.
```

The `PaginationOrderBy` enum has exactly two values:
```graphql
enum PaginationOrderBy {
  createdAt
  updatedAt
}
```

The default order across all `issues` queries (top-level and nested) is `createdAt`. This is consistent and deterministic across pages. It has no relationship to `sortOrder` (the manual drag-and-drop value). If two issues share the same `createdAt` timestamp, order between them is not guaranteed — this is a standard database tie-breaking problem Linear does not document resolving.

In practice (confirmed in the `linear-sortorder-alp935-sub-issues.md` observation), the API returns sub-issues in **descending `sortOrder`** order for the `children` / sub-issues relation — this may differ from the top-level `issues` query. The default ordering may vary by which relation you query through (parent issue's children vs. team's issues vs. top-level query).

### 3. Is sortOrder a float or integer? Does Linear use fractional ranking?

**It is a `Float`, and fractional values are used.**

From the schema:

```graphql
# Issue type (line 12551)
"""
The order of the item in relation to other items in the organization.
"""
sortOrder: Float!

# IssueCreateInput (line 13353)
"""
The position of the issue related to other issues.
"""
sortOrder: Float

# IssueUpdateInput (line 16721) — same Float type
```

`boardOrder` (the predecessor field, now deprecated) is also `Float!` with the deprecation message: `"Will be removed in near future, please use sortOrder instead"`.

A webhook payload example from Linear's docs shows `"sortOrder": 1234.56` — confirming fractional values appear in real data.

The correct algorithm for inserting between two items is the midpoint: `newSortOrder = (a.sortOrder + b.sortOrder) / 2`. Linear's own team member confirmed in GitHub issue #170 that naive `p2.sortOrder - 1` works only once — if you insert above the same item twice you get a collision problem. The midpoint approach is the standard fractional indexing pattern.

There is a separate `prioritySortOrder: Float!` field — this governs relative ordering within a priority-ordered view (where users can drag items to say "more important than this, less important than that" within a priority tier). It is distinct from `sortOrder`.

### 4. When using filter on the issues query, does Linear respect manual sort order?

**No. Filtering does not change the orderBy behavior.**

The `filter` parameter and `orderBy` parameter are independent. Adding a `filter` does not inject `sortOrder` as the sort. The result set is still ordered by `createdAt` (default) or `updatedAt` if you specify it. There is no way to pass `orderBy: sortOrder` — the enum does not support it.

To consume issues in manual (drag) order:
1. Fetch with `orderBy: createdAt` (or no `orderBy`)
2. Sort client-side by `.sortOrder` ascending

This matches the observation in the ALP-935 sub-issues research: the raw API returns issues in descending `sortOrder` order for sub-issue relations, so callers that want logical manual order must sort themselves.

---

## Schema Evidence (verified against `linear/linear` repo master)

| Field | Type | Location |
|-------|------|----------|
| `Issue.sortOrder` | `Float!` | line 12551 |
| `Issue.boardOrder` | `Float! @deprecated` | line 12040 |
| `Issue.prioritySortOrder` | `Float!` | line 12466 |
| `IssueCreateInput.sortOrder` | `Float` | line 13353 |
| `IssueUpdateInput.sortOrder` | `Float` | line 16721 |
| `PaginationOrderBy` enum | `createdAt`, `updatedAt` | line 25137 |
| `issues` query `orderBy` docstring | "Available options are createdAt (default) and updatedAt" | line 31680 |

---

## Sources

- [linear/linear schema.graphql](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql) — verified directly via `gh api`
- [GitHub issue #170: What's the correct way to change sortOrder?](https://github.com/linear/linear/issues/170) — Linear team member (eldh) confirmed midpoint approach
- [Linear changelog 2022-08-18: Board Ordering](https://linear.app/changelog/2022-08-18-board-ordering) — automatic vs manual positioning distinction
- [Linear changelog 2021-08-27: Multi-team boards & manual ordering](https://linear.app/changelog/2021-08-27-multi-team-boards-and-manual-ordering)
- [Linear Developers: Pagination](https://linear.app/developers/pagination) — createdAt/updatedAt as the only orderBy options
- [Linear Webhooks Guide (inventivehq)](https://inventivehq.com/blog/linear-webhooks-guide) — `"sortOrder": 1234.56` in example payload
- [linear-sortorder-alp935-sub-issues.md](./linear-sortorder-alp935-sub-issues.md) — empirical ALP-935 sub-issue ordering data

---

## Open Questions

- Does the `children` (sub-issues) relation use a different default sort than the top-level `issues` query? Empirical data suggests sub-issues return descending by `sortOrder`, which contradicts the `createdAt` default documented for `issues`. This may be a relation-specific override not documented in the schema.
- What is the initial `sortOrder` value assigned to a new issue? The ALP-935 data shows small positive integers (3–14) for recently created issues, suggesting Linear assigns sequential integers initially and floats only appear after reordering operations.
- Does the "reorder issues when moved to new status" setting place issues at the top or bottom of the destination column? Not documented publicly.

## Update (2026-03-09): subIssueSortOrder Discovered

The mismatch between `sortOrder` and the sub-issue panel is explained by a separate dedicated field: `subIssueSortOrder: Float` (nullable). See [linear-subissue-sort-order-schema.md](./linear-subissue-sort-order-schema.md) for full details. The short version: request `subIssueSortOrder` in your query and sort ascending by it client-side to match what Linear's UI shows in the sub-issues panel.
