# PR 302 quota probe 429 review

Reviewed `main..fix/anthropic-usage-limit-discriminator` at `e38bfa2e47f58d44877ace88ffd0b45d570c2fd5..b05f538d1974e4836be343d8badd716ef547ebd8`. The repository tree was pristine before review. This review made no repository writes.

## Verdict

Clean. No candidate findings.

## Evidence

1. `classify_provider_response_status()` now mints `usage_limit_reached` for Anthropic only when status is 429 and the normalized `x-should-retry` value is exactly `false` (`api/src/transport_matters/provider_conditions.py:64`). Explicit `true`, missing, empty, and unknown values return no condition. Case and surrounding whitespace are handled without widening the accepted semantic value.
2. The regression test pins the real quota probe discriminator value `true` and captured request ID `req_011Cd8fL2bQkYFBhCppstUr6` (`api/src/transport_matters/test_provider_conditions.py:10`). The relevant classifier input is the captured header scalar. Pure classifier tests and the handler seam test both fail if the former unconditional Anthropic 429 mapping is restored (`api/src/transport_matters/test_live_status_conditions.py:92`). The positive `false` case is correctly labeled as a synthetic contract case.
3. The response handler reads the Anthropic header and threads it through `LiveStatusObserver.observe_response_status()` to the pure classifier (`api/src/transport_matters/addon_handlers.py:93`, `api/src/transport_matters/live_status_observer.py:170`). The classifier has no I/O or stateful dependency. Searches found no missed production caller.
4. The writer boundary produces no provider condition row for retryable or headerless Anthropic 429 responses. Both downstream effects consume that shared signal: Activity projects the condition to `needs-you-usage-limit`, and launcher delivery resolves provider conditions through `_provider_condition()` (`packages/activity/src/projections/workspaceActivity.ts:55`, `api/src/transport_matters/controlplane/delivery_wait.py:595`). Anthropic 401 and Codex 401 and 403 behavior remains unchanged and has direct regression coverage. Codex 429 remains unclassified.
5. The committed range contains no temporary instrumentation, debug statements, or `/tmp` references. `git diff --check` is clean. Every changed file remains below 700 lines.
6. The source and control plane documentation state the conservative boundary: a real usage cap response with `x-should-retry: false` has not yet been captured, so the implementation accepts false negatives pending certification rather than representing the synthetic contract fixture as a real capture (`api/src/transport_matters/provider_conditions.py:47`, `CONTROLPLANE.md:184`).
7. Ripple review found one production classification seam and no alternate raw 429 consumer. The change is limited to header threading, the pure classifier, focused tests, and matching documentation. No Codex, Activity, launcher, or UI implementation changed.

## Verification boundary

This was a read only code trace. I did not rerun tests because the review brief prohibited writes and execution residue. The PR reports `just check` clean and `just test-affected` with 2,855 passing tests. Current GitHub checks did not start any steps, so they provide no execution evidence for this verdict.
