# Identity seam scout — the browser half (opus)

Read-only. Repo at `be26765b` (PR #328 head, unmerged), base `feat/multi-launch` @ `d1f499e5`.
Citations are `file:symbol`.

**Recommendation up front:** replace, not repair — but the replacement's first slice is
a prerequisite for either path, and "replace" keeps more of #328's *thinking* than its
code. Details in §7.

**Headline counts:** 19 identity write paths across four pre-existing surfaces (plus 6
more introduced by #328's shadow store). The plan's "list of four" covers 6 of the 19
and only one of the four surfaces. One store or two: **two modules, one representation**
— identity leaves `CanvasStoreState` entirely rather than being mirrored beside it.

---

## 1. Identity write paths

### How I searched

I started from the type rather than the plan, because the plan's list is the thing that
has failed twice.

1. `www/packages/canvas/src/model/canvasState.ts:CanvasStoreModel` — read the identity
   fields off the state type, then grepped every assignment of those key names across
   `www/packages`.
2. `grep -rn "\.setState(" www/packages/{canvas,space-client,core}/src` — 19 non-test
   hits, to catch writes that bypass named actions entirely.
3. `grep -rn "spaceId:\|canvasId:\|defaultWorktreeId:" www/packages/canvas/src/model` —
   object-literal writes inside patch builders. This is how
   `worktreeDefaults.ts:defaultWorktreePatch` surfaced.
4. `grep -rn "replaceState\|pushState" www/packages` — the URL is a write surface, not
   only a read source. Cross-checked against the three builders in
   `urlTupleCodec.ts` (`spaceSwitchUrl`, `worktreeSwitchUrl`, `canvasSwitchUrl`) and
   their callers.
5. `grep -rn "setActiveCanvasId\|getActiveCanvasId"` — the module mirror that keys
   persistence.
6. `grep -rn "worktreeId" model/canvasActions.ts model/paneRecords.ts
   model/capturedRunPanes.ts`, then followed `adoptRun` → `capturedRunAdoption.ts` →
   `attachableRun` to the wire boundary. This is the surface nobody has enumerated.
7. Exact read sweep: `useCanvasStore((state) => state.<field>)` and
   `useCanvasStore.getState().<field>` across `www/packages/canvas/src`.

Negative checks I ran, so "not found" is not "not looked for":

- `capturedRunStore.ts:CapturedRunIdentity` is `name | agentId | agentName` only — the
  captured-run store does **not** carry the triple. Not a write path.
- `canvasStore.persistence.ts:partializeExtras` returns `{ paneCounters }`; identity is
  not in the persisted blob today. Rehydrate is not an identity writer for the store
  fields (it *is* one for per-pane pins — surface D).
- `setApiTransport` has no non-test caller, so there is no alternate origin.
- `www/packages/inspector` — **not re-verified.** The plan records it as identity-free
  and I took that on trust.
- The Python and runtime planes are out of browser scope and were not enumerated.

### Surface A — `CanvasStoreState` identity fields (the plan's surface)

| # | Path | Note |
|---|---|---|
| 1 | `canvasState.ts:createInitialCanvasModel`, called by `canvasStore.ts:useCanvasStore`'s creator | module-load write of all three from `INITIAL_LAUNCH_CONTEXT` |
| 2 | `canvasStoreLifecycle.ts:initializeCanvas` — null-canvas branch | `setState` patch |
| 3 | `canvasStoreLifecycle.ts:initializeCanvas` — switching-canvas branch | full model replace |
| 4 | `canvasStoreLifecycle.ts:initializeCanvas` — same-canvas branch | `setState` patch |
| 5 | `canvasStoreLifecycle.ts:selectSpace` | full model replace |
| 6 | `canvasActions.ts:adoptDefaultWorktree` → `worktreeDefaults.ts:adoptDefaultWorktreePatch` | the meta seed |
| 7 | `canvasStore.ts:resetCanvasStoreForTests` | test-only in intent, a production module export in fact |

Plus the escape hatch that makes the count meaningless as a guarantee: `canvasStore.ts`
exports the raw hook with `setState`, and `canvasActions.ts:createCanvasActions` receives
an unrestricted `set`. Any of the ~30 actions can write identity with no compiler
objection. #328 contains two live demonstrations —
`canvasStore.test.ts` and `CommandCenter.spaces.test.tsx` both write `spaceId` /
`defaultWorktreeId` through a bare `setState`.

`worktreeDefaults.ts:defaultWorktreePatch` is exported but has exactly one caller
(`adoptDefaultWorktreePatch`, same file). A second identity writer already sitting on the
public surface, unused.

### Surface B — the module mirror `canvasStoreLifecycle.ts:activeCanvasId`

| # | Path | Note |
|---|---|---|
| 8 | `canvasStoreLifecycle.ts:resolveLaunchCanvasId` at module load | parses `window.location.search` **independently of the route** — a second URL derivation site |
| 9 | `canvasStoreLifecycle.ts:initializeCanvas` assigns `activeCanvasId = canvasId` directly | bypasses its own `setActiveCanvasId` setter |
| 10 | `canvasState.ts:createInitialCanvasModel` calls `setActiveCanvasId?.(canvasId)` | an identity write hidden inside a model constructor |

This mirror is not decoration: `canvasStore.persistence.ts` passes `getActiveCanvasId`
into `canvasCacheStorage.ts:createCanvasCacheStorage`, so it decides *which blob is read
and written*. It is identity state that lives outside the store, outside the URL, and
outside #328's bridge.

### Surface C — the URL

| # | Path |
|---|---|
| 11 | `CanvasCommandDispatcher.ts:activateSpace` → `spaceSwitchUrl` + `replaceState` |
| 12 | `CanvasCommandDispatcher.ts:activateWorktree` → `worktreeSwitchUrl` + `replaceState` |
| 13 | `CanvasCommandDispatcher.ts` `select-canvas` arm → `canvasSwitchUrl` + `replaceState` |

Each is a *separate statement* from the store write beside it. There is no primitive
making URL and store atomic, which is the entire divergence class the plan's §4 calls
"failed selection is atomic" and defers to S5.

### Surface D — per-pane worktree pins (persisted; the value that reaches the wire)

This surface is absent from the plan's §6 table as a *writer* concern and absent from
every S4 review's writer inventory. It matters because `contentRef.worktreeId`, not the
acting worktree, is what `CapturedRunPane` sends to `POST /v1/runs`.

| # | Path | Source of the worktree |
|---|---|---|
| 14 | `canvasActions.ts:addCapturedRun` | explicit arg ?? `getActingWorktreeId()` |
| 15 | `canvasActions.ts:adoptCapturedRun` | **the wire** — `capturedRunAdoption.ts:attachableRun` brands `asWorktreeId(value.worktreeId)` from `GET /v1/runs/{id}` |
| 16 | `canvasActions.ts:continueSession` | `getActingWorktreeId()` |
| 17 | `canvasActions.ts:spawnTerminal` | `getActingWorktreeId()` |
| 18 | persist rehydrate via `canvasStore.persistence.ts:paneRefsForOpenRecords` | the blob |

Path 15 is the sharp one: a server-sourced worktree id enters browser state, gets
persisted, and later drives a launch, without passing any acting-identity writer. Any
seam that guards only Surface A leaves it open.

### Surface E — #328's shadow store (new)

| # | Path |
|---|---|
| 19+ | `actingContextStore.ts`: `selectActingContext`, `clearActingContextForNavigation`, `mirrorLegacyActingContext`, `beginClaim`, `recordVerification`, `resetActingContextStoreForTests`, plus the exported raw `useActingContextStore.setState` |

### Reads, for scale

After #328, exactly **four** direct canvas-store identity reads remain:
`SessionCanvasRoute.tsx` ×3 (`storeSpaceId`, `storeWorktreeId`, `storeCanvasId`) and
`canvasStoreLifecycle.ts:initializeCanvas` ×1 (`switchingCanvas`). Everything else reads
props, command payloads, or inventory rows. This is the number that makes §2's seam
cheap.

---

## 2. Seam feasibility — can a direct write be made unrepresentable?

Yes, and the mechanism is the one nobody has used: **remove the fields from the state
type.**

Three mechanisms exist in this repo. Ranked by strength:

**(a) Field removal from `CanvasStoreState` — a compile error, not a convention.**
If `spaceId`, `defaultWorktreeId`, and `canvasId` are not members of the state type,
`set({ spaceId })` fails to typecheck in every one of the ~30 actions, and
`useCanvasStore.setState({ spaceId })` fails at every call site including tests. No
absence grep, no reviewer vigilance, no file list. This is the only mechanism that
delivers what the design call asks for, and it is not what the design call proposes
(it proposes hiding `setState`, which is weaker: `getState()`-based patches and any
in-package `set` still reach the fields).

Cost is bounded by the numbers above: 7 write sites (Surface A) and 4 read sites.

**(b) Package `exports` map + import-graph boundary.** `packages/AGENTS.md` mandates one
entrypoint per package, and
`www/packages/shell/src/testSupport/importGraphBoundary.test.ts` fails closed on deep
imports and relative reach-ins. If the identity store module is not re-exported from
`www/packages/space-client/src/index.ts`, no consumer outside the package can reach
`setState` at all. Structural, already enforced, free. It does nothing *inside*
`@tm/canvas`, which is why (a) is still needed.

**(c) Named-mutator module.** The in-repo precedent is
`interactions/dnd/dragSessionStore.ts` (`beginDragSession`, `updateDragSessionTarget`,
`endDragSession`), and `actingContextStore.ts` copied its shape faithfully. Both still
export the raw hook. This is convention only — it is exactly what #328 relies on, and
it is why three reviewers each found a different hole in the same convention.

**Recommended combination:** (a) inside canvas + (b) across the package boundary.
Identity fields exist in exactly one module, exported as selectors plus a closed command
union; the raw store never reaches a barrel.

**What cannot be made unrepresentable:** `window.history.replaceState`. No type stops it.
The available lever is the one the plan already uses for retired symbols — route all
three `urlTupleCodec` builders through the single activation function and gate on an
absence grep proving `replaceState` appears in one file. Surface D is likewise not
type-guardable at the wire boundary; it is guardable at the *constructor* — make the
pane ref's worktree obtainable only from a receipt-derived pin
(the plan's `withWorktree(receipt, pin)`), so `asWorktreeId(value.worktreeId)` in
`capturedRunAdoption.ts` cannot flow straight into a pane record.

---

## 3. One store or two

**Would a non-persisted slice of the canvas store satisfy §7? Yes — all three
constraints, verified:**

- *Nothing added to the persist blob*: `canvasStore.persistence.ts:partializeExtras`
  returns `{ paneCounters }` and `paneRefsForOpenRecords` handles panes. Identity is
  already excluded today while living in the same store. The mechanism works.
- *No `CANVAS_STORE_STORAGE_VERSION` bump*: follows from the above; the constant reads
  `1` and is untouched by #328.
- *canvasId not inside the blob it keys*: already solved without a second store, by
  `canvasStoreLifecycle.ts:activeCanvasId` — a module variable read by
  `createCanvasCacheStorage`. That is the existing proof that the keying constraint does
  not require store separation.

So §7 does **not** force a second store, and the plan's implied argument from persistence
is not load-bearing. The honest justification is different and stronger:

**A slice cannot deliver §2's mechanism (a).** Fields on `CanvasStoreState` are writable
by every action's `set`, whether or not they persist. Separation is the only way to make
the field removal meaningful — you cannot remove a field from a store and simultaneously
keep it there.

**Verdict: two modules, one store each, and one representation of the truth.**

The duality the reviewers objected to is dual *writing*, not dual *stores*. #328's real
defect on this axis is that its single new store holds **four** representations of one
truth — `context`, `receipt`, `projectedWorktreeId`, `navigationSpaceId` — while legacy
holds a fifth. Every S4 major traces to a disagreement among those five. The replacement
must have exactly one: identity lives in the identity module, the canvas store has no
identity fields, and legacy getters (if any survive the window) are derived functions,
not stored values.

What the separate module buys, precisely: the compiler seam, plus the package boundary
in (b). What it must not buy: a mirror.

---

## 4. The transport gap

### Which origin serves what, in each mode

`packages/gateway/src/app.ts:buildGateway` mounts `createSpaceRouter` under
`SPACE_CONTEXT_PREFIX = "/v1"` on a private Fastify instance. The browser never learns
its URL in any mode.

| Mode | Browser origin | Where the gateway lives | Can the browser reach `createSpaceRouter`? |
|---|---|---|---|
| **Dev (shell composer)** | Vite dev server; `www/packages/shell/vite.config.ts:buildDevServerProxy` forwards `/api`, `/v1`, `/health` to one `DEV_API_BASE_URL` origin (the Python app) | separate node process | **No** |
| **Desktop (Electron)** | the Python app; `main.py:create_app` serves `/canvas` and `/v1` | explicit `settings.gateway_url`, "Electron-owned desktop" | **No** |
| **Packaged** | the Python app | spawned by `main.py` from `plan_gateway_supervision(settings)` (D1-b); `api/src/transport_matters/gateway/` is embedded in the wheel and, per the project's own CLAUDE.md, *not served* | **No** |

In all three, the Python FastAPI app is the single browser origin, and the gateway is a
private backend peer.

### The one established route, and its precedent

The only way a browser reaches a gateway-owned context is an explicit Python mirror on
`run_proxy.py:create_run_proxy_mount`. `@tm/activity` already works this way, with the
comment stating the rule outright:

> `# Mirror gateway-owned activity through the Python origin for desktop and shell.`

— `run_proxy.py`, above `workspace_activity` and `workspace_activity_stream`.

Two facts that make the fix small and safe:

- **Mount order is already correct.** `main.py:create_app` includes
  `proxy_mount.router` at `/v1` *before* `space_routes.router` at `/v1`, so a mirrored
  `/spaces/acting-context/*` route wins. There is no FastAPI pattern collision anyway:
  Python's POST routes under `/spaces` are `/spaces` and
  `/spaces/{space_id}/worktrees`, neither of which matches
  `/spaces/acting-context/verify`. That is why today's request is a plain 404.
- **The no-gateway branch needs an answer.** When `gateway_url` is absent,
  `runs_unavailable.router` stubs only the five run-lifecycle patterns. A space
  acting-context route would 404 rather than 503 there. The mirror must define its D2
  behaviour explicitly, or the browser cannot distinguish "no gateway" from "route
  missing" — which is exactly the confusion that let this ship.

### Which test would fail if the browser could not reach the route

**None exists today.** That is the finding.

The shape to copy is
`api/src/transport_matters/api/v1/test_run_proxy.py:test_activity_snapshot_and_stream_routes_forward_to_gateway`,
which drives the Python route and asserts the forwarded gateway URL.

A Python forwarding test alone is not sufficient: it pins Python's route string, not the
browser's. The repo already has the cross-plane mechanism for that — the shared JSON
corpus in `packages/contract/fixtures/`, consumed on the TS side by
`packages/contract/src/space/fixtures.ts` and on the Python side by
`api/src/transport_matters/space/testing.py`. `packages/contract` currently declares no
route-path constants (verified by grep), so this is additive: put the two acting-context
paths in the corpus, have `spaceTransport.ts:verifyActingContext` import its path from
there, and assert from the Python side that the app's route table contains them. Two
small tests, one shared source of truth, and the 404 becomes unshippable.

---

## 5. What survives PR #328

**Keep as code (~300 of 1271 added lines, and the expensive part of the thinking):**

- `packages/contract/src/space/wire.ts:ActingContextResult` + the `index.ts` export and
  the `@tm/space` re-export. Correct DRY; all three reviewers agree. Untouched.
- `www/packages/space-client/src/spaceTransport.ts:verifyActingContext` and
  `actingContextFailureCode`. The envelope mapping is right —
  `spaceRouter.ts:sendResult` emits `{ error: <code> }` and
  `core/transport.ts:throwWithDetail` reads `data.error` — so only the path and origin
  are wrong. Keep, repoint at the mirrored path from §4.
- `www/packages/space-client/src/domain/actingContext.ts:resolveActingContext`. This is
  the eventual authority and it is worth keeping, with two fixes: the clear transition
  drops the generation watermark, and `via: "verified-claim"` is not sticky against a
  later `acting` event. Keep the shape, fix the two transitions.
- `domain/actingContext.test.ts` — the five transition tests and the corpus test.
  Strengthen the corpus test's failure branch (it currently asserts only
  `phase !== "acting"`, which every failure satisfies trivially).
- `commandTypes.ts` / `commandRows.ts` `anchorWorktreeId`. This is the fix for solmax's
  blocker and is needed under any design.
- The `commandRows.test.ts` → `canvasRows.test.ts` split. Already clean, no coverage
  lost.

**Discard:**

- `actingContextStore.ts` in full (203 lines) and `actingContextStore.test.ts` (168) —
  the four-representation store, `mirrorLegacyActingContext`, `projectedWorktreeId`,
  `beginClaim`'s request gating, `discardedVerificationCount`.
- `canvasStoreLifecycle.ts:syncActingContextFromCanvasState` and its five call sites —
  the dual-write bridge itself.
- `actingContextConsumerCoverage.test.ts` — replaced by the compiler seam plus one
  absence grep. A hand-maintained file list cannot do this job.
- The injected-divergence tests in `canvasStore.test.ts` and
  `CommandCenter.spaces.test.tsx` — they assert the shadow beating legacy, which the
  seam makes unrepresentable.
- The reader migrations in `CommandCenter.tsx`, `useLauncherData.ts`,
  `CanvasWorkbench.tsx`, `canvasActions.ts` — the *intent* survives and is redone in B3
  against the real owner, but the code as written carries the receipt-or-null divergence
  (fable Major 1 / solmax Major 1 / my M-4) and does not survive.

The design call estimates a third survives. On line count I make it closer to a quarter;
on value it is higher than either number, because the reducer and the shared corpus are
the parts that took judgment.

---

## 6. Revised slice plan (replaces S4–S6)

Each slice is PR-sized, independently gated, one writer at every stage. Gate baseline is
the repo recipe verbatim, `just check && just test`, plus the additions named.

**B1 — make `@tm/space` reachable.** Mirror `POST /spaces/acting-context/verify` and
`/resolve-workdir` through `run_proxy.py:create_run_proxy_mount`, in a
`controlplane_gateway_space.py` beside `controlplane_gateway_reads.py`. Define the
no-gateway (D2) answer. Move both route paths into the shared fixture corpus and consume
them from `spaceTransport.ts`. Zero browser behaviour change.
*Gate:* forwarding test shaped like `test_activity_snapshot_and_stream_routes_forward_to_gateway`,
plus the cross-plane path assertion from both planes.
*Works without B2:* yes — the S2 surface finally exists end to end.
**This lands first under either recommendation.** It is the only slice that is pure gain
whether the owner repairs #328 or replaces it.

**B2 — the activation seam, behaviour-preserving.** Introduce one module in
`@tm/space-client` owning a closed command union
(`selectSpace | selectWorktree | selectCanvas | adoptWorkdirDefault | initializeFromLaunch`)
and make it the sole performer of the paired URL write, legacy store write, cache-key
set, and `persist.rehydrate()`. Move the bodies of `activateSpace`, `activateWorktree`,
the `select-canvas` arm, `adoptDefaultWorktree`, `initializeCanvas`, and `selectSpace`
behind it. **It writes only the existing legacy fields.** No aggregate, no new state, no
reader migration.
*Gate:* absence grep proving `replaceState` and the three `urlTupleCodec` builders appear
only in the activation module; every existing dispatcher, route, and store suite
unchanged and green.
*Works without B3:* yes.

**B3 — field removal; the seam becomes a proof.** Delete `spaceId`,
`defaultWorktreeId`, `canvasId` from `CanvasStoreState`; the activation module owns them.
Migrate the 4 remaining direct reads and the #328 reader set onto its selectors, each
preserving **legacy per-field null semantics** rather than all-or-nothing, so the
"Current" marker and the pane-layer props do not change. Fold Surface B's mirror into the
same owner.
*Gate:* grep proving zero identity fields on `CanvasStoreState`; a test pinning the
worktree-only tuple still marking "Current" (the divergence all three reviewers found);
persist-OLD-snapshot-then-rehydrate.
*Works without B4:* yes. **After this slice a new identity writer is a type error.**

**B4 — authority flip.** `ActingContext` becomes the module's state from its first
production commit; there is never a second live representation. Selection installs
verified inventory rows; URL and locator candidates verify through B1; failed selection
is atomic. Solmax's anchor-vs-default separation lands here — the receipt carries
`anchorWorktreeId`, the spawn target stays a distinct concept — and Surface D's pins
become `withWorktree(receipt, pin)` so a wire-sourced worktree cannot enter a pane record
unmediated.
*Gate:* the plan's existing six S5 tests, each red before the flip, plus one live browser
A/B.
*Works without B5:* yes.

**B5 — locator and contraction.** Unchanged from the plan's S6: window-scoped
`sessionStorage` locator, delete the retired symbols, absence greps, and the
`CANVAS_STORE_STORAGE_VERSION` assertion.
*Works alone:* yes.

*Optional, not a slice:* a pure comparator running the old precedence and the new reducer
over the same command, reporting inequality in dev builds only. This is the design call's
observation point, and it needs no store, no generation lifecycle, and no reader surface.

Bounding constraints hold throughout: no seeding (B1 mirrors read-only S2 surfaces;
`resolveWorkdirContext` is already fail-closed), one command surface (⌘K and MCP both
terminate at `_resolved_domain_request`, untouched), `CANVAS_STORE_STORAGE_VERSION`
unchanged (B3 and B5 both assert it), verification stays narrow (checkout presence is
never consulted).

---

## 7. Recommendation, and the case against it

**Replace, with B1 first.**

The two blockers in #328 are structural, not local. The verify route was never reachable
from any browser origin, and the bridge's central mapping publishes
`defaultWorktreeId` where the contract demands the canvas anchor — so the projection is
wrong at the point of the mapping, not at one call site. Every major, across three
independent reviewers, resolves to the same missing thing: there is no choke point, so
totality is a claim about a file list rather than a property of the code. Adding a
fifth representation of identity to a system whose defect is that identity has four was
the wrong move, and no amount of ledger machinery fixes it — a detector maintained by
hand next to a convention maintained by hand fails the same way twice.

The replacement is also *smaller*. B2 and B3 together delete more than they add: seven
write sites collapse into one command union, four read sites move, and the shadow store,
its bridge, its ledger, and its coverage checklist all go away. The safety argument stops
depending on anyone understanding the bridge.

**The honest counterargument.** #328 is green, nine checks pass, and it is one round of
fixes from plausible. B3 is a bigger single blast radius than any slice shipped so far —
it edits the state type that ~30 actions and the whole persist path depend on, and if it
goes wrong it takes the canvas with it, whereas #328's worst failure is confined to a
shadow no production reader consumes. Someone arguing for repair would say: fix the four
majors, fix the route, keep the expand-then-contract sequencing the plan already
committed to, and do not bet the canvas store on a refactor mid-migration.

My answer is that B3's blast radius is *enumerated* — 7 writes, 4 reads, listed above by
symbol — and the compiler reports every one I missed, on the first build. #328's blast
radius is unbounded in the other direction: it is convention-based, and three reviewers
each found a different hole in the same convention, which is the empirical signal that
the fourth hole exists and none of us found it.

One concession to the counterargument, and it is not rhetorical: if the owner wants the
smallest correct step and nothing more, **land B1 alone and re-decide.** It is required
either way, it is small, it is testable, and it converts the S4 verification wiring from
fiction into something whose behaviour can actually be observed before anyone commits to
a design for the rest.
