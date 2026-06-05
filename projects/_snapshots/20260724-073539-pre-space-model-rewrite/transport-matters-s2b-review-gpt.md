# PR #293 adversarial review

Range: `070e10e11f248e72d9d055d88de68289b6cbd0bc...f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22`

Eligibility confirmed twice. PR #293 is open, non draft, authored by a human, and substantive at 14 changed files with 1,723 additions and 32 deletions. The GitHub user `srobinson` has not previously reviewed it. The shared tree was pristine on `feat/s2b-compatibility-releases` at the required head before review. Per brief, no gates were run.

## Findings

### Major 1: Frozen releases expose mutable signed content

Confidence: 97/100.

`api/src/transport_matters/harnesses/compatibility.py:88-124` declares frozen models, but `HarnessCompatibilityRelease.facet_observability` and `schema_digests` are ordinary mutable dictionaries. Both fields participate in `release_digest_payload()` at `compatibility.py:335-345`. `embedded_compatibility_manifest()` caches one validated manifest, and `embedded_release_entry()` returns entries from that same cache at `compatibility_store.py:196-236`.

A caller can mutate either dictionary after validation. The cached mutation persists while `release_digest` and `signature` retain their old values. A read only probe confirmed that mutating `schema_digests` through an embedded entry changed the recomputed digest and remained visible through a later accessor call.

This violates the immutable, content addressed release authority in HARNESS-COMPATIBILITY.md. Use a deeply immutable representation and add a regression that mutation is impossible.

Code: https://github.com/littleorgans/transport-matters/blob/f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22/api/src/transport_matters/harnesses/compatibility.py#L88-L124

### Major 2: Blocks from another release deny the active release

Confidence: 96/100.

`api/src/transport_matters/harnesses/compatibility.py:326-328` accepts a block when its `release_id` exists anywhere in the manifest. It does not require that release to match the block harness or the channel pointer. `match_release()` checks `block.release_id` only for release scope blocks at lines 413-420. Version, route, and target blocks at lines 421-448 ignore it.

An active block attributed to release `r1`, including a block whose release belongs to another harness, can therefore return `harness_version_blocked`, `connection_unavailable`, or `target_unavailable` after the pointer moves to `r2`. A read only probe built a Claude state containing a block attributed to the embedded Codex release. The manifest validated and the Claude match returned `harness_version_blocked`.

The contract says a new release covering the change restores support. Validate block and release harness identity, filter every block scope by the active release id, and add old release plus foreign harness fixtures.

Code: https://github.com/littleorgans/transport-matters/blob/f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22/api/src/transport_matters/harnesses/compatibility.py#L305-L332

### Major 3: Expired channel states can authorize compatibility

Confidence: 95/100.

`api/src/transport_matters/harnesses/compatibility_store.py:129-140` checks sequence, adapter revisions, product version, and release digests, then returns the manifest without evaluating `expires_at`. `match_release()` at `compatibility.py:379-449` has no trusted time input or expiry check.

A read only probe passed an active channel state with `expires_at="2000-01-01T00:00:00Z"` through the accepting verifier seam. Validation succeeded and matching returned `compatible`.

HARNESS-COMPATIBILITY.md explicitly requires that an expired update cannot activate. Parse and validate timestamps, evaluate expiry against an explicit trusted time, retain the last valid state on expiry, and add past, boundary, future, null, and malformed expiry fixtures.

Code: https://github.com/littleorgans/transport-matters/blob/f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22/api/src/transport_matters/harnesses/compatibility_store.py#L129-L140

### Major 4: Facet observability accepts incomplete and invented classifications

Confidence: 95/100.

`api/src/transport_matters/harnesses/compatibility.py:122` models `facet_observability` as `dict[str, FacetObservability]` without validating allowed keys or completeness. Empty maps, partial maps, and invented keys all validate. The shared fixture supplies only `wire_request`. Both embedded releases omit classifications for contract facets including certified routes and target catalog.

HARNESS-COMPATIBILITY.md requires the map to classify every facet as runtime observable or certification gated. Missing classifications leave open range enforcement undefined for those facets. Define the facet vocabulary once, require exact coverage, reject unknown keys, correct the embedded data, and add completeness fixtures.

Code: https://github.com/littleorgans/transport-matters/blob/f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22/api/src/transport_matters/harnesses/compatibility.py#L98-L124

### Major 5: Evidence digest fields accept malformed references

Confidence: 88/100.

`HarnessRouteCompatibility.evidence_digest`, `HarnessModelCompatibility.evidence_digest`, and `VersionBlock.evidence_digest` are unconstrained strings at `api/src/transport_matters/harnesses/compatibility.py:157-203`. The same module defines the SHA 256 format at line 57 and enforces it for release, fixture, schema, and release evidence digests at lines 145-153.

A release can be resealed over a route or target containing `evidence_digest="garbage"`, and a signed block can carry the same malformed value. Aggregate digest and signature checks then authenticate an invalid evidence reference. This violates the signed update requirement for internal digest and reference integrity and permits an attributed launch block without an auditable evidence digest.

Apply the shared digest validation to every evidence digest field and add malformed route, target, and block fixtures.

Code: https://github.com/littleorgans/transport-matters/blob/f8fe90db9aff4e8663b201ef4ab4a3c8c04d5d22/api/src/transport_matters/harnesses/compatibility.py#L145-L203

## Confirmed behavior

- `RejectAllSignatureVerifier.verify()` returns `False` for every mutable cached update.
- Channel sequence validation rejects equal and lower sequences.
- Release digest recomputation uses the shared `canonical_digest()` owner. Both embedded release digests recomputed successfully.
- `launch_service._intent_fingerprint()` uses `canonical_digest()`, and the guard test compares its bytes with the prior SHA 256 formula.
- `match_release()` returns the specified outcome codes for unavailable pointers, unorderable versions, below minimum versions, version blocks, route blocks, target blocks, and release blocks.
- Embedded data contains Claude `2.1.211` and Codex `0.144.4`, each with `minimum_version == baseline_version`. Stable and preview pointers are all paused. No Grok release or pointer ships.
- `detect_harness` is deleted. Repository search found no remaining reference.
- No new `--version` subprocess parser was added. `normalize_version()` only orders already extracted values.
- `harnesses/compatibility.py` is a pure computation leaf. Package resource I/O remains in `compatibility_store.py`.
- The existing fixture matrices cover below minimum, unknown, all four block scopes, supersession status, paused, revoked, missing pointer, tampered release content, stale and replayed sequence, missing adapter revision, cached rejection, embedded pause and activation, and embedded release digest consistency. They do not cover the five failures above.

## Code hygiene

Scope was limited to the 14 changed files. Every new file is below 700 lines. The largest new source module is `compatibility.py` at 449 lines. No changed function exceeds 150 lines. The largest function observed in the changed files is the preexisting `ControlPlaneLauncher._execute()` at 96 lines; new `match_release()` is 71 lines. Repository searches confirmed one compatibility digest owner, no private harness digest helper, no new version probe fork, the package resource loader precedent, and zero references to the deleted singular detector.

Craftsmanship verdict: The ownership split, reuse discipline, and fixture organization are strong. Five signed state integrity gaps prevent approval.
