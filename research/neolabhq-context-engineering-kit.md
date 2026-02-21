---
title: NeoLabHQ context-engineering-kit review
type: research
tags: [github-review, claude-code-plugins, skills, context-engineering, reflexion, sdd, prompt-library]
summary: Single-author Claude Code plugin marketplace, 14 plugins of curated long-form prompts. ~57k lines of markdown, ~1.5k lines of code. Strong README/marketing, almost no engineering. One genuinely useful primitive (per-skill `valid_until` evidence decay), the rest is prompt-shaped opinion that does not transfer.
status: active
source: github-researcher
confidence: high
created: 2026-05-01
updated: 2026-05-01
---

# NeoLabHQ/context-engineering-kit

## Stats

| Field | Value |
| --- | --- |
| Repo | https://github.com/NeoLabHQ/context-engineering-kit |
| Stars | 903 |
| Forks | 82 |
| Created | 2025-11-13 (~5.5 months old) |
| Last push | 2026-04-22 |
| Contributors | 5 (LeoVS09 = 298 commits, the other 4 = 1 each — single-author repo) |
| Author | Vlad Goncharov (NeoLab finance) |
| License | GPLv3 |
| Repo size | ~9 MB |
| Primary language | TypeScript (37 KB), Shell (12 KB), Just (8 KB), Dockerfile (3 KB) |
| CI | None (no `.github/workflows`) — README mentions "GitHub Action" guides hosted externally |
| Tests | 1 file: `plugins/reflexion/hooks/src/onStopHandler.test.ts` |
| Docs site | https://cek.neolab.finance (GitBook) |
| Plugin count | 14 (reflexion, sdd, sadd, review, git, tdd, ddd, fpf, kaizen, customaize-agent, docs, tech-stack, mcp) |
| SKILL.md files | 63 |
| Markdown LOC across plugins | 56,888 |
| TypeScript+Shell LOC total | 1,500 |
| README size | 40,436 bytes / 649 lines |

**README claim vs reality.** The README lists "minimal token footprint" and "scientifically proven" as headline features, citing 12 arXiv papers. The code/prompt ratio (~1500:57000) shows this is a long-form prompt library, not an engineered system. Individual SKILL.md files run 1,000–1,800 lines each (`plan-task` 1,223; `implement-task` 1,785). The "token-efficient" claim is contradicted by file sizes; the "scientifically proven" claim is name-dropping (Reflexion, ACE, ToT papers) without measurable benchmarks in this repo. The reliability table in the README ("60–80% one-shot, 99% with /plan-task + human review") cites "real development usage on production projects for more than 6 months" with no method, no fixtures, no anchor benchmark. Treat those numbers as marketing, not data.

## Grade

**C+ / borderline B−.**

Reasoning: well-organised, well-written prompt library with a working marketplace.json and one real primitive (FPF evidence decay). Below B− tier (claudex/metaharness) on engineering substance — there's effectively no system to study, only prose. Above DeepDiagram (C) because the prose is genuinely useful as a literature reference and the marketplace structure is clean. Anchored against `obra/superpowers` (B+, also a prompt library) the gap is large: superpowers ships hooks, version-bump registries, env-var hook dispatch; this repo ships one 50-line hook plus a transcript-parsing helper.

## Primitives that transfer

Three primitives are worth lifting. None are large.

### 1. FPF evidence-decay model — landing target: context-matters

`plugins/fpf/skills/decay/SKILL.md:1-228` and `plugins/fpf/skills/query/SKILL.md:1-178`.

The FPF plugin treats every knowledge entry as having a `valid_until` date plus a layer (L0 proposed → L1 verified → L2 validated). A separate `/decay` command surfaces FRESH/STALE/EXPIRED entries and offers three governance actions: refresh (re-verify), deprecate (downgrade layer), waive (explicitly accept stale evidence with a deadline and rationale, recorded as a separate file).

Why this matters for cm: cm currently has no decay model. Lessons and decisions accumulate forever. The retrieval-debugging memory in this user's own MEMORY.md is already an example of a fact that needs a half-life. The transferable shape:

- Add optional `valid_until: ISO-date` + `confidence_layer: proposed | verified | validated` to cm entry frontmatter
- Provide `cx_decay` MCP tool that returns the FRESH/STALE/EXPIRED report
- Support a "waiver" entry kind that explicitly extends validity without re-verification, surfacing rationale at recall time

The WLNK ("weakest link") rule from `decay/SKILL.md:183-188` ("a hypothesis is STALE if any of its evidence is expired") is also a clean composition rule for chained decisions.

### 2. Two-stage task lifecycle (draft → todo → in-progress → done) by directory location — landing target: helioy-plugins (sdd-style skill) or context-matters (as session/project state)

`plugins/sdd/skills/plan-task/SKILL.md:67-140` and the folder layout described at lines 318–325.

Status-by-folder (`.specs/tasks/draft/`, `todo/`, `in-progress/`, `done/`) is a deliberate refusal to encode task status in frontmatter or a database. `git mv` is the state transition. `--refine` mode reads `git diff HEAD -- <file>` to detect which sections the user edited, then re-runs only the stages downstream of that section using a section-to-stage mapping table (`plan-task/SKILL.md:130-137`).

Why this matters: the diff-driven re-run pattern is genuinely clever and small. For a future helioy-plugins spec/plan skill, the section-to-stage mapping table plus `git diff HEAD` parsing is ~30 lines of prompt logic that gives partial-replan semantics for free. The four-folder lifecycle is also a usable convention if helioy-plugins ever ships a task workflow.

### 3. Anti-hallucination judge guards — landing target: helioy-plugins (any judge skill) or attention-matters (salience scoring)

`plugins/sdd/skills/plan-task/SKILL.md:344-348`:

> - Reject Long Reports: If an agent returns a very long report instead of using the scratchpad, reject the result.
> - Judge Score 5.0 is a Hallucination: If a judge returns 5.0/5.0, treat it as hallucination or lazy evaluation. Reject and re-run.
> - Reject Missing Scores: If a judge report is missing the numerical score, reject it.

These are three concrete anti-patterns for LLM-as-judge that operationalise scepticism. The 5.0 rule especially is a cheap, non-obvious heuristic. For any Helioy component that uses LLM-as-judge (review skill, sadd-style judge, am salience scoring), these three guards are a paste-in addition to the judge prompt.

## Does NOT transfer

### 1. The ACE memorize → CLAUDE.md curation flow

`plugins/reflexion/skills/memorize/SKILL.md:1-303` curates reflections into CLAUDE.md. Skip.

Reason: Helioy already has a richer memory architecture (cm structured store, am geometric memory, ~/.mdx knowledge base). The ACE pattern of "append bullets to CLAUDE.md" is what cm was specifically designed to replace — CLAUDE.md is a flat token-eating context block, cm provides scoped retrieval with priority. Adopting the memorize skill would actively regress Helioy. The ACE paper (arxiv 2510.04618) is worth reading, but the implementation here is the wrong substrate.

### 2. The 14-plugin marketplace footprint, the 1000+ line SKILL.md files, the SDD/SADD orchestration ceremony

These are full Claude Code workflow systems (multi-phase, multi-agent, judge-gated, threshold-tuned). Skip wholesale.

Reason: superpowers already occupies this slot in Stuart's setup, with better engineering (env-var hook dispatch, per-platform manifests, version-bump registry). The CEK SDD plugin is a heavier, more ceremonious version of the same idea with no measurable advantage. The 1,200-line plan-task SKILL.md is the opposite of "minimal token footprint" — loading even one such skill at session start would burn 5–8k tokens before any real work.

The reflexion hook (`plugins/reflexion/hooks/src/onStopHandler.ts:11-37`) is also redundant: it parses transcripts to detect the word "reflect" in the user prompt and blocks Stop with a `/reflexion:reflect` instruction. Reasonable code, but Helioy's hook surface is already configurable through `update-config` and `helioy-bus`.

## Verdict

**Inspiration-only, leaning skip.** Borrow the FPF decay model into context-matters and the three judge anti-hallucination guards into any Helioy judge skill. Do not install any of the plugins. Do not vendor any code. Do not adopt the SDD/SADD ceremony. The README's reliability percentages are not reproducible without their internal tests, and the file sizes contradict the token-efficiency claim.

## Why

The repo's structural problem is that it sells engineering and ships prose. 57k lines of markdown represent six months of one developer's prompt-craft, organised into a clean marketplace. That's a useful artefact to read once but not a substrate to build on. The actual code (1,500 LOC) is a single 50-line hook plus a transcript-parsing helper — far below the engineering bar set by claudex (B−), metaharness (B−), or notebooklm-py (A−).

The FPF plugin is the one component that survived close reading. Its decay/waiver/deprecate triad is a real protocol with file artefacts, audit trail, and explicit governance actions. That's worth lifting. Everything else is either redundant with superpowers or actively misaligned with Helioy's memory architecture.

## How to apply

1. **Add evidence decay to cm.** Extend cm entry schema with optional `valid_until` and `confidence_layer`. Add `cx_decay` MCP tool returning the FRESH/STALE/EXPIRED report. Decide whether to support a separate `waiver` entry kind or fold waivers into existing `decision` kind with a `waives:` reference field. Smallest version: just `valid_until` on existing entries; `cx_decay` reads frontmatter, no schema change required.

2. **Add three judge guards to any Helioy review/judge skill.** Drop these three rules verbatim into the relevant SKILL.md (or whatever review prompt Helioy uses): reject long reports, treat 5.0/5.0 as hallucination, reject missing scores.

3. **Read the context-engineering SKILL.md once, do not vendor.** `plugins/customaize-agent/skills/context-engineering/SKILL.md` is a textbook-quality summary of attention budget, lost-in-middle, context poisoning, four-bucket optimization (write/select/compress/isolate). Worth reading; not worth installing. Anything actionable from it is already in Anthropic's prompt-engineering docs that Stuart has read.

4. **Skip everything else.** Do not install reflexion, sdd, sadd, ddd, kaizen, customaize-agent, docs, tech-stack, mcp, review, git, tdd, fpf-as-plugin. Helioy has equivalents or better in superpowers + helioy-plugins.

## Sources consulted

- README.md (lines 1-650) — full read
- `.claude-plugin/marketplace.json:1-156` — plugin inventory
- `plugins/reflexion/hooks/src/onStopHandler.ts:1-50` — actual hook logic
- `plugins/reflexion/hooks/src/lib.ts:1-475` — transcript parsing helper
- `plugins/reflexion/hooks/src/session.ts:1-58` — session data persistence to /tmp
- `plugins/reflexion/hooks/hooks.json:1-26` — hook wiring
- `plugins/reflexion/skills/memorize/SKILL.md:1-303` — ACE curation flow (rejected)
- `plugins/customaize-agent/skills/context-engineering/SKILL.md:1-1261` — context-engineering textbook (read once)
- `plugins/sdd/skills/plan-task/SKILL.md:1-1224` — multi-phase workflow with judge gates
- `plugins/fpf/skills/decay/SKILL.md:1-228` — evidence decay model (lift)
- `plugins/fpf/skills/query/SKILL.md:1-178` — knowledge layer query model
- `plugins/git/skills/git-notes/SKILL.md:1-438` — git notes reference (skipped)
- gh API: contributors, repo metadata
- Filesystem inventory of `plugins/`, `.claude/`, `.devcontainer/`

## Open questions

- Can the cm scope hierarchy (global > project > repo > session) be extended with the FPF layer model (proposed → verified → validated) cleanly, or do they conflict semantically? Layer is per-entry confidence; scope is per-entry visibility. Likely orthogonal but worth checking.
- Does Helioy already have a decay or expiry concept I'm missing in cm? Search before implementing.
