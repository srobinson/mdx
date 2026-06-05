---
title: Transport Matters overlay settings scout
type: scout
tags: [transport-matters, overlay, settings, reuse-map]
summary: Mode 1 reuse map for durable, scoped overlay policy reached through Settings; all citations pinned to commit d3aa151b
status: active
source: fable5-scout
confidence: high
created: 2026-08-03
---

# Overlay settings scout (Mode 1)

All citations are `file:symbol` at commit `d3aa151b` (`git show d3aa151b:<path>`).
The working tree was moving under a concurrent builder; nothing below reads it.
Prior art consumed: `transport-matters-firstcontact--synthesis.md`; its verified
marks were re-checked where load-bearing.

## Reuse Map

### 1. Scope identity: owners and precedence

| Level | Owning symbol | Writer / reader |
| --- | --- | --- |
| Owner | `packages/space/src/domain/actingContext.ts:resolveContextCanvas` (receipt `ownerId`); `packages/space/src/adapters/PostgresSpaceContextRepository.ts:findOwnedCanvas` | Space context writes owner-scoped rows; controlplane reads receipts |
| Space / Worktree / Canvas | branded ids in `packages/contract/src/space` (`asSpaceId`, `asWorktreeId`, `asCanvasId`); capture-plane mirror `api/src/transport_matters/space/models.py` (`SpaceId`, `WorktreeId` over `_UuidId`) | Product plane mints; capture plane carries |
| Workspace (path identity) | `workspace.py:WorkspaceId` (`workspace_id`, canonical path slug+hash) | Capture plane, launch time |
| Harness | opaque string; `harnesses:as_harness_id` | Set at launch, carried on binding |
| Model / effort | `harnesses/compatibility.py:match_release`; resolver effort intersection (per `docs/ARCHITECTURE.md` Harness compatibility) | Compatibility layer judges, never stores policy |
| Run | `run_id` on `shared_proxy/binding.py:ProxyRunBinding`; minted through `controlplane/launch_service.py` (`candidate_key`, `_candidate_dispatch_id`) | Launch service writes, capture plane reads |
| Track | `track_manager.py:classify_request` → `TrackAssignment.track_id` | Addon process, per request |

Identity transport to the capture plane: `session/affinity.py:SessionAffinityStamp`
travels under `SESSION_AFFINITY_LAUNCH_FIELD` inside `launch_fields`;
`shared_proxy/binding.py:bind_trusted_affinity` projects it onto the binding.
Precedence rule that exists today: the server-installed stamp wins over
caller-supplied binding fields. Writer is the server at launch resolution
(`session/affinity.py:build_session_affinity_stamp`); partial stamps are
rejected (`validate_affinity_group`).

**Policy precedence across levels: none found.** Searches:
`git grep -rn precedence d3aa151b` (hits are request-purpose metadata, config
resolution, wire field ordering only); override scope walk read first-hand.
What exists instead:

- Override lookup is exact-scope only. `overrides/state.py:normalize_scope`
  keys `(run_id, track_id)` with `LEGACY_SCOPE_ID` sentinel;
  `OverrideStore.get_all` reads one dict, no ancestor walk. Consequence:
  a run-scope override is invisible to a tracked request, because
  `request_pipeline.py:run_pipeline` selects `(run, track)` when a track is
  assigned. The MECH precedence chain is entirely new work; every enumerated
  level has an identity owner, none has a policy resolver.
- The only nearest-scope-wins logic anywhere:
  `packages/space/src/domain/actingContext.ts:resolveWorkdirCandidate`
  (deepest canonical path match).

### 2. Product plane → capture plane policy carrier

**The carrier exists and already carries override snapshots.**

- Message: `shared_proxy/models.py:SetOverridesRequest` with
  `OverrideSnapshotPayload` (`enabled` + flat `tuple[Override, ...]`), scoped by
  `OverrideScopePayload` (run, track). Ack carries `overridesGeneration`.
- Channel: `shared_proxy/control.py:SharedProxyControlClient` /
  `SharedProxyControlServer` (UDS, newline-framed JSON, 1 MiB limit).
- Sender: `shared_proxy/manager.py:SharedProxyManager.set_overrides`, which
  mirrors state in `_overrides` and replays it after subprocess restart via
  `_rehydrate_locked`. Receiver: `shared_proxy/subprocess.py:set_overrides`
  installing into the subprocess-local `overrides/state.py:get_store`.
- Current trigger: `api/v1/overrides.py:_sync_shared_overrides` after every
  route mutation. Pinned by `api/v1/test_overrides_shared_proxy.py`.

Verdict: a compiled snapshot is exactly the shape this channel already moves.
The compile step (durable scoped manifests → one flat `Override` list per
`(run, track)`) runs before the push; the channel, the addon, and the store
never need to learn owner, space, or worktree.

Gaps to close, not rediscover:

- `RegisterListenerRequest` carries no overrides. Registration and first
  snapshot are two messages, so a freshly registered listener can serve traffic
  before policy lands. Either extend `SharedProxyBindingPayload` or order the
  snapshot push before the run is released to traffic.
- The per-run sidecar path (`captured/run.py:prepare_captured_run`,
  `WEB_RUNTIME_EMBEDDED`) hosts API and store in one process, no UDS hop. A
  resolve-at-registration seam must cover both process shapes.

Precedent for a durable, launch-resolved, server-owned setting that never
touches the hot path: `harnesses/enablement_store.py:harness_enabled_sync`
behind `harnesses/enablement_service.py:gate_harness_enablement`, resolved at
launch preparation against the session store. The overlay policy store should
follow this shape. The product-plane resolution point already ferries identity
(`launch_fields` with the affinity stamp) through
`controlplane/launch_service.py` and the runtime port
(`packages/runtime/src/ports.ts:captureHealth`, `launchFields`).

### 3. Frontend settings surfaces

- **The settings surface exists**: the Command Center `settings` domain.
  `www/packages/canvas/src/launcher/commandRows.ts:buildSettingsRows` (theme,
  bypass permissions, control plane grant, canvas gesture), registered in
  `commandRows.ts:BASE_DOMAINS` with subtitle "homes · skills · defaults" and
  the ⌘, accelerator; `commandTypes.ts:GROUP_SETTINGS`; keybinding
  `keybindings/registry.ts:launcher.openSettings`. Harness settings already
  render in this scope (`CommandCenter.spaces.test.tsx`). This is the home for
  overlay settings rows, and it honors API-first only if rows call gateway
  APIs rather than client stores.
- First-run already anticipates the settings-first framing in source:
  `www/packages/canvas/src/firstrun/FirstRunScreen.tsx` comments that harness
  cards "stay for Settings / past-the-gate use" (`firstrun/harnessCards.ts`).
- Existing settings persistence is client-local zustand:
  `www/packages/canvas/src/model/capturedRunStore.ts` (`bypassPermissions`),
  `stores/themeStore.ts`. **No server-side user-settings store exists in the
  product plane.** Searches: `bypassPermissions` across `www/packages`;
  `packages/space/src/adapters/postgresSchema.ts` holds only space, worktree,
  canvas tables.
- Wire-shaped editing UI to reuse: Inspector
  `components/editor/BreakpointEditor.tsx` family,
  `components/routes/OverlaysView.tsx` (naming and scope curation), and the TS
  mirror `www/packages/core/src/types/overrides.ts` pinned to the Python model
  by `test_type_mirrors.py`.

### 4. Second writers (first check)

Override desired-state has one writer surface today: `api/v1/overrides.py`
(patch, delete, toggle). `api/v1/breakpoint_routes.py` only reads
(`get_all`, `is_enabled`). State resides in three places with a clear
precedence: API-process `overrides/state.py:get_store` is authoritative,
`SharedProxyManager._overrides` is the restart-replay mirror, the subprocess
store is the applied copy.

**The violation already in the tree**:
`www/packages/inspector/src/stores/overlaysStore.ts`. Durable, named, scoped
overlay bundles persisted in **browser localStorage** (zustand persist), born
from `BreakpointEditor.tsx:createDraft` ("SAVE AS OVERLAY"), scope vocabulary
`"shared" | {kind: "project", cwd}`, explicitly shipped without an apply
pipeline (`OverlaysView.tsx` header comment). This is a second durable
representation of overlay policy beside the session `OverrideStore`, and it is:

- client-side, where the director agent can never read it (violates API-first);
- carrying a cwd-string scope that duplicates identity owned by
  `workspace.py:WorkspaceId` (canonical path) and by Worktree ids in the space
  context, with no precedence rule against either.

The build must supersede this store with the product-plane manifest store:
migrate or delete, never extend. Related hazards:

- Vocabulary collision: "overlay" already means runtime-home overlay in the
  capture plane (`cli/home_overlay.py`). The settings feature must own the
  word product-wide or pick its manifest vocabulary deliberately.
- `capturedRunStore.bypassPermissions` is a launch-behavior setting persisted
  client-side; if Settings becomes server-owned it is the next migration
  candidate. Do not create a server twin while the client copy still decides
  launches.

### 5. overrides/ quality map

Sound kernel, confirmed as the synthesis claimed:
`overrides/__init__.py:apply_overrides` dispatches nine kinds in fixed
`_PRIORITY` order, adjusts indices against the original IR, and is wrapped
never-raise at `request_pipeline.py:run_pipeline` (fail-open, forward
unmodified). Nothing found dead: all nine ops are dispatched;
`codex_has_tool_result_only_turn` is exported and consumed.

Wrong-shaped for durable policy:

- `state.py:LEGACY_SCOPE_ID` / `root_scope` sentinel aliasing, and the
  unscoped `OverrideStore.enabled` property shim.
- Positional selectors: `targets.py:system_target` and
  `message_block_target` are index-based and valid only against one request's
  original IR; `adjust_system_index` / `adjust_blk_index` preserve
  intra-request consistency only. No shape preconditions exist. Only
  `tool:{name}`, `toolresult:{id}`, `sampling:{field}`,
  `provider_extras:{key}` are durable-shaped selectors today.
- `audit.py:OverrideAuditEntry` records `chars_delta` only: no manifest or
  revision identity, no mismatch reason. It cannot back drift verdicts or
  token claims (synthesis §4.5 stands).
- `Override.value` overloads a scalar with JSON-in-string payloads for
  sampling and provider extras; fine at the wire, not a format to inherit
  into durable manifests by accident.
- Behavior to surface, never silently keep:
  `ops_messages.py:sanitize_curated_messages` cascades orphan removal when one
  side of a tool pair is removed; any settings preview must show it.
- Duplication note: `api/v1/overrides.py:_snapshot_scope` / `_restore_scope`
  hand-roll transaction semantics the store lacks. If the store gains a
  compiled-snapshot install, give it one atomic replace instead of spreading
  the rollback idiom.

## Quality Map (cross-cutting)

- Two process shapes for the same store (embedded web runtime vs shared proxy
  subprocess) mean every policy-application change must be proven on both;
  only the shared path has a sync test today
  (`api/v1/test_overrides_shared_proxy.py`).
- Registration-before-snapshot window on the shared channel (above).
- Scope model fragmentation: four scope vocabularies exist with no bridge —
  override `(run, track)`, overlaysStore `shared|project:cwd`, capture
  `WorkspaceId`, product `owner/space/worktree/canvas`. The manifest store's
  scope keys should be the branded space-context ids plus harness string, and
  everything else derives.

## Plan (reuse sequencing, not a design)

1. Product-plane manifest store beside the space context (Postgres,
   owner-scoped, shaped like `PostgresSpaceContextRepository`), scope keys
   from `@tm/contract/space` ids plus harness string. Supersedes
   `overlaysStore` (migrate or delete, owner decision 1).
2. Resolve and compile at the launch seam (`launch_service` /
   capture registration): manifests → flat `OverrideSnapshotPayload` per
   `(run, track)`, pushed over `SetOverridesRequest` verbatim; close the
   register-before-snapshot window; cover the embedded-runtime shape.
3. Settings rows in the Command Center `settings` scope calling gateway APIs
   (API-first; the director reads the same control plane). Inspector
   `BreakpointEditor` keeps run-scope authoring; the SAVE AS OVERLAY promotion
   re-targets the manifest store.
4. Audit gains manifest identity and mismatch reasons only when drift verdicts
   arrive; no token claims from the chars-based audit meanwhile.

## Open decisions for the owner

1. `overlaysStore` disposition: migrate existing localStorage overlays into
   the manifest store, or delete outright.
2. Vocabulary: who owns the word "overlay" given `cli/home_overlay.py`
   (runtime-home overlays) already uses it in the capture plane.
3. v1 precedence chain: full MECH chain, or only the levels with existing
   identity owners (owner, space, worktree, harness, run); model and effort
   scoping would couple policy to the compatibility layer.
4. Snapshot delivery: extend `SharedProxyBindingPayload` to carry the compiled
   snapshot at registration, or keep a second control message strictly ordered
   before traffic release.
