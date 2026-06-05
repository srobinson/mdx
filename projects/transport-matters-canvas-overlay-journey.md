# Canvas automatic overlay journey and breakpoint coupling

- **Tree:** `c03edbd96e30d5c2917994897686bd4223f40065` (`c03edbd9`) branch `scout/canvas-overlay-boundary`
- **Date:** 2026-08-07
- **Revision:** phase-1 correction round (Opus reconciliation) plus delta-review fix. Corrects process topology for Canvas; re-scopes shared-proxy defects; confirms `meta.cwd` valid for per-run embedded Canvas project scope.
- **Owner binding:** CM `019fdb4f-abf7-7a12-a3be-bbda623caa68` — Canvas overlays automatic and non-blocking; no Arm, Pause, Forward, Pass Through, Drop, timeout, paused-flow state, or Inspector breakpoint state in Canvas; Inspector breakpoint remains separate and must not be deleted
- **Inputs:** live tree above; `docs/process/WARROOM.md`; `docs/ARCHITECTURE.md`; CM entry; whole-repo source sweep; Opus reconciliation of scout findings
- **Live product:** not running (channel ports 8787/8797/8807 and desktop-dev 18787/18788/15173 closed). Visible UI claims below are **source-only** (and tests), not a live screen walk. That limit is preserved.
- **Evidence tags:** `[measured-source]`, `[measured-absent]`, `[inference]`, `[unknown]`, `[corrected]`

---

## 0. Correction log (this revision)

| Prior claim in this artifact | Corrected fact |
|------------------------------|----------------|
| Canvas runs share shared mitmdump (K=1); Inspector arm on that process can pause Canvas traffic | **Canvas runs today use per-run mitmdump with embedded API**, not shared mitmdump. Topology: `CaptureLeaseRegistry.prepare_capture` → `prepare_captured_run` / product-plane `RunManager` → per-run addon `addon_runtime.load_runtime` (load_capture_runtime) + `web_runtime.start_web_runtime` embedding `create_app` on the run `web_port`. `[corrected]` |
| Enforcement gap: process-global arm + shared proxy ⇒ Canvas can pause | **No-pause on Canvas is UI/call-site absence:** nothing on the Canvas path calls **that run's** `POST /api/breakpoint/arm`. Arm state is still per-process `_mode` inside the run's own mitmdump/API process, but no Canvas client targets it. Pipeline apply remains independent and non-blocking either way. `[corrected]` |
| Scopeless DELETE / shared-proxy sync issues as Canvas automatic-path defects | **Re-scoped to shared-proxy-bound runs only.** Current Canvas journey is embedded (same process as store + pipeline); shared-proxy dual-store defects are out of the live Canvas journey unless topology changes. `[corrected]` |
| Shared-proxy mode inference as Canvas-relevant | **Outside the current Canvas journey.** Marked as adjacent shared-proxy hygiene, not Canvas path. `[corrected]` |
| Reject `meta.cwd` for embedded Canvas project scoping | **`meta.cwd` is valid for per-run embedded Canvas.** The captured-run spawn sets env CWD from the run's `working_dir` (`launch/environment.py` builder, flowed from the captured invocation) and `api/v1/meta.py:get_meta` prefers `settings.cwd`, so the embedded API reports the run worktree. Not a current Canvas defect. `[corrected]` |

---

## 1. Vocabulary (do not collapse)

Three different "overlay" words ship in this tree:

| Sense | Owner | Product meaning |
|-------|-------|-----------------|
| **Named Overlay** | Inspector `overlaysStore` / `OverlaysView` | Saved, named, scoped bundle of `Override[]` intended as a reusable transform. **Apply-at-intercept is not wired yet.** |
| **Standing override + pipeline** | Capture plane `OverrideStore` + `request_pipeline.run_pipeline` | Live process-scoped rules applied on every request. **This is the automatic, non-blocking rewrite path that exists today.** |
| **Canvas UI overlay** | `CanvasDragSessionOverlay`, `LayoutCanvas.overlay` slot, dock screen overlay | Visual chrome (DnD target labels, pane dock). **Unrelated to request transforms.** |

Owner decision language ("automatic Canvas overlay", "apply selected overlay", "reveal original/curated/audit/savings") maps to **Named Overlay + pipeline + Canvas evidence**. Today only the middle piece fully runs; Named Overlay is curation-only; Canvas evidence is partial.

**Homonyms excluded:** runtime home overlay (`cli/home_overlay.py`), activity "stalled" health overlay (`packages/contract/src/activity/wire.ts`), Electron titleBarOverlay, fullscreen UI overlays.

---

## 2. Canvas process topology (authoritative for this journey)

```
Canvas ensureRun / createCapturedRun
  → product Runtime RunManager
  → Capture RPC prepare
  → CaptureLeaseRegistry.prepare_capture
  → prepare_captured_run
  → per-run mitmdump process
       addon: addon_runtime.load_runtime / load_capture_runtime
       embedded API (Settings.web_runtime == "embedded" only on this path):
         web_runtime.start_web_runtime → create_app on run web_port
         mounts /api/overrides, /api/breakpoint, exchanges, …
       one OverrideStore singleton and one breakpoint._mode in THIS process
```

**Implications:**

1. Override store and pipeline for a Canvas run live **inside that run's process**, not in a channel-global shared mitmdump.
2. Arming requires a client to hit **that process's** `/api/breakpoint/arm`. Canvas does not. Detached Inspector-on-channel-origin and per-run `web_port` are different origins; Canvas does not arm either.
3. Shared-proxy manager / dual-store sync are a **different topology**. Relevant when a run is registered in `SharedProxyManager.by_run_id`. **Outside the current Canvas journey.** `[corrected]`

---

## 3. Automatic journey as implemented

### 3.1 End-to-end path that rewrites wire (non-blocking)

```
request hits this run's mitmproxy addon
  → parse IR (adapter inbound)
  → request_pipeline.run_pipeline(ir, flow_id, run_id)
       → OverrideStore.get_all(scope) when enabled
       → overrides.apply_overrides → curated_ir + OverrideAudit
  → capture_request_flow_state(original + curated + audit)
  → if NOT (armed AND not model-skip):
       rewrite body via outbound_request_if_changed(adapter, original, curated)
       persist provisional exchange outbound=true
       forward without waiting  [non-blocking]
  → else:
       handle_breakpoint / handle_websocket_breakpoint  [Inspector pause path only if armed]
```

**Source mechanism:**

- `request_pipeline.py:run_pipeline` — never raises; on failure logs and forwards unmodified
- `overrides/__init__.py:apply_overrides` — priority-ordered IR transforms + audit
- `overrides/state.py:OverrideStore` — process memory, scoped `(run_id, track_id)`
- `addon_handlers.py` — HTTP and Codex WS both call `run_pipeline`, then branch on `bp.is_armed()`
- `request_diff.py:outbound_request_if_changed` — structural equality gate; unchanged → original bytes untouched

**Pipeline vs pause:** apply is independent of arming. Arming only gates the pause branch. On Canvas, arm is never set by product UI, so every turn takes the non-blocking branch after apply. `[measured-source]` / `[corrected]`

### 3.2 How the store gets populated (today)

**On a detached run with Inspector:**

1. Open the run's embedded Inspector (`web_port`).
2. Arm: `POST /api/breakpoint/arm` → `breakpoint.arm` sets that process `_mode = "armed_once"`.
3. Next request pauses; editor PATCHes `/api/overrides` → same-process `OverrideStore.upsert`.
4. Forward / pass-through / drop resolve the pause.
5. Standing overrides reapply on later turns without re-pausing.

**On a Canvas run today:**

- Same capture seam and same pipeline.
- **No product client writes the store** on that run's embedded API (no arm → no pause editor → no PATCH; no launch-time seed of Named Overlays).
- Store stays empty; pipeline is an identity pass; still non-blocking.
- Abandoned wip shape for populate-at-launch is documented elsewhere (`tm-scout-canvas-overlay-populate.md`); **not in tree as shipped behavior**.

**Named Overlay birth (parallel, incomplete):**

1. Only from paused editor: `BreakpointEditor.handleSaveAsOverlay` → `overlaysStore.createDraft` → Overlays route.
2. Confirm name/scope; localStorage key `transport-matters-overlays`.
3. Apply-at-intercept "does not live here yet" (`OverlaysView` / `overlaysStore` comments).
4. **No `/api/overlays`.** Named overlays never enter `OverrideStore` today. `[measured-absent]`

### 3.3 Canvas-side journey (reveal / evidence)

```
Canvas pane may host:
  - captured-run terminal (PTY)  — run continues; no pause UI
  - provider-exchange resource pane → ArkExchangeViewer
       fetchExchange(runId, exchangeId)
       request tab: request_curated_ir ?? request_ir
       inspect tab: curated first; note if curated present
```

**Source mechanism:**

- `ArkExchangeViewer.tsx` — read-only Ark fork; omits editor sections, breakpoint/override affordances, export, "Edited" marker, store imports
- `ArkExchangePanels.tsx:ExchangeInspectPanel` — curated preference + note: "Showing the request as sent. The pipeline or a breakpoint edit mutated the original."
- Shared payload types: `exchanges.ts` (`request_ir`, `request_curated_ir`, `request_audit`, `entry.pipeline`, `mutated_manually`)

**Canvas vs Inspector evidence (source-only; product not running):**

| Evidence | Inspector | Canvas Ark viewer |
|----------|-----------|-------------------|
| Curated request as sent | yes | yes |
| Original IR side-by-side / greyed rows | yes | **no** — note only |
| `request_audit` / per-override before-after | yes | **no** (field unused in canvas viewers) |
| Pipeline savings bar / % | yes (`ExchangeCard`) | **no** |
| Arm / Pause / Forward / Pass Through / Drop | yes | **none found** in canvas package product UI |

### 3.4 Canvas and arming (corrected)

- **Docs:** `TLDR.md` / `Agents.md` — canvas run is never armed; capability not absent; never engages.
- **Mechanism of no-pause:** call-site / UI absence — nothing calls the Canvas run's `/api/breakpoint/arm`. Not a `launch_kind` gate in `addon_handlers`. `[corrected]`
- **Per-process arm still exists** inside the embedded process if something did call arm (e.g. a human opening that run's `web_port` Inspector). Canvas product surface does not. `[measured-source]`
- **Shared-proxy topology "arm flips dead `_mode`" / global-proxy collision claims** apply to shared-proxy runs, **not** to the current per-run embedded Canvas journey. `[corrected]`

---

## 4. Coupling inventory (breakpoint semantics × Canvas / overlay)

### 4.1 Couplings on the Canvas / Named Overlay journey

| # | Kind | Coupling | Evidence |
|---|------|----------|----------|
| C1 | **Birth path** | Named Overlay only from `BreakpointEditor.handleSaveAsOverlay` (paused form). Canvas cannot author. | sole `createDraft` product call site |
| C2 | **UX / copy** | Overlays empty state: "edit a paused request… SAVE AS OVERLAY". | `OverlaysView.EmptyState` |
| C3 | **UX / copy** | Canvas curated note names "pipeline **or a breakpoint edit**"; no provenance field. | `ArkExchangePanels` note |
| C4 | **Data model** | Named Overlay holds breakpoint-form `Override[]`. | `overlaysStore.Overlay.overrides` |
| C5 | **Implementation** | Override API re-previews paused flows (`_update_scoped_paused_preview`); degrades to no-op when none paused. Couples module to breakpoint state, not required for automatic apply. | `api/v1/overrides.py` |
| C6 | **Shared evidence model** | Same exchange fields for both surfaces; Inspector full audit/savings, Canvas thinner curated fork. | `exchanges.ts`; Ark vs `ExchangeCard`/`InspectTab` |
| C7 | **Empty store on Canvas** | Automatic path is live, but Canvas never populates store (no pause editor, no named-overlay apply). | topology + missing writers |

**Dropped as Canvas couplings (prior C1 shared-proxy arm collision):** not on current Canvas topology. `[corrected]`

### 4.2 Boundary-holding absences

| # | Observation |
|---|-------------|
| A1 | No Canvas Arm / Disarm / Pause / Forward / Pass Through / Drop controls |
| A2 | No Canvas import of `useBreakpoint`, `BreakpointEditor`, `overlaysStore` |
| A3 | Ark viewer omits breakpoint/override machinery by design |
| A4 | Named overlays not applied at intercept |
| A5 | Inspector breakpoint API/UI remain intact (must not delete) |

### 4.3 Incomplete product vs owner automatic-overlay vision

| Gap | Status |
|-----|--------|
| Select and apply a **named** Overlay through the request pipeline | **Not implemented** |
| Populate Canvas run store at launch | **Not shipped** (populate seam known; wip not current tree behavior) |
| Canvas reveals original + curated + audit + savings | **Partial** (curated + note) |
| Project scope for overlays | **`meta.cwd` is valid on per-run embedded Canvas** — env CWD is set from the run's `working_dir` and `get_meta` prefers `settings.cwd`, so the stamp is the run worktree (`BreakpointEditor` uses `meta?.cwd`). Revisit only if a shared multi-workspace backend arrives. `[corrected]` |
| Fail-open when target stops matching | Exception fail-open exists; silent per-override `_NOT_APPLIED` for drift; Named Overlay invalidation UX unbuilt |

---

## 5. Quality defects (scoped correctly)

### Q1 — Scopeless DELETE loss (**shared-proxy-bound runs only**)

`delete_overrides` with no `run_id`/`track_id` calls `store.clear()` (entire API-process store) then `_sync_shared_overrides` early-returns when `run_id is None`, so **shared-subprocess** stores keep applying overrides the UI thinks were cleared.

**Out of current Canvas journey:** embedded Canvas uses same-process store; clear affects the process that applies. Still a live defect for any run on shared-proxy topology. `[corrected]` re-scope.

Pin shape (from scout): scopeless `DELETE /api/overrides` while a run is in `SharedProxyManager.by_run_id` must clear subprocess scope too.

### Q2 — Lossy rollback on failed mutation (**add**)

On `patch_overrides` / `delete_overrides` / `toggle_overrides`, the handler snapshots **one** scope via `_snapshot_scope(scope)`, mutates, then on exception `_restore_scope(scope, previous)`.

For **scopeless DELETE**, mutation is `store.clear()` (all scopes), but snapshot/restore only cover the normalized unscoped root (`scope_from_params(None, None)` → `__legacy__` root). A failure after clear **does not restore other scopes**. That is a **lossy rollback** defect on the API-process store.

Severity on Canvas embedded: only if a client issues scopeless DELETE against that run's embedded API. Primary exposure coexists with shared-proxy multi-scope usage; still real code. `[measured-source]` / `[corrected]`

### Q3 — `meta.cwd` project stamp (**valid for per-run embedded Canvas**)

`BreakpointEditor.handleSaveAsOverlay` scopes project overlays with `meta?.cwd`. On the per-run embedded topology this is the run worktree: the captured-run spawn sets env CWD from the run's `working_dir` (`launch/environment.py` builder) and `api/v1/meta.py:get_meta` prefers `settings.cwd` over the process cwd. Not a current Canvas defect. Revisit only if a shared multi-workspace backend arrives. `[corrected]`

### Q4 — Shared-proxy mode inference (**outside Canvas journey**)

`shared_proxy` harness-name mode inference (`_infer_mode_kind` style dispatch on harness name) is adjacent hygiene / doctrine tension. **Not part of the current per-run embedded Canvas overlay journey.** Do not treat as a Canvas build dependency. `[corrected]`

### Q5 — UI-only Named Overlay storage

localStorage only; no backend resource; invisible to director / ⌘K. North Star API-first gap when Named Overlays become behavior.

---

## 6. Journey in one narrative (human answer)

**Today, "automatic overlay" on a Canvas run means:** each Canvas launch gets its own mitmdump process with an embedded API. That process runs `run_pipeline` on every request: if the process-local `OverrideStore` has standing overrides for the run/track scope, they rewrite the wire and forward without waiting. Canvas never arms that process and never opens a pause UI, so the pause branch does not engage from the Canvas product surface. The store is empty on a pure Canvas launch because nothing writes it (no pause editor, no named-overlay apply). After a turn, a Canvas exchange pane can show the **as-sent (curated)** payload when curation happened, plus a short note; it does not yet show full original/audit/savings.

**Named Overlays** are born only by saving breakpoint edits into browser localStorage and do not re-enter the intercept pipeline.

**Breakpoint remains Inspector-owned** on a surface that can arm and pause (typically a run's embedded Inspector). Couplings that remain on the Canvas story: authoring birth and empty-state copy, curated-note wording, shared exchange evidence model, and the empty-store gap — not shared-mitmdump arm collision.

---

## 7. Searches that returned nothing material (phase-1 sweep)

| Search intent | Result |
|---------------|--------|
| `/api/overlays` backend | **none found** |
| Named overlay apply-at-intercept beyond comments | **none found** |
| Canvas `useBreakpoint` / arm API clients | **none found** |
| `launch_kind == "canvas"` exclusion from pause | **none found** (no-pause is call-site absence) |
| Canvas rendering of `request_audit` or pipeline savings | **none found** |
| Live product UI | **not running** (source-only limit) |

---

## 8. Counts for orchestrator signal

- **Journey stages:** 4  
  1) (optional) override authoring via Inspector pause on a pausable run  
  2) automatic non-blocking `run_pipeline` apply in the run process  
  3) capture of original + curated + audit on exchange  
  4) Canvas partial reveal via Ark exchange viewer  
- **Canvas/overlay breakpoint couplings:** **7** (C1–C7 after topology correction; prior shared-proxy arm collision removed from Canvas set)  
- **Boundary-holding absences:** 5  
- **Quality defects called out:** Q1 shared-proxy DELETE loss; Q2 lossy rollback; Q3 meta.cwd valid on embedded Canvas (not a defect); Q4 shared-proxy mode inference out of journey; Q5 UI-only named overlays  

---

## 9. File:symbol index (primary)

| Role | Symbol |
|------|--------|
| Canvas capture prepare | `capture_rpc.CaptureLeaseRegistry.prepare_capture` |
| Spawn seam | `prepare_captured_run` / product-plane `RunManager` |
| Per-run addon + embedded API | `addon_runtime.load_runtime` / `load_capture_runtime`; `web_runtime.start_web_runtime` |
| Automatic apply | `request_pipeline.run_pipeline` |
| Transform + audit | `overrides.apply_overrides` |
| Store | `overrides.state.OverrideStore` / `get_store` |
| Non-blocking forward branch | `addon_handlers` (`pause_request = not skip and bp.is_armed`) |
| Wire rewrite gate | `request_diff.outbound_request_if_changed` |
| Arm state (per process) | `breakpoint.arm` / `is_armed` / `_mode` |
| Pause helpers | `pause_session.handle_breakpoint` |
| Override HTTP + pause preview | `api.v1.overrides` (`_update_scoped_paused_preview`, `_restore_scope`, `delete_overrides`) |
| Shared-proxy only | `SharedProxyManager.set_overrides`; `_sync_shared_overrides` |
| Named overlay model/UI | `overlaysStore` / `OverlaysView` |
| Birth from pause | `BreakpointEditor.handleSaveAsOverlay` |
| Canvas reveal | `ArkExchangeViewer` / `ArkExchangePanels.ExchangeInspectPanel` |
| Inspector savings | `ExchangeCard` pipeline tab |
| Owner binding | CM `019fdb4f-…`; `TLDR.md` canvas never armed; `NOW.md` overlay landing spot |

---

## 10. Unknowns (preserved)

1. Live Desktop Canvas layout and exchange pane chrome (product not running; source-only evidence limit).
2. Whether operators ever open a Canvas run's embedded `web_port` Inspector and arm it manually (behavioral).
3. Future shared-proxy Canvas mode: if Canvas ever moves onto shared mitmdump, Q1/Q4 and arm topology must be reopened; **not current journey**.
