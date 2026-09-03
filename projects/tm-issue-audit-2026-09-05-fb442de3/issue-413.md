# 413: Revisit the overlay name sets and clean them up

URL: https://github.com/littleorgans/transport-matters/issues/413
State: open
Labels: 
Updated: 2026-08-20T18:31:13Z

The overlay carries eleven hardcoded name sets in `cli/home_constants.py`, three of which enumerate harness runtime state. They are a mirror of three harnesses' internals that Transport Matters does not own, cannot keep current, and that measurement suggests are largely inert. This issue is to revisit all of them and clean up.

## The three under most suspicion

| Set | Literal names | Effective |
| --- | --- | --- |
| `_CLAUDE_TEMPLATE_LOCAL_WRITABLE_NAMES` | 11 | 16, it unions `_CLAUDE_DAEMON_LOCAL_NAMES` |
| `_CODEX_TEMPLATE_LOCAL_WRITABLE_NAMES` | 33 | 33 |
| `_GROK_TEMPLATE_LOCAL_WRITABLE_NAMES` | 9 | 9 |

They tell `_symlink_template_content_entries` not to symlink an entry and `_materialize_local_writable_entries` to create a fresh empty one instead, so a launch cannot see or corrupt another run's session state.

## The measurement that prompted this

Checked all 58 effective names against every template in `~/.agent-runtimes/runtimes`: **zero matches**. Not one name in those sets corresponds to any entry in any of the eleven templates.

That is structural rather than luck. Both functions only act on an entry the template already carries. A template is generator-authored content that has never been launched into, so harness runtime state does not exist in it. And the protection actually relied upon is elsewhere: `_symlink_template_content_entries` only symlinks entries that *exist* in the template, so a name the harness invents at runtime is not there and lands in the overlay by construction. That mechanism needs no list, and it is why codex's `installation_id` already works.

The cost is a list that rots silently in the worst direction. An unlisted name gets symlinked, which is a write channel back into the source home.

## The complication, and why this is not a two line deletion

The sets are consulted for **every** template launch, not just captures. Specialist runtimes are not bare: eight of them ship a real `skills/` directory, and all eight declare codex.

So the sets are provably inert for control templates and **not** provably inert for specialist ones. That asymmetry is the actual question this issue exists to answer, and it must be settled before anything is deleted.

Related and separate, worth resolving alongside because it shares the mechanism: a codex launch from a specialist template symlinks `skills/` into the overlay, and `codex debug prompt-input` writes `skills/.system` as a bundled tree of six skills, roughly ninety entries. Verified against codex-cli 0.148.0 with `CODEX_HOME` pointed at an empty scratch directory. That is Transport Matters writing into agent-runtimes' runtimes, which breaks the clean contract rather than policing it.

## Also in scope

The other eight sets in the same module, for consistency and for whether each still earns its place:

- `_CLAUDE_DAEMON_LOCAL_NAMES`
- `_CLAUDE_OVERLAY_COPIED_NAMES`, `_CODEX_OVERLAY_COPIED_NAMES`, `_GROK_OVERLAY_COPIED_NAMES`
- `_CLAUDE_OVERLAY_CREDENTIAL_NAMES`, `_CODEX_OVERLAY_CREDENTIAL_NAMES`, `_GROK_OVERLAY_CREDENTIAL_NAMES`
- `_CLAUDE_OVERLAY_LOCAL_NAMES`, `_CODEX_OVERLAY_LOCAL_NAMES`, `_GROK_OVERLAY_LOCAL_NAMES`
- `_OVERLAY_NEVER_SYMLINK_NAMES`

The `_OVERLAY_LOCAL_NAMES` trio governs the native home path, where the source is the operator's real home and is genuinely full of runtime state. Those are load-bearing in a way the template sets are not, and the two families should stop looking alike if they are not alike.

Worth asking whether the per-harness split is the right shape at all, or whether one table keyed by harness would say the same thing in less code, which is also the repo's standing rule that adding a harness stays one edit.

## Definition of done

- A stated rule for what belongs in each family, written down, so the next name has an obvious home or an obvious rejection.
- Whichever sets are provably inert are deleted rather than trimmed.
- The specialist versus control asymmetry is resolved explicitly, not by omission.
- No new constraint is imposed on agent-runtimes. Per the owner: the contract is that the runtimes are always clean, and Transport Matters trusts it rather than guarding it.

## Context

The three template sets were briefly expanded during #412 (grok to 25 names, codex gained six) on a premise that turned out to be false, and reverted to byte-equality with main before merge. #412 also removed two guards built on that premise. This issue is the follow-up the owner asked for after that cull, and it is the question that prompted it: why do we need these at all.


## Comment by srobinson at 2026-08-20T18:31:13Z (updated 2026-08-20T18:31:13Z)

https://github.com/littleorgans/transport-matters/issues/413#issuecomment-5360084041

## Disposition: deferred, not P1

Owner's call, 2026-08-20. Worth digging into properly rather than patching now. agent-runtimes gitignores the `skills/` directory, so the pollution is regenerable and does not dirty their working tree.

Recording what is known so the dig starts from evidence rather than from scratch.

## The channel is confirmed real, and it has fired

agent-runtimes reports three specialist runtimes carried a `skills/.system` tree on 2026-08-19: `codebase-mapper`, `imagegen`, `transcript-matters`. All cleaned the same day. That sighting is what prompted their `--audit` in the first place.

It cannot be attributed. Three candidates and no surviving evidence to separate them: a TM codex launch through the overlay symlink, the owner's own testing pointing a harness directly at `~/.agent-runtimes`, or agent-runtimes' own `audit.py` running with `CODEX_HOME` pointed at a template. The `.codex-system-skills.marker` carried a build hash that would have dated the writer and it was deleted with the rest. So it is proof the channel exists, not proof TM wrote it.

## What codex actually writes

Verified against codex-cli 0.148.0, `CODEX_HOME` pointed at an empty scratch directory, `codex debug prompt-input`:

- `.sandbox_migration`, `installation_id`, `tmp/arg0` at the root
- `skills/.system` as a bundled tree of six skills (`imagegen`, `openai-docs`, `plugin-creator`, `review-agent`, `skill-creator`, `skill-installer`) plus `.codex-system-skills.marker`, around ninety entries

Codex-only. Claude writes `projects/`, `sessions/`, `shell-snapshots/` and daemon state, none of it into `skills/`.

## Exposure

Eight specialist runtimes ship a real `skills/` directory and all eight declare codex: `codebase-mapper`, `frontend`, `generalist`, `imagegen`, `orchestrator`, `research`, `skill-matters`, `transcript-matters`.

Control templates are not exposed. `tm/capture` and `tm/capture-grok` carry only regular files, so a baseline harvest cannot hit this.

## The option that does not work

Naming `skills` in `_CODEX_TEMPLATE_LOCAL_WRITABLE_NAMES` strips the skills. `home_overlay:_materialize_local_writable_entries` creates an empty directory and copies nothing, which is correct for `sessions`, `projects` and the sqlite files where empty is the point, and wrong for content the run has to read. Both this repo and agent-runtimes reached that conclusion independently, from opposite directions.

## The option both sides recommend

Copy `skills/` into the overlay on the codex path only.

agent-runtimes measured the worst tree in the catalog, `frontend/skills` at 73 files and 903 KB: `shutil.copytree` 15.1 ms, `cp -Rc` with clonefile 19.1 ms. The cost is metadata on small files rather than bytes, so APFS cloning loses once the subprocess is counted. Every other runtime is smaller; `codebase-mapper` and `orchestrator` are one skill each.

Since agent-runtimes vendored skills as real bodies (`c1ecbe4`), this is a plain recursive copy with nothing to resolve. It would not have been a week ago, when those were symlink farms.

## One nuance for whoever picks this up

The gitignore keeps the working tree clean, and it is also why the three `.system` trees survived long enough to be found by eye rather than by tooling. agent-runtimes wrote the lesson into their own `.gitignore`: how long a write-through survives is bounded by what the ignore rules hide, not by what the harness writes. `installation_id` lands at a template root, is not ignored, and has never shown in `git status`.

Not an argument against the deferral. Recorded so the dig knows why absence of evidence in `git status` is not evidence of absence here.


## Sub issues
[]
