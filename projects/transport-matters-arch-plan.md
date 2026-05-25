---
title: Transport Matters Architecture Execution Plan
type: design
tags: [transport-matters, architecture, run_id, provider_data, harnesses, linear]
summary: Linear ready execution plan for multi instance storage, forward compatible request handling, and load bearing harness descriptors.
status: active
source: project-planner
confidence: high
created: 2026-05-28
updated: 2026-05-28
---

## Plan: Execute the Transport Matters architecture keystones

### Goal

Deliver three independent architecture keystones for Transport Matters: multi instance same directory runs, forward compatible provider request handling, and descriptor driven CLI onboarding for OpenCode and Gemini.

### Explicit Requirements

- Write this plan to `/Users/alphab/.mdx/projects/transport-matters-arch-plan.md`.
- Use one Linear sub-parent per keystone: K1, K2, K3.
- Make every work item session sized, behavioural, and verifiable.
- Include explicit dependencies inside and across keystones.
- Include verification gates per item. The repo gate is `just test`.
- Fold in all Q1, Q2, and Q3 verifier corrections.
- Treat `main` as the source of truth. Do not plan branch merges from stale feature branches.
- Note that ALP-2434 scoped Gemini and OpenCode out. K3 onboarding is a net new initiative.

### Inferred Requirements

- Preserve the import DAG from `api/CLAUDE.md`: `ir -> adapters -> rules -> pipeline -> storage -> breakpoint -> server`.
- Prefer API and CLI parity tests before refactors that touch launch behavior.
- Preserve the frontend `/api/meta` harness contract while making descriptors load bearing.
- Keep K1 UI per instance for this initiative. Aggregated UI needs a separate coordinator epic.
- Use `uv run --project api ...` or `cd api && PYTHONPATH=src uv run pytest ...` for targeted API tests when needed. Prefer root `just test` before closeout.

### Assumptions

- Transport Matters remains pre-release, so breaking internal layout changes are acceptable when they simplify the final design.
- Default storage should become run scoped. Explicit `--storage-dir` semantics must be decided before implementation.
- K3 v1 covers backend API and CLI onboarding. Desktop launch support is a scope decision in K3.1 and should not slip in implicitly.
- OpenCode is expected to speak Anthropic Messages over `/v1/messages`. If that is false, K3.6 becomes an adapter discovery item rather than a reuse item.
- The preferred K3 layout for this plan is staged horizontal modules plus registries, with strict import boundaries. A physical `providers/<name>/` layout remains viable only if package `__init__` files stay metadata only and never import both adapter and CLI launch code.

### Open Questions

- K1.1 must decide explicit `--storage-dir` sharing semantics.
- K1.1 must decide same CWD `paths` resolution: newest run, `--run-id`, or all runs.
- K1.1 must decide instance discovery shape: per run manifest directory, scoped manifest filename, or registry file.
- K3.1 must decide whether desktop launch support is in v1.
- K3.1 must decide how OpenCode appears in provider identity when it reuses the Anthropic wire adapter.

### Linear Shape

Master issue: Execute Transport Matters architecture corrections

Sub-parents:

1. K1: Enable multi instance runs per working directory
2. K2: Preserve provider wire compatibility unless traffic is edited
3. K3: Make harness descriptors load bearing and onboard new CLIs

---

### Parent Issue 1: K1: Enable multi instance runs per working directory

Description: Allow multiple Transport Matters instances to run from the same resolved CWD by extending the existing `run_id` boundary into storage, manifests, logs, and discovery. Keep the UI per instance and defer aggregated multi run UI to a future coordinator epic.

Acceptance Criteria:

- Two instances can launch from the same CWD with automatically allocated ports.
- Default storage, manifests, locks, and `mitmdump.log` do not collide across runs.
- `instances`, `paths`, `/api/v1/meta`, and `/api/v1/exchanges` report or filter the intended run without ambiguity.
- Aggregated UI is explicitly deferred with a rationale.
- Root `just test` passes before closeout.

  ├── Sub-issue K1.1: Decide multi run filesystem contract
  │   Description: Close the required design decisions before code changes: explicit `--storage-dir` behaviour, same CWD `paths` disambiguation, and instance discovery shape. Record that `main` is authoritative and stale feature branches are not merge inputs.
  │   Acceptance:
  │   - The contract states whether explicit `--storage-dir` is caller owned, run scoped, or rejected for same root concurrency.
  │   - The contract defines `paths` behaviour when several live runs share a CWD.
  │   - The contract chooses one manifest discovery model and explains why it is safer than the alternatives.
  │   - The contract states per instance UI for this initiative and defers aggregation.
  │   Verification Gate: Review the written contract against Q1 verification and `api/CLAUDE.md`; no code gate required beyond `fmm validate` if files move.
  │   Size: S | Deps: none | Labels: architecture, backend, storage
  │
  ├── Sub-issue K1.2: Move run creation before storage resolution
  │   Description: Ensure Claude and Codex launch paths create or receive `run_id` before resolving default storage. The storage resolver must be able to return a run scoped default path.
  │   Acceptance:
  │   - Claude and Codex launches compute the same `run_id` used for env, manifest, storage, and API metadata.
  │   - Default storage resolution can incorporate `run_id` without duplicating launch logic.
  │   - Explicit storage handling follows the K1.1 contract.
  │   Verification Gate: Target CLI launch storage tests for Claude and Codex, then `cd api && just test` for API closeout on this item.
  │   Size: M | Deps: K1.1 | Labels: backend, cli, storage
  │
  ├── Sub-issue K1.3: Scope default storage and logs by run
  │   Description: Move default disk storage and runtime log placement under a run scoped directory so `index.jsonl`, exchange directories, temporary index files, and `mitmdump.log` are isolated per instance.
  │   Acceptance:
  │   - Default storage for two same CWD runs resolves to distinct roots.
  │   - Disk layout paths remain relative to each run root.
  │   - `mitmdump.log` lands under the run scoped storage root.
  │   - Existing single instance storage tests still pass.
  │   Verification Gate: Target storage layout and start storage tests, plus a smoke test that two computed roots differ for one CWD.
  │   Size: M | Deps: K1.2 | Labels: backend, storage, observability
  │
  ├── Sub-issue K1.4: Replace workspace singleton lock with run safe locking
  │   Description: Remove the long lived same CWD launch gate while preserving safety for manifest publication and per run lifecycle cleanup. Use the K1.1 discovery model to choose per run locks or a short registry lock.
  │   Acceptance:
  │   - Same CWD launch no longer fails solely because another run is live.
  │   - Per run liveness remains observable by `instances`.
  │   - Manifest writes and cleanup cannot corrupt another live run.
  │   - Stale run cleanup only removes the selected run artifacts.
  │   Verification Gate: Lock and instances tests cover concurrent same CWD runs, stale manifests, and reaping.
  │   Size: L | Deps: K1.3 | Labels: backend, cli, lifecycle
  │
  ├── Sub-issue K1.5: Update instance discovery and path resolution
  │   Description: Teach `instances` and `paths` to understand multiple manifests under one workspace identity. Apply the K1.1 disambiguation rule without relying on a single `manifest.json` at the workspace root.
  │   Acceptance:
  │   - `instances` lists each live run separately with PID, ports, CWD, and run id.
  │   - `paths` handles multiple same CWD runs according to the chosen rule.
  │   - Reap and stale detection operate on one run at a time.
  │   - Ambiguous cases produce actionable errors rather than silent selection unless newest is the chosen policy.
  │   Verification Gate: CLI tests for `instances`, `paths`, and reap across one run, multiple live runs, and stale runs.
  │   Size: L | Deps: K1.4 | Labels: backend, cli, lifecycle
  │
  ├── Sub-issue K1.6: Preserve per instance API and UI semantics
  │   Description: Keep `/api/v1/meta`, `/api/v1/exchanges`, SSE, breakpoint controls, settings, and frontend state scoped to the serving process run. Do not attempt aggregation in this workstream.
  │   Acceptance:
  │   - `/api/v1/meta` reports the current process run id and storage identity.
  │   - `/api/v1/exchanges` defaults to the current run and keeps existing history behaviour only where it is still valid.
  │   - Frontend state remains keyed to the current run id.
  │   - Documentation names aggregated UI as a separate future epic because broadcast, breakpoint, settings, and storage are process local.
  │   Verification Gate: API meta and exchanges tests plus frontend API contract tests if response shape changes.
  │   Size: M | Deps: K1.4 | Labels: backend, frontend, api
  │
  ├── Sub-issue K1.7: Prove same CWD multi instance behaviour
  │   Description: Add an end to end verification path that launches or simulates two same CWD instances, checks distinct ports and storage roots, and verifies isolation across manifests, logs, and exchange listing.
  │   Acceptance:
  │   - The test proves two same CWD runs do not share storage, manifests, or logs by default.
  │   - The test proves pinned port collisions still fail with a clear error.
  │   - The test proves per instance API filtering returns only the intended run by default.
  │   - Operator docs explain the new same CWD behaviour.
  │   Verification Gate: Target integration test plus root `just test`.
  │   Size: L | Deps: K1.5, K1.6 | Labels: backend, integration, docs

---

### Parent Issue 2: K2: Preserve provider wire compatibility unless traffic is edited

Description: Stop mutating live provider requests when the pipeline leaves the IR unchanged, then improve edited path fidelity with shared mutation decisions, structural equality in storage and counting, Anthropic raw overlays, and explicit provider overflow where surfaced.

Acceptance Criteria:

- HTTP and Codex WebSocket requests are not rewritten when `curated_ir == ir`.
- The implementation does not reinject captured `raw` bytes, because the captured value is not guaranteed byte faithful.
- Storage does not record false curated request diffs caused only by canonical JSON serialization.
- Token counting uses original request semantics for the before side and avoids an after count when IR is unchanged.
- Edited Anthropic requests preserve unknown nested fields at message and content block levels.
- Root `just test` passes before closeout.

  ├── Sub-issue K2.1: Add provider compatibility characterization tests
  │   Description: Lock current and desired behaviour before changing request mutation. Cover HTTP, Codex WebSocket, storage curated raw diffs, token counting, and Anthropic nested extras. This item must pass on main without requiring the K2 change.
  │   Acceptance:
  │   - Characterization tests pass on main by asserting CURRENT behaviour: HTTP and Codex WebSocket requests are serialized from IR even when the IR is unchanged.
  │   - Desired future no-mutation cases are captured as xfail/expected-future markers (or deferred to K2.3), so this item's gate is green without the K2 change in place.
  │   - Tests characterize false curated raw diffs from sorted key JSON.
  │   - Tests cover before and after token counting when IR is equal.
  │   - Tests expose Anthropic message, text, tool result, tool use, image, and sampling extra preservation gaps.
  │   Verification Gate: Run targeted API pytest with `uv run --project api` or from `api` with `PYTHONPATH=src`.
  │   Size: M | Deps: none | Labels: backend, adapters, tests
  │
  ├── Sub-issue K2.2: Define shared request mutation decision
  │   Description: Introduce one shared decision point that classifies a request as unchanged or mutated using structural IR equality. This decision must be usable by live handlers, breakpoint release, storage, and token counting.
  │   Acceptance:
  │   - The decision uses `curated_ir == ir` and does not compare serialized bytes.
  │   - The helper clearly separates skip mutation, serialize curated IR, and explicit raw release payload cases.
  │   - Both HTTP and WebSocket call sites can consume the same decision without provider specific branching.
  │   Verification Gate: Unit tests for equal IR, changed IR, and explicit release payload cases.
  │   Size: M | Deps: K2.1 | Labels: backend, pipeline, adapters
  │
  ├── Sub-issue K2.3: Skip live request writes when IR is unchanged
  │   Description: Apply the shared decision to the live request handlers and breakpoint release so unchanged requests keep the original body or frame managed by mitmproxy.
  │   Acceptance:
  │   - Unchanged HTTP request bodies are not mutated on the live path.
  │   - Unchanged Codex WebSocket request frames are not mutated on the live path.
  │   - Breakpoint release preserves explicit release payloads and serializes only real IR mutations.
  │   - Mutated requests still use the provider adapter serializer.
  │   Verification Gate: Target addon handler and pause session tests for unchanged and mutated paths.
  │   Size: M | Deps: K2.2 | Labels: backend, mitmproxy, pipeline
  │
  ├── Sub-issue K2.4: Gate persisted curated request artifacts structurally
  │   Description: Update persistence so curated request artifacts are omitted when original and curated IR are equal, even if adapter serialization would reorder keys or normalize JSON.
  │   Acceptance:
  │   - Curated request persistence uses the shared structural equality decision rather than serialized-byte comparison.
  │   - Storage records curated raw only when there is a semantic mutation.
  │   - Existing persisted exchange shape remains compatible for genuinely edited requests.
  │   Verification Gate: Exchange recorder tests for unchanged canonicalization, edited payloads, and provider extras.
  │   Size: S | Deps: K2.2 | Labels: backend, storage, capture
  │
  ├── Sub-issue K2.5: Align token counting with original request semantics
  │   Description: Use original request payload semantics for before counts and avoid after counts when IR is unchanged. Preserve existing Anthropic header filtering and sampling field stripping.
  │   Acceptance:
  │   - Before counts do not require lossy IR serialization when original request data is available.
  │   - After counts are omitted or marked unchanged when `curated_ir == ir`.
  │   - Mutated requests still count the curated request.
  │   - Header forwarding remains allow listed and safe.
  │   Verification Gate: Counting and exchange stats tests for unchanged, edited, and missing raw payload cases.
  │   Size: M | Deps: K2.2 | Labels: backend, counting, adapters
  │
  ├── Sub-issue K2.6: Add Anthropic structural raw overlays for edited paths
  │   Description: Lift the Codex preserved raw overlay pattern into the Anthropic adapter at message and content block levels so edited known fields can be merged back into raw objects without dropping unknown siblings.
  │   Acceptance:
  │   - Unknown message object fields survive after editing a known message field.
  │   - Unknown content block fields survive after editing known text, image, tool use, or tool result fields.
  │   - Unknown top level, system, tool, and thinking fields continue to survive.
  │   (The cross-path check "overlay does not alter unedited requests when the skip-mutation path applies" is an integration proof in K2.8, keeping this item edited-path-only and parallel to the skip work.)
  │   Verification Gate: Anthropic adapter tests with nested unknown fields and edited known fields.
  │   Size: L | Deps: K2.1 | Labels: backend, adapters, provider-api
  │
  ├── Sub-issue K2.7: Wire explicit provider overflow for surfaced structures
  │   Description: Add or repair explicit `provider_data` capture for modeled structures where the UI, diffs, rules, or adapters need structured visibility. Use raw overlays for fidelity and provider data for intentional surfaced metadata.
  │   Acceptance:
  │   - Message, text, image, tool use, tool result, and sampling extras are either preserved by overlay or captured in provider data where surfaced.
  │   - Existing `ToolResultBlock.provider_data` is populated and restored where applicable.
  │   - New provider data fields do not create cross provider ambiguity in the IR.
  │   Verification Gate: IR, Anthropic adapter, and Codex adapter tests for provider data round trips.
  │   Size: M | Deps: K2.6 | Labels: backend, ir, adapters
  │
  ├── Sub-issue K2.8: Prove forward compatibility gates
  │   Description: Run the targeted provider compatibility suite and the root repo gate. Document the no mutation policy for future adapter work.
  │   Acceptance:
  │   - Targeted API tests pass for adapters, request pipeline, addon handlers, exchange recorder, counting, and pause session.
  │   - Integration proof: the Anthropic edited-path overlay (K2.6) does not alter unedited requests when the K2.3 skip-mutation path applies.
  │   - Root `just test` passes.
  │   - Documentation says unchanged live requests are left untouched and edited requests must preserve unknown provider fields.
  │   Verification Gate: Root `just test`; include command output in closeout.
  │   Size: S | Deps: K2.3, K2.4, K2.5, K2.6, K2.7 | Labels: backend, tests, docs

---

### Parent Issue 3: K3: Make harness descriptors load bearing and onboard new CLIs

Description: Convert `HarnessDescriptor` from informational metadata into launch behaviour input, preserve the `/api/meta` and frontend harness contract, then add OpenCode before Gemini. Use staged migration to avoid Codex launch regressions.

Acceptance Criteria:

- Existing Claude and Codex command behaviour remains stable through descriptor driven launch.
- Descriptor fields drive proxy mode, trust requirements, shell environment policy, pass through policy, and capabilities where they affect launch.
- `/api/meta` and frontend `harnesses` typing remain compatible or are migrated deliberately.
- Layout and registry changes respect the import DAG.
- OpenCode is added before Gemini if it truly reuses Anthropic Messages.
- Gemini adds a new HTTP adapter for `:generateContent`.
- Root `just test` passes before closeout.

  ├── Sub-issue K3.1: Decide onboarding scope and layout contract
  │   Description: Close v1 scope before code changes. Decide desktop launch inclusion, OpenCode provider identity, and whether v1 uses horizontal modules with registries or strict `providers/<name>/` subpackages.
  │   Acceptance:
  │   - The decision states whether desktop launcher support is in v1 or deferred.
  │   - The decision states how OpenCode appears in provider identity while reusing Anthropic wire format.
  │   - The decision recommends staged horizontal layout for v1, or documents strict vertical package rules if `providers/<name>/` is selected.
  │   - ALP-2434 scope exclusion is recorded so onboarding is tracked as net new work.
  │   Verification Gate: Written decision reviewed against Q3 verification and `api/CLAUDE.md` import DAG.
  │   Size: S | Deps: none | Labels: architecture, cli, adapters
  │
  ├── Sub-issue K3.2: Characterize current launch behaviour
  │   Description: Add tests that freeze Claude and Codex launch behaviour before refactoring. Cover `--print-command`, reverse versus explicit proxy mode, Codex CA bootstrap, shell environment excludes, pass through hints, and proxy only hints.
  │   Acceptance:
  │   - Claude print command and reverse proxy env behaviour are covered.
  │   - Codex print command, CA material, explicit proxy env, shell policy, and fallback flags are covered.
  │   - Desktop supported client tests are added only if K3.1 includes desktop in v1.
  │   - Tests fail if descriptor driven launch drops a current behaviour.
  │   Verification Gate: CLI launch tests under `api/src/transport_matters/cli`.
  │   Size: M | Deps: K3.1 | Labels: backend, cli, tests
  │
  ├── Sub-issue K3.3: Make descriptors drive launch in place
  │   Description: Update existing Claude and Codex command paths to consume `HarnessDescriptor` data for launch decisions while keeping command names, options, and operator surfaces stable.
  │   Acceptance:
  │   - Launch code reads descriptor proxy mode, trust requirement, shell environment policy, pass through policy, and capabilities where applicable.
  │   - Claude and Codex continue to produce equivalent commands and env after the refactor.
  │   - Descriptor registry remains the single source for launch metadata.
  │   Verification Gate: K3.2 characterization tests plus harness descriptor tests.
  │   Size: L | Deps: K3.2 | Labels: backend, cli, harnesses
  │
  ├── Sub-issue K3.4: Preserve frontend harness metadata contract
  │   Description: Treat `/api/meta` and the frontend `harnesses` payload as a contract. Update API models and frontend types only as needed to reflect load bearing descriptor fields.
  │   Acceptance:
  │   - `/api/meta` still returns all harness descriptors expected by the frontend.
  │   - Frontend API types compile after any descriptor field changes.
  │   - No frontend behaviour silently changes based on launch only descriptor fields.
  │   Verification Gate: API meta tests plus `cd www && just test` if frontend types change.
  │   Size: M | Deps: K3.3 | Labels: backend, frontend, api
  │
  ├── Sub-issue K3.5: Extract generic launch after parity
  │   Description: Consolidate duplicated launch behaviour into a generic launch path parameterized by descriptors and stable command specific options. Do this only after K3.3 proves parity in place.
  │   Acceptance:
  │   - Shared launch plumbing handles reverse and explicit proxy modes without Codex named branches leaking into generic code.
  │   - Trust bootstrap and shell policy remain provider specific inputs, not copied logic.
  │   - Existing Claude and Codex commands keep their public names and options.
  │   Verification Gate: Full CLI test slice for launch, validation, pass through, print command, child process, and Codex specific behaviour.
  │   Size: L | Deps: K3.3 | Labels: backend, cli, refactor
  │
  ├── Sub-issue K3.6: Introduce registry based module boundaries
  │   Description: Reduce central edit points through descriptor, adapter, and CLI harness registries. Use the K3.1 layout decision and enforce import boundaries so adapter code cannot import launch code and provider package roots do not create cycles.
  │   Acceptance:
  │   - New harnesses can register descriptor and launch behaviour without editing multiple unrelated central files.
  │   - New adapters can register wire detection and serialization without violating the import DAG.
  │   - Package root files remain metadata only if vertical provider packages are used.
  │   - `fmm validate` passes after the refactor.
  │   Verification Gate: Registry tests, `fmm validate`, CLI help tests, and adapter registry tests.
  │   Size: L | Deps: K3.4, K3.5 | Labels: backend, cli, adapters, architecture
  │
  ├── Sub-issue K3.7: Onboard OpenCode with Anthropic wire reuse
  │   Description: Add OpenCode as the first new CLI after descriptor driven launch and registry boundaries are in place. Scaffolding (descriptor, CLI entry, help, metadata, launch policy) depends only on K3.6. Reuse Anthropic Messages if OpenCode truly speaks `/v1/messages`; otherwise produce a follow up adapter spec before implementation.
  │   Acceptance:
  │   - OpenCode has a descriptor, CLI entry point, help text, and launch policy through the registry path.
  │   - OpenCode request capture uses Anthropic wire handling or an explicit wrapper that preserves a provider identity distinct from "anthropic".
  │   - API metadata exposes OpenCode as a distinct harness.
  │   - Desktop support follows the K3.1 scope decision; if desktop is in v1, touch points include `desktop/src/backendProcess.ts:5-9`, `desktop/src/backendProcess.ts:71-79`, and `desktop/src/main.ts:238-247`.
  │   - Capture-acceptance only is gated on K2.8 so OpenCode inherits the no-mutation/overflow policy; scaffolding is not gated on K2.8.
  │   Verification Gate: CLI help, print command, harness metadata, and capture smoke tests for OpenCode.
  │   Size: M | Deps: K3.6 (scaffolding); K2.8 (capture acceptance only) | Labels: backend, cli, provider-onboarding
  │
  ├── Sub-issue K3.8: Build the Gemini wire adapter
  │   Description: Implement the new HTTP adapter for Gemini `:generateContent` and its IR translation, without touching Codex WebSocket paths. Adapter and protocol only; no CLI or launch surface in this slice.
  │   Acceptance:
  │   - Gemini adapter matches only Gemini HTTP generate-content traffic.
  │   - Gemini request and response translation round trips through the canonical IR for supported fields.
  │   - Unknown Gemini fields follow the K2 no-mutation and edited-path preservation policies.
  │   Verification Gate: Gemini adapter unit tests; `cd api && just test` for backend-targeted closeout.
  │   Size: L | Deps: K3.6 | Labels: backend, adapters, provider-onboarding
  │
  ├── Sub-issue K3.9: Onboard the Gemini CLI harness
  │   Description: Add the Gemini descriptor, CLI entry point, help text, launch policy, and metadata through the registry path, wired to the K3.8 adapter.
  │   Acceptance:
  │   - Gemini has a descriptor, CLI entry point, help text, and metadata through the registry path.
  │   - Desktop support follows the K3.1 scope decision; if desktop is in v1, touch points include `desktop/src/backendProcess.ts:5-9`, `desktop/src/backendProcess.ts:71-79`, and `desktop/src/main.ts:238-247`.
  │   - Capture-acceptance only is gated on K2.8 so Gemini inherits the no-mutation/overflow policy; scaffolding is not gated on K2.8.
  │   Verification Gate: CLI launch tests, metadata tests, targeted capture smoke test, then root `just test`.
  │   Size: M | Deps: K3.8 (adapter); K2.8 (capture acceptance only) | Labels: backend, cli, provider-onboarding
  │
  ├── Sub-issue K3.10: Document new CLI onboarding playbook
  │   Description: Document how to add a reuse only CLI and a new protocol CLI under the chosen layout. Include import DAG rules, descriptor fields, launch policy, frontend metadata, and test expectations.
  │   Acceptance:
  │   - The playbook explains reuse only onboarding with OpenCode as the example.
  │   - The playbook explains new protocol onboarding with Gemini as the example.
  │   - The playbook calls out desktop scope and frontend metadata considerations.
  │   - The playbook states final verification commands, including that root `just test` is full-stack.
  │   Verification Gate: Documentation review plus link from the relevant developer docs or architecture notes.
  │   Size: S | Deps: K3.9 | Labels: docs, architecture, onboarding

---

### Cross Keystone Dependency Graph

Hard dependencies:

- K1 has no hard dependency on K2 or K3.
- K2 has no hard dependency on K1 or K3.
- K3 descriptor refactor has no hard dependency on K1.
- K3 onboarding work depends on K3 descriptor and registry work.
- K3.7 and K3.9 CAPTURE acceptance depend on K2.8 so new providers inherit the no-mutation and provider-overflow policy; their scaffolding depends only on K3.6 / K3.8 and does not wait on K2.8.

Internal chains:

```text
K1.1 -> K1.2 -> K1.3 -> K1.4 -> {K1.5, K1.6} -> K1.7

K2.1 -> K2.2 -> K2.3 -> K2.8
          |       -> K2.4 -> K2.8
          |       -> K2.5 -> K2.8
K2.1 -> K2.6 -> K2.7 -> K2.8
(K2.6/K2.7 are edited-path-only and parallel to the K2.2 skip-decision chain)

K3.1 -> K3.2 -> K3.3 -> {K3.4, K3.5} -> K3.6 -> K3.7
                                        K3.6 -> K3.8 -> K3.9 -> K3.10
(K3.7 and K3.9 capture acceptance additionally gated by K2.8)
```

Parallelizable streams:

- K2.1 through K2.5 can run while K1.1 and K3.1 are being decided.
- K1 implementation can run in parallel with K3 characterization and descriptor refactor because storage layout and launch descriptor work touch different seams.
- K1.6 (per-instance API/UI) may run in parallel with K1.5 (instances/paths CLI); both are gated by K1.4 and touch different seams.
- K2.6 and K2.7 (edited-path overlay and overflow) are orthogonal to the skip-mutation decision and can run after K2.1 in parallel with the K2.2 through K2.5 chain; the cross-path integration check lives in K2.8.
- K3.4 (frontend contract) and K3.5 (generic launch) run in parallel off K3.3 and rejoin at K3.6.
- K3.7 OpenCode and K3.8/K3.9 Gemini should not run in parallel unless the registry and descriptor refactor (through K3.6) are already stable, because both consume the same onboarding surface.

### Recommended Global Sequencing

1. Start K2 first. The unchanged request no mutation path is the cheapest high value compatibility win and reduces risk for every future provider.
2. In parallel, complete K1.1 and K3.1 decision specs. These remove ambiguity before implementation starts.
3. Implement K1 and K3 descriptor refactor in parallel if capacity exists. K1 unlocks multi instance operation, while K3 prepares the onboarding surface.
4. Finish K2.8 before the CAPTURE acceptance of OpenCode or Gemini so new providers inherit the provider compatibility policy; their descriptor/CLI/help/metadata scaffolding can proceed once K3.6 lands.
5. Add OpenCode before Gemini. OpenCode should be a reuse only harness if its `/v1/messages` contract holds, while Gemini introduces a new wire adapter.
6. Add Gemini last because it validates the new adapter path and has the highest provider specific uncertainty.

If execution is serial, use this order:

```text
K2 -> K1 decision and implementation -> K3 descriptor refactor -> OpenCode -> Gemini
```

Rationale: K2 is low blast radius and protects all traffic. K1 is independent and concrete once its three decisions are closed. K3 has the longest critical path and must precede onboarding, but onboarding itself is net new work outside ALP-2434.

### Critical Path

The full program critical path is K3:

```text
K3.1 -> K3.2 -> K3.3 -> K3.5 -> K3.6 -> K3.8 -> K3.9 -> K3.10
```

Reason: The complete scope includes Gemini and OpenCode onboarding, and both require descriptor driven launch plus registry boundaries first. K3.4 (frontend contract) runs in parallel off K3.3 and rejoins at K3.6; K3.7 OpenCode runs off K3.6 before or alongside the Gemini slices. K2.8 is a quality gate before the capture acceptance of K3.7 and K3.9, but K2 is shorter and can complete before K3 reaches onboarding. K1 is independent unless the product chooses to block all new provider work on multi instance support.

### Verification Strategy

Per item:

- Use the targeted gate named on each sub-issue.
- Prefer `uv run --project api ...` for API targeted tests from the repo root.
- Use `cd api && PYTHONPATH=src uv run pytest ...` if root pytest import paths fail.
- Note: root `just test` is FULL-STACK — it runs `cd desktop && just test`, `cd www && just test`, and `cd api && just test`. Use `cd api && just test` for backend-targeted gates; reserve root `just test` for parent and program closeout.
- Use `fmm validate` after structural moves, registry refactors, or import boundary changes.

Per parent:

- K1 closeout: targeted CLI, lock, storage, meta, exchanges, and multi instance tests, then root `just test`.
- K2 closeout: targeted adapter, addon handler, pause session, exchange recorder, counting, and request pipeline tests, then root `just test`.
- K3 closeout: targeted CLI, harness, adapter registry, API meta, and frontend type tests if touched, then root `just test` (which runs the www and desktop suites unconditionally).

Program closeout:

- `fmm validate`
- `just test`
- Manual smoke or scripted smoke for two same CWD instances.
- Manual smoke or scripted smoke for OpenCode and Gemini capture paths after onboarding.

### Risks

- K1 explicit `--storage-dir` sharing could allow unsafe shared index writes if the contract is too permissive.
- K1 aggregated UI is a separate architecture because storage, breakpoint, broadcast, settings, and track state are process local.
- K2 byte reinjection would be unsafe because captured `raw` is not guaranteed byte faithful. The safe path is to skip mutation.
- K2 Anthropic edited path overlays can become complex. Keep overlays local to adapter serialization and prove unknown sibling preservation with tests.
- K2 token counting may need a policy choice when original raw is unavailable. Prefer conservative omission over misleading normalized counts.
- K3 descriptor launch refactor can regress Codex trust material or proxy behaviour. Characterization tests must land first.
- K3 vertical `providers/<name>/` packaging can violate the import DAG if package roots import both adapter and CLI launch code.
- K3 desktop support can scope creep. Decide v1 desktop support before adding OpenCode or Gemini.
- OpenCode provider identity can be conflated with Anthropic if adapter metadata is not separated from harness identity.

### Deferred Work

- Aggregated multi run UI and coordinator process.
- Desktop launch support if K3.1 scopes it out.
- WebSocket provider generalization beyond Codex.
- Physical provider package relocation if staged horizontal registries are sufficient for v1.
