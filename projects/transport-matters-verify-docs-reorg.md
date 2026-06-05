# Transport Matters docs reorganization final verification

Target: `ba2457a6de4d712735be00def802d5403a9823ae`

Verdict: issue, major.

This pass uses the final review standard. Earlier inventory completeness standards are superseded.

## Findings

### Major: replay idempotence rule was lost

The parent `docs/CAPTURE-PLANE.md` stated that replay is idempotent through deterministic event sequencing and cursor state. The deletion removes that rule, and neither `TLDR.md` nor `docs/ARCHITECTURE.md` records it.

This is a durable data integrity invariant. The code still implements it through `session_id` plus `seq` event identity and `index.record_ingest.plan_ingest_records`, but the architecture guide no longer tells future changes to preserve it. Add the rule without the deleted implementation inventory.

The related transcript snapshot ordering rule was preserved in `Capture plane invariants`. The two stream model in `TLDR.md` also preserves the reason that backfill remains transcript scoped.

### Minor: strict `PROJECT.md` residue remains in captured fixtures

Each of these captured request fixtures contains one embedded Markdown link, `[PROJECT.md](./PROJECT.md)`:

- `api/tests/fixtures/claude_messages/turn-0/request.ir.json`
- `api/tests/fixtures/claude_messages/turn-1/request.ir.json`
- `api/tests/fixtures/claude_messages/turn-2/request.ir.json`

They are historical payload data rather than live documentation. The final brief says nothing anywhere may retain `PROJECT.md` as a documentation path, so the literal residue gate fails.

### Minor: archived snapshots fail the literal all links gate

All 44 relative Markdown links in the 25 live root and `docs/` files resolve. The historical snapshots under `docs/.archive/` and `docs/plans/.archive/` retain 95 unresolved relative targets: 25 under `docs/.archive/`, 58 in the archived runtime surfacing plans, and 12 in the archived S2 plans.

These failures predate the target and preserve historical document bodies. The final brief says every relative Markdown link across root and `docs/` must resolve, so the literal result remains a failure unless archives are excluded explicitly.

## Clean checks

- Exact head is detached and clean at `ba2457a6de4d712735be00def802d5403a9823ae`.
- No tracked file contains `CAPTURE-PLANE`.
- No live document contains `PROJECT.md`.
- All 44 live relative Markdown links resolve, including links from `docs/plans/` and `docs/process/`.
- The new section contains durable boundary names and protocol identity facts. It contains no function enumeration, file inventory, module chain, path list, or closed set.
- The section does not duplicate the two stream, Tier 1 layout, or dark wire store material in `TLDR.md`.
- The only nearby overlap is `Boundary enforcement standard`. Its credential source rule and general enforcement method are complementary to the template specific and capture specific invariants.
- `storage/` has no production import from `session/`. Snapshot and exchange sinks are injected while the runtime loads.
- Exchange persistence completes before post persistence observers run. Transcript snapshot writes complete before observers, event submission, and cursor advancement.
- Session capture startup failures return an empty session runtime while the proxy capture runtime remains live.
- `test_private_import_boundary.py` exists and scans production Python modules.
- `ClaudeLaunchProfile.mints_session_id` is true and injects `--session-id`. `CodexLaunchProfile.mints_session_id` is false and resumes a preseeded native rollout whose stored session key is synthesized.
- Managed home identity is carried in the transcript source descriptor and through adapter binding.
- Template credentials are rejected during materialization. Known writable state is redirected to the runtime home, and full launch preparation tests preserve template bytes.

## Verification

Selected invariant tests passed: 8 passed in 0.63 seconds. The set covered the private import boundary, Tier 1 observer ordering, snapshot failure retry and cursor stability, Claude and Codex minted semantics, template byte preservation for both harnesses, and template credential rejection.
