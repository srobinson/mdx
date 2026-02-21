---
title: Linear stale reference review for Nancy ALP 2007 through 2018
type: research
tags: [linear, nancy, stale-references, agent-review, decomposition]
summary: Reviewed ALP-2007 through ALP-2018 after test decomposition and updated stale Linear file references in place.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-27
updated: 2026-04-27
---

## Executive Summary

Four review agents checked ALP-2007 through ALP-2018 for stale file references after the decomposition work completed in ALP-2041 through ALP-2047. Linear descriptions were updated in place where stale references were found. No code was changed.

## Project Metadata

* Project: Nancy worktree at `/Users/alphab/Dev/LLM/DEV/helioy/manicure-worktrees/nancy-ALP-2019`
* Indexed shape from fmm: 287 files, 53,843 LOC
* Main areas: `api/` with 177 files, `www/` with 110 files
* Review date: 2026-04-27

## Architecture Context

The reviewed issues touch backend HTTP exchange recording, Codex transport tests, frontend exchange rendering, visual fixtures, and SSE recovery behavior. Recent decomposition moved several broad test files into focused fixture or behavior families, which made older Linear descriptions vulnerable to stale file references.

Relevant decomposition areas:

* Codex transport tests now live under `api/src/manicure/codex/` by lifecycle, addon, and support behavior.
* Visual fixtures now live under `www/tests/visual/fixtures/` by fixture family.
* Exchange and stream frontend tests now use more precise component and hook locations.

## Detailed Findings

### Issues with no stale references

* ALP-2007: all referenced backend paths still exist.
* ALP-2008: all referenced backend and project documentation paths still exist.
* ALP-2009: all referenced backend paths still exist.
* ALP-2010: all referenced backend paths still exist.
* ALP-2011: all referenced backend paths still exist.
* ALP-2012: all referenced backend paths still exist.
* ALP-2017: existing references are valid. `api/src/manicure/api/v1/test_exchanges_recovery.py` remains an optional new target, so its absence is expected.

### Issues updated in Linear

#### ALP-2013

Replaced stale `api/src/manicure/test_codex_transport.py` references with current decomposed test paths:

* `api/src/manicure/codex/test_transport_lifecycle.py`
* `api/src/manicure/codex/test_transport_addon.py`

#### ALP-2014

Replaced stale Codex transport test references with current decomposed paths:

* `api/src/manicure/codex/test_transport_addon.py`
* `api/src/manicure/codex/test_transport_lifecycle.py`
* `api/src/manicure/codex/test_transport_support.py`

Updated canonical emit pattern reference to:

* `api/src/manicure/codex/test_transport_addon.py:119-155`

#### ALP-2015

Replaced stale visual fixture reference `www/tests/visual/fixtures.ts` with:

* `www/tests/visual/fixtures/exchanges.ts`
* `www/tests/visual/fixtures/details.ts`

#### ALP-2016

Replaced stale references:

* `ExchangeList.test.tsx:604` to `www/src/components/ExchangeList.test.tsx:337`
* `www/tests/visual/fixtures.ts` to `www/tests/visual/fixtures/exchanges.ts`

#### ALP-2018

Updated stale hook line reference:

* `useExchangeStream.ts:231` to `www/src/hooks/useExchangeStream.ts:238`

## Verification

Agents used fmm first for structural orientation, then fetched Linear issues, extracted file references, and checked current paths against the worktree. Updates were made only to Linear descriptions. No branches were pulled and no code files were modified.

## Dependencies

Relevant tools used:

* fmm MCP tools for file topology and symbol or file validation
* Linear MCP tools for issue retrieval and in place description updates
* filesystem inspection for existence checks

## Relevance to Helioy

This review keeps Nancy work items executable after test decomposition. It reduces agent confusion by preserving stable file references in Linear before autonomous execution begins.

## Open Questions

None. No unresolved stale references were reported by the review agents.

## Related Research Notes

* `~/.mdx/research/linear-stale-reference-review-nancy-alp-2007-2009.md`
* `~/.mdx/research/linear-stale-file-reference-review-nancy-alp-2010-2012.md`
* `~/.mdx/research/linear-stale-reference-review-nancy-alp-2013-2014-2017.md`
* `~/.mdx/research/linear-stale-reference-review-nancy-alp-2015-2018.md`
