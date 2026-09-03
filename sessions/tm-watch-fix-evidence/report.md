# Watch framing and readiness fix

Committed as `3c2c6c4e` on `fix/support-derivation-causes`.

Activity snapshots no longer inherit the provider SSE parser's 1 MiB frame cap. Activity uses strict parsing; malformed JSON, invalid UTF-8, invalid schema and truncated final lines raise a typed control_plane_unavailable error. The watch engine propagates terminal stream errors immediately through registration and its public error mapping, preserving the cause in audit evidence.

Readiness now represents current source health independently of the retained Activity baseline. Transport disconnects and clean EOF clear Activity readiness and reconnect. Registrations wait for a fresh snapshot, and timeout responses retain the latest transport cause. Shutdown and unexpected consumer failure wake pending registrations. Registration checks health again after auditing, before applying the subscription.

## Proof

- Initial regression checks demonstrated 11 expected failures before the production fix. Two review findings added five further failing cases before correction.
- Final focused suite: 83 passed (`adjacent.log`).
- `just check`: passed, including TypeScript checks and Python lint, format and mypy over 971 files (`check.log`).
- `just test`: passed, 5,030 Python tests and all JavaScript suites (`test.log`).
- All changed Python files are at most 685 lines; the longest changed-file function is 111 lines. `git diff --check` passed.
- Live observer using the changed Python code registered against the preview gateway's 412-row workspace in 26.8 ms. It consumed a real Postgres completion signal and read the matching completion cursor for a dedicated captured Codex run, producing the expected watch notification (`live-result.json`). The probe was closed afterward.

The live test used an in-memory final notification sink and audit sink. Gateway streaming, Postgres listening, and completion reads were live; actual pane delivery was not exercised by that probe. `live-watch.py` records the repeatable observer. The existing preview backend was not restarted and still needs a restart to load this commit.

## Review and recovery behavior

Fable supplied a written review, and its two requested corrections have regression coverage. See `fable-review.md` and `review-disposition.md` for all findings and scope decisions. No claim is made that Fable's subsequently expanded review completed.

A terminal protocol failure stays attached to a feed while existing subscribers retain it. Subsequent registration returns the original typed cause. After repairing the underlying fault, removing retained subscriptions and registering again creates a fresh feed. Ordinary transport failures reconnect automatically.

The evidence and design notes are local artifacts, outside the repository. The commit changes only the watch framing, readiness, public error mapping, audit detail and their tests.
