---
title: gstack — Garry Tan's Claude Code skills pack + headless browser daemon
type: research
tags: [claude-code, skills, agentic-workflow, bun, playwright, cli-architecture, prompt-injection-defense, multi-host, garry-tan, yc]
summary: 23 opinionated slash-command skills (Markdown) plus a Bun-compiled headless Chromium daemon that give Claude Code a sprint-structured "virtual engineering team" and sub-second browser control.
status: active
source: github-researcher
confidence: high
created: 2026-04-23
updated: 2026-04-23
---

# gstack — Garry Tan's Claude Code workflow pack

- **Repo:** https://github.com/garrytan/gstack
- **Author:** Garry Tan (CEO, Y Combinator). Commits authored as `Garry Tan <garrytan@gmail.com>`.
- **Created:** 2026-03-11. Last push 2026-04-22. Version 1.6.1.0.
- **Stars:** ~80,441. **License:** MIT.
- **Primary language:** TypeScript on Bun. Skills are Markdown.

## Executive Summary

gstack is a monorepo that turns Claude Code (and nine other coding agents) into a structured sprint team through 23 opinionated `SKILL.md` files, plus a compiled `browse` binary that runs a persistent headless Chromium daemon for sub-second page interaction. The Markdown skills are declarative; the browser and supporting CLIs are a Bun-compiled runtime. It ships with an aggressive safety posture: cookie decryption only via macOS Keychain with user approval, a layered prompt-injection defense for its sidebar agent (ONNX classifier + Haiku transcript vote + canary token + verdict combiner), and a dual-listener HTTP architecture that physically separates local and tunneled command surfaces.

The project is also a claim about AI-assisted productivity: Tan reports a ~810× logical-LOC-per-day rate in 2026 vs 2013, and frames each skill as replacing a specialist role (CEO, eng manager, designer, QA lead, SRE, CSO, release engineer, debugger).

## Architecture

### Two halves

1. **Markdown skills (no compile step).** Each top-level directory (`office-hours/`, `review/`, `qa/`, `ship/`, `cso/`, `learn/`, ...) contains a `SKILL.md` with YAML frontmatter (`name`, `description`, `allowed-tools`, `triggers`, `preamble-tier`, `version`) and prose instructions. Claude Code reads these at skill-load time. ~2k-line skill files are normal (`office-hours/SKILL.md` = 2,121 lines; `review/SKILL.md` = 1,753; `SKILL.md` root = 45,977 bytes).
2. **Bun/TypeScript runtime.** `browse/src/server.ts` (2,835 LOC), `browse/src/cli.ts`, host adapters, and the doc generator are compiled with `bun build --compile` to ~58 MB single binaries. No `node_modules` at runtime.

### The browse daemon (the genuinely novel part)

Persistent localhost Chromium, addressed over HTTP:

```
Claude tool call → compiled CLI → POST localhost:PORT → Bun.serve → Playwright CDP → Chromium
                   (reads .gstack/browse.json: pid, random port 10000-60000, bearer token, binaryVersion)
```

- First call ~3 s (cold start). Every subsequent call ~100-200 ms. Auto-shutdown after 30 min idle.
- `.gstack/browse.json` is atomic tmp-rename write, mode `0o600`. Contains `binaryVersion = git rev-parse HEAD`; on mismatch the CLI kills and respawns the server (eliminates the stale-binary bug class).
- **Random port 10000-60000, retry on collision.** Deliberate: lets 10 Conductor workspaces each run their own daemon with zero config. The old 9400-9409 scan broke in multi-workspace setups.
- **Health-check is the primary liveness signal** because Bun-compiled binaries have unreliable PID-based process detection on Windows.
- Logging uses three circular ring buffers (console / network / dialog, 50k entries each), flushed async to disk every 1s so request handling never blocks on I/O.

### Dual-listener tunnel architecture (v1.6.0.0)

When a user runs `pair-agent --client`, ngrok is exposed. Rather than rely on header inference (ngrok headers drift; local proxies can forge), gstack binds **two separate TCP sockets**:

- Local listener (127.0.0.1): full surface — `/command`, `/cookie-picker`, `/health` (with token delivery), `/tunnel/{start,stop}`, etc.
- Tunnel listener (127.0.0.1 bound lazily, forwarded by ngrok): allowlisted paths only — `/connect`, `/command` with scoped tokens and a command allowlist, `/sidebar-chat`. Everything else returns 404.

Security property comes from physical port separation, not header checks. Tunnel denials are written to `~/.gstack/security/attempts.jsonl` (rate-capped 60/min). SSE streams use an HttpOnly `gstack_sse` cookie (EventSource cannot send `Authorization`), scoped by module boundary — `sse-session-cookie.ts` has no imports from `token-registry.ts`.

### The ref system (`@e1`, `@c1`)

Playwright `Locator`s, not DOM mutation, keyed by ARIA snapshot:

```
snapshot -i → accessibility.snapshot() → walk ARIA tree →
              assign @e1, @e2 sequentially → build getByRole(role,{name}).nth(i) Locator →
              Map<string, RefEntry{role,name,locator}>
```

Why Locators over DOM attributes: CSP blocks script DOM writes, React/Vue/Svelte hydration strips injected attrs, shadow DOM is unreachable externally. Refs cleared on `framenavigated` (main frame); `resolveRef()` does an async `count()` check before every use (~5 ms) so SPAs that mutate without navigating fail in 5 ms, not after Playwright's 30 s timeout. `@c` is a separate namespace for `cursor: pointer` / `onclick` / `tabindex` elements that don't show in the ARIA tree — custom components framework-rendered as `<div>` but behaviorally buttons.

### SKILL.md template system

`SKILL.md.tmpl` (human prose + `{{PLACEHOLDERS}}`) → `scripts/gen-skill-docs.ts` → committed `SKILL.md`. Placeholders are filled from source-of-truth modules at build time: `{{COMMAND_REFERENCE}}` from `browse/src/commands.ts`, `{{SNAPSHOT_FLAGS}}` from `snapshot.ts`, `{{PREAMBLE}}`, `{{BASE_BRANCH_DETECT}}`, `{{QA_METHODOLOGY}}`, `{{DESIGN_METHODOLOGY}}`, `{{REVIEW_DASHBOARD}}`, etc. Generated files are committed (not built at runtime) because Claude reads `SKILL.md` at skill-load with no build step, and because `git blame` matters.

Freshness gate: `gen:skill-docs --dry-run` + `git diff --exit-code` in CI.

### Multi-host plugin pattern

`hosts/index.ts` registers `HostConfig` records for claude, codex, factory, kiro, opencode, slate, cursor, openclaw, hermes, gbrain. Each is ~45 LOC declaring:

- filesystem roots (`globalRoot`, `localSkillRoot`)
- frontmatter transform (`denylist`/`allowlist`, `stripFields`, `descriptionLimit`)
- `pathRewrites`, `toolRewrites` (swap Claude tool names for host-equivalents)
- `suppressedResolvers` (skip placeholders that don't apply)
- `coAuthorTrailer`, `learningsMode`, `install` strategy

Adding a host is one TypeScript file, zero code changes elsewhere. `Host` union type is derived from the registry (`typeof ALL_HOST_CONFIGS[number]['name']`) so TypeScript catches drift.

## Key Patterns Worth Adopting

1. **Persistent daemon over per-call spawn for anything with state.** 3 s × 20 commands is 60 s of startup waste, and per-call spawn loses cookies, tabs, localStorage, login sessions. Daemon + HTTP + 30-min idle timeout is the right shape for tool-backed agents.
2. **Physical socket separation beats header inference.** Once a request is on the wrong TCP port, it can't reach paths that don't exist there. No amount of `x-forwarded-for` logic matches that guarantee.
3. **Binary version auto-restart.** `git rev-parse HEAD` burned into the binary + compared to the running server's `binaryVersion` on every CLI call eliminates stale-daemon bugs entirely. `browse/dist/.version` is written at build.
4. **Pure command registry with load-time self-check.** `commands.ts` defines `READ_COMMANDS`, `WRITE_COMMANDS`, `META_COMMANDS` as Sets and `COMMAND_DESCRIPTIONS` as a record. Module-load code raises if any command is missing a description or any description is for an unknown command. Server dispatch, doc generation, skill validation, and unknown-command error messaging (Levenshtein suggest + "added in version X" hint) all import from the same module.
5. **Template-generated docs with tiered tests.** Tier 1 (static parse of every `$B` command in SKILL.md against the registry) is free and <5 s; tier 2 (spawn `claude -p` for every skill) is ~$3.85 per run; tier 3 (LLM-as-judge on clarity/actionability) is ~$0.15. Tier 1 runs on every `bun test`, 2+3 gated behind `EVALS=1`. 95% of drift caught for free.
6. **Split-ownership observability.** `session-runner.ts` owns heartbeats (current state); `eval-store.ts` owns partial results (completed state). Neither imports the other — they share via atomic writes. `eval-watch.ts` reads both. All observability I/O is wrapped in `try/catch`; a write failure never fails a test.
7. **Machine-readable test diagnostics.** Every test result emits `exit_reason` (`success|timeout|error_max_turns|error_api|exit_code_N`), `timeout_at_turn`, `last_tool_call`. `jq '.tests[] | select(.exit_reason=="timeout") | .last_tool_call'` becomes a real debugging workflow.
8. **Errors are for agents, not humans.** Every `wrapError()` rewrite adds a concrete next action: "Run `snapshot -i` to see available elements", "Use @refs from `snapshot` instead", "Navigation timed out after 30s. The page may be slow or the URL may be wrong." This is opinionated, but every error becomes self-recovering.
9. **Crash recovery via restart, not reconnect.** On `browser.on('disconnected')` the server exits. The CLI detects a dead server on next command and spawns a new one. Simpler and more reliable than half-dead reconnection logic.
10. **Layered prompt-injection defense, not single-point.** For the Chrome sidebar agent (which has Bash/Read/Glob/Grep/WebFetch and reads hostile pages):
    - L1-L3 content security: datamarking, hidden-element strip, ARIA regex, URL blocklist, trust-boundary envelope.
    - L4 TestSavantAI: 22 MB BERT-small ONNX (int8), local-only, scans page content and tool outputs.
    - L4b transcript classifier: Claude Haiku vote on full conversation shape, gated at 0.40 log-only so clean traffic skips the paid call.
    - L5 canary token: random UUID in system prompt; rolling-buffer detection across `text_delta`, `input_json_delta`, tool args, URLs, file writes. Token leak = deterministic BLOCK + session end.
    - L6 verdict combiner: BLOCK requires two classifiers at WARN (0.60); single-layer BLOCK for tool outputs only (content wasn't user-authored). Opt-in 721 MB DeBERTa-v3 ensemble via `GSTACK_SECURITY_ENSEMBLE=deberta`.
    - Critical constraint: `@huggingface/transformers` v4 needs `onnxruntime-node`, which `dlopen` fails from Bun-compile's temp extract dir. So the ML layers run only in the sidebar-agent Node.js process; the compiled browse binary imports only pure-string pieces (canary, verdict combiner).
11. **Pre-preamble in every skill.** Shared bash block at the top of every `SKILL.md` does: update check, session-count (3+ concurrent flips every skill into "ELI16 mode"), telemetry (opt-in, off by default, jsonl append), learnings count + top-3 search, timeline log, routing-rules presence check, vendoring deprecation detection, checkpoint mode. Means every skill starts from a known environmental baseline without per-skill boilerplate drift.
12. **Voice triggers folded into descriptions at gen time.** Frontmatter `voice-triggers:` YAML list is extracted, prepended into the `description`, then stripped from the emitted frontmatter per host policy. Lets voice-input users say "run a security check" and route to `/cso` without slash-command syntax, while keeping the YAML clean.

## Dependencies

Minimal at runtime: `playwright` + `puppeteer-core` for browser control, `@huggingface/transformers` for ONNX prompt-injection classifiers, `@ngrok/ngrok` for the pair-agent tunnel, `marked` for Markdown, `diff`. `@anthropic-ai/sdk` is a devDependency. Bun ≥1.0, which gives the build native SQLite (for Chromium cookie DB reads), native TypeScript, `Bun.serve()`, and `bun build --compile`.

## Relevance to Helioy

Strong overlap with Stuart's ecosystem; several patterns are directly portable:

- **helioy-plugins ↔ gstack skills.** Same shape — Markdown skills with frontmatter routing rules, invoked as slash commands, shared preamble. gstack's template/resolver system (`scripts/resolvers/`) is a more sophisticated version of what plugin docs need. The "every skill starts with a bash preamble that records telemetry, counts sessions, loads learnings" pattern is exactly the pre-work helioy-plugins skills could standardize instead of per-skill drift.
- **helioy-bus ↔ `/pair-agent`.** gstack's pair-agent is cross-agent coordination via shared browser with scoped tokens, tab isolation, and rate limiting. helioy-bus is cross-agent coordination via mail/warroom. Design constraint worth stealing: **root tokens never cross the tunnel listener**. In bus terms, an agent's full registration/control token should never be exposed to peers — they should get scoped capability tokens.
- **nancyr ↔ browse daemon model.** A long-lived Bun/Rust daemon addressed over localhost HTTP with random ports + state file is a natural shape for nancyr's orchestration surface. The `binaryVersion` auto-restart pattern is especially relevant for a Rust daemon that agents cache a handle to across sessions.
- **context-matters / attention-matters ↔ `~/.gstack/projects/{SLUG}/learnings.jsonl`.** gstack stores per-project learnings with keyword search (`gstack-learnings-search --limit 3`) injected into every skill's preamble. This is a thin, file-based retrieval layer that cm's scoped recall already does better, but the **shape of integration** — inject top-K from the primary memory into every skill's context on start — is a pattern cm could codify as a skill-preamble helper.
- **fmm ↔ `browse/src/commands.ts` registry.** The load-time validation ("every command has a description, every description names a real command") and the dispatch categorization (READ / WRITE / META) are the kind of structural truth fmm surfaces for a codebase. An fmm equivalent could assert registry-vs-dispatch coherence as a codebase health check.
- **markdown-matters ↔ SKILL.md template system.** mdx is a Markdown knowledge base; gstack's `gen-skill-docs.ts` is a generator that fills placeholders from source-of-truth code modules. If mdx ever needs "these KB pages embed code references that must stay fresh", the same dry-run + `git diff --exit-code` CI gate is the right mechanism.
- **Prompt injection defense.** Helioy tools that scrape web content (any future brain-aware web-research skill) should look at `browse/src/content-security.ts`, `security-classifier.ts`, `security.ts` directly. The canary-token + verdict-combiner combo is a concrete, implementable baseline that's better than "trust the page".

Borrowable immediately without a full rewrite: the **pre-preamble skill bash block**, the **template + resolver doc generator**, the **random-port + state-file + bearer-token + version-restart pattern** for any persistent tool daemon, and the **tiered eval model** (free static / mid E2E / LLM judge).

## Selected File Paths

- `/tmp/gh-research/garrytan-gstack/ARCHITECTURE.md` — 420 lines, authoritative on the daemon, dual-listener, ref system, template system, logging, security
- `/tmp/gh-research/garrytan-gstack/ETHOS.md` — Boil the Lake, Search Before Building (3 layers of knowledge + "Eureka Moment"), User Sovereignty
- `/tmp/gh-research/garrytan-gstack/browse/src/commands.ts` — 284 LOC command registry with load-time validation + Levenshtein unknown-command suggester
- `/tmp/gh-research/garrytan-gstack/browse/src/server.ts` — 2,835 LOC Bun.serve dispatch
- `/tmp/gh-research/garrytan-gstack/browse/src/security.ts`, `content-security.ts`, `security-classifier.ts` — prompt-injection defense
- `/tmp/gh-research/garrytan-gstack/hosts/index.ts` + `hosts/claude.ts` — 10-host plugin system
- `/tmp/gh-research/garrytan-gstack/scripts/gen-skill-docs.ts` — 660 LOC template pipeline
- `/tmp/gh-research/garrytan-gstack/SKILL.md.tmpl` + generated `SKILL.md` — root skill with routing rules for every slash command
- `/tmp/gh-research/garrytan-gstack/office-hours/SKILL.md` (2,121 LOC) and `review/SKILL.md` (1,753 LOC) — representative skill files
- `/tmp/gh-research/garrytan-gstack/CHANGELOG.md` — 313 KB; each release documents the plan review that preceded it
- `/tmp/gh-research/garrytan-gstack/bin/` — 37 thin CLI helpers (gstack-config, gstack-learnings-search, gstack-telemetry-log, gstack-timeline-log, gstack-update-check, gstack-uninstall, etc.)

## Sources Consulted

README.md, ARCHITECTURE.md, ETHOS.md, DESIGN.md, AGENTS.md, CLAUDE.md, CHANGELOG.md (partial), CONTRIBUTING.md (referenced), package.json, hosts/index.ts, hosts/claude.ts, scripts/gen-skill-docs.ts (first 150 LOC + structure), browse/src/commands.ts (full), SKILL.md.tmpl (first 80 LOC), office-hours/SKILL.md (first 120 LOC — preamble shape), learn/SKILL.md (first 80 LOC), setup (first 80 LOC), slop-scan.config.json, git log authorship.

## Open Questions

- Cross-model benchmark details: `gstack-model-benchmark` claims LLM-as-judge comparison across Claude, GPT (Codex CLI), Gemini, with provider auto-detection. The implementation and its prompt-fairness controls would be worth reading before anything helioy-side adopts the pattern.
- `/learn` and `~/.gstack/projects/{SLUG}/learnings.jsonl`: the exact retrieval scoring (keyword only vs semantic) and how learnings are injected into skill preambles beyond top-3 count.
- Taste memory for `/design-shotgun` (`gstack-taste-update`, 5%/week decay): relevant if any Helioy component needs persistent preference learning per-project without vectors.
- `canary/` directory — post-deploy SRE monitoring. Unread; the approach to "watch prod for console errors and perf regressions as a shipped skill, not a hosted service" could be interesting.
- The `benchmark-models/` directory vs root `benchmark/` — probable split between page-benchmark and cross-model-benchmark but not verified.
