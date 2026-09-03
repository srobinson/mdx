# 472: Canvas: launch toggles silently reset to off after a home wipe

URL: https://github.com/littleorgans/transport-matters/issues/472
State: open
Labels: bug
Updated: 2026-08-26T14:08:14Z

Wiping a channel home silently resets the Canvas launch toggles to off.

## Observed

After deleting `~/.transport-matters-preview` and relaunching, both toggles came back off:

- **Bypass all permission checks** ("spawned agents skip permission prompts")
- **Control plane access** ("Director: spawned agents can inspect and manage peer runs")

Nothing said they had changed. The next spawned orchestrator was launched without control plane access, which is not a state an operator would think to re-check after a restart.

## Outcome

The toggles survive a home wipe, or the operator is told they were reset.

## Scope

- Establish where these are persisted today. `electron-user-data/` is one candidate, the session store is another.
- If they belong to the operator rather than the channel, they do not belong in a directory that is treated as disposable.

## Acceptance

- Set both toggles, wipe the channel home, relaunch, and the settings are unchanged.
- `just check` and `just test` green.


## Sub issues
[]
