---
title: Warroom skill groom — leaner/cleaner/meaner + scout-first
type: proposal
tags: [warroom, orchestration, skill-groom, scout, reuse, code-review, code-hygiene]
summary: Consolidate the warroom skill's repeated priming/compaction choreography into one reference, add a first-class Scout & Plan mode that produces a required reuse map and surfaces duplication/dead-code for a deviate/refactor decision, and state why review tokens are spent.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-22
updated: 2026-06-22
---

# Warroom skill groom proposal

Headline approach: **collapse the duplicated tmux priming/compaction choreography into one `Priming & Compaction` reference, and promote SCOUT to the first beat of an explicit Scout → Build → Review spine — a first-class mode whose required output is a reuse map plus a surfaced duplication/dead-code report that forces a reuse / deviate / refactor decision before any code is written.**

---

## 1. Diagnosis

The current `SKILL.md` is 319 lines. It is correct and battle-tested, but two problems dominate.

### A. Bloat is concentrated in one place: priming + compaction mechanics

The same tmux choreography is restated 4–5 times across the doc:

| Idea | Where it repeats |
|---|---|
| `/` vs `$` prefix rule, `$compact` is a no-op | Non-Negotiables (L58) **and** Phase Control (L112) |
| Swallowed-Enter / send a bare `Enter` to resubmit | L112, L114, L232, L236, L242–248 |
| Context-first-THEN-skills priming order + canonical send-keys block | Mode 3 step 5 (L232–248, ~17 lines), referenced again in Mode 5 step 3 (L280) |
| Re-prime skills after compaction (priming is evicted) | L114, L124, L236 |
| "Compaction is hygiene, not your budget" | Dedicated subsection L118–128, Mode 5 step 9 (L286), Anti-pattern row (L310) |
| "Recycle or compact before the next phase" | Closing step of **every** mode (L199, L218, L252, L266, L286) + Non-Negotiable L57 + its own section + anti-pattern L309 |

This is the single biggest signal-to-noise drag. The keystroke detail is load-bearing and must survive, but it belongs in exactly one home that every mode points to.

Secondary prose bloat:

- Each mode re-derives the same loop (brief → independent work → verify from disk → one correction round → re-verify deltas → close). The shared skeleton can be stated once; modes describe only their deltas.
- "Reply to the orchestrator only" is a Non-Negotiable yet is re-stated inside most mode flows.

### B. The scout/plan phase does not exist as a first-class step

The intended flow is **scout/plan → implement → review**, but today:

- The mode taxonomy has no Scout. `First Decision` routes "planning before implementation" straight to **Spec Writing**, which already assumes you know the solution shape.
- There is **no required reuse map**, so a plan can silently reinvent infrastructure that already exists. This is exactly the failure this week: an engineer hand-wrote a table list when the migration runner already produced a migrated DB.
- `/code-review` and `/code-hygiene` are invoked only at **review time** (Mode 3, Mode 5). Their reuse / duplication / dead-code / boundary lenses arrive *after* the code is written — too late to prevent reinvention. They should run during scout, on the existing area, before any new code.
- There is **no surface-and-decide gate**: even if duplication or a better path were found, nothing defines the moment where the orchestrator/human chooses to reuse, deviate deliberately, or refactor first. A deviation can be the right call, but it must be a recorded decision, not a silent default.

### C. The WHY of peer review is implicit

The doc mandates peer consensus and adversarial passes but never states plainly why the extra tokens are justified. Given Stuart's repeated token-economy steers, the discipline reads as cost without a stated payoff. Leanness work risks eroding it unless the rationale is on the page.

---

## 2. Proposed structure

Lifecycle-ordered, with the duplication pulled into one reference. New or substantially changed sections marked **[NEW]** / **[CHANGED]**.

```
1.  Role
2.  The Spine: Scout → Build → Review          [NEW]   — names the three beats, scout first
3.  First Decision                              [CHANGED] — add Scout row; keep do-not-spawn logic
4.  Agents                                      (unchanged — already lean)
5.  Non-Negotiables                             [CHANGED] — add "scout before you build"; point compaction/prefix detail to §7
6.  Priming & Compaction                        [NEW]   — THE one home for prefix rule, swallowed-Enter,
                                                          context-first priming, canonical send-keys, re-prime,
                                                          "hygiene not budget". Everything else references this.
7.  Phase & Churn Control                       [CHANGED] — keep phase contract + right-sizing + recycle/compact
                                                          decision; move keystroke mechanics to §6
8.  Message Protocol                            [CHANGED] — trim; the shared reply rules live here once
9.  Modes (shared loop stated once, then deltas):
      Mode 1: Scout & Plan                      [NEW]
      Mode 2: Spec Writing                      [CHANGED] — consumes the reuse map
      Mode 3: Slice Build Loop                  [CHANGED] — keep blast-radius scaling + deletion map
      Mode 4: Code Review                       [CHANGED] — priming points to §6
      Mode 5: Peer Consensus                    [CHANGED]
      Mode 6: Brainstorm                        [CHANGED] — precedes Scout when the space is open
10. Why We Spend Tokens On Review               [NEW]
11. Shared Practices                            [CHANGED] — keep symbols-not-file:line, pin baseline, review-file-only-when-read
12. Anti-Patterns                               [CHANGED] — drop rows now covered once; add scout/reuse rows
```

Net effect: one new mode + one new reference + one new rationale section, yet the doc gets **shorter** (~250 lines vs 319) because the priming/compaction duplication collapses from ~5 sites to 1.

---

## 3. Revised `SKILL.md` (full draft, ready to drop in)

~~~markdown
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

Agents research, review, draft, and implement. You own scope, evidence, context hygiene, and final judgment.

## The Spine: Scout → Build → Review

Every build runs three beats, in order:

1. **Scout** — audit the existing code and infra in the area you are about to touch, *before* designing anything. Produce a reuse map and surface duplication, dead code, and design risks. Skipping scout bakes in reinvention. (Real failure: an engineer hand-wrote a table list when the migration runner already produced a migrated DB.)
2. **Build** — spec and implement against the reuse map, in PR-sized slices.
3. **Review** — verify against the spec, issue, or PR, with review weight scaled to blast radius.

Scout is the first beat, not optional polish. The modes below instantiate these beats.

## First Decision

Do not spawn a warroom when ALL of these hold:

- The change is mechanically locked: one to three lines, one obvious implementation, no open design choice.
- The design is already adjudicated by a spec, prior review, or earlier item in the same batch.
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

## Agents

Choose runtime by task shape:

| Runtime | Context | Best For |
|---------|---------|----------|
| Claude | 1m context window | UI work, design synthesis, broad research, long specs, or any task where large context is the main constraint. |
| Codex | 250k context window | Backend work, implementation, tests, refactors, and codebase changes where code execution and patch quality dominate. |

For MoE, use both when the artifact benefits from model diversity. For focused execution, pick the runtime that fits the work instead of defaulting to mixed panes.

## Non-Negotiables

- Run `whoami` first. Use that agent_id as `reply_to` in every dispatch.
- Run `warroom_status` after any membership change (spawn, add, remove, recycle). Never reuse agent IDs after add or remove; panes renumber and bus IDs churn. Use `pane_id` (`%NNN`) for `tmux capture-pane` and `/compact` — it survives renumbering.
- Route replies to the orchestrator only. Do not wire agent-to-agent `reply_to` by default.
- Bus messages are single-sentence factual signals. Cite IDs, paths, SHAs, PRs, test names, and `file:line` evidence. If a message does not request a reply, do not reply.
- Bus pings wake you; they are not truth. Confirm `done`, `green`, `merged`, and `clean` from disk, `gh`, git, Linear, logs, or test output. Re-read live state before each verdict; memory-only consensus is false consensus.
- **Scout before you build.** Any work touching existing code starts with a Scout & Plan pass and a reuse map. A plan that introduces a new helper, type, table, runner, or command for a capability the reuse map already lists is a defect.
- Every completed phase and every merged slice is a hard boundary: compact (confirm via `capture-pane`) or recycle the continuing pane BEFORE the next brief. Re-briefing a stale pane is a defect, not an optimization. See Priming & Compaction.

## Setup

Use the `helioy-warroom` MCP tools.

```python
warroom_discover(query="security review")
warroom_discover(namespace="helioy-tools")

warroom_spawn(name="design", agents=["brand-guardian", "ui-designer"])

# MoE: same prompt, one pane per runtime.
warroom_spawn(name="moe", agents=["helioy-tools:codebase-analyst"])
warroom_add(name="moe", agent="helioy-tools:codebase-analyst", runtime="codex")

warroom_status(name="design")
warroom_kill(name="design")
```

- Qualified names (`<namespace>:<agent>`) select the namespace prompt; `runtime` controls the adapter.
- Passing the same plugin-qualified agent twice does not create MoE; both panes use the default adapter. Spawn once, then `warroom_add` the second pane with `runtime="codex"`.
- Named warrooms are idempotent; spawning the same name kills the old one first.
- Prefer a clean upfront spawn. If membership changes mid-build, call `warroom_status` and address only the fresh IDs.
- If MCP tools are unavailable, fall back to `~/.helioy/warroom.sh <name> "type1 type2 ..."`.

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

**Compaction.** End every phase by recycling or compacting continuing panes (see Phase & Churn Control). Compaction is not instant: a nudge sent too soon races it, landing your brief before the pane compacts so the agent compacts the brief away. After `/compact`, confirm via `tmux capture-pane -t %NNN -p | tail -5` that compaction started or finished before the next brief; if you cannot check, `sleep 5`. Compaction also evicts skill priming, so re-prime any skill-dependent pane after compacting — context line first, then skills.

**Compaction is hygiene, not your budget.** Compact between phases and slices regardless of how much orchestrator context you have left. The continuing pane carries stale residue (the merged diff, intermediate test failures, the gate run, merge chatter) that raises the odds it conflates already-merged state with new work. The durable knowledge it needs (the shapes and decisions it just built) lives on merged main and in the spec, re-read cheaply. "My context looks fine" is never a reason to reuse an un-compacted pane.

## Phase & Churn Control

Phasing is the load-bearing orchestration skill. A phase must be large enough to justify spawn, briefing, and synthesis, but small enough that agents finish before their context turns stale.

Before dispatch, define the phase contract:

- **Goal**: one bounded outcome.
- **Inputs**: exact files, Linear IDs, PRs, specs, or commands to read.
- **Outputs**: one artifact, verdict set, PR, or decision batch.
- **Done line**: exact single-sentence reply shape.
- **Gate**: how you will verify the phase yourself.
- **Closeout**: recycle or compact.

Right-size phases: combine mechanical siblings that share context, code path, gate, and reviewer; split on independent artifacts, unrelated modules, multiple repos, long diffs, long research inputs, or more than one fix-review loop. Do not phase every tiny edit (ceremony can cost more than the work). Do not run an open-ended mega-phase.

Close every phase with one:

1. **Recycle** (`warroom_kill` plus fresh spawn): default after heavy reads, long implementation, role changes, completed slices, or merges.
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

Large artifacts go to files you name and read. For no-reply notices, write `FYI no reply needed: <fact>`.

## Modes

Each mode instantiates one shared loop: **brief independently → agents re-read live state and reply one line to the orchestrator → orchestrator verifies from disk / `gh` / git → one focused correction round → re-verify deltas only → close (recycle or compact)**. Each mode below states only its deltas from this loop.

### Mode 1: Scout & Plan

Use before any spec or first slice, whenever the work touches an area with existing code or infra. Skip only for genuine greenfield with no adjacent system. The scout's job is not to design the solution; it is to map what already exists so the plan reuses it instead of reinventing it.

Composition: one or two scouts on the area. Claude for large or cross-cutting areas (1m context); Codex for a focused backend module. Prime EACH scout with `/code-review` and `/code-hygiene` first (Priming & Compaction) — these are the disciplines the scout runs on: the reuse lens from `/code-review` (reuse, simplification, efficiency), the duplication / dead-code / boundary lenses from `/code-hygiene` (Health Signals: duplicate blocks, parallel implementations, dead code, layer crossings, oversized files/functions).

Required scout report, written to `~/.mdx/projects/{project}-scout-{area}.md` with one `done:` line:

1. **Reuse map (REQUIRED).** For every capability the planned work needs, name the existing symbol, module, command, or infra that already provides it (`file path + symbol`, never line numbers), or state "no existing owner found" explicitly. The plan MUST consume this map. A plan that adds a new helper, type, table, runner, or command for a capability already listed here is a defect. This is the guardrail against reinvention.
2. **Duplication & dead-code findings.** Apply `/code-hygiene` Health Signals to the touched area: duplicate blocks, parallel or unfinished migrations, dead code, boolean soup, layer crossings, oversized files or functions. Report each as `area: signal → file+symbol → suggested remedy`.
3. **Design risks.** Bad design or boundary problems the new work would inherit or worsen.

Surface-and-decide gate (REQUIRED). After the report, the orchestrator surfaces the reuse map and findings to the human or decision-maker and records ONE disposition per finding:

- **Reuse** — the plan binds to the existing code; no new implementation.
- **Deviate** — deliberately build new despite existing code, with a one-line reason (existing code is wrong-shaped, would couple, etc.). A deviation can be the right call; it must be a recorded decision, not a silent default.
- **Refactor first** — groom the duplication or dead code as its own `/code-hygiene` slice before building on it, because building on a bad base bakes in the debt.

Quality is the goal: code is continuously groomed as it evolves, so reshaping the area you touch is in scope, not scope creep. The spec or slice plan that follows must reflect these dispositions and carry the reuse map into its briefs.

### Mode 2: Spec Writing

Use when planning non-trivial implementation before Linear or code. Run AFTER Scout; the spec consumes the reuse map and dispositions.

1. Group work into natural spec units, each mapping to one future Linear sub-parent. Phase dependent specs after prerequisites; run independent specs in parallel.
2. Dispatch one engineer per spec plus one architect reviewer.
3. Engineers write `~/.mdx/projects/{project}-spec-{grouping}.md` and send one `done:` line. Each spec states required inputs, decisions already made, the reuse map it binds to, exact output path and contents, completion line, and verification gate.
4. Architect reviews the named files against criteria → `review: clean` or `review: issue`.
5. One focused fix round per engineer; architect verifies deltas only.
6. When approved, file Linear per `helioy-tools:linear-workflows`. Consider Peer Consensus on the filed tree.

### Mode 3: Slice Build Loop

Use when an approved spec must land as small, PR-sized slices.

Composition: one engineer on the stronger build model plus one reviewer on the adversarial reader. Escalate the reviewer to Peer Consensus only for high-blast-radius slices: durability, identity, rekeying, deletion, migration, or commit seams.

Review weight scales with blast radius. A small mechanical PR (a few files, clear gate, no contract change) gets the orchestrator's own diff read plus the gate, not a queued adversarial pass — the reviewer pane existing is not a reason to use it. Reserve the full loop for slices that change contracts, persistence, identity, deletion, or cross-surface seams.

Per slice:

1. Brief the engineer: numbered deliverables, spec section, reuse map, extraction or removal map, branch, tests, and done line `done: <branch> <sha> PR#<n>` or `blocked: <one sentence>`.
2. On `done:`, verify the PR yourself with `gh pr view N`; never trust the bus line alone.
3. Brief the reviewer for one adversarial pass against the PR. Prime with `/code-review` and `/code-hygiene` first (Priming & Compaction). Findings are Blocker, Major, or Minor with `file:line`.
4. Reviewer replies `review: clean <evidence>` or `review: issue <severity> <path:line> <fact>`.
5. One focused fix round; every fix needs failing-before and passing-after evidence where feasible.
6. Reviewer verifies deltas only.
7. Run `gh pr checks N`, `just ci`, or the repo gate against real services.
8. Surface only dual-clean, gate-green PRs to the human. The human holds the merge gate.

Deletion slices require a forward-removal map first: delete, keep, trim, and extracted reusable core. Respawn a fresh warroom per slice by default (fresh pair of eyes); compact only when the same agents continue into a tightly related next slice.

### Mode 4: Code Review

Use when implementation exists and needs verification against a spec, issue, or PR.

1. Run the baseline gate first (`cargo test`, `pnpm test`, the repo's `just ci`, etc.).
2. Default focus is functionality unless the user asked for full or security review; ask only when depth is unclear.
3. Dispatch reviewers in parallel, one per issue, PR, or coherent code area. Each dispatch names SPEC, CODE, the Linear issue or PR, scope, focus, an explicit do-not-flag list, key checks, and reply shape.
4. Prime each reviewer with `/code-review` and `/code-hygiene` before they read any diff (Priming & Compaction). Pin the baseline ref (Shared Practices).
5. Reviewers reply `review: clean` or `review: issue` to the orchestrator only.
6. Create follow-up work only for genuine findings; do not change sub-parent status for review findings.
7. Synthesize a concise table: area, reviewer, verdict, evidence, follow-up.

### Mode 5: Peer Consensus

Use after drafting a substantial artifact (Linear plan, spec, design doc, PR, or risky decision) and before treating it as final.

Default composition: the same agent prompt on Claude and Codex (model diversity). Variants in preference order: (1) same `helioy-tools:*` prompt on both runtimes; (2) cross-role same-runtime, such as `code-reviewer` plus `silent-failure-hunter`; (3) two same-runtime same-role panes, only when nothing better exists; (4) three panes for high-stakes tie-breaking.

Brief both agents independently — do not ask them to debate; the orchestrator synthesizes. The brief must include: the artifact under review (exact IDs, files, PRs, SHAs); rules (concrete checklist plus relevant skill); discipline (find at least one substantive issue or positively justify none found); boundary (agents propose, orchestrator applies writes); reply shape; the sign-off strings (`I sign off on X as currently filed` / `I sign off conditional on the following changes:`); and an iteration bound (one critique round, one correction round, then sign off or escalate).

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
| Build before scouting the area | Run Scout & Plan first; bind the plan to the reuse map. |
| Add a new helper, type, table, or command for a capability that already exists | The reuse map names the existing owner; deviate only as a recorded decision. |
| Invoke `/code-review` into an empty pane | Standby/context line first, THEN skills (Priming & Compaction). |
| Use background subagents for warroom work | Spawn tmux agents that receive bus nudges and iterate. |
| Wire `reply_to` between agents by default | Route all replies to the orchestrator and synthesize there. |
| Run peer debate on the bus | Collect independent verdicts, then one focused correction or final sign-off. |
| Send long prose, diffs, or logs over the bus | One sentence with IDs, paths, SHAs, tests, `file:line`. |
| Start the next phase or slice in a stale pane | Compact (confirm via capture-pane) or recycle first, regardless of your own budget. |
| Trust a `done`, `green`, `clean`, or `merged` bus line | Verify from disk, `gh`, git, Linear, logs, or tests. |
| Run a full adversarial loop on a mechanical PR | Scale review weight to blast radius. |
| Reuse agent IDs after add or remove | Run `warroom_status` and use the fresh IDs. |
| Let agents apply authoritative artifact changes during consensus | Agents propose; orchestrator applies and verifies. |
~~~

---

## 4. What changed and why (for the orchestrator's review)

- **SCOUT is now first-class** (`The Spine`, Non-Negotiable "scout before you build", Mode 1, two anti-pattern rows). The reuse map is a REQUIRED, reviewable output, so a plan cannot silently reinvent. The surface-and-decide gate makes reuse / deviate / refactor an explicit recorded decision — a deliberate deviation stays available as the right call.
- **`/code-review` and `/code-hygiene` are pulled EARLY** into scout, referenced as the discipline (their Health Signals and reuse lenses), not duplicated. They still anchor review time in Modes 3–4.
- **Quality rigor preserved and justified** (`Why We Spend Tokens On Review`). Blast-radius scaling, model-diverse peer consensus, pin-the-baseline, symbols-not-file:line, and the fix-with-tests rule all survive intact.
- **Leanness from de-duplication, not from cutting discipline.** The priming/compaction choreography collapses from ~5 sites to one `Priming & Compaction` reference; the per-mode "recycle or compact" tail and the repeated "reply to orchestrator only" are stated once. The result is ~250 lines vs 319 while adding a whole new mode plus a rationale section.

## 5. Open questions for the orchestrator

1. **Scout report file vs bus-only.** I made the scout report a written file (`{project}-scout-{area}.md`) because the reuse map and dispositions feed downstream briefs and merit a read. If you want to honor "write a file only when the orchestrator will read it," the rule already fits (you WILL read it), but confirm you want it filed rather than bus-summarized for tiny areas.
2. **Mode numbering.** I reordered to lifecycle order (Scout → Spec → Slice → Review → Consensus → Brainstorm). If downstream docs or muscle memory reference the old numbers (Peer Consensus = Mode 1), keep the old numbering and just insert Scout as Mode 0/6 instead.
