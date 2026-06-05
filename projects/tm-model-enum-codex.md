# Codex runtime model enumeration

Date: 2026-07-19

## Conclusion

Trusted path: **yes**.

Codex `0.144.4` has an official, noninteractive JSON command:

```sh
codex debug models
codex debug models --bundled
```

`debug models` is the account effective path. It uses a fresh, version matched cache when one exists, otherwise it requests the provider model endpoint. `debug models --bundled` skips refresh and emits the catalog compiled into that exact executable.

Transport Matters should probe `debug models` per executable and connection, retain explicit provenance, and replace the hand authored target seeding at `state_refresh._seed_target_snapshot()`. The current target observation and snapshot store are already the correct downstream contract.

## Official source

Source tag: [`rust-v0.144.4`](https://github.com/openai/codex/tree/8c68d4c87dc54d38861f5114e920c3de2efa5876), commit `8c68d4c87dc54d38861f5114e920c3de2efa5876`.

Authoritative symbols:

- [`DebugModelsCommand`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/cli/src/main.rs#L277-L280) declares `--bundled` as the no refresh path.
- [`run_debug_models_command`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/cli/src/main.rs#L1988-L2015) emits `ModelsResponse` JSON. Its default uses `RefreshStrategy::OnlineIfUncached`; `--bundled` calls `bundled_models_response()`.
- [`bundled_models_response`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/src/lib.rs#L12-L16) compiles [`models.json`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/models.json) with `include_str!`.
- [`OpenAiModelsManager`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/src/manager.rs#L213-L247) starts from the bundled catalog and owns the remote catalog, ETag, and `$CODEX_HOME/models_cache.json`.
- [`refresh_available_models`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/src/manager.rs#L335-L391) uses a version matched cache first and requests the server on a miss. [`apply_remote_models`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/src/manager.rs#L398-L428) makes a nonempty ChatGPT catalog authoritative; other routes merge remote rows into bundled rows.
- [`ModelsCacheManager`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/models-manager/src/cache.rs#L14-L92) requires the exact client version and a five minute TTL. The cache records `fetched_at`, `etag`, `client_version`, and `models`.
- [`ModelsClient`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/codex-api/src/endpoint/models.rs#L31-L70) sends `GET models?client_version=<version>` and parses `ModelsResponse` plus ETag.
- [`ModelInfo`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/protocol/src/openai_models.rs#L352-L364) defines the required fields: `slug`, `default_reasoning_level`, `supported_reasoning_levels`, `visibility`, `supported_in_api`, and `priority`.
- [`ModelPreset::filter_by_auth` and `mark_default_by_picker_visibility`](https://github.com/openai/codex/blob/8c68d4c87dc54d38861f5114e920c3de2efa5876/codex-rs/protocol/src/openai_models.rs#L635-L658) define picker filtering and default selection.

There is no model enumeration config key or schema list that is more authoritative than this path. `model` and `model_reasoning_effort` select values; they do not enumerate supported combinations.

## Exact read and parse

For the effective ChatGPT catalog under the connection's own `CODEX_HOME`:

```sh
/path/to/codex debug models | jq '
  .models
  | sort_by(.priority)
  | map(select(.visibility == "list"))
  | map({
      model_id: .slug,
      efforts: [.supported_reasoning_levels[].effort],
      default_effort: .default_reasoning_level,
      priority
    })
'
```

For the exact static catalog embedded in the installed binary, with no provider request:

```sh
/path/to/codex debug models --bundled | jq '
  .models
  | sort_by(.priority)
  | map(select(.visibility == "list"))
  | map({
      model_id: .slug,
      efforts: [.supported_reasoning_levels[].effort],
      default_effort: .default_reasoning_level,
      priority
    })
'
```

The parser should use JSON fields, never display names or picker text. For the ChatGPT route, picker membership is `visibility == "list"`. For API key routes, also require `supported_in_api == true`. Sort by numeric `priority`. The first picker visible row is the source implementation's default.

Important provenance rule: `debug models` returns exit code 0 even when refresh fails because `raw_model_catalog()` logs the error and returns its current in memory catalog. A complete remote result therefore needs corroboration from `$CODEX_HOME/models_cache.json`:

- `client_version` equals the normalized executable version.
- `fetched_at` is within the five minute source TTL.
- The cache parses as the same `ModelInfo` schema.
- For authenticated ChatGPT with at least one visible remote model, command output matches the cache catalog.

Without that proof, classify the result as bundled fallback or unknown. Do not call it a complete account availability snapshot.

## Static versus server fetched

Both sources exist.

`--bundled` is static in the executable and changes with the Codex release. Re-read it for every installed binary version. It is suitable for schema support and fallback metadata. It cannot prove the account's current picker because the server can add, hide, or reprioritize models.

The default command uses `OnlineIfUncached`. A fresh version matched cache avoids a request. A miss requests the provider's `models?client_version=<version>` endpoint and persists the response with an ETag. For ChatGPT authentication, a nonempty remote response containing a visible model becomes the catalog authority. The picker then derives its rows and efforts from that catalog.

The observed `0.144.4` picker and bundled output prove the distinction. The picker included `gpt-5.3-codex-spark`; the `0.144.4` bundled catalog included `gpt-5.2` in that position. Model availability can therefore change independently of the installed version.

## Installed runtime facts

The requested executable path was checked directly:

```text
/Users/alphab/.local/share/mise/installs/node/25/bin/codex
readlink: ../lib/node_modules/@openai/codex/bin/codex.js
current version at 2026-07-19 09:37 +07: codex-cli 0.144.6
```

The supplied `0.144.4` version fact had drifted before this scout ran. The official `@openai/codex@0.144.4` package was invoked separately to verify that the historical executable exposes `debug models` and `debug models --bundled`. Source and command behavior were pinned to the matching `rust-v0.144.4` tag.

The supplied live picker observation for `0.144.4` remains the comparison authority below: `gpt-5.5` default; `gpt-5.6-sol` current; then `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.4`, `gpt-5.3-codex-spark`, and `gpt-5.4-mini`.

## Models and effort levels

| Runtime model | Valid efforts | Default effort | Transport Matters status |
|---|---|---|---|
| `gpt-5.5` | `low`, `medium`, `high`, `xhigh` | `medium` | Missing |
| `gpt-5.6-sol` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` | `low` | Model present; all effort metadata missing |
| `gpt-5.6-terra` | `low`, `medium`, `high`, `xhigh`, `max`, `ultra` | `medium` | Missing |
| `gpt-5.6-luna` | `low`, `medium`, `high`, `xhigh`, `max` | `medium` | Missing |
| `gpt-5.4` | `low`, `medium`, `high`, `xhigh` | `medium` | Missing |
| `gpt-5.3-codex-spark` | `low`, `medium`, `high`, `xhigh` | `high` | Missing |
| `gpt-5.4-mini` | `low`, `medium`, `high`, `xhigh` | `medium` | Model present; all effort metadata missing |

`supported_reasoning_levels` is the valid set for a model. `default_reasoning_level` is the per model default when effort is omitted. Every picker model in this observed catalog accepts explicit effort selection.

## Full catalog diff

Transport Matters currently declares:

```text
gpt-5-codex       low,medium,high,xhigh   default medium
gpt-5.6-sol       no efforts              no default
gpt-5.4-mini      no efforts              no default
```

Diff against the observed runtime picker:

- Invented or retired ID: `gpt-5-codex`. The installed `0.144.4` picker did not offer it. The official `0.144.4` bundled catalog also does not contain it.
- Missing IDs: `gpt-5.5`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.4`, and `gpt-5.3-codex-spark`.
- Correct IDs with wrong capabilities: `gpt-5.6-sol` and `gpt-5.4-mini` have empty effort sets and null defaults in Transport Matters. Their runtime effort sets and defaults are listed above.
- Wrong absence semantics: `state_refresh._seed_target_snapshot()` records the hand authored release catalog with `completeness="complete"`. This retires real runtime targets and certifies an absent target as available.

## Existing Transport Matters reuse seams

No new catalog or persistence model is needed.

- `api/src/transport_matters/harnesses/state_refresh.py:_seed_target_snapshot()` explicitly identifies itself as the temporary hand authored authority and says a future enumeration probe replaces this seam.
- `api/src/transport_matters/harnesses/probes/codex.py` already owns the Codex command plus pure parser and revision pattern for `codex login status`.
- `api/src/transport_matters/harnesses/probes/runner.py` already owns connection scoped environment selection, timeout, subprocess capture, and failure handling.
- `api/src/transport_matters/harnesses/probes/targets.py:build_target_observation()` already converts sanitized model facts into `LocalTargetObservation`.
- `ExecutorEvidenceStore.record_target_snapshot()` already owns atomic snapshots and omission retirement for complete results.

The generic auth runner is typed specifically to `AuthenticationEvidence`, so refactor its subprocess capture seam for reuse. Keep authentication and target result models separate.

## Recommended probe contract

Use a Codex target adapter beside the existing auth adapter.

```text
source:
  remote_account | bundled_binary | failed

command:
  primary  = (<resolved binary>, "debug", "models")
  bundled  = (<resolved binary>, "debug", "models", "--bundled")

parse:
  strict ModelsResponse JSON
  unique nonempty slug
  visibility, supported_in_api, integer priority
  supported_reasoning_levels[].effort as ordered unique values
  default_reasoning_level absent or contained in the supported set
  retain only sanitized model ID, efforts, default, and source metadata

revision:
  probe_revision = "codex-target-catalog-r1"
  observation_adapter_revision = next Codex observation revision
  bind evidence to executable path, normalized version, connection revision,
  command variant, source, raw evidence digest, cache client_version, ETag,
  fetched_at, and parser revision
```

Execution shape:

1. Run under the same connection scoped environment as `codex login status`.
2. Read the normalized executable version first.
3. Run `debug models`. It already avoids a request when a fresh matching cache exists.
4. Validate remote provenance with the version matched fresh cache rules above.
5. Emit `completeness="complete"` only for a proven `remote_account` result on the authenticated connection.
6. If the command yields only bundled evidence, emit `completeness="partial"`. It establishes positive binary metadata and cannot establish account level absence.
7. On command, JSON, schema, provenance, timeout, or version failure, record probe failure and preserve the prior complete target snapshot.
8. Feed successful rows through `build_target_observation()` and the existing atomic `record_target_snapshot()`.
9. Remove `_seed_target_snapshot()` and the hand authored release target path once the probe owns runtime availability. Keep certification data for tested launch edges, separate from what the installed account currently offers.

This shape mirrors the authentication probe while respecting the model command's larger JSON output and its silent fallback behavior.
