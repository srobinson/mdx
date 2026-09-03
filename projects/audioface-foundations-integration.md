---
title: Audioface foundations integration
type: projects
tags: [audioface, foundations, integration, merge, composition, runtime, build-report]
summary: The two independently reviewed foundation units merged locally on probe/foundation-integrated at 95efc3b, parents runtime 9204eaa and composition 41699f4, one barrel conflict resolved, combined gate and web build passing, with the obligations that remain open.
status: draft
created: 2026-09-05
updated: 2026-09-05
project: audioface-next
related: [audioface-foundations-composition-build, audioface-foundations-runtime-prerequisites-build, audioface-foundation-document-spec, audioface-foundation-runtime-probes-spec]
confidence: high
---

# Foundations integration

Worktree `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/worktrees/integrated`, branch `probe/foundation-integrated`. The lead started `git merge --no-ff --no-commit` of the composition head into the runtime head; Fable completed it. Merge commit `95efc3bd51c572a8396c7a6573b67322d8803431`.

| Role | Branch | SHA |
|---|---|---|
| First parent, runtime | `probe/foundation-runtime` | `9204eaa9b5be02dffa6b6649110b505c5903b4ff` |
| Second parent, composition | `probe/foundation-composition` | `41699f487eba5437786a2a8bcaa2316a10f03c08` |
| Common baseline, main | `main` | `10ba9fc16cea55271c6d428c8fe64c8df0b9c354` |

Both reviewed heads are exact parents of the merge (`git rev-list --parents -n 1 HEAD`) and `git merge-base --is-ancestor` confirms each. No parent commit was amended, squashed or rebased. Nothing was pushed, no PR opened, main not merged.

## The conflict

Confirmed before touching anything: HEAD `9204eaa`, MERGE_HEAD `41699f4`, and `git diff --name-only --diff-filter=U` listed exactly one file, `packages/engine/src/index.ts`.

The barrel is an alphabetical list of `export *` lines. Each parent appended one line at the end of it: runtime added `./voice-budget.ts`, composition added `./kernel-preparation.ts`. Both modules are new files in their respective parents and both are intended public surface. Resolution keeps both, placed in the barrel's alphabetical order, with no alias and no duplicate declaration. Every other file merged cleanly; the composition unit touched no engine module other than the barrel and its new `kernel-preparation.ts`, so no runtime change collided with composition code.

Checks made on the resolution:

- Exported names across all engine modules were listed; no name is exported by two modules, so `export *` cannot collide.
- `kernel-preparation.ts` imports only from `@audioface/contract`; it consumes nothing the runtime unit changed.
- `envelope-validation.ts`, new in the runtime parent, was not exported by the runtime's own barrel and remains internal. No export of a deleted legacy scheduling or admission path survives in either parent, and none was reintroduced.

No integration defect beyond the barrel appeared, so no code beyond the barrel was changed and no new test was written.

## Gates, at the merged tree before commit

Run in the integrated worktree with the frozen lockfile install the lead made. Logs beside the brief in `/Users/alphab/.mdx/TMP/pstack/audioface-foundations/`.

| Command | Result | Log |
|---|---|---|
| `pnpm run check` (typecheck, test, lint, format:check, verify:structure) | exit 0 | `integration-check-95efc3b.log` |
| `pnpm --filter @audioface/app-web build` | exit 0, `dist/index.html` 1459 KiB, `dist/null-test.html` 1427 KiB | `integration-build-95efc3b.log` |

Test totals from the check run: 335 tests, 334 pass, 0 fail, 1 skipped, 0 todo. The one skip is the sample half of foundations test 3 (nested, flat and the oracle sample for sample through the shared runtime, 48,000 frames under one root seed), marked pending integration by the composition unit and expected by the brief. No test was altered and no skip was added or masked.

Diff of the merge against each parent: against runtime, 39 files, 5104 insertions, 119 deletions; against composition, 23 files, 1501 insertions, 408 deletions. No `package.json`, workspace manifest or `pnpm-lock.yaml` differs from either parent.

## State after commit

Integrated worktree clean (`git status --short` empty). Other checkouts unchanged and clean: main at `10ba9fc`, composition worktree at `41699f4`, runtime worktree at `9204eaa`. Specifications untouched.

## Next obligations

- Shared program surface: wire the runtime to instantiate a `ProgramSpec` and apply compiled modulations at a voice's start. Until then the composition surface and the runtime remain two proven halves.
- The pending sample half of test 3: nested, flat and the oracle rendering 48,000 frames sample for sample. Unskip only when the runtime above exists.
- No browser or audible proof is claimed by this merge. Sample and browser proofs remain open.
- The lead's bounded integration delta check, scoped to the barrel resolution and the combined gate, before the next substantive runtime unit.
