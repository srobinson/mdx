# Spec S2: the two-gate launch model — enablement (hard) beside compatibility (advisory)

Status: build brief. Scouted against `main` @ `506e0409`. Citations are
file + symbol, never line numbers. Companion slice: S1 rejection signal
(`transport-matters-spec-s1-rejection-signal.md`), independent — do not couple.

## Goal

There are TWO launch gates, and this slice builds the first (Stuart-approved
model ruling):

- **ENABLEMENT (hard)**: installed + user toggle, default ON. Version
  compatibility is NOT an enablement input.
- **COMPATIBILITY (separate, existing)**: version, advisory today (records
  would-be outcomes, does not block) → enforcing at S2g. An
  incompatible-but-enabled harness LAUNCHES today under advisory; this slice
  changes nothing about that posture.
- **AUTH**: neither gate — surfaced live (S1).

codex, claude, and grok are all surfaced; a harness that is present is
enabled by default; the user can toggle it off. This slice also retires the
resolver's shipped auth-gating rejection codes so "enablement gates, auth
surfaces" is true in code with no dead-code window.

## Inputs

- Scout report: `~/.mdx/projects/transport-matters-scout-harness-auth.md`
  (Reuse Map item 6, Quality Map items 1 and 2).
- Fixed product decisions: auth never gates launch; enablement and auth are
  separate bounded contexts; launch eligibility is computed backend-side.

## Decisions already made — do not redesign

1. **Store is a new Postgres table + migration**, not `settings.toml`:
   mutable user state, queried by launch eligibility, survives restart.
   (`config.py :: TomlSettings` stays `[database]`-only.)
2. **The user-toggle fact threads into `harnesses/resolver.py` and
   `launch_options()`**: a disabled harness is visible but not launchable.
3. **The resolver auth-gating codes are RETIRED IN THIS SLICE**:
   `resolver.py :: _access_evidence` and the `authentication_required`,
   `authentication_expired`, `authentication_probe_failed`,
   `access_unavailable`, `access_probe_failed` members of
   `ResolutionRejectionCode`, plus the `authentication_required`
   no-ready-connection rejection in `_select_connection`. Connection
   structure rejections (`connection_missing`, `connection_ambiguous`,
   `connection_unavailable`) stay — they are topology, not auth.
4. **REST surface for the toggle: write AND read** — server-side is forced
   because CLI/MCP launch eligibility is backend-computed; localStorage
   cannot reach it. A persisted enablement READ endpoint is required (reload
   and S3 need it; a write-only route plus installed-only capabilities leaves
   no way to render current state). Settings UI rendering is S3.
5. **Fail closed on store failure**: a toggle-store read failure at launch
   time treats the harness as not launchable, surfaced through a defined
   domain error — never fail-open, never a raw 500.
6. **Executor scope in the natural key**: the toggle row is keyed
   `(executor_id, harness_id)` so one install sharing a database cannot
   disable another.

## Semantics (per the two-gate ruling)

- Default: present ⇒ enabled; no row means enabled. The table stores explicit
  user intent (disable, or re-enable), not derived state. Version plays NO
  part: enabling/disabling is valid regardless of compatibility outcome, and
  an incompatible-but-enabled harness launches today under advisory.
- Enablement eligibility = installed AND not user-disabled. Nothing else.
- Toggle-off blocks launch hard at the launch choke point — this is the
  user's own choice, not a compatibility judgment. The advisory version
  posture is UNCHANGED: `compatibility_service.py :: COMPATIBILITY_ROLLOUT`
  stays `"advisory"`; do not flip it or touch the four connection bounds.
- **Posture parity across surfaces (completes the two-gate fix)**: the
  resolver currently returns compatibility outcomes as HARD rejections and
  `launch_options` exclusions, while `prepare_launch` treats them as
  advisory — so an incompatible-but-enabled harness would launch via
  `prepare_launch` yet appear unlaunchable on the resolver surface. The
  resolver's compatibility handling must respect the SAME
  `compatibility_service.py :: COMPATIBILITY_ROLLOUT` posture as
  `prepare_launch`: under advisory, compatibility outcomes do NOT
  hard-reject or exclude (they remain visible as advisory detail); under
  enforcing (S2g), they exclude. One posture, both surfaces
  (`resolver.py :: resolve_target` / `launch_options`).
- **Toggle-time identity**: the write surface performs NO fresh binary
  probing or PATH re-observation — validating against a fresh `which` walk
  would judge a different executable than launch uses when `bin_override` is
  in play. Enablement is pure user intent; installed-ness is evaluated at
  launch/read time through the same resolved executor identity the launch
  path uses (`capabilities.py :: observe_resolved_binary` at
  `prepare_launch`; identity is the observed `--version` per S2f part 1,
  never a byte hash).
- Disabling never deletes evidence (observations, facts, audit rows stay).
- A disabled harness remains discoverable: capabilities and `launch_options`
  still list it, marked not launchable with a new exclusion reason (e.g.
  `harness_disabled`).
- Store-read failure at launch: fail CLOSED (blocked) with a typed domain
  error (`exceptions.py`, chained per `api/CLAUDE.md`). Boundary placement:
  the FastAPI outcome mapping belongs with the route layer
  (`api/v1/capture_rpc_routes.py`), NOT inside `capture_rpc.py` — domain
  raises, the boundary translates. The MCP launch path currently drops the
  upstream error code in `api/v1/run_proxy.py` before the generic
  `controlplane/action_policy.py` mapping; the specific enablement code must
  be preserved through that path, not flattened to a generic failure.
- **Full boundary matrix**: both codes ({`harness_disabled`,
  store-failure}) must render a structured, non-500 outcome at ALL FOUR
  boundaries — capture RPC (`api/v1/capture_rpc_routes.py`), Claude CLI
  (`cli/start_cmd.py`), Codex CLI (`cli/codex_cmd.py`), and MCP
  (`api/v1/controlplane_mcp.py :: launch` via `run_proxy.py`). The test list
  requires the full 2×4 matrix, not one generic CLI case.

## Reuse map

Gate facts (exist already — bind, do not rebuild):

- ENABLEMENT input "installed": `capabilities.py :: detect_harnesses` /
  `observe_resolved_binary` over the registry `harnesses/__init__.py ::
  list_harness_descriptors` / `HarnessId` / `launch_eligible_harness_ids`
  (grok has `launch=None` — a registry fact, distinct from the user toggle).
  REST read: `api/v1/capabilities.py :: get_capabilities`.
- The SEPARATE compatibility gate (context only, untouched here):
  `harnesses/compatibility.py :: match_release`, consumed by
  `harnesses/resolver.py :: resolve_target` / `launch_options` and by the
  advisory gate `harnesses/compatibility_service.py ::
  gate_launch_preparation` at the single `cli/launch_runtime.py ::
  prepare_launch` choke point (covers capture RPC, claude CLI, codex CLI).
  The toggle check lands beside it at the same choke point but is its own
  gate with its own posture (hard vs advisory).
- Blast radius note: `resolver.py` has NO production caller yet (its
  docstring assigns `ResolverSnapshots` gathering to the S2g inventory
  surfaces), so the retirement in decision 3 lands in the resolver, its
  colocated tests, and contract vocabulary only. The launch-blocking check
  for the toggle therefore belongs at `prepare_launch` (where the advisory
  gate already runs), with the same fact threaded into `ResolverSnapshots`
  for the S2g surfaces.

Store + migration (mirror, do not invent):

- Table/store pattern: `harnesses/connections_store.py` (column tuple +
  upsert SQL constants) or `harnesses/blocks_store.py :: ExecutorBlockStore`
  — pick the closer fit; one owner module beside them (e.g.
  `harnesses/enablement_store.py`) plus pure vocabulary beside the models it
  serves.
- Migration: **this slice owns revision `0026_harness_enablement`** (23
  chars, within Alembic's `version_num String(32)` limit). `down_revision`
  is whatever main's migration head is AT MERGE TIME — do NOT hardcode S1's
  revision; the slices are independent, and whichever merges second rebases
  its `down_revision` onto the other's head and re-verifies
  `session/testing.py :: EXPECTED_MIGRATION_HEAD_REVISION` plus the stepwise
  walk in `session/test_migration_roundtrip.py` (which gains a step or fails
  by design).
- Table DDL constraints, defined: primary key over
  `(executor_id, harness_id)`; CHECK constraints are **nonempty-only**
  (matching the actual `0022_harness_executor_tables.py` precedent, which
  checks nonempty `harness_id`, not a closed vocabulary). The harness
  vocabulary is enforced at the model/store layer (`harnesses/__init__.py ::
  HarnessId` Literal + frozen pydantic), so registering a future harness
  needs no migration; a closed-vocabulary DB CHECK would force one per
  addition for no integrity gain.
- Connection bounds: any launch-path read of the toggle uses the bounded
  `session/pool.py :: connect` parameters exactly as
  `compatibility_service.py :: _open_gate_connection` does — the launch path
  must never gain an unbounded DB wait.

REST surface (write + read):

- Follow the `api/v1/` route-module pattern (`capabilities.py` is the sibling
  precedent; register in `api/v1/router.py`). Typed request/response models,
  domain error translated at the FastAPI layer per `api/CLAUDE.md`.
- Write: set enabled/disabled per `(executor, harness)`.
- Read: the persisted enablement state (all harnesses for the executor, with
  effective eligibility), so a reload and the S3 settings UI have a source of
  truth beyond installed-only capabilities.
- **Read identity semantics, defined**: effective eligibility on the read is
  evaluated against the DEFAULT resolution — the same
  `capabilities.py :: observe_resolved_binary` walk launch uses absent
  `bin_override` — and the response carries the evaluated identity (resolved
  executable path + observed version) alongside the verdict, so a consumer
  can see exactly what was judged. A launch using `bin_override` may resolve
  a different executable; the read does not model overrides (they are
  launch-call-scoped), and saying so explicitly in the response contract is
  the fix.

Retirement sweep (decision 3) — no orphans:

- `resolver.py :: _access_evidence` and its callers; the five auth codes in
  `ResolutionRejectionCode`; access-evidence fields of `ResolverSnapshots`
  that exist solely for gating (`LocalHarnessAccessObservation` snapshots
  stay persistable — the probes and S3 read them; only the resolver's gating
  consumption retires).
- **`ResolvedTarget.access_observation_revision` loses its sole producer**
  (`_access_evidence` supplies it from `access.probe_revision`): remove the
  field and every reader, or the retirement ships a required field nothing
  can populate.
- **Contract docs are part of the sweep**: `LAUNCH-CONTRACT.md` and
  `HARNESS-COMPATIBILITY.md` still carry auth-authority launch semantics
  (access evidence authorizing launch). Update them to the two-gate posture
  in context, alongside the `RUNTIME-SURFACING-S2-PLAN.md` item-4 and
  probe-contract-rule retirement below. `.archive/` untouched.
- **Grep-zero, correctly scoped**: `authentication_probe_failed` is BOTH a
  retired `ResolutionRejectionCode` member AND the retained
  `ProbeFailureReason` literal (`harnesses/probes/__init__.py ::
  REASON_PROBE_FAILED`) — a repository-wide grep-zero is wrong. The residue
  check is: zero occurrences as a rejection/vocabulary member in the resolver
  path and contract docs; the probe vocabulary and access-observation models
  keep their literals. Trace the full radius: colocated resolver tests,
  `harnesses/compatibility_test_support.py` builders, and any contract
  vocabulary listing the retired codes.
- Terminology precision: `connection_missing` is a
  `ConnectionResolutionOutcome` (`harnesses/connections.py ::
  ConnectionResolution`), not a `ResolutionRejectionCode` member — the
  retained topology handling is the resolver's mapping of connection
  resolution outcomes (`connection_ambiguous`, `connection_unavailable`
  codes), which stays untouched.

## Deliverables

1. Migration `0026_harness_enablement` + store module for per-executor,
   per-harness user enablement.
2. Toggle read wired into `prepare_launch` (hard block with a typed domain
   error when disabled OR when the store read fails — fail closed) and into
   `ResolverSnapshots` / `launch_options` (visible, `launchable=False`,
   exclusion `harness_disabled`), with the error translated at all four
   boundaries per the matrix, and resolver compatibility posture parity per
   the semantics section.
3. REST write + read surface per the reuse map (no binary probing at write
   time).
4. Auth-gating retirement per decision 3, including
   `ResolvedTarget.access_observation_revision` removal and the
   LAUNCH-CONTRACT / HARNESS-COMPATIBILITY auth-authority doc sweep.
5. Plan-text retirement (this slice owns it): `RUNTIME-SURFACING-S2-PLAN.md`
   S2f item 4 ("sign in, test access" setup actions — never built) and the S2
   probe-contract rule "access remains `unknown` and cannot authorize
   launch", both rewritten to the reshaped posture (enablement gates, auth
   surfaces in-stream). `.archive/` snapshots untouched.

## Out of scope

Settings/frontend UI (S3), opportunistic probe wiring (S3), the S1 rejection
signal, any drift or compatibility-gate posture change, grok wire substrate.

## Tests (required)

- Enablement gates launch: toggle off ⇒ `prepare_launch` blocks with the
  typed error; toggle back on ⇒ launch proceeds.
- A disabled harness is not launchable but still discoverable
  (`launch_options` lists it with `harness_disabled`; capabilities still
  reports it installed).
- Two-gate independence: an incompatible-but-enabled harness still launches
  (advisory posture unchanged); enabling/disabling works regardless of
  compatibility outcome.
- Posture parity: under advisory, `resolve_target` / `launch_options` do not
  hard-reject or exclude on compatibility outcomes (the incompatible-enabled
  harness is launchable on BOTH surfaces); the enforcing branch excludes.
- Default-enabled: no row ⇒ eligible when installed.
- Full boundary matrix (2×4): BOTH the `harness_disabled` code AND the
  store-failure code render the structured domain outcome at capture RPC,
  Claude CLI, Codex CLI, and MCP (specific code preserved through
  `run_proxy.py`, not flattened) — never fail-open, never a raw 500.
- Executor scope: two executors sharing a database hold independent toggles;
  disabling under executor A leaves executor B launchable.
- Read endpoint returns persisted state + effective eligibility.
- The retired auth codes are gone from the resolver path and contract docs
  (scoped residue check per the retirement sweep — probe vocabulary literals
  retained); `ResolvedTarget` has no orphaned access field.
- Migration roundtrip walk passes with the new head; migration-smoke green.

## Completion line

Done when: a user can disable codex/claude/grok over REST and that harness
immediately stops launching (CLI, capture RPC, MCP) while remaining visible
with a `harness_disabled` exclusion; the read endpoint reports persisted
state; a store outage blocks launch with the structured outcome at every
boundary; an incompatible-but-enabled harness still launches under advisory;
no auth-derived rejection code remains in the resolver path or contract docs;
plan text reflects the two-gate posture; all gates pass.

## Verification gate

`just check` + `just test-affected` + `(cd api && just migration-smoke)`
(content-judged, not exit-code-through-a-pipe). Full `just test` before merge
via the standing pre-merge gate.
