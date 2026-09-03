# 470: Home wipe: entitlement exclusions are lost, so refused models are offered again

URL: https://github.com/littleorgans/transport-matters/issues/470
State: open
Labels: bug
Updated: 2026-09-05T03:11:02Z

Deleting a channel home makes TM forget which models the operator's account cannot use. It then offers them again and the provider refuses.

## Observed

Before wiping `~/.transport-matters-preview`, TM held:

```json
{ "launch_model": "gpt-5.2", "status": "failed",
  "target_exclusion": { "reason": "account_entitlement_unavailable", "provider_status": 400,
    "provider_message": "The 'gpt-5.2' model is not supported when using Codex with a ChatGPT account." } }
```

That is real knowledge, earned from a real 400. It lived in `baselines/attempts/codex/codex/gpt-5.2/0.149.1.json` and died with the home.

The resolver reads it from disk:

```python
excluded_models = account_entitlement_excluded_models(
    read_baseline_attempts(output=baseline_output, harness=harness_id), provider=provider)
```

(`harnesses/resolver_snapshots.py`, feeding `snapshots.account_excluded_models`.)

After the wipe, codex 0.149.1 still enumerates `gpt-5.2` as `ok`, so it becomes launchable again and a launch will be refused by the provider.

## Why this one and not the rest of the home

Most of the home regenerates for free: `settings.toml` is byte-identical to the shipped template, `runtime/` is scratch, current harness inventory repopulates at the next startup refresh. Drift evidence orphans under the new executor id, which the TLDR already calls harmless and which no operator acts on.

Entitlement exclusions are different. They are per-account facts that only a refused provider turn can establish, and losing them changes what the product offers.

## Outcome

Entitlement exclusions survive a home wipe.

## Scope

Options, in rough preference order:

1. Record the exclusion in the session store alongside the existing quota decisions (`read_known_quota_decision` already lives there), keyed by provider and model rather than by executor.
2. Keep them on disk but outside the channel home.

Note the natural key is the provider account, not the executor id. Two homes on one machine with one ChatGPT account share the refusal.

## Acceptance

- Wipe the channel home, restart, and `gpt-5.2` is still excluded without a new provider turn.
- Test covering an exclusion recorded, home discarded, exclusion still enforced.
- `just check` and `just test` green.


## Comment by srobinson at 2026-09-05T03:11:02Z (updated 2026-09-05T03:11:02Z)

https://github.com/littleorgans/transport-matters/issues/470#issuecomment-5548958570

## Still live, and now a boundary decision

Verified on `main` at 53511834: `harnesses/resolver_snapshots.py:138` and `harnesses/inventory.py:552` still read entitlement exclusions from the on disk baseline attempts under the channel home. The only reason `gpt-5.2` is excluded in the preview launch view today is that the home has not been wiped since `baselines/attempts/codex/codex/gpt-5.2/0.150.1.json` was written. No commit references this issue.

#632 proposes removing `account_entitlement_unavailable` from launch resolution and keeping it in certification and publishing, on the premise that the vendor's refreshed catalog is account aware. It is not for this case: codex 0.153.2 enumerates `gpt-5.2` with `visibility: list` and the provider still answers 400 for a ChatGPT account. The refusal is learned only from a provider turn.

Decision this issue should hold, so #632 does not encode the opposite:

- An entitlement exclusion is runtime evidence about this operator's provider account. It is never release data, because a release cannot know which account will run it.
- The session store owns it, keyed by provider and model, beside the quota decisions `read_known_quota_decision` already reads. Not the channel home, not the executor id.
- It is an enumerated block in the #384 sense: the one sanctioned refusal mechanism. Version and schema verdicts never refuse; a provider's own 400 does.

Scope of this issue is unchanged: record the exclusion in the store when the provider refuses, read it at resolution, and prove it survives a home wipe.


## Sub issues
[]
