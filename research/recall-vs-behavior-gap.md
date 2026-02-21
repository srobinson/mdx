---
title: "Recall vs Behavior: The Enforcement Gap in Agent Memory"
type: research
tags:
  [
    attention-matters,
    enforcement,
    hooks,
    experiment,
    continuity,
    agent-behavior,
  ]
status: active
created: 2026-02-21
summary: AM recall works but doesn't translate to behavioral compliance. Identifies the missing enforcement layer and proposes A/B experiments.
---

# Recall vs Behavior: The Enforcement Gap

## Observation

attention-matters geometric memory correctly recalls rules, conventions, and decisions when queried. But recall alone does not prevent violations. The agent knows the rule, has it in conscious memory, and still doesn't apply it at the moment of action.

Concrete example: the `~/.mdx` versioning protocol.

- AM stores the rule (conscious memory): "MOVE current file to `_versions/slug.vN.md` FIRST, then write new content"
- AM recalls it accurately when queried
- Agent still overwrites documents without versioning — multiple times, across multiple sessions
- Each time the agent says "I fixed this" — then doesn't

This is not a retrieval failure. It's a **behavior enforcement** failure.

## Analysis: What AM Is and Isn't

| Capability     | AM (Memory)                    | Hook (Enforcement)                 |
| -------------- | ------------------------------ | ---------------------------------- |
| Mechanism      | Associative retrieval on query | Intercept on action                |
| When it fires  | When the agent asks            | When a tool targets a path/pattern |
| Failure mode   | Recalled but not applied       | Cannot forget — it blocks          |
| What it proves | Knowledge retention            | Knowledge application              |

AM is an associative retrieval engine. It surfaces relevant context when queried. It does NOT:

- Intercept actions and validate them against known rules
- Fire proactively when the agent is about to violate a convention
- Block writes that skip required steps

This is analogous to human behavior: knowing you should stretch before running doesn't mean you do. Knowledge ≠ compliance.

## Hypothesis

**H1:** Adding a PostToolUse hook that intercepts Write/Edit operations targeting `~/.mdx/` and enforces versioning will eliminate versioning failures that AM recall alone cannot prevent.

**H2:** The combination of AM (contextual recall) + hooks (behavioral enforcement) produces reliable continuity that neither achieves alone.

**H3:** For local dev sessions, the right combination of AM queries + mdx session docs + enforcement hooks can produce continuity equivalent to nancyr's pre-compiled prompts.

## Experiment Design

### A: Baseline (Current State)

- AM stores versioning rule as conscious memory
- SKILL.md documents the protocol
- No automated enforcement
- **Metric:** Track versioning compliance across sessions (manual observation)

### B: With Enforcement Hook

- PostToolUse hook on Write/Edit targeting `~/.mdx/**`
- Hook checks: does the file already exist? If yes, was `_versions/` written to in this session first?
- If not: block with message "Version existing file first: `mv ~/.mdx/cat/slug.md ~/.mdx/cat/_versions/slug.vN.md`"
- **Metric:** Same compliance tracking — expect 100%

### C: Full Stack (AM + Hooks + mdx + git)

- Everything in B, plus:
- `~/.mdx` in git (safety net for anything hooks miss)
- SessionEnd hook writes session summary to `~/.mdx/sessions/`
- Smarter session-start AM queries (project-specific, not generic)
- **Metric:** Session continuity quality — does next session know what this one did?

## Layer Model

Each context source has a job. Misapplying one to another's job produces the failures we're seeing.

| Layer                  | Source        | Job                           | Anti-pattern                           |
| ---------------------- | ------------- | ----------------------------- | -------------------------------------- |
| Associative recall     | AM            | "What did we decide about X?" | Using it to enforce rules              |
| Structured knowledge   | mdx/mdcontext | "What specifically happened?" | Expecting it without session summaries |
| Behavioral enforcement | Hooks         | "Don't do X without Y"        | Not having any hooks                   |
| Code navigation        | FMM           | "What does this export?"      | grep/read when sidecars exist          |
| Task tracking          | Linear        | "What's the actionable work?" | Keeping plans only in memory           |

The merge of these layers — AM + mdx + Linear + FMM + hooks — is the full continuity stack. Each layer compensates for the others' blind spots.

## Required Work

1. **PostToolUse hook**: enforce `~/.mdx` versioning (the immediate fix)
2. **Git init ~/.mdx**: safety net, track all changes
3. **SessionEnd hook**: write session summary before context loss (ALP-655)
4. **Experiment capture**: track compliance metrics across sessions to validate H1/H2/H3
5. **Clean up /Dev/LLM/DEV/docs/**: predecessor to ~/.mdx, likely obsolete — archive or merge content

## Implications for attention-matters

AM is not broken. The math works — retrieval is accurate and relevant. But AM alone is insufficient for behavioral compliance. This isn't a reason to abandon it; it's a reason to stop asking it to do things it wasn't designed for.

AM's real value:

- Cross-session context ("we published mdcontext v0.2.0 last session")
- Architecture decision recall ("we chose CLI wrapping over direct API")
- Lateral connections ("this pattern is similar to what we did in FMM")
- User preference memory ("Stuart wants action, not permission-asking")

Hooks' real value:

- Rule enforcement ("version before overwrite")
- Workflow gates ("flush AM buffer before exit")
- Quality checks ("run tests before marking done")

Both are needed. Neither replaces the other.
