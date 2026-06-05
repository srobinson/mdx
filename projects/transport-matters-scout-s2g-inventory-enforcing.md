# Scout S2g backend: inventory + the enforcing flip

Read-only scout against main (1f9c1317). Backend only; the first-run UI
screen is deferred per the brief. Everything below is cited file+symbol and
the pointer state was verified firsthand by reading the embedded manifest.

**The single biggest decision up front: enforcing is NOT safe to flip now.
Every channel pointer in the embedded manifest ships `"status": "paused"`
(all four: stable and preview, for both claude and codex). Under enforcing,
a non-active pointer yields `compatibility_release_unavailable`, which
raises `HarnessCompatibilityRejected`. Flipping today rejects EVERY claude
and codex launch on every seam (claude CLI, codex CLI, capture RPC / desktop
canvas panes): a total launch outage with no channel escape, since both
channels are paused. Claude/codex pointers must be ACTIVATED first, gated on
the fresh-install proof; grok is naturally excluded (no launch path exists).**

## 1. Inventory: net-new service, three partial reads to consolidate

`harness_inventory()` does not exist. The word "inventory" appears only in
comments pointing at S2g (`harnesses/compatibility_service.py` module
docstring, `harnesses/resolver.py :: launch_options` docstring). It is a
net-new application service; natural home `harnesses/inventory.py`.

Reuse map, everything the join needs already exists:

- Installation: `capabilities.py :: detect_harnesses` walks every registered
  descriptor (`harnesses/__init__.py :: list_harness_descriptors`) and
  returns `{installed, path, version}` via a which-walk plus the bounded 2s
  `--version` probe.
- Enablement: `harnesses/enablement_store.py :: HarnessEnablementStore
  .list_intents` (executor scoped intents; absent means enabled).
- Channel state and release: `harnesses/compatibility_store.py ::
  embedded_channel_state` / `embedded_release_entry`; channel identity from
  `channel.py :: resolve_channel_id` (default `stable`).
- Blocks: `harnesses/blocks_store.py :: active_blocks_sync` merged by
  `harnesses/blocks.py :: merge_executor_blocks`.
- Connections: `harnesses/connections_store.py`.
- Compatibility judgment: `harnesses/compatibility.py :: match_release`,
  pure over the above snapshots.
- Enumeration: `harnesses/resolver.py :: launch_options(snapshots)` is
  already built for exactly this and has ZERO production callers today
  (the only `launch_options` import in `cli/__init__.py` is the unrelated
  `cli/launch_options.py` flag module). Inventory is the snapshot gatherer
  the pure resolver has been waiting for; `ResolverSnapshots` is the
  assembly target.

Surface shape: `/v1/harnesses` is a NEW read surface, not an extension of
the enablement read. Plan invariant 6 (RUNTIME-SURFACING-S2-PLAN.md) says
one service drives first run, REST, and MCP. Today three overlapping reads
exist: `api/v1/capabilities.py :: get_capabilities` (installed/path/version),
`api/v1/harness_enablement.py :: get_harness_enablement`
(enabled/configured/installed/eligible, no compatibility data), and nothing
for channel/compatibility. The inventory response strictly supersedes both
GET reads. Recommendation: `/v1/harnesses` projects `harness_inventory()`;
retire `GET /v1/capabilities` and the `GET /v1/harnesses/enablement` read in
the same slice (the PUT enablement write stays), per the no-parallel-paths
rule. Both are registered in `api/v1/router.py`, trivial to swap. MCP
projection: `api/v1/controlplane_mcp.py` is the FastMCP skin (478 lines,
room under the 700 threshold) and takes one read tool delegating to the same
service.

## 2. Startup refresh: nothing exists, the hook point is the lifespan

Today no harness state is established at startup at all. Every surface
probes on demand: the GET endpoints run `detect_harnesses` per request via
`asyncio.to_thread`, and the launch gates probe `observe_resolved_binary`
inline at `cli/launch_runtime.py :: prepare_launch`. There is no cache to
refresh and nothing blocking to remove.

The non-blocking hook point is `main.py :: lifespan` (the app's only
startup/shutdown owner; precedent: `_start_session_backed_services`
constructs stores there and the `finally` block closes them). An S2g refresh
is one `asyncio.create_task` spawned in the lifespan that warms an inventory
snapshot and runs the authentication/access probes
(`harnesses/probes/{claude,codex}.py`, grok stub pending S2h) as
diagnostics, per plan S2g item 4. Inventory reads serve last-known state and
never await the refresh. Launch gating must keep probing live at the launch
seam regardless; the refresh is a UX warm cache, not launch evidence.

## 3. The enforcing flip: mechanics, firsthand pointer state, blast radius

- The switch: `harnesses/compatibility_service.py :: COMPATIBILITY_ROLLOUT`
  (`"advisory"`), read through `compatibility_enforcing()`, which is shared
  by BOTH the launch gate (`_gate` raises after recording) and the pure
  resolver's dispositions (`resolver.py :: _compatibility_disposition` turns
  advisories into rejections). One constant flips both.
- Firsthand pointer state (`harnesses/compatibility_releases_v1.json`): four
  `channel_states`, `stable/claude`, `stable/codex`, `preview/claude`,
  `preview/codex`, every one `"status": "paused"`, pointing at embedded
  releases `claude-2.1.211-r1` and `codex-0.144.4-r1`.
- Paused fails closed by construction: `compatibility.py :: match_release`
  returns `compatibility_release_unavailable` whenever
  `channel_state.status != "active"`; under enforcing `_gate` raises
  `HarnessCompatibilityRejected` for any non-compatible outcome, and
  `gate_launch_preparation` converts internal failures into the same
  rejection.
- Coverage of the outage: every launch seam converges on
  `cli/launch_runtime.py :: prepare_launch` (capture RPC and claude CLI via
  `captured_run_context.py`, codex CLI via `cli/codex_cmd.py`), which calls
  the gate unless the caller is a dry run or client-disabled. Desktop canvas
  panes ride the capture RPC path, so they break too.
- Grok cannot break: `harnesses/__init__.py :: _GROK_DESCRIPTOR` has
  `launch=None`, so no launch path reaches the gate; no grok pointer is
  needed until S2h activates one after its conformance matrix passes.
- Activation is a release, not a runtime action:
  `compatibility_store.py :: RejectAllSignatureVerifier` rejects every
  mutable cached update (no trust root), so the ONLY way a pointer activates
  is editing the embedded manifest statuses to `"active"` and shipping a
  Transport Matters release. This matches plan S2g item 5 exactly: prove the
  fresh install, then ship active claude/codex pointers and the flip.

What still breaks after activation (the real enforcement teeth):

- Installed harness below `minimum_version` (claude < 2.1.211,
  codex < 0.144.4): `harness_update_required`, launch rejected.
- Version probe failure: `observe_resolved_binary` has a 2s `--version`
  timeout; a timeout means version `None`, `harness_version_unknown`,
  rejected under enforcing. A transiently slow binary kills a launch. Worth
  an explicit accept/mitigate decision (the advisory audit trail will show
  how often this happens in practice before the flip).
- Store unreachable: gate fails closed under enforcing. Note the enablement
  gate (#301, `harnesses/enablement_service.py :: gate_harness_enablement`)
  ALREADY fails closed on an unreachable store today, so store-down blocking
  launches is the existing posture, not new exposure.

Surface-and-decide framing for Stuart:

1. Hard flip now: NO. Paused pointers make it a total claude/codex outage.
2. Hard (activate + flip in one release) vs staged (release N activates
   pointers while still advisory, zero risk, and the gate's audit rows under
   the `harness_compatibility_gate` verb show real-world would-be outcomes;
   release N+1 flips once the audit shows `compatible` on live launches).
   Recommend STAGED: with CI down, the advisory recording is the only live
   conformance signal we have, and it is already built and writing.
3. Grok stays advisory/excluded by construction until S2h; no code needed.

## 4. Fresh-install proof without CI

The plan makes the proof a CI release gate (RUNTIME-SURFACING-S2-PLAN.md,
"the fresh install proof is a release gate in CI, not a local action";
completion criterion 10). With Actions down, the substitute follows the
existing warroom pattern (grok pane runs the full gate as the CI
substitute): a local release-gate recipe executed before the activation and
flip releases, consisting of the plan's repository gates verbatim
(`just check`, `just test`, `cd api && just migration-smoke`) plus the proof
itself: from a fresh `~/.transport-matters` and a fresh wheel install,
enable an installed harness and complete one real gated launch per harness.
The evidence is durable and firsthand checkable because the gate records it
already: the run-dir compatibility facts artifact
(`harnesses/compatibility_facts.py :: write_compatibility_facts`) and the
audit rows from `compatibility_service.py :: gate_audit_action` with
`outcome=compatible` under the target rollout. Codify as a workflow when
Actions returns; the local run is a substitute, not a redefinition.

## Slice breakdown (backend only)

- S2g-a inventory: `harness_inventory()` in `harnesses/inventory.py`
  assembling `ResolverSnapshots` and calling `launch_options`; `/v1/harnesses`
  REST projection; one MCP read tool in `controlplane_mcp.py`; retire the
  two subsumed GET reads. Tests: zero/one/several harnesses, every failed
  check without cross-harness blocking (plan verification list).
- S2g-b startup refresh: one non-blocking task in `main.py :: lifespan`
  warming the inventory snapshot and running auth/access probes as
  diagnostics.
- S2g-c activation release: flip the four embedded pointer statuses to
  `active` (claude/codex only) after the local fresh-install proof passes;
  still advisory, zero launch risk, starts producing live conformance
  evidence in the audit.
- S2g-d the flip: `COMPATIBILITY_ROLLOUT = "enforcing"` once the audit shows
  compatible outcomes on real launches; the enforcing branch and per-seam
  acceptance tests already exist from S2f, so this slice is one constant
  plus the version-probe-timeout decision.
