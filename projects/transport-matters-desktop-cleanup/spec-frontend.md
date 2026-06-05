---
title: Desktop Cleanup — Frontend Spec (Template Picker)
type: spec
tags: [frontend, transport-matters, desktop-cleanup, runtime-template, template-picker]
summary: Template-picker UI in www/ that sends runtime_template on CreateRunRequest when spawning a captured run; default selection preserves today's NATIVE launch.
status: active
source: frontend-engineer
confidence: high
created: 2026-06-17
updated: 2026-06-17
---

# Desktop Cleanup — Frontend Spec (Template Picker)

## Charter

The desktop becomes opinionated; transport-matters owns the launch config. The
frontend deliverable is a **template-picker UI** that lets the user choose a
runtime template when spawning a captured run, and sends that template's **name**
as `runtimeTemplate` on the `POST /v1/runs` request. Absent or empty selection
sends nothing, so today's behavior (NATIVE launch into the user's live config
home) is preserved byte for byte.

Backend Slice 4 already landed: `CreateRunRequest.runtime_template` exists and a
resolver threads a present name into TEMPLATE mode; absent/empty resolves to
NATIVE. The frontend owns the **picker UI** and the **request wiring**. The two
seams shared with the backend author (coordinate via the orchestrator) are:

1. The **template-list endpoint** the picker enumerates from (does not exist yet).
2. The `CreateRunRequest` **field name** the request carries (already `runtimeTemplate`).

Scope is `www/`. This spec is read-only analysis plus a change plan; no code was
modified.

---

## Current state

### How the desktop spawns a captured run today

The production surface is the session canvas, not the lab harness. (`CanvasLabRoute`
under `www/src/session-canvas/lab/` is an unimported dev harness — zero importers
— and is out of scope. The shipped path is `CanvasSurface` →
`SessionCanvasRoute`.)

The spawn flow, end to end:

1. **Spawn affordance** — `CanvasCommandBar`
   (`www/src/session-canvas/components/CanvasCommandBar.tsx`) renders one button
   per provider from `CAPTURED_RUN_PROVIDERS = ["claude", "codex"]`, labelled
   `Spawn {cliLabel(provider)}`. Each button calls `onSpawnCapturedRun(provider)`.
   The flow is linear: one click → one pane per provider. There is no
   intermediate selection step.

2. **Surface wiring** — `CanvasSurface`
   (`www/src/session-canvas/components/CanvasSurface.tsx`) passes its local
   `addCapturedRun` as `onSpawnCapturedRun`, which delegates to the store's
   `addCapturedRun(provider)`.

3. **Store action** — `useCanvasStore.addCapturedRun(provider)`
   (`www/src/session-canvas/model/canvasStore.ts`) calls
   `createCapturedRunRef(provider, cliLabel(provider))` then
   `spawnPane(ref, { focus: true })`.

4. **Ref construction** — `createCapturedRunRef(provider, label?)`
   (`www/src/session-canvas/model/spawn.ts`) returns a `CapturedRunRef`:
   `{ kind: "captured-run", owner: "local", provider, runKey: createCapturedRunKey(provider), label? }`.
   The ref is the persisted source of truth for the pane (zustand `persist` via
   `canvasStore.persistence.ts`); `createCapturedRunRef` is also re-invoked on
   rehydrate.

5. **Pane render** — `viewers/registry.tsx` maps the `captured-run` ref to a
   lazily-loaded `CapturedRunPane`, passing `runKey`, `provider`, and `cwd`.

6. **Run creation** — `CapturedRunPane`
   (`www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx`) calls
   `ensureRun(runKey, provider, cwd, oscColorReplies)` from `capturedRunStore`.
   `ensureRun` (`www/src/session-canvas/model/capturedRunStore.ts`) dedupes by
   `runKey`, persists the resulting `runId`, and on the first spawn calls
   `createCapturedRun(...)` under a concurrency slot.

7. **API client** — `createCapturedRun(cli, cwd?, oscColorReplies = true)`
   (`www/src/api.ts`) issues `POST /v1/runs` with body
   `{ cli, cwd?, oscColorReplies }`. **It does not send `runtimeTemplate` today.**

### The `CreateRunRequest` client shape the UI sends

```
{ cli: "claude" | "codex", cwd?: string, oscColorReplies: boolean }
```

The backend `CreateRunRequest`
(`api/.../api/v1/run_routes.py`) already accepts more than the client sends:
`cli`, `cwd`, `terminal`, `oscColorReplies`, `continueFromSessionId`,
`idempotencyKey`, and **`runtimeTemplate`** (Python `runtime_template: str | None`,
field alias `runtimeTemplate`). The resolver `_runtime_template_ref(body, cli)`
calls `resolve_runtime_template(name, cli, env=...)` when a name is present, and
returns `None` (NATIVE) when absent/empty. So the request field is **ready**; the
client just never populates it.

### "Launch in terminal" affordance — none in `www/`

There is **no** "launch in terminal" / detached-terminal affordance in the
desktop UI, so desktop cleanup has nothing to remove on the frontend here.
Verification:

- `createCapturedRun` sends no launch-mode flag. Captured runs always render as
  an in-canvas pane.
- The `terminal` field on `CreateRunRequest` is **not** a mode toggle: it is a
  `TerminalSizeModel | None` carrying PTY `cols`/`rows`. The client never sets it.
- The only "terminal" in `www/` is the in-canvas xterm viewer under
  `www/src/session-canvas/viewers/terminal/` (`CapturedRunPane`, `TerminalPane`,
  `terminalSession`, `terminalSocket`). That **is** the desktop pane surface and
  **stays**.

The detached/local terminal launch that desktop cleanup is dropping lives in the
CLI path (`transport-matters claude`), outside `www/`. **Flag:** if any future
"open in external terminal" button was contemplated for the canvas, it does not
exist today, so there is no frontend deletion to schedule. Confirm with the
orchestrator that "dropping terminal-spawning" is scoped to the CLI/backend and
imposes no `www/` removal.

---

## Proposed changes

### 1. Template-list enumeration (new backend seam — flag to orchestrator)

The picker must enumerate available templates. **No list endpoint or list
function exists today.** `runtime_registry.py` exposes only
`resolve_runtime_template` (single-name resolve), `_registry_root`, and
`_validated_template_name`. The registry root is `~/.agent-runtimes/runtimes/`;
names may be nested (e.g. `team/codex`); resolution rejects symlinks, `..`
traversal, and non-directories.

**The backend must add** (the backend author is speccing this seam — agree the
contract via the orchestrator):

- A `list_runtime_templates(client_name, env)` function in `runtime_registry.py`
  that lists `~/.agent-runtimes/runtimes/` and returns the valid template names.
- A `GET` endpoint (proposed `GET /v1/templates`, optional `?cli=` filter) that
  returns the list to the frontend.

**Frontend addition once the contract is fixed:** a `fetchRuntimeTemplates(cli?)`
function in `www/src/api.ts` mirroring the existing `fetch*` helpers (e.g.
`fetchCapabilities`), returning the parsed list. The picker calls it when it opens
(or on mount) and renders the results.

The exact **response shape** is an open contract item (see Open decisions): a bare
`string[]` of names, versus an array of objects with display metadata. The
frontend only needs the **name** to wire the request; any extra fields are for
picker display.

### 2. Template-picker component

**Where it lives:** a new component under
`www/src/session-canvas/components/` (e.g. `TemplatePicker.tsx`), hosted by
`CanvasCommandBar` alongside the existing spawn buttons. The command bar already
owns the spawn affordance, so the picker is cohesive there and avoids a new
top-level surface. Placement style is an open decision (split button vs. inline
select vs. spawn popover) — see Open decisions.

**Behavior:**

- Presents a "Native (default home)" option plus one entry per enumerated
  template. Default selection is **Native**.
- On spawn, the selected template's name is threaded into the request. **Native →
  send no `runtimeTemplate`** (omit the field entirely so the backend resolves
  NATIVE). A non-empty name → send `runtimeTemplate: name` (TEMPLATE mode).
- Eight-state coverage for the picker control: default, hover, active, focus,
  disabled (while the list is loading or a spawn is in flight), loading (list
  fetch pending), error (list fetch failed → fall back to Native-only so spawning
  still works), empty (no templates on disk → Native-only, no picker chrome, today's
  behavior unchanged). Keyboard navigable, visible focus ring, ARIA-labelled,
  wired into the existing `role="toolbar"` command bar.

### 3. Threading `runtimeTemplate` through the spawn flow

The selection must reach the request. The ref is the persisted source of truth, so
the template rides on the `CapturedRunRef`. Additive, optional field at every hop:

1. `www/src/api.ts` — `createCapturedRun(cli, cwd?, oscColorReplies?, runtimeTemplate?)`;
   include `runtimeTemplate` in the POST body only when non-empty.
2. `www/src/session-canvas/model/capturedRunStore.ts` — `ensureRun(runKey, provider, cwd, oscColorReplies, runtimeTemplate?)`;
   pass through to `createCapturedRun`. Dedupe stays keyed by `runKey` (template
   is a first-spawn input, not part of identity).
3. `www/src/session-canvas/viewers/terminal/CapturedRunPane.tsx` — add optional
   `runtimeTemplate` prop, pass to `ensureRun`, add to the `useEffect` deps.
4. `www/src/session-canvas/viewers/registry.tsx` — pass
   `runtimeTemplate={ref.runtimeTemplate}` to `<CapturedRunPane>`.
5. `www/src/session-canvas/model/paneRecords.ts` — add `runtimeTemplate?: string`
   to the `captured-run` member of the `PaneContentRef` union, and update the
   captured-run type guard (the `isCliName(...) && typeof runKey === "string"`
   check) plus `paneRecords.contract.test.ts`.
6. `www/src/session-canvas/model/spawn.ts` —
   `createCapturedRunRef(provider, label?, runtimeTemplate?)`; store it on the ref.
7. `www/src/session-canvas/model/canvasStore.ts` —
   `addCapturedRun(provider, runtimeTemplate?)`; forward to `createCapturedRunRef`.
8. `www/src/session-canvas/components/CanvasSurface.tsx` — read the picker's
   current selection and pass it through `onSpawnCapturedRun` →
   `addCapturedRun(provider, runtimeTemplate)`.

**Default selection (absent → NATIVE):** since the field is optional at every hop,
a ref with no `runtimeTemplate` (including any ref persisted before this change)
omits the field and resolves NATIVE. The persisted-store version needs **no
migration bump**: an absent optional field already means NATIVE, which is the
correct and safe default.

**Re-spawn note:** `ensureRun` only spawns on the first open; a reload re-attaches
the existing `runId` rather than re-spawning, so the template is consumed once at
first spawn. Carrying it on the persisted ref keeps the value available for that
first spawn even across a pre-spawn reload.

---

## Open decisions

These are genuine product forks for the orchestrator.

1. **Picker placement / interaction model.** Options:
   - **A. Split / dropdown spawn button** — keep `Spawn {provider}`, add a caret
     that opens the template list. Preserves one-click NATIVE default; template is
     one extra click.
   - **B. Inline `<select>` in the command bar** — a single template selector that
     applies to the next spawn of either provider. Compact; weakest at per-template
     metadata.
   - **C. Spawn popover/modal** — clicking a provider button opens a small
     popover to choose template (and potentially `cwd`) before confirming. Scales
     best to metadata and future fields; adds a click to every spawn.
   Recommendation: **A** if one-click NATIVE speed is paramount, **C** if the
   picker should show per-template metadata. Needs a product call.

2. **Default selection scope.** Confirm default is always **Native** (no sticky
   "last used template"), or whether the last selected template should persist
   per session. Default-Native is the safe, lowest-surprise choice.

3. **Per-template metadata shown in the picker.** Just the name, or also
   provider, a description, and required capabilities? This drives the list
   endpoint response shape (bare `string[]` vs. objects). The picker only needs the
   name to function; metadata is display polish.

4. **Per-CLI filtering.** Should the picker show only templates valid for the
   provider being spawned (the resolver already takes `client_name`, and nested
   names like `team/codex` suggest CLI-scoped homes), or all templates with the
   backend rejecting a mismatch at resolve time? Recommendation: filter client-side
   by provider if the endpoint returns per-template provider info; otherwise pass
   `?cli=` to the list endpoint.

### Backend seams to confirm via orchestrator

- **List endpoint:** path/method (`GET /v1/templates` proposed), filter param
  (`?cli=`?), and response shape (`string[]` vs. `{ name, provider?, description?,
  requiredCapabilities? }[]`).
- **Request field name:** confirmed **`runtimeTemplate`** (camelCase JSON alias on
  `CreateRunRequest`). No change needed; flagged for explicit agreement.
