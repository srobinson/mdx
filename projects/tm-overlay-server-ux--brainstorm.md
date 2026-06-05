# TM overlay server dependency: journey consequences

Fable seat brainstorm, 2026-08-07. Independent pass, no coordination with other seats.
Grounding: the five wireframes at `~/.mdx/projects/tm-ir-overlay-ux/fable/` (reveal → one
"Enable optimization" toggle → operating state), the Override/OverrideAudit contract, and
Stuart's stance under test: the overlay cannot ship in the code distribution; TM calls out
to a server to get it.

## Thesis

The server dependency is acceptable exactly when the network is needed at **acquisition**
and never at **operation**. The overlay is a small signed artifact keyed by fingerprint
(harness · version · model). Fetch it once per fingerprint, pin it locally, verify it
locally, apply it forever from cache. Then every degraded state collapses to one question,
"do I have a cached artifact for this fingerprint?", and the answer decides between
last-known-good and pass-through. Nothing ever blocks the wire.

One decomposition drives all of this: **the reveal is local, the cure is remote.** Token
reveal derives from TM's own capture of the run; it needs no server and must never degrade.
Only the curation artifact comes from the server. So TM's observability value survives any
outage, and the outage surface is limited to "optimization is stale or pending", which is a
chip, not a wall.

## 1. The gate moment needs network

The gate screen (00, gate state) asks the user to flip one switch. Enabling means fetching
the precomputed overlay for the user's current fingerprint. Three failure states, three
different answers.

### First-run offline

Never brick the gate. The reveal already rendered from local capture, so the screen is
doing its job. The switch stays interactive but resolves to a pending state:

```
┌─ Enable optimization ────────────────────────────────┐
│  [ ✓ ] Enabled — armed, pending activation           │
│                                                      │
│  TM has analyzed claude 2.1.161. Fetching your       │
│  optimization needs a connection once. It will       │
│  activate automatically when you're back online.     │
│                                                      │
│  Until then requests pass through unchanged.         │
└──────────────────────────────────────────────────────┘
```

The user's intent is recorded locally; activation completes silently on reconnect and the
operating card appears with its savings number. This is acceptable because the promise is
honest: nothing is optimized yet, and the UI says so in one line.

Consequence for the strong-gate variant ("enable optimization to start using TM"): it
survives only as "flip the switch to start", not "be online to start". The commitment is
the gate; the fetch is not. If the strong gate literally blocked capture until a server
round-trip succeeded, a dead vendor server would brick a paying customer's coding agent on
day one. Disqualifying.

### Server down (established install)

Invisible at the gate and nearly invisible in operation. The cached artifact applies
exactly as yesterday. The only surface is a staleness chip in the operating card:

```
┌─ Optimization active ── claude · 2.1.161 ────────────┐
│  −2,741 tok per request (−17.6%)     [ evidence → ]  │
│  ⚠ last sync 3 days ago — running on cached          │
│    optimization                                      │
└──────────────────────────────────────────────────────┘
```

Acceptable indefinitely. The artifact was correct for this fingerprint when fetched and the
fingerprint has not changed; there is nothing to be stale *about* until the harness updates.

### License lapsed

The one state where degradation is policy, not accident. Two rules:

- Lapse **stops optimizing**, it never **stops working**. TM sits in the traffic path; any
  enforcement that blocks the proxy is a self-inflicted outage inside the customer's dev
  loop, and the story told afterwards is "TM broke our agents", not "we forgot to renew".
- Grace window first. Cached overlay keeps applying for N days with a visible banner
  ("license lapsed · optimization continues until Aug 21"), then falls to pass-through with
  the reveal still live. The reveal is the best renewal ad TM has: the user watches the
  15,590-token requests come back.

```
lapsed →  grace (cached overlay applies, banner)  →  pass-through (reveal shows the cost)
                    never: blocked wire
```

## 2. The harness-release moment

claude ships 2.1.225. TM sees the new fingerprint on the first outbound request.

**Rule: an overlay applies only to the exact fingerprint it was recorded against.** The
audit machinery would make cross-version misapplication visible (targets go absent, entries
go no-op), but visible-after-the-fact is the wrong bar for an artifact that rewrites
prompts. Conservative default: new fingerprint, no artifact, pass through, and say so
quietly.

Happy path, server reachable and the new release already analyzed (this is the product's
operational promise — turnaround on harness releases is what the subscription buys):

```
feed ─────────────────────────────────────────────────
  ✓ TM re-optimized for claude 2.1.225
    −2,690 tok per request (−17.1%)     [ evidence → ]
    fetched 09:14 · applied from next request
```

The user ideally sees nothing at decision time — no consent re-prompt, because consent was
given to the *toggle*, i.e. to the delegation, not to one artifact version. Re-consenting
per release would recreate the harness-churn burden the product exists to absorb. The feed
entry plus evidence link is the accountability surface.

Gap path, release is newer than the server's analysis:

```
┌─ Optimization ── claude · 2.1.225 (new) ─────────────┐
│  New release detected. TM is preparing the           │
│  optimization for 2.1.225 — requests pass through    │
│  unchanged until it lands.                           │
│  2.1.161 optimization retained for rollback.         │
└──────────────────────────────────────────────────────┘
```

Honest, quiet, self-resolving. The measurable SLO behind it (time from harness release to
artifact published) is the number the org admin should be able to see.

## 3. Org and seat distribution

Model the server as a **fingerprint-keyed artifact registry with org namespaces**, because
that is what it is. Admin buys 10 seats; each seat client authenticates with a seat token
and pulls by (org, fingerprint). Three artifact channels, one precedence rule:

```
        TM optimizer (vendor-published, per fingerprint)
              │  baseline for everyone
        org overlay (admin-promoted, per fingerprint)
              │  overrides vendor baseline for the org
        local named overlays (this machine, user-recorded)
              │  power-user surface, screen 01/02, unchanged
```

Precedence must be a single stated rule (org > vendor at the same fingerprint; local named
overlays remain the separately-toggled advanced surface, not silently merged). A second
writer with no precedence rule is exactly the defect class the review checklist names.

Seat provisioning is boring on purpose: admin invites, seat activates with the token, the
gate screen is identical except the provenance line reads "published by TM · promoted by
your org admin". Nothing about the journey forks per seat.

## 4. Trust display: delegation, never injection

The overlay came from a server and rewrites prompts. What keeps that from feeling like
injection is one property: **trust rests on local verifiability, not server claims.** The
savings number the server implies is never what the UI shows; the UI shows what the local
audit measured on this run's actual bytes.

Provenance manifest, rendered wherever the overlay is named:

```
┌─ TM optimized · claude · 2.1.161 ────────────────────┐
│  origin      TM optimizer                            │
│  published   2026-08-01 · artifact a3f19c (signed ✓) │
│  applies to  claude · 2.1.161 · claude-fable-5       │
│  changes     9 overrides · system 4 · tools 4 ·      │
│              sampling 1                              │
│  [ inspect every change → ]   (screen 03, per-block  │
│                                before/after diff)    │
└──────────────────────────────────────────────────────┘
```

Rules:

- Nothing applies that cannot be inspected in one click. The evidence link resolves to the
  existing three-pane correlated view (original IR / curated IR / audit) — that surface is
  already built and is the whole trust story; the server design adds only the provenance
  header above it.
- The artifact is signed; the client verifies the signature and shows the check. A server
  compromise then degrades to "no new artifacts", not "arbitrary prompt rewriting", because
  cached verified artifacts keep applying.
- Every audit entry already carries per-entry provenance (the one contract addition flagged
  in the wireframe round); with three channels it becomes load-bearing: an entry says
  *which* overlay, from *which* channel, changed this block.
- The overlay is declarative (the nine Override kinds), never code. That is worth stating
  in the trust copy: the server ships data the client interprets, not behavior it executes.

## 5. Where ad-hoc recording output goes

Record locally, publish deliberately. The breakpoint inspect/edit/save-as-overlay loop
produces a **local named overlay** exactly as it does today — no network in the loop,
because the recording session is live agent traffic and must not depend on anything.

Then one explicit door on the saved overlay:

```
local overlay "trim webfetch schema"
   [ enable locally ]   [ publish to org → ]

publish → server: artifact + recorder identity + source
          fingerprint + evidence bundle (the recording
          run's before/after audit)
        → admin reviews evidence, promotes to org
          channel for that fingerprint
        → seats pick it up as an org overlay, feed
          entry with provenance "recorded by stuart ·
          promoted by admin"
```

Publishing without evidence is not offered; the evidence bundle is generated from the
recording run automatically, so the admin's review screen is the same screen-03 diff every
other trust surface uses. One rendering path, three channels.

## Recommendation: least-worst degraded mode

Cache-first with honest chips. Concretely, on server-unreachable:

1. Cached artifact matches current fingerprint → keep applying it, show the "running on
   cached optimization · last sync" chip. This is the normal degraded mode and is fine
   forever.
2. No cached artifact for this fingerprint (first run offline, or new release during an
   outage) → pass through unchanged, one-line pending notice, auto-resolve on reconnect.
3. Never block the wire, never silently pass through when the user believes optimization
   is active — the chip is mandatory in state 2 because the user is paying for a delta
   that currently is not happening.

Rejected alternatives: blocking runs (vendor outage bricks customer agents), silent
pass-through (invisible spend change breaks the trust contract), cross-version reuse of a
cached artifact (prompt-structure drift; conservative exact-fingerprint match plus fast
server turnaround is the right split of risk).

The one-line thesis: make the server a registry of small signed facts that the client
verifies and caches, and the dependency stops being a runtime dependency at all.
