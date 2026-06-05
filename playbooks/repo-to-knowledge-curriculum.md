---
title: Repo to Knowledge Curriculum
type: playbooks
tags: [knowledge-base, curriculum, github-research, warroom, moe, mdx, method]
summary: Turn a canonical external repo (tutorial, reference implementation, spec) into a verified ~/.mdx/knowledge/<domain>/ curriculum with thin cm/skill adapters. Worked pilot — kubernetes-the-hard-way.
status: active
created: 2026-06-05
updated: 2026-06-05
project: helioy
related: [kubernetes-knowledge-substrate]
confidence: high
---

# Repo to Knowledge Curriculum

A repeatable recipe for converting a canonical external repo into durable, agent-retrievable expertise. The pilot instance is `kubernetes-the-hard-way` (see `~/.mdx/knowledge/kubernetes/` and `~/.mdx/design/kubernetes-knowledge-substrate.md`). Use this when a repo is worth *mastering*, not just borrowing from.

## When to use

- The repo is a teaching artifact, reference implementation, or spec you want lasting fluency in.
- The goal is expertise that serves several consumers at once: agent recall during work, personal study, and content.
- Not for code-borrow reviews (use the GitHub repo review envelope) or one-off lookups.

## The shape: one substrate, thin adapters

The knowledge lives **once** in `~/.mdx/knowledge/<domain>/`. Every other consumer points at it rather than copying it:

| Layer | Role |
|---|---|
| Source of truth | the cloned repo (`~/Dev/LLM/DEV/helioy/REFS/<repo>`) + a long-form synthesis in `~/.mdx/research/<vendor>-<repo>.md` |
| Canonical substrate | `~/.mdx/knowledge/<domain>/` — `index.md` + N modules, md-matters indexed |
| Agent-expertise adapter | one cm `reference` pointer entry routing `cx_recall` into the curriculum |
| Skill adapter | a thin `helioy-tools:<domain>-fundamentals` skill (router into the curriculum) |
| Content adapter | blog-architect / social-loop read `~/.mdx/knowledge/` on demand |

DRY guarantee: modules exist once. cm holds a pointer. The research essay is a different altitude (narrative) and complements the operational modules.

## Steps

### 1. Clone and map
- Clone to `~/Dev/LLM/DEV/helioy/REFS/<repo>` (shallow).
- Map topology: docs, configs, units, line counts. Read the README and license files directly.
- **Record the license precisely.** Many repos are dual-licensed (code vs prose). This governs what derived knowledge may copy.

### 2. Deep research (subagent)
- Dispatch the `helioy-tools:github-researcher` agent. Brief it to produce an EXPERT synthesis (not a code-borrow review): the mental-model arc, component deep-dives with `file:line` citations, the hardest/most valuable concept, what the artifact teaches that abstractions hide, and a **knowledge taxonomy of ~6-10 modules**.
- Output: `~/.mdx/research/<vendor>-<repo>.md`. This is the source of truth the modules draw from.
- Persist a cm `decision` entry (the GitHub repo review envelope) linking the artifact.

### 3. Design the substrate (brainstorm gate)
- Confirm domain framing (`knowledge/<domain>/`, broad enough to grow), the module cut, and the build phasing with the user.
- Write the spec to `~/.mdx/design/<domain>-knowledge-substrate.md`.

### 4. Author the modules (warroom, parallel)
- `~/.mdx/knowledge/<domain>/` is a new subdirectory under the `knowledge/` category (see `_schema.md`). Create it (plus `_versions/`) yourself first to avoid a write race.
- Spawn a warroom of `helioy-tools:codebase-analyst` panes (max 8). **Pair modules by source-file affinity** so each pane shares its reads. Root the panes' cwd at the cloned repo so citations resolve naturally.
- Brief each pane to a written plan; the plan's Conventions section carries the frontmatter template, the uniform module shape, the citation rule, and the licensing rule. Keep bus briefs to one screen.
- **Each module uniform shape**: Concept → Why it exists → repo implementation with `file:line` citations → What the abstraction hides → Gotchas. Frontmatter records `source` and `license`.
- Tell panes NOT to run git (concurrent `git add` collides on `index.lock`); the orchestrator stages and commits.

### 5. Verify independently (do not trust self-reports)
Run these as the orchestrator (Python beats shell on macOS for this):
1. **Citations resolve**: extract every `path:line`, confirm the file exists and the line is in range. Target 0 broken.
2. **Licensing clean**: n-gram overlap of module prose vs the CC-restricted source prose. Expect ~0; investigate any sentence-length match.
3. **Structure**: frontmatter valid (`type: knowledge`), each module has its sections.

### 6. Flagship MoE sign-off (peer-consensus)
- The load-bearing module (the one where a confident draft most plausibly ships a subtle error) gets a mixture-of-experts pass: the same `codebase-analyst` on **Claude and Codex**, wired peer-to-peer.
- They adversarially cross-check technical correctness against ground truth, converge on a change set, sign off with the fixed phrase. The orchestrator applies edits, then collects clean sign-offs.
- **Why it matters**: mechanical verification proves provenance and structure, not correctness. Citations can resolve perfectly while the interpretation is wrong. (Pilot: the MoE pass caught an inverted RBAC gotcha and a key-misattribution that all mechanical checks had passed.)

### 7. Wire the adapters
- **md-matters**: reindex with the `mdm` CLI rooted at `~/.mdx` (`mdm index ~/.mdx`). The connected mdm MCP is rooted at the project dir, not `~/.mdx` — use the CLI. Smoke-test retrieval.
- **cm pointer**: store one `reference` entry at the project scope mapping the modules and a "recall when…" trigger.
- **Skill**: build a thin `helioy-tools:<domain>-fundamentals` skill (via `helioy-skill-creator`) that routes into the curriculum.

### 8. Commit
Stage only the curriculum files (`_schema.md` if the category was new, the spec, the research essay, `knowledge/<domain>/`). Commit on the user's go.

## Gotchas

- **Wrong index root.** The mdm MCP server is rooted at the project dir; `~/.mdx` has its own index. Reindex `~/.mdx` via the CLI, not the MCP.
- **Shell instability on macOS.** Per-citation `wc`/`awk` loops can hit `command not found` mid-script. Do verification in one Python pass.
- **Empty `_versions/`.** Git does not track empty dirs; harmless.
- **Self-reports are not verification.** Re-check citations and licensing yourself before committing.
- **License copy boundary.** Original synthesis (facts/procedures in our own words) is freely usable; never paste CC-NC source prose; quote Apache-licensed config/unit snippets with a notice.
