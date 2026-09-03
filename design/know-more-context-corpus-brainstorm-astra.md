---
title: KnowMoreContext corpus, evals, and a 90 day publishing strategy
type: design
tags: [know-more-context, transport-matters, corpus, evals, content-strategy, distribution]
summary: A public observatory for captured harness instructions, reproducible agent economics, and original evidence led publishing.
status: draft
confidence: medium
---

**The recommendation.** Build KnowMoreContext as a public observatory with three connected products: the Prompt Ledger, the Cost Lab, and Run Journeys. Launch the Prompt Ledger first, using Astro static output on Cloudflare Workers Static Assets, a separate public repository, and a custom domain. Add a React island for published run journeys on that same domain. Introduce a separate application only when people need private uploads, accounts, saved annotations, or live collaboration. Make the immutable, citable evidence URL the shared unit across the website, X, RSS, charts, and future developer tools.

The content promise: **“See what your coding agent sends. Measure what it costs.”** The weekly reason to return: **“Your harness updated. Here is what changed.”** The business connection: KnowMoreContext supplies public evidence and interpretation; Transport Matters supplies the instrument people can use on their own work.

Research date: 14 September 2026. Corpus numbers below come from the supplied #683 brief, unless explicitly identified as a calculation. I inspected the repository contracts, but did not independently enumerate the 482 private probes or rerun captures. All experiments, prices for proposed products, URLs on the proposed domain, schedules, and targets are proposals. Domain and package availability remain unverified. Nothing has been published or sent.

**Launch evidence inventory, supplied in the seed issue.** These are character measurements of the primary system surface, not token totals or whole request sizes.

| Captured scope | Supplied measurement | Editorial use |
| --- | --- | --- |
| Entire historical set | 482 probes, 26 harness versions, 88 first turn cells | Coverage statement tied to the initial export. |
| Claude Code 2.1.270 | Opus 9,383; Fable 13,094; Sonnet/default/opusplan 27,329; Haiku 27,431 characters | Model choice is the first navigation axis and a strong opening comparison. |
| Codex 0.154.0 | Captured selections from gpt-5.3-codex-spark through gpt-5.5 span 14,366 to 27,846 characters | Show each observed selection, without implying equal task capability. |
| Grok CLI 1.0.30 | grok-4.5 and grok-4.6: 5,892 characters | Include smaller instruction surfaces without equating brevity with quality. |
| Repeated observations within cells | Eight normalization rules make 80 cells internally consistent; 8 retain real variants | A method story and a reason the variant interface belongs in v1. |

The supplied tool turn observations include additional Codex model families beyond that size snapshot. Keep their coverage tables separate until the export establishes which versions, efforts, and shapes were actually captured together. A shorter primary field cannot rank full context overhead while secondary system content and tools remain excluded.

**1. Two discoveries that change the strategy.**

The broad claim that nobody publishes harness prompt changes is already contested. Piebald's own repository reports Claude Code 2.1.270, a prompt changelog across 287 versions, and extraction from the distributed CLI. It also promotes version change summaries on X. Credit that work and invite comparison. KnowMoreContext can establish a more specific position: assembled requests observed during controlled executions, with model and effort attribution, request shape, actual variants, and a path from a prompt change to an executable experiment. Source extraction and execution evidence answer complementary questions. [Piebald's corpus](https://github.com/Piebald-AI/claude-code-system-prompts).

X currently specifies 500 verified followers and 500,000 verified Home Timeline impressions in 90 days, excluding reply impressions. Its rewards rules also exclude content that “Was created or posted using automated means” and prohibit repeated engagement solicitation. Its definition of qualified impressions includes unique Premium viewers and a visibility condition. Admission remains discretionary. These facts make a fully automated X publishing pipeline a poor fit for this objective. [Original Content Rewards policy](https://help.x.com/en/using-x/original-content-rewards).

**Operating decision:** automate the research supply chain and publication of site data. Stuart should originate the editorial judgment and write and publish the qualifying X posts. The ten drafts below are material to work from, not a claim that AI supplied copy becomes eligible through manual submission. The treatment of software rendered research graphics under the broad automation wording is uncertain; obtain a specific policy answer before relying on those graphics for rewards. General permission to operate an informational bot does not establish rewards eligibility. [X automation rules](https://help.x.com/en/rules-and-policies/x-automation).

**2. The audience and the distinctive product.**

Start with developers already paying for two or more coding agents, people choosing an effort level daily, and engineering leads trying to understand a team bill. Their questions are concrete: “Did upgrading change what Opus is told?”, “Why did this tiny task use so much context?”, “Does xhigh improve completed work?”, and “Did delegation save time after the coordinator finished?” Researchers and journalists become a second audience because every claim has a stable evidence address.

The first screen should answer a question immediately. Show a selector for harness and model, the latest captured version and date, and one substantial recent change. Under it, show three editorial cards, a small coverage summary, and a link to the method. The entire rest state can fit in one viewport. The corpus directory follows below. Avoid opening on a warehouse of filters, a wall of statistics, or an infinite canvas with no obvious destination.

Make every public claim a small object with five parts: assertion, scope, measurement, evidence link, and interpretation. Example: “In the captured Claude Opus comparison from 2.1.261 to 2.1.269, normalized primary system text shrank by 2,442 characters. The diff contains 45 changed lines. This describes text on the captured route; the effect on token billing and task outcomes has not been measured.” Its card can shorten the wording while retaining the scope and unit.

A reader should move through four depths: the answer in ten seconds; the important hunk in thirty seconds; the complete comparison in two minutes; the capture manifest and reproduction procedure when needed. Social content should begin at the first depth and link directly to the second.

**Three recurring audience rewards:** discover a change before upgrading; make one better spending decision; inspect a surprising run without trusting a leaderboard author. Each rewards a different kind of return visit. All three rely on the same evidence system.

**3. Stack fit: choose the publication architecture before the application framework.**

| Shape | Search and first crawl | Interactivity and canvas | Economics and operations | OG cards and embeds | Judgment |
| --- | --- | --- | --- | --- | --- |
| Astro static on GitHub Pages | Complete HTML, simple crawlable timelines, easy custom domain. | Client React canvas can read static manifests; server features need another service. | Excellent for a modest public archive; distribution and commercial hosting limits constrain the future property. | Generate PNGs during builds; static iframe or SVG embeds work. | Credible fast launch, weaker permanent home for the stated business. |
| Next.js on Vercel | Prerendered corpus and server rendered reports can both be excellent; avoid client fetched core content. | One application can own accounts, private data, dynamic comparisons, and React canvas. | Commercial baseline is Pro; dynamic rendering and assets need budgets and caching. | First class image metadata conventions; prebuilt images still reduce runtime work. | Strong if authenticated workflows are imminent. Adds services the corpus does not yet need. |
| Astro static on Cloudflare, React journey island | Complete HTML for evidence and articles; interactive code loads only where useful. | Published replays and a read only infinite canvas fit inside Astro. Later server endpoints can be introduced separately. | Static asset serving has attractive scaling; bulk traces go in object storage. | Build PNGs, JSON, SVG, RSS, and small embed pages from the same records. | Recommended starting shape. |
| Static corpus plus an independently deployed application | Corpus and public report summaries stay prerendered; application pages need their own indexing discipline. | Clean ownership for authentication, private uploads, collaboration, and live runs. | Two deployment surfaces, shared schema and design tokens, explicit version coordination. | Evidence cards remain on corpus origin; app creates snapshots that receive public report URLs. | Recommended evolution when application behavior earns its cost. |
| Hugo or Eleventy plus a small standalone viewer | Very little runtime machinery and good HTML output. | Larger interactive surfaces need a deliberate separate component build. | Lean hosting; less immediate reuse of React UI code. | Build images and embeds externally. | Suitable for a publisher with little React work. TM's journey ambition favors Astro islands. |

Astro renders content to HTML and hydrates selected interactive components, so a canvas is compatible with a static site. Next.js also supports static exports; it is inaccurate to treat Next as inherently uncrawlable or inherently expensive. Its advantage here is application integration, not a special ability to get prompt pages indexed. [Astro islands](https://docs.astro.build/en/concepts/islands/), [Next static exports](https://nextjs.org/docs/app/guides/static-exports).

GitHub Pages currently limits published sites to 1 GB, has a 100 GB monthly soft bandwidth limit, and restricts use as hosting for an online business or commercial SaaS. An educational corpus may fit; the complete proposed monetized property deserves a different home. GitHub remains the source and audit surface regardless of where HTML is served. [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits).

Vercel's Hobby plan is restricted to personal, noncommercial use. Pro currently starts with a $20 monthly platform fee including one deploying seat and $20 usage credit; additional deploying seats and usage can add cost. A sensible early planning envelope is $20 to $100 monthly for the web application, excluding evals. This is a planning allowance, not a traffic quote. [Hobby](https://vercel.com/docs/plans/hobby), [Pro](https://vercel.com/docs/plans/pro-plan).

Cloudflare says static asset requests are free and unlimited; Worker execution is billed separately. Keep corpus requests on the asset path. Object storage is for large trace shards and downloadable bundles. R2 Standard currently lists $0.015 per GB month, separate operation charges, and no internet egress charge. Cloudflare Pages is also viable, but its Free plan's 20,000 file limit and 25 MiB per asset limit make it worth choosing the static assets deployment deliberately. [Static asset billing](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/), [R2 pricing](https://developers.cloudflare.com/r2/pricing/), [Pages limits](https://developers.cloudflare.com/pages/platform/limits/).

**Scale illustration, not a traffic forecast:** 88 prompts at 30 KB each occupy about 2.64 MB before variants and metadata. One million page loads at 300 KB each transfer about 300 GB. Ten thousand readers opening 10 MB traces transfer another 100 GB. The text archive is small; replay delivery, graphics, and loading behavior become the meaningful costs. Publish a 100 to 300 KB initial report and fetch trace chunks on demand. A working early allowance is $0 to $25 monthly for static delivery and modest storage, plus domain, email, optional analytics, and CI usage. Review actual charges monthly.

**OG images:** render immutable 1200 × 630 PNGs during the build, using one HTML/SVG based chart template. Also export a 1080 × 1350 portrait version for native image posts and a text description. Filenames include the claim revision digest. Keep the same fact, unit, labels, and citation on every crop. Next provides image file conventions and programmatic generation, but a corpus does not require a live image endpoint. [Next image metadata](https://nextjs.org/docs/app/api-reference/file-conventions/metadata/opengraph-image).

**Embedding:** every claim gets a compact HTML embed, a static image, and a Markdown citation. The iframe is an enhancement; an ordinary linked image is the baseline. Set narrow framing permissions on embed routes, keep scripts off raw data routes, and give remote JSON consumers an explicit CORS policy. Embeddable charts should contain a visible date and scope so an old screenshot remains interpretable.

**What changes the recommendation:** choose Next on Vercel at inception if private uploads and accounts are a committed first month deliverable and the team already owns the relevant stack. Split an application out when live sessions, collaborative state, or permissioned data become core, not merely when the first graph is drawn. Rework storage and incremental publishing when a full build exceeds ten minutes or the output approaches the host's published file limits. No framework migration is justified by the existence of an infinite canvas alone.

**4. Owning useful search results.**

The search target “claude code system prompt” already has competitors with substantial history. Compete on answer quality, evidence, freshness, and citations. Build a clear top level page for that exact intent, then link to model pages and observed version snapshots. Its opening paragraph should explain what the captured primary field contains, the latest observed version, and the difference between a compiled prompt component and an assembled request. The searcher should see actual prompt text without JavaScript or registration.

Proposed evergreen pages: `/claude-code/system-prompt/`, `/codex/system-prompt/`, `/grok-cli/system-prompt/`, `/guides/system-prompt-vs-full-request/`, `/guides/harness-token-usage/`, and `/guides/prompt-caching/`. The last two begin as careful measurement explainers, then link to completed experiments. Avoid filling them with unmeasured estimates just to target a keyword.

Model pages answer “what does my selected model get?” Version pages answer “what did this release send?” Diff pages answer “what changed?” These are separate search intents. Index the useful editorial pages and immutable snapshots; canonicalize equivalent filter permutations; exclude empty combinations and query driven explorer states. Put real anchors in the initial HTML, generate a sitemap with meaningful modification dates, and return real 404s for unknown observations. Google recommends prerendering or server rendering and notes that some bots cannot execute JavaScript. [Google's JavaScript SEO guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).

Titles should be literal: “Claude Code system prompt: Opus, captured versions and changes”; “Claude Code 2.1.261 to 2.1.269: Opus system prompt diff”; “Codex tool turns: when instructions are present in the request.” Each page earns a unique summary, capture date, scope, and relevant links. Do not manufacture thousands of near identical effort pages before there are meaningful differences.

A good cold start package is three harness landing pages, all observed model timelines, the existing version snapshots, six short evidence articles, a method page, and a public corrections page. Submit the sitemap in Search Console and inspect representative rendered pages. A target of twenty substantive external citations in ninety days is more useful than producing twenty thousand empty pages. Offer researchers stable permalinks, CSV, and ready attribution so citing the work is easy.

**5. An opinionated replacement brief for #683.**

Proposed title: **“Publish a versioned observatory of captured harness instructions and their changes.”** Retain the separate repository, generated static pages, consecutive version diffs, declared variants, and public credential free validation. Replace the hosting constraint with “portable static output on a custom domain.” Add explicit preservation of historical probes, capture scope, evidence completeness, and a small editorial front door.

V1 owns the primary first turn system instruction surface. It also publishes a small request shape facts record where captured evidence exists, such as instruction presence and continuation reference presence. It does not pretend that the primary system field accounts for the complete request. Tool descriptions, secondary system messages, and run economics receive their own later milestones. Show their coverage status in v1 so an apparently small prompt cannot be mistaken for a complete context bill.

**Repository:** propose `littleorgans/know-more-context`, with site and public export together. Its name is illustrative until the owner confirms the desired GitHub namespace. Keep operational run archives and provider credentials outside it.

```text
know-more-context/
  README.md
  LICENSE-CODE
  RIGHTS.md
  schemas/
    corpus-record.schema.json
    claim.schema.json
    run-manifest.schema.json
  data/
    releases/<export-id>/manifest.json
    observations/<observation-id>.json
    texts/<sha256>.txt
    changes/<change-id>.json
  editorial/
    changes/<change-id>.md
    studies/<study-id>.md
    corrections/<correction-id>.md
  src/
    pages/                    # Astro routes for corpus, studies, feeds, embeds
    components/               # Small reading and comparison components
    journeys/                 # React replay viewer, introduced with first study
    lib/                      # Public contract readers and shared selectors
  scripts/
    import-export.ts          # Validates an already sanitized export
    build-derived.ts          # Diff indexes, summaries, cards, feeds
    validate-publication.ts   # Traceability and publication invariants
  tests/
    fixtures/                 # Small synthetic and approved public examples
  .github/workflows/
    validate.yml
    publish.yml
```

The exporter that understands private TM bundles belongs with TM's evidence owner and is consumed at a pinned version. The public repository reads its explicit export contract. This avoids recreating provider decoding, legacy bundle migrations, or route attribution inside an Astro generator. These are proposed future changes; this brainstorm changes no implementation.

**Critical archival seam found in the code:** `baseline_evidence.py` currently declares artifact schema 13 and probe labels A1/A2. `read_baseline_bundle` upgrades schemas 8 through 12 by dropping the historical B probe. Its own documentation says content sample counts can shrink and B only values disappear. A corpus generator that simply calls that convenience reader may erase precisely the variants it is supposed to publish. Build a lossless archival iteration capability alongside the existing owner, sharing validation and provider extraction helpers. Preserve every original probe and label. Keep the structural comparison reader's existing contract intact. Sources: `api/src/transport_matters/baseline_evidence.py` and `api/src/transport_matters/baseline_bundle_store.py`.

**Caller first sketch:** the capture maintainer exports one pinned bundle directory into a reviewed publication package. The public import validates and commits that package. The site rebuild derives all pages and cards from the package. Proposed interfaces are `iter_archival_probes(bundle_root) -> HistoricalProbe`, `export_corpus(probes, policy) -> PublicExport`, and `readPublicExport(manifest) -> CorpusIndex`. The first two belong to the capture/export boundary. The third belongs to the public site. A `HistoricalProbe` retains raw artifact version and original label; a `PublicExport` contains only approved data and provenance. Avoid passing a live TM database connection into the website.

**Three possible ownership shapes:** a Python script in the public repo directly parses every historical bundle; a TM owned export API supplies a stable contract; or the public repo reads preselected text with no capture aware exporter. Choose the second. The first duplicates a sensitive format boundary. The third loses provenance and makes manual selection the undocumented source of truth. If an existing extraction script already embodies the eight normalization rules, inventory and move or reuse it; do not retype those rules into two runtimes.

**Export sequence:** validate file integrity and supported source schema; iterate all original probes; decode the request through the shared provider reader; extract the specific source pointers without flattening away segment boundaries; attach identity and scope; sanitize publication content; normalize the approved text for comparison; group variants; generate stable identifiers; validate; emit a complete manifest. The site generator consumes only the result. Neither CI nor the site runs a provider probe.

**Identity must carry more than three coordinates.** The human directory starts at harness and selected model. An observation records harness version, selected model, observed wire model, requested effort and observed effort when available, request shape, route or explicitly unknown route, environment template digest, isolation and permission mode, capture time, source artifact version, source evidence digest, and extraction/sanitization/normalization revisions. TM already records several of these in `BaselineCell`, including home isolation and template identity. Preserve unknown values rather than inventing defaults. A selected alias such as `default` or `best` is not a timeless model identity.

Effort deserves two fields: explicit selection and observed request value. A default, unavailable, ignored, and unknown setting have different meanings. Do not retroactively divide an old sample into effort cohorts because a modern CLI offers those knobs. Structural certification's cell identity can remain its own contract while the publication exposes richer experimental attribution.

**Public data shape, abbreviated:**

```json
{
  "schema_version": 1,
  "observation_id": "<stable digest>",
  "selection": {"harness": "claude", "version": "2.1.269", "model": "opus", "effort": null},
  "observed": {"wire_model": "<captured id>", "effort": null, "request_shape": "first-turn"},
  "scope": {"route_id": null, "template_digest": "<digest>", "captured_at": "<source timestamp>"},
  "surface": "primary-system",
  "coverage": {"secondary_system": "excluded", "tools": "excluded"},
  "status": "observed",
  "variants": [{"id": "<content digest>", "observations": 2, "text_sha256": "<digest>"}],
  "provenance": {"source_artifact_version": 12, "source_probe_labels": ["a1", "b", "a2"]},
  "transforms": {"sanitize": "s1", "normalize": "n1"},
  "counts": {"unit": "unicode-code-points", "view": "normalized", "value": "<computed integer>"}
}
```

This is a shape illustration, not a valid observed record or a claim that the sample variant occurs twice. Production schemas use real integers and digests. Count Unicode code points and UTF 8 bytes separately, with explicit line ending treatment. First reproduce the issue's counts before replacing its existing character unit with a more specific label. Never allow JavaScript UTF 16 length and Python string length to silently report different “characters.”

**Sanitization and normalization are separate transformations.** Sanitization decides what may be public. Normalization decides which public differences are environmental noise. Keep original raw evidence privately, public sanitized faithful text for inspection, and public normalized text for comparison. The faithful view retains nonprivate runtime variation; it cannot be called the exact original bytes after substitutions. Both text views have digests. Original digest provenance proves correspondence only to someone holding the source; a digest alone does not independently prove an HTTP request occurred.

The eight known normalization rules become a versioned policy with before/after fixtures and a per record replacement log. Scope replacements to the documented environment positions. A UUID shaped string inside substantive instructions should not disappear just because it looks like a session identifier. Test repeated identifiers, overlapping paths, flattened memory paths, and a literal discussion of `/Users/` that should remain. Preserve ordering, whitespace semantics, text segment boundaries, and cache annotations in the faithful representation.

The 80 of 88 result means **80 cells become internally consistent after normalization**. It does not mean ninety one percent of all models share one prompt. The eight remaining cells expose substantive observed alternatives. Keep a golden fixture that preserves the extra paragraph and `<total_tokens>15000000 tokens left</total_tokens>` line. That string is instruction content; it is not measured consumption or available model context.

**Variants:** show “2 observed variants” beside the snapshot title, two column comparison on desktop, and an A/B selector on mobile. Each variant has an immutable digest, sample count, capture times, template/route grouping, and probe references. State “observed 1 of 3 samples,” never “affects 33% of users.” Separate known configuration changes from unexplained alternatives. If a version changes from `{A, B}` to `{B, C}`, report A absent from the later observed set, B retained, and C newly observed. Do not manufacture a single A to C story by picking one sample per release. Across unmatched environments, offer an explicit exploratory comparison with the confound visible.

**URLs, all proposed under `https://knowmorecontext.com`:**

```text
/                                                        editorial front page
/claude-code/system-prompt/                               harness search landing page
/claude-code/opus/                                       model timeline
/claude-code/opus/2.1.269/                                version summary and variants
/claude-code/opus/2.1.269/observations/<observation-id>/    immutable full scope snapshot
/claude-code/opus/changes/2.1.261...2.1.269/               readable comparison landing page
/changes/<change-id>/                                    immutable comparison of exact observations
/changes/<change-id>/variants/<from-id>...<to-id>/         exact variant pair
/codex/gpt-5.5/                                          another model timeline
/studies/<study-id>/                                     method, result, charts, complete run list
/runs/<run-id>/                                          static report and optional journey
/runs/<run-id>/events/<event-id>/                         citable event with text fallback
/data/v1/index.json                                      discoverable static API
/data/v1/releases/<export-id>/manifest.json               pinned export
/data/v1/observations/<observation-id>.json                observation record
/data/v1/texts/<sha256>.txt                               approved text content
/data/v1/changes/<change-id>.json                         structured diff
/feed.xml                                               editorial RSS
/feeds/claude-code.xml                                   harness change RSS
/method/                                                measurement and normalization contract
/corrections/                                           revision history
```

Use friendly version pages for navigation and exact observation URLs for citations. The version comparison landing page is a set comparison that names all eligible pairs. A stable `change-id` binds exact inputs and algorithm revision. The mutable model page says “latest captured,” with capture date, and links to an immutable observation. Version order is parsed semantically. Where releases were skipped, label “consecutive captured versions,” and explicitly list the coverage gap. A diff across a gap cannot attribute a change to one unobserved intermediate release.

**Page per snapshot:** title and complete scope; one sentence summary; last captured time; primary field size and observed variants; links to previous/next captured versions; the actual text; diff view; scope exclusions; normalization explanation; provenance and downloads. A compact “Other request content” row says secondary system message excluded, tools excluded, shape facts available. Absence has explicit states: absent in a captured request, not captured, extraction unsupported, excluded from publication, and withdrawn. Zero is reserved for observed empty content.

**Homepage:** lead with one human selected change and its consequence worth testing. The next three cards are a model comparison, a method insight, and a completed or preregistered experiment. Put a tiny “88 first turn cells / 26 captured versions / 3 harnesses” scope label beneath the promise, explicitly derived from the pinned launch manifest. Keep 482 probes one click deeper so newcomers are not asked to understand certification sampling before seeing value. During a quiet week, feature a historical discovery with its date.

**Raw data:** publish both git readable `.txt` and machine readable `.json`. Hash addressed text deduplicates identical prompts; observation JSON preserves every association. Pretty print JSON with stable key order and LF endings. Publish structured edit hunks with source line ranges, and generate unified `.diff` downloads from the same comparison. JSON schema, dataset revision, rights metadata, and correction status are part of the public surface. Add CSV summaries for spreadsheets; reserve Parquet and bulk trace archives until volume merits them. Never force a researcher to scrape a rendered diff.

**CI:** untrusted pull requests validate with no secrets or publish rights. On an approved corpus commit, schema validation, safe content checks, deterministic regeneration, link verification, HTML escaping checks, and a build run. A trusted deployment job then publishes that exact output using only a narrowly scoped hosting credential, or platform native deploy identity where supported. “No provider credentials” does not imply “no hosting authorization.” No provider call, runtime home, database, or private bundle path is available to public jobs.

**Verification contracts for implementation:** the pinned initial manifest accounts for every supplied probe or an explicit exclusion; the historical B fixture survives; normalization is idempotent; approved content outside replacements is byte stable; real variants never collapse; transform order is fixed; applying the unified diff reconstructs its target; every changed line links to both source texts; every factual card value matches its JSON record; rebuilding the same inputs yields identical substantive output; unknown versions return 404; representative pages expose their main evidence with JavaScript disabled. Check mobile diff reading, keyboard variant selection, and a real deployed X card fetch after publication. A changed normalization revision rebuilds all comparisons consistently and creates a visible correction if a prior claim changes.

**V1, estimated five to seven focused working days:** export and lossless history first; text and scope validation second; timelines/diffs/variants third; three search landing pages and six editorial cards fourth; build generated PNGs, raw downloads, RSS, and deployment fifth; reserve the remainder for external reading and correction. These are scheduling estimates, contingent on the historical corpus being accessible and the eight rules being recoverable. No new eval runner, account system, live canvas, extension, or tokenizer is necessary to ship this version.

**Next:** v1.1 exposes secondary system content, tool descriptions and schemas, and richer request shape comparison; v1.2 ships the first completed economic experiment and one read only run journey; v2 adds repeatable study orchestration, subscriber alerts, and optional private data. A metric that makes a claim less misleading, such as the excluded secondary system label, belongs in v1 even when the corresponding content view comes later.

**6. The Cost Lab: establish the measurement contract before publishing a ranking.**

A useful experiment begins with an immutable task fixture, an independently executable success condition, and a bounded comparison. “Same prompt” alone is insufficient. Record repository digest, fixtures, tool availability, home template, local instructions, installed binary, selected and resolved model, effort requested and observed, permission mode, OS, provider route, pricing date, cache condition, and run order. Pin the result's actual request digest because a version label can conceal remotely supplied instructions or configuration changes.

Run two clearly named tracks. **Native setup** measures the actual product experience, including its tools and prompts. **Controlled tools** holds the accessible tools and task fixture as constant as the harnesses permit. The first supports “which configuration worked better here?” The second narrows some confounds. Neither gives an isolated model quality ranking when the harness and model change together. Unsupported combinations appear as unavailable, never as failed or zero cost. Restrict effort comparisons to values the selected route actually accepts, and retain mismatches between selection and observed request.

Use six owned, offline fixtures for the first general suite: repair a CSV parser's quoted newline handling; repair a bounded LRU cache's eviction ordering; fix an accessible modal's keyboard behavior; rename a public API across a small monorepo without preserving the obsolete name; implement JSONL validation with a precise error contract; and repair cancellation propagation across an asynchronous worker. Supply failing tests and a hidden validation set committed by digest before execution. Keep dependency artifacts fixed and network disabled after setup. Five runs per condition are enough for an exploratory report; expand close or unstable comparisons before making a strong winner claim.

For a pilot, run six valid configurations on two fixtures, three repetitions each: 36 runs. Use a $2 run ceiling where actual metered billing can be enforced, or an equivalent explicitly modeled budget otherwise, and a five minute timeout. Maximum modeled pilot allocation: $72. For the first full batch, use nine valid configurations × six fixtures × five repeats = 270 runs. At an $8 ceiling the maximum allocation is $2,160. Reserve $500 for targeted repeats and $268 for capture work, totaling a proposed $3,000 first month experiment envelope. These are spending limits, not predicted bills. Label all capped runs as censored and publish their rate; do not discard them to make the winners look cheaper.

**Accounting rules:** retain per request terminal provider usage, the original response fields, and the interpretation version. Streaming usage often arrives cumulatively; do not sum every event. Track logical requests, physical attempts, retries, and child runs separately. Reconcile aggregate usage against the actual route's billing evidence when available. TM's `UsageStats` currently exposes input, output, cache read, and cache creation fields, with zero defaults. A default zero does not prove a field was measured as zero. Preserve presence and raw provider detail at the export boundary, including any reasoning detail outside this shared structure. Source: `api/src/transport_matters/ir.py`.

**Four quantities deserve separate visual encodings:** transmitted text/bytes; provider reported processed tokens and cache categories; estimated list price cost at a pinned schedule; actual marginal charge when observable. Subscription quota consumption is another distinct quantity. Do not assign a dollar bill to a subscription run by silently applying API rates. A continued request can omit an instruction string while the service retains relevant state. Omission of bytes proves no saving in billed tokens by itself.

**Canonical formulas:** cost per successful task = total attributable cost of all attempts / successful tasks. Report success rate beside it. At zero successes, show no finite successful task price. Effort ROI = change in success percentage points / additional dollars, accompanied by latency and the full success counts. Cached fraction uses the provider's documented token semantics after mapping categories to a disjoint denominator. Some providers count cached input inside input; some expose it separately. Never apply one sum across every provider blindly. Time to success includes failed attempts, recovery, and final integration, according to the declared retry policy.

**Overhead deserves careful language.** The exact share of transmitted characters attributable to system text is measurable after component extraction. Its share of billed cost generally is not identifiable from aggregate input usage, especially with caching and token boundaries. A cost allocation model can be published as a model; a controlled intervention can estimate a treatment effect. Neither should be presented as the provider itemizing the cost of each paragraph. Distinguish coordination calls by explicit workflow stage and actor. Do not classify every orchestrator call as overhead if it also solves the task.

Randomize condition order in blocks by task and time, use fresh isolated homes, and record cache observations. Clearing a local session does not establish a cold provider cache. For estimates, report every run, medians, spread, success counts, and uncertainty intervals. Resample at the task level when making suite level statements; repeated attempts on one task are not independent tasks. Preregister the main metric and the first batch's comparisons. Label the forty ideas below exploratory until separately registered. Publish failures and negative results with the same evidence depth as a win.

The report unit is a **study release**: protocol, immutable task versions, condition manifest, all included runs, exclusions with reasons, charts, summary, and a reproducible analysis command. Each chart links to a filtered table that lists the underlying runs. Each run links to its artifact, tests, request journey, and usage ledger. A reader should be able to challenge a number without asking for access to a dashboard.

**7. Forty experiments worth running.** Each item names the question, setup, metric, artifact, and reason to share. “Launch” means it belongs among the earliest experiments; “later” means the idea should wait for the relevant instrumentation or enough data. The same registered batch can support several descriptive views without pretending they are independent confirmations.

**01. Same job, complete bill. Launch.** Question: which harness/model/effort configuration delivers a correct patch for the least total cost? Setup: the six owned fixtures, nine valid configurations, five repeats, all starting from the same fixture snapshot and independent test contract. Metric: success rate, cost per successful task including failures, and median completion time. Artifact: a receipt for each run and a cost versus success chart with uncertainty and a “show all attempts” link. Why share: readers can compare a task resembling their work and inspect the failures usually absent from marketing screenshots.

**02. High versus xhigh. Launch.** Question: what does the next effort level buy? Setup: within each supported model/route, run low or medium, high, and xhigh where those exact settings exist, on the same six fixtures with five repeats. Metric: incremental successful tasks, input/output/reasoning usage where reported, latency multiple, and incremental cost. Artifact: a marginal return curve with each task visible, plus a card stating the observed tradeoff. Why share: it answers a setting people choose every day. If two levels tie within uncertainty, “no reliable improvement detected here” is useful content.

**03. The one word task. Launch.** Question: how much traffic and usage accompanies an instruction as small as “Return OK”? Setup: fresh controlled homes, no local project context, ten invocations per valid configuration; score exact output and retain any unexpected tools. Metric: primary system characters, tool schema characters, total request bytes, reported input/cache/output tokens, latency, and modeled or actual cost. Artifact: a magnified request composition receipt, with excluded fields visible. Why share: an immediately understandable task reveals the fixed work involved before a coding problem even begins.

**04. Instruction resend versus continued state. Launch.** Question: how do the observed tool turn transport paths affect bytes, usage, and cost? Setup: a deterministic twenty step fixture whose next value is available only after the previous tool result; run five repetitions across the supported observed model paths. Metric: instruction presence per request, continuation reference presence, cumulative request bytes, provider input/cache usage, success and latency. Artifact: two synchronized turn strips and cumulative curves. Why share: it puts the striking “no system text in this request” observation beside the economic evidence needed to interpret it. Never turn the seed observation into an unmeasured savings percentage.

**05. The context composition ledger. Launch.** Question: what occupies a real coding run's requests? Setup: extract primary instructions, secondary system content, tool schemas, supplied project context, user messages, tool results, and remaining content from the batch in experiment 01, retaining unmapped sections. Metric: exact transmitted characters or bytes by component and turn, plus separately reported total usage. Artifact: an expandable stacked area chart where selecting a band reveals the text that contributed. Why share: people can see whether repeated history, huge tool results, or static instructions dominate their particular task. No synthetic dollar allocation is needed.

**06. Warm cache dividend. Launch after usage validation.** Question: how much benefit does a verified warm prefix deliver? Setup: identical task prefixes with controlled distinct suffixes, repeated at 30 seconds, 2 minutes, 6 minutes, and 15 minutes; randomize time blocks and record actual hit evidence. Use a provider supported cache control only where available. Metric: cache read/creation tokens, uncached input, latency, price, and quality. Artifact: a cache survival curve and a “first run / repeated run” receipt. Why share: it reveals the effect of work rhythm without assuming undocumented TTL behavior.

**07. The harmless edit that breaks cache reuse.** Question: which ordinary context edits alter cache behavior? Setup: add one line early in a project instruction file, append the same line late, reorder two tool declarations, and make a no change control; ten repetitions per treatment on one validated route. Metric: observed cache reuse, input charges, and time to first output. Artifact: a prefix diagram showing the first changed byte next to actual usage. Why share: it gives developers a concrete maintenance habit to test in their own environments. Exact cache causality still depends on controlled order and provider observations.

**08. Break even for three agents. Launch flagship.** Question: when does an orchestrator with three workers pay off? Setup: use three independent fixture modules followed by a required integration step; compare one capable agent with a TM orchestrator spawning exactly three workers, matching the task, tools, and final test contract. Run three task sizes and five repetitions each. Metric: total cost, wall time to validated integration, success, duplicate reads, and requests tagged to coordination stages. Artifact: a replayable delegation tree with a cumulative ledger and a break even chart. Why share: it answers the agent fleet question with the coordinator's full bill included.

**09. Coordinator model choice.** Question: can a cheaper or lower effort coordinator preserve the quality of stronger workers? Setup: hold the three worker configurations and the decomposition brief fixed; vary coordinator model and effort across four valid choices; run ten repetitions of the orchestration fixture. Metric: assignment errors, unnecessary followups, integration failures, coordination cost, and total time. Artifact: a matrix whose cells open the actual delegation instructions. Why share: one routing change could affect every workflow the reader runs. A coordinator's “thinking” story becomes observable task dispatch quality.

**10. Three workers reading the same file.** Question: how much does scoped context change fleet efficiency? Setup: identical orchestration with full repository briefs versus three scoped briefs pointing to separate modules, including one shared contract needed by everyone. Metric: duplicate bytes read, repeated transmitted context, total usage, correct integration, and missed shared requirements. Artifact: a context overlap map and before/after run receipts. Why share: it tests TM's own focused context thesis in public, including cases where narrowing context harms the result.

**11. Delegation depth.** Question: is one director, one orchestrator, and three specialists better than a flat four agent arrangement? Setup: use the same four work roles and task information, compare two explicit authority and briefing graphs, and repeat at small and large task sizes. Metric: number of handoffs, context duplication, cost, time, and completed contract checks. Artifact: matched graph replays with stage costs. Why share: the hierarchy question is visually obvious and commercially relevant. Be precise about any extra node; changing both topology and agent count is a separate condition.

**12. The merge bill.** Question: how much of a parallel coding workflow happens after workers claim completion? Setup: compare three truly independent edits with three edits touching a shared API; hold agent roster fixed and require an integration agent to run the final tests. Metric: time and cost from last worker completion to successful integration, conflicts, and rework. Artifact: a timeline where “agents done” and “work done” are separate timestamps. Why share: it exposes a frequent blind spot in multi agent speed demonstrations.

**13. Queue and retry amplification.** Question: how much does concurrency reduce useful throughput under a bounded route? Setup: fixed rate compliant workloads at concurrency 1, 2, and 4, with a predefined backoff policy and provider limits respected. Metric: validated tasks/hour, rate limit events, retries, wasted usage where charged, and completion tails. Artifact: a throughput curve and attempt ledger. Why share: it tests whether adding agents improves actual delivery. It avoids treating a spectacular simultaneous start as a performance result.

**14. Old CLI, same task, new instructions.** Question: does instruction following change across captured versions? Setup: three installable historical versions, one fixed accessible model identity and controlled home, twenty explicit instruction tests, five repetitions each. Examples: preserve a required filename, use the existing helper, include a demanded output field, and stop after the authorized scope. Metric: constraint satisfaction and task correctness, with each violated instruction quoted from the fixture. Artifact: version heatmap linked to prompt hunks. Why share: developers recognize regressions in everyday behavior. Version association is the result; attributing causality to one prompt edit requires a separate intervention.

**15. Apparent contradictions on trial.** Question: when two instruction passages appear to pull in different directions, how does the harness behave? Setup: human reviewers nominate ten exact text pairs and identify priority, conditions, and scope; discard pairs resolved by those distinctions; create three benign tasks for each remaining pair. Metric: distribution of actions, valid resolution, and task success. Artifact: a two quote card opening into a behavioral case file. Why share: a compelling reading puzzle gets an empirical answer. An automated contradiction score can nominate cases, but cannot establish inconsistency.

**16. Did a deleted paragraph matter?** Question: what behavioral effect does one meaningful prompt change have? Setup: only where supported and permitted, run an explicitly modified research harness or sanctioned instruction override with paragraph present versus absent, holding remaining request content stable; compare with native captures. Metric: targeted behavior, broad task correctness, token usage, and side effects. Artifact: treatment/control evidence and the exact injected difference. Why share: it connects the corpus to causality. If replacement changes other harness behavior, report the intervention as confounded and keep it off the native leaderboard.

**17. Same version, different day.** Question: can effective instructions vary without a CLI version change? Setup: pin a binary, model selection, home, tools, and launch flags; capture the same controlled first turn once daily for fourteen days. Metric: distinct normalized instruction digests, observed model changes, and transport changes. Artifact: a calendar with version held constant and any new variants opened on click. Why share: it tests whether a CLI version is enough to describe the tool developers actually used. Do not declare an A/B experiment without vendor evidence.

**18. Aliases that move.** Question: when does `default`, `best`, or a model family alias resolve differently? Setup: pair each alias with its currently observed explicit model selection under the same configuration for fourteen daily snapshots. Metric: wire model identity, instruction digest, supported effort, and a small fixed task's result. Artifact: an alias lineage chart with dates. Why share: it explains why identical launch commands can produce different experiments. Treat a provider alias as an observation, not a guaranteed pinned model.

**19. The twenty file instruction hunt.** Question: how does local instruction discovery affect what reaches the model? Setup: an owned nested repository with distinct benign markers in root and nested instruction files, plus an ignored directory and a sibling outside scope; ask tasks in selected subdirectories. Metric: markers actually transmitted, ordering, instruction compliance, and unexpected context. Artifact: a filesystem tree linked to request spans. Why share: it answers a common practical question with exact evidence. Publish only synthetic markers and files created for the study.

**20. Context length versus instruction survival.** Question: which constraints survive a long workflow? Setup: five required behaviors introduced at the start; grow a deterministic tool history through several size bands, including a recorded compaction boundary where one occurs. Metric: per constraint compliance, useful task completion, actual request context, and summary retention. Artifact: a timeline showing when the instruction disappeared from transmitted text or stopped influencing behavior. Why share: it separates forgetting, summarization, and ordinary execution failure. Do not infer hidden internal context from the wire alone.

**21. The compaction invoice.** Question: how much does compaction cost, and does it preserve what matters? Setup: a fixture with twenty named facts, five of which are needed later, and controlled tool output expansion; compare native compaction with a fresh session supplied a fixed concise handoff. Metric: compaction requests, usage, elapsed time, retained facts, and final task success. Artifact: a before/after summary diff and a usage spike trace. Why share: an invisible lifecycle event becomes something operators can budget and inspect.

**22. The second attempt strategy.** Question: is escalating effort after failure cheaper than starting high? Setup: compare fixed high effort, fixed lower effort, and a preregistered lower then high retry policy with fresh task state and the same overall ceiling. Metric: policy success probability, total cost across attempts, and time to successful output. Artifact: a decision tree and cumulative cost distribution. Why share: it produces an actionable routing policy, including the tasks where escalation wastes time.

**23. Fresh run versus continue debugging.** Question: after one failed patch, should the agent continue with its history or start over with the failure report? Setup: capture the same first failure, fork into continuation and fresh session conditions using an approved replay or controlled setup, and score with hidden tests. Metric: correction rate, extra cost, repeated mistakes, and elapsed time. Artifact: branching run journeys from a shared failure checkpoint. Why share: everyone encounters the moment where an agent appears stuck; this tests two familiar responses without anecdotal selection.

**24. Tool output diet.** Question: how much do concise, structured tool results help? Setup: a deterministic search task with the same relevant facts delivered as verbose logs, bounded snippets, or structured JSON; preserve an exact information inventory. Metric: retrieval success, repeated calls, transmitted bytes, usage, and unsupported claims. Artifact: three tool result receipts plus the resulting patch. Why share: an engineer can often improve a tool interface more easily than switch models. Equivalent information is the key control.

**25. Tool inventory size.** Question: what is the cost of offering tools that a task never uses? Setup: equip a controlled environment with 5, 20, and 100 safe toy tools with realistic schemas, holding the five useful tools unchanged; evaluate routes that accept the setup. Metric: schema size, observed input/cache usage, correct tool selection, and latency. Artifact: tool count versus success and usage curves. Why share: it turns the “too many MCP tools” discussion into a test. If the harness discovers tools lazily, record which schemas actually crossed the wire.

**26. Eager versus discovered tools.** Question: does lazy discovery save enough context to offset discovery calls? Setup: expose the same safe tool catalogue through two supported delivery modes, using tasks requiring 1, 3, and 10 tools. Metric: total requests, schema bytes, discovery failures, completion time, and cost per success. Artifact: a break even chart and a request sequence showing the discovery round trip. Why share: it identifies workloads where a fashionable architecture does or does not earn its extra step.

**27. Search first or read everything.** Question: when does targeted repository exploration outperform broad loading? Setup: owned repositories at three scales with planted implementation sites and unrelated files; compare an explicit search first brief with the native baseline. Metric: relevant files found, irrelevant bytes read, time to first correct edit, total usage, and success. Artifact: a repository heatmap showing visited files. Why share: the path to the answer is visually interesting and directly related to spend.

**28. Spend on verification.** Question: how much validation effort pays for itself? Setup: run the same tasks under baseline instructions, explicit “run the relevant tests,” and an enforced final test gate that returns failure evidence once. Metric: escaped defects, verification usage, corrective turns, and total successful task cost. Artifact: a funnel from first patch through test failures to final delivery. Why share: it challenges both “the agent tests too much” and “just trust the patch” using measurable outcomes.

**29. False completion receipts.** Question: how often does an agent claim a check passed when the evidence does not support it? Setup: deterministic fixtures with a missing executable, a failing hidden test, and a successful control; require an accurate final validation report. Metric: unsupported success claims, correctly acknowledged boundaries, and real task correctness. Artifact: paired final claim and tool result snippets. Why share: reliability includes reporting honestly. Avoid assigning intent to an inaccurate statement.

**30. Minimal patch discipline.** Question: which configurations complete the request with the least unrelated change? Setup: ten narrow fixes in owned fixtures with a predefined allowed change surface and independently scored exceptions. Metric: correctness, unrelated changed files, unnecessary dependencies, public API churn, and reviewer minutes in a blinded review. Artifact: patch thumbnails with a reviewer burden chart. Why share: the cheapest agent output can become expensive human work. This extends the receipt to the reviewer's time without claiming all code churn is bad.

**31. Long description versus short task contract.** Question: does a precise acceptance contract beat a long narrative brief? Setup: express identical requirements in three forms: concise checklist, prose with the same facts, and a longer brief with irrelevant background; randomize tasks and conditions. Metric: omitted requirements, correct tests, input usage, and followup questions. Artifact: a brief comparison with outcome distributions. Why share: readers can improve their own requests immediately, and the result can be negative without losing usefulness.

**32. Order of facts.** Question: does positioning the same critical requirement affect compliance? Setup: fixed length briefs with a synthetic required marker at the beginning, middle, or end, alongside the same substantive task; repeat across two context sizes and supported efforts. Metric: marker compliance, true task success, and interaction with compaction. Artifact: position versus compliance chart linked to exact prompts. Why share: it tests a common prompting rule under real harness conditions rather than a bare chat model.

**33. Permission round trips.** Question: how much operational time do approval interruptions add? Setup: a harmless fixture of file reads and writes, supported permission modes, and a deterministic human simulator that returns approvals after a fixed delay. Metric: number and duration of pauses, extra requests, eventual success, and total elapsed time. Artifact: a timeline separating model, tool, and waiting time. Why share: it makes “fast agent” claims honest about human waiting. No risky action or permission bypass is required for the study.

**34. Cancellation and resume.** Question: how much useful work survives an interrupted session? Setup: cancel at fixed observed milestones, then resume through the harness's supported path or supply a fixed handoff in a fresh run. Metric: lost completed work, duplicated reads, additional cost, final correctness, and time to recover. Artifact: a journey with an interruption marker and preserved artifacts. Why share: developers care about realistic reliability, including laptop sleep, mistakes, and ordinary interruptions. Provider cancellation accounting must be recorded rather than guessed.

**35. Small tasks versus batching.** Question: when is it cheaper to batch independent changes in one session? Setup: six equal independent fixes, delivered singly, in pairs, and together, with the same final tests and a fresh fixture for every condition. Metric: static instruction reuse, cache behavior, cross task interference, success, and total cost. Artifact: a batch size curve with a failure overlay. Why share: it translates repeated prompt overhead into a work planning decision while showing the risk of oversized briefs.

**36. Conversation memory earns its keep.** Question: does retained task history improve a second related change enough to cover its context cost? Setup: complete a first fix, then request a related second fix in the same session versus a fresh session with a concise artifact reference. Metric: second task success, context reuse, repeated exploration, added usage, and stale assumption errors. Artifact: two linked task receipts and an information retention map. Why share: it tests a choice made throughout every coding day.

**37. The transport envelope watch.** Question: can a routing or header name change explain an otherwise puzzling capture or behavior change? Setup: compare stored envelope projections across consecutive captured versions and repeat a controlled probe for any meaningful deviation. Metric: changed host/path/header names, capture completeness, and associated observed behavior. Artifact: a routing diff beside the body diff. Why share: it can give tool builders early evidence of integration drift. Published projections intentionally omit sensitive values; they cannot diagnose everything a full private transport log could.

**38. Reliability per ten dollars.** Question: how much validated work fits within a fixed budget? Setup: use the first registered batch to simulate a fixed, declared task ordering and spend ceiling; later verify selected policies with real budgeted runs. Metric: completed tasks, unresolved tasks, latency, and the distribution of remaining budget. Artifact: a budget race whose frames link to actual attempts. Why share: a fixed budget is more intuitive than separate token prices and success scores. Label simulation and subsequent execution as different evidence classes.

**39. Reproducibility across machines.** Question: how stable are the public corpus and eval findings in a second legitimate environment? Setup: two consenting operators use the same recipe on matched OS/tool versions with explicitly separate accounts and identical owned fixtures; compare normalization and outcomes. Metric: instruction variant differences, provider route differences, cache observations, and success/cost spread. Artifact: a replication report and environment delta sheet. Why share: successful replication strengthens the observatory; disagreement can reveal a meaningful new scope dimension. Do not pool accounts as if they were interchangeable.

**40. Predict the winner, reveal the receipt.** Question: how well do expert intuitions predict economical success on a specific task? Setup: privately collect five named expert forecasts against the preregistered task and budget before running it; publish the forecasts and full outcomes after consent. Metric: ranking error, cost prediction error, and successful task choice. Artifact: a forecast board that resolves into evidence linked receipts. Why share: the surprising part is the gap between expectations and observed work, with experts contributing original interpretation. Keep the X post self contained; participation and replies are unnecessary for understanding it.

**8. Turn these ideas into a publishing portfolio.**

The first three study releases should be: one word task and request composition; high versus xhigh on the owned fixtures; and one orchestrator plus three agents across three task sizes. The resend/continuation and cache studies follow as soon as accounting is verified. This sequence moves from easy to understand observations to the owner's distinctive orchestration capability.

Use existing benchmark infrastructure selectively. A small declared subset of SWE-bench can provide familiar tasks, and Aider's public leaderboard provides a useful reference for presenting benchmark methodology. Respect fixture licenses and exact benchmark rules. Call an adapted suite a custom subset rather than an official score. The new contribution is the request journey and full attempt economics. [SWE-bench](https://www.swebench.com/), [Aider's leaderboard](https://aider.chat/docs/leaderboards/).

A six chart study can yield six distinct original stories: a task result, a failed attempt, an effort tradeoff, a cache observation, a surprising transcript moment, and a method correction. Each must add a different observation. Recutting the same chart with six hooks produces repetition without six contributions. Maintain an idea ledger linking each editorial claim to a study, fact identifiers, and its previous use.

Publish a negative result every month: a prompt change with no measured behavioral effect, an effort increase with no detectable benefit, or a scoped briefing that made integration worse. Publish a replication or correction at least once per quarter. These are planned editorial slots, not quotas for manufacturing failures. The observatory should make it easy for a vendor to cite a favorable result and easy for a skeptical reader to inspect an unfavorable one.

**9. X: a ninety day original publishing plan.**

The operational target is 600,000 qualifying impressions and 650 verified followers, creating a margin above the owner's stated thresholds. Record the account's actual starting values on day zero; 650 is the desired total, not necessarily 650 new followers. The account's age and Premium requirements are already handled according to the brief. Use the eligibility dashboard as the source of truth for progress. Public view counters are a distribution diagnostic, not proof that the threshold has been reached.

The arithmetic below is a target distribution, not a forecast:

| Original standalone posts in 90 days | Qualifying impressions per post target | Contribution |
| --- | --- | --- |
| 54 precise routine observations | 2,000 | 108,000 |
| 24 broader comparisons or explanations | 8,000 | 192,000 |
| 12 flagship results or compelling journeys | 25,000 | 300,000 |
| 90 posts total | 6,667 average, rounded | 600,000 |

One original standalone post per day is the baseline. Some days will justify two; compensate with a lighter day rather than manufacturing a minor finding. Over roughly thirteen weeks, this supports one substantial weekly flagship. A fleet replay is expensive to produce; half the flagship slots can instead be unusually clear corpus findings or a completed result from a shared study batch.

The funnel needs real measurement. If qualifying impressions are 25% of the account's total displayed impressions, 600,000 qualifying requires about 2.4 million displayed impressions. At 10%, the requirement becomes 6 million; at 40%, 1.5 million. Those percentages are scenarios, not known audience composition. From a zero follower starting point, reaching 650 verified followers from 600,000 qualifying impressions implies about 10.8 verified follows per 10,000 impressions. Measure whether this account can approach that rate before treating the plan as on track.

Proposed cumulative milestones: day 30, 100,000 qualifying impressions and 150 verified followers; day 60, 300,000 and 350; day 90, 600,000 and 650. These milestones intentionally allow a slow beginning. If day 30 remains below 50,000 qualifying impressions, improve the story selection and secure more external citations. If day 60 remains below 180,000, concentrate on the two franchises producing the strongest relevant reach and a genuinely new collaborative study. Additional low value posts will not repair a weak editorial proposition.

**Cadence:** Monday: a real recent change or a clearly dated archival finding. Tuesday: model or effort comparison. Wednesday: one concept explained with a request diagram. Thursday: an observed variant or a useful tool/schema discovery. Friday: a completed experiment or a full run receipt. Saturday: a weekly digest with three concrete findings. Sunday: a method note, replication, correction, or useful annotated moment. Corpus history supplies the first three weeks while the first registered experiments run. A new release with no meaningful change is a site update; it does not automatically deserve an X post.

Start with two posting windows for a four week experiment: 13:00 UTC and 17:00 UTC, which are 20:00 and midnight in Bangkok. Alternate comparable content categories between them. These are test windows for the likely English speaking developer audience, not claims about the platform's best time. Choose the sustainable window using observed reach and Stuart's availability to engage thoughtfully. The core post must contain the observation, the essential scope, and a direct evidence URL. Do not hide the result or link in a reply.

Avoid building the strategy around threads. Each daily root post should stand alone even if the owner later adds context below it. A three part explanation can become three original posts on different days only if each contributes a complete, distinct finding. Quote posts that add a substantial new analysis may have editorial value, but the target arithmetic here credits only original standalone posts. Social replies can serve ordinary conversation; they receive no time budget as a growth tactic in this plan.

**Recurring franchises and their hooks:**

| Franchise | Hook shape | Visual or evidence | Frequency |
| --- | --- | --- | --- |
| The Prompt Changed | “This upgrade changed the instructions for [model]. Here is the relevant hunk.” | Three line red/green excerpt, exact version pair and scope. | As meaningful changes appear; about twice weekly. |
| The Model Split | “Same CLI version. These model selections received different instructions.” | Aligned model bars plus two small excerpt panels. | Weekly initially. |
| The Whole Receipt | “The patch passed. Here is every attempt that contributed to its cost.” | Success mark, cost, time, request count, full attempt link. | Weekly after eval launch. |
| Effort Returns | “What did [higher effort] buy on these six tasks?” | Success counts and usage/cost multiple on one card. | Every two weeks. |
| Context Anatomy | “This is what filled the request before the answer arrived.” | Labeled composition strip with a complete legend. | Weekly. |
| Cache Watch | “Same work, different observed cache state. Here are both receipts.” | Cache categories beside actual usage and time. | Every two weeks once measured. |
| Three Agents and a Coordinator | “The workers finished here. Integration finished here.” | Four lane journey with the final test gate. | Weekly clips from one complete study. |
| Variant File | “These two captures of the same selected cell disagree.” | Side by side text and sample provenance. | When there is a real variant to explain. |
| Release Receipt | “Installed version, captured version, observed model: all three matter.” | Small identity card and a changed alias or scope example. | Twice monthly. |
| Nothing Changed | “This release changed the binary; this captured instruction surface stayed identical.” | Stable digest with exact model and scope. | Only for a useful counterexample. |
| The Correction | “We changed this conclusion because [specific evidence].” | Old claim, corrected value, cause, dated link. | Whenever needed. |
| Week in Context | “Three changes, one result, one question we can now test.” | Four small panels and a concise original editorial summary. | Weekly. |

**How to make a diff stop a scroll:** begin with the consequence readers can evaluate. “Opus's captured primary prompt lost 2,442 characters” is stronger than “new corpus update.” Put the exact version pair directly below it. Show at most three substantive changed lines, with unchanged context sufficient to understand them. Explain what the hunk asks the model to do differently, and label that explanation as interpretation. The image should remain legible at phone width, with roughly 40 to 55 characters per excerpt line and large units. If the actual hunk is long, choose one clause and link to the whole diff. Never reduce font size until the receipt becomes decoration.

A useful card has one central number or contrast, one bounded assertion, one small source footer, and no more than two accent colors. Green and red describe additions and removals, with symbols and text also distinguishing them. A removal is not automatically an improvement. Editorial category colors can show planning, tool use, memory, output style, or safety only after human review of the text. A semantic label must link to the lines that justified it.

**Automatic assets from the corpus:** version delta PNG; model size bars; first turn/tool turn presence matrix; faithful/normalized comparison; variant pair card; release coverage calendar; scope/identity card; latest captured badge; unified diff download; weekly candidate digest; per harness RSS item; structured claim JSON; and an image caption containing the figure's exact data values. Reuse the same data objects for the chart, accessible table, and social preparation sheet. For evals, add cumulative cost curves, completion timelines, coordination graphs, and short silent journey recordings with captions.

**What could post itself from CI:** the website, the data release, RSS, updated badges, and an internal editorial preparation page can publish automatically after their checks. A routine informational X bot is technically possible through the official API under general automation rules, but it is outside this rewards plan and receives zero assumed qualifying reach. Do not launch a second bot account merely to push the same material around. For the intended account, CI provides candidate facts, diffs, and chart files; the human editorial step creates the contribution that the post exists to communicate. Do not treat pressing a publish button as proof of compliance with the automated creation issue identified earlier.

The editorial preparation record should contain: claim ID, source observation IDs, units, chart file, one line scope, proposed interpretation, correction status, and first publication status. A reviewable release is more valuable than a pipeline that invents urgency. CI may nominate a new prompt digest, newly observed variant, significant line deletion, new tool name, changed request shape, or observed envelope change. Only text changes supported by the comparison can supply exact quoted hunks. A summary model can propose an explanation for review; it cannot elevate a guess into a measured fact.

**Launch sequence:** days 1 through 3, prepare the domain, public corpus, method page, six editorial articles, RSS, profile bio, pinned launch post, and the first ten drafts; prepare two weeks of evidence material before announcing. Days 4 through 10, publish the first seven standalone observations, give external readers a concrete capture or diff to inspect, and preregister the first experiment. Days 11 through 21, publish three more launch pieces plus the one word study and a short video of reading an actual request. Days 22 through 45, make effort ROI the principal recurring result. Days 46 through 70, release the coordinator plus three workers journey and several distinct findings from it. Days 71 through 90, replicate the strongest result and publish an accessible state of agent economics report.

Do not wait for Google to deliver the initial audience. Every artifact should be citeable from a newsletter, repository README, benchmark discussion, or an original post by another author. The invitation is to inspect or reproduce a finding. No amplification is assumed or promised, and no outreach has been performed as part of this brainstorm.

**Who has a reason to amplify, and what to put in front of them:**

| Person or project | Specific material worth their attention | Productive angle |
| --- | --- | --- |
| Piebald / @PiebaldAI | A matched release where extracted components and assembled model specific requests illuminate each other. | Credit their chronology; offer a joint source versus execution comparison. |
| Simon Willison | A small structured dataset, a surprising exact capture, and a reproducible query. | Make it possible to explore the finding independently in minutes. |
| swyx and the Latent Space community | A full coordinator/worker cost and quality study with a replay. | Agent engineering practice with all attempts disclosed. |
| Aider maintainers and benchmark authors | Cost per successful task with transparent retries and a declared subset protocol. | A methodological comparison rather than a new unsupported overall winner. |
| SWE-bench researchers | A task subset release that exposes every request and failed attempt. | Reproducibility and harness effects. |
| Claude Code, Codex, and Grok CLI maintainers | A precise version, model, scope, and observable changed behavior. | A useful regression report or evidence of an improvement. |
| MCP and coding tool maintainers | Tool inventory, discovery, and schema overhead results on a public fixture. | Concrete interface changes they could measure locally. |
| Engineering newsletter writers | One immediately usable chart with a stable citation and clear reuse rights. | Save the editor a research task and give the reader a useful decision. |

These are prospective collaborators, not endorsements. Piebald's public release summaries are documented in its corpus; the other named venues have their own public work that makes them plausible research audiences. Prioritize fit over follower totals. [Simon Willison](https://simonwillison.net/), [Latent Space](https://www.latent.space/), [Aider](https://aider.chat/docs/leaderboards/), [SWE-bench](https://www.swebench.com/).

**Weekly editorial scorecard:** qualifying impressions over the rolling window; verified followers; per post impressions where available; profile visits; evidence page visits; study completion or raw download events; email subscriptions; and citations from other authors. Attribute a post to its claim ID and a link campaign parameter. If per post qualifying counts are unavailable, use post views as a clearly labeled proxy and the account eligibility counter for the actual target. Avoid pretending an aggregate delta identifies which post caused it.

Test one editorial variable at a time: result first versus question first; portrait figure versus landscape; one number versus a small comparison; direct evidence link versus an equivalent post whose complete evidence is visible in the image and profile. Do not assume external links are penalized. Keep category and time distribution balanced and treat small samples as directional. The metric is useful reach into the audience that cares about the work, not success at baiting generic reactions.

**10. First ten posts: complete draft copy.**

All links below are proposed launch URLs and must resolve before use. Corpus assertions inherit the seed brief's evidence scope and need the publication checks above. These are compact standalone editorial drafts, intentionally free of repeated engagement requests. Stuart should rewrite them in his own voice, inspect the actual evidence, and decide what to publish. No future eval result is invented.

**Post 01. Launch.** Visual: a three harness cover card with the corpus scope. Destination: the ready public homepage. Pin the human authored launch post.

```text
What does your coding agent send before it starts work?

We captured 482 probes across 26 Claude Code, Codex and Grok CLI versions.

KnowMoreContext opens the instruction history: model by model, version by version, with diffs and observed variants.

https://knowmorecontext.com/
```

**Post 02. The size split.** Visual: four bars from the latest certified Claude snapshot; label the surface as primary system text and show all grouped selections in the article.

```text
Same Claude Code version. Very different primary system prompts.

2.1.270:
Opus: 9,383 characters
Fable: 13,094
Haiku: 27,431

Model selection changes what gets sent. These counts exclude tools and the separate system message.

https://knowmorecontext.com/claude-code/system-prompt/
```

**Post 03. A substantial historical diff.** Visual: the actual meaningful hunk from the normalized comparison, chosen after reading it. Do not present this as a release that happened today.

```text
Claude Opus's captured primary system prompt shrank by 2,442 characters between Claude Code 2.1.261 and 2.1.269.

45 changed lines after environment normalization.

The complete diff:
https://knowmorecontext.com/claude-code/opus/changes/2.1.261...2.1.269/
```

**Post 04. The tool turn surprise.** Visual: a presence matrix, plus a caption specifying captured models and shapes. Article distinguishes transmission from accounting.

```text
Our Codex captures show two tool turn paths.

gpt-5.6 and gpt-6 families: a previous_response_id, with no system prompt in that request.

gpt-5.5 and Spark: full instructions again.

Billing needs a separate measurement.
https://knowmorecontext.com/studies/tool-turn-paths/
```

**Post 05. Why normalization matters.** Visual: one faithful noisy pair and its normalized version. Destination explains the precise replacement rules.

```text
A prompt diff can be mostly your laptop talking.

Paths, UUIDs and build suffixes made repeated captures look different. Eight normalization rules made 80 of 88 cells internally consistent.

The other 8 keep their real variants.
https://knowmorecontext.com/method/
```

**Post 06. A real variant.** Visual: exact variant hunk with source references, avoiding a fabricated usage gauge.

```text
One captured Claude Code 2.1.250 "best" variant contains:

<total_tokens>15000000 tokens left</total_tokens>

Another lacks it and an extra instruction paragraph.

That line is prompt content. It measures no usage.
https://knowmorecontext.com/claude-code/best/2.1.250/
```

**Post 07. The missing part of a size chart.** Visual: primary field and separately carried system message as distinct components. This supporting article can describe the measured scope before full secondary text publication.

```text
A system prompt size chart can miss a lot.

Our Claude captures also carry a separate system message of about 13,800 to 14,200 characters in every measured model except Haiku.

The primary field is only part of the request.
https://knowmorecontext.com/guides/system-prompt-vs-full-request/
```

**Post 08. A useful quiet result.** Visual: the exact equal length diff, with a clear zero character delta and two changed lines.

```text
Zero change in length can still hide a prompt edit.

Claude Opus, Code 2.1.246 to 2.1.247: 2 changed lines, net 0 characters after normalization.

That is why the archive leads with diffs as well as counts.
https://knowmorecontext.com/claude-code/opus/changes/2.1.246...2.1.247/
```

**Post 09. Register the effort study.** Visual: real task list and measurement protocol. Publish only when the protocol and fixtures are available.

```text
Does xhigh earn its extra spend?

Our first effort study will use the same six coding tasks, fixed starting states and independent tests.

Every attempt stays in the ledger, including failures. Results will show cost per successful task.
https://knowmorecontext.com/studies/effort-roi/
```

**Post 10. Register the flagship journey.** Visual: proposed workflow diagram clearly marked as the study design. No made up cost numbers.

```text
One orchestrator. Three workers. One final test suite.

Our next study measures the whole workflow: delegation, useful work, retries and integration.

The result will include a replay of every agent and a complete usage ledger.
https://knowmorecontext.com/studies/three-workers/
```

The first week includes several archive findings by design. Their timestamps and version pairs do the work of distinguishing discovery from breaking news. A newly published corpus page is an original editorial event; a historical harness release remains historical.

**11. Run Journeys: the interactive product worth building.**

Begin each run page with the task, the result artifact, pass/fail evidence, the full run cost basis, and elapsed time. Beneath it, show a static four lane thumbnail: orchestrator and three workers. The primary action is “Follow the run.” The browser then loads the interactive viewer. On a phone, the default is an ordered story with actor badges; on a desktop, the user can expand into a navigable graph. Nobody should need to pan a canvas to discover whether the task succeeded.

The journey has five useful frames: task accepted; delegation issued; workers acted; integration happened; tests answered. Selecting a frame reveals the exact inputs, tool outputs, decisions expressed in observable messages, and associated usage. Distinguish instructions, public assistant commentary, tool traffic, and artifacts. Do not invent a private reasoning transcript or label a reconstructed rationale as the model's actual internal reasoning.

The graph's edges represent delegation, communication, artifact dependency, or control flow with different explicit types. Time is an additional coordinate. Cross agent links can make the graph a DAG rather than a tree. The reader can color nodes by reported usage, selected model, completion state, or actor. Default to one view, then let the legend switch. The edge's thickness can represent transmitted message size where measured; it cannot silently represent dollar cost. A cumulative ledger is aligned to the same event cursor.

The killer interaction is **“show what this agent had at this moment.”** Open the assembled request segments, identify references to earlier response state, and mark any content unavailable from capture. A reader sees which brief reached the worker, which files it read, and whether the orchestrator actually received the result it later described. The public corpus's instruction snapshot becomes one linked component of that exact moment.

The second killer interaction is **“follow the dollar”**, enabled only for a stated actual or modeled cost basis. Start at the total, expand actor and workflow stage, then expand requests and attempts. Coordination and execution totals must reconcile to the overall ledger with an unclassified bucket where needed. A role label is insufficient to classify the purpose of a mixed call. Repeated references to the same exchange never add its usage twice.

For comparison, show two runs with synchronized semantic milestones, not falsely synchronized timestamps. “First edit,” “first failing test,” “worker complete,” and “final passing test” are more useful alignment points than second seventeen. A reader can compare a successful short path against a failed long path while retaining both complete histories. A “best run” spotlight must link to the distribution and all other attempts.

Use a React viewer with React Flow if node and edge inspection is the primary interaction. The library is MIT licensed. Use a freeform canvas SDK only if authoring arbitrary layouts and annotations becomes a real user requirement; tldraw currently requires a production license and its SDK is not permissively licensed. This is an interaction and maintenance choice, not simply a preference for an infinite canvas aesthetic. [React Flow](https://github.com/xyflow/xyflow), [tldraw licensing](https://tldraw.dev/community/license).

**Storage and loading proposal:** one immutable run manifest, actor records, event index, usage ledger, artifact index, and compressed event shards of roughly 100 to 250 events. Event IDs remain stable through UI changes. A public JSON export strips private details before any frontend reads it. Load the first useful frame under a 300 KB report budget, and fetch additional shards only when navigating. A 20,000 event run should still open with a result summary and a handful of visible nodes. Cluster folded subtrees and keep an accessible HTML event list beside the visual representation.

A share link such as `/runs/<id>/events/<event-id>/` renders that event's explanation and source references as HTML. Optional viewport parameters can restore a camera location, but the meaningful anchor is the event ID. “Copy receipt” exports an image and a citation containing the study revision. A 30 to 45 second narrated traversal is a stronger flagship social artifact than an unedited screen recording of the entire run.

**Replay does not mean reexecution.** Playback reads retained events. Reproduction launches new work with an explicit protocol and budget. The public site never needs access to an operator's local TM control plane to show a historical journey. A future private app can accept approved exports or connect locally through a deliberate user initiated flow; a public replay must not acquire live run controls by sharing UI components.

**12. Brand, developer surfaces, retention, and paid value.**

Keep **KnowMoreContext** as the distribution identity. In prose and the site logo, use **Know More Context** for readability. The name can encompass instructions, economics, and run histories without trapping the property in prompt archaeology. Suggested product labels: **Prompt Ledger**, **Cost Lab**, and **Run Journeys**. Suggested newsletter: **The Context Brief**. Avoid using “leaks,” “secrets,” or “hidden tax” as the brand's recurring vocabulary. The promise should sound useful to a maintainer as well as a customer.

Proposed bio: “What coding agents send. What useful work costs. Captured instructions, version diffs and reproducible evals. Built with Transport Matters.” Proposed site subtitle: “The public record of coding agent context.” Proposed domain: `knowmorecontext.com`; availability has not been checked. Prefer a durable custom domain over beginning at a repository URL and moving after it has accumulated citations.

**RSS is a first release feature.** Offer the editorial feed, one feed per harness, and machine readable releases. A person should be able to subscribe to Opus changes without receiving every Codex snapshot. Email starts as one weekly digest containing three findings, one chart, and the next registered experiment. Include the substantive summary in the email; the site supplies deeper evidence. A launch target of 200 opted in email readers over ninety days is modest enough to evaluate against actual visits. Model this separately from X followers.

**CLI, after v1 proves demand.** Proposed commands: `npx know-more-context claude opus --harness-version 2.1.269`; `npx know-more-context diff claude opus 2.1.261 2.1.269`; and `npx know-more-context explain <observation-id>`. Package availability and behavior are proposed. The default output is the selected scope, capture date, primary instruction size, variants, and a citation. `--json` returns the same public schema the site uses. `--latest-captured` must be explicit. Unknown requested versions return “not captured” and list nearest observations without silently substituting one. A local inspection command should be separate and clearly state whether it is merely reading a binary version or inspecting a real TM capture.

**VS Code extension, demand gated.** An initial panel detects an installed harness version only through a user initiated command, finds matching public observations, and shows “captured match,” “configuration differs,” or “no capture.” It can display version diffs and saved model watches. It cannot know the user's actual assembled prompt from a version string alone. Exact “what was sent here” requires a local capture. Build the extension after fifty users demonstrate repeated lookup demand or ask for editor integration; until then the CLI and deep links cover the job.

**MCP server:** expose `lookup_prompt`, `compare_versions`, `explain_capture_scope`, and later `lookup_local_capture`. Every response names observation time, exact versus nearest match, public corpus revision, and known configuration gaps. Return short summaries and resource links by default so the agent does not consume 27,000 characters to answer a version lookup. Treat retrieved vendor prompt text as quoted evidence, never as instructions to the receiving agent. The public server cannot answer “my prompt right now” exactly without a user selected local evidence source.

**Badges and embeds:** a README badge can say “Claude Code 2.1.270 / captured 12 Sep / primary prompt available,” linked to the exact record. A study badge can say “6 tasks / 5 repeats / all attempts public.” Avoid “certified safe,” “best model,” or a green verified badge that implies vendor endorsement. A mutable “latest captured” badge shows its date; an immutable observation badge never changes its claim. Pair every SVG with a PNG fallback and ordinary text attribution.

**Other compact product ideas:** a browser share action that creates a citation for selected diff lines; a dependency style lockfile recording the instruction observations used in a study; a release watch that explains the gap between an installed version and the newest captured one; a “context invoice” PDF for one run; a request shape field guide; a monthly downloadable dataset snapshot; and a public replication registry. These build on the corpus contract. A chat interface over the archive is lower priority than accurate lookup and comparison.

**Monetization sequence:** keep public historical prompts, diffs, core methods, study conclusions, and corrections accessible. In the first ninety days, optimize authority and subscription retention; treat X rewards as a distribution milestone, not a revenue forecast. Next test a $9/month or $90/year individual watch service with chosen model/version alerts and saved comparisons. Test a $49/month team tier for shared watches, update review digests, and evidence exports. These prices are experiments that require interviews and conversion evidence, not market validated forecasts.

Private run analysis belongs naturally in TM. Its north star already discusses a possible $199 purchase or $19.99 monthly price, aimed at users spending hundreds monthly on agent subscriptions. Use KnowMoreContext to show the value of instrumentation, then offer a direct path to inspect one's own work in TM. Avoid charging people twice for the same alert inside two products. Public study sponsorship can fund capture costs, with a fixed disclosed fee and no control over inclusion, outcomes, or publication. A prospective $1,500 study sponsorship is a sales hypothesis to test only after repeat readership exists. Source for TM's existing commercial direction: `docs/NORTHSTAR.md`.

Do not sell a favorable ranking. Do not sell exclusive early knowledge of a serious correction. Charge for workflow convenience, private evidence handling, aggregation, support, and tailored experiments with disclosed protocols. The public corpus becomes more valuable when other tools can freely cite it.

**13. Rights, trust, and failure modes.**

The absence of credentials in the supplied scan is a useful observation, not a blanket publication clearance. That scan covered stated patterns across the historical 482 probes. Export still needs a publication allowlist, review of newly captured fields, and handling for local identifiers, user instructions, private tool names, signed URLs, or customer content. The safe launch corpus uses controlled homes and deliberately chosen fixtures. Never repurpose an ordinary customer's full coding transcript as a public study without appropriate consent and review.

Proposed rights split: original generator/site code under MIT; original editorial text and charts under CC BY 4.0; owned factual metadata and measurement tables under CC0 where the owner has the rights to do so; vendor supplied prompt and tool text with a separate notice and upstream rights information. A repository license cannot grant rights the publisher does not hold. Mark each third party text surface distinctly and retain its source, scope, and any identified license. Some upstream code may permit redistribution under its own license; establish that provenance per item rather than inferring it from the harness brand.

**Concrete legal uncertainty:** whether full prompt republication and the capture/eval procedure are permitted depends on the relevant software license, service route terms, contract, and jurisdiction. Anthropic's current commercial and consumer terms contain reverse engineering restrictions, and its consumer terms also contain access and collection restrictions. Those clauses warrant a focused review of the actual technique and route. Their existence alone does not settle the legal classification of local outbound capture. [Commercial terms](https://www.anthropic.com/legal/commercial-terms), [Consumer terms](https://www.anthropic.com/legal/consumer-terms).

Budget a one time scoped review before broad full text distribution: the reviewer receives a real sanitized example, the capture procedure, the route/contract inventory, the intended license notices, and the proposed marketing language. Ask a concrete question about full text, excerpts, and the method. Do not rely on the fact that another corpus remains online. Fair use is fact dependent; descriptive research and commentary are relevant context, and they are not a universal permission slip. [U.S. Copyright Office overview](https://www.copyright.gov/fair-use/).

A practical fallback is to continue publishing owned measurements, editorial analysis, hashes, and appropriately reviewed limited excerpts where full text cannot be distributed. Preserve a rights status and a withdrawal mechanism per artifact. A valid takedown cannot be solved by moving the same file to another host. A withdrawn observation should retain an explanatory landing page only to the extent permitted, and public text removal may require addressing downloadable archives and repository history. Content addressing is an integrity tool; it does not override removal obligations.

**Vendor posture:** explain that the site records what a specific controlled run sent, without claiming access to vendor internal prompts beyond that request. Label capture date and scope prominently. “TM certification evidence” means TM's capture/compatibility process, never vendor certification of benchmark quality. Offer a factual correction channel and a right to supply context, while retaining editorial independence. Praise measurable improvements with the same precision used for regressions. Avoid “they secretly added” when the evidence only establishes a difference and says nothing about intent.

**Risks with concrete mitigations:** competitor speed is answered by observation depth and reproducible studies; vendor release churn by a declared capture schedule and coverage gaps; normalization mistakes by versioned fixtures and visible corrections; benchmark selection bias by registered inclusion rules and all attempt publication; alias drift by observed model identity and request digests; subscription accounting ambiguity by separate cost bases; an X policy change by email/RSS and a custom domain; graph complexity by a useful static report first; a viral traffic spike by static assets and lazy trace shards; operational overload by limiting studies to the declared budget and cadence.

**14. The durable advantages.**

A directory of text is easy to copy. An append only history of controlled, attributed captures is harder to reconstruct after a vendor version disappears. The strongest advantage is the chain from versioned instruction to registered workflow, from workflow to every request and artifact, and from those artifacts to an honest published conclusion. Give that chain stable identifiers early.

Normalization quality is a compounding asset when false collapses and missed noise become fixtures. The corpus gains value as it distinguishes observed variants, environment effects, aliases, and request shapes correctly. Each careful correction makes future captures easier to trust. A replication network adds environments TM does not own and exposes the limits of a single machine's evidence.

The public run journey is a distribution advantage because readers can inspect a memorable moment and share that exact state. The measurement contracts are an integration advantage because CLI tools, editors, researchers, and maintainers can cite the same observation. Editorial judgment is the retention advantage because it tells people which change actually deserves their time. None requires keeping the raw public facts exclusive.

**15. Decision order and the shortest useful launch.**

First, approve the editorial promise and claim boundaries: assembled requests observed under declared conditions, followed by measured agent economics. Second, give #683 the lossless archival export requirement and a complete scope label. Third, ship the static corpus on the custom domain with three useful search landing pages, all existing timelines, variants, direct downloads, six evidence articles, and RSS. Fourth, publish the first week of original observations while running the small accounting pilot. Fifth, register and execute effort ROI, then the three worker study. Sixth, turn one completed study into the first Run Journey.

The first month should leave four concrete public artifacts: a citable instruction archive, a method others can challenge, one complete cost study, and an audience that has already received useful recurring observations. The ninety day plan then has enough original evidence to publish from, and a product capable of retaining readers who arrive from one successful post.

## Round 2

**The replacement decision.** I was wrong to make the primary system prompt the v1 product and defer tool declarations and secondary messages. Publish a complete, attributed request specimen, with every instruction and tool declaration reachable through typed component views. Fable was already directionally right about this in its opening section and its proposal to include secondary messages; claiming both documents completely missed the layer would misrepresent Fable's document. Its implementation and economic claims still need substantial correction. This section supersedes the conflicting Round 1 scope, examples, and operating rules. I read Fable's full 600 line Round 1 document, decoded the actual bundles, checked body hashes, and fetched the current X policy and program terms. Lessons from the correction are recorded here under the single file instruction; no LESSONS.md or other file was changed.

**1. The layer changes, and the units need correction too.** The dominant unit is a **request specimen**: one exact captured body and its transport projection, bound to harness version, selected and observed model, effort, route, request shape, environment template, and capture time. Its first turn and tool turn can be linked into one observed exchange journey. A **tool declaration revision** is a separately addressable child artifact, reusable across specimens with the same content digest. A **change** compares two explicitly scoped specimens or tool revisions. The landing page answers “What did this configuration put in its first request?” System prompt search pages remain valuable entry points, but they open into the complete specimen. “What you pay before you type” overclaims twice: these captured requests already contain a user probe, and body length does not itemize the bill. Replace it with “What your first request contains.”

**Direct measurement corrects the supplied 86.2% headline.** In Opus bundle `5f075e0c-b10c-4679-b871-c9e1c51ec107`, probe A1, the decoded original JSON has 164,040 Unicode characters and 164,768 UTF 8 bytes. The supplied total is therefore bytes. The supplied system/tool values, 9,751 and 142,105, reproduce Python's default `json.dumps` lengths, which insert spaces and escape Unicode. They are not lengths of the original field slices. I located each value with `JSONDecoder.raw_decode` in the original body, then measured the untouched substring in UTF 8. That yields the following consistent denominator. Full body means decoded request body, excluding HTTP/WebSocket framing, TLS and compression overhead. Provenance: [Opus specimen](</Users/alphab/.transport-matters-preview/baselines/bundles/claude/anthropic/opus/5f075e0c-b10c-4679-b871-c9e1c51ec107.json>), captured 2026-09-12T22:16:50.004983Z, request SHA256 `9eaa18a0abed94a2c79faae780155ff0253038c269bd4e5141e8a4ea2629be21`.

| Original request component | UTF 8 bytes | Share of 164,768 bytes |
| --- | ---: | ---: |
| Primary `system` value | 9,676 | 5.87% |
| Entire `tools` array value | 139,195 | 84.48% |
| Entire `messages` array value | 15,436 | 9.37% |
| Other fields, property names and punctuation | 461 | 0.28% |
| `Artifact` declaration, included within tools above | 49,692 | 30.16% |

The corrected calculation strengthens the rescope while rejecting a mismatched denominator. The same slice method gives tool shares of 84.63% for Best, 82.56% for Fable, 78.06% for Sonnet, and 78.72% for Haiku in the supplied latest examples. `Artifact` is a complete declaration containing `name`, `description`, and `input_schema`; calling a description's length the whole schema is a different mistake. In this Opus specimen its original serialized declaration is 49,389 characters / 49,692 bytes; default `json.dumps` produces the supplied 50,643 characters. Against the cited 2.1.269 Opus specimen it grows by 2,030 original characters, 2,038 original bytes, or 2,068 default serialization characters. Publish the first two with named units. The two captures have different environment template digests, so that difference is observed across versions, with a configuration confound; it is not a proven effect of the binary update alone. Fable also selected another 2.1.270 Opus bundle, `e9c89203-cde8-4c78-9990-1b3edaa3e130`, whose body is 162,669 bytes. Version plus model cannot select a unique size even here.

**Messages belong in v1.** Preserve every message and content block, in original order, with its actual role and a separate semantic classification. The inspected Opus request has roles `[user, system]`, so Fable's proposed `messages[0]` system selector misses the system message. Haiku has one `user` message and no separate `role: system` message in the inspected specimen; its 15,629 byte messages value still belongs in the corpus. This prevents a field position from being confused with an instructional function. Label the controlled probe, environment context, reminders, and system message separately where the extraction proves those categories. Keep an unclassified bucket when it does not. The secondary system message in Opus is larger than the primary system value, so excluding it after this evidence would knowingly conceal a major component. Public export still sanitizes approved controlled captures; the unit does not authorize publishing unrelated user content.

**The information architecture changes.** Navigation becomes Requests, Tools, Changes, Studies. The home shows one specimen's composition with a selected model, version, capture date, shape, and environment. Its largest component is immediately inspectable; below it, an editorial explanation identifies one meaningful change. A tool page shows observed versions and models, complete declaration size, description versus parameter structure, capability changes, original order, and variants. The per model timeline exposes both whole request size and component changes. The old search landing pages survive as focused entrances, with the system view explicitly connected to the full request. Proposed URLs under `knowmorecontext.com` are:

```text
/harnesses/claude/models/opus/versions/2.1.270/     all scoped observations, both shapes
/requests/<observation-id>/                       exact specimen and complete composition
/requests/<observation-id>/tools/<tool-id>/       exact declaration inside its specimen
/harnesses/claude/tools/Artifact/                 tool timeline, model/environment facets
/changes/<from-id>...<to-id>/                     full specimen comparison
/changes/<from-id>...<to-id>/tools/<tool-id>/      one declaration comparison
/data/v1/requests/<observation-id>.json           source ranges, component refs, scope
/data/v1/tool-revisions/<revision-id>.json        immutable approved declaration
```

`tool-id` preserves namespace, tool name, and declared origin; similar names do not establish identity across harnesses or MCP servers. Slugs come from an explicit mapping that preserves the original spelling and refuses collisions. Request shape is part of identity, never inferred from sort order. Record the physical source pointer independently from the semantic component: Codex tool declarations can live under `input[].tools`, while developer messages carry instructions. This is why Fable's claim that more projections are merely a loop understates the contract change. Scope and decomposition must survive unfamiliar provider layouts.

**Normalization needs a tool specific projection, sharing the existing policy engine.** The eight existing substitutions establish a result for one text surface; they do not establish completeness for tool descriptions, JSON schemas, nested namespaces, examples, or message content. Reuse their approved environment replacements only at demonstrated locations. Add structural tool matching, explicit namespace handling, description/text extraction, and JSON schema comparison, without a second independent normalizer. Retain required fields, defaults, bounds, descriptions, examples, `$ref` values, enums, `oneOf` branches, cache annotations, and unknown fields. Do not replace arbitrary paths inside examples or erase a capability restriction because it resembles environment text. Keep raw order and cache positions in the faithful view. Sorting a tool index can aid lookup; sorting the actual tool array would hide an observed change that could affect cache reuse. Optional sorted object keys belong only to a labeled structural comparison view. V1 must prove exact component accounting, nested Codex tool extraction, system messages after index zero, preservation of meaningful parameter changes, and stability of environment substitutions. The 80/88 normalization result must not be extended to these layers without rerunning the expanded fixtures.

**Choose tool changes as the primary acquisition franchise.** A scroller rarely cares that an anonymous system paragraph moved. “One tool definition occupies 30% of this request” exposes something they can immediately understand and inspect. Pair the number with the capability the definition describes, and show the actual changed clause or parameter. A raw 50 KB schema screenshot is unreadable; the image needs a whole request composition and one legible detail. Run three tool/request stories for each system text story initially, then measure actual audience response. An important instruction change still wins editorial priority over inconsequential schema growth. This choice is about the story density in the evidence, not a rule that the biggest blob always deserves a post. The launch headline is **84.5% of this captured Opus request is tool declarations**, using consistent original body bytes. The following is draft copy for Stuart to originate afresh under the operating rule below; the specimen should be reachable from the profile:

```text
84.5% of this captured Claude Code Opus request is tool declarations.

31 tools: 139,195 bytes.
Artifact alone: 49,692 bytes, over 5x the primary system field.

2.1.270, medium effort, controlled capture. Full breakdown at KnowMoreContext. Billing remains unmeasured.
```

**2. Automation: factual policy, explicit uncertainty, literal operating rule.** I verified the live Help Center page. Under “Content will be ineligible if,” it says: **“Was created or posted using automated means”**. The rule independently covers creation and posting. No exception for deterministic charts or human approval appears in that rule. [Exact policy](https://help.x.com/en/using-x/original-content-rewards). The linked program terms put eligibility under the Help Center requirements and reserve admission and enforcement decisions to X; I cannot promise eligibility from a workflow. Content ineligibility also does not automatically prove permanent account disqualification. [Program terms, sections 3 and 7](https://legal.x.com/en/original-content-rewards-terms.html).

**(a) CI chart plus human copy and posting: unclear**, because mixed human commentary and mechanically generated figures are not distinguished. **(b) CI draft plus review and posting: treat retained automated copy as ineligible on the literal reading**; the effect of substantial human rewriting is unspecified. **(c) Detect and post without a human: clearly ineligible content.** None is an explicitly safe harbor. The lower risk case is independently authored, manually published human commentary about measured facts. Generic informational bot permission does not change rewards rules. [Automation rules](https://help.x.com/en/rules-and-policies/x-automation).

**Our operating rule, stricter than an unverified interpretation:** CI may capture, validate, calculate, render research figures, and publish the website/data/RSS. It stops at an evidence report, without X credentials, generated social copy, or an X publish action. Stuart reads the evidence, chooses the point, writes the post himself, checks the cited measurement, and presses Post manually. Initially use text only: no pasted AI/template drafts, CI cards, scheduled posting, or generated preview images. Put the evidence directory in the profile and name the specimen in the post where needed. Human designed figures can be considered separately, but they are not the CI cards in case (a). Keep that case out of the rewards plan until X answers it specifically. This retires my Round 1 suggestion that CI editorial drafts were an appropriate default for this account. There is no honest “guaranteed eligible” rule available from the published language; the operational response is to exclude unresolved cases, not quietly assume manual review cures them.

**3. Codex: the supposed first turn collapse is a selection error.** I decoded every stored `raw_request_base64` for gpt-5.6 Sol, Luna and Terra at 0.153.4 and 0.154.0 without upgrading the historical bundles. All 18 old first turn probes and all 9 new first turn probes carry three developer role input items, including an `additional_tools` item. None of those 27 first turn bodies contains `previous_response_id` or a `prompt` template reference. The six new tool turn probes all contain `previous_response_id` and a tool result. These are correctly labeled `tool-turn` in the stored cells. Their original lengths range from 1,982 to 3,631 characters. Fable's 2,203 and 3,714 figures exactly reproduce default `json.dumps` lengths for Sol and Terra tool turns, respectively. I cannot identify the line in Fable's analysis that mixed them, because its analysis script is not in the document; the raw records settle which shapes those numbers belong to.

| Version / selected model / effort | Stored shape | Probes | Original body characters | Default `json.dumps` characters |
| --- | --- | ---: | ---: | ---: |
| 0.153.4 / Sol / low | first-turn | 3 | 56,159 | 56,519 |
| 0.153.4 / Sol / xhigh | first-turn | 3 | 56,207 | 56,567 |
| 0.154.0 / Sol / xhigh | first-turn | 3 | 56,209 | 56,569 |
| 0.154.0 / Sol / low | first-turn | 2 | 60,412–60,413 | 60,771–60,772 |
| 0.154.0 / Sol / low | tool-turn | 2 | 1,982–2,138 | 2,047–2,203 |
| 0.154.0 / Terra / low | tool-turn | 2 | 3,631 | 3,714 |

**What actually changed in the comparable bodies:** the older and newer Sol xhigh captures both carry the same 17,730 character core developer instruction, with SHA256 prefix `a91357a1cd27`, and the same three nested tool leaves. The top level `instructions` and `tools` fields are absent in both versions; instructions are in `input[].content[].text`, and tool declarations are in `input[type=additional_tools].tools` under a namespace. Their absence at the top level is no evidence of absence on the wire. The newer low effort Sol capture instead has a 21,261 character core developer instruction and five nested tool leaves. Its environment template differs from the historical captures, so that is a configuration scoped change requiring attribution, not proof the CLI version alone changed the prompt. Both versions' stored envelope projections name WebSocket and `chatgpt.com/backend-api/codex/responses`. There is no observed endpoint switch explaining the supposed collapse.

**A concrete complete chain:** Sol's new first turn bundle is `43455716-21d1-4255-b5de-bd540eec9e7e`; its tool turn bundle is `e61b4687-d6ef-4b29-81ca-dd0edb849abc`, both under `/Users/alphab/.transport-matters-preview/baselines/bundles/codex/codex/gpt-5.6-sol/`. Their A1 probes share run `7f067d60-e14b-4874-8e17-b934d5abd01e`. The first body is 60,413 characters. The 2,138 character body contains `previous_response_id` and `custom_tool_call_output` for call `call_QXklPulpIMYD6CBjgchmKIVA`. Its retained, hash checked transcript shows the user request at 09:41:16.637Z, the matching `exec` tool call at 09:41:19.107Z, its output at 09:41:19.238Z, and completion at 09:41:21.233Z on 13 September. Thus this is a continuation after a tool result, with the first request also retained. Terra tool bundle `d82b3ec7-da7f-4cba-9ca2-4f1a5c3fd86c` supplies the exact 3,714 reserialized count. Old Sol low bundle `814cc552-6376-4a14-94b3-edce58d2ff52` supplies the 56,519 comparison count. These identifiers make the diagnosis repeatable.

**Candidate explanations adjudicated:** continuation reuse explains the small bodies; a different stored request shape explains the false comparison. A newly referenced server prompt is unsupported: no `prompt` reference exists in these bodies, and the real first turn still transmits developer instructions and tool definitions. A missing first request is disproved for the demonstrated run by its retained paired bundle. The endpoint projection is unchanged. The bundle classifier is correct in the inspected cases. `prompt_cache_key` must not be relabeled as a hosted prompt identifier. OpenAI's public documentation describes `previous_response_id` plus new input items as continuation and distinguishes a prompt template reference from a cache key; the actual consumer Codex endpoint remains proven by its own capture, not by assuming public API parity. [WebSocket continuation](https://developers.openai.com/api/docs/guides/websocket-mode), [Prompt and cache fields](https://developers.openai.com/api/reference/cli/resources/responses/methods/create). No live provider call is needed to settle this anomaly. The server may have additional internal instructions, which outbound capture cannot establish either way; that separate boundary does not rescue the claimed first turn collapse.

**Reproduction and a product guard:** the following command reads the original files, verifies their body digests, and prints the shape beside both length conventions. It writes nothing. The future exporter should also validate observed continuation evidence against the declared shape, require shape in every observation key, traverse nested tool declarations, and refuse to turn an unrecognized instruction carrier into a zero sized prompt. TM already implements nested tool extraction in `codex/request_parser.py` and `codex/tool_definitions.py`; reuse it. Neither the generator nor the editorial ranking should infer shape from whichever bundle happens to be last.

```sh
python3 -B - <<'CHECK'
from pathlib import Path
import base64, hashlib, json
root = Path('/Users/alphab/.transport-matters-preview/baselines/bundles/codex')
for path in sorted(root.rglob('*.json')):
    bundle = json.loads(path.read_text()); cell = bundle['cell']
    if cell['harness_version'] not in ('0.153.4', '0.154.0') or not cell['launch_model'].startswith('gpt-5.6'): continue
    for probe in bundle['probes']:
        raw = base64.b64decode(probe['raw_request_base64']); request = json.loads(raw)
        assert hashlib.sha256(raw).hexdigest() == probe['raw_request_sha256']
        print(path.stem, cell['harness_version'], cell['launch_model'], cell['effort'], cell['request_shape'], probe['label'], len(raw.decode()), len(json.dumps(request)), bool(request.get('previous_response_id')))
CHECK
```

**4. Three ideas from Fable I am adopting, because my Round 1 did not contain them.** **First: “A per-tool RSS feed so people who care only about `Bash` subscribe to that.”** Adopt it alongside the new independent tool timeline. This is a precise retention mechanism for tool authors and power users; a harness feed is too broad for someone investigating one declaration. Include model/environment filters and send an item only when the selected declaration revision changes. **Second: “the first version of an instruction and every edit since, one instruction per post.”** Adopt clause archaeology for tool descriptions as well as system instructions. It answers “when did this behavior enter the captured instructions?” and makes old evidence useful without inventing breaking news. A relocation continues the clause lineage; ambiguous matches remain manual. **Third: “A 'diff this prompt against yours' paste box” with comparison “client side.”** Adopt the local comparison concept, expanded to a sanitized request or tool declaration. My earlier CLI lookup and capture links did not offer this immediate browser interaction. Do not upload pasted content, persist it, or put it in analytics. A local parser can show exactly which observed scope matches and where the user's configuration differs. This is a useful onboarding route into TM when the user wants a fresh capture.

**The three weakest claims, rejected.** **First, automation:** Fable says the weekly cards “can post via the X API on a schedule because their copy never needs judgement.” Rejected. It tests editorial repetitiveness where the relevant rule concerns automated creation and posting. Six weeks of manual operation establishes no exemption. Delete the automatic X publishing milestone; retain website automation and human publication under section 2. **Second, economic attribution:** Fable proposes “bytes and `usage.input_tokens` per layer” and the headline “72% of what you paid for was the harness talking to itself.” Rejected. Aggregate provider usage does not supply layer token counts; characters cannot be allocated as billed tokens, cache categories differ, and subscription charges are not a per request token invoice. The corrected 84.48% here is a body byte share only. Publish separate measured composition and whole request usage; a cost allocation model must be labeled and cannot become a fabricated receipt. **Third, variant causality:** Fable says the `<total_tokens>` line “is a quota-driven injection” and proposes a regex that labels its cause `quota_injection`. Rejected. The string establishes the presence of an instruction, not where its number came from or whether it tracks the user's remaining allowance. Label its observed form `token-budget-text` and its cause `unknown` until a controlled quota change or the producing code establishes the link. Regex may classify syntax; it cannot manufacture provenance.

**My changed mind, with a rule that survives the correction.** Scope the public product around the complete request before optimizing one easy extraction surface. Measure a part and its denominator in the same representation, retain the source span, and bind every claim to its actual request shape and configuration. Tool declarations and message instructions ship in the first useful release. The Codex false alarm becomes a regression fixture for the publication pipeline, not a launch story about hidden instructions. Automated website evidence remains central; automated X content leaves the rewards plan. Astro static output with a React journey island still fits, because richer evidence changes the data model and the reading experience before it changes the hosting requirements.

## Round 2b

**The stronger finding is a template migration with an unresolved cause.** Sol's new core instruction is the instruction Astra already carried on 7 September, with exactly one substitution in the opening line: GPT-6 becomes GPT-5. That makes the change more interesting and the universal server rollout claim less defensible. I was wrong to let resolving the small continuation requests close the investigation. The same version can retain its request shape and still change the instructions inside it.

The accepted launch measurement remains 139,195 tool bytes, 15,436 message bytes, and 9,676 system bytes within a 164,768 byte Claude 2.1.270 Opus request. These are original UTF-8 body slices, totaling 164,307 bytes, with 461 bytes in the remaining fields and framing. The 84.48% tool share belongs on the launch card. The character measurements below describe decoded instruction text and have a separate denominator.

### 1. What the whole bundle tree actually controls

I scanned all 176 JSON bundles beneath `/Users/alphab/.transport-matters-preview/baselines/bundles`: 119 Claude, 40 Codex, and 17 Grok. This snapshot contains 486 probes, comprising 335 Claude, 104 Codex, and 47 Grok. Every decoded request matched its stored SHA256. The earlier 482 figure should retain its own snapshot attribution.

Grouping held harness, version, model, and request shape constant. I looked both for one effort on multiple dates and for multiple efforts on one date. Three first turn groups satisfy the first condition; nine satisfy the second. No tool turn group satisfies either. Dates below are UTC bundle generation dates. Where Claude and Codex transcripts expose timestamps, their days agree with the bundle day. Grok's retained records did not supply that same timestamp check, so its dates remain bundle dates.

| Same version, model, and effort on two dates | Probes | Instruction observation | Why it falls short of the Sol control |
| --- | --- | --- | --- |
| Claude 2.1.263, opus[1m], high: 6 and 7 September | 3 + 3 | Both primary system texts are 12,136 characters. The inspected pair becomes identical after UUID substitution alone. | Different harness and model. |
| Codex 0.153.4, gpt-5.6-luna, medium: 5 and 7 September | 3 + 3 | Core instruction is exactly 17,730 characters with hash prefix `a91357a1cd27` in all six probes. | Older binary, different model, earlier dates; capture template also changed. |
| Grok 1.0.13, grok-4.6, medium: 30 August and 7 September | 3 + 3 | System input text is exactly 6,057 characters with hash prefix `63f2afe426fa` across both bundles. | Different provider and dates; capture template changed. |

| Same version, model, and date at multiple efforts | Probes | What the control says |
| --- | --- | --- |
| Claude 2.1.250, fable[1m], 28 August: low/high | 3 + 3 | The inspected system diff changes the memory, workspace, and scratchpad paths. Its 180 character size difference is environmental. |
| Claude 2.1.263, opus, 7 September: low/medium | 6 + 3 | Two separate low bundles are present. Even the same effort has different raw sizes, so raw length alone cannot identify an effort effect. |
| Claude 2.1.263, opus[1m], 7 September: low/high | 3 + 3 | The inspected system differences are memory, workspace, and scratchpad paths. |
| Claude 2.1.270, opus[1m], 13 September: low/high | 2 + 3 | The inspected differences are the cc_version suffix and memory path. |
| Codex 0.153.4, gpt-5.3-codex-spark, 7 September: low/medium, plus unset effort | 3 + 3 + 3 | Top level instructions are exactly 13,802 characters, hash prefix `bbf233330fc2`. Unset effort is an additional observation, not a third established effort level. |
| Codex 0.153.4, gpt-5.6-luna, 7 September: low/medium | 3 + 3 | Identical 17,730 character core instruction. This connects to Luna's medium effort capture on 5 September, giving an L-shaped historical control. |
| Codex 0.153.4, gpt-6-astra, 7 September: low/medium/high | 3 + 3 + 3 | Identical 21,261 character core instruction in all nine probes. It already includes the new permission and persistence sections. |
| Grok 1.0.13, grok-4.5, 7 September: low/medium | 6 + 3 | All nine system input texts have the same `63f2afe426fa` hash prefix. |
| Grok 1.0.13, grok-4.6, 7 September: low/medium | 6 + 3 | All nine system input texts have that same hash prefix. This also connects to the earlier medium effort bundle. |

The inventory is exhaustive for the stated grouping. Content comparisons are explicitly scoped to the named carrier. Identical core instructions do not establish identical whole requests, tools, runtime instructions, or provider behavior.

**The decisive near miss is Astra.** Its core instruction has full SHA256 `152dfaeeb552876190962be1c12c93d426840ff12691f648261554a7675a6698` in 14 probes: nine on 0.153.4 on 7 September at low, medium, and high; three on 0.154.0 on 10 September at high; and two on 0.154.0 on 13 September at low. Its 0.154.0 date/effort coordinates have the same confounding pattern as Sol, but its core text did not change. Its surrounding skills and environment material did change. We must not describe Astra as replicating Sol's core instruction rewrite.

The 0.154.0 inventory has two first turn bundles on 10 September, Sol/xhigh and Astra/high, each with three probes. Its eight first turn bundles on 13 September all use low, with two probes each: Sol, Luna, Terra, Astra, Spark, gpt-5.5, gpt-reserve, and codex-auto-review. There is no missing control hiding elsewhere in that version.

A further counterexample to a universal rollout: on 13 September, Luna, Terra, Reserve, and Auto Review still carry the old 17,730 character core at low effort, while Sol carries the new core. Low effort therefore does not select the new core universally across models. A Sol-specific effort rule remains possible.

### 2. Reading the entire 208 changed lines

I reproduced 20,341 and 22,923 characters and exactly 208 added/deleted lines with Python's unified diff. That extraction takes the first text block of each developer item and appends two newlines per item, including the developer `additional_tools` item with no text. Its six separator characters are exporter formatting.

This reproduction matters because that convenient extraction is incomplete:

| Measurement of Sol developer instructions | 10 September, xhigh | 13 September, low | Change |
| --- | ---: | ---: | ---: |
| Core instruction, first developer message with content | 17,730 | 21,261 | +3,531 characters |
| First block of the later developer message, the skills catalog | 2,605 | 1,656 | -949 characters |
| Reported first-block extraction, including separators | 20,341 | 22,923 | +2,582 characters |
| All developer text blocks, excluding added separators and tool declarations | 22,672 | 24,607 | +1,935 characters |

The later message also carries permissions and environment material. The older request carries an additional 646 character collaboration mode block. Dropping it and changing the environment block by one character explains the difference between +2,582 and +1,935. The core contributes 203 changed lines; the skills first block contributes five, including three removed skill entries and a replaced path line. None of these text totals represents the size of all developer-role content, because the tool declarations occupy another developer item.

**My content judgment: this reads like adoption of a general instruction template.** The permission additions govern prior authorization, preparation before deployment, external messages, and explanations of approval rejection. The persistence additions govern unfinished tasks, ambiguous action requests, and whether new user input redirects ongoing work. The instruction to “persist until the user's intended goal is complete” applies to task completion, independent of a named reasoning budget. The new paragraph begins “The user gets very frustrated when you stop and ask for confirmation or permission” and requires an explanation for the interruption. It does not discuss token ceilings, low effort, or shortened reasoning.

The rest of the rewrite strengthens that reading. It replaces personality and writing guidance, changes the treatment of new messages and compaction, adds PR writing instructions, changes visualization policy, rewrites skill discovery and precedence, and adds Apps and Plugins sections. That is a broad operating contract. Effort tuning could plausibly add persistence to compensate for low effort, but it does not naturally explain a wholesale replacement of plugin documentation and prose style.

The strongest evidence is the exact match to an existing template. Sol's 13 September core differs from Astra's 7 September core only in the opening model identity. Sol's new core hash is `1700fc8930c0ac7420cae84532a553131bca47d0065e12d22647727e79af8f03`; its old hash is `a91357a1cd2727a0be06d461248d6e3a7274746e38108f548a3adf2cc2430415`.

**My ranked explanation:** Sol began selecting the newer instruction family between the observed requests. A change in remotely supplied model configuration is plausible. A Sol-specific effort selection rule is also compatible with every observed Sol request. A change in capture configuration remains a third explanation to test. Calling this a product-wide rewrite first introduced between 10 and 13 September is contradicted by Astra's earlier text and by the older text retained by other models.

The capture template is a real additional confound. The older captures use content digest `d5edf2f03760550d4da43381dcf6a32a8e244ea76820677293e28e10a6eab1e2`; the later captures use `ef4fa3d7235d27003f147fd5dd539372cbe6450e125ed15ca591255e9e55535f`. Their `generated_from` values differ too. The unchanged launch requirements digest does not make the templates identical. This certainly affects the surrounding skill catalog. Astra retaining its core across that template change weakens a universal template substitution explanation, but cannot eliminate a model-specific interaction.

The bundle version establishes the reported CLI version. It does not independently prove identical executable hashes, unchanged local configuration, identical server model catalogs, or identical account experiment assignment. Those are the missing attribution facts.

**Publishable language today:** “Codex 0.154.0 sent two instruction families for Sol. The newer one matches Astra's existing instructions, apart from model identity. Effort, date, and capture configuration changed together.” That is already a substantial observation. The corpus should group revisions by content digest within a binary version and show first/last observed timestamps, effort, and environment alongside them. A version-only URL needs observation children, for example `/codex/gpt-5.6-sol/0.154.0/observations/<observation-id>/`.

For a direct reproduction, read Sol bundles `c70f6bd0-02cd-43c1-9e8a-567e8b87061a.json` and `43455716-21d1-4255-b5de-bd540eec9e7e.json` under `codex/codex/gpt-5.6-sol/`. Astra's 7 September high bundle is `5503c3ed-3017-4044-8192-2af9e8af95f1.json`, its 10 September high bundle is `83f2cdc9-494f-4d89-8d91-561c38c367a9.json`, and its 13 September low bundle is `a436dbf0-e920-49eb-b5ab-b48aea0a1358.json`, under `codex/codex/gpt-6-astra/`. Decode each probe's `raw_request_base64`; select `input[]` items whose role is developer, then the first item that actually has content for the core. The earlier additional_tools item has a developer role and no content; treating it as the core would repeat the missing-instructions error.

### 3. The smallest useful capture experiment

**Run four fresh Sol first turns tonight.** Use Codex 0.154.0 and one pinned runtime template, preferably the exact retained 13 September template. Use the same executable hash, account, route, workspace content, skills, permissions, collaboration mode, and prompt in all four runs. Use a new conversation each time, with no `previous_response_id`. The fixed prompt can be “Reply with exactly ALPHA.” Record the effort actually present in the outgoing request.

| Model | Effort | UTC date | Fresh probes | Purpose |
| --- | --- | --- | ---: | --- |
| gpt-5.6-sol | low | 2026-09-14 | 2 | Replicate today's low template. |
| gpt-5.6-sol | xhigh | 2026-09-14 | 2 | Fill the missing contemporaneous effort control. |
| gpt-5.6-sol | low | 2026-09-15 | 2 | Hold effort constant across a prospective date change. |
| gpt-5.6-sol | xhigh | 2026-09-15 | 2 | Complete the prospective 2 x 2 design. |

Tonight's order is low, xhigh, xhigh, low, within one short session. Reverse the order tomorrow. Keep each day's captures on its specified UTC day; if execution slips, label the actual date instead of backdating. Four first requests tonight, eight across both days. No tool turns are needed to answer the instruction question. Two probes per cell expose gross within-cell variation; they do not certify the absence of a rare rollout variant.

Compare the complete core strings first, then all developer text blocks and tool declarations separately. Save incoming model/configuration responses and cache provenance if the harness obtains instructions through them. A changed remote model descriptor that supplies the changed text is much stronger source attribution than the outbound request alone. A response identifier or prompt cache key by itself does not supply that proof.

**Interpretation rules, fixed before capture:**

1. Low consistently produces the new core while xhigh produces the old core in an interleaved session: confirms an effort-associated selection under the pinned current conditions. Repeating that split tomorrow supports a stable effort rule. Historical attribution still needs the source of that selection.
2. Both efforts consistently produce the new core tonight: falsifies the simple, persistent “low gets new, xhigh gets old” explanation today. Relative to the old xhigh captures, it supports a temporal or configuration change. It does not establish that the change happened specifically between 10 and 13 September.
3. Both efforts change together between tonight and tomorrow, with local inputs held fixed: confirms an observed temporal change independent of effort in this experiment. The captured upstream descriptor or other provenance must establish whether its source was remote.
4. Both efforts retain the same core on both nights: establishes present stability. A historical rollout may already have finished; this outcome cannot disprove it.
5. Identical cells alternate between cores, or the effect differs by day: simple date-only and effort-only stories fail. Investigate experiments, caching, routing, and interactions. Report variants rather than averaging the instructions.

**One conditional addition for the third confound:** if tonight's four requests all show the new core and the historical runtime template can actually be restored, add two Sol/xhigh first turns tonight using the exact 10 September template, with everything else held fixed. A reproducible return to the old core would implicate local template/configuration selection. Retaining the new core would weaken that explanation. This brings tonight to six first requests, only when the extra comparison is available and informative. Merely labeling a reconstructed directory with the old digest is insufficient.

A second model is unnecessary for the first decision. Astra already supplies unusually strong archived controls. Spend on a second model after Sol produces an interpretable result.

**There is no honest promise that tonight can conclusively reconstruct 10 September.** No capture can be backdated, and a remote rollout cannot be forced to recur. The decisive historical evidence would be retained instruction-bearing remote model responses from both dates, compared while holding local overrides constant. If those were never captured, the product must preserve the causal uncertainty. Binary extraction competitors can miss remotely selected instructions, but these bundles alone do not establish that a remote change caused this particular difference.

### 4. X policy: what I retrieved and what I overclaimed

On 14 September I reopened the exact Help Center URL with the browser tool's direct URL open operation. It returned a parsed HTML page labeled “Crawled: today,” with 385 lines. The relevant lead-in is at line 103 and its bullet at line 111. This was a returned page body, rather than a search-result snippet. The tool does not expose enough transport metadata to attest to an uncached origin fetch or an authenticated account view.

Exact wording, preserving the page's lead-in and bullet fragment:

> Content will be ineligible if:
>
> Was created or posted using automated means

That is the actual wording I relied on. The second line is a list fragment, so manufacturing a longer purported policy sentence would be inaccurate. [X Original Content Rewards policy](https://help.x.com/en/using-x/original-content-rewards)

The policy also recognizes personally produced or designed work and substantive original perspective. It supplies no chart-specific explanation of the automation clause. The clause directly concerns content eligibility; its existence alone does not prove that a single ambiguous chart permanently disqualifies the entire account. Account enforcement and admission remain discretionary. [X Original Content Rewards policy](https://help.x.com/en/using-x/original-content-rewards)

**The strongest case for Fable:** Stuart designs the experiment, owns the captures, selects the comparison, chooses the visual encoding, verifies the result, and writes the interpretation. A script draws the resulting chart. The human intellectual contribution is substantial and original; mechanical rendering can reasonably be understood as production tooling, comparable to a spreadsheet exporting a chart. A human authored chart does not become authorless because software draws its pixels. On this reading, the target of the exclusion is automated content production and distribution without meaningful authorship.

**The strongest case against Fable:** an unattended CI job that detects an event, chooses a story, fills a recurring layout, and emits a finished social image is creating a content artifact automatically. The policy separates creation from posting, so pressing Post manually does not clearly resolve the creation issue. Human written copy alongside the image may or may not change how X judges the combined post. Nothing retrieved establishes an exception for original experimental data.

These are competing interpretations. The argument for charts is persuasive enough that my earlier claim of a necessary blanket ban was too strong. Fable's categorical safe harbor for CI cards is also unsupported. The uncertainty is about where X draws the authorship boundary.

**I soften the blanket text-only rule and retain a narrow hold on unattended CI social cards.** Stuart can personally design a chart in a normal authoring tool, select its data and annotations, inspect the final image, write his own copy, and post manually. That is the strongest case for a personally designed graphic, although no operational method guarantees admission. CI may compute evidence and render research graphics for the site immediately. Whether its unattended finished cards may be attached on X remains the specific unresolved question.

The distinction is substantive human authorship. Clicking Export on an automatically selected, finished CI card supplies little new authorship. Personally choosing and constructing the chart's comparison, layout, labels, emphasis, and interpretation supplies much more. I would not ask Stuart to hand draw bars or calculate numbers manually.

### 5. A staged operating rule Stuart can follow literally

**Days 1 through 7:** launch original human written posts now. Keep the website, corpus, RSS, and research graphics fully automated. Keep X publishing credentials out of CI. Stuart writes the social copy and publishes through X himself. Personally designed graphics are available under the narrower authorship interpretation above; reserve the unattended CI card franchise while seeking a written program-specific answer. If minimizing unresolved eligibility risk outranks every other concern, use the three text formats below for this first week.

Stuart should ask X support in writing, through an available account support channel: “I run original measurements of coding tools. Software computes the results and CI renders a chart from a template I designed. I choose which experiment to discuss, verify every number, write all post text myself, and manually attach the chart and publish. Is this content eligible for Original Content Rewards? Does your answer differ if I construct each chart manually in a charting application? Please address automated creation separately from automated posting.”

This is a proposed inquiry for Stuart. No message has been sent. Ask about this rewards program specifically; a statement that an automation tool is allowed on X generally would not settle rewards eligibility.

**When a specific written answer arrives:** introduce the CI chart workflow only to the extent the answer actually covers it. Preserve that answer and the production method it described. Begin with three manually posted chart posts, each with original analysis. Continue human copy and publication. Fully automatic detection and posting stays outside this rewards strategy.

**At day 7 without an answer:** inspect the actual reach and decide how much effort to put into personally designed graphics. An unanswered support request does not authorize CI attachments. If rewards eligibility remains a hard constraint, retain the narrow hold. If Stuart later ranks audience growth above uncertain rewards eligibility, he can explicitly choose the CI chart risk, but the strategy must then state that its eligibility assumption is unresolved. No invented timeout turns ambiguity into approval.

**Price the delay in impressions.** Using Round 1's planning target of 600,000 qualifying impressions over 90 days gives an average of 6,667 per day. These are scenarios, not measured causal effects of images:

| Time spent on text while the visual workflow waits | If text retains 25% of planned visual reach | If text retains 50% | If text retains 75% |
| --- | ---: | ---: | ---: |
| 7 days | 35,000 foregone impressions | 23,333 foregone | 11,667 foregone |
| 14 days | 70,000 foregone impressions | 46,667 foregone | 23,333 foregone |

At 50% retention, a seven day wait consumes about 23% of the plan's 100,000 impression buffer above the threshold. A fourteen day wait consumes about 47%. The early launch's actual reach may differ substantially from the 90 day average, and original Home Timeline impressions from verified users must be tracked separately from headline views.

This is why I reject an unexamined indefinite text-only strategy. A personally designed weekly chart costs human production time but preserves much of the intended visual product while the CI question is unresolved. Budget 30 to 45 minutes for that chart and compare its reach with the text posts. That time budget is a production target, not an observed result.

There is no defensible dollar break-even calculation without Stuart's value for eligibility, X's enforcement probability, and actual payout economics. The rational decision under a hard eligibility constraint is to automate measurement, preserve human authorship, seek the narrow written clarification, and measure the cost of waiting.

### 6. Text posts that carry a diff

Use short vertical comparisons, literal plus/minus lines, and a specific behavioral consequence. X post bodies do not reliably provide monospace formatting; aligned ASCII tables and Markdown code fences are poor dependencies. One claim per original main-timeline post, with the version or observation coordinates visible. The corpus URL belongs in the same post when it fits; these examples use no image or preview.

These are writing examples requested for this brainstorm. Under the conservative authorship rule, Stuart should compose his published wording himself from the verified findings rather than copying agent-written drafts verbatim.

**Post A: the clause arrived.**

```text
Codex 0.154.0. Sol. Same version.

Sep 10 / xhigh:
- no dedicated permission section
Sep 13 / low:
+ "When to ask the user for permission"
+ "Autonomy and persistence"

Date and effort both changed. The instruction changed. The cause is still open.
```

**Post B: the existing template.**

```text
The Sol prompt rewrite has a predecessor.

Astra, Sep 7:
- "based on GPT-6"
Sol, Sep 13:
+ "based on GPT-5"

The rest of the 21,261-character core is identical.

An existing template reached another model. Why it was selected is the next experiment.
```

**Post C: the chronology that punctures the headline.**

```text
Was Codex's new permission policy introduced Sep 13?

Astra / Sep 7 / low, medium, high:
+ permission section
+ persistence section

Sol / Sep 10 / xhigh:
- both absent

Sol / Sep 13 / low:
+ both present

The corpus needs a model timeline inside every version.
```

Post A sells the changed instruction and the open question. Post B sells an exact match that a reader can verify. Post C turns chronology into the reveal. Each is an original main-timeline post concept; none needs a reply thread to carry its argument. Alternate these behavioral stories with the launch composition numbers, because a byte-count account needs both what changed and why the text matters.

**The correction I am carrying forward:** distinguish an observed revision, its textual ancestry, the coordinate correlated with it, and the mechanism that caused it. Likewise, distinguish policy wording from my interpretation of a production workflow. A corpus whose strongest posts survive its own adversarial review has a more durable advantage than one that merely notices a large number.

## Round 3: The Launch

**Launch decision.** Bring KnowMoreContext to life as a record of the instructions coding harnesses actually send and the changes observed in those requests. Lead with the complete request composition, then show why pinning a CLI version does not pin its instructions. The recurring product is the observed change stream, including changes inside an unchanged binary version.

Stuart's controlled captures close the effort explanation for the observed Sol change. I accept his reported server/catalog attribution and withdraw that remaining hypothesis from the launch narrative. I also withdraw the earlier claim that “Autonomy and persistence” first appeared in the newer template. I independently checked the historical Sol and Luna cores again: the older text already contains that heading at level two, while the newer text uses level one and rewrites its guidance. The earlier Round 2b posts claiming absence must not be used. These ten launch posts supersede the previous copy.

This section supplies the launch plan. Fable's proposal owns the repository, snapshot schema, extractor implementation, and URL design. The publishing boundary below specifies what evidence the launch needs from that implementation.

**Evidence register and permitted numerical claims.**

V means independently checked by Astra in the retained bundles during this session. S means measured and reported by Stuart in this session, accepted here but not independently reread from the preview database by Astra. P means a proposed operating target or an arithmetic scenario, never a measured performance result. These labels apply to the entire claim, including its unit and scope.

| ID | Evidence | Permitted use |
| --- | --- | --- |
| V1 | Claude 2.1.270, opus, first turn, medium, bundle `5f075e0c-b10c-4679-b871-c9e1c51ec107`, probe `a1`: body 164,768 bytes; tools 139,195; messages 15,436; system 9,676; other 461. Artifact declaration: 49,692 bytes. | Exact figures only with this probe identity. Headline: tools about 84%; system field under 6%; Artifact roughly five times the system field. |
| V2 | All five 2.1.270 Opus first-turn probes in the current bundle scan pass byte-identical compact serialization and body hash checks. Their measurements differ. | Rounded statements scoped to these captured Opus requests. Any exact composition attaches to an individual probe. |
| V3 | Sol's September 13 core matches Astra's September 7 core except the GPT-5/GPT-6 identity substitution. | A template reuse story with the historical pair identified. Do not substitute today's equal stored lengths for this historical exact-text proof. |
| V4 | The small Codex request previously misidentified as a first turn is a retained tool continuation; its paired first request is present. | Explain request shape and continuation without claiming missing capture or a vanished first prompt. |
| S1 | Six fresh runs on Codex 0.154.0 in a bare `tm/capture` home. Sol at low, high, and xhigh yielded byte-identical instruction component sets, with reported `system_set_hash` prefix `19a6dedc`. | Effort did not select a different instruction set in this controlled test. The prefix is a display identifier; equality comes from the reported complete-set comparison. |
| S2 | Same binary, day, and effort: Luna 17,730; Sol 21,261; Astra 21,261 characters in the reported JSON-escaped stored-blob representation. Sol and Astra differ despite equal lengths. | Compare those stored blobs with each other. Do not relabel these quantities as request bytes or merge them with decoded historical character counts. |
| S3 | Sol changed again after the September 13 bundle: 24 changed lines at the same CLI version. Stuart reports two server-side revisions within four days. | An observed repeat event and a reason to monitor between releases. Its exact capture timestamps, pair, and diff convention belong in the public receipt. |

The latest experiment's run identifiers and the full latest diff were not supplied to Astra. Mark S1 through S3 as owner measurements in the launch evidence ledger until the corresponding raw receipts are linked. The public release should carry those receipts before the associated posts go live. Do not invent an etag, hash suffix, capture timestamp, line excerpt, or missing run identifier.

**The measurement contract, expressed as generator rules.**

1. The measurement subject is one probe. Its identity includes the source bundle or run/exchange identity, probe label where present, harness, binary version, model, request shape, capture timestamp, and recorded effort/configuration. Store a request-body digest alongside it. A page for a model or cell is a collection of observations; it does not automatically have one composition percentage.
2. Decode `raw_request_base64` to the captured body bytes B. Require the stored body SHA256 to match. The denominator is `len(B)`. Label it “captured request body bytes.” It excludes HTTP headers, WebSocket framing, TLS, and responses. A transport envelope can appear beside the body without entering this denominator.
3. Measure JSON value spans in that original byte representation. For the launch fixture, the `tools`, `messages`, and `system` values include their own JSON delimiters and escaping. The remainder covers all bytes outside those selected values, including other fields, property names, and outer punctuation. Call it “other fields and framing.”
4. A compact serializer is a permitted fast path only after an exact whole-body equality assertion. Use UTF-8 with `ensure_ascii=False` and compact comma/colon separators; verify that the resulting bytes equal B, not merely that their lengths agree. If equality fails, use original byte spans or withhold that composition metric. Default `json.dumps` output cannot be divided by a captured-byte denominator.
5. The layer spans must be disjoint within that probe. Their byte lengths plus the remaining bytes must equal the captured body length exactly. An Artifact declaration is a child inside the tools value; it must not be added again to the body total. The same discipline applies when tools and instruction text are nested within Codex input items.
6. Retain integer numerators and denominators. Compute percentages from those integers at display time. For V1 only, the results are tools 84.48%, messages 9.37%, system 5.87%, and remaining fields/framing 0.28%. Bind every precise percentage to V1's probe. Rounded displayed percentages need not add exactly because of rounding; the integer byte partition must.
7. Measurement precedes normalization and redaction. The reading diff may normalize declared environment noise, including environment-specific MCP naming under the proposal's explicit rule. It must preserve the original measured sizes, the normalizer revision, and a transformation record. A cleaner canonical diff is not a smaller captured request.
8. Store the representation on every metric: captured UTF-8 bytes, decoded text characters, JSON-escaped stored-blob characters, or a declared line-diff count. Reject comparisons across representations. A body share does not establish a token share, cache cost, or spend share.
9. Reject any machine-generated claim that assigns a precise percentage to a cell without identifying its probe or explicitly declaring an aggregation statistic and sample set. Fable owns the choice of cell-level statistic. The ten launch posts below use rounded composition claims so that this choice does not silently change their meaning.
10. Repeating generation from the same immutable source bytes and pinned measurement settings must reproduce the same metric records. The source fixture and arithmetic assertions are release checks. They establish the measurement; they do not turn one probe into a representative population.

The specific fixture identity for V1 is enough to rerun the launch arithmetic. Its body SHA256 is `9eaa18a0abed94a2c79faae780155ff0253038c269bd4e5141e8a4ea2629be21`. The independent check confirmed compact roundtrip equality. Its three named layers sum to 164,307 bytes, leaving 461. Use “about 84%” in the initial headline, because the observed cell contains real probe variance.

**Eligibility: the shared rule and Stuart's image decision.**

The retrieved X policy gives this lead-in and bullet:

> Content will be ineligible if:
>
> Was created or posted using automated means

The wording is reliable for this plan. Astra obtained it through a direct URL open returning parsed HTML labeled “Crawled: today”; an uncached origin fetch was not established. That retrieval boundary remains on the record. The policy does not explicitly settle CI-rendered research images attached to human-written analysis. [X Original Content Rewards policy](https://help.x.com/en/using-x/original-content-rewards)

The fixed operating rule is identical in both image branches. CI computes and validates measurements, publishes the site/data/RSS, and prepares evidence packets. It holds no X posting credentials and produces no publishable social prose. Stuart selects the finding, verifies its receipt, writes every word of the post in his own voice, and presses Post himself. No API posting, scheduling, or unattended detect-and-post. Human review of a machine-written draft does not, by itself, establish human authorship.

The decision on attaching a CI-rendered image belongs to Stuart. This document does not resolve it through a supposed exemption or an additional permission request.

| Stuart's choice | End-to-end publishing method | Cost and uncertainty |
| --- | --- | --- |
| Exclude CI images from X while seeking clarification | CI graphics remain available on the site. Stuart posts original text; he removes automatically attached CI-generated image previews if using this strict text-only branch. | Less unresolved image eligibility risk. At the explicitly hypothetical 50% text-reach retention used below, seven days costs about 23,333 planned impressions; fourteen days about 46,667. This is not a measured reach penalty. |
| Attach CI research images to personally written posts | Stuart chooses the comparison, checks the data and image, supplies original analysis, and manually attaches and publishes. | Preserves the intended visual format immediately. Its incremental reach has not been measured. X could treat the image as automated creation; content eligibility or admission may be affected. No supported dollar cost or enforcement probability is available. |
| Start with text, then change branches after a specific written answer | Begin publishing without waiting. Stuart asks X whether original measurements rendered by CI may accompany his personally written, manually posted analysis. Introduce images only under the interpretation he accepts. | A staged version of the same choice. The initial reach cost is measurable against the plan. Silence after a week supplies no policy answer. |

If Stuart chooses the image branch now, record that as an explicit accepted eligibility uncertainty. If he chooses text first, record a review date so that the delay gets examined. Neither choice changes the human-copy and manual-posting rule. No support inquiry or X post has been sent as part of this writing task.

At the P target of 600,000 qualifying impressions over 90 days, the daily average is 6,666.67. Seven days contain 46,666.67 planned impressions. If text retains half the planned visual reach, the difference is 23,333.33. Retention of 25% or 75% would instead produce losses of 35,000 or 11,667, rounded. These are sensitivity calculations; the retention assumptions have no measured support. Keep that sentence beside any use of the delay figure.

**The 90-day plan and its arithmetic.**

The program thresholds are 500 verified followers and 500,000 verified Home Timeline impressions within 90 days; reply impressions are excluded. Use the account's eligibility dashboard for progress. Public view counts and total followers cannot substitute for those measures. Admission is not guaranteed by hitting the thresholds. [X Original Content Rewards policy](https://help.x.com/en/using-x/original-content-rewards)

Set a P operating target of 600,000 qualifying impressions and 650 verified followers. The extra 100,000 impressions are headroom, not a policy requirement. Record starting dashboard totals before launch; 650 is the target total, not an assumption that the account starts at zero.

| Planned original main-timeline posts | Required yield allocation | Target contribution |
| --- | ---: | ---: |
| 54 precise observations and useful follow-through posts | 2,000 each on average | 108,000 |
| 24 model comparisons, paired captures, and substantial digests | 8,000 each on average | 192,000 |
| 12 flagship evidence stories | 25,000 each on average | 300,000 |
| 90 total | 6,666.67 overall average | 600,000 |

This is required yield, not an estimated distribution for a new account. I retain the arithmetic and reject treating each row's average as a likely result. For example, six flagship posts at 50,000 would supply the same 300,000 even if the other six supplied nothing. That is an arithmetic illustration of concentration, not a forecast of six viral posts. Do not use unsupported claims about typical account reach to make either scenario sound measured.

The threshold alone requires an average of about 5,556 qualifying impressions per day over the full window. From a hypothetical zero verified-follower start, 650 followers from 600,000 qualifying impressions implies about 10.83 verified follows per 10,000 impressions. That is the conversion the plan would need, not an observed conversion rate. Use the actual starting count and cohort results.

| Checkpoint | P cumulative impression target | P verified-follower target | Editorial work |
| --- | ---: | ---: | --- |
| Day 30 | 100,000 | 150 | Publish the first ten stories, establish the capture monitor, and learn which findings travel beyond current followers. |
| Day 60 | 300,000 | 350 | Concentrate on the strongest recurring stories; use new revisions and independent reproductions to earn outside citations. |
| Day 90 | 600,000 | 650 | Complete the public observed-change timeline and the strongest retrospective, while the earliest posts remain in the rolling window. |

Day 30 below 50,000 is a signal to change story selection and distribution, not to manufacture more routine updates. At day 60 with 180,000 impressions, the remaining 30 days would need about 10,667 per day to reach the minimum, or 14,000 to reach the operating target. Make that catch-up requirement visible before committing another month of the same plan.

**Launch sequence.** Before the first post, the public corpus must expose the actual cited specimens, dated diffs, methodology, and correction record without login. The byte fixture must pass. The fresh owner-measured experiment needs linked receipts. The profile should explain the product and point to the live corpus. Do not publish a placeholder domain or a link to private machine paths.

Use the ten posts below as the opening sequence, one complete original main-timeline story per publication. Publish the byte composition first, then the unchanged-binary finding and the effort control, followed by the model split, historical template reuse, and repeat revision. The remaining posts broaden the story to tools, message instructions, request shape, and the enduring product promise. Each post carries its essential result without requiring replies.

Continue at a P baseline of one original post per day on average. Keep one substantial flagship opportunity per week, a weekly digest when there are substantive findings, and the remaining slots for meaningful observations. Several posts can come from one capture series only when each supplies a distinct result. A quiet monitor does not create a story. Use dated archival evidence or skip a weak slot rather than portraying a normalizer change as vendor news.

The first month establishes the property and the monitoring habit. The second deepens the observed history and invites replication. The third publishes the strongest retrospective from that history. A run journey or workflow eval can enter when its actual evidence exists; there is no new eval matrix or invented result in this launch plan.

Prepare reusable public receipts for Piebald's maintainers, Codex maintainers, and authors of tools whose declarations changed. Stuart can offer a matched-capture comparison or an exact diff they can cite. These are potential amplifiers, not committed partners. Respond to substantive questions under the original posts as ordinary conversation; credit no reply impressions in the plan. No automated outreach or reply farming is part of the workflow.

**Recurring franchises and what the monitor actually watches.**

The observation is already recurring: the reported Sol sequence moved twice within four days. That warrants monitoring between CLI releases. It does not establish a permanent release cadence, a guaranteed number of changes per week, or a daily supply of news.

| Franchise | Trigger and evidence | Human editorial action |
| --- | --- | --- |
| Same Binary, New Instructions | A new core or complete instruction-set digest at an unchanged CLI version. Keep the observed dates and captured catalog revision where available. | Read the actual diff, identify the changed guidance, and write one bounded claim. Say when the changed text was observed rather than inventing the server's deployment time. |
| The Tool Declaration Changed | A declaration's content digest or source-byte size changes. Keep the per-tool identity and the containing request/probe. | Choose the tool and consequence a reader can understand. Explain a meaningful instruction or parameter change; avoid a wall of schema text. |
| The Request Breakdown | A newly verified probe changes the observed composition or provides a useful comparison. | Use rounded numbers for broad copy; exact numbers require the cited probe. State body-byte units without implying a spend percentage. |
| One Template, Different Model | Core text reveals exact reuse or a scoped difference across model selections. | Show the smallest verified substitution or clause difference. Equal lengths trigger a text comparison, never a declaration of equality. |
| The Control Settled It | A completed control eliminates an explanation, as the effort comparison did here. | Show the control and result. Scope invariance to the measured instruction component set and retain effort in its evidence. |
| Week in Context | Several substantive events or one substantial finding from the week. | Write a fresh digest that connects the observations. Do not merely paste an automated changelog. |
| The Correction | A new check changes a published fact or its interpretation. | Publish the corrected result with the reason and link the old receipt to its correction. Keep this as a credibility practice, not a quota. |

A daily monitor should consume the existing controlled capture pipeline, with fixed capture conditions and fresh conversations where the reference is a first turn. Start with the already measured models and request shapes. Watch CLI version changes, observed catalog/configuration identifiers, instruction component digests, tool declaration digests, message-instruction changes, and source-byte counts. Keep recording capture timestamps even when the binary is unchanged. A catalog identifier is useful provenance when actually retained; do not synthesize one from the date.

A daily captured observation is still needed when the release feed and visible catalog identifier remain unchanged. The observed outgoing request is the monitoring subject. Preserve the prior specimen, raw digest, normalized digest, and declared normalizer version. Keep the effort setting on each receipt; today's instruction-set invariance is evidence about the measured case, not a license to erase experimental provenance.

Capture runs stay in the owner's controlled environment. Public publishing CI validates exported artifacts without provider credentials. On a content change it produces an evidence packet: before/after specimen references, model and binary identity, capture times, available catalog identity, byte metrics, changed tool names, and the full reading diff. It may generate chart files for the website and the selected image branch. It never generates the X post's wording or presses Post.

When the monitor fires, Stuart verifies that the extractor read the actual carrier and the comparison used the same request shape. He checks whether the difference is substantive or a declared environment transformation, inspects changes in the complete text rather than heading levels alone, and chooses a claim supported by that evidence. If the capture is incomplete or the extraction cannot classify its carrier, the event is an investigation item. A missing carrier is not automatically a zero-length prompt.

Stuart then checks the figure's probe scope, writes the post, selects the image branch already chosen, and publishes manually with the live evidence link where it fits. An alert is a lead. An observed instruction edit is not by itself an eval showing changed model behavior. Keeping those distinctions clear makes the monitoring franchise reusable by vendors as well as skeptical users.

**Positioning against the competitors that already exist.**

Fable's candidate, “what was sent, not what was shipped,” isolates the right distinction for this launch: a binary version does not tell the reader which assembled instructions were selected for a particular request. It is strong campaign copy for the Codex finding. As the permanent positioning line, it is narrower than the property: remote configuration is also shipped, and a new reader needs to know what object the account measures.

Use **“The instructions your coding harness actually sends.”** The supporting line is: **“Captured system text, tool declarations, message instructions, and dated changes, within and between CLI versions.”** Use the candidate as an explained campaign idea rather than a claim that source extraction is useless.

| Competitor or substitute | What it already supplies | Where this launch has a defensible advantage |
| --- | --- | --- |
| Piebald's Claude Code prompt corpus | Extracted prompt components, tool descriptions, and a version changelog. Tool coverage and prompt diffs are already part of its product. | Show the assembled request used by a named probe and revisions observed while a binary version stays fixed. The Codex experiment demonstrates the need for this method; it does not establish an unmeasured Claude rollout. Credit Piebald and compare evidence. |
| OpenAI's public Codex source and releases | The implementation and a source/release history that researchers can inspect. | A captured specimen proves which available text and declarations were assembled in a particular observed request. Source inspection can help explain the selection; the two kinds of evidence reinforce each other. |
| Broad GitHub prompt collections such as x1xhlol's | Convenient discovery across many tools, including prompt and tool material. | Compete on traceable observations, scope, reproducible measurement, and dated revisions. Do not claim that every competing collection lacks provenance or that its text cannot be diffed. |
| Vendor release notes and shared prompt screenshots | Convenient summaries or examples that developers already encounter. | Let the reader inspect the actual captured request and its exact predecessor. A model-generated description of its instructions cannot substitute for captured input evidence. |

Piebald explicitly describes compilation-based extraction and publishes tool descriptions and change summaries; those capabilities must be credited. [Piebald corpus](https://github.com/Piebald-AI/claude-code-system-prompts). OpenAI publishes Codex as a public code repository. [Codex source](https://github.com/openai/codex). The broad collection names prompt, tool, and model material across products. [System prompts and models collection](https://github.com/x1xhlol/system-prompts-and-models-of-ai-tools). The competitive advantage column is our strategic inference from these surfaces and the capture findings.

The durable claim is observation quality and a growing revision history. Competitors can adopt request capture. Do not promise an exclusive technique forever, invoke leaks, or claim that outbound capture reveals everything a provider may add internally. “Here is the request, its scope, and the next observed change” remains useful even to a reader who distrusts the marketing.

**The first ten posts: final editorial copy.**

Each block is a complete text-only post under 280 characters, with no invented URL, required image, reply dependency, or repeated engagement solicitation. Evidence labels outside the blocks mark the source and independent-check boundary. The publishing process still requires Stuart's own authorship: this agent-written copy is not made reward-eligible merely by manual pasting or retyping. It is the finished editorial deliverable requested here; the policy interpretation is a separate claim this document cannot certify.

**Post 1.** V1 and V2. Independently checked across the five named Claude probes. Rounded composition, scoped to the observed Opus requests.

```text
Tools are about 84% of the body in these captured Claude Code 2.1.270 Opus first requests.

The system field is under 6%.

KnowMoreContext publishes the assembled request and its changes. The tool declarations belong in the prompt story.
```

**Post 2.** S1 and S3. Stuart's fresh experiment and server revision report, accepted as the launch basis; Astra has not independently queried those database rows. Written in Stuart's publishing voice.

```text
Pinning Codex 0.154.0 did not freeze Sol's instructions.

My captures found two server-side revisions within four days, with the CLI binary unchanged.

A release feed alone would miss this. We are building a feed of captured instruction changes.
```

**Post 3.** S1. The reported equality concerns instruction component sets. It does not claim that whole requests, effort parameters, or responses are identical.

```text
Codex 0.154.0 / Sol / controlled capture:

low = high = xhigh

The captured instruction component sets were byte-identical.

Effort did not choose a different prompt in this test. That closes the effort explanation for the observed change.
```

**Post 4.** S2. Stuart's same-day model comparison. Deliberately omits the exact stored-blob character counts from public copy.

```text
Same Codex binary. Same day. Same effort.

Luna and Sol received different instructions.

Sol and Astra had instruction blobs of equal length, but different text.

A model picker selects instructions too. A size chart alone cannot show which ones.
```

**Post 5.** V3. Historical Sol September 13 and Astra September 7 core text comparison, independently checked from bundles.

```text
Sol adopted an instruction template Astra already used.

Archived cores:
Astra, Sep 7: "based on GPT-6"
Sol, Sep 13: "based on GPT-5"

The rest of those core texts matches exactly.

That is template reuse with a model-name substitution.
```

**Post 6.** S3. The 24-line latest diff is Stuart's measurement, not independently recalculated by Astra. Its public receipt must identify both captures and the line-diff convention.

```text
Sol's instructions moved again after the Sep 13 capture.

I measured 24 changed lines.
Codex stayed on 0.154.0.

This is another revision inside the same CLI version. The monitor has to keep watching between releases.
```

**Post 7.** V1 and V2. The approximate size comparison survives the observed Artifact variants. It does not imply a corresponding token or spend ratio.

```text
One tool declaration was roughly five times the Opus system field.

The tool: Artifact.
The captures: Claude Code 2.1.270, Opus, first turn.

A tool's instructions can outweigh the system field. A corpus needs the tool declaration and its history.
```

**Post 8.** V2. Messages exceed the system field in all five inspected Opus probes. Both labels refer to serialized JSON value bytes.

```text
The messages layer was larger than the system field in every Claude Code 2.1.270 Opus first-turn probe we checked.

Publishing only the system field leaves out another place instructions travel.

The receipt needs both.
```

**Post 9.** V4. The paired first/tool-turn evidence was checked in Round 2, including the matching run and tool call.

```text
A tiny Codex continuation request caused a false alarm.

Its previous_response_id and tool result belonged to a later request. The full first request was also captured.

Request shape has to sit beside the diff. Otherwise a continuation can look like a vanished prompt.
```

**Post 10.** Product promise. Use after the public release exposes these named evidence surfaces for the captured harnesses.

```text
KnowMoreContext tracks the instructions your coding harness actually sends.

Captured system text.
Tool declarations.
Message instructions.
Dated diffs within and between CLI versions.

Claude Code, Codex and Grok. Evidence you can inspect before interpreting the change.
```

**Launch handoff and likely integration conflicts.** Fable's proposal must expose per-probe measurements and link the fresh controlled-run receipts before this copy is published. The exact byte figures above attach to V1, not to an undifferentiated Opus cell. The public method must keep the original measurement representation separate from normalized text and stored component blobs. The observation key must retain enough provenance to support the claimed same-binary revisions and the scoped effort-invariance result.

No scientific claim here depends on selecting the CI image branch. No launch claim says the autonomy section was newly introduced. No post turns bytes into money or treats equal-length prompts as identical. If the implementation chooses an aggregate statistic, its label and coverage must survive into every consuming chart or post. The rounded launch copy is deliberately compatible with that choice.

## Round 3b

**Composition is scoped to a probe.** I rechecked all five Claude 2.1.270 Opus first-turn probes. Each passes the exact compact-roundtrip and stored body-hash checks. Their percentages differ, including between probes of the same medium-effort cell.

The Round 3 measurement contract now requires probe identity on exact figures, applies the partition equation per probe, and rejects unlabeled cell percentages. Its precise example identifies bundle `5f075e0c-b10c-4679-b871-c9e1c51ec107`, probe `a1`, medium effort. Launch copy uses about 84% for tools, under 6% for the system field, and roughly five times for Artifact versus the system field. Fable owns the cell-level aggregation choice; its statistic and sample coverage must accompany any aggregate supplied to publishing.

**The 2,038-byte difference has a specific location.** In that medium bundle, `a1` has 139,195 tool bytes and `a2` has 137,157. Artifact falls from 49,692 to 47,654 bytes, accounting for the entire reduction. Messages remain 15,436 bytes in both probes, although their contents differ. The source of the Artifact variation is a separate attribution question. Probe variance is established; this pair's size change occurs in the tool declaration.

## Round 4

**Lead with Claude's declared capabilities.** The Artifact comparison is a stronger opening post than the Codex instruction rewrite: the difference names operations a reader immediately understands. It shows different declarations on the same reported CLI version, model, effort, and day. Use two captures as the subject; the evidence does not establish two different people. Keep the Codex revision story next and the rounded request composition as supporting context.

I independently checked bundle `5f075e0c-b10c-4679-b871-c9e1c51ec107`. Probes `a1` and `b` advertise 22 Artifact actions; `a2` advertises 18. The four absent actions are `upload_asset`, `list_assets`, `read_asset`, and `delete_asset`. Properties `after` and `asset_id` and the Artifact assets paragraph also disappear. Both variants still declare 31 tools. “Four tools disappeared” would be wrong: four actions within one named tool disappeared.

A further measurement distinction: the original system and message values have equal byte lengths across `a1` and `a2`, but they are not byte-identical. UUID substitution makes each pair identical. The capability difference survives that environment normalization. The declarations establish advertised operations; the underlying flag identity and successful execution of those operations require their own evidence.

**Add tool-set identity to the per-probe contract.**

- Retain the probe/run/exchange identity, source request digest, recorded scope and environment, full `system_set_hash` and `tools_set_hash` when available, and the hash implementation revision. Export the ordered member manifest, including member hashes and position metadata. An abbreviated hash is a display label.
- The database primitive addresses normalized IR components in order. The writer can fold position metadata into the persisted set identity. Consequently, differing `tools_set_hash` values identify a comparison candidate; they do not alone prove changed capabilities. This follows from `session/wire_normalization.py` and `session/wire_store.py`, which I read directly.
- Alongside that identity, retain raw declaration provenance, original byte spans, names and namespaces, schemas, action enums, required/optional properties, descriptions, and extraction completeness. Preserve every actual carrier, including Codex's top-level tools and developer `additional_tools` items. If the historical bundle lacks a database identity, publish a separately named, versioned digest rather than inventing a `wire_exchange.tools_set_hash`.
- Distinguish declarations present, explicitly empty, omitted on a continuation, and unsupported extraction. Omission from a continuation does not prove a capability was withdrawn. Keep the original byte-accounting contract for each probe.
- A cell with divergent declarations must expose the observed alternatives and their supporting probes. Refuse an unlabeled single inventory, a union presented as a real capture, or a “typical” capability list synthesized from a median. Equal tool counts do not establish equal capability sets. An aggregate byte statistic cannot conceal the alternatives.
- Classify known per-run values as environment with an explicit transformation record. A feedback draft path can normalize; action enums and schema properties cannot disappear through that rule. Preserve unclassified changes for review and block unsupported definitive claims.

**Replacement opening post, 235 characters:**

```text
Claude Code 2.1.270. Opus. Medium. Same day.

One captured Artifact schema declared:
upload_asset
list_assets
read_asset
delete_asset

Another declared none of them.

A pinned CLI version does not guarantee identical tool declarations.
```

The existing human-authorship and manual-posting rule still applies. The CI image decision remains Stuart's.

**Franchise: Claude Capability Watch.** Watch repeated fresh first-turn captures under the same recorded conditions, including when the binary version remains unchanged. Compare complete tool sets, then locate changed membership, actions, parameters, and instruction clauses. Publish each distinct observation with its supporting pair. Known environment-only differences remain in the provenance record and do not trigger a capability story.

A changed set creates an editorial candidate. Stuart checks the raw declarations, confirms extraction coverage and request shape, inspects normalization, and names the concrete advertised operation that changed. He writes the interpretation and posts manually. Do not call a changed hash a server flag without attribution, present sampled variants as a population rollout percentage, or describe an absent declaration as a failed execution test. A new meaningful capability difference, a verified return of an earlier variant, or a completed explanation can justify another post; repeated sightings of the same variant are primarily corpus updates.

**Positioning and budget.** This strengthens the runtime-observation argument behind Fable's candidate line. A binary's available strings do not establish which declaration a particular request carried. It does not prove that competitors could never add capture. Keep the property's broader instruction-capture positioning, with a Claude-specific capability campaign. The current evidence does not support a cross-vendor per-request flag claim.

Per Stuart's latest instruction, leave the 90-day plan unchanged: the existing planning targets remain 600,000 qualifying impressions, 650 verified followers, and 90 original posts. Claude Capability Watch replaces weaker slots within that plan. No increased reach forecast, lower production-cost claim, or larger spending allowance follows from the present census.

**Cross-harness check completed.** I inspected 40 Codex bundles containing 104 probes and 17 Grok bundles containing 47 probes, including both tool carriers in Codex. No Codex tool-declaration divergence appeared within a bundle or a same-day cell at the same recorded effort. Historical Sol captures do change from three declared tool leaves to five across dates, adding `functions__request_user_input_async` and `clock__sleep`; that comparison also changes recorded capture conditions and does not reproduce the Claude within-cell result.

Six Grok bundles showed raw declaration differences across their probes. All disappear after replacing the session feedback-drafts path in `send_feedback` with one declared placeholder. Tool names and schemas stay unchanged. These include first-turn and tool-turn bundles, so they must not be counted as six independent capability findings. The first-turn examples are grok-4.6 at 1.0.25 and grok-4.5/4.6 at 1.0.30. The cross-vendor capability claim is withdrawn.

A further search would repeat the same scoped comparison over newly exported probes, inspect every differing declaration, and separate membership/schema changes from description changes and environment substitutions. That is the method; no additional captures or new investigation were started after Stuart's instruction to stop.

**Latest census qualification.** Stuart reports 106 tool-carrying first-turn cells and 16 with tool-content divergence, approximately 15%. That is an owner-reported census, not independently reproduced here. The supplied Claude list contains 13 cases across five version labels: 2.1.250, 2.1.267, 2.1.268, 2.1.269, and 2.1.270. The three excluded Grok first-turn cases may explain the difference. Do not advertise 15% as verified capability incidence until those categories are reconciled. The original eight prompt-variant cells likewise receive no blanket flag attribution from this tool scan; their individual audit belongs to Fable's proposal work.

## Round 4b

**Census reconciled.** Stuart's per-harness recount releases the prevalence claim: **13 of 90 scanned Claude tool-carrying first-turn cells, 14.4%, show within-cell tool-set divergence classified as capability.** This is Stuart's verified census, not an independent recount by Astra. It spans five versions: 2.1.250, 2.1.267, 2.1.268, 2.1.269, and 2.1.270. Most cases involve Artifact; the 2.1.250 cases also involve CronCreate/WebFetch and SendUserFile.

The earlier 16/106 figure mixed these capability cases with three Grok environment-noise cases. It is withdrawn as capability prevalence. The released percentage applies to the sampled Claude cells, not all harnesses, users, requests, or deployments.

**Updated post, 257 characters:**

```text
Same Claude Code version, different declared tools.

13 of 90 scanned Claude tool-carrying first-turn cells (14.4%) had capability differences between probes.

Most involved Artifact. The same version and model did not guarantee identical tool declarations.
```

**Updated franchise wording:** “Claude Capability Watch tracks differences in the tools declared by repeated captures of the same cell. In this census, 13 of 90 Claude tool-carrying first-turn cells showed capability divergence.” Keep the denominator and census scope with the figure. Grok feedback identifiers remain environment findings; this recount does not establish that Fable's normalizer passes its completeness assertion. The 90-day plan and human publishing rule remain unchanged.
