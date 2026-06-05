# S1b review — opus (domain / contract / trust-boundary / write-once / STEP-0 lens)

Reviewer: opus architect, multilaunch warroom. READ-ONLY, no gates run (grok owns the
authoritative gate). Tree verified pristine before and after (`git status --porcelain` empty,
HEAD `119f520d` unchanged).

Target: `git diff 40c82e45..119f520d` — single commit `119f520d feat(session): thread trusted
canvas affinity`, 50 files. Plan: `~/.mdx/projects/tm-s1b-scout.md`. S1a context:
`~/.mdx/projects/tm-s1a-review-opus.md`.

## Verdict (my lens)

**Blockers: 0 · Majors: 0 · Minors: 0 (S1b-introduced) · Builder-trust: TRUST (strong).**

Two pre-existing backfill observations noted below (carried from S1a, NOT introduced by this
diff). A background `/code-review` posted 5 findings against a wider range (`d7bfb9ac..HEAD`);
I adjudicated all five (§7) — 3 are false, 2 are the pre-existing backfill items.

## 1. CROWN — PROVEN: live canvas launch stamps the full 8-field group on the first session

Traced browser → capture_rpc → resolution → SessionBinding → build_session → UPSERT and it holds
end to end, every value sourced from server-resolved Space records, never request strings:

- **Request boundary sanitize then trusted install.** `PrepareCaptureRequest.to_domain`
  (`capture_rpc_routes.py:184`) calls `affinity_launch_fields(self.launch_fields, None)` — strips
  every caller-supplied affinity key AND the reserved `session_affinity` carrier before anything
  server-side runs. `_resolved_domain_request` then, for a `canvas_id` request, calls
  `resolve_run_canvas`, replaces `directory`/`space_id`/`worktree_id`/`canvas_id` from the server
  result, and installs the trusted carrier via `affinity_launch_fields(domain.launch_fields,
  canvas_launch.affinity)` (`:329-347`).
- **Snapshot is server-built.** `resolve_run_canvas` (`launch_resolution.py:71-105`) resolves the
  worktree through the Space store, fetches the Canvas via `get_canvas(rest_caller(resolved.
  space_id), canvas_id)`, and constructs the stamp with `build_session_affinity_stamp(resolved,
  canvas)` — id/name/parent/paths/branch all from `ResolvedWorktree` + `CanvasRecord`.
- **Carrier survives the subprocess/shared-proxy boundary.** `launch_fields` → `Settings.
  launch_fields` → `build_proxy_run_binding` → `bind_trusted_affinity` (sets lifecycle
  `space_id`/`worktree_id`) and the carrier is retained. `launch_run_context` decodes it into
  `RunContext` via `**trusted_binding_affinity(binding)`.
- **Typed handoff, no dynamic extras.** `RunContext` and `SessionBinding` (`base.py:61-98,148-171`)
  declare all 8 fields explicitly. `ClaudeAdapter.bind`/`CodexAdapter.bind` both copy
  `**affinity_fields(run)` (one DRY helper, no hand-copied field list). `register_owned_cursor`'s
  `model_copy` strips generic launch fields then re-applies `**affinity_fields(session_binding)`
  last — the strip-then-reapply the plan §148 warned about is correct. `register_session_cursor`'s
  rebind rebuilds `RunContext` and the `model_copy` both carry `**affinity_fields(binding)`, so
  affinity survives the second bind.
- **Write-once still holds.** `_binding_affinity` (`ingest.py:102-108`) returns 8 nulls when
  `canvas_id` absent, else `validate_affinity_group` → full stamp; a partial group raises before
  SQL. The S1a single-sentinel UPSERT is unchanged. No path lands a partial/mixed group.

**Crown test** `test_launch_stamps_canvas_identity_on_first_session` (parameterized claude+codex):
real Space service + test DB, creates a Canvas whose `anchor_worktree_id != selected_worktree`
(proves §5), sends opaque selectors + forged affinity + forged carrier, drives the real
`_resolved_domain_request` → proxy binding → `register_owned_cursor` → `SessionWriter.submit`, then
reads the row via `AsyncSessionDao.get_session` and asserts every affinity field equals the
server-resolved stamp — **before any backfill runs**. Red at base (threading absent → all-null).

## 2. RULING (fail-closed) — ENFORCED

`_resolved_domain_request` (`:314-321`): `launch_kind is CANVAS` with any of
`space_id`/`worktree_id`/`canvas_id` absent raises `canvas_affinity_required` (400). No
`root_canvas_id` substitution anywhere on the launch path — `root_canvas_id` is used only in
historical backfill. A second guard (`:322-328`) rejects a stray `canvas_id` without
space/worktree even on non-canvas kinds. Service/detached (`launch_kind != CANVAS`, no
`canvas_id`) skip resolution and stay nullable. Confirmed.

## 3. Trust boundary — all four sub-points hold

- **Sanitize before install:** `to_domain` strips at the request boundary before the sole trusted
  writer (`_resolved_domain_request`) installs its stamp. Forgery test asserts
  `request.launch_fields == {}` after `to_domain`.
- **canvasId forces resolution even with an explicit directory:** the `if domain.canvas_id is not
  None` branch runs first and overwrites `directory = Path(resolved.cwd)`, so a caller directory
  cannot bypass resolution (§3 chose overwrite over reject — acceptable per plan).
- **worktree_in_space in BOTH branches:** `resolve_launch_worktree` (`service.py:303-325`) now
  calls `_require_worktree_in_space` in the `space_id is None` branch AND the explicit `space_id`
  branch. This closes the exact gap the scout §4 flagged ("explicit branch only verifies the Space
  exists").
- **Canvas not pinned to resolved worktree:** `get_canvas` (`service.py:236-247`) requires the
  Canvas's `anchor_worktree_id` to be in the resolved Space (cross-space Canvas → `space_mismatch`)
  but does NOT require `anchor_worktree_id == resolved.worktree_id`. §5 satisfied; the crown test's
  differing anchor proves it live.

## 4. STEP-0 — clean, zero behavior change, zero duplication

`addon_runtime.py` 699 → 633 lines (under 700). The owned-binding cluster
(`build_proxy_run_binding`, `launch_run_context`, `register_owned_cursor`,
`register_owned_cursor_safely`) moved to `owned_transcript_binding.py` (111 lines). No extracted
symbol is redefined in `addon_runtime.py`; it re-exports them via `import X as X` facade so existing
callers/tests keep their import path. Backward-compat preserved, DRY intact.

## 5. Cross-component contract — every seam carries canvasId

`createRunFingerprint` (`runManagerSupport.ts:51`, idempotency conflict on changed Canvas),
`prepareCaptureBody` RPC JSON (`CaptureRpcClient.ts:168`), `PrepareCaptureInput`
(`ports.ts:61`), `transport.ts` POST body + `CreateCapturedRunInput` (`:214,286,329`),
`PrepareCaptureRequest`/`CapturedRunRequest` (Python). No seam drops the field. TS contract tests
assert each hop; the Python crown test proves the end-to-end persistence.

## 6. Builder-trust: TRUST (strong) — supports large delegation

gpt build; Stuart is gauging delegation.

- **Craftsmanship:** the `build_session_affinity_stamp` factory single-sources the stamp for launch
  AND backfill (scout §338 DRY), one `affinity_fields` helper across both adapters + tailer +
  ingest, the strip-then-reapply trust pattern is exactly right, fail-closed is explicit, STEP-0
  extraction is clean with a compat facade.
- **Test rigor:** crown test is a real end-state proof (test DB, real Space service, forged inputs,
  asserts server values before backfill, red-first, both harnesses). Forgery test proves BOTH
  sanitize-at-`to_domain` and that server-installed affinity reaches declared binding fields — and
  asserts all 8 names are in `SessionBinding.model_fields`.
- **Spec + reuse fidelity:** followed the scout plan precisely (reused `ResolvedWorktree`,
  `get_canvas`, `SessionAffinityStamp`, the `launch_fields` carrier; no parallel affinity env var;
  no second Canvas payload).
- **Shortcuts:** none in my lens. Scope discipline is a positive signal.

## 7. Adjudication of the background `/code-review` (range d7bfb9ac..HEAD)

1. *"Live ingest strips identity → NULL affinity until restart."* **FALSE.** The crown test proves
   a live canvas launch persists the full group on the first session with no backfill. The reviewer
   read the `affinity_launch_fields(..., None)` strip but missed the `**affinity_fields(
   session_binding)` re-apply on the same `model_copy` — the exact trap plan §148 named.
2. *"Backfill has no per-row error isolation."* **PRE-EXISTING S1a**, not introduced here — the
   `for row in rows` loop with no try/except existed at base `40c82e45`. Low severity, startup-only
   best-effort path, out of the S1b crown scope. Worth a future hardening ticket, not an S1b defect.
3. *"Backfill get_canvas is N+1."* **PRE-EXISTING S1a** — `get_canvas(...,
   resolved.root_canvas_id)` was already there at base; S1b only swapped the inline stamp
   construction for the shared factory. Same low-severity startup-path note.
4. *"affinity_from_launch_fields is dead code."* **FALSE.** Production callers are
   `trusted_binding_affinity` and `bind_trusted_affinity` (`shared_proxy/binding.py:62-77`), both on
   the live launch path via `owned_transcript_binding`.
5. *"SessionBinding has no canvas_id field; assert is unreachable."* **FALSE.** `base.py:74`
   declares `canvas_id` (and 7 siblings); the forgery test asserts all 8 in
   `SessionBinding.model_fields`. The reviewer misquoted the test assertion `not hasattr(binding,
   SESSION_AFFINITY_LAUNCH_FIELD)` (the reserved carrier key `"session_affinity"`) as
   `not hasattr(binding, 'canvas_id')`.

**Nit (not counted):** `ingest.py:107` `assert stamp is not None` is type-narrowing stripped under
`python -O`; `stamp` is genuinely non-None when reached (the `canvas_id`-present guard precedes it),
so no `-O` AttributeError. Documented S1a nit, pre-existing.

## Scope note

Verdict scoped to crown / ruling / trust-boundary / write-once / STEP-0 / cross-component / DRY.
Deferred to grok: `just check` / `just test` / migration-smoke. My lens found the slice sound.

---

## Delta re-verify — correction `5d343637` "enforce canvas anchor affinity"

Range `git diff 119f520d..5d343637` (6 files). Tree pristine before and after (HEAD `5d343637`,
`git status --porcelain` empty). **Delta clean — all three fixes land, ruling holds, base APPROVE
unregressed.** Note this correction INVERTS the base review's §5 stance (Stuart's ruling changed to
"one Canvas → its anchor Worktree only"); the code and tests now enforce that, correctly.

1. **M1 — canvas_worktree_mismatch enforced before the stamp.** `resolve_run_canvas`
   (`launch_resolution.py:100-105`) now raises `canvas_worktree_mismatch` (409) when
   `canvas.anchor_worktree_id != resolved.worktree_id`, placed after `get_canvas` and BEFORE the
   `return ... build_session_affinity_stamp(...)` — no stamp is built on the reject path. The raise
   is an `HTTPException` (not `SpaceCrudError`), so it propagates past the `except SpaceCrudError`
   correctly. Test genuinely inverted: `_canvas_for` now defaults `anchor_worktree_id =
   resolved.worktree_id` (the old hardcoded `UUID(int=100)` acceptance is gone), so the existing
   positive path stamps a coherent Canvas; the new `test_prepare_rejects_canvas_from_another_worktree`
   supplies `UUID(int=100)` and asserts `409` + `code == canvas_worktree_mismatch` + `prepared == []`
   (rejected before the run spawns). Red-first: at `119f520d` there is no check, so the reject test
   would see `200`. The crown test was correctly collapsed to one coherent Worktree
   (`anchor_worktree.worktree_id` launched against itself, `assert anchor == worktree`) — otherwise
   the new rule would raise inside it; it still proves the 8-field first-session stamp.

2. **m1 — overlay is now carrier-authoritative.** `register_owned_cursor`
   (`owned_transcript_binding.py:95`) overlays `**trusted_binding_affinity(binding)` (decoded from
   the trusted launch carrier) instead of `**affinity_fields(session_binding)` (adapter output); the
   now-unused `affinity_fields` import was removed. New `test_owned_transcript_binding.py` drives an
   `AffinityDroppingAdapter` whose `bind` emits zero affinity and asserts the registered binding
   still equals the carrier stamp — fail-closes on the carrier independent of adapter output.
   Red-first: under the old `affinity_fields(session_binding)` overlay the dropping adapter would
   null the group.

3. **m2 — single carrier decode helper.** `shared_proxy/binding.py` routes both
   `trusted_binding_affinity` and `bind_trusted_affinity` through one `_trusted_stamp(binding)`
   helper (was two direct `affinity_from_launch_fields` call sites); `SessionAffinityStamp` imported
   under `TYPE_CHECKING` for the return annotation. DRY, no behavior change.

No regression to the base guarantees: write-once SQL, sanitize-at-`to_domain`, the fail-closed tuple
check, and both `worktree_in_space` branches are untouched; the delta only tightens the
Canvas↔Worktree binding.
