---
title: openprose/prose (OpenProse + Reactor) capability review
type: research
tags: [github-review, openprose, prose, reactor, typescript, mit, memoization, content-addressed, receipts, dag, agent-harness, schedule-matters, context-matters]
summary: OpenProse is a declarative Markdown-contract paradigm for agents; Reactor is a React-flavored harness that memoizes agent sessions in a self-wiring DAG and re-renders only on material change, leaving a chain-verifiable receipt ledger. Inference cost scales with surprise, not the clock.
status: active
source: github-researcher
confidence: high
created: 2026-06-04
updated: 2026-06-04
---

# openprose/prose — OpenProse (the language) + Reactor (the harness)

Reviewed repo: https://github.com/openprose/prose
Local clone (deleted after review): /tmp/gh-research/openprose-prose

## 1. Stats

1,416 stars, 105 forks, MIT licensed. The repo was created on GitHub 2026-01-03 but real code landed 2026-01-31 (first substantive commit: "feat: add agent-directed attention markers and post-execution guidance"); last commit 2026-06-03 ("feat(reactor-cli): route provider: anthropic through native Messages API", PR #113). That is roughly four months of active development at a high cadence, with the commit count paginating past ~212 pages of single-commit API queries (thousands of commits) and 9 contributors, though `irl-dan` / `dan` authors the overwhelming majority. It is a pnpm monorepo, TypeScript-dominant (~4.3MB TS vs ~210KB JS), ~39.7K non-test TS LOC plus 165 test files. CI is robust: 11 GitHub Actions workflows including a keyless offline examples-gate (`ci-examples-gate.yml`, three tiers all at `REACTOR_OFFLINE=1`), full package CI, automated release, plugin-manifest validation, and benchmark harnesses (`longcot-bench.yml`, `longcot-rlmify.yml`). Three packages are live on npm: `@openprose/reactor` 0.3.1, `@openprose/reactor-cli` 0.2.2, `@openprose/reactor-devtools` 0.2.0. Not archived; actively maintained.

## 2. What it is

OpenProse is a **declarative programming paradigm for agents**: you author the outcomes you want kept true as Markdown contracts (`*.prose.md`) rather than issuing instructions, with optional imperative "ProseScript" fulfillment plans for when ordering matters. A contract declares `### Maintains` (the world-model schema this node keeps current, with material vs immaterial fields and optional `####` facets), `### Requires` (the upstream facets it subscribes to), and `### Continuity` (the wake source: input-driven, self-driven on a cadence, or external). OpenProse ships first as a Skill (`skills/open-prose/`) and is positioned as harness-agnostic: the `.prose.md` is the public artifact and runs on "any Prose-Complete agent host."

Reactor (`@openprose/reactor`) is the harness built to run OpenProse, and the architecture is **explicitly React-flavored**: a Responsibility is a Component, the world-model is the DOM, a `render()` is a bounded LLM session, subscriptions are props, and `React.memo` becomes "skip the render if subscribed inputs haven't moved." The thesis is one sentence: **inference cost that scales with surprise, not wall-clock time.** Reactor compiles a contract set once (intelligently: a layer called Forme matches `Requires.<facet>` against `Maintains.<facet>` and wires the DAG itself; per-node canonicalizers and postcondition validators are frozen), then runs forever (dumbly: compare fingerprints, skip / render / propagate). The reconciler that decides whether to wake is deliberately deterministic with **no judge step and no clock in the memo key** — a render runs only when a node's subscribed-input fingerprints or its own contract fingerprint move. A render that cannot satisfy its postconditions commits nothing; the prior truth stands and a `failed` receipt records why.

The codebase maps one-to-one onto that vocabulary. `packages/reactor/src/` decomposes into `forme/` (DAG wiring), `canonicalizer/` (material-field reduction), `memo/` (the skip decision), `world-model/` (content-addressed published/private truth store), `receipt/` (the chain-verifiable ledger), `postcondition/` (commit-gate validators), `forecast/` (self-driven freshness scheduler), `cost/` (surprise attribution), `projection/` (derived views), plus `sdk/` (a curated facade with six reasoned subpaths) and `adapters/` (substrate + record/replay seam). The two empty-looking packages `co/` and `std/` are not stubs: they are OpenProse contract libraries (`.prose.md` files like `std/delivery/email-notifier.prose.md`), the standard library of the language. Data flow: contracts compile to a topology world-model; a wake event updates input fingerprints; the reconciler computes a memo key, skips or spawns a bounded session; a successful render commits a content-addressed world-model and appends a sha256-chained receipt; moved fingerprints propagate to subscribers.

## 3. Grade

**A−.** Sits with notebooklm-py / mngr / fallow-rs: a genuinely novel, coherent thesis ("cost scales with surprise") executed across a 40K-LOC TS monorepo with a self-wiring DAG, content-addressed truth, chain-verifiable receipts, 165 test files, a keyless offline replay gate in CI, three shipped npm packages, and unusually disciplined spec-cited code. It is held just short of off-scale-A by its own honest-status admissions: benchmarks are pending (the speedup is unproven), the signer is tamper-evident but not yet a cryptographic byte hash, receipts carry no timestamp or actor, and it is single-author at v0.x.

## 4. Primitives that transfer

1. **The memo key as `(contract_fingerprint, input_fingerprints)` and nothing else** — `packages/reactor/src/memo/index.ts:53` (`computeMemoKey`) and `:135` (`InMemoryMemoStore.decide`). A node re-renders only when its contract or its subscribed inputs move; cold-start always renders. **Landing target: schedule-matters.** This is the exact discipline schedule-matters wants for cron/standing jobs — skip the expensive agent run unless a tracked input fingerprint actually changed, instead of firing on a wall-clock cadence.

2. **Content-addressed world-model with a published/private split** — `packages/reactor/src/world-model/store.ts:95` (`WorldModelStore` interface), `:109` (`writeWorkspace`, never fingerprinted), `:117`/`:231` (`commitPublished`, write-and-fingerprint on commit). Scratch reaches subscribable truth only through an explicit commit. The doc-comment stance that "SQLite/vector/dashboard are a derived projection of canonical truth, never the truth itself" (store.ts:11-12) is directly applicable. **Landing target: context-matters.** cm could treat its FTS/vector index as a derived projection over a canonical content-addressed entry store, with a private-workspace vs published-entry distinction.

3. **The chain-verifiable receipt ledger** — `packages/reactor/src/receipt/index.ts:248` (`verifyReceiptChain`) and `:299` (`computeReceiptContentHash`). Each receipt sha256-commits to its fingerprints and its `prev`; verification is node-scoped chain consistency (cold start has `prev: null`). **Landing target: context-matters / history-matters.** A tamper-evident, append-only decision trail is exactly what cm's supersede/forget history and history-matters' command log want for an auditable "what changed and why" record.

4. **Forme: structure-is-subscription self-wiring DAG** — `packages/reactor/src/forme/index.ts:298` (`wire`), `:228` (`exactFacetMatcher`, the injected intelligence seam), `:443` (`hasNodeCycle`, acyclicity as a postcondition). The graph draws itself by matching declared `Requires.<facet>` to `Maintains.<facet>`; the one intelligent step (semantic facet matching) is an injected pure function. **Landing target: helioy-bus / warroom.** Multi-agent orchestration could wire agent dependency edges from declared produces/consumes contracts rather than hand-wired routing, with acyclicity enforced at compile.

5. **Surprise attribution / cost rollup** — `packages/reactor/src/cost/index.ts:21` (`ALLOWED_SURPRISE_CAUSES`), with invariants `surprise-attribution-complete` (every token-bearing receipt names exactly one wake cause) and `flat-spend-under-static` (post-bootstrap fresh spend is flat in a static world). **Landing target: littleorgans / any agent surface.** A fresh-vs-reused token meter attributed to a named wake cause is a clean cost-observability primitive for any Helioy agent loop.

6. **Self-driven freshness scheduler decoupling policy from state** — `packages/reactor/src/forecast/index.ts:51` (the continuity schedule). The recheck cadence is `### Continuity` policy; the per-facet `valid_until` is freshness state carried as data. **Landing target: schedule-matters.** This policy/state split is the right shape for cron-like freshness rechecks that still respect "skip if nothing moved."

## 5. Does NOT transfer

1. **The OpenProse contract language and ProseScript.** A whole authoring surface (`*.prose.md`, `### Maintains/Requires/Continuity`, the compiler skill at `skills/open-prose/`). Helioy already has its canonical workflow contract in linear-workflows and a memory model; importing a second declarative file-based contract format would duplicate that surface, which cm memory explicitly warns against.

2. **The React metaphor as a public API.** Reactor leans hard on React vocabulary (Component/DOM/render/memo/props) as the mental model. It is a teaching device, not a dependency Helioy needs; the underlying primitives (memo key, receipts) transfer without it.

3. **The `@openai/agents` render substrate and OpenRouter wiring.** `packages/reactor-cli` binds renders to `@ai-sdk/anthropic`, `@openai/agents-extensions`, and OpenRouter keys. Helioy routes providers through its own factory; this is the kind of provider/credential plumbing that must not be re-imported.

4. **DevTools DAG animator.** `packages/reactor-devtools` is a localhost visualization (nodes flash on render, dim-pulse on memo-skip, live cost meter). Polished, but Helioy has no equivalent visual surface today; inspiration only.

5. **The fixture/example bundle and replay tarball layout.** Thirteen committed `replay/` state-dirs with offline tests are excellent for *this* project's keyless-proof story but are domain-specific demonstrations, not reusable Helioy machinery.

## 6. Verdict

**Borrow (selectively).** The memo-key skip discipline, the content-addressed published/private store, and the chain-verifiable receipt ledger are clean, well-tested, spec-cited primitives worth lifting into schedule-matters and context-matters. Do not adopt the OpenProse language, the React API skin, or the provider plumbing.

## 7. Why

The deeper signal is that someone has independently arrived at the same instinct underneath Helioy's cognitive-organs thesis: **standing intent that persists across bounded runs, with continuity living in a durable trail rather than a session** (Tenet 3, `spec/00-Tenets.md:40`). OpenProse calls a maintained truth a "world-model" and keeps it on disk passed by pointer; Helioy calls it context/attention/knowledge and keeps it in cm/am. Both treat the database/index as a *derived projection* of canonical truth, both want a deterministic spine wrapping a bounded intelligent core, and both want auditability by construction. The convergence is validation that the architecture Helioy is building is a real category, and Reactor has already solved two hard sub-problems cleanly: how to decide *whether* to spend a model call (fingerprint memoization with no clock and no judge) and how to make the decision trail *checkable after the fact* (sha256-chained receipts). Those are exactly the seams where Helioy's schedule-matters and context-matters are weakest.

## 8. How to apply

- **schedule-matters:** Prototype a fingerprint-gated wake. Before running a scheduled agent job, compute a memo key from the job's contract fingerprint plus the fingerprints of its tracked inputs; if unchanged since the last run, write a cheap "skipped" record and spawn nothing. Lift the shape from `memo/index.ts:135` and the policy/state split from `forecast/index.ts:51`. This turns cron from time-driven into surprise-driven.
- **context-matters:** Evaluate a content-addressed canonical entry store with a published/private split (store.ts:95) where the FTS5/vector index is explicitly a derived projection, and an append-only sha256-chained receipt over supersede/forget so cm's history is tamper-evident (receipt/index.ts:248). This sharpens cm's "what changed and why" without changing its MCP surface.
- **history-matters:** Borrow the chain-verify shape (`verifyReceiptChain`, node-scoped, `prev`-linked) for an auditable command log.
- **helioy-bus / warroom:** Consider Forme-style declared-contract wiring (`forme/index.ts:298`) so agent edges derive from produces/consumes declarations with compile-time acyclicity, rather than hand-wired routing.
- **Do not** import the OpenProse language, the React API vocabulary, the devtools animator, or the `@openai/agents`/OpenRouter substrate. Route any provider work through Helioy's existing factory.
- Optional outreach: single strong author (`irl-dan`), MIT, explicitly invites agent-filed issues and evals (`packages/reactor/EVALS.md`). A thoughtful eval or a "responsibility the harness should keep and doesn't" would be a credible warm contact, given the thesis overlap.

## Sources consulted

- README.md (full), CHANGELOG.md, spec/00-Tenets.md, spec/01-Language.md..04-Evals.md (titles), docs/reactor/v0.1/report.md (referenced)
- packages/reactor/src: memo/index.ts, receipt/index.ts, world-model/store.ts, forme/index.ts, canonicalizer/, cost/index.ts, forecast/index.ts (read/inspected)
- packages/{co,std} contract libraries; std/delivery/email-notifier.prose.md (sample)
- .github/workflows/ (11 workflows), package.json manifests for all five packages
- gh API: stars, forks, license, languages, contributors, first/last commit

## Open questions

- Real-world speedup is unmeasured (benchmarks openly pending). The "cost scales with surprise" claim is architecturally checkable via keyless replay but not yet empirically benchmarked.
- How the semantic `FacetMatcher` behaves in production (the one LLM-adjacent compile step) versus the exact-name default used in tests.
- Whether the receipt model's missing timestamp/actor matters for Helioy's audit needs (Reactor flags this as a v1 gap).
