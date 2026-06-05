# Claude Code 2.1.238 selectors: fixed vs per-turn

Harness: `/Users/alphab/.local/share/claude/versions/2.1.238` (Mach-O, `claude --version` = `2.1.238 (Claude Code)`, embedded `VERSION:"2.1.238"` `GIT_SHA:"46283063a4c23f7afadb8440f549264ad93b7c06"`). Docs: https://code.claude.com/docs/en/model-config (fetched 2026-08-22). No session launched, no provider traffic.

Alias table in the binary (`JYe`): `sonnet`, `opus`, `haiku`, `fable`, `best`, `sonnet[1m]`, `opus[1m]`, `fable[1m]`, `opusplan`. Family aliases only (`TPn`): `sonnet`, `opus`, `haiku`, `fable`. `default` is not in `JYe`. `opusplan[1m]` is the `[1m]` suffix on `opusplan`, not a separate table entry.

## Selectors asked

`best`: fixed. Not a per-turn policy. `Ss("best")` returns `ECd()`. `wCd()` reads catalog `ECe().best`; if that family exists in `e8o` and `available()` is true, use it, else `"opus"`. At this build `e8o` only has `fable` (`available:YQt`, `defaultModel:fDn`). `ECd` then returns that family's default model if `Uu(t)` (allowlisted/available), else `MA()` (opus default). No `permissionMode` / prompt / plan-mode branch. Official table: "Uses Fable 5 where your organization has access to it, otherwise the latest Opus model." Re-evaluation if fable entitlement flips mid-session was not traced; still not a turn router.

`default`: fixed. Not a per-turn policy. Official table: "Special value that clears any model override and reverts to the runtime default for your account. Not itself a model alias." `Gi()` uses `Ss(X2())` when a model is set, else `CE()` = `Ss(o8())` = `Ss(Upt().setting)`. `Upt`/`RCd` pick an account-type (or org / `ANTHROPIC_DEFAULT_MODEL`) resting model; `cOt` ignores env values `default`, `inherit`, `opusplan`, and `haiku`. `RCd` last arm returns `{setting:NP(), envFamily:"sonnet"}` (sonnet) when the opus-default arms do not apply. Docs: Max / API / several enterprise paths default to Opus 5; Pro / Team Standard / Enterprise subscription seats default to Sonnet 5.

`opusplan`: per-turn policy. Proven. `Ss("opusplan")` always returns `NP()` (sonnet), or `Cre(NP())` for `opusplan[1m]`. The switch is `DM({permissionMode, mainLoopModel, exceeds200kTokens})`: if selected model `X2()` is `opusplan` or `opusplan[1m]` AND `permissionMode==="plan"` AND NOT `exceeds200kTokens`, return opus (`MA()`, or `Cre(MA())` when `opusplan[1m]` or auto-1M `l3()`). Otherwise return the resting `mainLoopModel`. Callers pass the live permission mode per query (e.g. `runtimeModel: DM(...)` vs `mainLoopModel`). Binary UI copy: "Opus in plan mode, else Sonnet" / "Use Opus in plan mode, Sonnet otherwise". Docs match. A trivial prompt that never enters plan mode therefore wires as sonnet; storing `opusplan = claude-sonnet-5` as a fixed alias is wrong.

## `[1m]`

Same model family, different context configuration. `kE(e)` is `/\[1m\]/i.test(e)` unless `Gpe()` (`CLAUDE_CODE_DISABLE_1M_CONTEXT`). `ll` / `pae` / `ld` strip `[1m]` (and `ld` also `[2m]`). `Cre` appends `[1m]`. `I7` is catalog `context.supports_1m_beta`; `IU` is catalog `context.native_1m` (Sonnet 5 / Opus 5 / Fable 5 on first-party, etc.).

Wire: request object is `{model:kre(t), ..., ...(betas.length)&&{betas:s3(A)}}` then `beta.messages.create`. `kre`/`toProviderWireModelId` starts with `ld(e)`, so the JSON body `model` field does not contain `[1m]`. `WTb` does `if(kE(e)) t.push(R7)` with `R7=Fx("long_context","context-1m-2025-08-07")`. `s3` maps betas to `.header` strings. The SDK lifts `betas` into the `anthropic-beta` header (`"anthropic-beta":[...].toString()`), not into the body `model` field. Context-size helper: `1e6` if `kE(e)` OR (`R7.header` present and `I7`) OR `IU(e)`.

Docs: "Claude Code strips the suffix before sending the model ID to your provider." `sonnet[1m]` "No effect when `sonnet` already resolves to Sonnet 5 with its native 1M window; behind an LLM gateway, selects the 1M window for Sonnet 5." `opusplan[1m]` forces 1M on both opusplan phases.

`~/.claude/settings.json` (read only): `"model":"opus"`, env `__CLAUDE_CODE_DISABLE_1M_CONTEXT":"true"`. Binary flag is `CLAUDE_CODE_DISABLE_1M_CONTEXT` (`Gpe`). See follow-up: the double-underscore settings key is a distinct `process.env` name and is not what `Gpe()` reads.

## Not determined

- Live value of catalog `ECe().best` on this machine (would need a request or executing the bundled catalog, not done).
- Whether `ECd`/`Upt` results are cached for a session or recomputed on every `Gi()`/`Ss()` call.
- Whether a native-1m model without a `[1m]` suffix still sends `context-1m-2025-08-07` (code only pushes `R7` when `kE(e)` is true).
- `haiku` also upgrades in plan mode inside `DM` (to sonnet). Out of scope; noted so it is not mistaken for `opusplan`.

## Capture `[1m]` cells and `DISABLE_1M`

### 1. `tm/capture` template does not disable 1M

Inspected `~/.agent-runtimes/runtimes/tm-capture` (files: `settings.json`, `runtime.toml`, `capabilities.json`, `.claude.json`, `config.toml`, `config.grok.toml`). `rg DISABLE_1M|context-1m|long_context` over that tree: no matches.

Capture home Claude settings that actually get installed (`settings.json`):

```json
"env": {
  "ENABLE_TOOL_SEARCH": "auto:100",
  "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1"
}
```

`runtime.toml` `[settings.claude] env` is only `ENABLE_TOOL_SEARCH`. `capabilities.json` launch_requirements add `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`. Overlay copies the template's `settings.json` (`_copy_secret_file_if_missing` from the template source, `home_overlay.py`), then merge-only adds `skipDangerousModePermissionPrompt` and TM proxy keys (`ANTHROPIC_BASE_URL`, run id, `NO_PROXY`). Operator `~/.claude/settings.json` is not that source.

Ambient child env: isolated-home launches drop keys whose `lstrip("_")` starts with `CLAUDECODE` / `CLAUDE_` / `CODEX_` / `GROK_` (`environment.py` `_ambient_harness_env_keys`). Test `test_isolated_home_drops_the_operators_own_harness_session` asserts `__CLAUDE_CODE_DISABLE_1M_CONTEXT` is absent from the isolated env.

### 2. `Gpe()` does not read the double-underscore key

`function Gpe(){return V.CLAUDE_CODE_DISABLE_1M_CONTEXT}`. `V=B3s(fb_,uOr)` (`2.1.238` @ 281639129):

```js
function B3s(e,t){let r=Object.create(t);for(let[n,o]of Object.entries(e)){let i=r,s;Object.defineProperty(r,n,{get:()=>{let a=process.env[n];if(a!==i)s=o.parse(a),i=a;return s},...}) }...}
```

The getter is `process.env[n]` with `n` the schema key `CLAUDE_CODE_DISABLE_1M_CONTEXT`. No underscore strip. String `__CLAUDE_CODE_DISABLE_1M_CONTEXT` is not in the binary (0 hits). Settings `env` is applied with `Object.assign(process.env, this.filterSettingsEnv(...))`; filters drop some keys, they do not rename `__FOO` to `FOO`. So a settings-file key with two leading underscores is a distinct `process.env` name from the flag `Gpe()` reads. The operator's `__CLAUDE_CODE_DISABLE_1M_CONTEXT` would not itself turn `Gpe()` on.

### 3. Consequence

The three `[1m]` baseline cells are **valid**. The capture home is not seeded with `CLAUDE_CODE_DISABLE_1M_CONTEXT`, isolated-home stripping removes an ambient `__CLAUDE_CODE_DISABLE_1M_CONTEXT`, and that double-underscore name is not the `Gpe()` flag. Body EXACT against the non-`[1m]` sibling is explained by `ld(e)` / `kre` stripping the suffix from the JSON `model` field, not by 1M being switched off.

Header confirmation (not in the baseline bundle's `raw_request_base64`): the captured run's exchange `transport.json` (`<run storage_dir>/<YYYYMMDDTHHMMSSZ>-<shortid>/transport.json`, `disk_layout.py`). Claude is HTTP, so the field is `request.headers` (list of `{name, value}`). Look up `anthropic-beta` case-insensitively (`transport_request_header_lookups` in `storage/base.py`, which also consults `upgrade.request_headers`; empty transport is no evidence, not an absent header). The token would be `context-1m-2025-08-07`. Not searched across runs.

## Effort provenance

Read-only against `main` `03dc8d62`, interpreter `api/.venv/bin/python`, store `~/.transport-matters/baselines` (stable). No harness launched.

### 1. Reconstruction

`baseline_harvest._enumerated_models` rebuilds `EnumeratedModel` from the launch view, not from `HarnessInventoryItem.launch_options` or target observations.

Uniform path (all models share one effort-option tuple). `default_effort` is omitted, so it is `None`:

```python
if isinstance(item, UniformEffortHarnessView):
    return tuple(
        EnumeratedModel(model_id=model, effort_options=item.efforts) for model in item.models
    )
```

Varying path keeps `model.default_effort`.

`project_harness_launch_view` chooses Uniform iff every projected model has the same `efforts` list (`harness_launch_view.py` `_project_harness`). Per-model `default_effort` is not part of that test, and Uniform does not carry it.

`baseline_capture._run_probe` then does `effort=model.default_effort`. `launch_profile._codex_effort_argv` / `_grok_effort_argv` substitute nothing: `[] if effort is None else ["-c", f"model_reasoning_effort={effort}"]` (codex) or `--reasoning-effort` (grok). `None` omits the flag; it does not pin a TM-wide effort.

### 2. Recorded `raw_request_base64` vs that path

`read_current_baselines`. Codex `reasoning.effort` is identical across a1/b/a2 in every cell. All four cells `harness_version=0.148.0`.

| launch_model | recorded effort | live inventory `native_default_effort` | reconstructed `default_effort` |
| --- | --- | --- | --- |
| gpt-5.5 | medium, medium, medium | medium | medium |
| gpt-5.6-luna | medium, medium, medium | medium | medium |
| gpt-5.6-sol | low, low, low | low | low |
| gpt-5.6-terra | medium, medium, medium | medium | medium |

Live stable inventory (`executor 9a68e89f-…`, channel `stable`, `codex-cli 0.148.0`) is `VaryingEffortHarnessView` because effort *options* differ (`gpt-5.5` has no `max`/`ultra`; luna has `max` not `ultra`; sol and terra have `max` and `ultra`). Reconstruction therefore keeps per-model defaults. Through the harvest path as it stands now, those four models would be launched with exactly the recorded efforts.

Claude cells carry `output_config.effort` (not `reasoning.effort`): `high` on every probe except `haiku`, which has no `output_config`. Claude is Uniform; inventory `default_effort` is already `None`. Grok cells carry `reasoning.effort=high` on every probe of `grok-4.5` and `grok-4.6`. Grok is Uniform with empty options and `default_effort=None`.

### 3. Verdict

**Refuted** as the cause of the observed Codex split. The Uniform-path drop is real code, and it is what Claude and Grok take, but Codex does not take it: option sets differ, so harvest keeps `default_effort`. The wire split is the Codex catalog's per-model `default_reasoning_level`.

Parser (`harnesses/probes/codex.py` `_parse_model_enumeration`): `default_effort = raw_model.get("default_reasoning_level")`, options from `supported_reasoning_levels[].effort`. Probe command `("debug", "models", "--bundled")`. Not executed (would launch the harness). Stored target observations at the same `0.148.0` already hold sol=`low`, luna/terra/5.5=`medium`. The adapter test fixture (`test_codex.py`) uses the same fields: sol `default_reasoning_level=low`, gpt-5.5 `medium`.

Not a harness-version mix: all four Codex cells are `0.148.0`. 5.6-* share `source_commit=b89831517278`. Capture `passthrough=()`. A Uniform-path `None` would omit the flag and let the harness apply those same native defaults, so the wire split would look the same; that path is not the one the current (and 0.148.0) Codex view takes.

## Pinning effort to low

Read-only. Stable executor `9a68e89f-d85c-44b1-9859-7ab1d0ef7d7b`. Inventory query as before. No harness session launched. `grok --help` and grok 1.0.5 binary strings only.

### 1. Stored target observations

Every observed model, `completeness=complete`.

Claude (`2.1.237` in inventory; captures were `2.1.238`): all ten models (`best`, `default`, `fable`, `fable[1m]`, `haiku`, `opus`, `opus[1m]`, `opusplan`, `sonnet`, `sonnet[1m]`) share efforts `('low', 'medium', 'high', 'xhigh', 'max', 'auto')` and `default_effort=None`. `low` is among them. Enumeration copies one global `/effort` vocabulary onto every model (`probes/claude.py`); it is not per-model.

Codex (`0.148.0`): `low` is on every model.

| model | native_efforts | default |
| --- | --- | --- |
| gpt-5.2 | low, medium, high, xhigh | medium |
| gpt-5.5 | low, medium, high, xhigh | medium |
| gpt-5.6-luna | low, medium, high, xhigh, max | medium |
| gpt-5.6-sol | low, medium, high, xhigh, max, ultra | low |
| gpt-5.6-terra | low, medium, high, xhigh, max, ultra | medium |

Grok (`1.0.5`): `grok-4.5` and `grok-4.6` have `native_efforts=()` and `default_effort=None`. The option set is genuinely empty in the store. The grok probe (`probes/grok.py`) parses `grok models` and always builds `EnumeratedModel(..., effort_options=())`.

### 2. What TM sends

`baseline_capture._run_probe` → `CapturedRunRequest.effort=model.default_effort` → `LaunchProfile.client_argv(effort=...)`. Harvest does not go through `resolve_target`.

| harness | effort is `None` | effort is `"low"` |
| --- | --- | --- |
| claude | no extra argv | no extra argv: `ClaudeLaunchProfile.client_argv` does `_ = effort` with the comment "Claude has no separate launch effort flag" (`launch_profile.py`). Capture RPC still records `effort_not_actuated` if a caller sets effort (`capture_rpc_routes.py`). |
| codex | no extra argv | `-c model_reasoning_effort=low` |
| grok | no extra argv | `--reasoning-effort low` |

The installed Claude binary does take a flag: `claude --help` lists `--effort <level>` (`low, medium, high, xhigh, max`). TM does not pass it.

### 3. Where recorded `high` came from

Claude cells: `output_config.effort=high` on every probe except `haiku` (no `output_config`). TM passed `None`, so no `--effort`. That `high` is the Claude Code native default (docs: default effort is `high` except Opus 4.7). Passing `"low"` through the current harvest path would not change it: the field is discarded. Wiring `--effort low` would be a new launch-profile change; not proven live. `haiku` did not emit an effort field at native default, so whether `--effort low` would appear on its body is undetermined.

Grok cells: `reasoning.effort=high` on every probe. TM passed `None`, so no `--reasoning-effort`. That `high` is the grok native default when the flag is omitted. Passing `"low"` would add `--reasoning-effort low`. The 1.0.5 binary error text is `expected one of: none, minimal, low, medium, high, xhigh, max`; embedded help repeats those as canonical levels. Expected to change the wire; not proven by a capture.

Codex cells already match catalog defaults (sol `low`, others `medium`). Passing `"low"` would add `-c model_reasoning_effort=low` on every model, changing luna/terra/5.5 and leaving sol unchanged.

### 4. Verdict

- **claude: the harness takes no effort flag (TM).** Binary offers `--effort low` unused. Honest alternative: add `--effort low` to `ClaudeLaunchProfile` (option is enumerated, including `low`), or leave the native `high` and record it. Current `_run_probe` passing `"low"` is a no-op.
- **codex: `low` is passable.** Present on every stored model's `native_efforts`. Harvest argv already has a path.
- **grok: stored option set is empty; CLI still accepts `low`.** Probe never enumerates efforts. Harvest argv would pass `--reasoning-effort low`, which the binary lists as valid. Resolver `invalid_effort` would reject grok+`low` on the MCP capture path because `completeness=complete` and `native_efforts=()`. Honest alternative for harvest: pin `--reasoning-effort low` anyway, or scrape grok's effort menu so observations are non-empty; do not treat the empty tuple as "harness has no effort". Native default when unpinned is `high`.
