---
title: MoE Local Batch
type: workflow
status: stable
inaugurated: 2026-05-22
---

# MoE Local Batch

Mixture-of-experts orchestration for a known list of small, independent code changes that land on one branch as N commits and ship as one PR. Codex implements; Claude reviews. Orchestrator (you, on Claude) drives.

## When to use

- You have a named list of N changes (typically 3-10) you can describe up front.
- Each item is 5-30 minutes of code work, bounded scope, no Linear ticket.
- Changes are independent or naturally ordered; later items don't change earlier scope.
- Single repo, single branch.
- Quality matters per-item (you want peer review on each), but the items are too small to be worth Nancy/Linear overhead.

**Fits:** refactors, bug-batch fixes, lint passes, dead-code removal, test-gap fills, naming consistency cleanup, dependency bumps with light migration, profile-driven micro-optimizations.

**Does not fit:** single one-off changes (warroom overhead too high), Nancy/Linear-tracked work (different orchestration), cross-repo work (warroom is single-cwd), brainstorm/spec-writing (use those modes instead), text-only artifacts (use peer-consensus instead).

## Shape

```
Phase 0  Identify N items
─────────────────────────
  Codebase review, profiler run, lint output, or hand-curated list.
  Each item: target file/symbol, scope, acceptance criteria.

For each item i in 1..N:
─────────────────────────
  warroom_spawn(codex backend-engineer + claude engineering-code-reviewer)
  brief engineer: target, constraints, mail discipline, sign-off phrase
  brief reviewer: artifact, what to check, sign-off phrase, adversarial discipline

  engineer  → Phase A design sketch        → mail orchestrator
  reviewer  → Phase A sign-off OR block    → mail orchestrator
  engineer  → implement + commit + tests   → mail orchestrator with SHA
  reviewer  → Phase B implementation review → sign-off OR block
  engineer  → push to origin (same branch) → mail closure

  warroom_kill

Phase F  Open single PR
────────────────────────
  gh pr create against main with all N commits visible in the diff.
```

## Step detail

### Phase 0 — identify items

Output is a named list with enough specificity that you can write each item's brief in 5 minutes. For each item record: target path, current shape, desired shape, behaviour-preservation constraint, sign-off phrase suffix (e.g. "ServerState split", "CLI verb split").

### Per-item loop

1. **Spawn fresh warroom.** `warroom_spawn` + `warroom_add`. Engineer on codex, reviewer on claude. Two distinct models = the mixture of experts. Fresh contexts every item.
2. **Brief both panes in parallel.** Engineer brief includes target, constraints, exact sign-off phrase, mail discipline. Reviewer brief includes what to check, adversarial discipline, common defect list, exact sign-off phrase.
3. **Phase A — design.** Engineer posts the design (file layout, symbol partition, blast radius) before moving code. Reviewer signs off design with the phrase `"I sign off on the proposed X as filed"` or blocks with a substantive issue.
4. **Phase B — implementation.** Engineer commits, mails SHA. Reviewer reads `git diff <SHA>~..<SHA>` and signs off with `"I sign off on the X as currently filed"` or blocks.
5. **Push.** Engineer pushes after sign-off, mails closure with SHA.
6. **Tear down.** Orchestrator `warroom_kill`, then `warroom_spawn` for item i+1.

### Phase F — PR

After item N closes and pushes, orchestrator opens one PR with all commits visible. Body lists each commit, the load-bearing decisions, the test verification, and the process note (one warroom per item, two-phase sign-off).

## Load-bearing decisions

These are the choices that make the workflow work. Skip any one and the pattern degrades.

### One branch, N commits — declared up front

The user (or orchestrator) commits to the single-branch shape before item 1 starts. Without this, each item drifts into "should this be its own branch?" decisions. Naming convention: `refactor/<scope>-cleanup`, `fix/<scope>-batch`, `chore/<scope>-pass`.

### Fresh warroom per item

The respawn between items is the load-bearing piece. Two reasons:

- **Context decay is the point.** Each new pair reads `git log main..HEAD` and the current file state cold. Carried context anchors agents to earlier decisions and prior code shapes. Fresh contexts catch defects that stale context would rationalize away.
- **Cheap.** Spawn/kill is seconds. The cost is far less than the cost of one bad commit slipping through.

Exception: multi-round iteration on the *same* item (Phase A → blocker → resolution → Phase A sign-off → Phase B → blocker → fix → Phase B sign-off) stays in the same warroom. Respawn fires on item boundaries, not iteration boundaries.

### Two-phase sign-off

Phase A (design) before Phase B (implementation) catches misclassifications before code is written. Worked example: in refactor 4 (docker_runtime split), the reviewer caught that `is_executable` and `docker_command` were classified as "pure" but read filesystem and PATH. Phase A blocked, engineer corrected the partition, then code went in clean. If Phase A had been skipped, the engineer would have moved them, the reviewer would have flagged it post-commit, and the engineer would have rewritten the commit.

Exact sign-off phrases matter:
- `"I sign off on the proposed X as filed"` — Phase A clean
- `"I sign off on the X as currently filed"` — Phase B clean
- `"Substantive issue blocking sign-off: <one line>"` — block at either phase

The phrases are parseable consensus signal. Free-form agreement is ambiguous.

### Engineer-led push after sign-off

Orchestrator does **not** gate the push. After Phase B clean, engineer pushes the commit and mails closure. Orchestrator's only role at that point is to acknowledge and start the next item. Gating the push adds latency and serializes through the orchestrator's attention.

### Brief constraints are negotiable mid-flight

When a brief constraint conflicts with reality, the engineer escalates to the orchestrator, who relaxes or clarifies. Worked example: in refactor 6 (lifecycle codec split), the brief required both files <300 LOC. Engineer realised the SQL store API alone was intrinsically >300 LOC; further reduction would be a separate refactor. Engineer raised it. Orchestrator relaxed to CLAUDE.md's 700 LOC hard ceiling. Phase A proceeded.

The principle: briefs are the orchestrator's best guess, not contracts. Engineers and reviewers push back on constraints that conflict with the artifact's structure.

### Mail discipline replaces CC

helioy-bus has no CC primitive. Instead, agents send a separate terse `send_message` to the orchestrator at each milestone (design sent, SHA committed, Phase A signed off, Phase B signed off, push complete). Without this, the orchestrator has to capture panes to know status — slow, noisy, and burns the orchestrator's context.

Briefs must say this explicitly: "After every milestone, send a terse mail to `<orchestrator-address>`."

### Orchestrator address must be registered

The orchestrator must `register_agent` on the bus before briefing. Otherwise resolved-but-unregistered addresses can drop messages or land in the wrong inbox. Verify with `list_agents` before sending briefs; `whoami` is unreliable.

## Anti-patterns

| Don't | Instead |
|-------|---------|
| Reuse the warroom across items | Kill + respawn between items for fresh-eyes |
| Skip Phase A and let engineer commit before design review | Two-phase sign-off catches partitioning errors cheaply |
| Use free-form sign-off ("looks good") | Exact phrases are parseable; "looks good" isn't |
| Make the orchestrator push commits | Engineer pushes after sign-off; orchestrator stays out of the critical path |
| Treat brief constraints as inviolable | Engineer escalates when reality conflicts; orchestrator adjusts |
| CC the orchestrator via reply_to | No CC primitive on the bus; mail discipline replaces it |
| Open a PR per item | One PR with all N commits — that's the point of the workflow |
| Run two same-runtime panes | Two different models is the mixture; same-runtime is degenerate |
| Bundle items with dependencies | If item B reads state from item A, they aren't independent — either order them strictly or merge into one item |

## Worked example: runtime-matters refactor session, 2026-05-22

Six refactors identified in a codebase review of `littleorgans/runtime-matters`. Branch `refactor/post-review-cleanup`, PR #47.

| # | Commit | Refactor |
|---|--------|----------|
| 1 | `70f7ed6` | Split `ServerState` god object along mutex boundaries (545 LOC → 5 coordinators) |
| 2 | `7060844` | Split `crates/rtm-cli/src/cli/mod.rs` into per-verb files (498 LOC → 8 files) |
| 3 | `5f06577` | Rename daemon-internal `EventBatch` to resolve wire-type collision |
| 4 | `e8e3a67` | Split `docker_runtime.rs` into pure argv module + effectful CLI runtime |
| 5 | `1332b86` | Extract `reconcile.rs` inline tests to sibling file (precedent from `spawn_preflight`) |
| 6 | `92614e4` | Split `lifecycle.rs` SQL store from row codec (530 LOC → 363 + 180) |

Total: 6 commits, 6 fresh warrooms, all 249 tests green at every step, one PR. ~75 minutes wall clock.

Defects caught by the workflow that would have shipped without it:

- Refactor 4 Phase A: reviewer flagged `is_executable` and `docker_command` as filesystem/env reads misclassified as pure.
- Refactor 6 Phase A: reviewer flagged the orchestrator's <300 LOC constraint as in conflict with the intrinsic SQL surface size; engineer escalated; orchestrator relaxed.

Process notes for future runs:

- The first warroom missed the orchestrator's correct mail address because I (orchestrator) hadn't registered on the bus. Fix: `register_agent` before briefing item 1.
- Engineer self-pushing after sign-off worked well and was strictly faster than orchestrator-gated pushes.
- The "fresh-eyes per item" pattern caught one Phase A defect that experienced same-pane engineering would have missed.
