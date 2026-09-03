# 631: codex enumeration: probe the refreshed catalog, admit every visibility, and stop collapsing probe failures to None

URL: https://github.com/littleorgans/transport-matters/issues/631
State: open
Labels: bug, P1
Updated: 2026-09-05T02:52:14Z

Sub issue of the harness and model discovery epic.

The codex enumeration probe reads the catalog embedded in the binary, so a model released after that binary shipped can never be discovered. A second filter discards models the vendor marks as hidden in its own picker. Enumeration failures collapse to `None`, so a slow probe silently preserves stale rows.

## Observed

```
codex debug models --bundled    11 models, gpt-6-astra visibility=hide
codex debug models               9 models, gpt-6-astra visibility=list priority=1
```

The refreshed catalog additionally carries `gpt-5.3-codex-spark` (`list`, priority 26) and `gpt-reserve`. It omits `gpt-5.2`, `gpt-5.4` and both daybreak variants, so it is account aware.

`visibility` is presentation only. `list` means `show_in_picker=true`; `hide` and `none` mean `show_in_picker=false` with metadata still available for explicit selection, and `none` is what upstream mints for an unknown slug without rejecting it. Explicit resolution never consults it. `codex exec --model gpt-6-astra` printed `ASTRA_OK` at exit 0.

Measured in a production style probe environment:

| command | latency |
| --- | --- |
| refreshed, stale cache | 0.557s |
| refreshed, fresh cache | 0.15 to 0.20s |
| bundled | 0.154s |
| refreshed, unauthenticated isolated home | exit 0 in 0.164s, bundled catalog |

The refreshed command is a catalog GET. It sends no model turn and costs no tokens. It advances `~/.codex/models_cache.json`, so it does perform network and filesystem IO. Startup is unaffected because `run_startup_refresh` is an unawaited background pass at `main.py:455`.

The claude enumeration probe measured 4.731s against a five second shared limit, leaving 0.269s of headroom, and was observed to time out at 5.048s earlier the same day against a command that completes in 7.411s.

## Scope

- `harnesses/probes/codex.py`: make `("debug", "models")` the primary command with `("debug", "models", "--bundled")` as fallback. Parse `list`, `hide` and `none` identically; delete the visibility filter at `:113`. Bump to `codex-model-enumeration-r2`.
- `harnesses/probes/__init__.py`: add `fallback_commands`, `refresh_policy` and `snapshot_policy` to `ModelEnumerationProbeAdapter`. Add typed `ModelEnumerationSuccess` and `ModelEnumerationFailed` results.
- `harnesses/probes/runner.py`: add a 30 second enumeration timeout distinct from the five second authentication timeout. Run primary then fallback. Return structured results with a closed failure vocabulary (`timeout`, `nonzero_exit`, `invalid_output`, `execution_failed`) and no raw stderr, paths or arguments.
- `harnesses/state_refresh.py`: consume structured results, log sanitized failure and fallback reasons, and record codex results as partial snapshots. Codex refreshes on every startup, because the remote catalog changes while the CLI version does not, so a revision bump alone would only repair the first startup.

Merge rules when the two catalogs disagree: a successful refreshed result wins for every model it returns and bundled is not consulted; if refreshed fails and bundled succeeds, bundled wins for models it returns; a model absent from the successful result retains its previous row unchanged, including version, timestamp, efforts and default effort; if both attempts fail, no target rows change. A model present only in the last known set stays offered. `record_target_snapshot` already upserts without deleting omissions under `partial` completeness, so no storage change is needed.

Do not persist upstream `show_in_picker`. Importing codex's presentation policy would recreate a hidden model class inside Transport Matters.

## Verification

- `probes/test_codex.py`: assert refreshed then bundled command order, `r2`, and retention of `list`, `hide` and `none` models with their effort fields.
- `probes/test_runner.py`: primary success, timeout fallback, nonzero fallback, parser fallback, both attempts failing, sanitized failures, and the separate 30 second enumeration timeout.
- `test_state_refresh.py`: fake store honours partial merge; codex refreshes at an unchanged CLI version; refreshed models update; omitted models retain provenance; complete failure changes no rows.
- A production style codex refresh run once authenticated and once in an isolated unauthenticated home.

## Outcome

`gpt-6-astra` and `gpt-5.3-codex-spark` appear in the launch view. The claude enumeration timeout stops silently preserving stale rows.


## Sub issues
[]
