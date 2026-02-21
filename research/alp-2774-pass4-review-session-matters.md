---
title: ALP-2774 pass 4 review of sm isolation gate
type: research
tags: [session-matters, linear, moe-review, sm-isolation, docker]
summary: Final live re-fetch verified N1 and N2 fixed; V signoff sent for ALP-2774 master tree.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-24
updated: 2026-05-24
---

## Executive Summary

Reviewed the live ALP-2774 master tree for pass 4 of the MoE issue review. After user adjudication confirmed extend, not merge, the tree was restored with ALP-2777 as a separate worker. Final live re-fetch verified the remaining cross-reference blockers were fixed, so V signoff was sent for the ALP-2774 master tree.

## Project Metadata

- Project: `session-matters`
- Language: Rust
- Build system: Cargo workspace, generated CLI and MCP surfaces from `tools/*.toml` through `crates/sm-cli/build.rs`
- fmm status: `.fmm.db` exists in `session-matters`; sibling `runtime-matters` also has `.fmm.db`
- Relevant external wire: `lilo-rm-core` and `lilo-rm-client` 0.7.0 from sibling `runtime-matters`

## Architecture

`session-matters` is the control plane for Helioy agent sessions. `sm` sends spawn requests to `smd`, which persists sessions, resolves namespaces and agent config, then delegates runtime work to `runtime-matters` through `RtmdDriver`.

Key reviewed paths:

- CLI spawn path: `crates/sm-cli/src/cli/run.rs:23-75`
- CLI daemon lifecycle: `crates/sm-cli/src/cli/daemon.rs:26-67`
- CLI wait surface: `crates/sm-cli/src/cli/wait.rs:9-36`
- Daemon spawn and delete paths: `crates/sm-daemon/src/handler.rs:132-215`, `392-431`
- MCP run handler: `crates/sm-daemon/src/mcp_tools.rs:117-163`
- rtmd bridge: `crates/sm-driver/src/rtmd.rs:48-80`
- runtime container argv: `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:66-98`

## Key Patterns

- `sm daemon start` is idempotent. It reports the currently running daemon and returns success rather than replacing it.
- Generated public surfaces are tied to `tools/run.toml`; changing run parameters affects CLI help, MCP schemas, generated help constants, and snapshots together.
- runtime-matters names Docker containers `rtm-<session_id>` and labels them with `io.helioy.runtime-matters.session=<session_id>`.
- After pass 2 amendments, ALP-2777 is absorbed into ALP-2776. Any dependency prose should describe ALP-2776 as owning both sm-core fields and SpawnLaunch/rtmd forwarding.

## Detailed Findings

### F C1: ALP-2782 does not force fresh daemons for the merge gate

Evidence:

- ALP-2782 tells the operator to start daemons before the gate.
- `crates/sm-cli/src/cli/daemon.rs:start` checks `status()` and returns `Ok(())` when any daemon is already running at lines `28-32`.
- `crates/sm-cli/src/cli/daemon.rs:status` only checks pid liveness and socket existence at lines `114-118`; it does not verify that the daemon was spawned from the freshly built binary.
- The peer accepted the same stale-daemon concern for `rtmd`: a default `~/.rtm/sock` daemon can also be stale relative to the runtime-matters checkout being tested.

Risk: a stale `smd` or `rtmd` on default sockets can accept requests from a fresh CLI, so the gate can test old daemon behavior while appearing to have followed the documented preconditions.

Bus response: conditional sign-off requires hermetic fresh `smd` and `rtmd` instances, preferably isolated `SM_HOME` and `RTM_SOCKET_PATH` for the gate run.

### F C2: ALP-2782 cleanup proof swallows Docker query failure

Evidence:

- Earlier ALP-2782 cleanup proof used `docker ps --filter "label=io.helioy.runtime-matters.session=$SESSION_ID" --quiet | grep -q . && fail || true`.
- Without `set -o pipefail`, Darwin and Linux shells return the status of `grep` for the pipeline. If `docker ps` fails and emits no stdout, `grep -q .` returns nonzero and the trailing `|| true` returns success.
- runtime-matters does provide the intended session-bound labels in `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:81-82`, so the locator is correct. The failure handling around the locator is the defect.

Risk: the cleanup proof can pass when Docker was not queried successfully, so it does not prove that the session container is absent.

Bus response: conditional sign-off requires a split Docker query, immediate failure on nonzero `docker ps`, nonempty output check after capture, and `set -euo pipefail` as defense in depth.

### Peer S1: ALP-2779 dependency prose drift after ALP-2777 absorption

Evidence:

- Live ALP-2779 dependency text says it is blocked by sm-core wire fields and `tools/run.toml` schema declaring the new params.
- Live ALP-2782 now absorbs ALP-2777 into ALP-2776 and its `Execute:` list is `ALP-2776, ALP-2778, ALP-2779, ALP-2780, ALP-2781`.
- Live ALP-2779 `blockedBy` contains ALP-2776 and ALP-2778 only.
- Current source still has `SpawnLaunch` without `isolation`, `image`, or `mounts` at `crates/sm-driver/src/driver.rs:21-28`, and `spawn_launch` still constructs the old fields at `crates/sm-daemon/src/handler.rs:609-644`. Those carrier fields are part of the ALP-2776 absorbed scope after the amendment.
- Current `agent_run` builds `SpawnRequest` without the new fields at `crates/sm-daemon/src/mcp_tools.rs:117-163`; ALP-2779 owns adding the handler reads.

Risk: ALP-2779 acceptance asserts values reach `SpawnLaunch`, but its dependency prose does not name the carrier forwarding prerequisite in the current absorbed shape.

Bus response: accepted the substance, but rejected the peer's proposed edit that would re-add ALP-2777 as a blocker. The required edit should say ALP-2776 supplies sm-core fields plus SpawnLaunch/rtmd forwarding, and ALP-2778 supplies the public schema/CLI surface.

### Structural integrity status after follow-up nudge

Live Linear changed during the pass. The current gate has ALP-2777 absorbed into ALP-2776 and removed from `Execute:`. The relevant executable set is now ALP-2776, ALP-2778, ALP-2779, ALP-2780, and ALP-2781.

ALP-2779 is blocked by ALP-2776 and ALP-2778 in live Linear. That relation matches the absorbed worker graph, but ALP-2779 body prose still needs the dependency rewrite described in S1.

### Locked amendment set after peer reconciliation

Final bus consensus before orchestrator edits:

1. C1: ALP-2782 gate must use hermetic fresh `smd` and `rtmd` instances, not default stale sockets.
2. C2: ALP-2782 cleanup proof must use a split Docker query with `set -euo pipefail` at the top of the block.
3. S1: ALP-2779 Dependencies prose must say ALP-2776 supplies sm-core fields plus SpawnLaunch/rtmd forwarding, while ALP-2778 supplies the public schema/CLI surface.

Pass-2 items outside this locked set were accepted as already satisfied by live Linear or withdrawn. Clean V should wait until the orchestrator lands these three amendments and a live re-read verifies them.

### Verify re-read blocker: ALP-2781 stale after ALP-2777 absorption

After the orchestrator signaled that C1, C2, and S1 had landed, live Linear was re-read before V. ALP-2782 now executes `ALP-2776, ALP-2778, ALP-2779, ALP-2780, ALP-2781`, and ALP-2777 is status `Duplicate`, canceled into ALP-2776. ALP-2779 Dependencies are fixed.

However, ALP-2781 still says it reviews "five worker issues" and retains a full `### ALP-2777` section with separate driver/daemon plumbing criteria. That contradicts the current gate shape and breaks PER scope mirroring. A clean V was not sent. Bus response was an `E` requiring ALP-2781 to be updated to the current four-worker shape or to fold the former ALP-2777 review bullets under ALP-2776 before sign-off.

### Hold state after orchestrator rollback directive

A later bus directive from `session-matters:general:2:2.1` put V on hold. The current Linear state at that moment was not the artifact under MoE review because external agents had reverted the user's pass-2 decision to keep ALP-2777 separate. The orchestrator is restoring the tree to the post-pass-3 shape, reopening ALP-2777, then applying pass-4 C1 and C2 amendments.

Implication: the earlier ALP-2781 stale-PER blocker was valid against the temporary absorption state, but should not drive V or further edits against the restored artifact unless it remains true after the new VERIFY. The next action is to wait for the new VERIFY, then re-fetch ALP-2782, workers, and PER live before responding.

### Triple-nudge hold update

Subsequent bus messages from `transport-matters:general:1:1.1` and `helioy:general:9:1.1` confirmed all ALP-2774-tree edits are paused. Root cause: pass 2 option text bundled two possible interpretations, "merge ALP-2777 into ALP-2776" or "extend ALP-2776 while keeping ALP-2777". `session-matters:general:2.1` reads the authoritative user direction as extend, not merge; other agents treated merge as selected.

Current stop state: no V, no Linear edits, and do not treat S1 or the temporary ALP-2777 absorption state as the artifact under review. Wait for user adjudication and a restored/VERIFY signal. Then re-fetch ALP-2782, all worker issues, and ALP-2781 live before responding. Pass-4 C1 and C2 remain valid and re-layer cleanly on either final shape.

### User adjudication received: extend, not merge

`helioy:general:9:1.1` reported user direction: "Extend, not merge." `session-matters:general:2.1`'s reading is authoritative. The expected restored artifact has ALP-2777 reopened as `Todo`, still listed in ALP-2782 `Execute:`, and still present in the required-order chain.

Follow-up bus context clarified S1 under the restored extend branch: the substance survives, but the fix text changes. ALP-2779 Dependencies should name ALP-2777 as a required SpawnLaunch-carrier blocker, matching the live graph and gate prose from pass 3. Do not use absorption prose.

A restored VERIFY arrived and live Linear was re-fetched. The artifact was not ready for V; an E was sent because live ALP-2779, ALP-2781, and ALP-2777 relation state still contradicted the restored extend shape.

### Restored VERIFY re-read outcome: E sent

After `session-matters:general:2.1` sent restored VERIFY, live Linear was re-fetched for ALP-2776, ALP-2777, ALP-2778, ALP-2779, ALP-2781, and ALP-2782. Three inconsistencies remained:

1. ALP-2779 `blockedBy` includes ALP-2777, but its Dependencies prose still says only that sm-core wire fields and `tools/run.toml` schema are prerequisites. It does not name ALP-2777 or the ALP-2782 design call resolution.
2. ALP-2781 is still the absorbed four-worker PER. It says ALP-2777 was absorbed into ALP-2776 and canceled, while restored ALP-2782 lists ALP-2777 in `Execute:`.
3. ALP-2777 is reopened as `Todo`, but its Linear `duplicateOf` relation still points at ALP-2776.

Bus response sent: `E|restored VERIFY does not match live Linear... Re-restore these before V.`

### Reconciliation hold after contradiction report

`helioy:general:9.1` reported a contradiction between `session-matters:general:2.1`'s restored VERIFY broadcast and the live Linear fields fetched by this agent. The standing state is hold V until `session-matters:general` re-fetches ALP-2779, ALP-2781, and ALP-2777 and either re-restores the fields or posts the live values it sees.

Bus acknowledgment sent: no V until reconciliation lands. The previous E was based on live Linear returned after restored VERIFY, not memory.

### Cross-session reconciliation update

`helioy:general:9.1` reported that a parallel `littleorgans:general:4.1` session surfaced the extend-versus-merge contradiction to the user, and the user confirmed extend is authoritative. Current reconciliation status:

- ALP-2779 generic Dependencies prose is explained by reverting to pre-merge state; the S1 extend-branch prose fix is still pending.
- ALP-2781 four-worker PER was likely cache lag after a revert to five-worker shape; re-fetch after the next restored broadcast should verify.
- ALP-2777 `duplicateOf=ALP-2776` is still real and must be cleared.

Standing pending items before V: session-matters must clear ALP-2777 duplicateOf and layer ALP-2779 S1 worker-prose fix naming ALP-2777 as the SpawnLaunch-carrier blocker. Then re-broadcast restored; this agent will re-fetch live before any V/E.

### Current blockers after 19:17 re-fetch

Live state now has E1, E2, and E3 clean: ALP-2779 Dependencies names ALP-2776/2777/2778, ALP-2781 is back to the five-worker PER, and ALP-2777 duplicateOf is cleared. Two new cross-reference consistency blockers remain:

- N1: ALP-2782 Required order and ALP-2777 body say ALP-2776 before ALP-2777, but live Linear relations still had `ALP-2777.blockedBy=[]` and ALP-2776 did not list ALP-2777 in `blocks`. Restore the ALP-2776 to ALP-2777 blocker edge.
- N2: ALP-2779 worker acceptance includes a `session_run` parity test, but ALP-2781 PER's ALP-2779 section still mirrors only `agent_run`, negative parse, and optional reads. Add the `session_run` review bullet.

Bus status: N1 and N2 accepted by `helioy:general`; V held until `session-matters:general` fixes both and broadcasts.


### Final verify after N1 and N2 fixes: V sent

A final live re-fetch of ALP-2777 and ALP-2781 verified the accepted N1 and N2 fixes:

- ALP-2777 is `Todo`, not canceled, `duplicateOf=null`, and its Linear relation graph now has `blockedBy=[ALP-2776]`. This matches its body and ALP-2782's required order.
- ALP-2781 is still the five-worker PER and the ALP-2779 review section now includes the `session_run` parity bullet. The bullet mirrors ALP-2779's worker acceptance and names the shared `"agent_run" | "session_run"` arm in `crates/sm-daemon/src/mcp_tools.rs`.

Bus response sent on topic `2774-review-pass4`: `V|I sign off on ALP-2774 master tree as currently filed`. Message id: `4e4ef089-0da8-4231-8ed8-c1092d8777f8`.

## Dependencies

- `lilo-rm-core` 0.7.0 adds `SpawnRequest.isolation`, `SpawnRequest.image`, and `SpawnRequest.mounts` at `../runtime-matters/crates/rtm-core/src/types/spawn.rs:86-103`.
- runtime-matters Docker argv labels and names containers in `../runtime-matters/crates/rtm-daemon/src/docker_argv.rs:66-98`.
- `IsolationPolicy::from_str` accepts `host`, `docker`, and `docker:<profile>` in `../runtime-matters/crates/rtm-core/src/isolation.rs:36-58`.
- `SpawnTarget::from_str` requires `tmux:` for tmux targets in `../runtime-matters/crates/rtm-core/src/types/spawn.rs:125-141`.

## Relevance to Helioy

The review protects the Helioy operator merge gate from false positives. The target feature crosses session-matters, runtime-matters, Docker, tmux, generated MCP schemas, and Linear worker ordering, so the gate must prove the correct daemon binaries and the correct container lifecycle.

## Open Questions

- No pass-4 issue-tree blockers remain after the final live re-fetch.
- Operator execution remains future work: the master gate still needs to be run against landed code before merge.
