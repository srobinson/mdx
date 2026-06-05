# TM Gateway slice-0 — review 2 (opus)

PR #200 @ head `6dca869` (branch `feat/gateway-slice0`, baseline main `ef11b6c`).
Adversarial read, direct (no subagents), diff-only. Two commits under review:
`f257ff2` (slice 0) + `6dca869` (fix: close fastify on shutdown).

**Verdict: ship-ready. 0 blockers, 0 majors, 3 minors (tests/cleanup), 1 ops
observation. Both requested fixes verified correct.**

## Evidence (ran, observed)

- `pnpm --filter @tm/gateway typecheck` → clean.
- `pnpm --filter @tm/gateway test` → 2 files, **6 tests passed**.
- Real boot (`tsx src/main.ts`) → logged `gateway listening at http://127.0.0.1:<port>`,
  `GET /health` → `{"status":"ok"}`. `isEntrypoint()` fires under tsx.
- Single-process `node --import tsx src/main.ts` + `SIGTERM` → **exit 0**, port
  then **connection refused** (socket released). Graceful shutdown runs Fastify
  close hooks end-to-end.

## Fix #1 — shutdown (`main.ts`: `runGatewayProcess`, `installShutdownHandlers`)

CONFIRMED correct.

- Build/listen failure: try builds → installs handlers → listens; catch closes
  an already-built app (guarded `if (app !== undefined)`, inner try around
  `app.close()`), logs, `exit(1)`.
- SIGINT/SIGTERM handlers `await app.close()` then `exit(0)`; a shared
  `shuttingDown` flag dedups across both signals.
- `main.test.ts` proves it with a REAL `fastify()` instance + `onClose` hook,
  not a stub: asserts the hook ran + exit 0 on SIGTERM, and app closed + exit 1
  on listen failure. Corroborated by the single-process SIGTERM probe above
  (exit 0 + socket closed).
- `isEntrypoint()` guard correctly prevents test-time auto-run — the green suite
  proves it (importing `main.ts` under vitest does not `process.exit`).

## Fix #2 — `packages/AGENTS.md` (Serving roots + One import surface)

CONFIRMED matches docs.

- "target product plane origin; Python remains the interim origin until the
  Gateway takes over" faithfully paraphrases `docs/ARCHITECTURE.md`
  "Product-plane gateway": *"Until the Gateway exists, Python remains the
  origin… At the target the origin flips."*
- One-import-surface rule now reads "whether context, foundational, or serving
  root"; the importGraphBoundary test covers gateway single-barrel and fails
  closed on the `@tm/gateway/app` deep import.

## General pass — sound

- **Mount contract is not a tautology.** `app.test.ts` injects `deps.greeting`
  through `createFixtureContextRouter` and reads it back at
  `/v1/fixture/greeting` via port-less `inject()`; a separate case asserts
  `/greeting` → 404 (prefix isolation). It exercises the real
  factory → plugin → register → prefix → deps chain, not a self-referential check.
- **Deep-import fail-closed.** `@tm/gateway/app` and `@tm/gateway/src/app` throw
  `Unresolvable local import`; the `@tm/gateway` barrel resolves;
  `packageInternalViolations(GATEWAY_SRC, …)` == `[]`; single-barrel guard's
  `arrayContaining` now includes `gateway`.
- **Gating complete.** gateway typecheck+test added to both CI (typecheck and
  test steps) and justfile `check`/`test`; the `activity_package` var was
  removed cleanly with no dangling `{{activity_package}}` reference; shell biome
  paths include `../../../packages/gateway` (correct depth, mirrors activity).
- **Fastify bootstrap.** `buildGateway` registers `/health`, mounts each context
  under its prefix, awaits `ready()`. Correct.
- **Port parsing** uses `optionalInteger` (throwing) — correct per AGENTS.md
  convention for trusted operator input: a malformed `TRANSPORT_MATTERS_GATEWAY_PORT`
  throws → caught → `exit(1)` (loud), not a silent ephemeral bind.

## Minors (low; tests/cleanup)

1. **Build-failure branch untested.** `main.test.ts` covers listen-failure (app
   defined) but not `build()` rejecting (the `app === undefined` path in the
   catch). Add a case where `build` throws → asserts no close, error logged,
   exit 1.
2. **Redundant `await` in the `buildGateway` mount loop.** `await app.register(router, { prefix })`
   per iteration forces a readiness cycle each time; the trailing
   `await app.ready()` already boots the whole plugin tree, so one cycle
   suffices. Defensible only if the intent is per-context error attribution;
   otherwise drop the per-iteration `await`.
3. **Test teardown asymmetry.** `app.test.ts` tests 1–3 and `main.test.ts`
   test 1 close the app without try/finally or an `afterEach`; only
   `app.test.ts` test 4 uses try/finally. An assertion failure before close
   leaks the instance (and, for the listen tests, the socket). Prefer an
   `afterEach`/helper for symmetry.

## Observation (not a defect; supervision is locked dev-mode-only)

The shipped `start` (`tsx src/main.ts`, via `pnpm … start`) runs the script
under the **tsx CLI wrapper** (and pnpm). A supervised `kill -TERM <wrapper pid>`
terminated the wrapper with 143 **without forwarding** to the node child, so the
graceful handler did not run in that path. Interactive Ctrl-C (SIGINT to the
whole foreground process group) DOES reach the node child → graceful;
single-process `node --import tsx` + SIGTERM → exit 0. So the handler is correct;
only a supervised SIGTERM-to-wrapper bypasses it. Worth a note for when
supervised operation lands (an exec-based process entry or a signal-forwarding
launcher). Out of scope for slice 0 (dev-mode-only supervision is locked).

## Did NOT flag (locked decisions)

Fastify; plain TS / no Effect; thin one-process Gateway now; dev-mode-only
supervision; Python interim origin; the fixture standing in for a real router;
tsx runner.
