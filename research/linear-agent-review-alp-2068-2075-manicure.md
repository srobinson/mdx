---
title: Linear Agent Review for ALP 2068, 2069, 2070, and 2075
type: research
tags: [manicure, linear, agent-review, fmm]
summary: Read-only review found ALP-2068 needs an import note and ALP-2075 has stale or incomplete call site guidance.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-28
updated: 2026-04-28
---

## Executive Summary

Read-only Agent Review ran against ALP-2068, ALP-2069, ALP-2070, and ALP-2075 in `manicure`. The current codebase validates most paths, symbols, tests, and route assumptions, with two actionable description fixes: ALP-2068 should mention `json` import needs, and ALP-2075 should correct current `codex/exchange.py` call site count and include frontend call sites that still reference `user_prompt_preview`.

## Project Metadata

- Project: `manicure`
- Topology from fmm: 296 indexed files, 57,233 LOC
- Primary areas: `api/` with 181 files and 38,445 LOC; `www/` with 115 files and 18,788 LOC
- Review mode: read-only. No codebase or Linear edits.

## Detailed Findings

### ALP-2068: Add `extract_response_text` IR helper

Status: mostly current. `api/src/manicure/exchange_stats.py` exists and currently imports `TextBlock`, `ToolResultBlock`, and `ToolUseBlock`, but not `ThinkingBlock`; it also does not import `json` (`api/src/manicure/exchange_stats.py:5-16`). The target response IR and block symbols exist: `InternalResponse.content` contains `TextBlock | ToolUseBlock | ThinkingBlock | UnknownBlock` (`api/src/manicure/ir.py:158-169`), `ToolUseBlock.input` exists (`api/src/manicure/ir.py:26-32`), and `ThinkingBlock.text` exists (`api/src/manicure/ir.py:45-50`). The test file exists at `api/src/manicure/test_exchange_stats.py`, and the current user preview helper starts at `api/src/manicure/exchange_stats.py:25`.

Recommended Linear patch text:

```markdown
* Modify: `api/src/manicure/exchange_stats.py` (add function, add `import json`, extend `manicure.ir` imports for `ThinkingBlock`)
```

### ALP-2069: Add `extract_user_prompt_text` uncapped IR helper

Status: current. The existing capped helper and flattening helper are present at `api/src/manicure/exchange_stats.py:25-39` and `api/src/manicure/exchange_stats.py:42-60`. The described uncapped implementation can reuse current `InternalRequest.messages` (`api/src/manicure/ir.py:131-146`) and current `ToolResultBlock.content` (`api/src/manicure/ir.py:35-42`). The test file path is valid at `api/src/manicure/test_exchange_stats.py`.

No patch needed.

### ALP-2070: Add `GET /api/exchanges/{id}/turn-content` endpoint

Status: current. `api/src/manicure/api/v1/exchanges.py` exists, defines `router = APIRouter()` (`api/src/manicure/api/v1/exchanges.py:41`), and already has adjacent exchange routes (`api/src/manicure/api/v1/exchanges.py:123-147`). Mount assumptions are valid: the v1 router includes exchanges with `prefix="/exchanges"` (`api/src/manicure/api/v1/router.py:5-6`), and the app includes that router at `prefix="/api"` (`api/src/manicure/main.py:80-85`). `storage.read_exchange(exchange_id)` and `FileNotFoundError` to `NotFoundError` are already used in `get_exchange` (`api/src/manicure/api/v1/exchanges.py:147-155`). `ExchangeArtifacts.request_ir` and `response_ir` exist (`api/src/manicure/storage/base.py:150-157`), and `InternalResponse.stop_reason` exists (`api/src/manicure/ir.py:161-166`). The existing async `client` fixture exists at `api/src/manicure/api/v1/conftest.py:50-55`.

No patch needed.

### ALP-2075: Drop `user_prompt_preview` field, extractor, and call sites

Status: needs description patch. The listed backend paths and symbols are valid: `IndexEntry.user_prompt_preview` (`api/src/manicure/storage/base.py:110-125`), `_PREVIEW_MAX_CHARS` and `extract_user_prompt_preview` (`api/src/manicure/exchange_stats.py:22-39`), test import and preview tests (`api/src/manicure/test_exchange_stats.py:5`, `api/src/manicure/test_exchange_stats.py:38-126`), and `exchange_recorder.py` import plus two kwargs (`api/src/manicure/exchange_recorder.py:13-18`, `api/src/manicure/exchange_recorder.py:240-252`, `api/src/manicure/exchange_recorder.py:306-317`).

The stale item is `api/src/manicure/codex/exchange.py`: current code has three `user_prompt_preview=...` kwargs, not four (`api/src/manicure/codex/exchange.py:33-38`, `api/src/manicure/codex/exchange.py:108-120`, `api/src/manicure/codex/exchange.py:250-260`, `api/src/manicure/codex/exchange.py:534-542`).

The current codebase also still has frontend references that the issue omits: `www/src/components/ExchangeTurnCard.tsx` renders `entry.user_prompt_preview` (`www/src/components/ExchangeTurnCard.tsx:278-281`), and `www/src/components/ExchangeList.test.tsx` sets `user_prompt_preview` in a fixture (`www/src/components/ExchangeList.test.tsx:556-564`). `www/src/types.ts` also has the listed type field at `www/src/types.ts:50-68`.

Recommended Linear patch text:

```markdown
* `api/src/manicure/codex/exchange.py`: remove the import and the three current `user_prompt_preview=...` kwargs.
* `www/src/components/ExchangeTurnCard.tsx`: if ALP-2074 has not already removed it, remove the `entry.user_prompt_preview` rendering branch and any now-unused `ExchangePreview` import.
* `www/src/components/ExchangeList.test.tsx`: remove or update the legacy "renders prompt preview in settled middle row" fixture/assertion if still present after ALP-2074.
```

Also update the Files list to include `www/src/components/ExchangeTurnCard.tsx` and `www/src/components/ExchangeList.test.tsx` if those references remain when ALP-2075 starts.

## Open Questions

- Whether ALP-2074 will remove the current `ExchangeTurnCard` and `ExchangeList.test` `user_prompt_preview` references before ALP-2075 runs. If yes, ALP-2075 can keep those frontend references as a conditional cleanup note rather than hard scope.
