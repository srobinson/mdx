# 381: TM Autopilot: first-turn education, controlled harness baselines, and owned overlays

URL: https://github.com/littleorgans/transport-matters/issues/381
State: open
Labels: enhancement
Updated: 2026-08-12T13:26:24Z

## Product goal

Transport Matters is the harness and token optimization authority across supported harnesses, providers, and models.

The product has three ordered capabilities:

1. An optional first-time report that proves the problem using the user's real first full turn.
2. TM Autopilot, the core paid capability, which controls the harness environment, understands request shapes, manages release compatibility, and applies TM-owned optimizations.
3. Future power-user controls for inspecting, customizing, and versioning overlays.

## Goal 1: optional first-turn education

Provide a one-off welcome and onboarding HTML report. The user can skip it and invoke it later.

Value proposition:

> Let me show you how much junk your harness sent with your request and will send repeatedly.

The report uses the user's real harness environment and first full provider-bound turn. Auxiliary requests such as prewarm, title generation, token counting, and health checks are excluded.

The report must show:

- the complete captured request safely rendered
- total bytes, characters, and tokens
- exact token counts when authoritative, clearly labelled estimates otherwise
- totals by API role: system, developer, user, assistant, tool, and metadata
- totals by provenance: user-authored, user-configuration-derived, session-derived, static harness content, provider metadata, and unknown
- every textual leaf with exact JSON Pointer, digest, characters, tokens, role, provenance, and classification evidence
- observed facts separately from inferred classifications

This path is read only. It does not require overlay support.

## Goal 2: TM Autopilot

Autopilot is the product USP. TM controls harness configuration, settings, and ephemeral homes, then minimizes provider requests safely.

A temporary feature flag or emergency escape hatch may use a name such as `TM_AUTO_PILOT`. Final naming and user-facing behavior remain TBD. Mature Autopilot should be enabled by default.

### Controlled capture

Reuse the existing ephemeral-home and agent-runtimes integration. Do not create a second runtime-home mechanism.

For each relevant harness, harness version, provider, model or model family, and request shape, launch controlled probes with:

- the known minimum settings required to pass harness onboarding
- no user skills
- no user MCP servers
- no user memory
- no project customization
- deterministic probe prompts
- fresh session state

These captures are internal TM certification evidence.

### Derived artifacts

Produce and persist four distinct artifacts:

1. Observed wire schema: exact paths, types, cardinality, optionality, and structural relationships seen across controlled captures.
2. Semantic mapping: provider fields mapped into TM IR system parts, messages, tools, sampling, metadata, and provider extras.
3. Static baseline: exact harness-supplied content, content digests, and request fingerprints.
4. Overlay: approved transformations for a matching harness/provider/version and request shape.

A schema inferred from captures is an observed schema, not an exhaustive provider contract. Multiple deterministic probes should strengthen it over time.

### Harness release lifecycle

At runtime, detect the installed harness version and resolve its compatibility state:

- Known certified release with matching shape: apply the approved overlay.
- New release with no drift: certify and continue.
- New release with compatible drift: record the new shape and continue safely.
- New release with breaking drift: forward requests unoptimized, inform the user that support is being prepared, then update TM's adapter, IR mapping, schema family, or overlay.

Breaking drift must degrade optimization without breaking the user's harness request.

Supporting new harness releases is mandatory.

### Open support-policy decision

Decide how long TM supports older harness releases after a new release is blessed.

Initial proposal: support compatibility families rather than permanent version-specific branches. Keep the current and immediately previous breaking compatibility families. Older releases that still match an active family continue to work without separate code.

## Goal 3: future power-user overlay control

After Goal 2 establishes one TM-owned capture, classification, matching, application, audit, and persistence path, allow power users to:

- inspect the active TM overlay
- fork it into a user variant
- edit selected operations
- save named versions
- compare token impact
- restore an earlier version
- return to the TM-managed overlay

This must reuse Goal 2's overlay authority. No parallel mutation or persistence path.

## Cross-cutting requirements

- Multi-harness and multi-provider by design.
- JSON request extraction is generic. Provider adapters own semantic mapping.
- Every mutable text preimage corresponds to one actual raw string leaf. Aggregated display values retain constituent paths and digests.
- Preserve original request, overlay version, provider-bound request, audit, and response.
- Fail safely to unoptimized passthrough when compatibility or application cannot be proven.
- Keep first-turn education, internal certification, and overlay mutation as separate product concerns.

## Related work

- #370 tracks the narrower worksheet/export mechanism.
- #369 tracks the opaque Codex `additional_tools` request shape.
- Existing controlled capture and normalization work in `baseline_harvest.py` is the likely reuse owner.
- Existing request mutation remains `OverrideStore` through `run_pipeline` and `apply_overrides`.

## Implementation order

1. #385 separates authentication from usable provider access.
2. #386 promotes Grok to a first class managed harness.
3. #382 captures controlled baselines and observed request schemas after the supported harness contract is truthful.
4. #383 builds the optional welcome report from that evidence.
5. #384 applies TM-owned overlays through the certified release lifecycle.

## Parent acceptance

This parent is complete when:

- Goal 1 can render an optional first-full-turn HTML report from a real user launch.
- Goal 2 can capture a controlled harness baseline, derive an observed schema, classify release drift, select a compatible overlay, and prove the provider-bound optimized request.
- Breaking drift produces safe passthrough and a truthful user notice.
- The older-version support policy is decided and documented.

Goal 3 may remain a linked future issue once the underlying Goal 2 authority is proven.



## Comment by srobinson at 2026-08-12T12:03:30Z (updated 2026-08-12T12:03:30Z)

https://github.com/littleorgans/transport-matters/issues/381#issuecomment-5266550015

## Implementation order

GitHub sub-issues now track delivery:

1. #370 creates the generic exact-leaf request inventory.
2. #382 uses that inventory for controlled captures and observed schemas.
3. #383 consumes #370 and #382 for the optional first-turn HTML welcome report.
4. #384 consumes #370 and #382 for the runtime compatibility lifecycle and TM-owned overlay application.

#369 remains related parser work for the opaque Codex `additional_tools` shape. It does not block the raw request inventory.

Goal 3 power-user overlay versioning remains future work after #384 proves the single TM-owned overlay authority.


## Sub issues
[
  {
    "number": 370,
    "state": "closed",
    "title": "Request inventory: exact JSON leaves, digests, and semantic labels"
  },
  {
    "number": 382,
    "state": "closed",
    "title": "Autopilot baselines: controlled captures and observed request schemas"
  },
  {
    "number": 383,
    "state": "open",
    "title": "Welcome report: explain the first full provider request in HTML"
  },
  {
    "number": 384,
    "state": "open",
    "title": "TM Autopilot: release compatibility lifecycle and owned overlay application"
  },
  {
    "number": 392,
    "state": "closed",
    "title": "RESPONSES coverage table: declare the second hop for codex and grok"
  }
]
