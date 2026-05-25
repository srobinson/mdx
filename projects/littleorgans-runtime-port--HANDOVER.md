# Runtime Port (Option D) — HANDOVER

Single entry point for continuing the runtime-port boundary work. Written 2026-05-29.

## State
- **WS1** (runtime in-process domain API) — MERGED to `main`, PR #8.
- **WS2 + WS3** (session RuntimePort + in-process adapter + shutdown ordering) — MERGED to `main`, PR #10 (squash `dec7015`). Worktree + branch `feat/session-runtime-port` removed.
- `nancy/ALP-2816` (CLI) — MERGED, PR #9.
- **WS4 — MERGED** (PR #11, squash `d756059` on `main`). 2 commits: `91751cd` (C1
  no-bypass authz gate) + `3aa8412` (C2 de-RPC spawn + audit de-dup). Full workspace gate
  green 537/537; reviewer (Claude) signed off both cards; verified via git + own gate.
  Worktree + branch removed.
- **WS5 — PR #12 OPEN** (https://github.com/littleorgans/littleorgans/pull/12), branch
  `feat/spawn-recovery-hardening` @ `611717b`, 1 commit, gate green 161/161, reviewer
  signed off. Closes the Tx-B commit-failure orphan window: direct-spawn inline-aborts
  (terminate + abort) on Tx-B failure; **reconcile keeps leave-pending-retry** (scoped via
  `OnCommitFailure { AbortRunning, LeavePending }` on the shared `complete_spawn_intent`);
  namespace-deleted stays uniform-abort (permanent failure). The originally-specced
  "stranded Forking" window was proven impossible (abort is atomic) — WS5 only asserts the
  invariant. Plan: `~/.mdx/projects/littleorgans-runtime-port-ws5--plan.md`. On merge:
  `git worktree remove` + delete branch. **Carry-forward:** `reconcile_pending_spawn_intents`
  `?`-aborts the whole sweep on one intent's error — log-and-continue is a later
  robustness pass (fold into WS6 or a small follow-up).
- **WS6 — PR #14 OPEN** (https://github.com/littleorgans/littleorgans/pull/14), branch
  `feat/runtime-port-conformance`, 3 commits: `b5c9190` (C1 tmux test hermeticity, ALP-2607,
  via `LILO_TMUX_SERVER_LABEL` config-DI — NOT a production probe) + `6a8e00b` (C2 dual-adapter
  conformance for status/poll_events/doctor + SpawnConflict parity, test-only) + `97a0e34`
  (C3 watcher poll_events retry + reconcile log-and-continue). Gate green 420/420; reviewer
  signed off all 3; verified via git + own gate. Review caught + corrected an over-broad C1
  (production probe-discovery of test tmux servers → explicit config-DI). On merge:
  `git worktree remove runtime-port-conformance` + delete branch.
  Plan: `~/.mdx/projects/littleorgans-runtime-port-ws6--plan.md`.
  **Skipped as moot** (documented in PR): merged shutdown-ordering test (exists), explicit
  Linux assertion (CI is Ubuntu-only), rev03 full-chain test (Tx-A ordering already
  asserted), production error-type change (provenance split is correct).

## Runtime-port boundary (Option D) — COMPLETE pending merges
WS1–WS6 done. Original `rtmd unavailable` symptom resolved at WS1+WS2; authz no-bypass +
audit de-dup (WS4); spawn-recovery hardening (WS5); conformance + hermeticity + resilience
(WS6). Open PRs awaiting Stuart's merge: **#13** (docs: error-model LESSONS entry), **#14**
(WS6). Carry-forwards (NOT blockers): shared error-model for bounded-context ports before
the 2nd service (`NOTES/bounded-context-port-error-model.md`, design §5.1, cm `019e73c2`);
namespace `Action` vocab cleanup (Kill labels create/delete); finer-grained read authz;
`Authorized<Action>` witness; macOS-in-CI; `TmuxSession::Drop` block-until-server-gone.
Next major track (separate from runtime-port): schedule / orchestrate / workflow — each a
new bounded-context port that should adopt the shared error-model first.
  Plan: `~/.mdx/projects/littleorgans-runtime-port-ws4--plan.md`.
  Delivered: exhaustive `authz_plan` classifier (no `_` arm) gates the 7 verbs at the
  session door; 3 spawn.rs self-calls now on the WS2 `RuntimePort` (composed spawn audit
  2→1); `SpawnedProcess` enriched to return its lifecycle (no status re-fetch);
  `StatusFilter::for_session` shared (DRY). NO new audit type (AuditRow/AuditDecision
  frozen). Design doc §4/§5 truthed-up. Carried forward: namespace Action vocab
  (`Kill` labels create/delete) cleanup; finer-grained read authz; `Authorized<Action>`
  witness.
- **Original problem RESOLVED:** the `rtmd unavailable` ENOENT spew + store-after-close hazard are gone (WS1+WS2). The composed session reaches the runtime in-process via `RuntimePort` (`InProcessRuntime` + `RtmdDriver` socket adapter over a shared `conv` layer in `lilo-session-driver`).

## Source docs
- Design (Option D, §6 workstreams, §8 risks): `~/.mdx/projects/littleorgans-runtime-port-boundary--design.md`
- WS1 plan (done): `~/.mdx/projects/littleorgans-runtime-port-ws1--plan.md`
- WS2 plan (done; carry-forwards in "Out of scope"): `~/.mdx/projects/littleorgans-runtime-port-ws2--plan.md`
- cm decisions: `019e70f9` (design locked), `019e716f` (WS1), `019e72c4` (WS2)

## Remaining workstreams (each: branch off updated `main`, writing-plans → moe-local-batch)

### WS4 — authz "no-bypass" + spawn-lifecycle de-RPC + domain audit
- **Authz gaps:** 7 `SessionRpc` verbs dispatched without identity context (`handler/dispatch.rs`): `NamespaceCreate` (a real unprivileged MUTATION — highest), + `List`, `NamespaceGet`, `NamespaceList`, `MailCheck`, `MailStopCheck`, `Wait` (read-only info leaks). Gate all 7 (thread context or a dispatch choke-point).
- **§4 audit split:** authz + decision-audit (incl. Deny/Error) at the WIRE door (`handle_rpc`); state-change audit at the DOMAIN layer for mutating verbs (spawn, kill, kill_by_pid, nudge, terminate_all/drain, shim_ready, shim_exit, post-commit append). De-dup door vs domain. Key off the VERB, not `Action` (ValidateTarget carries `Action::Spawn` but mutates nothing).
- **Spawn-lifecycle de-RPC (deferred from WS2 C4):** the 3 self-RPCs in `spawn.rs` — Spawn `:73`, recovery Kill `:167`, reconcile Status `:275` — still on `handle_rpc`. De-RPC them to the port WITH the domain state-change audit so the runtime-side decision-audit row that handle_rpc emits is REPLACED (no regression). The session-side `begin_spawn_intent` audit already covers spawn; the runtime row is redundant de-dup that WS4 formalizes. `compose.rs` wire door stays (external clients).

### WS5 — spawn-recovery hardening (R11-bounded)
- Inline-abort the spawn intent on Tx-B failure (today recovers only on next startup → orphan window if the daemon crashes between).
- Reconcile stranded `Forking` lifecycles whose intents are aborted/missing (today reconcile scans only `pending`, so an `abort_spawn_intent` that dies between the intent UPDATE and the lifecycle DELETE strands a Forking row forever).
- Stay within synthesis rev07 R11 (Tx-A/spawn/Tx-B spine; recovery via `session_spawn_intents`).

### WS6 — conformance + Linux + hermeticity
- Dual-adapter conformance suite (InProcessRuntime ≡ RtmdDriver) — partially seeded in C2 (reap_exited/nudge/capture); broaden.
- rev03 locked tests: `session-spawn → identity-audit → runtime-kqueue → session-record` ordering; merged Stop/Ctrl-C/SIGTERM shutdown ordering (C5 covers shutdown; add the spawn-ordering one).
- Linux assertion in CI on the gated seams (peer_creds SO_PEERCRED / pidfd) — Linux is already cfg-gated/sound; this just prevents regression.
- **tmux-capture hermeticity flake** (`lilo-runtime-app::integration_pass5::capture_tmux_pane_returns_snapshot_json`): leaks/flakes under load/tmux contention (ALP-2607). Make hermetic.
- **error-type-parity:** in-process `DriverError::Runtime(String)` vs socket `DriverError::Client(ClientError)` — conformance covers outcome parity, not error parity. Decide acceptability.
- **socket-port loop-resilience:** the watcher loop's `poll_events().await?` is a no-op for the infallible in-process port, but a future socket port's `poll_events` Err would end the loop with no retry. Decide.

## Execution pattern (proven across WS1/WS2)
- **Fresh warroom per commit** (kill + respawn): Codex `helioy-tools:backend-engineer` (impl) + Claude `superpowers:code-reviewer`, two-phase (design `D`→`S|A`, diff `C`→`S|B`). Mediated through the orchestrator. Avoids the context-compaction stalls that hit WS1's T5.
- The plan doc is the cold-read handoff for each fresh pair; the orchestrator is the continuity.
- **Trust nothing agent-reported:** verify SHAs, push state, and gate results via `git` + your own `just check && just build && just test`. This session saw SHA hallucination, a phantom B|B from corrupted reviewer tool output (line 295 in a 273-line file), and agent-id drift. Run the gate yourself before every PR; review diffs via `git diff HEAD~..HEAD` (no hand-typed SHAs); spot-check a reviewer's STRUCTURAL claims (line numbers, file contents) before relaying a block that triggers engineer work.
