# Cubicell Agent Observability

Status: SUPERSEDED (2026-07-18)

The complete v2.3 proposal is preserved at
`.archive/cubicell-spec-agent-observability.v1.md`.

The proposal was reviewed against `fix/gap0-coplanar-face-fighting` at
`10fd6a1`. That commit is not an ancestor of current Cubicell `main`. The
review on 2026-07-18 reconciled the design against `2048586` and the current
Workbench, interaction, camera track, and transport architecture.

## Decision

This document is no longer an active implementation contract. Version 2.3
joined two separate concerns:

1. A development flight recorder for interaction and camera debugging.
2. The supported product boundary through which an external LLM perceives,
   acts, awaits completion, and verifies the rendered result.

The current external control contract lives in
[`LLMDRIVES.md`](/Users/alphab/Dev/LLM/DEV/helioy/cubicell/LLMDRIVES.md).
The first implementation slice starts there.

## Why v2.3 was retired

- The authored root is now `Workbench`; the proposed `CubicellDocument`
  snapshot no longer matches the live model.
- The declared `ActionRecord` cannot reconstruct `before` and `after` state
  from its trace events because those events carry neither snapshots nor a
  document revision.
- The view bus returns a command id, then queues only the command. Coalescing
  drops request identity, so it cannot report applied versus superseded work.
- Draining a view command in `resolveFrame` begins eased motion. Terminal
  completion occurs on a later frame, so the proposed `command.settled` event
  was attached to the wrong boundary.
- Direct store flows, the transport clock, and camera track possession sit
  outside the proposed InteractionCore decorator.
- Camera projection samples now use `orthographicWeight`, camera tracks can
  own pose and projection, and reduced motion no longer participates in camera
  arbitration.

## Retained flight recorder direction

The following mechanics remain sound for a future diagnostic trace:

- separate frame and discrete buffers with one monotonic sequence
- bounded retention with dropped event counts
- observation at the routed command boundary and final camera writer
- versioned JSON using monotonic time plus `timeOrigin`
- an offline downloadable dump
- no telemetry service, analytics, network transport, or development overlay

That recorder remains parked. Its future specification must describe routed
command and resolved render evidence precisely. It must not serve as the
external control protocol or claim terminal command outcomes it cannot prove.

## Next implementation

Build the transport neutral, in process `StudioControl` boundary defined by
`LLMDRIVES.md`. The first executable gate proves one semantic snapshot and one
view request from dispatch through terminal camera state with deterministic
frame stepping. MCP and the diagnostic recorder follow only after that control
contract passes.
