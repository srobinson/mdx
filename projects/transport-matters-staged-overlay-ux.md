# Transport Matters Staged Overlay UX

Date: 2026-05-15

## Purpose

Transport Matters should move beyond an ARM first breakpoint workflow.

The stronger product shape is a staged launch flow:

1. Capture the real startup payload.
2. Let the user shape an overlay before work begins.
3. Launch a fresh working agent session under that overlay.
4. Inspect exchanges without mutating historical evidence.
5. Fork or replay when the user wants to test a different timeline.

This keeps Transport Matters focused on payload truth, overlay creation, replay,
and transport inspection. Runtime profiles, catalogs, MCP setup, and reusable
agent configuration remain the domain of Runtime Matters.

## Product Boundary

Transport Matters owns:

- Real request and response payload capture.
- Startup payload probing.
- Overlay editing from captured payloads.
- Section level payload navigation.
- Manual editing of text values.
- Agent assisted overlay creation.
- Exchange timeline and detail inspection.
- Replay, fork, and future overlay creation from historical exchanges.

Transport Matters does not own:

- General runtime profile composition.
- Catalog management.
- Long lived runtime home generation.
- Cross-agent setup policy.
- Reusable MCP or skill package management.

Those belong to Runtime Matters.

## Screen Flow

### Screen 0: Session Inputs

This screen exists before any payload capture.

It contains settings that can affect the initial request:

- `ENABLE_TOOL_SEARCH`
- `ENABLE_EXPERIMENTAL_MCP_CLI`
- `CLAUDE_CODE_DISABLE_1M_CONTEXT`
- other environment variables that change startup behavior

Compaction belongs here only if it changes the initial captured payload.
Otherwise, compaction should move to the overlay editor or session policy.

Primary action:

```text
Capture Startup Payload
```

### Screen 1: Probe

Transport Matters launches a temporary Claude Code instance without `-p`.

The Claude Code UI may be visible, but it is not reachable:

- dimmed
- blurred
- opacity reduced
- keyboard focus blocked
- pointer input blocked

The foreground state says:

```text
Initializing
Capturing startup payload
```

After the first real request is captured, Transport Matters exits the probe
instance immediately.

Invariant:

```text
No user work happens in the probe instance.
```

The probe exists only to produce the real startup payload.

### Screen 2: Overlay Editor

The overlay editor is built from the captured startup payload.

Core regions:

- Payload map: system prompt, messages, tools, MCP servers, transport metadata.
- Focused editor: one section at a time, with folding, search, diff, and manual edit.
- Ask Agent panel: propose patches, explain risk, estimate token deltas, and create overlays.
- Overlay output: accepted edits saved as a reusable overlay.

Primary actions:

```text
Ask Agent
Save Overlay
Start Claude Code with Overlay
```

The agent assistance should be framed as a job oriented Transport Matters
capability. `Ask Agent` is acceptable product language for now. It can harden
later into `Overlay Builder` if the workflow deserves a named surface.

### Screen 3: Working Session

Transport Matters launches a fresh Claude Code instance under the selected
overlay.

This is the real working session.

Main regions:

- Claude Code terminal or embedded app surface.
- Exchange sidebar, improved from the current list.
- Overlay entry or affordance that lets the user revisit the active overlay.
- Current capture status.

Clicking an exchange replaces the central Claude Code surface with Screen 4.
The user can toggle back to Claude Code without losing session state.

### Screen 4: Exchange Detail

The exchange detail screen is a distinct inspection mode.

It shows:

- request
- response
- parsed payload sections
- transport metadata
- artifacts
- token and character weight
- overlay effects
- diagnostics

Tools:

- explain token weight
- compare with prior exchange
- ask agent for analysis
- create future overlay rule
- replay from here
- fork from here
- return to Claude Code

## Fork Semantics

Historical exchanges are evidence.

They should not be mutated in place.

Rules:

- Past exchanges can be inspected, annotated, replayed, or forked.
- The latest unsent or future payload can be edited.
- Disabling a message from a past exchange creates a fork or future overlay rule.
- Rewriting history creates a new timeline, not a changed record.

Product phrase:

```text
Inspect past. Shape future. Fork when rewriting history.
```

Fork management becomes a real product capability.

A fork should record:

- source exchange id
- source turn
- source overlay
- changes applied
- replay command or launch path
- resulting exchange lineage

## Open Questions

1. What exact Claude Code action reliably emits the startup request without user
   work?
2. How should Transport Matters terminate the probe instance cleanly after
   capture?
3. Which environment variables belong on Screen 0 by default?
4. Does compaction affect the probe payload or only later overlay/session policy?
5. Can `Ask Agent` operate on the captured payload without leaking sensitive
   local data beyond the selected agent boundary?
6. How should forks appear in the exchange sidebar?
7. What actions are valid only on the latest exchange?
8. What actions are valid on any historical exchange?
9. Should overlay edits be stored as textual patches, structured rules, or both?

## Near Term Design Tasks

1. Validate the probe lifecycle with the real Claude Code process.
2. Define the Screen 0 env var model.
3. Design overlay storage and apply semantics.
4. Design fork metadata and sidebar representation.
5. Design Screen 4 exchange detail tools.
6. Prototype the five screen flow in the Transport Matters frontend.

