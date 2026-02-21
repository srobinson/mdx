---
title: Claude Code Custom Slash Commands, Skills, and Extensibility Model
type: research
tags: [claude-code, slash-commands, skills, hooks, plugins, extensibility, agent-skills]
summary: Complete reference for Claude Code's unified slash command/skill system, including legacy .claude/commands/, the SKILL.md format, hooks, plugins, and the Agent Skills open standard
status: active
source: deep-research
confidence: high
created: 2026-03-15
updated: 2026-03-15
---

## Executive Summary

Claude Code's extensibility model comprises five mechanisms: **skills** (the primary abstraction, subsuming the older "custom commands"), **hooks** (lifecycle event automation), **subagents** (delegated execution contexts), **plugins** (distributable bundles of skills/agents/hooks/MCP servers), and **MCP servers** (external tool integration). Custom commands (`.claude/commands/*.md`) still work but have been formally merged into the skills system. A file at `.claude/commands/deploy.md` and a skill at `.claude/skills/deploy/SKILL.md` both create `/deploy` and behave identically. Skills add supporting files, frontmatter-controlled invocation, and automatic context loading. The SKILL.md format follows the [Agent Skills](https://agentskills.io) open standard, adopted by Claude Code, VS Code Copilot, OpenCode, Cursor, Amp, and others.

## 1. How Custom Slash Commands Are Defined and Registered

### Legacy: `.claude/commands/` (still works)

Place a Markdown file in `.claude/commands/` and the filename (minus `.md`) becomes the slash command name.

```
.claude/commands/
  deploy.md        -> /deploy
  review.md        -> /review
  fix-issue.md     -> /fix-issue
```

These files support the same YAML frontmatter as SKILL.md files. No registration step is required; Claude Code discovers them at session start and on file change.

### Current: `.claude/skills/` (recommended)

Each skill is a directory containing a `SKILL.md` entrypoint plus optional supporting files.

```
.claude/skills/
  deploy/
    SKILL.md           # Required entrypoint
    template.md        # Optional template
    examples/
      sample.md        # Optional example
    scripts/
      validate.sh      # Optional script
```

The directory name becomes the slash command name. If a skill and a legacy command share the same name, the skill takes precedence.

### Precedence and Scope

| Location   | Path                                     | Applies to                     |
|:-----------|:-----------------------------------------|:-------------------------------|
| Enterprise | Managed settings                         | All users in organization      |
| Personal   | `~/.claude/skills/<name>/SKILL.md`       | All your projects              |
| Project    | `.claude/skills/<name>/SKILL.md`         | This project only              |
| Plugin     | `<plugin>/skills/<name>/SKILL.md`        | Where plugin is enabled        |

Priority: enterprise > personal > project. Plugin skills use `plugin-name:skill-name` namespacing and cannot conflict with other levels.

Monorepo support: skills in nested `.claude/skills/` directories (e.g., `packages/frontend/.claude/skills/`) are discovered automatically when editing files in that subdirectory.

## 2. File Format: SKILL.md and Command .md

### YAML Frontmatter Fields

All fields are optional. Only `description` is recommended.

| Field                      | Type    | Description                                                                                |
|:---------------------------|:--------|:-------------------------------------------------------------------------------------------|
| `name`                     | string  | Display name. Lowercase, numbers, hyphens. Max 64 chars. Defaults to directory name.       |
| `description`              | string  | What the skill does. Claude uses this for automatic invocation decisions.                   |
| `argument-hint`            | string  | Shown during autocomplete. e.g., `[issue-number]` or `[filename] [format]`                 |
| `disable-model-invocation` | boolean | `true` prevents Claude from auto-loading. Manual `/name` only. Default: `false`.           |
| `user-invocable`           | boolean | `false` hides from `/` menu. Background knowledge only. Default: `true`.                   |
| `allowed-tools`            | string  | Comma-separated tools Claude can use without permission when skill is active.              |
| `model`                    | string  | Model override when skill is active.                                                       |
| `context`                  | string  | `fork` runs in a subagent. Default: inline.                                                |
| `agent`                    | string  | Subagent type when `context: fork`. Options: `Explore`, `Plan`, `general-purpose`, custom. |
| `hooks`                    | object  | Lifecycle hooks scoped to this skill's lifetime.                                           |

### Invocation Control Matrix

| Frontmatter                      | User invokes | Claude invokes | Context loading                                          |
|:---------------------------------|:-------------|:---------------|:---------------------------------------------------------|
| (default)                        | Yes          | Yes            | Description always loaded; full content on invocation    |
| `disable-model-invocation: true` | Yes          | No             | Description NOT loaded; full content on user invocation  |
| `user-invocable: false`          | No           | Yes            | Description always loaded; full content on invocation    |

### String Substitutions

| Variable               | Description                                                    |
|:-----------------------|:---------------------------------------------------------------|
| `$ARGUMENTS`           | All arguments passed after `/skill-name`                       |
| `$ARGUMENTS[N]`        | 0-based positional argument access                             |
| `$N`                   | Shorthand for `$ARGUMENTS[N]` (e.g., `$0`, `$1`, `$2`)        |
| `${CLAUDE_SESSION_ID}` | Current session ID                                             |
| `${CLAUDE_SKILL_DIR}`  | Directory containing this skill's SKILL.md                     |

If `$ARGUMENTS` does not appear in the skill content, arguments are appended as `ARGUMENTS: <value>`.

### Dynamic Context Injection

The `` !`command` `` syntax runs shell commands as preprocessing before the skill content is sent to Claude:

```yaml
---
name: pr-summary
context: fork
agent: Explore
---

## Context
- PR diff: !`gh pr diff`
- Changed files: !`gh pr diff --name-only`

## Task
Summarize this pull request.
```

Each `` !`command` `` executes immediately. Output replaces the placeholder. Claude only sees the rendered result.

### Extended Thinking

Include the word "ultrathink" anywhere in skill content to enable extended thinking mode.

### Context Budget

Skill descriptions consume context budget: 2% of context window, fallback 16,000 characters. Override with `SLASH_COMMAND_TOOL_CHAR_BUDGET` env var. Check `/context` for warnings about excluded skills.

## 3. Bundled Skills

These ship with Claude Code and are always available:

| Skill                       | Purpose                                                                    |
|:----------------------------|:---------------------------------------------------------------------------|
| `/batch <instruction>`      | Parallel codebase changes via git worktrees, one agent per unit            |
| `/claude-api`               | Load Claude API reference for current language + Agent SDK reference       |
| `/debug [description]`      | Troubleshoot current session via debug log                                 |
| `/loop [interval] <prompt>` | Repeat a prompt on interval (polling, monitoring)                          |
| `/simplify [focus]`         | Three parallel review agents for code quality, then applies fixes          |

## 4. The Full Extensibility Model

### Skills (primary abstraction)

Declarative SKILL.md files. Can be reference content (conventions, patterns loaded inline) or task content (step-by-step workflows, often with `disable-model-invocation: true`). Support subagent execution via `context: fork`, supporting files, and frontmatter-controlled invocation.

### Hooks (lifecycle automation)

Shell commands, HTTP endpoints, LLM prompts, or agents that fire at 22+ lifecycle events. Configured in `.claude/settings.json` or skill/agent frontmatter. Key events:

- **Preventive** (can block): `PreToolUse`, `UserPromptSubmit`, `PermissionRequest`
- **Observational**: `PostToolUse`, `PostToolUseFailure`, `Notification`
- **Control** (can block): `Stop`, `SubagentStop`, `TaskCompleted`, `ConfigChange`
- **Setup/Cleanup**: `SessionStart`, `SessionEnd`, `InstructionsLoaded`

Four handler types: `command` (shell), `http` (webhook), `prompt` (LLM evaluation), `agent` (spawned agent).

Hooks can be scoped to a skill's lifetime via frontmatter:

```yaml
---
name: secure-operations
hooks:
  PreToolUse:
    - matcher: "Bash"
      hooks:
        - type: command
          command: "./scripts/security-check.sh"
---
```

### Subagents

Isolated execution contexts with their own system prompt, tools, and model. Defined in `.claude/agents/`. Skills use subagents via `context: fork` + `agent` field. Subagents can preload skills.

### Plugins (distributable bundles)

A directory with `.claude-plugin/plugin.json` manifest plus `skills/`, `agents/`, `hooks/`, `commands/`, `.mcp.json`, `.lsp.json`, and `settings.json`. Plugin skills are namespaced: `/plugin-name:skill-name`. Distributed via marketplaces. Tested locally with `--plugin-dir`.

Plugin directory structure:

```
my-plugin/
  .claude-plugin/
    plugin.json          # Manifest (name, description, version, author)
  skills/                # SKILL.md directories
  agents/                # Agent definitions
  hooks/
    hooks.json           # Event handlers
  commands/              # Legacy command .md files
  .mcp.json              # MCP server configs
  .lsp.json              # LSP server configs
  settings.json          # Default settings (currently only `agent` key)
```

### MCP Servers (external tool integration)

Configured in `.mcp.json`. Provide tools Claude can call. Integrated at the protocol level via Model Context Protocol.

### Relationship Summary

```
Plugin (distributable package)
  ├── Skills (SKILL.md) ─────── user or Claude invokes as /command
  │     ├── Supporting files
  │     ├── Scoped hooks (frontmatter)
  │     └── Subagent execution (context: fork)
  ├── Agents (.claude/agents/) ── delegated isolated execution
  ├── Hooks (hooks.json) ──────── lifecycle event automation
  ├── MCP Servers (.mcp.json) ── external tool integration
  └── LSP Servers (.lsp.json) ── code intelligence
```

Skills and commands are the same concept now. Hooks are orthogonal (passive automation). Plugins are the packaging format. MCP/LSP are protocol integrations.

## 5. Community Examples

### Curated Collections

- **[awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)**: Comprehensive index of skills, hooks, commands, agents, orchestrators, and plugins.
- **[wshobson/commands](https://github.com/wshobson/commands)**: 57 production-ready slash commands in two categories: 15 workflows (multi-agent orchestration) and 42 tools (single-purpose utilities).
- **[qdhenry/Claude-Command-Suite](https://github.com/qdhenry/Claude-Command-Suite)**: Professional slash commands for code review, feature creation, security auditing, architectural analysis.

### Skill Toolkits

- **[alirezarezvani/claude-code-skill-factory](https://github.com/alirezarezvani/claude-code-skill-factory)**: Toolkit for building and deploying production-ready skills at scale.
- **[spences10/claude-skills-cli](https://github.com/spences10/claude-skills-cli)**: CLI scaffolding tool for creating skills with progressive disclosure validation.
- **[ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase)**: Project-specific skills (core-components, graphql-schema, systematic-debugging).
- **[trailofbits/skills](https://github.com/trailofbits/skills)**: Security-focused skills for code auditing and vulnerability detection.
- **[K-Dense-AI/claude-scientific-skills](https://github.com/K-Dense-AI/claude-scientific-skills)**: Research, science, engineering, analysis, finance skills.
- **[featbit/featbit-skills](https://github.com/featbit/featbit-skills)**: Includes a skill-authoring best practices skill.

### Agent Skills Open Standard

Skills follow [agentskills.io](https://agentskills.io), an open format maintained by Anthropic. Adopted by Claude Code, VS Code Copilot, OpenCode, Cursor, Amp, Letta, and Goose. The core spec requires a directory with `SKILL.md` containing YAML frontmatter + markdown instructions. Claude Code extends the standard with invocation control, subagent execution, and dynamic context injection.

## Sources Consulted

### Official Documentation
- [Extend Claude with skills](https://code.claude.com/docs/en/skills) (primary reference, fetched 2026-03-15)
- [Slash commands](https://code.claude.com/docs/en/slash-commands)
- [Hooks](https://code.claude.com/docs/en/hooks)
- [Create plugins](https://code.claude.com/docs/en/plugins)
- [Agent Skills specification](https://agentskills.io/specification)

### Community Blog Posts
- [Claude Code Tips: Custom Slash Commands](https://cloudartisan.com/posts/2025-04-14-claude-code-tips-slash-commands/)
- [How to Create Custom Slash Commands](https://en.bioerrorlog.work/entry/claude-code-custom-slash-command) (BioErrorLog)
- [How I use Claude Code](https://www.builder.io/blog/claude-code) (Builder.io)
- [Essential Claude Code Skills and Commands](https://batsov.com/articles/2026/03/11/essential-claude-code-skills-and-commands/) (Batsov)
- [Claude Code Merges Slash Commands Into Skills](https://medium.com/@joe.njenga/claude-code-merges-slash-commands-into-skills-dont-miss-your-update-8296f3989697) (Joe Njenga, Medium)
- [Claude Code Skills vs Slash Commands 2026](https://yingtu.ai/en/blog/claude-code-skills-vs-slash-commands) (YingTu)
- [Skills and Hooks Starter Kit](https://medium.com/@davidroliver/skills-and-hooks-starter-kit-for-claude-code-c867af2ace32) (David R Oliver, Medium)
- [Understanding Claude Code: Skills vs Commands vs Subagents vs Plugins](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins) (Young Leaders)

### GitHub Repositories
- [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code)
- [wshobson/commands](https://github.com/wshobson/commands) (57 commands)
- [qdhenry/Claude-Command-Suite](https://github.com/qdhenry/Claude-Command-Suite)
- [alirezarezvani/claude-code-skill-factory](https://github.com/alirezarezvani/claude-code-skill-factory)
- [ChrisWiles/claude-code-showcase](https://github.com/ChrisWiles/claude-code-showcase)
- [trailofbits/skills](https://github.com/trailofbits/skills)
- [agentskills/agentskills](https://github.com/agentskills/agentskills) (open standard spec)

## Source Quality Assessment

**Confidence: High.** The official docs at code.claude.com were fetched directly and provided complete, authoritative detail on every aspect of the system. The Agent Skills open standard spec at agentskills.io confirms the cross-tool interoperability story. Community examples on GitHub validate the documented patterns. Multiple independent blog posts (Batsov, BioErrorLog, Builder.io, YingTu) corroborate the commands-to-skills migration story.

One area of moderate confidence: the exact list of 22+ hook lifecycle events was summarized from the docs page rather than enumerated exhaustively. The hooks doc page is the authoritative source for the complete event list.

## Open Questions

1. **Skill description budget mechanics**: The 2% context window budget for skill descriptions is documented, but the exact behavior when skills are excluded (which skills get priority?) is not fully specified.
2. **Agent Skills standard evolution**: The open standard is early. Cursor, VS Code Copilot, and others adopt it, but the degree of frontmatter field compatibility across tools is unclear.
3. **Plugin marketplace maturity**: The official Anthropic marketplace accepts submissions, but the volume of published plugins and review process timelines are not documented.
4. **LSP integration depth**: Plugin LSP support is documented but the extent to which Claude Code uses LSP diagnostics, completions, and references in practice is not well covered by community reports.

## Actionable Takeaways

1. **Migrate `.claude/commands/*.md` to `.claude/skills/*/SKILL.md`** for access to supporting files, invocation control, and subagent execution. Legacy files continue working indefinitely.
2. **Use `disable-model-invocation: true`** for any skill with side effects (deploy, commit, publish). Prevents Claude from triggering it autonomously.
3. **Use `context: fork`** for expensive or isolated operations (research, batch processing). Keeps the main conversation context clean.
4. **Bundle scripts in skill directories** referenced via `${CLAUDE_SKILL_DIR}` for portable, self-contained skills.
5. **Use `` !`command` `` preprocessing** to inject live data (git status, PR info, env vars) into skill prompts before Claude sees them.
6. **Package reusable skills as plugins** when sharing across projects or teams. The `.claude-plugin/plugin.json` manifest enables marketplace distribution.
7. **Scope hooks to skills via frontmatter** rather than global settings when the hook only applies during a specific workflow.
