# Salvaged from backup/turn-rotate-selection-pre-rebase

Branch deleted 2026-08-18 after PR #182 merged as `02690dc`. Tip was `1796e43`.

`turnSelection.test.ts` is the pre-rebase domain suite for the turn operation.
It predates the rename, so it calls `turnSelection` rather than `turnCubes` and
imports `rotateAroundAxis` from the old module path.

Four of its nine cases have no equivalent in the contract suite on main:

- composes the turn with an existing orientation as a rigid body
- materializes contextual selection and reports bounded cell transform impact
- persists the authored pose through compact storage
- shared axis rotation preserves the previous camera maths bit for bit

The last one guards the lift of `rotateAroundAxis` out of `cameraTrack`, which
PR #182 completed into `shared/vec3.ts`. That equivalence was verified by probe
during the review but is not guarded by a committed test.

The branch also held `selectorPanel.test.tsx`, a jsdom and @testing-library
component suite. It is not salvaged. `tests/` on main holds only `contracts/`,
and governance.json lists `@testing-library` and `jsdom` as forbidden imports,
so component tests are excluded from this repo by policy.
