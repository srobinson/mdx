---
title: Baseline Staleness as a First-Class Signal — Scout Reuse Map
type: research
tags: [transport-matters, baselines, harness-version, startup-refresh, staleness, boundary]
summary: The startup refresh already holds the freshly observed installed version; the baseline side hides its captured-at version behind a 56 MB revalidating read. The seam belongs in a new post-refresh startup task that reads enriched current pointers, and surfaces on the harness inventory, not the launch view.
status: active
source: scout
confidence: high
repo: /Users/alphab/Dev/LLM/DEV/helioy/transport-matters
commit: 10db3ca7
created: 2026-08-22
updated: 2026-08-22
---

## Executive Summary

Everything needed to compute "baselines stale: cells captured at X, installed Y" already
exists and is already in memory at the right moment. `_refresh_harness` in
`harnesses/state_refresh.py` holds the freshly observed installed version as
`observation.normalized_version` and already runs the exact staleness predicate one layer
down, in `_refresh_target_snapshot`, to decide whether to re-enumerate models. The baseline
side carries the captured-at version on `BaselineCell.harness_version`.

Three findings change the shape of the design.

1. **The brief's premise is understated and one part of it is inverted.** Three harnesses
   hold baselines, not one. Two are stale (claude, codex) and one is current (grok). For
   codex the *stored observation agrees with the baselines* and only the installed binary
   has moved, so a check that compares the store against the baselines reports codex as
   healthy and is wrong. The comparison must use the installed version observed in this
   pass, never the stored row.
2. **The cheap read is missing exactly one field.** The `current/` pointer is 4,263 bytes
   across all 16 cells and reads in 1.1 ms, but `_CurrentBundlePointer` does not carry
   `harness_version`. Getting the version today costs 56 MB and 2.63 s of full Pydantic
   revalidation. That is the whole design problem.
3. **`range_position == "above_ceiling"` looks like the answer and is not.** All three
   harnesses are `above_ceiling` right now, including grok, whose baselines are current. It
   carries zero discriminating information about baseline staleness. Proof in
   [Existing comparison](#3-does-a-staleness-comparison-already-exist).

The recommendation is a new post-refresh startup task modelled on the existing
`run_startup_verification` precedent, reading enriched pointers, surfacing on
`HarnessInventoryItem`. Detail in [Decision](#decision).

## Measured Ground Truth

Measured on this machine at `10db3ca7`, read-only. Installed versions via
`capabilities.detect_harnesses` + `probes.observation.extract_normalized_version`; stored
rows via `ExecutorEvidenceStore.latest_harness_observation`; captured-at via
`BaselineCell.harness_version` on each current bundle.

| harness | cells | baselines captured at | store observed | installed now | baselines stale | `range_position` |
| --- | --- | --- | --- | --- | --- | --- |
| claude | 10 | 2.1.238 | 2.1.237 | 2.1.239 | **yes** | `above_ceiling` |
| codex | 4 | 0.148.0 | 0.148.0 | 0.149.0 | **yes** | `above_ceiling` |
| grok | 2 | 1.0.5 | 1.0.5 | 1.0.5 | no | `above_ceiling` |

Store rows last written `2026-08-20T20:05Z`, two days stale, because the backend has not
started since the claude upgrade. That lag is not a bug: `run_startup_refresh` fires once
per backend start by design. It is the reason the stored row cannot be the "current" side
of the comparison.

The codex row is the instructive one. Store and baselines agree at `0.148.0`, so a
store-vs-baselines check reports codex healthy while its binary sits at `0.149.0` and every
one of its four cells is stale. **A store-vs-baselines comparison silently under-reports by
exactly the interval since the last backend start.**

Store cost, measured:

| read | files | bytes | wall |
| --- | --- | --- | --- |
| all 16 `current/` pointers, `json.load` only | 16 | 4,263 | 0.0011 s |
| all 16 current bundles via `read_current_baselines` | 16 (+16 pointers) | 56,230,184 | 2.63 s |

A 13,000x byte difference and ~2,400x wall difference for one string field.

## Reuse Map

### 1. Where the installed harness version is observed and stored

**Trace.** `main.py::_start_session_store` binds
`services.harness_refresh = partial(refresh_harness_state, ExecutorEvidenceStore(database_url, session_pool))`.
The lifespan creates `asyncio.create_task(run_startup_refresh(refresh), name="harness-state-refresh")`.
`run_startup_refresh` is a bare try/except that logs and swallows.
`refresh_harness_state` resolves `local_executor_id()` and `resolve_channel_id(None, env)`,
calls `detect_harnesses` off the loop, then loops `registered_harness_ids()` calling
`_refresh_harness` with per-harness exception isolation.

**Inside `_refresh_harness`,** in order:

| step | symbol | reads | writes |
| --- | --- | --- | --- |
| embedded release | `compatibility_store.embedded_channel_state`, `embedded_release_entry` | packaged JSON | — |
| build observation | `probes.observation.build_harness_observation` | `HarnessCapability` | — |
| persist observation | `EvidenceWriter.upsert_harness_observation` | — | `harness_observation` |
| **early return** | guard below | — | — |
| connections | `native_connections.reconcile_native_connection` | — | `harness_connection` |
| combined probe (grok) | `probes.runner.run_combined_refresh_probe` | binary | `harness_authentication_observation`, targets |
| enumeration (claude, codex) | `_refresh_target_snapshot` | binary | `harness_target_observation`, `harness_target_snapshot` |
| auth probe | `_refresh_connection_authentication` | binary | `harness_authentication_observation` |

**The early return** sits immediately after the `upsert_harness_observation` await:

```
if (entry is None
    or not observation.installed
    or observation.normalized_version is None
    or observation.executable_path is None):
    return
```

The root `CLAUDE.md` claims `entry is None` for grok "until S2h". **That note is stale.**
All three harnesses now resolve an active embedded release: `claude-2.1.211-r2`,
`codex-0.144.4-r2`, `grok-1.0.4-r2`. No harness takes the `entry is None` branch on this
machine.

**Installed version symbol:** `probes.observation.build_harness_observation` produces
`LocalHarnessObservation.normalized_version`, extracted by
`probes.observation.extract_normalized_version` and validated by
`compatibility.normalize_version`. This is the one owner of `--version` interpretation.

**Recorded/observed version symbol:**
`connections_store.ExecutorEvidenceStore.latest_harness_observation` returns
`LocalHarnessObservation`; the read is projected to the API by
`inventory._installation_info` into `HarnessInstallationInfo.normalized_version`.
Per-model recorded versions come from
`ExecutorEvidenceStore.latest_target_observations` →
`LocalTargetObservation.harness_version` → `inventory._target_info` →
`TargetObservationInfo.harness_version`.

**Key reuse fact:** `observation.normalized_version` is live in `_refresh_harness`'s local
scope at the moment the pass runs, already normalized, already validated. Nothing needs to
re-probe or re-read to obtain the installed side.

### 2. Where the captured-at version is readable

**Field:** `baseline_evidence.BaselineCell.harness_version: str | None`, reached as
`bundle.cell.harness_version`.

**Provenance:** written by `baseline_capture` from
`compatibility_facts.read_compatibility_facts(turn.storage_dir).observed_version`, per
probe, then folded into the cell as `harness_version=next(iter(versions))`.
`BaselineBundle.validate_probe_contract` enforces that all three probes agree with the
cell, so the cell version is authoritative for the whole bundle.

**Readers:** `baseline_store.read_current_baseline` (one cell) and
`read_current_baselines` (all cells for a harness/provider). Both go through
`_read_current_pointer`, which validates `_CurrentBundlePointer` and then calls
`read_baseline_bundle`.

**What a stale check must load, and its cost.** `read_baseline_bundle` does not do a cheap
parse. It performs the schema-version equality gate, then
`BaselineBundle.model_validate(payload)`, which runs `validate_probe_contract`:
base64-decodes three raw request bodies, re-mints the request schema via
`mint_request_schema`, recomputes `build_content_observations`, recomputes the static
fingerprint via `canonical_digest`, and verifies every transcript's SHA-256 against its
embedded bytes in `TranscriptEvidence.validate_bytes`. Measured across all three harnesses:

```
claude/anthropic: cells=10 versions=['2.1.238'] load=2.20s
codex/codex:      cells=4  versions=['0.148.0'] load=0.22s
grok/grok:        cells=2  versions=['1.0.5']   load=0.21s
```

**No DB round trip.** The baseline store is pure filesystem under
`storage_roots.default_storage_root() / "baselines"`. Zero provider turns, zero Postgres.

**The cheap read that almost works.** `_CurrentBundlePointer` carries
`artifact_schema_version`, `bundle_id`, `path`, `accepted_by`, `accepted_at`. It does
**not** carry `harness_version`. Reading only pointers costs 4,263 bytes and 1.1 ms. One
field stands between a 1 ms check and a 2.6 s one.

### 3. Does a staleness comparison already exist?

**Version-vs-version staleness against stored evidence: yes, and it is the right shape.**
`state_refresh._refresh_target_snapshot` already runs it:

```
cached = await evidence.latest_target_observations(...)
if cached and all(
    observation.harness_version == harness_version
    and observation.observation_revision == adapter.probe_revision
    and observation.completeness == "complete"
    and observation.status == "ok"
    for observation in cached
):
    return
```

Equality of a stored artifact's `harness_version` against the freshly observed installed
version, gating an expensive refresh. A baseline staleness check is the same predicate
against a different stored artifact, in the same function, at the same moment. **Reusable
as a pattern, not as code** — the loop body reads a Postgres row type, not a bundle.

**Baseline-vs-installed comparison: none found.** Searches run:
`grep -rn "stale\|Stale\|STALE"` across the package (hits are TTL evidence staleness,
lock staleness, desktop runtime staleness, test names — none baseline related);
`grep -rn "compare_versions"` (7 hits, all inside `compatibility.py` range checks plus
`compatibility_store._require_transport_matters_version`); `grep -rn "range_position"`;
`grep -rln "harness_version"` (24 files, no baseline/installed join);
`grep -rn "baseline_store\|read_current_baseline"` (importers listed in §5).

**The near-miss that must be rejected: `range_position`.**
`compatibility.range_position` returns `below_minimum | below_ceiling | at_ceiling |
above_ceiling`, and the `CompatibilityMatch` docstring says an above-ceiling version "is
due for wire schema comparison". That reads like the signal. It is not. Measured:

| harness | installed | blessed ceiling | `range_position` | baselines stale |
| --- | --- | --- | --- | --- |
| claude | 2.1.239 | 2.1.211 | `above_ceiling` | yes |
| codex | 0.149.0 | 0.144.4 | `above_ceiling` | yes |
| grok | 1.0.5 | 1.0.4 | `above_ceiling` | **no** |

All three are `above_ceiling`; grok's baselines are current. `range_position` answers
"installed is newer than the release we certified", which stays true until a new release is
embedded. Baseline staleness answers "installed differs from what these cells were captured
at". Different questions, and today the first has no discriminating power. **Wrong-shaped;
reuse `compare_versions`/`normalize_version` as primitives, not `range_position` as the
verdict.**

**Also wrong-shaped: the drift emitter.** `harnesses/drift_emitter.py::DriftEmitter` is the
shared best-effort evidence path, but its vocabulary in `harnesses/blocks.py` is
`DriftKind = wire_contract_drift | transcript_contract_drift | session_contract_drift |
launch_contract_drift`, with `DriftAttributionAction = create_block | pause_release`.
Emitting baseline staleness here attributes a block or release pause to a harness that has
violated no contract. Staleness is an evidence-coverage gap, not drift.

### 4. Where the signal would surface

| readout | symbol | fits? | why |
| --- | --- | --- | --- |
| `GET /v1/harnesses` | `api/v1/harnesses.py::get_harnesses` → `harnesses.inventory.harness_inventory` | **yes** | Already the per-harness evidence join. `HarnessInventoryItem` already carries `installation`, `compatibility`, `target_observations` — each a stored-evidence sub-record with its own model. A `baselines` sub-record is the same shape. |
| MCP `harnesses` tool | `api/v1/controlplane_mcp.py::harnesses` → `harness_launch_view.project_harnesses_view` | **yes, via `view="full"`** | Serves the same inventory object; `view="full"` returns it unprojected. Free once inventory carries it. |
| launch view | `api/v1/harness_launch_view.py::project_harness_launch_view` | **no** | Its models are `extra="forbid"` and deliberately minimal: `LaunchModelDeviation` documents itself as "Only launch facts that differ from the ordinary selectable case", and `project_harnesses_view` is documented "without consulting another data source". Staleness is not a launch fact — every stale cell still launches. Adding it distorts a projection whose contract is the launchable subset. |
| `cli/diagnose.py::run_doctor` | harness block at the `detect_harnesses()` loop | **yes, as a second line** | Already prints one line per harness from live detection (`_ok(name, capability.version)`). It has `_warn`, and precedent for advisory lines. It reads the filesystem freely and does not import inventory, so it can call the baseline reader directly. Cheapest real surface. |
| `cli/runs_health.py` | `fetch_runs`, `orphan_candidates` | **no** | Scoped to run lifecycle over the gateway HTTP contract (`runId`, `state`, `createdAt`). Harness evidence would be a foreign concern. |
| `run_startup_refresh` log | `state_refresh.run_startup_refresh` | **non-answer** | Confirmed: it is a bare `try/except: logger.exception`. Nothing reads it. `access_verification.run_startup_verification` has the identical problem — it computes `HarnessAccessVerification` outcomes and only `logger.info`s them. |

**Surfacing conclusion:** the inventory is the contract-correct home and reaches both the
canvas and the MCP tool for free; `doctor` is the cheap operator-facing second surface. The
launch view must be left alone.

### 5. Boundary check

The documented DAG in `api/CLAUDE.md` is
`ir → adapters → rules → pipeline → storage → breakpoint → server`.

**Import edges, extracted by AST at `10db3ca7`:**

```
baseline_store        -> atomic_io, baseline_evidence, request_schema
baseline_evidence     -> adapters, canonicalization, request_extras,
                         request_inventory, request_schema, session.wire_normalization
harnesses/state_refresh -> capabilities, channel, harnesses, harnesses.compatibility_store,
                         harnesses.connections, harnesses.executor_identity,
                         harnesses.native_connections, harnesses.probes{,.claude,.codex,
                         .grok,.observation,.runner,.targets}
```

**No cycle.** `baseline_store` does not import `harnesses`, so
`state_refresh → baseline_store` would not form one. **But it is still the wrong edge**, on
measured weight:

```
state_refresh alone:                23 transport_matters modules, 0.136 s
adding baseline_store:             +68 modules,                  +0.233 s
  of which session/*:               17 modules
  plus adapters.anthropic, codex.adapter, grok.adapter, request_inventory
```

The startup refresh path today touches only harness observation modules. Importing
`baseline_store` would quadruple its dependency surface and drag in the entire `session`
package and every provider adapter — to read one string. `api/CLAUDE.md` explicitly warns
`storage` must never import `session`; `state_refresh` is not `storage/`, so this is not a
literal violation, but it is the same direction the rule exists to prevent.

**Verdict: the startup refresh path can legally reach the baseline store, and should not.**
The seam belongs beside `state_refresh`, not inside it: a separate module that consumes
what the refresh produced rather than reaching across during it.

**The precedent already exists in `main.py`.** `_start_harness_access_verification` creates
a second startup task, `run_startup_verification(refresh_task, verification)`, which awaits
the refresh task and then runs its own guarded pass with its own dependencies, gated by
`settings.startup_access_verification`. A baseline staleness observer is the same wiring,
minus the cost — `verify_provider_access` runs billed captured turns, a staleness pass runs
none.

## Quality Map

Seven findings. Ranked by value, not effort.

**Q1 — The cheap read is one field short of complete (design defect, blocking).**
`baseline_store._CurrentBundlePointer` carries `bundle_id` and `path` but not
`harness_version`, so every consumer that wants the captured-at version pays the full
56 MB revalidating read. The trap: `_CurrentBundlePointer.artifact_schema_version` is typed
`BaselineArtifactSchemaVersion`, the **same `Literal[5]`** the bundle uses, and
`read_baseline_bundle` gates on exact equality with
`raise ValueError("unsupported baseline bundle schema; regenerate the baseline")`. Bumping
to 6 invalidates all 16 stored bundles and costs 48 billed provider turns to re-harvest.
*Resolution:* add `harness_version: str | None = None`. Optional with a default keeps
existing pointers valid at version 5 under `extra="forbid"`, so **no bump and no
re-harvest**. Backfill the 16 existing pointers once from their bundles — local, 2.6 s,
zero provider turns.

**Q2 — `model_dependence_assessed` is not simply dead; it is expensive dead
(refute-with-nuance).** Confirmed write-only: declared on both
`baseline_evidence.AbaAnalysis` and `baseline_evidence.BaselineBundle` as
`Literal[False] = False`, set explicitly once in `baseline_capture`, and read by no
non-test code. The `AbaAnalysis` copy is doubly inert — `classify_aba` sets it and
`baseline_capture` never propagates it, passing its own literal instead. **But it is a
serialized field of 16 stored bundles.** Deleting it changes the bundle schema, forces the
`Literal[5]` bump, and costs 48 billed turns. *Recommendation:* delete the `AbaAnalysis`
declaration now (in-memory only, zero cost, removes the duplication), and leave the
`BaselineBundle` declaration until a schema bump is already being paid for. The brief's
"dead code" framing is right about the symbol and wrong about the cost.

**Q3 — Pointers store absolute paths (latent data-loss defect).**
`baseline_store._write_current` stores `path` as the absolute
`_bundle_path(output, bundle)` result. Verified on disk:
`"path": "/Users/alphab/.transport-matters/baselines/bundles/claude/anthropic/opus/..."`.
Relocating the home or setting `$TRANSPORT_MATTERS_HOME` orphans all 16 pointers, and
`read_baseline_bundle`'s `is_relative_to(expected_root)` guard then rejects them outright.
Storing a path relative to `output` would make the store relocatable. Independent of this
feature; worth a separate fix.

**Q4 — Root `CLAUDE.md` is stale on two counts (doc drift).** It says `_refresh_harness`
"returns early when the harness has no embedded release" as the live grok case; all three
harnesses now have active embedded releases (`grok-1.0.4-r2`), so no harness takes that
branch. `state_refresh._fallback_observation_revision`'s comment ("grok until S2h") is
stale for the same reason.

**Q5 — Two startup passes swallow their results identically (duplication).**
`state_refresh.run_startup_refresh` and `access_verification.run_startup_verification` are
the same bare guarded-task idiom, and both terminate in a logger call nothing reads.
`run_startup_verification` even computes a typed `HarnessAccessVerification` tuple and
discards it into `logger.info`. A third pass should not repeat the mistake: whatever the
staleness pass computes must land somewhere readable. Consolidating the guarded-task
wrapper is a reasonable cleanup once there are three.

**Q6 — `baseline_store` has no production caller (scope fact, not a defect).** Its only
importers are `baseline_capture`, `baseline_compare` (an `argparse` script), and
`baseline_harvest` (an `argparse` script). No route, no control plane, no launch path
touches it. This feature would be the **first** production read of the baseline store. That
raises the bar on the seam and is the main argument for keeping it out of the refresh path.

**Q7 — LOC posture is clean; no refactor gate.** `state_refresh.py` 441,
`baseline_store.py` 183, `inventory.py` 508, `connections_store.py` 534,
`harness_launch_view.py` 268. All under 700, and `_refresh_harness` is roughly 110 lines,
under the 150 function threshold.

**Grooming recommendation: refactor *during*, not first.** Nothing blocks the work. Fold Q1
(pointer field + backfill) into the feature, since it *is* the feature's cheap path. Do Q2's
`AbaAnalysis` half and Q4's doc fixes in the same branch as free cleanups. Defer Q3 and Q5
to their own changes — Q3 touches persistence and per prior experience persistence edits
carry data-loss risk disproportionate to their size, and Q5 only pays off once the third
pass exists.

## Decision

**Where the computation lives:** a new module, `harnesses/baseline_staleness.py`, exposing a
pure comparison plus a guarded startup pass, wired in `main.py` as a second task that awaits
`app.state.harness_refresh_task` — the exact shape of
`_start_harness_access_verification` / `run_startup_verification`. The pure half takes the
installed versions the refresh already observed and the captured-at versions read from
enriched pointers, and returns a per-harness verdict using `compatibility.compare_versions`
and `normalize_version` as primitives.

**Where it surfaces:** a `baselines` sub-record on `HarnessInventoryItem`, carrying
`captured_at_version`, `installed_version`, `cell_count`, and a verdict, joined in
`inventory._harness_item` beside `installation` and `target_observations`. This reaches
`GET /v1/harnesses`, the canvas, and the MCP `harnesses` tool at `view="full"` with no
further work. A second line in `cli/diagnose.py::run_doctor`'s harness loop gives the
operator the same fact without a running backend.

**Why.** Three reasons, in order of weight.

1. **Correctness.** The installed side must come from the pass's own observation, never from
   the stored row. Codex proves it: store and baselines agree at `0.148.0` while the binary
   is at `0.149.0`, so any store-vs-baselines check reports four stale cells as healthy. A
   post-refresh task sees `LocalHarnessObservation.normalized_version` as the refresh just
   wrote it, which is the freshest fact the process has.
2. **Boundary.** Putting the comparison *inside* `_refresh_harness` would add 68 modules and
   the whole `session` package to a path that currently loads 23. A sibling task keeps the
   refresh path's dependency surface exactly where it is, and confines the baseline store's
   first production read to one module.
3. **Contract fit.** `HarnessInventoryItem` is already the per-harness evidence join, and
   every existing sub-record has this shape. The launch view is the wrong home by its own
   documented contract, and its `extra="forbid"` models would have to be widened for a fact
   that changes no launch decision.

**Strongest counter-argument.** A second startup task means the signal is only as fresh as
the last backend start, so a harness upgraded mid-session shows a stale verdict until
restart — and worse, an *incorrectly current* verdict if the operator downgrades to match
the baselines. The honest alternative is to compute the comparison on demand inside
`harness_inventory`, which already runs per request and already holds the executor id and
channel. That would always be current. It costs 1.1 ms per request with enriched pointers
(acceptable) but 2.6 s without them (not), so it is only viable *after* Q1 lands, and it
puts a filesystem read inside a function documented as "async reads only, over the caller's
pool". The counter-argument is real enough that it should be revisited once Q1 is in: if the
pointer read stays at 1 ms, moving the computation into the inventory join and dropping the
startup task entirely is the simpler system, and the startup task should be treated as
provisional rather than load-bearing.

**Non-goals.** No auto-harvest, no provider turns, no re-probe. The signal is detection only;
acting on it stays an operator decision through the existing `baseline_harvest` script.

## Notes

- **Brief conflict, resolved toward the report.** The session standby instruction named
  `helioy-plugins/plugins/helioy-tools/skills/code-review/SKILL.md`. That file does not exist;
  `helioy-tools/skills/` contains no `code-review` entry, and the only `code-review` on disk
  is the built-in Claude Code command. The `code-hygiene` lens loaded and is applied in the
  Quality Map. The review lens was unavailable; findings above are hygiene-framed, and a
  correctness review of any resulting change should be run separately.
- Read-only throughout: no commits, no tracked-file edits, no provider turns, no backend
  starts, no subagents. Store access was read-only (`latest_harness_observation`,
  `latest_target_observations`) plus filesystem reads of `~/.transport-matters/baselines`.
