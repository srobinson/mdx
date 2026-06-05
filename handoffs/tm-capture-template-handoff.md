# Handoff: TM autopilot wire, step 3

Written 2026-08-20 by the orchestrator session. Repo `/Users/alphab/Dev/LLM/DEV/helioy/transport-matters`.

Read `CLAUDE.md` (repo) and `~/.claude/CLAUDE.md` first. KISS, LESS IS MORE, path of least
resistance, DO NOT REINVENT CODE, zero duplication, no file over 700 lines, no narrating
comments, never an em dash anywhere including commit messages, conventional commits.

## State

`main` at `02e2c241`, clean. Two PRs open, neither merged, all gates verified first hand by
the orchestrator on both.

| PR | Branch | Worktree | Commits |
| --- | --- | --- | --- |
| #410 merged | (deleted) | (removed) | version range state machine, shipped as `02e2c241` |
| #411 open | `fix/pty-orphan-window` | `.claude/worktrees/pty-orphan` | `c241b540` |
| #412 open | `slice/capture-template-home` | `.claude/worktrees/capture-home` | `838dd3bb`, `000d67ff` |

Both worktrees have primed `node_modules`. Gates are `cd api && just check`,
`cd api && just test`, `pnpm --filter @tm/shell test`. Never bare pytest.

#411 lifts the supervisor half of `ca714eae` from the owner's closed #362. Two live defects:
a pre-registration orphan window in `spawn_with_detached_pty` and a drain thread joined with a
timeout before `master_fd` closes. It is independent of #412 and ready.

## THE RULING THAT DRIVES THIS HANDOFF

The owner has corrected a premise that most of #412's guarding was built on.

Verbatim: "The issue was that outside of tm some of my own testing mistakenly used
~/.agent-runtimes as agent home w/o copying which is why they got dirty. ~/.agent-runtimes
contract with tm is that the runtimes will always be clean. you do not and should not guard
against that."

So the templates did NOT get dirty from a TM launch writing through an overlay symlink. They
got dirty from the owner's own testing outside TM, pointing a harness directly at
`~/.agent-runtimes` with no copy. The contract is that runtimes are always clean, and TM must
trust it rather than police it.

This invalidates the write-through hazard as a TM concern. TM's overlay was already correct.

## Work item 1: remove the runtime guarding from #412

In `.claude/worktrees/capture-home` on `slice/capture-template-home`, commit on top of
`000d67ff`. Do not amend or rebase. Do not force push.

Remove:

- `cli/home_overlay:assert_runtime_template_has_no_write_through_entry` and its call in
  `baseline_capture:harvest_controlled_baseline`. It refuses a control template carrying a
  directory or symlink outside curated names. That is policing agent-runtimes' contract.
- `cli/home_overlay:assert_runtime_template_unchanged` and its `finally` call in
  `baseline_capture:_capture_probe`. The before-and-after digest per probe exists to catch a
  TM launch corrupting the template, which the ruling says is not TM's to guard.
- Their re-exports in `cli/home_seed`, and every test that pins them.
- The `_*_TEMPLATE_LOCAL_WRITABLE_NAMES` expansions that were made in this slice for the same
  phantom: grok gained roughly 16 names read off the owner's real `~/.grok`, codex gained
  `.personality_migration`, `ipc`, `mcp-oauth-locks` and the `queue_1.sqlite` trio. Check
  `git diff 02e2c241 -- api/src/transport_matters/cli/home_constants.py` and revert the
  additions this slice introduced. `.sandbox_migration` was added for codex; judge it on its
  own merits rather than keeping it by inertia.

KEEP, and this is a judgment call the orchestrator made that the owner has NOT ratified, so
raise it before removing anything beyond the list above:

- `BaselineCell.runtime_template.content_digest` and `runtime_template_entry_digests` /
  `runtime_template_content_digest` as the helper that produces it. Its justification is
  comparability, not policing. `generated_from` is a sha256 over `runtime.toml` raw bytes plus
  skill frontmatter, so it digests the generator's INPUTS. A generator change that renders
  different output from unchanged input moves neither published digest, and the baseline would
  then be compared against a stale reference with the difference attributed to the harness.
  That is legitimate evolution on agent-runtimes' side, not a contract breach, so recording
  which bytes a baseline was measured against still earns its place.
- The deletion of `cli/test_runtime_home:_tree_fingerprint`, which was a duplicate of the
  digest helper. This only holds if the helper survives.

## Work item 2: correct the plan document

`docs/plans/AUTOPILOT-WIRE-PLAN.md` states that a single `codex debug prompt-input` writes
`skills/.system`, `installation_id`, `.sandbox_migration` and `tmp/` into the template. That
observation is very likely the same misattribution: it would have been made while running codex
directly against the template rather than through TM's overlay. Verify before editing, then
correct it so the next reader does not rebuild the same guards.

## Work item 3: drop the open question, do not pursue it

The orchestrator flagged that eight specialist templates carry a `skills/` directory, all
declare codex, and `skills` is in no writable list, so a codex launch symlinks it into the
overlay. Under the ruling this is not TM's concern. No `.system` was found in any template.
Do not build a guard for it. Mentioned only so nobody rediscovers it and treats it as new.

## Also outstanding

- Tell agent-runtimes (bus id `.agent-runtimes:general:1:3.1`, topic
  `grok-launcher-config-keys`) that the guard is being removed and why. They wrote a test on
  their side (`test_a_bare_control_home_materializes_no_directory`, their `b51edd4`) to keep
  our assertion satisfiable, and they should not maintain a constraint we no longer impose.
  They also asked for a ping when the harvest first runs against the capture homes so they can
  verify grok directly.
- Owed to them and still unbuilt: the grok credentials-only seed path. `GrokSeeder.seed`
  currently copies the operator's whole native `~/.grok/config.toml` into a home that lacks one,
  and unconditionally writes `[ui.notifications.title]`. Both break the config-ownership
  contract. The template path masks the first because the overlay already has a config.
- Undetermined: whether grok prompts on an untrusted cwd. `trusted_folders.toml` is account
  state TM must seed, and nothing does. A headless probe parked on a trust prompt reads as a
  hang with nothing in the transcript.
- `neutral_cwd` is satisfied by construction and not asserted.

## What comes after #412

Step 3 part three: harvest the first real baselines and wire the comparator. There are ZERO
baseline bundles on disk in any channel, which is why the `artifact_schema_version` 3 to 4 bump
in #412 is free. `request_schema:compare_request_schema` takes two schemas and is ready;
`mint_request_schema` needs only raw request bytes. The trigger shipped in #410: observed
version above the blessed ceiling, which is currently true for all three harnesses
(claude 2.1.237 vs 2.1.211, codex 0.148.0 vs 0.144.4, grok 1.0.5 vs 1.0.4).

Context entries: `01a01e98-8dbf-7d30-9248-43777e0dc224` (continuation) and
`01a01eb8-84dc-7a02-b68a-95351177dbba` (harness version lifecycle decisions). Reviews at
`~/.mdx/reviews/tm-version-range-findings.md` and `~/.mdx/reviews/tm-capture-template-findings.md`.
