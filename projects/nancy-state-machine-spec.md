# Nancy state machine spec

Status: **draft, evolving**. This is a running doc capturing the target workflow architecture for Nancy. Mixes current behavior with aspirational design; sections are tagged where the distinction matters.

Date opened: 2026-05-02

## Philosophy

1. **One request, hands-off completion.** A unit of work begins with a single request (text prompt, spec file reference, Linear master issue, etc; the conveyance is semantics). Once accepted, the loop runs through all workflows until COMPLETE. The pre-workflow conversation that produces the request is upstream and out of scope for the state machine.

2. **Linear is the state oracle.** Mode is derived, never commanded. The selector is a pure function `Linear → Mode`. To change state, edit Linear.

3. **ESC is the only escape hatch.** Human interrupts by pressing ESC in the foreground terminal. No alternative override commands. Reduces surface area, prevents desync.

4. **State machine in one place.** Single module owns states, transition conditions, guards. Adding a new state means editing one file.

5. **Workflows are leaves.** Each state has exactly one workflow (a prompt template + agent invocation pattern). The state machine selects which workflow; the workflow executes. Workflows never know about each other.

6. **Hands-off iteration.** The loop self-advances. When workflow N finishes, the next selector tick reads Linear and picks workflow N+1. No state baton passed in code.

## Pipeline overview

```
[pre-workflow]      human ↔ agent conversation, produces master Linear issue
       │
       ▼
1. PM workflow                 decompose master issue into Linear issue tree
       │
       ▼
2. agent_issue_review          review the authored sub-issues
       │
       ▼
3. execution                   drain the authorized backlog, issue-by-issue
       │
       ▼
4. post_execution_review       review the executed work; may spawn new issues
       │             ↶ (if new issues created, return to step 2)
       ▼
5. COMPLETE                    everything green; loop exits
```

## Pre-workflow (out of scope for state machine)

Human and agent collaborate (chat, brainstorm, refine). Deliverable: a master Linear issue summarising the work to be done. This issue becomes the entry point for the state machine.

The state machine begins when `nancy go <task>` is invoked against this master issue.

---

## Stage 1: PM workflow

**Trigger:** master Linear issue exists; no decomposition yet (no children, or children are open planning items).

**Deliverable:** master issue decomposed into a Linear issue tree (sub-issues representing the actual units of work).

**Substrate options:**
- (a) **Warroom** — multi-agent tmux orchestration; agents collaborate in parallel panes coordinated via helioy-bus
- (b) **Linear workflow** — intentional, deliberate, painstaking; one or two agents iterate Linear directly with explicit gate authoring + acceptance steps

**Current state:** the Linear workflow exists today as the "two-agent planning gate" (Codex authors gate, Claude reviews; produces "Outcome: Ready for execution"). Warroom substrate is not yet used for this stage.

**Exit condition:** gate accepted with `Outcome: Ready for execution`, sub-issues authored under the gate.

**Open question:** when do we use warroom vs Linear workflow? Heuristic? User choice? Issue-size based?

---

## Stage 2: agent_issue_review_workflow

**Trigger:** authorized sub-issues exist that have not been reviewed.

**Deliverable:** every authorized sub-issue is reviewed; ready for execution. Issues that fail review are marked accordingly (returned to PM stage, edited, or deleted).

**Substrate options:**
- (a) **Two-agent tag team** (current) — Linear-driven; reviewer agent processes one issue at a time
- (b) **Warroom** — parallel review across multiple agents

**Current state:** two-agent tag team exists today via `agent_issue_review` mode in selector.

**Exit condition:** all authorized sub-issues reviewed and approved; ready for execution.

**Re-entry:** Stage 4 (post-execution review) can spawn new sub-issues that must be reviewed before execution. Re-enters this stage.

---

## Stage 3: execution

**Trigger:** authorized, reviewed sub-issues exist in `Todo` or `In Progress` state.

**Deliverable:** every authorized sub-issue reaches `QA Approved` (after worker completes and reviewer approves).

**Substrate:** two-agent tag team. Worker completes work; reviewer reviews.

**Inner-loop semantics (aspirational):**

The worker stage is an **inner loop**: when the sidecar kills the worker on context threshold, the next outer-loop iteration starts ANOTHER worker iteration on the same issue (fresh context, summary carryover). The kill IS the rotation mechanism. The loop only exits the worker stage when the worker updates Linear with `Worker Done`.

The reviewer stage works the same way: rotate-on-threshold inner loop, exits when reviewer marks the issue as either:
- `QA Approved` (new status, accepted) → state machine moves on
- `QA Failed` (new status, rejected) → issue state returns to `Todo`, worker takes another pass

**Current state (problem to fix):**
- Worker hits context threshold → sidecar kills (this is fine; it's how rotation works)
- **But** the outer loop currently routes to the reviewer on worker exit, regardless of whether the worker posted `Worker Done`
- Reviewer kicks in prematurely on possibly incomplete work
- The fix is at the routing layer, not the kill layer

**Required changes for aspirational model:**
- New Linear statuses: `QA Approved`, `QA Failed`
- Outer loop reads Linear after each worker iteration; if state is not `Worker Done`, stay in worker stage and rotate again
- Reviewer stage adopts the same rotate-on-threshold pattern, exits on `QA Approved` or `QA Failed`
- Transition trigger: Linear status, not process exit code

**Open questions:**
- How does worker carry state across rotations? (Session summary written to task dir? Re-read Linear + repo? Both?)
- What's the worker's stop condition if they CAN'T complete the work? Manual `Worker Failed` status? Block label? Escalation prompt after N rotations?
- Should there be a max-rotation cap to prevent runaway loops on impossible work?
- Sidecar role unchanged (token tracking, kill on threshold) — only the post-kill routing changes

---

## Stage 4: post_execution_review_workflow

**Trigger:** all authorized execution issues are `QA Approved`; review issues queued OR no review issues yet but execution drained.

**Deliverable:** holistic review of the completed work. May produce:
- New corrective sub-issues (back to Stage 2 → Stage 3)
- New planning items (back to Stage 1 if scope expanded; rare)
- Approval (transitions to COMPLETE)

**Substrate options:**
- (a) **Linear workflow** (current) — single review agent processes review-tagged issues one at a time
- (b) **Warroom orchestration** — parallel review agents identify defects independently

**Warroom-specific concern:**
If multiple agents in a warroom each surface defects, we need a deduplication / enhancement process:
- Agents send defects to a shared queue (helioy-bus)
- A coordinator agent identifies duplicates and merges them into single Linear issues
- Existing issues get enhanced with new findings rather than re-created

This coordinator does not exist today; it is a precondition for the warroom substrate at this stage.

**Exit conditions:**
- All review-spawned issues are `Done` AND no new work surfaced → transition to COMPLETE
- New work surfaced → cycle back to Stage 2 (or Stage 1 if scope-expanding)

---

## Stage 5: COMPLETE

**Definition (strict):**

COMPLETE fires when ALL conditions hold:

1. A gate was authored and accepted (`$accepted_gate != null`)
2. Every issue in `authorized_ids` has terminal state (`Done`, `Canceled`, or `Duplicate`; not `Worker Done`, not `QA Approved` if those become intermediate)
3. No execution work is selectable (`execution_open == 0`)
4. No corrective work is selectable (`corrective_open == 0`)
5. No review work is selectable (`review_open == 0`)
6. No unauthorized children under the gate parent (`unauthorized == 0`)
7. No open planning issues at parent level (`open_planning == 0`)
8. No pending gate review (`open_gate_review == null`)

**Side effect:** supervisor writes `COMPLETE` sentinel file. Loop exits cleanly via `task::is_complete` at `src/cmd/start.sh:555`.

**Plain English:** the accepted gate's scope is fully resolved, every spawned sub-task (corrective, review, or new) is also resolved, and no fresh planning has appeared. The state machine has nothing left to do.

---

## Cross-cutting concerns

### New Linear statuses (proposed)

| Status | Meaning | Set by | Triggers |
|--------|---------|--------|----------|
| `Todo` | not started | system | initial / `QA Failed` reset |
| `In Progress` | worker is iterating | worker | start of work |
| `Worker Done` | worker claims completion | worker | end of inner loop |
| `QA Approved` | reviewer approved (new) | reviewer | end of review inner loop, accepted |
| `QA Failed` | reviewer rejected (new) | reviewer | end of review inner loop, rejected; auto-transitions to `Todo` |
| `Done` | accepted (terminal) | reviewer or post-review | final acceptance |
| `Canceled` / `Duplicate` | out of scope | human | acknowledged, doesn't block COMPLETE |

The `released("final_completion")` predicate at `src/linear/selector.sh:30` already requires `state == "Done"` for terminal completion, so adding intermediate `QA Approved` does not affect COMPLETE conditions.

### Worker context threshold (current pain → desired model)

**Current:** worker hits token threshold → sidecar kills → outer loop routes to reviewer (premature; reviewer runs against possibly incomplete work).

**Desired:** sidecar still kills on threshold (rotation is the only way to manage context). What changes is the routing: outer loop checks Linear status after the kill, and if not `Worker Done`, stays in the worker stage and starts a fresh iteration on the same issue.

**Open:** continuation prompt design. The supervisor needs to give the next worker iteration enough context to make progress without re-discovering everything. Options: session summary written by previous worker, re-read of Linear + repo state, both. This affects how `templates/modes/execution.md.template` is structured (must instruct the worker to write a handoff summary before exiting).

The supervision substrate (sidecar + tmux foreground worker) does not change. Only the loop's routing logic changes.

### Substrate matrix

| Stage | Linear workflow | Two-agent tag team | Warroom |
|-------|-----------------|---------------------|---------|
| 1. PM | ✅ current | possible | possible (needs design) |
| 2. agent_issue_review | possible | ✅ current | possible (needs design) |
| 3. execution | n/a | ✅ current (needs inner-loop fix) | unclear |
| 4. post_execution_review | ✅ current | possible | possible (needs dedup coordinator) |

---

## Selector mapping (current → target)

Today's selector returns: `planning | corrective_resolution | post_execution_review | execution | needs_human_direction`.

Target mapping:

| Selector mode | Stage |
|---------------|-------|
| `planning_gate` (renamed/split) | 1. PM workflow (gate authoring + acceptance subset) |
| `agent_issue_review` (split out) | 2. agent_issue_review_workflow |
| `execution` | 3. execution |
| `corrective_resolution` | 3a. corrective sub-state of execution (or peer state, decision pending) |
| `post_execution_review` | 4. post_execution_review_workflow |
| `final_completion` (new) | 5. COMPLETE |
| `needs_human_direction` | escape state (orphan) |

Adding `final_completion` is the minimum change to close the loop. Splitting `planning` into `planning_gate` + `agent_issue_review` makes Stage 1 vs Stage 2 distinction explicit (currently collapsed).

---

## Open questions (running list)

1. Warroom vs Linear workflow per stage: when to use which? Heuristic, user choice, issue-size?
2. Inner-loop self-rotation mechanism for worker: how does state carry across rotations?
3. Worker stop condition when work is genuinely impossible: manual `Worker Failed` status? Block label? Escalate to human?
4. Sidecar role after kill-on-threshold is removed: telemetry only? Or other supervision?
5. Warroom defect dedup coordinator design (Stage 4): exists nowhere today; needed if warroom is used for post-review.
6. Corrective_resolution: peer state or sub-state of execution?
7. agent_issue_review entry: once after planning, every time new sub-issues appear, or unified "any unreviewed" condition?
8. How does the state machine handle a master issue with NO children (no decomposition done)? Stay in Stage 1, or escape to needs_human_direction?

---

## Things to verify against current code

- [ ] Selector if/elif chain reflects the 5 stages cleanly (currently 5 modes but mapping is fuzzy)
- [ ] Each stage has exactly one prompt template
- [ ] Transition conditions are derivable from Linear alone (no hidden state)
- [ ] `task::mark_complete` has exactly one caller (the selector hitting `final_completion`)
- [ ] No `CODE_COMPLETE` references remain (already removed; verify in next iteration)
- [ ] No worker-written `COMPLETE` instructions remain in any prompt template
