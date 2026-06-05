---
title: Audioface Studio IA Audit
type: design
tags: [ux-design, information-architecture, audioface, studio, audit]
summary: Information architecture audit of the current Audioface Studio against the shift to a deep layered sound design tool.
status: active
source: ux-designer
confidence: high
created: 2026-08-18
updated: 2026-08-18
---

# Audioface Studio IA Audit

Repo `/Users/alphab/Dev/LLM/DEV/helioy/audioface` at `3eb5675`, read only. Component facts below come from `apps/studio/src`. The audit is written against the strategic shift: Studio becomes an unbounded studio for designing layered sounds, with interface semantics layered on top.

## 1. What exists today

`StudioApp.tsx` renders exactly one thing: `SequenceAudition`. The entire product IA lives inside that component.

```
header  .sequence-audition__header          sticky, z-index 20
        kicker "Audioface Studio" + h1 "Sequence Audition"
        SequenceFlowControls                flow select, name field, state pill, New Flow, Save
        Play                                full width below 768px

layout  .sequence-audition__layout          1 col; 2 col only at >= 1024px
  main  .sequence-audition__main
        time readout
        SequenceTimeline                    ruler 34px + 64px per category lane (~300px)
        SequenceGraph                       "Signal DAG", fixed 148px x 560px canvas
        SequenceStepList                    ~70px per step (~350-420px)
  rail  EditorDock                          minmax(280px, 0.38fr)
        tab node   SequenceNodeEditor       token, label, start ms, velocity
        tab token  TokenEditor + SignalInspector stacked (~700-800px + ~400px)
        tab theme  ThemeComposer            material + 7 sliders + reset
```

Below 1024px the dock becomes a fixed bottom sheet with peek / half / full snaps driven by `useDockDrag`.

The full user facing parameter surface is 26 controls: 3 token macros (weight, brightness, tension), 4 per layer controls (gain, duration, delay, pitch or filter frequency), 8 theme controls (material plus 7 macros), 4 node fields, 2 flow fields, and 5 counting the timeline drag that duplicates Start.

## 2. Primary object mismatch

This is the structural finding. Everything else is downstream of it.

The root component is a **flow**. The **sound** is a derived selection two levels down: `selectedAssetId = selectedStep?.tokenId ?? draft.steps[0]?.tokenId ?? toTokenId("button.press")` (`useSequenceAudition.ts:79-80`). A designer cannot open a sound. They can only select a step in a flow and hope the token behind it is the one they wanted, and when no step is selected the Token tab silently falls back to a hardcoded `button.press` that no visible step references.

For the new product the layered sound is the primary object and the flow is one audition context among several. The current tree inverts that. There is no library browser, no way to address a sound directly, no create-sound entry point that is not "copy the token behind a step".

## 3. No primary work surface

Timeline, Signal DAG, and Step List are three renderings of the same step array, stacked vertically at equal visual weight, all wired to the same `selectStep`. The main column spends roughly 800px of vertical space saying one thing three times.

- `SequenceTimeline` is the only one with information the others lack: rhythm and category lanes.
- `SequenceGraph` prints `"{n} nodes · {edges} edges · DAG"` in a fixed 148px canvas that is mostly empty. It is an implementation assertion rendered as UI.
- `SequenceStepList` adds index, label, and raw `tokenId`. It is a debug dump with click targets.

The dock, which holds every parameter a sound designer actually manipulates, is the narrowest region on screen at `minmax(280px, 0.38fr)`.

## 4. Four uncoordinated selections

| Selection | Owner | Set by | Reacts |
|---|---|---|---|
| Step | `useSequenceAudition.ts:73` | timeline chip, graph node, step list | 3 views highlight, node editor fills, throttled solo audition |
| Token asset | derived, `useSequenceAudition.ts:79` | nothing, follows the step | Edit Token tab |
| Layer | `useTokenEditor.ts:47` | aria-hidden scope grid only | layer sliders |
| Flow | `useSequenceLibrary.ts:52` | flow select | everything |

Selecting a step changes what three panels show but does not route the user to the tab that reflects it. `EditorDock` defaults to `tab = "node"` and nothing about selection changes it; selecting a step while on Surface Feel leaves you on Surface Feel. `selectionVersion` exists only to nudge the mobile sheet from peek to half. The layer selection is keyboard invisible: the scope grid is `aria-hidden`, so the per layer sliders are unreachable for a keyboard user, a WCAG 2.1.1 failure today at four controls and a blocking failure at a hundred.

## 5. Competing models of the same idea

- **Loudness three ways**: layer Gain (1-100% mapped onto a `TOKEN_EDITOR_GAIN_CEILING` of 0.22), node Velocity (5-100%), theme Volume (0-100). Nothing in the UI states the relationship or shows the resulting level.
- **Onset two ways**: drag a timeline chip, or type into Start (ms). Same value, no shared affordance.
- **Weight, brightness, tension two ways**: editable macros in `TokenEditor.tsx:112-122`, read-only chips in `SignalInspector.tsx:70-72`, in different visual languages.
- **Two audition scopes with no hierarchy**: a per step solo audition fires on selection, and a full flow Play sits in the header. Neither is presented as the primary transport.

## 6. Debug bench residue

Raw identifiers and internal enums reach the screen in at least ten places:

```tsx
<em>{event.tokenId}</em>                                    // SequenceStepList.tsx:29 -> "user:294e46a7-9130-..."
<option disabled>Missing: {missingAssetId}</option>         // SequenceNodeEditor.tsx:58
<span>{editor.draft.action}</span><span>{editor.draft.category}</span>  // TokenEditor.tsx:85-86 -> "command-input"
<span>{activeLayer.type}</span>                             // TokenEditor.tsx:132 -> "fm"
<strong>{playback.mode}</strong>                            // SignalInspector.tsx:52 -> "raw" | "themed"
title: `${index + 1}. ${layer.type.toUpperCase()}`          // SignalInspector.tsx:133 -> "2. FM"
<span>{`${graph.nodes.length} nodes · ${graph.edges.length} edges · DAG`}</span>  // SequenceGraph.tsx:18
```

`SequenceNodeEditor` is inconsistent by origin: canonical options print `token.id`, library options print `token.label` (lines 65 and 73), so one select mixes two naming systems.

Further residue:

- **Raw Audition vs Themed Audition** buttons plus the `is-changed` comparison highlighting are an engineering A/B probe, not a product control. The underlying question (what does the theme do to my sound) is real and deserves a first class answer.
- **`SignalInspector` mounts only on the Edit Token tab**, stacked under an 800px editor. The only analysis surface in the product is the hardest thing to see.
- **`useDockDrag` is inert at >= 1024px** yet still measures a hidden safe-area probe on every resize. The handle, flick velocity resolver, and Escape-to-peek are dead weight in rail mode.
- `SignalInspector` copy prints synth internals verbatim: `carrier 420 Hz mod 840 Hz`, `/ Q 6.4`, `/ index 34`.

## 7. What breaks at 100+ parameters

The parallel inventories put the future surface at oscillators, noise, filters, envelopes, modulation, effects, and per layer time. A conservative projection: ~30 parameters per layer times 3-5 layers, plus token level identity and 8 theme macros, is 100-170 controls per sound.

Against that number, every current mechanism fails:

1. **The dock cannot hold it.** `TokenEditor` already claims 700-800px for 7 sliders and 6 buttons in a 280-380px column. At 150 controls in the same flat, ungrouped, one-slider-per-row pattern the tab becomes a 4000px+ scroll in the narrowest region of the screen. There is no grouping, no collapse, no search, no tabbing within the editor, no way to pin the four parameters you are actually working on.
2. **The layer scope grid cannot address the layers.** It is a fixed 112px strip of unlabeled buttons, `aria-hidden`, with layer identity communicated as the raw string `noise | tone | fm`. It does not scale past a handful of layers, has no reorder, no solo, no mute, no per layer bypass, no add or delete.
3. **There is no visual feedback.** No waveform, no spectrum, no envelope curve, no level meter anywhere in the product. `SignalInspector` renders text fingerprints. A synthesis tool without an analysis surface forces the designer to hold the sound in their head across every parameter change, which is exactly the load that a hundred parameters makes impossible.
4. **The time model is the wrong scale.** The timeline is flow time, seconds across an interaction sequence. The new primary object lives in the first 400ms of a single sound: onsets, attacks, decays, and layer offsets measured in milliseconds. There is no view of that at all, yet layer `delay` and `duration` are already editable numbers with no temporal representation.
5. **No structure to modulate.** Envelopes, LFOs, and a mod matrix imply a per parameter state (value, source, depth, range) that today's single slider per parameter cannot express, and no place to see what is modulating what.
6. **Editing has no memory.** No undo, no history, no compare-to-saved, no A/B slots, no revert-parameter. Dirty state is a pill. At 150 parameters, unrecoverable exploration is a product defect.
7. **Mobile first sizing fights desktop density.** Everything is sized to `--af-target` (44px) with a single column below 1024px. A professional rack needs 24-28px rows and pointer precision on desktop, which means the responsive story has to become two genuine layouts rather than one column count.

## 8. What survives

Worth carrying forward into any redesign:

- The resolution pipeline `definition -> theme resolve -> resolved layers -> engine`, which lets theme be a **lens** over an unthemed definition rather than a destructive edit.
- The layer as the unit of composition, already typed as `noise | tone | fm` with per layer `delay`, `duration`, `attack`, `decay`, `gain`.
- Locked canonical catalog plus user library, and flows that retain exact asset references with per step missing asset states.
- Category lanes in the timeline, the one genuinely informative view in the main column.
- Semantic token vocabulary and the 8 theme macros, which become the control surface over the engine rather than the engine itself.

## 9. Consequences for the redesign

1. The root object must be a sound. Flows, themes, and tokens attach to it, not the other way round.
2. Exactly one region must be the primary work surface, and it must be the largest.
3. Analysis (waveform, spectrum, envelope) is not a panel to add later. It is the feedback loop the whole tool depends on and must be designed in from the first layout.
4. Layers need a first class list object with order, mute, solo, bypass, add, delete, and keyboard reachability.
5. Parameter disclosure needs a stated strategy per concept: grouping, collapse, drill, search, or density. Any layout that leaves it implicit fails at the projected count.
6. Every raw id, enum, and count must be replaced by a designed label. `user:294e46a7` is a defect, not a placeholder.
7. Theme must be a togglable lens with visible deltas, replacing the Raw / Themed debug pair.
