# littleorgans dry fix P2: session misc and lilo cli

## Files changed

| Path | Change |
| --- | --- |
| `internal/session/core/src/tool_sources.rs` | Added the shared tool source block appender and used it when reading source files. |
| `internal/session/core/src/tool_contracts/registry.rs` | Reused the shared tool source block appender for bundled generated sources. |
| `internal/session/core/src/paths.rs` | Added the shared lifecycle transcript path extractor. |
| `internal/session/driver/src/conv.rs` | Delegated lifecycle transcript path extraction to session core while preserving the existing crate internal wrapper for current callers. |
| `internal/session/store/src/sqlite/spawn_intents.rs` | Removed local lifecycle transcript path extraction and used session core. |
| `crates/lilo-im-core/src/types.rs` | Introduced one macro owned action list that defines both `Action` and `Action::ALL`. |
| `crates/lilo/src/cli/mod.rs` | Moved command name ownership into one command macro, switched help grouping to clap headings, and added shared lilo path resolution. |
| `crates/lilo/src/cli/daemon.rs` | Reused shared lilo path resolution. |
| `crates/lilo/src/cli/doctor.rs` | Reused shared lilo path resolution and factored database probe construction. |
| `internal/runtime/app/src/cli/version.rs` | Added a shared simple RuntimeRpc request plus emit helper. |
| `internal/runtime/app/src/cli/doctor.rs` | Reused the shared RuntimeRpc request plus emit helper. |

## New shared API signatures

| Crate | API |
| --- | --- |
| `lilo-session-core` | `pub fn paths::lifecycle_transcript_path(lifecycle: &Lifecycle) -> Option<PathBuf>` |
| `lilo` | `pub(crate) fn cli::resolve_lilo_paths() -> Result<LiloPaths, LiloPathError>` |
| `lilo-runtime-app` | `pub(crate) async fn cli::version::emit_rpc_response<T>(output_args: &OutputArgs, rpc: RuntimeRpc, extract: impl FnOnce(RuntimeResponse) -> Result<T>) -> Result<()> where T: CliOutput` |

## Dependencies

No dependency changes were needed.

## Verification

Clean clippy runs:

- `cargo clippy -p lilo-session-core --all-targets -- -D warnings`
- `cargo clippy -p lilo-session-driver --all-targets -- -D warnings`
- `cargo clippy -p lilo-session-store --all-targets -- -D warnings`
- `cargo clippy -p lilo-im-core --all-targets -- -D warnings`

Blocked clippy runs:

- `cargo clippy -p lilo-runtime-app --all-targets -- -D warnings`
- `cargo clippy -p lilo --all-targets -- -D warnings`
- Combined lane command: `cargo clippy -p lilo-session-core -p lilo-session-driver -p lilo-session-store -p lilo-im-core -p lilo -p lilo-runtime-app --all-targets -- -D warnings`

All blocked runs stop before checking the touched `lilo-runtime-app` or `lilo` changes because dependency `lilo-runtime-daemon` fails outside this lane:

```text
error[E0599]: no method named `context` found for enum `std::result::Result<T, E>` in the current scope
  --> internal/runtime/daemon/src/service.rs:96:24
   |
96 |             task.await.context("periodic reconciliation task failed")?;
   |                        ^^^^^^^
help: trait `Context` which provides `context` is implemented but not in scope; perhaps you want to import it
   |
1 + use anyhow::Context;
```

Per the shared worktree rule, this was not edited because `internal/runtime/daemon/src/service.rs` is outside this lane.

## Left

`lilo-runtime-app` and `lilo` clippy need to be rerun after the runtime daemon dependency error is fixed by its owner. `fmm generate` was not run because the squad rules reserve shared/generated state for the orchestrator.
