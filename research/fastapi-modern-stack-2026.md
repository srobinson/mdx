---
title: Modern FastAPI Production Stack (2025-2026)
type: research
tags: [python, fastapi, uv, ruff, docker, github-actions, sqlalchemy, testing, ci-cd]
summary: Comprehensive survey of the modern FastAPI production stack including uv, ruff, ty, project structure, CI/CD, Docker, testing, database patterns, and versioning.
status: active
source: deep-research
confidence: high
created: 2026-04-10
updated: 2026-04-10
---

# Modern FastAPI Production Stack (2025-2026)

## Executive Summary

The modern Python FastAPI production stack has converged around a clear set of tools as of early 2026. **uv** (v0.11.6, Astral) is the default package/project manager, replacing pip/poetry/pipenv. **Ruff** (v0.15.x, Astral) is the unified linter and formatter, replacing flake8/black/isort. **ty** (beta, Astral) is the emerging type checker, though mypy and pyright remain production-stable. The official FastAPI full-stack template now uses uv, SQLModel, and GitHub Actions. Domain-based project structure (not file-type) is the consensus recommendation for anything beyond a microservice.

---

## 1. uv -- The Rust-Based Python Package/Project Manager

### Current State
- **Version**: 0.11.6 (April 9, 2026)
- **Maintainer**: Astral (same team as Ruff and ty)
- **Performance**: 10-100x faster than pip for dependency resolution and installation
- **Status**: De facto standard for new Python projects in 2026

### What uv Replaces
| Legacy Tool | uv Equivalent |
|------------|---------------|
| `pip install` | `uv add` / `uv pip install` |
| `pip freeze` | `uv lock` |
| `python -m venv` | `uv venv` |
| `poetry init` | `uv init` |
| `poetry add` | `uv add` |
| `poetry lock` | `uv lock` |
| `poetry run` | `uv run` |
| `pyenv install` | `uv python install` |

### Key Commands

```bash
# Initialize a new project (application layout)
uv init --app

# Initialize a new library
uv init --lib

# Add dependencies
uv add fastapi --extra standard
uv add sqlalchemy alembic pydantic-settings

# Add dev dependencies
uv add --dev pytest pytest-asyncio httpx ruff mypy

# Sync environment from lockfile
uv sync --locked --all-extras --dev

# Run commands in the managed environment
uv run fastapi dev
uv run pytest tests/
uv run ruff check src/

# Lock dependencies (regenerate uv.lock)
uv lock

# Upgrade specific package
uv lock --upgrade-package fastapi

# Install a specific Python version
uv python install 3.13

# Bump project version
uv version --bump patch   # or minor, major
```

### pyproject.toml Convention

```toml
[project]
name = "my-fastapi-app"
version = "0.1.0"
description = "Production FastAPI application"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "sqlalchemy[asyncio]>=2.0",
    "alembic>=1.14",
    "pydantic-settings>=2.6",
    "asyncpg>=0.30",
    "httpx>=0.28",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=1.0",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "ruff>=0.15",
    "mypy>=1.14",
    "pre-commit>=4.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Workspace Support

uv workspaces allow monorepo management with a shared lockfile, inspired by Cargo and npm workspaces.

```toml
# Root pyproject.toml
[tool.uv.workspace]
members = ["packages/*", "services/*"]
exclude = ["packages/deprecated-pkg"]
```

Each workspace member has its own `pyproject.toml` but shares a single `uv.lock` and virtual environment. `uv lock` operates on the entire workspace; `uv run --package <name>` targets a specific member.

### Community Consensus
- uv is the default recommendation for new projects in 2026 (HN, dev blogs, official FastAPI template)
- Poetry remains viable for existing projects that need its maturity, but migration to uv is a common trajectory
- The "Poetry vs uv" debate is largely settled in uv's favor for new work

**Sources**: [uv docs](https://docs.astral.sh/uv/), [uv FastAPI guide](https://docs.astral.sh/uv/guides/integration/fastapi/), [uv GitHub releases](https://github.com/astral-sh/uv/releases), [Astral blog](https://astral.sh/blog/uv-unified-python-packaging)

---

## 2. Linting and Formatting with Ruff

### Current State
- **Version**: 0.15.x (latest 0.15.10, April 2026)
- **Performance**: 10-100x faster than flake8/black/isort combined
- **Rule coverage**: 900+ lint rules from 70+ flake8 plugins

### What Ruff Replaces
flake8, isort, black, pyupgrade, autoflake, pydocstyle, bandit (partial), and dozens of flake8 plugins. Single binary, single config.

### Recommended pyproject.toml Configuration

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = [
    "E",     # pycodestyle errors
    "W",     # pycodestyle warnings
    "F",     # pyflakes
    "I",     # isort
    "UP",    # pyupgrade
    "B",     # flake8-bugbear
    "SIM",   # flake8-simplify
    "C4",    # flake8-comprehensions
    "RET",   # flake8-return
    "PTH",   # flake8-use-pathlib
    "TCH",   # flake8-type-checking
]
ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
```

**Note on rule selection**: Ruff docs recommend starting with `select = ["E", "F"]` and adding categories incrementally. The set above (E, W, F, I, UP, B, SIM) is the community-consensus "good default" for production projects.

### Pre-commit Integration

`.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.10
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
```

Install via uv:
```bash
uv tool install pre-commit --with pre-commit-uv --force-reinstall
uv run pre-commit install
```

The `sync-with-uv` library (pydevtools.com) can auto-sync tool versions between `uv.lock` and `.pre-commit-config.yaml` to prevent version drift.

**Sources**: [Ruff docs](https://docs.astral.sh/ruff/configuration/), [ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit), [pydevtools recommended defaults](https://pydevtools.com/handbook/how-to/how-to-configure-recommended-ruff-defaults/)

---

## 3. Directory Structure

### Consensus: Domain-Based (Module-Functionality) Layout

The community consensus, anchored by the zhanymkanov/fastapi-best-practices repo (inspired by Netflix Dispatch), is to organize by business domain rather than file type. This is the recommended approach for anything beyond a single-endpoint microservice.

```
my-fastapi-app/
├── pyproject.toml
├── uv.lock
├── .pre-commit-config.yaml
├── .env.example
├── .dockerignore
├── Dockerfile
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # Application factory + lifespan
│       ├── config.py            # Global pydantic-settings
│       ├── database.py          # Engine, session factory
│       ├── dependencies.py      # Shared dependencies
│       ├── exceptions.py        # Global exception handlers
│       ├── middleware.py         # CORS, logging, etc.
│       ├── api/
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       └── router.py    # Aggregates all domain routers
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── router.py        # Auth endpoints
│       │   ├── schemas.py       # Pydantic request/response models
│       │   ├── models.py        # SQLAlchemy ORM models
│       │   ├── service.py       # Business logic
│       │   ├── dependencies.py  # Auth-specific deps
│       │   ├── exceptions.py    # AuthError, InvalidToken, etc.
│       │   └── constants.py
│       ├── users/
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── schemas.py
│       │   ├── models.py
│       │   ├── service.py
│       │   └── repository.py    # Data access layer
│       └── items/
│           ├── ...
└── tests/
    ├── conftest.py              # Shared fixtures
    ├── auth/
    │   ├── test_router.py
    │   └── test_service.py
    ├── users/
    │   └── ...
    └── items/
        └── ...
```

### Key Structural Decisions

**src layout vs flat layout**: The `src/` layout is preferred for applications (prevents accidental imports of uninstalled code). Flat layout is acceptable for small projects or libraries.

**Router aggregation**: Each domain has its own `router.py`. A top-level `api/v1/router.py` aggregates them:

```python
from fastapi import APIRouter
from app.auth.router import router as auth_router
from app.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
```

**Explicit cross-module imports**: When importing from sibling domains, use explicit module names to avoid ambiguity:
```python
from app.auth import constants as auth_constants
```

### Settings/Config Management with pydantic-settings

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_name: str = "My FastAPI App"
    debug: bool = False

    # Database
    database_url: str
    database_echo: bool = False

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 30

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

The `@lru_cache` decorator ensures the `.env` file is read only once. Use FastAPI's `Depends(get_settings)` to inject settings into routes.

**Decoupled settings**: For larger projects, split into `DatabaseSettings`, `AuthSettings`, etc., each with their own `env_prefix`:

```python
class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_")
    url: str
    echo: bool = False
    pool_size: int = 5
```

**Sources**: [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices), [FastAPI docs - bigger applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/), [FastAPI settings docs](https://fastapi.tiangolo.com/advanced/settings/), [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

## 4. GitHub Actions CI/CD

### Standard Workflow Pattern

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --all-extras --dev

      - name: Ruff check
        run: uv run ruff check src/

      - name: Ruff format check
        run: uv run ruff format --check src/

      - name: Type check
        run: uv run mypy src/

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v6

      - name: Install uv
        uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --locked --all-extras --dev

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test_db
        run: uv run pytest tests/ --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v5
        with:
          file: ./coverage.xml

  docker:
    needs: [lint, test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v6

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

### uv Caching in CI

The `astral-sh/setup-uv@v7` action has built-in caching:

```yaml
- uses: astral-sh/setup-uv@v7
  with:
    enable-cache: true
    # Cache key defaults to hashing uv.lock
```

For manual caching (more control):

```yaml
env:
  UV_CACHE_DIR: /tmp/.uv-cache
steps:
  - uses: actions/cache@v5
    with:
      path: /tmp/.uv-cache
      key: uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
      restore-keys: |
        uv-${{ runner.os }}-${{ hashFiles('uv.lock') }}
        uv-${{ runner.os }}
  # ... run steps ...
  - name: Minimize uv cache
    if: always()
    run: uv cache prune --ci
```

### Python Version Matrix

```yaml
strategy:
  matrix:
    python-version: ["3.12", "3.13"]
steps:
  - uses: astral-sh/setup-uv@v7
    with:
      python-version: ${{ matrix.python-version }}
```

**Sources**: [uv GitHub Actions guide](https://docs.astral.sh/uv/guides/integration/github/), [Thomas Bury - CI/CD with uv](https://dev.to/thomas_bury_b1a50c1156cbf/mastering-python-project-management-with-uv-part-4-cicd-docker-385e)

---

## 5. Version and Release Management

### Approach 1: Manual with `uv version` + git-cliff

The simplest approach uses uv's built-in versioning and git-cliff for changelog generation.

**pyproject.toml**:
```toml
[project]
name = "my-app"
version = "1.2.0"
```

**Version reading at runtime**:
```python
# app/__init__.py
from importlib.metadata import version
__version__ = version("my-app")
```

**Bump and release**:
```bash
uv version --bump patch   # updates pyproject.toml
git-cliff --output CHANGELOG.md
git add pyproject.toml CHANGELOG.md uv.lock
git commit -m "chore: release v$(uv version)"
git tag "v$(uv version)"
git push --follow-tags
```

### Approach 2: python-semantic-release (Automated)

Fully automated versioning from conventional commits.

**pyproject.toml**:
```toml
[tool.semantic_release]
version_toml = ["pyproject.toml:project.version"]
branch = "main"
build_command = """
    uv lock --upgrade-package my-app
    git add uv.lock
    uv build
"""
commit_message = "chore(release): v{version}"

[tool.semantic_release.changelog]
changelog_file = "CHANGELOG.md"

[tool.semantic_release.publish]
upload_to_pypi = false
```

**GitHub Actions release workflow**:
```yaml
name: Release

on:
  push:
    branches: [main]

permissions:
  contents: write
  id-token: write

jobs:
  release:
    runs-on: ubuntu-latest
    concurrency: release

    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v7

      - name: Semantic Release
        id: release
        uses: python-semantic-release/python-semantic-release@v9
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

### Approach 3: Commitizen

Integrated commit validation + version bump + changelog.

```toml
[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"
version_files = ["pyproject.toml:project.version"]
update_changelog_on_bump = true
tag_format = "v$version"
```

### Tool Comparison

| Feature | git-cliff | python-semantic-release | commitizen |
|---------|-----------|------------------------|------------|
| Language | Rust | Python | Python |
| Changelog | Primary purpose | Built-in | Built-in |
| Version bump | No (use uv) | Yes | Yes |
| Commit validation | No | No | Yes (cz commit) |
| GitHub Release | No | Yes | Via CI |
| Conventional Commits | Required | Required | Required + enforced |

**Community take**: git-cliff for changelog only (fast, flexible). python-semantic-release for full automation. commitizen when you also want to enforce commit message format at development time.

**Sources**: [git-cliff](https://github.com/orhun/git-cliff), [python-semantic-release docs](https://python-semantic-release.readthedocs.io/), [commitizen docs](https://commitizen-tools.github.io/commitizen/), [pydevtools dynamic versioning](https://pydevtools.com/handbook/how-to/how-to-add-dynamic-versioning-to-uv-projects/)

---

## 6. Quickstart Templates

### Tier 1: Official / High Authority

**fastapi/full-stack-fastapi-template** (Official)
- GitHub: https://github.com/fastapi/full-stack-fastapi-template
- Stack: FastAPI + React + SQLModel + PostgreSQL + Docker + GitHub Actions + uv
- Maintained by tiangolo (FastAPI creator)
- Uses uv since late 2024 (announced on X by @tiangolo)
- Includes: JWT auth, email verification, Alembic migrations, Docker Compose, Traefik
- The canonical reference for "how does tiangolo do it"

**zhanymkanov/fastapi-best-practices** (Community Reference)
- GitHub: https://github.com/zhanymkanov/fastapi-best-practices
- Not a template per se but the most-referenced guide for FastAPI conventions
- Domain-based structure, dependency injection patterns, async best practices
- Actively maintained (last update August 2025)

### Tier 2: Modern uv-First Templates

**barabum0/fastapi-template-uv**
- GitHub: https://github.com/barabum0/fastapi-template-uv
- Stack: FastAPI + uv + mypy + ruff + loguru + pytest
- Focused, minimal, good for API-only projects

**a5chin/python-uv**
- GitHub: https://github.com/a5chin/python-uv
- Production-ready Python template: uv + Ruff + ty + VSCode Dev Containers
- General-purpose (not FastAPI-specific) but easily extended

**heshinth/fastapi-uv-template** (Copier)
- GitHub: https://github.com/heshinth/fastapi-uv-template
- Uses Copier for project generation (preferred over cookiecutter in 2025)
- FastAPI + uv

**osprey-oss/cookiecutter-uv**
- GitHub: https://github.com/fpgmaas/cookiecutter-uv
- General Python with uv + ruff + mypy + deptry
- Not FastAPI-specific but good foundation

**elefher/fastapi-uv-workspaces-template**
- GitHub: https://github.com/elefher/fastapi-uv-workspaces-template
- FastAPI + GraphQL + uv workspaces
- Monorepo-oriented

### Template Selection Guidance

| Need | Template |
|------|----------|
| Full-stack (API + frontend) | full-stack-fastapi-template |
| API-only, minimal | barabum0/fastapi-template-uv |
| API-only, Copier-based | heshinth/fastapi-uv-template |
| Monorepo / workspaces | elefher/fastapi-uv-workspaces-template |
| Learning best practices | zhanymkanov/fastapi-best-practices |

**Sources**: [FastAPI project generation docs](https://fastapi.tiangolo.com/project-generation/), [@tiangolo announcement](https://x.com/tiangolo/status/1839659645142442211), template repos linked above

---

## 7. Testing

### Core Stack

| Package | Purpose |
|---------|---------|
| pytest | Test runner |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage reporting |
| httpx | Async HTTP client for API tests |
| factory-boy | Test data factories |
| faker | Realistic fake data |

### pytest Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"

[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/migrations/*"]

[tool.coverage.report]
show_missing = true
fail_under = 80
```

### Async Test Client Fixture

```python
# tests/conftest.py
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.main import create_app
from app.database import get_db
from app.config import get_settings

@pytest.fixture
async def app():
    """Create application for testing."""
    app = create_app()
    yield app

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///test.db",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.fixture
async def client(app, db_session):
    """Create an async test client with DB override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
```

### Test Example

```python
# tests/users/test_router.py
import pytest

async def test_create_user(client):
    response = await client.post(
        "/api/v1/users/",
        json={"email": "test@example.com", "password": "secure123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "id" in data

async def test_create_user_duplicate_email(client, db_session):
    # Create first user
    await client.post(
        "/api/v1/users/",
        json={"email": "dupe@example.com", "password": "secure123"},
    )
    # Attempt duplicate
    response = await client.post(
        "/api/v1/users/",
        json={"email": "dupe@example.com", "password": "other456"},
    )
    assert response.status_code == 409
```

### Factory Pattern

```python
# tests/factories.py
import factory
from app.users.models import User

class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Faker("email")
    hashed_password = factory.LazyFunction(lambda: hash_password("testpass"))
    is_active = True
```

### Key Practices
- Use `asyncio_mode = "auto"` to avoid `@pytest.mark.asyncio` decorators everywhere
- Override dependencies with `app.dependency_overrides` rather than mocking
- Use SQLite in-memory for fast unit tests; real PostgreSQL in CI integration tests
- pytest-asyncio 1.0 (May 2025) simplified the API significantly
- `httpx.AsyncClient` is strongly preferred over the sync `TestClient` for async routes
- Always clear `dependency_overrides` in fixture teardown

**Sources**: [FastAPI async tests docs](https://fastapi.tiangolo.com/advanced/async-tests/), [TestDriven.io FastAPI testing](https://testdriven.io/blog/fastapi-crud/), [pytest-asyncio 1.0 changes](https://thinhdanggroup.github.io/pytest-asyncio-v1-migrate/)

---

## 8. Type Checking

### Current Landscape (April 2026)

| Tool | Language | Speed vs mypy | Status |
|------|----------|--------------|--------|
| mypy | Python | 1x (baseline) | Stable, mature |
| pyright | TypeScript | 3-5x faster | Stable, powers Pylance |
| basedpyright | TypeScript | ~pyright | Stricter pyright fork |
| ty (Astral) | Rust | 10-60x faster | Beta (Dec 2025) |

### Practical Recommendation

**For production today**: mypy in CI, pyright/Pylance in IDE. This gives you fast editor feedback and thorough CI validation.

**Emerging**: ty (from Astral, same team as uv/ruff) is the likely successor. 10-60x faster than mypy without caching, 80-500x faster with incremental analysis. Full language server with completions, navigation, and code actions. Integration with ruff and uv is planned.

### mypy Configuration

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
exclude = [
    "alembic/",
    ".venv/",
]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

# SQLAlchemy plugin for model type checking
plugins = ["sqlalchemy.ext.mypy.plugin"]
```

### pyright Configuration

```toml
# pyproject.toml
[tool.pyright]
pythonVersion = "3.12"
typeCheckingMode = "basic"  # or "standard" / "strict"
reportMissingImports = true
reportMissingTypeStubs = false
venvPath = "."
venv = ".venv"
```

**Sources**: [ty announcement](https://astral.sh/blog/ty), [mypy vs pyright comparison](https://pydevtools.com/handbook/explanation/how-do-mypy-pyright-and-ty-compare/), [Python type checker conformance](https://sinon.github.io/future-python-type-checkers/)

---

## 9. Docker

### Production Dockerfile (Multi-Stage, uv-Based)

```dockerfile
# ---- Builder Stage ----
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.6 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install dependencies first (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Copy application code and install project
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---- Runtime Stage ----
FROM python:3.13-slim

RUN groupadd -r app && useradd -r -d /app -g app app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH"

USER app
WORKDIR /app

COPY --chown=app:app ./src /app/src
COPY --chown=app:app ./alembic.ini /app/
COPY --chown=app:app ./alembic /app/alembic

EXPOSE 8000

CMD ["fastapi", "run", "src/app/main.py", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### Key Environment Variables

| Variable | Value | Purpose |
|----------|-------|---------|
| `UV_COMPILE_BYTECODE=1` | Pre-compile `.pyc` files | Faster container startup |
| `UV_LINK_MODE=copy` | Copy instead of hardlink | Avoids filesystem issues in Docker |
| `UV_PYTHON_DOWNLOADS=never` | Prevent Python download | Use base image Python |
| `UV_NO_DEV=1` | Skip dev deps | Smaller production image |

### Layer Caching Strategy

The critical insight: separate dependency installation from application installation.

1. Copy `pyproject.toml` + `uv.lock` via bind mounts
2. `uv sync --no-install-project` (dependencies only)
3. Copy application source code
4. `uv sync` (installs the project itself)

Changing application code only invalidates step 3+4. Dependency layers remain cached.

### .dockerignore

```
.venv/
.git/
.env
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
```

### Official uv Docker Image

Astral provides ready-made images at `ghcr.io/astral-sh/uv`:
- Distroless: `ghcr.io/astral-sh/uv:0.11.6` (just the binary)
- Python-based: `ghcr.io/astral-sh/uv:python3.13-slim` (full environment)
- Alpine: `ghcr.io/astral-sh/uv:python3.13-alpine`

For production FastAPI apps, the two-stage pattern (COPY --from distroless) is preferred over using the full uv base image.

### Docker Compose for Development

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - .:/app
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/app
    depends_on:
      db:
        condition: service_healthy
    develop:
      watch:
        - action: sync
          path: ./src
          target: /app/src
          ignore:
            - .venv/
        - action: rebuild
          path: pyproject.toml

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: app
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  pgdata:
```

**Sources**: [Hynek Schlawack - Production Docker with uv](https://hynek.me/articles/docker-uv/), [uv Docker guide](https://docs.astral.sh/uv/guides/integration/docker/), [Official FastAPI template Dockerfile](https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/Dockerfile)

---

## 10. Database / ORM

### SQLAlchemy 2.0 Async (Recommended for Complex Projects)

The community consensus for 2025-2026 is **SQLAlchemy 2.0 async** for production projects that need full control. SQLModel is recommended for simpler projects or when you want maximum FastAPI ergonomics.

**Engine and session setup**:

```python
# app/database.py
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.database_echo,
    pool_size=5,
    max_overflow=10,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**Model definition (SQLAlchemy 2.0 Mapped style)**:

```python
# app/users/models.py
from sqlalchemy import String, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
```

**Repository pattern**:

```python
# app/users/repository.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.users.models import User

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user
```

### SQLModel (Recommended for Simpler Projects)

SQLModel unifies SQLAlchemy model and Pydantic schema into a single class. Used by the official FastAPI full-stack template.

```python
from sqlmodel import SQLModel, Field

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True, max_length=255)
    is_active: bool = True

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

class UserCreate(UserBase):
    password: str

class UserPublic(UserBase):
    id: int
```

### SQLModel vs SQLAlchemy 2.0: Decision Matrix

| Factor | SQLModel | SQLAlchemy 2.0 |
|--------|----------|----------------|
| Boilerplate | Less (unified model/schema) | More (separate model + schema) |
| FastAPI integration | Native (same creator) | Requires manual schema mapping |
| Complex queries | Limited (drop to SA) | Full control |
| Maturity | Younger, smaller ecosystem | Battle-tested, extensive docs |
| Async support | Via SQLAlchemy engine | Native |
| Community size | Growing | Very large |
| Official recommendation | FastAPI full-stack template | Production-heavy teams |

### Alembic Migrations

**Initialize with async template**:
```bash
uv run alembic init -t async alembic
```

**Configure `alembic/env.py`** to import your models and use your settings:

```python
from app.database import engine
from app.users.models import Base  # Import all models

target_metadata = Base.metadata
```

**Naming conventions** (set in Base for consistent migration output):

```python
from sqlalchemy import MetaData

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)
```

**Key practice**: Alembic migrations run best with a sync engine, even if your application is async. The `async` template wraps sync operations in `connection.run_sync()`.

**Sources**: [SQLAlchemy 2.0 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [SQLModel docs](https://sqlmodel.tiangolo.com/), [TestDriven.io FastAPI + SQLModel](https://testdriven.io/blog/fastapi-sqlmodel/), [FastAPI/SQLModel discussion #9936](https://github.com/fastapi/fastapi/discussions/9936)

---

## Complete Reference pyproject.toml

Combining all sections into a single reference configuration:

```toml
[project]
name = "my-fastapi-app"
version = "0.1.0"
description = "Production FastAPI application"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.6",
    "httpx>=0.28",
    "pyjwt>=2.9",
    "pwdlib[argon2]>=0.2",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=1.0",
    "pytest-cov>=6.0",
    "httpx>=0.28",
    "aiosqlite>=0.20",
    "ruff>=0.15",
    "mypy>=1.14",
    "pre-commit>=4.0",
    "factory-boy>=3.3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

# ---- Ruff ----
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "W", "F", "I", "UP", "B", "SIM", "C4", "RET", "PTH", "TCH"]
ignore = ["E501"]

[tool.ruff.lint.isort]
known-first-party = ["app"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

# ---- mypy ----
[tool.mypy]
python_version = "3.12"
strict = true
exclude = ["alembic/", ".venv/"]
plugins = ["sqlalchemy.ext.mypy.plugin"]

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

# ---- pytest ----
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "-v --tb=short"

# ---- coverage ----
[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/alembic/*"]

[tool.coverage.report]
show_missing = true
fail_under = 80
```

---

## Sources Consulted

### Official Documentation
- [uv docs](https://docs.astral.sh/uv/) (FastAPI guide, Docker guide, GitHub Actions guide)
- [Ruff docs](https://docs.astral.sh/ruff/) (configuration, linter, formatter)
- [ty announcement](https://astral.sh/blog/ty)
- [FastAPI docs](https://fastapi.tiangolo.com/) (project structure, settings, async tests, Docker)
- [pydantic-settings docs](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [SQLAlchemy 2.0 async docs](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [SQLModel docs](https://sqlmodel.tiangolo.com/)
- [python-semantic-release docs](https://python-semantic-release.readthedocs.io/)

### GitHub Repositories
- [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template) (official template)
- [zhanymkanov/fastapi-best-practices](https://github.com/zhanymkanov/fastapi-best-practices)
- [barabum0/fastapi-template-uv](https://github.com/barabum0/fastapi-template-uv)
- [a5chin/python-uv](https://github.com/a5chin/python-uv)
- [heshinth/fastapi-uv-template](https://github.com/heshinth/fastapi-uv-template)
- [astral-sh/ruff-pre-commit](https://github.com/astral-sh/ruff-pre-commit)
- [orhun/git-cliff](https://github.com/orhun/git-cliff)

### Engineering Blogs
- [Hynek Schlawack - Production Docker with uv](https://hynek.me/articles/docker-uv/)
- [pydevtools.com](https://pydevtools.com/) (ruff defaults, uv lockfiles, dynamic versioning, type checker comparison)
- [TestDriven.io - FastAPI + SQLModel](https://testdriven.io/blog/fastapi-sqlmodel/)
- [slhck.info - Dynamic Versioning](https://slhck.info/software/2025/10/01/dynamic-versioning-uv-projects.html)

### Hacker News Discussions
- [Django vs FastAPI in 2025](https://news.ycombinator.com/item?id=43557087) - practical framework selection discussion
- [Real-time FastAPI + UV starter (Show HN)](https://news.ycombinator.com/item?id=45463893)
- [uv package manager discussion](https://news.ycombinator.com/item?id=44357411)

### X/Twitter
- [@tiangolo announcing uv adoption in official template](https://x.com/tiangolo/status/1839659645142442211)

### Community Articles
- [Thomas Bury - CI/CD with uv](https://dev.to/thomas_bury_b1a50c1156cbf/mastering-python-project-management-with-uv-part-4-cicd-docker-385e)
- [Medium: Poetry vs UV comparison](https://medium.com/@hitorunajp/poetry-vs-uv-which-python-package-manager-should-you-use-in-2025-4212cb5e0a14)
- [Medium: python-semantic-release + uv monorepo](https://medium.com/@asafshakarzy/releasing-a-monorepo-using-uv-workspace-and-python-semantic-release-0dafc889f4cc)

---

## Source Quality Assessment

**High confidence**: uv commands, Ruff configuration, Docker patterns, project structure conventions. These are well-documented in official sources and corroborated across multiple independent practitioners.

**Medium confidence**: Type checker recommendations (the ty landscape is evolving rapidly). SQLModel vs SQLAlchemy community consensus (opinions vary by project complexity). Version management tooling comparisons (the ecosystem is still consolidating).

**Low signal areas**: Reddit and X had minimal useful content specific to this stack combination. The Python community discussion has fragmented across GitHub issues, dev.to, Medium, and Discord (inaccessible). HackerNews had a few useful threads but mostly at the framework-choice level rather than tooling details.

---

## Open Questions

1. **ty adoption timeline**: When does ty reach stable and become the default recommendation over mypy? Astral says "2026" but no specific date.
2. **SQLModel 2.0**: Will SQLModel fully adopt SQLAlchemy 2.0 patterns? The official template uses it but community complaints about lagging behind SA/Pydantic versions persist.
3. **uv 1.0**: uv is still pre-1.0 (0.11.x). When does it hit stable? The versioning policy says pre-1.0 can have breaking changes.
4. **Astral + OpenAI**: Astral has entered into an agreement to join OpenAI. Impact on uv/ruff/ty maintenance is unclear.
