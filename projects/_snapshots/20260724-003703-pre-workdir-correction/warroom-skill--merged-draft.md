---
name: warroom
description: >
  Orchestrate a helioy-bus warroom: tmux agents doing parallel work under one
  orchestrator. Use for warroom, mixture of experts, MoE review, peer consensus,
  sign-off, brainstorm, spec-writing, scout, reuse audit, code-review,
  engineering, slice-build-loop, or any request that dispatches work to parallel
  agents.
---

# Warroom

## Role

A warroom is a set of specialist agents running in tmux panes, connected through helioy-bus, working toward one shared goal. You are the orchestrator: choose the mode, phase the work, brief agents, monitor progress, synthesize results, apply authoritative changes, and verify gates.

Agents research, scout, review, draft, and implement. You own scope, reuse, evidence, context hygiene, and final judgment.

## The Spine: Scout → Build → Review

Every build runs three beats, in order:

1. **Scout** — audit the existing code and infra in the area you are about to touch, *before* designing anything. Produce a reuse map and surface duplication, dead code, and design risk. Skipping scout bakes in reinvention. (Real failure: an engineer hand-wrote a table list when the migration runner already produced a migrated DB.)
2. **Build** — spec and implement against the reuse map, in PR-sized slices.
3. **Review** — verify against the spec, issue, or PR, with review weight scaled to blast radius.

Scout is the first beat, not optional polish. The modes below instantiate these beats.

## First Decision

Do not spawn a warroom when ALL of these hold:

- The change is mechanically locked: one to three lines, one obvious implementation, no open design choice.
- The design is already adjudicated by a current spec, prior review, or earlier item in the same batch.
- Your own verification gate is sufficient evidence.

Otherwise use a warroom when parallel agents improve correctness, coverage, speed, or confidence. Spawning is lightweight (a tmux pane plus bus registration); agents cost tokens only once briefed and working.

| Need | Mode |
|------|------|
| Audit existing code before building | Scout & Plan |
| Planning before Linear or implementation | Spec Writing |
| Approved spec implemented as small PRs | Slice Build Loop |
| Verification of existing code | Code Review |
| Sign-off on an artifact | Peer Consensus |
| Divergent ideas before deciding | Brainstorm |

Peer review spends tokens to buy quality. Cut prose and ceremony first, never quality discipline (see Why We Spend Tokens On Review).

## Agents

Choose runtime by task shape:

| Runtime | Context | Best For |
|---------|---------|----------|
| Claude | 1m context window | UI work, design synthesis, broad research, long specs, or any task where large context is the main constraint. |
| Codex | 250k context window | Backend work, implementation, tests, refactors, and codebase changes where code execution and patch quality dominate. |

For MoE, use both when the artifact benefits from model diversity. For focused execution, pick the runtime that fits the work instead of defaulting to mixed panes.

## Setup

Use the `helioy-warroom` MCP tools.

```python
warroom_discover(query="security review")
warroom_discover(namespace="helioy-tools")

warroom_spawn(name="design", agents=["brand-guardian", "ui-designer"])

# MoE: same prompt, one pane per runtime.
warroom_spawn(name="moe", agents=["helioy-tools:codebase-analyst"])
warroom_add(name="moe", agent="helioy-tools:codebase-analyst", runtime="codex")

warroom_status(name="moe")
warroom_kill(name="moe")
```

- Qualified names (`<namespace>:<agent>`) select the namespace prompt; `runtime` controls the adapter.
- Passing the same plugin-qualified agent twice does not create MoE; both panes use the default adapter. Spawn once, then `warroom_add` the second pane with `runtime="codex"`.
- Named warrooms are idempotent; spawning the same name kills the old one first.
- Prefer a clean upfront spawn. If membership changes mid-build, call `warroom_status` and address only the fresh IDs.
- If MCP tools are unavailable, fall back to `~/.helioy/warroom.sh <name> "type1 type2 ..."`.

## Non-Negotiables

- Run `whoami` first. Use that agent_id as `reply_to` in every dispatch.
- Run `warroom_status` after any membership change (spawn, add, remove, recycle). Never reuse agent IDs after add or remove; panes renumber and bus IDs churn. Use `pane_id` (`%NNN`) for `tmux capture-pane` and `/compact` — it survives renumbering.
- Route replies to the orchestrator only. Do not wire agent-to-agent `reply_to` by default.
- Bus messages are single-sentence factual signals. Cite IDs, paths, SHAs, PRs, test names, and `file:line` evidence. If a message does not request a reply, do not reply.
- Bus pings wake you; they are not truth. Confirm `done`, `green`, `merged`, and `clean` from disk, `gh`, git, Linear, logs, or test output. Re-read live state before each verdict; memory-only consensus is false consensus.
- **Scout before you build.** Any work touching existing code starts with a Scout & Plan pass and a reuse map. A plan that introduces a new helper, type, table, runner, or command for a capability the reuse map already lists is a defect.
- Every completed phase and every merged slice is a hard boundary: compact (confirm via `capture-pane`) or recycle the continuing pane BEFORE the next brief. Re-briefing a stale pane is a defect, not an optimization. See Priming & Compaction.

## Priming & Compaction

The single home for the tmux choreography. Every other section points here.

**Prefix rule.** `/compact` compacts BOTH runtimes — always `/compact`, never `$compact` (on a Codex pane `$compact` opens a non-existent skill and does nothing). SKILL names differ by runtime: Claude `/code-review`, Codex `$code-review` (`$` is Codex's skill prefix). This doc writes `/name`; on a Codex pane swap `$` for skill names only, never for `/compact`.

**Swallowed Enter.** The first Enter is often eaten (command palettes, paste buffers). After any send-keys line, if `capture-pane` shows text still at the prompt, send a bare `Enter` and re-check. Verify each line submitted before sending the next.

**Priming order: context FIRST, then skills (load-bearing).** A skill invocation is an action trigger, not a passive load. `/code-review` into an empty context makes the pane review whatever sits in the working tree immediately, burning cycles on the wrong artifact. So establish a standby frame BEFORE the skill commands. Pre-load via `tmux send-keys` (verifiable) by default; brief-time invocation is a fallback only when tmux is unavailable (unverifiable, races the pass).

Canonical sequence (fill `%PANE` / `<branch>` / `<scope>`; `/` for Claude, swap `$code-review`/`$code-hygiene` for Codex — `/compact` stays `/`):

```bash
tmux send-keys -t %PANE "Priming you with /code-review and /code-hygiene for an upcoming review of <branch> (<scope>). Await my brief over the bus; review nothing yet. When the brief arrives, proceed immediately without asking. No writes by you or any subagent; verify the tree is pristine before any verdict." Enter
sleep 2; tmux send-keys -t %PANE Enter                 # submit the standby line (first Enter often eaten)
sleep 1; tmux send-keys -t %PANE "/code-review" Enter   # queues behind standby, loads into the frame (no ad hoc pass)
sleep 1; tmux send-keys -t %PANE "/code-hygiene" Enter
sleep 2; tmux capture-pane -t %PANE -p | tail -5        # confirm all three landed; bare Enter if any sits at the prompt
```

The expiry clause ("proceed immediately when the brief arrives") is mandatory — without it a cautious pane stalls on a confirmation menu nobody is watching. The no-writes rule extends to any subagent the reviewer spawns: verify the tree is pristine before delivering a verdict.

**Compaction.** End every phase by recycling or compacting continuing panes (see Phase & Churn Control). Compaction is not instant: a nudge sent too soon races it, landing your brief before the pane compacts so the agent compacts the brief away. After `/compact`, confirm via `tmux capture-pane -t %NNN -p | tail -5` that compaction started or finished before the next brief; some runtimes never echo the `/compact` command itself, so look for compaction output or a fresh idle prompt, not the command. If you cannot check, `sleep 5`. Compaction also evicts skill priming, so re-prime any skill-dependent pane after compacting — context line first, then skills.

**Compaction is hygiene, not your budget.** Compact between phases and slices regardless of how much orchestrator context you have left. The continuing pane carries stale residue (the merged diff, intermediate test failures, the gate run, merge chatter) that raises the odds it conflates already-merged state with new work. The durable knowledge it needs (the shapes and decisions it just built) lives on merged main and in the spec, re-read cheaply. "My context looks fine" is never a reason to reuse an un-compacted pane.

## Phase & Churn Control

Phasing is the load-bearing orchestration skill. A phase must be large enough to justify spawn, briefing, and synthesis, but small enough that agents finish before their context turns stale.

Before dispatch, define the phase contract:

- **Goal**: one bounded outcome.
- **Inputs**: exact files, Linear IDs, PRs, specs, SHAs, or commands to read.
- **Outputs**: one artifact, verdict set, PR, decision batch, or scout report. When planning or implementing, the reuse map is a required output.
- **Done line**: exact single-sentence reply shape.
- **Gate**: how you will verify the phase yourself.
- **Closeout**: recycle or compact.

Right-size phases: combine mechanical siblings that share context, code path, gate, and reviewer; split on independent artifacts, unrelated modules, multiple repos, long diffs, long research inputs, or more than one fix-review loop. Do not phase every tiny edit (ceremony can cost more than the work). Do not run an open-ended mega-phase.

Close every phase with one:

1. **Recycle** (`warroom_kill` plus fresh spawn): default after heavy reads, long implementation, role changes, completed slices, or merges, and whenever an agent has drifted, a pane is noisy, or a pane is contaminated. A contaminated or drifted pane is recycled, never compacted forward — compaction is for a clean pane continuing into closely related work, not a way to salvage a bad one.
2. **Compact** continuing panes: only when the same agents continue into a tightly related next phase.

Never begin the next phase in a pane that was neither recycled nor compacted. Compact or recycle BEFORE the next brief, not after the agent has started the next slice — once the brief is in flight, `/compact` would evict it. Mechanics and the "hygiene, not budget" rule live in Priming & Compaction.

## Message Protocol

All dispatches use orchestrator-only replies:

```python
send_message(to=A, reply_to=ORCHESTRATOR, topic="{project}-{mode}", content=brief)
```

Use `;` recipients only for orchestrator fanout when the exact same brief applies to several agents; still set `reply_to` to the orchestrator.

Every brief must say:

> Reply to the orchestrator only, in one sentence. Keep to facts and evidence. Do not message other agents. Do not summarize unless asked. If this message does not ask for a reply, do not reply.

Prefer typed reply shapes:

- `done: <artifact|branch|PR> <evidence>`
- `blocked: <cause> <needed>`
- `review: clean <evidence>`
- `review: issue <severity> <path:line> <fact>`
- `signoff: I sign off on <X> as currently filed`
- `conditional: I sign off conditional on the following changes: <numbered facts>`

Large artifacts go to files you name and read. The bus is the signal, not the artifact. For no-reply notices, write `FYI no reply needed: <fact>`.

## Modes

Each mode instantiates one shared loop: **brief independently → agents re-read live state and reply one line to the orchestrator → orchestrator verifies from disk / `gh` / git → one focused correction round → re-verify deltas only → close (recycle or compact)**. Each mode below states only its deltas from this loop.

### Mode 1: Scout & Plan

Use before any spec or first slice whenever the work touches an area with existing code or infra. Skip only for genuine greenfield with no adjacent system. The scout's job is not to design the solution; it is to map what already exists so the plan reuses it instead of reinventing it.

Composition: one or two scouts on the area. Claude for large or cross-cutting areas (1m context); Codex for a focused backend module. Prime EACH scout with `/code-review` and `/code-hygiene` first (Priming & Compaction) — these are the disciplines the scout runs on: the reuse/simplification lens from `/code-review`, and the duplication / dead-code / boundary / sizing lenses (Health Signals) from `/code-hygiene`. Apply them EARLY, on the existing area, before any new code — not only at review time.

Required scout report, written to `~/.mdx/projects/{project}-scout-{area}.md` with one `done:` line, in this shape:

```markdown
## Reuse Map
- Reuse: <path> <symbol or command> <why>
- Existing infra: <path or tool> <how it will be used>
- Similar checked and rejected: <path> <reason it is wrong-shaped>
- None found: <searches run> <why new code is justified>

## Quality Map
- Duplication / parallel implementation: <file+symbol> <fact>
- Boundary / design issue: <file+symbol> <fact>
- Dead code / obsolete path: <file+symbol> <evidence>
- Grooming recommendation: refactor first | refactor during the slice | defer with reason

## Plan
- Decision needed: <question or none>
- Proposed steps bound to the reuse map: <ordered list>
- Tests and gates: <commands>
```

The Reuse Map is the guardrail against reinvention: for every capability the planned work needs, name the existing owner (`file path + symbol`, never line numbers) or state "none found" with the searches you ran — so "I did not find it" can never hide "I did not look." A plan that adds a new helper, type, table, runner, or command for a capability already listed in the Reuse Map is a defect.

**Surface-and-decide gate (REQUIRED).** After the report, surface the Reuse Map and Quality Map to the human or decision-maker and record ONE disposition per finding:

- **Reuse** — the plan binds to the existing code; no new implementation.
- **Deviate** — deliberately build new despite existing code, with a one-line reason (existing code is wrong-shaped, would couple, etc.). A deviation can be the right call; it must be a recorded decision, not a silent default.
- **Refactor first / during / defer** — groom the duplication or dead code before, alongside, or after the build, with a reason. Building on a bad base bakes in the debt.

Quality is the goal: code is continuously groomed as it evolves, so reshaping the area you touch is in scope, not scope creep. The spec or slice plan that follows MUST reflect these dispositions and carry the Reuse Map into its briefs.

### Mode 2: Spec Writing

Use when planning non-trivial implementation before Linear or code. Run AFTER Scout; the spec consumes the Reuse Map and dispositions.

1. Group work into natural spec units, each mapping to one future Linear sub-parent. Phase dependent specs after prerequisites; run independent specs in parallel.
2. Dispatch one engineer per spec plus one architect reviewer.
3. Engineers write `~/.mdx/projects/{project}-spec-{grouping}.md` and send one `done:` line. Each spec states required inputs, decisions already made, the Reuse Map and quality dispositions it binds to, exact output path and contents, completion line, and verification gate.
4. Architect reviews the named files against criteria → `review: clean` or `review: issue`.
5. One focused fix round per engineer; architect verifies deltas only. Cap spec review at one architect pass plus one correction round, then orchestrator spot-checks — never a third full round over citation mechanics.
6. When approved, file Linear per `helioy-tools:linear-workflows`. Consider Peer Consensus on the filed tree.

### Mode 3: Slice Build Loop

Use when an approved spec must land as small, PR-sized slices.

Composition: one engineer on the stronger build model plus one reviewer on the adversarial reader. Escalate the reviewer to Peer Consensus only for high-blast-radius slices: durability, identity, rekeying, deletion, migration, or commit seams.

Review weight scales with blast radius. A small mechanical PR (a few files, clear gate, no contract change) gets the orchestrator's own diff read plus the gate, not a queued adversarial pass — the reviewer pane existing is not a reason to use it. Reserve the full loop for slices that change contracts, persistence, identity, deletion, or cross-surface seams.

Per slice:

1. Confirm the slice carries a current Reuse Map; if not, run Scout before implementation.
2. Brief the engineer: numbered deliverables, spec section, Reuse Map, extraction or removal map, branch, tests, and done line `done: <branch> <sha> PR#<n>` or `blocked: <one sentence>`.
3. On `done:`, verify the PR yourself with `gh pr view N`; never trust the bus line alone.
4. Brief the reviewer for one adversarial pass against the PR. Prime with `/code-review` and `/code-hygiene` first (Priming & Compaction). Findings are Blocker, Major, or Minor with `file:line`.
5. Reviewer replies `review: clean <evidence>` or `review: issue <severity> <path:line> <fact>`.
6. One focused fix round; every fix needs failing-before and passing-after evidence where feasible.
7. Reviewer verifies deltas only.
8. Run `gh pr checks N`, `just ci`, or the repo gate against real services.
9. Surface only dual-clean, gate-green PRs to the human. The human holds the merge gate.

Deletion slices require a forward-removal map first: delete, keep, trim, and extracted reusable core. Respawn a fresh warroom per slice by default (fresh pair of eyes); compact only when the same agents continue into a tightly related next slice.

### Mode 4: Code Review

Use when implementation exists and needs verification against a spec, issue, or PR.

1. Run the baseline gate first (`cargo test`, `pnpm test`, the repo's `just ci`, etc.).
2. Default focus is functionality unless the user asked for full or security review; ask only when depth is unclear.
3. Dispatch reviewers in parallel, one per issue, PR, or coherent code area. Each dispatch names SPEC, CODE, the baseline ref, the Linear issue or PR, scope, focus, an explicit do-not-flag list, key checks, the no-writes boundary, and reply shape.
4. Prime each reviewer with `/code-review` and `/code-hygiene` before they read any diff (Priming & Compaction). Pin the baseline ref (Shared Practices).
5. Reviewers reply `review: clean` or `review: issue` to the orchestrator only.
6. Create follow-up work only for genuine findings; do not change sub-parent status for review findings.
7. Synthesize a concise table: area, reviewer, verdict, evidence, follow-up.

### Mode 5: Peer Consensus

Use after drafting a substantial artifact (Linear plan, spec, design doc, PR, or risky decision) and before treating it as final.

Default composition: the same agent prompt on Claude and Codex (model diversity). Variants in preference order: (1) same `helioy-tools:*` prompt on both runtimes; (2) cross-role same-runtime, such as `code-reviewer` plus `silent-failure-hunter`; (3) two same-runtime same-role panes, only when nothing better exists; (4) three panes for high-stakes tie-breaking.

Brief both agents independently — do not ask them to debate; the orchestrator synthesizes. The brief must include: the artifact under review (exact IDs, files, PRs, SHAs); the baseline ref; rules (concrete checklist plus relevant skill); discipline (find at least one substantive issue or positively justify none found); boundary (agents propose, orchestrator applies writes); reply shape; the sign-off strings (`I sign off on X as currently filed` / `I sign off conditional on the following changes:`); and an iteration bound (one critique round, one correction round, then sign off or escalate).

Accept only if both agents sign off on the same artifact shape. If either finds an issue, apply the agreed change or send one focused correction, then ask both to re-read live state and send a clean final sign-off. Persist the consensus with `cx_store` or `cx_deposit`. Escalate to the user if the agents disagree after two bounded rounds or if the fix would change scope.

### Mode 6: Brainstorm

Use when exploring a problem space and collecting diverse perspectives before deciding. Runs BEFORE Scout when the problem space itself is unsettled; once a direction is chosen, Scout audits the existing code for it.

1. Send the same problem statement in parallel, each agent's task tailored to its expertise; tell agents not to coordinate.
2. Each agent writes `~/.mdx/projects/{project}-{agent-role}--brainstorm.md` and sends one `done:` line.
3. Read the files, compare independent convergence, identify contradictions, present the synthesis.
4. Transition to Scout & Plan, Spec Writing, or direct execution.

## Why We Spend Tokens On Review

Peer review and adversarial passes cost real tokens. We spend them on purpose.

- **Cheap to catch, expensive to reverse.** A defect in a contract, persistence layer, identity or auth path, deletion, or cross-surface seam is cheap to catch before merge and costly to unwind after. A bad migration or a leaked boundary can cost far more than the review that would have caught it.
- **Diversity sees what one pass cannot.** One pass sees what one model or role primes it to see. A second independent pass on a different runtime or role catches the class the first was blind to. This is why Peer Consensus prefers model diversity.
- **Weight scales with stakes.** Review weight scales with blast radius (Slice Build Loop): a one-line mechanical change earns the orchestrator's own diff read, while a contract change earns the full adversarial loop.

Leanness applies to prose and structure. It never applies to this discipline.

## Shared Practices

- Use `tmux capture-pane -t %NNN -p` to check progress without messaging agents (also detects rabbit-holing).
- Specs and docs cite symbols, never `file:line`. Line numbers rot with every commit; `path + symbol` (`run_routes.py _http_error_from_manager`) survives and is greppable. Brief spec writers to express traceability as field → file+symbol, and brief reviewers to flag line anchors as findings. Bus review verdicts still use `path:line` for code findings; those are read once against a named sha, not stored.
- Pin the baseline for citation checks. A spec or code review that verifies references must name the ref it checks against (`git show main:path`, never the bare working tree — the shared checkout often sits on an open PR branch, and the wrong ref produces confidently false findings). Return the checkout to baseline after gating a PR, before any unrelated review.
- The bus is not the artifact: read artifact files after completion. Write a review file ONLY when you will read it to drive fixes; a clean or short verdict rides the bus.
- Store durable outcomes (a decision, lesson, consensus result, or reusable pattern) with `cx_store` or `cx_deposit`.

## Anti-Patterns

| Do NOT | Instead |
|--------|---------|
| Build before scouting the area | Run Scout & Plan first; bind the plan to the Reuse Map. |
| Add a new helper, type, table, runner, or command for a capability that already exists | The Reuse Map names the existing owner; deviate only as a recorded decision. |
| Plan from a blank page | Scout existing code, then write the Reuse Map before planning. |
| Hide scout findings inside implementation | Surface reuse, duplication, dead code, bad design, and deviation decisions before code. |
| Invoke `/code-review` into an empty pane | Standby/context line first, THEN skills (Priming & Compaction). |
| Use background subagents for warroom work | Spawn tmux agents that receive bus nudges and iterate. |
| Wire `reply_to` between agents by default | Route all replies to the orchestrator and synthesize there. |
| Run peer debate on the bus | Collect independent verdicts, then one focused correction or final sign-off. |
| Send long prose, diffs, or logs over the bus | One sentence with IDs, paths, SHAs, tests, `file:line`. |
| Reply to FYI or no-reply messages | Do not reply unless the message asks for one or blocks progress. |
| Start the next phase or slice in a stale pane | Compact (confirm via capture-pane) or recycle first, regardless of your own budget. |
| Trust a `done`, `green`, `clean`, or `merged` bus line | Verify from disk, `gh`, git, Linear, logs, or tests. |
| Run a full adversarial loop on a mechanical PR | Scale review weight to blast radius. |
| Reuse agent IDs after add or remove | Run `warroom_status` and use the fresh IDs. |
| Ship fix rounds without tests | Pair fixes with failing-before and passing-after evidence where feasible. |
| Use same-runtime same-role agreement as strong signal | Prefer mixed runtime MoE or cross-role diversity. |
| Let agents apply authoritative artifact changes during consensus | Agents propose; orchestrator applies and verifies. |
