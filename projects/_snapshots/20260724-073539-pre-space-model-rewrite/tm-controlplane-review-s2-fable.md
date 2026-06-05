---
title: S2 control-plane service + observe verbs + audit — adversarial review (Fable)
branch: controlplane-s2-observe @ 3d36f0b
scope: git diff main...controlplane-s2-observe (25 files, +1496/-16)
date: 2026-07-11
process: code-review high effort (8 finder angles, recall-biased verify) + code-hygiene lens
verdict: no blockers; 9 minors + 1 low; builder trust HIGH (unchanged vs S1)
---

# Verdict

No correctness blocker. The five focus areas of the brief hold (evidence below). Nine
minor findings and one low. Tree verified pristine at 3d36f0b before and after review;
review was read-only.

# Brief focus areas — evidence

1. **Conversation projection: CLEAN, one Codex edge (F1).** Built once in
   `controlplane/conversation.py` over `project_timeline` → MessageItem-only, role
   {user, assistant}, IR text-part join. Verified identical for both harnesses by the
   parametrized fixture test, which drives the REAL `ClaudeAdapter`/`CodexAdapter`
   normalize → `build_event` pipeline over `claude_transcript.jsonl` /
   `codex_rollout.jsonl` and asserts the same {turn, role, text} output. Cursor is
   sound: `turn_indices_by_seq` assigns a unique turn index per non-sidechain turn
   event, so a limit cut never splits a turn. Caps correct: per-message cap min'd with
   `MAX_CONVERSATION_CHARS // n`, total proven ≤ 12,000 by a test asserting the exact
   sum; `truncated` marker set on both selection and char truncation.
2. **Summary mode: CLEAN.** Same pipeline preset (`_summary_messages`: first genuine
   user turn after injected stripping + last 4 role-agnostic, value-equality dedup when
   they overlap), same caps. It reads only the timeline projection; forking from the
   activity wire is structurally excluded — `GatewayActivityRun` does not even model
   `initial_prompt`/`last_message` (pydantic ignores the extra wire fields), and
   nothing in `service.py`/`conversation.py` touches them. Edge: F5b.
3. **Roster / workspace_summary: CLEAN.** Fields per spec; state/tier consumed from
   the gateway wire, never re-derived (mapping verified byte-matched: the TS
   `activityStatusTier` exhaustive switch emits exactly the five Python Literal
   values). Gateway down → `busy_gateway` `ControlPlaneError`, audited, no crash
   (test-pinned). `GET_LAST_TURNS_FOR_RUNS_FOR_OWNER_SQL` is correct: owner+workspace
   scoped, `kind='turn'`, `is_sidechain=false`, latest non-null model; proven by the
   Postgres-backed read-store test (hidden foreign-workspace run asserted absent).
4. **Migration 0013: CORRECT, one naming break (F9).** Additive, chained 0012→0013,
   one-shape record {actor, verb, targets, text, mode, dispatch_id, per-target
   outcomes, timestamp} with jsonb-type CHECKs and a partial dispatch_id index.
   Applies fresh and downgrades (verified: migration smoke + fresh-migration test +
   audit-writer round-trip asserting column types, outcome order, tz-aware timestamp).
   Freeze-literals precedent honored inside the migration.
5. **Principal + DRY + size: CLEAN.** Every service/read method takes
   `ControlPlanePrincipal`; principal is minted server-side (owner from capture facts,
   workspace/role from the grant row) — no caller-supplied identity anywhere. All
   three new SQL statements double-gate owner AND workspace, so even a malicious
   gateway feeding foreign run_ids yields zero rows. All files ≤374 LOC. The unused
   `forbidden`/`delivery_failed` codes are the spec's declared vocabulary staged for
   S3+, not dead code.

Gates observed directly: pytest 148 (controlplane+session, incl. Postgres migration
and read-store scoping) + 15 (run_proxy, lifespan) passed; vitest `@tm/activity` 224
passed, `@tm/contract` 6 passed; `tsc --noEmit` clean both packages; `ruff format
--check` (491 files), `ruff check`, `mypy` clean on the CI scope (`src/`).

# Findings (ranked)

**F1 (minor, correctness edge) `api/src/transport_matters/controlplane/conversation.py` `_is_injected`** —
Injected-content stripping is 100% Claude-specific (raw `isMeta`/`isSidechain`/
`isCompactSummary`/`isVisibleInTranscriptOnly`). Codex framing is filtered only
incidentally via the adapter's `role=="developer"→"system"` mapping; a Codex rollout
variant that emits `<user_instructions>`/`<environment_context>` as a `role:"user"`
message (older/alternate formats do; the fixture models only the developer-role
variant) passes through as a genuine user turn, and `shape="summary"` then anchors on
that boilerplate as the "first genuine user turn". Also the wrong altitude and a
duplication: the same four-flag predicate already exists as
`isClaudeSyntheticUserRecord` in `packages/activity/src/adapters/transcriptRecords.ts`,
so the injected verdict now lives in two languages with no shared source; it belongs at
the timeline/adapter layer as a per-event verdict both surfaces consume.

**F2 (minor, consistency) `api/src/transport_matters/controlplane/read_store.py`
`workspace_sessions` + `service.py` `_sessions_by_run`** — Roster metadata and the
conversation timeline resolve "the run's session" differently. The CTE picks
root-preferred/newest (`controlplane_statements.py`); the roster join takes the FIRST
match in `list_session_views` order (`last_activity_at DESC`) with
`include_internal=True`, so a run with a recently active subagent child maps to the
CHILD row — RosterItem.name becomes the subagent description, workdir the child's,
while `conversation()` reads the root. The `limit=500` is also a correctness cliff (a
workspace beyond 500 sessions can drop an active run's row) and fetches 500 full views
to enrich ~5 runs. Fix at one seam: fetch sessions by the activity `run_ids` with the
same target-session selection the CTE uses.

**F3 (minor, drift hazard) `api/src/transport_matters/controlplane/activity.py:14`** —
The tier vocabulary is re-declared as a Python Literal and validated strictly, with no
cross-language contract test tying it to `ActivityStatusTier` in
`packages/contract/src/activity/wire.ts` (mapping verified matching today). When a
sixth tier lands in TS, `model_validate` rejects the whole activity response →
`GatewayUnavailableError` → every roster/workspace_summary in the workspace degrades
to a misleading `busy_gateway` while the gateway is healthy. `_summary_text` also
hand-indexes the five tier names a second time. Add a contract test (or tolerant tier
handling) so drift fails a build, not the runtime.

**F4 (minor, write amplification) `api/src/transport_matters/controlplane/service.py`
`_record`** — Every successful observe call (conversation/roster/workspace_summary)
awaits an `INSERT ... RETURNING` audit row inline on the read path.
`control_plane_actions` has no retention, cap, or partitioning; an agent polling
`roster()` every few seconds writes ~17k rows/day forever, and each pull-read pays a
Postgres round-trip of latency. CONTROLPLANE.md's audit section frames the record
around action verbs (text/mode/dispatch_id/receipts); auditing failed observes is
diagnosable gold, but successful pulls at per-call granularity deserve an explicit
decision: don't audit them, or write them off the response path.

**F5 (minor, cursor semantics) `api/src/transport_matters/controlplane/conversation.py`
`_cap_messages` + `project_conversation`** — Two edge defects at the pagination seam:
(a) an empty incremental poll returns `cursor=None`; a client that echoes the cursor
back then calls with `after_turn=None` and receives the entire tail feed again —
every idle poll re-dumps the conversation. Echo the caller's cursor (or omit the
field) on an empty delta. (b) `shape="summary"` composes before the `after_turn`
filter, so `conversation(run, shape="summary", after_turn=N)` silently drops the
first-genuine-user anchor the summary contract promises.

**F6 (minor, error contract) `api/src/transport_matters/controlplane/service.py`
`conversation`** — Caller-supplied `limit`/`max_chars_per_message` flow unvalidated
into `_bounded_limit`/`_bounded_message_cap`, which raise bare `ValueError`. That is
outside the `ControlPlaneError` vocabulary the skins will translate: `limit=0` from an
agent becomes an unhandled 500 with no audit row, where every other failure on this
surface is structured and audited.

**F7 (minor, error fidelity) `api/src/transport_matters/api/v1/run_proxy.py`
`read_workspace_activity` + `main.py:283`** — Three conflations at the gateway seam:
a gateway 4xx is laundered through `raise_for_status` into
`GatewayUnavailableError("gateway activity response was invalid")` (a 404/403 reads as
"gateway down"); a structurally gateway-less deployment (no `gateway_url`) and a
transient outage share the same `busy_gateway` code, so an agent cannot tell "retry
soon" from "never"; and `getattr(run_proxy_mount, "activity_reader", None)` on an
always-present frozen-dataclass field means a future rename silently yields permanent
`busy_gateway` instead of a loud startup error — guard the real optional
(`run_proxy_mount is None`) instead.

**F8 (minor, DRY) `api/src/transport_matters/session/controlplane_statements.py:12,49`** —
`s.workspace_slug || '/' || s.workspace_hash = %(workspace_id)s` is hand-inlined twice,
beside two existing copies in `dao_statements.py` (:183 as the projection alias, :220
as a filter — which is subtly LOOSER, also accepting a bare-hash match) and the Python
twin `workspace_key()` S1 just promoted. The workspace-identity format now lives in
five sites across two languages of SQL and Python with no shared fragment; a format
change makes control-plane reads silently return zero rows while the legacy path still
matches. Extract one SQL fragment constant.

**F9 (minor, conventions) `api/migrations/versions/0013_control_plane_actions.py:23` +
`controlplane/audit.py:10`** — `control_plane_actions` is the repo's only plural table
name; every existing table is singular, including sibling `control_plane_grant`
(0012). CONTROLPLANE.md spells it plural, so the doc codifies the break rather than
resolving it — surface to Stuart: rename table+doc to `control_plane_action` now
(pre-users, no migration debt) or accept the exception explicitly. Secondarily, the
public table constant lives in `audit.py` while the grant precedent homes it in
`controlplane/models.py`.

**F10 (low, hygiene) `api/src/transport_matters/controlplane/audit.py:36` +
`test_service.py` `_fixture_timeline`** — `details: dict[str, Any]` breaks the
api/CLAUDE.md rule "`Any` requires a comment explaining why" (sibling `service.py`
`_outcome` already uses the compliant `dict[str, object]`). The test's
`_fixture_timeline` re-implements the tailer's replay threading
(seq/model_hint/parent linkage) line-for-line instead of reusing the existing fixture
normalize helpers in `index/adapters/test_claude.py`, so the "byte-identical replay
linchpin" contract now has a second copy that can drift green. Three new tests also
add redundant `@pytest.mark.asyncio` under `asyncio_mode="auto"` where the repo norm
(and `test_service.py` itself) omits it.

# Refuted / noted, not findings

- A finder flagged `except OSError, TimeoutError, ...` in run_proxy.py as fatal
  Python 2 syntax — REFUTED firsthand: `requires-python >= 3.14`, venv is 3.14.5,
  PEP 758 makes it legal; the module parses clean and its tests pass.
- `last_turn_at` (max ts) and `model` (latest non-null) can come from different turns —
  deliberate best-effort; reporting NULL because the newest turn lacked a model would
  be worse.
- Session titles/cwd flow verbatim into `workspace_summary` text handed to a director
  LLM — a real same-workspace prompt-injection surface, same trust boundary, accepted
  by design; worth remembering when cross-workspace grants arrive.
- Gateway URL/port appears in audit `reason` and the run-proxy 503 body — loopback
  only, pre-existing shape.
- Even-split of the 12k conversation budget wastes budget on short messages — simple
  hard ceiling, acceptable.
- `GatewayWorkspaceActivity.items` unbounded — gateway is a trusted child process.
- Mixed pydantic-frozen vs dataclass idioms inside `controlplane/` — defensible
  (pydantic at the validating wire boundary), visible inconsistency only.
- Authz core verified CLEAN end to end: bearer→grant→principal server-minted;
  double-gated SQL scoping; psycopg-parameterized throughout; `%2F` path quoting
  correct; audit details carry counts only, never conversation text.

# Builder quality assessment (Stuart's standing request)

**Craftsmanship: strong, consistent with S1.** Clean package shape (ports as
Protocols, vocabulary in observe_models, policy in the service, adapters thin),
correct import direction (session/ never imports controlplane/), the TS side extended
at the existing "one tier authority" rather than a new mapping, and the conversation
projection landed exactly at the spec's altitude: once, over the normalized timeline,
provider-neutral.

**Test rigor: real.** The both-harness fixture test drives the REAL adapters through
normalize→build_event rather than hand-built rows; the read-store test runs against
Postgres and asserts the negative (foreign-workspace run invisible); the cap tests
assert exact totals; busy_gateway asserts the audit row. Weak edges: no cross-language
tier contract test (F3), the fixture loop duplicates the tailer (F10), and the
untested seams are exactly where the edge findings live (empty-poll cursor,
summary+after_turn, limit=0).

**Spec + reuse fidelity: high.** Summary preset, caps, cursor, roster fields,
busy_gateway, one-shape audit record with dispatch_id ready for the action verbs — all
as locked. The wire-forking prohibition is structurally enforced, not just followed.
Reuse map respected (project_timeline, AsyncSessionDao extended, existing route-path
helper, existing proxy seam).

**Shortcuts/gaps: the same S1 signature.** Local copies where a shared helper was one
grep away (F8 SQL predicate, F1 flag list, F9 constant home), edge semantics
unexamined at the new public seam (F5, F6, F7), and a convention not checked against
precedent (F9 plural). No overreach; scope tight to S2.

**TRUST VERDICT: HIGH — unchanged vs S1.** Second consecutive slice with zero
correctness blockers on a surface with real adversarial exposure (authz verified clean
end to end), spec-exact behavior, and genuinely load-bearing tests. The recurring
watch-item stands: DRY and repo-precedent checks trail the zero-tolerance bar, so
briefs should keep "search before writing" explicit and reviews should keep the
duplication pass.
