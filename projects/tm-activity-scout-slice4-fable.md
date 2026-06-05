# Transport Matters — Slice 4 Scout (Fable): CONFIRM/EXTEND pass

- **Date:** 2026-07-10. **SHA inspected:** `2caadd8` (= origin/main, tree clean before and after; read-only, no repo writes by me or any subagent).
- **Inputs:** prior scout reports `tm-activity-scout-slice4-codex.md` + `-opus.md` (both at `787fffc`), locked design cm `019f4232-db6a-7be2-9b37-9f470e67c019`.
- **Locked scope:** per-pane vitals = **token count + time + status (+ "needs you") only**. Cost and remaining-% DROPPED. Wire DTOs move to a new `@tm/contract` package with subpath exports (`@tm/contract/activity`), zero runtime deps; `@tm/activity` imports them back; browser consumes from `@tm/contract/activity`, never `@tm/activity`.
- **Drift check:** `git log 787fffc..2caadd8` = 4 commits (#250–#253), all wheel/desktop/Python. **Zero commits touched `www/` or `packages/activity`** (path-filtered logs empty). Every prior-scout file-level claim was re-verified against the current tree, not assumed.

## Headline

PR-1 is smaller than either prior report assumed: the five wire DTOs are exported from `activityRouter.ts` but **never re-exported by the `@tm/activity` barrel and have zero import sites outside their defining file** — the move rewires 3 files, not a consumer web. The one real design nuance is the status union: `ActivityWireRun.status` is typed as `ActivityStatus`, which is derived from the `activityStatuses` const (runtime code) in `domain/runActivityContext.ts`, so the contract package must own that pair. The load-bearing gate is `importGraphBoundary.test.ts`'s "single public barrel for every root package" check, which fails closed on any subpath exports map — it must be amended for `@tm/contract` in the same PR. Two corrections to carried assumptions: the activity stream has **no resume cursor or gap-backfill** (snapshot-on-connect; the new hook mirrors `useSessionEventStream`'s reconnect/teardown only), and **"needs you" needs no new source** — `needs-you` is a literal member of `activityStatuses`.

---

# Reuse Map

## PR-1 — `@tm/contract` extraction

### Move set (exact symbols in `packages/activity/src/server/activityRouter.ts`)

| # | Symbol | Kind | In-repo import sites outside defining file |
|---|---|---|---|
| 1 | `ActivityWireUsageTotals` | pure interface | **none** |
| 2 | `ActivityWireRun` | pure interface (field `status: ActivityStatus`) | **none** |
| 3 | `ActivityWorkspaceRollup` | pure interface (`status_counts: Record<ActivityStatus, number>`) | **none** |
| 4 | `ActivityWorkspaceResponse` | pure interface | **none** |
| 5 | `ActivityStreamFrame` | pure type union | **none** |
| 6 | `ActivityStatus` | pure type, currently in `domain/runActivityContext.ts` | referenced in 7 files (below) |
| 7 | `activityStatuses` | **`as const` array — the only runtime code in the move set** (zero deps, contract-compatible) | same 7 files |

Verified by repo-wide grep: none of #1–#5 is referenced anywhere but `activityRouter.ts`, none is in the `packages/activity/src/index.ts` barrel, and **no re-declaration exists anywhere** (the `context_tokens`/`cache_creation_input_tokens` hits in `www/` are the unrelated exchange `UsageStats` in `@tm/core` types/fixtures). `activityRouter.test.ts` asserts the wire shape via string literals, not type imports — it is untouched by the move and doubles as a wire-shape regression net.

**Status-union rewiring.** `ActivityStatus`/`activityStatuses` are referenced by: `domain/runActivityContext.ts` (definition), `domain/index.ts` (re-export), `domain/machineTestEvents.ts`, `domain/runActivityMachine.test.ts`, `projections/workspaceActivity.ts`, `src/index.ts` (barrel re-export), `server/activityRouter.ts`. Recommended move: relocate the pair to `@tm/contract/activity` (the `status_counts` keys and `status` values ARE the wire contract); `runActivityContext.ts` imports them back and `domain/index.ts` keeps re-exporting, so **only 3 files change imports**: the new contract module, `runActivityContext.ts`, and `activityRouter.ts` (which should import wire types from `@tm/contract/activity` directly). All other references keep resolving through `./domain`. `ActiveActivityStatus` (an `Exclude<>` derivation) stays in domain — it is machine vocabulary, not wire.

**Stays behind in `activityRouter.ts`:** `createActivityRouter`, `ActivityRouterDeps`, `ActivityProjectionReader`, `ActivityWorkspaceSubscriptionSource` (server), `ACTIVITY_STREAM_KEEPALIVE_MS` (server impl detail), `DEFAULT_ACTIVITY_OWNER` (server-side query default; the browser passes `?owner=local` explicitly — moving it is optional, default keep).

### Package skeleton (model: `@tm/common`, the foundational leaf — NOT gateway's file set)

- `packages/contract/package.json`: mirror `packages/common/package.json` (`"private": true`, `"type": "module"`, `version 0.1.0`, scripts `test` + `typecheck`, devDeps `vitest: catalog:`) with exports map `{"./activity": "./src/activity/index.ts"}` — **subpath-only, no `"."` barrel** (prevents a dumping-ground root; the boundary test edit below must sanction this shape). Zero `dependencies`. Omit `"types": ["node"]` from tsconfig (browser-neutral leaf).
- `packages/contract/tsconfig.json`: extends `../../tsconfig.base.json` + `../../tsconfig.bundler.json`, `lib: ["ES2023"]`, `include: ["src"]` (copy `packages/common/tsconfig.json`, drop the node types).
- `pnpm-workspace.yaml`: **no edit** — the `packages/*` glob auto-registers it.
- Consumers: `packages/activity/package.json` adds `"@tm/contract": "workspace:*"` (PR-1). `www/packages/core/package.json` adds the same in PR-2 — note this gives `@tm/core` its **first `@tm/*` dependency** (previously a pure leaf); sanctioned by the design since contract sits below core as a pure-type leaf.
- zod: **not in the pnpm catalog today**. Recommend PR-1 ships types-only (zero deps, honors the design's "zero runtime deps"); browser-edge validation is a separate decision if ever wanted.

### Gating mechanics (exact edit sites, `packages/gateway` as registration template)

1. **`www/packages/shell/src/testSupport/importGraphBoundary.test.ts` — the one real conflict.** The test "enforces a single public barrel for every root package" via `isSingleBarrel` (exports keys must be exactly `["."]`); `@tm/contract`'s subpath map **fails this closed today**. PR-1 must: (a) amend the single-barrel rule to sanction the contract package's subpath-per-context shape (still rejecting `./src/*` and wildcard leaks); (b) add `"contract"` to the vacuous-pass guard `expect.arrayContaining(["activity", "common", "gateway", "runtime"])`; (c) add `@tm/contract/activity` to the "resolves the entrypoints the exports maps declare" list; (d) add deep-import cases (`@tm/contract/src/activity`, `@tm/contract/activity/internal`) to the "fails closed for deep package imports" list; (e) extend `packageInternalViolations` — it takes a single entrypoint per package, and contract needs a multi-entrypoint variant (every exported subpath file is a legal target, everything else in `src/` is internal).
2. **`packages/AGENTS.md`**: both the package-kinds taxonomy (context / foundational / serving root) and the "One import surface per package" section state rules `@tm/contract` breaks. Add a fourth kind (contract package: published wire contracts, subpath export per bounded context, zero runtime deps) in the same PR — the boundary test cites this doc.
3. **`justfile`**: `check` recipe — add `pnpm --filter @tm/contract typecheck` beside the `@tm/common` line; `test` recipe — add `pnpm --filter @tm/contract test`. **Caveat: vitest exits nonzero with zero test files**, so ship at least one contract test (e.g. a wire-fixture or type-level assertion) or don't register in `test`; recommend the test. `build`, `verify-wheel`, `dmg`, `install-local`, `channel-restart` need **no edit** (contract has no build artifact). `test-affected` picks it up automatically via pnpm changed-since filters.
4. **`.github/workflows/ci.yml`** `product-plane` job: add `pnpm --filter @tm/contract typecheck` to the typecheck block (currently common/activity/runtime/gateway) and `pnpm --filter @tm/contract test` to the test block. The `www` job needs no PR-1 edit (the boundary test runs inside `pnpm --filter @tm/shell test`, already gated). `pnpm lint:product-plane` (root `package.json` → biome over `../../../packages`) covers the new directory automatically. `release.yml`: no edit.
5. **Gateway template — copy the registration, NOT the embed pipeline** (verified end-to-end): gateway registers via the `packages/*` glob + `package.json` (exports `"."`→`./src/index.ts`, scripts, catalog devDeps) + `tsconfig.json` (base+bundler) + explicit justfile `check`/`test` lines + CI product-plane filters + boundary-test coverage (`GATEWAY_SRC` internal-violations, entrypoint list, vacuous guard). Its *other* half — `scripts/build.mjs` esbuild embed into `api/src/transport_matters/gateway/`, the hatch `artifacts` glob, `api/scripts/assert_gateway_wheel.py`, CI tar/stage/`linux-wheel-spawn` gates (all from #249) — is wheel-embed machinery a types package must not copy.

## PR-2 — canvas vitals (carried findings, each marked)

| Carried finding | Verdict | Evidence on `2caadd8` |
|---|---|---|
| PaneChrome narrow slot mount; keep CapturedRunPane untouched | **CONFIRMED** (one nuance) | `PaneChrome.tsx` (111 LOC) owns `canvas-pane-window__header` + `__body`; no slot exists. Nuance: `PaneChromeProps` is not children-only (`title, badge, state, titleId, focused, closeDisabled?, expanded?, onClose?, onMinimize?, onExpand?, onFrame?, onHeaderDoubleClick?, children`) — the strip is a new optional prop rendered between header and body. `CanvasPaneLayer.tsx` (228 LOC) already branches on `pane.contentRef.kind === "captured-run"`; `PaneWindow.tsx` (51 LOC) is the thin adapter to thread it. |
| runKey→runId via `useCapturedRunBinding` / `capturedRunStore` | **CONFIRMED** | `useCapturedRunBinding` returns `{ runId, spawnError }`; `capturedRunStore.ts` (303 LOC) persists `runs[runKey].runId`, `CAPTURED_RUN_STORAGE_VERSION = 4` unchanged. Vitals are live wire data — keep the new store **non-persisted** and leave capturedRunStore's persist shape alone (data-loss lesson). |
| `useWorkspaceActivityStream` sibling of `useSessionEventStream` with resume cursor/reconnect/gap-backfill | **CORRECTED** | `useSessionEventStream` still has all claimed machinery, but the activity stream has **no cursor on the wire**: no `last_seq` param, data-only `snapshot`/`delta` frames, full snapshot on every connect (verified in `activityRouter.ts` + its test). The new hook mirrors reconnect (`RECONNECT_DELAY_MS` pattern) and teardown; resume-cursor and REST gap-backfill **do not apply** — reconnect self-heals via the fresh snapshot. Simpler hook than the brief assumed. |
| Core activity slice: fetch + URL builder in `transport.ts`, pure reducer `activityStreamEvents.ts` mirroring `exchangeStreamEvents.ts` | **CONFIRMED** | `transport.ts` 474 LOC / 38 exports (headroom to 700); `applyExchangeStreamEvent` is the pure-reducer pattern; no activity client/reducer exists anywhere in core. Wire types now come from `@tm/contract/activity`, not re-declared (opus D3 resolved by decision). Stream URL shape: `/v1/workspaces/{workspaceId}/activity/stream?owner=local` (`sessionEventsStreamUrl` in `canvas/src/infrastructure/api/sessionEvents.ts` is the builder shape to copy). |
| Vitals store keyed by `run_id` beside `capturedRunStore` | **CONFIRMED** | `canvas/src/model/` is the store home per canvas CLAUDE.md ("model/ = pane records and stores") + OWNERSHIP.md; the SSE hook belongs in `infrastructure/stream/`. No `vitals` symbol exists anywhere — clean namespace. |
| Reuse `core/formatting.ts` `contextTokens` | **CONFIRMED** | Exact formula `input_tokens + cache_creation_input_tokens + cache_read_input_tokens`. Wire vital = `ActivityWireRun.context_tokens` (server-computed via `windowTokens`); `contextTokens` is for any client-side recompute — do not add a third inline copy (two pre-existing re-inlines below). |
| Duration-formatter consolidation targets | **CONFIRMED, list complete** | Exactly three private impls, all inspector: `ExchangeTurnCard.tsx` → `formatElapsedTime`, `editor/PausedHeader.tsx` → `formatElapsed`, `detail/CodexTimeline.tsx` → `formatDuration`. Core has none (95-LOC `formatting.ts`, no duration, no currency). Consolidate one into `core/formatting.ts` for the time vital (`since_ts`) and rewire the three call sites. Currency formatter: **DISSOLVED** (no cost vital). |
| Canvas-native BEM status pill, zero Tailwind | **CONFIRMED** | Canvas package is Tailwind-free (comments in `tokens.css`/`canvas.css`/`pane-frame.css` state it explicitly); `--pane-header: 58px` unchanged; imitate `.terminal-pane__status` strip. **"needs you" source DISSOLVED as a decision** (opus D4): `activityStatuses = ["starting","thinking","running-tools","needs-you","stalled","exited"]` — the pill maps `status === "needs-you"` directly. |
| `#ffd700` retune-before-merge hack | **CONFIRMED** | Two occurrences in `terminal-pane.css` (`.xterm-bg-59`, `.xterm-bg-237`), DEMO comment intact. Resolve if PR-2 touches that file. |
| Model-metadata catalog / `model` end-to-end surfacing (opus headline crux, codex plan steps 1–2, opus D1) | **DISSOLVED** | Locked design dropped cost + remaining-%; all three vitals (`context_tokens`, `since_ts`, `status`) are already on `ActivityWireRun`. No catalog, no `model` threading, no pricing, no ceiling. |
| Wire-type ownership (opus D3, codex "decision needed") | **DISSOLVED (resolved)** | `@tm/contract` chosen; `@tm/core` re-declaration rejected. |

---

# Quality Map

- **Boundary drift from #249–#253: none in scope.** Only `packages/gateway/src/main.ts` changed under `packages/` (`isEntrypoint` newly exported — gateway self-boot code; do not carry into any scaffold). `pnpm-workspace.yaml` changes were catalog-only (electron-builder in, @electron/packager out). `packages/activity` and `www/` byte-identical since the prior scouts.
- **Pre-existing duplication PR-2 must not widen (both prior scouts, CONFIRMED):** (1) EventSource lifecycle hand-rolled twice (`useSessionEventStream`, inspector `useExchangeStream`) with no shared `useEventSource` — the activity hook is the third copy; extraction (opus D5) remains open but is NOT in the locked design; flag to orchestrator, don't smuggle it in. (2) `contextTokens` re-inlined in `ArkExchangeViewer.tsx` `tabReadout` and `ExchangeDetail.tsx` `tabReadout` — pre-existing, out of slice; do not add a third. (3) Duration formatting ×3 — PR-2 consolidates (in scope, it needs one).
- **Inherited justfile repetition:** the inspector/canvas/gateway build triad is copy-pasted across `build`/`verify-wheel`/`dev`/`dmg`/`install-local`/`channel-restart` + both workflows. `@tm/contract` has no build step so it does not widen this; noted for a future hygiene pass.
- **Sizing:** every PR-1/PR-2 edit site is far under 700 LOC (largest: `transport.ts` 474). `activityRouter.ts` drops ~35 lines in PR-1.
- **Doc updates owed:** `packages/AGENTS.md` (PR-1, see gating); `www/packages/canvas/CLAUDE.md` "Depends on `@tm/core` and `@tm/host`" needs `@tm/contract` added when canvas imports it (PR-2). `www/packages/core` has no CLAUDE.md/AGENTS.md, so its leaf-status change needs no doc edit.
- **Boundary-test PR-2 follow-through:** when core/canvas import `@tm/contract/activity`, the existing entrypoint-resolution list already covers it if PR-1 added the specifier; no further boundary edits expected.

# Plan (sharpened build order)

**PR-1 (pure refactor, no behavior change):**
1. Scaffold `packages/contract` (skeleton above, `@tm/common` as model; subpath-only exports).
2. Move the 5 wire DTOs + `ActivityStatus`/`activityStatuses` into `src/activity/index.ts`; rewire `runActivityContext.ts` (import back + `domain/index.ts` re-export unchanged) and `activityRouter.ts`; add `@tm/contract` dep to `packages/activity`.
3. Amend `importGraphBoundary.test.ts` (5 edits listed under Gating) + `packages/AGENTS.md` contract-kind clause.
4. Register in `justfile` `check`/`test` + `ci.yml` product-plane typecheck/test blocks; ship ≥1 contract test.
5. Gate: `just check` && `just test` verbatim (includes the shell boundary suite and the activity wire-literal tests, which prove the wire is byte-identical).

**PR-2 (feature):** core slice (`transport.ts` verb + URL builder, `activityStreamEvents.ts` reducer, types from `@tm/contract/activity`) → `useWorkspaceActivityStream` (reconnect/teardown only — no cursor/backfill) → non-persisted `run_id`-keyed vitals store in `canvas/src/model/` → PaneChrome strip prop threaded from `CanvasPaneLayer`/`PaneWindow` for captured-run panes via `useCapturedRunBinding` → BEM strip (token count via `context_tokens`, time via consolidated core duration formatter on `since_ts`, pill on `status` incl. `needs-you`). Full `@tm/shell` suite (structural-PR lesson) + `just check`/`just test`.

**Top risk:** the single-barrel boundary test vs subpath exports — if the builder scaffolds the package before amending the test, `just test` fails closed repo-wide; land the test amendment in the same commit as the package skeleton.
