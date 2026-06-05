# The overlay: scout map

Date: 2026-08-05. Seat: opus. Read-only; tree untouched at `feat/firstrun-slice3`.

Symbols cited `path::SYMBOL`. Measurements come from the human's own captured turn,
run `5f44eeaa-3032-4fbe-9ce1-78951c5df6dc`, exchange `20260805T050107Z-e6ca3001`,
`claude-fable-5`, under `~/.transport-matters/workspaces/dev-helioy-transport-matters/ecd9b0df/`.

---

## 1. What an override IS

**EXISTS.** `api/src/transport_matters/overrides/__init__.py::Override`. Three fields,
frozen, and that is the whole model:

```python
kind: OverrideKind          # one of nine
target: str                 # a string address, scheme below
value: str | bool | int | None   # None means delete
```

Identity is the tuple `(kind, target)` — `overrides/state.py::OverrideStore.upsert` keys on
it. There is no id, version, author, timestamp, or content hash. Nothing records which IR
shape the target was authored against.

Nine kinds, applied in a fixed order from `overrides/__init__.py::_PRIORITY` (toggles before
rewrites, knobs last), not in insertion order:

| kind | value | target scheme |
|---|---|---|
| `tool_toggle` | bool | `tool:{name}` |
| `tool_description` | str | `tool:{name}` |
| `system_part_toggle` | bool | `system:{index}` |
| `system_part_text` | str | `system:{index}` |
| `truncate_tool_result` | int | `toolresult:{tool_use_id}` |
| `message_block_toggle` | bool | `msg:{i}:blk:{j}` |
| `message_text` | str | `msg:{i}:blk:{j}` |
| `sampling_set` | str (JSON) | `sampling:{field}` |
| `provider_extras_set` | str (JSON) | `provider_extras:{key}` |

### Targeting is MIXED, and this is the load-bearing fact

`overrides/targets.py` is pure string encoding and parsing. Two disjoint regimes:

**Content-keyed (stable under vendor churn):** `tool:{name}`, `toolresult:{tool_use_id}`,
`sampling:{field}`, `provider_extras:{key}`. The address is the thing's own name. If the
vendor renames or drops a tool, the target stops matching — it **under-matches**, which is
the safe direction.

**Positional (unstable under vendor churn):** `system:{index}` and `msg:{i}:blk:{j}`. The
address is an ordinal. If the vendor inserts a system part ahead of yours, every later index
silently addresses a different block. That is **over-match**, which the human named as the
more dangerous direction, and nothing in the code detects it.

`targets.py::adjust_system_index` and `::adjust_blk_index` do compensate for shifted indices,
but only for removals made *by earlier overrides within the same apply pass* — the docstring
says so explicitly ("Only `message_block_toggle` mutates the block layout during the apply
pipeline"). They do nothing about the request shape changing between runs. There is no
recorded fingerprint of the block a positional target was authored against, so a stale
positional target is indistinguishable from a live one.

**Consequence for governance: the two blocks worth the most money sit on opposite sides of
this line.** Tools are name-addressed and safe. The human's own 35,409-char SessionStart hook
block is `msg:1:blk:0` and is not.

---

## 2. The store

**EXISTS.** `overrides/state.py::OverrideStore`, a module-level singleton `_store` reached
through `::get_store`. Its own docstring: *"Session-scoped override state. Lives in the addon
process."*

- **Scope** is `OverrideScope = tuple[run_id, track_id]` (`::normalize_scope`,
  `::scope_from_params`, `::root_scope`), with `LEGACY_SCOPE_ID = "__legacy__"` when run_id is
  absent.
- **Lifecycle** is process memory. Two plain dicts, no load, no save. It dies with the addon
  process. `grep -rniE "overlay|override" api/migrations` → zero hits across all 32
  revisions; there is no table.
- **Enabled defaults to True** — `::is_enabled` reads `self._enabled.get(normalized, True)`,
  so a scope is on unless someone explicitly stored False. Disabling is opt-out, not opt-in.
- **Readers:** `request_pipeline.py::run_pipeline` on every intercepted request;
  `api/v1/breakpoint_routes.py::re_audit_flow`; `api/v1/overrides.py::get_overrides` and
  `::_snapshot_scope`.
- **Writers:** `api/v1/overrides.py::patch_overrides` / `::delete_overrides` /
  `::toggle_overrides` in the API process, and
  `shared_proxy/subprocess.py::SharedProxyRuntime.set_overrides` in the proxy process, which
  is the one that matters because that is where `run_pipeline` runs.

### Where it WOULD be populated

`api/v1/overrides.py::patch_overrides` → `OverrideStore.upsert(scope)` →
`::_sync_shared_overrides` → `shared_proxy/manager.py::SharedProxyManager.set_overrides` →
`shared_proxy/subprocess.py::set_overrides`. The write is transactional on the API side:
`patch_overrides` snapshots the scope and calls `::_restore_scope` on any exception.

`_sync_shared_overrides` early-returns on `run_id is None` or `run_id not in
manager.by_run_id`, so a scope with no registered proxy binding lands only in the API
process's copy and never reaches the pipeline.

### Confirm/refute: does anything BLOCK a canvas run from the overlay?

**Refuted — nothing blocks it. The store is simply never written on that path.**

`request_pipeline.py::run_pipeline` reads the store for every intercepted request regardless
of which surface launched the run; there is no canvas-specific gate anywhere in the apply
path. The gap is upstream: the sole product caller of `patch_overrides` is the Inspector's
paused-flow editor (`www/packages/inspector/src/api.ts::patchOverrides`, driven from
`components/editor/BreakpointEditorActions.ts::useBreakpointEditorActions`), and a canvas run
never pauses — `packages/runtime/src/service/RunManager.ts::RunManager.register` sets
`RUNNING` unconditionally and `domain/runtimeRun.ts::RuntimeRunState` has no paused member.

Canvas is read-only toward overrides *by declaration*, not by accident.
`www/packages/canvas/src/viewers/resource/ArkExchangeViewer.tsx` says in its header:
"Deliberately omitted: editor sections, breakpoint/override", and
`viewers/resource/ArkExchangePanels.tsx`: "no breakpoint or override machinery, no store
imports."

So "TM takes over" takes over nothing because no writer exists on the surface the user lands
on, not because a guard refuses.

---

## 3. Application

**EXISTS.** `addon_handlers.py` → `request_pipeline.py::run_pipeline` →
`overrides/__init__.py::apply_overrides` → the nine `_apply_*` handlers → `_mutate_current_ir`
→ `_sanitize_current_ir` → `_build_override_audit`.

`apply_overrides` is a list comprehension over `sorted(overrides, key=_PRIORITY[kind])`,
threading an `_OverrideApplyContext` that holds both `original_ir` and `current_ir`. Index
targets resolve against `original_ir`; mutations accumulate on `current_ir`. The IR is frozen
pydantic (`api/CLAUDE.md`: "IR models are `frozen=True` — pipeline actions return new
instances"), so each handler returns a new instance.

Curated IR is persisted as `request.curated.ir.json`
(`storage/disk_layout.py::_REQUEST_CURATED_IR_FILENAME`) and omitted when it equals the
original.

### What happens when a target no longer matches

**It is silently skipped and everything else still applies.** Every handler returns the module
constant `overrides/__init__.py::_NOT_APPLIED` (`applied=False, chars_delta=0`) on a parse
failure, a type mismatch, an out-of-range index, or an already-removed block. `_apply_override`
turns that into an audit entry with `applied=False` and the comprehension moves on. There is
no abort, no rollback, no gate.

### The atomicity unit

**One override.** Not the overlay, not the request. Three stored overrides where the second
has gone stale produce a request on the wire carrying overrides one and three. Nothing
computes `all(entry.applied)` and nothing acts on it — the decision is the absence of a
decision, distributed across the `_NOT_APPLIED` returns in each handler.

---

## 4. Fail-open

**Enforced for exceptions. REACHABLE for drift.** The two are different failure classes and
only one is covered.

The deciding symbol is `request_pipeline.py::run_pipeline`, docstring *"Never raises."*:

```python
try:
    curated_ir, audit = apply_overrides(store.get_all(scope=scope), ir)
except Exception:
    logger.exception("Override pipeline failed for flow %s, forwarding unmodified", flow_id)
    return ir, None, track_assignment
```

If `apply_overrides` throws, the original IR goes out untouched with a null audit. That is
genuine forward-unmodified, and it is the only place the property is enforced. It is enforced
at byte level, not just at IR level: `curated_ir is ir`, so
`request_diff.py::outbound_request_if_changed` returns `None`, `addon_handlers.py` skips
`flow.request.set_text`, and mitmproxy forwards the **originally captured bytes** rather than
a reserialization. A partially mutated `current_ir` lives only in the local
`_OverrideApplyContext` and cannot escape.

One genuine fail-open bonus: `apply_overrides` sorts on `_PRIORITY[o.kind]`, an unguarded dict
index, so an override carrying a kind this build does not know raises `KeyError` and the whole
request forwards unmodified. Unknown-kind is safe by accident, which is the behaviour the
compatibility rule wants and the only place the code accidentally has it.

A stale target does not throw. It returns `_NOT_APPLIED`, so it never reaches that `except`,
and the request leaves **partially modified** — precisely the state the human ruled out. The
information needed to refuse is already computed and discarded: `OverrideAudit.entries` carries
`applied: bool` per override, so `any(not e.applied for e in entries)` is available at the exact
moment the decision would be made, and nobody reads it.

`store.is_enabled(scope)` is a per-scope kill switch checked before apply, defaulting to True,
toggled by `api/v1/overrides.py::toggle_overrides`. It is all-or-nothing for a scope and is not
drift-aware.

---

## 5. Audit

**EXISTS, mechanically complete, semantically anonymous.**

`overrides/audit.py::OverrideAuditEntry` records exactly `kind`, `target`, `applied`,
`chars_delta`, `curated_value`. `::OverrideAudit` wraps the list with before/after char totals
split by section (`system_chars_before/after`, `tools_chars_*`, `messages_chars_*`).

It lands per exchange in `entry.json` under `pipeline.overrides_applied`
(`storage/disk_helpers.py`), alongside `chars_before/after` and `tokens_before/after`, and is
mirrored to `request.audit.json`.

**Can it attribute a change to a named cause the user recognises?** Partly, and the split falls
along the same line as §1. For a tool override the target *is* the name —
`tool:mcp__plugin_helioy-tools_cm__cx_store` is self-describing and a user would recognise it.
For a positional override the target is `system:2` or `msg:1:blk:0`, which names a coordinate,
not a thing. There is no `reason`, `label`, `cause`, or `source` field anywhere in the audit
model, and no field says *which overlay* an override came from — because overrides do not carry
that either (§7).

`overrides/ops_messages.py` and `::ops_metadata.py` are private mutation helpers
(`ops_metadata.py::SAMPLING_FIELDS`, `::sampling_value_valid` shape-check JSON-decoded sampling
values); they are not a description catalogue.

Two accounting traps worth knowing before building on the ledger:

- **`PipelineStats.overrides_applied` includes the misses.** `exchange_recorder/stats.py::build_pipeline_stats`
  copies the full entry list, `applied=False` rows and all, despite the field name. The
  per-section char fields (`system_chars_*`, `tools_chars_*`, `messages_chars_*`) are dropped in
  that projection and survive only in `request.audit.json`.
- **The audit goes null three different ways and storage cannot tell them apart:** overrides
  disabled for the scope, `apply_overrides` raised, or a manual editor edit diverged (§6). All
  three write no `pipeline` block and no `request.audit.json`. Only the third leaves a trace, the
  `mutated_manually` boolean on `storage/base.py::IndexEntry`.

---

## 6. Manual edits versus TM-authored overlay

**Two mechanisms. The prior finding is CONFIRMED and still true.**

**Path A, standing policy.** Editor → `PATCH /api/overrides` → `OverrideStore.upsert` →
forwarded to the proxy process → `run_pipeline` → `apply_overrides` on every *later* turn of
the run. Audited, char-accounted, subject to §3 and §4.

**Path B, this turn only.** `api/v1/breakpoint_routes.py::release_flow(flow_id, ir:
InternalRequest)` takes the browser's edited IR **from the request body**, checks only that
`ir.provider == pf.original_ir.provider`, serializes via `::_validated_release_payload` and
releases it. It never calls `apply_overrides`. The bytes on the wire are the client's IR
verbatim.

So a manual release is a second writer that sits entirely outside the override store, outside
the audit ledger's derivation, and outside whatever atomicity rule the overlay later adopts.
`::release_flow_unmodified` is the reconciled variant — it releases `pf.curated_ir`, which
`::re_audit_flow` derives by re-applying the store to `original_ir`.

The deciding symbol on the wire side is `pause_session.py::_release_payload`, whose docstring
says it outright: *"An explicit user payload (Forward with edits) is always honored."* It
returns `pf.release_payload` when set, and `handle_breakpoint` writes those bytes with no diff
check and no re-application.

**And Path B destroys the ledger.** `pause_session.py::resolve_paused_flow` returns
`audit=None` whenever the editor's IR differs structurally from `pf.curated_ir`, setting
`mutated_manually=True` instead. So a manually edited turn carries no override record at all,
just a boolean. The one case that keeps its audit is an edit that happens to equal
`curated_ir` — and even then the bytes are the editor's serialization, not the captured
original.

Any governance rule enforced inside `apply_overrides` binds neither the partial case nor
Path B.

Note the panel edits themselves *do* converge: `api/v1/overrides.py::_update_scoped_paused_preview`
and `::re_audit_flow` both re-run `apply_overrides` against `pf.original_ir`. It is specifically
the Forward-with-edits textarea that bypasses everything.

---

## 7. Versioning, identity, provenance

**NONE FOUND on the backend.** `Override` has three fields (§1); `OverrideStore` has no
serialization; `api/migrations` has no overlay or override table.

**Partial, browser-only, on the frontend.** `www/packages/inspector/src/stores/overlaysStore.ts`
is the only place an overlay has identity: `id` (a `crypto.randomUUID()`), `name`, `scope`
(`"shared"` or `{kind:"project", cwd}`), `overrides: Override[]` snapshotted at save,
`createdAt`, `draft`. Persisted by zustand under
`stores/persistence.ts::INSPECTOR_STORAGE_KEYS.overlaysStore` = `"transport-matters-overlays"`.

That identity survives a reload on one browser profile and nothing more. No `updatedAt`, no
revision, no author, no hash of the overrides array, no export, no server row. And critically
for §1: **no binding to a harness, model, harness version, or wire fingerprint.** An overlay
authored against Claude's tool schema carries nothing that would stop it applying to Codex.

The store's own header concedes the gap: "The apply-at-intercept pipeline, chip strips, and
per-field attribution arrive in later slices."

---

## 8. Replay

**NONE FOUND.** Nothing re-sends a stored turn.

The only outbound provider call in the API is `counting.py::TokenCounter.count` against
`/v1/messages/count_tokens`, a metering endpoint, not inference. No route matches
replay/resend/rerun/reissue/fork/simulate/counterfactual.

Two near-misses, both worth naming because they bound the gap:

- `api/v1/breakpoint_routes.py::re_audit_flow` re-applies the current store to a **live paused
  flow's** `original_ir`, updating `pf.curated_ir` and `pf.audit` in place. It is
  recompute-over-a-held-payload, not replay: the request is still parked and only leaves via
  `release_flow`. It does make one network call, `::_recount_tokens` → `TokenCounter.count`.
- `api/v1/exchanges.py::get_pipeline_tokens` recounts tokens over a **stored** exchange, but it
  counts the two already-persisted IRs verbatim and never consults the store or calls
  `apply_overrides`.

`HarnessCapabilities.replay` and `.fork` are declared `False` for both launch-eligible
harnesses in `harnesses/__init__.py::_CLAUDE_DESCRIPTOR` / `::_CODEX_DESCRIPTOR`, and neither
flag is read by any production symbol.

The Inspector's `components/routes/RecallView.tsx` advertises "replay with or without saved
overlays" and renders `ComingSoonRoute`.

Given the human's sequencing puts replay underneath versioning and evals: the primitive does
not exist, and the closest existing machinery (`re_audit_flow`) is scoped to a flow that is
still in flight.

---

## 9. wip/canvas-overlay @ 23a49430

**Salvageable, and complementary rather than superseded.** One commit on merge-base
`c735e25c`, 27 files, +325/−56, carrying confirmed overlays from browser localStorage into a
captured run at launch: `capturedRunStore.ts` reads `useOverlaysStore`, through
`transport.ts::CreateCapturedRunOptions.overlays` → `runtime/src/ports.ts::PrepareCaptureInput`
→ `api/v1/capture_rpc_routes.py::PrepareCaptureRequest.overlays` → a new
`overrides/__init__.py::LaunchOverlay` in `settings.launch_fields` →
`addon_runtime.py::load_capture_runtime` calling `get_store().upsert(..., scope=root_scope(run_id))`.

That is exactly the missing writer from §2, at launch time rather than mid-run.

Against today's three merged first-run slices it is orthogonal: those *observe* the first turn,
this *transforms* it, and they meet only in the same launch call. `git merge-tree` against
`feat/firstrun-slice3` reports three conflict hunks, all additive-adjacent and none redefining a
shared symbol: `core/src/transport.ts` (both add optional fields to `CreateCapturedRunOptions`),
`canvas/src/model/capturedRunStore.ts` (both extend the same `ensureRun` spawn block),
`core/src/transport.test.ts`.

One caveat: the branch moves `overlaysStore.ts` into `@tm/core` and inlines the localStorage
key while deleting it from the inspector registry, and first-run also touched
`canvas/src/infrastructure/persistence/storageKeys.ts`. The shell asserts the two key
registries never collide, so that assertion needs checking on rebase.

It carries no identity or version on `LaunchOverlay`. It closes the plumbing gap, not the
provenance gap.

---

## The smallest overlay content that is safe, valuable, and buildable

Measured on the human's own turn: **114,434 chars total** — system 18,679, tools 52,667,
messages 43,088 — against a **14-char prompt**, producing **41,837 tokens of cache write**.

| candidate | mechanism | measured | % of payload | breaks if the vendor... |
|---|---|---|---|---|
| Drop the 10 `mcp__plugin_helioy-tools_cm__*` tools | `tool_toggle` on `tool:{name}` | **19,547** | 17.1% | never — the names are the user's own MCP server, not the vendor's |
| Drop `Artifact` + `AskUserQuestion` | `tool_toggle` | 15,564 | 13.6% | renames them; target stops matching, under-matches safely |
| Both of the above + `ScheduleWakeup` | `tool_toggle` | 23,288 | 20.4% | same |
| Drop the SessionStart hook block | `message_block_toggle` on `msg:1:blk:0` | 35,409 | 30.9% | inserts any earlier message or block — silently retargets |
| Trim system part 2 | `system_part_text` on `system:2` | up to 18,552 | 16.2% | inserts a system part — silently retargets |

**The recommendation is `tool_toggle` on named tools, and the reason is targeting, not size.**
It is the only kind whose address is content-keyed, so its failure mode is under-match: a
renamed tool quietly stops matching and the request goes out whole. Every other candidate on
that table is positional, and its failure mode is over-match against a block that moved.

The largest single win is the SessionStart hook at 35,409 chars — a third of the payload, and
the human wrote it himself, so it is the block he is most entitled to govern. It is also the
one addressed by `msg:1:blk:0`. That tension is the real finding here: **the most valuable
content to overlay is the least safely addressable.** Making it safe means content-addressing
message blocks, which does not exist today.

Two facts that bound any first slice, both from §3 and §4: a stale target is skipped silently
rather than refused, and a manual release bypasses the store entirely. A governance rule
written inside `apply_overrides` binds neither the partial case nor Path B.
