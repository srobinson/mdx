# S2 typed run inventory — Opus review

Range: `1c6f0645..3cf2e2c0` (feat/multi-launch, "add typed run inventory"), 5 files, backend-only.
Reviewer: `multi-launch:general:1:3.5` (claude-opus). READ-ONLY.
Tree verified pristine at HEAD `3cf2e2c0` before verdict (empty porcelain, worktree on feat/multi-launch).

Lens: correctness + contract + STEP-0 fidelity + builder-trust.

(Note: this file previously held a review of a different, earlier "S2" claims/leases slice
`d7bfb9ac..7df0d907`, 107 files — unrelated to this range. Overwritten per brief, which named
this exact output path.)

## Verdict

**0 blockers, 0 majors, 1 minor.** Ship after (optionally) closing the minor. Builder-trust: **HIGH**.

---

## 1. EXHAUSTIVE PAGING — PROVEN CORRECT

`list_runs` (controlplane_gateway_runs.py) loops `while True`, extends `runs` with each
page's items, returns `tuple(runs)` only when `next_cursor is None`. No single-page truncation.

Progress is genuinely enforced and infinite loops are impossible:

- `_GatewayRunListPage.validate_next_cursor` rejects any cursor that is not ASCII-decimal
  (`not value.isascii() or not value.isdecimal()` → ValueError → caught in `_typed_run_request`
  GET path → `GatewayResponseError "gateway run response was invalid"`). So `int(next_cursor)`
  can only ever see an ASCII non-negative integer. Unicode-decimal, empty, negative, and opaque
  cursors are all rejected.
- `if next_offset <= cursor_offset: raise GatewayResponseError("...cursor did not advance")`.
  A repeated or non-increasing cursor cannot loop and cannot return a partial inventory.
- Contract-verified against the Gateway: `runtimeRouter.ts:159-163` emits
  `nextCursor = nextOffset < items.length ? String(cursor + limit) : null`. The cursor is a
  monotonic decimal offset (+limit each page), so the Python decimal-validator and the
  `<=` progress guard exactly match producer semantics. No off-by-one over-fetch: an exactly-full
  final page (`nextOffset == items.length`) yields `null`, so no wasted trailing request.

Tests red-first (whole method is new) and assert observable outcomes:
- `rejects_a_repeated_cursor`: `pytest.raises(GatewayResponseError, match="cursor")` **and**
  `len(urls) == 2` — proves no infinite loop, no partial success. Exercises the `<=` guard.
- `rejects_an_invalid_success_response`: `{"runId": "run-invalid"}` (no `state`) →
  `GatewayResponseError, match="response was invalid"`. Confirmed a real red assertion:
  `GatewayRunView.state` is a required field (run_models.py:90), so validation genuinely fails.

## 2. OWNER ISOLATION — PROVEN CORRECT

- `owner` is required and blank-guarded (`if not owner.strip(): raise ValueError`).
- `base_query` carries `owner` and every page merges `base_query`, so owner is on **every**
  request, never relying on the Gateway `ownerFromQuery` → `local` fallback.
- `space_id`/`worktree_id` are typed `SpaceId`/`WorktreeId` at the port; empty strings cannot
  reach the query (`if not encoded: raise ValueError`), so a blank filter can never silently
  broaden the inventory via the Gateway `nonEmptyString` "empty == absent" behavior.
- Test `preserves_owner_and_filters_on_every_page` asserts the exact second-page URL keeps
  `owner` + both identity filters and adds `&cursor=100`.

## 3. STEP-0 FIDELITY — PROVEN, NO BEHAVIOR CHANGE

- `create_run` body dict moved **byte-identical**; `RunRouteProxy.create_run` now delegates.
- `terminate_run`: same target `run_route_path(run_id, "/terminate")`, same `_GatewayRunResponse`,
  same `404 → None`. The old generic `_run_view_request` helper (terminate-only caller) is
  removed and inlined — no lost behavior.
- `_typed_run_request` moved verbatim; GET→`GatewayUnavailableError`, non-GET→
  `GatewayOutcomeUnknownError`, `>=400`→`GatewayResponseError` with structured code all preserved.
- Error-message equivalence checked: old `self._gateway_url` vs new
  `target_origin(transport)` = `target_http_url("","").rstrip("/")`. Because
  `normalized_gateway_url` strips the trailing slash and `target_http_url` round-trips
  scheme/netloc/path losslessly, the two render **identically** (empty-path and base-path cases).
  No observable message change.
- `run_route_path`/`_run_request_error` moved and shared (run_proxy now calls
  `gateway_runs.run_route_path`) — no duplication.
- `GatewayRunView` **not** expanded (still runId/state/name/agentId; the test's extra
  spaceId/worktreeId are ignored, not persisted). `RunManagementPort` **extended** with
  `list_runs`, not a new delete-specific interface. `run_proxy.py` = **595** lines (< 700).
- Import DAG clean: `space.models` imported only under `TYPE_CHECKING` in both
  `activity.py` and `controlplane_gateway_runs.py`; no runtime cycle, no adapters→session
  back-edge class of problem.

## 4. BUILDER-TRUST (gpt build) — HIGH

- **Craftsmanship:** clean extraction mirroring `controlplane_gateway_reads.py` transport
  Protocol; `run_proxy.py` 690→595; delegation is thin and faithful.
- **Reuse fidelity:** extended the existing port, moved (not duplicated) shared helpers,
  reused `GatewayRunView`. No parallel registry/filter/runner invented.
- **Test rigor:** all 5 planned tests present, red-first, observable (exact URLs, run ids,
  exception type + `match`). Correctly models the Gateway offset cursor.
- **Shortcuts:** none material. `FakeGateway.list_runs` `assert owner == "local"` is test support.
  The empty-string guard on typed IDs is unreachable-but-harmless defensiveness.

Trustworthy for sizeable delegated scope.

---

## MINOR (1)

**M1 — cursor-shape validator is unproven (test-coverage gap).**
Plan test #5 promised "malformed items **or cursor shape** raise `GatewayResponseError`", but
`rejects_an_invalid_success_response` only covers a malformed **item** (missing `state`). The
`validate_next_cursor` decimal validator — the exact guard that stops a non-decimal/opaque
Gateway cursor from reaching `int()` — has no direct test. The repeated-cursor test exercises the
`<=` offset guard, not the validator. Add one case: a page with `"nextCursor": "abc"` (or `""`)
asserting `GatewayResponseError, match="response was invalid"`. Craftsmanship, not correctness —
the validator is present and correct; it is simply unwitnessed.

(Also unwitnessed, lower value: blank-`owner` and empty-filter ValueError guards. The empty-filter
guard is effectively unreachable for typed IDs.)
