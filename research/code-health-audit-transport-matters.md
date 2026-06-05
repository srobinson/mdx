---
title: Transport Matters code health audit
type: research
tags: [transport-matters, code-health, fmm, architecture, dry]
summary: fmm backed audit grades the repo C, with strong test volume but real duplication, cycles, facade debt, and oversized functions.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-23
updated: 2026-06-23
---

# Transport Matters code health audit

## Executive Summary

Grade: **C**.

Transport Matters is not a disaster, but green CI is flattering it. The repo has real tests and source files mostly stay below the stated size limits, yet fmm shows 26 production duplicate or near duplicate clusters, 2 runtime import cycles, obsolete re export surfaces, and 9 source functions over the 150 line threshold.

One line verdict: **C, shippable pre release code with decent test mass, but structural debt is now large enough that the next feature wave will make it worse unless duplication and layering get paid down first.**

## Measurement Basis

- fmm index: 889 files, 144,404 LOC.
- fmm validation: clean, all 889 files indexed and current.
- fmm status: git SHA `650bda1b7078`, branch `fix/liveness-recover-policy`. fmm reported `Dirty: dirty`, but an independent `git status --short --untracked-files=all` check after the audit was empty.
- fmm config: no `.fmmrc` found, defaults in use.
- Audit scope: `api/`, `www/`, and `desktop/`.
- Repo edits by this audit: none. Report written outside the repo.

## Project Metadata

| Area | Stack | Build and runtime notes |
| --- | --- | --- |
| `api/` | Python, FastAPI, Typer, mitmproxy, Pydantic, Postgres via psycopg, Alembic | `api/pyproject.toml`, Python `>=3.14`, Hatchling build, console script `transport-matters = transport_matters.cli:main` |
| `www/` | TypeScript, React, Vite, Zustand, TanStack Query, xterm, Playwright, Vitest | `www/package.json`, Node `>=20.19.0`, `pnpm@10.8.1` |
| `desktop/` | TypeScript, Electron, Vitest | `desktop/package.json`, Node `>=20.19.0`, `pnpm@10.8.1` |

Critical runtime dependencies: FastAPI, mitmproxy, Typer, psycopg, Alembic, React, Vite, Zustand, TanStack Query, xterm, Electron.

## Top Level Metrics

| Metric | Whole repo | `api/` | `www/` | `desktop/` |
| --- | ---: | ---: | ---: | ---: |
| Indexed files | 889 | 463 | 409 | 17 |
| Indexed LOC | 144,404 | 91,385 | 50,008 | 3,011 |
| Source files | 481 | 231 | 242 | 8 |
| Source LOC | 72,055 | 43,127 | 27,384 | 1,544 |
| Test files | 408 | 232 | 167 | 9 |
| Test LOC | 72,349 | 48,258 | 22,624 | 1,467 |
| Test to source LOC ratio | 1.00 | 1.12 | 0.83 | 0.95 |

Interpretation: test volume is high. The risk is not missing tests by count, it is structural false confidence from large, duplicated, integration shaped tests that keep current behavior green while design debt accumulates.

## Architecture

Documented architecture in `PROJECT.md` says the Python core should follow this acyclic order: `ir -> adapters -> rules -> pipeline -> storage -> breakpoint -> server`. fmm contradicts the acyclic claim in current code.

Runtime source cycles found by `fmm_dependency_cycles`:

1. Four file captured run cycle:
   - `api/src/transport_matters/captured_codex.py` + `build_codex_captured_invocation`
   - `api/src/transport_matters/captured_run_context.py` + `build_captured_run_context`
   - `api/src/transport_matters/captured_run.py` + `prepare_captured_run`
   - `api/src/transport_matters/cli/codex_cmd.py` + `build_codex_invocation`

   Why it matters: capture core imports CLI launch construction, then CLI imports capture. This keeps the captured run seam dependent on import order and makes server side run launch transitively reach CLI code.

2. Override state cycle:
   - `api/src/transport_matters/override_state.py` + override store state
   - `api/src/transport_matters/overrides.py` + override models and operations

   Why it matters: state and model or operation layers are coupled both ways. This makes future override changes harder to isolate.

Type inclusive cycle found by `fmm_dependency_cycles edge_mode=all`:

3. Canvas lifecycle cycle:
   - `www/src/session-canvas/model/capturedRunLifecycle.ts`
   - `www/src/session-canvas/model/paneLifecycle.ts`

   Why it matters: one edge is type only, but one runtime edge remains. The model layer is close to a bidirectional lifecycle aggregate.

Layering inversion worth naming: `api/src/transport_matters/api/v1/run_routes.py` reaches `api/src/transport_matters/cli/launch_profile.py`, `api/src/transport_matters/cli/launch_runtime.py`, and `api/src/transport_matters/cli/runner.py` transitively through `captured_run`. `fmm_search` also reports 64 files depending transitively on `api/src/transport_matters/cli/codex_cmd.py`.

## DRY Debt

fmm duplicate metrics:

| Scope | Clusters | Member symbols | Max copy count | Notes |
| --- | ---: | ---: | ---: | --- |
| Production only, min score 0.90 | 26 | 66 | 6 | 22 clusters touch `api/`, 4 touch `www/`, 0 touch `desktop/` |
| Production plus tests, min score 0.90 | 76 | 192 | 10 | Test duplication adds 50 clusters |
| `api/v1`, min score 0.80 | 14 | not summed | 5 | Captures route helper and model field near duplicates missed by the stricter 0.90 threshold |

Worst production duplicate clusters:

- Alembic migration `downgrade` functions: 6 copies across `api/migrations/versions/*`.
- Alembic migration `upgrade` functions: 6 copies across `api/migrations/versions/*`.
- `api/src/transport_matters/session/async_dao.py` + `AsyncSessionDao.count_dead_letters_by_run`, `AsyncSessionDao.count_dead_letters_by_session` and `api/src/transport_matters/session/dao.py` + `SessionDao.count_dead_letters_by_run`, `SessionDao.count_dead_letters_by_session`: 4 member cluster.
- `www/src/ambient/engine/viewport.ts` + `clampScale`, `panViewport`, `zoomViewportAt` duplicated exactly in `www/src/engine/reducers/layoutState.ts`.
- `api/src/transport_matters/api/v1/session_models.py` + `_to_camel` duplicated in `api/src/transport_matters/session/timeline_models.py`.
- `api/src/transport_matters/cli/home_overlay.py` + `validate_runtime_home_template` duplicated in `api/src/transport_matters/cli/home_seeders.py`.
- `api/src/transport_matters/cli/channel_cmd.py` + `_resolve_channel_or_exit` duplicated in `api/src/transport_matters/cli/tail_cmd.py`.

The copied API error helper is not isolated. At the strict repo threshold it is hidden below 0.90, but lowering fmm to 0.80 within `api/v1` shows 14 local clusters, including `run_routes._response_payload` versus `space_routes._response_payload`, `run_routes._not_found` and `session_routes._not_found`, plus duplicate `_decode_cursor` and `_encode_cursor` helpers. This points to route module copy patterns, not a one off mistake.

The worst test duplicate cluster is `storage` fixtures copied 10 times across storage and Codex repair tests. Other repeated test fixtures include `_reset_store` copied 5 times and API `client` fixtures copied 5 times. Tests are numerous, but not especially DRY.

## Dead Code, Obsolete Paths, and Export Surface Debt

fmm zero importer signals are noisy for route handlers and decorators, so this section only names high confidence structural debt from fmm glossary and file outlines.

High confidence facade and shim debt:

- `api/src/transport_matters/index/__init__.py`: 17 exports, 17 with zero source named importers. Examples: `TranscriptTailer`, `SessionBinding`, `get_adapter`, `ingest_records`, `register_session_cursor`, `synth_session_id`. The underlying symbols are used from their real modules, but the package facade appears unused by source code.
- `api/src/transport_matters/cli/__init__.py`: 558 LOC, 22 exports, 14 with zero source named importers. Examples: `allocate_port_pair`, `inject_system_prompt`, `port_in_use`, `run_children`, `run_client_with_retry`, `workspace_id`, `workspace_root`. This is a large compatibility barrel in a pre release repo where compatibility is not a constraint.
- `api/src/transport_matters/supervisor.py`: 5 re exports, with `install_parent_cbreak` and `pty_shuttle` showing zero source named importers through the facade.
- `api/src/transport_matters/adapters/__init__.py`: `get_adapter` and `get_adapter_for_provider` show zero source named importers through that facade.
- `api/src/transport_matters/index/adapters/__init__.py`: `get_adapter` shows zero source named importers through that facade.

Module level orphan candidates need manual review before deletion. fmm reports zero direct downstream for 32 `api/` source files, 6 `www/` source files, and 1 `desktop/` source file, but many are entrypoints, route modules, configs, migrations, or test setup files. The useful signal is not the raw zero downstream count. The useful signal is that obvious facades have zero named source use while original modules do real work.

## Size Discipline

File threshold results:

- Source files over 700 LOC: 0.
- All files over 700 LOC: 1, `www/src/components/ExchangeDetail.test.tsx` at 729 LOC.
- Largest source files are just below the hard limit:
  - `api/src/transport_matters/cli/desktop_cmd.py`: 696 LOC.
  - `api/src/transport_matters/api/v1/run_routes.py`: 680 LOC.
  - `api/src/transport_matters/index/tailer.py`: 677 LOC.
  - `api/src/transport_matters/cli/codex_cmd.py`: 675 LOC.
  - `desktop/src/main.ts`: 668 LOC.

Function threshold results:

- Source functions over 150 LOC: 9.
- Test functions or describe blocks over 150 LOC: 26.

Worst source functions:

| File + symbol | LOC |
| --- | ---: |
| `www/src/session-canvas/lab/CanvasLabRoute.tsx` + `CanvasLabRoute` | 291 |
| `www/src/components/ExchangeDetail.tsx` + `ExchangeDetail` | 266 |
| `www/src/components/detail/ExchangeCard.tsx` + `ExchangeCard` | 214 |
| `api/src/transport_matters/cli/diagnose.py` + `run_doctor` | 172 |
| `api/src/transport_matters/codex/exchange.py` + `finalize_codex_provisional_exchange` | 166 |
| `www/src/session-canvas/launcher/useCommandCenter.ts` + `useCommandCenter` | 159 |
| `www/src/components/editor/useThinkingOverrides.ts` + `useThinkingOverrides` | 155 |
| `www/src/session-canvas/components/CanvasSurface.tsx` + `CanvasSurface` | 155 |
| `api/src/transport_matters/captured_run_context.py` + `build_captured_run_context` | 151 |

Interpretation: the file rule is technically passing for source, but several major seams sit within 5 percent of the ceiling. The function rule is already failing in source.

## Test Quality

The test count is the repo's strongest metric:

- 408 test files and 72,349 test LOC.
- Test to source LOC ratio is 1.00 overall.
- `api/` test LOC exceeds source LOC by 12 percent.
- `desktop/` test LOC almost matches source LOC.

The concern is shape, not quantity:

- 26 test functions or describe blocks exceed 150 LOC.
- 50 duplicate clusters appear only when tests are included.
- The largest duplicate cluster is a `storage` fixture copied 10 times.
- `www/src/components/ExchangeDetail.test.tsx` is 729 LOC, which is the only file over the repo's hard threshold.

Green CI is useful here, but it should not be treated as a design health signal. The tests are large enough and duplicate enough that they may preserve current behavior while making refactors expensive.

## Top 5 Concrete Debts

1. **Captured run import cycle.** `api/src/transport_matters/captured_codex.py` + `build_codex_captured_invocation`, `api/src/transport_matters/captured_run_context.py` + `build_captured_run_context`, `api/src/transport_matters/captured_run.py` + `prepare_captured_run`, and `api/src/transport_matters/cli/codex_cmd.py` + `build_codex_invocation` form a runtime cycle. This is the highest risk debt because it violates the intended DAG and keeps the API launch path tied to CLI internals.

2. **Unused compatibility facades.** `api/src/transport_matters/index/__init__.py` has 17 of 17 exports with zero source named importers. `api/src/transport_matters/cli/__init__.py` has 14 of 22 exports with zero source named importers and is 558 LOC. Pre release status means these barrels should be deleted or collapsed into direct imports rather than preserved.

3. **Session DAO duplication.** `api/src/transport_matters/session/async_dao.py` + `AsyncSessionDao.count_dead_letters_by_run`, `AsyncSessionDao.count_dead_letters_by_session`, `get_events_with_raw_for_owner`, `list_child_sessions_for_owner`, and `get_events_for_owner` duplicate sync DAO logic in `api/src/transport_matters/session/dao.py`. This guarantees query fixes need parallel edits.

4. **Canvas viewport logic split.** `www/src/ambient/engine/viewport.ts` + `clampScale`, `panViewport`, `zoomViewportAt` are exact duplicates of `www/src/engine/reducers/layoutState.ts` + the same symbols. This is small but dangerous because viewport math must stay perfectly consistent.

5. **Oversized UI and command functions.** 9 source functions exceed the 150 LOC rule. Worst are `www/src/session-canvas/lab/CanvasLabRoute.tsx` + `CanvasLabRoute` at 291 LOC, `www/src/components/ExchangeDetail.tsx` + `ExchangeDetail` at 266 LOC, and `www/src/components/detail/ExchangeCard.tsx` + `ExchangeCard` at 214 LOC. These are already beyond the stated threshold.

## Recommendation

Do not start by rewriting everything. Start with the structural debt that blocks future work:

1. Break the captured run to CLI cycle by moving Codex invocation construction behind a lower level launch adapter or dependency injection seam. Add a subprocess cold import test for the extracted seam.
2. Delete or collapse unused re export facades, starting with `api/src/transport_matters/index/__init__.py`. Update imports to real owner modules.
3. Create shared route helpers for API cursor, response payload, and not found errors. Use one owner under `api/src/transport_matters/api/v1/`.
4. Consolidate viewport math into one module and make reducers import it.
5. Split the 9 oversized source functions before adding new code to their files.
6. Consolidate repeated test fixtures after the source seams settle, especially storage fixtures and API clients.

## Open Questions

- Some fmm zero importer candidates are decorators, route handlers, entrypoints, or configs. Deletion needs a targeted runtime or test proof per candidate.
- The sync DAO may be intentionally retained for old call sites. If not required, it is a strong deletion candidate because the async DAO appears to own modern session store access.
- The migration duplicate clusters may be acceptable Alembic boilerplate. They are counted objectively but should not be the first cleanup target.
