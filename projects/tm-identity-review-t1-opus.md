# T1 review — PR #329, `fix(space): proxy acting context through browser origin`

Reviewer: opus (`multi-launch:general:1:3.3`), sole reviewer.
Target: head `5bbc2608`, base `d1f499e5`, branch `ml/identity-transport`. Tree clean, read-only.
Diff: +172 / -2 across 7 files.

**Verdict: 0 blockers, 1 major, 2 minors.** The transport fix itself is correct and the
reachability test generalises well beyond the single perturbation the builder ran. The one
major is that the proof never executes in CI.

---

## Verification performed

Beyond reading, I ran the gates and drove the routes directly against a live Gateway process
(probe script kept out of the repo, in scratchpad):

- `ruff check` / `ruff format --check` / `mypy src/` — clean, 701 files.
- `pytest src/transport_matters/api/v1/test_run_proxy.py test_runs_unavailable.py` — 18 passed.
- `pnpm --filter @tm/gateway exec tsc --noEmit` — clean.
- Live-gateway probe matrix, results below.

| probe | result |
|---|---|
| POST resolve-workdir, trusted origin, valid body | `200` + the Gateway fixture receipt |
| POST resolve-workdir, trusted origin, **malformed** body | `400 invalid_request` (from `spaceRouter:workdirInput`) |
| POST verify, trusted origin, **malformed** body | `400 invalid_request` (from `spaceRouter:verifyInput`) |
| POST either route, foreign origin | `403 origin_not_allowed` |
| POST either route, no `origin` header | `403 origin_not_allowed` |
| POST with gateway dead (port 9) | `503 gateway_unavailable`, message names the unreachable URL |
| POST with no gateway configured | `503 gateway_unavailable` from the stub |
| POST either route, foreign origin, no gateway configured | `403` — guard wins before the 503, correct precedence |

The `400 invalid_request` rows are the load-bearing ones: the Gateway only produces that code
after parsing the forwarded body, so method, path, `content-type` and body all demonstrably
survive the hop, and a non-2xx upstream status propagates rather than being masked. Brief
item 3 is satisfied.

---

## Brief item 1 — does the unreachability test generalise? **Yes.**

`test_run_proxy.py:test_canvas_origin_reaches_space_gateway` spawns a **real Gateway process**
(`test_gateway_support:gateway_url` → `originContractGateway.ts` under `tsx`), builds the real
Python app, POSTs through `TestClient`, and asserts `200` plus the exact receipt body. It is not
tuned to the mount-move perturbation. It fails under every failure mode I could construct:

- route removed from `run_proxy:create_run_proxy_mount` → SPA catch-all is GET-only → `405`.
- `/v1` prefix dropped in `controlplane_gateway_space:gateway_space_route_path` → Fastify `404`.
- `createSpaceRouter` not mounted / space deps absent → Fastify `404`.
- Gateway not running → `503 gateway_unavailable`.
- body or `content-type` dropped by the proxy → `400 invalid_request`.
- wrong method on either side → `404`/`405`.

The builder's `405 != 200` observation is explained: an unmatched `/v1/...` path still matches
the GET-only SPA fallback, so a POST returns 405 rather than 404. Either way the assertion fails.
Only the Gateway→Postgres hop is stubbed, which is the right seam for a transport slice.

## Brief item 2 — are all three environments covered? **Structurally yes, by one mount.**

Each claim verified against code, not description:

- **Desktop** — `desktop/src/window.ts:createHostedWindow` loads `rendererUrlForPort(webPort)`,
  the Python port; `desktop/src/backendProcess.ts` hands the Gateway URL to the *backend* as
  `TRANSPORT_MATTERS_GATEWAY_URL`. The renderer has no route to the Gateway except through
  Python. Claim holds, and this is precisely why the route was unreachable before.
- **Dev** — `www/packages/shell/vite.config.ts:buildDevServerProxy` forwards all of `/v1` to the
  Python target. Nothing slice-specific needed.
- **Packaged** — `main.py:create_app` resolves `gateway_url = settings.gateway_url or gateway_plan.url`
  and takes the *same* `create_run_proxy_mount` branch. Packaged and desktop are one code path,
  not two.

There is exactly one mount decision, so per-environment tests would be redundant rather than
absent. No finding here.

## Brief item 4 — scope creep? **None.**

The diff touches transport only: the proxy routes, the no-gateway 503 stub, two tests, and the
Gateway test fixture. No identity ownership, precedence, persistence, or reload changes.
`createSpaceRouter` remains the sole handler; the Python side adds nothing but the origin guard
and a `/v1` path mapping — no second implementation, no divergent validation.

---

## MAJOR — the reachability proof is skipped in CI

`test_gateway_support:_GatewayProcess.__enter__` calls `pytest.skip` when `pnpm` is absent or
`node_modules` does not exist. The `backend · test` job in `.github/workflows/ci.yml` has no
`setup-node`, no pnpm, and no `pnpm install`; `actions/checkout` does not create `node_modules`.
It is the only job that runs pytest.

Confirmed empirically — same test, PATH without pnpm:

```
SKIPPED [1] test_gateway_support.py:32: pnpm is required for the Gateway origin contract test
1 skipped in 0.03s
```

Locally the recipe saves it: `just test` depends on `js-install`, so the test really runs.
CI is the merge gate, and in CI it reports green having proved nothing.

This is the exact defect class the slice exists to close — a verification that silently does not
run behind a green suite — reproduced in the fix's own gate. The mechanism is pre-existing (the
sibling `test_canvas_origin_contract_splits_run_routes_to_gateway` has always been skipped the
same way), but it was cheap insurance there and is the entire deliverable here.

Fix: add `pnpm/action-setup` + `setup-node` + `pnpm install --frozen-lockfile --ignore-scripts`
to `backend · test`, mirroring the `frontend` job (~8 lines of YAML, one extra install on one
job). A guard env var that turns the skip into a failure would also work but leaves the test
still not running.

## MINOR — the origin guard on both new routes is untested

`run_proxy:forward_space_acting_context` calls `proxy.require_http_origin`, and both
`space_gateway_unavailable` handlers take `Depends(require_http_origin)`. Every new test sends
`HTTP_HEADERS`, so deleting either guard leaves the suite green — while `space_routes.py` has an
explicit convention test for exactly this,
`test_space_routes:test_rest_inventory_mutations_require_trusted_origin`, enumerating every
mutating Space route and asserting `{403}`.

The guard works today (probe rows 4-6, both modes). This is coverage, not a live defect.

Fix: assert `403` for both routes with a foreign origin, once in `test_run_proxy.py` and once in
`test_runs_unavailable.py` — two lines each, reusing the existing clients.

## MINOR — `"gateway_unavailable"` is an unnamed literal

`space_gateway_unavailable:_raise_gateway_unavailable` inlines the wire code as a string while
naming only `SPACE_GATEWAY_UNAVAILABLE_MESSAGE`. Its direct model, `runs_unavailable`, names
`RUNTIME_UNAVAILABLE_CODE` alongside its message, and `run_proxy:forward_http` raises the same
string twice more. Three unnamed occurrences of one browser-visible error code.

Fix: name it once (next to `SPACE_GATEWAY_UNAVAILABLE_MESSAGE` or in `errors`) and use it in all
three places.

---

## Observation, not a finding — Space disabled on a live Gateway returns a bare 404

`gateway/src/main.ts:resolveSpaceDeps` returns `undefined` when `TRANSPORT_MATTERS_DATABASE_URL`
is unset, and `app.ts:gatewayContexts` then omits the space mount entirely. The proxy faithfully
propagates Fastify's `404`. So there are two "Space is not available" states with different
shapes: no gateway at all → diagnosable `503 gateway_unavailable`; gateway up but Space disabled
→ opaque `404`, indistinguishable to the browser from the bug this slice just fixed.

This is Gateway-side shape, identical for `activity`, untouched by this diff, and not T1's
subject. Flagging it because T2/T3 will put a real browser caller behind these routes and that
caller will need to tell the two states apart. It should be decided there, not patched here.

## Note on the diff's premise

There is no browser caller of `/v1/spaces/acting-context/*` on this line — the consumer lived on
`be26765b` (`origin/ml/identity-s4`), the discarded branch. T1 is therefore prospective plumbing,
correctly so under the replacement sequence, and the "404'd every boot" framing describes the
discarded branch's behaviour, not current `HEAD`. No action; recorded so the sequencing claim is
not mistaken for a live regression.

## Craftsmanship

Placement, naming, and shape are right. `space_gateway_unavailable.py` mirrors `runs_unavailable.py`
closely enough to read as one family. Sharing `ACTING_CONTEXT_*_PATH` between the proxy and the
stub means the two modes cannot drift apart. Using `proxy.require_http_origin` inside the mount
and `Depends(require_http_origin)` in the stub matches each file's existing convention rather than
inventing a third. Router ordering is correct — the proxy mount registers before `space_routes`,
so the literal `acting-context` paths cannot be shadowed.

Pre-existing DRY smell, out of scope: `RunRouteProxy.require_http_origin` duplicates
`origin.require_http_origin` verbatim, differing only in settings source.
