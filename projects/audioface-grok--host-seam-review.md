---
title: Audioface host seam review (Grok, adapter and control rows)
type: projects
tags: [audioface, host-seam, design-review, control, adapter]
summary: Adversarial review of issue #11 from the adapter and control-row side. One RowSet shape is a false economy.
status: active
created: 2026-09-04
updated: 2026-09-04
project: audioface-next
confidence: high
related:
  - audioface-2026-09-host-seam-audit.md
  - audioface-ui-direction.md
---

# Host seam review, adapter and control rows

Baseline `main` at `50b22cf` (PR #10). Tree clean. Citations are `git show main:<path>` symbols.

## Verdict

Conditional. Shrinking `Audition` and moving the rows into control are right. One `RowSet<Field>` is a pass through that erases the only typecheck the listener rows have, cannot delete `wholeListener`, and will parse `OUT-12.sample-rate` as a number, which is how 7 reaches `AudioContext` today.

## Findings

1. **One `RowSet<Field>` fails the deletion test.** Delete the generic and nothing a caller does changes. The web adapter already has two loops: `git show main:adapters/web/src/output.ts` `outputPanel` stringifies enum fields and calls `apply`, `git show main:adapters/web/src/bench.ts` `listenerRows` mutates a partial and calls `place`. CLI, HTTP, and MCP (`parseCommand`, `handleHttpRequest`, `createMcpServer`) speak `ControlRequest` only. They never iterate these rows. One adapter is a hypothetical seam. Two named modules plus one shared leaf parse is the real one.

2. **`schema: Record<keyof Field, ControlLeafSchema>` throws away depth.** `git show main:packages/control/src/audition.ts` `listenerControls` demands `ControlNumber` so a fourth listener row of another kind fails at typecheck. `outputControls` accepts mixed leaves because mute is boolean and `OUT-12.sample-rate` is enum. The generic makes both `ControlLeafSchema`. Locality for a new listener field moves back into every adapter.

3. **The proposed `read` cannot delete the shadow default.** Issue 11 claims `wholeListener` goes away. `git show main:adapters/web/src/performance.ts` `wholeListener` fills `Partial<ListenerField>` from `{ pan: 0, width: 1, distance: 0 }` then the leaves. Output has no partial. Without `complete` on the listener module, that fill stays in the adapter.

4. **`parseControlEdit` cannot be the parse path.** It needs a patch `ControlManifest` and a revision. Device rows have neither and turn no revision. `git show main:packages/control/src/parse.ts` `readValue` accepts any finite number and any enum string. Range lives in `git show main:packages/control/src/edit.ts` `valueAllowed`, after parse. Reusing only `readValue` leaves 7 legal.

5. **Sample rate 7 is an enum miss, and `OutputField` lies about the leaf.** `git show main:packages/patch/src/registry/parameters.ts` `OUT-12.sample-rate` is enum `["44100", "48000"]` with default `"48000"`. `git show main:packages/contract/src/control.ts` `OutputField.sampleRate` is `number`. `withField` does `Number(text)`. `git show main:packages/contract/src/block.ts` `assertSampleRate` accepts any positive integer, so 7 passes. `git show main:adapters/web/src/player.ts` `connect` then builds `new AudioContext({ sampleRate: 7 })`. Refuse in `outputRows.read` as `value_out_of_range` before `Player.apply`. `unparsable_value` is the wrong code. `Player.apply` must also `accept` a structured `OutputField`, or a game binding that never had text still ships 7.

## Amended interfaces

```ts
function parseControlLeaf(
  leaf: ControlLeafSchema,
  text: string
): ControlParse<ParameterValue>;
// unparsable_value from readValue; value_out_of_range from valueAllowed.
// parseSet calls this. Device rows call this. No manifest.

type ListenerRows = {
  readonly schema: Readonly<Record<keyof ListenerField, ControlNumber>>;
  readonly defaults: ListenerField;
  readonly fields: typeof LISTENER_FIELDS;
  read(
    current: ListenerField,
    field: keyof ListenerField,
    text: string
  ): ControlParse<ListenerField>;
  complete(partial: Partial<ListenerField>): ControlParse<ListenerField>;
};

type OutputRows = {
  readonly schema: Readonly<Record<keyof OutputField, ControlLeafSchema>>;
  readonly defaults: OutputField;
  readonly fields: readonly (keyof OutputField)[];
  read(
    current: OutputField,
    field: keyof OutputField,
    text: string
  ): ControlParse<OutputField>;
  accept(value: OutputField): ControlParse<OutputField>;
};
```

Callers learn `fields`, `schema`, `defaults`, `read`. Listener callers also learn `complete`. Output callers also learn `accept`. Depth: enum text `"48000"` becomes the number `AudioContext` wants inside `outputRows`, so adapters never `Number(text)`. Leverage: CLI, HTTP, MCP, and the web adapter iterate the same `fields` tuple. Locality: a new listener field breaks `ListenerRows.schema`; a new output field breaks `OUTPUT_PARAMETER_KEYS` and `OutputRows` together, as `git show main:packages/patch/src/registry/output.ts` already binds.

Keep `OutputField.sampleRate` as `number`. The leaf stays enum. Conversion is implementation of `outputRows`, the one place that knows both.

## Answers to questions 1 to 3

**1.** One `RowSet<Field>` is false economy. Listener rows are trigger authority, live, per voice, numbers only, filled from a partial. Output rows are output authority, device wide, mixed leaves, and a rate change rebuilds the device (`Player.apply` returns true). Share `parseControlLeaf`. Do not share the module.

**2.** Chassis and the Gate dock need nothing `Audition.listener` or `Audition.output` hold. Chassis reads `ControlSurface.snapshot`. The Gate dock reads `certify`. Event in the room needs `listenerRows` for the gizmo. The master bus strip needs `outputRows`. Shrinking `Audition` to `events`, `render`, `voice`, `targetOf` loses nothing those two surfaces use. Every future adapter iterates `fields`, paints `schema`, starts from `defaults`, and commits through `read`. It never parses. Import the modules from control even when `audition` is null, so a loose patch still has a device. CLI, HTTP, and MCP grow host verbs later; they do not grow a second `Number(text)`.

**3.** Parsing text against a row's range lives in `parseControlLeaf`, beside `parseControlEdit`, used by `parseSet` and both row modules. An out of range sample rate is refused in `outputRows.read` and `outputRows.accept` as `value_out_of_range`. `git show main:adapters/http/src/handler.ts` already maps that code to 422. Do not add a new issue code. Do not let `assertSampleRate` or the worklet see it.
