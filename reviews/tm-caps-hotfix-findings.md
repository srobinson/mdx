# Review: PR #403 runtime template extra fields hotfix (fix/runtime-template-extra-fields)

Reviewer pass over 34c8b6a0 on b648598c. Counts: Major 1, Minor 2, Note 5. Plus the root
cause of the 5 pre-existing gate failures, found and remedied in the hotfix worktree.

## Q1. Was `extra="forbid"` load-bearing, and is `extra="ignore"` right

**Verdict: `ignore` is the right boundary policy and the fix should ship, but the stated
justification is wrong for exactly the keys that broke, and the PR must say what it trades.**

Provenance of `forbid`: it arrived in #143 (`feat(runtime-templates): add browse reader`) as
the module-wide default on `RuntimeTemplateModel`, with no drift rationale in the commit or in
any doc. The only "reject unknown keys" statement in the repo, `docs/plans/RUNTIME-SURFACING-S1-PLAN.md`,
governs the producer's `runtime.toml` source contract, and that plan schedules the removal of
`capabilities.json` scanning altogether. The producer's own spec
(`~/.agent-runtimes/docs/specs/2026-06-17-launcher-home-spec.md`) says loaders ignore unknown keys
and "present-but-ignored is fine", and the producer has bumped `schema_version` for its one
breaking change (2 to 3, identity) and not for this additive one. So `schema_version: Literal[3]`
is the producer's declared gate and `forbid` was a default, not a decision.

But `forbid` was *incidentally* load-bearing in one way: it guaranteed TM never launched a
template whose launch contract TM does not read. The four keys that broke main are not inert
metadata. TM's own `docs/plans/AUTOPILOT-WIRE-PLAN.md`, section "The agent-runtimes contract",
says `launch_requirements` is "what the home cannot express and TM must apply at launch" and
`caller_constraints` is for TM to assert; the producer's `bin/agent_runtime_compiler/redaction.py`
module docstring says "transport-matters applies launch_requirements verbatim and asserts
caller_constraints". And the live catalog carries non-empty values:
`tm/capture` declares `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` (claude, kind env) and
`project_doc_max_bytes=0` (codex, kind config); `tm/capture-grok` declares the `neutral_cwd`
caller constraint. With `ignore`, TM now loads both and launches them without reading any of it.

That is safe today for two reasons TM does not assert anywhere: the plan records that the
generator self-applies `env` and `config` kinds into the home (`settings.json`, `config.toml`),
so both tm/capture entries are already in force via the materialized home and only `flag` and
`manual` kinds are TM's alone; and `neutral_cwd` holds by construction because TM launches
captures in its own workspace. Neither is checked by TM; both are future work the plan already
names ("What TM owes against this contract").

### Major 1. The docstrings assert "unknown keys are additive" about keys the repo's own plan says TM must honour

`RuntimeTemplateArtifactModel` docstring and
`test_read_runtime_template_capabilities_rejects_an_unsupported_schema_version`'s docstring
("Unknown keys are additive; a version bump is not") will mislead the next reader into treating
`launch_requirements` and `caller_constraints` as inert. Fix in this PR, no code change needed:
state in the `RuntimeTemplateArtifactModel` docstring that `launch_requirements`,
`caller_constraints` and `launch_requirements_digest` are dropped until TM reads them, and the
two facts that make dropping them safe today (self-applied kinds; capture cwd is TM's). Add the
same one line to the plan's "What TM owes" paragraph so the gap is on the roadmap, not only in a
docstring. Reword the test docstring to "producer keys TM does not yet read" rather than
"additive".

Not asked for here, and I am not asking for it in a hotfix: typing the three keys and
recording them in `BaselineCell` is the planned slice. Do not expand this PR into it.

## Q2. Is `RuntimeTemplateArtifactModel` on exactly the right set

Yes. Producer-generated and parsed by TM: `RuntimeTemplateCapabilities`, `RecommendedModel`,
`RecommendedModelDefault`, `RecommendedVendorModel` (all four are reached only through
`read_runtime_template_capabilities`). TM-built projections, never parsed from the producer:
`RuntimeTemplateDefaultTarget` (built in `runtime_registry:_default_target`),
`RuntimeTemplateReadiness` (built in `_catalog_summary`), `RuntimeTemplateSummary` (built by
`RuntimeTemplateListing.summary`), `AgentCatalogResult` (route output). Grep finds no
`model_validate` of any of the latter four anywhere in `api/src`, so `forbid` on them cannot
misfire on producer input. The nested `RecommendedModel` inside `RuntimeTemplateSummary` is the
already-parsed object, and `ignore` drops extras at parse time, so no producer key leaks into the
browse payload. No other TM model parses a producer artifact: TM only checks `runtime.toml`
exists (`_RUNTIME_MANIFEST_FILENAME`) and never parses it or a lock file.

## Q3. Does failure isolation silence anything that should stay fatal

No. The `try/except RuntimeTemplateRegistryError` in `_list_runtime_templates_in_root` wraps only
`read_runtime_template_capabilities` (OSError, JSON decode, validation). The catalog invariants
live in `_catalog_listings_by_id`, outside that function: `_validate_listing_authority` (fixed
name on untrusted root), duplicate agent id within a source, and duplicate fixed name across the
merged catalog all still raise `RuntimeTemplateRegistryError` up through `resolve_agent`,
`list_runtime_templates` and `reserved_runtime_template_names`. Confirmed by reading; the
existing tests for those three paths are untouched by the diff.

### Minor 2. The skip warning drops the reason

`logger.warning("skipping unreadable runtime template at %s", template_home)` discards `exc`,
whose message already carries the path and the pydantic detail. Today's incident cost a
debugging cycle because the 500 hid the cause; a warning that says "skipping" and nothing else
sets up the next one. Log `%s: %s` with the exception. One line.

## Q4. What makes this wrong under a breaking rather than additive producer change

- A `schema_version` bump (the declared breaking signal) is now per-template skip, not a raise.
  Every template in the root is dropped with one warning each, the catalog is empty,
  `reserved_runtime_template_names` returns an empty set, and `resolve_agent` reports "does not
  exist in the runtime catalog". That is the trade the PR makes on purpose and it is the right
  one for launches; the cost is that a whole-catalog break is now quiet. Minor 2 is the remedy
  that keeps it diagnosable.
- A type change on a known field (`vendors` becomes a mapping, a required field renamed) is
  caught by validation and skips that template; same signal as above.
- A semantic change with no shape change is invisible to both policies. The plan already
  flags one: `harnesses` is now authoritative and `vendors` is the intersection with targeted
  harnesses; TM still derives support from `vendors` via `runtime_template_supports_harness`,
  which is equivalent today only because of that intersection. Not this PR's problem, noted so
  nobody thinks `ignore` changed it.

### Minor 3. The replaced test left the scope of `ignore` untested

`test_producer_added_capability_keys_are_ignored` proves the relaxation; nothing proves it is
scoped. A two-case parametrized test that `RuntimeTemplateSummary` (or `AgentCatalogResult`)
still rejects an unknown key while `RuntimeTemplateCapabilities` accepts one pins the split the
PR description argues for, so a later "just move it to the base" edit fails a test instead of
widening the boundary silently.

## Notes (no change required)

- **Note A.** `RuntimeTemplateReadinessState` already declares `"invalid"` and nothing produces
  it. The vocabulary suggests the designed shape for a bad template was "list it as invalid",
  not "drop it". Unreachable for unparseable JSON (no identity to list under), so skip is the
  correct hotfix; if a later slice wants bad templates visible in the catalog, that literal is
  where it goes.
- **Note B.** `resolve_agent` on a skipped template says "does not exist", which is misleading
  when the directory exists and the file is unreadable. The warning (with Minor 2 applied) is
  the signal; not worth threading a skipped set through the listing for a hotfix.
- **Note C.** A broken platform profile in the `tm-fleet` root now silently drops its
  `fixed_name` reservation instead of failing the catalog, so a run could claim a name a broken
  profile reserved. Edge case, same trade as Q4, noted for completeness.
- **Note D.** The deleted test's fixture embedded a second hand-written `capabilities.json`;
  the replacement tests reuse `_write_test_capabilities` and mutate the payload. Cleaner than
  what it replaced.
- **Note E.** Test docstring and `RuntimeTemplateArtifactModel` docstring both use the word
  "additive"; Major 1 covers the wording.

## The 5 pre-existing gate failures: root cause found, remedied in the worktree

Not this PR's fault and not a missing built artifact. Cause: in a fresh worktree
`node_modules/.pnpm-workspace-state-v1.json` is absent, so pnpm 11 (`verify-deps-before-run`)
runs `pnpm install` in front of every `pnpm exec`; that install fails at the `prepare` lifecycle
because `lefthook install` refuses the repo's `core.hooksPath`
(`/Users/alphab/Dev/LLM/DEV/helioy/transport-matters/.git/hooks`), so the state file is never
written and the next `exec` repeats it. The install chatter ("Scope: all 14 workspace projects")
lands on stdout, and `test_gateway_support:_read_gateway_address` tries to `json.loads` it. Every
test that enters `gateway_url()` fails the same way; `test_run_proxy.py` alone is 5 of them.

I verified this by running `pnpm --filter @tm/gateway exec tsx src/testSupport/originContractGateway.ts`
in both worktrees: startup-verify prints the JSON address, caps-hotfix printed the install
banner. Disclosure: to confirm and unblock I ran `pnpm install --frozen-lockfile --offline
--ignore-scripts` in the caps-hotfix worktree (your tree, not mine; node_modules only, `git
status` stays clean). That wrote the state file, the gateway support now prints its address,
and `just test src/transport_matters/api/v1/test_run_proxy.py` passes 13/13 there
(`test_gateway_supervisor.py` 27/27). Re-run your full gate and you should see 0 failed.

Durable fix, separate PR: make `prepare` tolerate an existing hooks path (`lefthook install
--force`) or document `pnpm install --ignore-scripts` in the worktree bootstrap. Every fresh
worktree will hit this until then.
