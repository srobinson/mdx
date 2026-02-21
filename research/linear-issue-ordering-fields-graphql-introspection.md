---
title: Linear Issue Ordering Fields (GraphQL Introspection)
type: research
tags: [linear, graphql, sorting, ordering, sub-issues]
summary: The Issue type exposes three Float ordering fields; IssueConnection/IssueEdge carry no ordering metadata.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

The Linear `Issue` type exposes exactly three ordering-related fields, all typed `Float`:

| Field | Type | Semantics |
|---|---|---|
| `sortOrder` | Float | General board/list position |
| `prioritySortOrder` | Float | Position within a priority grouping |
| `subIssueSortOrder` | Float | Position within a parent issue's sub-issue list |

`IssueConnection` and `IssueEdge` carry no ordering metadata — only `edges`, `nodes`, `pageInfo`, `node`, and `cursor`.

## ALP-935 Sub-Issue Values

Sorted by `subIssueSortOrder` ascending (reflects intended display order within the parent):

| Identifier | Title (abbreviated) | sortOrder | prioritySortOrder | subIssueSortOrder |
|---|---|---|---|---|
| ALP-977 | Project Foundation [frontend-engineer] | -68526 | -349746 | 4220 |
| ALP-978 | Project Foundation [backend-engineer] | -75505 | -349723 | 5276 |
| ALP-979 | Haptic UX Validation [ux-researcher] | -78489 | -349611 | 6336 |
| ALP-980 | Haptic UX Validation [mobile-engineer] | -81583 | -349775 | 7287 |
| ALP-981 | Walk-and-Record Route Capture [mobile-engineer] | -86689 | -349637 | 8232 |
| ALP-982 | Walk-and-Record Route Capture [frontend-engineer] | -87697 | -349699 | 9312 |
| ALP-983 | Walk-and-Record Route Capture [backend-engineer] | -91468 | -349592 | 10341 |
| ALP-984 | Student Navigation App [ux-designer] | -93474 | -349747 | 11250 |
| ALP-985 | Student Navigation App [backend-engineer] | -98489 | -349627 | 12177 |
| ALP-986 | Student Navigation App [frontend-engineer] | -103191 | -349681 | 13124 |
| ALP-987 | Student Navigation App [mobile-engineer] | -117238 | -349731 | 14203 |
| ALP-988 | Admin Panel [ux-designer] | -95418 | -349655 | 15278 |
| ALP-989 | Admin Panel [backend-engineer] | -100333 | -349685 | 16298 |
| ALP-990 | Admin Panel [frontend-engineer] | -51951 | -349737 | 16543 |
| ALP-991 | Get apps building on Android | -110320 | -313896 | 13647 |
| ALP-998 | Verify runtime integration [mobile-engineer] | -123185 | -313987 | 16424 |

## Key Observations

- `subIssueSortOrder` is the canonical field for ordering children under a parent issue. It increases monotonically with display order.
- `sortOrder` reflects global list position and does NOT match sub-issue display order.
- `prioritySortOrder` reflects position within priority buckets and is largely negative (Linear uses descending floats for this).
- Neither `IssueConnection` nor `IssueEdge` expose ordering fields — ordering is entirely on the `Issue` node itself.

## Query Pattern

```graphql
{ issue(id: "ALP-935") {
    children(first: 50) {
      nodes { identifier title sortOrder subIssueSortOrder prioritySortOrder }
    }
  }
}
```

Sort client-side by `subIssueSortOrder` ascending to get the canonical sub-issue display order.

## Sources

- Linear GraphQL introspection: `https://api.linear.app/graphql`
- Live data from ALP-935 (EchoEcho Navigator MVP)
