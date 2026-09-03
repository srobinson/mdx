# 477: Launch: never block on target resolution; surface the verdict in the run status bar

URL: https://github.com/littleorgans/transport-matters/issues/477
State: open
Labels: enhancement
Updated: 2026-08-26T16:08:37Z

Stuart, 2026-08-26: nothing should ever block a launch. The launch's compatibility status (in range / above ceiling, blessed / degraded / no reference yet, unverified, unmatched) belongs in the run pane status bar next to the activity status (`RunVitalsStrip`).

## Today

`harnesses/launch_target.py::_passes_to_harness` passes only `invalid_effort`, `target_unverified_opt_in_required`, and `target_unavailable/not_observed` through as advisories. Every other resolver rejection raises `LaunchTargetRejected` (4xx on the capture RPC): `target_ambiguous`, `target_unavailable` with `no_agent_target` / `no_default_target` / `retired` / `target_probe_failed`, `account_entitlement_unavailable`. NOW.md's "never block on recognition" covers versions and unknown models; targets still refuse.

`launch_advisories` are stored on the run (`capture_rpc_routes.py`) but nothing in www reads them. Support verdicts (`support_verdict_store.py`) are keyed per release digest / route / model / version, not per run, so the status bar has no data path yet.

## Outcome

1. Every resolver rejection becomes an advisory. The launch goes out with what was asked for; the harness decides. Decide per code what string is sent (ambiguous canonical id verbatim; `no_agent_target` sends no model). Flip `docs/LAUNCH-CONTRACT.md` and the hard-failure tests.
2. A per-run launch status reaches `RunVitalsStrip`: range position, verification state (pending / blessed / degraded / no reference), and any advisories. Fed from the run's `launch_advisories` plus the verdict once verification lands.

NOW.md defers the status message behind the control-plane UI redesign. This issue records the rule and the data gap so both land together when that gate opens.

## Sub issues
[]
