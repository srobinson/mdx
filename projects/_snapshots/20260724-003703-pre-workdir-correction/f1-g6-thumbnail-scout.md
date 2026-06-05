# G6 Thumbnail Lifecycle Scout

Scope: current `main` at `333c3980e83a652313436a4cb85ea060079db280`, with PR #91 merged.

## Verdict

The original disposal race was a development Strict Mode artifact. It is not reachable through the current application's normal production mount, real unmount, and remount paths.

PR #91 already fixes the reported G6 path. Current main re-arms the provider service after an effect replay, creates the WebGL renderer only after the first thumbnail request reaches an idle slot, and disposes it on a real unmount.

Fix direction: no further production code change for the original `Thumbnail renderer is disposed` symptom. Run the exact production smoke below, then close G6 if it passes. A failure on current main would be a different defect and should be diagnosed from its exact rejection text and lifecycle trace.

## Original root cause

Before PR #91, `ThumbnailServiceProvider` eagerly called `createRenderer` inside its `useState` initializer. Its effect performed no setup work. Its cleanup cleared the cache and disposed the renderer.

The development sequence under root Strict Mode was:

1. React called the state initializer twice. The eager provider allocated two WebGL renderers, while only one service instance survived.
2. React ran the surviving provider effect.
3. Strict Mode ran the extra cleanup cycle against that same preserved service state. Cleanup cleared the cache and called `renderer.dispose()`.
4. React ran the effect setup again. The old setup had no acquisition or rearm step, so the retained service still referenced the disposed renderer.
5. When an initially empty piece later gained a State, `StateThumbnail` called `cache.get(pose)`. The cache reached `createOrthographicThumbnailRenderer::render`, which rejected with `Thumbnail renderer is disposed`.

The empty sequence made the race deterministic because no render was pending when cleanup ran. `createOrthographicThumbnailRenderer::dispose` could therefore mark and dispose the backend immediately.

Owners: `src/components/ui/thumbnail/thumbnailService.tsx::ThumbnailServiceProvider`, `src/thumbnail/thumbnailRenderer.ts::createOrthographicThumbnailRenderer`, `src/thumbnail/thumbnailCache.ts::createStateThumbnailCache`, `src/components/ui/thumbnail/StateThumbnail.tsx::StateThumbnail`.

## Production reachability

React documents the extra Strict Mode setup and cleanup cycle, plus the duplicate state initializer call, as development only behavior: [StrictMode](https://react.dev/reference/react/StrictMode), [useState](https://react.dev/reference/react/useState), and [Synchronizing with Effects](https://react.dev/learn/synchronizing-with-effects).

`src/main.tsx` wraps the app in `StrictMode`, but a production build does not run the extra replay. The first production mount creates one provider state, and its cleanup runs only when that provider actually leaves the tree.

Current real unmount paths are safe:

- Collapsing the dock makes `BottomDock` return the Motion tab, unmounting `ThumbnailServiceProvider`. Reopening mounts a new provider with new state.
- Hiding panels makes `StudioShell` remove the dock footer. Restoring panels mounts a new provider with new state.
- A real root unmount followed by a mount also creates new provider state.
- Preview mode hides the dock with CSS and does not run provider cleanup.

No current production path tears down the effect and later reuses the same provider state. The original provider therefore could not reproduce its Strict Mode failure through a normal real unmount and remount. A future state preserving visibility primitive could introduce that lifecycle shape, but current main now tolerates it.

## What PR #91 changed

`createDeferredThumbnailBackend` now separates the stable cache port from the disposable WebGL renderer:

- The state initializer creates only the deferred wrapper and cache. Duplicate development initializer calls allocate no WebGL context.
- Effect setup calls `retain`.
- Effect cleanup clears the cache and calls `release`.
- The Strict Mode setup after cleanup calls `retain` again on the preserved wrapper.
- `render` first yields through `whenIdle`, rejects while truly released, and lazily creates one renderer otherwise.
- `release` disposes the active renderer and clears the wrapper reference.
- The underlying renderer lets an accepted render finish before its WebGL backend is disposed.

This closes both parts of the old defect: the retained service is usable after replay, and the discarded initializer creates no renderer to leak.

Owners: `src/components/ui/thumbnail/thumbnailService.tsx::createDeferredThumbnailBackend`, `src/components/ui/thumbnail/thumbnailService.tsx::ThumbnailServiceProvider`, `src/thumbnail/thumbnailRenderer.ts::createOrthographicThumbnailRenderer`.

## Evidence

Focused verification on current main:

```text
pnpm exec vitest run tests/stateThumbnail.test.tsx tests/thumbnailRenderer.test.ts tests/thumbnailCache.test.ts

Test Files  3 passed (3)
Tests       15 passed (15)
```

The provider coverage includes:

- an empty mount creates no renderer;
- the first request creates one backend shared by all tiles;
- a real unmount disposes the backend once;
- an empty Strict Mode mount can gain a State later;
- a Strict Mode mount with a tile keeps one live service.

Relevant tests: `tests/stateThumbnail.test.tsx::deferred thumbnail service`, `tests/thumbnailRenderer.test.ts::orthographic thumbnail renderer`, `tests/thumbnailCache.test.ts::State thumbnail cache`.

## Scoped closeout

Run one production build smoke using the real WebGL backend:

1. Start with an empty piece and open Motion.
2. Create the first State and confirm its image replaces the loading placeholder.
3. Collapse Motion, reopen it, and confirm the thumbnail renders again.
4. Hide and restore panels, then confirm the thumbnail renders again.
5. Confirm the console has neither `Thumbnail renderer is disposed` nor `Thumbnail service is released`.

If this passes, close G6 with no patch. If it fails, record the exact error and which transition triggered it. The current wrapper makes those two rejection strings distinguish a stale request after release from the removed disposed renderer path.
