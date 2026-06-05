---
title: S3 control-plane twin skins (REST + MCP) — adversarial review (Fable)
branch: controlplane-s3-skins @ 1cdc69b
scope: git diff main...controlplane-s3-skins (8 files, +1102/-10)
date: 2026-07-11
process: code-review high effort (8 finder angles, recall-biased verify) + code-hygiene lens
verdict: no blockers, NO AUTH BYPASS; 8 minors + 2 low; self-audit visibly effective; builder trust HIGH
---

# Verdict

No correctness blocker and, decisively for this slice, no auth bypass. The full chain
(bearer → outer ASGI resolve → ContextVar stash → SDK BearerAuthBackend → verify_token →
RequireAuthMiddleware scope gate → AuthContextMiddleware → `_principal()` isinstance
check) was traced end to end against the installed `mcp` 1.28.1 SDK source. Identity is
always server-resolved, never self-declared; the digest binds the stashed principal to
the exact request token; ContextVars are per-task and anyio's `start` copies the request
context into the stateless server task, so no cross-request or stale-token path exists.
Revoked grant dies on the next request on both skins (tested). Eight minors + two lows;
one is live-reachable (F1, error-path disclosure on the MCP skin), the rest are latent,
consistency, or rigor items. Tree pristine at 1cdc69b before and after; review read-only.

# Brief strictness areas — evidence

1. **Skins carry no logic: HOLDS (with a test-rigor gap, F5).** REST routes and MCP
   tools are single-return delegators; params match `ControlPlaneService` signatures
   exactly (names, kw-only, defaults, `ConversationShape` values). The AST test
   `test_route_and_tool_entrypoints_are_branch_free_delegators` enforces it — but only
   on the decorated entrypoints, not the adapter layer beneath (F5), and the adapter
   does mint two taxonomy codes for wiring faults (F3).
2. **/mcp mount ordering: HOLDS.** Exact `/mcp` gets an explicit 307 route ahead of the
   mount (same idiom as the existing `/canvas` bare-path route), both registered before
   `mount_frontend_bundles`. `test_mcp_mount_precedes_and_is_not_shadowed_by_spa`
   asserts both registration order AND live dispatch (POST /mcp → 401 JSON, not SPA
   HTML). The MCP SDK's own client always sets `follow_redirects=True`, so the
   S1-seeded `.../mcp` URL works; cost is one extra loopback round trip per stateless
   call (noted).
3. **Auth on both skins: HOLDS.** With a token verifier and no auth-server provider /
   `resource_server_url=None`, `streamable_http_app()` mounts exactly ONE route,
   wrapped in `RequireAuthMiddleware` with `required_scopes=["controlplane"]` enforced —
   no unauthenticated `.well-known` or OAuth routes exist (verified in SDK source).
   Unauthenticated, non-bearer scheme, malformed, and revoked bearers are all rejected
   401 on both skins (parametrized + revoke tests); resolver outage is a byte-identical
   503 envelope on both skins (tested). The SDK-fit spike risk the scout flagged is
   retired: the binding bearer→run_id→grant→ControlPlanePrincipal is correct, and
   `verify_token` stores only the SHA-256 digest hex in SDK context, never the raw
   bearer (tested).
4. **Consistent identity + error shaping: HOLDS with edges.** Service errors produce
   the identical `{"detail":{"code","message"}}` envelope on both skins (tested,
   including MCP `isError` + structuredContent). Edges: unexpected service exceptions
   leak raw text on the MCP skin (F1, live); REST 422 validation errors
   escape the envelope (F6); the SDK-owned 401 body is OAuth-style
   `{"error":...}` + WWW-Authenticate rather than the REST envelope (noted —
   RFC 6750-conformant, arguably correct for MCP clients); service-absent outage
   diverges across skins (F3, latent).
5. **Schemas, pin, DRY, hygiene: HOLDS.** Tool schemas pinned by test (three tools,
   `shape` enum feed|summary, no principal/workspace_id leakage into the agent
   contract). `mcp>=1.28,<2` matches the `mitmproxy>=12.2,<13` pin idiom.
   `Annotated[CallToolResult, ControlPlaneToolOutput[...]]` is first-class SDK usage
   (func_metadata handles exactly this), not a workaround. No dead code. Files: mcp
   skin 274, routes 88, auth 73, errors 47, tests 476, main.py 479 — all <700. Import
   direction clean (api/v1 → controlplane, never the reverse).

Gates observed directly: pytest 1976 passed (full api suite, Postgres-backed);
`ruff format --check` (494 files), `ruff check`, `mypy` all clean (CI scope src/).

# Findings (ranked)

**F1 (minor, live error-path disclosure) `controlplane_mcp.py` `_McpObserveAdapter._invoke`** —
Catches only `ControlPlaneError`. Any other exception from the service (psycopg/DB
error, TimeoutError, ValueError) propagates into the SDK's tool-call catch-all
(`lowlevel/server.py`: `except Exception as e: return self._make_error_result(str(e))`,
verified in installed source), which returns the RAW exception string to the connected
agent as `isError` TextContent with no structuredContent — internal detail (SQL
fragments, paths) disclosed, and the shared `ControlPlaneFailure` envelope broken. REST
hits FastAPI's opaque 500 for the same failure, so the skins also diverge. Catch
`Exception` in `_invoke`, log with the chain, and return a fixed-message structured
failure. The only live-reachable finding in this review (any DB hiccup during a tool
call triggers it).

**F2 (minor, correctness edge) `controlplane_routes.py` `_ERROR_STATUS[error.code]`** —
Unguarded dict subscript in the exception handler, and no test pins
`set(_ERROR_STATUS) == set(get_args(ControlPlaneErrorCode))`. A sixth code added to the
Literal (the MCP side needs no map — `control_plane_failure` is total) raises KeyError
inside the handler → text/plain 500, envelope lost, while MCP keeps answering
structurally — silent cross-skin divergence at exactly the seam the slice exists to
keep identical. Repo already has the pinning pattern (S2's tier contract test). Add the
exhaustiveness test or a `.get` fallback; `desktop_runtime._DISCOVERY_ERROR_STATUS`
shares the unpinned pattern.

**F3 (minor, altitude/taxonomy) `controlplane_mcp.py` `_service()` / `_principal()`** —
The skin mints domain codes for wiring faults: `delivery_failed` for "service not
mounted on app.state", `forbidden` for "unexpected access-token type". An agent
branching on the documented taxonomy is sent to prompt-delivery/entitlement causes for
what are mount bugs. REST reports the same service-absent outage as 503
`control_plane_unavailable`, so the twins diverge (latent today: service and resolver
are gated on the same session-pool condition and identity 503s first). Give the service
lookup the same shared-seam treatment the diff gave identity
(`resolve_control_plane_bearer`), emitting `control_plane_unavailable` on both skins.

**F4 (minor, simplification + latent 500) `controlplane_mcp.py` `verify_token`** —
The fallback re-resolve branch is production-dead: the outer `ControlPlaneMcpAuthApp`
always stashes a resolution when a bearer is present (both layers strip the same 7-char
prefix from the same header, so digests always match), and with no bearer the SDK 401s
before `verify_token` runs. If the branch were ever reached during a resolver outage,
`ControlPlaneIdentityUnavailable` (RuntimeError) escapes — Starlette's
AuthenticationMiddleware catches only AuthenticationError — producing a 500 where the
wrapper produces 503 for the same outage. Collapse: ContextVar carries the principal
alone, verifier reads it and returns None on miss; deletes `_BearerResolution`, the
digest comparison, the second hash, and the 500 edge in one move.

**F5 (minor, test rigor) `test_controlplane_skins.py` branch-free-delegators test** —
The AST walk collects only `@router.get`/`@mcp.tool` functions, but the layer where
logic would actually accumulate — `_McpObserveAdapter` methods,
`require_control_plane_service`, `control_plane_error_handler` — is unchecked. The test
advertises the spec contract ("skins carry no logic") while enforcing a much narrower
property; an entitlement short-circuit added to the adapter keeps the suite green.
Extend the walk to all functions in both modules minus an explicit shaping allowlist.

**F6 (minor, consistency) `controlplane_routes.py` conversation params** —
Bad input has two error surfaces on an agent-facing API: `shape=invalid` → FastAPI 422
with list-shaped `detail` (no `code` field); `limit=0` → service `invalid_request` →
400 with the structured envelope. A client parsing `detail.code` per the taxonomy
breaks on the 422 path. Either scope a RequestValidationError handler to
`/v1/controlplane` translating into `invalid_request`, or document 422 as outside the
envelope. (MCP mirrors: SDK pydantic text vs structured failure.)

**F7 (minor, typing) `controlplane_auth.py` `resolve_control_plane_bearer(app: object)`** —
The one seam both skins funnel identity through is typed `object` with two `getattr`
chains, disabling static checking at the highest-traffic security boundary; a renamed
`control_plane_grant_resolver` attribute degrades silently to blanket 503 that looks
like an outage. Type it as `FastAPI` (all three call sites pass one) or a small
Protocol exposing the state attribute.

**F8 (minor, error-surface fragmentation) `controlplane_auth.py` + `controlplane/errors.py`** —
The full error vocabulary an agent can receive is split: five codes in the
`ControlPlaneErrorCode` Literal, `control_plane_unavailable` as loose constants in a
skin-support module. Three builders (`api_error`, `control_plane_failure`,
`control_plane_error_envelope`) plus one hand-assembled JSONResponse in the ASGI
wrapper converge on the identical `{"detail":{"code","message"}}` wire shape by
convention, pinned only by a single equality test. Consolidate the vocabulary and one
envelope constructor in `controlplane/errors.py`.

**F9 (low, test hygiene) `test_controlplane_skins.py` `_skin_app`** —
The resolver fake is `SimpleNamespace(resolve=AsyncMock(...))`, conforming to nothing;
`test_grants.py` established the typed-fake convention against the
`ControlPlaneGrantResolver` Protocol, so a Protocol signature change passes this suite
silently. ASGITransport/auth-header boilerplate is also repeated across ~6 test bodies
rather than drawn from the package's conftest client fixture.

**F10 (low, convention nit) `controlplane_mcp.py:31`** —
`# noqa: TC001` without the reason comment the in-directory idiom uses
(`session_routes.py`: "noqa + why"). The reason exists (pydantic needs the symbol at
runtime as a field type) and should be stated.

# Refuted / noted (verified, not findings)

- **No auth bypass** — full chain traced against SDK source; scope enforcement real;
  bearer-None pass-through safe because the mount exposes no unauthenticated route
  (worth a comment that this invariant is load-bearing if auth settings ever grow).
- **ContextVar concurrency** — per-task; anyio `start`/`start_soon` copy the caller's
  context, so stateless task spawn sees the right token; no bleed, no staleness.
- **Non-constant-time digest `==`** — both operands derive from the same request's
  token; no oracle.
- **`issuer_url="https://transport-matters.local"`** — inert: without an auth-server
  provider or `resource_server_url`, the SDK mounts no discovery routes; the field is
  required boilerplate. A comment would help.
- **`CallToolResult` with both TextContent and structuredContent** — required; the SDK
  does not synthesize one from the other, and only `CallToolResult` can express
  `isError=True` for the failure branch of the output union.
- **307 redirect** — fixed relative target, no open-redirect; matches the `/canvas`
  bare-path idiom; SDK client always follows redirects.
- **SDK 401 body diverges from the REST envelope** — OAuth-style
  `{"error","error_description"}` + WWW-Authenticate; RFC 6750-conformant and
  arguably the correct MCP-client behavior; accepted.
- **Lifespan now requires `control_plane_mcp` on state and is once-per-app-instance** —
  every lifespan-bearing app is built by `create_app`, which sets it unconditionally
  (all callers checked); design-intended.
- **`ApiError` vs `ControlPlaneFailure` parallel model trees** — `ControlPlaneFailure`
  is needed as the MCP output-schema union member; convergence covered under F8.
- **`resolve_control_plane_bearer` broad `except Exception` → 503, cause unlogged** —
  pre-existing shape carried over from the S1 dependency (behavior unchanged by this
  diff); fail-closed, but a `logger.warning` with the chained cause would satisfy the
  api/CLAUDE.md "never swallow silently" rule — fold into the F1/F4 fix round.
- **307 redirect drops any query string** — immaterial: the streamable HTTP protocol
  carries no query parameters on this endpoint.

# Self-audit efficacy (brief ask a)

**Reduced — clearly.** S1 and S2 each carried ~10 findings including live functional
defects on the happy path (S1: Codex TOML inline-key seeding failure; S2: Codex
injected-content leak into summaries, cursor loss, audit-on-observe). S3's ten findings
contain **one live item, and only on an error path** (F1: unexpected-exception text
disclosure through the SDK catch-all); the rest are a future-code 500 (F2), a latent
500 on a production-dead branch (F4), and consistency/rigor debts. The edge seams the
brief named were pre-covered by the builder's
own tests before review: auth failure paths (401 parametrized across missing/basic/
malformed/expired, revoked-grant death on both skins, outage 503 equality), the /mcp
SPA collision (ordering + live-dispatch test), schema contract, digest-only SDK
context, and even a self-enforcing skins-carry-no-logic AST test — the builder
anticipated reviewer angles and encoded them as tests. The residue is hardening,
consistency, and rigor, not bugs.

# Builder assessment (brief ask b)

**Trust: HIGH — reinforced, small positive delta vs S1/S2.** The scout-flagged SDK
spike risk (auth-hook fit) was executed correctly against a real SDK constraint
analysis: the outer ASGI pre-resolve exists precisely because `verify_token` cannot
express outage-vs-invalid, which is the right seam, and raw bearers are kept out of SDK
context deliberately. Craftsmanship signals: identity refactored to a shared seam
rather than copied, established idioms reused (/canvas bare-path route, pin style,
error-envelope reuse), disciplined test coverage of adversarial paths written
pre-review. Deductions are the unguarded exception path (F1) and consistency debts
(F2/F3/F8) of the exact kind the previous two rounds also surfaced — the builder's
self-audit catches its own edge cases now but still under-weights cross-surface
uniformity and the gap between what a guard-test claims and what it enforces (F5).
Suitable for sizeable delegated scope with a review
gate; the fix-round pattern (S1: 10/10, S2: 11/11 addressed cleanly) supports that.
