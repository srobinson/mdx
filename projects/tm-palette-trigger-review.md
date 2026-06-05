# Adversarial review: palette verification trigger

Target `fix/palette-verification-trigger` head `7bb9da91`, against `origin/main` `7a2ac8c5`.
16 files, 750 insertions. Read only.

**1 major, 6 minor. MERGE once the major is fixed.**
**The home refactor changes no launch's resolved home.** Verified by line by line equivalence
and by the full `cli/` suite, which covers home materialization for all three harnesses.

## Inspection boundary

Tree pristine throughout: `git status --porcelain` empty at start and at finish, branch
`fix/palette-verification-trigger`, head `7bb9da91`. No writes, no checkout, no stash. The
seven pre-existing stash entries are old and none is mine.

Ran read only: the full backend suite (`4131 passed in 48.75s`, matching the builder's
count), the affected subset plus the whole `cli/` tree (`585 passed`), the new reader
against the operator's three real homes, eleven constructed failure cases in the scratchpad,
`assess_baseline_staleness` against the live preview store, and one direct exercise of the
prepare route helper to settle the passthrough question. Scratch fixtures were written only
under the session scratchpad.

## What is correct, proven rather than accepted

### Hunt 1: cell naming only, never actuated. Holds.

Three independent proofs, none of them a reading of intent.

`resolve_launch_target_views` in `harnesses/launch_target.py` returns the strict `resolution`
computed before any replay. `_launch_verification_cell` rebinds only its own parameter, and
it builds the replay with `request.model_copy`, so the caller's `ResolverRequest` is never
mutated. `test_configured_target_replaces_a_different_observational_default` pins both
halves: `resolution.resolved.model_id == MODEL` while the cell names the configured
`claude-sonnet-5`, and `request.model_id is None` after the call.

At the route, `_resolve_launch_target` in `api/v1/capture_rpc_routes.py` still does
`model, effort = domain.model, domain.effort` and enters `launch_target_advisory` only when
one of them is set. A palette prepare leaves both `None`, so `replace(domain, model=None,
...)` is what reaches the spawn. `_model_argv` in `cli/launch_profile.py` is
`[] if model is None else ["--model", model]`, so no flag is emitted.

Executed: the flipped `#440` test asserts `(domain.model, domain.effort) == (None, None)`
in the same breath as the new `VerificationCell`. I also ran the route helper directly and
saw an explicit launch keep `model=claude-opus-4-8` unchanged.

`assess_provider_access` receives the original `resolver_request`, so provider access is
untouched by the configured selector as well.

The configured model does reach a harness, but only the probe harness that
`harvest_controlled_baseline` launches. That is the point of the feature, not a leak.

### Hunt 2: the `cli/home_*` refactor. No launch resolves a different home.

`resolve_launch_content_home` in `launch/environment.py` reproduces the branch that was
inline in `plan_runtime_home`. Checked case by case:

- `native_home`. Was `resolve_source_home_dir(harness, home_dir=None, env=env)`, which falls
  straight through to `resolve_native_harness_home` when `home_dir` is `None`. Now
  `resolve_native_harness_home` directly. The only behavioural difference would be the guard
  set, `_SEEDERS_BY_HARNESS` against `HOME_DIR_ENV_BY_HARNESS`. `_SEEDERS` is
  `(ClaudeSeeder(), CodexSeeder(), GrokSeeder())` and `HOME_DIR_ENV_BY_HARNESS` is keyed on
  the same three. Identical sets, both raise `ValueError`. No change.
- `env=None` handling is identical, both resolve `os.environ` internally.
- Precedence. Manual, then template, then native, in that order, in both versions.
- `manual_home`. Was `home_dir.expanduser() if home_dir is not None else None`. Now
  `content_source if mode == MANUAL else None`, which is the same value.
- Template content source. Was `validated_template.template_home.expanduser()`, now
  `runtime_template.template_home.expanduser()`. `_validated_template` in
  `cli/runtime_home.py` is a pure guard that returns its argument unchanged, so these are
  the same path. Validation still runs before `plan_runtime_home` returns, and it still does
  not run in manual mode, exactly as before.
- Everything downstream of the branch (`should_overlay`, `_runtime_child_home`,
  `descriptor_home`, `auth_source`) is untouched and reads the same three values.

The `GROK_HOME` and `CODEX_HOME` redirect risk is covered directly:
`launch/test_environment_home.py::test_native_content_home_honors_harness_redirect`
parametrizes all three env keys and asserts the redirected home is what comes back.

`atomic_io.read_json_object_if_exists` is a verbatim move of
`home_io._read_json_object_if_exists`, body unchanged. `claude_home.py` is call site renames
only. `home_constants.py` rebinds its two filename constants to imported values with the
same strings. Nothing in the diff alters a path a harness starts from.

### Hunt 3: key fidelity. Exact, three for three, live.

Ran the reader against the operator's real homes:

| harness | resolved file | model | existing bundle key |
| --- | --- | --- | --- |
| claude | `~/.claude/settings.json` | `opus` | `bundles/claude/anthropic/opus/` |
| codex | `~/.codex/config.toml` | `gpt-5.6-sol` | `bundles/codex/codex/gpt-5.6-sol/` |
| grok | `~/.grok/config.toml` | `grok-4.6` | `bundles/grok/grok/grok-4.6/` |

There is no normalization to scrutinise, which is the right answer: `_string` returns the
raw value and every downstream check is exact equality inside `matching_offered_targets`. A
selector that does not match an observation yields no cell rather than a coerced one, proved
by `test_configured_unknown_model_cannot_name_a_cell`. The store cannot fork.

### Hunt 4: absence. Eleven paths, all yield no cell.

Constructed and executed: missing home, missing file, no model key, malformed JSON,
malformed TOML, model as an integer, JSON that is a list rather than an object, model as
whitespace, a directory where `settings.json` should be, and an unmapped harness. Every one
returned `None`. The qualified `config.codex.toml` correctly won over `config.toml` in the
one case where both exist.

`read_configured_launch_model` catches `FileNotFoundError` silently and `OSError, ValueError`
with a warning, and `IsADirectoryError` arrives as an `OSError` so the directory case is
covered rather than accidentally uncaught. No invented default exists anywhere in the module.

### Hunt 5: no re-capture. Confirmed against the live store.

`assess_baseline_staleness` against `~/.transport-matters-preview/baselines`:

    claude opus        -> current  2.1.241
    codex  gpt-5.6-sol -> current  0.149.0
    grok   grok-4.6    -> current  1.0.5

All three are `current`, so the cells this branch now names for palette launches resolve to
stored evidence and spend nothing. The `#441` range position gate sits ahead of that inside
`_run_candidate` and is unchanged.

### Hunt 6: test honesty. The gap test genuinely flips.

`test_palette_unverified_catalog_cannot_name_a_cell_at_prepare` asserted
`NoVerificationCell(reason="target_unavailable")` and `not coordinator.submit(...)`. It is
now `test_palette_unverified_catalog_names_configured_cell_and_submits`, asserting a
`VerificationCell` and an accepted submit. The assertions are inverted, so the new form
cannot pass on `main`. That is the observable end state, not an intermediate mapping: it
checks the cell the operator's launch produces and that scheduling accepts it.

The injected `AcceptingTasks` counts `submitted == 1`, which pins that the coroutine really
reached `tasks.submit` rather than the method returning early through its blanket
`except Exception: return False`. Worth stating plainly: the test closes the coroutine, so
it does not re-prove `#441`'s spend gate, which lives inside `_run_candidate`. That is the
right division and not a gap.

The three new test modules import symbols that do not exist on `main`, so they cannot have
passed before.

## Major

### M1. Any passthrough discards a correct cell, regressing `#440`

`api/v1/capture_rpc_routes._resolve_launch_target` ends the new block with

    if domain.client_disabled or domain.passthrough:
        verification = NoVerificationCell(reason="target_unavailable")

This is unconditional on `domain.model`. It runs after `resolve_launch_target_views` has
already produced a correct cell and throws that cell away.

Executed against the branch, with the same helper the route tests use:

    explicit model + benign passthrough -> model= claude-opus-4-8 | cell= NoVerificationCell(reason='target_unavailable')
    explicit model, no passthrough      -> model= claude-opus-4-8 | cell= VerificationCell(harness='claude', model='claude-opus-4-8', effort=None)

The passthrough was `("--resume", "abc123")`. It carries no model. Transport Matters emits
`--model claude-opus-4-8` itself and knows exactly what will run, and the response says so
in the same object. The cell is discarded anyway.

The guard's intent is sound and it fixes a real corruption path: a passthrough
`--model claude-sonnet-5` would override the flag TM emits, so an explicit launch could file
evidence under the wrong key. `test_passthrough_capture_does_not_infer_a_cell_from_home_config`
covers exactly that case, and it should keep passing. The defect is breadth. Every
passthrough is treated as if it carried a model, so `--resume`, a prompt, or any user flag
silently removes verification from a launch that shipped working in `#440`.

This is out of the briefed scope and was not asked for. It is safe in direction, so it is not
a blocker, but it narrows shipped behaviour without saying so.

Fix: scope the suppression to the case it is for. Either restrict it to
`domain.model is None`, so an explicit launch keeps the cell it earned, or scan the
passthrough for a model selector the way `LaunchProfile.user_supplied_session` in
`cli/launch_profile.py` already scans it for session flags, including the `--flag=value`
form. The second is more precise and reuses an established pattern in the same module.

## Minor

### m1. Both deliberate skips report `target_unavailable`, which is false

The same line reports `reason="target_unavailable"` for two decisions that are not
resolution failures. In the case above the target is available and named in the same
response. An operator or a log reader is told the resolver could not find a target when the
resolver found one and the route chose not to use it.

`NoVerificationCell.reason` is typed `ResolutionRejectionCode | Literal["verification_replay_failed"]`,
so the codebase already has the pattern for a non resolver reason. Add one that says what
happened, and give the proxy only case its own, since "the client is disabled" and "the
launch carries arguments we cannot attribute" are different facts.

### m2. `_config_source_name` now answers a different question than it asks

`cli/home_overlay._config_source_name` delegates to
`configured_launch_model.resolve_launch_config_path`. Those two resolve different things.
`_config_source_name` asks which TOML config a home holds; `resolve_launch_config_path` asks
which file carries the model, and for claude that is `settings.json`. They agree for codex
and grok and diverge for claude.

Unreachable today: the only call site sits inside `if harness in {HARNESS_NAME_CODEX,
HARNESS_NAME_GROK}` and claude returns earlier. But the function's own docstring still says
"Name the file a ``config.toml`` harness is seeded from", and the body can now return
`settings.json`. Before the change it returned the shared TOML name for any harness. This is
a latent trap in the seeding path, held shut by one caller's guard.

Give the two questions two functions, or make `_config_source_name` reject non TOML
harnesses explicitly rather than silently returning a JSON filename.

### m3. `resolve_source_home_dir` is dead and still present

`cli/home_seeders.resolve_source_home_dir` has zero callers. The only three references in
the tree are its definition, its import in `cli/home_seed.py`, and its `__all__` entry. The
refactor moved the live path to `resolve_launch_content_home` and left the old one standing.
Delete it and its re-export.

### m4. `_string` tests the stripped value and returns the unstripped one

`configured_launch_model._string` rejects blanks with `not value.strip()` but returns
`value`. Confirmed: `_string("  opus  ")` returns `"  opus  "`. It cannot produce a wrong
key, since the resolver rejects the padded form and the launch yields no cell, but a config
with stray whitespace silently loses verification for a reason nothing reports. Return the
stripped value.

### m5. The home layer now imports its own filenames from a consumer

`cli/home_constants.py` imports `CLAUDE_SETTINGS_FILENAME`, `TOML_CONFIG_FILENAME` and
`qualified_config_filename` from `configured_launch_model`, then rebinds two of them to its
own private names. Home layout is `home_constants`'s subject and `configured_launch_model`
is a reader of it, so ownership is inverted. There is no import cycle, and the strings are
unchanged, so this is placement rather than behaviour. The constants belong in the home
layer with the reader importing them, which is also the direction that makes m2 go away.

### m6. Configured effort reaches the probes, and the store cannot tell efforts apart

The configured effort flows into `VerificationCell.effort`, then into
`harvest_controlled_baseline`, which validates it against `selected.effort_options` and sets
`default_effort`, which `_capture_probe` actuates. `BaselineCell` in `baseline_evidence.py`
records no effort, and `_bundle_path` and `_write_current` key on harness, provider and
`launch_model` only. Two captures of one cell at different efforts are indistinguishable in
the store and each replaces the other's current pointer.

The conflation is pre-existing, introduced when cells gained an effort that artifacts never
carried. This branch is the first to source that effort from a file rather than from
something the operator typed: the live `~/.claude/settings.json` sets `effortLevel: high`
and `~/.grok/config.toml` sets `default_reasoning_effort = "xhigh"`. Reasoning parameters can
move the request structure the gate compares, so a silent effort change is not only a
bookkeeping question.

Recording effort in `BaselineCell` is the honest fix and costs a
`BaselineArtifactSchemaVersion` bump. Dropping effort from the configured replay is the
cheap one and makes the cell less faithful to the launch. I would take the bump, and it is
reasonably a separate change from this one. Flagging it here because this branch is what
makes it reachable.

## Note, not a finding

The branch carries `7d35bdb9` ("ci: report slowest backend tests"), which adds
`--durations=25` to the backend job. It is a clean separate commit and a follow up to the
timing audit rather than part of this design, but it is in the diff the review targets.

## Verdict

**MERGE after M1.** The load bearing property holds under three independent proofs, the home
refactor is behaviour preserving, the keys are exact against the operator's live store and
bundles, every absence path fails closed, and no live cell re-captures. M1 is a five line
narrowing of a guard that is right in intent and too wide in reach. The six minors are the
kind this project does not defer: m2 and m5 are one shared cause, m3 is a deleted path left
standing, and m6 is the open decision from the design surfacing as a concrete gap.

---

# Delta re-review 0543ec77

`git diff 7bb9da91 0543ec77`, one commit "fix: preserve verification cell identity", 24
files, 332 insertions.

**0 major, 4 minor. MERGE.**
**Nothing in this delta falls outside the guard fix and my six minors.**
**Home certification renewed: no launch resolves a different home, and no home is seeded
differently. The delta strictly improves on `7bb9da91` here.**

Tree pristine at start and finish, head `0543ec77`. No writes, no checkout, no stash. Full
suite `4137 passed in 47.90s`.

## 1. Scope, per file

Every file maps to the guard fix or to one of the six minors. Nothing is unaccounted for.

| file | belongs to |
| --- | --- |
| `api/v1/capture_rpc_routes.py`, `verification_cell.py`, `api/v1/test_capture_rpc_verification_cell.py` | M1 guard fix and m1 reason codes |
| `configured_launch_model.py`, `cli/home_constants.py`, `cli/home_overlay.py`, `test_configured_launch_model.py` | m2 overloaded resolver, m4 unstripped `_string`, m5 placement inversion |
| `cli/home_seed.py`, `cli/home_seeders.py`, `cli/test_home_seed.py` | m3 dead `resolve_source_home_dir`, plus the m2 regression test |
| `baseline_evidence.py`, `baseline_store.py`, `baseline_attempts.py`, `baseline_capture.py`, `baseline_harvest.py`, `baseline_comparison.py`, `baseline_staleness.py`, `launch_verification.py` and their tests | m6 effort as a stored cell coordinate |

The 122 lines in `baseline_store.py` are m6 and nothing else. m6 was the one minor that could
not be small: making effort a coordinate means the artifact version, the cell, the current
pointer, the attempt record, the cohort key, the lock domain and the workspace all have to
agree, and legacy evidence has to keep reading.

### Does anything change a stored shape, a schema version, or a reader's tolerance? Yes, all three.

- `BaselineCell` gains `effort: str | None`, `BaselineArtifactSchemaVersion` goes `9` to `10`,
  and `PREVIOUS_BASELINE_ARTIFACT_SCHEMA_VERSION = 8` becomes
  `LEGACY_BASELINE_ARTIFACT_SCHEMA_VERSIONS = frozenset({8, 9})`.
- `BaselinePointerSchemaVersion` goes `5` to `6`, with a new
  `PREVIOUS_BASELINE_POINTER_SCHEMA_VERSION = 5`.
- `_current_path` forks: effort `None` keeps `<model>.json`, a real effort writes
  `<model>/<effort>.json`. `_bundle_path` is untouched, so bundles stay in one directory per
  model and are separated by their `cell.effort` field instead.
- `baseline_attempt_path` inserts an effort directory when effort is set.
- `read_current_baseline_refs` moves from `glob` to `rglob` so the nested pointers enumerate.

### Would any of the operator's live artifacts become unreadable? No. Verified live.

Every one of the operator's stored artifacts is version 8 (three bundles, three attempt
records); the three current pointers are version 5. All are in the accepted legacy sets.

Ran against the real preview store, using the efforts the reader actually produces for those
homes (`high`, `high`, `xhigh`):

    claude  opus         effort=high   staleness=current  durable_evidence=True  ref=HIT
    codex   gpt-5.6-sol  effort=high   staleness=current  durable_evidence=True  ref=HIT
    grok    grok-4.6     effort=xhigh  staleness=current  durable_evidence=True  ref=HIT

Two independent tolerances carry this. `has_baseline_bundle_for_version` skips the effort
comparison for a legacy artifact version, so the v8 bundles still satisfy an effort keyed
query. `read_current_baseline_ref` falls back to the effort-less path when the effort keyed
one is absent, and only accepts the fallback at pointer version 5, so it cannot pick up a
half migrated v6 pointer by mistake.

`_read_pointer` upgrades a v5 payload in memory (`effort = None`) and never rewrites the
operator's file, matching how `read_baseline_bundle` normalizes a legacy cell. `_prune_superseded_attempt_versions`
globs `current_path.parent`, which now includes the effort directory, so it prunes within
the right scope rather than across efforts.

`launch_verification_lock_root` and `launch_verification_workspace` append
`quote(cell.effort or "")`. `Path.joinpath` drops empty segments, confirmed, so an
effort-less cell keeps byte-identical lock and workspace paths. No in-flight lock identity
moves.

The one behaviour I want stated rather than discovered: for a legacy attempt record,
`_parse_baseline_attempt` sets `effort = None`, and `read_baseline_attempt` compares effort
as part of its identity tuple, so a v8 attempt is invisible to an effort keyed query. It
does not matter here: all three live records are `succeeded`, the durable evidence check runs
first and short circuits, and `_capture_is_due` treats `None` and `succeeded` identically.
It would matter for a crashed capture, where a legacy `in_progress` record would no longer
suppress a duplicate. No such record exists.

## 2. The residual gap

**Confirmed as described, and acceptable as shipped, but it is not stated plainly.** See d1.

Executed against the branch:

    explicit + benign passthrough  actuated_model=claude-opus-4-8  cell=VerificationCell(claude, claude-opus-4-8, None)
    explicit, no passthrough       actuated_model=claude-opus-4-8  cell=VerificationCell(claude, claude-opus-4-8, None)
    palette (no model), no pt      actuated_model=None             cell=VerificationCell(claude, claude-opus-4-8, None)
    palette + benign passthrough   actuated_model=None             cell=NoVerificationCell(model_ambiguous_passthrough)
    palette + model passthrough    actuated_model=None             cell=NoVerificationCell(model_ambiguous_passthrough)

**M1 is genuinely fixed.** Line 1 is the exact case I demonstrated broken at `7bb9da91`, and
it now yields a cell with actuation unchanged. `test_an_explicitly_named_model_with_benign_passthrough_is_the_cell`
pins it as a regression test.

Line 4 is the residual gap. It is the conservative option, it fails closed rather than
naming a cell it cannot justify, and the honest defence is that Transport Matters cannot
know whether an arbitrary passthrough carries a model without parsing three harnesses' flag
vocabularies. I would ship it.

## 3. `template_matches_harness`. Correct, necessary, and it suppresses nothing legitimate.

It predates this delta; I did not call it out at `7bb9da91` and should have.

Necessary. Without it, a launch whose `runtime_template.harness` differs from the launch
harness would read the template home anyway, and template homes carry both files: the
`generalist` home ships a `settings.json` with a model and a `config.toml` with a different
one. A codex template on a claude launch would hand back a real, wrong selector rather than
nothing. That is the wrong key case the whole design exists to avoid.

Correct, and it cannot suppress a legitimate launch. `_validated_template` in
`cli/runtime_home.py` raises on exactly this mismatch, so a mismatched pair never reaches a
successful launch. The guard only declines to read a home for a launch that will fail later.

One nit, not a finding: in `RuntimeHomeMode.MANUAL` the template is never validated, and
`resolve_launch_content_home` returns the manual home rather than the template home, so a
manual launch carrying a mismatched template would lose its cell for a reason that no longer
applies. Manual home, plus a mismatched template, plus no typed model is narrow enough to
leave alone.

## 4. Home certification, renewed

Re-certified rather than withdrawn.

`resolve_source_home_dir` had zero callers at `7bb9da91`: a definition, an import, and an
`__all__` entry. The delta deletes exactly those three references. Nothing called it, so
nothing resolves a home differently.

`home_overlay._config_source_name` now calls `home_constants.resolve_toml_config_path`,
whose body is the pre-`7bb9da91` logic restored verbatim for codex and grok: qualified
`config.<harness>.toml` when it is a file, the shared `config.toml` otherwise. For claude it
now raises instead of silently returning `settings.json`, which removes the latent trap I
raised as m2, and `test_config_source_name_rejects_non_toml_harness` pins it. This is
strictly better than `7bb9da91` and identical to `main` for every reachable harness.

The filename constants moved back to `cli/home_constants`, with
`configured_launch_model` importing them. That inverts the m5 direction correctly.

**A correction to my own design note.** I wrote there that "the API layer imports nothing
from `cli/` today and this must not be the first exception". That was true of files under
`api/`, and still is, but the runtime import graph already crossed that line before this
work: `baseline_capture` imports `cli.home_seed` and `captured/grok` imports
`cli.explicit_proxy` and `cli.trust`, both at module scope. So the new
`configured_launch_model` to `cli.home_constants` edge joins an existing pattern rather than
opening one, and importing `capture_rpc_routes` already pulled in `transport_matters.cli`
and typer. I am not raising it as a finding, and my earlier framing overstated the boundary.

## Minor

### d1. The residual gap is neither tested nor stated

`test_passthrough_capture_does_not_infer_a_cell_from_home_config` uses
`("--model", "claude-sonnet-5")`, the case where suppression is obviously right. Nothing
covers a benign passthrough with no typed model, which is the case the conservative choice
actually decides. Nothing would fail if someone later narrowed the guard to model bearing
passthrough only, which is the option that was considered and not taken.

The reason code `model_ambiguous_passthrough` names the intent well and is a real
improvement on m1. Add the missing case as a test, and say beside the guard why any
passthrough disqualifies: the alternative is parsing three harnesses' flag vocabularies to
decide whether one carries a selector.

### d2. Two readers of the same pointer disagree, deliberately, and nothing says so

Verified live: for all three cells, `read_current_baseline_ref(effort=...)` is a HIT while
`read_current_baseline(effort=...)` is a MISS. Only the ref reader has the legacy fallback.

The asymmetry is correct. `harvest_controlled_baseline` calls `read_current_baseline(...,
effort=model.default_effort)` for the reference bundle, and `_require_comparable_capture_plan`
now includes `"effort": effort` in its expected coordinates, so a legacy effort-less
reference would raise "not comparable" rather than compare. Returning `None` avoids a crash
the fallback would cause. The cheap freshness read wants the opposite, and gets it.

Two consequences worth writing down. Neither function's docstring mentions the split, so the
next reader has to derive it. And the first effort keyed re-capture of each existing cell,
which happens the next time a harness version moves, will produce a bundle with
`reference_bundle_id=None` and no comparison, silently indistinguishable from a first ever
capture. That is inherent to adding a coordinate and is the right trade, but it should be
stated where version 10 is explained, next to the sentence about legacy evidence carrying
unknown effort.

### d3. The effort-less current pointer is never superseded

A new capture writes `current/claude/anthropic/opus/high.json` and leaves
`current/claude/anthropic/opus.json` standing. `read_current_baseline_refs` now uses `rglob`,
so both enumerate forever. The legacy one can never be refreshed, because every future
palette launch supplies an effort: `~/.claude/settings.json` sets `effortLevel: high` and
`~/.grok/config.toml` sets `default_reasoning_effort = "xhigh"`.

Latent today. `assess_baseline_staleness` has no production caller, so nothing surfaces the
stale entry to an operator. But `publish_gate_projections` will keep republishing its
projection and `read_gate_projections` will keep feeding it into the comparison cohort as a
distinct effort-`None` member. `_ModelCohortCoordinates` gained `effort`, so it is treated
as a separate coordinate rather than a duplicate, which is why nothing breaks. It is an
immortal row that no code path can retire.

Either supersede the effort-less pointer when the first effort keyed pointer is written for
the same cell, or state that a legacy pointer is retained deliberately as unknown-effort
evidence. Do not leave it as an accident of the fallback.

### d4. `VerificationCell.effort` has no `min_length`, `BaselineCell.effort` does

`BaselineCell.effort` is `str | None = Field(default=None, min_length=1)`, so an empty string
is refused at the artifact boundary. `VerificationCell.effort` is a bare `str | None`. An
empty string there would flow into `quote(cell.effort or "")` in
`launch_verification_lock_root` and `launch_verification_workspace`, where `Path.joinpath`
drops the empty segment, silently collapsing an empty effort onto the effort-`None` lock and
workspace, and into `_current_path`, whose `if effort is None` test would take the effort
branch and write `<model>/.json`.

Not reachable through the resolver today, which yields `None` or a validated vocabulary
member. It is one field constraint away from being unreachable by construction, and the two
models describing the same coordinate should agree.

## Standing guards, all re-verified at 0543ec77

- **No re-capture.** All three live cells read `current` with `durable_evidence=True` under
  their configured efforts.
- **Cell naming only, actuation unchanged.** The palette case actuates `model=None` while
  naming `claude-opus-4-8`, executed above. The explicit cases keep their typed model.
- **The `#440` gap test still inverts.** `test_palette_unverified_catalog_names_configured_cell_and_submits`
  is untouched by this delta and still asserts a `VerificationCell` plus an accepted submit
  against `(domain.model, domain.effort) == (None, None)`.
- **Keys still exact.** `opus`, `gpt-5.6-sol`, `grok-4.6`, matching the operator's three
  bundle directories, and now with `.strip()` applied so a padded config value resolves
  instead of silently losing the cell.

## Verdict

**MERGE.** The major is fixed with a regression test that names the exact case, all six
minors are addressed, and the one that could not be small was done properly: effort is now a
coordinate everywhere it needs to be, legacy artifacts still read, and I proved on the
operator's real v8 store that nothing re-captures. The four remaining minors are all about
saying out loud what the code already does correctly, plus one field constraint.
