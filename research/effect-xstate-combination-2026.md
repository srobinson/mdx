# Effect + XState combination (mid-2026): who's using it

**Date:** 2026-07-03
**Method:** deep-research harness — 6 search angles, 12 sources fetched, 43 claims extracted, top 8 verified via 3-vote adversarial verification (0 killed), synthesized. 44 agents, ~8 min.
**Question:** Who is combining TypeScript's Effect (effect-ts, Effect 3.x) with XState (v5 statecharts) as of mid-2026? Named companies, example repos, integration libraries, talks, community discussion. Is it common or niche? What bridging patterns? Any official interop stance?

---

## Verdict

**Real but niche, patterns-based, not formalized.** No named company and no documented production deployment surfaced. What exists: one community library, one educator's tutorial corpus, and active leadership-level courtship between the two projects. Confidence high on the concrete artifacts, medium on the "how common" characterization.

---

## Load-bearing artifacts

### 1. `@prb/effect-xstate` — closest thing to an adapter library `[high]`
- npm package by **Paul Razvan Berg** (`@PaulRBerg`, of Sablier / PRBMath). MIT. Description: *"Effect-TS and xState v5 workflow utilities."*
- Ships a **Form Machine, Facilitator Machine, React Hooks, Error Utilities**. `peerDependencies` = `effect`, `xstate`, `@xstate/react`, `react` (confirms XState **v5**). Zero runtime deps.
- The `xstate` subpackage of his `prb-effect` Bun monorepo (siblings: effect-evm, effect-evm-safe, effect-next, effect-solana). 12 versions, created **2025-12-19**, latest v3.0.2 (modified 2026-06-09).
- `npmjs.com/package/@prb/effect-xstate` · `github.com/PaulRBerg/prb-effect/tree/main/xstate`

### 2. `SandroMaglione/getting-started-xstate-and-effect` — reference tutorial repo `[high]`
- Public, **75★, 99.7% TypeScript**. *"Learn how to use all the features of XState in combination with the power of Effect."*
- Audio-player example: `machine.ts` (XState machine) + `effect.ts` (actions as typed Effect values — `onLoad/onPlay/onPause/...` returning `Effect<OnLoadSuccess, OnLoadError>` with `Data`-based tagged errors) + `App.tsx` (React consumer).
- Backed by articles on `sandromaglione.com`, his `typeonce.dev` Effect course, and status as an official Effect Days speaker. De facto lead voice on this pairing.

---

## Official / cross-community signals `[high]`

**David Khourshid** (`@DavidKPiano`, XState creator, Stately.ai CEO) is the connective tissue:
- **Effect Days 2024** talk — *"Effective state machines for complex logic"* at Effect's own conference (YouTube `mZJxGgI7FXU`).
- **Effect Miami #2, 2026-07-14** — headlining with *"Effective State Machines with XState"* (official *This Week in Effect* newsletter, 2026-06-26; Luma reg `luma.com/ly80tuif`). NOTE: as of report date, not yet occurred.
- **XState Discussion #4767** — Khourshid personally responded (Feb 2024) pointing users to Maglione's article, *"we'll definitely have more resources."*

Community framing `[medium — single promo tweet]`: organizer **Ariel Azoulay** (`@ariazou`) pitched the meetup to *"anyone thinking seriously about @EffectTS_, XState, actors, AI systems, agentic loops, and reliable TypeScript."* Shared actor-model vocabulary is where the convergence narrative lives.

---

## The bridging pattern everyone converges on

> XState owns the **statechart / actor topology**. Side-effecting actions are implemented as **typed `Effect` values** — tagged errors, explicit error channels, DI via layers — in a **separate module**. React consumes the machine through `@xstate/react`.

No official Effect-team or XState-team adapter exists. The seam is a convention, not a package contract. `@prb/effect-xstate` is a community effort, not blessed by either core team.

---

## Caveats

- **Time-sensitivity:** Maglione's foundational content is ~2023, **predating Effect 3.x** — demonstrates the pattern, not necessarily current-API idioms. The `@prb` package is recent (Dec 2025), single-author; adoption/maturity unverified.
- **The Miami talk hasn't happened yet** (11 days out from report date).
- **Evidence gap:** no named company, no production deployment, no formal-adapter statement from either core team.

---

## Open questions

1. Any company running Effect + XState in production, or entirely individual-practitioner + educational?
2. Will the 2026-07-14 talk endorse a concrete integration / bridging library?
3. Has Effect core (Michael Arnaldi) or Stately signalled intent for a *formal* adapter, vs. leaving it to `@prb/effect-xstate`?
4. Real adoption of `@prb/effect-xstate` (downloads, dependents) vs. Maglione's hand-rolled action-as-Effect pattern?

---

## Sources

| URL | Quality | Angle |
|---|---|---|
| npmjs.com/package/@prb/effect-xstate | primary | integration libs |
| github.com/PaulRBerg/prb-effect/tree/main/xstate | primary | integration libs |
| github.com/SandroMaglione/getting-started-xstate-and-effect | primary | broad |
| sandromaglione.com/newsletter/state-management-with-xstate-state-machines-and-effect | blog | broad |
| sandromaglione.com/articles/getting-started-with-xstate-and-effect-audio-player | blog | broad |
| effect.website/events/effect-days/speakers/sandro-maglione | primary | practitioner |
| youtube.com/watch?v=mZJxGgI7FXU (Khourshid, Effect Days 2024) | primary | practitioner |
| effect.website/blog/this-week-in-effect/2026/06/26/ | primary | practitioner |
| luma.com/ly80tuif (Effect Miami #2) | primary | practitioner |
| github.com/statelyai/xstate/discussions/4767 | forum | maintainer stance |
| typeonce.dev/article/patterns-for-state-management-with-actors-in-react-with-xstate | blog | maintainer stance |
| x.com/SandroMaglione/status/1723592969842753843 | blog | community |

**Run stats:** 6 angles · 12 sources fetched · 43 claims → 8 verified (8 confirmed, 0 killed) → 5 synthesized findings · 16 URL dupes · 8 budget-dropped · 44 agent calls.

---

## Follow-up (2026-07-03): the four open questions, researched

Second deep-research pass — 47 agents, 15 sources, 57 claims → 7 confirmed / 1 killed. Primary-source metrics (npm download-stats API, GitHub API).

**Q1 — Production adoption?** No named company found. `[medium — absence of evidence]` Both artifacts are individual/non-corporate: `@prb/effect-xstate` sits in Berg's personal monorepo (not under Effect-TS or statelyai orgs); Maglione's repo is a personal tutorial. No engineering-blog case study, job posting requiring both, or company-org repo importing both surfaced. Near-miss: `restate.dev` publishes XState + durable-execution content, but that is XState + Restate, not Effect. Private/unpublished corporate use cannot be disproven.

**Q2 — Will the July 14 talk endorse a bridging library?** Not positioned to. `[high on the abstract]` Announced, not delivered (event July 14; research date July 3). Only published description (Luma `luma.com/ly80tuif`): *"David's talk will explore how state machines can help model behavior more explicitly — from application logic to event-driven systems and agentic loops where clarity, transitions, and control matter."* Zero mention of Effect, bridge, integration, or adapter; no reference to `@prb/effect-xstate`. Framed as a guest meetup talk. Contextual signals (Effect-hosted venue, the "Effective" pun, agentic themes) leave integration relevance an open possibility once delivered.

**Q3 — Official adapter intent (Effect core / Stately)?** None found. `[medium — absence of evidence]` No GitHub issue/discussion, Discord announcement, roadmap, or X statement from Effectful Technologies (Arnaldi) or Stately (Khourshid) signalling intent to build or bless a formal adapter. `@prb/effect-xstate` is outside both orgs under Berg's personal npm scope — community, not official.

**Q4 — Real adoption metrics.** Both near-individual scale:

| Artifact | Metric | Value |
|---|---|---|
| `@prb/effect-xstate` | npm downloads, week 2026-06-26→07-02 | **92** (daily 13+31+15+8+0+15+10) |
| | last month | **669** (~13/day) — likely CI/mirror/bot-inflated |
| | version / maintainers | v3.0.2 / **1** (Berg) |
| Maglione `getting-started-xstate-and-effect` | stars / forks / watchers | **75 / 0 / 4** |
| | published to npm? | **No** — `"private": true` |
| | deps | xstate 5.31.1 + **effect 4.0.0-beta.66** |
| | pattern | XState actions run Effect via `.pipe(Effect.runPromise)` / `Effect.runSync` |

Genuine human usage of `@prb/effect-xstate` is plausibly below 92/week once bots are discounted. Maglione's repo carries more mindshare but ships no installable package — the pattern travels by copy, not dependency.

**Revision to first report:** Maglione's repo depends on **effect 4.0.0-beta.66** (pushed 2026-05-21), not the ~2023 Effect 3.x flagged earlier as stale — the pattern is kept current against Effect 4.x beta. **Killed claim (1-2):** that the newsletter gave "no elaboration" on the talk (refuted; the Luma page carries the one-line abstract).

### Still open after this pass
- Will the delivered July 14 talk actually demonstrate an Effect↔XState integration?
- Any private/unpublished corporate deployments invisible to npm/GitHub/blogs?
- Any explicit maintainer issue where an official adapter was declined/deferred, vs. never raised?
- Does `@prb/effect-xstate` reaching v3.0.2 reflect real internal use (Sablier/PRBMath ecosystem) or automated monorepo version bumps?

**Follow-up run stats:** 6 angles · 15 sources fetched · 57 claims → 8 verified (7 confirmed, 1 killed) → 5 synthesized findings · 11 URL dupes · 9 budget-dropped · 47 agent calls.

---

## Mechanics (2026-07-03): the actions-as-Effect seam

Single deep-research subagent, first-party source verified via `gh api` across Maglione's three app variants, `@prb/effect-xstate`, and a newly-found `typeonce-dev/effect-xstate`. The pattern is an **interface between two runtimes**: XState owns *when* (transitions, actor lifecycle), Effect owns *how* (typed errors, layers, fibers). The "seam" is where an `Effect` gets *run*; error flow, cancellation, and DI are all determined by how you cross it.

### Canonical seam
Effects are typed values in a separate module (`R = never`, no runtime needed); the machine runs them in `setup({ actions })`:

```ts
// effect.ts — tagged error, no runtime here
class OnLoadError extends Data.TaggedError("OnLoadError")<{ message: string }> {}
export const onLoad = (...): Effect.Effect<OnLoadSuccess, OnLoadError> => Effect.gen(...)

// machine.ts — THE SEAM
onLoad: assign(({ self }, { audioRef }) =>
  onLoad({ audioRef }).pipe(
    Effect.tap(()    => Effect.sync(() => self.send({ type: "loaded" }))),   // success → event
    Effect.tapError(({message}) => Effect.sync(() => self.send({ type: "error", params:{message} }))),
    Effect.catchTag("OnLoadError", ({ context }) => Effect.succeed(context)),// MUST collapse E channel
    Effect.runSync))                                                          // else runSync throws into XState
```

### Four variants, ranked by how well they respect XState

| Variant | Boundary call | XState-aware? | Fiber interrupt on stop? |
|---|---|---|---|
| Effect-in-plain-action (Maglione audio-player) | `.pipe(Effect.runPromise/runSync)` | No — fire-and-forget | No — lost |
| Effect-in-`fromPromise`-actor (`@prb/effect-xstate`) | `fromPromise(() => Effect.runPromise(...))` | Yes — `invoke.onDone/onError` | No — lost |
| `fromPromise` + `ManagedRuntime` (Maglione todo-sync) | `Runtime.runPromise(...)`, runtime built once at module scope | Yes | No — lost |
| **Custom `ActorLogic`** (`@typeonce/effect-xstate`) | `Effect.runForkWith(services)` + fiber in WeakMap | Yes — genuine actor logic | **Yes — preserved** |

### Fiber-interruption verdict (the load-bearing finding)
`runPromise`/`runSync` hand back a Promise/value and detach — when XState stops the actor, the Effect fiber runs to completion; structured concurrency is severed. Only `@typeonce/effect-xstate`'s `fromEffect` (`src/from-effect.ts`) fixes it: `start` does `Effect.runForkWith(services)` and stashes the fiber in a WeakMap keyed by `actorScope.self`; `transition` on `event.type === "xstate.stop"` calls `fibers.get(self)?.interruptUnsafe()`. **XState cancellation maps to `Fiber.interrupt` only when you `runFork` and hook the stop lifecycle — never with `runPromise`.**

### Error-channel handling — two idioms
- **In actions:** catch with `Effect.tapError` / `Effect.catchTag`, re-emit as an XState event via `self.send({ type: "error" })`. `catchTag` must collapse the `E` channel before `runSync` or it throws into XState's executor.
- **In actors:** let the Effect fail — rejected promise / `Exit.Failure` surfaces as native `invoke.onError` with `event.error`. `@prb` reads `event.error.message`, adds an `isUserRejectedError` predicate routing wallet-cancels back to `initial` instead of `failure`.

### Criticisms / gotchas (thin online; grounded in code)
- **Redundancy** — XState actions/actors/invoke already are a declarative effect system (Khourshid's Effect Days 2024 thesis); two overlapping runtimes. *(Inferred from his position, not a direct quote — flagged.)*
- **`runSync` footgun** — throws synchronously into XState unless the error channel is collapsed first.
- **Untracked async** — `runPromise` in an action is fire-and-forget; the chart can't await or cancel it. Hence actor-wrapping is idiomatic in v5.
- **No official adapter** — Discussion #4767 has no pattern, only Khourshid linking Maglione's article; on 2025-11-29 he told PaulRBerg he still hasn't written official docs.

### New artifact (missed by landscape passes)
`@typeonce/effect-xstate` (`typeonce-dev/effect-xstate`) — the only library providing genuine XState actor logic (`fromEffect`/`fromStream`/`fromAtom`) wrapping an Effect fiber with proper interruption; DI via `xstateRuntime(Atom.runtime(Layer))` bridged through a runtime-context WeakMap. Effect-4-beta, ~2★, single-author, pre-1.0. The technically-correct approach the popular tutorials do not use.

**Flagged unverified:** `typeonce.dev` article returned 403 (prose not quotable); no direct Khourshid quote on the "two effect systems" critique exists online.

### Mechanics sources
- `SandroMaglione/getting-started-xstate-and-effect` — `apps/audio-player-react/src/{effect,machine}.ts`, `apps/audio-player-effect-xstate/src/{machine.ts,services/media-player.ts}`, `apps/todo-sync-reactivity/src/{runtime,sync-machines}.ts` (xstate 5.31.1 + effect 4.0.0-beta.66).
- `typeonce-dev/effect-xstate` — `src/{from-effect,runtime,runtime-context}.ts`.
- `PaulRBerg/prb-effect` — `xstate/src/machines/form.ts`, `xstate/src/errors/types.ts`.
- `github.com/statelyai/xstate/discussions/4767` (christophe-g / davidkpiano Feb 2024; PaulRBerg / davidkpiano exchange 2025-11-29).
