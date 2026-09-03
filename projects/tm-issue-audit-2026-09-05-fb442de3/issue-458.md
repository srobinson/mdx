# 458: Canvas Overlay: regenerate runtime prompts from the tool decision

URL: https://github.com/littleorgans/transport-matters/issues/458
State: open
Labels: enhancement
Updated: 2026-08-25T11:42:51Z

Parent: #455. Depends on: #457 (tool enablement).

## Outcome

When a runtime's tool set changes, the prose that teaches those tools is re-rendered to match. An overlay never leaves the model reading instructions for tools it no longer has.

## Why this is not optional

Subtraction without regeneration degrades the agent while claiming to optimize it:

- claude ships a **10,720-char `role: system` message** that is the agent catalog ("Available agent types for the Agent tool:"). Disable the Agent tool and that entire block describes capabilities that no longer exist.
- The 29,764-char system prompt has a "# Using your tools" section teaching tools by name.
- codex's runtime blocks (`<skills_instructions>`, `<collaboration_mode>`, `<apps_instructions>`) are separate content parts that describe the surface.

This is why the two Canvas Overlay verbs are coupled. The codex runtime confirmed the same thing empirically from the other direction: its tool contract lives in a 26,383-char prose description, not in schema.

## Design

**Two content kinds in an overlay:**

- **fixed replacement** — static text we author for a block.
- **runtime generated** — rendered from the overlay's own decisions.

**Where generation runs:** TypeScript, when the decision changes, not per request. The proxy receives rendered strings and splices bytes; it never templates. This keeps the Python side dumb per the plane rule.

**Guard:** the render records the tool set it assumed. The proxy compares that against the request's actual tool set and fails open on mismatch (an MCP server or plugin can add tools after the render), flagging the overlay for re-render. Consistent with the all-or-nothing rule.

**Generation inputs are not only the tool set.** Platform matters: shell, OS, available binaries and paths differ per machine, so the same overlay renders different text on macOS and Linux. The codex runtime listed environment guarantees (shell semantics, PATH, OS, utilities, timeouts) as a hard requirement for any prose that teaches a tool surface.

**Targets differ per class.** codex's runtime blocks are cleanly separated content parts, so part-level replacement works. claude's runtime content is *inside* one 29,764-char string, so it needs anchored section edits (heading or tag), which keep the artifact small and make staleness detectable when a release moves the anchor.

## Acceptance

- Disabling a tool via #457 re-renders the prose that references it; the agent catalog and tool-teaching sections match the surviving tool set, verified on the wire.
- A rendered overlay whose assumed tool set does not match the live request forwards original bytes and reports the mismatch.
- Rendering is platform-aware and produces different, correct output for at least two platform profiles.
- Byte-diff shows changes confined to the prompt and tool regions.
- User acceptance through the #456 viewer: the operator can see, before and after, exactly what changed.

## Sub issues
[]
