---
title: paperclipai/paperclip review for orchestration-matters + agent-matters + session-matters
type: research
tags: [github-review, paperclip, orchestration-matters, agent-matters, session-matters, runtime-matters, workflow-matters, knowledge-matters, typescript, drizzle, postgres, plugin-system, mit, control-plane, heartbeat, budget-governance]
summary: Paperclip is an MIT TypeScript control plane that orchestrates teams of heterogeneous AI agents as a "company" (org charts, budgets, governance, heartbeats). Grade B+; borrow the adapter/heartbeat contract, atomic checkout, budget hard-stop, and capability-gated out-of-process plugin worker.
status: active
source: github-researcher
confidence: high
created: 2026-06-15
updated: 2026-06-15
---

# paperclipai/paperclip — learn/leverage review

Source: https://github.com/paperclipai/paperclip
Local clone (cleaned up after review): /tmp/gh-research/paperclipai-paperclip
Default cm scope: `global/project:helioy`

## 1. Stats

70,382 stars, ~13,069 forks, 375 watchers, 4,999 open issues. Created 2026-03-02, last push 2026-06-13 (extremely active, ~3 months old at review). MIT licensed, © Paperclip Labs, Inc. Primarily TypeScript (~23 MB of TS) with Dockerfile/Shell/Go/HCL support code; ~105 MB on disk. pnpm 9.15 monorepo (`server`, `ui`, `cli`, `packages/*`), Node 20+, Drizzle ORM over PostgreSQL with embedded PGlite/embedded-postgres for zero-setup local dev. 563 test files (Vitest + Playwright e2e), 8 GitHub Actions workflows (`pr.yml`, `e2e.yml`, `release.yml`, `docker.yml`, release-smoke, agent-runtime-images, lockfile refresh, an LLM "commitperclip" review job). Contributor graph is dominated by one author (Jannes Stubbemann) across the shallow window; effectively a single-vendor open-source project with heavy outside fork activity. Date-stamped CalVer releases (`v2026.609.0`). Quality bars are real: TDD-first PRs, a mandatory PR template requiring a "Model Used" field and a "Thinking Path", contract-sync rules across db/shared/server/ui.

## 2. What it is

Paperclip is an open-source control plane for running "AI-agent companies": you define a business goal, hire a team of heterogeneous agents (Claude Code, Codex, Cursor, Gemini, bash, HTTP/webhook bots, OpenClaw), give them an org chart with reporting lines and per-agent budgets, and the server orchestrates their work through a ticketing system. Architecturally it is a Node/Express REST server plus React/Vite UI over a Drizzle/Postgres schema, with a DB-backed heartbeat wakeup queue as the execution engine, a pluggable adapter registry (the agent integration seam), governance/approval gates, atomic task checkout, token/cost budget hard-stops, an out-of-process capability-gated plugin system, and full company export/import. The thesis: "If OpenClaw is an employee, Paperclip is the company" — it deliberately does not build agents, it runs organizations of them. It is the cleanest open reference for the orchestration layer that sits *above* individual agents.

## 3. Grade

**B+** (same tier as superpowers). A mature, production-grade, single-vendor control plane that solves exactly the orchestration problem Helioy's `orchestration-matters` / `agent-matters` / `session-matters` family is converging on, with battle-tested DB-level primitives (atomic checkout, coalesced wakeup queue, budget hard-stop) that transfer as designs. Held below A− by (1) single-vendor bus-factor, (2) the `paperclip-as-a-company` product framing is heavier than Helioy's local-first laboratory needs, and (3) serious file-size hygiene problems (`server/src/services/heartbeat.ts` is 11,573 lines; `routes/issues.ts` 7,480; `services/issues.ts` 6,520) that violate Helioy's 700-line hard limit and signal the orchestration core is a god-module. Borrow the contracts, not the file structure.

## 4. Primitives that transfer

1. **Adapter contract: the minimal `ServerAdapterModule` interface** — `packages/adapter-utils/src/types.ts:352-435` (`type`, `execute(ctx)`, `testEnvironment(ctx)`, optional `listSkills`/`syncSkills`/`sessionCodec`/`sessionManagement`/`supportsLocalAgentJwt`). Mutable registry at `server/src/adapters/registry.ts:503-646` (`registerServerAdapter` / `unregisterServerAdapter` / `requireServerAdapter` into a `Map<string, ServerAdapterModule>`). **Landing target: agent-matters.** This is the literal "if it can receive a heartbeat, it's hired" seam — a tiny, stable interface that admits Claude/Codex/Cursor/bash/HTTP without the core knowing about any of them. Helioy's agent abstraction should be this narrow.

2. **DB-backed wakeup queue with coalescing + idempotency** — schema `packages/db/src/schema/agent_wakeup_requests.ts:5-40` (`status`, `coalesced_count`, `idempotency_key`, `claimed_at`); coalescing in `server/src/services/heartbeat.ts:10669-10705` (dedupe by idempotency key, increment `coalescedCount`); claim CAS at `heartbeat.ts:6823-6852`. **Landing target: session-matters / orchestration-matters.** A durable, restart-survivable scheduler that collapses duplicate wake requests is exactly what an autonomous agent (nancyr) needs instead of in-memory timers.

3. **Atomic task checkout via Compare-And-Swap** — `server/src/services/heartbeat.ts:6859-6878`: a single conditional `UPDATE issues SET executionRunId, executionLockedAt WHERE id = ? AND companyId = ? AND assigneeAgentId = ? AND (executionRunId IS NULL OR executionRunId = ?)`. **Landing target: workflow-matters / orchestration-matters.** This is how you guarantee two agents never double-work one task without distributed locks: a status/owner CAS in one statement. Directly applicable to any Helioy work-claim path.

4. **Budget hard-stop coupled to cost events** — policy schema `packages/db/src/schema/budget_policies.ts:4-43` (`metric`, `windowKind`, `hardStopEnabled`); incident ledger `budget_incidents.ts:7-42`; enforcement `server/src/services/costs.ts:99` (`budgets.evaluateCostEvent` after every cost insert) → `server/src/services/budgets.ts:214-249` (`pauseScopeForBudget`, sets `agents.status="paused"`, `pauseReason="budget"`). **Landing target: runtime-matters / agent-matters.** Token/cost runaway is the #1 autonomous-agent failure mode; an evaluate-on-write budget ledger with scoped auto-pause is the right shape for nancyr cost control.

5. **Out-of-process, capability-gated plugin worker** — manifest `packages/shared/src/types/plugin.ts:509` (`id`, `apiVersion`, `capabilities[]`, `entrypoints.worker`); worker lifecycle `server/src/services/plugin-worker-manager.ts` (`child_process.fork`, JSON-RPC 2.0 over stdio, 10s drain → SIGTERM → SIGKILL); capability gate `server/src/services/plugin-capability-validator.ts:44-131` (`OPERATION_CAPABILITIES` map; `assertOperation` rejects any host call whose capability the manifest did not declare). **Landing target: runtime-matters (harness tool-gating) + the matters plugin family.** This is a clean least-privilege model for letting third-party code call host services — the same problem Helioy's harness tool-gating and MCP exposure face. Maps onto the gvisor-inspired tool-gating note already in cm.

6. **Goal-ancestry context assembly** — `server/src/services/issues.ts:6396-6460` (`getAncestors`: walks `parentId` chain up to 50 levels with cycle guard, batch-loads project + goal metadata) feeding the run context so every task carries its "why." **Landing target: context-matters / knowledge-matters / runtime-matters (Helix).** The ancestry-walk-then-assemble pattern is a concrete JIT-context recipe: assemble the minimal lineage the agent needs at run time rather than dumping everything. Pairs with Helioy's scope-chain ancestor walk in cm.

7. **Runtime skill injection (no retraining)** — catalog/loader `server/src/services/company-skills.ts:4245-4275` (`listRuntimeSkillEntries`); injection into the run at `heartbeat.ts:8304-8310` (`paperclipRuntimeSkills` merged into resolved config per heartbeat). **Landing target: runtime-matters / the Helioy skills-sync system.** Skills are fetched per-run and pushed into the adapter context, with version selection — the same per-run skill-resolution Helioy's `skill-matters` / skills:sync is reaching for.

8. **Company export/import with secret scrubbing** — routes `server/src/routes/companies.ts:246-280`; scrubbing `server/src/services/company-portability.ts:499-510` (`secret_ref` bindings exported as empty `defaultValue`, importer must re-supply). **Landing target: littleorgans (org templates) / context-matters (cx_export).** Portable org bundles with secret-scrubbing-on-export is the right contract for sharing agent setups; cx_export already exists, this validates the scrub-on-export discipline.

9. **Company-scoped tenant isolation as a schema + access invariant** — every entity carries `companyId`; plugin tables got a `company_id` FK (`packages/db/src/schema/plugin_entities.ts:28-70`, per-tenant unique index); route gate `server/src/routes/agents.ts:205-217` (`access.decide` returns 403 across company boundary). **Landing target: orchestration-matters (multi-org) — inspiration only for v1.** Forward-compatible with the K8s-shaped namespace endgame; v1 local-first single-operator does not need multi-tenancy yet.

## 5. Does NOT transfer

1. **The "company" product framing** (CEO/CTO org charts, hire flows, board approvals, mobile dashboard). Helioy v1 is a local-first laboratory for one operator, not a SaaS that runs autonomous businesses. The org-chart/governance UI is product surface Helioy does not want.
2. **The god-module file structure.** `heartbeat.ts` (11,573 lines), `routes/issues.ts` (7,480), `services/issues.ts` (6,520) violate Helioy's 700-line hard limit by 10x+. Borrow the *contracts and SQL patterns*, never the file layout.
3. **Express REST + React/Vite stack.** Helioy's matters core is Rust (rusqlite/sqlx three-crate workspaces); the TS/Drizzle/Postgres implementation is the wrong language and storage engine for cm/am/fmm. Designs port, code does not.
4. **PGlite/embedded-postgres for local dev.** Helioy standardized on SQLite (cm uses sqlx, am uses rusqlite). No reason to adopt embedded Postgres.
5. **Multi-company tenancy machinery in v1.** Useful as a forward-compat signal for the K8s-namespace endgame, but the company_id-everywhere overhead is dead weight for a single operator now.
6. **Telemetry-on-by-default + heavy plugin marketplace ecosystem** (awesome-paperclip). Helioy's distribution model is MIT mirrors under `littleorgans`, not a hosted plugin marketplace.

## 6. Verdict

**Borrow (designs, not code).** Paperclip is the best open reference for the orchestration layer above individual agents, and four of its DB-level primitives (adapter contract, coalesced wakeup queue, atomic CAS checkout, evaluate-on-write budget hard-stop) are directly portable as designs into `orchestration-matters` / `agent-matters` / `session-matters` / `runtime-matters`. Reimplement the contracts in Rust; do not vendor the TypeScript.

## 7. Why

Helioy's "matters" family has built the cognitive organs (context, attention, knowledge, code-nav) but the orchestration layer that coordinates *multiple autonomous agents over time* (nancyr, helioy-bus, the warroom) is still emerging. Paperclip has already paid for the hard, boring correctness work at this layer: how to wake an agent durably without losing state on reboot, how to stop two agents from grabbing the same task, how to halt a runaway token loop atomically, and how to let an agent learn workflows at runtime. These are precisely the failure modes a local-first autonomous lab hits once it has more than one agent running. Paperclip's answers are DB-native CAS and ledger patterns that are language-agnostic, so Helioy can lift the design pressure without taking on the product weight or the TypeScript.

## 8. How to apply

1. **agent-matters:** Adopt the minimal adapter interface shape (`type` + `execute` + `testEnvironment` + optional skill/session hooks) and a mutable Rust registry as the canonical agent seam. Verify it stays under 700 lines per file — the opposite of Paperclip's `heartbeat.ts`.
2. **session-matters / orchestration-matters:** Design a durable wakeup queue table with `coalesced_count` + `idempotency_key` + `claimed_at` CAS for nancyr scheduling, mirroring `agent_wakeup_requests`. This replaces in-memory timers with restart-survivable state.
3. **workflow-matters:** Adopt the single-statement CAS task-claim (`UPDATE ... WHERE id=? AND owner=? AND (lock IS NULL OR lock=?)`) for any Helioy work-claim path so concurrent agents never double-work.
4. **runtime-matters:** (a) Build an evaluate-on-write budget ledger with scoped auto-pause for nancyr cost control. (b) Use Paperclip's `OPERATION_CAPABILITIES`-style capability gate as the model for harness tool-gating (ties to the existing gvisor-inspired cm note). (c) Mirror the per-run skill-resolution/injection pattern in the Helioy skills:sync path.
5. **context-matters / knowledge-matters:** Treat `getAncestors` as a concrete JIT-context recipe — walk the scope/issue lineage with a cycle guard and depth cap, batch-load metadata, assemble only the minimal "why" into the run context. Validates the scope-chain ancestor walk cm already does.
6. **Skip for now:** company/org product framing, multi-tenancy machinery, Express/React stack, embedded Postgres, plugin marketplace.

## Sources Consulted

- README.md, AGENTS.md, ROADMAP.md, adapter-plugin.md, package.json, pnpm-workspace.yaml
- `packages/adapter-utils/src/types.ts`, `server/src/adapters/registry.ts`
- `server/src/services/heartbeat.ts`, `packages/db/src/schema/{agent_wakeup_requests,heartbeat_runs,budget_policies,budget_incidents,plugin_entities}.ts`
- `server/src/services/{costs,budgets,company-skills,company-portability,issues}.ts`
- `server/src/routes/{agents,companies}.ts`
- `packages/shared/src/types/plugin.ts`, `server/src/services/{plugin-worker-manager,plugin-capability-validator}.ts`
- GitHub API: stars/forks/releases/contributors

## Open Questions

- How does Paperclip handle session continuity across heartbeats at the adapter level (`sessionCodec` / `sessionManagement` / `session-compaction.js`)? Worth a focused read if session-matters needs a compaction model.
- Recovery/orphan-sweep service (`server/src/services/recovery/service.ts`, 3,936 lines) — the orphaned-run recovery story is relevant to nancyr resilience but was not deeply traced.
- The "commitperclip-review.yml" LLM-in-CI review job — possibly a borrowable pattern for Helioy CI gating, not examined.
