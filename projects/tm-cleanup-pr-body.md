# Stop storing what we recompute, and make #424 reach the evidence

Branch `baseline-artifact-cleanup` at `e7a0a74a`, three commits on top of `b44073cb` (#431).

## The principle

**Nothing derived is stored. Anything stored is raw evidence.**

The bundle stored two projections of each probe's request body and seven derivations of
the three bodies together. Deleting the ones that were recomputed and re-checked on every
read is hygiene. Eliminating the ones that were *not* recomputed is why this PR matters:
they had already gone stale in production, silently.

## The defect this closes

#424 changed what `classify_aba` returns and did not move `artifact_schema_version`. Every
one of the operator's 16 bundles predates it, so all 16 stayed readable while carrying a
classification the running code would not produce. Because `validate_probe_contract`
rebuilt `content_observations` from the **stored** `runtime_generated_pointers`, the
comparator went on excluding `/system/2/text`, the pointer #424 exists to un-exclude.

Measured against the live store: **41 of 45 claude pairs** report a content finding count a
re-classified store would not. The hidden value is model-dependent, which is what makes it
matter.

## What changed

1. **Deletion** (`bcd33203`). `ProbeEvidence.inventory` and `.raw_nodes` are a pure
   function of `raw_request_base64`, verified byte-identical on 16/16 bundles.
   `classify_aba` rebuilds the leaf axis from the body and takes the cell for the
   coordinates a body needs to be read. `build_request_inventory` loses `internal_request`
   with its last caller, taking `request_inventory` off the `ir` package.
2. **Recomputation** (`b366d49a`). The seven derived bundle fields are gone;
   `baseline_projection.project_baseline` derives them from one bundle at one moment and
   never persists them. `extra="forbid"` on the two stored models makes a stored
   classification unrepresentable rather than merely unread.
3. **Bump** (`e7a0a74a`). `artifact_schema_version` is 6. A v5 bundle is refused with
   `unsupported baseline bundle schema; regenerate the baseline`. No pointer carries an
   `accepted_by`, so no operator judgment is destroyed.

## Why `project_baseline` and not `cached_property`

The obvious shape was recompute-on-read via a `cached_property` on the frozen bundle. It is
wrong here for a specific reason worth stating: **a warm cache survives `model_copy`**, so a
copy made with different probes reports the previous schema. That is the same class of
silent disagreement this PR exists to close, rebuilt one PR after diagnosing it. An
explicit `project_baseline(bundle)` cannot go stale, and it names the thing the gate
projection PR will persist.

The comparator pairs each cell with its projection once, so a cohort derives per cell
rather than per direction.

## Results, measured on the operator's real store, read-only

| | before | after |
| --- | ---: | ---: |
| bundles on disk | 53.7 MB | **8.4 MB** |
| bundles compact | 43.2 MB | **8.8 MB** (79.7% smaller) |

Every surviving field is byte-identical to the value the v5 artifact carried, asserted
field by field and probe by probe across all 16 cells.

Re-classification, per harness:

| harness | pairs | finding-count changes | no longer excluded |
| --- | ---: | ---: | --- |
| claude | 45 | **41** | `/system/2/text` |
| codex | 6 | 0 | `/input/0/content/0/text`, `/input/2/content/0/text` |
| grok | 1 | 0 | none |

## Two facts to keep in view

**The derivation moved rather than vanished.** The claude cohort gate went from 2.01 s read
plus 0.37 s compare to 0.03 s read plus 2.45 s compare: 2.38 s to 2.48 s overall, on 84%
less disk, with correct classification. The **gate projection PR is what removes that
cost**, by persisting the comparator's input (measured at 748,643 B for all 16 cells, 1.73%
of the old store) in the cheap place.

**The structural partition is unaffected by re-classification.** The reshaped cohort still
folds to the **same 2 claude equivalence classes** (`best` with 9 members, `haiku` alone).
This is expected and it is worth recording: `fold_model_equivalence_classes` gates on
`compare_request_schema`, and content never gates. Re-classification moves content findings
and leaves the partition alone, which is the property the launch-triggered capture design
depends on.

## Verification

- `just check` and `just test` verbatim, after the rebase onto main: **3984 passed, 11
  skipped in 61.21 s**, all 8 JS suites green, ruff and mypy clean on 793 files.
- **v5 under v6**, against a copy of the live store: the bundle read refuses with a
  comprehensible message, `read_current_baseline_ref` still answers with the bundle id, and
  `assess_baseline_staleness` returns `unknown` rather than raising.
- **Mutation tested.** Removing `extra="forbid"` fails both new tests. Reverting #424's
  masking fails the two content tests. Recoupling the pointer literal to the bundle bump
  fails the cross-version test and #431's own.
- No writes to `~/.transport-matters`; all measurement ran read-only or against copies.
