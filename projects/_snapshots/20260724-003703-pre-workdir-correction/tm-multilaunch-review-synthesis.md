# `launch_batch` v1 — peer review synthesis

Date: 2026-07-21  
Inputs: `tm-multilaunch-design-v1.md` + reviews opus / gpt (Codex) / grok  
Role: faithful synthesis for Stuart. Conflicts shown, not resolved.

Governing authority: `LAUNCH-CONTRACT.md`. Baseline reviewers used: `feat/multi-launch` @ `8c51797e…`.

---

## 1. VOTE TABLE

| Reviewer | Canvas-placement verdict | One-line core rationale |
| --- | --- | --- |
| **opus** | **A** (client placement; defer B; **reject hybrid**) | Canvas is presentation, not batch identity; batch-as-unit is already `dispatch_id`; server `canvas_id` is a lonely half-feature until general pane membership is server-truth. |
| **gpt** (Codex) | **Hybrid** | Twin clients + `canvas_ref` on the candidate require an enforceable affinity tag; pure A fails the draft’s own three-axis / twin-client claim; full B (server pane ownership) is out of L0. |
| **grok** | **Hybrid** | Same: pure A with `canvas_ref` on the profile shape is multi-client fiction; hybrid is optional create→view tag + client panes; pure A is only honest if `canvas_ref` is **removed** from L0. |

**Tally:** A = 1 · B = 0 · hybrid = 2  
**Full server pane ownership (deep B):** none recommend for v1.

---

## 2. UNANIMOUS FINDINGS

All three agree on these claims (wording differs; substance shared).

| # | Claim | Concrete fix | Raised by |
| --- | --- | --- | --- |
| U1 | **`canvas_ref` must not ride as an ignored field inside a durable, server-bound profile/candidate shape.** Either the server honors placement (affinity) or placement is a **client-side plan** post-receipt — not a field the server receives and ignores. | **opus:** split server candidate (model/effort/prompt/worktree) from client placement plan; drop `canvas_ref` from profile item. **gpt/grok:** if hybrid, map validated `canvas_id` at mint; if pure A, **remove** `canvas_ref` from L0 candidate/profile. | all three |
| U2 | **Draft is silent on `LAUNCH-CONTRACT.md` sealed workspace snapshot** (“candidate key + one sealed workspace snapshot + optional evaluation artifacts”). L0 as written reuses live `Worktree` / workdir without including snapshot or recording a deviation. | Record one posture: fold snapshot into L0, **or** explicit thin-foundation deviation (live worktree; `workspace_snapshot_id` unset) + note eval-fairness dependency deferred. | all three |
| U3 | **Candidate identity must thread ledger → gateway idempotency → (audit / delivery) → restart-replay story.** Today Python ledger is `(owner, dispatch_id)` process-resident; gateway keys `(owner, idempotency_key)` with control plane sending `dispatch_id`; equal candidates collapse / unequal conflict without `candidate_key`. | Extend ledger to `(owner, dispatch_id, candidate_key)`; candidate-scoped gateway key; **gpt:** also audit (`(actor, verb, dispatch_id)` collapse risk) + durable replay or recorded contract deviation; **grok:** call 2-tuple extension L0 work, not already-true. | all three (opus via locked D2 + ledger/gateway; gpt/grok with audit/restart detail) |
| U4 | **Core domain map is true:** no run `canvas_id` today; client panes; per-run HOME free via single-launch reuse; Space/Worktree/Canvas in `space.models`. | Keep domain model; fix imprecisions in §4. | all three (confirm) |
| U5 | **Blast-radius non-negotiables stand:** server-minted candidate keys before fanout; no client-minted per-candidate `dispatch_id`; no palette `/v1/runs` N-loop (one control-plane batch transport). | Keep as L0 hard gates. | all three |
| U6 | **Full B (server pane membership / layout ownership / canvas lifecycle ops) is not v1.** | Defer to parallel canvas-layering track. | all three |

---

## 3. THE ONE REAL FORK — canvas placement authority

### Side A — opus: pure A, defer server affinity, reject hybrid

**Strongest form:**

- Separate **batch-as-unit** (`dispatch_id` + `candidate_key`) from **canvas-as-group** (pane placement). The former is already server-owned; the latter is presentation and client-primary today for *every* pane.
- Process-resident runs die on API restart; a server `canvas_id` on the run **does not outlive the run**, so B’s durability pitch is largely null in v1.
- Cross-client canvas membership exists for **no** pane today. Giving batch runs a lonely affinity column is a half-feature; real director→worker drill needs general server pane membership (parallel track).
- “Stop/list the batch” is served by `dispatch_id`, not canvas. “List/stop by canvas” is canvas-layering, not batch L0/L1/L2.
- B is clean-additive later; A does not bake client **identity** authority (D2 already forbids that). Hybrid pays **contract cost** (`canvas_id` into frozen launch facts / `FrozenLaunchSpec` orbit) for near-zero v1 benefit and may pick the **wrong shape** (pane can move; same worktree spans canvases).
- Contract does not list canvas among batch deltas; A is contract-clean on canvas. Snapshot is the separate contract hole.

### Side B — gpt + grok: minimal hybrid now (or pure A only if `canvas_ref` is dropped)

**Strongest form:**

- The draft **locks** three orthogonal axes and **candidate = profile item**, with use cases that include split placement (N→canvas A, M→canvas B) and **twin clients (MCP + ⌘K)**.
- `adoptCapturedRun` / `addCapturedRun` mutate the **active** Zustand canvas only — no target `canvasId` arg. Multi-canvas “adopt receipt i into canvas X” is **not** free reuse; activity reconciler also dumps service runs into whichever canvas is active (`capturedRunAdoption` / `SessionCanvasRoute`).
- MCP has **no** `adoptCapturedRun`. Under pure A, MCP batch receipts are unplaced until some browser adopts — into **its** active canvas, not the candidate’s intended `canvas_ref`. Pure A implements only “palette places into the open canvas.”
- If `canvas_ref` ships on the L0/profile shape without server binding, profiles freeze placement intent as fiction; later B must redefine intent vs fact, migrate profiles, and unwind “client placement is authority” tests/docs. That is the **expensive-to-unwind** path.
- Hybrid: optional validated `canvas_id` affinity create → durable launch facts / receipt / view (and gpt: activity); client remains pane/layout authority; **no** server pane table; filters optional/deferred. Fallback both name: pure A **plus** remove `canvas_ref` from L0 shape is honest; pure A **with** `canvas_ref` is not.

### Single product question this reduces to

> **Is director / multi-canvas / MCP placement intent a cross-client, server-observable launch fact in L0, or a local view applied after receipts in the launching UI?**

| If you answer… | Then… |
| --- | --- |
| **Server-observable launch fact** | Hybrid (affinity tag; client panes). |
| **Local view only** | Pure A **and** strip `canvas_ref` from server candidate/profile; client placement plan only. |

### WHAT IS LOST by pure client placement (deduped across reviewers)

Accepting pure A (with or without hybrid) means these are **not** server-truth in v1:

1. **Second client / second browser / fresh profile** cannot reconstruct “these runs belong on canvas X” from the server (all three).
2. **MCP / director with no browser** cannot enforce a canvas destination; placement is optional ad hoc later (gpt, grok).
3. **Activity / service-run reconciliation** defaults into the **active** canvas, which may disagree with intended multi-canvas placement (gpt, grok).
4. **Server list / filter / stop-by-canvas** cannot use placement (all three; **opus/gpt/grok agree this is not a batch L0 must-have** — batch unit is `dispatch_id`).
5. If `canvas_ref` remains on the durable profile shape without affinity: **saved profiles encode placement the service does not honor** (all three as inconsistency; gpt/grok as migration poison).

**What is *not* lost (opus emphasis; others partly agree):** batch-as-unit ops via `dispatch_id`+`candidate_key`; same-browser reload of panes via localStorage; per-run HOME isolation; additive path to add `canvas_id` later *if* the field was never promised as honored profile truth.

---

## 4. CODE-GROUNDING

Draft’s core code claims (as reviewers tabulated them):

| Draft claim | opus | gpt | grok |
| --- | --- | --- | --- |
| No `canvas_id` on `CreateManagedRunInput` / `CapturedRunRequest` / `ManagedRunFilters` | **Confirm** | **Confirm** (+ `RuntimeRunView`) | **Confirm** (+ `RuntimeRunView` as doc omission) |
| Client placement seam `adoptCapturedRun` / `addCapturedRun` | **Confirm** | **Confirm with limit** — active store only; no target canvas | **Confirm with limit** — same; multi-canvas adopt non-trivial |
| run→HOME 1:1 at `captured_run_context._prepare_home_and_grant` | **Confirm** | **Confirm** | **Confirm** |
| Space / Worktree / Canvas in `space.models`; panes client-primary | **Confirm** | **Confirm** | **Confirm** |

### Grounding corrections (any reviewer)

| Correction | Who |
| --- | --- |
| `RuntimeRunView` has no canvas (and design’s “run carries workspaceId/owner” is create-path imprecise; view is runId + spaceId + worktreeId + sessionId, not full create input) | grok; gpt notes RuntimeRunView |
| Server `canvas.layout` jsonb ≠ live product pane store (implementers must not write panes there as the product store) | grok |
| `adoptCapturedRun` / reconciler only touch **active** `useCanvasStore` — Option A multi-canvas adopt is overstated | gpt, grok |
| `LaunchLedger` today is **2-tuple** `(owner, dispatch_id)`, process-resident — not yet contract 3-tuple | gpt, grok |
| Audit rows unique on `(actor, verb, dispatch_id)` — N item launches under one dispatch collapse unless batch verb or candidate-scoped audit identity | **gpt only** (material) |
| Contract requires durable launch ledger / replay across restart; reusable maps are process-resident — L0 must close gap or record deviation | **gpt** (primary); grok (receipt durability / batch-as-unit dies on restart) |
| Palette trusted adapter (origin-checked control-plane entry) underweighted relative to scout | **grok** |
| Worktree axis conflates **source selection** vs **isolation policy** (live vs sealed snapshot copy); no snapshot runtime exists | **gpt** |
| Shown `LaunchCandidate` is not full profile shape (omits harness/agent/connection/name/grant/…); need definition vs invocation layers; prompt inheritance needs three states | **gpt** |

**No reviewer refuted** the “no canvas on create path” or “HOME is per-run” claims.

---

## 5. CONDITIONS TO SIGN-OFF

Deduped union. Markers: **[unanimous]** / **[some]**.

| # | Condition | Who |
| --- | --- | --- |
| C1 | **Snapshot posture recorded** — include sealed workspace snapshot in L0 **or** explicit thin-foundation deviation + eval-fairness note (do not ship silent conflict with contract batch sentence). | **[unanimous]** |
| C2 | **`canvas_ref` honesty** — either hybrid affinity so the server honors placement, **or** remove `canvas_ref` from server candidate/profile and keep a client-only placement plan. No ignored field on durable shape. | **[unanimous]** (mechanism differs: opus→A+strip; gpt/grok→hybrid or strip) |
| C3 | **Candidate identity through ledger + gateway** before fanout; no client per-candidate `dispatch_id`; no palette `/v1/runs` N-loop. | **[unanimous]** |
| C4 | **Batch-as-unit = `dispatch_id` (+ `candidate_key`)**, not canvas — state explicitly so canvas is not mismotivated as batch identity. | **[some: opus required; gpt/grok compatible]** |
| C5 | **Placement decision recorded** as hybrid **or** pure A with `canvas_ref` removed (not pure A with profile `canvas_ref`). | **[some: gpt+grok required hybrid-or-strip; opus required A+strip and reject hybrid]** |
| C6 | If hybrid: optional validated `canvas_id` create→receipt/view (gpt: durable facts, activity, target-aware adopt); client keeps panes; no full filter/pane-server in v1 (gpt wants optional filter earlier; grok defers filters). | **[some: gpt+grok]** |
| C7 | If multi-canvas use case stays in v1: **honest multi-cache adopt** (not active-store-only). | **[some: grok; gpt]** |
| C8 | **Audit + restart-replay:** candidate identity through audit/delivery; one ordered batch action or candidate-scoped audit; resolve process-resident ledger gap or record contract deviation. | **[some: gpt primary; grok partial]** |
| C9 | **Schema hygiene before freeze:** profile definition vs invocation; workspace source vs isolation policy; three-state prompt inheritance. | **[some: gpt]** |
| C10 | Design grounding fixes: RuntimeRunView field list; active-store adopt limit; ledger still 2-tuple today. | **[some: grok; gpt overlaps]** |

---

## 6. OPEN QUESTIONS (surfaced, not resolved)

1. **Product call on the fork:** server-observable placement affinity in L0 vs local-only placement (with `canvas_ref` stripped)? (A vs hybrid; full B out.)
2. **Snapshot D1:** contract-complete seal in L0 vs thin live workdir + recorded deviation?
3. **Does use case 3 (split canvases in one batch) stay in v1?** If yes, multi-target adopt algorithm must be specified; if no, placement collapses to “active canvas.”
4. **How durable is “batch as unit” in v1?** Process-resident ledger/runs only, or durable claim/replay/audit as contract text implies?
5. **Does optional `ManagedRunFilters.canvasId` ship with hybrid or wait for canvas-layering?** (gpt lean preserve fact + optional filter; grok defer filter.)
6. **Profile layering depth in L0:** freeze full definition/invocation split + three-state prompts now (gpt), or minimal candidate fields first?
7. **Does hybrid `canvas_id` enter `FrozenLaunchSpec` / `spec_version` surface?** (opus: contract cost / wrong-shape risk; hybrid reviewers: affinity must ride durable launch facts — shape TBD.)
8. **Trusted Canvas→control-plane adapter for ⌘K** — in L0 critical path (scout/grok) or assumed elsewhere?

---

## Scannable bottom line for Stuart

| Topic | Status |
| --- | --- |
| Code map of “no canvas on run, client panes, per-run HOME” | **Unanimous: true** |
| Snapshot contract silence | **Unanimous: must fix doc/scope before ship** |
| Candidate key ledger→gateway | **Unanimous: L0 hard requirement** |
| `canvas_ref` on durable profile without server honor | **Unanimous: invalid** |
| Placement authority A vs hybrid | **Split 1–2** — product question in §3 |
| Full server canvas ownership | **Unanimous: not v1** |

**No synthesis recommendation.** Choose the product answer in §3, then apply C1–C3 at minimum; remaining conditions follow from that choice.
