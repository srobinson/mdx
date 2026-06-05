# Transport Matters documentation consistency check

Reviewed `main` at `33618e43275202a21c02a6a815a319e5ee57002d` after PR #309.

## Current shipped facts used for the check

- `MODEL_ENUMERATION_PROBE` uses `codex debug models --bundled` for Codex and `claude -p "/model"` plus `claude -p "/effort"` for Claude.
- `run_model_enumeration_probe` runs the credential free CLI catalog contract. `_refresh_target_snapshot` stores a complete snapshot and skips another probe when the stored snapshot has the same exact harness version, probe revision, completeness, and healthy status.
- `_refresh_target_snapshot` builds target rows from `EnumeratedModel`. It no longer seeds them from `CompatibilityReleaseEntry.targets`.
- Stable and preview pointers are active for both Claude and Codex in `compatibility_releases_v1.json`.
- `COMPATIBILITY_ROLLOUT` is `advisory`. Compatibility outcomes are recorded and surfaced, and they never block a launch in the shipped posture.
- Two real records exist: `claude-2.1.211-r2.json` and `codex-0.144.4-r2.json`. Each contains seven passed observability facets backed by an owned captured run.
- The two certification records and the manifest target edge sets still contain the older hand authored model and effort lists. Re-minting them from the enumerated catalogs remains pending.
- Credential free CLI enumeration is the accepted discovery path. The provider `/v1/models` API and executable string scraping were rejected as production enumeration paths.
- The next product focus is multi-launch: one control plane batch launch verb over the enumerated catalog.

## `docs/ARCHITECTURE.md`

### Stale spot 1: `Harness compatibility and certification`, catalog ownership

The paragraph beginning "The compatibility surface judges a live launch" says model and effort support flows from the certified release edges and that `resolver` enumerates those edges as the launch catalog. This now collapses two sources with different jobs.

Corrected text:

> Claude and Codex enumerate the installed CLI's native model and effort vocabulary through credential free commands. Startup refresh caches one complete target snapshot per harness, exact version, and enumeration probe revision. Compatibility release edges remain the product certification layer. The current manifest and certification records still carry the older hand authored edges, so `resolver` intersects live target evidence with those edges until the pending re-mint derives new certification artifacts from the enumerated catalog.

The pointer activation and advisory rollout paragraphs in this section are current and require no correction.

## `HARNESS-COMPATIBILITY.md`

### Stale spot 2: `Purpose`, source of the launch profile

The purpose says certification resolves "the release's model and effort launch profile." That wording makes the release appear to own the installed CLI vocabulary.

Corrected text:

> Certification matches the installed version to a compatibility release and proves a launch profile over owned capture evidence. The installed CLI supplies its native model and effort vocabulary through version scoped credential free enumeration. Compatibility edges supply product certification metadata. The current records still cite the older hand authored edges until re-minting is complete.

### Stale spot 3: `Stable harness identity`, release specific models and efforts

The section says "Release specific routes, models, and efforts belong to `HarnessCompatibilityRelease`." Routes and certification edges still belong there. The native version scoped vocabulary no longer does.

Corrected text:

> Release specific routes and certified target metadata belong to `HarnessCompatibilityRelease`. Native model selectors, effort options, and default efforts come from the installed harness CLI and are stored as exact version target observations. Certification artifacts retain edge references for audit and support policy.

### Stale spot 4: `Target catalog revision`, catalog definition

The section describes `target_catalog_revision` as the model and effort catalog Transport Matters can select, with effort owned by the compatibility edge. PR #309 introduced a separate native catalog authority.

Corrected text:

> `target_catalog_revision` identifies the immutable product certification edge set for a release. It carries route binding, support tier, lifecycle, adapter revision, and evidence references. The live native catalog comes from `ModelEnumerationProbeAdapter` and `LocalTargetObservation`. Resolution combines the certified edge with current native evidence. The embedded edge sets and both real certification records still use their older hand authored lists; re-minting them from the enumerated snapshots is the pending convergence step.

### Stale spot 5: `Channel state`, paused and revoked launch behavior

The section says `paused` and `revoked` block new launches. That describes the future enforcing posture as current behavior.

Corrected text:

> Channel status controls the compatibility outcome. `active` evaluates the pointed release; `paused` and `revoked` produce `compatibility_release_unavailable`. Under the shipped advisory rollout, every such outcome remains a flag and never blocks launch. A future Transport Matters build may change `COMPATIBILITY_ROLLOUT` to `enforcing`, at which point noncompatible outcomes become launch rejections. Stable and preview currently carry active pointers for both Claude and Codex.

### Stale spot 6: `Publication`, new target detection

The section assigns new target detection and catalog publication to `COMPATIBILITY-PUBLISHING.md` without separating local discovery from certified publication.

Corrected text:

> Credential free harness CLI enumeration detects the exact version native catalog locally and refreshes executor target snapshots. The publisher consumes that evidence to re-mint certification records and compatibility edge sets, then publishes signed support metadata. The provider `/v1/models` API and executable scraping are outside the production discovery path.

### Stale spot 7: `Open decisions`, initial baseline versions

"Initial baseline and minimum versions" is no longer open.

Corrected text:

> Remove the initial baseline and minimum version item. The active records are `claude-2.1.211-r2` with baseline and minimum `2.1.211`, and `codex-0.144.4-r2` with baseline and minimum `0.144.4`. Replace it with: "Re-mint the two certification records and manifest target edges from the exact version enumerated catalogs."

The `Local target observation` section is current after PR #309. Its complete CLI vocabulary, Claude global effort expansion, and common per model shape match the implementation.

## `NOW.md`

### Stale spot 8: `Current focus`, session transcript track

The document still names session transcripts and progressive subtraction as the current focus.

Corrected text:

> ## Current focus: multi-launch over the enumerated harness catalog
>
> Add one control plane batch launch verb that accepts an explicit set of tuples from the exact version enumerated Claude or Codex catalog and returns one result per requested launch. Reuse the existing single launch authority for every item. Preserve server minted dispatch identity, per item failure isolation, and advisory compatibility detail.

The remaining transcript subtraction items can move to committed follow-on work if they remain live.

### Stale spot 9: `Next up`, Runtime surfacing S2 status

The section places harness compatibility and target authority under "committed tracks, not yet started." The shipped sequence now includes stored inventory, advisory compatibility evaluation, active pointers, two real certification records, and live model enumeration.

Corrected text:

> Move Runtime surfacing S2 out of the unstarted list. Record the shipped state: active Claude and Codex compatibility pointers, advisory rollout, two seven facet real certification records, and credential free exact version catalog enumeration. Keep one pending follow-on: re-mint the certification records and manifest edge sets from the enumerated catalogs.

### Stale spot 10: `On our mind`, control plane fleet operations priority

The batch `specs[]` launch form is parked under "On our mind." It is now the next focus.

Corrected text:

> Move control plane fleet operations to `Current focus`. Define multi-launch as a batch verb over the enumerated catalog, with per item results and server minted dispatch ids. Keep close filters as a later fleet management follow-on unless they are included in the same approved slice.

## Fully consistent documents

- `PROJECT.md`: consistent. It makes no model catalog, certification artifact, pointer posture, or roadmap priority claim that conflicts with current shipped reality.
- `CLAUDE.md`: consistent. It delegates current priority to `NOW.md` and contains no stale catalog or certification ownership statement.
- `docs/CHANNELS.md`: consistent. Its stable and preview runtime isolation contract does not conflict with the active compatibility pointers or advisory rollout.

## Result

10 stale spots across 3 documents. The remaining 3 documents are fully consistent with the supplied current state.
