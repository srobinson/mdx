# 496: conversation read: revisit summary selection and add a tool-parts projection

URL: https://github.com/littleorgans/transport-matters/issues/496
State: open
Labels: enhancement
Updated: 2026-08-27T21:28:59Z

The `conversation` read has two projection axes that are currently conflated into one parameter. `shape` selects **which messages** are returned. Tool visibility would select **which parts of each message**. Today only the first exists, and its `summary` value is underspecified.

Both were found while reading a delegated run's output over MCP, where the caller could see an agent's conclusions but not the tool calls behind them.

## 1. Revisit `summary`

`packages/activity/src/projections/conversation.ts:212`

```ts
const firstUser = messages.findIndex((m) => m.source.role === "user");
const selectedIndices = new Set<number>();
if (firstUser >= 0) selectedIndices.add(firstUser);
for (let index = Math.max(0, messages.length - 4); index < messages.length; index += 1) {
  selectedIndices.add(index);
}
```

`summary` is *first user message + last 4 messages*, deduped and re-sorted. The intent reads as a sound anchor: what was originally asked, plus where it ended up. The implementation has gaps.

- **Silent elision.** A caller receives first-user + last-4 with no explicit marker that anything was dropped. It can be inferred from a jump in `turn`, but `has_older` / `has_newer` already set the precedent for stating this outright. A caller that does not diff turn numbers will read a summary as a complete conversation.
- **`4` is an unnamed literal**, and it counts *messages*, not turns. Assistant preamble text is its own message, so "last 4" can collapse to roughly the final two turns on a long run. Defensible as a policy, but it is neither named nor documented.
- **Identical to `feed` below 5 messages.** With 3 messages, `firstUser` is 0 and `Math.max(0, 3 - 4)` is 0, so every index is selected. The two shapes are provably indistinguishable at small sizes. Observed in practice: `shape=feed` and `shape=summary` returned byte-identical payloads for a 3-message run.
- **No coverage of the divergence.** Worth confirming whether any test exercises a conversation long enough for the two shapes to differ.

Questions for the revisit: should the tail be counted in turns rather than messages, should the elision be reported in the result, and should the count be a named constant or caller-supplied.

## 2. Tool visibility

Text-only by default is correct and should stay the default. Bulk evidence belongs in the delegated run, conclusions in the caller's context. But there is currently no way to opt in, so a caller reading a delegated agent gets assertions with no access to the evidence. The Inspector already renders `TOOL_USE`, so the data exists in capture; it is the read projection that omits it.

**Proposed shape.** Not `include_tools` / `tools_only` booleans: two flags give four states, one contradictory, and `tools_only` is a filter value in a flag's clothing. It also collides with `shape` (what would `shape=summary, tools_only=true` mean?).

A projection over part types instead:

```
include: ["text"]                    # default, today's behaviour
include: ["text", "tool_use"]        # the common verification case
include: ["tool_use", "tool_result"] # full trace
```

No invalid states, composes with `shape` on its own axis, and extends to thinking blocks or attachments without another boolean.

**Why the parts must be separately selectable.** `tool_use` and `tool_result` have opposite economics. The call is small and high-signal: seeing `du -sh /private/tmp/*` establishes that an agent measured rather than inferred. The result is large and low-signal-per-token. In the motivating case `tool_use` alone would have closed the gap and the result was never needed. A single boolean forces the caller to buy both.

### Blocking design questions

- **Truncation.** Tool results are the largest payloads in a transcript. If opting in means inheriting a 200KB file read, the flag defeats the purpose it was added for. `max_chars_per_message` is per-message today; with parts it likely needs to be per-part, and results likely want a tighter budget than text.
- **Pagination.** `text_offset` / `total_chars` are per-message. If parts become addressable, cursor semantics change. Note `read_user_messages` in `api/src/transport_matters/controlplane/conversation_scan.py` walks fragments with strict contiguity assertions (`text_offset != expected_offset` raises 502) and pins `shape="feed"`, so any part-level change to offsets must keep that scan correct.
- **Reuse over reinvention.** The Inspector already projects tool blocks. A part taxonomy and serializer likely exist; this should reuse that projection rather than introduce a second one.

## Touch points

- `packages/activity/src/projections/conversation.ts` — `selectMessages`, the projection itself
- `packages/activity/src/ports.ts`, `packages/activity/src/server/activityRouter.ts` — request type and query parsing
- `api/src/transport_matters/controlplane/observe_models.py` — `ConversationShape`
- `api/src/transport_matters/api/v1/controlplane_gateway_reads.py` — query construction
- `api/src/transport_matters/api/v1/controlplane_mcp.py` — MCP tool surface
- `api/src/transport_matters/controlplane/conversation_scan.py` — fragment contiguity scan


## Sub issues
[]
