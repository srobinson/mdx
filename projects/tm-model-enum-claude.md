# Claude Code model enumeration scout

Date: 2026-07-19

Repository state inspected: `main` at `d25132397e2bfe2910701a278096ff540b32b0fa`

## Conclusion

Trusted path: **yes**. Anthropic's documented `GET /v1/models` endpoint is the authoritative, noninteractive provider inventory for the exact credential Claude Code uses. Its response includes each available native model ID and a structured `capabilities.effort` object with support flags for `low`, `medium`, `high`, `xhigh`, and `max`. The [Models API documentation](https://platform.claude.com/docs/en/api/models/list) says the response determines which models are available for API use. The [models overview](https://platform.claude.com/docs/en/about-claude/models/overview) confirms that the response includes capability and token limit metadata.

The installed Claude Code CLI has no supported `models --json` or equivalent command. `claude doctor` is noninteractive and reports the installed version, commit, platform, and path, but no model catalog. `/model` remains interactive. Therefore the production probe should call the official endpoint with the same connection credential. Scraping the executable should remain verification evidence, never the production parser.

The live probe disproves two assumptions in `compatibility_releases_v1.json`:

1. The current credential exposes **nine** models, while the catalog contains four.
2. Claude exposes effort levels on seven of those nine models. The three latest effort capable models each accept all five levels.

## Trusted live result

The installed executable reports:

```text
claude auth status --json
{
  "loggedIn": true,
  "authMethod": "oauth_token",
  "apiProvider": "firstParty"
}
```

Using that same `CLAUDE_CODE_OAUTH_TOKEN` as a bearer token, this request returned HTTP 200 with `has_more: false`:

```text
GET https://api.anthropic.com/v1/models?limit=1000
Authorization: Bearer <the connection token>
anthropic-version: 2023-06-01
```

The response schema observed on 2026-07-19 was:

```text
top level: data, first_id, has_more, last_id
model: capabilities, created_at, display_name, id,
       max_input_tokens, max_tokens, type
effort: supported, low, medium, high, xhigh, max
```

Exact result for this Claude Code credential:

| Display name | Native model ID | Accepted effort levels |
| --- | --- | --- |
| Claude Sonnet 5 | `claude-sonnet-5` | `low`, `medium`, `high`, `xhigh`, `max` |
| Claude Fable 5 | `claude-fable-5` | `low`, `medium`, `high`, `xhigh`, `max` |
| Claude Opus 4.8 | `claude-opus-4-8` | `low`, `medium`, `high`, `xhigh`, `max` |
| Claude Opus 4.7 | `claude-opus-4-7` | `low`, `medium`, `high`, `xhigh`, `max` |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | `low`, `medium`, `high`, `max` |
| Claude Opus 4.6 | `claude-opus-4-6` | `low`, `medium`, `high`, `max` |
| Claude Opus 4.5 | `claude-opus-4-5-20251101` | `low`, `medium`, `high` |
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | none |
| Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | none |

This matches Anthropic's [effort documentation](https://platform.claude.com/docs/en/build-with-claude/effort). That page documents all five levels, and explicitly limits `xhigh` and `max` by model. It also says `ultracode` is a Claude Code mode built on `xhigh`, not an additional API effort value.

The endpoint does not publish a Claude Code default effort. Keep `default_effort: null` unless the product intentionally snapshots a separately documented CLI default. Omitted effort allows Claude Code to apply its own version and account specific default.

## Installed CLI and npm package grounding

`/Users/alphab/.local/bin/claude` resolves to:

```text
/Users/alphab/.local/share/claude/versions/2.1.214
```

Verified identity:

```text
version:    2.1.214
commit:     e158e55a79995c80ed463a5d2de322bc0ac2f711
build time: 2026-07-17T23:24:50Z
platform:   darwin-arm64
sha256:     59796dd18e9d77f1256f367db6d28ce4bd9cd5968e402ad3a327aac36abc6dec
install:    native
```

The current top level npm package is a wrapper. Its `package.json` declares optional platform packages, `cli-wrapper.cjs::PLATFORMS` resolves the platform package, and `install.cjs::placeBinary` places its native executable at the package bin path. The official [`@anthropic-ai/claude-code-darwin-arm64@2.1.214` tarball](https://registry.npmjs.org/@anthropic-ai/claude-code-darwin-arm64/-/claude-code-darwin-arm64-2.1.214.tgz) contains `package/claude`. Streaming that file directly from the registry produced the same SHA256 as the installed native executable. The installed artifact and the npm platform artifact are byte identical.

The native executable embeds static model descriptors and capability recognition. Read only `strings` inspection confirms:

* `claude-haiku-4-5` maps to first party wire ID `claude-haiku-4-5-20251001`.
* `claude-opus-4-5` maps to `claude-opus-4-5-20251101`.
* `claude-sonnet-4-5` maps to `claude-sonnet-4-5-20250929`.
* Dateless 4.6 and later IDs are native pinned IDs.
* The binary recognizes the `effort`, `xhigh_effort`, and `max_effort` capabilities and the same per model exclusions returned by the Models API.
* `claude --help` accepts `--effort low|medium|high|xhigh|max` and accepts model aliases or full model names.

There is no exported model JSON or stable source symbol in the native package. A production `strings` parser would depend on private binary layout and minified implementation details. It would be less trustworthy than the catalog it replaced.

## Static data and server data

Claude Code uses a mixed model:

* Static package data supplies built in aliases, display rows, provider ID mappings, legacy handling, and capability recognition.
* Anthropic's public Models API supplies live provider availability and structured capabilities for the credential.
* The first party CLI also fetches private startup data from `/api/claude_cli/bootstrap`. The installed binary validates fields including `model_access`, `additional_model_options`, and `org_model_default`, then caches projections in `~/.claude.json` as `modelAccessCache`, `additionalModelOptionsCache`, and `orgModelDefaultCache`.
* Managed `availableModels`, `modelOverrides`, family environment pins, and `ANTHROPIC_CUSTOM_MODEL_OPTION` can further filter or remap the CLI surface. The [Claude Code model configuration documentation](https://code.claude.com/docs/en/model-config) describes those controls and the capability override vocabulary.
* `/v1/models` gateway discovery inside Claude Code is separately gated by `CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY`. That branch concerns a custom gateway. Direct first party startup uses the bootstrap path.

Current local state has no `availableModels`, `modelOverrides`, or model environment pin. `modelAccessCache` is empty. `additionalModelOptionsCache` contains `claude-fable-5[1m]`; Claude Code 2.1.173 and later normalizes that suffix because Fable already has a native 1M context window, so this is not a distinct model target.

For an exact CLI launch surface, intersect the Models API response with private bootstrap restrictions and managed local policy. Apply provider overrides after that intersection. The Models API result alone is already the authoritative native inventory and effort capability source.

## Diff against `compatibility_releases_v1.json`

Current release: `claude-2.1.211-r2`, target catalog revision `claude-targets-r1`.

| Catalog target | Finding | Required correction |
| --- | --- | --- |
| `claude-opus-4-8` | Native ID correct. Efforts incorrectly empty. | Set accepted efforts to all five levels. |
| `claude-fable-5` | Native ID correct. Efforts incorrectly empty. | Set accepted efforts to all five levels. |
| `claude-sonnet-5` | Native ID correct. Efforts incorrectly empty. | Set accepted efforts to all five levels. |
| `claude-haiku-4-5` | User facing alias is valid. Native wire ID is wrong. No effort support is correct. | Keep the alias as `model_id`; change `native_model_id` to `claude-haiku-4-5-20251001`. |

Missing targets returned for the exact credential:

| Suggested model ID | Native model ID | Accepted effort levels |
| --- | --- | --- |
| `claude-opus-4-7` | `claude-opus-4-7` | `low`, `medium`, `high`, `xhigh`, `max` |
| `claude-sonnet-4-6` | `claude-sonnet-4-6` | `low`, `medium`, `high`, `max` |
| `claude-opus-4-6` | `claude-opus-4-6` | `low`, `medium`, `high`, `max` |
| `claude-opus-4-5` | `claude-opus-4-5-20251101` | `low`, `medium`, `high` |
| `claude-sonnet-4-5` | `claude-sonnet-4-5-20250929` | none |

No catalog target is extra relative to the live provider inventory. The catalog has four real models, one wrong native ID, three wrong effort sets, and five omissions.

The latest public model comparison still contains the same four promoted families already present in the catalog: Fable 5, Opus 4.8, Sonnet 5, and Haiku 4.5. The five omissions are currently available previous versions. If the product intends a promoted only catalog, the four family set is complete. If the contract means every model the installed CLI can launch with the current credential, the required set is nine. The task brief asks for exact runtime support, so nine is the applicable answer.

## Repository reuse map

No model enumeration adapter exists today.

Existing seams to reuse:

* `transport_matters.counting.relevant_auth_headers` already extracts only `authorization`, `x-api-key`, `anthropic-version`, and `anthropic-beta` from captured Claude traffic.
* `transport_matters.counting.set_recent_auth` and `get_recent_auth` retain the current connection scoped authorization in memory without persistence.
* `transport_matters.addon_runtime._build_capture_primitives` already owns the shared `httpx.AsyncClient` used for authoritative Anthropic calls.
* `transport_matters.harnesses.probes.targets.build_target_observation` owns the sanitized target observation shape.
* `EvidenceWriter.record_target_snapshot` owns complete snapshot replacement semantics.
* `state_refresh._seed_target_snapshot` is the exact replacement seam. Its docstring already says a future enumeration probe replaces certified catalog seeding without changing the store contract.

The current addon filters non message paths in `addon_handlers.handle_http_request`, so it passes `/api/claude_cli/bootstrap` through without observing its response. The public Models API probe avoids parsing this private response. Bootstrap restrictions still need a separate policy input if exact picker parity is required.

## Recommended probe contract

Use a new target catalog adapter parallel to the authentication adapter. Keep command construction and parsing pure, and execute through the existing connection scoped environment and HTTP ownership.

```text
source
  anthropic_models_api

request
  GET /v1/models?limit=1000
  same base URL and sanitized auth headers as the connection
  anthropic-version inherited from the captured request, or 2023-06-01
  follow pagination until has_more is false

parse
  validate the full response envelope
  require type == "model"
  native_model_id = id
  accepted_efforts = ordered levels whose supported flag is true
  order = low, medium, high, xhigh, max
  completeness = complete only after every page validates
  retain no credential and no raw response body
  digest the sanitized response for evidence

revision
  claude-models-api-r1
  record harness version, executable SHA, parser revision,
  anthropic-version, observed_at, and sanitized response digest
```

Failure behavior should follow the existing observation contract:

* HTTP, authentication, pagination, or schema failure produces `failed` or `partial` evidence.
* A failed or partial probe never infers absence.
* A complete response can establish additions and removals for that credential.
* Managed policy failure must fail closed for launch selection, while preserving the last known provider inventory.

For native keychain credentials, Transport Matters may not possess authorization before the first captured Claude request. Run the Models API probe immediately after the first request supplies connection scoped auth. Before then, serve the last complete snapshot and label freshness honestly. A fresh installation with no captured auth cannot claim complete live enumeration without either a supported CLI export or a credential handoff from Claude Code.

## Exact noninteractive verification commands

Installed artifact:

```bash
TM_CLAUDE_BIN=/Users/alphab/.local/bin/claude
TM_CLAUDE_REAL=$(realpath "$TM_CLAUDE_BIN")
"$TM_CLAUDE_BIN" --version
"$TM_CLAUDE_BIN" doctor
shasum -a 256 "$TM_CLAUDE_REAL"
```

Live model probe, with no token printed:

```bash
node --input-type=module - <<'JS'
const token = process.env.CLAUDE_CODE_OAUTH_TOKEN;
const levels = ["low", "medium", "high", "xhigh", "max"];
const response = await fetch("https://api.anthropic.com/v1/models?limit=1000", {
  headers: {
    authorization: `Bearer ${token}`,
    "anthropic-version": "2023-06-01",
  },
});
if (!response.ok) throw new Error(`models probe: HTTP ${response.status}`);
const body = await response.json();
if (body.has_more) throw new Error("models probe: pagination required");
console.log(JSON.stringify(body.data.map(model => ({
  native_model_id: model.id,
  display_name: model.display_name,
  accepted_efforts: levels.filter(
    level => model.capabilities?.effort?.[level]?.supported === true,
  ),
})), null, 2));
JS
```

This one off command assumes the current environment token. Production must use the connection scoped headers already owned by Transport Matters and must implement pagination.

## Recommendation

Replace hand authored Claude target and effort facts with a Models API derived snapshot. Keep compatibility publication responsible for freezing a reviewed source snapshot, or amend the current contract so the complete live observation becomes launch authority. Do not scrape the npm binary for production data. Retain installed binary inspection as a version matched cross check that Claude Code recognizes every returned ID and effort capability.
