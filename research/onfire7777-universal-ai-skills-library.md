---
title: onfire7777/universal-ai-skills-library review for Helioy
type: research
tags: [github-review, universal-ai-skills-library, skills, router, helioy-plugins, mit]
summary: A 1,812-skill markdown corpus (45% auto-generated SaaS templates) fronted by a genuinely well-engineered deterministic Go preflight router. Corpus is skip; the routing-as-hook pattern is inspiration-only for runtime-catalog.
status: active
source: github-researcher
confidence: high
created: 2026-06-05
updated: 2026-06-05
---

# onfire7777/universal-ai-skills-library review for Helioy

Reviewed commit `4a91f6b` (cloned 2026-06-05). Repo URL: https://github.com/onfire7777/universal-ai-skills-library

## 1. Stats

Six stars, created 2026-03-25, last push 2026-06-04, so roughly ten weeks old and actively committed (30 commits, version 2.2.8). Single contributor (`onfire7777`); no external collaborators. CI is present and real (`.github/workflows/ci.yml`): Go tests, `go build` of the router, and PowerShell validation/audit scripts, but it runs `runs-on: windows-latest` only and the operational tooling (`infrastructure/`, `ai-setup/runtime/`) is almost entirely PowerShell/`.ps1`/`.vbs`, so the project is Windows-first. License is MIT (`LICENSE`, "Copyright (c) 2026 onfire7777"), which means content and code are both legally borrowable with attribution. 8,610 files, ~55 MB on disk.

## 2. Grade

**C+.** The headline "1,807 skills" is inflated: of 1,812 skill directories, 809 are byte-identical 91-line `*-automation` templates (`diff` of `accelo-automation` vs `abstract-automation` after token substitution is empty) wrapping Composio/Rube MCP, one per SaaS toolkit. That is auto-generated padding, not authored content. The handcrafted core skills (18 of them) are competent but ordinary prompt-library entries on par with what Helioy already ships (e.g. `chat-summarizer` ≈ Helioy's `session-handover`, and it even hardcodes `/home/ubuntu/chat_summary.md`, a sign of unreviewed sandbox generation). What lifts this above the NeoLabHQ/context-engineering-kit C+ ("a long-form prompt library presented as engineering") is one thing: the `skill-router-cli` is real, tested Go engineering, not prose. So it sits at the top of the C band, below graphify (B), because the surrounding corpus is the usual aggregation and the engineering is narrow.

## 3. What it actually is

Directory layout: `skills/` (1,812 dirs, each with a `SKILL.md`), `skill-router-cli/` (Go CLI, the core), `manifest.json` (747 KB machine catalog), `plugin/` + `plugin-codex/` (host adapters), `ai-setup/runtime/` (PowerShell supervisor + Python router/proxy), `infrastructure/` (PowerShell MCP bridges/watchdog), `install.sh` / `install.ps1`, `marketplace.json`.

Skill format: each skill is a single `SKILL.md` with YAML frontmatter `name` + `description` (and optionally `requires.mcp: [...]`). No category taxonomy in the tree itself; categorization lives in `manifest.json` as a flat catalog split into `core_skills` (18) and `library_skills` (1794), each entry carrying `name`, `directory`, `description`, optional `aliases` (display-name strings), `has_scripts`, `scripts[]`. Canonical id = kebab-case directory name; aliases are legacy display names only.

It is NOT pure markdown. There is a real runtime: the Go `skill-router` binary plus a hook contract. `plugin/universal-agent-instructions.md` is the load-bearing doc: on every substantive user prompt the host runs `skill-router preflight --hook-event UserPromptSubmit --json "<prompt>"`, and if the decision is `route`, loads exactly one skill via `skill-router skill <name>`. The corpus is never preloaded; only a single thin wrapper skill (`DefaultWrapperSkills = ["universal-ai-skills"]`, `skill-router-cli/internal/skillsync/skillsync.go:17`) is propagated to each agent root, and the router reads the corpus in place.

## 4. Primitives that transfer

1. **Deterministic preflight router with evidence gates and three-way decision.** `skill-router-cli/cmd/skills/route_preflight.go:47` (`buildRoutePreflight`) scores every catalog entry lexically, then returns `route` / `no_route` / `ambiguous`. The scoring is in `route_scorer.go` (`scoreRouteFields`, `evidenceScore`): name/alias/description strong-vs-weak token hits, exact-name/alias/source flags, generic-single-token-name suppression (`isGenericSingleTokenName`, `route_scorer.go:181`), and uninstall-intent gating. **Landing target: runtime-catalog / the future skill dispatcher.** Helioy currently leans on Claude Code's native description-based skill activation; a cheap deterministic prescorer that runs before model attention could cut wrong-skill activations as the helioy-tools skill count grows.
2. **Margin-based ambiguity detection that escalates to the host AI instead of guessing.** `route_scorer.go:199` (`isAmbiguousRoute`: `best.score - second.score < automaticRouteMinMargin` = 18) plus `buildHostAIReview` (`route_preflight.go:134`), which emits a structured `host_ai_review` block listing the top-5 candidates with the instruction "load one only if the user intent clearly matches; otherwise continue normally." This "deterministic-when-confident, defer-to-model-when-close" handoff is the genuinely good idea. **Landing target: helioy-tools skill-router design notes / linear-workflows gating philosophy.**
3. **Wrapper-only propagation (one pointer skill, corpus read in place).** `skillsync.go:15-57`: only `universal-ai-skills` is copied into agent roots; `fullCopy` is opt-in. This is the inverse of duplicating a corpus into every install. **Landing target: the Helioy multi-target installer** as a confirming reference for "ship a pointer, not the payload" if the helioy-tools skill set ever grows past what is comfortable to copy per host.
4. **Quiet, hook-event-scoped routing contract.** `plugin/universal-agent-instructions.md` + `isUserPromptHookEvent` (`route_preflight.go:284`) restrict auto-routing to real `UserPromptSubmit` events and explicitly forbid routing from tool output, assistant messages, startup, stop, or compaction. **Landing target: any future Helioy UserPromptSubmit hook** that auto-suggests skills; the "never fire on non-user events" rule is a cheap correctness guard worth copying verbatim.

## 5. Does NOT transfer

1. **The skill corpus itself.** 809 of 1,812 are identical Composio/Rube MCP templates; the rest are generic prompt-library entries that do not beat helioy-tools (cm/am/fmm, blog-architect, social-loop, my-voice) or the superpowers framework. No category of skill here is one Helioy lacks and wants.
2. **Windows-first runtime.** `infrastructure/` and `ai-setup/runtime/scripts/` are PowerShell/`.vbs`; CI is `windows-latest`. Helioy is macOS/Linux. Porting cost exceeds value.
3. **Composio/Rube MCP coupling.** The automation skills assume a `rube` MCP server and Composio toolkits. Helioy's MCP surface (cm/am/fmm/linear/supabase) is different and self-owned.
4. **The PowerShell/Python "Universal AI Stack" supervisor + local Qwen proxy** (`ai-setup/runtime/bin/`). Parallel to Helioy's own runtime ambitions and Windows-bound.

## 6. Verdict

**Inspiration-only.** Skip the corpus and runtime entirely; study the `route_preflight.go` / `route_scorer.go` design as a reference for a deterministic skill prescorer with host-AI escalation if helioy-tools ever needs one.

## 7. Why

Helioy's bar is high and this clears it in exactly one place. A skills library is content, and this one's content is mostly machine-stamped SaaS wrappers padding a star-bait count; the "1,807 skills" framing is marketing, not substance. But the author solved a real second-order problem: when you have a thousand skills, native description-matching degrades, so they built a deterministic lexical preflight that is confident when evidence is strong and explicitly hands the decision back to the model when it is not. That confident/defer split, with structured candidate lists and evidence gates, is the transferable insight. It is the same retrieval-discipline lesson Helioy already internalized for cm recall (boost dominance, narrow pool), applied to skill activation.

## 8. How to apply

- Do not import any skills. The corpus adds nothing over helioy-tools + superpowers.
- If/when helioy-tools skill count makes native activation unreliable, prototype a deterministic prescorer modeled on `route_scorer.go` (strong/weak token hits, exact-name boost, generic-name suppression, margin-based ambiguity) and wire it through a `UserPromptSubmit` hook that suggests at most one skill and otherwise stays silent. Borrow the `host_ai_review` escalation shape verbatim.
- Capture the "ship a pointer skill, read corpus in place" pattern (`skillsync.go:17`) as a note for the multi-target installer; it is a cleaner mental model than copying skills per host.
- No PR, no borrow of MIT content. This is a design-pressure read, nothing more.

## Sources consulted

- `README.md`, `manifest.json` (version, core/library split, alias schema)
- `skill-router-cli/cmd/skills/route_preflight.go`, `route_scorer.go` (routing core)
- `skill-router-cli/internal/skillsync/skillsync.go` (propagation model)
- `plugin/universal-agent-instructions.md` (hook contract)
- `skills/accelo-automation/SKILL.md`, `skills/abstract-automation/SKILL.md` (template confirmation), `skills/chat-summarizer/SKILL.md` (core skill quality)
- `.github/workflows/ci.yml`, `LICENSE`, `git log`

## Open questions

- Router recall quality is untested here: lexical scoring will miss paraphrase intent that a model would catch. Whether the confident/defer split actually beats native activation in practice would need a head-to-head eval before Helioy commits engineering to a prescorer.
