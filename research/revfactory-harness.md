---
title: revfactory/harness — meta-skill team-architecture factory for Claude Code
type: research
tags: [claude-code, plugin, meta-skill, agent-teams, orchestration, skills, harness, single-author, korean-en]
summary: Single-skill Claude Code plugin (Korean-first) that scaffolds .claude/agents and .claude/skills from one domain sentence. Six pre-named team patterns, prose-only, no runtime. Three transferable primitives for helioy-plugins and nancyr.
status: active
source: github-researcher
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

# revfactory/harness

## 1. Snapshot

| Field | Value |
|---|---|
| Repo | https://github.com/revfactory/harness |
| Stars | 2,930 |
| Forks | 424 |
| Created | 2026-03-26 |
| Last push | 2026-04-18 |
| License | Apache-2.0 |
| Primary language | HTML (landing page); content is Markdown |
| Disk size | ~9.3 MB (mostly four PNG marketing images) |
| Files tracked | 35 (4 PNGs, 4 READMEs/CHANGELOGs, 1 SKILL.md, 6 reference MDs, 4 audit MDs, 2 docs MDs, 2 plugin manifests, 2 HTMLs, 1 LICENSE, .github templates) |
| Source LOC | 1,953 markdown lines across `skills/` + `docs/` (SKILL.md = 443, references = 1,510). No code. |
| Test coverage | None. No tests, no CI, no fixtures. |
| Single-author vs team | Single author. `git log --format="%an" | sort | uniq -c`: revfactory 22, Minho Hwang 3, JunghwanNA 1, hnts03 1. The non-revfactory commits are tiny PRs (rename `skill.md`->`SKILL.md`, fix workspace rerun template). |
| Commit cadence | 27 commits across 8 days between 2026-03-27 and 2026-04-18. Burst pattern: launch week + 4 follow-up days. |
| Open issues | 2 (one is a "you're featured in Awesome Claude Code" notice). |
| Open PRs | 1 (Phase numbering consistency fix). |

**Calibrated grade: B-**

Justification. The repo is a single SKILL.md plus six reference MDs, no code, no tests, no CI. What it does well: tight Progressive Disclosure structure, six well-named team patterns, an explicit "evolve" loop with a change-history table baked into CLAUDE.md, and a QA-agent guide grounded in a real bug catalogue (SatangSlide, 7 boundary bugs catalogued). What drags it: prose-only deliverable, no runtime, no marketplace install verification beyond a quickstart doc, four 2-3MB marketing PNGs in the repo, three READMEs to maintain (EN/KO/JA), a `_workspace/` polluted with the author's own GTM launch artifacts. Lands between claudex (B-) and graphify (B). Below SuperagenticAI/metaharness (B-) since metaharness at least had Codex-runtime ambitions, but functionally similar in surface area. Above DeepDiagram (C) because the SKILL.md content itself is well-engineered.

## 2. What it does

Harness is a single Claude Code skill named `harness` that, when triggered by a domain sentence ("build a harness for fintech risk assessment"), produces a directory tree of agent definitions (`.claude/agents/*.md`), skill definitions (`.claude/skills/*/SKILL.md`), and one orchestrator skill that wires them together. It picks from six named team patterns: Pipeline, Fan-out/Fan-in, Expert Pool, Producer-Reviewer, Supervisor, Hierarchical Delegation. The meta-skill runs an 8-phase workflow (Phase 0 audit through Phase 7 evolution) and, on completion, registers a minimal pointer + change-history table in the project's CLAUDE.md.

**Wire format / runtime shape.** No wire format. The skill emits and consumes Markdown files on the local filesystem under `.claude/agents/`, `.claude/skills/`, and `_workspace/`. At runtime it depends on three Claude Code primitives gated by `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (`TeamCreate`, `SendMessage`, `TaskCreate`) and the GA `Agent` invoke. It does not define a protocol of its own.

## 3. Architecture

**Module layout** (`/tmp/gh-research/revfactory-harness/`):

```
.claude-plugin/
  plugin.json          # name, version 1.2.0, keywords, author
  marketplace.json     # marketplace registration ("./", self-hosted)
skills/harness/
  SKILL.md             # 443 lines, 7 phases, the entire factory
  references/
    agent-design-patterns.md     # 285 lines — 6 team patterns + decision tree
    orchestrator-template.md     # 292 lines — 3 templates (team / sub / hybrid)
    skill-writing-guide.md       # 268 lines — description + body authoring
    skill-testing-guide.md       # 307 lines — with-skill vs baseline eval
    qa-agent-guide.md            # 228 lines — boundary-mismatch catalogue
    team-examples.md             # 328 lines — research team, novel-writing team
docs/
  quickstart.md                  # 5-step install
  experimental-dependency.md     # SLA + 3 scenarios for the experimental flag
_workspace/                      # author's own GTM launch artifacts (off-mission)
```

**Plugin/extension surfaces.** One plugin entry, one skill, no commands, no hooks, no scripts, no agent files of its own. The `plugin.json` declares 17 keywords and zero entry points beyond Markdown.

**Dependency choices.** Zero runtime dependencies. The README pins itself to three Anthropic Engineering posts as "required reading before filing issues" (effective-harnesses-for-long-running-agents, harness-design-long-running-apps, scaling-managed-agents).

**Data flow.** Phase 0 audits existing `.claude/agents/`, `.claude/skills/`, and CLAUDE.md to detect drift. Phase 1-2 analyze the domain and pick a team pattern. Phase 3-4 emit agent + skill files. Phase 5 wires the orchestrator. Phase 6 runs structural + trigger validation. Phase 7 captures user feedback into the CLAUDE.md change-history table. Intermediate artifacts persist in `_workspace/{phase}_{agent}_{artifact}.md`. Reruns either re-execute partial agents or move `_workspace/` to `_workspace_{ts}/` and start fresh (skills/harness/references/orchestrator-template.md:37-46).

## 4. Engineering signals

| Signal | State | Citation |
|---|---|---|
| Type discipline | N/A — Markdown only | — |
| Tests | None | — |
| CI/CD | None. No `.github/workflows/`. | — |
| Code hygiene | High prose discipline. SKILL.md is 443 lines and de-duplicated against references (commit 54bc6d2 trimmed it from 330 to 285, then it grew back). No dead code, no shadow files. | `git log --oneline` |
| File sizes | All MDs under 700 lines except `_workspace/02_content_launch_contents.md` at 660 lines. The 660-line file is the author's own marketing copy, not source. | `wc -l` |
| Releases | Zero git tags despite v1.0.0 -> v1.2.1 in CHANGELOG. CHANGELOG [1.2.1] explicitly notes "tagged-release zero state remediation prep" as a planned item. | CHANGELOG.md:5-9 |
| Version drift | README badges, marketplace.json, and plugin.json desynced as recently as 2026-04-18 (v1.0.1 / 1.1.0 / 1.2.0 three-way). Now reconciled. | CHANGELOG.md:6-7 |
| Issue/PR triage | CONTRIBUTING.md commits to 72h PR first-response, 48h issue triage. Currently 1 open PR (8 days old as of 2026-04-27), 1 substantive open issue. | CONTRIBUTING.md |
| i18n discipline | Three READMEs maintained in lockstep (EN/KO/JA). High maintenance burden, no automation. | README.md, README_KO.md, README_JA.md |
| Commit cadence | 27 commits in 8 active days, one-author-dominant. Unsustainable cadence; likely launch-driven. | `git log --since=2026-03-01` |

## 5. What transfers to Helioy

### Primitive 1: Phase 0 audit + drift detection before any work

**Files.** `skills/harness/SKILL.md:18-35` (Phase 0 routing matrix), `skills/harness/SKILL.md:395-415` (Phase 7-5 ops/maintenance workflow).

**Description.** Before generating or modifying any agent/skill, the meta-skill reads `.claude/agents/`, `.claude/skills/`, and `CLAUDE.md`, then routes to one of three branches: new build, extension, or maintenance. Drift detection compares the orchestrator's declared agent/skill list against the actual filesystem and reports mismatches to the user before any write.

**Helioy target.** `helioy-plugins` (skill-creator) and `nancyr` (orchestrator entry point).

**Why it's load-bearing.** Helioy already has multiple skill creators and a growing `.claude/agents/` surface in `helioy-plugins`. Without a Phase 0-style audit, repeated invocations cause silent drift between the orchestrator's expectations and the filesystem. The routing matrix at SKILL.md:29-33 (extension type vs phases needed) is a transferable decision table for `skill-creator` to copy.

### Primitive 2: Boundary-mismatch QA catalogue

**Files.** `skills/harness/references/qa-agent-guide.md:17-40` (six boundary patterns), `qa-agent-guide.md:42-99` (cross-reading methodology), `qa-agent-guide.md:tail` (catalogue of 7 SatangSlide bugs).

**Description.** Six concrete classes of boundary mismatch (API response shape vs frontend hook generic, file path vs href, state-transition map vs actual updates, endpoint vs hook 1:1 mapping, sync vs async response shape, snake_case vs camelCase) each with a "left side / right side" table specifying which two files to read simultaneously. Grounded in seven shipped bugs from a real Next.js project.

**Helioy target.** `fmm` (cross-reference queries), `helioy-plugins` (a future `qa` or `boundary-check` skill).

**Why it's load-bearing.** `fmm` already does symbol-level navigation. The QA guide formalizes a class of cross-file invariants that fmm could expose as a first-class query: "for every `NextResponse.json()` site, find the matching `fetchJson<T>` site and diff the shapes." This is exactly the kind of structural check that benefits from fmm's index. The catalogue itself is reusable as test fixtures for an fmm-based linter.

### Primitive 3: Change-history table as CLAUDE.md surface contract

**Files.** `skills/harness/SKILL.md:246-265` (Phase 5-4 pointer registration), `SKILL.md:373-386` (Phase 7-3 evolution log).

**Description.** Instead of dumping agent/skill lists into CLAUDE.md (which causes duplication and rot), register only a trigger pointer plus a `| date | change | target | reason |` table. Every subsequent harness modification appends a row. This makes harness drift visible in the CLAUDE.md diff itself and prevents regressions by documenting why each change was made.

**Helioy target.** `cm` (a `cx_change` log kind, narrower than `decision`), and the convention layer for Helioy's CLAUDE.md files across components.

**Why it's load-bearing.** Helioy has 9 components (helioy-bus, nancyr, cm, am, fmm, mdm, helioy-plugins, attention-matters, context-matters) each with their own CLAUDE.md. Without an enforced change-history convention, architectural decisions get reabsorbed into the prose and lost. The table format is trivial to enforce and survives compaction. Strictly less invasive than commits-as-decisions, since it surfaces in every new session.

## 6. What does NOT transfer

- **Six "named" team patterns as a closed set.** Pipeline / Fan-out-in / Expert Pool / Producer-Reviewer / Supervisor / Hierarchical Delegation are useful as vocabulary but already covered by Helioy's broader orchestration model in nancyr. Skip the closed enumeration; prefer composable graph nodes.
- **Three-language README maintenance.** EN/KO/JA in lockstep is a heavy ongoing tax. Single-language with translations on demand is the right call for Helioy.
- **`_workspace/` checked into the repo.** The author committed their own GTM launch contents (`02_content_launch_contents.md` at 660 lines, `03_scout_outreach_map.md`, `04_strategist_launch_plan.md`) as eat-your-own-dogfood evidence. This is `.gitignore` material; do not adopt the pattern of committing harness execution artifacts.
- **Marketing PNGs in repo.** Four PNGs at 1.3-2.9 MB each (`harness_banner.png`, `harness_icon.png`, `harness_social.png`, `harness_team.png`). Use a CDN or `gh-pages` branch.
- **`landing-page-as-index.html`.** 100KB single-file HTML landing page lives at the repo root. Off-mission for a Claude Code plugin; helioy-plugins should not absorb this.
- **CLAUDE.md "evolution mechanism" branding.** The `/harness:evolve` skill is referenced but not implemented in this repo. Skip the marketing layer; the change-history table (Primitive 3) is the substance.
- **Korean-first prose.** SKILL.md is primarily Korean with embedded English. Helioy's documentation language is English; do not adopt the bilingual prose style.
- **Six pattern names as competing vocabulary.** nancyr already has its own orchestration vocabulary. Adopting harness's six-pattern naming would cause a vocabulary conflict in the Ubiquitous Language workstream.

## 7. Overlap with metaharness (SuperagenticAI)

revfactory/harness explicitly positions itself against SaehwanPark/meta-harness in the L3 Meta-Factory layer (README.md:35-45). Their differentiation: harness is a "Team-Architecture Factory" for Claude Code; metaharness is the "same concept, Codex runtime"; coleam00/Archon is the "Runtime-Configuration Factory." This framing is directly relevant to nancyr positioning. revfactory's L3/L2 layer table is a useful map; the underlying claim that all three projects coexist rather than compete is also load-bearing for how Helioy should describe nancyr.

## 8. Sources consulted

- README.md, README_KO.md (skim)
- skills/harness/SKILL.md (full)
- skills/harness/references/agent-design-patterns.md (head + decision tree)
- skills/harness/references/orchestrator-template.md (Templates A and headers)
- skills/harness/references/qa-agent-guide.md (head + tail with catalogue)
- skills/harness/references/skill-writing-guide.md (head)
- skills/harness/references/skill-testing-guide.md (head)
- skills/harness/references/team-examples.md (head)
- _workspace/01_auditor_repo_audit.md (the author's self-audit)
- docs/quickstart.md, docs/experimental-dependency.md
- CHANGELOG.md (full), .claude-plugin/plugin.json + marketplace.json
- `git log --all --oneline`, `git log --format="%an" | sort | uniq -c`
- `gh pr list`, `gh issue list`

## 9. Why

Harness is an honest piece of Claude Code skill engineering wrapped in heavy GTM packaging. The 443-line SKILL.md is denser per byte than most plugins, and the QA-agent guide is the single most reusable artifact. The six-pattern enumeration is mostly vocabulary; the real load-bearing primitives are the Phase 0 audit, the boundary-mismatch QA catalogue, and the CLAUDE.md change-history convention. Helioy can lift those three without inheriting the prose-only delivery, the marketing artifacts, or the closed pattern set.

## 10. How to apply

1. **Phase 0 audit in `helioy-plugins/skill-creator`.** Before any skill mutation, read `.claude/agents/`, `.claude/skills/`, and CLAUDE.md, then route to new/extend/maintain. Mirror the routing matrix at SKILL.md:29-33.
2. **Boundary-check skill grounded in `fmm`.** Encode the six boundary patterns from qa-agent-guide.md as fmm queries. Start with API-response-shape vs hook-generic; that single check covers three of the seven SatangSlide bugs.
3. **CLAUDE.md change-history convention across Helioy components.** Append a `| date | change | target | reason |` table to each component's CLAUDE.md. Treat it as a soft contract; do not enforce via hooks initially.
4. **Skip the rest.** Do not adopt the six-pattern closed set, the trilingual prose, the `_workspace/`-in-repo pattern, or the marketing PNGs.

## 11. Open questions

- Does revfactory's `/harness:evolve` actually exist as a skill, or is it README-only? Search of the repo did not surface a corresponding SKILL.md. Treat as aspirational until proven.
- The CLAUDE.md change-history table convention has not been validated under high commit volume. May need git-hook automation if Helioy components churn faster than the table can be hand-maintained.
- Does the boundary-mismatch catalogue generalize beyond Next.js? Six of seven listed bugs are Next.js-specific (NextResponse.json, app router groups, fetchJson<T>). The methodology generalizes; the patterns may need a Helioy-specific re-derivation.
