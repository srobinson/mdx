# D1-c Plan Signoff - Codex

Verdict: SIGN-OFF with 4 must-fixes.

Scope reviewed:

- Plan: `~/.mdx/projects/tm-t3code-d1c-scout.md`
- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`
- Base verified: `main` / `origin/main` / `HEAD` all at `daa198460f3902aad0bb6fff9c1c59a245f95737`
- Tree before findings write: clean on `main`

The plan's core read is correct: the gateway output directory is ignored and untracked, CI and release do not build it, and the current wheel path therefore ships no `transport_matters/gateway/` unless the workflow explicitly builds and stages it.

## Must-fixes

1. CI must publish the exact package-job wheel for `linux-wheel-spawn`.

   The proposed `linux-wheel-spawn` job depends on `package` and says to download the wheel that `package` built. Current `ci.yml` builds and checks `api/dist/transport_matters-*.whl`, then stops. There is no `actions/upload-artifact` step for `api/dist/*` in the `package` job.

   Required build input: add a package-job artifact upload after the wheel is built and content-checked, then make `linux-wheel-spawn` install that artifact. Do not rebuild the wheel in the spawn job. Rebuilding proves a different artifact and weakens the release-chain assertion.

   Evidence: `.github/workflows/ci.yml:365-391`, plan `~/.mdx/projects/tm-t3code-d1c-scout.md:202-204`.

2. Gateway staging cannot reuse the current frontend `index.html` loop.

   The plan says to add `gateway` to the `for bundle in www canvas` stage loop. That loop is browser bundle specific: it looks for `/tmp/$bundle-bundle/index.html` or `/tmp/$bundle-bundle/$bundle/index.html`, then asserts `api/src/transport_matters/$bundle/index.html`. A gateway artifact has `main.js`, `package.json`, and `prebuilds/**`, not `index.html`.

   Required build input: stage gateway through a separate branch or helper that copies the artifact layout as-is and asserts at least `main.js`, `package.json`, `prebuilds/linux-x64/`, and the existing POSIX prebuild invariant before `uv build`. Then use `assert_gateway_wheel.py` for the zip-level gate.

   Evidence: `.github/workflows/ci.yml:326-348`, `.github/workflows/release.yml:97-105`, plan `~/.mdx/projects/tm-t3code-d1c-scout.md:142-149`.

3. The `[node]` extra must update `api/uv.lock`.

   The plan's touch list names `api/pyproject.toml` but not the lockfile. CI and release use locked uv sync. Adding `[project.optional-dependencies] node = ["nodejs-wheel-binaries>=22"]` without updating `api/uv.lock` will fail locked dependency sync before the resolver tests run.

   Required build input: include the lockfile update in the slice and add the base-vs-extra guardrail against the locked wheel environment, not an unlocked ad hoc install.

   Evidence: `api/pyproject.toml:57-66`, `.github/workflows/ci.yml:29`, `.github/workflows/ci.yml:73`, `.github/workflows/ci.yml:362`, `.github/workflows/release.yml:114`, plan `~/.mdx/projects/tm-t3code-d1c-scout.md:241-245`.

4. The wheel spawn test must run inside the installed-wheel venv with its own test runner.

   The plan says the new job should create a clean venv, install the wheel, ensure node is on PATH, and run `pytest api/tests/integration/test_gateway_wheel_spawn.py`. A venv containing only the wheel does not have pytest. Running pytest from the repo also risks importing checkout code instead of the installed wheel unless the command is pinned carefully.

   Required build input: install `pytest` into the same smoke venv, run `/tmp/spawn/bin/python -m pytest` from a temp cwd outside the repo, and add a cheap assertion that `transport_matters.__file__` resolves under the smoke venv's site-packages. That keeps the proof about the wheel, not the source tree.

   Evidence: `.github/workflows/ci.yml:369-379`, `.github/workflows/release.yml:153-163`, plan `~/.mdx/projects/tm-t3code-d1c-scout.md:170-204`.

## Nice-to-fix

1. Update local build wording when `assert_gateway_wheel.py` becomes required.

   `api/justfile build` currently says to build the gateway first "if you want" it in the wheel, then invokes `assert_gateway_wheel.py`. Once absence hard-fails, that comment and any release header language that mentions only www/canvas should change so the local build contract matches CI.

   Evidence: `api/justfile:45-67`, `.github/workflows/release.yml:3-18`.

## Verification

Commands run:

- `git status --short --branch`
- `git rev-parse HEAD main origin/main`
- `git status --short --ignored api/src/transport_matters/gateway`
- `git ls-files api/src/transport_matters/gateway/main.js api/src/transport_matters/gateway/package.json api/src/transport_matters/gateway/prebuilds/linux-x64/pty.node`
- `git check-ignore -v api/src/transport_matters/gateway/main.js api/src/transport_matters/gateway/prebuilds/linux-x64/pty.node`
- `git ls-tree -r --name-only HEAD api/src/transport_matters/gateway/main.js api/src/transport_matters/gateway/package.json api/src/transport_matters/gateway/prebuilds/linux-x64/pty.node`
- Targeted line reads of `ci.yml`, `release.yml`, `api/pyproject.toml`, `api/uv.lock`, `assert_gateway_wheel.py`, `gateway_supervisor.py`, `test_gateway_supervisor.py`, `test_backend_launch_smoke.py`, and `api/justfile`

No code changes were made.
