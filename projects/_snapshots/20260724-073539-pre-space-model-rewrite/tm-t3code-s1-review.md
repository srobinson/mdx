# PR#231 review — t3code P1 slice 1 (B-S1)

**Scope:** branch `feat/runtime-s1`, head `daf776d`, baseline `main` (merge-base `cd82775`). `@tm/runtime` skeleton + Gateway mount + full canvas origin contract (WS terminal proxy) + env-gated Python per-route run proxy.
**Method:** first-hand read of every changed file + baselines via `git show main:<path>`; independent read-only verifier + clean-room sweep; all library-behavior claims (httpx, websockets, starlette, Fastify) checked. Repo working tree verified pristine before and after (`git status --porcelain` empty).

## Verdict

**Ship-blocking: none. One Major, five Minor, three low.** The high-blast-radius seams the brief weighted are functionally correct (details under "Focus areas — clean"). The one Major is in the Gateway runtime router's handling of *malformed untrusted query input*, not in the proxy split or the WS bridge.

---

## Focus areas — clean (verified, not just asserted)

1. **WS bridge (sharpest risk).** No deadlock, no socket leak, no frame-type coercion. `_bridge_websockets` (`run_proxy.py:98-115`) waits FIRST_COMPLETED, cancels+gathers the pending side, and in `finally` cancels *both* tasks and closes *both* upstream and downstream. Frame fidelity preserved each direction: downstream `bytes→upstream.send(payload)` / `text→upstream.send(text)` (`160-179`); upstream `isinstance bytes→send_bytes` else `send_text` (`182-192`), matching the Gateway echo `socket.send(data,{binary:isBinary})` (`runtimeRouter.ts:186`). End-to-end bytes+text round-trip is asserted (`test_run_proxy.py:60-63`). Application close codes propagate: an upstream `ConnectionClosed(code)` is forwarded via `_wire_close_code` (only the unsendable reserved `1005/1006` are coerced to `1000`, which is required wire behavior).
2. **GOLDEN RULE (five explicit routes, never a `/v1/runs*` prefix).** Proxy exposes exactly the baseline five (`run_proxy.py:133-155` vs `run_routes.py` five decorators — none dropped). Proxy `GET /runs/{run_id}` (`142`) compiles to a `$`-anchored Starlette regex, so it does **not** shadow `/v1/runs/{run_id}/exchanges` or `/v1/runs/{run_id}/meta`; both stay Python-served. Proven live by `test_run_proxy.py:72-81` (exchanges→`[]`, meta→`run_id`, both 200 from Python).
3. **Env-gating (R1=b), both branches.** `gateway_url` unset → `run_routes.router` registered locally (`main.py:329-330`, no regression); set → the five proxy routes register and `app.state.run_proxy_mount` is wired for lifespan close (`322-328`, closed `266-267`). Empty string is falsy → local path.
4. **Mount contract.** Gateway mounts runtime via the barrel factory `createRuntimeRouter` from `@tm/runtime` (`app.ts:2,49`), no reach-in into internals. `/v1` shared with Activity without collision (Activity serves `/workspaces/...`, registers no websocket). `@fastify/websocket` is registered *inside* the runtime plugin's encapsulated scope (`runtimeRouter.ts:105`), off the Gateway HTTP surface, once. `require_http_origin` gating matches baseline exactly (POST create + POST terminate + WS gated; GET list/get ungated).
5. **Acceptance test exercises the real WS leg.** `TestClient.websocket_connect` (`test_run_proxy.py:53`) drives the proxy→Gateway hop over a real TCP socket to the `originContractGateway.ts` subprocess, and covers the full split (create/list/get/terminal[bytes+text]/terminate/exchanges/meta).
6. **Gate wiring is real.** `importGraphBoundary.test.ts` adds `RUNTIME_SRC`/`RUNTIME_ENTRYPOINT`, fail-closed deep-import cases for `@tm/runtime/server/runtimeRouter` and `@tm/runtime/src/server/runtimeRouter` (`65-66`), an entrypoint-resolves case (`96`), `packageInternalViolations(RUNTIME_SRC,…)` (`120-122`), and includes `runtime` in the single-barrel vacuous-pass guard (`132`). `justfile` check+test and `ci.yml` typecheck+test both enumerate `@tm/runtime`.

---

## Findings

### Major

**M1 — `runtimeRouter.ts:242, 249, 256-257`: throwing `optionalInteger` used on untrusted query strings → HTTP 500 (not the intended 400) and a broken terminal WS on any non-numeric `cursor`/`limit`/`cols`/`rows`; the router's own 400 branches are dead code.**
`optionalInteger` (`common/src/primitives.ts:31-34`) delegates to `requiredInteger` (`25-29`), which `throw new TypeError` for any present string not matching `/^-?\d+$/`; it returns `undefined` only for null/undefined. These routes carry no Fastify JSON-schema coercion (TS generics only), so a raw query string reaches it.
- `GET /v1/runs?cursor=abc` (or `1.5`, `0x1`, repeated `cursor`) → throws before the `cursor === undefined` guard → unhandled in the async handler → Fastify **500**. The `400 {error:"invalid_cursor"}` branch (`122-124`) is unreachable for non-numeric input.
- `GET /v1/runs?limit=abc` → same → **500** instead of `400 {error:"invalid_limit"}` (`126-128`).
- Terminal WS on a *valid* run with `?cols=abc` → `terminalSizeFromQuery` throws synchronously while building the ready frame (`177-184`) → `run.terminal.ready` never sent, socket dies. Baseline `run_routes.py:489-490` validated `cols`/`rows` with `Query(ge=1, le=MAX)` and rejected cleanly, so this is a regression the proxy faithfully forwards (client sees an abnormal close).
- Convention breach: `packages/AGENTS.md` — "Safe variants never throw and are for untrusted input such as wire payloads, where malformed data must be rejected without crashing the process." Wire query strings are untrusted input.
**Fix:** use `safeInteger` for `cursor`/`limit`/`cols`/`rows` (three-way absent/valid/malformed already fits the existing guards), and add tests for non-numeric values on all three params.

### Minor

**m2 — `runtimeRouter.ts:165`: terminal WS hardcodes `DEFAULT_RUNTIME_OWNER` instead of the query owner, so a run created under a non-`local` owner is unreachable over the terminal.** Every sibling route derives owner via `ownerFromQuery` (`108,120,146,155`); `TerminalQuery` (`215-218`) has no `owner` field. `POST /v1/runs?owner=alice` then opening its terminal → `get(runId,"local")` returns `null` → spurious `run_not_found`/`close(1008)` though the run exists. Over-restrictive (not a leak), latent while everything defaults to `local`, but inconsistent and a real gap the moment a non-default owner is used.

**m3 — `run_proxy.py:59-71, 224-225`: HTTP response forwarding re-sends upstream `Content-Encoding`/`Content-Length` over an already-decoded body.** httpx auto-decodes gzip/deflate into `.content` (`68`) but leaves the original `Content-Encoding` and *compressed* `Content-Length` in `.headers`; neither is in `_HOP_BY_HOP_HEADERS` (`27-39`), and Starlette `Response` does not override a caller-supplied length. If the Gateway ever sits behind a compressing layer, the client double-decodes / length-mismatches. Latent today (Fastify registers no `@fastify/compress`).

**m4 — `run_proxy.py:225`: `_forward_headers` collapses duplicate headers.** `httpx.Headers.items()` (response leg) comma-joins repeated names, so multiple `Set-Cookie` fold into one corrupt value (RFC 6265 forbids folding); the request leg (`starlette Headers.items()`) instead drops all but the last. Use `multi_items()` / preserve duplicates for a faithful proxy. Latent (the stub emits no duplicate headers).

**m5 — `run_proxy.py:78-96`: `forward_terminal` does not handle an upstream connect failure after `accept()`.** Only `ConnectionClosed` (`93`) and `WebSocketDisconnect` (`95`) are caught. If `websockets.connect(target)` (`91`) fails after `await websocket.accept()` (`85`) — Gateway down (`OSError`), non-101 handshake (`InvalidStatus`), or timeout — the exception propagates unhandled and the already-upgraded client gets an abnormal `1006`/`1011` close plus an error traceback per attach, instead of a clean policy close. Upstream is not leaked (the `async with` never binds); wrap connect and close downstream with a deliberate code.

**m6 — `test_run_proxy.py`: the sharpest slice risk is untested.** The file has a single happy-path test (`27`). No test drives an upstream application close code (e.g. `run_not_found` → `1008`) through the proxy to the downstream client, and there is no unit test for `_wire_close_code`, `normalized_gateway_url`, `_join_paths`, or `_forward_headers`. Add a close-code-propagation case and unit tests for the pure helpers.

### Low / notes

**L1 — `runtimeRouter.ts:224-237`: `stateFromQuery` silently maps any unrecognized `state` (typo, lowercase `running`) to `undefined` → returns the *unfiltered* list.** Baseline `run_routes.py` funnels `state` through `_public_state_filter` and 400s on a bad value. Tolerant-by-design is defensible, but a client filtering by a mistyped state silently receives more rows than intended.

**L2 — `runtimeRouter.ts:248`: default page size when `limit` is omitted is `MAX_RUNS_LIMIT` (100), vs baseline `DEFAULT_RUNS_LIMIT` (50).** Behavioral drift the proxy forwards; confirm intended.

**L3 — `run_proxy.py:60 vs 87`: run_id path-encoding asymmetry.** HTTP forwards `request.url.path` (ASGI-decoded) unencoded; WS re-encodes via `quote(run_id, safe="")`. Divergent upstream targets only for a run_id with reserved chars; ids are server-minted `runtime-run-N`, so no live trigger.

---

## Out of scope (per brief, not flagged)
Real PTY, capture RPC, real run behaviour (stub by design); the signed-off design decisions (Fastify, plain-TS no-Effect, env-gated proxy, interim Python front door).

---

## Delta verification — fix round `16815e8` (was `daf776d`)

One commit, 7 files. HEAD `16815e8`, tree pristine before and after. Verified **deltas only** against baseline `main`.

**Resolved 8/9, all with failing-before/passing-after tests asserting observable end-state:**

- **M1 (Major) FIXED** — new non-throwing `safeIntegerString` added to `@tm/common` (`primitives.ts`, exported, unit-tested), routed through `integerFromQueryValue`/`boundedIntegerFromQueryValue`. `cursor=abc`→`400 invalid_cursor`, `limit=1.5`→`400 invalid_limit`, terminal `cols=abc`/`rows=1.5`→`run.error invalid_terminal_size` + clean `1008` close (bounds now 1..500/1..200). No dead 400 branch. Tests: `runtimeRouter.test.ts` (malformed pagination, invalid terminal size).
- **m2 (Minor) FIXED** — terminal WS uses `ownerFromQuery`; `TerminalQuery.owner` added; test attaches a run created with `?owner=alice`.
- **m3 (Minor) FIXED** — response omits upstream `Content-Encoding`/`Content-Length` (`_DECODED_RESPONSE_HEADERS`), re-applies the auto-computed length via `_replace_raw_headers`; request strips `Content-Length`. Unit-tested.
- **m4 (Minor) FIXED** — `_forward_headers` now returns a `list[tuple]` via `multi_items()`/`.raw`, preserving duplicate `Set-Cookie`. Unit test asserts two `set-cookie` survive.
- **m5 (Minor) FIXED** — `websockets.connect` wrapped; `except (OSError, TimeoutError, InvalidHandshake, InvalidStatus)` (PEP 758, valid on this `requires-python >=3.14` repo, `py_compile` OK on 3.14.5) → closes downstream `1011 gateway_unavailable`. Test `test_terminal_proxy_closes_cleanly_when_gateway_connect_fails` asserts `1011`. Close-code extraction moved to `_closed_code`/`_closed_reason` via `exc.rcvd or exc.sent` — verified valid on `websockets` 16.0.
- **m6 (Minor) FIXED** — added run_not_found `1008` propagation assertion (real gateway leg, 0.60s call confirms it ran, not skipped) + connect-fail `1011` test + unit tests for `normalized_gateway_url`/`_join_paths`/`_wire_close_code`/`_forward_headers`.
- **L1 (low) FIXED** — `stateFromQuery` returns `null`(absent)/state/`undefined`(invalid); handler returns `400 invalid_state`. Test `state=running`→400.
- **L2 (low) FIXED** — omitted `limit` now defaults to `DEFAULT_RUNS_LIMIT` (50). Test: 51 runs → 50 items, `nextCursor "50"`.

**Not addressed (1/9):**

- **L3 (low) OPEN** — `run_proxy.py:60`: `forward_http` still forwards `request.url.path` (ASGI-decoded) unencoded while the WS leg quotes `run_id`. Unchanged in the delta. Lowest severity, **no live trigger** (run ids are server-minted `runtime-run-N`); latent inconsistency only for a crafted reserved-char id. Not a blocker; orchestrator/builder to accept-as-won't-fix or close.

**No regressions / no new issues.** Green: `@tm/common` 13, `@tm/runtime` 8, `@tm/gateway` 13 (consumer of `@tm/runtime`), python `test_run_proxy.py` 6/6; `@tm/runtime`+`@tm/common`+`@tm/gateway` typechecks clean.
