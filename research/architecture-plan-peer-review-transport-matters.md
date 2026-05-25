---
title: Transport Matters Architecture Plan Peer Review
type: research
tags: [transport-matters, architecture, peer-review, linear, run-id, provider-compatibility, harnesses]
summary: Peer consensus review of the Transport Matters execution plan found conditional signoff issues in K2 gates, K2 sequencing, K3 sizing, K3 dependencies, and verification wording.
status: active
source: codebase-analyst
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Executive Summary

Reviewed `/Users/alphab/.mdx/projects/transport-matters-arch-plan.md` against the Q1, Q2, and Q3 verification artifacts and live code. The plan is broadly aligned with the verified architecture, but it needs corrections before clean signoff: K2.1 has a green gate conflict, K2.6 has inconsistent dependencies, K3 onboarding is over serialized, K3.8 is too large, K3.5 has a false frontend dependency, and several acceptance criteria prescribe implementation details.

## Project Metadata

- Repo: `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`.
- Languages: Python 3.12 backend, TypeScript frontend and desktop.
- Frameworks: FastAPI, Typer, mitmproxy, Vite, React, Electron.
- Topology from fmm: 352 indexed files, 64,056 LOC. `api/` has 205 files and 42,287 LOC, `www/` has 133 files and 20,181 LOC, `desktop/` has 14 files and 1,588 LOC.
- Verification run: `fmm validate`, result: all 352 files indexed and up to date.
- Root gate: `just test` runs desktop, www, then api (`justfile:26-29`). The delegated gates are `api/justfile:26-27`, `www/justfile:18-19`, and `desktop/justfile:5-6`.

## Architecture

Transport Matters has three relevant seams:

1. Multi instance launch and storage, centered on `run_id`, workspace locks, manifests, storage roots, CLI launch flows, and per process API/UI state.
2. Provider wire compatibility, centered on mitmproxy request handlers, provider adapters, canonical IR, exchange recording, token counting, and breakpoint release.
3. Harness descriptor driven CLI onboarding, centered on `HarnessDescriptor`, CLI commands, help text, adapter registries, `/api/meta`, frontend typing, and optional desktop launch support.

fmm confirms the current K2 live request mutation surface. `handle_http_request` always writes `flow.request.set_text(adapter.outbound_request(curated_ir).decode())` at `api/src/transport_matters/addon_handlers.py:121-135`, and `handle_codex_websocket_message` always writes `message.content = adapter.outbound_request(curated_ir)` at `api/src/transport_matters/addon_handlers.py:233-242`. Storage already uses structural IR equality for persisted curated IR in `_persistable_curated_ir` at `api/src/transport_matters/exchange_recorder.py:72-82`, but `_curated_request_raw` still compares serialized bytes at `api/src/transport_matters/exchange_recorder.py:62-69`.

fmm also confirms the current K1 launch order. `run_start` resolves storage before creating `run_id` at `api/src/transport_matters/cli/start_cmd.py:196-207`, `run_codex` does the same at `api/src/transport_matters/cli/codex_cmd.py:331-342`, and `resolve_storage_dir` currently accepts only `storage_dir` and `working_dir` at `api/src/transport_matters/cli/launch_runtime.py:238-240`.

## Key Patterns

- Use fmm first for structural review. `fmm_list_files`, `fmm_file_outline`, `fmm_read_symbol`, and `fmm_dependency_graph` were enough to validate the plan's key code references without broad file reads.
- Treat characterization issues carefully. A task cannot require new desired behavior to pass on `main` unless those tests are explicit expected failures or documentation only.
- Gate the smallest behavior slice. Provider compatibility should gate final capture proof for new CLIs, not descriptor, CLI, help, or metadata scaffolding.

## Detailed Findings

### 1. K2.1 has a green gate conflict

Plan issue: K2.1 is a characterization task, but acceptance says tests should demonstrate unchanged IR requests should not need outbound serialization, and its verification gate says to run targeted API pytest. See `transport-matters-arch-plan.md:162-170`.

Live code contradicts that desired behavior on `main`: HTTP requests always write serialized IR at `api/src/transport_matters/addon_handlers.py:121-135`, and Codex WebSocket initial request frames always assign serialized IR at `api/src/transport_matters/addon_handlers.py:233-242`. Q2 verification documents the same split at `/Users/alphab/.mdx/projects/transport-matters-arch-q2-verify.md:35-43` and recommends no body assignment when IR is unchanged at `:60-69`.

Consensus correction: make K2.1 characterize current behavior with explicit future cases, or move the desired no mutation assertions to K2.3. If the desired tests stay in K2.1, mark them as expected failures and keep them outside the green gate.

### 2. K2.6 dependency text is inconsistent

Plan issue: K2.6 has three inconsistent dependency signals. The sub issue field says `Deps: K2.1` at `transport-matters-arch-plan.md:218`. The graph branches K2.6 from K2.2 at `:361`. The parallel note says K2.6 and K2.7 can run after K2.1 while using the shared decision from K2.2 at `:370`. Its acceptance also says the overlay does not alter unedited requests when K2.3 skip mutation applies at `:216`.

Consensus correction: keep K2.6 dependent on K2.1 so the edited path overlay can proceed in parallel. Fix the graph and parallel note so K2.6 does not require K2.2. Move the K2.3 conditioned unedited request acceptance from K2.6 to K2.8 as integration proof.

### 3. K3 onboarding is over serialized by K2.8

Plan issue: K3.7 and K3.8 both depend on K2.8 as whole issues at `transport-matters-arch-plan.md:319` and `:329`, and the cross keystone graph makes K2.8 a hard quality gate at `:351`. That is correct for capture behavior and provider compatibility closeout. It also blocks descriptor, CLI, help, and metadata scaffolding unnecessarily.

Consensus correction: K2.8 should gate only capture/provider compatibility closeout for K3.7 and K3.8. Descriptor, CLI, help, and metadata scaffolding can proceed once K3.6 is stable.

### 4. K3.8 is too large, and K3.7 should be resized if reuse holds

K3.8 bundles a new Gemini adapter, IR translation, unknown field policy, descriptor driven launch, CLI entry point, help text, metadata, capture smoke, and root `just test` into one L issue at `transport-matters-arch-plan.md:321-329`. Q3 verification says safe descriptor migration alone is likely two to three focused days because launch semantics and Codex trust material are risky (`/Users/alphab/.mdx/projects/transport-matters-arch-q3-verify.md:134-149`).

Consensus correction: split Gemini into at least adapter/protocol and harness/CLI/metadata/smoke slices. Resize K3.7 from L to M if OpenCode `/v1/messages` reuse is confirmed. Split provider identity wrapper work if that becomes the real complexity.

### 5. K3.5 falsely depends on K3.4

Plan issue: K3.5 lists `Deps: K3.3, K3.4` at `transport-matters-arch-plan.md:299`. K3.5 is backend generic launch extraction. K3.4 preserves the frontend `/api/meta` contract. Q3 verification's staged migration sequence puts frontend contract work outside the launch extraction path (`/Users/alphab/.mdx/projects/transport-matters-arch-q3-verify.md:144-149`).

Consensus correction: K3.4 and K3.5 should both hang off K3.3. Drop K3.4 from K3.5 dependencies.

### 6. Some acceptance criteria are implementation prescriptive

Plan issue: K2.3 acceptance names exact implementation mechanisms: HTTP handler avoids `set_text`, and Codex WebSocket handler avoids assigning `message.content`. See `transport-matters-arch-plan.md:181-188`. These are current symbols, confirmed at `api/src/transport_matters/addon_handlers.py:121-135` and `:233-242`, but Linear acceptance should state observable behavior.

Consensus correction: replace those criteria with “unchanged HTTP bodies and WebSocket frames are not mutated on the live path.” K2.4 also mentions `_curated_request_raw` at `transport-matters-arch-plan.md:191-198`; it should be behavior only too.

### 7. Verification wording needs full stack clarity

Root `just test` is full stack: desktop, www, then api (`justfile:26-29`). Therefore K3 wording that says “desktop tests if scoped in” is inaccurate when the closeout gate is root `just test`, because desktop tests run unconditionally. Use `cd api && just test` or `uv run --project api ...` for backend targeted gates, and reserve root `just test` for parent and program closeout.

### 8. Coverage is otherwise complete, with one desktop strengthening point

The plan covers the required verifier corrections for `mitmdump.log` isolation, sorted key curated raw diffs, token counting realignment, OpenCode provider identity, frontend `/api/meta`, the three K1 open questions, the two K3 open questions, and `main` as source of truth. Relevant plan lines include `transport-matters-arch-plan.md:48-52`, `:73`, `:98-102`, `:155-160`, `:166-168`, `:200-208`, `:248`, `:283-290`, and `:432`.

Desktop is represented as a K3.1 scope decision, but if desktop launch support is included in v1, the plan should explicitly name the desktop touch points: `desktop/src/backendProcess.ts:5-9`, `desktop/src/backendProcess.ts:71-79`, and `desktop/src/main.ts:238-247`.

## Dependencies

- fmm, used for index validation, topology, outlines, symbol reads, and dependency graphs.
- mitmproxy request and WebSocket mutation points in `addon_handlers.py`.
- Provider adapters, IR, exchange recorder, and token counting for K2 behavior.
- CLI launch modules, `HarnessDescriptor`, `/api/meta`, frontend API client, and desktop launcher files for K3 behavior.

## Relevance to Helioy

This review reinforces two Helioy planning rules. First, Linear sub issues must be independently green unless they explicitly declare expected failures. Second, cross keystone dependencies should gate the smallest behavior slice they actually protect, rather than serializing unrelated scaffolding.

## Open Questions

- Should K3.7 provider identity wrapper work be part of the resized OpenCode issue, or a separate small issue if OpenCode reuse holds?
- Should desktop support get a dedicated K3 issue if K3.1 scopes it into v1?

## Bus Outcome

The Codex reviewer and Claude peer converged. Claude round 2 confirmed both reviewers' conditional lists were identical and that applying items 1 through 8 would clear both signoffs. The orchestrator applied all 8 consensus changes to `/Users/alphab/.mdx/projects/transport-matters-arch-plan.md`; Codex re-read the plan from disk, confirmed the edits, and sent clean final signoff: `I sign off on the plan as currently filed`. A later peer message flagged possible K1 graph versus Deps drift, but a fresh disk read showed K1.5 Deps=K1.4, K1.6 Deps=K1.4, K1.7 Deps=K1.5/K1.6, matching the graph and parallel note; Codex replied that no blocker remained. Claude then independently re-read K1 from disk, confirmed the same reconciliation, and signed off clean. Both reviewers have disk-verified clean signoff. Final parseable conditional signoff before the clean round was:

“I sign off conditional on the following changes:” followed by these required changes:

1. K2.1 keeps characterization green and moves or xfails desired no mutation assertions.
2. K2.3 and K2.4 use behavioral acceptance criteria.
3. K2.6 keeps Deps=K2.1, fixes graph and parallel text, and moves the K2.3 conditioned unedited request AC to K2.8.
4. K2.8 gates only capture/provider compatibility closeout for K3.7 and K3.8.
5. K3.8 splits Gemini work; K3.7 resizes to M if OpenCode reuse is confirmed.
6. K3.5 drops K3.4 from dependencies.
7. Verification text states root `just test` is full stack.
8. Desktop touch points are named if K3.1 selects desktop in v1.
