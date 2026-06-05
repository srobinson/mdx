# PR#353 review — first-run harness cards (slice 1a)

Branch `ml/firstrun-cards`, head `0c506e94`, baseline `main` `101287bf`.
Worktree verified pristine (`git status --porcelain` empty) before and after review. Read-only, no writes to the tree, no gate run (the tree is the builder's).

Three independent passes, reconciled here. Every finding was verified first-hand against the Python producer or the sibling code it cites; nothing is carried on another reviewer's word.

**Verdict: 2 Blockers, 4 Majors, 10 Minors.**

> **Delta round `a8496feb` verified — 15 fixed, 1 overruled on the builder's contest. Nothing remains. See "Delta verification" at the end.**

Both Blockers are the same failure: the screen states, as fact, something the evidence does not support. That is the one thing this slice exists to not do.

---

## Blocker 1 — an installed harness is reported as "Check failed"

`www/packages/canvas/src/firstrun/harnessCards.ts:62-81`

`installedFact` tests `install.status === "probe_failed"` (line 73) before `install.installed === true` (line 76). On the producer side that ordering is exactly backwards. `build_harness_observation` (`api/src/transport_matters/harnesses/probes/observation.py:55-79`) emits `status="probe_failed"` on precisely one branch, and that branch always carries `installed=True` with a real `executable_path`:

```python
# observation.py:69-79 — executable found, --version unparseable
installed=True,
executable_path=capability.path,
raw_version=None,
status="probe_failed",
reason=_VERSION_PROBE_FAILED_REASON,   # = "harness_version_unknown"
```

The docstring says it outright: "An absent executable is a complete observation of absence, not a failure. A found executable whose version probe returned nothing is `probe_failed`."

So a user who *does* have Claude Code installed, whose `--version` output the parser did not recognise, reads:

> **INSTALLED** Check failed — `harness_version_unknown`

with the Compatible row directly beneath it saying "Version unknown". The primary fact is false, the two rows contradict each other, and the raw enum leaks into the product surface while `PROBE_FAILURE_DETAILS` humanizes the equivalent codes one function away (`harnessCards.ts:91`).

Fix: test `installed === true` first and render the version failure as that fact's *detail*, which is what it is. Humanize `install.reason` the way probe reasons already are.

**The test pins the wrong behaviour.** `harnessCards.test.ts:68-78` asserts this exact output from a fixture the API cannot produce — `observed: true, status: "probe_failed"` with `installed` left at its `null` default and `reason: "version parse failed"` (the real value is `harness_version_unknown`). The fixture was written to match the code rather than derived from the producer, so the suite certifies the defect. This is the recorded lesson about probe fixtures: build them from what the real channel emits.

## Blocker 2 — the screen asserts absence it has not observed

`www/packages/canvas/src/firstrun/FirstRunScreen.tsx:94` → `harnessCards.ts:48`

`anyConfirmedInstalled` returns false for two different worlds: "observed, and absent" and "not observed yet". The note it gates states only the first:

> No harnesses are installed. That is a valid state: Transport Matters is fully operational without them.

The startup refresh is fire-and-forget — `main.py:403` schedules `run_startup_refresh(refresh)` with `asyncio.create_task`, never awaited — so on a fresh install every item arrives `observed: false` while the probes are still running. The screen renders cards reading "Not yet checked" directly above a claim that nothing is installed. That is the *default* first-run rendering, not an edge case, and it is false for a user who has a harness installed.

`installedFact` makes exactly this distinction correctly at `harnessCards.ts:64`. The summary needs the same three-way split: all observed and absent → the valid-state note; nothing observed yet → a pending statement; mixed → neither.

## Major 1 — the pending state has no way forward

`www/packages/canvas/src/firstrun/useHarnessInventory.ts:19`

A mount-time snapshot: `staleTime: 30_000`, no `refetchInterval`, and nothing invalidates `harnessInventoryKey` anywhere in the tree. When the background refresh finishes writing rows, nothing re-reads them, and `retry` is reachable only from the `error` branch — the pending branch offers no affordance. A user who opens the app during the refresh window sits on "Not yet checked" until they reload the entire app. Since the likely behaviour is to leave this screen open while going off to install or sign in, this is the common path, not the unlucky one.

The codebase has the idiom: `workbench/spaceCommandDispatcher.ts:142`, `core/src/exchangeStreamEvents.ts:263`. A poll while any item is unobserved, or invalidation driven off the refresh completing, closes it.

## Major 2 — cross-plane mirror with no drift guard

`www/packages/core/src/types/harnessInventory.ts:1`

173 hand-written lines mirroring `inventory.py`, `connections.py`, `compatibility.py`, `resolver.py`, and `resolver_contracts.py`. Accurate today — checked member for member — with nothing keeping it accurate tomorrow.

The house convention for this exact boundary is both-sides pinning: `core/src/types/harnessDescriptors.test.ts` binds `capabilities.ts` to `shared/harness_descriptors_v1.json` byte for byte, with `api/.../harnesses/test_registry.py` holding the Python side. That test's own comment describes the guarantee this file lacks. `ARCHITECTURE.md:131` states the rule: single source any contract that crosses a boundary between planes, packages, or languages.

## Major 3 — total switches with no runtime fallback

`harnessCards.ts:121, 129, 143, 170`

`compatibleFact` and `authenticatedFact` switch exhaustively with no `default`, and `AUTH_METHOD_LABELS[method]` / `PROBE_FAILURE_DETAILS[reason]` are unguarded record lookups. TypeScript proves these total against the *mirror*, not against the API. Compounding Major 2: one new `CompatibilityOutcome` member on the Python side (`compatibility.py` anticipates that growth) makes the switch return `undefined`, `CardView` dereferences `fact.status`, and the render throws. There is no `ErrorBoundary` in canvas or host — grepped both, zero hits — so a backend-only change blanks the first-run window.

Drift should degrade one fact, not the screen.

## Major 4 — the default-connection fallback invents a resolution the domain refuses

`harnessCards.ts:161-165`

```ts
return connections.find((connection) => connection.is_default) ?? connections[0];
```

`resolve_connection` (`api/.../harnesses/connections.py:225-244`) is explicit: a sole connection resolves implicitly; several connections require exactly one explicit user-selected default; anything else is `connection_ambiguous`. The `?? connections[0]` branch fires in precisely the case the backend declines to resolve, and renders an arbitrary row's evidence as *the* harness's authentication state, attached to no visible connection identity. A user with two connections and no default can read "Signed in via API key" here while the launcher treats the harness as unresolvable.

The `is_default` lookup is right; the fallback is only right for the sole-connection case. Otherwise state the ambiguity, in the vocabulary the resolver already owns.

## Minors

1. **Enablement is dropped.** `harnessCards.ts:43` — `enablement` and `launch_options[].exclusion_reasons` are carried in the payload and never read. A harness the operator disabled (`enabled: false`, `eligible: false`) renders Installed / Signed in / Compatible with nothing to say it will not launch, on a screen whose lede promises "what this machine can capture and launch".
2. **Workbench effects run behind the first-run screen.** `SessionCanvasRoute.tsx:161` — the `firstRun` return sits after every effect, so lines 99-158 still run: the workspace activity WebSocket, `spawnOrFocusTranscript` (spawning a pane nobody sees), and the captured-run reconciler, which calls `dropRun`/`dropCapturedRunPane` at lines 143-144 and mutates persisted canvas state while an unrelated screen is displayed. Latent today because `?firstrun=1` is explicit and launch params are rarely present; slice 1b makes this the startup path and runs it on every cold start.
3. **The dated probe claim freezes at mount.** `FirstRunScreen.tsx:91` → `harnessCards.ts:37,151` — `nowMs` is captured from `Date.now()` at render with nothing re-rendering, so "probed 2m ago" still reads 2m an hour later. It under-reports evidence age, the one direction this screen cannot afford. `useElapsedTick(active, sinceTs)` in `@tm/core` owns this (`RunVitalsStrip.tsx:53`, inspector `ExchangeTurnCard.tsx:245`). Other `formatRelativeAge` callers do not tick either, so this matches house behaviour; flagged because dated evidence is this screen's stated claim.
4. **`storageKeys.test.ts` not updated.** `infrastructure/persistence/storageKeys.ts:12` — that test pins each key's literal value and exists for exactly that purpose; the one key that just changed is the one it does not cover. It passes because it enumerates by hand, which is the gap.
5. **The hint key rename is unmigrated.** `launcher/FirstRunHint.tsx:4` — moving the inline key into the registry is the correct fix, but the value changes with no read-old-key fallback, so everyone who has dismissed the ⌘K hint sees it once more. Benign and one-shot; still a persisted-state change shipping without a migration.
6. **Loading is invisible to assistive tech.** `FirstRunScreen.tsx:59` — `aria-hidden="true"` on the skeleton container where every canvas sibling sets `aria-busy="true"` (`SessionPickerPane.tsx:118`, `registry.tsx:190`, `TranscriptChatPane.tsx:115`, `CapturedRunPane.tsx:89`). A screen reader lands on the heading with a body explicitly hidden and no in-flight signal.
7. **No live region, so recovery is silent.** `FirstRunScreen.tsx:56-104` — the error branch has `role="alert"`, but a successful Retry just swaps content, announcing nothing. `launcher/CommandCenter.tsx:105` is the house pattern.
8. **Retry gives no feedback while retrying.** `FirstRunScreen.tsx:73`, `useHarnessInventory.ts:23` — `isError` stays true through the refetch, so the alert and button look identical before and during. Against a down store the slow case is the common case. The hook does not expose `query.isFetching`.
9. **`isFirstRunCanvas` duplicates `isStressCanvas`.** `route.ts:5-13` — identical but for one literal. One `hasCanvasFlag(search, name)` leaf collapses both before a third flag repeats it.
10. **`FetchStatus` borrowed across owners with no home.** `FirstRunScreen.tsx:3`, `useHarnessInventory.ts:4` — the four-state contract lives in `launcher/` (command palette grammar) and is now imported by a second top-level owner. It belongs to neither; it wants a shared leaf at `src/` root.

---

## Checked and clean

- **Contract fidelity.** The mirror matches the Python models member for member, including the six response groups, `LaunchOption`/`CompatibilityAdvisory` from `resolver.py`, and the `observed` / `installed: null` distinction. `_InventoryModel` sets only `frozen=True` — no alias generator, no `exclude_none` — so the header's "every field present, unset optionals arrive as null" claim holds today.
- **Route.** `/v1/harnesses` matches the mount at `main.py:497`, not the `/api` aggregate. The single 503 (`api/v1/harnesses.py:22`) is the state the screen renders.
- **Stale evidence.** Correct for the right reason: the backend suppresses `authentication_status` when evidence is stale, and `harnessCards.ts:108-119` reads that null as pending rather than inventing a status.
- **Timestamps.** `observed_at` is written from `datetime.now(UTC).isoformat()`, so it carries an offset and `new Date()` parses it as UTC. No local-time skew.
- **Identifiers standard.** Reuses the existing `HarnessId` union mirroring the closed Python `Literal` (`harnesses/__init__.py:15`, pinned by `test_registry.py:78`). No new brand, no branded ephemeral id.
- **Import boundaries.** `@tm/core/types/*` is a published entry in core's `exports` map and the settled canvas convention (~25 files). Value imports go through the index. No relative reach-in across packages.
- **Query conventions.** `useHarnessInventory` is shape-identical to `launcher/useSpaces.ts` and `useRuntimeTemplates.ts`. No twin fetch layer, no new enum; key added to the shared `core/src/queryKeys.ts`.
- **Reuse execution.** `canvas-button` and `canvas-picker__skeleton` live in `workbench/canvas.css`, imported globally by `index.css`, and are already used outside their nominal blocks. Nothing reinvented where the reuse map names an owner.
- **CSS.** All 14 custom properties resolve in `styles/tokens.css`. Tone is decorative only. `prefers-reduced-motion` disables all three animations (`firstrun.css:245`).
- **Mount.** `QueryClientProvider` sits above `SessionCanvasRoute` (`main.tsx:22`), so the early return is inside the provider; all hooks run before the branch, so theme tokens still apply.
- **Test hygiene.** Isolated and fixed-clock; each `SessionCanvasRoute.test.tsx` case pushes its own URL, so the new case leaks no state. Coverage gaps track the defects: nothing covers the installed-but-unparseable-version state, the all-unobserved fresh install, the multi-connection-without-default case, or the pending→observed transition.

## ARCHITECTURE.md two-way conformance

No new architectural fact to record: the slice adds a read client inside an existing product-plane package, introducing no context, serving root, brand, or cross-plane contract. Being the first frontend consumer of `/v1/harnesses` is a product fact, not one the document states or needs to.

The document bears on the diff in the other direction, and Major 2 is where: `ARCHITECTURE.md:131`'s magic-string rule is the rule the unguarded mirror sits outside of.

## Builder quality and trust verdict

Real craft in the shape work: the Python contract was mirrored faithfully with its null-versus-absent semantics preserved and sourced in comments, sibling conventions were followed rather than reinvented, the copy holds a deliberate honest-state line, and the CSS and reuse decisions are disciplined. Nothing is careless and nothing is over-built.

The defects share one shape, and it is not carelessness. Every one of them is a state that exists *between* two moments: before the refresh lands, while a retry is in flight, as evidence ages, when the contract moves a release later, when a probe half-succeeds. The static snapshot was reasoned about with care; the transitions were not reasoned about at all.

Blocker 1 adds a sharper edge. The producer's own docstring states the semantics the card gets backwards, and the fixture at `harnessCards.test.ts:71` was written to match the code rather than derived from `observation.py` — encoding a state the API cannot emit, so the suite certifies the bug. That is the probe-fixture lesson repeating in a new place: fixtures for a foreign producer must come from the producer.

Delegating comparable scope stays reasonable, with two conditions on the brief: name the time dimension explicitly (what renders before the data exists, what moves it forward, what happens when the contract grows), and require that any fixture standing in for another plane's output be derived from that plane's emitter, with the source cited.

---

# Delta verification — `a8496feb`

`git diff 0c506e94..a8496feb`, 19 files, +898/-112. Worktree pristine before and after. Deltas only, verified against the producer first-hand as before.

**15 of 16 fixed. 1 overruled — the builder's contest is correct. Nothing remains.**

## The three items flagged for special attention

**(a) One installation-state model, not three patches.** `installationState(installation)` (`harnessCards.ts`) is a single classifier over three worlds — `unknown` (no observation row), `absent` (a dated fact), `installed` — and all three renderings derive from it: the per-card fact (`installedFact` switches on it), the summary note (`inventorySummary` maps over it), and the poll condition (`hasUnobservedInstallation`). The ordering is now correct and the comment cites the producer branch that makes it correct. An observed row with no verdict returns `unknown` rather than asserting. Confirmed one model with three consumers, not three independently patched sites.

**(b) Fixtures derived from the emitter.** `build_harness_observation` (`observation.py:55-90`) has exactly three return branches, and the three new fixture builders match them field for field:

| `observation.py` branch | fixture |
|---|---|
| no executable → `installed=False`, `path=None`, versions `None`, `status="ok"` | `observedAbsentInstallation()` |
| executable found, `version is None` → `installed=True`, real path, versions `None`, `status="probe_failed"`, `reason="harness_version_unknown"` | `versionProbeFailedInstallation()` |
| executable + version → `installed=True`, real path, raw + normalized, `status="ok"` | `observedInstalledInstallation()` |

Source cited in the file header, and the impossible fixture from the old `harnessCards.test.ts:71` is gone. The state that produced Blocker 1 can no longer be authored by hand.

**(c) Vocabulary pinned from both planes.** `shared/harness_inventory_vocabulary_v1.json` holds 11 closed vocabularies. Python: `test_inventory_vocabulary.py` reads the fixture and asserts equality against `get_args()` over the real `Literal` aliases imported from `connections.py`, `compatibility.py`, and `resolver_contracts.py`. TypeScript: `harnessInventory.test.ts` binds the same fixture to an authored `EXPECTED`, plus an `Equal<…>` tuple that fails *typecheck* if any union widens or narrows. A member moving on either plane fails a gate. This is the `harnessDescriptors.test.ts` pattern applied to the boundary Major 2 named.

Residual, stated for the record and not a finding: the pin covers the closed vocabularies, not the models' field shape. A renamed or added *field* on `HarnessInstallationInfo` still drifts silently — though it now degrades through `installationState`'s `unknown` rather than throwing, and the ErrorBoundary contains what does throw. The failure mode Major 2 named is closed.

## Contest on Minor 8 (Retry feedback) — OVERRULED

The builder is right, and the evidence is in the installed library, not in reasoning about the API.

`@tanstack/query-core@5.101.2`, `src/query.ts:710-728`:

```ts
export function fetchState(data, options) {
  return {
    fetchFailureCount: 0,
    fetchStatus: canFetch(options.networkMode) ? 'fetching' : 'paused',
    ...(data === undefined && ({ error: null, status: 'pending' } as const)),
  }
}
```

The `fetch` action spreads this (`query.ts:648-653`), and `isError = status === 'error'` (`queryObserver.ts:559`). So refetching an errored query that holds **no data** resets `status` to `pending` and clears the error: `deriveFetchStatus(false, undefined)` returns `loading`, and the screen swaps the alert for the busy skeletons plus the "Checking harnesses…" live region. On the first-run path — a 503 before any success ever lands — a disabled "Retrying" button on a persisting alert is unreachable code. My finding described a dead button on exactly that path, and it was wrong.

The pinning test is honest: `FirstRunScreen.test.tsx:119` fails the first request, clicks Retry, holds the second response open on an unresolved promise, and asserts `aria-busy="true"` on the skeletons and the live-region text while it is in flight. It fails if the alert persists.

Narrow corner, noted and not re-raised: once a query *has* data, `fetchState` no longer resets status, so a success → failed-refetch → Retry sequence does keep a static alert. That is a different path from the one I reported, and not worth machinery.

## Every other finding

| # | Finding | Outcome |
|---|---|---|
| B1 | installed harness reported "Check failed" | **Fixed** — `installed` read before `status`; a failed version probe is now a detail ("Version unknown: the version probe returned nothing readable.") on an installed harness. Reason codes humanized with raw-code fallback. |
| B2 | absence asserted without observation | **Fixed** — `inventorySummary` returns `some_installed` / `none_installed` / `checking` / `partial`; only `none_installed` (every harness observed absent) states the valid zero-harness case. |
| M1 | no way forward from pending | **Fixed** — `refetchInterval` polls at 3s while `hasUnobservedInstallation`, stops when every harness has a row. Pinned by three cases in `useHarnessInventory.test.ts`. |
| M2 | mirror with no drift guard | **Fixed** — see (c). |
| M3 | total switches, no runtime fallback | **Fixed** — `default` arms on both switches, `Partial<Record<string, …>>` lookups with `?? raw code`, and a real `FirstRunErrorBoundary` with a Reload action. Trade-off accepted and correct: widening the lookup keys to `string` gives up compile-time exhaustiveness, which the new vocabulary pin now catches at the gate instead. |
| M4 | invented connection resolution | **Fixed** — `resolveConnection` mirrors `connections.py:237-244` exactly (0 → none; 1 → implicit; N with exactly one default → that one; else ambiguous) and renders "Connection ambiguous" with evidence withheld. |
| m1 | enablement dropped | **Fixed** — `card.enabled` renders "Disabled on this executor. It will not launch." (`launch_options[].exclusion_reasons` still unrendered; out of this slice's stated scope.) |
| m2 | workbench effects behind the screen | **Fixed** — all four gated on `!firstRun` with deps updated, so no activity stream, no pane spawn, and no captured-run pruning of persisted state. 1b inherits the containment. |
| m3 | frozen probe age | **Fixed** — `useElapsedTick` keyed to `newestProbeObservedAt(items)`, inactive when nothing dated is on screen. |
| m4 | `storageKeys.test.ts` not updated | **Fixed** — `launcherHintSeen` pinned. |
| m5 | hint key unmigrated | **Fixed** — legacy `tm.launcher.hintSeen` honored as a read fallback. |
| m6 | loading hidden from assistive tech | **Fixed** — `aria-busy` on the container, `aria-hidden` moved to the decorative bars. |
| m7 | no live region | **Fixed** — visually-hidden `role="status"` + `aria-live="polite"`; the error branch announces nothing, leaving `role="alert"` to speak once. |
| m8 | Retry feedback | **Overruled** — see contest above. |
| m9 | `route.ts` duplication | **Fixed** — `hasCanvasFlag(search, name)` with both flags as thin callers. |
| m10 | `FetchStatus` had no home | **Fixed** — `canvas/src/fetchStatus.ts` leaf at package root; verified a single definition survives repo-wide, with `launcher/commandTypes.ts` and `commandRows.ts` re-exporting for existing callers rather than keeping a copy. |

No gate run (the tree is the builder's), so this is a static verdict on the deltas; CI or the builder's own `just check`/`just test` remains the runtime authority.
