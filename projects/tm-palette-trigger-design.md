# Palette launch verification trigger: design decision

Slice A2. Report only. No code, no repo writes.

## Verdict

Neither A nor B. Both name a model string that the resolver cannot match against the
operator's actual target observations, and both fail on the same harness for the same
reason. I recommend **design C: read the model out of the harness home the launch will
actually use**, and use it only to name the verification cell, never to actuate the launch.

A declared `recommended_model` is **advisory, and today it is also factually wrong**. It is
not authoritative, and it is not made authoritative by anything in the launch path. The
config file inside the launch home is authoritative, because it is the only input the
harness reads when Transport Matters sends no `--model`.

Size: **about 160 production lines across 3 files (1 new, 2 edited)**, plus about 250 lines
of tests. Roughly one third of codex's 300 to 500 for A, with no registry, no notification
path, no race recovery and no orphan cleanup.

## Inspection boundary

Branch `main`, head `63391ae9` ("Gate automatic capture spending (#441)"). The tree was
pristine when this investigation began and every observation below was read at that commit.
By the time of writing codex had begun editing, and the modified set is exactly the timing
audit's target list (`.github/workflows/ci.yml`, `api/pyproject.toml`, ten timing test
files, `api/uv.lock`). None of it touches anything cited here, and I made no writes to the
repository.

Read: `www/packages/canvas/src/launcher/commandTypes.ts`, `templateRows.ts`,
`www/packages/core/src/types/runtimeTemplates.ts`, `api/src/transport_matters/`
(`verification_cell.py`, `harnesses/launch_target.py`, `harnesses/resolver.py`,
`harnesses/resolver_targets.py`, `harnesses/resolver_snapshots.py`, `runtime_templates.py`,
`runtime_registry.py`, `baseline_capture.py`, `baseline_evidence.py`, `baseline_store.py`,
`request_inventory.py`, `ir.py`, `launch_verification.py`, `api/v1/capture_rpc_routes.py`,
`api/v1/launch_verification_routes.py`, `cli/runtime_home.py`, `cli/home_seeders.py`,
`cli/home_overlay.py`, `cli/home_constants.py`, `cli/launch_profile.py`,
`launch/environment.py`), `harnesses/compatibility_releases_v1.json`, the operator's
`~/.agent-runtimes` tree, and `~/.claude`, `~/.codex`, `~/.grok` configs.

Queried read only: the `transport_matters_preview` database
(`harness_target_observation`), and the three stored baseline bundles under
`~/.transport-matters-preview/baselines/`. I decoded `raw_request_base64` from each bundle
to read the true wire body.

## 1. Is a declared `recommended_model` authoritative? No.

Six findings, in descending force.

### 1.1 The declared string is not an observed selector, so it does not resolve

`matching_offered_targets` (`harnesses/resolver_targets.py`) matches a model id against
`observation.native_model_id` first and `canonical_model_id` second. Nothing else.

The operator's live claude observations at the installed version 2.1.241 are aliases only:

    best, default, fable, fable[1m], haiku, opus, opus[1m], opusplan, sonnet, sonnet[1m]

Six templates (`frontend`, `generalist`, `orchestrator`, `research`, `skill-matters`,
`transcript-matters`) declare `"model": "claude-opus-5[1m]"` for anthropic. That string is
not in the observation set. The observed form is `opus[1m]`. So the declaration cannot name
a target through the existing matcher, and B does not reach a cell for claude at all.

Codex and grok happen to agree (`gpt-5.6-sol`, `grok-4.6` are both observed). The
disagreement is exactly on the harness with alias fan out.

### 1.2 The declaration is frequently absent

`_default_target` in `runtime_registry.py` reads `recommended_model.by_vendor[vendor].model`
and passes `None` straight through when the vendor block is missing or carries only
`effort`. Live: `tm/capture` declares `default.harness = "claude"` but has no `anthropic`
entry under `by_vendor`, so its claude model is `None`. `tm/codebase-mapper` declares
`anthropic: {effort: "xhigh"}` with no model.

`tm/capture`'s own `runtime.toml` says why, in a comment: "The capture plan supplies
harness, model, and effort per probe, so its explicit launch flags override this catalog
recommendation." The file states its own advisory status.

A key that may be absent by design cannot be the authority for a key that must be present.

### 1.3 The palette's primary rows have no template at all

`agentSpawnRows` in `www/packages/canvas/src/launcher/templateRows.ts` builds native rows
first, from `CAPTURED_RUN_PROVIDERS`, and calls `spawnCommand(harness, worktreeId)` with no
`agentId`. Templates come after, with `spawnCommand(harness, worktreeId, template.id, ...)`.

A native row carries no template, so it has no `capabilities.json` and no
`recommended_model`. B structurally cannot serve the three rows the palette shows first, and
the operator's three captured cells are exactly claude, codex and grok.

### 1.4 Nothing in the launch path sends the declaration

`templateSpawnHarness` reads `template.default_target?.harness` and discards the model.
`LauncherCommand` of kind `spawn` in `commandTypes.ts` has fields `harness`, `agentId`,
`name`, `suppressTerminalAutofocus`, `worktreeId`. No model.

The palette even displays the model it will not send: `recommendedSubtitle` renders
`<model> · <effort> · <Vendor>` from `default_target`, so the `generalist` row reads
"claude-opus-5[1m] · high · Anthropic" while its command carries `harness: "claude"` alone.
That is the declaration and actuation gap, already visible in the UI.

Downstream, `_model_argv` in `cli/launch_profile.py` is
`[] if model is None else ["--model", model]`. A palette launch emits no flag.

### 1.5 The resolver already has the declared preference path, and it is already inert

`ResolverSnapshots.agent_recommendation` and `agent_tested_default`
(`harnesses/resolver.py`) feed `_preference_edge`, which is the declared preference
mechanism B would need. Two facts kill it:

- `resolver_snapshots_for_harness` (`harnesses/resolver_snapshots.py`) never populates
  either field, and `kind="agent"` appears nowhere in production. The capture route builds
  `ResolverRequest(kind="native", ...)`. The branch is reachable only from tests.
- `_preference_edge` ends with `if not _default_eligible(target): return None`, and
  `_default_eligible` requires `support_tier == "tested"`. Every target in
  `harnesses/compatibility_releases_v1.json` is `observed_unverified` across all three
  releases. Populating the field would still return `None`.

So the declared preference machinery exists, is wired, and produces nothing. B is a
proposal to revive a dead path into the same gate that is already closed.

### 1.6 The harness can and does launch something other than the declaration

The orchestrator's test is whether a harness can launch something other than the declared
default. It can, trivially, because the declaration is never sent and the harness reads its
own config. It is not a hypothetical: for claude the declared `claude-opus-5[1m]` and the
configured `opus` are different selectors that a launch would key differently.

Keying a bundle on a declaration would file evidence under `claude-opus-5[1m]` for a turn
that ran `opus`. That is the data corruption the guess prohibition exists to prevent, with
one extra insult: the wrong key would look deliberate, because a file declared it.

## 2. Why design A also misses, on the same harness

A reads `RequestCaptureProvenance.model`, built in `baseline_capture._build_probe_evidence`
from `captured.request_ir.model`. That is the wire model, and Transport Matters already
knows it is a different thing from the launch model. `BaselineCell` in
`baseline_evidence.py` carries **both** `launch_model` and `wire_model` as separate required
fields, and `harvest_controlled_baseline` cross checks that the three probes observed one
`wire_model` before it builds the cell.

The operator's three live bundles:

| harness | `launch_model` | `wire_model` | raw wire `model` |
| --- | --- | --- | --- |
| claude | `opus` | `anthropic/claude-opus-5` | `claude-opus-5` |
| codex | `gpt-5.6-sol` | `codex/gpt-5.6-sol` | `gpt-5.6-sol` |
| grok | `grok-4.6` | `grok/grok-4.6` | `grok-4.6` |

Three consequences.

**A2.1 The store keys on `launch_model`, not the wire model.** `_bundle_path` and
`_write_current` in `baseline_store.py` both build the path from `bundle.cell.launch_model`.
A bundle keyed by wire model lands under `claude-opus-5`, which
`assess_baseline_staleness` will never look up for any future launch. It is write only
evidence unless the entire store is re-keyed, which is far past 500 lines.

**A2.2 The wire model is not a launch selector.** `harvest_controlled_baseline` launches
three probes and needs a selector the harness accepts and the resolver matches.
`claude-opus-5` is in neither the observation set nor the catalog. `matching_offered_targets`
returns empty, and the resolution is `target_unavailable / not_observed`.

**A2.3 The wire model is strictly less information than the cell.** `opus`, `opus[1m]`,
`opusplan`, `best` and `default` are five distinct observed selectors that can all resolve
on the wire to `claude-opus-5`. Given the wire model you cannot recover which one ran. The
mapping is many to one and not invertible, so wire provenance cannot identify a cell even in
principle.

A is genuine evidence of what ran. It is evidence at the wrong granularity, in the wrong
namespace, arriving after the point where the key is needed. Its 300 to 500 lines buy a
string that then has to be reverse mapped to a selector by a table that does not exist.

## 3. Design C: the config in the home the launch will read

When `--model` is absent, exactly one input decides the model: the config file in the home
the harness starts with. Reading it is not a guess and not a declaration. It is reading the
same bytes the harness reads, before it reads them.

Live, on this machine:

| harness | file and key | value | observed selector | existing bundle key |
| --- | --- | --- | --- | --- |
| claude | `~/.claude/settings.json` `model` | `opus` | `opus` | `opus` |
| codex | `~/.codex/config.toml` `model` | `gpt-5.6-sol` | `gpt-5.6-sol` | `gpt-5.6-sol` |
| grok | `~/.grok/config.toml` `[models] default` | `grok-4.6` | `grok-4.6` | `grok-4.6` |

Three for three, exact string equality with both the observed target and the bundle key the
operator's explicit launches already produced. No prefix stripping, no alias table, no
normalization. The claude effort agrees too: `settings.json` `effortLevel` is `high`, and
the `opus` observation carries `native_efforts` `["low","medium","high","xhigh","max"]`, so
the resolver's per model effort gate accepts it.

### Which home

`plan_runtime_home` in `cli/runtime_home.py` already owns the precedence and yields
`RuntimeHomePlan.content_source` with a `RuntimeHomeMode`: manual `home_dir` wins, then
`runtime_template.template_home`, then `resolve_native_harness_home`
(`launch/environment.py`). That ordering is the answer, and it must not be restated
anywhere.

There is no merge to replicate. `materialize_runtime_home_template_overlay`
(`cli/home_overlay.py`) symlinks template content entries from the template home only, so a
template launch's overlay contains the template's `settings.json` and nothing of the
operator's. `materialize_runtime_home_overlay` symlinks the operator's source home for a
native launch. One home, one config file, no precedence inside the file.

Verified against the templates: `generalist/settings.json` carries
`"model": "claude-opus-5[1m]"` and `generalist/config.toml` carries `model = "gpt-5.6-sol"`,
both generated from `generalist/runtime.toml` `[recommended_model]`. `tm-capture` carries
neither, matching its declared intent to leave the model to explicit probe flags.

That last point is worth stating plainly, because it reframes B rather than dismissing it:
for a template launch the declaration and the actuation share one generator source, so they
usually agree. C reads the generated artifact the harness consumes instead of the sibling
artifact nobody consumes. Where they agree, C is B with a correct reader. Where they
disagree, C is right and B is wrong, and today they disagree on claude.

### Where it goes

Read the model only to name the cell. The launch keeps actuating `None`. This preserves the
contract `verification_cell.py` states in its own docstring: "A CMDK launch sends no model at
all, and `None` there is valid actuation rather than a gap ... So the cell is an
*observation* of what that actuation resolves to, never a substitute for it."

The seam already exists. `_launch_verification_cell` in `harnesses/launch_target.py` already
re-resolves a modified request purely to name a cell, for the `target_unverified_opt_in_required`
case #440 added. C extends that same function with one more replay: when the strict
resolution yields no cell because no model was named, replay with the configured model and
`allow_unverified_target=True`. The strict resolution stays the sole launch authority, which
is what that module's docstring already promises.

Call site: `capture_rpc_routes` prepare, where `resolve_launch_target_views` is called with
`model_id=domain.model` and `snapshots` are already in hand. `CapturedRunRequest` already
carries `home_dir`, `runtime_template` and `isolated_home`, so no new field is needed on the
domain object and no second database read is added.

### Failure modes, all soft

- No config file, or no model key: no configured model, so no replay, so `NoVerificationCell`
  exactly as today. `tm/capture` on claude lands here, correctly.
- Configured model is not an observed selector: the replay rejects and the cell stays
  `NoVerificationCell`. A stale or hand edited config cannot produce a wrong key.
- Configured effort invalid for that model: degrade effort to `None` and keep the cell.
  Losing the whole cell over an effort string would be a worse trade.
- Unreadable or malformed config: log and treat as absent. Never raise into prepare.

Nothing here can write a bundle under a model that did not run, because the only strings
that survive are ones the observation set already contains.

## 4. Is a hybrid right?

No, and specifically: **the hybrid is larger than A, not smaller.**

The proposed hybrid is "declare intent from capabilities, confirm or correct from wire
provenance before the bundle is keyed". It needs every part of A (the pending run registry,
the wire notification hop, the post commit lookup, the race recovery, the orphan cleanup)
**plus** a comparator between a declaration and a wire model. On the operator's live data
that comparator would be asked whether `claude-opus-5[1m]` and `anthropic/claude-opus-5`
describe the same cell. They are not equal, neither is an observed selector, and no
normalization table exists to relate them. Building one is the alias mapping that section
2.3 shows is not invertible.

A hybrid of two sources that are each wrong in the same place does not become right. It
becomes A plus a table.

There is a real hybrid, and C already is it: declared intent lives in `runtime.toml`, the
generator materializes it into the home, and C confirms it against the observation set
before it is allowed to name a cell. The confirmation step is `matching_offered_targets`,
which exists.

## 5. Size

Comparable basis to codex's 300 to 500 production lines for A.

| item | file | lines |
| --- | --- | --- |
| Extract the content home selection out of `plan_runtime_home` into `launch/environment` so both callers share it | `cli/runtime_home.py`, `launch/environment.py` | ~25 moved, 0 net new |
| New leaf: read model and effort from a home, per harness | new `configured_launch_model.py` at package root | ~110 |
| Second replay in `_launch_verification_cell`, optional `configured_model` parameter | `harnesses/launch_target.py` | ~30 |
| Resolve the home and pass the configured model at prepare | `api/v1/capture_rpc_routes.py` | ~18 |
| **Production total** | **3 files edited, 1 new** | **~160** |
| Reader unit tests, three harnesses, present / absent / malformed | new `test_configured_launch_model.py` | ~140 |
| Replay tests, including the "no configured model leaves NoVerificationCell" guard | `harnesses/test_launch_target.py` | ~60 |
| Route test: `model=None` prepare yields a `VerificationCell` | capture route tests | ~50 |
| **Test total** | | **~250** |

Reuse rather than new code: `tomllib` is already imported in `cli/home_overlay.py`,
`cli/grok_home.py` and `cli/toml_edit.py`; `home_io._read_json_object_if_exists` already
reads a JSON home file defensively. The new leaf should call those, not re-open files.

Placement note. The leaf sits at the package root, not under `cli/` and not under
`harnesses/`, for the reason `verification_cell.py` gives for its own placement: the
harness resolver, the capture route and the home planner all touch it and none owns it. The
API layer imports nothing from `cli/` today and this must not be the first exception, which
is why the home selection moves to `launch/environment.py` rather than being imported from
`cli/runtime_home.py`.

## 6. The owner's open question: which artifact is the right home?

**Neither. Create no `capabilities.json` for the default homes, and add no section to the
root `capabilities.toml`.**

Against a `capabilities.json` for `~/.claude`, `~/.codex`, `~/.grok`: `~/.claude/settings.json`
already carries `"model": "opus"`, and claude reads it. A second file declaring the same fact
in a file no harness reads is precisely the declaration and actuation gap that makes B
unsafe. It would be a copy that can drift, and the drift would be invisible until a bundle
landed under the wrong key. It also fails the DRY rule outright: one fact, two homes, no
shared owner.

Against extending the root `capabilities.toml`: its own header says capabilities are
"a VENDOR fact: any harness (claude/codex/opencode/pi) driving that vendor's model gets
it", coarse and not harness keyed. A default launch model is the opposite on every axis. It
is harness keyed, home keyed, and it is a preference rather than an existence claim. The
owner's remit over the content is not in question; the vocabulary is. Putting a per harness
per home preference into a vendor keyed existence file would corrupt the one property that
makes that file cheap to reason about.

The parked question dissolves rather than resolves: the default homes already declare their
model, in the file that decides the outcome. Nothing needs to be created.

One coupling to note, since it cuts the other way. Template homes keep `recommended_model`
in `capabilities.json` and that stays correct, because it is generated from `runtime.toml`
alongside the home's own `settings.json` and `config.toml`. C reads the generated home
config, so the template case needs no schema change either. Consistent with
`docs/HARNESS-COMPATIBILITY.md`, none of this touches the global tested catalog: C only
selects among targets the local observation set already contains, and writes local evidence.

The `capabilities.json` forward compatibility rule is respected trivially. C reads no new
key from it, so no `schema_version` bump is implied and no consumer must change.

## 7. What I would not build

1. **No `capabilities.json` for the operator's default homes.** Section 6.
2. **No new section in the root `capabilities.toml`.** Section 6.
3. **No actuation of the configured model as a `--model` flag.** It would pin a model the
   operator did not choose, change observable launch behaviour to serve a bookkeeping goal,
   and break the "`None` is valid actuation" contract in `verification_cell.py`. C reads the
   config; it does not start sending it.
4. **No pending run registry, no wire notification hop, no post commit model lookup, no
   registration race recovery, no orphan cleanup.** The whole of A. It buys a wire model that
   section 2 shows cannot key a cell.
5. **No re-keying of the baseline store onto `wire_model`.** `_bundle_path` and
   `_write_current` stay on `launch_model`. `wire_model` remains what it is today: recorded
   evidence of what the wire carried, not an index.
6. **No wire model to selector alias table.** Many to one, not invertible, and it would need
   maintenance on every harness release.
7. **No population of `ResolverSnapshots.agent_recommendation`.** Section 1.5. It is gated on
   `support_tier == "tested"` and would stay inert. Whether that dead branch should be
   deleted is a separate question and not part of A2.
8. **No relaxation of `_default_eligible`.** Making `observed_unverified` default eligible
   would change which targets a launch resolves to, for every caller, to fix a verification
   trigger. Wrong blast radius. The replay with `allow_unverified_target=True` already opens
   exactly the one gate that needs opening, for the one resolution that only names a cell.
9. **No third capture path.** C produces a `VerificationCell` and hands it to the existing
   `LaunchVerificationCoordinator.submit`, which since #441 already gates spend by range
   position. Palette launches inherit that gate at no cost.

## 8. Open decisions

1. **Effort.** I recommend reading effort alongside the model (`effortLevel`,
   `model_reasoning_effort`, `[models] default_reasoning_effort`) and degrading to `None`
   when the per model vocabulary rejects it. The alternative is always `None`, which is
   simpler but files the cell under a tuple the launch did not exercise when the config sets
   a non default effort. Owner's call; I would take the read.
2. **Manual `home_dir` launches.** `RuntimeHomeMode.MANUAL` points at an arbitrary operator
   directory. C reads it the same way, which is correct but means a cell can be named from a
   directory Transport Matters does not own. I see no harm, since the observation gate still
   applies. Worth an explicit yes.
3. **Whether to surface the configured model in the launch view.** The palette already shows
   `default_target.model` for templates, and that string is the one C proves can be wrong.
   Showing the configured model instead would make the row honest. Out of A2's scope, and it
   overlaps the surfacing work deferred as M3.
