---
title: Sign-off findings — t3code P1 Slice D1-c (opus 5:2.3)
type: projects
tags: [transport-matters, t3code, p1, slice-d1c, sign-off, review, packaging, ci, node-pty, nodejs-wheel]
summary: Opus independent sign-off on D1-c (embed-gap fix + linux spawn proof + [node] extra; closes POSIX P1). Verdict SIGN-OFF with 2 must-fixes. The load-bearing (a0) finding is CONFIRMED first-hand — released wheels ship no gateway/, so D1-b is dark in the wild. Both must-fixes are about scoping the a0 CI enforcement to fail-closed in CI WITHOUT breaking local Python-only builds. First-hand on main @ daa1984.
status: active
source: opus (5:2.3), first-hand on main @ daa1984
confidence: high
created: 2026-07-08
---

# D1-c plan sign-off (opus) — SIGN-OFF with 2 must-fixes

Reviewed as a single slice (a0 embed-gap + a1 linux spawn + a2 optional supervisor + b [node] extra) per
Stuart's locked sequencing. The load-bearing finding is real and correctly scoped; my must-fixes are both
about how the a0 CI enforcement is wired so it fails-closed in CI without regressing local builds.

## Confirmed first-hand (main @ daa1984)

- **(a0) is a genuine ship-broken bug.** `ci.yml` `frontend` builds only `@tm/inspector` + `@tm/canvas`
  and uploads `www-bundle`/`canvas-bundle` — no `@tm/gateway build`, no gateway artifact. `release.yml`
  builds + verifies only `for bundle in www canvas`. `assert_gateway_wheel.py::check_wheel` soft-skips an
  absent bundle (`return errors` with `errors` empty → exit 0) and is invoked nowhere in either workflow.
  So the released PyPI wheel and CI-packaged wheel ship WITHOUT `transport_matters/gateway/` →
  `packaged_gateway_entry()` returns None → `plan_gateway_supervision` degrades to the D2 stub → canvas
  runs 503 on every `pip install`. D1-b is dark in the wild. The slice is necessary.
- **`--ignore-scripts` is SAFE (confirmed).** node-pty 1.2.0-beta.14 `package.json` `files` includes
  `prebuilds/`, so the npm tarball ships the prebuilds verbatim; `--ignore-scripts` skips node-pty's
  `install` (`prebuild.js || node-gyp rebuild`) and `postinstall` (`post-install.js`) but NOT tarball
  unpacking — `prebuilds/linux-x64/pty.node` is present regardless. `build.mjs` asserts each
  `prebuilds/{platform}` before copy (fails loudly on a tarball regression). The a1 spawn test is the
  end-to-end guard that the `--ignore-scripts` + esbuild-bundle result actually loads `pty.node` on linux —
  well-motivated; keep it as THE load-bearing proof.
- **a1 design is faithful.** Stub mode (`CAPTURE_RPC_URL` unset) + a fake `claude` on PATH drives
  `POST /runs` → `NodePtyAdapter.spawn` → `import("node-pty") → pty.node` — the identical prebuild-load path
  a real captured run uses. It correctly isolates the node-pty-prebuild concern; the capture RPC is
  Python-side and platform-agnostic (tested elsewhere). The negative (missing prebuild → `pty_spawn_failed`
  → test fails) is probative.

## Must-fix

### M1 — the soft→hard flip must not regress local `cd api && just build` (blast radius)

`api/justfile::build` DOES invoke `uv run python scripts/assert_gateway_wheel.py dist/*.whl`, and it
soft-skips absence by design — consistent with the sibling www/canvas echoes that also soft-warn when a
bundle was not built. A standalone `cd api && just build` (a legitimate Python-only local workflow that
does not build the JS gateway) relies on that soft-skip. If a0 flips the SCRIPT itself to hard-fail on
absence, that local build suddenly fails. Scope the strictness to CI: add a `--strict`/`--require` flag
(CI passes it; the api/justfile local call does not), or enforce presence via a separate CI check (M2)
and leave the script's local soft-skip intact. Do not make "no gateway" a hard error for local Python-only
builds.

### M2 — add an explicit CI presence check for gateway/main.js, mirroring the existing www/canvas pattern

`assert_gateway_wheel.py` hard-fails an INCOMPLETE bundle but soft-skips an ABSENT one — so after a0 stages
the gateway, a staging step that silently produced nothing would still pass the assert. Mirror release.yml's
existing per-bundle guard (`python -m zipfile -l "$wheel" | grep -q "transport_matters/$bundle/index.html"`
→ `::error`) by adding `gateway/main.js` to that loop in BOTH `ci.yml` package and `release.yml`, so
absence fails closed independently of the script's soft-skip. (This is the same mechanism M1's flag-or-grep
resolves — one CI check covers both: local stays soft, CI fails closed on absence.)

## Notes (sound / minor)

- **DRY consolidation of the port/poll helpers.** `_free_port`/`_poll_http` live in
  `test_backend_launch_smoke.py`, but sibling `_free_port` copies also exist in `cli/test_net.py` and
  `cli/test_ports.py`. When promoting to a shared `tests/integration` helper, consolidate ALL copies rather
  than leaving three duplicates behind a fourth home (confirm the sibling copies share the same
  signature/intent first).
- **(b) resolver precedence + path fragility.** Bundled-over-PATH is defensible (opting into `[node]`
  declares "use the bundled interpreter"). The `Path(nodejs_wheel.__file__).parent / "bin/node"` derivation
  has no public accessor and is layout-fragile — the plan's layout-guard unit test (fake `nodejs_wheel` with
  a real temp `bin/node`) + version floor (`>=22`) is the right mitigation; the floor is sound because
  node-pty's N-API prebuilds are ABI-stable across node majors (20/22/24 all load the same `pty.node`,
  esbuild targets node20). The Windows branch (`node.exe` at package root) is dead code in D1-c (the
  supervisor is `os.name == "posix"`-gated) — harmless but unverified until D1-win; note it, don't test it
  here. Base-install-pulls-no-node guardrail (import-fails-in-base-venv / succeeds-in-[node]-venv) is the
  correct proof.
- **release.yml blast radius is acceptable.** Adding the gateway build + presence verify fails the release
  closed if the gateway build breaks — strictly better than the current state (silently shipping a
  stub-degrading wheel). release.yml already has node+pnpm and uses `--ignore-scripts`, so the same
  (confirmed-safe) prebuild path applies.
- **a2 (supervisor integration) is correctly optional** and should not block the slice; a1 already proves
  the PTY, a2 only adds `plan_gateway_supervision` wiring proof on linux.

Strong plan — the a0 finding is a real caught bug and the a1 proof is the right shape. Both must-fixes are
about wiring the a0 enforcement so CI fails closed on a missing gateway while local Python-only builds keep
their soft-skip.
