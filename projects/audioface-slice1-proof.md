# Audioface Slice 1 Studio acceptance proof

Date: 2026-08-17
Repo: /Users/alphab/Dev/LLM/DEV/helioy/audioface, main at 73f6fc6, tree clean before and after (no repo writes).
Spec: docs/superpowers/specs/2026-07-19-authoring-loop-slice-1.md, sections "Studio acceptance proof" and "Completion criteria".
Driver: agent-browser (headless Chromium, fresh profile, localStorage empty at start), Studio via `pnpm run start:studio` on http://127.0.0.1:4174 (Vite 8.1.3). Dev server stopped at the end, port 4174 free.
Evidence directory: ~/.mdx/projects/audioface-proof/ (screenshots, JSON dumps of `ResolvedPlayback` read from the mounted `SignalInspector` props, localStorage snapshots).

Result: 6/6 PASS. `pnpm run check` exit code 0.

Storage key observed: `audioface.tokenLibrary.v1`. Assets created during the proof:

| Asset ID | Origin | Semantic token id | Final label |
|---|---|---|---|
| `user:b627f71c-f366-4bb7-8da6-98a7eed01f82` | user (copy, `sourceTokenId: panel.undock`) | `panel.undock` | Proof Undock Copy |
| `user:db0b14ae-84dc-40a4-a2e8-d8d625eca05f` | user (blank starter) | `custom.neutral.tick` | Proof Blank Tick |

## Step 1: copy a canonical token and create one from blank. PASS

- Flow "Command Flow", step 01 (`panel.undock`) selected, Edit Token tab. Editor state "Canonical", Save disabled, Copy to Library enabled.
- Clicked Copy to Library. Editor state became "User · Saved", step 01 token select value became `user:b627f71c-f366-4bb7-8da6-98a7eed01f82`. localStorage gained one entry with `origin: "user"`, `locked: false`, `sourceTokenId: "panel.undock"`, token layers identical to canonical (noise 0.014 s gain 0.11 bandpass 3000 Hz Q 3.4; triangle 166 to 238 Hz gain 0.075 duration 0.08). Screenshot `01a-after-copy.png`.
- Selected step 02, clicked New from Blank. Editor showed "Untitled Token", identity `custom.neutral.tick / tick / command-input`, one sine tone layer 620 to 540 Hz, gain 0.024, duration 0.026. localStorage gained `user:db0b14ae-84dc-40a4-a2e8-d8d625eca05f`. Step 02 reassigned to it. Screenshot `01b-after-blank.png`.

## Step 2: edit each and save. PASS

Blank (`user:db0b14ae…`): label set to "Proof Blank Tick", layer gain slider 11 to 40, duration 26 to 60 ms, pitch 620 to 880 Hz. State "User · Unsaved", Save enabled (`02a-blank-edited-unsaved.png`). Clicked Save: state "User · Saved", persisted layers `[{sine, frequency 880, endFrequency 766.45, gain 0.088, duration 0.06}]`, `updatedAt` 11:22:19.889Z vs `createdAt` 11:22:01.072Z, id unchanged (`02b-blank-saved.png`).

Copy (`user:b627f71c…`): step 01 selected, label set to "Proof Undock Copy", layer 1 gain 50 to 80, duration 14 to 30 ms, layer 2 pitch 166 to 220 Hz. State "User · Unsaved" (`02c-copy-edited-unsaved.png`). Clicked Save: state "User · Saved", persisted layers `[{noise 0.03 s, gain 0.176, bandpass 3000 Q 3.4}, {triangle 220 to 315.42 Hz, gain 0.075, 0.08 s}]`, `updatedAt` 11:22:51.037Z, `createdAt` 11:21:50.622Z unchanged, `sourceTokenId` retained (`02d-copy-saved.png`).

## Step 3: reload and confirm both entries and authored values survive. PASS

localStorage serialised before and after `agent-browser reload` byte-identical (`diff` empty). After reload the Edit Node token select lists a "Library" optgroup with "Proof Blank Tick" and "Proof Undock Copy" after the 23 canonical options. Post-reload store dump in `storage-after-reload.json` shows both ids, labels, layers, and timestamps as saved. No quarantine alert, no hydration error. Screenshot `03a-after-reload.png`. Note: sequence step assignments do not persist across reload (steps reverted to canonical ids), which matches the spec's out of scope list (no flow persistence).

## Step 4: assign a saved user asset to a sequence step. PASS

Selected step 06 ("Panel settles", `panel.dock`), Edit Node, chose `user:b627f71c-f366-4bb7-8da6-98a7eed01f82` in the Token select. Select value confirmed as the full library id, header became "Surfaces & Navigation · undock", step list row reads "06 Proof Undock Copy user:b627f71c-f366-4bb7-8da6-98a7eed01f82", timeline and DAG nodes updated to "undock". Screenshot `04-assigned-step06.png`. Later also assigned `user:db0b14ae…` to step 05 (row "05 Proof Blank Tick user:db0b14ae-…").

## Step 5: Play and confirm the saved definition resolves rather than its canonical source. PASS

Clicked Play (button showed "Playing", playhead advanced, `05a-playing.png`). After the run, `lastPlayback` (final step 06) read from SignalInspector props (`step5-playback.json`): `intent.assetId = user:b627f71c-f366-4bb7-8da6-98a7eed01f82`, `intent.tokenId = panel.undock`, `intent.source = sequence`, `intent.seed = command-flow:panel-settles`, `token.label = "Proof Undock Copy"`, mode themed. Themed layers: noise duration 0.04396, gain 0.11618; tone 286.97 to 406.40 Hz.

Control run: reassigned step 06 to canonical `panel.undock`, pressed Play, read the inspector (`step5-canonical-control.json`): `assetId = panel.undock`, label "Panel Undock", noise duration 0.02052, gain 0.07262; tone 216.53 to 306.65 Hz. Same theme, same seed, different layer values, so the saved definition (220 Hz / 0.03 s / 0.176) is what resolved, not the canonical recipe (166 Hz / 0.014 s / 0.11). Step 06 restored to the user copy afterwards. Inspector summary displays "Asset user:b627f71c…", "Mode themed", "Token panel.undock" (`05b-after-play.png`).

## Step 6: audition Raw and Themed, compare `ResolvedPlayback.token.layers` in SignalInspector. PASS

Asset `user:b627f71c…` selected in Edit Token:

- Raw Audition (`step6-raw.json`, `06a-raw-audition.png`): mode `raw`, assetId `user:b627f71c…`, source `token-editor`. `token.layers` deep-equal to the saved definition layers (Python `==` on the parsed JSON: True). `token.duration` 0.08 equals saved. Inspector rows: "NOISE bandpass 3 kHz 30 ms / gain 0.18 / Q 3.4", "TONE triangle 220 Hz to 315 Hz 80 ms / gain 0.08". Comparison `{current: raw, previous: null}`.
- Themed Audition (`step6-themed.json`, `06b-themed-audition.png`, `06e-inspector-layer-stack.png`): mode `themed`, same assetId. Layers differ from saved: noise duration 0.04259, gain 0.13613, filter 4344.41 Hz Q 3.562, attack 0.00227; tone 283.47 to 406.40 Hz, gain 0.05485, duration 0.11683. Inspector rows both carry `is-changed`, summary duration 117 ms vs raw 80 ms, Theme impact chips 42/58/36. Comparison `{current: themed, previous: raw}`.

Repeated for the blank asset `user:db0b14ae…` on step 05 (`step6-blank-raw.json`, `step6-blank-themed.json`, `06c-blank-raw-audition.png`, `06d-blank-themed-audition.png`): raw layers deep-equal saved (`[{sine 880 to 766.45 Hz, gain 0.088, 0.06 s}]`, True); themed layers 1312.65 to 1127.63 Hz, gain 0.06445, duration 0.04900 with attack and decay added.

## Console and errors

`agent-browser console` and `agent-browser errors` returned nothing at every checkpoint. `useStudioPlayback.error` (`.sequence-audition__error`) was null throughout.

## Repository gate

`pnpm run check` (typecheck, test, validate) exit code 0. Log: `~/.mdx/projects/audioface-proof/check.log`.

## Observations (not failures, not fixed)

1. `SignalInspector` is only mounted while the Edit Token tab is active, so a Play run finished on the Edit Node tab is not inspectable until switching tabs. Consistent with the spec's mount location.
2. The previous versus current comparison spans assets: the first Raw Audition of the blank asset showed `is-changed` because `comparison.previous` was the themed audition of the copy. Consistent with "consecutive Raw Audition and Themed Audition actions" but the highlight is not scoped per asset.
3. Step labels are copied from the token label at copy or blank time ("Untitled Token") and do not follow later token label edits until the step is reassigned. Step label is sequence state, so this looks intended.
4. React double-buffers fibers; reading `SignalInspector` props via the DOM node's `__reactFiber$` initially returned the stale alternate. The reader in this proof picks the newer of fiber and alternate by `intent.at`. Not a Studio issue.
