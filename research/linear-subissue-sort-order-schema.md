---
title: Linear subIssueSortOrder field — sub-issue panel ordering mechanism
type: research
tags: [linear, graphql, sub-issues, sortOrder, subIssueSortOrder, ordering, schema]
summary: Linear has a dedicated subIssueSortOrder Float field (nullable) on Issue that drives the sub-issue panel's manual drag order. It is distinct from sortOrder. Request it explicitly and sort ascending client-side.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Linear's sub-issue panel uses `subIssueSortOrder: Float` — a dedicated, nullable field present in the `Issue` type — to maintain manual drag-and-drop order among siblings. It is entirely separate from `sortOrder` (which governs global issue list order). The Linear UI reads `subIssueSortOrder` to order children under a parent. To replicate that order via GraphQL, request the field and sort ascending client-side.

---

## Details

### The Field

From `packages/sdk/src/schema.graphql` (verified via `gh api` against `linear/linear` master):

```graphql
"""
The order of the item in the sub-issue list. Only set if the issue has a parent.
"""
subIssueSortOrder: Float
```

Key properties:
- **Type**: `Float` (nullable — `null` when the issue has no parent)
- **Scope**: Only meaningful when the issue has a parent (`parentId` is set)
- **Semantics**: Manual order within the parent's sub-issue list, set by drag-and-drop in the sub-issues panel
- **Schema line**: 12592 in `packages/sdk/src/schema.graphql`

### Mutation Support

`subIssueSortOrder` is writable via both create and update mutations:

```graphql
# IssueCreateInput (line 13369)
subIssueSortOrder: Float

# IssueUpdateInput (line 16729)
subIssueSortOrder: Float
```

### Why sortOrder Doesn't Match the Sub-Issue Panel

`sortOrder` is a global, organization-scoped float that governs position in issue lists, board columns, and priority views. When issues are displayed in the sub-issue panel, Linear uses `subIssueSortOrder` instead. The two values are independent:

- An issue can have `sortOrder = -75505` (because it was drag-positioned early in a global list) and `subIssueSortOrder = 1.0` (because it was manually placed first under its parent).
- Filtering with `parent: { id: { eq: $id } }` and reading `sortOrder` will return values that have no visual correspondence to the sub-issue panel order.

### How to Query

```graphql
query SubIssuesInOrder($parentId: String!) {
  issues(filter: { parent: { id: { eq: $parentId } } }) {
    nodes {
      id
      identifier
      title
      sortOrder
      subIssueSortOrder   # <-- this is the one that matches the UI panel
    }
  }
}
```

Then sort the result client-side:

```python
sub_issues.sort(key=lambda i: (i["subIssueSortOrder"] is None, i["subIssueSortOrder"]))
```

Or via the parent's `children` relation (same field applies):

```graphql
query ParentWithChildren($id: String!) {
  issue(id: $id) {
    children {
      nodes {
        id
        identifier
        title
        subIssueSortOrder
      }
    }
  }
}
```

The `children` relation also only supports `orderBy: createdAt | updatedAt`, so client-side sort by `subIssueSortOrder` ascending is required.

### Related Fields on Issue Type (all confirmed in schema)

| Field | Type | Purpose |
|-------|------|---------|
| `sortOrder` | `Float!` | Global manual order in issue lists and board columns |
| `subIssueSortOrder` | `Float` | Manual order within parent's sub-issue panel (null if no parent) |
| `prioritySortOrder` | `Float!` | Relative order within a priority-grouped view |
| `boardOrder` | `Float! @deprecated` | Predecessor to sortOrder (deprecated, use sortOrder) |

---

## Sources

- `linear/linear` repo, `packages/sdk/src/schema.graphql` — verified via `gh api repos/linear/linear/contents/packages/sdk/src/schema.graphql` (master branch, 2026-03-09)
  - `Issue.subIssueSortOrder`: line 12592
  - `IssueCreateInput.subIssueSortOrder`: line 13369
  - `IssueUpdateInput.subIssueSortOrder`: line 16729

---

## Open Questions

- Does Linear assign an initial `subIssueSortOrder` value when a sub-issue is created, or is it null until first reorder? The field is nullable, but the UI presumably has a default placement order.
- When `subIssueSortOrder` is null for some children but set for others, what order does the UI fall back to? Likely `createdAt` for null items.
- Is there a `subIssueSortOrder` equivalent for the `PaginationOrderBy` enum, or is client-side sort always required? Current enum only supports `createdAt` and `updatedAt`.
