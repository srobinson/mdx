# Review: PR #420 `fix/codex-harvest-refusal-fast-fail`

- Repo: transport-matters, head `57099a40`, baseline `main` @ `b8983151`
- Scope: 4 commits, +892/-609 across 10 files, all under `api/src/transport_matters/`
- Reviewer: transport-matters:general:1:3.1
- Date: 2026-08-21

**Verdict: 0 Blocker, 0 Major, 5 Minor.** All four priority checks in the brief pass, and the
regression was verified empirically to fail without the fix.

---

## Verification performed

| Gate | Result |
| --- | --- |
| Worktree pristine before and after | `git status --porcelain` empty at both ends |
| `cd api && just check` | ruff format 781 unchanged, ruff check clean, mypy clean on 781 files |
| Affected pytest modules (46 tests) | 46 passed in 3.89s |
| Regression falsification | see below |

### The regression genuinely fails before the fix

`captured_turn.transport_refusal` was replaced at runtime with `main`'s semantics (status parsed
from `res.stop_reason` only) via a scratchpad-only pytest plugin, with no repo write:

```
FAILED test_codex_server_refusal_fails_fast_with_the_provider_reason
- the provider refused the turn for claude/gpt-5.2/a1 with HTTP 400: "The 'gpt-5.2' model is ..."
+ the delivery for claude/gpt-5.2/a1 matched 1 request(s), but no response IR was captured before the timeout
1 failed in 30.14s
```

The failure reproduces the reported bug message verbatim and burns the full 30s deadline. The test
drives the real `harvest_controlled_baseline` → `_wait_for_correlated_exchange` path, with a real
`transport.json` parsed through `TransportArtifacts.model_validate_json`
(`test_captured_turn.py:_install_capture_fakes`), `stop_reason="ws_close_1006"`, no response IR and
no transcript. It asserts the full raised message and `elapsed < 5.0`, not an intermediate predicate.

### Brief checks 1, 2, 4, 5, 6, 7

1. **Subsumption.** `http_error_status` had exactly one caller on main
   (`main:captured_turn.py:189`) and was never exported from `storage/__init__.py`. Reader deleted,
   caller migrated, no parallel path left. `HTTP_ERROR_STOP_REASON_PREFIX` still drives the writer at
   `exchange_recorder/artifacts.py:118`. Remaining `http_error_status` greps are the unrelated
   recorder symbol `tag_http_error_status`. **Pass.**
2. **Structural classification.** `extract_codex_model_rejection` returns `None` before touching
   `error.message`; the message is read only after `type`/`status`/`error.type` all match, and a
   non-string message degrades to `None` rather than to a non-refusal
   (`test_model_rejection.py:test_codex_model_rejection_accepts_a_missing_or_non_string_message`).
   Message text cannot influence classification. **Pass.**
4. **Import DAG.** `storage/base.py` gains `codex.protocol`, which imports only `codex.events`,
   `codex.json_utils` and `json_tags`; none reach storage. `storage/base.py` already imported
   `codex.events` on main, so no new edge direction. Codex frame structure stays owned by
   `codex/protocol.py`; `storage/base.py` delegates. No adapter imports storage. **Pass.**
5. **Deliverable 4.** `_recorded_outcome` returns `inconclusive` when the observation is absent or
   `unknown`, and the harness outcome otherwise. Freshness holds because `_verify_harness` returns
   `current` earlier whenever a scoped observation already exists, so any observation seen after the
   turn was written by that turn. **Correct**, but see Minor 3 for the untested half.
6. **Test extraction fidelity.** All 15 test functions on main survive across the two files; an
   AST-level body comparison found zero dropped tests and zero weakened assertions. HTTP refusal,
   client frame, near miss, unrelated (startup) exchange, both timeout halves, cleanup
   (`test_harvest_refuses_a_mismatched_capture_plan_before_launch`), malformed transport and grok
   fan-out all still assert what they did on main. One docstring was lost: Minor 4.
7. **Sizing.** `test_baseline_capture.py` 861 → 290, new `test_captured_turn.py` 699,
   `storage/base.py` 408, `codex/protocol.py` 452, `captured_turn.py` 296. No function over 150:
   longest are `_wait_for_correlated_exchange` at 109 and `_install_capture_fakes` at 122. **Pass**,
   though `test_captured_turn.py` sits one line under the hard limit with no headroom for the next
   test.

---

## Findings

### Minor 1 — the recorded-HTTP-response branch is unreachable in production
`api/src/transport_matters/storage/base.py:325`

```python
response_status = (
    None if transport is None or transport.response is None else transport.response.status_code
)
if response_status is not None and response_status >= 400:
    return TransportRefusal(status=response_status)
```

Both HTTP writers set `res_stats` and `transport.response` from the same `flow`, in the same block:
`exchange_recorder/__init__.py:278-279` and `exchange_recorder/__init__.py:495-500`. The writer at
`exchange_recorder/artifacts.py:113-118` stamps `stop_reason=f"http_{status_code}"` for exactly
`status_code >= 400`, the same predicate. So whenever this branch could fire, the `stop_reason`
branch below it fires too and returns the identical `TransportRefusal(status=...)`. The only caller
that reaches it is the hand-built model at `storage/test_transport_refusal.py:22`.

Deliverable 3 was subsumption of the HTTP branch into one owner. This adds a second HTTP decision
path inside that owner, and the test id `legacy-index-summary` labels the live recorder path as
legacy while it is the one production actually uses. Either delete the branch, or, if it is meant as
deliberate independence from the derived index summary, say so in the docstring and correct the test
id.

### Minor 2 — every capture failure is logged as a refusal
`api/src/transport_matters/harnesses/access_verification.py:143-144`

```python
except CapturedTurnError:
    logger.info("provider access verification turn refused for %s", harness_id)
```

`CapturedTurnError` has six raise sites in `captured_turn.py`: cancellation (`:140`), the refusal
(`:192`), an ambiguous match (`:210`) and three timeout messages (`:220`, `:225`, `:229`). Only one
is a refusal. A correlation timeout during access verification will now write a log line claiming
the provider refused, which is precisely the misattribution this PR exists to remove.

The exception is also discarded, and it is the object that now carries the provider's own sentence.
Bind it and log it: `except CapturedTurnError as exc:` with
`logger.info("provider access verification turn failed for %s: %s", harness_id, exc)`.

Routing all six to `_recorded_outcome` is defensible and matches the deliverable as briefed; only
the message is wrong.

### Minor 3 — the `inconclusive` half of deliverable 4 is untested
`api/src/transport_matters/harnesses/test_access_verification.py:193`

`test_a_refused_provider_reports_its_fresh_reason` covers a `CapturedTurnError` that has recorded
evidence (`unavailable` / `organization_access_disabled`). Nothing covers a `CapturedTurnError` with
no scoped observation, so the new branch's fall-through to `inconclusive` is never exercised.
`test_one_failing_harness_does_not_stop_the_others:225` looks like that case but raises
`RuntimeError`, which lands in the pre-existing generic handler at `access_verification.py:146`, not
in the new one. A second parametrization of the refusal test with an unchanged `after` snapshot
closes it.

### Minor 4 — the move dropped a rationale docstring
`api/src/transport_matters/test_captured_turn.py:560`

`test_correlation_timeout_names_which_half_is_missing` lost its docstring, present on main at
`main:api/src/transport_matters/test_baseline_capture.py:783-788`:

> Nothing arriving points at the launch, the proxy or the store. A matched exchange with no
> transcript points at the harness transcript. The live harvest reported the first message for the
> second condition, which sent debugging at the correlator rather than at the transcript.

The parametrize ids and `match` strings survive intact, so no assertion weakened. What was lost is
the field lesson explaining why the two messages are kept distinct, which is the same class of
knowledge the sibling test `test_a_refused_provider_fails_before_the_timeout` still carries in its
own docstring three functions later. Restore it.

### Minor 5 — four copies of the exchange-writing block in new helper code
`api/src/transport_matters/test_captured_turn.py:131`, `:170`, `:210`

The extraction commit created `_write_standard_exchanges`, `_write_grok_exchanges` and
`_prepare_capture_spec`, and left the same `request.raw` + `request.ir.json` + `response.ir.json`
triple written out four times: the startup exchange (`:222-228`), the owned exchange (`:139-152`),
the title exchange (`:154-168`) and the grok loop (`:176-186`). The variation is provider, prompt,
whether a response IR is written, and an optional transport blob, which is four parameters. One
`_write_exchange(dir, *, prompt, provider, response_ir, transport)` collapses all four. A refactor
commit whose purpose was structural cleanup is the right place to fix it.

---

## Explicitly not flagged

Per the brief: PEP 758 `except A, B:`, the deferred WebSocket handshake refusal path
(`persist_codex_handshake_failure`, which lands on `upgrade.response_status_code` and is correctly
untouched by the new reader), `model_dependence_assessed`, the absent cross-cell comparator, and
style the surrounding code does not already follow.

Also considered and dismissed: `transport_refusal` / `TransportRefusal` are not re-exported from
`storage/__init__.py`, but neither was `http_error_status` on main, so this matches prior art.
`transport_refusal(captured.transport, entry.res)` pairs artifacts and index stats from the same
exchange (`captured` is read per `entry` at `captured_turn.py:161`), so there is no misattribution
across a grok fan-out.

---

# Delta pass: `57099a40..4ced4e85` (2026-08-21)

Head now `4ced4e85`, +907/-628 across 10 files. Tree pristine before and after.
`cd api && just check` clean (ruff format 781 unchanged, ruff check clean, mypy clean on 781 files).
Affected modules: 46 passed in 3.84s, the same count as the previous head (Minor 3 added one
parametrization, Minor 1 removed one).

**All five findings closed. No regression found.**

| # | Closure | Evidence |
| --- | --- | --- |
| Minor 1 | Deleted | `storage/base.py` branch gone; only callers left are `captured_turn.py:189` and the test module, which dropped its `TransportHttpResponseArtifacts` import |
| Minor 2 | Fixed | `access_verification.py:143-144` binds `exc` and logs "turn failed … : %s" |
| Minor 3 | Fixed | `test_access_verification.py:193` parametrized, `no-recorded-outcome` → `{("inconclusive", None)}` |
| Minor 4 | Restored | docstring byte-identical to `main:test_baseline_capture.py:783-788` (verified by `diff`) |
| Minor 5 | Fixed | one `_write_exchange` at `test_captured_turn.py:131`, all four sites collapsed, no residual copy |

### Minor 1: the builder's deletion rationale verified independently

Both HTTP writers derive `res_stats` and `transport` from the same `flow` in adjacent statements
(`exchange_recorder/__init__.py:278-279` and `:495-500`), and `_http_error_response_stats`
(`exchange_recorder/artifacts.py:113-118`) stamps `http_{status_code}` for exactly
`status_code >= 400`, the same predicate the deleted branch used. Neither recorder file is touched by
this delta. The claim holds; deletion was the right call over documentation.

The `legacy-index-summary` id did not survive: it is now `recorded-http-error`
(`storage/test_transport_refusal.py:20`), which is accurate for the only remaining path.

### Minor 3: the new case lands in the new handler

`refuse` raises `CapturedTurnError`, so it enters `access_verification.py:143`, not the generic
handler at `:146`. The caplog assertion pins this: it requires `"provider access verification turn
failed for"`, and the generic handler emits `"provider access verification failed for"` with no
`turn`. The same assertion also proves the provider's sentence reaches the log, since it requires
`"provider refused the access verification turn"` in the formatted message.

### The headline regression still bites

Re-ran the falsification against `4ced4e85` with `transport_refusal` reverted to `main`'s semantics:

```
FAILED test_codex_server_refusal_fails_fast_with_the_provider_reason
- the provider refused the turn for claude/gpt-5.2/a1 with HTTP 400: "The 'gpt-5.2' model is ..."
+ the delivery for claude/gpt-5.2/a1 matched 1 request(s), but no response IR was captured before the timeout
1 failed in 30.22s
```

The consolidation did not defang it. The test still drives the real path with `stop_reason=
"ws_close_1006"`, `response_ir=False`, `transcript_reply=False`, and still asserts the full raised
string with `str(raised.value) ==` plus `elapsed < 5.0`.

### Consolidation fidelity checks

- The UUID literal sequence was rewritten as `UUID(int=value) for value in (0x382, 1, 2, 3, 0x383,
  4, 5, 6)`. Verified equal to the eight original strings. Intent is now less legible: `0x382` and
  `0x383` encode issue numbers 382 and 383, which read as decimal in the original literals.
- The startup exchange's `request.raw` changed shape from `{"prompt": "startup"}` to
  `{"messages": [{"content": "startup"}]}`. Inert: the fake reader extracts the same `"startup"`,
  and `request.ir.json` content is never read (`captured_turn.py:158` tests existence only).
- `mkdir()` became `mkdir(parents=True, exist_ok=True)` at the owned and title sites. No test
  depended on a collision raising.

### Observation, below the bar for a finding this round

`test_captured_turn.py:334` still carries `else payload["prompt"]` in the fake reader's prompt
extraction. Now that `_write_exchange` is the only writer and always emits the `messages` shape,
that fallback is unreachable. Cheap to drop with the next touch of this file.
