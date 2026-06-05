# MCP Canvas Inspection Walkthrough

This note records how a Transport Matters agent answered:

> What's happening on this canvas?

The inspection used read only MCP operations. No agents were launched, prompted,
interrupted, or closed.

## 1. Establish the inspecting run

Tool:

```text
whoami({})
```

Relevant result:

```json
{
  "run_id": "805912a5-b970-406c-a2a4-b9f4d15e68c1",
  "name": "codex-2",
  "harness": "codex",
  "workspace_id": "claude-worktrees-multi-launch/2043e1eb",
  "control_access": "director",
  "working_dir": "/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch"
}
```

This identified the current run, workspace, working directory, and control
authority. The run ID was later matched against the roster.

## 2. Read the aggregate workspace state

Tool:

```text
workspace_summary({})
```

Result:

```text
18 panes: 1 working, 5 idle, 0 need you, 1 stalled, 11 exited.
States: exited 11, idle 5, stalled 1, running-tools 1.
```

This supplied the headline counts. The 18 panes include exited history. Seven
panes were live.

## 3. Identify the live panes

Tool:

```text
roster({"limit": 50})
```

The roster returned seven live runs:

| Run | Harness | Agent | State |
| --- | --- | --- | --- |
| `codex-2` | Codex | none | `running-tools` |
| `claude-1` | Claude | `tm/orchestrator` | `stalled` |
| `codex-1` | Codex | none | `idle` |
| `codex-1` | Codex | none | `idle` |
| `codex-3` | Codex | none | `idle` |
| `claude-1` | Claude | `tm/frontend` | `idle` |
| `claude-5` | Claude | none | `idle` |

Every run used the `multi-launch` worktree. None had a `needs_you` value.

The `codex-2` run ID matched the result from `whoami`. Its `running-tools`
state showed that this inspection was the one active operation.

## 4. Read the Canvas hierarchy

Tool:

```text
canvas_list({})
```

The relevant hierarchy was:

```text
multi-launch
├── renamed-a
└── test-child-b
    └── test-grandchild
```

The `multi-launch` root Canvas had ID
`20a7146f-02fc-4449-a5dd-4e46da3eef3a`. A separate root Canvas named
`cubicell` also existed.

The hierarchy is verified. Describing the descendants as test data is an
inference from their names.

## 5. Map the Canvas to repository state

Tool:

```text
worktree_list({})
```

Relevant result:

```json
{
  "worktreeId": "747d7569-4f9a-4c34-9374-fb362f860e23",
  "rootCanvasId": "20a7146f-02fc-4449-a5dd-4e46da3eef3a",
  "path": "/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.claude/worktrees/multi-launch",
  "branchName": "feat/multi-launch",
  "headOid": "72adadc1fd04827134c3512c3dd5c1176f24eba5",
  "lifecycleState": "active"
}
```

The `rootCanvasId` matched the Canvas ID from `canvas_list`. This established
the relationship between the Canvas and the active worktree.

## Important gap: run to Canvas identity

The available MCP data identifies the worktree root Canvas, but does not prove
that the run belongs to a specific nested Canvas.

For this run, the verified mapping is:

```text
whoami.working_dir
  → worktree_list.path
  → worktree.rootCanvasId
  → canvas_list.canvasId
  → multi-launch
```

The resolved identities are:

| Identity | Value |
| --- | --- |
| Run | `codex-2` |
| Run ID | `805912a5-b970-406c-a2a4-b9f4d15e68c1` |
| Workspace | `claude-worktrees-multi-launch/2043e1eb` |
| Worktree ID | `747d7569-4f9a-4c34-9374-fb362f860e23` |
| Root Canvas | `multi-launch` |
| Root Canvas ID | `20a7146f-02fc-4449-a5dd-4e46da3eef3a` |
| Space ID | `263ce1e0-636b-48c9-a8d9-1956a69d653b` |

`whoami` does not return a `canvas_id`. The roster does not expose one either.
The current read surfaces therefore cannot establish whether this pane has
affinity to `renamed-a`, `test-child-b`, or `test-grandchild`.

The strongest supported statement is:

> This run belongs to the worktree anchored by the `multi-launch` root Canvas.

Claiming that the run is inside a particular nested Canvas would require an
explicit run to Canvas identity field or another authoritative affinity
surface. This is an important observability gap because worktree identity is
less specific than Canvas identity.

## 6. Explain each live pane's activity

Tool, called once for each of the six other live runs:

```text
conversation({
  "run_id": "<run ID>",
  "shape": "summary",
  "limit": 8,
  "max_chars_per_message": 1200
})
```

Three Codex runs had been asked:

```text
What time is love?
```

Their answers were:

```text
The KLF’s answer: 3 a.m. Eternal.
3 a.m. Eternal.
KLF o’clock.
```

The stalled Claude orchestrator showed:

```text
User: What's happening on this canvas?
Assistant: Not logged in · Please run /login
```

This explained its stalled state.

The two remaining Claude conversation reads returned:

```json
{
  "code": "not_found",
  "message": "gateway conversation request failed with 404"
}
```

The precise conclusion is that their conversation history was unavailable
through the Gateway. A 404 does not prove that no conversation exists in any
store.

## Evidence flow

```text
whoami
  identifies the inspecting run
      ↓
workspace_summary
  supplies aggregate state
      ↓
roster
  identifies the seven live panes
      ↓
canvas_list and worktree_list
  map the Canvas to its branch and commit
      ↓
conversation per live run
  explains recent pane activity
```

## Final interpretation

At inspection time, the workspace contained 18 recorded panes. Seven were
live and 11 had exited. This Codex run was working, five panes were idle, one
Claude orchestrator was stalled because its harness was not logged in, and no
run was waiting for user input. The live runs were attached to the
`feat/multi-launch` worktree at commit
`72adadc1fd04827134c3512c3dd5c1176f24eba5`.

The MCP surfaces mapped the run to the `multi-launch` worktree root Canvas.
They did not expose enough identity to determine whether the run belonged to
one of its nested Canvases.
