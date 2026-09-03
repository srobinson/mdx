# 515: Add a read-only watch status verb to the control-plane MCP

URL: https://github.com/littleorgans/transport-matters/issues/515
State: open
Labels: enhancement
Updated: 2026-08-29T02:26:08Z

## Problem

`watch` and `unwatch` are the only verbs on the watch surface. There is no way to ask what this run is currently subscribed to.

The consequences show up in real orchestration:

- **Subscriptions are invisible.** An orchestrating run that registered a watch several turns ago has no way to confirm it still holds one. After a context summarization or a resume, the only record is the model's recollection of a tool call.
- **Observation requires mutation.** The one signal available is `changed` on the `watch` response, so the only way to learn whether a subscription exists is to re-register it. That works because registration is idempotent, but reading state by writing it is the wrong shape.
- **Redundant watches are undetectable.** A workspace watch covers runs launched after it was registered, and runs the session never launched. A per-run watch on a covered run therefore delivers a second copy of every event. Nothing in the API reveals the overlap.
- **Stale watches accumulate.** A watch on a run that has since been closed stays registered with nothing to report, and there is no way to enumerate and reap them.

Observed directly: a session registered a workspace watch alongside a per-run watch on the same run and double-pinged on every event, with no way to see why. Separately, `state_changed` on a workspace target fires on every `reasoning` to `running-tools` flip of every live run, so a redundant registration multiplies an already high-volume event.

## Proposal

A read-only status verb, consistent with the existing separate-verb style rather than an action discriminator on `watch`:

```
watch_status()                 -> every subscription held by this run
watch_status(target="<id>")    -> just that one
```

Per subscription:

| field | purpose |
| --- | --- |
| `target` | run id, or the workspace target |
| `events` | the subscribed event set |
| `registered_at` | when it was established |
| `last_event_at` | last delivery, so a silent watch is distinguishable from a dead one |
| `deliveries` | count since registration |
| `target_state` | live, exited, or unknown; identifies watches worth reaping |
| `shadowed_by` | set when a workspace watch already covers this target |

`shadowed_by` is the field that carries the most value. It turns an invisible duplication into something an orchestrator can detect and fix with one `unwatch`, and it is derivable from state the server already holds.

An empty result is a legitimate answer and should be distinguishable from an error, so a caller can tell "no subscriptions" from "could not determine".

## Notes

- Watches are session-local, so status is scoped to the calling run, matching `unwatch`, which the tool description already frames as removing "this run's watch".
- Purely additive. No change to `watch` or `unwatch` semantics.
- Naturally pairs with a follow-up: having enumerated stale subscriptions, a caller wants to drop several at once, so `unwatch` accepting a list would compose well. Out of scope here.

## Documentation impact

The `tm-orchestrate` skill recommends registering exactly one workspace watch on `turn_completed` and avoiding per-run duplicates. That guidance is currently unverifiable at runtime by the agent following it.


## Sub issues
[]
