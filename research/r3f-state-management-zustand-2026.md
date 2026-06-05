---
title: R3F state management with Zustand (mid-2026 best practice)
type: research
tags: [react-three-fiber, zustand, valtio, jotai, three.js, state-management, performance, r3f]
summary: The canonical 2026 architecture for R3F state is a two-tier split — React/Zustand for structural state, refs mutated in useFrame for per-frame state — with Zustand's getState()/subscribe as the bridge between them.
status: active
confidence: high
created: 2026-07-07
updated: 2026-07-07
---

# R3F state management with Zustand (mid-2026 best practice)

**Date:** 2026-07-07
**Method:** deep-research harness — primary docs (r3f.docs.pmnd.rs, zustand.docs.pmnd.rs, valtio.dev), pmndrs GitHub discussions, three.js discourse, npm registry for exact versions. Cross-checked docs against maintainer (drcmda / Paul Henschel) statements.
**Question:** What is the current best-practice architecture for managing state in a React Three Fiber app in 2026, and specifically how should Zustand be used with R3F?

---

## Verdict

**The architecture has not changed in years, and that stability is the finding.** The canonical pattern is a hard two-tier split:

1. **Structural / UI state** (what exists, selected item, config, loaded dataset, "paused") → React state or a **Zustand** store, driving reconciliation.
2. **Transient / per-frame state** (position, rotation, uniforms, camera smoothing, physics, interpolation) → **refs mutated inside `useFrame`**, never React state.

Zustand is the default and near-universal choice for tier 1 in R3F apps, for one reason that is specific to this domain: its `getState()` escape hatch lets tier-2 frame code **read** tier-1 state at 60fps without subscribing, and its `subscribe(selector, cb)` lets you **push** into refs without re-rendering. That "transient update" capability is the whole reason pmndrs built Zustand alongside R3F in the first place. Valtio and Jotai are viable and pmndrs-blessed alternatives with narrower sweet spots (below).

The single most repeated maintainer line, from drcmda on the three.js forum (2024-02-08) and echoed across the docs: **"you do not push frame updates through app/local state."** Do not store per-frame values in any store. Interpolate *from* store values *toward* goals inside the loop, by mutation.

Confidence: **high** on the pattern (stable, documented, maintainer-stated). Medium on the "which alternative when" nuance, since it is preference-driven.

---

## Current versions (npm, verified 2026-07-07)

| Package | Version | Last published |
|---|---|---|
| `@react-three/fiber` | **9.6.1** | 2026-04-28 |
| `@react-three/drei` | **10.7.7** | 2026-02-03 |
| `zustand` | **5.0.14** | 2026-05-28 |
| `valtio` | **2.3.2** | 2026-05-01 |
| `jotai` | **2.20.1** | 2026-06-11 |

Notable version context:
- **R3F v9** is the React 19 compatibility line (v9.0 shipped early 2025). It supports React 19.0–19.2. Caveat from the field: React bumped its internal reconciler at 19.2.x in a way that was not backward-compatible with 19.1.x, so pin React and R3F together. (pmndrs/react-three-fiber issue #3222; drei discussion #2213.)
- **Zustand v5** shipped **2024-10-20**. It is a *maintenance* release with no new features: drops React <18, drops TS <4.5, drops ES5, drops default exports, and — the load-bearing change for R3F — drops the `use-sync-external-store` shim to use React's **native `useSyncExternalStore`**. (pmnd.rs/blog/announcing-zustand-v5.)
- **Valtio v2** (proxy state) and **Jotai v2** are both current and stable.

---

## 1. The central tension: React render loop vs. imperative frame loop

Three.js has its own render loop; React has reconciliation. They run on different clocks. The R3F performance docs state it plainly: *"Threejs has a render-loop, it does not work like the DOM does. Fast updates are carried out in `useFrame` by mutation."* (r3f.docs.pmnd.rs/advanced/pitfalls.)

Why `setState` is the wrong tool for 60fps:
- Each `setState` schedules a React render + reconciliation pass. At 60fps that is 60 reconciliations/second per animated value, plus GC pressure from the objects React allocates. It tanks the frame rate within seconds.
- The frame loop already gives you a `delta`; you do not need React's scheduler to time anything.

The canonical minimal pattern — mutate a ref, no state, no re-render:

```jsx
function Spinner() {
  const meshRef = useRef()
  useFrame((state, delta) => {
    meshRef.current.rotation.y += delta        // mutate directly, refresh-rate independent
  })
  return <mesh ref={meshRef}>{/* ... */}</mesh>
}
```

Rule of thumb (from the pitfalls doc and drcmda's forum answer): **React state for things that change infrequently** (a filter click, a loaded dataset, a selection). **Refs + direct Three.js mutation for things that change every frame** (animation, camera smoothing, physics). Mixing these up is the most common source of R3F performance problems.

---

## 2. Zustand-specific techniques with R3F (the heart of the report)

Zustand is the pmndrs sibling of R3F and is designed for exactly this seam. Two directions cross the React/frame boundary.

### 2a. Reading store state inside `useFrame` via `getState()` (the pull direction)

This is the single most important Zustand+R3F idiom, and it is in the R3F docs verbatim (pitfalls page):

```jsx
// Store holds a GOAL value that changes on user input (infrequent).
const useStore = create((set) => ({
  target: 0,
  setTarget: (target) => set({ target }),
}))

function Follower() {
  const ref = useRef()
  useFrame(() => {
    // Read latest state WITHOUT subscribing — no re-render is ever triggered here.
    ref.current.position.x = useStore.getState().target
  })
  return <mesh ref={ref} />
}
```

`getState()` is a non-reactive read. The component never re-subscribes, so updating `target` 1000×/sec would not cost a single React render. You typically pair this with lerp for smoothing:

```jsx
useFrame((_, delta) => {
  const { target } = useStore.getState()
  ref.current.position.x = THREE.MathUtils.damp(ref.current.position.x, target, 4, delta)
})
```

### 2b. Transient updates via `subscribe` (the push direction)

When you want a callback to fire on store change and mutate a ref directly (bypassing React), use the imperative `subscribe`. Zustand's own "Transient updates" doc: *"The subscribe function allows components to bind to a state-portion without forcing re-render on changes... a drastic performance impact when you are allowed to mutate the view directly."* (zustand.docs.pmnd.rs.)

```jsx
function Rig() {
  const ref = useRef()
  useEffect(() => {
    // subscribe returns an unsubscribe fn — clean it up.
    const unsub = useStore.subscribe((s) => {
      ref.current.position.x = s.target   // mutate on change, no re-render
    })
    return unsub
  }, [])
  return <mesh ref={ref} />
}
```

For selector-scoped subscriptions (fire only when a slice changes), add the **`subscribeWithSelector`** middleware — in v4/v5 the plain `subscribe` no longer takes a selector by default; you opt in:

```jsx
import { subscribeWithSelector } from 'zustand/middleware'

const useStore = create(subscribeWithSelector((set) => ({ target: 0, /* ... */ })))

// now the selector signature is available:
useStore.subscribe((s) => s.target, (target) => { ref.current.position.x = target },
  { fireImmediately: true })
```

(zustand.docs.pmnd.rs/reference/middlewares/subscribe-with-selector.)

### 2c. Selector patterns and `useShallow` (avoid over-subscription)

For tier-1 React rendering, subscribe to the narrowest slice:

```jsx
const count = useStore((s) => s.count)   // re-renders only when count changes
```

When a component needs several fields or a derived object/array, a naive selector returns a **new reference every render**. In **Zustand v5 this is not just a perf smell — it throws `Maximum update depth exceeded`**, because v5 uses native `useSyncExternalStore`, which requires a stable snapshot. The fix is `useShallow`:

```jsx
import { useShallow } from 'zustand/react/shallow'

const { a, b } = useStore(useShallow((s) => ({ a: s.a, b: s.b })))
// or an array:
const ids = useStore(useShallow((s) => Object.keys(s.entities)))
```

This is the number-one v4→v5 migration gotcha (pmnd.rs migration guide; discussion #2763). If you upgraded a working R3F app to Zustand 5 and it now infinite-loops, an object/array selector without `useShallow` is the cause.

### 2d. Storing Three.js object refs (meshes, materials, groups) in a store

**Recommendation: mostly no. Prefer local `useRef`.** The community consensus (three.js discourse thread 61223, drcmda) is: *"user data, API responses, and form inputs live in a store. The 3D scene reads this data but does not own it... actual mesh references should be kept as component-level refs rather than in global state."*

When you genuinely need cross-component access to an object (e.g. a UI panel that must call `.lookAt()` on a shared camera target), storing the ref is acceptable, but with these pitfalls:
- **Staleness/lifecycle:** the stored ref can outlive the mounted object. On unmount, null it out (`set({ obj: null })`) or you hold a detached Three.js object and leak it.
- **Disposal:** R3F auto-disposes geometries/materials/textures when the JSX element unmounts. A ref parked in a store does **not** extend that; but if your store is the last thing holding the object, R3F's automatic disposal may run while the store still points at freed GPU resources. Never dispose manually on an object you handed to R3F unless you took it out of the tree.
- **Serialization:** never persist a store slice holding live Three.js objects (Zustand `persist` middleware will choke / produce garbage). Keep object refs in a separate, non-persisted store or transient slice.
- Store **IDs/handles or plain data**, resolve to objects at the edge, as the safer default.

### 2e. Vanilla store for non-React frame code

For frame loops, workers, or imperative systems that live outside the component tree, create a framework-agnostic store with `createStore` from `zustand/vanilla` and read it with `.getState()` / `.subscribe()` directly:

```js
import { createStore } from 'zustand/vanilla'
export const store = createStore(() => ({ target: 0 }))
// in any imperative loop:
store.getState().target
// bind to React elsewhere with useStore(store, selector) from 'zustand'
```

This is the clean way to share one source of truth between a plain-JS simulation/physics tick and React UI without the store being "a React thing."

### 2f. Zustand v5 status relevant to R3F

- Native `useSyncExternalStore` means Zustand participates correctly in **React 18/19 concurrency** (tearing-safe snapshots). This is a correctness upgrade for R3F v9 (React 19) apps.
- No API change to `getState()` or `subscribe()` — the transient-update patterns above are identical to v4.
- The one behavioral change that bites R3F upgraders is the stricter selector-stability requirement (§2c).

---

## 3. Alternatives and how they compare

All three (Zustand, Jotai, Valtio) are pmndrs libraries, all documented to work with react-three-fiber, and the choice is largely stylistic. The pmndrs framing (docs.pmnd.rs and the community cheatsheet):

- **Zustand** — module/global state, immutable update model, manual render-optimization via selectors. The default for R3F because of `getState()`/`subscribe` transient updates.
- **Jotai** — component-oriented *atomic* state (modeled on `useState`), bottom-up, fine-grained reactivity, no selector boilerplate. Good when state is naturally decomposed per-entity and you want automatic dependency tracking. Note: Jotai has **no direct transient-update equivalent** to Zustand's `subscribe` — you use `store.get(atom)` from a vanilla Jotai store inside `useFrame`, or the `atomWithStore`/subscription patterns (jotai discussion #610). This makes it slightly less ergonomic for the frame-read idiom.
- **Valtio** — proxy/*mutable* update model. You mutate `state.x = 5` directly (feels natural for a scene graph), and `useSnapshot` render-optimizes automatically by tracking which keys a component read. pmndrs recommends it specifically when the mental model of "just mutate the scene state" fits, e.g. deeply nested mutable scene configuration. The rule: **proxies for actions/mutations, snapshots for rendering** (valtio.dev). For frame code, read `store` (the proxy) directly, not `useSnapshot`.

### Decision matrix

| Scenario | Best fit | Why |
|---|---|---|
| Shared app/UI state that frame code must **read** at 60fps | **Zustand** | `getState()` = zero-cost non-reactive read inside `useFrame`; the reason it exists |
| Push store changes into a ref without re-rendering | **Zustand** (`subscribe` / `subscribeWithSelector`) | Purpose-built transient-update API; Valtio/Jotai are clumsier here |
| Only one component animates; no cross-cutting state | **No store — `useFrame` + `useRef`** | A store adds nothing; refs are sufficient and fastest |
| Deeply nested, frequently-mutated scene config; you want "just mutate it" | **Valtio** | Proxy mutation model + automatic read-tracking via `useSnapshot` |
| State decomposes into many small independent per-entity pieces | **Jotai** | Atomic model, automatic dependency graph, no selector wiring |
| Persisted / serializable app config | **Zustand** (`persist`) | Mature middleware; keep object refs out of the persisted slice |
| Physics/worker sim shared with React UI | **Zustand vanilla** (`createStore`) | Framework-agnostic store, one source of truth across the boundary |

Bottom line as of 2026: **Zustand remains the pmndrs-default for R3F**, chosen in the overwhelming majority of R3F starters and examples, precisely because of the transient-update bridge. Valtio is the considered choice when a mutable proxy model matches your scene data; Jotai when your state is naturally atomic. There is no signal in 2026 of pmndrs steering R3F users away from Zustand.

### `useFrame` + refs only — when a store is unnecessary

If the animated value is local to one component and nothing else reads it, skip the store entirely. A ref + `useFrame` is the fastest and simplest path. Reach for a store only when state must be **shared** across components or between the frame loop and the React UI.

### Newer entrants / signals (2026 currency check)

No signals-based library has displaced the pmndrs trio for R3F. React 19's own features (Actions, `useTransition`, `use`) are orthogonal to the frame loop and do not change the transient-update pattern. TC39 Signals remain at proposal stage with no R3F integration. Libraries like Legend State (signals/observables) work with R3F in principle but have no meaningful R3F-specific adoption or pmndrs endorsement as of mid-2026. The frame-loop-vs-render-loop split is a Three.js reality, not a React-version artifact, so signals do not dissolve it.

---

## 4. Performance & correctness mechanics

### Instanced meshes driven from a store
Store the **instance data** (positions/rotations/scales as plain arrays or typed arrays), never the matrices in React state. In `useFrame`, read the data (via `getState()`), write each matrix with a reused dummy `Object3D`, and flag the buffer:

```jsx
const dummy = useMemo(() => new THREE.Object3D(), [])
useFrame(() => {
  const items = useStore.getState().items
  for (let i = 0; i < items.length; i++) {
    dummy.position.set(items[i].x, items[i].y, items[i].z)
    dummy.updateMatrix()
    meshRef.current.setMatrixAt(i, dummy.matrix)
  }
  meshRef.current.instanceMatrix.needsUpdate = true   // required after setMatrixAt
})
```

Pitfalls (r3f docs + discussions): `instancedMesh` needs a fixed max `count`; when the count changes you must force a fresh instance (change the `key`) to avoid a crash. Instancing collapses hundreds of thousands of objects into one draw call. (r3f.docs.pmnd.rs/advanced/scaling-performance; discussion #761, #2206.)

### Avoiding the "store update re-renders the whole scene" trap
- Subscribe to the **narrowest slice** with a selector; wrap multi-field/derived selectors in `useShallow`.
- For per-frame values, do not put them in the store at all — use `getState()`/`subscribe` + ref mutation so zero components re-render.
- Split unrelated concerns into separate stores (or well-scoped slices) so an unrelated update cannot touch a subscribed component.

### Concurrent React / React 19 interaction
- R3F v9 targets React 19; Zustand v5's native `useSyncExternalStore` is **tearing-safe** under concurrent rendering, so store reads stay consistent across a torn render. This is the main reason to be on Zustand ≥5 with R3F ≥9.
- The frame loop itself is outside React's concurrent scheduler; `useFrame` mutations are unaffected by transitions. Use `frameloop="demand"` + `invalidate()` for static/on-input scenes to stop rendering when nothing moves (r3f scaling-performance doc).

### Disposal, memory, ref-lifecycle
- R3F auto-disposes objects removed from the JSX tree. Monitor `renderer.info.memory`; if counts climb, you have a leak.
- Objects parked in a store are **not** part of the tree's disposal accounting — null them on unmount (§2d).
- Reuse allocations (`Vector3`, `Object3D`, `Color`, `Matrix4`) outside the loop via `useMemo`; allocating inside `useFrame` creates GC pressure at 60fps. (pitfalls doc: object-pooling section.)

---

## 5. Ecosystem signals (2026)

- **No architectural shift.** The pitfalls / scaling-performance docs and drcmda's forum guidance from 2024 are still the current advice in mid-2026; the pattern is considered settled.
- **Zustand 5.0.x is the maintained line** (5.0.14, 2026-05-28); the only migration friction for R3F users is the strict-selector / `useShallow` requirement.
- **R3F 9.x** (9.6.1) is the React 19 line; watch React 19.1↔19.2 reconciler pinning.
- **drei 10.x** (10.7.7) is the matching helper set for R3F v9.
- Community "best practices" roundups (e.g. utsubo.com "100 Three.js tips", 2026; various R3F configurator write-ups) all restate the same two-tier split — evidence of consensus rather than churn.

---

## Open questions / watch list

1. **React 19.2+ reconciler churn.** R3F pins to specific React minor lines. Track pmndrs/react-three-fiber issues for the next reconciler-compat bump before upgrading React inside an R3F app.
2. **Zustand v6?** The v5 announcement said "new features will only be added in v5," implying a future v6 for the next breaking change. No v6 as of 2026-07; watch for one that might touch `useSyncExternalStore` internals or selector semantics.
3. **Jotai transient reads.** Whether Jotai gains a first-class Zustand-style `subscribe`-into-ref idiom for R3F (currently the weakest link for the frame-read pattern) — still community-pattern territory (discussion #610).
4. **Signals.** If TC39 Signals or Legend State gains real R3F adoption, the "store read in useFrame" ergonomics could improve; no movement yet.
5. **Valtio v2 in R3F practice.** v2 dropped implicit promise handling (explicit `use`). Confirm no R3F-specific gotchas when a Valtio proxy holds async-loaded scene assets.

---

## Sources

| URL | Type | Angle |
|---|---|---|
| r3f.docs.pmnd.rs/advanced/pitfalls | primary docs | transient updates, refs vs setState, getState() snippet, object pooling |
| r3f.docs.pmnd.rs/advanced/scaling-performance | primary docs | instancing, frameloop=demand, invalidate |
| r3f.docs.pmnd.rs/tutorials/v9-migration-guide | primary docs | R3F v9 / React 19 |
| pmnd.rs/blog/announcing-zustand-v5 | primary blog | v5 breaking changes, native useSyncExternalStore, date 2024-10-20 |
| zustand.docs.pmnd.rs (Transient updates; subscribe-with-selector; migrating-to-v5) | primary docs | subscribe, getState, useShallow, v5 selector rule |
| valtio.dev/docs (useSnapshot; proxy; how-valtio-works) | primary docs | proxy-for-actions/snapshot-for-render rule |
| discourse.threejs.org/t/.../61223 | forum (drcmda, 2024-02-08) | "do not push frame updates through app state"; refs not store |
| github.com/pmndrs/react-three-fiber issues/3222, discussions #761/#2080/#2095/#2206 | GitHub | React 19.2 reconciler, instancing, render-on-demand, external store |
| github.com/pmndrs/zustand discussions #2763, #2103, #2857 | GitHub | v5 default-behaviour change, subscribeWithSelector caveats |
| github.com/pmndrs/jotai discussions #610 | GitHub | Jotai transient-update equivalent |
| npm registry (verified 2026-07-07) | registry | exact versions/dates for all five packages |
| utsubo.com/blog/threejs-best-practices-100-tips (2026) | blog | disposal, renderer.info.memory, consensus restatement |

## Source quality assessment
High confidence on the core pattern and versions: primary pmndrs docs + npm registry + a direct maintainer (drcmda) statement all agree, and the guidance is unchanged over multiple years. Medium confidence on the "which alternative when" nuance — it is preference-driven and pmndrs deliberately declines to pick a single winner. Reddit/r/threejs and X yielded no higher-signal material than the primary docs for this specific question; the authoritative discussion lives in pmndrs GitHub discussions, the three.js discourse, and the docs themselves.
