---
title: lilo doctor daemon/client version-skew detection — scoping
type: research
tags: [littleorgans, lilo-doctor, version-skew, roadtest, session-daemon, scoping]
summary: lilod never reports its build version over the wire and lilo doctor bare-connects; reuse SessionRpc::Doctor + inject version through compose to detect skew.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-30
updated: 2026-05-30
---

# lilo doctor — daemon/client version-skew detection

## Executive Summary

`lilo doctor` cannot detect daemon/client build-version skew. `DaemonHealth::collect`
(`crates/lilo/src/cli/doctor.rs:101`) is a bare `UnixStream::connect().is_ok()` with no
version RPC, and the session daemon (`lilod`) never reports its own build version over the
socket. A user who `cargo install`s a new `lilo` while an old `lilod` keeps running sees
`daemon: reachable, warnings: none` with zero signal (the bug behind commit 3096992 / item 1).
The fix is small and DRY: surface the daemon build version on the **existing** `SessionRpc::Doctor`
round-trip and compare it against the client's own `VERSION` const.

## Architecture (as found)

- **Client version source.** `crates/lilo/src/main.rs:10` → `pub const VERSION = env!("LILO_CLI_VERSION")`.
  The env var is a compile-time const emitted by `crates/lilo/build.rs:2` calling
  `lilo_build_support::emit_cli_version("LILO_CLI_VERSION")`, which produces
  `CARGO_PKG_VERSION` + an **opt-in** `+<short-sha>` suffix
  (`crates/lilo-build-support/src/lib.rs:10-25`). The suffix appears only when
  `LILO_VERSION_INCLUDE_GIT_SHA` is truthy (`include_git_sha`, ibid:71-78); the sha comes
  from `LILO_GIT_SHA`/`GITHUB_SHA`, else `git rev-parse --short=7 HEAD`. Same pattern for
  session-app (`SM_CLI_VERSION`, `internal/session/app/src/lib.rs:18`) and runtime-app
  (`RTM_CLI_VERSION`). All sibling crates in one `cargo build` share the workspace version
  and the same HEAD sha, so `LILO_CLI_VERSION == SM_CLI_VERSION` byte-for-byte per build.

- **`lilod` identity.** `lilo daemon start` → `lilo_session_app::compose::run_from_env()`
  (`crates/lilo/src/cli/daemon.rs:31`); `run_from_env` → `run(LiloPaths)` (`compose.rs:62`,
  no version param today). So the daemon **is** the `lilo` binary in daemon mode — its build
  version equals the client's `LILO_CLI_VERSION` for any given build.

- **Wire surface.** Session RPC enum `SessionRpc` (`internal/session/core/src/proto/rpc.rs:16`)
  has **no** `Version` variant. `DoctorResponse` (`internal/session/core/src/proto/doctor.rs:6-12`)
  carries `status`, `runtime`, `runtime_matters`, `findings` — **no build-version field**.
  Only the **runtime** version reaches the wire: `RuntimeRpc::Version` → `VersionPayload`
  (`crates/lilo-rm-core/src/proto.rs`), and `lilo_rm_core::DoctorResponse.version`
  (`crates/lilo-rm-core/src/admin.rs:211`) is nested under session
  `RuntimeDoctorReport.doctor`. The session daemon builds its Doctor response at
  `internal/session/daemon/src/polish.rs:79`.

- **Two doctors.** `crates/lilo/src/cli/doctor.rs` (the roadtest target) does **local-only**
  probes and never calls the daemon. The legacy `sm doctor`
  (`internal/session/app/src/cli/doctor.rs:8-9`) **does** issue `SessionRpc::Doctor` via a
  session client — the reusable call pattern for the fix.

## Proposed fix (minimal, DRY)

Reuse the existing `SessionRpc::Doctor` round-trip — no new RPC.

1. **Proto:** add `daemon_version: String` to `DoctorResponse`
   (`internal/session/core/src/proto/doctor.rs`).
2. **Inject the version at startup.** The daemon crate (`internal/session/daemon`) **cannot**
   `env!("SM_CLI_VERSION")` (per-crate env, invisible there) and **must not** import the app's
   `VERSION` (layering cycle: app → daemon → core). Thread it instead: give
   `compose::run_from_env`/`run` a version param, have `lilo daemon start` pass `crate::VERSION`,
   and fill `daemon_version` in the handler at `polish.rs:79`. (Equivalently, `compose` lives in
   session-app and may pass `lilo_session_app::VERSION` — byte-equal per build.)
3. **Client probe:** replace the bare `UnixStream::connect` in `DaemonHealth::collect`
   (`crates/lilo/src/cli/doctor.rs:97-104`) with a `SessionRpc::Doctor` call; add
   `version: Option<String>` to `DaemonHealth` (doctor.rs:90-94).
4. **Compare + warn:** in `DoctorStatus::collect` (`crates/lilo/src/cli/doctor.rs:35-50`),
   compare `crate::VERSION` against `daemon_version`; on mismatch (when reachable) push to
   `self.warnings` (line 31) and render in `render_human` (52-80).

### Threshold

Trigger on **exact build-version inequality**. The failure mode is new-binary-vs-old-daemon, so
any difference warrants a warning. This is a **separate axis** from protocol gating:
`RUNTIME_PROTOCOL_VERSION="0.6"` (`crates/lilo-rm-core/src/version.rs:8`) is minor-gated
smd↔rtmd via `RuntimeClient::check_protocol_version` (`crates/lilo-rm-client/src/lib.rs:189`).
Doctor should not reimplement protocol-minor logic; it should report build skew.

Suggested copy: `warn: client lilo {c} but daemon lilod {d} — restart the daemon (lilo daemon stop && lilo daemon start)`.

## Risks / gotchas

- **The `+sha` suffix is build-time opt-in.** A plain release `cargo install` without
  `LILO_VERSION_INCLUDE_GIT_SHA` emits bare `0.8.0` (no sha), so two different `0.8.0` builds
  compare **equal** and skew is invisible to a string compare — the roadtest scenario itself.
  Mitigation: release/CI (release-plz) must set `LILO_VERSION_INCLUDE_GIT_SHA=1`, else the
  warning silently under-fires on same-version rebuilds.
- **Version is compile-time embedded, not runtime.** A long-running daemon reports the version
  it was *built* from — which is the desired signal.
- **Layering.** Resist `env!` in the daemon crate or importing app `VERSION` into it; inject.

## Open questions

- Should the warning also escalate `doctor` exit status, or stay advisory? (Current
  `DoctorStatus` has no non-zero-exit path for warnings; mirror existing behavior unless the
  pair decides otherwise.)
- Do release builds already set `LILO_VERSION_INCLUDE_GIT_SHA`? Verify in CI/release-plz config
  before relying on `+sha` for skew detection.
