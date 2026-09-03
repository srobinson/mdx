---
title: Pstack support for Claude Code and Codex
type: research
tags: [pstack, claude, codex, agent-runtimes, plugins]
summary: Official upstream remains Cursor focused; three community ports provide distinct Claude Code and Codex adaptations.
status: active
created: 2026-09-11
updated: 2026-09-11
project: agent-runtimes
confidence: high
source: https://github.com/cursor/plugins/tree/main/pstack
---

# Pstack support investigation

As of 2026-09-11, I found no published Claude Code or Codex port maintained or
endorsed by Lauren Tan or Cursor. Current upstream ships only a Cursor plugin
manifest and documents Cursor installation. Community ports exist and are active.
This is a finding about the public sources checked, not proof that no private
work or unindexed announcement exists.

## Official status

- [Current upstream](https://github.com/cursor/plugins/tree/f5bdd6826fd0a0d9cbc4347134c3a74a200b9d9d/pstack)
  is version 0.15.2. It contains 47 skill entry points and only
  `.cursor-plugin/plugin.json`. Its author field names Lauren Tan.
- [PR 285](https://github.com/cursor/plugins/pull/285) proposed a native Codex
  package under `pstack/codex/`. GitHub reports `mergedAt: null`. The issue events
  API records its author, `0xjoma`, closing it on 2026-08-28. There is no public
  maintainer explanation in its conversation. It was not a shipped official port.
- [PR 330](https://github.com/cursor/plugins/pull/330) proposes a generic portable
  fork. It remains open. Its proposal is not an upstream support commitment.
- [Issue 237](https://github.com/cursor/plugins/issues/237) remains open and
  documents portability failures caused by display names in skill frontmatter.
  The checked upstream still uses `name: Poteto Mode`, `mode: true`, and `reminder:`.
- Searches of the public Anthropic official plugin repository returned no pstack
  result. The OpenAI plugins repository search returned an unrelated charting file.
  A search of the maintainer's public repositories found no dedicated official port.
- Direct access to the maintainer's X page failed. Indexed searches did not yield
  an official port announcement. No conclusion depends on claiming a complete X scan.

## Community options

| Project | Checked version | Upstream base | Hosts |
| --- | --- | --- | --- |
| [ericlitman/open-pstack](https://github.com/ericlitman/open-pstack) | 1.4.1 | 0.15.1, `f8abedd` | Claude Code and Codex |
| [michael-denyer/pstack-claude](https://github.com/michael-denyer/pstack-claude) | 0.9.28 | 0.14.8 plus September density changes, `e8d856f` | Claude Code, Codex; additional discovery paths for OpenCode, Gemini CLI, Prime Agent |
| [Aqua-123/pstack-for-codex](https://github.com/Aqua-123/pstack-for-codex) | 0.1.0 | 0.14.3, `bdf7aa3` | Codex |

### Open Pstack

Its README explicitly calls it an unofficial community project. It builds on
Michael Denyer's port, shares one skill tree between Claude Code and Codex, and
includes plugin manifests for both. It is the closest to current upstream among
the three inspected ports. Its upstream sync policy records exclusions and local
model routing decisions, so its behavior is not identical to upstream.

Provider dispatch uses the parent runtime for models it can run natively and an
external runner for the other provider CLIs. This preserves the possibility of
Claude, OpenAI, and Grok review panels. Grok is a worker provider, not a supported
parent host in this port.

[Upstream record](https://github.com/ericlitman/open-pstack/blob/de67e6b40511814171e5e4c8ad7af3b79f07c9ee/UPSTREAM.md),
[provider dispatch](https://github.com/ericlitman/open-pstack/blob/de67e6b40511814171e5e4c8ad7af3b79f07c9ee/plugins/pstack/skills/poteto-mode/references/provider-dispatch.md).

### Michael Denyer's port

The checked tree has 54 skills and both plugin manifests. It translates Cursor
primitives to Claude Code, with a separate Codex mapping document. Its shared
skills installation includes supporting scripts, references, portable agent
definitions, and license texts. Claude startup hooks and native agent registration
are separate from that skills installation.

The maintainer reports live Codex discovery and OpenCode discovery. Prime Agent
and Gemini CLI support are based on documentation; delegation and model mapping
on those additional hosts remain explicitly unverified. Codex mapping is source
guidance, not a guarantee that every API name or model selection fits this session.

[Pinned source](https://github.com/michael-denyer/pstack-claude/tree/5d8752c3dd620f344ed8f87ec47fbf3b1fb90b7e),
[upstream pins](https://github.com/michael-denyer/pstack-claude/blob/5d8752c3dd620f344ed8f87ec47fbf3b1fb90b7e/tools/upstream.json).

### Codex specific derivative

Aqua-123's port has 45 explicit skills, 23 playbooks, Codex invocation metadata,
optional agent profiles, a source lock and compatibility map. Its hook tracks
explicit Poteto Mode activation, with documented degradation when the hook is not
trusted. Benny automation remains optional and paused until separately activated.
It changes workflow and authorization rules rather than only substituting names.

[Pinned source](https://github.com/Aqua-123/pstack-for-codex/tree/03ffe520e21c840c967edb039f631888d0c1862c),
[source lock](https://github.com/Aqua-123/pstack-for-codex/blob/03ffe520e21c840c967edb039f631888d0c1862c/upstream.lock.json).

## Assessment and evidence boundary

For a shared Claude Code and Codex candidate, evaluate Open Pstack first. Its
recorded upstream base is newer and it explicitly implements provider dispatch.
For a Codex specific workflow with explicit activation, compare Aqua-123's design.
Michael Denyer's port offers the broadest documented host discovery paths.

These are candidates for evaluation, not an endorsement based on live task tests.
Importing into agent-runtimes would require reviewing resource paths, agent
dispatch, hooks, and scripts in addition to copying skill prose.

Clones were inspected under `/tmp/pstack-support.IAbN83`:

| Clone | Exact HEAD |
| --- | --- |
| upstream | `f5bdd6826fd0a0d9cbc4347134c3a74a200b9d9d` |
| open-pstack | `de67e6b40511814171e5e4c8ad7af3b79f07c9ee` |
| claude-port | `5d8752c3dd620f344ed8f87ec47fbf3b1fb90b7e` |
| codex-port | `03ffe520e21c840c967edb039f631888d0c1862c` |

GitHub reports successful CI on the inspected
[Open Pstack HEAD](https://github.com/ericlitman/open-pstack/actions/runs/34486434574)
and [Michael Denyer HEAD](https://github.com/michael-denyer/pstack-claude/actions/runs/34295848471).
The observed successful Aqua-123 workflow is a security scan, not a full task
evaluation. I did not install a port or run its live agent workflows. The existing
Matt Pocock import worktree was left unchanged.
