# Audioface Slice 2 Studio Acceptance Proof

Date: 2026-08-18
Repo: `/Users/alphab/Dev/LLM/DEV/helioy/audioface`, `main` at `4db2ef9`, tree clean before and after.
Spec: `docs/superpowers/specs/2026-08-17-flow-persistence-slice-2.md`, sections "Studio acceptance proof" and "Completion criteria".
Studio: `pnpm run start:studio`, Vite 8.1.3 on `http://127.0.0.1:4174/` (`--host 127.0.0.1 --port 4174 --strictPort`).
Browser: agent-browser (Chromium, session `af2`), viewport 1440x900.
Screenshots: `~/.mdx/projects/audioface-proof2/`.

Result: **11/11 PASS** (8 numbered spec steps plus 3 additional outcomes named in the work item). No fixes applied; nothing was changed in the repo.

## Audio evidence method

Headless Chromium produces no audible output, so playback was proven by instrumenting the Web Audio scheduler in the page before each Play:

```js
window.__afProbe=[];
for (const t of [OscillatorNode.prototype, AudioBufferSourceNode.prototype]) {
  const o = t.start;
  t.start = function (w, ...r) { window.__afProbe.push({ n: this.constructor.name, w }); return o.call(this, w, ...r); };
}
```

Every scheduled source start is recorded with its absolute `AudioContext` time; offsets below are relative to the first start, in milliseconds. The probe was reinstalled after each page reload.

## Identifiers used

| Thing | Value |
|---|---|
| Flow | `user:61401a21-4d43-4643-acdf-b9fc606fc4b9`, label `Checkout Confirm` |
| User token A | `user:4e621ef3-7b14-4b39-998a-044b4c36fe5c`, label `Alpha Tap` |
| User token B | `user:4a4b76ce-941d-4286-9c60-8ee393b89d44`, label `Beta Tap` |

The proof used two user token assets, not one, so that step 8 could be executed with a second step still dangling (work item requirement).

## Step 1: New Flow. PASS

Pressed `New Flow`. Evidence (`01-new-flow.png`), flow select `innerHTML`:

```html
<optgroup label="Canonical"><option value="command-flow">Command Flow</option><option value="edit-reject">Edit And Reject</option><option value="drag-settle">Drag And Settle</option><option value="success-fanfare">Success Fanfare</option></optgroup>
<optgroup label="Library"><option value="user:61401a21-4d43-4643-acdf-b9fc606fc4b9">Untitled Flow</option></optgroup>
```

`Untitled Flow` selected under `Library`, all four fixtures still listed under `Canonical`. Step list: `01 | Button Press | button.press`, a single step. State text `USER · SAVED` (create persists the blank entry immediately, per D5 and 2c.1).

## Step 2: Rename to `Checkout Confirm`. PASS

Filled the Name field. State text moved `USER · SAVED` to `USER · UNSAVED`; `Save` button `disabled` moved `true` to `false` (`02-renamed.png`).

Observation, not a failure: the `Flow` select option keeps reading `Untitled Flow` until Save, because the option label comes from `asset.entry.draft.label` (the persisted entry) while the working copy holds the new name. This matches the spec's `SequenceFlowControls` contract.

## Step 3: Duplicate, retime, reassign to a saved user asset. Play. PASS

No user token assets existed (`audioface.tokenLibrary.v1` was `null`), so two were created with `New from Blank` in Edit Token, renamed and saved: `Alpha Tap` and `Beta Tap`. `New from Blank` assigned each new id to the selected step, as specified in 2c.2 (`persistEntry` assigns the new id whenever it differs).

Authored flow (`03-three-steps.png`):

```
01 | Button Press    | button.press                                 @0
02 | Alpha Tap       | user:4e621ef3-7b14-4b39-998a-044b4c36fe5c    @200
03 | Alpha Tap Copy  | user:4a4b76ce-941d-4286-9c60-8ee393b89d44    @400
```

Play, probe output: `starts: 4`, offsets `[6, 6, 206, 406]` (step 01 schedules two layers). All three steps sound at their authored delays. No error strip, no console output.

Step 03's label stayed `Alpha Tap Copy` after assignment to the just saved `Beta Tap`. That is the documented behavior ("Refreshing a step label when a just saved asset is assigned" is Out of scope), not a defect.

## Step 4: Save. PASS

Pressed `Save`. Before: state `USER · UNSAVED`, Save enabled. After: state `USER · SAVED`, Save `disabled: true` (`04-saved.png`).

`localStorage["audioface.sequenceLibrary.v1"]` entries:

```json
[{"id":"user:61401a21-4d43-4643-acdf-b9fc606fc4b9","label":"Checkout Confirm",
  "steps":["button.press@0","user:4e621ef3-7b14-4b39-998a-044b4c36fe5c@200","user:4a4b76ce-941d-4286-9c60-8ee393b89d44@400"]}]
```

Exact `TokenAssetId` references and `delayMs` values persisted.

## Step 5: Reload, find the flow, play it. PASS

Page reload. Flow select after hydration contains `<optgroup label="Library"><option value="user:61401a21-...">Checkout Confirm</option></optgroup>`; initial selection is `command-flow` (remembering the last flow is Out of scope). Selected `Checkout Confirm`.

Step list identical to Step 3, both user references intact. Name field `Checkout Confirm`, state `USER · SAVED`, no `Unresolved` rail.

Play, probe output: `starts: 4`, offsets `[0, 0, 200, 400]`. The saved user definitions resolve after reload. No alerts (`05-reload-restored.png`).

## Step 6: Reset semantics. PASS

Fixture: selected `Command Flow`, set step 01 `Start` 0 to 750. State read `CANONICAL · DRAFT`. Pressed `Reset` (Edit Node). `Start` returned to `0`, six fixture steps unchanged, state text returned to `CANONICAL`.

User flow: selected `Checkout Confirm`, set step 02 `Start` 200 to 900. State read `USER · UNSAVED`. Pressed `Reset`. `Start` returned to `200` (the last saved draft) and state returned to `USER · SAVED` (`06-reset.png`).

## Step 7: Dangling asset case. PASS

Storage manipulation performed, exactly:

```js
const parsed = JSON.parse(localStorage.getItem('audioface.tokenLibrary.v1'));
parsed.state.entries = [];                       // removed user:4e621ef3-... and user:4a4b76ce-...
localStorage.setItem('audioface.tokenLibrary.v1', JSON.stringify(parsed));
// after: {"state":{"entries":[]},"version":1}
```

Both user token assets were removed (the envelope stays well formed, so this is a missing asset case and not a hydration quarantine case). Page reloaded, `Checkout Confirm` selected.

- No `StudioErrorBoundary`: body text never matched `/failed to render/i`; `agent-browser errors` empty; console clean apart from Vite and React DevTools notices.
- Step list keeps original order and numbering, with the two dangling rows marked:
  `01 ... class="sequence-step-list__step"`, `02 ... class="sequence-step-list__step is-unresolved"`, `03 ... class="sequence-step-list__step is-unresolved"`.
- Timeline lanes: `Activation` holds `01 Button Press`; a separate `Unresolved` rail holds `02` and `03`. Chip inline styles:

  | Chip | `--event-start` | `--event-width` |
  |---|---|---|
  | 01 Button Press | `0%` | `19.259%` (104 ms, its real resolved span) |
  | 02 Alpha Tap (unresolved) | `37.037%` | `13.333%` |
  | 03 Alpha Tap Copy (unresolved) | `74.074%` | `13.333%` |

  Timeline duration is 540 ms, so `200/540 = 37.037%` and `400/540 = 74.074%`: both unresolved slots start at their original `delayMs`, and step 01 keeps its position and order. `13.333% x 540 = 72 ms = SEQUENCE_TIMELINE_MIN_EVENT_MS`, and it differs from the resolved chip's span, so the slot width is the minimum and not a cached former length. Unresolved chips carry `--accent: var(--af-ink-a40)` and `aria-pressed=false`.
- Edit Node reads `Missing asset` and its Token select has a disabled, selected first option `Missing: user:4e621ef3-7b14-4b39-998a-044b4c36fe5c` above the `Canonical` and `Library` groups; Label and Start stay enabled.
- Edit Token renders `.missing-asset-notice`: the dangling id, the sentence "This step references a token that is not in the library. Reassign it in Edit Node or create a new token.", and an enabled `NEW FROM BLANK` button (`07-unresolved.png`, `07b-missing-notice.png`).
- Play: probe `starts: 2`, offsets `[0, 0]`. Only step 01 sounds, at its time; both unresolved steps are silent. No `[role=alert]` node, no element matching `[class*=error]`, no boundary.

## Step 8: Repair with a second step still dangling. PASS

With step 03 still dangling, reassigned step 02 in Edit Node from `Missing: user:4e621ef3-...` to `toggle.snap`.

Immediately after reassignment: step 02 became `02 | Toggle Snap | toggle.snap` with no `is-unresolved` class and moved into the `State` lane at `--event-start: 37.037%` (unchanged 200 ms) with a real span `--event-width: 23.333%`; step 03 stayed in the `Unresolved` rail at `74.074%`; the missing asset notice disappeared; no boundary; state `USER · UNSAVED` (`08-repaired.png`).

Saved: state `USER · SAVED`, persisted steps `["button.press@0","toggle.snap@200","user:4a4b76ce-941d-4286-9c60-8ee393b89d44@400"]`.

Reloaded and reselected `Checkout Confirm`: the repaired flow persists, step 03 still marked `is-unresolved`, no boundary. Play: probe `starts: 6`, offsets `[0, 0, 200, 200, 200, 200]` (step 01 two layers at 0, `toggle.snap` four layers at 200), step 03 silent. Order and delays hold (`08b-repaired-reloaded.png`).

## Additional outcome: flow name field rejects an empty name with a visible reason. PASS

Cleared the Name field while `Checkout Confirm` was unsaved (`02b-empty-name.png`).

- Visible reason: `<small id="sequenceFlowNameRequirement">Flow name is required.</small>`, computed `display: block`, `visibility: visible`, `opacity: 1`, height 15 px, wired to the input through `aria-describedby`. The input is also `required`, so native validation reports `Please fill out this field.`
- The blank name is rejected at the model level: `useSequenceLibrary.renameFlow` returns early on `label.trim() === ""` (`apps/studio/src/app/useSequenceLibrary.ts:93`), so the working copy never takes it. Pressing Save then persisted `Checkout Confirm`, and the input re-rendered back to `Checkout Confirm`.

Two observations, neither a spec violation:

1. The reason text is static, always rendered, rather than appearing on the invalid state; there is no `aria-invalid` toggle.
2. Because `renameFlow` ignores the change, React does not re-render, so the DOM input transiently keeps the empty text the user typed until some other render restores the bound value. The persisted and in memory label are correct throughout.

## Additional outcome: dangling step surfaces with its id and a reassign path. PASS

Covered in Step 7: the id appears verbatim in three places (step list row text, the disabled `Missing: <id>` option in Edit Node, and the missing asset notice), and two reassign paths are offered (the Token select, and `New from Blank` in the notice).

## Additional outcome: playback skips the unresolved step while order and delays hold. PASS

Covered in Steps 7 and 8: with two dangling steps, only step 01 was scheduled; after repair, steps 01 and 02 were scheduled at 0 and 200 ms with step 03 still skipped; step order and every other step's `delayMs` were unchanged throughout.

## Repository gate

```
pnpm run check
```

Exit code `0`. `tsc -b` clean; `node --test`: `tests 249, pass 249, fail 0, cancelled 0, skipped 0, todo 0, duration_ms 10030.87`; `audioface validate` passed (23 shipping tokens, 20 profiled verbs, 4 sequence timelines).

`git status --porcelain` empty before and after the proof. The dev server was stopped at the end of the run. All probes and screenshots live outside the repo.
