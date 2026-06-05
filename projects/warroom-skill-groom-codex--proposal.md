# Warroom skill groom proposal

## Diagnosis

The current skill has the right standards, but the document spends too many words repeating the same operational cautions. The largest redundancy is compaction: the boundary rule appears in Non Negotiables, Phase And Churn Control, the compaction subsection, Slice Build Loop, Shared Practices, and Anti Patterns (`plugins/helioy-bus/skills/warroom/SKILL.md:57`, `:107-128`, `:286`, `:297-310`). The runtime prefix rule is correct and important, but line 58 is a dense paragraph that hides the usable rule.

Planning is the main missing piece. Mode 2 starts with grouping specs and dispatching engineers, then goes straight to writing spec files (`plugins/helioy-bus/skills/warroom/SKILL.md:203-220`). It does not require a code audit, reuse map, duplication scan, dead code scan, or an explicit pause when scout findings suggest a deviation or refactor. That gap invites blank page design and reinvention.

The existing Code Review mode primes `/code-review` and `/code-hygiene`, but only after implementation exists (`plugins/helioy-bus/skills/warroom/SKILL.md:222-252`). Those skills contain exactly the lenses Scout needs: code-review checks real bugs and project conventions (`/Users/alphab/.agents/skills/code-review/SKILL.md:12-32`), while code-hygiene measures structure, duplication, boundaries, seams, and verification (`plugins/helioy-tools/skills/code-hygiene/SKILL.md:31-68`, `:70-85`, `:139-161`). The revised skill should invoke those disciplines before design is locked, then use peer review later to protect quality. The extra tokens are justified when they buy independent evidence against false assumptions, duplication, and missed seams.

## Proposed leaner structure

1. Frontmatter and Role
2. First Decision, with a quality budget note
3. Agents and Setup
4. Non Negotiables
5. Phase And Churn Control
6. Message Protocol
7. Scout Before Plan, new load bearing section
8. Reviewer Skill Priming, shared once and referenced by review modes
9. Mode 1: Peer Consensus
10. Mode 2: Scout / Plan / Spec Writing
11. Mode 3: Code Review
12. Mode 4: Brainstorm
13. Mode 5: Slice Build Loop
14. Shared Practices
15. Anti Patterns

## Revised `SKILL.md` draft

```markdown
---
name: warroom
description: >
  Orchestrate a helioy-bus warroom: tmux agents doing scoped scout, planning,
  implementation, review, consensus, or brainstorm work under one orchestrator.
  Use for warroom, mixture of experts, MoE review, peer consensus, sign-off,
  brainstorm, spec-writing, code-review, engineering, and slice-build-loop work.
---

# Warroom

## Role

A warroom is a set of specialist agents running in tmux panes, connected through helioy-bus, working toward one bounded outcome.

You are the orchestrator. You choose the mode, phase the work, brief agents, monitor progress, synthesize results, apply authoritative changes, verify gates, and decide when to escalate.

Agents research, scout, draft, implement, and review. You own scope, reuse, evidence, context hygiene, and final judgment.

## First Decision

Do not spawn a warroom when all of these hold:

- The change is mechanically locked: one to three lines, one obvious implementation, no open design choice.
- The design is already adjudicated by a current spec, prior review, or earlier item in the same batch.
- Your own verification gate is sufficient evidence.

Use a warroom when parallel agents improve correctness, coverage, speed, or confidence.

| Need | Mode |
|------|------|
| Sign-off on an artifact | Peer Consensus |
| Scout existing code and plan before Linear or implementation | Scout / Plan / Spec Writing |
| Verification of existing code | Code Review |
| Divergent ideas before deciding | Brainstorm |
| Approved spec implemented as small PRs | Slice Build Loop |

Peer review spends tokens to buy quality. Independent agents catch false assumptions, missed reuse, duplicated contracts, weak boundaries, and stale-state errors that solo work often misses. Cut prose and ceremony first, not quality discipline.

## Agents and Setup

Choose runtime by task shape:

| Runtime | Context | Best For |
|---------|---------|----------|
| Claude | 1m context window | UI, design synthesis, broad research, long specs, and large-context tasks. |
| Codex | 250k context window | Backend work, implementation, tests, refactors, and patch quality. |

Use both for MoE when model diversity improves confidence. For focused execution, pick the runtime that fits the work.

Use the `helioy-warroom` MCP tools:

```python
whoami()
warroom_discover(query="security review")
warroom_spawn(name="design", agents=["brand-guardian", "ui-designer"])
warroom_spawn(name="moe", agents=["helioy-tools:codebase-analyst"])
warroom_add(name="moe", agent="helioy-tools:codebase-analyst", runtime="codex")
warroom_status(name="moe")
warroom_kill(name="moe")
```

Notes:

- Qualified names (`<namespace>:<agent>`) select the prompt; `runtime` controls the adapter.
- Passing the same plugin-qualified agent twice to `warroom_spawn` does not create MoE. Spawn once, then add the second pane with `runtime="codex"`.
- Named warrooms are idempotent. Spawning the same name kills the old warroom first.
- Prefer a clean upfront spawn. If membership changes, run `warroom_status` and address only fresh IDs.
- `pane_id` (`%NNN`) survives pane renumbering. Use it for `tmux capture-pane` and `/compact`.
- If MCP tools are unavailable, fall back to `~/.helioy/warroom.sh <name> "type1 type2 ..."`.

## Non Negotiables

- Run `whoami` first. Use that agent_id as `reply_to` in every dispatch.
- Run `warroom_status` after spawn, add, remove, recycle, or any membership change.
- Never reuse agent IDs after `warroom_add` or `warroom_remove`; panes renumber and bus IDs churn.
- Route replies to the orchestrator only. Do not wire agent-to-agent `reply_to` by default.
- Bus messages are single-sentence factual signals. Cite IDs, paths, SHAs, PRs, test names, and `file:line` evidence.
- If a message does not request a reply, do not reply.
- Bus pings wake you; they are not truth. Confirm `done`, `green`, `merged`, and `clean` claims from disk, `gh`, git, Linear, logs, or test output.
- Re-read live state before each verdict. Memory-only consensus is false consensus.
- Do not plan from a blank page. Planning and implementation require a current reuse map unless the task is mechanical and already adjudicated.
- Surface Scout findings before implementation when they reveal reuse, duplication, bad design, dead code, or a proposed deviation.
- Treat every completed phase and merged slice as a hard boundary. Before the next brief, recycle the warroom or compact every continuing pane and confirm compaction with `tmux capture-pane`.
- `/compact` compacts both Claude and Codex panes. Skill prefixes differ: Claude uses `/code-review`; Codex uses `$code-review`. Never send `$compact`.

## Phase And Churn Control

A phase must be large enough to justify spawn, briefing, and synthesis, but small enough that agents finish before context becomes stale.

Before dispatch, define the phase contract:

- Goal: one bounded outcome.
- Inputs: exact files, Linear IDs, PRs, specs, SHAs, or commands to read.
- Outputs: one artifact, verdict set, PR, decision batch, or Scout report.
- Required reuse output when planning or implementing: reuse map, rejected alternatives, and deviation decisions.
- Done line: exact single-sentence reply shape.
- Gate: how you will verify the phase yourself.
- Closeout: recycle or compact.

Right-size phases:

- Combine mechanical siblings that share context, code path, gate, and reviewer.
- Split work across independent artifacts, unrelated modules, multiple repos, long diffs, long research inputs, or more than one expected fix-review loop.
- Do not phase every tiny edit.
- Do not run open-ended mega-phases.

End every phase with one action:

1. **Recycle**: `warroom_kill(name=...)`, then spawn fresh panes. Default after heavy reads, long implementation, role changes, completed slices, merges, or context-heavy reviews.
2. **Compact**: for each continuing pane, run `tmux send-keys -t %NNN '/compact' Enter`. Use only when continuity matters and the same agents continue into a closely related phase.

After `/compact`, confirm via `tmux capture-pane -t %NNN -p | tail -5` that compaction started or finished before sending the next brief. If the command remains at the prompt, send a bare `Enter` and check again. If you cannot check, wait before dispatch. Compaction evicts skill priming, so re-prime skill-dependent panes before the next review.

Never brief a stale pane. A just-finished slice carries residue from diffs, errors, gates, and merge chatter. That residue is liability. Durable knowledge lives in merged code, specs, and artifacts that the agent can re-read.

## Message Protocol

All dispatches use orchestrator-only replies:

```python
send_message(to=A, reply_to=ORCHESTRATOR, topic="{project}-{mode}", content=brief)
send_message(to=B, reply_to=ORCHESTRATOR, topic="{project}-{mode}", content=brief)
```

Use `;` recipients only when the exact same brief applies to multiple agents. Still set `reply_to` to the orchestrator.

Every brief must say:

> Reply to the orchestrator only, in one sentence. Keep to facts and evidence. Do not message other agents. Do not summarize unless asked. If this message does not ask for a reply, do not reply.

Prefer typed reply shapes:

- `done: <artifact|branch|PR> <evidence>`
- `blocked: <cause> <needed>`
- `review: clean <evidence>`
- `review: issue <severity> <path:line> <fact>`
- `signoff: I sign off on <X> as currently filed`
- `conditional: I sign off conditional on the following changes: <numbered facts>`

Large artifacts go to files you name and read. The bus is the signal, not the artifact.

For no-reply notices, write `FYI no reply needed: <fact>`.

## Scout Before Plan

Scout is required before Spec Writing and implementation unless the task is mechanical and a current spec already names the reuse map and gate.

Scout answers:

1. What code, tests, migrations, commands, scripts, schemas, fixtures, infra, docs, or prior decisions already exist?
2. What will we reuse, with file paths and symbols?
3. What similar implementations were checked and rejected, with reasons?
4. What duplication, parallel implementation, boundary problem, dead code, or bad design exists in the touched area?
5. What decision is needed before implementation, including deliberate deviation, refactor first, delete old path, or accept existing debt for this slice?
6. What tests or gates prove the plan?

Use existing disciplines rather than copying them here:

- `/code-review` lens: real bugs, convention violations, historical context, and false-positive filtering.
- `/code-hygiene` lens: measurement, reuse, duplication, seams, boundaries, file and function size, dead paths, and verification.

Scout output must include:

```markdown
## Reuse Map
- Reuse: <path> <symbol or command> <why>
- Existing infra: <path or tool> <how it will be used>
- Similar checked and rejected: <path> <reason>
- None found: <searches run> <why new code is justified>

## Quality Map
- Duplication or parallel implementation: <path:line or symbol> <fact>
- Boundary or design issue: <path or symbol> <fact>
- Dead code or obsolete path: <path or symbol> <evidence>
- Grooming recommendation: refactor first | refactor during slice | defer with reason

## Plan
- Decision needed: <question or none>
- Proposed steps: <ordered list>
- Tests and gates: <commands>
```

If Scout finds an existing path to reuse, make that the default. If Scout finds a better deviation or cleanup, surface it before implementation. A deviation can be the right answer, but only after the orchestrator or human chooses it deliberately.

## Reviewer Skill Priming

Prime reviewers before Code Review and Slice Build Loop review passes. For Scout, prime only when the agent needs those lenses and would otherwise jump straight to solution design.

Context first, then skills. A skill invocation is an action trigger. Sending `/code-review` or `$code-review` into an empty pane can start the wrong review.

Default priming uses `tmux send-keys` because it is verifiable:

```bash
tmux send-keys -t %PANE "I am priming you with /code-review and /code-hygiene for an upcoming <artifact> pass. Await my bus brief; do not start yet. When the brief arrives, proceed immediately. No writes by you or subagents; verify the tree is pristine before any verdict." Enter
sleep 2; tmux send-keys -t %PANE Enter
sleep 1; tmux send-keys -t %PANE "/code-review" Enter
sleep 1; tmux send-keys -t %PANE "/code-hygiene" Enter
sleep 2; tmux capture-pane -t %PANE -p | tail -5
```

For Codex skill commands, use `$code-review` and `$code-hygiene`. Keep `/compact` unchanged on both runtimes. If any line remains at the prompt, send a bare `Enter` and re-check.

Brief-time skill invocation is a fallback only when send-keys is unavailable.

## Mode 1: Peer Consensus

Use after drafting a substantial artifact, such as a Linear plan, spec, design doc, PR, or risky decision, before treating it as final.

Default composition: same agent prompt on Claude and Codex.

```python
warroom_spawn(name="moe-{topic}", agents=["helioy-tools:codebase-analyst"])
warroom_add(name="moe-{topic}", agent="helioy-tools:codebase-analyst", runtime="codex")
warroom_status(name="moe-{topic}")
```

Variant order:

1. Same `helioy-tools:*` prompt on Claude and Codex.
2. Cross-role same-runtime panes, such as `code-reviewer` plus `silent-failure-hunter`.
3. Two same-runtime same-role panes, only when no better composition exists.
4. Three panes for high-stakes tie-breaking.

Brief agents independently. Do not ask them to debate each other. The orchestrator synthesizes.

The brief must include artifact, baseline ref, checklist or skill, discipline to find at least one substantive issue or positively justify none found, no-writes boundary, reply shape, sign-off strings, and an iteration bound.

Flow:

1. Agents independently re-read live state and reply to the orchestrator.
2. Orchestrator compares verdicts and evidence.
3. If both clean, accept only if they sign off on the same artifact shape.
4. If either finds an issue, apply the agreed change or send one focused correction brief.
5. Ask both agents to re-read live state and send final sign-off.
6. Persist durable consensus with `cx_store` or `cx_deposit`.
7. Recycle or compact before the next phase.

Escalate if agents disagree after two bounded rounds or if the fix changes scope.

## Mode 2: Scout / Plan / Spec Writing

Use when planning not trivial implementation before Linear or code.

Flow:

1. Group work into natural spec units. Each unit should map to one future Linear sub-parent.
2. Dispatch Scout first for each unit. Require the Scout output shape from Scout Before Plan.
3. Read the Scout files. Decide reuse, deviation, refactor, deletion, and deferral choices before any spec is treated as approved.
4. If Scout reveals a material deviation or cleanup choice, surface it to the orchestrator or human before implementation.
5. Dispatch spec writers with the approved Scout decisions, exact output path, required contents, done line, and verification gate.
6. Engineers write named files, such as `~/.mdx/projects/{project}-spec-{grouping}.md`, then send one `done:` line.
7. Send an architect reviewer the files, Scout decisions, and criteria. Reviewer replies `review: clean ...` or `review: issue ...`.
8. Send one focused fix round to each engineer, then ask the architect to verify deltas only.
9. When specs are approved, file Linear according to `helioy-tools:linear-workflows`.
10. Consider Peer Consensus on the filed tree.
11. Recycle or compact before the next phase.

Every spec must include the reuse map, quality map, approved deviations, implementation steps, removal or extraction map when relevant, and verification gates.

## Mode 3: Code Review

Use when implementation exists and needs verification against a spec, issue, or PR.

Flow:

1. Run the baseline gate first, such as `cargo check`, `cargo test`, `pnpm test`, or the repo's `just ci`.
2. Default focus is functionality unless the user asked for full or security review. Ask only when requested depth is unclear.
3. Dispatch reviewers in parallel. Use one reviewer per issue, PR, or coherent code area.
4. Each dispatch names SPEC, CODE, baseline ref, Linear issue or PR, scope, focus, explicit do-not-flag list, key checks, no-writes boundary, and reply shape.
5. Prime reviewers with Reviewer Skill Priming unless the review is intentionally narrow and the brief says why.
6. Reviewers reply to the orchestrator only: `review: clean <evidence>` or `review: issue <severity> <path:line> <fact>`.
7. Create follow-up work only for genuine findings. Do not change sub-parent status for review findings.
8. Synthesize a concise table: area, reviewer, verdict, evidence, follow-up.
9. Recycle or compact before the next phase.

## Mode 4: Brainstorm

Use when exploring a problem space and collecting diverse perspectives before deciding.

Flow:

1. Send the same problem statement in parallel, with each agent's task tailored to its expertise.
2. Tell agents not to coordinate with peers.
3. Each agent writes to `~/.mdx/projects/{project}-{agent-role}--brainstorm.md`.
4. Each agent sends one `done:` line to the orchestrator.
5. Read the files, compare convergence and contradictions, then present the synthesis.
6. Transition to Scout / Plan, direct execution, or Peer Consensus.
7. Recycle or compact before the next phase.

## Mode 5: Slice Build Loop

Use when an approved spec must land as small, PR-sized slices.

Default composition: one engineer pane on the stronger build model and one reviewer pane on the adversarial reader. Escalate reviewer coverage to Peer Consensus only for high-blast-radius slices: durability, identity, rekeying, deletion, migration, or commit seams.

Review weight scales with blast radius. Small mechanical PRs get orchestrator diff read plus the gate. The existence of a reviewer pane is not a reason to spend a full review pass.

Per slice:

1. Confirm the slice has a current reuse map and quality map. If not, run Scout before implementation.
2. Brief the engineer with numbered deliverables, spec section, reuse map, extraction or removal map, branch expectations, tests, and done line: `done: <branch> <sha> PR#<n>` or `blocked: <one sentence>`.
3. On `done:`, verify the PR yourself with `gh pr view N`; never trust the bus line alone.
4. Brief the reviewer for one adversarial pass against the PR. Use Reviewer Skill Priming first unless the review is intentionally narrow and you say why. Findings are Blocker, Major, or Minor with `file:line`.
5. Reviewer replies `review: clean <evidence>` or `review: issue <severity> <path:line> <fact>`.
6. Send the engineer one focused fix round. Every fix needs failing-before and passing-after evidence where feasible.
7. Reviewer verifies deltas only.
8. Run `gh pr checks N`, `just ci`, or the repo gate against real services.
9. Surface only dual-clean, gate-green PRs to the human. The human holds the merge gate.
10. After the slice, recycle by default. Compact only if the same agents continue into a tightly related next slice.

Deletion slices require a forward-removal map first: delete, keep, trim, and extracted reusable core.

## Shared Practices

- Use `tmux capture-pane -t %NNN -p` to check progress without messaging agents.
- Read artifact files after completion. The bus is not the artifact.
- Store durable outcomes with `cx_store` or `cx_deposit` when a decision, lesson, consensus result, or reusable pattern emerges.
- Specs and docs cite symbols, not line numbers. Bus review verdicts may use `path:line` for code findings against a named SHA.
- Pin the baseline for citation checks. Verify code references against a named ref, such as `git show main:path`, not an arbitrary working tree.
- Return shared checkouts to the baseline branch after PR gating before dispatching unrelated review.
- Use `warroom_kill` plus fresh spawn when context is heavy, agents drift, panes get noisy, or the next phase changes composition.
- Use `/compact` only for continuing panes that need local continuity, then verify it and re-prime skills if needed.

## Anti Patterns

| Do NOT | Instead |
|--------|---------|
| Plan from a blank page | Scout existing code, then write a reuse map before planning. |
| Treat reuse as optional | Require reuse map evidence or explicit none-found searches. |
| Hide Scout findings inside implementation | Surface reuse, duplication, dead code, bad design, and deviation decisions before code. |
| Use background subagents for warroom work | Spawn tmux agents that can receive bus nudges and iterate. |
| Wire `reply_to` between agents by default | Route all replies to the orchestrator and synthesize there. |
| Run peer debate on the bus | Collect independent verdicts, then send one focused correction or sign-off request. |
| Send long prose, diffs, logs, or essays over the bus | Send one sentence with IDs, paths, SHAs, tests, and `file:line` evidence. |
| Reply to FYI or no-reply messages | Do not reply unless the message asks for one or blocks progress. |
| Start the next phase in stale panes | Recycle or send `/compact` to every continuing pane first. |
| Reuse a just-finished slice pane because your context budget looks fine | Compact or recycle before the next brief. |
| Phase every tiny task | Combine mechanical siblings with shared context and gate. |
| Run mega-phases that saturate context | Split by artifact, module, repo, decision boundary, or review loop. |
| Trust a `done`, `green`, `clean`, or `merged` bus line | Verify from disk, `gh`, git, Linear, logs, or tests. |
| Reuse agent IDs after add or remove | Run `warroom_status` and use fresh IDs. |
| Ask reviewers to write files by default | Use bus verdicts unless findings need a file and you will read it. |
| Ship fix rounds without tests | Pair fixes with failing-before and passing-after evidence where feasible. |
| Use same-runtime same-role agreement as strong signal | Prefer mixed runtime MoE or cross-role diversity. |
| Let agents apply authoritative artifact changes during consensus | Agents propose; orchestrator applies and verifies. |
```
