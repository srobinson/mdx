# Transport Matters Launcher — `provider → model → agent`

Date: 2026-06-17
Status: PEER-REVIEWED (Claude codebase-analyst + Codex, MoE; §8 consensus = keep repos separate). 2026-06-17 additions re-reviewed, conditions applied: §6 sequencing (launcher-before-loading-flow), §10 reframed around fleet-vs-curation (dissolves old §10.1), §11 track-2 horizon. §10 `tm-fleet` vendoring RATIFIED with agent-runtimes (bus `tm-launcher-proposal`, 2026-06-17): portable seed (`runtime.toml` + `capabilities.json`) + `~/.agent-runtimes/tm-fleet.toml` membership manifest; target-time materialization of machine-specific config is an open TM packaging decision. One verification prerequisite surfaced: non-interactive `/model` enumeration is unverified for both CLIs (§6.1). Two-repo design.
Owners: transport-matters (TM, this doc + the wire/cascade half) and agent-runtimes (the home/skill half).
Counterpart spec (home half): `/Users/alphab/.agent-runtimes/docs/specs/2026-06-17-launcher-home-spec.md` (canonical for §"agent-runtimes half"; summarized here, not duplicated).
Bus topic of record: `tm-launcher-proposal`.

## 1. What we are building

A layered launcher for captured runs in the desktop canvas. At spawn time the user
configures a run along three layers — **provider → model → agent** — where "agent"
is the product-surface name for a runtime home (`~/.agent-runtimes/runtimes/<name>`
template; the registry root is `~/.agent-runtimes/runtimes/`, per
`runtime_registry.py::_registry_root`).

This grew out of the NOW.md ephemeral-home "desktop template-picker UI" follow-up.
The picker becomes the third layer of a richer configurator. The backend for the
agent layer already exists (ephemeral-home Slices 1-4, merged): `runtime_template`
is plumbed request-edge → `SpawnRun` → `CapturedRunRequest` → `plan_runtime_home`.

The layers form a constraint chain, not three independent dropdowns:

- **Provider** (claude / codex) — entry point; pins CLI + auth. Already the spawn
  affordance today (the two canvas spawn buttons).
- **Model + effort** (the middle layer). The model is sourced from the CLI's own
  `/model` availability (the CLI already entitlement-filters it, so it is the per-user
  set of usable models; no plan→models catalog or plan detection is required). Effort
  (Claude low/medium/high/xhigh/max; Codex its own reasoning-effort enum) is a second
  managed field chosen alongside the model and may be constrained per model. Both are
  managed launch fields, not passthrough.
- **Agent** (runtime home) — filtered to homes compatible with the chosen
  model+provider via a single capability check. Most homes are dual-target (DRY
  default); only homes requiring a provider-exclusive capability pin a provider.

Empty selection = current behavior (native home, default model). Selections persist
per provider in the canvas store (same as existing zustand view-state), so the
zero-config fast path stays fast. Exact visual layout (panel vs popover vs
split-button) is a frontend-design decision at build time, out of scope for this
data-model design.

**Launcher scope (Stuart).** The launcher manages the per-run spawn choices ONLY:
provider, model, effort, agent. Every other setting is managed outside the launcher in
a separate settings panel, not at spawn. So the managed-field set here is bounded
(model + effort), not an open extensible bag; a new non-spawn setting lands in the
settings panel, never in this cascade.

## 2. Two confirmed corrections to the naive model

1. **Model availability is captured, not inferred.** The CLI's `/model` command
   already returns only entitled models. The cascade's model layer reads that
   captured list directly. TM does **not** maintain a static plan→models catalog
   and does **not** detect the plan to filter models.
   - **Staleness (review finding, Major).** A captured list is a point-in-time
     snapshot and is NOT evergreen: a mid-subscription plan upgrade/downgrade,
     server-side model deprecation, or a capture taken under a different account
     can leave the list stale (hiding newly-entitled models, or offering a model
     that now rejects `--model`). v1 must name a refresh trigger (a TTL on the
     cached `/model` list and/or re-capture on onboarding re-run), with the
     launch-time validation (§3.2.6) as the backstop, not the only guard. A
     one-time lazy capture is insufficient.
   - **Capture is wire-first, and carries a label↔id mapping (Stuart).** The `/model`
     list reaches TM as bytes, so TM captures it from the wire rather than scraping the
     interactive picker. This matters: the picker shows friendly LABELS ("Opus",
     "Sonnet") and surfaces the canonical id only for the selected entry, while
     `--model` needs the canonical id (e.g. `claude-opus-4-8`). Wire-capture yields the
     canonical ids directly; the friendly label is kept for display only, and the
     label↔id pairing is captured rather than hand-maintained (so it does not rot on
     provider renames). Mechanism preference order: wire-capture, then the CLI's
     on-disk model cache, then driving the PTY to issue `/model`, then a
     non-interactive flag if one exists.
2. **Subscription plan is declared, and orthogonal to the cascade.** The plan
   (Claude Pro/Max5x/Max20x, Codex Go/Plus/Pro) cannot be inferred — verified: TM
   captures zero entitlement/tier signal today and it is likely not parseable on
   the wire. It is a prompted value at onboarding, used for **token optimization**
   (defaults, quota/cost awareness), NOT to filter the model list. It sits outside
   the cascade.

Net effect: the cascade collapses to a single filter. `provider → (captured
/model availability) → agent (capability-filtered)`. The only filter applied is
capability set-containment: `model.capabilities ⊇ agent.required_capabilities`.

## 3. Ownership split

### 3.1 agent-runtimes half (LOCKED — see counterpart spec §1-8)

- Homes go **model-agnostic**: `generate.py` stops baking a binding `model` into
  `settings.json` / `config.toml`. Legacy `[settings.*].model` deprecates to a
  non-binding `recommended_model` hint.
- Skills declare their own needs in `SKILL.md` frontmatter: `requires_capability`
  (default `[]`), optional `provider` (`claude`|`codex`). The skill is the single
  source of truth; the home inherits, never re-declares.
- `runtime.toml` gains `[skills] required/optional` (required skills' constraints
  bind the home; optional degrade gracefully) and `[recommended_model]`.
- `generate.py` (runs only at author/build time, writes into the pristine template
  root) derives `home.provider` and `required_capabilities` and emits
  `<template>/capabilities.json`.

### 3.2 transport-matters half (this doc)

1. **Plan setting** — declared per-provider tier (prompted at onboarding). Informs
   token/cost optimization only. (Auto-detection = v2, see §7.)
2. **Model source** — captured `/model` availability per provider (from onboarding's
   CLI-detection capture; the launcher captures lazily on first use if onboarding
   has not run). This is the entitlement-filtered model list.
3. **Capability matrix** — TM owns the *fine* truth (which captured model provides
   which capabilities). TM publishes a *coarse* per-capability `providers`
   projection into the shared registry that `generate.py` reads (§4).
4. **Capability filter** — the single cascade filter: hide agents whose
   `required_capabilities` are not all satisfiable by the chosen model. Bidirectional
   (pick model → filter agents; pick agent → filter models) as the same join read
   both ways. Base case (the common one): an empty `required_capabilities` set is
   satisfied by every model (`model.capabilities ⊇ []` is always true), so a
   dual-target home with no required capabilities matches all models — no guard
   needed, this is the intended default.
5. **Model + effort injection** — *managed* `model` and `effort` launch fields
   translated to their flags by the spawn builder (`--model`, plus the per-CLI effort
   flag). NOT raw user passthrough (per NOW.md #2 "tm owns launch config, not flag
   passthrough"). Bounded to model + effort; all other settings are the settings
   panel's job (§1 scope), not launch fields here.
6. **Read surface** — the list-templates endpoint reads each template's
   `capabilities.json` at browse (populate + filter the cascade) and at launch
   (validate the chosen model). TM never parses skill frontmatter.

## 4. The seam (data contract)

1. **Shared versioned capability vocabulary.** v1 = **`{image-generation}`** only.
   Inclusion rule (YAGNI): a name earns v1 only if a real catalog skill requires it
   AND it varies across offered models. `image-generation` qualifies: required by
   `helioy-imagegen` / `helioy-imagegen-primatives` (codex-source-only), provided by
   zero Claude models — the canonical hard split that proves the pipeline
   end-to-end. `vision` deferred to v2 (every offered model has vision today, so it
   never discriminates; reopen when a no-vision tier is offered).
   `web-search`/`computer-use`/`code-execution` excluded (served by harness tools,
   not model-native); names reserved.
2. **Per-capability `providers` projection** in the registry (coarse). Example:
   `[image-generation] providers = ["codex"]`. TM owns it (a projection of the fine
   matrix); `generate.py` reads only this coarse field, never the fine matrix.
   Coarse `providers` is provider-level existence ("≥1 model of this provider, any
   tier, provides it") — NOT plan-conditional. Plan-narrowing stays TM's fine filter.
3. **Provider derivation (coarse/fine boundary).** `generate.py` computes
   `home.provider` at build = "both" by default, narrowed by INTERSECTION over
   required skills of {explicit `provider` pin, skill source-availability,
   registry `providers`}. So an imagegen-required home precomputes `provider="codex"`
   into `capabilities.json`; TM reads it straight off the artifact and does not
   re-derive. Empty intersection / contradictory explicit pins = should-never-fire
   build-time assert (Stuart's invariant: targeted homes never mix exclusives;
   homes stay dual-target unless a required provider-exclusive capability forces a
   pin — DRY, no near-duplicate claude/codex homes).
4. **`capabilities.json` shape** (emitted into template root):
   ```json
   {
     "schema_version": 1,
     "provider": "both" | "claude" | "codex",
     "required_capabilities": ["image-generation"],
     "recommended_model": { "claude"?: "<canonical-id>", "codex"?: "<canonical-id>" } | null,
     "generated_from": "<hash>"
   }
   ```
   `recommended_model` is per-key-optional; values are the provider's **canonical
   model-id string** (exactly what TM passes to `--model`); omit a key rather than
   guess. `generated_from` supports a v2 drift check (present-but-ignored in v1).
   TM reads this at browse and launch.
   - **Pre-select fallback (review finding, Minor).** A present `recommended_model`
     value may not be in the user's captured `/model` availability (deprecated, or
     a different tier). Pre-selection is best-effort: if the hinted id is not in the
     captured list, TM does NOT pre-select it and falls back to its own default for
     that provider. Same fallback as an absent key.

## 5. TM-side design detail (file:symbol)

Seam already exists; this is additive.

- **Request edge.** `CreateRunRequest` (`api/.../api/v1/run_routes.py`) already
  carries `runtime_template` (alias `runtimeTemplate`). Add two managed fields: `model`
  (validated against the captured `/model` availability for the resolved provider) and
  `effort` (validated against the provider's effort enum, and against the chosen
  model's `allowed_efforts` if that constraint is captured). Bounded set, not an open
  bag: all other settings live in the settings panel (§1 scope), not on the spawn
  request.
- **Model + effort injection.** The spawn builder
  (`api/.../captured_claude.py::build_claude_captured_invocation` →
  `api/.../cli/launch_profile.py::ClaudeLaunchProfile.client_argv` /
  `CodexLaunchProfile.client_argv`) already threads a `passthrough` sequence. Thread
  the managed `model` and `effort` through `SpawnRun`/`CapturedRunRequest` and have the
  profile emit the flags: `--model <id>` (Claude `--model`, Codex `-m`/`--model`, both
  verified) plus the effort flag per CLI. The effort flag names are NOT yet verified
  for either CLI (the picker exposes effort as an interactive adjuster, not a confirmed
  launch flag); verify the Claude and Codex effort-flag spelling alongside the §6.1
  capture-mechanism check, before the injection slice.
  - **Sequencing dependency (review finding, Major; sharpened by agent-runtimes).**
    TM does not synthesize a model key, but launch materialization
    (`api/.../cli/home_overlay.py::materialize_runtime_home_template_overlay`,
    `_copy_overlay_local_files`) copies the template's `settings.json`/`config.toml`
    **verbatim** into the home, and **every current template**
    (research / frontend / skill-matters / frontend-test-1 / transcript-matters)
    today carries a baked model in its generated config. So a model IS effectively
    written at launch, inherited from the template. The safe ordering is three
    steps: (1) agent-runtimes makes `generate.py` model-agnostic (their spec §2);
    (2) **re-run `generate.py` on all existing templates** so no stale baked model
    survives anywhere; (3) TM ships `--model` injection. Step (2) is load-bearing:
    regenerating first removes the file-vs-flag precedence question **entirely**,
    rather than leaning on flag-wins-over-file as transition safety. That matters
    because the precedence is verified only for Claude (`--model` overrides
    `settings.json`); **Codex `-m`/`--model` overriding `config.toml`'s `model` is
    UNVERIFIED**. Regenerate-first sidesteps that unknown; if a transition overlap
    is ever required, verifying Codex precedence becomes a hard gate. This ordering
    (agent-runtimes model-agnostic + full template regen BEFORE TM injection) is a
    hard constraint, not an aside.
- **`/model` capture.** Net-new. Capture the CLI's `/model` availability at
  CLI-detection (onboarding) and cache it alongside the CLI-version/first-frame
  facts. The launcher reads the cache; captures lazily if absent. (Shared with
  onboarding — see §6.)
- **List-templates + capability read.** Net-new endpoint (verified: no
  `list_templates` exists in either repo today): enumerate
  `~/.agent-runtimes/runtimes/*` (currently flat: `frontend`, `research`,
  `skill-matters`, `transcript-matters`, …), read each
  `<template>/capabilities.json`, return
  `{name, provider, required_capabilities, recommended_model}` for the cascade.
  Resolution of a single template already exists
  (`api/.../runtime_registry.py::resolve_runtime_template`). Note (review finding,
  Minor): flatness is the current *data shape*, not an enforced contract —
  `runtime_registry.py::_validated_template_name` permits nested relative names
  (covered by `test_resolve_runtime_template_allows_nested_relative_names`). The
  list endpoint must decide whether it enumerates one level or walks the tree; pick
  one explicitly rather than assuming flatness.
- **Frontend cascade.** `www/src/api.ts::createCapturedRun` (extend to send
  `model` + `runtimeTemplate`), `www/src/.../spawn.ts::createCapturedRunRef`,
  `capturedRunStore.ts::ensureRun`, `CapturedRunPane.tsx`,
  `CanvasLabRoute.tsx` (the cascade UI near the spawn affordance). Selection persists
  in the canvas store.

## 6. Onboarding coupling and sequencing: can the launcher ship before the loading flow?

**Yes.** The launcher sits downstream of the loading flow's *outputs*, not its UI.
The loading flow (NOW.md #1, the LOADING/WELCOME path) produces the primitives the
cascade consumes. Provider selection already exists today as the spawn affordance
(§1, the two canvas buttons), so the genuinely onboarding-fed inputs are two: the
captured `/model` data per provider (model ids, display labels, and per-model
efforts), and the declared plan per provider. The loading
flow also produces the CLI-version and first-frame facts the drift baseline needs.
Define the contract those inputs live in now, build the launcher against it with lazy
fallbacks, and the loading flow plugs in later as a richer producer of the same
contract with zero launcher change.

### 6.1 The profile seam (the plug-in point)

A single owned value object, the **capture profile** persisted at
`~/.transport-matters/profile.json`, is the contract between the loading flow
(producer) and the launcher (consumer):

```json
{
  "schema_version": 1,
  "providers": {
    "claude": {
      "cli_version": "...",
      "models": [
        { "id": "claude-opus-4-8", "label": "Opus 4.8", "allowed_efforts": ["low", "medium", "high", "xhigh", "max"] }
      ],
      "models_captured_at": "...",
      "plan": "max5x"
    },
    "codex": {
      "cli_version": "...",
      "models": [
        { "id": "gpt-5.5", "label": "GPT-5.5", "allowed_efforts": ["low", "medium", "high"] }
      ],
      "models_captured_at": "...",
      "plan": null
    }
  }
}
```

The drift baseline (first-frame payload) also lives in onboarding's facts, but the
launcher ignores it; it is not a cascade input.

- The **launcher reads** `providers[p].models` (each `{id, label, allowed_efforts}`)
  and `providers[p].plan`, and never imports onboarding. The effort enum per provider
  is a small stable provider-defined set (TM-owned); `allowed_efforts` is the
  per-model constraint.
- A **capture service** (one new module) populates each field lazily when absent:
  detect installed CLIs on demand (`api/.../capabilities.py::detect_clis` already does
  version/path detection); run the `/model` capture on first cascade open and cache it
  with `models_captured_at` (refreshed per the §2.1 TTL); default plan to `null`
  meaning unknown, which makes the plan filter the identity (consistent with §2.2,
  where plan is orthogonal and informs token optimization only, never the model list).
  An optional lightweight inline plan prompt is allowed but not required for the
  cascade to function.
  - **Capture mechanism (open, wire-first; reframes the earlier "non-interactive"
    note).** Per §2.1, TM captures `/model` from the WIRE rather than scraping the
    interactive picker (the picker shows friendly labels and only the selected entry's
    canonical id, while `--model` needs the canonical id). No `capture_models` exists
    yet; `detect_clis` captures version/path only. The mechanism is an open choice in
    preference order (wire-capture, on-disk cache, PTY-drive, non-interactive flag);
    confirm the cleanest per CLI before the model-layer build. Labeled open on the §5
    precedent (Codex `--model` precedence is similarly unverified). The agent layer
    (provider → agent capability filter) does not depend on this and remains buildable
    regardless.
  - `profile.json` is a **new per-install (global) store**. TM today persists only
    per-run facts (`storage/session_facts.py::RunSessionFacts` via
    `storage/disk_layout.py::sessions_facts_path`); the capture profile is a distinct
    global artifact, not a duplicate of those.
- **Onboarding (the loading flow) becomes the eager, authoritative producer** of the
  same object. It runs detection, the `/model` capture, and the plan prompt up front
  and writes `profile.json`. When it lands, the launcher changes nothing: it already
  reads the object, and onboarding simply fills it earlier and with better UX.

### 6.2 The DRY guard (the one real risk)

The failure mode is building the launcher's lazy capture so that onboarding cannot
reuse it, after which onboarding re-implements detection, `/model`, and the plan
prompt and the two fork. That is exactly the NOW.md warning that #1 and #2 share a
config model and must be built once or they fork. The mitigation is structural: the
capture primitives live in one shared capture module from day one. This module is
**net new** except for CLI detection, which already exists
(`api/.../capabilities.py::detect_clis`, version/path only today, to be extended);
`capture_models` and the plan read/write are net new. The launcher calls them lazily;
onboarding calls the same primitives eagerly with UI. One implementation, two callers,
no duplication. The profile module is the shared kernel both depend on, and neither
depends on the other.

Net: the launcher (slices 3-6) does not block on the loading flow. It blocks only on
the profile contract and the capture module, both small, and both the thing the
loading flow will itself consume.

## 7. v1 scope / deferred (named, not dropped)

- **Deferred to v2:** `vision` capability (reopen when a no-vision tier is offered);
  plan auto-detection from the wire (rides onboarding's first-frame seam if the wire
  proves to reveal tier); the `generated_from` drift-check + `generate.py --check`.
- **Out of scope:** fork/share/eval (the agent-runtimes initiative destination, not
  this phase); the launcher's visual layout (frontend-design pass at build time).

## 8. OPEN STRATEGIC QUESTION — should transport-matters own .agent-runtimes?

This launcher tightly couples two currently-separate repos. The question is whether
they should remain separate bounded contexts behind the §4 seam, or whether TM
should absorb `.agent-runtimes`.

**For TM owning it:**
- The launcher couples them; one config model wanted (NOW.md "build it once or they
  fork").
- This session spent a full cross-agent bus negotiation to align a seam two
  co-located domains could have settled in-process.
- TM already owns the launch path (ephemeral-home Slices 1-4 live in TM).

**Against (keep separate):**
- Distinct domains: `.agent-runtimes` curates config homes (skills/MCP/settings);
  TM is wire-level observability. CLAUDE.md states TM "is orthogonal to the rest of
  the Little Organs stack."
- The §4 seam (capability vocabulary + `capabilities.json`) **decouples** them by
  design — a good contract is the alternative to co-ownership, not a reason for it.
- `.agent-runtimes` serves consumers beyond TM's launcher (it is a general
  runtime-home system); folding it into TM would scope-creep TM and couple those
  other consumers to TM's release cadence.

**Lean (author's, for review to pressure-test):** keep them separate. The clean seam
we designed is precisely what lets them stay separate; the coordination cost we paid
this session was a one-time design cost, not a recurring tax, because the contract is
now stable. But the "one config model" pull is real — if onboarding's capture, the
overlay/config model, and the launcher keep forcing lockstep changes across the repo
boundary, that is the signal to revisit. Decision is Stuart's; this section exists to
get an independent read.

**Peer consensus (both reviewers, independently): KEEP SEPARATE.** Reasoning:
- agent-runtimes' core domain is *curating config homes* (skills/MCP/settings
  materialization) with its own authority (`skill-matters`), its own consumers, and
  a lifecycle independent of any wire observer. TM's core domain is *seeing the
  bytes*. Two genuinely orthogonal bounded contexts.
- The §4 seam is a textbook published-language contract: `capabilities.json` is
  narrow, versioned, one-directional (agent-runtimes emits, TM reads; TM never
  parses frontmatter; `generate.py` never learns the fine matrix). That is
  low-coupling/high-cohesion — the alternative to co-ownership, not a reason for it.
- Absorbing agent-runtimes would couple its *other* consumers to TM's release
  cadence and dilute TM's stated orthogonality invariant (CLAUDE.md).
- The single legitimate pull is the shared **config-capture layer** (onboarding
  capture + overlay model). If THAT keeps forcing lockstep cross-repo edits, the
  capture layer alone is the absorption/extraction candidate — **not** the whole
  repo. The author's "revisit signal" framing is the right trigger.

Recorded decision for v1: separate repos, seam as designed. Revisit only if the
capture layer forces recurring lockstep edits.

## 9. Rough implementation slices (post-approval, indicative only)

1. Shared capability vocabulary registry + `image-generation` entry + coarse
   `providers` projection (cross-repo, tiny).
2. agent-runtimes half: skill frontmatter + `runtime.toml [skills]`+`recommended_model`
   + `generate.py` derivation + `capabilities.json` emission + `[settings.*].model`
   deprecation, **then regenerate all existing templates so no baked model survives
   anywhere** (their repo; this regen is their first implementation slice per their
   spec §9).
3. TM `/model` capture at CLI-detection + cache, with refresh trigger (shared with
   onboarding).
4. TM list-templates + `capabilities.json` read endpoint.
5. TM managed `model` field + `--model` injection through the spawn builder.
   **Hard prerequisite: slice 2 fully done — model-agnostic `generate.py` AND all
   templates regenerated (see §5 sequencing). Not parallel with slice 2.**
6. TM cascade UI (provider → model → agent) in the canvas, selection persistence.
7. Plan prompt + token-optimization wiring (onboarding-adjacent).

Slice 1 unblocks everything; slice 5 **gates on slice 2's full completion (regen
included)**, not parallel; slices 3-4 are TM-internal and parallelizable; 6 depends
on 3-5; 7 is onboarding-adjacent and can trail.

Sequencing (per §6): the launcher (slices 3-6) builds against the **profile seam**,
not the loading-flow UI. Slice 3's `/model` capture lands in a shared capture module
with lazy fallbacks, so the launcher ships before onboarding (slice 7+), which later
becomes the eager producer of the same `profile.json` with no launcher change.

## 10. Bootstrapping: two kinds of agent, two owners

On a fresh `transport-matters` install, `~/.agent-runtimes/runtimes/` may not exist
(the user may not have agent-runtimes installed), and `runtime_registry.py` is
literally a "thin consumer for the external `.agent-runtimes` registry" with no clone
or install hook. The launcher must not hard-depend on it (§8 holds). The clarifying
insight (Stuart): there are **two kinds of agent home, with different owners and
lifecycles**, even though they share one runtime-home format and the §4
`capabilities.json` seam.

- **The fleet (TM productizes; agent-runtimes authors).** A curated set of tuned homes
  that are part of TM's product. agent-runtimes authors and curates the member runtimes
  in `~/.agent-runtimes/runtimes/<name>/` as normal (per §8) and owns the membership
  manifest; TM proposes candidates, then vendors, versions, ships, and surfaces them. On
  a product-install machine that lacks agent-runtimes, the vendored fleet lives under
  TM's own home, `~/.transport-matters/runtimes/` (shipped, read-only), so a fresh
  install is not empty: it has a fleet, because the fleet is the product. On a local dev
  machine the same members resolve directly from `~/.agent-runtimes/runtimes/` and no
  vendoring is involved. (v1 ships a minimal fleet; §11 is where it grows into the
  specialist decomposition fleet.)
- **User curation (agent-runtimes owns).** Homes authored from the user's installed
  skills via skill-matters and `bin/generate.py`, materialized into
  `~/.agent-runtimes/runtimes/`. These are the homes that legitimately degrade to
  "install agent-runtimes to populate."

Same format, same seam, different owner and lifecycle. This dissolves the old
seed-versus-empty dilemma (former §10.1): the seed is the fleet, owned by TM because
it is product. It also **strengthens** §8 rather than threatening it. TM owning a
fleet of internal agents does not absorb agent-runtimes; the format is shared
infrastructure (published language) and ownership splits by purpose.

Consequences for the registry resolver
(`runtime_registry.py::_registry_root`, today a single dir):

- Make it an ordered search path over roots, each carrying declared **provenance**:
  `agent-runtimes` (external user curation, `~/.agent-runtimes/runtimes/`) and
  `tm-fleet` (shipped product, read-only, `~/.transport-matters/runtimes/`).
  Native is the always-present floor.
- TM **never writes into `~/.agent-runtimes/`** (boundary unchanged); it writes only
  its own home.
- **Fleet provenance (RATIFIED with agent-runtimes 2026-06-17, bus `tm-launcher-proposal`).**
  TM must NOT invoke agent-runtimes' `generate.py` at TM build time (a build-time
  cross-repo coupling the locked counterpart spec, "byte-aligned" / "SEPARATE", never
  ratified). The agreed shape:
  - **Membership manifest.** agent-runtimes owns and curates a `tm-fleet` membership
    manifest at its repo root, `~/.agent-runtimes/tm-fleet.toml`
    (e.g. `members = ["codebase-mapper", ...]`). Members are normal runtimes authored in
    `~/.agent-runtimes/runtimes/<name>/` (per §8); the manifest just marks which are
    product-fleet members, keeping personal/test homes (`frontend-test-1`,
    `skill-matters`) out. `generate.py` is untouched (no nesting under `runtimes/`) and
    there is no coupling to `capabilities.json`. TM proposes candidate members;
    agent-runtimes curates the final v1 list.
  - **Portable seed, not built templates (correctness, agent-runtimes finding).** A
    BUILT template is not portable. `capabilities.json` is pure metadata (portable,
    vendor freely), but `.claude.json mcpServers`, `config.toml [mcp_servers.*]`, and
    `skills/` symlinks carry machine-specific ABSOLUTE paths to the author's environment
    (e.g. `config.toml` fmm `command=/Users/.../.cargo/bin/fmm`;
    `skills/codebase-map -> /Users/.../.agents/skills/codebase-map`) and assume those
    binaries + skill bodies exist on the target. Shipped verbatim to another machine, the
    mcp and skills layers break. So the **vendorable seed = `runtime.toml` +
    `capabilities.json`**; machine-specific config is **re-materialized on the target**,
    not shipped. Members are generated with the **model-agnostic `generate.py` (post
    slice-2, §5)** so no baked model survives.
  - **Open TM packaging decision (target-time materialization).** Making the
    re-materialized fleet functional on a target that lacks the author's binaries/skills
    is a TM-side packaging call, scoped to product DISTRIBUTION (moot for a local
    single-machine dev install, where members resolve directly from
    `~/.agent-runtimes/runtimes/`): (a) TM re-materializes mcp/skill paths on the target
    at install time (a target-time generator-EQUIVALENT, distinct from the rejected
    build-time coupling but still a resolution dependency, and a DRY/boundary watch item
    since materialization is agent-runtimes' competence); or (b) TM vendors the skill
    BODIES too and rewrites paths into `~/.transport-matters/runtimes/.../skills` plus
    its own mcp command paths. Decide at the fleet-packaging spec; not blocking the
    launcher cascade.
- Native-only stays the graceful-degradation floor when no root has templates, but
  with a shipped fleet that path is the exception, not the default. This changes only
  what the cascade can offer: empty selection still yields the native home + default
  model, so §1's zero-config fast path is unchanged.

## 11. Track-2 horizon: the fleet as a decomposition engine (vision, not v1)

This section records direction, not v1 scope. It exists so the launcher's design does
not foreclose it.

Product thesis (Stuart): token optimization through **agent decomposition**. Instead
of one long-lived "god" agent accreting context, a director delegates to specialist,
**ephemeral** agents that each perform one task and are then disposed; context is
distributed across the fleet rather than concentrated. This is the killer capability
the launcher's "agent" layer is a first step toward, and the fleet (§10) is the set
of tuned specialists the director draws from.

Most of the substrate already exists, by deliberate design (stepping stones):

- A specialist ephemeral agent that does one task and is disposed **is a per-run
  ephemeral home**: pristine template, injected auth, disposable home, durable history
  in Postgres (ephemeral-home Slices 1-4, merged).
- `RunManager` (`api/.../run_manager.py::RunManager`) is the existing substrate:
  `spawn` / `list` / `attach` / `detach` / `terminate` / `close`, with concurrent runs
  tracked in `_runs` on `app.state`. That substrate is real and need not be rebuilt.
  The director-of-directors on top of it (scheduler semantics, fleet selection,
  fan-out/reap policy, child-run delegation) does **not** exist yet and is OPEN design,
  not an implied extension.
- TM already captures the full wire and transcript across all agents and sessions,
  which is the audit substrate the decomposition layer reads.

The one genuinely new primitive is the **internal bus** (Stuart: "not email"). Open
contract decision, deferred but named so the launcher does not assume it away:

- **Side-channel.** A real message-passing aggregate that agents write to explicitly,
  with its own store and ordering guarantees. Can carry *intent* (a child requests X
  from sibling Y). A new bounded context with its own ownership.
- **Projection over capture.** Derived from the wire/transcript TM already owns;
  agents never address each other, and the director observes their outputs from the
  capture stream. Cheap, because TM owns the data, but it cannot carry intent: only
  emit-and-observe.

Lean (for when this phase opens): the killer-app version needs explicit intent, so a
real channel is likely, with the captured transcript as the audit and replay layer
underneath it rather than the transport itself. Not decided here.

Bearing on v1: none mandatory. The launcher must only avoid designing the "agent"
layer or the run lifecycle around a single foreground run. The `RunManager` seam
already supports multiple concurrent runs, so this is satisfied by not regressing it.
