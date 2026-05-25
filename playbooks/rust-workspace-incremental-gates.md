---
title: Rust workspace incremental gates and build cache
type: playbooks
tags: [rust, cargo, just, clippy, nextest, incremental, build-cache, changed-crates, reverse-deps, moon, ci, workspace]
summary: Scope build/test/clippy gates to changed crates plus their reverse-dependency closure so warm pre-commit checks run in seconds, with a full-workspace regression gate held in reserve.
status: active
project: helioy
related: [rust-workspace-justfile, rust-workspace-cli-binary, rust-clippy-monorepo-speedups-2026, rust-conventions-2026]
confidence: high
---

# Rust workspace incremental gates and build cache

Use this when a Rust workspace's pre-commit gate has grown slow enough that contributors skip it. The fix is to stop gating the whole workspace on every change. Scope `build`, `test`, and `clippy` to the crates that actually changed plus their reverse-dependency closure, fall back to `--workspace` only when a workspace-wide file moves, and keep one unconditional full gate (`regression`) for merge, CI, and audits.

This playbook owns the scoping mechanism: the `changed-crates.sh` helper, the recipe wiring that consumes it, the `cargo clippy --fix` fingerprint trap, nextest serialization for shared-resource tests, and how CI composes incremental local gates with a cached full gate. Recipe naming and the overall justfile shape live in [[rust-workspace-justfile]]. The broader 2026 field survey of Rust CI speedups lives in [[rust-clippy-monorepo-speedups-2026]].

## Why scope the gate

A full-workspace `cargo clippy --workspace --all-targets` plus `cargo build --workspace` plus `cargo nextest run --workspace` is the correct merge gate but the wrong pre-commit gate. On a few-dozen-crate workspace it runs for tens of seconds to minutes even when warm, because every member is re-fingerprinted and every test binary is considered.

Most commits touch one or two crates. Cargo already has the dependency graph; `cargo metadata` exposes it. Compute which crates changed, walk the reverse-dependency edges to find everything that could be affected, and pass exactly those as `-p` flags. The warm gate then costs whatever it costs to re-check the touched subgraph, which is sub-second for a leaf-crate edit. The unchanged-crate fingerprints stay warm in `target/` and are reused, not rebuilt.

This is a local-dev complement to the CI changed-path gating surveyed in [[rust-clippy-monorepo-speedups-2026]] §3.5. CI gates by *path* (skip the whole job on docs-only PRs); this gates by *crate* (run the gate, but only over the affected subgraph). Both rely on the same insight: do not recompute what did not change.

## The scoping helper

One script is the source of truth for "what changed". It emits cargo `-p` flags, the sentinel `--workspace`, or an empty line. Recipes branch on those three outputs. The script is project-agnostic: it reads `cargo metadata` and git, with no hard-coded crate names, so it copies across workspaces unchanged.

Place it at `scripts/changed-crates.sh` and mark it executable. It is Python with a `.sh` extension so callers invoke one stable path regardless of implementation language.

```python
#!/usr/bin/env python3
"""Emit -p flags for workspace crates whose source changed since base_ref,
plus the transitive reverse-dep closure.

Usage:  scripts/changed-crates.sh [base_ref]
Output:
  - Empty line: no relevant changes; caller should skip the gate.
  - `--workspace`: change touched a workspace-wide file (root Cargo.toml,
                   rust-toolchain.toml, .cargo/*). Caller falls back to full gate.
  - `-p crateA -p crateB ...`: scope the gate to these crates.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WORKSPACE_WIDE_FILES = {"Cargo.toml", "rust-toolchain.toml"}
WORKSPACE_WIDE_PREFIXES = (".cargo/",)


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line]


def changed_files(base_ref: str) -> list[str]:
    if subprocess.run(
        ["git", "rev-parse", "--verify", base_ref], capture_output=True
    ).returncode != 0:
        base_ref = "HEAD~1"
    files: set[str] = set()
    files.update(git("diff", "--name-only", f"{base_ref}...HEAD"))
    files.update(git("diff", "--name-only", "HEAD"))
    files.update(git("diff", "--name-only", "--cached"))
    files.update(git("ls-files", "--others", "--exclude-standard"))
    return sorted(files)


def main() -> int:
    base_ref = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BASE_REF", "main")
    files = changed_files(base_ref)
    if not files:
        print("")
        return 0

    meta = json.loads(
        subprocess.run(
            ["cargo", "metadata", "--format-version=1"],
            check=True, capture_output=True, text=True,
        ).stdout
    )
    workspace_ids: set[str] = set(meta["workspace_members"])
    pkg_name: dict[str, str] = {}
    pkg_dir: dict[str, Path] = {}
    for pkg in meta["packages"]:
        if pkg["id"] in workspace_ids:
            pkg_name[pkg["id"]] = pkg["name"]
            pkg_dir[pkg["id"]] = Path(pkg["manifest_path"]).parent.resolve()

    reverse_deps: dict[str, set[str]] = {pid: set() for pid in workspace_ids}
    for node in meta["resolve"]["nodes"]:
        if node["id"] not in workspace_ids:
            continue
        for dep in node["deps"]:
            if dep["pkg"] in workspace_ids:
                reverse_deps[dep["pkg"]].add(node["id"])

    repo_root = Path.cwd().resolve()
    dir_to_pkg = {d: pid for pid, d in pkg_dir.items()}

    touched: set[str] = set()
    workspace_wide = False
    for rel in files:
        path = (repo_root / rel).resolve()
        match: str | None = None
        for ancestor in [path, *path.parents]:
            if ancestor in dir_to_pkg:
                match = dir_to_pkg[ancestor]
                break
            if ancestor == repo_root:
                break
        if match is not None:
            touched.add(match)
            continue
        if rel in WORKSPACE_WIDE_FILES or any(
            rel.startswith(p) for p in WORKSPACE_WIDE_PREFIXES
        ):
            workspace_wide = True

    if workspace_wide:
        print("--workspace")
        return 0
    if not touched:
        print("")
        return 0

    needed = set(touched)
    queue = list(touched)
    while queue:
        cur = queue.pop()
        for parent in reverse_deps.get(cur, ()):
            if parent not in needed:
                needed.add(parent)
                queue.append(parent)

    print(" ".join(f"-p {pkg_name[pid]}" for pid in sorted(needed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

What it does, in order:

1. **Collect changed files** against `BASE_REF` (default `main`, override with the env var or a positional arg). It unions four sources so uncommitted work is gated too: committed diff `base...HEAD`, unstaged `diff HEAD`, staged `diff --cached`, and untracked-but-not-ignored files. If `base_ref` does not resolve, it falls back to `HEAD~1`.
2. **Map files to crates** by matching each changed path against every workspace member's manifest directory, walking up to the nearest enclosing crate.
3. **Detect workspace-wide changes.** A change to the root `Cargo.toml`, `rust-toolchain.toml`, or anything under `.cargo/` invalidates the whole graph (shared deps, lints, toolchain, build config). The script emits `--workspace` and stops. Extend `WORKSPACE_WIDE_FILES` / `WORKSPACE_WIDE_PREFIXES` for any other file that should force a full gate.
4. **Walk the reverse-dependency closure.** A change to crate A must also re-check everything that depends on A, transitively. The script seeds the queue with touched crates and follows reverse edges until the set stops growing.
5. **Emit `-p` flags** for the closure, sorted for stable output.

The empty-output case matters: a commit that touches only docs, CI config, or non-crate files produces no flags, and the recipe skips the gate entirely rather than running it over zero crates.

## Recipe wiring

Each gated recipe calls the helper once, branches on the three outputs, and labels what it is doing. The branch is identical across `build`, `test`, and clippy, so keep the shape consistent.

```just
BASE_REF := env("BASE_REF", "main")

build:
    #!/usr/bin/env bash
    set -euo pipefail
    flags="$(scripts/changed-crates.sh {{BASE_REF}})"
    if [[ -z "$flags" ]]; then
        echo "[build] no relevant changes vs {{BASE_REF}}; nothing to compile."
        exit 0
    fi
    if [[ "$flags" == "--workspace" ]]; then
        echo "[build] workspace-wide change; cargo build --workspace."
        cargo build --workspace
    else
        echo "[build] scoped:$(echo "$flags" | tr -s ' ' | sed 's/-p / /g')"
        cargo build $flags
    fi

test *ARGS:
    #!/usr/bin/env bash
    set -euo pipefail
    flags="$(scripts/changed-crates.sh {{BASE_REF}})"
    if [[ -z "$flags" ]]; then
        echo "[test] no relevant changes vs {{BASE_REF}}; nothing to run."
        exit 0
    fi
    if [[ "$flags" == "--workspace" ]]; then
        echo "[test] workspace-wide change; cargo nextest run --workspace."
        cargo nextest run --workspace {{ARGS}}
    else
        echo "[test] scoped:$(echo "$flags" | tr -s ' ' | sed 's/-p / /g')"
        cargo nextest run $flags {{ARGS}}
    fi
```

`build` scopes `inputs` to `sources` only; `test` also forwards `{{ARGS}}` so an individual test can still be targeted on top of the scope.

## The clippy `--fix` fingerprint trap

This is the non-obvious finding that makes or breaks the speedup.

`cargo clippy` (read-only) and `cargo clippy --fix` use **different fingerprint modes**. Running `--fix` rewrites the fingerprint such that the *next* read-only clippy, and often the next `build`, sees the whole workspace as dirty and recompiles from scratch (tens of seconds warm). So a `check` recipe that runs `clippy --fix` unconditionally on every invocation pays a full-recompile tax every single time, even when there is nothing to fix. This silently defeats the entire incremental gate.

The fix is to run read-only clippy first and only fall back to `--fix` when it actually fails:

```just
# Run read-only clippy first; it keeps the fingerprint cache warm and is
# sub-second when validation passes. Only fall back to --fix on failure,
# auto-correct, then re-validate. Never run --fix unconditionally: it uses
# a different fingerprint mode and forces a full workspace recompile.
_clippy-incremental:
    #!/usr/bin/env bash
    set -euo pipefail
    flags="$(scripts/changed-crates.sh {{BASE_REF}})"
    if [[ -z "$flags" ]]; then
        echo "[clippy] no relevant changes vs {{BASE_REF}}; skipping."
        exit 0
    fi
    if [[ "$flags" == "--workspace" ]]; then
        scope_label="workspace-wide"
        scope_flags=(--workspace)
    else
        scope_label="scoped:$(echo "$flags" | tr -s ' ' | sed 's/-p / /g')"
        scope_flags=($flags)
    fi
    echo "[clippy] $scope_label (read-only)"
    if cargo clippy "${scope_flags[@]}" --all-targets -- -D warnings; then
        exit 0
    fi
    echo "[clippy] lint failures; running --fix"
    cargo clippy --fix "${scope_flags[@]}" --all-targets --allow-dirty --allow-staged -- -D warnings
    echo "[clippy] re-validating after --fix"
    cargo clippy "${scope_flags[@]}" --all-targets -- -D warnings
```

This inverts the older "always apply autofixes, then verify" convention. With the incremental gate, the common path (clean lints) must stay read-only to preserve the cache; autofix is the exceptional path. The clean-warm gate is sub-second; only a real lint failure pays for the `--fix` round trip.

## The two-gate split

Keep two distinct gates with different jobs.

```just
# Pre-commit gate. Incremental by default. fmt / loc / provenance run
# workspace-wide because they are cheap and operate on raw files, not the
# Rust compile graph; only the clippy step is scoped.
check: fmt _clippy-incremental fmt-check check-loc check-provenance

# Full-workspace gate. Use before merging to main, in CI, or any time the
# scoping heuristic might miss a regression surface (workspace-wide
# refactors, release-prep, manual audits).
regression:
    cargo fmt --all -- --check
    bash scripts/check-loc-limit.sh
    bash scripts/check-provenance.sh
    cargo clippy --workspace --all-targets -- -D warnings
    cargo nextest run --workspace
```

- `check` is the fast inner-loop gate. Only the compile-graph steps (clippy, and `build`/`test` when invoked) are scoped. File-level checks (`fmt`, LOC budget, provenance) stay workspace-wide because they are cheap and do not touch `target/`.
- `regression` is the unconditional safety net. It never consults `changed-crates.sh`. Run it before merge, in CI, and whenever a change is wide enough that you do not trust the heuristic.

The scoping heuristic is deliberately conservative (it over-includes via the reverse-dep closure and escalates to `--workspace` on any shared-config change), but `regression` exists precisely so correctness never depends on the heuristic being perfect.

## Serializing shared-resource tests

Scoped runs and full runs both go through nextest, so any test that contends on a global resource must be capped, or it will flake under parallelism. Declare a test group and bind it with a filter in `.config/nextest.toml`:

```toml
# Tests that share one global resource (a tmux server, a fixed port, a
# singleton daemon) race under parallel execution. Cap them to one at a time.
[test-groups]
tmux = { max-threads = 1 }

[[profile.default.overrides]]
filter = 'test(/tmux/)'
test-group = 'tmux'
```

The group cap applies whether the run is `--workspace` or scoped to a few crates, so the serialization invariant holds in both gates. Match the `filter` to whatever names the contended tests share.

## CI composition

CI runs the full gate, not the incremental one, because a clean merge must not depend on what a contributor's working tree happened to touch. Compose two things:

1. **A cached full gate.** Restore `target/` and the cargo registry with `Swatinem/rust-cache@v2`. If the workspace is driven by Moon, `moon ci` orchestrates the same `fmt-check`/`clippy`/`build`/`test` plus file-checks set as `regression`, and Moon's own hash-based task cache skips tasks whose declared inputs did not change. Cargo's warm `target/` from rust-cache plus Moon's task-level skip give the full gate most of the incremental gate's speed without trusting the local heuristic.
2. **A binary smoke test** after the gate, exercising the actual built artifact (`--version`, `doctor --output json | jq .`) so a green gate also proves the binary runs.

```yaml
      - name: Cache Rust build outputs
        uses: Swatinem/rust-cache@v2
      - name: Install Moon toolchain
        uses: moonrepo/setup-toolchain@v0
      - name: Install cargo-nextest
        uses: taiki-e/install-action@nextest
      - name: Moon CI
        run: moon ci
```

For the cache-action selection itself (rust-cache vs sccache vs hosted-runner volumes, `save-if: main`, pinning by SHA), defer to [[rust-clippy-monorepo-speedups-2026]] §3.2 and §5. This playbook only fixes the local gate and the CI orchestration around it.

## Verification

After wiring the gate, prove all three helper outputs and both gates:

```bash
# 1. Helper emits scoped flags for a leaf-crate edit.
touch crates/<some-leaf-crate>/src/lib.rs
scripts/changed-crates.sh            # expect: -p <leaf-crate> [+ reverse-dep closure]

# 2. Helper escalates on a workspace-wide change.
touch rust-toolchain.toml
scripts/changed-crates.sh            # expect: --workspace
git checkout -- rust-toolchain.toml

# 3. Warm incremental gate is fast and clean.
just check                           # second run on a clean tree should be sub-second on clippy

# 4. Full gate passes.
just regression
```

Confirm the warm `just check` does **not** trigger a full recompile (watch for a long `cargo clippy` rebuild). If it does, the `--fix` trap is back: verify `check` calls `_clippy-incremental`, not `clippy-fix`.

## Guardrails

- Do not run `cargo clippy --fix` unconditionally in `check`. It uses a different fingerprint mode and forces a full workspace recompile on every invocation, defeating the incremental gate. Read-only first, `--fix` only on failure.
- Do not make `regression` consult the scoping helper. Its job is to be the unconditional full gate that does not depend on the heuristic.
- Do not scope `fmt`, LOC, or provenance checks. They are cheap, operate on raw files, and must run workspace-wide.
- Do not forget the empty-output case. A docs-only or CI-only commit must skip the gate, not run it over zero crates.
- Do not drop the reverse-dependency closure. Gating only the directly-touched crate misses regressions in its dependents.
- Do not hard-code crate names in `changed-crates.sh`. It must stay project-agnostic so it copies across workspaces; extend the workspace-wide file lists instead.
- Do not rely on the incremental gate for merge correctness. CI runs the full cached gate; `check` is the inner-loop accelerator only.
- Do not let shared-resource tests run unbounded under nextest. Cap them with a test group so both scoped and full runs stay deterministic.

## Good completion evidence

An acceptable closeout includes:

- `scripts/changed-crates.sh` present, executable, and project-agnostic.
- `build`, `test`, and `_clippy-incremental` consuming the helper with the three-way branch.
- `check` wired to `_clippy-incremental` (not `clippy-fix`) and `regression` as the unconditional full gate.
- A `.config/nextest.toml` test group for any shared-resource tests.
- Verification output showing scoped flags for a leaf edit, `--workspace` for a toolchain edit, a sub-second warm `just check`, and a passing `just regression`.
- CI running the full cached gate (`moon ci` or equivalent) plus a binary smoke test.
- A cm decision entry naming the gate split, the `--fix` fingerprint finding, and the verification results.
