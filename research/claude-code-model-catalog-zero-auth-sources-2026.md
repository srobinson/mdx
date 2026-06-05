---
title: Zero-Auth Sources for the Claude Code Model Catalog
type: research
tags: [claude-code, models, anthropic, model-catalog, zero-auth, models.dev, litellm, openrouter, piebald]
summary: No project tracks Claude Code's own /model picker set in real time; the closest is Piebald-AI/claude-code-system-prompts (per-version binary extract, ~2wk lag). For the general Anthropic API catalog, models.dev api.json and LiteLLM's raw JSON are the best zero-auth feeds.
status: active
confidence: high
created: 2026-07-19
updated: 2026-07-19
---

## Executive Summary

There is no community project that tracks the Claude Code *picker* catalog (the curated `/model` subset with effort tiers) in near real time as a clean JSON feed. The single project that even attempts the Claude-Code-specific catalog is **Piebald-AI/claude-code-system-prompts**, which extracts the model-catalog reference doc from the CLI binary per version (currently ~2 weeks behind npm). For the **general Anthropic API model list** (which is a superset of, and differs in naming from, the Claude Code picker), the best zero-auth feeds are **models.dev** (`api.json`, community-maintained, fresh) and **LiteLLM's** `model_prices_and_context_window.json` (raw GitHub, updated multiple times daily, fastest to pick up new IDs). **OpenRouter's** `/api/v1/models` is zero-auth and fresh but uses its own slug convention. The **Anthropic docs model-overview page** is the authoritative human-maintained zero-auth surface but is MDX, not JSON.

Critical distinction that runs through everything below: **API model IDs != Claude Code picker set**. Claude Code's picker is a curated subset with effort tiers (low/medium/high/xhigh/max, plus `opusplan`), and its embedded catalog even carries templated placeholders for unreleased models. None of the general feeds capture that curation.

## Detailed Findings

### The Claude-Code-specific catalog (the thing actually asked for)

**Piebald-AI/claude-code-system-prompts** — `system-prompts/data-claude-model-catalog.md`
- URL (raw): `https://raw.githubusercontent.com/Piebald-AI/claude-code-system-prompts/main/system-prompts/data-claude-model-catalog.md`
- Zero-auth: Yes (public GitHub, raw file).
- What it is: the actual model-catalog reference document that ships embedded inside the Claude Code binary, extracted per CLI release. This is the closest thing in existence to "what the latest Claude Code knows about models," because it is literally Claude Code's own embedded catalog doc. It includes current/legacy/deprecated/retired tables, a resolution guide, and the effort-tier vocabulary.
- Update mechanism: maintainer re-extracts on new Claude Code npm releases and commits with messages like "v2.1.197 (+21,695 tokens)". Commit cadence is irregular (1-18 day gaps).
- Observed freshness/lag: latest catalog commit at the time of research was **v2.1.197 (2026-06-30)**, while npm `latest` was **2.1.215**. So roughly a two-week / ~18-version lag. Not real time.
- Caveat: at v2.1.197 the file still carried template placeholders (`{{FABLE_NAME}}`, `{{MYTHOS_NAME}}`, `{{SONNET_NEXT_NAME}}`) for models the binary had staged but not activated. That is genuine signal about Claude Code's staged rollout, but it means the file is not always a clean list of live IDs.
- Maintenance health: actively maintained through at least June 2026; the repo also extracts all system prompts and tool descriptions per version, so it has a reason to keep pace.
- Sibling project: **x1xhlol/system-prompts-and-models-of-ai-tools** (`Anthropic/Claude Code/`) mirrors prompts/tools but is prompt-focused, not a structured model catalog.

**Note on the user's own extractor**: `scripts/extract-claude-model-catalog.py` in this repo already does the binary string-pool scrape and is explicitly self-described as "verification-only" and fragile (pinned to the 2.1.214 build signature). Piebald is the external maintained analogue to that same approach and carries the same fragility class, just crowd-maintained.

### models.dev (general API catalog, best structured JSON)

- Zero-auth JSON endpoints: `https://models.dev/api.json` (full), `https://models.dev/models.json`, `https://models.dev/catalog.json`. Human page: `https://models.dev/labs/anthropic/`.
- Zero-auth: Yes.
- What it lists: **Anthropic API model IDs** (not the Claude Code picker). Rich per-model fields: `id`, `name`, `family`, `reasoning`/`reasoning_options`, `tool_call`, `temperature`, `knowledge`, `release_date`, `last_updated`, `modalities`, `limit` (context/output), `cost`. Also carries per-provider variants across ~40 providers.
- Freshness: fresh. The `labs/anthropic` view lists `claude-fable-5`, `claude-sonnet-5`, `claude-opus-4-8`, `claude-haiku-4-5`, down through legacy (opus-4-1, sonnet-4-x, 3.x). Newest entry Sonnet 5, release_date 2026-06-30. (A raw `api.json` fetch that appeared to omit the Claude 5 family was a truncation artifact of reading a very large file, not an actual staleness gap — the generated site view proves the data is present.)
- Update mechanism: community-contributed **TOML files per provider/model**, validated by GitHub Actions (Zod schema via `validate.ts`) on every PR, then `generate()` compiles the TOMLs into the JSON. So freshness depends on someone opening a PR; typically days behind a launch, not real time.
- Maintenance health: active. Repo moved from `sst/models.dev` to **`anomalyco/models.dev`** (sst redirect still resolves). Many forks exist.
- Does it distinguish Claude Code support? No. It is the general API/provider catalog with capability metadata; there is no "Claude Code picker" flag.

### LiteLLM model_prices_and_context_window.json (fastest to pick up new IDs)

- URL (raw): `https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json`
- Zero-auth: Yes (raw GitHub).
- What it lists: **API model keys with pricing + context windows**, across `anthropic`, `bedrock`/`bedrock_converse`, and Vertex namespaces. Confirmed present: `claude-opus-4-8`, `claude-sonnet-5`, `claude-fable-5`, `claude-haiku-4-5`, `claude-opus-4-5`, plus regional Bedrock variants (`us.`, `eu.`, `au.`, `jp.`, `global.`, `apac.` prefixes). `litellm_provider` distinguishes `anthropic` vs `bedrock_converse`.
- Freshness/lag: fastest-moving of the general feeds. LiteLLM merges pricing/model PRs multiple times per day, so new Anthropic IDs typically land within hours-to-days of announcement. Had the full Claude 5 family already.
- Downsides: very large file; heavily Bedrock/Vertex-oriented so a lot of noise (regional duplicates); pricing-first, so capability metadata is thinner than models.dev; no Claude Code picker distinction.
- Maintenance health: extremely active (core LiteLLM data file).

### OpenRouter /api/v1/models

- URL: `https://openrouter.ai/api/v1/models`
- Zero-auth: Yes (public list; only `listForUser` needs a bearer token).
- What it lists: Anthropic models under OpenRouter's **own slug convention**: `anthropic/claude-sonnet-5`, `anthropic/claude-fable-5`, `anthropic/claude-opus-4.8`, plus **effort/speed variants OpenRouter invents** like `anthropic/claude-opus-4.8-fast` and router aliases `~anthropic/claude-fable-latest`, `~anthropic/claude-haiku-latest`. Note dots not dashes (`4.8` vs `4-8`), and `-fast`/`~latest` slugs that do NOT exist as Anthropic API IDs.
- Freshness: fresh. Newest Anthropic `created` timestamp was Sonnet 5 at 2026-06-30. Rich pricing/context/modality metadata.
- Downsides: slug translation required to map back to Anthropic API IDs; the `-fast`/`~latest` entries are OpenRouter routing constructs, not real model IDs; not the Claude Code picker.
- Maintenance health: OpenRouter updates continuously as a commercial routing product.

### Anthropic-official zero-auth surfaces

- **Docs model overview**: `https://platform.claude.com/docs/en/about-claude/models/overview` (also `docs.anthropic.com` equivalent). Zero-auth, static MDX. Authoritative and very fresh: full comparison table with **Claude API ID, Claude API alias, AWS Bedrock ID, Google Cloud ID**, pricing, context, cutoffs for Fable 5, Opus 4.8, Sonnet 5, Haiku 4.5, plus a Legacy accordion (Opus 4.7/4.6, Sonnet 4.6/4.5, Opus 4.5/4.1). Also documents that `claude-mythos-5` / `claude-mythos-preview` exist behind invitation-only Project Glasswing. Best canonical zero-auth source, but it is a page to scrape (MDX/HTML), not a JSON API, and it is the API catalog, not the Claude Code picker.
- **Claude Code effort/model docs**: `https://code.claude.com/docs/en/model-config` and `claude.com/blog/claude-model-and-effort-level-in-claude-code` document the picker semantics (low/medium/high, xhigh/max on newer models, `max` only on some Opus tiers, `opusplan`). Human prose, not a machine catalog, but the closest official description of the picker curation.
- **`GET /v1/models`**: the authoritative machine list, but requires API key or OAuth. Out of scope by the task's zero-auth constraint. (Docs confirm the response carries `max_input_tokens`, `max_tokens`, and a `capabilities` object.)
- **anthropics/claude-code repo**: contains `CHANGELOG.md`, docs, plugins/examples; **no `models.json`, no `src/`**. The changelog does not enumerate the model catalog. Third-party changelog mirrors exist (claudefa.st, claudelog) but they narrate features, not model IDs.
- No unauthenticated Statsig / control-plane model list was found exposed as a clean public feed. Claude Code fetches feature flags at startup, but that is not a published model catalog.

### npm registry angle

- URL: `https://registry.npmjs.org/@anthropic-ai/claude-code`
- Zero-auth: Yes. Gives `dist-tags.latest` (was **2.1.215**) and per-version publish timestamps under `time`.
- Value: it anchors **cadence and the version axis**, not the catalog itself. There is **no model catalog embedded in the package metadata**. The catalog lives in the platform-specific native binary that the npm wrapper downloads, so you cannot read it from registry JSON.
- Best use: combine npm `time`/`latest` (which version is current) with Piebald's per-version extract (what catalog that version embeds) to build a "which catalog ships in version X" mapping. No one publishes a per-release extracted catalog as a package.

### Other sources found

- **jqueryscript/anthropic-claude-timeline**: a human-curated timeline of Anthropic model releases/product milestones. Good for narrative history, not model IDs.
- Blog references (Tygart Media "Claude API Model Strings", hikari-dev "Obtaining a List of Claude Models", secondtalent, developersdigest model-picker guide): useful human-readable snapshots, but manually maintained and quickly stale.
- **chauncygu/collection-claude-code-source-code** and the March 2026 Claude Code source-map leak: relevant to binary/source extraction approaches, not a live model feed.
- No dedicated repo was found that runs a scheduled GitHub Action to poll `/v1/models` and commit the JSON. Searched explicitly; the pattern is discussed generically but no maintained Anthropic-models-snapshot repo surfaced.

## Ranked Recommendation

**For "the general Anthropic API model catalog," zero-auth, as JSON:**
1. **models.dev `api.json`** — best structured capability metadata, community-validated, distinguishes families/reasoning/limits/cost. Days-behind freshness. Primary recommendation for a clean programmatic feed.
2. **LiteLLM raw `model_prices_and_context_window.json`** — fastest to pick up brand-new IDs (hours-to-days), best when you need the newest ID the moment it ships. Noisier (Bedrock/Vertex regional variants), pricing-first.
3. **OpenRouter `/api/v1/models`** — fresh and rich, but requires slug translation and filters out the fake `-fast`/`~latest` routing entries.
4. **Anthropic docs overview page** — authoritative and fresh, but scrape target (MDX), not JSON. Best as the ground-truth cross-check.

Use two of these together and reconcile (e.g., LiteLLM for "is the new ID live yet," models.dev/docs for capabilities), since any single one lags on some axis.

**For "the models the latest Claude Code *picker* supports" specifically:**
- **The honest answer: no project tracks the Claude Code picker catalog in real time.** The picker is a curated subset with effort tiers that differs from the API list, and it is only knowable from the binary.
- **Closest existing proxy: Piebald-AI/claude-code-system-prompts `data-claude-model-catalog.md`** — it is Claude Code's own embedded catalog doc, extracted per version, but lags npm by ~2 weeks and can carry unreleased placeholders.
- **Most reliable path if you need current + Claude-Code-specific: self-extract from the binary** (what this repo's `scripts/extract-claude-model-catalog.py` already does), pinned per version, treated as verification-only, cross-checked against models.dev/docs. There is no maintained external substitute that is both current and Claude-Code-picker-accurate.

## Source Quality Assessment

High confidence on the landscape and on which feeds carry the Claude 5 family (verified by direct fetches of models.dev labs view, LiteLLM raw JSON, OpenRouter API, and the Anthropic docs table). Medium confidence on exact update-lag numbers (Piebald's ~2-week lag is inferred from commit dates vs npm `latest` at one point in time and will drift). The one contradiction encountered (a raw models.dev `api.json` fetch appearing to omit Claude 5) was resolved as a large-file truncation artifact, not real staleness.

## Open Questions

- Does any Claude Code startup control-plane/Statsig response expose the picker set unauthenticated? Not found, but not exhaustively probed at the network layer.
- Exact real-world lag distribution of Piebald extracts across many releases (only a handful of commit dates were sampled).
- Whether Anthropic will ever ship a `claude --models` / non-interactive picker dump (would obviate all of this).

## Actionable Takeaways

- If the goal is a maintained external feed and API-level IDs are acceptable: wire to **models.dev api.json** (primary) + **LiteLLM raw JSON** (freshness backstop). Both are trivially cache-able and zero-auth.
- If the goal is truly "what this exact Claude Code version offers in `/model`": keep the in-repo binary extractor as the source of truth, pin per version, and use **Piebald's catalog** as an external sanity cross-check rather than a primary feed.
- Anchor everything to **npm `registry.npmjs.org/@anthropic-ai/claude-code`** for the version axis; map version -> catalog via Piebald or the local extractor.
- Do not treat OpenRouter slugs or LiteLLM Bedrock-prefixed keys as Anthropic API IDs without normalization.
