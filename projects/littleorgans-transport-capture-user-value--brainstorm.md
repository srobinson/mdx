---
title: littleorgans mandatory capture — product value and operator jobs
type: research
tags: [ux-research, littleorgans, transport, capture, product-value]
summary: Evidence-grounded study of the product value and operator jobs created by mandatory wire capture in lilo run
status: complete
source: ux-researcher
confidence: medium
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

# littleorgans mandatory capture: product value and operator jobs

## Scope and evidence baseline

- Subject: product value and operator jobs created by mandatory capture inside littleorgans, where capture is a side effect of every `lilo run`.
- Evidence repos (exact SHAs):
  - littleorgans monorepo @ `98d8928941b5b5db670ed73ed06af57f61dcfa0a`
  - transport-matters pinned phase-one baseline @ `a252df24a7e3cc0f7dabd3fa1faef35d6f052b55` (research input only; `NOTES/` neither read nor cited)
- Constraints honored: no repo edits, no checkout; `tm`/transport-matters treated as pattern evidence, never as a dependency (consistent with the working-tree LESSONS.md direction: implement Transport natively under littleorgans ownership).
- Baseline revalidation: the initial transport sweep ran at `ed099336ebfa9e72da32ed547b29b932f077ccbd`, a direct descendant of the pinned `a252df24` (3 commits ahead; verified `git merge-base --is-ancestor`). Every transport-derived finding was revalidated against the immutable `a252df24` tree via read-only `git show`/`git grep` (no checkout, no repo edits). The full delta (`git diff --stat a252df24..ed099336`) touches only `NOW.md` wording, a new first-run harness evidence card slice under `www/packages/canvas/src/firstrun/` plus `harnessInventory` types, and a 14-line credential change to `www/packages/core/src/transport.ts`. Nothing under `api/src/transport_matters/`, `packages/runtime/`, `www/packages/inspector/`, `desktop/`, or any other cited top-level doc changed, so all appendix B paths, symbols, quotes, and line anchors hold at `a252df24` except one line shift noted in B8. Later-only evidence is labeled explicitly at the end of appendix B.
- Method: two parallel code sweeps (one per repo) producing path+symbol evidence, synthesized by a single researcher. Findings below are tagged Fact (observed in code/docs at the stated SHA), Inference (pattern drawn from facts), or Recommendation.

## Worker Status

| Worker | Scope | State |
|---|---|---|
| Explore (littleorgans) | Capture/transport surfaces in littleorgans @ 98d8928: launch chain, env registry, session lifecycle, doctor, events/audit, failure semantics, privacy | COMPLETE — evidence in appendix A |
| Explore (transport-matters) | Capture stack in transport-matters @ ed09933: proxy core, launch contract, read surfaces, fidelity diff, sharing, privacy, degraded modes, doc intent (NOTES/ excluded) | COMPLETE — evidence in appendix B |
| Baseline revalidation (solo) | Revalidate all transport-derived findings against pinned a252df24 via read-only git show/git grep; label later-only evidence | COMPLETE — see Scope §Baseline revalidation and appendix B |

## Executive summary

Mandatory capture converts the operator question "what did my agent actually do?" from unanswerable into a one-command answer, with zero setup, for every run by construction. The strongest evidence for its value is a live defect in littleorgans today: `lilo logs` returns nothing for tmux sessions (`lifecycle_transcript_path()` yields `None` for `TmuxPaneSnapshot`), leaving `lilo capture`, an ANSI scrollback scrape, as the only inspection tool. transport-matters proves the mechanism is buildable and enforceable (deterministic child env that cannot bypass the proxy; capture death terminates the run) but also proves the governance gap: bodies are stored verbatim with no retention, no payload redaction, and no sharing surface. The product opportunity is capture that is invisible when things work, decisive when they do not, and governed from day one.

## 1. Operator jobs-to-be-done

Ranked by how directly the evidence supports value today.

1. **Reconstruct what happened after the fact** (debugging). Fact: littleorgans cannot do this for tmux sessions (A4). Fact: TM records raw request/response bytes, parsed IR, per-frame transport artifacts, and turn summaries per exchange (B1). This is the job mandatory capture wins outright.
2. **Confirm my launch actually worked** (launch confidence). Fact: littleorgans `ShimReady` proves only that a process started (A1, A7). Fact: TM's `PromptReceipt` defines `submitted` as "exactly one correlated provider exchange finalized with positive response evidence" (B2, LAUNCH-CONTRACT.md). Inference: capture upgrades launch truth from "process spawned" to "agent reached the provider and got a response."
3. **See what my agent is doing right now** (live inspection). Fact: TM streams exchange events over SSE and shows live token/elapsed vitals (B3). littleorgans has only the pane scrape.
4. **Understand why a specific turn went wrong**. Fact: TM's `ExchangeDetail` exposes original vs curated request, audit entries, and authoritative token counts (B3, B4).
5. **Respond to an incident**. Fact: TM has run-level `interrupt`/`close`/`terminate` and an explicit `capture_lost` settled state (B5, B8). littleorgans has SIGTERM/SIGKILL escalation but no capture-informed incident surface.
6. **Prove what happened** (compliance, enterprise). Fact: TM has canonical JSON digests, sha256 content addressing, blake2b artifact hashes, immutable-on-create evidence rows, `mutated_manually` stamping, and attributed action audit (B9). littleorgans has decision-only `identity_audit` written inside the spawn transaction (A6).
7. **Hand a session to another person or agent** (sharing). Fact: neither repo ships sharing; TM's closest primitives are a single-exchange local HTML download and an MCP `conversation` read tool (B6). This job is unmet and is the natural second act.
8. **Control what is retained**. Fact: nothing in either repo governs captured content: no retention, no TTL, no purge API, header-only redaction in TM, none in littleorgans (A8, B7). This job must be created alongside capture, not after.

## 2. User journeys

Each journey: today (fact), with mandatory capture (design intent), friction to resolve.

### J1. Launch confidence
- Today: operator runs `lilo run claude`, sees a pane appear. If the agent silently fails after spawn (bad credentials, provider outage), littleorgans reports Running until termination; nothing distinguishes "working" from "spinning" (A1, A7: `ShimReady` is the only success signal).
- With capture: first correlated exchange is the real "it's alive" event. `lilo get session` can show first-exchange time and receipt state; a session that never produces an exchange is visibly suspect. Pattern proof: TM `PromptReceipt` `submitted|unknown|failed` (B2).
- Friction: littleorgans `RuntimeEvent` has exactly three variants (A6); a first-exchange or receipt event is a new variant plus an `EventLogKind`.

### J2. Session inspection
- Today: `lilo get session` shows lifecycle metadata; `lilo logs` works only for headless sessions; tmux sessions fall back to `lilo capture`'s ANSI scrape with no turn structure (A4).
- With capture: `lilo logs` gains a provider-truth turn stream for every session type; `lilo get session` can show turn count and token totals. Pattern proof: TM `IndexEntry` fields (`ts`, `model`, `req`/`res` stats, track lineage) and the paged exchanges API (B1, B3).
- Friction: none structural; the join key (`LILO_AGENT_SESSION_ID`) already reaches every spawned process (A3), and TM's env design anticipates the prefix rename as a one-line change (B2).

### J3. Debugging a bad turn
- Today: impossible below the pane surface. No request bytes, no response bytes, no token accounting anywhere in littleorgans (A2, A4).
- With capture: per-turn artifacts (raw request, parsed IR, response, events) keyed by SessionId; the operator moves from "the agent seemed confused" to "turn 14's request contained X and the provider answered Y."
- Friction: storage governance (see J6) must exist before bodies land on disk.

### J4. Sharing a session
- Today: unmet in both repos (B6). Operators copy pane text.
- With capture: a captured session is a serializable artifact correlated by SessionId; the v1 handoff can be file-based (TM's self-contained HTML export pattern, `exportInspect.ts`) and agent-facing (an MCP `conversation`-style capped read tool, per CONTROLPLANE principle "push carries references, pull carries content").
- Friction: no share-link infrastructure exists anywhere; defer links, ship local export plus agent read surface first (see anti-features).

### J5. Incident response
- Today: `lilo mail`/`lilo nudge`/kill are the levers; evidence of what the agent did is lost with the pane scrollback.
- With capture: the incident record is already written when the incident is noticed. `capture_lost` (B8) becomes a first-class lifecycle evidence state; audit rows plus turn artifacts reconstruct the timeline without operator foresight.
- Friction: littleorgans has no degraded-lifecycle concept (A7); `capture_lost` requires one.

### J6. Compliance and retention review
- Today: `identity_audit` proves decisions, not content (A6). Nothing proves what an agent sent to a provider, and nothing limits how long anything is kept.
- With capture: every session carries hashed, timestamped, immutable-on-create evidence (patterns in B9) plus a retention policy and purge verb that make the evidence governable.
- Friction: this is the largest unbuilt surface; TM's gap list (no TTL, no purge API, manual `wire-gc`, header-only redaction, B7) is the checklist.

## 3. Privacy controls

- Fact: littleorgans' entire privacy posture is env-var scoped: caller-env denylist, tmux argv secret guard, DB URL redaction (A8). No content governance exists because no content is stored.
- Fact: TM redacts sensitive headers at write time (`transport_redaction.py` denylist: authorization, cookies, api-key families) but stores request/response bodies and websocket payloads verbatim; its transcript denylist is presentation-only and "never strips content from the wire" (B7).
- Inference: mandatory capture makes littleorgans a custodian of prompt and response content for the first time; the existing "never logged" convention for `LILO_GITHUB_PAT` (A8) is not an enforceable model for payload data.
- Recommendations (priority order):
  1. Header redaction at write time from day one; adopt TM's denylist shape. (engineering, high)
  2. Retention policy with a default TTL and an operator purge verb; scheduled GC, not manual. (engineering, high)
  3. A capture-consent/audit event: the first content-writing subsystem should announce itself in `identity_audit`, which today records only decisions. (engineering, medium)
  4. Payload secret scanning is an open research question, not a v1 blocker; flag it explicitly rather than implying coverage. (design+engineering, medium)

## 4. Failure communication, empty and degraded states

- Fact: littleorgans' launch path is strictly fail-closed; no partial-degradation state exists in `SpawnOutcome`, `Lifecycle`, or `SessionState` (A7).
- Fact: TM splits the invariant precisely: the proxy is mandatory (capture death terminates the run, both desktop and CLI paths, B8), while durable persistence is best-effort (persist failures are swallowed so "the wire path never fails because of an observer," B8).
- Inference: this split is the correct product contract. Capture liveness is a run invariant; capture persistence is an observer that must never kill a run.
- States to design:
  - **Empty session** (zero exchanges): must distinguish "agent never reached the provider" (a launch-confidence failure, J1) from "capture data missing" (a capture failure). TM's receipt semantics provide the vocabulary.
  - **Capture lost mid-run**: run settles with explicit evidence (`capture_lost` pattern, B8); `lilo get session` and the exit diagnostic must both say so. littleorgans' typed `Diagnostic` kernel and exit-code registry (A7) are the delivery mechanism; capture needs its own codes.
  - **Doctor**: `DoctorStatus` and `DoctorResponse` have no transport slot (A5) and CLAUDE.md forbids a per-substrate doctor; capture health must appear as a new axis inside the existing 5-line doctor block.
  - **Error copy**: today's `lilo logs` failure text ("no transcript available for session {id}") becomes the empty-state message only for truly exchange-less sessions; for everything else it becomes an answer.

## 5. Enterprise buyer proof

- Fact: proof primitives already demonstrated in TM: canonical JSON digests, sha256 content addressing, blake2b artifact hashes, immutable-on-create certification and drift evidence rows sealed against owned capture evidence, deterministic dispatch ids, server-minted identity ("a caller is its run"), and human-edit stamping (`mutated_manually`, `OverrideAudit`) (B9).
- Fact: littleorgans contributes the decision-side proof: authorization audit committed inside the spawn transaction, including denials (A6).
- Inference: the enterprise story is "every agent action on this host is evidenced by construction: who authorized it, what was sent, what came back, whether a human touched it." No competitor claim survives contact with an opt-in capture model; mandatory is the proof.
- Gaps that a buyer will probe (facts): no retention/deletion story, no payload redaction, no per-turn latency/TTFT telemetry anywhere (B7, B9). Recommendation: treat retention and redaction as enterprise-gating; treat latency telemetry as deferrable.
- Context: NORTHSTAR.md prices the wedge at $199 or $19.99/month against $400 to $1000/month agent spend; the buyer's alternative today is trusting harness self-report.

## 6. Product principles

1. **Capture is a property of the platform, not a feature.** No enable flag, no setup, no partial mode the operator must reason about. Enforced structurally: a deterministic child env "that cannot bypass proxy or trust" (B2) at the single exec seam littleorgans already isolates (`runtime_command`, `resolve_binary`, A1).
2. **Proxy liveness is a run invariant; persistence is best-effort.** If capture cannot come up or dies, the run fails or settles visibly (B8); if a disk write fails, the wire proceeds and the gap is recorded. Never invert these.
3. **One id is the spine.** `SessionId` (already injected as `LILO_AGENT_SESSION_ID` into every spawn, A3) keys every artifact from authorization to wire bytes. No provider-minted or capture-local id ever surfaces to the operator.
4. **Provider truth over harness self-report.** The wire and the transcript are captured and never collapsed; their difference is the long-term product (B4, B10). littleorgans should preserve both streams from day one even though the diff ships later.
5. **Silence is the success state.** A healthy captured run looks identical to an uncaptured one: no new output, no perceived latency, nothing to configure. Capture speaks only through existing verbs (`lilo logs`, `lilo get session`, `lilo doctor`) when asked or when something breaks.
6. **Content capture ships with content governance.** Header redaction, retention, and purge are part of the first release, because littleorgans has zero existing infrastructure for governing stored content (A8) and TM demonstrates the cost of deferring it (B7).
7. **Evidence is attributed and immutable-on-create.** Adopt TM's discipline: hashes computed over canonical serialization, records that reject divergent rewrites, human mutations stamped on the record (B9).

## 7. Anti-features

1. **No capture opt-out flag.** An off switch destroys the enterprise proof and the debugging guarantee. Privacy is served by retention and redaction controls, not bypass.
2. **No `lilo transport doctor`.** CLAUDE.md locks doctor as a single top-level aggregate (A5); transport health is a row inside it.
3. **No capture of agent-run shell commands.** TM deliberately scopes capture to model traffic and strips proxy vars from agent-spawned shells (B2, B8 summary). Wire capture is not host keylogging; crossing that line changes the product's trust category.
4. **No always-armed interception.** Pause-and-edit (TM's most complete feature, B5) is explicit, one-shot, and audited; capture-by-default must never imply intervention-by-default.
5. **No public share links in v1.** No sharing infrastructure exists in either repo (B6); ship local export and an agent-facing capped read surface first.
6. **No blocking the hot path on durable writes.** TM's sink fan-out swallows observer failures by design (B8); littleorgans must not put Postgres in the request path.
7. **No self-declared identity in capture records.** Identity is minted at spawn and resolved server-side (B9); captured artifacts never trust the child process's claims about itself.
8. **No capture chrome in normal-run output.** Nothing prints on success; see principle 5.
9. **No runtime dependency on `tm` or transport-matters.** They are research evidence; littleorgans implements Transport natively (working-tree LESSONS.md direction, A9).
10. **No analytics dashboards before governance.** Token/cost/latency reporting waits until retention and redaction exist; storing more derived views of ungoverned content compounds the liability.

## 8. What should remain invisible

Fact-grounded list of machinery the operator should never see in a healthy run:

- Proxy mechanics: process supervision, port allocation and retry, listen-port demux (B1, B8).
- Trust plumbing: CA material, env stripping and re-setting, `NO_PROXY` scoping, harness home redirection (B2).
- Storage internals: run-dir layout, tmp/activate/rollback write protocol, index rewrites, content-addressed wire store (B1).
- Correlation plumbing: transcript tailing, exchange-id containment probes, owned-session minting (B4, B9).
- Drift detection: schema-drift evidence accumulates silently until a human needs it (B4).
- Token counting and curation audit: computed and stored, surfaced only on inspection (B3, B5).
- The reaper: parent-death self-reaping and orphan cleanup (B8).

The operator-visible surface is exactly: session verbs that now return real answers, one doctor row, and failure states that name themselves.

## Sources consulted

- littleorgans @ `98d8928` — code sweep across `crates/`, `internal/`, `docs/reference/env-vars.md`, `docs/architecture/session.md`, migration `0001_unified_schema.sql`; working-tree LESSONS.md delta (uncommitted, noted as such).
- transport-matters — code sweep at `ed09933` across `api/src/transport_matters/`, `www/packages/`, `packages/`, `desktop/src/`; top-level docs README.md, TLDR.md, PROJECT.md, NORTHSTAR.md, CONTROLPLANE.md, LAUNCH-CONTRACT.md, RUN-IDENTITY.md, HARNESS-COMPATIBILITY.md, docs/ARCHITECTURE.md, NOW.md; all findings revalidated against pinned `a252df24` via read-only `git show`/`git grep`/`git diff` (see Scope §Baseline revalidation). `NOTES/` excluded per directive.

## Open questions

1. Fail-closed vs settle-visible: when the proxy dies mid-run, TM kills the run (B8); is that acceptable for long-lived littleorgans sessions, or does a degraded-but-alive state earn its complexity? (Decision needed before the lifecycle model is extended.)
2. Where does the capture plane live in the monorepo: which bounded context owns storage, and does the wire store share the operator Postgres or isolate? (Out of scope here; flagged because governance answers depend on it.)
3. What is the minimum viable `lilo logs` rendering of a captured turn stream (transcript projection vs raw exchanges)?
4. Payload secret scanning: feasible at write time without unacceptable false positives? No evidence in either repo.
5. Does the fidelity diff (wire vs transcript) justify capturing owned transcript snapshots from v1, given TM's wire store shipped dark with zero readers? (Inference in principle 4 says yes; cost unquantified.)

---

## Evidence appendix A: littleorgans @ 98d8928

### A1. Launch chain and the exec seam

- `crates/lilo/src/cli.rs` — `Command::Run`, `define_commands!` (full verb registry; no `Transport` variant).
- `internal/session/app/src/cli/run.rs` — `run()` → `spawn_session()` → `SessionRpc::Spawn`.
- `internal/session/daemon/src/handler/spawn.rs` — `DaemonState::spawn()`, `spawn_launch()`, two-phase `begin_spawn_intent()` / `complete_spawn_intent()` / `abort_spawn_intent()`, `OnCommitFailure`.
- `internal/runtime/daemon/src/api.rs:81` — `spawn_domain()` → `lilo_runtime_launchers::dispatch(..).launch_spec(..)` decides argv.
- `internal/runtime/app/src/cli/shim.rs` — hidden `lilo __shim`; `runtime_command()` (shim.rs:119) is the exec seam: `Command::new(launch.command()?)`. No wrapper interposed.
- `internal/runtime/launchers/src/lib.rs` — `resolve_binary()` shells out to `which claude`; the single function that would change for interposition.
- `crates/lilo-rm-core/src/launcher.rs` — `LaunchSpec { argv, env, cwd, shell_resume }`: no field for wrapper, proxy endpoint, or capture sink.

### A2. Transport in code: absent

- Zero transport crates, binaries, CLI verbs, feature gates, TODOs. Only forward hook: `internal/runtime/daemon/src/tmux_busy.rs:7` comment ("future transport or shim turn signal can replace the scrape in one place").
- Vestigial recorder vocabulary: `crates/lilo-rm-core/src/capture.rs::LogsUnavailableReason::{CaptureDisabled, PipeInUse, RecorderFailed}` — never constructed in production code.
- One transport commit ever (`6c267da`), touching CLAUDE.md only.

### A3. Join key is live before capture exists

- Registry: `crates/lilo-paths/src/env.rs` — `LILO_AGENT_SESSION_ID` (L35) plus `LILO_AGENT_RUNTIME/ROLE/WORKSPACE`.
- Injection: `handler/spawn.rs::spawn_launch()` (strips inherited `LILO_AGENT_*`, upserts fresh) and `launchers/src/lib.rs::runtime_env()`.
- Denylist capture: `crates/lilo-rm-core/src/spawn_context.rs::CALLER_ENV_DENYLIST(_PREFIXES)`.
- In-repo readers: `internal/session/app/src/mcp/server.rs:19`, `internal/session/app/src/cli/mail.rs:319`.

### A4. Inspection surfaces and the live gap

- `lilo get session` (`internal/session/app/src/cli/get.rs`), `lilo wait` (`cli/wait.rs`), mail/nudge (`cli/mail.rs`, `internal/session/daemon/src/handler/messaging.rs`).
- `lilo logs` (`cli/logs.rs` → `SessionRpc::Logs`): server errors "no transcript available for session {id}" (`internal/session/daemon/src/polish.rs:29-34`).
- **Live defect surface**: `internal/session/core/src/paths.rs::lifecycle_transcript_path()` returns `Some` only for `LogAvailability::Headless`. tmux sessions get `None`: `lilo logs` does not work for tmux-targeted sessions; operator recourse is `lilo capture` (`cli/capture.rs`, `TmuxGateway::capture_pane`), an ANSI pane scrape bounded by scrollback, with no turn structure and no provider-side truth.
- Schema: `internal/db/migrations/0001_unified_schema.sql` — `session_sessions` (incl. `runtime_session`, `transcript_path`, `lost_evidence`), `session_spawn_intents`, `runtime_lifecycle`, `identity_audit`.

### A5. Doctor and health

- `crates/lilo/src/cli/doctor.rs` — `DoctorStatus { daemon, database, substrates, runtime, warnings }`; `internal/runtime/daemon/src/doctor.rs::DoctorResponse`.
- No transport/capture slot in either struct. CLAUDE.md forbids per-substrate doctor verbs, so transport health must land inside `DoctorStatus`.

### A6. Events and audit

- Event vocabulary is exactly three variants: `crates/lilo-rm-core/src/types/lifecycle.rs::RuntimeEvent { Running, Terminated, Lost }`; JSONL via `internal/runtime/daemon/src/event_log.rs::EventLog`. No turn/capture/wire event exists.
- Audit: `crates/lilo-im-core/src/audit.rs::AuditRow` (session_ref-keyed), written inside the spawn transaction (`handler/spawn.rs:107-119`); denials commit the audit row before erroring. Audit records decisions, never content; no data-collection consent event exists.

### A7. Failure semantics: strictly fail-closed

- `crates/lilo-common/src/diagnostic.rs::Diagnostic`, exit codes in `exit_codes.rs`.
- Every launch-path dependency failure aborts the spawn: preflight conflicts (`spawn_preflight.rs`), 10s `ShimReady` timeout (`api.rs:96`), shim reconnect exhaustion (`shim.rs::reconnecting()`), commit failure → SIGTERM (`OnCommitFailure::AbortRunning`).
- No partial-degradation state exists in `SpawnOutcome`, `Lifecycle`, or `SessionState`.

### A8. Privacy posture: env-only, no content governance

- `LILO_GITHUB_PAT` rides generic caller-env passthrough (`spawn_context.rs` test asserts survivors `["PATH", "LILO_GITHUB_PAT", "ANTHROPIC_API_KEY"]`); "never logged" is convention, not an enforced invariant.
- One real secret-boundary invariant: `internal/runtime/daemon/src/tmux.rs:341-355` — secrets never in `respawn-pane -e` argv (world-readable via ps); env travels over post-spawn UDS.
- `internal/db/src/lib.rs:139::redacted()` for DB URLs; `SHELL_RESUME_ENV_ALLOWLIST` (allowlist, not denylist).
- No content redaction, PII handling, retention policy, or opt-out anywhere.

### A9. Direction signal (working tree, not in 98d8928)

Two uncommitted LESSONS.md lines (current intent): treat Transport capture as a first-class littleorgans product context, capture by construction in `lilo run`; and treat `tm`/transport-matters as experimental research only — littleorgans must not invoke, package, or depend on them, but should learn from their proven capture, durability, and fidelity patterns, then implement Transport natively. This supersedes the CLAUDE.md "`lilo run claude` execs `tm claude`" framing.

## Evidence appendix B: transport-matters @ a252df24 (pinned baseline)

Gathered at descendant `ed09933`, revalidated against `a252df24`: every path, symbol, quote, and line anchor below was confirmed present in the `a252df24` tree (the `api/src/`, `packages/runtime/`, `www/packages/inspector/`, and `desktop/` subtrees are byte-identical between the two commits), except the one line shift noted in B8.

### B1. Proxy/capture core

- Interception: mitmproxy addon `api/src/transport_matters/addon.py::TransportMattersAddon`; handlers in `addon_handlers.py` (`handle_http_request` L176, `handle_response` L457, `handle_codex_websocket_message` L279) filter to `/v1/messages` and Codex responses flows; non-matching traffic passes through.
- Pipeline: `request_pipeline.py::parse_request_ir/run_pipeline`; streaming tee `response_stream.py::install_response_tee`.
- Recorded per exchange (`storage/base.py::ExchangeArtifacts` L149): `request_raw`, `request_ir`, `request_curated_raw/ir`, `request_audit` (`OverrideAudit`), `response_raw/ir`, `transport` (per-frame `TransportMessageArtifact`), Codex `events`/`turn`. Index: `IndexEntry` (L115) with req/res/pipeline stats, `mutated_manually`, track/subagent lineage.
- Storage tiers: disk (`storage/disk.py::persist_exchange` L230, tmp→activate→rollback protocol; layout under `~/.transport-matters/workspaces/...` with `index.jsonl`, per-exchange dirs) and content-addressed sha256 Postgres wire store (`session/wire_store.py`, migration `0008_wire_store`).
- Sink fan-out keeps observers out of the hot path: `storage/exchange_sink.py::emit_to_index` and friends.

### B2. Launch wrappers and the mandatory-capture mechanism

- No `tm` binary, no `LILO_*` vars; console script `transport-matters` (`api/pyproject.toml:58`); commands `claude`, `codex`, `doctor`, etc. (`cli/__init__.py`).
- Env contract `env_keys.py` (`TRANSPORT_MATTERS_` prefix; docstring says the littleorgans rename is "a one-line change"). Correlation carriers: `TRANSPORT_MATTERS_RUN_ID`, `TRANSPORT_MATTERS_OWNED_NATIVE_SESSION_ID`.
- Enforcement: `launch/environment.py::build_managed_child_env` (L216) strips inherited proxy/trust vars, then sets proxy vars, process-scoped CA, and harness home; docstring: "Return a deterministic child env that cannot bypass proxy or trust." No sudo, no system proxy, no global cert (README.md).
- Launch contract (`LAUNCH-CONTRACT.md`): six stages ending in `LaunchReceipt`; `PromptReceipt.submitted` requires "exactly one correlated provider exchange finalized with positive response evidence"; stable failure-code table. Implementation `controlplane/launch_service.py`, `launch_ledger.py`.
- Spawn paths: CLI `cli/runner.py::run_client_children_until_outcome` (L448); shared seam `captured/run.py::prepare_captured_run` (L185); desktop lease RPC `capture_rpc.py` + `api/v1/capture_rpc_routes.py` consumed by `packages/runtime/src/service/RunManager.ts`.

### B3. Read/inspection surfaces

- API `api/v1/`: paged `GET /v1/runs/{run_id}/exchanges`, `.../exchanges/{id}` (`ExchangeDetailResponse`), `.../turn-content`, `.../pipeline_tokens` (with degradation `reason`), SSE `GET /v1/runs/{run_id}/stream`, session timeline routes (`session_routes.py`, projection `session/timeline.py::project_timeline` L65).
- UI `www/packages/inspector/`: `ExchangeList.tsx`, `ExchangeDetail.tsx` + `detail/InspectTab.tsx`, `TokenBar.tsx`, `CodexTimeline.tsx`. Canvas viewers registry incl. read-only `ArkExchangeViewer.tsx` (4 tabs, test asserts no edit affordances) and `RunVitalsStrip.tsx` (live tokens/elapsed).
- Stubs (absence evidence): `TraceView.tsx` and `RecallView.tsx` render `ComingSoonRoute`; `OverlaysView.tsx` notes the apply-at-intercept pipeline "does not live here yet."

### B4. Fidelity diff: direction, not shipped

- PROJECT.md: "Wire versus transcript diff remains a product direction." TLDR.md: two streams "captured and never collapsed... Their difference is the product"; the wire store "ships dark... nothing reads them back" (verified: zero read-side SQL against `wire_` tables).
- What exists: original-vs-curated request diff (`request_diff.py::request_unchanged/outbound_request_if_changed`; UI `TextOverrideEditor.tsx` with `diffLines`); schema drift detection (`drift_capture.py::detect_unknown_shapes` L80, `WireDriftObserver` L174, evidence table via migration `0023`); wire↔transcript correlation plumbing (`session/exchange_correlation.py`, `storage/transcript_snapshot.py` byte-faithful tee).

### B5. Pause-and-edit (most complete feature)

- `breakpoint.py` (`PausedFlow`, `arm/disarm/pause/release/drop`, global `pause_serializer()`); `pause_session.py::handle_breakpoint` L296; routes `api/v1/breakpoint_routes.py` (release with edited `InternalRequest`, release-unmodified, re-audit with authoritative `count_tokens` recount, drop); persistent overrides `overrides/` with `OverrideAudit`; editor suite `www/packages/inspector/src/components/editor/`.
- Semantics: `off | armed_once`, holds exactly the next outbound turn, no timeout on the hold; edits stamp `mutated_manually=True`. Run-level `interrupt`/`close`/`terminate` in `controlplane_routes.py`.

### B6. Sharing/export: absent

- No share link, session export, or handoff serialization (grep-verified). Closest: single-exchange self-contained HTML download (`www/packages/inspector/src/lib/exportInspect.ts::downloadInspectHtml`) and the MCP control plane (`api/v1/controlplane_mcp.py`: `conversation`, `roster`, `launch`, `watch`, ...) returning capped plain-text transcript projections.

### B7. Privacy/redaction

- Header-only redaction at write time: `transport_redaction.py` (denylist authorization/cookie/api-key families; `Bearer [redacted]`). Presentation-only transcript denylist (`transcript_denylist.py`: "It never strips content from the wire").
- Credential discipline: broker mints access-only short-lived credentials (`credential_broker.py`); secrets written 0600 atomically (`atomic_io.py`); certification records scrubbed by construction (`harnesses/certification.py`).
- Gaps: no body/payload scanner (bodies and frames verbatim); no retention/TTL/scheduled deletion; `db wire-gc` is manual (`cli/db_cmd.py` L68); per-exchange deletes only on dropped/errored flows.

### B8. Failure/degraded modes

- Capture death terminates the run: desktop `packages/runtime/src/service/CaptureHealthMonitor.ts` (3s poll, threshold 3, immediate on `alive:false`/404) → `RunManager.settleRun({kind:"capture-lost"})` (RunManager.ts L548, wire mapping to `capture_lost` L673-674 at `a252df24`) → contract close reason `capture_lost` (`packages/contract/src/runtime/index.ts`), surfaced in `www/packages/core/src/transport.ts` L404 at `a252df24` (L418 at `ed09933` after an unrelated credential change); CLI: mitmdump exit brings the client down, exit 1 (`cli/runner.py` L448 docstring). The agent never runs uncaptured.
- Backend death: proxy self-reaps (`self_reap.py::install_parent_death_reaping`).
- Persistence is best-effort: `exchange_recorder/__init__.py::persist_exchange` (L61) swallows all exceptions; "emit_to_index swallows any failure so the wire path never fails because of an observer"; drift emission best-effort by design.
- Postgres down: degrade to 503s, don't crash (`main.py::_start_session_store` L175); launch preflight hard-blocks (`session_store_preflight.py`); transcript write quarantine with dead-letter (`session/quarantine.py`).

### B9. Compliance/audit primitives

- Hashing: `canonicalization.py::canonical_json`; `wire_normalization.py::_sha256` content addressing; `session/artifacts.py::ARTIFACT_HASH_ALGO = "blake2b-256"`; certification digests sealed over owned capture evidence, failing closed on absent artifacts (`harnesses/certification.py`, `certification_evidence.py`).
- Immutability: blocks/compat/certification rows immutable-on-create ("a replayed create is a no-op"; divergent content under a reused id rejected); `write_atomic_bytes_once`; append-only transcript snapshots with gap errors. Caveat: the disk index is rewrite-based (`_rewrite_index`), not truly append-only.
- Attribution: `controlplane/audit.py::ControlPlaneActionRow` + deterministic `audit_dispatch_id`; "Identity is never self-declared. A caller is its run. Tokens are minted by TM at spawn"; durable `sessions.json` launch facts; `RUN-IDENTITY.md` id lifetimes; `IndexEntry.mutated_manually`.
- Absent: per-turn latency/TTFT telemetry (grep-verified).

### B10. Product-intent statements (top-level docs)

- README.md: "a context control plane for coding agents. It proxies live agent traffic, captures turn artifacts, shows the exchange in a web UI, and can pause the next outbound request." No aggregated multi-run view exists yet.
- NORTHSTAR.md: "wire-level capture of every agent, controlled agent homes, scoped context delivery, and evals grounded in evidence rather than vibes"; pricing thesis $199 / $19.99-month against $400-1000/month agent spend.
- CONTROLPLANE.md five principles (identity never self-declared; push carries references, pull carries content; every action attributed and persisted).
- HARNESS-COMPATIBILITY.md: certification "advisory until enforcement ships."
- docs/ARCHITECTURE.md: Python = capture plane (maintained, not extended), TypeScript = product plane.
- NOW.md (verified at `a252df24`): current focus is the first-run credential-onboarding screen, then launch truthfulness, then the `launch_batch` verb, then fleet close; nothing on the roadmap is capture/diff/export; the "no new UI until the control-plane UI redesign" gate stands (first run is its sole exception).

### B11. Later-only evidence (present at `ed09933`, absent from pinned `a252df24`)

None load-bearing for any finding above. The complete `a252df24..ed09933` delta (3 commits):
- First-run harness evidence cards (slice 1a): `www/packages/canvas/src/firstrun/` (`FirstRunScreen.tsx`, `harnessCards.ts`, `useHarnessInventory.ts`), `www/packages/core/src/types/harnessInventory.ts`, `shared/harness_inventory_vocabulary_v1.json`, launcher/route wiring.
- Credential dispatch-by-source: 14 lines added to `www/packages/core/src/transport.ts` (shifts the `"capture-lost"` union member from L404 to L418; the member itself exists at both commits).
- `NOW.md` wording update marking slice 1a shipped; roadmap substance unchanged from the baseline text cited in B10.
