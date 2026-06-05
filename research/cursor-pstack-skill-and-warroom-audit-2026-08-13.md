---
title: Cursor pstack Skill and Warroom Audit
type: research
tags: [cursor, pstack, skills, claude-code, codex, warroom, helioy-bus, orchestration]
summary: Pinned audit of pstack 0.14.0, its 44 skills and orchestration system, with a selective adoption plan for Helioy warroom.
status: active
source: multi-agent-audit
confidence: high
created: 2026-08-13
updated: 2026-08-13
---

# Cursor pstack Skill and Warroom Audit

## Experiment decision and implementation update

The selective adoption recommendation below records the initial audit. Stuart subsequently chose a full pstack experiment and clarified the governing interpretation:

> A substantial part of pstack's principle layer improves Helioy's AGENTS rules.

That correction is supported by the audit evidence. Helioy's rules already state simplicity, verification, root cause fixing, DRY, file limits, and autonomous bug fixing. Pstack adds operational procedures that make those principles more executable: proof ladders, caller first design, design space exploration, explicit migration and deletion order, context guarding, idempotency, boundary discipline, and verifiable sequencing.

The experiment is implemented as a distinct `helioy-pstack` plugin in the Helioy marketplace. This keeps provenance, update cadence, and removal independent from `helioy-tools` while making it part of the same plugin repository and distribution surface.

### Experiment contents

- Pinned upstream: Cursor plugins commit `6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa`, pstack 0.14.0.
- Full surface: 44 skills, 2 agents, 23 Poteto Mode playbooks, Benny automation, documentation, and verification scripts.
- Dual manifests: Claude Code and Codex plugin metadata.
- Attribution: upstream README notice, `UPSTREAM.md`, MIT license, Lauren Tan authorship.
- Compatibility: shared project skills use `.agents/skills`; transcript recall uses Transport Matters; model preferences use `~/.config/helioy/pstack-models.md`.
- Runtime ownership: pstack owns the method and playbooks. `helioy-warroom` owns member lifecycle. `helioy-bus` owns communication and completion events.

### Orchestration mapping used by the experiment

| Pstack concept | Helioy execution |
|---|---|
| Arena | Bakeoff: parallel warroom candidates plus an independent judge |
| Swarm | Coverage: disjoint warroom slices plus coordinator synthesis |
| Orchestrate | Program mode: Frame, Install, Pilot, Scale, Drain, Land, Close over warroom and bus |
| Cursor Task fields | Dispatch contract: task, scope, evidence, output schema, completion event |
| Task completion | Typed bus reply correlated to the dispatched unit |
| Session transcript scan | `transcript-search` scoped to the active workspace |

The adapter deliberately avoids a second agent registry, message transport, or lifecycle implementation. The upstream orchestration store remains available during the experiment as a durable program fact store. Live execution remains with the existing Helioy owners.

### AGENTS rule improvements adopted

The canonical runtime catalog AGENTS source now adds:

- a four rung proof ladder from build and typecheck through real feature and integration proof;
- caller first design and explicit migration and deletion plans;
- deterministic reproduction before autonomous bug fixes;
- caller inventories and removal conditions for temporary adapters;
- domain modeling, boundary discipline, idempotency, shared state separation, reader load, verifiable sequencing, earned automation, structural learning, and context guarding.

These additions strengthen the existing rules. They do not replace Stuart's ownership of what and why, the repository thresholds, or the zero tolerance DRY rule.

### Trial recommendation

Run the full plugin for two weeks as an explicitly experimental capability. Capture each invocation, outcome, runtime friction, duplicated instruction, and useful principle. Review after the trial with four questions:

1. Which skills produced decisions or proof that the base Helioy stack would have missed?
2. Which playbooks mapped cleanly to warroom and bus?
3. Which instructions remained Cursor specific in live use?
4. Which principles deserve promotion into canonical AGENTS, and which should remain opt in skills?

The experiment should optimize from observed use. Avoid pruning the imported surface before those observations exist.

## Executive verdict

**Recommendation:** retain pstack as an MIT licensed reference. Do not install or translate the collection wholesale for Claude Code or Codex.

Pstack contains strong engineering judgment, especially around evidence, parallel coverage, candidate bakeoffs, program drains, and verification tied to an exact artifact. Its packaging is a poor fit for Helioy. The plugin exposes 44 top level skills, including 21 small principle files, and binds its orchestration to Cursor Task fields, model slugs, cloud agents, `/loop`, `.cursor` paths, Cursor Automations, Graphite, and companion skills from `cursor-team-kit`.

The highest value path is to strengthen the existing Helioy warroom owner in small slices:

1. Add **Coverage** accounting from Swarm.
2. Add **Bakeoff** selection and grafting from Arena.
3. Add an **Agreement Map** from Interrogate.
4. Trial a runtime neutral verification contract before creating any new installed skill.
5. Defer Program mode until a real migration exceeds the current Slice Build Loop. If that happens, extend helioy-bus state rather than introducing a parallel orchestration store.

The first slice should be Coverage. It closes a real gap, requires no new service or store, and can be evaluated on the next fanout with four or more independent slices.

## Evidence language

- **Fact** records behavior observed in the pinned source or current Helioy source.
- **Inference** interprets the consequence of those observations.
- **Proposal** recommends a future change. No proposal in this document has been implemented.

## Method and pinned sources

**Fact.** The source was cloned read only and inspected at commit [`6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack), dated 2026-08-11. The checkout was clean. The audited plugin identifies itself as pstack 0.14.0.

**Fact.** Three independent audit lanes covered:

- every `pstack/skills/*/SKILL.md` file and relevant local references
- Arena, Swarm, Poteto Mode, Orchestrate, autonomous and PR lifecycle playbooks
- the TypeScript orchestration store and PR watcher
- both custom agents and the dormant Benny automation pack
- all Pstack guide pages
- portability against Claude Code, Codex, and current Helioy owners

**Fact.** The Helioy comparison is pinned to `helioy-plugins` commit `001818e1ba284d335d39689134370eabf5013b9a`, with primary comparison against [`warroom`](https://github.com/helioy/helioy-plugins/blob/001818e1ba284d335d39689134370eabf5013b9a/plugins/helioy-bus/skills/warroom/SKILL.md), `mail`, `code-hygiene`, Context Matters, FMM, `code-review`, `codebase-map`, and `transcript-search`.

**Method.** Recommendations were evaluated through duplication, dead or weak content, portability, authority, state ownership, verification strength, and smallest useful adoption slice. Source history was unavailable because the source clone was shallow. “Dead” therefore means unreachable in the default plugin, redundant, trivial, or dependent on unavailable runtime behavior. It does not claim abandoned maintenance.

## Factual plugin architecture

| Surface | Observed architecture |
|---|---|
| Manifest | [`.cursor-plugin/plugin.json`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/.cursor-plugin/plugin.json) exposes `skills` and `agents`. |
| Scale | 156 files, about 14,178 lines, 44 top level skill directories, 21 principle skills, and 23 Poteto playbooks. |
| Front door | [`poteto-mode`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/poteto-mode/SKILL.md) routes a request to a playbook and copies the selected steps into the task list. |
| Fanout | [`arena`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/arena/SKILL.md) runs competing full solutions. [`swarm`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/swarm/SKILL.md) partitions coverage or races alternatives. |
| Program execution | [`orchestrate.md`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/poteto-mode/playbooks/orchestrate.md) runs Frame, Install, Pilot, Scale, Drain, Land, and Close. |
| Program state | `orch.ts` and [`store.ts`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/poteto-mode/scripts/orch/store.ts) own preferences, units, frontier, ledger, inbox, gates, decisions, and derived status. |
| PR control | [`watch-pr`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/poteto-mode/scripts/watch-pr) models merge blockers and the Graphite frontier. |
| Agents | [`poteto-agent`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/agents/poteto-agent.md) is a thin Poteto wrapper. [`comment-sicko`](https://github.com/cursor/plugins/blob/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/agents/comment-sicko.md) is an aggressive comment reviewer. |
| Automation | [`automations/benny`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/automations/benny) is copied into a target repository for Slack driven triage and reproduction. It is dormant in a default install and absent from slash skill discovery. |

**Inference.** Pstack is a playbook library plus a Cursor execution adapter. Its reusable value sits mainly in contracts and state transitions. Its installation shape and executor assumptions should stay behind.

## Complete inventory of the 41 non-orchestration skills

The 41 audited skills below exclude Arena, Swarm, and Poteto Mode because those receive a dedicated orchestration analysis later. Classification totals are **Adopt 0, Adapt 5, Merge 27, Skip 9**. Zero direct adoptions reflects the current Helioy ownership model and the recent skill pruning.

### Workflow, analysis, and writing skills

| Skill | Disposition | Rationale |
|---|---|---|
| [`architect`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/architect) | **Merge** | Put caller first sketches, two structurally distinct options, module ownership, migration, and redesign triggers into warroom Spec Writing and Brainstorm. Fixed Cursor model roles and the Arena dependency do not transfer. |
| [`automate-me`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/automate-me) | **Skip** | Transcript mining, structured questions, skill creation, prose cleanup, and PR creation combine too much authority. Context Matters, transcript search, AGENTS guidance, and skill creator already own the useful parts. |
| [`blast-radius`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/blast-radius) | **Merge** | Add its proof ladder and explicit safety invariant to code review, code hygiene, and high risk warroom briefs. FMM already supplies structural impact. |
| [`bro`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/bro) | **Skip** | Seven lines restate normal conversational behavior. It does not justify an installed trigger. |
| [`create-verification-skill`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/create-verification-skill) | **Adapt** | Strongest standalone concept. Preserve Launch, Doctor, Drive, Evidence, Cleanup, Helpers, feature map, side effect checks, and a real end to end proof. Use neutral paths and reuse existing harnesses. |
| [`figure-it-out`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/figure-it-out) | **Merge** | Add a falsifiable done predicate, riskiest unknown first, and VERIFIED, NOT VERIFIED, or INCONCLUSIVE outcomes to warroom phase contracts. The wrapper duplicates warroom routing and lifecycle. |
| [`how`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/how) | **Merge** | Use its overview, concepts, flow, file map, and gotchas contract in Scout. FMM and codebase map handle narrow questions; warroom handles complex lanes. |
| [`interrogate`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/interrogate) | **Merge** | Add a shared rubric, agreement map, explicit dismissals, and lead judgment to Code Review and Peer Consensus. Retain Helioy's exact head and live state rules. |
| [`maintain-verification-skill`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/maintain-verification-skill) | **Adapt** | Pair with the verification generator. Keep clean, changed, and blocked outcomes, a strict edit fence, feature coverage, and coordinator owned live proof. Bound fanout by phase size. |
| [`no-comments`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/no-comments) | **Skip** | The default deletion posture can remove durable rationale and depends on Comment Sicko. Keep only the review question: can an asserted invariant become a type, test, lint, or runtime check? |
| [`recall`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/recall) | **Merge** | Add its compact thread status and single next move output to transcript search and Context Matters. Replace Cursor JSONL paths with the Transport Matters session API. |
| [`reflect`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/reflect) | **Skip** | Three reviewers plus synthesis is costly for routine reflection, and automatic backlog filing expands authority. Store repeated decision changing lessons after approval. |
| [`setup-pstack`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/setup-pstack) | **Skip** | It writes Cursor model slugs into an always applied rule. Runtime capability and selection already belong to warroom. |
| [`show-me-your-work`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/show-me-your-work) | **Adapt** | Use the formula safe six column TSV only for long or high risk phases. Place it in the named phase artifact directory. Do not require transcript replay and another reviewer for ordinary work. |
| [`tdd`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/tdd) | **Skip** | Current AGENTS and Slice Build rules already require regression proof. Pstack permits skipping the test when setup is expensive, which is weaker than the local bug fixing rule. |
| [`teach`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/teach) | **Skip** | A presentation wrapper around How, Why, diagrams, and prose cleanup adds no durable capability owner. |
| [`technical-writing`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/technical-writing) | **Adapt** | Extract a concise shared writing reference with document mode, active instructions, stable terminology, concrete symbols, and ambiguity checks. Drop arbitrary sentence limits and overlapping style doctrine. |
| [`typescript-best-practices`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/typescript-best-practices) | **Merge** | Keep `unknown` at external boundaries, discriminated unions, exhaustive matching, and schema derived types in repo guidance or code hygiene. Treat casts and branded primitives as review signals. |
| [`unslop`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/unslop) | **Skip** | It overlaps current writing rules and `my-voice`. Objective checks are useful; categorical objections to punctuation and technical vocabulary can reduce precision. |
| [`why`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/why) | **Adapt** | Preserve code anchoring, citation discipline, confidence, contradictions, source coverage, and explicit gaps. Search only relevant available sources. Record null results with query and access limits. |

### Principle skills

These are internal doctrine modules presented as top level triggers. Their content is generally stronger than their packaging.

| Skill | Disposition | Rationale |
|---|---|---|
| [`principle-boundary-discipline`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-boundary-discipline) | **Merge** | Add boundary parsing and domain focused internals to code hygiene. Retain defense at persistence and privilege boundaries. |
| [`principle-build-the-lever`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-build-the-lever) | **Merge** | Deterministic tooling helps repeated mechanical work. Require evidence that a tool earns its maintenance cost. |
| [`principle-encode-lessons-in-structure`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-encode-lessons-in-structure) | **Merge** | Put repeated enforceable lessons in code hygiene or Context Matters. Preserve human judgment where mechanical enforcement would distort the rule. |
| [`principle-exhaust-the-design-space`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-exhaust-the-design-space) | **Merge** | Use two or three distinct shapes for novel or expensive choices through Brainstorm or Spec Writing. |
| [`principle-experience-first`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-experience-first) | **Merge** | Add to product facing briefs when user experience drives the decision. It is too general for a global trigger. |
| [`principle-fix-root-causes`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-fix-root-causes) | **Merge** | Existing AGENTS rules already own root cause fixes. The restart state heuristic is a useful review prompt. |
| [`principle-foundational-thinking`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-foundational-thinking) | **Merge** | Add data shape, mutable state, and shared setup questions to code hygiene and Spec Writing. |
| [`principle-guard-the-context-window`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-guard-the-context-window) | **Merge** | Warroom already has the stronger owner: orchestrator context is the budget, artifacts stay on disk, bus carries signals. |
| [`principle-laziness-protocol`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-laziness-protocol) | **Merge** | Fold deletion, flat call paths, centralized decisions, and small diffs into code hygiene. |
| [`principle-make-operations-idempotent`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-make-operations-idempotent) | **Merge** | Add an idempotency test for lifecycle, queue, installer, and cleanup work. Keep it contextual rather than global. |
| [`principle-migrate-callers-then-delete-legacy-apis`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-migrate-callers-then-delete-legacy-apis) | **Merge** | Directly matches Helioy's pre release and DRY rules. Combine caller migration and old path deletion in one change. |
| [`principle-minimize-reader-load`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-minimize-reader-load) | **Merge** | Add the reader load test to code hygiene. It overlaps simplification principles and needs no trigger. |
| [`principle-model-the-domain`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-model-the-domain) | **Merge** | Prefer structures that remove branches and invalid states. Reject abstractions that add indirection without compression. |
| [`principle-never-block-on-the-human`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-never-block-on-the-human) | **Skip** | Current authority policy defines reversible work and external actions more carefully. Broad autonomy language can hide product decisions. |
| [`principle-outcome-oriented-execution`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-outcome-oriented-execution) | **Merge** | Planned temporary breakage can be valid in pre release rewrites when the verification boundary is explicit. Combine with migration guidance. |
| [`principle-prove-it-works`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-prove-it-works) | **Merge** | Existing AGENTS, code review, and warroom gates own this rule. Preserve artifact evidence over worker self report. |
| [`principle-redesign-from-first-principles`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-redesign-from-first-principles) | **Merge** | Fits breaking change tolerance. Combine with foundational and migration guidance. |
| [`principle-separate-before-serializing-shared-state`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-separate-before-serializing-shared-state) | **Merge** | Warroom already isolates panes, branches, and outputs. Keep the one writer test for any shared artifact. |
| [`principle-sequence-verifiable-units`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-sequence-verifiable-units) | **Merge** | Add explicit before and after evidence to Slice Build when feasible. Existing phase and gate rules own unit sizing. |
| [`principle-subtract-before-you-add`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-subtract-before-you-add) | **Merge** | Already aligned with DRY and deletion of old paths. Fold into code hygiene. |
| [`principle-type-system-discipline`](https://github.com/cursor/plugins/tree/6dbbdd50cef1bdbfb540f80df8b598d0a546e3aa/pstack/skills/principle-type-system-discipline) | **Merge** | Keep illegal state modeling, external parsing, exhaustive matching, and schema derivation in language or repo guidance. Avoid universal cast and branding bans. |

## Thematic quality audit

### Strengths

**Fact.** Pstack provides unusually precise parallel work contracts. Arena separates candidate production, judgment, base selection, grafting, and verification. Swarm declares partition, race, or mix before dispatch and accounts for terminal outcomes. Interrogate preserves lead judgment after model review.

**Fact.** Verification is treated as a product surface. The generator requires launch, health, drive, evidence, cleanup, a feature map, and execution of the generated instructions. Program verdicts are keyed to PR plus head SHA, so a new SHA invalidates prior proof.

**Fact.** Orchestrate contains mature long run lessons: pilot before scale, rolling windows, completion as a queue event, self contained briefs, terminal child accounting, early drain, and reattachment by branch or PR rather than agent identity.

### Duplication

| Cluster | Overlap | Synthesis |
|---|---|---|
| Simplification | Laziness, subtract first, reader load, foundational thinking, first principles redesign | One short code hygiene doctrine. |
| Domain boundaries | Domain model, boundary discipline, type discipline, foundational thinking | One boundary and data shape checklist. |
| Migration | Outcome execution, caller migration, subtract first, first principles redesign | One breaking migration contract. |
| Proof | Prove it, verifiable units, TDD, blast radius, create and maintain verification | Keep the verification lifecycle as a trial; merge the proof rules. |
| Learning | Reflect, automate me, recall, why, structural lessons, work log | Context Matters and transcript search remain owners. |
| Model panels | Architect, How critique, Interrogate, Reflect, Teach, Blast Radius | Warroom remains the single orchestration owner. |
| PR owner loop | `autopilot-full` and `autopilot-stack` repeat the same lifecycle | One policy with a merge authorization flag if ever adapted. |
| Fanout ceremony | Arena and Swarm repeat framing, dispatch, isolation, and dropout rules | Share warroom phase contracts; vary aggregation semantics. |
| Verdicts | Swarm, Figure It Out, ledger, Shipping, watch-pr, Benny, and warroom use separate vocabularies | Define translation boundaries. Mergeability, behavioral proof, and message state remain distinct types. |

### Weak or dead content

- **Fact:** Benny is intentionally dormant in a default install.
- **Fact:** `multi-phase-plan.md` is a three line redirect that still appears as a first class playbook.
- **Fact:** `overview.md` is specified by Orchestrate but untouched by the CLI.
- **Fact:** Comment Sicko participates in orchestration indirectly. Poteto Mode requires `no-comments` before review, and PR playbooks invoke that skill. `no-comments` is the direct caller of the agent.
- **Fact:** Orchestrate records a failed trial where ceremony turned a 12 unit, half hour job into one landed unit.
- **Inference:** The 21 principle skills are implementation modules for Poteto Mode. Exposing them as user triggers creates discovery noise and maintenance burden.
- **Inference:** Absolute rules around casts, comments, tool creation, and all source searches encode one engineer's taste too broadly for shared Helioy policy.

### Portability hazards

- Cursor paths: `.cursor/skills`, `.cursor/rules`, `.cursor/automations`, `.cursor/settings.json`, and Cursor transcript directories.
- Cursor APIs: `Task`, `AskQuestion`, `run_in_background`, `environment: cloud`, named subagent types, and resume semantics.
- Cursor lifecycle: `/loop`, `/automate`, built in skill creation, dashboard liveness, and cloud sleeper chains.
- Cursor metadata: `mode`, `reminder`, `icon`, `is_background`, and unverified target support for `disable-model-invocation`.
- Perishable model slugs in `pstack-models.mdc`.
- External dependencies: `cursor-team-kit`, Graphite `gt`, Bugbot, Slack actions, Bun, GitHub GraphQL, and optional tracker adapters.
- Authority expansion: unattended merge, ticket updates, team chat, eval launches, and automatic WIP commits exceed Helioy's default grant.
- State duplication: copying the orchestration file store beside helioy-bus would create two operational owners.
- Module size: `store.ts` is 1,607 lines and `watch-pr/policy.ts` is 832 lines, both beyond the local 700 line threshold.
- Vendor parsing: the Graphite frontier fails closed on an allowlist of UI status strings. A vendor wording change can stall the loop.

## Runtime compatibility matrix

| Capability | Cursor | Claude Code | Codex | Helioy translation |
|---|---|---|---|---|
| Plugin manifest | Native `.cursor-plugin` discovery | Requires Claude plugin manifest and supported hooks | Requires Codex plugin packaging or installed skills | Maintain target manifests only for capabilities that pass adoption trials. |
| Skill basics | `SKILL.md` plus Cursor metadata | Basic name and description transfer; Cursor mode fields need rewriting | Basic name and description transfer; Cursor mode fields need rewriting | Keep a small common frontmatter surface. |
| Sticky Poteto mode | Native mode and reminder behavior | No equivalent established by this audit | No equivalent established by this audit | Use explicit `/warroom` routing and phase contracts. |
| Parallel agents | Cursor Task, background, cloud, named agents | Agent API differs; Cursor fields do not transfer | Agent API differs; Cursor fields do not transfer | Use tmux warrooms and explicit runtime adapters. |
| Model selection | Cursor model slugs from an always applied rule | Claude model names and flags differ | Codex model names and effort controls differ | Warroom runtime IDs are the sole policy owner. |
| Read only child | `readonly: true` in Task | Prompt boundary and permission profile differ | Prompt boundary and permission profile differ | State no writes in the brief and verify a pristine tree. |
| Wake and liveness | `/loop`, cloud events, dashboard | No direct `/loop` translation | No direct `/loop` translation | Bus nudge, heartbeat, stable pane ID, and `warroom_status`. |
| Completion | Cursor notifications and Task results | Different agent result surface | Different agent result surface | Typed one line bus signal with artifact path. |
| Transcript mining | Cursor workspace JSONL paths | Different format and location | Different format and location | Transport Matters transcript search plus Context Matters. |
| Browser or CLI proof | `cursor-team-kit` control skills | Claude specific tools may exist | Codex browser and PTY tools may exist | Verification contract selects installed repo appropriate drivers. |
| Program state | Local `orch` TSV and JSON store | Portable code, host specific executor | Portable code, host specific executor | Reuse concepts only; extend bus schema after a measured need. |
| PR frontier | Graphite `gt`, GitHub, typed watcher | CLI can run where installed | CLI can run where installed | Keep Graphite behind an optional adapter. Human merge gate stays default. |
| Slack automation | Cursor Automations and `/automate` | No direct equivalent established | No direct equivalent established | Future named automation product with explicit Slack and tracker grants. |

## Orchestration review and warroom mapping

### Arena

**Fact.** Arena runs Frame, Fan out, Cross judge, Pick, Graft, Verify. Candidates receive the same goal and rubric, write to isolated targets, and are judged by another model family. The parent still reads every candidate.

**Inference.** The distinct value is the selection protocol. Reading every full artifact at the root conflicts with Helioy's context budget rule.

**Proposal.** Add a **Bakeoff** modifier to Brainstorm and Spec Writing. Candidate agents write full artifacts to isolated paths and send bounded rationales. A fresh judge recommends a base and named grafts. The orchestrator records the selection, rejections, and verification result.

**Current owners:** Warroom Mode 6 Brainstorm, Mode 2 Spec Writing, runtime table, phase contracts, and artifact on disk message protocol.

### Swarm

**Fact.** Swarm declares partition, race, or mix, assigns isolated slices, and requires each slice to end in PASS, ISSUES, or BLOCKED. It reports gaps and dropouts.

**Inference.** Formal coverage accounting is a genuine gap in current warroom fanout. A child can disappear from synthesis without a complete slice ledger.

**Proposal.** Add a **Coverage** modifier to Scout, Code Review, and verification fanout. Define all slices before dispatch, assign one owner and gate per slice, and account for every terminal state before synthesis.

**Current owners:** Warroom Modes 1 and 4, phase contract, typed bus replies, status, and pane lifecycle.

### Poteto Mode

**Fact.** Poteto Mode is a large dispatcher across 22 playbooks, a principles index, autonomy rules, subagent policy, and prose rules. It copies chosen playbook steps into the task list and permits skips only with a recorded reason.

**Inference.** Porting it would create a second operating constitution beside AGENTS and warroom. Its single front door is useful, while its surface and Cursor bindings are costly.

**Proposal.** Keep warroom's six modes and First Decision as the router. Add modifiers rather than another mode skill. Preserve declared routing, explicit skips, falsifiable done predicates, and evidence gates.

**Current owners:** Warroom First Decision, Spine, six Modes, Non Negotiables, and Phase and Churn Control.

### Automate Me

**Fact.** Automate Me mines weeks of Cursor transcripts, interviews the user, creates a personal mode skill, applies Unslop style cleanup, and opens a PR.

**Inference.** It joins sensitive discovery, preference inference, artifact creation, and publication in one flow. Repeated evidence and explicit approval need stronger boundaries.

**Proposal.** Do not make this a warroom mode. If revisited, use transcript search for a bounded corpus, Context Matters for repeated preferences, skill creator for the artifact, and an explicit user decision before any repository write or PR.

**Current owners:** Transcript search, Context Matters, skill creator, and pull request skill. Warroom may run independent evidence lanes only when the corpus justifies them.

### Benny

**Fact.** Benny is a dormant automation pack copied into a repository. Slack threads trigger issue triage or reproduce and fix flows. It freezes source coordinates, centralizes Slack writes in one coordinator, waits for a trusted marker, drives the real UI twice, and may open one bounded draft PR. It never merges.

**Inference.** The thread safety and fail closed rules are reusable. Cursor Automations, Slack actions, tracker assumptions, and committed `.cursor` paths prevent a direct port.

**Proposal.** Defer until Helioy names an automation product and grants Slack plus tracker access. Preserve frozen thread identity, coordinator only writes, trusted markers, real surface reproduction, and draft only output.

**Current owners:** No direct warroom mode. Bus mail can carry internal events, but external Slack intake and tracker mutation need a separate authorized adapter.

### Agents

**Fact.** Poteto Agent is a nine line wrapper that loads Poteto Mode. Comment Sicko is a theatrical adversarial comment deletion reviewer. Poteto Mode and PR playbooks reach it through `no-comments`; they do not name the agent directly.

**Inference.** Poteto Agent has no value without the full mode. Comment Sicko's extreme posture can erase durable rationale.

**Proposal.** Do not port either agent. Use raw `general` warroom panes unless a bounded specialist role proves necessary. Add the enforceable invariant comment question to code review.

**Current owners:** Warroom `general` agents, Code Review, Code Hygiene, and runtime selection.

### Overnight and program flow

**Fact.** The overnight family includes Autonomous Run for one predicate, Orchestrate for a standing program, two Autopilot variants for PR queues, Babysit for merge readiness, and Shipping for verified contiguous landing. Orchestrate pilots one unit, uses a rolling window, drains completions as queue events, externalizes state, and reconciles every child. Verification is keyed to PR plus SHA. Restacks can invalidate verdicts.

**Fact.** The program store uses a lock, atomic writes, units, frontier, ledger, inbox, gates, decisions, and derived status. The executor remains Cursor Task. The store never spawns, waits, or wakes agents.

**Inference.** The state model is the richest source of future ideas, but copying it now would duplicate bus state and introduce Graphite coupling. Warroom already has durable panes, nudge, heartbeat, runtime identity, status, phase churn, and a human merge gate.

**Proposal.** Trial a bus backed Program mode only when a real program contains at least five independent units and ordinary Slice Build is demonstrably constrained. Use bus completion events, terminal member accounting, artifact keyed verdicts, and a rolling window. Extend bus state once if the trial proves a missing data model. Keep unattended merge behind a separate explicit grant.

**Current owners:** Warroom Slice Build Loop, Phase and Churn Control, bus mail, warroom status, Context Matters for durable decisions, and the human merge gate.

## Explicit mapping to current Helioy owners

| Pstack concept | Current Helioy owner | Recommended change |
|---|---|---|
| How a subsystem works | FMM, codebase map, Warroom Scout | Add the explanation output contract to Scout briefs. |
| Why and lineage | Git, GitHub, Context Matters, mdm, transcript search | Trial bounded evidence lanes. Avoid a new top level skill first. |
| Recent work recall | Context Matters and transcript search | Add concise thread status and next move output. |
| Design exploration | Warroom Brainstorm and Spec Writing | Add caller first design and Bakeoff. |
| Parallel coverage | Warroom Scout and Code Review | Add Coverage ledger and dropout accounting. |
| Model review | Warroom Code Review and Peer Consensus | Add Agreement Map and explicit dismissal reasons. |
| Runtime selection | Warroom runtime table and adapters | Reject pinned vendor model slugs. |
| Agent execution | Warroom spawn, add, remove, status, kill | Reject Cursor Task translation. |
| Completion events | Helioy bus mail | Keep one line signals and artifacts on disk. |
| Runtime identity | Bus registry, stable pane ID, heartbeat | Reconcile work by member plus artifact identity. |
| Verification | AGENTS gates, Slice Build, browser and CLI tools | Trial a neutral verification lifecycle. |
| PR lifecycle | Pull request skill, GitHub checks, human merge gate | Keep Graphite optional and adapter scoped. |
| Program state | Warroom status and bus registry | Extend bus only after Program mode evidence. |
| Durable decisions | Context Matters | Keep as the decision owner. |
| Long audit trail | Named phase artifact, optional TSV | Use only for expensive or unattended runs. |
| Engineering doctrine | AGENTS and code hygiene | Merge a short set of decision changing rules. |
| External automation | No current generic owner | Require a named product and explicit grants before design. |

## Initial prioritized proposals, superseded by the full experiment

### P0. Coverage modifier

**Smallest useful slice:** update warroom guidance and its behavior checks. Apply only when fanout has four or more slices, or when omission has high consequence.

**Acceptance criteria:**

- brief declares a complete slice list before dispatch
- every slice has one owner, one output, and one gate
- every child ends PASS, ISSUES, or BLOCKED with evidence
- synthesis includes a compact coverage table, dropouts, and explicit gaps
- a missing terminal state prevents a clean verdict
- no new skill, store, MCP, or service is introduced

**Risk:** ceremony can exceed value on small fanouts. The threshold and explicit opt in limit this.

### P1. Bakeoff and Agreement Map

**Smallest useful slices:** add Bakeoff to Brainstorm or Spec Writing first. Add Agreement Map to Peer Consensus in a separate change.

**Bakeoff acceptance criteria:** identical goal and rubric, isolated outputs, at least two runtime families when diversity matters, independent judge, one selected base, named grafts, recorded rejections, and proof of the synthesized artifact.

**Agreement Map acceptance criteria:** identical review intent and exclusions, deduplicated findings, convergence and disagreement labels, Act, Consider, Note, or Dismiss classification with one reason, and final judgment retained by the orchestrator.

**Risks:** the root can consume too much candidate content; correlated models can create false confidence. Require artifacts on disk, bounded rationales, and family diversity.

### P2. Caller first design and proof ladder

**Smallest useful slice:** strengthen existing Spec Writing and high risk Code Review wording.

**Acceptance criteria:** each expensive design shows caller usage, data shape and owner, public signatures, module map, migration and deletion path, and real verification method. Each high risk review names the critical safety invariant and proof level. Multiple independent hazards remain allowed.

**Risk:** mechanical changes may attract unnecessary design ceremony. Apply only when the decision is novel, expensive, or high blast radius.

### P3. Verification lifecycle trial

**Smallest useful slice:** one workflow document under `~/.mdx/workflows/` and one target repository with a repeated, unreliable user visible verification need. Promote to a skill after at least two successful uses.

**Acceptance criteria:** Launch, Doctor, Drive, Evidence, Cleanup, Helpers, and feature map are complete; an existing harness is preferred; the real surface and side effects are exercised; instances are isolated; cleanup touches only owned resources; instructions execute successfully in both Claude Code and Codex where the repository supports both.

**Risks:** runtime paths leak into the contract, generated wrappers duplicate repo tooling, or cleanup affects user processes.

### P4. Bounded lineage trial

**Smallest useful slice:** investigate one known architectural decision across git, Context Matters, and markdown. Add GitHub or transcripts only when relevant.

**Acceptance criteria:** exact code and git anchor, citations for direct evidence, explicit inference, contradictions, source coverage, null query details, access limitations, and unresolved gaps.

**Risk:** mandatory all source fanout wastes context and null results can be overstated. The question determines lanes.

### P5. Bus backed Program mode experiment

**Smallest useful slice:** one real migration with at least five independent units. Compare against ordinary Slice Build on wall time, landed units, rework, dropped units, and orchestrator context.

**Acceptance criteria:** pilot succeeds before scale; rolling window follows drain capacity; each worker brief is self contained; every member reaches a terminal state; completions arrive as bus events; verdicts bind to artifact identity; status is derived from one owner; spawning stops early enough to verify and land; human merge gate remains unless explicitly expanded.

**Risks:** duplicated state, Graphite coupling, orchestration overhead, stale verdicts, and unattended external actions. Extend bus schema only when the experiment proves the need.

## Options rejected during the initial selective adoption audit

1. Full pstack translation.
2. Poteto Mode as a second root operating mode.
3. Installation of the 21 principle skills.
4. Separate top level Arena, Swarm, Architect, How, Why, Recall, or Interrogate skills before existing owner trials fail.
5. Cursor Task fields, cloud agent semantics, model slugs, `/loop`, or `.cursor` paths in common Helioy guidance.
6. A second operational program store beside helioy-bus.
7. Graphite or Bugbot behavior in generic warroom policy.
8. Default four model bakeoffs.
9. Comment Sicko and blanket comment deletion.
10. Benny before a named automation product and explicit external grants.
11. Automatic WIP commits, ticket mutation, team chat, eval launches, or unattended merge without user authority.
12. Growth of the 1,607 line store module if code is ever reused. Split lock and IO, domain tables, frontier adapters, and rendering first.

## Initial decisions for Stuart, resolved by the experiment decision

1. **Approve or reject P0 Coverage.** Recommended: approve and evaluate on the next fanout with four or more slices.
2. **Choose whether P1 follows automatically after a successful Coverage trial.** Recommended: require separate evidence for Bakeoff and Agreement Map.
3. **Nominate a repository for the verification lifecycle trial.** Recommended criterion: a repeated user visible check that is currently unreliable or undocumented.
4. **Choose whether a bounded lineage trial is worth a workflow document.** Recommended: trial once before creating any installed skill.
5. **Defer Program mode until a concrete migration exceeds Slice Build.** Recommended: approve the evaluation rule now, defer implementation.
6. **Keep the human merge gate as default.** Recommended: any unattended merge becomes a separate explicit grant.
7. **Retain pstack as a pinned reference.** Recommended: record MIT attribution when copying text or code; prefer Helioy native wording for borrowed ideas.

## Initial recommendation, superseded by the experiment decision

Approve Coverage as one bounded warroom improvement. Keep pstack as a pattern source. Evaluate every further adoption through a real trial and strengthen current owners before adding another skill, store, or runtime abstraction.
