---
title: "Council Skills — Multi-Persona Deliberation Pattern Analysis"
type: research
tags:
  [
    claude-code,
    plugins,
    skills,
    prompt-engineering,
    multi-agent,
    deliberation,
    council,
  ]
summary: Deep analysis of otrofimo/claude-skills "council" plugin — a virtual advisory board pattern using domain expert personas with Feynman as synthesizer. Evaluated for relevance to Helioy ecosystem.
status: active
created: 2026-02-22
updated: 2026-02-22
project: helioy
confidence: high
source: https://github.com/otrofimo/claude-skills
---

# Council Skills — Multi-Persona Deliberation Pattern

## What It Is

A Claude Code plugin by [otrofimo](https://github.com/otrofimo/claude-skills) that provides a `/council` slash command. Convenes a virtual advisory board of domain experts to deliberate on a question. Richard Feynman is always present as first-principles questioner and session opener.

**Structure**: Single skill, single command, pure prompt engineering — no MCP servers, no hooks, no code execution.

## Architecture

```
council-skills/
  .claude-plugin/
    marketplace.json          # Marketplace manifest
  skills/
    council/
      .claude-plugin/
        plugin.json           # Plugin manifest
      commands/
        council.md            # The actual skill (slash command)
```

### Plugin Manifest Pattern

marketplace.json uses `$schema: https://anthropic.com/claude-code/marketplace.schema.json` — useful reference for the official schema URL. Plugin source uses relative path (`./skills/council`).

### Command Registration

The skill file (`council.md`) uses YAML frontmatter:

```yaml
description: "Consult a virtual advisory board..."
argument-hint: "[--board=<council>] [--list] <question>"
```

Arguments are parsed from `$ARGUMENTS` variable — supports `--board=<name>`, `--list`, and freeform question text. This is the standard Claude Code skill argument passing mechanism.

## Available Councils (7 boards)

| Board                 | Experts                                          | Domain                              |
| --------------------- | ------------------------------------------------ | ----------------------------------- |
| engineering (default) | Lamport, Dean, Torvalds, Thompson                | Systems, distributed, unix          |
| design                | Ive, Norman, Kelley, Jobs, Rams                  | UX, industrial, product design      |
| business              | Munger, Dalio, Cuban, Buffett, Graham            | Strategy, investment, startups      |
| agentic               | Engineering + Huntley, Yegge, Willison, Karpathy | AI-assisted dev, LLM tooling        |
| product               | Jobs, Norman, Dunford, Fried                     | Positioning, usability, simplicity  |
| refactoring           | Beck, Fowler, Thomas                             | TDD, patterns, pragmatic            |
| security              | Schneier, Hunt, Hyppönen, Ormandy, Ptacek        | Crypto, web, vulns, threat modeling |

## Session Protocol

Three-phase structured deliberation:

1. **Feynman opens** — Reframes question to essence, asks 1-2 first-principles questions, challenges assumptions in plain language, uses analogies
2. **Council responds** — Each member speaks in authentic voice (2-4 paragraphs), draws from actual work/books/talks, disagrees when philosophies conflict
3. **Synthesis** — Key agreements, creative tensions, actionable takeaways

## Voice Engineering

The skill relies on LLM's training data containing extensive corpora from each expert. Voice guidelines provided per-member:

- Feynman: curious, playful, cuts jargon, "surely you're joking" energy
- Torvalds: blunt, technical, occasionally abrasive, practical
- Munger: folksy wisdom, mental models, inversion
- Jobs: poetic, obsessive about details
- Schneier: measured, policy-aware, "security is a process"

**Key design choice**: Members chosen specifically because they have large written/spoken corpora in training data. This is smart — the LLM can genuinely channel distinctive voices rather than producing generic "expert" output.

## Relevance to Helioy

### 1. Plugin Structure Reference (Medium value)

Clean example of a minimal marketplace plugin. Confirms patterns we already documented in `claude-plugin-distribution.md`. The marketplace.json schema URL is a useful reference.

### 2. Multi-Persona Deliberation Pattern (High value)

The council pattern is structurally identical to what nancyr does at the process level — multiple specialized agents deliberating on a problem with structured synthesis. The difference:

| Aspect      | Council (prompt)                     | Nancyr (orchestrator)           |
| ----------- | ------------------------------------ | ------------------------------- |
| Execution   | Single LLM call, personas via prompt | Multiple agent processes        |
| Memory      | None (session only)                  | Persistent via am               |
| Tool access | None                                 | Full tool access per agent      |
| Cost        | Cheap (one API call)                 | Expensive (multiple sessions)   |
| Depth       | Surface (LLM knowledge only)         | Deep (can read code, run tests) |
| Fidelity    | LLM's training data                  | Actual expert systems/tools     |

**Insight**: The council pattern is a lightweight precursor to full multi-agent deliberation. It works well for high-level strategic questions where you want diverse perspectives but don't need agents to actually _do_ anything. Nancyr handles the cases where agents need tool access and persistent state.

### 3. Synthesizer Role (High value)

Feynman's role as the "always present" first-principles questioner who opens every session is a strong pattern. In nancyr terms, this maps to having a dedicated "reframing agent" that runs before task decomposition — questioning assumptions before work begins.

**Applicable to nancyr**: Consider a "Feynman phase" in nancy orchestration where the first step is always to reframe the task to its essence before decomposing into sub-tasks.

### 4. Skill Argument Parsing (Low value)

The `--board=X` argument parsing via `$ARGUMENTS` is standard Claude Code — nothing novel, but confirms how argument-hint works in practice.

## What We Could Adopt

### Direct adoption: No

The council skill itself isn't something to install — it's pure prompt engineering and doesn't integrate with Helioy's tool ecosystem. We'd get more value from our own tools.

### Pattern adoption: Yes

1. **First-principles reframing phase** — Add to nancyr's task decomposition: before breaking work into sub-tasks, have the orchestrator reframe the problem statement, identify assumptions, and validate scope
2. **Structured synthesis** — The "agreements / tensions / takeaways" format is a good template for nancyr's result aggregation when multiple agents report back
3. **Voice-per-agent** — If we ever build persona-based advisors into Helioy, the approach of selecting experts with large training corpora is the right strategy
4. **Lightweight deliberation skill** — Could build a Helioy-native version that combines prompt-based council with actual tool access (read code, check architecture) for higher-fidelity advice

## Verdict

**Interesting, not actionable right now.** The council pattern validates design choices we're already making in nancyr (multi-perspective deliberation, structured synthesis). The first-principles reframing phase is worth considering for nancy task decomposition. No need to install or fork — the value is in the patterns, not the code.
