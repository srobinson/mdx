# 602: Port the two-agent ping pong review loop from tmux to Canvas

URL: https://github.com/littleorgans/transport-matters/issues/602
State: open
Labels: 
Updated: 2026-09-02T16:49:29Z

## Position

The two-agent "ping pong" review loop was designed for agents in tmux panes talking over
helioy-bus. The delivery contract still holds; the transport around it was scaffolding for
tmux and should not be ported. This issue records where the Canvas translation stands and
the threads still open.

Source workflow: cm entry `01a05554-0534-7933-b7a9-9967b69e8efd` (scope
`global/project:helioy/repo:transport-matters`).

### Survives unchanged

The exact commit SHA is the unit of handoff. Gate evidence attaches to a SHA and is reusable
while the head is unchanged. The loop terminates only when both agents bless the same SHA.
A blessing of an earlier SHA does not bless a later one. PR after both blessings, merge on
Stuart's authorization. All of this is transport independent.

### Was scaffolding for tmux

| tmux mechanism | Canvas replacement |
| --- | --- |
| pane discovery, "never hardcode pane numbers", re-register after pane changes | `launch` returns a durable `run_id`; `roster` lists them. The re-registration section deletes. |
| helioy-bus mail, "you have mail!" nudges, do not poll | `prompt` returns a `delivery_id`, `wait_for_reply` returns that delivery's bounded reply. Correlation is in the transport. `watch` on `turn_completed` / `needs_you` covers the rest. |
| model and role contract discovered at runtime | Composition is declared at launch: agent id, harness, model, effort. |
| one shared checkout, implicit | One Workdir per agent via `worktree_create`. Handoff travels by SHA through the shared origin. Two agents in one checkout is a live hazard today. |

### New in Canvas: there is a director

In tmux the agents were peers, each privately remembering whose turn it was and which SHA was
blessed. In Canvas the orchestrator sees both conversations and can hold that state machine
centrally. Two candidate shapes:

1. **Director relays.** Agents launch with grant `none`. The orchestrator prompts A, waits,
   reads the SHA, prompts B with it, waits. The blessing ledger is orchestrator state.
   Deterministic, observable, cannot deadlock on unread mail.
2. **Peers with a referee.** Agents get `director` grant and prompt each other. Closer to the
   original, more moving parts, reintroduces the "did they read it" question.

Current lean is shape 1. It also gives the architecture-disagreement step a real home: the
escalation goes to the director, who puts it to Stuart, rather than two agents negotiating
design in mail.

## Primary constraint: token efficiency

This is the governing concern for the next iteration, ahead of fidelity to the original
workflow. Where the loop currently spends tokens:

- Two agents each carry full repo context. Round N carries rounds 1..N-1 of argument.
- A relaying director puts every handoff through a third context.
- Prose handoffs restate what the diff already says.
- Both agents re-read the same files every round.
- `conversation` pulls are expensive next to a bounded `wait_for_reply`.

### Threads to explore

Nothing below is decided.

- **Pointer, not payload.** A handoff carries branch and SHA. The reviewer reads the diff from
  git. No diff, no file content, and no restated rationale travels in a message.
- **Capped reply schema.** Agents answer in a fixed small shape: SHA, verdict, changed
  behaviour, gates run or reused. Anything longer is a bug in the prompt.
- **Fresh run per round.** Instead of two long-lived agents accumulating context, launch a run
  per round whose context is the brief plus the diff. Cheaper, and a reviewer with no memory of
  writing the code may review it better. Trade-off: loses continuity and earned judgment.
- **Director holds addresses, not content.** The orchestrator's context stays near constant
  regardless of round count.
- **Asymmetric models.** Decide deliberately which side gets the expensive model. Implementation
  and review do not obviously deserve equal spend.
- **Measure it.** No target is meaningful until a round trip has a token cost attached. Worth
  instrumenting before tuning.

## Next

Iterate on the shape here, then supersede the cm entry with the Canvas version once settled.


## Sub issues
[]
