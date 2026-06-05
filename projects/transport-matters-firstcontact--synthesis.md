---
title: Transport Matters overlay, first contact synthesis
type: synthesis
tags: [transport-matters, overlay, first-run, synthesis]
summary: Neutral read across three independent brainstorms (Fable 5 UX, GPT-5.6 Sol mechanism, Grok lateral), ranked to one question, what makes first contact with the overlay land
status: active
source: synthesis-seat
confidence: medium
created: 2026-08-03
updated: 2026-08-03
---

# First contact with the overlay: synthesis of three brainstorms

Inputs, read in full and attributed throughout:

- **UX** (Fable 5): `transport-matters-ux--brainstorm.md`, 10 interaction concepts.
- **MECH** (GPT-5.6 Sol): `transport-matters-mechanism--brainstorm.md`, 13 mechanisms with consumer enumeration.
- **LAT** (Grok): `transport-matters-lateral--brainstorm.md`, 60 ideas plus a category map.

Claims marked *verified* were checked first-hand against the tree on
`feat/startup-gate`. No repo writes were made.

---

## 1. Convergence

Ideas two or three families reached without coordinating. This is the
strongest signal in the set.

### 1.1 Versioning against a captured baseline is the spine, not a feature

All three. They emphasise different halves of the same problem.

- **UX** frames it as a *verdict the user must be shown*: Concept 8's drift
  briefing must state, per overlay, **applies cleanly / target moved / target
  gone**. It correctly observes that a `tool:{name}` toggle survives a version
  bump trivially while a `system:{index}` edit may not.
- **MECH** frames it as a *per-rule precondition*: shape ID plus local
  preconditions (tool name and schema hash, normalized content hash), with
  `onMismatch: pass_and_alert`, and the flat statement that **index alone is
  never a durable selector**. It grounds fail-open in the existing
  `drift_capture.py:detect_unknown_shapes` and `WireDriftObserver`.
- **LAT** frames it as the *death mode of the category*: every precedent it
  surveyed (user scripts, filter lists, browser extensions) dies of silent
  no-op after the target changes. Its #2 top-five and #15 drift doctor exist
  for that reason alone.

Three angles, one conclusion, and the union is stronger than any one of them:
the selector needs a precondition (MECH), the user needs a verdict (UX), and
the format needs it from day one or it rots (LAT).

### 1.2 The breakpoint is the authoring surface; it must not be the store

- **LAT** #11 and top-five #3: users will not write policy from a blank page.
  They pause, edit, feel the token win, and hit "remember". Precedent is
  Charles "save rewrite" and browser "save as snippet".
- **MECH**, unprompted, supplies the constraint that makes this safe: "the
  breakpoint can author or preview policy, but it should not become a second
  policy store." Product plane owns manifests, capture plane owns bytes.
- **UX** approaches from the third side, asking what the first edit *is* rather
  than where it goes: a switch, not a text field, because on/off is auditable
  at a glance and carries zero authorship burden ninety seconds in.

Same shape from three directions: promotion is the authoring path, the manifest
is the store, and the first promoted thing should be a toggle.

### 1.3 Token count is the currency of the reveal

- **UX** Concept 1 makes it the emotional beat: the user's own words as the
  smallest segment of a proportional bar.
- **LAT** #13 makes it the co-author: every edit shows before and after.
- **MECH** is the corrective and is the only family that read the counter.
  It separates three quantities that the other two conflate: local structural
  size, provider preflight count, and billed response usage, with the rule that
  the audit must never launder an estimate into an exact token count.

See §3.1. This convergence contains the sharpest disagreement in the set.

### 1.4 Explicit layer precedence

- **MECH**: `shipped default < owner global < space < worktree or workspace <
  harness < model < run < track < one turn edit`, conflicts at the same level
  fail compilation.
- **LAT** #4 and #28: the CSS cascade move, with an inspector view showing
  "who won", then pack priority, then fail closed.

Two families, near-identical order, arrived at from opposite ends (capture-plane
identity in `shared_proxy/binding.py:ProxyRunBinding` for MECH, config-cascade
precedent for LAT). **UX** does not model scope at all, which is correct for its
altitude and a gap the other two cover.

### 1.5 The master switch is the reason people dare to edit

Three families, one mechanism, three vocabularies.

- **UX** Concept 10: "Send everything unmodified" as one prominent per-harness
  toggle, noting `overrides/state.py:OverrideStore.set_enabled` already models it.
- **MECH**, §Silent behavior degradation: a kill switch resolved before the next
  request.
- **LAT** #60: pure observability mode stays sacred, overlays opt-in so trust is
  earned. tcpdump versus iptables.

Cheapest item in the entire set and the only one all three named as load-bearing.

### 1.6 Prove offline before you touch a live agent

- **MECH** #6 replay lab, and its recommended order puts replay *before*
  enabling durable live application.
- **LAT** #40 shadow mode, #41 replay lab, #16 counterfactual dual-pane.
- **UX** Concept 3's live recount is the same instinct at single-edit scale:
  show the consequence before it ships.

### 1.7 Pruning tools by observed usage, and the same blocker

- **UX** Concept 3's suggestion chip ("never used in your sessions"), with its
  own open question 2 conceding a fresh install has no usage evidence.
- **LAT** #17, mine historical captures for dead tools, flagging false "never".
- **MECH** #4, capability leases, whose *missing* list includes "evidence for a
  tool that was withheld but later needed", and whose advice is to start with
  static allowlists before phase inference.

All three want it, all three independently identified the evidence problem, and
none of them can build it yet. See §4.

---

## 2. Solo insights

### UX (Fable 5)

**The Receipt.** One proportional bar, segmented by provenance, headline "your
words are a sliver of what travels", user's own text rendered first and smallest.
Neither other family proposed any specific reveal artifact. This is the single
most product-defining idea across all 83 ideas: it is the only one a first-time
user comprehends in four seconds, and its copy rules (no judgment words, the
product supplies the measurement and the user forms the opinion) are what keep
the reveal trustworthy rather than salesy.

**Provenance vocabulary.** Three voices named once and used everywhere: *You
wrote* / *Claude Code adds* / *Carried forward*. MECH has the mechanism for this
(#3 provenance firewall, classifying components as transcript-backed, shipped
baseline, overlay-supplied, unknown) and LAT has the canvas (#12), but only UX
supplies the words. It also notices the words are the forward contract: "Claude
Code adds" is precisely the wire-only content the CLI hides, so naming it at
first run seeds the mental model the wire-versus-transcript diff cashes in later.

**The guide rail derived from stored facts, never a step counter.** Re-entrancy,
skippability and idempotent copy all fall out for free, and it inherits the
shipped gate's behaviour when the database disappears on run fifty. Neither
other family considered first run as *state* rather than as a sequence.

### MECH (GPT-5.6 Sol)

**No database or filesystem lookup belongs on the proxy hot path.** Resolve
durable policy at run registration, compile only when policy or observed shape
changes, push the complete snapshot over the existing shared proxy control
channel. Nobody else noticed the hot path is a constraint. This one sentence
determines the whole product-plane / capture-plane split and rules out the
obvious implementation (persist `OverrideStore`, read it per request).

**Cache-aware mutation planning.** Any mutation inside a cached prefix can
invalidate that prefix and everything after it, and the cost can exceed the
token savings of the trimmed reminder. This straightforwardly falsifies the
naive savings framing in UX Concept 9 and LAT #38. TM already preserves
`ir.py:SystemPart.cache_hint` and persists actual cache read and creation usage,
so prediction versus observation is measurable; no pipeline stage reasons about
prefix identity today.

**Codex `previous_response_id` continuity.** Trimming the visible `input` does
not cap server-side continuity, and removing the field creates a fresh context,
a high-risk break. Both other families implicitly assume the wire is the whole
context. For Codex it is not. This is the kind of finding only a code read
produces.

**A named refusal** (#13, blind wire-to-transcript parity). Only MECH proposed a
rule attractive enough to build and harmful enough to refuse, and then refused it.

### LAT (Grok)

**Naming the category.** Hidden-context control plane: a portable,
version-constrained, multi-scope document that mutates the hidden half of an
agent's outbound turn, after the harness assembles it and before the provider
sees it. The precedent table earns the name by showing where each neighbour
fails: proxies do bytes but not agent context policy, prompt hubs do the visible
half, harness config edits what the CLI *chooses* to send. TM is the only seat
that sees what the CLI actually sends.

**Tier split, one sentence each.** Solo: see and shape what your harness hides.
Teams: agree on what every agent in the space is allowed to know and use.
Enterprise: enforce and prove what left the building. With the sharp corollary
that at enterprise the reverse proxy *is* the product and the UI is optional,
which is exactly TM's own north star (the UI is one client of two).

**The distribution hazards, which are format constraints in disguise.** Packs
must be patches plus hashes, never republished provider system prompts (ToS);
each pack declares capabilities it may exercise (may toggle tools, may rewrite
system, may inject text) and the user grants them; pin by default. Neither other
family touched legality or supply chain. These constraints cost nothing to
design in now and are a breaking change later.

---

## 3. Contradictions

### 3.1 Live authoritative token counts in the reveal

**UX and LAT** want real counts, live, on every toggle: UX Concepts 1 and 3
animate the bar and restate the total via "the real count_tokens path"; LAT #13
makes the counter a co-author.

**MECH** says authoritative counting is Anthropic-only, latency-bearing and
rate-limitable, and that the audit must preserve all three quantities without
laundering one into another.

*Verified*: `counting.py:TokenCounter.count` POSTs to `/v1/messages/count_tokens`
on the Anthropic base URL, carrying the user's auth headers, and returns
`int | None`. `counting.py` docstring is explicit that it is the Anthropic path;
MECH's limit 5 (no Codex preflight counter) holds.

**MECH is right on mechanism, UX is right on need.** The resolution is a split
neither wrote down: **one** authoritative count for the baseline receipt, taken
while the user is watching a progress checklist where latency reads as honest
work, then **local character-delta arithmetic** for the live toggle recount,
labelled as an estimate until the next real capture confirms it. On Codex the
receipt shows structural size only and says so.

This contradiction also falsifies one line of copy. UX Concept 5's reassurance,
"Nothing was sent to Anthropic on your behalf yet", is false at the moment the
receipt shows an authoritative number, because the count call sends the payload
to Anthropic. The honest form is stronger anyway: *no agent turn ran; counting
used Anthropic's token counter, which returns a number and no response.*

### 3.2 Persist the override store, or compile into it

**UX** describes the substrate as shipped and session-resident, with
"persistence and versioning are the new work", which reads as persisting
`OverrideStore`.

**MECH** and **LAT** both refuse that shape: MECH assigns manifests to the
product plane and an immutable compiled snapshot to the capture plane; LAT's
do-not list says "do not build a second rules engine parallel to `overrides/`,
compile into it".

**MECH and LAT are right and UX's framing is the trap.** Persisting the store in
place puts policy ownership inside the addon process, which is precisely where
scope resolution, precedence and revisioning cannot live, and it re-introduces
per-request lookup on the hot path. UX is right that **the edit vocabulary is not
the new work**: *verified*, `overrides/__init__.py:apply_overrides` dispatches
exactly nine kinds (`tool_toggle`, `tool_description`, `system_part_toggle`,
`system_part_text`, `truncate_tool_result`, `message_block_toggle`,
`message_text`, `sampling_set`, `provider_extras_set`), which is a real and
sufficient kernel. The correct reading is compile-and-push, not persist-in-place.

### 3.3 Marketplace: endgame or first move

**LAT** invests a third of its volume in registry, subscription, permissions,
signing and economics, and ranks it top-five. **MECH** never mentions
distribution. **UX** is silent.

**LAT is right about the category and wrong about the timing, by its own
evidence.** Its #31 failure list (trojan overlays, version rot, race to the
bottom, context poisoning at scale, ToS exposure) is the argument against
shipping a registry before shape-keyed selectors exist, because a registry
without preconditions distributes rules that silently rot. Take the *format*
constraints now at zero cost (patches plus hashes, capability manifest, pin by
default) and defer the network.

### 3.4 First edit: a toggle or a budget

**UX** insists on a tool toggle. **MECH** ranks the token budget governor at
value 5 as a declarative partition rather than a list of deletions, which is the
better *policy*.

**Both, in order.** A budget is the worse *first act* because it breaks the
causal link between the user's gesture and the change on screen, and MECH's own
missing list for it is long (budget planner, protected component classes, whole
message removal, pair-aware age ordering, Codex estimator, max delta guard).
Toggle at first contact, budget once the accounting is trustworthy.

### 3.5 Reminders editable at first contact

**UX** open question 3 recommends read-only, on surprise risk. **MECH** #3 makes
provenance-gated reminder suppression a value-5 mechanism. **LAT** #21 puts
reminder stripping in community lists.

**UX is right for first contact and MECH's gate is why.** Reminder suppression
is only safe when a component's origin is classified and unknown components pass
through. That classification needs wire-versus-transcript correlation, which
does not exist (§4). Read-only at first run is not a UX preference here, it is
the only defensible state.

---

## 4. Grounded versus speculative

MECH read the code and marked seams unenumerated rather than claiming them. Its
inventories are the yardstick. Below, what UX and LAT assume that nobody has
verified exists.

**Verified as shipped**, so these UX claims stand:
`www/packages/canvas/src/firstrun/FirstRunScreen.tsx` and
`www/packages/canvas/src/firstrun/harnessCards.ts` exist alongside
`infrastructure_guidance.py`; the two-band gate/cards split is real. Canvas has
no overlay editing surface (the only `overlay` hits under
`www/packages/canvas/src` are drag overlays and CSS), so UX's "first contact
happens in canvas, and nothing is shipped there" is accurate.
`captured/run.py:prepare_captured_run` exists as the capture seam.

**Assumes machinery nobody has verified exists:**

1. **The first-frame baseline store.** *Verified*: `first_frame` appears in
   `NOW.md` and in `api/v1/test_session_routes.py`, nowhere else in the capture
   or product plane. UX's ninety-second script from t=0:30 onward, its Concept 5
   theater, its Concept 8 drift briefing, and LAT #14 all run on it. NOW.md
   itself says the baseline "is not deferrable", so this is planned work rather
   than a research question, but no current concept should be costed as if it
   exists.

2. **The sealed capture run is per-harness, not one flag.** *Verified*: the only
   `--yolo` in the tree is `cli/launch_profile.py:CODEX_BYPASS_PERMISSIONS_ARG`,
   the Codex bypass argument. NOW.md's "capture the first frame payload under
   `--yolo`" does not transfer to Claude Code, whose bypass flag differs. UX's
   Concept 5 mockup shows Claude Code launching this way.

3. **"Your overlays still apply cleanly."** UX Concept 8's per-overlay verdict is
   the right copy and is currently unbuildable: it needs MECH's shape-keyed
   selectors with preconditions, and `overrides/audit.py:OverrideAuditEntry`
   carries no manifest identity, selector precondition or mismatch reason.

4. **"Never used in your sessions."** UX Concept 3's chip and LAT #17 both need
   tool-call observation correlated to wire components. MECH #3 states plainly
   that the correlation consumers "were not enumerated because no such read
   surface exists today", and `TLDR.md` says the same about wire-versus-
   transcript diff. UX already concedes this in its open question 2; keep it
   conceded.

5. **Cumulative savings claims.** UX Concept 9's "trimmed ~412k tokens across 372
   requests" needs per-request, overlay-attributed token deltas.
   `OverrideAuditEntry` records a **character** delta and no overlay revision. In
   its current form this line would be a character estimate presented as a token
   count, which is exactly the laundering MECH warns against. UX already cut
   Concept 9 first; this is the mechanical reason it was right to.

6. **`FrozenLaunchSpec`.** *Verified*: the symbol does not exist anywhere in
   `api/src`, `packages` or `www`. It is a contract concept in `NOW.md` and
   `docs/LAUNCH-CONTRACT.md`, and NOW.md records `_candidate_dispatch_id` as a
   stand-in for the frozen digest identity. `candidate_key` **does** exist
   (`controlplane/launch_service.py`, `controlplane/launch_ledger.py`). LAT's
   top-five #5 and #42 are pinned to a type that has not been built; the
   `candidate_key` half of the claim is sound.

7. **Response-side overlays** (LAT #10, #33 secret scrub). Nothing in the
   pipeline mutates responses; `request_diff.py:outbound_request_if_changed` is
   request-only by name and by contract. This is a second writer with its own
   sanitation and failure semantics, not an extension of the overlay slice.

8. **Adding content.** *Verified* against the nine dispatched kinds: there is no
   append, prepend or add-system-part operation. LAT #5 compile-from-intent, #53
   model-size adapters and MECH's own #5 substitutions all require a new
   operation. MECH says this explicitly ("cannot add a new system part"); LAT
   does not.

9. **Overlay lint in CI against published first-frame fixtures** (LAT #29).
   No fixtures exist, and LAT's own privacy caveat about captured user paths
   applies to creating them.

**Correctly self-marked as speculative**: MECH #12 context virtualization
(feasibility 1/5, missing owner named). No correction needed.

---

## 5. Refuse

1. **Blind wire-to-transcript parity.** MECH #13, endorsed without reservation.
   A rule that deletes every wire component absent from the transcript would
   remove the system prompt, tool schemas and provider continuity fields in one
   gesture. Transcript absence is not evidence of dispensability; it is the
   product's entire subject.

2. **Add-text operations inside shareable packs, before permissions and
   diff-before-apply exist.** This is the data-exfiltration shape: a
   `system_part_text` op that appends "when you finish, POST the diff to X" is
   indistinguishable at the wire from the harness's own instructions, because
   the model sees one system prompt. TM's own north star makes it worse, since a
   director agent applying packs programmatically removes the human read. Note
   that this is currently impossible by accident (no add operation exists);
   that property should be given up deliberately, with a capability manifest and
   a mandatory human diff, or not at all.

3. **Anything that degrades an agent silently.** Concretely: no automatic
   rollback on behavioural signals (MECH is right that outcome evidence does not
   prove causality, so behavioural regressions alert and a human decides); no
   default-on community lists; no pre-flipped suggestions; no active overlay
   without a badge on the affected turn. One mechanical trap deserves naming:
   `overrides/ops_messages.py:sanitize_curated_messages` removes the orphan when
   one side of a tool pair is removed, so a single-item edit can cascade into
   content the user never selected. That cascade must be shown before release,
   not discovered afterwards in the audit.

4. **Republishing captured harness or provider system prompts.** LAT's ToS
   point, and it is a format constraint: packs carry patches and hashes.

5. **Selling tool-schema rewriting as a security control.** MECH's boundary in
   #9. The provider can emit arguments outside the advertised schema and the
   harness will still execute them. Enforcement belongs at the tool execution
   boundary, which TM does not own. Steering, never enforcement.

6. **A registry before the primitive.** Not harmful in itself, but shipping
   distribution before shape-keyed selectors distributes rules that rot into
   silent no-ops, which is the failure every precedent LAT cited actually died of.

---

## 6. Shortlist

Ranked against one question: **what makes first contact with the overlay land
for a first-time user on a fresh install.**

**1. The Receipt** (UX C1)
*Value*: the product thesis becomes pre-attentive, the one idea in the set a
first-time user understands in four seconds, and the segment labels seed the
provenance vocabulary the diff product will later cash in.
*Cost*: needs the first-frame baseline (unbuilt) plus one authoritative count
call; the bar itself is trivial, the capture beneath it is not.

**2. The sealed baseline capture, narrated** (UX C5, NOW.md stage 2)
*Value*: prerequisite for everything above it, and the checklist is where the
user learns TM sits in front of the wire rather than beside it.
*Cost*: per-harness bypass flag (not one `--yolo`), a throwaway home over
`prepare_captured_run`, and corrected copy, because the count call does reach
Anthropic.

**3. One tool toggle with an honest live delta** (UX C3, LAT #13)
*Value*: converts a viewer into an author in one reversible gesture, and
`tool:{name}` is the only selector in the shipped vocabulary that survives a
harness version bump.
*Cost*: small, if the live number is local character arithmetic labelled as an
estimate rather than a second network count per keystroke.

**4. Durable scoped manifest, shape-keyed selectors, compiled at run
registration** (MECH #1, LAT top-five #1 and #2)
*Value*: the difference between a setting and a session. Without it every
gesture above evaporates on API process restart, and every promise made at first
run is false by run two.
*Cost*: by far the largest item here. Product-plane store, deterministic
precedence, revision fields on `OverrideAudit` and `ExchangeArtifacts`, and
atomic snapshot replacement over the shared proxy control channel.

**5. Promotion from an edit to a rule** (LAT #11, bounded by MECH's
"not a second policy store")
*Value*: the only authoring path a first-time user will actually take, and it
makes the manifest in item 4 self-writing instead of a blank YAML file.
*Cost*: one action plus a scope picker, small once item 4 exists, meaningless
before it.

**6. The master switch and the per-turn badge** (UX C10, MECH kill switch,
LAT #60)
*Value*: the escape hatch is why anyone risks the first edit, and the badge is
what keeps "nothing silent" true; the only item all three families named.
*Cost*: the smallest in the set. `OverrideStore.set_enabled` already models the
switch; the badge rides the shipped `request_diff.request_unchanged` seam.

**7. The drift briefing with a per-overlay binding verdict** (UX C8, MECH
preconditions, LAT #15)
*Value*: first run promises that every future request carries this shape; this
is the only thing that keeps the promise true after the harness updates.
*Cost*: needs item 4's preconditions plus a stored baseline diff. It is the
second session's feature, which is precisely why the first session's copy must
not over-promise.

**Cut, with reasons.** The guide rail (UX C6) is correct, cheap and re-entrant,
but it is chrome around the seven above rather than the thing that lands; ship
it, do not rank it. Plan currency (UX C9) cannot be backed by the current audit
in tokens. The cache-aware planner (MECH #7) is necessary before any quantitative
savings claim and is the wrong altitude for first contact. The budget governor
(MECH #2) is the better policy and the worse first act. Everything in LAT's
marketplace section is the endgame of the category and a hazard as an opening
move; take its format constraints, defer its network.
