# Cubicell transitions: candidate data shapes for a subject-scoped route entry

Brainstorm D (data shape). Read-only design study against `main @ ae44cbf`.
Sources read: `domain/score.ts`, `domain/morphSettings.ts`, `evaluation/sceneMorph.ts`,
`domain/pieceCameraTrack.ts`, plus `domain/cameraTrack.ts`, `domain/selectionQuery.ts`,
`evaluation/scoreAt.ts`, `evaluation/sceneTransition.ts`, `transport/activeTransitionPlan.ts`
for the seams a new shape has to land in.

## 0. Two corrections to the brief before designing against it

**Add/remove is not "no authored transition at all". It is one hardcoded manner.**
`prepareSceneMorphSchedule` does schedule added and removed cells: `settings.arrive` and
`settings.depart` produce real `MorphClassPlan`s, and `sampleSceneMorph` writes a per-cell
ramp into `Moment.presence`. The gap is downstream, in `applyMomentToLayout` (`scoreAt`):
presence is consumed as **a scale multiplier and nothing else**. Every arrival in the product
is a scale pop, as a constant in the evaluator, not as authored data. So instance one is not
"add a transition where none exists". It is "promote one hardcoded manner to an authorable
channel". That is a much narrower and much better-posed problem, and any candidate that
solves it by inventing a parallel presence mechanism is duplicating `Moment.presence`.

**Instances two and three are already solved once, on the camera.**
`CameraOrbitArc = { normal, sweepRadians }` is a signed, unbounded sweep authored on the
route (`PoseSegment.arc`), and `reverseCameraOrbitSweep` and `addCameraOrbitFullTurn`
already exist to express "the other way round" and "one more full turn". `resolveCameraOrbitArc`
supplies the invariant that makes it safe: **authored route data is a preference, endpoints
are the authority**. If `isCameraOrbitArcEndpointCompatible` rejects the authored arc, the
sampler falls back to `deriveShortestCameraOrbitArc` rather than rendering a wrong path.

That trio (signed unbounded datum, congruence check, derive-on-reject) is the reusable
asset here. The cell side has no equivalent: `interpolateCell` lerps `placement.rotation` as
a euler triple, so a full turn is a no-op and a 270° anticlockwise turn renders as 90°
clockwise. Candidates below are graded on whether they can host that trio without inventing
a second one.

## 1. The seam any candidate must land in

`sceneMorph` is deliberately split, and `createActiveTransitionPlanCache` exploits the split:

| Phase | Depends on | Cached by |
|---|---|---|
| `prepareSceneMorphTopology` | the two scenes only | endpoint revision pair |
| `prepareSceneMorphSchedule` | topology + `MorphSettings` | re-run on every settings edit |

Anything whose value depends on scene content (a predicate, a resolved selection) wants to
be in phase one; anything the inspector edits live wants to be in phase two. A subject-scoped
route entry is *both*: authored (phase two) but resolved against cells (phase one). Where
that resolution lands is the main hidden cost in every candidate, and the reason
`routesByCubeId` below always appears on `SceneMorphPlan` rather than on `SceneMorphTopology`.

Validation lands in `state/scoreValidation.ts`: `isTransition` uses
`hasOnlyKeys(value, ["mode", "settings"])`, so every candidate costs at least one edit there
plus a recursive guard. `authoredInverse` passes `settings` through by reference for undo;
`MotionInspector` reads `transition.settings[selectedClass]`, so a shape that is not keyed by
`MorphClassId` costs a new editor surface, not a new control.

Repo conventions to honour: object type members are alphabetically sorted (see `MorphSettings`,
`ClassMotion`), discriminants are inline `kind` fields, and optional fields are omitted rather
than set to `undefined` (`setOptionalAssemblyTrackField`).

## 2. Candidate A — literal id entries

```ts
export type MorphRouteEntry = {
  cubeIds: readonly string[];
  path: MorphPath;
};

export type MorphSettings = {
  arrive: ClassMotion;
  cutAt: number;
  depart: ClassMotion;
  durationMs: number;
  glide: ClassMotion;
  routes: readonly MorphRouteEntry[];
};
```

**Add/remove**: `{ cubeIds: ["c17"], path: { kind: "enter-offset", by: [0, 4, 0] } }`.
**Turn sweep**: needs a `MorphPath` variant `{ kind: "turn", sweeps: Vec3 }`; the entry shape
itself is untouched. Passes the no-rewrite test.
**Spinor**: the same `turn` variant with `sweeps` at ±2π beyond the shortest euler delta.

**Subject addressing**: literal ids only. A 1000-cell grid where the author wants "every cell
on the top face falls in" serialises 100 ids. Worse, ids are unstable across structural edits
in a way `repairScore` already had to solve once for `AssemblyTrack.order`; every entry needs
the same repair pass or it silently accumulates dead ids.

**Cost**: serialised size O(subjects), not O(entries). One new guard. `sceneMorph` gains a
`Map<string, MorphPath>` built in `prepareSceneMorphSchedule` and read in `interpolateCell`
and the added/removed loops. `scoreAt` unchanged if enter/exit stay expressed as cell
interpolation rather than as new `Moment` fields.

**Failure mode in two years**: the file is 80% id lists. Every structural refactor of the
grid orphans routes, and the repair rule ("drop entries whose ids all vanished") quietly
deletes authored intent. Authors stop using it because it does not survive editing.

## 3. Candidate B — selection-expression subject, channel-bag payload (preferred, see §7)

```ts
export type MorphChannelId = "ink" | "placement" | "presence" | "rotation" | "scale";

export type MorphRoute =
  | { kind: "cut"; at: number }
  | { kind: "lerp" }
  | { from: Partial<CubePlacement>; kind: "spring-from" }
  | { kind: "turn"; sweeps: Vec3 };

export type MorphRouteEntry = {
  channels: Partial<Record<MorphChannelId, MorphRoute>>;
  motion?: Partial<ClassMotion>;
  subject: SelectionExpression;
};
```

`SelectionExpression = SelectionQuery[]` already exists in `domain/selectionQuery.ts`: a
serialisable OR of predicate queries with scopes, already validated by
`validateSelectionExpression` and already resolvable by `resolveSelectionExpression`. It is
the product's own answer to "name a set of cells without listing them", built for
select-similar. Reusing it is the difference between adding a language and adding a field.

**Add/remove**: `{ subject: <top face cells>, channels: { presence: { kind: "spring-from",
from: { offset: [0, 4, 0] } } } }`. Class membership still comes from
`prepareSceneMorphTopology`, so the entry does not say *whether* a cell is arriving; it says
what arriving looks like for that subject. The default when no entry matches is exactly
today's behaviour (`presence` scalar into `applyMomentToLayout`), so the shape is
behaviour-preserving on landing.

**Turn sweep**: `{ channels: { rotation: { kind: "turn", sweeps: [0, -Math.PI / 2, 0] } } }`.
No new entry shape, one new `MorphRoute` variant. `interpolateCell`'s rotation branch consults
the resolved route; absent one, `lerpVec3` continues, and `{ kind: "turn", sweeps: after - before }`
reproduces `lerpVec3` exactly. That equality is the migration-free proof: the new path
subsumes the old default rather than replacing it.

**Spinor**: same datum, `sweeps` = shortest ± 2π. Directly analogous to
`addCameraOrbitFullTurn`; the unification is to lift both to a shared
`resolveSweep(before, after, authored)` that checks congruence mod 2π and falls back to the
derived shortest, mirroring `resolveCameraOrbitArc`. Camera and cell then share the invariant
and the helper, not the type. Sharing the *type* is the wrong unification: camera routes hang
off `CameraKeyframe.outgoing` (keyframes with `atMs`), transitions are positional entries in
`StateTransitionTrack.transitions`. Forcing one type on both moves one of those structures for
no gain.

**Subject addressing**: expressions. Size is O(entries), independent of grid size. Predicate
subjects survive structural edits by construction ("the top face" is still the top face after
a resize), which is the exact failure mode candidate A dies of. Overlap between entries is
possible, so the shape needs a stated resolution rule: **last entry wins per channel**, which
is total, order-explicit, and diffable.

**Cost**: resolution is O(cells × queries) per schedule prepare, landing in
`prepareSceneMorphSchedule` and materialising `routesByCubeId: ReadonlyMap<string, ResolvedEntry>`
on `SceneMorphPlan`. That is on the settings-keyed path, so live inspector scrubbing re-resolves;
for a 1000-cell grid and a handful of entries this is well inside the existing per-prepare cost,
but it should be measured, not assumed. `sampleSceneMorph` changes in three places: added cells
stop returning `cell` unchanged, `interpolateCell` gains a rotation branch, and the removed loop
consults exit routes. `scoreAt` is unchanged: presence stays a scalar and enter/exit manner is
expressed as cell interpolation, which keeps `getMomentCells`' presence-zero-is-absence invariant
intact. Validation: extend `isTransition`'s key list, add `isMorphRouteEntry`, delegate the
subject to the existing expression validator. Wire: one new optional key on `MorphSettings`.

**Failure mode in two years**: channel proliferation with unclear composition. Someone adds a
`bend` channel that is really placement plus rotation, and the last-wins rule now silently drops
half of an author's intent. Also: expression subjects are opaque in the inspector. A cell doing
something unexpected requires resolving four expressions in your head to find out which entry
won, and the product has no debugger for that.

## 4. Candidate C — gestures (verbs, not channels)

```ts
export type MorphGesture =
  | { by: Vec3; kind: "enter-from" }
  | { kind: "fade" }
  | { kind: "turn"; sweeps: Vec3 }
  | { kind: "shatter"; seed: number };

export type MorphRouteEntry = {
  gestures: readonly MorphGesture[];
  subject: SelectionExpression;
};
```

**Add/remove**: `{ gestures: [{ kind: "enter-from", by: [0, 4, 0] }] }`.
**Turn sweep** and **spinor**: additive new `kind`s, same as B.

**Subject addressing**: identical to B.

The difference from B is composition. Channels give exactly one writer per (subject, channel),
so conflict resolution is a one-line rule. Gestures are a bag of verbs with no declared output
domain: `enter-from` and `turn` both write `placement`, and nothing in the type says what
happens when both are present. In practice this gets resolved by application order plus
accumulated special cases in `sampleSceneMorph`, which is precisely where the current
`sharedEdgeTweens` complexity already lives and does not want a neighbour.

**Cost**: same as B on wire and validation, worse in `sceneMorph` because every added verb
needs a documented interaction with every existing verb: O(n²) prose, not O(n).

**Failure mode in two years**: the gesture list is a small uncontrolled effects language.
`shatter` ships with a seed, then wants a per-cell delay, then wants its own easing, and the
entry grows a parallel `ClassMotion` that does not compose with `settings.glide`.

## 5. Candidate D — cascade: the three classes become rule zero

```ts
export type MorphRule = {
  channels: Partial<Record<MorphChannelId, MorphRoute>>;
  motion: ClassMotion;
  subject: MorphSubject;
};

export type MorphSubject =
  | { classId: MorphClassId; kind: "class" }
  | { expression: SelectionExpression; kind: "expression" };

export type MorphSettings = {
  cutAt: number;
  durationMs: number;
  rules: readonly MorphRule[];
};
```

The three fixed buckets `arrive | depart | glide` stop being struct fields and become the
first three rules with `kind: "class"` subjects; author-added rules append and override.
One concept instead of two, and `MotionInspector` becomes a list editor whose first three
rows happen to be the built-ins.

**Add/remove, turn, spinor**: identical expressive power to B, since a class rule is just a
subject variant.

**Cost**: highest of the four. It is a wire rewrite of `MorphSettings`, and
`patchMorphSettings` (which today reference-compares three named fields to preserve identity
for the cache in `createActiveTransitionPlanCache`) has to be rebuilt over an ordered list
while retaining the same identity-stability guarantee. `MotionInspector`'s
`transition.settings[selectedClass]` indexing disappears entirely. The project's no-migration
posture makes the wire cost genuinely near-zero, but the churn cost is real and lands in
tested code that currently works.

**Failure mode in two years**: it is CSS. Cascade order becomes load-bearing semantics, and
the built-in class rules can be reordered or deleted, so the "every cell has a defined
behaviour" totality that the current three exhaustive disjoint buckets guarantee by
construction now has to be enforced by validation. Authors lose the one property that makes
the present shape legible.

## 6. Comparison

| | A ids | B channels | C gestures | D cascade |
|---|---|---|---|---|
| Instance two without rewrite | yes | yes | yes | yes |
| Survives structural edit | no | yes | yes | yes |
| Serialised size | O(cells) | O(entries) | O(entries) | O(entries) |
| Conflict rule | positional | one per channel | undefined | cascade order |
| Existing code reused | none | `SelectionExpression`, `resolveCameraOrbitArc` pattern | `SelectionExpression` | both, plus rewrite |
| Totality preserved | yes | yes | yes | validation-enforced |
| Blast radius | small | medium | medium | large |

## 7. Preferred: B, with D's unification deferred

Candidate B: `SelectionExpression` subject, channel-bag payload, last-entry-wins per channel,
added as one optional `routes` key on `MorphSettings`. It reuses the two things the codebase
already got right (the selection language, and the camera's resolve-or-derive route invariant),
it is behaviour-preserving on landing because the empty route list reproduces today's frame
exactly, and its second instance (turn sweep) is a new `MorphRoute` variant rather than a new
field. D is the better end state and should stay on the table, but it should be reached by
*discovering* that the three class buckets are just three rules, after author-added routes have
shipped and proven they compose.

## 8. The case against B

**1. It may be solving a problem nobody has.** The brief asserts add/remove is the
highest-frequency instance, and it is almost certainly right about *frequency of occurrence*.
But frequency of occurrence is not frequency of **differentiation**. If, in real projects, all
added cells in a transition should behave the same way, then the entire subject-scoping axis is
speculative generality and the correct change is three fields on `MorphSettings.arrive` /
`.depart` (`enterFrom`, `exitTo`, `presenceCurve`) plus a `turn` on `glide`. That is one wire
key, no expression resolution, no cascade, no new editor surface, and it makes instances one
through three all authorable. B would then be a language built to serve a case that arises once
a year, and the product would carry the resolution cost and the "which entry won?" opacity
forever.

**2. Expression subjects put scene-dependent resolution on the settings-keyed path.**
`createActiveTransitionPlanCache` is built around the fact that scene-dependent work
(topology) is cached separately from author-dependent work (schedule). B breaks that clean
split: subjects are authored but resolve against cells. Every inspector scrub re-resolves every
expression against every cell. The honest reading is that B is smuggling phase-one work into
phase two, and the architecture will push back.

**3. The claimed camera unification is thinner than it sounds.** What actually transfers is a
*rule* (authored route is a preference, endpoints are authority, derive on reject) and possibly
one helper. The types stay separate because the structures differ (keyframes with `atMs` vs
positional pair entries). If the unification argument is doing persuasive work in favour of B,
it is doing more work than it can support.

**What evidence settles it.** Two measurements, both cheap and both about authored data rather
than opinion:

- Across real saved projects, for each transition with a non-empty add/remove diff, how many
  *distinct* manners would the author want among the added cells? If the modal answer is one,
  ship the fields, not the language. If it is two or more (typical case: "the new layer drops in,
  everything else fades"), subject scoping is load-bearing and B is right.
- Instrument `prepareSceneMorphSchedule` wall time on the largest real grid with a synthetic
  four-entry route list and predicate subjects, scrubbing the inspector. If resolution is not
  visible against the existing prepare cost, objection two is dead. If it is, subjects must be
  resolved in the topology phase and cached against the revision pair, which changes the shape:
  `routes` moves off `MorphSettings` and becomes a third argument alongside it.

Neither measurement needs the feature built. Both should precede a decision.
