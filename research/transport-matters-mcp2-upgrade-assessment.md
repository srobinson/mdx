---
title: Transport Matters MCP SDK 1.28.1 to 2.1.1 Upgrade Assessment
type: research
tags: [transport-matters, mcp, sdk-migration, mcp2, fastmcp, mcpserver, tools-list, sequencing]
summary: The mcp 2.1.1 migration is 7 production files and one semantic trap, resolves cleanly on Python 3.14, and buys nothing for a filtered tool catalog because list_tools() still takes no auth argument in 2.x; filter first on 1.28.1, upgrade second on its own merits.
status: active
source: codebase-analyst
confidence: high
created: 2026-09-02
updated: 2026-09-02
---

# Transport Matters MCP 2.x Upgrade Assessment

Synthesis of three prior investigations (`mcp2-code-impact.md`,
`mcp2-compatibility.md`, `mcp-ground-upstream.md`, plus `mcp2-sequencing.md`)
against the current tree at `8a55fb41` and the official
`modelcontextprotocol/python-sdk` v2 migration guide.

Where the inputs disagreed, this document resolves the conflict against source.
Section 8 lists every correction.

---

## Executive Summary

**Recommendation: filter first, upgrade second. The two are independent, and the
upgrade is not a prerequisite for anything the filtered catalog needs.**

The decisive fact is verifiable in the 2.1.1 wheel:
`MCPServer.list_tools()` (`mcp/server/mcpserver/server.py:501`) takes no request
and no auth argument, exactly like `FastMCP.list_tools()` in 1.28.1. Both are
called by the protocol handler through `self`, so a subclass override works in
both. **MCP 2.x sells no filtering API.** Everything the filtered catalog needs
already exists on the installed SDK, and the override written against `FastMCP`
ports to `MCPServer` with one import change, because the method signature is
byte-identical.

The migration itself is genuinely cheap and low risk: 7 production files, one
real semantic trap, and a dependency set that resolves on Python 3.14 with a
two-package delta. It is worth doing. It is not worth doing *first*, and it is
worth doing on its own schedule rather than as a feature gate.

| Question | Answer |
| --- | --- |
| Upgrade now or filter first? | **Filter first.** Sequence B from `mcp2-sequencing.md`. |
| Does the upgrade unblock filtering? | **No.** `list_tools()` has no auth hook in either version. |
| Does filter-first create rework? | **Near zero.** The override is signature-identical across versions. |
| Is the upgrade risky? | **Low.** Every break is loud except one. |
| Client breakage? | **None expected.** All three clients keep a supported path on the same URL. |
| Estimated slices | **3** (filter) then **2** (upgrade). |

---

## 1. What the upgrade actually is

### 1.1 Production surface (7 files)

Only four production modules import `mcp`.

| # | File | Change | Class |
| --- | --- | --- | --- |
| 1 | `api/pyproject.toml:47` | `"mcp>=1.28,<2"` → `"mcp>=2.1,<3"` | mechanical |
| 2 | `api/uv.lock` | `uv lock` | mechanical |
| 3 | `api/src/transport_matters/api/v1/controlplane_mcp.py` | `FastMCP` → `MCPServer`; delete `FastMCPSettings.model_rebuild()`; remove three transport kwargs from the constructor; add `version=` | mixed |
| 4 | `api/src/transport_matters/main.py` | move three transport kwargs onto `streamable_http_app(...)` | **semantic** |
| 5 | `api/src/transport_matters/api/v1/mcp_tooling.py` | `structuredContent=` → `structured_content=`, `isError=` → `is_error=` | mechanical |
| 6 | `api/src/transport_matters/api/v1/space_mcp.py` | TYPE_CHECKING import + two annotations | mechanical |
| 7 | `api/src/transport_matters/api/v1/browsing_mcp.py` | same | mechanical |

`main.py` imports no `mcp` symbol. It consumes `create_control_plane_mcp`,
`ControlPlaneMcpAuthApp`, and `ControlPlaneMcpExactPathApp`.

### 1.2 The one semantic trap

`FastMCP(stateless_http=True, json_response=True, streamable_http_path="/")`
moves to the app builder. The 2.x signature
(`mcp/server/mcpserver/server.py:1264`) is keyword-only with different defaults:

```python
streamable_http_path: str = "/mcp"   # TM needs "/"
json_response: bool = False          # TM needs True
stateless_http: bool = False         # TM needs True
```

Leaving them on the constructor raises `TypeError` (loud). **Omitting them at
the new call site raises nothing and silently changes transport behaviour.**
That is the only silent failure in the whole migration.

`streamable_http_app()` on `MCPServer` forwards `auth=self.settings.auth` and
`token_verifier=self._token_verifier` from the constructor
(`server.py:1286-1288`), so TM's auth wiring stays exactly where it is.

**Cohesion note.** `main.py:600-616` is transport wiring; the three kwargs are
transport policy that belongs beside server construction. A small
`control_plane_http_app(mcp)` helper in `controlplane_mcp.py` keeps the policy
with the server and reduces `main.py` to a one-symbol change. Worth taking: it
also gives the one silent failure a single owning site.

### 1.3 Symbol-level fate

| 1.28.1 | 2.1.1 |
| --- | --- |
| `mcp.server.fastmcp.FastMCP` | removed; renamed `mcp.server.mcpserver.MCPServer`. Stub module raises with a migration URL |
| `mcp.server.fastmcp.server.Settings` | module removed. TM's 3.14 `model_rebuild()` workaround is obsolete: delete, do not port |
| `mcp.types.CallToolResult` | survives. Fields snake_case with `to_camel` aliases and `populate_by_name=True`. camelCase ctor kwargs still parse; camelCase **attribute reads raise `AttributeError`** |
| `mcp.types.TextContent` | unchanged |
| `TokenVerifier`, `AccessToken`, `AuthSettings`, `get_access_token` | **unchanged, and officially blessed.** The migration guide's "Unchanged auth surfaces" section names `AuthContextMiddleware`/`get_access_token` explicitly |
| `mcp.session_manager` / `.run()` | unchanged public property and method |
| `@mcp.tool()` | unchanged shape; new optional kwargs TM does not pass |
| `Annotated[CallToolResult, McpToolOutput[...]]` | preserved verbatim; 2.x `func_metadata` has identical dispatch |
| `streamable_http_client` | survives; requires an `httpx2.AsyncClient`, and yields a **2-tuple** (session-id callback gone) |
| `list_tools()` | **unchanged signature: no auth argument.** See §3 |

### 1.4 Dependency and lock impact (resolution proven)

`uv pip compile` against TM's exact runtime dependency set with `mcp>=2.1,<3`
on Python 3.14 resolves with no solve failure.

The true lock delta is **two new packages and one removal**:

| Package | Delta |
| --- | --- |
| `mcp` | 1.28.1 → 2.1.1 |
| `mcp-types` | **new**, exact-pinned `==2.1.1` |
| `opentelemetry-api` | **new**, `>=1.28.0` (API only, no exporter; spans are no-ops) |
| `httpx-sse` | **drops** (required only by mcp 1.x) |
| `httpx2`, `httpcore2`, `truststore` | already in the lock from the dev group; promote to runtime |
| `jsonschema`, `pyjwt[crypto]` | already required by 1.28.1; unchanged |
| `httpx` 0.28.1 | stays, via TM direct + fastapi; mcp no longer an edge |
| `pydantic`, `starlette`, `anyio`, `sse-starlette` | floors already satisfied by the current lock |

`httpx` and `httpx2` coexist under distinct import names. TM's own runtime
client is unaffected.

### 1.5 Behavioural deltas shipped by the bump

1. **Protocol ceiling rises to 2026-07-28** for modern clients. Handshake
   clients keep negotiating 2024-11-05..2025-11-25 exactly as today.
2. **`serverInfo.version` becomes `""`.** In 1.x an unversioned server reported
   the installed `mcp` package version; 2.x reports empty. TM passes no
   `version` today, so it currently misreports "1.28.1" as its own version.
   Pass `version=` at migration: it turns a latent misreport into correct
   identity for the same one-line cost.
3. **4 MiB Streamable HTTP body limit, new in 2.x** (`DEFAULT_MAX_REQUEST_BODY_SIZE`,
   `mcp/server/transport_security.py:15`). 1.28.1 has no such constant.
   Exceeding it returns `413` before JSON parsing. TM's largest tool argument is
   `prompt` text, well under. Accept the default; add one boundary test.
4. **`resultType: "complete"` on every result.** Older peers ignore it. TM
   asserts specific fields, not whole payloads.
5. **Error results skip output-schema validation.** Neutral for TM's
   dual-optional envelope.
6. **Lifespan enters once at manager startup** rather than per request under
   `stateless_http=True`. TM's lifespan is process-wide state; unaffected.
7. **Extra fields on protocol models are no longer preserved.** This kills the
   "stuff `ttlMs`/`cacheScope` on as extras" forward-compatibility idea. Do not
   invest in it on 1.x either.
8. **Crash messages become opaque.** Unreachable in practice: TM wraps its own
   failures in `invoke_control_plane` before the SDK path fires.

### 1.6 Non-issues, resolved

- **DNS rebinding / 421.** `mcp-ground-upstream.md` open question 4 asked how TM
  survives `TransportSecurityMiddleware`. Both versions auto-enable the same
  localhost allowlist (`127.0.0.1:*`, `localhost:*`, `[::1]:*`) when `host`
  defaults to `127.0.0.1`: 1.28.1 in `FastMCP.__init__`, 2.1.1 in
  `streamable_http_app`. TM rides it today and keeps riding it. Leave `host` at
  its default. **Closed.**
- **`get_access_token` publicness.** `mcp2-code-impact.md` held this as a
  residual risk. The official migration guide lists
  `AuthContextMiddleware`/`get_access_token` under "Unchanged auth surfaces".
  **Closed.**
- **Python 3.14 × mcp 2.x.** `mcp2-sequencing.md` held this as an open gate. The
  `mcp2-code-impact.md` probe constructed `MCPServer` on 3.14 with no
  `model_rebuild()`, and the dependency set resolves for 3.14. Residual risk is
  the full in-tree suite, not the interpreter.

---

## 2. Test surface

93 model-attribute occurrences across 7 files, of which 92 are the camelCase
rename and 1 is a serialization change.

| File | Change | Count |
| --- | --- | --- |
| `test_controlplane_skins.py` | `_mcp_session` fixture: `httpx2` client, 2-tuple unpack; attr renames | 25 |
| `test_browsing_skins.py` | attr renames | 23 |
| `test_space_mcp.py` | attr renames | 21 |
| `test_controlplane_mcp_inventory.py` | attr renames (adapter-direct) | 14 |
| `test_agent_catalog_skins.py` | attr renames | 4 |
| `test_controlplane_action_skins.py` | attr renames (3) **+ `by_alias=True`** (1) | 4 |

All six live in `api/src/transport_matters/api/v1/` (colocated, not `api/tests/`).
`_mcp_session` is defined in `test_controlplane_skins.py:231` and shared by five
modules.

### 2.1 The serialization change both prior docs mishandled

`test_controlplane_action_skins.py:90-92`:

```python
tools = {
    tool.name: tool.model_dump(mode="json")
    for tool in await app.state.control_plane_mcp.list_tools()
}
```

It then asserts on `tool["outputSchema"]` and `tool["inputSchema"]`, the **wire**
key names. In 1.x that worked because the model fields *were* camelCase. In 2.x,
`MCPModel` sets `alias_generator=to_camel, populate_by_name=True` and **not**
`serialize_by_alias`, so this dump emits `input_schema` / `output_schema`.

The fix is `model_dump(mode="json", by_alias=True)`, which is also more correct
than a rename: the test's own comment says strict clients reject a top-level
`anyOf` in `outputSchema`, so it is asserting the **wire** contract and should
serialize as the wire. The migration guide flags exactly this pattern:

> In v2 the same call emits snake_case keys (`input_schema`, not `inputSchema`),
> which peers and other MCP implementations will not recognize. No error is
> raised; the output is silently in the wrong shape.

Here it does raise (`KeyError`), so it is loud. But this is the test that *is*
the 34-tool agent contract, and it must keep asserting wire names.

### 2.2 Not touched

`test_controlplane_skin_structure.py` (AST-only), `test_harnesses.py` (plain
REST), `test_controlplane_auth.py` (TM-internal), `test_main_lifespan_*` (fakes
`session_manager` via `SimpleNamespace`).

---

## 3. Why the upgrade does not unblock the filtered catalog

This is the load-bearing finding, and it is checkable in one place.

```python
# mcp/server/mcpserver/server.py:501  (2.1.1)
async def list_tools(self) -> list[MCPTool]:
    tools = self._tool_manager.list_tools()
    return [MCPTool(...) for info in tools]

# mcp/server/mcpserver/server.py:417
async def _handle_list_tools(...):
    return ListToolsResult(tools=await self.list_tools())
```

No request. No auth. No principal. Identical in shape to
`mcp/server/fastmcp/server.py:315` on 1.28.1. Filtering requires **subclassing
and overriding** in both versions, and in both versions the override is reached
because `_handle_list_tools` dispatches through `self`.

The override therefore costs the same to write on either SDK, and porting it
across the migration is an import line. `mcp2-sequencing.md` scored this as
sequence B's only duplicate work; it is closer to zero than that scorecard
allowed, which strengthens B rather than weakening it.

What 2.x *does* add for filtering is one thing: native `cache_hints` with
`cacheScope: "private"`, which the 2026-07-28 caching model requires for a list
that varies per credential. That matters only when a real client both speaks
2026-07-28 and caches list results. None do today:

| Client | Today | After the upgrade |
| --- | --- | --- |
| Claude Code 2.1.258 | legacy handshake unless a rollout flag selects v2 | either path; same URL |
| Codex CLI 0.152.1 | legacy; `mcp_2026_07_28` present but disabled | unchanged until the flag ships |
| Grok CLI 1.0.13 | legacy; bundled `rmcp` 2.1.0 sets `2025-11-25` as latest | unchanged |

Seeded client configs carry a URL and a bearer and nothing else
(`api/src/transport_matters/cli/{claude,codex,grok}_home.py`). No protocol pin
exists to break.

Filtering on 1.28.1 is legal by silence at 2025-11-25, explicitly blessed at
2026-07-28, and was proven working by probe against the installed SDK. The one
constraint to honour now so nothing is undone later: **the filter must be a pure
function of the presented credential**, never of connection identity or prior
calls on the connection.

---

## 4. Recommendation

**Filter first. Upgrade second, on its own merits, unbundled from any feature.**

Grounds, in order of weight:

1. **The upgrade purchases no filtering capability.** §3. This alone removes the
   only architectural argument for upgrade-first.
2. **Filter-first has near-zero rework cost.** Signature-identical override.
3. **Time to a useful result.** A granted observer stops downloading 20
   director-only schemas after slice 2 of the filter work. Upgrade-first delays
   that behind a migration that delivers nothing user-visible.
4. **Failure isolation.** Bundling means a filter bug and an SDK port bug are
   indistinguishable in the same red suite, and a revert restores the
   34-tool observer dump.
5. **Reversibility.** Deleting an override restores prior behaviour. Rolling
   back a pin change means a second port.

**What would flip this:** a real client landing on 2026-07-28 *and* caching
`tools/list` across principals before the filter ships. That would make
`cacheScope: "private"` load-bearing and put the upgrade on the critical path.
Watch the Codex `mcp_2026_07_28` flag and Claude's v2 rollout. Nothing else
flips it.

**What this refuses:**

- Upgrading to obtain a filter hook. It does not exist in 2.1.1.
- Treating per-runtime subsets as a prerequisite for role-filtered `tools/list`.
  Role is the subset TM already persists; per-runtime needs a `capabilities.json`
  producer contract and a grant-row change, which is a different program.
- Multiple `/mcp` mounts for namespacing. Provisioning is one URL; the bearer is
  the audience.
- Emitting `ttlMs`/`cacheScope` as extras on 1.x. 2.x drops unknown fields.

---

## 5. PR slices

### Filter track (ships first, 3 slices)

Per `mcp2-sequencing.md`, unchanged by this synthesis except the catalog size.

1. **Freeze the catalog.** One ordered module-level catalog of the 34 names with
   `min_role ∈ {observer, director}`. Source of truth for
   `test_mcp_tool_schemas_are_the_agent_contract`. No behaviour change.
   Registration order (core, space, browsing) satisfies the 2026-07-28
   deterministic-order SHOULD for free.
2. **Subclass and override.** `list_tools` reads `get_access_token()`; full set
   when no principal (in-process/test path), role projection when present.
   Tools stay registered; `require_director` unchanged.
3. **Prove the boundary.** An observer calling a director-only name by string
   still hits the call-time check before side effects.

### Upgrade track (ships second, 2 slices)

**Slice U1, mechanical port.** Pin, lock, four import/annotation renames,
`FastMCPSettings.model_rebuild()` deletion, `mcp_tooling` snake_case, 92
test attribute renames, `by_alias=True` at
`test_controlplane_action_skins.py:91`, `_mcp_session` onto `httpx2` + 2-tuple.
Every break here is loud.

**Slice U2, transport relocation and identity.** The
`control_plane_http_app(mcp)` helper carrying
`streamable_http_path="/"`, `json_response=True`, `stateless_http=True`;
`version=` on the constructor; one 4 MiB boundary test. This is the review-
attention slice and it is deliberately small.

Splitting U1/U2 is what makes the one silent failure reviewable in isolation.
Bundling them is acceptable if the reviewer is told where to look.

Deferred, each with its own GO: native `cache_hints` with `cacheScope:"private"`
once the filter is live on 2.x; per-runtime subsets; `listChanged` publication
(needs subscriber selection, revocation, and shutdown design first, and the SDK
bus has no replay); protocol observability.

---

## 6. Gates

Ordered, runnable from repo root.

```bash
# G1: dependency flip resolves and syncs
cd api && uv lock && uv sync --all-extras --dev

# G2: no v1 import survives
! grep -rn "mcp.server.fastmcp" api/src --include="*.py"

# G3: no camelCase SDK field spelling survives
! grep -rn "structuredContent\|isError" api/src --include="*.py"

# G4: MCP skin suite: fixture, auth, envelopes, inventory, e2e session
cd api && uv run python -m pytest -n auto --dist loadfile src/transport_matters/api/v1 -q

# G5: repo gates, verbatim recipes
just check && just test
```

G4 is the real end-to-end gate: it runs initialize → tools/list → tools/call
through the actual auth stack over ASGI, which is precisely the surface the
migration touches, and a wrong transport mode behaves differently under the
fixture. G5 is the merge bar.

Add one live smoke after G5: one seeded harness home (Claude or Codex) listing
tools against the running preview backend on the 2025 handshake. That is the
only gate that proves a real client, and no in-process test substitutes for it.

**Missing gate to add during the filter track:** G3 has no counterpart for the
silent `model_dump` shape. Add a wire-shape assertion (`"inputSchema" in dump`)
rather than relying on a `KeyError` to surface it.

---

## 7. Risk

| Risk | Level | Basis |
| --- | --- | --- |
| Client breakage | **Low** | All three clients keep a legacy path on the same URL; no protocol pin in any seeded config |
| Silent transport misconfiguration | **Medium, contained** | The one non-loud failure; contained by U2 being a separate small slice and by G4 |
| Migration implementation | **Low** | 7 production files; TM's full shape reproduced working on 2.1.1 by probe; every other break raises |
| Dependency resolution | **Low** | Resolution proven on 3.14; delta is two packages |
| Supply chain | **Medium-low** | `httpx2` and `opentelemetry-api` are new runtime surface; OTel is API-only and inert without an exporter |
| Authorization | **Low** | Per-request resolution and call-time checks intact; auth surface officially unchanged |
| Operational | **Low** | 4 MiB limit and an idle `subscriptions/listen` listener need coverage, not design |
| Audit completeness | **Medium, pre-existing** | Existing gaps remain; SDK telemetry does not close them and must never be presented as action audit |

No data, schema, or persistence surface is touched. Blast radius is the MCP skin
and its tests.

---

## 8. Corrections to the input documents

Recorded because these paths and counts will be copied into a plan.

| Claim | Source | Correct |
| --- | --- | --- |
| `api/src/transport_matters/api/main.py:377-491, 600-617` | compatibility | `api/src/transport_matters/main.py`; no `api/main.py` exists |
| `ControlPlaneExactPathApp` | compatibility | `ControlPlaneMcpExactPathApp` (`controlplane_mcp.py:191`) |
| Tests at `api/tests/test_controlplane_skins.py` | compatibility | colocated at `api/src/transport_matters/api/v1/` |
| Harness homes at `api/src/transport_matters/harnesses/*_home.py` | compatibility | `api/src/transport_matters/cli/*_home.py` |
| `by_alias` fix at `test_controlplane_skins.py:91` | compatibility | `test_controlplane_action_skins.py:91` |
| 9 tools in `browsing_mcp.py`; 35 total | code impact | **8**; **34** total (13 + 13 + 8), matching the contract test |
| `test_controlplane_action_skins.py`: "attr renames, 3" | code impact | 3 renames **plus** the `by_alias=True` serialization fix, which that doc missed |
| ~93 / ~96 occurrence edits | both | **92** camelCase occurrences (90 test, 2 production) plus 1 serialization change |
| `httpcore2`, `truststore` arrive with the upgrade | code impact | already in the lock via the httpx2 dev group; they re-scope to runtime |
| `jsonschema`, `pyjwt` unmentioned | both | already required by 1.28.1; no delta |
| `get_access_token` is unblessed private surface | code impact | named under "Unchanged auth surfaces" in the official guide |
| FastMCP defaults `allowed_hosts` empty → 421 everything | ground upstream | 1.28.1 auto-enables the same localhost allowlist as 2.x; open question 4 closed |
| Python 3.14 × mcp 2.x unproven | sequencing | `MCPServer` constructs on 3.14 without `model_rebuild()`; resolution proven |
| `serverInfo.version` unmentioned | both | 1.x reports the SDK version, 2.x reports `""`; pass `version=` |
| 4 MiB limit "a v2 default to accept" | compatibility | it is **new**; 1.28.1 has no body limit at all |

---

## 9. Open questions

1. **Which negotiated version do real harness clients land on?** The SDK defaults
   header-less clients to `2025-03-26`, below the revision that carries
   `outputSchema` and `structuredContent`. TM ships both. Neither track depends
   on the answer, but the live smoke in §6 will produce it, and it should be
   captured when it does.
2. **In-process `list_tools()` with no token returns the full catalog.** That
   keeps the contract test honest. Confirm that is intended before slice 2
   locks it in.
3. **Hidden-name disclosure.** Keeping the `ControlPlaneFailure` envelope on a
   call to a filtered-out name tells a guessing client the tool exists. A
   JSON-RPC unknown-tool error hides it and changes the envelope the twin-skin
   tests pin. Default: keep the envelope; revisit as a security design, not
   inside the filter slices.
4. **`subscriptions/listen` in practice.** 2.x `MCPServer` registers a listen
   handler and advertises tool `listChanged`. TM publishes no changes, so the
   listener idles, but it affects connection counts and auth logs. Whether any
   supported Claude or Codex configuration actually opens it is unmeasured.

---

## 10. Sources

**Repository, read-only**, at `8a55fb41`:
`api/pyproject.toml:41,47,69`, `api/uv.lock`,
`api/src/transport_matters/api/v1/{controlplane_mcp,space_mcp,browsing_mcp,mcp_tooling}.py`,
`api/src/transport_matters/main.py` (`create_app`, `lifespan`),
`api/src/transport_matters/cli/{claude,codex,grok}_home.py`,
the six colocated MCP test modules, `justfile`.

**Installed SDK 1.28.1** (`api/.venv`, Python 3.14.5):
`mcp/server/fastmcp/server.py` (`__init__`, `list_tools`, transport security
auto-allowlist), `mcp/server/lowlevel/server.py` (`pkg_version` fallback),
`mcp/server/transport_security.py`.

**SDK 2.1.1 wheels** (`mcp-2.1.1`, `mcp_types-2.1.1`):
`mcp/server/mcpserver/server.py:154,417,501,1264`,
`mcp/server/lowlevel/server.py:413,538,716`,
`mcp/server/transport_security.py:15`,
`mcp_types/_types.py:45,1411`.

**Official documentation** (fetched 2026-09-02):
[v2 migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md),
sections "Field names changed from camelCase to snake_case", "Unversioned
servers report an empty version", "Transport-specific parameters moved",
"Streamable HTTP request bodies are limited to 4 MiB", "Streamable HTTP:
lifespan now entered once", "Unchanged auth surfaces", "`streamablehttp_client`
removed", "Extra fields on MCP types are no longer preserved".
PyPI: `mcp` latest is 2.1.1; requires-dist for 1.28.1 and 2.1.1.

**Resolution probe**: `uv pip compile` of TM's runtime dependency set with
`mcp>=2.1,<3` on Python 3.14, diffed against `api/uv.lock`.

**Prior investigations**, `/Users/alphab/.mdx/TMP/pstack/01a061b1/`:
`mcp2-code-impact.md`, `mcp2-compatibility.md`, `mcp-ground-upstream.md`,
`mcp2-sequencing.md`.
