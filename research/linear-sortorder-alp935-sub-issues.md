---
title: Linear sortOrder values for ALP-935 sub-issues
type: research
tags: [linear, sortorder, alp-935, echoecho, graphql]
summary: ALP-935 sub-issues have unique but non-contiguous sortOrder values; raw API order is reverse-sortOrder (descending); two fetches return identical ordering.
status: active
source: quick-research
confidence: high
created: 2026-03-09
updated: 2026-03-09
---

## Summary

ALP-935 "EchoEcho Navigator MVP" has 14 sub-issues. No duplicate sortOrder values exist. The raw API response returns issues in descending sortOrder order (highest to lowest). Ordering is stable across two consecutive fetches.

## sortOrder Values (ascending)

| Identifier | sortOrder | Title |
|------------|-----------|-------|
| ALP-978 | -75505 | Project Foundation [backend-engineer] |
| ALP-983 | -73743 | Walk-and-Record Route Capture [backend-engineer] |
| ALP-977 | -68526 | Project Foundation [frontend-engineer] |
| ALP-979 | 3 | Haptic UX Validation [ux-researcher] |
| ALP-980 | 4 | Haptic UX Validation [mobile-engineer] |
| ALP-981 | 5 | Walk-and-Record Route Capture [mobile-engineer] |
| ALP-982 | 6 | Walk-and-Record Route Capture [frontend-engineer] |
| ALP-984 | 8 | Student Navigation App [ux-designer] |
| ALP-985 | 9 | Student Navigation App [backend-engineer] |
| ALP-986 | 10 | Student Navigation App [frontend-engineer] |
| ALP-987 | 11 | Student Navigation App [mobile-engineer] |
| ALP-988 | 12 | Admin Panel [ux-designer] |
| ALP-989 | 13 | Admin Panel [backend-engineer] |
| ALP-990 | 14 | Admin Panel [frontend-engineer] |

## Key Observations

- **No duplicates**: all 14 sortOrder values are unique.
- **Non-contiguous**: three issues (ALP-978, ALP-983, ALP-977) have large negative sortOrder values (around -75k to -68k), while the remaining 11 cluster between 3 and 14.
- **Missing value at 7**: the sequence jumps from 6 to 8, meaning ALP-984 was inserted after some deletion or reordering.
- **Raw API order is descending by sortOrder**: the `get_sub_issues.gql` query returns nodes from highest to lowest sortOrder (ALP-990=14 first, ALP-977=-68526 last). If consuming code expects ascending/priority order, it must `sort_by(.sortOrder)`.
- **Ordering is stable**: both fetches returned identical sequences.

## Implications for Consumers

Code that processes sub-issues in raw API order sees them highest-sortOrder-first. The three issues with large negative sortOrder values appear at the end of the raw list. If the intent is to process in logical/priority order, sort ascending by sortOrder before processing.

## Sources

- Live Linear API via `linear::issue:sub` (nancy bash framework, `src/linear/issue.sh`)
- Query file: `src/gql/q/get_sub_issues.gql`
- Parent issue ID: `f70c3ac7-aea5-422a-a46b-fd1a696a3cb1`

## Open Questions

- Why do ALP-978, ALP-983, ALP-977 have large negative sortOrder values? These are the "Project Foundation" and one "Walk-and-Record" backend issue. They may have been created first and manually reordered relative to later issues, or they were bulk-moved which reset their sortOrder to a large negative anchor.
- Does the `get_sub_issues.gql` query include a sort directive, or does Linear always return in this order by default?
