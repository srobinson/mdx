---
title: Python Conventions Gap Audit — transport-matters/api
type: research
tags: [python, conventions, uv, ruff, mypy, ty, moon, monorepo, migration, transport-matters, littleorgans]
summary: Section-by-section measurement of transport-matters/api against python-conventions-2026, with a prioritized punch list for landing it as a uv workspace member under littleorgans/python/ on Moon.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

# Python Conventions Gap Audit — transport-matters/api

## Executive Summary

`transport-matters/api/` is already a modern, uv-managed, src-layout, ruff+mypy-strict
FastAPI service that complies with the large majority of `python-conventions-2026`. It is
**not yet** a uv *workspace* member and is **not yet** known to Moon. The blockers to landing
it under `littleorgans/littleorgans/python/` are environmental (workspace wiring, version
floor alignment, Moon toolchain enablement), not code-quality rewrites. Two genuine
convention gaps in the code itself are the `requires-python` floor (3.12 vs the 3.13 standard
the repo already pins) and a pydantic mypy plugin dependency that blocks a future `ty` swap.

## Audited Inputs

- Guide / rubric: `~/.mdx/research/python-conventions-2026.md`
- Target conventions: `littleorgans/littleorgans/CLAUDE.md`, `moon.yml`, `.moon/{toolchains,workspace}.yml`, empty `python/` stub
- Member-discovery mechanics: `~/.mdx/research/python-workspace-monorepo-member-discovery-reference.md`
- Actual code: `transport-matters/api/` (fmm index present but STALE — built with v0.3.0, runtime v0.3.4; `fmm generate` required before structural tooling. Structure here was derived directly from the filesystem.)

## Open Questions — Resolved

1. **src-layout vs flat-layout?** **src-layout.** Package lives at `src/transport_matters/`; `pyproject.toml:88` declares `packages = ["src/transport_matters"]`. Complies with the guide's preference for libraries/services.
2. **uv workspace member, or pip/requirements?** **Standalone uv project, not a workspace member.** `uv.lock` (324 KB) is present and committed; there is no `requirements.txt`, `setup.py`, or `setup.cfg`. `[tool.uv]` exists (`pyproject.toml:74`) but only carries `override-dependencies`; there is **no `[tool.uv.workspace]`**. Package manager is uv; lockfile situation is clean and single-project.
3. **CI type checker / strict?** **mypy, strict ON.** `pyproject.toml:135-141`: `[tool.mypy] strict = true`, `warn_return_any = true`, `warn_unused_configs = true`, `plugins = ["pydantic.mypy"]`. `.mypy_cache/` confirms it runs. Gate is `mypy src/` in `justfile:50` and the `ci` recipe (`justfile:62-66`). No pyright config present.
4. **mypy plugins that block a future `ty` migration?** **Yes — one: `pydantic.mypy`** (`pyproject.toml:141`). `ty` has no plugin system as of 2026, so the Pydantic plugin's inferred `__init__` signatures and validator typing would not carry over. SQLAlchemy/Django plugins are absent (no ORM in deps). This is the single `ty`-migration blocker.
5. **How should Moon wrap uv/ruff/pytest without duplicating deps?** Moon owns the task graph only; uv stays the single source of truth for what is installed. Each task shells `uv run …` (`uv sync`, `uv run ruff …`, `uv run mypy`, `uv run pytest`). No dependency lists enter Moon config. See "uv-workspace-member wiring steps" below.

## Section-by-Section Verdicts

### Project Shape — GAP (minor)
- src-layout: COMPLIES (`src/transport_matters/`).
- Single source of truth in `pyproject.toml`: COMPLIES. No `setup.py`/`setup.cfg`/`.flake8`/`.isort.cfg`/`tox.ini`; ruff, mypy, pytest, coverage, hatch all configured in `pyproject.toml`.
- Distribution name `transport-matters` (kebab) → import `transport_matters` (snake): COMPLIES with default mapping.
- Thin `__init__.py`: COMPLIES. Root `__init__.py` only resolves `__version__` and sets `__all__` (no side effects).
- **GAP:** naming suffix. The distribution is named `transport-matters`, not `transport-matters-api`/`-service`. The guide's `-api`/`-service` suffix convention is advisory; littleorgans treats transport as an **external** context (root CLAUDE.md: "Transport remains external and out of scope"). Decision needed on whether the member keeps `transport-matters` or is renamed for the monorepo namespace.

### Packaging and Build — GAP (workspace wiring)
- uv as manager/resolver: COMPLIES.
- `uv.lock` committed: COMPLIES.
- PEP 621 `[project]` deps + PEP 735 `[dependency-groups] dev`: COMPLIES (`pyproject.toml:38-65`).
- Explicit build backend: COMPLIES — `hatchling` + `hatch-vcs` (`pyproject.toml:79-81`), not bare setuptools. Guide names hatchling as acceptable.
- **GAP (P0):** not a workspace member. No `[tool.uv.workspace]` anywhere in the littleorgans tree, and api/ has no `[tool.uv.sources] … { workspace = true }`. The guide requires monorepo members to share one workspace + one lockfile at the language-subtree root and depend on each other via workspace sources.
- **GAP (P0):** Moon does not orchestrate it. `littleorgans/moon.yml` is Rust-only; `.moon/toolchains.yml:8` has `python` commented out; `.moon/workspace.yml` globs only `crates/*/` and `tools/*/`. No `python/` project source is registered.

### Python Version and Runtime — GAP
- **GAP (P1):** version-floor mismatch. `requires-python = ">=3.12"` and `ruff target-version = "py312"` / `mypy python_version = "3.12"` (`pyproject.toml:8,97,136`), but `.python-version` pins **3.13** and classifiers list 3.13. The guide's standard floor is **3.13**. The pinned interpreter and the declared floor disagree.
- **GAP (P1):** `from __future__ import annotations` appears in **194 files** — reflexive blanket use the guide explicitly warns against on 3.13+ ("add it only when you need deferred evaluation … or to break an import cycle"). On a 3.13 floor most are removable. Low correctness risk, high convention noise.
- No free-threaded/JIT reliance observed: COMPLIES.

### Modules and Files — COMPLIES
- `__all__` used in 29 modules; no star imports anywhere in src.
- LOC discipline: COMPLIES. Largest non-test file is `exchange_recorder.py` at 695 lines; **zero files exceed 700** (littleorgans hard limit). `repair.py` 672, `supervisor.py` 666, `disk.py` 599 sit just under and are watch-items if extended.
- Cohesive modules, shallow relative imports, documented import DAG (`api/CLAUDE.md`: `ir → adapters → rules → pipeline → storage → breakpoint → server`): COMPLIES.

### Typing and API Design — COMPLIES
- Builtin generics and `X | None` enforced by local `api/CLAUDE.md` ("Builtins only"); mypy strict is the gate.
- ABC for runtime dispatch / Protocol for shape-only: documented and matches the guide.
- Pydantic v2 at trust boundaries, frozen IR models: COMPLIES (`api/CLAUDE.md`).
- `Any` requires a justifying comment: local rule matches guide.
- PEP 695 native type params: not separately verified per-symbol; mypy-strict + py312 target permits them. N/A to flag as a gap absent a counter-example.

### Error Handling — COMPLIES (with one note)
- Package exception story: domain exceptions in `exceptions.py`, translated at the FastAPI layer, always chained `raise X from original` (`api/CLAUDE.md`). COMPLIES.
- **Note (not a gap):** `exceptions.py` roots `NotFoundError`/`ConflictError` in `fastapi.HTTPException` and `UnsupportedProviderError` in bare `Exception`; there is no single package-base error class as the guide's example suggests. This is a deliberate FastAPI-edge pattern, acceptable per "follow the local source of truth."
- 38 `except Exception` occurrences in non-test src — the guide tolerates these only at top-level boundaries that log and re-raise/convert. Most appear to be addon/proxy/IO boundaries (mitmproxy, subprocess, serialization). **Spot-audit recommended** but not a blocker; no bare `except:` exists (0 occurrences).

### Async — COMPLIES
- asyncio with the documented async/sync boundary (`api/CLAUDE.md`: I/O async, pure computation sync).
- One `asyncio.gather` in non-test src; **zero `TaskGroup`**. The guide prefers `TaskGroup` for *fallible* groups. Single gather is a P2 review item, not a blocker — verify it is not a fallible fan-out.

### Dependencies — COMPLIES
- `httpx`, `pydantic-settings`, `fastapi[standard]`, `typer`, `aiofiles`, `mitmproxy`: all guide-sanctioned defaults; all typed (`types-aiofiles` stub pulled in dev).
- Lower-bounded `>=` constraints, exact pins deferred to `uv.lock`: COMPLIES.
- `override-dependencies` for `pyOpenSSL>=26.0.0` is documented with rationale (`pyproject.toml:67-77`): good practice.

### Logging and Diagnostics — GAP (minor)
- **GAP (P2):** guide recommends **structlog**; api uses a hand-rolled `JSONFormatter(logging.Formatter)` (`logging.py`) over stdlib logging. 17 `logging.getLogger` call sites, library-style. Zero `print()` for diagnostics (COMPLIES with the anti-print rule). The custom JSON formatter is functional; structlog is a nice-to-have, not a blocker. Stuart is the sole operator, so log-aggregator ergonomics are low priority.

### Lints and Formatting — GAP (config drift) / mostly COMPLIES
- ruff as sole linter+formatter, no black/isort/flake8: COMPLIES. Rich select set (`E,W,F,I,UP,B,SIM,C4,RET,PTH,TCH`).
- **GAP (P2):** `line-length = 88` (`pyproject.toml:98`); guide example uses `100`. Cosmetic; align on whatever littleorgans/python standardizes.
- **GAP (P2):** ruff select omits `ASYNC` and `RUF` from the guide's recommended set; adds `RET`/`TCH` (fine). Add `ASYNC` and `RUF` for parity given the async-heavy codebase.
- **GAP (P1, decision):** type checker is mypy-strict (good, guide-sanctioned), but littleorgans is a Rust-first Astral-tooled monorepo. Guide recommendation: keep mypy/pyright as the gate, track `ty`. The `pydantic.mypy` plugin (see Q4) is the concrete obstacle to ever switching to `ty`.
- `target-version = "py312"` should move to `py313` (ties to the version-floor gap).

### Type-Safety Escape Hatches — COMPLIES
- Only 3 `type: ignore` in non-test src; local rule requires coded ignores and justified `Any`. No bare-ignore sprawl.

### Testing — GAP (minor)
- pytest, colocated unit tests (`src/.../test_*.py`, 116 files) + `tests/integration/` (7 files): COMPLIES and matches `api/CLAUDE.md`.
- Plain functions + fixtures in `conftest.py`, `asyncio_mode = "auto"`: COMPLIES. No `unittest.TestCase` pattern observed.
- `fail_under = 80` coverage gate (`pyproject.toml:157`): reasonable.
- **GAP (P2):** uses `pytest-asyncio` (`pyproject.toml:59`), guide *prefers* `anyio`'s pytest plugin but explicitly allows `pytest-asyncio`. Acceptable; no action required unless standardizing the python subtree on anyio.

### Documentation — COMPLIES
- `api/CLAUDE.md` documents the async boundary, type rules, pydantic idioms, import DAG, test layout, and error policy. Public-API docstrings present (e.g., `UnsupportedProviderError`). No counter-evidence of signature-restating docstrings at scale.

### Build and CI — GAP (Moon integration)
- Local proof exists: `justfile` `ci` recipe runs `ruff format --check`, `ruff check`, `mypy src/`, `pytest` (`justfile:62-66`) — matches the guide's local-proof block, minus `uv sync --frozen`.
- `.pre-commit-config.yaml` runs ruff-check + ruff-format + hygiene hooks: COMPLIES with the pre-commit recommendation (no type-check hook, which the guide allows — full type-check belongs in CI).
- **GAP (P0):** not expressed as Moon tasks. littleorgans requires `moon ci` to orchestrate the gate (root CLAUDE.md "Build, test, and generated surfaces"). The api/ gate currently lives only in its own `justfile`.
- **GAP (P1):** CI should use `uv sync --frozen` to fail on lockfile drift; the current `install` recipe uses plain `uv sync --all-extras --dev`.

### Monorepo-Member Checklist (guide §Review) — GAP
- deps via workspace sources: GAP (standalone today).
- one lockfile: GAP (own `uv.lock`; must fold into a `python/`-rooted workspace lock).
- config in `pyproject.toml`: COMPLIES.
- tasks wired into repo runner (Moon): GAP.

## COMPLIES vs GAP Tally

- **COMPLIES:** Modules/Files, Typing, Error Handling, Async, Dependencies, Escape Hatches, Documentation, plus most of Project Shape, Packaging, Lints, Testing. **~11 sections substantially clean.**
- **GAP:** Packaging (workspace wiring), Python Version/Runtime, Logging, Lints (config drift + ty/plugin), Build/CI (Moon), Monorepo-member checklist. **~6 sections with gaps**, of which only 3 are P0 blockers and all 3 are environmental wiring, not code rewrites.

## (a) Prioritized Migration Punch List

### P0 — blockers (must land for the member to exist under Moon)
1. **Create the python-subtree uv workspace.** Add a root `pyproject.toml` (or reuse `littleorgans/python/pyproject.toml`) with `[tool.uv.workspace] members = ["*/"]` (or `["api"]`) rooted at `littleorgans/python/`. One `uv.lock` at that root; delete api's standalone lock after folding it in.
2. **Move api/ into `littleorgans/python/api/`** (or `python/transport-matters/`) preserving src-layout. Keep its `pyproject.toml`; remove `[tool.uv]` if its only content (`override-dependencies`) needs to move to the workspace root (workspace-level resolution overrides live at the root).
3. **Enable the Python toolchain in Moon.** Uncomment `python: {}` in `.moon/toolchains.yml`; pin `version: "3.13"`. Add the project source to `.moon/workspace.yml` (`"python/api": "python/api"` or extend globs to `python/*/`). Add a `python/api/moon.yml` with `language: "python"` and `uv run`-wrapping tasks (see wiring steps).

### P1 — required before sign-off (correctness/convention)
4. **Align the version floor to 3.13.** Set `requires-python = ">=3.13"`, ruff `target-version = "py313"`, mypy `python_version = "3.13"`. `.python-version` already says 3.13. Resolves the pin/floor contradiction.
5. **Switch CI sync to `uv sync --frozen`** (Moon `install`/`sync` task) to fail on lockfile drift.
6. **Decide and record the type-checker path:** keep mypy-strict as the gate (recommended) and document that `pydantic.mypy` blocks `ty`; or commit to evaluating `ty` and accept the Pydantic typing regression. Do not switch silently.

### P2 — nice-to-haves
7. Strip reflexive `from __future__ import annotations` (194 files) down to the few that need forward-ref deferral or cycle-breaking on a 3.13 floor.
8. Add `ASYNC` and `RUF` to ruff `select`; align `line-length` with the python-subtree standard (88 vs 100).
9. Spot-audit the 38 `except Exception` sites; confirm each is a true top-level boundary that logs and re-raises/converts.
10. Verify the single `asyncio.gather` is not a fallible fan-out; convert to `TaskGroup` if it is.
11. Optional: adopt `structlog` to replace the hand-rolled `JSONFormatter`; optional: move `pytest-asyncio` → anyio plugin if the subtree standardizes on anyio.
12. Regenerate the stale api/ fmm index (`fmm generate && fmm validate`) post-move; the current index is v0.3.0 against a v0.3.4 runtime.

## (b) uv-Workspace-Member Wiring Steps

1. **Workspace root** at `littleorgans/python/pyproject.toml`:
   ```toml
   [tool.uv.workspace]
   members = ["*/"]            # or ["api"]
   # exclude = ["experimental"]
   ```
   Move api's `override-dependencies = ["pyOpenSSL>=26.0.0"]` here under `[tool.uv]` so the override applies workspace-wide.
2. **Member manifest** `python/api/pyproject.toml`: unchanged except the version-floor bumps (P1.4) and removal of the now-root-level `[tool.uv]` overrides. Keep `[build-system] hatchling`, ruff/mypy/pytest config.
3. **Single lockfile:** run `uv sync` at the workspace root; commit `python/uv.lock`. Delete `python/api/uv.lock`. Members share one venv.
4. **Workspace sources (future cross-member deps):** when a second python member needs api, add to that member: `[tool.uv.sources] transport-matters = { workspace = true }`. None needed today (api is the only member).
5. **Moon project** `python/api/moon.yml` — Moon owns the graph, uv owns installs (no dependency lists in Moon):
   ```yaml
   language: "python"
   layer: "application"
   tasks:
     sync:        { command: "uv sync --frozen", options: { runInCI: "always" } }
     fmt-check:   { command: "uv run ruff format --check src/", deps: ["sync"], options: { runInCI: "always" } }
     lint:        { command: "uv run ruff check src/",          deps: ["sync"], options: { runInCI: "always" } }
     typecheck:   { command: "uv run mypy src/",                deps: ["sync"], options: { runInCI: "always" } }
     test:        { command: "uv run pytest",                   deps: ["sync"], options: { runInCI: "always" } }
     check:       { deps: ["fmt-check", "lint", "typecheck"],   options: { runInCI: false } }
   ```
6. **Toolchain + workspace registration:** `.moon/toolchains.yml` → `python: { version: "3.13" }`; `.moon/workspace.yml` → add `"python/api": "python/api"` (or `python/*/` glob). `moon ci` now runs the python gate alongside Rust.
7. **Verify:** `uv sync --frozen` at root resolves clean; `moon run python/api:check` and `moon run python/api:test` pass; `moon ci` includes the new tasks.

## (c) Needs a Human Decision

- **Member name & namespace.** Keep `transport-matters`, or rename to fit the littleorgans python namespace? Root CLAUDE.md says transport is an *external* context and "out of scope for this monorepo phase" — so confirm transport-matters is actually migrating into `littleorgans/python/` now, versus staying a sibling repo. This contradicts the littleorgans framing and must be resolved before any move.
- **Type-checker future.** Stay on mypy-strict (recommended, keeps Pydantic plugin) vs invest in `ty` early (Astral-tooled monorepo argument) and accept lost Pydantic plugin inference.
- **structlog adoption** vs keeping the working hand-rolled JSON formatter — purely cost/benefit for a single-operator tool.
- **anyio vs pytest-asyncio** standardization for the whole python subtree, if more members arrive.
- **Backcompat stance on env vars.** api uses `DEBUG`, `SECRET_KEY`, etc.; littleorgans mandates `LILO_*` and refuses legacy `RTM_*`/`SM_*`/`AGM_*`. If transport migrates in, confirm whether its env-var surface must converge on `LILO_*` (likely yes per the no-backcompat doctrine).

## Confidence

High on the code-and-config findings (read directly from source). Medium on whether transport-matters is genuinely slated to move into `littleorgans/python/` at all — the littleorgans CLAUDE.md explicitly scopes transport as external, so the migration premise itself is the first thing to confirm with Stuart.
