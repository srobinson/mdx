# TM overlay server trust boundary

Date: 2026-08-07

Repository evidence: `c03edbd96e30d5c2917994897686bd4223f40065`

Scope: architecture brainstorm. The repository remained read only.

## Thesis

The overlay server belongs on the control path before launch. Every request must
remain on a local, frozen, verified data path.

TM should fetch one immutable signed overlay for the authenticated user and exact
harness release, verify it locally, cache it, compose it with explicitly active
local layers, and freeze the effective revision for the run. A request must never
wait for the server and a run must never hot swap revisions.

The least harmful offline behavior is:

1. Use a valid cached signed overlay for the exact subject and harness release.
2. Without one, keep history, inspection, export, account repair, and `doctor`
   available while blocking new captured launches before any proxy or harness
   process starts.

This preserves the product gate without turning a distribution outage into an
application lockout or an in flight prompt loss.

## Current ownership and the missing boundary

Measured facts from the current source:

* `api/src/transport_matters/overrides/state.py:OverrideStore` owns process resident
  override state. Each scope has one ordered map keyed by `(kind, target)`.
  `OverrideStore.upsert` gives the latest write for that key authority. Source and
  provenance are absent.
* `api/src/transport_matters/api/v1/overrides.py:patch_overrides` is the current
  manual write path. It upserts the submitted batch, updates a paused preview,
  synchronizes the shared proxy snapshot, and restores the prior snapshot on an
  exception.
* `api/src/transport_matters/request_pipeline.py:run_pipeline` selects one run or
  track scope, reads one effective list from the store, and invokes
  `apply_overrides`. An application exception forwards the original IR.
* `api/src/transport_matters/overrides/__init__.py:apply_overrides` sorts by
  operation kind. It has no source priority. Source precedence and operation
  execution order are separate decisions.
* `api/src/transport_matters/overrides/__init__.py:Override` contains only `kind`,
  `target`, and `value`. `api/src/transport_matters/overrides/audit.py:OverrideAuditEntry`
  records no overlay identity, revision, signer, author, or digest.
* `www/packages/inspector/src/components/editor/BreakpointEditor.tsx:handleSaveAsOverlay`
  copies the current live overrides into a draft.
  `www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` persists
  draft and confirmed bundles through browser storage. Its source comment states
  that application at intercept is outside that slice.
* `api/src/transport_matters/shared_proxy/subprocess.py:SharedProxySubprocess.set_overrides`
  replaces the full scoped snapshot in the proxy process. It is a transport
  consumer. It should never decide source precedence.
* `packages/runtime/src/service/RunManager.ts:RunManager.createNew` prepares capture
  before spawning the harness PTY. Overlay resolution must complete before capture
  preparation so an unavailable overlay cannot leave a proxy lease or a waiting
  harness process.
* `api/src/transport_matters/harnesses/enablement_service.py:gate_harness_enablement`
  already establishes the local precedent that unreadable required enablement
  state blocks launch with a typed failure.

The current last write rule is insufficient once the server becomes a writer.
Call order would silently define authority.

## Threat model

Protected assets:

* The exact prompt and tool surface sent to the provider.
* The user's own prompt, messages, tool results, files, and credentials.
* Tenant isolation and the user's local enable decision.
* Reproducibility of a recorded run.
* Attribution of every applied mutation.

Relevant failures and adversaries:

| Boundary | Capability | Required containment |
| --- | --- | --- |
| Distribution service compromise | Serve arbitrary bytes, suppress updates, replay responses, misroute tenants | Client signature verification, subject binding, revision rollback protection, expiry, valid cache |
| Candidate ingest compromise | Create or alter proposed overlays | Candidate state has no activation authority; publication requires a separate signer |
| Curation pipeline compromise | Produce a hostile proposed system rewrite | Fixed client policy, independent release approval, signed provenance |
| Signing authority compromise | Publish a hostile allowed rewrite | This remains the root trust risk; short validity, key revocation, constrained operations, and auditable releases limit exposure |
| Tenant authorization defect | Return another user's overlay | Signed organization and user subject, server authorization derived from the access token, local subject check |
| Cache tampering or rollback | Replace or downgrade the local blob | Signature, content digest, highest seen revision, subject and release checks |
| Harness drift | Apply a valid overlay to changed input | Exact release binding and per target preimage hashes; atomic no apply on drift |
| Accidental sharing | Upload sensitive exchange content | Local default, explicit share action, narrow candidate schema, client and server rejection of forbidden targets |

TLS authenticates the connection. It does not establish overlay provenance. The
blob needs its own signature because it is cached, replayable, and directly
changes provider input.

## Integrity and provenance

### Separate distribution from publication

The online distribution service should hold no overlay signing key. A distinct
publication service signs immutable artifacts after policy validation and release
approval. The installed client pins the public root key. A key is small trust
material; carrying it in the app does not place the overlay in the code release.

A compromised distribution service can deny service and can attempt replay. It
cannot create a new accepted prompt mutation. If distribution, curation, and
signing share one online authority, compromise of that authority can curate a
hostile prompt into every eligible seat. Cryptography cannot repair that trust
collapse.

The signed envelope must bind:

* Schema version.
* Overlay ID and monotonic revision.
* Organization and user subject. Seat identity authorizes access but does not
  broaden the subject.
* Harness ID and exact release fingerprint.
* Client policy version and minimum compatible client version.
* Every operation, target, value, and target preimage digest.
* Author identity and author kind, such as TM curator or submitted candidate.
* Approver or automated policy identity.
* Source candidate IDs.
* Issue time, validity start, validity end, content digest, key ID, and signature.

The signer is not the author. Both identities must survive into the exchange
audit.

### Client semantic sandbox

A valid signature proves who authorized the content. It does not prove the
content is benign. The client must enforce a smaller managed operation language
than the current general `Override` model.

For v1, a server managed overlay may:

* Disable an existing tool.
* Disable an existing harness system part.
* Replace an existing tool description or harness system part only when the exact
  preimage digest matches.

For v1, a server managed overlay may not:

* Add a message, system part, or tool.
* Enable a tool.
* Target user messages or tool results.
* Change sampling or provider extras.
* Carry scripts, regular expressions, templates, remote URLs, or executable logic.
* Increase the target's canonical character count.

The replacement restriction reduces the surface. A short hostile instruction is
still possible. Independent signing and release governance remain necessary while
arbitrary system text replacement is a product capability.

Each operation needs an exact preimage digest. The whole managed layer applies
atomically. Expected absence on a sparse incremental turn is a normal no op.
Presence with a mismatched digest is drift and must never yield partial mutation.

## Precedence

The client must compose layers before `run_pipeline` reads them. The fixed order,
from strongest to weakest, is:

| Priority | Source | Activation and scope |
| --- | --- | --- |
| 1 | Live user draft | Explicit breakpoint editing, scoped to the paused flow and current run |
| 2 | Local confirmed recording | Explicitly selected for a recording or debug run; never activated by confirmation alone |
| 3 | Server managed overlay | Required baseline for the authenticated user and exact harness release when optimization is enabled |

Rules:

1. The strongest layer wins for the same `(kind, target)` key.
2. A layer needs an explicit suppression tombstone so a user can suppress a weaker
   operation without deleting that weaker source.
3. Duplicate keys inside one signed artifact are invalid.
4. Composition happens once per run and again for a deliberate breakpoint edit.
5. After source composition, the existing operation priority in
   `apply_overrides` still controls safe execution order.
6. The server cannot set the local enable toggle, activate a local recording, or
   raise its own priority.
7. A local recording cannot satisfy the required managed gate by itself. It may
   refine a valid managed baseline for an explicitly initiated run.

The enforcement owner should be an extended
`api/src/transport_matters/overrides/state.py:OverrideStore`, with typed layers and
one `get_effective` composition method. `patch_overrides` should write the live
draft layer. A managed bootstrap path should replace the server layer atomically.
The shared proxy should receive the same layered snapshot and provenance through
its existing control channel. No caller should flatten layers by write order.

## Server unreachable at startup

### Required behavior matrix

| Condition | New captured launches | Existing or in flight run | Local product surfaces |
| --- | --- | --- | --- |
| Server reachable, valid newer envelope | Verify, cache, freeze revision, launch | Keep its frozen revision | Full |
| Server unreachable, exact valid cached envelope | Launch from cache with visible cached age and background retry | Keep frozen revision | Full |
| Server unreachable, no cache | Block before capture preparation and process spawn | None at a cold start | History, inspection, export, settings repair, sign in, logs, and `doctor` remain available |
| Cache expired or wrong harness release | Block with `overlay_unavailable` | Keep any already frozen valid run until it exits | Same observation and repair surfaces |
| Bad signature, wrong subject, unknown key, or revision rollback | Treat response as hostile; use a newer valid cache or block | Keep frozen revision | Show security failure without displaying attacker supplied text |
| Exact release unsupported | Block that harness with `overlay_unsupported_release` | Existing frozen run is unchanged | Other eligible harnesses and observation remain available |
| New revision appears during a run | Use on the next run only | Never hot swap | Show update available |
| Server disappears during a run | No effect | Continue frozen verified overlay | Show distribution health separately |

The valid cached case is the least harmful degradation. For a cold cache, an
observation only shell is safer than either total application failure or silent
unoptimized launch.

TM should never start a harness and then hold its first request while attempting
network recovery. Blocking before `RunManager.createNew` prepares capture yields a
clear retry boundary and avoids prompt loss.

If application drift appears after a request is already captured, forward that
one request byte identical, record a security and drift event, quarantine the
managed revision for later turns, and prevent new runs. Dropping an already issued
user prompt is more harmful than one explicit fail open turn. Partial application
remains forbidden.

## Data direction

### Fetch request

The client may send only:

* Its short lived account credential.
* Harness ID and exact release fingerprint.
* Supported overlay schema and client policy version.
* A conditional request digest or ETag.

Organization, user, and seat identity come from the authenticated credential.
The server must ignore any client supplied tenant identifier.

### Content the client must never upload automatically

* Raw wire requests or responses.
* Transcript content.
* Harness system prompts and tool descriptions.
* User prompts, messages, code, files, tool inputs, and tool results.
* Provider credentials, authorization headers, cookies, or runtime home content.
* Working directories, repository names, canonical paths, environment variables,
  or local machine identifiers.
* Breakpoint drafts, local confirmed recordings, before and after IR, or audit
  text.

Fetch telemetry should use stable product identifiers and coarse error codes. It
should not include current request fingerprints.

### Explicit candidate sharing

`SAVE AS OVERLAY` remains local. A separate explicit `Submit for organization
curation` action may upload a candidate containing:

* Client generated candidate ID and idempotency key.
* Harness ID and exact release fingerprint.
* Allowed operation kinds, targets, preimage digests, and replacement values.
* Aggregate before and after character counts.
* Optional user supplied name and rationale.

Replacement text is necessarily disclosed when the user chooses to share it. The
confirmation surface must show exactly which replacement bytes and metadata will
leave the machine. Original target text and the surrounding exchange stay local.

Candidates containing message targets, tool result targets, provider extras,
sampling changes, paths, or credential shaped fields must be rejected both before
upload and at ingestion. Submission creates an inactive candidate. It cannot
publish or activate an overlay.

## Minimal viable server contract

Two authenticated endpoints satisfy distribution and deliberate recording.

### 1. Resolve the effective managed overlay

`GET /v1/overlays/effective?harness_id=<id>&release_id=<exact>&schema_version=1`

Properties:

* Account token supplies organization, user, and seat authorization.
* One exact result. No list, search, nearest release, or client selected tenant.
* `ETag` equals the signed content digest.
* `200` returns the immutable signed envelope.
* `304` permits use of the already verified identical cache.
* `404 overlay_unsupported_release` is distinct from network failure.
* `401` and `403` are account failures.
* Unknown fields and unsupported schema fail closed.

Illustrative envelope:

```json
{
  "schema_version": 1,
  "overlay_id": "ovl_01",
  "revision": 17,
  "subject": { "organization_id": "org_01", "user_id": "usr_01" },
  "harness": { "id": "claude", "release_id": "sha256:..." },
  "policy_version": 1,
  "issued_at": "2026-08-07T00:00:00Z",
  "valid_until": "2026-08-14T00:00:00Z",
  "operations": [
    {
      "kind": "system_part_text",
      "target": "system:0",
      "preimage_sha256": "...",
      "value": "..."
    }
  ],
  "provenance": {
    "author_kind": "tm_curator",
    "author_id": "cur_01",
    "approved_by": "policy_04",
    "source_candidate_ids": []
  },
  "content_sha256": "...",
  "signature": { "algorithm": "Ed25519", "key_id": "tm-overlay-2026-01", "value": "..." }
}
```

### 2. Submit an inactive candidate

`POST /v1/overlay-candidates`

Properties:

* Explicit user action and an idempotency key are required.
* Subject and organization derive from the token.
* The narrow candidate schema accepts only the shareable subset above.
* Response is a candidate ID, content digest, and `received` state.
* The endpoint has no publish, activate, bulk import, script, raw exchange, or
  arbitrary metadata capability.
* Promotion occurs in the separate curation and signing system.

No per request fetch endpoint, push channel, remote execution facility, or general
overlay CRUD API belongs in v1.

## Audit contract

Every captured exchange should record:

* Overlay ID, revision, content digest, author, approver, and signing key ID.
* Verified subject and exact harness release.
* Resolution source, `network` or `cache`, and cache age.
* Frozen run revision.
* Source layer for every override audit entry.
* Applied, expected absent, target missing, preimage mismatch, suppressed, and
  policy rejected as distinct outcomes.
* Original and curated character counts already owned by `OverrideAudit`.

Audit data must never contain the account token or server supplied content that
failed verification.

## Refusals for v1

* No server call on each request.
* No unsigned emergency overlay.
* No nearest version fallback.
* No silent use of an expired or cross subject cache.
* No server ability to enable optimization.
* No automatic upload from capture, inspect, edit, or save.
* No direct client publication to other seats.
* No source precedence determined by call order.
* No partial application after a preimage mismatch.

These constraints leave one explicit root of trust: the overlay publication
authority. If the product requires arbitrary system prompt rewrites without local
per revision approval, the user delegates that authority to TM. The architecture
can make the delegation narrow, attributable, reversible, and outage tolerant. It
cannot make a compromised signing authority harmless.
