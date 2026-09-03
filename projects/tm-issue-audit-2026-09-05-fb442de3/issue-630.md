# 630: harness discovery: enumeration acts as permission, so a model released today is undiscoverable and unverdicted

URL: https://github.com/littleorgans/transport-matters/issues/630
State: open
Labels: bug, P1
Updated: 2026-09-05T02:52:12Z

Transport Matters supports every new harness release and every new model automatically. A version inside the blessed range is supported. A version outside it is evaluated on first launch and comes out blessed or degraded. Nothing is ever blocked, and nothing is ever hidden.

Three independent defects break that premise today. `gpt-6-astra` released on 2026-09-04 and no Transport Matters user can discover it.

## Observed

`gpt-6-astra` is enumerated by the installed `codex-cli 0.153.2`, runs correctly, and is captured correctly. It does not appear in the launch view, and it has no support verdict.

```
launch view codex models   gpt-5.2, gpt-5.5, gpt-5.6-luna, gpt-5.6-sol, gpt-5.6-terra
codex exec --model gpt-6-astra   model: gpt-6-astra   ASTRA_OK   exit 0
wire_exchange.model              codex/gpt-6-astra    (11 exchanges)
roster.observed_model            gpt-6-astra
harness_target_observation       no row
support verdict                  none
```

The runtime never objected. Capture never objected. Discovery and verification are the layers that failed.

Separately, `claude` disappeared from the launch view entirely for part of the same session, while claude runs continued to launch and complete normally.

## The three causes

**1. The enumeration probe reads the build time catalog.** `harnesses/probes/codex.py:147` runs `("debug", "models", "--bundled")`, which is embedded in the binary and by construction cannot contain a model released after that binary shipped.

```
codex debug models --bundled    11 models, gpt-6-astra visibility=hide
codex debug models               9 models, gpt-6-astra visibility=list priority=1
```

The refreshed catalog also carries `gpt-5.3-codex-spark`, a second model no user can currently select, and omits `gpt-5.2`, `gpt-5.4` and both daybreak variants. The omission matters: `gpt-5.2` is the model this account's subscription cannot use, so the vendor's live catalog is already account aware.

A second, smaller filter sits behind it. `harnesses/probes/codex.py:113` discards every model whose `visibility` is not exactly `list`. Upstream `visibility` is presentation only: `list` means `show_in_picker=true`, `hide` and `none` mean `show_in_picker=false` with metadata still available for explicit selection, and `none` is what upstream mints for an unknown slug without rejecting it. Explicit model resolution never consults it. Proven by `codex exec --model gpt-6-astra` returning `ASTRA_OK` at exit 0.

**2. Resolution treats target observations as version locked permission records.** `harnesses/resolver.py:370` requires `target.harness_version == installed.normalized_version`. A harness patch release therefore erases every retained target.

```
target 2.1.260 / installed 2.1.260   10 launch options
target 2.1.260 / installed 2.1.261    0 launch options
```

Zero options makes `api/v1/harness_launch_view.py:155` emit `launchable: false` with the fallback reason `target_unavailable` at `:286`. The rows go stale because enumeration failed silently: `claude -p /model` under the shared five second probe limit returned TIMEOUT at 5.048s, while the identical command completed in 7.411s and parsed to all ten models. Failures collapse to `None` at `harnesses/probes/runner.py:229`.

Actuation is unaffected throughout. `harnesses/launch_target.py:185` converts `target_unavailable` into advisory launch arguments, which is why runs kept working while the picker offered nothing.

**3. A model the shipped release does not reference gets no verdict at all.** `support_verdict_store.py:224` requires an exact launch model match and `:78` returns silently when none exists, so the model is neither blessed nor degraded. `launch_verification.py:220` compounds this by skipping capture whenever the installed harness version sits inside the blessed range, so a new model on an in range harness is never captured and never compared.

## Outcome

A model or harness version released today is discoverable, launchable, captured, and classified blessed or degraded on its first launch. Enumeration is discovery. It is never permission.

## Sub issues

- [ ] Probe and catalog recovery
- [ ] Resolution and launch semantics
- [ ] First launch verdict for an unreferenced model


## Sub issues
[
  {
    "number": 631,
    "state": "open",
    "title": "codex enumeration: probe the refreshed catalog, admit every visibility, and stop collapsing probe failures to None"
  },
  {
    "number": 632,
    "state": "open",
    "title": "resolution: retained targets must survive a harness version change and never gate launchability"
  },
  {
    "number": 633,
    "state": "open",
    "title": "verification: a model the release does not reference must come out of first launch blessed or degraded"
  }
]
