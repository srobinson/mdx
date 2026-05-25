# littleorgans dry fix: config identity

## Files changed

| Path | Change |
| --- | --- |
| `crates/lilo-paths/src/lilo.rs` | Added the shared home expansion policy and coverage for bare `~`, `~/`, non matching `~user`, and non home paths. |
| `crates/lilo-paths/src/lib.rs` | Re exported the new path policy function. |
| `internal/session/core/src/agent_config.rs` | Replaced local home expansion with the shared lilo paths policy while preserving fallback behavior when HOME is unavailable. |
| `internal/session/daemon/src/agent_config.rs` | Replaced local home expansion with the shared lilo paths policy and retained the structured HOME required error. |
| `crates/lilo-im-core/src/types.rs` | Added the shared session ResourceSpec constructor and coverage for its default field behavior. |
| `internal/runtime/daemon/src/identity.rs` | Replaced duplicated session ResourceSpec construction with the shared constructor. |
| `internal/session/daemon/src/identity_client.rs` | Kept the existing public session helper and delegated it to the shared constructor. |

## New shared API signatures

| Crate | API |
| --- | --- |
| `lilo-paths` | `pub fn expand_home_path(value: &str, home: Option<&Path>) -> Option<PathBuf>` |
| `lilo-im-core` | `impl ResourceSpec { pub fn session(session_id: Uuid) -> Self }` |

## Dependencies

No dependency changes were needed. All touched consumers already depended on `lilo-paths` or `lilo-im-core` as required.

## Verification

`cargo check -p lilo-paths -p lilo-im-core -p lilo-session-core -p lilo-session-daemon -p lilo-runtime-daemon`

Result: OK. Finished in 13.93s.

## Left

No code follow up is left in this lane. `fmm generate` was not run because this shared worktree instruction allows edits only in the assigned lane and the orchestrator owns generated or shared navigation state updates.
