# Cubicell selection authoring UX: proposal

v0.5, 2026-07-10. Fable (8:4.1) holds the pen. Warroom: Opus 8:4.2 (UX
architecture), Codex 8:4.3 (prior-art rigor), Grok 8:4.4 (pragmatics).
Folded: Grok's stack inventory, prior-art delta, and line-by-line
review, Opus's architecture spine, supplement delta, and live-code
verification of the `against` contract, the deep-research prior-art
supplement
(~/.mdx/research/selection-query-authoring-ux-prior-art-2026.md), and
Codex's five delta rounds. **Sign-off state: all three lanes signed
off** (Codex clean, Grok verified its conditions folded, Opus
unconditional with its two amendments folded). Deliverable is this
document. No code.

Ground truth: [cubicell-select-similar-DIGEST.md](cubicell-select-similar-DIGEST.md)
(naming), [cubicell-select-similar-lang.md](cubicell-select-similar-lang.md)
(canonical v0.3), `MODEL.v2.md` (thesis).

## The problem

The engine resolves attribute predicates (negate, tolerance), relation
predicates (`face-exposed`, `cube-exposed`, `edge-junction` with five
mask classes), semantic projections (`face-perimeter`, `axis-parallel`),
the any/all exemplar quantifier, and four combine modes. The human
surface after phase 1 is one panel button ("Similar", hard-coded
replace, not on the keymap) and a shift-click toggle. The driving use
case that reopened the spec, "select all outer top edges", is
unreachable by a human. An LLM can already speak it; the person holding
the pointer cannot. This proposal designs the smallest surface that
closes that gap.

## The authoring model

One sentence: **pick an exemplar on canvas, speak a verb, read back
chips.**

- **Pick.** Direct manipulation stays the root of every query. The
  thing you tapped is the exemplar; its subject (cube, face, edge) and
  its state seed the compile. The existing pick mode is the
  element-type pre-filter (Fusion's selection-priority pattern), and it
  already ships: Tab cycles it, the Inspector shows it, and
  `applySelectionResult` syncs it from every selection write (verified,
  `cubicellStore.ts:297`). There is no query without a canvas pick
  first.
- **Verb.** Every capability the human reaches is a named intent that
  compiles a complete `SelectionExpression` from the exemplars and
  dispatches `select-query`. "Similar" is already such a verb. The new
  power (relations, projections, negate) arrives as more verbs, not as
  a form. Verbs act immediately with smart defaults; they never ask
  first.
- **Chips.** After any query resolves, a transient strip renders the
  compiled expression as chips plus a result count. Refinement is
  post-hoc: edit a chip, the draft re-resolves live. The chips are the
  human-readable rendering of the exact payload an LLM speaks. One
  payload, all actors; the strip is a view of it, never a second
  semantics.

Combine is orthogonal: plain invocation replaces, Shift adds, Alt
subtracts, Shift+Alt intersects, uniformly across every verb (key,
button modifier-click, palette). Combine lives on the command, never in
the query, and therefore never inside the chip row: the strip shows it
as a visually separate **Apply control** (segmented, default replace,
intersect present but recessed). A cross-subject combine renders
disabled when the draft subject differs from the captured `against`
base subject (not the current selection, which the query itself just
rewrote; after Outer perimeter replaces a face pick with edges, the
base is still the face world the combine would run against);
structural prevention of the canonical's truthful reject, not
click-then-error.

### The mapping law (Opus, folded)

The surface is an adapter that assembles a `select-query` payload
identical to the one an LLM sends. It never writes selection; the
descriptor's atomic write is the only author. Completeness criterion:
the surface is complete iff every model element is reachable, scope x
projection x {attribute predicate, relation predicate} x combine. Every
chip renders exactly one model element; no chip without a model
referent, no reachable element without a chip path. The coverage grid
below is the proof obligation, not a pile of stolen features.

### Feel principles

1. **One-tap first.** Every rung of the ladder is reachable from the
   canvas in one or two taps. Options never precede action.
2. **Result first, form second.** The resolved result is the prompt for
   refinement (Blender operator-redo, the supplement's crown jewel),
   never a dialog before it. Invert AutoCAD entirely: no blank form
   before a result exists.
3. **Readback teaches the language.** Every query select shows what the
   compile saw. The user learns the vocabulary by using one-tap verbs,
   not by reading docs. Discoverability of the deep language is a
   byproduct of using the shallow surface.
4. **Transient but not fragile.** The draft dies on the events that
   invalidate it (below), survives everything else (orbiting or
   scrubbing to inspect a result must never erase refinement), and is
   re-summonable ("Last query") rather than a click-to-dismiss ghost.
   This is the fix for Blender's documented redo-panel failure.
5. **No privilege.** Nothing the strip or a verb does is expressible
   only by UI. Every state it reaches, including a stable refinement
   session, is a serializable command any actor can dispatch verbatim
   (the `against` contract below). Raw expression text stays off the
   1.5 surface; literal predicates and any text surface sit behind the
   canonical's phase 2 gate, which stays intact.

## The leverage table

The mandate is theft, not invention. Ranked by the supplement's
leverage ordering, with Codex's prior-art corrections applied.

| Steal | From | What we take | What we fix or leave behind |
| --- | --- | --- | --- |
| Result-first refine panel | Blender operator redo ("Adjust Last Operation", F9) | The lifecycle, not the look: run with defaults, float live compiled parameters over the canvas, re-run from the pre-operation state on every edit, die on the next operation. This is the chip strip's spine and it answers "when does the draft die" | Fix the documented failure (T57727): the panel hides and evaporates on a stray click. Ours auto-shows, survives view and transport actions, and re-summons. Threshold slider stays phase 2 |
| Exemplar, then generalize | Blender Select Similar (Shift+G), AutoCAD SELECTSIMILAR | One-tap entry, zero syntax; multi-exemplar union; comparator-owned tolerance | Their one-shot ceiling: one trait per invocation, no composition (the add-on ecosystem is the complaint made flesh). Our exemplar tap feeds the chip surface instead of being terminal. An initial-axis trait menu is demand-gated: it ships only if the smart default proves wrong often (Grok) |
| Three-zone chips | Linear filter pills, Notion filters | Chip = one predicate with independently editable zones; dismissible, "+" to add, count readout, live results. Zone anatomy is family-aware (below), which is where we exceed Linear | Linear locks the trait after creation (keep trait-swap cheap by remove-and-add); Notion's nested groups stay out of 1.5. Our OR renders as term groups, not nesting |
| Named topological verbs | Blender Select Sharp, Select Boundary Loop; Rhino Named Selections | Relations and projections as flat named one-tap verbs; most usage is one verb, the grammar is the floor beneath. The highest human leverage for cubicell now (Grok) | Blender's deep nested Select menu (the discoverability tax). Our verbs ride the selection context, flat and few; no palette until the verb list hurts |
| Subject-flip signal | Blender Select Boundary Loop auto-switching to edge mode | When a projection changes the result's element type (face pick, edge result), flip the pick mode. Free in cubicell: `applySelectionResult` already syncs pick mode from every selection write, so every actor gets it; no UI-only behavior (verified by Codex and Grok) | Nothing; already idiomatic |
| Element-type pre-filter | Fusion 360 selection priority | Constraining what the canvas picks kills the top source of mis-selection. Already ships as pick mode. Bidirectionally bound to the draft: it reflects the draft's subject and constrains which predicates the "+" offers (Opus) | Fusion's one-at-a-time modality quirks; no new chrome rebuilt |
| The narrowing loop | AutoCAD QSELECT "apply to current selection" | Refinement as repeated combine. Steal QSELECT's decomposition (scope, type, property, operator, value, include-exclude); it is the correct predicate anatomy | None of its surface: six choices before Apply, modal, blind, one property per pass (community-documented). The anti-pattern this proposal inverts |
| Scope plus predicates plus combine in one node | Houdini Group Create | Validates the query shape (scope, predicates, replace/union/intersect/subtract) for the programmatic payload | Its tab semantics vary between keep, remove, and unconditional include: a warning to keep combine and predicate operators explicit. Expression syntax is LLM-only territory |
| Saved filters and sets | AutoCAD FILTER, Fusion and SolidWorks selection sets, Rhino Named Selections, Navisworks search sets | Validation of the phase 2 nouns: member snapshots vs persisted criteria is exactly the NamedSelection vs SavedExpression split, already the rigorous version | Deferred wholesale, per the canonical |
| Flat "select same" menu | Illustrator, Figma | The discoverability anchor: a small named list where the user already is | The single-axis, no-tolerance, no-compose ceiling (the floor we left) |
| Query as atom, ids derived | tldraw signals, Houdini named groups | The data model for the refine session only: while a draft is active, the draft is the authoring source and the committed selection is its latest applied result. Recompute on user edits only | Once dismissed, only the committed selection remains; ids are not forever derived. Scene-reactive re-derivation is LiveExpression, a phase 2 hard boundary with the canonical's cost story (Opus). The narrow phrasing is deliberate (Codex): no accidental phase 2 promises |

### The kill list (anti-leverage)

- **The modal blind builder.** No dialog, no property-grid form, no
  inspector-side predicate builder, no pre-result form of any kind.
- **Raw text as a surface.** Excluded from 1.5; literal predicates and
  any text DSL are canonical phase 2 deferrals (not bans), and the
  phase 2 gate stays intact.
- **The one-shot single-axis exemplar.** Similar always feeds the
  draft; it never dead-ends.
- **The menu of everything.** The verb list is curated, not an
  enumeration of every engine aspect.
- **Chips as a required path.** The driving case resolves without ever
  touching a chip. Chips are never the primary entry path; the
  subject-filtered "+" extends an existing result, it does not open a
  blank builder.
- **A novel component language.** The strip and verbs ride existing
  primitives (Button xs outline, Segmented, action rows, floating
  panel positions). No new palette scaffolding before three-plus verbs
  prove demand.

## The disclosure ladder

Five rungs. Each is strictly optional; a user who never leaves rung 1
loses nothing they have today. Every rung compiles to the same payload.
**The ship bar for "a human can select the outer top edges" is rung 1;
everything past it is refinement, not the gate.**

**Rung 0, Tap (ships today).** Click, shift-click toggle, drill to face
and edge, pick-mode cycle on Tab (visible in the Inspector, synced by
every selection write), the face-to-perimeter-edges gesture (local
cube). Untouched.

**Rung 1, Verb.** Named one-tap compiles, seeded from the exemplars,
with combine modifiers.

- "Similar" as today, plus a keymap binding and the Shift/Alt/Shift+Alt
  combine modifiers (spec'd, engine-ready, unwired). From the first
  slice, every query select also retains its expression as the draft
  (hours of work, no UI): this gives re-summon and LLM round-trip
  inspection before any strip exists.
- Six new verbs, two per subject, each a canned expression over phase 1
  engine capability only:

| Exemplar subject | Verb (user word) | Compiles to | Workflow it serves |
| --- | --- | --- | --- |
| Face | **Exposed faces** | `face` subject, scope all, `part: all`, relation `face-exposed` | Work the structurally exposed faces (occupancy is structural; hidden spacers count as occupied) |
| Face | **Outer perimeter** | `edge` subject, scope all, `part: face-perimeter(faceId)`, relation `edge-junction: [convex]` | The driving case: all outer top edges. Pick mode flips to edge on resolve |
| Cube | **Shell** | `cube` subject, scope all, relation `cube-exposed` | Grab the outside of a solid |
| Cube | **Interior** | `cube` subject, scope all, relation `cube-exposed` negated | Edit the interior. Negate reaches the human with zero negate UI |
| Edge | **Along axis** | `edge` subject, scope all, `part: axis-parallel(axis of exemplar)` | All verticals, all rails |
| Edge | **Outer edges** | `edge` subject, scope all, `part: all`, relation `edge-junction: [convex]` | The outer wireframe |

  Face and edge queries always carry a projection (`part` is required
  by the type); cube queries carry none. One conditional seventh verb:
  **Similar to all**, shown only when multiple exemplars exist, calling
  the already-defined all-quantifier compiler directly. It closes the
  any/all reachability gap at rung 1 with no draft provenance needed;
  plain Similar stays any-of.

  Verb naming is colloquial on buttons, canonical on chips: the button
  says "Outer perimeter"; the chips it produces read
  `[projection: face-perimeter(top)]` `[relation: edge-junction(convex)]`,
  compact typography allowed, digest words mandatory. The verb is the
  friendly alias; the chip is the language.

  Home: the existing `SelectionSection` action row, contextual by the
  active selection's subject (two buttons appear beside Similar). The
  same verbs are ordinary command registrations, so palette entries and
  keymap rows come free later.

**Rung 2, Chip.** The transient strip, after any `select-query`
resolve. The operator-redo lifecycle wearing Linear's clothes. This
rung makes the language generally human-authorable, not just
toggleable.

- **Family-aware chip anatomy** (Codex blocker; schema honesty is the
  design):

| Chip | Zones | Notes |
| --- | --- | --- |
| Attribute predicate | trait, operator (comparator and negate; ≈ only where the aspect descriptor declares scalar capability), value | Values are not Linear-simple: `size` is three floats, `face-state` and `edge-state` are composites, `cube-state` is a full snapshot. The chip shows the aspect name plus a compact summary (for example `face-state · α0.5`). Scalar edits ride the existing Inspector scrub fields as the value editor (no new pickers); `cube-state` renders read-only summary, dismiss only. Edits touch the materialized value only; the exemplar is never re-read |
| `face-exposed`, `cube-exposed` | trait, is/is-not | No value zone; asserted, re-derives at resolve |
| `edge-junction` | trait, is/is-not, junction classes (multi-toggle pills over convex, flat-seam, non-manifold, concave, interior) | Asserted value, editable; no tolerance, no exemplar. Flat-seam selection is one edit here, which is why it earns no verb |
| Projection | kind, value (faceId or axis) | Typed value editing. Removing the only projection rewrites to `part: all`, never an ill-typed empty (face and edge queries require `part`) |
| Scope | kind, value | 1.5b ships tap-cycle over all, selected, selection-set (the values a refine actually reaches; verbs default to all). The full `CubeScope` picker (single, axis, plane, pattern need spatial pickers) is demand-gated to 1.5c; the design covers all seven, the build phases them |

  Outside the chip row, two command-level controls: the **Apply
  control** (combine, as above) and, for multi-exemplar compiles only,
  the **Match control** (match any exemplar, match every exemplar).
  Both render apart from the chips because neither is a predicate:
  combine is command state, the quantifier is compile vocabulary.
- **Provenance.** The draft carries the compile's materialized
  exemplar cache. The Match control recompiles from it; the "+" add
  affordance offers relation predicates always (asserted directly) and
  attribute traits only where the cache holds materialized values for
  them. Never re-reads a live exemplar, so the expression survives
  exemplar deletion and "+" stays consistent with that contract.
- **Expression truth.** A multi-exemplar compile can emit several
  correlated query terms. A flat chip row would lie, and Notion-style
  nested groups would imply user-authored boolean trees (Criterion is
  a reserved phase 2 word) when our OR is compile provenance, one term
  per exemplar part. The ruling: a **term switcher**. Single-term
  expressions render a flat chip row with no OR chrome. Multi-term
  expressions render a header (`Match any · 3 alternatives`) and a
  segmented switcher (short labels from the differing values); only
  the active term's chips are editable at once, any edit re-dispatches
  the whole expression. Collapses to `3 alternatives ▸` when the strip
  is tight. When the Match control flips to every-of, the expression
  becomes a single query and the switcher disappears, which is the
  control proving itself.
- **Behavior.** Any chip edit re-resolves immediately and lands
  through one atomic `select-query` dispatch carrying `against`
  (below). Recompute triggers are user edits only; the scene never
  re-derives a draft (that is LiveExpression, phase 2).
- **Lifecycle.** Born from a query select. Dies on: Esc, Document
  mutation, external Selection mutation (a manual pick), or an
  external subject or pick-mode change. Under Model A death needs no
  commit step: the draft's result already is the committed selection,
  so death just discards refinability (expression, `against`,
  provenance) and whatever is selected stays selected; Esc "keeping
  the selection" is automatic. Re-resolve stays synchronous in 1.5
  (cheap one-shot per the canonical); a debounce would reopen a real
  commit gap. Survives View and Transport actions (neither fires a
  selection or Document mutation). Re-summonable via "Last query",
  which reopens the draft with a freshly captured base.
  **The self-write discriminator (Opus, load-bearing):** the draft's
  own re-resolve writes selection and pick mode through the same
  `applySelectionResult` transaction, so a naive die-on-change
  subscription would kill the draft on its own re-resolve and on its
  own projection subject flip. The draft therefore holds its
  last-applied result; on any selection or pick-mode change, committed
  state is compared to last-applied: match means own write (stay
  live), divergence means external (die). One equality check covers
  every death trigger on both channels, with no action-source
  plumbing. Never modal, never steals focus, never blocks the canvas.
- **Placement.** Bottom-center above the dock, riding the existing
  floating panel positioning. A caption of what just happened, not a
  form waiting for input.

**Rung 3, Palette (later).** Typed fuzzy access to every verb plus
recent expressions, live result counts. Pure enumeration of the command
registry; no new semantics, no syntax. Built when the verb list hurts
(more than about six), not before.

**Rung 4, Saved (phase 2).** SavedExpression, NamedSelection,
LiveExpression, per the canonical. The strip grows a "save" affordance
then and not before.

## State model and the `against` contract

Two states, kept apart:

- **Committed selection.** `CubeSelectionSet`, the Selection aggregate,
  the only durable truth. Exists today.
- **Query draft.** Transient editor-session state, sibling to
  pick-mode: `{ expression, combine, against, provenance }`. Not a new
  aggregate, not in domain, not undoable, never in Document or history.

**The `against` contract (Codex blocker 1; Opus-verified against the
live handler).** Base capture cannot live only in UI state: the live
`select-query` handler (`selection.commands.ts:55`) always resolves
and combines against the current context, so a chip re-dispatch would
self-feed no matter what the draft remembers. The fix is actor-equal:
`select-query` grows an optional serializable
`against: { selection, selectionSet }`. The field names reuse the
codebase's own words (`CommandContext` is already
`{ scene, selection, selectionSet }`); `against` is a pinned partial
context minus scene, and the implementation is one effective-context
substitution (`command.against ?? current`) read by all four context
sites, which Opus traced and confirmed are exactly the handler's four
reads: resolve context, combine base, cross-subject validation (in
`canRun`, which receives the command and needs no ports), and the
active-retention prior. Absent means current context, which is every
existing invocation, so nothing changes for one-shot queries. The
draft captures `against` at draft-open and every re-dispatch carries
it. An LLM refining a selection sends exactly the same field; the
mapping law holds with no hidden handler behavior.

Boundary notes, each deliberate:

- **Scene is not in `against`.** Relation predicates and every
  re-resolve must read the live scene or "outer" freezes (the
  materialized-exposure nightmare). The draft dies on Document
  mutation, so scene is invariant across a draft's life, which is what
  makes re-dispatch idempotent. Nobody "helpfully" pins scene later.
- **The retention prior stays pinned.** `resolveActiveMember` measures
  retention against `against.selection`, the original pre-query
  active, not the draft's current active: the anchor is a
  deterministic function of `(against.selection, expression, combine)`
  independent of session history, which is what actor-equality means.
  If anchor-jumpiness across successive edits ever bites, the phase 2
  fix is an explicit serializable anchor field, never a drifting
  prior.
- **Staleness is bounded, not validated.** `against` carries raw ids,
  but a live draft never spans a deletion (death on Document mutation)
  and resolve is total (stale scope ids yield empty, never throw). A
  persisted cross-actor `against` is phase 2 NamedSelection id-repair
  territory. Named here so it is a decision, not an oversight.
- **"Last query" re-summon captures a fresh `against`** from the
  selection as it stands at re-summon, never the stale one from first
  open, or a re-summon after edits combines against a ghost.

Eager re-resolve straight into the committed selection (the canonical's
Model A). No separate preview aggregate, no explicit commit step, one
durable truth. During an active refine session the draft is the
authoring source and the committed selection is its latest applied
result; on dismissal only the committed selection remains.
Preview-overlay plus commit is a later escape hatch only if
live-resolve cost or destructive-combine safety forces it.

The subject flip on projections is command behavior, already shipped:
`applySelectionResult` syncs pick mode from the selection write. Every
actor gets it; no UI-only side effects.

## Coverage grid (the completeness proof)

| Model element | Rung 1 path | Rung 2 path |
| --- | --- | --- |
| Subject | Exemplar pick under the visible pick mode | Subject badge; projections flip pick mode via the command write |
| Scope | Verbs default to all; Similar defaults per compile | Scope chip: tap-cycle over the common three in 1.5b; the full `CubeScope` vocabulary via the 1.5c pickers (ruling 11) |
| Projection | Perimeter verbs (`face-perimeter`); Along axis (`axis-parallel`) | Projection chip, value editable, removable |
| Attribute predicates | Similar's compile from exemplars | Three-zone pill; "+" adds traits backed by the provenance cache |
| Relation predicates | Exposed faces, Shell, Interior, Outer perimeter, Outer edges | Family-aware chips; junction classes editable; "+" asserts new relations directly |
| Negate | Interior verb (baked in) | is/is-not zone on every chip family |
| Tolerance | None; compiles are exact (canonical: epsilon is a separately shipped opt-in) | ≈ in the operator zone opts a scalar predicate in |
| Quantifier (any/all) | Multi-exemplar Similar compiles any-of; the conditional "Similar to all" verb compiles every-of | Match control (any/every), recompiled from provenance, outside the chip row |
| Combine | Shift/Alt/Shift+Alt on every verb | Apply control, replace default, intersect recessed, cross-subject disabled on mismatch |

No gaps. Every model element is reachable within two rungs.

## The workflows, walked

The four mandated workflows, end to end, zero forms:

1. **The outer shell.** Tap any cube of the solid, tap "Shell". One
   pick, one verb. The interior pass is the same with "Interior"
   (negate baked in).
2. **The top ring.** Tap the top face of any cube, tap "Outer
   perimeter". Two interactions to the 8-edge acceptance case; pick
   mode flips to edge through the command write; the strip reads
   "8 edges" with `[projection: face-perimeter(top)]`
   `[relation: edge-junction(convex)]` proving what resolved. Want the
   roof seams too? Add flat-seam in the junction chip's value zone; the
   draft re-resolves.
3. **Everything like this but not that.** Tap exemplar, tap Similar
   (replace). Tap the counter-exemplar, Alt-tap Similar (subtract).
   Pure rung 1, the QSELECT narrowing loop with no dialog.
4. **Scrub then tolerance.** Scrub opacity, tap Similar. The compile is
   exact (the canonical's default), so the strip shows the aspect chip
   with its compact summary (`face-state · α0.5`) and the count may
   read low. One tap on the operator zone flips the scalar comparison
   to ≈ with the default epsilon and the selection breathes wider.
   Tolerance is one post-result tap, never a pre-form and never a
   silent default. No slider anywhere (Blender's threshold slider is
   the phase 2 precedent when demand shows).

## Phased rollout

Sequenced by Grok's cost inventory, cheapest first, each step
independently shippable. The driving case does not wait for draft
infrastructure (Opus's phase-line push; Grok's ship bar).

- **Phase 1 tail (1 day ship, plus half a day of tests).** Similar on
  the keymap; combine modifiers wired through button modifier-click
  and key chord; the Outer perimeter compile helper and its binding;
  the draft field retained after every query select (no UI, enables
  re-summon later). `against` is deliberately not here: one-shot verbs
  never re-dispatch, so it waits for 1.5b. The driving case becomes
  human-reachable. Acceptance: "all outer top edges" in two canvas
  interactions.
- **Phase 1.5a (about two days).** The remaining verbs: pure compile
  helpers in domain beside `compileSimilarExpression`, affordance
  registrations, contextual buttons on the `SelectionSection` action
  row. If the row crowds (two subject verbs plus Similar plus the
  conditional Similar-to-all), the conditional overflows into a small
  menu under Similar rather than becoming a fourth primary button.
- **Phase 1.5b (5 to 8 days honest; the gates hold it to the low
  end).** The `against` field on `select-query` with its canRun
  threading (0.5 to 1 day); the draft slice completed (`{expression,
  combine, against, provenance}`, invalidation via the self-write
  discriminator, survive-view/transport, "Last query" re-summon; 1 to
  1.5 days); then
  the chip strip riding it (3 to 4 days): family-aware chips,
  subject-filtered "+", the term switcher, the Apply and Match
  controls. Gated out of 1.5b to keep it honest: the full `CubeScope`
  spatial pickers (tap-cycle covers all, selected, selection-set) and
  bespoke value editors (scalar edits ride the existing Inspector
  scrub fields; cube-state is read-only summary). The only genuinely
  new UI component in the proposal.
- **Demand-gated additions.** The full scope picker (1.5c); an
  initial-axis trait menu on Similar, only if the smart default
  misfires often in practice.
- **Phase 2 (per the canonical).** Palette with live counts, saved
  nouns, threshold slider, literal predicates and any text reveal, an
  invert binding if interior demand outgrows the verb, live
  expressions.

One-tap survives every step: Similar's plain-tap behavior today is
byte-for-byte its plain-tap behavior after 1.5b (compiles stay exact;
tolerance is opt-in per chip).

## Rulings (converged)

1. **Manual click during an active draft: detach.** Unanimous (all
   four lanes) against the supplement's clause-chip recommendation:
   clause promotion needs literal id predicates and their rename
   repair (canonical phase 2), chips carry intent rather than id
   lists, and a plain click is an existing `select` command whose
   meaning must not change. The draft ends (its result already is the
   committed selection under Model A; nothing to commit), the click
   applies normally; "Last query" re-summons. Revisit with phase 2
   literals.
2. **Projection subject transition.** Command-layer pick-mode sync,
   already shipped; the subject badge and count make the flip legible.
3. **Combine billing.** Replace-default primary; add and subtract as
   the spec'd modifiers; intersect present but recessed in the Apply
   control; cross-subject options disabled on subject mismatch.
4. **Verb home.** The visible `SelectionSection` row for 1.5.
   At-cursor menus repeat Blender's hidden-menu discoverability cost
   and add a new surface. Palette search is the later layer.
5. **Press-again widening: deleted.** A novel state machine with no
   demonstrated workflow; repeat-to-widen would make repeated
   invocations change meaning.
6. **Saved and named selections: phase 2**, unchanged. The prior-art
   record (snapshots vs criteria) confirms the canonical's noun split.
7. **Exactness.** Compiles stay exact by default per the canonical;
   epsilon is a per-chip post-result opt-in; the equivalence claim
   stands.
8. **The all quantifier.** Closed twice over: at rung 1 by the
   conditional "Similar to all" verb (no provenance machinery needed),
   and at rung 2 by the Match control recompiled from the draft's
   provenance cache. The coverage grid ships without a gap.
9. **Verb list frozen at six plus the conditional.** No flat-seam
   verb: it is one edit on a junction chip, which is the chip surface
   proving its worth. Interior stays (the only rung 1 negate), Along
   axis stays (the only rung 1 `axis-parallel`), Outer edges stays
   (edge-mode users need a verb pair) despite being the weakest.
10. **OR readback is a term switcher, not nested groups.** Nesting
    implies user-authored boolean trees (phase 2 Criterion); the term
    switcher is honest to DNF-as-compile-provenance.
11. **Scope authoring is phased.** The design covers all seven
    `CubeScope` kinds; 1.5b builds tap-cycle over the three a refine
    actually reaches, and the spatial pickers (single, axis, plane,
    pattern) are demand-gated to 1.5c. Verbs default to scope all, so
    nothing at rung 1 is affected.
12. **Cross-subject disable tests the captured base.** The Apply
    control compares the draft subject to the `against` base subject,
    never the current selection, which the query itself just rewrote
    (Codex residual, folded).

## Open questions

None. The last one, the `against` contract shape, closed with Opus's
live-code verification: all four context reads in the handler traced
and confirmed, the atomic-write port confirmed single-author, and
survive-view/transport confirmed free. Verb count and OR rendering
closed as rulings 9 and 10.

## Delta ledger

- **Grok pre-delta (stack inventory), folded:** command bus and
  `select-query` descriptor ready; Similar is panel-button only,
  hard-coded replace; combine modifiers engine-done, unwired;
  `selectFaceEdges` gesture is local-cube, not the projection; no
  chip, HUD, or palette primitive exists; draft state on the editor
  session slice; cost ladder adopted; kill list seeded.
- **Opus pre-brief (architecture spine), folded:** the mapping law and
  chip-to-model-element bijection; the coverage grid as proof; the
  two-state model with base capture; eager re-resolve (Model A);
  subscription-based invalidation; the six-leak list as strip
  constraints; face-gesture compile into phase 1.
- **Prior-art supplement (deep research), folded:** six ranked
  patterns onto the ladder; operator-redo as the spine with the T57727
  fix; three-zone pill anatomy; Boundary Loop's mode flip; Fusion
  priority mapped onto pick mode; query-as-atom (narrowed);
  QSELECT-vs-Linear as the one-image brief. Overruled where it
  conflicted with the canonical: clause-chip (detach ruled), raw-text
  reveal in 1.5 (phase 2 gate).
- **Opus supplement delta, folded:** split recompute trigger (user
  edits in 1.5; scene-reactive is LiveExpression, phase 2); detach
  concurrence; pre-filter as the subject-flip signal with
  bidirectional binding; combine billing; base capture reaffirmed.
- **Codex delta round 1, folded:** pinned resolution context;
  generally authorable chips; expression truth (OR term groups);
  subject transition as command behavior; exactness fixed; digest
  vocabulary on chips; "Outer perimeter" rename; structural-exposure
  and interior wording; raw-text removed; prior-art corrections;
  open-question rulings; the DSL-gate self-correction.
- **Grok prior-art delta, folded:** draft-retention as the cheap first
  slice (hours, no UI); re-summon affordance named; trait menu
  demand-gated; pick-mode pre-filter verified already shipping
  (`applySelectionResult`); ship bar pinned at the verb rung; palette
  gated on verb-count pain; anti-pattern enforcement list; detach
  concurrence with the behavior-break argument.
- **Codex delta round 2, folded:** the `against` contract replacing
  inert UI-side base capture (handler verified at
  `selection.commands.ts:55`; snapshot includes prior active plus
  set); family-aware chip anatomy with editable junction classes and
  full `CubeScope` scope zone; the Match control closing the any/all
  gap with compile provenance and the "+" value-source rule;
  query-as-atom phrasing narrowed to the refine session; subject-flip
  verification (`cubicellStore.ts:297`); kill-list text-DSL wording
  corrected.
- **Codex delta round 3, folded:** the two ill-typed canned
  expressions fixed (`part: all` on Exposed faces and Outer edges;
  face and edge queries always carry a projection); the conditional
  "Similar to all" verb closing the quantifier gap at rung 1; the
  scope chip as a typed picker over the full seven-kind `CubeScope`
  vocabulary with tap-cycle for common values; "chips never originate"
  reworded to "never the primary entry path"; the `against` contract
  and the provenance-gated "+" (already stated in v0.2) confirmed as
  the intended resolution of its blocker; the saved-nouns-are-cheap
  phrasing already removed.
- **Grok line-by-line review, folded (its six sign-off conditions):**
  honest costs (phase 1 tail 1 to 1.5 days; 1.5b 5 to 8 days with the
  split stated); `against` kept out of the phase 1 tail; scope chip
  gated to tap-cycle in 1.5b with the spatial pickers demand-gated;
  attribute values as compact summaries riding the Inspector scrub
  fields, cube-state read-only, ≈ only on descriptor-declared scalar
  capability; projection removal rewrites to `part: all`; junction
  classes as multi-toggle pills; the OR term switcher (ruling 10);
  verb list frozen (ruling 9), flat-seam demoted to a chip edit;
  action-row overflow rule for the conditional verb; canRun threading
  and fresh-capture-on-re-summon implementer notes.
- **Codex residual and sign-off:** cross-subject disable tests the
  captured `against` base subject, not the current selection
  (ruling 12); after that correction Codex re-read the full artifact,
  found the stale-vocabulary and contradiction scan empty, and signed
  off its lane. Sign-off re-confirmed on v0.4 after a targeted
  re-review of the Grok folds.
- **Grok sign-off on v0.4:** all six conditions verified folded;
  pragmatic lane clean; one micro-nit (the coverage grid's scope cell
  matching ruling 11) folded here.
- **Opus verification round, folded (sign-off unconditional):** the
  `against` contract traced through the live handler and adopted; the
  field renamed to `{ selection, selectionSet }` (a pinned partial
  `CommandContext` minus scene, no new vocabulary); scene deliberately
  excluded (live-scene re-derivation; Document-mutation death makes
  re-dispatch idempotent); the retention prior pinned to
  `against.selection` with the anchor a deterministic function of
  `(against.selection, expression, combine)` (a drifting prior would
  break actor-equality; a phase 2 explicit anchor field is the escape
  hatch); the self-write discriminator added to the lifecycle (a naive
  die-on-change subscription would kill the draft on its own
  re-resolve and subject flip; committed-vs-last-applied equality
  discriminates); Model A death wording corrected (no commit step,
  death discards refinability only, re-resolve stays synchronous); the
  `against` staleness bound named. Verified clean with no change:
  single-author atomic write, actor-universal subject flip,
  survive-view/transport for free.
