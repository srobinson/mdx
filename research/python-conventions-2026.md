---
title: Python Conventions for Agents, 2026
type: research
tags: [python, conventions, uv, ruff, pyproject-toml, typing, async, pytest, ty, mypy, monorepo, ci]
summary: Condensed operating instructions for agents writing, editing, and reviewing modern Python in a uv-based polyglot monorepo.
status: active
confidence: high
created: 2026-05-30
updated: 2026-05-30
related:
  - python-workspace-monorepo-member-discovery-reference.md
  - python-language-support-gap-analysis-fmm.md
  - rust-conventions-2026.md
---
# Python Conventions for Agents, 2026
This file is an instruction guide, not a survey.
Use it when creating, editing, reviewing, or planning Python code.
Prefer the project conventions in front of you when they are explicit.
Use this guide when the repo is silent, inconsistent, or newly scaffolded.
If a local `AGENTS.md`, `CLAUDE.md`, issue body, or design record conflicts
with this file, follow the local source of truth.
This guide is generic. It is not specific to any one codebase.
For monorepo member discovery and import-name resolution mechanics, defer to
`python-workspace-monorepo-member-discovery-reference.md`; do not re-derive them.
For how a code indexer sees Python structure, see
`python-language-support-gap-analysis-fmm.md`.

## Agent Rules
Validate before acting.
Read the existing package shape before adding code.
Search before creating helpers, types, protocols, modules, constants, or files.
Do not introduce duplicate paths for the same behavior.
Delete old paths during refactors unless a staged migration is explicit.
Keep public API changes deliberate and easy to review.
Keep private implementation changes boring.
Do not expand scope because a pattern looks convenient.
Run the repo's documented checks before claiming done.
If no documented checks exist, run ruff format, ruff check, the type checker,
and pytest.
Target a single supported Python version per the project; do not write code for
versions the project does not run.
Do not add dependencies casually.
Do not add a Protocol or ABC for testability unless a second real
implementation exists.
Do not hand roll async primitives, retry loops, or parsers when the project
already has a proven local abstraction.
Type all new public functions; let local inference cover obvious locals.
Write docstrings on public API; skip them on self-evident private helpers.
Write comments only where they prevent real confusion.

## Project Shape
Use `pyproject.toml` as the single source of truth for packaging, tooling, and
metadata. Do not split config across `setup.py`, `setup.cfg`, `requirements.txt`,
`.flake8`, `.isort.cfg`, `tox.ini`, and `pyproject.toml`. Consolidate into
`pyproject.toml` plus a lockfile.
Prefer **src-layout** for libraries and services:
```
package/
├── pyproject.toml
└── src/
    └── package_name/
        └── __init__.py
```
src-layout prevents accidental imports of the in-tree package before install
and makes the import surface explicit. Flat-layout is acceptable for tiny
single-module utilities.
Distribution name (`[project] name`, hyphen-friendly) differs from import name
(underscores, a valid identifier). Default mapping: lowercase, collapse runs of
`-`, `.`, `_` into a single `_`. See the member-discovery reference for the full
resolution algorithm and per-backend overrides.
One importable top-level package per distribution unless there is a deliberate
namespace-package reason.
Use kebab-case for distribution names. Use snake_case for import names.
Common suffixes mirror Rust-side intent and aid a polyglot monorepo:
- `-core` for domain types and pure logic.
- `-api` or `-service` for the application/server surface.
- `-cli` for command line surfaces.
- `-client` for SDKs and outbound adapters.
- `-testing` for shared test helpers.
Keep `__init__.py` thin: re-export the public API, do not run side effects.

## Packaging and Build
Use **uv** as the package manager, resolver, and virtual-environment manager.
By 2026 uv is the de facto default for new Python projects, with resolution
10-100x faster than pip and first-class Cargo-style workspaces. (Astral docs;
pydevtools; Airflow and others run uv workspaces in production.)
Commit `uv.lock`. It is the reproducibility contract. One lockfile per
workspace, not per member.
Declare dependencies under PEP 621 `[project]`:
```toml
[project]
name = "package-name"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["httpx>=0.27", "pydantic>=2.7"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6", "ty"]
```
Use PEP 735 `[dependency-groups]` for dev/test/lint groups. Prefer it over
legacy `[project.optional-dependencies]` extras for purely-internal tooling.
Pin a build backend explicitly. For a pure-Python package the uv build backend
or `hatchling` are both fine:
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```
Do not use bare `setuptools` + `setup.py` for new packages.
For monorepo members, use a uv workspace at the repo (or language-subtree) root:
```toml
[tool.uv.workspace]
members = ["packages/*", "apps/*"]
exclude = ["packages/internal-experimental"]
```
Every directory matched by `members` must contain its own `pyproject.toml`.
Members depend on each other via workspace sources, not PyPI:
```toml
[tool.uv.sources]
package-core = { workspace = true }
```
Workspace members share one lockfile and one virtual environment. Use
`uv run --package <name>` and `uv sync --package <name>` to target a member.
Do not use a workspace when members have genuinely conflicting requirements;
use separate projects with path dependencies instead. (Astral uv workspaces
docs.) See the member-discovery reference for the discovery algorithm a tool
must implement.
In a Moon-orchestrated monorepo, let Moon own task graph and caching; let uv own
resolution and the venv. Wire `uv sync`, `ruff`, the type checker, and `pytest`
as Moon tasks. Do not duplicate dependency declarations into Moon config; uv is
the single source of truth for what is installed.

## Python Version and Runtime
Target **3.13** as a safe production floor in 2026; **3.14** when the project
opts in. State the floor in `requires-python` and pin the exact interpreter for
the venv (uv reads `.python-version`).
Free-threading (no-GIL, PEP 703): officially supported but not the default
build as of 3.14 (PEP 779, Phase II, Oct 2025). Single-thread penalty is now
~5-10%. Do not adopt the free-threaded build for production by default; many
C-extension wheels still lack free-threaded support and the default-GIL switch
(Phase III) has no timeline, realistically 2028-2029. (peps.python.org/pep-0779;
py-free-threading.github.io.) Treat free-threading as opt-in, benchmarked, and
gated behind verified wheel availability.
The experimental JIT (3.13+) is off by default; do not rely on it for
correctness or assume its presence.
Do not write code for end-of-life interpreters (3.8 reached EOL; 3.9 is near
it). Do not add `from __future__ import annotations` reflexively on 3.13+;
add it only when you need deferred evaluation for forward references or to
break an import cycle.

## Modules and Files
Use private modules by default; the package's public API is what `__init__.py`
re-exports.
Name what is public with `__all__` in modules that are import targets. A code
indexer keys off `__all__`; a leading underscore marks intent as private.
Prefer explicit re-exports over `from .module import *`:
```python
from .errors import Error, ValidationError
from .store import Store, StoreConfig
__all__ = ["Error", "ValidationError", "Store", "StoreConfig"]
```
Avoid star imports anywhere. They defeat static analysis and the indexer.
Avoid import side effects at module top level (network, file IO, global state
mutation). Module import must be cheap and deterministic.
Split files when they become hard to scan. If no local limit exists, treat 700
lines as a hard stop. Break functions before they hide separate
responsibilities; treat 150 lines as a warning sign.
Prefer cohesive modules over one-class-per-file ceremony.
Keep relative imports intra-package and shallow (`from .submodule import X`).
Use absolute imports across package boundaries.

## Typing and API Design
Type all public functions, methods, and module-level constants. Annotate
parameters and return types; let inference handle obvious local variables.
Use **PEP 695** native type-parameter syntax on 3.13+ (no manual `TypeVar`):
```python
def first[T](items: list[T]) -> T | None: ...

class Cache[K, V]:
    def get(self, key: K) -> V | None: ...

type Json = dict[str, "Json"] | list["Json"] | str | int | float | bool | None
```
Use built-in generics (`list`, `dict`, `tuple`, `set`) and `X | None`, not
`typing.List`, `typing.Dict`, or `Optional[X]`. The capitalized aliases are
legacy. (docs.python.org/3/library/typing.)
Use `TypedDict` with `Required`/`NotRequired` for structured dicts with known
keys, and `Unpack[SomeTypedDict]` to type `**kwargs` precisely (PEP 692). Prefer
a dataclass or Pydantic model over a free-form dict when the shape is a real
domain type.
Use `Protocol` for structural interfaces; reach for `abc.ABC` only when you need
runtime enforcement or a shared base implementation. Do not introduce a Protocol
for a single implementation (see Anti-Patterns).
Use `@dataclass(frozen=True, slots=True)` for immutable value objects and
`enum.Enum` / `StrEnum` for closed sets. Use **Pydantic v2** at trust
boundaries (request/response bodies, config, external payloads); do not use it
for hot internal-only structures where a dataclass is enough.
Use newtypes (`NewType`) or thin wrapper classes when a primitive carries domain
meaning (an `UserId` is not any `str`).
Use concrete argument types first. Generalize to a Protocol or generic only when
a second caller needs it. Avoid `Any`-typed public surfaces.
Prefer keyword-only arguments (`*,`) for functions with several optional
parameters over a positional cascade.

## Error Handling
Define a small exception hierarchy rooted at one package base error:
```python
class PackageError(Exception): ...
class ValidationError(PackageError): ...
class NotFoundError(PackageError): ...
```
Catch narrowly. Never bare `except:`; avoid blanket `except Exception` except at
a top-level boundary that logs and re-raises or converts.
Chain causes with `raise NewError(...) from err` to preserve the traceback;
use `from None` only when deliberately hiding an irrelevant cause.
Add context at IO, process, network, and serialization boundaries. Do not erase
domain errors into bare strings too early; convert to user-facing diagnostics at
the CLI or API edge.
Use **exception groups** and `except*` (PEP 654, 3.11+) when handling
concurrent failures from `TaskGroup`/`anyio` task groups, where multiple tasks
can fail at once.
Let Pydantic raise `ValidationError`; inside validators raise `ValueError` or
`AssertionError` and let Pydantic aggregate. (docs.pydantic.dev.)
Do not use exceptions for normal control flow. Return `None` or a result value
for expected-absent cases; raise for genuinely exceptional conditions.

## Async
Default to **asyncio** with **structured concurrency**. Use `asyncio.TaskGroup`
(3.11+) over bare `asyncio.gather` / `create_task` for groups of tasks: it
tracks children, cancels siblings on failure, and surfaces an exception group.
Use **anyio** when you need backend portability (asyncio/Trio) or its richer
structured-concurrency and cancellation-scope primitives, and when integrating
libraries built on it. Prefer anyio APIs over raw asyncio where the project
already depends on anyio. (anyio.readthedocs.io.)
Do not mix blocking IO into the event loop. Push blocking calls to
`asyncio.to_thread` or an executor; do not call `time.sleep` or sync DB drivers
in async paths.
Make cancellation explicit. Respect `CancelledError`: never swallow it; let it
propagate after cleanup.
Do not create orphan tasks. Every spawned task belongs to a task group or has an
owner that awaits it.
Use timeouts at IO boundaries (`asyncio.timeout` / anyio cancel scopes).
Keep `asyncio` and sync code paths separate; do not write dual-colored helpers
that try to be both.

## Dependencies
Before adding a dependency, check:
- Is there already a local helper or a stdlib equivalent?
- Is the package maintained and typed (ships `py.typed`)?
- Does it pull a large transitive tree?
- Is the API stable enough for this project?
- Are alternatives clearly worse?
Sensible defaults unless the repo has chosen otherwise:
- HTTP: `httpx` (async + sync), `requests` only for legacy sync code.
- Data models / validation: `pydantic` v2.
- Settings: `pydantic-settings`.
- CLI: `typer` or `click`; `argparse` for zero-dependency tools.
- Web: `fastapi` (+ `uvicorn`) for services, `starlette` for thin ASGI.
- ORM / DB: `sqlalchemy` 2.x (typed), or `asyncpg` for raw async Postgres.
- Logging: `structlog`.
- Dates: stdlib `datetime` with `zoneinfo`; avoid `pytz`.
- Retry: `tenacity`.
- Test: `pytest`, `pytest-cov`, `hypothesis`, `anyio`/`pytest-asyncio`.
Prefer typed dependencies. Untyped dependencies force `Any` across your API.
Keep version constraints lower-bounded (`>=`), let `uv.lock` pin exact versions.
Avoid upper-bound caps unless a known incompatibility exists.

## Logging and Diagnostics
Use **structlog** for new application logging; configure it to wrap the stdlib
`logging` module so library logs flow through the same pipeline. (structlog docs;
Dash0; Last9.)
Emit structured key-value events, not formatted strings:
```python
log.info("session.started", session_id=sid, user_id=uid)
```
Render human-friendly console output in development and JSON in production for
log aggregators. Set log level to INFO or higher in production.
Bind request/trace context once (`structlog.contextvars`) rather than threading
it through every call.
Libraries should use a module-level `logging.getLogger(__name__)` and not
configure handlers or levels; the application owns configuration.
Never log secrets, tokens, or full request bodies. Keep machine-readable output
separate from human prose.
Never use `print` for diagnostics in library or service code.

## Lints and Formatting
Use **ruff** as the single linter and formatter. It replaces black, isort,
flake8, pyupgrade, pydocstyle, and dozens of plugins with one Rust binary,
10-100x faster. By 2026 it is the default. (github.com/astral-sh/ruff;
docs.astral.sh/ruff.)
Configure once in `pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "C4", "RUF", "ASYNC", "PTH"]
ignore = []

[tool.ruff.format]
docstring-code-format = true
```
Run `ruff format` (not black) and `ruff check --fix`. Do not keep black, isort,
or flake8 alongside ruff; remove them to avoid conflicting formatters.
For **type checking**, the field is genuinely in transition in 2026. Stable,
correct, plugin-capable: **mypy** or **pyright**. Pyright is the strongest
correctness-to-speed default (98% spec conformance, 2-5x faster than mypy, best
editor LSP). Astral's **ty** (Rust, beta as of 2026, 1.0 targeted for 2026) is
10-60x faster but passes fewer conformance tests (~15% as of early 2026) and has
no plugin system, so it cannot replace mypy for projects depending on Django,
SQLAlchemy, or Pydantic-v1 mypy plugins. (astral.sh/blog/ty; pydevtools;
sinon.github.io/future-python-type-checkers.)
Recommendation: use **pyright** (or mypy if the project already standardized on
it) as the gate today; track ty and adopt when it reaches 1.0 and conformance
parity. In a Rust-first Astral-tooled monorepo, evaluating ty early is
reasonable since it shares config ergonomics with ruff/uv, but keep pyright or
mypy as the CI gate until ty is stable.
Configure the chosen checker in strict mode:
```toml
[tool.mypy]
strict = true
python_version = "3.13"
```
ty reads `[tool.ty]` with per-rule severity under `[tool.ty.rules]` when adopted.
Run lint, format-check, and type-check in CI with failures hard.

## Type-Safety Escape Hatches
Avoid `Any`. It silently disables checking and propagates. Prefer `object` when
you truly mean "any object but I will narrow", and narrow with `isinstance`.
Use `typing.cast` only when you know more than the checker and cannot express it;
add a one-line comment saying why. A cast is a claim you are asserting, not a
fix.
Use `# type: ignore[code]` with the specific error code, never bare
`# type: ignore`. Treat an unexplained ignore as a review failure.
Prefer `typing.assert_never` in exhaustive matches so a new enum variant fails
type-checking instead of silently falling through.
Do not reach for `# noqa` to silence a lint you should fix; scope it to the rule
code and justify it.
Each escape hatch is a localized, documented exception, not a pattern.

## Testing
Use **pytest**. Use plain functions and `assert`; do not write `unittest.TestCase`
classes for new tests.
Use fixtures for setup/teardown and dependency injection; scope them
(`function`, `module`, `session`) deliberately. Put shared fixtures in
`conftest.py`. Prefer fixtures over module-level setup globals.
Parametrize with `@pytest.mark.parametrize` instead of copy-pasting cases.
For async tests, use **anyio**'s pytest plugin (or `pytest-asyncio`). With
anyio, define an `anyio_backend` fixture returning `"asyncio"` and mark tests
`@pytest.mark.anyio`; the backend fixture must be at the same or higher scope
than any async fixture depending on it. (anyio.readthedocs.io.)
Use **hypothesis** (property-based testing) for parsers, serializers,
encoders/decoders, and state machines where input coverage matters.
Test the public API through its real surface; avoid asserting on private
internals. Do not mock what you can construct cheaply. Mock only at true
external boundaries (network, clock, filesystem), and prefer fakes/fixtures over
deep `unittest.mock` patching.
Keep tests deterministic: freeze time, seed randomness, isolate the filesystem
with `tmp_path`. Serialize tests that share a global resource (a fixed port, a
singleton, a shared DB) rather than letting them flake under `pytest-xdist`.
Track coverage but do not chase 100%; cover behavior, not lines.

## Documentation
Write docstrings on public modules, classes, and functions. Pick one style
(Google or NumPy) and keep it consistent; ruff's `D` rules can enforce it.
Document the contract (what, args, returns, raises), not the implementation.
Keep README runnable examples in sync with the code; a broken example is a bug.
Do not write docstrings that restate the signature. Document private helpers
only where intent is non-obvious.
Type annotations are documentation; keep them accurate rather than duplicating
types in prose.

## Build and CI
The normal local proof should include:
```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run <pyright|mypy>
uv run pytest
```
If the repo uses Moon, `just`, `nox`, or `tox`, use the repo's commands. In a
Moon monorepo, express these as Moon tasks so caching and the task graph apply;
do not bypass the documented gate except to diagnose a failure.
Use `uv sync --frozen` in CI to fail on lockfile drift.
Use `pre-commit` (or `prek`) for fast local gates: ruff format, ruff check,
and a quick type-check on changed files. Keep the full type-check and test suite
in CI.
Pin the interpreter (`.python-version`) and the lockfile so CI and local match.
For monorepo CI, scope the fast inner-loop gate to changed members plus their
reverse-dependency closure (uv workspace graph / Moon affected), and keep one
unconditional full-workspace gate for merge and audits so correctness never
depends on the scoping heuristic.

## Performance
Prefer clarity first. Measure before optimizing; use `cProfile`,
`py-spy`, or `scalene` to find the real hot path before changing anything.
Reach for stdlib data structures and `collections`/`itertools` before
third-party. Use generators and `yield` to stream rather than materialize large
sequences.
For CPU-bound parallelism, use `ProcessPoolExecutor` (GIL build) and only
consider the free-threaded build after verifying wheel support and benchmarking.
For IO-bound concurrency, use asyncio task groups.
Cache pure functions with `functools.cache` / `lru_cache`; be careful with
unbounded caches on long-lived processes.
Do not micro-optimize cold paths. Do not drop to C extensions or Rust bindings
without a measured bottleneck; in this monorepo, a measured hot path is a
candidate to move to Rust rather than to obfuscate in Python.

## Metaprogramming
Use decorators for cross-cutting concerns (caching, retry, logging, timing).
Always `functools.wraps` the inner function to preserve name, docstring, and
signature.
Use descriptors and metaclasses sparingly; prefer `__init_subclass__`,
`__set_name__`, dataclasses, and Protocols, which cover most cases more legibly.
Prefer `match`/`case` (structural pattern matching) over a chain of `isinstance`
checks when dispatching on shape.
Use `contextlib` (`@contextmanager`, `ExitStack`, `suppress`) instead of
hand-rolled try/finally ladders.
Do not generate types or run heavy logic at import time via metaclasses when a
factory function or explicit registration is clearer.
Keep magic legible: a reader should be able to find where behavior comes from.

## Anti-Patterns
Avoid `from module import *` and implicit re-exports without `__all__`.
Avoid bare `except:` and blanket `except Exception` outside a top boundary.
Avoid `Any`-typed public APIs and unexplained `# type: ignore` / `# noqa`.
Avoid mutable default arguments (`def f(x=[])`); use `None` and assign inside.
Avoid module-level import side effects and expensive import-time work.
Avoid `requirements.txt` + `setup.py` + scattered tool configs; consolidate into
`pyproject.toml` + `uv.lock`.
Avoid a Protocol/ABC with a single implementation introduced "for testing".
Avoid `asyncio.gather` for fallible task groups; use `TaskGroup`/`anyio`.
Avoid blocking calls inside the event loop.
Avoid `print` for diagnostics; avoid string-formatted log messages.
Avoid `unittest.TestCase` for new tests; avoid deep `mock.patch` chains.
Avoid black/isort/flake8 alongside ruff (conflicting formatters).
Avoid keeping old and new implementations alive without an approved migration.
Avoid the free-threaded build in production without verified wheels and a
benchmark.
Avoid `os.path` string-juggling; use `pathlib.Path` (ruff `PTH`).

## Review Checklist
Before signing off, ask:
- Does this follow the local repo conventions?
- Did I search for an existing helper, type, or Protocol?
- Did I avoid duplicate implementations?
- Is the public API typed and intentional, with `__all__` where it matters?
- Are generics PEP 695 native and aliases modern (`list`, `X | None`)?
- Are exceptions narrow, chained with `from`, and grouped where concurrent?
- Are async tasks owned by a task group with timeouts and cancellation respected?
- Are dependencies typed, lower-bounded, and pinned in `uv.lock`?
- Are escape hatches (`Any`, `cast`, `type: ignore`, `noqa`) scoped and justified?
- Does it pass ruff format, ruff check, the type checker, and pytest?
- Are public surfaces documented without restating signatures?
- For monorepo members: dependencies via workspace sources, one lockfile,
  config in `pyproject.toml`, tasks wired into the repo's runner?
If any answer is no, fix it or state the reason explicitly.

## Sources
- uv workspaces — docs.astral.sh/uv/concepts/projects/workspaces/
- uv build backend — docs.astral.sh/uv/concepts/build-backend/
- uv adoption / monorepo (Airflow, pydevtools, Talk Python #540) — 2026
- ruff — github.com/astral-sh/ruff ; docs.astral.sh/ruff/
- ty (beta, 1.0 target 2026) — astral.sh/blog/ty ; docs.astral.sh/ty/ ;
  pydevtools.com/handbook/reference/ty/
- type-checker conformance comparison — sinon.github.io/future-python-type-checkers ;
  pydevtools "how do mypy, pyright and ty compare" ; danilchenko.dev
- free-threading — peps.python.org/pep-0779 ; py-free-threading.github.io ;
  docs.python.org/3/howto/free-threading-python.html ;
  docs.python.org/3/whatsnew/3.14.html
- typing — docs.python.org/3/library/typing ; peps.python.org/pep-0695 ;
  peps.python.org/pep-0692
- async — anyio.readthedocs.io ; docs.python.org asyncio.TaskGroup
- structlog — structlog.org/en/stable/logging-best-practices.html ;
  dash0.com python-logging-with-structlog ; last9.io
- pydantic v2 error handling — docs.pydantic.dev/latest/errors/errors/
- pytest async — anyio.readthedocs.io/en/stable/testing.html ; pypi pytest-asyncio
- DRY references (do not re-derive): python-workspace-monorepo-member-discovery-reference.md ;
  python-language-support-gap-analysis-fmm.md
