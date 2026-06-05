# S1b Review — thread trusted canvas affinity

- **Range**: `40c82e456c5d74dcb26e13f910c38c18acbe02d3..119f520d877590ee254e83349c0e916e6198d07d`
- **Commit**: `119f520d` `feat(session): thread trusted canvas affinity` (50 files)
- **Branch**: `feat/multi-launch`
- **Tree at review**: pristine (`git status --porcelain` empty; HEAD = `119f520d`)
- **Gates**: not run (shared tree; orchestrator owns full gate)
- **Lens**: DRY + dead code + alternate producer completeness
- **Verdict**: **approve with majors** (0 blockers, 1 major, 2 minors, 1 nit)

## Lens checklist

| Check | Result |
|-------|--------|
| ONE `build_session_affinity_stamp` for live resolve + `session/backfill.py` | **PASS** — only production constructors are `session/affinity.py::build_session_affinity_stamp` → `launch_resolution.resolve_run_canvas` and `backfill.backfill_session_spaces` |
| ONE adapter affinity helper keyed by `AFFINITY_FIELD_NAMES` | **PASS** — `index/adapters/base.py::affinity_fields`; claude/codex use `**affinity_fields(run)` only (no hand-copied 8-field lists) |
| ONE trusted Worktree resolver (Canvas reuses internals) | **PASS** — `launch_resolution._resolve_launch_worktree` shared by `resolve_run_worktree` and `resolve_run_canvas` |
| `_make_exchange_cursor_sink` threads full 8-field group | **PASS** — `**trusted_binding_affinity(binding)` on `SessionBinding` construction (`addon_runtime.py`) |
| `register_session_cursor` second bind preserves 8-field group | **PASS** — `**affinity_fields(binding)` on both `RunContext` and `model_copy` (`index/tailer.py`) |
| No parallel affinity env var; reserved `session_affinity` launch field only | **PASS** — carrier is `SESSION_AFFINITY_LAUNCH_FIELD` inside `launch_fields` / `LAUNCH_FIELDS` JSON; no new env key |
| Fixtures match fail-closed ruling | **PASS** — non-canvas prepares use `launchKind: "service"`; canvas paths send full space/worktree/canvas tuple; obsolete canvas-ish service fixtures cleaned |

## End-to-end threading (facts)

Browser `registry` → `CapturedRunPane` → `useCapturedRunBinding` → `capturedRunStore` → `createCapturedRunView` → runtime `POST /v1/runs` (`canvasId` in fingerprint) → `CaptureRpcClient` → Python `PrepareCaptureRequest` → `to_domain` strips client forgeries via `affinity_launch_fields(..., None)` → `resolve_run_canvas` + `build_session_affinity_stamp` installs trusted carrier → `build_proxy_run_binding` / shared-proxy `bind_trusted_affinity` decode carrier → owned cursor / exchange sink / tailer re-bind → `session/ingest._binding_affinity` write-once stamp.

## Blockers

None.

## Majors

### M1 — `resolve_run_canvas` does not enforce canvas↔worktree coherence

- **File**: `api/src/transport_matters/api/v1/launch_resolution.py` — `resolve_run_canvas`
- **Also**: `api/src/transport_matters/api/v1/test_capture_rpc_worktree_resolution.py` — `_canvas_for` (`anchor_worktree_id=WorktreeId.from_uuid(UUID(int=100))` deliberately ≠ resolved worktree)
- **Description**: After resolving the requested worktree and loading the canvas (space membership only via `get_canvas` + worktree-in-space), the stamp is built from **those two independently chosen records**. Nothing asserts `canvas.anchor_worktree_id == worktree_id` (or membership of the canvas under that worktree root). Same-space cross-worktree pairs yield a write-once `SessionAffinityStamp` whose `worktree_id`/`worktree_path`/`worktree_branch_name` disagree with the canvas's anchor. Because affinity is write-once, a mismatched prepare permanently stamps incoherent placement.
- **Suggestion**: In `resolve_run_canvas`, after both records resolve, reject with `space_mismatch` (or a dedicated code) when `canvas.anchor_worktree_id != resolved.worktree_id` unless product explicitly allows multi-worktree canvas launch. Lock the invariant in `_canvas_for` / a dedicated negative test.

## Minors

### m1 — owned cursor re-stamps affinity from adapter output, not the trusted carrier

- **File**: `api/src/transport_matters/owned_transcript_binding.py` — `register_owned_cursor`
- **Description**: After `adapter.bind(run)`, the final `model_copy` applies `**affinity_fields(session_binding)` rather than `**trusted_binding_affinity(binding)`. Production claude/codex forward via `affinity_fields(run)`, so the live path works. A future adapter that omits the helper would drop affinity even when the launch carrier is present; the strip of `session_affinity` via `affinity_launch_fields(..., None)` means the carrier is not recovered later on this path.
- **Suggestion**: Prefer `**trusted_binding_affinity(binding)` (or decode-once stamp) as the authoritative post-bind overlay so owned registration fail-closes on the carrier, independent of adapter discipline.

### m2 — dual decode of the same carrier on binding helpers

- **File**: `api/src/transport_matters/shared_proxy/binding.py` — `trusted_binding_affinity`, `bind_trusted_affinity`
- **Description**: Both helpers independently call `affinity_from_launch_fields`. Correct, but callers that need both projection and lifecycle fields re-validate twice.
- **Suggestion**: Optional micro-DRY: one private `_trusted_stamp(binding) -> SessionAffinityStamp | None` shared by both.

## Nits

### n1 — `ProxyRunBinding` still only surfaces `space_id`/`worktree_id` at top level

- **File**: `api/src/transport_matters/shared_proxy/binding.py` — `ProxyRunBinding`, `bind_trusted_affinity`
- **Description**: Full 8-field group lives in the launch carrier only; top-level still projects two fields for lifecycle. Intentional for this slice; lifecycle emission (`addon_runtime._emit_run_lifecycle_event`) correctly uses those two. No change required unless a later consumer needs canvas at the binding top level.

## Dead code / cleanup

- Prior forked stamp construction in `session/backfill.py` deleted; uses `build_session_affinity_stamp`.
- Owned binding construction extracted to `owned_transcript_binding.py` (addon_runtime shrinks; re-exports preserved).
- Shared-proxy test renamed from “leave for backfill” to “persists trusted session affinity” — matches new behavior.
- No obsolete canvas launch fixture left sending partial affinity under default `LaunchKind.CANVAS` without the service override.

## Maintainability (strict bar)

- No file pushed toward 1k lines by this change; `addon_runtime` loses surface area.
- Affinity projection is centralized (`affinity_fields` / `AFFINITY_FIELD_NAMES`); adapters avoid spaghetti field lists.
- Field declarations still repeat across `SessionAffinityStamp` (required), `SessionBinding`/`RunContext` (optional) — acceptable dual shape for nullable pre-stamp vs write-once stamp; not a regression.

## Summary

S1b meets the stated DRY and alternate-producer bar: one stamp factory, one field projector, shared worktree resolution internals, both exchange-sink and tailer re-bind paths carry the full affinity group, and the reserved `session_affinity` launch field is the sole subprocess/shared-proxy carrier. Fixtures align with fail-closed canvas affinity. The only substantive gap is canvas↔worktree coherence at `resolve_run_canvas` before the write-once stamp (M1). Fix M1 (or document intentional cross-worktree pairing) before treating placement identity as fully trusted; m1 is hardening.
