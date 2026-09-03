# 555: Roster: grok observed_model reports grok-4.6-build, the harness name leaking into a model field

URL: https://github.com/littleorgans/transport-matters/issues/555
State: open
Labels: 
Updated: 2026-09-03T20:18:14Z

## Summary

Every grok run reports `observed_model: grok-4.6-build`, a model id that appears in no target
catalog. The launch declared `grok-4.6`, the request carried `grok-4.6`, and the response reported
`grok-4.6-build`. The roster surfaces an id an operator cannot look up and that matches no
launchable target.

This is a reporting question rather than a correctness failure. `observed_model` has no consumer
that makes a decision from it, so nothing downstream is currently wrong.

## Observed

Four grok runs across one session, two launched with `model=grok-4.6` and one native launch with
no declared model, all reported the same thing:

```
"model":"grok-4.6", "observed_model":"grok-4.6-build"
```

Compare the other harnesses in the same session:

| harness | declared | observed | in catalog |
| --- | --- | --- | --- |
| codex | `gpt-5.6-sol` | `gpt-5.6-sol` | yes |
| claude | `opus` | `claude-opus-5` | yes, as `canonical_model_id` |
| grok | `grok-4.6` | `grok-4.6-build` | no |

Claude's declared to observed change is an alias resolving to a documented canonical id that
`harnesses` publishes. Grok's has no such entry anywhere.

## Evidence

The two stores disagree because they record different halves of the exchange.

```sql
select distinct model from event where run_id='2fb54ba9-869c-471e-b6ba-a32e64749f21';
-- grok-4.6-build

select distinct model from wire_exchange where run_id='2fb54ba9-869c-471e-b6ba-a32e64749f21';
-- grok/grok-4.6
```

`wire_exchange` holds the request model, normalised. `event` holds the response model, raw.
`observed_model` is projected from the latest turn (`roster_projection.py:85-91`), so it reports
the response value.

The target catalog knows only two grok models:

```sql
select distinct native_model_id from harness_target_observation where harness_id='grok';
-- grok-4.5
-- grok-4.6
```

No `-build` id exists in `harness_target_observation`, and `harnesses` offers only `grok-4.5` and
`grok-4.6`, the latter `blessed`.

Normalisation cannot account for the difference. `model_ids.py:4-13` only adds or strips a prefix:

```python
def normalise_model(model: str, prefix: str) -> str:
    if model.startswith(prefix):
        return model
    return f"{prefix}{model}"
```

Nothing strips a `-build` suffix, so the response id is carried through as the provider sent it.

## Impact

`observed_model` is written at `roster_projection.py:47` and defined at `observe_models.py:54`.
Searching the API source finds no other consumer: no comparison against the declared model, no
input to support state, no gate on launch. The compatibility contract keys on harness version, not
on the response model id, so the blessed range for grok 1.0.5 is unaffected.

What it costs is discoverability. An operator reading the roster sees a model that is not offered
by `harnesses`, is not in the catalog, and cannot be launched by that name. Any future check that
compares declared against observed would mismatch on every grok run.

## Resolved: the suffix is the harness, not the model

`grok-4.6-build` is not a model id. xAI publishes `grok-4.6` as the API id, and **Grok Build is the
name of xAI's coding agent CLI**, which is the harness Transport Matters launches. The suffix names
the agent surface the request arrived through, not a deployed build variant.

That answers the question this issue originally put to the maintainers. Option 2 is correct, and on
firmer ground than the issue assumed: this is not a build tag the catalog is failing to track. It is
a harness identifier leaking into a model field, so no catalog entry will ever exist for it.

Sources: [Grok Build overview](https://docs.x.ai/build/overview),
[Grok 4.6 docs](https://docs.x.ai/developers/grok-4-6),
[Introducing Grok 4.6](https://x.ai/news/grok-4-6).

## Current state

Still reproducing. `roster_projection.py`, `model_ids.py` and `observe_models.py` are unchanged
between `1d199d18` and `6d8e21dc`.

Every grok response ever recorded in the preview channel carries the same value, with no variation:

```sql
select model, count(*), min(ts)::date, max(ts)::date
from event where model like 'grok%' group by model;
-- grok-4.6-build | 148 | 2026-08-31 | 2026-09-01
```

## Fix

Strip the agent suffix on the grok projection path. `model_ids.py:4-13` currently only adds or
strips a prefix, so the suffix rule belongs beside it rather than in the roster.

`event` keeps the raw response value as captured evidence. Only the projection resolves. The
operator gets an id that `harnesses` can answer for, and the capture keeps what the provider
actually sent.

This is safe to do now. The compatibility contract keys on harness version rather than the response
model id, so the blessed range for grok 1.0.5 is unaffected, and `observed_model` still has no
consumer that makes a decision from it.

## Verification

1. Regression pinning declared to observed resolution per harness, so an unresolvable id fails a
   test rather than reaching the roster. This is the durable guard and the reason the issue is worth
   closing properly rather than patching the string.
2. `observed_model` for grok resolves to something an operator can find in `harnesses` output.

## Remaining boundaries

- The 148 samples span two days and exercise only `grok-4.6`. Nothing here establishes how
  `grok-4.5` reports, and the fix should not assume the suffix is the only variant.
- The Grok Build finding comes from xAI's public documentation, not from an authenticated
  `/v1/models` call on this account. That call is the cheap way to close the question against the
  account actually in use.

## Environment

Branch `main` at `1d199d18`, preview channel, grok harness 1.0.5, launched as `grok-4.6` at
`tm/generalist`, medium effort. Also observed on a native launch with no declared model.



## Sub issues
[]
