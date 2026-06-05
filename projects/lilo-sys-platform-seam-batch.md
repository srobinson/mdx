---
title: lilo-sys Platform Seam — MoE Local Batch Ledger
type: orchestration-ledger
status: active
branch: refactor/lilo-sys-platform-seam
orchestrator: littleorgans:general:9:4.1
started: 2026-06-01
---

# lilo-sys Platform Seam — Batch Ledger

Centralize the OS platform seam behind one published crate `lilo-sys` (the
PAL), mirroring Rust std's `sys/pal` model. Behaviour-preserving, Unix-family
only (Linux + macOS); Windows deferred (stub to `lilo-port` Unsupported). One
branch, N commits, one PR. Codex implements, Claude reviews, two-phase sign-off.

## Locked decisions

1. **Placement:** `crates/lilo-sys`. crates/ = `publish = true` (empirical:
   lilo-paths/lilo-common true, lilo-port internal false). So lilo-sys is a
   PUBLISHED crate.
2. **Selector:** `cfg_select!` (std macro, Rust 1.95 pinned — confirmed
   `rustc 1.95.0`). No `cfg-if` dep needed.
3. **Defer:** no `interprocess`/`process-wrap`, no real `windows.rs` yet. Back
   the seam with relocated Unix code. BUT consolidate the existing Linux/macOS
   split now (pidfd vs kqueue, SO_PEERCRED vs getpeereid).
4. **Creds boundary → F2 Phase A panel decision** (not pre-locked).

## Open forks routed to F1 Phase A panel

- **Error dep / publish:** lilo-sys is publish=true, so it cannot depend on
  `lilo-port` (publish=false) or `lilo-rm-core` (runtime domain). Resolve:
  (a) lilo-sys carries its own `thiserror` error (`Unsupported` etc.), OR
  (b) lilo-port goes publish=true, OR (c) lilo-sys relocates to internal/.
  Default lean: (a) — keep lilo-sys self-contained and publishable.
- **Extraction boundary:** current `lilo-runtime-platform` depends on
  `lilo-rm-core` for `RuntimeSignal`/`KillOutcome` (signal.rs) and
  `TmuxAddress`/`PaneSnapshot`/`LaunchEnv`/`CaptureError`/`strip_ansi_escapes`
  (tmux.rs). lilo-sys must NOT pull those. Default lean: raw OS primitives
  (pidfd, kqueue, process, process_exit, `kill(pid, signum)`) move to
  lilo-sys; `tmux.rs` and the `RuntimeSignal`→signum mapping STAY in runtime
  and call lilo-sys primitives.

## Target layout (lilo-sys)

```
crates/lilo-sys/src/
  lib.rs            # OS-agnostic surface; re-exports sys::*; NO os cfg here
  error.rs          # own thiserror error incl. Unsupported (decision F1.a)
  process.rs        # surface: start_time, pid_alive, ...
  process_exit.rs   # surface: exit watcher
  signal.rs         # raw kill(pid, signum) primitive only
  creds.rs          # peer_cred(fd) -> PeerCred ; current_uid()   (F2)
  ipc.rs            # listener/stream surface                      (F3)
  sys/
    mod.rs          # cfg_select!: unix | windows(stub) | _ unsupported
    unix/
      mod.rs        # POSIX-common + cfg_select! delegating the 2 divergent fns
      linux.rs      # pidfd, SO_PEERCRED
      macos.rs      # kqueue, getpeereid
    windows.rs      # -> Unsupported stub
    unsupported.rs
  os/               # opt-in raw extensions, gated (AsRawFd etc.)
```

## Items (grouped by coupling)

### F1 — lilo-sys stand-up + primitive migration  [WARROOM]
- Phase A adjudicates: error/publish fork + extraction boundary (above).
- Phase B: create crate; move pure primitives into sys/{unix/{linux,macos}};
  leave tmux + RuntimeSignal mapping in runtime; delete lilo-runtime-platform;
  rewire internal/runtime imports. May split into 2 commits in-warroom.
- Sign-off suffix: "lilo-sys stand-up".
- Acceptance: `just check && just build && just test`; `rg 'cfg\(.*(unix|windows|target_os)' crates/lilo-sys` shows the seam ONLY in sys/.

### F2 — creds seam + DDD split  [WARROOM]
- Phase A = creds boundary (decision #4): lilo-sys owns `peer_cred(fd)->PeerCred`
  + `current_uid()`; lilo-im-core maps to `Principal`.
- Phase B: implement in lilo-sys (linux SO_PEERCRED / macos getpeereid),
  refactor crates/lilo-im-core/src/peer_creds.rs to consume it; retire 6
  `nix::unistd::getuid()` sites (runtime/daemon {service,api,server/runner,
  server/state}; session/daemon {server,service}) to one `current_uid()`.
- Sign-off suffix: "creds seam".

### F3 — IPC + shutdown-signal seam (ALL callers)  [WARROOM]
- Shared surface defined AND all callers rerouted atomically.
- Define lilo_sys::ipc (UnixListener/UnixStream bind+connect; IpcStream =
  AsRawFd+AsyncRead+AsyncWrite; bind sets NO socket mode — none today) +
  lilo_sys::signal::on_shutdown() (SIGTERM + SIGINT/ctrl_c BOTH). Unix-only.
- AUTHORITATIVE SCOPE (IDENTIFIER scan; reconciled twice — see lesson):
  NET (9): crates/lilo-rm-client/src/lib.rs, crates/lilo-im-core/src/peer_creds.rs
  (extract &UnixStream->fd/AsFd), crates/lilo/src/cli/doctor.rs,
  internal/session/daemon/src/{socket.rs, server.rs},
  internal/runtime/daemon/src/{shim_socket.rs(async+blocking), handler.rs,
  server/runner.rs}, internal/session/app/src/compose.rs.
  SIGNAL (2): session/app/src/compose.rs, runtime/daemon/src/server/runner.rs.
  OUT OF SCOPE: all tests + *test_support* (incl runtime/daemon/src/
  tmux_test_support.rs signal) — harnesses legitimately build raw sockets.
- accept-loop + prepare/remove-socket stay in daemons; path policy in lilo-paths.
- F5 seam-lint MUST exclude tests + *test_support* and will FAIL if any raw unix
  IPC/signal remains in the 9 prod files.
- May land as 1-3 logical commits in one warroom, each moon-ci-green.
- LESSON: scope seam-reroute from an IDENTIFIER `rg` (\bUnixListener\b etc.), NOT
  qualified-path (tokio::net::Unix misses brace-imports `{UnixListener}` and bare
  idents). Mapper's 4-file list AND my path-regex correction were both short;
  engineer's identifier scan was authoritative.
- Sign-off suffix: "ipc+signal seam".

### F4 — spawn seam (shim)  [WARROOM]
- SCOPE (identifier scan): ONLY internal/runtime/app/src/cli/shim.rs.
  Unix bits to move: `std::os::unix::process::{CommandExt, ExitStatusExt}`
  (L1), `command.pre_exec(reset SIG_DFL)` (L196), raw `libc::signal(SIGTERM/
  SIGINT, ...)` sync handler install (set_signal_disposition L177+),
  exit-status signal extraction (ExitStatusExt).
- lilo_sys additions (sync, distinct from F3 async on_shutdown): pre_exec
  child-disposition helper (no CommandExt leak), sync signal-handler install,
  exit-status->signal extraction. KEEP the SIGTERM->SIGKILL grace/escalation
  POLICY in shim; kill primitive uses F1 lilo_sys::signal.
- Acceptance: moon ci; shim.rs has NO std::os::unix::process / libc::signal /
  SIG* / pre_exec; behaviour-preserving (grace window, SIGKILL escalation).
- Sign-off suffix: "spawn seam".

### F5 — creds cfg removal (NOT an fs seam)  [WARROOM]
- CORRECTION: the "filesystem seam" was a MIS-SCOPE. namespace_resolver.rs
  symlink/chmod (cfg(test) @L138+) and spawn_context.rs OsStringExt (cfg(test)
  @L137+) are TEST-ONLY inline #[cfg(test)] blocks — NO production fs seam exists.
  Orchestrator path-glob scan (!**/tests/**) missed inline cfg(test) a 3rd time
  (after doctor.rs, shim.rs). Reviewer's pre-D scope-check caught it.
- The ONLY real production residual: crates/lilo-im-core/src/peer_creds.rs L1/L6
  #[cfg(unix)] on `extract<S: AsRawFd>`.
- USER DECISION = REMOVE (centralize into lilo-sys), not allowlist.
- Approach: extract takes the lilo_sys IPC stream type (not S: AsRawFd); the
  platform gate moves INTO lilo_sys::creds (unix: as_raw_fd+SO_PEERCRED/getpeereid;
  windows: Unsupported stub via cfg_select). Touches peer_creds.rs + 3 prod
  extract callers + tests. RESULT: zero cfg(unix|windows) outside lilo-sys.
- namespace_resolver + spawn_context: UNTOUCHED (test code).
- Acceptance: moon ci; peer_creds.rs prod (excl cfg(test)) ZERO cfg/std::os; no drop.
- Sign-off suffix: "creds cfg removal".
- NB: F5 engineer (codex) bus address = memories:...:9:5.2 (not littleorgans:).
- LESSON (3rd time): scope from a scan that strips inline #[cfg(test)] blocks,
  NOT a path-glob. Verify "production" claims by reading the cfg(test) bounds.

### F6 — CI seam-lint + cfg hygiene  [WARROOM]  (LAST — the enforcement)
- scripts/check-seam.sh (mirror check-loc-limit.sh/check-provenance.sh), run by
  moon ci + justfile. After F5, can forbid ALL of: cfg(unix|windows|target_os|
  target_family), std::os::unix, UnixListener/UnixStream, tokio::signal::unix,
  libc::signal/raw SIG* handlers, pre_exec, CommandExt, ExitStatusExt, getuid,
  getpeereid, SO_PEERCRED, pidfd, kqueue — OUTSIDE crates/lilo-sys.
- MUST EXCLUDE: tests, benches, *test_support*, AND inline #[cfg(test)] blocks
  in src files (doctor.rs, shim.rs precedents — path-glob is insufficient).
- ALLOWLIST: internal/runtime/daemon/src/signal.rs RuntimeSignal->libc::SIG*
  mapping (F1 boundary: domain mapping stays in runtime).
- Add workspace [lints] deny unexpected_cfgs; confirm check-cfg clean.
- Sign-off suffix: "seam lint".

## Status

| Item | State | SHA | Notes |
|------|-------|-----|-------|
| baseline | green | — | `just regression` full run: 631 tests pass |
| F1 | COMPLETE (local) | a779976 | S|B signed; reviewer re-ran moon ci 631/631. Defects A/B + doc split folded in. CLAUDE.md incl (user). Push deferred to PR. |
| F2 | COMPLETE (local) | cd06283 | S|B signed; reviewer re-ran moon ci 631/631. Creds DDD boundary held; 11 getuid collapsed. Push deferred. |
| F3 | COMPLETE (local) | 3a3d901 | S|B signed; reviewer re-ran moon ci 631/631. Seam-lint EMPTY (8 files); session/daemon/socket.rs deleted; on_shutdown SIGTERM+SIGINT armed-once. Push deferred. |
| F4 | COMPLETE (local) | 84b67eb | S|B signed; reviewer re-ran moon ci 632/632. shim prod OS-clean; F1 boundary 0-diff; DRY shared helper; pre_exec MORE async-signal-safe (removed in-child format!). Push deferred. |
| F5 | COMPLETE (local) | f5c209f | S|B signed; reviewer re-ran moon ci 632/632. extract(&IpcStream) cfg-free; gate fully in lilo-sys. GOAL MET: zero production OS cfg/seam outside lilo-sys. Push deferred. |
| F6 | COMPLETE (local) | 71bd699 | S|B signed. python3 masker stripper; adversarial reintroduction 10/10; signal.rs allowlist SIG-scoped; moon ci 7 tasks exit 0. BATCH COMPLETE. Push deferred to PR (user approval). |

## BATCH COMPLETE 2026-06-01 — all 6 items S|B signed, local on refactor/lilo-sys-platform-seam
Commits: a779976(F1 seam) cd06283(F2 creds) 3a3d901(F3 ipc+signal) 84b67eb(F4 spawn) f5c209f(F5 creds cfg removal) 71bd699(F6 seam-lint).
Result: zero production OS seam/cfg outside crates/lilo-sys; enforced by moon ci check-seam.
## CI FAILURE (PR #17 first run) — macOS-only local gate missed Linux clippy
moon ci was green LOCALLY (macOS) but PR gate FAILED on Linux: clippy `-D warnings`
in crates/lilo-sys/src/sys/unix/linux.rs (never compiled locally — macOS builds
macos.rs, not linux.rs). Two lints:
- linux.rs:47 clippy::borrow_as_ptr (`&mut length` -> `&raw mut length`).
- linux.rs:149 clippy::unnecessary_wraps (watch_process_exit Result never Err) ->
  `#[allow]` justified: macos (kqueue fails) + unsupported (always Err) return
  Result, sys/unix/mod.rs re-exports all 3 uniformly, so Result is contract-required.
Fix verified via cross-clippy: `cargo clippy --target x86_64-unknown-linux-gnu -p lilo-sys --all-targets -- -D warnings`.
LESSON: a per-OS seam split means the local gate only exercises the host OS's arm.
"moon ci green" on macOS does NOT compile linux.rs. Verify cross-target locally
(cross-clippy / cross build) OR run a CI matrix (houseabsolute/actions-rust-cross)
BEFORE claiming a platform-split change is green. The seam refactor that centralized
per-OS code is exactly what created host-only blind spots.

Phase F: pushed origin/refactor/lilo-sys-platform-seam; PR #17
(https://github.com/littleorgans/littleorgans/pull/17), title "refactor: centralize
OS platform seams into lilo-sys crate"; squash auto-merge ARMED. Blocker = PR gate
CI pending (no approval required). Merges to main on green. Final local proof:
just check && build && test = 632/632, 0 skipped, no leaky.

## F1 locked design (Phase A signed off 2026-06-01)

- lilo-sys publish=true, own `thiserror` error (Unsupported etc.); NO lilo-port/lilo-rm-core dep.
- Primitives-only extraction → lilo-sys: pidfd, process, process_exit, kqueue, raw signal.
  STAY in runtime: tmux.rs, test_support, RuntimeSignal/KillOutcome mapping (call lilo-sys raw kill).
- sys/mod.rs `cfg_select!` unix | windows(stub) | _ unsupported.
- sys/unix/mod.rs POSIX-common + `cfg_select!` linux, macos, `_ => unsupported` (other-unix compile preserved — reviewer block 1).
- lilo-sys owns `SignalOutcome { Delivered, ProcessGone }`; runtime maps to `KillOutcome`, treats ProcessGone as error for send_signal (preserves current already_exited_ok=false — reviewer block 2).
- Phase B watch-item: send_signal ESRCH error-wording preservation; engineer to add boundary test.

## Known non-blocking issues (do NOT blame on later items)
- `moon ci` reports "1 leaky" on a PRE-EXISTING integration test (timing/fd
  cleanup). Present before F2, still counts passed, gate exit0. Investigate
  separately, out of this batch's scope. PARKED by user 2026-06-01.
  Suspects (tests/integration/tests/, the only daemon/socket-spawning tests):
  db_contract.rs, session_spawn_contract.rs, shutdown_contract.rs. To pinpoint
  later (when NO warroom is mid-build, to avoid socket collisions):
  `cargo nextest run -p <integration-pkg> 2>&1 | grep -i leak`.

## Protocol
Bus typed messages only: D, B, C, S, E, P, M. Exact sign-off phrases. Engineer
self-pushes after Phase B sign-off. Fresh warroom per item. Milestone `M` to
orchestrator `littleorgans:general:9:4.1` after every phase.

## F2 locked design (Phase A signed off 2026-06-01) — decision #4 resolved
- lilo-sys `creds.rs`: `PeerCred { uid, gid, pid: Option<u32> }` raw-only (pid
  Option because macOS getpeereid has no pid); `current_uid() -> u32`. NO domain
  dep; peer_cred takes BorrowedFd/RawFd, NOT tokio UnixStream.
- lilo-im-core keeps `Principal` + raw->Principal map (`principal_from_uid`,
  `Principal::Local`); callers wrap `current_uid()` with `Principal::local(..)`.
- peer_cred divergence in sys/unix/{linux SO_PEERCRED, macos getpeereid} behind
  cfg_select! `_ => unsupported`.
- Scope: ALL getuid under runtime/session daemon roots collapse to
  `lilo_sys::creds::current_uid()` (11 sites incl tests; reviewer affirmed > the
  6-prod estimate). Phase B verifies ZERO getuid remain there.
- Phase B watch-items: (1) lilo-sys Cargo.toml domain-dep-free + no tokio leak;
  (2) preserve macOS spawn_blocking wrap in lilo-im-core::extract; (3) tidy
  crates/lilo-im-core/tests/peer_creds.rs getuid.

## Commit hygiene + acceptance (ALL items)
- ACCEPTANCE GATE = `moon ci` (NOT just `just check && build && test`).
  just-cargo misses Moon project-graph drift; it passed F1 while `moon ci` was
  red. Any item that adds/deletes/moves a crate MUST run `moon ci`.
- COMMIT-FIRST: engineer commits, then sends `C|<item>|<sha>|...`; reviewer
  diffs the SHA, not the working tree.
- NO PER-ITEM PUSH. Global rule "push only when the user asks" overrides the
  workflow's engineer-self-push. Commits stay local on the branch; push + PR
  happen once at Phase F with explicit user approval.
- `CLAUDE.md`: was pre-existing dirty; user CHOSE to include it in F1 (f12ea06).
  For later items, do not sweep unrelated dirty files via `git add -A`; stage
  explicitly and verify `git show --stat <sha>`.

## Defects caught in F1 (would have shipped a red CI)
- A: .moon/workspace.yml had stale `internal/runtime/platform` source after the
  crate was deleted → `moon project ...` errors project_graph::missing_source.
  Fix: delete the line; lilo-sys auto-covered by `crates/*/` glob.
- B: .github/workflows/pr.yml pinned `dtolnay/rust-toolchain@1.90` vs required
  1.95 (cfg_select!). Fix: bump to @1.95.
- LESSON: when a crate is added/deleted/moved, the blast radius includes
  .moon/workspace.yml sources AND CI toolchain pins, not just Cargo.toml
  members. Acceptance must be `moon ci`.
