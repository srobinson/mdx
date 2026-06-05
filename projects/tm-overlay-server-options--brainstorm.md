# Where the recorded overlay lives

Options analysis for TM v1. Scout seat, warroom `canvas-overlay-delta`.
Read-only pass over `scout/canvas-overlay-boundary`.

## Thesis

Stuart's stance holds, but the stated reason is the wrong one. The overlay
cannot live in the release distribution, and the binding constraint is not
that the overlay is per-user. It is that the overlay is *per harness
release*, and harness releases ship on a cadence TM's install path cannot
follow. The per-user part of the overlay is exactly the part that must
never reach a server.

That inverts the framing of the question. "Does the overlay go to a server"
is two questions wearing one coat, because the artifact is two artifacts:

- a **release overlay**, derived from the harness's own boilerplate (tool
  schemas, system parts, injected reminders), identical for every seat
  running that harness release;
- a **local overlay**, derived from one person's captured exchanges in one
  project, addressed against their own conversation blocks.

The first belongs on a signed server channel. The second must not leave the
machine. Every option below is scored against that split, and the options
that refuse the split are the ones that fail.

## What exists today

Grounding before argument. The current state constrains the answer more than
any of the five options do.

**Overlays are a browser-local draft feature with no apply path.**
`www/packages/inspector/src/stores/overlaysStore.ts:useOverlaysStore` persists
`Overlay[]` through `createFrontendPersistStorage()` under
`INSPECTOR_STORAGE_KEYS.overlaysStore`. Its own docstring states the scope
plainly: "This slice ships only the data model and the draft lifecycle. The
apply-at-intercept pipeline, chip strips, and per-field attribution arrive in
later slices" (lines 16-19). So there is no incumbent home to displace. The
storage decision is open, and it is open at the cheapest possible moment.

**The overlay payload is small, declarative, and typed.**
`www/packages/core/src/types/overrides.ts:Override` is `{kind, target, value}`
over a nine-member `OverrideKind` vocabulary. An overlay is a list of those
plus a name and an `OverlayScope`
(`overlaysStore.ts:OverlayScope` = `"shared"` | `{kind: "project", cwd}`).
This is kilobytes of declarative data, not a model, not a binary. Any of the
five distribution options is *mechanically* viable. The decision is made on
privacy, freshness, and commercial control, never on payload cost.

**TM already has the exact rails for signed per-release data, half-built.**
`api/src/transport_matters/harnesses/compatibility.py` defines release
entries, channel states, digests, and expiry.
`api/src/transport_matters/harnesses/compatibility_releases_v1.json` is the
package-embedded manifest.
`api/src/transport_matters/harnesses/compatibility_store.py:validate_channel_update`
already enforces the full update contract: schema strictness, known channel
identity, trusted signature, monotonic sequence, unexpired active pointers,
installed adapter revisions, TM version compatibility, digest integrity. And
it is deliberately inert:
`compatibility_store.py:_RejectingVerifier.verify` returns `False` with the
comment "Rejecting every mutable cached update keeps activation exclusive to
the package embedded manifest until real verification arrives; enabling it
later changes no schema because signature fields already round trip."

Read that again in the context of this decision. The hard part of a hosted
overlay channel, the signed-update contract with an embedded fallback, is
built, tested, and waiting on one thing: a trust root. The overlay decision
does not need to invent a delivery architecture. It needs to decide whether
the overlay rides the one that exists.

**The privacy boundary already has a precedent, written down.**
`api/src/transport_matters/harnesses/certification.py` module docstring: the
certification record "stores identities, digests, and normalized assertions
only; raw wire bytes, transcripts, terminal output, credentials, and absolute
paths never enter it." That rule was written for a different artifact and
applies verbatim here. Note in particular *absolute paths*: today's
`OverlayScope` project variant carries a raw `cwd` string. An overlay
uploaded as-is leaks the user's directory layout before it leaks a single
prompt.

**Tenancy does not exist yet.** `api/src/transport_matters/api/v1/owners.py`
is ten lines: `DEFAULT_OWNER = "local"`, documented as "Single-user local
deployment: every surface defaults to the `local` owner." Pricing at
$999/org and $99/seat requires accounts, and there are none. Whatever else
this decision does, it forces the account boundary into existence. The one
piece of prior art is
`api/src/transport_matters/api/v1/controlplane_auth.py:ControlPlaneGrantResolver`,
a bearer boundary with a per-request grant resolver, which is the shape a
seat token would reuse.

**The gate has a precedent shape.**
`api/src/transport_matters/harnesses/enablement.py:HarnessEnablementIntent`
is "one executor scoped user toggle persisted independently of installation."
The "Enable optimization" toggle is that shape one level up: an intent that
persists independently of whether the thing it enables is currently
reachable. Hold that thought; it decides the offline question.

## The nine kinds are not equally sensitive

The privacy axis is usually argued as a whole-artifact question. It is not.
`OverrideKind` splits cleanly by where the bytes come from:

| Kind | Bytes originate with | Publishable |
|---|---|---|
| `tool_toggle` | harness (tool name) | yes |
| `system_part_toggle` | harness (part index) | yes |
| `truncate_tool_result` | numeric limit | yes |
| `sampling_set` | numeric/enum | yes |
| `provider_extras_set` | provider vocabulary | yes |
| `tool_description` | user-authored, describes a harness tool | with review |
| `system_part_text` | may carry CLAUDE.md, project instructions | **no** |
| `message_text` | the user's own words | **no** |
| `message_block_toggle` | addresses a position in the user's conversation | **no** |

The token win Stuart is selling lives almost entirely in the top five rows.
Suppressing a tool the user never calls, dropping a system part, capping tool
results: those are harness-shaped, they repeat identically across every seat
on a release, and they carry no user bytes at all. The bottom three rows are
where the personal content is, and they are also the rows least likely to
generalize past the project that produced them.

This is enforceable at the type level rather than by policy. A publishable
overlay is a distinct type whose kind vocabulary is a strict subset, with the
project `cwd` structurally absent. Nothing downstream then needs to remember
the rule, and no reviewer has to catch it. Establish the invariant once, at
the boundary where a local overlay becomes a publishable one.

## The five options

### A. Shipped in the release distribution

The overlay is embedded package data, exactly like
`compatibility_releases_v1.json`, updated when TM ships.

*Privacy.* Perfect. Nothing derived from any user exists in it, because it is
authored centrally before any user has run anything. The per-user recording
workflow has no home at all under this option, which is not a privacy virtue
so much as a scope amputation.

*Gate coupling.* Perfect. TM operates offline, forever, unlicensed. Which is
the problem: it also means the overlay cannot enforce anything commercial.

*Churn response time.* Fatal. A harness ships releases weekly or faster; the
overlay's `target` addressing is release-shaped, so a release that reorders
system parts or renames a tool invalidates the overlay for every seat until
TM itself ships. TM's release cadence becomes the ceiling on the product's
core value. The embedded compatibility manifest already demonstrates this
failure mode in the adjacent domain; it is the reason `validate_channel_update`
exists at all.

*Seat/org distribution.* Trivial, because there is nothing to distribute.

*Licensing.* None. The artifact that gates operation ships inside the thing
being licensed. Anyone can run it.

**Verdict: viable only as the floor.** As the whole answer it makes the
product a slow follower of every harness release and gives away the gate.

### B. Local-only, recorded on the user's machine

Recording is the whole story. Each user runs the inspect/edit/save-as-overlay
loop against their own captured exchanges, and the result stays in their
store. This is closest to where the code already is.

*Privacy.* Perfect and honest. A wire observability tool that promises your
prompts never leave is a strong position, and it is the position TM's
architecture currently occupies by default.

*Gate coupling.* Perfect. Offline forever, degradation impossible, no network
in the hot path.

*Churn response time.* Bad in a subtle way. There is no central staleness,
but every user personally re-does the work on every harness release, and most
will not. The overlay quietly stops matching, and the failure is silent
unless release-pinning is enforced. Effective response time is "whenever that
particular user notices," which for most users is never.

*Seat/org distribution.* Bad at 40 seats. Forty people record forty
incoherent overlays against the same harness release, each rediscovering the
same five suppressible tool schemas. The org has no lever, no consistency,
and no way to correct a seat whose overlay is degrading their agent. This
directly contradicts the stated product promise that "the user never
maintains it," because under B maintenance is the user's job by construction.

*Licensing.* None, same as A, and worse: the value is generated locally, so
there is not even a central artifact to withhold.

**Verdict: the correct home for the user-derived layer, and only that layer.**
As the whole answer it breaks the no-maintenance promise and forfeits the
commercial model.

### C. TM-hosted overlay service

TM publishes overlays per harness release; the client fetches them,
authenticated per seat.

*Privacy.* Depends entirely on direction. Downstream-only (server publishes,
client fetches, nothing uploaded) is privacy-neutral and leaks only the fact
of which harness release a seat runs, which is already implicit in any
update check. Upstream (client contributes recordings) is where the exposure
lives, and the kinds table above says it is avoidable: contribute only
publishable kinds, and only on explicit per-overlay consent with a visible
diff of the exact bytes leaving. Silent telemetry-style contribution would be
a product-defining mistake for a tool whose entire pitch is showing you what
is being sent without your knowledge.

*Gate coupling.* This is the option's real cost and the sharpest question in
the brief. If "Enable optimization" gates TM operation, and enabling requires
an overlay, and the overlay requires a server, then TM has become a product
that stops working on a plane. That is unacceptable as stated, and it is
avoidable: the gate is an *intent*, not a *fetch*, exactly as
`enablement.py:HarnessEnablementIntent` is "persisted independently of
installation." Enablement persists; overlay resolution is what degrades. See
the degradation ladder below.

*Churn response time.* Excellent, and this is the decisive axis. A signed
channel update is hours from a harness release, not a TM release cycle, and
`validate_channel_update` already carries monotonic sequences and expiry so
a stale or replayed publish cannot activate.

*Seat/org distribution.* Excellent. One publish reaches every seat. This is
also the only option under which "the user never maintains it" is literally
true.

*Licensing.* Excellent and elegantly cheap. The overlay fetch *is* the
entitlement check. No separate license subsystem, no key file, no phone-home
distinct from the thing the client already wants. A seat token authenticates
the fetch;
`api/v1/controlplane_auth.py:ControlPlaneGrantResolver` is the existing
bearer shape to extend rather than duplicate.

**Verdict: correct for the release layer. Wrong if it is the only layer,**
because it has nowhere to put a user's own recordings and no offline story on
its own.

### D. Org-hosted / self-hosted

The org runs the overlay endpoint. TM publishes to the org; the org curates,
pins, and serves its seats.

*Privacy.* Best available for the enterprise objection. Nothing crosses the
org boundary, and the org can inspect every byte it serves. This is the
answer to the security review that will otherwise stall the $999 tier.

*Gate coupling.* Same shape as C, one hop closer. An org-internal endpoint is
reachable when the internet is not, which helps the office and does nothing
for the plane.

*Churn response time.* Adds a human review step to every harness release.
Realistically days, not hours, and orgs that staff this poorly end up worse
off than C. The mitigation is a pass-through default with opt-in pinning: the
org endpoint proxies TM's channel unless someone has explicitly pinned or
vetoed a release.

*Seat/org distribution.* Excellent, and it is the only option that lets an
org *veto*. That matters more than it first appears: a published overlay
edits tool descriptions and system parts, which is a behavior change shipped
to every agent in the org. Some org will need to say no to one, fast, without
waiting for TM.

*Licensing.* Workable but inverted. Self-hosting weakens the fetch-as-license
mechanism, so the org tier needs its entitlement bound to the publish
relationship (a signed org grant with an expiry the endpoint carries) rather
than to per-seat fetch traffic.

**Verdict: a deployment mode of C, not a separate architecture.** Treat it as
where the channel is pointed. It should not fork the resolution logic.

### E. Hybrid with local cache

Composition: published release overlay, plus local recorded overlay, plus an
embedded floor, resolved together and cached.

*Privacy.* Best of the set, and it is the only option that can make an
unqualified promise: user-derived kinds never leave, structurally, because
the publishable type cannot represent them.

*Gate coupling.* Best of the set. The cache is what makes the plane case
work, and the embedded floor is what makes the never-fetched case work.

*Churn response time.* Matches C, since the published layer is the same
channel.

*Seat/org distribution.* Matches C and D, since both are the same layer
pointed at different hosts.

*Licensing.* Matches C, with one deliberate hole (the cache grace window)
discussed in the objections.

*Cost.* Real. Two layers means a precedence rule, a merge, and an attribution
surface that can explain, per edited block, whether the change came from the
user, their org, or TM. That is more machinery than any single-home option.
It is also machinery the reveal already half-owns:
`overrides.ts:OverrideAudit` carries `chars_before`/`chars_after` per entry,
which is precisely the attribution primitive a layered overlay needs.

**Verdict: recommended.**

## Recommendation

**Publish the release overlay over the existing compatibility channel rails;
keep the recorded overlay local; resolve both in one composition behind the
enablement intent.**

Concretely:

1. **Make the overlay a release-pinned artifact with the same shape as
   `CompatibilityReleaseEntry`**: `release_id`, digest, signature, sequence,
   expiry. Do not write a second verifier. Extend
   `compatibility_store.py:validate_channel_update` or mirror its rules in one
   shared validator, and mint the trust root that `_RejectingVerifier` is
   already waiting for. One trust root serves compatibility and overlay
   together; two would be the same mistake twice.

2. **Pin overlays to harness releases and fail closed on mismatch.** An
   overlay recorded or published against release X must never apply to
   release Y, because `Override.target` addresses release-shaped structure.
   `compatibility.py` already owns the outcome vocabulary for this
   (`harness_version_unknown`, `harness_update_required`,
   `compatibility_release_unavailable`); reuse those outcomes rather than
   invent a parallel set.

3. **Make the fetch the license check.** A seat token authenticates the
   overlay fetch through the existing bearer boundary. No separate license
   subsystem. Org tier binds to a signed org grant so self-hosting stays
   enforceable.

4. **Enforce the publish boundary in the type system.** A publishable
   overlay's kind vocabulary is a strict subset (the top five rows above,
   plus reviewed `tool_description`), and it structurally cannot carry a
   project `cwd`. Follow `certification.py`'s stated rule: no raw wire bytes,
   no transcripts, no absolute paths. Contribution is explicit, per overlay,
   with a visible diff, defaulting to off.

5. **Degrade in three steps, never to broken:**
   - fetched overlay matching the installed harness release, or
   - last-known-good cached overlay for that same release, or
   - embedded floor overlay, and if none matches,
   - **reveal-only**: TM still shows what the harness sends, and applies
     nothing.

   Reveal-only is the important rung. TM's observability is what earns trust;
   optimization is what earns revenue. Never let the revenue gate switch off
   the trust.

6. **Precedence: local, then org, then published, then embedded floor.** One
   resolver, one attribution surface, `OverrideAudit` per layer so the reveal
   can name who changed what.

## The two hardest objections

**1. The gate becomes a network dependency for a local observability tool,
and no setting of the grace dial is right for both the pirate and the
passenger.**

A cached overlay that survives offline is, by definition, a licence that
survives revocation for the length of the cache. Make the window short and a
consultant on a two-week client site loses the feature they paid for; make it
long and the enforcement is theatre. Clock rollback beats any wall-clock
expiry on a machine the user controls. There is no dial setting that is
simultaneously honest to the paying passenger and effective against the
non-paying one.

The best available answer is to stop measuring grace in days and measure it
in harness releases: an entitled overlay for release X stays valid as long as
X is the installed release. That self-limits without a clock, because moving
to release X+1 requires a fetch anyway, and harness upgrade cadence is fast
enough to make indefinite offline use converge on reveal-only. It is still a
hole. It is a hole sized to "one harness release," which is defensible, and
it should be stated as a deliberate choice rather than discovered later as a
bug.

**2. The two-layer split rests on an untested empirical claim.**

The entire recommendation assumes the valuable overlay is harness-derived and
therefore publishable. If the real wins turn out to be project-shaped, this
repo's CLAUDE.md, this team's MCP tool set, this person's habit of pasting
long logs, then the published layer is thin, the local layer is the product,
the server is a licence turnstile wearing a value costume, and the $999 org
tier is selling curation of something nobody needed curated. Worse, the
architecture would have been chosen for a value split that does not exist,
and the offline cost in objection 1 would have been paid for nothing.

This is falsifiable cheaply and should be falsified before the server is
built. Record overlays independently on N machines against one harness
release, then measure overlap of `(kind, target)` pairs and the share of
total `chars_before - chars_after` attributable to the publishable kinds. High
overlap and a publishable-kind majority: publish, and the recommendation
stands as written. Low overlap: the honest architecture is B plus a thin
entitlement service, and the product should say so rather than route local
value through a server to justify a price.
