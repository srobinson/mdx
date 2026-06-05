# littleorgans Transport Capture: Codex Evidence Final Signoff

Status: COMPLETE

## Worker Status

No nested workers. Final closure review was performed directly. Only this new signoff report was edited.

## Scope and exact v2 delta

- Canonical synthesis: 552 lines, SHA-256 `9a8c03f7ca7016cc5c2d0c3a0089b8308293fd6890896863d818fda3fafc9a22`
- Archived v2: 543 lines, SHA-256 `47403b80dc7c626a989146db030089805619958bc9e20fc8cb5f50203fd22b31`
- Failed signoff consensus: Status COMPLETE, SHA-256 `3f7f5e48b3b71234a98aebe208e60680d8bdf57e914faf18ba03a9faf95af80a`
- The exact v2 delta has nine bounded hunks. They change only the B-1, B-2 option (b), F-2, and F-3 closure text, their experiment and gate criteria, U3, the line-count audit, and the closure map.
- The canonical remains below 700 lines, has Status COMPLETE, contains zero em dashes, preserves both source pins, and introduces no `tm` or transport-matters dependency.

## Blocker results

| Item | Result | Evidence |
|---|---|---|
| B-1 local fault attribution | PASS | Line 310 replaces the provider-shaped body with a lilo-namespaced envelope containing `source=lilo` and `type=lilo_capture_error`, retains HTTP 422/413, records `origin=lilo`, and sets CAPTURE to `failed` with `failure_origin=lilo`. Line 227 adds retry-count-zero proof to X1. Line 389 requires one harness failure, zero upstream requests, zero retry amplification, local CAPTURE attribution, and no persisted provider attribution. Provider truth is preserved. |
| B-2 option (b), per-artifact durability | PASS | Lines 245 to 246 remove the unscoped power-loss promise. Strict durability now applies only to the request artifact, transform manifest, and synchronized response prefixes. Lines 245, 308, 311, 313, 422, and 479 consistently bound the unsynchronized response suffix to 1 MiB, permit its loss on kernel or power failure, and require Interrupted rather than Complete recovery. My prior CS-7 failure is closed. |
| F-2 APFS directory-entry limitation | PASS | Line 246 states that APFS has no directory-entry equivalent of `F_FULLFSYNC`, selects pre-created and synchronized exchange directories and fixed artifact slots, and makes proof a Gate 2 condition. Lines 232, 313, and 422 carry the same APFS layout into X6 and the gate exit. |
| F-3 stale root instruction text | PASS | Line 167 adds the stale `CLAUDE.md` Transport verb list to the delete-and-rewrite targets. Line 418 requires Gate 0 to remove `paths` and align the list with daemon-mediated `list`, `show`, and `export`. |
| Adjacent consistency | PASS | The B-1 origin contract is aligned across X1, request failure semantics, persisted records, CAPTURE state, and the release assertion. The B-2 durability scope is aligned across X6, the crash contract, request and response semantics, Gate 2, and U3. The 8 MiB spool remains distinct from the 1 MiB unsynchronized-loss ceiling, and every partial response outcome remains Interrupted. No rejected consensus position was reopened. |

## Remaining findings

None. The bounded closure introduces no P0 or P1 defect.

Verdict: PASS
