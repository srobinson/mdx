# Slice 6 — www Space/Worktree launcher scopes + Canvas model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the Spaces model to the React UI: the ⌘K launcher gets real **Space + Worktree** scopes (replacing the disabled Workdir stub), the canvas domain model is re-keyed by a minted **`canvasId`** with a promoted **`defaultWorktreeId`** fallback, spawnable pane refs become **worktree-rooted**, localStorage becomes a per-canvas cache with a one-time legacy import, and `api.ts` speaks **`spaceId`/`worktreeId`** instead of a raw `cwd`/`workspaceId`.

**Architecture:** Pure model functions (commandModel, paneRecords guards, persistence key helpers, the launch-context helper) carry the behaviour and are unit-tested in isolation; the zustand `useCanvasStore` and the React launcher hooks are the thin wiring on top. The canvas store stays a singleton; identity becomes a minted `canvasId` (decoupled from `workspaceHash`), and the persist middleware namespaces localStorage by that id. This slice is **detect/observe only** (the launcher never mutates worktrees) and the Canvas server store is out of scope — localStorage remains the cache.

**Tech Stack:** React 18, zustand (+ `persist` middleware), `@tanstack/react-query`, `@ark-ui/react` combobox, TypeScript, **vitest**, `tsc -b --noEmit`, biome. All commands run from `transport-matters/www/`. **Gate (repo recipe, source of truth):** `just check && just test` — `just check` = `pnpm format` + `pnpm lint:fix` + `pnpm typecheck`; `just test` = `pnpm test`. Targeted single-file runs in the TDD inner loop use `pnpm vitest run <path>`; mid-task `tsc` sweeps use `pnpm typecheck`. Never gate on bare `pnpm typecheck && pnpm test` — it skips `pnpm format` and goes CI-red.

**Binding requirements satisfied (peer-consensus, `transport-matters-spaces--proposal.md`):**
- **R3** — pane worktree-rooting: `worktreeId` required on `terminal` + `captured-run` refs, optional on `resource(url)`; `Canvas.defaultWorktreeId` promoted into the domain model as the spawn fallback. (Tasks A, B)
- **R7** — doc/UX hygiene: the Space scope renders disambiguating chrome so it never reads like the `Canvas gesture modifier: Space` settings row; no "Surface" rename. (Task C)
- **R1/R2** — run-path identity: the www client targets `spaceId`/`worktreeId` and drops `workspaceId` from the run surface. (Task E)
- **Resume anchor** — the `captured-run` ref gains a nullable durable `sessionId?` (Task B), the pane→session-lineage anchor for native resume and internal continuation. The field is persisted now so canvases carry it; populating it on session-bind and the resume behavior are deferred to Slice 7 (no later canvas migration). (Task B)

**Conventions to honour (verified in-tree):**
- Tests: `import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"`. Pure-function tests need no mocks. Store tests call `resetCanvasStoreForTests()` / `useCanvasStore.getState()`. localStorage tests `localStorage.clear()` in `beforeEach`. The api test harness is `stubFetch(body, status)` (`vi.stubGlobal("fetch", …)` returning a `vi.fn()`), asserting `fetchMock).toHaveBeenCalledWith(path, init)`.
- A single test file runs with `pnpm vitest run <path>`; a single case with `pnpm vitest run <path> -t "<name fragment>"`.
- IDs are opaque uuid strings. Bare serialization (no `spc_`/`wkt_`/`cnv_` prefix on the wire); the launcher's row-`value` prefixes (`space:`, `worktree:`) are UI item ids, not identity tags.

**Task order & dependencies:** A → B → C → D → E → F → G.
`A` (identity) unblocks `B` (refs need `defaultWorktreeId`) and `D` (cache needs `canvasId`). `C` (commandModel) is independent. `E` (api) is independent. `F` (wiring) depends on A + C + E. `G` (persistence drop-invalid hardening) depends on B (its test exercises the now-required `worktreeId` guard) and complements D (it makes the one-time legacy import non-destructive for mixed canvases); land it any time after B + D. Each task ends green (`just check && just test`, run from `transport-matters/www/`) and is a self-contained commit.

---

## Task A: Canvas identity — minted `canvasId`, `spaceId`, promoted `defaultWorktreeId`

Re-key the canvas domain model off `workspaceHash` onto a minted `canvasId`, add `spaceId`, and promote `defaultWorktreeId` into the model (R3 fallback). Introduce the shared Space/Worktree DTOs that Tasks C and E reuse.

**Files:**
- Modify: `src/types.ts` (add `SpaceId`, `WorktreeId`, `WorktreeSummary`, `SpaceSummary`)
- Modify: `src/session-canvas/route.ts` (`CanvasLaunchContext` fields + `parseCanvasLaunchContext` + `defaultCanvasId` helper)
- Test: `src/session-canvas/route.test.ts` (create)
- Modify: `src/session-canvas/model/paneRecords.ts` (`CanvasModel` fields)
- Modify: `src/session-canvas/model/canvasStore.ts` (`INITIAL_LAUNCH_CONTEXT`, `createInitialCanvasModel`, `initializeCanvas`)
- Test: `src/session-canvas/model/canvasStore.test.ts` (add cases)
- Modify: `src/session-canvas/components/CanvasSurface.tsx:226` (`state.id` → `state.canvasId`)

- [ ] **Step 1: Add the shared Space/Worktree DTOs to `types.ts`**

Append to `src/types.ts` (these mirror the backend DTOs from Slices 1–3; opaque uuid strings):

```typescript
export type SpaceId = string;
export type WorktreeId = string;

/** A launchable path under a Space (a git worktree, or the lone dir of a plain Space). */
export interface WorktreeSummary {
  worktreeId: WorktreeId;
  spaceId: SpaceId;
  /** Worktree root path. Shown as the row subtitle; never emitted as identity. */
  path: string;
  /** Checked-out branch, or null for detached HEAD / a plain directory. */
  branch: string | null;
  /** The repo's primary checkout (vs. a linked worktree). */
  isPrimary: boolean;
  /** Path no longer exists on disk (mirrors the backend `missing` flag, R4). */
  missing: boolean;
}

/** A project/area, with its worktrees inlined for the launcher's single-vs-multi decision. */
export interface SpaceSummary {
  spaceId: SpaceId;
  /** Project/area display label (repo name or plain-dir basename). */
  label: string;
  /** Git repo (0..n linked worktrees) vs. a plain directory (exactly one). */
  kind: "repo" | "plain";
  worktrees: WorktreeSummary[];
}
```

- [ ] **Step 2: Write the failing test for `defaultCanvasId` + launch-context parsing**

Create `src/session-canvas/route.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { defaultCanvasId, parseCanvasLaunchContext } from "./route";

describe("parseCanvasLaunchContext", () => {
  it("reads space_id, worktree_id, and canvas_id from the query", () => {
    const launch = parseCanvasLaunchContext(
      "?workspace_hash=hash-1&space_id=space-1&worktree_id=wt-1&canvas_id=canvas-1&harness=claude",
    );
    expect(launch).toEqual({
      owner: "local",
      workspaceHash: "hash-1",
      spaceId: "space-1",
      worktreeId: "wt-1",
      canvasId: "canvas-1",
      harness: "claude",
      runId: null,
    });
  });

  it("defaults the new fields to null when absent", () => {
    const launch = parseCanvasLaunchContext("");
    expect(launch.spaceId).toBeNull();
    expect(launch.worktreeId).toBeNull();
    expect(launch.canvasId).toBeNull();
  });
});

describe("defaultCanvasId", () => {
  const base = {
    owner: "local" as const,
    workspaceHash: null,
    spaceId: null,
    worktreeId: null,
    canvasId: null,
    harness: null,
    runId: null,
  };

  it("prefers an explicit canvasId", () => {
    expect(defaultCanvasId({ ...base, canvasId: "canvas-9", spaceId: "space-1" })).toBe("canvas-9");
  });

  it("derives one default canvas per space from spaceId", () => {
    expect(defaultCanvasId({ ...base, spaceId: "space-1" })).toBe("space:space-1");
  });

  it("falls back to the legacy workspaceHash, then direct-local", () => {
    expect(defaultCanvasId({ ...base, workspaceHash: "hash-1" })).toBe("hash-1");
    expect(defaultCanvasId(base)).toBe("direct-local");
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `pnpm vitest run src/session-canvas/route.test.ts`
Expected: FAIL — `defaultCanvasId` is not exported; `parseCanvasLaunchContext` result has no `spaceId`/`worktreeId`/`canvasId`.

- [ ] **Step 4: Extend `CanvasLaunchContext`, the parser, and add `defaultCanvasId`**

In `src/session-canvas/route.ts`, replace the `CanvasLaunchContext` interface and `parseCanvasLaunchContext`, and add `defaultCanvasId`:

```typescript
export interface CanvasLaunchContext {
  owner: "local";
  workspaceHash: string | null;
  spaceId: string | null;
  worktreeId: string | null;
  canvasId: string | null;
  harness: string | null;
  runId: string | null;
}

export function parseCanvasLaunchContext(search: string | URLSearchParams): CanvasLaunchContext {
  const params = typeof search === "string" ? new URLSearchParams(search) : search;
  return {
    owner: "local",
    workspaceHash: valueOrNull(params.get("workspace_hash")),
    spaceId: valueOrNull(params.get("space_id")),
    worktreeId: valueOrNull(params.get("worktree_id")),
    canvasId: valueOrNull(params.get("canvas_id")),
    harness: valueOrNull(params.get("harness")),
    runId: valueOrNull(params.get("run_id")),
  };
}

/**
 * The localStorage cache key id for this launch. A Space's default Canvas is
 * `space:<spaceId>` (one default Canvas per Space); an explicit `canvas_id`
 * overrides; a worktree-less / pre-Spaces launch keeps the legacy `workspaceHash`
 * (or `direct-local`) so existing single-canvas behaviour is preserved.
 */
export function defaultCanvasId(launch: CanvasLaunchContext): string {
  if (launch.canvasId) return launch.canvasId;
  if (launch.spaceId) return `space:${launch.spaceId}`;
  return launch.workspaceHash ?? "direct-local";
}
```

(`valueOrNull` already exists at the bottom of the file — leave it.)

- [ ] **Step 5: Run the test to verify it passes**

Run: `pnpm vitest run src/session-canvas/route.test.ts`
Expected: PASS

- [ ] **Step 6: Write the failing test for the re-keyed `CanvasModel`**

Add to `src/session-canvas/model/canvasStore.test.ts` (inside the top-level describe, alongside the existing store tests):

```typescript
describe("canvas identity (Slice 6)", () => {
  it("mints a default canvasId per space and promotes defaultWorktreeId", () => {
    resetCanvasStoreForTests();
    useCanvasStore.getState().initializeCanvas({
      owner: "local",
      workspaceHash: "hash-1",
      spaceId: "space-1",
      worktreeId: "wt-1",
      canvasId: null,
      harness: null,
      runId: null,
    });

    const state = useCanvasStore.getState();
    expect(state.canvasId).toBe("space:space-1");
    expect(state.spaceId).toBe("space-1");
    expect(state.defaultWorktreeId).toBe("wt-1");
    expect(state.workspaceHash).toBe("hash-1");
  });

  it("falls back to direct-local with no space and no worktree root", () => {
    resetCanvasStoreForTests();
    const state = useCanvasStore.getState();
    expect(state.canvasId).toBe("direct-local");
    expect(state.spaceId).toBeNull();
    expect(state.defaultWorktreeId).toBeNull();
  });
});
```

- [ ] **Step 7: Run the test to verify it fails**

Run: `pnpm vitest run src/session-canvas/model/canvasStore.test.ts -t "canvas identity"`
Expected: FAIL — `state.canvasId` / `state.spaceId` / `state.defaultWorktreeId` are `undefined`.

- [ ] **Step 8: Re-key `CanvasModel` in `paneRecords.ts`**

In `src/session-canvas/model/paneRecords.ts`, add the `SpaceId`/`WorktreeId` import and replace the `CanvasModel` interface:

```typescript
import type { HarnessName, SpaceId, WorktreeId } from "../../types";
```

(merge with the existing `import type { HarnessName } from "../../types";` — make it the single line above.)

```typescript
export interface CanvasModel {
  canvasId: CanvasId;
  owner: "local";
  spaceId: SpaceId | null;
  workspaceHash: string | null;
  /**
   * Promoted into the model (R3): the fallback worktree root for spawnable panes
   * (terminal / captured-run) that carry no explicit worktree of their own.
   */
  defaultWorktreeId: WorktreeId | null;
  cwd: string | null;
  launch: CanvasLaunchContext;
  layout: EngineLayoutState;
  panes: Record<PaneId, PaneRecord>;
}
```

- [ ] **Step 9: Update the store model construction in `canvasStore.ts`**

In `src/session-canvas/model/canvasStore.ts`:

Add the helper import (merge into the existing `../route` import):

```typescript
import { type CanvasLaunchContext, defaultCanvasId } from "../route";
```

Replace `INITIAL_LAUNCH_CONTEXT`:

```typescript
const INITIAL_LAUNCH_CONTEXT: CanvasLaunchContext = Object.freeze({
  owner: "local",
  workspaceHash: null,
  spaceId: null,
  worktreeId: null,
  canvasId: null,
  harness: null,
  runId: null,
});
```

Replace the `initializeCanvas` action body:

```typescript
      initializeCanvas(launch) {
        set((state) => ({
          ...state,
          canvasId: defaultCanvasId(launch),
          spaceId: launch.spaceId,
          defaultWorktreeId: launch.worktreeId,
          launch,
          workspaceHash: launch.workspaceHash,
        }));
      },
```

In `createInitialCanvasModel`, replace the `id`/`workspaceHash` lines of the `model` object so it reads:

```typescript
  const model: CanvasStoreModel = {
    canvasId: defaultCanvasId(launch),
    owner: "local",
    spaceId: launch.spaceId,
    workspaceHash: launch.workspaceHash,
    defaultWorktreeId: launch.worktreeId,
    cwd: null,
    launch,
    layout,
    panes: { [pane.paneId]: pane },
    activeStrategyId,
    bounds: DEFAULT_BOUNDS,
    fitToContent: true,
    params,
    framing: emptyFraming(),
    expandedPaneId: null,
    docked: [],
  };
```

- [ ] **Step 10: Update the one production reader of `state.id`**

In `src/session-canvas/components/CanvasSurface.tsx` line 226, change:

```typescript
  const canvasId = useCanvasStore((state) => state.canvasId);
```

(The `id: canvasId` field of the `ViewerCanvasContext` it builds at line ~169 is unchanged — `ViewerCanvasContext.id` keeps its name and is still fed by this const. `ViewerCanvasContext` is imported by 28 files; renaming its field is deliberately out of scope.)

- [ ] **Step 11: Run the targeted tests to verify they pass**

Run: `pnpm vitest run src/session-canvas/model/canvasStore.test.ts -t "canvas identity"`
Expected: PASS

- [ ] **Step 12: Enumerate the `state.id` reader sweep, then run the gate**

First confirm the rename's blast radius is fully covered — enumerate the canvas-store id readers the way Tasks B/E enumerate their `tsc` sweeps:

```bash
grep -rn "state\.id\b" src --include='*.ts' --include='*.tsx'
```

Expected: exactly one hit — `src/session-canvas/components/CanvasSurface.tsx:226`, the production reader already changed to `state.canvasId` in Step 10. The persist snapshot does NOT partialize the canvas `id` field (`canvasStore.persistence.ts` persists panes/layout, not `id`), and the lab store uses its own model, so the sweep touches no other file. If the grep returns any other hit, change that `state.id` → `state.canvasId`.

Then run the gate from `transport-matters/www/`:

```bash
just check && just test
```

Expected: PASS. (`just check` = `pnpm format` + `pnpm lint:fix` + `pnpm typecheck`; the typecheck pass flags any `.id` read on the canvas store `tsc` can still see.)

- [ ] **Step 13: Commit**

```bash
git add src/types.ts src/session-canvas/route.ts src/session-canvas/route.test.ts \
  src/session-canvas/model/paneRecords.ts src/session-canvas/model/canvasStore.ts \
  src/session-canvas/model/canvasStore.test.ts src/session-canvas/components/CanvasSurface.tsx
git commit -m "feat(canvas): re-key canvas model on minted canvasId with spaceId + defaultWorktreeId (R3)"
```

---

## Task B: Pane-ref worktree-rooting (R3) + durable resume `sessionId` anchor

Make `worktreeId` required on `terminal` + `captured-run` content refs and optional on `resource(url)`; tighten the `isPaneContentRef` guard; root the captured-run spawn path on `Canvas.defaultWorktreeId`. In the same pass, add a nullable durable `sessionId?: string` to the `captured-run` ref alongside `worktreeId`.

**Durable resume anchor (`sessionId`).** This `sessionId` is the durable pane→session-lineage anchor for BOTH native resume (`--resume` claude / `resume` codex) and internal continuation (`parent_session_id`). The FIELD is persisted now so canvases carry it through partialize/serialize and the one-time legacy import (legacy panes simply have it `undefined`); POPULATING it on session-bind and the resume behavior itself are deferred to Slice 7. Persisting it now means no canvas migration is needed later, because the field already exists on every saved captured-run ref.

**Files:**
- Modify: `src/session-canvas/model/paneRecords.ts` (`PaneContentRef` union + `isPaneContentRef`, adds `sessionId?` to `captured-run`)
- Test: `src/session-canvas/model/paneRecords.test.ts` (create; includes the `sessionId` round-trip)
- Modify: `src/session-canvas/model/spawn.ts` (`createCapturedRunRef` requires `worktreeId`)
- Modify: `src/session-canvas/model/canvasStore.ts` (`addCapturedRun` sources `worktreeId` from `defaultWorktreeId`)
- Modify: `src/session-canvas/testUtils.tsx` (`makeCapturedRunRef` sets `worktreeId`)
- Modify (compile sweep, demo/test fixtures): `src/session-canvas/lab/canvasLabStore.ts` + the terminal-ref test fixtures listed in Step 7.

- [ ] **Step 1: Write the failing guard test**

Create `src/session-canvas/model/paneRecords.test.ts`:

```typescript
import { describe, expect, it } from "vitest";
import { isPaneContentRef } from "./paneRecords";

describe("isPaneContentRef — worktree-rooting (R3)", () => {
  it("requires worktreeId on a terminal ref", () => {
    expect(isPaneContentRef({ kind: "terminal", owner: "local", worktreeId: "wt-1" })).toBe(true);
    expect(isPaneContentRef({ kind: "terminal", owner: "local", label: "T" })).toBe(false);
  });

  it("requires worktreeId on a captured-run ref", () => {
    expect(
      isPaneContentRef({
        kind: "captured-run",
        owner: "local",
        provider: "claude",
        runKey: "claude:1",
        worktreeId: "wt-1",
      }),
    ).toBe(true);
    expect(
      isPaneContentRef({
        kind: "captured-run",
        owner: "local",
        provider: "claude",
        runKey: "claude:1",
      }),
    ).toBe(false);
  });

  it("treats worktreeId as optional on a resource(url) ref", () => {
    expect(isPaneContentRef({ kind: "resource", owner: "local", source: "url", url: "https://x" })).toBe(true);
    expect(
      isPaneContentRef({
        kind: "resource",
        owner: "local",
        source: "url",
        url: "https://x",
        worktreeId: "wt-1",
      }),
    ).toBe(true);
    expect(
      isPaneContentRef({ kind: "resource", owner: "local", source: "url", url: "https://x", worktreeId: 7 }),
    ).toBe(false);
  });

  it("round-trips a captured-run ref with and without sessionId (Slice 6 resume anchor)", () => {
    const base = {
      kind: "captured-run" as const,
      owner: "local" as const,
      provider: "claude" as const,
      runKey: "claude:1",
      worktreeId: "wt-1",
    };
    // Legacy pane: no sessionId. Round-trips clean and stays undefined.
    const legacy = JSON.parse(JSON.stringify(base));
    expect(isPaneContentRef(legacy)).toBe(true);
    expect(legacy.sessionId).toBeUndefined();
    // Bound pane: sessionId persists through serialize and passes the guard.
    const bound = JSON.parse(JSON.stringify({ ...base, sessionId: "sess-7" }));
    expect(isPaneContentRef(bound)).toBe(true);
    expect(bound.sessionId).toBe("sess-7");
    // A non-string sessionId is rejected.
    expect(isPaneContentRef({ ...base, sessionId: 7 })).toBe(false);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pnpm vitest run src/session-canvas/model/paneRecords.test.ts`
Expected: FAIL — the guard currently accepts a terminal/captured-run ref without `worktreeId`.

- [ ] **Step 3: Confirm no production terminal-ref site, then update the `PaneContentRef` union + guard**

Making `worktreeId` REQUIRED on `terminal` refs is safe only if no production code constructs a terminal `PaneContentRef` (only the lab + tests should). Confirm with one grep — a `PaneContentRef` terminal literal carries `owner` (the `DropTarget` terminal literal does not, so this targets only the ref):

```bash
grep -rn 'kind: "terminal", owner' src --include='*.ts' --include='*.tsx' | grep -vE '\.test\.|/lab/'
```

Expected: no hits. The only runtime terminal-ref construction is the lab demo (`canvasLabStore.ts`, fixed in Step 9). If any other production site appears, it needs a `worktreeId` source before this field becomes required — resolve that first.

In `src/session-canvas/model/paneRecords.ts`, change the three variants in `PaneContentRef` (leave the others untouched):

```typescript
  | { kind: "resource"; owner: "local"; source: "url"; url: string; worktreeId?: string }
```

```typescript
  | { kind: "terminal"; owner: "local"; label?: string; worktreeId: string }
  | {
      kind: "captured-run";
      owner: "local";
      provider: HarnessName;
      runKey: string;
      label?: string;
      // Named runtime template this run launched under. Absent → NATIVE launch.
      // Persisted on the ref so a detach/restore re-attaches under the same template.
      runtimeTemplate?: string;
      // Worktree root this run is captured under (R3). Required: a captured run
      // must resolve a cwd, so it can never be worktree-less.
      worktreeId: string;
      // Durable pane→session-lineage anchor for native resume (--resume / resume)
      // and internal continuation (parent_session_id). Persisted now so canvases
      // carry it; populated on session-bind in Slice 7. Legacy panes: undefined.
      sessionId?: string;
    };
```

In `isPaneContentRef`, update the `resource` url branch, the `terminal` case, and the `captured-run` case:

```typescript
    case "resource":
      if ("source" in value) {
        return (
          (value.source === "path" && typeof value.path === "string") ||
          (value.source === "url" &&
            typeof value.url === "string" &&
            isOptionalString(value.worktreeId))
        );
      }
      return typeof value.sessionId === "string" && typeof value.resourceId === "string";
```

```typescript
    case "terminal":
      return isOptionalString(value.label) && typeof value.worktreeId === "string";
    case "captured-run":
      return (
        isHarnessName(value.provider) &&
        typeof value.runKey === "string" &&
        isOptionalString(value.label) &&
        isOptionalString(value.runtimeTemplate) &&
        typeof value.worktreeId === "string" &&
        isOptionalString(value.sessionId)
      );
```

- [ ] **Step 4: Run the guard test to verify it passes**

Run: `pnpm vitest run src/session-canvas/model/paneRecords.test.ts`
Expected: PASS

- [ ] **Step 5: Write the failing test for the rooted captured-run spawn**

Add to `src/session-canvas/model/canvasStore.test.ts` (`addCapturedRun` already exists on the store):

```typescript
describe("addCapturedRun roots on defaultWorktreeId (Slice 6)", () => {
  it("stamps the canvas defaultWorktreeId onto the captured-run ref", () => {
    resetCanvasStoreForTests();
    useCanvasStore.getState().initializeCanvas({
      owner: "local",
      workspaceHash: null,
      spaceId: "space-1",
      worktreeId: "wt-7",
      canvasId: null,
      harness: null,
      runId: null,
    });

    const paneId = useCanvasStore.getState().addCapturedRun("claude");
    const ref = useCanvasStore.getState().panes[paneId]?.contentRef;
    expect(ref).toMatchObject({ kind: "captured-run", provider: "claude", worktreeId: "wt-7" });
  });

  it("throws when no worktree root is available", () => {
    resetCanvasStoreForTests();
    expect(() => useCanvasStore.getState().addCapturedRun("claude")).toThrow(
      /worktree/i,
    );
  });
});
```

- [ ] **Step 6: Run it to verify it fails**

Run: `pnpm vitest run src/session-canvas/model/canvasStore.test.ts -t "addCapturedRun roots"`
Expected: FAIL — `createCapturedRunRef` does not yet take a `worktreeId`; the ref has no `worktreeId`.

- [ ] **Step 7: Require `worktreeId` in `createCapturedRunRef` and root `addCapturedRun`**

In `src/session-canvas/model/spawn.ts`, change `createCapturedRunRef` (insert `worktreeId` as the second positional, before `label`):

```typescript
export function createCapturedRunRef(
  provider: HarnessName,
  worktreeId: string,
  label?: string,
  runtimeTemplate?: string,
): CapturedRunRef {
  return {
    kind: "captured-run",
    owner: "local",
    provider,
    runKey: createCapturedRunKey(provider),
    worktreeId,
    ...(label === undefined ? {} : { label }),
    ...(runtimeTemplate === undefined ? {} : { runtimeTemplate }),
  };
}
```

In `src/session-canvas/model/canvasStore.ts`, replace `addCapturedRun`:

```typescript
      addCapturedRun(provider, runtimeTemplate) {
        const worktreeId = get().defaultWorktreeId;
        if (worktreeId === null) {
          throw new Error("Cannot spawn a captured run without a rooted worktree");
        }
        const ref = createCapturedRunRef(
          provider,
          worktreeId,
          harnessLabel(provider),
          runtimeTemplate,
        );
        return get().spawnPane(ref, { focus: true });
      },
```

In `src/session-canvas/testUtils.tsx`, update `makeCapturedRunRef` so its returned ref carries a `worktreeId` (default `"wt-test"`, overridable). Read the current factory at line 38 and add `worktreeId` to the returned object, e.g.:

```typescript
export function makeCapturedRunRef(
  runKey = "claude:test",
  provider: HarnessName = "claude",
  worktreeId = "wt-test",
) {
  return { kind: "captured-run", owner: "local", provider, runKey, worktreeId } as const;
}
```

(Keep whatever existing parameter names the factory already uses; only add the `worktreeId` field. If callers in `canvasStore.test.ts` / `capturedRunStore.test.ts` rely on a fixed shape, the added field is additive and safe.)

- [ ] **Step 8: Run the rooted-spawn test to verify it passes**

Run: `pnpm vitest run src/session-canvas/model/canvasStore.test.ts -t "addCapturedRun roots"`
Expected: PASS

- [ ] **Step 9: Compile sweep — make the required field type-check across demo/test fixtures**

Run: `pnpm typecheck`

`tsc` will flag every `{ kind: "terminal", … }` and captured-run literal that now lacks `worktreeId`. These are the demo lab + test fixtures (the only production terminal site is the lab; production captured-run refs go through `createCapturedRunRef`). Fix each:

1. `src/session-canvas/lab/canvasLabStore.ts` — at the top of the file add `const LAB_WORKTREE_ID = "lab";` and change the line 147 literal to `{ kind: "terminal", owner: "local", label, worktreeId: LAB_WORKTREE_ID }`.
2. Add `worktreeId: "wt-1"` (any literal) to each terminal/captured-run ref literal `tsc` reports in these files:
   - `src/session-canvas/lab/canvasLabStore.test.ts`
   - `src/session-canvas/lab/canvasLabStore.persistence.test.ts`
   - `src/session-canvas/lab/CanvasLabRoute.test.tsx`
   - `src/session-canvas/components/PaneDock.test.tsx`
   - `src/session-canvas/viewers/registry.test.ts`
   - `src/session-canvas/viewers/terminal/TerminalPane.test.tsx`
   - `src/session-canvas/persistence/canvasPanePersistence.test.ts`
   - `src/session-canvas/dnd/canvasDrop.test.ts`

   (The DnD `dropTargetStore` literals `{ kind: "terminal"; paneId; label }` are a **different** type — `DropTarget`, not `PaneContentRef` — and must NOT be touched.)

Re-run `pnpm typecheck` until clean.

- [ ] **Step 10: Run the gate to verify nothing regressed**

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS

- [ ] **Step 11: Commit**

```bash
git add src/session-canvas/model/paneRecords.ts src/session-canvas/model/paneRecords.test.ts \
  src/session-canvas/model/spawn.ts src/session-canvas/model/canvasStore.ts \
  src/session-canvas/model/canvasStore.test.ts src/session-canvas/testUtils.tsx \
  src/session-canvas/lab src/session-canvas/components/PaneDock.test.tsx \
  src/session-canvas/viewers/registry.test.ts src/session-canvas/viewers/terminal/TerminalPane.test.tsx \
  src/session-canvas/persistence/canvasPanePersistence.test.ts src/session-canvas/dnd/canvasDrop.test.ts
git commit -m "feat(canvas): require worktreeId on spawnable pane refs, root captured runs on defaultWorktreeId (R3)"
```

---

## Task C: Launcher Space + Worktree scopes (R7)

Replace the disabled Workdir `buildDeferredRows("Workdir")` stub with real **Space** rows (Workdir scope) and a **Worktree** sub-scope, add the `select-worktree` leaf command, and thread a per-frame `param` through the nav grammar so the worktree sub-scope knows its Space. All changes here are pure functions in `commandModel.ts` — fully unit-tested.

**Files:**
- Modify: `src/session-canvas/launcher/commandModel.ts`
- Test: `src/session-canvas/launcher/commandModel.test.ts` (add cases)

- [ ] **Step 1: Write the failing tests for the new scopes + nav param**

Add to `src/session-canvas/launcher/commandModel.test.ts`. First extend the existing `baseInputs` helper (find it near the top of the file) so it supplies the two new `ScopeRowInputs` fields — add these into its default object:

```typescript
    spaces: [],
    activeWorktreeId: null,
```

Then add this block:

```typescript
import type { SpaceSummary } from "../../types";

const repoSpace: SpaceSummary = {
  spaceId: "space-repo",
  label: "transport-matters",
  kind: "repo",
  worktrees: [
    { worktreeId: "wt-main", spaceId: "space-repo", path: "/p/tm", branch: "main", isPrimary: true, missing: false },
    { worktreeId: "wt-feat", spaceId: "space-repo", path: "/p/tm-feat", branch: "feat/x", isPrimary: false, missing: false },
  ],
};

const plainSpace: SpaceSummary = {
  spaceId: "space-dir",
  label: "scratch",
  kind: "plain",
  worktrees: [
    { worktreeId: "wt-only", spaceId: "space-dir", path: "/p/scratch", branch: null, isPrimary: true, missing: false },
  ],
};

describe("Workdir scope — Space rows (R7)", () => {
  it("lists one row per Space, never titled the bare word 'Space'", () => {
    const rows = buildScopeRows("workdir", baseInputs({ spaces: [repoSpace, plainSpace] }), "");
    expect(rows.map((row) => row.value)).toEqual(["space:space-repo", "space:space-dir"]);
    expect(rows.map((row) => row.title)).toEqual(["transport-matters", "scratch"]);
    // R7: no Space row collides with the settings "Canvas gesture modifier: Space" row.
    expect(rows.some((row) => row.title.includes("gesture modifier"))).toBe(false);
    expect(rows.every((row) => row.group === "Workdir")).toBe(true);
  });

  it("a multi-worktree Space descends into the worktree sub-scope", () => {
    const rows = buildScopeRows("workdir", baseInputs({ spaces: [repoSpace] }), "");
    expect(rows[0]?.action).toEqual({ kind: "enter", scope: "worktree", param: "space-repo" });
    expect(rows[0]?.subtitle).toBe("2 worktrees");
  });

  it("a single-worktree Space selects directly (skips the sub-step)", () => {
    const rows = buildScopeRows("workdir", baseInputs({ spaces: [plainSpace] }), "");
    expect(rows[0]?.action).toEqual({
      kind: "command",
      command: { kind: "select-worktree", spaceId: "space-dir", worktreeId: "wt-only" },
    });
  });

  it("shows a quiet placeholder when no spaces are detected", () => {
    const rows = buildScopeRows("workdir", baseInputs({ spaces: [] }), "");
    expect(rows).toHaveLength(1);
    expect(rows[0]?.disabled).toBe(true);
    expect(rows[0]?.value).toBe("status:workdir-empty");
  });
});

describe("Worktree sub-scope rows", () => {
  it("lists the worktrees of the Space named by the nav param", () => {
    const rows = buildScopeRows("worktree", baseInputs({ spaces: [repoSpace], activeWorktreeId: "wt-main" }), "", "space-repo");
    expect(rows.map((row) => row.value)).toEqual(["worktree:wt-main", "worktree:wt-feat"]);
    expect(rows[0]?.trailing).toBe("Current");
    expect(rows[1]?.action).toEqual({
      kind: "command",
      command: { kind: "select-worktree", spaceId: "space-repo", worktreeId: "wt-feat" },
    });
  });

  it("disables a missing worktree and surfaces a fallback for an unknown space", () => {
    const missing: SpaceSummary = {
      ...repoSpace,
      worktrees: [{ ...repoSpace.worktrees[0]!, missing: true }],
    };
    const rows = buildScopeRows("worktree", baseInputs({ spaces: [missing] }), "", "space-repo");
    expect(rows[0]?.disabled).toBe(true);
    expect(rows[0]?.action).toBeUndefined();

    const unknown = buildScopeRows("worktree", baseInputs({ spaces: [] }), "", "nope");
    expect(unknown[0]?.value).toBe("status:worktree-missing");
  });
});

describe("nav param threading", () => {
  it("pushFrame stamps the new frame with the param", () => {
    const stack = pushFrame([createScopeNavFrame("workdir")], "worktree", "space:space-repo", "space-repo");
    expect(topFrame(stack)).toEqual({ scope: "worktree", query: "", highlightedValue: undefined, param: "space-repo" });
  });
});
```

(Ensure the test file imports `buildScopeRows`, `createScopeNavFrame`, `pushFrame`, `topFrame` — most already are; add any missing names to the existing import from `./commandModel`.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/session-canvas/launcher/commandModel.test.ts -t "Workdir scope"`
Expected: FAIL — `select-worktree` command, the `worktree` scope, `buildScopeRows` param, and `NavFrame.param` don't exist; `ScopeRowInputs` has no `spaces`.

- [ ] **Step 3: Add the `worktree` scope, the `select-worktree` command, and the `param`-aware nav frame**

In `src/session-canvas/launcher/commandModel.ts`:

Add `WorktreeSummary`, `SpaceSummary` and `locatorTail` to the imports:

```typescript
import { CAPTURED_RUN_PROVIDERS, harnessLabel, locatorTail } from "../model/paneRecords";
import type { HarnessName, RuntimeTemplateHarness, RuntimeTemplateSummary, RuntimeTemplateVendor, SpaceSummary, WorktreeSummary } from "../../types";
```

(Merge with the existing `../../types` import rather than duplicating it.)

Add `"worktree"` to `LAUNCHER_SCOPES` (after `"workdir"`):

```typescript
export const LAUNCHER_SCOPES = [
  "root",
  "agents",
  "canvas",
  "workdir",
  "worktree",
  "settings",
  "sessions",
] as const;
```

Extend `NavFrame` with `param`:

```typescript
export interface NavFrame {
  scope: LauncherScope;
  query: string;
  highlightedValue?: string;
  /** Opaque scope argument (e.g. the spaceId a worktree sub-scope filters by). */
  param?: string;
}
```

Update `createScopeNavFrame` and `pushFrame` to carry `param`:

```typescript
export function createScopeNavFrame(scope: LauncherScope, param?: string): NavFrame {
  return { scope, query: "", highlightedValue: undefined, param };
}
```

```typescript
export function pushFrame(
  stack: NavFrame[],
  target: LauncherScope,
  originValue: string,
  param?: string,
): NavFrame[] {
  const parent = { ...topFrame(stack), highlightedValue: originValue };
  return [...stack.slice(0, -1), parent, createScopeNavFrame(target, param)];
}
```

Add the leaf command to `LauncherCommand` and the `param` to the `enter` action:

```typescript
export type LauncherCommand =
  | { kind: "spawn"; harness: HarnessName; runtimeTemplate?: string }
  | { kind: "reset-view" }
  | { kind: "focus-picker" }
  | { kind: "goto"; path: string }
  | { kind: "cycle-theme" }
  | { kind: "toggle-bypass-permissions" }
  | { kind: "set-canvas-gesture-modifier"; modifier: CanvasGestureModifier }
  | { kind: "select-worktree"; spaceId: string; worktreeId: string };
```

```typescript
export type RowAction =
  | { kind: "enter"; scope: LauncherScope; param?: string }
  | { kind: "command"; command: LauncherCommand }
  | { kind: "effect"; effect: LauncherEffect };
```

- [ ] **Step 4: Add the Space/Worktree row builders and wire them into `buildScopeRows`**

Add a `GROUP_WORKDIR` constant next to the other group constants:

```typescript
const GROUP_WORKDIR = "Workdir";
```

Add the builders (place them after `buildSettingsRows`):

```typescript
/** Subtitle for a worktree row: its root path. */
function worktreeSubtitle(worktree: WorktreeSummary): string {
  return worktree.path;
}

/** Title for a worktree row: the branch, else "main worktree", else the path tail. */
function worktreeTitle(worktree: WorktreeSummary): string {
  if (worktree.branch) return worktree.branch;
  return worktree.isPrimary ? "main worktree" : locatorTail(worktree.path);
}

/**
 * Workdir scope: one row per detected Space (R7). Rows are titled by the project
 * label (never the bare word "Space"), so they never read like the Settings
 * "Canvas gesture modifier: Space" row. A single-worktree Space selects its lone
 * worktree directly; a multi-worktree Space descends into the worktree sub-scope.
 */
export function buildSpaceRows(spaces: SpaceSummary[], activeWorktreeId: string | null): CommandRow[] {
  if (spaces.length === 0) {
    return [
      {
        value: "status:workdir-empty",
        title: "No spaces detected yet",
        subtitle: "Open a project directory to capture a Space",
        group: GROUP_WORKDIR,
        disabled: true,
      },
    ];
  }
  return spaces.map((space): CommandRow => {
    const single = space.worktrees.length === 1 ? space.worktrees[0] : undefined;
    const rooted = single && single.worktreeId === activeWorktreeId;
    return {
      value: `space:${space.spaceId}`,
      title: space.label,
      subtitle: single ? worktreeSubtitle(single) : `${space.worktrees.length} worktrees`,
      group: GROUP_WORKDIR,
      trailing: rooted ? "Current" : space.kind === "repo" ? "repo" : "dir",
      action: single
        ? {
            kind: "command",
            command: { kind: "select-worktree", spaceId: space.spaceId, worktreeId: single.worktreeId },
          }
        : { kind: "enter", scope: "worktree", param: space.spaceId },
    };
  });
}

/** Worktree sub-scope: one row per worktree of the Space named by `spaceId` (the nav param). */
export function buildWorktreeRows(
  spaces: SpaceSummary[],
  spaceId: string | undefined,
  activeWorktreeId: string | null,
): CommandRow[] {
  const space = spaces.find((candidate) => candidate.spaceId === spaceId);
  if (!space) {
    return [
      {
        value: "status:worktree-missing",
        title: "Space no longer available",
        group: GROUP_WORKDIR,
        disabled: true,
      },
    ];
  }
  return space.worktrees.map((worktree): CommandRow => ({
    value: `worktree:${worktree.worktreeId}`,
    title: worktreeTitle(worktree),
    subtitle: worktreeSubtitle(worktree),
    group: GROUP_WORKDIR,
    trailing:
      worktree.worktreeId === activeWorktreeId ? "Current" : worktree.missing ? "Missing" : undefined,
    disabled: worktree.missing,
    action: worktree.missing
      ? undefined
      : {
          kind: "command",
          command: { kind: "select-worktree", spaceId: space.spaceId, worktreeId: worktree.worktreeId },
        },
  }));
}
```

Add the two fields to `ScopeRowInputs`:

```typescript
export interface ScopeRowInputs {
  templates: RuntimeTemplateSummary[];
  agentsStatus: AgentsStatus;
  themeName: string;
  canvasGestureModifier: CanvasGestureModifier;
  bypassPermissions: boolean;
  spaces: SpaceSummary[];
  activeWorktreeId: string | null;
}
```

Replace `buildScopeRows` to accept `param` and handle the two scopes (the `workdir` case replaces the old `buildDeferredRows("Workdir")`):

```typescript
export function buildScopeRows(
  scope: LauncherScope,
  inputs: ScopeRowInputs,
  query: string,
  param?: string,
): CommandRow[] {
  const { templates, agentsStatus, themeName, canvasGestureModifier, bypassPermissions } = inputs;
  switch (scope) {
    case "root":
      return query.trim().length === 0 ? buildDomainRows() : buildFlatSearchRows(inputs);
    case "agents":
      return buildAgentRows(templates, agentsStatus);
    case "canvas":
      return buildCanvasRows();
    case "settings":
      return buildSettingsRows(themeName, canvasGestureModifier, bypassPermissions);
    case "workdir":
      return buildSpaceRows(inputs.spaces, inputs.activeWorktreeId);
    case "worktree":
      return buildWorktreeRows(inputs.spaces, param, inputs.activeWorktreeId);
    case "sessions":
      return buildDeferredRows("Sessions");
  }
}
```

(`buildDeferredRows` stays — it still backs the `sessions` scope.)

- [ ] **Step 5: Run the new tests to verify they pass**

Run: `pnpm vitest run src/session-canvas/launcher/commandModel.test.ts`
Expected: PASS (new cases plus the existing ones, now that `baseInputs` supplies `spaces`/`activeWorktreeId`).

- [ ] **Step 6: Typecheck**

Run: `pnpm typecheck`
Expected: PASS. (`useLauncherRows` still calls `buildScopeRows(scope, inputs, query)` — the new `param` is optional, so this compiles; Task F threads it through. `inputs` there must now supply `spaces`/`activeWorktreeId` — Task F adds them. If `tsc` flags `useLauncherRows.ts` for the missing `ScopeRowInputs` fields, that is expected and resolved in Task F; to keep this task green in isolation, add `spaces: [], activeWorktreeId: null` to the `inputs` literal in `useLauncherRows.ts` now and let Task F replace the placeholders with real data.)

- [ ] **Step 7: Run the gate**

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/session-canvas/launcher/commandModel.ts src/session-canvas/launcher/commandModel.test.ts \
  src/session-canvas/launcher/useLauncherRows.ts
git commit -m "feat(launcher): Space + Worktree scopes with disambiguating chrome and select-worktree (R7)"
```

---

## Task D: Per-canvas localStorage cache + one-time legacy import

Namespace the canvas persist storage by `canvasId`, and import the pre-Spaces single-canvas blob into the current Space's default Canvas exactly once.

**Files:**
- Create: `src/session-canvas/persistence/canvasCacheStorage.ts`
- Test: `src/session-canvas/persistence/canvasCacheStorage.test.ts` (create)
- Modify: `src/session-canvas/persistence/canvasPersistOptions.ts` (accept a `storage` override)
- Modify: `src/session-canvas/model/canvasStore.persistence.ts` (use the namespaced storage)
- Modify: `src/session-canvas/model/canvasStore.ts` (import legacy + rehydrate inside `initializeCanvas`)

- [ ] **Step 1: Write the failing test for the key helper, the import, and the namespacing storage**

Create `src/session-canvas/persistence/canvasCacheStorage.test.ts`:

```typescript
import { beforeEach, describe, expect, it } from "vitest";
import {
  canvasCacheKey,
  createCanvasCacheStorage,
  importLegacyCanvasCache,
  LEGACY_CANVAS_CACHE_KEY,
} from "./canvasCacheStorage";

beforeEach(() => {
  localStorage.clear();
});

describe("canvasCacheKey", () => {
  it("namespaces the base canvas key by canvasId", () => {
    expect(canvasCacheKey("space:s1")).toBe("transport-matters-canvas:space:s1");
  });
});

describe("importLegacyCanvasCache", () => {
  it("copies the legacy blob into the per-canvas key once, then clears the legacy key", () => {
    localStorage.setItem(LEGACY_CANVAS_CACHE_KEY, '{"version":1}');

    expect(importLegacyCanvasCache("space:s1", localStorage)).toBe("imported");
    expect(localStorage.getItem(canvasCacheKey("space:s1"))).toBe('{"version":1}');
    expect(localStorage.getItem(LEGACY_CANVAS_CACHE_KEY)).toBeNull();

    // Idempotent: a second call (legacy now gone) is a no-op.
    expect(importLegacyCanvasCache("space:s2", localStorage)).toBe("skipped");
    expect(localStorage.getItem(canvasCacheKey("space:s2"))).toBeNull();
  });

  it("never overwrites an existing per-canvas blob", () => {
    localStorage.setItem(LEGACY_CANVAS_CACHE_KEY, '{"version":1,"from":"legacy"}');
    localStorage.setItem(canvasCacheKey("space:s1"), '{"version":1,"from":"existing"}');

    expect(importLegacyCanvasCache("space:s1", localStorage)).toBe("skipped");
    expect(localStorage.getItem(canvasCacheKey("space:s1"))).toBe('{"version":1,"from":"existing"}');
  });
});

describe("createCanvasCacheStorage", () => {
  it("routes get/set/remove through the active canvasId namespace", () => {
    let active = "space:s1";
    const storage = createCanvasCacheStorage<{ value: number }>(() => active);
    if (!storage) throw new Error("expected storage");

    storage.setItem("ignored-name", { state: { value: 1 }, version: 1 });
    expect(localStorage.getItem(canvasCacheKey("space:s1"))).not.toBeNull();

    active = "space:s2";
    expect(storage.getItem("ignored-name")).toBeNull();

    active = "space:s1";
    expect(storage.getItem("ignored-name")).toEqual({ state: { value: 1 }, version: 1 });

    storage.removeItem("ignored-name");
    expect(localStorage.getItem(canvasCacheKey("space:s1"))).toBeNull();
  });
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pnpm vitest run src/session-canvas/persistence/canvasCacheStorage.test.ts`
Expected: FAIL — the module does not exist.

- [ ] **Step 3: Implement `canvasCacheStorage.ts`**

Create `src/session-canvas/persistence/canvasCacheStorage.ts`:

```typescript
import { createJSONStorage, type PersistStorage } from "zustand/middleware";
import { FRONTEND_STORAGE_KEYS } from "../../stores/persistence";

/** The bare key the pre-Spaces build persisted its single canvas under. */
export const LEGACY_CANVAS_CACHE_KEY = FRONTEND_STORAGE_KEYS.canvasStore;

/** localStorage key for one canvas's cached layout, namespaced by canvasId. */
export function canvasCacheKey(canvasId: string): string {
  return `${FRONTEND_STORAGE_KEYS.canvasStore}:${canvasId}`;
}

/**
 * One-time migration: the pre-Spaces build kept a single canvas under the bare
 * LEGACY key. Copy it into the per-canvas key the first time a canvas is
 * initialized, so the user's one canvas becomes the default Canvas of the Space
 * they open first. Idempotent — never overwrites an existing per-canvas blob,
 * and clears the legacy key after a successful copy so it imports exactly once.
 */
export function importLegacyCanvasCache(
  canvasId: string,
  storage: Storage,
): "imported" | "skipped" {
  const target = canvasCacheKey(canvasId);
  if (storage.getItem(target) !== null) return "skipped";
  const legacy = storage.getItem(LEGACY_CANVAS_CACHE_KEY);
  if (legacy === null) return "skipped";
  storage.setItem(target, legacy);
  storage.removeItem(LEGACY_CANVAS_CACHE_KEY);
  return "imported";
}

/**
 * A zustand persist storage that namespaces every read/write by the active
 * canvasId. The `name` zustand passes is ignored; the live canvasId (from
 * `getCanvasId`) keys the cache instead, so switching canvases switches caches.
 */
export function createCanvasCacheStorage<S>(
  getCanvasId: () => string,
): PersistStorage<S> | undefined {
  const inner = createJSONStorage<S>(() => globalThis.localStorage);
  if (!inner) return undefined;
  return {
    getItem: (_name) => inner.getItem(canvasCacheKey(getCanvasId())),
    setItem: (_name, value) => inner.setItem(canvasCacheKey(getCanvasId()), value),
    removeItem: (_name) => inner.removeItem(canvasCacheKey(getCanvasId())),
  };
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pnpm vitest run src/session-canvas/persistence/canvasCacheStorage.test.ts`
Expected: PASS

- [ ] **Step 5: Let `canvasPersistOptions` accept a `storage` override**

In `src/session-canvas/persistence/canvasPersistOptions.ts`, add an optional `storage` to the config and prefer it over the default. In `CanvasPersistOptionsConfig`, add:

```typescript
  storage?: PersistOptions<State, PersistedCanvasSnapshot<TRef>>["storage"];
```

In `createCanvasPersistOptions`, change the returned `storage` line:

```typescript
    storage: config.storage ?? createFrontendPersistStorage<PersistedCanvasSnapshot<TRef>>(),
```

(`PersistOptions` is already imported at the top of the file.)

- [ ] **Step 6: Wire the namespaced storage into the canvas persist options**

In `src/session-canvas/model/canvasStore.persistence.ts`, add the import and pass the storage. The store factory will supply `getCanvasId`; thread it as a parameter:

```typescript
import { createCanvasCacheStorage } from "../persistence/canvasCacheStorage";
```

Change the signature and body of `createCanvasStorePersistOptions`:

```typescript
export function createCanvasStorePersistOptions<State extends CanvasStorePersistableState>(
  getCanvasId: () => string,
) {
  return createCanvasPersistOptions<State, CanvasPaneRef>({
    name: FRONTEND_STORAGE_KEYS.canvasStore,
    version: CANVAS_STORE_STORAGE_VERSION,
    storage: createCanvasCacheStorage<unknown>(getCanvasId) as ReturnType<
      typeof createCanvasPersistOptions<State, CanvasPaneRef>
    >["storage"],
    isContentRef: isCanvasPaneRef,
    getContentRefs: paneRefsForOpenRecords,
    mergeCanvasState: mergeCanvasStoreState,
  });
}
```

In `src/session-canvas/model/canvasStore.ts`, the `persist(...)` call passes the persist options as its second argument:

```typescript
    createCanvasStorePersistOptions<CanvasStoreState>(() => get().canvasId),
```

(`get` is the store factory's getter, in scope at that call site.)

- [ ] **Step 7: Import the legacy cache + rehydrate inside `initializeCanvas`**

In `src/session-canvas/model/canvasStore.ts`, add the import:

```typescript
import { importLegacyCanvasCache } from "../persistence/canvasCacheStorage";
```

Update `initializeCanvas` to run the one-time import for the resolved canvas, then re-read the per-canvas cache:

```typescript
      initializeCanvas(launch) {
        const canvasId = defaultCanvasId(launch);
        // One-time: fold the pre-Spaces single canvas into this Space's default Canvas.
        importLegacyCanvasCache(canvasId, globalThis.localStorage);
        set((state) => ({
          ...state,
          canvasId,
          spaceId: launch.spaceId,
          defaultWorktreeId: launch.worktreeId,
          launch,
          workspaceHash: launch.workspaceHash,
        }));
        // canvasId changed → re-read the namespaced cache for the new canvas.
        void useCanvasStore.persist.rehydrate();
      },
```

- [ ] **Step 8: Add the store-level persistence test (per-canvas isolation + legacy import)**

Add to `src/session-canvas/model/canvasStore.persistence.test.ts` (mirror its existing reload helpers; if it has a `reloadCanvas()` / store-rebuild helper, reuse it):

```typescript
import { canvasCacheKey, LEGACY_CANVAS_CACHE_KEY } from "../persistence/canvasCacheStorage";

it("imports the legacy canvas blob into the initialized Space's default canvas (Slice 6)", () => {
  localStorage.clear();
  localStorage.setItem(LEGACY_CANVAS_CACHE_KEY, '{"state":{},"version":1}');

  useCanvasStore.getState().initializeCanvas({
    owner: "local",
    workspaceHash: null,
    spaceId: "space-1",
    worktreeId: "wt-1",
    canvasId: null,
    harness: null,
    runId: null,
  });

  expect(localStorage.getItem(canvasCacheKey("space:space-1"))).toBe('{"state":{},"version":1}');
  expect(localStorage.getItem(LEGACY_CANVAS_CACHE_KEY)).toBeNull();
});
```

- [ ] **Step 9: Run the persistence tests + full suite**

Run: `pnpm vitest run src/session-canvas/persistence/canvasCacheStorage.test.ts src/session-canvas/model/canvasStore.persistence.test.ts`
Expected: PASS

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS

- [ ] **Step 10: Commit**

```bash
git add src/session-canvas/persistence/canvasCacheStorage.ts \
  src/session-canvas/persistence/canvasCacheStorage.test.ts \
  src/session-canvas/persistence/canvasPersistOptions.ts \
  src/session-canvas/model/canvasStore.persistence.ts \
  src/session-canvas/model/canvasStore.ts \
  src/session-canvas/model/canvasStore.persistence.test.ts
git commit -m "feat(canvas): key the localStorage cache by canvasId with a one-time legacy import"
```

---

## Task E: `api.ts` — Space/Worktree client + run re-key (R1/R2)

Add the Space/Worktree read client the launcher consumes, re-type the run surface onto `spaceId`/`worktreeId` (dropping `workspaceId`), and send `worktreeId` (not `cwd`) on captured-run spawn.

**Files:**
- Modify: `src/api.ts`
- Modify: `src/api.test.ts`
- Modify: `src/session-canvas/model/capturedRunStore.ts` (`ensureRun` param `cwd` → `worktreeId`)
- Modify: `src/session-canvas/viewers/terminal/CapturedRunPane.tsx` (read `worktreeId` from the ref)

- [ ] **Step 1: Write the failing tests for the new endpoints + run body**

Add to `src/api.test.ts`:

```typescript
import { createCapturedRun, fetchSpaces, fetchWorktrees } from "./api";

describe("fetchSpaces", () => {
  afterEach(() => {
    resetApiTransport();
    vi.unstubAllGlobals();
  });

  it("returns the items from GET /v1/spaces", async () => {
    const items = [
      { spaceId: "space-1", label: "tm", kind: "repo", worktrees: [] },
    ];
    const fetchMock = stubFetch({ items });
    await expect(fetchSpaces()).resolves.toEqual(items);
    expect(fetchMock).toHaveBeenCalledWith("/v1/spaces");
  });
});

describe("fetchWorktrees", () => {
  afterEach(() => {
    resetApiTransport();
    vi.unstubAllGlobals();
  });

  it("returns the worktrees of a space, optionally refreshing", async () => {
    const items = [
      { worktreeId: "wt-1", spaceId: "space-1", path: "/p", branch: "main", isPrimary: true, missing: false },
    ];
    const fetchMock = stubFetch({ items });
    await expect(fetchWorktrees("space-1", true)).resolves.toEqual(items);
    expect(fetchMock).toHaveBeenCalledWith("/v1/spaces/space-1/worktrees?refresh=1");
  });
});
```

Replace the existing `createCapturedRun` "forwards an absolute cwd" test (lines ~147–162) with a worktree-targeting test:

```typescript
  it("forwards a worktreeId when supplied", async () => {
    const fetchMock = stubFetch({ run: { runId: "run-xyz" } }, 201);

    await expect(createCapturedRun("codex", "wt-7")).resolves.toBe("run-xyz");

    expect(fetchMock).toHaveBeenCalledWith("/v1/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        harness: "codex",
        worktreeId: "wt-7",
        oscColorReplies: true,
        bypassPermissions: false,
      }),
    });
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pnpm vitest run src/api.test.ts -t "fetchSpaces"`
Expected: FAIL — `fetchSpaces`/`fetchWorktrees` are not exported; `createCapturedRun` still sends `cwd`.

- [ ] **Step 3: Add the Space/Worktree client and re-key the run surface in `api.ts`**

In `src/api.ts`, add `SpaceSummary`/`WorktreeSummary` to the type import from `./types`:

```typescript
import type {
  // …existing names…
  SpaceSummary,
  WorktreeSummary,
} from "./types";
```

Add a new section (near the run endpoints):

```typescript
// ── Space / Worktree endpoints (detect-only) ──────────────────────

/** List detected Spaces with their worktrees inlined via `GET /v1/spaces`. */
export async function fetchSpaces(): Promise<SpaceSummary[]> {
  const response = await requestApiJson<{ items: SpaceSummary[] }>(
    "/v1/spaces",
    "Failed to load spaces",
  );
  return response.items;
}

/**
 * List a Space's worktrees via `GET /v1/spaces/{id}/worktrees`. `refresh=1`
 * reconciles against `git worktree list` server-side before returning.
 */
export async function fetchWorktrees(
  spaceId: string,
  refresh = false,
): Promise<WorktreeSummary[]> {
  const query = refresh ? "?refresh=1" : "";
  const response = await requestApiJson<{ items: WorktreeSummary[] }>(
    `/v1/spaces/${encodeURIComponent(spaceId)}/worktrees${query}`,
    "Failed to load worktrees",
  );
  return response.items;
}
```

Change `createCapturedRun` — rename the `cwd` parameter to `worktreeId` and send it as `worktreeId` in the body:

```typescript
export async function createCapturedRun(
  harness: HarnessName,
  // Worktree root the run is captured under (Slice 4 contract: POST /v1/runs takes
  // worktreeId; the CLI resolves the cwd internally). Omitted → backend resolves
  // its launch worktree.
  worktreeId?: string,
  oscColorReplies = true,
  runtimeTemplate?: string,
  bypassPermissions = false,
): Promise<string> {
  const body = {
    harness,
    ...(worktreeId === undefined ? {} : { worktreeId }),
    oscColorReplies,
    ...(runtimeTemplate === undefined ? {} : { runtimeTemplate }),
    bypassPermissions,
  };
  const response = await requestJson<{ run: { runId: string } }>(
    "/v1/runs",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
    "Failed to spawn captured run",
    true,
  );
  return response.run.runId;
}
```

Re-type the run read surface — replace `RunView` and `RunFilters` (R2: drop `workspaceId`, add `spaceId`/`worktreeId`):

```typescript
export interface RunView {
  runId: string;
  spaceId: string;
  worktreeId: string;
  sessionId: string;
  harness: HarnessName;
  state: RunState;
  endReason?: RunEndReason;
  error?: string;
  createdAt: string;
}

export interface RunFilters {
  state?: RunState;
  spaceId?: string;
  worktreeId?: string;
}
```

Extend `listRuns` to forward the new filters:

```typescript
export async function listRuns(filters?: RunFilters): Promise<RunView[]> {
  const query = new URLSearchParams();
  if (filters?.state !== undefined) query.set("state", filters.state);
  if (filters?.spaceId !== undefined) query.set("space_id", filters.spaceId);
  if (filters?.worktreeId !== undefined) query.set("worktree_id", filters.worktreeId);
  const suffix = query.toString();
  const response = await requestJson<{ items: RunView[]; nextCursor: string | null }>(
    suffix ? `/v1/runs?${suffix}` : "/v1/runs",
    undefined,
    "Failed to list captured runs",
  );
  return response.items;
}
```

- [ ] **Step 4: Re-key the captured-run spawn cascade (`cwd` → `worktreeId`)**

In `src/session-canvas/model/capturedRunStore.ts`, rename the `ensureRun` parameter from `cwd` to `worktreeId` in both the interface declaration (line ~95) and the implementation (line ~146), and pass it through unchanged to `createCapturedRun`:

Interface:

```typescript
  ensureRun(
    runKey: CapturedRunKey,
    provider: HarnessName,
    worktreeId?: string,
    /** Bridge answers the harness OSC color queries (default true; spawn-time only). */
    oscColorReplies?: boolean,
    /** Named runtime template to launch under (spawn-time only; absent → NATIVE). */
    runtimeTemplate?: string,
  ): Promise<string>;
```

Implementation header:

```typescript
      ensureRun(runKey, provider, worktreeId, oscColorReplies = get().oscColorReplies, runtimeTemplate) {
```

…and the `createCapturedRun(provider, cwd, …)` call becomes `createCapturedRun(provider, worktreeId, oscColorReplies, runtimeTemplate, get().bypassPermissions)`.

In `src/session-canvas/viewers/terminal/CapturedRunPane.tsx`, replace the (currently dead) `cwd?` prop with a `worktreeId` read from the pane's content ref. The viewer receives the `captured-run` ref (which now carries `worktreeId`, Task B) via `ViewerProps`. Change the prop interface field `cwd?: string;` (line ~16) to `worktreeId: string;`, change the destructure `cwd,` (line ~36) to `worktreeId,`, and pass it to `ensureRun`:

```typescript
    ensureRun(runKey, provider, worktreeId, oscColorReplies, runtimeTemplate).then(
```

…and update the effect dep array (line ~60): replace the dead `cwd` dep with `worktreeId` (a dead → live swap — the old `cwd` prop was never fed). The captured-run viewer registration in `src/session-canvas/viewers/registry.tsx` does NOT pass `cwd` today — it maps only `runKey`/`provider`/`runtimeTemplate` into the viewer props. So ADD `worktreeId={props.pane.contentRef.worktreeId}` to the captured-run registration's `render(props)` (there is no `cwd={…}` mapping to replace). Run `pnpm typecheck` and fix the registration mapping `tsc` points at.

- [ ] **Step 5: Run the api tests + typecheck + suite**

Run: `pnpm vitest run src/api.test.ts`
Expected: PASS

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS. If `capturedRunStore.test.ts` calls `ensureRun` with a 3rd positional arg, the rename is positional-compatible (still a string|undefined), so those tests are unaffected.

- [ ] **Step 6: Commit**

```bash
git add src/api.ts src/api.test.ts src/session-canvas/model/capturedRunStore.ts \
  src/session-canvas/viewers/terminal/CapturedRunPane.tsx src/session-canvas/viewers/registry.tsx
git commit -m "feat(api): add Space/Worktree client, target worktreeId, drop workspaceId from runs (R1/R2)"
```

---

## Task F: Launcher wiring — feed Spaces in, dispatch `select-worktree`

Thread the nav `param` and the Space data through the React launcher hooks so the new scopes render and navigate, and handle the `select-worktree` leaf command.

**Files:**
- Modify: `src/session-canvas/launcher/useCommandCenter.ts`
- Modify: `src/session-canvas/launcher/useLauncherRows.ts`
- Create: `src/session-canvas/launcher/useSpaces.ts`
- Test: `src/session-canvas/launcher/useSpaces.test.tsx` (create)
- Modify: `src/session-canvas/launcher/CommandCenter.tsx` (constructs `useCommandCenter`; source `useSpaces()` + `activeWorktreeId` here — Step 5a)
- Modify: `src/session-canvas/components/CanvasSurface.tsx` (owns the `onCommand` switch `useCanvasCommandHandler`; add the `select-worktree` case here — Step 5b)

- [ ] **Step 1: Thread `param` + `spaces`/`activeWorktreeId` through `useLauncherRows`**

In `src/session-canvas/launcher/useLauncherRows.ts`, add the new args to `LauncherRowsArgs`, the `inputs` memo, and the `buildScopeRows` call:

```typescript
import type { RuntimeTemplateSummary, SpaceSummary } from "../../types";
```

```typescript
export interface LauncherRowsArgs {
  scope: LauncherScope;
  query: string;
  param: string | undefined;
  templates: RuntimeTemplateSummary[];
  status: AgentsStatus;
  themeName: string;
  canvasGestureModifier: CanvasGestureModifier;
  bypassPermissions: boolean;
  spaces: SpaceSummary[];
  activeWorktreeId: string | null;
  setHighlighted: Dispatch<SetStateAction<string | undefined>>;
}
```

```typescript
export function useLauncherRows({
  scope,
  query,
  param,
  templates,
  status,
  themeName,
  canvasGestureModifier,
  bypassPermissions,
  spaces,
  activeWorktreeId,
  setHighlighted,
}: LauncherRowsArgs) {
  const inputs = useMemo<ScopeRowInputs>(
    () => ({
      templates,
      agentsStatus: status,
      themeName,
      canvasGestureModifier,
      bypassPermissions,
      spaces,
      activeWorktreeId,
    }),
    [templates, status, themeName, canvasGestureModifier, bypassPermissions, spaces, activeWorktreeId],
  );
  const visibleRows = useMemo(
    () => filterRows(buildScopeRows(scope, inputs, query, param), query),
    [scope, inputs, query, param],
  );
  // …rest unchanged…
```

- [ ] **Step 2: Thread `param` + the Space args through `useCommandCenter`**

In `src/session-canvas/launcher/useCommandCenter.ts`:

Add `param` to the `NavFrameController` and `useNavFrameStack` return, and make `descend` carry it.

In `NavFrameController` add `param: string | undefined;`. In `LauncherActionInterpreterArgs` change `descend` to `descend: (scope: LauncherScope, originValue: string, param?: string) => void;`. In `useLauncherActionInterpreter`'s `enter` lifecycle case:

```typescript
        case "descend":
          if (action.kind === "enter") {
            descend(action.scope, row.value, action.param);
          }
          return;
```

In `useNavFrameStack`, update `descend` and the return:

```typescript
  const descend = useCallback(
    (target: LauncherScope, originValue: string, param?: string) =>
      setStack((current) => pushFrame(current, target, originValue, param)),
    [],
  );
```

```typescript
  return {
    scope: frame.scope,
    query: frame.query,
    param: frame.param,
    highlighted: frame.highlightedValue,
    canBack: stack.length > 1,
    resetStack,
    setQuery,
    setHighlighted,
    descend,
    back,
    openScopeStack,
  };
```

Add `spaces` + `activeWorktreeId` to `UseCommandCenterArgs`:

```typescript
import type { SpaceSummary } from "../../types";
```

```typescript
export interface UseCommandCenterArgs {
  onCommand: (command: LauncherCommand) => void;
  themeName: string;
  canvasGestureModifier: CanvasGestureModifier;
  bypassPermissions: boolean;
  spaces: SpaceSummary[];
  activeWorktreeId: string | null;
}
```

Destructure them in `useCommandCenter`, read `param` from the nav stack, and pass everything into `useLauncherRows`:

```typescript
export function useCommandCenter({
  onCommand,
  themeName,
  canvasGestureModifier,
  bypassPermissions,
  spaces,
  activeWorktreeId,
}: UseCommandCenterArgs) {
  const [open, setOpen] = useState(false);
  const {
    scope,
    query,
    param,
    highlighted,
    canBack,
    resetStack,
    setQuery,
    setHighlighted,
    descend,
    back,
    openScopeStack,
  } = useNavFrameStack();
  // …
  const { collection, grouped, rowByValue, fleetStatus } = useLauncherRows({
    scope,
    query,
    param,
    templates,
    status,
    themeName,
    canvasGestureModifier,
    bypassPermissions,
    spaces,
    activeWorktreeId,
    setHighlighted,
  });
```

- [ ] **Step 3: Write the failing test for `useSpaces`**

Create `src/session-canvas/launcher/useSpaces.test.tsx`:

```typescript
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { resetApiTransport, setApiTransport } from "../../api";
import { useSpaces } from "./useSpaces";

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

afterEach(() => resetApiTransport());

describe("useSpaces", () => {
  it("returns the fetched spaces once loaded, [] before", async () => {
    const items = [{ spaceId: "s1", label: "tm", kind: "repo", worktrees: [] }];
    setApiTransport({
      request: vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ items }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    });

    const { result } = renderHook(() => useSpaces(true), { wrapper });
    expect(result.current).toEqual([]);
    await waitFor(() => expect(result.current).toEqual(items));
  });
});
```

- [ ] **Step 4: Implement `useSpaces` (mirrors `useRuntimeTemplates`)**

Create `src/session-canvas/launcher/useSpaces.ts`:

```typescript
import { useQuery } from "@tanstack/react-query";
import { fetchSpaces } from "../../api";
import type { SpaceSummary } from "../../types";

/**
 * Fetches detected Spaces for the Workdir launcher scope. Sticky like the
 * specialist fleet: gated on "the palette has been opened" so a never-opened
 * command center never hits the endpoint. A failed fetch degrades to no spaces
 * (the Workdir scope shows its empty placeholder); it never blocks a spawn.
 */
export function useSpaces(enabled = true): SpaceSummary[] {
  const query = useQuery({
    queryKey: ["spaces"],
    queryFn: fetchSpaces,
    enabled,
    staleTime: 30_000,
  });
  return query.data ?? [];
}
```

The two new args (`spaces`, `activeWorktreeId`) and the `select-worktree` handler live in **two different files**: `useCommandCenter` is constructed in `CommandCenter.tsx`, but the `onCommand` switch it dispatches into is `useCanvasCommandHandler` in `CanvasSurface.tsx` (`CommandCenter` only forwards `onCommand` as a prop — it owns no switch). Both edits below.

- [ ] **Step 5a: `CommandCenter.tsx` — source `useSpaces()` + `activeWorktreeId`, pass into `useCommandCenter`**

Add the imports to `src/session-canvas/launcher/CommandCenter.tsx`:

```typescript
import { useSpaces } from "./useSpaces";
import { useCanvasStore } from "../model/canvasStore";
```

Replace the component head + the `useCommandCenter({ … })` call:

```typescript
export function CommandCenter({
  onCommand,
  themeName,
  canvasGestureModifier,
  bypassPermissions,
}: CommandCenterProps) {
  const spaces = useSpaces();
  const activeWorktreeId = useCanvasStore((state) => state.defaultWorktreeId);
  const center = useCommandCenter({
    onCommand,
    themeName,
    canvasGestureModifier,
    bypassPermissions,
    spaces,
    activeWorktreeId,
  });
```

(The rest of `CommandCenter` is unchanged. `useSpaces()` defaults `enabled=true`; react-query's `staleTime: 30_000` + dedupe keep it cheap, and a failed fetch degrades to the Workdir empty placeholder.)

- [ ] **Step 5b: `CanvasSurface.tsx` — add the `select-worktree` case to `useCanvasCommandHandler`**

The switch is in `src/session-canvas/components/CanvasSurface.tsx`, in `useCanvasCommandHandler` (cases `spawn` / `reset-view` / `focus-picker` / `goto` / `cycle-theme` / `toggle-bypass-permissions` / `set-canvas-gesture-modifier`). Mirror the `goto` case (`navigateToRoute(command.path)`), then re-root via `parseCanvasLaunchContext` → `initializeCanvas`.

`useCanvasStore` and `navigateToRoute` are already imported in this file (`useCanvasStore` backs the `state.canvasId` read at line 226 from Task A; `navigateToRoute` backs the `goto` case). Add only the value import for the parser (line 16 currently imports the `CanvasLaunchContext` *type* from `../route`; add a separate value import):

```typescript
import { parseCanvasLaunchContext } from "../route";
```

Add the case to the switch, after `set-canvas-gesture-modifier`:

```typescript
        case "select-worktree": {
          const params = new URLSearchParams(window.location.search);
          params.set("space_id", command.spaceId);
          params.set("worktree_id", command.worktreeId);
          navigateToRoute(`${window.location.pathname}?${params.toString()}`);
          useCanvasStore.getState().initializeCanvas(parseCanvasLaunchContext(params));
          return;
        }
```

The case calls only module-stable functions (`navigateToRoute`, `parseCanvasLaunchContext`) and `useCanvasStore.getState()`, so the `useCallback` dependency array is unchanged.

- [ ] **Step 6: Run the launcher tests + typecheck + full suite**

Run: `pnpm vitest run src/session-canvas/launcher/useSpaces.test.tsx src/session-canvas/launcher/commandModel.test.ts`
Expected: PASS

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS. (`useCommandCenter.test.tsx` constructs `useCommandCenter` — add `spaces: [], activeWorktreeId: null` to its args object so it type-checks.)

- [ ] **Step 7: Commit**

```bash
git add src/session-canvas/launcher/useCommandCenter.ts src/session-canvas/launcher/useLauncherRows.ts \
  src/session-canvas/launcher/useSpaces.ts src/session-canvas/launcher/useSpaces.test.tsx \
  src/session-canvas/launcher/CommandCenter.tsx src/session-canvas/components/CanvasSurface.tsx \
  src/session-canvas/launcher/useCommandCenter.test.tsx
git commit -m "feat(launcher): feed detected Spaces into the Workdir scope and re-root the canvas on select-worktree"
```

---

## Task G: Persistence rehydrate hardening — drop invalid refs, never null the whole canvas

Make canvas rehydration **drop only the invalid pane refs** instead of nulling the entire persisted set. Today `readContentRefs` / `readDockedPanes` return `null` on the first ref that fails the guard, which cascades `readPersistedPanes` → `rebuildPersistedPanesFromSaved(null)` → `resetPanes` → an **empty canvas**. After Task B makes `worktreeId` required, a single pre-Slice-6 `captured-run` ref (persisted without `worktreeId`) would therefore wipe its valid sibling panes (transcript / resource) on the first reload. Skip the invalid entry and keep the rest. **This also makes the one-time legacy import (Task D) non-destructive for mixed legacy canvases:** the import copies the blob, and on the next rehydrate only the now-invalid captured-run ref is dropped while every valid pane survives.

**Files:**
- Modify: `src/session-canvas/persistence/canvasPanePersistence.ts` (`readContentRefs`, `readDockedPanes`; add `dropOrphanedRects`, wire it into `readPersistedPanes`)
- Test: `src/session-canvas/persistence/canvasPanePersistence.test.ts` (add the drop-invalid case)

**Depends on:** Task B (the test relies on `worktreeId` being required, so a worktreeId-less `captured-run` ref is genuinely invalid). Complements Task D.

- [ ] **Step 1: Write the failing test**

Add to `src/session-canvas/persistence/canvasPanePersistence.test.ts` (inside the `describe("canvas pane persistence", …)` block):

```typescript
it("drops only the invalid legacy ref and preserves valid sibling panes (Slice 6 hardening)", () => {
  // A pre-Slice-6 captured-run ref persisted before worktreeId became required:
  // it now fails the guard and must be dropped WITHOUT wiping its valid siblings.
  // Built as a raw object (not `satisfies PaneContentRef`) because, post-Task-B, a
  // captured-run literal without worktreeId no longer type-checks.
  const legacyCapturedRef = {
    kind: "captured-run",
    owner: "local",
    provider: "claude",
    runKey: "claude:legacy",
    label: "Legacy",
  };
  const sessionRef = {
    kind: "session-timeline",
    owner: "local",
    sessionId: "sess-1",
  } satisfies PaneContentRef;
  const resourceRef = {
    kind: "resource",
    owner: "local",
    source: "url",
    url: "https://example.test",
  } satisfies PaneContentRef;
  const persisted: unknown = {
    contentRefs: {
      "claude:legacy": legacyCapturedRef,
      "session-1": sessionRef,
      "resource-1": resourceRef,
    },
    paneRects: {
      "claude:legacy": { x: 0, y: 0, width: 360, height: 280 },
      "session-1": { x: 400, y: 0, width: 360, height: 280 },
      "resource-1": { x: 800, y: 0, width: 360, height: 280 },
    },
    docked: [],
  };

  const rebuilt = rebuildPersistedPanes(persisted, emptySeedState());

  // NOT a full reset: the two valid panes survive with their refs and rects.
  expect(Object.keys(rebuilt.layout.nodes).sort()).toEqual(["resource-1", "session-1"]);
  expect(rebuilt.contentRefs["session-1"]).toEqual(sessionRef);
  expect(rebuilt.contentRefs["resource-1"]).toEqual(resourceRef);
  // The invalid legacy captured-run ref is dropped — ref AND rect (no ghost node).
  expect(rebuilt.contentRefs["claude:legacy"]).toBeUndefined();
  expect(rebuilt.layout.nodes["claude:legacy"]).toBeUndefined();
});
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pnpm vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts -t "drops only the invalid legacy ref"`
Expected: FAIL — the current all-or-nothing `readContentRefs` returns `null` on the invalid ref, so `rebuildPersistedPanes` resets to an empty canvas; `rebuilt.layout.nodes` is `{}`, not `["resource-1", "session-1"]`.

- [ ] **Step 3: Make `readContentRefs` drop-invalid**

In `src/session-canvas/persistence/canvasPanePersistence.ts`, replace `readContentRefs`:

```typescript
function readContentRefs<TRef extends CanvasPaneRef = PaneContentRef>(
  value: unknown,
  isContentRef: (candidate: unknown) => candidate is TRef,
): Record<PaneId, TRef> | null {
  if (value === undefined) return {};
  if (!isRecord(value)) return null;
  const contentRefs: Record<PaneId, TRef> = {};
  for (const [paneId, ref] of Object.entries(value)) {
    // Drop only the invalid ref (e.g. a pre-Slice-6 captured-run ref lacking
    // worktreeId); keep every valid sibling so one malformed/legacy entry never
    // nulls the whole map and resets the canvas. The now-orphaned rect is pruned
    // by dropOrphanedRects so the dropped pane fully disappears (no ghost node).
    if (isContentRef(ref)) contentRefs[paneId] = ref;
  }
  return contentRefs;
}
```

(A non-record `contentRefs` container still returns `null` → a genuine reset; only per-entry failures are now skipped.)

- [ ] **Step 4: Make `readDockedPanes` drop-invalid**

In the same file, replace `readDockedPanes`:

```typescript
function readDockedPanes<TRef extends CanvasPaneRef = PaneContentRef>(
  value: unknown,
  isContentRef: (candidate: unknown) => candidate is TRef,
): DockedPane[] | null {
  if (value === undefined) return [];
  if (!Array.isArray(value)) return null;
  const docked: DockedPane[] = [];
  for (const entry of value) {
    // Drop only the invalid docked entry; keep every valid docked pane so one bad
    // entry never nulls the whole dock.
    if (isPersistedDockedPane(entry, isContentRef)) docked.push(entry);
  }
  return docked;
}
```

(A non-array `docked` still returns `null` → a genuine reset.)

- [ ] **Step 5: Prune orphaned rects and wire it into `readPersistedPanes`**

In the same file, replace `readPersistedPanes` and add `dropOrphanedRects` immediately after it:

```typescript
function readPersistedPanes<TRef extends CanvasPaneRef = PaneContentRef>(
  persisted: unknown,
  isContentRef: (value: unknown) => value is TRef,
): PersistedCanvasPanes<TRef> | null | undefined {
  if (persisted === undefined || persisted === null) return undefined;
  if (!isRecord(persisted)) return null;
  if (!hasPersistedPanePayload(persisted)) return undefined;

  const contentRefs = readContentRefs(persisted.contentRefs, isContentRef);
  const paneRects = readPaneRects(persisted.paneRects);
  const order = readPaneOrder(persisted.order);
  const docked = readDockedPanes(persisted.docked, isContentRef);
  if (!contentRefs || !paneRects || !docked) return null;
  return {
    contentRefs,
    paneRects: dropOrphanedRects(persisted.contentRefs, contentRefs, paneRects),
    order,
    docked,
  };
}

// A rect whose paneId carried a contentRef that FAILED the guard is now orphaned
// (its content was dropped as invalid). Drop the rect too, so the invalid pane
// fully disappears instead of resurrecting as a contentless ghost node. Rects with
// no persisted contentRef entry at all (demo/placeholder panes) are preserved.
function dropOrphanedRects(
  rawContentRefs: unknown,
  validContentRefs: Record<PaneId, unknown>,
  paneRects: Record<PaneId, WorldRect>,
): Record<PaneId, WorldRect> {
  if (!isRecord(rawContentRefs)) return paneRects;
  const pruned: Record<PaneId, WorldRect> = {};
  for (const [paneId, rect] of Object.entries(paneRects)) {
    if (paneId in rawContentRefs && !(paneId in validContentRefs)) continue;
    pruned[paneId] = rect;
  }
  return pruned;
}
```

(`isRecord`, `PaneId`, and `WorldRect` are already imported at the top of the file — no new imports.)

- [ ] **Step 6: Run the new test to verify it passes**

Run: `pnpm vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts -t "drops only the invalid legacy ref"`
Expected: PASS

- [ ] **Step 7: Run the whole persistence file to confirm no regression**

Run: `pnpm vitest run src/session-canvas/persistence/canvasPanePersistence.test.ts`
Expected: PASS. The existing reset tests stay green because their payloads are all-invalid (drop-invalid + orphaned-rect pruning yields the same empty canvas): "resets non-record and malformed pane payloads" hits the retained container-level `null` returns; "resets stale pane payloads instead of hydrating invalid refs" drops its single invalid ref **and its rect** → `{}`; "resets docked records that fail the injected ref guard" drops its single invalid docked entry → `[]`.

- [ ] **Step 8: Run the gate**

Run from `transport-matters/www/`: `just check && just test`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add src/session-canvas/persistence/canvasPanePersistence.ts \
  src/session-canvas/persistence/canvasPanePersistence.test.ts
git commit -m "fix(canvas): drop invalid pane refs on rehydrate instead of resetting the whole canvas"
```

---

## Final verification

- [ ] Run the whole www gate green from `transport-matters/www/`: `just check && just test` (the repo recipe — `just check` runs `pnpm format` + `pnpm lint:fix` + `pnpm typecheck`, `just test` runs `pnpm test`).
- [ ] Manually confirm the launcher: `⌘K → Workdir` lists Spaces; a multi-worktree repo descends into worktrees; a single-worktree Space selects directly; no row reads like the Settings `Canvas gesture modifier: Space` row (R7).
- [ ] Confirm a fresh load with a pre-Spaces `transport-matters-canvas` blob imports it once into the first Space's default Canvas, then leaves the legacy key gone.
- [ ] Confirm a legacy canvas that contained a `captured-run` pane (no `worktreeId`) reloads with its valid transcript/resource panes intact and only the invalid captured-run pane dropped — not wiped to an empty canvas (Task G).

---

## Self-review (run against `transport-matters-spaces--proposal.md` + the Slice 6 index)

**Spec coverage:**
- Slice 6 bullet "replace the disabled Workdir `buildDeferredRows` stub with Space + Worktree scopes; single-worktree Space skips the worktree sub-step; disambiguating chrome vs the gesture-modifier row (R7)" → **Task C** (buildSpaceRows single-vs-multi, buildWorktreeRows, R7 chrome test).
- "`CanvasModel.id` becomes `canvasId` (not `workspaceHash`); add optional `spaceId`; `worktreeId` required on terminal + captured-run, optional on resource(url); promote `Canvas.defaultWorktreeId` (R3)" → **Tasks A + B**.
- "canvasStore + persistence — localStorage as a cache keyed by `canvasId`; one-time import per legacy `workspaceHash` → one default Canvas per Space" → **Task D**.
- Resume-review hardening (Finding 1): canvas rehydrate drops only invalid pane refs instead of resetting the whole canvas, so the `worktreeId`-required guard (Task B) + the one-time legacy import (Task D) never wipe a mixed legacy canvas → **Task G**.
- "`api.ts` — target `spaceId`/`worktreeId`" → **Task E** (new client + run re-key + drop `workspaceId`, R1/R2).
- "Tests: launcher scope rows; pane ref types; canvas import" → Task C (`commandModel.test.ts`), Task B (`paneRecords.test.ts`), Task D (`canvasCacheStorage.test.ts` + persistence test), Task G (`canvasPanePersistence.test.ts` drop-invalid case).

**Placeholder scan:** No `TBD`/`implement later`/`add error handling`. Every code step has complete code; the one explicit `tsc`-driven sweep (Task B Step 9, Task E Step 4) enumerates the exact files and the one-line edit, which is concrete, not a placeholder.

**Type consistency:** `canvasId` (field) / `defaultCanvasId` (helper) / `canvasCacheKey` (storage key) are distinct and used consistently. `SpaceSummary`/`WorktreeSummary`/`SpaceId`/`WorktreeId` are defined once in `types.ts` (Task A) and imported by `paneRecords`, `commandModel`, `api`, `useLauncherRows`, `useCommandCenter`, `useSpaces`. `select-worktree` command shape `{ kind, spaceId, worktreeId }` is identical in `commandModel.ts`, its tests, and the host handler. `NavFrame.param` / `pushFrame(…, param?)` / `buildScopeRows(…, param?)` / `descend(…, param?)` thread the same optional string end to end.

**Known scope boundaries (intentional, not gaps):** `ViewerCanvasContext.id` keeps its name (28 importers; renaming is out of scope). Worktree CRUD is the deliberate next iteration (detect-only here). The Canvas server store sync is out of scope (localStorage stays the cache). The legacy import lands the single pre-Spaces canvas into whichever Space initializes first (documented one-time semantic).
