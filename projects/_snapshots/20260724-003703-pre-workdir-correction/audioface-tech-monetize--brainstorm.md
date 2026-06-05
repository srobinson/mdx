# Audioface monetization brainstorm

## Best paid SKU

Audioface Source Extract API: a hosted service that turns a song, movie clip, brand video, or reference reel into an Audioface theme, token expansion, and polished procedural SFX palette.

## Open core line

Free forever:

- `AUDIO.md` contract
- `audioface.schema.json`
- base semantic token catalog
- reference resolver
- browser Web Audio runtime
- framework adapters
- local composer
- validation CLI
- loader for third party themes and packs

Paid:

- hosted source extraction
- hosted agent theme generation
- commercial SFX packs
- team library, approvals, and usage analytics
- enterprise self host for extraction and generation
- commercial license for proprietary packs and generated brand systems

The oscillators, resolver, schema, and default runtime should stay MIT or Apache 2.0. The moat is proprietary extraction models, curated datasets, evaluation harnesses, commercial pack recipes, source ingestion infrastructure, and the hosted generation workflow.

## Ranked mechanisms

1. Source Extract API.

   Highest defensible revenue with low OSS risk. Users pay for compute, models, and taste. Playback stays in the free runtime. Input is source media. Output is a portable `.audioface.json`, `AUDIO.md`, and optional token pack that runs on the free runtime.

   API shape:

   ```ts
   const result = await audioface.cloud.extract({
     source: "s3://brand/reel.mp4",
     target: "product-ui",
     constraints: {
       politeness: "low-fatigue",
       tokenCoverage: "full-ui",
       avoid: ["melody", "speech-like", "long tails"]
     }
   });
   ```

   License line: input analysis and model weights are commercial service code. Generated `.audioface.json` belongs to the customer. Runtime stays free.

   Metered unit: source minute analyzed plus generated candidate count.

   Pricing:

   - Developer trial: 30 source minutes free once.
   - Pro: $29 per seat per month, includes 120 source minutes and 500 generated candidates.
   - Usage: $0.35 per source minute, $0.02 per candidate after quota.
   - Studio: $299 per month, includes 2,000 source minutes, 10,000 candidates, shared libraries, and private theme history.
   - Enterprise: annual contract, private model options, indemnity, retention controls, and self host.

2. Agent Theme Generation API.

   Strong adoption fit because agents can request unique themes from `AUDIO.md`, design tokens, screenshots, product copy, or brand guidelines. The free packages expose the client interface and local validation. The hosted service creates the opinionated theme.

   API shape:

   ```ts
   const theme = await audioface.cloud.generateTheme({
     designTokens,
     audioContract: "./AUDIO.md",
     product: "dense operational dashboard",
     density: "quiet",
     uniqueness: 0.7
   });
   ```

   License line: client SDK and response schema are OSS. Prompt pipelines, ranking models, sound quality evaluation, and hosted candidate search are commercial.

   Metered unit: generated candidate plus evaluation pass.

   Pricing:

   - Free: 100 candidates per month for public projects.
   - Builder: $19 per month, 1,000 candidates.
   - Team: $99 per month, 10,000 candidates, shared keys, audit log.
   - Overage: $0.01 per candidate, $0.03 per evaluated candidate set.

3. Commercial SFX Packs.

   Sell polished procedural packs that expand the semantic catalog while preserving the no audio file rule. Packs are recipe libraries: extra tokens, layer primitives, theme presets, sequence patterns, and constraints.

   Examples:

   - `precision-command`: command palette, terminal, power user workflows.
   - `spatial-panels`: docking, sheets, drawers, split panes, canvas tools.
   - `commerce-trust`: checkout, payment, validation, order status.
   - `creative-suite`: timeline, trim, brush, layer, scrub, snap.
   - `system-grade`: install, update, permission, security, destructive action.

   License line: pack loader and pack schema are OSS. Premium pack recipes and names are commercial licensed content.

   Metered unit: licensed app seat, domain, or repository. No runtime call metering.

   Pricing:

   - Single pack: $49 per app per year.
   - Pro bundle: $149 per app per year.
   - Team library: $499 per org per year for all packs and updates.

4. Audioface Cloud Library.

   Teams pay for versioned theme libraries, approval flows, private generated themes, signed pack distribution, and usage analytics across apps. This monetizes serious adoption without gating the free runtime.

   API shape:

   ```ts
   import { loadTheme } from "audioface/cloud";

   const theme = await loadTheme("org/product/studio@2.1.0");
   ```

   License line: local theme loading from files is free. Hosted registry, access control, changelog, approvals, analytics, and signed distribution are paid.

   Metered unit: seats plus private theme versions stored.

   Pricing:

   - Team: $12 per seat per month, 100 private theme versions.
   - Business: $29 per seat per month, 1,000 versions, SSO, audit log.
   - Overage: $0.10 per stored private theme version per month.

5. Enterprise self host for extraction and generation.

   Some companies keep unreleased films, campaigns, product videos, and brand sounds off external cloud services. Sell a containerized extraction and generation service with private storage and optional customer tuned models.

   License line: OSS runtime can self host playback and validation. Hosted extraction stack, model server, evaluation suite, admin console, and model updates require a commercial license.

   Metered unit: annual platform license plus compute node.

   Pricing:

   - Self host standard: $25,000 per year, one environment, capped model updates.
   - Self host scale: $75,000 per year, multiple environments, private support, higher throughput.
   - Private model tuning: $15,000 setup plus usage based compute.

6. Composer Pro.

   The local composer remains free. Composer Pro adds commercial workflows: source references, A/B tests, team comments, brand locks, export governance, pack previews, and generated theme comparison.

   License line: editing and exporting `.audioface.json` stays free. Collaboration, hosted history, source extraction calls, and commercial pack previews are paid.

   Metered unit: seat plus compute calls.

   Pricing:

   - Solo Pro: $15 per month, cloud sync and 200 generation candidates.
   - Team: $25 per seat per month, approval flows and shared pack licenses.

7. Certification and marketplace revenue share.

   Let expert sound designers publish commercial Audioface packs and themes. Audioface takes a platform fee and offers automated quality checks: fatigue, loudness, token contrast, sequence rhythm, and accessibility constraints.

   License line: marketplace format and local install are free. Marketplace hosting, certification badges, discovery, payment rails, and pack signing are paid.

   Metered unit: revenue share plus certification run.

   Pricing:

   - 20 percent marketplace fee.
   - $99 certification submission for commercial packs.
   - Free certification for OSS packs under size and usage limits.

8. Compliance and accessibility reports.

   Teams with mature design systems will pay for reports proving sound is restrained, muted by default where required, user gesture safe, accessible, and consistent across products.

   License line: validator rules for the spec are free. Hosted reports, historical trend data, organization policy checks, and signed compliance artifacts are paid.

   Metered unit: project scan.

   Pricing:

   - $9 per scan.
   - $199 per month for 100 scans and policy history.
   - Enterprise bundled with Cloud Library.

## Package boundary by registry

`crates.io/audioface`

- Free: schema types, resolver, validator, fixture generator, deterministic tests.
- Paid hook: feature gated client types for cloud job manifests, with no secrets or paid model code in the crate.

`npm/audioface`

- Free: browser runtime, Web Audio scheduler, adapters, local composer, schema exports, base tokens.
- Paid hook: optional cloud client, license key loader, signed pack loader, and Pro composer UI panels.

`pypi/audioface`

- Free: validation CLI, Python bindings, fixture diffing, `AUDIO.md` generation.
- Paid hook: authenticated CLI commands for extraction jobs, theme generation, cloud library sync, compliance reports.

## Technical defensibility

- Extraction uses source separation, timbre embeddings, onset density, spectral brightness, dynamic range, motif abstraction, and fatigue scoring.
- Mapping models convert sonic identity into material, density, politeness, contrast, mechanical feel, warmth, token coverage, and SFX constraints.
- Evaluation ranks candidates against the Audioface contract: short decay, semantic separation, low fatigue, no hover noise, no long decorative tails.
- Proprietary datasets should include curated UI sound identities, product interaction flows, film and music palette annotations, and negative examples that violate restraint.
- The free runtime only needs resolved recipes. Keeping generation server side protects the model investment while keeping adoption friction low.

## Best sequence

1. Keep npm runtime and `AUDIO.md` free.
2. Ship free composer with theme export and shareable links.
3. Add API key based agent theme generation.
4. Add source extraction as the premium launch SKU.
5. Add commercial SFX packs once token coverage and pack quality are strong.
6. Add Cloud Library when teams have enough generated assets to manage.
