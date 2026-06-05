# Canvas status row / "Native · Claude" archaeology (updated)

**Branch:** `ml/s3-cmdk` @ `699fb578` (worktree left pristine).
**Method:** `git log -S`, `git show`, `git log --follow` on owning files. No checkout of other refs in this worktree.

**Frame correction:** Owner invariant "all canvas runs are captured runs" is **consistent with the code for agent panes titled `Claude-N` / `Codex-N`**. The header string `"Native · Claude"` does **not** mean `contentRef.kind !== "captured-run"`. It means a **captured-run** pane whose agent-identity fields are all nullish. Prior note about intentional empty strip still describes the *render* path when vitals are missing; it is not a claim that non-captured chrome is acceptable for canvas runs.

---

## (1) Where does `"Native"` come from?

| Item | Evidence |
|------|----------|
| File + symbol | `www/packages/canvas/src/workbench/PaneWindow.tsx` → `PaneWindow` |
| Expression | `` `${run?.agentName ?? run?.agentId ?? capturedRef.agentId ?? "Native"} · ${harnessLabel(capturedRef.provider)}` `` |
| Variant that produces it | **Only** when `pane.contentRef.kind === "captured-run"` (same gate that mounts `RunVitalsStrip`) |
| Meaning of `"Native"` | Fallback label when store + ref have no `agentName` / `agentId` — i.e. a **native harness** captured run (no specialist agent binding), not a different pane kind |
| Product vocabulary | `paneRecords.ts` documents `CAPTURED_RUN_PROVIDERS` as the managed harnesses spawnable as captured runs ("Native" agents) |

Introduced deliberately in:

- **`e874c30f`** (2026-07-14) `feat: surface managed agent runtimes (#286)` — commit body: "Native Claude and Codex launches remain first class. A native launch omits agent and requires harness."

Before `e874c30f`, `PaneWindow` had no subtitle; strip already gated on `kind === "captured-run"` since `350e50c1`.

---

## (2) Paths that create `contentRef.kind !== "captured-run"`

These are **non-run chrome / other viewers**, not the Claude-N agent path:

| Path | Symbol / site | Kind |
|------|----------------|------|
| Default empty canvas | `canvasState` picker seed | `session-picker` |
| Bare shell terminal | `canvasActions` `spawnTerminal` | `terminal` |
| Transcript focus | `canvasActions.spawnOrFocusTranscript` | `session-timeline` |
| Dev lab | `canvasActions` (developers domain) | `dev-blank` |
| Resource / exchange viewers | resource spawn paths | `resource` / `provider-exchange` |

**Agent run spawns** go through `canvasActions.addCapturedRun` / `adoptCapturedRun` / `continueSession` → `spawnCapturedRunPane` → `spawn.createCapturedRunRef` → always `kind: "captured-run"`.

`createCapturedRunRef` has been `kind: "captured-run"` since provider-parametric panes:

- **`34feb9ee`** (2026-06-09) `feat(canvas): provider-parametric captured pane + capability-gated spawn (#69)` — first reverse hit for `kind: "captured-run"` in history.

Non-captured kinds have existed in parallel for non-agent chrome (terminal, picker, resources) since the canvas package era (`ec354ba7` and earlier dock work); they are not "Claude-N runs".

---

## (3) Did canvas runs stop being uniformly captured runs?

**No commit demoted agent/canvas runs from `captured-run` to another kind.**

- Claude/Codex pane titles (`labelFor` → `Claude-N` / `Codex-N`) are allocated only on the `spawnCapturedRunPane` path (`canvasActions.spawnCapturedRunPane` + `spawn.labelFor` + `harnessLabel`).
- `git log -S'?? "Native"'` on `PaneWindow` points only at **`e874c30f`**, which **adds** identity subtitle on the existing captured-run gate; it does not change `contentRef.kind`.
- Non-captured variants (terminal, picker, …) **existed all along** for non-run surfaces. They did not "recently become" the agent-run path.
- What **did** become newly user-visible on captured runs: the word `"Native"` as subtitle (`e874c30f`), and the always-on vitals slot that collapses when activity is missing (`350e50c1`).

So: **no single culprit demoting kind**; the history shows captured-run agent panes throughout, with **`e874c30f` deliberately labeling agent-less captured runs "Native"**.

---

## (4) Deliberate vs incidental for the `"Native"` label

**Deliberate.** `e874c30f` message and archived plan state native launches omit `agent` and remain first-class. The `"Native"` fallback is intentional product copy for agent-less captured runs, not collateral from `699fb578`.

`699fb578` (`feat(canvas): sticky launch identity and CMDK reachability from empty DB`) does **not** touch `PaneWindow`, `RunVitalsStrip`, or `createCapturedRunRef` kind. Ruled out for both the Native string and strip mount gate.

---

## (5) Shared root with MCP / SSE adoption?

| Path | How panes appear | Kind | Identity subtitle |
|------|------------------|------|-------------------|
| Client CMDK / launcher | `addCapturedRun` → immediate `spawnCapturedRunPane` | `captured-run` | `"Native · {Harness}"` if no `agentId`; agent name if template bound |
| Service / MCP | Activity SSE → `CapturedRunAdoptionReconciler` (`capturedRunAdoption.ts`) → `adoptCapturedRun` | still `captured-run` | Store identity from lookup; title uses `identity.name` when present (not `Claude-N` counters unless name missing) |

Adoption introduced:

- **`e05373b6`** (2026-07-12) `feat(controlplane): S6b canvas adoption reconciler (#283)` — deliberate: "adopt service-launched runs".
- Identity plumbing on adopt: **`e874c30f`** extended `adoptCapturedRun(..., identity?)`.

**Shared surface, not shared "wrong kind" bug:**

- MCP that never inserts a client pane relies on SSE adoption (`SessionCanvasRoute` wires frames to both `runVitalsStore.applyFrames` and the reconciler). Failure modes: never appears as pane (adoption dormant/gone), or appears late.
- A **visible** `Claude-1` with `"Native · Claude"` is the **client native spawn** shape (`labelFor` counters + missing agent identity), **not** proof of non-captured kind.
- Empty vitals on that pane still means missing `runVitalsStore.byRunId[runId]` (or unbound `runId`), while the strip shell is mounted — same captured-run chrome as Codex with `"0 tok" / Idle"`.

If MCP runs are promptable server-side but never adopted, that is **`e05373b6` adoption / activity workspace membership**, not a contentRef-kind demotion. It can share the **activity stream workspace id** with empty vitals for some runs, but the Native header alone does not diagnose that.

---

## Answers in one table

| Q | Answer |
|---|--------|
| (1) Native source | `PaneWindow` fallback on **captured-run** only; agent identity missing |
| (2) Non-captured creators | picker / terminal / transcript / resource / dev-blank — never emit `"Native · Claude"` |
| (3) Uniform captured demotion? | **No** — agent runs have been `captured-run` since `34feb9ee`; Native is a label on that kind from `e874c30f` |
| (4) Culprit for Native string | **`e874c30f` deliberate** (not `699fb578`) |
| (5) MCP root | Same family of service-vs-client insertion (`e05373b6`); not "kind left captured-run" |

## SHAs

| SHA | Date | Role |
|-----|------|------|
| `34feb9ee` | 2026-06-09 | First `kind: "captured-run"` agent panes |
| `350e50c1` | 2026-07-10 | Always-on vitals strip; empty shell until activity |
| `e05373b6` | 2026-07-12 | SSE adoption of service/MCP runs into captured panes |
| `e874c30f` | 2026-07-14 | `"Native"` subtitle + agent identity on captured runs (**deliberate**) |
| `699fb578` | HEAD | Identity stickiness / CMDK; **not** strip or Native source |
