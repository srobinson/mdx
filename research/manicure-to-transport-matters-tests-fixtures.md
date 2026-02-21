---
title: Manicure to Transport Matters Test and Fixture Rename Scan
type: research
tags: [manicure, transport-matters, rename, tests, fixtures, playwright, pytest]
summary: Tracked tests and fixtures contain many package level manicure references, plus a smaller set of product name, env var, storage key, fixture, and snapshot concerns for the transport-matters rename.
status: active
source: codebase-analyst
confidence: high
created: 2026-04-29
updated: 2026-04-29
---

## Executive Summary

The narrowed scan covered tracked test, fixture, sample payload, and Playwright visual files only. The main rename risk is the Python package path and import namespace in 95 tracked pytest files under `api/src/manicure`; visual and sample payload risks are smaller but include product text, localStorage keys, absolute fixture paths, and 13 tracked PNG snapshots that must be regenerated after UI copy changes.

## Scope and Method

Started with fmm structure, then used `git ls-files` plus read only searches. Excluded `node_modules`, `.venv`, caches, `dist`, `TMP`, `.nancy`, `test-results`, `playwright-report`, and coverage data. Binary PNG snapshots were counted by path only and not inspected.

Tracked narrowed scope:

| Category | Files | Text lines | Notes |
| --- | ---: | ---: | --- |
| `api/src/**/test_*.py` | 95 | 21,871 | Pytest files beside source package |
| `api/tests/**` | 13 | 380 | Integration test plus Codex fixture corpus |
| `www/src/**/*.test.tsx` | 28 | 5,974 | Narrowed TSX unit tests only |
| `www/tests/**` | 26 | 1,004 | Playwright specs, visual fixtures, tracked snapshots |
| Fixture or sample payload paths | 17 | 1,182 | Overlaps with `api/tests/**`, `www/tests/**`, and `www/src/visualFixtures.test.ts` |
| Tracked binary snapshot PNGs | 13 | 0 | Counted only |
| Total scoped files | 163 | 29,229 text lines | 150 text files and 13 PNGs |

fmm context:

- Repo has `.fmm.db`, so it is indexed.
- fmm top level: 300 indexed files, 57,576 LOC, split across `api/` and `www/`.
- fmm test index reports 53 files, 8,631 LOC. This misses many pytest files under `api/src/manicure` because they are source adjacent, so `git ls-files` was required for the narrowed tracked count.

## Exact Occurrence Counts

Counts are across the 150 scoped text files only.

| Token category | Occurrences | Files | Rename interpretation |
| --- | ---: | ---: | --- |
| `manicure`, case insensitive | 705 | 101 | Total brand, package, env, path, and fixture surface |
| lowercase `manicure` | 615 | 98 | Mostly Python imports, monkeypatch targets, CLI strings, paths |
| title case `Manicure` | 45 | 12 | UI text, docs in fixtures, class and product wording |
| `MANICURE_` env prefix | 45 | 11 | Requires coordinated env var decision |
| Python import namespace | 337 | 94 | `from manicure...` and `import manicure...` in pytest |
| Monkeypatch module strings | 206 | 34 | Patch target strings such as `manicure.cli...` |
| Metadata keys `manicure_*` | 9 | 3 | Runtime contract keys, not simple cosmetic text |
| `~/.manicure` or `/.manicure` | 2 | 2 | Storage path expectations |
| UI localStorage style keys | 5 | 2 | Includes `manicure-ui`, probably migration sensitive |
| Absolute repo path with `manicure` | 3 | 3 | Expected slug and CWD tests, visual metadata fixture |
| `manicure-worktrees` | 1 | 1 | Visual fixture CWD only |
| CLI command text | 30 | 22 | Examples and expected user facing output |
| `transport`, case insensitive | 529 | 49 | Existing domain language, should mostly remain |

Top files by case insensitive `manicure` count:

1. `api/src/manicure/cli/test_start_acceptance.py`: 38
2. `api/src/manicure/cli/test_start_storage.py`: 32
3. `api/src/manicure/cli/test_codex.py`: 28
4. `api/src/manicure/test_supervisor_pty.py`: 25
5. `api/src/manicure/api/v1/test_exchanges_pipeline_tokens.py`: 22
6. `api/src/manicure/api/v1/test_exchanges_list.py`: 21
7. `api/src/manicure/cli/test_diagnose.py`: 20
8. `api/src/manicure/test_http_provisional.py`: 19
9. `api/src/manicure/codex/test_transport_addon.py`: 19
10. `api/src/manicure/codex/test_transport_lifecycle.py`: 18

## Rename Categories and Line References

### 1. Python package imports and monkeypatch targets

These dominate the scope. If the package import namespace changes from `manicure` to a valid Python module name, likely `transport_matters`, tests must update imports and string patch targets together.

Representative lines:

- `api/src/manicure/adapters/test_adapter_registry.py:13` imports `manicure.adapters`.
- `api/src/manicure/adapters/test_adapter_registry.py:17` parametrizes module names `manicure.storage` and `manicure.codex`.
- `api/src/manicure/cli/test_start_storage.py:29` patches `manicure.cli.shutil.which`.
- `api/src/manicure/cli/test_start_storage.py:131` patches `manicure.cli.runner._run_children`.
- `api/src/manicure/codex/test_transport_support.py` has fmm downstream dependents in 8 transport test files, so rename this helper after package path moves.

Risk: stale monkeypatch strings will fail late at runtime, not at import time. Search specifically for quoted `"manicure.` after mechanical import rewriting.

### 2. Environment variables and storage locations

The tests assert `MANICURE_*` environment keys and `.manicure` storage paths. These are contract decisions, not just name cleanup.

Representative lines:

- `api/src/manicure/cli/test_start_storage.py:31` clears `MANICURE_STORAGE_DIR`.
- `api/src/manicure/cli/test_start_storage.py:78` states that `MANICURE_CWD` rides on the child env.
- `api/src/manicure/cli/test_start_storage.py:88` asserts `MANICURE_CWD` for the Claude child env.
- `api/src/manicure/cli/test_start_storage.py:107` reads `MANICURE_RUN_ID`.
- `api/src/manicure/cli/conftest.py:73` describes `MANICURE_STORAGE_DIR` sandboxing.
- `api/src/manicure/cli/conftest.py:75` mentions the `~/.manicure/workspaces/` manifest tree.
- `api/src/manicure/test_workspace.py:163` expects `Path.home() / ".manicure" / "workspaces"`.

Risk: renaming env variables without compatibility aliases will break users and test assumptions. Decide whether tests should expect `TRANSPORT_MATTERS_*`, keep `MANICURE_*`, or support both during migration.

### 3. Workspace slugs, absolute paths, and manifest payloads

Representative lines:

- `api/src/manicure/test_workspace.py:23` builds identity from `/Users/alphab/Dev/LLM/DEV/helioy/manicure/api`.
- `api/src/manicure/test_workspace.py:24` expects slug `helioy-manicure-api`.
- `api/src/manicure/test_manifest.py:14` defaults `_sample` slug to `helioy-manicure-api`.
- `api/src/manicure/test_manifest.py:16` embeds the same absolute repo path.
- `api/src/manicure/test_manifest.py:20` embeds `/Users/alphab/.manicure`.
- `www/tests/visual/fixtures/setup.ts:9` embeds a visual metadata CWD under `manicure-worktrees`.

Risk: after repo path rename, slug tests must change to `helioy-transport-matters-api` if the slugging behavior is intentionally path derived. Manifest fixture fields should move in the same commit as workspace semantics.

### 4. Runtime metadata keys

Representative lines:

- `api/src/manicure/test_flow_state.py:61` asserts `manicure_curated_ir`.
- `api/src/manicure/test_flow_state.py:66` writes `manicure_ir`.
- `api/src/manicure/test_flow_state.py:96` asserts `manicure_mutated_manually`.
- `api/src/manicure/test_flow_state.py:136` asserts `manicure_provisional_exchange_id`.
- `api/src/manicure/test_flow_state.py:160` asserts `manicure_dropped`.
- `api/src/manicure/api/v1/test_breakpoint.py:233` embeds `manicure_codex_transport` in flow metadata.

Risk: these keys may exist in live mitmproxy flow metadata or persisted artifacts. Rename only with migration or compatibility. Treat as data schema, not display copy.

### 5. API fixture corpus and sample transport payloads

Tracked API sample payload files:

- `api/tests/fixtures/codex_response_create.json`
- `api/tests/fixtures/codex_response_create_later_turn.json`
- `api/tests/fixtures/codex_response_create_outputs_only.json`
- `api/tests/fixtures/codex_response_create_tool_outputs.json`
- `api/tests/fixtures/codex_transport_chatgpt_success.json`
- `api/tests/fixtures/codex_transport_chatgpt_403.json`
- `api/tests/fixtures/codex_transport_chatgpt_403_response.txt`
- `api/tests/fixtures/codex_transport_proxy_502.json`
- `api/tests/fixtures/codex_transport_proxy_502_response.txt`
- `api/tests/fixtures/README.md`

Representative lines:

- `api/tests/fixtures/README.md:3` says the Codex transport contract is for Manicure.
- `api/tests/fixtures/README.md:16` anchors fixtures to stored `transport.json` shape.
- `api/tests/fixtures/codex_response_create_outputs_only.json:28` contains `M api/src/manicure/overrides.py` in sample output.
- `api/tests/fixtures/codex_transport_chatgpt_success.json:3` uses websocket protocol.
- `api/tests/fixtures/codex_transport_chatgpt_success.json:36` captures `response.create`.
- `api/tests/fixtures/codex_transport_proxy_502.json:3` uses websocket protocol.

Risk: fixture names already use `transport` and can mostly stay. Update embedded sample path `api/src/manicure/overrides.py` if package paths change, and adjust README product wording.

### 6. Frontend unit tests and product copy

Representative lines:

- `www/src/app.test.tsx:118` expects heading `Manicure`.
- `www/src/app.test.tsx:215` has paused flow transport `http`.

Risk: product rename changes visible copy assertions. Keep transport values unchanged unless protocol vocabulary changes.

### 7. Playwright visual fixtures and snapshots

Tracked visual fixture files:

- `www/tests/visual/fixtures.ts`
- `www/tests/visual/fixtures/details.ts`
- `www/tests/visual/fixtures/exchanges.ts`
- `www/tests/visual/fixtures/pausedFlow.ts`
- `www/tests/visual/fixtures/setup.ts`
- `www/tests/visual/fixtures/time.ts`

Representative lines:

- `www/tests/visual/top-bar.spec.ts:10` waits for heading `Manicure`.
- `www/tests/visual/top-bar.spec.ts:22` repeats the same heading check.
- `www/tests/visual/fixtures/setup.ts:70` writes localStorage key `manicure-ui`.
- `www/tests/visual/fixtures/details.ts:68` embeds response header value `manicure`.
- `www/tests/visual/fixtures/details.ts:397` recommends checking the Manicure proxy.
- `www/tests/visual/fixtures/details.ts:399` recommends `manicure codex --debug`.
- `www/tests/visual/fixtures/exchanges.ts:121` uses model `codex/transport-handshake`.

Tracked snapshot PNGs, 13 files:

- `www/tests/visual/exchange-detail-header.spec.ts-snapshots/exchange-detail-header-clean-visual-darwin.png`
- `www/tests/visual/exchange-detail-header.spec.ts-snapshots/exchange-detail-header-edited-visual-darwin.png`
- `www/tests/visual/exchange-detail-timeline.spec.ts-snapshots/exchange-detail-timeline-codex-visual-darwin.png`
- `www/tests/visual/exchange-detail-timeline.spec.ts-snapshots/exchange-detail-timeline-open-codex-visual-darwin.png`
- `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/exchange-detail-transport-codex-visual-darwin.png`
- `www/tests/visual/exchange-detail-transport.spec.ts-snapshots/exchange-detail-transport-diagnostics-visual-darwin.png`
- `www/tests/visual/exchange-list-anchored.spec.ts-snapshots/exchange-list-anchored-subagent-visual-darwin.png`
- `www/tests/visual/paused-header.spec.ts-snapshots/paused-1000-visual-darwin.png`
- `www/tests/visual/paused-header.spec.ts-snapshots/paused-1200-visual-darwin.png`
- `www/tests/visual/paused-header.spec.ts-snapshots/paused-1440-visual-darwin.png`
- `www/tests/visual/paused-header.spec.ts-snapshots/paused-1920-visual-darwin.png`
- `www/tests/visual/top-bar.spec.ts-snapshots/topbar-armed-visual-darwin.png`
- `www/tests/visual/top-bar.spec.ts-snapshots/topbar-disarmed-visual-darwin.png`

Risk: visual snapshots that include top bar text or transport diagnostic copy will change. Regenerate snapshots only after UI copy, localStorage migration, and fixture text decisions are final.

### 8. Existing transport terminology

The narrowed scope already contains 529 `transport` occurrences in 49 files. Most are domain terms for websocket or HTTP transport and should stay. Key examples:

- `www/tests/visual/exchange-detail-transport.spec.ts:8` describes Codex websocket states.
- `www/tests/visual/exchange-detail-transport.spec.ts:21` finds the transport tab.
- `api/src/manicure/api/v1/test_breakpoint.py:149` asserts `transport == "http"`.
- `api/src/manicure/api/v1/test_breakpoint.py:225` asserts `transport == "websocket"`.

Risk: avoid blind replacement of `transport` during the repo rename. It is core domain language and overlaps with the new repo name.

## Recommended Sequencing

1. Freeze compatibility decisions first: Python import namespace, CLI executable, env prefix, storage directory, localStorage keys, and persisted metadata keys.
2. Rename Python package path and update pytest imports, `pytest_plugins`, and monkeypatch string targets in one pass. Verify with a quoted string search for `"manicure.`.
3. Update path based tests next: workspace slug, manifest fixtures, absolute CWD examples, and sample payload file paths.
4. Update user facing test copy and visual fixtures: `Manicure` headings, proxy help text, CLI examples, and `api/tests/fixtures/README.md`.
5. Run unit tests before visual work: API pytest first, then Vitest TSX tests.
6. Regenerate Playwright snapshots last. Do this only after UI copy and fixture payloads stabilize.
7. Run final read only verification searches for `manicure`, `MANICURE_`, `.manicure`, `manicure-ui`, and `api/src/manicure` across tracked files.

## Open Questions

- Should the Python import namespace become `transport_matters`, or remain `manicure` for package compatibility?
- Should `MANICURE_*` env vars and `~/.manicure` storage paths be renamed immediately or supported as legacy aliases?
- Should persisted metadata keys such as `manicure_ir` and `manicure_codex_transport` migrate, or remain stable schema keys?
- Should visual localStorage keys migrate from `manicure-ui` to a new key with a backward compatibility bridge?

## Work Log

- fmm topology and test listings inspected first.
- Narrowed tracked scope with `git ls-files` and explicit exclusion filters.
- Counted occurrences in text files only.
- Sampled representative pytest, fixture, payload, TSX, and Playwright files.
- Did not modify the target repo.
