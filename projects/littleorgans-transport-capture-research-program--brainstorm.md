---
title: littleorgans transport capture research program
type: design
tags: [littleorgans, transport, capture, research-program, brainstorm]
summary: Research and decision sequence to turn mandatory capture into a first-class littleorgans product capability, treating tm as experimental evidence only
status: complete
source: project-planner
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

# littleorgans transport capture research program

A research and decision sequence, deliberately short of an implementation plan. It defines what must be decided, in what order, which experiments retire which risks, and what evidence would falsify each premise. Zero tm dependency: transport-matters is inspected as experimental evidence only, per `LESSONS.md:19` ("littleorgans must not invoke, package, version against, or depend on them").

## Baseline

| Repo | Pinned SHA | Verified | State notes |
|---|---|---|---|
| littleorgans | `98d8928941b5b5db670ed73ed06af57f61dcfa0a` | HEAD matches pin | Working tree has `M LESSONS.md` (2 insertions, the two governing transport lessons quoted below are present in the tree) |
| transport-matters | `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` | Commit exists; diverged from branch HEAD `ed099336` (merge base `101287bf`); inspected via detached read-only worktree `/tmp/tm-a252df24` | `NOTES/` excluded from all reads per directive. Factual caveat: `api/src/transport_matters/cli/credential_source.py:184` at this commit has an unparenthesized multi-exception clause; the committed blob fails `ast.parse`, so the pinned commit does not import cleanly. Treat auth evidence as design evidence, not as a runnable baseline |

No repo edits were made in either repository.

## Governing constraints

1. `littleorgans/LESSONS.md:18`: Transport capture is a first-class littleorgans product context. "A shippable `lilo run` path includes capture by construction," covered across installation, readiness, diagnostics, compatibility, lifecycle, release qualification, and operator commands.
2. `littleorgans/LESSONS.md:19`: `tm` and transport-matters are experimental research. Do not invoke, package, version against, or depend on them. Learn from their proven capture, durability, fidelity, and test patterns.
3. Consequence: `NOTES/transport-integration.md` (dated 2026-06-05, status "design, planning") is superseded in its dependency posture. Its Decisions 1/4/10 assume migrating and invoking the Python `tm`; the newer lesson inverts that. Its Decision 2 (naming), Decision 5 (SessionId join via `LILO_AGENT_SESSION_ID`), and the open questions 8/9 (read surface, reliability) remain live inputs.
4. `CLAUDE.md` keeps transport outside the control plane: it observes the wire and never authorizes, decides what to spawn, or reconciles.

## Evidence summary

### littleorgans at 98d8928: where capture would attach

- Launch chain has five interposition seams, ordered by proximity to exec:
  - Seam A: `internal/runtime/launchers/src/lib.rs:48` `BinaryLauncher::argv` (argv is `vec![which(binary)]`; per-runtime).
  - Seam B: `internal/runtime/daemon/src/api.rs:74` `spawn_domain` (single funnel for every spawn, both isolation modes, session-backed and raw diagnostic).
  - Seam C: `internal/runtime/daemon/src/backend.rs:33` `RuntimeBackends::prepare_launch` (proven argv/env rewrite precedent: `docker_argv.rs::docker_run_launch`).
  - Seam D: `internal/runtime/daemon/src/server/spawn.rs:15` `SpawnCoordinator.pending_launches` (last point the `LaunchSpec` can mutate before UDS handoff).
  - Seam E: `internal/runtime/app/src/cli/shim.rs:119` `runtime_command` (shim `env_clear()` then `LaunchSpec.env`; the child sees exactly `LaunchSpec.env`).
- Session identity is already solved: `SessionId` (UUIDv4, `crates/lilo-common/src/id.rs:44`) minted at `internal/session/daemon/src/handler/spawn.rs:29`, injected as `LILO_AGENT_SESSION_ID` at `handler/spawn.rs:384` and re-upserted at `internal/runtime/launchers/src/lib.rs:97` `runtime_env`. Registry: `crates/lilo-paths/src/env.rs:33-41`, enforced by `scripts/check-env.sh`.
- Nothing transport exists yet: no `transport` crate or workspace member, no `lilo transport` namespace in `crates/lilo/src/cli.rs:234 define_commands!`, no capture path helper in `lilo-paths` (`capture_root()` absent), no ADR directory. `lilo capture` is tmux pane capture (`crates/lilo-rm-core/src/capture.rs`), a distinct verb.
- Extension points ready to receive capture: `crates/lilo-rm-core/src/version.rs:10` `RUNTIME_PROTOCOL_CAPABILITIES` (additive `#[non_exhaustive]` enum, natural home for a `WireCapture` capability), protocol pinned at `0.8`; event JSONL at `data/events/runtime.jsonl` (`crates/lilo-paths/src/lilo.rs:107`); Postgres unified schema `internal/db/migrations/0001_unified_schema.sql` (10 tables, `session_sessions` carries `transcript_path`).
- littleorgans does not redirect harness config homes: launcher argv is the bare binary, caller env passes through a denylist (`crates/lilo-rm-core/src/spawn_context.rs:16`). Agents authenticate through their native homes today.

### transport-matters at a252df24: what the experiment proved

- Claude interposition is env-only: a reverse proxy in front of `api.anthropic.com` plus `extra_env={"ANTHROPIC_BASE_URL": proxy_url}` (`captured/claude.py:206`). No CA install, no MITM, no HTTP_PROXY, no sudo, no system trust mutation.
- Codex interposition is a different risk class: explicit forward proxy (`mode="regular"`), `HTTP_PROXY/HTTPS_PROXY/...` plus a merged CA bundle via `CODEX_CA_CERTIFICATE` (`cli/codex_cmd.py::build_codex_invocation`, `cli/trust.py`), and websocket turn semantics (`codex/protocol.py::is_codex_turn_start`).
- Managed session mint closes the identity loop: Claude launched with `--session-id <uuid4>` makes wire metadata, transcript `sessionId`, and the transcript filename stem agree (`cli/launch_profile.py::ClaudeLaunchProfile`, `mints_session_id = True`). Codex requires seed-then-`resume <uuid>` (`cli/codex_session.py::seed_codex_session`).
- Durability pattern proven: tier-1 filesystem is authoritative ("raw bytes before any derived observer work"), atomic write via temp file + fsync + rename (`atomic_io.py::write_atomic_bytes`), `index.jsonl` as the run marker with crash recovery (`storage/disk_helpers.py::DiskStorageRecoveryMixin`), byte-faithful transcript snapshot that fails hard on gaps (`storage/transcript_snapshot.py`).
- Reliability semantics proven: capture plane authoritative, derived store best-effort at runtime (`addon_runtime.py::load_capture_runtime` degrades transcript capture without stopping the proxy); proxy death mid-session tears down the client; bounded bind-retry at startup (`cli/bind_failure.py`); grant persistence and credential resolution fail closed.
- The headline product (wire-vs-transcript diff) was never shipped there: the wire store "ships dark" with no read surface (`TLDR.md:48-52`, `NOW.md:417`). What is proven instead is request-pipeline fidelity (`request_diff.py::request_unchanged`, forward original bytes verbatim when unchanged) and post-persist drift detection (`drift_capture.py::detect_unknown_shapes`) feeding a certification scheme (`harnesses/certification.py`, sealed records for `claude-2.1.211-r2` and `codex-0.144.4-r2`).
- Credential lesson is conditional: the entire broker/fleet-home apparatus exists because transport-matters redirects `CLAUDE_CONFIG_DIR`, and Claude on macOS keys its keychain entry by `sha256(config_dir)`. A capturer that does not redirect the config home never inherits this problem.
- Performance envelope: CPU knee near ~50 concurrent active streams on the Python mitmproxy plane; load harness publishes its own fidelity caveats (`api/tests/integration/shared_proxy_load_harness.py`).
- Test patterns worth adopting: real-run round-trip proof over temp dirs shaped like live runs, crash-atomicity tests, fixture corpora as persisted-artifact contracts shared across planes, architecture-enforcing tests (import boundaries), a load harness deliberately outside test collection.

## Decision register

Each decision states the question, the evidence that bounds it, and its gate (what must be known before it can close). No decision below is closed by this document.

### D1. Bounded-context home for capture
Where does the first-class capability live: a new `internal/transport/` context beside runtime and session, or a capability inside runtime?
Evidence: `CLAUDE.md` already names transport a bounded context with an operator namespace; runtime owns the spawn seams the capturer must touch; transport must stay outside the control plane.
Gate: closes after E2 shows whether interposition needs any runtime-internal state beyond `LaunchSpec.env` mutation. If env-only suffices, a separate context with a narrow runtime-side hook is viable; if the capturer must participate in shim lifecycle, the boundary sits differently.

### D2. Capture-plane language and process model
Rust in-workspace (proxy as a `lilod`-managed component or per-session task) versus an owned Python plane under `python/` (reserved placeholder exists).
Evidence: transport-matters' plane is Python mitmproxy and hit a ~50-stream CPU knee; Claude capture needs only a streaming reverse proxy (no MITM), which is squarely within mainstream Rust (hyper) capability; Codex needs TLS MITM plus CA minting, harder everywhere; the monorepo's crate train is Rust with atomic releases, and a Python plane would ride a separate version train.
Gate: closes on E1 (Rust reverse-proxy spike passes SSE fidelity) for the Claude scope. The Codex scope re-opens it only if E5 falsifies Rust MITM feasibility.

### D3. Interposition seam
Env-only injection at Seam C (`prepare_launch`) or launcher level (Seam A), versus an exec-wrapper inversion (`lilo run` execs a capture wrapper that spawns the agent).
Evidence: the strongest sequencing fact of this study. transport-matters proves Claude capture rides a single env var. littleorgans already owns every spawn through one funnel (`spawn_domain`) and has a proven `prepare_launch` rewrite precedent (Docker). The wrapper inversion assumed by the stale note is therefore not on the critical path for the first vertical; it becomes relevant only if the proxy must be per-session and process-owned by the launch (E2 decides).
Gate: closes after E2.

### D4. Proxy topology and lifecycle
One shared proxy owned by the daemon versus per-session proxy instances; who starts it, who tears it down, what happens to it when `lilod` restarts.
Evidence: transport-matters ran per-run proxies with bind-retry loops and manifest liveness beacons, and separately prototyped a shared-proxy pool (K=1, generalization estimated there at ~4 days). A daemon-resident shared proxy matches littleorgans' K8s shape (substrate service, not per-spawn ceremony) but concentrates blast radius.
Gate: closes after E2 (single-session) plus E6 (overhead and concurrency measurement).

### D5. Artifact store shape
Filesystem tier-1 under the `LILO_HOME` derived tree plus a Postgres index, versus Postgres-only.
Evidence: tier-1-authoritative with atomic fsync writes is the proven durability pattern; littleorgans already has an event JSONL precedent and a single unified Postgres schema; raw provider bytes are large and streamy, a poor fit for row storage; `session_sessions.transcript_path` shows the existing pattern of pathing artifacts from the DB.
Gate: closes after E4 (crash-durability proof of the chosen write path) and requires a `lilo-paths` decision (`capture` dir under the derived tree, registered like the others).

### D6. Session identity and managed mint
Adopt managed mint (`--session-id <SessionId>` for Claude) so wire, transcript, and `session_sessions` agree on one key, or correlate post-hoc.
Evidence: `SessionId` is already minted pre-spawn and injected as `LILO_AGENT_SESSION_ID`; transport-matters proved the mint path for Claude and the seed-resume path for Codex; post-hoc correlation there required a uuid5 synthesis namespace and 14-shape containment probes, which is exactly the complexity managed mint avoids.
Gate: closes after E3. Falsification risk is low for Claude and structural for Codex (no direct mint; requires seed-plus-resume, which touches the launcher argv contract).

### D7. Reliability contract
Fail-closed (no proxy, no spawn) versus fall back to uncaptured spawn; existence of `lilo run --no-capture`; mid-session proxy death semantics.
Evidence: the stale note leaned fail-closed with an explicit escape flag; transport-matters implements capture-authoritative with derived-store degradation and client teardown on proxy death; `LESSONS.md:18` ("capture by construction") argues fail-closed as default.
Gate: closes after E7 demonstrates the operator experience of both failure modes through real `lilo run` error surfaces. This is an operator-contract decision for Stuart, informed by E7 evidence.

### D8. Runtime-home isolation scope
Does v1 capture keep agents in their native config homes (no credential problem exists), or does it also take on isolated runtime homes (importing the credential-broker problem class)?
Evidence: littleorgans today passes caller env and never redirects `CLAUDE_CONFIG_DIR`; the entire transport-matters broker exists only because it redirects homes; the keychain service name is derived from `sha256(config_dir)` on macOS.
Gate: scoping decision, closeable now on evidence: keeping native homes removes an entire risk class from the capture program. Isolated homes are a separate future program with its own research sequence.

### D9. Harness scope ordering
Claude-first (reverse proxy, no trust surgery) with Codex as a gated second phase (explicit proxy, CA minting, websocket turns), or both at once.
Evidence: the two harnesses differ in proxy mode, trust requirement, session mint, and turn segmentation (declaratively tabulated in `shared/harness_descriptors_v1.json`); every Codex-specific mechanism is strictly harder.
Gate: closeable now on evidence: sequencing Claude first minimizes the falsifiable surface per experiment. Codex opens only after E1 through E4 hold.

### D10. Capture depth for v1
Raw byte capture only (tier-1) versus parsed IR plus drift detection versus the full fidelity-diff product.
Evidence: transport-matters shipped raw capture and drift detection but never shipped the diff read surface; raw-bytes-first is the insurance policy that makes later parsing retroactive ("when a schema breaks, evidence survives").
Gate: raw-first is closeable now on evidence. IR/drift depth closes after E4 and a separate review of what the littleorgans product (agents inspecting sessions, the human UI) actually reads first.

### D11. Protocol and surface advertisement
When to add `RuntimeCapability::WireCapture`, whether capture participates in `lilo doctor`, and when the `lilo transport` operator namespace (`list`, `paths`, `show <session>`) lands.
Evidence: capability enum is additive and `#[non_exhaustive]`; doctor is aggregate by locked decision; namespace shape is already sketched in `CLAUDE.md` and the namespace-consistency note (option B: diagnostic residue only).
Gate: closes after D1 through D5; surfaces trail substance.

## Decision dependency graph

```
D8 (native homes)  D9 (claude-first)  D10 (raw-first)     closeable now, evidence-backed
        │                 │                │
        └────────┬────────┘                │
                 ▼                         │
   E1 ──► D2 (language)                    │
   E2 ──► D3 (seam) ──► D1 (context home)  │
   E2+E6 ──► D4 (topology)                 │
   E4 ──► D5 (store) ◄─────────────────────┘
   E3 ──► D6 (identity)
   E7 ──► D7 (reliability, Stuart decides)
   D1..D5 ──► D11 (capability + namespace)
   E5 (codex, gated) ──► reopens D2 scope only if falsified
```

Critical path: E1 → E2 → E3 → E4, in that order. Everything else parallelizes or trails.

## Experiment program

Each experiment is a thin vertical proof with an explicit falsification criterion. All are throwaway spikes on branches; none commit the implementation. "Proven" means the stated check passes and the evidence (output, capture file, measurement) is recorded in the experiment log.

### E1. Rust reverse-proxy fidelity spike
Premise: a minimal Rust streaming reverse proxy in front of `api.anthropic.com` is transparent to a real Claude Code session pointed at it via `ANTHROPIC_BASE_URL`, including SSE streaming, while teeing raw request and response bytes to disk.
Proof: run a multi-turn interactive session and a tool-use turn through it; the session is indistinguishable from direct connection; captured bytes replay-parse as valid SSE.
Falsified if: streaming stalls, chunked transfer breaks, TLS/SNI upstream handling fails, or latency overhead is humanly perceptible. Falsification consequence: D2 re-opens toward an owned non-Rust plane; program does not stop.
Depends on: nothing. Start immediately.

### E2. Env-only interposition through the existing spawn path
Premise: injecting `ANTHROPIC_BASE_URL` into `LaunchSpec.env` at Seam C (or Seam A) routes a `lilo run claude` session through the E1 proxy with zero changes to argv, shim, tmux, or lifecycle.
Proof: `lilo run claude` produces a live captured session; `lilo get session`, mail, nudge, capture (pane), and terminate all behave unchanged; the shim env test (`shim_env_only_contains_socket_path`) still holds.
Falsified if: the harness ignores the env var in this spawn mode, or interposition demands process ownership of the proxy per spawn (which would resurrect the wrapper-exec design as a real dependency).
Depends on: E1. Closes D3, informs D1, D4.

### E3. Managed mint identity closure
Premise: adding `--session-id <SessionId>` to the Claude launcher argv makes the transcript filename stem, wire-visible session metadata, and `session_sessions.id` agree with `LILO_AGENT_SESSION_ID`.
Proof: one captured run where all four keys are string-equal; `transcript_path` in the session record points at the transcript whose stem is the SessionId.
Falsified if: Claude rejects externally minted ids in this environment, or the transcript key diverges. Falsification consequence: D6 falls back to post-hoc correlation, importing the synthesis-namespace complexity; sequence a dedicated correlation experiment before Codex work.
Depends on: E2.

### E4. Crash-durability proof of the write path
Premise: the tier-1 pattern (atomic temp+fsync+rename, ordered index append, recovery scan) holds under kill -9 of the capture process at arbitrary points, on the littleorgans artifact layout under `LILO_HOME`.
Proof: scripted crash injection at each write stage; after restart, recovery yields either the complete exchange or no trace, never a torn artifact; the index never references a missing dir.
Falsified if: any torn state survives recovery. Falsification consequence: D5 store shape re-opens (Postgres-first with large-object streaming becomes the alternative).
Depends on: E2 (needs real captured bytes to write).

### E5. Codex MITM spike (gated, second phase)
Premise: Rust can mint a per-install CA, terminate TLS for an explicit proxy, hand the trust bundle to Codex via `CODEX_CA_CERTIFICATE`-equivalent env, and segment websocket turns.
Proof: one captured Codex turn with correct start/stop boundaries.
Falsified if: CA trust injection fails without system trust mutation, or websocket interception in Rust proves impractical within a bounded spike. Falsification consequence: Codex capture moves to its own decision track (possibly a different mechanism entirely); Claude scope ships regardless.
Depends on: E1 through E4 all holding. Do not start earlier.

### E6. Overhead and concurrency envelope
Premise: the Rust proxy's latency and CPU overhead is negligible at v1 scale (one operator, one host) and degrades predictably with concurrent streams.
Proof: measured latency delta and CPU under 1, 5, 20 concurrent streaming sessions; publish the numbers with the harness' fidelity caveats stated, following the transport-matters load-harness pattern (verdict carries its own caveat).
Falsified if: overhead is perceptible at single-session scale. Informs D4 (shared versus per-session) rather than gating the program.
Depends on: E1. Parallel to E2 through E4.

### E7. Failure-mode operator experience
Premise: both candidate reliability contracts (fail-closed spawn refusal; degraded uncaptured fallback) can surface through existing error paths with an operator experience Stuart can judge.
Proof: demonstrate proxy-down-at-spawn and proxy-death-mid-session under both contracts; record the exact CLI output and session-record state for each.
Falsified if: neither contract can produce a clear operator surface without deep error-path rework (which would promote error-surface work into the critical path).
Depends on: E2. Output is the decision brief for D7.

## Sequencing

1. Now, no dependencies: close D8 (native homes, no credential program), D9 (Claude first), D10 (raw capture first) as evidence-backed scoping positions; start E1.
2. E1 result closes D2 for the Claude scope.
3. E2 closes D3 (seam) and unblocks D1 (context home) and E3/E4/E7.
4. E3 closes D6 (identity). E4 closes D5 (store). E6 runs in parallel and, with E2, closes D4 (topology).
5. E7 produces the D7 decision brief; D7 is Stuart's call.
6. D1 through D5 closed permits D11 (capability advertisement, doctor integration, `lilo transport` namespace shape) to close.
7. Only after all of the above hold: E5 (Codex), then a Codex-scope decision pass reusing this register.
8. Program exit: decision register fully closed for the Claude scope, at which point (and only then) an implementation plan is warranted.

## Stop conditions

- Per experiment: each E has a falsification criterion above; a falsified experiment stops its branch and re-opens the named decision, never silently continues.
- Spike time-box: any single experiment exceeding roughly three focused days without proof or falsification is itself a finding (the premise is not thin); stop and re-scope the experiment before continuing.
- Program-level stop: if both E1 and its non-Rust fallback fail SSE fidelity, or if E2 falsifies env-only interposition AND the wrapper-exec alternative is rejected on control-plane-boundary grounds, halt and escalate to Stuart with the evidence; the capture-by-construction premise of `LESSONS.md:18` would need re-examination.
- Scope stop: no v2 scope, no UI work, no fidelity-diff product, no isolated runtime homes, no Codex work before its gate. Any pull toward these stops the pull, not the program.
- Standing constraint: at no point does any experiment invoke, import, package, or version against `tm` or transport-matters code. Reading its artifacts and tests as evidence is the permitted ceiling.

## Explicitly out of scope for this program

- An implementation plan (issue breakdown, estimates, PR sequence). That is the phase after the register closes.
- The wire-vs-transcript fidelity diff as a product surface (D10 fixes raw-first; the diff is retroactively buildable from tier-1 evidence).
- Isolated runtime homes and the credential-broker problem class (D8).
- The TS product plane and human UI (separate train per `CLAUDE.md`).
- transport-matters migration in any form.

## Worker Status

| Worker | Scope | Final state |
|---|---|---|
| Explore subagent 1 | littleorgans at 98d8928: launch chain seams, env registry, session lifecycle join points, transport absence, docs and NOTES status | Complete; evidence incorporated above |
| Explore subagent 2 | transport-matters at a252df24 via read-only worktree /tmp/tm-a252df24, NOTES/ excluded: launch/wrap chain, capture pipeline, identity, fidelity, reliability, read surface, auth, test patterns, stack, top-level docs | Complete; evidence incorporated above; flagged the credential_source.py:184 syntax defect at the pinned commit |

## Evidence index (path + symbol anchors)

littleorgans (98d8928):
`crates/lilo/src/cli.rs:85` Command::Run · `internal/session/app/src/cli/run.rs:15` spawn_session · `internal/session/daemon/src/handler/spawn.rs:29` SessionId mint, `:369` spawn_launch env injection · `internal/session/driver/src/conv.rs:22` runtime_spawn_request · `internal/runtime/daemon/src/api.rs:74` spawn_domain · `internal/runtime/launchers/src/lib.rs:48` BinaryLauncher::argv, `:97` runtime_env · `internal/runtime/daemon/src/backend.rs:33` prepare_launch · `internal/runtime/daemon/src/server/spawn.rs:15` SpawnCoordinator · `internal/runtime/daemon/src/shim_socket.rs:148` shim_env · `internal/runtime/app/src/cli/shim.rs:119` runtime_command, `:152` apply_launch_env_cwd · `crates/lilo-paths/src/env.rs:33` LILO_AGENT_* consts · `crates/lilo-common/src/id.rs:44` UUIDv4 · `crates/lilo-rm-core/src/version.rs:8` RUNTIME_PROTOCOL_VERSION "0.8", `:10` capabilities · `crates/lilo-rm-core/src/capture.rs` pane-capture types · `crates/lilo-rm-core/src/spawn_context.rs:16` caller-env denylist · `internal/db/migrations/0001_unified_schema.sql:30` session_sessions, `:115` session_spawn_intents, `:130` runtime_lifecycle · `LESSONS.md:18,:19` governing lessons · `NOTES/transport-integration.md` superseded dependency posture.

transport-matters (a252df24, NOTES/ excluded):
`captured/claude.py:206` ANTHROPIC_BASE_URL-only interposition · `cli/codex_cmd.py` build_codex_invocation (explicit proxy + CA) · `cli/trust.py` process-scoped trust · `cli/launch_profile.py` LaunchProfile, ClaudeLaunchProfile.mints_session_id · `cli/codex_session.py` seed_codex_session · `cli/runner.py` run_client_children_until_outcome, spawn/teardown matrix · `addon.py` TransportMattersAddon · `atomic_io.py` write_atomic_bytes (fsync+rename) · `storage/disk_layout.py` DiskStorageLayout tier-1 · `storage/disk_helpers.py` DiskStorageRecoveryMixin · `storage/transcript_snapshot.py` gap-hard snapshot writer · `request_diff.py` request_unchanged · `drift_capture.py` detect_unknown_shapes · `harnesses/certification.py` sealed records · `index/sessions.py` SESSION_NS uuid5 synthesis · `session/exchange_correlation.py` 14-shape containment probes · `addon_runtime.py` load_capture_runtime degradation, close_capture_runtime ordered shutdown · `cli/bind_failure.py` bounded bind retry · `credential_broker.py` keychain-by-config-dir broker (evidence for D8 avoidance) · `shared/harness_descriptors_v1.json` per-harness launch facts · `api/tests/integration/shared_proxy_load_harness.py` caveat-carrying load verdict · TLDR.md/PROJECT.md/NOW.md: wire store ships dark, diff unshipped, runs process-resident.
