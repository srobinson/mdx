---
title: Lilo help examples reference review
type: research
tags: [littleorgans, lilo, cli, help, codegen, review]
summary: Final review of the `lilo run --help` reference verified all consensus changes and signed off cleanly.
status: active
source: codebase-analyst
confidence: high
created: 2026-06-02
updated: 2026-06-02
---

## Executive Summary

The `feat/lilo-help-examples` worktree adds generated long help and examples for `lilo run`, intended as the reference pattern for the main session verbs. The architecture is sound: authored TOML feeds xtask generation, generated Rust feeds Clap help and tests, and generated JSON carries the same surface. Final live verification confirmed all consensus changes were applied: the docker example uses bare `docker`, rendered examples shell quote argv elements, the parse test documents its scope, and dead `next_help_heading` attributes were removed.

## Project Metadata

- Language: Rust.
- CLI framework: Clap derive.
- Build and generation: Cargo workspace, `tools/xtask`, `just`, Moon CI.
- Critical dependencies in this change: `clap`, `serde`, `serde_json`, `lilo_rm_core`, `lilo_session_app`, `lilo_session_core`.
- Indexed topology observed by fmm: 382 indexed files, 54,344 LOC. The largest buckets are `internal/` at 295 files and `crates/` at 82 files.

## Architecture

The help surface has one authored source of truth.

1. `tools/schemas/cli.toml:22-49` declares the public `run` command, `long_about`, and four examples.
2. `tools/xtask/src/main.rs:196-211` deserializes `long_about` and `examples` into `CommandSpec` and `Example`.
3. `tools/xtask/src/main.rs:236-293` emits help constants, rendered example text, and `RUN_EXAMPLE_ARGS` for tests.
4. `crates/lilo/src/cli/mod.rs:205-231` wires `RUN_LONG_ABOUT` and `RUN_EXAMPLES` into the Clap `Run` variant.
5. `crates/lilo/src/cli/generated_help.rs` and `crates/lilo/src/cli/generated_schema.rs` are generated outputs, not the authored edit surface.

The runtime contract used by the examples lives outside the top level `lilo` crate. `RunArgs` is defined in `internal/session/app/src/cli/cli_def.rs:58-75`; `run` validates isolation and mounts in `internal/session/app/src/cli/run.rs:15-27`, then creates a `SpawnRequest` in `internal/session/app/src/cli/run.rs:41-99`. Runtime value parsing for isolation, target, and mounts lives in `crates/lilo-rm-core`.

## Key Patterns

- Good DRY move: examples as argv arrays give one structured source for rendered help, generated JSON, and parse tests.
- Good boundary: generated files reflect `tools/schemas/cli.toml`; proposed changes should target TOML or xtask, not generated Rust or JSON.
- Good heading fix: root grouping is produced by the generated root template, so per subcommand `next_help_heading` labels were the wrong mechanism.
- Propagation risk: argv arrays are correct storage, but display must be shell aware. Joining with spaces is not safe for examples with message text, selectors, paths with spaces, or shell metacharacters.

## Detailed Findings

### Filed state

`git diff main...HEAD` was empty in the checkout, while the worktree had six modified files: `tools/schemas/cli.toml`, `tools/xtask/src/main.rs`, `crates/lilo/src/cli/mod.rs`, and three generated files. The review used the current worktree diff because that is where the filed change existed.

### Example accuracy

- `--target tmux:work:0.1` is correct. `SpawnTarget::from_str` accepts only `headless` or `tmux:` prefixed values in `crates/lilo-rm-core/src/types/spawn.rs:252-264`. `TmuxAddress::from_str` parses `SESSION:WINDOW.PANE` in `crates/lilo-rm-core/src/types/spawn.rs:27-47`.
- `--mount /repo:/work:rw` is syntactically valid. `RunArgs` declares `--mount` as `HOST:CONTAINER[:ro|:rw]` in `internal/session/app/src/cli/cli_def.rs:65-70`; `MountSpec::from_str` accepts `rw` in `crates/lilo-rm-core/src/types/spawn.rs:149-182`.
- `--namespace team-a` is syntactically valid. `Namespace::new` validates a slug and rejects reserved prefixes in `internal/session/core/src/namespace.rs:23-32`.
- `--label task=alp-123` is syntactically valid. `Label::from_str` splits `key=value` in `internal/session/core/src/label.rs:16-24`, and `parse_label_token` rejects only empty trimmed parts in `internal/session/core/src/label.rs:47-53`.
- The docker example now uses `--isolation docker` in `tools/schemas/cli.toml:43-45` and the generated help. This resolves the prior redundant `docker:default` wording. `IsolationPolicy::from_str` maps `docker` to the default docker profile and `docker:PROFILE` to a named profile in `crates/lilo-rm-core/src/isolation.rs:39-58`; runtime preflight accepts `None`, `default`, `own-init`, `allow-root`, and `arm64-manifest-escape` in `internal/runtime/daemon/src/spawn_preflight.rs:80-110`.

### Generator and schema design

The schema shape is good. `CommandSpec` owns `long_about` and `examples` with serde defaults in `tools/xtask/src/main.rs:196-211`, and `cli_surface_json` serializes public commands in `tools/xtask/src/main.rs:333-355`. Including examples in `lilo_cli_surface.json` is useful because the JSON mirrors the user visible CLI contract.

The renderer now keeps argv as the authored source and renders each argument through `shell_quote` in `tools/xtask/src/main.rs:266-294`. Single token examples still render bare, while future examples with spaces or shell metacharacters remain copy paste safe.

### Heading fix

Removing `next_help_heading` from the command variants is correct. The root help grouping comes from `root_help_template` in `tools/xtask/src/main.rs:319-331`; the top level variants now avoid leaking root group headings into subcommand option sections in `crates/lilo/src/cli/mod.rs:205-249`. Live search found no remaining `next_help_heading` in `crates/lilo/src/cli/mod.rs`.

### Test honesty

`run_examples_parse_as_valid_invocations` in `crates/lilo/src/cli/mod.rs:305-315` remains a useful Clap parse freshness test. Its new comment documents the intended scope: flag existence, required args, and FromStr flag syntax only. That resolves the consensus condition by making semantic review responsibility explicit for fields such as `--target` and docker profile behavior.

## Dependencies

- `clap`: CLI derive, help rendering, parse tests.
- `serde` and `serde_json`: TOML to Rust struct deserialization, generated JSON surfaces.
- `lilo_rm_core`: isolation, mount, target, and docker launch semantics.
- `lilo_session_core`: namespace and label semantics.
- `lilo_session_app`: session CLI definitions and `run` request construction.

## Relevance to Helioy

This change is the template for higher quality, generated command help across the `lilo` surface. The right pattern is one authored command registry, generated Rust and JSON surfaces, parse tested argv examples, rendered help that remains shell correct, and explicit review scope for semantic example correctness.

## Verification

Ran the requested and targeted verification commands on 2026-06-02:

- `cargo run -q -p lilo -- run --help`: rendered the new long help and examples.
- `cargo run -q -p lilo -- --help`: confirmed root grouping remains intact.
- `cargo run -q -p xtask -- codegen --check`: passed.
- `cargo test -q -p lilo`: passed, 16 unit tests plus 2 integration or doc test binaries.
- `cargo clippy -q -p lilo -p xtask --all-targets -- -D warnings`: passed.
- `rg "next_help_heading" crates/lilo/src/cli/mod.rs`: no matches.

## Final Signoff

After live reread and verification on 2026-06-02, sent the exact clean phrase to `littleorgans:general:5:2.1`:

`I sign off on the lilo help reference as currently filed`

## Open Questions

- Should `-c, --config <CONFIG>` get help text before calling this surface kubectl grade? It appears blank in both root and run help, but it is outside the reviewed diff.
- Should target validation move into a Clap value parser in a later cleanup, or remain daemon validated for forward compatibility with future target shapes?
