---
title: Rust workspace CLI version stamps
type: playbooks
tags: [rust, cargo, clap, version, git-sha, install-local, install-release, binary]
summary: Build-time version stamp contract for Rust workspace CLIs with local and release install paths
status: active
project: runtime-matters
related: [rust-workspace-install, rust-binary-workspace-cargo-dist]
confidence: high
---

# Rust workspace CLI version stamps

Use this when a Rust workspace CLI needs a root `--version` flag that identifies the installed binary without requiring a daemon, socket, network call, or database.

## Contract

Root `--version` is process local. It should be handled by the CLI parser before any service connection or runtime setup is required.

Use the product name in version output, even when the executable name is shorter.

```text
runtime-matters 0.1.5
runtime-matters 0.1.5+7b97019
```

Release install output:

```text
<product-name> <package-version>
```

Local install output:

```text
<product-name> <package-version>+<7-char-sha>
```

The sha records the source revision used when `install-local` was run. Release installs should print only the package version.

If the project also has daemon or service metadata, keep that on a separate command. In runtime-matters, `rtm --version` identifies the local binary, while `rtm version` asks `rtmd` for JSON metadata.

## Build Stamp

Emit one compile-time version string from the CLI crate build script.

Default to the package version. Append the git sha only when `RTM_VERSION_INCLUDE_GIT_SHA=1`.

```rust
fn emit_cli_version() {
    emit_git_rerun_directives();
    println!("cargo:rerun-if-env-changed=RTM_GIT_SHA");
    println!("cargo:rerun-if-env-changed=GITHUB_SHA");
    println!("cargo:rerun-if-env-changed=RTM_VERSION_INCLUDE_GIT_SHA");

    let package_version = std::env::var("CARGO_PKG_VERSION").expect("CARGO_PKG_VERSION set");
    let version = match (include_git_sha(), build_git_sha()) {
        (true, Some(sha)) => format!("{package_version}+{sha}"),
        _ => package_version,
    };
    println!("cargo:rustc-env=RTM_CLI_VERSION={version}");
}
```

Watch git ref files so local rebuilds pick up a changed commit when the local install profile is rebuilt.

```rust
fn emit_git_rerun_directives() {
    println!("cargo:rerun-if-changed=../../.git/HEAD");
    println!("cargo:rerun-if-changed=../../.git/packed-refs");

    let Some(head) = std::fs::read_to_string("../../.git/HEAD").ok() else {
        return;
    };
    if let Some(ref_path) = head.trim().strip_prefix("ref: ") {
        println!("cargo:rerun-if-changed=../../.git/{ref_path}");
    }
}
```

Prefer explicit CI sha values when available, then fall back to git.

```rust
fn build_git_sha() -> Option<String> {
    std::env::var("RTM_GIT_SHA")
        .ok()
        .and_then(short_sha)
        .or_else(|| std::env::var("GITHUB_SHA").ok().and_then(short_sha))
        .or_else(git_head_sha)
}
```

## CLI Wiring

Expose the compiled stamp from the CLI crate.

```rust
pub const VERSION: &str = env!("RTM_CLI_VERSION");
```

Wire Clap to use the product display name and the compiled version.

```rust
#[derive(Debug, Parser)]
#[command(name = "rtm")]
#[command(display_name = "runtime-matters", version = crate::VERSION)]
pub struct Cli {
    #[command(subcommand)]
    command: Command,
}
```

This keeps usage and subcommands on the executable name while making `--version` print the product name.

## Install Recipe Wiring

Set the sha flag only on the local install build.

```just
build-local:
    RTM_VERSION_INCLUDE_GIT_SHA=1 cargo build -p rtm-cli --bin rtm --profile install-local

build-install-release:
    RTM_VERSION_INCLUDE_GIT_SHA=0 cargo build -p rtm-cli --bin rtm --release
```

Do not use labels such as `local-version`. The package version stays the base in both outputs.

## Tests

Add a focused test for the default binary built by `cargo test`.

```rust
#[test]
fn root_version_flag_prints_runtime_matters_package_version() {
    let output = std::process::Command::new(env!("CARGO_BIN_EXE_rtm"))
        .arg("--version")
        .output()
        .expect("rtm --version");

    assert!(output.status.success(), "rtm --version failed: {output:?}");
    assert!(output.stderr.is_empty(), "stderr was not empty: {output:?}");

    let stdout = String::from_utf8(output.stdout).expect("version output utf8");
    let expected = format!("runtime-matters {}\n", env!("CARGO_PKG_VERSION"));
    assert_eq!(stdout, expected);
}
```

Then verify install switching with a temporary destination.

```bash
tmpdir="$(mktemp -d)"
timeout 300s env RTM_LOCAL_BIN="$tmpdir/rtm" just install-release
"$tmpdir/rtm" --version
timeout 180s env RTM_LOCAL_BIN="$tmpdir/rtm" just install-local
"$tmpdir/rtm" --version
```

Expected shape:

```text
runtime-matters 0.1.5
runtime-matters 0.1.5+7b97019
```

Run the repo gate before closing out.

```bash
just check && just build && just test
```

## Guardrails

- Do not make `--version` depend on a daemon or socket.
- Do not append git sha for release installs.
- Do not use a separate local label in place of the package version.
- Do not duplicate version formatting across runtime code and build scripts.
- Keep service metadata commands separate from binary identity.
