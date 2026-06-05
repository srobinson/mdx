---
title: Plan — t3code P1 Slice D1-c, Linux wheel verification + optional transport-matters[node] extra
type: projects
tags: [transport-matters, t3code, p1, slice-d1c, scout, plan, gateway, node-pty, wheel, ci, nodejs-wheel, linux]
summary: >
  Build plan for D1-c on main @ daa1984 (closes POSIX P1). LOAD-BEARING FINDING that reshapes part (a):
  neither ci.yml nor release.yml ever runs `pnpm --filter @tm/gateway build` or `assert_gateway_wheel.py`,
  and assert_gateway_wheel soft-skips an absent bundle — so the CI-packaged wheel AND the released PyPI
  wheel currently ship WITHOUT transport_matters/gateway/, meaning the D1-b packaged launch silently
  degrades to the D2 stub (canvas runs 503) in every pip install. So D1-c(a) is not just a verification
  recipe: it must first close the D1-a→CI/release embedding gap (build @tm/gateway, embed like www/canvas,
  flip assert_gateway_wheel from soft-skip to hard-fail), THEN add a runtime PTY-spawn assertion.
  Recommendation: NATIVE ci.yml as primary (runners are already ubuntu → continuous cross-platform
  coverage, zero docker) + a thin `just verify-linux` docker recipe that reuses the SAME pytest for mac
  local repro. Cheapest runtime proof = boot the wheel's packaged gateway alone under system node in stub
  mode with a fake `claude` on PATH, POST /runs, assert RUN_STARTED→EXITED; exercises the identical
  NodePtyAdapter → prebuilds/linux-x64/pty.node loader a real run uses, no postgres/Python/real-harness.
  Part (b): add `[project.optional-dependencies] node = [nodejs-wheel-binaries]`; a new resolve_node_binary
  (sibling to resolve_gateway_entry) probes the extra's bundled node BEFORE PATH; desktop execPath path
  unchanged; doctor reuses the same resolver. Node path verified first-hand from the real wheel.
status: active
source: scout (fable 5:2.2), first-hand on main @ daa1984
confidence: high
created: 2026-07-08
---

# Plan — Slice D1-c: prove the POSIX wheel spawns, and let it bundle its own node

Scope per brief: (a) a Linux verification recipe proving the wheel's node-pty prebuilds spawn a captured
run on linux-x64, with a CI-vs-docker recommendation; (b) an OPTIONAL `transport-matters[node]` extra that
bundles node so web mode no longer needs system node on PATH. This slice closes POSIX P1.

---

## 0. Recovered current state (main @ daa1984)

### The packaged gateway launch (D1-a + D1-b, already shipped)

- **The bundle** is built by `packages/gateway/scripts/build.mjs`: esbuild bundles `main.ts` → `main.js`
  (ESM, `format: "esm"`), inlining node-pty's JS but keeping `*.node` **external**, then copies node-pty's
  `prebuilds/{darwin-arm64,darwin-x64,linux-arm64,linux-x64}` next to `main.js` into
  `api/src/transport_matters/gateway/`. The load-bearing invariant, stated in the build header: node-pty's
  loader resolves `./prebuilds/{platform}-{arch}/pty.node` **relative to the caller**, so `prebuilds/` must
  sit beside `main.js`. `spawn-helper` is darwin-only (Linux spawns through `pty.node` directly), exec bit
  set explicitly and verified.
- **The wheel embed** is declared in `api/pyproject.toml` `[tool.hatch.build.targets.wheel].artifacts`
  (`src/transport_matters/gateway/**`). hatch ships whatever is on disk under that glob.
- **The packaging gate** is `api/scripts/assert_gateway_wheel.py::check_wheel`: soft-skips when the wheel
  carries no `gateway/` at all (prints `! gateway/ bundle NOT in wheel`, returns no errors), hard-fails on
  an *incomplete* bundle (missing `main.js`, missing a POSIX prebuild dir, any win32 prebuild present, a
  darwin `spawn-helper` without its exec bit). `REQUIRED_PREBUILDS` already lists both linux arches.
- **The Python supervisor** (`api/src/transport_matters/gateway_supervisor.py`):
  - `resolve_gateway_entry(env)` — env override → `packaged_gateway_entry()` (`__file__/gateway/main.js`)
    → workspace `main.ts`. This is the JS-entry resolver.
  - `plan_gateway_supervision(settings, *, env, which)` — the sibling **node-interpreter** resolution
    lives here as a bare `node = which("node")` (line under "Node.js not found on PATH"); `None` → the D2
    `runs_unavailable` stub degrade. POSIX-gated (`os.name == "posix"`). Builds `argv = (node, str(entry))`
    for `.js`, `(node, "--import", "tsx", str(entry))` for `.ts`.
  - `GatewayAwareServer.shutdown` drains the gateway before socket close (the M1 lease-release ordering).
- **The desktop launch** (`desktop/src/gateway/gatewayProcess.ts::buildGatewayLaunch`) is a **separate**
  path: it passes `nodeBinary = process.execPath` (Electron's own node, `ELECTRON_RUN_AS_NODE=1`). This is
  the "Electron-execPath path" the brief says stays UNCHANGED. It never touches the Python resolver.

### The run/PTY spawn seam (what a captured run actually hits)

- `packages/gateway/src/main.ts::runGatewayProcess` → `createDefaultRuntimeRouterDeps` builds a
  `RunManager` over a `NodePtyAdapter` (`ptyPort`) and a `PlainTerminalSessions`. Capture side: with
  `TRANSPORT_MATTERS_CAPTURE_RPC_URL` set → real `CaptureRpcClient`; **without it → `StubCaptureAdapter`**,
  whose `stubHarnessClientSpec` spawns `argv: [input.harness]` uncaptured.
- `packages/runtime/src/server/runtimeRouter.ts`: `POST /runs` (harness ∈ {claude, codex} only, else 400)
  → `RunManager.create` → `createNew` → `capturePort.prepareCapture` → `ptyPort.spawn(...)` →
  `register` (state RUNNING = "RUN_STARTED"). `GET /runs/:runId` reports state; on child exit the run
  settles to `EXITED`. There is also a `GET /terminal` **plain-terminal WS** that spawns a bare shell PTY
  through the same `PtyPort.spawn`, no harness, no capture, no DB.
- `packages/runtime/src/adapters/NodePtyAdapter.ts::NodePtyAdapter.loadNodePtyModule` = `await
  import("node-pty")`; `spawn` calls `nodePtyModule.spawn(command, args, {...})`. This is the ONE code path
  that loads `pty.node`. Whether invoked by a captured run or a plain terminal, it is identical.

### CI / release today (`.github/workflows/{ci,release}.yml`)

- `ci.yml` jobs: `backend-lint`, `backend-test` (postgres service), `frontend` (builds + uploads
  `www-bundle` and `canvas-bundle` artifacts), `product-plane` (postgres; runs `@tm/gateway test` +
  `@tm/runtime test` under **pnpm-workspace node-pty**, system node 20), `frontend-e2e`, `desktop`
  (ubuntu-22.04, packaged smoke under xvfb — the model for "a packaged smoke that loads the real
  artifact"), `package` (downloads the two bundle artifacts, stages them, `uv build`, smoke-installs the
  wheel, asserts www+canvas `index.html` inside the wheel).
- **Both runners for every job are `ubuntu-latest` / `ubuntu-22.04`.** A native Linux job needs no new
  infra.

---

## 1. THE finding that reshapes part (a): the released wheel has no gateway

`pnpm --filter @tm/gateway build` appears **only** in the root `justfile` (`build`, `install-local`,
`channel-restart`). It is **absent from both `ci.yml` and `release.yml`**. `assert_gateway_wheel.py` is
invoked **only** from `api/justfile::build` (local), never in either workflow — and even there it
soft-skips an absent bundle.

Consequence: the `package` job in `ci.yml` and the build job in `release.yml` both stage only `www` and
`canvas`, then run `uv build`. The gateway bundle is never produced in CI, so:

- **The CI-packaged wheel and the released PyPI wheel ship WITHOUT `transport_matters/gateway/`.**
- On any `pip install transport-matters`, `packaged_gateway_entry()` returns `None`, and (outside a
  workspace checkout) `resolve_gateway_entry` returns `None` → `plan_gateway_supervision` degrades to the
  D2 stub → **canvas runs answer 503 in the wild.** The D1-b work is dark in every release.
- `assert_gateway_wheel.py` would not have caught it: it soft-skips absence, and it is not wired into CI
  regardless.

So D1-c(a) cannot "prove the wheel's linux prebuild spawns a run" until the wheel actually contains the
gateway. Part (a) is therefore two layers: **(a0) close the D1-a→CI/release embedding gap**, then **(a1)
add the runtime spawn assertion.** This is the sharpest decision to surface to Stuart (§5).

---

## 2. Part (a): the Linux verification recipe

### 2a. Recommendation: native ci.yml primary, docker secondary (one shared assertion)

**Primary = a native `ci.yml` job on `ubuntu-latest`.** Rationale, weighed against the brief's axes:

- **Continuous coverage of the cross-platform claim.** The node-pty prebuild is a beta pin
  (`1.2.0-beta.14`) shipping N-API prebuilds; the risk is silent ABI/loader-layout drift on upgrade. A CI
  job re-proves linux-x64 on every push for free. A local-only docker recipe proves it the day a dev
  remembers to run it.
- **Zero new infra.** Every runner is already ubuntu; the `desktop` job is the precedent for "install a
  runtime, run a packaged smoke". No docker daemon, no image pull in CI.
- **It doubles as the fix-verification for §1.** The same job builds the gateway into the wheel and then
  spawns from it, so the embedding gap and the spawn proof are closed by one green job.

**Secondary = a thin `just verify-linux` docker recipe** for mac devs (uv + node base image) that runs the
**same pytest** inside a container. This is local repro only; it is not the source of truth. Keeping one
assertion behind two callers (CI step + docker recipe) is the DRY requirement — no second copy of the
spawn logic.

Not chosen: docker-only (loses continuous coverage, the primary value); a matrix (unnecessary — one linux
arch on the CI runner covers the untested claim; darwin is covered by the mac road-test).

### 2b. Layer a0 — embed the gateway in the wheel (close the §1 gap), in BOTH workflows

Mirror the existing www/canvas bundle pipeline exactly (DRY with the precedent, not a new pattern):

- **`ci.yml` `frontend` job**: add `pnpm --filter @tm/gateway build` after the inspector/canvas builds, and
  upload `api/src/transport_matters/gateway/` as a `gateway-bundle` artifact (`if-no-files-found: error`).
- **`ci.yml` `package` job**: add `gateway` to the `for bundle in www canvas` stage loop (download +
  stage), then flip the wheel-contents assertion to call `assert_gateway_wheel.py` and require it (the
  bundle is now expected, so absence must fail). The script already hard-fails an incomplete bundle; the
  only change is that "absent" is no longer acceptable once we stage it.
- **`release.yml`**: the same two additions (build gateway into the package; verify it landed) so the
  released wheel carries what CI proved.

Note: `pnpm install --frozen-lockfile --ignore-scripts` is what CI already uses. node-pty 1.2.0-beta.14
ships its prebuilds **in the published tarball**, so `--ignore-scripts` still yields
`node-pty/prebuilds/{platform}` for `build.mjs` to copy. (Verify in the build: `build.mjs` already asserts
each `prebuilds/{platform}` dir exists and fails loudly otherwise, so a tarball-layout regression is caught
at build time, not at spawn time.)

### 2c. Layer a1 — the runtime spawn assertion (cheapest hermetic proof)

The risk to retire is precisely: *does the wheel's bundled `prebuilds/linux-x64/pty.node` load and spawn a
PTY when required from the esbuild `main.js`?* The cheapest faithful exercise of `NodePtyAdapter.spawn` is
to boot the **packaged gateway alone under system node in stub mode**, with a fake `claude` on PATH, and
POST a run:

- No Python backend, no postgres, no capture RPC, no real harness. Stub mode (`CAPTURE_RPC_URL` unset)
  makes `POST /runs {harness:"claude"}` spawn `argv:["claude"]` directly through node-pty. A 2-line fake
  `claude` on PATH (print a line, `exit 0`) gives a genuine `RUN_STARTED → EXITED` lifecycle.
- This is the identical `import("node-pty") → pty.node` path a real captured run uses; it proves the linux
  prebuild loads and spawns without provisioning claude/codex or a workspace.

New assertion, as a pytest in `api/tests/integration/` (so it runs in the wheel-install CI job and locally
after `just build`, and **skips** in the bare `backend-test` job that has no bundle):

```
# api/tests/integration/test_gateway_wheel_spawn.py  (new)
# Reuse _free_port / _poll_http from test_backend_launch_smoke.py — promote them to a
# shared tests/integration helper rather than copy (DRY; they are currently module-private there).

skip_if packaged_gateway_entry() is None        # only runs against an embedded-gateway install

def test_packaged_gateway_spawns_a_captured_run_via_node_pty(tmp_path):
    port = _free_port()
    fake_claude = tmp_path / "bin" / "claude"     # prints a line, exit 0; chmod +x
    entry = packaged_gateway_entry()              # <site-packages>/transport_matters/gateway/main.js
    env = {**os.environ,
           "PATH": f"{fake_claude.parent}{os.pathsep}{os.environ['PATH']}",
           env_keys.GATEWAY_PORT: str(port)}
    env.pop(env_keys.CAPTURE_RPC_URL, None)       # stub mode
    env.pop(env_keys.DATABASE_URL, None)          # Activity disabled
    proc = Popen([which("node"), str(entry)], env=env, stdin=PIPE)   # system node; parent-watch off
    try:
        _poll_http(f"http://127.0.0.1:{port}/health")                # gateway up
        run = POST f"http://127.0.0.1:{port}/runs" {"harness":"claude"}
        assert run.status == 201 and run.body.run.state == "RUNNING" # RUN_STARTED
        eventually: GET /runs/{id} .state == "EXITED"                # RUN_EXITED via node-pty exit
    finally:
        terminate(proc)
```

The fake-`claude` harness is the only reason the run reaches a clean `EXITED`; without a real prebuild the
`POST /runs` fails at `ptyPort.spawn` (`pty_spawn_failed`) and the test fails — the negative is probative.

**CI job** (`ci.yml`, new `linux-wheel-spawn`, `needs: [package]`): download the gateway-embedded wheel the
`package` job built, `uv venv` + `pip install` it in a clean venv, ensure `node` is on PATH
(`actions/setup-node@v5`), and `pytest api/tests/integration/test_gateway_wheel_spawn.py`. No postgres.

### 2d. Optional second layer — prove the D1-b supervisor spawns on linux (integration, no run)

If Stuart wants the *supervisor* wiring (not just node-pty) proven on linux, add a lighter assertion that
boots the real Python backend from the installed wheel with `TRANSPORT_MATTERS_GATEWAY_SUPERVISE=1` (reuse
the `backend-test` postgres service and the `test_backend_launch_smoke.py` subprocess-launch shape), and
asserts the run proxy answers instead of the D2 stub (e.g. `GET /runs` → 200, not 503). This proves
`plan_gateway_supervision` resolves the packaged entry, spawns it, health-gates it, and mounts the proxy on
linux — without needing a run to spawn (layer a1 already proved the PTY). Recommend as a follow-on assertion
in the same job, gated behind the embedded bundle; flag as optional so it does not block the slice.

---

## 3. Part (b): the optional `transport-matters[node]` extra

### 3a. Verified upstream facts (first-hand, from the real wheel)

Downloaded `nodejs_wheel_binaries-24.16.0-py2.py3-none-macosx_13_0_arm64.whl` and inspected it:

- **Distribution name: `nodejs-wheel-binaries`** (binaries only, no console-script CLI). The sibling
  `nodejs-wheel` adds CLI entry points and depends on `-binaries`; we want `-binaries`.
- **Module import: `nodejs_wheel`** (submodule `nodejs_wheel.executable`).
- **No public `executable_path()` helper exists.** `nodejs_wheel/executable.py` defines
  `ROOT_DIR = os.path.dirname(__file__)` and, in `_program`, computes `bin_dir = ROOT_DIR if os.name ==
  "nt" else os.path.join(ROOT_DIR, "bin")`, then runs `os.path.join(bin_dir, "node"[".exe" on nt])`. So
  the node binary is at **`<package>/bin/node`** on POSIX, `<package>/node.exe` on Windows. The wheel
  layout confirms it: `nodejs_wheel/bin/node` (a real 124 MB binary), `nodejs_wheel/bin/{npm,npx,corepack}`.
- **Wheel tag is `py2.py3-none-<platform>`** (platform-specific, ~55 MB download / 124 MB unpacked). It is
  a universal-python, platform-specific wheel → installs cleanly on `requires-python >=3.14`. Base install
  must NOT pull it (it is heavy).

Recommended resolution (there is no documented path accessor, so derive from the shipped layout, guarded):
`Path(nodejs_wheel.__file__).parent / ("node.exe" if os.name == "nt" else "bin/node")`, existence-checked.

### 3b. Touch list

- **`api/pyproject.toml`** — add:
  ```
  [project.optional-dependencies]
  node = ["nodejs-wheel-binaries>=22"]   # floor = a version with the bin/ layout above; pin decision §5
  ```
  Base `[project.dependencies]` stays unchanged (the guardrail: base install pulls no node).
- **`api/src/transport_matters/gateway_supervisor.py`** — add a `resolve_node_binary` resolver (sibling to
  `resolve_gateway_entry`, same module, exported in `__all__`), and switch `plan_gateway_supervision` from
  `node = which("node")` to `node = resolve_node_binary(env, which=which)`. Everything else in the plan is
  unchanged; `None` still degrades to the D2 stub.
- **`api/src/transport_matters/cli/diagnose.py`** — the node check (`node = shutil.which("node")` under the
  "everything except canvas run spawning works without it" comment) reuses `resolve_node_binary` so doctor
  and the supervisor agree on which node will actually run. When PATH has no node but the bundled node is
  present, `_ok("node", "<path> (bundled via transport-matters[node])")`; when neither, the existing warn
  gains a second remedy line: `Or: pip install transport-matters[node]`.
- **Tests** — `api/src/transport_matters/test_gateway_supervisor.py`: add `resolve_node_binary` cases
  (bundled present via a monkeypatched fake `nodejs_wheel` module with a real temp `bin/node` file; bundled
  absent → falls through to `which`; both absent → `None`). Add a `plan_gateway_supervision` case asserting
  it consults `resolve_node_binary` (bundled node wins over an empty PATH). A `cli/test_diagnose.py` case
  for the bundled-node doctor line.
- **UNCHANGED (assert explicitly in the PR description):** `desktop/src/gateway/gatewayProcess.ts`
  (`buildGatewayLaunch`, execPath/`ELECTRON_RUN_AS_NODE`) — the Electron path never consults the extra.

### 3c. Resolve-order pseudocode

```python
def resolve_node_binary(env: Mapping[str, str] = os.environ,
                        *, which: Callable[[str], str | None] = shutil.which) -> str | None:
    """Node interpreter for a Python-spawned gateway: bundled extra first, then PATH.

    Mirrors resolve_gateway_entry's precedence idea for the *interpreter* half.
    None => no node available; plan_gateway_supervision degrades to the D2 stub.
    """
    bundled = _bundled_node_binary()            # the transport-matters[node] extra, if installed
    if bundled is not None:
        return str(bundled)
    return which("node")                        # system node on PATH (unchanged base behaviour)


def _bundled_node_binary() -> Path | None:
    try:
        import nodejs_wheel                      # optional extra; ModuleNotFoundError in base install
    except ModuleNotFoundError:
        return None
    root = Path(nodejs_wheel.__file__).parent
    candidate = root / ("node.exe" if os.name == "nt" else "bin/node")
    return candidate if candidate.is_file() else None
```

Precedence rationale: the operator who opts into `[node]` is declaring "use the bundled node", so it wins
over an incidental PATH node (version skew is then the operator's single, known interpreter). No new env
override is proposed (YAGNI); flag in §5 if Stuart wants `GATEWAY_ENTRY`-style symmetry.

---

## 4. Test plan — how each part is proven green

| Part | Proof | Gate |
|---|---|---|
| a0 embed | wheel now contains `transport_matters/gateway/main.js` + `prebuilds/linux-x64/`; `assert_gateway_wheel.py` hard-requires it | `ci.yml` `package` + `release.yml` (both fail closed if the bundle is missing/incomplete) |
| a1 spawn | packaged gateway boots under system node, `POST /runs {claude}` → 201 RUNNING → EXITED via node-pty | new `linux-wheel-spawn` CI job + `just verify-linux` docker (same pytest) |
| a2 supervisor (optional) | Python backend + `GATEWAY_SUPERVISE=1` → run proxy answers 200 not 503 on linux | same CI job, postgres service |
| b resolver | `resolve_node_binary` prefers bundled over PATH; degrades to None; doctor reflects it | `just check` + `just test` (unit: `test_gateway_supervisor.py`, `cli/test_diagnose.py`) |
| b guardrail | base `pip install transport-matters` pulls no node; `[node]` pulls `nodejs-wheel-binaries` | manual/CI: assert `nodejs_wheel` import fails in the base wheel smoke venv, succeeds in a `[node]` venv |

Repo gates verbatim: `just check` and `just test` at the root (the recipes in `justfile` — desktop, shell,
product-plane, api). The new integration test is opt-in via the `packaged_gateway_entry() is None` skip so
`just test` stays green on a workspace checkout that has not built the bundle, and exercises the real path
in CI and after `just build`.

---

## 5. Risks & decisions flagged for Stuart

1. **[DECISION — the load-bearing one] The released wheel currently ships no gateway (§1).** Confirm D1-c
   should own closing the D1-a→CI/release embedding gap (build @tm/gateway + embed + hard-assert in both
   workflows). Everything in part (a) depends on it. If you'd rather split it into its own hotfix PR ahead
   of D1-c, say so; my recommendation is one slice, since the spawn proof and the embed fix verify each
   other.
2. **[DECISION] CI-primary vs docker-primary.** Recommending native `ci.yml` primary + `just verify-linux`
   docker secondary (shared pytest). Confirm, or if you want zero new CI minutes, flip to docker-only and
   lose continuous coverage.
3. **[DECISION] Captured-run vs plain-terminal for the a1 assertion.** Recommending the stub-mode captured
   run with a fake `claude` (faithful to "RUN_STARTED/EXITED"). The `GET /terminal` plain-terminal WS is an
   even lighter alternative that hits the identical `NodePtyAdapter.spawn` with no fake harness at all, if
   you'd rather not stage a fake binary. Both prove the linux prebuild.
4. **[DECISION] node path resolution has no public accessor.** Deriving `<package>/bin/node` from
   `nodejs_wheel.__file__` (verified layout). Add a layout-guard unit test + a version floor so an upstream
   reshape fails a test rather than a spawn. Confirm the floor pin (I suggest `>=22`, matching the node
   line the gateway targets — esbuild `target: "node20"`, so any 20/22/24 bundled node runs `main.js`).
5. **[RISK] Bundled node ABI vs node-pty prebuilds.** node-pty ships **N-API** prebuilds (ABI-stable across
   node majors), which is the whole reason execPath/bundled-node works. The a1 CI job spawns from bundled
   node ONLY if we also test the `[node]` path there; recommend the a1 job runs the spawn once under system
   node (proves the prebuild) and the b guardrail venv proves `[node]` resolves the interpreter — keeping
   the two concerns separate rather than entangling a1 with the extra.
6. **[RISK] `--ignore-scripts` + node-pty prebuilds.** CI installs with `--ignore-scripts`; the plan relies
   on node-pty 1.2.0-beta.14 shipping prebuilds in its tarball. `build.mjs` already asserts each
   `prebuilds/{platform}` dir exists and fails loudly, so a regression surfaces at gateway-build time in
   the `frontend` job, not at spawn time. No extra guard needed.
7. **[NOTE] Wheel size.** `[node]` pulls a ~55 MB platform wheel (124 MB unpacked). Strictly optional and
   opt-in; base install is untouched. Worth a one-line mention in the doctor remedy so users know the cost.

---

## 6. Build order (once signed off)

1. a0: embed gateway in `ci.yml` (`frontend` upload + `package` stage/assert) and `release.yml`; flip
   `assert_gateway_wheel.py` usage to required. Prove: CI `package` job now finds `gateway/main.js` in the
   wheel.
2. a1: `test_gateway_wheel_spawn.py` + `linux-wheel-spawn` CI job + `just verify-linux`. Prove: green spawn
   on the ubuntu runner and in docker.
3. b: pyproject `[node]` extra, `resolve_node_binary`, wire into `plan_gateway_supervision` + `diagnose`,
   unit tests. Prove: `just check` + `just test`, plus the base-vs-[node] venv guardrail.
4. (optional) a2 supervisor integration assertion.

codex + opus sign off on this PLAN before any code.
