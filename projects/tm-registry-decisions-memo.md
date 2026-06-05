---
title: "Overlay Registry: Decisions Memo"
type: projects
tags: [transport-matters, overlay, registry, trust, decisions]
summary: "Analysis and one flat recommendation for each of the four Open Decisions in the overlay registry spec, re-derived under the v1 local disk backend."
status: draft
created: 2026-08-08
related: [transport-matters-spec-overlay-registry]
project: transport-matters
confidence: high
---

# Overlay Registry: decisions memo

Answers to the four Open Decisions in
`~/.mdx/projects/transport-matters-spec-overlay-registry.md`, re-derived under
the binding v1 transport: a local disk backend. Artifact files are versioned in
the repo beside the authoring worksheets landed in `docs/overlays/` at
`ca3eaec7`, served by the existing local TS gateway through an adapter that
speaks the exact registry response format, with initial operations at identity
so afters equal captures.

The disk backend changes the analysis in one specific way that runs through all
four answers. It removes the network, the account, and the tenant from v1, and
it leaves the contract, the validation path, and the client state machine fully
exercised. Every decision below is therefore answered as a contract decision
with a deferred deployment, never as a decision the disk era gets to skip.

The worksheets already carry per-entry `sha256` values over exact captured
fields, which is the same content addressing the spec's
`system:sha256:{digest}` and `msg:sha256:{digest}` targets resolve against. An
identity artifact built from a worksheet has `preimage_sha256` equal to the
captured digest and a replacement equal to the captured text, so it proves
selector resolution, preimage matching, freeze, and audit end to end at a
measured zero delta.

---

## 1. Org channel in v1

**Recommendation: vendor plus local only. No org channel, and no org shaped
placeholder beyond the provenance fields already specified.**

An org channel is not a data structure, it is an authority. Promoting an
artifact to an organization requires someone entitled to promote, a tenant the
promotion binds to, and a precedence rule that survives a second writer. With a
disk backend none of those three exist: the file is whatever the release ships,
the tenant is the person running the binary, and the promoter is the same
person again. Building the channel now buys a third precedence layer whose
writer is the same hand that wrote layer one, which is the defect class the
review already caught once when browser drafts sat in the precedence table with
no live writer. The cost of leaving it out is close to nothing, because the
artifact already carries `publisher`, `author`, `author_kind`, `approver`, and
`publication_id` as signed provenance, so an org artifact is a provenance value
and a delegated signing key rather than a new document shape or a new
application path. One thing should be held firm through the disk era: keep
`tenant_subject` required and verified against the current account subject even
when that subject is a fixed local constant, so the field never relaxes to
optional and then has to be tightened under a live client. Org becomes real at
the first moment two seats share one curated artifact that neither seat
authored, which cannot happen before the remote transport carries a token with
a tenant claim.

*What would change it:* a customer paying for seats before the remote transport
ships, which would make a shared curated artifact a delivery requirement rather
than a roadmap item.

---

## 2. Registry and accounts topology

**Recommendation: charter one service with two contracts. The artifact origin
contract is the one the disk adapter implements today, and the account token
issuer contract is separate from it and never called by the registry.**

The question answers itself if the disk adapter is taken seriously as a
conformance test. That adapter serves the exact registry response format with
no account, no token, and no entitlement lookup, and if the registry contract
is drawn correctly the adapter is a complete implementation of it rather than a
subset. That forces the useful boundary: the registry resolves a tuple to
signed bytes and does nothing else, entitlement arrives as a verified claim
inside the bearer token rather than as a lookup the registry performs, and the
account authority mints tokens without ever touching artifact bytes. Under that
split, one deployable is the right call for the remote era, because two
deployables would add an availability dependency and a shared table between
modules that the contract says must not share state, and the operational cost
lands before there is a tenant to justify it. Splitting later is then a
deployment change with no client change, which is the property worth buying.
The signing authority stays a third boundary under either topology and is not
part of this decision. Stated as a rule the code can be held to: the registry
never performs a database read on user identity to answer a request, and any
requirement that it must is the signal that the topology decision needs
revisiting rather than a reason to weaken the rule.

*What would change it:* a residency or compliance requirement that puts billing
identity in a different jurisdiction or trust tier from artifact bytes, which
turns the module boundary into a deployment boundary immediately.

---

## 3. Trust root mechanics

**Recommendation: Slice 2 ships real signing and a real production verifier
over the local disk files, with a build time development root whose custody is
the deferred part. No test verifier reaches a production apply path, at any
point, in either era.**

The reason Slice 2 was promoted ahead of cache, freeze, and apply was that
`RejectAllSignatureVerifier` at `compatibility_store.py:87` is the only thing
currently standing between a downloaded document and the request pipeline, and
no apply path may exist while it is the packaged verifier. A disk backend does
not weaken that argument, it sharpens it: a file on disk inside the release is
exactly the shape of input an attacker with local write access controls, and
the release integrity story does not extend to a file the gateway reads at
runtime. If the disk era served unsigned artifacts behind a test verifier, then
the later remote swap would change the transport and the trust path together,
and the whole justification for the disk bridge, that the swap is transport
only, would be false. So keep every verified thing real: canonical bytes from
`canonical_json`, detached signature through the existing `SignatureVerifier`
seam at `compatibility_store.py:79`, the same keyring for compatibility and
overlay updates, and `RejectAllSignatureVerifier` retained as the fallback when
no trusted root is configured. Defer only custody. The disk era signs artifacts
at build time with a development key held in the repo, ships the public half as
the packaged trusted root, and accepts openly that anyone with the repo can
mint a locally trusted artifact, which is tolerable only because the product is
pre release and the same person owns both halves. When remote arrives, custody
becomes an offline root that signs a keyset rather than artifacts, a constrained
online intermediate in KMS or HSM that signs artifacts, and root signed keyset
distribution to clients. Rotation runs the intermediate on a period shorter than
the longest artifact expiry, and verification keys are retained for the longest
artifact lifetime so held caches keep validating. Re signing preserves the
immutable `content_sha256` and produces a new signed envelope revision, so the
artifact identity never moves under a frozen run. The development root must be
placed on the revocation list at that same moment, otherwise a key that lived
in a git history stays trusted forever. A later org channel receives a
separately delegated key scoped to its `tenant_subject`, never the vendor
signing key.

*What would change it:* a decision to ship the disk backend to anyone outside
the team before the remote transport lands, which would make a repo held
signing key an actual compromise rather than an accepted pre release cost.

---

## 4. Entitlement lapse and offline grace

**Recommendation: pre wire a signed grace deadline now, defaulted to fourteen
days, with the terminal state reached at the earliest of the signed deadline,
artifact expiry, or harness version change. The v1 disk era carries the field
and implements the ladder with the `403` branch unreachable.**

There is no `403` in the disk era, which makes this the cheapest possible
moment to decide it, because the client state machine can implement the full
ladder against a field that is present in every artifact and never has to be
retrofitted under live traffic. Fourteen days is the number because the spec's
own artifact carries a fourteen day window between `issued_at` and
`expires_at`, so a grace deadline on the same cadence never outlives the
artifact it protects, and because harness churn ends grace first in practice
anyway. Claude Code moved 2.1.224 to 2.1.225 overnight, and since an artifact
binds to an exact version, a lapsed seat on an updating harness typically falls
to `PASSTHROUGH` within days regardless of what the deadline says. The ladder:
on first `403` the exact cached artifact keeps applying and the human surface
shows the lapse with its deadline; through the window nothing about application
changes; at the earliest of the three bounds the state becomes `PASSTHROUGH`
with the lapse still shown and the reveal still live; the wire is never blocked
at any rung. Two guards make the deadline mean something. It is signed into the
tenant resolved artifact, so an unsigned `403` cannot extend authority and a
locally computed value cannot invent it. It is bounded by the accepted cache's
recorded first lapse observation, so a rolled back local clock shortens grace
rather than extending it. The disk era default is `issued_at` plus fourteen
days written by the build time signer, which exercises the field without ever
exercising the lapse.

*What would change it:* an enterprise agreement requiring entitlement
enforcement to be immediate and provable, which replaces the ladder with the
deterministic `PASSTHROUGH` baseline already specified as the fallback.
