# TM PR #450 review: publish immutable baseline revisions

Target: `fix/baseline-release-revisions` at `0dbd4ffe`, against main `db6131c3`.
Merge base is exactly `db6131c3`, one commit ahead, 4 files, 249 insertions.
Tree confirmed pristine (`git status --porcelain` empty) before and after. Read only.
No provider turns spent.

Verdict: **0 major, 3 minor. Merge.**
An unchanged store **cannot** mint a revision, at any revision depth.

Gates run independently: `cd api && just check` clean (ruff, mypy 842 files),
`just test` 4201 passed (up 3).

---

## 1. The no-op, proven live at revision depth

**Holds.** Verified by a read-only dry run of `baseline_publish.publish_release_catalog`
against the owner's real store (`~/.transport-matters-preview/baselines`) and the real
embedded manifest, with `append_inactive_release_entries` and `require_clean_worktree`
stubbed so nothing was written:

    run 1: minted claude-2.1.241-r2   appended_total=1
    run 2: release catalog unchanged=claude-2.1.241-r2 action=no-op
    run 3: release catalog unchanged=claude-2.1.241-r2 action=no-op

Run 2 compares against **r2**, not r1. Latest-revision selection follows the chain, which
is the specific property asked about. `existing_ids` names r2 in the no-op line, so the
operator can see which revision was matched.

The stability is structural, not incidental. `release_publication.derive_inactive_release_entry`
overrides exactly six fields (`release_id`, `baseline_version`, `minimum_version`,
`maximum_version`, `published_at`, `signature`) and copies everything else from the
predecessor's release plus `predecessor.routes`; targets and references are derived from
the bindings, launch models and store. So once rN has itself been derived,
`derive(rN, rN's own id and published_at) == rN`. Deriving is a fixed point after one
application, at any depth. `test_baseline_publish_revisions.test_same_version_publication_mints_only_one_successor_for_a_changed_cohort`
pins the same shape in five runs (2 no-op, 1 mint, 2 no-op, `len(appended) == 1`,
four `action=no-op` lines).

A pure no-op never touches the manifest file: the write is guarded by `if entries:`.
Confirmed in source and empirically (`appended_total=0` on runs 2 and 3).

**What actually moved, precisely.** The field-level diff r1 to r2 against his store:

    target best/default/fable/fable[1m]/haiku/opus[1m]/opusplan/sonnet/sonnet[1m]
                    : compatibility_release_id only  (the back-reference to the new id)
    target opus     : compatibility_release_id, evidence_digest
    ref    opus     : effort  None -> 'low'
    release         : release_id, release_digest, published_at, signature

Nine of ten targets differ only in the release-id back-reference, and nine of ten
references are byte-identical. The one substantive change is opus, whose reference effort
moves from null to `low` because the bootstrap bundle from #449 was captured at low
effort. That corroborates Codex's diagnosis and sharpens it: the observable cohort change
is the effort axis plus the evidence digest, on exactly one cell.

## 2. Immutability

**Holds, byte level.** r1 is never rewritten. In the changed-cohort branch the entry is
rebuilt under `next_release_id(...)` and appended; `existing_ids` receives the
predecessor's id only on the no-op path. Across all three live runs r1's payload compared
equal to its pre-run payload.

`compatibility_store.append_inactive_release_entries` carries existing releases through as
the **raw dicts from `json.loads`**, not re-serialized pydantic models, and validates a
copy rather than writing the validated model. Unrelated entries therefore keep their
values and key order. Formatting is stable too: the live manifest round-trips
byte-identically under `write_atomic_json`'s `json.dumps(value, indent=2)` plus newline
(456908 bytes in, 456908 out, identical). So an append reformats nothing.

## 3. Revision ordering and selection

**Robust.**

- "Latest" is `max(exact, key=release_revision)` over entries matching harness and
  baseline_version, keyed on the integer suffix, so it is insensitive to manifest order.
- A gap is fine: with r1 and r3 present, max picks r3 and the successor is r4.
- Non-conforming ids are rejected, not silently coerced. `_RELEASE_ID_RE` is
  `(?P<stem>.+-r)(?P<revision>[1-9]\d*)` under `fullmatch`, so `-r0`, `-r01` and any id
  not ending in `-rN` raise `CertificationMintingError`.
- Two entries claiming the same revision cannot exist: `compatibility.py` rejects a
  manifest with duplicate release ids at validation time. The deleted
  `if len(exact) > 1: raise` guard was redundant against that, and actively wrong once
  multiple revisions per version became the point. Removing it is correct.

**One id generator, confirmed.** `initial_release_id` constructs the first id,
`next_release_id` increments, and both go through the shared `_release_id_match`.
Grepping production source for surviving hardcoded `-r1` release-id construction returns
only `certification_minting.initial_release_id` itself; every other `-r1` hit is an
unrelated adapter or probe revision constant, or test support. The f-string that used to
live in `publish_release_catalog` is gone.

**The new tiebreak in `_compare_release_versions` is load-bearing, not cosmetic.** That
comparator now falls back to `release_revision` when baseline versions are equal. It is
used on the `else` branch, choosing a predecessor for a *new* baseline version. Before
this PR two entries could not share a baseline version, so a tie was impossible; now they
can. Without the tiebreak, publishing claude 2.1.242 after r2 existed at 2.1.241 could
pick r1 as predecessor and inherit its routes.

## 4. The standing question: what does this key on?

Revision **selection** keys on `(harness_id, baseline_version)` for membership and on the
integer revision suffix for latest. Both are stable, and a moving baseline_version simply
starts a fresh `-r1` chain from the highest existing predecessor.

The **no-op decision** is the interesting one. It keys on full structural equality between
a freshly derived entry and the latest revision, so its inputs are: the predecessor
(routes plus every non-overridden release field), `baseline_version`, `launch_models` from
the plan, the `bindings` chosen from the store, and `baseline_root`. Working through each
input moving a second time:

- **Launch view effort options move.** `accepted_efforts` / `default_effort` change on
  targets, a successor is minted. Legitimate and desirable.
- **A cell is recaptured.** The binding and `evidence_digest` change, a successor is
  minted. Legitimate, and exactly what #449's bootstrap triggered here.
- **`maximum_version` is widened.** Not preserved. See m1.
- **Bundle file mtimes move without content changing.** Selection flips. See m3.
- **A malformed release id enters the manifest.** `_compare_release_versions` now calls
  `release_revision` on both sides, so a non-conforming id raises for that harness even on
  the new-version path, where previously only version strings were compared. All six
  entries in the live manifest conform and duplicates are impossible, so this is not
  reachable today; noting it as the one place the change narrowed what the comparator
  tolerates.

Nothing in the delta refuses work that should progress. The two ways it can *re-do* work
are m1 and m3.

## 5. `--all` atomicity message

**Correct.** `execute_baseline_publish_plan` prints
``--all is atomic; publish one harness independently with `just baseline-publish <harness>` ``
on a non-zero publish result when `len(plan.harnesses) > 1`, so a single-harness failure
stays quiet. `test_baseline_publish_revisions.test_all_harness_failure_names_the_independent_publication_recipe`
asserts the exact string, and the recipe name matches the justfile. This is the signal the
owner lacked.

Small note, not a finding: the hint prints for any non-zero publish result with more than
one harness, including failures unrelated to atomicity. It is still true advice in those
cases, so leaving it broad is defensible.

---

## Minors

**m1. A widened `maximum_version` is silently reverted, and mints a revision to do it.**
`release_publication.derive_inactive_release_entry` forces
`minimum_version = maximum_version = baseline_version`. `CLAUDE.md` documents that
`blessed_ceiling` returns `maximum_version or baseline_version` and that a declared maximum
records versions the comparator cleared rather than versions a run observed, and two active
entries in the live manifest (`claude-2.1.211-r2`, `codex-0.144.4-r2`) already carry
`maximum_version: null` rather than an exact pin. The moment anything widens the ceiling on
a latest revision, the next publish run derives an entry differing only in that field,
mints a successor, and the successor narrows the ceiling back to the exact baseline. The
operator gets a new revision and a lost blessing with no message saying so. Not reachable
today because nothing widens the ceiling yet, but "verification extends the range" is the
documented next step in this subsystem, so the collision is near. Either carry a wider
`maximum_version` forward from the predecessor, or exclude it from the equality that
decides the no-op.

**m2. Minting a successor does not say what changed.** On a mint the operator gets
`release catalog path=… releases=claude-2.1.241-r2 status=inactive activation=…` and
nothing about why a new revision exists. This feature exists precisely because an opaque
`captured cohort differs from the immutable embedded release` left the owner stuck, and a
silent successor is the same opacity with the error removed. The derived entry and the
predecessor are both in hand at the mint site, so naming the cells whose reference or
target payload differs is a few lines: my dry run produced `ref opus: effort None -> 'low'`
and `target opus: evidence_digest` that way. Print the moved cells beside the new release
id.

**m3. Binding selection keys on filesystem mtime, and this PR changed what that costs.**
`baseline_store.read_latest_baseline_for_version` orders candidate bundles by
`(path.stat().st_mtime_ns, path.name)` descending, so which bundle backs a cell depends on
filesystem metadata rather than content. Before this PR a flip in that ordering raised
`captured cohort differs from the immutable embedded release`, which is loud and sends the
operator looking. After this PR the same flip silently appends a revision recording no real
change. A store restored from backup, a `cp -r` without `-p`, or an rsync without `-t` is
enough. Order by the bundle's recorded `generated_at` instead of mtime, so selection keys
on content. m2 is the cheap partial mitigation: if the mint said which cell moved, a
spurious revision would at least be legible.
