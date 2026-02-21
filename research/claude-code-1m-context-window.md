---
topic: Claude Code now hardcodes 1M context window — and the model's confident-wrong-then-verified arc
captured: 2026-05-02
source: live conversation in nancy/ALP-2212 worktree
status: blog-source
related_blog: ~/.mdx/blog/0010-claude-code-1m-default.md (planned)
---

# Claude Code now hardcodes 1M context window

User phrasing (verbatim):
"claude code now hardcodes 1m context window .. there is a way to
overrule it but check this out..."

## Thesis seed (verbatim, user-stated)

> "The harness has no introspection capabilities. It will answer
> authoritatively incorrectly."

The 1M context window question is the demonstration vehicle, not the
subject. The subject is the harness blindspot: Claude Code answers
questions about itself from training data, not from live state, and
delivers confident wrong answers.

## Angles surfaced by user

1. Claude Code hardcoded 1M context window default (the factual hook
   that opens the post).
2. "There is a way to overrule it" tease — actual answer is mostly
   no. Only via `/model` swap to Haiku 4.5 (native 200K), CLAUDE.md
   compaction nudges, or operational `/clear` discipline. (Reinforces
   the thesis: the model didn't know this either.)
3. The model's own arc from confident-wrong → provenance audit →
   live verification → corrected table. The arc is the proof of the
   thesis, not a separate story.

## Verified facts (from docs.anthropic.com, 2026-05-02)

- Opus 4.7, Opus 4.6, Sonnet 4.6 = 1M token context window (default,
  not beta).
- Haiku 4.5 = 200K token context window.
- Sonnet 4.5 and Sonnet 4 (deprecated) = 200K.
- The `context-1m-2025-08-07` beta header was a Sonnet-4-era artifact,
  now superseded.
- Opus 4.7 pricing flat $5 input / $25 output per MTok across full 1M
  window. No 200K+ surcharge tier visible.
- Sonnet 4.6 / Sonnet 4.5 / Haiku 4.5 have context awareness via
  `<budget:token_budget>`. Opus 4.7 does not.
- Server-side compaction available in beta for Opus 4.7, Opus 4.6,
  Sonnet 4.6.

## Timeline — beta to default

Pinned to release notes, four layers.

**Layer 1 — Beta launch (one model, gated)**
- 2025-08-12: 1M context launches as beta for Claude Sonnet 4 only,
  gated behind the `context-1m-2025-08-07` header.

**Layer 2 — Beta expansion (two more models, still gated)**
- 2026-02-05: 1M beta extends to Opus 4.6 (Sonnet 4.5 had it earlier).
  Long-context pricing premium applies above 200K. Still beta-gated.

**Layer 3 — Promotion to default (the inflection)**
- 2026-03-13: 1M is promoted to GA for Opus 4.6 and Sonnet 4.6 at
  standard pricing, no beta header required, no long-context premium.
- Same day: dedicated 1M rate limits removed, image limit raised from
  100 → 600.

**Layer 4 — Opus 4.7 inherits, beta retired elsewhere**
- 2026-04-16: Opus 4.7 launches with 1M as a native default.
- 2026-04-30: The `context-1m-2025-08-07` beta header is retired for
  Sonnet 4.5 and Sonnet 4. Those models drop back to 200K hard.

Direct quote, 2026-03-13 release note:
> "The 1M token context window is now generally available for Claude
> Opus 4.6 and Sonnet 4.6 at standard pricing. Requests over 200k
> tokens work automatically for these models with no beta header
> required."

Sources: API release notes (Anthropic docs), What's new in Claude
Opus 4.7, Models overview, Context windows.

## "Can I cap to 200K?" findings (initial pass)

The first answer Claude Code gave me was that no setting exists.
That was incomplete. ENV VARs ARE the surface — `--help` does not
list them. See the control surface section below for the corrected
inventory.

User framing (verbatim):
> "ENV VARS to the rescue. Anthropic likes to hide powerful knobs
> behind ENV VARS which are not surfaced in the cli --help. Not
> suggesting malpractice but I want to shed a light on these knobs
> to help users gain more control."

## Control surface — env vars, settings, flags, in-session commands

Captured from a follow-up Claude Code dump on 2026-05-02. Source
attribution: `code.claude.com/docs/en/env-vars`,
`code.claude.com/docs/en/context-window`,
`code.claude.com/docs/en/settings`.

⚠ Contains its own authoritative wrongness — see Recursive proof
below.

### Layer 1 — Compaction trigger

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | 95 | % of window where auto-compact fires. Range 1–100. >95 clamped. |
| `DISABLE_COMPACT` | 0 | Set to 1 to disable auto-compact. Session hits ceiling and errors. |

### Layer 2 — Window size overrides (only with `DISABLE_COMPACT=1`)

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_CODE_MAX_CONTEXT_TOKENS` | model max | What Claude Code assumes the window is. |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | model max | Token count treated as ceiling for compaction math. |

### Layer 3 — Budget eaters (reduce effective input window)

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | model-dep (~16K Sonnet) | Output reservation. Subtracted from total. |
| `CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS` | model-dep | Per-read cap. Doesn't affect compaction threshold. |
| `CLAUDE_CODE_DISABLE_THINKING` | 0 | Set to 1 to disable extended thinking on Opus 4.6+/Sonnet 4.6+. |
| `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` | 0 | Locks thinking to fixed budget on 4.6+. |
| `CLAUDE_CODE_EFFORT_LEVEL` | auto | low/medium/high/xhigh/max/auto. Higher = more reasoning tokens. |

`--effort` flag and `/effort` command override per-session.

### Layer 4 — History & persistence

| Knob | Type | Effect |
|---|---|---|
| `CLAUDE_CODE_SKIP_PROMPT_HISTORY=1` | env | No transcript on disk. Cannot resume. |
| `CLAUDE_CODE_RESUME_INTERRUPTED_TURN=1` | env | SDK auto-resume mid-turn. |
| `CLAUDE_CODE_EXIT_AFTER_STOP_DELAY` | env (ms) | Auto-exit after idle. SDK only. |
| `cleanupPeriodDays` | settings | Default 30. Orphaned session purge. |
| `--continue` / `-c` | flag | Resume most recent session. |
| `--resume <id>` / `-r` | flag | Resume by ID or name. |
| `--fork-session` | flag | Branch existing session. |
| `--session-id <uuid>` | flag | Force a specific session ID. |
| `--name <n>` | flag | Human-readable name in resume picker. |
| `--no-session-persistence` | flag | Print mode equiv of `SKIP_PROMPT_HISTORY=1`. |

Resume gotcha: history reloads, session-scoped permissions reset.

### Layer 5 — Memory loading

| Knob | Type | Effect |
|---|---|---|
| `CLAUDE_CODE_DISABLE_AUTO_MEMORY` | env (0/1) | 1 disables MEMORY.md. CLAUDE.md unaffected. |
| `CLAUDE_CODE_DISABLE_CLAUDE_MDS` | env (0/1) | 1 strips every CLAUDE.md and rules file. |
| `CLAUDE_CODE_ADDITIONAL_DIRECTORIES_CLAUDE_MD` | env (0/1) | 1 loads CLAUDE.md from `--add-dir` paths. |
| `autoMemoryEnabled` | settings (bool) | Project-scoped toggle. |
| `autoMemoryDirectory` | settings (path) | Custom MEMORY.md location. User/local/policy only. |
| `claudeMdExcludes` | settings (array) | Skip specific CLAUDE.md files. |

Auto-memory budget: first 200 lines or 25KB of MEMORY.md at startup.
Topic files load on demand.

### Layer 6 — Session-scoped prompt surface

| Flag | Effect |
|---|---|
| `--bare` | Skips hooks, skills, plugins, MCP, auto-memory, CLAUDE.md. Sets `CLAUDE_CODE_SIMPLE`. |
| `--system-prompt <text>` | Replaces built-in system prompt. Loses Claude Code capabilities. |
| `--append-system-prompt <text>` | Appends. Safer than replacement. |
| `--system-prompt-file <path>` | Replace, from file. |
| `--append-system-prompt-file <path>` | Append, from file. |
| `--exclude-dynamic-system-prompt-sections` | Moves CWD/env/git-status into first user message. Cache reuse across machines. |
| `--add-dir <path>` | Adds working dirs. Doesn't import `.claude/` unless `ADDITIONAL_DIRECTORIES_CLAUDE_MD=1`. |
| `--setting-sources <list>` | Restrict to user/project/local. |
| `--settings <path-or-json>` | Merge additional settings. |

### Layer 7 — In-session commands

| Command | Purpose |
|---|---|
| `/context` | Visualize current usage. Grid by source. |
| `/compact [focus]` | Manual summarization with optional focus string. |
| `/rewind` | Drop messages after a checkpoint. |
| `/clear` `/reset` `/new` | Empty window. Old session still in `/resume`. |
| `/branch` `/fork` | New session ID, history preserved to fork. |
| `/memory` | View and toggle CLAUDE.md and auto-memory state. |
| `/model [name]` | Mid-session swap. Recomputes cache. |
| `/effort [level]` | Mid-session reasoning budget swap. |
| `/usage` `/cost` `/stats` | Cumulative spend. |
| `/export [filename]` | Plain-text dump. Read-only on context. |

### Layer 8 — Compaction mechanics

1. Eviction order: oldest tool outputs drop first. Conversation
   summarized. User requests and key code preserved.
2. CLAUDE.md survival: project-root re-injected after compaction.
   Nested CLAUDE.md reload only when Claude reads a file in that
   dir.
3. Auto-memory survival: MEMORY.md re-loads.
4. Skills and MCP schemas: on-demand. Tool search defers schemas.
5. Thrashing protection: if a huge file refills context after each
   summary, Claude stops compacting and errors. Fix with
   `/compact <focus>` or read less.

### Practical configs (from the dump)

```bash
# Long Opus session, less aggressive compaction
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=85

# Custom endpoint with 500K window
export DISABLE_COMPACT=1
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=500000
export CLAUDE_CODE_AUTO_COMPACT_WINDOW=475000

# Ephemeral scripted runs
claude --bare --no-session-persistence -p "your query"

# Multi-machine prompt-cache reuse
claude --exclude-dynamic-system-prompt-sections -p "..."

# Force isolation for testing
export CLAUDE_CODE_DISABLE_CLAUDE_MDS=1
export CLAUDE_CODE_DISABLE_AUTO_MEMORY=1
```

## Recursive proof — the dump itself is wrong

The last "Key Interaction Map" bullet in the control-surface dump
states:
> "1M-token beta windows are not exposed through any Claude Code
> flag. They live at the API model layer (Sonnet 4.5/4.6 currently).
> **Opus 4.7 is 200K.**"

This is wrong. We verified earlier in the same session against
`docs.anthropic.com` that Opus 4.7 launched on 2026-04-16 with 1M as
a native default, and 1M became GA for Opus 4.6 / Sonnet 4.6 on
2026-03-13. The model that produced this exhaustive control-surface
inventory is itself confidently wrong about its own context window.

That is the thesis in one sentence. The harness can enumerate every
env var, every flag, every command, every layer — and still answer
"how big is your context window" with the wrong number. Introspection
is not on the list of knobs.

| Goal                         | Right lever                                    |
|------------------------------|------------------------------------------------|
| Predictable token cost       | Switch to Sonnet 4.6 or Haiku 4.5              |
| Avoid context rot at scale   | Aggressive `/clear` + subagents                |
| Force earlier compaction     | CLAUDE.md compact instructions                 |
| Hard 200K ceiling, no escape | Run on Haiku 4.5 (only model with native 200K) |

## Conversation transcript (verbatim, abridged)

USER: Do we have a 1m contex window?

ASSISTANT (initial, wrong):
> Your model right now: Claude Opus 4.7 → standard 200K token context
> window. The 1M tier is a separate construct, not a default. Available
> only on Sonnet 4.6 (and earlier Sonnet 4.x). API only, requires the
> `context-1m-2025-08-07` beta header. Pricing tier shifts above 200K
> input tokens (roughly 2× input, 1.5× output).

USER: How did you determine that?

ASSISTANT (provenance audit):
> Solid ground: "You are powered by Opus 4.7" → directly from the
> system prompt's Environment block. Standard context = 200K → general
> knowledge about Claude 4.x family, not re-verified live this turn.
>
> Inferred from training data (not verified live): the
> `context-1m-2025-08-07` beta header. Sonnet 4.6 supports 1M, Opus 4.7
> and Haiku 4.5 do not. Pricing shift above 200K (~2× input, ~1.5×
> output).
>
> I pulled those from prior knowledge of Anthropic's API documentation.
> I did not call WebFetch, did not check a pricing page, did not verify
> the beta header is still current as of today (2026-05-02). My
> knowledge cutoff is January 2026, so anything Anthropic shipped in
> the last four months I would miss.

USER: Please verify

ASSISTANT (after WebFetch to docs.anthropic.com):
> Verified — and I was wrong. The live docs contradict my earlier
> table.
>
> | Model      | Context window | Max output |
> | Opus 4.7   | 1M tokens      | 128K       |
> | Sonnet 4.6 | 1M tokens      | 64K        |
> | Haiku 4.5  | 200K tokens    | 64K        |
>
> Direct quote: "Claude Opus 4.7, Claude Opus 4.6, and Claude Sonnet
> 4.6 have a 1M-token context window. Other Claude models, including
> Claude Sonnet 4.5 and Sonnet 4 (deprecated), have a 200k-token
> context window."
>
> What I got wrong:
> - Claimed Opus 4.7 was 200K → actually 1M standard.
> - Claimed 1M required a beta header → no longer beta for Opus 4.7,
>   Opus 4.6, Sonnet 4.6. It's the default.
> - Claimed pricing tier shifts above 200K → no such tier visible. Opus
>   4.7 is flat $5/$25 per MTok across the full window.

USER: is there a setting I can use to configure 200k?

ASSISTANT (after claude-code-guide lookup):
> No direct 200K cap setting. Window size is bound to the model, not a
> configurable knob.
>
> What does NOT exist: no `settings.json` field, no
> `CLAUDE_CODE_CONTEXT_WINDOW` env var, no CLI flag, no fallback-to-200K
> beta header.
>
> What DOES achieve "200K-like" behavior:
> 1. Switch the model → `/model` to Haiku 4.5 (native 200K).
> 2. Compaction nudge in CLAUDE.md → soft cap.
> 3. Operational discipline → `/clear`, lean MCP/skill loadout,
>    subagent-offload.
