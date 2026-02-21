---
title: Linear Sub-Issue Sort Order - Schema Fields and API
type: research
tags: [linear, graphql, sub-issues, sorting, api]
summary: subIssueSortOrder is a dedicated Float field on the Issue type that controls ordering within a parent's sub-issue list; it is settable via both IssueCreateInput and IssueUpdateInput.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

Linear uses a dedicated `subIssueSortOrder: Float` field on the `Issue` type to control the manual ordering of sub-issues within a parent issue. This is separate from the global `sortOrder` field. Both `IssueCreateInput` and `IssueUpdateInput` expose it as a settable field.

Source: `packages/sdk/src/schema.graphql` in `github.com/linear/linear` (master branch).

---

## Details

### Issue type (read fields)

The `Issue` type has two relevant float fields for ordering:

| Field | Type | Description |
|---|---|---|
| `sortOrder` | `Float!` | Order of the item in relation to other issues in the organization |
| `prioritySortOrder` | `Float!` | Order when sorted by priority |
| `subIssueSortOrder` | `Float` (nullable) | Order within the parent's sub-issue list. Only set if the issue has a parent. |

Schema line references (schema.graphql):
- `sortOrder: Float!` at line 12551
- `prioritySortOrder: Float!` at line 12466
- `subIssueSortOrder: Float` at line 12592, with docstring: _"The order of the item in the sub-issue list. Only set if the issue has a parent."_

### IssueCreateInput

```graphql
input IssueCreateInput {
  # ...
  sortOrder: Float          # "The position of the issue related to other issues."
  subIssueSortOrder: Float  # "The position of the issue in parent's sub-issue list."
  preserveSortOrderOnCreate: Boolean  # "Whether the passed sort order should be preserved."
  # ...
}
```

- `subIssueSortOrder` is available at creation time.
- `preserveSortOrderOnCreate: Boolean` is also present, suggesting the backend may auto-assign sort order unless this flag is set.

### IssueUpdateInput

```graphql
input IssueUpdateInput {
  # ...
  sortOrder: Float          # "The position of the issue related to other issues."
  subIssueSortOrder: Float  # "The position of the issue in parent's sub-issue list."
  # ...
}
```

Both fields are optional floats. To reorder a sub-issue within its parent's list, call `issueUpdate` with a new `subIssueSortOrder` value.

### Issue.children connection

```graphql
type Issue implements Node {
  children(
    after: String
    before: String
    filter: IssueFilter
    first: Int
    includeArchived: Boolean
    last: Int
    orderBy: PaginationOrderBy  # only createdAt or updatedAt
  ): IssueConnection!
}
```

The `orderBy` parameter on the `children` connection is **limited to `PaginationOrderBy`**, which only supports:
```graphql
enum PaginationOrderBy {
  createdAt
  updatedAt
}
```

There is no `subIssueSortOrder` option in the `orderBy` enum for the `children` connection. The manual sort order is stored on the child issue itself (`subIssueSortOrder`) but is **not a pagination sort key** via the connection. To get sub-issues in their manual order, you must fetch them and sort client-side by `subIssueSortOrder`, or rely on the default ordering the API returns.

### Mutations

- `issueCreate(input: IssueCreateInput!)` - set `subIssueSortOrder` at creation
- `issueUpdate(id: UUID!, input: IssueUpdateInput!)` - update `subIssueSortOrder` to reorder
- `issueBatchUpdate(ids: [UUID!]!, input: IssueUpdateInput!)` - batch update, same input

### No junction table sort field

There is no separate junction/relationship type for parent-child ordering. `subIssueSortOrder` lives directly on the child `Issue` record itself. This is a flat float field, not a separate relationship model.

---

## Key Findings

1. **`subIssueSortOrder: Float`** is the canonical field for sub-issue ordering. It is nullable and only meaningful when the issue has a parent.
2. It is writable via both `IssueCreateInput` and `IssueUpdateInput`.
3. The `children` connection does **not** support ordering by `subIssueSortOrder` server-side. The `orderBy` enum only has `createdAt` and `updatedAt`.
4. `boardOrder` exists but is deprecated in favor of `sortOrder`.
5. `preserveSortOrderOnCreate: Boolean` in `IssueCreateInput` controls whether the backend should preserve the provided `sortOrder` rather than auto-assigning.

---

## Sources

- `github.com/linear/linear` - `packages/sdk/src/schema.graphql` (master, ~906KB)
  - `type Issue` starts at line 11963
  - `input IssueCreateInput` starts at line 13253
  - `input IssueUpdateInput` starts at line 16629
  - `enum PaginationOrderBy` at line 25137
- Linear developer docs at `linear.app/developers` - no sub-issue ordering documentation found on the landing page

---

## Open Questions

- Does the Linear API return `children` sorted by `subIssueSortOrder` by default (when no `orderBy` is specified), even though it's not exposed as an enum option?
- What float values does Linear use for initial assignments (LexoRank style, midpoint insertion, etc.)?
- Is there a `issueUpdateOrder` or similar batch-reorder mutation not visible in the input types?
