# Claude Code OAuth refresh probe

Date: 2026-07-27

Method: static analysis only. No Claude Code command was executed. No OAuth
request was sent. No keychain or credential file was read.

## Result

The production first party OAuth client ID is:

```text
9d1c250a-e61b-44d9-88ed-5944d1962f5e
```

Tag: **READ** from the production OAuth configuration embedded in both inspected
binaries.

The production refresh endpoint is:

```text
https://platform.claude.com/v1/oauth/token
```

Tag: **READ** from `TOKEN_URL` in both inspected binaries.

This corrects the design document. Neither inspected binary uses
`https://claude.ai/v1/oauth/token` as its production `TOKEN_URL`.

## Binaries inspected

Current executable resolution:

```text
/Users/alphab/.local/bin/claude
  -> /Users/alphab/.local/share/claude/versions/2.1.220
```

Current binary:

```text
path:      /Users/alphab/.local/share/claude/versions/2.1.220
version:   2.1.220
build:     2026-07-24T22:17:45Z
git SHA:   4073f59596e272f39393db4f96abc5f4b10eff21
file SHA:  8addc857f3fe64d5a0368af9ee50321b50afb4a6918ba3ef018ab84f5dbbe081
format:    Mach-O 64-bit executable arm64
```

The design document names 2.1.219, so that installed binary was also inspected:

```text
path:      /Users/alphab/.local/share/claude/versions/2.1.219
version:   2.1.219
build:     2026-07-24T03:24:19Z
git SHA:   7006c4c3acac98e554d3997baeda6a7fa4d1ff7c
file SHA:  a8e806faaefac53c7a0f26523d8a45c60dbef3407b14ef990c75765d08febc82
format:    Mach-O 64-bit executable arm64
```

The refresh contract reported below is identical in 2.1.219 and 2.1.220.

## Literal request specification

### Request line and destination

```http
POST /v1/oauth/token HTTP/1.1
Host: platform.claude.com
```

Field tags:

| Element | Value | Confidence |
|---|---|---|
| Method | `POST` | **READ** at the refresh call site |
| URL | `https://platform.claude.com/v1/oauth/token` | **READ** from production `TOKEN_URL` |
| `Host` | `platform.claude.com` | **INFERRED** from the URL and the underlying HTTP transport |

`CLAUDE_CODE_CUSTOM_OAUTH_URL` can replace the base URL with one of a small
approved set. That override is a separate configured mode. The literal above is
the production default.

### Headers

```http
Accept: application/json, text/plain, */*
Content-Type: application/json
User-Agent: axios/1.15.2
Accept-Encoding: gzip, compress, deflate, br
Content-Length: <UTF-8 byte length of the compact JSON body>
```

Field tags:

| Header | Confidence | Evidence |
|---|---|---|
| `Accept: application/json, text/plain, */*` | **READ** | Bundled Axios default |
| `Content-Type: application/json` | **READ** | Set explicitly at the refresh call site |
| `User-Agent: axios/1.15.2` | **READ** | Bundled Axios HTTP adapter sets it when the caller does not |
| `Accept-Encoding: gzip, compress, deflate, br` | **READ** for the adapter expression, **INFERRED** for `br` at runtime | The bundled adapter adds `br` when Brotli decompression is available |
| `Content-Length` | **READ** | Bundled adapter computes the serialized byte length |

The refresh call sets no `anthropic-beta`, `anthropic-version`, `Authorization`,
`x-api-key`, or custom Claude Code user agent header. The only global Axios
request interceptor in the binary configures proxy agents and does not add
headers.

`Host`, connection management, and any proxy authorization are transport or
machine configuration details. No `Connection` value is claimed here because
static analysis does not establish its runtime value.

### JSON body

For the default first party client and default Claude AI scope set, Axios emits
this compact JSON shape:

```json
{"grant_type":"refresh_token","refresh_token":"<ROTATING_REFRESH_TOKEN>","client_id":"9d1c250a-e61b-44d9-88ed-5944d1962f5e","scope":"user:profile user:inference user:sessions:claude_code user:mcp_servers user:file_upload"}
```

Field tags:

| Field | Value or representation | Confidence |
|---|---|---|
| `grant_type` | String literal `refresh_token` | **READ** |
| `refresh_token` | Existing rotating refresh token | **READ** as a required input field; no credential value was accessed |
| `client_id` | `9d1c250a-e61b-44d9-88ed-5944d1962f5e` | **READ** |
| `scope` | One space joined string | **READ** |
| `expires_in` | Optional numeric request field | **READ** as supported, absent from the normal background refresh call |

Encoding is JSON, not form encoding. Axios applies `JSON.stringify` to the
object because the call explicitly sets `Content-Type: application/json`.

`client_id` can come from a caller supplied stored client ID. If none is
supplied, it defaults to the production literal above. The environment variable
`CLAUDE_CODE_OAUTH_CLIENT_ID` can also replace the production default.

## Scope behavior

The refresh request always includes `scope`.

The embedded default scope list, in order, is:

```text
user:profile
user:inference
user:sessions:claude_code
user:mcp_servers
user:file_upload
```

Tag: **READ** from the `CLAUDE_AI_OAUTH_SCOPES` array.

The normal background refresh path behaves as follows:

1. For a default first party credential with no stored custom `clientId`, it
   sends the default list above plus any stored `user:projects:read` and
   `user:projects:write` scopes.
2. If that request fails with `invalid_scope`, it retries with the exact stored
   scope array when that array is nonempty and contains `user:inference`.
3. For a credential with a stored client ID, including the design OAuth path,
   the caller passes its stored scopes.
4. At the refresh helper boundary, a missing or empty scope array falls back to
   the default list above.

All four points are **READ** from the binary.

Whether the server formally requires refresh scopes to match the original grant
is **NOT ESTABLISHED** by static analysis. The binary does not universally
enforce equality. Its first attempt can expand a legacy first party credential
to the current default list, then it falls back to the stored scopes only after
an `invalid_scope` response.

## Literal response specification

The refresh helper consumes this JSON shape:

```text
{
  "access_token": "<NEW_ACCESS_TOKEN>",
  "refresh_token": "<NEW_ROTATED_REFRESH_TOKEN>",
  "expires_in": <NUMBER_OF_SECONDS>,
  "refresh_token_expires_in": <NUMBER_OF_SECONDS, OPTIONAL>,
  "scope": "user:profile user:inference user:sessions:claude_code user:mcp_servers user:file_upload",
  "account": {
    "uuid": "<ACCOUNT_UUID>",
    "email_address": "<EMAIL>"
  },
  "organization": {
    "uuid": "<ORGANIZATION_UUID>"
  }
}
```

The helper expects HTTP status `200`. Tag: **READ** from its explicit status
check.

An eight hour access token would carry `expires_in: 28800`. That duration is
**INFERRED** from the observed lifetime in the design document. The binary does
not hardcode or validate `28800`.

Fields consumed by the binary:

| Wire field | Meaning and conversion | Confidence |
|---|---|---|
| `access_token` | New access token; returned as `accessToken` | **READ** |
| `refresh_token` | New rotating refresh token; returned as `refreshToken` | **READ** |
| `expires_in` | Access token lifetime in seconds | **READ** from multiplication by `1000` |
| `refresh_token_expires_in` | Refresh token lifetime in seconds, when present | **READ** from multiplication by `1000` |
| `scope` | Space separated scope string | **READ** from splitting on spaces |
| `account.uuid` | Optional token account UUID | **READ** |
| `account.email_address` | Optional token account email | **READ** |
| `organization.uuid` | Optional token organization UUID | **READ** |

The client converts access expiry to:

```text
expiresAt = Date.now() + expires_in * 1000
```

`expiresAt` is therefore an absolute Unix epoch timestamp in JavaScript
milliseconds. The wire field is `expires_in`, measured in seconds. There is no
wire field named `expiresAt`.

When `refresh_token_expires_in` is numeric, the client converts it to:

```text
refreshTokenExpiresAt = Date.now() + refresh_token_expires_in * 1000
```

When it is absent on refresh, `refreshTokenExpiresAt` is undefined.

The helper tolerates an omitted `refresh_token` by retaining the old refresh
token in memory. That fallback is **READ** from
`refresh_token: newRefreshToken = oldRefreshToken`. Static analysis cannot
confirm whether the production server ever omits the field. Given rotating
refresh tokens, the broker must require and persist the returned rotated value
before releasing the access token.

The helper tolerates an absent or nonstring `scope` by producing an empty scope
array. The production server's complete response may contain additional fields
that this client ignores. Static analysis establishes the fields consumed by
the binary, not every field the server may return.

`token_type` and `id_token` are **NOT FOUND** in the refresh response handling.
Static analysis cannot establish whether the server returns either field. The
binary does not consume them on this path.

## Fields and artifacts not sent on refresh

The refresh call does not send:

| Item | Confidence |
|---|---|
| `redirect_uri` | **READ** as absent from the refresh object |
| PKCE `code_verifier` or `code_challenge` | **READ** as absent |
| authorization `code` or `state` | **READ** as absent |
| `client_secret` | **READ** as absent |
| client assertion | **READ** as absent |
| DPoP proof | **READ** as absent |
| `anthropic-beta` header | **READ** as absent at the call site and from global interceptors |
| `anthropic-version` header | **READ** as absent at the call site and from global interceptors |

The authorization code exchange elsewhere in the binary does use
`redirect_uri`, `code_verifier`, and `state`. Their absence from the refresh
path is deliberate, not evidence that those concepts are absent from initial
login.

No server side requirement was inferred from a live response. The binary's
request path is direct evidence that the refresh exchange does not require a
redirect URI, PKCE artifact, or client secret for this public client.

## Static searches performed

Representative commands, all read only:

```bash
command -v claude
which -a claude
readlink /Users/alphab/.local/bin/claude
file /Users/alphab/.local/share/claude/versions/2.1.220
codesign -dv --verbose=4 /Users/alphab/.local/share/claude/versions/2.1.220
shasum -a 256 /Users/alphab/.local/share/claude/versions/2.1.219
shasum -a 256 /Users/alphab/.local/share/claude/versions/2.1.220
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'oauth/token|refresh_token|client_id'
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'async function kNe'
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'CLAUDE_AI_OAUTH_SCOPES|TOKEN_URL|CLIENT_ID'
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'function ano|function NWr'
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'axios/|User-Agent|Accept-Encoding'
strings -a /Users/alphab/.local/share/claude/versions/2.1.220 | rg 'Lo.interceptors.request.use'
```

Searches for `client_secret`, `redirect_uri`, `code_verifier`,
`anthropic-beta`, and `anthropic-version` found those symbols in other
authorization and API paths, but none in the refresh function or a global
header interceptor.

## Broker implementation contract

The minimum production request contract established by this probe is:

```text
POST https://platform.claude.com/v1/oauth/token
Content-Type: application/json

grant_type     = "refresh_token"
refresh_token  = owner credential's current refresh token
client_id      = "9d1c250a-e61b-44d9-88ed-5944d1962f5e"
scope          = space joined owner scopes, using the binary's default list when absent
```

The minimum successful response contract is:

```text
access_token              required
refresh_token             required by the broker's rotation invariant
expires_in                seconds
refresh_token_expires_in  optional seconds
scope                     space separated string
```

The broker must convert `expires_in` to an absolute millisecond `expiresAt`
locally and must persist the new `refresh_token` before returning the access
token.
