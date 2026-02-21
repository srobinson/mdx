---
title: Stale file reference sweep after SamplingSection and visual fixture test decomposition
type: research
tags: [manicure, linear, testing, stale-references]
summary: Reviewed ALP-2032, ALP-2028, ALP-2031, ALP-2029, ALP-2038, ALP-2034, ALP-2037, ALP-2035, ALP-2030, ALP-2039, ALP-2036, and ALP-2033 for stale SamplingSection or visual fixture paths after ALP-2042 and ALP-2045.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

The target pre-decomposition Linear issues do not contain concrete stale references to the removed monolithic SamplingSection test file or to decomposed visual fixture modules. No Linear updates were performed.

## Project Metadata

- Repository: `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
- fmm topology: 287 files, 53,830 LOC, split across `api/` and `www/`
- Relevant area: frontend tests under `www/src/components/editor` and visual tests under `www/tests/visual`

## Architecture

ALP-2042 split SamplingSection coverage into behavior family files:

- `www/src/components/editor/SamplingSection.commits.test.tsx`
- `www/src/components/editor/SamplingSection.providerExtras.test.tsx`
- `www/src/components/editor/SamplingSection.render.test.tsx`
- `www/src/components/editor/SamplingSection.reset.test.tsx`
- `www/src/components/editor/SamplingSection.thinking.test.tsx`
- `www/src/components/editor/SamplingSection.testSupport.tsx`

ALP-2045 split visual fixtures into family modules while keeping the barrel:

- `www/tests/visual/fixtures.ts`
- `www/tests/visual/fixtures/details.ts`
- `www/tests/visual/fixtures/exchanges.ts`
- `www/tests/visual/fixtures/pausedFlow.ts`
- `www/tests/visual/fixtures/setup.ts`
- `www/tests/visual/fixtures/time.ts`

## Detailed Findings

Reviewed target issues and comments:

- ALP-2032: no SamplingSection or visual fixture references.
- ALP-2028: no SamplingSection or visual fixture references. One comment references backend anchor fields only.
- ALP-2031: no SamplingSection or visual fixture references.
- ALP-2029: no SamplingSection or visual fixture references.
- ALP-2038: no SamplingSection or visual fixture references.
- ALP-2034: no SamplingSection or visual fixture references.
- ALP-2037: no SamplingSection or visual fixture references.
- ALP-2035: no SamplingSection or visual fixture references.
- ALP-2030: no SamplingSection or visual fixture references.
- ALP-2039: contains a generic visual smoke requirement but no concrete visual fixture file reference. No stale path.
- ALP-2036: no SamplingSection or visual fixture references.
- ALP-2033: no SamplingSection or visual fixture references.

## Dependencies

- fmm was used first for repository topology and relevant file discovery.
- Linear was used to inspect issue descriptions and comments.

## Relevance to Helioy

This confirms the ALP-2019 target issue set does not need cleanup for the ALP-2042 or ALP-2045 decompositions.

## Open Questions

None for the requested sweep.
