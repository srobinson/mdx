---
title: Rust workspace CLI binary install and version stamp
type: playbooks
tags: [rust, cargo, clap, just, install-local, install-release, version, git-sha, binary, local-development]
summary: Single contract for Rust workspace CLI installation and binary version identity
status: active
project: helioy
related: [rust-workspace-justfile, rust-binary-workspace-cargo-dist, rust-workspace-crates-io-publishing]
confidence: high
---

# Rust workspace CLI binary install and version stamp

Use this when a Rust workspace ships an executable that developers install locally. It covers four tightly coupled concerns that must move together:

- A fast local install profile that does not weaken the release profile.
- Install recipes that route both local and release builds to the same destination.
- A build-time version stamp that distinguishes a local install from a release install.
- Clap wiring so `--version` is process-local and identifies the installed binary.

Justfile shape and the `check` pipeline live in [[rust-workspace-justfile]]. GitHub Releases plumbing lives in [[rust-binary-workspace-cargo-dist]]. crates.io publishing lives in [[rust-workspace-crates-io-publishing]].

## Identity Contract

Root `--version` is process local. It is handled by the CLI parser before any service connection, daemon handshake, or runtime setup.

Use the product name in version output, even when the executable name is shorter.

```text
runtime-matters 0.1.5
runtime-matters 0.1.5+7b97019
```

| Path | Output shape |
| --- | --- |
| Release install (`just install`) | `<product-name> <package-version>` |
| Local install (`just install-local`) | `<product-name> <package-version>+<7-char-sha>` |

The sha records the source revision used when `install-local` was run. Release installs print only the package version. `just install` reinstalls the release binary so users can revert from a local build with one command.

If the project also exposes daemon or service metadata, keep that on a separate command. In runtime-matters, `rtm --version` identifies the local binary while `rtm version` asks `rtmd` for JSON metadata.

## Install Profile

Keep `[profile.release]` strict. Add a separate `install-local` profile that stays optimized but skips full LTO.

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

`install-local` exists so local rebuilds stay sub-15s after the profile cache is warm. Do not delete it once added.

## Build Stamp

Emit one compile-time version string from the CLI crate's `build.rs`.

Default to the package version. Append the git sha only when `<PROJECT>_VERSION_INCLUDE_GIT_SHA=1`.

```rust
fn emit_cli_version() {
    emit_git_rerun_directives();
    println!("cargo:rerun-if-env-changed=SM_GIT_SHA");
    println!("cargo:rerun-if-env-changed=GITHUB_SHA");
    println!("cargo:rerun-if-env-changed=SM_VERSION_INCLUDE_GIT_SHA");

    let package_version = std::env::var("CARGO_PKG_VERSION").expect("CARGO_PKG_VERSION set");
    let version = match (include_git_sha(), build_git_sha()) {
        (true, Some(sha)) => format!("{package_version}+{sha}"),
        _ => package_version,
    };
    println!("cargo:rustc-env=SM_CLI_VERSION={version}");
}
```

Watch git ref files so local rebuilds pick up a changed commit when the local install profile is rebuilt. Resolve both normal checkouts and linked worktrees. In a linked worktree, `.git` is a file that points at a worktree git directory, while branch refs usually live under the common git directory named by `commondir`.

```rust
use std::path::{Path, PathBuf};

fn emit_git_rerun_directives() {
    let git_path = workspace_git_path();
    println!("cargo:rerun-if-changed={}", git_path.display());

    let Some(git_dir) = resolve_git_dir() else {
        return;
    };

    let head_path = git_dir.join("HEAD");
    println!("cargo:rerun-if-changed={}", head_path.display());

    let Ok(head) = std::fs::read_to_string(&head_path) else {
        return;
    };
    if let Some(ref_path) = head.trim().strip_prefix("ref: ") {
        println!("cargo:rerun-if-changed={}", git_dir.join(ref_path).display());
        if let Some(common_dir) = resolve_common_git_dir(&git_dir) {
            println!("cargo:rerun-if-changed={}", common_dir.join(ref_path).display());
            println!("cargo:rerun-if-changed={}", common_dir.join("packed-refs").display());
        }
    }
}
```

Prefer explicit CI sha values when available, then fall back to git.

```rust
fn build_git_sha() -> Option<String> {
    std::env::var("SM_GIT_SHA")
        .ok()
        .and_then(short_sha)
        .or_else(|| std::env::var("GITHUB_SHA").ok().and_then(short_sha))
        .or_else(git_head_sha)
}
```

The fallback must read Git metadata through the same checkout aware resolver. Try the worktree git dir first for detached heads and worktree specific refs, then the common git dir for branch refs and packed refs.

```rust
fn git_head_sha() -> Option<String> {
    let git_dir = resolve_git_dir()?;
    let head = std::fs::read_to_string(git_dir.join("HEAD")).ok()?;
    let trimmed = head.trim();
    if let Some(ref_path) = trimmed.strip_prefix("ref: ") {
        for dir in git_lookup_dirs(&git_dir) {
            let ref_file = dir.join(ref_path);
            if let Ok(sha) = std::fs::read_to_string(&ref_file) {
                return short_sha(sha.trim().to_string());
            }
        }
        for dir in git_lookup_dirs(&git_dir) {
            if let Ok(packed) = std::fs::read_to_string(dir.join("packed-refs")) {
                for line in packed.lines() {
                    if let Some((sha, name)) = line.split_once(' ')
                        && name == ref_path
                    {
                        return short_sha(sha.to_string());
                    }
                }
            }
        }
        None
    } else {
        short_sha(trimmed.to_string())
    }
}

fn workspace_git_path() -> PathBuf {
    PathBuf::from("../../.git")
}

fn resolve_git_dir() -> Option<PathBuf> {
    let git_path = workspace_git_path();
    if git_path.is_dir() {
        return Some(git_path);
    }

    let git_file = std::fs::read_to_string(&git_path).ok()?;
    let git_dir = git_file.trim().strip_prefix("gitdir: ")?;
    let git_dir = PathBuf::from(git_dir);
    if git_dir.is_absolute() {
        Some(git_dir)
    } else {
        Some(git_path.parent().unwrap_or_else(|| Path::new(".")).join(git_dir))
    }
}

fn resolve_common_git_dir(git_dir: &Path) -> Option<PathBuf> {
    let common_dir = std::fs::read_to_string(git_dir.join("commondir")).ok()?;
    let common_dir = PathBuf::from(common_dir.trim());
    if common_dir.is_absolute() {
        Some(common_dir)
    } else {
        Some(git_dir.join(common_dir))
    }
}

fn git_lookup_dirs(git_dir: &Path) -> Vec<PathBuf> {
    let mut dirs = vec![git_dir.to_path_buf()];
    if let Some(common_dir) = resolve_common_git_dir(git_dir)
        && common_dir != git_dir
    {
        dirs.push(common_dir);
    }
    dirs
}
```

Replace `SM_` with the project's prefix consistently across the env var, the emitted rustc env, and the const exported from the CLI crate.

## CLI Wiring

Expose the compiled stamp from the CLI crate.

```rust
pub const VERSION: &str = env!("SM_CLI_VERSION");
```

Wire Clap to use the product display name and the compiled version.

```rust
#[derive(Debug, Parser)]
#[command(
    name = "sm",
    display_name = "session-matters",
    about = "session-matters control plane",
    version = crate::VERSION,
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}
```

Usage and subcommands stay on the executable name. `--version` prints the product name.

## Install Recipes

Build the package that owns the binary. Do not build the entire workspace for local installs. Set the sha flag only on the local install build. Make `just install` reinstall the release binary so a developer can revert from a local build with one command.

```just
SM_LOCAL_BIN := env("SM_LOCAL_BIN", env("HOME") / ".cargo/bin/sm")

install: install-release

build-local:
    SM_VERSION_INCLUDE_GIT_SHA=1 cargo build -p sm-cli --bin sm --profile install-local

build-install-release:
    SM_VERSION_INCLUDE_GIT_SHA=0 cargo build -p sm-cli --bin sm --release

install-local: build-local
    @just _install-bin target/install-local/sm

install-release: build-install-release
    @just _install-bin target/release/sm

_install-bin src:
    @set -eu; \
    src="$(pwd)/{{src}}"; \
    dest="{{SM_LOCAL_BIN}}"; \
    case "$dest" in /*) ;; *) dest="$(pwd)/$dest";; esac; \
    if [ "$src" = "$dest" ]; then \
        echo "Built $src"; \
    else \
        mkdir -p "$(dirname "$dest")"; \
        install -m 755 "$src" "$dest"; \
        echo "Installed $dest"; \
    fi; \
    "$dest" --version
```

After copying the binary, run `"$dest" --version`. The important check is the destination binary, not the build output the recipe just produced.

Replace `sm-cli`, `sm`, `SM_LOCAL_BIN`, and `SM_VERSION_INCLUDE_GIT_SHA` with the workspace package, binary, install variable, and project env-var prefix.

`install-local` and `install-release` write to the same destination. Switching means running the other install recipe, then checking `--version`.

## Tests

Add a focused test for the default binary built by `cargo test`.

```rust
#[test]
fn root_version_flag_prints_session_matters_package_version() {
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_sm"))
        .arg("--version")
        .output()
        .expect("sm --version");

    assert!(output.status.success(), "sm --version failed: {output:?}");
    assert!(output.stderr.is_empty(), "stderr was not empty: {output:?}");

    let stdout = String::from_utf8(output.stdout).expect("version output utf8");
    let expected = format!("session-matters {}\n", env!("CARGO_PKG_VERSION"));
    assert_eq!(stdout, expected);
}
```

Add recipe coverage for the switching contract.

```rust
#[test]
fn install_recipe_switches_to_release_install() {
    let justfile = read_workspace_justfile();
    assert!(
        justfile.contains("\ninstall: install-release\n"),
        "just install must reinstall the release binary"
    );
}

#[test]
fn install_helper_prints_installed_binary_version() {
    let justfile = read_workspace_justfile();
    assert!(
        justfile.contains("\"$dest\" --version"),
        "install helper must print the version from the installed binary"
    );
}
```

## Verification Recipe

Verify both install paths against one temporary destination.

```bash
tmpdir="$(mktemp -d)"
timeout 180s env SM_LOCAL_BIN="$tmpdir/sm" just install-local
"$tmpdir/sm" --version
timeout 300s env SM_LOCAL_BIN="$tmpdir/sm" just install
"$tmpdir/sm" --version
```

Expected shape:

```text
session-matters 0.1.2+c0c62d1
session-matters 0.1.2
```

Run the repo gate before claiming the contract is in place.

```bash
just check && just build && just test
```

## Investigation Recipe (LTO Stall)

If `just install-local` is slow or stalls, the cause is usually a full-LTO release profile and an install recipe that builds `--workspace --release` instead of one binary under a focused profile.

1. Confirm what the current recipe does.

   ```bash
   just --dry-run install-local
   ```

2. Reproduce without overwriting the real installed binary.

   ```bash
   tmpdir="$(mktemp -d)"
   timeout 180s env SM_LOCAL_BIN="$tmpdir/sm" just install-local
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

5. Add `[profile.install-local]` and a focused `build-local` recipe.

6. Factor copy logic into one helper used by both install recipes.

Observed on runtime-matters on 2026-05-18: full-LTO release profile in `install-local` killed a 180s timeout. After adding `[profile.install-local]` and `-p rtm-cli --bin rtm`, first install completed in 51.38s and cached installs in 0.89s.

## Guardrails

- Do not make `--version` depend on a daemon, socket, or network call. It is process local.
- Do not append the git sha to release installs.
- Do not introduce a separate local label in place of the package version. The package version stays the base in both outputs.
- Do not duplicate version formatting across runtime code and the build script. One stamp, one source.
- Do not assume `.git` is a directory. Linked worktrees use a `.git` file and often store branch refs under the common git directory.
- Keep service metadata commands separate from binary identity.
- Do not weaken `[profile.release]` to make local installs faster. Add `[profile.install-local]` instead.
- Do not point `install-local` at `target/release/<bin>` after moving the build to a custom profile.
- Do not install over the live user binary until a temporary destination install works.
- Build the package that owns the binary with `-p <package> --bin <binary>` instead of rebuilding every workspace target.
- Do not leave `just install` as setup only when it should switch from local back to release.
- Do not trust build output alone. Check the installed binary with `--version`.

## Good Completion Evidence

An acceptable closeout includes:

- The `[profile.install-local]` block in `Cargo.toml`.
- The new install recipe set in `justfile`, including the `_install-bin` helper with `"$dest" --version`.
- The `build.rs` version emit function, the exported `VERSION` const, and the clap `display_name` + `version` attrs.
- Worktree proof when applicable: `just install-local` from a linked worktree prints `<package-version>+<7-char-sha>`.
- A temp destination release install result.
- A temp destination local install result.
- The exact `--version` output for both installs (release without sha, local with sha).
- The `--version` clap test and the two justfile contract tests passing.
- The repo gate result (`just check && just build && just test`).
