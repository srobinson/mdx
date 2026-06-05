# Review — Developers Launcher Domain (dev-only)

**PR:** #216 · branch `feat/canvas-developers-domain` · HEAD `8273768` (pre-PR main `9555e93`)
**Diff:** +355/-22 across 19 files
**Reviewer:** transport-matters:general:2:7.2 (adversarial, read-only, tree untouched)
**Date:** 2026-07-05

## Verdict: **CONDITIONAL** — 0 blockers / 0 majors / 1 minor

The feature is correct and airtightly gated at the command/UI level (DEV gating,
lifecycle, actions, first-position, count all clean; full frontend suite green). One
hygiene gap the brief pre-flagged is real: dev-blank panes persist and rehydrate on
reload, including in a prod build reading shared-origin localStorage — harmless (renders
an empty `aria-hidden` div, no crash) but it violates the stated "dev tools FULLY absent
in prod" guarantee. One-line fix.

Evidence:
- `pnpm --filter @tm/shell test` (full suite, per the structural-PR lesson) → **1100 passed** (154 files).

---

## Minor

**M1 — dev-blank panes persist and rehydrate, including in a production build.**

dev-blank is correctly excluded from `PaneContentRef` (`paneRecords.ts` `isPaneContentRef`
has no `dev-blank` case → returns `false`). But the canvas store's persistence does not
treat it as ephemeral:
- `canvasStore.persistence.ts` `paneRefsForOpenRecords` persists **every** open pane's
  `contentRef` with no kind filter (`if (layout.nodes[paneId]?.lifecycle === "open")
  refs[paneId] = pane.contentRef`), so an open dev-blank is written to localStorage.
- The store's rehydrate guard is `isContentRef: isCanvasPaneRef` (not `isPaneContentRef`),
  and `isCanvasPaneRef` **accepts** dev-blank (`kind === "dev-blank" && id && title`), so
  a persisted dev-blank is kept on rehydrate and re-seeded as a pane.
- The dev-blank viewer registration in `viewers/registry.tsx` is **not** DEV-gated
  (always in `registry`), so in prod a rehydrated dev-blank resolves to its viewer and
  renders `<div className="canvas-dev-blank-pane" aria-hidden="true" />`.

Consequence: a developer who spawns dev-blank panes in a DEV build, then loads a PROD
build at the **same origin** (e.g. the desktop canvas dev-mode toggle sharing the
loopback origin, or a rebuilt bundle on the same host:port), rehydrates those dev-blank
panes even though prod cannot spawn them. Impact is low — an empty aria-hidden div, no
crash, no data corruption — but it contradicts the spec's "in a production build the
domain, its rows, its commands ... are FULLY absent."

**Fix:** make dev-blank ephemeral — skip `kind === "dev-blank"` in
`paneRefsForOpenRecords` (don't persist it), or reject dev-blank in the store's rehydrate
`isContentRef`. Either keeps prod free of dev scaffolding.

---

## Audit points (all others PASS)

### 1. DEV gating is airtight — PASS

`isDev` flows `import.meta.env.DEV` → `useLauncherRows.ts` → `ScopeRowInputs.isDev`, and
**every** surface funnels through one gate, `visibleDomains(inputs) = inputs.isDev ?
[DEVELOPERS_DOMAIN, ...BASE_DOMAINS] : BASE_DOMAINS` (`commandRows.ts`):
- Domain rows: `buildDomainRows` maps `visibleDomains`.
- Header count: `launcherDomainCount = visibleDomains(inputs).length` (derived) →
  `useLauncherRows` `domainCount` → `CommandCenter.tsx` `${domainCount} domains`.
- Flat search: `buildFlatSearchRows` includes `buildDevelopersRows()` only when
  `visibleDomains(inputs).some(scope === "developers")`.
- Direct scope nav: `buildScopeRows` `case "developers"` returns `[]` unless
  `visibleDomains` contains it.
- No keybinding path dispatches the dev commands (grep of `keybindings/` +
  `useLauncherHotkeys` → none).

In prod (`DEV=false`) the domain, its rows, its three commands, and the count (5, not 6)
are fully absent — no flat-search or scope-nav path reaches them. Both DEV states are
tested (`commandRows.test.ts` `launcherDomainCount` 5 and 6; `isDev: true` flat-search
and scope cases; `useCommandCenter.test.tsx` developers-domain interactions).

### 2. Lifecycle wiring — PASS

`COMMAND_INTERACTIONS` sets `spawn-empty-pane` and `spawn-terminal` to
`{ enter: "run-stay" }` (palette stays open); `clear-canvas` is absent from the map so
`interactionFor` falls through to `RUN_AND_CLOSE` (`enter: "run-close"`). Exercised via
`useCommandCenter.test.tsx` (`selectValue("domain:developers")` + item selection).

### 3. Actions correctness — PASS

- `spawnEmptyPane` mints a unique label per call via `labelFor(paneCounters, "Pane")`
  (Pane-1, Pane-2, …), so each dev-blank has a unique `id`/paneId (`dev-blank:${id}`) and
  multiples coexist. No worktree needed; no crash path.
- `spawnTerminal` = `spawnPane({ kind: "terminal", owner: "local", worktreeId:
  requireWorktreeId(defaultWorktreeId) })` — spawn-or-focus the singleton terminal
  (`paneIdForRef` terminal → `"terminal"`, `runSpawnPaneFlow` focuses if already open).
  `requireWorktreeId` throws on a worktree-less canvas, and the dispatcher wraps the call
  in try/catch → `console.error` (mirrors `addCapturedRun`), so no crash.
- `clearCanvas` invokes the dismiss lifecycle for every open + docked pane, then resets
  `panes: {}`, `docked: []`, `expandedPaneId: null`, `framing: emptyFraming()`, `layout:
  createInitialEngineLayoutState()`. It preserves `paneCounters` (numbering continues).
  It deliberately clears the picker too (a full "clear"; observation, not a defect — the
  brief's "without tripping picker protection").
- Existing spawn/agent paths unchanged (`spawnPane`/`runSpawnPaneFlow` reused;
  `buildFlatSearchRows` uses `agentSpawnRows(inputs.templates)`).

### 4. First position + count integrity — PASS

`visibleDomains` prepends `DEVELOPERS_DOMAIN`, so Developers renders first (above
Agents). The count is derived (`launcherDomainCount = visibleDomains().length`), never a
hardcoded 5/6, so it tracks the visible set in both DEV states.

### 5. dev-blank identity/registry consistency — PASS (persistence hygiene is M1)

`paneIdForRef` (`dev-blank:${ref.id}`), `titleForRef` (`ref.title`), and `viewerIdForRef`
(`"dev-blank"`) are consistent with the registry (`id: "dev-blank"`,
`canRender: ref.kind === "dev-blank"`), and the registry cross-check
(`registry.test.ts` "keeps registry identity aligned with the model", iterating
`registryRefs()` which includes dev-blank) plus `paneIdentity.test.ts` pin all three.
Terminal identity is unchanged (`paneIdForRef` terminal → `"terminal"`, singleton
preserved).

### 6. Full frontend suite green, no depth-relative fs issues — PASS

`pnpm --filter @tm/shell test` → 1100 passed (154 files). The new files add no
depth-relative fs joins (the boundary test is untouched here).

---

## Verification note

Read-only throughout (`git show` for pre-PR state, no branch switch, no temp files);
`git status` clean.
