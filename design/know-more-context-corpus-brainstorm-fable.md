---
title: KnowMoreContext corpus, evals and X strategy (Fable brainstorm)
type: design
tags: [transport-matters, corpus, system-prompts, evals, x-strategy, knowmorecontext, issue-683]
summary: Brainstorm for publishing the certification prompt corpus as a public diff, the eval programme on top of it, the #683 proposal, and the X plan for 500 followers and 500K impressions in 90 days
status: draft
confidence: medium
project: transport-matters
related: [transport-matters-north-star]
---

# KnowMoreContext: corpus, evals, X strategy

Independent brainstorm, one of two. Written against the live preview bundle directory (`~/.transport-matters-preview/baselines/bundles`, 176 bundles, artifact schema 13, 26 harness versions) and issue #683. Numbers below were measured this session unless marked as issue data.

## 0. The one correction to the framing

Issue #683 publishes the **system prompt**. The system prompt is the smallest of the three things a harness sends before the user's first word.

Measured, first-turn request, claude 2.1.270 opus, `json.dumps` length:

| component | chars | share |
| --- | --- | --- |
| tool schemas (31 tools) | 140,037 | 84% |
| top-level `system` | 9,383 | 6% |
| `role: system` message + reminders + user turn | ~16,000 | 10% |
| **whole request** | **165,759** | |

The `Artifact` tool schema alone is 27,490 chars. `Workflow` is 21,870. Those two tools outweigh the entire system prompt three to one. Tool schema bytes for opus moved 134,557 (2.1.246) to 119,569 (2.1.250) to 140,037 (2.1.270): a 15K drop and a 20K climb inside seven weeks that nobody published.

The other harnesses, same measure, latest version:

| harness / model | tools | tool chars | instructions chars | whole request |
| --- | --- | --- | --- | --- |
| claude 2.1.270 haiku | 35 | 166,096 | 27,431 | 210,434 |
| claude 2.1.270 sonnet | 31 | 158,848 | 27,329 | 202,950 |
| codex 0.154.0 gpt-5.5 | 14 | 17,177 | 21,299 | 42,307 |
| codex 0.153.4 gpt-5.6-sol | 0 on wire | 0 | 54K in developer items | 56,519 |
| grok 1.0.30 grok-4.6 | 28 | 44,404 | 6,197 | 53,476 |

Claude Code sends four to five times the bytes Codex or Grok send for the identical prompt. That sentence is the whole brand. So:

**The corpus has three layers, not one.** `system` (the text), `tools` (the schemas, per tool, diffable per tool), and `envelope` (headers, betas, `thinking`, `output_config`, `context_management`). The issue's generator already reads the raw request. Emitting three projections instead of one is a loop, not a redesign, and the tool layer is the one that produces the numbers people repost.

One open question from the data, unresolved in a line: codex 0.154.0 gpt-5.6 first-turn probes total 2,203 to 3,714 chars with no instructions on the wire, versus 56K at 0.153.4. Either the capture caught a chained turn or 0.154.0 moved the instructions server side. Either way it is a post, and the generator must surface it rather than silently publish an empty cell.

## 1. Stack fit

The property has to host three things with different physics:

- **The corpus**: thousands of static pages, generated, SEO is the product. `claude code system prompt` and `codex system prompt` are the queries to own. Must be crawlable cold with no JS.
- **The eval explorer**: tables, charts, per-run drill-in. Static data, interactive rendering.
- **The run journey canvas**: infinite canvas of requests and transcripts for one eval run. Heavy client, large JSON per run, never needs SSR.

### Options

**A. Astro static on GitHub Pages** (the issue). Zero cost, zero ops, islands for interactivity. GH Pages limits: 1 GB site, 100 GB/month soft bandwidth, no headers control, no redirects beyond meta refresh, no edge functions, builds via Actions only. Astro generates ~200 to 2,000 pages in under a minute. Canvas can be an island. OG images at build time via `astro-og-canvas` or satori. Weakness: no per-request logic, so any future "what is in my prompt right now" API has to be a static JSON tree, and a 5,000-page corpus with per-pair diff pages and OG PNGs will sit around 300 to 800 MB of build output within a year.

**B. Next.js on Vercel**. SSR/ISR, edge OG images (`@vercel/og`), API routes, first-class React for the canvas. Cost: free tier caps at 100 GB bandwidth then $20/seat plus overage; a viral post can cost real money. SEO is fine but ISR pages that were never rendered are not in the crawl until hit. Lock-in is moderate. It buys nothing the corpus needs and adds an ops surface.

**C. Hybrid: static corpus plus a separate app.** Astro (or plain generator) for `/prompts/**`, a Vite React SPA for `/evals/**` and `/runs/**`, both behind one domain on Cloudflare Pages. Each half is deployed by its own CI. The corpus stays crawlable and cheap; the app stays free to use tldraw or React Flow with a 5 MB run JSON. Costs the seam: two build systems, two designs to keep in the same skin.

**D. Astro on Cloudflare Pages** (A with a different host). Same static output, unlimited bandwidth on the free plan, 20,000 files per deploy, 25 MB per file, `_headers` and `_redirects` files, Workers available later for an API without moving. Custom domain and OG images unchanged. Build time via Actions or Cloudflare's own builder.

**E. Observable Framework / Quarto**: data-app generators. Good charts for free, weak page routing and OG story, wrong shape for a corpus with thousands of leaf pages.

### Weighing

| criterion | A GH Pages | B Next/Vercel | C Hybrid | D Astro/CF |
| --- | --- | --- | --- | --- |
| SEO for `claude code system prompt` | full static, best | good | best for corpus | full static, best |
| cold crawlability | yes | ISR gaps | yes | yes |
| cost at viral scale | free, soft caps | can bill | free | free, no bandwidth cap |
| OG per page | build time (satori) | edge | build time | build time, or Worker later |
| embeddability (iframes, badges) | fine | fine | fine | fine, plus `_headers` for CORS on JSON |
| canvas in same property | island, ok | native | separate app, best | island, ok |
| future API (`/api/prompt/claude/opus/latest`) | static JSON only | yes | static JSON | static JSON now, Worker later |
| ops | none | some | two pipelines | none |

### Recommendation

**D: Astro, static output, on Cloudflare Pages, one repo, one domain.** Keep the issue's Astro choice, drop GitHub Pages. Reasons: the JSON surface wants CORS headers and `Cache-Control` you can set in `_headers`, the 20,000 file limit is generous, the bandwidth is uncapped, and a Worker can front the same static tree the day someone wants an MCP endpoint or a redirect from `/latest`. Everything else is identical to A, so the issue's acceptance criteria stand unchanged. Fallback to GH Pages costs nothing if Cloudflare is an unwanted dependency.

The canvas lives in the same property as an Astro island (`client:only="react"`) under `/runs/<run-id>` loading `/runs/<run-id>/graph.json`. That is enough until run JSON exceeds a few MB, at which point the run pages become a lazy-loaded chunked format, still static. React Flow for the graph, tldraw only if free-form annotation is wanted. Do not build C's second app until the canvas needs shared state, comments or auth.

**What would change the recommendation:**
- Per-viewer state (saved comparisons, watchlists, "my harness version") pushes to B or to D plus a Worker with KV. Likely in month four, not month one.
- If eval runs are to be launched from the site (not just viewed), that is TM's own backend and lives elsewhere; the site links to it.
- If build output passes ~15,000 files, shard: `/prompts` and `/evals` become two Cloudflare Pages projects behind one domain via `_redirects` or a Worker router. That is C by evolution, which is the right way to reach C.

Domain: `knowmorecontext.com`, with `kmc.sh` or similar as the short link for post copy if available. Uncertain whether the .com is free; check before naming anything.

## 2. Eval ideas

Design rule for every eval: the artifact must be one image or one number that stands alone in a timeline. Every eval below produces (a) a JSON row in the corpus, (b) a static page, (c) an OG image.

Token unit: characters everywhere in the corpus, with an explicit `chars / 4 ≈ tokens` note, until a tokenizer lands. For evals that run live, use the provider's own `usage` from the captured response so the token counts are real and attributable to the exact request.

### 2.1 The Overhead Tax
- **Question**: How many tokens does the harness spend before you have said anything?
- **Setup**: Already captured. First-turn request per (harness, version, model). Split into system, tools, reminders, user.
- **Metric**: bytes and `usage.input_tokens` per layer; overhead share.
- **Artifact**: A stacked bar per harness, "your first 'hi' costs N tokens". Plus a seven-week line per harness.
- **Why repost**: Everybody paying $200/month has never seen the number. Claude Code 165K chars vs Codex 42K vs Grok 53K on one chart is an argument starter.

### 2.2 Tool-turn tax by model
- **Question**: Which harness resends the whole context on every tool call, and what does that cost over a 40-tool session?
- **Setup**: Already captured (tool-turn shape). Multiply per-turn bytes by turn counts from real sessions (TM roster has turns and exchanges per run).
- **Metric**: cumulative bytes over N tool turns; cache hit share from `usage.cache_read_input_tokens`.
- **Artifact**: Two curves: codex gpt-5.6 (`previous_response_id`, near flat) vs claude (linear). Title: "The same 40 tool calls".
- **Why repost**: Real money, per model, and it contradicts the assumption that harness choice is the cost driver.

### 2.3 Effort ROI ladder
- **Question**: Does xhigh beat high, and at what token multiple?
- **Setup**: Fixed task set (10 tasks: bug fix with failing test, refactor with test suite, add endpoint, write migration, explain code). Run each at low/medium/high/xhigh, three seeds, per harness and model.
- **Metric**: pass rate, `usage` output tokens, wall clock. ROI = pass rate delta per token multiple.
- **Artifact**: Ladder chart per model: x is token multiple over low, y is pass rate. One line per model.
- **Why repost**: "xhigh costs 3.4x and gains 2 points" or the opposite. Either result is a post.

### 2.4 System prompt overhead vs useful work
- **Question**: Across a full task, what share of input tokens was harness scaffolding?
- **Setup**: Same task set. Every request captured. Classify every byte of every request as system, tools, reminders, prior turns, tool results, user text.
- **Metric**: per-run pie; per-harness median.
- **Artifact**: One donut per harness. "72% of what you paid for was the harness talking to itself."
- **Why repost**: It reframes the bill.

### 2.5 Instruction drift across versions
- **Question**: When the system prompt changed, did behaviour change?
- **Setup**: Pin the same model, run the same 10 tasks on version N and N+1 where the corpus shows a prompt diff. TM pins harness binaries per run.
- **Metric**: pass rate, tool call count, tokens. Correlate with the diff.
- **Artifact**: Diff on the left, behaviour delta on the right. "2.1.269 removed 2,442 chars. Here is what changed in practice."
- **Why repost**: The corpus makes the "why" visible; nobody else can show cause and effect.

### 2.6 Self-contradiction audit
- **Question**: Does the prompt tell the model two incompatible things?
- **Setup**: Static. An LLM judge reads each canonical prompt with a rubric: find pairs of instructions that conflict, quote both. Human verifies before publishing.
- **Metric**: count of verified contradictions per (harness, version).
- **Artifact**: A page per contradiction with the two quotes side by side. A trend line of contradictions per version.
- **Why repost**: Screenshot bait, and vendor engineers will read it. Keep the tone as a bug report, not a gotcha.

### 2.7 Multi-agent coordination overhead
- **Question**: Orchestrator spawns three agents for a fixed workflow. What share of spend is coordination?
- **Setup**: TM orchestrator with a fixed prompt, three specialists, fixed task (split a module, write tests, review). Capture every request of every agent (TM already counts subagent tracks per run).
- **Metric**: tokens by node; coordination share = orchestrator tokens plus the briefing bytes each child received that did not come from the task.
- **Artifact**: The infinite canvas of the run, with a cost heat overlay per node. Plus a single number.
- **Why repost**: This is the NORTHSTAR cost thesis measured. "Coordination cost 31% of the run" is a headline for every agent-team vendor.

### 2.8 Prompt cache economics
- **Question**: How much does the harness's cache breakpoint placement save, and how does a system prompt change invalidate it?
- **Setup**: Captured `cache_control` positions in claude requests, `prompt_cache_key` in codex and grok. Run a 30-turn session; read `cache_read_input_tokens` and `cache_creation_input_tokens` per turn.
- **Metric**: cache hit share per turn; cost with and without cache at list price (pulled from vendor pricing pages at build time, never hardcoded).
- **Artifact**: A waterfall per session. "The day 2.1.269 shipped, everyone's cache went cold once. That cost X per user."
- **Why repost**: Explains a bill spike people saw but could not attribute.

### 2.9 Same task, three harnesses, one model family each
- **Question**: Cheapest harness for a fixed task at parity effort.
- **Setup**: 10 tasks, claude opus vs codex gpt-5.5 vs grok-4.6, medium effort.
- **Metric**: total tokens, tool calls, wall clock, pass.
- **Artifact**: A leaderboard, weekly.
- **Why repost**: Leaderboards get reposted by whoever is winning.

### 2.10 Tool schema bloat vs tool use
- **Question**: Of 31 tools declared on every request, how many are ever called?
- **Setup**: Run the task set; count `tool_use` by name across all runs.
- **Metric**: schema bytes per call; tools never called.
- **Artifact**: Bar chart, tools sorted by schema size, coloured by whether they were ever invoked. `Artifact` at 27K chars is the obvious bar.
- **Why repost**: "You pay 27K chars per request for a tool called in 0 of 300 runs."

### 2.11 Reminder injection census
- **Question**: What `<system-reminder>` blocks does claude inject, when, and how many bytes over a session?
- **Setup**: Captured. Parse reminders out of user turns per request.
- **Metric**: reminder kinds, bytes per turn, growth over session.
- **Artifact**: Timeline of reminders arriving per turn.
- **Why repost**: Users see "the model ignored my instruction" and never see the 14 reminders between them.

### 2.12 The `role: system` message
- **Question**: What is in the second system message claude sends (13.8 to 14.2K chars), and how does it differ from the top-level one? Out of scope in #683, in scope here.
- **Setup**: Captured.
- **Artifact**: A page, plus a diff timeline of its own.
- **Why repost**: It is the part nobody knows exists.

### 2.13 Effort knob reality check
- **Question**: What does `effort: low` actually change on the wire?
- **Setup**: Captured across efforts. Diff the requests.
- **Metric**: the field-level delta (claude: `output_config.effort`, `thinking.type`; codex: `reasoning.effort`).
- **Artifact**: A tiny diff per harness. "Effort is one field. Here it is."
- **Why repost**: Demystifies a setting people argue about.

### 2.14 Compaction cost
- **Question**: What does context compaction cost, and what survives it?
- **Setup**: Drive a session past the compaction threshold under capture. Diff the request before and after.
- **Metric**: bytes removed, bytes of summary, tokens spent producing the summary.
- **Artifact**: Before/after request skeleton.
- **Why repost**: "Compaction cost 9K output tokens and dropped your CLAUDE.md" if that is what it shows.

### 2.15 Instruction following on planted rules
- **Question**: Does the harness's own system prompt get obeyed, and does obedience decay by version?
- **Setup**: Pick five testable rules from the prompt itself (for example, "reference code as file:line", "no closing offer"). Score outputs across versions.
- **Metric**: obedience rate per rule per version.
- **Artifact**: Heatmap rules x versions.
- **Why repost**: Uses the vendor's own words as the rubric. Unarguable.

### 2.16 CLAUDE.md / AGENTS.md dilution
- **Question**: At what harness prompt size does the user's own instruction file stop mattering?
- **Setup**: Same planted-rule task with a user instruction file, run under each harness whose scaffolding varies 42K to 210K chars.
- **Metric**: obedience to the user rule vs scaffolding bytes.
- **Artifact**: Scatter.
- **Why repost**: Direct advice: "your AGENTS.md is 1.2% of the request".

### 2.17 Model swap under one harness
- **Question**: Same harness version, same task, opus vs sonnet vs haiku: does the 18K longer sonnet/haiku prompt buy anything?
- **Setup**: Captured prompt plus live runs.
- **Artifact**: The extra 18K chars, annotated, next to the pass rates.

### 2.18 Version release cadence and churn index
- **Question**: How often does each vendor change the prompt, and how big is a typical change?
- **Setup**: Static from corpus.
- **Metric**: changes per month, mean chars changed, longest stable streak.
- **Artifact**: A "prompt churn index" per harness, monthly. Becomes a recurring franchise.

### 2.19 Latency to first token vs request size
- **Question**: Does the 200K-char request cost time as well as money?
- **Setup**: TM captures timings per exchange. Correlate first-byte latency with request bytes, controlling for model.
- **Artifact**: Scatter with a fitted line.

### 2.20 Harness A running model B's system prompt
- **Question**: Is the Claude Code prompt better than the Codex prompt, for the same model, on the same task?
- **Setup**: TM overrides (`system_part_text`) can swap the prompt body under capture. Run codex tasks under claude with the codex instructions, and vice versa, model held fixed.
- **Metric**: pass rate, tokens.
- **Artifact**: A 2x2.
- **Why repost**: It is the only place this experiment can be run. Label it clearly as an experiment against ToS grey areas (see risks).

### 2.21 "What did 2.1.x cost you this month" calculator
- Not an eval, a tool built on evals: input your turns per day and model, output overhead spend at each version. Shareable result card.

## 3. Proposal for #683

### 3.1 What to challenge in the issue

1. **System prompt only.** Publish system, tools and envelope. Same reader, three projections. The tool layer carries 84% of the bytes and the most surprising diffs (a 15K drop at 2.1.250, a 20K climb by 2.1.270). Not publishing it leaves the headline on the floor.
2. **Page per (harness, model).** Keep it, but the primary unit for SEO and for X is the **change**, not the model. Add a page per consecutive-version pair per model (`/prompts/claude/opus/2.1.261..2.1.269`) and a page per harness version (`/prompts/claude/2.1.269`, "what changed in this release across all models"). The pair page is the thing linked from a post.
3. **GitHub Pages.** Cloudflare Pages, per section 1. Keep Astro.
4. **Character count as the unit.** Correct for the diff. For the overhead story, add the provider's own `usage.input_tokens` from the captured response where TM has it, labelled as measured, and `chars/4` elsewhere labelled as estimate. Do not ship a tokenizer yet.
5. **`role: system` excluded.** Include as its own layer (`system-message`). It is the same extractor with one more selector.
6. **Sanitization as a non-contract.** Agree there is nothing secret. Still ship a `redaction-report.json` per publish (patterns scanned, match counts, all zero) because it is the first thing a sceptic asks and it is free to produce.
7. **Variants as side-by-side.** Yes, but declare the *cause* where known. The 2.1.250 `best` variant carries `<total_tokens>15000000 tokens left</total_tokens>`: that is a quota-driven injection, which is itself a finding ("Claude Code tells the model your remaining quota"). Variants get a `cause` field: `quota_injection`, `effort`, `context_window`, `unknown`.

### 3.2 Repository

Name: `littleorgans/know-more-context` (public). The main TM repo gains only a generator entry point and a test.

```
know-more-context/
  README.md
  LICENSE-DATA              CC BY 4.0 for corpus data
  LICENSE                   MIT for code
  corpus/                   committed, generated, git-diffable
    schema-version.txt
    index.json              every cell, sizes, hashes, variant counts
    claude/
      opus/
        2.1.246/
          system.md         canonical, normalized
          system.raw.md     one representative capture, unnormalized (paths still there)
          system-message.md the role:system message
          tools/
            _index.json     name, sha, chars, order
            Bash.json
            Artifact.json
            ...
          envelope.json     header names, betas, thinking, output_config, cache_control positions
          cell.json         version, model, effort(s), capture dates, bundle ids, variant list
          variants/
            v1/system.md    only when the cell has >1 canonical text
            v1/cause.json
        2.1.247/
        ...
        timeline.json       consecutive pairs with line and char deltas per layer
      sonnet/ ...
    codex/gpt-5.5/ ...
    grok/grok-4.6/ ...
  diffs/                    committed, generated: unified diffs per pair per layer
    claude/opus/2.1.261..2.1.269/system.diff
    claude/opus/2.1.261..2.1.269/tools/Artifact.diff
  site/                     Astro
    src/pages/...
    src/components/Diff.astro, Timeline.astro, Variants.astro, RunCanvas.tsx
    public/_headers         CORS on /corpus/** and /api/**
  generator/                python, reads a bundle dir, writes corpus/ and diffs/
    extract.py              per-harness selectors (system, instructions, developer items, tools)
    normalize.py            the eight rules plus per-tool sorting
    diff.py                 pairs, variants, relocation aware
    og.py                   OG PNG per page (or do it in Astro via satori)
    validate.py             CI: byte-identical regen, every cell resolves, sizes match index
  .github/workflows/
    validate.yml            on PR: regen from committed raw, assert identical, run tests
    publish.yml             on main: astro build, deploy Cloudflare Pages
    announce.yml            on new pair: render card, open a draft post (section 4.6)
```

Bundles never leave the local machine. The generator runs locally (`tm corpus export --bundles ~/.transport-matters-preview/baselines/bundles --out ../know-more-context/corpus`) and the resulting commit is the PR. CI has no provider credentials and no bundles; it validates that `corpus/` is internally consistent and that `diffs/` regenerate byte-identically from `corpus/`.

### 3.3 Generator design

Input: bundle JSON, `probes[].raw_request_base64`. Per probe:

1. **Extract** by profile. anthropic-messages: top-level `system[]` (concatenate text blocks with a `\n\n---\n\n` separator and keep block boundaries in `cell.json`), `messages[0]` `role: system` if present, `tools[]`, and the envelope fields. codex: `instructions` if present, else `input[]` items with `role: developer`; `tools[]`. grok: `input[]` `role: system`; `tools[]`.
2. **Normalize** with the eight rules. Add two: sort `tools[]` by name for the per-tool diff (record original order in `_index.json`), and strip `cache_control` markers from the text projection (they go to `envelope.json`).
3. **Canonicalize** per cell: group probes by normalized sha. One group is the canonical prompt. More than one is variants, ordered by first capture date, with a `cause` heuristic (regex for `<total_tokens>` sets `quota_injection`; effort differing sets `effort`; otherwise `unknown`).
4. **Timeline** per (harness, model): sort versions with a semver comparator, emit consecutive pairs with `lines_changed`, `chars_delta`, `tools_added`, `tools_removed`, `tools_changed`, `envelope_changed`.
5. **Diff** per pair per layer with `difflib.unified_diff`, three lines of context, and a relocation pass reusing TM's comparator idea (a removed hunk reappearing verbatim elsewhere is one `moved` hunk).
6. **Index** everything into `corpus/index.json` and per-model `timeline.json`.
7. **Validate**: rerun on the same input, assert byte-identical output (the issue's acceptance test), assert every cell has exactly one canonical or a declared variant set, assert the 2.1.261 to 2.1.269 opus pair reads 45 lines and -2,442 chars.

Tests: normalizer maps two captures of one cell to one text; codex 0.154.0 gpt-5.6 empty instructions raises a `MissingInstructions` finding rather than emitting an empty cell; semver ordering handles `2.1.250` after `2.1.247`.

### 3.4 URL scheme

```
/                                       homepage
/prompts                                corpus index
/prompts/claude                         harness page: versions, models, churn index
/prompts/claude/opus                    model page: timeline, latest prompt, variants
/prompts/claude/opus/2.1.270            cell page: system, tools, envelope tabs
/prompts/claude/opus/2.1.261..2.1.269   pair page: the diff, per layer
/prompts/claude/2.1.269                 release page: what changed across all models
/prompts/claude/opus/latest             redirect to newest cell (via _redirects)
/tools/claude/Artifact                  tool page: schema timeline across versions
/compare?a=claude/opus/2.1.270&b=codex/gpt-5.5/0.154.0   cross-harness diff, client side
/evals                                  eval index
/evals/overhead-tax                     one eval, latest run, history
/runs/<run-id>                          run journey canvas
/changes                                the feed: every new pair, newest first (also RSS)
/changes/2026-09-14                     daily digest page
/corpus/**                              raw files, served as-is, CORS on
/api/v1/prompt/claude/opus/latest.json  static JSON, same as corpus but stable shape
/badge/claude/opus.svg                  embeddable badge: version, chars, last change
```

Slugs match the launch model string TM uses (`opus`, `sonnet[1m]` becomes `sonnet-1m`). Harness versions are verbatim.

### 3.5 Page shapes

**Cell page** (`/prompts/claude/opus/2.1.270`): header with harness, model, version, capture date, char counts per layer, "changed since previous: +0 chars system, +0 tools, 1 envelope field". Tabs: System (rendered markdown with a "raw" toggle and line numbers, anchors per heading so a post can link `#memory`), Tools (table: name, chars, changed-since-previous badge; expand to schema), Envelope (key/value), Variants (side by side, cause). Right rail: version scrubber. Footer: bundle ids and TM commit as provenance, "download cell.json".

**Pair page** (`/prompts/claude/opus/2.1.261..2.1.269`): summary line, then the unified diff per layer, hunks collapsible, moved hunks marked, each hunk with a permalink and a "copy as image" button that renders the hunk as PNG client side (html-to-image) for posting. Below: "what this means" free text, written by hand for notable pairs and blank otherwise. OG image is the summary line plus the largest hunk.

**Model page**: sparkline of chars per version, table of pairs with deltas, latest prompt below the fold.

**Release page**: one row per model, deltas, and the union of hunks.

**Homepage**: three numbers big at the top ("Claude Code 2.1.270 opus sends 165,759 chars before your first word. Codex 0.154.0 gpt-5.5: 42,307. Grok 1.0.30: 53,476."), then the change feed, then the harness cards, then "what is this" in two paragraphs, then the newsletter box.

**Variants**: two columns, shared lines collapsed, differences highlighted, `cause` badge at the top. Three or more variants become a tab strip.

### 3.6 Raw data surface

- `corpus/**` served verbatim with CORS. Markdown for prompts, JSON for schemas, so `curl` and `git diff` both work.
- `/api/v1/**` is a stable-shape JSON mirror: `latest.json`, `versions.json`, `pair.json`. Version the shape in the path.
- `/changes.rss` and `/changes.json` (JSON Feed).
- One `corpus.tar.zst` per release tag on GitHub Releases for offline use.
- Everything CC BY 4.0 with an attribution line that names knowmorecontext.com.

### 3.7 CI

- `validate.yml` on PR: regenerate `diffs/` from `corpus/`, `git diff --exit-code`; run generator tests against a small fixture bundle set committed under `generator/fixtures` (three cells, one variant, one pair) so the pipeline is exercised without real bundles.
- `publish.yml` on main: `astro build`, OG render, deploy. Under three minutes.
- `announce.yml` on main when `corpus/index.json` gained a pair: render the pair card PNG, write `post.txt` from a template, open a GitHub issue titled `post: claude opus 2.1.269..2.1.270` with the card attached. A human posts it (X API posting from CI is possible on Basic at $100/month, but hand-posting keeps tone and timing; revisit at week six).

### 3.8 v1 vs later

**v1 (two weeks):** generator with three layers, corpus committed, cell/pair/model/harness/release pages, change feed with RSS, OG images, raw surface, validate and publish CI, homepage with the three numbers. No evals, no canvas, no compare.

**v1.1:** tool pages, `/compare`, badges, `latest` redirects, copy-as-image on hunks, `announce.yml`.

**v2:** evals section fed by TM eval runs (static JSON export), leaderboards, the churn index.

**v3:** run journey canvas.

**Later:** MCP server, CLI, VS Code extension, Worker API.

## 4. X strategy: 500 followers and 500K impressions in 90 days

### 4.1 The arithmetic

500K impressions in 90 days is 5,556 per day. A new account's ordinary post earns 300 to 2,000 impressions. The target is not reached by cadence; it is reached by a handful of posts that clear 50K to 150K each, on a base of daily posts that keep the algorithm warm. Plan for: 90 daily posts at a median 1,500 (135K), 12 weekly franchise posts at 8K (96K), and four to six spikes at 50K plus (250K+). That is the shape. Every spike candidate must be a **number with a receipt** and an image that reads in the timeline without opening it.

Verified followers only count. That skews to developers already paying for Premium, which is the target audience anyway.

### 4.2 Formats that work for this corpus

1. **The receipt**: a screenshot of a hunk from the actual diff, one sentence above it. Auto-generated from the pair page.
2. **The number card**: three harnesses, one number each, one sentence. Auto-generated from `index.json`.
3. **The before/after**: two prompt excerpts side by side, one line highlighted.
4. **The chart**: one line per harness over versions. Auto-generated.
5. **The thread of receipts** (used sparingly, first post of the thread must stand alone since replies do not count).
6. **The quote**: a verbatim instruction from a system prompt, in a typographic card, with the harness and version. These travel furthest because they are funny or surprising on their own.
7. **The "it changed today" alert**: fixed template, always the same shape, so followers learn to recognise it.

### 4.3 Franchises

- **Prompt Changed** (event driven, fires when a pair lands, ~2 to 4 per week across three harnesses). Template: `[harness] [version] shipped. System prompt: [+/-N chars, M lines]. Tools: [added/removed]. What moved: [one line]. Diff: [url]`.
- **Overhead Tax Tuesday**: the number card, weekly, three harnesses, latest versions. Same layout every week so the trend is visible.
- **Week in Prompts** (Sunday): digest card of the week's pairs, link to `/changes/week`.
- **Tool of the Week**: one tool schema, its size, when it appeared, whether it changed. Starts with `Artifact` at 27,490 chars.
- **One Line**: a single verbatim instruction quoted, typographic card. Daily filler with the highest ceiling.
- **Leaderboard** (monthly once evals run): cheapest harness for the fixed task set.
- **Cache Cold Day**: whenever a prompt change invalidates caches, a post explaining what that cost.
- **Ask the Corpus**: a screenshot answer to a question people ask ("does Claude Code know my remaining quota?" answered with the `<total_tokens>` line).

### 4.4 Cadence

Daily at 14:00 UTC (US morning, EU afternoon): one post. Event-driven Prompt Changed posts go out within two hours of the corpus commit, whatever the time. Weekly franchises on fixed days. Never more than three main-timeline posts a day. Replies to comments within the hour on launch days (replies do not count for impressions but they drive the algorithm's early ranking of the original).

### 4.5 Turning a diff into a post nobody scrolls past

Rules, derived from what a hunk looks like:
- Lead with the consequence, not the diff. "Claude Code stopped telling opus to X" beats "-3 lines in section Y".
- One hunk per image. Crop to eight lines or fewer. Red and green on a dark card, monospace, harness and version in the corner, site URL in the footer.
- The sentence above the image never restates the image. It answers "so what".
- End with the link on its own line. No hashtags. At most one mention.
- If the change is boring, say so: "2.1.251 changed nothing in the prompt. Tool schemas moved 2,311 chars. That is the whole release." Boring, stated plainly, still builds the habit.

### 4.6 What posts itself from CI

`announce.yml` renders: the pair card (PNG, 1200x675, dark), the weekly digest card, the Overhead Tax card, the tool card. Each with `post.txt` from a template. Automation stops at a draft in a GitHub issue for the first six weeks. After that, the Overhead Tax and Week in Prompts cards can post via the X API on a schedule because their copy never needs judgement; Prompt Changed stays hand-posted because the "what moved" line is the value.

### 4.7 Launch sequencing

- **T-14 to T-7**: site live, ten cells and all pairs published, RSS up, OG images verified in the X card validator. Account bio, pinned post drafted, banner is the three-number card.
- **T-7 to T-1**: post nothing. Follow 200 relevant accounts (harness engineers, agent tooling authors, people who post Claude Code tips). DM five people who will be sent the launch post early.
- **Day 0 (a Tuesday)**: post 1 (the three numbers). Reply to every comment. Post 2 six hours later.
- **Day 1 to 7**: one post a day from the first ten below. Post 5 (the quota line) is the intended first spike.
- **Day 8 onward**: franchises start. First Overhead Tax Tuesday, first Week in Prompts.
- **Week 4**: first eval (Overhead Tax with real `usage` tokens). Week 6: tool-turn tax. Week 8: effort ladder. Week 10: coordination overhead with the canvas.

### 4.8 Who amplifies

Named by role rather than handle, since handles change: the Claude Code and Codex engineering leads who post about releases (they will reply, and a vendor reply is the largest single impression multiplier available); authors of agent frameworks and MCP servers; the "AI engineering" newsletter writers who need a chart each week; the Cursor/Windsurf/Zed communities who will want the same for their harness (an invitation, see 5.9); the people who run agent cost threads. Tag one vendor engineer only when the post is a bug report they would want (the contradiction audit), never on a "look how big your prompt is" post.

### 4.9 First ten posts

1. (Day 0, number card)
   > Before you type a single word, your coding harness has already sent this much to the model:
   >
   > Claude Code 2.1.270 (opus): 165,759 chars
   > Codex 0.154.0 (gpt-5.5): 42,307 chars
   > Grok CLI 1.0.30 (grok-4.6): 53,476 chars
   >
   > Captured on the wire. Every version, every model, diffed: knowmorecontext.com

2. (Day 0, +6h, stacked bar)
   > 84% of a Claude Code request is tool schemas. The system prompt everyone argues about is 6%.
   >
   > 31 tools, 140,037 chars, on every single request.
   >
   > The Artifact tool alone is 27,490 chars. Longer than the prompt itself.

3. (Day 1, receipt of the 2.1.261 to 2.1.269 opus hunk)
   > Claude Code 2.1.269 cut 2,442 characters from the opus system prompt. No changelog mentioned it.
   >
   > 45 lines changed. Here is the largest hunk.
   >
   > knowmorecontext.com/prompts/claude/opus/2.1.261..2.1.269

4. (Day 2, two curves)
   > Same 40 tool calls. Two Codex models.
   >
   > gpt-5.6 sends previous_response_id and no system prompt on tool turns.
   > gpt-5.5 resends all 21,299 chars of instructions every turn.
   >
   > The harness is the same. The model decides the bill.

5. (Day 3, quote card, intended spike)
   > Claude Code tells the model how much of your quota is left.
   >
   > `<total_tokens>15000000 tokens left</total_tokens>`
   >
   > Sent inside the system prompt, 2.1.250, `best` model alias. Found because two captures of the same version disagreed.

6. (Day 4, chart)
   > Claude Code tool schemas, opus, by version:
   >
   > 2.1.246 134,557
   > 2.1.250 119,569
   > 2.1.270 140,037
   >
   > A 15K drop and a 20K climb in seven weeks. Your cache went cold each time.

7. (Day 5, side by side)
   > Sonnet gets an 18,000 character longer system prompt than opus in Claude Code 2.1.270.
   >
   > 27,329 vs 9,383.
   >
   > Same harness, same version, same request. Here is what the extra text says.

8. (Day 6, envelope receipt)
   > "Effort" in Claude Code is one field.
   >
   > `"output_config": {"effort": "low"}`
   >
   > That is the entire difference on the wire between low and high. Codex: `"reasoning": {"effort": "high"}`. Grok: same key.

9. (Day 7, first Week in Prompts digest card)
   > Week in prompts, 8 to 14 Sep:
   >
   > claude 2.1.270: system unchanged, tools +2,068 chars (fable[1m])
   > codex 0.154.0: gpt-5.6 first turn down to 2,203 chars on the wire
   > grok 1.0.30: no change
   >
   > Every diff: knowmorecontext.com/changes

10. (Day 8, number card, Overhead Tax Tuesday #1)
    > Overhead Tax, week 1.
    >
    > What each harness sends before your first word, latest version, default model:
    >
    > Claude Code 165,759
    > Grok CLI 53,476
    > Codex 42,307
    >
    > Same card every Tuesday. Watch the numbers move.

Post 9's codex line depends on resolving the 0.154.0 question in section 0 first. If it is a capture artefact, swap in the grok 1.0.25 to 1.0.30 tool schema growth (44,038 to 44,404).

## 5. Everything else

### 5.1 Brand and naming

KnowMoreContext works: it reads as "know more" and "no more" at once, and both are the pitch. Keep the handle. Site name in the header: **Know More Context**, wordmark in monospace, tagline "What your harness sends before you speak." Colour: dark card, one accent (amber for changes, green/red for diffs). The three-number card is the visual identity; every franchise card is a variation of it. Avoid a mascot and avoid the word "leak" anywhere.

Sub-brands, only as URL sections: `/prompts` (the corpus), `/evals`, `/runs`. Do not name them separately.

### 5.2 The run journey canvas

One run is a tree: the human prompt at the root, each agent a lane, each request a node in the lane, each tool call an edge to a child node, subagent spawns as branches into new lanes. Node size is request bytes; node colour is layer share (scaffolding vs work); hovering shows the request skeleton; clicking opens the captured request and the transcript at that point. A cost meter at the top accumulates as you scrub time. The canvas is the artifact for eval 2.7 and the demo for TM itself.

Build: React Flow with a custom node, static `graph.json` per run generated from TM's exchange and event tables (the roster already knows turns and exchanges per run, and subagent tracks are counted the way the inspector lists them). Ship as an Astro island. Provide a "share this moment" URL that encodes node and time, with an OG image of the tree coloured by cost.

### 5.3 Newsletter and RSS

RSS from day one (`/changes.rss`). Newsletter (Buttondown, free under 100 subscribers, then $9/month) sends Week in Prompts on Sunday with the digest card and the three deepest hunks, and a Prompt Changed alert as an optional instant subscription. The newsletter is where a vendor engineer subscribes when they would not follow on X.

### 5.4 CLI

`npx know-more-context claude opus` prints the latest canonical system prompt; `--version 2.1.269 --diff 2.1.270` prints the unified diff; `--tools` lists tool schemas with sizes; `--json` for scripts. It reads `/api/v1/**`, no install beyond npx. Also `know-more-context which` reads the installed `claude --version` and prints whether that version is in the corpus and what changed since the user's last run (stored in `~/.kmc`). That last command is the one people run in a terminal screenshot.

### 5.5 VS Code extension

Status bar item: `claude 2.1.270 · prompt unchanged 3d`. Click opens the cell page. Notification when the installed harness version's prompt changed relative to the last one seen. Low effort, high visibility on screenshots.

### 5.6 MCP server

`know-more-context` MCP with tools `prompt(harness, model, version?)`, `diff(harness, model, from, to)`, `tools(harness, model, version?)`, `whats_new(harness, since)`. An agent can then answer "what is in my own system prompt right now" from the corpus. This is a Worker in front of `/api/v1`. Novelty value is high; the demo post is a Claude Code session asking about itself.

### 5.7 Badges

`/badge/claude/opus.svg`: shields style, "system prompt · 2.1.270 · 9,383 chars · changed 2.1.269". Anyone writing a Claude Code tutorial embeds it. Each badge is a backlink and an impression on GitHub READMEs.

### 5.8 Data licensing

Code MIT. Corpus CC BY 4.0. The prompt text itself is vendor copyright; the corpus publishes it as factual documentation of software behaviour with attribution, the same footing as the many existing GitHub repos that mirror harness prompts from the binary. State this plainly in `/about`. Do not sell the corpus. Do sell what is built on it (5.10).

### 5.9 Non-adversarial posture and the vendor relationship

- Tone: changelog, not exposé. Every post describes what shipped, never what was "hidden".
- Offer vendors a correction path: `/about#corrections` with an email and a public issue tracker. Publish corrections in the feed.
- Invite: a "capture your harness" guide so Cursor, Zed, Amp and others can be added by their own communities via TM. Growth and goodwill in one move.
- Never publish anything that authenticates or addresses (already true). Never publish a user's own prompts or repo content (the corpus is certification probes only, which the issue already scopes).

### 5.10 Monetisation

Not in the first 90 days. After: (1) TM itself, which the corpus advertises on every page footer as the thing that captured it; (2) a paid instant alert tier for teams who pin harness versions and need to know when the prompt moves (Buttondown paid list, $5/month); (3) eval sponsorship, one sponsor per eval page, labelled; (4) the API behind a Worker with a free tier and a key above 1,000 requests/day. Never ads.

### 5.11 Risks

- **Vendor ToS.** Capturing one's own client traffic on one's own machine is ordinary debugging. Publishing verbatim prompt text is the exposure. Mitigation: factual framing, attribution, correction path, no circumvention of anything, and the corpus contains what any user can see with a proxy. A takedown request is answered by taking down the specific text and keeping the diff statistics, which are facts about size and change, not the copyrighted text. Keep the generator able to publish stats-only mode in one flag.
- **"Leaking".** The word will be used by others. Pre-empt with the `/about` page and the zero-match redaction report.
- **Being wrong.** A wrong number in a viral post is the real risk. Every card carries the bundle id and the TM commit; every number on a card is read from `index.json`, never typed.
- **Vendor changes that break capture.** A harness moving to a transport TM cannot proxy leaves a gap in the timeline. Publish the gap as a gap.
- **The empty codex 0.154.0 cell** from section 0. Resolve before post 9.
- **Copyright on the prompt text in the OG images.** Same as the corpus; hunks of eight lines are quotation.

### 5.12 Moats

- The capture pipeline and its certification discipline. Anyone can proxy once; keeping 26 versions across three harnesses with declared variants and byte-identical regeneration is a system.
- The timeline itself. Every week the corpus exists it becomes harder to reproduce, because old binaries and old server behaviour are gone.
- The evals grounded in captured requests rather than in vendor-reported usage.
- The habit: a fixed card every Tuesday for a year.

### 5.13 Smaller ideas, unranked

- A "diff this prompt against yours" paste box that diffs a user's own captured prompt against the canonical one client side.
- A `/prompts/claude/opus/2.1.270#L214` deep link format so people cite lines.
- An annual "State of the System Prompt" long post with the churn index per vendor.
- A public Google-style "site:" search across every version of every prompt (Pagefind, static).
- A "prompt archaeology" series: the first version of an instruction and every edit since, one instruction per post.
- Publish the tool-turn request skeleton as its own page since it is the cost story.
- A per-tool RSS feed so people who care only about `Bash` subscribe to that.
- `robots.txt` that allows every crawler, including AI crawlers. Being in the training data is distribution.

## Round 2

Written after reading the astra document in full and re-measuring the bundles. Every number below was measured this session unless attributed. Two Round 1 claims are withdrawn in this section: the codex 0.154.0 anomaly (my own script error, item 3) and CI posting to X (item 2).

### R2.1 Rescope: the publishable unit is the request, decomposed

Stuart's table matches mine within serialization choice (his 164,768 total for 2.1.270 opus against my 165,759 is `json.dumps` with separators versus raw bytes; the corpus must count the decoded `raw_request_base64` bytes as sent and never re-serialize). Round 1 already made the 84 to 86% observation, but it still called the site "the corpus" and put system prompts at the top of the URL tree. That was wrong. What follows replaces it.

**The unit is a request snapshot: one (harness, version, model, shape) cell, decomposed into six layers, each published, each diffed, each with its own timeline.**

| layer | source, per profile | claude 2.1.270 opus | what moves it |
| --- | --- | --- | --- |
| `tools/<name>` | `tools[]` (claude, grok), codex `additional_tools` developer item | 140,037 (31 tools) | the harness ships or rewrites a tool |
| `system` | top level `system[]`, codex base instructions developer item, grok `role: system` | 9,383 | the harness edits its prompt |
| `system-message` | claude `messages[]` item with `role: system` | 14,186 | same, second document |
| `reminders` | `<system-reminder>` blocks in the user turn | 1,121 (haiku: 15,704) | environment and session state |
| `envelope` | headers, betas, `thinking`, `output_config`, `context_management`, `reasoning`, `prompt_cache_key` | ~400 | routing and knobs |
| `environment` | codex `<skills_instructions>` developer item, `mcp__*` tools, paths | 3,844 (codex sol) | the capturing machine |

Two measured facts force the tool layer to be per tool and to have its own timeline:

```
Artifact tool schema, claude opus, chars
  2.1.246  27,490
  2.1.250  28,478   Workflow 21,870 -> 5,473 in the same release (-16,397)
  2.1.251  30,385
  2.1.260  38,333   (+7,948)
  2.1.269  48,575   (+10,242)
  2.1.270  48,575
```

One tool grew 77% in seven weeks and is now five times the opus system prompt. In the same window the system prompt moved by hundreds of chars per release and 2,442 once. Version to version, the tool layer is where the bytes move, and `Artifact` alone explains most of the opus request's growth from 159,210 to 165,759.

**The `role: system` message comes in.** At 14,186 chars for opus it is 51% larger than the system prompt #683 publishes, and it is a document with a diff timeline of its own. Excluding it while publishing the 9,383-char field is publishing the smaller of two prompts and calling it the prompt. It is one more selector in the same extractor. Haiku has none and instead carries its reminders in a 15,704-char user turn, which is itself a post: "haiku gets the same instructions as a user message, not a system message."

**Revised URL scheme.** Top level is the request, not the prompt.

```
/                                                 the three numbers, the change feed
/requests/claude/opus                             model page: request size by version, stacked by layer
/requests/claude/opus/2.1.270                     cell page: six layer tabs, sizes, provenance
/requests/claude/opus/2.1.269..2.1.270            pair page: diff per layer, largest hunk first
/requests/claude/2.1.269                          release page: every model, every layer, what moved
/tools/claude/Artifact                            tool page: schema by version, per-version diff, which models carry it
/tools/claude/Artifact/2.1.263..2.1.269           tool pair page
/tools/claude                                     tool roster: 31 tools sorted by size, added/removed per version
/prompts/claude/opus                              alias for /requests/claude/opus#system (keeps the SEO landing)
/prompts/claude/opus/2.1.270                      the system prompt text, canonical, for the "claude code system prompt" query
/system-message/claude/opus/2.1.270               the second document
/shapes/codex/gpt-5.6-sol/0.154.0                 first-turn vs tool-turn side by side
/changes, /changes.rss, /api/v1/**, /corpus/**    unchanged from Round 1
```

`/prompts/**` stays because it is the search query people type, and it is an alias, not a second tree. The Round 1 `/compare` and `/badge` routes are unchanged.

**Normalizer for the tool layer.** Measured: zero matches for `/Users/`, `/private/`, UUIDs or dates across every claude tool schema in every version. The eight rules are not needed for tools, and applying them is harmless. What the tool layer needs instead is two rules of its own:

- **Rule 9, environment tools.** Haiku's roster goes 35 to 41 to 35 to 41 across 2.1.258 to 2.1.270 because six `mcp__claude_ai_Gmail__*`, `Google_Calendar` and `Google_Drive` tools appear and vanish with the capturing machine's connected MCP servers. Any tool whose name starts `mcp__` is moved to the `environment` layer and never enters the canonical roster or its diff. Without this rule the corpus publishes "Claude Code added six tools in 2.1.260 and removed them in 2.1.263", which is false.
- **Rule 10, stable serialization.** Sort `tools[]` by name, sort keys, LF endings, and keep the original order in `_index.json`. The diff is then per tool and a reorder is not a change.

Codex needs two more: the `additional_tools` developer item carries an `at_<uuid>` id (rule 4 already covers it), and the `<skills_instructions>` developer item lists whatever skills the capture home had, with `r0 = /Users/...` paths. That item is `environment`, not `system`. Between the 10 Sep and 13 Sep captures of gpt-5.6-sol it differed by three skills and a workspace path; none of that is Codex changing.

**Which franchise: system prompt diffs or tool schema diffs?** System prompt hunks for the recurring visual, tool numbers for the recurring card. Defence: a scroller reacts to a sentence a vendor wrote to a model ("The user gets very frustrated when you stop and ask for confirmation") because it is English, it is about them, and it is quotable without explanation. A JSON schema hunk reads as noise at phone width and needs a caption to mean anything. But the tool layer wins every time the post is a number: "one tool schema is 48,575 chars" needs no hunk. So the rule is: if the layer that moved is `system` or `system-message`, post the hunk; if it is `tools`, post the number and the tool name, never the schema. Overhead Tax Tuesday stays a number card and now stacks six layers.

**Headline number and the launch post.** Round 1 led with 165,759 chars. The better number is the ratio, because it survives every unit argument:

> 86% of what Claude Code sends the model before you type is tool schemas.
>
> 2.1.270, opus, one request: 165,759 chars.
> Tools: 140,037. System prompt: 9,383.
>
> One tool, Artifact, is 48,575 chars. It was 27,490 seven weeks ago.
>
> Every version, every model, every layer, diffed: knowmorecontext.com

### R2.2 Automation and the rewards policy

**What I could verify.** Direct fetches of `help.x.com/en/using-x/original-content-rewards` and `.../x-automation` returned HTTP 403 twice each, including with a browser user agent, and the archive mirror is blocked from this environment. I did not read the policy page. What I have is the search index's rendering of that page, which reproduces its eligibility list verbatim and reads, on the automation point: "Content created or posted by automated means is ineligible", alongside "Impressions: Have at least 500,000 Home Timeline impressions from verified users in the last 90 days (impressions on replies are excluded)" and "Qualified impressions are unique impressions from Premium users ... on the Home Timeline feed, where at least 50% of the post is visible." Astra quotes the same clause as "Was created or posted using automated means". Two secondary articles (a beehiiv guide and TechCrunch) paraphrase the same exclusion and do not mark it as a direct quote. Treat the exact wording as unverified and the substance as settled: creation by automation and posting by automation are each disqualifying on their own, and the clause is written as a disjunction.

**The three cases.**

- **(a) CI generates the artifact, a human writes the copy and presses post.** Safe under the disjunction as I read it. The post is the text plus an attachment; a chart rendered from data is the same class of object as a screenshot or a photo, and the policy's stated targets are copied, reuploaded, aggregated and bot-posted content. The residual risk is an image-only post where the image carries all the content and the text is a URL. Do not make those.
- **(b) CI drafts the copy, a human reviews and posts.** Genuinely unclear, and it splits. If the human rewrites, the post was created by the human from automated inputs, which is (a). If the human pastes the draft, the content was "created by automated means" and only posted by hand, which the disjunction catches. Nobody on the outside can tell the two apart, and X's enforcement will pattern match on cadence and template regularity, not on who typed. Assume Stuart follows the rule literally: no drafted prose reaches the composer.
- **(c) Fully automated detect and post.** Disqualifying on both halves. No argument.

**Round 1 was wrong here and is withdrawn.** I proposed that Overhead Tax Tuesday and Week in Prompts post via the X API after week six. That is case (c) on the account whose eligibility is the goal. It would have disqualified the account for a franchise that earns 8K impressions a week.

**Operating rule, end to end.**

The pipeline may, without a human:
1. Regenerate the corpus, diffs, JSON, RSS, badges and the site on every commit.
2. Render every image: number cards, diff hunk PNGs, per-tool timelines, weekly digest cards. Images contain data, labels, a version pair, a date and the site URL. They contain no sentence of editorial prose.
3. Open a GitHub issue per candidate ("claude opus 2.1.269..2.1.270 landed") carrying: the image files, a bulleted fact list read from `index.json` (numbers, tool names, line counts, the URL), and the largest hunk as plain text. No draft post text, no LLM summary. The fact list is the input to a human, the way a wire feed is input to a reporter.
4. Post to RSS, the newsletter and a Mastodon or Bluesky mirror if one exists, since none of those gate a rewards programme. Never to the KnowMoreContext X account.

The human must, every time:
1. Write every word of the post in the X composer, from the fact list, in their own voice.
2. Choose which image to attach and check it against the numbers.
3. Press post. No scheduler, no third party tool, no API token on the account.
4. Keep the templates for the franchises as a habit of shape, not as pasted text. The card is the constant; the sentence above it is written fresh each week.

One line of copy per post is enough to satisfy this rule honestly, and one line is also what performs. The rule costs Stuart ten minutes a day. The alternative costs the programme.

### R2.3 The codex anomaly, resolved

**Round 1 was wrong about what it saw.** The 2,203 to 3,714-char probes at codex 0.154.0 are the **tool-turn** bundles: `correlation_method: delivery-run-tool-result`, one `custom_tool_call_output` input item, `previous_response_id` set, no developer items. First-turn and tool-turn shapes are separate bundles under the same model directory, and my Round 1 script took `probes[0]` of whichever bundle the glob listed first. For 0.154.0 gpt-5.6-sol and gpt-6-astra the tool-turn bundle sorted first. The first-turn bundles at 0.154.0 are 56,569 to 60,772 chars with three developer items and no `previous_response_id`, in line with 0.153.4. Not a capture gap, not a moved prompt, not a different endpoint. A script bug, and exactly the bug the generator's `MissingInstructions` check from Round 1 §3.3 exists to catch.

**What the bundles do show is bigger.** Two first-turn captures of gpt-5.6-sol at the same binary, `codex-cli 0.154.0`, carry different base instructions:

```
capture       effort  developer items (chars)         base instruction opens with
2026-09-07    low     30,012 / 17,730 / 4,942  (0.153.4)  "...until their goal is genuinely handled."
2026-09-10    xhigh   30,012 / 17,730 / 4,942  (0.154.0)  same
2026-09-13    low     32,419 / 21,261 / 3,346  (0.154.0)  "...until their intended goal is completely handled."
gpt-6-astra 09-10     32,419 / 21,261 / 4,295  (0.154.0)  the new text, GPT-6 spelling
```

The 10 Sep to 13 Sep diff of the sol base instruction is 232 lines. It adds a "When to ask the user for permission" section and an "Autonomy and persistence" section, and replaces the three-paragraph personality passage ("curious, rich personality ... another subjectivity") with one paragraph ("a curious, thoughtful collaborator and a lucid communicator"). The `additional_tools` item also grew 2,407 chars. gpt-6-astra had the new text already on 7 Sep at 0.153.4.

Evidence on the mechanism: both the old phrase ("curious, rich personality") and the new phrases ("Autonomy and persistence", "curious, thoughtful collaborator") are present as strings in the installed 0.154.0 binary at `@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin/bin/codex`. The binary ships both prompts. Something outside the binary chose which one gpt-5.6-sol receives, and that choice flipped between 10 and 13 Sep. Effort is ruled out (sol got the old text at low and at xhigh; astra got the new text at low, medium and high). Model id is ruled out (same `codex/gpt-5.6-sol`). What remains is a remote selector, and the obvious candidate is the model catalog that `codex debug models` reads, which CLAUDE.md already documents as the credential free GET that can name models the binary does not know.

**The one check that settles it:** run `codex debug models` outside the sandbox (it failed here on reading `~/.codex/config.toml`, operation not permitted) and look for a per-model field that names an instruction variant or a prompt template id; then compare against the catalog TM's harness refresh stored before 10 Sep. If the catalog carries the selector, the story is "Codex can change your system prompt without shipping a binary", and the corpus gains a fourth coordinate, capture date, beside harness version. If it does not, the next candidate is a server side experiment flag, and the same story holds with a less satisfying mechanism.

Either way this is the biggest single finding in the corpus so far and it was not visible in the 0.154.0 cell as #683 would publish it, because #683 keys on version. Astra's experiment 17, "Same version, different day", predicted this exactly. It moves to the front of the eval queue and it needs no eval runner: capture the same first turn daily and diff.

### R2.4 The astra document

**Three strongest ideas not in mine.**

1. *"The broad claim that nobody publishes harness prompt changes is already contested. Piebald's own repository reports Claude Code 2.1.270, a prompt changelog across 287 versions, and extraction from the distributed CLI."* Adopt, and it sharpens the position rather than weakening it. Piebald extracts from the binary. Today's codex finding is the proof that the binary is not the prompt: 0.154.0 ships both instruction sets and only the wire shows which one a model was sent on which day. The brand sentence becomes "what was sent, not what was shipped", and the first collaboration offer to Piebald is a matched release where their extraction and our capture disagree.
2. *"`read_baseline_bundle` upgrades schemas 8 through 12 by dropping the historical B probe ... A corpus generator that simply calls that convenience reader may erase precisely the variants it is supposed to publish."* Adopt. Verified: the schema comment in `baseline_evidence.py` says a bundle at 12 or below "loads with its B probe dropped and its prompt pair collapsed to the A prompt". My Round 1 generator read `probes[]` from the raw JSON and would have kept B by accident, not by design. The generator gets an explicit archival iterator that never goes through the upgrading reader, and a test that a schema 12 fixture yields three probes.
3. *Experiment 17, "Same version, different day"*, and the general insistence that identity carries capture time and observed wire model, not just three coordinates. Adopt in full; item 3 above is the evidence. Capture date becomes a first class axis on the cell page and the pair page can be two dates at one version.

Two more I take in part: the five-part claim object (assertion, scope, measurement, evidence link, interpretation) is right as the JSON behind a card and wrong as a writing style for X; and the rights review before full text distribution is right, with the stats-only publish mode from Round 1 §5.11 as the fallback it names.

**Three weakest claims.**

1. *"54 precise routine observations at 2,000; 24 broader comparisons at 8,000; 12 flagship results at 25,000 ... 600,000."* A new account does not average 25,000 on twelve flagships and 8,000 on twenty four comparisons. Median posts from a sub-1,000 account land at hundreds to low thousands; the target is met by four to six posts that clear 50K to 150K, and the plan has to be built to produce candidates for those spikes, which means quotable vendor sentences and single numbers, not "broader comparisons". The same section says *"Social replies ... receive no time budget as a growth tactic"*. Replies do not count for impressions, but replying to every comment in the first hour is what ranks the original into more Home timelines. That budget is not optional.
2. The evals are hedged past the point of being shareable. Post 04 ends *"Billing needs a separate measurement."* Experiment 04's rule is *"Never turn the seed observation into an unmeasured savings percentage."* Experiment 05 forbids a *"synthetic dollar allocation"*. Every one of those cautions is correct in a methods section and every one of them removes the sentence a reader would repost. The fix is not to invent numbers; it is to measure the one number that makes the sentence true (a 40-tool-turn session under capture, `usage` read off the responses) before the post exists, then post the number without the caveat. Forty experiments and a *"$3,000 first month experiment envelope"* with 270 runs is a research programme, not a 90-day content plan. Three evals in 90 days, each producing one number, is the plan.
3. Post 02 of its launch week: *"Same Claude Code version. Very different primary system prompts. Opus: 9,383 characters, Fable: 13,094, Haiku: 27,431 ... These counts exclude tools and the separate system message."* That is the 6% published as the size story with the 86% in a footnote, the exact framing this round rejects. Its week one also spends post 05 on *"Why normalization matters ... Eight normalization rules made 80 of 88 cells internally consistent"*, a method note about the corpus's own laptop noise, to an account with no followers. Method belongs on `/method`, and week one belongs to numbers and vendor sentences. The seven-day rotation makes this structural: Wednesday "one concept explained" and Sunday "method note, replication, correction" put two of every seven posts inward-facing.

A smaller point of disagreement: astra prefers Cloudflare Workers static assets over Pages on the 20,000 file limit. The revised URL scheme above adds tool pages and pair pages per layer and will reach that limit within a year, so the concern is right. Where it lands is a deployment flag, not a design decision, and Round 1's recommendation stands with that flag noted.

### R2.5 What changed my mind

One thing, and it is item 3. I went in believing harness version was the primary key of the corpus and the vendor's changelog was the thing missing. The bundles show a model receiving a different prompt on Wednesday than on Sunday from the same binary, with both prompts inside that binary. Harness version is a necessary coordinate and an insufficient one; capture date is the other, and the property that makes KnowMoreContext different from a binary extraction is that it can see the difference at all.

## Round 2b

### R2b.0 Withdrawal

Round 2 said "effort is ruled out (sol got the old text at low and at xhigh; astra got the new text at low, medium and high)". The sol half of that sentence crossed binaries: sol at low was the 7 Sep capture on 0.153.4, sol at xhigh was 10 Sep on 0.154.0. It does not rule out an effort mapping introduced in 0.154.0. The astra half says nothing about sol. As stated, the claim is withdrawn. What replaces it is below, and it is stronger than the original because it rests on two things I had not looked at: every uncertified run in the workspaces, not only the 176 certified bundles, and a response header the envelope projection drops.

### R2b.1 What the evidence now separates

I classified every captured codex first-turn request body in `~/.transport-matters-preview/workspaces/**/transport.json` (about 2,000 `response.create` bodies without `previous_response_id`, 28 Aug to 14 Sep) by two markers of the new prompt generation: the "When to ask the user for permission" section in the developer instructions, and the `clock` namespace in `additional_tools`. The two markers never disagree. Beside them I read the `x-models-etag` response header the Codex backend returns on the websocket upgrade, which the envelope projection records by name only.

| model | old generation | new generation |
| --- | --- | --- |
| gpt-6-astra | never | every capture from 4 Sep, at low, medium, high, xhigh, on 0.153.2, 0.153.4, 0.154.0 |
| gpt-5.6-sol | every capture to 10 Sep, incl. 0.153.4 at low (x16) and xhigh (x8) on 7 Sep, and 0.154.0 at xhigh (x36) on 10 Sep | every capture from 12 Sep: 0.154.0 at medium (12 Sep x14, 14 Sep x32) and low (13 Sep x8) |
| gpt-5.6-luna | every capture to 14 Sep, all four efforts, incl. 0.154.0 at low, medium, high and xhigh on 12 to 14 Sep | never |
| gpt-5.6-terra | every capture to 13 Sep, incl. 0.154.0 at low on 13 Sep | never |

Three consequences:

1. **Effort has never selected the generation for any model.** Astra is new at all four efforts. Luna and terra are old at all four efforts at 0.154.0 on the same dates sol is new. Sol itself was old at both low and xhigh on 7 Sep under 0.153.4. Across four models, four efforts, seven binaries and eighteen days there is no (model, binary, date) where two efforts received two generations.
2. **On 13 Sep, at 0.154.0, at effort low, under the same catalog etag, sol received the new generation and luna received the old.** Same binary, same day, same effort, same server catalog state, different model. The selector is per model. That is what a model catalog does and not what an effort knob does.
3. **The catalog moved in the window.** `x-models-etag` was `cd818831` on every 10 Sep capture (sol old, astra new) and `45a6c0af` on every capture from 12 Sep (sol new, luna old). The etag changes roughly daily with the binary held fixed: six distinct etags under 0.150.1 alone, twenty across the eighteen days. The server revises its model catalog far more often than OpenAI ships a CLI, and one of those revisions coincides with sol's flip.

What the evidence does not contain is the one cell Stuart named: sol at xhigh (or high) after 12 Sep. Every post-flip sol capture is at low or medium. So the effort hypothesis survives in exactly one form: "0.154.0 introduced, for gpt-5.6-sol only, a mapping where low and medium get the new prompt and high and xhigh get the old one, and this mapping is absent for luna, terra and astra". That is a strange mechanism and it is still a mechanism. One capture kills it.

### R2b.2 The capture matrix for tonight

Certification already captures A1 and A2 for a cell, which is two probes; one is enough because the text is deterministic per (model, catalog), but A1/A2 is the existing path, so use it.

| launch | model | effort | expected under date/catalog | expected under effort |
| --- | --- | --- | --- | --- |
| 1 | gpt-5.6-sol | xhigh | new (permission section, clock) | old |
| 2 | gpt-5.6-sol | high | new | old |
| 3 | gpt-5.6-sol | low | new (control, matches 13 Sep) | new |
| 4 | gpt-5.6-luna | low | old, unless the rollout reached luna since 14 Sep | old |
| 5 | gpt-5.6-luna | xhigh | same as launch 4 | old |
| 6 | gpt-6-astra | low | new (control) | new |

Record `x-models-etag` from each upgrade response. Decision rule:

- Launch 1 new: effort is dead in every form. The story is date/catalog. Launches 2 to 6 are confirmation.
- Launch 1 old and launch 3 new under the same etag: effort selects for sol at 0.154.0. The story is effort. Launch 4 versus 5 says whether luna has the same mapping.
- Launch 1 old and launch 3 old: sol rolled back since 14 Sep. Still date/catalog, and a better post than either.
- Launches 4 and 5 new: the rollout continued; the etag will differ from `45a6c0af`; record the date.

Also record, from the same runs, whether `codex debug models` (run outside the sandbox: `! codex debug models`) lists per-model instruction or feature fields. If the catalog names the prompt generation, the mechanism is settled and the corpus can read it directly rather than inferring it from text.

### R2b.3 Consequences under each hypothesis

**If effort selects the prompt.** Effort becomes a content coordinate. The cell key is (harness, version, model, effort, shape). The corpus does not quadruple everywhere: claude's system prompt is identical across efforts at every version measured (2.1.263 opus[1m] at low and high, 2.1.250 fable[1m] at low and high, 2.1.270 opus[1m] at low and high all share one normalized text), so claude and grok cells collapse across effort and publish "effort: any". Codex splits only where the text differs. The generator computes this: group probes by normalized text within (harness, version, model, shape); if all efforts land in one group, the cell publishes once with `efforts: [all observed]`; if not, it publishes one cell per effort group with `efforts: [low, medium]` and `efforts: [high, xhigh]`. Page count grows by the number of split cells, which today would be two.

URL scheme: effort enters the path only for split cells, `/requests/codex/gpt-5.6-sol/0.154.0/low` and `/requests/codex/gpt-5.6-sol/0.154.0/xhigh`, with `/requests/codex/gpt-5.6-sol/0.154.0` as the page that shows the split and links both. Unsplit cells keep the three-coordinate URL. A URL never lies about a dimension that did not matter.

Consecutive pairs with two axes: pairs are along one axis with the other fixed. Version pairs hold (model, effort group) fixed: `0.153.4..0.154.0` for sol at low. Effort pairs hold (model, version) fixed: `0.154.0/low..xhigh` for sol. A change feed entry is a change in canonical text, and it names which axis moved. The generator never diffs across both axes at once, and a version pair whose effort groups differ on the two sides is published as two pairs, one per group that exists on both sides, plus an "effort split appeared in 0.154.0" entry.

**If the catalog selects the prompt.** The corpus is keyed on a coordinate OpenAI changes without shipping anything, and the naming answer is that OpenAI already names it: `x-models-etag`. A snapshot is (harness, version, model, shape, catalog etag). The etag is a vendor identifier for the server state that chose the prompt, it rides on every captured response, and it is short enough for a URL: `/requests/codex/gpt-5.6-sol/0.154.0@45a6c0af`. Claude and grok have no equivalent header yet; their snapshots carry the capture date as the fallback fourth coordinate and the generator checks whether an Anthropic or xAI response header behaves the same way.

Never claiming a change at a version boundary that did not happen there: a version pair is published as a version change only when the catalog etag is the same on both sides. When the etag also moved, the pair page says "binary 0.153.4 to 0.154.0 and catalog 3498e390 to 45a6c0af; the text change cannot be attributed to the binary" and the change feed entry is labelled `attribution: ambiguous`. When the binary is the same and the etag moved, it is a catalog change and says so: "gpt-5.6-sol, codex-cli 0.154.0 unchanged, catalog cd818831 to 45a6c0af, +2,582 chars, new permission and autonomy sections, clock tool added". Today's certified bundles give exactly this ambiguous pair for sol at 0.153.4 to 0.154.0, and the uncertified runs give the clean same-binary pair, which is why the workspaces need to feed the corpus, not only the bundles.

Timeline UI: two tracks under one time axis. Top track, binary releases as ticks. Bottom track, catalog etags as ticks. The prompt text is a band that spans time and changes colour where its canonical sha changes; the band's edge sits on whichever tick it coincides with. For sol the band flips between the 10 Sep and 12 Sep catalog ticks with no binary tick in between, and a reader sees that without a caption. For astra the band is flat. For luna the band is flat and old, next to sol's, which is the rollout picture in one frame. Every day of capture adds a point; the daily first-turn capture per model becomes the corpus's heartbeat, and the certified bundles remain the reference points it is calibrated against.

### R2b.4 Both launch posts

**If the capture says date/catalog:**

> Codex changed what it tells gpt-5.6-sol on 12 September. No CLI update. Same binary, 0.154.0, both days.
>
> +2,582 chars: a permission section, an autonomy section, a clock tool.
>
> gpt-5.6-luna, same binary, same day, same effort: still the old prompt.
>
> We know because we captured what was sent. knowmorecontext.com

**If the capture says effort:**

> Set Codex to low effort and gpt-5.6-sol gets a different system prompt than at high.
>
> Same binary, 0.154.0, same day. Low and medium: a new permission section, an autonomy section, a clock tool. High and xhigh: none of it.
>
> Effort is not a knob. It picks the prompt.
>
> Captured on the wire, every model, every setting: knowmorecontext.com

The bet: date/catalog, and not narrowly. Effort would require a mechanism that exists for one model out of four and appeared in one binary, against a catalog that visibly revised itself in the window and a per-model rollout pattern (astra 4 Sep, sol 12 Sep, luna and terra pending) that is what a staged server-side rollout looks like. Two thousand captured requests contain no effort-selected prompt. I would put it at nine in ten, and launch 1 tonight settles it either way.

### R2b.5 The positioning line

**What was sent, not what was shipped.**

The argument. A harness's prompt is not a file in a binary. It is the result of a selection the binary makes at runtime, from templates it carries, under inputs it gets from the vendor's server. Codex 0.154.0 contains both the old and the new gpt-5.6 instruction text as strings; extracting the binary tells you both exist and cannot tell you which one gpt-5.6-sol received on 13 September, or that luna received the other. Only the request on the wire carries that answer, and the wire carries the vendor's own identifier for the server state that made the choice. Extraction publishes the menu. Capture publishes the order.

Who this beats, by name:

- **Piebald's `claude-code-system-prompts`**, the strongest competitor, 287 versions extracted from the distributed CLI. Its unit is the binary version. It cannot show a prompt changing while the version holds still, cannot show which of several embedded templates a model was sent, cannot attach effort, model or request shape to a text, and cannot show tool schemas as assembled. Credit it, link it, and offer the matched-release comparison from Round 2; the day sol's flip is published, the comparison writes itself.
- **OpenAI's own `codex` source**, where the Rust core carries the prompt markdown. Source is the menu with comments. It shows the templates and the selection code, never the server-side value that drove the selection on a given day, and it cannot show the assembled `additional_tools` item or the `clock` namespace arriving.
- **The "system prompts of AI tools" collections on GitHub**, which republish leaked or extracted text without version, model, effort, shape, date or provenance. They are quotations. Nothing in them can be diffed against anything.
- **Vendor changelogs**, which do not mention prompt text at all and cannot mention a catalog revision that shipped no binary.
- **Prompt-injection "reveal your system prompt" screenshots**, which are model output, not the request, and are wrong whenever the model paraphrases.

Every one of those publishes a version of the prompt. None of them can publish the sentence "same binary, different prompt, here is the server etag that changed", and that sentence is the one that makes a reader check their own harness tonight. The property's line, the bio, the homepage header and the first launch post all carry it: what was sent, not what was shipped.

## Round 3: The Proposal

This section stands alone. It replaces the deliverable, data and acceptance sections of issue #683 and is written to become the issue comment and then the repository README. Every number is from this session's measurements of `~/.transport-matters-preview/baselines/bundles` (176 bundles, artifact schema 13) and `~/.transport-matters-preview/workspaces/**/transport.json`, or from Stuart's six-run experiment on 14 Sep. Numbers marked † were measured once and not independently checked.

### 1. What the corpus is

A public, versioned record of the exact request each coding harness sends to its provider, captured on the wire by Transport Matters certification, decomposed into layers, and diffed along every axis on which it has been observed to change. The system prompt is one layer. It is 5.8% of a Claude Code request.

Three findings fix the design:

- **Tool schemas dominate.** Claude Code 2.1.270, opus, first turn, 167,710 bytes as sent: `tools` 141,538 (84.4%), `messages` 16,053 (9.6%), `system` 9,661 (5.8%). Stuart's reading from the component tables gives 84.48 / 9.37 / 5.87; the difference is sub-object serialization and the house rule in §5 removes it. One tool, `Artifact`, is 48,575 chars and grew from 27,490 at 2.1.246. `Workflow` fell from 21,870 to 5,473 at 2.1.250.
- **The prompt moves without a release.** Codex 0.154.0, one binary, sent gpt-5.6-sol one instruction set on 10 Sep and a different one from 12 Sep (+2,582 chars, 208 changed lines, a `clock` tool namespace added), then moved again by 14 Sep (24 changed lines against the 13 Sep bundle). gpt-5.6-luna and gpt-5.6-terra stayed on the old set throughout; gpt-6-astra was on the new set from 4 Sep. The server's `x-models-etag` response header changed in the same window and changes roughly daily with the binary fixed (twenty distinct values in eighteen days; six under 0.150.1 alone). Harness version is therefore a necessary coordinate and not a sufficient one.
- **Effort does not select the prompt.** Stuart's experiment: sol at xhigh, high and low on 0.154.0, one day, byte-identical component sets (`system_set_hash 19a6dedc`). The historical captures agree: astra new at four efforts, luna old at four efforts, sol old at low and xhigh on 7 Sep. Effort leaves the identity key.

### 2. Snapshot identity

A **cell** is `(harness, harness_version, model, shape)`. A **snapshot** is a cell observed on a date. A **span** is a run of consecutive snapshots of one cell whose canonical text (every layer) is identical.

```
cell      claude / 2.1.270 / opus / first-turn
snapshot  claude / 2.1.270 / opus / first-turn @ 2026-09-13
span      codex / 0.154.0 / gpt-5.6-sol / first-turn  [2026-09-10 .. 2026-09-10]  sha a27cb90a
          codex / 0.154.0 / gpt-5.6-sol / first-turn  [2026-09-12 .. 2026-09-13]  sha ace06116
          codex / 0.154.0 / gpt-5.6-sol / first-turn  [2026-09-14 .. ]            sha <new>
```

Rules:

- `model` is the launch model string TM records (`opus`, `sonnet[1m]`, `gpt-5.6-sol`). The wire model rides on the snapshot as provenance.
- `shape` is `first-turn` or `tool-turn`. The two are separate cells and never diffed against each other.
- **Effort is not in the key.** It is recorded per snapshot as `efforts_observed: [low, xhigh]`, and the cell carries `effort_invariance: proven | single`. `proven` requires at least two efforts captured for that cell with one canonical text. Today `proven` holds for claude 2.1.263 opus (low, medium), 2.1.263 opus[1m] (high, low), 2.1.250 fable[1m] (high, low), 2.1.270 opus[1m] (high, low), codex 0.153.4 gpt-5.3-codex-spark (unset, low, medium), 0.153.4 gpt-5.6-luna (low, medium), 0.153.4 gpt-6-astra (low, medium, high), 0.154.0 gpt-5.6-sol (low, high, xhigh, Stuart's run), grok 1.0.13 grok-4.5 and grok-4.6 (low, medium). Every other cell is `single` and the page says so. If a future cell ever yields two texts at two efforts on one date, the generator refuses to publish it and raises `EffortSplit`, which is the signal to revisit this section, not a case to be handled silently.
- **Server state is provenance, not key.** For codex the snapshot records `server_state: {x-models-etag: "45a6c0af..."}`. Claude and grok record none until an equivalent header is found. The date is the axis; the etag is the evidence that the vendor's server changed.
- **Two snapshots of one cell with different canonical text on different dates are two spans, not variants.** A variant is two texts on one date in one cell (claude 2.1.250 `best`, with and without a `<total_tokens>15000000 tokens left</total_tokens>` line†). Variants carry a `cause`: `quota_injection`, `unknown`.

### 3. The request specimen: six layers

Every snapshot publishes the same six layers. A layer that a profile does not have is `absent`, never empty.

| layer | anthropic-messages (claude) | codex | grok |
| --- | --- | --- | --- |
| `system` | top-level `system[]` text blocks, joined | `instructions` (gpt-5.5, gpt-5.3-codex-spark) or the `input[]` `role: developer` items that are not `additional_tools` and not `<skills_instructions>` (gpt-5.6, gpt-6) | `input[]` `role: system` |
| `system-message` | `messages[]` item with `role: system` (14,258 bytes for 2.1.270 opus; absent for haiku) | absent | absent |
| `tools/<name>` | `tools[]`, one file per tool | `tools[]` (5.5, spark) or the `additional_tools` developer item's namespaces, one file per function | `tools[]` |
| `reminders` | `<system-reminder>` blocks in the user turn (haiku carries 15,704 chars here†) | absent | absent |
| `envelope` | header names, `anthropic-beta`, `thinking`, `output_config`, `context_management`, `cache_control` positions | header names, `reasoning`, `text`, `include`, `store`, `x-codex-beta-features`, `x-models-etag` | header names, `reasoning`, `include` |
| `environment` | `mcp__*` tools; normalized paths and ids | `<skills_instructions>` developer item; `client_metadata`; `at_<uuid>` ids | normalized paths and ids |

**The two codex extraction locations are a hard requirement, not a detail.** gpt-5.5 and gpt-5.3-codex-spark send `instructions` as a top-level key and `tools[]` as a top-level array. gpt-5.6 and gpt-6 send no `instructions` key and no `tools` key: the instructions are `role: developer` items in `input[]` and the tools are inside an `additional_tools` developer item. An extractor that reads `instructions` publishes 5.5 and silently emits an empty `system` for every 5.6 and gpt-6 cell; an extractor that reads developer items does the reverse. The Round 1 measurement table in this document shows exactly that failure (`tools=0 sys=0` for every 5.6 cell) because it read only the top-level keys. The extractor reads both, records which one answered as `system_source: instructions | developer-items`, and treats a codex first-turn snapshot with an empty `system` as a fatal `MissingInstructions`.

### 4. Normalization

Normalization makes two captures of one snapshot compare equal. It never removes content and it never hides a difference between two dates.

Rules 1 to 8 are #683's: UUIDs, the `cc_version` build suffix, `/Users/…`, `/private/var/folders/…`, `/private/tmp/…`, and the flattened `-Users-…`, `-private-var-folders-…`, `-private-tmp-…` forms. Each replacement is logged per snapshot as `(rule, count)`.

Added:

- **Rule 9, environment tools.** Any tool whose name starts `mcp__` is moved from `tools/` to `environment`. Measured cause: haiku's roster reads 35, 41, 35, 41 across 2.1.258 to 2.1.270 because six `mcp__claude_ai_Gmail__*`, `Google_Calendar` and `Google_Drive` tools follow the capturing machine's connected MCP servers. Without the rule the corpus publishes a tool addition and removal that Anthropic never shipped.
- **Rule 10, stable serialization.** `tools[]` sorted by name, object keys sorted, compact separators, LF, UTF-8. Original tool order is kept in `tools/_index.json`. Measured: claude tool schemas contain zero paths, UUIDs or dates in any version, so rules 1 to 8 are no-ops on this layer and rule 10 is the only one that matters there.
- **Rule 11, codex environment items.** The `<skills_instructions>` developer item is `environment` (it lists the capture home's skills and their `/Users/…` paths and differed by three skills between two sol captures). The `additional_tools` item id (`at_<uuid>`) falls under rule 1.
- **Rule 12, codex `client_metadata`.** Session, thread, turn, window and installation ids fall under rule 1; the remainder is `environment`.

Byte accounting follows the house standard astra's launch section defines: sizes are bytes of the request as sent, decoded from `raw_request_base64`, never a re-serialization; a layer's size is the byte length of its compact serialization and, per probe, the layer sizes plus a stated `other` bucket sum to that probe's request total. Two probes of one cell differ in the messages layer because it carries environment, so every published size names its probe (Round 3b).

### 5. Pairing and attribution

A **pair** is two spans of one cell that are adjacent along one axis with the other axes fixed. Two axes exist: harness version and date.

- **Version pair**: `(model, shape)` fixed, consecutive captured versions, and the same server state on both sides where the profile has one. `claude/opus/2.1.261..2.1.269` (45 changed lines, −2,442 chars in #683's normalized measurement). Consecutive means consecutive *captured* versions for that model; the page lists the versions captured for other models in between.
- **Date pair**: `(version, model, shape)` fixed, consecutive spans. `codex/gpt-5.6-sol/0.154.0/2026-09-10..2026-09-12`.
- **Ambiguous pair**: the version and the server state both moved between the two sides. Published, labelled `attribution: ambiguous`, and excluded from the "what changed in release X" view. Today's certified sol 0.153.4 (7 Sep, etag `3498e390`) to 0.154.0 (13 Sep, etag `45a6c0af`) is one; the uncertified workspace runs supply the clean date pair inside 0.154.0.

The change feed is keyed on canonical text sha changing, and each entry names the axis that moved. The generator never diffs across two axes at once.

### 6. URL scheme

```
/                                                     three numbers, change feed
/requests/claude                                      harness: versions, models, roster, churn
/requests/claude/opus                                 cell timeline: bytes by version stacked by layer, spans, pairs
/requests/claude/opus/2.1.270                         latest span of the cell, six layer tabs
/requests/claude/opus/2.1.270/2026-09-13              snapshot (immutable)
/requests/claude/opus/2.1.261..2.1.269                version pair
/requests/codex/gpt-5.6-sol/0.154.0/2026-09-10..2026-09-12   date pair
/requests/claude/2.1.269                              release: every model, every layer, what moved
/requests/claude/opus/tool-turn/2.1.270               tool-turn shape (first-turn is the default path)
/tools/claude                                         roster by size, added and removed per version
/tools/claude/Artifact                                one tool's schema timeline
/tools/claude/Artifact/2.1.263..2.1.269               tool pair
/prompts/claude/opus                                  alias of /requests/claude/opus#system (the search landing)
/prompts/claude/opus/2.1.270                          the system prompt text alone
/system-message/claude/opus/2.1.270
/changes  /changes.rss  /changes/2026-09-13
/corpus/**                                            raw files, verbatim, CORS
/api/v1/**                                            stable-shape JSON mirror
/method  /corrections  /about
```

Model slugs: `sonnet[1m]` becomes `sonnet-1m`. Versions verbatim. Dates ISO.

### 7. Pages

- **Cell timeline** (`/requests/claude/opus`): a stacked bar per captured version (tools, system, system-message, reminders, envelope, environment, other) with spans drawn as bands across a date axis beneath, colour changing where the canonical sha changes; the pairs table with per-layer deltas; the latest span's text below the fold.
- **Snapshot / span**: header with cell, dates, bytes per layer, `efforts_observed`, `effort_invariance`, `server_state`, bundle ids, TM commit. Tabs per layer. Tools tab is a table (name, bytes, changed-since-previous) expanding to the schema. Variants side by side with `cause`.
- **Pair**: summary line, then per-layer unified diffs, largest hunk first, hunks collapsible, moved hunks marked, one permalink per hunk, `attribution` badge. The OG image is the summary line and the largest hunk.
- **Release**: rows per model, deltas per layer, union of hunks, ambiguous pairs listed separately.
- **Tool**: bytes by version, per-version diff, which models carry it.
- **Homepage**: the three numbers (bytes before the first word per harness, latest versions), then the change feed.

### 8. Raw data

`corpus/**` is served verbatim: Markdown for prose layers, JSON for schemas and envelopes, `.diff` per pair per layer, `index.json`, per-cell `timeline.json`, per-snapshot `snapshot.json` with the replacement log and provenance. `/api/v1/` mirrors it with a versioned shape. `/changes.rss` and `/changes.json`. A `corpus.tar.zst` per release tag. Code MIT, corpus data CC BY 4.0 with a rights notice for vendor text and a stats-only publish flag if any text must be withdrawn.

### 9. Repository, generator, CI

```
know-more-context/
  corpus/<harness>/<model>/<version>/<date>/   system.md  system-message.md  reminders.md
                                               tools/_index.json  tools/<Name>.json
                                               envelope.json  environment.json  snapshot.json
  corpus/<harness>/<model>/timeline.json
  corpus/index.json  corpus/scan-report.json
  diffs/<harness>/<model>/<a>..<b>/<layer>.diff
  generator/  extract.py  normalize.py  identity.py  pairs.py  diff.py  validate.py
              fixtures/   (three synthetic cells: one variant, one date pair, one schema-12 bundle with a B probe)
  site/       Astro, static output, Cloudflare Pages; islands only where needed
  .github/workflows/validate.yml  publish.yml  candidates.yml
```

Generator, per probe: decode raw bytes; extract per profile (§3), reading both codex locations; normalize (§4) with a replacement log; compute per-layer canonical shas; group into snapshots, spans, variants (§2); build pairs (§5); write corpus and diffs; write `index.json`. Inputs are the bundle directory **and** the workspaces' `transport.json` files, both local. The archival reader iterates original probes and never goes through `read_baseline_bundle`, which drops the B probe of bundles at schema 12 or below (verified in `baseline_evidence.py`).

CI has no provider credentials and no bundles. `validate.yml` on every PR: regenerate `diffs/` and `index.json` from the committed `corpus/` and `git diff --exit-code`; run generator tests on the fixtures; assert every snapshot has a non-empty `system` unless the profile marks it `absent`; assert no `mcp__` name in any `tools/`; assert layer sizes plus `other` equal the request total. `publish.yml` on main: build, deploy. `candidates.yml` on a new span or pair: open a GitHub issue with the rendered images and a bulleted fact list, no prose, per the operating rule in astra's launch section; CI never posts to X.

Byte-identical regeneration: running the generator twice on the same inputs produces identical `corpus/` and `diffs/` trees, enforced by a test that hashes both trees.

### 10. Daily capture

Because the prompt moves on a multi-day cadence with no release, the corpus needs a heartbeat: one first-turn probe per (harness, model) per day, at the installed version, into the workspaces, without certification. The generator reads them as snapshots. A day with identical text extends the span; a day with new text opens one and fires a candidate. Certified bundles remain the reference points; the heartbeat is what makes the date axis continuous. This is a v1 requirement, because without it the sol change would have been visible only as an ambiguous version pair.

### 11. v1 and later

**v1:** six layers; both codex extraction locations; rules 1 to 12; snapshots, spans, variants, effort invariance; version and date pairs with attribution; cell, snapshot, pair, release, tool pages; `/prompts` alias; change feed and RSS; raw surface; validate and publish CI; daily heartbeat capture; scan report.

**Later:** `/compare` across harnesses; badges; `/api/v1` beyond the mirror; provider `usage` token counts where a captured response carries them; tool-turn cumulative cost views; an equivalent of `x-models-etag` for claude and grok if one exists; eval and run pages.

### 12. Acceptance criteria

1. Every published snapshot resolves to one canonical text per layer or to a declared variant set with a `cause`, and two snapshots of one cell on different dates with different text are two spans, never collapsed and never called variants.
2. The normalizer maps two captures of one snapshot to one text (fixture: two claude captures differing only in paths, ids and build suffix), and does **not** map two captures on two dates with different instruction text to one text (fixture: sol 10 Sep and 13 Sep).
3. A codex fixture in each extraction shape (`instructions` and developer items) yields a non-empty `system`; a codex first-turn probe with neither fails the build.
4. A haiku fixture carrying `mcp__claude_ai_Gmail__authenticate` publishes 35 tools, not 41, and the six names appear under `environment`.
5. Every cell with two or more observed efforts and one text reads `effort_invariance: proven`; every other cell reads `single`; a cell with two texts at two efforts on one date fails the build with `EffortSplit`.
6. The claude opus 2.1.261 to 2.1.269 version pair renders 45 changed lines and −2,442 chars in the `system` layer under the stated unit, and its page names the versions captured for other models between them.
7. The codex gpt-5.6-sol 0.154.0 date pair 10 Sep to 12 Sep renders as a date change with the binary unchanged, `attribution: server`, and the 0.153.4 to 0.154.0 version pair for sol renders `attribution: ambiguous`.
8. For every probe, layer byte sizes plus `other` equal that probe's request byte total, and the compact round trip of the decoded body is byte-identical to the captured bytes. Cell and span pages publish the canonical probe's figures by bundle id and label, plus the min..max range across the span's probes; no percentage is attributed to a cell without a probe named (see Round 3b).
9. A schema 12 fixture bundle with a B probe yields three probes in the archival read.
10. Regenerating from unchanged inputs produces byte-identical `corpus/` and `diffs/` trees.
11. The site builds with no provider credential and no bundle present.

### 13. What in #683 is now wrong

- **"A page per (harness, model)"** as the deliverable. The unit is the request snapshot with six layers; the model page is a timeline of them.
- **"Every published cell resolves to one canonical prompt or to a declared set of variants."** Wrong as keyed. A cell without a date axis has, for sol at 0.154.0, three different texts in five days that are revisions, not variants. Criterion 1 replaces it.
- **"The `role: system` message. Distinct from the system prompt and out of scope."** It is 14,258 bytes for opus against 9,661 for the system prompt. In scope as its own layer.
- **"Astro on GitHub Pages."** Astro stays; Cloudflare Pages replaces GitHub Pages for uncapped bandwidth, `_headers` and `_redirects`, and a later Worker on the same domain.
- **"Model dominates; version is the secondary axis."** Model dominates size. Date is the axis on which the prompt was seen to change with no version change, and it is missing from the issue.
- **The 88-cell count and the 80-of-88 normalization result** stand as measurements of the system layer only. They say nothing about the tool layer, which is where 84% of the bytes are.
- **"Token counts excluded."** Retained for v1; the unit is bytes as sent, and provider `usage` is a later addition where a captured response carries it.
- **The sanitization exclusion** stands, and `scan-report.json` ships anyway because it is free.
- **Not claimed anywhere:** that the "Autonomy and persistence" section was introduced by the sol change. It is present in every 0.154.0 variant including luna. The sol change is the +2,582 chars, the `clock` namespace, and the permission section my scan flagged†; the pair page shows the hunks and the copy says nothing the hunks do not.

## Round 3b: byte accounting, corrected

**My 167,710 was the wrong probe.** It is claude 2.1.270 opus, effort low, label a1, bundle `54c032d5`, and that bundle's cell reads `request_shape: tool-turn`. My glob took the first opus bundle at 2.1.270 without reading the shape, which is the same mistake the codex 2,203-char figure came from in Round 1, now on claude. The first-turn opus probes at 2.1.270 are Stuart's five, and my rerun with the exact method reproduces them byte for byte (medium a1 and b: 164,768, tools 84.48%, msgs 9.37%, sys 5.87%, other 461; medium a2: 162,730; low a1 and a2: 162,669). The compact round trip is byte-identical to the captured bytes on every probe, so the accounting is exact. Round 3 §1's "167,710 bytes as sent: tools 141,538 (84.4%), messages 16,053 (9.6%), system 9,661 (5.8%)" is a tool-turn probe and is superseded by this section; the shape field on the cell is what the generator must read, and criterion 3's spirit applies to shape as it does to extraction location.

**Adopted.** There is no single percentage for a cell. Two probes of one cell (medium a1 vs a2) differ by 2,038 bytes in the messages layer because it carries environment. Criterion 8 is now per probe (edited in place above). The Round 1 and Round 2 "chars" figures produced with default `json.dumps` separators are superseded wherever a byte figure exists; the "86%" in the Round 2 launch post is withdrawn and the safe claims are: tools are about 84% of a Claude Code first-turn request, the system prompt is under 6%, and the `Artifact` schema alone is roughly five times the opus system prompt.

**Cell-level statistic: the canonical probe, named, with the span's range beside it.** Definition: the earliest-captured `a1` probe whose normalized text equals the span's canonical text, ties broken by bundle id; the page and every card carry its bundle id and label. Reasons: it is a request that was actually sent, so a reader can reproduce the number from one bundle; it links to a sha; and it does not move when a later probe is added to the span. A median is a number no request ever had, and a range is not a number a post can carry. The range (min..max bytes and percentages across the span's probes) is published beside the canonical figure so the reader sees that the spread is environment, not vendor.

**Rounding rule for copy.** Percentages in prose and on cards are rounded to whole numbers ("about 84%"); exact bytes appear only with the probe named. The generator enforces it: `index.json` carries `canonical_probe`, `range`, and a `display` block with the rounded values, and cards read only `display`.

## Round 4: capability reopens the key

Appends to Round 3. Every number below was measured this session from the bundle set (138 cells across both shapes, 114 first-turn), with `mcp__*` tools excluded and tools serialized compact with sorted keys. Numbers marked † were measured once.

### R4.1 What the bundles show

**The Artifact flag is per request, not per day.** Two normalized tool sets recur across every claude model at 2.1.269 and 2.1.270: `f1f8e500` (Artifact 50,163 bytes, actions `upload_asset`, `list_assets`, `read_asset`, `delete_asset`, properties `after`, `asset_id`) and `60898f80` (Artifact 48,113 bytes, without them). Haiku and default carry the same split under their own set ids because their rosters differ. The two sets flip between consecutive probes of one run: 2.1.270 opus[1m] bundle `89e04193` has a1 on `f1f8e500` and a2 on `60898f80`; bundle `97333854` has a1 and b on `60898f80` and a2 on `f1f8e500`. Same binary, model, effort, day, session. The flag is decided per request. It is visible at 2.1.267 (sonnet, Artifact 39,368 vs 37,380) and 2.1.268 (opus[1m], 42,039 vs 44,027), so it has been toggling since at least 10 Sep. It shows in tool-turn cells identically.

**Sixteen claude cells, one codex cell and six grok cells have more than one tool set.** The claude sixteen are the Artifact flag plus two others: 2.1.250 haiku has `SendUserFile` present in one run and absent in another on the same day, system text identical; and 2.1.250 `best` has one probe (bundle `c11309f1`, a1) with six tools missing (`Artifact`, `EndConversation`, `Monitor`, `PushNotification`, `RemoteTrigger`, `SendFeedback`), `CronCreate` and `WebFetch` descriptions different ("durable persistence is not available" against "persist to .claude/scheduled_tasks.json"), and a different system text. The codex cell is gpt-5.6-sol 0.154.0, where the 13 Sep set adds `clock/sleep` and `functions/request_user_input_async` and changes `functions/exec`: the server revision from Round 2b, now seen in the tool layer. The grok six are noise: `send_feedback` differs between probes by 7-character hex tokens at equal length, which are run-scoped identifiers embedded in the schema. No grok cell has a real tool-set split.

**#683's eight variant cells.** With the `cc_version=2.1.246.a33` form normalized correctly, nine first-turn cells carry more than one system text. They fall into three kinds, and only one is what #683 called them:

| kind | cells | co-varies with tool set | disposition |
| --- | --- | --- | --- |
| capability profile | claude 2.1.250 `best` (extra paragraph, `<total_tokens>15000000 tokens left</total_tokens>`) | yes: six tools absent, two descriptions changed | a real alternative, cause `capability` |
| server revision | codex 0.154.0 gpt-5.6-sol (10 Sep vs 13 Sep) | yes: two tools added, one changed | two spans, not a variant |
| environment | codex 0.150.1 terra, 0.152.0 sol, 0.152.1 sol, 0.153.0 sol, 0.153.2 sol, 0.153.4 terra, 0.154.0 astra: a `<plugins_instructions>` block and a skills list naming the capture home's installed plugins (`product-design:audit`, `plugin-management`, `deep-research-work`) inside the main developer item | no: tool set identical | normalizer rule, not a variant |

So the model #683 inherited was describing a capability profile in exactly one cell and environment leakage in six. The variant concept is renamed and generalised below, and the claude Artifact flag is the same phenomenon at scale: a capability decided outside the binary, per request, changing 84% of the request.

### R4.2 Capability: alternative, not key, not provenance

Three shapes were weighed.

- **Key dimension.** `(harness, version, model, shape, capability-set)`. Every flag combination is a new cell; two flags give four cells per version per model; the URL tree multiplies and the timeline fragments. Unusable, and it hides the fact that the flags are one binary's behaviour.
- **Provenance.** Record the tool set id on the snapshot and publish one canonical set. Honest about which probe is shown, dishonest about the cell: "what tools does 2.1.270 send" has two answers and a reader would see one.
- **Alternatives per layer.** The key stays `(harness, version, model, shape)` plus date. A snapshot has, per layer, an **alternative set**: the distinct normalized values observed, each with a stable id, a probe count and probe ids, and one marked canonical. A layer is `single` or `multi`. This is the shape chosen. It survives multiplication because alternatives live inside the snapshot and never enter the URL tree, and it survives the honesty test because a `multi` layer is always shown as multi.

The old `variants` block becomes `alternatives` and applies to every layer. Each alternative carries a `cause`:

```
capability        same binary, same day, values differ; tool set or system text co-varies across probes
server-revision   different dates, same binary (a span boundary, published as two spans, never as alternatives)
environment       differs only in positions the normalizer should cover; a bug in the corpus, fails the build
unknown
```

Claude 2.1.250 `best` reads `system: multi (2), tools: multi (2), cause: capability`, with the two alternatives linked because they came from the same probes. 2.1.270 opus reads `system: single, tools: multi (2), cause: capability`.

**Tool-set identity.** TM already mints `wire_exchange.tools_set_hash` over the raw component set (`wire_store.py:148`, `dao_statements.py:398`). The corpus publishes its own `tool_set_id`, the sha of the normalized, name-sorted, compact, `mcp__`-free set, so that grok's `send_feedback` ids and claude's connected MCP servers do not mint spurious sets, and records TM's `tools_set_hash` per probe as provenance. Two ids are comparable on one page: `/tools/claude/sets/f1f8e500..60898f80` renders the **capability delta**: tools added, tools removed, and per changed tool the added and removed `action` enum values, properties, and description paragraphs. That delta is a first-class object with its own id, so the same flag observed on ten cells is one delta linked ten times, not ten diffs.

**Pairing with alternatives.** A pair diffs like with like: when both sides are `multi`, alternatives are matched by capability-delta signature (the "assets on" side of 2.1.269 against the "assets on" side of 2.1.270), and the pair page shows the per-alternative diffs plus a line saying whether the delta itself changed. When one side is `single`, the pair is drawn against the canonical alternative and the page says so. The canonical alternative is the most observed one, ties broken by earliest probe, and the canonical probe of Round 3b is the canonical alternative's earliest a1.

### R4.3 New normalizer rules

- **Rule 13, codex environment inside the instructions item.** The `<plugins_instructions>…</plugins_instructions>` block and the skills list (`- name: description (file: rN/…)` lines and the `rN = <path>` table) are cut from `system` and placed in `environment`. This collapses the six codex cells above.
- **Rule 14, grok `send_feedback` identifiers.** The 7-character hex tokens in `send_feedback` are replaced with `<id>`. This collapses the six grok cells.

After rules 13 and 14, the cells with a real `system` alternative set are one (claude 2.1.250 `best`), and the cells with a real `tools` alternative set are the claude Artifact and SendUserFile flags plus that one.

### R4.4 The cell page when a layer is multi

Above the layer tabs, a banner: **"2 tool sets observed on 2.1.270 (opus): 5 of 8 probes with Artifact assets, 3 without"**, with the capability-delta strip inline: `Artifact +4 actions (upload_asset, list_assets, read_asset, delete_asset) +2 properties (after, asset_id)`. A toggle on the tools tab switches between alternatives; the table marks the rows that differ. The timeline chart draws the tools band split into two sub-bands where a cell is multi, proportional to probe counts, so a flag rolling out reads as one sub-band widening over versions. The set ids link to `/tools/claude/sets/<id>` and the delta links to its page. Nothing is hidden behind the toggle: the summary line and the strip carry the whole fact.

### R4.5 Acceptance criteria, changed again

- **1** becomes: every snapshot resolves, per layer, to one canonical value or to a declared alternative set with a `cause`; `environment` as a cause fails the build.
- **New 12:** the claude 2.1.270 opus first-turn snapshot publishes two tool sets, `f1f8e500` and `60898f80`, whose capability delta is four `action` values and two properties on `Artifact`, and the snapshot is `tools: multi, cause: capability`.
- **New 13:** claude 2.1.250 `best` publishes `system: multi` and `tools: multi` with linked alternatives and cause `capability`; the `<total_tokens>` line is in the alternative's text.
- **New 14:** the six codex cells listed in R4.1 publish `system: single` after rule 13, and the six grok cells publish `tools: single` after rule 14.
- **New 15:** a flag observed on two versions produces one capability-delta object referenced from both, not two.
- **New 16:** every probe records TM's `tools_set_hash` and `system_set_hash` beside the corpus ids.
- **4** (haiku `mcp__` fixture) stands; **5** (effort) stands; **7** (sol date pair) gains "and the pair's tools layer shows `clock/sleep` and `functions/request_user_input_async` added"; **8** stands as per probe.

### R4.6 Codex and grok

Codex shows the phenomenon at day granularity, not per request: no codex cell has two tool sets on one day, and the one split is the 10 to 13 Sep server revision that changed instructions and tools together. Grok shows none once `send_feedback` ids are normalized. Looking further is the heartbeat from Round 3 §10 with `tool_set_id` computed per probe: for codex, hash the `additional_tools` namespaces per request and watch for two ids under one `x-models-etag`; for grok, hash `tools[]` after rule 14 and watch the same way; for claude, the flag is already visible and the heartbeat measures its rollout rate as the share of probes on `f1f8e500` per day.

### R4.7 What this does to #683

"8 cells retain real content variants" is one capability profile, one server revision, and six environment leaks. "80 of 88 collapse to a single canonical prompt" understates the collapse once rules 13 and 14 exist. And the tool layer, absent from the issue, is where the same binary sends two different capability sets to two consecutive requests, which no extraction of that binary can see.

### R4b. Scan results absorbed

Stuart's first-turn scan: 106 tool-carrying cells, 16 (15%) with tool-set content differing across probes of one cell, all claude, across 2.1.250, 2.1.267, 2.1.268, 2.1.269 and 2.1.270, driven by `Artifact` in 13, by `CronCreate` and `WebFetch` in 2.1.250 `best`, and by `SendUserFile` membership in 2.1.250 haiku. Grok's `send_feedback` difference is retracted as a capability; it is a per-run id. Codex shows day-granularity revision only. The alternative-set model and rules 13 and 14 absorb this unchanged.

Two clarifications to the criteria:

- **New 17:** on the current bundle set, the generator reports exactly 16 of 106 first-turn tool-carrying cells as `tools: multi, cause: capability`, every one claude, and zero codex or grok cells. The scan is a fixture test, so a normalizer regression that mints a grok alternative or loses a claude one fails the build.
- **Rule 14 clarified:** `send_feedback`-style per-run identifiers are normalized before hashing, so they never mint an alternative. Any residue that survives normalization and differs across probes of one snapshot is classified `cause: environment`, and criterion 1 fails the build on it. The two mechanisms are the same rule seen from both sides: normalize what is known, refuse what is not.

### R4c. Census reconciled; criterion 17 rewritten; rule 14 withdrawn

Criterion 17 as written ("16 of 106, all claude, zero grok") was self-contradictory: three of the sixteen were the grok cells. Withdrawn. Stuart's per-harness census: claude 13 of 90 tool-carrying first-turn cells divergent (14.4%), codex 0 of 7, grok 3 of 9 by crude hex normalization.

**Rule 14 is withdrawn as a rule.** The grok `send_feedback` difference is the capturing run's workspace path with the run UUID inside the tool description (`…/4e45b4a7/e1b7f196-a8b1-4cac-…` against `…/cf2c66a6-946d-43ed-…`). That is rules 1 and 3 applied to the tool layer, not a new pattern. Round 2's "claude tool schemas carry zero paths or UUIDs" stands for claude and does not extend to grok, so rules 1 to 8 run over every layer including tools.

**Proof of (b).** Rules 1 and 3 applied to grok tool JSON, all 12 grok cells across both shapes: raw sets 3, 2, 2, 2 for 1.0.25 grok-4.6 and 1.0.30 grok-4.5/4.6 in both shapes; normalized sets 1 in every cell; zero residue. Measured this session, not independently checked.

**Criterion 17, two assertions:**
- **17a, capability divergence:** on the current bundle set the generator reports exactly 13 of 90 claude first-turn tool-carrying cells as `tools: multi, cause: capability` (versions 2.1.250, 2.1.267, 2.1.268, 2.1.269, 2.1.270) and 0 of 7 codex cells.
- **17b, normalizer completeness:** after rules 1 to 8 run over the tool layer, 0 of 9 grok first-turn tool-carrying cells are divergent, and no grok probe mints an alternative. Status: passing on my run above; Stuart's crude scan leaves the three standing, so the fixture is the proof, not the census.

The publishable prevalence figure is 14.4% of claude tool-carrying first-turn cells (13 of 90), never a share of all cells.
