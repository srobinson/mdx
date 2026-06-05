# MCP harnesses tool — launch-view projection

Branch: `feat/launch-contract-model-effort` (stacked on the launch contract). Small, self-contained.

## Problem (from the Director agent consuming the tool)
The MCP `harnesses` tool (`api/v1/controlplane_mcp.py`, `_McpControlPlaneAdapter.harnesses`) passes the full `HarnessInventoryResponse` through untouched. That payload is the **diagnostic** read model — doctor, certification, inspector UI need observation revisions, probe timestamps, channel records, executable paths. A **token-priced agent deciding what to launch** needs none of it. Two consumers, two read models; the tool serves the wrong one to the agent. ~90% of the payload is waste for the launch consumer.

## Fix: a pure projection, launch view by default
Add a parameter `view: "launch" | "full"` to the MCP `harnesses` tool, **default `"launch"`**. Implement as a **PURE PROJECTION in the MCP adapter over the same `HarnessInventoryResponse`** — no new query, no second source of truth. `GET /api/v1/harnesses` and the inventory model stay exactly as-is for the API/UI.
- `view="full"` → current behavior (full payload). Must remain a real escape hatch.
- `view="launch"` → the lean projection below.

## Launch-view shape
Per the director's target:
```json
{
  "harnesses": [
    {"harness": "claude", "launchable": true, "auth": "authenticated",
     "efforts": ["low","medium","high","xhigh","max","auto"],
     "models": ["best","default","fable","fable[1m]","haiku","opus","opus[1m]","opusplan","sonnet","sonnet[1m]"]},
    {"harness": "codex", "launchable": true, "auth": "authenticated",
     "models": [{"id": "gpt-5.6-sol", "efforts": ["low","medium","high","xhigh","max","ultra"], "default_effort": "low"}, "..."]},
    {"harness": "grok", "launchable": false, "reason": "compatibility_release_unavailable"}
  ]
}
```
Projection rules:
1. **Drop `target_observations` entirely** — it is the raw evidence; `launch_options` is the derived launchable surface. Use launch_options.
2. **Hoist per-row boilerplate to harness level**, surface only DEVIATIONS. connection_id, route_id, support_tier, lifecycle, requires_unverified_opt_in, empty advisory arrays are identical across rows — do not repeat per model. Surface a deviation only when real (a deprecated model, a genuine exclusion reason).
3. **Effort**: when the effort list is uniform across a harness's models (claude: identical across all 10), emit ONE harness-level `efforts` list and models as a flat string list. When it genuinely varies (codex sol/terra add max/ultra), emit per-model `{id, efforts, default_effort}` one line each.
4. **Drop timestamps, revisions, probe metadata** — diagnostic only.
5. **Non-launchable harness** (e.g. grok): one line, `launchable: false` + `reason` (the exclusion/compat code, e.g. `compatibility_release_unavailable`). Answer the only question about it in one line.

## GUARD (coherence with the launch contract — the one thing the director's note doesn't state)
The launch view's model/effort vocabulary MUST be exactly what the launch contract accepts. Both source from `launch_options` / the enumerated catalog. The projection reads model/effort from **`launch_options`** (the same surface `resolve_target`/the launcher use), NOT re-derived from observations — so an agent can pass any model/effort it sees here straight to `launch(model=..., effort=...)` and vice versa. No drift between read view and write contract.

## Tests
- Projection produces the lean shape; no target_observations, no timestamps/revisions/probe metadata in launch view.
- Uniform-effort harness (claude): one harness-level `efforts` + flat model list. Varying harness (codex): per-model efforts + default_effort.
- Boilerplate hoisted; a deviation (deprecated model / exclusion reason) surfaces.
- Non-launchable harness → one-line launchable:false + reason.
- `view="full"` returns the unchanged full payload (escape hatch intact).
- COHERENCE: the models/efforts in the launch view equal `launch_options`' models/efforts (== what `launch()` accepts).

## Gate
`just check` + `just test-affected`.
