---
title: Matt Pocock skills import review
type: research
tags: [agent-runtimes, skills, mattpocock, review]
summary: Review of 37 upstream skills and verification of their catalog import and dedicated runtime.
status: active
created: 2026-09-11
updated: 2026-09-11
project: agent-runtimes
confidence: high
source: https://github.com/mattpocock/skills/tree/3cca18b368ae95cdbdebbff572ccafa662551015
---

# Matt Pocock skills review

The published engineering and productivity set is useful as an optional runtime.
Its strongest material makes the agent obtain evidence, state a design clearly,
and test observable behavior. Several workflows impose substantial interaction
and repository conventions, so adopting the collection as fleet defaults would
need a separate decision.

Reviewed source: commit `3cca18b368ae95cdbdebbff572ccafa662551015`, plugin version
`1.2.3`, cloned to `/tmp/mattpocock-skills.vtzQgA`. The collection has 18 engineering,
7 productivity, 8 in progress, and 4 miscellaneous skills. The plugin selects the
first two groups. The import preserves that distinction.

## Assessment

- `diagnosing-bugs` is the strongest operational skill. It requires a reproducible
  failure signal, minimization, falsifiable hypotheses, and rechecking the original
  failure after a fix. Its absolute refusal to form hypotheses before a runnable
  reproduction can slow investigations where source inspection is needed to build
  that reproduction.
- `tdd` gives useful guidance against implementation coupled and tautological
  tests. It also requires user approval of test interfaces and defers refactoring
  to review. Those are explicit workflow choices to accept or override.
- `codebase-design` and `domain-modeling` provide shared terminology and concrete
  methods for reviewing interfaces and overloaded domain names. Their vocabulary
  rules are more restrictive than this repo's existing language.
- `grill-with-docs`, `to-spec`, and `to-tickets` compose a clear planning flow, but
  they introduce glossary, ADR, tracker, and labeling conventions. They can be
  useful for larger work and cumbersome for a small, well specified edit.
- `handoff` uses pointers to existing artifacts and redacts sensitive information.
  `writing-for-agents` addresses discovery and document maintenance directly.
- The in progress set is explicitly beta upstream. `retro` is marked as a stub in
  its category README. Miscellaneous exercise scaffolding depends on Matt's
  course tooling. Keeping both groups out of the default selection is appropriate.

## Reproduced findings

### Commit comparison misses uncommitted work

The [review skill](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/engineering/code-review/SKILL.md)
advertises work in progress review but prescribes `git diff <ref>...HEAD`.
In an isolated repository with one commit and a modified tracked file,
`git diff HEAD...HEAD` returned no content while `git diff` showed the edit.
An invocation against uncommitted work can therefore stop as an empty review.
Use it for committed changes under its current contract.

### Guardrail patterns miss command variants

The [Git hook](https://github.com/mattpocock/skills/blob/3cca18b368ae95cdbdebbff572ccafa662551015/skills/misc/git-guardrails-claude-code/scripts/block-dangerous-git.sh)
returned status 2 for a JSON input containing `git push origin main`.
It returned status 0 for each of these JSON inputs:

```text
git -C /tmp push origin main
git clean -df
git restore --worktree .
```

The commands were supplied as strings to the hook. None was executed.
The hook is a convenience filter with incomplete matching. It cannot establish
command authorization. It remains available only through explicit catalog
selection; importing it installs no hook.

## Integration

The owned catalog, pinned source, selection instructions, local adaptations, and
other workflow caveats are recorded in
[UPSTREAM.md](/Users/alphab/.agent-runtimes/skills/mattpocock/UPSTREAM.md).
The dedicated [runtime manifest](/Users/alphab/.agent-runtimes/runtimes/mattpocock/runtime.toml)
selects the 25 member `mattpocock/core` bundle. Existing runtime selections are
unchanged. No generator behavior changed.

Cross-skill references now use generated names. Explicit Skill tool invocations
become instructions to load the named skill. The upstream invocation policy files
and script logic are preserved. Each selectable skill carries the MIT license.

## Verification

- All 37 skills appear in `generate.py --catalog` across three explicit bundles.
- The core membership exactly matches the pinned upstream plugin manifest.
- All 100 upstream skill files are retained. Twenty six files have mechanical
  invocation adaptations; all other files are byte identical to the clone.
- All 37 `agents/openai.yaml` files and executable bits are preserved.
- All 39 links to bundled files still resolve. Links illustrating future project
  layouts are preserved as examples.
- Every generated skill reference resolves within the imported catalog. All
  references from the core set resolve within the core set.
- Each of the 25 generated skill trees matches the compiler's rendered digest.
- All three bundled shell scripts pass `bash -n`; the dependency cruiser config
  passes `node --check`.
- Full generation and audit pass. The test suite reports 129 passed. The two
  catalog inventory assertions were updated for the additional bundles and runtime.
- A disposable copy of the runtime, with `config.grok.toml` placed at `config.toml`,
  is discovered by `grok inspect --json`: all 25 selected skill names appear.

This verifies source packaging, reference integrity, and Grok discovery. It does
not prove every workflow under all three harnesses, prompt inclusion semantics,
the safety of live provisioning scripts, or improved engineering outcomes.
