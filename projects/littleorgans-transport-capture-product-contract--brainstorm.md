# littleorgans Transport capture: product contract brainstorm

Status: COMPLETE
Date: 2026-07-31
Author: littleorgans warroom worker (lilo-transport-study-phase1)

## Evidence baseline

| Repo | Path | Pinned SHA |
|---|---|---|
| littleorgans (monorepo) | `/Users/alphab/Dev/LLM/DEV/helioy/littleorgans/littleorgans` | `98d8928941b5b5db670ed73ed06af57f61dcfa0a` (HEAD) |
| transport-matters (experimental, evidence only) | `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters` | `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` (phase-one pin) |

**Baseline reconciliation.** Initial exploration audited transport-matters at repo HEAD `ed099336`; the phase-one pin `a252df2` is a sibling commit (merge-base `101287bf`: the pin carries the pre-squash auth branch, HEAD carries its squash `#352` plus canvas slice 1a and a docs commit). The full tree diff between the two, `NOTES/` excluded, touches only `NOW.md`, `shared/harness_inventory_vocabulary_v1.json` + its test, and ~22 `www/packages/{canvas,core}` first-run UI files. None of those files is cited by this contract, so every transport-derived citation is byte-identical across both trees; load-bearing symbols were additionally spot-verified directly in the `a252df2` tree via `git show`/`git grep` (no checkout): `prepare_captured_run`, `_BIND_RETRY_ATTEMPTS = 3`, `wait_for_port_ready` 5s default, `DEFAULT_CAPTURE_HEALTH_POLL_MS = 3000` / `CAPTURE_HEALTH_FAILURE_THRESHOLD = 3`, `ANTHROPIC_BASE_URL` in `captured/claude.py`, `trust_requirement` none/codex_ca_certificate and grok `"launch": null` in `shared/harness_descriptors_v1.json`, `ENV_PREFIX` in `env_keys.py`, `synth_session_id` uuid5 in `index/sessions.py`, `FORCE_EXIT_AFTER_S = 20.0` in `self_reap.py`, `DEFAULT_DELIVERY_RETENTION_DAYS = 30`, `requires-python >= 3.14` and `mitmproxy>=12.2,<13`, "nothing reads them back" in `TLDR.md`, and the migrations tree (32 revisions, `0001`–`0032`; an earlier draft said 33 and is corrected below). No later-only evidence is load-bearing anywhere in this document.

Constraints honored: no repo edits; `transport-matters/NOTES/` neither read nor cited; transport-matters treated as validated-lessons evidence only. Zero `tm` dependency is a premise of every section below: littleorgans must not invoke, package, version against, or depend on `tm` or the transport-matters distribution. All evidence citations are `path :: symbol` at the SHAs above.

## Framing

Transport is a first class bounded context inside littleorgans, peer to Identity, Runtime, and Session. It owns the wire between an agent and its model provider and the durable capture of that wire. Its authority is narrow (observe, record, serve reads); its presence is not optional. littleorgans cannot ship without capture: the `lilo run` product path, installation, readiness, diagnostics, lifecycle, release qualification, and operator surface include Transport by construction.

The prior design (`lilo run` execs a `tm` wrapper; `NOTES/transport-integration.md`, CLAUDE.md bounded-context section) is withdrawn. transport-matters remains a research vehicle whose validated lessons (proxy-before-agent ordering, per-harness trust model, capture-loss handling, storage layout, identity minting, fail-closed preflights, and its gaps) inform this contract. The capability is implemented in Rust under littleorgans ownership, inside the existing workspace, behind the existing seams named in Appendix A9.

Ubiquitous language: **capture** is the recorded wire for one session. **Exchange** is one request/response pair on the wire. **Capture state** is the per-session lifecycle of that recording. `lilo capture` (tmux pane snapshot) is a Runtime verb and keeps its name; nothing in Transport reuses the word "capture" as a CLI verb.

## 1. Launch behavior

**Invariant: no agent process starts unless its wire is already observed.** Capture is a structural property of `lilo run` and `lilo create session`, not a flag.

- Interposition is by environment, not argv. The proxy endpoint rides the existing env-injection seams: for Claude, `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>` (reverse proxy, no certificate trust; proven by transport-matters `shared/harness_descriptors_v1.json` claude `trust_requirement: "none"`); for Codex, explicit proxy env plus a process-scoped CA bundle (descriptor `trust_requirement: "codex_ca_certificate"`, `proxy_mode: "explicit"`). Neither variable exists in littleorgans Rust source today (verified, Appendix A1), so this is additive.
- Injection site: `internal/runtime/launchers/src/lib.rs :: runtime_env` (already injects `LILO_AGENT_SESSION_ID`, `LILO_AGENT_RUNTIME`) extends per-launcher with proxy env; `RuntimeBackends::prepare_launch` (`internal/runtime/daemon/src/backend.rs`) remains the argv seam if a launcher ever needs argv interposition — the Docker backend already rewrites argv there, so the precedent exists and no new seam is invented.
- Ordering: proxy listener live and accepting before the shim execs the agent (transport-matters `cli/runner.py :: run_client_children_until_outcome`: "mitmdump first, then the interactive client"). In littleorgans terms: capture readiness is part of spawn preflight (`internal/runtime/daemon/src/spawn_preflight.rs :: check`) or the `begin_spawn` window, before `ShimLaunch` is answered.
- The join key is `SessionId` (UUIDv4, minted by Session at spawn time). Capture records are keyed by it from birth; the provider-native conversation id is an attribute, never a key. transport-matters proves why: Claude's native id can be minted and injected (`--session-id`), Codex's is read back and synthesized (`uuid5`), so native ids are per-harness and unstable as keys (`api/src/transport_matters/session/session_facts.py`, `models.py :: SessionRow.native_session_id`).
- Raw `lilo runtime spawn` (diagnostic, identity-gated, no session record) also runs under capture. Observability of the wire does not depend on which door started the process.
- Caller-env hygiene: the existing denylists (`crates/lilo-rm-core/src/spawn_context.rs :: CALLER_ENV_DENYLIST*`) extend to strip inherited proxy and trust variables (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`, `NODE_EXTRA_CA_CERTS`, `SSL_CERT_FILE`, ...) before Transport sets its own, and pin `NO_PROXY=127.0.0.1,localhost` for the child. transport-matters' `build_managed_child_env` strips ~35 proxy vars and 9 trust vars; that lesson transfers verbatim.

## 2. Readiness

- **Component readiness**: Transport is composed into `lilod` (composition root `internal/session/app/src/compose.rs`). `lilo daemon start --ready-check` extends the existing `RunMode::ReadyCheck` pattern: prove capture readiness by doing the real work (bind an ephemeral proxy listener, open the capture store, write and read back a probe artifact) then tear down through the real shutdown path. Output stays the existing shape (`{"ok":true}` plus a human line naming capture among the proven subsystems).
- **Per-spawn readiness**: each spawn allocates a proxy port and confirms accept before the agent execs. Bind conflicts retry with port reallocation (transport-matters retries 3 times, distinguishing `EADDRINUSE` from timeout via the proxy log; the distinction between retryable bind conflict and genuine startup failure is the transferable contract).
- **Store readiness**: capture's durable store is preflighted before any process that writes to it starts, same posture as transport-matters `session_store_preflight.py :: prepare_session_store` (probe, migrate under advisory lock, or stop with setup instructions). littleorgans already opens Postgres once at compose time; capture preflight joins that path rather than adding a second one.

## 3. Failure semantics

- **Launch-time: fail closed.** A spawn whose capture cannot start fails the spawn. The failure flows through the existing intent machinery: `abort_spawn_intent` persists `aborted_reason` (`internal/session/daemon/src/handler/spawn.rs`), the CLI surfaces a typed, stable reason. Silent uncaptured runs do not exist. Stable failure codes are part of the contract (transport-matters carries 21; littleorgans needs at least: `capture_bind_conflict`, `capture_start_timeout`, `capture_store_unavailable`).
- **Mid-run capture loss**: if the proxy dies while the agent lives, Transport emits a capture-lost signal correlated to the session, the session's capture state becomes `lost` with evidence, and doctor reports it. Whether the run is then terminated (transport-matters tears the run down: `CaptureHealthMonitor` → `RunManager.settleRun({kind: "capture-lost"})`) or continues visibly degraded is Question Q1 for Stuart. Either way the loss is loud, durable, and attributed.
- **Orphan prevention**: the proxy's lifetime is bound to its supervisor; parent death reaps the proxy (transport-matters `self_reap.py`: PDEATHSIG on Linux, ppid watchdog on macOS, 20s force exit). In littleorgans the shim/daemon already supervises the agent; the proxy joins that supervision tree so no orphan listener outlives its session.
- **Agent exit**: capture finalizes (flush, seal, state → `complete`) as part of the existing `ShimExit` → `Terminated` path. `RuntimeEvent` (`crates/lilo-rm-core/src/types/lifecycle.rs`) today has exactly three variants (`Running`, `Terminated`, `Lost`); capture state changes either become a fourth event family or ride session-side events — a design choice inside the contract, not a product question.
- **Provider rejection is not a capture failure.** Auth errors, rate limits, and provider 4xx/5xx are recorded as exchanges and surfaced from the live run; capture never authorizes or blocks on provider access (transport-matters `LAUNCH-CONTRACT.md` resolution rule).

## 4. Session views

- `lilo get session` gains a `CAPTURE` column (headers today: `ID RUNTIME NAMESPACE ROLE TMUX STATUS AGE`; seam: `internal/session/app/src/cli/output.rs :: print_session_table_with_rows` + `session_cells_with_id`). Values: `active`, `complete`, `lost`, `failed`. There is no `none` for session-backed runs; mandatory capture means its absence is a failure state, not a mode.
- `Session` (`internal/session/core/src/session.rs`) gains capture fields (state, evidence, exchange count or artifact pointer). Because `lilo get session --output json` serializes the struct verbatim (`internal/session/app/src/cli/get.rs`), the JSON surface follows for free.
- Capture detail lives behind the operator namespace (`lilo transport show <session>`, §6), not in the session table. The session view answers "is my wire observed"; the transport view answers "what is on it".

## 5. Capture status

Per-session capture state machine, persisted, keyed by `SessionId`:

`pending` (intent begun) → `active` (proxy accepting, agent spawned) → `complete` (agent exited, artifacts sealed) | `lost` (proxy died mid-run, evidence attached) | `failed` (never started; spawn aborted).

- State transitions are durable rows, not in-memory flags, so daemon restart reconciles them the same way `reconcile_pending_spawn_intents` reconciles spawn intents today.
- The probe sweep (`internal/runtime/daemon/src/reconcile.rs`, 30s) extends to capture liveness: a session `active` whose proxy pid is gone transitions to `lost` with evidence, mirroring `LostEvidence` for runtimes.
- Aggregate status: `lilo doctor` (§7) and `lilo transport list` (§6) both read this state; there is one source of truth.

## 6. CLI

- New operator namespace `lilo transport ...`, third alongside `lilo runtime ...` and `lilo session ...`. Verbs, all read/ops (no spawn path — launch is `lilo run`'s):
  - `lilo transport list` — capture state across sessions (JSON supported).
  - `lilo transport show <session>` — one session's capture: state, evidence, exchange summaries, artifact paths. Accepts the same selector/short-prefix rules as `lilo get session`.
  - `lilo transport export <session>` — §10.
- Surface mechanics: verbs are added in `tools/schemas/cli.toml` and regenerated via `xtask codegen`; the guard test (`crates/lilo/tests/generated_surface_guard.rs`) makes hand-edited clap impossible. This is the locked, existing path for any new verb.
- `lilo capture` stays the tmux pane-capture verb (Runtime's). No collision; documented adjacency.
- No per-substrate doctor: transport health folds into `lilo doctor` per the existing rule.

## 7. Doctor

`lilo doctor` extends `DoctorStatus` (`crates/lilo/src/cli/doctor.rs`) with a transport block:

- capture store reachable and migrated (piggybacks `DatabaseHealth`; capture tables counted in `SubstrateHealth::collect` alongside identity/session/runtime counts),
- proxy capability (can bind a loopback listener now),
- Codex trust material present and valid (CA bundle exists, not expired) when Codex is a supported runtime,
- sessions currently `active`/`lost` capture counts; `lost` captures produce warnings, same rendering path as runtime warnings (`crates/lilo/src/cli/doctor/runtime.rs :: warnings_for_report` precedent).

## 8. Artifact access and storage

- **Location**: all capture state lives under the existing tree: blobs and per-exchange artifacts under `~/.lilo/data/capture/<session-id>/...` (derivation via `crates/lilo-paths/src/lilo.rs :: LiloPaths`, new accessor; the pinning test `assert_default_tree` extends), index and metadata in the one operator Postgres (`LILO_DATABASE_URL`), in transport-owned `transport_`-prefixed tables matching the unified schema's `session_`/`runtime_`/`identity_` convention (`internal/db/migrations/0001_unified_schema.sql`). No second database, no second connection chain.
- **Per-exchange shape** (informed by transport-matters `storage/disk_layout.py`): raw request bytes, raw response bytes, parsed representation, and a small entry record per exchange; atomic write discipline (tmp/rename) is required. Which representations are v1-mandatory is Q3.
- **Identity**: directory and rows keyed by `SessionId`; provider-native session id stored as an attribute column with a uniqueness constraint scoped to provider, never as the key.
- **Access paths**: operators via `lilo transport show/export`; agents via the same CLI JSON (agents already receive `LILO_AGENT_SESSION_ID`, so self-inspection is `lilo transport show $LILO_AGENT_SESSION_ID --output json`) and, when the MCP surface grows, via `lilo mcp`. Files on disk are readable but the CLI/JSON contract is the supported surface; paths are an implementation detail that `show` reports rather than a promise.
- **Anti-lesson**: transport-matters shipped its wire store dark ("nothing reads them back"). This contract forbids that: no capture artifact class ships without at least one read path (`show` or `export`) in the same release.

## 9. Application needs

Two named consumers drive the read surface:

1. **Agents inspecting and sharing sessions**: need self-identification (already solved: `LILO_AGENT_SESSION_ID`), listing (`transport list --output json`), detail (`show --output json`), and a stable schema they can parse. Cross-agent sharing happens by `SessionId`, which mail already carries.
2. **The littleorgans human UI** (separate TS/Electron train): needs a read contract, not a bundled server. v1 commits to the CLI JSON schema as the contract; whether a headless HTTP read API ships in v1 is Q5. The UI never reads capture files directly.

## 10. Support and export

- `lilo transport export <session>` produces one self-contained bundle (directory or tarball): session metadata, capture state history, exchanges, and a manifest with versions (`lilo` version, capture schema version, SHAs) so a bundle is diagnosable without the originating machine.
- **Redaction is a write-time property, not an export-time patch**: authorization headers and known credential material (`ANTHROPIC_API_KEY`, `Authorization`, OAuth tokens; transport-matters' `HARNESS_CREDENTIAL_ENV_KEYS` denylist is the seed list) are redacted or tokenized before bytes hit disk, so no artifact class can leak a credential into an export. Posture confirmed as Q4.
- Support flow: a failing run's export bundle plus `lilo doctor --output json` is the complete support payload.

## 11. Retention and deletion

transport-matters' largest validated gap: Tier-1 grows unbounded, no sweeper, per-exchange delete exists but is unexposed. The contract closes this at ship:

- `lilo delete session` deletes capture rows and artifacts with the session (cascade semantics; the DB cascade precedent exists in transport-matters migration 0001).
- A retention policy is configurable in `settings.toml` (age and/or size bound) and enforced by a daemon sweeper; defaults are generous but finite. Enforcement events are auditable.
- Disk pressure is a doctor warning before it is an incident (capture root size surfaced in the transport doctor block).
- Deletion is complete: rows, blobs, directory. No tombstone artifacts left behind.

## 12. Installation and release acceptance

- **Installation adds nothing.** Capture is compiled into the existing binaries (`lilod`/`lilo`). No Python, no mitmproxy, no Node, no `uv`, no separate install step. The Postgres requirement already exists (`LILO_DATABASE_URL`); capture reuses it. This is the sharpest divergence from transport-matters (Python ≥3.14 + mitmproxy + Postgres + optional Node) and the core payoff of native ownership.
- **Codex trust**: if Codex ships in v1 scope (Q2), littleorgans generates and manages its own CA material under `~/.lilo`, process-scoped to the child only — never installed system-wide, no sudo (transport-matters proves the process-scoped bundle approach works).
- **Release acceptance**: the crate-train release gate extends with capture acceptance: `just check && just build && just test` includes capture integration tests (spawn gated on proxy, artifact readback, fail-closed abort, delete cascade); a release in which capture acceptance fails does not tag. "littleorgans cannot ship without capture" is enforced by the gate, not by policy prose.
- **Compat surface**: if capture adds daemon↔client or shim protocol surface, it rides the existing `RUNTIME_PROTOCOL_VERSION` + capabilities mechanism (`crates/lilo-rm-core/src/version.rs`), e.g. a `WireCapture` capability, hard-gated in `lilo-rm-client :: check_protocol_version` and soft-gated in doctor.

## 13. Explicit non-goals (v1)

- No invocation of, packaging of, or version coupling to `tm`/transport-matters. No shelling out to any external capture binary.
- No pause-and-edit, breakpoints, request curation, or override rules on the wire (transport-matters inspector features). v1 capture is observe-and-record only.
- No bundled web UI or HTTP server requirement in `lilod` (pending Q5, and even then headless-read only).
- No fidelity diff read surface in v1 unless Q6 says otherwise; nothing ships dark either way.
- No harness coverage beyond Claude (and Codex per Q2). No Grok, no Gemini, no opencode.
- No cross-host or multi-operator capture. v1 is one operator, one host, one `lilod`.
- No provider-native conversation id as a join key, anywhere.
- No new environment prefix: capture config is `LILO_*`, registered in `crates/lilo-paths/src/env.rs`, enforced by `scripts/check-env.sh --check`.

## Product journeys

**J1 — First run on a fresh install.** Operator installs littleorgans, sets `LILO_DATABASE_URL`, runs `lilo daemon start --ready-check` (capture proven among subsystems), then `lilo run claude`. The proxy comes up, Claude spawns against it, `lilo get session` shows `CAPTURE active`. After exit, `CAPTURE complete`; `lilo transport show <id>` lists exchanges. Zero capture-specific setup occurred.

**J2 — Capture cannot start.** Proxy port allocation fails repeatedly (pathological bind conflicts). `lilo run` exits nonzero with `capture_bind_conflict`; `lilo get session` shows the intent aborted (`CAPTURE failed`); `lilo doctor` explains the environment problem. No agent process ever started; nothing ran unobserved.

**J3 — Proxy dies mid-run.** The capture proxy crashes while the agent is alive. Within one probe sweep the session shows `CAPTURE lost` with evidence, doctor warns, and (per Q1) the run is terminated or continues visibly degraded. The operator learns from `lilo transport show` exactly where the record stops.

**J4 — Support export.** An agent misbehaves; Stuart runs `lilo transport export <id>` and shares the bundle. The bundle carries versions and redacted exchanges; no credential appears in it because redaction happened at write time.

**J5 — Agent self-inspection.** An agent reads `LILO_AGENT_SESSION_ID`, runs `lilo transport show $LILO_AGENT_SESSION_ID --output json`, and reasons about its own prior turns; it mails another agent the `SessionId`, which is sufficient for that agent to view the same capture.

**J6 — Deletion.** `lilo delete session <id>` removes the session record, capture rows, and `~/.lilo/data/capture/<id>/`. `lilo transport list` no longer shows it; disk reflects it.

## Questions Stuart must decide

- **Q1 — Mid-run capture loss policy.** Terminate the run (transport-matters behavior; capture is load-bearing) or keep the agent alive with a loud `lost` state (work preservation). Launch-time is fail-closed either way.
- **Q2 — v1 harness scope.** Claude-only (reverse proxy, zero trust setup) or Claude+Codex (adds explicit-proxy path and CA lifecycle under `~/.lilo`).
- **Q3 — v1 artifact depth.** Raw bytes only (parse on read) vs raw + parsed representation at write time. Raw-only is smaller and simpler; parsed-at-write powers richer `show` output immediately.
- **Q4 — Redaction posture.** Confirm write-time credential redaction as mandatory (recommended; makes export safe by construction) vs raw storage with export-time redaction.
- **Q5 — Headless read API in v1.** CLI JSON only, or also an HTTP read surface for the future UI train. CLI-only keeps `lilod` free of an HTTP server; the UI train then builds against the JSON schema.
- **Q6 — Fidelity diff scope.** Reserve fidelity (harness-believed vs provider-received) as a v2 direction, or require v1 to store the inputs needed so v2 can compute it retroactively.
- **Q7 — Escape hatch existence.** Is there any identity-gated diagnostic to run uncaptured (e.g. under `lilo runtime spawn` only), or is uncaptured execution impossible by construction? Recommendation: no escape hatch in the session-backed path; if diagnostics demand one, it lives behind the operator namespace, is identity-gated, and the session view records that nothing was captured because nothing session-backed ran.

## Acceptance tests

Written as release-gate assertions; each maps to a journey or contract clause.

1. `lilo daemon start --ready-check` output includes capture among proven subsystems; exit 0 with store reachable, exit nonzero with `LILO_DATABASE_URL` unreachable, message names capture preflight. (J1, §2)
2. Spawn ordering: instrumented `lilo run claude` shows the proxy listener accepting before the agent pid exists; killing the proxy between allocation and agent exec aborts the spawn with a stable code and an `aborted` intent row. (§1, §3, J2)
3. Env contract: the child env of a spawned agent contains `ANTHROPIC_BASE_URL` pointing at loopback, no inherited `HTTP_PROXY`/`HTTPS_PROXY`/trust vars, and `NO_PROXY` pinned; `scripts/check-env.sh --check` passes with all new `LILO_*` names registered. (§1, §13)
4. `lilo get session --output json` for a live captured run contains capture state `active`; the human table shows the `CAPTURE` column. After exit, state is `complete`. (§4, §5)
5. Mid-run proxy kill: within one probe sweep the state is `lost` with evidence; `lilo doctor` emits a warning; behavior matches the Q1 ruling. (J3, §5, §7)
6. `lilo transport show <id> --output json` returns ≥1 exchange for a run that made a provider round trip; every artifact class it names is readable; no artifact class exists that neither `show` nor `export` can surface. (§8, anti-dark-ship)
7. Export bundle from a run made with a real credential contains zero occurrences of that credential's bytes. (§10, J4)
8. `lilo delete session <id>` leaves no capture rows and no `~/.lilo/data/capture/<id>` directory. (§11, J6)
9. Retention: with a test-scoped policy (e.g. `LILO_TEST_*` override), the sweeper removes expired capture and doctor reflects size before/after. (§11)
10. `xtask codegen --check` and the generated-surface guard pass with `lilo transport` verbs present; `lilo capture` still resolves to tmux pane capture. (§6)
11. Grep gate: no reference to `tm`, `transport-matters`, or its env prefix (`TRANSPORT_MATTERS_*`) in littleorgans source; no path or subprocess dependency on any transport-matters artifact. (§13)
12. Full gate `just check && just build && just test` green with all of the above included; release tagging blocked otherwise. (§12)

## Worker Status

| Worker | Scope | Final state |
|---|---|---|
| Explore #1 | littleorgans current-state surfaces: launch chain, session views, doctor, env registry, data tree, readiness/failure precedents, CLI tree, protocol gating (8 areas) | completed; report merged into Appendix A |
| Explore #2 | transport-matters evidence (NOTES/ excluded): architecture, launch contract, artifacts, readiness/failure, read surface, harness compatibility, retention, install deps (8 areas) | completed; report merged into Appendix B |

No other workers were spawned. No repo edits were made by this worker or its sub-workers.

## Appendix A: littleorgans current-state evidence (SHA 98d8928)

Every claim below was verified against the working tree at the baseline SHA.

### A1. Launch chain (six hops, no wrapper today)

`lilo run` → session app → session daemon → session driver → runtime daemon (in-process in `lilod`) → shim process → agent process.

- CLI entry: `crates/lilo/src/cli.rs` (`Command::Run(RunArgs)` via `define_commands!`), args in `internal/session/app/src/cli/cli_def.rs` (`RunArgs`, `SessionCreateArgs`). No transport or capture flag exists.
- Spawn intent: `internal/session/app/src/cli/run.rs::run` captures caller env client-side (`lilo_rm_core::capture_caller_env`) and sends `SessionRpc::Spawn` over the UDS.
- Env injection site 1: `internal/session/daemon/src/handler/spawn.rs::spawn_launch` (lines 369-407) strips `LILO_AGENT_*` then upserts `LILO_AGENT_SESSION_ID`, `LILO_AGENT_ROLE`, `LILO_AGENT_WORKSPACE`. Transaction shape: Tx A (`begin_spawn_intent`) → `runtime.spawn()` → Tx B (`complete_spawn_intent`) → `append_event`.
- Env injection site 2: `internal/runtime/launchers/src/lib.rs::runtime_env` upserts `LILO_AGENT_SESSION_ID` and `LILO_AGENT_RUNTIME`.
- argv materialization: `internal/runtime/daemon/src/api.rs::spawn_domain` line 81 (`lilo_runtime_launchers::dispatch(...).launch_spec(...)`) then line 83 `backends.prepare_launch(...)`. `HostRuntimeBackend::prepare_launch` (`internal/runtime/daemon/src/backend.rs`) is a pass-through no-op; `DockerRuntimeBackend::prepare_launch` rewrites argv (`docker run ...`) and is the existing precedent for argv wrapping. Launcher argv is literally `vec![resolved_binary]` (`internal/runtime/launchers/src/claude.rs`, `codex.rs`).
- Shim: same `lilo` binary as hidden `__shim` subcommand (`crates/lilo/src/cli.rs:326`). `internal/runtime/daemon/src/shim_socket.rs::shim_env` (lines 139-156) passes exactly one var, `LILO_SOCKET_PATH`; test `shim_env_only_contains_socket_path` asserts `env.len() == 1` and the doc comment declares widening a deliberate act requiring justification. `internal/runtime/app/src/cli/shim.rs::apply_launch_env_cwd` does `env_clear()` then layers `LaunchSpec.env` (authoritative env source). Flow: `ShimLaunch` → spawn child → `ShimReady { shim_pid, runtime_pid, start_time }` → wait → `ShimExit`.
- Env capture policy: `crates/lilo-rm-core/src/spawn_context.rs` (`CALLER_ENV_DENYLIST`, `CALLER_ENV_DENYLIST_PREFIXES` incl. `LILO_AGENT_`). No `ANTHROPIC_BASE_URL`, `HTTPS_PROXY`, or `OPENAI_BASE_URL` appears anywhere in Rust source today.
- Existing `tm`/transport references: narrative docs only (`CLAUDE.md`, `LESSONS.md`); zero code references.

### A2. Session views

- Record: `internal/session/core/src/session.rs:67 struct Session` (id, runtime, role, workspace, namespace, dir, labels, state, runtime_pid, runtime_session, transcript_path, tmux_pane, agent_config, timestamps, exit_code). JSON output is the serde derive verbatim (`internal/session/app/src/cli/get.rs`), so new fields surface in `--output json` for free.
- Human table: `internal/session/app/src/cli/output.rs::print_session_table_with_rows` headers `ID RUNTIME NAMESPACE ROLE TMUX STATUS AGE` (+`LABELS`); cells in `session_cells_with_id`. A CAPTURE column lands in these two functions.
- Schema: `internal/db/migrations/0001_unified_schema.sql` — `session_sessions` mirrors `Session` plus `owner`, `lost_evidence`; `session_spawn_intents` (status pending/resolved/aborted, `spawn_request_json` blob rides new fields without DDL change).

### A3. Doctor

- `crates/lilo/src/cli/doctor.rs` (452 lines): `DoctorStatus { daemon, database, substrates, runtime, warnings }`; `DaemonHealth` (3s RPC timeout), `DatabaseHealth::ping`, `SubstrateHealth::collect` (hardcoded sqlx COUNTs for identity_audit, active sessions, active runtimes). No check registry exists; adding a substrate check means extending these structs.
- Runtime detail: `internal/runtime/daemon/src/doctor.rs::collect` (version, migrations, lifecycles, watchers, launchers, tmux, docker, log_availability, last_probe_sweep, recent_lost). `launcher_statuses()` iterating `registered_launchers()` is the closest per-component registration seam.
- Wire types: `internal/session/core/src/proto/doctor.rs` (`DoctorResponse`, `RuntimeDoctorReport`, `DoctorFinding { severity, session_id, message }`).

### A4. Env registry and gates

- `crates/lilo-paths/src/env.rs` is the const registry (all `LILO_*` owned names). `scripts/check-env.sh --check` (python3) parses the registry and rejects any unregistered `LILO_`-looking literal; also bans legacy `RTM_|SM_|AGM_|HELIOY_`. Wired into `just check` (justfile:169-170, 206).
- Reference doc: `docs/reference/env-vars.md` with per-variable "Injected at" citations.

### A5. Data tree and storage

- `crates/lilo-paths/src/lilo.rs::LiloPaths`: `config/`, `run/`, `data/`, `logs/`, `cache/`, `tmp/` under `LILO_HOME` (default `~/.lilo`); `events_log_path()` = `data/events/runtime.jsonl`; `session_log(id)` = `logs/sessions/<id>.log`; `runtime_log_dir(id)` = `logs/runtimes/<id>`; socket `run/lilod.sock`; test `assert_default_tree` pins the tree.
- Headless stdio: `internal/runtime/daemon/src/server/config.rs::session_log_paths` → `logs/runtimes/<id>/{stdout.log,stderr.log}`.
- Event JSONL: `internal/runtime/daemon/src/event_log.rs::EventLog` (dedup keys, sync batching, retention consts).
- Postgres: single resolution chain `lilo_paths::env::resolve_database_url` (`LILO_DATABASE_URL` → settings.toml `[database]`); opened once in `internal/session/app/src/compose.rs:123` and shared by RuntimeService + SessionService.

### A6. Readiness and failure precedents

- `--ready-check`: `crates/lilo/src/cli/daemon.rs::StartArgs { ready_check }` + `internal/session/app/src/compose.rs::RunMode::ReadyCheck` — readiness proven by executing the real startup (DB open, migrations, reconcile, socket bind) then cancelling through the real teardown. Output `{"ok":true}` / one human line.
- Spawn failure: `spawn_preflight::check` conflicts → `SpawnOutcome::Conflict`; backend error cancels pending spawn; hard 10s `ShimReady` timeout (`api.rs:93`). Session layer renders `runtime_spawn_failure` string, `abort_spawn_intent` persists `aborted_reason`, CLI receives a flat `RpcResponse::Error` string (no typed error on the run path). Boot-time `reconcile_pending_spawn_intents` sweeps stale pendings.
- Lifecycle: `crates/lilo-rm-core/src/types/lifecycle.rs` — `LifecycleState { Forking, Running, Exited, Lost }`; `RuntimeEvent { Running, Terminated, Lost }` (exactly three variants; no capture-shaped slot). Probe sweep every 30s (`internal/runtime/daemon/src/reconcile.rs`, `record_probe_sweep` into `runtime_metadata`).

### A7. CLI surface is generated and guarded

- Authored source: `tools/schemas/cli.toml`; `xtask codegen` emits `generated_help.rs`, `generated_schema.rs`, `lilo_cli_surface.json`, `lilo_mcp_schema.json`; staleness guard `crates/lilo/tests/generated_surface_guard.rs`. Current verbs: run, create, get, delete, label, mail, nudge, capture (tmux pane capture), logs, wait, mcp, runtime, session, doctor, version, daemon, `__shim`. `lilo transport` does not exist.
- `lilo runtime` operator verbs: spawn, kill, nudge, capture, validate-target, status, events. `lilo session` operator verbs: config only.

### A8. Version and protocol gating precedent

- `crates/lilo-rm-core/src/version.rs`: `RUNTIME_PROTOCOL_VERSION = "0.8"` + 13 `RuntimeCapability` entries; hard exact-equality gate in `crates/lilo-rm-client/src/lib.rs:189::check_protocol_version`; soft capability-set warnings in `crates/lilo/src/cli/doctor/runtime.rs::detail_warnings`; separate client↔daemon product-version skew warning (`daemon_version_skew_warning`).

### A9. Seam table (where a capture contract lands)

| Concern | Exact seam |
|---|---|
| argv/proxy interposition | `internal/runtime/daemon/src/api.rs:81-83` (`launch_spec` → `RuntimeBackends::prepare_launch`); host backend currently no-op, docker backend is the argv-rewrite precedent |
| env injection | `handler/spawn.rs::spawn_launch` + `launchers/lib.rs::runtime_env`, both `upsert_env`-shaped |
| shim bootstrap widening | `shim_socket.rs::shim_env` (1-entry contract, guarded by test) |
| new env var | `crates/lilo-paths/src/env.rs` const registry, enforced by `check-env.sh --check` |
| new CLI verb | `tools/schemas/cli.toml` + `xtask codegen`, guarded test |
| new doctor check | extend `DoctorStatus`/`SubstrateHealth` and/or runtime `DoctorResponse` |
| new session field/column | `Session` struct + `session_sessions` DDL + `output.rs` table fns |
| readiness | `RunMode::ReadyCheck` precedent |
| compat gating | `version.rs` const pair precedent |

## Appendix B: transport-matters evidence (pinned SHA a252df2, NOTES/ excluded)

Validated lessons and gaps only; nothing here implies a dependency. Initially gathered at `ed099336` and revalidated against the pinned `a252df2` tree (see Baseline reconciliation); all cited files are identical in both.

### B1. Architecture

Hybrid two-plane system: Python ≥3.14 capture plane (`api/`, distribution `transport-matters`, deps mitmproxy ≥12.2, FastAPI, psycopg, alembic, typer, mcp) plus TypeScript product plane (`packages/` Fastify gateway/runtime/activity; `www/packages/` React inspector + canvas; `desktop/` Electron 43). `docs/ARCHITECTURE.md` "two plane rule": durable seam is the Postgres session store; live seam is the Gateway. This whole install surface (Python, mitmproxy, optional bundled Node ~120MB, pnpm) is what native Rust ownership eliminates.

### B2. Launch contract

- CLI `transport-matters claude|codex|desktop|tail|doctor|paths|list|version` (`api/src/transport_matters/cli/__init__.py`). No `tm` alias exists.
- Shared preparation seam `captured/run.py::prepare_captured_run(request) -> (CapturedRunSpawnSpec, CapturedRunLease)`; HTTP RPC `POST /v1/capture/prepare`, `/{run_id}/release`, `/{run_id}/health` (`api/v1/capture_rpc_routes.py`); TS client `packages/runtime/src/adapters/CaptureRpcClient.ts`.
- `LAUNCH-CONTRACT.md`: six stages `LaunchRequest → LaunchIntent → ResolutionContext → FrozenLaunchSpec → LaunchActuation → LaunchReceipt`; idempotency ledger `(owner, dispatch_id, candidate_key)`; 21 stable failure codes; "authentication and provider access observations never authorize or block launch".
- Claude interposition: `mitmdump --mode reverse:https://api.anthropic.com`, child gets `ANTHROPIC_BASE_URL=http://127.0.0.1:<port>`; `trust_requirement: "none"` (`shared/harness_descriptors_v1.json`). Codex: explicit proxy (`HTTP(S)_PROXY` et al.) + `CODEX_CA_CERTIFICATE` process-scoped merged bundle (`cli/trust.py::resolve_codex_ca_certificate`), CA never installed system-wide.
- Session id: `cli/launch_profile.py` — Claude `mints_session_id = True` (argv `--session-id <uuid>`); Codex `mints_session_id = False` (resume over pre-seeded rollout). Env source of truth `env_keys.py` (`ENV_PREFIX = "TRANSPORT_MATTERS_"`); rich self-identity JSON `TRANSPORT_MATTERS_RUN_IDENTITY` (`run/identity.py::RunSelfIdentity`).
- Env hygiene: `launch/environment.py::build_managed_child_env` strips ~35 proxy vars + 9 trust vars, pins `NO_PROXY=127.0.0.1,localhost`; credential denylist `HARNESS_CREDENTIAL_ENV_KEYS` (`ANTHROPIC_API_KEY`, `CLAUDE_CODE_OAUTH_TOKEN`, `CODEX_ACCESS_TOKEN`, `OPENAI_API_KEY`, ...).

### B3. Capture artifacts

- Tier-1 disk per run: `<channel home>/workspaces/{slug}/{hash}/{run_id}/` with `lock` (flock = only liveness truth), `manifest.json` (advisory beacon, unlinked on exit), `index.jsonl`, `sessions.json`, `compatibility.json`, `transcripts/<session_id>.jsonl` (byte-faithful owned copy; tailer-offset gap is a hard failure), `logs/mitmdump.log`, one dir per exchange (`storage/disk_layout.py::ExchangeArtifactPaths`: `entry.json`, `request.raw`, `request.ir.json`, `request.curated.*`, `request.audit.json`, `response.raw`, `response.ir.json`, `transport.json`, `events.jsonl`, `turn.json`); atomic `.tmp`/`.bak`/`.del` discipline.
- Postgres store: 32 forward-only alembic revisions (`0001_session_store_foundation` – `0032_space_worktree_ownership`); core tables `session`, `event` ((session_id, seq) PK, raw+ir jsonb, generated tsvector FTS), `artifact`, `event_artifact` (ON DELETE CASCADE). Identity rule: minted native id is the PK for Claude (`storage/session_facts.py`, `cli/launch_profile.py :: mints_session_id`); Codex PK synthesized as `uuid5(SESSION_NS, f"{run_id}|{provider}|{native_session_id}")` (`index/sessions.py :: synth_session_id`) — native ids are per-harness, unstable as external keys.
- Wire store (migration 0008) ships dark: `wire_store_observer` writes exchanges/blobs and "nothing reads them back" (`TLDR.md`). Fidelity diff retired/never shipped as a read surface; only `request_diff.py::request_unchanged` (original vs curated IR) exists.

### B4. Readiness and failure

- Readiness = TCP accept (`loopback.py::wait_for_port_ready`, 5s timeout, 0.1s interval); no HTTP health on the proxy itself. Bind conflict vs timeout distinguished via `EADDRINUSE` in the mitmdump log (`cli/bind_failure.py`); 3 retry attempts with port reallocation (`_BIND_RETRY_ATTEMPTS`).
- Spawn order fixed: proxy first, then client (`cli/runner.py::run_client_children_until_outcome`).
- Proxy death: TTY path brings the client down too, exit 1; managed path polls `GET /v1/capture/{run_id}/health` every 3s, degrades after 3 failures (immediately on `alive: false`/404) → `RunManager.settleRun({kind: "capture-lost"})` — run torn down on capture loss.
- Orphan prevention: `self_reap.py` (PDEATHSIG / ppid watchdog, 20s force exit).
- Fail-closed preflights: Postgres (`session_store_preflight.py`, migrate-under-advisory-lock or stop with instructions), harness enablement, control-plane grant. Fail-open: compatibility verdicts (advisory build constant `COMPATIBILITY_ROLLOUT`). Never a gate: provider auth.

### B5. Read surface

- CLI: `list` (manifest scan + lock probe, `--json`), `paths`, `doctor --reap-orphans`, `tail`, `channel`, `db`. No `show <session>` and no export command exist.
- REST: `/v1/sessions` (+detail, events, timeline, SSE), `/v1/runs/{run_id}/exchanges` (+detail, turn-content, tokens), run/control-plane routes, MCP at `/mcp` (13 tools incl. `whoami`, `roster`, `conversation`, `launch`, `close`). Inspector SPA at `/`, canvas at `/canvas`; each web UI serves exactly one run, no aggregate view.

### B6. Harness compatibility

`shared/harness_descriptors_v1.json`: claude (reverse, no trust), codex (explicit, CA, websocket/transport diagnostics extras), grok declared but `launch: null`. Compatibility releases pin per-facet revisions with digests (`harnesses/compatibility_releases_v1.json`); optimistic range support with advisory runtime drift detection (CI fails on unknown shapes; runtime never blocks); stable outcome codes (`harness_not_installed`, `harness_update_required`, `harness_version_blocked`, ...).

### B7. Retention and deletion (the gap)

No Tier-1 retention, size cap, or sweeper; per-exchange delete exists in the storage layer but is unexposed on any route; the one retention constant is delivery-ledger cleanup (30 days, at API startup); whole-channel reset (`scripts/reset-channel-store.sh`) is the only bulk deletion; session-row cascade exists but nothing calls it.

### B8. Install and runtime deps

`curl | bash` installer → uv tool install; requires Python ≥3.14, mitmproxy 12.x, mandatory Postgres 17, Node ≥20 for the gateway (optional ~120MB bundled wheel), pnpm for source builds; `~/.mitmproxy` CA needed for Codex only. docker-compose provides dev Postgres only. Degradation without Node: canvas 503s while detached CLI capture still works.
