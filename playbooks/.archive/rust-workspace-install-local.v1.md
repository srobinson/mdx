---
title: Rust workspace install-local without full release LTO
type: playbooks
tags: [rust, cargo, just, install-local, local-development, binary, version]
summary: Recipe for making a Rust workspace local install fast while preserving release builds and version identity
status: active
project: runtime-matters
related: [rust-binary-workspace-cargo-dist]
confidence: high
---

# Rust workspace install-local without full release LTO

Use this when a Rust workspace has a local install recipe for a CLI binary and `just install-local` appears to hang.

The common failure mode is simple: `install-local` depends on the full release build. If `[profile.release]` enables full LTO and `codegen-units = 1`, Cargo can spend minutes inside `rustc` linking the binary. That is acceptable for release artifacts, but too slow for a local developer install.

## Runtime-matters validation

Observed on `runtime-matters` on 2026-05-18:

- Old command: `just install-local`
- Dry run showed `cargo build --workspace --release`
- Live run with a temporary `RTM_LOCAL_BIN` was killed after 180 seconds
- Process tree showed `rustc` linking `rtm` with `-C lto -C codegen-units=1`
- Fixed path completed a first successful install in 51.38 seconds after populating a new profile cache
- Cached install completed in 0.89 seconds
- Repo gate passed: `just check && just build && just test`

## Target shape

Keep release artifact production strict. Add a separate local install profile that is still optimized, but does not use full LTO.

```toml
[profile.release]
codegen-units = 1
lto = true
opt-level = 3
strip = true

[profile.dist]
inherits = "release"
lto = "thin"

[profile.install-local]
inherits = "release"
codegen-units = 16
lto = false
```

Then make `install-local` build the actual binary package, not the entire workspace release profile.

```just
build-local:
    RTM_VERSION_INCLUDE_GIT_SHA=1 cargo build -p rtm-cli --bin rtm --profile install-local

build-install-release:
    RTM_VERSION_INCLUDE_GIT_SHA=0 cargo build -p rtm-cli --bin rtm --release

install-local: build-local
    @just _install-bin target/install-local/rtm

install-release: build-install-release
    @just _install-bin target/release/rtm

_install-bin src:
    @set -eu; \
    src="$(pwd)/{{src}}"; \
    dest="{{RTM_LOCAL_BIN}}"; \
    case "$dest" in /*) ;; *) dest="$(pwd)/$dest";; esac; \
    if [ "$src" = "$dest" ]; then \
        echo "Built $src"; \
    else \
        mkdir -p "$(dirname "$dest")"; \
        install -m 755 "$src" "$dest"; \
        echo "Installed $dest"; \
    fi
```

Replace `rtm-cli`, `rtm`, and `RTM_LOCAL_BIN` with the workspace package, binary, and install variable for the repo.

`install-local` and `install-release` should write to the same destination. Switching means running the other install recipe, then checking `--version`.

## Version stamp contract

Every local install recipe should prove which binary was installed. Add a root `--version` flag that is handled in process. It must not require a daemon, socket, network call, or database.

Use this output shape:

```text
<product-name> <package-version>
<product-name> <package-version>+<7-char-sha>
```

Examples:

```text
runtime-matters 0.1.5
runtime-matters 0.1.5+88ee409
```

Release installs should print only the package version. Local install builds should set `RTM_VERSION_INCLUDE_GIT_SHA=1` so the installed binary records the source revision that produced the local build.

Keep daemon or service metadata on its existing command if the project has one. In runtime-matters, `rtm --version` identifies the local binary, while `rtm version` still asks `rtmd` for JSON metadata.

## Investigation recipe

1. Confirm what `install-local` really does.

   ```bash
   just --dry-run install-local
   ```

2. Reproduce without overwriting the real installed binary.

   ```bash
   tmpdir="$(mktemp -d)"
   timeout 180s env RTM_LOCAL_BIN="$tmpdir/rtm" just install-local
   ```

3. If it stalls, inspect the process tree.

   ```bash
   ps -eo pid,ppid,stat,%cpu,%mem,etime,time,command | rg 'just|cargo|rustc|ld|clang'
   ```

   A full LTO stall usually appears as `rustc` with `-C lto -C codegen-units=1`.

4. Check the release profile.

   ```bash
   rg -n '\[profile\.release\]|\[profile\.dist\]|lto|codegen-units|strip|opt-level' Cargo.toml
   ```

5. Add `[profile.install-local]` and a separate `build-local` recipe.

6. Verify with a temporary destination.

   ```bash
   tmpdir="$(mktemp -d)"
   timeout 180s env RTM_LOCAL_BIN="$tmpdir/rtm" just install-local
   "$tmpdir/rtm" --version
   timeout 300s env RTM_LOCAL_BIN="$tmpdir/rtm" just install-release
   "$tmpdir/rtm" --version
   ```

   The release output should use the product name and package version. The local output should add a 7 character git sha to the same package version.

7. Run the repo gate before claiming the recipe is fixed.

   ```bash
   just check && just build && just test
   ```

## Guardrails

- Do not weaken `[profile.release]` just to make local installs faster.
- Do not point `install-local` at `target/release/<bin>` after moving the build to a custom profile.
- Do not install over the live user binary until a temporary `RTM_LOCAL_BIN` install works.
- Keep cargo-dist or release automation on `release` or `dist`; `install-local` is for local developer convenience.
- Build the package that owns the binary with `-p <package> --bin <binary>` instead of rebuilding every workspace target.

## Good completion evidence

An acceptable closeout includes:

- The old command and where it stalled.
- The specific release profile flags responsible for the long build.
- The new profile and recipe path.
- A temp destination install result.
- A cached reinstall timing if available.
- The repo gate result.
