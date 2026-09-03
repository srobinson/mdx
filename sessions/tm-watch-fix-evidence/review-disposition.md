# Fable review disposition

Fable wrote fable-review.md after 47 focused tests passed. The native review skill then launched additional subagents despite the explicit single-review, no-helper brief. The parent run was closed to stop the expansion; the written review is the bounded review evidence, not a claim that every launched angle finished.

- F1: fixed. Strict finish rejects any nonblank unfinished line, including partial data prefixes. Four regression cases failed before and passed after.
- F2: fixed. require_ready reports current unavailable state; wait deadline names its timeout. Added an audit-window disconnect test that failed before and passed after. Commit-time health changes fail promptly; they do not extend the original registration with another full deadline.
- F3: accepted explicit lifecycle policy. Gateway Activity route has only invalid-request 400 responses for malformed workspace/owner; connection failures and 5xx are retryable. Permanent protocol or authorization failure remains attached to retained watchers and subsequent watch calls return its typed cause. Explicit unwatch of retained subscribers releases the failed feed; a new watch creates a fresh feed after repair. No new public watch-health/push-error API is part of this change.
- F4: retained existing audit-before-effect convention with a corrective gateway_failed row if the audited registration loses readiness before commit. The final row proves the actual outcome. A broader transactional audit migration is outside this fix.
- F5: the loopback endpoint detail already appears in other control plane error responses and is useful for diagnosis. Watch now retains it. No other service operation was changed.
- F6: removed duplication. One named registration-stop message; unexpected consumer task errors now reach the existing completion callback, eliminating the second fallback error constructor.

Final focused validation: 83 tests passed. Full repository gates are repeated after these corrections.
