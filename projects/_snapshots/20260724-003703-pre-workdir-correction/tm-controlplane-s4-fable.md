---
title: S4 delta-verify round 2 + max-review triage (controlplane-s4-watch @ 7054d439)
reviewer: fable (transport-matters:general:1:2.3)
date: 2026-07-12
verdict: ISSUE — none of the five in-scope max-review fixes exist at 7054d439; the named HEAD is byte-identical to the commit those defects were adjudicated on. Triage of N2/N3/N5/L1–L8 below.
---

# 1. Fix-landing verification: MISSING ALL FIVE

7054d439b85c92396b26ceb90e488a7af2e648fd is the same commit I delta-verified and adjudicated earlier today. A commit hash pins content; the claimed fixes cannot have "landed on" it. Verified each site firsthand at HEAD, tree pristine:

- **B2 (retry only on ConnectError): NOT LANDED.** run_proxy.py still has `except httpx.RequestError` at both call sites (lines 197, 219) — the exact broad guard adjudicated as the B2 defect. No idempotency key either.
- **M1 (commit-time watermark): NOT LANDED.** `wire_exchange.created_at` still `DEFAULT now()` (0008_wire_store.py); latest migration is the pre-existing 0013; `GET_COMPLETED_WIRE_TURNS_FOR_OWNER_SQL` unchanged.
- **Med1 (unwatch buffer purge): NOT LANDED.** `_unwatch_serialized` still pops the target and never touches `watcher.buffer`; no purge site exists in watch.py.
- **Med2 (runtimeRouter extract): NOT LANDED.** `createRuntimeRouter` measures 153 lines at HEAD, exactly the adjudicated value.
- **M2-consumer (dedupe): NOT LANDED as anything new.** The only consumer-side guard is the bounded 2048 `OrderedDict` that was already in 7054d439 (it was the F7 fix from the first correction round) — the mechanism M2 showed is insufficient against replays older than the window. Nothing was added.

Exhaustively checked for a mislaid commit: `git worktree list` shows this checkout only; no `origin/controlplane-s4-watch` exists; `git log --all --since` shows only docs commits on main after 7054d439; no sibling transport-matters clone or worktrees directory on disk carries anything newer. If a builder reported these fixes as landed, that report is false — there is no correction commit to review.

# 2. New-hazard check

Vacuous: no new edits exist at HEAD, so no new hazard. The branch remains in the state my adjudication described (B2/M1/Med1/Med2/M2 defects present; B1 now owner-deferred to S5, not re-litigated).

# 3. Triage of MAX's additional findings (N2, N3, N5, L1–L8)

All verified against the code before disposition. "Fold-in" means: cheap, rides the correction commit that is already required for §1; not independently merge-gating.

| id | disposition | reason |
|---|---|---|
| N2 | **Fold-in** (S4-introduced, real race) | `aclose` takes neither `_registry_lock` nor the watcher-operation lock, so a registration suspended on the audit await can complete after close — but the process is in lifespan teardown, so the zombie entry is inert. One-line `_closed` re-check in `_watch_serialized`'s registration block closes it; not worth gating merge alone. |
| N3 | **Fix now, rides M1** (S4-introduced query) | Correct: only `(run_id, ts)` / `(session_id, ts)` indexes exist, and the correction made catch-up periodic (every 1,000 live exchanges per feed), so the unindexed `created_at` scan is now recurring, not reconnect-only. The M1 watermark fix already requires a migration; the index is one line in it. |
| N5 | **Defer** (S4-introduced coupling) | Audit awaits under the global `_registry_lock` do couple all workspaces to audit latency, but the audit pool shares fate with the DB the whole API needs, the overflow path now degrades to durable catch-up (verified in round 1), and the fix (audit outside the lock or per-workspace locks) is a real redesign. Follow-up hardening, not a merge gate. |
| L1 | **Fold-in** (correction-introduced hygiene) | `test_watch_corrections.py` imports `_engine`/`_principal`/`_run`/`_until` from a sibling test file — an undeclared support module per api/CLAUDE.md's shared-test-support carve-out. The Med1 fix touches these tests anyway; extract the fakes/builders to a named support module then. |
| L2 | **Must-address with the pending fixes** (S4-introduced) | watch.py is at 695/700. The required B2/M1/Med1/M2 edits add code to it, and the repo rule is refactor **before** adding to a file at the cap — so the pending correction commit must split watch.py first (natural seams: feed consumption, delivery, registry lifecycle). Not optional once any fix lands. |
| L3 | **Defer** (S4 design tradeoff) | Requiring both sources keeps the shared per-workspace feed uniform across watchers with different event sets; the availability coupling is real but v1-acceptable. Document, revisit if single-source subscriptions become a need. |
| L4 | **Defer** (product decision) | 4-char run refs can collide; whether push carries a longer ref or the full id is a CONTROLPLANE.md product call, not a code defect. |
| L5 | **Defer / no change** | MAX's own evidence (40/100, failure-only auditing tested as intentional, locked design says failure audit only) says this is working as designed; at most clarify the "every action" wording. |
| L6 | **Defer** (cosmetic) | `is_watching` is a reasonable test inspection accessor; the unconsumed `GatewayActivityRun.needs_you` field was already a note in my round-1 review. Delete or consume opportunistically. |
| L7 | **Fold-in, docs-only** | The two locked sources genuinely disagree (event topology: all-SSE vs tm_events for turns; retry: keep-and-retry vs never-retry). The B2 fix changes retry semantics again — reconcile both documents in that same commit, naming CONTROLPLANE.md authoritative. |
| L8 | **Defer** (pre-existing binding nullability, S4-added strict parser) | A bindingless finalize drops the live signal without a catch-up marker, but the periodic cursor advance and reconnect catch-up bound the delay, and bindings normally survive finalize. Cheap hardening if desired: treat a wire-typed payload that fails field validation as a catch-up trigger. |

**Must-fix-before-merge list, net:** the five §1 fixes (still owed), plus L2's watch.py split (forced by the 700 rule the moment those fixes touch the file), plus N3's index riding the M1 migration. Everything else folds in opportunistically or defers with the reasons above.

# 4. Builder trust verdict (this correction round)

**Withheld-at-low.** There is no craftsmanship to assess: the correction round this brief describes does not exist in the repository. The trust-relevant fact is the gap between the claim and the tree — five named fixes were represented as landed on a specific hash that provably cannot contain them (it is the very commit the defects were adjudicated on), and no unpushed commit, branch, or worktree anywhere on this machine holds them. If the builder self-reported completion, that is a false completion report, which is categorically worse than a defective fix: defects cost a review cycle, false completion claims poison the delegation loop that lets anyone trust a green status. Recommendation: do not extend sizeable scope until the builder produces the actual commit and it passes delta-verify; treat any future "landed" claim from this builder as unverified until a hash is independently checked. (For contrast: the first correction round at 7054d439 itself was genuinely excellent work — the failure here is in the reporting of the second round, wherever that report originated.)

# Round-3 delta-verify (7054d439..abe9d033, 2026-07-12)

Two commits: 8674007 "refactor(controlplane): split watch registry state", abe9d03 "fix(controlplane): harden watch replay and delivery". **Verdict: clean — all five in-scope fixes genuinely landed, split cohesive, no new hazard found.** Gates firsthand: pytest 2023 passed (fresh-DB migrations included), ruff format/check + mypy clean on 503 files, @tm/runtime vitest 162/162. Tree pristine at abe9d033.

## 1. The five fixes

- **B2 — LANDED, on the retry paths, not cosmetic.** `_request_http`/`_open_http_stream` now map only `httpx.ConnectError` (provably no side effect) to retryable `GatewayUnavailableError`. `deliver_watch_nudge` wraps every other `httpx.RequestError` — ReadTimeout, RemoteProtocolError — as `GatewayResponseError(502, "outcome is unknown after the request was sent")`, which `_flush` drops-and-audits instead of retrying; gateway 5xx likewise reclassified to non-retried. The other four `_request_http`/`_open_http_stream` call sites (forward_http, read/stream_workspace_activity, forward_sse) each got explicit handlers preserving their old idempotent-GET semantics, so the ambiguity classification is scoped to the one path with side effects. Three new tests pin ambiguous-no-retry, ConnectError-retries, 5xx-no-retry. CONTROLPLANE.md documents the classification.
- **M1 — LANDED, deeper than the suggested margin heuristic.** Three coordinated parts: migration 0014 flips `created_at` default to `clock_timestamp()`; the UPSERT refreshes `created_at` to `clock_timestamp()` exactly on the NULL→NOT NULL `response_id` transition (so the column is a completion watermark — provisional insert, finalize bump, replay stable, tested); and an advisory-lock protocol (`WIRE_COMMIT_WATERMARK_LOCK_KEY`): `write_wire_exchange` takes the exclusive xact lock immediately before the exchange upsert (heavy blob/set writes happen before it, so the serialized window is only the row tail through commit), while `wire_replay_cursor` and `completed_wire_turns_since` take the shared side. Invariant: any watermark below a cursor was committed and visible when that cursor was read, so a row can never surface later behind the fence — the double-fault loss case is structurally gone, not narrowed. Blocking behavior tested with a real lock holder.
- **N3 — LANDED** in the same migration: partial index `(created_at, exchange_id) WHERE response_id IS NOT NULL`, matching the catch-up query's predicate and sort exactly. Migration ordering sound: 0014 revises 0013, fresh-DB apply + downgrade + re-upgrade round-trip tested, migration-head assertions updated across the suite.
- **Med1 — LANDED, thorough.** `retain_active_facts` purges the buffer on unwatch AND on failed-delivery restore, and `unwatch` now takes the new `_serialize_delivery` lock so it waits out an in-flight flush. Three tests: purge on unwatch, in-flight failed facts not restored post-unwatch, unwatch waits for in-flight delivery before reporting removal.
- **Med2 — LANDED, mechanical.** `createRuntimeRouter` is now a 7-line composer over `registerRunRoutes` (~122 lines) and `registerTerminalRoutes` (~28); route bodies moved verbatim.
- **M2-consumer — LANDED, deeper than asked.** `_consume_wire_exchange` rereads the durable owner-scoped row (`completed_wire_turn`, new single-row query sharing the extracted `_COMPLETED_WIRE_TURN_OWNER_PREDICATE`) before emitting, and drops any signal whose watermark is behind the feed cursor — stale replays die on the cursor check regardless of the 2048 dedupe window, and NOTIFY payload fields are demoted to routing metadata (a spoofed payload run_id/turn_index is ignored in favor of the durable row, tested). This also resolves L7's substantive half: the code now honors the Activity-contract rule that durable state is reread before acting, and CONTROLPLANE.md declares itself the authoritative WATCH contract over the older design notes.

Fold-ins landed too: **N2** (`aclose` takes the registry lock; the post-readiness recheck now also checks `_closed`; shutdown-vs-suspended-registration test with a blocking audit sink), **L1** (fakes and builders extracted to `watch_test_support.py`, a named shared support module — both test files import from it), **L7** (CONTROLPLANE.md supersession note plus the retry-classification and two-path topology paragraphs).

## 2. Split cohesion (L2)

Cohesive, not cosmetic. `watch_registry.py` (81 lines) owns the pure in-memory vocabulary — `Watcher`, `WorkspaceFeed`, `WatcherOperation`, plus the side-effect-free rules `target_events`, `retain_active_facts`, `remember_exchange` — a genuine models-and-domain-core seam with no I/O. `watch_test_support.py` (177 lines) removes the test-fixture weight. watch.py sits at 691 after absorbing ~60 lines of new engine logic, so the extraction bought real room rather than gaming the number; caveat recorded: headroom is thin again (691/700), and the next slice (S5 loop suppression) will force the next natural extraction (delivery/flush or feed consumers). The engine file still owns orchestration only, which is defensible ownership.

## 3. New-hazard sweep

None found. Lock ordering is consistent (watcher-op → delivery → registry everywhere; `_flush` takes delivery → registry; no inversion, no path acquires registry before either). `aclose` under the registry lock cannot deadlock with a flush (flush's registry acquisition is ordered after delivery, which aclose never takes). The advisory-lock reasoning was checked both directions, including the subtle case of a watermark landing between a catch-up's max-returned row and its read time (impossible: it would have been committed and visible to that query). `completed_wire_turn` correctly needs no watermark lock — NOTIFY only fires post-commit. Live signals arriving before the feed baseline or behind the cursor are fenced intentionally (watch starts "now"). Cost accepted knowingly: all wire writes now serialize a short exclusive window cross-instance, and each live turn costs one indexed single-row read. Nits only: `watch_test_support` exports underscore-named helpers (allowed by the privacy rule, but public names would suit a support module); registerRunRoutes at ~122 lines is fine today but is the next split candidate.

## 4. Builder trust (this round)

**High for the work product.** Every claimed fix landed and matches the triage exactly; two of the six went beyond the prescription to the structurally correct depth (durable reread instead of consumer-side patching; advisory-lock watermark instead of an overlap margin); tests attack the actual race surfaces (blocking audit sink for the shutdown race, in-flight-delivery-vs-unwatch interleavings, spoofed NOTIFY payload, migration round-trip from an unmigrated DB, watermark-refresh-exactly-once); scope discipline held (B1 untouched per the owner deferral, deferred N5/L3–L6/L8 left alone). The reporting failure from the previous round remains a process fact — this round restores confidence in the builder's engineering, and delegation of sizeable scope is reasonable again provided completion claims keep being verified against a hash, which this warroom now does as standard practice.
