# Scout S2f: resolver, launch gating, setup actions (ADVISORY)

Baseline main @ 10e922fb (S2e merged). Tree pristine, report only.
Contract sources: RUNTIME-SURFACING-S2-PLAN.md (S2f section, shared decisions,
Data placement), HARNESS-COMPATIBILITY.md (Version enforcement, Outcome codes),
LAUNCH-CONTRACT.md (Resolution, selection order).

## Reuse Map

Every S2f capability with its existing owner. "None found" entries list the
searches that proved absence.

### Pure range + block matcher: EXISTS, reuse unchanged

- `harnesses/compatibility.py` `match_release` + `CompatibilityMatch` +
  `CompatibilityOutcome`. Pure over explicit snapshots (channel state, release,
  observed version, optional route/model, injected `now`). Fails closed on
  missing/paused/mismatched channel state and unprovable expiry. Zero production
  callers today (grep `match_release` outside harnesses: only docstring
  references in `blocks.py` and `probes/targets.py` saying "uncalled until S2f").
  Do not fork; the resolver composes it.

### Release + channel state snapshots: EXISTS

- `harnesses/compatibility_store.py` `embedded_channel_state(channel, harness_id)`
  and `embedded_release_entry(release_id)` over the lru-cached
  `embedded_compatibility_manifest()`. Sync, no I/O beyond first package read.
- Channel identity: `channel.py` `resolve_channel_id(value, env)` /
  `activate_channel`; both CLI seams already call `activate_channel(channel)`.

### Executor block merge: EXISTS

- `harnesses/blocks.py` `merge_executor_blocks(channel_state, executor_blocks)`
  merges active executor-origin blocks into channel state as a matching input
  (never persisted). Executor blocks read via `harnesses/blocks_store.py`
  `ExecutorBlockStore.active_blocks` (async, pool).

### Installation/version observation: EXISTS

- `capabilities.py` `detect_harness_descriptor` (which-walk + `--version` probe,
  2s timeout) → `harnesses/probes/observation.py` `build_harness_observation`
  → `LocalHarnessObservation`. Version extraction owner:
  `extract_normalized_version`. Executor identity: `harnesses/executor_identity.py`
  `local_executor_id()` (sync).

### Connection resolution: EXISTS

- `harnesses/connections.py` `resolve_connection(connections)` — pure
  sole/default/`connection_ambiguous`/`connection_missing`.
  Records via `harnesses/connections_store.py` `ExecutorEvidenceStore`
  (sync psycopg writes, async pool reads: `list_connections`,
  `latest_harness_observation`, `latest_access_observations`,
  `latest_target_observations`).

### Release attribution for observations: EXISTS, distinct from authorization

- `harnesses/probes/targets.py` `resolve_compatibility_release_id` maps channel
  → active release id for evidence attribution (minimum-version floor, open
  ceiling). Deliberately NOT an authorization gate: `match_release` authorizes,
  `resolve_compatibility_release_id` attributes. Do not conflate the two when
  wiring the gate. `build_target_observation` builds `LocalTargetObservation`
  with attribution wired.

### Auth/access probes under connection context: EXISTS

- `harnesses/probes/runner.py` `run_authentication_probe` +
  `probe_environment` (strips all harness home + credential env keys, applies
  the connection's home). Adapters: `probes/claude.py`, `probes/codex.py`
  (`codex login status`, stderr-scanned per #295), `probes/grok.py`.
  Evidence → `probes/__init__.py` `build_access_observation` →
  `LocalHarnessAccessObservation`.

### Compatibility fact artifact + audit mirror: EXISTS, uncalled

- `harnesses/compatibility_facts.py` `compatibility_fact_artifact` (requires a
  resolved release + installed ok observation), `write_compatibility_facts`
  (atomic, frozen-once, idempotent retry), `mirror_compatibility_facts`
  (async `ControlPlaneAuditSink`, idempotent dispatch id). Zero production
  callers (grep confirmed) — S2f wires them.

### The three launch preparation seams: EXIST, and they converge

- Capture RPC: `capture_rpc.py` `CaptureLeaseRegistry.prepare_capture` →
  `_prepare_with_dependencies` → `captured_run.py` `prepare_captured_run`.
- Claude CLI: `cli/start_cmd.py` `run_start` → `captured_run.py`
  `run_captured_run_on_local_tty`.
- Codex CLI: `cli/codex_cmd.py` `run_codex` → `cli/launch_runtime.py`
  `prepare_launch`.

**Convergence fact:** both claude paths flow through
`captured_run_context.py` `build_captured_run_context` →
`_prepare_launch_state` → `cli/launch_runtime.py` `prepare_launch`, the same
function `run_codex` calls directly. `prepare_launch` is the single choke
point where harness name, resolved client binary path, `run_id`, and
`resolved_storage` (the run dir) all exist. One service invocation there
covers all three seams; the "both native CLIs and capture RPC reject the same
incompatibility" proof follows from one call site plus three per-seam
acceptance tests.

### Best-effort gating precedent: EXISTS

- `drift_capture.py` `build_drift_emitter`: any construction failure logs and
  returns None, "leaving the caller's live path untouched". The advisory gate
  wants the same posture.
- Sync CLI Postgres precedent: `session_store_preflight.py` (sync psycopg
  connect) and `ExecutorEvidenceStore.persist_connection` (sync `connect()`
  writes). Async audit writer: `controlplane/audit.py` `ControlPlaneAuditWriter`
  (pool only; **no sync audit write path exists** — see Plan, decision 3).

### REST action surface pattern: EXISTS

- `api/v1/router.py` `api_router.include_router(...)`;
  `api/v1/capabilities.py` is the thin-projection precedent
  (`asyncio.to_thread(detect_harnesses)`). App state holds
  `app.state.control_plane_audit = ControlPlaneAuditWriter(session_pool)`
  (`main.py`) — the REST setup actions get audit + pool for free.

### CLI fallback pattern: EXISTS

- `cli/__init__.py` `main.add_typer(db_app, name="db")` /
  `main.add_typer(channel_app, name="channel")` — a `setup`/`harness` sub-app
  follows `cli/channel_cmd.py` / `cli/db_cmd.py` shape.

### None found (net-new S2f code)

- Pure resolver: no `harnesses/resolver.py`; grep `resolver` under
  `harnesses/` → nothing. (`api/v1/launch_resolution.py` exists but is
  worktree/runtime-template resolution — a naming hazard, not an owner.)
- `launch_options()`: no owner (grep `launch_options` → only `cli/launch_options.py`
  which is CLI flag plumbing — second naming hazard).
- Compatibility application service / gate: none.
- Setup actions (sign in, test access): none. grep `setup_action`, `test_access`,
  `setup_adapter` → only the revision field in `compatibility.py`.
  `setup_adapter_revision` exists in every embedded release; no setup adapter
  code exists.

## Quality Map

1. **`cli/codex_cmd.py` at 693 LOC** — the 700 hard limit bites before any S2f
   wiring lands there. Refactor first. (If the gate call lands inside
   `prepare_launch` only, `run_codex` may need zero edits; the setup-action CLI
   must NOT be added to this file regardless.)
2. **Known S2a leftover:** `harnesses/probes/runner.py` carries
   `TODO(S2 completion)`: `HOME_DIR_ENV_BY_HARNESS` should generalize onto
   `HarnessDescriptor`. Setup actions reuse `probe_environment`; do not copy the
   env-strip logic.
3. **Naming hazards:** `api/v1/launch_resolution.py` (worktree resolution) and
   `cli/launch_options.py` (CLI flags) both collide conceptually with S2f's
   resolver/`launch_options()`. The new module must be `harnesses/resolver.py`
   per the plan's ownership table; REST naming should avoid `launch_resolution`.
4. **`run_codex` is a parallel orchestration of the captured-run lifecycle.**
   `cli/codex_cmd.py` `_prepare_codex_launch_parts` + `_run_codex_launch` +
   `run_codex` hand-roll what `captured_run.py` `run_captured_run_on_local_tty`
   does generically (runtime home, managed session, `persist_owned_session_facts`,
   banner + retry loop, workspace manifest), while
   `captured_run_context.py` already dispatches codex (`HARNESSES[request.harness]`,
   `build_codex_captured_invocation` reusing `build_codex_invocation` +
   `resolve_codex_addons_and_ca`). The low-level builders are shared; the
   orchestration is a second, older copy. Full collapse is beyond S2f scope,
   but it is why the gate must land in `prepare_launch` (below both copies),
   not per-orchestration.
5. **codex_cmd refactor-first seam identified:** the CA trust-bundle
   resolution + cache cluster (~220 LOC: `_PathFingerprint`,
   `_CodexCACacheKey`, cache globals, `_resolve_codex_ca_certificate_or_exit`,
   `_codex_ca_cache_key`, `_path_fingerprint`, atexit cleanup, test reset)
   depends only on `cli/trust.py` + `cli/net.py` and extracts cleanly to a new
   `cli/codex_trust.py` (or folds into `cli/trust.py`). That alone clears the
   700 headroom if S2f must touch the file at all.
6. **Store-plumbing duplication (S2f must not add an 8th copy):** the read
   shape `fetch_all(pool, SQL, {executor_id, harness_id})` →
   `tuple(Model.model_validate(dict(row)))` recurs 7x across
   `connections_store` + `blocks_store`; the "upsert → rowcount → re-SELECT →
   raise on identity mismatch" write idiom recurs 3x (`persist_connection`,
   `supersede_block`, `record_drift_evidence`). If S2f adds any store surface,
   extract the shared `_fetch_models`-style helper first or reuse existing
   methods only.
7. **Launch facts are already bundled three ways** — `RunIdentitySeed`
   (`captured_run_context.py` `_run_identity_seed`), `CapturedRunContext`,
   and `capture_rpc.py` `_CaptureRunFacts`. The gate must consume
   `LaunchPreparation` (+ `RunIdentitySeed` where present), never mint a
   fourth fact bundle. `drift_emitter.py` `evidence_fields` explicitly leaves
   `release_id`/`route_id`/`model_id` absent "until S2f records it" — the
   gate's resolved context is what feeds those fields.
8. **Binary resolution is single-path (no dupe to fix):**
   `capabilities.py` `resolve_harness_binary`/`resolve_runnable_binary` is the
   one owner; `cli/launch_runtime.py` `resolve_client_binary` wraps it with
   typer UX only. The gate's observation should reuse the already-resolved
   client path from `prepare_launch` rather than a second which-walk.
9. **Probe adapters are parallel shape, not duplication** (JSON vs line-scan
   parsers, shared `unknown_evidence`/`probe_evidence_digest`); no
   consolidation needed. Setup adapters should follow the same shape and the
   closed reason vocabulary — never persist `ProbeCapture` (redaction
   boundary).
10. Minor, in-scope-adjacent: `captured_run_context.py` `_descriptor_home` is
    dead indirection over `descriptor_home`; `_build_provider_invocation`
    assembles ~25 kwargs twice with a large shared prefix;
    `capture_rpc.py` hand-rolls a camelCase serializer
    (`capture_spawn_spec_payload`) beside the repo's `model_dump(mode="json")`
    convention. None block S2f; fix opportunistically only if touched.

## Plan

### Shape

1. `harnesses/resolver.py` (new, pure, no I/O): `ResolverSnapshots` (explicit
   inputs: channel state w/ merged executor blocks, release entry, harness
   observation, connections, access observations, target observations, agent
   recommendation), `resolve_target(request, snapshots)` implementing
   LAUNCH-CONTRACT Resolution selection order (validate explicit fields
   together → agent recommendation → agent tested default → release tested
   default for native → fail on ambiguity/absence; explicit fields never fall
   back; defaults tested+active+ready only; deprecated/unverified need explicit
   selection (+opt-in); rejections carry stable outcome codes). Composes
   `match_release` and `resolve_connection` unchanged. `launch_options()` lives
   here too: pure enumeration of launchable tuples + structured exclusion
   reasons, for agent and native launches.
2. Compatibility application service (new module, e.g.
   `harnesses/compatibility_service.py`): gathers snapshots (embedded channel
   state + release, executor blocks via `ExecutorBlockStore.active_blocks` +
   `merge_executor_blocks`, fresh `LocalHarnessObservation` via
   `build_harness_observation` reusing the seam's already-resolved binary path
   from `LaunchPreparation.client_path` — no second which-walk),
   calls the resolver/`match_release`, records outcome, returns an advisory
   verdict. Build-level rollout constant in this module:
   `COMPATIBILITY_ROLLOUT: Literal["advisory", "enforcing"] = "advisory"`.
   One-way: flipping to enforcing is a code change shipped in a TM release
   (S2g). Enforcing branch implemented + tested NOW (missing/paused/revoked
   fail closed; incompatible outcomes raise the typed rejection), but dead
   under the advisory constant.
3. Wire once at `prepare_launch` (covers all three seams), acceptance-tested
   per seam: capture RPC rejects, claude CLI rejects, codex CLI rejects the
   same fixture incompatibility when the test flips rollout to enforcing;
   in advisory the same fixtures record would-be outcomes and the launch
   proceeds untouched.
4. Facts on every gated run: when release + installed observation resolve,
   `compatibility_fact_artifact` → `write_compatibility_facts(resolved_storage,
   artifact)` → `mirror_compatibility_facts`. Would-be outcomes (including
   rejections that cannot produce an artifact, e.g. release unavailable) go to
   the control plane audit as a new verb (e.g. `harness_compatibility_gate`)
   with the `CompatibilityMatch` outcome + advisory/enforcing marker in details,
   idempotent dispatch id keyed on run_id + outcome digest (the
   `compatibility_facts_dispatch_id` shape).
5. Setup actions: per-harness setup adapters beside the probes (owned by
   `setup_adapter_revision`), REST action routes (POST, explicit confirmation
   in body) on the api_router + a thin typer sub-app fallback. Sign-in runs the
   harness's interactive login under `probe_environment`; test access performs
   exactly one bounded minimal request per confirmation (hard timeout, no
   retry, cancellation before send), records sanitized evidence digest +
   adapter revision, upserts `LocalHarnessAccessObservation` via
   `ExecutorEvidenceStore`. Outcomes: confirmed/cancelled/unavailable/failed
   (plan's verification list). Observations built through the existing
   `probes/__init__.py` `build_access_observation` with release attribution
   from `probes/targets.py` `resolve_compatibility_release_id`; setup adapters
   follow the probe-adapter shape and closed reason vocabulary, and raw
   capture never persists.
6. Thread the gate's resolved context (release_id, route_id, model_id,
   normalized_version) toward drift evidence: `drift_emitter.py`
   `evidence_fields` leaves these absent "until S2f records it", and S2d item 4
   gates automatic block creation on S2f-recorded context. Minimum S2f
   delivery: the compatibility fact artifact + gate audit record carry the
   resolved context; wiring it into live `DriftEmitter` fields can ride the
   same seam or be an explicit planner-scoped follow-up.

### Live-launch safety (advisory must never break a launch)

- The entire gate call at `prepare_launch` is wrapped best-effort in advisory
  mode (the `build_drift_emitter` posture): embedded manifest error, DB
  unreachable, probe timeout, artifact write failure → log + skip recording,
  launch proceeds. The ONLY behavior advisory adds to the live path is bounded
  latency: one `--version` subprocess (2s cap). Auth/access probes are NOT run
  at the gate in S2f (they are setup-action + S2g refresh territory); the gate
  consumes stored observations only, so no 5s probe rides launch prep.
- `write_compatibility_facts` frozen-artifact rejection cannot fire on a fresh
  run dir (run_id is new per launch); retry idempotence already handled.
- `preflight_session_store_or_exit` already hard-blocks launches on a dead
  store before the gate runs, so "DB down" is not a new advisory failure mode
  on CLI paths; capture RPC has `check_session_store` likewise.

### Open decisions for the planner

1. Audit mirror transport at sync CLI seams: `ControlPlaneAuditWriter` is
   async-pool only. Options: (a) short-lived `asyncio.run` + pool at the seam,
   (b) a sync psycopg audit write path (precedent: `ExecutorEvidenceStore`
   sync writes), (c) record run-dir artifact synchronously and mirror from the
   API/addon process later. Recommend (b): smallest, matches the store split
   pattern already in the area.
2. Whether the gate consumes stored access observations in S2f advisory
   verdicts or records version/block matching only. The artifact needs only
   release + installation observation; recommend version+block gate in S2f,
   route/target once inventory (S2g) provides fresh evidence surfaces.
3. Sign-in over REST for interactive OAuth flows: REST can start
   `codex login`-style device flows but cannot own a TTY; recommend REST
   returns the provider URL/instructions where the harness supports headless
   login, CLI fallback owns the interactive path.

### S2f/S2g boundary (explicitly out)

No `harnesses/inventory.py`, no `/v1/harnesses` inventory join, no first-run
screen, no nonblocking startup refresh, no enforcing flip, no package-embedded
active pointer changes. Advisory is a build property; channel state stays as
embedded data says.
