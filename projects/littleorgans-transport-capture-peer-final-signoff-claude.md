---
title: Final closure sign-off — littleorgans transport capture synthesis (claude backend-engineer)
type: review
tags: [backend, security, durability, transport, capture, signoff]
summary: Final closure sign-off of the corrected synthesis against archived v2; both blockers closed, verdict PASS
status: complete
source: backend-engineer
confidence: high
created: 2026-07-31
updated: 2026-07-31
---

Status: COMPLETE

Verdict: PASS

Both blockers (B-1, B-2 option (b)) and both non-blocking riders (F-2, F-3) are closed in the corrected canonical. The v2 delta is bounded to exactly those four items. No new defect at any severity. One non-blocking advisory for Gate 2 is recorded below; it does not affect the verdict.

## Worker Status

- Reviewer: littleorgans:helioy-tools:backend-engineer:5:2.1. Read-only, no nested agents spawned. No edit to the synthesis, either archive, any prior report, or either repository.
- Scope: closure only. B-1, B-2 option (b), F-2, F-3, and adjacent consistency. No scope broadened; no rejected item reopened; no correction outside the two blockers and two riders was re-litigated.
- Baseline identity verified by hash, not by assertion. Archived v2 `.archive/littleorgans-transport-capture--synthesis.v2.md` is SHA-256 `47403b80dc7c626a989146db030089805619958bc9e20fc8cb5f50203fd22b31`, which is exactly the 543-line corrected canonical I reviewed in my delta sign-off and which the aggregation recorded as the common baseline for all three reviewers. Current canonical is SHA-256 `9a8c03f7ca7016cc5c2d0c3a0089b8308293fd6890896863d818fda3fafc9a22`, 552 lines.
- Delta verified exactly: `diff` of v2 against the current canonical returns 9 hunks, all inside sections 5, 7, 8, 10, 13, 15, 16, and the self-audit. Every hunk maps to B-1, B-2, F-2, or F-3. Nothing else changed.
- Mechanical: 552 lines (under 700), zero em dashes, both source pins intact at lines 17 and 18, self-audit line count updated to 552, no `tm` dependency introduced by any hunk.

## Blocker-by-blocker

### B-1 capture-fault envelope, attribution, assertion, retry proof — PASS

All four required elements are present and mutually consistent.

1. **Lilo-namespaced envelope.** Section 10 now specifies `{"source":"lilo","type":"lilo_capture_error","code":"<stable_code>","message":"capture unavailable"}` for the 422, and the same envelope with `capture_request_too_large` for the 413. Both Anthropic discriminants are gone: a grep of the full document returns zero occurrences of `invalid_request_error` and zero of "provider-shaped". Origin is now carried by two independent machine-readable fields (`source` and `type`), so a consumer classifying on either cannot misattribute the fault. The stable code moved out of the free-text message into its own `code` field, which is a strict improvement over what B-1 required.
2. **Local CAPTURE attribution.** "The capture record sets `origin=lilo`; CAPTURE is `failed` with `failure_origin=lilo` and the stable code." Consistent with the CAPTURE state set in section 12 (`active`, `complete`, `lost`, `failed`), so no new state was introduced to carry this.
3. **Persisted-artifact assertion.** The section 13 release-gate assertion now reads "a pre-delivery 422/413 capture fault yields one harness failure, zero upstream requests, zero retry amplification, and no persisted artifact that attributes the local fault to the provider; CAPTURE and the capture record mark `origin=lilo`". It covers both status codes and asserts the negative on persisted artifacts, which is the property my F-1 was about.
4. **X1 retry proof.** The X1 row now exercises "locally generated 422/413 faults with retry count zero" and its decides column includes "local-fault non-retryability". Non-retryability is now measured against the real harness rather than assumed from the status class, which matters because the envelope shape changed.

**Adjacent consistency.** The section 10 sentence "the proxy never fabricates a provider response" (line 311) previously sat four lines from a specified provider-schema body; with a lilo-typed envelope the two are now coherent, and the tension my F-1 identified is gone rather than merely relabelled. Section 7's relay constraint to forward provider error bodies unmodified is untouched and remains correctly scoped to genuine upstream errors. Section 2 principle 4 (provider truth over harness self-report) is no longer contradicted by a synthetic provider-typed record entering the transcript stream.

### B-2 option (b), per-artifact durability scope — PASS

Section 8 crash-contract item 1 was replaced with a per-class claim: the request artifact, transform manifest, and each durably synchronized response prefix survive process crash, kernel crash, and power loss; at most 1 MiB of the in-flight response suffix may be lost on kernel or power failure, and recovery records Interrupted and never Complete. The unscoped global sentence and the "measured loss window is incompatible" line are both removed.

Every downstream statement was brought into the same direction, which is what option (b) required and the part most likely to be missed:

- Section 10 line 308 now names the 1 MiB unsynchronized suffix as the loss bound with Interrupted recovery, in the same bullet that sets the ceiling.
- Section 10 line 309 states the request artifact and transform manifest cross the strict barrier before delivery and that each synchronized response prefix carries the same strict guarantee.
- Section 8 item 2 states response bytes enter the strict claim only when their prefix crosses the barrier.
- X6 (line 232) proves strict durability per class and the 1 MiB Interrupted bound.
- Gate 2 exit requires request artifacts, transform manifests, and synchronized prefixes to pass the strict barrier and every lost suffix to be at most 1 MiB recovering as Interrupted.
- U3 is restated to the scoped barriers with the 1 MiB bound retained.

A grep for "power loss" and "power failure" returns exactly four occurrences (lines 232, 245, 308, 422), all scoped identically. There is no surviving unscoped promise.

### F-2 APFS directory-entry limitation — PASS, resolved by the stronger of the two options

Section 8 item 2 states plainly that APFS has no directory-entry equivalent of `F_FULLFSYNC`, then removes the dependency rather than scoping the claim down: Transport pre-creates and synchronizes the exchange directory and fixed artifact slots before a request may forward, so the strict barrier updates already-reachable files and does not depend on a post-barrier rename. Gate 2 must prove the layout, and X6 verifies it. The hedge phrase "the strongest supported directory synchronization" is gone.

**Adjacent consistency.** The old item 1 language ("temp, fsync, rename; exchange activation is an atomic directory swap") is fully replaced, so nothing in the crash contract now contradicts the pre-created-slot design. The surviving rename references are correctly scoped elsewhere: line 153 describes the rejected runtime `EventLog`, line 181 is a research-system lesson, line 320's "blob activation" and line 399's rename fault-injection boundary cover non-barrier paths where rename remains appropriate. No contradiction.

### F-3 stale `CLAUDE.md` Transport verb list — PASS

Section 5's delete-and-rewrite list gains the entry at line 167 naming the `CLAUDE.md` command-surface text and requiring `paths` removed and the list aligned to `list`, `show`, `export`. Gate 0 exit now requires "the root `CLAUDE.md` Transport verb list removes `paths` and matches `list`, `show`, and `export`". The rider is closed in both places, consistent with R16 and E18.

## Non-blocking advisory

**A-1 (advisory, Gate 2 execution detail, not a finding).** Moving the barrier from temp-plus-rename to in-place updates of pre-created slots changes artifact visibility from all-or-nothing to partially-visible: a reader can now encounter a torn slot that rename semantics would have hidden. The governing invariant is already normative and correct (item 1 forbids Complete on an unsynchronized suffix; the state machine carries Interrupted; section 13 already requires torn-tail and byte-corruption repair tests), so nothing in the document is wrong. The recommendation is only that Gate 2's proof of the layout explicitly include torn-slot detection, since the framing that distinguishes a durable prefix from a torn write is what makes the Interrupted-never-Complete invariant enforceable under the new scheme. This is implementation-level and does not require a synthesis edit.

## Verdict

PASS. B-1 closes with a lilo-namespaced envelope carrying two independent origin markers, local CAPTURE and capture-record attribution, a persisted-artifact negative assertion covering both status codes, and empirical retry proof folded into an experiment already scheduled. B-2 closes on option (b) with the claim scoped per artifact class and every downstream statement, experiment, gate exit, and ledger entry moved in the same direction. F-2 closes by removing the platform dependency rather than hedging it. F-3 closes in both the rewrite list and the Gate 0 exit. The delta is bounded to these four items, introduces no new defect at any severity, and preserves line count, em-dash, source-pin, and zero-`tm` discipline.
