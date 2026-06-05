# PR #257 review — agent-state Slice 1 (grok)

- **PR / branch / head:** #257 / `agent-state-slice1` / `536140e44852d8b859b55da2cbf817f1e610358e`
- **Spec:** `~/.mdx/projects/tm-agent-state-spec-slice1.md`
- **Tree check:** pristine (clean working tree, HEAD matches head SHA)
- **Mode:** read-only review; no source edits
- **Verdict:** **approve with minors** — Slice 1 contract is met end to end; one residual machine edge is incomplete; hygiene pressure on the machine file.

## Summary

The PR delivers the locked in-place enum replace: flat wire vocabulary + `activityStatusTier`, domain split of turn-end vs question, exhaustive `wireStatusFromMachineState`, Claude/Codex reasoning+generating parse paths, fail-loud `stop_reason` table, router `needs_you`, and strip labels/tier styling. The old cast is gone. Frozen api capture plane and `docs/ARCHITECTURE.md` are untouched. Browser stays on `@tm/core` / `@tm/contract` (no `@tm/activity`). Fixtures stay on `@tm/contract/activity/testing`. Acceptance-oriented tests assert observable end states (`idle` ≠ `needs-you` at projection and strip).

## Issues

### Issue 1 — Severity: minor
- **Symbol:** `runActivityMachine` states `running-tools` → `record.reasoning` / `record.generating`; destinations `reasoning` / `generating`
- **Evidence:** Pre-main `running-tools` had no free exit into `thinking` via a status record; only `turn_open` (clears pending), tool completion, etc. This PR wires `record.reasoning` and `record.generating` into every non-final state per spec, including `running-tools`, while `applyReasoning` / `applyGenerating` preserve `pendingToolCallIds`. Neither `reasoning` nor `generating` handles `record.tool_result` / `record.tool_error` (only `running-tools`, `needs-you-asked`, `stalled` do).
- **Why it matters:** An out-of-order or multi-row stream that emits reasoning/generating while tools are still pending leaves the machine in `generating`/`reasoning` with ghost pending ids; a later `tool_result` is a no-op until something else moves the graph (e.g. stall). Journaled Claude order (text before tools in the same multi-record apply) usually avoids this; it is still a real hole on the new edges.
- **Suggestion:** While `pendingToolCallIds.length > 0`, either keep the run in `running-tools` on reasoning/generating (context-only refresh), or accept tool_result/tool_error from `reasoning`/`generating` the same way `stalled` does. Add a machine test that does `tool_use` → `generating` → `tool_result` and locks the chosen behavior.
- **Status:** open

### Issue 2 — Severity: minor (hygiene)
- **Symbol:** `packages/activity/src/domain/runActivityMachine.ts` (`runActivityMachine`)
- **Evidence:** File is **698 LOC** (repo hard guardrail: 700). Slice 1 correctly grew the transition table (idle split, generating, reasoning events on every non-final state, usage restore arms). Next meaningful edit will force a split under project rules.
- **Suggestion:** Before Slice 2/3 machine work, extract pure action/guard setup or per-state transition maps into a sibling module so the graph owner stays under the ceiling. Do not block this PR on it.
- **Status:** open

### Issue 3 — Severity: nit
- **Symbol:** `BaseRunActivityEvent` comment in `runActivityContext` (`messageText` documentation)
- **Evidence:** Comment still says messageText rides turn-end/tool-use only; generating records now carry `messageText` via `activityRecordToEvent` and `markApplied`.
- **Suggestion:** Update the comment to include generating.
- **Status:** open

## Spec conformance (checklist)

| Area | Result |
|------|--------|
| `activityStatuses` flat enum (reasoning/generating/needs-you-asked/needs-you-gated/idle/…) | pass |
| `activityStatusTier` pure, dep-free; stalled own tier | pass |
| `ActivityNeedsYou` + `ActivityWireRun.needs_you` | pass |
| `emptyStatusCounts` / fixtures / testing barrel; no fixture leak into prod barrel | pass |
| Machine: thinking→reasoning; turn-end→idle; question→needs-you-asked; idle wake-ups; gated unreachable comment | pass |
| ports + `activityRecordToEvent` for reasoning/generating | pass |
| `wireStatusFromMachineState` exhaustive never-default; projection uses it; needs_you only on asked | pass |
| Claude thinking→reasoning; text→generating; block kind order; Codex reasoning kept; message→generating | pass |
| stop_reason: end_turn\|max_tokens→turn-end; refusal→refused-turn; unknown→unmapped; tool_use\|pause_turn ignore | pass |
| Scaffold dedupe (`transcriptRowParser` / shared `tokens`) | pass (shared normalizer is `tokens`, not a named `usageTotals`; harness field maps remain correctly separate) |
| Router `needs_you`; strip STATUS_LABELS; tier via `activityStatusTier` | pass |
| Browser must not import `@tm/activity` | pass (prod imports clean) |
| FROZEN api capture plane / ARCHITECTURE.md | pass (absent from diff) |
| Red-first style tests for idle vs needs-you, stop_reason, strip Idle pill | pass |

## Hygiene / boundaries

- Contract purity surface unchanged in spirit (`packagePurity.test` still asserts zero runtime deps).
- `defaultNeedsYou` in fixtures duplicates domain `needsYouFromWireStatus`; acceptable across the contract↔domain boundary (fixtures cannot import `@tm/activity`). Optional later: one helper on `wire.ts` if Slice 2 adds gated payload.
- Duplication of large per-state `on` maps in the machine is pre-existing structure amplified by new events; Issue 2 covers the ceiling.

## Residual non-issues (checked, not filed)

- Codex assistant `message` no longer emits turn-end: intentional; `task_complete` owns idle.
- `needs-you-gated` has no machine state and `needs_you` stays null: matches projection rule for Slice 1 (asked only).
- Stall mechanism left as health overlay; idle has no silence timer.

## Pre-verdict tree

```
HEAD 536140e44852d8b859b55da2cbf817f1e610358e
branch agent-state-slice1
working tree clean
```
