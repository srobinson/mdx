---
title: Transport Matters provider access evidence
type: design
tags: [transport-matters, harnesses, provider-access, canvas, launch]
summary: Architecture for independent authentication and provider access evidence in issue 385
status: active
created: 2026-08-16
updated: 2026-08-16
project: transport-matters
confidence: high
source: https://github.com/littleorgans/transport-matters/issues/385
---

# Transport Matters provider access evidence

## Decision

Implement issue 385 with separate authentication and provider access records.
Authentication refresh cannot write provider access. Provider outcomes cannot
write authentication. Both records bind to one registered connection and carry
their own revision, observation time, and reason.

Use the current owners:

- `refresh_harness_state` runs safe startup and targeted refresh.
- `ExecutorEvidenceStore` persists both evidence types.
- `harness_inventory()` assembles every read view.
- The resolver decides launch policy from pinned snapshots.
- The managed capture path sends the optional diagnostic request.
- `HarnessSection` owns Canvas actions.

Startup, inventory reads, polling, and safe refresh never send a potentially
billable provider request.

## Evidence records

Add `LocalHarnessAuthenticationObservation`. Redefine
`LocalHarnessAccessObservation` as provider access only.

Both records carry:

- executor id
- compatibility release id
- harness id and normalized version
- connection id and revision
- credential route id
- evidence adapter or probe revision
- observation time
- a closed sanitized reason

Provider access also carries `available`, `unavailable`, or `unknown`, its
source, and `expires_at`. Its source is one of a certified nonconsuming probe,
an explicit diagnostic test, or a genuine provider outcome.

The access assessment derives `available`, `unavailable`, `unknown`, `stale`,
or `missing`. Stored status never changes merely because time passes.

One pure scope predicate compares every stored binding field with the current
executor, release, harness version, connection, route, and adapter revision.
Both inventory and launch policy use it. The store also locks the parent
connection and rejects executor, harness, route, or connection revision
mismatch before a write.

## Persistence

Add migration `0033_provider_access_evidence.py` after
`0032_space_worktree_ownership`.

The migration creates `harness_authentication_observation`, copies only the
authentication portion of old rows, and replaces the combined
`harness_access_observation` with a provider access table. Old access values
are discarded because current authentication probes did not prove provider
access.

Each table has primary key `(executor_id, connection_id)` and a composite
foreign key to `harness_connection`. Each upsert compares timestamps only
with its own evidence type. Equal timestamp and different content fails.

Do not add a receipt table. The server writes one validated access receipt to
the existing durable `launch_fields`. That receipt already reaches
`ProxyRunBinding`, which gives passive classification exact connection
attribution without a second persistence format.

## Producers

Safe refresh builds only `LocalHarnessAuthenticationObservation`. A certified
nonconsuming adapter may also record provider access. Claude and Codex have no
such adapter today.

Add one `ProviderAccessRecorder`. Certified probes, diagnostic tests, and
genuine outcomes all call it. The recorder resolves the current certified
route, computes expiry, builds normalized access evidence, and calls the one
access upsert.

Provider classifiers are false negative biased. A genuine successful assistant
response records available. A certified entitlement rejection records
unavailable. Authentication rejection updates authentication and leaves access
unchanged. Network failures, server failures, utility traffic, and unknown
bodies write no access evidence.

The explicit test uses the normal managed capture path with a fixed bounded
prompt. Canvas first discloses that the action sends a provider request and may
consume tokens. The user must confirm. Startup never sets this mode.

## Launch policy

Every launch selects a connection and assesses provider access. This includes
requests that omit model and effort. Omitted targets stay omitted so the native
harness keeps its default target.

| Evidence | Ordinary launch | Confirmed diagnostic test |
| --- | --- | --- |
| available | Proceed | Proceed if requested |
| unavailable | Reject with sanitized remediation | Proceed with disclosure and confirmation |
| unknown | Require per launch approval | Proceed with disclosure and confirmation |
| stale | Require per launch approval | Proceed with disclosure and confirmation |
| missing | Require per launch approval | Proceed with disclosure and confirmation |

Approval is request scoped. It never becomes a preference or changes evidence.
The receipt retains the selected connection, assessed state, approval mode,
sanitized reason, observation time, and expiry.

Extract shared connection and certified route selection from `resolver.py`
before adding policy. The file is 685 lines at the base commit and must remain
below 700 lines.

## Canvas

Keep `GET /v1/harnesses` as the display read. Return authentication and access
as independent nested facts. The backend derives current access state from
trusted time and current scope.

Extend the generic card to render four facts:

- Installed
- Authenticated
- Access
- Models

Models summarize target observations only. Unknown access never receives a
positive tone.

`HarnessSection` adds Safe Refresh and Test Access. Safe Refresh reruns stored
safe probes and refetches inventory. Test Access opens the disclosure, then
creates the bounded managed run. Poll only while an action is active. Do not
poll forever for legitimate unknown access.

## Delivery units

1. Extract the minimum resolver connection helpers with no behavior change.
2. Add split records, migration, store methods, and overwrite regression tests.
3. Make refresh authentication only. Add independent inventory and lean views.
4. Add pure access assessment, request approval, omitted target handling, and
   the durable launch receipt.
5. Add the shared recorder and passive Claude and Codex outcomes.
6. Add the confirmed diagnostic run and the four Canvas facts and actions.
7. Update `HARNESS-COMPATIBILITY.md` and `LAUNCH-CONTRACT.md`, then run the full
   acceptance path.

Each unit deletes its superseded path. No compatibility reexport remains.

## Verification

The focused matrix must prove:

- a newer authentication write preserves available or unavailable access
- a newer access write preserves authentication
- every scope mismatch is rejected or assessed stale
- old combined rows migrate to authentication plus absent access
- startup invokes no billable provider request
- passive Claude and Codex success writes available for the receipt connection
- certified entitlement rejection writes unavailable and preserves authentication
- unknown provider responses write nothing
- available, unavailable, unknown, stale, and missing launch cases are deterministic
- omitted model and effort still produce an access receipt while staying omitted
- the receipt survives through `ProxyRunBinding.launch_fields`
- a diagnostic test requires disclosure and confirmation
- Canvas renders Installed, Authenticated, Access, and Models independently
- Python and TypeScript accept the same closed vocabulary
- changed source files stay at or below 700 lines

Final proof must include database migration and store tests, Python capture and
observer tests, Runtime and Canvas Vitest projects, a production build, and one
real startup flow through the desktop surface.

## Throughput checkpoint

- Blocking first step: split persistence and lock the overwrite regression.
- Independent work: Canvas pure facts can follow the inventory contract while
  provider classifiers follow the receipt contract.
- Shared mutable state: `connections.py`, `connections_store.py`, inventory,
  capture request types, and shared vocabulary have one owner at a time.
- Smallest safe decomposition: land the seven units above in order and run each
  focused gate before the next unit.

## Rejected designs

A connection aggregate with partial merge relies on every future writer using
the merge procedure. Separate tables make cross fact overwrite impossible at
the storage boundary.

A second receipt table duplicates durable launch metadata. Existing
`launch_fields` already reach the passive observation boundary.

A Canvas provider client would duplicate capture, credentials, classification,
and persistence. Canvas expresses consent and renders normalized state.
