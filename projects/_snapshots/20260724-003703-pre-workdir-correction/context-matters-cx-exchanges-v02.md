---
title: "cx_exchanges: Conversation continuity tool"
tags: [context-matters, v0.2, tool-design]
status: draft
created: 2026-03-14
---

# cx_exchanges

Semantic inverse of `cx_deposit`. Retrieves the most recent conversation exchanges for continuity across sessions.

## Problem

At session start, an agent has no task context. `cx_recall` requires a meaningful query to be useful. The agent needs a way to retrieve what happened in prior sessions before it knows what the current task is.

`cx_deposit` stores conversation exchanges at session end. There is no corresponding retrieval tool that returns them cleanly.

### Current workaround (v0.1)

```
cx_browse(kind: "observation", tag: "conversation", limit: 20)
cx_get(ids: [...])
```

Gaps:
- No session boundary: exchanges from different sessions interleave
- Reverse chronological order (newest first, want oldest first for reading)
- Two calls required (browse for snippets, get for bodies)
- Summary entries mixed with exchange entries
- No batch grouping: deposits don't stamp a batch ID

## Proposed tool: cx_exchanges

Single call that returns recent conversation deposits in reading order.

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `scope_path` | string | no | Filter to a specific scope. Default: current project scope. |
| `sessions` | integer | no | Number of recent sessions to retrieve. Default: 1 (last session only). |
| `limit` | integer | no | Max exchanges to return across all sessions. Default: 50. |

### Response

```json
{
  "sessions": [
    {
      "deposited_at": "2026-03-14T05:48:10Z",
      "scope_path": "global/project:helioy",
      "summary": "Reviewed context-matters specs, dispatched warroom...",
      "exchanges": [
        { "user": "...", "assistant": "...", "entry_id": "uuid" },
        { "user": "...", "assistant": "...", "entry_id": "uuid" }
      ]
    }
  ],
  "total_sessions_available": 12
}
```

### Data model requirement

`cx_deposit` needs to stamp entries with a batch identifier so `cx_exchanges` can group them. Options:

1. **Batch tag**: auto-generate `deposit:{timestamp}` tag on all entries in a deposit call
2. **Session scope**: require or default to session-scoped paths (`global/project:helioy/session:{id}`)
3. **Relation grouping**: the summary already has `elaborates` relations to exchanges; walk relations from the most recent summary

Option 3 works with the current data model if a summary is always provided. Options 1 and 2 require a spec change to `cx_deposit`.

### Workflow with cx_exchanges

```
Session start:
  cx_exchanges(sessions: 1)
  -> returns what happened last session, giving the agent continuity
  -> agent now understands prior context

Receive task from user:
  cx_recall(query: "summary of task")
  -> retrieve stored knowledge relevant to this specific task

During session:
  cx_store() for reusable knowledge

Session end:
  cx_deposit(exchanges, summary)
```

## Dependencies

- Requires batch grouping mechanism in cx_deposit (v0.2 spec change)
- Or: use relation walking from summary entries (works with v0.1 data model)
