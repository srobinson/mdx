# 633: verification: a model the release does not reference must come out of first launch blessed or degraded

URL: https://github.com/littleorgans/transport-matters/issues/633
State: open
Labels: bug, P2
Updated: 2026-09-05T02:52:19Z

Sub issue of the harness and model discovery epic.

A model the shipped release does not reference receives a verification cell but no verdict, so it is neither blessed nor degraded. It falls out of the compatibility contract entirely.

## Observed

`gpt-6-astra` released on 2026-09-04. The shipped codex release reference carries only `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` and `gpt-5.5`. `support_verdict_store.py:224` requires an exact launch model match and `:78` returns silently when none exists. `launch_verification.py:220` skips capture whenever the installed harness version is inside the blessed range, so a new model on an in range harness is never captured and never compared.

Once the enumeration probe reads the live catalog, new models arrive routinely and several at a time, so this becomes the normal path rather than a corner case. `gpt-5.3-codex-spark` is a second present example.

## Reference selection: exact precedence, then alternative sibling contracts

For each required `RequestShape`:

1. Select references from the pinned release matching the candidate's harness, exact route, body profile and request shape.
2. If an exact launch model reference exists, use it exclusively. A failed exact comparison cannot escape through a sibling.
3. Otherwise compare separately against every eligible sibling, each call keeping the shipped reference on the left of `assess_support_state`.
4. Bless the cell when at least one complete comparison is blessed. Otherwise degrade it.
5. A complete comparison covers body and envelope from the same reference whenever both sides carry an envelope. A passing body from one sibling may not be paired with a passing envelope from another.
6. Sort references by their existing reference key; the first passing reference is the displayed witness. Persist every comparison result with reference identities and digests. Ordering affects presentation only.

Alternatives beat a fixed representative because the shipped references disagree with each other. `gpt-5.5` differs in schema from sol, terra and luna, so a candidate carrying sol's schema is degraded against `gpt-5.5` and blessed against the other three. A fixed representative or an all siblings requirement would degrade a schema Transport Matters already ships as supported. The accepted tradeoff is that an unreferenced model can satisfy a less demanding shipped variant; exact precedence takes over once its own reference ships.

Candidate identity is preserved everywhere. Reference identities are provenance, never replacement identities. `RequestShape`, `SupportState` and the directional comparator are unchanged, and `baseline_comparison.compare_model_pair` keeps its two direction peer comparison for cohorts.

Runtime blessed newcomers never become references for other models. A local verdict establishes compatibility against publisher owned evidence; it does not confer authority to extend the reference set. Allowing it would make results depend on a machine's launch history.

## Every first launch has a state

An uncovered model begins at `degraded` with reason `verification_pending` and phase `queued` or `running`. A completed comparison replaces that assessment. Missing references, failed capture, provider refusal, unavailable provenance and derivation failure each retain degraded with their own reason. No compatible reference at all yields `degraded` with reason `no_compatible_reference`, retaining first turn evidence and inventing no structural findings. Blessed requires every required shape satisfied; partial completion stays degraded. Pending or failed verification must never manufacture a missing property finding.

## Verification queue

`launch_verification_support.py:114` rejects excess submissions. Three simultaneous submissions returned `accepted: true, true, false`, so one verification is silently dropped. With several new models arriving from one catalog refresh this becomes routine.

Replace it with a durable, deduplicated queue of requested verification cells, keeping the existing two worker execution limit: repeated launches of one cell join existing work; distinct models get separate records; saturation queues rather than discards; workers recheck existing evidence under the cell lock before spending provider requests; capture deadlines start at execution so queue waiting does not consume the capture budget; restart recovery discovers pending work without another launch. Queue admission must not increment `attempt_count`.

## Capture cost

Refresh itself spends zero provider requests. Capture is per launched model and independent of sibling count, since comparison is local.

| capture required | provider requests per model |
| --- | ---: |
| first turn | 3 |
| tool turn | 6 |
| both shapes | 9 |
| valid captured evidence reused | 0 |
| already referenced model inside the blessed range | 0 |

Today's codex release carries first turn references only, so astra costs 3 and spark costs 3. Existing evidence reconciliation precedes the quota check, so a refusal to spend further provider requests must never prevent a local comparison.

## Retention

A verdict answers what support a captured model earned on a route and harness version against a release. Catalog membership answers what the vendor currently offers this account. Removing `gpt-5.2` or `gpt-5.4` from the latter does not invalidate the former. Refresh never deletes or downgrades a verdict, a stored verdict never reintroduces a model into the picker, and disappearance triggers no capture. Reappearance at the same evidence coordinates reuses the verdict; changed coordinates require a new assessment.

Add a read only `GET /v1/harnesses/{harness_id}/support-verdicts` with model, route, version and release filters, backed by the same store validation functions. `GET /v1/harnesses` exposes only baseline attempt information today (`harnesses/inventory.py:549`) and is not a complete reader.

## Scope

| file | change |
| --- | --- |
| new `support_reference_policy.py` | own `SupportReferencePlan`, required shapes, exact precedence, sibling alternatives, empty set behaviour. Shared by writer, reader, resolver and capture planner |
| `support_verdict.py` | separate candidate identity from a collection of `ReferenceComparison` records; distinct typed variants for comparison backed assessments and conservative degraded reasons |
| `support_verdict_store.py` | replace `_matching_reference`; write under candidate identity; discover verdicts independently of release model names and live targets |
| `harnesses/resolver.py`, `resolver_snapshots.py` | consume the same plan and candidate assessments |
| `launch_verification.py`, `launch_verification_support.py` | model aware capture eligibility, reconcile before quota, drain queued work through bounded workers |
| new `launch_verification_queue.py` | one `VerificationRequest` per capture key; admission, deduplication, restart discovery |
| `baseline_capture.py`, `baseline_evidence.py` | bind the actual capture route, prevent evidence reuse across routes, retain candidate identity |
| new support diagnostics route | expose retained verdicts independently of catalog membership |
| `CLAUDE.md`, `docs/HARNESS-COMPATIBILITY.md` | model aware eligibility, provisional degradation, publisher only reference authority, queueing, retention |

`baseline_store.py` is 699 lines and `resolver.py` is 692. Extract before expanding either.

## Verification

1. Astra and spark arrive together; each receives its own first launch verdict on an in range harness.
2. At least three distinct new models launch simultaneously. All work drains, at most two captures run concurrently, none is dropped.
3. Duplicate launches share one capture; reversing launch and completion order preserves results.
4. Runtime blessed newcomers never enter another candidate's reference set.
5. First turn only capture costs three requests per new model; both shapes cost nine; sibling count adds no provider requests.
6. Exact precedence, sibling alternatives, directionality, envelope pairing and shape separation behave as specified.
7. No reference, queued, partial, failed and corrupt evidence cases always produce explicit degraded assessments.
8. Removing a model from a complete refreshed catalog preserves its artifact and diagnostics result without restoring its picker entry.
9. Reappearance reuses valid evidence; changed coordinates cannot reuse the wrong verdict.
10. Writer, reader and resolver agree on the selected reference set and reject tampered identities or digests.

## Outcome

A model released today comes out of its first launch blessed or degraded, never verdictless.


## Sub issues
[]
